import tempfile
import errno
import unittest
import json
from pathlib import Path
import sys
import shutil
import tomllib
import subprocess
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import configuration
import install
import workflow
from test_support import isolate_git


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        isolate_git(self)

    def test_role_expectations_use_one_settings_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.toml"
            settings = configuration.load()
            settings["roles"]["ticket_implementer"] = {"model": "example.other-model", "effort": "medium"}
            sections = {"launcher": settings["launcher"]}
            sections.update({"roles." + name: role for name, role in settings["roles"].items()})
            path.write_text('default_session = "current"\n' + "\n".join(
                f"[{name}]\nmodel = {json.dumps(role['model'])}\neffort = {json.dumps(role['effort'])}\n"
                for name, role in sections.items()
            ))
            expected = configuration.expectations(path)
            self.assertEqual(("example.other-model", "medium", 2), expected["ticket_implementer"])

    def test_invalid_entry_mode_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.toml"
            path.write_text(configuration.SETTINGS.read_text().replace(
                f'default_session = "{configuration.load()["default_session"]}"',
                'default_session = "unknown"'))
            with self.assertRaises(ValueError):
                configuration.load(path)

    def test_audit_repair_limit_requires_positive_integer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.toml"
            original = configuration.SETTINGS.read_text()
            for value in ("0", "-1", "true", '"two"'):
                with self.subTest(value=value):
                    path.write_text(original.replace("audit_repair_rounds = 2", f"audit_repair_rounds = {value}"))
                    with self.assertRaisesRegex(ValueError, "audit_repair_rounds"):
                        configuration.load(path)

    def test_install_and_runtime_follow_changed_settings_without_changing_outer_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            shutil.copytree(configuration.SETTINGS.parent, source, ignore=shutil.ignore_patterns("__pycache__"))
            selected = configuration.load()
            replacement = selected["roles"]["ticket_implementer"]["model"] + "-changed"
            settings = source / "settings.toml"
            settings.write_text(settings.read_text().replace(
                json.dumps(selected["roles"]["ticket_implementer"]["model"]), json.dumps(replacement)))
            destination = root / "skills/implement-spec-single-worker"
            tdd = destination.parent / "tdd/SKILL.md"
            tdd.parent.mkdir(parents=True)
            tdd.write_text("TDD fixture")
            home = root / "codex"
            home.mkdir()
            base = home / "config.toml"
            base.write_text('model = "user-choice"\nmodel_reasoning_effort = "low"\n')
            retired = {
                "scripts/smoke_test.py": "old probe script",
                "references/runtime-evidence.json": '{"old": "probe receipt"}',
            }
            for name, content in retired.items():
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            install.install(source, destination, home)
            for name, content in retired.items():
                self.assertFalse((destination / name).exists())
                backups = list((home / "backups").rglob(Path(name).name))
                self.assertEqual(1, len(backups))
                self.assertEqual(content, backups[0].read_text())
            expected = configuration.expectations(settings)
            with patch.dict("os.environ", {"CODEX_HOME": str(home)}), \
                    patch.object(configuration, "SETTINGS", destination / "settings.toml"):
                for target in workflow.config_paths():
                    role = "outer" if target.name.endswith(".config.toml") else target.stem
                    rendered = tomllib.loads(target.read_text())
                    self.assertEqual(expected[role][:2],
                                     (rendered["model"], rendered["model_reasoning_effort"]))
                    self.assertNotIn("max_concurrent_threads_per_session", rendered.get("agents", {}))
                workflow.verify_configuration()
                arguments = workflow.enforced_config_arguments()
                self.assertFalse(any("max_concurrent_threads_per_session" in value or "features." in value
                                     for value in arguments))
                current_arguments = workflow.enforced_config_arguments(include_outer_model=False)
                self.assertFalse(any(value.startswith(("model=", "model_reasoning_effort="))
                                     for value in current_arguments))
                self.assertIn("agents.max_depth=2", current_arguments)
                for role in configuration.DEPTHS:
                    self.assertTrue(any(value.startswith(f"agents.{role}.config_file=")
                                        for value in current_arguments))
                for target in (home / "implement-spec.config.toml",
                               home / "agents/implementation_coordinator.toml"):
                    self.assertNotIn("features", tomllib.loads(target.read_text()))
                self.assertNotIn("agents", tomllib.loads(
                    (home / "agents/implementation_coordinator.toml").read_text()))
                initial = workflow.config_fingerprint()
                current = destination / "settings.toml"
                current.write_text(current.read_text().replace(json.dumps(replacement), '"example.next-model"'))
                self.assertNotEqual(initial, workflow.config_fingerprint())
                with self.assertRaises(workflow.WorkflowError):
                    workflow.verify_configuration()
            self.assertEqual('model = "user-choice"\nmodel_reasoning_effort = "low"\n', base.read_text())

    def legacy_project(self, directory, cap=False):
        project = Path(directory) / "repo"
        project.mkdir()
        workflow.git(project, "init", "-b", "main")
        home = Path(directory) / "codex"
        config = project / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text(
            '[features]\nmulti_agent = true\nmulti_agent_v2 = false\n'
            '[agents]\nmax_depth = 2\n'
            + ('max_concurrent_threads_per_session = 2\n' if cap else "")
            + "\n".join(
                f'[agents.{role}]\nconfig_file = {json.dumps(str(home / "agents" / (role + ".toml")))}'
                for role in configuration.DEPTHS
            ) + "\n"
        )
        return project, home, config

    def test_removes_only_confirmed_workflow_config_with_exact_backup(self):
        for cap in (False, True):
            with self.subTest(cap=cap), tempfile.TemporaryDirectory() as directory:
                project, home, config = self.legacy_project(directory, cap)
                original = config.read_bytes()
                install.remove_project_setup(project, home, confirmed_workflow_only=True)
                self.assertFalse(config.exists())
                backups = list((home / "backups").glob("implement-spec-project-removed-*.toml"))
                self.assertEqual(1, len(backups))
                self.assertEqual(original, backups[0].read_bytes())
                install.remove_project_setup(project, home, confirmed_workflow_only=True)
                self.assertEqual(backups, list((home / "backups").glob("*.toml")))
                self.assertFalse((home / "config.toml").exists())

    def test_cleanup_preserves_mixed_user_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            project, home, config = self.legacy_project(directory)
            original = 'model = "user-choice"\n' + config.read_text().replace("max_depth = 2", "max_depth = 7")
            config.write_text(original)
            with self.assertRaisesRegex(RuntimeError, "user settings"):
                install.remove_project_setup(project, home, confirmed_workflow_only=True)
            self.assertEqual(original, config.read_text())
            self.assertFalse((home / "backups").exists())
            self.assertFalse((home / "config.toml").exists())

    def test_cleanup_refuses_symlinked_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            project, home, config = self.legacy_project(directory)
            original = config.read_bytes()
            other = Path(directory) / "other.toml"
            config.rename(other)
            try:
                config.symlink_to(other)
            except OSError as error:
                if getattr(error, "winerror", None) == 1314 or error.errno in {errno.EPERM, errno.ENOSYS, errno.EOPNOTSUPP}:
                    self.skipTest(f"Symlink creation unavailable: {error}")
                raise
            with self.assertRaisesRegex(RuntimeError, "symlink"):
                install.remove_project_setup(project, home)
            self.assertEqual(original, other.read_bytes())
            self.assertTrue(config.is_symlink())

    def test_matching_generated_values_do_not_prove_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            project, home, config = self.legacy_project(directory, cap=True)
            original_user = '[agents]\nmax_depth = 7\nmax_concurrent_threads_per_session = 2\n'
            backup = home / "backups/implement-spec-project-original.toml"
            backup.parent.mkdir(parents=True)
            backup.write_text(original_user)
            installed = config.read_bytes()
            with self.assertRaisesRegex(RuntimeError, "do not prove ownership"):
                install.remove_project_setup(project, home)
            self.assertEqual(installed, config.read_bytes())
            self.assertEqual(original_user, backup.read_text())
            self.assertEqual([backup], list(backup.parent.glob("*.toml")))

    def test_old_setup_command_cannot_reintroduce_project_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            project, home, config = self.legacy_project(directory)
            config.unlink()
            result = subprocess.run(
                [sys.executable, str(Path(install.__file__)), "--project", str(project),
                 "--codex-home", str(home)],
                capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("unrecognized arguments", result.stderr)
            self.assertFalse(config.exists())
            self.assertFalse(home.exists())


if __name__ == "__main__":
    unittest.main()
