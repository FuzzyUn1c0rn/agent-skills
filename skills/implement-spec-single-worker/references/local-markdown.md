# Local Markdown tracker

Read only when the repository explicitly selects local Markdown as its issue
tracker. Use `docs/agents/issue-tracker.md` for the specification/map location,
one-artifact-per-ticket convention, relationships and discussion format.
Canonical references are the configured repository-relative artifact paths.

For the existing local helper integration, each specification and ticket has
exactly one top-level `Status:` line. Resolve ready/finished values from repository
rules; use `ready-for-agent`, `closed` and `done` only where those rules are silent.
A fresh run reads these actual tracker artifacts directly. Keep `ref` in the
plan and report identities; do not create execution copies.

The ticket commit updates the actual ticket status with verified work and
execution evidence. A passing audit updates the actual specification status.
These are local tracker transactions, so no remote publication receipt is needed.

For `repair-audit`, a new local ticket supplies `content` in the configured
format, including its ready status. The guard creates or reopens that actual
artifact, appends audit/finding/requirement links, and commits it with the updated
plan. Local paths retain traversal and symlink checks. Keep source requirements
and unrelated content intact.

Existing version-2 local runs and their saved paths remain supported without
migration. Their historical `path` plan field is a local-tracker compatibility
format; new plans use `ref`.
