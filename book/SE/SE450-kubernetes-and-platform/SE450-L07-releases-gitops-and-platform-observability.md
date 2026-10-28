---
id: SE450-L07
course: SE450
title: "Releases, GitOps, and Platform Observability"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE450-L06
next: SE450-L08
---


<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE215-L06
Preserve Kubernetes-specific deployment controllers, Helm, GitOps reconciliation,
and progressive-delivery mechanics.
Cross-reference SE215-L06 for the wider DevOps/platform engineering organizational context.
Do not expand the SE215 lecture into another Kubernetes course.
-->





# SE450 — Kubernetes and Platform Engineering

## Lecture 07: Releases, GitOps, and Platform Observability

*The deployment succeeded. Every Pod is Ready. The release pipeline is green. Kubernetes has nothing to complain about. Unfortunately, your customers have stopped receiving the service they're paying for.*

---

# Part I — Intuition

## The picture to carry in your head

Imagine a cybersecurity platform that scans customers' internet-facing assets.

The architecture has an API, a RabbitMQ broker, and a fleet of scanner workers.

Customers submit domains through the API. The API validates each request, records a scan operation, and publishes a message that workers consume.

The workers execute scanning tools, discover exposed assets, and persist findings.

The system works.

Then the engineering team deploys version two of the API.

The update appears completely successful.

Kubernetes replaces the old API Pods with new ones. Every new Pod starts. Every readiness probe succeeds. The Deployment eventually reports that all replicas are updated and available.

The deployment pipeline displays a green checkmark.

Twenty minutes later, customer support starts receiving complaints.

Customers can submit scans, but the scans never finish.

The engineers investigate.

The new API publishes a modified message format. The existing workers still expect the previous format.

The messages reach RabbitMQ, but workers cannot process them correctly.

The HTTP API returns successful responses. Its Pods are healthy. Kubernetes sees no problem.

And Kubernetes is right—from its limited perspective.

The cluster successfully deployed the requested application version.

The application version is simply incompatible with the rest of the system.

**Infrastructure success and business success are different claims.**

This lecture is about the engineering required to connect them.

## 1. A successful rollout proves less than you think

Suppose a Deployment requests four API replicas.

After a rollout, Kubernetes observes four updated, available replicas and no old replicas remaining.

That's meaningful information.

It tells us that the Deployment controller reached its desired rollout state according to Kubernetes' availability semantics.

But what does it not tell us?

It doesn't prove that every API endpoint returns correct business results.

It doesn't prove that the database schema is compatible.

It doesn't prove that background workers understand newly published events.

It doesn't prove that payment processing works.

It doesn't prove that customers can complete their intended workflows.

Kubernetes can tell us that the declared machinery exists and is available according to the signals provided.

It cannot independently understand the entire business meaning of that machinery.

So we need two kinds of verification.

**Deployment verification:** Did the desired infrastructure change occur?

**Product verification:** Does the resulting application still perform its intended functions?

A mature release process checks both.

## 2. Readiness is not a complete acceptance test

Our API exposes a readiness endpoint.

When Kubernetes calls `/health/ready`, the application returns HTTP 200.

The API is listening, its initialization has completed, and it believes it can accept requests.

That's useful.

But the application has a bug in its message-publishing logic.

Should the readiness endpoint detect that?

Possibly, if the failure makes the instance fundamentally incapable of serving its declared purpose and can be detected reliably.

But not every application defect belongs in a readiness probe.

Imagine performing a full customer scan every five seconds just to determine whether an API Pod should remain in service.

That would be expensive, slow, and potentially destructive.

Readiness probes should provide efficient signals about whether a particular instance can serve traffic.

Full workflow verification belongs in broader release testing and production monitoring.

The distinction is:

**Readiness asks whether this instance is eligible to serve. Release verification asks whether the system still behaves correctly.**

Those questions overlap, but they are not identical.

## 3. Changing the software is not the same as changing the system

Our API and workers are separate applications.

They have separate container images, deployment schedules, and lifecycle decisions.

But they communicate through a message contract.

Version one of the API publishes messages in a format the workers understand.

Version two publishes messages in a different format.

If the workers cannot understand both versions, the deployment order matters.

Deploying the API first may break existing workers.

Deploying compatible workers first may allow a safe transition.

This is a consequence of distributed systems.

A release is not always one atomic event.

During an upgrade, old and new versions may coexist.

The architecture must tolerate that intermediate state.

Imagine renovating a bridge while cars are still driving across it.

You can't simply replace half the bridge with an incompatible design and declare that the construction team successfully installed its section.

The complete crossing must remain usable.

## 4. Helm organizes deployment configuration

Now suppose the platform consists of many Kubernetes resources.

Each application has a Deployment, Service, ConfigMaps, security settings, and possibly other resources.

Managing all those manifests manually becomes repetitive.

Helm provides a system for packaging and parameterizing Kubernetes resources into charts.

A chart contains templates and configuration values.

A Helm release represents an installed instance of a chart with its associated configuration and revision history.

This is useful because an application often needs several related Kubernetes resources deployed together.

But Helm is not a magic distributed transaction.

A successful Helm upgrade doesn't prove business correctness.

A rollback may restore earlier Kubernetes resource specifications, but it cannot necessarily reverse an already executed database migration, retract a message sent to RabbitMQ, or refund a payment.

Helm helps manage Kubernetes releases.

It doesn't abolish distributed-systems failure semantics.

## 5. GitOps makes declared intent persistent

Now imagine another problem.

An engineer modifies a Deployment manually during an incident.

The system appears fixed.

Several minutes later, the configuration mysteriously changes back.

Why?

Because a GitOps controller may be reconciling the cluster toward configuration stored in Git.

The engineer changed the live cluster.

But Git still declared the previous configuration.

Depending on the GitOps controller and its synchronization settings, the controller may detect the difference and restore the declared state.

This is the same reconciliation principle from SE450-L01, applied to deployment configuration.

GitOps answers an important operational question:

**Where is the authoritative declaration of what production should run?**

In a GitOps-managed environment, the intended answer is usually a version-controlled repository or another explicitly configured declarative source.

But that creates a responsibility.

Emergency changes must be coordinated with the reconciliation system.

Otherwise, a human and an automation controller can repeatedly undo one another's work.

## 6. Observability tells us whether reality is actually useful

Return to the broken scanner release.

The API responds successfully.

The Pods are healthy.

RabbitMQ accepts messages.

Yet scans do not complete.

What should we measure?

Not just CPU utilization.

Not just Pod restarts.

Not just HTTP success responses.

We should measure the customer operation itself.

For example:

- How many scan requests were accepted?
- How many scans actually started?
- How many completed successfully?
- How long did completion take?
- How many failed because of incompatible messages?
- How old is the oldest unfinished scan?

Those measurements reveal a failure invisible to the Deployment controller.

Now we can compare the release timestamp against changes in actual business outcomes.

This is the bridge between platform observability and application reliability.

### Visual anchor — three layers of truth

```text id="k7u1"
        DECLARED RELEASE
        Git / Helm / CI
               |
               v
       KUBERNETES STATE
     Deployments, Pods,
      Services, status
               |
               v
       APPLICATION STATE
    Requests, jobs, events,
      databases, errors
               |
               v
        BUSINESS OUTCOME
    Scans completed correctly
```

Each layer can appear healthy while the next one is broken.

The release process must verify progressively deeper claims.

## Your mental checkpoint

Before moving on, answer these aloud.

1. Why can a Deployment complete successfully while customers experience broken functionality?
2. Why shouldn't a readiness probe attempt to verify every possible business operation?
3. Why might a GitOps controller reverse a manual production fix?
4. Why does rolling back an application image not necessarily reverse its effects on databases or external systems?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The Release That Successfully Broke Every Scan

Our scanner platform has been running version one for several months.

The API receives scan requests and publishes RabbitMQ messages with a stable event contract.

Each message contains a scan identifier, a customer identifier, an asset identifier, and parameters controlling the investigation.

Workers consume those messages and perform the requested work.

The engineering team decides to improve the event schema.

The new API version introduces a more explicit message structure and changes the event version.

The code passes unit tests.

The Docker image builds successfully.

The Kubernetes manifests validate.

The new API Pods pass readiness checks.

The Deployment rollout completes.

But the existing workers still expect the old message schema.

They receive the new events, reject them, and repeatedly fail to process the affected jobs.

Depending on broker and application retry settings, those messages might be requeued, routed to a dead-letter queue, or left in another failure state.

Meanwhile, the API continues returning HTTP 202 Accepted for scan requests.

Every infrastructure dashboard looks reassuring.

Yet completed scans per minute collapse.

This is a classic release failure because the software is individually healthy but incompatible with its environment.

Let's understand how a mature release process prevents, detects, and recovers from it.

## 2. What a Kubernetes Deployment Actually Reports

A Deployment manages declarative updates to Pods through ReplicaSets.

When its Pod template changes, Kubernetes can create a new ReplicaSet and gradually replace the old population.

A rolling update is controlled by settings including `maxSurge` and `maxUnavailable`.

These define how much extra capacity may be used during the transition and how many desired replicas may temporarily be unavailable.

The Deployment controller observes progress and updates status conditions.

### Progressing

A Deployment can be progressing when a new ReplicaSet is created, scaled, or its Pods become ready or available.

The `Progressing` condition communicates information about rollout progress.

But a `Progressing=True` condition isn't always equivalent to a complete rollout.

The associated reason and current replica counts matter.

### Available

The `Available` condition reports whether the Deployment meets its minimum availability requirement under its strategy.

This is useful for infrastructure health.

It doesn't mean the application is satisfying every customer request.

### Complete rollout

A Deployment rollout is complete when the updated replicas satisfy the Deployment's completion conditions, including their availability, and the old replicas have been retired.

This is the condition commonly reported by a successful `kubectl rollout status`.

The result is meaningful but narrow.

Kubernetes has observed the required Pod population transition.

It has not run an end-to-end business acceptance suite.

### `minReadySeconds`

By default, a Pod can become available as soon as it is considered ready.

The Deployment supports `minReadySeconds`, requiring a new Pod to remain ready for a specified period before it counts as available.

This can prevent an application that briefly passes readiness and immediately crashes from being considered available too quickly.

But a continuously broken business operation can coexist with stable readiness for hours.

Increasing `minReadySeconds` doesn't repair a misleading readiness signal.

### `progressDeadlineSeconds`

A Deployment can report that rollout progress has stalled after a configured deadline.

The corresponding condition may report `ProgressDeadlineExceeded`.

This is a detection mechanism.

The ordinary Deployment controller does not automatically roll back the application simply because the progress deadline was exceeded.

A higher-level deployment system or an operator must decide how to respond.

This distinction is important when designing release automation.

**Kubernetes reports rollout conditions. Your release system decides what those conditions mean for promotion, rollback, or incident response.**

## 3. Availability During Rolling Updates

Suppose our scanner API runs four replicas.

We configure:

`maxSurge: 1`

`maxUnavailable: 0`

The Deployment may create an additional Pod before retiring an old available Pod.

This provides a conservative approach to maintaining application availability, assuming enough node capacity exists.

But consider the application-level implications.

During the rollout, version one and version two may coexist.

If both versions are compatible with the database and event contracts, the transition can be uneventful.

If version two changes the message format incompatibly, some requests may be handled by a producer that emits incompatible messages while others are handled by an older producer.

Customers experience inconsistent behavior depending on which replica handles their requests.

The rollout mechanism itself is doing what we requested.

The application compatibility contract is broken.

### Mixed-version compatibility is not optional

A rolling update creates a period in which different application versions can coexist.

Unless the system explicitly prevents mixed-version operation, the release design must tolerate it.

This affects more than event messages.

It can affect API request and response shapes, database schema, cache formats, session representation, serialized objects, and background jobs.

A safe release must identify these shared contracts.

A change isn't safe merely because it works when every application is upgraded simultaneously in a development environment.

Production rarely offers that kind of perfectly synchronized transition.

## 4. Designing Backward-Compatible Changes

Let's repair our scanner event migration.

The original event format is version one.

The new event format is version two.

The workers initially understand only version one.

We want to migrate without stopping the platform.

### The dangerous approach

Deploy the new producer first.

It immediately emits version-two events.

Old workers cannot process them.

The system breaks.

### The compatible approach

First, deploy workers that understand both version-one and version-two events.

Verify that they continue processing the existing queue successfully.

Then deploy the API version that begins producing version-two events.

Both formats can coexist while old messages remain in the broker.

Once no remaining producer emits version one and retained version-one messages have been processed or safely handled, the old-format support can eventually be removed.

This is a form of expand-and-contract migration.

We temporarily expand compatibility so that old and new systems can coexist.

Later, after the migration has completed, we contract the supported formats.

### Compatibility has a cost

Supporting two event versions adds code and testing complexity.

But that complexity is often much cheaper than requiring a coordinated shutdown of an entire production platform.

The same idea applies to database schemas.

A new application version may need an additional column.

A safe migration can add the column while preserving compatibility with old code.

The application can then begin using the new schema.

Only after old readers and writers are no longer active should the team remove obsolete structures.

The ordering depends on the exact change, but the general principle is stable:

**Deploy compatibility before deploying dependency on the new contract.**

## 5. Readiness, Termination, and Connection Draining

Even a perfectly compatible application can experience disruptions during rollout.

Recall SE450-L02.

When a Pod begins termination, Kubernetes starts a graceful shutdown process.

EndpointSlice conditions change to reflect the terminating endpoint.

Ordinary Service routing should avoid using terminating endpoints for new traffic.

But these changes propagate asynchronously.

A client may already have an established connection to the old Pod.

A reverse proxy may temporarily retain routing information.

An application may still have in-flight requests when SIGTERM arrives.

### Why readiness alone doesn't prevent dropped requests

Readiness controls eligibility for normal service traffic.

It doesn't guarantee that existing connections have disappeared.

It doesn't guarantee that every external load balancer has immediately updated its configuration.

And it doesn't automatically complete long-running requests before process termination.

The application needs a deliberate shutdown sequence.

For an HTTP API, that may involve stopping acceptance of new work, draining existing requests, closing listeners, and exiting within the termination grace period.

For a scanner worker, it may involve stopping message consumption, finishing bounded work where possible, and ensuring that unfinished messages remain recoverable.

### The timeout hierarchy

Imagine an HTTP request with a 90-second processing duration.

The Pod has a 30-second termination grace period.

The ingress proxy has a 60-second timeout.

The client has a 45-second timeout.

These values describe conflicting expectations.

Even if the application tries to finish gracefully, the client may abandon the request before the process exits.

A well-designed system should coordinate time budgets across client, proxy, application, and shutdown behavior.

This is not solely a Kubernetes problem.

It is a distributed request-lifecycle problem expressed through Kubernetes deployment mechanics.

## 6. PodDisruptionBudgets Are Not Deployment Rollout Budgets

A common misunderstanding involves PodDisruptionBudgets, or PDBs.

A PDB helps constrain certain voluntary Pod disruptions, especially eviction operations associated with maintenance such as node draining.

For example, it can express how many replicas should remain available during supported eviction operations.

But a PDB does not universally prevent all Pod termination.

It doesn't stop a node from crashing.

It doesn't prevent every resource-pressure or application failure.

And Deployment rolling updates are controlled by the Deployment's own update strategy rather than being constrained by PDBs in the same way as Eviction API operations.

That is an important distinction.

### Two different questions

A Deployment rollout strategy asks:

How should this workload transition from one Pod template to another?

A PDB asks:

How many voluntary evictions may the system permit under the disruption-budget rules?

They address related availability concerns but operate through different mechanisms.

A production system may need both.

For example, a Deployment can maintain appropriate availability during application upgrades, while a PDB helps protect the service during node maintenance.

Neither replaces the need for actual spare capacity or application-level readiness.

## 7. Helm: Packaging and Managing Kubernetes Releases

Kubernetes resources are individually declarative, but real applications often require many related resources.

Our scanner API may need a Deployment, Service, ConfigMaps, ServiceAccount, NetworkPolicies, and monitoring configuration.

Managing all of them as independent handwritten files can become cumbersome.

Helm addresses this by packaging related Kubernetes resource templates into charts.

### What a chart contains

A chart usually contains metadata, default values, and templates that render Kubernetes manifests.

Values customize a particular deployment.

For example, different environments might use different replica counts, image references, resource requests, or feature settings.

The same chart can be rendered with different values.

This helps standardize application deployment.

But excessive template abstraction can make charts difficult to understand.

A chart with dozens of conditional branches may be harder to maintain than a small set of straightforward manifests.

Helm is a packaging and release-management tool, not a competition to create the most elaborate YAML templating engine.

### What a release represents

A Helm release is an installed instance of a chart in a Kubernetes environment.

Helm maintains release metadata and revision history in the cluster.

Operators can inspect release history and perform upgrades or rollbacks.

This provides useful operational traceability.

For example, a team can identify which chart and values produced a previous release revision.

But that history is not necessarily a complete record of external application state.

The database may have changed.

Messages may have been published.

Users may have performed actions.

A release revision does not capture those business consequences.

## 8. Helm Rollback Isn't a Distributed Transaction

Suppose version two of our scanner API has already published thousands of version-two events.

The team uses Helm to roll back the API to version one.

The old API Pods return.

Does that fix the messages already in RabbitMQ?

No.

Those messages still exist in their previously published format.

If the workers don't support that format, the backlog may remain broken.

This is why application rollback cannot be treated as time travel.

### Helm's failure-handling capabilities

Helm provides mechanisms for waiting on Kubernetes resource readiness and rolling back failed upgrades.

Specific CLI flags have evolved between Helm versions.

For example, Helm 3 provides `--atomic`, which combines upgrade failure handling with rollback behavior.

Helm 4 introduces the corresponding `--rollback-on-failure` option.

Regardless of the flag name, the fundamental limitation remains: Helm can manage Kubernetes release resources according to its release semantics, but it cannot automatically reverse arbitrary external side effects.

### Hooks introduce additional complications

Helm supports lifecycle hooks.

A chart may define a pre-upgrade Job that performs a database migration.

Another hook might run a validation task after deployment.

These mechanisms are useful, but they must be designed carefully.

Suppose a migration Job permanently deletes an obsolete database column.

The application upgrade subsequently fails.

Rolling back the Kubernetes resources does not recreate the deleted column or its data.

Furthermore, Helm hook resources have lifecycle behavior distinct from ordinary release-managed resources.

A hook Job may persist after a release operation unless appropriate cleanup policies or TTL behavior are configured.

The architectural question is therefore not merely whether Helm supports rollback.

It's whether the application and its external dependencies can safely return to the previous operating state.

## 9. Database Migrations: The One-Way Door

Consider a database schema migration.

Version one stores a customer's scan status as a simple string.

Version two introduces a new state representation and begins writing values that version one cannot interpret.

Now imagine rolling back the application.

The old code encounters records written using the new representation.

It crashes or misinterprets their meaning.

The container image was restored, but application compatibility was not.

### Expand and contract

A safer migration may proceed through several stages.

First, extend the schema in a backward-compatible manner.

Second, deploy application versions capable of reading both old and new representations.

Third, gradually shift writes toward the new representation.

Fourth, migrate existing data if necessary.

Finally, remove old schema elements only after all relevant application versions and recovery requirements permit it.

This does not make every migration reversible.

Some transformations are inherently lossy.

But it reduces the chance that an ordinary deployment rollback leaves the previous application unable to function.

### A useful release classification

Before deployment, classify changes by reversibility.

An image-only change with unchanged external contracts may be easy to roll back.

A new optional database column may be relatively safe.

A destructive schema migration may not be safely reversible.

A change to a public API consumed by external customers may require long compatibility windows.

A message-format change affecting queued work may require support for multiple versions until old messages have drained.

The release process should reflect those differences.

**Rollback readiness is an architectural property, not a deployment-tool feature.**

## 10. GitOps: Git as the Declared Source of Truth

Helm helps package and install resources.

GitOps introduces a different architectural concern: how the desired state of a running environment is maintained over time.

In a typical GitOps workflow, deployment configuration is stored in version control.

A controller observes the relevant source and reconciles cluster resources toward the declared configuration.

Tools such as Argo CD and Flux implement variations of this pattern.

The details differ, but the fundamental model is familiar from SE450-L01.

### The control loop

```text id="k7u2"
         GIT REPOSITORY
        Desired configuration
                |
                v
         GITOPS CONTROLLER
       Compare desired/live
                |
                v
          KUBERNETES API
                |
                v
        WORKLOAD CONTROLLERS
                |
                v
          RUNNING SYSTEM
```

The GitOps controller does not replace Kubernetes' Deployment controller.

It operates one level above it.

The GitOps controller maintains the declared Kubernetes resources.

The Deployment controller maintains the declared Pod population.

The kubelet maintains the assigned containers.

This is a hierarchy of reconciliation loops.

### Why GitOps is useful

Version control provides review history, change attribution, approval workflows, and a place to compare intended configuration revisions.

The controller can detect differences between desired and live state.

Depending on its settings, it may automatically reconcile those differences.

This reduces reliance on manual production commands.

It also helps make environments more reproducible.

But reproducibility depends on more than storing YAML in Git.

Image references, chart versions, external dependencies, Secrets, database state, and cloud infrastructure may affect the actual environment.

A repository is only as authoritative as the system's real reconciliation and configuration model makes it.

## 11. The Incident Patch That GitOps Reverted

Return to the broken scanner release.

An engineer identifies the problem and manually changes the API Deployment back to the old image.

The application begins recovering.

But the Git repository still declares the new image.

Argo CD is configured for automated synchronization with self-healing enabled.

The controller observes that the live Deployment differs from the desired configuration.

It restores the new image.

The broken release returns.

The engineer changes it back.

The controller changes it again.

Now we have two actors with conflicting intent.

The Kubernetes API has accepted both sets of changes.

Each actor is behaving according to its own instructions.

The operational design has failed to establish who owns the desired production state during an incident.

### A better emergency procedure

In a GitOps-managed environment, the preferred recovery path is often to revert or correct the declared configuration in Git, then let the controller reconcile it.

If an immediate live-cluster intervention is necessary, the team must coordinate with the GitOps control mechanism.

That may involve temporarily suspending or disabling the relevant automated reconciliation according to the selected tool's documented procedure.

The exact action depends on whether the environment uses Argo CD, Flux, an ApplicationSet, HelmRelease, or another controller.

The important principle is universal:

**During an incident, understand which automation owns the resource before attempting a manual override.**

Otherwise, a correct emergency action can be immediately undone by a healthy controller.

### Self-healing and pruning are separate choices

In Argo CD, automated synchronization can be configured with different behaviors, including self-healing and pruning.

Self-healing can correct certain live-cluster deviations from desired state.

Pruning can remove resources that no longer belong to the declared application.

These features are not interchangeable.

And their defaults and exact behavior matter.

A dangerous configuration mistake could remove resources unintentionally if pruning and ownership are poorly understood.

GitOps must be reviewed as production automation capable of modifying and deleting infrastructure, not merely as a dashboard showing Git commits.

## 12. Drift: Not Every Difference Is an Error

Suppose Git declares that a Deployment should have four replicas.

The live cluster has six because an HPA increased the replica count.

Should GitOps immediately force the replica count back to four?

That depends on field ownership and configuration.

If both systems try to own the same field, they may conflict.

A well-designed GitOps arrangement must distinguish user-declared configuration from fields intentionally managed by other controllers.

Similarly, some resource fields are generated by Kubernetes itself.

Others are modified by admission controllers.

Some represent status rather than desired configuration.

A naive comparison of complete live resources against original manifests would produce constant irrelevant differences.

GitOps tools therefore implement resource tracking, normalization, field handling and configurable drift behavior.

The exact mechanisms differ between implementations.

### The ownership principle

For each important configuration field, determine who is supposed to control it.

A GitOps controller may own the application image and rollout configuration.

An HPA may own the effective desired replica count through the workload's scale interface.

A certificate controller may manage particular Secret contents.

A cloud controller may populate external load-balancer status.

If multiple actors control the same field without coordination, reconciliation can become unstable.

This is the same distributed-control problem we studied when examining multiple autoscalers.

Automation doesn't eliminate governance.

It makes governance executable.

## 13. CI, CD, Helm, and GitOps Have Different Jobs

These tools are often discussed as though they all represent the same deployment system.

They don't.

A continuous integration pipeline builds and tests software artifacts.

It may produce a container image, scan dependencies, run automated tests, and publish an immutable artifact.

A deployment process selects which artifact and configuration should run in a particular environment.

Helm can render and manage Kubernetes resources corresponding to that choice.

A GitOps controller can reconcile the cluster toward version-controlled deployment intent.

Kubernetes controllers then attempt to realize that intent.

### A coherent example

Our scanning platform uses a GitHub repository for application code.

A CI pipeline runs tests and builds a container image with a specific digest.

The image is published to a registry.

A separate change updates the deployment configuration to reference that digest.

The change receives appropriate review.

A GitOps controller observes the new desired configuration.

It applies the Kubernetes resource changes.

The Deployment controller rolls out the new Pods.

A release-verification system checks application and business-level signals.

If the release passes the required checks, it can be promoted more broadly.

The key benefit is separation of responsibilities.

The build pipeline doesn't necessarily need unrestricted cluster-administrator access.

The deployment configuration is reviewable.

The actual rollout is managed through controlled reconciliation.

And application success is verified independently of mere API acceptance.

### Don't turn the pipeline into a single security identity

A common anti-pattern is giving the CI system one extremely powerful credential that can build code, modify every namespace, read production Secrets, and delete infrastructure.

The pipeline becomes a major trust boundary.

If compromised, it can potentially deploy arbitrary software throughout the environment.

A mature architecture separates artifact-building permissions from production-deployment authority where feasible.

This continues the security principles from SE450-L06.

## 14. Progressive Delivery: Reduce the Blast Radius

Suppose we're not confident that version two of the scanner API will behave correctly under production traffic.

We have unit tests and staging tests, but production has traffic patterns and dependencies that staging cannot reproduce completely.

Deploying the new version to every Pod simultaneously creates unnecessary risk.

A safer approach may expose a small portion of production traffic to the new version.

This is the idea behind progressive delivery.

### Canary releases

A canary release introduces a new version to a limited population or subset of traffic.

The team measures its behavior before increasing exposure.

For example, the new scanner API might receive a small fraction of scan-submission traffic.

If the results remain healthy, traffic increases gradually.

If completion rates decline, the rollout stops and the new version is withdrawn.

### Replica percentages aren't necessarily traffic percentages

This distinction is essential.

Suppose a Deployment has nine old Pods and one new Pod.

Does the new Pod automatically receive exactly 10 percent of HTTP requests?

No.

Ordinary Kubernetes Service routing is commonly connection-oriented.

Long-lived connections, uneven client behavior and load-balancing implementation details can produce highly unequal request distribution.

A 10 percent Pod population is not a rigorous guarantee of 10 percent request traffic.

For precise traffic weighting, you may need an appropriate L7 gateway, service mesh or progressive-delivery controller that supports controlled traffic allocation.

Even then, verify how traffic weight is defined and measured.

### Blue-green deployment

Another approach maintains two application environments or revision populations.

One is active.

The other contains the candidate release.

After verification, traffic shifts from the old environment to the new one.

This can make certain reversions easier because the old environment remains available.

But blue-green doesn't solve incompatible database changes or irreversible external side effects.

And the traffic switch itself may involve connection-draining and propagation delays.

### Progressive delivery tools

Systems such as Argo Rollouts or Flagger can coordinate progressive changes using traffic-routing integrations and analysis signals.

They can automate promotion or rollback decisions.

But automation is only as good as its signals.

If the tool watches only CPU usage and HTTP success rates, our broken scanner release may pass every gate.

The metric must reflect the customer operation at risk.

## 15. What Should a Release Gate Measure?

Let's design a release gate for the scanner platform.

We could start with infrastructure signals:

Are the candidate Pods ready?

Is the Deployment progressing?

Are container restarts increasing?

Is memory consumption abnormal?

These are useful.

But they're not enough.

We also need application-level signals.

Are HTTP requests failing?

Are message-publishing errors increasing?

Are consumers rejecting the new event schema?

Are retry rates or dead-letter counts rising?

And then we need business outcomes.

Are accepted scans being completed?

Is the completion time within acceptable bounds?

Are findings being persisted correctly?

Are scan outcomes associated with the correct customers?

### Why HTTP 202 can be misleading

Our API returns HTTP 202 Accepted.

That means the request was accepted for processing according to the API's semantics.

It does not mean the scan completed.

So a dashboard reporting 99.99 percent successful HTTP responses may look excellent while the underlying asynchronous work is completely broken.

The API may be truthfully reporting successful acceptance.

But the product's actual service objective concerns completed useful work.

We need to track the operation beyond the original request.

### The scan funnel

A useful model is:

```text id="k7u3"
       SCAN REQUEST RECEIVED
                 |
                 v
          VALIDATION PASSED
                 |
                 v
         DURABLY ACCEPTED
                 |
                 v
          MESSAGE PUBLISHED
                 |
                 v
          WORKER STARTED
                 |
                 v
        SCAN RESULT PERSISTED
                 |
                 v
          SCAN COMPLETED
```

Each transition should have a durable or observable representation.

That makes it possible to identify where work stopped.

If requests are accepted but no workers start, inspect publishing, message routing and consumer behavior.

If workers start but never complete, inspect execution failures, resource limits, downstream dependencies and retries.

If results are persisted but scans remain incomplete, inspect workflow-state transitions and acknowledgment behavior.

This is considerably more useful than a single green API health indicator.

## 16. Metrics: Measure Rates, Durations, and Backlogs

Metrics summarize system behavior numerically.

For our platform, useful technical metrics include HTTP request rate, error rate, latency, container restarts, CPU throttling, queue depth and consumer failures.

Useful business metrics include scan acceptance rate, successful completion rate, completion latency and age of outstanding scans.

### Counters

A counter records events that accumulate over time.

For example, `scanner_jobs_completed_total` may increase whenever a scan reaches successful completion.

The rate of increase tells us how quickly useful work is being completed.

A counter can also track failures or retry attempts.

But it needs clear semantics.

If a worker retries the same job five times, should that contribute five failures or one failed business operation?

Both measurements may be useful, but they answer different questions.

### Gauges

A gauge represents a quantity that can increase or decrease.

Queue depth is a typical example.

The number of currently active scans is another.

But gauges can be misleading without context.

Ten thousand tiny tasks may represent less outstanding work than a hundred very expensive tasks.

A useful dashboard combines the size of the backlog with the rate at which work arrives and completes.

### Histograms

Histograms help describe distributions of durations or sizes.

For example, scan completion latency may vary dramatically by scanning module and target complexity.

An average completion time can hide a long tail of very slow scans.

Histograms allow analysis of latency distributions across observations, subject to correct instrumentation and aggregation.

### Avoid pathological labels

Metrics often include labels identifying dimensions such as environment, region, workload or operation type.

Labels are useful for filtering and aggregation.

But including a unique scan ID as a metric label can create extremely high cardinality.

Every new scan may produce a new time series.

That can overwhelm monitoring infrastructure.

Unique identifiers generally belong in logs or traces, not as unrestricted metric labels.

Metrics should summarize populations.

Logs and traces should provide individual-event detail.

## 17. Logs: Reconstructing the Specific Failure

When the scanner release fails, metrics tell us that completion rates declined.

But they don't necessarily explain which individual messages failed or why.

Logs provide more detailed evidence.

The API might log that it accepted scan `4821` and published an event with schema version two.

A worker might log that it rejected the event because a required field was missing.

The correlation between those records reveals the incompatibility.

### Structured logging

A useful application log should carry relevant context.

For example:

- Timestamp.
- Service and version.
- Environment.
- Operation or event type.
- Stable scan identifier.
- Request or correlation identifier.
- Error classification.

Not every log needs every field.

But a consistent structure makes investigations much easier than arbitrary free-text output.

### Do not leak sensitive information

Our platform processes customer data and security findings.

Logs should not casually include API tokens, authentication headers, raw secrets or unnecessary sensitive records.

A debugging feature that dumps entire HTTP requests into logs can become a serious security incident.

Observability has its own confidentiality requirements.

### Container logs have limited local lifetimes

Kubernetes commonly captures container output written to standard output and standard error.

`kubectl logs` can retrieve available container logs.

But these logs are not necessarily durable across every Pod or node failure.

Kubernetes itself does not provide a complete long-term centralized log storage system.

Production environments generally need an independent log collection and retention architecture.

A node-level agent, often deployed as a DaemonSet, may collect container logs and forward them to a centralized backend.

This connects observability to the workload abstractions we studied in SE450-L02.

## 18. Events: What Kubernetes Thinks Happened

Kubernetes Events provide diagnostic information about cluster resource activity.

They can reveal scheduling failures, image-pull problems, failed mounts, unsuccessful probe checks and other operational conditions.

For a Deployment rollout that never becomes healthy, Events are often extremely useful.

They help explain why Kubernetes couldn't realize the desired resource state.

But Events are not a complete application audit trail.

Our scanner event-schema bug may never produce a Kubernetes Event.

The API Pods are healthy.

The worker Pods are healthy.

The application-level message contract is wrong.

Kubernetes has no general reason to generate an Event for that semantic failure.

### Events versus application events

The word *event* is overloaded.

A Kubernetes Event describes something observed by cluster components.

A RabbitMQ message may represent a domain event or work command in the application.

These are different systems.

When investigating production, use precise terminology.

A failed Kubernetes scheduling Event is not the same as a failed business-event consumption attempt.

They may be causally related, but they belong to different layers.

## 19. Distributed Tracing: Following One Scan Across Services

Now consider the complete life of a scan request.

A customer sends an HTTP request.

The API validates it.

The application records a scan operation.

A message is published.

A worker eventually consumes it.

The worker calls several external services, runs scanners, and persists results.

The request may take seconds or hours to complete.

How do we reconstruct this journey?

Distributed tracing provides a model for observing operations across components.

A trace contains spans representing parts of a larger operation.

Spans may describe HTTP requests, database operations, message publishing, message processing and other work.

### A useful trace

```text id="k7u4"
SCAN OPERATION
  |
  +-- HTTP POST /scans
  |     |
  |     +-- Validate request
  |     +-- Persist scan intent
  |     +-- Publish message
  |
  +-- RabbitMQ processing
        |
        +-- Parse event
        +-- Execute scanner
        +-- Persist findings
        +-- Mark completed
```

This diagram shows a logical workflow. The actual trace structure depends on instrumentation and message-context propagation.

For asynchronous messaging, spans may be related using parent-child relationships, trace-context propagation or span links, as appropriate to the messaging pattern.

The important requirement is that the system preserves enough correlation to associate downstream work with the original logical operation.

### Tracing and queues

A queue introduces temporal separation.

The API request may finish long before the worker begins processing.

A worker may retry the same message.

Several workers may participate in one business operation.

Therefore, the trace model must account for asynchronous execution.

A stable scan ID remains important independently of trace IDs.

Tracing helps reconstruct execution.

The business operation ID identifies the durable task whose lifecycle matters to customers.

These concepts complement rather than replace one another.

### Sampling

Tracing every operation at full detail can be expensive.

Production systems often sample traces.

But sampling must be designed carefully.

Rare failures may be more valuable than routine successes.

A strategy that aggressively samples successful operations while preserving critical error traces may improve diagnostic usefulness, subject to privacy and cost constraints.

Metrics provide broad statistical visibility.

Traces provide sampled execution detail.

Logs provide individual records.

A mature investigation uses them together.

## 20. Release Correlation: Did This Deployment Cause the Incident?

Suppose scan completion rate falls sharply at 14:05.

A new API version was deployed at 14:02.

Is the deployment responsible?

It's a strong hypothesis, not yet proof.

Perhaps a third-party scanning provider experienced an outage at the same time.

Perhaps a large customer increased traffic.

Perhaps MongoDB became saturated.

We need evidence.

### Mark releases in telemetry

Observability systems should know when relevant releases occurred.

Metrics and logs can include low-cardinality version metadata.

Dashboards can annotate deployment events.

Traces can identify the service version associated with execution.

This makes it easier to compare system behavior before and after a release.

### Compare candidate and baseline

For a canary release, compare the new version against a stable baseline under reasonably comparable conditions.

Look at error rates, latency and relevant business outcomes.

Beware that candidate and baseline populations may differ.

A canary receiving only internal test traffic is not necessarily representative of production customer requests.

Similarly, a candidate deployed in one region may experience different workloads or infrastructure conditions.

A release comparison needs enough context to avoid false conclusions.

### The asynchronous attribution problem

Our scanner API accepts work now, but the scan may finish much later.

If completion latency is normally thirty minutes, evaluating the release only two minutes after deployment may be premature.

A useful release gate may combine immediate indicators, such as message schema rejection rates, with delayed outcome measurements.

The release-verification window should reflect the workload's actual lifecycle.

This is particularly important for systems where the business effect occurs asynchronously.

## 21. Rollback, Roll Forward, or Contain?

The scanner release is broken.

What should we do?

The answer depends on the failure and the reversibility of the change.

### Rollback

If the new API version is the only incompatible component, and the old version remains compatible with the current database and queued work, restoring the previous image may be appropriate.

But our scenario includes version-two events already published.

We must account for them.

The workers may need compatibility support, a controlled repair procedure or another safe recovery mechanism.

Rolling back the producer alone may stop new incompatible messages without fixing the existing backlog.

### Roll forward

Sometimes the safest fix is to deploy compatible workers that understand version-two messages.

This preserves the new event contract and allows the backlog to recover.

But the new worker code must itself be sufficiently tested.

During an incident, introducing another unverified change carries risk.

### Containment

The team may temporarily disable new scan submissions or restrict the affected feature.

That can prevent additional broken work from accumulating.

A temporary degraded mode may be preferable to accepting customer requests that cannot be fulfilled.

But the behavior should be transparent.

Returning HTTP 202 while knowing the system cannot process the work may be misleading, depending on the API's contract.

### Decision criteria

Ask which action most safely restores correct business behavior.

Consider:

- Whether the change is reversible.
- Whether queued work remains compatible.
- Whether database state has changed.
- Whether external side effects have occurred.
- Whether the old version can run against current dependencies.
- Whether a forward fix is sufficiently tested.
- How quickly the system can recover.

A release rollback is a tool.

Incident recovery is a decision process.

## 22. Designing a Production Release Procedure

Let's design a defensible deployment process for our scanner platform.

### Before deployment

Build and test an immutable image artifact.

Verify that expected security and quality checks pass.

Check the compatibility of event formats, API contracts and database changes.

Review whether the release contains irreversible operations.

Ensure that the deployment configuration references the intended artifact and configuration versions.

### During deployment

Apply the desired change through the organization's established release mechanism.

Use appropriate rollout settings and capacity headroom.

Observe Pod scheduling, readiness, restarts and Deployment progress.

Confirm that old and new versions coexist safely when rolling updates are used.

### After infrastructure readiness

Run suitable application checks.

Verify that the API can perform representative operations.

Confirm that a newly accepted scan can reach the broker and worker-processing pipeline.

Inspect immediate error signals such as message parsing failures, rejected events and dead-letter routing.

### During progressive exposure

Compare candidate and baseline behavior where traffic management supports it.

Watch meaningful business-level indicators.

Consider queue age, completion rate and latency in addition to HTTP metrics.

Hold promotion when evidence is insufficient.

Don't treat the absence of an alert during a thirty-second window as proof that a thirty-minute workflow is healthy.

### Promotion or recovery

If the release behaves correctly, increase exposure.

If it fails, stop promotion and choose rollback, roll-forward repair or containment based on the actual failure.

Coordinate the action with GitOps reconciliation.

Keep a record of the release decision and resulting operational state.

### After the release

Continue monitoring for delayed effects.

Some regressions emerge only after caches expire, background tasks accumulate or customer traffic reaches an unusual path.

A release is not finished merely because the pipeline has stopped running.

It is finished when the system has reached an acceptable stable operating condition and the verification requirements have been satisfied.

## 23. The Oral Examination

Answer these without rereading the lecture. A good answer should explain the failure mechanism and the operational decision.

### Challenge 1 — The Green Deployment

Kubernetes reports four available replicas and a successful rollout.

Customers can submit scans, but none completes.

What exactly has Kubernetes verified? What additional evidence do you need?

### Challenge 2 — The Message Schema Migration

The new API publishes version-two events.

Existing workers understand only version one.

Describe a safe deployment sequence that permits rolling upgrades without breaking queued work.

### Challenge 3 — The Rollback That Didn't Fix It

The team rolls the API back to version one.

New scans work, but thousands of previously accepted scans remain stuck.

Why? What should the incident recovery plan address?

### Challenge 4 — The GitOps Tug-of-War

An engineer manually fixes a Deployment image.

Minutes later, Argo CD restores the broken image.

What is happening, and what is the correct operational approach?

### Challenge 5 — The Fake Canary

A team deploys one new Pod alongside nine old Pods behind a normal ClusterIP Service.

They announce that exactly 10 percent of HTTP requests now use the new version.

What assumption is unsafe?

### Challenge 6 — The Misunderstood PDB

A team configures a PodDisruptionBudget and assumes that the Deployment controller cannot make more replicas unavailable during rolling updates than the PDB allows.

What is wrong with that assumption?

### Challenge 7 — The Helm Migration

A pre-upgrade Helm hook removes a database column.

The application upgrade fails, and Helm rolls back the Kubernetes resources.

Why might the old application still fail?

### Challenge 8 — The Perfect API Dashboard

The HTTP success rate is 99.99 percent, but the oldest scan has been waiting for six hours.

What measurements would expose the problem more accurately?

## 24. Solutions and Discussion

### Solution 1 — Kubernetes verified infrastructure convergence

The Deployment reached its requested Pod template and availability state according to Kubernetes' status semantics.

That does not establish business correctness.

Investigate request acceptance, message publishing, consumer failures, queue behavior, scan state transitions and completion outcomes.

Follow a representative scan through the full workflow.

### Solution 2 — Expand compatibility before changing producers

First deploy workers capable of processing both event versions.

Verify their compatibility with version-one messages.

Then deploy the API producing version-two events.

Maintain old-format support until previous producers and retained messages have been handled.

Only afterward consider removing the old contract.

### Solution 3 — Rollback doesn't erase queued messages

The version-two messages already exist in RabbitMQ.

Restoring the old API prevents additional version-two publication but doesn't transform existing messages.

The team must preserve and recover affected work through compatible consumers, controlled transformation or another safe procedure.

It must also check for partial side effects and duplicate execution.

### Solution 4 — Competing desired-state authorities

The live Deployment differs from Git.

With suitable automated self-healing enabled, the GitOps controller restores the declared configuration.

The recovery process should change the authoritative configuration or coordinate a temporary suspension of the relevant reconciliation mechanism.

Repeated manual patches without understanding ownership create an automation conflict.

### Solution 5 — Pod ratios don't guarantee request ratios

Ordinary Service routing is commonly connection-oriented.

A small number of long-lived connections may distribute requests unevenly.

Precise canary traffic weighting requires appropriate traffic management and measurement.

A one-in-ten Pod ratio is not a strict 10 percent HTTP request allocation guarantee.

### Solution 6 — PDBs and rollouts have different controls

PDBs constrain supported voluntary evictions.

Deployment rolling updates follow Deployment strategy settings such as `maxSurge` and `maxUnavailable`.

A PDB doesn't replace those controls.

Both mechanisms can be useful for availability, but they protect different operations.

### Solution 7 — External state isn't rolled back

The database column was removed.

Restoring Kubernetes manifests does not recreate its contents or guarantee compatibility with the previous application.

The migration should have been designed for mixed-version operation and safe rollback, or treated as an explicitly irreversible release requiring a different recovery strategy.

### Solution 8 — Measure the complete business lifecycle

Track accepted scans, started scans, completed scans, failures, retry counts and completion latency.

Monitor queue depth and age of outstanding work.

Correlate these metrics with release versions and timestamps.

HTTP request success is only one stage of the product's actual service contract.

## 25. The Mental Model Worth Keeping

A production release moves through several distinct forms of correctness.

**Artifact correctness:** Was the intended software built and tested?

**Configuration correctness:** Was the intended version and configuration declared?

**Infrastructure correctness:** Did Kubernetes realize the desired workload state?

**Application correctness:** Do the services and dependencies communicate successfully?

**Business correctness:** Can customers complete the operations the product promises?

A green signal at one layer doesn't establish correctness at every deeper layer.

Helm manages releases.

GitOps reconciles declared infrastructure intent.

Kubernetes controllers maintain resource state.

Observability provides evidence of runtime behavior.

The application architecture determines whether versions are compatible and operations can recover.

A mature deployment system connects these mechanisms through explicit verification and recovery decisions.

Whenever a release succeeds technically but fails operationally, ask:

1. What exactly did the successful tool verify?
2. Which application contract changed?
3. What business outcome stopped working?
4. What evidence establishes the cause?
5. Which recovery action preserves correctness?
6. Which automation owns the desired production state?

**A successful deployment is not a successful release until the resulting system is demonstrably useful.**

## 26. Next Lecture — SE450-L08: The Kubernetes Incident Room

We now understand Kubernetes' major mechanisms.

Control loops reconcile desired state.

Workload controllers manage process lifecycles.

Networking routes traffic through Services and endpoints.

The scheduler places Pods according to resources and constraints.

Storage and configuration follow their own persistence and update rules.

Security controls limit identities, privileges and reachability.

Release systems change the running environment while observability helps verify the outcome.

In the final lecture, we'll bring those mechanisms together in a production incident.

The cluster will present several misleading symptoms. Some Pods will be Pending. Others will be Running but unready. Service routing will appear suspicious. A recent deployment will complicate the investigation.

We'll work as the incident team, not as students memorizing YAML.

The objective will be to identify the actual failure chain, contain the damage, restore useful service, and explain how the architecture should change afterward.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

## Optional Practical Lab — A Successful Rollout With a Broken Application

**Goal:** Demonstrate that a Deployment can roll out successfully while an application route stops working.

This lab uses an isolated practice namespace and a simple Nginx container. It deliberately creates a functional regression without modifying real application infrastructure.

Use Minikube, kind or another disposable Kubernetes cluster. Confirm the current context before proceeding. Do not run this against production or a GitOps-managed namespace.

### Lab A — Verify and isolate

```bash
kubectl config current-context
kubectl get nodes
kubectl create namespace se450-l07
```

All subsequent resources belong to this practice namespace.

### Lab B — Deploy a working application

Create `web-v1.yaml`.

The application serves two endpoints. `/health/ready` represents a basic readiness check. `/api/scans` represents a simplified business endpoint.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scanner-api
  namespace: se450-l07
spec:
  replicas: 2
  revisionHistoryLimit: 5
  minReadySeconds: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: scanner-api
  template:
    metadata:
      labels:
        app: scanner-api
        version: v1
    spec:
      containers:
        - name: web
          image: nginx:stable-alpine
          command:
            - /bin/sh
            - -c
          args:
            - |
              mkdir -p /usr/share/nginx/html/health
              mkdir -p /usr/share/nginx/html/api
              printf 'ready\n' > /usr/share/nginx/html/health/ready
              printf 'accepted\n' > /usr/share/nginx/html/api/scans
              exec nginx -g 'daemon off;'
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 80
            periodSeconds: 3
            failureThreshold: 2
---
apiVersion: v1
kind: Service
metadata:
  name: scanner-api
  namespace: se450-l07
spec:
  selector:
    app: scanner-api
  ports:
    - port: 80
      targetPort: 80
```

Apply the manifest:

```bash
kubectl apply -f web-v1.yaml
kubectl rollout status deployment/scanner-api -n se450-l07
```

Inspect the Pods and Deployment.

```bash
kubectl get deployment,pods,service -n se450-l07
```

### Lab C — Verify readiness and functionality

In one terminal, forward the Service to your local machine:

```bash
kubectl port-forward -n se450-l07 service/scanner-api 18080:80
```

Leave that command running.

In another terminal, check the readiness endpoint:

```bash
curl -i http://localhost:18080/health/ready
```

It should respond successfully with `ready`.

Now check the business endpoint:

```bash
curl -i http://localhost:18080/api/scans
```

It should respond successfully with `accepted`.

Both infrastructure readiness and our simplified business check are working.

### Lab D — Create a broken version

Copy `web-v1.yaml` to `web-v2.yaml`.

In the second file, change the Pod-template label to `version: v2`.

Then modify the startup script so it still creates `/health/ready`, but no longer creates `/api/scans`.

The relevant script becomes:

```sh
mkdir -p /usr/share/nginx/html/health
printf 'ready\n' > /usr/share/nginx/html/health/ready
exec nginx -g 'daemon off;'
```

Apply the modified Deployment:

```bash
kubectl apply -f web-v2.yaml
kubectl rollout status deployment/scanner-api -n se450-l07
```

The rollout should complete successfully once the new Pods become ready and satisfy `minReadySeconds`.

Inspect the Deployment:

```bash
kubectl get deployment scanner-api -n se450-l07
kubectl get pods -n se450-l07 --show-labels
kubectl rollout history deployment/scanner-api -n se450-l07
```

### Lab E — Observe the false-positive health signal

Check readiness again:

```bash
curl -i http://localhost:18080/health/ready
```

It still returns success.

Now check the business endpoint:

```bash
curl -i http://localhost:18080/api/scans
```

It should return HTTP 404 because the new image's startup script no longer creates the expected file.

The application server is alive.

Its readiness endpoint is healthy.

The Deployment rollout completed.

But the application contract is broken.

**Explain:** Which system failed? Was the Deployment controller wrong to report success?

### Lab F — Recover the previous revision

Inspect the rollout history:

```bash
kubectl rollout history deployment/scanner-api -n se450-l07
```

Then perform a rollback:

```bash
kubectl rollout undo deployment/scanner-api -n se450-l07
kubectl rollout status deployment/scanner-api -n se450-l07
```

Verify the application endpoint again:

```bash
curl -i http://localhost:18080/api/scans
```

It should return `accepted`.

This demonstrates a simple reversible application change.

Now imagine that version two had also modified a database or published incompatible messages.

Would the rollback necessarily restore those external systems?

No.

That's the distinction between Kubernetes rollout history and application-level recovery.

### Lab G — Examine the operational evidence

Inspect the Deployment's status and ReplicaSets:

```bash
kubectl describe deployment scanner-api -n se450-l07
kubectl get replicasets -n se450-l07
kubectl get events -n se450-l07 --sort-by=.metadata.creationTimestamp
```

Notice that Kubernetes Events are unlikely to explain why `/api/scans` disappeared.

The cluster had no reason to consider that route part of its declared Deployment contract.

The error was detectable only through application-level verification.

### Lab H — Design a release gate

Without adding more infrastructure, propose an automated release check that performs these steps:

1. Wait for Deployment rollout completion.
2. Send a request to `/health/ready`.
3. Send a request to `/api/scans`.
4. Verify the expected response.
5. Reject release promotion if the business endpoint fails.

Then extend the thought experiment to the real scanner platform.

A request to `/scans` may return HTTP 202 immediately.

What additional test would prove that a worker actually processed the resulting message?

How long should that test wait?

How would you avoid creating expensive or irreversible production work?

A good answer might involve a dedicated synthetic scan using a controlled test target and isolated test tenant, with bounded execution and cleanup.

### Lab I — Cleanup

Stop the port-forward command.

Verify the practice resources:

```bash
kubectl get all -n se450-l07
```

Then remove the disposable namespace:

```bash
kubectl delete namespace se450-l07
```

### Final reflection

Explain why all three statements can be true simultaneously:

- The API server successfully accepted the Deployment update.
- Kubernetes successfully completed the Pod rollout.
- The application release failed its intended purpose.

That distinction is the central lesson.

---

## Further Reading

1. [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) — Rollouts, availability conditions, deadlines and revisions.
2. [Updating a Deployment](https://kubernetes.io/docs/tasks/run-application/update-deployment-rolling/) — Rolling updates and rollback operations.
3. [Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) — Readiness, termination and lifecycle behavior.
4. [Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/) — PodDisruptionBudgets and voluntary disruption semantics.
5. [Helm Documentation](https://helm.sh/docs/) — Charts, releases, upgrade and rollback behavior.
6. [Helm Chart Hooks](https://helm.sh/docs/topics/charts_hooks/) — Release lifecycle hooks and cleanup considerations.
7. [Argo CD Automated Sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/) — Reconciliation, self-healing and pruning.
8. [Flux HelmRelease](https://fluxcd.io/flux/components/helm/helmreleases/) — Controller-driven Helm reconciliation.
9. [Kubernetes Logging Architecture](https://kubernetes.io/docs/concepts/cluster-administration/logging/) — Container logs and cluster-level logging.
10. [Kubernetes Resource Metrics](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/) — Metrics Server and resource measurements.
11. [OpenTelemetry Concepts](https://opentelemetry.io/docs/concepts/) — Traces, metrics, logs and context propagation.

---

## Dense Cheatsheet — Interview Glance Card

*This final reference is intended for screen revision. Voice readers may skip the fenced material.*

```text
SE450-L07 — RELEASES, GITOPS, AND PLATFORM OBSERVABILITY

FIVE LAYERS OF RELEASE CORRECTNESS

1. Artifact
   Correct software built and tested?

2. Configuration
   Intended version/configuration declared?

3. Infrastructure
   Kubernetes resources reconciled and available?

4. Application
   Services, dependencies and contracts compatible?

5. Business
   Customer operations complete correctly?

   Success at one layer != success at every layer

DEPLOYMENT ROLLOUT

  Deployment -> ReplicaSet -> Pods

  maxSurge
    Additional non-terminating Pods during rollout

  maxUnavailable
    Allowed unavailable desired replicas

  minReadySeconds
    Pod must remain ready before counted available

  progressDeadlineSeconds
    Detects stalled progress
    Does NOT automatically roll back

  rollout status
    Reports Deployment progress/completion
    Does NOT test business correctness

MIXED-VERSION COMPATIBILITY

  Old/new application versions may coexist

  Check:
    API contracts
    Event schemas
    Database schemas
    Cache formats
    Session formats
    External dependencies

SAFE EVENT MIGRATION

  1. Consumers accept v1 + v2
  2. Deploy compatible consumers
  3. Deploy v2 producers
  4. Drain/handle retained v1 messages
  5. Eventually remove obsolete format

READINESS VS BUSINESS HEALTH

  Readiness:
    Is this instance eligible to serve?

  Release verification:
    Does the full system behave correctly?

  HTTP 202 Accepted != asynchronous job completed

TERMINATION

  Readiness/EndpointSlice updates are asynchronous
  Existing connections may remain
  SIGTERM initiates shutdown
  Grace period bounds orderly exit
  Worker must preserve recoverability of unfinished jobs

PDB

  Controls supported voluntary evictions
  Does not universally prevent all termination
  Deployment rolling update governed by rollout strategy
  PDB != maxUnavailable

HELM

  Chart:
    Parameterized Kubernetes resource package

  Release:
    Installed chart instance with revision history

  upgrade:
    Applies new release configuration

  rollback:
    Restores prior release resource state

  Hooks:
    Additional lifecycle actions
    External side effects may be irreversible
    Hook resources have distinct cleanup behavior

  HELM ROLLBACK != DATABASE ROLLBACK
  HELM ROLLBACK != MESSAGE RECALL
  HELM ROLLBACK != BUSINESS COMPENSATION

GITOPS

  Git/repository -> Desired configuration
  Controller -> Reconcile Kubernetes API resources
  Kubernetes -> Reconcile running workloads

  Argo CD / Flux implement related patterns

  self-heal:
    May restore desired configuration after live drift

  prune:
    Can remove resources no longer declared

  Emergency fix must coordinate with GitOps authority

FIELD OWNERSHIP

  GitOps -> image/configuration
  HPA -> replica scaling
  Other controllers -> managed fields/status

  Competing owners can create reconciliation conflicts

CI/CD RESPONSIBILITIES

  CI:
    Build/test/scan/publish immutable artifacts

  CD:
    Select/promote deployment configuration

  Helm:
    Template/package/manage release

  GitOps:
    Reconcile version-controlled desired state

  Kubernetes:
    Maintain declared infrastructure

PROGRESSIVE DELIVERY

  Rolling update:
    Gradually replaces Pods

  Canary:
    Limited exposure to candidate version

  Blue-green:
    Parallel revision environments, traffic switch

  10% candidate Pods != exactly 10% HTTP requests
  L7 traffic weighting may be required

RELEASE GATES

  Infrastructure:
    Ready Pods, rollout status, restart rate

  Application:
    Request errors, message failures, dependencies

  Business:
    Accepted -> Started -> Completed
    Completion latency
    Queue age
    Failed/duplicate operations

  Delayed workflows require longer verification windows

OBSERVABILITY

  Metrics:
    Population trends, rates, gauges, histograms

  Logs:
    Individual events, errors, structured context

  Traces:
    Execution path across services and async boundaries

  Kubernetes Events:
    Cluster-resource conditions and operational changes

  None replaces the others

METRICS TO WATCH

  API request rate / errors / latency
  Message publish and consumer failures
  Queue depth and oldest-message age
  Scan started/completed/failed rates
  Completion latency distribution
  Container restarts and CPU throttling
  Database/broker saturation

HIGH CARDINALITY

  Version/region/service = often suitable labels
  Unique scan ID = generally NOT a metric label
  Unique IDs belong in logs/traces

RELEASE INCIDENT RESPONSE

  1. Identify regression and affected business operation
  2. Correlate with release/configuration changes
  3. Contain further damage
  4. Evaluate rollback compatibility
  5. Roll back or roll forward safely
  6. Recover queued/partial operations
  7. Coordinate GitOps desired state
  8. Verify restored business outcomes

ROLLBACK LIMITS

  Image rollback doesn't undo:
    database mutations
    messages already published
    external API calls
    irreversible migrations
    customer-visible side effects

  Reversibility must be designed before release

SIX SENIOR QUESTIONS

  1. What exactly passed?
  2. What business contract failed?
  3. Which versions coexist?
  4. What external state changed?
  5. Which recovery operation is safe?
  6. Which automation owns desired state?

SENIOR LINE

  "A deployment is infrastructure convergence, not proof of
   business correctness. I design mixed-version compatibility,
   verify customer outcomes, use controlled progressive delivery,
   and ensure rollback or roll-forward decisions account for
   external state and GitOps reconciliation."
```
