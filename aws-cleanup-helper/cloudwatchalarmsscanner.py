from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

# DeleteAlarms accepts a batch of names per call; chunking keeps each request small
# and bounded regardless of how many alarms an account has.
BATCH_SIZE = 100

class CloudWatchAlarmsScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.alarms_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("cloudwatch")

    def __list_alarms(self, region: str) -> list[dict[str, Any]]:
        alarms = []
        try:
            cloudwatch = self.session.client("cloudwatch", region_name=region)
            paginator = cloudwatch.get_paginator("describe_alarms")
            for page in paginator.paginate():
                for alarm in page.get("MetricAlarms", []) + page.get("CompositeAlarms", []):
                    alarms.append({
                        "AlarmName": alarm["AlarmName"],
                        "Region": region,
                        "StateValue": alarm.get("StateValue")
                    })
        except ClientError as e:
            print(f"Could not list CloudWatch alarms in {region}: {e}")
            alarms = []
        return alarms

    def scan(self) -> None:
        self.alarms_info = []
        for region in self.__get_regions():
            self.alarms_info.extend(self.__list_alarms(region))

    def verbose_scan(self) -> None:
        for alarm_info in self.alarms_info:
            print(f"Alarm: {alarm_info['AlarmName']}, Region: {alarm_info['Region']}, State: {alarm_info['StateValue']}")

    def __delete_alarms(self, region: str, alarm_names: list[str]) -> None:
        try:
            cloudwatch = self.session.client("cloudwatch", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete {len(alarm_names)} alarm(s) in {region}: {alarm_names}")
                return
            cloudwatch.delete_alarms(AlarmNames=alarm_names)
        except ClientError as e:
            print(f"Could not delete alarms {alarm_names}: {e}")

    def delete(self) -> None:
        alarms_by_region: dict[str, list[str]] = {}
        for alarm_info in self.alarms_info:
            alarms_by_region.setdefault(alarm_info["Region"], []).append(alarm_info["AlarmName"])

        for region, alarm_names in alarms_by_region.items():
            for i in range(0, len(alarm_names), BATCH_SIZE):
                self.__delete_alarms(region, alarm_names[i:i + BATCH_SIZE])
