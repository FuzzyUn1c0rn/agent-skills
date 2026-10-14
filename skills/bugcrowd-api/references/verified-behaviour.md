# Verified API Behaviour — Test Log

Live read-only probes against `https://api.bugcrowd.com` on **2026-08-31**, plus file-download
probes on **2026-09-15**, using a Zeta Global credential. Every claim in SKILL.md marked "verified"
traces to a row here. **No state-changing request was issued** — every probe is a `GET`, with the
single exception of
`POST /submissions/search`, which is a read-only query endpoint (it cannot create a submission;
`POST /submissions` does that).

Shell note: `curl` treats `[` and `]` as glob metacharacters, so every bracketed parameter here
(`filter[state]`, `page[limit]`, …) needs either `--globoff`/`-g` or `--get --data-urlencode`.
Without one, curl fails locally with `bad range in URL position N` and never reaches Bugcrowd.

Re-run these probes after any Bugcrowd version bump; several findings are deviations from the
published spec and may be fixed (or may drift further) without notice.

## Reference data confirmed

| Claim | Method | Result |
|---|---|---|
| Organization "Zeta Global" exists | `GET /organizations` | ✅ Exactly one org, `1300de0c-d1b5-4548-af5c-cf56360a7d71`, 6 programs, 33 targets |
| Program "Zeta Global Vulnerability Disclosure Program" | `GET /programs?filter[organization_id]=…` | ✅ `code=zetaglobal-vdp`, `id=5bf97379-ad28-4fb3-929e-9b9872dfc667` |
| It has 9 engagements | `GET /programs/{id}?include=engagements` | ✅ `relationships.engagements.links.related.meta = {count: 9, total_hits: 9}`, 9 objects in `included` |
| 9 engagements (independent route) | `GET /engagements?page[limit]=100` | ✅ 14 engagements org-wide; 9 have `relationships.bounty.data.id == <VDP id>` |
| 4 bug bounty | both routes | ✅ `engagement_type.name == "Bug Bounty"` × 4 |
| 5 vulnerability disclosure | both routes | ✅ `engagement_type.name == "Vulnerability Disclosure"` × 5 |

The 9 engagements, for reference:

| Code | State | `engagement_type.name` |
|---|---|---|
| `zetaglobal-vdp-ess` | `in_progress` | Vulnerability Disclosure |
| `zetaglobal-vdp-ess1` | `draft` | Vulnerability Disclosure |
| `zetaglobal-vdp-ess2` | `draft` | Vulnerability Disclosure |
| `cheetah-vdp` | `in_progress` | Vulnerability Disclosure |
| `liveclicker-vdp` | `in_progress` | Vulnerability Disclosure |
| `cheetahdigital-mbb` | `launching` | Bug Bounty |
| `selligent-mbb` | `draft` | Bug Bounty |
| `sailthru-mbb` | `draft` | Bug Bounty |
| `liveclicker-mbb` | `draft` | Bug Bounty |

**Naming evidence:** the API reported `"Vulnerability Disclosure"` where the UI says "Vulnerability
Disclosure Essentials", and the `-ess` code suffix appears on only three of the five (`cheetah-vdp`
and `liveclicker-vdp` carry no marker). The matching `engagement_type.id` is
`d4c421ac-baed-4c71-bdbf-e9b0240088dd`. Rule in `bugcrowd-api-overview.md` § 3.

Submissions ("reports"/"issues" in other vendors' terminology) — confirmed on **2026-08-31**:

| Claim | Method | Result |
|---|---|---|
| Exactly one submission in state `new` | `GET /submissions?filter[state]=new` | ✅ `total_hits: 1`, id `4c5c9c87-1369-43ea-9496-904e2d2262fb` |
| Same, scoped to the program | `+ filter[program]=zetaglobal-vdp` | ✅ `total_hits: 1`, same id |
| Same, via the search endpoint | `POST /submissions/search {"filter":{"state":["new"]}}` | ✅ `total_hits: 1`, same id |

That submission: `source: email`, `severity: null`, `vrt_id: other`, submitted `2026-08-14T20:38:59Z`,
attached to engagement `zetaglobal-vdp-ess`. It is a beg-bounty email (subdomain-takeover report with
PayPal details), which is why it is still unrouted.

### State census — the eight states are exhaustive and mutually exclusive

A per-state census was run twice, org-wide and scoped to `zetaglobal-vdp`. **Both summed exactly to
the corresponding unfiltered `total_hits`**, so no submission sits in a ninth or null state and none
is double-counted. A per-program census summed exactly as well, across all 6 programs — so
`GET /submissions` with no `filter[program]` really does return every submission the credential can
see. The state enum, from a deliberate `400`:
`new, out-of-scope, not-applicable, not-reproducible, triaged, unresolved, resolved, informational`.

`triaged` held **0** records in every census, which is a real and expected state rather than a fault:
triage is a brief transition. Treat an empty `triaged` bucket as normal.

> **This queue is live — the per-state absolutes are not a regression baseline.** Within one session
> the `zetaglobal-vdp` breakdown moved from `unresolved 48 / resolved 257 / informational 92` to
> `unresolved 27 / resolved 287 / informational 83`; 30 records transitioned into `resolved` while
> testing, and the census still summed exactly both times. Re-verify against the *invariants* — the
> sum matching unfiltered `total_hits`, and the states partitioning the set — never against a count.
> The individual state counts are therefore deliberately not recorded here.

**Session baselines**, kept only because later sections use them as denominators: `total_hits` was
**1140** org-wide and **890** for `zetaglobal-vdp`, of which **217** carried a non-null `severity`.
Expect all three to have moved.

Other enums recovered the same way:

- `sort`: `submitted-asc`, `submitted-desc`, `severity-asc`, `severity-desc`, `updated-asc`,
  `updated-desc`. Note the sort keys are **not** attribute names — the attribute is `submitted_at`,
  the sort key is `submitted`; there is no `updated_at` attribute at all.
- `include` (25 values): `activities`, `activities.actor`, `activities.event`, `active_blocker`,
  `active_researcher_request_response`, `assignee`, `assignees`, `claim_ticket`, `comments`,
  `comments.author`, `comments.file_attachments`, `cvss_vector`, `duplicates`, `duplicate_of`,
  `external_issues`, `file_attachments`, `monetary_rewards`, `monetary_rewards.payments`, `program`,
  `program.organization`, `engagement`, `engagement_brief`,
  `engagement_brief.engagement_brief_target_groups`, `researcher`, `target`.
- A bogus `filter[...]` **key** gives `additional properties ['zzz'] … when none are allowed` without
  listing the valid keys — unlike bogus *values*, which do enumerate. Get the key list from
  `api-spec.yaml` (20 filters, identical for `GET /submissions` and `POST /submissions/search`).

## Deviations from the published spec

| # | Finding | Spec says | Production does |
|---|---|---|---|
| 1 | `Accept` header | `required: false` | **Mandatory.** Any other value — including the default `*/*` — returns `404` + HTML |
| 2 | Response `Content-Type` | `application/vnd.bugcrowd.v4+json` | Always `application/json; charset=utf-8` |
| 3 | Rate-limit headers | undocumented | `x-ratelimit-limit: 60`, `x-ratelimit-remaining: <n>` on every response. No reset header |
| 4 | Missing/invalid credential | `401` implied | `404` + HTML. `401` occurs *only* for an unrecognised scheme keyword (`Bearer`) |
| 5 | `links.next` | end-of-data signal | Always non-null, even at `total_hits: 1` and past the end of the set |
| 6 | `/programs/{id}/targets` `sort` | free string, `example: -created_at` | Enforces the `/programs` enum; `-created_at` and `created_at-desc` both `400` |
| 7 | `/programs/{id}/targets` filters | `explode: true` (repeat param) | Comma-joining works; repeating silently keeps only the last value |
| 8 | `/programs/{id}/targets` filter enums | enumerated | Not validated — bogus value returns `200` / `total_hits: 0` |
| 9 | `engagement_type` | `additionalProperties: false`, has `enabled_reports` | ~12 undocumented keys present; `enabled_reports` absent |
| 10 | `links.related.href` | a URL | Sometimes the literal string `"(NOT IMPLEMENTED YET)"` |
| 11 | Collection `meta` | `{count, total_hits}` | Also `deprecated_fields` / `deprecated_relationships` (currently: `assignee` → `assignees`) |
| 12 | `Bugcrowd-Version` | version override | Unrecognised values silently ignored (`1999-01-01` → `200`); no header echoes the version in effect |
| 13 | `POST /submissions/search` + `fields` | sparse fieldsets supported | **`fields` is silently ignored** — full 23-attribute payload returned. `filter`, `sort`, `page`, `include` all work |
| 14 | `POST /submissions/search` body | — | Filters must be **JSON arrays**; the comma-string form that works in the query string is a `400` |
| 15 | `filter[program]` / `filter[engagement]` | takes a code | Correct, but an unknown value **or a valid UUID** returns `200` / `total_hits: 0` — never a `400` |
| 16 | `filter[severity]` | `maxItems: 4` | Spec and server agree — but there are **5** severities, so "all severities" is unexpressible |
| 17 | Relationship `meta.count` | matches `data` | Can contradict it: `external_issues` returned `data: []`, `included: []`, `meta: {count: 1, total_hits: 1}` |
| 18 | `ListExternalIssueResponse` schema | — | No path in `paths` returns it; there is no external-issues endpoint |
| 19 | Report permalink | — | **No attribute anywhere exposes a UI URL.** `links.self` is the API path; `bug_url` is the *vulnerable* URL, not the report. UI links must be constructed by hand |
| 20 | File `download_url` redirect | authenticated endpoint returns a fresh 10-second S3 redirect | Bugcrowd's Varnish edge can replay redirects aged thousands of seconds. A unique query parameter produced a fresh redirect in every tested case |

### `program.name` is mutable; `program.code` is not

Observed on 2026-08-31: the program's `name` changed from `"Zeta Global Vulnerability Disclosure
Program"` to `"Zeta Global VDP"` while `code` (`zetaglobal-vdp`) and `id`
(`5bf97379-ad28-4fb3-929e-9b9872dfc667`) both stayed put. Never key on `name` — it is a display label
that changes without notice. Match on `code` (for `filter[program]`) or `id` (for relationships).

Current program names, for orientation — only `zetaglobal-vdp` is in active use; the other five are
legacy and hold historical submissions:

| Code | Name |
|---|---|
| `zetaglobal-vdp` | Zeta Global VDP |
| `rocketfuel` | Rocket Fuel |
| `rocketfuelse` | Rocket Fuel Social Engineering |
| `sizmek` | Sizmek Servers |
| `sizmek-brief-drafts` | Sizmek Servers *(duplicate name, distinct code)* |
| `zeta-global` | Zeta Global |

Note that `name` is **not unique** — `sizmek` and `sizmek-brief-drafts` share one. Two more reasons to
key on `code`.

## Probe details

### File attachment redirects can be stale at acquisition

Verified on 2026-09-15 with two different attachments. Each authenticated
`https://files.bugcrowd.com/{file_id}` request returned a `302` to an S3 URL with
`X-Amz-Expires=10`. Plain requests received redirects whose `Age` was in the thousands of seconds,
so S3 returned `403 AccessDenied` because the request had expired. Repeating the same origin request
returned the same redirect and request id, so reacquisition without changing the origin URL did not
help.

Sanitized probe shapes:

```bash
curl -sS -D origin.headers -o /dev/null \
  --url "https://files.bugcrowd.com/${FILE_ID}" \
  --header "Authorization: Token ${BUGCROWD_API_TOKEN}" \
  --header "Accept: application/vnd.bugcrowd+json"

curl -sS -D origin.headers -o /dev/null \
  --url "https://files.bugcrowd.com/${FILE_ID}" \
  --header "Authorization: Token ${BUGCROWD_API_TOKEN}" \
  --header "Accept: application/vnd.bugcrowd+json" \
  --header "Cache-Control: no-cache"

curl -sS -D origin.headers -o /dev/null \
  --url "https://files.bugcrowd.com/${FILE_ID}?_cb=${UNIQUE_NONCE}" \
  --header "Authorization: Token ${BUGCROWD_API_TOKEN}" \
  --header "Accept: application/vnd.bugcrowd+json"
```

Each `Location` was fetched separately without the Bugcrowd authorization header. The signed
locations and file ids are omitted because they grant access to private evidence.

| Origin request | Result |
|---|---|
| Plain | Origin `302`, observed `Age: 3126`, `X-Cache: MISS, HIT`; S3 `403 AccessDenied`, `Request has expired` |
| `Cache-Control: no-cache` request header | Origin `302` with a stale cached redirect; S3 `403 AccessDenied`, `Request has expired` |
| Unique query parameter | Origin `302`, `Age: 0`, `X-Cache: MISS, MISS`; S3 `200` with non-empty file bytes |

Use a fresh nonce on every acquisition attempt while constructing the request from the pinned
`files.bugcrowd.com` host and the trusted attachment id. Do not reuse any query string from the API
payload. This depends on the current Varnish cache key including unknown query parameters, which is
observed behavior rather than a published contract. Permanent failures must remain visible if that
behavior changes.

### Header and auth matrix

| Request | Status | Body type |
|---|---|---|
| `Accept: application/vnd.bugcrowd+json` + valid token | `200` | JSON |
| `Accept: application/vnd.bugcrowd.v4+json` | `200` | JSON (response still `application/json`) |
| `Accept: */*` | `404` | HTML |
| `Accept: application/nonsense+json` | `404` | `text/plain` |
| no `Accept` header | `404` | HTML |
| no `Authorization` header | `404` | HTML |
| `Authorization: Token aaaa:bbbb` (invalid) | `404` | HTML |
| `Authorization: Bearer <valid token>` | `401` | HTML |
| valid token, `GET /engagements/00000000-0000-0000-0000-000000000000` | `404` | **JSON** `errors` envelope |
| valid token, `GET /engagements/not-a-uuid` | `404` | **JSON** `errors` envelope |

→ **The body's content type discriminates auth/`Accept` failures (HTML) from genuine resource 404s
(JSON).** A malformed UUID is not distinguished from a missing one.

### Query-parameter validation

Strict everywhere except `/programs/{id}/targets`. Errors enumerate the accepted values, which makes
a deliberate bad request the cheapest way to discover an enum:

| Probe | Status | `detail` |
|---|---|---|
| `GET /engagements?filter[program]=zetaglobal-vdp` | `400` | `The property '#/' contains additional properties ['filter'] outside of the schema when none are allowed.` |
| `GET /engagements?sort=-created_at` | `400` | `… did not match one of the following values: created_at-asc, created_at-desc.` |
| `GET /engagements?page[limit]=500` | `400` | `The property '#/page/limit' did not have a maximum value of 100, inclusively.` |
| `GET /engagements?fields[engagement]=not_a_field` | `400` | lists all 15 valid `fields[engagement]` values |

### `filter[state]` hyphen vs underscore (`GET /submissions`, program `zetaglobal-vdp`)

| Value | Status | Result |
|---|---|---|
| `not-applicable` | `200` | matched, non-empty |
| `not_applicable` | `400` | `… did not match one of the following values: new, out-of-scope, not-applicable, not-reproducible, …` |
| `out-of-scope` | `200` | matched, non-empty |
| `out_of_scope` | `400` | as above |

→ The API returns `"state": "not_applicable"` in `attributes` but rejects that same spelling in the
filter. State values cannot be round-tripped from response to query without translating `_` → `-`.

### `/programs/zetaglobal-vdp/targets` filter arithmetic

| Query | `total_hits` |
|---|---|
| *(no filter)* | 33 |
| `filter[category]=api` | 4 |
| `filter[category]=website` | 24 |
| `filter[category]=api,website` (comma-joined) | **28** ✅ = 4 + 24 |
| `filter[category]=api` **&** `filter[category]=website` (repeated) | **24** ❌ last value only |
| `filter[category]=nonsense_category` | **0** ❌ no `400` |

### `/submissions` filter semantics

| Query | `total_hits` | Note |
|---|---|---|
| `filter[state]=new,out-of-scope` (comma-joined) | **14** ✅ | = 1 + 13, the correct union |
| `filter[state]=new` **&** `filter[state]=out-of-scope` (repeated) | **13** ❌ | last value only — same silent-drop bug as `/targets` |
| `filter[program]=zetaglobal-vdp` (code) | 890 | ✅ |
| `filter[program]=5bf97379-…` (the program's real UUID) | **0** ❌ | no error |
| `filter[program]=no-such-program` | **0** ❌ | no error |
| `filter[engagement]=zetaglobal-vdp-ess` (code) | 3 | ✅ |
| `filter[engagement]=4c4c8972-…` (that engagement's real UUID) | **0** ❌ | no error, even though the `new` submission's own `relationships.engagement.data.id` **is** that UUID |
| `filter[state]=New` (capitalised) | `400` | values are case-sensitive |
| `filter[severity]=1,2,3,4` | 195 | ✅ |
| `filter[severity]=5` | 22 | ✅ |
| `filter[severity]=1,2,3,4,5` | `400` | `'#/filter/severity' had more items than the allowed 4` |

→ **The repeat-vs-comma bug is API-wide, not a `/targets` quirk** (deviation #7). Always comma-join.

→ Only 217 of 1140 submissions carry a severity at all, so **any** `filter[severity]` silently
excludes the ~923 null-severity records — including the single `new` one. "All high-severity new
reports" returns zero for the wrong reason.

→ Engagement attribution is sparse: of the 890 `zetaglobal-vdp` submissions, only **3** are linked to
any engagement (all to `zetaglobal-vdp-ess`); the other 8 engagements return 0. `relationships.engagement`
is `null` on the rest. Filter by program, not engagement, to enumerate a program's reports.

### `filter[submitted]` reflects the import, not the report

`GET /submissions?filter[program]=zetaglobal-vdp&filter[submitted]=2026-04-20` returned **887 of the
program's 890** submissions. Every one of the 887 carried `source: csv` and a `submitted_at` inside a
**2.6-second window** (`2026-04-20T17:55:36.793Z` → `17:55:39.424Z`).

→ `submitted_at` is a settable create-only attribute, so a bulk migration stamps the whole backlog
with its own clock. On a migrated program the date filters partition by *import batch*, not by when
anything was reported, and the original filing dates are not recoverable through the API. Check the
spread of `submitted_at` (and whether `source` is `csv`) before presenting any date-based figure as a
reporting timeline.

### Constructing a report URL (unresolved)

There is no permalink attribute (deviation 19), so the UI URL must be built. Unauthenticated probes,
which distinguish a routable path from a non-existent one but cannot validate an id:

| Probe | Result |
|---|---|
| `bugcrowd.com/{program_code}/submissions/{id}` | `404` |
| `tracker.bugcrowd.com/{program_code}/submissions/{id}` | `302` → `/user/sign_in` |
| same shape with a bogus UUID | `302` → `/user/sign_in` |

→ The redirect proves the *route* exists but says nothing about the id, so the canonical form remains
**unconfirmed** without a logged-in session. `tracker.bugcrowd.com/{program_code}/submissions/{id}` is
the best-supported shape; flag it as constructed whenever you hand such a link to someone.

### `POST /submissions/search` vs `GET /submissions`

Both accept the identical 20 filter keys (diffed from `api-spec.yaml`); the `POST` form exists only to
escape URL-length limits. Verified differences:

| | `GET /submissions` | `POST /submissions/search` |
|---|---|---|
| `fields[submission]=title,state` / `{"fields":{"submission":["title","state"]}}` | **2** attributes ✅ | **23** attributes ❌ silently ignored |
| Multi-value filter form | `filter[state]=new` (comma string) | `{"state":["new"]}` — a bare string is a `400` |
| `filter` / `sort` / `page` / `include` | ✅ | ✅ (`include=program` populated `included`; `sort=submitted-desc` ordered correctly) |

→ The endpoint sold as the fix for oversized queries returns the **largest possible** response body,
`description` and all. If payload size matters, use `GET` with `fields[...]`, not `POST /search`.
This was the only non-`GET` request issued in this log; `POST /submissions/search` is read-only by
definition ("Returns a filtered list of submissions").

### Pagination edges (`GET /submissions?filter[program]=zetaglobal-vdp`, `total_hits: 890`)

| Query | Status | Result |
|---|---|---|
| `page[offset]=5000` (past the end) | `200` | `count: 0`, `links.next` still non-null |
| `page[offset]=9901` (old cap was 9900) | `200` | `count: 0`, accepted → token is on a post-`2025-04-23` version |
| `GET /organizations` with `total_hits: 1` | `200` | `links.next` → `page[offset]=25` despite one record |

→ Terminate pagination on `count == 0` or `offset + count >= total_hits`. Never on `links.next`.

### Relationship truncation at 100

`GET /programs/5bf97379-…?fields[program]=code,submissions` on a program with 890 submissions:

```
relationships.submissions.data            → array of exactly 100
relationships.submissions.links.related   → {"href": "/submissions?filter[program]=zetaglobal-vdp",
                                             "meta": {"count": 100, "total_hits": 890}}
```

→ Confirms the 100-record embedded cap. Here `links.related.href` **is** a usable path; on the
engagement resource the same field is the literal `"(NOT IMPLEMENTED YET)"`.

## Access level of the credential used

The token has direct program access to all 6 Zeta Global programs: submission `title`, `description`,
`state`, `severity`, and `source` were all populated across the full result set, with `email` and
`csv` the only `source` values observed. The `"Original submission in another program"`
title-redaction path was therefore **not** exercised and remains unverified.

## Not yet verified

- Any state-changing endpoint (`POST /submissions`, `PATCH`, `DELETE`) — nothing was written.
- The `last_transitioned_to_*_at` timestamps. All were `null` on the records inspected, and with
  `triaged` empty no submission was observed mid-transition, so their population is unconfirmed.
- Title/description redaction for submissions in programs the caller cannot access.
- Webhook `X-Bugcrowd-Digest` HMAC construction (requires a configured consumer endpoint).
- `429` response shape and whether a `Retry-After` header appears under real throttling.
- Severity direction (`1` = P1 = most severe) — taken from Bugcrowd's documented VRT priority model,
  not provable from the API alone.
