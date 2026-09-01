from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class NetworkFirewallScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.firewalls_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("network-firewall")

    def __list_firewalls(self, region: str) -> list[dict[str, Any]]:
        firewalls = []
        try:
            network_firewall = self.session.client("network-firewall", region_name=region)
            paginator = network_firewall.get_paginator("list_firewalls")
            for page in paginator.paginate():
                for firewall in page.get("Firewalls", []):
                    details = network_firewall.describe_firewall(FirewallArn=firewall["FirewallArn"])
                    firewalls.append({
                        "FirewallArn": firewall["FirewallArn"],
                        "FirewallName": firewall.get("FirewallName"),
                        "Region": region,
                        "Status": details.get("FirewallStatus", {}).get("Status"),
                        "DeleteProtection": details.get("Firewall", {}).get("DeleteProtection", False)
                    })
        except ClientError as e:
            print(f"Could not list Network Firewalls in {region}: {e}")
            firewalls = []
        return firewalls

    def scan(self) -> None:
        self.firewalls_info = []
        for region in self.__get_regions():
            self.firewalls_info.extend(self.__list_firewalls(region))

    def verbose_scan(self) -> None:
        for firewall_info in self.firewalls_info:
            print(f"Network Firewall: {firewall_info['FirewallName']}, Region: {firewall_info['Region']}, Status: {firewall_info['Status']}")

    def __disable_delete_protection(self, region: str, arn: str) -> None:
        try:
            network_firewall = self.session.client("network-firewall", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would disable delete protection for Network Firewall {arn}")
                return
            network_firewall.update_firewall_delete_protection(FirewallArn=arn, DeleteProtection=False)
        except ClientError as e:
            print(f"Could not disable delete protection for Network Firewall {arn}: {e}")

    def __delete_firewall(self, region: str, arn: str) -> None:
        try:
            network_firewall = self.session.client("network-firewall", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete Network Firewall {arn}")
                return
            network_firewall.delete_firewall(FirewallArn=arn)
        except ClientError as e:
            print(f"Could not delete Network Firewall {arn}: {e}")

    def delete(self) -> None:
        for firewall_info in self.firewalls_info:
            region = firewall_info["Region"]
            arn = firewall_info["FirewallArn"]
            # Delete protection blocks delete_firewall, so it must be turned off first.
            if firewall_info["DeleteProtection"]:
                self.__disable_delete_protection(region, arn)
            self.__delete_firewall(region, arn)
