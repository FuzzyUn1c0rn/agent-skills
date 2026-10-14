# Snyk v1 API — Overview

This document provides a structured overview of all endpoints defined in the Snyk **v1 API** specification. The v1 API is the older, predecessor to the modern Snyk REST API — prefer the REST API for new work. Some capabilities (notably user/member management, ignores, and test/monitor endpoints for specific package manifests) still only exist in v1.

Endpoints are grouped by functional theme, mirroring the tags defined in the spec.

## 1. Users

Endpoints for fetching information about the currently authenticated user or another user by ID.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/user/me` | Get the profile of the currently authenticated user. |
| `GET` | `/user/{userId}` | Get details for a specific user by ID. |

## 2. Notification Settings

Endpoints for managing the current user's notification preferences at organization and project scopes.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/user/me/notification-settings/org/{orgId}` | Get organization-level notification settings for the current user. |
| `PUT` | `/user/me/notification-settings/org/{orgId}` | Modify organization-level notification settings. |
| `GET` | `/user/me/notification-settings/org/{orgId}/project/{projectId}` | Get project-level notification settings for the current user. |
| `PUT` | `/user/me/notification-settings/org/{orgId}/project/{projectId}` | Modify project-level notification settings. |

## 3. Groups

Endpoints for managing Snyk Groups — group membership, organizations within a group, tags, roles, and group-level settings.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/group/{groupId}/settings` | View group settings. |
| `PUT` | `/group/{groupId}/settings` | Update group settings. |
| `GET` | `/group/{groupId}/members` | List all members in a group. |
| `POST` | `/group/{groupId}/org/{orgId}/members` | Add a member to an organization within a group. |
| `GET` | `/group/{groupId}/orgs` | List all organizations in a group. |
| `GET` | `/group/{groupId}/roles` | List all roles defined for the group. |
| `GET` | `/group/{groupId}/tags` | List all tags used in the group. |
| `POST` | `/group/{groupId}/tags/delete` | Delete a tag from the group. |

## 4. Organizations

Endpoints for creating and managing Snyk Organizations, including settings and lifecycle.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs` | List all organizations the authenticated user belongs to. |
| `POST` | `/org` | Create a new organization. |
| `DELETE` | `/org/{orgId}` | Remove an organization. |
| `GET` | `/org/{orgId}/settings` | View organization settings. |
| `PUT` | `/org/{orgId}/settings` | Update organization settings. |
| `GET` | `/org/{orgId}/notification-settings` | Get organization-wide notification settings. |
| `PUT` | `/org/{orgId}/notification-settings` | Set organization-wide notification settings. |

## 5. Organization Members & Provisioning

Endpoints for managing org membership — listing members, inviting/provisioning users, updating roles, and removing users. This is the primary location in the API for user administration workflows (the REST API has partial coverage).

### Members

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/org/{orgId}/members` | List members of the organization. |
| `PUT` | `/org/{orgId}/members/{userId}` | Update a member in the organization. |
| `DELETE` | `/org/{orgId}/members/{userId}` | Remove a member from the organization. |
| `PUT` | `/org/{orgId}/members/update/{userId}` | Update a member's role in the organization. |

### Invitations & Provisioning

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/org/{orgId}/invite` | Invite one or more users to the organization by email. |
| `POST` | `/org/{orgId}/provision` | Provision a user to the organization (pre-create membership). |
| `GET` | `/org/{orgId}/provision` | List pending user provisions. |
| `DELETE` | `/org/{orgId}/provision` | Delete a pending user provision. |

## 6. Integrations

Endpoints for configuring source control, registry, and tool integrations at the organization scope — including credential management, broker tokens, and integration settings.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/org/{orgId}/integrations` | List all integrations for an organization. |
| `POST` | `/org/{orgId}/integrations` | Add a new integration. |
| `GET` | `/org/{orgId}/integrations/{type}` | Get an existing integration by type (e.g. `github`, `docker-hub`). |
| `PUT` | `/org/{orgId}/integrations/{integrationId}` | Update an existing integration. |
| `POST` | `/org/{orgId}/integrations/{integrationId}/clone` | Clone an integration (with settings and credentials). |
| `GET` | `/org/{orgId}/integrations/{integrationId}/settings` | Get settings for a specific integration. |
| `PUT` | `/org/{orgId}/integrations/{integrationId}/settings` | Update settings for a specific integration. |
| `DELETE` | `/org/{orgId}/integrations/{integrationId}/authentication` | Delete integration credentials. |
| `POST` | `/org/{orgId}/integrations/{integrationId}/authentication/provision-token` | Provision a new broker token. |
| `POST` | `/org/{orgId}/integrations/{integrationId}/authentication/switch-token` | Switch between broker tokens. |

## 7. Import Projects

Endpoints for importing targets (repos, images, manifests) into Snyk via a configured integration.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/org/{orgId}/integrations/{integrationId}/import` | Import targets via an integration. |
| `GET` | `/org/{orgId}/integrations/{integrationId}/import/{jobId}` | Get the status and details of an import job. |

## 8. Projects

Endpoints for managing Snyk Projects — the individual monitored manifests, repositories, or images.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/org/{orgId}/project/{projectId}` | Retrieve a single project. |
| `PUT` | `/org/{orgId}/project/{projectId}` | Update a project. |
| `DELETE` | `/org/{orgId}/project/{projectId}` | Delete a project. |
| `POST` | `/org/{orgId}/project/{projectId}/activate` | Activate a project. |
| `POST` | `/org/{orgId}/project/{projectId}/deactivate` | Deactivate a project. |
| `PUT` | `/org/{orgId}/project/{projectId}/move` | Move a project to a different organization. |
| `GET` | `/org/{orgId}/project/{projectId}/settings` | List project settings. |
| `PUT` | `/org/{orgId}/project/{projectId}/settings` | Update project settings. |
| `DELETE` | `/org/{orgId}/project/{projectId}/settings` | Delete project settings. |
| `POST` | `/org/{orgId}/project/{projectId}/tags` | Add a tag to a project. |
| `POST` | `/org/{orgId}/project/{projectId}/tags/remove` | Remove a tag from a project. |
| `POST` | `/org/{orgId}/project/{projectId}/attributes` | Apply attributes (criticality, environment, lifecycle) to a project. |
| `GET` | `/org/{orgId}/project/{projectId}/dep-graph` | Get a project's dependency graph. |

## 9. Project Issues, Ignores & Jira

Endpoints for inspecting issues found in projects, managing ignore rules, and linking issues to Jira.

### Aggregated Issues & Paths

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/org/{orgId}/project/{projectId}/aggregated-issues` | List all aggregated issues in a project. |
| `GET` | `/org/{orgId}/project/{projectId}/issue/{issueId}/paths` | List all paths for a project issue. |
| `POST` | `/org/{orgId}/project/{projectId}/history` | List project snapshots. |
| `POST` | `/org/{orgId}/project/{projectId}/history/{snapshotId}/aggregated-issues` | List aggregated issues for a snapshot. |
| `GET` | `/org/{orgId}/project/{projectId}/history/{snapshotId}/issue/{issueId}/paths` | List issue paths for a snapshot. |

### Ignores

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/org/{orgId}/project/{projectId}/ignores` | List all ignores for a project. |
| `GET` | `/org/{orgId}/project/{projectId}/ignore/{issueId}` | Retrieve a specific ignore rule. |
| `POST` | `/org/{orgId}/project/{projectId}/ignore/{issueId}` | Add an ignore for an issue. |
| `PUT` | `/org/{orgId}/project/{projectId}/ignore/{issueId}` | Replace ignores for an issue. |
| `DELETE` | `/org/{orgId}/project/{projectId}/ignore/{issueId}` | Delete ignores for an issue. |

### Jira

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/org/{orgId}/project/{projectId}/jira-issues` | List all Jira issues linked to a project. |
| `POST` | `/org/{orgId}/project/{projectId}/issue/{issueId}/jira-issue` | Create a Jira issue from a Snyk issue. |

## 10. Dependencies & Licenses

Endpoints for listing dependencies and license information across an organization.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/org/{orgId}/dependencies` | List all dependencies across the organization, filterable by project/package. |
| `POST` | `/org/{orgId}/licenses` | List all licenses across the organization. |

## 11. Entitlements

Endpoints for querying which Snyk product entitlements are active for an organization.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/org/{orgId}/entitlements` | List all entitlements for an organization. |
| `GET` | `/org/{orgId}/entitlement/{entitlementKey}` | Get the value of a specific entitlement. |

## 12. Test (Public Packages & Manifests)

On-demand vulnerability testing of public packages (by coordinates) and of package manifests (by file content). The `GET` variants test a known public package; the `POST` variants test an uploaded manifest.

### Maven

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/test/maven/{groupId}/{artifactId}/{version}` | Test a public Maven package by coordinates. |
| `POST` | `/test/maven` | Test a Maven manifest file. |

### npm / Yarn

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/test/npm/{packageName}/{version}` | Test a public npm package by name and version. |
| `POST` | `/test/npm` | Test `package.json` & `package-lock.json`. |
| `POST` | `/test/yarn` | Test `package.json` & `yarn.lock`. |

### RubyGems

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/test/rubygems/{gemName}/{version}` | Test a public gem by name and version. |
| `POST` | `/test/rubygems` | Test a `Gemfile.lock` file. |

### Gradle / sbt

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/test/gradle/{group}/{name}/{version}` | Test a public Gradle-resolvable package. |
| `POST` | `/test/gradle` | Test a Gradle manifest file. |
| `GET` | `/test/sbt/{groupId}/{artifactId}/{version}` | Test a public sbt package by coordinates. |
| `POST` | `/test/sbt` | Test an sbt manifest file. |

### Python

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/test/pip/{packageName}/{version}` | Test a public pip package by name and version. |
| `POST` | `/test/pip` | Test a `requirements.txt` file. |

### Go

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/test/golangdep` | Test `Gopkg.toml` & `Gopkg.lock`. |
| `POST` | `/test/govendor` | Test a `vendor.json` file. |

### PHP

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/test/composer` | Test `composer.json` & `composer.lock`. |

## 13. Test & Monitor (Dep Graph)

Generic dependency-graph-based test and monitor endpoints — the ecosystem-agnostic alternatives to the manifest-specific endpoints above.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/test/dep-graph` | Test an arbitrary dependency graph for issues. |
| `POST` | `/monitor/dep-graph` | Submit a dependency graph for continuous monitoring. |

## 14. Reporting API

Endpoints for querying aggregate issue and project counts across an organization or group. Used to power dashboards and scheduled reports.

### Issues

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/reporting/issues/latest` | Get the latest issues. |
| `POST` | `/reporting/issues` | Get issues over a time range. |
| `POST` | `/reporting/counts/issues/latest` | Get latest issue counts. |
| `POST` | `/reporting/counts/issues` | Get issue counts over a time range. |

### Projects & Tests

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/reporting/counts/projects/latest` | Get latest project counts. |
| `POST` | `/reporting/counts/projects` | Get project counts over a time range. |
| `POST` | `/reporting/counts/tests` | Get test run counts over a time range. |

## 15. Webhooks

Endpoints for managing organization-scoped webhooks that deliver event notifications to external systems.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/org/{orgId}/webhooks` | List webhooks for an organization. |
| `POST` | `/org/{orgId}/webhooks` | Create a webhook. |
| `GET` | `/org/{orgId}/webhooks/{webhookId}` | Retrieve a specific webhook. |
| `DELETE` | `/org/{orgId}/webhooks/{webhookId}` | Delete a webhook. |
| `POST` | `/org/{orgId}/webhooks/{webhookId}/ping` | Send a test ping through a webhook. |

---

*Document generated from the Snyk v1 API specification (`v1-api-spec.yaml`). The v1 API is the legacy API; prefer the Snyk REST API for new integrations unless a needed capability only exists here.*
