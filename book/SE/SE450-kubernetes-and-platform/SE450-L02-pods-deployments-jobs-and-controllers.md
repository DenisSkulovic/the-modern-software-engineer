---
id: SE450-L02
course: SE450
title: "Pods, Deployments, Jobs, and Controllers"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE450-L01
next: SE450-L03
---






# SE450 — Kubernetes and Platform Engineering

## Lecture 02: Pods, Deployments, Jobs, and Controllers

*Your application is running. Then Kubernetes decides to replace it. Does the work disappear, finish, repeat, or get handed to someone else? The answer depends on what kind of workload you've built—and whether you understand what Kubernetes actually promises.*

---

# Part I — Intuition

## The picture to carry in your head

Imagine a cybersecurity company operating a platform that scans customers' internet-facing assets.

The architecture has several moving parts.

An HTTP API accepts scan requests. Background workers fetch jobs from RabbitMQ and investigate domains. A MongoDB cluster stores results. A monitoring agent collects node-level metrics and reports unusual resource consumption.

All these processes run inside containers.

You could deploy all of them in essentially the same way: start each container, watch whether it crashes, and restart it when necessary.

But consider what happens when they stop.

If an API instance exits, you generally want another instance running as soon as possible. The process is supposed to remain available indefinitely.

If a scanner starts a specific finite task, executes it successfully, and exits with code zero, that's not necessarily a failure. That might be the entire point of its existence.

If a database instance disappears, blindly starting another instance under a different identity may not be sufficient. It may need access to its previous persistent data and stable cluster membership information.

And if a node-monitoring agent runs on every machine, adding a fourth machine should probably cause a fourth monitoring instance to appear.

These are fundamentally different operational requirements.

Kubernetes provides different workload abstractions because **not all processes have the same relationship with time, identity, completion, and failure**.

## 1. A Pod is not quite a container

Start with the smallest important unit: the Pod.

A container is an isolated execution environment for a process and its dependencies.

A Pod is the Kubernetes object that groups one or more cooperating containers into a shared execution and scheduling unit.

Imagine an API server alongside a helper container that forwards its logs. The two containers might need to communicate locally and share a volume.

Kubernetes can place them inside the same Pod.

Containers within that Pod share its network namespace, including the Pod's IP address and port space. They can communicate through localhost, provided the relevant applications are listening on compatible addresses and ports.

They can also share explicitly configured volumes.

They don't automatically share every aspect of their filesystems or process namespaces. They remain distinct containers.

The Pod acts as a small execution environment holding these related components together.

One Pod runs on one node. Kubernetes does not distribute the containers of a single Pod across separate machines.

This matters when one component depends closely on another.

If the application and its helper must always be placed together, a shared Pod can make sense.

But two completely independent services probably shouldn't be forced into the same Pod merely because they communicate occasionally. They would inherit unnecessary placement and lifecycle coupling.

### Visual anchor — the Pod

```text
                KUBERNETES NODE
           +-------------------------+
           |          POD            |
           |                         |
           |  +-------+  +--------+  |
           |  |  API  |  | Helper |  |
           |  +-------+  +--------+  |
           |                         |
           |  Shared Pod network     |
           |  Shared named volumes   |
           +-------------------------+
```

The Pod is the unit Kubernetes schedules onto a node.

But it doesn't necessarily follow that every failure inside a Pod requires an entirely new Pod.

That distinction comes next.

## 2. Restarting a container is not replacing a Pod

Suppose an API process crashes.

The kubelet may restart the container inside its existing Pod, depending on the configured restart policy.

The Pod has not necessarily disappeared. It can retain the same name, UID and node assignment while the container restart count increases.

Now suppose the node itself disappears.

The original Pod cannot simply migrate, carrying its process memory onto another machine.

A workload controller may create a replacement Pod, and the scheduler may place that replacement on another healthy node.

The replacement is a new Pod object. It receives its own identity, execution environment and startup lifecycle.

So we have two very different recovery mechanisms:

**Container restart:** recreate execution inside the existing Pod.

**Pod replacement:** create a new Pod to satisfy the desired workload state.

This is why an engineer investigating a problem should inspect both Pod identity and container restart counts.

A container with 20 restarts inside the same Pod suggests a different failure pattern from 20 successive Pods being created and deleted.

## 3. The Deployment — maintain a population

Return to our HTTP API.

We want three instances running so that the application can tolerate ordinary instance failures and serve concurrent traffic.

We don't particularly care which instance is called `scanner-api-abc` or `scanner-api-xyz`.

We care that the correct version of the application remains available in sufficient numbers.

That's what a Deployment is designed to manage.

You declare the desired replica count and a Pod template.

Kubernetes creates and manages the subordinate resources that maintain those replicas.

If one managed Pod disappears, a replacement may be created.

If you change the container image, the Deployment can coordinate the replacement of the old replicas with new ones.

The important idea is that the individual Pods are disposable representatives of a larger desired population.

A Deployment manages continuity at the application-replica level, not continuity of each individual process.

## 4. The Job — completion is success

Now consider a single bounded scan.

A customer requests a particular asset investigation. The scanner starts, performs the work, writes its result, and exits successfully.

Should Kubernetes restart that completed process forever?

Obviously not.

A Job describes work that is expected to reach a completion condition.

Instead of maintaining three indefinitely running replicas, a Job controller manages Pods toward a specified number of successful completions, subject to the Job's policies.

If a Pod fails, the controller may arrange another attempt.

If the work completes successfully, the Job can be marked complete.

This changes the meaning of a process exiting.

For a continuously running API, an unexpected exit is a condition to recover from.

For a Job, a successful exit is the desired outcome.

### A subtle but important distinction

Our cybersecurity platform might use long-lived workers consuming jobs from RabbitMQ.

In that design, the worker processes should continue running. A Deployment is often appropriate.

The RabbitMQ messages represent individual scanning tasks, not Kubernetes Jobs.

Alternatively, the application might create a Kubernetes Job for each sufficiently substantial, bounded scan.

That can also be appropriate, but it introduces control-plane object overhead and different scheduling characteristics.

There is no rule saying that every background task should become a Kubernetes Job.

**Choose the workload abstraction for the process lifecycle, not merely because the application performs background work.**

## 5. The StatefulSet — identity matters

Now think about MongoDB.

A database replica may need persistent storage, a stable identity, and deliberate membership in a replication topology.

A conventional Deployment can create several Pods, but its replicas are largely interchangeable.

A StatefulSet provides stable ordinal identity and mechanisms for stable network identities and persistent volume claims.

An instance might be known as `mongo-0`, with a persistent volume associated with that ordinal.

If its Pod is replaced, Kubernetes can recreate the same logical member identity and reattach its persistent storage, subject to storage availability and correct configuration.

That is useful for stateful systems.

But Kubernetes does not automatically guarantee database correctness merely because the database runs inside a StatefulSet.

Replication, failover, quorum, durability and recovery remain database-specific responsibilities.

The StatefulSet gives us valuable infrastructure primitives. It does not replace the database's own distributed-systems protocols.

## 6. The DaemonSet — the shape of the infrastructure matters

Our monitoring agent has another requirement.

We want one instance on each eligible cluster node.

If the cluster grows from four nodes to six, two additional agents should appear.

If a node is removed, its agent is no longer needed.

That's the purpose of a DaemonSet.

Its desired population is tied to eligible nodes rather than an ordinary fixed replica count.

This makes it suitable for node-level monitoring, logging, networking and storage agents.

You wouldn't normally use a DaemonSet to maintain three HTTP API instances. Three replicas and one replica per node are different requirements.

### Visual anchor — choosing the right controller

```text
DEPLOYMENT      Keep N interchangeable app replicas
JOB             Complete bounded work
CRONJOB         Create Jobs on a schedule
STATEFULSET     Maintain stable workload identities
DAEMONSET       Run an agent on eligible nodes
```

These workload types are not interchangeable conveniences. Each encodes a different contract with the cluster.

## 7. The moment Kubernetes asks your process to leave

Picture a scanner worker halfway through an expensive investigation.

It has pulled a message from RabbitMQ, spent twenty seconds gathering information, and is about to publish the results.

A new application version is deployed.

Kubernetes begins terminating the old Pod.

What happens to the unfinished work?

The operating system doesn't automatically send it to another worker. Kubernetes doesn't serialize the process's memory and resume it somewhere else.

Instead, the workload has a limited opportunity to shut down gracefully.

The application can stop accepting new tasks, finish suitable in-flight work, persist progress, and acknowledge messages only after successful processing.

If the process doesn't finish before the termination deadline, it may be killed.

The broker may then redeliver the unacknowledged message.

The same business operation can be attempted again.

This is not necessarily a Kubernetes bug or a RabbitMQ bug.

It is the normal consequence of combining finite process lifetimes with durable work delivery.

The correct architecture assumes that processes can disappear.

## Your mental checkpoint

Answer these before continuing.

1. Why might a Deployment be appropriate for a long-lived RabbitMQ consumer, while a Job is appropriate for a bounded scan?
2. What is the difference between restarting a container and replacing its Pod?
3. Why does a StatefulSet provide useful database infrastructure without guaranteeing database correctness?
4. What should a scanner worker do when it receives a termination signal?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The Deployment That Duplicated a Thousand Scans

Our cybersecurity platform has an API, six long-running scanner workers, MongoDB, and RabbitMQ.

Each worker repeatedly receives a scan message, performs network investigations, writes results, and acknowledges the message.

The platform has been stable for weeks.

Then the team deploys a new scanner image.

The Deployment replaces old Pods with new ones. Kubernetes reports that the rollout completed.

But the operations dashboard shows something peculiar: a substantial number of scans have executed twice. Some were expensive enough to trigger external API rate limits. Others generated duplicate observations in MongoDB.

The developers initially blame Kubernetes.

"Why did it kill our workers halfway through their jobs?"

But process replacement is exactly what the Deployment was instructed to perform.

The actual failure lies in an assumption: the application treated successful process execution as if it had an uninterrupted lifetime.

A rolling update is not an atomic transfer of business operations from old Pods to new Pods.

To understand this properly, we need to examine the Pod lifecycle, workload controllers, probes and termination sequence.

## 2. A Pod Has Identity, State, and a Lifetime

A Pod is an API resource with its own metadata, specification and observed status.

Its specification describes containers, volumes, networking-related settings, resource requirements and lifecycle configuration.

The scheduler assigns the Pod to a node. The kubelet on that node works with the container runtime to realize it.

Once created, a Pod is generally intended for the lifetime of that particular execution environment.

Its ordinary replacement is not an in-place relocation.

### Pod phases are intentionally broad

The Pod API defines several major phases.

**Pending** means the Pod has been accepted, but one or more containers have not yet been set up and started. The Pod may be waiting for scheduling, image retrieval or initialization.

**Running** means the Pod has been bound to a node and its containers have been created, with at least one running or starting/restarting.

**Succeeded** indicates that all containers terminated successfully and will not be restarted.

**Failed** indicates that all containers have terminated and at least one terminated unsuccessfully, or the system has otherwise determined the Pod failed.

**Unknown** means the cluster cannot obtain the Pod's state, commonly because communication with the node has failed.

These phases do not provide the full diagnostic story.

For example, `CrashLoopBackOff` is a container waiting reason commonly displayed by `kubectl`, not a formal Pod phase.

Similarly, `Terminating` is a convenient status presentation associated with a deletion in progress, not another official phase.

An engineer must distinguish the broad Pod phase from container states, waiting reasons, readiness conditions and events.

### Container states

Within a Pod, individual containers can be Waiting, Running or Terminated.

A container may be waiting because its image cannot be pulled.

It may be running while the application remains unready.

It may terminate with exit code zero, indicating successful process completion, or with a nonzero exit code indicating failure.

The kubelet may restart that container according to its restart policy.

Consequently, the string `Running` is not proof that an application is healthy.

A process can be alive and still be deadlocked, disconnected from its dependencies or returning incorrect results.

## 3. Restart Policies: What Happens When the Process Exits?

The Pod-level `restartPolicy` traditionally offers three main choices.

**Always** restarts ordinary application containers after termination, whether the exit was successful or unsuccessful. This is the normal policy for Deployments.

**OnFailure** restarts containers after unsuccessful termination but not after successful completion.

**Never** does not automatically restart terminated containers.

Jobs typically use OnFailure or Never, while Deployment Pod templates require Always.

These rules describe restart behavior inside a Pod. They do not define the separate replacement behavior of a higher-level controller.

For example, a Job with `restartPolicy: Never` can still lead to a new Pod being created after a failed attempt. The kubelet won't restart the failed container inside the original Pod, but the Job controller may create another Pod.

This is a useful distinction:

**Restart policy belongs to container recovery. Controller policy belongs to workload recovery.**

Some Kubernetes versions also support more specialized per-container restart rules. Those details are version-dependent and should be checked against the target cluster. For our conceptual model, the three Pod-level policies remain the starting point.

### Crash loops and exponential backoff

Suppose the scanner API immediately exits because an environment variable is missing.

A kubelet doesn't necessarily restart the failing container in a tight loop thousands of times per second.

Repeated failures trigger a restart backoff. Kubernetes commonly reports `CrashLoopBackOff` as the container repeatedly fails and waits before another attempt.

This protects the node from extreme restart churn.

But it does not solve the underlying application problem.

A missing secret, invalid configuration or incompatible binary may continue failing indefinitely until somebody fixes the cause.

Deleting the Pod may briefly change the visible symptoms, but its controller can create another Pod with the same broken specification.

## 4. Controllers, Ownership, and Why Deleting Pods Usually Doesn't Work

Recall L01's reconciliation model.

A Deployment does not normally manage its Pods by issuing direct container commands.

Instead, the Deployment controller manages ReplicaSets, and ReplicaSet controllers manage Pods.

The resources form an ownership hierarchy.

A Deployment defines the desired number of replicas and desired Pod template.

A ReplicaSet attempts to maintain a population of Pods matching its specification.

Pods carry metadata identifying their controller ownership.

This ownership relationship is important for lifecycle coordination and garbage collection.

### The futile deletion

Suppose you have a Deployment requesting four replicas.

You execute `kubectl delete pod` on one of its Pods.

The ReplicaSet controller notices that its desired population is no longer satisfied and creates a replacement.

The system is doing exactly what it should.

If you actually want fewer replicas, change the Deployment's desired replica count.

If you want to stop the workload, scale it down or remove the appropriate higher-level object according to your operational intent.

Deleting an individual Pod is not the same as changing the desired workload.

### Labels and selectors

ReplicaSets use label selectors to identify Pods that belong to their desired population.

A Deployment defines a selector and a Pod template whose labels match it.

A simplified configuration might include:

```yaml
selector:
  matchLabels:
    app: scanner-api
template:
  metadata:
    labels:
      app: scanner-api
```

Labels are organizational metadata, but they also participate in actual control behavior.

Overlapping selectors can produce confusing ownership or controller conflicts if workloads are poorly designed.

The `ownerReferences` relationship and selectors together provide mechanisms for identifying and controlling resources.

This is why casually editing labels on live infrastructure can have consequences beyond changing how objects appear in a dashboard.

## 5. Deployments: Managing Replicas and Rollouts

A Deployment provides declarative updates for Pods and ReplicaSets.

It is generally well suited to interchangeable, long-running application instances.

Imagine three API replicas, all running version one.

You want to deploy version two.

One possible strategy would be to terminate all three old instances and then create three new ones.

That can introduce downtime.

A rolling update instead gradually changes the replica population.

The Deployment creates or scales a ReplicaSet for the new Pod template and reduces the old one according to configured constraints.

### RollingUpdate versus Recreate

The default Deployment strategy is RollingUpdate.

This aims to maintain some application availability while the rollout proceeds.

A Recreate strategy terminates the old Deployment revision's Pods before starting the new revision's Pods during an upgrade.

Recreate can be appropriate for specialized cases where old and new revisions should not coexist, but it normally introduces an availability gap.

Neither strategy magically guarantees correct application behavior.

A rolling update depends on how accurately Kubernetes can determine whether the new Pods are ready and whether the application can tolerate multiple revisions existing simultaneously.

### maxSurge and maxUnavailable

Two settings control much of a rolling update's capacity behavior.

`maxSurge` specifies how many extra non-terminating Pods the Deployment may create above the desired replica count during the rollout.

`maxUnavailable` specifies how many desired replicas may be unavailable during the rollout.

Consider four desired replicas with:

`maxSurge: 1`

`maxUnavailable: 0`

The Deployment can temporarily create a fifth Pod while keeping the four desired replicas available, then retire old Pods as replacements become available.

This is attractive for important APIs, but it requires spare cluster capacity.

If the cluster cannot accommodate the surge Pod, the rollout can stall.

A termination grace period can also mean that terminating Pods remain present while replacements are being created, so observed total Pods may temporarily exceed the simplistic surge calculation.

Now imagine:

`maxSurge: 0`

`maxUnavailable: 1`

The rollout may remove one old available replica before its replacement is ready, allowing progress with less spare capacity but reducing available replicas during the transition.

The correct settings depend on workload capacity, startup time, availability requirements and resource constraints.

### Default percentages and rounding

The default values for both settings are 25 percent.

When percentages are used, `maxSurge` rounds up and `maxUnavailable` rounds down.

For a small Deployment, those rounding rules matter.

A Deployment with three replicas doesn't necessarily have permission to take one of them unavailable merely because the default is 25 percent.

The actual arithmetic is part of the rollout's behavior.

### Rollout failure does not imply automatic rollback

Suppose the new scanner API image cannot start.

The Deployment may report that rollout progress has exceeded its deadline.

That condition is important, but the ordinary Deployment controller does not automatically revert to the previous revision merely because the progress deadline was exceeded.

A human or deployment automation must decide whether to roll back or otherwise repair the rollout.

`kubectl rollout undo` can restore a previous Deployment revision, provided the appropriate rollout history remains available.

The larger lesson is that **a successful configuration update and a successful software release are different events**.

## 6. Readiness, Liveness, and Startup: Three Different Questions

A Pod may be running but unable to serve requests.

Perhaps the API process has started listening on its port but hasn't finished loading its configuration.

Perhaps the worker is alive but temporarily unable to process new scans.

Kubernetes provides probes to help distinguish some of these conditions.

The most common types are readiness, liveness and startup probes.

Their meanings are distinct, and confusing them is one of the easiest ways to turn a modest application problem into a production incident.

### Readiness: should this container receive work?

A readiness probe determines whether the container is ready to serve its intended workload.

For an API, that usually relates to whether the Pod should receive normal traffic through Kubernetes Services.

A failed readiness probe marks the container unready. The Pod's readiness reflects relevant container readiness and other configured conditions.

Service routing then uses readiness information to avoid treating an unready endpoint as eligible for normal traffic.

The process is not automatically restarted merely because readiness fails.

This is important.

An application may be temporarily unable to serve requests while still being perfectly capable of recovering without a restart.

For example, an API might be waiting for a required local initialization step.

Restarting it every few seconds could only delay recovery.

### Liveness: is this process stuck beyond useful recovery?

A liveness probe asks whether the container should be restarted because it is no longer functioning acceptably.

An application that has deadlocked or entered an unrecoverable internal condition may benefit from restarting.

But an external dependency being unavailable is not automatically proof that the application itself needs to restart.

Suppose MongoDB becomes unavailable for thirty seconds.

If every API replica's liveness probe checks MongoDB availability, all replicas may begin restarting during the outage.

Now, when MongoDB recovers, every API process starts simultaneously and opens new connections.

You have transformed a temporary dependency incident into a coordinated restart storm.

The better probe design distinguishes between a process that can still make progress and a process that is internally broken.

**Liveness should be conservative. Readiness can express temporary inability to serve.**

### Startup: give slow applications time to initialize

Some applications need significant startup time.

A service might load a large model, initialize local caches, or perform other necessary startup work.

An aggressive liveness probe could repeatedly kill it before initialization completes.

A startup probe lets the application establish that startup has succeeded.

While the startup probe has not succeeded, Kubernetes holds back liveness and readiness probe execution for that container.

Once startup succeeds, the other probes take over according to their configuration.

This prevents a predictable slow startup from being mistaken for an unrecoverable process failure.

### An example

A simple HTTP application might expose:

- `/health/live` — verifies that the application process is responsive and internally functional.
- `/health/ready` — verifies that the instance is prepared to accept its expected traffic.
- `/health/startup` — indicates completion of essential startup initialization.

The precise checks depend on the application.

A Node.js process responding to an HTTP request is some evidence of health, but it doesn't prove that every route or background task works correctly.

At the other extreme, probing every external dependency can make health assessment unnecessarily fragile.

The right design deliberately chooses what failure should trigger traffic removal, process restart or operator intervention.

### Configuration example

```yaml
startupProbe:
  httpGet:
    path: /health/startup
    port: 8080
  periodSeconds: 5
  failureThreshold: 24

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  periodSeconds: 5
  failureThreshold: 2

livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  periodSeconds: 10
  failureThreshold: 3
```

This illustrative configuration gives startup up to roughly two minutes before repeated startup probe failure triggers container termination and restart according to policy.

After startup succeeds, readiness and liveness checks operate independently.

The numbers are not universal recommendations. They should reflect measured initialization time, failure behavior and operational tolerance.

### Beware the readiness illusion

If your application exposes a readiness endpoint that always returns success, Kubernetes can report that the Pod is ready even when it cannot perform useful work.

The probe has to test the property you actually care about.

Similarly, a readiness probe that fails because an optional analytics service is unavailable may unnecessarily remove an otherwise healthy API replica from traffic.

Probe design is part of the application's reliability contract, not a box to tick in a YAML file.

## 7. Startup Is a Lifecycle, Not an Instant

Let's follow a new Pod from its creation to useful operation.

The scheduler assigns it to a node.

The kubelet arranges for the Pod's execution environment and container images.

Regular init containers, if configured, execute before ordinary application containers.

The application containers start.

Startup probes may assess whether essential initialization has completed.

Readiness probes determine when the application can join normal service traffic.

The Pod eventually becomes ready if its relevant readiness conditions are satisfied.

But several failures can interrupt this journey.

An image pull may fail.

A volume may be unavailable.

An init container may repeatedly fail.

The application may exit during startup.

Or the application may run indefinitely without ever passing readiness.

Each failure happens at a different layer.

This is why debugging a new Pod should begin with its status, events and lifecycle stage, rather than immediately assuming an application bug.

## 8. Init Containers and Sidecars: Cooperating Without Confusing Lifecycles

An init container is a container designed to execute before the ordinary application containers.

Regular init containers execute sequentially and must complete successfully before the next init container or the application containers proceed.

Imagine a scanner requiring a configuration bundle to be prepared locally.

An init container could retrieve or construct the necessary files and write them into a shared volume.

The main scanner container then starts with that prepared environment.

This can be cleaner than duplicating initialization logic inside every application entrypoint.

### But initialization can repeat

Do not assume an init container is globally guaranteed to execute only once.

Pod replacement can cause initialization to execute again, and certain local lifecycle events can also require re-execution.

Therefore, initialization actions should generally tolerate repetition.

A particularly dangerous anti-pattern is making every API Pod's init container run global database migrations without coordination.

Deploy five replicas and you may produce five concurrent migration attempts.

Those operations may have destructive or incompatible effects.

Global migrations deserve explicit lifecycle and concurrency management, often through a separately coordinated release step or suitable Job.

### Sidecars

A sidecar is a supporting container that runs alongside the main application.

Typical examples include proxies, telemetry helpers and local supporting services.

Modern Kubernetes supports native sidecars through restartable entries in `initContainers`, allowing controlled startup and shutdown behavior.

A native sidecar can remain running while the main application runs, and its shutdown ordering is managed differently from unrelated ordinary containers.

That matters when the main process needs the sidecar during its final moments.

For instance, terminating a log-forwarding sidecar before the application finishes its shutdown logging can lose important diagnostic records.

However, adding a sidecar also creates coupling. Both containers share the Pod's placement and relevant lifecycle constraints.

A sidecar should exist because close cooperation is genuinely useful, not because every application is expected to have three containers.

## 9. Graceful Shutdown — The Most Expensive Thirty Seconds You Never Planned

Return to our scanner workers.

A worker receives a RabbitMQ message and begins a sixty-second investigation.

Twenty seconds later, Kubernetes starts terminating its Pod during a rollout.

By default, ordinary Pod termination uses a grace period of thirty seconds, although applications can configure a different period.

That creates a problem: our worker may need another forty seconds to finish its job, but the termination deadline is approaching.

The application must have a deliberate policy for that situation.

### What graceful termination actually does

When a Pod is marked for deletion, Kubernetes records a deletion timestamp and grace period.

The kubelet observes termination and begins shutting down the containers.

If a `preStop` lifecycle hook exists and the grace period is nonzero, Kubernetes executes it as part of shutdown. The hook consumes time from the overall grace period; it does not normally receive an additional independent timeout budget.

The container runtime is then asked to signal the main process, usually with SIGTERM.

The application gets an opportunity to shut down.

If containers remain running after the allowed grace period, the runtime can forcibly terminate them, typically with SIGKILL.

The exact sequence can involve asynchronous coordination and timing differences between components.

This is not a synchronous guarantee that all traffic has stopped everywhere before the process receives SIGTERM.

### Termination and traffic routing

As Pods enter termination, Kubernetes updates their endpoint state.

Terminating endpoints are represented with conditions that allow consumers to distinguish them from ordinary ready endpoints.

Their `ready` condition is false for normal routing compatibility.

But networking updates and external load balancers may not react instantaneously.

Existing connections may remain active.

Some clients may continue sending requests briefly during propagation.

The application therefore needs to cooperate with shutdown rather than assuming that the moment termination begins, nobody can possibly reach it.

### A good API shutdown sequence

For an HTTP API, an orderly shutdown often includes:

1. Stop accepting new application work.
2. Begin draining or closing relevant listeners and connections.
3. Allow existing requests to finish within a bounded deadline.
4. Persist necessary state and flush critical telemetry.
5. Close resources and exit before the termination grace period expires.

The exact mechanisms depend on the application server, proxy configuration and traffic patterns.

A request that lasts two minutes cannot necessarily be allowed to finish when the entire shutdown window is thirty seconds.

The architecture must choose its timeouts and recovery behavior deliberately.

### A good RabbitMQ worker shutdown sequence

For our scanner worker, the desired behavior is different.

When SIGTERM arrives, it should stop accepting new messages and decide what to do with the work already in progress.

If an active scan can finish safely within the remaining time, it may complete the work, persist its results, and acknowledge the message.

If it cannot finish, the system must rely on its durable processing semantics to recover the task.

Under manual acknowledgment, an unacknowledged message can become eligible for redelivery when its channel or connection closes.

But redelivery does not roll back partial external effects.

The scan may already have contacted remote services or written some results.

This means the application needs a strategy for deduplication, resumption or safe repetition.

### The shutdown budget

A reasonable `terminationGracePeriodSeconds` should account for real workload behavior.

It must be long enough for the shutdown procedure that the system actually intends to perform.

But excessively long grace periods also slow replacement and resource release.

There is no universal correct value.

A fast stateless HTTP API and a worker performing long security scans may require very different shutdown strategies.

This is why termination design belongs in application architecture, not merely infrastructure configuration.

## 10. The Duplicate-Work Trap

Let's reconstruct our original incident.

The scanner worker receives message `scan-4821`.

It fetches DNS records, discovers endpoints and writes several findings.

Before it acknowledges the message, the Pod begins shutting down.

The application is killed after its grace period.

RabbitMQ detects that the message was not acknowledged and makes it available for redelivery.

A replacement worker receives `scan-4821`.

It performs the scan again.

Now the database contains duplicate findings unless the persistence layer prevents them.

Perhaps the first scan also consumed an external API quota or performed an expensive network operation.

Kubernetes didn't create the duplicate message.

It exposed the fact that the processing operation was not designed for interruption and replay.

### The business operation needs identity

A robust system might assign a stable scan identifier to the business task.

The database can use that identity, along with stable finding identifiers or version information, to prevent unintended duplicates.

A worker might use atomic state transitions or leases with fencing where appropriate.

For very long tasks, it might persist checkpoints and resume from known progress.

But the design must account for concurrency.

A naive pattern like "check whether the scan exists, then insert it" can race when two workers execute simultaneously.

Database uniqueness constraints, conditional updates and carefully designed state machines may be needed.

### Exactly-once is not a free infrastructure setting

Even if each message is delivered once under ideal conditions, crashes can introduce uncertainty between performing side effects and recording completion.

Kubernetes cannot guarantee exactly-once business execution.

RabbitMQ cannot generally guarantee exactly-once external side effects for arbitrary consumers.

The application must make repeated attempts safe enough for its business requirements.

For security scanning, repeating a DNS query may be harmless, but repeating an expensive third-party API call may have financial implications.

For payments, the consequences are much more serious.

The general principle is the same as in distributed systems:

**Design for uncertain execution boundaries, not imaginary uninterrupted processes.**

## 11. Jobs: When Completion Matters More Than Continuity

A Kubernetes Job is designed for work that reaches a terminal completion condition.

For example, suppose our platform launches a daily analysis that processes a finite collection of newly discovered domains.

We could represent this as a Job.

The Job's specification describes its Pod template and completion behavior.

The controller creates Pods and tracks successful completions.

### Completions and parallelism

A Job can use `completions` to express how many successful Pod completions are required.

It can use `parallelism` to express the desired maximum concurrency of active Pods under normal operation.

For example:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: nightly-enrichment
spec:
  completions: 6
  parallelism: 2
  backoffLimit: 3
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: enrich
          image: example.com/enrichment:v1
```

This illustrative Job aims for six successful completions, normally with up to two active Pods at a time.

But there's an important business question.

What does each successful Pod actually process?

Without additional coordination, six identical Pod executions could perform the same work six times.

Kubernetes doesn't automatically divide your company's domain database into six mutually exclusive business partitions just because you wrote `completions: 6`.

You need an appropriate work-distribution strategy.

That might be a task queue, explicit partition identifiers, or an Indexed Job where each successful completion corresponds to a logical index.

The application must still interpret that index safely.

### Jobs can repeat work

A Job controller attempts to achieve its completion condition despite failures.

However, a particular logical task can be attempted more than once under certain failure or replacement conditions.

Even Jobs designed for a single completion should tolerate the possibility of repeated execution.

This is another reason to avoid irreversible side effects without appropriate guards.

### Retry limits and deadlines

The Job's `backoffLimit` helps determine when repeated failures should cause the Job to be considered failed.

`activeDeadlineSeconds` places an overall active-time deadline on the Job. When reached, the Job can be terminated as failed even if the retry limit has not otherwise been exhausted.

These features bound execution attempts and duration. They do not determine whether the business operation is semantically recoverable.

When a Job is permanently Failed, Kubernetes does not automatically restart the whole completed-failure Job forever. Recovery requires a suitable higher-level action or new execution, depending on your system.

### Should each scan become a Job?

Not necessarily.

Imagine hundreds of thousands of short network checks per hour.

Creating a separate Kubernetes Job and Pod for every tiny check could impose unnecessary API, scheduling and container startup overhead.

A long-running Deployment of RabbitMQ consumers may be more economical and responsive for that workload.

Now imagine a scan that takes forty minutes, requires a specialized container image, has defined resource requirements and benefits from isolated execution.

A Kubernetes Job might be an excellent fit.

The choice depends on workload duration, isolation, startup overhead, scheduling needs and operational observability.

## 12. CronJobs: A Schedule Is Not a Transaction

A CronJob creates Jobs according to a schedule.

It is suitable for recurring batch tasks: periodic report generation, cleanup or scheduled data processing.

The syntax resembles traditional cron scheduling.

But a CronJob is not an exactly-once business scheduler.

There can be delays, missed schedules, controller interruptions and situations where multiple executions are possible.

Applications must tolerate those conditions.

### Concurrency policies

A CronJob supports several concurrency policies.

**Allow** permits Jobs created by the CronJob to overlap.

**Forbid** prevents a new scheduled Job from starting while a previous Job from the same CronJob is still running, causing the overlapping occurrence to be skipped.

**Replace** replaces the currently running Job with a new one when the schedule calls for another execution.

These policies apply to Jobs belonging to the same CronJob, not every similar job elsewhere in the cluster.

### The dangerous daily report

Suppose a report normally takes twenty minutes but occasionally takes ninety.

It runs every hour.

With Allow, two report processes may overlap.

With Forbid, an hourly occurrence may be skipped while the previous report still runs.

With Replace, the old report may be terminated before completing.

Which behavior is correct?

That depends on the business requirements.

A report that can safely be regenerated is different from a billing batch that must produce one authoritative invoice set for a defined period.

For important workflows, the business period needs a durable identity. A database may need to enforce that the same period cannot be finalized twice.

A schedule determines when work is attempted.

It does not automatically guarantee what the work means.

## 13. StatefulSets: Preserving Identity Across Replacement

A StatefulSet manages applications requiring stable identities or persistent storage association.

Consider a three-member database replica set.

Each member may need an identifiable role, stable network name and persistent data directory.

A StatefulSet can provide ordinal Pod identities such as:

`mongo-0`, `mongo-1` and `mongo-2`.

When a Pod is replaced, the same ordinal identity can be recreated.

With appropriate persistent volume claim templates, storage remains associated with that logical member rather than with a disposable Pod name generated during each rollout.

### Stable doesn't mean immortal

The Pod itself can still disappear.

Its container can still crash.

Its node can still become unreachable.

The important property is that the StatefulSet maintains a predictable identity relationship across replacements.

The persistent storage also has its own lifecycle and retention behavior.

Deleting a StatefulSet does not necessarily mean its persistent volume claims are deleted, and storage behavior depends on applicable retention policies and configuration.

This must be planned rather than assumed.

### Ordered operations

StatefulSets provide ordered creation, deletion and update behavior by default under their usual Pod management policy.

That can be useful for systems whose members have startup dependencies.

But the infrastructure order is not a replacement for application-level coordination.

A database cluster may need one member to be elected primary, replicas to synchronize, and old members to be safely fenced during failover.

Kubernetes does not infer those rules from the existence of three numbered Pods.

### The split-brain danger

Suppose a database node becomes unreachable from the control plane, but the process is still running and communicating with some clients.

A replacement may eventually be created or a recovery operation may be initiated.

If the application does not correctly enforce membership and fencing, two processes may believe they have authority over the same logical role or storage.

This is precisely the kind of failure that makes stateful infrastructure dangerous.

StatefulSet identity is useful. Application-level consensus and storage safety are still essential.

A properly designed database operator can help coordinate these concerns, but it too must respect the database's safety guarantees.

## 14. DaemonSets: The Population Follows the Nodes

A DaemonSet ensures that a Pod exists on each eligible node, or on an eligible subset selected through configuration.

Our security platform might deploy a node-level telemetry collector.

If a new node is added, the DaemonSet controller notices that the new node requires an agent.

If the node is removed, its corresponding workload no longer needs to exist.

This differs from a Deployment with three replicas.

A Deployment targets an application population size.

A DaemonSet targets a relationship between eligible nodes and Pods.

### Why not run everything as a DaemonSet?

Imagine an API that requires three replicas.

If the cluster currently has ten nodes and you use an unrestricted DaemonSet, you'll generally ask Kubernetes to run an instance on every eligible node.

You may end up with ten API instances instead of three.

Moreover, the workload's scale is now coupled to cluster node count rather than application demand.

This is usually the wrong abstraction for an ordinary service.

DaemonSets are strongest when node locality is itself part of the requirement.

Network agents, log shippers and node-level monitoring tools are common examples.

## 15. Workload Choice Is an Architectural Decision

Let's classify the components of our cybersecurity platform.

The HTTP API is a continuously serving application with interchangeable replicas. A Deployment is a natural choice.

The RabbitMQ consumers are long-lived processes. A Deployment also makes sense, even though the workers perform background tasks.

A large isolated scan that should run until completion might be represented by a Job.

A scheduled nightly reconciliation task might use a CronJob.

A database requiring stable identity and persistent storage may use a StatefulSet, often alongside database-aware operational automation.

A node telemetry agent might use a DaemonSet.

Notice what this classification is based on.

Not programming language.

Not whether the process connects to MongoDB.

Not whether the container image is large.

And not whether the team calls the service a microservice.

The classification depends on **what must remain true about the workload over time**.

That is the deeper meaning of Kubernetes workload abstractions.

## 16. Failure Investigation: A Senior Engineer's Decision Tree

Suppose someone tells you: "Kubernetes is broken. The scanner workers aren't working."

That's not a diagnosis.

You need to determine which lifecycle stage and controller guarantee has failed.

### Case A — No Pods exist

Check whether the Deployment, Job or other workload object exists.

Does its specification actually request active instances?

Is the controller creating the required child resources?

Are selectors and ownership relationships correct?

### Case B — Pods remain Pending

Inspect scheduling events and Pod conditions.

The scheduler may have no eligible node, or image retrieval and initialization may still be in progress.

Don't assume every Pending Pod is a scheduler failure. The Pod phase is broad.

### Case C — Containers repeatedly restart

Inspect container waiting and termination reasons, restart counts, prior logs and Pod events.

Possible causes include application crashes, liveness probe failures, configuration errors or resource-related termination.

Distinguish whether the same Pod is restarting containers or whether entire Pods are being replaced.

### Case D — Pods run but never become ready

Investigate startup and readiness probes.

Check whether the application can perform its intended work and whether probe definitions accurately reflect that capability.

Don't immediately loosen probes until everything turns green.

A green dashboard produced by disabling meaningful readiness checks can be worse than an honest unhealthy status.

### Case E — A rollout is stuck

Inspect the old and new ReplicaSets.

Determine whether new Pods can be scheduled, start successfully and become available.

Check whether surge capacity exists and whether rollout conditions indicate stalled progress.

Don't assume `progressDeadlineSeconds` caused automatic rollback.

### Case F — Work is duplicated after a deployment

Inspect application shutdown handling, queue acknowledgment semantics, worker concurrency and persistence invariants.

The deployment may have correctly replaced the Pods while the business workflow mishandled interruption.

The problem may not be the Kubernetes controller at all.

### Case G — The database Pod was replaced but recovery failed

Inspect persistent storage attachment, member identity and database-specific recovery state.

A replacement Pod existing is not proof that the database replica has rejoined safely.

The next investigation belongs partly to the database's own clustering and durability mechanisms.

## 17. The Oral Examination

Try these aloud before looking at the answers. A strong response should explain a sequence of events and defend a decision, rather than merely name a Kubernetes resource.

### Challenge 1 — The Restarts That Never End

A Pod is Running but shows 31 restarts and the `CrashLoopBackOff` reason.

What can you infer, and what can you not infer? How would you determine whether the problem is application startup, liveness probing or something else?

### Challenge 2 — The Correct Controller

Your platform has two possible scanning systems.

System A uses a pool of permanently running workers that pull short tasks from RabbitMQ.

System B launches isolated scans that can each run for forty minutes, then finish and exit.

Would you use Deployments or Jobs? Explain why.

### Challenge 3 — The Readiness Disaster

All API replicas use a liveness probe that checks whether MongoDB is reachable.

MongoDB becomes temporarily unavailable.

Describe a plausible chain of failures, and propose a better health-check design.

### Challenge 4 — The Stalled Rollout

A critical service has four replicas.

Its Deployment uses `maxSurge: 1` and `maxUnavailable: 0`.

The cluster has no remaining capacity for another Pod.

What happens when you roll out a new image, and what are your options?

### Challenge 5 — The Duplicate Scan

A worker writes results to MongoDB, then crashes before acknowledging its RabbitMQ message.

A replacement worker receives the same message.

What should the application's processing contract guarantee?

### Challenge 6 — The Misleading StatefulSet

A team deploys a database with three StatefulSet replicas and announces that database availability and correctness are now guaranteed.

What have they misunderstood?

### Challenge 7 — The CronJob That Sends Two Invoices

A billing CronJob runs daily.

A controller or scheduling problem causes a duplicate execution for the same billing period.

How would you design the business workflow so that this doesn't produce duplicate invoices?

## 18. Solutions and Discussion

### Solution 1 — Distinguish the layers

Repeated container restarts suggest that the kubelet has repeatedly attempted to recover container execution within the Pod.

`CrashLoopBackOff` indicates restart backoff, not the root cause.

Inspect `kubectl describe pod`, container last termination reasons, current and previous logs, resource-related events and probe failures.

Determine whether the process exits on its own, is killed by liveness failures, or encounters another condition.

A Pod being Running does not imply the application is ready or useful.

### Solution 2 — Match process lifetime to workload semantics

A Deployment is appropriate for the long-lived RabbitMQ consumers. Their processes continuously receive independent messages and should generally remain running.

Jobs are attractive for the bounded isolated scans, especially when per-scan resource allocation, completion status and execution isolation matter.

However, a Job-per-task architecture has startup and control-plane overhead. If tasks are sufficiently short or numerous, a worker pool may be preferable.

### Solution 3 — Dependency health is not process liveness

When MongoDB fails, every API Pod may fail its liveness check and restart.

The simultaneous restarts can cause connection storms and delay recovery.

The application should use liveness to detect internal conditions requiring process restart, readiness to indicate its capacity to serve relevant traffic, and startup probes where initialization needs protection.

Critical dependency checks must be chosen carefully to avoid cascading failures or removing all capacity unnecessarily.

### Solution 4 — The rollout may not have sufficient capacity

With four desired replicas, no permitted unavailability and one allowed surge Pod, the Deployment needs suitable capacity to create a new Pod before reducing old available capacity.

If no eligible node can accommodate it, the rollout may stall.

Options include adding capacity, reducing resource requirements where justified, changing rollout parameters with an understood availability trade-off, or choosing another deployment approach.

Never change `maxUnavailable` blindly for a critical service.

### Solution 5 — Durable, replay-safe processing

The worker may have performed its effects before the acknowledgment was lost.

The replacement may repeat the attempt.

The application should identify the logical scan independently of its execution attempt and enforce appropriate deduplication, atomic state transitions or resumability.

It may need uniqueness constraints or other concurrency-safe mechanisms in MongoDB.

Acknowledgment should follow the appropriate durable completion point, and duplicate attempts should not produce unacceptable duplicate effects.

### Solution 6 — StatefulSet is not a database consensus protocol

A StatefulSet provides stable identities and useful persistent storage associations.

It does not automatically handle database leader election, transaction durability, quorum, replica synchronization, failover fencing or recovery consistency.

Those remain the responsibility of the database software and its operational automation.

### Solution 7 — The billing period must have business identity

A scheduled execution is an attempt to process a business period.

The period itself should have a stable identifier, such as the relevant billing cycle.

The system should use durable state and database constraints to ensure that finalizing the same period twice cannot generate duplicate authoritative invoices.

CronJob concurrency settings may reduce accidental overlaps but do not replace application-level correctness.

## 19. The Mental Model Worth Keeping

A Kubernetes workload is a promise about **time, identity and recovery**.

A Deployment promises to maintain a population of running application replicas.

A Job seeks successful completion.

A CronJob schedules Job creation attempts.

A StatefulSet preserves useful logical identity and storage relationships.

A DaemonSet maintains node-related coverage.

A Pod is an execution unit, not a permanent process.

And when a Pod disappears, Kubernetes can restore execution capacity—but your application remains responsible for the meaning, durability and correctness of the work that was interrupted.

When choosing a workload, ask:

**Should this process keep running, finish once, run periodically, keep its identity, or follow the nodes?**

When investigating failure, ask:

**Was a container restarted, a Pod replaced, a workload rolled out, or a business operation repeated?**

Those two questions will save you from an astonishing amount of Kubernetes confusion.

## 20. Next Lecture — SE450-L03: Cluster Networking and Service Discovery

Our applications can now start, run, stop and recover.

But how do they communicate?

A Pod gets an IP address, but Pods are disposable. An API instance can disappear and return with a different IP. A Service can route traffic to changing backends, while DNS provides stable names.

What happens when the DNS lookup succeeds but the connection fails? What if the Service exists but has no eligible endpoints? What if a NetworkPolicy blocks the traffic?

In the next lecture, we'll follow packets through Kubernetes networking, from service discovery to Pod routing and network policy enforcement.

*The spoken lecture ends here. The remaining material is for hands-on investigation and screen-based revision.*

---

## Optional Practical Lab — Watch a Rolling Update Succeed, Stall, and Recover

**Objective:** Observe Pod replacement, controller ownership, rollout behavior and readiness gating in a disposable practice environment.

**Requirements:** A working local Kubernetes cluster (Minikube or kind), `kubectl`, and permission to create a namespace and Deployments.

Do not execute this lab against a production cluster.

### Lab A — Create an isolated namespace

First verify the selected context:

```bash
kubectl config current-context
kubectl get nodes
```

Create a practice namespace, using a unique name if it already exists:

```bash
kubectl create namespace se450-l02
```

All subsequent commands explicitly use the practice namespace.

### Lab B — Deploy a healthy application

Create `web.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      terminationGracePeriodSeconds: 30
      containers:
        - name: nginx
          image: nginx:stable-alpine
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 3
            failureThreshold: 2
          livenessProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 10
            failureThreshold: 3
```

Apply the manifest:

```bash
kubectl apply -n se450-l02 -f web.yaml
kubectl rollout status -n se450-l02 deployment/web
```

Inspect the ownership hierarchy:

```bash
kubectl get deployments -n se450-l02
kubectl get replicasets -n se450-l02
kubectl get pods -n se450-l02 -o wide
```

Choose one Pod, inspect its metadata and find its controller reference:

```bash
kubectl get pod POD_NAME -n se450-l02 -o yaml
```

**Question:** Why are Pods controlled by a ReplicaSet rather than being directly created by the Deployment as independent unmanaged objects?

### Lab C — Delete a managed Pod

Open a terminal that watches the Pods:

```bash
kubectl get pods -n se450-l02 -w
```

In another terminal, delete one Pod by name:

```bash
kubectl delete pod POD_NAME -n se450-l02
```

Watch the replacement appear.

Inspect its UID and compare it with the original if you recorded the earlier UID.

**Question:** Did Kubernetes restart the original container, or create a different Pod? How can you prove the difference?

### Lab D — Deliberately break readiness

Create a new version of `web.yaml` by changing the readiness probe path from `/` to `/does-not-exist`.

Do not change the liveness probe.

Apply the modified manifest:

```bash
kubectl apply -n se450-l02 -f web.yaml
```

Watch the Deployment and ReplicaSets:

```bash
kubectl get deployments -n se450-l02 -w
```

In another terminal:

```bash
kubectl get replicasets -n se450-l02
kubectl get pods -n se450-l02
```

Try checking rollout completion with a bounded wait:

```bash
kubectl rollout status -n se450-l02 deployment/web --timeout=45s
```

The rollout is expected not to complete successfully while the replacement Pods fail readiness.

Inspect events:

```bash
kubectl describe deployment web -n se450-l02
kubectl get events -n se450-l02 --sort-by=.metadata.creationTimestamp
```

**Questions:**

1. Why can the containers be Running while the Deployment rollout remains incomplete?
2. Why do the old available replicas remain important?
3. Why does Kubernetes not automatically roll back simply because the new Pods fail readiness?
4. What would happen if you had also made the liveness probe point to a nonexistent endpoint?

### Lab E — Recover the previous revision

Use the Deployment's rollback mechanism:

```bash
kubectl rollout undo deployment/web -n se450-l02
kubectl rollout status deployment/web -n se450-l02
```

Inspect the ReplicaSets and Pods again.

If the rollback cannot proceed, inspect rollout history, availability and resource constraints rather than deleting resources randomly.

**Question:** What information did the Deployment retain that allowed it to return to a previous Pod template?

### Lab F — Run bounded work as a Job

Create `job.yaml`:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: bounded-work
spec:
  completions: 3
  parallelism: 2
  backoffLimit: 2
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: task
          image: busybox:1.36
          command:
            - sh
            - -c
            - |
              echo "Starting a bounded task"
              sleep 5
              echo "Task completed"
```

Apply it:

```bash
kubectl apply -n se450-l02 -f job.yaml
kubectl get jobs -n se450-l02 -w
```

In another terminal:

```bash
kubectl get pods -n se450-l02 -l job-name=bounded-work
kubectl describe job bounded-work -n se450-l02
```

**Questions:**

1. Why doesn't the Job keep restarting completed Pods forever?
2. How many successful completions are required?
3. What does `parallelism: 2` control?
4. If the command had written the same database record three times, would Kubernetes automatically prevent duplicates?

### Lab G — Cleanup

After verifying the namespace is the isolated practice environment you created for this lecture, remove it:

```bash
kubectl delete namespace se450-l02
```

Do not run namespace deletion against a shared environment without verifying its contents and ownership.

---

## Further Reading

1. [Pods](https://kubernetes.io/docs/concepts/workloads/pods/) — Pod execution semantics and ownership.
2. [Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) — Phases, container states, restart policies and termination.
3. [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) — ReplicaSets and rolling updates.
4. [Configure Liveness, Readiness, and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/) — Probe behavior and configuration.
5. [Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/) — Completion-oriented workloads.
6. [CronJobs](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/) — Scheduled Jobs and concurrency policies.
7. [StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/) — Stable identity and storage associations.
8. [DaemonSets](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/) — Node-local workload management.
9. [Init Containers](https://kubernetes.io/docs/concepts/workloads/pods/init-containers/) and [Sidecar Containers](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/) — Startup ordering and supporting containers.

---

## Dense Cheatsheet — Interview Glance Card

*This final fenced reference is intended for rapid visual revision rather than voice playback.*

```text
SE450-L02 — PODS, DEPLOYMENTS, JOBS, AND CONTROLLERS

THE FIVE WORKLOAD CHOICES

Deployment:
  Desired number of interchangeable running replicas
  Good for: APIs, long-lived queue consumers
  Manages ReplicaSets and rolling updates

Job:
  Bounded work with completion semantics
  Good for: finite data processing, isolated scans
  May retry; repeated work is possible

CronJob:
  Scheduled creation of Jobs
  Concurrency: Allow / Forbid / Replace
  Scheduling is not exactly-once business execution

StatefulSet:
  Stable ordinal identity + network identity + storage association
  Good for: stateful clustered applications
  Does NOT supply database quorum or consistency

DaemonSet:
  Pod on every eligible node (or selected nodes)
  Good for: logging, monitoring, CNI/node agents
  Population follows eligible nodes

POD
  Smallest schedulable workload unit
  One or more cooperating containers
  One node per Pod
  Shared network namespace/IP/port space
  Shared configured volumes
  Replacement Pod != live migration
  New Pod has new UID

POD PHASES
  Pending      Accepted; containers not all initialized/started
  Running      Bound; container running or starting/restarting
  Succeeded    Containers finished successfully
  Failed       Terminal unsuccessful state
  Unknown      Status unavailable

  CrashLoopBackOff != official Pod phase
  Terminating      != official Pod phase

CONTAINER RESTART VS POD REPLACEMENT
  Container restart:
    kubelet; same Pod; policy dependent
  Pod replacement:
    workload controller creates new Pod; new identity

POD RESTART POLICIES
  Always       Restart on termination
  OnFailure    Restart on nonzero exit
  Never        Don't restart inside this Pod

  Deployment requires Always
  Job usually OnFailure or Never

CONTROLLER HIERARCHY
  Deployment -> ReplicaSet -> Pods
  Job -> Pods
  CronJob -> Jobs -> Pods
  StatefulSet -> Pods
  DaemonSet -> Pods

  Labels/selectors determine matching
  OwnerReferences describe controller ownership

DEPLOYMENT UPDATES
  RollingUpdate   Gradual old/new population replacement
  Recreate        Old revision terminates before new revision starts

  maxSurge        Extra non-terminating Pods above desired count
  maxUnavailable  Allowed unavailable desired replicas

  Defaults: 25% each
  maxSurge rounds UP
  maxUnavailable rounds DOWN

  progressDeadlineSeconds:
    Detects lack of rollout progress
    Does NOT automatically roll back

PROBES
  Startup:
    Has initialization completed?
    Holds back liveness/readiness until success

  Readiness:
    Can this instance receive normal traffic?
    Failure marks unready; does NOT itself restart

  Liveness:
    Is this process unrecoverably unhealthy?
    Failure can trigger restart

  BAD IDEA:
    Restart every API Pod if shared MongoDB fails briefly

  BETTER:
    Conservative liveness
    Meaningful readiness
    Startup window where necessary

INIT CONTAINERS
  Regular init containers run sequentially before app containers
  Must finish successfully
  Can repeat; make idempotent
  Avoid uncontrolled global migration races

SIDECARS
  Cooperating helper containers
  Native sidecars use restartable initContainers
  Shutdown ordering can preserve helper availability
  Adds Pod lifecycle and placement coupling

GRACEFUL TERMINATION
  Pod deletion timestamp + grace period
  preStop hook (if configured) consumes grace time
  SIGTERM normally delivered to main container process
  Application drains and exits
  SIGKILL after timeout if still running

  Default grace period: 30 seconds
  Endpoint updates are asynchronous
  Terminating endpoints marked not ready for normal traffic
  Old connections may still exist

WORKER SHUTDOWN
  Stop consuming new messages
  Finish bounded in-flight work if possible
  Persist completion/checkpoint
  ACK only after appropriate durable processing
  Unacknowledged messages may be redelivered
  Deduplicate business effects

JOBS
  completions   Required successful completions
  parallelism   Desired active Pod concurrency
  backoffLimit  Failure retry limit
  activeDeadlineSeconds  Overall Job time limit
  restartPolicy Usually Never or OnFailure

  Kubernetes does not divide business work automatically
  Job completion != exactly-once external side effect

CRONJOBS
  Allow     Runs may overlap
  Forbid    Skip scheduled run when previous still active
  Replace   Replace running Job with new scheduled Job
  Duplicate/missed/delayed execution possible
  Give business period a durable identity

STATEFULSETS
  Stable ordinal names: db-0, db-1, db-2
  Persistent volume claims associated with logical members
  Ordered behavior by default
  State storage can outlive Pods
  NOT a substitute for database failover/fencing/consensus

DAEMONSETS
  One Pod per eligible node
  Automatic coverage as eligible nodes change
  Node locality is the requirement

SENIOR TROUBLESHOOTING
  No Pods?        Controller, selectors, ownership, desired count
  Pending?        Scheduling, images, init, storage
  Restarting?     Logs, exit status, probes, OOM
  Not Ready?      Readiness, startup, dependencies
  Rollout stuck?  Capacity, ReplicaSets, maxSurge, readiness
  Duplicate work? Shutdown, broker ACKs, idempotency
  DB failure?     Storage, membership, consensus, fencing

SENIOR LINE:
  "Choose the Kubernetes controller according to process
   lifetime, identity and completion semantics. Kubernetes
   restores execution capacity; the application must preserve
   correctness when execution is interrupted or repeated."
``` 
