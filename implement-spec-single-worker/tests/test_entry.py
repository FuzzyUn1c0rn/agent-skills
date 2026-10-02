import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import unittest
import datetime
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import configuration
import install
import workflow


class EntryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        workflow.git(self.repo, "init", "-b", "main")
        workflow.git(self.repo, "config", "user.name", "Entry test")
        workflow.git(self.repo, "config", "user.email", "entry@example.invalid")
        (self.repo / "PRD.md").write_text("Status: ready-for-agent\n")
        workflow.git(self.repo, "add", "PRD.md")
        workflow.git(self.repo, "commit", "-m", "Fixture")
        self.home = self.root / "codex"
        self.skill = self.root / "skills/implement-spec-single-worker"
        tdd = self.skill.parent / "tdd/SKILL.md"
        tdd.parent.mkdir(parents=True)
        tdd.write_text("TDD fixture")
        source = Path(__file__).resolve().parents[1]
        install.install(source, self.skill, self.home)
        binary = self.root / "bin"
        binary.mkdir()
        codex = binary / "codex"
        codex.write_text('#!/bin/sh\nif [ "$1" = "--version" ]; then\n'
                         'echo "codex-cli fixture"\nelse\n'
                         'echo "UNEXPECTED_CODEX_LAUNCH" >&2\nexit 99\nfi\n')
        codex.chmod(0o755)
        self.env = dict(os.environ, CODEX_HOME=str(self.home),
                        CODEX_THREAD_ID="selected-outer", PATH=str(binary) + ":" + os.environ["PATH"])
        self.command = [sys.executable, str(self.skill / "scripts/entry.py")]

    def start(self, *options):
        process = subprocess.Popen(
            self.command + ["start", "PRD.md", "--repo", str(self.repo), "--session", "current", *options],
            env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        def cleanup():
            if process.poll() is None:
                process.terminate()
            process.communicate(timeout=5)
        self.addCleanup(cleanup)
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            self.assertTrue(selector.select(5), "Current-session entry did not report readiness")
        line = process.stdout.readline()
        if not line:
            self.fail(process.stderr.read())
        return process, json.loads(line)

    def command_result(self, action, report=None):
        command = self.command + [action, "PRD.md", "--repo", str(self.repo), "--session", "current"]
        if report is not None:
            path = self.root / "report.json"
            path.write_text(json.dumps(report))
            command += ["--report", str(path)]
        return subprocess.run(command, env=self.env, capture_output=True, text=True, timeout=5)

    def test_current_entry_holds_common_lock_without_launching_or_switching_branch(self):
        process, entry = self.start()
        self.assertEqual("preflight", entry["phase"])
        self.assertEqual("selected-outer", entry["outer_session"])
        self.assertEqual("main", workflow.git(self.repo, "branch", "--show-current"))
        self.assertFalse((self.repo / ".codex").exists())
        self.assertFalse((self.home / "config.toml").exists())
        with self.assertRaises(workflow.WorkflowError):
            with workflow.exclusive(workflow.git_home(self.repo) / "launch.lock"):
                self.fail("A second workflow acquired the checkout")
        rejected = self.command_result("stop")
        self.assertEqual(2, rejected.returncode)
        released = self.command_result("stop", {
            "previous_workers_inactive": True, "evidence": "No workflow agents were started.",
        })
        self.assertEqual(0, released.returncode, released.stderr)
        self.assertEqual(0, process.wait(timeout=5))
        with workflow.exclusive(workflow.git_home(self.repo) / "launch.lock"):
            pass
        self.assertFalse((workflow.git_home(self.repo) / "entry.json").exists())

    def test_crashed_entry_requires_explicit_inactive_worker_recovery(self):
        process, entry = self.start()
        process.kill()
        process.wait(timeout=5)
        failed = self.command_result("start")
        self.assertEqual(2, failed.returncode)
        self.assertIn("recover", failed.stderr)
        rejected = self.command_result("recover", {"previous_workers_inactive": True})
        self.assertEqual(2, rejected.returncode)
        recovered = self.command_result("recover", {
            "previous_workers_inactive": True, "previous_outer_session": entry["outer_session"],
            "evidence": "The old process and its children are confirmed stopped.",
        })
        self.assertEqual(0, recovered.returncode, recovered.stderr)
        self.assertFalse((workflow.git_home(self.repo) / "entry.json").exists())

    def test_admission_needs_no_probe_agents_transcripts_or_receipts(self):
        process, _ = self.start()
        (self.skill / "references/runtime-evidence.json").unlink(missing_ok=True)
        self.assertEqual("main", workflow.git(self.repo, "branch", "--show-current"))
        admitted = self.command_result("admit")
        self.assertEqual(0, admitted.returncode, admitted.stderr)
        entry = json.loads(admitted.stdout)
        self.assertEqual("admitted", entry["phase"])
        self.assertEqual("selected-outer", entry["outer_session"])
        self.assertFalse((self.repo / ".codex").exists())
        self.assertFalse((self.home / "sessions").exists())
        self.assertFalse((workflow.git_home(self.repo) / "current-probe.txt").exists())
        self.assertFalse((workflow.git_home(self.repo) / "current-evidence.json").exists())
        self.assertNotIn("probe_prompt", entry)
        self.assertNotIn("checks", entry)
        self.assertTrue(entry["branch"].startswith("implement/"))
        self.assertEqual(entry["branch"], workflow.git(self.repo, "branch", "--show-current"))
        self.assertIsNone(process.poll())

    def test_admission_still_rejects_changed_profile_configuration(self):
        self.start()
        profile = self.home / "agents/ticket_implementer.toml"
        profile.write_text(profile.read_text() + "\n")
        failed = self.command_result("admit")
        self.assertEqual(2, failed.returncode)
        self.assertIn("settings changed", failed.stderr)
        self.assertEqual("main", workflow.git(self.repo, "branch", "--show-current"))

    def test_explicit_branch_can_contain_a_prd_absent_on_the_starting_branch(self):
        workflow.git(self.repo, "branch", "feature-with-prd")
        (self.repo / "PRD.md").unlink()
        workflow.git(self.repo, "add", "-u")
        workflow.git(self.repo, "commit", "-m", "No PRD on main")
        self.start("--branch", "feature-with-prd")
        self.assertEqual("main", workflow.git(self.repo, "branch", "--show-current"))
        result = self.command_result("admit")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("feature-with-prd", workflow.git(self.repo, "branch", "--show-current"))
        self.assertTrue((self.repo / "PRD.md").is_file())

    def test_resume_transfers_outer_without_resetting_attempts_or_accepting_dirty_changes(self):
        (self.repo / "ticket.md").write_text("Status: ready-for-agent\n")
        workflow.git(self.repo, "add", "ticket.md")
        workflow.git(self.repo, "commit", "-m", "Ticket")
        workflow.choose_branch(self.repo, "PRD.md", "existing-feature")
        run = workflow.Run(self.repo, "PRD.md")
        run.create({
            "spec": "PRD.md", "checks": [["suite"]], "requirements": ["US1"],
            "approval_evidence": "Approved fixture",
            "tickets": [{"path": "ticket.md", "execution": "AFK", "criteria": ["AC1"], "seams": ["public"]}],
        })
        run.begin("ticket.md")
        run.data["outer_session"] = "previous-outer"
        run.save()
        checkpoint = run.data["checkpoint"]
        (self.repo / "unfinished.py").write_text("unfinished = True\n")
        self.start("--resume")
        rejected = self.command_result("admit")
        self.assertEqual(2, rejected.returncode)
        accepted = self.command_result("admit", {
            "previous_workers_inactive": True, "previous_outer_session": "previous-outer",
            "evidence": "Confirmed previous outer and every child stopped; retained unfinished changes.",
        })
        self.assertEqual(0, accepted.returncode, accepted.stderr)
        recovered = workflow.Run(self.repo, "PRD.md")
        self.assertEqual("selected-outer", recovered.data["outer_session"])
        self.assertEqual(1, recovered.data["tickets"]["ticket.md"]["attempts"])
        self.assertEqual(checkpoint, recovered.data["checkpoint"])
        self.assertEqual("implementing", recovered.data["phase"])
        self.assertTrue((self.repo / "unfinished.py").exists())
        self.assertEqual("existing-feature", workflow.git(self.repo, "branch", "--show-current"))

    def test_guard_rejects_mutation_before_current_session_admission(self):
        self.start()
        result = subprocess.run(
            [sys.executable, str(self.skill / "scripts/workflow.py"), "init", "PRD.md",
             "--repo", str(self.repo), "--plan", "/missing-plan"],
            env=self.env, capture_output=True, text=True,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("admission", result.stderr)

    def test_new_session_uses_configured_launcher_and_marks_the_attached_outer(self):
        binary = self.root / "bin/codex"
        capture = self.root / "launch.json"
        binary.write_text(
            f"#!{sys.executable}\nimport json, os, sys\n"
            "if sys.argv[1:] == ['--version']:\n    print('codex-cli fixture')\n"
            f"else:\n    open({str(capture)!r}, 'w').write(json.dumps("
            "{'arguments': sys.argv[1:], 'attached': os.environ.get('IMPLEMENT_SPEC_LAUNCH')}))\n"
        )
        binary.chmod(0o755)
        (self.skill / "references/runtime-evidence.json").unlink(missing_ok=True)
        result = subprocess.run(
            self.command + ["start", "PRD.md", "--repo", str(self.repo), "--session", "new"],
            env=self.env, capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        launched = json.loads(capture.read_text())
        selected = configuration.load()["launcher"]
        self.assertIn("model=" + json.dumps(selected["model"]), launched["arguments"])
        self.assertIn("model_reasoning_effort=" + json.dumps(selected["effort"]), launched["arguments"])
        self.assertFalse(any("max_concurrent_threads_per_session" in value for value in launched["arguments"]))
        self.assertFalse(any(value.startswith("features.") for value in launched["arguments"]))
        self.assertIn("agents.max_depth=2", launched["arguments"])
        self.assertFalse((self.repo / ".codex").exists())
        self.assertFalse((self.home / "config.toml").exists())
        self.assertEqual("1", launched["attached"])
        self.assertIn("already", launched["arguments"][-1])
        self.assertTrue(workflow.git(self.repo, "branch", "--show-current").startswith("implement/"))

    def test_doctor_checks_local_configuration_without_starting_codex_agents(self):
        (self.skill / "references/runtime-evidence.json").unlink(missing_ok=True)
        result = subprocess.run(
            [sys.executable, str(self.skill / "scripts/workflow.py"), "doctor"],
            env=self.env, capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("codex-cli fixture", report["runtime"])
        self.assertEqual({"installed_models": True}, report["checks"])
        self.assertFalse((self.home / "sessions").exists())

    def guard_result(self, environment=None):
        return subprocess.run(
            [sys.executable, str(self.skill / "scripts/workflow.py"), "init", "PRD.md",
             "--repo", str(self.repo), "--plan", "/missing-plan"],
            env=environment or self.env, capture_output=True, text=True, timeout=5,
        )

    def test_current_guard_rejects_unrelated_and_former_owners(self):
        self.start()
        self.assertEqual(0, self.command_result("admit").returncode)
        for caller in ("unrelated-session", "former-outer", ""):
            result = self.guard_result(dict(self.env, CODEX_THREAD_ID=caller))
            self.assertEqual(2, result.returncode)
            self.assertIn("owner", result.stderr)

    def test_workflow_profile_drift_invalidates_admission(self):
        self.start()
        self.assertEqual(0, self.command_result("admit").returncode)
        config = self.home / "agents/implementation_coordinator.toml"
        config.write_text(config.read_text() + "\n")
        result = self.guard_result()
        self.assertEqual(2, result.returncode)
        self.assertIn("stale", result.stderr)

    def test_user_project_settings_are_not_managed_or_required_for_admission(self):
        config = self.repo / ".codex/config.toml"
        config.parent.mkdir()
        original = ('model = "my-choice"\n[features]\nmulti_agent_v2 = true\n'
                    '[agents]\nmax_depth = 7\nmax_concurrent_threads_per_session = 12\n')
        config.write_text(original)
        workflow.git(self.repo, "add", ".codex/config.toml")
        workflow.git(self.repo, "commit", "-m", "User startup settings")
        self.start()
        admitted = self.command_result("admit")
        self.assertEqual(0, admitted.returncode, admitted.stderr)
        self.assertEqual(original, config.read_text())
        config.unlink()
        result = self.guard_result()
        self.assertIn("/missing-plan", result.stderr)
        self.assertNotIn("stale", result.stderr)

    def test_only_the_registered_fresh_coordinator_can_mutate(self):
        self.start()
        self.assertEqual(0, self.command_result("admit").returncode)
        command = self.command + ["coordinator", "PRD.md", "--repo", str(self.repo), "--agent"]
        rejected = subprocess.run(command + ["implementation_coordinator"], env=self.env,
                                  capture_output=True, text=True, timeout=5)
        self.assertEqual(2, rejected.returncode)
        folder = self.home / "sessions" / datetime.datetime.now(datetime.timezone.utc).strftime("%Y/%m/%d")
        folder.mkdir(parents=True)
        for identifier in ("actual-coordinator", "other-coordinator"):
            event = {
                "type": "session_meta", "payload": {
                    "id": identifier, "cwd": str(self.repo),
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "source": {"subagent": {"thread_spawn": {
                        "parent_thread_id": "selected-outer", "agent_role": "implementation_coordinator", "depth": 1,
                    }}},
                },
            }
            (folder / f"rollout-{identifier}.jsonl").write_text(json.dumps(event) + "\n")
        admitted = subprocess.run(command + ["actual-coordinator"], env=self.env,
                                  capture_output=True, text=True, timeout=5)
        self.assertEqual(0, admitted.returncode, admitted.stderr)
        authorized = self.guard_result(dict(self.env, CODEX_THREAD_ID="actual-coordinator"))
        self.assertIn("/missing-plan", authorized.stderr)
        plan = self.root / "coordinator-init.json"
        plan.write_text(json.dumps({"spec": "PRD.md"}))
        rejected_init = subprocess.run(
            [sys.executable, str(self.skill / "scripts/workflow.py"), "init", "PRD.md",
             "--repo", str(self.repo), "--plan", str(plan)],
            env=dict(self.env, CODEX_THREAD_ID="actual-coordinator"),
            capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(2, rejected_init.returncode)
        self.assertIn("Only the admitted outer", rejected_init.stderr)
        self.assertIsNone(workflow.Run(self.repo, "PRD.md").data)
        unauthorized = self.guard_result(dict(self.env, CODEX_THREAD_ID="other-coordinator"))
        self.assertIn("owner", unauthorized.stderr)
        replaced = subprocess.run(command + ["other-coordinator"], env=self.env,
                                  capture_output=True, text=True, timeout=5)
        self.assertEqual(2, replaced.returncode)
        missing_evidence = self.command_result("release-coordinator", {"coordinator": "actual-coordinator"})
        self.assertEqual(2, missing_evidence.returncode)
        wrong_coordinator = self.command_result("release-coordinator", {
            "coordinator": "other-coordinator", "previous_workers_inactive": True,
            "evidence": "All worker threads closed.",
        })
        self.assertEqual(2, wrong_coordinator.returncode)
        released = self.command_result("release-coordinator", {
            "coordinator": "actual-coordinator", "previous_workers_inactive": True,
            "evidence": "The recorded coordinator and every child are confirmed closed.",
        })
        self.assertEqual(0, released.returncode, released.stderr)
        former = self.guard_result(dict(self.env, CODEX_THREAD_ID="actual-coordinator"))
        self.assertIn("owner", former.stderr)
        reused = subprocess.run(command + ["actual-coordinator"], env=self.env,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(2, reused.returncode)
        replacement = subprocess.run(command + ["other-coordinator"], env=self.env,
                                     capture_output=True, text=True, timeout=5)
        self.assertEqual(0, replacement.returncode, replacement.stderr)
        authorized = self.guard_result(dict(self.env, CODEX_THREAD_ID="other-coordinator"))
        self.assertIn("/missing-plan", authorized.stderr)
        entry = json.loads(self.command_result("status").stdout)
        self.assertEqual("actual-coordinator", entry["closed_coordinators"][0]["coordinator"])

    def test_audit_repair_and_continuation_commands_use_the_admitted_outer(self):
        (self.repo / "ticket.md").write_text("Status: ready-for-agent\n")
        workflow.git(self.repo, "add", "ticket.md")
        workflow.git(self.repo, "commit", "-m", "Ticket")
        self.start()
        self.assertEqual(0, self.command_result("admit").returncode)
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "selected-outer"}):
            run = workflow.Run(self.repo, "PRD.md")
            run.create({
                "spec": "PRD.md", "checks": [["suite"]], "requirements": ["US1"],
                "approval_evidence": "Approved documentation",
                "tickets": [{"path": "ticket.md", "execution": "AFK", "criteria": ["AC1"],
                             "kind": "documentation"}],
            })
            for round_number in range(3):
                run.begin("ticket.md")
                record = run.data["tickets"]["ticket.md"]
                run.implemented({
                    "outcome": "READY_FOR_REVIEW", "ticket": "ticket.md", "attempt": record["attempts"],
                    "tdd_not_applicable_reason": "Documentation repair", "checks": ["Links checked"],
                })
                run.reviewed({
                    "verdict": "PASS", "ticket": "ticket.md", "attempt": record["attempts"],
                    "base_commit": record["review_base"], "reviewed_snapshot": run.data["checkpoint"],
                    "criteria": [{"id": "AC1", "satisfied": True, "evidence": "Checked documentation"}],
                    "checks": [{"command": ["suite"], "exit_code": 0, "evidence": "Passed"}],
                    "blocking_findings": [], "unavailable_checks": [],
                    "resolved_findings": [{"id": "A1", "evidence": "Correction checked"}],
                })
                run.commit_ticket()
                run.finish({
                    "verdict": "REWORK", "audited_commit": run.data["head"],
                    "baseline_commit": run.data["baseline"], "reviewed_snapshot": run.data["checkpoint"],
                    "blocking_findings": [{"id": "A1", "evidence": "Integration wording missing"}],
                    "unavailable_checks": [],
                })
                report = {
                    "audit_number": len(run.data["audits"]), "reviewed_snapshot": run.data["checkpoint"],
                    "previous_workers_inactive": True, "evidence": "All review threads closed.",
                    "findings": [{"id": "A1", "classification": "confirmed_blocker",
                                  "reference": "PRD.md#US1", "evidence": "Missing requirement text."}],
                    "tickets": [{"action": "reopen", "path": "ticket.md", "finding_ids": ["A1"],
                                 "requirements": ["US1"]}],
                }
                report_path = self.root / "audit-command.json"
                report_path.write_text(json.dumps(report))
                command = [
                    sys.executable, str(self.skill / "scripts/workflow.py"), "repair-audit", "PRD.md",
                    "--repo", str(self.repo), "--report", str(report_path),
                ]
                result = subprocess.run(command, env=self.env, capture_output=True, text=True, timeout=5)
                if round_number < 2:
                    self.assertEqual(0, result.returncode, result.stderr)
                else:
                    self.assertEqual(2, result.returncode)
                    self.assertIn("exhausted", result.stderr)
                run = workflow.Run(self.repo, "PRD.md")
            report_path.write_text(json.dumps({
                "cycle": 1, "reviewed_snapshot": run.data["checkpoint"],
                "previous_workers_inactive": True, "evidence": "User reviewed the stopped run.",
                "user_authorization": "Continue working on the audit defects.",
            }))
            command[2] = "continue-audit"
            result = subprocess.run(command, env=self.env, capture_output=True, text=True, timeout=5)
            self.assertEqual(0, result.returncode, result.stderr)
            restored = workflow.Run(self.repo, "PRD.md")
            self.assertEqual(2, restored.data["audit_cycles"][-1]["number"])
            self.assertEqual(3, len(restored.data["audits"]))


if __name__ == "__main__":
    unittest.main()
