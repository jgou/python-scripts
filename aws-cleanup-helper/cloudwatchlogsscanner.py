from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class CloudWatchLogsScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.log_groups_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("logs")

    def __list_log_groups(self, region: str) -> list[dict[str, Any]]:
        log_groups = []
        try:
            logs = self.session.client("logs", region_name=region)
            paginator = logs.get_paginator("describe_log_groups")
            for page in paginator.paginate():
                for log_group in page.get("logGroups", []):
                    log_groups.append({
                        "LogGroupName": log_group["logGroupName"],
                        "Region": region,
                        "StoredBytes": log_group.get("storedBytes", 0),
                        "DeletionProtectionEnabled": log_group.get("deletionProtectionEnabled", False)
                    })
        except ClientError as e:
            print(f"Could not list CloudWatch log groups in {region}: {e}")
            log_groups = []
        return log_groups

    def scan(self) -> None:
        self.log_groups_info = []
        for region in self.__get_regions():
            self.log_groups_info.extend(self.__list_log_groups(region))

    def verbose_scan(self) -> None:
        for log_group_info in self.log_groups_info:
            print(f"Log Group: {log_group_info['LogGroupName']}, Region: {log_group_info['Region']}, Stored Bytes: {log_group_info['StoredBytes']}")

    def __disable_deletion_protection(self, region: str, log_group_name: str) -> None:
        try:
            logs = self.session.client("logs", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would disable deletion protection for log group {log_group_name}")
                return
            logs.put_log_group_deletion_protection(logGroupIdentifier=log_group_name, deletionProtectionEnabled=False)
        except ClientError as e:
            print(f"Could not disable deletion protection for log group {log_group_name}: {e}")

    def __delete_log_group(self, region: str, log_group_name: str) -> None:
        try:
            logs = self.session.client("logs", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete log group {log_group_name}")
                return
            logs.delete_log_group(logGroupName=log_group_name)
        except ClientError as e:
            print(f"Could not delete log group {log_group_name}: {e}")

    def delete(self) -> None:
        for log_group_info in self.log_groups_info:
            region = log_group_info["Region"]
            log_group_name = log_group_info["LogGroupName"]
            # Deletion protection blocks delete_log_group, so it must be turned off first.
            if log_group_info["DeletionProtectionEnabled"]:
                self.__disable_deletion_protection(region, log_group_name)
            self.__delete_log_group(region, log_group_name)
