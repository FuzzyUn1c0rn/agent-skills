# Tracker artifacts

Read before preflight, on resume, and before changing tracker state.
Read applicable repository instructions and `docs/agents/issue-tracker.md` first.
Use its configured tools, relationships and operations for every artifact:
specifications, Wayfinder maps, child tickets, dependencies and repair tickets.
They stay in that tracker throughout the run.

## References and preflight

Accept a tracker reference as the invocation's specification argument. Resolve
short IDs against the configured repository/project and save the canonical
reference. Fetch the specification or map, its discussion, and the complete
required child-ticket set, including completed dependencies. Follow native
parent/child and blocking relationships where the configured workflow uses them.

Capture bodies, relevant discussion, revisions or content hashes, acceptance
criteria, AFK eligibility, approved testing boundaries, requirement IDs and the
full dependency graph in the preflight plan. These are execution evidence in
JSON run state; fetching an issue does not create a second issue or specification
in the checkout. Worker handoffs use the canonical references and approved
captures. Significant source changes require reconciliation before more work.

Record `tracker.kind` and the configured read, create, comment, link, reopen and
completion operations. Triage/readiness labels do not determine completion.
Normalize ticket eligibility to `state: "ready"` or `state: "completed"` in the
plan; preserve the actual tracker state separately when useful. Remote writes
retain the existing explicit run-level authorization requirement.

The helpers accept specification and ticket references directly. `spec`, `ref`,
`ticket`, `blocked_by` and `related_tickets` identify tracker artifacts. Only code
paths, helper paths and report destinations are filesystem paths. The helpers
guard execution and local commits; agents call the configured tracker tools.

If repository tracker configuration is absent, use an explicit user-supplied
workflow. Ask only for unresolved workflow or access details. Editing this skill
does not authorize running setup or changing repository configuration.

## Completion and recovery

After a verified ticket commit, the guard saves `pending_publication` containing
the ticket's canonical `ref`, implementation `commit` and stable `marker`.
The coordinator uses that marker when publishing evidence and completing the
actual ticket through the configured tracker. Read back the artifact to confirm
the evidence and resulting state, then call `published` with the matching receipt.
The guard blocks the next ticket and final audit while publication is pending.

A passing final audit enters `publishing`. The outer publishes the audit evidence
and completes the actual specification/map through its configured workflow, then
records the read-back receipt with `published`. Only then does the run reach
`done`. The publication receipt is committed as execution evidence; a Git commit
and a remote state transition are separate operations.

On an uncertain response or interruption, inspect the pending operation and
query the tracker for its stable marker before retrying. Reuse matching evidence
and complete only missing operations. Preserve local commits, attempt counts and
audit allowances. Publication recovery never reruns implementation. An
offline-only run stops with publication pending and reports the required update.

Before advancing, publishing or resuming, check source revisions, discussion,
relationships and states against the approved plan, excluding acknowledged
changes made by this run. Reconcile new blockers and human edits. Keep approved
captures and original evidence; changed requirements need an explicit decision,
not an overwritten live plan.

## Audit repairs

The outer assesses the audit against actual tracker artifacts. Reopen deficient
existing tickets, or create and link repair tickets in that same tracker. Preserve
original acceptance criteria and requirement links. Record stable finding IDs,
dependencies, source revisions and evidence for those tracker operations.

Persist intended creation/reopening and a stable marker in a recovery journal
beneath Git's `implement-spec/` directory before external writes. Record its path
in the plan's `tracker.journal`. After an uncertain outcome, locate the actual
artifact by its marker instead of creating a duplicate. Reopening may change
workflow state and evidence; it does not change approved requirements.

Pass actual canonical repair-ticket references and `tracker_evidence` to
`repair-audit`. The guard commits the updated execution plan and allowances before
workers start. If local plan validation or its commit fails after tracker updates,
retain the journal and reconcile the same artifacts; do not repeat creation or
restart budgets. All subsequent handoffs include the real repair references.

## Selected local Markdown tracker

Only when `tracker.kind` is `local-markdown`, read
[local-markdown.md](local-markdown.md). That conditional resource covers the
configured local artifact conventions. Other trackers use their own native
artifacts and operations through the contract above.
