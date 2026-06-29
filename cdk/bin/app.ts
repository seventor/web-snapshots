#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { CertificateStack } from "../lib/certificate-stack";
import { NewsScreenshotsStack } from "../lib/news-screenshots-stack";

const app = new cdk.App();

const hostedZoneName = process.env.HOSTED_ZONE_NAME ?? "grense.land";
const domainName = process.env.DOMAIN_NAME ?? "snapshots.grense.land";
const account = process.env.CDK_DEFAULT_ACCOUNT;
const region = process.env.CDK_DEFAULT_REGION ?? "eu-north-1";
const githubRepository = process.env.GITHUB_REPOSITORY ?? "";

const certStack = new CertificateStack(app, "NewsScreenshotsCertificateStack", {
  domainName,
  hostedZoneName,
  crossRegionReferences: true,
  env: {
    account,
    region: "us-east-1",
  },
});

const mainStack = new NewsScreenshotsStack(app, "NewsScreenshotsStack", {
  domainName,
  hostedZoneName,
  certificate: certStack.certificate,
  githubRepository,
  crossRegionReferences: true,
  env: {
    account,
    region,
  },
});
mainStack.addDependency(certStack);
