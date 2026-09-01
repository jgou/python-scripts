from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class ElasticIPScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.addresses_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("ec2")

    def __list_addresses(self, region: str) -> list[dict[str, Any]]:
        addresses = []
        try:
            ec2 = self.session.client("ec2", region_name=region)
            response = ec2.describe_addresses()
            for address in response.get("Addresses", []):
                addresses.append({
                    "AllocationId": address.get("AllocationId"),
                    "PublicIp": address.get("PublicIp"),
                    "AssociationId": address.get("AssociationId"),
                    "Region": region
                })
        except ClientError as e:
            print(f"Could not list Elastic IPs in {region}: {e}")
            addresses = []
        return addresses

    def scan(self) -> None:
        self.addresses_info = []
        for region in self.__get_regions():
            self.addresses_info.extend(self.__list_addresses(region))

    def verbose_scan(self) -> None:
        for address_info in self.addresses_info:
            status = "associated" if address_info["AssociationId"] else "unassociated"
            print(f"Elastic IP: {address_info['PublicIp']} ({address_info['AllocationId']}), Region: {address_info['Region']}, Status: {status}")

    def __disassociate_address(self, region: str, association_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would disassociate Elastic IP association {association_id}")
                return
            ec2.disassociate_address(AssociationId=association_id)
        except ClientError as e:
            print(f"Could not disassociate Elastic IP association {association_id}: {e}")

    def __release_address(self, region: str, allocation_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would release Elastic IP {allocation_id}")
                return
            ec2.release_address(AllocationId=allocation_id)
        except ClientError as e:
            print(f"Could not release Elastic IP {allocation_id}: {e}")

    def delete(self) -> None:
        for address_info in self.addresses_info:
            region = address_info["Region"]
            # An associated Elastic IP must be disassociated before it can be released.
            if address_info["AssociationId"]:
                self.__disassociate_address(region, address_info["AssociationId"])
            self.__release_address(region, address_info["AllocationId"])
