---
id: SE450-L01
course: SE450
title: "Kubernetes: A System That Reconciles Reality"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: null
next: SE450-L02
---




# SE450 — Kubernetes and Platform Engineering

## Lecture 01: Kubernetes — A System That Reconciles Reality

*You tell a computer what you want. It decides what must happen. The machines disagree, crash, disappear, and recover. Somehow, the system keeps trying.*

---

# Part I — Intuition

## The picture to carry in your head

Imagine that you operate a cybersecurity platform. Customers submit domains to scan, your API accepts their requests, and background workers investigate the assets.

The platform runs across several servers. You have three identical instances of the API because a single instance would be a fragile point of failure.

On Monday morning, one server disappears.

Not metaphorically. Its virtual machine stops responding. Perhaps the host crashed. Perhaps a cloud provider terminated it. Perhaps somebody accidentally deleted it.

One of your three API instances has vanished.

What happens next?

If you built everything manually, somebody needs to notice the failure, choose another server, start another instance, connect it to the network, and verify that the service is healthy.

A monitoring system could send an alert. A script could restart the application. A load balancer could stop routing traffic to the failed machine.

But those are separate mechanisms, and somebody has to coordinate them.

Kubernetes approaches the problem differently.

Instead of telling it, "Start these three processes," you declare:

**"I want three replicas of this application to exist."**

Kubernetes remembers that requirement.

When one disappears, the system doesn't need a new instruction from you. It already knows that the current world violates the declared requirement, and its controllers attempt to correct it.

This is the central idea of Kubernetes.

Not containers. Not YAML. Not microservices.

**Reconciliation: continuously comparing what should exist with what actually exists, then attempting to reduce the difference.**

## 1. A thermostat for an entire computing platform

Picture a thermostat in your apartment.

You set the temperature to 22 degrees.

The room is currently at 19 degrees. The thermostat detects the difference and activates the heating.

Eventually, the temperature approaches 22.

Then somebody opens a window. The room cools. The thermostat responds again.

You don't give the thermostat a fresh instruction every time the environment changes. You define the target, and a control loop keeps working toward it.

Kubernetes follows a similar pattern, although the controlled environment is far more complicated.

The desired condition might be three running application replicas. The observed condition might be only two.

A controller notices the discrepancy and requests the creation of another replica.

Later, the application might be upgraded. Now the desired condition includes a new container image.

The system notices that the existing replicas do not match the new specification and begins changing them.

The key distinction is between a **one-time command** and a **persistent declaration**.

A command says, "Do this now."

A declaration says, "This is the condition I want maintained."

### Visual anchor — the control loop

```text
        DESIRED STATE
          3 replicas
              |
              v
       +-------------+
       |  CONTROLLER |
       |  Compare    |
       +-------------+
          ^       |
          |       v
       Observe   Act
          |       |
          +-------+
              |
        ACTUAL CLUSTER
       2 running replicas
```

The controller doesn't have to perform a dramatic intervention. If the world already matches the desired state, it may have nothing to change.

This is important because a healthy Kubernetes cluster is not constantly rebuilding itself. Its control loops keep observing, reacting and deciding whether intervention is necessary.

## 2. The declaration survives the person who made it

Suppose you submit a configuration describing three replicas and then close your laptop.

The application doesn't depend on your terminal remaining connected.

Kubernetes stores the declared configuration as part of the cluster's persistent API state.

Controllers running inside the cluster continue to reconcile resources after your terminal disappears.

This gives the platform a useful property: the person or deployment pipeline that originally requested the application does not need to remain alive to supervise it.

A DevOps engineer, CI/CD workflow or GitOps controller can declare intent. The cluster takes responsibility for attempting to realize that intent.

Notice the careful wording: **attempting**.

Kubernetes cannot manufacture CPU capacity from nothing. It cannot pull an image from an unavailable registry. It cannot repair arbitrary application bugs.

If you demand ten replicas but the cluster has enough resources for only six, declaring ten does not magically produce four more healthy instances.

The desired state remains ten. The observed state exposes the shortfall.

Kubernetes can report that the system is not converging. It cannot guarantee that every requested condition is physically achievable.

## 3. Kubernetes is a society of specialists

Now imagine a city government.

One office accepts applications and maintains official records.

Another decides where new buildings may be constructed.

Another tracks whether the required buildings actually exist.

Local inspectors visit the sites and make sure construction follows the approved plans.

Kubernetes divides responsibility in a comparable way.

There is an **API server**, which exposes the cluster's official interface.

There is a persistent store called **etcd**, which records the cluster's API state.

There are **controllers**, which notice mismatches and request changes.

There is a **scheduler**, which decides which eligible machine should host a new Pod.

And there is a **kubelet** running on each node, responsible for making the assigned Pods run through a container runtime.

No single component performs the entire operation.

The system works because each participant handles a particular responsibility and communicates through shared API state.

### Visual anchor — the team

```text
             YOU / CI PIPELINE
                    |
                    v
               API SERVER
                    |
             Persistent state
                 (etcd)
                    |
          +---------+---------+
          |                   |
     CONTROLLERS          SCHEDULER
     What is missing?     Where should
                          it be placed?
          |                   |
          +---------+---------+
                    |
                API STATE
                    |
                  KUBELET
                    |
             CONTAINER RUNTIME
                    |
             RUNNING CONTAINERS
```

This is a conceptual diagram, not a literal network trace. The API server is the central coordination interface; controllers and the scheduler do not normally manipulate etcd directly.

## 4. The API can accept success while the application still fails

Here is a subtle but extremely important distinction.

You apply a configuration. Kubernetes responds successfully.

Does that mean the application is running?

No.

It means the API operation was accepted and the relevant resource state was recorded.

The scheduler may not yet have selected a node.

The kubelet may not yet have pulled the image.

The application may crash immediately after starting.

The Pod may exist but never become ready to receive traffic.

The API's successful response is not a promise that the real-world outcome has already occurred.

This is a familiar distributed-systems problem wearing different clothing.

**Accepted intent, observed progress and achieved outcome are three different things.**

You can inspect them separately.

And a senior engineer who understands Kubernetes will never confuse them.

## 5. A disappearing server

Return to our three API replicas.

All three are running. Then one node dies.

The cluster eventually detects that the node is no longer healthy.

Controllers responsible for the affected resources react according to their rules. The old workload may be marked unavailable or removed, and a replacement Pod may be created.

The scheduler finds an eligible node for that replacement.

The kubelet on the selected node starts the required containers.

If the application starts and becomes ready, the available replicas return toward the declared target.

This takes time. Node failure detection, Pod replacement, image downloads, startup and readiness all contribute to recovery delay.

Kubernetes does not promise instantaneous failover.

And it does not necessarily preserve the identity or memory of the old application instance.

If the old process held an unfinished scanning task only in RAM, that task might be lost.

Kubernetes can restore the existence of the worker process. It cannot automatically reconstruct the business operation the process was performing.

For that, the application needs durable work tracking, acknowledgments, retries and idempotency.

**Infrastructure recovery and business recovery are related, but they are not the same problem.**

## Your mental checkpoint

Before moving on, answer these aloud.

1. Why is declaring "three replicas" different from executing "start three processes"?
2. Why can a successful API response precede an unsuccessful deployment?
3. Which part of a Kubernetes cluster decides where a Pod should run, and which part actually starts its containers?

If you can answer those questions, you already possess the fundamental picture.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The Cluster That Kept Rebuilding a Broken Application

Consider an external attack-surface management platform.

Its architecture includes an HTTP API, an asset database, a message broker and scanner workers. The API receives scan requests; workers eventually perform the expensive investigations.

The API has been packaged into a container image. The team has deployed it onto Kubernetes.

One evening, a developer notices that the API has restarted repeatedly.

The engineer checks the running containers, identifies the failing one and deletes its Pod.

A replacement appears.

It crashes.

Another replacement appears.

It crashes too.

The developer becomes increasingly annoyed.

"Why does Kubernetes keep restarting this thing when it's obviously broken?"

Because Kubernetes is following instructions.

The declared requirement says that an application replica should exist and run. The observed state repeatedly fails to satisfy that requirement.

The system attempts reconciliation.

But the desired application configuration is defective. Perhaps a required environment variable is missing. Perhaps the process cannot connect to MongoDB. Perhaps the image has a broken entrypoint.

Kubernetes is successfully enforcing an unsuccessful specification.

This gives us our first serious principle:

**A reconciliation system can be operationally correct while the application it manages remains completely broken.**

We will spend this lecture understanding how that happens.

## 2. What Kubernetes Actually Manages

Kubernetes is an extensible orchestration platform built around an API and controllers. Its core purpose is to manage containerized workloads and their supporting resources across a collection of machines.

A cluster contains a **control plane** and a set of **nodes**.

The nodes provide computing resources. They are the machines—physical or virtual—on which workloads execute.

The control plane manages the cluster's API, stored state, placement decisions and controllers.

An application does not normally ask Kubernetes to run a bare container as its primary abstraction. It defines resources that eventually result in **Pods**, which are the fundamental deployable units for workloads.

A Pod can contain one or more closely cooperating containers. Those containers share some execution context, including network namespace and volumes defined for the Pod.

Most ordinary backend applications run one main application container per Pod, but that is a convention rather than a requirement.

Kubernetes then provides higher-level workload objects that manage Pods.

For example, a Deployment manages a declarative application rollout through ReplicaSets, while a Job represents work that should run to completion.

In this lecture, we will use a Deployment as an example because its control loop is easy to understand. The full differences among Deployments, StatefulSets, Jobs, DaemonSets and other workloads belong to SE450-L02.

For now, focus on the abstraction:

**The API stores objects describing the intended system, and controllers interpret those objects into actions.**

## 3. The API Server — The Cluster's Front Door

Suppose you execute `kubectl apply -f api.yaml`.

`kubectl` is a client. It reads your configuration and communicates with the Kubernetes API server.

The API server performs several jobs.

First, it authenticates the caller and determines whether the operation is authorized. A valid cluster credential does not automatically permit every possible modification.

Second, it validates the request against the relevant API contract. The resource must use an appropriate API version and kind, and its fields must satisfy applicable rules.

Third, the request may pass through admission mechanisms that can reject or modify resource definitions. Policy enforcement, defaulting and injected configuration can therefore affect the accepted object.

Finally, a successful create or update is persisted through the API server's configured storage backend, ordinarily etcd.

The API server returns the result of the API operation.

Notice what it has not done.

It has not personally chosen a worker node. It has not started a Linux process. It has not necessarily downloaded the container image.

It has changed the cluster's authoritative API state.

Other components observe that change and respond.

This distinction explains why `kubectl apply` can succeed while `kubectl rollout status` later reports that progress has stalled.

### Why the API boundary matters

Kubernetes components generally coordinate through its API rather than editing a shared database or directly commanding every other component.

The scheduler observes unscheduled Pods and records placement decisions using the API.

Controllers observe resources and modify or create dependent resources through the API.

Kubelets observe Pods assigned to their nodes and report their status.

This separation produces a system that can evolve through independently operating components.

It also creates failure modes.

If the API server is unavailable, clients cannot reliably submit or inspect changes. Controllers and schedulers may lose their normal coordination channel. Existing containers, however, may continue running on healthy nodes because an API outage is not the same event as terminating every Linux process.

The exact result depends on which components fail and for how long.

**The control plane's availability and the application's immediate runtime availability are distinct operational concerns.**

## 4. etcd — Remembering the Cluster's Intent

The API server needs persistent state.

If every controller's knowledge existed only in RAM, restarting the control plane could make the cluster forget what it was supposed to maintain.

Kubernetes commonly uses etcd, a distributed key-value store designed for consistent state management.

It stores Kubernetes API objects and related cluster state.

For example, the cluster must remember that the `scanner-api` Deployment requests three replicas and specifies a particular container image.

That information survives the laptop that submitted it and, assuming the storage system remains healthy, survives ordinary controller restarts.

etcd is not the application database.

Your MongoDB collections do not magically live inside etcd. Neither do the business records in PostgreSQL.

etcd stores Kubernetes cluster state, not arbitrary application persistence.

This distinction matters enormously when planning backups.

If you lose the cluster's etcd state, you may lose critical resource configuration and control-plane records.

If you lose MongoDB, Kubernetes might happily restart three API replicas that can no longer access their customer data.

The two failures are different and require different recovery strategies.

### Why consistency is valuable here

Imagine two controllers acting on incompatible versions of the same resource.

Without coordination, they could overwrite one another's updates or make contradictory assumptions about the current specification.

Kubernetes API objects carry version metadata that supports concurrency control.

The field `metadata.resourceVersion` identifies a version of an object for API operations. It is opaque and should not be interpreted as a wall-clock timestamp or universally increasing numeric counter.

A client performing an update can use version-aware API semantics to detect conflicting changes.

Watchers can also track resource changes over time.

This does not make every multi-object Kubernetes operation globally transactional. It gives clients useful primitives for coordinating modifications to individual API resources.

### The operational consequence

Control-plane state is critical infrastructure. It deserves access controls, backup procedures, recovery testing and capacity planning.

Treating etcd as "just another internal container" is a serious mistake.

## 5. Desired State, Observed State, and Object Identity

A typical Kubernetes resource contains several important sections.

The field `apiVersion` identifies which API contract is being used.

The field `kind` identifies the resource type.

`metadata` contains identifying and organizational information.

`spec` describes the desired characteristics of the resource.

`status`, for resources that expose it, reports observations made by the system.

For our API Deployment, the intended replica count appears in the specification.

A simplified configuration might look like this:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scanner-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: scanner-api
  template:
    metadata:
      labels:
        app: scanner-api
    spec:
      containers:
        - name: api
          image: example.com/scanner-api:v1
```

The example declares three instances of the application. The image name is illustrative, not a runnable public image.

The Deployment controller will attempt to make the cluster match the declared configuration by managing subordinate workload resources.

Meanwhile, the Deployment's status might report only two available replicas.

The specification says three. The status says two.

That discrepancy is not inherently an error in the API.

It is a statement about reality.

The controller's job is to respond according to its reconciliation rules.

### A subtle detail: generation versus observed generation

For many Kubernetes resources, `metadata.generation` changes when the desired specification changes.

A controller may expose `status.observedGeneration`, indicating which desired generation it has observed or processed according to that resource's semantics.

This is useful when reasoning about stale status.

Suppose you update the desired replica count from three to five. Immediately afterward, the status may still describe the previous generation.

Until the controller has observed the updated specification, interpreting that status as a final result would be premature.

But even when observed generation has caught up, the requested state may not yet have been achieved. You must still inspect readiness, availability and relevant conditions.

**Observed configuration is not equivalent to achieved configuration.**

### Names, UIDs, and labels

An object's name provides a human-readable identifier within its naming scope.

Its UID identifies the particular lifetime of that resource.

If you delete a Pod and a controller creates another Pod with a similar name, that replacement is a new object.

Labels are key-value metadata used to organize and select resources. They are essential because controllers and Services often identify related objects through label selectors.

Annotations also carry metadata, but they are not principally intended for selector matching.

These distinctions help explain why a Deployment can maintain stable application identity even while the individual Pods continually change.

## 6. Controllers — The Heart of the System

We now reach the central mechanism.

A controller is a control loop that observes resources and attempts to make relevant actual conditions agree with desired conditions.

In simplified pseudocode:

```python
while True:
    desired = read_desired_state()
    actual = observe_current_state()

    changes = calculate_required_actions(desired, actual)

    perform_or_request(changes)
    wait_for_next_reconciliation()
```

This is a conceptual model, not the literal implementation of every Kubernetes controller.

Real controllers typically use API watches, cached objects, event queues and reconciliation functions. They may also requeue objects after delays or periodically revisit them.

This matters because Kubernetes is not necessarily running a brute-force loop that scans every object every millisecond.

It is a distributed, event-driven control system whose controllers react to changes and retry work when necessary.

### One controller, one responsibility

Kubernetes is not controlled by a single giant algorithm that understands every possible resource.

Instead, multiple controllers maintain different kinds of relationships.

For example, a Deployment controller manages the desired rollout and corresponding ReplicaSets.

A ReplicaSet controller attempts to maintain the required number of Pods matching its selector.

A Job controller coordinates Pods that perform completion-oriented work.

A node-related controller participates in detecting node health problems and managing the consequences.

Each controller has a relatively narrow responsibility.

This division is extremely important.

The Deployment controller does not generally start containers directly. It works through other API objects.

The ReplicaSet controller does not decide which physical machine should execute each Pod.

And the scheduler does not directly run the application either.

Several control loops and agents cooperate to produce the final outcome.

### Reconciliation is not a one-shot transaction

Imagine that a controller observes two Pods when it expects three.

It asks the API to create another Pod.

Then its process crashes.

Was the operation completed?

Perhaps the API accepted it before the controller crashed. Perhaps the controller never received confirmation.

A robust controller must be able to observe the resulting state again and reconcile safely, without assuming that every prior attempt completed exactly once.

This is one reason Kubernetes controllers are designed around repeatable reconciliation rather than fragile sequences of one-time commands.

A controller should generally be able to revisit the same desired condition and make a sensible decision based on current state.

The detailed behavior depends on the specific controller, but the architectural principle is broadly applicable.

### Why writing a controller is harder than writing a script

A shell script might create a resource and exit.

A controller has to survive incomplete information, concurrent changes, failed API operations, restarts, stale caches and repeated events.

It also needs a way to decide whether progress has stopped, whether to retry, and how to communicate conditions to operators.

This is why the controller pattern is interesting far beyond Kubernetes.

It is a general method of building reliable automation around desired state.

## 7. From Deployment to Running Process — Follow the Entire Journey

Let's trace our scanner API into existence.

The user submits a Deployment requesting three replicas.

The API server validates and persists the resource.

The Deployment controller observes the Deployment and reconciles its desired state by creating or updating a ReplicaSet.

The ReplicaSet controller observes that ReplicaSet. If three Pods are required but none exists, it creates the missing Pod objects.

Those Pods initially have no node assignment.

The scheduler observes unscheduled Pods and determines suitable placement based on available information and constraints.

It records a binding decision through the Kubernetes API.

The kubelet on each selected node observes the assigned Pods and works with the container runtime to create the required execution environment.

The runtime starts the containers.

The kubelet continues monitoring and reporting relevant Pod and container state.

Meanwhile, higher-level controllers observe the evolving conditions and continue their own work.

This can be summarized as:

```text
Deployment
    |
    v
Deployment controller
    |
    v
ReplicaSet
    |
    v
ReplicaSet controller
    |
    v
Pod objects
    |
    v
Scheduler assigns nodes
    |
    v
Kubelets on those nodes
    |
    v
Container runtimes
    |
    v
Running containers
```

This sequence is a useful logical dependency graph. In reality, the components operate concurrently and asynchronously, communicating through the API.

There is no single central thread that pauses until every step completes.

### A consequence: the system is eventually coordinated

For a period of time, the Deployment may exist without a ReplicaSet.

A ReplicaSet may exist without all its desired Pods.

A Pod may exist without a node assignment.

A Pod may be assigned without its image being available locally.

A container may start without the application being ready to serve traffic.

These are not necessarily contradictions. They may be normal intermediate states.

The question becomes whether the system continues making progress and, if not, which boundary prevents convergence.

This is the basis of Kubernetes troubleshooting.

## 8. The Scheduler — Placement, Not Execution

The scheduler has a surprisingly specialized responsibility.

It looks for Pods that need node assignments and chooses suitable nodes.

The decision considers resource requests, available allocatable capacity, constraints and scheduling policies.

It may account for node labels, affinity rules, taints, topology preferences and other requirements.

A Pod requesting capabilities that no node can provide may remain Pending.

Adding more Kubernetes API servers will not solve that problem.

Nor will restarting the Deployment controller.

The scheduler cannot assign the Pod to a genuinely unsuitable node without violating the applicable constraints.

### Why the scheduler is not a resource manager for running processes

Once a Pod is bound to a node, the scheduler's primary placement decision is finished.

The kubelet and other components manage ongoing execution.

A Pod is generally not live-migrated from one node to another like a virtual machine being teleported while its memory is preserved.

If a node fails, a workload controller may cause replacement Pods to be created, and those new Pods may be scheduled elsewhere.

This is recreation, not transparent process migration.

A developer who assumes that Kubernetes automatically preserves in-memory state during rescheduling is going to have a bad day.

We will examine requests, limits, taints, affinity, topology and autoscaling in SE450-L04.

For now, remember:

**The scheduler decides where a Pod belongs; it does not personally execute the Pod.**

## 9. The Kubelet — Turning API Decisions into Local Reality

Every ordinary Kubernetes node runs a kubelet.

The kubelet is the node-level agent responsible for ensuring that Pods assigned to its node are realized through the available container runtime.

It interacts with the runtime to prepare and start containers, monitors their state, and reports observations back through the API.

For example, the scheduler may bind a Pod to node A.

The kubelet on node A then works to obtain the image and start the defined containers.

If the image cannot be pulled, the workload does not become healthy merely because a scheduling decision succeeded.

The kubelet reports the relevant problem through Pod status and events.

The control plane can observe that state.

### Container runtime versus kubelet

The kubelet is not the container runtime itself.

The runtime performs the low-level container lifecycle operations through the Container Runtime Interface.

Common Kubernetes deployments use containerd or another compatible runtime.

Linux namespaces, cgroups, process isolation and related mechanisms provide the actual operating-system execution environment.

Those concepts were introduced in SE340 and CS320.

Kubernetes adds distributed coordination around them.

### Node-local behavior during control-plane trouble

Suppose the API server becomes temporarily inaccessible.

Existing containers do not necessarily stop. The kubelet and runtime may continue managing local execution according to the state already available to them.

However, cluster-level changes, new scheduling decisions and reliable status coordination can be interrupted.

The control plane and node-level execution are related, but they do not share a single failure boundary.

This explains why a Kubernetes outage can produce a strangely mixed situation: existing applications continue serving traffic, but deployments, replacements or operational visibility become impaired.

## 10. Control Plane, Data Plane, and Everything Between

Engineers often divide Kubernetes infrastructure into control-plane and data-plane responsibilities.

The **control plane** decides what the cluster should maintain and coordinates resource changes.

The **data plane** carries application execution and traffic.

For our scanner API, the actual Node.js process serving HTTP requests belongs to the workload execution side.

The API server, scheduler and controllers belong to cluster coordination.

But do not overinterpret the distinction.

The kubelet is a node agent that participates in control and execution management. Networking components may maintain traffic rules based on resources observed through the Kubernetes API.

It is more accurate to think of control-plane versus data-plane as a separation of responsibility than as a perfectly clean division between two physical boxes.

### Why this distinction matters operationally

Imagine that the control plane is slow because its storage layer is overloaded.

Existing HTTP requests to healthy Pods may still succeed.

Now imagine the opposite: the API server is healthy, but the container network implementation is broken.

`kubectl get pods` may work perfectly while applications cannot communicate.

A successful control-plane query does not prove healthy application networking.

Likewise, a responsive application endpoint does not prove the cluster is capable of scheduling replacements.

A senior engineer asks: **Which plane, component and responsibility are actually failing?**

## 11. The Failure That Kubernetes Cannot Repair

Return to the opening incident.

The scanner API is configured with three replicas.

Its container starts, but it cannot connect to MongoDB because the application points to the wrong hostname.

Depending on the application and its health checks, it might crash, remain running but unready, or even report healthy while failing business operations.

Kubernetes responds only to the signals and policies it has been given.

If the application exits, the node-level workload machinery may restart the container according to the Pod's restart policy.

If a Pod disappears, its owner controller may arrange for a replacement Pod.

If the application keeps running but silently returns incorrect data, Kubernetes may have no reason to consider the Pod unhealthy.

This is the central limitation of infrastructure automation.

**Kubernetes reconciles resources and observable conditions. It does not automatically understand business correctness.**

### Self-healing has boundaries

There are several different questions:

- Is the container process running?
- Is the application capable of handling requests?
- Is the application behaving correctly?
- Are its dependencies available?
- Is the business operation durable and recoverable?

These are not interchangeable.

Health probes can help Kubernetes make useful decisions about process restart and traffic readiness. But a poorly designed probe can itself cause trouble.

For example, if every Pod restarts whenever a shared database becomes unavailable, a temporary database incident can turn into a large-scale application restart storm.

We will explore lifecycle, readiness, liveness and startup probes in SE450-L02.

### Kubernetes does not guarantee exactly-once processing

Suppose our scanner worker takes a job from a broker, starts scanning a domain, and then disappears.

Kubernetes may restore a worker replica.

But that does not tell us whether the original scan completed, partially completed, or produced external side effects.

The queue and application must define acknowledgments, retry behavior, deduplication and the identity of each business operation.

A Pod is an execution environment. It is not a transaction.

This is the same principle encountered in CS430 and SE320, now applied to infrastructure recovery.

## 12. Kubernetes Is Declarative, but Not Every Operation Is Magical

A popular summary says that Kubernetes is declarative rather than imperative.

The distinction is useful, but it deserves precision.

You can issue imperative commands with `kubectl`. You can create, delete, scale and modify resources through commands.

You can also maintain desired resource definitions in version-controlled YAML and apply those definitions.

The important property is that Kubernetes resources store desired configurations that controllers continue to reconcile.

A declarative file does not make the underlying process instantaneous or infallible.

### Applying the same configuration twice

If you apply the same desired configuration again, the goal is not to create another unrelated application every time.

The API operation identifies the existing resource, and the apply mechanism manages the declared fields.

Server-side apply can track ownership of individual fields and detect conflicting attempts by different field managers.

Ordinary `kubectl apply` does not necessarily use server-side apply unless it is requested or configured accordingly.

This matters when several actors modify the same resource.

One team might update replica counts manually. An automation might also modify those fields. A GitOps controller might attempt to restore a configuration from a repository.

Now there are competing sources of intent.

Kubernetes has mechanisms for managing these interactions, but it cannot invent a coherent organizational policy.

The people and automation systems must agree on who owns which decisions.

### Git is not automatically the cluster's truth

A GitOps system can treat version-controlled configuration as the desired source and repeatedly reconcile cluster resources toward it.

But Kubernetes itself does not automatically read your Git repository.

It operates on API resources.

An external agent such as a GitOps controller provides the bridge from version-controlled files to cluster state.

This is a useful distinction because developers sometimes confuse three separate layers:

1. Desired configuration stored in Git.
2. Desired resource state accepted into the Kubernetes API.
3. Actual workload state in the running cluster.

Each can temporarily differ from the others.

## 13. Debugging Is Finding the First Broken Reconciliation Boundary

Let's imagine a deployment that never becomes healthy.

You should not immediately delete random Pods and hope for divine intervention.

Instead, follow the path from intent to execution.

### Boundary A — Was the resource accepted?

If the API rejected the configuration, the failure occurred before reconciliation could begin.

Investigate validation, permissions, admission rules and API availability.

### Boundary B — Did the workload controllers create their resources?

If the Deployment exists but its expected ReplicaSet or Pods do not, inspect the Deployment and subordinate objects.

Check events, conditions, selectors and controller behavior.

### Boundary C — Was the Pod scheduled?

If the Pod is Pending without a node assignment, investigate the scheduler's reasons.

Possible causes include insufficient requested resources or incompatible placement constraints.

The kubelet cannot start a Pod on a node that the scheduler has not assigned.

### Boundary D — Did the kubelet start the container?

If the Pod is assigned but its container cannot start, investigate image availability, runtime errors, mount failures, configuration and node health.

An `ImagePullBackOff` is not an HTTP routing problem.

### Boundary E — Is the application healthy?

If the process starts but fails readiness or crashes, inspect application logs, probes, dependencies and lifecycle behavior.

If everything appears healthy but clients still cannot reach the service, the failure may be in networking or service routing. That is SE450-L03 territory.

This produces a disciplined troubleshooting method:

**Find the first point where the expected state fails to become observed reality.**

Do not debug the entire cluster simultaneously.

### A practical command sequence

Start with the workload status:

`kubectl get deployments`

Then inspect the specific Deployment:

`kubectl describe deployment scanner-api`

Inspect its subordinate resources and Pods:

`kubectl get replicasets`

`kubectl get pods -o wide`

Describe a problematic Pod:

`kubectl describe pod POD_NAME`

Then inspect its logs if the container started:

`kubectl logs POD_NAME`

These commands don't solve every problem. But they lead you from declarative intent through increasingly concrete execution state.

That's the correct direction of investigation.

## 14. Why Kubernetes Is Both Powerful and Expensive

At this stage, Kubernetes may sound like an obviously superior alternative to running containers manually.

It often is, when the organizational and operational requirements justify it.

But the system introduces substantial complexity.

You need a cluster lifecycle, networking implementation, persistent control-plane state, resource governance, access control, workload security, observability and procedures for upgrades and recovery.

A tiny application may not need any of that machinery.

Imagine a company operating one internal service with a few dozen users. It rarely changes and can tolerate occasional maintenance.

Deploying it onto a managed container platform or a simple virtual machine might be a perfectly reasonable decision.

Now imagine a company operating dozens of services across several teams, with independent deployment schedules, different resource needs, strict availability requirements and significant infrastructure automation.

Kubernetes becomes more attractive because its common resource model and controllers can standardize many operational patterns.

### The value is not primarily YAML

A common mistake is evaluating Kubernetes by asking whether its configuration syntax is convenient.

That's like evaluating PostgreSQL by asking whether SQL has too many keywords.

The real question is whether the platform's abstractions solve organizational and technical problems worth solving.

The value may include:

- A shared deployment and operational model across teams.
- Automated workload reconciliation and replacement.
- Declarative rollout mechanisms.
- Scheduling against shared infrastructure capacity.
- Extensibility through custom resources and controllers.
- Integration with infrastructure tooling, observability and policy enforcement.

The costs include control-plane complexity, networking layers, operational expertise, resource overhead and additional failure modes.

A platform is useful when its benefits exceed those costs.

For a small product, Kubernetes can be an expensive way to discover that a container can crash.

For a mature engineering organization, it can provide the foundation for an internal platform that makes deployment and operation substantially more systematic.

## 15. Operators and Custom Controllers — Kubernetes as a Platform for Building Platforms

So far we have discussed built-in resources.

But Kubernetes' architecture is intentionally extensible.

A team can define a Custom Resource Definition, often abbreviated CRD, introducing a new API resource type.

For example, a security platform might define a resource representing a managed scanning environment.

A custom controller could observe that resource and create the appropriate Deployments, Jobs, Services and configuration.

The operator would continue reconciling the associated infrastructure as conditions change.

This is the basis of the Operator pattern: encode domain-specific operational knowledge into controllers.

### Why this is more than a fancy deployment script

Imagine a custom resource that represents a database cluster.

A script might create three database instances and stop.

An operator might continually observe replica health, membership, upgrades and configuration, then perform carefully designed actions to maintain the declared operational state.

But an operator must understand the application-specific rules.

Blindly replacing an unavailable database node without respecting quorum or replication safety can cause severe problems.

A custom controller is not automatically reliable simply because it runs inside Kubernetes.

It is distributed automation and must be engineered with the same seriousness as any other stateful distributed system.

This is where Kubernetes becomes intellectually interesting: it isn't merely a tool for deploying applications. It is a framework for creating specialized infrastructure control systems.

## 16. The Oral Examination

Answer these without rereading the lecture. Explain mechanisms, not just definitions.

### Question 1 — The Successful Deployment That Never Runs

You apply a Deployment requesting five replicas.

`kubectl apply` reports success. Ten minutes later, the Deployment has zero available replicas.

What exactly succeeded, and what would you investigate next?

### Question 2 — The Disappearing Node

A cluster has three scanner API replicas across multiple nodes.

One node becomes unreachable.

Describe the sequence of components involved in restoring the desired replica count. Does Kubernetes guarantee immediate recovery?

### Question 3 — Controller Failure

The Deployment controller becomes unavailable, but all currently running application Pods remain healthy.

Does the application necessarily stop serving requests? What capability is impaired?

### Question 4 — The Impossible Request

A team requests ten additional Pods that each require more memory than any available node can provide.

Why can the API accept the objects while the Pods remain Pending?

### Question 5 — The Repeating Crash

An application Pod repeatedly restarts because its configuration references a nonexistent MongoDB hostname.

Is Kubernetes malfunctioning? What must actually change for reconciliation to converge to a healthy application?

### Question 6 — Building an Operator

A platform team creates a custom resource for a scanner environment.

Why is a continuously reconciling controller generally more resilient than a one-time script that creates all its resources and exits?

## 17. Solutions and Discussion

### Answer 1 — API acceptance is not workload readiness

The API successfully accepted and stored the requested resource state. That does not prove that controllers created subordinate objects, that the scheduler found suitable nodes, or that kubelets started healthy containers.

Inspect the Deployment's status and conditions, then check ReplicaSets, Pods and events. Follow the process until you find the first boundary where expected progress stops.

### Answer 2 — Several components cooperate

The cluster must first detect the node failure. Depending on workload and node conditions, affected Pods may be marked unavailable or removed after relevant delays.

The appropriate workload controller attempts to restore the missing replica count, potentially by creating replacement Pod objects.

The scheduler chooses eligible nodes for unscheduled replacement Pods. Kubelets on the selected nodes start the containers through their runtimes.

There is no guarantee of immediate recovery, and application state is not automatically transferred from the failed process.

### Answer 3 — Existing execution can continue

The running application Pods do not automatically terminate when the Deployment controller stops.

However, the system may be unable to perform the Deployment controller's reconciliation responsibilities, such as coordinating desired rollout changes through ReplicaSets.

The application may continue functioning while cluster automation is impaired.

### Answer 4 — Desired state can be infeasible

The API can record a valid request for resources that the cluster currently lacks capacity to schedule.

The scheduler cannot place a Pod unless suitable nodes satisfy its constraints and resource requirements.

The desired Pods may remain Pending until capacity, resource requests or scheduling constraints change.

Successful resource creation does not imply successful placement.

### Answer 5 — The controller is faithfully enforcing a bad specification

Kubernetes may be behaving correctly according to the declared workload configuration and restart policies.

The application cannot become healthy because it has a bad dependency configuration.

The correction must address the application configuration, its dependency, or the relevant environment.

Repeated restarts cannot repair an incorrect hostname by themselves.

### Answer 6 — Continuous reconciliation survives interruptions

A one-time script may leave partially created infrastructure if a step fails or the script crashes.

A controller can revisit the declared resource, observe what already exists and attempt the missing actions.

This approach handles changing conditions and interrupted attempts more naturally.

But the controller must itself be engineered to tolerate retries, concurrent updates and uncertain outcomes.

## 18. The Mental Model Worth Keeping

Kubernetes is a distributed system for maintaining declared resource state through cooperating controllers and node agents.

Whenever something goes wrong, ask four questions:

1. **What was declared?** — the desired specification.
2. **What is observed?** — current resource status and runtime condition.
3. **Who owns the difference?** — controller, scheduler, kubelet, runtime or external system.
4. **What prevents convergence?** — capacity, permissions, configuration, dependency failure or a broken assumption.

These four questions are more valuable than memorizing a hundred `kubectl` commands.

## 19. Next Lecture — SE450-L02: Pods, Deployments, Jobs, and Controllers

We now understand the platform's central idea.

But we have treated workloads as though they were all interchangeable replicas.

They aren't.

A web API should ordinarily keep serving requests. A scanner Job should eventually complete. A database may require stable identity and persistent storage. A node monitoring agent may need to run on every relevant node.

In the next lecture, we'll explore the actual workload abstractions, their lifecycles, and how Kubernetes decides what to replace, restart, preserve or terminate.

*The spoken lecture ends here. The remainder is for hands-on practice and screen-based revision.*

---

## Optional Practical Lab — Watch Kubernetes Reconcile a Real Deployment

**Goal:** Watch a desired replica count become real Pods, deliberately remove one, and observe Kubernetes restore the requested state.

**Prerequisites:** A working local Kubernetes cluster such as Minikube or kind, plus a configured `kubectl` client. Use a disposable local cluster or an isolated practice namespace, never an unfamiliar production context.

### Lab A — Confirm your environment

Before doing anything destructive, inspect the current context and cluster nodes.

```bash
kubectl config current-context
kubectl get nodes
kubectl cluster-info
```

Confirm that the selected context is the intended practice cluster.

### Lab B — Create the desired state

Create a local file called `reconcile-demo.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: reconcile-demo
  labels:
    app: reconcile-demo
spec:
  replicas: 3
  selector:
    matchLabels:
      app: reconcile-demo
  template:
    metadata:
      labels:
        app: reconcile-demo
    spec:
      containers:
        - name: web
          image: nginx:stable-alpine
          ports:
            - containerPort: 80
```

This example uses a convenient Nginx image for local exploration. In production, prefer a deliberately selected, tested image version or digest rather than a moving convenience tag.

Apply it:

```bash
kubectl apply -f reconcile-demo.yaml
```

Then inspect the result:

```bash
kubectl get deployments
kubectl get replicasets
kubectl get pods -l app=reconcile-demo -o wide
kubectl rollout status deployment/reconcile-demo
```

**Investigate:** Which resources were created automatically? Which controller owns each level of the resource hierarchy?

### Lab C — Observe reconciliation

In one terminal, run:

```bash
kubectl get pods -l app=reconcile-demo -w
```

In another terminal, list the Pods and choose one:

```bash
kubectl get pods -l app=reconcile-demo
```

Delete one of those Pods:

```bash
kubectl delete pod POD_NAME
```

Watch the first terminal.

A new Pod should be created to restore the required replica count. The replacement will have a different identity from the deleted Pod.

Notice that the Deployment continues to request three replicas even though an individual Pod was deleted.

**Investigate:** Why doesn't Kubernetes interpret your Pod deletion as a permanent request to reduce replica count?

### Lab D — Change the desired state

Scale the Deployment:

```bash
kubectl scale deployment/reconcile-demo --replicas=5
kubectl get pods -l app=reconcile-demo -w
```

Then inspect the declared and observed replica counts:

```bash
kubectl get deployment reconcile-demo \
  -o jsonpath='{.spec.replicas}{" desired, "}{.status.availableReplicas}{" available\n"}'
```

If the counts differ, investigate whether the cluster is still making progress.

You can also compare resource generations:

```bash
kubectl get deployment reconcile-demo \
  -o jsonpath='{.metadata.generation}{" desired generation, "}{.status.observedGeneration}{" observed generation\n"}'
```

Do not interpret generation equality alone as proof of workload readiness.

### Lab E — Break the desired configuration

Change the container image to an intentionally nonexistent image:

```bash
kubectl set image deployment/reconcile-demo \
  web=invalid.example.invalid/no-such-image:v1
```

Observe:

```bash
kubectl get pods -l app=reconcile-demo
kubectl describe deployment reconcile-demo
kubectl get events --sort-by=.metadata.creationTimestamp
```

Inspect one failing Pod with `kubectl describe pod POD_NAME`.

You should see evidence that the requested image cannot be obtained.

The API accepted the image change, but the cluster cannot realize it.

Restore the previous image:

```bash
kubectl set image deployment/reconcile-demo \
  web=nginx:stable-alpine
kubectl rollout status deployment/reconcile-demo
```

### Lab F — Cleanup

Remove the test Deployment and its dependent objects:

```bash
kubectl delete deployment reconcile-demo
```

If you reused a production namespace by mistake, stop before executing additional changes and verify the context and resource ownership.

### Lab reflection

Explain these three observations in your own words:

1. Why does deleting an individual managed Pod normally result in a replacement?
2. Why does an invalid image not cause Kubernetes to abandon the desired configuration automatically?
3. What would change if the Deployment controller were unavailable during the experiment?

---

## Further Reading

Official Kubernetes documentation is the primary reference for this course. Feature details, API behavior and lifecycle semantics may evolve between Kubernetes versions.

1. [Kubernetes Components](https://kubernetes.io/docs/concepts/overview/components/) — Control-plane and node components.
2. [Controllers](https://kubernetes.io/docs/concepts/architecture/controller/) — The reconciliation pattern.
3. [Objects in Kubernetes](https://kubernetes.io/docs/concepts/overview/working-with-objects/) — Resources, specification and status.
4. [Kubernetes API Concepts](https://kubernetes.io/docs/reference/using-api/api-concepts/) — API operations, resource versions and watches.
5. [Server-Side Apply](https://kubernetes.io/docs/reference/using-api/server-side-apply/) — Field ownership and declarative updates.
6. [Pods](https://kubernetes.io/docs/concepts/workloads/pods/) — The fundamental workload execution unit.

---

## Dense Cheatsheet — Interview Glance Card

*The following compact reference is fenced for screen revision; voice readers may skip it.*

```text
SE450-L01 — KUBERNETES: A SYSTEM THAT RECONCILES REALITY

CENTRAL IDEA
  Declare desired state.
  Observe actual state.
  Reconcile differences.
  Repeat as conditions change.

  Kubernetes maintains infrastructure intent.
  It does not guarantee business correctness.

CLUSTER ARCHITECTURE
  Control plane   Coordinates API state, placement, controllers
  Worker nodes    Execute workloads and report their condition

CONTROL PLANE
  kube-apiserver  API entrypoint; authn/authz, admission, validation,
                  persistence, read/watch operations
  etcd            Consistent persistent Kubernetes API state
  scheduler       Chooses suitable nodes for unscheduled Pods
  controller mgr  Runs built-in control loops
  cloud ctrl mgr  Optional cloud-provider integration

NODE
  kubelet         Ensures assigned Pods are realized via runtime
  runtime         Executes containers through CRI
  CNI plugin      Implements relevant Pod networking capabilities
  kube-proxy      Optional Service-routing implementation

OBJECTS
  apiVersion      API contract
  kind            Resource type
  metadata        Name, UID, labels, annotations, versions
  spec            Desired characteristics
  status          Reported observations and conditions

  resourceVersion        API concurrency/watch token, opaque
  metadata.generation    Desired-object specification generation
  status.observedGeneration  Controller's reported observed generation
                             (semantics depend on resource)

DEPLOYMENT EXECUTION CHAIN
  User/CI
    -> API server
    -> Deployment stored
    -> Deployment controller
    -> ReplicaSet
    -> ReplicaSet controller
    -> Pod objects
    -> Scheduler binds Pods to nodes
    -> Kubelet
    -> Container runtime
    -> Running containers

  Asynchronous, not one atomic operation.

CONTROLLER
  Observes resources
  Compares actual with desired
  Makes/requests changes
  Retries and reconciles
  Should tolerate repeated attempts and stale observations

IMPORTANT DISTINCTIONS
  API accepted         != workload healthy
  Spec recorded        != controller observed it
  Controller observed  != desired state achieved
  Scheduled            != container started
  Running              != ready
  Ready                != business operation correct
  Replaced Pod         != restored process memory
  Restored process     != recovered unfinished business operation

FAILURE DIAGNOSIS
  Rejected request     -> API, auth, validation, admission
  Missing ReplicaSet   -> Deployment controller, conditions
  Missing Pods         -> ReplicaSet/controller, selectors
  Pod Pending          -> scheduler, capacity, constraints
  ImagePullBackOff     -> image reference, registry, credentials
  CrashLoopBackOff     -> process startup, config, dependencies
  Running but unready  -> readiness probe, application
  Healthy but unreachable -> service networking/routing/policy

KUBECTL
  config current-context   Verify target cluster
  get deploy,rs,pods       Inspect resources
  describe                Events, conditions, diagnostic details
  get pods -o wide        Node placement
  logs                    Application output
  rollout status          Wait for rollout progress
  get -w                  Watch resource changes

SELF-HEALING LIMITS
  Cannot create nonexistent capacity
  Cannot fix application bugs
  Cannot recover arbitrary in-memory business state
  Does not guarantee zero downtime
  Does not imply exactly-once task execution
  Does not automatically make dependencies healthy

KUBERNETES VS GITOPS
  Git                Repository configuration
  GitOps agent       Reconciles Git intent to API resources
  Kubernetes API     Stores resource intent
  Controllers        Reconcile API objects toward actual state

SENIOR DIAGNOSTIC QUESTIONS
  1. What state was declared?
  2. What state is observed?
  3. Which component owns the transition?
  4. Where did convergence stop?
  5. Is this infrastructure health or business correctness?

SENIOR LINE
  "Kubernetes is a distributed reconciliation system:
   the API records desired state; controllers, scheduler and
   node agents cooperate to achieve it. Successful API writes
   do not imply successful execution, and infrastructure
   recovery does not replace application-level reliability."
```
