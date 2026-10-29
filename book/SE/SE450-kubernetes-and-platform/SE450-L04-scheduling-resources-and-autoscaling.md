---
id: SE450-L04
course: SE450
title: "Scheduling, Resources, and Autoscaling"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE450-L03
next: SE450-L05
---

<!--
EDITORIAL-TODO: P3 / AUDIT_DENSITY
Previously measured at approximately 52 spoken minutes.
Future TODO: Review overlap with CS320-L02 on CPU quotas and contention, and with
CS320-L04 on memory pressure and cgroups.
Keep the Kubernetes scheduler, placement, resource-request, and autoscaling details here.
Consider replacing repeated OS explanations with concise reminders and cross-references.
Do not apply automatic word-count reductions.
-->





# SE450 — Kubernetes and Platform Engineering

## Lecture 04: Scheduling, Resources, and Autoscaling

*Your cluster has twelve CPUs sitting almost idle. Kubernetes refuses to schedule another Pod. Meanwhile, a running worker is throttled so severely that its tasks are timing out. You add an autoscaler. It creates more Pods, which cannot start. What exactly is this system optimizing?*

---

# Part I — Intuition

## The picture to carry in your head

Imagine a cybersecurity company operating a fleet of scanning workers.

The workers investigate domains, identify technologies, inspect certificates, and sometimes run computationally expensive analysis tools.

Everything runs in Kubernetes.

The platform has three worker nodes. Each node has eight CPUs and enough memory to run several scanner processes.

One afternoon, customer activity increases. A large number of new domains arrive for investigation, and the engineering team decides to scale the worker Deployment.

But the new Pods remain Pending.

A developer checks the cluster's CPU utilization.

The nodes appear to be using only about 30 percent of their available CPU.

"How can Kubernetes say there's no capacity when 70 percent of our CPUs are idle?"

Another engineer notices a different problem.

One existing scanner is performing a CPU-heavy task. Its node has plenty of unused processing capacity, yet the scanner is advancing painfully slowly.

Someone increases the replica count again.

Now even more Pods are Pending.

The engineers have encountered three distinct systems:

1. A scheduler deciding where Pods are allowed to run.
2. A resource-control mechanism deciding how much CPU or memory running containers may consume.
3. An autoscaler deciding whether the declared workload population should change.

These systems do not use identical information or optimize identical objectives.

Understanding Kubernetes resource management begins by separating their responsibilities.

## 1. Scheduling is a reservation system, not a live CPU meter

Imagine a hotel.

It has ten rooms, and all ten are booked for tonight.

At 2 p.m., the receptionist notices that only three guests are physically inside the building.

Can the hotel safely sell the other seven rooms again?

No.

The guests have reservations. They may return later.

Their temporary absence does not mean the rooms are available for another booking.

Kubernetes resource requests work in a somewhat similar way.

When a Pod declares that it needs one CPU, the scheduler accounts for that request when deciding where it can fit.

The scheduler generally compares requested resources with the node's allocatable capacity and the requests already committed to other Pods.

It doesn't simply look at the current CPU usage and place new Pods wherever the utilization graph appears low.

Consider a node with eight allocatable CPUs.

Eight Pods each request one CPU.

At this particular moment, each Pod uses only 0.2 CPUs.

The monitoring dashboard reports 20 percent CPU utilization.

But the node's eight CPUs are already fully allocated in scheduling-request terms.

A ninth Pod requesting one CPU will not fit on that node under ordinary scheduling rules.

The scheduler is not confused.

It's making placement decisions from declared resource requirements rather than assuming the currently idle workloads will remain idle forever.

**Current consumption and reserved scheduling capacity are two different accounting systems.**

## 2. Requests and limits answer different questions

Now let's change the story.

A worker Pod declares:

- CPU request: 500 millicores.
- CPU limit: 1 CPU.
- Memory request: 512 MiB.
- Memory limit: 1 GiB.

The request describes a resource amount used for placement decisions and resource-control considerations.

The limit describes a maximum enforced during execution.

For CPU, a limit acts as an execution quota.

If the container tries to consume substantially more CPU than its quota permits, the Linux kernel can throttle it.

That can happen even when the node has otherwise idle CPUs.

Why?

Because the CPU quota is a policy constraint on that container. It isn't merely a suggestion to use spare capacity when available.

Memory behaves differently.

A memory limit isn't enforced by slowing down memory access in the same ordinary way that CPU limits are enforced by throttling CPU time.

Instead, excessive memory consumption can result in an out-of-memory kill.

The process may disappear and subsequently restart according to its workload's restart policy.

So there are three different resource questions:

**Request:** What resources should the scheduler account for?

**CPU limit:** How much execution capacity is this container permitted to consume?

**Memory limit:** What memory usage boundary can trigger an out-of-memory termination?

Confusing these concepts explains a surprising number of Kubernetes incidents.

## 3. The scheduler is solving a packing problem

Imagine packing suitcases into several car trunks.

One trunk has space for two large suitcases. Another has room for four small ones.

The total unused space across the cars might be sufficient for another large suitcase, but no individual trunk has a suitable contiguous space for it.

The suitcase doesn't fit.

Kubernetes has an analogous problem.

Suppose you have three nodes, each with two CPUs of unallocated scheduling capacity.

A new Pod requests four CPUs.

Across the cluster, six CPUs are unallocated.

But no single node can accommodate the Pod's four-CPU request.

Kubernetes generally schedules one Pod onto one node. It cannot split the Pod's ordinary CPU requirement across three machines.

The Pod remains Pending.

This is **resource fragmentation**: total capacity exists, but it is distributed in a way that cannot satisfy the requested placement.

And CPU isn't the only constraint.

The scheduler may also consider memory, maximum Pod count, storage requirements, node labels, taints, hardware devices and topology restrictions.

A Pod has to fit the relevant constraints together.

## 4. Placement rules can make available capacity irrelevant

Our scanning platform has a special type of worker that performs particularly sensitive investigations.

The infrastructure team wants those workers to run only on a dedicated node pool.

The Pods specify a requirement for nodes labeled `workload=isolated-scanner`.

Now imagine that the cluster has twenty ordinary nodes with abundant spare CPU.

But every node in the isolated-scanner pool is full.

Where can the new scanner run?

Nowhere that satisfies its declared requirement.

The ordinary nodes are irrelevant because the Pod isn't allowed to run on them.

A hard placement rule is a constraint, not a preference.

This is an important architectural choice.

Sometimes the restriction is genuinely necessary for compliance, isolation, hardware availability or workload safety.

Other times, someone has created an unnecessarily strict rule and accidentally prevented the cluster from using available capacity.

**Scheduling flexibility is itself a resource.**

Every hard constraint reduces the set of acceptable placement options.

## 5. Autoscaling doesn't create work capacity by magic

Now suppose traffic increases and the Horizontal Pod Autoscaler decides the API needs eight replicas instead of four.

It changes the desired replica count.

The Deployment controller creates additional Pod objects.

But where will they run?

The scheduler still needs eligible nodes with sufficient allocatable capacity.

If the cluster is full, the additional Pods remain Pending.

This is where node autoscaling enters the picture.

An appropriate node autoscaler may notice unschedulable Pods and provision more nodes, subject to its configuration and infrastructure constraints.

Eventually, the new Pods may become schedulable.

But there are delays.

Provisioning a virtual machine takes time. Joining the cluster takes time. Pulling images takes time. Application startup and readiness take time.

An HPA increase is not an instant increase in serving capacity.

And if the application's real bottleneck is a saturated database, adding more application replicas may make the problem worse.

The autoscaler can increase the population of clients competing for the same constrained resource.

### Visual anchor — three decisions

```text id="m1l04a"
       APPLICATION DEMAND
                |
                v
         HPA / WORKLOAD
          AUTOSCALER
       How many Pods?
                |
                v
            SCHEDULER
      Where can Pods fit?
                |
                v
        NODE AUTOSCALER
    Do we need more nodes?
                |
                v
        RUNNING CONTAINERS
      CPU / MEMORY LIMITS
                |
                v
      ACTUAL WORK COMPLETED
```

This diagram is conceptual. The control loops run independently, and the node autoscaler reacts to scheduling and capacity information rather than receiving a direct command from the HPA.

The key point is that increasing desired replicas, adding cluster capacity and increasing useful throughput are three different outcomes.

## Your mental checkpoint

Try answering these before continuing.

1. Why might a node show 20 percent CPU usage while being unable to accept another CPU-requesting Pod?
2. How can a container be throttled while its node has idle CPU capacity?
3. Why can a cluster with six CPUs of spare scheduling capacity fail to accommodate a four-CPU Pod?
4. Why might an HPA increase the number of Pods without improving throughput?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. Twenty-Four CPUs, Nine Pending Pods, and a Queue That Wouldn't Shrink

Our security-scanning platform operates three worker nodes.

Each node has eight CPUs, for twenty-four CPUs in total, before accounting for resources reserved for the operating system and Kubernetes components.

The scanner workers pull messages from RabbitMQ.

Under ordinary conditions, each worker runs several scanning modules and publishes findings to MongoDB.

One afternoon, a large customer submits a broad domain scan.

The queue grows rapidly.

The engineering team scales the scanner Deployment from six Pods to fifteen.

Nine new Pods appear in Kubernetes, but they remain Pending.

The team inspects node utilization.

Average CPU usage is only 30 percent.

Meanwhile, some of the six running workers experience extreme processing latency.

Their CPU limits are low enough to constrain bursts, and the applications have begun timing out during computationally intensive scanning phases.

The queue keeps growing.

The team's first instinct is to increase replicas again.

But that would confuse demand, scheduling capacity and execution capacity.

Before making changes, we need to understand exactly what Kubernetes reserves, enforces and measures.

## 2. Capacity, Allocatable, Requests, and Usage

A Kubernetes node exposes resource information through its status.

Two important concepts are **capacity** and **allocatable**.

Capacity describes the node's total advertised resources.

Allocatable describes the portion available for Pods after relevant node-level reservations and configuration.

A machine with eight logical CPUs may expose less than eight CPUs as allocatable, depending on its configuration.

The kubelet and other system processes also need resources.

Kubernetes cannot responsibly assume that the entire machine belongs to application containers.

### An illustrative node

Imagine a node reports:

- CPU capacity: 8 cores.
- CPU allocatable: 7.5 cores.
- Existing Pods' CPU requests: 7 cores.
- Current observed CPU usage: 2 cores.

A new Pod requests 1 CPU.

Does it fit?

Not under the ordinary CPU request accounting.

Only 0.5 CPUs remain unallocated.

The node might be mostly idle in terms of actual execution. But its scheduled resource commitments leave insufficient room for the new request.

The scheduler primarily uses resource requests, not instantaneous CPU consumption, for this part of placement.

It also doesn't reserve a physical CPU core exclusively for every ordinary Pod with a CPU request.

Several Pods can share processors over time.

Requests are scheduling and resource-allocation inputs; they aren't generally private, permanently assigned physical cores.

### Why requests matter

Without requests, a scheduler could pack far too many workloads onto a node, assuming that every workload would remain quiet.

With realistic requests, it can make a more informed placement decision.

But requests are estimates.

Overly large requests waste scheduling capacity.

Overly small requests permit excessive oversubscription, which can cause severe contention when workloads become active.

The goal isn't to request the largest conceivable amount.

It's to describe reasonable resource needs while accounting for workload variability and acceptable risk.

### Resource fragmentation

Suppose two nodes each have 1.5 CPUs of unallocated capacity.

A Pod requests 2 CPUs.

There are 3 CPUs unallocated in aggregate, but no node has a full 2 CPUs available for scheduling.

The Pod remains unscheduled.

This is a bin-packing problem with multiple constraints.

The same reasoning applies to memory, GPUs and other schedulable resources.

And the constraints are multidimensional.

A node may have sufficient CPU but insufficient memory.

Another may have memory but lack the required storage topology.

A third may satisfy both but carry a taint that the Pod cannot tolerate.

The scheduler must find a node satisfying the applicable constraints simultaneously.

## 3. Resource Requests and Limits in Practice

Let's inspect a scanner worker definition.

```yaml id="m1l04b"
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "1500m"
    memory: "2Gi"
```

The CPU request is 500 millicores, equivalent to half a CPU.

The CPU limit is 1500 millicores, equivalent to 1.5 CPUs.

The memory request is 512 mebibytes.

The memory limit is 2 gibibytes.

These quantities use Kubernetes resource notation.

A millicore is one-thousandth of a CPU unit.

The suffixes `Mi` and `Gi` are binary memory units, based on powers of 1024.

Be careful with CPU and memory quantities. A value like `400m` means something useful for CPU, while memory quantities must be interpreted according to their own units.

### The scheduler sees a Pod, not just one container

A Pod may have multiple application containers.

Its scheduling resource requirements account for their requests.

For ordinary application containers, requests are generally added together.

Regular init containers have different lifecycle behavior, so scheduling accounts for their peak requirements rather than simply assuming they execute concurrently with all ordinary application containers.

Pod overhead and supported Pod-level resource settings may also affect the effective resource calculation, depending on the cluster's configuration and Kubernetes version.

The exact calculation matters in sophisticated multi-container Pods.

For example, a scanner Pod with a main worker and a substantial supporting sidecar consumes resources for both.

A sidecar is not free merely because it is called a helper.

### Requests are not limits

A container with a CPU request of 500m but no CPU limit can generally use more than half a CPU when execution capacity is available, subject to other resource controls and contention.

A CPU request influences scheduling and relative CPU allocation under contention.

It does not necessarily create a ceiling.

Conversely, setting a CPU limit of 500m constrains CPU consumption even if the application could use more and the node has idle capacity.

### The surprising default

If you specify a limit for a resource but omit the corresponding request, Kubernetes can use the limit as the request when no admission-time default has already supplied a request.

So a configuration containing a CPU limit of 2 CPUs without an explicit CPU request can end up reserving 2 CPUs for scheduling purposes.

This can make Pods unexpectedly difficult to place.

Namespace-level LimitRanges may also provide default requests and limits, so always inspect the effective accepted Pod configuration rather than assuming the original YAML tells the entire story.

## 4. CPU Limits: Why Idle Machines Can Run Slow Applications

Return to the scanner worker that appears mysteriously slow.

It has a CPU limit of 500m.

Its process launches a computationally expensive analysis that could use several CPU cores effectively.

The node has four idle CPUs.

Why doesn't the scanner take advantage of them?

Because the configured CPU limit constrains it.

On typical Linux Kubernetes nodes, CPU limits are enforced through cgroup CPU bandwidth controls.

The kernel accounts for execution time over enforcement periods.

When the container consumes its permitted CPU quota, its runnable processes may be throttled until further execution budget becomes available.

### An illustrative quota

Imagine a container limited to one CPU.

Over a simplified 100-millisecond quota period, it may receive approximately 100 milliseconds of aggregate CPU execution time.

If it uses four CPUs simultaneously, it could consume that aggregate budget in roughly 25 milliseconds of wall-clock time, then be throttled for the remainder of the period.

Exact behavior depends on kernel configuration, scheduling and the workload's execution pattern.

The practical consequence is what matters:

A parallel process can be throttled even when the host has spare processors.

### Why this damages latency

CPU throttling is not always experienced as a smooth slowdown.

A process may make rapid progress, exhaust its budget, pause, and resume later.

A latency-sensitive request can suffer because its critical work happens to be delayed during one or more throttling periods.

That may produce long-tail latency spikes.

For CPU-heavy workloads, throttling can also reduce throughput directly.

### Should we remove CPU limits?

There is a strong practical case for avoiding overly restrictive CPU limits on trusted workloads in appropriately isolated and well-governed clusters.

CPU requests can provide useful scheduling information and proportional resource allocation, while allowing applications to use otherwise idle capacity.

But removing limits everywhere is not a universal best practice.

In a hostile or strongly multitenant environment, limits can help prevent a workload from monopolizing resources.

For shared development clusters, noisy-neighbor protection may be more important than maximizing burst performance.

The decision depends on isolation requirements, workload trust, resource governance and performance objectives.

**A CPU limit is a deliberate trade-off between isolation and burst capacity. Treat it as such.**

## 5. Memory Limits: A Different Kind of Failure

Memory is not CPU.

A CPU-bound process can be slowed down by throttling and continue operating.

A process that exceeds its usable memory may be terminated.

Kubernetes uses the container runtime and kernel mechanisms to enforce memory limits.

On Linux, memory cgroup enforcement commonly results in an out-of-memory kill when sufficient memory cannot be reclaimed.

The kubelet may then restart the terminated container according to its restart policy.

### The misleading restart loop

Imagine a Node.js scanner process that gradually accumulates large scan results in memory.

Its container has a 512 MiB memory limit.

It reaches the limit during a particularly large scan.

The kernel kills it.

The kubelet restarts it.

The worker receives the scan again and eventually accumulates the same memory.

It is killed again.

The application appears to be experiencing intermittent random failures, but the problem is deterministic under this workload.

The correct diagnosis is not "Kubernetes keeps killing my application."

It is that the workload's memory behavior is incompatible with its configured resource boundary.

### Memory limits are reactive

A memory limit does not necessarily terminate a container at the exact instant that its measured usage briefly exceeds the configured value.

Kernel accounting and reclaim behavior matter.

The general mechanism is reactive: memory pressure or allocation behavior can trigger the OOM killer.

That's different from the ordinary CPU throttling model.

### Requests do not prevent OOM

A memory request of 512 MiB does not guarantee that a process using 2 GiB will remain healthy.

The request helps with placement and influences resource-pressure behavior.

The limit and actual available memory determine important aspects of runtime survival.

A Pod with a large memory request can still be OOM-killed if its container exceeds a restrictive memory limit.

Conversely, a Pod with a modest request and a high limit may consume much more than requested while memory is available, but become vulnerable when the node experiences pressure.

## 6. Quality of Service: Guaranteed, Burstable, and BestEffort

Kubernetes classifies Pods into resource-related Quality of Service classes.

The three familiar classes are Guaranteed, Burstable and BestEffort.

These classifications influence resource-pressure and OOM behavior.

### Guaranteed

A Pod qualifies as Guaranteed under the conventional resource model when every application and init container has CPU and memory requests and limits specified, with each request equal to its corresponding limit.

For example, a one-container Pod requesting one CPU and 1 GiB of memory, with equal limits, can qualify as Guaranteed.

This provides strong predictability about its declared resource allocation.

But "Guaranteed" does not mean the Pod can never be terminated.

Nodes can fail. Applications can crash. Containers can exceed memory limits. Other operational failures still occur.

The label describes a resource QoS class, not universal application availability.

### Burstable

A Pod is generally Burstable when it has some CPU or memory requests or limits but doesn't satisfy the exact Guaranteed criteria.

This is common for applications that request a reasonable baseline but allow bursting beyond it.

For example, a worker with a 500m CPU request and a 1500m CPU limit is Burstable under the normal classification rules.

Burstable doesn't inherently mean poor quality or unreliable.

It can represent a sensible balance between scheduling commitments and execution flexibility.

### BestEffort

A Pod with no CPU or memory requests or limits, under the conventional rules, is classified as BestEffort.

It provides the scheduler with little explicit information about resource consumption.

Under contention and node pressure, BestEffort workloads can be particularly vulnerable.

They are not necessarily unsuitable for every possible task, but they are generally a poor default for important production applications.

### QoS isn't the full eviction algorithm

It's tempting to memorize:

BestEffort dies first, then Burstable, then Guaranteed.

That is too simplistic.

The kubelet's node-pressure eviction decisions account for whether resource usage exceeds requests, Pod priority, and usage relative to requests.

QoS class correlates with some of these behaviors, but it is not the sole direct ordering rule.

For accurate incident analysis, inspect the actual resource usage, requests, priority and the resource that triggered pressure.

## 7. Three Ways a Running Workload Can Lose Its Place

Here we need to distinguish three events that engineers often lump together.

### Container OOM kill

A container exceeds its memory boundary or is selected by the kernel's out-of-memory handling.

The container process is killed.

Depending on the restart policy, the kubelet may restart it within the same Pod.

Look for termination reasons such as `OOMKilled` and relevant container status.

### Node-pressure eviction

A node approaches critical resource pressure, such as insufficient available memory, disk space or process IDs.

The kubelet may attempt to reclaim resources and, when necessary, evict Pods to protect node stability.

An evicted Pod is not merely a running container that received a restart signal.

The Pod may become Failed with an eviction reason, and a workload controller may create a replacement.

The replacement might run on another node if suitable capacity is available.

### Scheduling preemption

A higher-priority Pod cannot be scheduled.

The scheduler may identify lower-priority Pods whose removal would create a feasible placement.

Those lower-priority Pods can be preempted to make room.

This is a scheduling decision, not a node detecting that it is already out of memory.

### Why the distinction matters

Suppose a scanner disappears.

Did it exceed its container memory limit?

Was its node under memory pressure?

Was it preempted by a higher-priority workload?

Was it deleted during a rollout?

Did the node fail?

Each event requires a different investigation and potentially a different architectural response.

Restarting the application without identifying the cause is not enough.

## 8. Node Selection: Hard Requirements Versus Preferences

Kubernetes allows Pods to constrain which nodes may host them.

One of the simplest mechanisms is `nodeSelector`.

Suppose a class of scanner requires nodes with a particular label.

```yaml id="m1l04c"
spec:
  nodeSelector:
    workload: isolated-scanner
```

This is a hard requirement.

The scheduler needs a node whose labels satisfy the selector.

If no appropriate node exists, the Pod remains unscheduled.

### Node affinity

Node affinity provides more expressive placement rules.

It can declare required conditions or preferred conditions.

Required conditions must be satisfied for scheduling.

Preferred conditions influence scoring but can be relaxed if necessary.

For example, you might require Linux nodes while preferring a particular availability zone.

The difference is important.

A required condition protects an invariant but reduces placement flexibility.

A preferred condition guides placement without necessarily blocking progress.

### Pod affinity and anti-affinity

Placement can also depend on other Pods.

Pod affinity can express a desire or requirement to place a new Pod near related workloads within some topology domain.

Pod anti-affinity can express a desire or requirement to separate workloads.

For example, you might prefer that API replicas do not all run on the same node.

This reduces the chance that one node failure eliminates the entire API population.

But rigid anti-affinity can create scheduling problems.

A hard rule requiring every replica to occupy a different node cannot be satisfied if you request ten replicas and have only six eligible nodes.

The resulting Pending Pods are consistent with the policy.

The policy, however, may be operationally inappropriate.

## 9. Taints and Tolerations: Nodes Can Reject Workloads

Node labels and selectors express which nodes a Pod wants.

Taints work in the opposite direction: they allow nodes to repel Pods.

Suppose a node pool is reserved for sensitive security scanning.

Its nodes might carry a taint such as:

`workload=isolated-scanner:NoSchedule`

A Pod without an appropriate toleration will not normally be scheduled there.

A scanner Pod can carry a matching toleration to permit placement.

But a toleration is not a reservation or a request to use that node.

It merely means that the specified taint does not exclude the Pod.

If you want a Pod to run only on that node pool, you may need both appropriate node selection and toleration.

### Taint effects

The three familiar effects are:

**NoSchedule:** new Pods without matching tolerations are prevented from scheduling onto the node.

**PreferNoSchedule:** the scheduler tries to avoid placing such Pods there, but the restriction is soft.

**NoExecute:** Pods without suitable tolerations can be evicted, and new incompatible Pods are excluded.

A NoExecute toleration can include `tolerationSeconds`, allowing an existing Pod to remain for a bounded period after the relevant taint applies.

This is useful for handling temporary node problems.

### Taints don't solve every security requirement

Taints and tolerations are scheduling mechanisms.

They aren't complete isolation or authorization systems.

If a workload must be protected from other tenants, you may also need node-pool access controls, admission policies, appropriate labels, runtime isolation and network restrictions.

A toleration can be added to a Pod specification by someone with sufficient permissions.

Therefore, the presence of a taint alone is not necessarily a strong security boundary.

## 10. Topology Spread: Don't Put All the Eggs on One Node

Imagine an API with six replicas.

The scheduler could potentially place several on the same node if there are no constraints preventing it.

But a node failure might then eliminate much of the available API capacity.

Kubernetes supports topology spread constraints that can distribute matching Pods across topology domains such as nodes or availability zones.

For example, you may want replicas spread across three zones.

The scheduler evaluates the distribution of matching Pods and attempts to satisfy the configured skew rules.

### Hard versus soft spreading

`DoNotSchedule` means the scheduler should reject placements that violate the configured topology spread constraint.

`ScheduleAnyway` means the scheduler can still place the Pod when strict spreading isn't possible, while considering the preference during scoring.

These choices encode different priorities.

If strict geographic distribution is required for availability or compliance, DoNotSchedule may be appropriate.

If serving traffic is more important than perfect distribution during an exceptional shortage, a soft preference may be better.

### The availability paradox

Suppose an API uses strict zone spreading.

One availability zone experiences a capacity shortage.

The cluster has plenty of resources in the other zones.

But a new Pod remains Pending because placing it elsewhere would violate the configured spread constraint.

That's not random scheduler behavior.

It's the consequence of asking Kubernetes to prioritize a particular distribution guarantee.

The architectural question is whether that guarantee remains appropriate during a partial infrastructure failure.

The answer depends on service objectives, failure-domain requirements and the acceptable cost of reduced replica count.

## 11. Priority and Preemption: When Some Work Matters More

A production platform often contains workloads with different importance.

An authentication API may be more critical than a batch report generator.

A cluster DNS component may be more critical than an experimental scanner.

Kubernetes supports Pod priority through PriorityClasses.

A higher-priority Pod can receive scheduling preference.

Under appropriate conditions, the scheduler may preempt lower-priority Pods to make room.

But preemption isn't magical.

Removing a lower-priority Pod cannot make an unavailable GPU appear.

It cannot override a hard node-affinity constraint.

It cannot manufacture a larger node than the infrastructure provides.

And it can cause real disruption to the workloads being displaced.

### Priority inversion at the platform level

Imagine a low-priority batch workload occupying much of the cluster.

A critical API needs another Pod.

With an appropriate priority arrangement, Kubernetes may be able to remove some lower-priority work and schedule the critical replica.

But if all workloads share equal priority, the scheduler has fewer mechanisms for expressing business importance.

The cluster may treat a disposable data-processing experiment and a critical authentication service as peers.

That can be undesirable.

Priority should reflect real operational needs rather than becoming a competition in which every team labels its Pods critical.

If everything is the highest priority, the priority scheme has stopped communicating useful information.

### PodDisruptionBudgets

PodDisruptionBudgets help constrain certain voluntary disruptions, such as administrative eviction operations during node drains.

They are not a universal guarantee against crashes, resource-pressure eviction or all other failures.

They also do not automatically create spare capacity.

A system with four replicas and a strict availability budget still needs enough capacity to replace or move those replicas safely during maintenance.

Availability policy without capacity planning can become an operational deadlock.

## 12. The Horizontal Pod Autoscaler: Scaling Desired Replicas

We now understand where Pods are placed and what resource controls apply after they start.

Next comes the question of how many Pods should exist.

The Horizontal Pod Autoscaler, or HPA, is a Kubernetes controller that adjusts the desired replica count of supported scalable workloads.

It can use CPU utilization, memory measurements, custom metrics or external metrics, depending on its configuration and available metrics APIs.

For ordinary CPU-based autoscaling, utilization is measured relative to declared CPU requests.

This is a crucial detail.

### CPU utilization is relative to requests

Suppose an API Pod requests 500m CPU.

Its measured CPU usage is 400m.

That represents 80 percent utilization relative to its request.

It does not mean the Pod is using 80 percent of an eight-core node.

It does not mean the Pod is 80 percent of the way toward its CPU limit.

It means:

400 millicores used, divided by 500 millicores requested, equals 80 percent.

The HPA target might be 50 percent.

That means the controller seeks a replica population whose average CPU usage is approximately half the requested CPU per Pod, subject to its algorithm and constraints.

### The scaling calculation

At a simplified level, HPA estimates:

`desired replicas = ceil(current replicas × current metric / target metric)`

Suppose:

- Current replicas: 3.
- Average CPU utilization: 80 percent of request.
- Target CPU utilization: 50 percent.

The ratio is 80 divided by 50, or 1.6.

Three replicas multiplied by 1.6 gives 4.8.

The simplified calculation recommends five replicas after rounding upward.

This is a mathematical estimate, not a guarantee that five replicas will become ready or that application performance will improve.

### The control loop has safeguards

The actual HPA algorithm includes details beyond the simple ratio.

It accounts for missing metrics and Pods that are not yet ready.

It applies tolerance thresholds to avoid reacting to insignificant changes.

It supports stabilization windows and rate policies to reduce oscillation.

For example, a default downscale stabilization window helps prevent the HPA from rapidly deleting replicas every time observed load briefly falls.

Those details matter because a real system's metrics are noisy, delayed and affected by the very actions the autoscaler takes.

The HPA is an adaptive controller, not a clairvoyant capacity planner.

## 13. The CPU Request Can Distort Autoscaling

Imagine two otherwise identical deployments.

Both receive the same traffic.

Their Pods each consume about 400m CPU.

Deployment A requests 500m CPU.

Deployment B requests 1000m CPU.

The measured utilization relative to request is:

- Deployment A: 80 percent.
- Deployment B: 40 percent.

If both have a target of 60 percent CPU utilization, they can produce different scaling decisions despite performing essentially the same work.

That's not a measurement bug.

The denominator has changed.

CPU requests influence both scheduler placement and CPU-utilization-based HPA behavior.

This makes resource requests an architectural tuning parameter, not merely a bookkeeping field.

### The danger of artificially small requests

Suppose you set CPU requests unrealistically low so that the scheduler packs more Pods onto each node.

Now average CPU utilization relative to those requests becomes very high.

The HPA may respond by creating more replicas.

The new replicas require additional scheduling capacity, but the cluster may already be crowded with workloads whose requests understate their actual resource needs.

You have created a system whose signals encourage further overcrowding.

### The danger of artificially large requests

If requests are much larger than real needs, the HPA may see a relatively low utilization percentage.

Meanwhile, the scheduler may struggle to place additional Pods because the large requests consume the node's allocatable budget.

Oversized requests can therefore simultaneously suppress a CPU-based scaling signal and reduce placement flexibility.

The solution isn't to tune requests merely to manipulate the HPA.

It's to establish realistic resource requests and choose scaling metrics that correlate with useful capacity.

## 14. CPU Is Not Always the Right Autoscaling Signal

Our scanner workers consume RabbitMQ messages.

Some scans require only a few DNS queries.

Others launch complex external tools, wait for network responses, or call rate-limited services.

The number of queued jobs may grow while CPU utilization remains low.

For example, workers might spend most of their time waiting for external APIs.

Adding more workers could help if sufficient independent work and downstream capacity exist.

But CPU-based autoscaling may not notice the demand because the Pods aren't consuming much CPU.

A better scaling signal might involve queue depth, work arrival rate, age of the oldest message, or an estimate of outstanding work per worker.

### Queue depth has limitations too

Suppose a queue contains ten thousand jobs.

That sounds alarming.

But what if each job normally takes ten milliseconds?

The backlog could be processed quickly.

Now imagine only one hundred jobs, each requiring thirty minutes of expensive scanning.

That much smaller queue may represent far more work.

So queue depth alone isn't a universal capacity metric.

The more meaningful quantity is **work waiting relative to processing capacity and required completion time**.

A rough approach estimates how much work arrives per unit time, how much useful work one worker can complete, and how quickly the backlog needs to drain.

Those estimates should be measured rather than guessed.

### External-metric autoscaling

Kubernetes HPA can use external metrics through a suitable metrics adapter.

Other ecosystem tools, such as KEDA, can make event-driven scaling easier for supported systems.

For a RabbitMQ-based workload, the desired replica count might be derived from queue metrics.

But scaling should be constrained by maximum safe concurrency, downstream rate limits and actual node capacity.

Otherwise, increasing workers may overwhelm MongoDB, external APIs or the broker itself.

**The best scaling metric predicts useful work capacity, not merely visible activity.**

## 15. Node Autoscaling: When the Cluster Itself Must Grow

Suppose HPA increases the desired scanner replicas from six to twelve.

The Deployment creates additional Pods.

The scheduler cannot place four of them.

Now a node autoscaler may become relevant.

Cluster Autoscaler and Karpenter are examples of node autoscaling implementations.

Their internal strategies differ, but the broad goal is to provide suitable nodes when the existing cluster cannot schedule required workloads.

### Scaling Pods versus scaling nodes

The HPA determines desired workload replica counts.

A node autoscaler determines whether infrastructure capacity should change.

These are separate control loops.

The HPA doesn't ordinarily create a cloud virtual machine.

The node autoscaler doesn't ordinarily decide how many replicas the API should run based directly on its HTTP request latency.

Their cooperation is indirect.

The HPA creates additional workload demand.

The scheduler attempts placement.

The node autoscaler can react to unschedulable Pods and provision suitable infrastructure.

### Why node autoscaling can fail

A Pod might require a GPU that no configured node pool provides.

An autoscaler may be limited to certain machine types.

A cloud region may lack available capacity.

The cluster may have reached a configured maximum node count.

An organizational quota may prevent provisioning.

A Pod might request more memory than any allowed machine type provides.

Under those circumstances, the node autoscaler cannot simply fix the problem.

A permanently Pending Pod can be completely consistent with the autoscaler's configuration.

### The startup delay

Even when new nodes can be created, provisioning is not instant.

The cloud provider must supply the infrastructure.

The operating system starts.

The kubelet joins the cluster.

Networking and node-level agents become ready.

The scheduler assigns suitable Pods.

Images may need to be downloaded.

Applications start and pass readiness checks.

If traffic spikes faster than this entire sequence can complete, users experience degraded service before new capacity arrives.

That is why production systems often maintain some headroom instead of expecting all capacity to arrive on demand.

## 16. Vertical Scaling: What If Each Pod Is the Wrong Size?

Horizontal scaling increases the number of replicas.

Vertical scaling changes the resources associated with each replica.

Suppose a scanner worker consistently needs 2 GiB of memory to process ordinary workloads, but requests only 256 MiB.

The Pod may fit onto crowded nodes where its actual resource usage becomes problematic.

Increasing replica count doesn't correct the mismatch.

The workload may need larger requests, a different memory limit or a change in application behavior.

The Vertical Pod Autoscaler, or VPA, can recommend or manage resource request adjustments based on workload measurements and policies.

Its exact behavior depends on the installed implementation, configuration and available Kubernetes features.

### Horizontal and vertical scaling can interact

Imagine HPA scaling on CPU utilization relative to requests.

Now VPA changes those CPU requests.

The utilization percentages change even if actual CPU consumption does not.

The two autoscalers may therefore influence each other's behavior.

This can create competing feedback loops if not designed carefully.

A common strategy is to avoid letting two independent controllers aggressively manipulate related variables without a coherent policy.

For example, VPA may be used for recommendations while HPA controls replica count, or the system may scale on metrics less sensitive to request changes.

The correct combination depends on workload characteristics and supported autoscaler behavior.

## 17. Autoscaling Feedback Loops Can Become Unstable

We now have the ingredients for a particularly nasty incident.

Our scanner API experiences a surge of requests.

CPU utilization rises.

HPA increases replicas.

The new Pods start.

Every Pod opens a pool of connections to MongoDB.

The database is already close to its connection or query capacity.

Adding application Pods increases the total number of competing database connections.

Database latency increases.

API requests stay active longer.

Some Pods accumulate more work and consume additional resources.

The HPA continues to observe pressure and may recommend additional replicas.

But the additional replicas do not increase useful throughput.

They increase contention.

### The positive-feedback trap

What began as a sensible scaling response has become a reinforcing failure.

More Pods create more database pressure.

More database pressure increases request latency.

More latency creates more outstanding work.

Depending on the metrics, the autoscaler may respond with even more Pods.

This is not unique to Kubernetes.

It's a general control-systems problem: the controller's action alters the environment, and the measured feedback no longer has the relationship to system health that the controller assumed.

### Why scaling out sometimes helps

If the application is CPU-bound and requests are independent, adding replicas can increase useful throughput.

If the backend database and network have substantial spare capacity, distributing requests may reduce application-level contention.

But if the bottleneck is shared and already saturated, more application instances cannot create additional downstream capacity.

The system's maximum useful throughput is bounded by its limiting resources and architecture.

This connects directly to CS430's treatment of bottlenecks, queues and backpressure.

### Guardrails

A reliable autoscaling design may include:

- Minimum and maximum replica bounds.
- Stabilization windows and scaling-rate limits.
- Admission control and request concurrency limits.
- Realistic resource requests.
- Sufficient node headroom.
- Monitoring of downstream resource saturation.
- Scaling signals that correlate with completed useful work.

These measures do not eliminate every failure, but they constrain how aggressively the controller can amplify one.

**Autoscaling is a control loop. Control loops require stable signals, bounded actions and an understanding of the system being controlled.**

## 18. Capacity Planning: Enough for Normal Traffic Is Not Enough

Imagine the scanner API needs four replicas to handle ordinary traffic.

The team provisions exactly enough node capacity for those four replicas.

Everything appears efficient.

Then one node fails.

Two replicas disappear.

The remaining nodes have insufficient allocatable capacity to run their replacements.

The platform has no spare room to recover.

This is a capacity-planning failure.

### Headroom for failure

Production capacity should consider ordinary demand, expected peaks, deployment surges and infrastructure failures.

For example, a service with an N+1 availability requirement needs sufficient capacity to tolerate the loss of one relevant failure domain while continuing to meet its service objectives.

But merely counting nodes is insufficient.

Three nodes in one availability zone don't provide geographic redundancy against the loss of that zone.

Four nodes with identical dependency paths may share a critical failure mode.

And spare CPU doesn't help if memory, networking, disk or a database connection pool is the limiting resource.

### Rollout capacity

SE450-L02 introduced rolling updates.

A Deployment using `maxSurge` may need room to start replacement Pods before terminating old ones.

If every node is packed exactly to its requested capacity, the rollout can stall even when the existing application is healthy.

The organization must either maintain headroom or accept an availability trade-off through different rollout parameters.

### The economics

Idle infrastructure is not always waste.

Some idle capacity is an insurance policy against failures and sudden demand.

But excessive idle capacity is expensive.

The objective is not maximum utilization at every instant.

It is an appropriate balance between cost, reliability, latency and recovery speed.

For important services, running at 100 percent resource saturation is rarely an admirable achievement.

It's often a warning that the system has no room to absorb an unexpected event.

## 19. Diagnosing Our Original Incident

Let's return to the security-scanning platform.

We have nine Pending Pods, low average node CPU utilization, slow running workers and a growing queue.

We should separate the symptoms and investigate each one.

### First: why are Pods Pending?

Start by inspecting the Pod's events.

`kubectl describe pod POD_NAME`

Look for scheduling messages such as insufficient CPU, insufficient memory, untolerated taints or unsatisfied node-affinity rules.

Next inspect node allocatable resources and allocated requests.

`kubectl describe nodes`

Compare the Pod's effective resource requests with the available scheduling capacity on eligible nodes.

Don't substitute a utilization chart for this accounting.

### Second: why are running workers slow?

Inspect their CPU requests and limits.

Check actual CPU usage, throttling metrics and application behavior.

A worker with a low CPU limit may be throttled during compute-intensive phases even when the node has idle CPU.

But throttling is not the only possible explanation.

The worker may be waiting on an external service, contending on locks, or constrained by a serial execution path.

This is where the Linux/runtime measurements from CS320 become valuable.

### Third: why is the queue growing?

Measure message arrival rate and completion rate.

Determine average and tail task duration.

Inspect the age of the oldest queued task.

Identify whether workers are CPU-bound, I/O-bound or blocked by downstream rate limits.

A queue can grow because there are too few workers.

It can also grow because each worker has become slower.

Those problems require different interventions.

### Fourth: would more Pods help?

Only if the new Pods can be scheduled and the actual bottleneck can benefit from additional concurrency.

If CPU limits are unnecessarily restrictive, correcting them may improve existing-worker throughput.

If node allocatable capacity is exhausted, additional nodes may be needed.

If MongoDB is saturated, increasing scanner concurrency could make the backlog worse.

If workers are blocked by a third-party rate limit, new replicas may merely produce more rejected requests.

### Fifth: what should the autoscaler measure?

For a CPU-heavy scanner, CPU metrics may be useful.

For a mixed external-I/O workload, queue age or estimated outstanding processing time may be more representative.

The chosen metric should align with the actual capacity objective.

A queue-based autoscaler must still respect downstream and infrastructure limits.

### The resulting architecture

A defensible system might use realistic CPU and memory requests, carefully chosen CPU-limit policies, separate worker pools for different workload classes, and bounded queue-driven scaling.

A node autoscaler can provision additional capacity for schedulable workload demands.

Priority and topology policies can protect critical services and distribute replicas across failure domains.

Observability should distinguish scheduler failures, CPU throttling, memory pressure, queue growth and downstream saturation.

Most importantly, the system should measure completed useful work rather than celebrating increased replica counts.

## 20. The Oral Examination

Answer each question aloud before reading the solutions.

### Challenge 1 — The Idle Node

A node has eight allocatable CPUs.

Existing Pods request 7.8 CPUs but currently consume only 1.5.

A new Pod requests 500m CPU.

Why might the scheduler refuse to place it?

### Challenge 2 — Throttled at 20 Percent Utilization

A scanner Pod has a CPU limit of 500m.

Its node has eight CPUs and reports only 20 percent CPU utilization.

The scanner repeatedly experiences CPU throttling.

How is this possible, and what evidence would you collect?

### Challenge 3 — Memory Disappearance

A Node.js worker repeatedly terminates with reason `OOMKilled`.

Its memory request is 256Mi and its limit is 512Mi.

The node has free memory according to its dashboard.

Explain a plausible failure and the correct investigation.

### Challenge 4 — Three Free CPUs, No Placement

Two nodes each have 1.5 CPUs of unallocated capacity.

A new Pod requests 2 CPUs.

Why does the Pod remain Pending, and what would resolve the situation?

### Challenge 5 — The Dedicated Node Pool

A scanner Pod tolerates a taint applied to dedicated nodes.

The team expects this to force the Pod onto those dedicated nodes.

Is their assumption correct?

### Challenge 6 — The Misleading HPA

A Deployment has three replicas.

Its Pods each request 500m CPU and consume an average of 400m.

The HPA target is 50 percent utilization.

What is the simplified recommended replica count, and why might the actual HPA decision differ?

### Challenge 7 — The Autoscaler That Attacked MongoDB

An HPA doubles API replicas during a period of high latency.

Database connections and latency increase, and completed requests per second decline.

What went wrong, and how would you redesign the scaling strategy?

### Challenge 8 — The Availability Zone Failure

An API has six replicas spread across three zones.

One zone becomes unavailable.

Hard topology constraints prevent replacement Pods from scheduling in the two surviving zones.

Is Kubernetes malfunctioning? What trade-off has the organization made?

## 21. Solutions and Discussion

### Solution 1 — Request accounting, not live utilization

The node has only 200m CPU left in unallocated scheduling-request capacity.

The new Pod requests 500m.

The scheduler cannot fit it under ordinary request accounting, even though the node's current CPU usage is low.

The correct investigation examines node allocatable resources and existing Pod requests.

### Solution 2 — A per-container quota can bind on an idle node

The CPU limit applies to the container independently of overall node utilization.

The Linux kernel can throttle the container after it consumes its permitted CPU quota.

Inspect CPU throttling metrics, resource configuration, actual CPU usage and relevant latency measurements.

Do not automatically remove the limit without considering workload isolation requirements.

### Solution 3 — The container may exceed its own memory limit

The worker can be OOM-killed when it exceeds its configured memory boundary even if the node has spare physical memory.

Inspect current and previous container status, memory usage, application allocation patterns and whether the scan workload requires more memory.

Changing the limit may be justified, but fixing excessive buffering or leaks may be more important.

### Solution 4 — Capacity is fragmented

The Pod needs a single node with at least two CPUs of available scheduling capacity.

Two separate 1.5-CPU gaps cannot jointly host one ordinary Pod.

Possible remedies include adding a suitable node, changing placement of other workloads, reducing a justified request or redesigning work into independent smaller Pods where appropriate.

### Solution 5 — Toleration is permission, not attraction

A matching toleration allows the Pod to be considered for nodes carrying that taint.

It does not necessarily force placement there.

A nodeSelector or suitable node-affinity requirement can constrain the Pod to the intended pool.

The system must satisfy both the desired placement conditions and applicable taint rules.

### Solution 6 — Five replicas in the simplified model

400m consumption divided by 500m request equals 80 percent utilization.

With a 50 percent target, the ratio is 1.6.

Three replicas multiplied by 1.6 equals 4.8, rounded up to five.

The actual HPA result may differ because of missing metrics, unready Pods, stabilization, tolerance, rate policies and min/max replica bounds.

### Solution 7 — Scaling amplified a shared bottleneck

More API replicas created more concurrent demand on a saturated database.

The system increased contention rather than useful throughput.

Investigate database connection limits, query latency, request concurrency and dependency capacity.

Use scaling metrics and guardrails that reflect the actual limiting resources, and introduce appropriate admission control or backpressure.

### Solution 8 — The scheduler is enforcing a hard policy

Kubernetes is respecting the configured topology constraints.

The organization chose stronger placement distribution requirements at the cost of reduced flexibility during a zone failure.

If maintaining service capacity during partial-zone outages is more important, the topology policy and capacity strategy should reflect that priority.

The right design depends on the intended availability and failure-domain guarantees.

## 22. The Mental Model Worth Keeping

Kubernetes resource management contains several cooperating but distinct mechanisms.

**Requests describe scheduling demand. Limits constrain runtime resource consumption. Placement policies restrict acceptable nodes. Autoscalers modify desired workload or infrastructure capacity.**

These mechanisms cannot be understood through a single utilization percentage.

A Pending Pod is not evidence that the cluster is busy.

An idle node is not evidence that a new Pod can fit.

A Running container is not evidence that it has sufficient CPU or memory.

An increased replica count is not evidence of increased throughput.

And successful autoscaling is not evidence that the application can tolerate the resulting downstream demand.

When investigating a resource problem, ask:

1. What is the Pod requesting?
2. What is the node able and allowed to provide?
3. Which constraint prevents placement?
4. What limits are enforced after execution begins?
5. Which resource is actually saturated?
6. What signal drives scaling, and will scaling improve completed useful work?

Those questions turn resource management from mysterious Kubernetes behavior into ordinary engineering.

## 23. Next Lecture — SE450-L05: Configuration, Secrets, and Persistent State

We've learned how Kubernetes decides where workloads run and how much infrastructure they can consume.

But what happens when a Pod moves?

Our scanner process may be perfectly replaceable, yet its configuration, credentials and stored results are not necessarily disposable.

An application that works on node A can fail on node B because it cannot access a volume. A container may restart and lose data written into its writable filesystem. A Secret may change without a running process immediately adopting the new value.

The next lecture will explore ConfigMaps, Secrets, volumes, PersistentVolumes, PersistentVolumeClaims, StorageClasses and CSI.

The central question is simple:

**If Kubernetes is free to replace the process, which parts of the application's identity and state must survive?**

*The spoken lecture ends here. The remainder is for hands-on investigation and screen-based revision.*

---

## Optional Practical Lab — Why a Pending Pod Can Coexist with Idle CPUs

**Objective:** Observe node allocatable capacity, resource requests, failed scheduling and hard placement constraints without deliberately exhausting the computer.

Use a disposable local Kubernetes cluster such as Minikube or kind. The exercise is designed for observation and intentionally unschedulable resources, not high-load stress testing.

### Lab A — Verify the environment

Check your current Kubernetes context:

```bash
kubectl config current-context
kubectl get nodes
```

Confirm that this is your disposable practice cluster.

Create an isolated namespace:

```bash
kubectl create namespace se450-l04
```

### Lab B — Compare node capacity and allocatable resources

Inspect the node:

```bash
kubectl describe nodes
```

Find the `Capacity`, `Allocatable` and `Allocated resources` sections.

Notice that allocatable resources can be smaller than advertised capacity, and that allocated requests can be high even when actual utilization is low.

If Metrics Server is installed, inspect current usage:

```bash
kubectl top nodes
```

If the command reports that resource metrics are unavailable, that does not invalidate the lab. The metrics pipeline is an optional dependency for this observation.

Compare three concepts:

- Node allocatable CPU.
- Sum of Pod CPU requests.
- Actual measured CPU usage.

Explain why these values are different.

### Lab C — Create a small schedulable Pod

Create `small-pod.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: small-pod
spec:
  restartPolicy: Never
  containers:
    - name: sleeper
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: "50m"
          memory: "32Mi"
        limits:
          cpu: "200m"
          memory: "128Mi"
```

Apply it:

```bash
kubectl apply -n se450-l04 -f small-pod.yaml
kubectl get pods -n se450-l04 -o wide
```

Inspect the Pod:

```bash
kubectl describe pod small-pod -n se450-l04
```

Find the resource requests, limits and assigned node.

**Question:** Which resource values were used for ordinary scheduling capacity checks, and which will constrain execution?

### Lab D — Create a Pod that cannot fit

Create `oversized-pod.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: oversized-pod
spec:
  restartPolicy: Never
  containers:
    - name: sleeper
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: "100"
          memory: "512Gi"
        limits:
          cpu: "100"
          memory: "512Gi"
```

These extreme requests are deliberately unsuitable for a normal local practice node. Do not run this exercise on a cloud cluster with automatic expensive node provisioning.

Apply the Pod to the disposable cluster:

```bash
kubectl apply -n se450-l04 -f oversized-pod.yaml
```

Inspect:

```bash
kubectl get pods -n se450-l04
kubectl describe pod oversized-pod -n se450-l04
```

Look for scheduling failure events, typically involving insufficient resources.

**Questions:**

1. Why did the API accept this Pod definition?
2. Why didn't Kubernetes simply start the container and let it consume whatever CPU was available?
3. Would reducing only the CPU request guarantee that the Pod could schedule?

Delete the impossible Pod afterward:

```bash
kubectl delete pod oversized-pod -n se450-l04
```

### Lab E — Demonstrate a hard placement constraint

Create `selector-pod.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: selector-pod
spec:
  restartPolicy: Never
  nodeSelector:
    se450.example.com/special-node: "true"
  containers:
    - name: sleeper
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: "20m"
          memory: "16Mi"
```

Apply it:

```bash
kubectl apply -n se450-l04 -f selector-pod.yaml
kubectl describe pod selector-pod -n se450-l04
```

Assuming none of your nodes has the deliberately unusual label, this Pod should remain Pending because its hard placement condition cannot be satisfied.

Note that it requests very little CPU and memory.

**Question:** Why doesn't abundant free CPU help this Pod?

Now delete the constrained Pod:

```bash
kubectl delete pod selector-pod -n se450-l04
```

Avoid adding special labels or modifying taints on nodes for this exercise. The goal is to observe scheduling behavior without changing the cluster's overall placement policy.

### Lab F — Inspect resource and QoS classification

Inspect the small Pod's full status:

```bash
kubectl get pod small-pod -n se450-l04 -o yaml
```

Look for:

`status.qosClass`

Based on its resource requests and limits, determine why it received that classification.

Then calculate its CPU request and limit in ordinary CPU units:

- Request: 50m = 0.05 CPU.
- Limit: 200m = 0.2 CPU.

Explain why a container using 0.2 CPU for a sustained period may be throttled even on a node with several available CPUs.

You do not need to generate CPU pressure to demonstrate the concept.

### Lab G — Inspect autoscaling prerequisites

Check whether resource metrics are available:

```bash
kubectl top pods -n se450-l04
```

Then check for existing HPAs:

```bash
kubectl get hpa -A
```

A CPU-utilization-based HPA generally needs a working resource metrics API, commonly supplied by Metrics Server, and suitable CPU requests for the target Pods.

If metrics are unavailable, do not invent HPA results. Instead, revisit the simplified calculation from the lecture.

Suppose three Pods each request 500m CPU, consume 400m, and target 50 percent utilization.

Calculate the recommended replica count.

Then explain why five desired replicas do not guarantee five running, ready replicas.

### Lab H — Cleanup

Verify that the namespace contains only this exercise's resources:

```bash
kubectl get all -n se450-l04
```

Then remove the practice namespace:

```bash
kubectl delete namespace se450-l04
```

### Final lab reflection

Explain, without consulting the lecture:

1. The difference between node capacity, allocatable resources and actual usage.
2. Why a high CPU request can prevent a Pod from scheduling.
3. Why hard node selection can prevent placement even when resources are plentiful.
4. Why CPU limits can restrict execution independently of cluster utilization.
5. How HPA and node autoscaling solve different capacity problems.

---

## Further Reading

Official Kubernetes documentation should remain the primary source for implementation-specific details. Some resource-management features vary across Kubernetes versions and cluster configurations.

1. [Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/) — CPU and memory requests, limits and enforcement.
2. [Assigning Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/) — Selectors, affinity and anti-affinity.
3. [Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/) — Placement restrictions and eviction effects.
4. [Pod Topology Spread Constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/) — Distributing workloads across failure domains.
5. [Pod Quality of Service Classes](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/) — Guaranteed, Burstable and BestEffort.
6. [Node-pressure Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/) — Resource pressure and eviction behavior.
7. [Horizontal Pod Autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/) — Metrics, scaling calculations and stabilization.
8. [Node Autoscaling](https://kubernetes.io/docs/concepts/cluster-administration/node-autoscaling/) — Cluster capacity provisioning and consolidation.
9. [Pod Priority and Preemption](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/) — Scheduling priority and displacement.

---

## Dense Cheatsheet — Interview Glance Card

*This fenced reference is intended for rapid screen-based revision rather than voice playback.*

```text
SE450-L04 — SCHEDULING, RESOURCES, AND AUTOSCALING

CENTRAL DISTINCTION
  Request       Scheduling resource demand / allocation input
  Limit         Runtime resource boundary
  Usage         Actual measured consumption
  Allocatable   Node resources available for Pods

  Usage != requests != limits != allocatable

SCHEDULER
  Filters nodes against hard requirements
  Scores feasible nodes
  Binds Pod to chosen node

  Primary resource fit:
    Pod requests vs node allocatable - existing requests

  Does NOT simply schedule onto least-utilized CPU meter

RESOURCE FRAGMENTATION
  Node A spare: 1.5 CPU
  Node B spare: 1.5 CPU
  Pod request:  2 CPU

  Total spare = 3 CPU
  No individual node fits = Pending

CPU
  1000m = 1 CPU
  500m  = 0.5 CPU

  CPU request:
    Scheduling accounting
    Relative CPU allocation influence under contention

  CPU limit:
    Kernel/cgroup quota
    May throttle even when node has idle CPU

MEMORY
  Request:
    Scheduling input; pressure behavior

  Limit:
    Enforced via kernel memory controls
    May trigger OOM kill

  Memory != CPU:
    Memory usually killed under pressure/excess
    CPU typically throttled

RESOURCE CONFIGURATION
  Explicit requests and limits recommended for control
  Limit without request may become request
  LimitRange can inject defaults
  Multi-container Pod requirements are aggregated
  Init-container peak requirements affect scheduling

QOS CLASSES
  Guaranteed:
    CPU/memory requests = limits for all relevant containers

  Burstable:
    Some resources defined, not Guaranteed

  BestEffort:
    No CPU/memory requests or limits

  QoS influences resource-pressure behavior
  Eviction ordering also considers usage vs request + priority

THREE DIFFERENT TERMINATIONS
  OOMKilled:
    Kernel kills container due to memory pressure/limit

  Evicted:
    Kubelet removes Pod under node resource pressure

  Preempted:
    Scheduler displaces lower-priority Pod for higher-priority Pod

PLACEMENT
  nodeSelector:
    Hard node-label requirement

  nodeAffinity:
    Required or preferred placement rules

  podAffinity:
    Place near matching Pods/topology

  podAntiAffinity:
    Separate from matching Pods/topology

  topologySpreadConstraints:
    Spread replicas across nodes/zones

  Hard constraints reduce schedulability

TAINTS
  NoSchedule        Reject incompatible new Pods
  PreferNoSchedule  Soft avoidance
  NoExecute         Can evict incompatible existing Pods

TOLERATIONS
  Permit placement despite matching taint
  Do NOT force placement onto tainted nodes

PRIORITY
  PriorityClass provides relative scheduling priority
  Higher-priority Pod may preempt lower-priority Pods
  Cannot override hard placement impossibility

PDB
  Constrains certain voluntary disruptions
  Does NOT prevent all failures or OOM kills
  Does NOT create replacement capacity

HPA
  Changes desired workload replica count
  Based on resource/custom/external metrics

  Simplified:
    desired = ceil(current × measured / target)

  Example:
    replicas = 3
    usage    = 80% of CPU request
    target   = 50%
    desired  = ceil(3 × 80/50) = 5

  Actual algorithm includes:
    missing metrics
    readiness handling
    tolerance
    stabilization
    scaling-rate policies
    min/max replicas

CPU UTILIZATION
  measured CPU / requested CPU

  NOT percentage of total node CPU
  NOT percentage of CPU limit

NODE AUTOSCALING
  Adds/consolidates nodes to meet capacity needs
  Responds to unschedulable workload demand
  Depends on configured machine types, quotas, cloud capacity

VPA
  Recommends/adjusts workload resource requests
  Can interact with CPU-utilization HPA
  Coordinate controller objectives

QUEUE-DRIVEN SCALING
  CPU may not reflect I/O-bound work
  Queue depth is imperfect
  Better signals may include:
    arrival rate
    processing rate
    age of oldest task
    estimated outstanding work
    downstream concurrency limits

AUTOSCALING FAILURE MODE
  HPA adds API Pods
    -> More DB connections
    -> DB contention worsens
    -> Latency increases
    -> More outstanding work
    -> HPA may add further Pods

  More replicas != more useful throughput

CAPACITY PLANNING
  Account for:
    ordinary demand
    peak load
    deployment surge
    node/zone failure
    system reservations
    startup latency
    downstream limits

  Some idle capacity is deliberate resilience

DIAGNOSE PENDING
  kubectl describe pod
  kubectl describe nodes
  Inspect:
    effective requests
    node allocatable
    existing allocated requests
    taints/tolerations
    node selection/affinity
    topology constraints
    volumes/devices
    node autoscaler provisioning constraints

DIAGNOSE SLOW RUNNING POD
  CPU throttling?
  Memory pressure/OOM?
  Application locks?
  External I/O waiting?
  DB/queue/network bottleneck?
  Too much concurrency?

SIX QUESTIONS
  1. What is requested?
  2. Which nodes are eligible?
  3. What prevents fit?
  4. What runtime limits apply?
  5. What is the true bottleneck?
  6. Will scaling increase completed useful work?

SENIOR LINE
  "Requests drive scheduling, limits constrain execution,
   placement policies define eligibility, and autoscalers
   modify desired capacity. I investigate those decisions
   separately and optimize for useful throughput, not
   merely CPU utilization or replica count."
```
