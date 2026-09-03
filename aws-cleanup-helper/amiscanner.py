from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class AmiScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.images_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("ec2")

    def __list_images(self, region: str) -> list[dict[str, Any]]:
        images = []
        try:
            ec2 = self.session.client("ec2", region_name=region)
            paginator = ec2.get_paginator("describe_images")
            for page in paginator.paginate(Owners=["self"]):
                for image in page.get("Images", []):
                    images.append({
                        "ImageId": image["ImageId"],
                        "Region": region,
                        "Name": image.get("Name"),
                        "State": image.get("State"),
                        "DeregistrationProtection": image.get("DeregistrationProtection") == "enabled"
                    })
        except ClientError as e:
            print(f"Could not list AMIs in {region}: {e}")
            images = []
        return images

    def scan(self) -> None:
        self.images_info = []
        for region in self.__get_regions():
            self.images_info.extend(self.__list_images(region))

    def verbose_scan(self) -> None:
        for image_info in self.images_info:
            print(f"AMI: {image_info['ImageId']} ({image_info['Name']}), Region: {image_info['Region']}, State: {image_info['State']}")

    def __disable_deregistration_protection(self, region: str, image_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would disable deregistration protection for AMI {image_id}")
                return
            ec2.disable_image_deregistration_protection(ImageId=image_id)
        except ClientError as e:
            print(f"Could not disable deregistration protection for AMI {image_id}: {e}")

    def __deregister_image(self, region: str, image_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would deregister AMI {image_id} and delete its backing snapshots")
                return
            ec2.deregister_image(ImageId=image_id, DeleteAssociatedSnapshots=True)
        except ClientError as e:
            print(f"Could not deregister AMI {image_id}: {e}")

    def delete(self) -> None:
        for image_info in self.images_info:
            region = image_info["Region"]
            image_id = image_info["ImageId"]
            # Deregistration protection blocks deregister_image, so it must be turned off first.
            if image_info["DeregistrationProtection"]:
                self.__disable_deregistration_protection(region, image_id)
            self.__deregister_image(region, image_id)
