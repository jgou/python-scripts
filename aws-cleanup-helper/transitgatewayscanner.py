from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

# Only VPC and peering attachments have a dedicated delete API; VPN attachments are
# deleted via the VPN connection itself (see vpnscanner.py), and Direct Connect Gateway
# attachments are managed outside this tool's scope.
DELETABLE_RESOURCE_TYPES = {"vpc", "peering"}

class TransitGatewayScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.attachments_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("ec2")

    def __list_attachments(self, region: str) -> list[dict[str, Any]]:
        attachments = []
        try:
            ec2 = self.session.client("ec2", region_name=region)
            paginator = ec2.get_paginator("describe_transit_gateway_attachments")
            for page in paginator.paginate():
                for attachment in page.get("TransitGatewayAttachments", []):
                    if attachment.get("State") in ("deleted", "deleting"):
                        continue
                    attachments.append({
                        "TransitGatewayAttachmentId": attachment["TransitGatewayAttachmentId"],
                        "Region": region,
                        "ResourceType": attachment.get("ResourceType"),
                        "State": attachment.get("State")
                    })
        except ClientError as e:
            print(f"Could not list Transit Gateway attachments in {region}: {e}")
            attachments = []
        return attachments

    def scan(self) -> None:
        self.attachments_info = []
        for region in self.__get_regions():
            self.attachments_info.extend(self.__list_attachments(region))

    def verbose_scan(self) -> None:
        for attachment_info in self.attachments_info:
            print(f"Transit Gateway Attachment: {attachment_info['TransitGatewayAttachmentId']} ({attachment_info['ResourceType']}), Region: {attachment_info['Region']}, State: {attachment_info['State']}")

    def __delete_attachment(self, region: str, attachment_info: dict[str, Any]) -> None:
        attachment_id = attachment_info["TransitGatewayAttachmentId"]
        resource_type = attachment_info["ResourceType"]
        if resource_type not in DELETABLE_RESOURCE_TYPES:
            print(f"Skipping Transit Gateway attachment {attachment_id}: deletion not supported for resource type '{resource_type}'")
            return
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete Transit Gateway attachment {attachment_id} ({resource_type})")
                return
            if resource_type == "vpc":
                ec2.delete_transit_gateway_vpc_attachment(TransitGatewayAttachmentId=attachment_id)
            elif resource_type == "peering":
                ec2.delete_transit_gateway_peering_attachment(TransitGatewayAttachmentId=attachment_id)
        except ClientError as e:
            print(f"Could not delete Transit Gateway attachment {attachment_id}: {e}")

    def delete(self) -> None:
        for attachment_info in self.attachments_info:
            self.__delete_attachment(attachment_info["Region"], attachment_info)
