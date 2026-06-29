from __future__ import annotations

import os
from pathlib import Path

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_certificatemanager as acm,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_ecr as ecr,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_s3 as s3,
)
from constructs import Construct


class NewsScreenshotsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        domain_name: str,
        snapshots_path: str,
        certificate: acm.ICertificate,
        github_repository: str = "",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        snapshots_prefix = snapshots_path.strip("/")
        public_base_url = f"https://{domain_name}/{snapshots_prefix}"

        bucket = s3.Bucket(
            self,
            "SnapshotsBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
        )

        repository = ecr.Repository(
            self,
            "ScreenshotRepository",
            repository_name="news-screenshots",
            removal_policy=RemovalPolicy.RETAIN,
            empty_on_delete=False,
        )

        project_root = Path(__file__).resolve().parents[2]
        image_tag = os.environ.get("IMAGE_TAG")
        if image_tag:
            function_code = lambda_.DockerImageCode.from_ecr(
                repository,
                tag_or_digest=image_tag,
            )
        else:
            function_code = lambda_.DockerImageCode.from_image_asset(
                str(project_root),
                file="Dockerfile",
            )

        screenshot_function = lambda_.DockerImageFunction(
            self,
            "ScreenshotFunction",
            function_name="news-screenshots",
            code=function_code,
            timeout=Duration.minutes(5),
            memory_size=2048,
            architecture=lambda_.Architecture.X86_64,
            environment={
                "S3_BUCKET": bucket.bucket_name,
                "S3_PREFIX": f"{snapshots_prefix}/",
                "PUBLIC_BASE_URL": public_base_url,
                "CONFIG_PATH": "/var/task/config.yaml",
            },
        )
        bucket.grant_read_write(screenshot_function)

        schedule_minutes = int(os.environ.get("SCHEDULE_RATE_MINUTES", "5"))
        rule = events.Rule(
            self,
            "ScreenshotSchedule",
            schedule=events.Schedule.rate(Duration.minutes(schedule_minutes)),
        )
        rule.add_target(targets.LambdaFunction(screenshot_function))

        hosted_zone = route53.HostedZone.from_lookup(
            self,
            "HostedZone",
            domain_name=domain_name,
        )

        origin_access_control = cloudfront.S3OriginAccessControl(
            self,
            "SnapshotsOAC",
            signing=cloudfront.Signing.SIGV4_ALWAYS,
        )

        distribution = cloudfront.Distribution(
            self,
            "SnapshotsDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    bucket,
                    origin_access_control=origin_access_control,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            domain_names=[domain_name],
            certificate=certificate,
            minimum_protocol_version=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
            comment=f"Public snapshots for {domain_name}",
        )

        bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudFrontServicePrincipalRead",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
                actions=["s3:GetObject"],
                resources=[bucket.arn_for_objects("*")],
                conditions={
                    "StringEquals": {
                        "AWS:SourceArn": (
                            f"arn:aws:cloudfront::{self.account}:distribution/"
                            f"{distribution.distribution_id}"
                        ),
                    },
                },
            )
        )

        route53.ARecord(
            self,
            "DomainAliasRecord",
            zone=hosted_zone,
            record_name=domain_name,
            target=route53.RecordTarget.from_alias(
                route53_targets.CloudFrontTarget(distribution)
            ),
        )

        if github_repository:
            self._create_github_deploy_role(
                github_repository=github_repository,
                repository=repository,
                screenshot_function=screenshot_function,
            )

        CfnOutput(self, "BucketName", value=bucket.bucket_name)
        CfnOutput(self, "RepositoryUri", value=repository.repository_uri)
        CfnOutput(self, "FunctionName", value=screenshot_function.function_name)
        CfnOutput(
            self,
            "DistributionDomainName",
            value=distribution.distribution_domain_name,
        )
        CfnOutput(self, "SnapshotsBaseUrl", value=public_base_url)

    def _create_github_deploy_role(
        self,
        *,
        github_repository: str,
        repository: ecr.Repository,
        screenshot_function: lambda_.DockerImageFunction,
    ) -> None:
        provider = iam.OpenIdConnectProvider(
            self,
            "GitHubOidcProvider",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
            thumbprints=["6938fd4d98bab03faadb97b34396831e3780aea1"],
        )

        deploy_role = iam.Role(
            self,
            "GitHubDeployRole",
            role_name="news-screenshots-github-deploy",
            assumed_by=iam.FederatedPrincipal(
                provider.open_id_connect_provider_arn,
                {
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                    },
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": (
                            f"repo:{github_repository}:*"
                        ),
                    },
                },
                "sts:AssumeRoleWithWebIdentity",
            ),
            description="Allows GitHub Actions to build and deploy news-screenshots",
        )

        repository.grant_pull_push(deploy_role)
        screenshot_function.grant_invoke(deploy_role)
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "cloudformation:*",
                    "iam:*",
                    "lambda:*",
                    "s3:*",
                    "ecr:*",
                    "events:*",
                    "cloudfront:*",
                    "route53:*",
                    "acm:*",
                    "sts:GetCallerIdentity",
                ],
                resources=["*"],
            )
        )

        CfnOutput(self, "GitHubDeployRoleArn", value=deploy_role.role_arn)
