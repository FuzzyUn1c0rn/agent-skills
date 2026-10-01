# Execution contract

Read this before preflight, after compaction, and when resolving a blocked run.
The outer agent owns interpretation of the specification. The coordinator
executes the approved plan.

## Roles

| Role | Model | Effort | Responsibility |
| --- | --- | --- | --- |
| Outer session | openai.gpt-6-astra | high | Preflight, decisions, final audit and report |
| implementation_coordinator | openai.gpt-6-luna | medium | Dependency order, handoffs, ticket closure and local commits |
| ticket_implementer | openai.gpt-6-sol | high | TDD implementation and scoped repairs |
| ticket_verifier | openai.gpt-6-sol | high | Independent ticket verification |
| spec_auditor | openai.gpt-6-astra | high | Independent verification of the complete specification |

The workflow preset applies to the outer session. Agent profiles apply to
spawned sessions. Ordinary Codex defaults remain unchanged.

## Preflight and branch selection

1. Confirm exclusive use of the checkout. A fresh run requires a clean index
   and working tree, including untracked non-ignored files.
2. Resolve the requested branch before interpreting repository instructions.
   If explicitly supplied, use that branch. Create it from the current commit
   when it does not exist. Otherwise, create a unique `implement/<spec-slug>`
   branch when currently on `main`; use the current branch elsewhere. Refuse
   detached HEAD, invalid names and branch overwrites. Do not fetch, pull,
   reset, push or rewrite commits as part of branch selection.
3. On resume, reconcile the saved run with its repository, branch, HEAD,
   unfinished changes, attempts and active agents. A dirty checkout is allowed
   only when it matches the interrupted run. Preserve mismatched work and
   return the discrepancy to the user.
4. Read the selected branch's applicable AGENTS.md files, tracker instructions,
   architecture decisions, testing guidance, PRD and all required tickets.
5. Resolve the full ticket set and dependency graph. Reject missing
   dependencies, cycles, non-AFK required work, unclear acceptance criteria,
   missing access and unapproved behavior, interface or testing-boundary
   decisions before implementation.
6. Resolve finished-ticket and finished-PRD labels from explicit repository
   rules. Where the tracker is silent, use `closed` for tickets and `done` for
   the PRD. Escalate conflicting explicit rules.
7. Record the plan, baseline commit, branch, ordered tickets, dependencies,
   acceptance criteria, approved testing boundaries, verification commands,
   completion labels and operation authorization. Resolve ordering ties by
   the PRD's explicit order, then ticket path.
8. Establish the offline test baseline. A required check that cannot complete
   or already fails blocks the run; do not silently exclude it.
9. Require current compatibility evidence for named-profile selection,
   effective models and efforts, nested delegation and rejection of a second
   implementation worker. A configuration file or a cooperating lock alone
   is not evidence that the runtime rejects concurrent workers.

Live integration tests, migrations and external-service writes require explicit
run-level authorization. Mention in a ticket is insufficient. Required checks
without authorization block preflight.

## Ticket cycle

The coordinator remains active while its one child works. The outer agent
waits for the coordinator and does not start another worker. The implementer,
verifier and auditor execute their own tasks without delegation.

1. Select the next unfinished ticket whose dependencies have completed commits.
   Record its starting HEAD and increment its persistent attempt count before
   starting implementation.
2. Start a fresh implementer for every attempt, including repairs. Supply the
   ticket, relevant PRD context, approved testing boundaries and the TDD skill
   path. For a repair, also supply the current diff and untracked files, prior
   TDD evidence and stable verifier findings from the saved attempt history.
   Do not resume a closed implementer or assume its earlier context survives.
3. The implementer reads TDD and its applicable references before writing tests.
   For each behavioral slice, observe the test fail for the missing behavior,
   then make it pass. Record commands and actual outcomes. Setup errors do not
   establish the red phase. Documentation-only work records its validation and
   why TDD was inapplicable. Run focused checks during implementation.
4. Wait for the implementer to return. Save its session identifier and full
   structured result in the attempt history, then close its active agent slot
   before starting verification.
5. Start a fresh verifier with the ticket, PRD, repository rules, starting
   commit, current changed and untracked files, test evidence and prior findings.
   The verifier inspects the actual uncommitted changes, checks acceptance,
   correctness, regressions, test quality and documented architecture rules,
   and runs the full supported offline suite. It leaves project source and
   tracker files unchanged; ordinary disposable test output is allowed.
6. Act on the structured verdict:
   - `PASS`: all required criteria and checks completed, no blocking finding.
   - `REWORK`: evidence-backed problems that can be corrected within the agreed
     scope. Close the verifier and submit its report to the guard. Resolve any
     required adjudication before starting a fresh Sol/high repair implementer.
   - `BLOCKED`: missing decisions, unavailable checks, permission failures or
     another obstacle that implementation cannot resolve within scope.
   Invalid, incomplete or contradictory reports are not a pass.
7. Allow the initial implementation and at most two repair attempts. The
   count survives interruption. Repeated findings without progress can stop
   earlier. A blocker or exhausted attempts stops the whole run, including
   otherwise independent tickets.
8. On `PASS`, confirm the reviewed changes still match the checkout, inspect
   the exact diff and file list, update the ticket's status and evidence record,
   and commit that cohesive set locally. Stage explicit paths. The code,
   ticket closure and verification summary belong in the same commit.
   A changed implementation invalidates the pass, including changes introduced
   by formatters or commit hooks. A failed commit does not complete the ticket.
   If a hook commits unreviewed edits, preserve that commit and use the guard's
   invalidation recovery. Keep the ticket unfinished until a fresh verifier
   checks the entire diff from its original review base; never rewrite history.
9. Record the resulting commit and choose the next ticket. Leave the PRD
   unfinished until the final audit passes.

Keep advisory suggestions separate. Concrete defects, unmet criteria and
documented architecture violations can block approval. Style preferences and
unrelated improvements do not create repair work.

## Adjudication

Each ticket gets at most one outer-agent adjudication across the whole run.
The guard queues it when a blocking finding ID recurs. This is deliberately
conservative: the outer agent determines whether a repair made sufficient
progress. Keep IDs stable for the same underlying problem; changing an ID does
not make an old disagreement new. The coordinator must also call `dispute` before
another repair when it or the implementer contests a finding, even on attempt one.

Close the verifier and all other leaves first. The coordinator returns the
request and remains open but idle. The outer Astra/high agent adjudicates
directly, without another sub-agent or source edits. Give it the ticket, approved
PRD, repository rules, current diff, actual check results, original reports,
attempt history and dispute evidence.

The outer agent classifies every current blocker as `confirmed_blocker`,
`advisory`, `unsupported` or `needs_human`, citing the relevant requirement or
repository rule and concrete evidence. A preferred design or naming change is
not a blocker without an applicable rule. Do not invent requirements to settle
a dispute. Choose one outcome and record it with `adjudicate`:

- `REPAIR`: give a fresh implementer the confirmed blockers and decision.
  It consumes the next existing attempt. No remaining attempt means BLOCKED.
- `REVERIFY`: all alleged blockers were advisory or unsupported. Run one fresh
  independent verification of the unchanged code with the decision as context.
  This does not consume an implementation attempt or grant PASS.
- `BLOCKED`: a human decision or other unresolved obstacle prevents continuation.

Adjudication changes neither acceptance criteria nor required checks. The fresh
verifier must still meet the full PASS contract. It should not repeat rejected
preferences as blockers without new evidence; genuinely discovered defects
still block. Another repeated or disputed finding after adjudication stops the
whole run for the user, not another adjudication. Explicit user resolution may
resume eligible work but never resets the adjudication or implementation budget.

## Recovery

Keep the human-readable execution record beside the PRD. Record the run's
baseline, planned tickets, current ticket, attempts, worker identifiers,
verification evidence and completed commits. Runtime bookkeeping and verbose
logs may live under the repository's Git directory.

After interruption, inspect the record, branch, HEAD, index, changed files and
agent lifecycle state. Confirm old workers are inactive before resuming. Do not
reset files, restart attempt counts or accept an interrupted verification.
Reconcile a commit that succeeded just before interruption against the actual
commit and ticket status before recording it as complete.

Only the outer Codex session is resumed. Do not resume closed sub-agents:
the tested runtime can replace their model settings with their parent's.
After confirming old children and coordinator are inactive, spawn a fresh
coordinator with the saved run. Reuse a completed implementation result only
when it matches the current attempt and checkout; rerun interrupted verification
with a fresh verifier. An incomplete implementation attempt is recorded as
`BLOCKED`, then resolved to `rework` only after reconciliation. Its replacement
consumes the next attempt; interruption never grants extra attempts.

## Final audit

After all required ticket commits exist, the coordinator reports the results
and releases its active agent slot. The outer agent starts `spec_auditor`.

The auditor reviews the whole change from the recorded baseline against the
PRD, all completed tickets and relevant repository rules. It verifies
cross-ticket behavior, requirements coverage and architecture. It may reuse
test evidence only when it applies to the exact audited code and environment.
Run additional checks where evidence is missing.

Return the audited commit, requirements-to-evidence mapping, performed and
reused checks, blocking findings, advisory findings and unavailable checks.
The auditor reports findings and does not change implementation or tracker files.

The outer agent saves `final-audit.md` beside the PRD and commits that report
locally even when there are blockers. Mark the PRD finished only when required
verification is complete and no blocking finding remains. Advisory findings
do not block completion. Leave completed tickets closed until the user decides
how to handle audit findings. Do not start an automatic audit-repair cycle.

Report completed commits, audit outcome, remaining blockers and the report
path to the user.
