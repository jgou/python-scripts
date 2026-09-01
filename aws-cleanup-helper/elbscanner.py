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
            print(f"Could not disable deletion protection for load balancer {arn}: {e}")

    def __deregister_from_target_groups(self, region: str, arn: str) -> None:
        try:
            elbv2 = self.session.client("elbv2", region_name=region)
            paginator = elbv2.get_paginator("describe_target_groups")
            for page in paginator.paginate():
                for target_group in page.get("TargetGroups", []):
                    # A load balancer can itself be registered as a target (e.g. an ALB
                    # fronted by an NLB or Global Accelerator); it must be deregistered
                    # from any such target group before it can be deleted.
                    if target_group.get("TargetType") != "alb":
                        continue
                    target_group_arn = target_group["TargetGroupArn"]
                    health = elbv2.describe_target_health(TargetGroupArn=target_group_arn)
                    for target in health.get("TargetHealthDescriptions", []):
                        if target.get("Target", {}).get("Id") != arn:
                            continue
                        if self.config.dry_run:
                            print(f"Dry run: would deregister load balancer {arn} from target group {target_group_arn}")
                            continue
                        elbv2.deregister_targets(TargetGroupArn=target_group_arn, Targets=[{"Id": arn}])
                        print(f"Deregistered load balancer {arn} from target group {target_group_arn}")
        except ClientError as e:
            print(f"Could not deregister load balancer {arn} from target groups: {e}")

    def __delete_load_balancer(self, region: str, arn: str) -> None:
        try:
            elbv2 = self.session.client("elbv2", region_name=region)
            elbv2.delete_load_balancer(LoadBalancerArn=arn) if not self.config.dry_run else print(f"Dry run: would delete load balancer {arn}")
        except ClientError as e:
            print(f"Could not delete load balancer {arn}: {e}")

    def delete(self) -> None:
        for lb_info in self.load_balancers_info:
            region = lb_info["Region"]
            arn = lb_info["LoadBalancerArn"]
            # Deletion protection blocks delete_load_balancer, so it must be turned off first.
            self.__disable_deletion_protection(region, arn)
            # A load balancer registered as a target elsewhere must be deregistered first too.
            self.__deregister_from_target_groups(region, arn)
            self.__delete_load_balancer(region, arn)
