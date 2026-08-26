import argparse

from config import ToolConfig
from updater import LoadBalancerUpdater


def main():
  parser = argparse.ArgumentParser(description="Disable Load Balancer Protection")
  parser.add_argument("--profile", type=str, required=True, help="AWS profile to use.")
  parser.add_argument("--region", type=str, required=True, help="AWS region where the load balancer is located.")
  parser.add_argument("--search-name-criteria", type=str, required=True, help="Search criteria to identify the load balancer from its name.")
  parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without making any changes.")

  args = parser.parse_args()
  config = ToolConfig(
    profile=args.profile,
    region=args.region,
    search_criteria=args.search_name_criteria,
    dry_run=args.dry_run
  )
  print(vars(config))

  updater = LoadBalancerUpdater(config)
  updater.update_load_balancer()



