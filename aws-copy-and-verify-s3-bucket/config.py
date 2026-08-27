class ToolConfig:
    def __init__(self, source_bucket, destination_bucket, source_profile, destination_profile, source_region, destination_region, prefix="", dry_run=False, verify_only=False):
        self.source_bucket = source_bucket
        self.destination_bucket = destination_bucket
        self.source_profile = source_profile
        self.destination_profile = destination_profile
        self.source_region = source_region
        self.destination_region = destination_region
        self.prefix = prefix
        self.dry_run = dry_run
        self.verify_only = verify_only
