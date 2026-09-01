from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class VpcEndpointScanner:
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
            paginator = ec2.get_paginator("describe_vpc_endpoints")
            for page in paginator.paginate():
                for endpoint in page.get("VpcEndpoints", []):
                    if endpoint.get("State") in ("deleted", "deleting"):
                        continue
                    endpoints.append({
                        "VpcEndpointId": endpoint["VpcEndpointId"],
                        "Region": region,
                        "VpcId": endpoint.get("VpcId"),
                        "ServiceName": endpoint.get("ServiceName"),
                        "Type": endpoint.get("VpcEndpointType"),
                        "State": endpoint.get("State"),
                        "RequesterManaged": endpoint.get("RequesterManaged", False)
                    })
        except ClientError as e:
            print(f"Could not list VPC endpoints in {region}: {e}")
            endpoints = []
        return endpoints

    def scan(self) -> None:
        self.endpoints_info = []
        for region in self.__get_regions():
            self.endpoints_info.extend(self.__list_endpoints(region))

    def verbose_scan(self) -> None:
        for endpoint_info in self.endpoints_info:
            managed_note = " [requester-managed, not deletable via this account]" if endpoint_info["RequesterManaged"] else ""
            print(f"VPC Endpoint: {endpoint_info['VpcEndpointId']} ({endpoint_info['Type']}), Region: {endpoint_info['Region']}, VPC: {endpoint_info['VpcId']}, Service: {endpoint_info['ServiceName']}, State: {endpoint_info['State']}{managed_note}")

    def __delete_endpoint(self, region: str, endpoint_id: str) -> None:
        try:
            ec2 = self.session.client("ec2", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete VPC endpoint {endpoint_id}")
                return
            response = ec2.delete_vpc_endpoints(VpcEndpointIds=[endpoint_id])
            # A per-ID failure comes back as an entry here, not as a raised exception.
            for failure in response.get("Unsuccessful", []):
                error = failure.get("Error", {})
                print(f"Could not delete VPC endpoint {endpoint_id}: {error.get('Code')}: {error.get('Message')}")
        except ClientError as e:
            print(f"Could not delete VPC endpoint {endpoint_id}: {e}")

    def delete(self) -> None:
        for endpoint_info in self.endpoints_info:
            # Requester-managed endpoints are owned by the service provider on the other
            # end of the PrivateLink connection; this account can't delete them via the API.
            if endpoint_info["RequesterManaged"]:
                print(f"Skipping VPC endpoint {endpoint_info['VpcEndpointId']}: requester-managed by {endpoint_info['ServiceName']}")
                continue
            self.__delete_endpoint(endpoint_info["Region"], endpoint_info["VpcEndpointId"])
