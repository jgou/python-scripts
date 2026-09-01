from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class NatGatewayScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.nat_gateways_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("ec2")

    def __list_nat_gateways(self, region: str) -> list[dict[str, Any]]:
        nat_gateways = []
        try:
            ec2 = self.session.client("ec2", region_name=region)
            paginator = ec2.get_paginator("describe_nat_gateways")
            for page in paginator.paginate():
                for nat_gateway in page.get("NatGateways", []):
                    if nat_gateway.get("State") in ("deleted", "deleting"):
                        continue
                    nat_gateways.append({
                        "NatGatewayId": nat_gateway["NatGatewayId"],
                        "Region": region,
                        "VpcId": nat_gateway.get("VpcId"),
                        "State": nat_gateway.get("State")
                    })
        except ClientError as e:
            print(f"Could not list NAT gateways in {region}: {e}")
            nat_gateways = []
        return nat_gateways

    def scan(self) -> None:
        self.nat_gateways_info = []
        for region in self.__get_regions():
            self.nat_gateways_info.extend(self.__list_nat_gateways(region))

    def verbose_scan(self) -> None:
        for nat_gateway_info in self.nat_gateways_info:
            print(f"NAT Gateway: {nat_gateway_info['NatGatewayId']}, Region: {nat_gateway_info['Region']}, VPC: {nat_gateway_info['VpcId']}, State: {nat_gateway_info['State']}")

    def __delete_nat_gateway(self, region: str, nat_gateway_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete NAT gateway {nat_gateway_id}")
                return
            ec2.delete_nat_gateway(NatGatewayId=nat_gateway_id)
        except ClientError as e:
            print(f"Could not delete NAT gateway {nat_gateway_id}: {e}")

    def delete(self) -> None:
        for nat_gateway_info in self.nat_gateways_info:
            self.__delete_nat_gateway(nat_gateway_info["Region"], nat_gateway_info["NatGatewayId"])
