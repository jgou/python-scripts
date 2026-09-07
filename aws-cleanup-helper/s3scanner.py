from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

# Listing is inherently sequential (each page needs the previous page's continuation
# token), but the delete_objects calls for already-listed pages don't depend on each
# other, so running several of them at once closes most of the gap with the S3 console's
# parallel "Empty bucket" feature instead of waiting for each batch before listing the next.
MAX_CONCURRENT_DELETES = 10

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
            print(f"Could not get region for bucket {bucket_name}: {e}")
            location = None
        return location

    def __has_objects(self, bucket_name: str) -> bool:
        has_objects = False
        try:
            s3 = self.session.client("s3")
            response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
            has_objects = response.get("KeyCount", 0) > 0
        except ClientError as e:
            print(f"Could not check objects for bucket {bucket_name}: {e}")
            has_objects = False
        return has_objects

    def __list_buckets(self) -> list[str]:
        buckets = []
        try:
            s3 = self.session.client("s3")
            response = s3.list_buckets()
            buckets = [bucket["Name"] for bucket in response.get("Buckets", [])]
        except ClientError as e:
            print(f"Could not list buckets: {e}")
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
        print(f"Scan complete: found {len(self.buckets_info)} bucket(s).")

    def verbose_scan(self) -> None:
        for bucket_info in self.buckets_info:
            print(f"Bucket: {bucket_info['Name']}, Region: {bucket_info['Region']}, Has Objects: {bucket_info['HasObjects']}")

    def __delete_bucket(self, bucket_name: str) -> None:
        try:
            s3 = self.session.client("s3")
            if self.config.dry_run:
                print(f"Dry run: would delete bucket {bucket_name}")
                return
            print(f"Deleting bucket {bucket_name}...")
            s3.delete_bucket(Bucket=bucket_name)
            print(f"Deleted bucket {bucket_name}.")
        except ClientError as e:
            print(f"Could not delete bucket {bucket_name}: {e}")

    def __delete_batch(self, s3, bucket_name: str, delete_keys: list[dict[str, str]], page_number: int) -> int:
        try:
            s3.delete_objects(Bucket=bucket_name, Delete={"Objects": delete_keys})
            print(f"Deleted {len(delete_keys)} object(s) from bucket {bucket_name} (page {page_number})")
            return len(delete_keys)
        except ClientError as e:
            print(f"Could not delete a batch of {len(delete_keys)} object(s) from bucket {bucket_name} (page {page_number}): {e}")
            return 0

    def __delete_objects(self, bucket_name: str) -> None:
        try:
            # A boto3 client's methods are safe to call concurrently from multiple threads,
            # so one client can be shared across the whole thread pool below.
            s3 = self.session.client("s3")
            print(f"Deleting objects in bucket {bucket_name}...")
            paginator = s3.get_paginator("list_objects_v2")
            total_deleted = 0
            with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DELETES) as executor:
                futures = []
                for page_number, page in enumerate(paginator.paginate(Bucket=bucket_name), start=1):
                    objects = page.get("Contents", [])
                    if not objects:
                        continue
                    delete_keys = [{"Key": obj["Key"]} for obj in objects]
                    if self.config.dry_run:
                        print(f"Dry run: would delete {len(delete_keys)} object(s) from bucket {bucket_name} (page {page_number})")
                        continue
                    futures.append(executor.submit(self.__delete_batch, s3, bucket_name, delete_keys, page_number))
                for future in as_completed(futures):
                    total_deleted += future.result()
            if not self.config.dry_run:
                print(f"Finished deleting objects in bucket {bucket_name}: {total_deleted} object(s) removed.")
        except ClientError as e:
            print(f"Could not delete objects in bucket {bucket_name}: {e}")

    def delete(self) -> None:
        total_buckets = len(self.buckets_info)
        for index, bucket_info in enumerate(self.buckets_info, start=1):
            bucket_name = bucket_info["Name"]
            if bucket_name in self.config.skip_s3_buckets:
                print(f"Skipping bucket {bucket_name} ({index}/{total_buckets}): excluded via --skip-s3-bucket")
                continue
            print(f"Processing bucket {bucket_name} ({index}/{total_buckets})...")
            if bucket_info["HasObjects"]:
                self.__delete_objects(bucket_name)
            self.__delete_bucket(bucket_name)
