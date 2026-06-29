import * as path from "node:path";
import * as cdk from "aws-cdk-lib";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as route53Targets from "aws-cdk-lib/aws-route53-targets";
import * as s3 from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";

export interface NewsScreenshotsStackProps extends cdk.StackProps {
  domainName: string;
  hostedZoneName: string;
  certificate: acm.ICertificate;
  githubRepository?: string;
}

export class NewsScreenshotsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: NewsScreenshotsStackProps) {
    super(scope, id, props);

    const { domainName, hostedZoneName, certificate, githubRepository = "" } =
      props;
    const publicBaseUrl = `https://${domainName}`;

    const bucket = new s3.Bucket(this, "SnapshotsBucket", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      autoDeleteObjects: false,
    });

    const repository = new ecr.Repository(this, "ScreenshotRepository", {
      repositoryName: "news-screenshots",
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      emptyOnDelete: false,
    });

    const projectRoot = path.join(__dirname, "..", "..");
    const imageTag = process.env.IMAGE_TAG;
    const functionCode = imageTag
      ? lambda.DockerImageCode.fromEcr(repository, { tagOrDigest: imageTag })
      : lambda.DockerImageCode.fromImageAsset(projectRoot, {
          file: "Dockerfile",
          exclude: [
            "cdk",
            "node_modules",
            ".git",
            "output",
            ".venv",
            "playwright-report",
            "test-results",
          ],
        });

    const screenshotFunction = new lambda.DockerImageFunction(
      this,
      "ScreenshotFunction",
      {
        functionName: "news-screenshots",
        code: functionCode,
        timeout: cdk.Duration.minutes(5),
        memorySize: 2048,
        architecture: lambda.Architecture.X86_64,
        environment: {
          S3_BUCKET: bucket.bucketName,
          S3_PREFIX: "",
          PUBLIC_BASE_URL: publicBaseUrl,
          CONFIG_PATH: "/var/task/config.json",
        },
      },
    );
    bucket.grantReadWrite(screenshotFunction);

    const scheduleMinutes = Number(process.env.SCHEDULE_RATE_MINUTES ?? "5");
    const rule = new events.Rule(this, "ScreenshotSchedule", {
      schedule: events.Schedule.rate(cdk.Duration.minutes(scheduleMinutes)),
    });
    rule.addTarget(new targets.LambdaFunction(screenshotFunction));

    const hostedZone = route53.HostedZone.fromLookup(this, "HostedZone", {
      domainName: hostedZoneName,
    });

    const subdomain = domainName.endsWith(`.${hostedZoneName}`)
      ? domainName.slice(0, -(hostedZoneName.length + 1))
      : domainName;

    const originAccessControl = new cloudfront.S3OriginAccessControl(
      this,
      "SnapshotsOAC",
      {
        signing: cloudfront.Signing.SIGV4_ALWAYS,
      },
    );

    const distribution = new cloudfront.Distribution(
      this,
      "SnapshotsDistribution",
      {
        defaultBehavior: {
          origin: origins.S3BucketOrigin.withOriginAccessControl(bucket, {
            originAccessControl,
          }),
          viewerProtocolPolicy:
            cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
          cachedMethods: cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
          cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
        },
        domainNames: [domainName],
        certificate,
        minimumProtocolVersion:
          cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
        comment: `Public snapshots for ${domainName}`,
      },
    );

    bucket.addToResourcePolicy(
      new iam.PolicyStatement({
        sid: "AllowCloudFrontServicePrincipalRead",
        effect: iam.Effect.ALLOW,
        principals: [new iam.ServicePrincipal("cloudfront.amazonaws.com")],
        actions: ["s3:GetObject"],
        resources: [bucket.arnForObjects("*")],
        conditions: {
          StringEquals: {
            "AWS:SourceArn": `arn:aws:cloudfront::${this.account}:distribution/${distribution.distributionId}`,
          },
        },
      }),
    );

    new route53.ARecord(this, "DomainAliasRecord", {
      zone: hostedZone,
      recordName: subdomain,
      target: route53.RecordTarget.fromAlias(
        new route53Targets.CloudFrontTarget(distribution),
      ),
    });

    if (githubRepository) {
      this.createGithubDeployRole({
        githubRepository,
        repository,
        screenshotFunction,
      });
    }

    new cdk.CfnOutput(this, "BucketName", { value: bucket.bucketName });
    new cdk.CfnOutput(this, "RepositoryUri", {
      value: repository.repositoryUri,
    });
    new cdk.CfnOutput(this, "FunctionName", {
      value: screenshotFunction.functionName,
    });
    new cdk.CfnOutput(this, "DistributionDomainName", {
      value: distribution.distributionDomainName,
    });
    new cdk.CfnOutput(this, "SnapshotsBaseUrl", { value: publicBaseUrl });
  }

  private createGithubDeployRole({
    githubRepository,
    repository,
    screenshotFunction,
  }: {
    githubRepository: string;
    repository: ecr.Repository;
    screenshotFunction: lambda.DockerImageFunction;
  }): void {
    const provider = new iam.OpenIdConnectProvider(this, "GitHubOidcProvider", {
      url: "https://token.actions.githubusercontent.com",
      clientIds: ["sts.amazonaws.com"],
      thumbprints: ["6938fd4d98bab03faadb97b34396831e3780aea1"],
    });

    const deployRole = new iam.Role(this, "GitHubDeployRole", {
      roleName: "news-screenshots-github-deploy",
      assumedBy: new iam.FederatedPrincipal(
        provider.openIdConnectProviderArn,
        {
          StringEquals: {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          },
          StringLike: {
            "token.actions.githubusercontent.com:sub": `repo:${githubRepository}:*`,
          },
        },
        "sts:AssumeRoleWithWebIdentity",
      ),
      description: "Allows GitHub Actions to build and deploy news-screenshots",
    });

    repository.grantPullPush(deployRole);
    screenshotFunction.grantInvoke(deployRole);
    deployRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
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
        resources: ["*"],
      }),
    );

    new cdk.CfnOutput(this, "GitHubDeployRoleArn", {
      value: deployRole.roleArn,
    });
  }
}
