---
id: SE320-L03
course: SE320
title: "Queues, Workers, and Asynchronous Workflows"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [BACK301-S06]
prev: SE320-L02
next: null
---

<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE325-L02, SE325-L03
Keep queue fundamentals, retries, duplicate delivery, and DLQs here.
When SE325 exists, cross-reference distributed scheduling / cron failure modes
and resumable bulk import-export jobs. Do not repeat those operational topics here.
-->

<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE335-L02, SE335-L03
When SE335 exists, cross-reference RabbitMQ-class worker forensics and the async
incident studio (QUEUE-01). Keep BullMQ-centric teaching here; do not regenerate
as a broker lab.
-->










# SE320 — Backend Services and Asynchronous Processing

## Lecture 03: Queues, Workers, and Asynchronous Workflows

*Why a background job can execute twice even when the queue is functioning correctly, and how to build workflows that survive crashes, retries, and unreliable dependencies.*

---

# 1. The Email That Was Sent Twice by a Perfectly Healthy Queue

At 14:32, a customer completes a hotel reservation. PostgreSQL commits the booking, the API returns `201 Created`, and a background job enters BullMQ to send the confirmation email.

A worker picks up the job and calls the email provider. The provider responds successfully, and the email is delivered.

The worker then prepares to mark the job as completed.

But at that precise moment, the process crashes.

Perhaps the container was terminated during deployment. Perhaps the Node.js process ran out of memory, or the virtual machine simply disappeared.

The email has already been sent. Unfortunately, BullMQ has not recorded that the job finished.

After the worker's processing lock expires, BullMQ detects that the job is no longer being actively maintained. It returns the job to the queue, where another worker eventually picks it up.

The second worker knows nothing about the successful email delivery. It sees an unfinished job and executes the handler:

```typescript
const worker = new Worker(
  "notifications",
  async job => {
    await emailProvider.send({
      to: job.data.email,
      template: "reservation-confirmation",
      reservationId: job.data.reservationId
    });
  },
  { connection }
);
```

The customer receives the same email twice.

BullMQ has not necessarily malfunctioned. The Redis server is healthy, the workers are healthy, and the queue is doing exactly what a recoverable job-processing system is supposed to do: **recover work whose completion was never established**.

The real problem lies in an uncomfortable distinction.

The worker performed the business effect, but the queue never learned that it did.

And this leads to one of the central principles of asynchronous engineering:

**Executing a job is not the same thing as recording that it was executed. Neither is necessarily the same as completing its business effect.**

The spaces between those three events are where some of the most interesting production failures occur.

---

# 2. Why We Introduce Queues

Consider a reservation API that performs the following operations synchronously:

```text
POST /reservations
        |
        +-- Validate reservation
        +-- Allocate inventory
        +-- Commit database transaction
        +-- Send email
        +-- Generate invoice PDF
        +-- Synchronize CRM
        +-- Update analytics
        |
        v
HTTP response
```

Even if the database work takes only 80 milliseconds, the other operations might require several seconds. The request remains open while multiple external systems complete work that may not be necessary to establish the reservation's validity.

Worse, the customer experiences failures in those secondary systems as failures of the entire booking operation.

A more useful arrangement separates the critical operation from its consequences:

```text
                  HTTP REQUEST
                       |
                       v
              Reservation Service
                       |
                       v
                Commit Booking
                       |
                       v
                 HTTP RESPONSE

                       |
                  Durable Work
                       |
                       v
                 Job Queue
                       |
            +----------+----------+
            |          |          |
            v          v          v
          Email      Invoice     CRM Sync
          Worker     Worker      Worker
```

A queue provides a boundary between producing work and executing it. Producers submit jobs, while consumers—usually called workers—retrieve and process them independently.

That separation provides several benefits. The API no longer waits for every secondary operation, workers can scale independently, failures can be retried, and sudden traffic bursts can be absorbed as pending work.

But moving work into a queue changes its execution contract.

Instead of promising that the requested work is complete before returning, the application may promise only that the work has been durably accepted for later processing.

These are different outcomes.

### When should an operation be asynchronous?

A useful question is whether the result of an operation is required before the caller can receive a truthful response.

For example, if the customer must secure inventory before a reservation can be confirmed, inventory allocation belongs in the critical booking path. Sending a confirmation email usually doesn't.

An API that initiates a long-running report might return:

```http
HTTP/1.1 202 Accepted
Content-Type: application/json

{
  "jobId": "report-842",
  "status": "pending"
}
```

The client can later retrieve the report's status and eventually download it.

By contrast, a reservation API might return `201 Created` after committing the actual reservation, while separately scheduling its notification.

The queue is therefore not merely a performance optimization. It establishes a boundary between **work already completed** and **work the system has accepted responsibility for completing**.

---

# 3. The Anatomy of a BullMQ Job

Let's examine the mechanism using BullMQ, which builds job queues on Redis.

A producer creates a queue and submits a job:

```typescript
import { Queue } from "bullmq";

const notifications = new Queue("notifications", {
  connection: { host: "localhost", port: 6379 }
});

await notifications.add(
  "send-confirmation",
  {
    reservationId: "R-10842",
    email: "customer@example.com"
  }
);
```

A worker processes jobs from that queue:

```typescript
import { Worker } from "bullmq";

const worker = new Worker(
  "notifications",
  async job => {
    await sendConfirmation(job.data);
  },
  {
    connection: { host: "localhost", port: 6379 }
  }
);
```

Underneath these few lines, BullMQ coordinates job records, waiting lists, active processing, delayed work, failures, and completion state using Redis data structures and atomic operations.

A simplified lifecycle looks like this:

```text
                  PRODUCER
                      |
                      v
                   WAITING
                      |
                Worker claims
                      |
                      v
                   ACTIVE
                  /      \
                 /        \
             Success     Failure
               |            |
               v            +----> Retry / Delay
           COMPLETED        |            |
                            |            v
                            |          WAITING
                            |
                            +----> FAILED
```

Jobs may also be delayed, prioritized, paused, or waiting for dependencies. The diagram captures the basic processing path rather than every possible state transition.

When a worker begins processing a job, BullMQ establishes a processing lock so another worker does not normally claim the same active job. The worker renews that lock while work continues.

Upon successful completion, BullMQ records the completed state. If the processor throws an error, the job can be failed or retried according to its configuration.

But an active job is not permanently owned by a particular process.

If its worker disappears or stops renewing the lock, BullMQ must eventually allow recovery.

Otherwise, one crashed process could leave work stuck forever.

And that's how the duplicate email becomes possible.

---

# 4. The Crash Window That Changes Everything

Let's examine the sequence more precisely.

```text
TIME       WORKER A                       BULLMQ
────────────────────────────────────────────────────────

T1         Claims job                     Job becomes active

T2         Calls email provider           Job remains active

T3         Provider sends email           Job remains active

T4         Worker receives success        Job remains active

T5         PROCESS CRASHES                Job still appears active

T6                                         Lock expires

T7                                         Stalled-job recovery

T8                                         Job returns to waiting

T9         Worker B claims job            Job becomes active

T10        Provider sends email again

T11        Worker B finishes              Job becomes completed
```

From the queue's perspective, Worker A never established completion. Reprocessing is therefore a reasonable recovery action.

BullMQ's stalled-job mechanism also handles situations where a worker remains alive but cannot renew its lock. A CPU-intensive processor that blocks the Node.js event loop for too long can produce this behavior.

Importantly, a *stalled job* is not a permanent job state in BullMQ. It's a recovery event that can result in a job returning to waiting or eventually failing after too many stalls.

There is another subtle case: Worker A can lose its lock without immediately stopping its own JavaScript execution. Another worker may then acquire the job while the original process is still performing external work.

This creates the possibility of overlapping execution attempts.

Extending a lock duration may reduce certain accidental stalls, but it delays recovery when a worker genuinely crashes. It also doesn't eliminate the fundamental uncertainty around external side effects.

**A queue processing lock coordinates job ownership inside the queue. It cannot undo work already performed in an external system.**

The distinction takes us into delivery guarantees.

---

# 5. At-Most-Once, At-Least-Once, and Exactly-Once

Distributed messaging systems are frequently described using three delivery models.

These terms require care because message delivery, handler execution, and business effects are not interchangeable.

| Model | Central promise | Main trade-off |
|---|---|---|
| At-most-once | Work isn't deliberately redelivered after an uncertain attempt | Some work may be lost |
| At-least-once | Unfinished work can be delivered again | Duplicates are possible |
| Exactly-once effect | A particular business effect happens once | Requires additional coordination |

Imagine a worker receiving a message.

### At-most-once

The system might remove or acknowledge the message before executing the handler.

If the worker crashes immediately afterward, the work is lost.

But the broker doesn't retry that message.

This can be acceptable for disposable telemetry or information whose loss has little consequence.

### At-least-once

The system retains responsibility for unfinished work and allows redelivery after failures.

This is broadly the recovery-oriented model relevant to BullMQ workers.

It reduces the chance that transient worker failures permanently abandon jobs, assuming the queue itself is durably maintained.

But the worker must tolerate duplicate execution attempts.

### Exactly-once

This term is especially dangerous because different technologies use it to describe different guarantees.

A broker may prevent certain duplicate message transitions or provide transactional processing within its own ecosystem. That does not automatically guarantee that an email provider sends exactly one email or that a payment gateway charges exactly once.

Consider a job that does two things:

```typescript
await paymentProvider.capture(paymentId);
await markJobComplete();
```

These operations belong to different systems.

Unless they participate in an appropriate shared protocol, a crash can occur between them.

The worker may not know whether capture succeeded.

Therefore, exactly-once **business effects** generally require mechanisms such as idempotency, durable operation identities, provider-side deduplication, or reconciliation.

Sometimes true exactly-once external effects are impossible to guarantee with the available provider interface.

The useful engineering objective is not to make vague exactly-once claims. It's to define what duplicates are acceptable, what side effects must be unique, and which component enforces that uniqueness.

---

# 6. Idempotency: Making Repetition Harmless

A mathematical operation is idempotent when applying it more than once has the same effect as applying it once.

Setting an order's status to `confirmed` can be idempotent:

```sql
UPDATE orders
SET status = 'confirmed'
WHERE id = 10842;
```

Repeating the assignment leaves the same final status.

Incrementing a balance is different:

```sql
UPDATE accounts
SET balance = balance + 100
WHERE id = 42;
```

Executing this twice changes the balance twice.

The same distinction applies to background jobs.

Sending the same confirmation email twice might be annoying. Capturing the same payment twice may be financially serious.

### The business operation needs an identity

Suppose we have a job to issue a refund:

```json
{
  "refundId": "refund-9281",
  "paymentId": "payment-481",
  "amountMinor": 5000
}
```

The important identifier is not necessarily the queue's generated job ID.

It's `refund-9281`, which identifies the underlying business operation.

If a worker receives the same refund operation twice, it should recognize that both executions refer to the same intended refund.

A simple database-backed pattern uses a unique record of processed operations:

```sql
CREATE TABLE processed_operations (
  operation_id TEXT PRIMARY KEY,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

For a purely PostgreSQL-local side effect, the worker can perform the deduplication and business update in one transaction:

```sql
BEGIN;

INSERT INTO processed_operations (operation_id)
VALUES ('refund-9281')
ON CONFLICT DO NOTHING
RETURNING operation_id;
```

If the insert returns a row, this transaction has claimed a new operation. It can perform the relevant database changes and commit.

If no row is returned, an already committed operation with that identity exists, so the worker should not apply the effect again.

For example, the following ledger entry could be inserted in the same transaction:

```sql
INSERT INTO ledger_entries (
  operation_id,
  account_id,
  amount_minor
)
VALUES (
  'refund-9281',
  42,
  5000
);

COMMIT;
```

Assume appropriate uniqueness and business constraints on the ledger table as well.

If the transaction rolls back, neither the marker nor the ledger entry is committed.

This creates an atomic boundary around the local business effect.

### The external side-effect trap

Now replace the ledger insert with:

```typescript
await externalPaymentProvider.issueRefund(...);
```

Our database transaction no longer covers the full operation.

If we mark the refund processed before calling the provider, a crash may cause us to skip a refund that never happened.

If we call the provider before recording success, a crash may cause the refund to execute twice.

This is the same fundamental uncertainty from our opening incident.

An external provider that supports stable idempotency keys can help. We submit the same refund operation identity on every retry, and the provider enforces its documented deduplication behavior.

Without provider support, we may need to query the provider for an existing refund or reconcile its records against our own.

**Idempotency must be enforced where the business effect actually occurs, or through a protocol that reliably coordinates that effect.**

A local `processed = true` flag is not a universal solution.

---

# 7. BullMQ Job IDs Are Not a Substitute for Business Idempotency

BullMQ lets you provide a custom job identifier:

```typescript
await queue.add(
  "send-confirmation",
  { reservationId: "R-10842" },
  {
    jobId: "confirmation-R-10842"
  }
);
```

If a job with the same identifier already exists in that queue, BullMQ can reject the duplicate addition.

This is useful for avoiding redundant enqueue operations.

But what happens after the original job is removed?

For example:

```typescript
{
  removeOnComplete: true
}
```

Once the job has been removed, its ID no longer prevents a future job with the same identifier from being added.

More importantly, a unique job ID doesn't prevent the *same job* from being processed again after a stall.

These are two different problems:

**Enqueue deduplication** prevents certain duplicate job records.

**Processing idempotency** makes repeated execution attempts safe.

BullMQ also provides more sophisticated deduplication capabilities, including mechanisms for collapsing repeated work and retaining the latest request in some situations.

Those features are valuable for tasks such as synchronizing a profile or refreshing cached information.

But none of them should be mistaken for a general guarantee that an external payment or email operation can only occur once.

In a reliable system, a queue job ID usually serves a technical purpose, while a stable business operation ID serves a correctness purpose.

Sometimes they're deliberately derived from the same identifier. Their guarantees remain different.

---

# 8. The Dual-Write Problem Returns

Remember our reservation service from earlier sessions.

A booking transaction commits successfully, and then the application adds a notification job:

```typescript
await reservationRepository.save(reservation);

await notificationQueue.add(
  "send-confirmation",
  { reservationId: reservation.id }
);
```

What happens if PostgreSQL succeeds but Redis is unavailable?

The reservation exists, but the notification job was never accepted.

Reversing the operations doesn't solve the problem.

If Redis accepts the job first and the database transaction later fails, the worker may attempt to send confirmation for a nonexistent reservation.

We have two independent state changes:

```text
Write A: PostgreSQL reservation
Write B: Redis job
```

There is no shared atomic transaction spanning ordinary PostgreSQL and Redis operations.

This is the **dual-write problem**.

### The transactional outbox

One common solution is to write the intended job into PostgreSQL as part of the reservation transaction.

```sql
BEGIN;

INSERT INTO reservations (...)
VALUES (...);

INSERT INTO outbox_events (
  event_id,
  event_type,
  aggregate_id,
  payload
)
VALUES (
  'evt-9281',
  'reservation.confirmed',
  'R-10842',
  '{"reservationId":"R-10842"}'
);

COMMIT;
```

Now the reservation and the notification intent are committed atomically.

If the transaction rolls back, neither exists.

A separate outbox publisher retrieves pending events and submits jobs to BullMQ.

```text
POSTGRESQL TRANSACTION
        |
        +-- Reservation record
        |
        +-- Outbox event
        |
        +-- COMMIT
                |
                v
          Outbox Publisher
                |
                v
              BullMQ
                |
                v
          Notification Worker
```

This solves an important problem: the committed business operation carries a durable record of the work it requires.

But it doesn't eliminate duplicate publication.

Imagine the outbox publisher sends the job to Redis successfully, then crashes before marking the event as published in PostgreSQL.

On restart, it sees the event as unpublished and sends it again.

So the outbox provides **recoverable, potentially repeated publication**, not automatic exactly-once effects.

Stable event IDs and appropriate consumer idempotency make this manageable.

### Multiple outbox publishers

At scale, several publishers may process events concurrently.

A common PostgreSQL approach uses bounded batches and `FOR UPDATE SKIP LOCKED` to let publishers claim different rows without waiting on one another's row locks.

However, care is needed with claim leases and failure recovery.

A publisher should not simply hold an open database transaction while performing arbitrarily slow external network calls.

One design records an event's claimed status and lease expiration, commits the claim, publishes the event, then records success. Expired claims can be recovered by another publisher.

The exact implementation depends on throughput and recovery requirements.

The important architectural distinction is that **the outbox records a durable obligation; the queue transports and schedules attempts to fulfill it**.

---

# 9. Retries: Not Every Failure Deserves Another Attempt

Suppose a notification worker calls an email provider, and the call fails.

Should BullMQ retry?

Sometimes.

Consider four failures:

| Failure | Sensible response |
|---|---|
| Temporary network interruption | Retry |
| Provider rate limit | Retry after appropriate delay |
| Invalid email address | Usually permanent failure |
| Unknown outcome after timeout | Investigate or retry idempotently |

Automatically retrying every exception can be disastrous.

An invalid email address doesn't become valid because we submit it six more times.

A missing authorization credential may require configuration repair rather than immediate repetition.

And an ambiguous payment timeout cannot safely be interpreted as permission to create a new payment operation.

### BullMQ attempts and backoff

BullMQ supports automatic retries:

```typescript
await queue.add(
  "send-confirmation",
  {
    reservationId: "R-10842"
  },
  {
    attempts: 5,
    backoff: {
      type: "exponential",
      delay: 1000,
      jitter: 0.5
    }
  }
);
```

Here, `attempts: 5` means at most five ordinary attempts in the configured retry mechanism, including the initial attempt.

Exponential backoff increases the delay between failures. Jitter introduces randomness so many failing jobs don't all retry simultaneously.

Without a backoff strategy, rapidly failing jobs may retry too aggressively.

### Why exponential backoff matters

Imagine an external provider suffers a two-minute outage.

You have 50,000 pending notification jobs.

If all workers retry every failed job immediately, your system may bombard the unavailable provider with even more traffic.

That increases queue activity, consumes resources, and can make recovery harder.

Exponential backoff gradually spaces retries, giving the dependency time to recover.

Jitter reduces synchronized retry waves.

But retries should also respect business deadlines. A hotel confirmation email delayed by five minutes may still be useful; an offer that expires in thirty seconds may not be.

A good retry policy therefore has three dimensions:

- Which failures are transient?
- How many attempts or how much elapsed time is acceptable?
- What happens when retries are exhausted?

That final question leads us to poison messages and dead-letter queues.

---

# 10. Failed Jobs, Poison Messages, and Dead-Letter Queues

Imagine a worker processing reservation notifications.

Most jobs complete successfully, but one repeatedly crashes the processor because its payload contains a malformed template structure.

The job is retried five times and fails every time.

What should happen next?

The job should not endlessly consume resources.

A **poison message** is a message that repeatedly fails because of its contents, processor behavior, or an incompatibility that cannot be resolved through ordinary retries.

Queues need a terminal failure policy.

BullMQ can retain failed jobs in its failed set, subject to configured retention. It doesn't automatically create a conventional separate dead-letter queue for every exhausted job.

If your architecture requires one, you can implement a process that transfers terminally failed work to a dedicated queue or durable failure store.

A dead-letter record might include:

```json
{
  "operationId": "notification-R-10842",
  "reason": "INVALID_TEMPLATE_DATA",
  "attempts": 5,
  "lastErrorAt": "2026-10-25T14:32:00Z"
}
```

The purpose isn't merely to archive failures.

It's to make them inspectable and recoverable.

An operator may repair the underlying problem and replay the original operation.

But replaying work safely requires idempotency, because previous attempts may have partially completed.

### Permanent failure doesn't always mean business failure

Suppose the customer reservation is confirmed, but its confirmation email permanently fails.

The booking should normally remain confirmed.

The notification has failed; the reservation has not.

This is why business workflow state should not be inferred exclusively from the technical state of an individual queue job.

A queue job represents an execution task.

A reservation represents a business commitment.

Their lifecycles are connected, but they're not identical.

---

# 11. Concurrency, Ordering, and Parallel Workers

BullMQ allows a worker to process several jobs concurrently:

```typescript
const worker = new Worker(
  "notifications",
  processNotification,
  {
    connection,
    concurrency: 20
  }
);
```

This is particularly useful for I/O-bound jobs.

While one notification waits for an email provider, another can perform database access, and another can call an HTTP API.

But as we learned in the computer science foundations courses (CS110, CS220, CS320), Node.js concurrency doesn't automatically mean CPU parallelism.

Twenty CPU-intensive JavaScript calculations running through one event loop don't become twenty parallel CPU cores.

For heavy computation, separate processes or sandboxed processors may be more appropriate.

### Ordering is not as simple as FIFO

Imagine these jobs arrive:

```text
1. Reservation created
2. Reservation modified
3. Reservation cancelled
```

It may seem natural to assume they'll finish in that order.

But with multiple workers or concurrent processing, the first job could take ten seconds while the second completes in one.

Retries and delays further complicate ordering.

Even if jobs are initially selected in FIFO order, **completion order is not guaranteed to match submission order under concurrency and failures**.

This matters when processing events that modify the same business entity.

Suppose a cancellation event executes before an older creation event. If the handlers simply overwrite the reservation's current state, the final result could incorrectly become `confirmed`.

One solution is to carry a monotonically increasing entity version:

```json
{
  "reservationId": "R-10842",
  "version": 12,
  "status": "cancelled"
}
```

A consumer can reject or ignore updates that would move a projection backward to an older version.

Other solutions include partitioning work by entity, enforcing serialized processing for particular resources, or reconstructing state from an authoritative event sequence.

Each carries different throughput and complexity costs.

### Queue partitioning

Sometimes a sensible approach is to distribute jobs so all events for one reservation are processed sequentially, while unrelated reservations proceed concurrently.

That can improve ordering behavior without reducing the entire system to one global worker.

But partitioning alone isn't enough if duplicate or delayed events can reappear after failure.

Version checks and idempotency remain useful.

---

# 12. Backpressure: What Happens When Work Arrives Faster Than It Finishes?

Queues absorb bursts, but they don't create infinite processing capacity.

Suppose your system receives 1,000 jobs per second.

Workers can complete 800 jobs per second.

The backlog grows by approximately 200 jobs every second.

After one hour:

\[
200 \times 3600 = 720{,}000
\]

That's 720,000 pending jobs.

Increasing Redis memory doesn't fix the underlying throughput mismatch.

It merely allows the backlog to grow for longer.

### The queue as a buffer

A queue is useful when incoming load temporarily exceeds processing capacity.

For example, a ten-second burst at 1,000 jobs per second may be manageable if workers process 1,500 per second afterward.

But if sustained arrival rate exceeds sustained service capacity, no finite queue can absorb the difference indefinitely.

This is a fundamental queueing principle.

### Why latency grows before everything breaks

Imagine your workers complete 500 jobs per second.

Under ordinary traffic, arrival rate is 300 jobs per second.

The system has spare capacity.

Now traffic increases to 490 jobs per second.

The system is still technically processing work faster than it arrives, but there is very little spare capacity to clear fluctuations.

Small bursts create backlogs that take increasingly long to drain.

Queue waiting time grows, even though the processing time of each job may remain unchanged.

This is why utilization near 100% is often dangerous.

### Backpressure strategies

The system may need to:

- Increase worker capacity when downstream systems can support it.
- Limit job production.
- Rate-limit calls to constrained providers.
- Reject or defer low-priority work.
- Batch compatible operations.
- Drop or coalesce disposable work.
- Separate latency-sensitive jobs from bulk workloads.

A useful metric is **age of the oldest waiting job**.

A queue containing 10,000 jobs isn't necessarily unhealthy if workers normally process millions per minute.

A queue containing only 100 jobs may be problematic if its oldest job has been waiting six hours.

Backlog size, arrival rate, processing rate, and waiting-time distribution tell a much more useful story together.

---

# 13. Durable Work Requires More Than a Durable Queue Library

We've discussed logical correctness. Now consider operational durability.

BullMQ typically uses Redis as its storage system, which means Redis configuration matters.

If Redis is configured purely as a disposable cache, important job data may be lost through eviction or insufficient persistence.

For production queue workloads, BullMQ's guidance recommends a `noeviction` memory policy and suitable persistence configuration, commonly involving Redis AOF.

But persistence isn't an absolute immunity shield.

Durability depends on replication, acknowledgement behavior, configuration, failover characteristics, and the actual failure scenario.

A queue can also become unavailable.

A producer attempting to add a job during a Redis outage needs a defined response. For an interactive API, waiting indefinitely for Redis may be unacceptable.

Workers, however, may reasonably reconnect and resume after temporary disconnections.

These two roles have different operational needs.

### Graceful shutdown

Suppose you're deploying a new worker version.

A good shutdown procedure stops accepting new jobs, gives active jobs an opportunity to complete, and closes connections cleanly.

BullMQ provides a `worker.close()` mechanism for graceful shutdown.

But deployment systems impose deadlines. A worker may still be forcibly terminated before completion.

Therefore, graceful shutdown reduces unnecessary duplication; it does not eliminate the need for idempotency.

### Monitoring real queues

At minimum, production monitoring should cover waiting, active, delayed, completed, and failed job counts; processing durations; retry and stall frequency; queue age; Redis availability; and worker throughput.

For important workflows, measure the business outcome too.

A notification queue reporting 99.99% completed jobs sounds excellent. But if the missing 0.01% includes every confirmation email for one major hotel, the business impact may be substantial.

Track whether required outcomes were actually achieved, not merely whether workers returned without throwing.

---

# 14. A Queue Is Not Necessarily a Workflow Engine

As backend systems grow, jobs begin depending on other jobs.

For example, generating a report might require:

```text
Load source data
       |
       v
Transform data
       |
       v
Generate PDF
       |
       v
Upload document
       |
       v
Notify customer
```

BullMQ supports job dependencies and flows, allowing parent jobs to wait for child jobs to complete.

That's useful for coordinating processing stages.

But consider a more complex business workflow:

1. Reserve a hotel room.
2. Request payment authorization.
3. Wait for an external callback.
4. Confirm the booking.
5. Capture payment.
6. Handle cancellation or compensation.
7. Reconcile unresolved operations.

This workflow may span minutes, hours, or days.

It includes business states, external decisions, and failure recovery.

Representing it entirely through transient queue-job relationships may become difficult.

A common architecture stores the durable business workflow state in PostgreSQL, while queues trigger attempts to advance that workflow.

```text
PostgreSQL: Booking Workflow State
                |
                v
         BullMQ Job
                |
                v
        Execute Next Step
                |
                v
       Record New State
                |
                v
     Schedule Subsequent Work
```

The database records what has happened and what remains necessary.

The queue schedules execution attempts.

For sufficiently complex workflows, a dedicated durable workflow engine may be useful, but ordinary application services plus a database and queue can handle many systems quite well.

We'll revisit the distinction when designing reliable payment and reservation workflows in CS430-L05.

---

# 15. Practical Lab: Reproduce a Job That Executes Twice

Let's recreate the opening incident using BullMQ.

Instead of sending real emails, we'll append a line to a local file representing a successful external side effect. Then we'll deliberately crash the worker before BullMQ records job completion.

You'll need Node.js, Redis, and two terminal windows.

Start Redis:

```bash
docker run --rm -p 6379:6379 redis:7
```

Create a small Node.js project:

```bash
npm init -y
npm install bullmq
```

Add `"type": "module"` to `package.json`.

### Step 1 — The producer

Create `producer.mjs`:

```javascript
import { Queue } from "bullmq";

const queue = new Queue("lab-notifications", {
  connection: {
    host: "127.0.0.1",
    port: 6379
  }
});

await queue.add(
  "send-confirmation",
  {
    reservationId: "R-10842",
    email: "customer@example.com"
  },
  {
    jobId: "confirmation-R-10842",
    removeOnComplete: false
  }
);

console.log("Job added");

await queue.close();
```

Run it once:

```bash
node producer.mjs
```

The job now exists in Redis, waiting for a worker.

### Step 2 — The deliberately unreliable worker

Create `worker.mjs`:

```javascript
import { Worker } from "bullmq";
import {
  appendFileSync,
  existsSync,
  writeFileSync
} from "node:fs";

const marker = "./first-attempt.marker";
const deliveries = "./deliveries.log";

const worker = new Worker(
  "lab-notifications",
  async job => {
    console.log("Processing:", job.id);

    // Simulate a successful external effect.
    appendFileSync(
      deliveries,
      `Sent email for ${job.data.reservationId}\n`
    );

    console.log("Email delivered");

    // Crash once, before BullMQ records completion.
    if (!existsSync(marker)) {
      writeFileSync(marker, "crashed-once");

      console.log("Crashing before completion");
      process.exit(1);
    }

    return { delivered: true };
  },
  {
    connection: {
      host: "127.0.0.1",
      port: 6379
    },
    lockDuration: 5000,
    stalledInterval: 5000
  }
);

worker.on("completed", job => {
  console.log("Completed:", job.id);
});

worker.on("stalled", jobId => {
  console.log("Stalled job:", jobId);
});

worker.on("failed", (job, error) => {
  console.error("Failed:", job?.id, error.message);
});

worker.on("error", console.error);
```

The short lock settings are intended only to make the experiment easier to observe. They're not production recommendations.

Run:

```bash
node worker.mjs
```

The worker claims the job, records one simulated delivery, and exits with status 1.

Look at `deliveries.log`:

```text
Sent email for R-10842
```

The external effect occurred, but BullMQ never recorded successful completion.

### Step 3 — Restart the worker

Run the same worker again:

```bash
node worker.mjs
```

After the previous lock expires and stalled-job recovery occurs, the job can be returned to waiting.

The worker executes it again.

This time, the marker file exists, so it doesn't crash.

Inspect `deliveries.log`:

```text
Sent email for R-10842
Sent email for R-10842
```

We've reproduced the duplicate-effect problem.

The job was added once.

It was processed twice.

And both executions performed the simulated external effect.

Depending on BullMQ timing and your environment, recovery may not be instantaneous. Don't mistake a short delay for a failed experiment.

### Step 4 — Consider a naive idempotency marker

Suppose you modify the worker to check a `delivered` marker before sending.

That seems promising.

But where do you write the marker?

If you write it **after** delivery, a crash between delivery and marker creation can produce duplicates.

If you write it **before** delivery, a crash between marker creation and delivery can cause the email to be skipped forever.

This is the central difficulty.

A local file, Redis key, or PostgreSQL row cannot automatically make an external email operation atomic with the marker update.

### Step 5 — Design a safer solution

Imagine the email provider supports an idempotency key for its send API.

The worker could submit:

```typescript
await emailProvider.send({
  idempotencyKey: `confirmation-${reservationId}`,
  reservationId,
  recipient
});
```

If the provider guarantees deduplication for that operation identity within an appropriate retention period, retries can become safe under that contract.

If the provider lacks such a feature, you may need to record provider message IDs, query delivery status, reconcile uncertain outcomes, or accept that rare duplicate emails are possible.

For notifications, occasional duplication may be a tolerable trade-off.

For financial operations, the requirements will normally be considerably stricter.

The lab demonstrates why these decisions must be made at the business-effect boundary rather than merely inside queue configuration.

---

# 16. Engineering and Interview Challenges

### Question 1 — The successful job that repeats

A BullMQ worker sends an email successfully, then loses its Redis lock before reporting completion. Another worker subsequently executes the same job.

Is BullMQ broken? How would you prevent harmful duplicate effects?

### Question 2 — The missing notification

A reservation is committed in PostgreSQL, but the subsequent `queue.add()` operation fails because Redis is unavailable.

Why doesn't wrapping the PostgreSQL operations in a transaction solve this? Which architectural pattern would you use?

### Question 3 — The dangerous payment retry

A worker calls a payment provider and receives a timeout. Its retry policy immediately attempts the charge again with a new request identifier.

What is the fundamental problem?

### Question 4 — Ordering versus concurrency

A queue contains `created`, `updated`, and `cancelled` events for a reservation, in that order. Workers process jobs concurrently.

Can the final stored state become incorrect even if every event is processed successfully? How would you address this?

### Question 5 — The growing backlog

Jobs arrive at 2,000 per second, but workers complete only 1,600 per second. The system has sufficient Redis memory for now.

Is the queue healthy? What should you measure and change?

### Question 6 — The completed-job deduplication trick

A developer assigns a custom BullMQ `jobId` to every payment job and enables `removeOnComplete: true`, claiming this guarantees that a payment will never execute twice.

Is the claim correct?

---

# 17. Solutions and Discussion

### 1. The queue is recovering uncertain work

BullMQ cannot infer that the external email was sent merely because the worker began processing. Once the processing lock is lost, recovery may cause another attempt.

The worker should be designed for repeated execution. Stable business operation identifiers, provider-side idempotency, and durable delivery records can help, depending on what the email provider supports.

A unique queue job ID alone doesn't solve repeated execution of an existing job.

### 2. PostgreSQL and Redis cannot be committed atomically through an ordinary database transaction

The reservation transaction controls PostgreSQL changes, not the subsequent Redis enqueue operation.

A transactional outbox stores the notification intent in PostgreSQL alongside the reservation, allowing a separate publisher to retry job submission.

The publisher must tolerate repeated publication, and consumers still need appropriate idempotency.

### 3. A timeout doesn't establish failure

The payment may have succeeded even though the worker never received the response.

Retrying with a new operation identity can create a second charge.

The system should reuse a stable payment operation identifier supported by the provider's idempotency mechanism, or query and reconcile the previous attempt before creating another effect.

### 4. Concurrent completion can violate intended ordering

Jobs may be selected in one order but finish in another, particularly under concurrency and retries.

If handlers blindly overwrite current state, an older event can arrive after a newer one and incorrectly reverse the entity's state.

Useful approaches include entity versions, conditional state updates, ordered processing by entity, and authoritative state reconstruction. The correct choice depends on the event semantics and throughput requirements.

### 5. The backlog grows indefinitely under sustained overload

At the given rates, pending work increases by 400 jobs every second.

More Redis memory only postpones the consequences.

The team must increase sustainable processing capacity, reduce production rate, batch or coalesce compatible jobs, or introduce backpressure.

Oldest-job age and queue waiting-time distributions are particularly useful for understanding whether the system is meeting its business deadlines.

### 6. Queue deduplication isn't exactly-once execution

BullMQ custom job IDs prevent certain duplicate enqueue operations while the corresponding job exists.

If completed jobs are removed, the same identifier may be accepted again.

Furthermore, a job can execute multiple times because of stalls and recovery without any new enqueue operation.

Payment correctness must be enforced through stable business operation identities and appropriate provider/database coordination, not simply queue-job uniqueness.

---

# 18. Mental Model

A reliable asynchronous system has four distinct responsibilities:

- **Business state:** What outcome must eventually be achieved, and what has already happened?
- **Durable intent:** What work has the application committed to performing?
- **Execution scheduling:** When and where should an attempt run?
- **Effect enforcement:** How do we prevent retries from causing incorrect duplicate changes?

Queues are particularly good at execution scheduling and failure recovery. They do not automatically solve all four responsibilities.

The practical checklist is straightforward: define the success contract, preserve durable work, assume duplicate attempts, make side effects idempotent where possible, classify failures, bound retries, and measure backlog against actual business deadlines.

**The key principle: design every important background operation as though its worker could crash immediately after performing the side effect but before recording success.**

If the architecture still behaves correctly—or has an explicit recovery and reconciliation strategy—you've understood the problem.

---

# Next Session — Distributed Systems and Partial Failure

Imagine a worker charging a customer's card. It sends the payment request, waits three seconds, and receives a network timeout.

Did the payment fail? Did it succeed? Is the provider still processing it?

The timeout cannot answer any of those questions.

In **CS430-L01 — Distributed Systems and Partial Failure**, we'll investigate why separate computers can disagree about what happened, why failure detection is fundamentally uncertain, and how timeouts, retries, idempotency, circuit breakers, and operation identities help us build systems that remain useful despite incomplete information.

---


---

## End of SE320

**SE320 — Backend Services and Asynchronous Processing** is complete. See the recommended study order in `README.md` for natural next courses.

## Further Reading

- **BullMQ — Introduction and Processing Guarantees:** https://docs.bullmq.io/
- **BullMQ — Stalled Jobs:** https://docs.bullmq.io/guide/workers/stalled-jobs
- **BullMQ — Idempotent Jobs:** https://docs.bullmq.io/patterns/idempotent-jobs
- **BullMQ — Retrying Failing Jobs:** https://docs.bullmq.io/guide/retrying-failing-jobs
- **BullMQ — Job Identifiers:** https://docs.bullmq.io/guide/jobs/job-ids
- **BullMQ — Worker Concurrency:** https://docs.bullmq.io/guide/workers/concurrency
- **BullMQ — Flows:** https://docs.bullmq.io/guide/flows/
- **BullMQ — Going to Production:** https://docs.bullmq.io/guide/going-to-production


---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE320-L03  QUEUES / WORKERS — INTERVIEW GLANCE CARD

CORE MODEL
  Execute effect ≠ record completion ≠ business effect done
  Crash after send, before ack → recovery redelivers → duplicates
  Queue lock coordinates ownership inside queue; can't undo external work

WHY QUEUES
  Separate critical accept from secondary consequences
  Scale workers independently; absorb bursts; retry failures
  Contract shifts: “done” → “durably accepted for later”
  202 Accepted + job status vs 201 after committed reservation

BULLMQ LIFECYCLE (simplified)
  waiting → claim → active → completed | retry/delay | failed
  Lock renewal while processing; stall → recover to waiting
  Stall ≠ permanent state; blocked event loop can stall too
  Overlap possible if lock lost while JS still running

DELIVERY MODELS (careful terms)
  At-most-once   may lose work; no deliberate redelivery
  At-least-once  unfinished can retry; duplicates possible (BullMQ-ish)
  Exactly-once effect  needs idempotency / provider coords — not
                       “broker magic” alone
  Delivery ≠ handler run ≠ business effect

IDEMPOTENCY
  Business operation ID (refund-9281) > mere queue job ID
  Local PG: INSERT processed_operations ON CONFLICT + effect in ONE txn
  External call: mark-before / call-before both race; need provider
  idempotency keys, query, or reconcile
  Enforce where effect occurs

JOB ID ≠ PROCESSING IDEMPOTENCY
  Custom jobId: enqueue dedupe while job exists
  removeOnComplete: ID free again; stalls still re-execute same job
  Technical queue ID ≠ business uniqueness guarantee

DUAL-WRITE / OUTBOX
  save() then queue.add() — no shared atomicity with Redis
  Outbox: insert business + outbox_events same PG txn → publisher → queue
  Publisher may republish; consumers need idempotency
  FOR UPDATE SKIP LOCKED for concurrent publishers; don't hold txn
  during slow network
  Outbox = durable obligation; queue = schedule attempts

RETRIES
  Transient vs permanent (invalid email ≠ retry forever)
  Ambiguous timeout ≠ permission for new payment ID
  attempts + exponential backoff + jitter; respect deadlines
  Exhausted → poison / failed set / DLQ-like store; inspect + replay
  Job fail ≠ business fail (reservation confirmed, email failed)

CONCURRENCY / ORDERING
  concurrency:N good for I/O; not free CPU parallelism
  Completion order ≠ submission under concurrency/retries
  Entity version / partition-by-entity / conditional updates
  Partition alone insufficient if delayed duplicates appear

BACKPRESSURE
  Arrival > service forever → unbounded backlog (memory only delays)
  Near 100% util → waiting time explodes on small bursts
  Measure oldest waiting age + rates, not only depth
  Scale / limit / rate-limit / coalesce / separate latency classes

OPS
  Redis for queues: noeviction + suitable AOF/persistence
  Producer vs worker outage policies differ
  Graceful close reduces dupes; doesn't remove need for idempotency
  Monitor waiting/active/failed, stalls, age, AND business outcomes

QUEUE ≠ WORKFLOW ENGINE
  Complex multi-day payment/booking: durable state in PG;
  queue advances steps; job graph ≠ full business machine

FOUR RESPONSIBILITIES
  Business state · Durable intent · Execution scheduling · Effect enforcement

SENIOR LINE: Design as if worker crashes right after the side effect
             and before recording success.
```

---

