---
id: SE335-L03
course: SE335
title: "The Asynchronous System Incident Studio"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE335-L02
next: null
---


# SE335 — Queues, Caches, and Worker Production Diagnostics
## Lecture 03: The Asynchronous System Incident Studio

*Redis reports 99% cache hits. RabbitMQ reports enormous delivery activity. The worker fleet has quadrupled. Database connections are exhausted. Somehow, the system completes fewer jobs than before.*

---

# Part I — Intuition

## 1. The Incident Where Every Dashboard Told a Different Story

It's Thursday afternoon at a SaaS company operating a large asset-discovery platform.

Customers submit domains, configure scans, and request reports. The backend uses Redis to cache frequently requested information, RabbitMQ to distribute background work, and MongoDB to store results.

At 14:00, the operations dashboard looks healthy.

At 14:12, API latency begins climbing.

At 14:15, RabbitMQ's ready queue contains thousands of jobs.

The operations team scales the worker deployment from eight instances to thirty-two.

At 14:18, MongoDB connection utilization reaches its limit.

At 14:20, worker logs fill with timeouts.

At 14:22, RabbitMQ redelivery activity spikes.

Redis continues reporting a global hit ratio close to 99%.

The database team blames the workers.

The worker team blames the database.

The application team points out that Redis appears healthy.

The infrastructure team proposes increasing resource limits.

Every team is looking at a real symptom.

Nobody has yet established the sequence of causes.

This is where production incident diagnosis becomes fundamentally different from debugging an isolated function.

You don't merely need to find something that's wrong.

You need to understand **how one failure changes the workload experienced by other components**.

## 2. The First Failure Wasn't Where the Outage Became Visible

Imagine discovering that a recent release changed the Redis key used for customer report summaries.

Previously, the application cached a report under a key determined by tenant, report type, filters, and data version.

Repeated requests for the same report could reuse one computed result.

The new release accidentally included the unique request ID in the cache key.

Every request now generated a different key.

Even when two requests asked for exactly the same report, they could no longer share the cached value.

The cache didn't disappear.

Redis didn't crash.

The application continued using `GET` and `SET`.

But the effective cache hit rate for the expensive report workflow collapsed.

The global Redis hit rate remained excellent because inexpensive configuration lookups dominated the aggregate statistics.

This is the initiating failure.

Everything else followed from the additional backend work.

### Visual anchor 1 — The initiating defect

```text
BEFORE RELEASE

Request A ──┐
Request B ──┼──► report:mercury:quarterly:v1
Request C ──┘          |
                       v
                  Shared result


AFTER RELEASE

Request A ──► report:mercury:quarterly:v1:req-A
Request B ──► report:mercury:quarterly:v1:req-B
Request C ──► report:mercury:quarterly:v1:req-C

Three equivalent requests.
Three different cache identities.
```

The database doesn't know that the cache key is wrong.

It merely receives additional computation requests.

RabbitMQ doesn't know that the work is redundant.

It merely distributes more jobs.

The workers don't know that the database is approaching saturation.

They attempt the jobs they've been given.

Each component behaves according to its local rules.

The resulting system behaves badly.

## 3. The Queue Didn't Create the Work

When report-cache misses increased, the application began publishing additional report-generation jobs to RabbitMQ.

The queue grew.

That was the first highly visible operational symptom.

But the queue wasn't necessarily the source of the increased workload.

It was where the additional demand accumulated.

Think of a highway accident.

Traffic jams appear several kilometers behind the accident.

The vehicles in the traffic jam aren't the original cause.

Adding more entrance ramps behind the blockage doesn't clear the highway.

A queue similarly reveals a mismatch between arriving work and completed work.

It does not automatically explain why the mismatch began.

If arrivals increase from twenty jobs per second to eighty while the downstream processing system can sustain only forty, the backlog grows.

The queue buffers the difference.

It cannot manufacture additional database capacity.

## 4. More Workers Moved the Backlog

The operations team saw thousands of ready messages.

It increased the number of workers.

RabbitMQ delivered more messages.

The ready count began falling.

For a moment, this looked like recovery.

But unacknowledged messages increased.

Many workers were waiting for MongoDB connections.

The queue had moved from RabbitMQ's ready state into consumer processes and database connection-pool waits.

### Visual anchor 2 — A backlog can move without shrinking

```text
BEFORE SCALING

RabbitMQ ready:       8,000
Worker in-flight:       100
Database waiting:        20


AFTER SCALING

RabbitMQ ready:       6,500
Worker in-flight:     1,400
Database waiting:     1,100

The visible ready count fell.

The unfinished work didn't
necessarily fall.
```

These numbers are illustrative.

The point is that a system can improve one metric by moving work into another waiting area.

**A falling queue-ready count is not proof of increased successful throughput.**

The definitive question is how many business operations actually complete.

## 5. Retries Turned Overload into an Amplifier

Now the database begins rejecting or timing out operations.

The worker code treats all failures as transient.

On failure, it immediately negatively acknowledges the message with requeue enabled.

RabbitMQ makes the message available again.

Another worker receives it.

The database is still overloaded.

The request fails again.

The worker requeues again.

The system now has two sources of work.

New jobs arrive from customers.

Old jobs repeatedly return after failing.

The attempted workload may become much larger than the original arrival rate.

### Visual anchor 3 — The feedback loop

```text
Cache misses increase
         |
         v
More jobs published
         |
         v
More worker requests
         |
         v
Database saturation
         |
         v
Timeouts and rejections
         |
         v
Immediate requeues
         |
         v
More worker requests
         |
         +──────► feedback loop
```

This is a positive feedback loop.

One subsystem's degradation creates behavior that further degrades it.

The retry mechanism intended to provide reliability becomes an outage amplifier.

The system can produce enormous delivery rates while useful completion rates collapse.

## 6. The Difference Between a Trigger and an Amplifier

The bad cache-key change initiated additional work.

That is the trigger.

Worker scaling increased simultaneous pressure on the database.

That is one amplifier.

Immediate RabbitMQ requeues generated repeated attempts.

That is another amplifier.

Database connection saturation is an observed bottleneck.

Growing queue depth is a symptom of unfinished work.

These distinctions are important because different interventions act at different points.

Reverting the cache-key change prevents much of the redundant future work.

Reducing concurrency limits pressure on the database.

Changing retry behavior prevents failures from immediately generating additional load.

Adding database capacity may increase the system's sustainable throughput.

But increasing database capacity alone doesn't eliminate the redundant work caused by the cache-key defect.

Likewise, repairing the cache key doesn't automatically make the existing retry storm stop immediately.

Incident response often requires **containment first, durable correction second**.

## 7. Contain the Incident Without Making It Worse

Imagine that you're the engineer coordinating the response.

You have several possible actions.

You could add workers.

You could increase RabbitMQ prefetch.

You could increase database connection limits.

You could temporarily reduce worker concurrency.

You could stop immediate requeues.

You could restore the previous cache-key behavior.

You could temporarily limit new report-generation requests.

Which should happen first?

The answer depends on evidence, but the general priority is clear.

Prevent the system from amplifying its own failure.

If database saturation is causing repeated retries, reducing concurrency and interrupting the retry storm can stabilize the situation.

Once the system stops getting worse, you can restore correct cache behavior and drain legitimate work at a sustainable rate.

You should also preserve failed jobs appropriately rather than silently deleting important customer requests.

Recovery is not simply making the dashboards green.

It is restoring useful service without losing or corrupting work.

## 8. The Diagnostic Habit Worth Developing

Cross-service incidents reward engineers who can reason in terms of rates, dependencies, and causality.

How many distinct business requests arrive?

How many jobs are published?

How many delivery attempts occur?

How many database operations are attempted?

How many succeed?

How many fail?

How much work is waiting at each boundary?

These numbers reconstruct the incident.

A Redis hit ratio without workload segmentation is incomplete.

A RabbitMQ delivery rate without acknowledgments is incomplete.

A database connection count without pool waiting and successful operation rate is incomplete.

And a CPU graph without knowledge of the actual bottleneck can be misleading.

### A tiny comprehension check

Suppose incoming customer requests remain constant at fifty per second.

After a release, database attempts rise from twenty per second to two hundred.

Can we conclude that customer demand increased?

No.

The extra attempts may come from cache misses, duplicate work, retries, or other application behavior.

Now suppose reducing workers from thirty-two to eight improves completed jobs per second.

Is that impossible?

No.

If the larger fleet overloaded a downstream dependency, reducing concurrency may reduce failures and improve useful throughput.

That's the central lesson of the studio.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 9. Diagnose the System as a Dependency Graph

An isolated component can be analyzed through its inputs, state, and outputs.

A distributed workflow needs a broader model.

For our SaaS platform, imagine the following path:

An API receives a report request.

The application checks Redis for an existing report.

On a cache miss, it may publish background work to RabbitMQ.

A worker receives the message.

The worker performs report computation against MongoDB.

The completed result is cached in Redis.

The worker acknowledges the message.

The API eventually returns or exposes the report.

Each boundary can introduce latency, duplication, loss, or backpressure.

### 9.1 The essential distinctions

A Redis lookup is not the same as a database operation.

A published RabbitMQ message is not the same as a completed report.

A delivered message is not the same as an acknowledged message.

An acknowledged message is not automatically evidence that every external business effect was correct.

A database query attempt is not necessarily a successful query.

A successful database operation doesn't necessarily imply the caller received confirmation.

These distinctions prevent us from using convenient but misleading metrics.

## 10. Construct a Causal Timeline

A production incident often produces many simultaneous alerts.

To understand it, establish ordering.

For our case:

At 14:00, the system was stable.

At 14:08, a new application version began deploying.

At 14:12, expensive report-cache misses increased.

At 14:15, RabbitMQ backlog began growing.

At 14:16, workers were scaled out.

At 14:18, database pool saturation increased sharply.

At 14:20, worker timeouts and immediate requeues multiplied.

At 14:22, successful completion throughput declined.

This timeline suggests a causal sequence.

But temporal correlation isn't proof.

The investigation must test whether the cache-key change actually increased unique key cardinality and database loads.

It must confirm whether worker scaling preceded additional saturation.

It must establish whether redeliveries rose because of transient failures.

Only then does the timeline become an evidence-backed explanation.

### 10.1 Why timestamps need care

Logs from different machines may have clock skew.

Metric collection intervals may not align.

A dashboard may aggregate events into one-minute buckets, obscuring exact ordering.

Use trace identifiers, structured events, deployment timestamps, and consistent time references when possible.

A causal explanation must not depend on pretending that monitoring has perfect temporal precision.

## 11. Separate External Demand from Internal Attempts

One of the most useful incident measurements is the distinction between new business work and repeated execution attempts.

Suppose the platform receives 100 unique report requests.

Those requests result in 100 RabbitMQ jobs.

Each job should normally produce one successful report.

But database timeouts cause messages to be requeued repeatedly.

The system might perform 300 database attempts before completing the original 100 jobs.

The customer-demand rate hasn't tripled.

The internal-attempt rate has.

### 11.1 Amplification ratio

A useful diagnostic ratio is:

**Database attempts divided by unique business jobs.**

For example, 300 database attempts for 100 unique jobs gives an amplification ratio of three.

This metric must be interpreted carefully.

A legitimate workflow may require several database operations per job.

Therefore, define the expected baseline for the operation.

The useful comparison is whether attempts per logical job increased unexpectedly.

### 11.2 Delivery attempts are not unique messages

RabbitMQ may deliver the same message repeatedly.

A high delivery rate can reflect successful work distribution, retries, or both.

Track unique job IDs and redelivery behavior wherever practical.

A dashboard reporting 5,000 deliveries per second could describe a healthy system or a poison-message storm.

The distinction requires completion and failure metrics.

## 12. The Cache-Key Cardinality Failure

Return to the Redis defect.

The intended report-cache identity is determined by inputs that affect the result.

For example:

Tenant.

Report type.

Time range.

Relevant filters.

Authorization scope.

Data version.

The request ID does not affect the report's contents.

Including it creates unnecessarily distinct cache entries.

### 12.1 A cache key is a statement about equivalence

When two requests use the same cache key, the application claims that the same cached value can safely satisfy both requests.

When they use different keys, the cache treats the values as independent.

A correct key must distinguish requests whose results can differ.

But it should avoid distinguishing requests that produce the same reusable result.

This is a correctness and performance boundary.

### 12.2 Cache-key under-specification is also dangerous

Removing too many key dimensions is not safe.

If two tenants share a key for private report data, one tenant may receive another tenant's information.

If the report depends on date filters but the key ignores them, users may receive incorrect results.

Therefore, the correction is not simply making keys shorter.

It is modeling the actual identity of the result.

### 12.3 High-cardinality keys destroy reuse

A request ID makes every cache key effectively unique.

Even if the TTL is generous, another request cannot reuse the value.

The cache becomes a storage system containing results that are unlikely to be read again.

Increasing Redis memory may allow more such results to accumulate.

It doesn't repair the missing reuse.

## 13. Why the Global Redis Hit Ratio Lied by Omission

Redis exposes cumulative keyspace hit and miss counters.

These counters measure successful and unsuccessful key lookups across the observed workload.

They don't tell us the business value of each lookup.

Imagine a frequently accessed configuration key generating twenty thousand hits.

At the same time, 120 report jobs generate unique cache misses.

The aggregate hit ratio remains approximately 99.4%.

But every expensive report lookup missed.

The global ratio is mathematically correct.

It's operationally incomplete.

### 13.1 Segment by workload

Useful application metrics distinguish:

Configuration-cache hits.

Report-cache hits.

Report-cache misses.

Database loads caused by misses.

Duplicate report computations.

Cache-fill failures.

The cost of a miss can vary dramatically.

A configuration miss may require one inexpensive lookup.

A report miss may require a large MongoDB aggregation.

### 13.2 Lifetime counters versus rates

Redis `INFO` exposes cumulative counters.

To understand the incident, compare their differences over equivalent time windows.

A lifetime count alone can hide sudden changes.

If the application restarts, the relevant counters may reset.

An incident report should state the observation interval and avoid mixing cumulative totals with per-second rates.

## 14. Cache Stampedes and Duplicate Queued Work

Even after correcting the cache key, a concurrency problem may remain.

Suppose one report cache entry expires.

Fifty API requests arrive simultaneously.

Each checks Redis before any of the others has populated the value.

All fifty see a miss.

All fifty publish a refresh job.

The key identity is now correct.

But the application still generates duplicate work.

### 14.1 Correct keys are necessary, not sufficient

A good cache key allows reuse after a value exists.

It doesn't automatically coordinate the first concurrent loads.

This is the cache-stampede problem from SE335-L01.

Possible remedies include local single-flight coordination, distributed leases, request coalescing, stale-while-revalidate, or durable job deduplication where appropriate.

### 14.2 Distinguish duplicate computation from duplicate business effects

Repeating an idempotent report calculation wastes resources.

Repeating a reservation charge can create a correctness disaster.

The appropriate protection depends on what the job does.

For report generation, redundant computation may be undesirable but tolerable.

For money movement or external side effects, business-level idempotency is essential.

### 14.3 A Redis lock isn't automatic exactly-once execution

A distributed lock can coordinate some operations.

But locks have expiration, ownership, crash, and recovery semantics.

A worker can lose a lease while an external operation continues.

Another worker may then begin the same operation.

Locking can reduce duplicate work, but it doesn't automatically prove exactly-once effects.

## 15. Queue Growth: Arrivals, Completions, and Retry Traffic

Consider the work queue as a buffer.

If new jobs arrive faster than they're successfully completed, backlog grows.

A simplified relationship is:

**Backlog growth rate = new work arrival rate − successful completion rate.**

This formulation assumes the units represent unique logical jobs and accounts appropriately for terminal failures.

RabbitMQ's raw delivery rate may include repeated attempts and therefore cannot substitute directly for unique business arrivals or completions.

### 15.1 Queue depth is a stock

The ready-message count tells us how many messages are waiting at the broker at a particular moment.

The unacknowledged count tells us how many deliveries are outstanding with consumers.

Neither alone establishes successful throughput.

### 15.2 Completion rate is a flow

Successful business completions per second describe useful output.

Compare that flow with new logical work entering the system.

If new work arrives at fifty per second but only thirty complete, the backlog accumulates.

### 15.3 Redelivery changes attempted load

Failed deliveries that return immediately can increase broker and worker activity without increasing unique new work.

This is why a requeue storm can overwhelm a system even when customer demand is stable.

## 16. Prefetch and Consumer Concurrency

RabbitMQ prefetch limits unacknowledged deliveries.

It does not necessarily control how many tasks a worker executes simultaneously.

A synchronous worker with prefetch twenty may process one task while holding nineteen others.

A worker pool with many processes can create substantial aggregate in-flight work.

### 16.1 Prefetch can conceal the backlog

If the operations team increases prefetch, the ready-message count may decline because more messages have been delivered to consumers.

That can look like progress.

But the messages may simply be waiting inside the worker processes.

Inspect both ready and unacknowledged counts.

### 16.2 Consumer count can multiply downstream demand

Suppose each worker has one active database operation.

Scaling from eight workers to thirty-two can increase concurrent database demand fourfold.

If each worker executes several tasks concurrently, the increase may be larger.

The effective concurrency depends on the worker implementation.

Do not infer it solely from prefetch.

### 16.3 The correct tuning question

How many simultaneous operations can the downstream dependency sustainably support?

Then determine how worker concurrency and prefetch should relate to that capacity.

The objective is not maximizing the number of outstanding deliveries.

It is maximizing successful throughput under acceptable latency and failure rates.

## 17. Database Saturation and the Hidden Queue

The MongoDB connection pool is a finite resource.

A worker may acquire a connection, execute an operation, and release it.

When all available connections are busy, additional operations wait.

This creates another queue.

The application may have thousands of jobs waiting for the broker, hundreds delivered to workers, and dozens waiting for database connections.

The real system contains several waiting areas.

### 17.1 More concurrency can increase latency

Suppose the database can sustain four expensive report computations concurrently.

With four workers, each report completes in a predictable amount of time.

With twenty workers, the excess requests wait or fail.

If failures trigger immediate requeues, the same operations may be attempted repeatedly.

The system spends resources on failed attempts and retry coordination.

Useful throughput may decline.

### 17.2 Pool saturation is not necessarily database CPU saturation

The database may be overloaded because of CPU, I/O, locks, memory, or connection limits.

Alternatively, the application pool may be configured too small even though the database has spare capacity.

The distinction matters.

Inspect database metrics and application pool metrics together.

A pool wait is not automatically evidence that the database server itself has exhausted its capacity.

## 18. Retry Amplification

RabbitMQ supports negative acknowledgments with requeueing.

When a worker calls `basic.nack` with requeue enabled, the message can become eligible for immediate redelivery.

If the underlying failure is still present, the next attempt may fail in the same way.

### 18.1 A retry must have a reason to succeed

A transient failure may recover.

But an immediate retry against an already saturated database is unlikely to help.

A permanent schema or payload error won't be repaired by retrying at all.

The correct retry policy classifies failures.

Transient overload may justify delayed, bounded attempts.

Invalid payloads may belong in a dead-letter queue.

Uncertain external side effects require state verification and idempotent business logic.

### 18.2 A bounded retry budget

A retry policy should define limits.

These may include maximum attempts, maximum elapsed time, backoff, and a terminal failure route.

A budget prevents one failing job from consuming unlimited resources.

But retry counters must be reliable.

A process-local counter that resets after a worker crash is not sufficient for durable production control.

### 18.3 Delayed retries reduce feedback

If a dependency is temporarily unavailable, a delay gives it time to recover.

Exponential backoff and jitter can reduce synchronized retry bursts.

The retry path must not silently lose messages or duplicate irreversible effects.

RabbitMQ queue type and version influence which broker-managed retry features are available.

## 19. Triage: Stop the Amplification

During a real incident, the team may not have time to complete a perfect root-cause analysis before acting.

The first priority is preventing further damage.

If worker concurrency is overwhelming the database, temporarily reducing consumers or their execution concurrency may help.

If immediate requeues are generating a storm, adjust failure handling to avoid tight retry loops.

If a defective release created high-cardinality cache keys, revert or correct that behavior when safe.

If new report requests are noncritical, temporary admission limits may protect more important operations.

### 19.1 Containment is not deletion

Reducing throughput can increase queue depth temporarily.

That's acceptable if it prevents downstream collapse and preserves legitimate work.

Purging queues to make dashboards green is not a recovery strategy.

A queue may contain business work that cannot simply be discarded.

### 19.2 Preserve durable work

If messages must survive interruptions, ensure the queue and publishing configuration provide the required durability.

Dead-letter terminal failures through a correctly configured route.

Track jobs that are deferred, failed, or awaiting manual intervention.

An incident response should avoid turning a latency problem into silent data loss.

### 19.3 Separate immediate and durable changes

Immediate containment might reduce worker concurrency from thirty-two to eight.

The durable correction might restore correct cache keys, introduce request coalescing, implement delayed retries, and establish better capacity controls.

Both phases matter.

## 20. Rank Hypotheses Rather Than Listing Everything

A useful incident investigation doesn't begin with an exhaustive catalogue of possible failures.

It begins with the most plausible hypotheses supported by the symptoms.

For our scenario:

**Hypothesis A:** A recent application change reduced cache reuse for expensive reports.

Evidence: deployment timing, increased unique cache-key cardinality, increased report-cache misses.

**Hypothesis B:** Scaling workers exceeded downstream concurrency capacity.

Evidence: worker-count increase followed by connection-pool saturation and higher rejection rates.

**Hypothesis C:** Immediate requeues amplified database attempts.

Evidence: redelivery-rate spike, repeated job IDs, increased attempts per unique request.

These hypotheses are connected.

They need not be mutually exclusive.

The investigation should test them in causal order.

### 20.1 A counterfactual question

Ask:

> If the cache-key change had not occurred, would the same workload have saturated the database?

This helps identify the trigger.

Then ask:

> If retries had been delayed and bounded, would the incident have escalated as severely?

This identifies the amplifier.

Finally:

> If the database had more capacity, would the system still perform redundant report computations?

This reveals whether capacity expansion addresses the root cause or merely raises the threshold at which it becomes visible.

## 21. Establish Recovery Through Invariants

A system can appear recovered while remaining vulnerable to the same failure.

Define what healthy operation means.

The report cache should reuse results for equivalent requests without crossing tenant or filter boundaries.

Duplicate report requests should not create uncontrolled computation bursts.

Worker concurrency should remain within sustainable downstream capacity.

Transient failures should be retried according to a bounded policy.

Permanent failures should not circulate indefinitely.

Successful business completion rate should be sufficient to drain expected backlog.

Database connection waits and timeouts should remain within acceptable ranges.

These invariants provide a better recovery contract than merely requiring the queue depth to reach zero.

## 22. Monitor the Causal Chain

A useful monitoring dashboard might show five groups of measurements.

### Cache behavior

Segmented hit and miss rates for expensive report keys.

Distinct key cardinality.

TTL and eviction behavior.

Backend loads per cache miss.

### RabbitMQ behavior

New messages published.

Ready messages.

Unacknowledged deliveries.

Delivery and redelivery rates.

Acknowledgment rates.

Dead-letter volume.

### Worker behavior

Active jobs.

Successful completions.

Failure categories.

Processing duration.

Retry attempts per logical job.

### Database behavior

Connection-pool acquisition waits.

Concurrent operations.

Query duration.

Timeout and rejection rates.

CPU and I/O utilization.

### Product behavior

Report completion latency.

Percentage of requests completing successfully.

Age of outstanding customer work.

Number of unique jobs still unfinished.

The strongest monitoring system connects these metrics through job IDs, tenant IDs, trace IDs, and consistent time windows.

## 23. The Incident Review

Let's reconstruct the incident as a complete engineering explanation.

A release changed the report-cache key so that equivalent requests produced distinct entries.

Cache reuse for expensive reports collapsed.

The application published additional report-generation jobs.

RabbitMQ backlog increased.

Operators scaled workers.

The additional consumers generated more simultaneous database operations than the downstream service could sustain.

Database requests began failing.

The workers immediately requeued failed messages.

Redelivery created additional attempts, increasing pressure on the already saturated dependency.

Redis's global hit ratio remained high because inexpensive hot-key lookups dominated the counter.

RabbitMQ's delivery rate increased, but successful business completions fell.

This is not four independent incidents.

It is one causal chain with several feedback mechanisms.

The effective recovery requires stopping amplification, repairing cache identity and duplicate-work behavior, and restoring sustainable worker concurrency.

## 24. What a Strong Interview Explanation Sounds Like

A strong answer might be:

"The queue depth is the symptom I'd investigate, but not necessarily the root cause. I'd compare unique job arrivals with successful completions and redeliveries, then check whether workers are waiting on MongoDB connections. The Redis hit ratio is too aggregated to rule out expensive report-cache misses. I'd investigate the report key distribution and the release timeline. If scaling workers increased database failures and immediate requeues, I'd contain concurrency and retry amplification first, then correct the cache-key or request-coalescing defect and verify recovery."

This answer doesn't require pretending to know every implementation detail before examining the evidence.

It establishes a testable causal model.

That is the skill the studio is designed to develop.

---

# The Oral Examination

Answer aloud before reading the solutions.

## Question 1 — The 99% Cache Hit Rate

Redis reports 99% hits, but the database receives far more report queries than before.

How can both observations be correct?

What additional measurements are needed?

## Question 2 — The Falling Ready Count

RabbitMQ's ready count falls after worker scaling, but unacknowledged messages increase dramatically.

Does this prove the backlog is shrinking?

## Question 3 — The Attempt Explosion

The system receives 100 unique jobs but performs 400 database attempts.

What does this suggest?

How would you establish whether retries caused the amplification?

## Question 4 — The Worker Scaling Failure

Why might reducing worker concurrency increase successful job throughput?

Under what conditions would increasing concurrency be useful instead?

## Question 5 — The Cache-Key Fix

A developer removes tenant ID from the report-cache key so more requests share cached values.

Would this necessarily be a valid optimization?

Why not?

## Question 6 — The Correct Key, Duplicate Jobs

You fix cache-key identity, but fifty simultaneous requests still miss before the cache is populated.

What problem remains?

What strategies might address it?

## Question 7 — Immediate Requeue

A worker gets a database-overload error and immediately calls `nack(requeue=true)`.

Why might this be harmful?

What would a better retry policy consider?

## Question 8 — The Connection Pool

The application reports pool-acquisition waits.

Can you conclude that MongoDB itself has exhausted CPU or I/O capacity?

What additional evidence is needed?

## Question 9 — Containment Versus Correction

You reduce worker concurrency, and database timeouts disappear.

Is the incident permanently fixed?

What root-cause work remains?

## Question 10 — Senior Incident Judgment

You have five minutes to stabilize the system.

Which measurements and interventions deserve priority?

What actions would you avoid without additional evidence?

---

# Solutions and Discussion

## Solution 1 — The Cache Hit Rate

The global counter may be dominated by inexpensive hot-key reads.

Expensive report lookups may have poor cache reuse despite the high aggregate ratio.

Measure per-operation hit rates, key cardinality, and database loads caused by misses.

## Solution 2 — Ready Versus Unacknowledged

No.

Work may have moved into consumers without completing.

Inspect ready and unacknowledged counts together, along with successful completion rates and downstream waits.

## Solution 3 — Attempt Amplification

The system is performing multiple database attempts per unique logical job.

Possible causes include retries, redeliveries, duplicate job submission, or multiple legitimate database operations per job.

Correlate job IDs, delivery attempts, and actual database calls.

## Solution 4 — Worker Concurrency

Excessive concurrency can overload a shared dependency, causing timeouts and retry overhead.

Reducing concurrency can improve successful throughput by lowering contention.

Increasing concurrency is useful when downstream capacity is available and worker execution is genuinely the bottleneck.

## Solution 5 — Cache Identity

No.

Tenant identity may affect both result correctness and authorization boundaries.

Removing it could expose one tenant's data to another.

A cache key must include every dimension that materially changes the result or its permitted audience.

## Solution 6 — Cache Stampede

Concurrent misses can still generate duplicate computation.

Possible remedies include request coalescing, single-flight coordination, carefully designed distributed leases, stale-while-revalidate, or durable job deduplication.

Each requires appropriate failure semantics.

## Solution 7 — Immediate Requeue

The message can be redelivered before the database recovers.

Repeated attempts increase load.

A better strategy classifies the failure, applies bounded delayed retries, includes jitter where appropriate, and handles terminal failure safely.

## Solution 8 — Pool Waiting

No.

An undersized application pool can cause waits even when the database has spare capacity.

Inspect actual database utilization, connection limits, active operations, query latency, and pool configuration.

## Solution 9 — Containment Versus Root Fix

Reducing concurrency may stabilize the system without correcting the high-cardinality cache keys or duplicate report submissions.

The durable fix must address the initiating defect and prevent recurrence.

## Solution 10 — Incident Priorities

Measure unique arrivals, successful completions, redeliveries, worker concurrency, database waits, and report-cache misses.

Contain retry storms and excessive concurrency when evidence supports them.

Avoid blindly scaling workers, purging durable work, disabling failure protection, or increasing resource limits without identifying the bottleneck.

---

# The Mental Model Worth Keeping

A distributed incident is a graph of dependencies and feedback loops.

The initiating failure may occur in one service.

The largest symptoms may appear elsewhere.

Retries, queueing, caching, and scaling can either absorb pressure or amplify it.

To diagnose the system, distinguish:

**Trigger:** What first changed the workload?

**Amplifier:** What behavior made the problem grow?

**Bottleneck:** Which resource limited progress?

**Symptom:** What did users and dashboards observe?

**Containment:** What stops the system from getting worse?

**Correction:** What restores the intended behavior?

**Verification:** What proves sustainable recovery?

That's the operational model worth carrying into production.

---

# Course Completion — SE335

This completes the three-lecture SE335 specialist course.

SE335-L01 investigated Redis memory, latency, cache misses, eviction, and misleading hit ratios.

SE335-L02 investigated RabbitMQ acknowledgments, prefetch, consumer failures, poison messages, and worker concurrency.

SE335-L03 combines these mechanisms into a cross-service incident.

The manuscripts provide knowledge.

The studio is where that knowledge becomes independent diagnostic competence.

Successful completion requires more than recognizing the terms. You should be able to reconstruct a causal timeline, identify the source of redundant work, contain amplification, verify throughput recovery, and defend the operational trade-offs.

A completed manuscript is not the same as demonstrated fluency.

*The spoken lecture ends here. The following exercises are intended for independent investigation. Read the diagnostic notes only after attempting the incident.*

---

# Optional Practical Lab — The Cross-Service Incident Room

## Lab Contract

This is a synthetic but runnable incident.

It uses real Redis and RabbitMQ services, plus a small HTTP service simulating a database with limited concurrent query capacity.

The database simulator is deliberately simple. It models a concurrency bottleneck and overload rejection, not actual MongoDB query execution, locking, or storage behavior.

The lab is isolated and disposable.

It does not model every production reliability guarantee.

Your tasks are to reproduce the incident, collect evidence, rank hypotheses, implement a correction, and verify the result.

**Prediction → Evidence → Containment → Correction → Verification → Defense.**

Do not read the solution key before your first independent attempt.

## 1. Start the Infrastructure

Create a directory named `se335-incident-studio`.

Inside it, create `compose.yaml`.

The file starts Redis and RabbitMQ on localhost-only ports.

```yaml
services:
  redis:
    image: redis:7.4-alpine
    command:
      - redis-server
      - --save
      - ""
      - --appendonly
      - "no"
    ports:
      - "127.0.0.1:6388:6379"

  rabbitmq:
    image: rabbitmq:4-management
    environment:
      RABBITMQ_DEFAULT_USER: lab
      RABBITMQ_DEFAULT_PASS: labpass
    ports:
      - "127.0.0.1:5680:5672"
      - "127.0.0.1:15680:15672"
```

Start the services.

```bash
docker compose up -d
```

The RabbitMQ management interface is available at:

`http://localhost:15680`

Use the laboratory credentials:

`lab` / `labpass`

Do not expose these services or credentials outside the local environment.

### Python dependencies

Create a Python virtual environment and install the clients.

```bash
python -m venv .venv
source .venv/bin/activate

python -m pip install "pika<2" "redis>=5,<7"
```

On Windows, use the corresponding PowerShell or Command Prompt activation command.

The laboratory uses Pika's blocking adapter for simplicity. Its current documentation warns that this adapter is deprecated for future Pika 2.0 and that blocking user callbacks can delay heartbeat processing. Our simulated operations are deliberately short; the lab is not a recommended production worker architecture.

---

# 2. Create the RabbitMQ Topology

Create `setup.py`.

The script declares three queues.

`studio.work` contains report-generation jobs.

`studio.retry` delays transient retries using a queue-level TTL.

`studio.dead` receives terminal failures.

```python
import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host="localhost",
        port=5680,
        credentials=pika.PlainCredentials(
            "lab", "labpass"
        ),
    )
)

channel = connection.channel()

channel.exchange_declare(
    exchange="studio.dlx",
    exchange_type="direct",
    durable=True,
)

channel.queue_declare(
    queue="studio.dead",
    durable=True,
)

channel.queue_bind(
    queue="studio.dead",
    exchange="studio.dlx",
    routing_key="dead",
)

channel.queue_declare(
    queue="studio.work",
    durable=True,
)

channel.queue_declare(
    queue="studio.retry",
    durable=True,
    arguments={
        "x-message-ttl": 1200,
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": "studio.work",
    },
)

connection.close()

print("Studio queues declared.")
```

Run the setup.

```bash
python setup.py
```

Configure a dead-letter policy for the work queue.

```bash
docker compose exec rabbitmq rabbitmqctl set_policy \
  studio_dead \
  '^studio\.work$' \
  '{"dead-letter-exchange":"studio.dlx","dead-letter-routing-key":"dead"}' \
  --apply-to queues
```

The retry queue uses fixed declaration arguments solely to keep this disposable lab simple. For operationally adjustable dead-letter and retry configurations, RabbitMQ policies are generally preferable.

Inspect the queues.

```bash
docker compose exec rabbitmq rabbitmqctl list_queues \
  name messages_ready messages_unacknowledged consumers
```

### Verification

Confirm that `studio.work`, `studio.retry`, and `studio.dead` exist.

Confirm that the dead-letter policy applies to `studio.work`.

The retry queue should route expired messages back to `studio.work`.

---

# 3. Create the Capacity-Limited Database Simulator

Create `database_simulator.py`.

The simulator accepts a maximum of four simultaneous report computations.

Each successful computation takes approximately 250 milliseconds.

Requests arriving when all four slots are occupied receive HTTP 503.

It exposes counters through `/metrics`.

```python
import json
import threading
import time

from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)


capacity = threading.BoundedSemaphore(4)
lock = threading.Lock()

metrics = {
    "active": 0,
    "completed": 0,
    "rejected": 0,
    "max_active": 0,
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_error(404)
            return

        with lock:
            body = json.dumps(metrics).encode()

        self.send_response(200)
        self.send_header(
            "Content-Type", "application/json"
        )
        self.send_header(
            "Content-Length", str(len(body))
        )
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/compute":
            self.send_error(404)
            return

        length = int(
            self.headers.get("Content-Length", "0")
        )

        self.rfile.read(length)

        if not capacity.acquire(blocking=False):
            with lock:
                metrics["rejected"] += 1

            self.send_response(503)
            self.end_headers()
            return

        try:
            with lock:
                metrics["active"] += 1
                metrics["max_active"] = max(
                    metrics["max_active"],
                    metrics["active"],
                )

            time.sleep(0.25)

            with lock:
                metrics["completed"] += 1

            body = b'{"result":"report-ready"}'

            self.send_response(200)
            self.send_header(
                "Content-Type", "application/json"
            )
            self.send_header(
                "Content-Length", str(len(body))
            )
            self.end_headers()
            self.wfile.write(body)

        finally:
            with lock:
                metrics["active"] -= 1

            capacity.release()

    def log_message(self, format, *args):
        return


server = ThreadingHTTPServer(
    ("127.0.0.1", 8099),
    Handler,
)

print(
    "Database simulator: localhost:8099",
    flush=True,
)

server.serve_forever()
```

Start the simulator in a separate terminal.

```bash
python database_simulator.py
```

Open:

`http://localhost:8099/metrics`

Initially, completed and rejected operations should be zero.

### Important distinction

A rejected simulator request represents an overloaded downstream dependency.

It does not prove that real MongoDB behaves this way under connection saturation.

Real database pressure can cause waiting, timeouts, lock contention, resource exhaustion, or other effects.

The simulator gives us one controlled mechanism to investigate.

---

# 4. Seed the Misleading Redis Hit Rate and RabbitMQ Jobs

Create `producer.py`.

The script performs two activities.

First, it repeatedly reads an inexpensive Redis configuration key.

Second, it publishes 120 logically equivalent report-generation requests.

Each request has a distinct request ID, but all ask for the same Mercury quarterly report.

This is intentional.

```python
import json

import pika
import redis


cache = redis.Redis(
    host="localhost",
    port=6388,
    decode_responses=True,
)

cache.set(
    "config:regions",
    "eu-central,eu-west",
)

for _ in range(20000):
    cache.get("config:regions")

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host="localhost",
        port=5680,
        credentials=pika.PlainCredentials(
            "lab", "labpass"
        ),
    )
)

channel = connection.channel()
channel.confirm_delivery()

for number in range(1, 121):
    job = {
        "id": f"report-{number:04d}",
        "tenant": "mercury",
        "report": "quarterly",
        "version": "v1",
    }

    channel.basic_publish(
        exchange="",
        routing_key="studio.work",
        body=json.dumps(job).encode(),
        mandatory=True,
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
            message_id=job["id"],
        ),
    )

connection.close()

print("Published 120 report jobs.")
print("Performed 20,000 config-cache hits.")
```

Run:

```bash
python producer.py
```

### Initial observation

Redis has recorded many successful key lookups.

RabbitMQ has 120 queued report jobs.

The database simulator has performed no report computation yet.

### Question

If every report job later misses its cache key, how useful will the global Redis hit rate be for diagnosing the expensive report workflow?

---

# 5. The Deliberately Broken Worker

Create `worker.py`.

The worker has two modes:

`broken`: uses a unique cache key per request and immediately requeues transient failures.

`corrected`: uses a shared result identity and routes transient failures through a delayed, bounded retry queue.

Both modes use the same database simulator.

The broken mode includes a six-attempt safety ceiling stored in the local Redis instance to prevent an unlimited demonstration loop. This ceiling is not a production-grade retry system.

```python
import argparse
import json
import urllib.error
import urllib.request

import pika
import redis


parser = argparse.ArgumentParser()

parser.add_argument(
    "--mode",
    choices=["broken", "corrected"],
    required=True,
)

parser.add_argument(
    "--prefetch",
    type=int,
    default=1,
)

args = parser.parse_args()

if args.prefetch < 1:
    raise SystemExit("Prefetch must be positive.")


cache = redis.Redis(
    host="localhost",
    port=6388,
    decode_responses=True,
)

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host="localhost",
        port=5680,
        heartbeat=60,
        blocked_connection_timeout=30,
        credentials=pika.PlainCredentials(
            "lab", "labpass"
        ),
    )
)

channel = connection.channel()

channel.basic_qos(
    prefetch_count=args.prefetch,
)

channel.confirm_delivery()


def compute_report(job):
    body = json.dumps(job).encode()

    request = urllib.request.Request(
        "http://127.0.0.1:8099/compute",
        data=body,
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=3,
    ) as response:
        return response.read().decode()


def retry_later(ch, method, properties, body):
    old_attempt = (
        properties.headers or {}
    ).get("attempt", 0)

    next_attempt = int(old_attempt) + 1

    if next_attempt > 3:
        ch.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=False,
        )
        return

    retry_properties = pika.BasicProperties(
        delivery_mode=2,
        content_type="application/json",
        message_id=properties.message_id,
        headers={"attempt": next_attempt},
    )

    # A confirmed republish must succeed before
    # acknowledging the original delivery.
    #
    # This is NOT an atomic transaction across
    # publishing and acknowledgment. A crash
    # between them can still cause duplication.
    ch.basic_publish(
        exchange="",
        routing_key="studio.retry",
        body=body,
        mandatory=True,
        properties=retry_properties,
    )

    ch.basic_ack(
        delivery_tag=method.delivery_tag,
    )


def on_message(ch, method, properties, body):
    job = json.loads(body)
    job_id = job["id"]

    if args.mode == "broken":
        cache_key = (
            f"report:{job['tenant']}:"
            f"{job['report']}:{job['version']}:"
            f"{job_id}"
        )

    else:
        cache_key = (
            f"report:{job['tenant']}:"
            f"{job['report']}:{job['version']}"
        )

    existing = cache.get(cache_key)

    if existing is not None:
        print(
            f"CACHE HIT {job_id}",
            flush=True,
        )

        ch.basic_ack(
            delivery_tag=method.delivery_tag,
        )
        return

    print(
        f"CACHE MISS {job_id}",
        flush=True,
    )

    try:
        result = compute_report(job)

    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
    ) as exc:
        print(
            f"COMPUTE FAILED {job_id}: {exc}",
            flush=True,
        )

        if args.mode == "broken":
            attempts = cache.incr(
                f"studio:attempt:{job_id}"
            )

            if attempts >= 6:
                ch.basic_nack(
                    delivery_tag=method.delivery_tag,
                    requeue=False,
                )
            else:
                ch.basic_nack(
                    delivery_tag=method.delivery_tag,
                    requeue=True,
                )

        else:
            retry_later(
                ch,
                method,
                properties,
                body,
            )

        return

    cache.set(
        cache_key,
        result,
        ex=30,
    )

    print(
        f"COMPLETED {job_id}",
        flush=True,
    )

    ch.basic_ack(
        delivery_tag=method.delivery_tag,
    )


channel.basic_consume(
    queue="studio.work",
    on_message_callback=on_message,
    auto_ack=False,
)

print(
    f"Worker mode={args.mode}",
    f"prefetch={args.prefetch}",
    flush=True,
)

try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
finally:
    if connection.is_open:
        connection.close()
```

## Important limitations

This is a teaching implementation.

It assumes the report result is identical for requests sharing the same tenant, report type, and version. In a real application, the key must also include any relevant filters, time ranges, authorization scope, and data version.

The corrected mode doesn't provide perfect distributed single-flight coordination. Several workers can still observe the initial miss before the first result is cached.

The retry queue and acknowledgment sequence are not one atomic operation. If a worker crashes after publishing the retry but before acknowledging the original, duplicate work is possible.

The demonstration does not implement complete business-level idempotency.

These limitations are intentional discussion points.

---

# 6. Run the Broken System

Start several worker processes in separate terminals.

For the initial experiment, use twelve workers with prefetch ten.

Each process executes one callback at a time, so prefetch ten does not create ten simultaneous computations per worker.

You can start them manually or create a small supervisor script.

Create `run_workers.py`.

```python
import argparse
import subprocess
import sys
import time

from pathlib import Path


parser = argparse.ArgumentParser()

parser.add_argument(
    "--mode",
    choices=["broken", "corrected"],
    required=True,
)

parser.add_argument(
    "--workers",
    type=int,
    default=4,
)

parser.add_argument(
    "--prefetch",
    type=int,
    default=1,
)

parser.add_argument(
    "--seconds",
    type=int,
    default=12,
)

args = parser.parse_args()

Path("logs").mkdir(exist_ok=True)

processes = []
log_files = []

try:
    for index in range(args.workers):
        path = Path(
            f"logs/{args.mode}-{index}.log"
        )

        log_file = path.open("w")
        log_files.append(log_file)

        process = subprocess.Popen(
            [
                sys.executable,
                "worker.py",
                "--mode",
                args.mode,
                "--prefetch",
                str(args.prefetch),
            ],
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

        processes.append(process)

    time.sleep(args.seconds)

finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()

    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    for log_file in log_files:
        log_file.close()

print("Worker run completed.")
```

Run:

```bash
python run_workers.py \
  --mode broken \
  --workers 12 \
  --prefetch 10 \
  --seconds 12
```

### Observe the database simulator

Open:

`http://localhost:8099/metrics`

Record:

- Completed computations.
- Rejected computations.
- Maximum concurrent computations.

### Observe RabbitMQ

```bash
docker compose exec rabbitmq rabbitmqctl list_queues \
  name messages_ready messages_unacknowledged consumers
```

Inspect the work and dead-letter queues.

### Observe Redis

```bash
docker compose exec redis redis-cli INFO stats
```

Record:

- `keyspace_hits`
- `keyspace_misses`
- `expired_keys`
- `evicted_keys`

### Investigate worker logs

Open the files under `logs/`.

Look for repeated request IDs, cache misses, computation failures, and successful completions.

### Questions before proceeding

1. Does the global hit rate remain high despite expensive report misses?
2. How many database computation attempts were rejected?
3. Do repeated job IDs appear in worker logs?
4. Is the ready count alone sufficient to understand unfinished work?
5. What caused the first unnecessary database computations?
6. What amplified the failures?

Do not read the diagnostic notes yet.

---

# 7. Compare with a Controlled Recovery

For a clean comparison, stop all worker processes.

Restart the disposable environment to reset Redis and RabbitMQ state.

```bash
docker compose down
docker compose up -d
```

Because no persistent volumes are configured in this laboratory, this restarts the services with fresh container-local state.

If Docker retains an existing container unexpectedly, ensure the laboratory services are correctly recreated. Do not apply destructive reset commands to unrelated infrastructure.

Restart `database_simulator.py` separately to reset its in-memory counters.

Run the queue setup and dead-letter policy again.

```bash
python setup.py
```

Then reapply the policy:

```bash
docker compose exec rabbitmq rabbitmqctl set_policy \
  studio_dead \
  '^studio\.work$' \
  '{"dead-letter-exchange":"studio.dlx","dead-letter-routing-key":"dead"}' \
  --apply-to queues
```

Seed the same workload.

```bash
python producer.py
```

Run four corrected workers with prefetch one.

```bash
python run_workers.py \
  --mode corrected \
  --workers 4 \
  --prefetch 1 \
  --seconds 12
```

### Compare the results

Record the same measurements as before.

The corrected cache key allows equivalent requests to reuse the same result.

The lower worker concurrency is within the simulator's four-operation capacity.

Transient failures, if they occur, use a delayed, bounded retry route rather than immediate requeue.

### Important qualification

The corrected implementation still permits an initial cache stampede.

Several workers may simultaneously miss before any result is cached.

The experiment should demonstrate reduced redundant work under the tested conditions, but exact counts and timing depend on scheduling.

Do not invent a fixed performance improvement.

Measure what happens.

---

# 8. The Remaining Stampede

Now run a third experiment.

Use the corrected cache key but twelve workers.

Keep the simulator's capacity at four.

### Prediction

Several workers may receive messages before the first shared report result has been cached.

They may all observe a cache miss.

Some may attempt the downstream computation concurrently.

The simulator may reject operations beyond its capacity.

Once a successful computation populates Redis, later jobs can reuse the cached result.

### Investigation

Does the corrected key eliminate all redundant computation?

Or does it mainly allow reuse after the first result becomes available?

How could the application coordinate concurrent requests for the same report?

### Design task

Propose a request-coalescing mechanism.

Your design must account for:

- Distributed API instances.
- Worker crashes.
- Lock or lease expiration.
- Duplicate messages.
- Report version changes.
- Tenant isolation.
- Recovery when the first computation fails.

Do not assume a single Redis lock automatically provides exactly-once execution.

---

# 9. The Incident Timeline Exercise

You are given the following synthetic incident timeline.

| Time | Observation |
|---|---|
| 14:00 | Stable operation |
| 14:08 | New API release begins |
| 14:12 | Report-cache misses increase |
| 14:15 | RabbitMQ ready backlog increases |
| 14:16 | Workers scaled from 8 to 32 |
| 14:18 | Database pool waits increase |
| 14:20 | Worker timeouts spike |
| 14:22 | RabbitMQ redeliveries surge |
| 14:25 | Successful report throughput declines |

### Task

Classify each meaningful observation as:

- Trigger.
- Amplifier.
- Bottleneck.
- Symptom.
- Recovery signal, if applicable.

Then write a causal explanation in no more than three paragraphs.

Your explanation must identify which claims are directly supported by the observations and which still require verification.

---

# 10. The Containment Decision

Imagine you're the on-call engineer.

The database simulator represents a real production dependency.

The business has important background jobs waiting.

You're presented with five proposed actions.

### Proposal A — Double the workers again

The queue is large, so additional consumers might drain it faster.

### Proposal B — Increase prefetch from ten to one hundred

This should reduce the number of messages still showing as ready.

### Proposal C — Temporarily reduce concurrency

Limit simultaneous database work while investigating the overload.

### Proposal D — Disable retry limits

Keep retrying until every job succeeds.

### Proposal E — Correct cache identity and introduce bounded retry behavior

Remove redundant computation while preserving legitimate jobs.

### Assignment

Rank these proposals according to the evidence in the incident.

Explain which actions you would use immediately, which are durable corrections, and which could make the incident worse.

Do not assume one intervention addresses every failure mode.

---

# 11. Final Incident Report

Prepare a technical incident report with the following structure.

## Business impact

What did customers experience?

Which workflows were delayed or unavailable?

What business work remains outstanding?

## Initiating change

Which release behavior likely caused additional workload?

What evidence supports that claim?

## Amplification mechanisms

How did worker scaling and immediate requeues increase pressure?

## Downstream bottleneck

What resource limited successful report computation?

## Why monitoring was misleading

Explain the high Redis hit ratio and the difference between RabbitMQ delivery activity and successful completions.

## Immediate containment

Which actions stabilize the system without discarding legitimate work?

## Durable correction

Describe the cache-key fix, duplicate-work handling, retry policy, and concurrency controls.

## Verification

Define concrete signals indicating recovery.

Examples include:

- Reduced report-cache miss rate.
- Fewer database attempts per unique report.
- Lower downstream rejection rate.
- Higher successful completion rate.
- Falling outstanding backlog.
- Reduced redelivery amplification.

## Prevention

What tests, alerts, and release checks would reduce recurrence?

---

# STOP — End of Independent Studio

Do not read the following diagnostic notes until after completing at least one independent investigation.

The purpose is to practice causal diagnosis rather than memorize the intended answer.

---

# Diagnostic Notes and Reference Discussion

## Root Cause — Cache-Key Cardinality

The broken worker includes a unique request ID in the cache key.

All 120 jobs request the same logical report, but each receives a distinct cache identity.

The application therefore loses the ability to reuse cached results across equivalent requests.

Redis continues serving the configuration key efficiently.

The global hit ratio can remain high while the expensive report workflow misses repeatedly.

The root cause is not insufficient Redis memory.

It is incorrect cache-key identity for the intended result.

## Amplifier One — Excessive Worker Concurrency

Twelve workers submit computations to a simulator supporting four concurrent operations.

Requests exceeding that capacity are rejected.

Increasing workers beyond the simulator's supported concurrency doesn't automatically improve useful throughput.

It increases attempted load and can cause more failures.

In a real database, saturation may appear through connection-pool waits, query latency, lock contention, or resource exhaustion rather than immediate HTTP 503 responses.

## Amplifier Two — Immediate Requeues

The broken worker immediately requeues failed deliveries.

RabbitMQ can redeliver them rapidly.

This produces repeated attempts against the same overloaded dependency.

The six-attempt safety cap prevents the local demonstration from becoming an unlimited loop.

It is not a substitute for durable production retry semantics.

## The Corrected Cache Key

The corrected worker uses a key based on tenant, report type, and version.

Under the laboratory assumptions, all requests represent the same reusable report.

Once a result is cached, subsequent jobs can reuse it.

In a real system, the key must include every dimension affecting the result or its permitted audience.

## Why the Corrected Version Can Still Stampede

Several workers can observe the same missing key before the first computation completes.

Those workers may all attempt the downstream operation.

A correct key enables reuse after population but doesn't automatically coordinate the initial computation.

A production design may require request coalescing, single-flight behavior, durable deduplication, or a suitable distributed coordination mechanism.

## Why Lower Concurrency Helps

The database simulator has four concurrent processing slots.

Running four workers avoids intentionally exceeding that limit in the simplified experiment.

This reduces overload rejection.

The exact optimal concurrency of a real system depends on processing time, I/O behavior, database capacity, and workload characteristics.

The purpose is to tune against evidence rather than assume more workers always help.

## Why Delayed Retries Help

The corrected worker routes transient failures through a retry queue with a short TTL.

That creates a delay before the message becomes available again.

It also bounds the number of retries.

This reduces the risk of a tight requeue loop.

But the publish-then-ack sequence is not atomic.

Production systems must still account for duplicate deliveries and uncertain outcomes.

## Why the Queue-Ready Count Can Mislead

RabbitMQ distinguishes ready messages from unacknowledged deliveries.

A large prefetch can move messages from the broker's ready state into consumers without completing them.

A falling ready count doesn't necessarily mean useful throughput increased.

Compare total outstanding work, acknowledgments, and business completions.

## Why the Incident Needs Several Corrections

Fixing the cache key reduces redundant future computation.

It doesn't automatically eliminate all duplicate queued work.

Reducing concurrency contains downstream pressure.

It doesn't fix cache identity.

Delayed retries prevent immediate amplification.

They don't increase the database's underlying capacity.

A sustainable solution addresses the trigger and the relevant amplifiers while respecting the actual bottleneck.

---

# Further Reading

1. **Redis — Key Eviction and Cache Hit Statistics**  
   https://redis.io/docs/latest/develop/reference/eviction/

2. **Redis — INFO**  
   https://redis.io/docs/latest/commands/info/

3. **RabbitMQ — Consumer Acknowledgments and Publisher Confirms**  
   https://www.rabbitmq.com/docs/confirms

4. **RabbitMQ — Consumer Prefetch**  
   https://www.rabbitmq.com/docs/consumer-prefetch

5. **RabbitMQ — Dead-Letter Exchanges**  
   https://www.rabbitmq.com/docs/dlx

6. **RabbitMQ — Monitoring**  
   https://www.rabbitmq.com/docs/monitoring

7. **RabbitMQ — Quorum Queues**  
   https://www.rabbitmq.com/docs/quorum-queues

8. **RabbitMQ — Reliability Guide**  
   https://www.rabbitmq.com/docs/reliability

9. **Pika — Blocking Connection Adapter**  
   https://pika.github.io/pika/latest/modules/adapters/blocking/

10. **Pika — Consuming Messages**  
    https://pika.github.io/pika/latest/examples/blocking_consume/

Cross-reference SE335-L01 for Redis cache forensics, SE335-L02 for RabbitMQ delivery behavior, SE320-L02/L03 for caching and asynchronous workflow foundations, CS430-L01/L03 for distributed failures and capacity reasoning, SE325-L06 for multi-tenant fairness, and `production-cases/REDIS-01.md` and `QUEUE-01.md` for the related incident packets.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text
SE335-L03 — ASYNCHRONOUS SYSTEM INCIDENT STUDIO
================================================

THE SIX DIAGNOSTIC QUESTIONS
----------------------------
1. What triggered the change?
2. What amplified the failure?
3. What resource became the bottleneck?
4. Where is unfinished work waiting?
5. What contains the incident safely?
6. What proves durable recovery?

CAUSAL CHAIN
------------
Bad cache-key identity
    ↓
Expensive cache misses
    ↓
More report jobs
    ↓
Queue backlog
    ↓
Worker scaling
    ↓
Database saturation
    ↓
Timeouts
    ↓
Immediate requeues
    ↓
Retry amplification

CACHE DIAGNOSIS
---------------
Global hit ratio can hide
expensive workload misses.

Segment:
  report hits/misses
  config hits/misses
  database loads
  unique key cardinality
  duplicate computations

CACHE KEY CONTRACT
------------------
Same key:
  equivalent reusable result

Different key:
  materially different result

Include:
  tenant
  filters
  report type
  range
  version
  authorization scope as required

Do NOT include request ID
unless it actually changes result identity.

CACHE STAMPEDE
--------------
Correct key doesn't prevent
simultaneous initial misses.

Potential:
  single-flight
  request coalescing
  lease coordination
  stale-while-revalidate
  durable job deduplication

Retries and crashes remain relevant.

RABBITMQ
--------
ready:
  waiting for delivery

unacknowledged:
  delivered, awaiting ack

delivery rate:
  not necessarily unique work

redelivery rate:
  may indicate retry amplification

ack rate:
  delivery completion signal,
  not automatically business correctness

PREFETCH
--------
Limits unacknowledged deliveries.

Does NOT guarantee
parallel execution.

High prefetch may reserve work
inside slow consumers.

WORKER CONCURRENCY
------------------
More workers increase potential
downstream demand.

Throughput rises only while
the bottleneck has capacity.

Too much concurrency can cause:
  pool waits
  timeouts
  contention
  retries
  reduced useful throughput

RETRY AMPLIFICATION
-------------------
New work + repeated failed attempts
= increased attempted load

Immediate nack(requeue=true)
may create tight loops.

Use:
  failure classification
  bounded retries
  delayed retry
  backoff + jitter
  dead-letter terminal failures

DOWNSTREAM POOLS
----------------
An application pool is another queue.

Distinguish:
  waiting for pool connection
  active database execution
  database lock wait
  service overload

Low CPU doesn't rule out
queueing and contention.

BACKLOG
-------
For unique logical jobs:

Backlog growth ≈ arrivals - completions

Raw broker deliveries may include
multiple attempts of same job.

Measure useful business completions.

CONTAINMENT
-----------
Stop retry amplification.
Bound worker concurrency.
Protect downstream capacity.
Limit noncritical new work if needed.
Preserve durable jobs.
Investigate trigger.

Do not blindly:
  add workers
  increase prefetch
  purge queues
  disable retry limits
  raise DB connection limits

DURABLE CORRECTION
------------------
Correct cache identity.
Coordinate duplicate requests.
Bound concurrency.
Classify failures.
Use safe retry topology.
Maintain business idempotency.
Monitor end-to-end completion.

VERIFICATION
------------
Report-cache reuse improves.
DB attempts per logical job fall.
Rejected operations decline.
Successful throughput recovers.
Outstanding backlog drains.
Redelivery amplification falls.
Latency becomes sustainable.

INTERVIEW ANSWER
----------------
Start from business impact.
Build evidence-based timeline.
Separate trigger from amplifiers.
Identify actual bottleneck.
Contain before redesigning.
Propose minimal durable changes.
Verify with rates and invariants.

COURSE COMPLETION
-----------------
SE335-L01:
  Redis memory, latency, cache failures

SE335-L02:
  RabbitMQ ack, prefetch, poison, retry

SE335-L03:
  Cross-service failure diagnosis

FINAL MODEL
-----------
The loudest symptom isn't necessarily
the initiating cause.

Find the feedback loop.
Break the amplifier.
Repair the trigger.
Verify useful work.
```
