from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class CloudTrailScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.trails_info: list[dict[str, Any]] = []

    def __list_trails(self) -> list[dict[str, Any]]:
        trails = []
        try:
            # DescribeTrails returns every trail in the account, including ones homed in
            # other regions, regardless of which region's endpoint is called.
            cloudtrail = self.session.client("cloudtrail", region_name="us-east-1")
            response = cloudtrail.describe_trails(includeShadowTrails=True)
            for trail in response.get("trailList", []):
                home_region = trail.get("HomeRegion")
                if self.config.regions and home_region not in self.config.regions:
                    continue
                trails.append({
                    "Name": trail["Name"],
                    "TrailARN": trail["TrailARN"],
                    "HomeRegion": home_region,
                    "S3BucketName": trail.get("S3BucketName"),
                    "IsMultiRegionTrail": trail.get("IsMultiRegionTrail", False),
                    "IsOrganizationTrail": trail.get("IsOrganizationTrail", False)
                })
        except ClientError as e:
            print(f"Could not list CloudTrail trails: {e}")
            trails = []
        return trails

    def scan(self) -> None:
        self.trails_info = self.__list_trails()

    def verbose_scan(self) -> None:
        for trail_info in self.trails_info:
            print(f"CloudTrail Trail: {trail_info['Name']}, Home Region: {trail_info['HomeRegion']}, Multi-Region: {trail_info['IsMultiRegionTrail']}, S3 Bucket: {trail_info['S3BucketName']}")

    def __stop_logging(self, region: str, trail_arn: str) -> None:
        try:
            cloudtrail = self.session.client("cloudtrail", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would stop logging for trail {trail_arn}")
                return
            cloudtrail.stop_logging(Name=trail_arn)
        except ClientError as e:
            print(f"Could not stop logging for trail {trail_arn}: {e}")

    def __delete_trail(self, region: str, trail_arn: str) -> None:
        try:
            cloudtrail = self.session.client("cloudtrail", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete trail {trail_arn}")
                return
            cloudtrail.delete_trail(Name=trail_arn)
        except ClientError as e:
            print(f"Could not delete trail {trail_arn}: {e}")

    def delete(self) -> None:
        for trail_info in self.trails_info:
            region = trail_info["HomeRegion"]
            trail_arn = trail_info["TrailARN"]
            if trail_info["IsOrganizationTrail"]:
                print(f"Skipping trail {trail_info['Name']}: it's an AWS Organizations trail and must be deleted from the management account")
                continue
            # Stopping logging first avoids new events landing mid-deletion.
            self.__stop_logging(region, trail_arn)
            self.__delete_trail(region, trail_arn)
