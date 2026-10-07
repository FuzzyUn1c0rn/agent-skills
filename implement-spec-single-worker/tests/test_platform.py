import os
import errno
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
HELPER_ENV = dict(os.environ, PYTHONPATH=os.pathsep.join(
    part for part in (str(SCRIPTS), os.environ.get("PYTHONPATH")) if part
))


class ExecutableTests(unittest.TestCase):
    def test_path_resolution_accepts_a_native_binary_in_a_directory_with_spaces_and_unicode(self):
        from platform_support import resolve_codex

        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "native tools Ω"
            folder.mkdir()
            binary = folder / ("codex.exe" if os.name == "nt" else "codex")
            shutil.copy2(sys.executable, binary)
            with patch.dict(os.environ, {"PATH": str(folder)}):
                os.environ.pop("IMPLEMENT_SPEC_CODEX", None)
                self.assertEqual(binary.resolve(), resolve_codex())

    def test_selected_path_wrapper_is_not_skipped_for_a_later_native_installation(self):
        from platform_support import ExecutableError, resolve_codex

        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            later = Path(directory) / "later"
            first.mkdir()
            later.mkdir()
            wrapper = first / ("codex.cmd" if os.name == "nt" else "codex")
            wrapper.write_bytes(b"#!/bin/sh\necho unsupported\n")
            wrapper.chmod(0o755)
            shutil.copy2(sys.executable, later / ("codex.exe" if os.name == "nt" else "codex"))
            with patch.dict(os.environ, {"PATH": str(first) + os.pathsep + str(later)}):
                os.environ.pop("IMPLEMENT_SPEC_CODEX", None)
                with self.assertRaises(ExecutableError) as rejected:
                    resolve_codex()
                self.assertIn(str(wrapper.resolve()), str(rejected.exception))

    def test_symlink_to_a_native_binary_resolves_to_the_executable(self):
        from platform_support import resolve_codex

        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / ("codex.exe" if os.name == "nt" else "codex")
            try:
                link.symlink_to(sys.executable)
            except OSError as error:
                if getattr(error, "winerror", None) == 1314 or error.errno in {errno.EPERM, errno.ENOSYS, errno.EOPNOTSUPP}:
                    self.skipTest(f"Symlink creation unavailable: {error}")
                raise
            with patch.dict(os.environ, {"IMPLEMENT_SPEC_CODEX": str(link)}):
                self.assertEqual(Path(sys.executable).resolve(), resolve_codex())

    def test_invalid_overrides_are_paths_not_shell_commands_or_fallback_requests(self):
        from platform_support import ExecutableError, resolve_codex

        with tempfile.TemporaryDirectory() as directory:
            for selected in ("", str(Path(directory) / "absent"), directory, sys.executable + " --version"):
                with self.subTest(selection=selected), patch.dict(os.environ, {"IMPLEMENT_SPEC_CODEX": selected}):
                    with self.assertRaises(ExecutableError) as rejected:
                        resolve_codex()
                    self.assertIn("IMPLEMENT_SPEC_CODEX", str(rejected.exception))

    def test_missing_path_selection_has_installation_override_guidance(self):
        from platform_support import ExecutableError, resolve_codex

        with patch.dict(os.environ, {"PATH": ""}):
            os.environ.pop("IMPLEMENT_SPEC_CODEX", None)
            with self.assertRaises(ExecutableError) as rejected:
                resolve_codex()
            self.assertIn("IMPLEMENT_SPEC_CODEX", str(rejected.exception))

    @unittest.skipIf(os.name == "nt", "Windows chmod does not control executable permission")
    def test_nonexecutable_native_file_is_rejected(self):
        from platform_support import ExecutableError, resolve_codex

        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "codex"
            shutil.copy2(sys.executable, binary)
            binary.chmod(0o644)
            with patch.dict(os.environ, {"IMPLEMENT_SPEC_CODEX": str(binary)}):
                with self.assertRaises(ExecutableError):
                    resolve_codex()

    def test_selected_script_wrapper_is_rejected_with_override_guidance(self):
        from platform_support import ExecutableError, resolve_codex

        with tempfile.TemporaryDirectory() as directory:
            wrapper = Path(directory) / ("codex.exe" if os.name == "nt" else "codex")
            wrapper.write_bytes(b"#!/usr/bin/env python3\nprint('wrapper')\n")
            wrapper.chmod(0o755)
            with patch.dict(os.environ, {"IMPLEMENT_SPEC_CODEX": str(wrapper)}):
                with self.assertRaises(ExecutableError) as rejected:
                    resolve_codex()
            self.assertIn("unsupported", str(rejected.exception).lower())
            self.assertIn("IMPLEMENT_SPEC_CODEX", str(rejected.exception))

    def test_explicit_native_executable_overrides_path_and_resolves_absolute_path(self):
        from platform_support import resolve_codex

        with patch.dict(os.environ, {"IMPLEMENT_SPEC_CODEX": sys.executable, "PATH": ""}):
            self.assertEqual(Path(sys.executable).resolve(), resolve_codex())


class LockTests(unittest.TestCase):
    def test_missing_dependency_identifies_the_selected_interpreter_and_install_command(self):
        for helper in ("entry.py", "workflow.py", "install.py"):
            with self.subTest(helper=helper):
                result = subprocess.run(
                    [sys.executable, "-S", str(SCRIPTS / helper), "--help"],
                    env=dict(os.environ, PYTHONPATH=""),
                    capture_output=True, text=True,
                )
                self.assertNotEqual(0, result.returncode)
                self.assertIn(sys.executable, result.stderr)
                self.assertIn("Missing Portalocker", result.stderr)
                self.assertIn("-m pip install -r", result.stderr)
                self.assertIn("requirements.txt", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_unsupported_runtime_identifies_the_selected_interpreter_and_upgrade(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.version_info = (3, 10, 0); import workflow"],
            env=HELPER_ENV, capture_output=True, text=True,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn(sys.executable, result.stderr)
        self.assertIn("Python 3.11 or later", result.stderr)
        self.assertIn("rerun this helper", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_backend_failures_remain_errors_instead_of_contention(self):
        import portalocker
        from platform_support import LockContended, LockError, exclusive

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkout.lock"
            with patch("portalocker.portalocker.lock", side_effect=portalocker.LockException("backend unavailable")):
                with self.assertRaises(LockError) as failed:
                    with exclusive(path):
                        self.fail("Entered after a backend failure")
            self.assertNotIsInstance(failed.exception, LockContended)
            self.assertIn("backend unavailable", str(failed.exception))
            with exclusive(path):
                pass

    def test_filesystem_failures_remain_errors_instead_of_contention(self):
        from platform_support import exclusive

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(OSError):
                with exclusive(Path(directory)):
                    self.fail("A directory cannot be used as a lock file")

    def test_forced_holder_death_releases_the_lock_for_a_new_process(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkout.lock"
            child = subprocess.Popen(
                [sys.executable, "-c",
                 "import sys; from platform_support import exclusive; "
                 "\nwith exclusive(sys.argv[1]):\n print('ready', flush=True); input()", str(path)],
                env=HELPER_ENV,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                ready = queue.Queue()
                threading.Thread(target=lambda: ready.put(child.stdout.readline()), daemon=True).start()
                self.assertEqual("ready\n", ready.get(timeout=5))
                child.kill()
                child.communicate(timeout=5)
                acquired = subprocess.run(
                    [sys.executable, "-c",
                     "import sys; from platform_support import exclusive; "
                     "\nwith exclusive(sys.argv[1]):\n print('acquired')", str(path)],
                    env=HELPER_ENV,
                    capture_output=True, text=True, timeout=5,
                )
                self.assertEqual(0, acquired.returncode, acquired.stderr)
                self.assertEqual("acquired\n", acquired.stdout)
                self.assertTrue(path.is_file())
            finally:
                if child.poll() is None:
                    child.kill()
                child.communicate(timeout=5)

    def test_helpers_import_in_the_selected_native_interpreter(self):
        result = subprocess.run(
            [sys.executable, "-c", "import workflow, entry, install, configuration"],
            env=HELPER_ENV, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_independent_holder_contends_then_releases_without_removing_lock_file(self):
        from platform_support import LockContended, exclusive

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkout.lock"
            code = ("import sys; from platform_support import exclusive; "
                    "\nwith exclusive(sys.argv[1]):\n print('ready', flush=True); input()")
            child = subprocess.Popen(
                [sys.executable, "-c", code, str(path)],
                env=HELPER_ENV,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                ready = queue.Queue()
                threading.Thread(target=lambda: ready.put(child.stdout.readline()), daemon=True).start()
                self.assertEqual("ready\n", ready.get(timeout=5))
                started = time.monotonic()
                with self.assertRaises(LockContended):
                    with exclusive(path):
                        self.fail("Competing checkout operation entered")
                self.assertLess(time.monotonic() - started, 1, "Contention must fail immediately")
                child.communicate("\n", timeout=5)
                self.assertEqual(0, child.returncode)
                self.assertTrue(path.is_file())
                with exclusive(path):
                    pass
            finally:
                if child.poll() is None:
                    child.kill()
                child.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
