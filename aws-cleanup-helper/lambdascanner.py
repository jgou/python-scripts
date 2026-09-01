from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import ToolConfig

class LambdaScanner:
    def __init__(self, session: boto3.Session, config: ToolConfig) -> None:
        self.session: boto3.Session = session
        self.config: ToolConfig = config
        self.functions_info: list[dict[str, Any]] = []

    def __get_regions(self) -> list[str]:
        if self.config.regions:
            return self.config.regions
        return self.session.get_available_regions("lambda")

    def __list_functions(self, region: str) -> list[dict[str, Any]]:
        functions = []
        try:
            lambda_client = self.session.client("lambda", region_name=region)
            paginator = lambda_client.get_paginator("list_functions")
            for page in paginator.paginate():
                for function in page.get("Functions", []):
                    functions.append({
                        "FunctionName": function["FunctionName"],
                        "Region": region,
                        "Runtime": function.get("Runtime"),
                        "LastModified": function.get("LastModified")
                    })
        except ClientError as e:
            print(f"Could not list Lambda functions in {region}: {e}")
            functions = []
        return functions

    def scan(self) -> None:
        self.functions_info = []
        for region in self.__get_regions():
            self.functions_info.extend(self.__list_functions(region))

    def verbose_scan(self) -> None:
        for function_info in self.functions_info:
            print(f"Lambda Function: {function_info['FunctionName']} ({function_info['Runtime']}), Region: {function_info['Region']}, Last Modified: {function_info['LastModified']}")

    def __delete_function(self, region: str, function_name: str) -> None:
        try:
            lambda_client = self.session.client("lambda", region_name=region)
            if self.config.dry_run:
                print(f"Dry run: would delete Lambda function {function_name}")
                return
            lambda_client.delete_function(FunctionName=function_name)
        except ClientError as e:
            print(f"Could not delete Lambda function {function_name}: {e}")

    def delete(self) -> None:
        for function_info in self.functions_info:
            self.__delete_function(function_info["Region"], function_info["FunctionName"])
