import json
import os
import subprocess
import unittest
from pathlib import Path

import test_workflow as fixtures
import test_entry as entry_fixtures

workflow = fixtures.workflow


class RepositoryPathTests(unittest.TestCase):
    setUp = fixtures.WorkflowTests.setUp
    audit_report = fixtures.WorkflowTests.audit_report

    spec = "plans café/仕様/PRD.md"
    ticket = "plans café/tickets/初めの ticket.md"

    def new_run(self, spec=None, ticket=None, dependencies=()):
        for name in (self.spec, self.ticket, *dependencies):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Status: ready-for-agent\n", encoding="utf-8")
        workflow.git(self.repo, "add", "--all")
        workflow.git(self.repo, "commit", "-m", "Nested tracker fixtures")
        run = workflow.Run(self.repo, spec or self.spec)
        run.create({
            "spec": self.spec, "tracker": {"kind": "local-markdown"}, "checks": [["suite"]], "approval_evidence": "Confirmed PRD",
            "requirements": ["US1"],
            "tickets": [{"path": "./" + name, "criteria": ["AC1"], "blocked_by": [],
                         "seams": ["public"], "execution": "AFK", "kind": "behavior"}
                        for name in dependencies] + [
                {"path": ticket or self.ticket, "criteria": ["AC1"], "blocked_by": ["./" + name for name in dependencies],
                 "seams": ["public"], "execution": "AFK", "kind": "behavior"}],
        })
        return run

    def implement_and_review(self, run, spelling=None):
        name = spelling or run.data["current"]
        record = run.data["tickets"][run.data["current"]]
        run.implemented({
            "outcome": "READY_FOR_REVIEW", "ticket": name, "attempt": record["attempts"],
            "tdd": [{"boundary": "public",
                     "red": {"command": ["test"], "exit_code": 1, "evidence": "Behavior absent"},
                     "green": {"command": ["test"], "exit_code": 0, "evidence": "Behavior present"}}],
        })
        run.reviewed({
            "verdict": "PASS", "ticket": name, "attempt": record["attempts"],
            "base_commit": record["review_base"], "reviewed_snapshot": run.data["checkpoint"],
            "criteria": [{"id": "AC1", "satisfied": True, "evidence": "Observed behavior"}],
            "checks": [{"command": ["suite"], "exit_code": 0, "evidence": "Suite passed"}],
            "resolved_findings": [{"id": identifier, "evidence": "Regression test passes"}
                                  for identifier in record.get("audit_findings", [])],
            "blocking_findings": [], "unavailable_checks": [],
        })

    def test_nested_unicode_workflow_commits_ticket_and_final_audit(self):
        run = self.new_run()
        self.assertEqual("plans café/仕様/implementation-run.json", run.record)
        run.begin(self.ticket)
        source = self.repo / "code space" / "données.py"
        source.parent.mkdir()
        source.write_text("result = 42\n", encoding="utf-8")
        self.implement_and_review(run)
        committed = run.commit_ticket()
        self.assertEqual("result = 42", workflow.git(self.repo, "show", f"{committed}:code space/données.py"))
        run.finish(self.audit_report(run))
        resumed = workflow.Run(self.repo, self.spec)
        self.assertEqual("done", resumed.data["phase"])
        self.assertEqual("plans café/仕様/final-audit.md", resumed.data["audits"][0]["path"])
        self.assertEqual("", workflow.git(self.repo, "status", "--porcelain"))

    def test_equivalent_spec_ticket_dependency_and_report_paths_identify_the_same_run(self):
        dependency = "plans café/tickets/準備.md"
        run = self.new_run(
            spec="./plans café//仕様/PRD.md",
            ticket="./plans café/tickets/./初めの ticket.md", dependencies=[dependency],
        )
        resumed = workflow.Run(self.repo, str(Path(self.spec)))
        self.assertEqual(run.data, resumed.data)
        self.assertEqual({dependency, self.ticket}, set(run.data["tickets"]))
        with self.assertRaisesRegex(workflow.WorkflowError, "dependencies"):
            run.begin("./" + self.ticket)
        run.begin(str(Path(dependency)))
        self.implement_and_review(run, spelling="./" + dependency)
        run.commit_ticket()
        run.begin(str(Path(self.ticket)))
        self.implement_and_review(run, spelling="./plans café/tickets/./初めの ticket.md")
        run.commit_ticket()
        self.assertEqual(1, run.data["tickets"][self.ticket]["attempts"])
        self.assertEqual(self.ticket, run.data["tickets"][self.ticket]["history"][0]["implementation"]["ticket"])
        self.assertEqual([dependency], run.data["plan"]["tickets"][-1]["blocked_by"])

    def test_nested_repair_paths_and_links_survive_rejected_commit_recovery(self):
        self.spec = "plans space/spec/PRD.md"
        self.ticket = "plans space/tickets/initial ticket.md"
        repair = "repairs café/deep/統合 ticket.md"
        run = self.new_run()
        run.begin(self.ticket)
        self.implement_and_review(run)
        run.commit_ticket()
        run.finish(dict(self.audit_report(run), verdict="REWORK", blocking_findings=[
            {"id": "A1", "evidence": "The integration violates US1", "reference": self.spec + "#US1"},
        ]))
        report = {
            "audit_number": 1, "reviewed_snapshot": run.data["checkpoint"],
            "previous_workers_inactive": True, "evidence": "Auditor and coordinator closed.",
            "findings": [{"id": "A1", "classification": "confirmed_blocker",
                          "reference": self.spec + "#US1", "evidence": "Reproduced missing behavior."}],
            "tickets": [{"path": "./" + repair, "action": "create", "finding_ids": ["A1"],
                         "requirements": ["US1"], "execution": "AFK", "criteria": ["AC1"],
                         "seams": ["public"], "blocked_by": ["./" + self.ticket],
                         "related_tickets": [str(Path(self.ticket))],
                         "content": "# Repair\n\nStatus: ready-for-agent\n"}],
        }
        hook = self.repo / ".git/hooks/pre-commit"
        hook.write_bytes(b"#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        with self.assertRaises(workflow.WorkflowError):
            run.repair_audit(report)
        hook.unlink()
        resumed = workflow.Run(self.repo, "./" + self.spec)
        resumed.reconcile_commit()
        self.assertIn(repair, resumed.data["tickets"])
        self.assertIn("(../../plans space/spec/final-audit.md)", (self.repo / repair).read_text())
        self.assertEqual([self.ticket], resumed.data["plan"]["tickets"][-1]["related_tickets"])
        resumed.begin(str(Path(repair)))
        self.implement_and_review(resumed, spelling="./" + repair)
        resumed.commit_ticket()
        resumed.finish(self.audit_report(resumed))
        self.assertEqual("done", resumed.data["phase"])
        self.assertEqual(1, resumed.data["tickets"][repair]["attempts"])

    def test_snapshot_exclusions_accept_equivalent_unicode_paths_without_hiding_other_changes(self):
        run = self.new_run()
        initial = workflow.snapshot(self.repo, [run.record])
        (self.repo / run.record).write_bytes(b"updated execution record\n")
        self.assertEqual(initial, workflow.snapshot(self.repo, ["./" + run.record]))
        self.assertEqual(initial, workflow.snapshot(self.repo, [str(Path(run.record))]))
        (self.repo / self.ticket).write_bytes(b"Status: changed\n")
        self.assertNotEqual(initial, workflow.snapshot(self.repo, ["./" + run.record]))

    def test_absolute_traversal_and_git_paths_cannot_identify_a_run(self):
        for name in ("../PRD.md", "plans/../../PRD.md", "/tmp/PRD.md", r"C:\PRD.md",
                     r"C:PRD.md", r"\\server\share\PRD.md", ".git/config"):
            with self.subTest(name=name), self.assertRaises(workflow.WorkflowError):
                workflow.Run(self.repo, name)

    def test_selected_local_tracker_rejects_symlink_files_and_parent_directories(self):
        run = self.new_run()
        link = self.repo / "linked spec.md"
        directory = self.repo / "linked directory"
        try:
            link.symlink_to(self.repo / self.spec)
            directory.symlink_to(self.repo / "plans café", target_is_directory=True)
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 1314:
                self.skipTest("Windows symlink creation requires privileges unavailable in this session.")
            raise
        workflow.git(self.repo, "add", "--all")
        workflow.git(self.repo, "commit", "-m", "Selected local tracker symlink fixtures")
        for name in ("linked spec.md", "linked directory/仕様/PRD.md"):
            plan = dict(run.data["plan"], spec=name, tracker={"kind": "local-markdown"})
            with self.subTest(name=name), self.assertRaisesRegex(workflow.WorkflowError, "regular file"):
                workflow.Run(self.repo, name).create(plan)
        self.assertEqual("ready", run.data["phase"])

    @unittest.skipIf(os.name == "nt", "Windows filenames cannot contain tabs, newlines or quotes.")
    def test_supported_git_delimiters_in_filenames_survive_ticket_and_audit_commits(self):
        run = self.new_run()
        workflow.git(self.repo, "config", "core.quotePath", "true")
        run.begin(self.ticket)
        names = ["code space/tab\tname.py", "code space/line\nname.py", 'code space/quote"name.py',
                 r"code space/back\slash.py"]
        for name in names:
            path = self.repo / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(b"result = 42\n")
        self.implement_and_review(run)
        committed = run.commit_ticket()
        for name in names:
            self.assertEqual("result = 42", workflow.git(self.repo, "show", f"{committed}:{name}"))
        run.finish(self.audit_report(run))
        self.assertEqual("done", run.data["phase"])


class EntryPathTests(unittest.TestCase):
    setUp = entry_fixtures.EntryTests.setUp
    start = entry_fixtures.EntryTests.start

    def test_current_entry_accepts_equivalent_spec_names(self):
        process, ownership = self.start()
        admitted = subprocess.run(
            self.command + ["admit", "./PRD.md", "--repo", str(self.repo)],
            env=self.env, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(0, admitted.returncode, admitted.stderr)
        self.assertEqual("PRD.md", json.loads(admitted.stdout)["spec"])
        report = self.root / "release.json"
        report.write_text(json.dumps({"launch_id": ownership["launch_id"], "previous_workers_inactive": True,
                                      "evidence": "No agents started."}))
        stopped = subprocess.run(
            self.command + ["stop", str(Path(".") / "PRD.md"), "--repo", str(self.repo), "--report", str(report)],
            env=self.env, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(0, stopped.returncode, stopped.stderr)
        self.assertEqual(0, process.wait(timeout=5))


if __name__ == "__main__":
    unittest.main()
