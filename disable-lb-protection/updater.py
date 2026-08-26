import boto3
from config import ToolConfig


class LoadBalancerUpdater:

  def __init__(self, config: ToolConfig):
    self.config = config

  def __init_session(self):
    self.session = boto3.Session(profile_name=self.config.profile, region_name=self.config.region)

  def __get_load_balancers(self):
    elbv2 = self.session.client('elbv2', region_name=self.config.region)
    try:
      paginator = elbv2.get_paginator('describe_load_balancers')
      load_balancers = []
      for page in paginator.paginate():
        load_balancers.extend(page['LoadBalancers'])
    except (boto3.exceptions.Boto3Error, boto3.exceptions.ClientError) as e:
      print(f"  ! Could not list load balancers in {self.config.region}: {e}")
      load_balancers = []
    return load_balancers

  def __filter_load_balancers(self, load_balancers):
    filtered = [lb for lb in load_balancers if self.config.search_criteria in lb['LoadBalancerName']]
    if not filtered:
      print(f"  ! No load balancers found matching criteria '{self.config.search_criteria}' in {self.config.region}.")
    return filtered

  def __disable_protection(self, load_balancer_arn):
    elbv2 = self.session.client('elbv2', region_name=self.config.region)
    try:
      if not self.config.dry_run:
        elbv2.modify_load_balancer_attributes(
          LoadBalancerArn=load_balancer_arn,
          Attributes=[{'Key': 'deletion_protection.enabled', 'Value': 'false'}]
        )
      print(f"  {'dry_run' if self.config.dry_run else ''} - Disabled deletion protection for load balancer ARN: {load_balancer_arn}")
    except (boto3.exceptions.Boto3Error, boto3.exceptions.ClientError) as e:
      print(f"  ! Could not disable deletion protection for load balancer ARN {load_balancer_arn}: {e}")

  def update_load_balancer(self):
    # Placeholder for the actual logic to disable load balancer protection
    print(f"Disabling load balancer protection in region {self.config.region} with profile {self.config.profile} using search criteria '{self.config.search_criteria}'. Dry run: {self.config.dry_run}")
    self.__init_session()
    filtered_load_balancers = self.__filter_load_balancers(self.__get_load_balancers())
    for lb in filtered_load_balancers:
      self.__disable_protection(lb['LoadBalancerArn'])
