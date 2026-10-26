---
id: SE340-L04
course: SE340
title: "CI/CD and Infrastructure as Code"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [ENG401-S06]
prev: SE340-L03
next: null
---



# SE340 — Linux, Cloud Infrastructure, and Delivery

## Lecture 04: CI/CD and Infrastructure as Code

*How a Git commit becomes a production system—and why a perfectly green deployment pipeline can still destroy your afternoon.*

---

## 1. The Deployment That Passed Every Test

It's Thursday afternoon. Your team has finished implementing corporate billing for a hotel-booking SaaS.

The feature introduces a new `payment_terms` column in PostgreSQL. Ordinary customers must pay immediately, while approved corporate customers may receive thirty-day payment terms.

The code passes its unit tests. Integration tests succeed against a freshly created database. The Docker image builds correctly, security checks find nothing suspicious, and the deployment pipeline completes without errors.

GitHub Actions displays a reassuring green checkmark.

Five minutes later, production begins failing.

The application logs reveal:

```text
QueryFailedError:
column reservations.payment_terms does not exist
```

Someone forgot to run the database migration before deploying the new application version.

The team quickly executes the migration, and the errors disappear.

Problem solved?

Not quite.

The migration also introduced a new database constraint requiring every reservation to have a value for `payment_terms`. The new application supplies that value, but several instances of the previous application version are still running during the rolling deployment.

Those older instances continue inserting reservations without the new field.

PostgreSQL rejects their inserts.

Meanwhile, a background worker deployed separately still uses the old database model. It begins failing too.

The team rolls the API back to its previous image, hoping to restore normal operations. But the previous application version isn't compatible with the database's new constraint either.

What began as a routine release has become an incident involving three application versions, a shared database, and an increasingly nervous engineering team.

The pipeline performed its configured steps correctly. The tests passed. The new container started successfully.

Yet the overall deployment was unsafe.

**A successful build proves that an artifact was constructed. A successful deployment proves that deployment machinery completed its work. Neither proves that the resulting production system is correct.**

This distinction is the foundation of modern release engineering.

---

## 2. The Journey From Source Code to Production

Let's first separate several concepts that engineers frequently collapse into the single phrase *CI/CD*.

A production release involves a chain of transformations:

```text
Source Code
     │
     ▼
Version Control
     │
     ▼
Build and Tests
     │
     ▼
Versioned Artifact
     │
     ▼
Artifact Registry
     │
     ▼
Deployment
     │
     ▼
Running Application
     │
     ▼
Production Verification
```

Each step answers a different question.

Version control establishes which source changes exist and how they relate to previous revisions.

The build transforms source code and dependencies into an executable or deployable artifact.

Testing provides evidence about selected aspects of correctness.

An artifact registry stores the thing that will actually be deployed.

Deployment changes the running environment.

Production verification determines whether the deployed system behaves acceptably with real configuration, dependencies, and workloads.

A pipeline can automate this journey, but automation does not make the stages interchangeable.

### Continuous Integration

**Continuous Integration**, or CI, is the practice of integrating changes into a shared codebase frequently and validating those changes automatically.

A typical CI pipeline might:

1. Install dependencies.
2. Check code formatting and static analysis.
3. Compile TypeScript.
4. Run automated tests.
5. Build an application artifact.

The objective is rapid detection of problems introduced through code integration.

If ten developers work independently for two months before combining their changes, integration becomes a major event. Frequent integration reduces the accumulated uncertainty.

CI is therefore partly a technical mechanism and partly a collaboration practice.

A GitHub Actions workflow that runs tests on pull requests is useful, but it does not automatically establish healthy continuous integration if the team maintains long-lived branches that diverge substantially.

### Continuous Delivery

Continuous delivery aims to keep the software in a state where a production deployment can be performed safely and predictably.

The build and verification process produces a release candidate that can be promoted into production.

A human approval step may still exist.

For example:

```text
Commit
   │
   ▼
Automated Verification
   │
   ▼
Deploy to Staging
   │
   ▼
Release Approval
   │
   ▼
Deploy to Production
```

The important property is that deploying does not require an improvised sequence of manual engineering activities.

### Continuous Deployment

Continuous deployment goes one step further: changes passing the required automated gates are automatically released to production.

This can be highly effective for teams with strong testing, deployment, monitoring, and rollback capabilities.

But it is not automatically superior to continuous delivery.

A financial platform, a small team operating a critical legacy system, and a consumer application shipping minor interface improvements may reasonably choose different approval policies.

The engineering objective is reliable delivery of useful changes, not maximizing the number of automated releases for its own sake.

---

## 3. The Artifact: What Exactly Are We Deploying?

Imagine your pipeline runs:

```bash
npm ci
npm run build
npm test
```

Everything succeeds.

The next job connects to production, checks out the repository again, installs dependencies again, rebuilds the application, and launches it.

What's wrong with that?

Potentially, production is not executing the same artifact that passed verification.

The second build may encounter changed external dependencies, different environment settings, native compilation differences, or modified build tooling.

Even with a lockfile, builds are not necessarily bit-for-bit reproducible across different environments.

### Build once, promote the artifact

A stronger model separates artifact creation from environment deployment.

```text
               Git Commit
                   │
                   ▼
            Verified Build
                   │
                   ▼
            Image Digest X
                   │
           ┌───────┴───────┐
           ▼               ▼
        Staging         Production
           │               │
           └── Same Image ─┘
```

The application image should be constructed once and then deployed to the required environments without rebuilding it.

Environment-specific configuration is supplied separately.

The central property is **artifact identity**.

### Tags versus digests

Consider a Docker image:

```text
hotel-api:latest
```

The tag `latest` is mutable. Someone can publish another image under the same name.

Even a version-like tag such as:

```text
hotel-api:v2.4.1
```

may be mutable unless repository policies prevent replacement.

Container registries also identify image manifests using cryptographic digests:

```text
hotel-api@sha256:abc123...
```

The digest references specific image content.

A production deployment recorded by digest is easier to audit and reproduce because the reference identifies the artifact rather than relying on a mutable label.

Tags remain useful for humans. Digests are stronger identifiers for deployment automation.

### Reproducible builds versus immutable artifacts

These are related but distinct goals.

A **reproducible build** aims to produce the same artifact from the same inputs under controlled conditions.

An **immutable artifact** is a produced artifact whose identity and contents are preserved during promotion.

Building once and promoting by digest reduces the need to rely on exact reproducibility between staging and production.

However, build reproducibility remains valuable for debugging, supply-chain verification, and disaster recovery.

An artifact should also carry useful provenance: which Git commit produced it, which workflow ran, and which dependencies and build tools were involved.

This creates a traceable relationship between source code and production execution.

---

## 4. The Build Is a Dependency Graph

A modern application build is not one magical command.

It is a collection of tasks with dependencies.

For example:

```text
            Source Commit
                  │
         ┌────────┴─────────┐
         ▼                  ▼
      Typecheck         Unit Tests
         │                  │
         └────────┬─────────┘
                  ▼
             Build Image
                  │
                  ▼
           Publish Artifact
                  │
                  ▼
              Deployment
```

Independent checks can often execute in parallel, reducing feedback time.

But tasks that produce or consume the same artifacts must be ordered correctly.

This resembles the dependency graphs we've already encountered in compilers, build systems, and distributed workflows.

### Dependency management

For Node.js projects, committing `package-lock.json` and using `npm ci` in automated environments establishes a controlled dependency resolution process.

```bash
npm ci
```

The command expects the lockfile to agree with the package manifest and does not update the lockfile as a normal installation might.

However, dependency versions aren't the entire build environment.

The Node.js version, operating-system libraries, architecture, environment variables, code-generation tools, and native dependencies may also influence output.

For example, a package containing native binaries may behave differently when built for ARM64 versus AMD64.

A Docker-based build environment can reduce these differences, although the base image and build tooling must still be controlled.

### Build caching

CI systems often cache package downloads or intermediate build results.

This can dramatically reduce pipeline execution time.

But caches should be treated as optimization inputs, not authoritative artifacts.

A cache key that ignores relevant dependency changes can produce stale or inconsistent outputs.

Security also matters: caches restored from less-trusted workflows should not be allowed to compromise privileged release jobs.

**A correct build must not depend on a lucky cache hit.**

---

## 5. A Realistic GitHub Actions Pipeline

Let's construct a simplified release workflow for a Node.js API deployed to AWS ECS/Fargate.

The application uses:

- TypeScript and Node.js.
- Docker for packaging.
- Amazon ECR for container images.
- ECS/Fargate for execution.
- PostgreSQL on RDS.
- GitHub Actions for automation.

The repository contains:

```text
repository/
├── src/
├── tests/
├── Dockerfile
├── package.json
├── package-lock.json
├── infra/
│   └── ecs-task-definition.json
└── .github/
    └── workflows/
        └── release.yml
```

The workflow has three conceptual jobs:

```text
VERIFY
   │
   ▼
PUBLISH IMAGE
   │
   ▼
DEPLOY
```

Here is a practical illustrative implementation.

```yaml
name: API Release

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  verify:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "24"
          cache: npm

      - run: npm ci
      - run: npm run typecheck
      - run: npm test
      - run: npm run build

  publish:
    if: github.event_name == 'push'
    needs: verify
    runs-on: ubuntu-latest

    permissions:
      id-token: write
      contents: read

    outputs:
      image: ${{ steps.reference.outputs.image }}

    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.AWS_ECR_ROLE_ARN }}
          aws-region: eu-central-1

      - id: ecr
        uses: aws-actions/amazon-ecr-login@v2

      - id: build
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: >-
            ${{ steps.ecr.outputs.registry }}/${{ vars.ECR_REPOSITORY }}:${{ github.sha }}

      - id: reference
        run: |
          echo "image=${{ steps.ecr.outputs.registry }}/${{ vars.ECR_REPOSITORY }}@${{ steps.build.outputs.digest }}" >> "$GITHUB_OUTPUT"

  deploy:
    needs: publish
    runs-on: ubuntu-latest
    environment: production

    concurrency:
      group: production-api
      cancel-in-progress: false

    permissions:
      id-token: write
      contents: read

    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.AWS_DEPLOY_ROLE_ARN }}
          aws-region: eu-central-1

      - id: render
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: infra/ecs-task-definition.json
          container-name: api
          image: ${{ needs.publish.outputs.image }}

      - uses: aws-actions/amazon-ecs-deploy-task-definition@v2
        with:
          task-definition: ${{ steps.render.outputs.task-definition }}
          service: hotel-api
          cluster: production
          wait-for-service-stability: true
```

This example assumes that ECR, ECS, the task definition, IAM roles, and appropriate GitHub environment variables already exist. The AWS roles must have narrowly scoped permissions, and their OIDC trust policies must constrain which repository, branch, or environment can assume them.

For a hardened production pipeline, third-party actions should also be pinned to reviewed full commit SHAs rather than relying solely on mutable version tags.

The example deliberately omits database migrations, vulnerability gates, and post-deployment verification. Those are separate release responsibilities we'll develop below.

### Notice the security boundary

The `verify` job does not require permission to deploy infrastructure.

The publishing job receives credentials suitable for writing the application image to ECR.

The deployment job receives a separate role for changing the ECS service.

GitHub's OpenID Connect integration allows workflows to obtain short-lived AWS credentials without storing long-lived AWS access keys in GitHub secrets.

But OIDC is only secure when the AWS trust policy properly restricts who can assume the role.

Granting a deployment role to every workflow in every repository would simply replace one credential problem with another.

### Why separate jobs?

The separation makes responsibilities visible.

A pull request can run verification without receiving production authority.

Only a qualifying push proceeds to publishing.

The deployment job is associated with the `production` environment, which can enforce approval and branch protection rules.

The concurrency configuration prevents two production deployment jobs from actively deploying simultaneously through the same group.

However, release ordering still deserves attention. Depending on workflow concurrency and queuing configuration, serialization alone does not necessarily guarantee that every release executes in commit order.

A production release system should also ensure that an older queued release cannot accidentally supersede a newer desired version.

---

## 6. Configuration Is Not the Same Thing as an Artifact

The same container image may execute in development, staging, and production.

But those environments use different databases, endpoints, credentials, resource allocations, and feature settings.

This gives us a useful separation:

```text
Application Artifact
         +
Environment Configuration
         +
Infrastructure State
         =
Running Deployment
```

The artifact contains application code and required runtime dependencies.

Configuration supplies values that vary by environment.

Infrastructure provides the resources and permissions needed for execution.

### What belongs in configuration?

Typical examples include:

```text
NODE_ENV=production
LOG_LEVEL=info
PAYMENT_PROVIDER=stripe
MAX_OUTBOUND_CONNECTIONS=50
```

Other values may include database endpoints, external API addresses, and feature configuration.

But configuration should be validated.

Consider:

```typescript
const timeout = Number(process.env.API_TIMEOUT);
```

If the variable is missing, the result may become `NaN`.

A safer application validates configuration at startup:

```typescript
const rawTimeout = process.env.API_TIMEOUT_MS;
const timeoutMs = Number(rawTimeout);

if (
  !rawTimeout ||
  !Number.isFinite(timeoutMs) ||
  timeoutMs <= 0
) {
  throw new Error("Invalid API_TIMEOUT_MS");
}
```

For larger applications, a schema-validation library can make this process systematic.

A service should fail clearly when required configuration is invalid rather than quietly operating with nonsensical settings.

### Secrets require a different level of care

Database passwords, API credentials, signing keys, and payment-provider secrets should not be embedded in container images.

Managed services such as AWS Secrets Manager or Systems Manager Parameter Store can provide secure secret storage and controlled retrieval.

The application still needs appropriate IAM permissions and must avoid leaking secret values through logs, error reports, or diagnostics.

Secrets may be injected into the environment or fetched at runtime, but neither approach is magically risk-free.

Rotation is also an operational concern. A running application may cache credentials and require explicit refresh or reconnection behavior when they change.

---

## 7. Database Migrations: The Hardest Part of Many Deployments

Now we reach the source of our opening disaster.

Application code is relatively easy to replace. You can deploy a new image and later restore an older one.

A production database is different.

It contains continuously evolving customer data, and schema modifications may be irreversible or expensive to reverse.

Meanwhile, application versions can coexist.

During a rolling deployment:

```text
Application v1 ──┐
                 ├── PostgreSQL
Application v2 ──┘
```

Both versions may query and modify the same database simultaneously.

Therefore, compatibility cannot be evaluated solely between the newest code and newest schema.

It must also account for the versions that remain active during the transition.

### The dangerous migration

Suppose reservations currently contain:

```sql
CREATE TABLE reservations (
  id UUID PRIMARY KEY,
  customer_id UUID NOT NULL,
  total_cents INTEGER NOT NULL
);
```

A developer introduces:

```sql
ALTER TABLE reservations
ADD COLUMN payment_terms TEXT NOT NULL;
```

Existing rows have no `payment_terms` value, so this statement would generally fail unless the data already satisfies the constraint through another mechanism, such as a suitable default.

Even if the migration is modified to succeed, enforcing a new non-null requirement may break old application versions that insert reservations without the field.

We need a safer method.

### Expand, migrate, contract

A common strategy divides schema evolution into compatible stages.

**Expand:** Add new structures without immediately removing or invalidating old ones.

**Migrate:** Update application behavior and existing data while maintaining compatibility.

**Contract:** Remove obsolete structures only after no remaining consumers require them.

Let's apply this to corporate billing.

### Phase 1 — Expand the schema

First, add the optional column:

```sql
ALTER TABLE reservations
ADD COLUMN payment_terms TEXT;
```

Existing code can continue inserting reservations without specifying the new field, assuming it does not depend on exact column layouts or other unusual schema assumptions.

The new application can treat null as the previous behavior:

```typescript
const paymentTerms =
  reservation.paymentTerms ?? "IMMEDIATE";
```

The application should also avoid enabling the corporate-billing feature until the required code and data conditions are satisfied.

### Phase 2 — Deploy compatible application code

The next application version understands both the old and expanded schema states it is designed to support.

For existing reservations, null means immediate payment.

For new corporate reservations, it may write:

```text
payment_terms = NET_30
```

Crucially, older application instances must remain able to operate while the new schema exists.

Adding a nullable column is often compatible with old code.

Removing or renaming a column usually isn't.

### Phase 3 — Backfill existing data

If the application eventually requires explicit payment terms for every reservation, populate older records.

For example:

```sql
UPDATE reservations
SET payment_terms = 'IMMEDIATE'
WHERE payment_terms IS NULL;
```

This is logically straightforward, but executing one enormous update on a table containing hundreds of millions of rows can generate substantial transaction logs, locks, I/O pressure, and replication lag.

Large backfills should often execute in controlled batches with monitoring and a way to resume after interruption.

The operation should also be safe to repeat.

### Phase 4 — Enforce the new invariant

Once all relevant writers populate the field and existing rows have been backfilled, the team can introduce stronger constraints.

For example:

```sql
ALTER TABLE reservations
ADD CONSTRAINT valid_payment_terms
CHECK (
  payment_terms IN ('IMMEDIATE', 'NET_30')
) NOT VALID;
```

A PostgreSQL `NOT VALID` check constraint avoids an immediate full validation scan of existing rows, while the new constraint still applies to subsequently inserted or updated rows.

Later:

```sql
ALTER TABLE reservations
VALIDATE CONSTRAINT valid_payment_terms;
```

Validation itself still requires database work and locking considerations.

Also notice that this particular check permits SQL null values. PostgreSQL check constraints reject false expressions, while null evaluates as unknown rather than false.

A separate non-null invariant would need to be established when safe.

The precise migration procedure depends on PostgreSQL version, table size, workload, and available locking tolerance.

### Phase 5 — Contract only when safe

If the change involved replacing an old field, the old field should not be dropped until every active API, worker, scheduled job, and other consumer has stopped depending on it.

This may require several releases.

The essential principle is:

**Schema changes should be planned across an interval of coexistence, not as one instantaneous switch from old code to new code.**

---

## 8. Database Migration Operations Have Their Own Failure Modes

It's tempting to treat migrations as small scripts that always run instantly.

But schema modifications are real database operations.

They can acquire locks, consume I/O, scan large tables, and interfere with ongoing transactions.

### Adding indexes

Consider:

```sql
CREATE INDEX idx_reservations_customer
ON reservations(customer_id);
```

On a large production table, an ordinary PostgreSQL index build can block concurrent writes for the duration of the operation.

PostgreSQL supports:

```sql
CREATE INDEX CONCURRENTLY idx_reservations_customer
ON reservations(customer_id);
```

This allows ordinary writes to continue during index construction, although it has additional overhead and limitations.

For example, `CREATE INDEX CONCURRENTLY` cannot execute inside a regular transaction block, and failed builds can leave invalid indexes requiring cleanup.

A migration framework that wraps every migration inside a transaction may therefore need special configuration for this operation.

### Who runs migrations?

A dangerous pattern is to make every application instance execute migrations automatically during startup.

Suppose ten ECS tasks launch simultaneously.

All ten attempt to perform the same schema migration.

Depending on the migration tooling and locking behavior, the result may be conflicts, blocked startups, or unnecessary database pressure.

A better approach usually gives migration execution a clearly controlled owner.

Possible designs include:

- A dedicated migration job.
- An explicitly coordinated release step.
- A deployment mechanism that executes migrations with appropriate locking guarantees.

For ECS, a one-off migration task can be a reasonable mechanism.

But the task still needs appropriate networking, credentials, observability, and failure handling.

**A migration is a production operation, not merely a build step.**

---

## 9. Deployment Strategies: Replacing a Running System

Suppose we have a verified application image and a compatible database schema.

How should the new version enter production?

There are several common strategies.

### All-at-once deployment

Stop the old application, then start the new one.

```text
v1 running
    ↓
v1 stopped
    ↓
v2 started
```

This is simple but may introduce downtime.

For an internal tool used occasionally, that might be perfectly acceptable.

For a customer-facing booking platform requiring high availability, it may not be.

### Rolling deployment

Replace application instances incrementally.

```text
Initial:       v1  v1  v1  v1
Intermediate:  v2  v1  v1  v1
Intermediate:  v2  v2  v1  v1
Final:         v2  v2  v2  v2
```

This can preserve availability while introducing the new version.

However, the old and new versions temporarily coexist.

That means they must be compatible with shared databases, message contracts, caches, and any relevant cross-version behavior.

### Blue-green deployment

Maintain two application environments or service revisions:

```text
              Load Balancer
                   │
          ┌────────┴────────┐
          ▼                 ▼
       BLUE v1           GREEN v2
       Production        Candidate
```

The green environment is prepared and validated before production traffic is shifted to it.

If problems arise, traffic can potentially return to blue, provided the older application remains compatible with current data and dependencies.

Blue-green deployments generally require additional temporary infrastructure capacity.

They also do not automatically revert database mutations.

### Canary deployment

Send a small portion of production traffic to the new version.

```text
95% traffic → v1
 5% traffic → v2
```

Observe its behavior.

If error rates, latency, and business outcomes remain acceptable, increase the new version's traffic share.

A canary limits initial exposure, but meaningful evaluation requires sufficient traffic and appropriately sensitive metrics.

A service receiving only a few requests per hour may not produce enough evidence during a short canary period.

### The hidden difficulty: stateful systems

Traffic shifting is relatively straightforward for stateless HTTP handlers.

It becomes more complicated with:

- Long-lived WebSocket sessions.
- Background workers consuming shared queues.
- Incompatible message formats.
- Database schema changes.
- Shared caches containing version-specific representations.

For example, reducing HTTP traffic to a buggy API version does not stop its background workers from consuming jobs.

Release strategies must cover the complete deployed system, not merely the frontend-facing service.

---

## 10. Feature Flags Separate Deployment From Release

One of the most useful techniques in modern deployment engineering is the feature flag.

A feature flag allows code to be deployed without immediately exposing the feature.

Consider:

```typescript
if (flags.corporateBillingEnabled) {
  return createInvoiceBasedReservation(request);
}

return createImmediatePaymentReservation(request);
```

The application can contain both code paths while only the established behavior remains enabled.

This makes it possible to:

1. Expand the database schema.
2. Deploy the compatible application code.
3. Verify production health.
4. Enable the feature for internal accounts.
5. Enable it for selected customers.
6. Expand availability gradually.

Deployment and product release become separate operations.

### Feature flags are not free

A feature flag introduces additional application states.

With three independent boolean flags, the theoretical number of flag combinations is:

\[
2^3 = 8
\]

With ten flags:

\[
2^{10} = 1024
\]

Not every combination is necessarily valid or reachable, but the broader point stands: excessive flags create testing and maintenance complexity.

Temporary rollout flags should generally have clear owners and removal plans.

Long-lived business configuration may deserve a different representation.

For example, corporate billing eligibility is probably a persistent business rule, not merely a temporary deployment flag.

Also, don't rely on a feature flag to conceal an incompatible schema assumption that occurs during application startup. A disabled feature cannot protect code that already queries missing columns before the flag is checked.

---

## 11. Rollbacks Are Easier for Code Than for Data

Imagine that a new version introduces a subtle payment calculation bug.

You deploy the previous container image.

Does this restore the previous state of the entire system?

No.

The database may already contain records written by the new version. External payments may have been processed. Messages may have been published and consumed.

Rolling back code cannot reverse all those effects.

### Three different forms of recovery

**Application rollback:** Restore a previously deployed application artifact.

**Configuration rollback:** Restore previously valid feature settings or runtime configuration.

**Data recovery or correction:** Repair, compensate for, or restore persistent state affected by the change.

These operations have different risks.

An application rollback can often be quick.

A database restoration may replace legitimate transactions completed since the backup was taken.

A payment refund is not simply a reversal of the original charge from the distributed system's perspective; it is a new financial operation with its own lifecycle.

This is why forward-compatible migrations and forward fixes are often safer than attempting to reverse destructive database changes.

### Roll forward or roll back?

The decision depends on the nature of the failure.

If a new version merely crashes on startup while the database remains compatible, restoring the previous image is often sensible.

If the deployment has already transformed persistent data into a new representation, rolling back may be unsafe without additional work.

A senior engineer must know the difference before pressing the rollback button.

---

## 12. Infrastructure as Code: Making the Environment Reproducible

So far, we've concentrated on deploying application artifacts.

But consider the infrastructure itself.

Your SaaS requires an S3 bucket, IAM roles, networking, an ECS cluster, database resources, and monitoring configuration.

If engineers create these manually through the AWS console, how does the organization know what infrastructure actually exists?

How can it reproduce the environment after a disaster?

How can another engineer review proposed changes?

This motivates **Infrastructure as Code**, or IaC.

### Declarative infrastructure

With a tool such as Terraform, engineers describe the desired infrastructure configuration.

For example:

```hcl
resource "aws_s3_bucket" "documents" {
  bucket = "example-company-documents"
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = "Enabled"
  }
}
```

This example describes a bucket, its public-access restrictions, and versioning configuration. A production bucket may additionally require encryption policy, lifecycle rules, access logging, ownership settings, and other controls.

The important conceptual shift is that infrastructure changes become reviewable source changes.

### Desired state versus actual state

Terraform evaluates three important inputs:

1. The desired configuration.
2. The infrastructure state it tracks.
3. Information retrieved from the provider about real resources.

It then calculates a proposed set of changes.

For example:

```text
Desired:
  ECS service has 4 tasks

Current:
  ECS service has 2 tasks

Plan:
  Update desired count from 2 to 4
```

The planning operation identifies what Terraform believes must change to reconcile infrastructure with the configuration.

This resembles a control system attempting to move observed state toward desired state.

But Terraform is not a continuously operating orchestrator by default. It performs reconciliation when a plan and apply operation is executed.

### The basic Terraform workflow

```bash
terraform init
terraform fmt -check
terraform validate
terraform plan -out=tfplan
terraform apply tfplan
```

`init` prepares the working directory and provider dependencies.

`validate` checks configuration structure and consistency without proving that the infrastructure is operationally correct.

`plan` proposes changes.

`apply` performs approved changes against the configured provider APIs.

A saved plan is valuable because the reviewed changes can be applied without independently recalculating a different plan at that moment.

But the saved plan must be protected: plan files can contain sensitive values, and infrastructure may change between planning and application.

---

## 13. Terraform State: The Other Source of Truth

If Terraform configuration describes desired infrastructure, why does Terraform need a state file?

Because Terraform must track which real resources correspond to particular declarations in its configuration.

For example:

```text
aws_s3_bucket.documents
        │
        ▼
Actual AWS Bucket Identifier
```

The state records resource identities, attributes, and other information needed to manage the infrastructure.

Without reliable state, Terraform may struggle to distinguish between resources it already manages and resources it should create.

### Remote state

For team environments, state should generally be stored in a controlled remote backend.

A suitable backend provides shared access, access controls, and preferably state locking.

State locking protects against concurrent Terraform operations that could otherwise attempt incompatible modifications.

Sensitive state data must be protected through encryption and least-privilege access.

State files can contain credentials or other sensitive infrastructure information even when Terraform configuration marks particular values as sensitive.

A private Git repository is not automatically an appropriate location for unencrypted state.

### Infrastructure drift

Suppose Terraform declares that an ECS service should run four tasks.

An engineer manually changes the desired count to six through the AWS console.

The deployed environment now differs from the declared configuration.

This is **drift**.

A subsequent Terraform plan may detect the difference and propose restoring the configured value.

But not every difference is necessarily accidental. An autoscaling mechanism may legitimately modify operational capacity.

Good IaC design must establish ownership boundaries so Terraform doesn't fight other controllers.

For example, Terraform can configure autoscaling policies without insisting on continuously overriding every runtime scaling adjustment.

### Should everything be controlled by Terraform?

Not necessarily.

Terraform is well suited to many infrastructure resources, but application deployment systems, autoscaling controllers, secret-rotation processes, and Kubernetes operators may manage certain runtime details better.

Two independent systems attempting to own the same property can create configuration conflicts.

The guiding principle is to make ownership explicit.

Infrastructure as Code should improve reproducibility and control, not introduce competing automation systems that repeatedly undo one another's work.

---

## 14. CI/CD and Terraform: Two Related but Different Pipelines

It's useful to separate application delivery from infrastructure provisioning.

An application release pipeline might:

```text
Commit
   ↓
Test
   ↓
Build Image
   ↓
Publish Image
   ↓
Deploy to ECS
```

An infrastructure pipeline might:

```text
Terraform Change
      ↓
Validate
      ↓
Plan
      ↓
Review
      ↓
Apply
```

They interact, but they solve different problems.

A new application version may require no infrastructure changes.

An infrastructure update may replace an RDS instance class without modifying application code.

Combining everything into one giant pipeline can create unnecessary coupling.

On the other hand, a feature requiring a new SQS queue, IAM permissions, and application code needs coordinated delivery.

The right design allows these changes to be sequenced deliberately without treating every application deployment as an opportunity to rebuild the entire cloud environment.

### Infrastructure changes deserve release discipline

A Terraform plan that modifies a security group may be low-risk.

A plan that destroys and recreates a production database is profoundly different.

Automated approval policies should account for the consequences of changes.

A production plan showing:

```text
-/+ aws_db_instance.production
```

indicates replacement rather than a simple in-place update.

That's the kind of symbol an experienced engineer learns to inspect very carefully.

A green Terraform validation result does not mean the proposed changes are safe.

It means the configuration passed certain checks.

The plan still requires interpretation.

---

## 15. Production Verification: The Pipeline Doesn't End at Deployment

Consider the GitHub Actions example from earlier.

Its ECS deployment step waits for service stability.

That is useful, but what does stability establish?

The service may have the desired number of running tasks and healthy load-balancer targets.

Yet customers may still experience business errors.

A `/health` endpoint might return HTTP 200 while payment processing fails for every customer.

A deployment system usually cannot infer complete application correctness from process liveness alone.

### Layers of release verification

A practical production verification strategy may include:

**Infrastructure health:** Are the required application instances running and reachable?

**Technical health:** Are error rates, latency, memory consumption, database connections, and queue backlogs within expected bounds?

**Business health:** Can customers perform important operations, such as creating reservations or processing payments?

**Comparative health:** Is the new version behaving worse than the previous version or established baseline?

For canary deployments, comparative metrics are especially valuable.

Suppose the previous version had a 0.2% HTTP error rate and the new version shows 4%.

That's meaningful evidence even if the application's health endpoint remains green.

### Avoid relying on averages

An average latency of 100 milliseconds may conceal a small but significant group of customers experiencing ten-second delays.

Percentiles, request distributions, and segmented metrics provide more useful evidence.

We'll examine this more thoroughly in the observability session.

### A release needs an explicit success condition

For example:

> After deploying the new version, the service must maintain an HTTP 5xx rate below 1% and p95 latency below 500 milliseconds over the configured evaluation window, while critical reservation smoke tests pass.

These thresholds are illustrative. Real values should reflect business requirements and established baseline behavior.

A release strategy should also specify what happens when verification fails.

Should traffic automatically shift back? Should a feature flag be disabled? Should the deployment pause for human review?

Without such decisions, automated deployment merely moves failure detection into production without defining the response.

---

## 16. Practical Lab — Design a Safe Release

Consider a TypeScript hotel-booking SaaS with the following components:

```text
Vue Frontend
     │
     ▼
Node.js API on ECS
     │
     ├── PostgreSQL RDS
     ├── Redis / BullMQ
     └── Payment Provider
```

Your team plans to introduce corporate billing.

The change requires:

- A new nullable `payment_terms` database column.
- A new API field.
- Updated reservation confirmation logic.
- A new background worker for generating invoices.
- A new SQS queue for invoice-processing events.
- A feature flag enabling corporate billing for selected customers.

The deployment must avoid customer-facing downtime.

### Investigation A — Separate the changes

Classify each change:

| Change | Category |
|---|---|
| Add nullable database column | Schema migration |
| Create SQS queue | Infrastructure |
| Add IAM permission to publish messages | Infrastructure/security |
| Update Node.js reservation logic | Application artifact |
| Deploy invoice worker | Application deployment |
| Enable corporate billing | Feature release |

Now determine the dependencies.

The queue must exist before the producer attempts to publish to it.

The application must have appropriate IAM authority before sending messages.

The schema must support the new code before the code assumes that support.

The worker should be deployed and verified before the feature begins generating production invoice workloads.

### Investigation B — Create the release sequence

A reasonable sequence might be:

```text
1. Expand PostgreSQL schema
          ↓
2. Provision queue and IAM configuration
          ↓
3. Deploy compatible API and worker code
          ↓
4. Verify infrastructure and application health
          ↓
5. Backfill or validate required data
          ↓
6. Enable corporate billing for test accounts
          ↓
7. Observe real business behavior
          ↓
8. Expand rollout gradually
          ↓
9. Remove obsolete compatibility code later
```

This is not a universal sequence. Some changes may be safely reordered or executed in parallel.

The important requirement is that each intermediate state remains valid.

### Investigation C — Identify rollback boundaries

For every step, ask what happens if it fails.

If creating the queue fails, the new feature should remain disabled.

If the API deployment fails, the prior version should remain functional against the expanded schema.

If invoice generation fails after a corporate reservation is confirmed, the system needs a durable retry or reconciliation process.

If the feature produces incorrect financial records, disabling the flag may stop new damage but will not automatically repair existing records.

### Investigation D — Define production evidence

Choose meaningful indicators:

- Reservation creation success rate.
- Invoice generation completion rate.
- Queue backlog age.
- Database errors.
- Payment-provider failures.
- Incorrectly classified payment terms.
- Duplicate invoices.
- New application error rate and latency.

For each indicator, decide what constitutes unacceptable behavior.

The lab is successful when you can explain why the proposed release is safe across its intermediate states—not merely when you have drawn a convincing pipeline diagram.

---

## 17. Engineering and Interview Challenges

### Challenge 1 — The perfect pipeline

A team has 100% successful CI runs over the past month. Nevertheless, production experiences frequent regressions after deployment.

What might CI be failing to establish? How would you improve release confidence without merely adding thousands of tests?

### Challenge 2 — The destructive migration

A new application version renames `customers.email` to `customers.primary_email`.

The deployment uses rolling updates, and old application instances may remain active for several minutes.

How would you introduce the new field without breaking old versions or losing updates?

### Challenge 3 — The misleading rollback

A release introduces a database migration, deploys new code, and begins writing data in a new representation.

An application bug is discovered thirty minutes later.

Would you immediately restore the previous Docker image?

What must be established first?

### Challenge 4 — Terraform drift

Terraform manages an ECS service configured for four tasks. An autoscaling policy increases the running task count to twelve during a traffic surge.

The next infrastructure pipeline proposes reducing the count to four.

Is Terraform malfunctioning? How would you resolve the ownership conflict?

### Challenge 5 — The supply-chain problem

An attacker gains control of a third-party GitHub Action used in your production release workflow.

Your pipeline stores long-lived AWS deployment credentials and grants broad repository permissions.

What could go wrong, and which architectural controls would reduce the damage?

---

## 18. Solutions and Discussion

### Challenge 1 — CI is only one source of confidence

Successful CI runs establish that selected checks passed against selected code and test environments.

They do not necessarily establish production configuration correctness, cross-version compatibility, realistic traffic behavior, external integration health, or safe database migration order.

I'd investigate recent incidents and identify which classes of failure escaped testing.

Then I'd improve the relevant boundaries: production-like integration tests, contract tests, migration compatibility checks, deployment smoke tests, canary monitoring, and operational rollback procedures.

Adding more unit tests may be ineffective if the failures arise from infrastructure configuration or incompatible deployment sequencing.

The objective is not maximum test count. It is evidence covering the actual risks.

### Challenge 2 — Renaming requires a compatibility interval

I'd avoid immediately renaming the existing column.

First, add `primary_email` while retaining `email`.

Next, deploy code that understands both representations and maintains data consistency during the transition.

However, simple application-level dual writing requires care: old instances may still update only `email`, causing the new column to become stale.

The team may need database-level synchronization, carefully sequenced writer upgrades, or another strategy ensuring all relevant writes remain consistent.

After old writers are retired, backfill and verify the new field, shift reads to it, and only later remove the old column.

The compatibility problem is semantic, not merely structural.

### Challenge 3 — Determine whether rollback is actually safe

Before restoring the previous image, I'd establish whether that version can read and write the current database schema and data representation.

I'd also investigate whether new background jobs, external operations, or data transformations have occurred.

If the old version remains compatible, code rollback may be appropriate.

If not, a forward fix or targeted compatibility patch may be safer.

Restoring the database from a backup could discard legitimate transactions completed after the backup, so it must not be treated as a routine application rollback.

The correct recovery strategy depends on which state changes have already become durable.

### Challenge 4 — Two controllers disagree about desired state

Terraform isn't necessarily malfunctioning.

It is attempting to reconcile the ECS service with the configuration that declares four tasks.

The autoscaling system is independently adjusting runtime capacity according to observed demand.

The team should define which system owns the desired-count property during normal operation.

A common solution is to let Terraform manage the autoscaling configuration while avoiding unnecessary reconciliation of runtime capacity changes controlled by the autoscaler.

The precise Terraform lifecycle configuration should be chosen carefully because ignoring changes also reduces drift visibility.

The broader lesson is that declarative automation requires clear ownership of each property.

### Challenge 5 — The release pipeline is a privileged system

A compromised action running inside a sufficiently privileged job could potentially read accessible secrets, modify build artifacts, publish malicious images, or deploy unauthorized code.

Long-lived AWS credentials increase the consequences of credential theft, while broad permissions expand the available attack surface.

I'd prioritize short-lived OIDC credentials with tightly constrained AWS trust policies, least-privilege job permissions, separation of verification and deployment roles, protected production environments, and review of third-party actions.

Pinning actions to reviewed commit SHAs reduces exposure to unexpected mutable-tag changes, although it does not eliminate the need to evaluate the action's trustworthiness.

Artifact provenance, image scanning, branch protection, and controlled deployment approvals provide additional defenses.

A deployment pipeline is not merely an automation convenience.

It is a security-sensitive component with the authority to change production.

---

## Mental Model

A production release is a coordinated transition across several kinds of state:

1. **Source state:** Which reviewed commit defines the change?
2. **Artifact state:** Which exact executable image was built and verified?
3. **Infrastructure state:** Which resources, permissions, and configuration exist?
4. **Schema and data state:** Which application versions can safely operate against current persistent data?
5. **Deployment state:** Which versions are running, and how is traffic distributed?
6. **Feature state:** Which capabilities are actually enabled for customers?
7. **Operational state:** What evidence establishes that the release is healthy?

**The central principle: Safe deployment means preserving system correctness through every intermediate state—not merely ensuring that the final version works in isolation.**


---

## End of SE340

**SE340 — Linux, Cloud Infrastructure, and Delivery** is complete. See the recommended study order in `README.md` for natural next courses.

## Further Reading

1. **GitHub — [Workflow Syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)**. Workflow structure, job dependencies, permissions, concurrency, environments, and deployment configuration.

2. **GitHub — [Configuring OpenID Connect in AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)**. Secure GitHub Actions authentication with short-lived AWS credentials and IAM trust-policy restrictions.

3. **HashiCorp — [Running Terraform in Automation](https://developer.hashicorp.com/terraform/tutorials/automation/automate-terraform)**. The plan/apply workflow, remote state, state locking, and automated infrastructure changes.

4. **HashiCorp — [Terraform State](https://developer.hashicorp.com/terraform/language/state)**. How Terraform tracks managed resources and why state requires careful protection.

5. **PostgreSQL — [ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)**. Schema modification operations, locking behavior, constraints, and compatibility considerations.

6. **PostgreSQL — [CREATE INDEX](https://www.postgresql.org/docs/current/sql-createindex.html)**. Concurrent index creation, locking trade-offs, and production migration limitations.

7. **AWS — [Amazon ECS Deployment Strategies](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_service-options.html)**. Rolling, blue-green, linear, and canary deployment models.

8. **Martin Fowler — [Feature Toggles](https://martinfowler.com/articles/feature-toggles.html)**. Separating deployment from feature release and understanding the maintenance costs of conditional behavior.

9. **Martin Fowler — [Blue-Green Deployment](https://martinfowler.com/bliki/BlueGreenDeployment.html)**. The core idea behind maintaining parallel environments to reduce release risk.

---


