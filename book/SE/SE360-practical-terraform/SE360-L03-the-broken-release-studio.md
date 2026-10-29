---
id: SE360-L03
course: SE360
title: "The Broken Release Studio"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE360-L02
next: null
---

# SE360 — Practical Terraform and Cloud Delivery
## Lecture 03: The Broken Release Studio

*The pipeline is green. The registry contains the correct image. Terraform reports no errors. Kubernetes accepts the deployment. Production is broken, and the automatic rollback makes it worse.*

---

# Part I — Intuition

## 1. The Release That Succeeded Three Times and Failed Once

Imagine you're working at a European SaaS company responsible for a hotel-booking platform.

The backend runs on Kubernetes. PostgreSQL stores reservations and payments. Redis accelerates frequently requested information, and background workers handle asynchronous operations.

Infrastructure is managed through Terraform. A CI/CD platform builds container images and deploys them through a controlled release pipeline.

The engineering team has spent several weeks preparing a booking-service update.

The new application fixes a payment reconciliation bug, introduces a new contact-email field, and updates an internal API.

On Thursday afternoon, the release begins.

The build passes.

Tests pass.

The Docker image is published.

Terraform reports no unexpected changes.

The database migration completes.

The deployment command exits successfully.

A release notification announces that version 2.0 has reached production.

Then the monitoring dashboard turns red.

The booking API begins returning errors.

The release automation responds by restoring the previous application image.

That operation also succeeds.

Unfortunately, the errors become worse.

The previous application version expects a database column that the migration has already renamed.

The application is now incompatible with the database.

Meanwhile, someone notices that the earlier production deployment may actually have targeted staging because of a credential configuration mistake.

And another engineer discovers that the container tag used in the release points to an older image.

You now have several plausible causes.

Some may be related.

Some may be independent.

Your job is not to guess which one sounds most familiar.

Your job is to reconstruct the release.

## 2. A Release Is Not One Operation

Developers often speak about deployment as though it were atomic.

"We deployed version 2."

That phrase conceals several independent processes.

The source revision is selected.

A build produces an artifact.

Tests verify some properties of that artifact.

An artifact is stored in a registry.

A deployment process selects an artifact.

Infrastructure and configuration are prepared.

A database schema may change.

Kubernetes receives a desired workload configuration.

Controllers start or replace application instances.

Traffic reaches the new instances.

Application behavior is verified.

These operations do not necessarily happen at the same moment.

They do not all share one transaction.

They may not even be performed by the same system.

### Visual anchor 1 — The release crosses multiple boundaries

```text
Approved source commit
          |
          v
Build and test
          |
          v
Immutable artifact
          |
          v
Deployment selection
          |
          v
Cloud account / cluster / namespace
          |
          +----------------------+
          |                      |
          v                      v
   Application rollout      Database changes
          |                      |
          +-----------+----------+
                      |
                      v
             Runtime compatibility
                      |
                      v
              Business verification
```

Each boundary can succeed locally while the overall release fails.

A container registry can publish an image correctly while the deployment selects another image.

Terraform can correctly apply a configuration while targeting the wrong account.

A database migration can complete successfully while breaking an older application version.

Kubernetes can start healthy Pods whose business operations fail against the current database.

The release must therefore be verified as a whole.

## 3. The Three Identities That Don't Match

Return to our incident.

The approved source commit is B.

The build system produces image B.

The deployment references the tag `latest`.

But `latest` points to image A.

The deployment tool successfully deploys image A.

The first mismatch is between the approved artifact and the selected artifact.

Now suppose the deployment job authenticates using credentials associated with staging.

The job is named `deploy-production`.

Its logs announce the production release.

But the actual target is staging.

The second mismatch is between the intended environment and the authenticated environment.

Finally, suppose a database migration renames `guest_email` to `contact_email`.

The new application understands `contact_email`.

The old application understands only `guest_email`.

When automation rolls back the application image without restoring compatibility, the old application fails.

The third mismatch is between application expectations and database schema.

These failures have different remedies.

### Visual anchor 2 — Three broken contracts

```text
ARTIFACT CONTRACT

Expected image B
Actual image A


TARGET CONTRACT

Expected production
Actual staging


COMPATIBILITY CONTRACT

Old application expects guest_email
Database now exposes contact_email
```

Treating these as one vague deployment failure makes diagnosis harder.

We need to establish which contract is broken, where, and with what consequences.

## 4. A Green Checkmark Is a Local Claim

A command returning exit code zero establishes that the command completed according to its own success criteria.

It doesn't establish that the entire business objective succeeded.

Suppose `docker push` succeeds.

That tells us the registry accepted the image under the relevant publishing semantics.

It doesn't prove that production runs it.

Suppose `terraform apply` succeeds.

That tells us Terraform completed the proposed infrastructure operations according to its provider interactions.

It doesn't prove that the application is healthy.

Suppose `kubectl apply` succeeds.

That tells us the Kubernetes API accepted the requested configuration change.

It doesn't prove the intended Pods are ready or serving traffic.

And suppose an application Pod reports readiness.

That means its configured readiness check passes.

It doesn't prove every important business workflow works correctly.

Each system has its own definition of success.

### 4.1 The hierarchy of evidence

A strong deployment process moves from intention to observation.

First, identify what should be deployed.

Then verify what was selected.

Next, verify where it was deployed.

Then establish what actually runs.

Finally, verify the intended business behavior.

**The release succeeds when the desired outcome is observed, not merely when its instructions finish executing.**

## 5. Rollback Is More Difficult Than Deployment

Imagine replacing a hotel elevator.

The new elevator requires changes to the building's electrical system.

You install the new elevator and rewire the controls.

Then the new elevator malfunctions.

Could you simply reinstall the old elevator?

Perhaps not.

The electrical system has changed.

Restoring the old physical equipment may not restore a working system.

Application releases have the same problem.

The new application may depend on new database columns, statuses, message formats, or configuration.

The database migration may remove structures required by the old version.

The new application may already have written data the old version doesn't understand.

Rolling back the container image is only one part of restoring a compatible system.

### Visual anchor 3 — The rollback trap

```text
BEFORE RELEASE

App v1 ─────► Schema A
guest_email   guest_email


AFTER MIGRATION

App v2 ─────► Schema B
contact_email contact_email


AUTOMATIC ROLLBACK

App v1 ──X──► Schema B
guest_email   contact_email

Image rollback succeeded.
Application compatibility failed.
```

The database isn't necessarily broken.

The old application isn't necessarily broken in isolation.

Their combination is broken.

## 6. Compatibility Is a Time Window

A safe database migration often requires old and new application versions to work during a transition period.

Instead of immediately renaming or deleting the old column, the system can introduce the new column alongside it.

The application adopts a compatible write strategy.

Existing records are backfilled.

The new application gradually changes its read path.

Only after old consumers and rollback requirements have been retired is the old column removed.

This is the expand–migrate–contract approach developed in CS350-L04.

The essential insight is temporal.

A schema doesn't merely have to be correct before and after the release.

It must remain compatible throughout the deployment sequence.

This includes moments when old and new application replicas coexist.

## 7. Containment Comes Before Cleverness

Now imagine being called into the incident while customers are experiencing errors.

You have several options.

Rebuild the application.

Rerun the deployment.

Force Terraform to apply again.

Revert the database migration.

Restore the old container image.

Deploy a corrected new application.

Before choosing, establish the actual state.

Which artifact is running?

Which environment is affected?

What schema exists?

Which business operations are failing?

Which operations can be safely paused?

What data has already changed?

The wrong intervention can increase the blast radius.

If only staging received the wrong artifact, deploying a new image to production without understanding the target mismatch might repeat the mistake.

If the database contains new-format data, blindly restoring an old schema may lose information.

If a Terraform state lock is held by an active operation, forcing it open may create competing infrastructure writers.

A good incident response stabilizes the system while preserving enough evidence to determine what actually happened.

## 8. A Tiny Comprehension Check

Suppose the deployment job built image B but production runs image A.

Should you immediately rebuild B?

No. First establish whether the build was correct and where artifact identity diverged.

Suppose the deployment job claims production but the authenticated cloud account is staging.

Should you trust the job name?

No. Verify the actual target identity.

Suppose the old application fails after rollback because the database schema has changed.

Does that mean the image rollback mechanism malfunctioned?

Not necessarily. It may have restored the image perfectly while creating an incompatible application/database combination.

Those three distinctions are the foundation of the release studio.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 9. Reconstruct the System Before Diagnosing the Incident

The most dangerous part of an unfamiliar production incident is the temptation to start changing things immediately.

A pipeline failure may involve CI configuration, artifact storage, cloud credentials, Terraform state, Kubernetes workloads, database schema, or application behavior.

Without reconstructing the relevant dependency graph, an engineer can easily intervene at the wrong layer.

Our case involves four independently managed systems.

The CI platform produces artifacts.

The registry stores artifacts.

Terraform manages supporting infrastructure.

Kubernetes deploys application workloads.

PostgreSQL manages persistent application data.

The release coordinates all of them.

### 9.1 Establish the approved intention

Begin with the release request.

Which source revision was approved?

Which services were supposed to change?

Which database migrations were included?

Which environments were authorized?

Which release checks were required?

If this information is missing, the release process itself has a traceability problem.

### 9.2 Establish the observed state

Next, inspect actual evidence.

Which artifact is currently running?

Which Terraform backend and cloud account were used?

Which Kubernetes cluster and namespace received the deployment?

Which database schema is present?

What errors are occurring?

The difference between intention and observation is where the investigation begins.

## 10. Incident One — The Correct Build and Wrong Image

Let's investigate the artifact mismatch.

The pipeline ran against commit B.

The build created an image.

Tests passed.

The image registry contains the expected image.

Yet production runs commit A.

This indicates that the source-to-build portion of the chain may be correct while the build-to-deployment portion is not.

### 10.1 Build identity

A strong build records the exact source revision, build run, and artifact digest.

For container images, the digest provides a content identity stronger than a mutable tag.

The build should produce evidence connecting commit B to the image selected for testing.

### 10.2 Artifact selection

Suppose the deployment references `booking-api:latest`.

The tag may currently point to image A.

The deployment tool has no independent knowledge that the engineering team intended B.

It follows the reference supplied.

The operation can succeed perfectly while selecting the wrong artifact.

### 10.3 Runtime selection

Even when the correct image reference is configured, the runtime must be inspected.

Kubernetes may still have old replicas during rollout.

A tag-based reference may interact with image-pull policies.

A Pod-template change may not have occurred.

The deployment may be stalled or incomplete.

Therefore, distinguish the configured image from the observed running image.

### 10.4 Corrective action

The correct release artifact should be selected by verified immutable identity.

Then the team must confirm the actual workload uses that identity.

A new build isn't necessarily required.

If image B was correctly produced and tested, rebuilding introduces another output that must be verified.

Sometimes the safest recovery is simply promoting the already-tested artifact.

## 11. Incident Two — The Right Artifact and Wrong Target

Now consider a different failure.

The release selects image B correctly.

The deployment job intends production.

But the credentials point to staging.

The deployment succeeds against the authenticated environment.

Production remains unchanged.

### 11.1 Names aren't authority

A CI job named `production-release` is only a label.

An environment variable named `PRODUCTION=true` is also only a value.

The actual target depends on credentials, provider configuration, cluster context, namespace, and related settings.

### 11.2 Terraform makes the distinction more important

Terraform has a declared configuration, a state backend, and a provider target.

A configuration variable indicating staging doesn't guarantee that the selected state or credentials belong to staging.

The backend identifies managed resource state.

The provider credentials determine which real infrastructure APIs can be modified.

Both must be checked.

### 11.3 Environment identity as a tuple

A deployment target can be represented conceptually as a collection of verified identities.

For example:

Cloud account.

Region.

Kubernetes cluster.

Namespace.

Application service.

Terraform backend and state key, when infrastructure changes are involved.

The deployment should compare this identity against the approved target before making changes.

### 11.4 Fail closed

If the intended environment and authenticated environment disagree, the deployment should stop.

Logging a warning is not enough.

A production release should not succeed merely because a command reached some valid cluster.

It should require evidence that the cluster is the approved production target.

## 12. Incident Three — A Database Migration Breaks Rollback

The third incident is more dangerous because persistent state has changed.

Application v1 reads `guest_email`.

Application v2 reads `contact_email`.

The release migrates the database by renaming the column.

Then v2 encounters an unrelated business bug.

The deployment system rolls back to v1.

The old application now queries a nonexistent column.

### 12.1 A migration can succeed while the release fails

The schema migration may be logically correct.

It may complete without errors.

But its compatibility consequences can still be unacceptable.

The database may support v2 while no longer supporting v1.

That is especially dangerous during rolling deployments, when old and new replicas can coexist.

### 12.2 The state transition is not symmetric

Application deployment can often restore an earlier container image.

Data changes aren't equally reversible.

A renamed column may preserve its values, but the application interface has changed.

A dropped column may remove information from the logical schema.

A transformed value may not retain enough information to reconstruct its previous representation.

A new business status may be unknown to old application code.

Even if the schema can technically be reversed, that doesn't prove reversal is safe for data written since the migration.

### 12.3 Correct recovery may be forward

Suppose v2 has a business bug unrelated to the schema.

The new schema is intact and data is consistent.

The old application is incompatible.

A corrected v2 release may be safer than restoring the old schema.

This is forward recovery.

Alternatively, a compatibility restoration may be necessary if no corrected new application is available.

That decision depends on actual data, application requirements, and operational urgency.

**Rollback is one recovery strategy, not a universal obligation.**

## 13. A Fourth Identity: Data Compatibility

SE360-L01 taught us to follow source and artifact identity.

SE360-L02 added infrastructure state and target identity.

Now the release also has a data compatibility contract.

An image digest establishes which application bytes are running.

It doesn't establish that those bytes understand the current database schema.

A successful migration establishes that the database accepted a schema change.

It doesn't establish that every deployed application version understands the new schema.

We therefore need to evaluate the application/schema combination.

### 13.1 A compatibility matrix

Imagine two schema versions.

Schema A contains `guest_email`.

Schema B contains both `guest_email` and `contact_email`.

Schema C contains only `contact_email`.

Application v1 reads the old field.

Application v2 reads the new field.

If v2 can tolerate partially populated data during migration, Schema B can provide a useful compatibility interval.

But the write behavior matters.

If v1 continues modifying only `guest_email` while v2 reads `contact_email`, the fields can diverge.

A historical backfill alone doesn't guarantee ongoing consistency.

### 13.2 Compatibility requires more than column presence

The application may also depend on constraints, data formats, enumerated statuses, message payloads, or transaction assumptions.

A schema can contain the correct column names while the stored values remain incompatible.

The release contract must include the business meaning of the data.

## 14. Expand–Migrate–Contract in a Real Release

A safer transition avoids combining a destructive schema change with the first deployment of code depending on that change.

### 14.1 Expand

Introduce the new field without removing the old one.

The existing application should continue working.

Perform this as a carefully controlled schema operation.

PostgreSQL schema changes still have locking consequences even when they don't require a full table rewrite.

### 14.2 Establish compatible writers

Deploy application logic that maintains the necessary representations.

The authoritative source of truth must be clear.

If the old field remains authoritative during transition, compatible writers may need to update both fields.

### 14.3 Backfill

Populate historical values.

Use bounded operations for large datasets.

Verify counts and semantic equality.

Handle concurrent writes explicitly.

### 14.4 Switch readers

Move application reads to the new representation.

Continue maintaining whatever backward compatibility the rollback window requires.

### 14.5 Validate

Establish constraints and invariants once the data and write paths are ready.

Validation should not make still-deployed application instances suddenly incompatible.

### 14.6 Contract

Remove the old field only after old consumers and rollback requirements have been retired.

This is the deliberate point at which an old application version may cease to be deployable.

It should not be an accidental side effect of the initial rollout.

## 15. Infrastructure Changes Have Their Own Partial-Failure Semantics

Now introduce Terraform into the release.

Suppose the release includes a new database security group, an application role, and an updated service configuration.

The Terraform plan includes several changes.

Three succeed.

The fourth fails.

Terraform reports an unsuccessful apply.

But the first three changes may already exist.

Terraform apply is not one atomic transaction across every provider resource.

### 15.1 Don't assume failed means unchanged

After a partial apply, inspect current state and real infrastructure.

A retry may be necessary.

But it should be based on the updated situation, not an unsupported assumption that nothing happened.

### 15.2 The state backend matters

A Terraform saved plan is tied to configuration and state context.

It can contain backend configuration and sensitive values.

A plan produced against the wrong backend is not made safe by a green review check.

Before applying infrastructure changes, establish the approved backend, state identity, workspace, and provider target.

### 15.3 Locking is part of safety

If another operation holds a legitimate state lock, don't casually disable locking to force progress.

That can create competing state writers.

The correct response is to investigate the lock owner and the operation's status.

An incident response should not create a second infrastructure-control incident.

## 16. Kubernetes Success Is Not Business Success

A deployment system can accept a new desired state while the application remains unavailable.

Kubernetes Deployment controllers reconcile desired replicas.

They create new ReplicaSets, start Pods, and track rollout progress.

A release should inspect that progress.

### 16.1 Rollout status

`kubectl rollout status` can help establish whether a Deployment completed its rollout.

But completion should not be interpreted as complete business verification.

### 16.2 Readiness probes

Readiness probes determine whether a Pod is eligible to receive traffic under its configured readiness behavior.

A readiness endpoint may check that the process is running and that essential dependencies are reachable.

It may not test every business workflow.

A successful readiness probe is useful evidence.

It isn't exhaustive proof.

### 16.3 Business smoke tests

A booking platform might verify that the API can retrieve a booking using the expected schema.

A payment service might validate a safe read-only reconciliation operation.

A worker system might verify that a representative job can complete without introducing irreversible side effects.

These checks should be selected according to release risk.

### 16.4 Mixed-version rollout

During a rolling deployment, old and new Pods may coexist.

If a database migration is compatible only with v2, old v1 Pods may fail while the rollout proceeds.

A migration strategy must account for the rollout's overlap period.

## 17. Deployment Ordering Can Create Unexpected Downgrades

Two pipelines may target the same environment.

Pipeline A builds an older revision.

Pipeline B builds a newer revision.

B finishes first and deploys.

A later finishes and deploys.

Production moves backward.

Both pipelines may report success.

### 17.1 Serializing isn't always enough

CI systems support deployment serialization mechanisms.

Jenkins can use suitable locks.

GitHub Actions supports concurrency controls.

GitLab CI provides resource groups and outdated-deployment protections.

These can prevent overlapping operations.

But the intended version order still matters.

An older queued deployment might execute later unless the release process rejects it.

### 17.2 Explicit rollback is different from stale deployment

There are legitimate reasons to deploy an older artifact.

A rollback can intentionally select a previous digest.

But that action should be explicit and authorized.

An outdated pipeline automatically overwriting the current version is a different failure.

The deployment system should distinguish them.

## 18. The Release Approval Should Name What It Approves

Imagine an engineer clicking Approve beside a job labeled:

"Deploy latest to production."

What exactly are they approving?

Which commit?

Which image digest?

Which infrastructure plan?

Which schema migration?

Which production account?

A meaningful approval should have a concrete target.

For example, it can identify the exact source revision, image digest, environment identity, migration compatibility requirements, and relevant infrastructure plan.

This turns approval into a reviewable decision.

### 18.1 Deployment authorization versus artifact provenance

A release can be correctly authorized but select the wrong artifact.

An artifact can be correctly built but deployed without appropriate authorization.

These are separate security and correctness controls.

Strong release engineering needs both.

## 19. A Practical Release Manifest

A useful release manifest records the identities involved in a deployment.

For a backend service, it might include:

Source revision.

Build run.

Artifact digest.

Application version.

Expected database schema compatibility range.

Target environment.

Infrastructure change reference.

Required health checks.

The manifest can be reviewed before release and compared with runtime observations afterward.

### 19.1 A manifest isn't magic

A manifest can contain incorrect information.

A compromised build system might produce false metadata.

For high-assurance supply chains, trusted builders, signatures, and attestations may be appropriate.

But even a straightforward manifest helps detect accidental mismatches.

It provides an explicit record of what the release intended.

### 19.2 Bind the manifest to the artifact

Build information should be produced consistently and associated with the artifact.

The deployment should verify that it selected the intended artifact.

The runtime should expose or report its build identity through a trustworthy operational channel.

The objective is preserving identity across the release chain.

## 20. Incident Containment: What Should Happen First?

Return to the broken release.

Production is experiencing errors.

The pipeline has already completed.

The team is debating whether to run another deployment.

A strong response begins with current state.

### Step 1 — Freeze uncontrolled changes

Prevent overlapping automated deployments or migrations from introducing new uncertainty.

Don't arbitrarily terminate legitimate operations without understanding their state.

### Step 2 — Establish business impact

Which endpoints are failing?

Which customers are affected?

Are writes occurring?

Is data at risk?

### Step 3 — Identify runtime and target

Which application version is actually serving traffic?

Which environment was modified?

Are some replicas still running another version?

### Step 4 — Establish schema compatibility

What schema and data representations currently exist?

Which application versions can safely operate against them?

### Step 5 — Choose containment

Depending on evidence, possible actions include pausing rollout, routing traffic to compatible replicas, disabling a faulty feature, or deploying a known-compatible release.

Avoid automatically restoring an incompatible image.

### Step 6 — Preserve evidence

Record artifact digests, pipeline run IDs, relevant logs, Terraform state identity, migration history, and runtime observations.

### Step 7 — Recover deliberately

Choose rollback, forward fix, or another recovery method.

Define the expected post-recovery state.

### Step 8 — Verify business behavior

Don't stop at a green deployment or passing readiness probe.

Confirm the affected user operations work correctly.

## 21. The Wrong Easy Fixes

Several interventions may appear attractive under pressure.

### "Just rebuild the image"

If the correct image already exists, rebuilding adds another artifact without addressing the original selection error.

First inspect the digest used in production.

### "Just redeploy latest"

If `latest` points to the wrong image, repeating the deployment may repeat the mistake.

Select a verified immutable artifact.

### "Just change the CI environment variable"

Changing a variable doesn't prove the actual credentials and target are correct.

Verify the account, cluster, namespace, and state context.

### "Just rerun Terraform"

A partial apply or unexpected plan requires current-state inspection.

Blindly repeating infrastructure operations can cause additional changes.

### "Just roll back the application"

The database may no longer support the old version.

Check compatibility before rollback.

### "Just reverse the migration"

The new application may already have written data that the old schema cannot represent safely.

A reverse migration requires its own data and compatibility analysis.

### "The readiness probe passed"

A readiness check may not exercise the affected business operation.

Verify the relevant workflow.

These mistakes share one pattern.

They treat a local success mechanism as proof of system-wide correctness.

## 22. Building a Causal Incident Report

A good incident report separates facts, hypotheses, and corrections.

Start with the impact.

Then reconstruct the timeline.

Identify the first observed mismatch.

Explain which later decisions amplified the failure.

For example:

> The approved release built image B, but deployment selected image A through a mutable tag. Separately, a staging credential was used for a production-targeted job. The database migration renamed a column required by the old application, and automatic image rollback restored an incompatible application/schema combination.

This is a meaningful diagnosis because it distinguishes independent failure mechanisms.

Now describe the recovery.

Maybe the immediate repair is deploying the corrected v2 artifact against the current schema.

Maybe the correct environment must be targeted explicitly.

Maybe the release process needs to pause destructive migrations until compatibility is established.

Finally, define prevention.

Immutable artifact references.

Target-identity checks.

Compatibility-preserving migrations.

Release concurrency controls.

Post-deployment business verification.

The incident report should explain why those controls address the failures observed.

## 23. The Senior Engineer's Judgment

The strongest engineer isn't necessarily the person who remembers the most CI directives.

It's the person who can preserve a coherent model of the release while evidence arrives from different systems.

They understand that an application image, cloud environment, database schema, and running service are separate entities with separate identities.

They don't confuse a successful command with the successful business outcome.

They can reason about partial failures.

And they understand that rollback can be unsafe when persistent state has moved forward.

A good senior engineer can say:

"The image rollback succeeded, but it restored a version that cannot read the current schema. We should not repeat it. Let's verify the migration state, identify a compatible artifact, and restore service through the least disruptive recovery path."

That is the kind of judgment this capstone is designed to test.

---

# The Oral Examination

Answer aloud before reading the solutions.

## Question 1 — The Green Pipeline

A pipeline builds image B and reports a successful production deployment, but runtime inspection identifies image A.

What evidence would you collect first?

## Question 2 — The Mutable Tag

The build system publishes the correct image, but deployment uses `latest`.

Why does this weaken artifact provenance?

## Question 3 — The Wrong Target

A deployment job is named production but authenticates to staging.

Which identity should the deployment system trust?

What should it do when expected and actual targets differ?

## Question 4 — Terraform State

A Terraform saved plan was generated against one backend.

The deploy process now uses a different backend configuration.

Why does this require investigation?

## Question 5 — Rollback Compatibility

Application v1 reads `guest_email`.

The database now contains only `contact_email`.

A deployment system restores v1 successfully.

Why is the service still broken?

## Question 6 — The Safe Migration

Describe a compatible sequence for moving from `guest_email` to `contact_email`.

What must happen before the old column can be removed?

## Question 7 — Kubernetes Rollout

`kubectl apply` exits successfully.

What further evidence is needed before claiming that production runs the expected application?

## Question 8 — The Business Probe

All Pods are ready, but booking lookups fail.

What does that tell you about the readiness contract?

## Question 9 — Partial Apply

Terraform creates two resources and fails on a third.

Can you assume nothing changed?

How should recovery proceed?

## Question 10 — The Deployment Race

A newer pipeline deploys before an older pipeline.

The older pipeline later completes and deploys its image.

How would you prevent accidental regression while preserving the ability to perform an authorized rollback?

## Question 11 — The Recovery Choice

The new schema is consistent, but application v2 has a non-schema-related bug.

The old application is incompatible with the schema.

Would you automatically reverse the database migration?

Explain your decision.

## Question 12 — The Incident Commander

You have a failing production release, conflicting dashboard signals, and three engineers proposing different fixes.

What sequence of evidence and containment actions would you prioritize?

---

# Solutions and Discussion

## Solution 1 — Artifact Identity

Identify the approved commit, build run, produced digest, tested digest, selected deployment reference, resolved digest, and observed running image.

Find the first mismatch.

## Solution 2 — Mutable Tags

A tag can be moved to another image.

The deploy job might resolve it to an artifact different from the one tested and approved.

A verified immutable digest preserves the selected artifact's content identity more precisely.

## Solution 3 — Target Identity

The actual authenticated account, cluster, namespace, and service determine where operations act.

The deployment should fail on a mismatch with the approved target.

A job name isn't an authorization or identity boundary.

## Solution 4 — Terraform Backend

Saved Terraform plans capture relevant backend configuration.

Applying one requires understanding the state and infrastructure context against which it was generated.

A saved plan can also contain sensitive backend information.

## Solution 5 — Compatibility

The old application expects a column the database no longer exposes.

Restoring the old image doesn't restore the old schema.

The application and database are individually valid but mutually incompatible.

## Solution 6 — Expand–Migrate–Contract

Add the new field while keeping the old one.

Deploy compatible writers.

Backfill historical records.

Eliminate incompatible writers and reconcile data.

Switch reads.

Validate required constraints.

Remove the old field only after the compatibility and rollback window has closed.

## Solution 7 — Runtime Verification

Inspect rollout status, Pod readiness, desired image references, actual running image identities, and business behavior.

Deployment command success is only one stage of verification.

## Solution 8 — Health Contract

The readiness probe checks a narrower condition than the failing business operation.

A release should include appropriate smoke tests that exercise important application/database compatibility paths.

## Solution 9 — Partial Apply

Some resources may already exist.

Inspect current state and actual infrastructure, then generate an appropriate fresh recovery plan.

Terraform apply is not a universal multi-resource transaction.

## Solution 10 — Release Ordering

Serialize conflicting deployments where appropriate and reject stale candidate releases.

An intentional rollback should explicitly authorize deploying an older artifact.

Don't rely solely on pipeline completion order.

## Solution 11 — Forward Recovery

A corrected v2 may be safer than reversing a schema migration, particularly if new-format data has already been written.

Choose based on the actual schema, data, compatibility, and recovery implications.

## Solution 12 — Incident Priorities

Establish business impact and freeze uncontrolled changes.

Identify actual artifact, environment, schema, and runtime state.

Separate observed facts from hypotheses.

Contain the immediate failure.

Choose a compatible recovery path.

Verify the business operation, not merely infrastructure command success.

---

# The Mental Model Worth Keeping

A production release crosses multiple independently managed systems.

The source revision identifies the intended code.

The build artifact identifies the produced bytes.

The deployment target identifies where changes should occur.

The runtime identifies what actually runs.

The database schema and stored data determine which application versions remain compatible.

The essential questions are:

**What did we approve? What did we build? What did we deploy? Where did it go? What is running? What data does it expect? What happens if we reverse the application change?**

A green pipeline is evidence about execution.

A healthy release is evidence about the complete system.

---

# Course Completion — SE360

This completes the three-lecture SE360 specialist sequence.

SE360-L01 investigated CI/CD platforms, artifacts, caches, credentials, and deployment provenance.

SE360-L02 investigated Terraform state, drift, locking, environment identity, and infrastructure reconciliation.

SE360-L03 combines those concerns with application/schema compatibility and recovery.

The next step is demonstrating the ability to investigate unfamiliar release failures without relying on memorized answers.

The strongest outcome is not knowing every Jenkins, GitHub Actions, GitLab CI, Terraform, or Kubernetes command by heart.

It is understanding how release identity and responsibility move between systems—and how to establish what went wrong when those systems disagree.

*The spoken lecture ends here. The following practical studio uses a disposable local simulation. Attempt the incident packets before consulting the diagnostic notes.*

---

# Optional Practical Lab — The Broken Release Room

## Lab Contract

This studio contains three independent incidents.

The exercises reproduce real failure patterns with an isolated local simulation.

It uses Python's standard library, JSON artifacts, SHA-256 digests, and SQLite.

No production credentials, cloud account, container registry, or Kubernetes cluster is required.

The SQLite database demonstrates application/schema incompatibility. It does not reproduce PostgreSQL's lock modes, MVCC behavior, or online migration costs.

The infrastructure-target simulation uses credential labels rather than real Terraform or cloud provider operations.

The difference is intentional.

We want to isolate the release logic before introducing cloud infrastructure.

**Hypothesis → Evidence → Mechanism → Containment → Correction → Verification.**

## 1. Prepare the Workspace

Create a directory named `se360-broken-release`.

Inside it, create `studio.py`.

The script provides six commands:

- `init` resets the isolated release room.
- `artifact` reproduces the wrong-artifact deployment.
- `target` reproduces a wrong-environment deployment.
- `schema` reproduces an incompatible rollback.
- `inspect` displays the current evidence.
- `forward-fix` repairs the schema-compatible application in the third scenario.

Each scenario should start from a fresh `init` unless explicitly instructed otherwise.

The script deletes only the `release-room` directory beneath its working directory.

Do not place unrelated work inside that directory.

### The simulation

The program creates four immutable application artifacts.

Version A is the original application.

Version B includes the intended business fix but still reads the old database schema.

Version C reads the new schema but contains a simulated business defect.

Version D reads the new schema and fixes the defect.

The artifact digests are calculated from the actual bytes of the simulated application metadata.

```python
import hashlib
import json
import shutil
import sqlite3
import sys

from pathlib import Path


ROOT = Path("release-room")

REVISIONS = {
    "A": (
        "a" * 40,
        "1.0.0",
        "guest_email",
        False,
    ),
    "B": (
        "b" * 40,
        "1.1.0",
        "guest_email",
        False,
    ),
    "C": (
        "c" * 40,
        "2.0.0",
        "contact_email",
        True,
    ),
    "D": (
        "d" * 40,
        "2.0.1",
        "contact_email",
        False,
    ),
}


def write(path, value):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
    )


def read(path):
    return json.loads(
        path.read_text()
    )


def blob(label):
    revision, version, column, defect = (
        REVISIONS[label]
    )

    contents = json.dumps(
        {
            "source_commit": revision,
            "version": version,
            "read_column": column,
            "business_defect": defect,
        },
        sort_keys=True,
    ).encode()

    digest = hashlib.sha256(
        contents
    ).hexdigest()

    path = (
        ROOT
        / "registry"
        / "blobs"
        / f"{digest}.json"
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_bytes(contents)

    return digest


def init_db(environment):
    path = (
        ROOT
        / "databases"
        / f"{environment}.sqlite"
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE bookings (
                id INTEGER PRIMARY KEY,
                guest_email TEXT NOT NULL
            )
            """
        )

        db.execute(
            """
            INSERT INTO bookings
            VALUES (
                42,
                'guest@example.test'
            )
            """
        )


def init():
    if ROOT.exists():
        shutil.rmtree(ROOT)

    digests = {
        label: blob(label)
        for label in REVISIONS
    }

    write(
        ROOT / "registry" / "tags.json",
        {
            "latest": digests["A"],
            "release-B": digests["B"],
        },
    )

    write(
        ROOT / "ci" / "build.json",
        {
            "approved_commit":
                REVISIONS["B"][0],
            "tested_digest":
                digests["B"],
            "test_result": "passed",
        },
    )

    write(
        ROOT / "ci" / "credentials.json",
        {
            "account": "production",
        },
    )

    for environment in (
        "production",
        "staging",
    ):
        init_db(environment)

        write(
            ROOT
            / "environments"
            / f"{environment}.json",
            {
                "running_digest":
                    digests["A"],
                "deployment_status":
                    "initial",
            },
        )

    print(
        "Initialized isolated release room."
    )

    print(
        "Expected build: B;"
        " latest currently selects A."
    )


def resolve(ref):
    if ref.startswith("sha256:"):
        return ref.split(":", 1)[1]

    tags = read(
        ROOT / "registry" / "tags.json"
    )

    return tags[ref]


def deploy(
    ref,
    expected="production",
):
    actual = read(
        ROOT / "ci" / "credentials.json"
    )["account"]

    digest = resolve(ref)

    record = (
        ROOT
        / "environments"
        / f"{actual}.json"
    )

    write(
        record,
        {
            "running_digest": digest,
            "deployment_status":
                "success",
        },
    )

    write(
        ROOT / "ci" / "last-deploy.json",
        {
            "expected_environment":
                expected,
            "actual_environment":
                actual,
            "reference":
                ref,
            "resolved_digest":
                digest,
            "job_status":
                "success",
        },
    )

    print(
        "Deployment command succeeded:"
        f" expected={expected},"
        f" actual={actual},"
        f" reference={ref}"
    )


def artifact():
    deploy("latest")


def target():
    write(
        ROOT / "ci" / "credentials.json",
        {
            "account": "staging",
        },
    )

    deploy("release-B")


def schema():
    path = (
        ROOT
        / "databases"
        / "production.sqlite"
    )

    with sqlite3.connect(path) as db:
        db.execute(
            """
            ALTER TABLE bookings
            RENAME COLUMN guest_email
            TO contact_email
            """
        )

    digest_c = blob("C")

    write(
        ROOT
        / "environments"
        / "production.json",
        {
            "running_digest": digest_c,
            "deployment_status": "success",
        },
    )

    print(
        "Applied destructive rename;"
        " deployed C;"
        " business probe:",
        probe("production"),
    )

    digest_a = blob("A")

    write(
        ROOT
        / "environments"
        / "production.json",
        {
            "running_digest": digest_a,
            "deployment_status":
                "rollback-success",
        },
    )

    print(
        "Rolled back image to A;"
        " business probe:",
        probe("production"),
    )


def probe(environment):
    digest = read(
        ROOT
        / "environments"
        / f"{environment}.json"
    )["running_digest"]

    image_path = (
        ROOT
        / "registry"
        / "blobs"
        / f"{digest}.json"
    )

    image_bytes = image_path.read_bytes()

    if (
        hashlib.sha256(
            image_bytes
        ).hexdigest()
        != digest
    ):
        return (
            "FAIL: image digest mismatch"
        )

    image = json.loads(image_bytes)

    column = image["read_column"]

    database = (
        ROOT
        / "databases"
        / f"{environment}.sqlite"
    )

    try:
        with sqlite3.connect(
            database
        ) as db:
            db.execute(
                f"""
                SELECT {column}
                FROM bookings
                WHERE id = ?
                """,
                (42,),
            ).fetchone()

    except sqlite3.OperationalError as exc:
        return (
            "FAIL: schema incompatibility:"
            f" {exc}"
        )

    if image["business_defect"]:
        return (
            "FAIL: simulated business regression"
        )

    return (
        f"PASS: app {image['version']}"
        f" / column {column}"
    )


def inspect():
    build = read(
        ROOT / "ci" / "build.json"
    )

    tags = read(
        ROOT / "registry" / "tags.json"
    )

    credentials = read(
        ROOT / "ci" / "credentials.json"
    )

    print(
        "Approved commit:",
        build["approved_commit"][:8],
    )

    print(
        "Tested digest:",
        build["tested_digest"][:16],
    )

    print(
        "Tag latest:",
        tags["latest"][:16],
    )

    print(
        "Credentials account:",
        credentials["account"],
    )

    deployment_record = (
        ROOT
        / "ci"
        / "last-deploy.json"
    )

    if deployment_record.exists():
        print(
            "Last deployment:",
            read(deployment_record),
        )

    for environment in (
        "production",
        "staging",
    ):
        runtime = read(
            ROOT
            / "environments"
            / f"{environment}.json"
        )

        database = (
            ROOT
            / "databases"
            / f"{environment}.sqlite"
        )

        with sqlite3.connect(
            database
        ) as db:
            columns = [
                row[1]
                for row in db.execute(
                    "PRAGMA table_info(bookings)"
                )
            ]

        print(
            environment,
            "runtime_digest=",
            runtime["running_digest"][:16],
            "columns=",
            columns,
            "probe=",
            probe(environment),
        )


def forward_fix():
    database = (
        ROOT
        / "databases"
        / "production.sqlite"
    )

    with sqlite3.connect(
        database
    ) as db:
        columns = [
            row[1]
            for row in db.execute(
                "PRAGMA table_info(bookings)"
            )
        ]

    if "contact_email" not in columns:
        raise SystemExit(
            "Expected migrated schema."
            " Run schema scenario first."
        )

    write(
        ROOT
        / "environments"
        / "production.json",
        {
            "running_digest": blob("D"),
            "deployment_status":
                "forward-fix-success",
        },
    )

    print(
        "Forward fix:",
        probe("production"),
    )


COMMANDS = {
    "init": init,
    "artifact": artifact,
    "target": target,
    "schema": schema,
    "inspect": inspect,
    "forward-fix": forward_fix,
}


if __name__ == "__main__":
    if (
        len(sys.argv) != 2
        or sys.argv[1] not in COMMANDS
    ):
        raise SystemExit(
            "Usage: python studio.py "
            + "|".join(COMMANDS)
        )

    COMMANDS[sys.argv[1]]()
```

The implementation deliberately uses synthetic artifact content and credential labels. It does not authenticate to a real registry or cloud provider.

The test script uses the artifact's declared database column to perform a genuine SQL query against the local SQLite database.

That makes the compatibility failure observable rather than merely reported through a hardcoded status flag.

---

# Incident A — CICD-01: Wrong Artifact, Successful Deployment

## Starting symptom

The release system approves commit B.

The build job produces and tests artifact B.

Production continues running artifact A.

The deployment job reports success.

### Step A1 — Initialize

Run:

```bash
python studio.py init
```

Inspect the generated files.

The build metadata is stored under `release-room/ci/`.

The simulated registry contains content-addressed artifacts and mutable tags.

The environment records identify currently running digests.

### Step A2 — Form a hypothesis

Before triggering the deployment, inspect:

`release-room/ci/build.json`

`release-room/registry/tags.json`

What artifact was approved?

What artifact does `latest` reference?

Are those the same?

### Step A3 — Reproduce

Run:

```bash
python studio.py artifact
```

Then inspect the system:

```bash
python studio.py inspect
```

### Task A4 — Explain the result

The deployment command reports success.

Production remains on application version 1.0.0.

The tested artifact corresponds to version 1.1.0.

Find the first identity mismatch.

### Required correction

Describe how the deployment should select the immutable digest from the verified build rather than resolving a mutable tag.

Your answer must distinguish:

- Fixing the build.
- Fixing artifact selection.
- Verifying runtime identity.

### Acceptance criteria

You identify the wrong artifact without rebuilding.

You demonstrate the exact provenance mismatch.

You can explain why a deployment job can succeed while delivering the wrong version.

---

# Incident B — The Wrong Environment

## Starting symptom

The intended artifact is correct.

The deployment job reports success.

Production remains unchanged.

Staging unexpectedly runs the new version.

### Step B1 — Reset

Run:

```bash
python studio.py init
```

### Step B2 — Reproduce

Run:

```bash
python studio.py target
python studio.py inspect
```

### Task B3 — Investigate the target

Inspect:

`release-room/ci/credentials.json`

`release-room/ci/last-deploy.json`

`release-room/environments/production.json`

`release-room/environments/staging.json`

Which environment was intended?

Which environment did the synthetic credentials select?

Which environment actually changed?

### Task B4 — Explain the failure

Why did the deployment command return success?

Why doesn't the job's stated intention establish where the operation occurred?

### Required correction

Design a deployment preflight that checks expected target identity against the authenticated environment.

It must fail before mutation if the identities disagree.

In a real platform, extend the check to cloud account, region, cluster, namespace, and target service.

### Acceptance criteria

You distinguish the deployment's intention from the actual authenticated target.

You can explain why environment variables and job names are insufficient safeguards.

---

# Incident C — RELEASE-01: The Rollback That Made Things Worse

## Starting symptom

A database migration renames the email column.

Application v2 understands the new schema but contains an unrelated business defect.

The deployment system rolls back to application v1.

The old application cannot read the migrated database.

### Step C1 — Reset

Run:

```bash
python studio.py init
```

### Step C2 — Predict

Before running the scenario, answer:

What database column does application A require?

What database column does application C require?

What happens if the database exposes only the latter?

Does restoring the old image restore the old database schema?

### Step C3 — Reproduce

Run:

```bash
python studio.py schema
```

Then:

```bash
python studio.py inspect
```

The simulation performs three actions.

First, it executes a real SQLite column rename.

Second, it deploys application C, which reads the new column but has a simulated business regression.

Third, it restores application A, whose code still expects the old column.

### Task C4 — Read the failure

The resulting error should identify that `guest_email` is missing.

Explain the sequence.

Why did the application rollback technically succeed?

Why did the business operation fail afterward?

Which release boundary was violated?

### Task C5 — Choose a recovery

Would you immediately reverse the schema rename?

Or would you deploy a corrected application compatible with the current schema?

What evidence should determine the decision?

### Step C6 — Test forward recovery

Run:

```bash
python studio.py forward-fix
python studio.py inspect
```

The simulator deploys application D, which understands the new column and doesn't contain the simulated business defect.

The production business probe should pass.

### Important qualification

This is a simplified compatibility example.

In a real release, a forward fix requires its own tests, approval, artifact provenance, and deployment verification.

It is not automatically safe merely because its version number is higher.

### Acceptance criteria

You explain why restoring a previous application image may not restore a compatible system.

You distinguish application rollback from schema reversal.

You demonstrate one working forward-recovery path.

---

# Incident D — Design the Safe Migration

## Starting requirement

Move customer contact information from `guest_email` to `contact_email`.

Old and new application instances may coexist during a rolling deployment.

The old application reads and writes the old field.

The new application eventually reads and writes the new field.

### Task D1 — Design the expansion

Instead of immediately renaming the column, add `contact_email` while keeping `guest_email`.

On a disposable SQLite database, the basic data expansion could begin with these statements.

```sql
ALTER TABLE bookings
ADD COLUMN contact_email TEXT;

UPDATE bookings
SET contact_email = guest_email
WHERE contact_email IS NULL;
```

These statements establish a historical copy.

They do not by themselves solve concurrent write synchronization.

### Task D2 — Define the write contract

Suppose the old application updates `guest_email` after the backfill.

The new application reads `contact_email`.

What happens?

Design a compatibility release or another controlled mechanism that keeps the representations consistent during the transition.

### Task D3 — Define the cutover

Specify the sequence for:

1. Expanding the schema.
2. Deploying compatible writers.
3. Backfilling historical records.
4. Eliminating incompatible writers.
5. Reconciling data.
6. Switching reads.
7. Validating the new invariant.
8. Retiring the old column.

### Task D4 — Define the rollback window

At which point can v1 no longer be safely restored?

What conditions must be met before reaching that point?

### Acceptance criteria

Your migration supports mixed-version deployment.

It doesn't rely on a one-time backfill while incompatible writers remain active.

It identifies the deliberate point when backward compatibility is retired.

---

# Incident E — The Terraform Target Mismatch

## Starting symptom

A deployment pipeline runs a Terraform operation.

The job is labeled production.

But its state backend or provider credentials refer to a different environment.

The resulting infrastructure changes may not correspond to the approved release.

This incident is conceptual rather than executed by the Python simulator.

### Investigation packet

The release approval expects:

- Production infrastructure.
- The approved Terraform configuration revision.
- The production state backend.
- The production provider account.
- A specific reviewed plan.

The execution environment reports:

- Workspace `production`.
- Provider credentials associated with staging.
- A saved plan from another pipeline run.

### Task E1 — Rank the problems

Which facts establish target identity?

Which are merely descriptive labels?

Why can a workspace named production coexist with staging credentials?

### Task E2 — Inspect the saved plan

What configuration and backend context was captured when the plan was created?

Why shouldn't it be applied casually in another environment?

### Task E3 — Design containment

What should happen before any further `terraform apply`?

### Task E4 — Recovery

If an apply partially changed the wrong environment, how would you determine which resources changed?

Why shouldn't you simply rerun the old plan?

### Acceptance criteria

You understand that Terraform state identity and provider target identity are separate.

You recognize that saved plans can be sensitive and context-specific.

You can reason about partial infrastructure changes.

---

# Incident F — The Release Race

## Starting symptom

Pipeline A contains an older application revision.

Pipeline B contains a newer application revision.

B deploys first.

A deploys afterward.

The production application moves backward.

Both pipelines report success.

### Task F1 — Reconstruct the sequence

Why can pipeline completion order differ from source revision order?

### Task F2 — Prevent unintended regression

Design controls that serialize conflicting deployments and prevent stale candidate releases from automatically replacing newer approved releases.

### Task F3 — Preserve legitimate rollback

How would an authorized rollback differ from an accidental stale deployment?

### Task F4 — Translate across platforms

Explain the relevant capabilities conceptually in:

- Jenkins.
- GitHub Actions.
- GitLab CI.

You don't need to memorize vendor-specific syntax for every mechanism.

### Acceptance criteria

You distinguish concurrency control from release-order authorization.

You understand why simply serializing jobs isn't always sufficient.

---

# Integrated Incident — The Broken Thursday Release

## Business context

A hotel-booking service is undergoing a release that includes:

- A payment reconciliation bug fix.
- A new application image.
- Terraform-managed infrastructure changes.
- A database email-column migration.
- A rolling Kubernetes deployment.

## Incident symptoms

The CI/CD pipeline reports success.

The registry contains the expected image.

Production runs an unexpected version.

A deployment target mismatch is suspected.

The database schema has changed.

An attempted application rollback causes SQL errors.

## Required incident report

Prepare a concise report with the following sections.

### Business impact

Which customer-facing operations are broken?

Are reads or writes affected?

Is there a risk of incorrect persistent data?

### Approved release

Identify the intended source revision, artifact, environment, infrastructure plan, and schema contract.

### Observed state

Which artifact actually runs?

Where did deployment actions occur?

What schema is present?

Which application versions are compatible with it?

### Causal reconstruction

Identify independent failure mechanisms rather than combining them into one vague deployment error.

### Immediate containment

Explain which operations should pause and how further uncontrolled changes would be prevented.

### Recovery decision

Choose a compatible artifact and schema combination.

Explain whether backward rollback or forward recovery is safer.

### Verification

Describe checks proving that the intended artifact is running in the correct environment and that the affected business workflow succeeds.

### Prevention

Recommend specific controls for artifact selection, target verification, migration compatibility, and deployment ordering.

## Interviewer challenge

Your interviewer says:

"The deployment system reports success. The image rollback reports success. Terraform reports success. Why are you calling the release a failure?"

Your answer should explain that all three systems may have completed their local operations while the combined application, infrastructure, and data state failed the business contract.

---

# STOP — End of Independent Studio

Do not read the following diagnostic notes until after attempting the investigations.

The objective is to reconstruct the evidence chain without being handed the root causes.

---

# Diagnostic Notes and Reference Solutions

## Incident A — Wrong Artifact

The CI build expects artifact B.

The registry's mutable `latest` tag points to artifact A.

The deployment resolves `latest` to A and successfully runs it.

The first broken boundary is artifact selection, not source checkout or compilation.

A verified immutable digest should be propagated from the approved build into deployment.

## Incident B — Wrong Environment

The intended target is production.

The simulated credential context selects staging.

The deployment succeeds in staging because that is where the operation was actually sent.

The correction is an enforced preflight that compares approved and authenticated environment identities before mutation.

## Incident C — Incompatible Rollback

The migration renamed `guest_email` to `contact_email`.

Application C understands the new schema but has a simulated business regression.

The rollback restores application A, which still expects `guest_email`.

The image rollback succeeds, but the database query fails.

A corrected application compatible with the migrated schema restores service in the controlled simulation.

## Incident D — Safe Schema Evolution

The correct migration introduces a compatibility period.

The new column is added while the old one remains.

Compatible writers maintain both representations.

Historical data is backfilled and reconciled.

Read paths switch only when data is ready.

The old representation is removed after obsolete consumers and rollback requirements have ended.

## Incident E — Terraform Identity

A workspace name doesn't guarantee provider-account isolation.

A saved plan carries context from its creation.

Before applying, verify state, backend, provider identity, approved plan, and real target.

A partial apply requires current-state investigation before recovery.

## Incident F — Release Ordering

Two independently successful pipelines can complete in the wrong order.

A deployment system needs serialization where appropriate and stale-release rejection.

Intentional rollback should remain an explicit, authorized operation.

## Integrated Recovery

A strong recovery establishes the real artifact, environment, schema, and runtime state before intervening.

It avoids blindly repeating deployment or migration commands.

It restores a compatible application/database combination, verifies the actual business operation, and implements controls that address the distinct failure boundaries.

---

# Further Reading

1. **Jenkins — Pipeline**  
   https://www.jenkins.io/doc/book/pipeline/

2. **GitHub Actions — Workflow Artifacts**  
   https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts

3. **GitHub Actions — Secure Use**  
   https://docs.github.com/en/actions/reference/security/secure-use

4. **GitLab CI — Deployment Safety**  
   https://docs.gitlab.com/ci/environments/deployment_safety/

5. **GitLab CI — Resource Groups**  
   https://docs.gitlab.com/ci/resource_groups/

6. **Terraform — Backend Configuration**  
   https://developer.hashicorp.com/terraform/language/backend

7. **Terraform — State Storage and Locking**  
   https://developer.hashicorp.com/terraform/language/state/backends

8. **Terraform — Plan Command**  
   https://developer.hashicorp.com/terraform/cli/commands/plan

9. **PostgreSQL — ALTER TABLE**  
   https://www.postgresql.org/docs/18/sql-altertable.html

10. **Kubernetes — Deployments**  
    https://kubernetes.io/docs/concepts/workloads/controllers/deployment/

11. **Kubernetes — Update a Deployment**  
    https://kubernetes.io/docs/tasks/run-application/update-deployment-rolling/

Cross-reference SE360-L01 for CI/CD and artifact provenance, SE360-L02 for Terraform state and target identity, CS350-L04 for database migration safety, SE340-L04 for delivery foundations, and `production-cases/CICD-01.md` and `RELEASE-01.md` for the related incident packets.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text
SE360-L03 — THE BROKEN RELEASE STUDIO
================================================

THE COMPLETE RELEASE CONTRACT
-----------------------------
Approved source
    ↓
Verified build
    ↓
Immutable artifact
    ↓
Authorized target
    ↓
Infrastructure state
    ↓
Compatible database schema
    ↓
Running application
    ↓
Verified business operation

LOCAL SUCCESS != GLOBAL SUCCESS
-------------------------------
Build passed:
  source compiled/tests passed

Image pushed:
  registry accepted artifact

Terraform applied:
  infrastructure operations completed

kubectl apply succeeded:
  desired configuration submitted

Rollout succeeded:
  workload reached rollout criteria

Business succeeded:
  intended operation actually works

These are different claims.

ARTIFACT IDENTITY
-----------------
Commit SHA:
  source revision

Image digest:
  content identity

Mutable tag:
  movable reference

Use verified digests for promotion.

TARGET IDENTITY
---------------
Verify actual:
- cloud account/project
- region
- cluster
- namespace
- service
- Terraform backend/state

A job name is not proof.

TERRAFORM
---------
Configuration != state != reality.

Saved plans carry backend context.
State locking prevents competing writers.
Partial applies may change real resources.

Do not blindly rerun after failure.

DATABASE COMPATIBILITY
----------------------
Old app expects old schema.
New app expects new schema.

Application rollback does not
automatically reverse database state.

Expand
Migrate
Contract

Maintain compatibility throughout
mixed-version deployment and rollback
windows.

ROLLBACK
--------
Backward rollback:
  restore earlier compatible state

Forward recovery:
  correct new version while preserving
  current schema/data

Choose by evidence.

KUBERNETES
----------
Check:
- desired image digest
- rollout progress
- Pod readiness
- running image identities
- mixed-version replicas
- business smoke tests

Readiness is not exhaustive
business verification.

RELEASE RACE
------------
Older pipeline may finish last.

Serialization helps.
Stale-release rejection also needed.

Intentional rollback must be explicit.

INCIDENT TRIAGE
---------------
1. Establish business impact.
2. Freeze uncontrolled changes.
3. Identify approved release.
4. Identify actual artifact.
5. Verify actual target.
6. Inspect schema/data compatibility.
7. Inspect runtime state.
8. Choose safe recovery.
9. Verify business operation.
10. Prevent recurrence.

THREE CLASSIC FAILURES
----------------------
CICD-01:
  correct build, wrong artifact

ENVIRONMENT MISMATCH:
  correct artifact, wrong target

RELEASE-01:
  rollback image incompatible
  with migrated schema

ANTI-PATTERNS
-------------
"Pipeline green means deployed."
"latest must be newest."
"Job name proves production."
"Terraform apply success means healthy."
"kubectl apply means Pods are ready."
"Ready Pods mean business is correct."
"Rollback image and everything is fixed."
"Reverse the migration immediately."
"Rerun the failed plan blindly."
"All deployment pipelines can overlap."

FINAL MENTAL MODEL
------------------
What did we intend?
What did we build?
What did we deploy?
Where did it go?
What is running?
What data does it expect?
What recovery is safe?

Verify the complete system.

SE360 COMPLETE
--------------
L01: CI/CD artifact forensics
L02: Terraform operational forensics
L03: Integrated broken-release studio
```
