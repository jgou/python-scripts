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


