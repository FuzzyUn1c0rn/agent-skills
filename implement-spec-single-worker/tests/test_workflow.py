import datetime
import json
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import workflow
import smoke_test


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.repo = Path(self.directory.name)
        workflow.git(self.repo, "init", "-b", "main")
        workflow.git(self.repo, "config", "user.name", "Workflow test")
        workflow.git(self.repo, "config", "user.email", "workflow@example.invalid")
        (self.repo / "PRD.md").write_text("Status: ready-for-agent\n")
        (self.repo / "ticket.md").write_text("Status: ready-for-agent\n")
        workflow.git(self.repo, "add", "PRD.md", "ticket.md")
        workflow.git(self.repo, "commit", "-m", "Fixture")

    def test_main_gets_new_branch_at_same_commit(self):
        baseline = workflow.git(self.repo, "rev-parse", "HEAD")
        branch = workflow.choose_branch(self.repo, "PRD.md")
        self.assertTrue(branch.startswith("implement/"))
        self.assertEqual(branch, workflow.git(self.repo, "branch", "--show-current"))
        self.assertEqual(baseline, workflow.git(self.repo, "rev-parse", "HEAD"))

    def test_snapshot_includes_untracked_content_and_modes(self):
        initial = workflow.snapshot(self.repo)
        source = self.repo / "source.py"
        source.write_text("result = 1\n")
        added = workflow.snapshot(self.repo)
        self.assertNotEqual(initial, added)
        source.write_text("result = 2\n")
        changed = workflow.snapshot(self.repo)
        self.assertNotEqual(added, changed)
        source.chmod(0o755)
        self.assertNotEqual(changed, workflow.snapshot(self.repo))

    def test_second_run_is_rejected_while_first_holds_lock(self):
        lock = self.repo / ".git" / "workflow.lock"
        with workflow.exclusive(lock):
            with self.assertRaises(workflow.WorkflowError):
                with workflow.exclusive(lock):
                    self.fail("Second run acquired the occupied checkout")
        with workflow.exclusive(lock):
            pass

    def test_pass_requires_every_criterion_check_and_current_snapshot(self):
        ticket = {"path": "ticket.md", "criteria": ["AC1", "AC2"]}
        report = {
            "verdict": "PASS", "ticket": "ticket.md", "reviewed_snapshot": "current",
            "criteria": [{"id": "AC1", "satisfied": True, "evidence": "observed"}],
            "checks": [{"command": ["suite"], "exit_code": 0, "evidence": "passed"}],
            "blocking_findings": [], "unavailable_checks": [],
        }
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_pass(report, ticket, [["suite"]], "current")

    def new_run(self):
        run = workflow.Run(self.repo, "PRD.md")
        run.create({
            "spec": "PRD.md", "checks": [["suite"]], "approval_evidence": "Confirmed PRD",
            "requirements": ["US1"],
            "tickets": [{"path": "ticket.md", "criteria": ["AC1"], "blocked_by": [],
                         "seams": ["public"], "execution": "AFK", "kind": "behavior"}],
        })
        return run

    def implement_and_review(self, run, verdict):
        attempt = run.data["tickets"]["ticket.md"]["attempts"]
        run.implemented({
            "outcome": "READY_FOR_REVIEW", "ticket": "ticket.md", "attempt": attempt,
            "tdd": [{"boundary": "public",
                     "red": {"command": ["test"], "exit_code": 1, "evidence": "Behavior absent"},
                     "green": {"command": ["test"], "exit_code": 0, "evidence": "Behavior present"}}],
        })
        run.reviewed({
            "verdict": verdict, "ticket": "ticket.md", "attempt": attempt,
            "base_commit": run.data["head"], "reviewed_snapshot": run.data["checkpoint"],
            "criteria": [{"id": "AC1", "satisfied": True, "evidence": "Observed behavior"}],
            "checks": [{"command": ["suite"], "exit_code": 0, "evidence": "Suite passed"}],
            "blocking_findings": [] if verdict == "PASS" else [{"id": "F1", "evidence": "Missing behavior"}],
            "unavailable_checks": [],
        })

    def test_attempt_limit_survives_reload(self):
        run = self.new_run()
        for attempt in range(3):
            run.begin("ticket.md")
            self.implement_and_review(run, "REWORK")
            run = workflow.Run(self.repo, "PRD.md")
        with self.assertRaises(workflow.WorkflowError):
            run.begin("ticket.md")

    def test_commit_closes_ticket_with_code_and_preserves_prd_until_audit(self):
        run = self.new_run()
        run.begin("ticket.md")
        (self.repo / "source.py").write_text("result = 42\n")
        self.implement_and_review(run, "PASS")
        commit = run.commit_ticket()
        self.assertEqual("closed", workflow.status_text(self.repo / "ticket.md"))
        self.assertEqual("Status: ready-for-agent\n", (self.repo / "PRD.md").read_text())
        self.assertEqual("result = 42", workflow.git(self.repo, "show", f"{commit}:source.py"))
        self.assertIn("Status: closed", workflow.git(self.repo, "show", f"{commit}:ticket.md"))
        self.assertEqual(commit, workflow.Run(self.repo, "PRD.md").data["tickets"]["ticket.md"]["commit"])

    def test_code_change_after_pass_prevents_commit(self):
        run = self.new_run()
        run.begin("ticket.md")
        source = self.repo / "source.py"
        source.write_text("result = 42\n")
        self.implement_and_review(run, "PASS")
        source.write_text("result = 99\n")
        with self.assertRaises(workflow.WorkflowError):
            run.commit_ticket()
        self.assertEqual("ready-for-agent", workflow.status_text(self.repo / "ticket.md"))

    def test_blocking_audit_is_committed_without_finishing_prd(self):
        run = self.new_run()
        run.begin("ticket.md")
        self.implement_and_review(run, "PASS")
        run.commit_ticket()
        run.finish({
            "verdict": "BLOCKED", "audited_commit": run.data["head"],
            "baseline_commit": run.data["baseline"], "reviewed_snapshot": run.data["checkpoint"],
            "blocking_findings": [{"id": "F1", "evidence": "Cross-ticket behavior missing"}],
            "unavailable_checks": [],
        })
        self.assertEqual("ready-for-agent", workflow.status_text(self.repo / "PRD.md"))
        self.assertEqual("closed", workflow.status_text(self.repo / "ticket.md"))
        self.assertEqual("", workflow.git(self.repo, "status", "--porcelain"))
        self.assertEqual("audit-blocked", workflow.Run(self.repo, "PRD.md").data["phase"])

    def test_explicit_branch_overrides_main_rule_and_reuses_existing(self):
        workflow.choose_branch(self.repo, "PRD.md", "feature/chosen")
        self.assertEqual("feature/chosen", workflow.git(self.repo, "branch", "--show-current"))
        workflow.git(self.repo, "switch", "main")
        self.assertEqual("feature/chosen", workflow.choose_branch(self.repo, "PRD.md", "feature/chosen"))

    def test_dirty_checkout_is_preserved(self):
        (self.repo / "draft.txt").write_text("Human work")
        with self.assertRaises(workflow.WorkflowError):
            workflow.choose_branch(self.repo, "PRD.md", "feature/new")
        self.assertEqual("main", workflow.git(self.repo, "branch", "--show-current"))
        self.assertEqual("Human work", (self.repo / "draft.txt").read_text())

    def test_existing_feature_branch_is_reused(self):
        workflow.git(self.repo, "switch", "-c", "feature/existing")
        self.assertEqual("feature/existing", workflow.choose_branch(self.repo, "PRD.md"))

    def test_dependency_cycle_is_rejected_before_run_record(self):
        run = workflow.Run(self.repo, "PRD.md")
        with self.assertRaises(workflow.WorkflowError):
            run.create({
                "spec": "PRD.md", "checks": [["suite"]], "requirements": ["US1"],
                "approval_evidence": "PRD",
                "tickets": [{"path": "ticket.md", "execution": "AFK", "criteria": ["AC1"],
                             "seams": ["public"], "blocked_by": ["ticket.md"]}],
            })
        self.assertFalse((self.repo / "implementation-run.json").exists())

    def test_failed_commit_does_not_close_ticket(self):
        run = self.new_run()
        run.begin("ticket.md")
        self.implement_and_review(run, "PASS")
        hook = self.repo / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        with self.assertRaises(workflow.WorkflowError):
            run.commit_ticket()
        self.assertEqual("ready-for-agent", workflow.status_text(self.repo / "ticket.md"))
        self.assertIsNone(workflow.Run(self.repo, "PRD.md").data["tickets"]["ticket.md"]["commit"])

    def test_complete_audit_finishes_prd_in_clean_commit(self):
        run = self.new_run()
        run.begin("ticket.md")
        self.implement_and_review(run, "PASS")
        run.commit_ticket()
        run.finish({
            "verdict": "PASS", "audited_commit": run.data["head"],
            "baseline_commit": run.data["baseline"], "reviewed_snapshot": run.data["checkpoint"],
            "requirements": [{"id": "US1", "satisfied": True, "evidence": "Verified complete behavior"}],
            "checks": [{"command": ["suite"], "exit_code": 0, "evidence": "Complete passing suite"}],
            "blocking_findings": [], "unavailable_checks": [],
        })
        self.assertEqual("done", workflow.status_text(self.repo / "PRD.md"))
        self.assertEqual("", workflow.git(self.repo, "status", "--porcelain"))

    def completed_run(self):
        run = self.new_run()
        run.begin("ticket.md")
        (self.repo / "source.py").write_text("result = 42\n")
        self.implement_and_review(run, "PASS")
        run.commit_ticket()
        return run

    def audit_report(self, run):
        return {
            "verdict": "PASS", "audited_commit": run.data["head"],
            "baseline_commit": run.data["baseline"], "reviewed_snapshot": run.data["checkpoint"],
            "requirements": [{"id": "US1", "satisfied": True, "evidence": "Verified behavior"}],
            "checks": [{"command": ["suite"], "exit_code": 0, "evidence": "Passing suite"}],
            "blocking_findings": [], "unavailable_checks": [],
        }

    def test_hidden_staged_source_prevents_finalization(self):
        run = self.completed_run()
        report = self.audit_report(run)
        source = self.repo / "source.py"
        source.write_text("result = 99\n")
        workflow.git(self.repo, "add", "source.py")
        source.write_text("result = 42\n")
        with self.assertRaises(workflow.WorkflowError):
            run.finish(report)
        self.assertEqual("ready-for-agent", workflow.status_text(self.repo / "PRD.md"))
        self.assertEqual("result = 42", workflow.git(self.repo, "show", "HEAD:source.py"))

    def test_audit_hook_source_edit_prevents_completion(self):
        run = self.completed_run()
        hook = self.repo / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nprintf 'result = 99\\n' > source.py\n")
        hook.chmod(0o755)
        with self.assertRaises(workflow.WorkflowError):
            run.finish(self.audit_report(run))
        self.assertNotEqual("done", workflow.Run(self.repo, "PRD.md").data["phase"])
        self.assertEqual("ready-for-agent", workflow.status_text(self.repo / "PRD.md"))

    def test_rejected_final_commit_can_be_retried(self):
        run = self.completed_run()
        hook = self.repo / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        with self.assertRaises(workflow.WorkflowError):
            run.finish(self.audit_report(run))
        hook.unlink()
        recovered = workflow.Run(self.repo, "PRD.md")
        recovered.reconcile_commit()
        self.assertEqual("done", recovered.data["phase"])
        self.assertEqual("done", workflow.status_text(self.repo / "PRD.md"))
        self.assertEqual("", workflow.git(self.repo, "status", "--porcelain"))

    def test_interruption_before_ticket_commit_can_be_retried(self):
        run = self.new_run()
        run.begin("ticket.md")
        self.implement_and_review(run, "PASS")
        original_git = workflow.git
        def interrupted(repo, *arguments):
            if arguments[0] == "commit":
                raise KeyboardInterrupt()
            return original_git(repo, *arguments)
        with patch.object(workflow, "git", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                run.commit_ticket()
        recovered = workflow.Run(self.repo, "PRD.md")
        recovered.reconcile_commit()
        self.assertEqual("ready", recovered.data["phase"])
        self.assertEqual("closed", workflow.status_text(self.repo / "ticket.md"))

    def test_interruption_after_final_commit_reconciles(self):
        run = self.completed_run()
        report = self.audit_report(run)
        original_git = workflow.git
        def interrupted(repo, *arguments):
            result = original_git(repo, *arguments)
            if arguments[0] == "commit":
                raise KeyboardInterrupt()
            return result
        with patch.object(workflow, "git", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                run.finish(report)
        recovered = workflow.Run(self.repo, "PRD.md")
        recovered.reconcile_commit()
        self.assertEqual("done", recovered.data["phase"])
        self.assertEqual("", workflow.git(self.repo, "status", "--porcelain"))

    def test_old_implementation_evidence_cannot_resolve_new_attempt(self):
        run = self.new_run()
        run.begin("ticket.md")
        self.implement_and_review(run, "REWORK")
        run.begin("ticket.md")
        run.implemented({"outcome": "BLOCKED", "ticket": "ticket.md", "attempt": 2})
        with self.assertRaises(workflow.WorkflowError):
            run.resolve({"evidence": "Access restored", "previous_workers_inactive": True,
                         "next_phase": "reviewing"})

    def test_fresh_repair_preserves_prior_agent_tdd_and_findings(self):
        run = self.new_run()
        run.begin("ticket.md")
        run.checkpoint("first-agent")
        self.implement_and_review(run, "REWORK")
        run = workflow.Run(self.repo, "PRD.md")
        run.begin("ticket.md")
        run.checkpoint("repair-agent")
        history = run.data["tickets"]["ticket.md"]["history"]
        self.assertEqual(2, len(history))
        self.assertEqual("first-agent", history[0]["implementer"])
        self.assertEqual("Behavior absent", history[0]["implementation"]["tdd"][0]["red"]["evidence"])
        self.assertEqual("F1", history[0]["reviews"][0]["blocking_findings"][0]["id"])
        self.assertEqual("repair-agent", history[1]["implementer"])
        self.assertIsNone(run.data["implementation"])

    def test_repair_cannot_reuse_a_previous_agent_id(self):
        run = self.new_run()
        run.begin("ticket.md")
        run.checkpoint("first-agent")
        self.implement_and_review(run, "REWORK")
        run.begin("ticket.md")
        with self.assertRaises(workflow.WorkflowError):
            run.checkpoint("first-agent")

    def smoke_records(self):
        records = [
            {"id": role, "role": role, "models": [[model, effort]], "depth": depth,
             "parent": None if role == "outer" else "outer" if depth == 1 else "implementation_coordinator",
             "limit_rejections": 1 if role == "implementation_coordinator" else 0,
             "markers": [f"{role.split('_')[-1].upper()}_PROFILE_OK"], "operations": []}
            for role, (model, effort, depth) in smoke_test.EXPECTED.items()
        ]
        for role in ("ticket_implementer", "ticket_verifier"):
            original = next(record for record in records if record["role"] == role)
            records.append({**original, "id": role + "_repair", "operations": []})
        outer = next(record for record in records if record["role"] == "outer")
        coordinator = next(record for record in records if record["role"] == "implementation_coordinator")
        for owner, children in (
            (outer, ["implementation_coordinator", "spec_auditor"]),
            (coordinator, ["ticket_implementer", "ticket_verifier",
                           "ticket_implementer_repair", "ticket_verifier_repair"]),
        ):
            for child in children:
                role = next(record["role"] for record in records if record["id"] == child)
                owner["operations"].append(
                    {"name": "spawn_agent", "spawned": child, "role": role, "succeeded": True})
                if child == "ticket_implementer":
                    owner["operations"].append(
                        {"name": "spawn_agent", "role": role, "succeeded": False, "limit_rejected": True})
                owner["operations"].extend([
                    {"name": "wait_agent", "completed": [child], "succeeded": True},
                    {"name": "close_agent", "target": child, "succeeded": True},
                ])
        return records

    def test_native_smoke_accepts_sequential_fresh_repairs(self):
        self.assertTrue(all(smoke_test.validate_records(self.smoke_records()).values()))

    def test_native_smoke_rejects_repair_before_previous_worker_closes(self):
        records = self.smoke_records()
        coordinator = next(record for record in records if record["role"] == "implementation_coordinator")
        closure = coordinator["operations"].pop(3)
        coordinator["operations"].append(closure)
        self.assertFalse(smoke_test.validate_records(records)["repair_lifecycle"])

    def test_native_smoke_rejects_repair_model_drift(self):
        records = self.smoke_records()
        repair = next(record for record in records if record["id"] == "ticket_implementer_repair")
        repair["models"] = [["openai.gpt-6-luna", "medium"]]
        self.assertFalse(smoke_test.validate_records(records)["effective_models"])

    def test_native_smoke_rejects_auditor_closed_before_completion(self):
        records = self.smoke_records()
        outer = next(record for record in records if record["role"] == "outer")
        outer["operations"] = [
            operation for operation in outer["operations"]
            if "spec_auditor" not in operation.get("completed", [])
        ]
        self.assertFalse(smoke_test.validate_records(records)["workers_completed"])

    def test_smoke_does_not_accept_commentary_markers(self):
        home = self.repo / "codex"
        folder = home / "sessions" / datetime.datetime.now(datetime.timezone.utc).strftime("%Y/%m/%d")
        folder.mkdir(parents=True)
        events = [
            {"type": "session_meta", "payload": {"id": "outer", "cwd": str(self.repo)}},
            {"type": "response_item", "payload": {
                "type": "message", "role": "assistant", "phase": "commentary",
                "content": [{"type": "output_text", "text": "I will return AUDITOR_PROFILE_OK later"}],
            }},
        ]
        (folder / "session.jsonl").write_text("\n".join(json.dumps(event) for event in events) + "\n")
        with patch.dict("os.environ", {"CODEX_HOME": str(home)}):
            records = smoke_test.metadata("outer", self.repo, time.time() - 1)
        self.assertEqual([], records[0]["markers"])

    def test_model_metadata_alone_cannot_pass_smoke(self):
        records = [
            {"id": role, "role": role, "models": [[model, effort]], "depth": depth,
             "limit_rejections": 1 if role == "implementation_coordinator" else 0,
             "markers": [], "operations": []}
            for role, (model, effort, depth) in smoke_test.EXPECTED.items()
        ]
        checks = smoke_test.validate_records(records)
        self.assertTrue(checks["effective_models"])
        self.assertFalse(checks["workers_completed"])
        self.assertFalse(checks["repair_lifecycle"])
        self.assertFalse(checks["children_closed"])

    def test_interruption_after_status_write_is_recoverable(self):
        run = self.new_run()
        run.begin("ticket.md")
        self.implement_and_review(run, "PASS")
        original = workflow.set_status
        def interrupted(path, label):
            original(path, label)
            if label == "closed":
                raise KeyboardInterrupt()
        with patch.object(workflow, "set_status", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                run.commit_ticket()
        recovered = workflow.Run(self.repo, "PRD.md")
        recovered.reconcile_commit()
        self.assertEqual("ready", recovered.data["phase"])
        self.assertEqual("closed", workflow.status_text(self.repo / "ticket.md"))

    def test_interruption_after_audit_write_is_recoverable(self):
        run = self.completed_run()
        report = self.audit_report(run)
        original = Path.write_text
        def interrupted(path, *arguments, **keywords):
            result = original(path, *arguments, **keywords)
            if path.name == "final-audit.md":
                raise KeyboardInterrupt()
            return result
        with patch.object(Path, "write_text", new=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                run.finish(report)
        recovered = workflow.Run(self.repo, "PRD.md")
        recovered.reconcile_commit()
        self.assertEqual("done", recovered.data["phase"])

    def test_deletion_commit_can_retry_after_rejecting_hook(self):
        source = self.repo / "retired.py"
        source.write_text("old = True\n")
        workflow.git(self.repo, "add", "retired.py")
        workflow.git(self.repo, "commit", "-m", "Existing source")
        run = self.new_run()
        run.begin("ticket.md")
        source.unlink()
        self.implement_and_review(run, "PASS")
        hook = self.repo / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        with self.assertRaises(workflow.WorkflowError):
            run.commit_ticket()
        hook.unlink()
        recovered = workflow.Run(self.repo, "PRD.md")
        recovered.reconcile_commit()
        self.assertEqual("ready", recovered.data["phase"])
        self.assertEqual("", workflow.git(self.repo, "ls-files", "retired.py"))

    def test_formatting_hook_requires_fresh_review_without_resetting_attempts(self):
        run = self.new_run()
        run.begin("ticket.md")
        (self.repo / "source.py").write_text("result=42\n")
        self.implement_and_review(run, "PASS")
        hook = self.repo / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nprintf 'result = 42\\n' > source.py\nexit 1\n")
        hook.chmod(0o755)
        with self.assertRaises(workflow.WorkflowError):
            run.commit_ticket()
        recovered = workflow.Run(self.repo, "PRD.md")
        with self.assertRaises(workflow.WorkflowError):
            recovered.reconcile_commit()
        recovered.invalidate({"evidence": "Formatter changed source", "previous_workers_inactive": True})
        self.assertEqual("reviewing", recovered.data["phase"])
        self.assertEqual(1, recovered.data["tickets"]["ticket.md"]["attempts"])
        self.assertIsNone(recovered.data["review"])

    def test_successful_formatting_hook_requires_full_diff_reverification(self):
        run = self.new_run()
        run.begin("ticket.md")
        baseline = run.data["head"]
        (self.repo / "source.py").write_text("result=42\n")
        self.implement_and_review(run, "PASS")
        hook = self.repo / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nprintf 'result = 42\\n' > source.py\ngit add source.py\n")
        hook.chmod(0o755)
        with self.assertRaises(workflow.WorkflowError):
            run.commit_ticket()
        committed = workflow.git(self.repo, "rev-parse", "HEAD")
        self.assertNotEqual(baseline, committed)
        self.assertEqual("ready-for-agent", workflow.status_text(self.repo / "ticket.md"))
        recovered = workflow.Run(self.repo, "PRD.md")
        recovered.invalidate({"evidence": "Successful formatter changed reviewed tree",
                              "previous_workers_inactive": True})
        self.assertEqual(committed, recovered.data["head"])
        self.assertEqual(baseline, recovered.data["tickets"]["ticket.md"]["review_base"])
        self.assertEqual([committed], recovered.data["tickets"]["ticket.md"]["unverified_commits"])
        report = dict(recovered.data["tickets"]["ticket.md"]["history"][0]["reviews"][0],
                      base_commit=baseline, reviewed_snapshot=recovered.data["checkpoint"])
        recovered.reviewed(report)
        final_commit = recovered.commit_ticket()
        self.assertEqual(committed, workflow.git(self.repo, "rev-parse", final_commit + "^"))
        self.assertEqual("ready", recovered.data["phase"])
        self.assertEqual(1, recovered.data["tickets"]["ticket.md"]["attempts"])

    def test_resumed_worker_needs_a_second_closure(self):
        records = [
            {"id": role, "role": role, "models": [[model, effort]], "depth": depth,
             "limit_rejections": 0, "markers": [], "operations": []}
            for role, (model, effort, depth) in smoke_test.EXPECTED.items()
        ]
        coordinator = next(record for record in records if record["role"] == "implementation_coordinator")
        coordinator["operations"] = [
            {"name": "close_agent", "target": "ticket_implementer", "succeeded": True},
            {"name": "resume_agent", "target": "ticket_implementer", "succeeded": True},
        ]
        self.assertFalse(smoke_test.validate_records(records)["children_closed"])


if __name__ == "__main__":
    unittest.main()
