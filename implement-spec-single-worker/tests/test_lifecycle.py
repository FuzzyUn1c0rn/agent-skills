import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import unittest
import datetime
from unittest.mock import patch

import test_entry
import workflow


class LifecycleTests(unittest.TestCase):
    setUp = test_entry.EntryTests.setUp
    command_result = test_entry.EntryTests.command_result
    guard_result = test_entry.EntryTests.guard_result

    def wait_file(self, path):
        deadline = time.monotonic() + 15
        while not path.exists():
            if time.monotonic() > deadline:
                self.fail(f"Fixture did not create {path}")
            time.sleep(0.03)

    def start_dedicated(self, resume=False, **options):
        environment = dict(self.env, IMPLEMENT_SPEC_TEST_CHILD=str(Path(__file__).with_name("dedicated_child.py")),
                           IMPLEMENT_SPEC_TEST_CHILD_ROOT=str(self.root), IMPLEMENT_SPEC_TEST_REPO=str(self.repo), **options)
        process = subprocess.Popen(
            self.command + ["start", "PRD.md", "--repo", str(self.repo), "--session", "new"] + (["--resume"] if resume else []),
            env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        def cleanup():
            (self.root / "child-exit").touch()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            process.communicate(timeout=10)
        self.addCleanup(cleanup)
        ready = queue.Queue()
        threading.Thread(target=lambda: ready.put(process.stdout.readline()), daemon=True).start()
        line = ready.get(timeout=10)
        if not line:
            self.fail(process.stderr.read())
        ownership = json.loads(line)
        if not options.get("IMPLEMENT_SPEC_TEST_SPAWN_FAILURE"):
            self.wait_file(self.root / "child-ready.json")
        self.env.update(CODEX_THREAD_ID="dedicated-outer", IMPLEMENT_SPEC_LAUNCH_ID=ownership["launch_id"])
        return process, ownership

    def test_dedicated_ownership_precedes_spawn_and_child_failure_does_not_clear_it(self):
        process, ownership = self.start_dedicated(IMPLEMENT_SPEC_TEST_CHILD_EXIT="7")
        self.assertEqual("dedicated", ownership["mode"])
        self.assertIsNone(ownership["outer_session"])
        self.assertEqual("preflight", ownership["phase"])
        self.assertTrue(ownership["launch_id"])
        self.assertEqual(7, process.wait(timeout=10))
        self.assertTrue((workflow.git_home(self.repo) / "entry.json").is_file())

    def test_fresh_dedicated_outer_must_admit_before_guarded_work(self):
        self.start_dedicated()
        rejected = self.guard_result()
        self.assertEqual(2, rejected.returncode)
        self.assertIn("admission", rejected.stderr)
        admitted = self.command_result("admit")
        self.assertEqual(0, admitted.returncode, admitted.stderr)
        self.assertEqual("dedicated-outer", json.loads(admitted.stdout)["outer_session"])
        allowed = self.guard_result()
        self.assertIn("missing-plan", allowed.stderr)

    def test_release_is_one_way_and_requires_worker_evidence_plus_child_exit(self):
        process, ownership = self.start_dedicated()
        self.assertEqual(0, self.command_result("admit").returncode)
        stopped = self.command_result("stop", {
            "launch_id": ownership["launch_id"], "previous_workers_inactive": True,
            "evidence": "Every workflow worker was closed before requesting release.",
        })
        self.assertEqual(0, stopped.returncode, stopped.stderr)
        saved = json.loads((workflow.git_home(self.repo) / "entry.json").read_text(encoding="utf-8"))
        self.assertEqual("releasing", saved["phase"])
        self.assertIsNone(process.poll(), "Release must not wait for Codex exit")
        self.assertEqual(2, self.guard_result().returncode)
        (self.root / "child-exit").touch()
        self.assertEqual(0, process.wait(timeout=10))
        self.assertFalse((workflow.git_home(self.repo) / "entry.json").exists())

    def test_release_and_workflow_mutations_are_serialized(self):
        (self.repo / "ticket.md").write_text("Status: ready-for-agent\n", encoding="utf-8")
        workflow.git(self.repo, "add", "ticket.md")
        workflow.git(self.repo, "commit", "-m", "Ticket fixture")
        _, ownership = self.start_dedicated()
        self.assertEqual(0, self.command_result("admit").returncode)
        pause = self.root / "pause"
        pause.mkdir()
        self.addCleanup(lambda: (pause / "resume").touch())
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({
            "spec": "PRD.md", "checks": [["suite"]], "requirements": ["US1"],
            "approval_evidence": "Approved fixture", "tickets": [
                {"path": "ticket.md", "execution": "AFK", "kind": "documentation", "criteria": ["AC1"]},
            ],
        }), encoding="utf-8")
        mutation = subprocess.Popen(
            self.workflow_command + ["init", "PRD.md", "--repo", str(self.repo), "--plan", str(plan)],
            env=dict(self.env, IMPLEMENT_SPEC_TEST_PAUSE_GIT=str(pause)),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        def close_mutation():
            (pause / "resume").touch()
            mutation.communicate(timeout=30)
        self.addCleanup(close_mutation)
        self.wait_file(pause / "entered")
        report = {"launch_id": ownership["launch_id"], "previous_workers_inactive": True,
                  "evidence": "No workflow workers remain."}
        stopped = self.command_result("stop", report)
        self.assertEqual(2, stopped.returncode, "Release raced a mutation that already passed admission")
        (pause / "resume").touch()
        output, errors = mutation.communicate(timeout=30)
        self.assertEqual(0, mutation.returncode, errors)
        self.assertEqual(0, self.command_result("stop", report).returncode)
        self.assertEqual(2, self.guard_result().returncode)

    def test_zero_exit_without_release_and_spawn_failure_leave_recoverable_null_ownership(self):
        process, ownership = self.start_dedicated(IMPLEMENT_SPEC_TEST_CHILD_EXIT="0")
        self.assertEqual(0, process.wait(timeout=10))
        for mode in ("current", "new"):
            rejected = subprocess.run(
                self.command + ["start", "PRD.md", "--repo", str(self.repo), "--session", mode],
                env=self.env, capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(2, rejected.returncode)
            self.assertIn("recover", rejected.stderr)
        unfinished = self.repo / "unfinished.txt"
        unfinished.write_text("Retain this unfinished work", encoding="utf-8")
        wrong = self.command_result("recover", {
            "launch_id": "old-launch", "previous_workers_inactive": True, "evidence": "Fixture child exited.",
        })
        self.assertEqual(2, wrong.returncode)
        recovered = self.command_result("recover", {
            "launch_id": ownership["launch_id"], "previous_workers_inactive": True,
            "evidence": "Fixture child exited and no workers were started.",
        })
        self.assertEqual(0, recovered.returncode, recovered.stderr)
        self.assertEqual("Retain this unfinished work", unfinished.read_text(encoding="utf-8"))
        unfinished.unlink()
        (self.root / "child-ready.json").unlink()
        failed, second = self.start_dedicated(IMPLEMENT_SPEC_TEST_SPAWN_FAILURE="1")
        self.assertEqual(2, failed.wait(timeout=10))
        self.assertNotEqual(ownership["launch_id"], second["launch_id"])
        self.assertTrue((workflow.git_home(self.repo) / "entry.json").exists())

    def test_live_holder_cannot_be_recovered_and_launcher_death_does_not_bypass_surviving_child(self):
        process, ownership = self.start_dedicated()
        report = {"launch_id": ownership["launch_id"], "previous_workers_inactive": True,
                  "evidence": "Recovery fixture evidence"}
        self.assertEqual(2, self.command_result("recover", report).returncode)
        self.wait_file(self.root / "child-heartbeat")
        process.kill()
        process.wait(timeout=10)
        previous = (self.root / "child-heartbeat").read_text(encoding="utf-8")
        deadline = time.monotonic() + 5
        while (self.root / "child-heartbeat").read_text(encoding="utf-8") == previous:
            if time.monotonic() > deadline:
                self.fail("Child did not survive launcher death")
            time.sleep(0.03)
        with workflow.exclusive(workflow.git_home(self.repo) / "launch.lock"):
            pass
        self.assertEqual(2, self.guard_result().returncode)
        for mode in ("current", "new"):
            result = subprocess.run(
                self.command + ["start", "PRD.md", "--repo", str(self.repo), "--session", mode],
                env=self.env, capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("recover", result.stderr)
        (self.root / "child-exit").touch()
        self.wait_file(self.root / "child-exited")
        self.assertEqual(0, self.command_result("recover", report).returncode)

    def test_dedicated_admission_rejects_stale_context_leaf_metadata_and_wrong_checkout(self):
        _, ownership = self.start_dedicated()
        metadata_path = self.home / "sessions/fixture/rollout-dedicated-outer.jsonl"
        valid = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.env["IMPLEMENT_SPEC_LAUNCH_ID"] = "old-launch"
        self.assertEqual(2, self.command_result("admit").returncode)
        self.env["IMPLEMENT_SPEC_LAUNCH_ID"] = ownership["launch_id"]
        for change in (
            {"source": {"subagent": {"thread_spawn": {"parent_thread_id": "unrelated"}}}},
            {"cwd": str(self.root)},
            {"timestamp": "2020-01-01T00:00:00+00:00"},
        ):
            invalid = {"type": "session_meta", "payload": dict(valid["payload"], **change)}
            metadata_path.write_text(json.dumps(invalid) + "\n", encoding="utf-8")
            self.assertEqual(2, self.command_result("admit").returncode)
            self.assertIsNone(json.loads((workflow.git_home(self.repo) / "entry.json").read_text(encoding="utf-8"))["outer_session"])
        metadata_path.write_text(json.dumps(valid) + "\n", encoding="utf-8")
        self.assertEqual(0, self.command_result("admit").returncode)
        self.env["CODEX_THREAD_ID"] = "unrelated-outer"
        self.assertEqual(2, self.guard_result().returncode)

    def test_only_bound_outer_can_release_matching_launch_and_coordinators_are_retired(self):
        _, ownership = self.start_dedicated()
        report = {"launch_id": ownership["launch_id"], "previous_workers_inactive": True,
                  "evidence": "All workers closed."}
        self.assertEqual(2, self.command_result("stop", report).returncode)
        self.assertEqual(0, self.command_result("admit").returncode)
        for identifier in ("coordinator-one", "coordinator-two"):
            metadata = {"type": "session_meta", "payload": {
                "id": identifier, "cwd": str(self.repo),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "source": {"subagent": {"thread_spawn": {"parent_thread_id": "dedicated-outer",
                           "agent_role": "implementation_coordinator", "depth": 1}}},
            }}
            (self.home / f"sessions/fixture/rollout-{identifier}.jsonl").write_text(json.dumps(metadata) + "\n", encoding="utf-8")
        register = self.command + ["coordinator", "PRD.md", "--repo", str(self.repo), "--agent"]
        self.assertEqual(0, subprocess.run(register + ["coordinator-one"], env=self.env, capture_output=True).returncode)
        coordinator = dict(self.env, CODEX_THREAD_ID="coordinator-one")
        self.assertIn("missing-plan", self.guard_result(coordinator).stderr)
        original = self.env
        self.env = coordinator
        self.assertEqual(2, self.command_result("stop", report).returncode)
        self.env = original
        self.assertEqual(2, self.command_result("stop", dict(report, launch_id="old-launch")).returncode)
        retired = self.command_result("release-coordinator", dict(report, coordinator="coordinator-one"))
        self.assertEqual(0, retired.returncode, retired.stderr)
        self.assertIn("owner", self.guard_result(coordinator).stderr)
        self.assertEqual(2, subprocess.run(register + ["coordinator-one"], env=self.env, capture_output=True).returncode)
        self.assertEqual(0, subprocess.run(register + ["coordinator-two"], env=self.env, capture_output=True).returncode)

    def test_dedicated_resume_accepts_saved_native_identity_and_preserves_attempts_and_dirty_work(self):
        (self.repo / "ticket.md").write_text("Status: ready-for-agent\n", encoding="utf-8")
        workflow.git(self.repo, "add", "ticket.md")
        workflow.git(self.repo, "commit", "-m", "Resume ticket")
        workflow.choose_branch(self.repo, "PRD.md", "saved-feature")
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "dedicated-outer"}):
            run = workflow.Run(self.repo, "PRD.md")
            run.create({"spec": "PRD.md", "checks": [["suite"]], "requirements": ["US1"],
                        "approval_evidence": "Approved fixture", "tickets": [
                            {"path": "ticket.md", "execution": "AFK", "criteria": ["AC1"], "seams": ["public"]},
                        ]})
            run.begin("ticket.md")
        checkpoint = run.data["checkpoint"]
        unfinished = self.repo / "unfinished.py"
        unfinished.write_text("unfinished = True\n", encoding="utf-8")
        self.start_dedicated(resume=True, IMPLEMENT_SPEC_TEST_OLD_SESSION="1")
        admitted = self.command_result("admit", {
            "previous_outer_session": "dedicated-outer", "previous_workers_inactive": True,
            "evidence": "The prior coordinator and every leaf were closed.",
        })
        self.assertEqual(0, admitted.returncode, admitted.stderr)
        retained = workflow.Run(self.repo, "PRD.md")
        self.assertEqual(1, retained.data["tickets"]["ticket.md"]["attempts"])
        self.assertEqual(checkpoint, retained.data["checkpoint"])
        self.assertEqual("implementing", retained.data["phase"])
        self.assertTrue(unfinished.exists())


if __name__ == "__main__":
    unittest.main()
