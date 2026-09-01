from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class ELBScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.load_balancers_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("elbv2")

    def __list_load_balancers(self, region: str) -> list[dict[str, Any]]:
        load_balancers = []
        try:
            elbv2 = self.session.client("elbv2", region_name=region)
            paginator = elbv2.get_paginator("describe_load_balancers")
            for page in paginator.paginate():
                for lb in page.get("LoadBalancers", []):
                    load_balancers.append({
                        "LoadBalancerArn": lb["LoadBalancerArn"],
                        "Name": lb["LoadBalancerName"],
                        "Type": lb["Type"],
                        "Region": region,
                        "State": lb.get("State", {}).get("Code")
                    })
        except ClientError as e:
            load_balancers = []
        return load_balancers

    def scan(self) -> None:
        self.load_balancers_info = []
        for region in self.__get_regions():
            self.load_balancers_info.extend(self.__list_load_balancers(region))

    def verbose_scan(self) -> None:
        for lb_info in self.load_balancers_info:
            print(f"Load Balancer: {lb_info['Name']} ({lb_info['Type']}), Region: {lb_info['Region']}, State: {lb_info['State']}")

    def __disable_deletion_protection(self, region: str, arn: str) -> None:
        try:
            elbv2 = self.session.client("elbv2", region_name=region)
            elbv2.modify_load_balancer_attributes(
                LoadBalancerArn=arn,
                Attributes=[{"Key": "deletion_protection.enabled", "Value": "false"}]
            ) if not self.config.dry_run else print(f"Dry run: would disable deletion protection for load balancer {arn}")
        except ClientError as e:
            pass

    def __delete_load_balancer(self, region: str, arn: str) -> None:
        try:
            elbv2 = self.session.client("elbv2", region_name=region)
            elbv2.delete_load_balancer(LoadBalancerArn=arn) if not self.config.dry_run else print(f"Dry run: would delete load balancer {arn}")
        except ClientError as e:
            pass

    def delete(self) -> None:
        for lb_info in self.load_balancers_info:
            region = lb_info["Region"]
            arn = lb_info["LoadBalancerArn"]
            # Deletion protection blocks delete_load_balancer, so it must be turned off first.
            self.__disable_deletion_protection(region, arn)
            self.__delete_load_balancer(region, arn)
