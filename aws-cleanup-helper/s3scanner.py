from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class S3Scanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.buckets_info: list[dict[str, Any]] = []

    def __get_bucket_region(self, bucket_name: str) -> str | None:
        location = None
        try:
            s3 = self.session.client("s3")
            response = s3.get_bucket_location(Bucket=bucket_name)
            location = response.get("LocationConstraint")
        except ClientError as e:
            location = None
        return location

    def __has_objects(self, bucket_name: str) -> bool:
        has_objects = False
        try:
            s3 = self.session.client("s3")
            response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
            has_objects = response.get("KeyCount", 0) > 0
        except ClientError as e:
            has_objects = False
        return has_objects

    def __list_buckets(self) -> list[str]:
        buckets = []
        try:
            s3 = self.session.client("s3")
            response = s3.list_buckets()
            buckets = [bucket["Name"] for bucket in response.get("Buckets", [])]
        except ClientError as e:
            buckets = []
        return buckets

    def scan(self) -> None:
        self.buckets_info = []
        for bucket_name in self.__list_buckets():
            region = self.__get_bucket_region(bucket_name)
            has_objects = self.__has_objects(bucket_name)
            self.buckets_info.append({
                "Name": bucket_name,
                "Region": region,
                "HasObjects": has_objects
            })

    def verbose_scan(self) -> None:
        for bucket_info in self.buckets_info:
            print(f"Bucket: {bucket_info['Name']}, Region: {bucket_info['Region']}, Has Objects: {bucket_info['HasObjects']}")

    def __delete_bucket(self, bucket_name: str) -> None:
        try:
            s3 = self.session.client("s3")
            s3.delete_bucket(Bucket=bucket_name) if not self.config.dry_run else print(f"Dry run: would delete bucket {bucket_name}")
        except ClientError as e:
            pass

    def __delete_objects(self, bucket_name: str) -> None:
        try:
            s3 = self.session.client("s3")
            paginator = s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket_name):
                objects = page.get("Contents", [])
                if objects:
                    delete_keys = [{"Key": obj["Key"]} for obj in objects]
                    s3.delete_objects(Bucket=bucket_name, Delete={"Objects": delete_keys}) if not self.config.dry_run else print(f"Dry run: would delete objects in bucket {bucket_name}")
        except ClientError as e:
            pass

    def delete(self) -> None:
        for bucket_info in self.buckets_info:
            bucket_name = bucket_info["Name"]
            if bucket_info["HasObjects"]:
                self.__delete_objects(bucket_name) if not self.config.dry_run else print(f"Dry run: would delete objects in bucket {bucket_name}")
            self.__delete_bucket(bucket_name) if not self.config.dry_run else print(f"Dry run: would delete bucket {bucket_name}")