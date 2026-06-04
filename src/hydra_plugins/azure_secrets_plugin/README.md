# Azure Key Vault Plugin

This plugin registers an OmegaConf custom resolver for Azure Key Vault, enabling secure lazy-loaded secret injection into Hydra configurations.

## Installation

### Option 1: Install with optional dependency (recommended)

```bash
pip install mxm-scaffold[azure_secrets]
```

### Option 2: Install SDKs directly

```bash
pip install azure-identity azure-keyvault-secrets
```

## Usage in YAML Configs

```yaml
auth:
  token: "${azure_secret:my-vault, my-secret}"
```

### Arguments

- `vault_name`: The name of the Key Vault (just the vault name, not the full URL)
- `secret_name`: The name of the secret to retrieve

## Examples

### Simple Secret

```yaml
api:
  key: "${azure_secret:my-vault, api-key}"
```

### Multiple Secrets

```yaml
database:
  host: "prod-db.example.com"
  username: "${azure_secret:my-vault, db-username}"
  password: "${azure_secret:my-vault, db-password}"
```

## Features

- **Lazy Evaluation**: Secrets are fetched only when accessed, not at config load time
- **No Hardcoded Values**: Config files show only the resolver string, never the actual secret
- **Automatic Registration**: The plugin auto-registers on Hydra initialization
- **Type Safe**: Proper error messages for misconfiguration

## Authentication

Azure Key Vault uses `DefaultAzureCredential` for authentication, which checks credentials in the following order:

1. Environment variables (`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`)
2. Managed Identity (if running on Azure services)
3. Azure CLI credentials
4. Interactive browser login

Example with service principal:

```bash
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
```

## Vault Access Requirements

Ensure the authenticated principal has the following Key Vault permissions:
- `secrets/get` - Read secrets from the vault
- `secrets/list` - List secrets in the vault
