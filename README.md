# python-scripts

## k8s-deployment-validator

A Python utility for validating Kubernetes deployment YAML configuration files. This tool helps ensure that your Kubernetes manifests are correctly formatted and meet validation requirements before deployment.

### Features

- Validates Kubernetes deployment YAML files for syntax and structure
- Supports batch processing of multiple YAML files in a directory
- Fully configurable validation fields via `validation_fields.yaml` (no hardcoded checks)
- Supports nested field validation using dot notation
- Clear error reporting for invalid configurations

### Configuration

The tool reads validation requirements from `config/validation_fields.yaml`. You can customize which fields are required for validation by editing this file. Fields use dot notation for nested attributes.

Default validation checks:
- `readinessProbe` (top-level container field)
- `livenessProbe` (top-level container field)
- `resources.limits` (nested under resources)
- `resources.requests` (nested under resources)

To customize validation rules, modify the `config/validation_fields.yaml` file:

```yaml
required_fields:
  - readinessProbe
  - livenessProbe
  - resources.limits
  - resources.requests
```

You can add or remove any container fields. Use dot notation for nested fields (e.g., `securityContext.runAsNonRoot`).

### Usage

Run the validator by providing a path to your Kubernetes deployment YAML files:

```bash
python3 k8s-deployment-validator --path /path/to/yaml/files
```

### Requirements

- PyYAML 6.0.2

## env-files-compare

A Python utility for comparing two or more `.env` files and reporting differences in their key-value pairs.

### Features

- Compares any number of environment files and identifies keys with differing values
- Detects keys present in some files but missing from others
- Ignores blank lines and comments (lines starting with `#`)
- Clear, human-readable difference report

### Usage

Run the comparer by providing paths to two or more environment files:

```bash
python3 env-files-compare --paths /path/to/.env.1 /path/to/.env.2 /path/to/.env.3
```

### Requirements

- Python 3 standard library only (no external dependencies)

## aws-disable-lb-protection

A Python utility for bulk-disabling deletion protection on AWS Elastic Load Balancers (ELBv2) whose name matches a search string.

### Features

- Lists load balancers in a given AWS region using a specified AWS profile
- Filters load balancers by a substring match on their name
- Disables the `deletion_protection.enabled` attribute on each matching load balancer
- Supports a `--dry-run` mode to preview matches without making any changes

### Usage

```bash
python3 aws-disable-lb-protection --profile my-aws-profile --region us-east-1 --search-name-criteria my-lb-name --dry-run
```

Remove `--dry-run` to actually disable deletion protection on the matched load balancers.

### Requirements

- boto3>=1.26.0 (see `requirements.txt`)
- AWS credentials configured for the given `--profile` with permissions for `elasticloadbalancing:DescribeLoadBalancers` and `elasticloadbalancing:ModifyLoadBalancerAttributes`
