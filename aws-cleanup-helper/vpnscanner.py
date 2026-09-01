import time
from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class VpnScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.vpn_connections_info: list[dict[str, Any]] = []
        self.customer_gateways_info: list[dict[str, Any]] = []
        self.vpn_gateways_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("ec2")

    def __list_vpn_connections(self, region: str) -> list[dict[str, Any]]:
        vpn_connections = []
        try:
            ec2 = self.session.client("ec2", region_name=region)
            response = ec2.describe_vpn_connections()
            for vpn_connection in response.get("VpnConnections", []):
                if vpn_connection.get("State") in ("deleted", "deleting"):
                    continue
                vpn_connections.append({
                    "VpnConnectionId": vpn_connection["VpnConnectionId"],
                    "Region": region,
                    "State": vpn_connection.get("State"),
                    "Type": vpn_connection.get("Type")
                })
        except ClientError as e:
            print(f"Could not list VPN connections in {region}: {e}")
            vpn_connections = []
        return vpn_connections

    def __list_customer_gateways(self, region: str) -> list[dict[str, Any]]:
        customer_gateways = []
        try:
            ec2 = self.session.client("ec2", region_name=region)
            response = ec2.describe_customer_gateways()
            for customer_gateway in response.get("CustomerGateways", []):
                if customer_gateway.get("State") in ("deleted", "deleting"):
                    continue
                customer_gateways.append({
                    "CustomerGatewayId": customer_gateway["CustomerGatewayId"],
                    "Region": region,
                    "State": customer_gateway.get("State"),
                    "IpAddress": customer_gateway.get("IpAddress")
                })
        except ClientError as e:
            print(f"Could not list Customer Gateways in {region}: {e}")
            customer_gateways = []
        return customer_gateways

    def __list_vpn_gateways(self, region: str) -> list[dict[str, Any]]:
        vpn_gateways = []
        try:
            ec2 = self.session.client("ec2", region_name=region)
            response = ec2.describe_vpn_gateways()
            for vpn_gateway in response.get("VpnGateways", []):
                if vpn_gateway.get("State") in ("deleted", "deleting"):
                    continue
                attached_vpc_ids = [
                    attachment["VpcId"] for attachment in vpn_gateway.get("VpcAttachments", [])
                    if attachment.get("State") == "attached"
                ]
                vpn_gateways.append({
                    "VpnGatewayId": vpn_gateway["VpnGatewayId"],
                    "Region": region,
                    "State": vpn_gateway.get("State"),
                    "AttachedVpcIds": attached_vpc_ids
                })
        except ClientError as e:
            print(f"Could not list Virtual Private Gateways in {region}: {e}")
            vpn_gateways = []
        return vpn_gateways

    def scan(self) -> None:
        self.vpn_connections_info = []
        self.customer_gateways_info = []
        self.vpn_gateways_info = []
        for region in self.__get_regions():
            self.vpn_connections_info.extend(self.__list_vpn_connections(region))
            self.customer_gateways_info.extend(self.__list_customer_gateways(region))
            self.vpn_gateways_info.extend(self.__list_vpn_gateways(region))

    def verbose_scan(self) -> None:
        for vpn_connection_info in self.vpn_connections_info:
            print(f"VPN Connection: {vpn_connection_info['VpnConnectionId']} ({vpn_connection_info['Type']}), Region: {vpn_connection_info['Region']}, State: {vpn_connection_info['State']}")
        for customer_gateway_info in self.customer_gateways_info:
            print(f"Customer Gateway: {customer_gateway_info['CustomerGatewayId']} ({customer_gateway_info['IpAddress']}), Region: {customer_gateway_info['Region']}, State: {customer_gateway_info['State']}")
        for vpn_gateway_info in self.vpn_gateways_info:
            print(f"Virtual Private Gateway: {vpn_gateway_info['VpnGatewayId']}, Region: {vpn_gateway_info['Region']}, State: {vpn_gateway_info['State']}, Attached VPCs: {vpn_gateway_info['AttachedVpcIds'] or 'None'}")

    def __delete_vpn_connection(self, region: str, vpn_connection_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete VPN connection {vpn_connection_id}")
                return
            ec2.delete_vpn_connection(VpnConnectionId=vpn_connection_id)
        except ClientError as e:
            print(f"Could not delete VPN connection {vpn_connection_id}: {e}")

    def __delete_customer_gateway(self, region: str, customer_gateway_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete Customer Gateway {customer_gateway_id}")
                return
            ec2.delete_customer_gateway(CustomerGatewayId=customer_gateway_id)
        except ClientError as e:
            print(f"Could not delete Customer Gateway {customer_gateway_id}: {e}")

    def __detach_vpn_gateway(self, region: str, vpn_gateway_id: str, vpc_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would detach Virtual Private Gateway {vpn_gateway_id} from VPC {vpc_id}")
                return
            ec2.detach_vpn_gateway(VpnGatewayId=vpn_gateway_id, VpcId=vpc_id)
        except ClientError as e:
            print(f"Could not detach Virtual Private Gateway {vpn_gateway_id} from VPC {vpc_id}: {e}")

    def __wait_for_detachment(self, region: str, vpn_gateway_id: str, vpc_id: str, max_attempts: int = 40, delay_seconds: int = 15) -> None:
        # There's no boto3 waiter for VGW detachment, so this polls describe_vpn_gateways
        # directly; delete_vpn_gateway fails with IncorrectState while still detaching.
        try:
            ec2 = self.session.client("ec2", region_name=region)
            for _ in range(max_attempts):
                response = ec2.describe_vpn_gateways(VpnGatewayIds=[vpn_gateway_id])
                gateways = response.get("VpnGateways", [])
                attachment = next(
                    (a for g in gateways for a in g.get("VpcAttachments", []) if a.get("VpcId") == vpc_id),
                    None
                )
                if attachment is None or attachment.get("State") == "detached":
                    return
                time.sleep(delay_seconds)
            print(f"Timed out waiting for Virtual Private Gateway {vpn_gateway_id} to detach from VPC {vpc_id}")
        except ClientError as e:
            print(f"Could not confirm detachment of Virtual Private Gateway {vpn_gateway_id} from VPC {vpc_id}: {e}")

    def __delete_vpn_gateway(self, region: str, vpn_gateway_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete Virtual Private Gateway {vpn_gateway_id}")
                return
            ec2.delete_vpn_gateway(VpnGatewayId=vpn_gateway_id)
        except ClientError as e:
            print(f"Could not delete Virtual Private Gateway {vpn_gateway_id}: {e}")

    def delete(self) -> None:
        for vpn_connection_info in self.vpn_connections_info:
            self.__delete_vpn_connection(vpn_connection_info["Region"], vpn_connection_info["VpnConnectionId"])
        for customer_gateway_info in self.customer_gateways_info:
            # A Customer Gateway still referenced by a VPN connection can't be deleted;
            # deleting VPN connections first (above) clears that dependency.
            self.__delete_customer_gateway(customer_gateway_info["Region"], customer_gateway_info["CustomerGatewayId"])
        for vpn_gateway_info in self.vpn_gateways_info:
            region = vpn_gateway_info["Region"]
            vpn_gateway_id = vpn_gateway_info["VpnGatewayId"]
            # A Virtual Private Gateway must be detached from every VPC before it can be deleted.
            for vpc_id in vpn_gateway_info["AttachedVpcIds"]:
                self.__detach_vpn_gateway(region, vpn_gateway_id, vpc_id)
                if not self.config.dry_run:
                    self.__wait_for_detachment(region, vpn_gateway_id, vpc_id)
            self.__delete_vpn_gateway(region, vpn_gateway_id)
