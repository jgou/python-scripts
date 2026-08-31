import argparse
from azure_users import AzureUsers

def main():
  parser = argparse.ArgumentParser(description="List Entra ID users via Microsoft Graph.")
  parser.add_argument("--tenant-id", help="The Tenant ID of your Entra ID.", required=True)
  parser.add_argument("--export", help="CSV file path to export the results to.")
  parser.add_argument("--upn-contains", help="Filter users whose UserPrincipalName contains this substring.")
  parser.add_argument("--only-enabled", action="store_true", help="Only include enabled accounts.")
  args = parser.parse_args()

  azure_users = AzureUsers(tenant_id=args.tenant_id)
  print("Authenticating with Microsoft Graph...")
  azure_users.authenticate()
  print("Fetching users...")
  users = azure_users.get_all_users()
  print(f"Total users found: {len(users)}")

  if args.only_enabled:
      users = AzureUsers.get_enabled_users(users)
      print(f"After filtering to enabled only: {len(users)}")

  if args.upn_contains:
      substr = args.upn_contains
      users = AzureUsers.filter_users(users, substr)
      print(f"After filtering by UPN containing '{args.upn_contains}': {len(users)}")

  AzureUsers.pretty_print(users)

  if args.export:
     AzureUsers.export(args.export, users)