#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

: "${CDK_DEFAULT_ACCOUNT:?Set CDK_DEFAULT_ACCOUNT to your AWS account ID}"
: "${CDK_DEFAULT_REGION:=eu-north-1}"
: "${HOSTED_ZONE_NAME:=grense.land}"
: "${DOMAIN_NAME:=snapshots.grense.land}"
: "${GITHUB_REPOSITORY:=}"

echo "Bootstrapping CDK in ${CDK_DEFAULT_REGION} and us-east-1..."
cd cdk
npm ci
npm install -g aws-cdk 2>/dev/null || true

cdk bootstrap "aws://${CDK_DEFAULT_ACCOUNT}/${CDK_DEFAULT_REGION}"
cdk bootstrap "aws://${CDK_DEFAULT_ACCOUNT}/us-east-1"

export HOSTED_ZONE_NAME
export DOMAIN_NAME
export GITHUB_REPOSITORY

echo "Deploying stacks (this builds the Lambda image locally on first run)..."
cdk deploy --all --require-approval never

echo ""
echo "Deployment complete. Stack outputs:"
aws cloudformation describe-stacks \
  --stack-name NewsScreenshotsStack \
  --query "Stacks[0].Outputs" \
  --output table \
  --region "${CDK_DEFAULT_REGION}"

if [[ -n "${GITHUB_REPOSITORY}" ]]; then
  ROLE_ARN="$(aws cloudformation describe-stacks \
    --stack-name NewsScreenshotsStack \
    --query "Stacks[0].Outputs[?OutputKey=='GitHubDeployRoleArn'].OutputValue" \
    --output text \
    --region "${CDK_DEFAULT_REGION}")"
  echo ""
  echo "Add these GitHub repository secrets:"
  echo "  AWS_ACCOUNT_ID=${CDK_DEFAULT_ACCOUNT}"
  echo "  AWS_DEPLOY_ROLE_ARN=${ROLE_ARN}"
fi
