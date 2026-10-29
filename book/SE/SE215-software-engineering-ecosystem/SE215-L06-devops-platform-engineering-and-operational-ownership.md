---
id: SE215-L06
course: SE215
title: "DevOps, Platform Engineering, and Operational Ownership"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE215-L05
next: SE215-L07
---


# SE215 — The Software Engineering Ecosystem

## Lecture 06: DevOps, Platform Engineering, and Operational Ownership

*The deployment pipeline is green. Kubernetes reports six healthy application pods. The load balancer is routing traffic correctly. Yet customers cannot complete a reservation. Developers insist the deployment succeeded. Platform engineers insist the cluster is healthy. Who is responsible for the broken product?*

---

# Part I — Intuition

## The picture to carry in your head

Imagine Mercury, our hotel-booking company, is preparing a new release.

The frontend has been updated. The Node.js API includes new reservation logic. PostgreSQL needs a schema change. Several Python workers consume events produced by the API.

The developers finish their changes and open pull requests.

The tests pass.

A build pipeline creates new container images.

A deployment system updates the running workloads.

Kubernetes reports that the new application instances are available.

Everyone congratulates themselves.

Then customer support receives a message:

"I've tried to change my reservation dates three times. The page says something went wrong."

The support team contacts engineering.

Developers inspect their logs. The requests reach the API, but something fails during database access.

The platform engineer checks Kubernetes.

All pods are running.

CPU usage is normal.

The network appears healthy.

The database administrator reports that PostgreSQL is reachable.

Every subsystem looks reasonable from its owner's perspective.

Nevertheless, the product is broken.

What happened?

The application release expected a database column that had not been introduced safely for the versions currently running.

The health endpoint checked only whether the HTTP process could respond.

It didn't prove that the reservation workflow was compatible with the database.

The deployment system performed its job.

But the complete business system didn't.

This is the sort of problem that motivates modern approaches to DevOps, platform engineering, and site reliability.

**The engineering challenge is not merely to automate deployment. It's to create a delivery and operating system in which software can be changed safely and failures can be understood and repaired.**

## 1. Four related ideas, four different responsibilities

Let's distinguish several terms that frequently appear together.

**DevOps** describes practices and organizational principles that connect software development with the work of delivering and operating software.

**Infrastructure engineering** provides and maintains foundational computing capabilities: networks, compute resources, storage, identity systems, and related infrastructure.

**Platform engineering** creates reusable internal capabilities that let application teams develop, deploy, and operate software with less repetitive infrastructure work.

**Site Reliability Engineering**, or SRE, applies software-engineering methods to reliability, operations, automation, and managing production risk.

These ideas overlap.

A company might have a platform team that also performs SRE work.

An employee titled DevOps Engineer might spend most of their time writing Terraform.

A small startup might assign all these responsibilities to two full-stack developers.

The job title doesn't tell us exactly how the work is divided.

We need to examine the responsibilities.

## 2. DevOps is not a department at the end of the pipeline

An older organizational model treated development and operations as largely separate groups.

Developers wrote software.

Operations deployed it.

When something broke, the groups argued about whose fault it was.

That division created poor incentives.

Developers could optimize for shipping code without considering operating consequences.

Operations could optimize for minimizing changes because changes introduce risk.

DevOps attempts to improve that relationship through shared goals, automation, feedback, and cooperation.

The point is not that every developer must personally configure every router and database.

It's that software delivery and operation cannot be treated as unrelated activities.

A backend developer must understand how their application starts, fails, scales, logs, and shuts down.

An infrastructure engineer must understand enough about application requirements to provide useful operating capabilities.

Neither needs to become an expert in the other's entire profession.

## 3. Platform engineering: build the road, don't drive every car

Now imagine Mercury grows to fifty engineering teams.

Each team needs a container registry, deployment pipeline, secrets, databases, service monitoring, and a way to create test environments.

Should every team independently invent these capabilities?

That would create enormous duplication.

Should every deployment require opening a ticket and waiting for an infrastructure engineer to perform it manually?

That would create a bottleneck.

A platform team can provide a reusable path.

For example, developers might create a new service from a template.

The template includes a sensible project structure, build pipeline, deployment configuration, identity setup, logging conventions, and basic health checks.

The developer still implements the service.

The platform makes the routine infrastructure work easier.

This is often called a **golden path** or **paved road**.

The objective is to make a safe, maintainable way of working the convenient default.

A good platform reduces cognitive load without preventing developers from understanding or investigating their systems.

## 4. SRE: reliability as an engineering discipline

Now imagine Mercury's application is growing rapidly.

Customers use it around the clock.

A database outage can interrupt reservations.

An incorrect deployment can produce thousands of failed requests.

The company needs explicit expectations for service reliability and methods for improving it.

An SRE team may help define measurable service-level objectives, build monitoring and alerting systems, improve incident response, and automate repetitive operational work.

SRE is particularly concerned with the relationship between reliability, change, and operational risk.

A system cannot be made perfectly reliable at any reasonable cost.

The organization must decide what level of reliability the product requires.

Then engineering can manage that objective.

This is different from simply keeping servers powered on.

A server can be available while its application returns incorrect results.

## 5. The entire delivery path matters

Let's summarize Mercury's release.

```text
Source code
    |
    v
Build and test
    |
    v
Immutable artifact
    |
    v
Deployment configuration
    |
    v
Running application
    |
    v
Production verification
    |
    v
Customer outcome
```

Different specialists may own different parts of this process.

But if the final customer outcome is wrong, success in the earlier stages isn't sufficient.

The organization needs a way to understand the entire chain.

That brings us to the Deep Dive.

### Three questions before the Deep Dive

1. Why can an automated deployment system complete successfully while the application is still broken?
2. What is the difference between a platform team providing a deployment capability and an application team owning the behavior of a deployed service?
3. Why is a service being reachable not the same thing as meeting a reliability objective?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. A release is more than moving files to production

Let's reconstruct Mercury's failed release.

A developer changes the reservation model.

The previous application stores a booking status in one field.

The new application expects an additional field describing the progress of date-change operations.

The team writes a database migration and merges the code.

CI builds the application and executes its test suite.

A container image is published.

The deployment pipeline updates the application instances.

Everything appears successful.

But the schema migration and the application rollout weren't designed as one compatible sequence.

Some application instances start using the new field before the database is ready.

The health endpoint still returns success because it checks only that the process can serve HTTP requests.

The deployment completes.

Customers receive errors.

This incident exposes several separate responsibilities.

The application team owns the software's assumptions about the schema.

The deployment system controls when application artifacts are introduced.

The database migration mechanism changes persistent state.

The monitoring system should reveal whether the release has harmed actual service behavior.

No single status indicator establishes that all four are compatible.

## 2. CI, CD, infrastructure management, and runtime operations

These activities are frequently grouped under "DevOps," but they do different jobs.

### Continuous Integration

Continuous Integration is the practice of integrating changes frequently and verifying the integrated code through automated feedback.

The automation may compile TypeScript, run tests, perform static analysis, and build artifacts.

A green CI result means the configured checks passed for the tested revision and environment.

It doesn't prove the production deployment will be healthy.

### Continuous Delivery and deployment

Continuous Delivery seeks to keep software in a state where it can be released safely and routinely.

Continuous Deployment goes further by automatically deploying changes that satisfy the required pipeline.

Neither term refers merely to having a deployment script.

The broader capability depends on testing, release compatibility, automation, and recovery.

### Infrastructure as Code

Infrastructure as Code describes infrastructure through version-controlled configuration rather than relying entirely on manual changes.

Terraform is one implementation.

It can manage cloud resources, permissions, networking, and other infrastructure.

But Terraform doesn't ordinarily build the application's business logic or decide whether the latest reservation workflow is correct.

### Runtime operations

Once the application is running, someone must monitor it, investigate failures, manage capacity, respond to incidents, and maintain its reliability.

These responsibilities continue long after the deployment pipeline turns green.

Our SE340-L04 lecture explores CI/CD, releases, and Terraform in depth.

Here we're concerned with how those capabilities fit together organizationally.

## 3. The artifact and the environment

Suppose Mercury builds a container image for the Node.js API.

The image contains the application code and its runtime dependencies.

Ideally, the same identifiable artifact can be tested and promoted through environments rather than rebuilt differently for every stage.

But the artifact isn't the complete deployed system.

Its behavior also depends on environment configuration.

The production application may use a different database, secrets, API endpoints, feature flags, network rules, and resource limits from the test environment.

### Configuration drift

Imagine staging has a database connection pool of ten connections.

Production has fifty.

That difference may be deliberate.

But suppose staging also uses an old environment variable name, while production uses the new one.

Now a test that passes in staging may fail to represent production behavior.

Configuration drift becomes dangerous when environments diverge unintentionally.

The goal isn't to make all environments identical.

Their security, scale, and operational requirements may differ.

The goal is to understand and control the differences that matter.

### Who owns configuration?

The platform team may define how configuration is supplied to workloads.

The application team must document which configuration values its software requires and how invalid values should be handled.

Security specialists may govern how secrets are stored and accessed.

These are complementary responsibilities.

A platform cannot infer every application-specific requirement.

And developers shouldn't invent insecure mechanisms for retrieving secrets simply because the platform interface is unfamiliar.

## 4. GitOps: declared state is not application correctness

Mercury uses Kubernetes.

Its desired deployment configuration lives in Git.

A GitOps controller observes that configuration and reconciles the cluster toward it.

For example, the repository says the booking API should run a particular container image with six replicas.

The controller applies the relevant resource changes.

Kubernetes controllers then attempt to establish the requested runtime state.

This is valuable because deployment intent is versioned, reviewable, and continuously compared against the running infrastructure.

But notice the boundary.

GitOps can establish that the cluster is configured to run the specified application.

It cannot automatically determine whether the new application's reservation calculations are correct.

Nor does reverting a Kubernetes manifest automatically reverse a database migration or undo payments already processed.

### The emergency-change trap

Suppose an engineer manually modifies a Kubernetes resource during an incident.

The application improves temporarily.

Then the GitOps controller restores the configuration declared in Git.

The manual fix disappears.

Was the controller broken?

No.

It was following its reconciliation policy.

The team needs a documented incident procedure that accounts for the authoritative configuration and any emergency overrides.

That is one reason platform procedures matter alongside technical tools.

## 5. Health checks answer particular questions

Our failed release had six healthy pods.

What did that actually mean?

Kubernetes supports several kinds of probes.

A **startup probe** can help determine whether an application has completed the startup process sufficiently for normal probe handling.

A **liveness probe** helps determine whether a container should be restarted because it is no longer functioning properly.

A **readiness probe** helps determine whether a container should receive normal service traffic.

These are different questions.

### The dangerous liveness check

Suppose Mercury's liveness endpoint checks whether PostgreSQL is reachable.

PostgreSQL experiences a brief outage.

Every application instance begins failing liveness checks.

Kubernetes starts restarting the application containers.

Now the database recovery is accompanied by widespread application restarts and potentially a new connection surge.

That's not necessarily helpful.

A shared dependency failure shouldn't automatically be treated as proof that every application process is irrecoverably broken.

### The useful readiness check

Readiness may consider whether the application can meaningfully serve the traffic it's about to receive.

But readiness itself must be designed carefully.

A health endpoint shouldn't execute expensive database operations on every probe.

And a dependency outage doesn't always mean every application capability is unusable.

Perhaps hotel search can continue while reservation creation is unavailable.

The team needs to decide what "ready" means for the actual traffic and service architecture.

Most importantly, even a well-designed readiness check cannot prove that every business workflow works.

Production verification needs separate signals.

## 6. Internal developer platforms: self-service with guardrails

Let's return to Mercury after several years of growth.

The company now operates dozens of services.

Developers repeatedly ask the platform team to create databases, provision environments, configure deployments, and grant service identities.

The platform team becomes overwhelmed with tickets.

This is where an internal developer platform becomes attractive.

A platform team can provide self-service capabilities such as:

- Creating a new service from a maintained template.
- Provisioning approved infrastructure.
- Building and deploying applications through standardized pipelines.
- Managing environment configuration and secrets.
- Accessing logs, metrics, and traces.
- Discovering service ownership and documentation.
- Applying approved security and operational policies.

The interface might be a web portal, CLI, repository template, or API.

### Platform versus portal

An internal developer platform is the underlying collection of capabilities and abstractions.

An internal developer portal is often an interface through which developers discover and use those capabilities.

The portal isn't automatically the entire platform.

A beautiful dashboard does little good if creating a database still requires fourteen manual approval steps and several days of waiting.

### Platform as a product

Good platform engineering uses a product mindset.

The users are other developers.

The platform team should understand where those developers lose time, which workflows are repeated, and what capabilities they actually need.

It should measure whether its services improve delivery.

A platform that introduces more configuration files and approval requirements than it removes has not necessarily improved developer experience.

## 7. Golden paths should reduce decisions, not eliminate judgment

Imagine a developer wants to introduce a new Node.js API.

Without a standard workflow, they must decide how to structure the repository, build the container, configure CI, create Kubernetes resources, provision secrets, implement logging, and deploy.

An internal golden path provides a recommended starting point.

The developer creates a service from a template.

The template includes sensible defaults.

There is a standard process for requesting resources, deploying changes, and observing the application.

This saves time and reduces inconsistency.

But it has a danger.

If the platform hides too much, developers may lose the ability to diagnose their systems.

For example, a developer might know only that pressing "Deploy" creates a running service.

When the service cannot reach PostgreSQL, they have no understanding of networking, credentials, or connection configuration.

A well-designed platform should reduce routine complexity while preserving access to the underlying information needed for troubleshooting.

The paved road should be convenient, not compulsory for every unusual case.

## 8. SRE: reliability objectives and operational risk

Now Mercury wants explicit reliability guarantees.

The business asks for a highly available reservation service.

An SRE-minded approach begins by defining what availability means from the customer's perspective.

Suppose a customer successfully loading the home page isn't enough.

A critical user journey might require searching for a room, beginning a reservation, and receiving a reliable confirmation.

The team must choose useful service-level indicators, or SLIs.

An SLI is a measurement of service behavior.

A service-level objective, or SLO, defines a desired target for that measurement.

For example, Mercury might aim for a certain proportion of valid reservation requests to complete successfully within an agreed time window.

The exact target should reflect product requirements and the cost of failure.

### Error budgets

If the organization chooses an SLO below perfect reliability, it implicitly accepts some amount of failure.

The difference between the objective and perfect reliability is often discussed as an error budget.

An error budget can inform the balance between introducing changes and investing in stability.

If the service is repeatedly missing its reliability objective, the team may need to prioritize corrective work over additional risky releases.

But this isn't a universal mathematical rule that automatically dictates every product decision.

It's a framework for discussing reliability as a managed business constraint.

### Toil

SRE also emphasizes reducing repetitive operational work.

Imagine a team spends hours every week manually restarting a known-bad worker process and clearing a temporary queue.

If that activity is repetitive, manual, and grows with the size of the system, it may represent operational toil.

The better long-term solution may involve fixing the worker's failure mechanism, improving automation, or redesigning the workflow.

A team that spends all its time performing manual recovery has less capacity to improve reliability.

## 9. Who should be on call?

This is one of the most consequential organizational choices.

Suppose the booking API fails at midnight.

Who receives the alert?

The developer who wrote the code?

The platform engineer who owns Kubernetes?

The SRE team?

A shared operations group?

There isn't one universally correct answer.

Different organizations divide on-call responsibilities differently.

But the divisions must be explicit.

### Service ownership

A useful model gives the application team responsibility for the business behavior and health of its service.

That includes maintaining appropriate runbooks, dashboards, and understanding common failure modes.

The platform team owns the shared infrastructure and deployment capabilities it provides.

The SRE organization may support reliability strategy, incident response, and selected service operations.

These responsibilities can overlap during incidents.

The critical requirement is that a failure doesn't disappear into the gap between ownership boundaries.

### Why on-call changes engineering behavior

If developers never observe production failures, they may underestimate the operational cost of their design choices.

A seemingly harmless retry loop might generate enormous downstream load.

An overly verbose log statement may create substantial telemetry costs.

A background worker may be difficult to shut down safely.

Seeing those consequences can improve engineering decisions.

But on-call must also be sustainable.

A company that routinely requires developers to work overnight without proper staffing, compensation arrangements, or operational support hasn't automatically embraced DevOps.

It may simply have created an unhealthy operating model.

## 10. The incident: Kubernetes is green, customers are failing

Let's reconstruct our opening incident as a realistic collaboration.

Mercury deploys version 4.8 of its reservation API.

The new API expects a database column that isn't present in the production schema.

The deployment completes.

Readiness probes pass because they check only an HTTP endpoint.

Reservation modifications begin failing.

### Step one: detect the real symptom

The monitoring system sees an increase in reservation-operation failures.

A product-level metric is more useful here than simply observing that all pods are running.

Customer support also reports the issue.

The incident is declared.

### Step two: contain the damage

The team evaluates whether the broken feature can be disabled or whether traffic should be returned to a compatible application version.

Any rollback must account for the current database schema and recent business operations.

The immediate objective is restoring safe behavior.

### Step three: identify the failing boundary

Application logs indicate a database error.

The application team checks whether the deployed code's schema assumptions match production.

The database team or responsible engineers examine migration status.

Platform engineers verify which image and configuration were deployed and whether the rollout process behaved as expected.

### Step four: decide on a compatible correction

The team might apply a safe additive schema migration if that is appropriate.

Alternatively, it may roll back the application code to a version compatible with the existing database.

The right choice depends on the actual state and migration design.

The response should avoid making the situation worse through untested manual changes.

### Step five: verify customer behavior

Once a correction is applied, the team does not stop at "pods healthy."

It verifies representative reservation operations.

It checks whether errors have returned to expected levels.

It monitors for additional consequences, such as queued retries or inconsistent operation states.

### Step six: improve the delivery system

The post-incident review asks why the failure was possible.

Perhaps the migration wasn't included in the release plan.

Perhaps old and new versions couldn't coexist safely.

Perhaps the health endpoint provided false confidence.

Perhaps release verification lacked a meaningful business-level check.

Several improvements may be appropriate.

But the objective isn't producing a hundred corrective-action tickets.

It's identifying the most important systemic changes.

## 11. The organizational anti-pattern: everyone owns their component, nobody owns the outcome

Imagine Mercury responds to the incident through blame.

Developers say the platform should have blocked the release.

Platform engineers say developers supplied the image.

The database team says the migration wasn't scheduled.

SRE says monitoring correctly raised an alert.

Everyone has a defensible explanation of their local responsibility.

Yet the organization failed to deliver a safe change.

This is the problem DevOps attempts to address.

Different teams need clear technical boundaries, but they also need shared responsibility for the delivery outcome.

### Accountability doesn't mean everyone does everything

The solution isn't requiring the platform engineer to inspect every SQL query or the backend developer to become an expert in Kubernetes internals.

The solution is establishing useful contracts.

The application team declares migration requirements and compatibility constraints.

The platform provides a deployment mechanism that supports safe sequencing and observable releases.

The database operations process provides suitable ways to apply and verify changes.

Reliability instrumentation exposes meaningful failures.

The organization agrees on who coordinates incidents and who can authorize potentially risky actions.

This preserves specialization while making the interfaces explicit.

### What the senior engineer contributes

A senior application engineer should understand enough infrastructure to recognize that "the pod is running" is not a correctness guarantee.

They should know what their application needs at startup.

They should understand how it handles termination and in-flight requests.

They should identify critical configuration and permissions.

They should participate in designing deployment-compatible migrations.

They should expose meaningful health and business metrics.

And they should know how to work with platform and SRE colleagues when things fail.

They don't need to personally maintain every cloud resource.

But they should not treat production as a mysterious destination beyond their responsibility.

---

# The Oral Examination

Answer aloud before reading the solutions.

### Question 1 — DevOps or DevOps engineer?

What is the difference between DevOps as an approach and a company employing someone titled DevOps Engineer?

### Question 2 — The platform team's role

A backend developer needs a new service, database, deployment pipeline, and monitoring. Which capabilities might an internal platform provide, and what remains the developer's responsibility?

### Question 3 — Health checks

Kubernetes reports that every pod is ready, but reservations are failing. Is Kubernetes necessarily wrong?

### Question 4 — CI/CD and GitOps

What's the difference between building and testing an artifact, declaring which version should run, and reconciling the cluster toward that declaration?

### Question 5 — Shared responsibility

A new application version expects a database field missing from production. How should responsibilities be divided between application, platform, and database operations?

### Question 6 — SRE and reliability

What's the difference between a service being reachable and meeting a meaningful service-level objective?

### Question 7 — Ownership during incidents

Two teams disagree about whether the incident belongs to application or platform engineering. What should happen first, and what organizational problem should be addressed afterward?

---

# Solutions and Discussion

## Solution 1 — Practices versus title

DevOps describes practices emphasizing collaboration, automation, and shared responsibility across development and operations.

A DevOps Engineer is a job title whose responsibilities vary by employer. The employee may specialize in CI/CD, infrastructure, cloud operations, or other capabilities.

The title alone doesn't establish the company's operating philosophy.

## Solution 2 — Platform provides capabilities, developers own behavior

The platform may provide templates, approved infrastructure, deployment automation, access to secrets, standard monitoring, and self-service workflows.

The application team still defines the service's API, business rules, dependency requirements, meaningful health behavior, and application-specific operational risks.

## Solution 3 — The probes may be doing exactly what they were designed to do

Readiness checks verify a specified condition.

They cannot automatically prove every business operation is correct.

If readiness merely checks that an HTTP process responds, it may pass while reservation operations fail.

The application needs additional production verification and meaningful service indicators.

## Solution 4 — Different stages of delivery

CI builds and verifies code and artifacts.

Deployment configuration describes what should run.

A GitOps controller compares that desired state with actual infrastructure and reconciles differences.

None of these mechanisms automatically proves business-level correctness.

## Solution 5 — A coordinated compatibility contract

The application team owns its schema assumptions and must define compatibility requirements.

Platform and deployment tooling should support safe rollout sequencing and observation.

Database operations should support applying migrations with appropriate controls.

All participants need agreement about release order, validation, and recovery.

## Solution 6 — Reliability must reflect customer outcomes

A reachable server may still return errors, incorrect results, or unacceptable latency.

Useful SLIs and SLOs should measure behavior relevant to the customer and product, not merely process availability.

## Solution 7 — Restore service before arguing about blame

Establish incident coordination, contain the failure, gather evidence, and involve whichever teams are needed.

After recovery, clarify ownership, escalation paths, and operational contracts.

The objective is preventing future failures from falling between responsibilities.

---

# The Mental Model Worth Keeping

When discussing DevOps, platform engineering, and SRE, distinguish four questions.

**Delivery:** How does a source-code change become a safe production release?

**Enablement:** Which shared capabilities make developers more effective and independent?

**Reliability:** How do we measure, operate, and improve the health of production services?

**Ownership:** Who understands and responds when the complete system fails?

DevOps connects development and operations through shared practices.

Platform engineering makes good engineering workflows reusable and accessible.

SRE develops methods for managing reliability and operational risk.

Application engineers remain responsible for the actual behavior of their software.

**A healthy engineering organization does not eliminate boundaries between specialties. It makes those boundaries explicit, cooperative, and difficult for important responsibilities to fall through.**

# Next Lecture — SE215-L07: Owning End-to-End Testing

Mercury's application is now deployed through a repeatable pipeline.

The platform is healthy.

Its logs and metrics are working.

The feature team's unit tests pass.

Then an ordinary customer tries to complete a reservation, and the workflow fails.

The frontend behaves correctly in isolation.

The backend tests pass independently.

But the browser, API, authentication, and database disagree when used together.

What should developers test themselves?

What should be mocked?

Which scenarios need real infrastructure?

And how do we avoid creating an enormous collection of flaky browser tests?

Next we'll examine how application developers can own meaningful end-to-end testing using Playwright and well-designed test environments.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Workshop — Design Mercury's Operational Responsibility Model

## Exercise A — Map the responsibilities

Mercury has four groups:

- Application engineering.
- Platform engineering.
- SRE/reliability engineering.
- Security engineering.

For each capability, identify a primary owner, relevant collaborators, and the interface between them.

| Capability | Questions to resolve |
|---|---|
| Container build | Who defines the image? Who provides reusable build tooling? |
| Deployment pipeline | Who maintains the mechanism? Who authorizes releases? |
| Database migration | Who writes it? Who executes and verifies it? |
| Service identity | Who provisions identities? Who requests and approves permissions? |
| Health probes | Who defines application semantics? Who configures the runtime checks? |
| Business metrics | Who defines meaningful measurements? Who provides instrumentation infrastructure? |
| Production alerts | Who sets thresholds? Who receives and acts on alerts? |
| Incident response | Who coordinates? Who investigates each subsystem? |
| Backups | Who configures and tests restoration? Who defines recovery requirements? |
| Rollback | Who can initiate it? What application-specific conditions make it safe? |

There is no universal table of answers.

The important outcome is that responsibilities are explicit and usable during normal work and emergencies.

## Exercise B — Review a broken release

Mercury's release process is:

```text id="t0d6qw"
Pull request merged
       |
       v
Build container
       |
       v
Run unit tests
       |
       v
Update deployment image
       |
       v
Wait for 6 Ready pods
       |
       v
Mark release successful
```

The next version introduces a new database field.

Propose an improved release workflow.

Include:

1. Schema compatibility requirements.
2. Artifact identity and configuration.
3. Appropriate integration testing.
4. Safe migration sequencing.
5. Controlled rollout.
6. Business-level verification.
7. Recovery decisions.

Explain why simply adding more pod replicas doesn't fix the original failure.

## Exercise C — Design useful health and reliability signals

Mercury has these application capabilities:

- Public hotel search.
- Reservation creation.
- Reservation modification.
- Background notifications.

Define which failures should make an API instance unready to receive normal traffic and which should trigger application-level alerts without necessarily removing it from service.

Then propose a few meaningful SLIs.

Possible examples include valid reservation-operation success rate, end-to-end reservation latency, and age of pending notification work.

Don't put every expensive dependency check into a high-frequency health endpoint.

## Exercise D — GitOps and emergency operations

Suppose a Kubernetes configuration is managed by a GitOps controller.

During an incident, an engineer manually changes an environment variable on a Deployment.

The application appears to recover.

A short time later, the variable returns to its earlier value.

Explain why this might happen.

Then design an emergency-change procedure that preserves incident speed without fighting the configuration reconciliation system.

Consider how the change should be reviewed, recorded, applied, and later cleaned up.

## Exercise E — Senior interview rehearsal

Answer aloud:

"At your company, what should DevOps or platform engineers own, and what should application developers own?"

A strong response should distinguish shared infrastructure capabilities from application-specific behavior.

It should explain how those teams cooperate on deployment, configuration, observability, incidents, and security.

Avoid saying either that platform engineers own all of production or that every developer must personally operate everything.

---

# Further Reading

- **DORA — DevOps Capabilities:** https://dora.dev/capabilities/
- **DORA — Loosely Coupled Teams:** https://dora.dev/capabilities/loosely-coupled-teams/
- **CNCF — Platform Engineering Community:** https://contribute.cncf.io/community/tcgs/platform-engineering/
- **CNCF — Internal Developer Platforms:** https://www.cncf.io/blog/2023/12/08/internal-developer-platform-vs-internal-developer-portal-vs-paas/
- **Google — Site Reliability Engineering Book:** https://sre.google/sre-book/table-of-contents/
- **Google SRE — Eliminating Toil:** https://sre.google/sre-book/eliminating-toil/
- **Argo CD — How GitOps Reconciliation Works:** https://argo-cd.readthedocs.io/en/stable/
- **Kubernetes — Configure Liveness, Readiness and Startup Probes:** https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/

Related programme chapters:

- SE215-L01 — The People and Teams Behind Software
- SE215-L02 — How Engineering Work Gets Planned and Delivered
- SE215-L05 — Cloud Platforms and Service Models
- SE215-L07 — Owning End-to-End Testing
- SE340-L04 — CI/CD and Infrastructure as Code
- SE440-L01 — Observability: Understanding Production Systems
- SE440-L02 — Reliability Engineering and Incident Response
- SE450-L07 — Releases, GitOps, and Platform Observability

---

## Dense Cheatsheet — Interview Glance Card

*Fenced for TTS skipping and rapid screen revision.*

```text
SE215-L06 — DEVOPS, PLATFORM ENGINEERING, OPERATIONAL OWNERSHIP

FOUR QUESTIONS
  Delivery     How does code safely reach production?
  Enablement   How do teams receive reusable capabilities?
  Reliability  How do we measure and improve service health?
  Ownership    Who responds when the whole system fails?

DEVOPS
  Practices connecting development and operations
  Shared goals, automation, feedback, continuous delivery
  Not synonymous with one job title or tool

INFRASTRUCTURE ENGINEERING
  Networks, compute, storage, identity, base infrastructure
  May be distinct from or overlap with platform engineering

PLATFORM ENGINEERING
  Internal developer platform as a product
  Golden paths / paved roads
  Self-service environments, deploys, secrets, observability
  Reduce repetitive decisions and cognitive load
  Portal UI != entire platform
  Platform should allow investigation and escape hatches

SRE
  Software engineering applied to reliability and operations
  SLIs: measurements of service behavior
  SLOs: desired targets for those measurements
  Error budgets: managed reliability/change trade-off
  Toil: repetitive, operational work to reduce through engineering
  On-call, monitoring, incidents, capacity, automation

CI/CD
  CI: integrate frequently and verify changes
  Continuous Delivery: keep software safely releasable
  Continuous Deployment: automatically deploy qualifying changes
  Build success != deployment success != customer success

RELEASE PIPELINE
  Source -> tests -> immutable artifact -> declared config
         -> running app -> production verification
  Track deployed image, config and schema compatibility
  Rollback code may not reverse database/data changes

IAC / GITOPS
  IaC: version-controlled infrastructure definitions
  GitOps: reconcile actual environment toward declared state
  Controller correctness != business correctness
  Manual patches may be reverted by reconciliation
  Emergency changes need a defined procedure

HEALTH CHECKS
  Startup: has initialization completed sufficiently?
  Liveness: should a broken process/container restart?
  Readiness: should the instance receive normal service traffic?
  Ready pods != correct application behavior
  Avoid making shared dependency outages restart every service
  Business-level metrics and verification are separate

CONFIGURATION
  Artifact + configuration + dependencies = deployed behavior
  Staging differs from production; understand relevant differences
  Platform provides mechanisms; app defines required semantics
  Secrets need proper access and lifecycle controls

ON-CALL
  Explicit ownership, escalation, runbooks, incident coordination
  Application team owns behavior and business-specific signals
  Platform team owns shared platform capabilities
  SRE may partner on reliability and operations
  Sustainable rotation and support matter

FAILED DEPLOYMENT CASE
  API expects new DB column
  Pods healthy but booking operations fail
  Contain -> inspect compatibility -> correct -> verify business
  Improve migration sequencing and release verification
  Don't stop at green Kubernetes status

ANTI-PATTERNS
  "Works on my machine" as final evidence
  "Infrastructure is green" as proof of product health
  Platform tickets required for every trivial deployment
  Golden path hiding all diagnostic information
  Liveness dependent on every shared external system
  Unowned business-level monitoring
  Manual cluster patch that GitOps undoes
  Blame between teams instead of coordinated recovery

SENIOR INTERVIEW FRAMEWORK
  Clarify service ownership
  Separate platform capabilities from application behavior
  Explain deployment and config dependencies
  Define business-level success metrics
  State how incidents are coordinated
  Propose clear, practical responsibility boundaries

MENTAL MODEL
  Good DevOps makes delivery and operation cooperative.
  Good platforms make the safe path convenient.
  Good SRE makes reliability measurable and improvable.
  Good developers own what their software actually does.
```
