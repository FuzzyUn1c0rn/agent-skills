# Guard commands

Set the selected interpreter, installed skill path and external report directory
using [runtime.md](runtime.md#helper-shell-paths-and-temporary-reports). Run from
the repository root or supply `--repo`. Quote helper paths and all arguments.
`SPEC` and `TICKET` mean canonical tracker references, never inferred filenames.
Read [sources.md](sources.md) before preflight or tracker operations and
[entry.md](entry.md) for admission and checkout ownership.

## Plan and state

After admission, write the approved preflight plan outside the checkout and
initialize the run:

```powershell
& $Python "$Skill/scripts/workflow.py" init "$Spec" --plan "$Reports/approved-plan.json"
```

```sh
"$PYTHON" "$SKILL/scripts/workflow.py" init "$SPEC" --plan "$REPORTS/approved-plan.json"
```

The plan records artifacts fetched from the configured tracker:

```json
{
  "spec": "canonical-specification-reference",
  "tracker": {
    "kind": "configured-tracker",
    "instructions": "docs/agents/issue-tracker.md",
    "completion": "Configured ticket and specification completion operations",
    "journal": "absolute recovery-journal path beneath Git's implement-spec directory"
  },
  "specification": {"body": "Approved requirements", "revision": "source revision or hash", "discussion": []},
  "approval_evidence": "User-approved requirements and testing boundaries, with source references",
  "requirements": ["US1"],
  "checks": [["python", "-m", "pytest"]],
  "authorization": {"live_operations": []},
  "tickets": [
    {
      "ref": "canonical-ticket-reference",
      "body": "Approved ticket requirements",
      "revision": "source revision or hash",
      "discussion": [],
      "state": "ready",
      "execution": "AFK",
      "kind": "behavior",
      "criteria": ["AC1"],
      "seams": ["The approved public interface"],
      "blocked_by": []
    }
  ]
}
```

Use the actual tracker kind and repository checks. Include every required ticket
and completed dependency; `state: "completed"` skips an already completed ticket.
Nonbehavioral tickets use `kind: "documentation"` and explain validation. The
guard checks dependencies, cycles and evidence coverage; the outer confirms the
plan faithfully represents the actual approved tracker artifacts.

Canonical recovery state lives beneath Git's `implement-spec/runs/` directory.
For new runs, `.implement-spec/<run-id>/execution.json` is a versioned execution
record and audit JSON lives in that same evidence directory. These are framework
bookkeeping, not tracker artifacts. `status "SPEC"` reports authoritative state;
`record` and `state_path` identify its evidence destinations. The versioned export
can lag the resulting commit/phase to avoid self-referential commits.

## Ticket cycle

1. `begin "SPEC" --ticket "TICKET"` records the attempt before implementation.
2. Save the actual implementer ID with `checkpoint "SPEC" --implementer ID` before
   file changes, or after it returns while the checkout is stable.
3. Close the implementer and save its result outside the checkout. Call
   `implemented "SPEC" --report "<report-directory>/implementation.json"`.
4. Start an independent verifier with `snapshot "SPEC"`, the attempt, ticket's
   `review_base` from `status`, captured tracker artifacts and required checks.
   Review the full diff from `review_base` through the current working tree.
5. Close the verifier and call
   `reviewed "SPEC" --report "<report-directory>/verification.json"`.
6. On PASS, inspect the exact diff and call `commit "SPEC"`. The guard commits the
   verified work and evidence. Remote trackers then queue publication: publish
   and confirm the actual ticket using the next section before advancing.
   Selected local tracker updates are included in the ticket transaction.
7. REWORK permits a fresh bounded repair after required adjudication. BLOCKED
   stops the entire run. Preserve attempt history and stable finding IDs.

The guard validates structure and snapshot integrity, not the truth of reports.
The verifier inspects actual code and runs the required checks.

## Tracker publication

After the local commit, `status` exposes `pending_publication`. The publishing
agent uses the configured tracker tools to post evidence and perform completion,
then reads the actual artifact back. Record confirmation with:

```text
published "SPEC" --report "<report-directory>/publication.json"
```

```json
{
  "ref": "pending canonical artifact reference",
  "commit": "pending implementation or audit commit",
  "marker": "pending stable marker",
  "previous_workers_inactive": true,
  "receipt": "actual tracker operation or evidence reference",
  "observed_state": "actual read-back completion state",
  "evidence": "Confirmed required evidence and state through the configured tracker"
}
```

The guard binds the receipt to its pending operation and commits it as execution
evidence. It cannot verify a live API result itself. A matching receipt permits
the next ticket; specification publication changes `publishing` to `done`.
Failed or uncertain tracker writes retain the pending operation. Query for its
marker before retrying. Failed receipt commits use `reconcile-commit`.

Only a selected local Markdown tracker uses the conditional behavior in
[local-markdown.md](local-markdown.md), where artifact status is included in the
local transaction instead of requiring remote publication.

## Adjudication

`reviewed` queues `adjudicating` for recurring blocking finding IDs. For a dispute,
call `dispute "SPEC" --report "<report-directory>/dispute.json"` with the current
`ticket`, `attempt`, `reviewed_snapshot`, `finding_ids` and concrete `evidence`.
Preserve the verifier's original report. Disputes may concern REWORK or BLOCKED.

With the coordinator idle and all leaves closed, the outer calls
`adjudicate "SPEC" --report "<report-directory>/adjudication.json"` using
[results.md](results.md#adjudication). REPAIR consumes an existing attempt;
REVERIFY requests independent verification of unchanged code; BLOCKED requires
resolution. None grants PASS or renews a budget. Return the decision to the open
coordinator; do not resume a closed agent.

## Recovery and audit

`status` reports phase, attempts, agent IDs, branch, expected HEAD and pending
tracker operations. Inspect changed files and confirm inactive old workers before
checkpointing. Never refresh a stale PASS into validity.

`reconcile-commit "SPEC"` recovers an interrupted local transaction. A commit that
already succeeded is accepted only if its parent and tree match saved evidence.
Unexpected HEAD changes or hook edits require investigation. For a pending ticket
whose reviewed implementation changed, use
`invalidate "SPEC" --report "<report-directory>/reason.json"` with evidence and
`previous_workers_inactive: true`. Preserve commits and the original review base;
a fresh verifier must inspect the entire ticket diff.

A blocked ticket resumes with `resolve "SPEC" --report "<report-directory>/resolution.json"`:

```json
{
  "evidence": "The recorded blocker is resolved, with actual decisions and authorization",
  "previous_workers_inactive": true,
  "next_phase": "reviewing"
}
```

`reviewing` verifies an existing implementation; `rework` uses an available
attempt. Exhausted budgets or `requires_user_resolution` require actual
`user_authorization`. Ordinary resolution/resume does not renew allowances.
For an interrupted incomplete implementer, first record `implemented` with
`outcome: "BLOCKED"` and interruption evidence, reconcile, then resolve to rework.

After every ticket commit and required publication is confirmed, close the
coordinator and run the final auditor. Save it with
`finish "SPEC" --report "<report-directory>/audit.json"`. Its audited commit,
baseline, snapshot and complete requirement mapping must match the run. A PASS
queues specification publication for remote trackers or completes the selected
local tracker transaction; a failed audit enters `audit-blocked`.

For failed audits, use `repair-audit "SPEC" --report "<report-directory>/audit-repairs.json"`
with actual tracker references. After exhaustion, explicit human continuation
uses `continue-audit "SPEC" --report "<report-directory>/audit-continuation.json"`.
Read [audit-repairs.md](audit-repairs.md) for schemas, limits and decisions.
