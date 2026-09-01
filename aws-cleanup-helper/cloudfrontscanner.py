from typing import Any

import boto3
from botocore.exceptions import ClientError, WaiterError

from config import ToolConfig

class CloudFrontScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.distributions_info: list[dict[str, Any]] = []

    def __list_distributions(self) -> list[dict[str, Any]]:
        distributions = []
        try:
            cloudfront = self.session.client("cloudfront")
            paginator = cloudfront.get_paginator("list_distributions")
            for page in paginator.paginate():
                for distribution in page.get("DistributionList", {}).get("Items", []):
                    distributions.append({
                        "Id": distribution["Id"],
                        "DomainName": distribution.get("DomainName"),
                        "Status": distribution.get("Status"),
                        "Enabled": distribution.get("Enabled", False)
                    })
        except ClientError as e:
            print(f"Could not list CloudFront distributions: {e}")
            distributions = []
        return distributions

    def scan(self) -> None:
        self.distributions_info = self.__list_distributions()

    def verbose_scan(self) -> None:
        for distribution_info in self.distributions_info:
            print(f"CloudFront Distribution: {distribution_info['Id']} ({distribution_info['DomainName']}), Status: {distribution_info['Status']}, Enabled: {distribution_info['Enabled']}")

    def __delete_distribution(self, distribution_id: str) -> None:
        try:
            cloudfront = self.session.client("cloudfront")
            if self.config.dry_run:
                print(f"Dry run: would disable and delete CloudFront distribution {distribution_id}")
                return
            config_response = cloudfront.get_distribution_config(Id=distribution_id)
            distribution_config = config_response["DistributionConfig"]
            etag = config_response["ETag"]
            # A distribution must be disabled, and fully redeployed in that state, before it can be deleted.
            if distribution_config.get("Enabled"):
                distribution_config["Enabled"] = False
                update_response = cloudfront.update_distribution(
                    Id=distribution_id, DistributionConfig=distribution_config, IfMatch=etag
                )
                etag = update_response["ETag"]
                print(f"Disabled CloudFront distribution {distribution_id}; waiting for it to finish deploying before deleting (this can take a while)...")
            waiter = cloudfront.get_waiter("distribution_deployed")
            waiter.wait(Id=distribution_id)
            # The deploy may have advanced the ETag since it was last read above.
            etag = cloudfront.get_distribution(Id=distribution_id)["ETag"]
            cloudfront.delete_distribution(Id=distribution_id, IfMatch=etag)
        except (ClientError, WaiterError) as e:
            print(f"Could not delete CloudFront distribution {distribution_id}: {e}")

    def delete(self) -> None:
        for distribution_info in self.distributions_info:
            self.__delete_distribution(distribution_info["Id"])
