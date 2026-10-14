---
name: bugcrowd-api
description: >
  Use when working with the Bugcrowd REST API (v1.1.0) — writing code against it, querying it
  directly with curl, pulling submissions/reports, programs, engagements, targets or rewards, or
  verifying a Bugcrowd webhook delivery. Covers authentication, the JSON:API envelope, filtering,
  pagination, error diagnosis, and the silent failures where production deviates from the published
  spec.
---

# Bugcrowd API Skill

This file covers what applies to **every** request. Per-resource detail — paths, attribute lists,
enums, request bodies, and the traps specific to one endpoint — lives in the references below.

Zeta's *process* — what a submission state means, whose court the report is in, VDP versus private bug
bounty engagement, points and bounty eligibility — is the `bugcrowd-workflow` skill. Invoke it when
the question is about the report's handling rather than the request.

## Reference Documentation

`references/bugcrowd-api-overview.md` indexes all 52 operations grouped by resource, with each
resource's `fields[...]`, `include`, and `filter[...]` enums and its known traps. **Read the section
for a resource before writing your first request against it** — the enums it lists are the ones the
server actually accepts, and every section carries at least one behaviour the spec gets wrong.

`references/api-spec.yaml` is the OpenAPI spec, for full request/response schemas. It is a
self-contained merge of Bugcrowd's published `openapi.yml` and its companion `external_elements.yml`,
so every `$ref` resolves inside that one file. Shared enums and parameter schemas live under the
top-level `domain_model_helpers`, `relationship_param_helpers`, `general_helpers`,
`description_helpers`, and `error_helpers` keys — not under `components` — so when a path's parameter
points at `#/domain_model_helpers/SubmissionFilterState`, search for that key at the top level.

`references/verified-behaviour.md` is the evidence behind every claim this skill marks "verified" —
the exact probe and the exact response for each deviation from the published spec. **Where the spec
and the test log disagree, the test log wins**, and that adjudication is already applied throughout
this file and the overview. So it is a maintenance reference, not one you need to consult to make a
request. Reach for it when:

- **A response contradicts a rule in this skill.** Compare against the original probe to distinguish
  a Bugcrowd change from a mistake on your side, then update the log with what you now observe.
- **You need to know whether something was ever actually tested.** Its `Not yet verified` and
  `Access level of the credential used` sections bound what this skill knows — notably that no
  state-changing request has ever been issued against this API, so every write path here is
  documented from the spec alone.
- **Re-verifying after a `Bugcrowd-Version` bump.** Deviations get fixed, or drift further, without
  notice.

## Environment Variables

Preloaded by the deployment environment; read them at runtime rather than hardcoding, and validate
them before constructing a request so a missing credential fails by name instead of as a `404`.

- `BUGCROWD_API_TOKEN` — credential in `TOKEN_USERNAME:TOKEN_PASSWORD` form (the full colon-joined
  string, exactly as shown when created at https://tracker.bugcrowd.com/user/api_credentials)
- `BUGCROWD_API_BASE_URL` (optional, defaults to `https://api.bugcrowd.com`) — may carry a trailing
  slash, so strip it (`"${BUGCROWD_API_BASE_URL%/}"`) or you will request `//organizations`
- `BUGCROWD_API_VERSION` (optional) — sent as `Bugcrowd-Version` to override the version pinned to
  the token, see API Versioning below

## Authentication

Bugcrowd uses a token username/password pair sent as a single `Authorization` header value prefixed
with the literal word `Token`:

```
Authorization: Token gvnzkgmklo:gPYS2SMN3zJ_k-QAEvyMAcr_PqsGlA-vJ2voA7ysZ635GlT_VZdr2Sg3_YCctkM3SwnBtDCn
```

The scheme keyword is `Token`, **not** `Bearer` or `Basic`, and the value is not base64-encoded.
Credentials are shown once at creation and are not retrievable afterwards. They may be restricted to
an IPv4 allowlist, so a `401` from a new network location can mean the allowlist, not a bad token.

There is no org-scoping header — access is determined entirely by what the credential's owner can
see. To discover what you can operate on: `GET /organizations` → `GET /programs` (optionally
`filter[organization_id]`) → use the program's `code` for `filter[program]` on submissions, and its
`id` (UUID) everywhere a program relationship or `filter[program_id]` is required.

## HTTP Request Headers

- `Authorization: Token ${BUGCROWD_API_TOKEN}`
- `Accept: application/vnd.bugcrowd+json` — **effectively mandatory**, see below
- `Content-Type: application/vnd.bugcrowd.v4+json` — on `POST`/`PATCH` requests carrying a body,
  **except** `POST /submissions/search`, which the spec declares as `application/json`
- `Bugcrowd-Version: ${BUGCROWD_API_VERSION}` — optional, see API Versioning below

The spec marks `Accept` as `required: false`. That is wrong: verified against production, **any**
`Accept` value other than `application/vnd.bugcrowd+json` — including `*/*`, which is what curl and
most HTTP clients send by default — returns **`404` with an HTML body**, not a `406`. A mysterious
404 on a URL you are sure exists is almost always a missing or wrong `Accept` header. Send it on
every request, including `GET`s.

Despite the vendor request media types, **successful responses come back as
`application/json; charset=utf-8`**, never `application/vnd.bugcrowd.v4+json`. Parse on the JSON
body, not on a vendor content type.

### Example `curl` commands

```bash
# Discover accessible organizations
curl -sS --request GET \
  --url "${BUGCROWD_API_BASE_URL:-https://api.bugcrowd.com}/organizations" \
  --header "Authorization: Token ${BUGCROWD_API_TOKEN}" \
  --header "Accept: application/vnd.bugcrowd+json" \
  | jq '.data[] | {id: .id, name: .attributes.name}'
```

```bash
# List unresolved P1/P2 submissions for a program, newest first, with the target included.
# `--get --data-urlencode` keeps curl from glob-expanding the brackets — see Silent failures.
curl -sS --request GET \
  --get "${BUGCROWD_API_BASE_URL:-https://api.bugcrowd.com}/submissions" \
  --data-urlencode "filter[program]=${PROGRAM_CODE}" \
  --data-urlencode "filter[state]=triaged,unresolved" \
  --data-urlencode "filter[severity]=1,2" \
  --data-urlencode "fields[submission]=title,state,severity,submitted_at,vrt_id,target" \
  --data-urlencode "fields[target]=name,category" \
  --data-urlencode "include=target" \
  --data-urlencode "sort=submitted-desc" \
  --data-urlencode "page[limit]=100" \
  --header "Authorization: Token ${BUGCROWD_API_TOKEN}" \
  --header "Accept: application/vnd.bugcrowd+json"
```

```bash
# Create a submission. PATCH uses the same envelope and the same vendor Content-Type.
curl -sS --request POST \
  --url "${BUGCROWD_API_BASE_URL:-https://api.bugcrowd.com}/submissions" \
  --header "Authorization: Token ${BUGCROWD_API_TOKEN}" \
  --header "Accept: application/vnd.bugcrowd+json" \
  --header "Content-Type: application/vnd.bugcrowd.v4+json" \
  --data '{
    "data": {
      "type": "submission",
      "attributes": {
        "title": "Reflected XSS in the search parameter",
        "description": "Steps to reproduce and impact...",
        "severity": 3,
        "vrt_id": "cross_site_scripting_xss"
      },
      "relationships": {
        "program": { "data": { "type": "program", "id": "'"${PROGRAM_ID}"'" } }
      }
    }
  }'
```

## API Versioning

Every API credential is **pinned** to a date-based version (e.g. `2025-04-23`), chosen in the
credential's settings, and automatically receives minor releases and bug fixes within its major
version. Sending a `Bugcrowd-Version` header overrides the pinned version for that single request —
the supported way to test a newer version before repinning the token.

Behaviour genuinely differs between versions (for example, the `page[offset]` cap was removed in
`2025-04-23`), so if a documented feature appears to be missing, check the token's pinned version
before concluding the endpoint is broken. Determine the version in effect with a behavioural probe
(such as whether `page[offset]=9901` is accepted): an unrecognised `Bugcrowd-Version` is silently
ignored rather than rejected, and no response header reports which version served the request.

## JSON:API Request and Response Shape

Bugcrowd follows [JSON:API](https://jsonapi.org/format/). Every resource object has `type`, `id`
(UUID), `attributes`, `relationships`, and `links.self`. Collections return `data` as an array;
single fetches return `data` as an object. Requested `include`s arrive as a flat array under
`included`, not nested inside the parent.

Write bodies use the same envelope, and `data.type` is always required:

```json
{ "data": { "type": "<resource_type>", "attributes": { }, "relationships": { } } }
```

Almost every request schema sets `additionalProperties: false`, so an unrecognised or misspelled
attribute is a hard `400` with a JSON pointer in `errors[].source.pointer`. Omit `data.id` on a
create; client-generated IDs are rejected with a `403`.

**The same strictness applies to the query string,** which is validated as one object — so an
unsupported query parameter is a hard `400` rather than a silently ignored one:
`GET /engagements?filter[program]=...` (that endpoint has no filters at all) returns
`"The property '#/' contains additional properties ['filter'] outside of the schema when none are
allowed."`

Better still, validation errors **enumerate the accepted values**:
`"The property '#/sort/0' value '-created_at' did not match one of the following values:
created_at-asc, created_at-desc."` Deliberately sending a bogus *value* is the fastest way to
discover an endpoint's real enum. (Bogus *keys* do not enumerate — get the key list from
`api-spec.yaml`.)

### Sparse fieldsets (`fields[...]`)

`fields[<resource_type>]=attr1,attr2,relationship1` limits what comes back for that resource type; if
omitted, all fields are returned. The key is the singular resource *type* (`fields[submission]`,
`fields[monetary_reward]`), and it applies to included resources too — so narrowing a submission list
means setting `fields[submission]` *and* a `fields[...]` for each type you included. An invalid value
returns `400` listing the valid ones; they are also enumerated per resource in the overview.

### Includes (`include`)

`include=program,target,comments.author` pulls related resources into `included`. Nested paths use
dot notation and must be drawn from that endpoint's own include enum — submissions allow
`monetary_rewards.payments` and `program.organization`, while engagements allow
`engagement_brief.engagement_brief_target_groups.reward_range`.

### Filtering

`filter[<name>]=<value>`. Most filters accept a comma-separated list (`explode: false`) and a few
accept only a single scalar. Date filters accept a bare date or a range using `from.` and `to.`
prefixes: `filter[submitted]=from.2021-02-28,to.2021-03-01`.

**Always comma-join multi-value filters** — `filter[state]=new,out-of-scope` — rather than repeating
the parameter, which silently keeps only the last occurrence (see Silent failures). Filter values are
**case-sensitive**: `filter[state]=New` is a `400`.

### Sorting

`sort=<field>-asc` / `sort=<field>-desc`, comma-separated for multiple keys
(`sort=submitted-asc,severity-desc`). This **deviates from JSON:API**, which uses a `-` prefix. Only
the enumerated sort keys per endpoint are accepted, and they are **not** attribute names —
`submitted-desc` orders by the `submitted_at` attribute, and submissions accept `updated-asc` even
though no `updated_at` attribute is ever returned.

## Pagination

List endpoints use offset pagination via `page[limit]` and `page[offset]`. `page[limit]` defaults to
`25` with a maximum of `100` (`page[limit]=500` is a `400`); `page[offset]` defaults to `0`.
Collection `meta` reports `count` (records on this page) and `total_hits` (the whole result set).

> **`links.next` is always present and non-null — even on the last page.** Verified: a collection
> with `total_hits: 1, count: 1` still returns a `links.next` pointing at `page[offset]=25`, and
> requesting an offset past the end returns `200` with `count: 0` and *another* non-null `links.next`.
> **Looping until `links.next` is null never terminates.** Stop when `count == 0`, or when
> `offset + count >= total_hits`. Treat `links.next` as a convenience URL, not an end-of-data signal.

Three more limits to design around:

- On API versions older than `2025-04-23`, `page[offset]` is capped at `9900`, making a result set
  reachable only to ~10,000 records. Split the query into smaller slices (e.g. by `filter[submitted]`
  date ranges) and paginate each slice.
- Included relationships are capped at **100 records each** and cannot be paginated in the same
  request. Verified: a program with 890 submissions returns a `relationships.submissions.data` array
  of exactly 100 alongside `meta: {count: 100, total_hits: 890}`. Whenever `count < total_hits` the
  list was truncated — refetch from the standalone endpoint instead of trusting the embedded array.
- `relationships.<name>.links.related.href` is sometimes the literal placeholder string
  `"(NOT IMPLEMENTED YET)"` rather than a URL (engagement `engagement_brief` and `bounty` both return
  it). Check the value before requesting it; where it *is* implemented it is a real relative path,
  e.g. `/submissions?filter[program]=zetaglobal-vdp`.

Not every list endpoint is paginated: `/authorization_logs` and `/disclosure_requests` do not accept
`page[...]` parameters.

Collection `meta` also carries undocumented `deprecated_fields` and `deprecated_relationships`
objects when applicable — `GET /submissions` currently returns a notice that the singular `assignee`
field and relationship are being removed in favour of `assignees`. These are not in the spec; log
them, and prefer the replacement field they name.

## Rate Limits

Bugcrowd limits API requests to **60 requests per minute per IP address**, across all credentials
used from that IP. Because the limit is per IP rather than per token, parallel workers behind one
egress IP share one budget — serialise them or coordinate a shared limiter.

Although Bugcrowd's docs don't mention them, every response **does** carry rate-limit headers
(verified): `x-ratelimit-limit: 60` and `x-ratelimit-remaining: <n>`. Read
`x-ratelimit-remaining` and throttle as it approaches zero. There is **no** reset or retry-after
header, so on `429` fall back to exponential backoff — up to a full 60-second window may need to
elapse.

## Error Handling

Errors come back in the JSON:API error envelope:

```json
{ "errors": [ { "status": "400", "title": "Bad Request", "detail": "...", "source": { "pointer": "/data/attributes" } } ] }
```

`status`, `title`, and `detail` are always present; `source.pointer` appears on validation errors and
names the offending field. Up to 100 errors are returned at once — report all of them, not just the
first.

### First: check whether the error body is JSON or HTML

This is the most useful diagnostic in the whole API, because Bugcrowd overloads `404` for three
unrelated causes. Verified behaviour:

| You sent | You get | Body |
|---|---|---|
| Valid token + valid `Accept`, resource missing or not visible to you | `404` | **JSON** `errors` envelope |
| No `Authorization` header at all | `404` | HTML |
| A syntactically fine but invalid/revoked token | `404` | HTML |
| `Authorization: Bearer …` (wrong scheme) | `401` | HTML |
| Missing/wrong `Accept` (e.g. `*/*`) | `404` | HTML |

So: **an HTML 404 is an authentication or `Accept` problem, never a missing resource.** A JSON 404
with `{"errors":[{"detail":"The requested resource could not be found.", …}]}` is the genuine
resource-level 404. Branch on the response `Content-Type`, not the status code alone. Counter-
intuitively, `401` is the *narrow* case — it only means the auth scheme keyword wasn't recognised —
while bad credentials masquerade as `404`.

| Code | Meaning |
|------|---------|
| 400 | Bad Request — malformed body, unknown attribute, unsupported **query parameter**, or an invalid `fields[...]`/`filter[...]`/`sort`/`page[...]` value. Read `source.pointer`; `detail` usually lists the accepted values. |
| 401 | Unauthorized — the `Authorization` scheme keyword is not `Token`. HTML body. |
| 403 | Forbidden — no access to this resource, or a client-generated `data.id` was supplied on a create |
| 404 | Not Found — **JSON body**: resource missing, or outside your access, or a referenced `program`/`target`/`submission` you cannot see. **HTML body**: missing/invalid credential, or a missing/wrong `Accept` header. |
| 409 | Conflict — the `data.type` in the body is not the type this endpoint accepts (`"Provided type: X is not supported by this endpoint."`), *not* a duplicate resource |
| 422 | Unprocessable Entity — well-formed but semantically invalid (missing required attribute, invalid `vrt_id`, disallowed state transition) |
| 429 | Too Many Requests — see Rate Limits |
| 500 / 503 | Server error — retry with backoff |

Explain any error you surface and name the likely fix. On an HTML `404` or a `401`, check in this
order: (1) the `Accept` header is exactly `application/vnd.bugcrowd+json`, (2) the scheme keyword is
`Token`, (3) `BUGCROWD_API_TOKEN` is the full `username:password` string, (4) the credential's IPv4
allowlist covers the caller, then regenerate it from
https://tracker.bugcrowd.com/user/api_credentials. On a JSON `403`/`404` for a resource that should
exist, the credential's owner most likely lacks a role on that program or organization — confirm with
`GET /programs` before assuming the ID is wrong.

## Silent failures

This API's characteristic hazard is not the error you get, it's the plausible-looking `200` you get
instead. Each of these was verified against production, and each returns success:

| Silent behaviour | What it looks like | Do this instead |
|---|---|---|
| Repeating a `filter[...]` parameter keeps only the **last** value | a smaller result set that looks legitimate | comma-join: `filter[state]=new,out-of-scope` |
| `filter[program]` / `filter[engagement]` take short **codes**; a wrong code — or the resource's genuine UUID — returns `total_hits: 0` | "that program has no submissions" | resolve the code from `GET /programs`; cross-check zero against an unfiltered count |
| Filtering a nullable attribute drops the null rows with no way to filter *for* null | `filter[state]=new` + `filter[severity]` reliably returns nothing, because new reports arrive `severity: null` | omit the filter and partition client-side |
| `POST /submissions/search` ignores `fields` entirely | the full 23-attribute payload, `description` included | use `GET /submissions` with `fields[...]` unless the query string is genuinely too long |
| An unrecognised `Bugcrowd-Version` is ignored | a normal `200` on the token's pinned version | probe behaviourally; no header echoes the version |
| `GET /programs/{program_id}/targets` does not validate its filter enums | `filter[category]=nonsense` → `total_hits: 0` | compare against the unfiltered count |
| A relationship's `meta.count` can contradict its `data` | `data: []` and empty `included` alongside `meta: {count: 1}` | trust `data`/`included`; treat `meta.count` as a hint |
| `submitted_at` is create-only, so a bulk import stamps the whole backlog with its own clock | a date filter that looks like a reporting timeline (verified: 887 of 890 submissions inside one 2.6-second window, `source: csv`) | check the spread of `submitted_at` and whether `source` is `csv` before calling a date filter a report date |
| `curl` glob-expands the `[`/`]` in bracketed parameters | `bad range in URL position N` — a local failure that never reaches Bugcrowd | `--globoff`/`-g`, or `--get --data-urlencode` |

The habit that catches all of them: **sanity-check every filtered count against the unfiltered
`total_hits`** for the same query, and treat an unexpected zero as a malformed request until proven
otherwise.

## Data model rules

Four properties of the data itself that mislead on first contact. Per-resource detail is in the
overview; these apply wherever you touch submissions or programs.

- **Severity is inverted: `1` is the most severe.** `severity` is a nullable integer 1–5 mapping to
  Bugcrowd's P1–P5, where P1 is critical and P5 informational. `sort=severity-asc` puts the worst
  findings first. Flip it before mapping onto any "higher is worse" scale.
- **Submission states are hyphenated in filters and underscored everywhere else.** Verified: the API
  returns `"state": "not_applicable"` but `filter[state]=not_applicable` is a hard `400`, while
  `filter[state]=not-applicable` works. The same split applies to
  `filter[blocked_by]=bugcrowd-operations` versus the attribute value `bugcrowd_operations`.
  Translate `_` → `-` before feeding a response value into a filter.
- **Identify a program by `code` or `id`, never by `name`.** Verified: `program.name` is a mutable
  display label that changes without notice while `code` and `id` stay fixed, and it is **not
  unique** (two programs in one organization both read `"Sizmek Servers"`). Treat `name` as
  presentation only.
- **There is no report permalink in the API.** No attribute exposes a UI URL — `links.self` is the
  API path (`/submissions/{id}`) and `bug_url` is the *vulnerable* URL, not a link to the report.
  Construct UI links as `https://tracker.bugcrowd.com/{program_code}/submissions/{submission_id}`,
  and say so when you hand them over: the shape is constructed, not returned.

## Webhooks

Bugcrowd delivers `submission.created`, `submission.updated`, `blocker.created`, and
`blocker.updated` events as `POST` requests to a consumer URL configured per program under
**Settings → Integrations → Outgoing Webhooks**. These are not endpoints you call; they are defined
under `x-webhooks` in the spec, and their payloads are tabulated in the overview.

Verify every delivery before trusting it. The `X-Bugcrowd-Digest` header has the form
`timestamp=<value>;sha256=<hex>`, where the hex digest is
`HMAC-SHA256(secret, raw_request_body + timestamp)`. Compute the HMAC over the **raw** body bytes
(not a re-serialised parse), compare with a constant-time comparison, and reject deliveries whose
timestamp is too old to bound replay.

`submission.updated` payloads carry only what changed, as
`data.attributes.data.changes = {"<field>": {"from": ..., "to": ...}}` — treat absent fields as
unchanged rather than as null. Webhooks require API version `2021-10-28` or later.
