# Guard commands

Run `python3 <skill-directory>/scripts/workflow.py ACTION SPEC` from the repository
root, or supply `--repo`. Spec and ticket paths are repository-relative.

Read [entry.md](entry.md) for both entry modes. The launcher selects the branch
before opening Codex. Current-session entry holds the same lock and selects the
branch during local admission. Guard mutations require a live, admitted entry in
either mode, and are serialized with release. Inherited launch context authorizes
no mutations. `doctor` checks the launcher's installed runtime/profile
settings and makes no project changes or model calls; it does not start agents.

## Plan and state

Write the preflight plan outside the checkout, then call:

```sh
python3 <skill-directory>/scripts/workflow.py init path/to/PRD.md --plan /tmp/approved-plan.json
```

The outer agent constructs the plan from the approved source documents. Example:

```json
{
  "spec": "path/to/PRD.md",
  "approval_evidence": "User-approved PRD and testing boundaries, with source references",
  "requirements": ["US1"],
  "finished_ticket": "closed",
  "finished_spec": "done",
  "checks": [[".venv/bin/python", "-m", "pytest"]],
  "authorization": {"live_operations": []},
  "tickets": [
    {
      "path": "path/to/issues/01-example.md",
      "execution": "AFK",
      "kind": "behavior",
      "criteria": ["AC1"],
      "seams": ["The approved public interface"],
      "blocked_by": []
    }
  ]
}
```

Use the repository's actual check commands and labels. Nonbehavioral tickets use
`kind: "documentation"` and explain their validation. Include the complete
required ticket list in execution order, including already completed dependencies.
The guard detects missing dependencies and cycles. The outer agent confirms that
this list and its criteria faithfully represent the PRD; structural validation
cannot establish that correspondence.

Canonical recovery state lives beneath Git's directory in
`implement-spec/runs/`. `implementation-run.json` beside the PRD is a readable,
versioned export. It records the pre-commit transaction and can lag the last
commit identifier and resulting phase to avoid self-referential commits.
Use `status` for authoritative state.

## Ticket operations

1. `begin SPEC --ticket TICKET` increments the persistent attempt count before
   spawning a fresh implementer. Previous attempts retain their agent IDs,
   TDD evidence and verification reports in the ticket's `history`.
2. Save the spawned implementer ID with
   `checkpoint SPEC --implementer AGENT_ID` before it starts changing files.
   If it is already running, record its ID after it returns, when the tree is
   stable. The coordinator must never fingerprint a tree while a worker writes.
3. Wait, close the implementer slot and save its structured result outside the
   checkout. Call `implemented SPEC --report /tmp/implementation.json`.
4. Start a fresh verifier. Give it `snapshot SPEC`, the attempt, current HEAD and
   ticket's `review_base` from `status SPEC`, and all required source documents and
   checks. Its `base_commit` is `review_base`; review that complete diff through
   the current working tree, not just changes since the latest commit.
5. Wait, close the verifier and call
   `reviewed SPEC --report /tmp/verification.json`.
6. On PASS, inspect the exact diff and selected paths, then call `commit SPEC`.
   The guard rejects a stale review, closes the ticket and commits that status
   with the reviewed work. On REWORK, return to `begin` and spawn a fresh
   configured implementer with the current diff, prior TDD evidence and findings.
   First check for `adjudicating` and report any dispute as described below.
   Do not resume the old agent. On BLOCKED, stop the entire run.

The guard validates handoff structure and evidence coverage, not the truth of
an agent's claims. The independent verifier must inspect the real code and run
the commands. Save factual test evidence without credentials or sensitive output.

## Adjudication commands

`reviewed` automatically enters `adjudicating` for recurring blocking finding
IDs. For an explicit disagreement, the coordinator calls
`dispute SPEC --report /tmp/dispute.json` after saving the original review.
The dispute identifies the current `ticket`, `attempt`, `reviewed_snapshot`,
`finding_ids` and concrete `evidence`. It never edits the verifier's report.
It may dispute findings from either `REWORK` or `BLOCKED`. If automatic
adjudication is already pending, it attaches one consolidated dispute to that
request without spending another decision.

With the coordinator idle and all leaves closed, the outer session calls
`adjudicate SPEC --report /tmp/adjudication.json`. Use the schema in
[results.md](results.md#adjudication). The guard checks the recorded outer
session ID when available, binds the decision to the current snapshot, and
requires a classification for every current blocker. It cannot assess the truth
of the evidence; that remains the outer agent's responsibility.

The ticket's `adjudication` record survives reloads. `REPAIR` enters `rework`
only if an attempt remains. `REVERIFY` clears the current verdict and enters
`reviewing`; only a fresh complete PASS permits a commit. `BLOCKED` or a second
adjudication request requires user resolution. Return the saved decision to the
open coordinator with `send_input`, not `resume_agent`.

## Recovery and audit

Use `status SPEC` to inspect phase, attempts, saved agent identifiers, expected
HEAD and branch. `checkpoint` accepts a reconciled stable working tree only in
implementation, rework or blocked phases. The outer agent must inspect changed
files and confirm previous workers have stopped before using it. It must not
use checkpointing to erase a disputed change or revive a stale PASS.

Use `reconcile-commit SPEC` to retry a pending ticket or audit commit. The guard
records the transaction before editing status or writing the audit report.
If the commit already succeeded, it accepts it only when its parent and tree
match that transaction. Other HEAD changes require investigation.
If a formatter changed a ticket's source, inspect those changes,
confirm old workers are inactive, and use `invalidate SPEC --report /tmp/reason.json`
with `evidence` and `previous_workers_inactive: true`. This preserves the work and
attempt count but discards the stale PASS, requiring a fresh verifier.
If the hook committed its edits successfully, invalidation also records that
unverified commit, retains the original `review_base`, and restores the unfinished
ticket status in the working tree. Verification must cover the full ticket diff,
including those committed edits. A later evidence/status commit completes the
ticket without rewriting history. Unexpected extra commits require investigation.
A blocked run remains blocked until
the outer agent and user resolve its recorded cause; do not edit state by hand.
After reconciling changes and confirming old workers are inactive, record a
checkpoint and use `resolve SPEC --report /tmp/resolution.json` with:

```json
{
  "evidence": "The recorded blocker is resolved, with evidence and any user authorization",
  "previous_workers_inactive": true,
  "next_phase": "reviewing"
}
```

`reviewing` reruns independent verification of an existing implementation.
`rework` allows another implementation attempt only when the current allowance
has not been exhausted. Resolution never renews an allowance.
When `requires_user_resolution` is true or the attempt allowance is exhausted, include `user_authorization`
recording the user's explicit decision. A new agent's opinion or an automatic
retry is not authorization. Resolving the blocker does not replenish adjudication.
An interrupted pending adjudication resumes from its saved request; do not
checkpoint changed code into that request or restart its budget. Explicit human
continuation of exhausted audit repairs uses `continue-audit`, described below.
For an interrupted implementer without a completed result, first use `implemented`
with the current ticket, attempt, `outcome: "BLOCKED"` and interruption evidence.
After reconciliation, resolve to `rework`. Do not resume the old sub-agent.

After all required tickets are committed, close the coordinator and run the
final auditor. Call `finish SPEC --report /tmp/audit.json`. Its `requirements`
must cover the plan's PRD requirement IDs; its snapshot and commits must match.
The guard commits the report and execution record, and sets the PRD's finished
label only for a complete PASS. Reports have distinct paths, beginning with
`final-audit.md`; `status` identifies the latest one.

After failure, the outer uses `repair-audit SPEC --report /tmp/audit-repairs.json`
to commit reopened or new repair tickets and the updated plan. After exhaustion,
explicit human continuation uses
`continue-audit SPEC --report /tmp/audit-continuation.json`. Ordinary `resume`
does not replenish allowances. Read [audit-repairs.md](audit-repairs.md) for the
decision rules, report schemas, round limits and recovery procedure.
