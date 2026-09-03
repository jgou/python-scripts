from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class EbsSnapshotScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.snapshots_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("ec2")

    def __list_snapshots(self, region: str) -> list[dict[str, Any]]:
        snapshots = []
        try:
            ec2 = self.session.client("ec2", region_name=region)
            paginator = ec2.get_paginator("describe_snapshots")
            for page in paginator.paginate(OwnerIds=["self"]):
                for snapshot in page.get("Snapshots", []):
                    snapshots.append({
                        "SnapshotId": snapshot["SnapshotId"],
                        "Region": region,
                        "VolumeSize": snapshot.get("VolumeSize"),
                        "State": snapshot.get("State")
                    })
        except ClientError as e:
            print(f"Could not list EBS snapshots in {region}: {e}")
            snapshots = []
        return snapshots

    def scan(self) -> None:
        self.snapshots_info = []
        for region in self.__get_regions():
            self.snapshots_info.extend(self.__list_snapshots(region))

    def verbose_scan(self) -> None:
        for snapshot_info in self.snapshots_info:
            print(f"EBS Snapshot: {snapshot_info['SnapshotId']} ({snapshot_info['VolumeSize']} GiB), Region: {snapshot_info['Region']}, State: {snapshot_info['State']}")

    def __delete_snapshot(self, region: str, snapshot_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete EBS snapshot {snapshot_id}")
                return
            ec2.delete_snapshot(SnapshotId=snapshot_id)
        except ClientError as e:
            print(f"Could not delete EBS snapshot {snapshot_id}: {e}")

    def delete(self) -> None:
        for snapshot_info in self.snapshots_info:
            self.__delete_snapshot(snapshot_info["Region"], snapshot_info["SnapshotId"])
