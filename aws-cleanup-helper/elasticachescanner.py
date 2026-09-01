from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class ElastiCacheScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.clusters_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("elasticache")

    def __list_clusters(self, region: str) -> list[dict[str, Any]]:
        clusters = []
        try:
            elasticache = self.session.client("elasticache", region_name=region)
            paginator = elasticache.get_paginator("describe_cache_clusters")
            for page in paginator.paginate():
                for cluster in page.get("CacheClusters", []):
                    clusters.append({
                        "CacheClusterId": cluster["CacheClusterId"],
                        "Region": region,
                        "Status": cluster.get("CacheClusterStatus"),
                        "Engine": cluster.get("Engine")
                    })
        except ClientError as e:
            clusters = []
        return clusters

    def scan(self) -> None:
        self.clusters_info = []
        for region in self.__get_regions():
            self.clusters_info.extend(self.__list_clusters(region))

    def verbose_scan(self) -> None:
        for cluster_info in self.clusters_info:
            print(f"Cache Cluster: {cluster_info['CacheClusterId']} ({cluster_info['Engine']}), Region: {cluster_info['Region']}, Status: {cluster_info['Status']}")

    def __delete_cluster(self, region: str, cluster_info: dict[str, Any]) -> None:
        cluster_id = cluster_info["CacheClusterId"]
        try:
            elasticache = self.session.client("elasticache", region_name=region)
            if self.config.dry_run:
                snapshot_note = "no final snapshot" if self.config.skip_final_snapshot else "with a final snapshot"
                print(f"Dry run: would delete cache cluster {cluster_id} ({snapshot_note})")
                return
            # Only Redis clusters support final snapshots; Memcached does not.
            if not self.config.skip_final_snapshot and cluster_info["Engine"] == "redis":
                snapshot_id = f"{cluster_id}-final-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
                elasticache.delete_cache_cluster(CacheClusterId=cluster_id, FinalSnapshotIdentifier=snapshot_id)
            else:
                elasticache.delete_cache_cluster(CacheClusterId=cluster_id)
        except ClientError as e:
            pass

    def delete(self) -> None:
        for cluster_info in self.clusters_info:
            self.__delete_cluster(cluster_info["Region"], cluster_info)
