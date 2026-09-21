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

## Authentication

The aws secrets plugin uses `boto3`, which resolves credentials using the Standard AWS Credential Provider Chain in the following order:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`)
2. Managed Identity / IRSA (IAM roles for EKS service accounts or ECS tasks)
3. AWS CLI credentials (`~/.aws/credentials` or IAM Identity Center / SSO)
4. EC2 Instance Metadata Service (IAM roles attached to EC2 instances)

You may create AWS credentials using ``aws configure``.