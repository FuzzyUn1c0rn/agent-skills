import copy
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_workflow as fixtures

workflow = fixtures.workflow


class AuditRepairTests(unittest.TestCase):
    setUp = fixtures.WorkflowTests.setUp
    new_run = fixtures.WorkflowTests.new_run
    completed_run = fixtures.WorkflowTests.completed_run
    audit_report = fixtures.WorkflowTests.audit_report

    def implement_and_review(self, run, verdict, finding_id="F1", ticket="ticket.md"):
        record = run.data["tickets"][ticket]
        run.implemented({
            "outcome": "READY_FOR_REVIEW", "ticket": ticket, "attempt": record["attempts"],
            "tdd": [{"boundary": "public",
                     "red": {"command": ["test"], "exit_code": 1, "evidence": "Behavior absent"},
                     "green": {"command": ["test"], "exit_code": 0, "evidence": "Behavior present"}}],
        })
        report = {
            "verdict": verdict, "ticket": ticket, "attempt": record["attempts"],
            "base_commit": record["review_base"], "reviewed_snapshot": run.data["checkpoint"],
            "criteria": [{"id": criterion, "satisfied": True, "evidence": "Observed behavior"}
                         for criterion in run.ticket()["criteria"]],
            "checks": [{"command": ["suite"], "exit_code": 0, "evidence": "Suite passed"}],
            "blocking_findings": [] if verdict == "PASS" else [{"id": finding_id, "evidence": "Defect"}],
            "resolved_findings": [{"id": identifier, "evidence": "Regression test passes"}
                                  for identifier in record.get("audit_findings", [])],
            "unavailable_checks": [],
        }
        run.reviewed(report)
        return report

    def failed_audit(self, run, identifiers=("A1",)):
        report = dict(self.audit_report(run), verdict="REWORK", blocking_findings=[
            {"id": identifier, "evidence": "The integration violates US1", "reference": "PRD.md#US1"}
            for identifier in identifiers
        ])
        run.finish(report)
        return report

    def repair_plan(self, run, create=False):
        path = "repairs/integration.md" if create else "ticket.md"
        ticket = {
            "path": path, "action": "create" if create else "reopen",
            "finding_ids": ["A1"], "requirements": ["US1"],
        }
        if create:
            ticket.update(
                execution="AFK", criteria=["REPAIR1"], seams=["public"], blocked_by=["ticket.md"],
                related_tickets=["ticket.md"],
                content="# Repair integration\n\nStatus: ready-for-agent\nExecution: AFK\n\n"
                        "REPAIR1: Correct the integration required by US1.\n",
            )
        return {
            "audit_number": len(run.data["audits"]),
            "reviewed_snapshot": run.data["checkpoint"],
            "previous_workers_inactive": True, "evidence": "Auditor and coordinator are closed.",
            "findings": [{"id": "A1", "classification": "confirmed_blocker",
                          "reference": "PRD.md#US1", "evidence": "Reproduced the missing behavior."}],
            "tickets": [ticket],
        }

    def continuation(self, run):
        return {
            "cycle": run.data["audit_cycles"][-1]["number"],
            "reviewed_snapshot": run.data["checkpoint"], "previous_workers_inactive": True,
            "evidence": "Reviewed the stopped run and confirmed all workers closed.",
            "user_authorization": "User: continue working on the remaining audit defects.",
        }

    def repair_and_audit(self, run):
        run.repair_audit(self.repair_plan(run))
        run.begin("ticket.md")
        self.implement_and_review(run, "PASS")
        run.commit_ticket()
        self.failed_audit(run)
        return workflow.Run(self.repo, "PRD.md")

    def test_reopen_preserves_original_work_and_requires_new_independent_pass(self):
        run = self.completed_run()
        original_commit = run.data["tickets"]["ticket.md"]["commit"]
        original_history = copy.deepcopy(run.data["tickets"]["ticket.md"]["history"])
        baseline = run.data["baseline"]
        self.failed_audit(run)
        original_audit = (self.repo / "final-audit.md").read_bytes()
        run.repair_audit(self.repair_plan(run))
        self.assertEqual("ready-for-agent", workflow.status_text(self.repo / "ticket.md"))
        self.assertEqual("", workflow.git(self.repo, "status", "--porcelain"))
        self.assertEqual(original_history, run.data["tickets"]["ticket.md"]["history"])
        self.assertEqual(original_commit, run.data["tickets"]["ticket.md"]["completions"][0]["commit"])
        self.assertIsNone(run.data["tickets"]["ticket.md"]["commit"])
        with self.assertRaises(workflow.WorkflowError):
            run.finish(self.audit_report(run))
        run.begin("ticket.md")
        self.assertEqual(2, run.data["tickets"]["ticket.md"]["attempts"])
        self.implement_and_review(run, "PASS")
        run.commit_ticket()
        run.finish(self.audit_report(run))
        self.assertEqual("done", run.data["phase"])
        self.assertEqual("done", workflow.status_text(self.repo / "PRD.md"))
        self.assertEqual(original_audit, (self.repo / "final-audit.md").read_bytes())
        self.assertTrue((self.repo / "final-audit-002.md").exists())
        self.assertEqual(baseline, run.data["baseline"])
        self.assertEqual(2, len(run.data["audits"]))
        self.assertEqual("", workflow.git(self.repo, "status", "--porcelain"))

    def test_create_linked_repair_ticket_keeps_original_closed(self):
        run = self.completed_run()
        self.failed_audit(run)
        run.repair_audit(self.repair_plan(run, create=True))
        self.assertEqual("closed", workflow.status_text(self.repo / "ticket.md"))
        repair = self.repo / "repairs/integration.md"
        self.assertEqual("ready-for-agent", workflow.status_text(repair))
        self.assertIn("A1", repair.read_text())
        self.assertIn("final-audit.md", repair.read_text())
        run.begin("repairs/integration.md")
        self.implement_and_review(run, "PASS", ticket="repairs/integration.md")
        run.commit_ticket()
        run.finish(self.audit_report(run))
        self.assertEqual("done", run.data["phase"])

    def test_two_rounds_stop_and_explicit_continuation_preserves_history(self):
        run = self.completed_run()
        self.failed_audit(run)
        run = self.repair_and_audit(run)
        run = self.repair_and_audit(run)
        history = copy.deepcopy(run.data["audit_cycles"])
        audits = copy.deepcopy(run.data["audits"])
        self.assertEqual("audit_rounds", run.data["budget_exhausted"])
        with self.assertRaises(workflow.WorkflowError):
            run.repair_audit(self.repair_plan(run))
        missing = self.continuation(run)
        missing.pop("user_authorization")
        with self.assertRaises(workflow.WorkflowError):
            run.continue_audit(missing)
        report = self.continuation(run)
        run.continue_audit(report)
        with self.assertRaises(workflow.WorkflowError):
            run.continue_audit(report)
        self.assertEqual(history, run.data["audit_cycles"][:-1])
        self.assertEqual(audits, run.data["audits"])
        self.assertEqual(2, run.data["audit_cycles"][-1]["number"])
        self.assertEqual([], run.data["audit_cycles"][-1]["rounds"])
        run.repair_audit(self.repair_plan(run))
        run.begin("ticket.md")
        self.implement_and_review(run, "PASS")
        run.commit_ticket()
        run.finish(self.audit_report(run))
        self.assertEqual("done", run.data["phase"])
        self.assertEqual(4, run.data["tickets"]["ticket.md"]["attempts"])

    def test_unfinished_ticket_budget_can_be_renewed_without_losing_dirty_work(self):
        run = self.completed_run()
        self.failed_audit(run)
        run.repair_audit(self.repair_plan(run))
        for attempt in range(3):
            run.begin("ticket.md")
            (self.repo / "source.py").write_text(f"unfinished = {attempt}\n")
            self.implement_and_review(run, "REWORK", finding_id=f"F{attempt}")
        with self.assertRaises(workflow.WorkflowError):
            run.begin("ticket.md")
        original_history = copy.deepcopy(run.data["tickets"]["ticket.md"]["history"])
        review_base = run.data["tickets"]["ticket.md"]["review_base"]
        run.continue_audit(self.continuation(run))
        self.assertEqual("unfinished = 2\n", (self.repo / "source.py").read_text())
        self.assertEqual(original_history, run.data["tickets"]["ticket.md"]["history"])
        self.assertEqual(review_base, run.data["tickets"]["ticket.md"]["review_base"])
        self.assertEqual(1, len(run.data["audit_cycles"][-1]["rounds"]))
        run.begin("ticket.md")
        self.implement_and_review(run, "PASS")
        run.commit_ticket()
        run.finish(self.audit_report(run))
        self.assertEqual("done", run.data["phase"])

    def test_exhausted_blocked_attempt_can_continue_after_its_obstacle_is_resolved(self):
        run = self.completed_run()
        self.failed_audit(run)
        run.repair_audit(self.repair_plan(run))
        for attempt in range(2):
            run.begin("ticket.md")
            self.implement_and_review(run, "REWORK", finding_id=f"F{attempt}")
        run.begin("ticket.md")
        run.implemented({
            "outcome": "BLOCKED", "ticket": "ticket.md",
            "attempt": run.data["tickets"]["ticket.md"]["attempts"],
            "blockers": ["Required local test dependency is unavailable."],
        })
        recovered = workflow.Run(self.repo, "PRD.md")
        report = self.continuation(recovered)
        with self.assertRaisesRegex(workflow.WorkflowError, "blocker"):
            recovered.continue_audit(report)
        report["blocker_resolution"] = "The required dependency is restored; the local test command now runs."
        recovered.continue_audit(report)
        recovered.begin("ticket.md")
        self.implement_and_review(recovered, "PASS")
        recovered.commit_ticket()
        recovered.finish(self.audit_report(recovered))
        self.assertEqual("done", recovered.data["phase"])

    def test_three_rework_results_stop_without_a_fourth_begin_and_legacy_state_can_continue(self):
        run = self.completed_run()
        self.failed_audit(run)
        run.repair_audit(self.repair_plan(run))
        for attempt in range(3):
            run.begin("ticket.md")
            self.implement_and_review(run, "REWORK", finding_id=f"F{attempt}")
            if attempt == 0:
                with self.assertRaises(workflow.WorkflowError):
                    run.continue_audit(self.continuation(run))
        self.assertEqual("blocked", run.data["phase"])
        self.assertEqual("ticket_attempts", run.data["budget_exhausted"])
        run.data["phase"] = "rework"
        run.data.pop("budget_exhausted")
        run.save()
        restored = workflow.Run(self.repo, "PRD.md")
        restored.continue_audit(self.continuation(restored))
        restored.begin("ticket.md")
        self.assertEqual(5, restored.data["tickets"]["ticket.md"]["attempts"])

    def test_new_session_initialization_belongs_to_the_native_outer(self):
        child_source = {"subagent": {"thread_spawn": {
            "parent_thread_id": "outer", "agent_role": "implementation_coordinator", "depth": 1,
        }}}
        with patch.dict(os.environ, {"IMPLEMENT_SPEC_LAUNCH": "1", "CODEX_THREAD_ID": "coordinator"}), \
                patch.object(workflow, "session_metadata", return_value={"source": child_source}):
            with self.assertRaisesRegex(workflow.WorkflowError, "outer"):
                self.new_run()
        self.assertIsNone(workflow.Run(self.repo, "PRD.md").data)
        with patch.dict(os.environ, {"IMPLEMENT_SPEC_LAUNCH": "1", "CODEX_THREAD_ID": "outer"}), \
                patch.object(workflow, "session_metadata", return_value={"source": "cli"}):
            run = self.new_run()
        self.assertEqual("outer", run.data["outer_session"])

    def test_prior_audits_cannot_be_edited_or_deleted_by_repair_workers(self):
        run = self.completed_run()
        self.failed_audit(run)
        run.repair_audit(self.repair_plan(run))
        run.begin("ticket.md")
        path = self.repo / "final-audit.md"
        original = path.read_bytes()
        for mutation in ("edit", "delete"):
            with self.subTest(mutation=mutation):
                if mutation == "edit":
                    path.write_text("All previous findings erased.\n")
                else:
                    path.unlink()
                with self.assertRaisesRegex(workflow.WorkflowError, "Historical audit"):
                    self.implement_and_review(run, "PASS")
                self.assertEqual("implementing", run.data["phase"])
                path.write_bytes(original)
        self.implement_and_review(run, "PASS")
        run.commit_ticket()
        self.assertEqual(original, path.read_bytes())

    def test_successful_reverification_clears_stop_marker_without_resetting_attempts(self):
        run = self.completed_run()
        self.failed_audit(run)
        run.repair_audit(self.repair_plan(run))
        for attempt in range(3):
            run.begin("ticket.md")
            report = self.implement_and_review(run, "REWORK", finding_id=f"F{attempt}")
        with self.assertRaises(workflow.WorkflowError):
            run.begin("ticket.md")
        run.resolve({
            "evidence": "User resolved the last review dispute using the existing requirements.",
            "previous_workers_inactive": True, "next_phase": "reviewing",
            "user_authorization": "Reverify the existing implementation.",
        })
        run.reviewed(dict(report, verdict="PASS", blocking_findings=[]))
        run.commit_ticket()
        self.assertNotIn("budget_exhausted", run.data)
        self.assertEqual(3, run.data["audit_cycles"][-1]["finding_attempts"]["A1"])

    def test_new_ticket_cannot_reset_same_finding_budget(self):
        run = self.completed_run()
        self.failed_audit(run)
        run.repair_audit(self.repair_plan(run))
        for attempt in range(3):
            run.begin("ticket.md")
            self.implement_and_review(run, "PASS" if attempt == 2 else "REWORK", finding_id=f"F{attempt}")
        run.commit_ticket()
        self.failed_audit(run)
        with self.assertRaisesRegex(workflow.WorkflowError, "attempt"):
            run.repair_audit(self.repair_plan(run, create=True))
        self.assertFalse((self.repo / "repairs/integration.md").exists())
        run = workflow.Run(self.repo, "PRD.md")
        run.continue_audit(self.continuation(run))
        run.repair_audit(self.repair_plan(run, create=True))
        run.begin("repairs/integration.md")

    def test_repair_pass_requires_evidence_for_every_assigned_finding(self):
        run = self.completed_run()
        self.failed_audit(run)
        run.repair_audit(self.repair_plan(run))
        run.begin("ticket.md")
        self.implement_and_review(run, "REWORK")
        report = dict(run.data["review"], verdict="PASS", blocking_findings=[])
        run.data["phase"] = "reviewing"
        run.save()
        report["reviewed_snapshot"] = run.data["checkpoint"]
        report.pop("resolved_findings")
        with self.assertRaisesRegex(workflow.WorkflowError, "finding"):
            run.reviewed(report)

    def test_repair_plan_rejects_missing_findings_unknown_requirements_and_cycles(self):
        run = self.completed_run()
        self.failed_audit(run)
        for change in ("findings", "scope", "dependency"):
            with self.subTest(change=change):
                report = self.repair_plan(run, create=True)
                if change == "findings":
                    report["findings"] = []
                elif change == "scope":
                    report["tickets"][0]["requirements"] = ["UNAPPROVED"]
                else:
                    report["tickets"][0]["blocked_by"] = ["repairs/integration.md"]
                before = copy.deepcopy(run.data)
                with self.assertRaises(workflow.WorkflowError):
                    run.repair_audit(report)
                self.assertEqual(before, run.data)
                self.assertFalse((self.repo / "repairs/integration.md").exists())

    def test_outer_only_and_stale_snapshot_guards_apply_to_repair_planning(self):
        run = self.completed_run()
        self.failed_audit(run)
        run.data["outer_session"] = "outer"
        run.save()
        report = self.repair_plan(run)
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "coordinator"}):
            with self.assertRaisesRegex(workflow.WorkflowError, "outer"):
                run.repair_audit(report)
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "outer"}):
            (self.repo / "unexpected.py").write_text("changed = True\n")
            with self.assertRaises(workflow.WorkflowError):
                run.repair_audit(report)
        self.assertEqual("closed", workflow.status_text(self.repo / "ticket.md"))

    def test_human_decisions_and_unavailable_checks_cannot_be_waived_by_repair(self):
        run = self.completed_run()
        self.failed_audit(run)
        report = self.repair_plan(run)
        report["findings"][0]["classification"] = "needs_human"
        with self.assertRaises(workflow.WorkflowError):
            run.repair_audit(report)
        report = self.repair_plan(run)
        run.data["audit"]["unavailable_checks"] = ["Required suite unavailable"]
        run.data["audits"][-1]["report"]["unavailable_checks"] = ["Required suite unavailable"]
        run.save()
        with self.assertRaises(workflow.WorkflowError):
            run.repair_audit(report)

    def test_advisory_reclassification_requires_fresh_audit_and_consumes_round(self):
        run = self.completed_run()
        self.failed_audit(run)
        report = self.repair_plan(run)
        report["findings"][0]["classification"] = "advisory"
        report["tickets"] = []
        run.repair_audit(report)
        self.assertEqual("ready", run.data["phase"])
        self.assertEqual("ready-for-agent", workflow.status_text(self.repo / "PRD.md"))
        self.assertEqual(1, len(run.data["audit_cycles"][-1]["rounds"]))
        run.finish(self.audit_report(run))
        self.assertEqual("done", run.data["phase"])

    def test_legacy_failed_audit_can_enter_repair_without_overwriting_report(self):
        run = self.completed_run()
        self.failed_audit(run)
        original = (self.repo / "final-audit.md").read_bytes()
        run.data.pop("audits")
        run.data.pop("audit_cycles")
        run.data["version"] = 1
        run.save()
        restored = workflow.Run(self.repo, "PRD.md")
        restored.repair_audit(self.repair_plan(restored))
        self.assertEqual(original, (self.repo / "final-audit.md").read_bytes())
        self.assertEqual("ready", restored.data["phase"])

    def test_repair_plan_commit_recovers_before_and_after_commit(self):
        for timing in ("before", "after"):
            with self.subTest(timing=timing):
                if timing == "after":
                    self.tearDown()
                    self.setUp()
                run = self.completed_run()
                self.failed_audit(run)
                original_git = workflow.git

                def interrupted(repo, *arguments):
                    if arguments[0] == "commit" and timing == "before":
                        raise KeyboardInterrupt()
                    result = original_git(repo, *arguments)
                    if arguments[0] == "commit" and timing == "after":
                        raise KeyboardInterrupt()
                    return result

                with patch.object(workflow, "git", side_effect=interrupted):
                    with self.assertRaises(KeyboardInterrupt):
                        run.repair_audit(self.repair_plan(run, create=True))
                recovered = workflow.Run(self.repo, "PRD.md")
                recovered.reconcile_commit()
                self.assertEqual("ready", recovered.data["phase"])
                self.assertEqual(1, len(recovered.data["audit_cycles"][-1]["rounds"]))
                self.assertEqual("", workflow.git(self.repo, "status", "--porcelain"))


if __name__ == "__main__":
    unittest.main()
