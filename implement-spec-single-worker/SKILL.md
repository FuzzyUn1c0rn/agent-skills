---
name: implement-spec-single-worker
description: Execute an approved AFK PRD sequentially with a coordinator, TDD implementers, independent verification, local commits and a final audit.
---

# Sequential implementation

Use this skill when the user explicitly requests implementation of an approved
PRD and its AFK tickets. Designing or editing this framework does not authorize
executing repository tickets.

## Start

The user invokes the skill, not a Python command:

```text
$implement-spec-single-worker path/to/PRD.md
$implement-spec-single-worker path/to/PRD.md session=new branch=feature/name
$implement-spec-single-worker path/to/PRD.md resume
```

Read [entry.md](references/entry.md) before starting or recovering a run.
Resolve `session` from the invocation, then `default_session` in
[settings.toml](settings.toml). The shipped default is `current`.

- `current`: this invoking Codex session is the outer agent. The user selects
  its model and effort. Do not change either or start a replacement outer.
  Run the entry helper internally to hold the checkout lock, complete local
  preflight and proceed to the actual ticket work.
- `new`: run the dedicated launcher internally. It opens a separate outer
  with the configured launcher model and effort. An outer already opened by
  the launcher proceeds directly; never recursively launch another session.

Use `branch=name` to select an existing branch or create it from the current
commit. Otherwise create a branch on `main` and reuse a non-main branch.
`resume` preserves the saved run, unfinished changes and retry budgets.
No remembered Python syntax is required from the user.

Role models and efforts come only from `settings.toml`. Generated profiles and
tests consume that file. Read [runtime.md](references/runtime.md) when changing
settings or handling an actual agent-tool error.
Missing native `agent_type` tools or a failed real-work spawn blocks execution.
Do not copy role prompts into generic agents as a substitute.
Use existing session defaults whenever adequate. Never create or edit project or
personal startup configuration to enable this skill. Required launcher overrides
apply only to its dedicated process. If current-session capabilities are missing,
report the missing capability; switching modes requires the user's choice.

Agent threads are for the real coordinator, ticket implementation or repair,
ticket verification and final audit. Do not spawn runtime probes, test agents,
marker-only agents or simulated repair cycles. In current mode keep the native
agent tree attached to this visible outer session. Report ticket transitions,
completed commits and blockers here so the user can follow the work.

## Outer agent

1. Read [workflow.md](references/workflow.md) for the agreed execution contract
   and [commands.md](references/commands.md) for guard commands and the plan format.
2. Perform preflight against the selected branch. Read applicable repository
   instructions and all required tickets. Resolve the entire dependency graph,
   required checks, completion labels and approved testing boundaries. Missing
   significant decisions or required authorization stop the run.
3. Write the preflight plan outside the checkout and initialize the run using
   the guard. For a resume, reconcile the saved state and old agent lifecycle
   before allowing any new worker. Never discard unfinished changes.
4. Spawn exactly one native `implementation_coordinator` by `agent_type`, with
   no model or effort override or full-history fork. In current-session mode
   first ask it to return `COORDINATOR_READY` without starting work. Wait for that response, register
   its ID using `entry.py coordinator SPEC --agent ID`, then send the plan with
   `send_input`. Supply the PRD and saved run record paths.
   Wait while it processes tickets. The outer agent does not modify project
   files or start another worker while the coordinator or a worker is executing.
5. Adjudicate repeated or disputed blocking findings once per ticket, using
   [the adjudication rules](references/workflow.md#adjudication). The coordinator
   must be idle with every leaf closed. Record the evidence-backed decision
   through the guard, then return it to the open coordinator. Missing decisions
   and further unresolved disagreement return to the user.
6. After all required ticket commits exist, close the coordinator. Spawn one
   native `spec_auditor` with the complete PRD, ticket set, baseline, commit list,
   repository rules and verification evidence.
7. Close the auditor when it returns. Save and commit its report with the
   guard's `finish` command. Mark the PRD finished only after a complete audit
   without blockers. Report findings without automatically repairing them or
   reopening completed tickets.

## Coordinator

Read [workflow.md](references/workflow.md), [commands.md](references/commands.md)
and [results.md](references/results.md).

Follow the saved plan. One unfinished ticket and one child at a time. Run the
guard's `begin` before a new implementation attempt. Spawn `ticket_implementer`
fresh without a full-history fork for every attempt, including repairs. Supply
the current diff and untracked files, prior TDD evidence and verifier findings
from the saved attempt history.
Never resume a closed implementer: the tested runtime changes its model settings.

Wait for the implementer, record its result, and close its active agent slot.
Start a fresh `ticket_verifier` for every attempt. Close the verifier before
starting a repair. The initial attempt and two repairs are the maximum,
including across interrupted sessions.

Use structured verdicts. `PASS` permits the guard's ticket commit after checking
the exact diff; `REWORK` permits a bounded repair; `BLOCKED` stops the whole run.
Unavailable required checks, ambiguous reports and exhausted retries cannot
be treated as a pass. Advisory suggestions do not authorize scope expansion.

Before another repair, check the guard's phase. `adjudicating` requires the outer
agent's decision. Report disputed findings with `dispute`; preserve the
verifier's original report. Keep your thread open but idle during adjudication.
The decision cannot grant PASS or reset attempts.

Keep the coordinator open while its child runs. The coordinator is responsible
for sequential execution even when Codex offers additional agent slots. This
workflow does not set a runtime concurrent-agent cap. The outer agent waits;
leaf agents have delegation disabled. Python guards manage ticket state but do
not intercept native agent spawning. There is no hard single-worker guarantee.
A second workflow entry is rejected by the checkout lock, but that lock does not
control unrelated agents or software. The user must keep the checkout exclusive.

## Limits

Implementers use the existing TDD skill directly at approved boundaries.
They do not use `/implement`, delegate, commit or close tickets. Verifiers and
auditors leave source and tracker files unchanged. The coordinator owns ticket
commits; the outer agent owns the final report and PRD status commit.

Run ordinary local implementation and offline checks autonomously. Live tests,
migrations and external-service writes require explicit run-level authorization.
Never push or rewrite history.

Read [runtime.md](references/runtime.md) when installing, changing runtime
settings or handling an actual agent-tool error. Startup checks local settings,
checkout ownership and saved state without launching test agents.
