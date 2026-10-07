# Issue tracker: GitHub

Issues and specs live in GitHub Issues for FuzzyUn1c0rn/agent-skills.
Use the gh CLI from this clone; it infers the repository from origin.

## Operations

- Publish a spec or ticket: create a GitHub issue.
- Create: `gh issue create --title "..." --body-file <path>`.
- Read a ticket and its discussion: `gh issue view <number> --comments`.
- List: `gh issue list --state open --json number,title,body,labels,comments`,
  adding label and state filters as needed.
- Comment: `gh issue comment <number> --body-file <path>`.
- Apply or remove labels: `gh issue edit <number> --add-label "..."`
  or `--remove-label "..."`.
- Close: `gh issue close <number> --comment "..."`.

For multiline bodies, save the text to a temporary file and use --body-file.

## Pull requests as a triage surface

**PRs as a request surface: no.**

GitHub shares issue and PR numbers. If a referenced number is ambiguous,
resolve its type with `gh pr view <number>` and fall back to
`gh issue view <number>`.

## Wayfinding

- Map: one issue labelled `wayfinder:map`, containing Notes,
  Decisions-so-far, and Fog.
- Child: one issue per ticket, linked as a sub-issue of the map.
  Label it `wayfinder:<type>`: research, prototype, grilling, or task.
  If sub-issues are unavailable, list children in the map body and
  put `Part of #<map>` at the top of each child's body.
- Blocking: use native GitHub issue dependencies. Add a blocker with
  `gh api --method POST repos/{owner}/{repo}/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`.
  Obtain the database ID with
  `gh api repos/{owner}/{repo}/issues/<blocker> --jq .id`.
  If dependencies are unavailable, use a `Blocked by: #<number>` line.
- Frontier: choose the first open, unassigned child in map order
  with no open blockers.
- Claim: assign the ticket to the driving developer before working.
- Resolve: comment with the answer, close the ticket, and append a
  summary and link to the map's Decisions-so-far.
