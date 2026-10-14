---
name: snyk-api
description: >
  Use this skill to develop code that interacts with the Snyk API or to directly interact with the Snyk API using tools like `curl`. This skill provides reference documentation, and guidelines for making API requests and handling errors for both the new REST API and the old V1 API.
---

# Snyk API Skill
## Reference Documentation
### New REST API
To get a high-level understanding of all available APIs in the new REST API, search this API index: `reference/snyk-rest-api-overview.md`.

For all details of specific APIs, perform searches in OpenAPI spec file: `references/rest-spec.json`, which provides rich, detailed information about all endpoints, request parameters, and response formats.

### Old v1 API
The old V1 API should only be used as a fallback when the new REST API does not yet have a certain endpoint that the V1 does have.

To get a high-level understanding of all available APIs in the old V1 API, search this API index: `reference/snyk-v1-api-overview.md`.

For all details of specific APIs, perform searches in OpenAPI spec file: `references/v1-api-spec.yaml`, which provides rich, detailed information about all endpoints, request parameters, and response formats.

## Environment Variables
The following environment variables are available in your deployment context:

- `SNYK_GROUP_ID`
- `SNYK_REST_API_VERSION`
- `SNYK_API_TOKEN`
- `SNYK_API_BASE_URL`   (optional, see Data Regions)
- `SNYK_DATA_REGION`    (optional, see Data Regions)

### When Generating Code
When generating code, follow these steps:

1. Load configuration values from environment variables at runtime.
2. Do not hardcode configuration values.
3. Read variables from `os.environ` (Python), `process.env` (Node.js), or equivalent for other languages.
4. Validate required variables before constructing any API request.
5. If a required variable is missing or invalid, fail with a clear error message that names the variable and corrective action.
6. After validation succeeds, construct and execute API requests.
7. Assume these environment variables are preloaded by the deployment environment.

Example implementation flow: read required variables, check for missing values, report exactly which variable is missing or invalid, then continue with API request construction.

### When Directly Interacting with the API
When directly interacting with the API (for example, by running a `curl` command or a Python script), assume these environment variables are available and use them appropriately. Reference them using shell variable syntax (e.g., `${SNYK_API_TOKEN}`). 

## HTTP Request Headers
When making requests to the API, include the following headers:
- `Content-Type: application/vnd.api+json`
- `Authorization: token {SNYK_API_TOKEN}`
- `Accept: */*`

Where `{SNYK_API_TOKEN}` is the Snyk API token used for authentication.

### Example `curl` commands
```bash
curl --request GET \
--url "${SNYK_API_BASE_URL}/orgs/{orgId}/projects?version=${SNYK_REST_API_VERSION}" \
--header "Content-Type: application/vnd.api+json" \
--header "Authorization: token ${SNYK_API_TOKEN}" \
--header "Accept: */*"
```

```bash
curl -sS --request GET \
--url "${SNYK_API_BASE_URL}/groups/${SNYK_GROUP_ID}/orgs?version=${SNYK_REST_API_VERSION}&limit=100" \
--header "Content-Type: application/vnd.api+json" \
--header "Authorization: token ${SNYK_API_TOKEN}" \
--header "Accept: */*" | jq '{count: (.data|length), next: .links.next, first_three: [.data[0:3][] | {id: .id, name: .attributes.name, slug: .attributes.slug}]}'
```

## Data Regions
If both `SNYK_API_BASE_URL` and `SNYK_DATA_REGION` are undefined, default to `SNYK-US-01`.
If `SNYK_API_BASE_URL` is defined, use it as the base URL regardless of region.
If `SNYK_API_BASE_URL` is undefined and `SNYK_DATA_REGION` is defined, use the table entry for that region.

### When Using new REST API
Use the following table to determine the base URLs per data region.

| Region | Base URL |
|--------|----------|
| SNYK-US-01 | https://api.snyk.io/rest |
| SNYK-US-02 | https://api.us.snyk.io/rest |
| SNYK-EU-01 | https://api.eu.snyk.io/rest |
| SNYK-AU-01 | https://api.au.snyk.io/rest |

### When Using old V1 API
Use the following table to determine the base URLs per data region.

| Region | Base URL |
|--------|----------|
| SNYK-US-01 | `https://api.snyk.io/v1/` |
| SNYK-US-02 | `https://api.us.snyk.io/v1/` |
| SNYK-EU-01 | `https://api.eu.snyk.io/v1/` |
| SNYK-AU-01 | `https://api.au.snyk.io/v1/` |

## Error Handling
When directly interacting with the API, for example, by performing a request by using `curl`, you may encounter error responses.
If the API returns an error response, provide a detailed explanation of the error and suggest possible resolutions.
If the API indicates the token is invalid or expired (for example, 401 or 403 authentication/authorization errors), instruct the user to verify the token value, regenerate it if needed, update `SNYK_API_TOKEN`, and retry the request.