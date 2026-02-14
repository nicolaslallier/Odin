# Azure Infrastructure (Bicep)

Baseline Azure infrastructure for the Odin project, deployed to resource group **Valhalla** in **canadaeast**.

## Prerequisites

- **Azure CLI** (`az`) installed and logged in: `az login`
- **Active subscription** selected: `az account set --subscription "<name-or-id>"`
- Permissions to create resource groups and deploy resources (Contributor or Owner)

## Quick Start

```bash
make check              # Verify az CLI and active account
make providers          # Register required resource providers (first-time)
make rg                 # Ensure resource group Valhalla exists
make validate ENV=dev   # Validate Bicep template
make whatif ENV=dev     # Preview changes (recommended before deploy)
make deploy ENV=dev     # Deploy infrastructure
make outputs ENV=dev    # Print deployment outputs
```

## Resources Deployed

| Resource | Purpose |
|----------|---------|
| Log Analytics Workspace | Centralized logs |
| Application Insights | APM and telemetry |
| Key Vault | Secrets (RBAC-based) |
| Storage Account | General-purpose storage |
| Container Apps Environment | Managed environment for container workloads |

## Environments

- `dev` – `infra/params/dev.json` (prefix: odin-dev)
- `prod` – `infra/params/prod.json` (prefix: odin-prod)

Use a different subscription: `AZ_SUBSCRIPTION=my-sub make deploy ENV=dev`
