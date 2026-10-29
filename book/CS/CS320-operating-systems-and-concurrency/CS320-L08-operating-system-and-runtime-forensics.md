---
id: CS320-L08
course: CS320
title: "Operating-System and Runtime Forensics"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: CS320-L07
next: null
---

# CS320 — Operating Systems and Concurrency

## Lecture 08: Operating-System and Runtime Forensics

*At 09:00, your team deploys a small change to a supplier integration. By 09:16, API latency is climbing, sockets are accumulating, memory usage is rising, and Kubernetes is restarting workers. CPU looks fine. The database looks fine. Everyone has a theory. Your job is to determine which theory is actually true.*

# Part I — Intuition

## The picture to carry in your head

Imagine arriving at a hotel during a particularly disastrous morning.

Guests are waiting at reception. The elevators have stopped working properly. The laundry department is overwhelmed, and the building manager reports unusually high electricity consumption.

Every department offers its own explanation.

Reception blames the elevators.

Maintenance blames the electrical system.

The laundry supervisor says the hotel accepted too many guests.

Someone proposes hiring more receptionists.

Someone else suggests installing a larger electrical transformer.

The manager wants to restart the building's central control system.

All these proposals might change something. But none begins by establishing what actually happened.

A capable investigator starts differently.

She reconstructs the timeline.

She asks which symptoms appeared first.

She identifies which systems share resources.

She looks for one observation that distinguishes competing explanations.

Perhaps the elevator problem started when a maintenance procedure left a door sensor engaged. Guests then used the stairs, overwhelming the reception area's access system. The laundry delays and electricity alerts may be consequences of other systems attempting to compensate.

Or perhaps these symptoms really do have independent causes.

The investigator's job is not to force them into one satisfying story.

It is to establish which causal relationships the evidence supports.

Production software works the same way.

## 1. A symptom is not a diagnosis

Suppose an API request takes five seconds.

That's an observation.

"The CPU is overloaded" is a hypothesis.

"The supplier is slow" is another hypothesis.

"The database is blocked" is a third.

All three could produce a five-second response.

So could a request waiting for an available connection from a pool, a callback delayed by a blocked event loop, or an operation waiting to obtain CPU time under a cgroup restriction.

Latency tells us how long something took.

It does not tell us where that time was spent.

This distinction will guide the entire investigation.

**An observation establishes what happened. A mechanism explains how it could happen. A causal conclusion requires evidence connecting the two.**

## 2. Follow one request through the machinery

Our hotel-booking backend receives an availability request.

The application validates the search, contacts an external supplier, processes the response, and returns available rooms to the customer.

Imagine tracing that request through the layers we've studied.

At the application layer, the request has a deadline, a business identifier, and a collection of asynchronous tasks.

At the runtime layer, Node.js coordinates callbacks, Promises, sockets, native operations, and memory allocation.

At the operating-system layer, Linux manages threads, file descriptors, network sockets, memory mappings, CPU scheduling, and resource limits.

Each layer has its own notion of progress.

A Promise can reject while its underlying network connection remains open.

A socket can be readable while its JavaScript callback hasn't executed.

A process can have low JavaScript heap usage while its container approaches a memory limit.

A host can have idle processors while one container is being throttled.

These aren't contradictions.

They're observations made at different boundaries.

A strong investigation asks which boundary controls the behavior currently causing trouble.

## 3. One failure can produce several symptoms

Consider a request that contacts a supplier.

The supplier doesn't respond before our application's deadline.

We return a timeout error.

But suppose the application forgets to close the associated connection.

That connection remains alive.

After enough timed-out requests, the process accumulates sockets.

Open sockets consume file descriptors and other resources.

Pending operations may also retain JavaScript objects, buffers, timers, and native state.

Now the service begins approaching its descriptor limit.

New connection attempts fail.

The application retries.

Retries create more attempts.

Memory usage rises.

Eventually, the container may encounter an OOM condition.

From the outside, we see timeouts, connection errors, memory pressure, and restarts.

It would be easy to conclude that four things are broken.

But the chain may begin with one incorrectly managed resource lifetime, amplified by an uncontrolled retry policy.

This is the incident we'll investigate.

## 4. The first clue is not always the root cause

In our story, the supplier response was slow.

Was the supplier responsible for the incident?

It might have triggered the failure.

But a well-designed client should tolerate ordinary slow responses without accumulating resources indefinitely.

The supplier can be slow without causing a local resource leak in a correctly implemented client.

This is why we distinguish a **trigger** from a **root cause**.

A trigger creates the circumstances in which a defect becomes visible.

The root cause explains why the system failed to behave correctly under those circumstances.

Contributing factors determine how severely the failure spreads.

The distinction isn't always perfectly objective, but it makes our explanation more useful.

If we only blame the supplier, we may leave the cleanup defect untouched.

If we fix the cleanup defect but ignore an unlimited retry policy, the next supplier outage may still overwhelm the service through a different mechanism.

## 5. The investigator's most valuable question

Imagine three competing explanations for the current latency.

The main JavaScript thread is blocked.

The supplier is slow.

Timed-out operations are leaking connections.

What should we measure next?

Not everything.

We should choose a measurement whose possible outcomes distinguish these explanations.

If lightweight endpoints are also delayed, main-thread blockage becomes more plausible.

If supplier calls are slow from independent clients but resource usage remains bounded, genuine external latency becomes more plausible.

If socket counts keep increasing after application requests time out, the resource-lifetime hypothesis becomes much stronger.

A good investigator doesn't merely collect more data.

She collects data that reduces uncertainty.

## 6. Remember the difference between mitigation and understanding

During a severe incident, restarting a worker may restore service.

Rolling back a deployment may reduce customer impact.

Increasing a limit may buy time.

Those can be reasonable emergency actions.

But they don't automatically explain what happened.

A restart closes connections, releases memory, and resets process-local state.

Of course a resource leak disappears temporarily when the leaking process disappears.

The question is whether the same failure will return under the same conditions.

**Mitigation reduces the current damage. Remediation removes or controls the mechanism that caused it.**

We need both, but we shouldn't confuse them.

## Three questions before the Deep Dive

1. Why does a rising memory graph not automatically establish that a JavaScript memory leak is the root cause?
2. Why might a supplier timeout and an open TCP connection legitimately coexist?
3. What makes a targeted comparison between two competing explanations more valuable than collecting dozens of unrelated dashboard metrics?

Keep one mental picture: a chain of system boundaries, each with its own state and guarantees. Our job is to locate the first broken contract and trace its consequences.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. Thursday, 09:00 — the deployment

Our hotel-booking platform operates a Node.js availability service running in Kubernetes.

The service receives customer searches and requests availability from external suppliers.

Each request can involve several concurrent supplier operations.

At 09:00, the team deploys a new supplier-client implementation.

The changes seem modest.

The client now uses a shorter timeout.

It introduces a revised retry policy.

It also records more detailed timing information.

For the first few minutes, everything appears healthy.

Then latency begins to rise.

At 09:08, the first cluster of HTTP 504 responses appears at the application gateway.

At 09:11, container memory usage begins climbing.

At 09:14, one worker restarts.

At 09:16, another begins reporting errors while opening outbound connections.

The incident dashboard contains contradictory-looking signals.

Host CPU utilization is around twenty percent.

PostgreSQL latency remains normal.

The Node.js managed heap appears relatively stable.

The supplier's public status page reports no incident.

But customers are struggling to search for hotels.

Someone suggests increasing the number of replicas.

Someone else suspects Kubernetes CPU throttling.

Another engineer blames garbage collection.

Before changing the system, we need a better account of what happened.

The following figures are illustrative evidence for our teaching incident, not measurements from a real production system.

## 2. Define the incident precisely

"The backend is slow" is not an adequate incident definition.

A better description is:

"Following the 09:00 supplier-client deployment, availability requests involving delayed supplier responses began experiencing elevated tail latency and timeouts. Open socket counts and container memory usage subsequently increased, followed by descriptor errors and worker restarts."

Notice what this description does.

It identifies the affected operation.

It specifies the time relationship to a deployment.

It distinguishes early request failures from later resource exhaustion.

And it does not prematurely claim that the deployment caused the problem.

We have a correlation and a timeline.

We still need a mechanism.

### Build competing hypotheses

At this stage, four possibilities deserve investigation.

First, the new client may perform expensive synchronous work on the event-loop thread.

Second, a supplier may genuinely be responding more slowly, causing otherwise healthy requests to exceed their deadlines.

Third, the revised timeout implementation may abandon requests without terminating their underlying operations.

Fourth, resource restrictions or contention may be delaying otherwise runnable work.

We don't need to investigate these with equal intensity forever.

We need observations that quickly distinguish them.

## 3. Preserve evidence without making the outage worse

An incident commander asks whether we should immediately restart the unhealthy pods.

That's a legitimate mitigation question.

But we should first preserve whatever evidence can be captured quickly and safely.

The deployment version and configuration.

The relevant request and error timeline.

Previous container termination reasons.

Open descriptor counts.

Socket-state distributions.

Runtime and container memory metrics.

CPU restrictions and throttling counters.

A representative request trace.

We don't need a perfect forensic snapshot before helping customers.

If the outage is severe, rollback or traffic diversion may take priority.

But evidence that costs little to collect can prevent hours of speculation afterward.

### The disappearing evidence problem

When a process terminates, its open descriptors are closed.

Its in-memory queues disappear.

Its live thread states disappear.

Its native allocations are released.

A newly started replacement process may look completely healthy.

That doesn't prove the previous process was healthy.

It means the old process's ephemeral state no longer exists.

In Kubernetes, previous-container logs and recorded termination status may remain available, but retention is not unlimited or guaranteed across every replacement scenario.

A production incident needs a deliberate evidence-retention strategy.

## 4. Follow one representative request

Let's investigate a customer search that takes five seconds and eventually times out.

The expected path is straightforward.

The request arrives at the Node.js service.

The handler validates the request.

The supplier client initiates an outbound connection or obtains one from its configured pool.

The service sends the supplier request.

The supplier replies.

The runtime processes the response.

The application produces an availability result.

The HTTP response is returned.

But our request doesn't complete normally.

Where does it stop?

### Measure boundaries, not just totals

We want timestamps or duration measurements for meaningful stages.

When the handler began.

When the supplier operation was initiated.

How long obtaining a connection took.

When the request was actually sent.

When the first response byte arrived, if it did.

When the supplier operation settled.

When the handler completed.

These measurements can distinguish connection-pool waiting from remote response latency and from callback-delivery delay.

But telemetry itself must be interpreted carefully.

An application timer measuring "supplier duration" may begin before a connection is acquired.

A tracing span might include local queueing.

A timeout may occur before any request bytes leave the process.

Labels such as "network latency" can therefore mislead if the measured interval isn't defined.

The useful question is: **what happened during the interval, and who was responsible for making progress?**

## 5. The first strong clue: file descriptors

At 09:12, an engineer notices that the Node.js process has an unusually large number of open file descriptors.

The count has increased steadily since the deployment.

At 09:16, the service begins logging `EMFILE`.

On Linux, `EMFILE` indicates that the process has reached its applicable limit for open file descriptors.

This is much more specific than "the API is slow."

It tells us that a process-level resource boundary has been reached.

It does not yet tell us why.

### What owns the descriptors?

The process might have many open files.

It might have numerous sockets.

It might retain pipes or other descriptor-backed resources.

We inspect the descriptor targets and socket information.

Most of the increase corresponds to outbound TCP sockets associated with supplier communication.

Now the hypothesis space narrows.

A growing count of supplier sockets could reflect legitimate traffic growth, a change in connection-pooling policy, slower requests remaining active longer, or connections not being released properly.

We need to distinguish these.

### `CLOSE_WAIT` is a particularly useful clue

Suppose several sockets are in `CLOSE_WAIT`.

In TCP, this state generally means the local TCP stack has received a FIN from the peer, but the local endpoint hasn't completed its own close.

A substantial, persistent accumulation can indicate that application-side connection cleanup isn't happening.

But don't treat every `CLOSE_WAIT` socket as proof of a leak.

Some connections may briefly pass through this state during normal shutdown.

We need persistence, scale, ownership, and the associated application behavior.

### Don't blame `TIME_WAIT` blindly

`TIME_WAIT` is different.

It is a normal part of TCP connection termination, generally associated with the endpoint performing the active close.

It can help prevent delayed packets from an earlier connection from being confused with a later connection using the same connection identity.

Large numbers of `TIME_WAIT` entries may matter for connection churn or certain resource limits.

But they are not automatically leaked open application file descriptors.

A TCP-state count and a process descriptor count describe different things.

The investigator must not treat them as interchangeable.

## 6. The code review: the timeout that canceled nothing

We inspect the new supplier client.

It opens a TLS connection and starts waiting for a response.

The application also creates a timer Promise that rejects after two seconds.

The implementation races the supplier operation against that timer.

When the timer wins, the caller receives a timeout error.

The request handler logs the failure and returns an error to the customer.

From the caller's perspective, the operation is finished.

But the underlying supplier request wasn't canceled.

The socket remains active.

A custom registry still holds its reference.

The operation may continue waiting for data, and associated resources remain retained.

### Why `Promise.race` doesn't cancel losers

`Promise.race` settles according to the first input Promise that settles.

It does not inherently stop the operations represented by the other Promises.

If the timeout rejects first, the aggregate rejects.

The underlying network request can continue.

The application may no longer care about its result, but the resource still has a lifetime.

In other words:

**Promise settlement is an application-level observation. Connection closure is a separate resource-management action.**

The kernel doesn't know that our high-level Promise returned a timeout error.

And the runtime doesn't automatically infer a universal cancellation policy for every operation involved in the race.

### A timeout wrapper isn't enough

A correct deadline implementation needs to decide what happens to underlying work.

For APIs supporting cancellation, an AbortSignal or equivalent mechanism can request that work stop.

For manually managed sockets, the code must use the appropriate resource-lifecycle operations.

For pooled connections, it must distinguish a reusable healthy connection from one that should be closed or discarded.

The caller, timeout, network operation, registry, listeners, and timers must have coherent ownership.

The bug in our teaching incident is not simply that a timer fired.

It's that the code treated the end of waiting as the end of the operation.

## 7. Why the supplier's latency matters—but isn't the root cause

Someone says, "The supplier was slow. That's why everything broke."

Let's test that explanation.

Suppose the supplier occasionally takes five seconds to respond.

Our application has a two-second deadline.

Timeouts are therefore expected under those conditions.

But why should a timeout permanently increase open socket count?

It shouldn't, if the client correctly handles the operation's resource lifetime.

A healthy implementation may cancel the request, close a disposable connection, or manage a pooled connection according to its documented semantics.

After the operation is properly completed or abandoned, its resources should no longer remain unintentionally retained.

The supplier's slow response is a **trigger**.

The failed cleanup is the **defect**.

The connection count rises because timed-out operations are not being properly released.

### A discriminating comparison

Imagine running two versions of the supplier client against the same controlled delayed-response server.

The previous version times out but releases the appropriate resources.

The new version times out and retains connections.

That difference strongly supports the cleanup hypothesis.

It is much more informative than merely observing that the supplier sometimes responds slowly.

The experiment holds the trigger approximately constant while changing the suspected implementation.

That's how causal investigations become stronger.

## 8. Retry amplification: when recovery becomes another failure

Now consider the revised retry policy.

A supplier request times out.

The application retries.

But the previous request may still be active at the transport level.

The retry starts another connection.

If that attempt also times out, the application may create yet another.

The system is accumulating unfinished work while generating new work.

This is retry amplification.

### A simple capacity illustration

Suppose one hundred customer searches per second each trigger one supplier operation.

If ten percent encounter timeouts and each timeout produces two additional attempts, the retry policy introduces extra request demand.

Under certain failure patterns, retries can increase dramatically as failures become more common.

The precise rate depends on retry rules, request durations, and how attempts overlap.

But the causal direction is clear.

The dependency becomes slow.

The application produces more attempts.

More attempts consume connection slots, buffers, memory, and supplier capacity.

Those additional demands can make the service even slower.

### Backoff isn't sufficient by itself

Exponential backoff with jitter can reduce synchronization and repeated load bursts.

That's useful.

But a retry policy also needs a maximum attempt budget, a deadline, and consideration of whether the operation is safe to retry.

A retry that begins while the previous attempt remains active can increase real concurrency.

If the operation has side effects, an ambiguous timeout creates business-correctness questions.

Our availability lookup is principally a read, but the same policy applied to payments could be dangerous.

Retry logic must account for operation identity, idempotency, and uncertainty.

### More attempts, less useful progress

During the incident, total outbound requests increase.

But successful availability results do not increase.

This distinction matters.

Higher request volume isn't necessarily higher useful throughput.

The service is performing more work while delivering fewer successful outcomes.

The retry mechanism has become a load amplifier.

## 9. The memory mystery

At 09:11, container memory begins rising.

The JavaScript heap dashboard looks comparatively stable.

An engineer concludes that the memory alert is unrelated to the socket problem.

That's too quick.

In CS320-L04, we established that V8 heap usage, process RSS, and cgroup memory charges are different measurements.

Open connections can involve native socket state, kernel buffers, JavaScript objects, listeners, TLS state, and other resources.

Pending operations can also retain application state.

The managed heap may grow, but it need not account for every additional byte.

### How retained work becomes memory demand

Imagine each abandoned operation retaining a connection wrapper and some request metadata.

Some operations also retain response buffers or closures.

The kernel maintains associated socket state while the connection remains active.

Meanwhile, retries create additional operations.

The number of unfinished objects and resources grows.

Our process's resident footprint can rise.

Cgroup charges can rise through several relevant memory categories.

Eventually, the workload may encounter reclaim pressure.

The system can become slower before it crashes.

### A stable heap isn't an acquittal

A flat `heapUsed` graph does not prove that no resource leak exists.

It only describes one portion of runtime memory under that metric's semantics.

Conversely, rising RSS does not automatically prove a JavaScript object leak.

Allocator retention, native allocations, file cache, and other causes are possible.

The appropriate investigation compares runtime memory, process RSS, cgroup usage, and relevant breakdowns without adding overlapping categories.

The objective is to identify which resources and allocations persist longer than intended.

### OOMKilled is a termination fact

Suppose the previous Kubernetes container status reports `OOMKilled`.

That tells us the process encountered an OOM-related termination condition under the platform's reported semantics.

It does not, by itself, identify the precise allocation or application bug.

The cgroup may have reached a hard memory boundary.

But the ultimate cause might be excessive legitimate concurrency, native allocation growth, cache pressure, or a leak.

In this incident, we have a plausible causal chain from abandoned operations to retained resources and rising memory.

We still want supporting timeline and reproduction evidence before declaring that chain established.

## 10. The CPU dashboard: an attractive distraction

Host CPU utilization is only twenty percent.

Can we rule out CPU-related delays?

No.

A single JavaScript thread might be saturated while other cores remain idle.

A container may have a restrictive CPU quota.

Threads might be runnable but waiting for CPU service.

Lock contention could delay work independently of overall host utilization.

So we check.

For our teaching incident, suppose the evidence shows:

The main event loop remains responsive during much of the supplier waiting.

There is no sustained increase in per-thread CPU execution matching the five-second request delays.

The container's CPU-throttling counters do not increase materially during the incident.

A controlled lightweight endpoint remains responsive while supplier operations accumulate.

These observations weaken the hypothesis that CPU scheduling or main-thread computation is the primary cause.

They don't prove CPU can never contribute.

They show that CPU is not currently the best explanation for the dominant symptom.

### What about the native worker pool?

We also consider libuv worker-pool saturation.

Certain asynchronous filesystem, cryptographic, and DNS-related operations can use native workers.

If those workers are occupied, pool-dependent operations can queue.

But the suspect supplier client primarily waits on network connections.

The evidence points toward retained transport operations and descriptor pressure rather than a saturated filesystem worker pool.

Again, the point is not to eliminate every conceivable contributing factor.

It's to identify which mechanisms are supported by actual observations.

## 11. Why thread states alone are insufficient

An engineer inspects the Node.js process and finds many sleeping threads.

"Everything is blocked!" she announces.

But sleeping threads are common in healthy systems.

A worker-pool thread may sleep waiting for a task.

An event-loop thread may wait for I/O readiness.

A thread may wait for a synchronization primitive.

The state alone doesn't tell us whether the wait is expected.

### Runnable versus blocked

A runnable thread has work ready but isn't necessarily receiving CPU service.

A blocked thread is waiting for some other condition.

The remedies differ.

If the thread is runnable but CPU-throttled, inspect its effective CPU budget.

If it is blocked on I/O, inspect the relevant I/O operation.

If it is waiting for a mutex, inspect lock ownership and contention.

A thread-state code is useful only when tied to a question about progress.

### A deadlock is another distinct possibility

Suppose two threads each hold a lock needed by the other.

That can create a deadlock.

But our supplier incident doesn't currently require a shared-memory deadlock to explain the evidence.

We have a more direct explanation: network operations remain active beyond their intended application lifetime.

We should not invent a lock problem merely because the course recently taught deadlocks.

Forensics is about using relevant knowledge, not displaying every concept we know.

## 12. The socket that outlived its request

Let's inspect the transport state more closely.

The application records:

"Supplier request timed out after 2000 milliseconds."

But the corresponding TCP connection remains present.

That is possible because the application and operating system maintain different kinds of state.

The application knows about request deadlines, Promises, and business operation identifiers.

The kernel knows about socket state, buffers, and transport-level events.

A Promise rejection doesn't automatically close a socket.

### Connection pooling complicates the picture

Not every socket that remains open after an HTTP request is leaked.

HTTP clients often maintain connection pools.

A healthy reusable connection may remain open intentionally so future requests can avoid establishing a new connection.

Therefore, finding an open socket after a request completes is not sufficient evidence of a leak.

We need to ask who owns it.

Is it part of a bounded pool?

Is it eligible for reuse?

Does it have a sensible idle lifetime?

Is there a configured maximum number of active and idle connections?

Is the corresponding request still active?

Can abandoned operations accumulate without bound?

A healthy connection pool has resource-lifetime rules.

Our custom registry does not.

### The dangerous registry

In the suspect implementation, each request creates an entry in a map of active connections.

The timeout branch rejects the caller's Promise but leaves the entry in the registry.

Because the registry retains the connection object, application-managed cleanup does not occur.

The connection may remain open, and the registry continues growing.

The exact native and kernel state depends on the transport library and peer behavior, but the architectural defect is clear.

The application has lost track of the difference between a request whose result is no longer wanted and a resource whose lifetime must still be managed.

## 13. The reproduction that settles the argument

At this point, we have a strong hypothesis.

But a credible root-cause analysis needs more than a plausible story.

We build a local supplier simulator.

It accepts connections and deliberately delays selected responses longer than the client's configured timeout.

We run the previous client implementation and the new one under comparable conditions.

### What should healthy behavior look like?

Suppose we initiate twenty supplier requests against the slow simulator.

The requests time out according to the application deadline.

The client performs its configured cancellation or cleanup actions.

Any intentionally reusable connections remain within a bounded pool.

Operation-specific registry entries disappear when their owners are finished.

After the workload becomes idle, resource usage returns to an appropriate bounded baseline.

Not necessarily exactly zero connections, because pooling may be intentional.

But there should be no unbounded accumulation associated with completed or abandoned operations.

### What does the defective version do?

The first request times out.

The caller receives an error.

The socket remains in the custom registry.

The second request behaves the same way.

After twenty timeouts, the registry contains twenty abandoned entries.

After fifty, it contains fifty.

The number of retained connections continues rising under repeated delayed responses.

Now we replace the faulty timeout behavior with cancellation and cleanup appropriate to the client's connection-lifecycle contract.

The same delayed-response workload produces timeouts, but the operation-specific resources no longer accumulate.

This comparison strongly supports the diagnosis.

### An important experimental qualification

We shouldn't blindly assume the entire incident has been reproduced merely because descriptor counts rose in a small test.

The production environment may have additional factors: TLS, connection reuse, retries, varying supplier latency, and container constraints.

But reproducing the suspected resource-lifetime defect and showing that the corrected implementation removes it is powerful causal evidence.

We can then validate the fix under representative production-like load.

## 14. The remediation has two parts

The immediate defect is connection cleanup.

But the severity of the incident also depended on uncontrolled demand.

A robust remediation should therefore address both the defective resource lifecycle and the system's ability to contain future slow dependencies.

### First: correct resource ownership

Every supplier operation needs a defined lifecycle.

What happens when it succeeds?

What happens when the supplier rejects it?

What happens when the local deadline expires?

What happens when the client disconnects?

What happens when the service shuts down?

The implementation should release or transfer ownership of resources appropriately in every path.

Where possible, use a mature HTTP client with documented pooling, timeout, and cancellation behavior rather than rebuilding transport lifecycle management.

If using a custom socket, cleanup must account for the actual connection state and ownership.

A `finally` block can be useful, but correct cleanup is more than mechanically calling `destroy()` on every socket.

A deliberately pooled healthy connection may need to be returned to the pool rather than destroyed.

The principle is explicit ownership and bounded lifetime.

### Second: bound work and retries

The application should limit concurrent supplier operations according to useful capacity.

It should bound waiting queues and memory retained by queued work.

Retries should have budgets, backoff, jitter where appropriate, and an overall deadline.

Repeated failures should not cause unlimited additional work.

And cancellation should propagate through task lifetimes, subject to each API's actual guarantees.

These changes make the system more resilient even if another supplier becomes slow tomorrow.

### Third: improve observability

The incident wasn't visible early enough because dashboards emphasized request latency, CPU, and managed heap usage.

We should also observe resource-lifetime indicators.

Relevant metrics include active supplier operations, queued operations, open descriptors, connection-pool usage, timeout and cancellation counts, retry amplification, memory charges, and per-operation duration.

The exact metric names aren't sacred.

What matters is that we can detect when application-level requests finish while underlying resources continue accumulating.

An effective alert should catch the system losing boundedness before it reaches a hard limit.

## 15. Why simply raising limits may make things worse

During the incident, three proposals sounded reasonable.

Raise the file-descriptor limit.

Raise the container memory limit.

Increase supplier timeouts.

Each might change the symptoms.

None necessarily fixes the defect.

### Raising the descriptor limit

If the process can open more descriptors, it may take longer to hit `EMFILE`.

That can buy operational time.

But if abandoned connections continue accumulating, the leak remains.

A larger limit may allow a larger accumulation before failure.

### Raising the memory limit

More memory may postpone the OOM condition.

It can be appropriate if the application genuinely needs additional capacity.

But if the problem is an unbounded set of abandoned operations, the higher limit merely allows more abandoned operations to survive.

### Increasing timeouts

Longer timeouts can reduce the fraction of responses classified as failures when suppliers are merely slow.

But they also allow in-flight work to live longer.

If the system lacks bounded concurrency, longer lifetimes may increase the number of active operations.

Under the relevant stable-system assumptions, Little's Law tells us that average in-flight work relates to throughput multiplied by average time in the system.

Longer request lifetimes can therefore increase resource demand even when arrival rates remain unchanged.

A timeout is a workload and policy decision, not a universal cure.

### The false comfort of restarting

Restarting the service closes its connections and releases process-local resources.

The incident appears resolved.

But if the defective code remains deployed, the same slow-response pattern can recreate the accumulation.

A restart can be a valid mitigation.

It is not proof of remediation.

## 16. Choosing measurements that distinguish causes

Let's gather the investigation into one practical framework.

Suppose we receive a new incident with rising latency and memory usage.

We should begin by identifying the competing explanations.

Then choose observations that best distinguish them.

| Hypothesis | Discriminating evidence |
|---|---|
| Main event loop blocked | Event-loop delay, synchronous-operation timing, unrelated endpoints delayed |
| CPU quota throttling | Effective quota, rising throttle counters, workload correlation |
| Native worker-pool saturation | Pool-dependent operations delayed while unrelated callbacks remain responsive |
| Memory pressure | Cgroup charges, reclaim events, PSI stalls, workload peaks |
| Socket or descriptor leak | Open descriptors or connections grow after operations should have ended |
| External dependency slow | Remote-operation timing corroborated independently, bounded local resource behavior |
| Shared-memory deadlock | Threads stuck in circular synchronization dependencies |

This table is for screen-based revision; during an actual investigation, we don't have to check every row.

We select plausible hypotheses according to the affected operation and the observed timeline.

### The information-gain principle

If we suspect that requests are waiting for CPU versus waiting for a supplier, measuring more aggregate host CPU may tell us very little.

A per-request trace and cgroup CPU statistics may be more informative.

If we suspect abandoned sockets versus a legitimate connection pool, collecting one connection count isn't enough.

We need to observe whether connection and registry counts return to a bounded baseline after work ends.

The most useful test is often the smallest one that separates two competing mechanisms.

## 17. The incident conclusion

We can now write a defensible explanation.

### Root cause

The revised supplier client treated an application-level timeout as completion of the overall operation.

It did not correctly release or otherwise manage the underlying transport resources and registry entries for abandoned requests.

Controlled delayed-response tests reproduced the accumulation and demonstrated that corrected resource-lifecycle handling removed it.

### Trigger

Supplier responses occasionally exceeded the application's two-second deadline.

That exposed the faulty timeout path.

Slow supplier responses alone would not have required unbounded local resource retention.

### Contributing factors

The implementation permitted too many concurrent supplier operations.

The retry policy could create additional attempts before earlier operations had actually stopped.

Resource telemetry did not detect the accumulating descriptors and unfinished operations early enough.

Hard process and container limits eventually converted the accumulation into connection failures and OOM-related restarts.

### Immediate mitigation

The team rolled back the defective supplier client or otherwise disabled the problematic behavior to reduce customer impact.

Affected instances could be restarted or drained where necessary.

Resource and error metrics were monitored while service recovered.

### Permanent remediation

The timeout implementation was replaced with correct cancellation and resource-lifecycle handling.

Concurrency and retry budgets were bounded.

Connection-pool behavior was made explicit.

Regression tests verified that repeated timeouts did not cause unbounded descriptor, registry, or memory growth.

Observability was expanded to detect accumulation before hard limits were reached.

This explains not only why the service failed, but why the failure escalated so severely.

## 18. The postmortem should teach the organization something

A useful postmortem is not simply a description of the faulty line of code.

It asks why the system allowed the defect to escape and amplify.

Why didn't tests catch it?

Because they verified that the timeout Promise rejected, not that the underlying operation released its resources.

Why didn't the monitoring system detect it early?

Because it measured request outcomes without adequately measuring resource lifetimes.

Why did retries make things worse?

Because the retry policy increased outstanding work during conditions that were already straining resource capacity.

Why did memory grow?

Because operations and related resources remained retained, while new attempts continued accumulating.

Why did containers restart?

Because their enforced memory boundaries could no longer satisfy the charged demand under the observed conditions.

Why was the supplier blamed first?

Because slow supplier responses were the visible trigger, even though the application's cleanup defect was the mechanism that turned routine slow responses into an escalating local failure.

### Avoid false certainty

Not every production incident provides perfectly complete evidence.

Perhaps the original container was already destroyed.

Perhaps some metrics were sampled too slowly.

Perhaps the reproduction covers only one of several contributing mechanisms.

A credible postmortem distinguishes established facts from strong inferences and unresolved uncertainties.

It doesn't manufacture certainty for the sake of a neat story.

The purpose is to improve future engineering decisions, not to produce a courtroom confession from the logs.

## 19. From incident response to engineering judgment

We've now used nearly every major mechanism from CS320.

We reasoned about processes and their resource limits.

We considered CPU scheduling and event-loop execution.

We distinguished runtime memory from cgroup memory.

We inspected file descriptors and socket states.

We examined asynchronous I/O and the lifetime of native resources.

We traced how cancellation and retries interact with unfinished work.

And we considered whether synchronization or deadlocks could explain the observed delays.

The important skill wasn't reciting those concepts.

It was deciding which concept mattered at each stage of the investigation.

A strong engineer can move between abstraction layers without confusing them.

When the application says "timeout," ask whether the network operation stopped.

When Linux says "EMFILE," ask which resource owners created and retained descriptors.

When Kubernetes says "OOMKilled," ask what memory was charged and what workload caused the growth.

When the dashboard says "low CPU," ask whether the relevant execution thread was actually receiving CPU service.

The kernel, runtime, and application each tell part of the story.

Our job is to reconstruct how those parts interact.

---

# The Oral Examination

Treat these as senior engineering interview questions. For each, explain what is known, what remains uncertain, and which evidence you'd collect next.

**Question 1 — The healthy CPU dashboard**

A sixteen-logical-CPU host shows approximately six percent utilization. One API endpoint is CPU-bound. Does the host metric rule out a CPU bottleneck? How would you distinguish a saturated main thread from CPU-quota throttling?

**Question 2 — The invisible memory**

A Node.js process is OOM-killed. Its latest `heapUsed` value was 110 MiB, while the container limit was 512 MiB. Name plausible explanations and the metrics you'd inspect next.

**Question 3 — The descriptor explosion**

A process reports `EMFILE`, and outbound TCP socket counts have been rising. Why isn't increasing `ulimit -n` a complete solution? What would you examine to distinguish legitimate concurrency from a leak?

**Question 4 — The TCP-state trap**

You observe many `TIME_WAIT` connections and a smaller number of persistent `CLOSE_WAIT` sockets. What does each state suggest, and why shouldn't they be interpreted identically?

**Question 5 — Two kinds of slow operations**

A synchronous report-reading endpoint delays every other endpoint. Later, after converting it to asynchronous filesystem I/O, only pool-dependent operations remain slow. Explain the two different execution bottlenecks.

**Question 6 — The timeout that didn't cancel**

A client uses `Promise.race` to reject after two seconds, but the underlying fetch or custom socket operation remains active. What guarantee was missing? What additional lifecycle actions might be required?

**Question 7 — The retry storm**

A dependency becomes slow, and your service increases retry attempts. Successful throughput falls while outbound requests and memory usage increase. Explain the feedback mechanism and propose containment.

**Question 8 — The suspicious deployment**

Latency begins increasing eight minutes after a deployment, and descriptor exhaustion appears later. Does this establish that the deployment caused the incident? What experiment would strengthen the causal conclusion?

**Question 9 — The restart that fixed everything**

Restarting all pods returns latency and memory usage to normal. What did the restart establish? What did it fail to establish?

**Question 10 — The incident report**

Give a concise incident conclusion distinguishing root cause, trigger, contributing factors, mitigation, and permanent remediation for the supplier-client failure.

---

# Solutions and Discussion

## Solution 1 — The denominator matters

No. One fully occupied logical CPU on a sixteen-logical-CPU host can appear as approximately 6.25 percent aggregate utilization under simple normalization.

Inspect per-thread CPU usage and the application's critical path. For throttling, inspect the relevant cgroup quota and changes in CPU-throttling counters. A saturated single execution lane and a bandwidth-limited container are different mechanisms.

## Solution 2 — Heap and container memory are different

The V8 heap is only part of process memory. Native allocations, Buffers, stacks, mapped pages, and other resident memory may contribute to RSS. Cgroup accounting can additionally include relevant file cache and kernel charges.

Inspect Node.js memory categories, process RSS, cgroup usage, `memory.stat`, and `memory.events`. Correlate changes with workload activity. Don't add overlapping metrics.

## Solution 3 — Find the owner of the descriptors

Raising the limit may postpone failure without addressing unbounded accumulation.

Inspect descriptor targets, socket counts, process limits, connection-pool policy, registry entries, and cleanup paths. Determine whether resource counts return to a bounded baseline once operations complete or time out.

## Solution 4 — Different TCP lifecycle states

`TIME_WAIT` is a normal connection-termination state commonly associated with active close behavior. It doesn't automatically represent an open application descriptor leak.

`CLOSE_WAIT` indicates that the local TCP stack has received the peer's FIN while the local side hasn't completed its close. Persistent accumulation can suggest missing application cleanup, but requires investigation in context.

## Solution 5 — Main-thread versus native-pool waiting

A synchronous operation on the main event-loop thread prevents unrelated JavaScript callbacks from executing promptly.

A saturated native worker pool can delay pool-dependent tasks while leaving the main event-loop thread available.

Distinguish the cases using endpoint scope, event-loop measurements, task timing, and resource evidence.

## Solution 6 — Promise settlement isn't resource cancellation

`Promise.race` chooses the aggregate outcome but doesn't automatically cancel losing operations.

The underlying API must support and receive appropriate cancellation or cleanup. Custom sockets may need explicit lifecycle handling. Pooled connections need a correct reuse or discard policy.

Timeouts don't guarantee that lower-level work stopped instantaneously.

## Solution 7 — Retry amplification

Slow operations remain active longer while retries create additional attempts.

This increases concurrency, descriptor demand, memory retention, and downstream load.

Bound active operations and queues, enforce retry budgets and deadlines, use appropriate backoff, and avoid overlapping retries where they cannot be safely supported.

## Solution 8 — Correlation needs a discriminating test

The deployment's timing supports suspicion but doesn't prove causation.

Compare old and new client implementations under the same controlled delayed-response workload. Measure connection and registry lifetimes, timeouts, and resource usage.

If only the new implementation accumulates abandoned resources, the causal hypothesis becomes much stronger.

## Solution 9 — Restart is mitigation evidence

The restart shows that resetting process-local state and resources improved service.

It doesn't establish which resource was defective or whether the same problem will recur.

The deployed code, workload, and resource-lifecycle policy must still be investigated.

## Solution 10 — A complete causal explanation

The root cause was a timeout path that failed to release owned transport resources and registry entries.

Slow supplier responses triggered the faulty path.

Unbounded concurrency, retry amplification, and insufficient resource-lifetime monitoring contributed to escalation.

Rollback or restarting affected instances mitigated impact.

Correct cancellation, bounded work, regression testing, and better observability provided permanent remediation.

---

# The Mental Model Worth Keeping

A production incident is a sequence of events across systems that obey different contracts.

The operating system provides execution time, memory, descriptors, sockets, and enforced resource limits.

The runtime coordinates callbacks, Promises, native operations, workers, and memory management.

The application adds deadlines, retries, resource ownership, and business meaning.

When something fails, use five questions:

**Observe:** What happened, precisely, and when?

**Hypothesize:** Which mechanisms could produce it?

**Discriminate:** What measurement or experiment separates those explanations?

**Verify:** Does the evidence support the proposed mechanism under controlled conditions?

**Remediate:** Does the change remove the failure mode and prevent its amplification?

The investigator's most important skill is not knowing every diagnostic command.

It is knowing which uncertainty to eliminate next.

# End of CS320 — From Mechanisms to Engineering Judgment

We've worked from the operating system's execution environment through scheduling, virtual memory, memory pressure, I/O, application concurrency, and shared-memory synchronization.

You now have a model of the machinery beneath a modern backend service.

But a model becomes useful only when you can apply it without following a prepared script.

When an interviewer describes a slow API, don't immediately blame the database.

When someone reports low CPU utilization, don't assume execution capacity is abundant.

When a Promise rejects, don't assume the underlying operation stopped.

When a process is OOM-killed, don't assume the JavaScript heap leaked.

And when an incident produces five alarming symptoms, don't assume you have five independent problems.

Find the boundary. Establish the evidence. Explain the mechanism.

That's the difference between recognizing terminology and understanding the system.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Lab — Build an Incident Room

These experiments are intended for a disposable local environment. Do not intentionally exhaust file descriptors, memory, or network resources on production machines.

## Lab A — Capture the process boundary

On Linux, inspect a process you control:

```bash
PID=$$

ps -o pid,ppid,stat,psr,pcpu,comm -p "$PID"
grep -E 'Threads|VmRSS|VmSize|FDSize' /proc/"$PID"/status
ls -l /proc/"$PID"/fd | head -30
```

Observe process identity, thread count, memory statistics, and file descriptors.

**Question:** Which of these measurements describes the process's resource environment rather than its business logic?

## Lab B — Inspect socket state

On a Linux system with `ss` available:

```bash
ss -tan
ss -tan state established
ss -tan state close-wait
ss -tan state time-wait
```

Use `ss -tanp` where permitted to inspect process associations.

Compare the TCP states.

Remember that socket-table entries and process-owned file descriptors aren't interchangeable measurements.

**Question:** Why might a server with many legitimate short-lived connections have substantial `TIME_WAIT` activity without leaking application file descriptors?

## Lab C — Reproduce a timeout that leaves work alive

This example uses the Node.js TCP module to create a small, local, intentionally faulty client. It doesn't contact external services or create an unbounded number of sockets.

Create `timeout-leak.mjs`:

```javascript
import net from "node:net";
import { setTimeout as delay } from "node:timers/promises";

const active = new Map();
let nextId = 0;

// A local server that accepts connections but doesn't reply.
const server = net.createServer(() => {});

await new Promise(resolve => {
  server.listen(0, "127.0.0.1", resolve);
});

const port = server.address().port;

async function badRequest() {
  const id = ++nextId;
  const socket = net.createConnection({
    host: "127.0.0.1",
    port
  });

  active.set(id, socket);

  // Avoid an unhandled error crashing this teaching example.
  socket.on("error", () => {});

  // This simulates an application deadline.
  const neverCompletes = new Promise(() => {});

  try {
    await Promise.race([
      neverCompletes,
      delay(30).then(() => {
        throw new Error("Application timeout");
      })
    ]);
  } catch {
    // BUG: the caller finishes, but the socket remains owned.
  }
}

for (let i = 0; i < 12; i++) {
  await badRequest();
}

console.log("Abandoned registry entries:", active.size);
console.log("Open client sockets:", [...active.values()]
  .filter(socket => !socket.destroyed).length);

// Cleanup so the demonstration exits safely.
for (const socket of active.values()) {
  socket.destroy();
}

active.clear();
server.close();
```

Run:

```bash
node timeout-leak.mjs
```

The script deliberately retains twelve client socket objects after the application-level timeouts. The exact connection state may vary with scheduling, but the unbounded-lifetime pattern is visible in the registry.

**Question:** Which event ended the caller's wait, and which event actually ended the socket's lifetime?

## Lab D — Correct the resource lifecycle

Modify the previous example so each request owns its socket and performs cleanup when the deadline expires.

One useful pattern is to attach the resource to an explicit operation object and ensure that timeout or cancellation closes the owned disposable socket.

For a reusable HTTP client connection, use the client's documented cancellation and pooling semantics rather than always destroying every socket.

After repeating the delayed-response experiment, verify that the number of abandoned operation-specific resources doesn't grow with the number of completed timeouts.

**Success criterion:** repeated timeouts do not cause the registry and open resources to grow indefinitely.

## Lab E — Distinguish the runtime and container memory views

For a Node.js process, log:

```javascript
console.log(process.memoryUsage());
```

On Linux, compare with:

```bash
cat /proc/self/status
```

In a suitable cgroup v2 environment, inspect:

```bash
cat /sys/fs/cgroup/memory.current
cat /sys/fs/cgroup/memory.stat
cat /sys/fs/cgroup/memory.events
cat /sys/fs/cgroup/memory.max
```

The files visible inside a container may reflect a cgroup namespace or mount arrangement. Use the correct host-side cgroup path when needed.

**Question:** Why might `heapUsed`, RSS, and `memory.current` all report substantially different values?

## Lab F — Check CPU restrictions and pressure

Where available:

```bash
cat /sys/fs/cgroup/cpu.max
cat /sys/fs/cgroup/cpu.stat
cat /proc/pressure/cpu
cat /proc/pressure/memory
```

These interfaces describe different things.

CPU quota and throttling are not the same as host CPU utilization.

Memory pressure describes stalled progress, not merely the percentage of RAM occupied.

**Question:** What measurements would distinguish a process waiting for CPU service from one waiting for a supplier response?

## Lab G — Preserve Kubernetes incident evidence

In a disposable development cluster, inspect a workload:

```bash
kubectl describe pod <pod-name> -n <namespace>

kubectl logs <pod-name> \
  -n <namespace> \
  --previous \
  --container <container-name>
```

Inspect resource limits, restart counts, previous termination reasons, and events.

Do not assume previous logs always remain available after multiple replacements or Pod deletion.

**Question:** Why is an `OOMKilled` status important evidence but not a complete root-cause explanation?

## Lab H — Construct a causal timeline

Consider this hypothetical evidence:

```text
09:00  Supplier-client deployment completed
09:04  Supplier timeout rate begins rising
09:07  Active connection registry begins growing
09:08  Availability p95 latency increases
09:11  Process RSS and cgroup memory increase
09:13  Open descriptors approach process limit
09:14  First worker restarted; OOMKilled recorded
09:16  Other workers report EMFILE
09:18  Rollback initiated
09:23  Error rate falls
09:30  New instances maintain stable descriptor counts
```

Prepare a timeline distinguishing:

- Observation versus proposed explanation.
- Trigger versus root cause.
- Direct consequence versus contributing amplifier.
- Mitigation versus verified permanent remediation.

Then identify which evidence would most strongly test the claim that timeout cleanup was the first broken application contract.

## Lab I — Write the postmortem

Produce a short incident report with the following sections:

1. Customer impact and duration.
2. Technical timeline.
3. Root cause and supporting evidence.
4. Trigger and contributing factors.
5. Immediate mitigation.
6. Permanent corrective actions.
7. Verification and regression tests.
8. Unresolved questions and confidence levels.

Avoid blaming individual developers.

Focus on what the system allowed, what assumptions failed, and what changes will prevent recurrence.

---

# Further Reading

Authoritative technical references:

1. Node.js — Don't Block the Event Loop (or the Worker Pool)  
   https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop

2. Node.js — Process Memory Usage  
   https://nodejs.org/api/process.html#processmemoryusage

3. MDN — `Promise.race()`  
   https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/race

4. Linux Manual Pages — `proc_pid_fd(5)`  
   https://man7.org/linux/man-pages/man5/proc_pid_fd.5.html

5. Linux Manual Pages — `tcp(7)`  
   https://man7.org/linux/man-pages/man7/tcp.7.html

6. Linux Kernel Documentation — Control Group v2  
   https://docs.kernel.org/admin-guide/cgroup-v2.html

7. Linux Kernel Documentation — Pressure Stall Information  
   https://docs.kernel.org/accounting/psi.html

8. Kubernetes — Debug Running Pods  
   https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/

9. Google SRE Book — Postmortem Culture  
   https://sre.google/sre-book/postmortem-culture/

Related programme chapters:

- CS320-L01 — The Kernel, Processes, and Containers
- CS320-L02 — CPU Scheduling, Quotas, and Contention
- CS320-L03 — Virtual Memory, Pages, and Address Translation
- CS320-L04 — Memory Pressure, Cgroups, and OOM
- CS320-L05 — System Calls, File Descriptors, and Asynchronous I/O
- CS320-L06 — Concurrency, Event Loops, and Cancellation
- CS320-L07 — Threads, Atomics, and Memory Ordering
- SE440-L02 — Reliability Engineering and Incident Response

---

## Dense Cheatsheet — Interview Glance Card

```text
CS320-L08 — OPERATING-SYSTEM AND RUNTIME FORENSICS

THE FIVE-STEP METHOD
  OBSERVE       What happened, where, and when?
  HYPOTHESIZE   Which mechanisms could explain it?
  DISCRIMINATE  Which measurement separates hypotheses?
  VERIFY        Reproduce or otherwise confirm mechanism
  REMEDIATE     Fix failure mode; verify under representative load

EVIDENCE LEVELS
  Observation       measured event or state
  Hypothesis        plausible explanation
  Mechanism         how system produces the symptom
  Causal evidence   supports mechanism under relevant conditions
  Root cause        underlying defect or broken contract
  Trigger           circumstance that exposes the defect
  Contributor       factor increasing likelihood/severity
  Mitigation        reduces current customer impact
  Remediation       prevents or contains recurrence

INCIDENT PATTERN
  Slow supplier response
    -> application timeout
    -> Promise rejects
    -> underlying socket stays alive
    -> registry retains connection
    -> retry creates more work
    -> descriptors and memory grow
    -> EMFILE / pressure / OOM possible

TIMEOUT TRAP
  Promise.race timeout != cancellation of losing operation
  Local deadline != remote failure
  Abandoned result != abandoned socket
  Correct lifetime requires ownership + cleanup
  Reusable pooled connection != automatically a leak

FILE DESCRIPTORS
  fd = process-local resource handle
  EMFILE = process open-descriptor limit
  ENFILE = system-wide open-file-table limit
  Count and inspect descriptors; find ownership
  Raising limit != fixing unbounded resource retention

TCP STATES
  ESTABLISHED   connection established
  CLOSE_WAIT    peer FIN received, local side not finished closing
  TIME_WAIT     normal connection-termination protection state
  CLOSE_WAIT accumulation may indicate missing cleanup
  TIME_WAIT count != count of leaked process descriptors
  Always compare state distribution with process fd ownership

RUNTIME BOUNDARIES
  Kernel socket state
  Native I/O operation
  Runtime callback / Promise state
  Application request / business operation
  One finishing does not force all others to finish

CPU FORENSICS
  Host utilization != per-thread CPU service
  CPU time != wall time
  Runnable waiting != blocked waiting
  Cgroup quota can throttle on idle host
  Event-loop delay may have several causes
  Inspect per-thread CPU and cpu.stat

MEMORY FORENSICS
  heapUsed != process RSS != cgroup memory.current
  arrayBuffers included in external (Node.js)
  RSS includes native/stacks/mappings
  Cgroup charges also include relevant file/kernel memory
  memory.stat helps explain charge composition
  memory.events distinguishes limit pressure/OOM kills
  OOMKilled = termination evidence, not full root cause

I/O FORENSICS
  Network readiness != callback execution
  Socket data can arrive while main JS thread blocked
  Async filesystem work may use finite native worker pool
  Pool saturation != event-loop blockage
  Look at actual operation timing and queues

CONCURRENCY FORENSICS
  More retries may produce less successful throughput
  Bound active operations AND waiting queues
  Scope limits across all replicas
  Cancellation needs propagation and cleanup
  A timed-out operation may still be active
  A retry may overlap with its predecessor

THREADS / LOCKS
  Sleeping thread != necessarily unhealthy
  Runnable thread != currently executing
  Lock wait != CPU-queue wait
  Deadlock requires dependency analysis
  No evidence of shared-memory deadlock? Don't invent one

CAUSAL INVESTIGATION
  Trace one representative slow request
  Preserve previous container evidence before reset
  Compare before/after deployment
  Test old/new client under identical slow-supplier trigger
  Inspect whether resource counts return to bounded baseline
  Use minimal reversible experiments

BAD FIRST FIXES
  Raise FD limit without finding resource lifetime
  Raise memory limit without identifying working set
  Add retries while dependency is overloaded
  Increase timeout without bounding in-flight work
  Add replicas without assessing global dependency demand
  Restart repeatedly and call it root-cause resolution

POSTMORTEM
  State impact and timeline
  Show evidence supporting root cause
  Separate trigger/contributors
  Explain why defenses didn't contain failure
  Name immediate mitigation
  Define permanent corrective actions
  Include regression tests and verification
  Acknowledge remaining uncertainty

SENIOR INTERVIEW ANSWER
  "I'd reconstruct the request and resource timeline, identify
   plausible execution boundaries, select measurements that
   distinguish them, and validate the first broken contract
   before making capacity or architectural changes. I'd also
   separate mitigation from remediation and verify that the
   underlying resource-lifetime and overload behavior is fixed."

DURABLE MENTAL MODEL
  Follow the resource.
  Find the first broken contract.
  Prove the causal chain.
  Fix the mechanism, not only the symptom.
```
