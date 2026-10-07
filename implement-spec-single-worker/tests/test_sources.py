import copy
import json
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

import test_workflow as fixtures
import test_audit_repairs as repairs
import test_entry as entry_fixtures
from test_support import isolate_environment

workflow = fixtures.workflow


class SourceTests(unittest.TestCase):
    audit_report = fixtures.WorkflowTests.audit_report
    implement_and_review = repairs.AuditRepairTests.implement_and_review

    def setUp(self):
        isolate_environment(self)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        workflow.git(self.repo, "init", "-b", "main")
        workflow.git(self.repo, "config", "user.name", "Tracker test")
        workflow.git(self.repo, "config", "user.email", "tracker@example.invalid")
        (self.repo / "code.py").write_text("result = 0\n", encoding="utf-8")
        workflow.git(self.repo, "add", "code.py")
        workflow.git(self.repo, "commit", "-m", "Code baseline without tracker artifacts")
        self.spec = "https://github.com/example/project/issues/41"
        self.ticket = "https://github.com/example/project/issues/42"

    def plan(self, tracker="github"):
        return {
            "spec": self.spec, "tracker": {"kind": tracker, "instructions": "docs/agents/issue-tracker.md"},
            "specification": {"body": "Approved requirement US1", "revision": "parent-revision", "discussion": []},
            "checks": [["suite"]], "requirements": ["US1"],
            "approval_evidence": "Approved actual tracker requirements and testing boundaries",
            "tickets": [{
                "ref": self.ticket, "body": "AC1: implement US1", "revision": "ticket-revision", "state": "ready",
                "execution": "AFK", "criteria": ["AC1"], "seams": ["public"], "blocked_by": [],
            }],
        }

    def start(self, tracker="github"):
        run = workflow.Run(self.repo, self.spec)
        run.create(self.plan(tracker))
        return run

    def complete_ticket(self, run, ticket=None):
        ticket = ticket or self.ticket
        run.begin(ticket)
        (self.repo / "code.py").write_text(f"result = {len(run.data['tickets'])}\n", encoding="utf-8")
        self.implement_and_review(run, "PASS", ticket=ticket)
        return run.commit_ticket()

    def receipt(self, run):
        return dict(run.data["pending_publication"], previous_workers_inactive=True,
                    receipt="actual tracker evidence reference", observed_state="configured completion state",
                    evidence="Read back the evidence and completion state from the configured tracker")

    def publish(self, run):
        return run.published(self.receipt(run))

    def test_tracker_references_complete_without_creating_specification_or_ticket_files(self):
        cases = (
            ("github", self.spec, self.ticket),
            ("gitlab", "https://gitlab.example/project/-/issues/41", "https://gitlab.example/project/-/issues/42"),
            ("custom", "TEAM-41", "TEAM-42"),
            ("custom", "tracker:project/map-41", "tracker:project/task-42"),
        )
        for index, (tracker, spec, ticket) in enumerate(cases):
            with self.subTest(tracker=tracker, spec=spec):
                if index:
                    self.setUp()
                self.spec, self.ticket = spec, ticket
                run = self.start(tracker)
                self.complete_ticket(run)
                self.assertEqual(ticket, run.data["pending_publication"]["ref"])
                with self.assertRaises(workflow.WorkflowError):
                    run.finish(self.audit_report(run))
                self.publish(run)
                run.finish(self.audit_report(run))
                self.assertEqual("publishing", run.data["phase"])
                self.assertEqual(spec, run.data["pending_publication"]["ref"])
                self.publish(run)
                restored = workflow.Run(self.repo, spec)
                restored.ensure(checkpoint=True)
                self.assertEqual("done", restored.data["phase"])
                self.assertEqual(spec, restored.data["plan"]["spec"])
                self.assertEqual(ticket, restored.data["plan"]["tickets"][0]["ref"])
                self.assertEqual(2, len(restored.data["publications"]))
                self.assertTrue(restored.record.endswith("execution.json"))
                self.assertEqual([], list(self.repo.glob("**/*.md")))
                self.assertEqual("", workflow.git(self.repo, "status", "--porcelain"))
                tracked = workflow.git(self.repo, "ls-files").splitlines()
                self.assertTrue(all(name == "code.py" or name.startswith(".implement-spec/") for name in tracked))

    def test_pending_publication_survives_resume_and_blocks_more_ticket_work(self):
        run = self.start()
        self.complete_ticket(run)
        pending = copy.deepcopy(run.data["pending_publication"])
        restored = workflow.Run(self.repo, self.spec)
        with self.assertRaisesRegex(workflow.WorkflowError, "pending tracker publication"):
            restored.begin(self.ticket)
        self.assertEqual(pending, restored.data["pending_publication"])
        for key in ("ref", "marker", "commit", "receipt", "observed_state"):
            invalid = self.receipt(restored)
            invalid[key] = "wrong" if key in {"ref", "marker", "commit"} else ""
            with self.subTest(field=key), self.assertRaises(workflow.WorkflowError):
                restored.published(invalid)
        self.assertEqual(pending, restored.data["pending_publication"])
        self.publish(restored)
        self.assertEqual(1, restored.data["tickets"][self.ticket]["attempts"])

    def test_publication_commit_failure_recovers_without_reimplementation_or_duplicate_receipts(self):
        run = self.start()
        self.complete_ticket(run)
        original_git = workflow.git

        def reject_commit(repo, *arguments):
            if arguments[0] == "commit":
                raise workflow.WorkflowError("Temporary publication-evidence commit failure")
            return original_git(repo, *arguments)

        with patch.object(workflow, "git", side_effect=reject_commit):
            with self.assertRaises(workflow.WorkflowError):
                self.publish(run)
        restored = workflow.Run(self.repo, self.spec)
        self.assertEqual("committing", restored.data["phase"])
        restored.reconcile_commit()
        restored.ensure(checkpoint=True)
        self.assertEqual("ready", restored.data["phase"])
        self.assertEqual(1, len(restored.data["publications"]))
        self.assertEqual(1, restored.data["tickets"][self.ticket]["attempts"])

    def test_actual_repair_issue_references_drive_audits_without_local_ticket_artifacts(self):
        run = self.start()
        self.complete_ticket(run)
        self.publish(run)
        report = self.audit_report(run)
        report.update(verdict="REWORK", blocking_findings=[{
            "id": "A1", "reference": self.spec + "#US1", "evidence": "Integration missing",
        }])
        run.finish(report)
        repair_ref = "https://github.com/example/project/issues/43"
        repair = {
            "audit_number": 1, "reviewed_snapshot": run.data["checkpoint"],
            "previous_workers_inactive": True, "evidence": "All workers stopped",
            "findings": [{"id": "A1", "classification": "confirmed_blocker",
                          "reference": self.spec + "#US1", "evidence": "Reproduced"}],
            "tickets": [{
                "action": "create", "ref": repair_ref, "body": "AC2: finish US1 integration",
                "revision": "created-issue-revision", "tracker_evidence": "Read-back of created and linked issue 43",
                "finding_ids": ["A1"], "requirements": ["US1"], "execution": "AFK",
                "criteria": ["AC2"], "seams": ["public"], "blocked_by": [self.ticket],
            }],
        }
        run.repair_audit(repair)
        restored = workflow.Run(self.repo, self.spec)
        self.assertEqual(repair_ref, restored.data["plan"]["tickets"][-1]["ref"])
        self.complete_ticket(restored, repair_ref)
        self.publish(restored)
        restored.finish(self.audit_report(restored))
        self.publish(restored)
        self.assertEqual("done", restored.data["phase"])
        self.assertEqual(2, len(restored.data["audits"]))
        self.assertEqual([], list(self.repo.glob("**/*.md")))

    def test_remote_reopening_preserves_original_requirements_and_attempt_history(self):
        run = self.start()
        self.complete_ticket(run)
        self.publish(run)
        report = self.audit_report(run)
        report.update(verdict="REWORK", blocking_findings=[{"id": "A1", "evidence": "Original AC1 unmet"}])
        run.finish(report)
        run.repair_audit({
            "audit_number": 1, "reviewed_snapshot": run.data["checkpoint"],
            "previous_workers_inactive": True, "evidence": "Workers stopped; actual issue reopened",
            "findings": [{"id": "A1", "classification": "confirmed_blocker",
                          "reference": self.spec + "#US1", "evidence": "Original criterion unmet"}],
            "tickets": [{"action": "reopen", "ref": self.ticket, "finding_ids": ["A1"],
                         "requirements": ["US1"], "tracker_evidence": "Read back reopened issue 42"}],
        })
        self.assertEqual(self.plan()["tickets"][0]["body"], run.data["plan"]["tickets"][0]["body"])
        self.assertEqual(1, run.data["tickets"][self.ticket]["attempts"])
        run.begin(self.ticket)
        self.assertEqual(2, run.data["tickets"][self.ticket]["attempts"])

    def test_missing_tracker_bodies_revisions_and_path_based_remote_plans_are_rejected(self):
        for missing in ("tracker", "specification", "body", "revision", "ref"):
            plan = self.plan()
            if missing in {"tracker", "specification"}:
                plan.pop(missing)
            elif missing == "ref":
                plan["tickets"][0]["path"] = plan["tickets"][0].pop("ref")
            else:
                plan["tickets"][0].pop(missing)
            with self.subTest(missing=missing), self.assertRaises(workflow.WorkflowError):
                workflow.Run(self.repo, self.spec).create(plan)
        self.assertEqual([], list(self.repo.glob("**/*.md")))

    def test_only_selected_local_markdown_tracker_reads_and_updates_actual_local_artifacts(self):
        self.spec, self.ticket = ".scratch/feature/spec.md", ".scratch/feature/issues/01-task.md"
        for ref in (self.spec, self.ticket):
            path = self.repo / ref
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Status: ready-for-agent\n", encoding="utf-8")
        workflow.git(self.repo, "add", ".scratch")
        workflow.git(self.repo, "commit", "-m", "Selected local tracker artifacts")
        run = self.start("local-markdown")
        self.complete_ticket(run)
        self.assertEqual("closed", workflow.status_text(self.repo / self.ticket))
        self.assertNotIn("pending_publication", run.data)
        run.finish(self.audit_report(run))
        self.assertEqual("done", workflow.status_text(self.repo / self.spec))
        self.assertEqual("done", run.data["phase"])


class ReferenceEntryTests(unittest.TestCase):
    setUp = entry_fixtures.EntryTests.setUp

    def test_real_current_entry_and_init_accept_an_issue_url_without_specification_files(self):
        workflow.git(self.repo, "rm", "PRD.md")
        (self.repo / "code.py").write_text("result = 0\n", encoding="utf-8")
        workflow.git(self.repo, "add", "code.py")
        workflow.git(self.repo, "commit", "-m", "Code-only tracker-backed checkout")
        spec = "https://github.com/example/project/issues/41"
        ticket = "https://github.com/example/project/issues/42"
        process = subprocess.Popen(self.command + ["start", spec, "--repo", str(self.repo), "--session", "current"],
                                   env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        def cleanup():
            if process.poll() is None:
                process.terminate()
            process.communicate(timeout=30)

        self.addCleanup(cleanup)
        ready = queue.Queue()
        threading.Thread(target=lambda: ready.put(process.stdout.readline()), daemon=True).start()
        ownership = json.loads(ready.get(timeout=30))
        result = subprocess.run(self.command + ["admit", spec, "--repo", str(self.repo)],
                                env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        plan = self.root / "approved-plan.json"
        plan.write_text(json.dumps({
            "spec": spec, "tracker": {"kind": "github"}, "checks": [["suite"]], "requirements": ["US1"],
            "specification": {"body": "Approved US1", "revision": "r1"}, "approval_evidence": "Approved boundaries",
            "tickets": [{"ref": ticket, "body": "Approved AC1", "revision": "r2", "state": "ready",
                         "execution": "AFK", "criteria": ["AC1"], "seams": ["public"]}],
        }), encoding="utf-8")
        result = subprocess.run(self.workflow_command + ["init", spec, "--repo", str(self.repo), "--plan", str(plan)],
                                env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(spec, json.loads(result.stdout)["spec"])
        self.assertEqual([], list(self.repo.glob("**/*.md")))
        release = self.root / "release.json"
        release.write_text(json.dumps({"launch_id": ownership["launch_id"], "previous_workers_inactive": True,
                                       "evidence": "No workflow children were started"}), encoding="utf-8")
        stopped = subprocess.run(self.command + ["stop", spec, "--repo", str(self.repo), "--report", str(release)],
                                 env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, stopped.returncode, stopped.stderr)
        self.assertEqual(0, process.wait(timeout=30))


if __name__ == "__main__":
    unittest.main()
