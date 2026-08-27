import argparse

from config import ToolConfig
from copier import S3BucketCopier
from verifier import S3BucketVerifier


def main():
    parser = argparse.ArgumentParser(description="Copy and verify S3 bucket contents.")
    parser.add_argument("--source-bucket", type=str, required=True, help="Source S3 bucket name.")
    parser.add_argument("--destination-bucket", type=str, required=True, help="Destination S3 bucket name.")
    parser.add_argument("--source-profile", type=str, required=True, help="AWS profile to use for the source bucket.")
    parser.add_argument("--destination-profile", type=str, required=True, help="AWS profile to use for the destination bucket.")
    parser.add_argument("--source-region", type=str, required=True, help="AWS region where the source bucket is located.")
    parser.add_argument("--destination-region", type=str, required=True, help="AWS region where the destination bucket is located.")
    parser.add_argument("--prefix", type=str, default="", help="Optional folder path (S3 key prefix) to scope the copy and verification to, in both source and destination buckets.")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without making any changes.")
    parser.add_argument("--verify-only", action="store_true", help="Only verify the contents of the destination bucket without copying.")
    args = parser.parse_args()

    config = ToolConfig(
        source_bucket=args.source_bucket,
        destination_bucket=args.destination_bucket,
        source_profile=args.source_profile,
        destination_profile=args.destination_profile,
        source_region=args.source_region,
        destination_region=args.destination_region,
        prefix=args.prefix,
        dry_run=args.dry_run,
        verify_only=args.verify_only
    )

    copier = S3BucketCopier(config)
    copier.copy()

    verifier = S3BucketVerifier(config)
    verifier.verify().report()
