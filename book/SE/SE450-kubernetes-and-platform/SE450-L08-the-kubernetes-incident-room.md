---
id: SE450-L08
course: SE450
title: "The Kubernetes Incident Room"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE450-L07
next: null
---





# SE450 — Kubernetes and Platform Engineering

## Lecture 08: The Kubernetes Incident Room

*The cluster is technically alive. The API is accepting requests. The workers are failing, the queue is growing, some Pods cannot start, and the autoscaler keeps requesting more. Welcome to the incident room. You're responsible for getting the system back under control.*

---

# Part I — Intuition

## The picture to carry in your head

It is Tuesday morning.

Your company operates a cybersecurity platform that scans customers' external assets. An API accepts scanning requests, RabbitMQ distributes the work, and a fleet of Kubernetes workers performs the investigations.

The system has been healthy for weeks.

At 09:12, a new release begins.

The release includes several changes intended to improve efficiency and security. Scanner concurrency has increased, memory limits have been adjusted, and network access has been restricted.

The deployment pipeline reports success.

At 09:18, an alert fires.

The oldest queued scan is taking longer than expected.

At 09:21, another alert appears.

Some scanner Pods are repeatedly restarting.

At 09:24, a third alert reports that several new Pods remain Pending.

Meanwhile, the application logs contain intermittent DNS errors.

The Kubernetes dashboard tells you that most nodes are healthy and that the cluster has spare CPU.

The platform's autoscaler responds to the backlog by requesting additional scanner replicas.

Those replicas also struggle to start.

Customer support is now reporting that scans aren't completing.

Welcome to the incident room.

Your job is not to guess which Kubernetes component is broken. Your job is to reconstruct the chain of events, identify the actual failure mechanisms, contain the impact, and restore correct business behavior.

## 1. Five alarms do not necessarily mean five independent incidents

Imagine a car.

The engine overheats. Power drops. Fuel consumption increases. The dashboard shows several warning lights.

A mechanic who treats each warning light as an independent failure may replace several perfectly healthy components.

A better mechanic asks whether the symptoms share a cause.

Perhaps the cooling system failed.

The engine then reduced power to protect itself.

Fuel efficiency deteriorated because the engine was operating abnormally.

Several alarms appeared, but the failure chain originated somewhere else.

Kubernetes incidents often have the same structure.

A configuration change might cause application failures.

Those failures might cause message retries.

Retries increase memory consumption.

OOM kills restart workers.

The resulting reduction in processing capacity makes the queue grow.

An autoscaler reacts to the growing queue by requesting more workers.

But new workers cannot be scheduled because of resource and placement constraints.

Now the cluster shows multiple problems.

Some are root causes. Others are consequences. Still others may be unrelated.

**The first task in incident response is to distinguish causal relationships from coincidental symptoms.**

## 2. The three clocks of an incident

There are three timelines worth reconstructing.

The first is the **change timeline**.

What was deployed? Which configuration changed? Did a new NetworkPolicy appear? Were resource requests modified? Did an autoscaler change the desired replica count?

The second is the **infrastructure timeline**.

When did Pods become Pending? When were containers terminated? When did readiness fail? Were endpoints removed from Services? Did nodes report pressure?

The third is the **business timeline**.

When did accepted scans stop completing? When did customer-visible latency increase? Did results disappear, or were they merely delayed? Were any scans duplicated?

These timelines are related, but they are not identical.

A deployment may begin at 09:12, complete some infrastructure operations at 09:15, and cause business failures only when a particular scanning module runs at 09:18.

A customer may report a problem at 09:30 even though the original failure occurred fifteen minutes earlier.

An engineer who looks only at the time the alert fired can easily miss the relevant change.

### Visual anchor — three timelines

```text
CHANGE
  09:12 Release begins
  09:14 New Pod specifications applied

INFRASTRUCTURE
  09:15 Some Pods fail readiness
  09:18 Containers restart
  09:24 New Pods remain Pending

BUSINESS
  09:16 Scan completion rate declines
  09:20 Queue age rises
  09:30 Customer complaints arrive
```

The numbers are illustrative. The investigative method is what matters.

## 3. Follow the work, not the dashboard

Suppose Kubernetes reports that the API Deployment is healthy.

The customer submits a scan and receives HTTP 202 Accepted.

Does that mean the customer received the service?

No.

The scan still needs to reach RabbitMQ, be consumed, execute successfully, persist its results, and reach a completed state.

So instead of beginning with every cluster component, follow one real business operation.

Take scan `4821`.

Was it accepted?

Was its message published?

Did a worker receive it?

Did execution begin?

Did it fail, retry, or complete?

Were findings persisted?

That journey is the shortest path to understanding what the customer experienced.

It also tells us which infrastructure components are actually relevant.

If the API accepted the request and RabbitMQ stored the message, a failing public Ingress controller is unlikely to explain why that particular message never completed.

If a worker consumed the message but failed during DNS enumeration, investigate the scanner's network behavior.

If the worker completed and persisted results but the customer sees a Pending state, investigate workflow state and read paths.

**Start with the broken business operation, then descend into the infrastructure that supports it.**

## 4. Every symptom is evidence, not a diagnosis

A Pod is Pending.

Does that mean insufficient CPU?

Maybe. It might also be a node selector, taint, memory request, storage topology, or another scheduling constraint. And the Pending phase can cover initialization work after scheduling.

A container reports `OOMKilled`.

Does that prove a memory leak?

No. It indicates an out-of-memory termination, but the cause might be legitimate workload growth, inappropriate limits, excessive concurrency, memory-backed temporary storage, or an application defect.

DNS lookups fail.

Does that prove CoreDNS is broken?

No. A network policy might block the queries. A particular application might use a different resolver. DNS configuration or search-domain behavior might be wrong.

An HPA requests more replicas.

Does that prove Kubernetes needs more nodes?

No. The scaling metric might reflect a downstream bottleneck that additional workers cannot improve.

The correct question is always:

**What does this observation establish, and what remains uncertain?**

That distinction separates serious incident investigation from ritualistic command execution.

## 5. Containment comes before architectural perfection

Imagine that every minute another hundred customer scans enter a queue that the system cannot process.

You could spend an hour investigating the perfect permanent fix.

But the backlog keeps growing.

Customers continue receiving optimistic responses.

Some scans may eventually expire or generate duplicate work.

A sensible incident commander asks what can safely reduce the damage now.

Perhaps new scan intake should be temporarily limited.

Perhaps the release should be stopped or reverted.

Perhaps one problematic scanning module can be disabled without interrupting the rest of the platform.

These are business decisions supported by technical evidence.

They have different costs.

Stopping all traffic may be unnecessarily destructive.

Continuing to accept work indefinitely may be dishonest and dangerous.

The appropriate action depends on what remains functional and what the system can recover.

The goal during an incident is not to produce the most elegant architecture.

It is to restore a controlled, understandable state while protecting customers and preserving evidence.

## Your mental checkpoint

Before entering the full investigation, answer these questions aloud.

1. Why should you investigate one failed scan instead of randomly examining every unhealthy Pod?
2. What is the difference between a root cause, a contributing factor, and a downstream symptom?
3. Why is HTTP 202 Accepted insufficient evidence that a scanning platform is healthy?
4. Why might adding replicas during an incident make the situation worse?
5. What should you establish before issuing a production rollback?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. Tuesday, 09:31 — You're the Incident Commander

The company operates an external attack-surface management platform.

Its architecture is familiar:

The public API receives requests.

RabbitMQ distributes scanning work.

Scanner workers perform DNS enumeration, port discovery, certificate analysis, and web technology detection.

MongoDB stores asset data and scan results.

The platform runs on Kubernetes with separate namespaces for application and infrastructure components.

The scanner worker pool normally contains six replicas.

Workers run on a designated group of nodes because they execute potentially hostile scanning tools.

The platform also uses an external-metric autoscaler driven by outstanding scan work.

At 09:31, the incident channel contains four messages.

The frontend team reports that scan submissions still succeed.

The backend team reports that RabbitMQ queue depth is increasing.

The platform team reports several Pending Pods and repeated container restarts.

The security team mentions a new egress NetworkPolicy introduced during the release.

Everyone has a theory.

The frontend engineer suspects a broken API.

The backend engineer wants more scanner replicas.

The platform engineer suspects node capacity.

The security engineer thinks the policy may be blocking something.

You have thirty minutes before a major customer's automated reporting window closes.

What do you do?

The worst answer is to begin changing things immediately.

The best answer starts by establishing the impact, the change boundary, and the evidence necessary to choose a safe containment action.

## 2. Establish the Business Impact

The first question is not "Which Pod is broken?"

It is "What useful service is currently failing?"

Your team retrieves the following measurements.

Before the release, the platform accepted approximately forty new scans per minute and completed around forty-five per minute, including existing backlog.

After the release, submissions continue at approximately forty per minute.

Successful completions fall to twelve per minute.

The backlog grows by roughly twenty-eight scans per minute, ignoring other transitions for this simplified calculation.

The public API's HTTP error rate remains low.

This tells us something important.

The customer-facing acceptance path still functions.

The downstream processing path has lost substantial capacity.

The service is degraded, not completely unavailable.

### Define the incident objective

The immediate objective is to restore a completion rate that can keep up with incoming work, prevent unacceptable data loss or duplicate effects, and recover the accumulated backlog.

The secondary objective is to identify why the release caused the degradation.

Those objectives are related but not identical.

You may restore service through a controlled rollback before fully understanding every secondary symptom.

But you must know enough to avoid making the system worse.

### Identify the affected population

Are all customers affected?

Only scans using certain modules?

Only new scans?

Only jobs assigned to a particular worker version?

This distinction determines whether partial containment is possible.

If DNS-based modules are failing while other modules remain healthy, the platform might temporarily disable affected modules or route work to known-good workers.

If every worker is experiencing OOM kills, broader rollback may be necessary.

Do not announce a complete outage when evidence supports a partial degradation.

Equally, do not call the platform healthy because the API still responds.

## 3. Preserve a Timeline and Freeze Uncoordinated Changes

At 09:34, you establish a working incident timeline.

The most recent deployment began at 09:12.

The first problematic scanner Pods appeared shortly afterward.

The completion-rate decline followed.

No major infrastructure maintenance was scheduled during that period.

These observations make the release a strong suspect.

They do not yet prove it caused every symptom.

### One person coordinates changes

During an incident, several engineers may independently attempt fixes.

One increases replicas.

Another changes resource limits.

A third edits a NetworkPolicy.

A fourth rolls back a Deployment.

Those changes can conflict, destroy diagnostic evidence, or make later reconstruction impossible.

Establish a change coordinator.

Record what is changed, why, and what outcome is expected.

For important actions, agree on a verification signal before execution.

For example:

"We will revert the worker release configuration. We expect the number of OOM-killed containers to stop increasing and scan completions to recover."

That's a testable intervention.

"Let's restart everything and see what happens" is not.

### Preserve volatile evidence

Container logs may disappear when Pods are removed.

Kubernetes Events have limited retention.

A previous container's logs may be available through `kubectl logs --previous`, but not indefinitely.

Before deleting resources, collect relevant status, events, logs, configuration revisions, and metrics where feasible.

This does not mean delaying emergency containment indefinitely.

It means avoiding unnecessary destruction of evidence while recovering.

## 4. First Evidence Card — The Deployment Changed More Than the Image

The team compares the previous and current scanner configuration.

The new release included four important changes.

First, scanner concurrency increased from two active scans per worker to eight.

Second, the worker memory limit decreased from one gibibyte to 512 mebibytes.

Third, CPU requests increased and the workload received stricter placement requirements on designated scanner nodes.

Fourth, a new egress NetworkPolicy restricted outgoing network traffic for the new worker revision.

These changes were intended to improve throughput and security.

Individually, each might have seemed defensible.

Together, they introduced a new operational regime.

### The dangerous combination

Higher concurrency increases the number of simultaneous scanning operations and their aggregate resource demands.

A lower memory limit reduces the headroom available to those operations.

Larger CPU requests make individual Pods harder to schedule.

Stricter placement narrows the set of eligible nodes.

A new egress policy changes which external systems scanning modules can reach.

The release altered execution behavior, resource allocation, placement, and connectivity in one step.

This makes attribution more difficult.

It also increases the risk that several individually reasonable changes interact in unexpected ways.

### Your first hypothesis

The new worker revision may be less capable than the previous one, despite the intention to improve throughput.

But we still need to determine which changes actually explain the observed symptoms.

Do not assume every configuration difference is harmful merely because it changed.

## 5. Second Evidence Card — Some Pods Cannot Be Scheduled

At 09:38, the platform engineer presents the following observation.

Several new worker Pods remain Pending.

Their events include messages about insufficient CPU on eligible nodes and node-affinity restrictions.

Meanwhile, a dashboard shows substantial idle CPU on other nodes.

The backend engineer says, "But the cluster has spare capacity!"

You ask, "On which eligible nodes?"

That is the relevant question.

### Reconstruct the scheduling calculation

The scanner workload now requests more CPU per Pod.

It also requires placement on nodes labeled for scanner execution.

The scheduler evaluates only nodes satisfying that hard requirement, along with all other constraints.

A general-purpose node may have eight idle CPUs and still be ineligible.

A designated scanner node may have low actual CPU utilization but insufficient unallocated request capacity.

These are separate constraints.

### Pending is not one universal problem

The Pending phase can describe a Pod that has not yet been scheduled or one still preparing its execution environment.

For this incident, the scheduler's `FailedScheduling` Events provide the stronger evidence.

They identify a placement problem.

The appropriate investigation includes node labels, taints, Pod requests, node allocatable resources, and existing scheduled requests.

### Why the HPA makes the dashboard look worse

The external-metric HPA observes growing scan backlog and increases the desired replica count.

The Deployment creates more Pod objects.

But these objects must still satisfy the scheduler's rules.

Additional Pending Pods appear.

The HPA has increased desired capacity, not actual processing capacity.

At this point, the system is requesting resources it cannot currently provide.

### Should we immediately loosen affinity?

Not necessarily.

The scanner node restriction may exist for security reasons.

Allowing potentially hostile scanner workloads onto general-purpose nodes could violate an important isolation requirement.

The correct response isn't to remove a hard constraint merely because it is inconvenient.

First determine whether the constraint protects a real security or operational boundary.

Then evaluate whether the original resource requests or worker population can be restored safely, or whether more suitable scanner-node capacity is needed.

**Scheduling failures are evidence of a mismatch between requested placement and available eligible capacity, not automatically evidence of a defective scheduler.**

## 6. Third Evidence Card — Running Containers Are Being OOM-Killed

At 09:41, the next finding arrives.

Some new worker Pods are scheduled and their containers start.

But their container status shows repeated terminations with reason `OOMKilled`.

The restart count increases.

The process appears to consume more memory after beginning several scans concurrently.

This is a different failure from Pending Pods.

A Pending Pod may never reach useful execution.

An OOM-killed container has started and subsequently been terminated under memory constraints.

### Inspect the actual boundary

The worker's memory limit is now 512 MiB.

The previous version had substantially more memory available.

At the same time, the application is permitted to execute eight scans concurrently rather than two.

Imagine that one scan consumes roughly 100 MiB at peak.

Eight concurrent scans could require around 800 MiB before accounting for the Python runtime, shared libraries, buffers, and supporting processes.

Those numbers are illustrative, not a universal memory model.

But they make the problem obvious.

The new concurrency target can exceed the configured memory boundary under realistic workloads.

The kernel may terminate the container when memory consumption reaches an enforced limit under the relevant accounting and pressure conditions.

The kubelet can then restart the container according to its restart policy.

### Why restarting doesn't help

The restarted worker loads the same configuration.

It begins processing new or redelivered tasks.

It again reaches a problematic memory state.

It gets killed again.

Kubernetes' restart mechanism is working.

The application's resource configuration is not.

### Is the correct fix increasing the limit?

Possibly, but that answer is incomplete.

You should investigate whether the application is retaining more memory than necessary, whether the workload's concurrency is appropriate, and whether tasks can be partitioned into smaller execution units.

A higher limit may be justified.

Lowering concurrency may be safer during an incident.

But changing both at once without understanding the consequences can create another confusing experiment.

The immediate choice should prioritize predictable recovery.

### OOMKilled versus eviction

Do not confuse a container OOM kill with a node-pressure eviction.

A container may be killed for exceeding its memory boundary even when the node has some free memory.

A node-pressure eviction is a kubelet response to node-level resource scarcity, potentially causing the Pod to fail and be replaced.

The remedies differ.

Inspect the termination reason and node conditions instead of calling both events "Kubernetes killed the Pod."

## 7. Fourth Evidence Card — DNS Fails, but CoreDNS Looks Healthy

At 09:45, the network engineer reports a peculiar result.

Some scanner modules successfully resolve internal Service names.

Other DNS lookups fail with timeouts.

The failures occur predominantly in new worker Pods.

CoreDNS Pods are running and healthy.

A test from an unrelated debug Pod resolves the same ordinary Kubernetes Service names successfully.

The team initially suspects an intermittent CoreDNS outage.

But the evidence suggests a narrower problem.

### Follow the actual resolver path

Our scanning platform contains several tools.

Some use the container's normal resolver configuration.

Others make DNS queries directly to specific external recursive resolvers as part of scanning behavior.

This distinction matters.

The new egress NetworkPolicy permits ordinary access to the cluster DNS service.

But it does not permit arbitrary direct DNS traffic to external resolvers.

The application's normal resolution of RabbitMQ and internal services continues to work.

A scanner module that attempts a direct query to an external resolver may time out.

Thus, some DNS operations succeed and others fail.

The pattern looks intermittent at the application level, but it is not random.

Different modules are using different network destinations and therefore different policy paths.

### Prove the hypothesis

The investigator should identify the destination IP, port and protocol used by the failing DNS request.

Then compare that request with the NetworkPolicy's allowed egress.

Inspect which Pods the policy selects.

Check whether the failures correlate with the new worker revision.

A DNS lookup from an unrelated debug Pod is not necessarily representative because the debug Pod may have different labels and therefore different network policies.

Likewise, a successful lookup through CoreDNS doesn't prove that a tool using a separate external resolver can communicate.

### The critical security question

Should we simply permit all outbound DNS traffic?

Not automatically.

The new policy may have been introduced to prevent unauthorized external communication.

A security-scanning platform has unusual requirements, but those requirements still deserve deliberate control.

Perhaps the scanner should use an approved DNS egress service.

Perhaps particular modules should be configured to use designated resolvers.

Perhaps a narrow external DNS exception is acceptable.

The correct fix must preserve legitimate functionality without casually removing an intended security boundary.

### Why readiness is also failing

The new worker's readiness check includes an operation that depends on one of the restricted external DNS paths.

When that check fails, the Pod becomes unready.

But these workers consume messages from RabbitMQ rather than receiving their work through a Kubernetes Service.

A failed readiness probe doesn't automatically prevent an already running application process from consuming queue messages.

The probe mainly influences the Pod's readiness state and normal Service endpoint eligibility.

So a worker can be unready while continuing to execute tasks.

This is another example of a signal being misunderstood.

**Readiness is not an application-level pause switch for arbitrary background processing.**

The application must explicitly control whether it accepts and processes new work.

## 8. The Combined Failure Chain

By 09:49, the team can reconstruct a plausible causal chain with supporting evidence.

The new release increases per-worker concurrency.

At the same time, it lowers the memory limit.

Workers that successfully execute several scans encounter memory pressure and OOM kills.

The release also introduces a restrictive egress policy.

Certain scanner modules can no longer reach their intended DNS resolvers.

Some tasks fail or retry because their network operations cannot complete.

Those retries and interrupted executions reduce useful throughput and can increase resource consumption.

Meanwhile, larger CPU requests and stricter placement rules prevent many new workers from scheduling.

The HPA sees an increasing backlog and requests additional replicas.

But those replicas cannot provide the expected additional capacity.

The queue grows further.

### Visual anchor — the incident graph

```text
                   RELEASE
                      |
       +--------------+--------------+
       |              |              |
  Higher scan      Smaller       New egress
  concurrency     memory limit     policy
       |              |              |
       +-------+------+         DNS restrictions
               |                    |
          Memory pressure      Module failures
               |                    |
           OOM kills              Retries
               |                    |
               +---------+----------+
                         |
                  Lower goodput
                         |
                    Queue grows
                         |
                   HPA scales up
                         |
               New replicas requested
                         |
               Larger CPU requests
               + strict node affinity
                         |
                    Pending Pods
                         |
               Capacity never arrives
```

This is a causal model supported by the investigation, not something the team should assume without evidence.

Notice that several different Kubernetes components are behaving correctly.

The scheduler enforces placement requirements.

The kernel enforces memory limits.

The network implementation enforces security policy.

The HPA reacts to its metric.

The workload controller tries to maintain the declared population.

The system is failing because the collective configuration and application behavior do not produce the intended business outcome.

**A distributed system can consist of locally correct components and still behave disastrously as a whole.**

## 9. Choose a Containment Strategy

The team now has enough evidence to make a controlled recovery decision.

The recent release changed several interacting parameters.

The previous worker revision was functioning.

No evidence suggests that the previous revision is incompatible with newly persisted business data.

The most defensible immediate strategy may therefore be to restore the known-good worker configuration, including its associated network and resource policies.

But this requires coordination.

### Stop conflicting automation

First, identify which system owns the production deployment configuration.

If GitOps manages the resources, a manual Deployment rollback may be undone by the reconciliation controller.

The team should correct or revert the authoritative desired state, or follow an established emergency procedure for temporarily controlling synchronization.

Do not create an endless contest between `kubectl` and GitOps.

### The HPA complication

The backlog remains large.

Even after reverting the worker image, the HPA may continue requesting additional replicas because its metric still indicates demand.

The team needs to decide how to bound scaling during recovery.

This might involve temporary, documented adjustments to autoscaling limits or other approved capacity controls.

But arbitrary manual scaling can conflict with the HPA.

The relevant control loops must be coordinated rather than fought individually.

### Protect incoming work

If the system cannot keep pace with incoming scans, consider temporarily limiting new submissions or deferring noncritical work.

If the API continues accepting requests, it should provide honest status and preserve durable work records.

Do not clear the RabbitMQ queue merely to make a dashboard look healthy.

Those messages represent customer operations.

Deleting them could turn a recoverable backlog into permanent data loss.

### Preserve recovery semantics

Some messages may have been processed partially before workers crashed.

The platform must tolerate redelivery and prevent unacceptable duplicate effects.

Before aggressively restarting workers, verify the task acknowledgment and idempotency behavior.

A healthy worker pool executing the same expensive scan multiple times may still produce the wrong outcome.

## 10. The Recovery Is Not Complete When Pods Turn Green

At 10:03, the known-good worker configuration is restored.

New Pods start successfully.

OOM kills stop increasing.

Internal and expected external DNS operations recover.

The number of Pending Pods declines as the desired population becomes schedulable.

The rollout reports success.

Can the team close the incident?

Not yet.

The backlog still exists.

Some tasks may have exhausted retries or entered dead-letter handling.

Some may have partially completed.

Some customers may have received inaccurate status updates.

### Recover the backlog

Verify that workers are processing messages and that successful completion rate has recovered.

Compare task arrival rate and completion rate.

If completions exceed arrivals, the backlog should begin shrinking.

But a falling queue depth alone is not proof of success.

Messages could also be disappearing because they are rejected, discarded or moved to a dead-letter destination.

Track the actual terminal outcomes of business operations.

### Reconcile uncertain tasks

Identify scans whose execution state is ambiguous.

For example, a worker may have persisted findings before being killed but failed to acknowledge the RabbitMQ message.

A replacement worker may receive the same task.

The application needs a safe way to determine whether to resume, retry, or consider the operation already completed.

That may rely on durable scan identifiers, atomic state transitions, idempotent persistence, or other application-level mechanisms.

Kubernetes cannot infer the correct answer.

### Verify customers' results

Choose a representative sample of affected scans.

Confirm that their state and findings are coherent.

Check whether failures are concentrated in specific scanning modules.

Verify that no tenant's data became associated with another tenant's operation.

For a security product, incorrect results can be as damaging as missing results.

A dashboard showing "100 percent available" is not sufficient evidence that the service has recovered.

## 11. Time to Declare Service Recovery

At 10:12, the team has the following evidence.

The scanner Deployment is stable.

No new OOM kills have been observed during the monitoring interval.

DNS failures associated with the new policy have stopped.

The queue completion rate is higher than the current arrival rate.

The oldest queued message is getting younger as backlog drains.

Representative affected scans complete correctly.

The team has isolated any messages requiring manual reconciliation.

Now the incident commander can reasonably declare that the primary service has recovered, while maintaining a separate follow-up for remaining customer work.

This distinction is useful.

**Service recovery** means the platform has returned to an acceptable operating state.

**Incident closure** may require additional reconciliation, communication, analysis, and preventive work.

The platform can be operational before every follow-up action is complete.

But unresolved customer data or business correctness issues must remain explicitly tracked.

## 12. Why the Incident Was Harder Than It Looked

Let's examine the deceptive signals.

### The healthy API

The API accepted scans.

This showed that the request-acceptance path was functioning.

It did not prove that background processing worked.

### The idle CPU dashboard

Some nodes had unused CPU.

But the scanner Pods had resource requests and placement constraints that prevented scheduling onto those nodes.

Actual CPU utilization did not establish schedulability.

### The healthy CoreDNS Pods

CoreDNS was available for ordinary cluster DNS lookups.

Some scanner modules nevertheless attempted DNS queries through external resolvers blocked by the new egress policy.

DNS health depended on the actual resolver path.

### The restarting containers

Kubernetes correctly restarted containers after termination.

But the processes repeatedly encountered the same resource configuration and workload.

Restarting execution didn't fix the underlying memory mismatch.

### The active HPA

The autoscaler reacted to increasing backlog.

But desired replicas didn't become useful processing capacity.

The controller optimized its configured signal, not the entire system's business objective.

### The successful rollback

Restoring a previous image and configuration helped recover execution.

But it didn't automatically resolve partially completed scan operations or messages in dead-letter handling.

Business recovery remained a separate responsibility.

Every misleading observation came from interpreting one component's narrow status as a guarantee about the whole system.

That is the central intellectual challenge of production engineering.

## 13. What Would a Better Release Have Looked Like?

The team's post-incident review identifies several improvements.

### Separate high-risk changes

The release combined concurrency tuning, memory-limit reduction, scheduling changes, and network-policy restrictions.

These changes affected different mechanisms and created interactions that were difficult to test.

A safer approach would introduce them through smaller, observable changes.

For example, first deploy the egress policy in a controlled environment and verify every scanner module's legitimate network dependencies.

Then test higher concurrency against representative workloads.

Only afterward adjust resource requests, limits, and scaling behavior based on measured data.

This doesn't mean every change must be deployed individually.

It means related changes should be grouped deliberately, and high-risk interactions should be tested before broad exposure.

### Test scanner modules under real network policy

A successful unit test inside a developer laptop doesn't establish that a scanner will work under production egress restrictions.

Integration tests should cover representative module operations in an environment with the intended policies enforced.

The tests should distinguish normal cluster DNS from direct external resolver access.

Where direct external DNS is a legitimate requirement, it should be incorporated into an approved egress design.

### Test realistic memory peaks

Increasing scan concurrency changes aggregate memory consumption.

Performance tests should measure memory usage under representative combinations of scanning modules.

A single lightweight scan isn't sufficient evidence that eight concurrent complex scans fit within a 512 MiB limit.

The team should use measured peak behavior and appropriate safety margins.

### Validate scheduling feasibility

Before rollout, compare Pod resource requests and placement constraints against eligible node pools.

Ensure that planned replicas can fit, including capacity needed during rolling updates.

If node autoscaling is expected to provide more capacity, test whether the provisioner can actually create nodes satisfying those constraints.

A configuration that is valid YAML can still describe an impossible deployment.

### Make scaling follow useful capacity

For queue-driven workloads, monitor how many scans are completed per unit time, queue age, and the relationship between concurrency and downstream capacity.

Use the HPA as part of a broader capacity design rather than assuming additional replicas always increase throughput.

### Treat readiness carefully

A scanner readiness probe should reflect an appropriate local ability to participate in the workload.

It should not become a fragile collection of every possible external dependency or scanning operation.

And if the application consumes RabbitMQ messages directly, the worker's application logic must decide whether it should continue accepting new work when important dependencies are unavailable.

Kubernetes readiness alone will not stop the queue consumer.

## 14. The Postmortem: Write Causes, Not Blame

A useful postmortem should explain what happened, why it happened, how the incident was detected, how it was contained, and what will change.

It shouldn't settle for "human error" or "bad configuration."

Those labels provide very little engineering value.

### Trigger

A release introduced several changes affecting worker concurrency, resource boundaries, placement, and outbound network policy.

### Contributing factors

The release process didn't adequately test the combined effects.

Module-level DNS requirements were insufficiently documented.

Resource limits were not validated against peak concurrency.

Scheduling feasibility under the new Pod requests wasn't adequately checked.

The autoscaling strategy reacted to queue growth without confirming that additional replicas could become healthy processing capacity.

### Impact

Customer scans experienced delayed or failed completion.

The backlog grew.

Some operations required retry or reconciliation.

The exact impact should be reported from measured production data rather than guessed from alert volume.

### Detection

The strongest early signal was declining successful scan completion relative to accepted work.

Infrastructure signals such as OOM kills and Pending Pods provided diagnostic evidence.

### Recovery

The team coordinated an authoritative rollback of the affected workload configuration and policies, contained incoming demand where necessary, and verified recovery of useful processing throughput.

### Prevention

Future changes will have better module-level network tests, realistic concurrency and memory testing, scheduling-capacity checks, controlled rollouts, and business-outcome release gates.

This is what a useful postmortem produces: a better system.

Not a ceremonial document explaining that engineers should be more careful next time.

## 15. The Senior Engineer's Diagnostic Framework

We can now generalize the incident into a reusable method.

When a Kubernetes application appears broken, investigate from the outside inward.

Start with the business operation.

What is failing, and how much of the product is affected?

Next, identify the relevant change.

Which application revision, configuration, policy, or infrastructure event preceded the degradation?

Then find the first broken transition in the application's execution path.

Was the request accepted?

Was the message published?

Was the worker scheduled?

Did its container start?

Did it receive the work?

Could it reach dependencies?

Did it persist results?

Finally, investigate the Kubernetes mechanism responsible for the failed transition.

### If the Pod does not exist

Inspect the controlling workload resource and its subordinate objects.

Is the Deployment or Job asking for the expected Pod population?

Are controllers creating the resources?

### If the Pod cannot schedule

Inspect scheduler events, resource requests, node allocatable capacity, labels, taints, topology constraints, and storage requirements.

### If the Pod is assigned but cannot start

Inspect image pulling, container configuration, volume mounts, Secrets, and kubelet events.

### If the container starts but repeatedly exits

Inspect termination reasons, previous logs, health probes, resource limits, and application behavior.

### If the application cannot communicate

Separate DNS resolution, Service endpoints, network policies, Pod routing, transport connection, and application protocol behavior.

### If infrastructure looks healthy but customers are failing

Investigate business workflows, database consistency, message semantics, external dependencies, and end-to-end tracing.

### If autoscaling behaves strangely

Inspect the scaling metric, desired replica count, ready capacity, scheduling constraints, and downstream bottlenecks.

The purpose of this framework is not to memorize a fixed sequence of commands.

It is to ask the right question at the right abstraction boundary.

## 16. Communicating During the Incident

Technical investigation is only one part of senior-level incident response.

You also need to communicate uncertainty and decisions clearly.

Imagine management asks:

"Is Kubernetes down?"

A poor response is:

"Some Pods are Pending, the HPA is scaling, there are DNS errors, and we're checking kubelet logs."

That may be technically accurate, but it doesn't explain the business situation.

A better response is:

"The API is accepting scan requests, but background processing capacity has dropped substantially following the worker release. We're investigating resource and network-policy changes. The queue is growing, so we're preparing a controlled rollback and will verify recovery through scan completion metrics."

This response distinguishes impact, evidence, hypothesis, and action.

It doesn't pretend to know the root cause before the investigation confirms it.

It also doesn't drown the audience in implementation details.

### A useful incident update structure

Communicate four things.

**Impact:** What customer functionality is affected?

**Evidence:** What facts are established?

**Action:** What is the team doing now?

**Uncertainty:** What remains unknown or needs verification?

Avoid unsupported promises about exact recovery time.

Don't announce that the issue is resolved merely because a deployment completed.

And don't confuse technical confidence with communication clarity.

A senior engineer should make the system understandable to people who aren't inside the Kubernetes dashboard.

## 17. The Oral Examination

This is the final oral examination of SE450. Answer the questions without looking at the solutions.

Treat them like a senior engineering interview or a production incident simulation.

### Challenge 1 — The First Five Minutes

You join an incident with these symptoms:

- API requests succeed.
- Scanner completion rate has collapsed.
- Several Pods are Pending.
- Some workers are restarting.
- RabbitMQ backlog is growing.

What are your first five investigative actions, and what would each establish?

### Challenge 2 — The Idle Cluster

New scanner Pods request 1.5 CPUs each.

Several general-purpose nodes have abundant spare CPU.

The scanner Pods nevertheless remain Pending.

Their specification requires nodes labeled `pool=scanner`.

What would you inspect before modifying the placement policy?

### Challenge 3 — The DNS Red Herring

CoreDNS is healthy.

A debug Pod resolves Kubernetes Services normally.

New scanner Pods report DNS timeouts during selected scanning modules.

Why does this evidence not establish that DNS is globally healthy or globally broken?

What specific comparison would you perform?

### Challenge 4 — The OOM Loop

The new worker version increases concurrency from two to eight and reduces its memory limit.

Containers repeatedly report `OOMKilled`.

What evidence would distinguish excessive legitimate memory demand from a memory leak?

Which short-term mitigation might be safest?

### Challenge 5 — The HPA That Creates Pending Pods

An external-metric HPA requests twelve replicas.

Only seven workers are actually running.

Five more remain Pending.

Queue depth keeps increasing.

What has the HPA accomplished, and what has it not accomplished?

### Challenge 6 — The Unready Queue Consumer

A scanner worker fails its readiness probe because a remote DNS query fails.

It nevertheless continues consuming RabbitMQ messages.

Is Kubernetes malfunctioning?

How should the application control its intake of work?

### Challenge 7 — The Dangerous Rollback

A GitOps controller owns the worker Deployment and NetworkPolicy.

An engineer manually rolls back the Deployment image.

Several minutes later, the new image returns.

What happened?

What must the team coordinate before attempting another intervention?

### Challenge 8 — The Queue Looks Empty

After recovery, RabbitMQ queue depth falls rapidly.

The platform team announces success.

However, successful scans per minute remain low.

Name at least three possible explanations.

### Challenge 9 — The Security Trade-off

The new NetworkPolicy blocks direct DNS queries to external resolvers.

Some scanning modules require those queries.

Would you remove the policy entirely?

Propose a safer design.

### Challenge 10 — The Incident Commander

You have evidence that the recent worker release caused severe degradation.

The previous version was healthy.

The backlog is growing.

The rollback is believed to be compatible with current persisted state.

Would you continue investigating indefinitely, or initiate recovery?

Explain your decision and the signals you would use to verify success.

## 18. Solutions and Discussion

### Solution 1 — Establish impact, change, and the broken transition

First, quantify the business failure through scan acceptance, start, and completion metrics.

Second, identify recent application and infrastructure changes.

Third, follow a representative failed scan through API, queue, worker, and persistence.

Fourth, inspect the relevant workload status, including Pending Pod events and container termination reasons.

Fifth, correlate the failure with configuration and resource differences between known-good and current revisions.

These actions create a testable hypothesis without making unnecessary changes.

### Solution 2 — Eligible capacity matters, not global spare CPU

Inspect the Pod's resource requests and node-selection requirements.

Then inspect nodes carrying the required label.

Compare their allocatable resources with existing scheduled requests.

Check taints, tolerations, affinity, topology constraints, and autoscaler provisioning options.

Only consider relaxing the placement requirement after understanding why it exists.

### Solution 3 — Resolver paths may differ

The debug Pod may use CoreDNS while scanner modules use explicit external resolvers.

Different Pods may also be selected by different NetworkPolicies.

Compare the source Pod, destination resolver address, port, protocol, and effective network policy.

Test from a representative affected Pod or equivalent diagnostic environment.

Don't equate one successful DNS test with universal DNS connectivity.

### Solution 4 — Measure workload demand and allocation behavior

Inspect memory usage over time, peak consumption, scan concurrency, active module types, and termination reasons.

A repeatable increase tied to concurrent workload size may reflect an undersized limit or unsuitable concurrency.

Continually growing retained memory under comparable work may suggest a leak.

A safe immediate mitigation may be restoring the previous concurrency and memory settings, especially if they are known to be compatible with the workload.

Further optimization can follow controlled measurements.

### Solution 5 — Desired capacity increased, actual capacity did not

The HPA increased the target workload population.

The Deployment created additional Pod objects.

But the scheduler could not place all of them.

Useful processing capacity did not rise proportionally.

The team must investigate scheduling constraints and resource capacity, while also verifying that additional workers would improve throughput rather than overload downstream systems.

### Solution 6 — Readiness doesn't pause arbitrary background processing

Kubernetes readiness determines whether the Pod is considered ready and influences normal Service endpoint routing.

It does not inherently stop a running process from consuming RabbitMQ messages.

The worker should implement its own intake-control behavior.

It can stop fetching new work when essential dependencies are unavailable and preserve or safely recover in-flight tasks.

The readiness signal should reflect appropriate local workload health without introducing unnecessary dependence on every external system.

### Solution 7 — GitOps restored the declared state

The live Deployment changed, but the authoritative Git configuration still declared the new image.

With appropriate automated reconciliation settings, the GitOps controller restored the declared version.

The team should correct the authoritative configuration or use the established emergency procedure for coordinating reconciliation.

The Deployment and NetworkPolicy may both need to be restored as a compatible set.

### Solution 8 — Queue disappearance isn't completed work

Messages might have been moved to a dead-letter queue.

They might have been rejected or discarded according to broker and application policies.

Consumers might have acknowledged work prematurely.

Jobs could remain stuck after removal from the ready queue.

Or the monitoring metric might describe only one queue state while active or unacknowledged work remains elsewhere.

Verify durable business outcomes, not merely queue depth.

### Solution 9 — Preserve the intended security boundary

Do not automatically permit unrestricted outbound traffic.

Determine which scanning modules legitimately require external DNS and which resolvers they need.

Consider an approved DNS egress service or narrow policy exceptions with appropriate monitoring.

Test the resulting configuration under actual network-policy enforcement.

Security and functionality must be designed together.

### Solution 10 — Recover once the evidence justifies it

If the recent release is strongly implicated, the previous version is known-good, and rollback compatibility has been established sufficiently for the incident's risk, initiate controlled recovery.

Preserve relevant evidence, coordinate GitOps and autoscaling ownership, and communicate the decision.

Verify recovery through successful scan completions, reduced failure rates, stable container behavior, and backlog drainage.

Continue investigating the deeper causes after the system is under control.

Incident response is not an academic exercise in discovering every possible failure before taking any action.

It is the engineering of safe decisions under uncertainty.

## 19. The Mental Model Worth Keeping

Every production incident is a disagreement between expected and observed reality.

Kubernetes provides many mechanisms for reducing that disagreement, but each mechanism understands only part of the system.

The scheduler understands placement constraints.

The kubelet understands aspects of container execution.

Network policies control permitted traffic.

Workload controllers maintain resource populations.

Autoscalers respond to configured metrics.

None of them independently understands whether a customer received correct scanning results.

When investigating, reconstruct the chain from business intent to execution and back.

**What changed? What failed? Which component owns that transition? What evidence proves it? What intervention is safe? How will we verify recovery?**

Those six questions form the core of production incident reasoning.

---

## Course Completion — SE450: Kubernetes and Platform Engineering

You've now walked through Kubernetes from its central abstraction to its operational consequences.

In SE450-L01, you learned that Kubernetes is a distributed reconciliation system.

In SE450-L02, you learned that different workloads require different lifecycle and identity contracts.

In SE450-L03, you followed traffic through DNS, Services, endpoints, Pod networking, and security policy.

In SE450-L04, you separated scheduling requests, runtime limits, placement constraints, and autoscaling feedback loops.

In SE450-L05, you distinguished disposable execution from configuration, secrets, and persistent state.

In SE450-L06, you examined workload identity, privilege boundaries, and multi-tenant isolation.

In SE450-L07, you learned that deployment success is not the same as product correctness.

And in this final lecture, you integrated those mechanisms into a single incident investigation.

The purpose of the course wasn't to turn you into a walking encyclopedia of Kubernetes flags.

It was to make the platform intelligible.

When you see a broken Deployment, you should understand which controllers are involved.

When a Pod remains Pending, you should know how placement decisions are made.

When a Service is unreachable, you should distinguish name resolution from endpoint membership and packet transport.

When a worker disappears, you should understand what Kubernetes can restore and what application state remains at risk.

And when production fails, you should be able to organize the investigation without mistaking symptoms for causes.

That is the beginning of real platform-engineering competence.

*The spoken lecture ends here. The remaining material is an optional incident-response workshop, further reading, and the final interview reference.*

---

## Optional Practical Lab — The Incident Commander Workshop

**Objective:** Investigate an intentionally broken application in a disposable Kubernetes environment, then prepare an incident report with evidence-based conclusions.

This lab deliberately avoids generating real memory exhaustion, crashing nodes, or tampering with cluster DNS. Those experiments can destabilize an environment and aren't necessary to demonstrate the investigative principles.

Use a local Minikube or kind cluster with a known context.

### Part A — Prepare a controlled incident

Verify your environment:

```bash
kubectl config current-context
kubectl get nodes
```

Create a dedicated namespace:

```bash
kubectl create namespace se450-l08
```

Create `incident.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inventory-api
  namespace: se450-l08
spec:
  replicas: 2
  selector:
    matchLabels:
      app: inventory-api
  template:
    metadata:
      labels:
        app: inventory-api
    spec:
      containers:
        - name: web
          image: nginx:stable-alpine
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 3
---
apiVersion: v1
kind: Service
metadata:
  name: inventory-api
  namespace: se450-l08
spec:
  selector:
    app: inventory-service
  ports:
    - port: 8080
      targetPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: impossible-worker
  namespace: se450-l08
spec:
  restartPolicy: Never
  nodeSelector:
    training.example.com/special-worker: "true"
  containers:
    - name: worker
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      resources:
        requests:
          cpu: "50m"
          memory: "32Mi"
```

The namespace contains two deliberately independent faults.

The Service's selector doesn't match the Deployment's Pod labels.

The standalone worker Pod requires a node label that an ordinary practice cluster won't have.

Apply the resources:

```bash
kubectl apply -f incident.yaml
```

Allow the Deployment to become ready:

```bash
kubectl rollout status deployment/inventory-api \
  -n se450-l08 --timeout=120s
```

Do not correct the faults yet.

### Part B — Gather evidence without changing resources

Inspect the objects:

```bash
kubectl get deployments,pods,services -n se450-l08 -o wide
kubectl get endpointslices -n se450-l08
kubectl get events -n se450-l08 \
  --sort-by=.metadata.creationTimestamp
```

Describe the Deployment and the unschedulable worker:

```bash
kubectl describe deployment inventory-api -n se450-l08
kubectl describe pod impossible-worker -n se450-l08
```

Now inspect the Service:

```bash
kubectl describe service inventory-api -n se450-l08
```

Answer the following without changing anything:

1. Why does the Deployment report healthy replicas while its Service has no eligible backends?
2. Why is the worker Pod Pending despite its tiny CPU and memory requests?
3. Which controller or mechanism is responsible for each failure?
4. Which Kubernetes observations prove your conclusions?
5. Which symptoms would be invisible if you looked only at container logs?

### Part C — Form and test hypotheses

Your first hypothesis should explain why the Service has no usable endpoints.

Compare:

`spec.selector` on the Service.

The labels on the Deployment's Pod template.

The labels on the actual Pods.

Your second hypothesis should explain why the worker cannot schedule.

Inspect the `nodeSelector` and the node labels.

A healthy application container doesn't solve the Service selector problem.

And increasing node CPU doesn't solve a missing hard-required node label.

These are different constraints.

### Part D — Make targeted corrections

Patch the Service selector:

```bash
kubectl patch service inventory-api -n se450-l08 \
  --type=merge \
  -p '{"spec":{"selector":{"app":"inventory-api"}}}'
```

Inspect the EndpointSlices again:

```bash
kubectl get endpointslices -n se450-l08 \
  -l kubernetes.io/service-name=inventory-api -o wide
```

For the worker, don't modify node labels just to make the Pod schedule.

Instead, use a corrected copy of its manifest that removes the artificial `nodeSelector`. Because ordinary Pod scheduling fields are not freely mutable after creation, delete only the disposable training Pod and recreate it with the corrected manifest.

```bash
kubectl delete pod impossible-worker -n se450-l08
```

Then apply the corrected Pod definition.

Verify that the new Pod can schedule.

The important lesson is that each correction addresses a specific violated contract.

### Part E — Analyze an OOM incident from evidence

Rather than exhaust the local machine's memory, consider the following fictional observation from the production scanner incident.

```text
Pod: scanner-worker-7c8d
Container: scanner
Last termination reason: OOMKilled
Last exit code: 137
Memory request: 256Mi
Memory limit: 512Mi
Configured concurrency: 8
Restart count: 6
```

Explain:

1. Which facts are established by this record?
2. Does it prove a memory leak?
3. What additional metrics or profiling information would help?
4. Why might changing the CPU request not solve the failure?
5. What does the restart count tell you, and what doesn't it tell you?

A good answer should distinguish resource policy, application allocation behavior, and workload characteristics.

### Part F — Prepare an incident update

Write a concise incident update using this structure.

**Impact:** What is broken for users or systems?

**Established evidence:** Which observations have been verified?

**Working hypothesis:** What mechanism best explains the failure?

**Immediate action:** What change will you make, and why?

**Verification:** What observation will establish that the change worked?

Do not write "Kubernetes is broken."

Name the failing resource relationship or behavior.

### Part G — Cleanup

Verify that the namespace contains only the exercise's resources:

```bash
kubectl get all -n se450-l08
```

Then remove it:

```bash
kubectl delete namespace se450-l08
```

Do not delete a shared namespace or production resources.

### Final workshop — The senior interview

Imagine an interviewer presents this scenario:

"A production application works locally, but its Kubernetes deployment has intermittent errors. Some Pods restart, others remain Pending, and scaling doesn't improve throughput. How would you investigate?"

Deliver a structured five-minute answer.

Begin with business impact and recent changes.

Explain how you would identify the first broken transition.

Describe which Kubernetes resources and status fields you would inspect.

Distinguish scheduling, execution, networking, and application failure.

Explain how you would select a safe containment action.

Finish with the evidence required to declare recovery.

If you can do that convincingly, you have understood the central lessons of SE450.

---

## Further Reading

1. [Debugging Running Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/) — Pod status, events, container logs, and inspection.
2. [Debugging Services](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/) — Service discovery, selectors, endpoint membership, and connectivity.
3. [Debugging DNS Resolution](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/) — Cluster DNS troubleshooting.
4. [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) — Rollout conditions, availability, and revision management.
5. [Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/) — Scheduling requests, resource limits, and OOM behavior.
6. [Assigning Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/) — Selectors and affinity.
7. [Node-pressure Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/) — Eviction behavior and node resource pressure.
8. [Horizontal Pod Autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/) — Scaling calculations and controller behavior.
9. [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/) — Egress restrictions and workload isolation.
10. [Argo CD Automated Synchronization](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/) — Automated synchronization and self-healing behavior.

---

## Dense Cheatsheet — Interview Glance Card

*This final reference is fenced for rapid screen-based revision.*

```text
SE450-L08 — THE KUBERNETES INCIDENT ROOM

INCIDENT METHOD

1. Establish customer/business impact
2. Identify recent changes
3. Trace one failed operation end-to-end
4. Find first broken transition
5. Identify owning component/mechanism
6. Collect discriminating evidence
7. Contain damage safely
8. Verify business recovery
9. Reconcile unfinished work
10. Prevent recurrence

THREE TIMELINES

Change:
  Deployments, config, policy, infrastructure

Infrastructure:
  Pod states, scheduling, restarts, endpoints, nodes

Business:
  Accepted, started, completed, failed, delayed

ROOT CAUSE VS SYMPTOM

  Root cause:
    Fundamental condition creating failure

  Contributing factor:
    Makes failure more likely or severe

  Symptom:
    Observable consequence

  Multiple alarms may share a causal chain

KUBERNETES RESOURCE PATH

  Desired object
    -> Controller
    -> Pod
    -> Scheduler
    -> Kubelet/runtime
    -> Container
    -> Network/dependencies
    -> Business operation

PENDING POD

  Inspect:
    Pod conditions/events
    CPU/memory requests
    Node allocatable and allocated requests
    Node selectors/affinity
    Taints/tolerations
    Topology constraints
    Storage attachment/binding
    Node autoscaler configuration

  Idle CPU != schedulable capacity

CONTAINER RESTARTING

  Inspect:
    Restart count
    Current/last state
    Termination reason
    Logs --previous
    Memory usage
    CPU throttling
    Probe failures
    Application configuration

  OOMKilled != proof of memory leak
  CrashLoopBackOff != root cause

NETWORK FAILURE

  Check:
    Exact failing name/address
    Source Pod/namespace/labels
    Resolver path
    Service ports/selectors
    EndpointSlice readiness
    Direct Pod IP connectivity
    NetworkPolicy ingress/egress
    CNI datapath
    Application listener/protocol

  CoreDNS healthy != all DNS paths work
  Debug Pod success != affected Pod success

READINESS

  Controls ready status / Service endpoint eligibility
  Does not automatically pause a queue consumer
  Application must implement work-intake control

AUTOSCALING

  HPA increases desired replicas
  Scheduler must place Pods
  Node autoscaler may provide capacity
  Running Pods must process useful work

  More desired replicas != more throughput

OOM VS EVICTION

  OOMKilled:
    Container memory failure, possible restart

  Node-pressure eviction:
    Kubelet responds to node resource pressure
    Pod failed/replaced depending on controller

  Preemption:
    Scheduler may displace lower-priority Pod

GITOPS

  Git/source configuration may own desired state
  Live manual changes can be reconciled away
  Coordinate emergency recovery with controller
  Revert image, config, and policies coherently

RABBITMQ RECOVERY

  Queue depth != successful business completion
  Check ready/unacked/dead-letter states
  Verify task ID and idempotency
  Reconcile partial executions
  Never delete customer work casually

INCIDENT DECISION

  What is affected?
  Which evidence is established?
  What remains uncertain?
  Which action safely contains impact?
  What could the intervention break?
  How will recovery be verified?

POSTMORTEM

  Trigger
  Contributing factors
  Customer impact
  Detection
  Timeline
  Response
  Recovery
  Preventive actions

NO MAGIC STATUS

  API 202             != scan completed
  Pod Running         != ready
  Pod Ready           != business correct
  Deployment complete != customer success
  DNS success         != reachable endpoint
  Idle node CPU       != schedulable Pod
  HPA scaling         != added processing capacity
  Queue shrinking     != completed customer work
  Rollback complete   != external state restored

FINAL SENIOR MENTAL MODEL

  Desired state
      vs
  Observed infrastructure
      vs
  Actual business outcomes

  Reconstruct the transitions.
  Establish where they diverge.
  Change the smallest safe thing.
  Verify useful recovery.

SENIOR LINE

  "I begin with business impact, reconstruct the change
   and execution timelines, identify the first broken
   boundary, and use Kubernetes status as evidence
   rather than treating it as the whole truth. Recovery
   is complete only when useful business operations
   work correctly again."
```
