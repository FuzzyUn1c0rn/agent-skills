# Audit repairs and human continuation

Read after a failed specification audit, when resuming an audit-blocked run, or
when the user authorizes more work after the repair allowance is exhausted.
The outer owns finding assessment, repair tickets and the updated plan.
The coordinator executes that plan through the existing ticket cycle.

## Assess and plan

1. Close the auditor and all other workflow agents. In current-session mode,
   release any closed coordinator registration using [entry.md](entry.md).
   Keep the checkout lock while planning and running repairs.
2. For a newly returned audit, commit its report using
   `finish SPEC --report /tmp/audit.json`. On resume, reuse the already saved
   audit; an interrupted audit commit uses `reconcile-commit`. Inspect
   `status SPEC` for the latest audit, current snapshot, allowance and remaining
   work. A complete PASS finishes the PRD.
3. Assess every blocking finding against the approved PRD and repository rules.
   Classify it as `confirmed_blocker`, `advisory`, `unsupported` or `needs_human`,
   with requirement references and concrete evidence. Preserve the original
   report. Missing decisions return to the user. Required unavailable checks
   need evidence that the capability or authorization has been restored.
   Permission to continue repairs alone does not authorize live operations.
4. For confirmed defects, reopen a completed ticket whose original acceptance
   criteria are unmet. Create a linked AFK repair ticket for cross-ticket defects
   or missing work within the approved specification. Keep the original
   acceptance criteria and requirements. Record dependencies, testing boundaries,
   related tickets and which findings each repair must resolve. Group one
   finding's correction into one repair ticket; multiple findings may share it.
5. Write the repair plan outside the checkout and call
   `repair-audit SPEC --report /tmp/audit-repairs.json`. The guard validates the
   complete dependency graph, reopens or creates the ticket files, and commits
   the plan and execution record before workers start. The outer supplies new
   ticket content in the repository's format. Use this command instead of editing
   tracker status or saved state by hand.
6. Spawn and register a fresh coordinator as described in `SKILL.md`. Give it
   the updated plan, audit decisions, assigned findings and saved attempt history.
   Each repair uses a fresh implementer, independent verifier and local commit.
   Repair PASS must include evidence for every assigned audit finding as well
   as all original acceptance criteria and required checks.
7. After repairs, close and release the coordinator and start a fresh auditor.
   Review the whole PRD from the original baseline, including earlier completed
   work, repair commits, prior audits and finding dispositions. A ticket's PASS
   does not establish that the full specification now passes.

If all alleged blockers are advisory or unsupported, submit the classifications
with an empty `tickets` list. This requests a fresh full audit of unchanged code;
the outer's decision never grants PASS. It consumes one audit-repair round.

The initial audit is saved as `final-audit.md`. Later audits use
`final-audit-002.md`, `final-audit-003.md`, and so on. Earlier reports remain
unchanged. `status SPEC` identifies the latest report and committed audit.

## Resume a pre-repair-workflow audit

Use the normal skill invocation with `resume` in the original checkout and
branch, and read the current skill instructions from disk. The old audit verdict
`REWORK` was saved under run phase `audit-blocked`. Loading that run retains its
audit and initializes the first bounded audit-repair allowance.

After entry recovery and admission, reuse the saved audit and continue at finding
assessment above. Completed work and attempt history remain intact. This initial
allowance uses `repair-audit`; `continue-audit` is for an exhausted allowance.
If the audit was never persisted, reconcile the actual review evidence and save
it before planning repairs. Later manual commits or checkout changes must be
reconciled before the old audit can be reused.

## Repair plan

Bind the plan to the current post-audit snapshot from `status SPEC`, not the
auditor's pre-commit snapshot. Classify every original blocking finding exactly
once. Every confirmed blocker must appear in exactly one ticket's `finding_ids`.

```json
{
  "audit_number": 1,
  "reviewed_snapshot": "current snapshot from status",
  "previous_workers_inactive": true,
  "evidence": "The auditor, coordinator and all leaf agents have closed.",
  "findings": [
    {
      "id": "AUDIT-F01",
      "classification": "confirmed_blocker",
      "reference": "path/to/PRD.md#US1 and path/to/ticket.md#AC1",
      "evidence": "Concrete reproduction showing the required behavior is missing."
    }
  ],
  "tickets": [
    {
      "action": "reopen",
      "path": "path/to/ticket.md",
      "finding_ids": ["AUDIT-F01"],
      "requirements": ["US1"]
    }
  ]
}
```

A `create` ticket additionally supplies `execution: "AFK"`, `criteria`, `seams`,
`blocked_by`, optional `related_tickets`, and complete Markdown `content` with
exactly one ready `Status:` line. Use the preflight plan's labels. Nonbehavioral
work uses `kind: "documentation"` and follows the usual validation contract.
Behavioral work defaults to `kind: "behavior"` and requires approved `seams`.
The guard appends the audit link, finding IDs and requirement IDs to either
ticket type. It preserves the original ticket text when reopening.

When the audit lists unavailable checks, include `check_resolution` explaining
how they became available and identifying any required authorization. The next
audit still has to run or validly reuse every required check.

If writing or committing the repair plan is interrupted, use `reconcile-commit`.
It resumes the recorded transaction without spending another round. Changed
files, unexpected commits or hooks that alter the planned content require
investigation; they are not accepted as a new plan.

## Allowances and stopping

`audit_repair_rounds` in `settings.toml` defaults to two. Each run records its
limit, so changing settings does not alter an existing allowance. A round is
one repair plan followed by ticket work and a fresh whole-spec audit. The first
audit does not spend a round. An unchanged-code re-audit after outer
reclassification does.

The first audit repair opens a new ticket allowance while retaining all
original implementation attempts and commits. Each ticket has at most three
implementation attempts within that allowance. The same stable audit finding
also has at most three attempts across all its repair tickets in the allowance.
Renaming a ticket or reopening it does not replenish those limits. Keep finding
IDs stable across audits for the same underlying defect.

Repeated or disputed ticket-verifier findings use the existing outer
adjudication. Its one-decision limit applies within the allowance. Previous
decisions remain in history when a new authorized allowance begins.

When a limit is exhausted, save the unresolved findings, remaining ticket work,
attempt evidence, commits and latest audit. Close all agents, release the
checkout entry and report the stop to the user. Include the allowance and round
used, latest report path and what remains. Preserve unfinished source changes.

## Continue after human review

An explicit instruction such as "continue working on the remaining audit
defects" authorizes a new bounded allowance for this run. An interrupted session
or ordinary `resume` keeps its existing allowance. Earlier authorization cannot
be reused to replenish it.

1. Re-enter with `resume` if the entry was released. Reconcile the saved branch,
   HEAD, checkout and inactive workers before changing run state.
2. Resolve any missing requirements decision, unavailable check or permission.
   Continuing work grants repair attempts; it does not answer those questions
   or waive verification.
3. Record the user's actual instruction and call
   `continue-audit SPEC --report /tmp/audit-continuation.json`:

   ```json
   {
     "cycle": 1,
     "reviewed_snapshot": "current snapshot from status",
     "previous_workers_inactive": true,
     "evidence": "Reviewed the stopped run and confirmed all workers closed.",
     "user_authorization": "User's explicit instruction to continue this run"
   }
   ```

   If the exhausted ticket's last implementation, verification or adjudication
   also reported a non-budget blocker, include `blocker_resolution` with the
   actual decision or evidence that resolved it. The user's instruction to
   continue alone does not satisfy this field.

4. If stopped at an audit, plan its remaining findings with `repair-audit`.
   If stopped during ticket repair, send the preserved unfinished work to a
   fresh coordinator. That carried work counts as the first round of the new
   allowance. The next implementation attempt gets a fresh worker and retains
   the original review base, unfinished diff and earlier evidence.
5. Continue the normal repair and audit flow. Stop again if the new allowance
   is exhausted.

The continuation preserves baseline, completed commits, audit reports,
requirements, checks and operation authorizations. Lifetime attempt numbers
continue increasing; each allowance records its own starting point. Completed
tickets stay closed unless the outer's next repair plan explicitly reopens them.
An already-passing `done` run is not reopened by these recovery commands.
