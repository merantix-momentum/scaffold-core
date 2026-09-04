# GCP Secret Manager Plugin

This plugin registers an OmegaConf custom resolver for GCP Secret Manager, enabling secure lazy-loaded secret injection into Hydra configurations.

## Installation

### Option 1: Install with optional dependency (recommended)

```bash
pip install mxm-scaffold[gcp_secrets]
```

### Option 2: Install SDK directly

```bash
pip install google-cloud-secret-manager
```

## Usage in YAML Configs

```yaml
database:
  api_key: "${gcp_secret:my-project/secret-name, api_key}"
```

### Arguments

- `secret_name`: The GCP secret (format: `project_id/secret_name` or full resource name `projects/project_id/secrets/secret_name/versions/latest`)
- `key` (optional): If the secret is JSON-formatted, extract this specific key from it

## Examples

### Simple String Secret

```yaml
auth:
  token: "${gcp_secret:my-project/auth-token}"
```

### JSON Secret with Key Extraction

```yaml
database:
  password: "${gcp_secret:my-project/db-credentials, password}"
  username: "${gcp_secret:my-project/db-credentials, username}"
```

### Full Resource Name

```yaml
api:
  key: "${gcp_secret:projects/my-project-123/secrets/api-key/versions/latest}"
```

## Features

- **Lazy Evaluation**: Secrets are fetched only when accessed, not at config load time
- **No Hardcoded Values**: Config files show only the resolver string, never the actual secret
- **Automatic Registration**: The plugin auto-registers on Hydra initialization
- **JSON Support**: Extract specific keys from JSON-formatted secrets
- **Type Safe**: Proper error messages for misconfiguration

## Authentication

GCP Secret Manager uses Application Default Credentials. Ensure your environment has proper credentials configured:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```
