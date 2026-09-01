import argparse
from config import ToolConfig
from scanner import Scanner

def main() -> None:
    parser = argparse.ArgumentParser(description="AWS Cleanup Helper")
    parser.add_argument("--profile", help="AWS profile to use")
    parser.add_argument("--regions", help="AWS regions to use, comma-separated. Default is all regions.")
    parser.add_argument("--services", type=ToolConfig.parse_services, help="AWS services to scan and delete, comma-separated (ec2, elasticache, elb, rds, route53, s3). Default is all services.")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without making any changes")
    parser.add_argument("--skip-final-snapshot", action="store_true", help="Skip final snapshot for RDS instances")
    args = parser.parse_args()

    config = ToolConfig(
        profile=args.profile,
        regions=args.regions.split(",") if args.regions else [],
        services=args.services,
        dry_run=args.dry_run,
        skip_final_snapshot=args.skip_final_snapshot
    )

    scanner = Scanner(config=config)
    scanner.init_session()
    scanner.scan()
    scanner.delete()
    