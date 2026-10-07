import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_workflow as fixtures
import test_audit_repairs as repair_fixtures
import test_entry as entry_fixtures

workflow = fixtures.workflow


class TrackerTextTests(unittest.TestCase):
    setUp = fixtures.WorkflowTests.setUp
    new_run = fixtures.WorkflowTests.new_run
    implement_and_review = repair_fixtures.AuditRepairTests.implement_and_review
    audit_report = fixtures.WorkflowTests.audit_report
    failed_audit = repair_fixtures.AuditRepairTests.failed_audit
    repair_plan = repair_fixtures.AuditRepairTests.repair_plan

    def tracker_fixture(self, newline):
        workflow.git(self.repo, "config", "core.autocrlf", "false")
        workflow.git(self.repo, "config", "core.safecrlf", "false")
        original = ("# 仕様 café" + newline + "Status: ready-for-agent" + newline
                    + "Keep: 東京 🚀" + newline + "No final newline").encode("utf-8")
        for name in ("PRD.md", "ticket.md"):
            (self.repo / name).write_bytes(original)
        workflow.git(self.repo, "add", "--all")
        workflow.git(self.repo, "commit", "-m", "Unicode trackers")
        return original

    def test_status_edits_preserve_unicode_and_every_unrelated_byte(self):
        tracker = self.repo / "ticket.md"
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=repr(newline)):
                original = ("# 仕様 café" + newline + newline + "Status: ready-for-agent" + newline
                            + "Keep: 東京 🚀" + newline + "No final newline").encode("utf-8")
                tracker.write_bytes(original)
                self.assertEqual("ready-for-agent", workflow.status_text(tracker))
                workflow.set_status(tracker, "ready-for-agent")
                self.assertEqual(original, tracker.read_bytes())
                workflow.set_status(tracker, "closed")
                self.assertEqual(original.replace(b"Status: ready-for-agent", b"Status: closed"),
                                 tracker.read_bytes())

    def test_invalid_or_ambiguous_status_is_rejected_without_rewriting_the_tracker(self):
        tracker = self.repo / "ticket.md"
        for content in (b"Status: \r\n", b"Status: ready\nStatus: ready\r\n",
                        b"Status: ready\r\nStatus: \r\n", b"No status line\n"):
            with self.subTest(content=content):
                tracker.write_bytes(content)
                with self.assertRaises(workflow.WorkflowError):
                    workflow.set_status(tracker, "closed")
                self.assertEqual(content, tracker.read_bytes())

    def test_historical_audit_accepts_git_checkout_conversion_but_rejects_edits_and_deletion(self):
        workflow.git(self.repo, "config", "core.autocrlf", "true")
        workflow.git(self.repo, "config", "core.safecrlf", "false")
        run = self.new_run()
        run.begin("ticket.md")
        self.implement_and_review(run, "PASS")
        run.commit_ticket()
        self.failed_audit(run)
        audit = self.repo / "final-audit.md"
        audit.unlink()
        workflow.git(self.repo, "checkout", "--", "final-audit.md")
        original = audit.read_bytes()
        self.assertIn(b"\r\n", original)
        resumed = workflow.Run(self.repo, "PRD.md")
        resumed.ensure()
        audit.write_bytes(original + b"Meaningful report edit\r\n")
        with self.assertRaisesRegex(workflow.WorkflowError, "Historical audit"):
            resumed.ensure()
        audit.write_bytes(original)
        audit.unlink()
        with self.assertRaisesRegex(workflow.WorkflowError, "Historical audit"):
            resumed.ensure()

    def test_attributes_and_clean_filters_define_audit_integrity_while_snapshots_keep_raw_bytes(self):
        workflow.git(self.repo, "config", "core.autocrlf", "false")
        workflow.git(self.repo, "config", "core.safecrlf", "false")
        attributes = self.repo / ".gitattributes"
        attributes.write_bytes(b"* -text\nfinal-audit*.md text eol=crlf filter=audittext\n")
        filter_script = self.repo / "audit-filter.py"
        filter_script.write_bytes(
            b"import sys\ncontent = sys.stdin.buffer.read()\n"
            b"if sys.argv[1] == 'clean':\n"
            b"    content = content.removeprefix(b'CHECKOUT HEADER\\r\\n').removeprefix(b'CHECKOUT HEADER\\n')\n"
            b"else:\n    content = b'CHECKOUT HEADER\\n' + content\n"
            b"sys.stdout.buffer.write(content)\n"
        )
        command = f'"{Path(sys.executable).as_posix()}" "{filter_script.as_posix()}"'
        workflow.git(self.repo, "config", "filter.audittext.clean", command + " clean")
        workflow.git(self.repo, "config", "filter.audittext.smudge", command + " smudge")
        workflow.git(self.repo, "config", "filter.audittext.required", "true")
        workflow.git(self.repo, "add", "--all")
        workflow.git(self.repo, "commit", "-m", "Audit checkout attributes and filter")
        run = self.new_run()
        run.begin("ticket.md")
        self.implement_and_review(run, "PASS")
        run.commit_ticket()
        self.failed_audit(run)
        snapshot = workflow.snapshot(self.repo, [run.record])
        audit = self.repo / "final-audit.md"
        audit.unlink()
        workflow.git(self.repo, "checkout", "--", "final-audit.md")
        checked_out = audit.read_bytes()
        self.assertTrue(checked_out.startswith(b"CHECKOUT HEADER\n"))
        self.assertIn(b"\r\n", checked_out)
        resumed = workflow.Run(self.repo, "PRD.md")
        resumed.ensure()
        self.assertNotEqual(snapshot, workflow.snapshot(self.repo, [run.record]))
        audit.write_bytes(checked_out + b"Meaningful report edit\r\n")
        with self.assertRaisesRegex(workflow.WorkflowError, "Historical audit"):
            resumed.ensure()

    def test_failed_ticket_commit_and_retry_preserve_lf_and_crlf_unicode_trackers(self):
        for index, newline in enumerate(("\n", "\r\n")):
            with self.subTest(newline=repr(newline)):
                if index:
                    self.setUp()
                original = self.tracker_fixture(newline)
                run = self.new_run()
                run.begin("ticket.md")
                self.implement_and_review(run, "PASS")
                hook = self.repo / ".git/hooks/pre-commit"
                hook.write_bytes(b"#!/bin/sh\nexit 1\n")
                hook.chmod(0o755)
                with self.assertRaises(workflow.WorkflowError):
                    run.commit_ticket()
                self.assertEqual(original, (self.repo / "ticket.md").read_bytes())
                self.assertEqual(original, (self.repo / "PRD.md").read_bytes())
                hook.unlink()
                resumed = workflow.Run(self.repo, "PRD.md")
                resumed.reconcile_commit()
                self.assertEqual(original.replace(b"Status: ready-for-agent", b"Status: closed"),
                                 (self.repo / "ticket.md").read_bytes())
                self.assertEqual(1, resumed.data["tickets"]["ticket.md"]["attempts"])

    def test_interrupted_unicode_repair_reopening_preserves_capture_and_recovery(self):
        original = self.tracker_fixture("\r\n")
        run = self.new_run()
        run.begin("ticket.md")
        self.implement_and_review(run, "PASS")
        run.commit_ticket()
        self.failed_audit(run)
        original_run = subprocess.run

        def interrupt_commit(command, *arguments, **keywords):
            if command[:1] == ["git"] and "commit" in command[3:4]:
                raise KeyboardInterrupt()
            return original_run(command, *arguments, **keywords)

        with patch("subprocess.run", side_effect=interrupt_commit):
            with self.assertRaises(KeyboardInterrupt):
                run.repair_audit(self.repair_plan(run))
        resumed = workflow.Run(self.repo, "PRD.md")
        captured = resumed.data["transaction"]["file_edits"]["ticket.md"]
        self.assertEqual(original.replace(b"Status: ready-for-agent", b"Status: closed"),
                         captured["before"].encode("utf-8"))
        resumed.reconcile_commit()
        reopened = (self.repo / "ticket.md").read_bytes()
        self.assertTrue(reopened.startswith(original))
        self.assertNotIn(b"\n", reopened.replace(b"\r\n", b""))
        self.assertEqual(original, (self.repo / "PRD.md").read_bytes())
        self.assertEqual(1, resumed.data["tickets"]["ticket.md"]["attempts"])
        resumed.begin("ticket.md")
        self.implement_and_review(resumed, "PASS")
        resumed.commit_ticket()
        self.assertEqual(reopened.replace(b"Status: ready-for-agent", b"Status: closed"),
                         (self.repo / "ticket.md").read_bytes())
        self.assertEqual(2, resumed.data["tickets"]["ticket.md"]["attempts"])


class Utf8EncodingTests(unittest.TestCase):
    def test_configuration_and_native_metadata_use_utf8_with_legacy_locale_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / "settings.toml"
            settings.write_bytes(entry_fixtures.configuration.SETTINGS.read_bytes() + "\n# 東京 🚀\n".encode("utf-8"))
            session = root / "sessions/native-unicode.jsonl"
            session.parent.mkdir()
            session.write_bytes(json.dumps({"type": "session_meta", "payload": {
                "id": "unicode", "cwd": "東京 🚀", "source": "cli",
            }}, ensure_ascii=False).encode("utf-8") + b"\n")
            script = (
                "import sys, json\n"
                f"sys.path.insert(0, {str(Path(workflow.__file__).parent)!r})\n"
                "import workflow, configuration\n"
                "configuration.load(sys.argv[1])\n"
                "print(json.dumps(workflow.session_metadata('unicode')))\n"
            )
            environment = dict(os.environ, CODEX_HOME=str(root), PYTHONUTF8="0",
                               PYTHONCOERCECLOCALE="0", LC_ALL="C")
            result = subprocess.run([sys.executable, "-X", "utf8=0", "-c", script, str(settings)],
                                    env=environment, capture_output=True, text=True, encoding="utf-8", timeout=10)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("東京 🚀", json.loads(result.stdout)["cwd"])

    def test_installed_utf8_configuration_preserves_unicode_templates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            shutil.copytree(entry_fixtures.configuration.SETTINGS.parent, source,
                            ignore=shutil.ignore_patterns("__pycache__"))
            template = source / "assets/implement-spec.config.toml"
            comment = "\n# 東京 🚀\n".encode("utf-8")
            template.write_bytes(template.read_bytes() + comment)
            destination = root / "skills/implement-spec-single-worker"
            tdd = destination.parent / "tdd/SKILL.md"
            tdd.parent.mkdir(parents=True)
            tdd.write_bytes("# TDD 東京\n".encode("utf-8"))
            home = root / "codex"
            entry_fixtures.install.install(source, destination, home)
            self.assertIn(comment, (home / "implement-spec.config.toml").read_bytes())
            with patch.dict(os.environ, {"CODEX_HOME": str(home)}), \
                    patch.object(entry_fixtures.configuration, "SETTINGS", destination / "settings.toml"):
                workflow.verify_configuration()


class EntryUtf8Tests(unittest.TestCase):
    setUp = entry_fixtures.EntryTests.setUp
    start = entry_fixtures.EntryTests.start

    def test_utf8_release_report_is_accepted_by_real_entry_command(self):
        (self.repo / "ticket.md").write_bytes("# 仕様 東京 🚀\nStatus: ready-for-agent\n".encode("utf-8"))
        workflow.git(self.repo, "add", "ticket.md")
        workflow.git(self.repo, "commit", "-m", "Unicode ticket fixture")
        process, ownership = self.start()
        admitted = subprocess.run(self.command + ["admit", "PRD.md", "--repo", str(self.repo)],
                                  env=self.env, capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(0, admitted.returncode, admitted.stderr)
        plan = self.root / "plan.json"
        plan.write_bytes(json.dumps({
            "spec": "PRD.md", "tracker": {"kind": "local-markdown"}, "checks": [["suite"]], "requirements": ["US1"],
            "approval_evidence": "東京 🚀 approved requirements and seams.",
            "tickets": [{"path": "ticket.md", "execution": "AFK", "criteria": ["AC1"], "seams": ["public"]}],
        }, ensure_ascii=False).encode("utf-8"))
        initialized = subprocess.run(
            self.workflow_command + ["init", "PRD.md", "--repo", str(self.repo), "--plan", str(plan)],
            env=self.env, capture_output=True, text=True, encoding="utf-8", timeout=10,
        )
        self.assertEqual(0, initialized.returncode, initialized.stderr)
        self.assertEqual("東京 🚀 approved requirements and seams.",
                         workflow.Run(self.repo, "PRD.md").data["plan"]["approval_evidence"])
        report = self.root / "release.json"
        report.write_bytes(json.dumps({"launch_id": ownership["launch_id"], "previous_workers_inactive": True,
                                      "evidence": "東京 🚀 agents closed."},
                                     ensure_ascii=False).encode("utf-8"))
        released = subprocess.run(
            self.command + ["stop", "PRD.md", "--repo", str(self.repo), "--report", str(report)],
            env=self.env, capture_output=True, text=True, encoding="utf-8", timeout=10,
        )
        self.assertEqual(0, released.returncode, released.stderr)
        self.assertEqual(0, process.wait(timeout=5))


if __name__ == "__main__":
    unittest.main()
