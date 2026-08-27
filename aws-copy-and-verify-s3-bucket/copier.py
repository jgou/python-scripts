import boto3
from config import ToolConfig

class S3BucketCopier:
    def __init__(self, config: ToolConfig):
        self.config = config

    def __init_sessions(self):
        # Initialize boto3 sessions for source and destination profiles
        self.source_session = boto3.Session(profile_name=self.config.source_profile, region_name=self.config.source_region)
        self.destination_session = boto3.Session(profile_name=self.config.destination_profile, region_name=self.config.destination_region)

    def __create_s3_clients(self):
        # Create S3 clients for source and destination buckets
        self.source_client_s3 = self.source_session.client('s3', region_name=self.config.source_region)
        self.destination_client_s3 = self.destination_session.client('s3', region_name=self.config.destination_region)

    def __copy_objects(self):
        try:
            paginator = self.source_client_s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.config.source_bucket, Prefix=self.config.prefix):
                for obj in page.get("Contents", []):
                    source_key = obj['Key']
                    if not self.config.dry_run:
                        copy_source = {'Bucket': self.config.source_bucket, 'Key': source_key}
                        self.destination_client_s3.copy(copy_source, self.config.destination_bucket, source_key)
                    print(f"Copied object: {source_key} from {self.config.source_bucket} to {self.config.destination_bucket}")
        except Exception as e:
            print(f"Error copying objects from {self.config.source_bucket} to {self.config.destination_bucket}: {e}")

    def copy(self):
        if self.config.verify_only:
            print("Verify only mode enabled. Skipping copy operation.")
            return
        
        print(f"Copying from {self.config.source_bucket} to {self.config.destination_bucket} using profiles {self.config.source_profile} and {self.config.destination_profile}. Dry run: {self.config.dry_run}, Verify only: {self.config.verify_only}")

        self.__init_sessions()
        self.__create_s3_clients()
        self.__copy_objects()
