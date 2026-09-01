from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class Ec2Scanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.instances_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("ec2")

    @staticmethod
    def __get_name_tag(instance: dict[str, Any]) -> str | None:
        for tag in instance.get("Tags", []):
            if tag["Key"] == "Name":
                return tag["Value"]
        return None

    @staticmethod
    def __get_volumes(instance: dict[str, Any]) -> list[dict[str, Any]]:
        volumes = []
        for mapping in instance.get("BlockDeviceMappings", []):
            ebs = mapping.get("Ebs")
            if not ebs:
                continue
            volumes.append({
                "VolumeId": ebs.get("VolumeId"),
                "DeviceName": mapping.get("DeviceName"),
                "DeleteOnTermination": ebs.get("DeleteOnTermination", False)
            })
        return volumes

    def __list_instances(self, region: str) -> list[dict[str, Any]]:
        instances = []
        try:
            ec2 = self.session.client("ec2", region_name=region)
            paginator = ec2.get_paginator("describe_instances")
            for page in paginator.paginate():
                for reservation in page.get("Reservations", []):
                    for instance in reservation.get("Instances", []):
                        instances.append({
                            "InstanceId": instance["InstanceId"],
                            "Name": self.__get_name_tag(instance),
                            "Region": region,
                            "State": instance["State"]["Name"],
                            "Volumes": self.__get_volumes(instance)
                        })
        except ClientError as e:
            instances = []
        return instances

    def scan(self) -> None:
        self.instances_info = []
        for region in self.__get_regions():
            self.instances_info.extend(self.__list_instances(region))

    def verbose_scan(self) -> None:
        for instance_info in self.instances_info:
            volume_ids = ", ".join(v["VolumeId"] for v in instance_info["Volumes"]) or "None"
            name = instance_info["Name"] or "-"
            print(f"Instance: {instance_info['InstanceId']} ({name}), Region: {instance_info['Region']}, State: {instance_info['State']}, Volumes: {volume_ids}")

    def __terminate_instance(self, region: str, instance_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            ec2.terminate_instances(InstanceIds=[instance_id]) if not self.config.dry_run else print(f"Dry run: would terminate instance {instance_id}")
        except ClientError as e:
            pass

    def __wait_for_termination(self, region: str, instance_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            waiter = ec2.get_waiter("instance_terminated")
            waiter.wait(InstanceIds=[instance_id])
        except ClientError as e:
            pass

    def __delete_volume(self, region: str, volume_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            ec2.delete_volume(VolumeId=volume_id) if not self.config.dry_run else print(f"Dry run: would delete volume {volume_id}")
        except ClientError as e:
            pass

    def delete(self) -> None:
        for instance_info in self.instances_info:
            instance_id = instance_info["InstanceId"]
            region = instance_info["Region"]
            volumes_to_delete = [v["VolumeId"] for v in instance_info["Volumes"] if not v["DeleteOnTermination"]]

            if self.config.dry_run:
                print(f"Dry run: would terminate instance {instance_id}")
                for volume_id in volumes_to_delete:
                    print(f"Dry run: would delete volume {volume_id} after terminating instance {instance_id}")
                continue

            self.__terminate_instance(region, instance_id)
            if volumes_to_delete:
                # Volumes without DeleteOnTermination survive the instance and must be
                # deleted explicitly, but only once detached, i.e. after termination completes.
                self.__wait_for_termination(region, instance_id)
                for volume_id in volumes_to_delete:
                    self.__delete_volume(region, volume_id)
