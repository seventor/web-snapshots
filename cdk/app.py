#!/usr/bin/env python3
import os

import aws_cdk as cdk

from stack.certificate_stack import CertificateStack
from stack.news_screenshots_stack import NewsScreenshotsStack

app = cdk.App()

domain_name = os.environ.get("DOMAIN_NAME", "grense.land")
account = os.environ.get("CDK_DEFAULT_ACCOUNT")
region = os.environ.get("CDK_DEFAULT_REGION", "eu-north-1")
github_repo = os.environ.get("GITHUB_REPOSITORY", "")

cert_stack = CertificateStack(
    app,
    "NewsScreenshotsCertificateStack",
    domain_name=domain_name,
    cross_region_references=True,
    env=cdk.Environment(account=account, region="us-east-1"),
)

main_stack = NewsScreenshotsStack(
    app,
    "NewsScreenshotsStack",
    domain_name=domain_name,
    snapshots_path=os.environ.get("SNAPSHOTS_PATH", "snapshots"),
    certificate=cert_stack.certificate,
    github_repository=github_repo,
    cross_region_references=True,
    env=cdk.Environment(account=account, region=region),
)
main_stack.add_dependency(cert_stack)

app.synth()
