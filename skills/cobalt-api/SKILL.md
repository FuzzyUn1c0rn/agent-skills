---
name: cobalt-api
description: >
  Use this skill to develop code that interacts with the Cobalt.io v2 API or to directly interact with it using tools like `curl`. This skill provides reference documentation and guidelines for authentication, org scoping, pagination, idempotency, rate limits, and error handling for Organizations, Assets, Pentests, Findings, Engagements, DAST, Webhooks, Integrations, and Billing endpoints.
---

# Cobalt API Skill

## Reference Documentation

To get a high-level understanding of all available APIs, search this endpoint index, grouped by resource: `references/cobalt-api-overview.md`.

For full details on any specific endpoint — request/response schemas, parameters, and enum values — search the OpenAPI spec file: `references/api-spec.yaml`.

## Environment Variables

The following environment variables are available in your deployment context:

- `COBALT_API_TOKEN` — personal API token, created at https://app.cobalt.io/settings/api-token
- `COBALT_ORG_TOKEN` — organization token, required for org-scoped endpoints (see Org Scoping below)
- `COBALT_API_BASE_URL` (optional, see Data Regions — defaults to the US base URL)

### When Generating Code

When generating code, follow these steps:

1. Load configuration values from environment variables at runtime.
2. Do not hardcode configuration values.
3. Read variables from `os.environ` (Python), `process.env` (Node.js), or equivalent for other languages.
4. Validate required variables before constructing any API request.
5. If a required variable is missing or invalid, fail with a clear error message that names the variable and corrective action.
6. After validation succeeds, construct and execute API requests.
7. Assume these environment variables are preloaded by the deployment environment.

### When Directly Interacting with the API

When directly interacting with the API (for example, by running a `curl` command or a Python script), assume these environment variables are available and use them appropriately. Reference them using shell variable syntax (e.g., `${COBALT_API_TOKEN}`).

## Org Scoping

Almost every endpoint except `GET /orgs` is scoped to a specific organization via the `X-Org-Token` header. To obtain it:

1. `GET /orgs` (no `X-Org-Token` needed for this call).
2. Copy the `token` field from the organization you want to operate on.
3. Send it as `X-Org-Token` on all subsequent calls to that organization's resources.

If `COBALT_ORG_TOKEN` is not set, call `GET /orgs` first and ask which organization to use before making any org-scoped request.

## HTTP Request Headers

When making requests to the API, include the following headers:

- `Authorization: Bearer ${COBALT_API_TOKEN}`
- `Accept: application/vnd.cobalt.v2+json`
- `X-Org-Token: ${COBALT_ORG_TOKEN}` — required for org-scoped endpoints (all except `GET /orgs`)
- `Content-Type: application/vnd.cobalt.v2+json` — required on `POST`/`PUT`/`PATCH`/`DELETE` requests that carry a body
- `Idempotency-Key: <uuid>` — optional on `POST` requests, see Idempotency below
- `User-Agent: [IntegrationName]/[IntegrationVersion]` — optional but encouraged for partner integrations, e.g. `MyCobaltIntegration/1.0.0`

### Example `curl` commands

```bash
# List organizations and get the org token
curl -sS --request GET \
  --url "${COBALT_API_BASE_URL:-https://api.us.cobalt.io}/orgs" \
  --header "Authorization: Bearer ${COBALT_API_TOKEN}" \
  --header "Accept: application/vnd.cobalt.v2+json" \
  | jq '.data[] | {id: .id, name: .name, token: .token}'
```

```bash
# List findings for an asset, newest first, org-scoped
curl -sS --request GET \
  --url "${COBALT_API_BASE_URL:-https://api.us.cobalt.io}/findings?asset=${ASSET_ID}&sort=-created_at&limit=50" \
  --header "Authorization: Bearer ${COBALT_API_TOKEN}" \
  --header "X-Org-Token: ${COBALT_ORG_TOKEN}" \
  --header "Accept: application/vnd.cobalt.v2+json"
```

```bash
# Create an asset (mutating request — needs Content-Type and benefits from an idempotency key)
curl -sS --request POST \
  --url "${COBALT_API_BASE_URL:-https://api.us.cobalt.io}/assets" \
  --header "Authorization: Bearer ${COBALT_API_TOKEN}" \
  --header "X-Org-Token: ${COBALT_ORG_TOKEN}" \
  --header "Accept: application/vnd.cobalt.v2+json" \
  --header "Content-Type: application/vnd.cobalt.v2+json" \
  --header "Idempotency-Key: $(uuidgen)" \
  --data '{"name": "example.com", "asset_type": "web"}'
```

## Data Regions

If `COBALT_API_BASE_URL` is undefined, default to the US base URL.

| Region | Base URL |
|--------|----------|
| US (default) | `https://api.us.cobalt.io` |
| EU | `https://api.eu.cobalt.io` |

EU customers (using `app.eu.cobalt.io`) must set `COBALT_API_BASE_URL` to the EU base URL — all examples in the spec default to US.

## Pagination

List endpoints use cursor-based pagination via `cursor` and `limit` query parameters (`limit` max 1000, default 10 in v2). If `next_page` or `prev_page` in the response is non-`null`, more resources exist. To fetch the next page, request the path in `next_page` directly (it already includes the `cursor` query param) against the base URL — do not construct the cursor yourself.

## Idempotency

All `POST` requests optionally accept an `Idempotency-Key: <uuid>` header (a V4 UUID or other high-entropy string) to safely retry a request without double-creating a resource. Keys expire after 5 minutes. The header name `Mutation-Check` is also accepted for backwards compatibility. Reusing a key for a genuinely different request body returns `409 Conflict`.

## Rate Limits

Rate limiting is per-user (across all of that user's API tokens combined) and fixed-window:

| Request Type | Verbs | Limit | Window |
|---|---|---|---|
| Get | `GET` | 100 | 60 seconds |
| Mutate | `POST`, `PATCH`, `PUT`, `DELETE` | 20 | 60 seconds |

Response headers `X-Rate-Limit-Get-Limit` / `X-Rate-Limit-Mutate-Limit` and `X-Rate-Limit-Remaining` report the applicable limit and remaining budget. Exceeding the limit returns `429 TOO_MANY_REQUESTS`; back off until the window resets.

## Error Handling

| Code | Meaning |
|------|---------|
| 400 | Bad Request — malformed request |
| 401 | Unauthorized — API token is missing or wrong |
| 403 | Forbidden — no access to this resource |
| 404 | Not Found |
| 405 | Method Not Allowed |
| 406 | Not Acceptable — requested a non-JSON format |
| 409 | Conflict — reused an `Idempotency-Key` with a different request |
| 410 | Gone — endpoint removed |
| 422 | Unprocessable Entity — well-formed but semantically invalid |
| 429 | Too Many Requests — see Rate Limits |
| 500 / 503 | Server error — retry later |

If the API returns an error response, provide a detailed explanation of the error and suggest possible resolutions. If the API indicates the token is invalid or expired (401/403), instruct the user to verify `COBALT_API_TOKEN`, regenerate it from their Cobalt profile if needed, and retry. A `403`/`404` on an org-scoped endpoint often means `X-Org-Token` is missing, stale, or for the wrong organization — re-fetch it from `GET /orgs`.

## Key Gotchas

These are non-obvious behaviors worth checking before writing code against specific endpoints — see `references/api-spec.yaml` for full detail on each:

- **`PUT /pentests/{pentestId}` is a full replace, not a patch.** `asset_id`, `title`, `description`, and `technology_stack` are required every call. Fields like `instructions`, `test_credentials`, `scoping`, and `targets` are cleared to empty if omitted. Read the pentest first, then send back the full brief with changes applied.
- **Pentest field naming is confusing:** the pentest's `description` field holds testing *objectives* and is returned as `objectives` in responses (there is no `description` field on the response). Testing priorities/exclusions go in `instructions`; environment access details go in `test_credentials`.
- **`targets` on a pentest is a comma-separated string, not an array** (e.g. `"https://a.com,https://api.a.com"`). Targets not already in the org are created automatically.
- **`scoping` unrecognized keys are silently ignored, not rejected.** A misspelled asset-type key under `scoping` produces no validation error — it just surfaces later as incomplete scoping.
- **There is no API endpoint to submit a pentest for review.** `POST /pentests` only creates a draft (`new` state); submission happens in the Cobalt UI.
- **DAST findings can't be moved to `check_fix`/`valid_fix` via `PATCH`.** Use `POST /dast/findings/{id}/retest` instead — the state updates automatically when the retest completes.
- **`/external_finding_references` and `/external_ticket_references` are duplicate path spellings of the same resource.** Prefer `/external_ticket_references`; only references created via the Integration Builder or the public API are visible through this resource (not ones from older native Jira/GitHub integrations).
- **Finding severity is `null` until both `impact` and `likelihood` are set** by the pentester; severity = impact × likelihood (OWASP model).
