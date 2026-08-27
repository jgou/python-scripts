import boto3

class S3BucketVerifier:

  def __init__(self, config):
    self.config = config
    self.source_bucket = config.source_bucket
    self.destination_bucket = config.destination_bucket
    self.source_objects = {}
    self.destination_objects = {}

  def __init_sessions(self):
    # Initialize boto3 sessions for source and destination profiles
    self.source_session = boto3.Session(profile_name=self.config.source_profile, region_name=self.config.source_region)
    self.destination_session = boto3.Session(profile_name=self.config.destination_profile, region_name=self.config.destination_region)

  def __create_s3_clients(self):
    # Create S3 clients for source and destination buckets
    self.source_client_s3 = self.source_session.client('s3', region_name=self.config.source_region)
    self.destination_client_s3 = self.destination_session.client('s3', region_name=self.config.destination_region)

  @staticmethod
  def __list_objects_in_bucket(s3_client, bucket_name, prefix):
    objects = {}
    try:
      paginator = s3_client.get_paginator("list_objects_v2")
      for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get("Contents", []):
          objects[obj['Key']] = {
            'Size': obj['Size'],
            'ETag': obj['ETag']
          }
          print(f"Found object: {obj['Key']} in bucket: {bucket_name}")
    except Exception as e:
      print(f"Error listing objects in bucket {bucket_name}: {e}")
    return objects

  def __get_missing_in_destination(self):
    source_keys = set(self.source_objects.keys())
    destination_keys = set(self.destination_objects.keys())
    return source_keys - destination_keys

  def __get_extra_in_destination(self):
    source_keys = set(self.source_objects.keys())
    destination_keys = set(self.destination_objects.keys())
    return destination_keys - source_keys

  def __get_common_keys(self):
    source_keys = set(self.source_objects.keys())
    destination_keys = set(self.destination_objects.keys())
    return source_keys & destination_keys

  def __get_size_mismatches(self, common_keys):
    size_mismatches = []
    for key in sorted(common_keys):
      source_obj = self.source_objects[key]
      destination_obj = self.destination_objects[key]
      if source_obj['Size'] != destination_obj['Size']:
        size_mismatches.append(key)
    return size_mismatches

  def __get_etag_mismatches(self, common_keys):
    etag_mismatches = []
    for key in sorted(common_keys):
      source_obj = self.source_objects[key]
      destination_obj = self.destination_objects[key]
      if source_obj['ETag'] != destination_obj['ETag']:
        etag_mismatches.append(key)
    return etag_mismatches

  def verify(self):
    if self.config.dry_run:
      print("Dry run mode enabled. Skipping verification.")
      return VerificationResults([], [], [], [])

    print(f"Starting verification after copying {self.config.source_bucket} to {self.config.destination_bucket} using profiles {self.config.source_profile} and {self.config.destination_profile}.")

    self.__init_sessions()
    self.__create_s3_clients()

    self.source_objects = self.__list_objects_in_bucket(self.source_client_s3, self.source_bucket, self.config.prefix)
    self.destination_objects = self.__list_objects_in_bucket(self.destination_client_s3, self.destination_bucket, self.config.prefix)

    missing_in_destination = self.__get_missing_in_destination()
    extra_in_destination = self.__get_extra_in_destination()
    common_keys = self.__get_common_keys()
    size_mismatches = self.__get_size_mismatches(common_keys)
    etag_mismatches = self.__get_etag_mismatches(common_keys)

    return VerificationResults(
      missing_in_destination=missing_in_destination,
      extra_in_destination=extra_in_destination,
      size_mismatches=size_mismatches,
      etag_mismatches=etag_mismatches
    )


class VerificationResults:

  def __init__(self, missing_in_destination, extra_in_destination, size_mismatches, etag_mismatches):
    self.missing_in_destination = missing_in_destination
    self.extra_in_destination = extra_in_destination
    self.size_mismatches = size_mismatches
    self.etag_mismatches = etag_mismatches

  def __is_empty(self):
    return len(self.missing_in_destination) == 0 and len(self.extra_in_destination) == 0 and len(self.size_mismatches) == 0 and len(self.etag_mismatches) == 0

  def is_successful(self):
    return not (self.missing_in_destination or self.extra_in_destination or self.size_mismatches or self.etag_mismatches)

  def report(self):
    if self.__is_empty():
      print("Verification completed successfully. No discrepancies found.")
      return
    
    print("\nVerification Report:")
    print("--------------------")
    if self.missing_in_destination:
      print(f"Missing in destination: {len(self.missing_in_destination)}")
      for key in sorted(self.missing_in_destination):
        print(f"  - {key}")
    else:
      print("No missing objects in destination.")

    if self.extra_in_destination:
      print(f"\nExtra in destination: {len(self.extra_in_destination)}")
      for key in sorted(self.extra_in_destination):
        print(f"  - {key}")
    else:
      print("\nNo extra objects in destination.")

    if self.size_mismatches:
      print(f"\nSize mismatches: {len(self.size_mismatches)}")
      for key in sorted(self.size_mismatches):
        print(f"  - {key}")
    else:
      print("\nNo size mismatches.")

    if self.etag_mismatches:
      print(f"\nETag mismatches: {len(self.etag_mismatches)}")
      for key in sorted(self.etag_mismatches):
        print(f"  - {key}")
    else:
      print("\nNo ETag mismatches.")