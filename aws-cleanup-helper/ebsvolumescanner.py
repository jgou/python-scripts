from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class EbsVolumeScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.volumes_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("ec2")

    def __list_volumes(self, region: str) -> list[dict[str, Any]]:
        volumes = []
        try:
            ec2 = self.session.client("ec2", region_name=region)
            paginator = ec2.get_paginator("describe_volumes")
            for page in paginator.paginate():
                for volume in page.get("Volumes", []):
                    volumes.append({
                        "VolumeId": volume["VolumeId"],
                        "Region": region,
                        "Size": volume.get("Size"),
                        "State": volume.get("State")
                    })
        except ClientError as e:
            print(f"Could not list EBS volumes in {region}: {e}")
            volumes = []
        return volumes

    def scan(self) -> None:
        self.volumes_info = []
        for region in self.__get_regions():
            self.volumes_info.extend(self.__list_volumes(region))

    def verbose_scan(self) -> None:
        for volume_info in self.volumes_info:
            print(f"EBS Volume: {volume_info['VolumeId']} ({volume_info['Size']} GiB), Region: {volume_info['Region']}, State: {volume_info['State']}")

    def __delete_volume(self, region: str, volume_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete EBS volume {volume_id}")
                return
            ec2.delete_volume(VolumeId=volume_id)
        except ClientError as e:
            print(f"Could not delete EBS volume {volume_id}: {e}")

    def delete(self) -> None:
        for volume_info in self.volumes_info:
            self.__delete_volume(volume_info["Region"], volume_info["VolumeId"])
