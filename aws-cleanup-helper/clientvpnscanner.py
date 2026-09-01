from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class ClientVpnScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.endpoints_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("ec2")

    def __list_endpoints(self, region: str) -> list[dict[str, Any]]:
        endpoints = []
        try:
            ec2 = self.session.client("ec2", region_name=region)
            paginator = ec2.get_paginator("describe_client_vpn_endpoints")
            for page in paginator.paginate():
                for endpoint in page.get("ClientVpnEndpoints", []):
                    status = endpoint.get("Status", {}).get("Code")
                    if status in ("deleted", "deleting"):
                        continue
                    endpoints.append({
                        "ClientVpnEndpointId": endpoint["ClientVpnEndpointId"],
                        "Region": region,
                        "Status": status
                    })
        except ClientError as e:
            print(f"Could not list Client VPN endpoints in {region}: {e}")
            endpoints = []
        return endpoints

    def scan(self) -> None:
        self.endpoints_info = []
        for region in self.__get_regions():
            self.endpoints_info.extend(self.__list_endpoints(region))

    def verbose_scan(self) -> None:
        for endpoint_info in self.endpoints_info:
            print(f"Client VPN Endpoint: {endpoint_info['ClientVpnEndpointId']}, Region: {endpoint_info['Region']}, Status: {endpoint_info['Status']}")

    def __disassociate_target_networks(self, region: str, endpoint_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            paginator = ec2.get_paginator("describe_client_vpn_target_networks")
            for page in paginator.paginate(ClientVpnEndpointId=endpoint_id):
                for association in page.get("ClientVpnTargetNetworks", []):
                    if association.get("Status", {}).get("Code") in ("disassociated", "disassociating"):
                        continue
                    association_id = association["AssociationId"]
                    if self.config.dry_run:
                        print(f"Dry run: would disassociate target network {association_id} from Client VPN endpoint {endpoint_id}")
                        continue
                    ec2.disassociate_client_vpn_target_network(ClientVpnEndpointId=endpoint_id, AssociationId=association_id)
        except ClientError as e:
            print(f"Could not disassociate target networks from Client VPN endpoint {endpoint_id}: {e}")

    def __delete_endpoint(self, region: str, endpoint_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete Client VPN endpoint {endpoint_id}")
                return
            ec2.delete_client_vpn_endpoint(ClientVpnEndpointId=endpoint_id)
        except ClientError as e:
            print(f"Could not delete Client VPN endpoint {endpoint_id}: {e}")

    def delete(self) -> None:
        for endpoint_info in self.endpoints_info:
            region = endpoint_info["Region"]
            endpoint_id = endpoint_info["ClientVpnEndpointId"]
            # Target network associations must be removed before the endpoint can be deleted.
            self.__disassociate_target_networks(region, endpoint_id)
            self.__delete_endpoint(region, endpoint_id)
