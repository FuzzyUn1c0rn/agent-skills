# Cobalt API (v2) — Overview

This document provides a structured overview of all 72 endpoints defined in the Cobalt v2 OpenAPI specification. Endpoints are grouped by functional theme, mirroring the tags defined in the spec. For full request/response schemas, parameters, and enum values, search `references/api-spec.yaml`.

Unless noted otherwise, every endpoint below is scoped to the organization specified in the `X-Org-Token` header.

## 1. Organizations

Endpoints for listing the organizations you belong to. Not org-scoped — this is how you obtain the `X-Org-Token` value used by every other endpoint.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs` | List all organizations you belong to. Save the `token` field from the org you want to operate on — pass it as `X-Org-Token` on subsequent calls. |

## 2. Assets

Assets are the applications, networks, or systems that are targets for security testing (types: `api`, `cloud_config`, `external_network`, `internal_network`, `mobile`, `web`, `web_plus_api`, `web_plus_mobile`, `wireless_network`, `iot`, `thick_client`, `physical`, `other`).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/assets` | List all assets. |
| `POST` | `/assets` | Create an asset. |
| `GET` | `/assets/{assetId}` | Get an asset. |
| `PUT` | `/assets/{assetId}` | Update an asset. |
| `DELETE` | `/assets/{assetId}` | Delete an asset. Also deletes all associated tags. |
| `POST` | `/assets/{assetId}/logo` | Upload an asset logo. |
| `POST` | `/assets/{assetId}/attachments` | Upload an asset attachment. |
| `DELETE` | `/assets/{assetId}/attachments/{attachmentId}` | Delete an asset attachment. |

> Attachment/logo download URLs are pre-authorized and expire after 10 minutes.

## 3. Pentests

Scheduled security testing engagements against an asset. `POST /pentests` only creates a **draft** — there is no endpoint that submits a draft for review; that step happens in the Cobalt UI.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/pentests` | List all pentests. |
| `POST` | `/pentests` | Create a pentest (always created in `new`/draft state; requires an existing `asset_id`). |
| `GET` | `/pentests/{pentestId}` | Get a pentest. |
| `PUT` | `/pentests/{pentestId}` | Update a pentest. **Full replace, not a patch** — see gotchas in SKILL.md. |
| `DELETE` | `/pentests/{pentestId}` | Delete a pentest. Only allowed in draft or review state. |
| `POST` | `/pentests/{pentestId}/duplicate` | Duplicate a pentest. The copy is always created in draft state. Cannot duplicate a pentest that is itself in draft state. |
| `GET` | `/pentests/{pentestId}/test_coverage_summary` | Get the test coverage summary for a pentest. |
| `GET` | `/pentests/{pentestId}/report` | Get a pentest report. A `404` here on an otherwise-viewable pentest usually means a report-visibility/permissions issue, not a missing report. |

Pentest states: `new` (draft) → `in_review` → `planned` → `live` → `remediation` → `closed` (or `cancelled`).

## 4. Findings

Vulnerability reports created by pentesters during a pentest. Includes finding comments.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/findings` | List all findings. Supports filters: `pentest`, `asset`, `state`, `severity`, `labels_contains_all[]`, `created_at_gte/lte`, `updated_at_gte/lte`; `sort` (e.g. `-created_at`); pagination via `cursor`/`limit`. |
| `GET` | `/findings/{findingId}` | Get a finding. |
| `PATCH` | `/findings/{findingId}` | Update a finding (e.g. transition state). Call `possible_states` first to get valid next states. |
| `GET` | `/findings/{findingId}/possible_states` | Get the current state and all valid next states for a finding. |
| `GET` | `/findings/{findingId}/comments` | List comments on a finding. |
| `POST` | `/findings/{findingId}/comments` | Create a comment. Include `author_name`, `author_email`, `source_system`, `external_comment_id` when posting from an external system (Jira, ServiceNow, etc.). |
| `GET` | `/findings/{findingId}/comments/{commentToken}` | Get a comment. |
| `PATCH` | `/findings/{findingId}/comments/{commentToken}` | Update a comment. |
| `DELETE` | `/findings/{findingId}/comments/{commentToken}` | Delete a comment. Soft-deleted; remains in the list with a placeholder `body`. |

Finding states: `new` (Draft) → `triaging` → `need_fix` → `check_fix` → `valid_fix`, or `wont_fix` / `carried_over` / `not_applicable` / `invalid` (`duplicate`, `stale`, `out_of_scope` are deprecated aliases of `invalid`).

Severity = `impact` × `likelihood` (OWASP risk model, both 1–5): `critical` (25), `high` (16–24), `medium` (5–15), `low` (2–4), `informational` (1). `severity` is `null` until both are set.

## 5. Engagements

Security reviews other than traditional pentests: secure code reviews and digital risk assessments. Response fields vary by `engagement_type`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/engagements` | List all engagements. |
| `GET` | `/engagements/{engagementId}` | Get an engagement. |

Types: `secure_code_review`, `digital_risk_assessment`. States: `draft`, `in_review`, `planned`, `live`, `remediation`, `closed`, `cancelled`.

## 6. Engagement Findings

Vulnerability reports created during engagements. Uses the same severity model as Findings (§4).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/engagement_findings` | List all engagement findings. |
| `GET` | `/engagement_findings/{engagementFindingId}` | Get an engagement finding. |
| `PATCH` | `/engagement_findings/{engagementFindingId}` | Update state of an engagement finding. Fires the `ENGAGEMENT_FINDING_STATE_UPDATED` webhook. |

Finding type determines extra fields: `secure_code_review_finding` (`code_snippets`, `cvss_score`) vs. `digital_risk_assessment_finding` (`prerequisites`).

## 7. DAST Targets

The web application URLs that DAST scans run against.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/dast/targets` | List all DAST targets. |
| `GET` | `/dast/targets/{targetId}` | Get a DAST target. |
| `POST` | `/dast/targets/{targetId}/scans` | Start a DAST scan against a target. |
| `POST` | `/dast/targets/{targetId}/scheduled_scans` | Schedule a recurring DAST scan for a target (`WEEKLY`, `MONTHLY`, or `QUARTERLY`). |

## 8. DAST Scans

Automated security scans run against DAST targets.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/dast/scans` | List all DAST scans. |
| `GET` | `/dast/scans/{scanId}` | Get a DAST scan. |

Scan states progress: `queued` → `started` → `under_review` → `finishing_up` → `completed` (or `completed_with_errors` / `failed`); pause/resume/cancel states also exist (`pausing`, `paused`, `resuming`, `canceling`, `canceled`).

## 9. DAST Findings

Vulnerabilities discovered by automated DAST scans.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/dast/findings` | List all DAST findings. |
| `GET` | `/dast/findings/{findingId}` | Get a DAST finding. |
| `PATCH` | `/dast/findings/{findingId}` | Transition a DAST finding's state. **Cannot** set state to `check_fix` or `valid_fix` this way — use the retest endpoint instead. |
| `POST` | `/dast/findings/{findingId}/retest` | Retest a DAST finding. Runs a short scan; state updates automatically (`check_fix` → `valid_fix`) once the retest completes. |

States: `need_fix`, `wont_fix`, `invalid`, `check_fix`, `valid_fix`.

## 10. Attack Surface

High-level view of domains and hosts discovered for the organization.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/attack_surface/stats` | Get attack surface statistics. |

## 11. External Finding / Ticket References

Links Cobalt findings to tickets in external issue trackers (Jira, ServiceNow, Asana, etc.). **Note:** `/external_finding_references` and `/external_ticket_references` are parallel path spellings for the same underlying resource in this spec — same request/response shape, same operations. Prefer `/external_ticket_references` (the current name); `/external_finding_references` appears to be retained for compatibility. Only references created via the Integration Builder or the public API are visible here — references from the older native Jira/GitHub integrations are not.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/external_ticket_references` | Create an external ticket reference. |
| `POST` | `/external_ticket_references/search` | Search references by `findings` (array of finding ID objects), `ticketing_system`, and/or `external_id` (case-sensitive exact match). |
| `PATCH` | `/external_ticket_references/{referenceId}` | Update an external ticket reference. |
| `DELETE` | `/external_ticket_references/{referenceId}` | Delete an external ticket reference. |
| `POST` | `/external_finding_references` | Same as `POST /external_ticket_references` (legacy path). |
| `POST` | `/external_finding_references/search` | Same as `POST /external_ticket_references/search` (legacy path). |
| `PATCH` | `/external_finding_references/{referenceId}` | Same as `PATCH /external_ticket_references/{referenceId}` (legacy path). |
| `DELETE` | `/external_finding_references/{referenceId}` | Same as `DELETE /external_ticket_references/{referenceId}` (legacy path). |

Recognized `ticketing_system` values (for logo display in the UI; any string is accepted): `asana`, `azure_devops_boards`, `bmc`, `basecamp`, `bitbucket`, `clickup`, `freshservice`, `github`, `gitlab`, `hive`, `jira`, `monday`, `pivotaltracker`, `servicenow`, `trello`, `wrike`, `zendesk`.

## 12. Integrations & Integration Connections

Configuration for pentest/org-level tool integrations (distinct from the External Ticket References resource above).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/integrations` | List all supported integrations. |
| `POST` | `/integrations` | Create a new integration for a pentest. |
| `GET` | `/integrations/{integrationId}` | Get a single integration. |
| `PATCH` | `/integrations/{integrationId}` | Update an integration. |
| `DELETE` | `/integrations/{integrationId}` | Delete an integration. |
| `GET` | `/integrations/connections` | List all integration connections. |
| `POST` | `/integrations/connections` | Create a new integration connection within your organization. |
| `GET` | `/integrations/connections/{connectionId}` | Get a single integration connection. |
| `PATCH` | `/integrations/connections/{connectionId}` | Update an integration connection. |
| `DELETE` | `/integrations/connections/{connectionId}` | Delete an integration connection. |

## 13. Webhooks

Notifies your system of platform events via HTTP POST instead of polling.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/webhooks` | List all webhooks. |
| `POST` | `/webhooks` | Create a webhook. Set a high-entropy `secret`; verify the `X-Secret` header on incoming deliveries. |
| `GET` | `/webhooks/{webhookId}` | Get a webhook. |
| `PATCH` | `/webhooks/{webhookId}` | Update a webhook. |
| `DELETE` | `/webhooks/{webhookId}` | Delete a webhook. |
| `GET` | `/webhooks/event-types` | List all webhook event types and their payload schemas. |

Delivery: on failure, Cobalt retries 5 times at 5-second intervals, then hourly; an endpoint unhealthy for 48 hours is auto-deactivated and must be reactivated via the API or UI.

## 14. Events

Activity feed for the account (comment creation, pentest state changes, finding creation, etc.). For push notifications instead of polling, use Webhooks (§13).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/events` | List recent events. |

## 15. Tokens

Manage the API tokens used to authenticate requests.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tokens` | List all tokens. |
| `POST` | `/tokens/{tokenId}/refresh` | Revoke a token and issue a new one with the same name. The new secret is returned in the `secret` field; the old token stops working immediately. |

## 16. Billing (Balance, Contracts, Credit Transactions)

Credit balance and contract/usage history for the organization.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/balance` | Get the current credit balance. |
| `GET` | `/contracts` | List all contracts, including credit allocation and usage. |
| `GET` | `/credit-transactions` | List all credit transactions. |

---

## Common Query Parameters

Most list (`GET`) endpoints accept:

- `cursor` (string) — pagination cursor; use the `next_page`/`prev_page` value from the previous response.
- `limit` (integer, 1–1000, default 10 in v2) — page size.

`GET /findings` additionally supports `state`, `severity`, `pentest`, `asset`, `labels_contains_all[]`, `created_at_gte/lte`, `updated_at_gte/lte`, `sort`, and `image_attachments_render_format` (`markdown` default, or `token` for programmatic attachment handling).

See `references/api-spec.yaml` for the full parameter list on any given endpoint.
