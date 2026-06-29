from __future__ import annotations

from aws_cdk import CfnOutput, Stack, aws_certificatemanager as acm, aws_route53 as route53
from constructs import Construct


class CertificateStack(Stack):
    """ACM certificate in us-east-1 (required for CloudFront)."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        domain_name: str,
        hosted_zone_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        hosted_zone = route53.HostedZone.from_lookup(
            self,
            "HostedZone",
            domain_name=hosted_zone_name,
        )

        self.certificate = acm.Certificate(
            self,
            "Certificate",
            domain_name=domain_name,
            validation=acm.CertificateValidation.from_dns(hosted_zone),
        )

        self.certificate_arn = self.certificate.certificate_arn

        CfnOutput(self, "CertificateArn", value=self.certificate.certificate_arn)
