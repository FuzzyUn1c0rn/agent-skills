# AppSec Jira Field Cheat Sheet

**Project:** VM — "InfoSec (AppSec) VM" (id `13316`), site `zetaglobal.atlassian.net`
**Issue type:** `Bug` (id `13689`) — the only issue type in this project; used for every security finding.
**Last verified:** 2026-08-29, from `getJiraIssueTypeMetaWithFields` (all 33 screen fields, live) + a 25-ticket `*all`-fields JQL sample, cross-checked field-by-field. Two corrections were made from that pass — see the validation note below each affected field.

> Purpose: reference for AI agents generating or validating code/JQL/payloads against the AppSec project. If a create/edit call rejects a value here, re-pull `getJiraIssueTypeMetaWithFields` rather than trusting this doc — option lists can change over time.

A few fields below are marked **"unclear — confirm with Stefan"**. Everything else comes directly from the live field metadata or observed ticket data.

---

## 1. Required fields to create an issue

| Field Key | Display Name | Type | Default | Description |
|---|---|---|---|---|
| `project` | Project | fixed | — | Always `VM` for this project. |
| `issuetype` | Issue Type | fixed | — | Always `Bug` / id `13689`. Single issue type for every finding, not just software bugs. |
| `summary` | Summary | text | — | One-line ticket title. |
| `reporter` | Reporter | user picker | connector's authenticated user | Who filed the ticket. Has a default; don't set unless filing on someone else's behalf. |
| `customfield_31880` | Product | dropdown (single-select) | none | Which Zeta product/brand the finding affects. **Required at creation.** See allowed values below. |
| `customfield_31882` | Source | dropdown (single-select) | none | Where the finding came from (bug bounty, pentest, scanner, etc). **Required at creation.** See allowed values below. |

---

## 2. Dropdown (single-select) fields — exact allowed values

Jira rejects any value that isn't an exact match (case- and punctuation-sensitive). These four (plus the unusable `Category`) are the only true single-select fields on the VM screen — everything else is free text, date, or array.

### Priority — `priority`
Default: **P3** if unset.

| Value | id |
|---|---|
| P1 | 11088 |
| P2 | 11089 |
| P3 | 11090 |
| P4 | 11091 |
| P5 | 11092 |

Description: severity/urgency ranking assigned during triage.

### Product — `customfield_31880`
Default: none. Description: which Zeta product/brand/asset the finding affects.

Allowed values (18): `Marigold (all products)`, `zeta.expr.cd.grow`, `zeta.expr.cd.engage+`, `zeta.expr.cd.loyalty`, `zeta.expr.cd.loyalty.edp`, `zeta.expr.cd.login`, `zeta.expr.lc.liveclicker`, `zeta.expr.st.engage`, `zeta.expr.st.mobile`, `zeta.expr.sl.engage`, `zeta.expr.sl.site`, `zeta.expr.sl.cortex`, `zeta.expr.sl.message.studio`, `zeta.zmp`, `zeta.disqus`, `zeta.whatcounts`, `zeta.liveintent`, `Unknown (TBD)`

### Source — `customfield_31882`
Default: none. Description: how/where the finding was discovered.

Allowed values (11): `Bugcrowd`, `Internal Assessment`, `Customer Reported`, `Internally Reported`, `3rd party Pentest`, `Cobalt.io Pentest`, `DAST (Black Duck)`, `BLA (Black Duck)`, `CVE`, `Other`, `Snyk`

### Taxonomy — `customfield_31885`
Default: none. Description: vulnerability classification/type. Overlaps almost exactly with the `vulnerability-report-analyzer` skill's "Vulnerability Classification" output — pick the closest match if wording differs.

Allowed values (44 — corrected from an earlier miscount of 43; the list itself was already complete and verified byte-for-byte against live `allowedValues`): `Cross Site Scripting (XSS)`, `Insecure Direct Object Referencing (IDOR)`, `Server Side Request Forgery (SSRF)`, `Cross Site Request Forgery (CSRF)`, `SQL Injection (SQLi)`, `Server Security Misconfiguration`, `Lack of Security Headers`, `Sensitive Data Exposure`, `Broken Access Control (BAC)`, `Broken Auth and Session Mgmt`, `Unsafe File Upload`, `Insecure Defaults`, `Insecure Design`, `Insecure Data Transport`, `Denial of Service (DoS)`, `Remote Code Execution (RCE)`, `Open Redirect`, `Subdomain Takeover`, `Enumeration`, `No Rate Limiting`, `Weak 2FA Implementation`, `Using Components with Known Vulnerabilities`, `HTTP Response Manipulation`, `Xml eXternal Entity Injection (XXE)`, `Local File Inclusion (LFI)`, `Remote File Inclusion (RFI)`, `Information Disclosure`, `Application Logic`, `Application Misconfiguration`, `Input Validation Failure`, `Command Injection`, `Content Injection`, `Other`, `HTML Injection`, `Insecure Dependencies`, `Attack Surface Area`, `Defense in Depth`, `Cryptographic Failure`, `Insecure Mass Assignment`, `Race Condition`, `Server-side template injection (SSTI)`, `Client-side template injection`, `Outdated Version`, `Clickjacking`

### Category — `customfield_10042`
Type: select (`option`), but **allowed-values list is empty** on this project. Description: leftover from a generic Jira Work Management template — not configured by the AppSec team. **Do not attempt to set; there is nothing valid to set it to.**

---

## 3. Other on-screen fields (text / text area / date / array)

| Field Key | Display Name | Type | Default | Description |
|---|---|---|---|---|
| `description` | Description | text area | none | Finding narrative. Convention: open with `Asset ID:` / `Asset Name:` / `Location:` header lines, then the writeup. |
| `customfield_31888` | Endpoint | text | none | Specific URL/API endpoint/path where the vulnerability was found. |
| `customfield_31860` | Reproduction Steps | text area | none | Step-by-step instructions to reproduce the finding. |
| `customfield_31850` | Remediation | text area | none | Recommended fix/remediation guidance for engineering. |
| `customfield_31884` | VRT | text area | none | Bugcrowd Vulnerability Rating Taxonomy reference/classification text (typically populated for Bugcrowd-sourced findings). |
| `customfield_31909` | CVSS | text | none | CVSS score and/or vector string for the finding. |
| `customfield_31861` | Source Vuln ID *(was "Vuln ID")* | text | `N/A` | Vulnerability ID assigned by the originating source/scanner (e.g. a CVE ID or scanner finding ID). |
| `customfield_31857` | Bugcrowd Priority | text | none | Priority/severity rating as reported by Bugcrowd (when Source = Bugcrowd). |
| `customfield_31891` | Bugcrowd URL | text | none | Link to the submission on the Bugcrowd platform. |
| `customfield_31858` | Source Status *(was "Black Duck Status")* | text | `N/A` | Status of the finding in its originating scanner/source system (e.g. Black Duck). |
| `customfield_31871` | Source URL *(was "Black Duck URL")* | text | none | Link to the finding in its originating scanner/source system. |
| `customfield_31872` | Pentest ID *(was "BLA ID")* | text | `N/A` | Identifier for the pentest engagement that produced the finding. |
| `customfield_31867` | Program Name | text | none | Name of the bug bounty program or pentest engagement. |
| `customfield_31924` | Payloads Used *(was "Payload (migrated)")* | text area | none | Attack payload(s) / proof-of-concept used to demonstrate the finding. |
| `customfield_31876` | Labels (migrated 2) | array of strings | none | Free-form labels carried over from a migration; supplements standard Jira `labels`. |
| `duedate` | Due date | date (system field) | none | Standard Jira due date. **Corrected:** a 25-ticket live sample showed this populated on 23/25 tickets — the earlier claim (inherited from the skill's own guidance) that "there's no reliable SLA/due-date field populated in practice" does not hold up. Worth re-testing an aging/overdue JQL report against `duedate` directly rather than assuming it's empty. |
| `customfield_31902` | Eng. Close Date | date | none | Date engineering closed out the remediation. Verified: populated on 3/25 sampled tickets (only when remediation has actually closed, as expected). |
| `customfield_31862` | External Creation Date | date | none | Date the finding was originally created in its external/source system (predates the VM ticket). |
| `customfield_10015` | Start date | date | none | Standard Jira start date field. Verified: populated on 24/25 sampled tickets — like Due date, this is actually well-populated in practice. |
| `customfield_10019` | Rank | internal (LexoRank) | none | Jira's internal backlog sort order (Agile ranking). Don't set directly. |

### Standard system fields (standard Jira behavior — not custom)

| Field Key | Display Name | Type | Description |
|---|---|---|---|
| `assignee` | Assignee | user picker | Engineer/analyst currently working the ticket. |
| `attachment` | Attachment | file array | Screenshots, PoC files, scan output, etc. |
| `issuelinks` | Linked Issues | array of issue links | Same-instance issue links (`relates to`, `Duplicate`, `Similar`, etc.) — distinct from remote issue links used for the engineering-link requirement. |
| `parent` | Parent | issue link | Not typically used (single, non-hierarchical issue type). |

That's 33 fields on the VM Bug create/edit screen, verified 1:1 against a live `getJiraIssueTypeMetaWithFields` pull: 11 standard Jira system fields (`assignee`, `attachment`, `description`, `duedate`, `issuelinks`, `issuetype`, `parent`, `priority`, `project`, `reporter`, `summary` — Priority included here since it's schema-type `system`, not a custom field) + 22 custom fields, of which 3 are true dropdowns (Product, Source, Taxonomy), 1 is the unusable dropdown (`Category`), and 18 are plain text/date/array fields.

**Correction:** the original draft of this doc also listed `environment` as an on-screen field. Live metadata shows it is **not** part of the 33-field VM Bug screen — it's a standard Jira field that exists on every issue but isn't exposed here, and it was null on all 25 sampled tickets. Removed from the table above.

---

## 4. Fields that appear in raw ticket data but are NOT on any create/edit screen

These show up when pulling a ticket with `fields: ["*all"]`, but don't appear in `getJiraIssueTypeMetaWithFields` or in a ticket's `editmeta` — there is no supported way to set them via `editJiraIssue`. Across a 60-ticket sample, every one of these was null **except** `customfield_31864`.

| Field Key | Display Name | Type | Description |
|---|---|---|---|
| `customfield_31849` | Severity | legacy | Predecessor to the `priority` field. Not used; null in current tickets. |
| `customfield_31851` | Severity migrated | legacy | Migration artifact of Severity; null. |
| `customfield_31864` | Link issue | legacy link | Populated on 4/25 sampled tickets (not universally null like the rest of this section) — values seen include legitimate cross-site engineering links (e.g. `cmgroup-security.atlassian.net`), not only stale `cheetahdigital.atlassian.net` URLs. Still **don't rely on it alone**: never treat this as satisfying the engineering-link requirement (section 5 of the skill) — cross-check with `getJiraIssueRemoteIssueLinks`, since this field's reliability/freshness is unconfirmed either way. |
| `customfield_31866` | Labels migrated | legacy array | Migration artifact of labels; null. |
| `customfield_31869` | Vuln ID migrated | legacy | Migration artifact of Source Vuln ID; null. |
| `customfield_31922` | Payload | legacy text area | Predecessor to `Payloads Used` (`customfield_31924`); null, superseded. |
| `customfield_10021` | Flagged | legacy (standard Jira "Impediment" flag) | Standard Jira flag/impediment marker; null in practice for this project. |
| `customfield_31907` | Trigger Retest | **unclear — confirm with Stefan** | Not on any screen and null across the sample. Name suggests a flag to request a rescan, but unconfirmed. |
| `customfield_31908` | Release | **unclear — confirm with Stefan** | Not on any screen and null across the sample. Possibly a version/release-tracking leftover from a template. |
| `customfield_31921` | Analysis | **unclear — confirm with Stefan** | Not on any screen and null across the sample. Possibly free-text analysis notes (e.g. from a scanner). |
| `customfield_34489`–`customfield_34493` | Checklist app fields (×5) | **unclear — confirm with Stefan** | From a third-party "Checklist" Jira Marketplace app; null across the sample, structure/purpose unknown. |
| `customfield_34830` | Agent Sessions | **unclear — confirm with Stefan** | Not on any screen and null across the sample. Name suggests tracking of AI-agent session activity against a ticket, but unconfirmed. |

**Guidance for AI agents:** treat all fields in this section as inert/unsupported for writes. Safe to ignore for read purposes too, except `customfield_31864`, which needs the special "don't trust it" handling above.

---

## 5. Status workflow and transition graph

**Status/transition data verified 2026-09-04** (separately from the field metadata above), by sampling one real Issue per status with `searchJiraIssuesUsingJql` and calling `getTransitionsForJiraIssue` on it with `includeUnavailableTransitions: true`, as `smoreas@zetaglobal.com`. Full workings, per-status sample Issue keys and evidence: `docs/research/jira/01-vm-board-transition-graph.md`.

**Re-verified 2026-09-04, later the same day**, after `Invalid` and `Not Applicable` were added to the workflow by hand. That pass re-read `VM-1603` (`Open`) and `VM-1681` (`Done`) in full and confirms: the two new statuses and their transitions are live and global, `Done → In Progress` (`17`) is unchanged, and **the five transition conditions recorded earlier are now gone** (see §5.4).

**Re-verified 2026-09-19** after the importer met the new `Handoff` column during live incremental validation. `GET /rest/api/3/project/VM/statuses` reports `Handoff` as status `13894`, category `In Progress`. Transition `53` is global and lands on `Handoff`; the status then named `Triaged` also offered local transition `54`, `Handoff to engineering`, and `Handoff` offered local transition `13`, `Remediation started`, to `In Progress`. Three Issues were in the column during verification.

**Re-verified 2026-09-24 after the rename:** status `13079` changed from `Triaged` to `Triaging`, and transition `14` changed from `Triage completed` to `Begin triage`. A live project-status read confirmed `Triaging` remains category `In Progress`, and a live transition read confirmed `14` lands on it. `Triaging` means AppSec triage is underway. The separate `Handoff` status means AppSec triage is complete and engineering owns the next step. The status ids and lifecycle classification did not change.

**The starting status for a newly created Issue is `Open` (13073).** Every one of the 742 Issues on the board has been in `Open` at some point (`project = VM AND status WAS NOT "Open"` → 0), and the earliest changelog status item on Issues created years apart departs *from* `Open`.

### 5.1 The 22 statuses

**Corrected 2026-09-04 and 2026-09-19: 16 → 19 → 21 → 22.** Three statuses (`Validation Failed`, `Re-work`, `Pending External Retest`) were missing from earlier versions of this table. Two more (`Invalid`, `Not Applicable`) were then created on 2026-09-04 for the Cobalt importer. `Handoff` was added later and first observed by the importer on 2026-09-19.

**Renamed 2026-09-04:** status `13089` read `Pending black duck retest` and transition `33` read `Trigger whitehat retest`. Both named a vendor that is shut down, and the retest state outlives it, so both went vendor-neutral. `Validation Failed` (13081) and `Re-work` (13082) were reviewed in the same pass and stay as they are — already neutral, confirmed with the board owner.

| Status | id | Category |
|---|---|---|
| Open | 13073 | To Do |
| Backlog (Security Debt) | 13084 | To Do |
| Stale | 13085 | To Do |
| Needs Review | 13086 | To Do |
| Candidate Accepted Risk | 13087 | To Do |
| Triaging | 13079 | In Progress |
| **Handoff** | **13894** | **In Progress** |
| In Progress | 13075 | In Progress |
| Blocked/On Hold | 13076 | In Progress |
| Validation | 13080 | In Progress |
| **Validation Failed** | **13081** | **In Progress** |
| **Re-work** | **13082** | **In Progress** *(inferred — not confirmed in the admin UI)* |
| Pending Prod Release | 13088 | In Progress |
| **Pending External Retest** | **13089** | **In Progress** |
| Done | 13074 | Done |
| Out Of Scope | 13091 | Done |
| False Positive | 13090 | Done |
| Duplicate | 13078 | Done |
| Accepted Risk | 13077 | Done |
| As Designed | 13083 | Done |
| **Invalid** | **13761** | **Done** |
| **Not Applicable** | **13762** | **Done** |

`Pending External Retest` (13089) is **not** a removed status, despite what older notes in this repo claim. It is reachable (transition `33` from `Validation`), 48 Issues have passed through it, and `VM-1061` is in it now. `StatusMap` maps it to `Status.PENDING_RETEST` — a domain name that was deliberately vendor-free from the day it was added, which is why the Board's rename needed no `bl/` change.

**`Invalid` (13761) and `Not Applicable` (13762) are live**, added to the workflow by hand on 2026-09-04 for the Cobalt importer (`Status.SOURCE_INVALID` and `Status.NOT_APPLICABLE`). Both are `statusCategory: done`. Both were empty at verification. Note their ids sit in a different block from the `130xx` statuses and their `description` is empty rather than carrying the `(Migrated on 19 Mar 2026 …)` suffix every pre-existing status has — they are newly created, not reused from elsewhere in the site.

### 5.2 The fourteen global transitions

**Fourteen transitions are `isGlobal: true`, offered from every status.** The eleven originals were byte-identical across all 14 sampled statuses, the two added on 2026-09-04 were confirmed on both `Open` and `Done`, and `Handoff` transition `53` was confirmed on `Open`, the status then named `Triaged`, `Handoff`, and `Done` on 2026-09-19.

| Transition | id | → Status | id | Category |
|---|---|---|---|---|
| Done | 11 | Done | 13074 | Done |
| Backlog (Security Debt) | 25 | Backlog (Security Debt) | 13084 | To Do |
| Stale | 26 | Stale | 13085 | To Do |
| Needs Review | 29 | Needs Review | 13086 | To Do |
| Candidate Accepted Risk | 31 | Candidate Accepted Risk | 13087 | To Do |
| Out Of Scope | 40 | Out Of Scope | 13091 | Done |
| False Positive | 45 | False Positive | 13090 | Done |
| Duplicate | 47 | Duplicate | 13078 | Done |
| Accepted Risk | 48 | Accepted Risk | 13077 | Done |
| As Designed | 49 | As Designed | 13083 | Done |
| Validation | 50 | Validation | 13080 | In Progress |
| **Invalid** | **51** | **Invalid** | **13761** | **Done** |
| **Not Applicable** | **52** | **Not Applicable** | **13762** | **Done** |
| **Handoff** | **53** | **Handoff** | **13894** | **In Progress** |

All fourteen are `hasScreen: false`, `isInitial: false`, and `isConditional: false`. See §5.4 on the conditions that used to be here.

The eight statuses *not* reachable globally: `Open` (13073), `Triaging` (13079), `In Progress` (13075), `Blocked/On Hold` (13076), `Validation Failed` (13081), `Re-work` (13082), `Pending Prod Release` (13088), `Pending External Retest` (13089).

**The globals include self-loops, and `isLooped` does not report them.** An Issue already in `Validation` is still offered transition `50` → `Validation`, and Jira reports `isLooped: false` on it. **Do not use `isLooped` to detect a no-op transition on this board** — only local transition `21` (`Done` → `Done`) sets it true. Guard idempotency on your own recorded state instead (see `docs/adr/0006-status-changes-and-importer-idempotency.md`).

### 5.3 Local (status-specific) transitions

Each row is *in addition to* the fourteen globals. All came back `isAvailable: true`, `isConditional: false`, `hasScreen: false`.

| From | id | Transition | → To |
|---|---|---|---|
| Open (13073) | 14 | Begin triage | Triaging (13079) |
| Open (13073) | 42 | on hold | Blocked/On Hold (13076) |
| Backlog (Security Debt) (13084) | 28 | Start work | Triaging (13079) |
| Stale (13085) | 27 | Reactivate | Triaging (13079) |
| Stale (13085) | 39 | Ready to Validate | Validation (13080) |
| Candidate Accepted Risk (13087) | 32 | Reactivate | Triaging (13079) |
| Triaging (13079) | 4 | Mark as Duplicate | Duplicate (13078) |
| Triaging (13079) | 12 | Revert | **Open (13073)** |
| Triaging (13079) | 13 | Remediation started | In Progress (13075) |
| Triaging (13079) | 54 | Handoff to engineering | **Handoff (13894)** |
| Triaging (13079) | 20 | It's not a bug, it's a feature | As Designed (13083) |
| Triaging (13079) | 41 | Asset not owned by Marigold | Out Of Scope (13091) |
| Triaging (13079) | 46 | Not a vulnerability | False Positive (13090) |
| Handoff (13894) | 13 | Remediation started | In Progress (13075) |
| In Progress (13075) | 2 | Progress is blocked | Blocked/On Hold (13076) |
| In Progress (13075) | 6 | Mark as Accepted Risk | Accepted Risk (13077) |
| In Progress (13075) | 7 | Ready to Validate Fix | Validation (13080) |
| In Progress (13075) | 16 | Revert | Triaging (13079) |
| In Progress (13075) | 34 | Fix release to staging/dev environment. | Pending Prod Release (13088) |
| Validation (13080) | 5 | Validation failed | Validation Failed (13081) |
| Validation (13080) | 9 | Issue Remediated | Done (13074) |
| Validation (13080) | 23 | Revert | In Progress (13075) |
| Validation (13080) | 33 | Request External Retest | Pending External Retest (13089) |
| Validation (13080) | 44 | Fix not deployed | Pending Prod Release (13088) |
| Pending External Retest (13089) | 36 | Issue Remediated | Done (13074) |
| Pending External Retest (13089) | 38 | Revert | Validation (13080) |
| Done (13074) | 15 | Mark as Duplicate | Duplicate (13078) |
| Done (13074) | 17 | **Revert** | **In Progress (13075)** |
| Done (13074) | 21 | Apply resolution | Done (13074) — self-loop, `isLooped: true` |
| Duplicate (13078) | 22 | Revert | **Open (13073)** |
| Accepted Risk (13077) | 8 | Risk no longer accepted | In Progress (13075) |
| Accepted Risk (13077) | 24 | Revert | In Progress (13075) |
| As Designed (13083) | 19 | Revert | Triaging (13079) |
| Out Of Scope (13091) | — | *none* | globals only |
| False Positive (13090) | — | *none* | globals only |

**Reopening a closed finding is possible.** `Done → In Progress` is transition `17`, named `Revert`. Longer revert chains exist: `Done -17→ In Progress -16→ Triaging -12→ Open`.

**Only two edges lead back into `Open`:** `12` from `Triaging` and `22` from `Duplicate`. Nothing else returns to the start column directly.

### 5.4 Caveats and known gaps

- **The transition conditions were removed on purpose, 2026-09-04.** Earlier the same day, five globals reported `isConditional: true` (`11`, `47`, `48`, `49`, `50` — four of them landing in closed columns, which read as a "not just anyone closes a finding" control). **Stefan Moreas removed them by hand**, in the same admin-UI session that added the `Invalid` and `Not Applicable` columns, to simplify the workflow. Every one of the fourteen globals now reports `isConditional: false`, confirmed for the original set on 2026-09-04 and for `Handoff` transition `53` on 2026-09-19. **Not a side effect of the workflow editor, and nothing to restore.** What the conditions used to test was never captured — the API only ever returned the boolean — so that is gone for good. Consequence to know: closing, dismissing or accepting the risk on a finding is no longer gated on group membership.
- **Availability is still not proven for the importer.** Every transition read came back `isAvailable: true` for `smoreas@zetaglobal.com`; the importer's service account has never been tested. With the conditions deliberately gone, the likeliest cause of a surprise here is gone too — no condition can now pass for one account and fail for another — but project permissions still apply. Degrade gracefully when a target is not offered, and watch the logs.
- **Five statuses have no outbound edges recorded**: `Needs Review` (13086), `Blocked/On Hold` (13076), `Validation Failed` (13081), `Re-work` (13082), `Pending Prod Release` (13088). No Issue was in them at verification time, so a transitions sweep cannot see them. Transition ids `1, 3, 10, 18, 30, 35, 37, 43` were never observed and are presumably theirs — so §5.3 is missing roughly eight edges. **Do not read §5.3 as a complete graph.** Two historical edges are known from changelogs: `Validation Failed → Re-work` and `Re-work → Validation`.
- **No transition on this board has a screen** (`hasScreen: false` on all ~180 read), so none collects mandatory input. Validators and post-functions are not exposed read-only; the `Done` transition does appear to set `resolution` via a post-function.
- **`VM` reports as team-managed** (`style: next-gen`, `simplified: true`, migrated 19 Mar 2026) despite the company-managed-style workflow. Admin edits land in the team-managed editor, not the classic workflow designer.
- `getTransitionsForJiraIssue` on the specific Issue remains the source of truth. Fourteen transitions *are* available from every status, but the rest are status-specific and availability is still per-user.
