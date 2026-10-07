import os
from pathlib import Path
import queue
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
