# Snyk REST API — Overview

This document provides a structured overview of all APIs defined in the Snyk REST specification. The 185 endpoints are grouped by functional theme. Endpoints marked **[EA]** are in Early Access.

## 1. Authentication & User Identity

Endpoints for the currently authenticated user: fetching profile details, managing personal access tokens, installed apps, and access requests.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/self` | Get the profile of the currently authenticated user. |
| `GET` | `/self/access_requests` | List pending access requests submitted by the current user. **[EA]** |
| `GET` | `/self/apps` | List all Snyk Apps the current user has authorized. |
| `GET` | `/self/apps/installs` | List all app installations for the current user. |
| `DELETE` | `/self/apps/installs/{install_id}` | Revoke an app installation for the current user. |
| `DELETE` | `/self/apps/{app_id}` | Revoke authorization for a specific app. |
| `GET` | `/self/apps/{app_id}/sessions` | List active sessions for a given app. |
| `DELETE` | `/self/apps/{app_id}/sessions/{session_id}` | Terminate a specific app session. |
| `GET` | `/self/personal_access_tokens` | List all personal access tokens for the current user. |
| `DELETE` | `/self/personal_access_tokens/{personal_access_token_id}` | Delete a personal access token. |

## 2. Organizations

Endpoints for listing and managing Snyk Organizations — the core unit of project and team grouping.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs` | List all organizations accessible to the authenticated user. |
| `GET` | `/orgs/{org_id}` | Retrieve details of a specific organization. |
| `PATCH` | `/orgs/{org_id}` | Update settings or metadata for an organization. |
| `GET` | `/orgs/{org_id}/memberships` | List all members of the organization. |
| `POST` | `/orgs/{org_id}/memberships` | Add a user to the organization with a given role. |
| `PATCH` | `/orgs/{org_id}/memberships/{membership_id}` | Update a user's role within the organization. |
| `DELETE` | `/orgs/{org_id}/memberships/{membership_id}` | Remove a user's membership from the organization. |
| `GET` | `/orgs/{org_id}/invites` | List pending invitations to the organization. |
| `POST` | `/orgs/{org_id}/invites` | Send an invitation to a user to join the organization. |
| `DELETE` | `/orgs/{org_id}/invites/{invite_id}` | Cancel a pending invitation. |
| `GET` | `/orgs/{org_id}/users/{id}` | Get a user's details within the organization. **[EA]** |

## 3. Groups

Endpoints for managing Snyk Groups — the top-level hierarchy above organizations. Includes group membership, SSO connections, and group-level settings.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/groups` | List all groups accessible to the authenticated user. **[EA]** |
| `GET` | `/groups/{group_id}` | Retrieve details of a specific group. **[EA]** |
| `GET` | `/groups/{group_id}/orgs` | List all organizations within the group. |
| `GET` | `/groups/{group_id}/memberships` | List all memberships in the group. |
| `POST` | `/groups/{group_id}/memberships` | Add a user to the group with a specified role. |
| `PATCH` | `/groups/{group_id}/memberships/{membership_id}` | Update a user's role in the group. |
| `DELETE` | `/groups/{group_id}/memberships/{membership_id}` | Remove a member from the group. |
| `GET` | `/groups/{group_id}/org_memberships` | List all organization memberships for users in the group. |
| `PATCH` | `/groups/{group_id}/users/{id}` | Update a user's role within a group. **[EA]** |
| `GET` | `/groups/{group_id}/sso_connections` | List all SSO connections configured for the group. **[EA]** |
| `GET` | `/groups/{group_id}/sso_connections/{sso_id}/users` | List all users authenticating via a given SSO connection. **[EA]** |
| `DELETE` | `/groups/{group_id}/sso_connections/{sso_id}/users/{user_id}` | Remove a user from a group's SSO connection. **[EA]** |

## 4. Tenants

Endpoints for managing Tenants — the highest-level entity in Snyk's hierarchy, above groups. Includes tenant metadata, memberships, and custom role management.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tenants` | List all tenants accessible to the authenticated user. |
| `GET` | `/tenants/{tenant_id}` | Retrieve details of a specific tenant. |
| `PATCH` | `/tenants/{tenant_id}` | Update tenant-level metadata or settings. |
| `GET` | `/tenants/{tenant_id}/memberships` | List all memberships within the tenant. **[EA]** |
| `PATCH` | `/tenants/{tenant_id}/memberships/{membership_id}` | Update a user's tenant membership (e.g., role). **[EA]** |
| `DELETE` | `/tenants/{tenant_id}/memberships/{membership_id}` | Remove a user's membership from the tenant. **[EA]** |
| `GET` | `/tenants/{tenant_id}/roles` | List all available roles defined for the tenant. **[EA]** |
| `POST` | `/tenants/{tenant_id}/roles` | Create a custom role for the tenant. **[EA]** |
| `GET` | `/tenants/{tenant_id}/roles/{role_id}` | Retrieve a specific tenant role. **[EA]** |
| `PATCH` | `/tenants/{tenant_id}/roles/{role_id}` | Update a custom tenant role. **[EA]** |
| `DELETE` | `/tenants/{tenant_id}/roles/{role_id}` | Delete a custom tenant role. **[EA]** |

## 5. Users & Memberships

User-specific endpoints scoped to the authenticated user's self-service or to group/org administrative operations (see also Organizations and Groups sections).

> Most user management operations are nested under `/orgs`, `/groups`, or `/self`. See those sections for the full list.

## 6. Service Accounts

Endpoints for creating and managing machine (non-human) service accounts at both organization and group scopes. Service accounts are used for CI/CD pipelines and automated workflows.

### Organization Service Accounts

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/service_accounts` | List all service accounts for the organization. |
| `POST` | `/orgs/{org_id}/service_accounts` | Create a new service account for the organization. |
| `GET` | `/orgs/{org_id}/service_accounts/{serviceaccount_id}` | Retrieve a specific service account. |
| `PATCH` | `/orgs/{org_id}/service_accounts/{serviceaccount_id}` | Update a service account's name or role. |
| `DELETE` | `/orgs/{org_id}/service_accounts/{serviceaccount_id}` | Delete a service account. |
| `POST` | `/orgs/{org_id}/service_accounts/{serviceaccount_id}/secrets` | Rotate or manage the client secret for a service account. |

### Group Service Accounts

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/groups/{group_id}/service_accounts` | List all service accounts for the group. |
| `POST` | `/groups/{group_id}/service_accounts` | Create a new service account at group level. |
| `GET` | `/groups/{group_id}/service_accounts/{serviceaccount_id}` | Retrieve a specific group service account. |
| `PATCH` | `/groups/{group_id}/service_accounts/{serviceaccount_id}` | Update a group service account. |
| `DELETE` | `/groups/{group_id}/service_accounts/{serviceaccount_id}` | Delete a group service account. |
| `POST` | `/groups/{group_id}/service_accounts/{serviceaccount_id}/secrets` | Manage the client secret for a group service account. |

## 7. Apps & App Bots

Endpoints for creating, managing, and installing Snyk Apps — OAuth-based third-party or internal integrations. Also covers App Bots (non-interactive app installations).

### App Management (Creation & Secrets)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/apps` | List all apps created by the organization. |
| `POST` | `/orgs/{org_id}/apps` | Create a new Snyk App for the organization. |
| `GET` | `/orgs/{org_id}/apps/{client_id}` | Retrieve an app by its client ID. |
| `PATCH` | `/orgs/{org_id}/apps/{client_id}` | Update app attributes (name, redirect URIs, token TTL). |
| `DELETE` | `/orgs/{org_id}/apps/{client_id}` | Delete an app. |
| `POST` | `/orgs/{org_id}/apps/{client_id}/secrets` | Manage client secrets for an app. |
| `GET` | `/orgs/{org_id}/apps/creations` | List all apps created by the organization (alternative endpoint). |
| `POST` | `/orgs/{org_id}/apps/creations` | Create a new app (alternative endpoint). |
| `GET` | `/orgs/{org_id}/apps/creations/{app_id}` | Retrieve a specific app by app ID. |
| `PATCH` | `/orgs/{org_id}/apps/creations/{app_id}` | Update app metadata by app ID. |
| `DELETE` | `/orgs/{org_id}/apps/creations/{app_id}` | Delete a specific app by app ID. |
| `POST` | `/orgs/{org_id}/apps/creations/{app_id}/secrets` | Manage client secrets for a specific app. |

### App Installations (Org & Group)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/apps/installs` | List all Snyk Apps installed for an organization. |
| `POST` | `/orgs/{org_id}/apps/installs` | Install a Snyk App for an organization. |
| `DELETE` | `/orgs/{org_id}/apps/installs/{install_id}` | Revoke an app installation from an organization. |
| `POST` | `/orgs/{org_id}/apps/installs/{install_id}/secrets` | Manage the client secret for a non-interactive app installation. |
| `GET` | `/groups/{group_id}/apps/installs` | List all Snyk Apps installed for a group. |
| `POST` | `/groups/{group_id}/apps/installs` | Install a Snyk App for a group. |
| `DELETE` | `/groups/{group_id}/apps/installs/{install_id}` | Revoke an app installation from a group. |
| `POST` | `/groups/{group_id}/apps/installs/{install_id}/secrets` | Manage the client secret for a non-interactive group app installation. |

### App Bots

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/app_bots` | List all app bots authorized for the organization. |
| `DELETE` | `/orgs/{org_id}/app_bots/{bot_id}` | Revoke authorization for an app bot. |

## 8. Integrations & Broker

Endpoints for managing source control, registry, and tool integrations, plus the Snyk Broker infrastructure for connecting self-hosted systems.

### Integrations (Org-level)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/integrations` | List all integrations configured for an organization. **[EA]** |
| `POST` | `/orgs/{org_id}/integrations` | Create a new integration for an organization. **[EA]** |
| `GET` | `/orgs/{org_id}/integrations/{integration_id}` | Retrieve a specific integration. **[EA]** |
| `PATCH` | `/orgs/{org_id}/integrations/{integration_id}` | Update an existing integration. **[EA]** |
| `DELETE` | `/orgs/{org_id}/integrations/{integration_id}` | Delete an integration. **[EA]** |
| `GET` | `/orgs/{org_id}/integrations/{integration_id}/settings` | Get settings for a specific integration. **[EA]** |
| `PATCH` | `/orgs/{org_id}/integrations/{integration_id}/settings` | Update settings for a specific integration. **[EA]** |

### Broker Connections

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/brokers/connections` | List all Broker connections for a given organization. |
| `GET` | `/tenants/{tenant_id}/brokers/deployments` | List all Broker deployments at tenant level. |
| `GET` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments` | List all Broker deployments for an install. |
| `POST` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments` | Create a new Broker deployment. |
| `PATCH` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}` | Update a Broker deployment. |
| `DELETE` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}` | Delete a Broker deployment. |
| `GET` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}/connections` | List all connections for a Broker deployment. |
| `POST` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}/connections` | Create a new Broker connection. |
| `GET` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}/connections/{connection_id}` | Retrieve a specific Broker connection. |
| `PATCH` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}/connections/{connection_id}` | Update a Broker connection. |
| `DELETE` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}/connections/{connection_id}` | Delete a specific Broker connection. |
| `DELETE` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}/connections` | Bulk delete Broker connections for a deployment. |
| `GET` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}/connections/{connection_id}/bulk_migration` | List organizations eligible for bulk migration via a Broker connection. |
| `POST` | `/tenants/{tenant_id}/brokers/connections/{connection_id}/orgs/{org_id}/integration` | Create an integration configuration for a Broker connection. |
| `DELETE` | `/tenants/{tenant_id}/brokers/connections/{connection_id}/orgs/{org_id}/integrations/{integration_id}` | Remove an integration from a Broker connection. |
| `GET` | `/tenants/{tenant_id}/brokers/installs/{install_id}/connections/{connection_id}/integrations` | List integrations associated with a Broker connection. |

### Broker Contexts

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tenants/{tenant_id}/brokers/installs/{install_id}/connections/{connection_id}/contexts` | List all contexts for a Broker connection. |
| `GET` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}/contexts` | List all contexts for a Broker deployment. |
| `POST` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}/contexts` | Create a new Broker context. |
| `GET` | `/tenants/{tenant_id}/brokers/installs/{install_id}/contexts/{context_id}` | Retrieve a specific Broker context. |
| `PATCH` | `/tenants/{tenant_id}/brokers/installs/{install_id}/contexts/{context_id}` | Update a Broker context. |
| `DELETE` | `/tenants/{tenant_id}/brokers/installs/{install_id}/contexts/{context_id}` | Delete a Broker context. |
| `PATCH` | `/tenants/{tenant_id}/brokers/installs/{install_id}/contexts/{context_id}/integration` | Associate an integration with a Broker context. |
| `DELETE` | `/tenants/{tenant_id}/brokers/installs/{install_id}/contexts/{context_id}/integrations/{integration_id}` | Remove an integration from a Broker context. |

### Broker Deployment Credentials

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}/credentials` | List all credentials for a Broker deployment. |
| `POST` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}/credentials` | Create a new credential for a Broker deployment. |
| `GET` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}/credentials/{credential_id}` | Retrieve a specific deployment credential. |
| `PATCH` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}/credentials/{credential_id}` | Update a deployment credential. |
| `DELETE` | `/tenants/{tenant_id}/brokers/installs/{install_id}/deployments/{deployment_id}/credentials/{credential_id}` | Delete a deployment credential. |

## 9. Projects

Endpoints for managing Snyk Projects — individual monitored repositories, manifests, or configurations within an organization.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/projects` | List all projects in an organization, with optional filtering. |
| `GET` | `/orgs/{org_id}/projects/{project_id}` | Retrieve details of a specific project. |
| `PATCH` | `/orgs/{org_id}/projects/{project_id}` | Update project attributes (e.g., name, settings, tags). |
| `DELETE` | `/orgs/{org_id}/projects/{project_id}` | Delete a project from the organization. |
| `GET` | `/orgs/{org_id}/projects/{project_id}/sbom` | Get the Software Bill of Materials (SBOM) document for a project. |

## 10. Targets

Endpoints for managing Targets — the source control repositories or other monitored sources that projects are imported from.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/targets` | List all targets in an organization. |
| `GET` | `/orgs/{org_id}/targets/{target_id}` | Retrieve a specific target. |
| `DELETE` | `/orgs/{org_id}/targets/{target_id}` | Delete a target and all its associated projects. |

## 11. Issues & Vulnerabilities

Endpoints for querying security issues detected by Snyk, available at both organization and group scope.

### Organization Issues

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/issues` | List all issues for an organization, with filtering by severity, type, etc. |
| `GET` | `/orgs/{org_id}/issues/{issue_id}` | Retrieve full details of a specific issue. |

### Group Issues

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/groups/{group_id}/issues` | List all issues across all organizations in a group. |
| `GET` | `/groups/{group_id}/issues/{issue_id}` | Retrieve a specific issue at group scope. |

## 12. Packages

Endpoints for querying vulnerability information for specific open source packages using PURL (Package URL) identifiers.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/packages/{purl}/issues` | List all known issues for a specific package (identified by PURL). |
| `POST` | `/orgs/{org_id}/packages/issues` | Batch-query issues for multiple packages at once. (Currently not available to all customers.) |
| `GET` | `/orgs/{org_id}/ecosystems/{ecosystem}/packages/{package_name}` | Get metadata for a specific package in a given ecosystem. **[EA]** |
| `GET` | `/orgs/{org_id}/ecosystems/{ecosystem}/packages/{package_name}/versions/{package_version}` | Get metadata for a specific version of a package. **[EA]** |

## 13. Cloud Security

Endpoints for managing cloud environments (AWS, Azure, GCP), scanning infrastructure resources, and generating cloud provider permissions for Snyk Cloud.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/cloud/environments` | List all registered cloud environments for an organization. **[EA]** |
| `POST` | `/orgs/{org_id}/cloud/environments` | Register a new cloud environment (e.g., AWS account). **[EA]** |
| `PATCH` | `/orgs/{org_id}/cloud/environments/{environment_id}` | Update a registered cloud environment. **[EA]** |
| `DELETE` | `/orgs/{org_id}/cloud/environments/{environment_id}` | Remove a cloud environment from monitoring. **[EA]** |
| `POST` | `/orgs/{org_id}/cloud/permissions` | Generate the required cloud provider permissions for Snyk scanning. **[EA]** |
| `GET` | `/orgs/{org_id}/cloud/resources` | List cloud resources discovered in registered environments. **[EA]** |
| `GET` | `/orgs/{org_id}/cloud/scans` | List all cloud infrastructure scans for the organization. **[EA]** |
| `POST` | `/orgs/{org_id}/cloud/scans` | Trigger a new cloud infrastructure scan. **[EA]** |
| `GET` | `/orgs/{org_id}/cloud/scans/{scan_id}` | Get the status and results of a specific scan. **[EA]** |

## 14. Container Images & Import Policies

Endpoints for listing container images monitored by Snyk, and for managing automated container registry import policies.

### Container Images

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/container_images` | List all container image instances monitored by the organization. |
| `GET` | `/orgs/{org_id}/container_images/{image_id}` | Retrieve details of a specific container image. |
| `GET` | `/orgs/{org_id}/container_images/{image_id}/relationships/image_target_refs` | List target references associated with a container image. |

### Container Registry Import Policies

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/container_import/{integration_id}/policy` | Get the import policy for a container registry integration. |
| `POST` | `/orgs/{org_id}/container_import/{integration_id}/policy` | Create an import policy for a container registry integration. |
| `PATCH` | `/orgs/{org_id}/container_import/{integration_id}/policy` | Update an existing container import policy. |
| `DELETE` | `/orgs/{org_id}/container_import/{integration_id}/policy` | Delete a container import policy. |
| `POST` | `/orgs/{org_id}/container_import/{integration_id}/policy/dry_run` | Run a dry-run simulation of an import policy without applying changes. |
| `GET` | `/orgs/{org_id}/container_import/{integration_id}/policy/dry_run/{job_id}` | Get the status of a container import policy dry-run job. |

## 15. Custom Base Images

Endpoints for managing custom base images used in container scanning. Custom base images define trusted base layers against which Snyk assesses container projects.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/custom_base_images` | List all custom base images available in the account. |
| `POST` | `/custom_base_images` | Create a new custom base image from an existing container project. |
| `GET` | `/custom_base_images/{custombaseimage_id}` | Retrieve a specific custom base image. |
| `PATCH` | `/custom_base_images/{custombaseimage_id}` | Update a custom base image's metadata or versioning scheme. |
| `DELETE` | `/custom_base_images/{custombaseimage_id}` | Delete a custom base image. |

## 16. Assets & Inventory

Endpoints for querying and managing Snyk's unified asset inventory — a unified view of all repositories, packages, and artifacts across your development ecosystem. Available at org, group, and tenant scopes.

### Asset Aliases (Repository)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/assets/repository/aliases` | List repository aliases in an organization. **[EA]** |
| `POST` | `/orgs/{org_id}/assets/repository/aliases` | Add an alias for a repository asset in an organization. **[EA]** |
| `DELETE` | `/orgs/{org_id}/assets/repository/aliases` | Bulk remove repository aliases in an organization. **[EA]** |
| `GET` | `/groups/{group_id}/assets/repository/aliases` | List repository aliases in a group. **[EA]** |
| `POST` | `/groups/{group_id}/assets/repository/aliases` | Add an alias for a repository asset in a group. **[EA]** |
| `DELETE` | `/groups/{group_id}/assets/repository/aliases` | Bulk remove repository aliases in a group. **[EA]** |

### Asset Search (Legacy)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/groups/{group_id}/assets/search` | Search and filter assets within a group. **[EA]** |
| `GET` | `/groups/{group_id}/assets/{asset_id}` | Get a specific asset in a group by ID. **[EA]** |
| `PATCH` | `/groups/{group_id}/assets/{asset_id}` | Update asset attributes at group scope. **[EA]** |
| `GET` | `/groups/{group_id}/assets/{asset_id}/relationships/assets` | List assets related to a given asset. **[EA]** |
| `GET` | `/groups/{group_id}/assets/{asset_id}/relationships/projects` | List projects linked to a given asset in a group. **[EA]** |

### Inventory Assets — Organization Scope

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/inventory/assets` | List or search all assets synchronously at org scope. **[EA]** |
| `PATCH` | `/orgs/{org_id}/inventory/assets` | Bulk update asset attributes at org scope. **[EA]** |
| `GET` | `/orgs/{org_id}/inventory/assets/filters` | Get available filter fields for asset queries. **[EA]** |
| `GET` | `/orgs/{org_id}/inventory/assets/filters/{filter_id}/values` | Get autocomplete suggestions for a given filter field. **[EA]** |
| `GET` | `/orgs/{org_id}/inventory/assets/groups` | Get available grouping fields for asset aggregation. **[EA]** |
| `GET` | `/orgs/{org_id}/inventory/assets/groups/{group_field_id}/values` | Get aggregated values for a grouping field. **[EA]** |
| `POST` | `/orgs/{org_id}/inventory/assets/searches` | Create an asynchronous asset search job. **[EA]** |
| `GET` | `/orgs/{org_id}/inventory/assets/searches/{search_id}/results` | Retrieve results of an asynchronous asset search. **[EA]** |
| `GET` | `/orgs/{org_id}/inventory/assets/{asset_id}` | Get a single asset by ID at org scope. **[EA]** |
| `PATCH` | `/orgs/{org_id}/inventory/assets/{asset_id}` | Update attributes of a specific asset at org scope. **[EA]** |
| `GET` | `/orgs/{org_id}/inventory/assets/{asset_id}/relationships/projects` | List projects linked to an asset at org scope. **[EA]** |
| `GET` | `/orgs/{org_id}/inventory/assets/{asset_id}/relationships/targets` | List targets linked to an asset at org scope. **[EA]** |

### Inventory Assets — Group Scope

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/groups/{group_id}/inventory/assets` | List or search all assets synchronously at group scope. **[EA]** |
| `PATCH` | `/groups/{group_id}/inventory/assets` | Bulk update asset attributes at group scope. **[EA]** |
| `GET` | `/groups/{group_id}/inventory/assets/filters` | Get available filter fields at group scope. **[EA]** |
| `GET` | `/groups/{group_id}/inventory/assets/filters/{filter_id}/values` | Get filter value autocomplete suggestions at group scope. **[EA]** |
| `GET` | `/groups/{group_id}/inventory/assets/groups` | Get available grouping fields at group scope. **[EA]** |
| `GET` | `/groups/{group_id}/inventory/assets/groups/{group_field_id}/values` | Get group value aggregation at group scope. **[EA]** |
| `POST` | `/groups/{group_id}/inventory/assets/searches` | Create an asynchronous asset search at group scope. **[EA]** |
| `GET` | `/groups/{group_id}/inventory/assets/searches/{search_id}/results` | Retrieve results of an asynchronous asset search at group scope. **[EA]** |
| `GET` | `/groups/{group_id}/inventory/assets/{asset_id}` | Get a single asset by ID at group scope. **[EA]** |
| `PATCH` | `/groups/{group_id}/inventory/assets/{asset_id}` | Update attributes of a specific asset at group scope. **[EA]** |
| `GET` | `/groups/{group_id}/inventory/assets/{asset_id}/relationships/projects` | List projects for an asset at group scope. **[EA]** |
| `GET` | `/groups/{group_id}/inventory/assets/{asset_id}/relationships/targets` | List targets for an asset at group scope. **[EA]** |

### Inventory Assets — Tenant Scope

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tenants/{tenant_id}/inventory/assets` | List or search all assets synchronously at tenant scope. **[EA]** |
| `PATCH` | `/tenants/{tenant_id}/inventory/assets` | Bulk update asset attributes at tenant scope. **[EA]** |
| `GET` | `/tenants/{tenant_id}/inventory/assets/filters` | Get available filter fields at tenant scope. **[EA]** |
| `GET` | `/tenants/{tenant_id}/inventory/assets/filters/{filter_id}/values` | Get filter value autocomplete suggestions at tenant scope. **[EA]** |
| `GET` | `/tenants/{tenant_id}/inventory/assets/groups` | Get available grouping fields at tenant scope. **[EA]** |
| `GET` | `/tenants/{tenant_id}/inventory/assets/groups/{group_field_id}/values` | Get group value aggregation at tenant scope. **[EA]** |
| `POST` | `/tenants/{tenant_id}/inventory/assets/searches` | Create an asynchronous asset search at tenant scope. **[EA]** |
| `GET` | `/tenants/{tenant_id}/inventory/assets/searches/{search_id}/results` | Retrieve results of an asynchronous asset search at tenant scope. **[EA]** |
| `GET` | `/tenants/{tenant_id}/inventory/assets/{asset_id}` | Get a single asset by ID at tenant scope. **[EA]** |
| `PATCH` | `/tenants/{tenant_id}/inventory/assets/{asset_id}` | Update attributes of a specific asset at tenant scope. **[EA]** |
| `GET` | `/tenants/{tenant_id}/inventory/assets/{asset_id}/relationships/projects` | List projects for an asset at tenant scope. **[EA]** |
| `GET` | `/tenants/{tenant_id}/inventory/assets/{asset_id}/relationships/targets` | List targets for an asset at tenant scope. **[EA]** |

## 17. Collections

Endpoints for organizing projects into named collections for easier management, filtering, and reporting.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/collections` | List all collections in the organization. |
| `POST` | `/orgs/{org_id}/collections` | Create a new collection. |
| `GET` | `/orgs/{org_id}/collections/{collection_id}` | Retrieve a specific collection. |
| `PATCH` | `/orgs/{org_id}/collections/{collection_id}` | Update a collection's name or description. |
| `DELETE` | `/orgs/{org_id}/collections/{collection_id}` | Delete a collection. |
| `GET` | `/orgs/{org_id}/collections/{collection_id}/relationships/projects` | List all projects in a collection. |
| `POST` | `/orgs/{org_id}/collections/{collection_id}/relationships/projects` | Add projects to a collection. |
| `DELETE` | `/orgs/{org_id}/collections/{collection_id}/relationships/projects` | Remove projects from a collection. |

## 18. SBOM & AI BOM

Endpoints for generating, uploading, and testing Software Bills of Materials (SBOM) and AI Bills of Materials (AI-BOM) for compliance, dependency tracking, and AI model inventories.

### SBOM

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/projects/{project_id}/sbom` | Download the SBOM document for a specific project (CycloneDX or SPDX formats). |
| `POST` | `/orgs/{org_id}/sbom_tests` | Submit an SBOM document for vulnerability testing. **[EA]** |
| `GET` | `/orgs/{org_id}/sbom_tests/{job_id}` | Check the status of an SBOM test run. **[EA]** |
| `GET` | `/orgs/{org_id}/sbom_tests/{job_id}/results` | Retrieve the results of a completed SBOM test run. **[EA]** |

### AI BOM

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/orgs/{org_id}/ai_boms` | Create a new AI Bill of Materials entry. **[EA]** |
| `POST` | `/orgs/{org_id}/ai_boms/upload` | Create and upload an AI-BOM document. **[EA]** |
| `GET` | `/orgs/{org_id}/ai_boms/{ai_bom_id}` | Retrieve a specific AI-BOM record. **[EA]** |
| `GET` | `/orgs/{org_id}/ai_bom_jobs/{job_id}` | Get the status of an AI-BOM processing job. **[EA]** |

## 19. Tests & Findings

Endpoints for running on-demand security tests and retrieving granular findings. This is distinct from project monitoring — tests are point-in-time scans.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/orgs/{org_id}/tests` | Create a new on-demand test. **[EA]** |
| `GET` | `/orgs/{org_id}/tests/{test_id}` | Retrieve the status and summary of a test. **[EA]** |
| `GET` | `/orgs/{org_id}/test_jobs/{job_id}` | Get status of a test job. **[EA]** |
| `GET` | `/orgs/{org_id}/tests/{test_id}/findings` | List all findings produced by a test (detailed vulnerability results). **[EA]** |

## 20. Policies

Endpoints for creating and managing security policies that define automated actions or rules for Snyk projects and issues, at both org and group levels.

### Organization Policies

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/policies` | List all policies configured for the organization. |
| `POST` | `/orgs/{org_id}/policies` | Create a new policy for the organization. |
| `GET` | `/orgs/{org_id}/policies/{policy_id}` | Retrieve a specific policy. |
| `PATCH` | `/orgs/{org_id}/policies/{policy_id}` | Update an existing policy. |
| `DELETE` | `/orgs/{org_id}/policies/{policy_id}` | Delete a policy. |
| `GET` | `/orgs/{org_id}/policies/{policy_id}/events` | List events triggered by a policy (audit trail). **[EA]** |

### Group Policies

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/groups/{group_id}/policies` | List all policies configured for a group. **[EA]** |
| `POST` | `/groups/{group_id}/policies` | Create a new group-level policy. **[EA]** |
| `PATCH` | `/groups/{group_id}/policies/{policy_id}` | Update a group-level policy. **[EA]** |
| `DELETE` | `/groups/{group_id}/policies/{policy_id}` | Delete a group-level policy. **[EA]** |

## 21. Settings

Endpoints for configuring feature-specific settings at organization and group scopes. Covers Infrastructure as Code (IaC), Open Source, SAST (Snyk Code), language-specific settings, pull request templates, and Broker settings.

### Infrastructure as Code (IaC) Settings

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/settings/iac` | Retrieve IaC settings for an organization. |
| `PATCH` | `/orgs/{org_id}/settings/iac` | Update IaC settings for an organization. |
| `GET` | `/groups/{group_id}/settings/iac` | Retrieve IaC settings for a group. |
| `PATCH` | `/groups/{group_id}/settings/iac` | Update IaC settings for a group. |

### Open Source Settings

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/settings/opensource` | Get open source settings for an organization. **[EA]** |
| `GET` | `/orgs/{org_id}/settings/opensource/broker` | Get the Broker configuration for open source in an organization. |
| `POST` | `/orgs/{org_id}/settings/opensource/broker` | Enable Broker for open source in an organization. |
| `DELETE` | `/orgs/{org_id}/settings/opensource/broker` | Delete the Broker configuration for open source in an organization. |
| `GET` | `/orgs/{org_id}/settings/opensource/{ecosystem}/broker` | Get Broker settings for a specific ecosystem in an organization. |
| `PATCH` | `/orgs/{org_id}/settings/opensource/{ecosystem}/broker` | Update Broker settings for a specific ecosystem. |
| `GET` | `/groups/{group_id}/settings/opensource/broker` | Get the open source Broker setting for a group. |
| `POST` | `/groups/{group_id}/settings/opensource/broker` | Enable open source Broker for a group. |
| `DELETE` | `/groups/{group_id}/settings/opensource/broker` | Delete the open source Broker setting for a group. |

### Language Settings

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/settings/open_source/languages` | List language-specific open source settings for an organization. **[EA]** |
| `PATCH` | `/orgs/{org_id}/settings/open_source/languages/{language}` | Update settings for a specific language in the organization. **[EA]** |

### SAST (Snyk Code) Settings

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/settings/sast` | Retrieve Snyk Code (SAST) settings for an organization. |
| `PATCH` | `/orgs/{org_id}/settings/sast` | Enable or disable Snyk Code for an organization. |

### Pull Request Templates

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/groups/{group_id}/settings/pull_request_template` | Retrieve the pull request fix template for a group. |
| `POST` | `/groups/{group_id}/settings/pull_request_template` | Create or replace the pull request template for a group. |
| `DELETE` | `/groups/{group_id}/settings/pull_request_template` | Delete the pull request template for a group. |

## 22. Audit Logs

Endpoints for searching and retrieving audit log events at organization and group levels. Useful for compliance monitoring and security investigations.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/audit_logs/search` | Search audit log events for an organization, filterable by user, event type, and date range. |
| `GET` | `/groups/{group_id}/audit_logs/search` | Search audit log events across all organizations in a group. |

## 23. Export

Endpoints for generating large data exports asynchronously. Supports exporting issues, projects, and other data at both org and group scopes.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/orgs/{org_id}/export` | Start an asynchronous data export job for an organization. |
| `GET` | `/orgs/{org_id}/export/{export_id}` | Check the status and retrieve results of an org-level export. |
| `GET` | `/orgs/{org_id}/jobs/export/{export_id}` | Get the status of an export job at org scope. |
| `POST` | `/groups/{group_id}/export` | Start an asynchronous data export job for a group. |
| `GET` | `/groups/{group_id}/export/{export_id}` | Check the status and retrieve results of a group-level export. |
| `GET` | `/groups/{group_id}/jobs/export/{export_id}` | Get the status of an export job at group scope. |

## 24. Slack Integration

Endpoints for configuring Snyk's Slack App integration — setting up notification defaults and per-project overrides, and querying available Slack channels.

### Slack Notification Settings

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/slack_app/{bot_id}` | Retrieve the default Slack notification settings for the integration. |
| `POST` | `/orgs/{org_id}/slack_app/{bot_id}` | Create default Slack notification settings for a bot integration. |
| `DELETE` | `/orgs/{org_id}/slack_app/{bot_id}` | Remove the Slack App integration for the organization. |
| `GET` | `/orgs/{org_id}/slack_app/{bot_id}/projects` | List Slack notification override settings for specific projects. |
| `POST` | `/orgs/{org_id}/slack_app/{bot_id}/projects/{project_id}` | Create a Slack notification override for a project. |
| `PATCH` | `/orgs/{org_id}/slack_app/{bot_id}/projects/{project_id}` | Update the Slack notification override for a project. |
| `DELETE` | `/orgs/{org_id}/slack_app/{bot_id}/projects/{project_id}` | Remove the Slack notification override for a project. |

### Slack Channel Lookup

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/slack_app/{tenant_id}/channels` | List all available Slack channels for a given Slack tenant. |
| `GET` | `/orgs/{org_id}/slack_app/{tenant_id}/channels/{channel_id}` | Get the name of a specific Slack channel by ID. |

## 25. Snyk Learn

Endpoints for Snyk Learn — the developer security education platform. Covers the content catalog, learning assignments, and progress tracking.

### Catalog

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/learn/catalog` | List all available learning resources (lessons, courses) in Snyk Learn. **[EA]** |

### Learning Assignments

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/learn/assignments` | List all learning assignments for the organization. **[EA]** |
| `POST` | `/orgs/{org_id}/learn/assignments` | Bulk-create learning assignments for users in the organization. **[EA]** |
| `PATCH` | `/orgs/{org_id}/learn/assignments` | Update the due dates for existing assignments. **[EA]** |
| `DELETE` | `/orgs/{org_id}/learn/assignments` | Bulk-delete learning assignments for the organization. **[EA]** |
| `POST` | `/orgs/{org_id}/learn/assignments/bulk_delete` | Alternative endpoint for bulk-deleting assignments. **[EA]** |

### Learning Progress

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orgs/{org_id}/learn/progress/catalog` | Get aggregated learning progress across the catalog for the whole organization. **[EA]** |
| `GET` | `/orgs/{org_id}/learn/progress/users` | Get individual learning progress broken down by user. **[EA]** |

## 26. OpenAPI

Endpoints exposing the Snyk REST API specification itself — useful for tooling, SDK generation, and discovering available API versions.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/openapi` | List all available API versions. |
| `GET` | `/openapi/{version}` | Retrieve the full OpenAPI specification for a specific API version. |

---

*Document generated from Snyk REST API specification. Endpoints marked **[EA]** are in Early Access and may change.*
