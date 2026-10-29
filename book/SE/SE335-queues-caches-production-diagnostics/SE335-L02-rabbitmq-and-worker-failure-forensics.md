---
id: SE335-L02
course: SE335
title: "RabbitMQ and Worker Failure Forensics"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE335-L01
next: SE335-L03
---

# SE335 — Queues, Caches, and Worker Production Diagnostics
## Lecture 02: RabbitMQ and Worker Failure Forensics

*The queue is growing, so the team adds workers. Throughput barely improves. Database errors multiply, unacknowledged messages accumulate, and one poisonous message is delivered hundreds of times without ever succeeding.*

---

# Part I — Intuition

## 1. The Worker Fleet That Made Production Worse

Imagine you're investigating a production incident at a cybersecurity SaaS company.

The platform performs asset discovery. Customers submit domains and IP addresses, and background workers execute scanning modules, collect results, and update MongoDB.

The architecture is familiar.

An API accepts work. A manager publishes jobs to RabbitMQ. Worker processes consume those jobs. A processor collects results and writes them to the database.

During an unusually busy afternoon, the queue begins growing.

The operations team sees twelve thousand pending jobs.

The obvious response is to add more workers.

The deployment scales from eight worker processes to thirty-two.

For a few minutes, the team expects the queue to drain rapidly.

Instead, processing latency increases.

MongoDB connections become saturated. Some workers time out while writing results. Failed messages return to the queue, and the broker's delivery rate rises dramatically.

The dashboard now shows more activity than before.

But completed scans per second have barely improved.

The system is busier without being more productive.

What happened?

The team assumed that more consumers meant more throughput.

That assumption is only true while the rest of the system has capacity to support the additional concurrency.

## 2. A Queue Is a Waiting Room, Not an Engine

Imagine a hospital with four doctors.

Patients wait in a reception area.

Adding more receptionists can make registration faster, but it doesn't necessarily increase the number of patients the doctors can treat.

If receptionists send patients into examination rooms faster than doctors can process them, the hospital fills with people who have already left the waiting room but haven't received treatment.

This resembles what happens when RabbitMQ delivers messages to consumers.

The message may no longer appear in the queue's *ready* count.

But it may still be waiting inside a consumer process or undergoing processing.

RabbitMQ distinguishes messages ready for delivery from messages already delivered but awaiting acknowledgment.

These are different states.

### Visual anchor 1 — The two places where work waits

```text
Publisher
    |
    v
RabbitMQ queue
    |
    ├── READY
    |   Waiting to be delivered
    |
    v
Consumer
    |
    ├── UNACKNOWLEDGED
    |   Delivered, not yet completed
    |
    v
Business operation
    |
    v
Acknowledgment
```

A queue with ten thousand ready messages is obviously backlogged.

But a queue with zero ready messages and ten thousand unacknowledged deliveries may also be unhealthy.

Those messages have been handed out.

They haven't necessarily been completed.

**Delivery is not completion.**

## 3. Acknowledgments Are the Boundary of Responsibility

Suppose a worker receives a job to scan a domain.

RabbitMQ delivers the message.

The worker starts the scanning process.

The scan takes twenty seconds.

Then the worker writes the results to MongoDB.

Only after successfully completing the required operation should the worker acknowledge the message.

The acknowledgment tells RabbitMQ that the delivery has been handled and no longer needs to remain outstanding.

What if the worker crashes before acknowledging?

RabbitMQ detects the closed connection or channel and makes the unacknowledged delivery available again.

Another worker can process it.

This is necessary for recovering from crashes.

But it creates an important possibility.

The first worker may have completed a business side effect before crashing.

Perhaps it already wrote results to MongoDB.

The second worker may execute the same job again.

The queue cannot know whether the first worker's database operation committed.

This is why acknowledgments do not automatically provide exactly-once business execution.

We explored that broader reliability problem in SE320-L03.

Here we are interested in how RabbitMQ represents the delivery and how to diagnose what happened.

## 4. Prefetch: How Much Work a Consumer Can Reserve

RabbitMQ has a mechanism called *prefetch*.

It limits the number of unacknowledged deliveries a consumer can have outstanding.

Suppose a consumer has a prefetch count of five.

RabbitMQ may deliver five messages before receiving any acknowledgment.

Once the consumer reaches that limit, RabbitMQ stops sending additional messages to it until outstanding deliveries are acknowledged.

This prevents unlimited delivery accumulation inside the consumer.

But there is a subtle distinction:

**Prefetch is not necessarily processing concurrency.**

A synchronous Python worker may process one callback at a time.

It can have five messages delivered and unacknowledged while actively processing only one.

The other four are waiting for the worker's callback loop.

A worker with prefetch twenty doesn't automatically perform twenty scans simultaneously.

### Visual anchor 2 — Prefetch versus execution

```text
Consumer prefetch = 5

Delivered messages:
  A  B  C  D  E

Actually executing:
  A

Waiting inside consumer:
  B  C  D  E

RabbitMQ sees:
  5 unacknowledged deliveries
```

Now imagine a slow worker and a fast worker consuming from the same queue.

If the slow worker reserves many messages, those messages may remain unavailable to the fast worker while the slow worker processes them.

An excessively large prefetch can therefore affect fairness and waiting time.

The correct value depends on processing duration, resource usage, network latency, concurrency model, and queue type.

## 5. The Message That Refuses to Die

Now imagine a malformed job.

Its payload lacks a required field.

Every worker attempts to parse it and throws an exception.

The developer wrote the following failure behavior:

> If processing fails, reject the delivery and requeue it.

RabbitMQ puts the message back into the queue.

Another consumer receives it.

It fails again.

The consumer requeues it.

The cycle repeats.

Nothing about the payload changes.

The system performs the same unsuccessful operation over and over.

This is a **poison-message requeue loop**.

If redelivery happens immediately, the loop may consume CPU, network bandwidth, broker resources, and worker capacity.

A system can report an enormous delivery rate while completing almost no useful work.

### Visual anchor 3 — The requeue storm

```text
Poison message
      |
      v
Consumer receives
      |
      v
Processing fails
      |
      v
nack(requeue=true)
      |
      v
RabbitMQ requeues
      |
      v
Consumer receives again
      |
      +---- repeat indefinitely
```

The correct response depends on the failure.

A temporary database outage may justify a delayed retry.

An invalid payload may never succeed, no matter how often it is retried.

These failures should not receive identical treatment.

## 6. Dead-Letter Queues Are a Quarantine Area

Imagine a hospital laboratory receiving a damaged sample.

Rather than passing it repeatedly between technicians, the laboratory sets it aside for investigation.

RabbitMQ can do something similar using dead-letter exchanges.

When a consumer rejects a message without requeueing it, RabbitMQ can route the message to a configured dead-letter exchange.

The exchange can then route it to a dead-letter queue.

Now the problematic message is separated from normal work.

An operator can investigate it without allowing it to consume the main worker fleet indefinitely.

A dead-letter queue doesn't automatically repair the message.

It preserves a failure artifact for later examination or controlled recovery.

Nor does rejection without requeueing guarantee preservation. If no suitable dead-letter route exists, the message may be discarded.

The topology must be configured correctly.

## 7. More Workers Can Reduce Successful Throughput

Return to our overloaded scanning system.

Eight workers submit results to MongoDB.

The database handles their write workload comfortably.

The team scales to thirty-two workers.

Now more jobs execute concurrently.

More scans complete at approximately the same time.

More workers attempt database writes.

The database connection pool saturates.

Operations wait, time out, and retry.

The total number of attempts rises, while the number of successful completions may stagnate or decline.

Increasing worker count has amplified pressure on the bottleneck.

The important quantity is not consumers, deliveries, or attempts.

It is **successful business completions per unit time**.

### The throughput distinction

Imagine two configurations:

Configuration A performs forty successful scans per second with very few retries.

Configuration B attempts one hundred scans per second but completes only thirty because of downstream failures and retries.

Configuration B looks busier.

Configuration A delivers more useful work.

A successful optimization must be evaluated at the business-operation boundary.

## 8. The Four Questions Behind a RabbitMQ Incident

When a queue-based system behaves badly, begin with four questions.

**First: Where is the work waiting?**

Is it ready in RabbitMQ, delivered but unacknowledged, waiting for a database connection, or blocked inside a worker?

**Second: Is work being completed or repeated?**

Compare successful completion rate with delivery and redelivery rates.

**Third: What limits concurrency?**

Inspect prefetch, worker execution capacity, database pools, external APIs, and downstream rate limits.

**Fourth: What happens when processing fails?**

Does the consumer acknowledge, requeue, delay, dead-letter, crash, or silently discard the message?

### A tiny comprehension check

A RabbitMQ queue reports zero ready messages and 500 unacknowledged messages.

Can you conclude the queue has finished its work?

No.

Those messages have been delivered but are not yet acknowledged.

Now suppose the team doubles the number of consumers, while every consumer depends on a database pool that is already saturated.

Should throughput necessarily double?

No.

The database may become the limiting resource, and additional consumers may simply increase contention.

These distinctions form the foundation of RabbitMQ production forensics.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 9. Understand the Actual RabbitMQ Delivery Path

SE320-L03 introduced queues, retries, idempotency, and asynchronous workflows using a broader architectural perspective.

This lecture focuses on the RabbitMQ mechanisms that determine delivery behavior.

A typical AMQP 0-9-1 arrangement contains publishers, exchanges, queues, and consumers.

A publisher sends a message to an exchange.

The exchange routes the message to suitable queues according to bindings and routing rules.

A consumer subscribes to a queue.

RabbitMQ delivers messages over a channel.

The consumer processes each delivery and acknowledges or rejects it.

These relationships are important because publishing, routing, delivery, and processing are separate events.

### 9.1 Publishing does not mean a worker processed the message

A publisher can successfully send a message while no consumer is currently available.

The message may remain ready in the queue.

A consumer can receive a message while its business operation is still unfinished.

The business operation can finish while the acknowledgment hasn't yet reached RabbitMQ.

A database transaction can commit while the worker crashes before acknowledging.

Each boundary has different failure semantics.

### 9.2 Publisher confirms and consumer acknowledgments are different

Publisher confirms help a publisher establish that RabbitMQ has accepted responsibility for a published message under the relevant queue and durability semantics.

Consumer acknowledgments tell RabbitMQ that a delivered message has been handled.

A publisher confirm does not mean a consumer completed the work.

A consumer acknowledgment does not retroactively prove that the original publication was safely persisted.

A reliable workflow may need both mechanisms, alongside appropriate queue durability and message persistence.

## 10. Ready, Unacknowledged, and Total Messages

RabbitMQ's management system distinguishes several queue measurements.

`messages_ready` represents messages ready to be delivered.

`messages_unacknowledged` represents messages already delivered to consumers but not yet acknowledged.

`messages` represents the combined total.

These numbers answer different operational questions.

### 10.1 High ready count

A growing ready count suggests messages are arriving faster than available consumers can accept them, or that consumption has stopped or slowed.

Possible causes include insufficient consumer capacity, unavailable consumers, broker flow restrictions, downstream bottlenecks, or a sudden workload burst.

The count alone doesn't identify the cause.

### 10.2 High unacknowledged count

A high unacknowledged count indicates many deliveries are outstanding.

Some may be actively processing.

Others may be buffered inside consumers because of prefetch.

Some workers may be stuck waiting for external systems.

A large unacknowledged count is not automatically proof of failure.

For a large worker fleet, it may be normal.

The interpretation depends on processing times, prefetch settings, and the expected number of concurrent operations.

### 10.3 Queue depth is not business backlog by itself

A queue can appear mostly empty because messages have moved into consumers.

Yet the real processing backlog may remain large.

For capacity planning, consider ready and unacknowledged messages, their age, and the number of tasks successfully completed.

## 11. Acknowledgment Semantics

RabbitMQ supports automatic and manual consumer acknowledgment modes.

In automatic acknowledgment mode, RabbitMQ considers a message handled when it is delivered according to the protocol's semantics.

The broker does not wait for application-level processing success.

This can be appropriate for certain low-value or disposable workloads.

For jobs that must survive worker crashes, manual acknowledgments are usually more suitable.

### 11.1 Positive acknowledgment

A consumer sends `basic.ack` when the required processing has completed.

RabbitMQ can then remove the outstanding delivery from its responsibility.

The acknowledgment should correspond to the application's actual success boundary.

### 11.2 Negative acknowledgment

RabbitMQ supports `basic.nack` and `basic.reject`.

A negative acknowledgment can request requeueing or permanent removal from the current queue.

If requeueing is disabled and a dead-letter exchange is configured, RabbitMQ can route the message to that exchange.

Otherwise the message may be discarded.

### 11.3 Delivery tags are channel-scoped

Each delivered message carries a delivery tag.

The tag identifies the delivery within its channel.

An acknowledgment must be sent on the same channel that received the delivery.

Acknowledging on the wrong channel can produce an unknown-delivery-tag error and close the channel.

This matters when application code shares channels across asynchronous callbacks or attempts to acknowledge from a different connection.

### 11.4 Double acknowledgment is a protocol error

A worker should not acknowledge the same delivery twice.

Doing so can close the channel.

That channel closure may cause other unacknowledged deliveries on the channel to be requeued.

A local acknowledgment bug can therefore cause broader redelivery behavior.

## 12. The Crash Window

Consider a job that updates the database.

The worker receives the message.

It performs the database transaction.

The database commits.

Then the worker crashes before acknowledging RabbitMQ.

From the database's perspective, the operation succeeded.

From RabbitMQ's perspective, the delivery remains unacknowledged.

When the connection closes, RabbitMQ requeues the message.

Another worker receives it.

Now the business operation may execute twice.

This is the classic at-least-once processing problem.

The RabbitMQ-specific observation is that delivery recovery follows the channel and connection lifecycle.

### 12.1 What the redelivered flag means

RabbitMQ can set a message's `redelivered` flag when a delivery is being sent again.

This is evidence that the message has previously been delivered or attempted for delivery.

It does not prove the earlier worker completed its business operation.

Nor does a redelivered flag identify how many times the business operation ran.

A worker should not treat the flag as a complete idempotency mechanism.

### 12.2 Consumer disappearance isn't always detected instantly

If a worker process exits cleanly and its TCP connection closes, RabbitMQ can react to the closure.

If a host disappears or a network path fails silently, detection can take longer.

Heartbeats and connection timeouts influence the recovery behavior.

During that interval, messages may remain unacknowledged.

This is why worker failure detection and message recovery should be measured, not assumed instantaneous.

## 13. Prefetch Is a Delivery Window

RabbitMQ uses prefetch to limit outstanding unacknowledged deliveries.

For ordinary AMQP 0-9-1 consumption, RabbitMQ applies a non-global `basic.qos` prefetch count separately to each consumer.

This differs from the original AMQP interpretation of a shared channel-wide limit.

A prefetch count of zero means no explicit prefetch limit, subject to other queue-type limits.

### 13.1 A concrete example

Suppose one worker has prefetch five.

It receives five deliveries.

Until it acknowledges one of them, RabbitMQ need not send a sixth.

The worker might process those deliveries concurrently.

Or it might process them one at a time.

The broker cannot infer the worker's application-level execution concurrency from the prefetch count.

### 13.2 Prefetch is not a thread pool

In a synchronous worker, one callback may block until its job completes.

Prefetch twenty can still result in one job actively executing at a time.

The remaining delivered messages may wait in the client library.

Increasing prefetch alone does not create parallel processing.

To increase actual concurrent execution, the application needs an appropriate concurrency model: multiple worker processes, threads, tasks, or another controlled execution mechanism.

### 13.3 Large prefetch can cause unfair distribution

Imagine two consumers.

Consumer A is slow.

Consumer B is fast.

If A receives a large batch of unacknowledged deliveries, B cannot process those reserved messages until they return to the queue or A finishes them.

A smaller prefetch may distribute work more responsively.

However, a very small prefetch can reduce throughput when workers spend substantial time waiting for broker round trips.

There is no universally optimal value.

It must be tuned for the workload.

### 13.4 High prefetch also increases crash recovery work

If a worker holds many outstanding deliveries and crashes, those deliveries must be recovered and redistributed.

The more work held in flight, the larger the possible redelivery burst.

This can contribute to retries, duplicated execution, and recovery latency.

## 14. Consumer Concurrency and the Downstream Bottleneck

Suppose a worker spends 100 milliseconds on CPU work and 400 milliseconds waiting for MongoDB.

Its total service time is approximately 500 milliseconds.

One synchronous worker can process roughly two jobs per second under these simplified conditions.

Adding consumers initially increases throughput because the database has spare capacity.

But eventually the database reaches its concurrency limit.

Beyond that point, extra workers mostly increase the number of simultaneous requests competing for the same resource.

### 14.1 Throughput eventually plateaus

Imagine MongoDB can sustainably handle forty relevant writes per second.

The queue receives sixty jobs per second.

Even with unlimited workers, completed throughput cannot sustainably exceed the actual downstream capacity without changing the workload or increasing capacity.

A queue can buffer the difference temporarily.

But if arrivals remain at sixty per second while completions remain at forty, backlog grows by roughly twenty jobs per second.

### 14.2 Retries make the problem worse

Suppose overloaded database calls begin timing out.

Workers requeue their messages immediately.

The failed operations create additional attempts.

Those attempts compete with first-time work.

The database receives more traffic without delivering more successful completions.

This is retry amplification.

A system with too much concurrency can reduce successful throughput even as it increases the number of attempted operations.

### 14.3 The actual bottleneck may move

During a load test, throughput may initially be limited by worker CPU.

After increasing workers, the limiting resource might become database connections.

After improving the database, the limiting resource might become an external API's rate limit.

Performance engineering requires identifying the current bottleneck rather than assuming one component remains limiting forever.

## 15. Poison Messages and Immediate Requeue Loops

A poison message is one that repeatedly fails processing.

It may contain malformed data, violate a business invariant, reference a missing resource, or trigger a deterministic bug.

The failure isn't necessarily temporary.

A worker that immediately requeues every failure can repeatedly receive the same message.

RabbitMQ explicitly documents that such requeue/redelivery loops can consume significant CPU and network resources.

### 15.1 The misleading delivery rate

Suppose the same poison message is delivered one thousand times per second.

The broker's delivery metrics show substantial activity.

The workers produce errors rapidly.

But the successful business completion rate for that message is zero.

A monitoring system that celebrates delivery throughput without comparing acknowledgments and completions can misinterpret the incident.

### 15.2 Redelivery is not automatically a scheduled retry

`nack(requeue=true)` asks RabbitMQ to return the message to the queue.

It doesn't establish a five-second delay.

Depending on queue state and consumer availability, the message can become eligible for redelivery immediately.

If a transient dependency is unavailable, that can create a tight failure loop.

### 15.3 Classify failures before retrying

An invalid payload may deserve immediate dead-lettering.

A transient database error may deserve a delayed retry.

A business conflict may require special handling rather than blind repetition.

A timeout from an external payment provider may require checking the operation's authoritative state before retrying.

The failure classification determines the recovery strategy.

RabbitMQ doesn't know the business meaning of every exception.

## 16. Dead-Letter Exchanges and Queues

A dead-letter exchange, or DLX, receives messages that can no longer remain in their original queue under certain conditions.

Dead-lettering can occur when:

- A consumer rejects or negatively acknowledges a delivery without requeueing.
- A message expires due to its applicable TTL.
- A queue-length policy causes a message to be dropped.
- A quorum queue exceeds its configured delivery limit.

The dead-letter exchange then routes the message according to normal exchange rules.

A dead-letter queue is simply a queue bound to receive those messages.

### 16.1 Dead-lettering requires a valid route

If the configured dead-letter exchange doesn't exist or the message doesn't route to an appropriate queue, preservation is not guaranteed.

A dead-letter configuration must be tested.

Otherwise the team may believe it has quarantined failures while messages are actually disappearing.

### 16.2 Prefer policies for operational configuration

RabbitMQ recommends configuring dead-letter behavior through policies rather than hardcoded queue declaration arguments.

Policies can be modified without redeploying applications or recreating queues.

Hardcoded `x-arguments` are much harder to change after a queue exists.

The laboratory will use a policy for this reason.

### 16.3 Dead-lettering is another publish operation

Dead-lettering isn't magic movement between folders.

RabbitMQ republishes the message to the dead-letter exchange.

Like other publishing operations, that process has failure semantics.

In clustered environments, default at-most-once dead-lettering may not provide the delivery guarantees an application expects.

Quorum queues support more robust at-least-once dead-lettering configurations, with their own resource and availability considerations.

This is important for critical workloads where losing a dead-lettered message would be unacceptable.

## 17. Retry Topologies

A common retry design separates immediate work from delayed retries.

Suppose an API dependency is temporarily unavailable.

The worker rejects the message without immediate requeue.

The message enters a retry mechanism.

After an appropriate delay, it becomes eligible for another attempt.

If repeated attempts fail, the message eventually moves to a terminal dead-letter queue.

### 17.1 Why delay matters

A delayed retry gives the external dependency time to recover.

It also prevents a large population of failing messages from continuously hammering the same unavailable service.

Without delay, retries can amplify an outage.

### 17.2 TTL-based retry queues

A traditional RabbitMQ pattern uses a retry queue with message TTL and a dead-letter route back to the work queue.

This can implement delayed retry.

But it requires careful handling of routing, message expiration, ordering, and retry counts.

It may also introduce repeated republishing and potential message-loss considerations.

### 17.3 Newer quorum-queue features

Modern RabbitMQ quorum queues support broker-managed poison-message controls.

RabbitMQ 4.0 introduced a default delivery limit of twenty for quorum queues.

RabbitMQ 4.4 also documents native delayed retry support for quorum queues.

These features are version-specific and queue-type-specific.

A classic queue does not automatically inherit the same delivery-limit semantics.

When investigating a real system, verify the RabbitMQ version, queue type, policy configuration, and effective limits.

Do not assume all queues behave identically.

## 18. Classic Queues Versus Quorum Queues

RabbitMQ supports several queue types.

For ordinary work queues, classic and quorum queues are particularly relevant.

Classic queues provide familiar queue semantics and can be suitable for many workloads.

Quorum queues are replicated durable queues based on the Raft consensus algorithm.

They are designed for data safety and availability under appropriate cluster configurations.

### 18.1 Replication changes the operational cost

A quorum queue must coordinate its replicated state.

This adds resource and network costs compared with a simple single-node classic queue.

The trade-off is stronger replicated durability and availability properties when the cluster is appropriately configured.

### 18.2 Poison-message behavior differs

Quorum queues have built-in delivery-limit mechanisms.

Classic queues do not automatically provide the same retry ceiling.

This matters enormously when diagnosing endless requeue behavior.

A configuration that worked on a classic queue may behave differently after migration to a quorum queue.

### 18.3 The lab intentionally uses a classic queue

Our laboratory uses a disposable single-node RabbitMQ instance and a classic work queue.

This keeps the requeue and dead-letter behavior easy to observe.

It does not model the fault tolerance of a production quorum queue.

The production architecture decision requires separate reliability and capacity analysis.

## 19. Acknowledgment Timeouts and Stuck Consumers

Suppose a worker receives a message and then hangs indefinitely.

RabbitMQ continues waiting for an acknowledgment.

The delivery remains unacknowledged.

The worker may continue occupying a consumer slot and holding other resources.

RabbitMQ supports consumer acknowledgment timeout mechanisms that can close a channel when deliveries remain unacknowledged beyond configured limits.

When the channel closes, outstanding deliveries can be requeued.

### 19.1 The timeout is not a business cancellation

Closing a RabbitMQ channel doesn't necessarily stop the actual business operation.

The worker may have started an external process, sent an HTTP request, or initiated a database operation.

Those activities may continue independently.

RabbitMQ can redeliver the message while some previous side effect is still in progress.

This is another reason idempotency remains necessary.

### 19.2 Set timeouts according to real workloads

A scanning job that normally takes twenty minutes cannot use the same assumptions as a worker processing tiny JSON messages in milliseconds.

Timeouts should reflect the expected processing duration and the recovery requirements.

A timeout that's too short can cause unnecessary channel closures and redeliveries.

A timeout that's too long delays recovery from genuinely stuck workers.

## 20. Broker Health Signals

RabbitMQ's management interface and monitoring APIs expose queue and consumer metrics.

During an incident, the most useful measurements include:

Ready messages.

Unacknowledged messages.

Publishing rate.

Delivery rate.

Acknowledgment rate.

Redelivery rate.

Consumer count.

Consumer capacity.

Connection and channel counts.

Memory and disk alarms.

The important task is correlating these measurements with successful application work.

### 20.1 Consumer capacity

RabbitMQ's consumer-capacity metric estimates the proportion of time a queue can immediately deliver messages to consumers.

Low consumer capacity can indicate that the queue lacks available consumer credit or processing capacity.

But it doesn't automatically identify the downstream bottleneck.

A consumer may be unavailable because its prefetch window is full while it waits for a database connection.

### 20.2 Memory and disk alarms

RabbitMQ can raise resource alarms when memory or disk free-space thresholds are reached.

These alarms can block publishing connections to protect the broker.

A growing queue may therefore be a symptom of consumer limitations, resource alarms, or both.

Check broker-level health rather than focusing exclusively on application worker logs.

### 20.3 Queue depth without rates is incomplete

A queue contains ten thousand messages.

Is that alarming?

It depends.

If consumers drain five thousand per second and new work arrives slowly, the backlog may disappear quickly.

If arrivals exceed completions, the backlog may grow indefinitely.

You need rates and trends.

The queue depth is a snapshot.

The system's behavior is a process over time.

## 21. A Diagnostic Procedure for the Worker Fleet

Return to the cybersecurity scanning incident.

The queue grows.

The team scales workers.

The system becomes slower.

Let's reconstruct the investigation.

### Step 1 — Establish the business completion rate

How many scanning jobs complete successfully per second?

Do not substitute the broker's delivery rate.

### Step 2 — Compare arrivals and completions

Is work arriving faster than it completes?

Is the backlog growing steadily or only during bursts?

### Step 3 — Inspect ready and unacknowledged counts

Are messages waiting at the broker?

Or are consumers holding large numbers of unacknowledged deliveries?

### Step 4 — Inspect prefetch and actual concurrency

What prefetch count does each consumer use?

How many jobs does each worker execute concurrently?

How many worker processes exist?

What is the aggregate potential in-flight workload?

### Step 5 — Inspect failure and redelivery rates

Are messages failing once and moving to a dead-letter queue?

Or are they immediately requeued and retried repeatedly?

### Step 6 — Inspect downstream capacity

Check MongoDB connections, external API rate limits, CPU, memory, I/O, and application pool waits.

More consumers may be driving a downstream bottleneck.

### Step 7 — Identify poison-message patterns

Are the same message IDs or job IDs failing repeatedly?

Are failure payloads identical?

Do retries have meaningful delay and limits?

### Step 8 — Form a causal explanation

For example:

> Scaling workers increased concurrent MongoDB writes beyond the available connection capacity. Database timeouts caused immediate RabbitMQ requeues, increasing repeated attempts. The broker's delivery rate rose while successful scanning throughput stagnated.

This explanation connects the symptoms.

### Step 9 — Apply a focused correction

Possible changes include reducing worker concurrency, tuning prefetch, introducing bounded delayed retries, routing permanent failures to a dead-letter queue, or increasing downstream capacity where justified.

Don't change everything at once.

### Step 10 — Verify recovery

The successful completion rate should improve.

Redelivery amplification should decrease.

Database pressure should return to sustainable levels.

The backlog should drain.

Poison messages should no longer circulate indefinitely.

## 22. Why More Concurrency Is Not Always More Throughput

We can express the queue's behavior using a simple throughput relationship.

If jobs arrive at rate λ and complete at rate μ, then backlog grows when arrivals sustainably exceed completions.

Adding consumers can increase μ only while the downstream system can support the additional work.

Once a shared dependency saturates, adding workers may increase queueing and retry overhead instead.

### 22.1 Little's Law as a useful intuition

For a stable system, Little's Law relates average work in the system, throughput, and time spent in the system.

More in-flight work is not automatically useful.

If throughput stays constant while the number of in-flight jobs rises, average time in the system increases.

This is exactly what happens when too many workers compete for the same saturated database.

### 22.2 Backpressure is a control mechanism

A queue buffers bursts.

But buffering doesn't create unlimited downstream capacity.

A sustainable design must eventually limit intake, regulate worker concurrency, or increase the actual bottleneck's capacity.

Retries also need their own bounds.

Without such controls, the system can convert a temporary overload into a self-sustaining failure loop.

## 23. Production Incident: QUEUE-01

Let's summarize the central case.

The manager publishes scanning jobs to RabbitMQ.

Workers consume them and write results to MongoDB.

The operations team sees a growing queue and scales workers.

Throughput gets worse.

The investigation reveals three interacting mechanisms.

First, worker concurrency exceeds the sustainable database write capacity.

Second, large prefetch windows allow workers to accumulate unacknowledged deliveries.

Third, transient database errors trigger immediate requeues.

Those requeues generate additional attempts.

The database receives even more pressure.

The apparent backlog may move from RabbitMQ's ready state into unacknowledged deliveries and database waits.

The queue is not the only queue in the system.

There is another queue at the database connection pool.

And potentially another inside the database itself.

### The wrong fix

Adding more workers without increasing the actual bottleneck's capacity or regulating concurrency can make the incident worse.

### The better diagnosis

Measure successful work and downstream saturation.

Reduce or bound concurrency.

Separate transient and permanent failures.

Introduce delayed, bounded retry behavior.

Tune prefetch based on the actual worker execution model.

Then verify the effect under representative load.

This is the practical judgment the lecture is designed to develop.

---

# The Oral Examination

Answer aloud before reading the solutions.

## Question 1 — Ready Versus Unacknowledged

A queue has zero ready messages and 500 unacknowledged messages.

Is the work complete?

What should you investigate?

## Question 2 — Prefetch

A synchronous worker uses prefetch twenty.

How many messages can RabbitMQ deliver before acknowledgments arrive?

How many jobs is the worker necessarily executing concurrently?

## Question 3 — Worker Crash

A consumer writes a result to MongoDB, then crashes before acknowledging RabbitMQ.

What happens to the message?

What correctness risk remains?

## Question 4 — Poison Message

A message has invalid JSON.

The worker immediately uses `nack(requeue=true)`.

Why might this create an expensive loop?

## Question 5 — Dead-Lettering

What happens when a consumer rejects a message with requeue disabled?

What must be configured to preserve it in a dead-letter queue?

## Question 6 — Queue Type

A team migrates from classic queues to quorum queues.

What important differences might affect poison-message handling and delivery limits?

## Question 7 — The Scaling Failure

Eight workers complete forty jobs per second.

Thirty-two workers complete only thirty-five, while database timeouts multiply.

How could increasing concurrency reduce successful throughput?

## Question 8 — Broker Metrics

RabbitMQ reports a large delivery rate but a much smaller acknowledgment rate.

What hypotheses would you investigate?

## Question 9 — Acknowledgment Bugs

A developer attempts to acknowledge a delivery on a different channel.

What can happen?

Why might that trigger further redeliveries?

## Question 10 — Production Judgment

Your team proposes setting prefetch to one thousand and doubling workers to eliminate a growing backlog.

What evidence would you request before approving the change?

---

# Solutions and Discussion

## Solution 1 — Ready Versus Unacknowledged

No.

The messages have been delivered but not acknowledged.

Inspect worker processing state, prefetch, downstream waits, acknowledgments, and consumer health.

## Solution 2 — Prefetch

RabbitMQ may deliver up to twenty outstanding messages under the configured prefetch limit.

A synchronous worker may execute only one callback at a time.

Prefetch doesn't automatically create application concurrency.

## Solution 3 — Worker Crash

When RabbitMQ detects the connection or channel closure, the unacknowledged delivery is requeued.

Another worker may process it.

The business side effect may already have committed, so processing must tolerate duplication.

## Solution 4 — Poison Message

The same invalid message can be redelivered immediately and fail repeatedly.

This consumes broker and worker resources without making progress.

Permanent failures should normally be quarantined or otherwise handled through a bounded recovery policy.

## Solution 5 — Dead-Lettering

RabbitMQ may route the rejected message to a configured dead-letter exchange.

That exchange must have an appropriate route to a queue.

Without a suitable configuration, the message may be discarded.

## Solution 6 — Queue Type

Quorum queues provide replicated durable queue semantics and built-in poison-message handling.

RabbitMQ 4.0 and later default to a delivery limit of twenty for quorum queues.

Classic queues don't automatically have the same behavior.

Exact features depend on RabbitMQ version and configuration.

## Solution 7 — Scaling Failure

Additional workers may saturate the database or another downstream dependency.

Timeouts and retries create additional attempts, increasing load while reducing successful completions.

The bottleneck is downstream capacity, not merely worker count.

## Solution 8 — Delivery Versus Acknowledgment

Investigate long-running jobs, stuck consumers, high prefetch, worker crashes, requeues, and repeated delivery of poison messages.

Delivery activity does not establish business completion.

## Solution 9 — Acknowledgment Bug

Delivery tags are scoped to channels.

Acknowledging on the wrong channel can cause a protocol error and channel closure.

Other unacknowledged deliveries on that channel may then be requeued.

## Solution 10 — Production Judgment

Inspect ready and unacknowledged counts, successful completion rate, worker execution concurrency, processing duration, downstream capacity, redelivery rate, and memory usage.

A large prefetch could increase outstanding work without improving execution throughput.

Scaling should be justified through measured capacity.

---

# The Mental Model Worth Keeping

RabbitMQ coordinates delivery, not business success.

Ready messages are waiting at the broker.

Unacknowledged messages have been delivered but are not yet completed.

Prefetch limits outstanding deliveries, not necessarily execution concurrency.

Acknowledgments define when RabbitMQ can release responsibility.

Requeueing can recover failed work—or create a destructive retry loop.

Adding consumers can increase useful throughput only while downstream capacity remains available.

The central operational question is:

**Where is the work waiting, how much is actually completing, and which failure mechanism is creating repeated attempts?**

Diagnose those boundaries before scaling.

---

# Next Lecture — SE335-L03: The Asynchronous System Incident Studio

We've now investigated Redis cache failures and RabbitMQ worker behavior separately.

In production, those systems often fail together.

A cache expires.

The database receives additional work.

Workers begin timing out.

RabbitMQ requeues failed messages.

The database receives even more traffic.

The queue grows.

The operations team adds consumers.

The additional concurrency amplifies the original overload.

SE335-L03 will combine these mechanisms into one integrated incident.

You'll have to identify the initial trigger, distinguish causes from consequences, and design a recovery that avoids making the outage worse.

*The spoken lecture ends here. The following experiments are intended for independent investigation using an isolated RabbitMQ environment.*

---

# Optional Practical Lab — RabbitMQ Worker Failure Forensics

## Lab Contract

This lab deliberately creates worker crashes, poison-message redelivery, unacknowledged deliveries, and downstream overload.

Use only a disposable local RabbitMQ instance.

The experiments are designed for RabbitMQ 4.x and Python using Pika.

They do not establish production-grade reliability guarantees.

The required process is:

**Predict → Reproduce → Inspect → Diagnose → Correct → Verify → AI Review.**

Do not read the diagnostic notes until after your first independent attempt.

## Lab 1 — Start RabbitMQ

Run RabbitMQ with the management plugin.

```bash
docker run --name se335-rabbit \
  -p 5679:5672 \
  -p 15679:15672 \
  -d rabbitmq:4-management
```

Wait until RabbitMQ is ready.

```bash
docker exec se335-rabbit \
  rabbitmq-diagnostics -q ping
```

Open the management interface:

`http://localhost:15679`

For this local disposable container, use the default `guest` / `guest` credentials.

Do not expose this laboratory broker to the public internet.

### Install the Python client

Create a working directory and install Pika.

```bash
mkdir se335-rabbit-lab
cd se335-rabbit-lab

python -m venv .venv
source .venv/bin/activate

python -m pip install pika
```

On Windows, activate the virtual environment through the appropriate PowerShell or Command Prompt activation script.

## Lab 2 — Create the Queue Topology

The laboratory uses:

- One durable classic work queue.
- One direct dead-letter exchange.
- One durable dead-letter queue.
- A RabbitMQ policy connecting work-queue rejection to the dead-letter exchange.

Create `setup.py`:

```python
import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host="localhost",
        port=5679,
        credentials=pika.PlainCredentials("guest", "guest"),
    )
)

channel = connection.channel()

channel.exchange_declare(
    exchange="se335.dlx",
    exchange_type="direct",
    durable=True,
)

channel.queue_declare(
    queue="se335.dead",
    durable=True,
    arguments={"x-queue-type": "classic"},
)

channel.queue_bind(
    queue="se335.dead",
    exchange="se335.dlx",
    routing_key="dead",
)

channel.queue_declare(
    queue="se335.work",
    durable=True,
    arguments={"x-queue-type": "classic"},
)

connection.close()

print("Topology declared.")
```

Run:

```bash
python setup.py
```

Now configure a dead-letter policy.

```bash
docker exec se335-rabbit rabbitmqctl set_policy \
  se335_dead \
  '^se335\.work$' \
  '{"dead-letter-exchange":"se335.dlx","dead-letter-routing-key":"dead"}' \
  --apply-to queues
```

Inspect the policy:

```bash
docker exec se335-rabbit rabbitmqctl list_policies
```

### Why a policy?

RabbitMQ recommends policies over hardcoded dead-letter queue arguments because policies can be changed operationally without recreating application-declared queues.

The laboratory policy applies only to `se335.work`.

### Verify the topology

In the management interface, inspect:

`se335.work`

`se335.dead`

And the exchange:

`se335.dlx`

Confirm that the dead-letter exchange exists and that the dead-letter queue is bound using the routing key `dead`.

---

# Lab 3 — Publish Persistent Jobs

Create `producer.py`.

The producer sends JSON jobs to the work queue using a confirm channel.

The `mandatory` flag helps detect unroutable publications.

```python
import json
import sys
import pika

count = int(sys.argv[1]) if len(sys.argv) > 1 else 50
include_poison = "--poison" in sys.argv

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host="localhost",
        port=5679,
        credentials=pika.PlainCredentials("guest", "guest"),
    )
)

channel = connection.channel()
channel.confirm_delivery()

jobs = [
    {
        "jobId": f"scan-{i}",
        "type": "scan",
        "asset": f"example-{i}.com",
    }
    for i in range(count)
]

if include_poison:
    jobs.insert(
        0,
        {
            "jobId": "poison-1",
            "type": "invalid",
            "asset": None,
        },
    )

for job in jobs:
    body = json.dumps(job).encode("utf-8")

    channel.basic_publish(
        exchange="",
        routing_key="se335.work",
        body=body,
        mandatory=True,
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
            message_id=job["jobId"],
        ),
    )

print(f"Published {len(jobs)} jobs.")

connection.close()
```

Run:

```bash
python producer.py 50
```

Inspect the work queue.

### Observe queue state

Use:

```bash
docker exec se335-rabbit rabbitmqctl list_queues \
  name messages_ready messages_unacknowledged consumers
```

Expected observation: the work queue has messages ready for consumption and no unacknowledged deliveries before a consumer starts.

### Important qualification

Durable queues, persistent messages, and publisher confirms address different parts of message safety.

None guarantees that a business operation executes exactly once.

---

# Lab 4 — A Worker with Manual Acknowledgments

Create `worker.py`.

The worker supports several experimental modes:

- `normal`: process and acknowledge.
- `slow`: process slowly.
- `crash`: simulate a process crash before acknowledgment.
- `poison`: repeatedly requeue an invalid job, then dead-letter it after a local attempt cap.
- `db`: call the optional constrained downstream service.

```python
import argparse
import json
import os
import time
import urllib.error
import urllib.request

import pika


parser = argparse.ArgumentParser()

parser.add_argument(
    "--mode",
    choices=["normal", "slow", "crash", "poison", "db"],
    default="normal",
)

parser.add_argument(
    "--prefetch",
    type=int,
    default=1,
)

parser.add_argument(
    "--seconds",
    type=float,
    default=0.3,
)

args = parser.parse_args()

if args.prefetch < 1:
    raise SystemExit("Use a positive prefetch for this lab.")

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host="localhost",
        port=5679,
        heartbeat=60,
        blocked_connection_timeout=30,
        credentials=pika.PlainCredentials("guest", "guest"),
    )
)

channel = connection.channel()

channel.basic_qos(
    prefetch_count=args.prefetch,
)

local_attempts = {}


def process_downstream(job):
    data = json.dumps(job).encode("utf-8")

    request = urllib.request.Request(
        "http://localhost:8099/process",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=5,
    ) as response:
        return response.read()


def callback(ch, method, properties, body):
    job = json.loads(body)
    job_id = job["jobId"]

    print(
        f"RECEIVED {job_id}",
        f"redelivered={method.redelivered}",
        flush=True,
    )

    if args.mode == "crash":
        print(
            f"SIMULATED SIDE EFFECT {job_id}",
            flush=True,
        )

        os._exit(17)

    if args.mode == "poison" and job["type"] == "invalid":
        attempts = local_attempts.get(job_id, 0) + 1
        local_attempts[job_id] = attempts

        print(
            f"POISON attempt={attempts}",
            flush=True,
        )

        if attempts < 6:
            ch.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=True,
            )
        else:
            ch.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=False,
            )

        return

    if job["type"] == "invalid":
        print(f"REJECT INVALID {job_id}", flush=True)

        ch.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=False,
        )
        return

    if args.mode == "db":
        try:
            process_downstream(job)
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
        ) as exc:
            print(f"DOWNSTREAM FAILURE {exc}", flush=True)

            # Simplified lab failure handling:
            # quarantine rather than immediate retry.
            ch.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=False,
            )
            return

    else:
        duration = (
            1.5 if args.mode == "slow"
            else args.seconds
        )

        time.sleep(duration)

    print(f"COMPLETED {job_id}", flush=True)

    ch.basic_ack(
        delivery_tag=method.delivery_tag,
    )


channel.basic_consume(
    queue="se335.work",
    on_message_callback=callback,
    auto_ack=False,
)

print(
    f"Worker started mode={args.mode}",
    f"prefetch={args.prefetch}",
    flush=True,
)

try:
    channel.start_consuming()
except KeyboardInterrupt:
    print("Stopping worker.")
    channel.stop_consuming()
finally:
    if connection.is_open:
        connection.close()
```

### Important limitations of this laboratory worker

The poison-message attempt counter is local to the process.

It does not survive crashes, reconnects, or distribution across several workers.

It is an intentional safety cap for demonstrating a requeue loop without making it endless.

It is **not** a production retry-attempt mechanism.

The worker also treats downstream failures as terminal for simplicity. Production systems should distinguish transient failures and route them through an appropriate bounded delayed-retry mechanism.

## Lab 5 — Observe Ready and Unacknowledged Messages

Publish sixty jobs:

```bash
python producer.py 60
```

Start a slow worker with prefetch twenty:

```bash
python worker.py \
  --mode slow \
  --prefetch 20
```

While it processes messages, inspect queue state.

```bash
docker exec se335-rabbit rabbitmqctl list_queues \
  name messages_ready messages_unacknowledged consumers
```

### Prediction

How many messages might be unacknowledged?

How many jobs is the synchronous Python callback actually executing at one time?

Does increasing prefetch make this worker process twenty jobs concurrently?

### Investigation

Watch the queue's ready and unacknowledged counts.

Then compare with a worker using prefetch one.

### Acceptance criteria

You can distinguish outstanding deliveries from actual execution concurrency.

You understand why high prefetch can reserve work without increasing processing throughput.

---

# Lab 6 — Slow Consumer, Fast Consumer

## Objective

Demonstrate that large prefetch values can affect work distribution.

First, ensure the previous queue is empty or purge only the dedicated laboratory work queue using the RabbitMQ management interface.

Publish sixty jobs:

```bash
python producer.py 60
```

Start a slow consumer:

```bash
python worker.py \
  --mode slow \
  --prefetch 20
```

Then start a faster consumer in another terminal:

```bash
python worker.py \
  --mode normal \
  --prefetch 1 \
  --seconds 0.1
```

### Tasks

Observe which messages the slow worker receives.

Inspect unacknowledged counts.

Does the slow worker reserve many jobs while processing one at a time?

Can the fast worker process jobs reserved by the slow worker?

### Second experiment

Repeat with both consumers using prefetch one.

Compare distribution and completion behavior.

### Acceptance criteria

You understand how prefetch affects fairness and in-flight work.

You don't claim that prefetch one is universally optimal.

---

# Lab 7 — Crash Before Acknowledgment

## Objective

Demonstrate redelivery when a worker crashes before acknowledging.

Clear the dedicated work queue.

Publish one job:

```bash
python producer.py 1
```

Start the crashing worker:

```bash
python worker.py \
  --mode crash \
  --prefetch 1
```

The process deliberately exits without acknowledging.

Inspect the queue.

Then start a normal worker:

```bash
python worker.py \
  --mode normal \
  --prefetch 1
```

### Expected behavior

The message can become available again when RabbitMQ detects that the original connection closed.

The second worker may receive it with `redelivered=true`.

### Investigation

The crashing worker printed a simulated business side effect.

The second worker processed the same job again.

What would happen if the first side effect were an actual payment charge or database write?

### Acceptance criteria

You understand the crash-before-ack window.

You can explain why message redelivery requires idempotent business processing.

You don't interpret the redelivered flag as a complete record of previous side effects.

---

# Lab 8 — A Bounded Poison-Message Requeue Loop

## Objective

Observe repeated delivery of a permanently invalid message.

The demonstration is intentionally bounded to six attempts.

Clear the laboratory work queue.

Publish one poison job:

```bash
python producer.py 0 --poison
```

Start the worker:

```bash
python worker.py \
  --mode poison \
  --prefetch 1
```

### Prediction

What happens after the first failed attempt?

Will the message return to the queue?

Will RabbitMQ introduce a delay automatically?

What happens on the sixth attempt?

### Investigation

Observe the repeated `POISON` logs.

Inspect the dead-letter queue afterward.

```bash
docker exec se335-rabbit rabbitmqctl list_queues \
  name messages_ready messages_unacknowledged consumers
```

The poison message should eventually be routed to `se335.dead`, assuming the dead-letter policy and binding are correctly configured.

### Important qualification

The local attempt counter is intentionally simplistic.

If the process restarts, the counter resets.

With multiple consumers, attempts are distributed across processes.

The example demonstrates a failure mechanism, not production-safe bounded retry logic.

### Acceptance criteria

You can explain the difference between immediate requeue and delayed retry.

You know how to verify that a dead-lettered message is actually preserved.

---

# Lab 9 — Constrained Downstream Service

## Objective

Demonstrate that more RabbitMQ consumers can exceed downstream capacity.

This experiment uses a small HTTP service to simulate a database or external dependency that supports only four concurrent operations.

It deliberately rejects overload instead of queueing unlimited requests.

Create `downstream.py`.

```python
import json
import threading
import time

from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)


capacity = threading.BoundedSemaphore(4)

metrics = {
    "active": 0,
    "completed": 0,
    "rejected": 0,
    "max_active": 0,
}

lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_error(404)
            return

        with lock:
            body = json.dumps(metrics).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/process":
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

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

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
    "Downstream service on localhost:8099",
    flush=True,
)

server.serve_forever()
```

Start the service:

```bash
python downstream.py
```

Inspect its counters:

`http://localhost:8099/metrics`

## Experiment A — Low concurrency

Clear the work and dead-letter queues in the disposable broker.

Restart the downstream service to reset its counters.

Publish forty jobs:

```bash
python producer.py 40
```

Start one worker in database mode:

```bash
python worker.py \
  --mode db \
  --prefetch 1
```

Observe successful completion and rejection counts.

## Experiment B — Higher concurrency

Repeat with a fresh set of forty jobs and reset downstream metrics.

Start four worker processes.

Each should use:

```bash
python worker.py \
  --mode db \
  --prefetch 1
```

Compare successful processing throughput.

## Experiment C — Excessive concurrency

Repeat again, this time with twelve worker processes.

The downstream service permits only four concurrent operations.

### Investigation

Does the service reject some requests?

Does RabbitMQ show dead-lettered messages?

Does delivery activity increase?

Does successful completion throughput necessarily improve?

### Important limitation

This is a synthetic downstream service with an explicit concurrency limit.

It demonstrates resource saturation and overload rejection.

It does not model all the behavior of PostgreSQL, MongoDB, or an external API under real production load.

The exact successful-throughput difference between configurations depends on scheduling and timing.

Do not claim that twelve workers must always be slower than four.

### Acceptance criteria

You can explain how additional consumers create downstream pressure.

You compare successful completions, rejected attempts, and total delivery activity.

You recognize that concurrency must be matched to downstream capacity.

---

# Lab 10 — QUEUE-01 Incident Report

## Starting Symptom

A worker fleet grows from eight to thirty-two consumers.

The queue continues growing.

Database timeouts increase.

RabbitMQ redelivery activity rises.

Successful job completions per second decrease.

### Required investigation

Prepare a short incident report with:

**Business requirement:** What are workers expected to accomplish?

**Observed symptoms:** Which queue, worker, and downstream metrics changed?

**Bottleneck hypothesis:** Which resource limits successful work?

**Prefetch diagnosis:** Are consumers holding excessive unacknowledged messages?

**Retry diagnosis:** Are failures producing immediate repeated attempts?

**Correction:** What configuration or application changes would reduce amplification?

**Verification:** Which metrics demonstrate recovery?

### Required defense

Your interviewer asks:

"The queue is getting longer. Why are you proposing fewer workers?"

Explain why reducing concurrency can improve successful throughput when the downstream dependency is overloaded.

Then describe what evidence would justify increasing worker count again.

---

# Lab Diagnostic Notes

**Do not read until after completing the independent investigations.**

## Lab 5 — Ready Versus Unacknowledged

A large prefetch allows RabbitMQ to deliver several messages before receiving acknowledgments.

The synchronous worker processes one callback at a time.

Additional deliveries may remain buffered in the client while appearing unacknowledged to the broker.

This demonstrates why outstanding deliveries and executing tasks are different quantities.

## Lab 6 — Consumer Fairness

A slow consumer with large prefetch may reserve many messages.

A fast consumer cannot process those messages while they remain outstanding on the slow consumer.

Smaller prefetch values can improve responsiveness and work distribution for this particular workload.

But very small prefetch values may reduce throughput for other workloads.

## Lab 7 — Crash and Redelivery

The worker exits without acknowledging.

RabbitMQ eventually detects the closed connection and requeues the outstanding delivery.

Another worker can receive the same message.

If the first worker completed a business side effect, that side effect may be repeated.

The correct production design requires appropriate idempotency or deduplication at the business boundary.

## Lab 8 — Poison Loop

The invalid message repeatedly fails.

Immediate `nack(requeue=true)` allows it to return rapidly.

The local attempt counter stops the experiment after six attempts and rejects the final delivery without requeueing.

The dead-letter policy routes it to `se335.dead`.

A production retry policy needs durable attempt tracking or suitable broker-managed mechanisms, meaningful delays, and operational monitoring.

## Lab 9 — Downstream Capacity

The synthetic service permits four concurrent operations.

Additional workers beyond that level can create rejected requests.

The broker may show substantial delivery activity while successful completions remain limited.

The lesson is not that four workers is a universal optimum.

It is that sustainable worker concurrency depends on downstream capacity and observed failure behavior.

## Lab 10 — Production Diagnosis

The worker fleet exceeded the downstream service's sustainable capacity.

Timeouts and immediate retries increased repeated attempts.

Large prefetch windows could also leave excessive work unacknowledged.

A defensible correction includes bounding concurrency, tuning prefetch, separating permanent failures from transient failures, introducing delayed bounded retries, and monitoring successful completions rather than delivery counts alone.

The final verification must show that the system completes useful work sustainably and that backlog growth and retry amplification are under control.

---

# Further Reading

1. **RabbitMQ — Consumer Acknowledgments and Publisher Confirms**  
   https://www.rabbitmq.com/docs/confirms

2. **RabbitMQ — Consumer Prefetch**  
   https://www.rabbitmq.com/docs/consumer-prefetch

3. **RabbitMQ — Dead Letter Exchanges**  
   https://www.rabbitmq.com/docs/dlx

4. **RabbitMQ — Quorum Queues**  
   https://www.rabbitmq.com/docs/quorum-queues

5. **RabbitMQ — Queues**  
   https://www.rabbitmq.com/docs/queues

6. **RabbitMQ — Reliability Guide**  
   https://www.rabbitmq.com/docs/reliability

7. **RabbitMQ — Monitoring**  
   https://www.rabbitmq.com/docs/monitoring

8. **RabbitMQ — Management Plugin**  
   https://www.rabbitmq.com/docs/management

9. **RabbitMQ — Resource Alarms**  
   https://www.rabbitmq.com/docs/alarms

10. **RabbitMQ — Consumer Timeouts**  
    https://www.rabbitmq.com/docs/consumers

11. **RabbitMQ — Production Checklist**  
    https://www.rabbitmq.com/docs/production-checklist

12. **Pika — Python RabbitMQ Client**  
    https://pika.readthedocs.io/

Cross-reference SE320-L03 for general asynchronous processing, SE335-L01 for Redis incident diagnosis, `production-cases/QUEUE-01.md` for the worker-scaling incident, and SE335-L03 for the integrated asynchronous-system studio.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text
SE335-L02 — RABBITMQ PRODUCTION FORENSICS
================================================

CORE PRINCIPLE
--------------
Delivery != business completion.

Measure successful business work,
not merely message delivery activity.

MESSAGE STATES
--------------
READY:
  waiting at broker

UNACKNOWLEDGED:
  delivered, awaiting ack

TOTAL:
  ready + unacknowledged

ACKNOWLEDGMENTS
---------------
basic.ack:
  positive acknowledgment

basic.nack / basic.reject:
  negative acknowledgment

requeue=true:
  return to queue, possibly immediately

requeue=false:
  dead-letter if configured,
  otherwise potentially discard

Delivery tags are channel-scoped.
Ack on same channel.

DOUBLE ACK
----------
Can produce unknown delivery tag
and channel closure.

Channel closure can requeue
other outstanding deliveries.

CRASH WINDOW
------------
1. Receive message.
2. Commit database operation.
3. Crash before ack.
4. RabbitMQ requeues.
5. Another consumer executes again.

At-least-once delivery requires
idempotent business processing.

REDELIVERED FLAG
----------------
Indicates previous delivery attempt.
Does not prove prior side effect.
Not a retry-count mechanism.

PREFETCH
--------
Limits outstanding unacked deliveries.

RabbitMQ normally applies non-global
prefetch separately per consumer.

Prefetch != execution concurrency.

Large prefetch:
- more reserved work
- possible unfairness
- more in-flight memory
- larger crash recovery burst

Small prefetch:
- greater delivery coordination
- can reduce throughput in some workloads

Tune with evidence.

POISON MESSAGE
--------------
Deterministic failure.
Immediate requeue can create
CPU/network/delivery storm.

Don't retry permanent failures forever.

DEAD LETTERING
--------------
DLX = dead-letter exchange.
DLQ = queue receiving routed failures.

Can occur from:
- nack/reject without requeue
- expiration
- length limit
- quorum delivery limit

Verify routing and preservation.

POLICIES
--------
Preferred for mutable DLX settings.

Hardcoded queue x-arguments
are harder to change later.

QUORUM QUEUES
-------------
Replicated durable queue type.

RabbitMQ 4.0+:
default delivery limit 20.

Modern versions have additional
poison and delayed retry features.

Classic queue behavior differs.

PUBLISHER CONFIRMS
------------------
Publisher knows broker accepted
responsibility under relevant semantics.

Not equivalent to consumer ack.
Not proof business operation completed.

RETRY STRATEGY
--------------
Classify error:
- permanent
- transient
- uncertain outcome

Use bounded attempts.
Use delay/backoff.
Avoid immediate retry storms.
Dead-letter terminal failures.

WORKER SCALING
--------------
Throughput constrained by bottleneck.

More consumers can increase:
- DB connections
- lock contention
- API requests
- timeouts
- retries

Measure successful completion rate.

QUEUE METRICS
-------------
messages_ready
messages_unacknowledged
messages
publish rate
delivery rate
ack rate
redelivery rate
consumer count
consumer capacity

BROKER HEALTH
-------------
Memory alarms
Disk alarms
Connections
Channels
File descriptors
Queue resource usage

BROKER VS DOWNSTREAM
--------------------
Ready backlog:
  broker waiting room

Unacked backlog:
  consumer responsibility

DB pool wait:
  application-side queue

DB lock wait:
  database coordination queue

A system may have several queues
even when only one is called RabbitMQ.

DIAGNOSTIC PROCEDURE
--------------------
1. Measure successful business completions.
2. Compare arrivals and completions.
3. Inspect ready/unacked.
4. Inspect prefetch and actual concurrency.
5. Inspect ack/requeue rates.
6. Identify poison patterns.
7. Check DB/API downstream capacity.
8. Identify causal amplification.
9. Apply focused correction.
10. Verify sustainable recovery.

RED FLAGS
---------
"More workers always means faster."
"Prefetch 100 means 100 parallel jobs."
"Zero ready messages means no backlog."
"Delivered means processed."
"Redelivered means duplicated side effect."
"Just nack and requeue every error."
"DLQ means the message was fixed."
"Publisher confirm means customer notified."
"High delivery rate means high throughput."
"Increase concurrency to fix timeouts."

MENTAL MODEL
------------
Where is work waiting?
Who currently owns the delivery?
What counts as completion?
What happens after failure?
What resource limits useful throughput?

NEXT
----
SE335-L03
The Asynchronous System Incident Studio
```
