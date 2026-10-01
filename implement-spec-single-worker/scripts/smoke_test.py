#!/usr/bin/env python3
import datetime
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

import workflow


EXPECTED = {
    "outer": ("openai.gpt-6-astra", "high", 0),
    "implementation_coordinator": ("openai.gpt-6-luna", "medium", 1),
    "ticket_implementer": ("openai.gpt-6-sol", "high", 2),
    "ticket_verifier": ("openai.gpt-6-sol", "high", 2),
    "spec_auditor": ("openai.gpt-6-astra", "high", 1),
}

PROMPT = """IMPLEMENT_SPEC_RUNTIME_PROBE
The user has confirmed installation and isolated validation of this personal
framework. Reading its non-secret instruction files is explicitly within this
delegated task: ~/.agents/skills/implement-spec-single-worker/SKILL.md and its
references/*.md, ~/.agents/skills/unslop/SKILL.md, and the TDD skill's Markdown
instructions if needed. These are agent instructions, not credentials. Pass this
read authorization to each child. Do not read credentials or unrelated files.
Use shell cat for those authorized Markdown reads; the local node_repl reader
is unavailable. Other shell commands and all writes are outside this probe.
This is an isolated temporary Git repository. Do not modify project files
or contact external services. This is the profile's explicit
compatibility-probe branch, not a request to execute PRD tickets.
Select the real named profiles
using native agent_type with no model or effort overrides.
Spawn exactly one implementation_coordinator and give it this procedure:
  IMPLEMENT_SPEC_RUNTIME_PROBE. Spawn one ticket_implementer with the probe marker.
  Keep its thread open and attempt a second ticket_implementer immediately.
  Record the actual tool error; successful second spawning is a failed test.
  Wait for the first worker, then close it.
  Spawn one ticket_verifier with IMPLEMENT_SPEC_RUNTIME_PROBE, wait and close it.
  Spawn a fresh ticket_implementer for a simulated repair, with
  IMPLEMENT_SPEC_RUNTIME_PROBE and the first worker's result as handoff context.
  Wait and close it. Do not resume any worker.
  Spawn a fresh ticket_verifier with IMPLEMENT_SPEC_RUNTIME_PROBE, wait and close it.
  Report the actual outcomes and COORDINATOR_PROFILE_OK. Keep your own thread
  open until the outer agent closes it. Only authorized Markdown reads may use
  shell cat. Do not edit any files.
Wait for the coordinator to finish and close it. Then spawn spec_auditor with
IMPLEMENT_SPEC_RUNTIME_PROBE, wait and close it. Report the results and
OUTER_PROFILE_OK. Never replace named roles with generic agents.
"""


def metadata(root_id, repository, started):
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "sessions"
    dates = {datetime.datetime.fromtimestamp(started, datetime.timezone.utc).date(),
             datetime.datetime.now(datetime.timezone.utc).date()}
    candidates = []
    for date in dates:
        folder = home / date.strftime("%Y/%m/%d")
        for path in folder.glob("*.jsonl"):
            if path.stat().st_mtime < started:
                continue
            with path.open() as stream:
                first = json.loads(next(stream))
            if first.get("type") == "session_meta" and first["payload"].get("cwd") == str(repository):
                candidates.append((path, first["payload"]))
    known = {root_id}
    selected = []
    while candidates:
        remaining = []
        progressed = False
        for path, session in candidates:
            source = session.get("source")
            spawn = source.get("subagent", {}).get("thread_spawn", {}) if isinstance(source, dict) else {}
            if session["id"] != root_id and spawn.get("parent_thread_id") not in known:
                remaining.append((path, session))
                continue
            known.add(session["id"])
            record = {
                "id": session["id"], "role": spawn.get("agent_role", "outer"),
                "parent": spawn.get("parent_thread_id"), "depth": spawn.get("depth", 0),
                "models": [], "limit_rejections": 0, "markers": [], "operations": [],
            }
            calls = {}
            for line in path.read_text().splitlines():
                event = json.loads(line)
                payload = event.get("payload", {})
                if event.get("type") == "turn_context":
                    record["models"].append([payload.get("model"), payload.get("effort")])
                if event.get("type") == "response_item" and payload.get("type") == "function_call":
                    name = payload.get("name", "").split(".")[-1]
                    if name in {"spawn_agent", "resume_agent", "send_input", "close_agent", "wait_agent"}:
                        arguments = json.loads(payload.get("arguments", "{}"))
                        calls[payload["call_id"]] = {
                            "name": name, "target": arguments.get("target", arguments.get("id")),
                            "role": arguments.get("agent_type"),
                        }
                if event.get("type") == "response_item" and payload.get("type") == "function_call_output":
                    output = str(payload.get("output", ""))
                    if "collab spawn failed: agent thread limit reached" in output:
                        record["limit_rejections"] += 1
                    if payload.get("call_id") in calls:
                        operation = calls[payload["call_id"]]
                        operation["limit_rejected"] = "collab spawn failed: agent thread limit reached" in output
                        try:
                            value = json.loads(output)
                        except (ValueError, TypeError):
                            value = {}
                        operation["succeeded"] = (
                            isinstance(value, dict) and any(
                                key in value for key in ("agent_id", "status", "submission_id", "previous_status")
                            ) and "error" not in value
                        )
                        operation["spawned"] = value.get("agent_id") if isinstance(value, dict) else None
                        operation["completed"] = [
                            target for target, status in value.get("status", {}).items()
                            if isinstance(status, dict) and "completed" in status
                        ] if isinstance(value, dict) and isinstance(value.get("status"), dict) else []
                        record["operations"].append(operation)
                if (event.get("type") == "response_item" and payload.get("type") == "message"
                        and payload.get("role") == "assistant" and payload.get("phase") == "final_answer"):
                    text = "\n".join(item.get("text", "") for item in payload.get("content", []))
                    for marker in ("IMPLEMENTER_PROFILE_OK", "VERIFIER_PROFILE_OK", "AUDITOR_PROFILE_OK"):
                        if marker in text:
                            record["markers"].append(marker)
            selected.append(record)
            progressed = True
        if not progressed:
            break
        candidates = remaining
    return selected


def validate_records(records):
    by_role = {}
    for record in records:
        by_role.setdefault(record["role"], []).append(record)
    configured = all(
        role in by_role and all(
            record["models"] and all(tuple(setting) == expected[:2] for setting in record["models"])
            and record["depth"] == expected[2]
            for record in by_role[role]
        )
        for role, expected in EXPECTED.items()
    )
    workers = by_role.get("ticket_implementer", [])
    coordinator_ops = [
        operation for record in by_role.get("implementation_coordinator", [])
        for operation in record.get("operations", [])
    ]
    spawns = [(index, operation) for index, operation in enumerate(coordinator_ops)
              if operation["name"] == "spawn_agent" and operation["succeeded"]]
    expected_cycle = ["ticket_implementer", "ticket_verifier", "ticket_implementer", "ticket_verifier"]
    repair_complete = [operation["role"] for _, operation in spawns] == expected_cycle
    first_close = None
    for position, (start, operation) in enumerate(spawns):
        end = spawns[position + 1][0] if position + 1 < len(spawns) else len(coordinator_ops)
        completed = next((index for index in range(start + 1, end)
                          if coordinator_ops[index]["name"] == "wait_agent"
                          and operation["spawned"] in coordinator_ops[index].get("completed", [])), None)
        closed = next((index for index in range((completed or start) + 1, end)
                       if coordinator_ops[index]["name"] == "close_agent"
                       and coordinator_ops[index].get("target") == operation["spawned"]
                       and coordinator_ops[index]["succeeded"]), None)
        repair_complete = repair_complete and completed is not None and closed is not None
        if position == 0:
            first_close = closed
    repair_complete = repair_complete and not any(
        operation["name"] == "resume_agent" and operation["succeeded"] for operation in coordinator_ops
    )
    lifecycle = {}
    completed_waits = set()
    completed_closures = set()
    for record in records:
        for operation in record.get("operations", []):
            if operation["succeeded"]:
                if operation["name"] == "spawn_agent" and operation.get("spawned"):
                    lifecycle[operation["spawned"]] = "open"
                elif operation["name"] == "resume_agent":
                    lifecycle[operation["target"]] = "open"
                    completed_waits.discard(operation["target"])
                    completed_closures.discard(operation["target"])
                elif operation["name"] == "wait_agent":
                    completed_waits.update(operation.get("completed", []))
                elif operation["name"] == "close_agent":
                    lifecycle[operation["target"]] = "closed"
                    if operation["target"] in completed_waits:
                        completed_closures.add(operation["target"])
    markers = {"ticket_implementer": "IMPLEMENTER_PROFILE_OK",
               "ticket_verifier": "VERIFIER_PROFILE_OK", "spec_auditor": "AUDITOR_PROFILE_OK"}
    return {
        "named_profiles": set(by_role) == set(EXPECTED) and all(
            len(by_role.get(role, [])) == (2 if role in {"ticket_implementer", "ticket_verifier"} else 1)
            for role in EXPECTED
        ),
        "effective_models": configured,
        "nested_delegation": bool(workers) and len(by_role.get("implementation_coordinator", [])) == 1
        and all(record.get("parent") == by_role["implementation_coordinator"][0]["id"]
                and record["depth"] == 2
                for role in ("ticket_implementer", "ticket_verifier") for record in by_role.get(role, [])),
        "second_worker_rejected": first_close is not None and any(
            operation["name"] == "spawn_agent" and operation.get("limit_rejected")
            for operation in coordinator_ops[spawns[0][0] + 1:first_close]
        ) and len(workers) == 2,
        "workers_completed": all(
            by_role.get(role) and all(
                marker in record.get("markers", []) and record["id"] in completed_closures
                for record in by_role[role]
            )
            for role, marker in markers.items()
        ),
        "repair_lifecycle": repair_complete and len(workers) == 2
        and len({record["id"] for record in workers}) == 2,
        "children_closed": all(lifecycle.get(record["id"]) == "closed" for record in records if record["role"] != "outer"),
    }


def main():
    directory = Path(tempfile.mkdtemp(prefix="implement-spec-native-smoke-"))
    workflow.git(directory, "init", "-b", "main")
    started = time.time()
    events = directory / "events.jsonl"
    errors = directory / "stderr.txt"
    command = [
        "codex", "--no-daemon", "-a", "never", "exec", "--profile", "implement-spec",
        "-C", str(directory), "--json", "-o", str(directory / "result.txt"),
    ] + workflow.enforced_config_arguments() + [PROMPT]
    with events.open("w") as output, errors.open("w") as error:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=output,
                                stderr=error, timeout=1200)
    messages = [json.loads(line) for line in events.read_text().splitlines()]
    roots = [item["thread_id"] for item in messages if item.get("type") == "thread.started"]
    if result.returncode or len(roots) != 1 or not any(item.get("type") == "turn.completed" for item in messages):
        raise workflow.WorkflowError(f"Native smoke did not complete. Inspect {directory}")
    records = metadata(roots[0], directory, started)
    checks = validate_records(records)
    receipt = {
        "runtime": workflow.runtime_version(),
        "config_fingerprint": workflow.config_fingerprint(),
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "checks": checks, "sessions": records, "probe_directory": str(directory),
        "scope": "Native V1 tree with a resident coordinator, one leaf, and an exclusive launcher.",
    }
    workflow.write_json(directory / "evidence.json", receipt)
    if not all(checks.values()):
        raise workflow.WorkflowError(f"Native compatibility failed: {checks}. Evidence: {directory}")
    destination = Path(__file__).resolve().parents[1] / "references/runtime-evidence.json"
    workflow.write_json(destination, receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
