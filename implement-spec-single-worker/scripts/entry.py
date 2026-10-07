#!/usr/bin/env python3
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import configuration
import platform_support
import workflow


def session_id():
    selected = os.environ.get("CODEX_THREAD_ID")
    if not selected:
        raise workflow.WorkflowError("Entry requires the invoking native Codex session.")
    return selected


def entry_path(repo):
    return workflow.git_home(repo) / "entry.json"


def owned_entry(repo, spec, admission=False):
    path = entry_path(repo)
    if not path.exists():
        raise workflow.WorkflowError("No checkout ownership. Run entry.py start first.")
    entry = json.loads(path.read_text(encoding="utf-8"))
    workflow.require_entry_context(entry)
    unbound = admission and entry["mode"] == "dedicated" and entry["outer_session"] is None
    if (not unbound and entry["outer_session"] != session_id()) or entry["spec"] != spec:
        raise workflow.WorkflowError("This checkout entry belongs to a different outer session or PRD.")
    if entry.get("release"):
        raise workflow.WorkflowError("Checkout release is already pending.")
    try:
        with workflow.exclusive(workflow.git_home(repo) / "launch.lock"):
            pass
    except workflow.LockContended:
        return entry
    raise workflow.WorkflowError("The lock holder stopped. Confirm old workers are inactive, then recover.")


def require_inactive(report):
    if not report or report.get("previous_workers_inactive") is not True or not report.get("evidence"):
        raise workflow.WorkflowError("Confirm all old workflow agents are closed, with concrete evidence.")


def create_ownership(repo, spec, mode, executable, branch=None, resume=False,
                     outer=None, selected_branch=None, expected_outer=None):
    """Persist ownership while the caller retains the checkout lock."""
    with workflow.exclusive(workflow.git_home(repo) / "entry-state.lock"):
        if entry_path(repo).exists():
            raise workflow.WorkflowError("A previous entry was interrupted. Confirm inactive workers, then recover.")
        entry = {
            "mode": mode, "launch_id": str(uuid.uuid4()), "phase": "preflight",
            "outer_session": outer, "expected_outer_session": expected_outer,
            "spec": spec, "requested_branch": branch, "resume": resume,
            "started": time.time(), "runtime": workflow.runtime_version(executable),
            "codex_executable": str(executable), "branch": selected_branch,
            "config_fingerprint": workflow.config_fingerprint(),
        }
        workflow.write_json(entry_path(repo), entry)
        return entry


def complete_release(repo, launch_id):
    """Clear valid shutdown evidence while the caller retains the checkout lock."""
    with workflow.exclusive(workflow.git_home(repo) / "entry-state.lock"):
        entry = json.loads(entry_path(repo).read_text(encoding="utf-8"))
        if entry.get("launch_id") != launch_id:
            raise workflow.WorkflowError("Checkout ownership changed while the holder was running.")
        release = entry.get("release", {})
        if (entry["phase"] != "releasing" or release.get("launch_id") != launch_id
                or release.get("previous_workers_inactive") is not True or not release.get("evidence")):
            return False
        entry_path(repo).unlink()
        return True


def hold(repo, spec, branch=None, resume=False):
    workflow.verify_configuration()
    executable = platform_support.resolve_codex()
    owner = session_id()
    workflow.relative_file(repo, spec)
    with workflow.exclusive(workflow.git_home(repo) / "launch.lock"):
        entry = create_ownership(repo, spec, "current", executable, branch, resume, outer=owner)
        print(json.dumps(entry), flush=True)
        while True:
            current = json.loads(entry_path(repo).read_text(encoding="utf-8"))
            if current.get("release"):
                try:
                    if complete_release(repo, entry["launch_id"]):
                        return 0
                except workflow.LockContended:
                    pass
            time.sleep(0.2)


def admit(repo, spec, report=None):
    with workflow.exclusive(workflow.git_home(repo) / "entry-state.lock"):
        entry = owned_entry(repo, spec, admission=True)
        owner = session_id()
        if entry["mode"] == "dedicated":
            native = workflow.session_metadata(owner)
            source = native.get("source")
            if (not source or (isinstance(source, dict) and "subagent" in source)
                    or Path(native["cwd"]).resolve() != Path(repo).resolve()
                    or (entry["resume"] and owner != entry["expected_outer_session"])
                    or (not entry["resume"] and datetime.datetime.fromisoformat(native["timestamp"]).timestamp() < entry["started"])):
                raise workflow.WorkflowError("Dedicated admission requires the matching native outer session and checkout.")
            if entry["branch"] != workflow.git(repo, "branch", "--show-current"):
                raise workflow.WorkflowError("Dedicated admission branch changed after launch.")
        workflow.verify_configuration()
        if (entry["runtime"] != workflow.runtime_version(entry["codex_executable"])
                or entry["config_fingerprint"] != workflow.config_fingerprint()):
            raise workflow.WorkflowError("Runtime or settings changed during admission. Stop and start again.")
        if entry["phase"] == "admitted":
            return entry
        if entry["resume"]:
            require_inactive(report)
            if entry["requested_branch"] and entry["requested_branch"] != workflow.git(repo, "branch", "--show-current"):
                existing = workflow.git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()
                if entry["requested_branch"] not in existing:
                    raise workflow.WorkflowError("A resume branch must already exist.")
                workflow.choose_branch(repo, spec, entry["requested_branch"])
            with workflow.exclusive(workflow.git_home(repo) / "state.lock"):
                run = workflow.Run(repo, spec)
                if not run.data or report.get("previous_outer_session") != run.data.get("outer_session"):
                    raise workflow.WorkflowError("Resume must identify the saved outer session and inactive workers.")
                if entry["mode"] == "dedicated":
                    if run.data["outer_session"] != owner:
                        raise workflow.WorkflowError("Dedicated resume must retain the saved outer session.")
                else:
                    run.data.setdefault("handovers", []).append({
                        "from": run.data.get("outer_session"), "to": owner, "evidence": report["evidence"],
                    })
                    run.data["outer_session"] = owner
                    workflow.write_json(run.path, run.data)
                    workflow.write_json(workflow.relative_file(repo, run.record), run.data)
            selected = run.data["branch"]
        else:
            selected = workflow.choose_branch(repo, spec, entry["branch"] if entry["mode"] == "dedicated" else entry["requested_branch"])
            if workflow.Run(repo, spec).data:
                raise workflow.WorkflowError("Run already exists on this branch. Stop, then start with --resume.")
        workflow.relative_file(repo, spec).read_text()
        entry.update(phase="admitted", admitted_at=time.time(), branch=selected, outer_session=owner)
        workflow.write_json(entry_path(repo), entry)
        return entry


def register_coordinator(repo, spec, identifier):
    with workflow.exclusive(workflow.git_home(repo) / "entry-state.lock"):
        entry = owned_entry(repo, spec)
        workflow.verify_checkout_entry(repo, spec)
        if entry.get("coordinator") not in (None, identifier):
            raise workflow.WorkflowError("Close and release the recorded coordinator before registering another.")
        if identifier in {item["coordinator"] for item in entry.get("closed_coordinators", [])}:
            raise workflow.WorkflowError("A closed coordinator cannot be reused; spawn a fresh named coordinator.")
        workflow.validate_coordinator(identifier, entry)
        entry["coordinator"] = identifier
        workflow.write_json(entry_path(repo), entry)


def release_coordinator(repo, spec, report):
    require_inactive(report)
    with workflow.exclusive(workflow.git_home(repo) / "entry-state.lock"):
        entry = owned_entry(repo, spec)
        workflow.verify_checkout_entry(repo, spec)
        if not entry.get("coordinator") or report.get("coordinator") != entry["coordinator"]:
            raise workflow.WorkflowError("Identify the recorded coordinator whose workers have closed.")
        run = workflow.Run(repo, spec)
        if run.data:
            run.ensure({"ready", "audit-blocked", "blocked"}, checkpoint=True)
        entry.setdefault("closed_coordinators", []).append(dict(report, closed_at=time.time()))
        entry["coordinator"] = None
        workflow.write_json(entry_path(repo), entry)


def stop(repo, spec, report):
    require_inactive(report)
    with workflow.exclusive(workflow.git_home(repo) / "entry-state.lock"):
        entry = owned_entry(repo, spec)
        if report.get("launch_id") != entry["launch_id"]:
            raise workflow.WorkflowError("Release evidence must identify the matching launch ID.")
        if entry["mode"] == "dedicated" and entry["phase"] != "admitted":
            raise workflow.WorkflowError("Dedicated release requires an admitted outer session.")
        entry["release"] = report
        entry["phase"] = "releasing"
        workflow.write_json(entry_path(repo), entry)


def recover(repo, spec, report):
    require_inactive(report)
    with workflow.exclusive(workflow.git_home(repo) / "launch.lock"):
        with workflow.exclusive(workflow.git_home(repo) / "entry-state.lock"):
            entry = json.loads(entry_path(repo).read_text(encoding="utf-8"))
            if not entry.get("launch_id"):
                raise workflow.WorkflowError("Legacy ownership must be recovered with the previous helper before upgrading.")
            if (entry["spec"] != spec or report.get("launch_id") != entry["launch_id"]
                    or report.get("previous_outer_session") != entry["outer_session"]):
                raise workflow.WorkflowError("Recovery must identify the interrupted PRD, launch ID and outer session (if bound).")
            workflow.write_json(workflow.git_home(repo) / "entry-recovery.json",
                                {"entry": entry, "resolution": report})
            entry_path(repo).unlink()


def main():
    parser = argparse.ArgumentParser(description="Use the invoking Codex session or launch a dedicated outer session.")
    parser.add_argument("action", choices=[
        "start", "admit", "coordinator", "release-coordinator", "status", "stop", "recover",
    ])
    parser.add_argument("spec")
    parser.add_argument("--repo", default=os.getcwd())
    parser.add_argument("--session", choices=["current", "new"])
    parser.add_argument("--branch")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--report")
    parser.add_argument("--agent")
    arguments = parser.parse_args()
    try:
        repo = Path(workflow.git(arguments.repo, "rev-parse", "--show-toplevel"))
        spec_path = Path(arguments.spec)
        spec = str(spec_path.resolve().relative_to(repo)) if spec_path.is_absolute() else arguments.spec
        report = json.loads(Path(arguments.report).read_text()) if arguments.report else None
        if arguments.action == "start":
            mode = arguments.session or configuration.load()["default_session"]
            if mode == "new":
                return workflow.launch(repo, spec, arguments.branch, arguments.resume)
            return hold(repo, spec, arguments.branch, arguments.resume)
        if arguments.action == "stop":
            stop(repo, spec, report)
        elif arguments.action == "admit":
            print(json.dumps(admit(repo, spec, report), indent=2))
        elif arguments.action == "status":
            print(json.dumps(owned_entry(repo, spec), indent=2))
        elif arguments.action == "coordinator":
            register_coordinator(repo, spec, arguments.agent)
        elif arguments.action == "release-coordinator":
            release_coordinator(repo, spec, report)
        else:
            recover(repo, spec, report)
        return 0
    except (workflow.WorkflowError, platform_support.LockError, platform_support.ExecutableError,
            OSError, ValueError, KeyError, TypeError,
            subprocess.CalledProcessError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
