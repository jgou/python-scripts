from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

# NS and SOA records at the zone apex exist on every hosted zone by default and can't be
# deleted directly; they get removed automatically when the hosted zone itself is deleted.
DEFAULT_RECORD_TYPES = {"NS", "SOA"}

class Route53Scanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.hosted_zones_info: list[dict[str, Any]] = []

    @staticmethod
    def __get_zone_id(zone: dict[str, Any]) -> str:
        return zone["Id"].replace("/hostedzone/", "")

    @staticmethod
    def __is_default_record(record: dict[str, Any], zone_name: str) -> bool:
        return record["Type"] in DEFAULT_RECORD_TYPES and record["Name"] == zone_name

    def __list_hosted_zones(self) -> list[dict[str, Any]]:
        zones = []
        try:
            route53 = self.session.client("route53")
            paginator = route53.get_paginator("list_hosted_zones")
            for page in paginator.paginate():
                zones.extend(page.get("HostedZones", []))
        except ClientError as e:
            zones = []
        return zones

    def __list_record_sets(self, zone_id: str) -> list[dict[str, Any]]:
        record_sets = []
        try:
            route53 = self.session.client("route53")
            paginator = route53.get_paginator("list_resource_record_sets")
            for page in paginator.paginate(HostedZoneId=zone_id):
                record_sets.extend(page.get("ResourceRecordSets", []))
        except ClientError as e:
            record_sets = []
        return record_sets

    def scan(self) -> None:
        self.hosted_zones_info = []
        for zone in self.__list_hosted_zones():
            zone_id = self.__get_zone_id(zone)
            record_sets = self.__list_record_sets(zone_id)
            deletable_records = [r for r in record_sets if not self.__is_default_record(r, zone["Name"])]
            self.hosted_zones_info.append({
                "Id": zone_id,
                "Name": zone["Name"],
                "Private": zone.get("Config", {}).get("PrivateZone", False),
                "RecordCount": len(record_sets),
                "DeletableRecords": deletable_records
            })

    def verbose_scan(self) -> None:
        for zone_info in self.hosted_zones_info:
            zone_type = "Private" if zone_info["Private"] else "Public"
            print(f"Hosted Zone: {zone_info['Id']} ({zone_info['Name']}), Type: {zone_type}, Records: {zone_info['RecordCount']}")

    def __delete_record_set(self, zone_id: str, record: dict[str, Any]) -> None:
        try:
            route53 = self.session.client("route53")
            route53.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch={"Changes": [{"Action": "DELETE", "ResourceRecordSet": record}]}
            ) if not self.config.dry_run else print(f"Dry run: would delete record {record['Name']} ({record['Type']}) in zone {zone_id}")
        except ClientError as e:
            pass

    def __delete_hosted_zone(self, zone_id: str) -> None:
        try:
            route53 = self.session.client("route53")
            route53.delete_hosted_zone(Id=zone_id) if not self.config.dry_run else print(f"Dry run: would delete hosted zone {zone_id}")
        except ClientError as e:
            pass

    def delete(self) -> None:
        for zone_info in self.hosted_zones_info:
            zone_id = zone_info["Id"]
            for record in zone_info["DeletableRecords"]:
                self.__delete_record_set(zone_id, record)
            self.__delete_hosted_zone(zone_id)
