from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class RDSScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.instances_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("rds")

    def __list_instances(self, region: str) -> list[dict[str, Any]]:
        instances = []
        try:
            rds = self.session.client("rds", region_name=region)
            paginator = rds.get_paginator("describe_db_instances")
            for page in paginator.paginate():
                for instance in page.get("DBInstances", []):
                    instances.append({
                        "DBInstanceIdentifier": instance["DBInstanceIdentifier"],
                        "Region": region,
                        "Status": instance.get("DBInstanceStatus"),
                        "Engine": instance.get("Engine")
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
            print(f"DB Instance: {instance_info['DBInstanceIdentifier']} ({instance_info['Engine']}), Region: {instance_info['Region']}, Status: {instance_info['Status']}")

    def __disable_deletion_protection(self, region: str, identifier: str) -> None:
        try:
            rds = self.session.client("rds", region_name=region)
            rds.modify_db_instance(
                DBInstanceIdentifier=identifier,
                DeletionProtection=False,
                ApplyImmediately=True
            ) if not self.config.dry_run else print(f"Dry run: would disable deletion protection for DB instance {identifier}")
        except ClientError as e:
            pass

    def __delete_instance(self, region: str, identifier: str) -> None:
        try:
            rds = self.session.client("rds", region_name=region)
            if self.config.dry_run:
                snapshot_note = "no final snapshot" if self.config.skip_final_snapshot else "with a final snapshot"
                print(f"Dry run: would delete DB instance {identifier} ({snapshot_note})")
                return
            if self.config.skip_final_snapshot:
                rds.delete_db_instance(DBInstanceIdentifier=identifier, SkipFinalSnapshot=True)
            else:
                snapshot_id = f"{identifier}-final-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
                rds.delete_db_instance(
                    DBInstanceIdentifier=identifier,
                    SkipFinalSnapshot=False,
                    FinalDBSnapshotIdentifier=snapshot_id
                )
        except ClientError as e:
            pass

    def delete(self) -> None:
        for instance_info in self.instances_info:
            region = instance_info["Region"]
            identifier = instance_info["DBInstanceIdentifier"]
            # Deletion protection blocks delete_db_instance, so it must be turned off first.
            self.__disable_deletion_protection(region, identifier)
            self.__delete_instance(region, identifier)
