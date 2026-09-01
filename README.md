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

## aws-copy-and-verify-s3-bucket

A Python utility for copying the contents of one S3 bucket to another, then verifying that the copy completed correctly.

### Prerequisites

- The destination bucket must already exist; the tool does not create it
- For a verification of 0 differences, the destination bucket must be empty before running the tool — any pre-existing objects will show up as "extra in destination"
- When `--source-profile` and `--destination-profile` belong to different AWS accounts, the copy is performed server-side (`CopyObject`) using the destination account's credentials reading from the source bucket. The source bucket must have a bucket policy granting the destination account read access, e.g.:

  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AllowDestinationAccountReadForMigration",
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::<DESTINATION_ACCOUNT_ID>:root"
        },
        "Action": ["s3:GetObject", "s3:GetObjectAcl"],
        "Resource": "arn:aws:s3:::<SOURCE_BUCKET>/<PREFIX>*"
      },
      {
        "Sid": "AllowDestinationAccountListForMigration",
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::<DESTINATION_ACCOUNT_ID>:root"
        },
        "Action": "s3:ListBucket",
        "Resource": "arn:aws:s3:::<SOURCE_BUCKET>",
        "Condition": {
          "StringLike": {
            "s3:prefix": "<PREFIX>*"
          }
        }
      }
    ]
  }
  ```

  Omit the `Condition` block (and use `Resource: "arn:aws:s3:::<SOURCE_BUCKET>/*"` / `"arn:aws:s3:::<SOURCE_BUCKET>"`) to grant access to the whole bucket instead of a single prefix. If the source bucket already has a policy, merge this statement into it rather than overwriting it.

### Features

- Copies all objects from a source bucket to a destination bucket, each accessed via its own AWS profile and region
- Verifies the copy by comparing object keys, sizes, and ETags between source and destination
- Reports objects missing from the destination, extra objects in the destination, and size/ETag mismatches
- Supports an optional `--prefix` to scope the copy and verification to a single folder path, applied to both buckets
- Supports a `--dry-run` mode to preview the copy without making any changes
- Supports a `--verify-only` mode to skip copying and only verify existing bucket contents

### Usage

```bash
python3 aws-copy-and-verify-s3-bucket --source-bucket my-source-bucket --destination-bucket my-destination-bucket --source-profile source-profile --destination-profile destination-profile --source-region us-east-1 --destination-region us-east-1 --prefix my-folder/ --dry-run
```

Remove `--dry-run` to actually copy the objects, or pass `--verify-only` to skip copying and only verify the destination bucket against the source.

### Requirements

- boto3>=1.26.0 (see `requirements.txt`)
- AWS credentials configured for the given `--source-profile` and `--destination-profile` with permissions for `s3:ListBucket` and `s3:GetObject` on the source bucket, and `s3:ListBucket` and `s3:PutObject` on the destination bucket

## aws-cleanup-helper

A Python utility that scans an AWS account and deletes resources, organized per AWS service. Currently supports S3 (every bucket in the account), EC2 (every instance in the account, plus its attached EBS volumes), Route 53 (every hosted zone in the account, plus its record sets), and ELB (every Application/Network Load Balancer in the account). Unless `--dry-run` is passed, everything scanned gets deleted.

> [!WARNING]
> Without `--dry-run`, this tool deletes every S3 bucket, terminates every EC2 instance, deletes every Route 53 hosted zone, and deletes every load balancer in the target account — it does not filter by name, age, tags, or state. Always run with `--dry-run` first and review the output before running for real.

### Features

- Scans and reports all S3 buckets in the account, their region, and whether they contain objects
- Deletes all objects in each bucket, then the bucket itself
- Scans and reports all EC2 instances across regions, their state, and their attached EBS volumes
- Terminates each EC2 instance; for volumes not set to delete on termination, waits for the instance to finish terminating and deletes them explicitly
- Scans and reports all Route 53 hosted zones, whether they're public or private, and their record count
- Deletes all non-default record sets in each hosted zone (the apex `NS`/`SOA` records are left alone, since they're removed automatically), then the hosted zone itself
- Scans and reports all Application/Network Load Balancers across regions, their type and state
- Disables deletion protection on each load balancer (required before it can be deleted), then deletes it
- Supports a `--regions` flag to limit which AWS regions are scanned (EC2 and ELB only; S3 buckets and Route 53 hosted zones are always listed account-wide), comma-separated. Default is all regions.
- Supports a `--services` flag to limit which AWS services are scanned/deleted, comma-separated (`ec2`, `elb`, `route53`, `s3`)
- Supports a `--dry-run` mode to preview what would be deleted without making any changes

### Usage

```bash
python3 aws-cleanup-helper --profile my-aws-profile --services ec2,elb,route53,s3 --dry-run
```

Remove `--dry-run` to actually delete the scanned resources.

### Requirements

- boto3>=1.26.0 (see `requirements.txt`)
- AWS credentials configured for the given `--profile` with permissions for `s3:ListAllMyBuckets`, `s3:GetBucketLocation`, `s3:ListBucket`, `s3:DeleteObject`, `s3:DeleteBucket`, `ec2:DescribeInstances`, `ec2:TerminateInstances`, `ec2:DeleteVolume`, `route53:ListHostedZones`, `route53:ListResourceRecordSets`, `route53:ChangeResourceRecordSets`, `route53:DeleteHostedZone`, `elasticloadbalancing:DescribeLoadBalancers`, `elasticloadbalancing:ModifyLoadBalancerAttributes`, and `elasticloadbalancing:DeleteLoadBalancer`

## az-offboard-users

A Python utility that offboards a list of users from Microsoft Entra ID and Azure RBAC. For each UPN, it:

1. Blocks sign-in (`accountEnabled = False`)
2. Revokes all active sessions / refresh tokens
3. Removes the user from every group they belong to
4. Removes every directory role assignment (Entra ID roles)
5. Removes every Azure RBAC role assignment at any scope (via Azure CLI, reusing your existing `az login` session)

### Features

- Accepts UPNs directly via `--upns` or from a file (one per line) via `--upns-file`
- Authenticates to Microsoft Graph interactively via device code flow (MSAL)
- Resolves each UPN to its object ID, including guest UPNs containing literal `#` characters (e.g. `...#EXT#@...`)
- Supports a `--dry-run` mode to preview what would be changed without making any changes

### Usage

```bash
python3 az-offboard-users --tenant-id <tenant-id> --upns user1_contoso.com#EXT#@tenant.onmicrosoft.com user2@tenant.onmicrosoft.com --dry-run
python3 az-offboard-users --tenant-id <tenant-id> --upns-file users_to_remove.txt --dry-run
```

Remove `--dry-run` to actually apply the offboarding changes.

### Requirements

- msal==1.38.0, requests==2.34.2 (see `requirements.txt`)
- Azure CLI installed and logged in (`az login`) with permissions to view/remove role assignments (User Access Administrator or Owner)
- Delegated Microsoft Graph permissions, consented by an admin: `User.ReadWrite.All`, `Group.ReadWrite.All`, `RoleManagement.ReadWrite.Directory`

## az-list-entraid-users

A Python utility that lists all Microsoft Entra ID (Azure AD) users via Microsoft Graph, with optional CSV export and UPN filtering.

### Features

- Authenticates to Microsoft Graph interactively via device code flow (MSAL)
- Walks Graph's pagination to retrieve every user in the tenant
- Supports `--upn-contains` to filter users by a substring of their UserPrincipalName
- Supports `--only-enabled` to include only enabled accounts
- Supports `--export` to write the results to a CSV file

### Usage

```bash
python3 az-list-entraid-users --tenant-id <tenant-id>
python3 az-list-entraid-users --tenant-id <tenant-id> --export users.csv
python3 az-list-entraid-users --tenant-id <tenant-id> --upn-contains hotaka
python3 az-list-entraid-users --tenant-id <tenant-id> --only-enabled
```

### Requirements

- msal==1.38.0, requests==2.34.2 (see `requirements.txt`)
- Delegated Microsoft Graph permission, consented by an admin or the user: `User.Read.All`
