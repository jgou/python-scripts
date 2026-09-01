from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

# Memcached is the only ElastiCache engine that doesn't support snapshots; it also can't
# be part of a replication group, so any replication group is guaranteed to support them.
SNAPSHOT_UNSUPPORTED_ENGINES = {"memcached"}

class ElastiCacheScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.clusters_info: list[dict[str, Any]] = []
        self.replication_groups_info: list[dict[str, Any]] = []

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
                    # Clusters that belong to a replication group can't be deleted via
                    # delete_cache_cluster; they're handled as part of their replication group.
                    if cluster.get("ReplicationGroupId"):
                        continue
                    clusters.append({
                        "CacheClusterId": cluster["CacheClusterId"],
                        "Region": region,
                        "Status": cluster.get("CacheClusterStatus"),
                        "Engine": cluster.get("Engine")
                    })
        except ClientError as e:
            print(f"Could not list ElastiCache clusters in {region}: {e}")
            clusters = []
        return clusters

    def __list_replication_groups(self, region: str) -> list[dict[str, Any]]:
        groups = []
        try:
            elasticache = self.session.client("elasticache", region_name=region)
            paginator = elasticache.get_paginator("describe_replication_groups")
            for page in paginator.paginate():
                for group in page.get("ReplicationGroups", []):
                    groups.append({
                        "ReplicationGroupId": group["ReplicationGroupId"],
                        "Region": region,
                        "Status": group.get("Status"),
                        "Engine": group.get("Engine")
                    })
        except ClientError as e:
            print(f"Could not list ElastiCache replication groups in {region}: {e}")
            groups = []
        return groups

    def scan(self) -> None:
        self.clusters_info = []
        self.replication_groups_info = []
        for region in self.__get_regions():
            self.clusters_info.extend(self.__list_clusters(region))
            self.replication_groups_info.extend(self.__list_replication_groups(region))

    def verbose_scan(self) -> None:
        for cluster_info in self.clusters_info:
            print(f"Cache Cluster: {cluster_info['CacheClusterId']} ({cluster_info['Engine']}), Region: {cluster_info['Region']}, Status: {cluster_info['Status']}")
        for group_info in self.replication_groups_info:
            print(f"Replication Group: {group_info['ReplicationGroupId']} ({group_info['Engine']}), Region: {group_info['Region']}, Status: {group_info['Status']}")

    def __delete_cluster(self, region: str, cluster_info: dict[str, Any]) -> None:
        cluster_id = cluster_info["CacheClusterId"]
        supports_snapshot = cluster_info["Engine"] not in SNAPSHOT_UNSUPPORTED_ENGINES
        try:
            elasticache = self.session.client("elasticache", region_name=region)
            if self.config.dry_run:
                snapshot_note = "no final snapshot" if self.config.skip_final_snapshot or not supports_snapshot else "with a final snapshot"
                print(f"Dry run: would delete cache cluster {cluster_id} ({snapshot_note})")
                return
            if not self.config.skip_final_snapshot and supports_snapshot:
                snapshot_id = f"{cluster_id}-final-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
                elasticache.delete_cache_cluster(CacheClusterId=cluster_id, FinalSnapshotIdentifier=snapshot_id)
            else:
                elasticache.delete_cache_cluster(CacheClusterId=cluster_id)
        except ClientError as e:
            print(f"Could not delete cache cluster {cluster_id}: {e}")

    def __delete_replication_group(self, region: str, group_info: dict[str, Any]) -> None:
        group_id = group_info["ReplicationGroupId"]
        try:
            elasticache = self.session.client("elasticache", region_name=region)
            if self.config.dry_run:
                snapshot_note = "no final snapshot" if self.config.skip_final_snapshot else "with a final snapshot"
                print(f"Dry run: would delete replication group {group_id} ({snapshot_note})")
                return
            if self.config.skip_final_snapshot:
                elasticache.delete_replication_group(ReplicationGroupId=group_id)
            else:
                snapshot_id = f"{group_id}-final-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
                elasticache.delete_replication_group(ReplicationGroupId=group_id, FinalSnapshotIdentifier=snapshot_id)
        except ClientError as e:
            print(f"Could not delete replication group {group_id}: {e}")

    def delete(self) -> None:
        for cluster_info in self.clusters_info:
            self.__delete_cluster(cluster_info["Region"], cluster_info)
        for group_info in self.replication_groups_info:
            self.__delete_replication_group(group_info["Region"], group_info)
