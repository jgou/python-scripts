import boto3

from config import ToolConfig
from s3scanner import S3Scanner
from ec2scanner import Ec2Scanner
from route53scanner import Route53Scanner
from elbscanner import ELBScanner
from rdsscanner import RDSScanner
from elasticachescanner import ElastiCacheScanner
from natgatewayscanner import NatGatewayScanner
from elasticipscanner import ElasticIPScanner
from vpcendpointscanner import VpcEndpointScanner
from vpnscanner import VpnScanner
from transitgatewayscanner import TransitGatewayScanner
from clientvpnscanner import ClientVpnScanner
from networkfirewallscanner import NetworkFirewallScanner
from cloudfrontscanner import CloudFrontScanner
from lambdascanner import LambdaScanner
from internetgatewayscanner import InternetGatewayScanner

class Scanner:
    def __init__(self, config: ToolConfig) -> None:
        self.config: ToolConfig = config

    def init_session(self) -> None:
        self.session: boto3.Session = boto3.Session(profile_name=self.config.profile) if self.config.profile else boto3.Session()
        self.__authenticate()
        self.s3_scanner: S3Scanner = S3Scanner(session=self.session, config=self.config)
        self.ec2_scanner: Ec2Scanner = Ec2Scanner(session=self.session, config=self.config)
        self.route53_scanner: Route53Scanner = Route53Scanner(session=self.session, config=self.config)
        self.elb_scanner: ELBScanner = ELBScanner(session=self.session, config=self.config)
        self.rds_scanner: RDSScanner = RDSScanner(session=self.session, config=self.config)
        self.elasticache_scanner: ElastiCacheScanner = ElastiCacheScanner(session=self.session, config=self.config)
        self.nat_gateway_scanner: NatGatewayScanner = NatGatewayScanner(session=self.session, config=self.config)
        self.eip_scanner: ElasticIPScanner = ElasticIPScanner(session=self.session, config=self.config)
        self.vpc_endpoint_scanner: VpcEndpointScanner = VpcEndpointScanner(session=self.session, config=self.config)
        self.vpn_scanner: VpnScanner = VpnScanner(session=self.session, config=self.config)
        self.transit_gateway_scanner: TransitGatewayScanner = TransitGatewayScanner(session=self.session, config=self.config)
        self.client_vpn_scanner: ClientVpnScanner = ClientVpnScanner(session=self.session, config=self.config)
        self.network_firewall_scanner: NetworkFirewallScanner = NetworkFirewallScanner(session=self.session, config=self.config)
        self.cloudfront_scanner: CloudFrontScanner = CloudFrontScanner(session=self.session, config=self.config)
        self.lambda_scanner: LambdaScanner = LambdaScanner(session=self.session, config=self.config)
        self.internet_gateway_scanner: InternetGatewayScanner = InternetGatewayScanner(session=self.session, config=self.config)

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
        if ToolConfig.Services.ELB.value in self.config.services:
            self.elb_scanner.scan()
            self.elb_scanner.verbose_scan()
        if ToolConfig.Services.RDS.value in self.config.services:
            self.rds_scanner.scan()
            self.rds_scanner.verbose_scan()
        if ToolConfig.Services.ELASTICACHE.value in self.config.services:
            self.elasticache_scanner.scan()
            self.elasticache_scanner.verbose_scan()
        if ToolConfig.Services.NAT_GATEWAY.value in self.config.services:
            self.nat_gateway_scanner.scan()
            self.nat_gateway_scanner.verbose_scan()
        if ToolConfig.Services.EIP.value in self.config.services:
            self.eip_scanner.scan()
            self.eip_scanner.verbose_scan()
        if ToolConfig.Services.VPC_ENDPOINT.value in self.config.services:
            self.vpc_endpoint_scanner.scan()
            self.vpc_endpoint_scanner.verbose_scan()
        if ToolConfig.Services.VPN.value in self.config.services:
            self.vpn_scanner.scan()
            self.vpn_scanner.verbose_scan()
        if ToolConfig.Services.TRANSIT_GATEWAY.value in self.config.services:
            self.transit_gateway_scanner.scan()
            self.transit_gateway_scanner.verbose_scan()
        if ToolConfig.Services.CLIENT_VPN.value in self.config.services:
            self.client_vpn_scanner.scan()
            self.client_vpn_scanner.verbose_scan()
        if ToolConfig.Services.NETWORK_FIREWALL.value in self.config.services:
            self.network_firewall_scanner.scan()
            self.network_firewall_scanner.verbose_scan()
        if ToolConfig.Services.CLOUDFRONT.value in self.config.services:
            self.cloudfront_scanner.scan()
            self.cloudfront_scanner.verbose_scan()
        if ToolConfig.Services.LAMBDA.value in self.config.services:
            self.lambda_scanner.scan()
            self.lambda_scanner.verbose_scan()
        if ToolConfig.Services.INTERNET_GATEWAY.value in self.config.services:
            self.internet_gateway_scanner.scan()
            self.internet_gateway_scanner.verbose_scan()

    def delete(self) -> None:
        if ToolConfig.Services.S3.value in self.config.services:
            self.s3_scanner.delete()
        if ToolConfig.Services.EC2.value in self.config.services:
            self.ec2_scanner.delete()
        if ToolConfig.Services.ROUTE53.value in self.config.services:
            self.route53_scanner.delete()
        if ToolConfig.Services.ELB.value in self.config.services:
            self.elb_scanner.delete()
        if ToolConfig.Services.RDS.value in self.config.services:
            self.rds_scanner.delete()
        if ToolConfig.Services.ELASTICACHE.value in self.config.services:
            self.elasticache_scanner.delete()
        # A Lambda@Edge function still associated with a CloudFront distribution can't be
        # deleted, so distributions are removed first.
        if ToolConfig.Services.CLOUDFRONT.value in self.config.services:
            self.cloudfront_scanner.delete()
        if ToolConfig.Services.LAMBDA.value in self.config.services:
            self.lambda_scanner.delete()
        if ToolConfig.Services.CLIENT_VPN.value in self.config.services:
            self.client_vpn_scanner.delete()
        if ToolConfig.Services.VPN.value in self.config.services:
            self.vpn_scanner.delete()
        if ToolConfig.Services.TRANSIT_GATEWAY.value in self.config.services:
            self.transit_gateway_scanner.delete()
        if ToolConfig.Services.VPC_ENDPOINT.value in self.config.services:
            self.vpc_endpoint_scanner.delete()
        if ToolConfig.Services.NETWORK_FIREWALL.value in self.config.services:
            self.network_firewall_scanner.delete()
        # NAT Gateways release their Elastic IP association on deletion, so delete them
        # before releasing Elastic IPs to avoid a transient disassociation conflict.
        if ToolConfig.Services.NAT_GATEWAY.value in self.config.services:
            self.nat_gateway_scanner.delete()
        if ToolConfig.Services.EIP.value in self.config.services:
            self.eip_scanner.delete()
        if ToolConfig.Services.INTERNET_GATEWAY.value in self.config.services:
            self.internet_gateway_scanner.delete()

    