from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

# CloudWatch dashboards are account-wide, not regional, but the API still requires a
# region endpoint; DeleteDashboards accepts a batch of names per call.
BATCH_SIZE = 100

class CloudWatchDashboardsScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.dashboards_info: list[dict[str, Any]] = []

    def __list_dashboards(self) -> list[dict[str, Any]]:
        dashboards = []
        try:
            cloudwatch = self.session.client("cloudwatch")
            paginator = cloudwatch.get_paginator("list_dashboards")
            for page in paginator.paginate():
                for dashboard in page.get("DashboardEntries", []):
                    dashboards.append({
                        "DashboardName": dashboard["DashboardName"],
                        "LastModified": dashboard.get("LastModified")
                    })
        except ClientError as e:
            print(f"Could not list CloudWatch dashboards: {e}")
            dashboards = []
        return dashboards

    def scan(self) -> None:
        self.dashboards_info = self.__list_dashboards()

    def verbose_scan(self) -> None:
        for dashboard_info in self.dashboards_info:
            print(f"Dashboard: {dashboard_info['DashboardName']}, Last Modified: {dashboard_info['LastModified']}")

    def __delete_dashboards(self, dashboard_names: list[str]) -> None:
        try:
            cloudwatch = self.session.client("cloudwatch")
            if self.config.dry_run:
                print(f"Dry run: would delete {len(dashboard_names)} dashboard(s): {dashboard_names}")
                return
            cloudwatch.delete_dashboards(DashboardNames=dashboard_names)
        except ClientError as e:
            print(f"Could not delete dashboards {dashboard_names}: {e}")

    def delete(self) -> None:
        names = [dashboard_info["DashboardName"] for dashboard_info in self.dashboards_info]
        for i in range(0, len(names), BATCH_SIZE):
            self.__delete_dashboards(names[i:i + BATCH_SIZE])
