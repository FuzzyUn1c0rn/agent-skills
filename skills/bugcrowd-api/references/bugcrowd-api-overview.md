# Bugcrowd REST API (v1.1.0) — Overview

This document provides a structured overview of all 52 operations across 37 paths defined in the
Bugcrowd REST API OpenAPI specification, plus the 4 outgoing webhook events. Endpoints are grouped
by resource, mirroring the `*_resource` tags in the spec. For full request/response schemas,
parameters, and enum values, search `references/api-spec.yaml`.

Everything is served from `https://api.bugcrowd.com`. The API follows the
[JSON:API](https://jsonapi.org/format/) specification — see SKILL.md for the request/response
envelope, headers, pagination, sparse fieldsets, and filter/sort conventions.

Resource IDs are UUIDs everywhere **except**: `filter[program]` and `filter[engagement]` on
submissions take short *codes*, and the `program_id` path segment of `/programs/{program_id}/targets`
accepts either a UUID or a program code.

---

## 1. Submissions

The core resource: a vulnerability report against a program. This is the resource most integrations
are built around.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/submissions` | List/search submissions with `filter[...]`, `sort`, `include`, `fields[...]`, `page[...]`. |
| `POST` | `/submissions/search` | Same 20 filters as `GET /submissions`, sent as a JSON body (`{filter, sort, page, include}`) to escape URL length limits. Read-only. Values must be JSON arrays, and **`fields` is silently ignored** — you always get the full payload back. |
| `POST` | `/submissions` | Create a submission in a program. Requires `title` + `description` attributes and a `program` relationship. |
| `GET` | `/submissions/{id}` | Fetch one submission. |
| `PATCH` | `/submissions/{id}` | Update a submission (state, severity, assignees, VRT, duplicate_of, custom fields, …). |
| `GET` | `/submissions/{id}/comments` | List comments on a submission. `filter[visibility_scope]`, paginated. |
| `GET` | `/submissions/{id}/activities` | List activity-feed entries for a submission. `filter[key]` (e.g. `submission.created`), paginated. |

### Submission states (`SubstateEnum`)

`new`, `triaged`, `unresolved`, `resolved`, `informational`, `out_of_scope`, `not_applicable`,
`not_reproducible`

> **`filter[state]` uses hyphens, attributes and write payloads use underscores.**
> Filter: `filter[state]=out-of-scope,not-applicable`. Read/write attribute: `"state": "out_of_scope"`.

Verified: these eight states are exhaustive and mutually exclusive — a per-state census sums exactly
to the unfiltered `total_hits`, so every submission is in exactly one and none is null. `new` means
untriaged; `triaged` is a short-lived transient state and is frequently empty.

Each state has a corresponding read-only timestamp attribute:
`last_transitioned_to_triaged_at`, `last_transitioned_to_unresolved_at`,
`last_transitioned_to_resolved_at`, `last_transitioned_to_informational_at`,
`last_transitioned_to_out_of_scope_at`, `last_transitioned_to_not_applicable_at`,
`last_transitioned_to_not_reproducible_at`.

### Severity

Integer `1`–`5` mapping to Bugcrowd priority **P1–P5, where 1 is the most severe** (P1 = critical,
P5 = informational). Nullable. This is the inverse of most severity scales — do not sort or compare
it as if higher meant worse.

`filter[severity]` is capped at `maxItems: 4` even though five values exist, so "all severities" is
unexpressible — omit the filter. Note also that most submissions have `severity: null` (verified: 217
of 1140), and a `null` severity is excluded by *any* `filter[severity]` with no way to filter for it.
New reports arrive with `severity: null`, so combining `filter[state]=new` with `filter[severity]`
reliably returns nothing.

### Source (`SourceEnum`)

`api`, `csv`, `platform`, `qualys`, `external_form`, `email`, `jira`, `customer_source`

### `fields[submission]` — selectable attributes and relationships

Attributes: `bug_url`, `custom_fields`, `description`, `duplicate`, `extra_info`, `http_request`,
`last_activity_feed_item_created_at`, `last_transitioned_to_*_at` (7 fields, see above),
`remediation_advice`, `severity`, `source`, `state`, `submitted_at`, `title`, `vrt_id`,
`vrt_version`, `vulnerability_references`

Relationships: `active_blocker`, `active_researcher_request_response`, `activities`, `assignee`,
`assignees`, `claim_ticket`, `comments`, `cvss_vector`, `duplicate_of`, `duplicates`, `engagement`,
`engagement_brief`, `external_issues`, `file_attachments`, `monetary_rewards`, `program`,
`researcher`, `target`

### `include` (`SubmissionIncludeEnum`)

`activities`, `activities.actor`, `activities.event`, `active_blocker`,
`active_researcher_request_response`, `assignee`, `assignees`, `claim_ticket`, `comments`,
`comments.author`, `comments.file_attachments`, `cvss_vector`, `duplicates`, `duplicate_of`,
`external_issues`, `file_attachments`, `monetary_rewards`, `monetary_rewards.payments`, `program`,
`program.organization`, `engagement`, `engagement_brief`,
`engagement_brief.engagement_brief_target_groups`, `researcher`, `target`

### Filters on `GET /submissions` / `POST /submissions/search`

| Filter | Accepts |
|---|---|
| `filter[program]` | up to 10 **program codes** (not UUIDs) |
| `filter[engagement]` | up to 10 **engagement codes** |
| `filter[state]` | `new`, `triaged`, `unresolved`, `resolved`, `informational`, `out-of-scope`, `not-applicable`, `not-reproducible` (hyphens) |
| `filter[severity]` | up to 4 integers in 1–5 |
| `filter[source]` | any of the `SourceEnum` values |
| `filter[assignee]` / `filter[assignees]` | up to 10 of: email address, `me`, `none` |
| `filter[researcher]` | up to 10 researcher usernames |
| `filter[target]` | up to 1000 target names |
| `filter[target_type]` | `website`, `api`, `ios`, `android`, `iot`, `hardware`, `network`, `other`, `ip_address`, `collection` |
| `filter[duplicate]` | boolean |
| `filter[vrt]` | dot-separated VRT id, e.g. `cross_site_scripting_xss` |
| `filter[search]` | free text over title, description, and comment text |
| `filter[blocked_by]` | `present`, `none`, `bugcrowd-operations`, `customer`, `researcher` (hyphens) |
| `filter[payments]` | `present`, `none` |
| `filter[points]` | `present`, `none` |
| `filter[retest]` | `pending`, `completed`, `patched`, `failed`, `present`, `none` |
| `filter[submitted]` | date, or a range: `from.2021-02-28,to.2021-03-01` |
| `filter[updated]` | date, or a `from.`/`to.` range |
| `filter[last_activity_feed_item_created_at]` | date, or a `from.`/`to.` range |

`sort`: up to 6 of `submitted-asc`, `submitted-desc`, `severity-asc`, `severity-desc`,
`updated-asc`, `updated-desc` (verified against production). The sort keys are **not** attribute
names — `submitted` sorts the `submitted_at` attribute, and `updated` has no corresponding attribute
in the response at all. There is no `created_at` sort key here, unlike `GET /engagements`.

Verified: `filter[program]` and `filter[engagement]` return `total_hits: 0` — not a `400` — for an
unknown code *or* for the resource's genuine UUID. Every other filter above rejects a bad value with
a `400` that enumerates the accepted ones.

**To enumerate a program's reports, filter by program, not engagement.** Engagement attribution is
sparse: verified, only 3 of one program's 890 submissions were linked to an engagement at all, with
`relationships.engagement` `null` on the rest and 8 of the program's 9 engagements returning zero
submissions. `filter[engagement]` narrows within a live engagement; it does not partition a backlog.

### Attributes gated on direct program access

`title`, `description`, `bug_url`, `extra_info`, `http_request`, `custom_fields`, and
`remediation_advice` are only populated when the credential has access to that submission's program.
Without it, `title` reads literally `"Original submission in another program"` — treat that exact
string as "redacted", not as data.

### `POST /submissions` body

`data.type` must be `submission`. Required attributes: `title`, `description`. Required
relationship: `program`. Optional relationships: `engagement`, `target`.

Optional attributes: `bug_url`, `custom_fields` (object of string→string, labels configured in the
UI), `extra_info`, `http_request`, `researcher_email`, `severity` (1–5, nullable), `state`,
`submitted_at`, `vrt_id`, `cvss_string`.

`cvss_string` must match `^CVSS:(3\.[01]|4\.0)/.*$` — for example
`CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:L` or
`CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N`.

### `PATCH /submissions/{id}` body

`data.type` must be `submission`. Settable attributes: `bug_url`, `custom_fields`, `http_request`,
`remediation_advice`, `severity`, `state`, `title`, `vrt_id`, `vulnerability_references`.
Settable relationships: `assignee` (nullable), `assignees` (max 20 identities), `cvss_vector`,
`duplicate_of` (nullable).

Note that `description`, `extra_info`, and `submitted_at` are **not** patchable — they can only be
set at creation.

---

## 2. Programs

A program is the ongoing engagement container that submissions belong to. Identified by a UUID, but
also has a human-readable `code` used by `filter[program]`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/programs` | List programs. `filter[organization_id]`, `sort`, `include`, paginated. |
| `GET` | `/programs/{id}` | Fetch a program. |
| `GET` | `/programs/{program_id}/targets` | List a program's targets with vulnerability and engagement rollups. Accepts a UUID **or a program code** as `program_id`. |

`fields[program]`: `code`, `name`, `organization`, `engagements`, `submissions`
`include`: `organization`, `submissions`, `engagements`
`sort`: `promoted-asc/desc`, `starts-asc/desc`, `ends-asc/desc`, `name-asc/desc`, `reward-asc/desc`

### `GET /programs/{program_id}/targets` — different conventions from the rest of the API

This endpoint returns `type: program_target` objects with attributes `name`, `category`,
`url_location`, `tags`, `priority`, `coverage`, `vulnerabilities`
(`{vulnerability_count, priority_stats}`), and `engagements_data`
(`{engagements_count, engagements_details}`). Response `meta` carries `total_hits` and `count`.

The spec misdescribes this endpoint in three ways. Verified against production:

- `sort` is documented as a free-form string with `example: -created_at`, but the server enforces the
  **`/programs` sort enum** (`promoted-asc/desc`, `starts-asc/desc`, `ends-asc/desc`,
  `name-asc/desc`, `reward-asc/desc`). `-created_at` and `created_at-desc` both return `400`.
- Its filters are marked `explode: true`, but comma-joining is what works; repeating the parameter
  silently keeps only the last value.
- It does not validate filter enums — a bogus `filter[category]` returns `200` with `total_hits: 0`
  rather than `400`.

Filters: `filter[category]` (`api`, `website`, `ios`, `android`, `iot`, `hardware`, `network`,
`other`, `ip_address`, `collection`), `filter[priority]` (`1`–`4` or `p1`–`p4`),
`filter[coverage]` (`in_scope`, `out_of_scope`, `not_assigned`), `filter[status]` (`open`,
`archived`). This is also the only operation in the spec that documents a `401` response.

---

## 3. Engagements

A time-boxed piece of work within a program (bounty, pentest, etc.), with a brief describing scope
and rewards. Read-only through the API.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/engagements` | List engagements. `sort` accepts `created_at-asc` or `created_at-desc`. Paginated. **No filter parameters exist** — passing any `filter[...]` is a `400`. |
| `GET` | `/engagements/{id}` | Fetch an engagement. |

**The parent program is the `bounty` relationship**, which is typed `program` — there is no `program`
relationship on an engagement. Since `/engagements` cannot be filtered, scope it to one program either
with `GET /programs/{id}?include=engagements` (capped at 100) or by grouping a full `/engagements`
listing on `relationships.bounty.data.id`.

`fields[engagement]`: `id`, `code`, `state`, `engagement_type`, `starts_at`, `ends_at`,
`expected_completed_at`, `last_transition_at`, `paused_reason`, `cancellation_reason`, `created_at`,
`updated_at`, `engagement_brief`, `bounty`, `submissions`

`include`: `engagement_brief`, `engagement_brief.engagement_brief_target_groups`,
`engagement_brief.engagement_brief_target_groups.reward_range`,
`engagement_brief.engagement_brief_target_groups.targets`, `submissions`

`engagement.state` is a free-form string in the schema (no enum) — read the value and branch
defensively rather than hardcoding a list, and likewise for `cancellation_reason` and
`paused_reason`. Values observed in production: `draft`, `launching`, `in_progress`. Note these do
**not** match the pentest-style lifecycle (`planned`/`live`/`closed`) used by other vendors' APIs.

`engagement_type` is a nested object, not a string: `{id, name, allowed_methodologies,
allowed_participations, reward_allocation_type, point_schema, enabled_reports, final_report,
timeboxed, …}`. Its real shape exceeds the spec: despite `additionalProperties: false`, production
returns roughly a dozen undocumented keys (`allow_listing`, `credentials_enabled`,
`decommissioned_at`, `customer_invites_enabled`, `reserved_funds_enabled`,
`allowed_crowd_selection_strategies`, `platform_submissions_enabled`, `brief_enabled`,
`external_submission_form_enabled`, `created_at`, `updated_at`) while the documented
`enabled_reports` key is **absent**. Read `engagement_type.name` for the human label (e.g.
`"Bug Bounty"`, `"Vulnerability Disclosure"`) and parse defensively — validating a response against
the spec's schema will fail on valid data.

**The type name is not the UI label.** The API reports `"Vulnerability Disclosure"`, while Bugcrowd's
commercial name is "Vulnerability Disclosure Essentials"; the "Essentials" wording survives only as
an `-ess` suffix on some engagement *codes*, and not all of them. Match on `engagement_type.id` or
`engagement_type.name`; the code does not encode the type.

`fields[engagement_brief]`: `id`, `name`, `tagline`, `description`, `additional_information`,
`targets_overview`, `collaboration_enabled`, `coordinated_disclosure`, `crowdstream_visible`,
`safe_harbor_status`, `share_known_issues`, `engagement`, `engagement_brief_target_groups`

`fields[target_group]`: `name`, `description`, `in_scope`, `reward_range`, `engagement_brief`, `targets`

`fields[reward_range]`: `p1_min_cents`/`p1_max_cents` … `p5_min_cents`/`p5_max_cents`,
`program_max_cents`

---

## 4. Targets

Testable assets belonging to an organization. The top-level collection is read-only; per-program
target data with rollups lives at `GET /programs/{program_id}/targets` (section 2).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/targets` | List targets. `filter[organization_id]`, `include=organization`, paginated. |

`fields[target]`: `name`, `category`, `organization`, `submissions`
Categories (`TargetTypeEnum`): `website`, `api`, `ios`, `android`, `iot`, `hardware`, `network`,
`other`, `ip_address`, `collection`

---

## 5. Organizations, members, and program roles

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/organizations` | List organizations you can access. Start here to discover org UUIDs. |
| `GET` | `/organizations/{id}` | Fetch an organization. `include=programs,targets`. |
| `GET` | `/organizations/{id}/members` | List org members with their access grants. Paginated. |
| `GET` | `/organizations/{id}/members/{member_id}` | Fetch one org member. |
| `PATCH` | `/organizations/{id}/members/{member_id}` | Change a member's role. Body: `{data: {type: "organization_member", attributes: {role}}}`. |
| `DELETE` | `/organizations/{id}/members/{member_id}` | Remove a member from the organization. `204`. |
| `GET` | `/organizations/{id}/program_roles` | List per-program role grants. `filter[user_id]`, `filter[program_id]`. |
| `POST` | `/organizations/{id}/program_roles` | Grant a program role. Body needs `attributes.role` plus `program` and `user` relationships. |
| `DELETE` | `/organizations/{id}/program_roles/{program_role_id}` | Revoke a program role. `204`. |

`fields[organization]`: `name`, `programs`, `targets`
`fields[organization_member]` (`MemberFields`): `name`, `email`, `access_grants`
`fields[organization_program_role]`: `name`, `email`, `program_name`, `program_code`, `role`

Organization roles: `owner`, `org_admin`, `member`, `test_operator`
Program roles: `admin`, `analyst`, `viewer`
`OrganizationOrProgramRolesEnum` (used for member updates and invitations) is the union of both.

---

## 6. Access invitations

Invite a user by email to an organization and/or specific programs. The roles are supplied as
`resource_role` objects in the JSON:API `included` array, not inside `data`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/access_invitations` | List invitations. `filter[organization_id]`, `filter[grantee_email]`, `include`, paginated. |
| `POST` | `/access_invitations` | Create an invitation. Requires `data` (type `access_invitation`, `attributes.grantee_email`, `relationships.organization`) **and** `included` (one or more `resource_role` objects carrying `attributes.role`). |
| `DELETE` | `/access_invitations/{id}` | Revoke an invitation. `204`. |

`fields[access_invitation]`: `approved_at`, `created_at`, `grantee_email`, `granting_identity`,
`organization`, `resource_roles`

---

## 7. Teams

Groups of users that can be granted program roles collectively.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/teams` | List teams. `include=team_members,roles`, paginated. |
| `POST` | `/teams` | Create a team. Requires `name` + `description` attributes and an `organization` relationship. |
| `GET` | `/teams/{id}` | Fetch a team. |
| `DELETE` | `/teams/{id}` | Delete a team. `204`. |
| `GET` | `/teams/{id}/members` | List team members. Paginated. |
| `POST` | `/teams/{id}/members` | Add a member. Body: type `team_member` with a `user` relationship. |
| `GET` | `/teams/{id}/members/{member_id}` | Fetch a team member. |
| `DELETE` | `/teams/{id}/members/{member_id}` | Remove a team member. `204`. |
| `POST` | `/teams/{id}/roles` | Grant the team a program role. Body: type `team_role`, `attributes.role` (`admin`/`analyst`/`viewer`), `relationships.program`. |
| `DELETE` | `/teams/{id}/roles/{role_id}` | Revoke a team role. `204`. |

`fields[team]`: `name`, `description`, `team_members`, `roles`
`fields[team_member]`: `name`, `email`, `access_grants`
`fields[role]`: `role`, `resource`, `resource_type`

---

## 8. Comments

Comments are created through a top-level endpoint but read through the submission sub-resource.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/comments` | Create a comment on a submission. Requires `attributes.body`, `attributes.visibility_scope`, and a `submission` relationship. |
| `GET` | `/submissions/{id}/comments` | List a submission's comments (see section 1). |

`visibility_scope` (required on create): `everyone`, `bugcrowd_and_researcher`,
`bugcrowd_and_customer`, `customer`, `bugcrowd`

This is a disclosure decision, not a formality: `everyone` is visible to the researcher, while
`customer` and `bugcrowd` are internal-only. Choose deliberately, and default to the narrowest scope
that accomplishes the task.

`fields[submission_comment]`: `body`, `created_at`, `visibility_scope`, `author`, `file_attachments`
`fields[comment]` (when included from a submission): `body`, `created_at`, `visibility_scope`,
`author`, `file_attachments`

---

## 9. Monetary rewards and payments

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/monetary_rewards` | Reward a submission. Requires `attributes.amount_cents` (≥ 1) and a `submission` relationship; optional `comment`. |
| `GET` | `/monetary_rewards/{id}` | Fetch a reward. `include` payments, submission, funding_pool, identities. |
| `PATCH` | `/monetary_rewards/{id}` | Cancel a reward. Requires **both** `attributes.cancelled` and `attributes.cancellation_reason`; optional `cancellation_comment`. |

`cancellation_reason`: `amount_incorrect`, `bounty_incorrect`, `expired`,
`handled_outside_platform`, `other`, `researcher_incorrect`

`fields[monetary_reward]`: `amount_cents`, `formatted_amount`, `comment`, `reason`, `created_at`,
`rewarded_at`, `cancelled`, `cancelled_at`, `cancellation_reason`, `cancellation_comment`,
`submission`, `rewarded_by`, `cancelled_by`, `payments`, `funding_pool`

`fields[payment]`: `amount_cents`, `created_at`, `remitted_at`, `monetary_reward`, `researcher`
`fields[funding_pool]`: `pool_balance`, `funding_pool_type`, `pending_deposit_balance`,
`cumulative_program_balance`, `organization_pool_balance`, `total_available_funding_balance`

Amounts are always in **cents** (integers). There is no list endpoint for monetary rewards — reach
them via `include=monetary_rewards` on submissions.

---

## 10. Credentials and credential buckets

Buckets hold pools of researcher credentials (test accounts) for a program; credentials are
individual entries that can be assigned to researchers.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/credential_buckets` | List buckets. **`filter[program_id]` is required.** |
| `POST` | `/credential_buckets` | Create a bucket. Requires `name`, `credential_type`, `credentials_per_researcher`, `is_ready`, `description`; optional `low_balance_threshold` and a `program` relationship. |
| `GET` | `/credential_buckets/{id}` | Fetch a bucket. `include=credentials`. |
| `PATCH` | `/credential_buckets/{id}` | Update a bucket. Requires `name`, `credentials_per_researcher`, `is_ready`, `description` on every call — effectively a full replace. |
| `POST` | `/credentials` | Create a credential. Requires a `credential_bucket` relationship; optional `user`. |
| `GET` | `/credentials/{id}` | Fetch a credential. |
| `PATCH` | `/credentials/{id}` | Set `attributes.state` to `recycle` or `archive`. |
| `DELETE` | `/credentials/{id}` | Delete a credential. `204`. |
| `POST` | `/credentials/assign` | Assign credentials to the caller. Requires `attributes.requested_quantity` (1–100). |

`credential_type`: `email` or `text`
`fields[credential_bucket]`: `credential_type`, `credentials_per_researcher`, `description`,
`is_ready`, `low_balance_threshold`, `name`, `credentials`, `bounty`
`fields[credential]`: `credential_bucket_id`, `user_id`, `data`

---

## 11. Claim tickets

A claim ticket lets a researcher claim ownership of a submission that arrived through a channel
without an attributed researcher (API, email, external form, CSV).

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/claim_tickets` | Create a claim ticket. Requires a `submissions` relationship containing **exactly one** submission. |

`fields[claim_ticket]`: `status`, `claimed_at`
`status`: `claimed`, `expired`, `pending`

---

## 12. Disclosure requests

Researcher requests to publicly disclose a resolved submission.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/disclosure_requests` | List disclosure requests. `filter[status]`. Not paginated. |

`fields[disclosure_request]`: `status`, `disclosure_level`, `created_at`, `responded_at`,
`approved_by`, `submission`
`filter[status]`: `requested`, `draft`, `denied`, `approved`, `cancelled`

---

## 13. Audit logs

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/authentication_logs` | Platform access history. `filter[organization_id]`, `filter[start_date]`, `filter[end_date]`, paginated. |
| `GET` | `/authorization_logs` | Authorization/role-change history. `filter[organization_id]`, `filter[start_date]`, `filter[end_date]`. **Not paginated.** |

`fields[authentication_log]`: `time`, `actor`, `action`, `ip_address`, `reason`
`fields[authorization_log]`: `time`, `actor`, `object`, `action`, `attribute`, `resource`

---

## 14. Resources reachable only via `include`

These have no endpoints of their own; request them as `include=` targets on submissions (or other
parents) and shape them with `fields[...]`.

| Resource | `fields[...]` key | Selectable fields |
|---|---|---|
| Activity | `activity` / `submission_activity` | `created_at`, `key`, `actor`, `event`, `program`, `submission` |
| Event | `event` / `submission_activity_event` | `created_at`, `key`, `data`, `resource`, `actor` |
| Blocker | `blocker` | `unblocked_at`, `blocked_by`, `reason`, `resource` — `blocked_by`: `bugcrowd_operations`, `customer`, `researcher` |
| Researcher request response | `researcher_request_response` | `reason`, `requested_to`, `description`, `created_at`, `replied_at` |
| CVSS vector | `cvss_vector` | `version`, `score`, `attack_vector`, `attack_complexity`, `attack_requirements`, `privileges_required`, `user_interaction`, `authorization_scope`, `confidentiality_impact`, `integrity_impact`, `availability_impact`, `vulnerable_confidentiality`, `vulnerable_integrity`, `vulnerable_availability`, `subsequent_confidentiality`, `subsequent_integrity`, `subsequent_availability` |
| File attachment | `file_attachment` | `file_name`, `file_size`, `file_type`, `s3_signed_url`, `download_url`, `parent` |
| External issue | `external_issue` | `remote_id`, `remote_url`, `integration`, `resource` — `integration`: `jira_integration`, `qualys_integration`, `ibm_resilient_integration`, `github_integration`, `service_now_integration`, `azure_dev_ops_integration`. Verified unreachable in practice: a submission reported `relationships.external_issues` with `data: []` and empty `included` even under `include=external_issues`, while `links.related.meta` claimed `{count: 1}` — and there is no external-issues endpoint to fall back on |
| Identity | `identity` | `name`, `email`, `staff` |

`file_attachment.download_url` is stable, but the authenticated `302` behind it may be replayed by
Bugcrowd's Varnish edge after its 10-second S3 signature has expired. Verified on 2026-09-15:
`Cache-Control: no-cache` did not help, while a fresh unknown query parameter forced a cache miss for
both tested files. Rebuild each acquisition URL from the pinned `files.bugcrowd.com` host and the
trusted file id, then add a new nonce on every attempt. Never log or retain the S3 redirect.

The spec also defines schemas with no corresponding paths in this version —
`CreateProgramRequest`, `CreateTargetRequest`, `CreateOrganizationRequest`, `CreateIdentityRequest`,
`CreateRewardRangeRequest`, `CreateAccessGrantRequest`, `LinkExternalIssueRequest`,
`UpdateExternalIssueRequest`, `ListAccessGrantsResponse`, `ListExternalIssueResponse`,
`UpdateMonetaryTransferRequestPayload`. Do not assume the corresponding endpoints exist; there is no
documented path for them here.

---

## 15. Outgoing webhooks

Bugcrowd delivers these as `POST` requests to a consumer URL configured per program under
**Settings → Integrations → Outgoing Webhooks**. They are not endpoints you call. Requires API
version `2021-10-28` or later.

| Event key | Payload `data.attributes.data` |
|---|---|
| `submission.created` | Submission snapshot; `included` carries the `submission` and `identity`. |
| `submission.updated` | `{changes: {<field>: {from, to}}}` — only the fields that changed. |
| `blocker.created` | `{blocked_by: ...}` — one of `bugcrowd_operations`, `customer`, `researcher` |
| `blocker.updated` | `{blocked_by: ...}` — same shape as `blocker.created` |

Payload shape: `{data: <event resource>, included: [...]}` where the event resource has
`type: "event"`, `attributes: {created_at, key, data}`, and `relationships: {actor, resource}`.

Verification: the `X-Bugcrowd-Digest` request header has the form
`timestamp=<value>;sha256=<hex>`, where the hex is `HMAC-SHA256(secret, raw_body + timestamp)`.
Compare with a constant-time comparison, and reject stale timestamps — see SKILL.md § Webhooks for
the full verification procedure.
