import argparse

from config import ConfigTool
from az_user_manager import AzureUserManager


def main():
    parser = argparse.ArgumentParser(description="Offboarding users in Entra ID + Azure RBAC.")
    parser.add_argument("--tenant-id", required=True, help="Tenant ID in Entra ID.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--upns", nargs="+", help="UPN list to process.")
    group.add_argument("--upns-file", help="Text file with one UPN per line.")
    parser.add_argument("--dry-run", action="store_true", help="Enable dry-run mode; no changes will be made.")
    args = parser.parse_args()

    config = ConfigTool(upns=args.upns, upns_file=args.upns_file, dry_run=args.dry_run)
    upns = config.load_upns()

    azure_user_manager = AzureUserManager(tenant_id=args.tenant_id, dry_run=args.dry_run)
    azure_user_manager.authenticate()

    for upn in upns:
        print(f"\n=== Processing: {upn} ===")
        azure_user_manager.set_user(upn)
        if not azure_user_manager.user_id:
            print("  User not found, skipping.")
            continue

        print(f"  Found: {azure_user_manager.display_name} ({azure_user_manager.user_id})")
        azure_user_manager.block_signin()
        azure_user_manager.revoke_sessions()
        azure_user_manager.remove_from_all_groups()
        azure_user_manager.remove_directory_roles()
        azure_user_manager.remove_azure_rbac_roles()

    print("\nReady.")
