# Deployment

## Default Direction

Deploy on AWS first, but do it in a way that keeps migration possible later.

## Recommended First Cloud Shape

For the first real deployment, keep the stack practical:

- one web/API service in a container
- one background worker service
- S3 for media storage
- SQS for async jobs
- Postgres for metadata

This is enough to learn real deployment without jumping straight into an overbuilt platform.

## Suggested Rollout Order

1. local development with local storage
2. switch storage to S3
3. deploy API/web container
4. deploy worker
5. add SQS job flow
6. add CDN only if media delivery needs it

## Cost Discipline

Rules for early cost control:

- store originals once
- generate only the derivatives we actually need
- process media asynchronously
- keep the first deploy single-user oriented
- add heavier infra only after real usage

## Portability Guardrails

- use storage adapters rather than raw S3 calls across the codebase
- use queue adapters rather than direct SQS logic everywhere
- keep media processing containerized and portable
- avoid AWS naming leaking into the product/domain layer

## What We Will Not Do Early

- build a large multi-region setup
- lock the app to one cloud-only implementation
- assume autoposting is the core value before media curation is working well

