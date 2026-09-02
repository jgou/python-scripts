from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class InternetGatewayScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.internet_gateways_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("ec2")

    def __list_internet_gateways(self, region: str) -> list[dict[str, Any]]:
        internet_gateways = []
        try:
            ec2 = self.session.client("ec2", region_name=region)
            paginator = ec2.get_paginator("describe_internet_gateways")
            for page in paginator.paginate():
                for internet_gateway in page.get("InternetGateways", []):
                    attached_vpc_ids = [
                        attachment["VpcId"] for attachment in internet_gateway.get("Attachments", [])
                        if attachment.get("State") == "available"
                    ]
                    internet_gateways.append({
                        "InternetGatewayId": internet_gateway["InternetGatewayId"],
                        "Region": region,
                        "AttachedVpcIds": attached_vpc_ids
                    })
        except ClientError as e:
            print(f"Could not list Internet Gateways in {region}: {e}")
            internet_gateways = []
        return internet_gateways

    def scan(self) -> None:
        self.internet_gateways_info = []
        for region in self.__get_regions():
            self.internet_gateways_info.extend(self.__list_internet_gateways(region))

    def verbose_scan(self) -> None:
        for internet_gateway_info in self.internet_gateways_info:
            print(f"Internet Gateway: {internet_gateway_info['InternetGatewayId']}, Region: {internet_gateway_info['Region']}, Attached VPCs: {internet_gateway_info['AttachedVpcIds'] or 'None'}")

    def __detach_internet_gateway(self, region: str, internet_gateway_id: str, vpc_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would detach Internet Gateway {internet_gateway_id} from VPC {vpc_id}")
                return
            ec2.detach_internet_gateway(InternetGatewayId=internet_gateway_id, VpcId=vpc_id)
        except ClientError as e:
            print(f"Could not detach Internet Gateway {internet_gateway_id} from VPC {vpc_id}: {e}")

    def __delete_internet_gateway(self, region: str, internet_gateway_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete Internet Gateway {internet_gateway_id}")
                return
            ec2.delete_internet_gateway(InternetGatewayId=internet_gateway_id)
        except ClientError as e:
            print(f"Could not delete Internet Gateway {internet_gateway_id}: {e}")

    def delete(self) -> None:
        for internet_gateway_info in self.internet_gateways_info:
            region = internet_gateway_info["Region"]
            internet_gateway_id = internet_gateway_info["InternetGatewayId"]
            # An Internet Gateway must be detached from every VPC before it can be deleted.
            for vpc_id in internet_gateway_info["AttachedVpcIds"]:
                self.__detach_internet_gateway(region, internet_gateway_id, vpc_id)
            self.__delete_internet_gateway(region, internet_gateway_id)
