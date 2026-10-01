---
name: implement-spec-single-worker
description: Execute an approved AFK PRD sequentially with a coordinator, TDD implementers, independent verification, local commits and a final audit.
argument-hint: "PRD path; optional branch; resume"
disable-model-invocation: true
---

# Sequential implementation

Use this skill when the user explicitly requests implementation of an approved
PRD and its AFK tickets. Designing or editing this framework does not authorize
executing repository tickets.

## Start

Use the dedicated launcher from the repository root:

```sh
python3 ~/.agents/skills/implement-spec-single-worker/scripts/workflow.py launch path/to/PRD.md
```

Add `--branch feature/name` to select an existing branch or create it from the
current commit. Without it, `main` gets a new implementation branch and other
branches are reused. Add `--resume` for an interrupted run on its recorded branch.

The launcher uses the `implement-spec` Codex preset, checks recorded native
compatibility and holds an operating-system checkout lock for the session.
When invoked inside an ordinary session, finish the requested planning or
inspection and explain the launch command. Execution requires the preset and
launcher; do not emulate named profiles by copying prompts into generic agents.

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
   no model or effort override. Supply the PRD and saved run record paths.
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
fresh for every attempt, including repairs. Supply the current diff and untracked
files, prior TDD evidence and verifier findings from the saved attempt history.
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
Astra agent's decision. Report disputed findings with `dispute`; preserve the
verifier's original report. Keep your thread open but idle during adjudication.
The decision cannot grant PASS or reset attempts.

Keep the coordinator open while its child runs. The V1 settings allow two open
threads across the tree, reserving one for the coordinator and one for its worker.
The root must retain the coordinator until all ticket work stops.
Leaf agents have delegation disabled.
A second launcher is rejected by the checkout lock. This applies to the
supported workflow; the user must keep the checkout exclusive.

## Limits

Implementers use the existing TDD skill directly at approved boundaries.
They do not use `/implement`, delegate, commit or close tickets. Verifiers and
auditors leave source and tracker files unchanged. The coordinator owns ticket
commits; the outer agent owns the final report and PRD status commit.

Run ordinary local implementation and offline checks autonomously. Live tests,
migrations and external-service writes require explicit run-level authorization.
Never push or rewrite history.

Read [runtime.md](references/runtime.md) when installing, changing runtime
settings, or when the compatibility check fails. The framework must demonstrate
named-profile selection, resolved models, nested delegation and rejection of
overlapping workers before processing real tickets.
