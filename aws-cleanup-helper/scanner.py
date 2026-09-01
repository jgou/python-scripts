import boto3

from config import ToolConfig
from s3scanner import S3Scanner
from ec2scanner import Ec2Scanner
from route53scanner import Route53Scanner

class Scanner:
    def __init__(self, config: ToolConfig) -> None:
        self.config: ToolConfig = config

    def init_session(self) -> None:
        self.session: boto3.Session = boto3.Session(profile_name=self.config.profile) if self.config.profile else boto3.Session()
        self.__authenticate()
        self.s3_scanner: S3Scanner = S3Scanner(session=self.session, config=self.config)
        self.ec2_scanner: Ec2Scanner = Ec2Scanner(session=self.session, config=self.config)
        self.route53_scanner: Route53Scanner = Route53Scanner(session=self.session, config=self.config)

    def __authenticate(self) -> None:
        try:
            sts = self.session.client("sts")
            sts.get_caller_identity()
            print(f"Authenticated as {sts.get_caller_identity()['Arn']}")
        except Exception as e:
            print(f"Authentication failed: {e}")

    def scan(self) -> None:
        if ToolConfig.Services.S3.value in self.config.services:
            self.s3_scanner.scan()
            self.s3_scanner.verbose_scan()
        if ToolConfig.Services.EC2.value in self.config.services:
            self.ec2_scanner.scan()
            self.ec2_scanner.verbose_scan()
        if ToolConfig.Services.ROUTE53.value in self.config.services:
            self.route53_scanner.scan()
            self.route53_scanner.verbose_scan()

    def delete(self) -> None:
        if ToolConfig.Services.S3.value in self.config.services:
            self.s3_scanner.delete()
        if ToolConfig.Services.EC2.value in self.config.services:
            self.ec2_scanner.delete()
        if ToolConfig.Services.ROUTE53.value in self.config.services:
            self.route53_scanner.delete()

    