# Worker results

Use these fields for handoffs. `ticket` is the canonical tracker reference.
Supply the actual specification/ticket references, approved bodies and discussion
using [sources.md](sources.md). Only code changes and report destinations use
filesystem paths.
Reference actual command results; do not fabricate test runs.

## Implementer

```json
{
  "outcome": "READY_FOR_REVIEW",
  "ticket": "canonical-ticket-reference",
  "attempt": 1,
  "changed_paths": ["src/example.py", "test/test_example.py"],
  "tdd": [
    {
      "criterion": "AC1",
      "boundary": "Approved public interface",
      "red": {"command": ["python", "-m", "pytest", "test/test_example.py"], "exit_code": 1, "evidence": "Test failed because the requested behavior is absent"},
      "green": {"command": ["python", "-m", "pytest", "test/test_example.py"], "exit_code": 0, "evidence": "Observed passing result"}
    }
  ],
  "checks": [],
  "blockers": []
}
```

Use `BLOCKED` instead when further work needs a decision or unavailable access.
For documentation-only work, replace behavioral TDD evidence with
`tdd_not_applicable_reason` and the actual validation results.

Each attempt's agent ID, implementation result and verifier reports remain in
the run record's ticket `history`. A fresh repair agent receives that evidence
with the current diff and untracked files. Prior green results are context, not
proof that newly changed code passes; repairs still require observed TDD evidence.

## Ticket verifier

```json
{
  "verdict": "PASS",
  "ticket": "canonical-ticket-reference",
  "attempt": 1,
  "base_commit": "full starting SHA",
  "reviewed_snapshot": "fingerprint of the reviewed working tree",
  "criteria": [{"id": "AC1", "satisfied": true, "evidence": "Specific code and test evidence"}],
  "checks": [{"command": ["python", "-m", "pytest"], "exit_code": 0, "evidence": "Observed complete offline suite result"}],
  "blocking_findings": [],
  "advisories": [],
  "unavailable_checks": []
}
```

`PASS` requires every required criterion and check. `REWORK` needs at least one
concrete in-scope finding. `BLOCKED` explains the missing decision or capability.
A finding includes an identifier, affected path, evidence, violated requirement
or rule, and the correction needed. Keep identifiers stable across attempts.

For audit repair work, PASS also includes `resolved_findings`, with one
`{"id": "AUDIT-F01", "evidence": "Actual code and regression-test evidence"}`
entry for every ID assigned in the ticket record's `audit_findings`. Check the
repair itself as well as every original criterion. Prior PASS results are
context, not proof that the defect is corrected.

## Adjudication

Only the outer agent supplies this decision, with the coordinator
idle and all leaves closed. Classify every current blocker, including findings
that were not disputed. Keep the original verifier report intact.

```json
{
  "ticket": "canonical-ticket-reference",
  "attempt": 2,
  "reviewed_snapshot": "fingerprint of the unchanged working tree",
  "previous_workers_inactive": true,
  "decision": "REVERIFY",
  "evidence": "Compared the review, actual code and tests with the approved requirements.",
  "findings": [
    {
      "id": "F1",
      "classification": "advisory",
      "reference": "canonical-ticket-reference#AC1 and applicable repository guidance",
      "evidence": "The required behavior and checks pass; the finding requests an optional naming change."
    }
  ]
}
```

Classifications are `confirmed_blocker`, `advisory`, `unsupported` or
`needs_human`. `REPAIR` requires a confirmed blocker and no unresolved human
decision. `REVERIFY` requires every blocker to be advisory or unsupported;
it requests a fresh verifier, not approval. `BLOCKED` returns the obstacle
to the user. Cite actual evidence, not the illustrative explanation above.

## Final auditor

Use the verifier structure with `audited_commit`, `baseline_commit` and
`requirements` covering the whole specification in place of the ticket-specific fields.
Identify evidence reused from earlier verification and why it remains valid.
Unavailable required checks prevent `PASS`. The outer agent saves the report
and owns specification completion through the configured tracker and its evidence commit.

On subsequent audits, inspect prior findings, the outer's dispositions and all
repair commits while reviewing the whole specification from the original baseline. Use
the same finding ID when the underlying defect persists. The outer plans repairs
through [audit-repairs.md](audit-repairs.md); the auditor remains independent and
leaves implementation and tracker artifacts unchanged.
