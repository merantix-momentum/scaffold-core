# AWS Secrets Manager Plugin

This plugin registers an OmegaConf custom resolver for AWS Secrets Manager, enabling secure lazy-loaded secret injection into Hydra configurations.

## Installation

### Option 1: Install with optional dependency (recommended)

```bash
pip install mxm-scaffold[aws_secrets]
```

### Option 2: Install SDK directly

```bash
pip install boto3
```

## Usage in YAML Configs

```yaml
database:
  password: "${aws_secret:secret_name, key_name}"
  host: "prod-db.example.com"
```

### Arguments

- `secret_id`: The name or ARN of the secret in AWS Secrets Manager
- `key` (optional): If the secret is JSON-formatted, extract this specific key from it

## Examples

### Simple String Secret

```yaml
api:
  token: "${aws_secret:prod/api/token}"
```

### JSON Secret with Key Extraction

```yaml
database:
  password: "${aws_secret:prod/db/credentials, password}"
  username: "${aws_secret:prod/db/credentials, username}"
```

## Features

- **Lazy Evaluation**: Secrets are fetched only when accessed, not at config load time
- **No Hardcoded Values**: Config files show only the resolver string, never the actual secret
- **Automatic Registration**: The plugin auto-registers on Hydra initialization
- **JSON Support**: Extract specific keys from JSON-formatted secrets
- **Type Safe**: Proper error messages for misconfiguration
