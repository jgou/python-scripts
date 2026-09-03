from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class OutboundResolverScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.endpoints_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("route53resolver")

    def __list_rules_for_endpoint(self, route53resolver, endpoint_id: str) -> list[str]:
        rule_ids = []
        paginator = route53resolver.get_paginator("list_resolver_rules")
        for page in paginator.paginate():
            for rule in page.get("ResolverRules", []):
                if rule.get("ResolverEndpointId") == endpoint_id:
                    rule_ids.append(rule["Id"])
        return rule_ids

    def __list_endpoints(self, region: str) -> list[dict[str, Any]]:
        endpoints = []
        try:
            route53resolver = self.session.client("route53resolver", region_name=region)
            paginator = route53resolver.get_paginator("list_resolver_endpoints")
            for page in paginator.paginate():
                for endpoint in page.get("ResolverEndpoints", []):
                    if endpoint.get("Direction") != "OUTBOUND":
                        continue
                    if endpoint.get("Status") in ("DELETING",):
                        continue
                    endpoint_id = endpoint["Id"]
                    endpoints.append({
                        "Id": endpoint_id,
                        "Name": endpoint.get("Name"),
                        "Region": region,
                        "Status": endpoint.get("Status"),
                        "HostVPCId": endpoint.get("HostVPCId"),
                        "ResolverRuleIds": self.__list_rules_for_endpoint(route53resolver, endpoint_id)
                    })
        except ClientError as e:
            print(f"Could not list Route 53 Resolver outbound endpoints in {region}: {e}")
            endpoints = []
        return endpoints

    def scan(self) -> None:
        self.endpoints_info = []
        for region in self.__get_regions():
            self.endpoints_info.extend(self.__list_endpoints(region))

    def verbose_scan(self) -> None:
        for endpoint_info in self.endpoints_info:
            print(f"Outbound Resolver Endpoint: {endpoint_info['Id']} ({endpoint_info['Name']}), Region: {endpoint_info['Region']}, VPC: {endpoint_info['HostVPCId']}, Status: {endpoint_info['Status']}, Resolver Rules: {endpoint_info['ResolverRuleIds'] or 'None'}")

    def __disassociate_rule_from_vpcs(self, route53resolver, rule_id: str) -> None:
        paginator = route53resolver.get_paginator("list_resolver_rule_associations")
        for page in paginator.paginate():
            for association in page.get("ResolverRuleAssociations", []):
                if association.get("ResolverRuleId") != rule_id:
                    continue
                if association.get("Status") in ("DELETING",):
                    continue
                vpc_id = association["VPCId"]
                if self.config.dry_run:
                    print(f"Dry run: would disassociate resolver rule {rule_id} from VPC {vpc_id}")
                    continue
                route53resolver.disassociate_resolver_rule(VPCId=vpc_id, ResolverRuleId=rule_id)

    def __delete_rule(self, region: str, rule_id: str) -> None:
        try:
            route53resolver = self.session.client("route53resolver", region_name=region)
            # A resolver rule must be disassociated from every VPC before it can be deleted.
            self.__disassociate_rule_from_vpcs(route53resolver, rule_id)
            if self.config.dry_run:
                print(f"Dry run: would delete resolver rule {rule_id}")
                return
            route53resolver.delete_resolver_rule(ResolverRuleId=rule_id)
        except ClientError as e:
            print(f"Could not delete resolver rule {rule_id}: {e}")

    def __delete_endpoint(self, region: str, endpoint_id: str) -> None:
        try:
            route53resolver = self.session.client("route53resolver", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete outbound Resolver endpoint {endpoint_id}")
                return
            route53resolver.delete_resolver_endpoint(ResolverEndpointId=endpoint_id)
        except ClientError as e:
            print(f"Could not delete outbound Resolver endpoint {endpoint_id}: {e}")

    def delete(self) -> None:
        for endpoint_info in self.endpoints_info:
            region = endpoint_info["Region"]
            # An outbound endpoint can't be deleted while any resolver rule still targets it.
            for rule_id in endpoint_info["ResolverRuleIds"]:
                self.__delete_rule(region, rule_id)
            self.__delete_endpoint(region, endpoint_info["Id"])
