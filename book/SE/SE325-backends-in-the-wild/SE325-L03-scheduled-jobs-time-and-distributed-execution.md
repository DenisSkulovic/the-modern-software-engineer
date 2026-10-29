---
id: SE325-L03
course: SE325
title: "Scheduled Jobs, Time, and Distributed Execution"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE325-L02
next: SE325-L04
---

# SE325 — Backends in the Wild: Production Field Guide
## Lecture 03: Scheduled Jobs, Time, and Distributed Execution

*The nightly billing job has run successfully for eleven months. Then a scheduler fails over, two replicas execute the same run, and customers begin receiving duplicate invoices. The next morning, finance discovers another problem: the previous day's job never ran at all.*

---

# Part I — Intuition

## 1. The Job That Ran Twice

Imagine you're working at Mercury, a hotel-booking platform.

Every night, the company performs several housekeeping operations.

It prepares invoices for completed reservations, reconciles payment records, refreshes analytical summaries, removes expired temporary files, and checks for bookings whose external supplier confirmations never arrived.

Some tasks run every few minutes.

Others run daily.

A few happen only at the end of the month.

The engineering team has a scheduler that triggers these operations automatically.

For months, everything works.

Then the company increases availability by running two replicas of its backend service.

Both replicas contain the scheduler.

At midnight, both wake up.

Both inspect the clock.

Both conclude that it's time to prepare yesterday's invoices.

Both begin working.

The database now contains two invoice-preparation attempts for the same business period.

Perhaps a uniqueness constraint prevents the second invoice record.

Perhaps it doesn't.

Perhaps the invoice records are correct, but a downstream email service sends each invoice twice.

The scheduler has done exactly what each replica was programmed to do.

But the distributed system has performed one logical business operation twice.

This is our first problem.

**A schedule tells us when work is due. It does not, by itself, establish who has permission to perform that work.**

## 2. A Cron Expression Isn't a Business Contract

You may already have encountered cron.

A cron expression is a compact way of describing recurring execution times.

For example, in conventional five-field Unix cron syntax, `0 0 * * *` represents a job scheduled at midnight every day, interpreted according to the scheduler's timezone.

At first glance, the problem appears solved.

Write the expression.

Register the job.

Forget about it.

But consider the assumptions hidden in that simplicity.

Which timezone determines midnight?

What happens if the computer is offline at midnight?

What happens if the previous execution is still running?

What happens if the scheduler launches the job and crashes before recording that fact?

What happens if two scheduler instances are active?

And what happens if the clock moves forward or backward?

The cron expression answers only one part of the problem.

It describes when a launch should be considered.

It doesn't define whether missing a launch is acceptable, whether duplicate execution is dangerous, or how the business operation recovers.

## 3. A Scheduled Job Has Three Different Responsibilities

Imagine a railway company.

Its timetable says a train should depart at eight o'clock.

That's the schedule.

But the timetable doesn't decide which locomotive is assigned to the train.

Nor does it guarantee that passengers reach their destination.

Three separate questions exist.

First, should a departure happen?

Second, which train is responsible for it?

Third, did the journey actually complete?

Scheduled software works similarly.

### Visual anchor 1 — The three boundaries

```text id="s32503a"
SCHEDULE
"Run daily at midnight"
           |
           v
OCCURRENCE
"Process business day October 28"
           |
           v
OWNERSHIP
"Worker B may execute this run"
           |
           v
BUSINESS EFFECT
"Invoices prepared correctly"
           |
           v
VERIFICATION
"All expected invoices accounted for"
```

The scheduler can successfully create a job even if the job later fails.

A worker can claim the job even if it crashes before doing anything.

And a worker can complete the business operation while losing the acknowledgment that would have recorded success.

**Scheduling success, execution success, and business success are different claims.**

## 4. The Missing Midnight

Now imagine a different incident.

The scheduler is unavailable at midnight.

Its database loses connectivity, or the service is temporarily shut down for maintenance.

It returns at 03:17.

Should the missed job execute immediately?

That depends on the job.

Suppose the scheduled task refreshes a disposable cache every five minutes.

If one refresh is missed, the next refresh may be sufficient.

Running twelve old cache refreshes after an outage would probably be pointless.

But suppose the task prepares invoices for each completed business day.

Skipping yesterday's invoices may be unacceptable.

The system should identify which business period remains unprocessed and arrange recovery.

A cache refresh and an invoice-preparation operation have different catch-up requirements.

The scheduler cannot choose correctly merely by knowing how late it is.

It must understand the job's policy.

## 5. The Date Is Not the Time

There's another subtlety.

Suppose finance requires invoices for each business day.

The scheduler happens to execute at midnight.

But what identifies the business operation?

Is it the moment when the process starts?

Or is it the business period being processed?

Imagine the job for October 28 is scheduled to launch at midnight on October 29.

If the scheduler recovers at 03:17, it should still process October 28.

It shouldn't suddenly process October 29 merely because that's the current calendar date.

We need to preserve the identity of the scheduled occurrence.

For example:

`prepare-invoices / business-day-2026-10-28`

The same logical operation retains that identity whether it starts at midnight, 03:17, or the following morning.

This identity is also useful when the system retries.

Two attempts to prepare invoices for the same day should not accidentally become two different business operations.

## 6. A Lease Is a Temporary Ownership Agreement

Return to the two scheduler replicas.

How do we prevent both from processing the same occurrence?

One approach is to create a durable record describing which worker currently owns the run.

Worker A acquires ownership.

The record says A may execute the job until a specified deadline.

Worker B attempts to acquire the same run.

The system rejects B while A's ownership remains valid.

This temporary ownership arrangement is called a **lease**.

Unlike a permanent lock, a lease expires.

That matters because A might crash.

If ownership never expired, the job could remain permanently stuck.

### Visual anchor 2 — Lease and failover

```text id="s32503b"
00:00  Worker A claims the run
       Lease valid until 00:05

00:02  Worker B tries
       Ownership denied

00:03  Worker A crashes

00:05  Lease expires

00:06  Worker B claims the run
       Processing resumes
```

This looks promising.

But we haven't solved everything.

What if Worker A didn't actually crash?

What if it merely stopped responding for several minutes and later resumed?

A could still believe it owns the job.

Worker B now owns the newer lease.

Both may attempt to perform work.

A lease reduces competing execution.

It doesn't automatically make the old worker incapable of acting.

## 7. Fencing Tokens: The Old Worker Must Stay Old

Imagine a hotel where employees receive temporary access badges.

Worker A receives badge number 17.

Its access expires.

Worker B receives badge number 18.

Later, A returns and tries to use badge 17.

A correct security system should reject the older badge.

That's the intuition behind a **fencing token**.

Each successful ownership claim receives a monotonically increasing token.

Worker A receives token 17.

After recovery, Worker B receives token 18.

A shared resource rejects operations from stale tokens.

### Visual anchor 3 — Fencing stale ownership

```text id="s32503c"
Worker A              Shared state             Worker B
token 17              latest = 17
   |                                             |
   |          Lease expires                      |
   |                                             |
   |                             New claim ------+
   |                         latest = 18          |
   |                                             |
   +-- Write with token 17                       |
          |
          v
       REJECTED

                              Write with token 18
                                      |
                                      v
                                   ACCEPTED
```

The important detail is that the resource receiving the operation must enforce the fencing rule.

Merely handing workers increasing numbers isn't enough.

If Worker A can directly call an external API that doesn't know anything about those tokens, the token alone cannot stop it.

This distinction will matter when we investigate external side effects.

## 8. The Clock That Repeated an Hour

Now imagine the scheduler is configured to run at 03:30 local time.

In some timezones, daylight-saving transitions can make that time nonexistent or ambiguous.

For a concrete example, consider Europe/Vilnius in 2026.

On March 29, the clock moves forward.

Local 03:30 never occurs.

On October 25, the clock moves backward.

Local 03:30 occurs twice.

What should a 03:30 scheduled job do?

Skip the spring occurrence?

Execute at the next valid time?

Run twice in autumn?

Run once, choosing the first occurrence?

Run once, choosing the second?

Different scheduling systems implement different policies.

The important point is not memorizing the policies of every scheduler.

It's recognizing that local calendar time is not always a one-to-one mapping to an instant.

A business rule such as "once per local business day" needs a deliberate interpretation.

And a rule such as "every twenty-four hours" isn't necessarily equivalent to "every day at the same local time."

## 9. Our First Reliable-Scheduler Design

We now have a useful mental picture.

A recurring schedule identifies which business occurrence is due.

The occurrence gets a durable identity.

A worker must claim the occurrence.

The claim is temporary and recoverable.

Stale workers must not overwrite newer ownership decisions.

The business operation must tolerate uncertain execution and retries.

The system needs a policy for missed runs.

And completion must be verified through authoritative business evidence.

That's more involved than adding a cron decorator to a Python or Node.js function.

But these mechanisms don't necessarily require a complicated distributed platform.

For a small application, a database table and a well-designed worker may be sufficient.

For larger systems, Kubernetes, managed schedulers, or workflow platforms can handle part of the problem.

The business guarantees remain yours to define.

### A tiny comprehension check

Two application replicas independently run the same cron expression. Does cron alone prevent duplicate execution?

No.

A worker's lease expires while the worker is paused. Another worker claims the job. Can the first worker safely assume its old ownership is still valid when it resumes?

No.

A daily invoice job was missed because the scheduler was down. Should the next scheduler invocation automatically process the current date and forget the previous one?

No. The job's business-period identity and catch-up policy determine what remains due.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 10. Time Has Several Meanings in Software

A surprising number of scheduled-job failures begin with treating time as one simple number.

But applications use time for different purposes.

A timestamp may represent an absolute instant.

A local date may represent a business day.

A duration represents elapsed time.

A timezone determines how an instant is displayed or interpreted under local calendar rules.

A scheduled occurrence represents an intended execution slot.

These concepts overlap but are not interchangeable.

### 10.1 An instant

An instant identifies a particular point on the global timeline.

For example, a timestamp in UTC can identify when a payment event occurred.

UTC is particularly useful for comparing events across services and regions.

### 10.2 A local business date

A finance department may define its accounting day according to a specific local timezone.

The business day October 28 is a calendar concept.

Its boundaries depend on the relevant timezone and business policy.

The same UTC instant may belong to different local dates in different regions.

### 10.3 A duration

A lease valid for thirty seconds expresses elapsed time.

That is not the same as a calendar rule that runs at 09:00 every morning.

Elapsed durations and calendar recurrences require different reasoning.

### 10.4 A scheduled occurrence

Suppose Mercury prepares daily reconciliation reports.

The occurrence might be identified by the date being reconciled.

For example:

`reconcile-payments / Europe-Vilnius / 2026-10-28`

That identity should remain stable even if execution is delayed.

The execution timestamp describes when an attempt happened.

It doesn't redefine the business period.

## 11. Cron Syntax Is Only the Beginning

Traditional Unix cron commonly uses five fields.

They represent minute, hour, day of month, month, and day of week.

Other scheduling platforms use different expressions.

For example, EventBridge Scheduler uses a six-field cron expression with a year component.

Some libraries support seconds.

Others include vendor-specific special characters.

A cron expression is therefore not a universally interchangeable string.

### 11.1 Always identify the implementation

When reviewing a scheduled job, determine which scheduler interprets its expression.

A Unix cron daemon, a Node.js scheduling library, a Kubernetes CronJob, and EventBridge Scheduler can differ in syntax and behavior.

Timezone interpretation, missed executions, overlapping runs, and daylight-saving treatment must be checked against the actual implementation.

### 11.2 A timestamp is not a schedule

A one-time execution at a specific instant is different from a recurring calendar rule.

A one-time timer can be represented by an absolute timestamp.

A recurring schedule needs a rule for calculating future occurrences.

This distinction becomes especially important across timezone changes.

## 12. Every Scheduled Occurrence Needs an Identity

Suppose Mercury's invoice-preparation job is scheduled every day.

A simple implementation checks whether the current time is after midnight and then performs the task.

But what happens if the scheduler restarts at 03:17?

Without durable history, it may not know whether the midnight run already happened.

A stronger design records occurrences.

Conceptually, a record contains:

Job identity.

Scheduled business period.

Expected execution time.

Current state.

Owner.

Attempt or fencing information.

Completion evidence.

### 12.1 Unique occurrence identity

The database can enforce uniqueness for the combination of job identity and scheduled occurrence.

For example, there should be only one logical `prepare-invoices` occurrence for business day October 28.

There may be several execution attempts.

But they belong to the same occurrence.

### 12.2 Why the scheduled time matters

Imagine a scheduler crashes after launching the job but before recording completion.

On recovery, the replacement scheduler looks up the occurrence.

If the occurrence already exists, it can inspect the state rather than immediately creating an unrelated new job.

This is a foundation for safe retry and reconciliation.

### 12.3 Business-period identity versus launch identity

A job might launch twice for the same business period.

If its business operation is "prepare one invoice per reservation per day," the downstream data should also recognize that business identity.

The scheduling layer's occurrence ID is useful.

It isn't necessarily sufficient to protect every downstream side effect.

## 13. Duplicate Launches Are a Normal Distributed Risk

Let's examine how duplicate execution happens.

Imagine two backend Pods.

Both contain a timer configured for midnight.

At midnight, both timers fire.

Unless they coordinate, both begin the same work.

The simplest mistake is assuming that deploying multiple application replicas automatically makes every component highly available.

It may do the opposite for periodic work.

### 13.1 Multiple replicas mean multiple clocks

A timer embedded in every application process naturally exists once per process.

Scaling the service from one replica to five may create five independent timers.

If every timer performs a non-idempotent business operation, the risk increases.

### 13.2 A leader helps, but leadership can change

One scheduler replica might act as the leader.

Other replicas remain standby.

But the leader can become unavailable.

A replacement leader must determine what work has already been launched.

Otherwise, failover can produce duplicate or missing executions.

### 13.3 Launching and recording aren't atomic

Suppose the leader sends a request to create a worker job.

The request succeeds.

The leader crashes before recording the launch.

The replacement leader sees no completion record and launches the job again.

The failure is not caused by poor clock precision.

It's an uncertainty window between an external action and its durable acknowledgment.

This should sound familiar from queue processing and payment workflows.

## 14. What Does "Exactly Once" Mean for Scheduled Work?

People often ask whether a scheduler guarantees exactly-once execution.

That phrase needs careful interpretation.

A scheduler may try to create one job object per scheduled occurrence.

A worker process may execute more than once.

The business effect may need to happen exactly once in the logical sense.

Those are different guarantees.

### 14.1 At-most-once launch

A system can favor avoiding duplicate launches.

But if it crashes at the wrong moment, it may miss an occurrence.

For disposable maintenance tasks, this may be acceptable.

### 14.2 At-least-once attempt

A system can favor retrying uncertain occurrences.

But that creates the possibility of repeated execution.

The business operation must handle repetition safely.

### 14.3 Exactly-once business effect

If preparing an invoice produces one durable database record with a unique business identity, the database may enforce one logical invoice.

But that doesn't automatically guarantee one email, one external payment request, or one physical execution.

Those effects may require independent idempotency keys, provider-side lookup, or reconciliation.

### 14.4 Prefer precise guarantees

Instead of declaring that a scheduler runs exactly once, state the actual invariant.

For example:

"For each completed reservation and accounting period, at most one authoritative invoice record can be created."

And separately:

"Every eligible accounting period must eventually be reconciled."

These requirements can be tested.

The vague phrase "the cron job only runs once" conceals too many distinct failure modes.

## 15. Claiming Scheduled Work

A common implementation uses a database-backed job table.

A worker attempts to claim an occurrence.

The claim must be atomic.

Two workers racing to claim the same occurrence must not both receive successful ownership.

### 15.1 Why check-then-update is unsafe

Suppose Worker A reads:

`owner = null`

Worker B reads the same value.

Both conclude the job is available.

Both write their own owner identity.

Both begin processing.

The implementation has a race.

### 15.2 Conditional update

A safer claim uses a database operation whose success depends on the current state.

For example, it may claim a row only if the occurrence is unowned or its previous lease has expired.

The database determines which competing transaction wins.

The application checks the affected-row count or returned record.

### 15.3 Unique creation

If two schedulers attempt to create the same occurrence simultaneously, a unique constraint can ensure only one logical occurrence record is created.

The rejected insertion is not necessarily a production error.

It may simply mean another scheduler created the record first.

### 15.4 One occurrence, several attempts

The durable occurrence remains the same.

The owner and attempt metadata can change after failure.

Keeping these identities separate makes incident investigation much easier.

## 16. Leases: Ownership That Can Expire

A lease assigns temporary authority.

A worker may claim a job for a defined duration.

While the lease is active, competing workers should not acquire that occurrence.

After expiration, another worker may recover it.

### 16.1 Why not use permanent ownership?

If the worker crashes, a permanent ownership flag can leave the job stuck indefinitely.

A lease provides a recovery mechanism.

### 16.2 Lease duration

Too short, and healthy jobs may lose ownership while processing.

Too long, and failover recovery may be unnecessarily delayed.

The choice depends on expected work duration, heartbeat frequency, database availability, and acceptable recovery latency.

### 16.3 Lease renewal

For long-running work, a worker may periodically renew its lease.

Renewal must verify that the worker still owns the occurrence.

It shouldn't blindly overwrite ownership established by another worker.

### 16.4 Time authority

A lease usually depends on a trusted time source.

If workers independently use badly skewed wall clocks, they can disagree about expiration.

A database-backed design can use the database's time authority for claim and renewal decisions.

A local process may use a monotonic clock for measuring elapsed durations, but a distributed lease needs a coherent shared protocol.

Do not confuse these two uses of clocks.

## 17. The Stale-Worker Problem

Now consider a dangerous failure.

Worker A claims the job.

It begins an operation.

Then its process is paused for longer than the lease duration.

Perhaps the container experiences a long pause, network partition, or scheduling problem.

The lease expires.

Worker B claims the same occurrence.

Then A resumes.

A still holds an old in-memory variable saying:

`ownsJob = true`

That variable is no longer authoritative.

### 17.1 Checking the lease once isn't enough

Suppose A checks its lease before starting a lengthy calculation.

It then spends several minutes computing.

The lease expires.

A eventually writes the result.

The earlier check doesn't establish current ownership.

### 17.2 Fencing tokens

A fencing token identifies the generation of ownership.

Each successful claim advances the generation.

A shared destination can reject writes using an older token.

### 17.3 Where fencing must be enforced

The receiving database can compare the supplied token against the current ownership record.

This can prevent stale workers from committing changes.

But if a worker sends an email through an external provider that doesn't know about the token, simply passing the token locally offers no protection.

The effect needs a durable, idempotent authorization path or suitable downstream cooperation.

### 17.4 The key lesson

A lease controls who is *supposed* to act.

Fencing and business-level idempotency help ensure that old or repeated actors cannot produce invalid effects.

They complement one another.

## 18. Advisory Locks Versus Durable Job Records

PostgreSQL provides advisory locks.

They can be useful for coordination when the application needs a lock unrelated to a specific ordinary row.

But advisory locks have their own semantics.

### 18.1 Session-level advisory locks

A session-level advisory lock remains held until released or the database session ends.

This can make it convenient for certain single-owner tasks.

However, connection pooling and connection lifetime require careful consideration.

The lock belongs to the database session, not to an abstract business operation.

### 18.2 Transaction-level advisory locks

A transaction-level advisory lock is released when its transaction ends.

It can be useful for a short critical section.

But it doesn't automatically provide durable ownership throughout a long-running job that spans many transactions.

### 18.3 Locks aren't progress records

Even if a lock prevents concurrent execution, the system still needs to know which business periods were completed.

A lock says something about present coordination.

A durable job record says something about the history and outcome of work.

For recurring financial jobs, that difference is essential.

## 19. The Lost Completion Acknowledgment

Let's revisit the opening incident.

The worker prepares invoice records successfully.

The database transaction commits.

Then the process crashes before marking the scheduled run completed.

The next scheduler sees an unfinished occurrence.

Should it retry?

Probably, after checking the appropriate recovery policy.

But what happens when the records are processed again?

### 19.1 Durable effects with unique identities

Suppose the database enforces one invoice record per reservation and accounting period.

The retry encounters existing invoice records and recognizes that those business effects already exist.

The system can reconcile the expected set of invoices rather than blindly creating duplicates.

### 19.2 External side effects

Now suppose the worker also sent emails.

The database cannot simply roll back those emails.

If email delivery happened before the crash, retrying may send duplicates.

The scheduling system needs a durable notification obligation and a suitable delivery and reconciliation strategy.

### 19.3 Provider-specific guarantees

Some external systems accept idempotency keys.

Others permit querying an operation by a stable external ID.

Others provide only weaker delivery semantics.

The scheduler must not claim guarantees that the downstream system cannot enforce.

### 19.4 Acknowledgment is evidence, not truth

The absence of a completion acknowledgment does not prove the business operation failed.

The correct recovery process inspects authoritative effects.

## 20. Missed Executions: Catch Up or Skip?

Now consider the scheduler that was unavailable at midnight.

It returns at 03:17.

Different tasks deserve different recovery policies.

### 20.1 Skip missed runs

A frequently executed cache refresh may only need the next normal run.

The intermediate missed refreshes don't necessarily provide value.

### 20.2 Execute the latest occurrence

A metrics aggregation that produces the current materialized view may be able to regenerate the latest state rather than replay every missed interval.

But this depends on whether earlier intervals contain information that cannot be reconstructed later.

### 20.3 Catch up every business period

Daily invoice preparation or settlement reconciliation may require every business period to be processed.

The scheduler should enumerate missing periods and create or resume their occurrences.

### 20.4 Bound catch-up

Suppose a scheduler was unavailable for forty days.

Launching forty expensive jobs simultaneously may overload production.

A catch-up process can preserve completeness while processing missing periods through a bounded queue.

### 20.5 Define deadlines

Some work becomes pointless after a particular time.

For example, sending a reminder that a reservation starts tomorrow may be inappropriate if the reservation already ended.

A catch-up policy can use deadlines to decide whether an overdue occurrence should execute, be skipped, or require human review.

The decision is a business rule, not merely a timer setting.

## 21. Calendar Time and Daylight Saving

Let's investigate the clock problem more precisely.

A scheduler may operate in UTC or a named timezone.

UTC timestamps identify instants unambiguously.

Named timezones define how local calendar times map to instants, including daylight-saving rules.

### 21.1 Spring-forward gaps

In Europe/Vilnius on March 29, 2026, the clock moves forward.

Local 03:30 does not occur.

A job configured for that exact local time needs a policy.

Some schedulers skip it.

Others may shift it.

The behavior must be established from the implementation.

### 21.2 Fall-back ambiguity

On October 25, 2026, local 03:30 occurs twice.

The first occurrence has the summer-time UTC offset.

The second has the winter-time offset.

These correspond to different UTC instants.

A scheduler might invoke once or twice according to its implementation and configuration.

### 21.3 Midnight is a separate case

For Europe/Vilnius in those specific transitions, the skipped and repeated hour is around 03:00, not midnight.

A daily midnight schedule therefore doesn't encounter the same local-time ambiguity on those dates.

However, other timezones have historically changed clocks at or around midnight.

A robust calendar scheduler shouldn't assume every local date has exactly twenty-four hours or that all local times always exist.

### 21.4 Every twenty-four hours versus every local day

A timer that repeats after exactly twenty-four elapsed hours remains aligned to elapsed time.

A calendar rule such as "09:00 every local morning" follows local clock time.

During daylight-saving transitions, the elapsed interval between consecutive local occurrences may be twenty-three or twenty-five hours.

These are different scheduling contracts.

### 21.5 Business dates need named timezones

If finance closes its daily accounting period according to Lithuanian time, record that policy explicitly.

Store authoritative timestamps as instants where appropriate, but calculate accounting dates using the agreed timezone.

Don't infer a business period from the worker machine's default timezone.

## 22. Overlapping Runs

Suppose a reconciliation job runs every five minutes.

One execution sometimes takes eight minutes.

What happens when the next occurrence becomes due?

### 22.1 Allow overlap

Both executions run concurrently.

This can be appropriate for independent occurrences.

But shared state and resource contention must be considered.

### 22.2 Forbid overlap

The scheduler may skip or delay a new run while an earlier one remains active.

This can protect shared resources.

But if the job takes longer than its interval, missed occurrences may accumulate.

### 22.3 Replace the existing run

A scheduler may terminate or replace an active execution when a new occurrence becomes due.

This can be reasonable for disposable, replaceable computations.

It is dangerous for tasks with non-reversible business effects.

### 22.4 Queue every occurrence

Another approach is to preserve every due occurrence and process them serially.

This supports completeness.

But the backlog can grow indefinitely when execution time consistently exceeds the schedule interval.

### 22.5 Choose according to semantics

A cache refresh might reasonably skip intermediate occurrences.

A daily financial reconciliation may require every period.

A cleanup task might allow overlap only when workers operate on disjoint partitions.

There is no universally correct concurrency policy.

## 23. Kubernetes CronJobs: Useful, Not Magical

Kubernetes provides CronJobs for recurring work.

A CronJob describes a schedule and a Job template.

The controller attempts to create Jobs at the appropriate times.

### 23.1 Timezones

Kubernetes supports a `timeZone` field for CronJob schedules.

This makes the intended timezone explicit.

### 23.2 Concurrency policy

Kubernetes CronJobs support policies commonly named `Allow`, `Forbid`, and `Replace`.

These control how overlapping Jobs from the same CronJob are handled.

But the policy isn't a global distributed lock across every unrelated CronJob or external scheduler that might perform the same business operation.

### 23.3 Starting deadlines

`startingDeadlineSeconds` controls how late a missed start may still be considered.

This helps define scheduling behavior after controller delays.

It doesn't replace a business-level catch-up policy for every possible failure.

### 23.4 Duplicate and missing Jobs

Kubernetes documentation explicitly acknowledges that CronJob scheduling is approximate.

In some circumstances, it may create more than one Job or fail to create one at the intended time.

Therefore, the Job's business processing should tolerate these conditions.

### 23.5 The scheduled timestamp

Modern Kubernetes versions annotate created Jobs with the intended scheduled timestamp.

This can help associate execution with a particular occurrence.

But an application still needs appropriate business-period identity and idempotency.

### 23.6 Beware of destructive replacement

For a non-idempotent payment or invoice workflow, replacing an active Job doesn't undo completed external effects.

The new Job must be able to reconcile prior progress.

## 24. Managed Scheduling Platforms

AWS EventBridge Scheduler offers recurring cron and rate schedules, one-time schedules, timezone support, retry configuration, and flexible execution windows.

This can remove the need to operate an application-local scheduler.

But using a managed scheduler doesn't eliminate business correctness requirements.

### 24.1 Rate expressions

A rate schedule describes elapsed intervals.

For example, a daily rate expression can mean an interval of twenty-four hours.

This differs from a local calendar rule tied to a wall-clock time.

### 24.2 Cron expressions

A cron schedule can specify a named timezone.

The platform's documented daylight-saving behavior determines what happens for nonexistent or repeated local times.

For EventBridge Scheduler, a nonexistent spring-forward invocation is skipped, while an ambiguous fall-back invocation is executed once.

### 24.3 Invocation windows

A flexible time window allows the platform to invoke work within a configured interval.

This can reduce concentrated bursts.

But the job must not assume that invocation always begins at an exact second.

### 24.4 Managed triggering isn't managed correctness

The scheduler may invoke a queue or function.

Your application still needs to decide which business occurrence is due, whether it has already completed, and whether a retry can safely reproduce the operation.

## 25. Why You Shouldn't Embed Every Cron in Every API Replica

Small applications often begin with in-process scheduling libraries.

That can be a perfectly reasonable choice for noncritical work in a single-process environment.

But consider what happens after deployment architecture changes.

A service scales from one replica to four.

Every replica initializes the scheduler.

Now the same function may run four times.

Or the deployment platform restarts the service at midnight.

The timer never fires.

Or a process shuts down while a scheduled operation is still running.

The application loses track of progress.

### 25.1 Separate scheduling from execution when appropriate

A dedicated scheduler can create durable job occurrences.

Workers can process those occurrences independently.

The scheduler no longer needs to perform every business operation itself.

### 25.2 The queue isn't the scheduler

A queue transports work.

It doesn't automatically know which business dates must be reconciled.

The scheduling component must determine due occurrences and enqueue them reliably.

### 25.3 Keep complexity proportional

A small internal maintenance job may be fine as a cron task on one host.

A business-critical monthly settlement requires stronger evidence and recovery.

The architecture should reflect the consequences of missing or duplicating work.

## 26. Long-Running Scheduled Work

Suppose Mercury runs a monthly settlement job.

The job can take several hours.

It processes millions of records, contacts external providers, and generates reconciliation reports.

### 26.1 A lease must outlive individual steps safely

A single fixed thirty-second lease isn't appropriate unless the worker can renew it and the recovery logic handles expiration.

The worker should periodically demonstrate ownership while processing bounded units of work.

### 26.2 Progress checkpoints

As in SE325-L02, the job should record durable progress.

If the worker crashes, recovery shouldn't start from the beginning unnecessarily.

### 26.3 Ownership and checkpoints have different purposes

The lease says which worker may currently perform work.

The checkpoint says which work is durably complete.

You need both.

### 26.4 Cancellation

Stopping a scheduled job may prevent future processing.

It doesn't reverse already committed business effects.

A monthly billing job shouldn't be assumed safely reversible merely because its worker Pod can be deleted.

### 26.5 Job duration may exceed the recurrence interval

A job scheduled every hour may occasionally take ninety minutes.

The overlap policy must be defined.

Otherwise the system may quietly accumulate competing executions or skip required periods.

## 27. Business Effects Need Their Own Idempotency

Let's return to invoice preparation.

Suppose the scheduled occurrence is uniquely identified as:

`prepare-invoices / 2026-10-28`

Within that run, the application processes three bookings.

Each booking produces an invoice record.

What prevents the same invoice from being created twice?

A suitable database uniqueness constraint might identify one invoice per booking and accounting period.

The scheduled occurrence ID alone may not be enough.

### 27.1 The effect's business identity

Use an identity appropriate to the operation.

For example:

`invoice / booking-482 / business-day-2026-10-28`

The database can enforce uniqueness for that logical effect.

### 27.2 External payment and email operations

If the job contacts an external provider, the application needs a compatible idempotency or reconciliation strategy.

A local database uniqueness constraint doesn't necessarily prevent an external effect that happened before the local transaction committed.

### 27.3 Never treat a timeout as proof of failure

Suppose the invoice email provider accepts a message.

The response is lost.

The worker sees a timeout.

Retrying may send another email.

The system must determine whether the provider supports idempotency, message identity, or authoritative status lookup.

### 27.4 Exactly-once outcomes require end-to-end cooperation

No cron expression can guarantee that an arbitrary external side effect occurs exactly once.

Correctness depends on the entire workflow.

## 28. Reconciliation Is the Safety Net

A scheduler can miss an occurrence.

A worker can crash.

A completion acknowledgment can disappear.

A lease can expire.

A downstream system can respond ambiguously.

How does the business recover?

Reconciliation.

### 28.1 Enumerate expected work

Suppose finance requires an invoice-preparation occurrence for every completed business day.

The system can enumerate those expected periods.

### 28.2 Compare with durable results

For each period, inspect whether the required business effects exist and whether the occurrence has been verified complete.

### 28.3 Repair missing effects

If an invoice record is missing, create or resume the corresponding operation using its stable identity.

### 28.4 Detect unexpected duplicates

A reconciliation process should also identify conflicting or duplicate results.

It may not be able to undo an already sent email or external payment automatically.

But it can provide evidence for compensation or human review.

### 28.5 Don't blindly replay everything

A reconciliation job should act according to authoritative current state.

It shouldn't assume that every missing completion flag means all underlying work must be performed from scratch.

## 29. A Failure Matrix for Scheduled Jobs

Let's summarize the critical failure windows.

### Before occurrence creation

The scheduler may be unavailable.

A catch-up process should determine whether the occurrence is still required.

### After occurrence creation, before worker claim

The work exists durably.

An eligible worker can claim it later.

### After claim, before any effects

The worker may crash.

Lease expiration allows recovery.

### After effects, before completion recording

The operation's results may already exist.

A retry must inspect and reuse those durable effects safely.

### After completion recording, before scheduler acknowledgment

The scheduler may retry or inspect the occurrence again.

The completed state should prevent a second logical business operation.

### After lease expiration, before old worker stops

A stale worker may resume.

Fencing and business-level idempotency must prevent invalid effects.

### During a clock transition

A local scheduled time may be ambiguous or nonexistent.

The scheduler's timezone and occurrence policy must determine the intended behavior.

## 30. Monitoring a Scheduler Properly

A dashboard reporting that the scheduler process is alive doesn't prove every expected job executed.

Useful signals include several different categories.

### 30.1 Scheduled versus created

How many occurrences should have existed?

How many were actually created?

### 30.2 Created versus claimed

Are occurrences waiting unusually long before a worker begins?

### 30.3 Claimed versus completed

Are jobs becoming stuck, retrying, or losing ownership?

### 30.4 Schedule lag

How late does execution begin relative to its intended time?

### 30.5 Execution duration

How long do jobs run, and how does that compare with the schedule interval?

### 30.6 Business completeness

Were the expected invoice records or reconciliation results actually produced?

### 30.7 Duplicate attempts

How many occurrences required multiple execution attempts?

Attempts are not necessarily incidents, but rising retry rates may indicate instability.

### 30.8 Stale workers

How often do workers attempt operations after losing ownership?

Frequent fencing rejection can reveal process pauses, lease configuration problems, or network partitions.

## 31. The Incident Investigation

Return to Mercury's overnight billing failure.

Finance reports duplicate invoices.

One accounting day is also missing.

Start by separating the two incidents.

For the duplicate day, determine how many scheduler replicas were active.

Inspect whether they both created or claimed the same occurrence.

Identify which invoice records were committed.

Check uniqueness and downstream notification behavior.

For the missing day, determine whether the scheduler was unavailable at the intended launch time.

Inspect the catch-up policy.

Check whether the occurrence was created but never claimed, or whether no occurrence record exists.

Then inspect the relevant timezone and calendar rules.

### 31.1 Don't repair symptoms blindly

Re-running the entire billing job may duplicate effects.

Deleting duplicate database rows may not correct already sent invoices.

Restarting the scheduler may create additional occurrences.

The recovery procedure should be based on authoritative business state.

### 31.2 Correct the scheduling layer

Ensure expected occurrences have durable identities.

Establish safe claims.

Define lease and ownership semantics.

Prevent stale workers from committing invalid effects.

### 31.3 Correct the business layer

Enforce appropriate uniqueness and idempotency.

Reconcile uncertain external operations.

Verify each required business period.

### 31.4 Correct the calendar policy

State the timezone explicitly.

Define the handling of missed and overlapping occurrences.

Test daylight-saving boundaries relevant to the schedule.

## 32. The Senior Engineer's Scheduling Model

A senior engineer doesn't need to implement a distributed consensus service to use scheduled jobs responsibly.

They need to recognize the boundaries.

The calendar determines what is due.

The scheduler records the occurrence.

The ownership mechanism determines who may act.

The worker performs bounded operations.

The business data establishes whether those operations actually succeeded.

Reconciliation repairs uncertainty.

And observability reveals what was missed, duplicated, or delayed.

A cron expression is the beginning of the design—not the entire design.

---

# The Oral Examination

Answer aloud before reading the solutions.

## Question 1 — Multiple Replicas

A Node.js backend runs a cron scheduler inside the application process.

The deployment scales from one Pod to four.

What new risk appears?

How would you address it?

## Question 2 — The Missing Midnight

A daily billing job was due at midnight.

The scheduler recovers at 03:17.

Should it run immediately?

What information determines the answer?

## Question 3 — Occurrence Identity

Why should a daily financial job be identified by a business period rather than simply by its actual process start time?

## Question 4 — The Lease

Worker A holds a lease.

The lease expires during a long pause.

Worker B claims the same occurrence.

Worker A resumes.

Why is the lease alone insufficient?

## Question 5 — Fencing

What does a fencing token prevent?

Where must the token be checked?

Why might it fail to protect an external email API?

## Question 6 — The Commit-Acknowledgment Gap

An invoice record is committed.

The worker crashes before recording that the scheduled occurrence completed.

What should happen on retry?

## Question 7 — The Daylight-Saving Boundary

A job is scheduled daily at 03:30 Europe/Vilnius.

What makes March 29 and October 25, 2026, special?

How should a production scheduler handle those dates?

## Question 8 — Elapsed Time Versus Calendar Time

Why isn't running every twenty-four hours always equivalent to running at 09:00 local time every day?

## Question 9 — Kubernetes CronJobs

Does `concurrencyPolicy: Forbid` guarantee that an arbitrary invoice-processing business operation can never execute twice?

Explain.

## Question 10 — The Overlapping Run

A job runs every five minutes but occasionally takes eight minutes.

What policies could the scheduler implement?

Which would you choose for a replaceable cache refresh versus a financial reconciliation?

## Question 11 — Advisory Locks

Why might a PostgreSQL advisory lock help coordinate work but fail to provide enough information for recovery of missed business periods?

## Question 12 — Senior Design

Design a daily invoice-preparation system that survives scheduler failover, duplicate launch attempts, worker crashes, clock changes, missed runs, and uncertain completion.

Explain how you'd verify that all required invoices were prepared.

---

# Solutions and Discussion

## Solution 1 — Replica Multiplication

Each backend replica may independently initialize the scheduler.

Four replicas can launch the same logical job.

Move scheduling into an appropriately coordinated component or use durable occurrence claims and business idempotency.

## Solution 2 — Catch-Up Policy

The correct action depends on the business contract.

A daily financial occurrence may need catch-up.

A disposable cache refresh may be skipped.

The system should identify the missed scheduled period rather than derive a new period from the recovery time.

## Solution 3 — Stable Business Identity

A business period remains the same even when an attempt runs late.

This allows retries, reconciliation, and duplicate detection to refer to one logical occurrence.

## Solution 4 — Expired Ownership

Worker A may continue operating after its lease has expired.

A lease alone doesn't prevent stale actions.

Use ownership validation, fencing where supported, and idempotent business effects.

## Solution 5 — Fencing Enforcement

A monotonically increasing token distinguishes old ownership from new ownership.

The destination performing the operation must reject stale tokens.

An external email provider that doesn't understand the token may still accept a stale worker's request.

## Solution 6 — Recover from Durable Evidence

The retry should inspect the authoritative invoice record and avoid creating a duplicate logical invoice.

The missing completion acknowledgment isn't proof that the business effect failed.

## Solution 7 — Local-Time Ambiguity

On March 29, 2026, local 03:30 doesn't exist in Europe/Vilnius.

On October 25, 2026, it occurs twice.

The business must define a policy, and the selected scheduler's behavior must be verified against it.

## Solution 8 — Different Time Models

Twenty-four hours is a duration.

09:00 local time is a calendar-time rule.

Daylight-saving transitions can make the elapsed interval between local occurrences different from twenty-four hours.

## Solution 9 — CronJob Limits

No.

The policy controls overlapping Jobs associated with the CronJob under Kubernetes's scheduling behavior.

It doesn't enforce arbitrary business idempotency, coordinate unrelated schedulers, or eliminate every duplicate-job possibility.

## Solution 10 — Overlap Policy

Possible choices include allowing overlap, forbidding it, replacing active work, or preserving every occurrence for serial processing.

A cache refresh may skip obsolete intermediate runs.

A financial reconciliation may require durable catch-up of every period.

## Solution 11 — Durable History

An advisory lock coordinates current ownership.

It doesn't inherently record which business days were required, completed, skipped, or left uncertain.

A durable occurrence ledger provides that history.

## Solution 12 — Reliable Daily Work

Generate durable occurrences for each required business period.

Enforce uniqueness.

Use safe worker claims and expiring leases.

Prevent stale ownership through appropriate fencing and business-effect controls.

Make invoice preparation idempotent by stable business identity.

Reconcile missing or uncertain effects.

Monitor schedule lag, completion, duplicates, and business completeness.

---

# The Mental Model Worth Keeping

A recurring job has three fundamental responsibilities.

**Scheduling:** Decide which logical occurrence is due.

**Ownership:** Decide which worker may execute it.

**Correctness:** Ensure the required business effect is produced without invalid duplication.

These responsibilities must survive process crashes, failover, clock changes, and lost acknowledgments.

A lease helps recover ownership.

A fencing token helps reject stale ownership.

An idempotency key or durable business identity helps prevent repeated effects.

A catch-up policy determines what happens to missed periods.

Reconciliation establishes whether the required work actually happened.

The questions worth remembering are:

**Which occurrence is this?**

**Who currently owns it?**

**Can an old owner still act?**

**What if the operation completed but its acknowledgment was lost?**

**What should happen to missed or overlapping occurrences?**

**What evidence proves the business effect exists?**

---

# Next Lecture — SE325-L04: Production Data Repair, Audit, and Lifecycle

We've investigated how scheduled processes can duplicate, omit, or delay business operations.

The next lecture deals with the consequences when production data becomes incorrect.

Support discovers a reservation with an impossible state.

An engineer proposes a manual SQL update.

But PostgreSQL is not the only system holding the information.

Redis has a cached representation.

The search index contains an older version.

Analytics has already processed the incorrect event.

A scheduled reconciliation job may overwrite the proposed correction tomorrow.

And the audit trail must explain what happened.

SE325-L04 will investigate safe production data repairs, approvals, auditability, reconciliation, retention, and deletion across multiple systems.

*The spoken lecture ends here. The following exercises are a practical investigation rather than part of the continuous audio lecture.*

---

# Optional Practical Lab — The Scheduler That Lost Ownership

## Lab Contract

This laboratory uses Python's standard library and SQLite.

It simulates a recurring business occurrence, two competing scheduler workers, an expiring lease, a fencing token, and durable business effects.

There are no real payments, invoices, emails, or cloud operations.

The example deliberately distinguishes a simulated invoice-preparation ledger from an external side effect.

The laboratory demonstrates:

- Unique logical occurrence identity.
- Atomic claim attempts.
- Lease expiration.
- Fencing-token increments.
- A crash after durable effects but before completion recording.
- Safe repeated database effects.
- Rejection of a stale worker.
- Calendar-time ambiguity across daylight-saving transitions.

It is intentionally single-machine and command-driven.

It does not claim to simulate real network partitions or the complete behavior of a production distributed database.

Time is controlled by manually supplied **logical seconds**, allowing us to reproduce a lease expiration without actually waiting.

## Lab 1 — Create the Scheduler Simulator

Create a directory named `se325-scheduling-lab`.

Save this script as `studio.py`.

The database is created only in the working directory.

The initialization command refuses to overwrite an existing laboratory database.

### The simulator

```python id="s32503lab"
import argparse
import sqlite3

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


DB = Path("se325_scheduling_lab.sqlite3")

JOB = "daily-invoice-preparation"
DAY = "2026-10-29"

# Simulated logical seconds, not real time.
LEASE = 30


def db():
    if not DB.exists():
        raise SystemExit("Run init first")

    connection = sqlite3.connect(
        DB,
        timeout=5,
    )

    connection.row_factory = sqlite3.Row

    return connection


def init():
    if DB.exists():
        raise SystemExit(
            "Lab database already exists. "
            "Delete it yourself to reset."
        )

    with sqlite3.connect(DB) as connection:
        connection.executescript("""
            CREATE TABLE runs (
                job TEXT NOT NULL,
                business_day TEXT NOT NULL,
                state TEXT NOT NULL,
                owner TEXT NOT NULL,
                fence INTEGER NOT NULL,
                lease_until INTEGER NOT NULL,
                PRIMARY KEY (job, business_day)
            );

            CREATE TABLE effects (
                business_day TEXT NOT NULL,
                invoice_id TEXT NOT NULL,
                action TEXT NOT NULL,
                PRIMARY KEY (
                    business_day,
                    invoice_id
                )
            );
        """)

    print(
        "Created isolated SQLite lab. "
        "No emails or charges are sent."
    )


def claim(owner, at):
    with db() as connection:

        connection.execute("BEGIN IMMEDIATE")

        row = connection.execute(
            """
            SELECT *
            FROM runs
            WHERE job = ?
              AND business_day = ?
            """,
            (JOB, DAY),
        ).fetchone()

        if row is None:

            connection.execute(
                """
                INSERT INTO runs
                VALUES (?,?,?,?,?,?)
                """,
                (
                    JOB,
                    DAY,
                    "RUNNING",
                    owner,
                    1,
                    at + LEASE,
                ),
            )

            print(
                f"{owner}: CLAIMED fence=1 "
                f"until={at + LEASE}"
            )

        elif row["state"] == "COMPLETED":

            print(
                f"{owner}: DENIED already completed"
            )

        elif row["lease_until"] > at:

            print(
                f"{owner}: DENIED lease owned by "
                f"{row['owner']} through "
                f"{row['lease_until']}"
            )

        else:

            new_fence = row["fence"] + 1

            connection.execute(
                """
                UPDATE runs
                SET owner = ?,
                    fence = ?,
                    lease_until = ?,
                    state = ?
                WHERE job = ?
                  AND business_day = ?
                """,
                (
                    owner,
                    new_fence,
                    at + LEASE,
                    "RUNNING",
                    JOB,
                    DAY,
                ),
            )

            print(
                f"{owner}: RECOVERED "
                f"fence={new_fence} "
                f"until={at + LEASE}"
            )


def process(owner, fence, at, crash):

    with db() as connection:

        connection.execute("BEGIN IMMEDIATE")

        row = connection.execute(
            """
            SELECT *
            FROM runs
            WHERE job = ?
              AND business_day = ?
            """,
            (JOB, DAY),
        ).fetchone()

        if (
            not row
            or row["state"] != "RUNNING"
            or row["owner"] != owner
            or row["fence"] != fence
            or row["lease_until"] <= at
        ):

            print(
                f"{owner}: REJECTED stale ownership "
                "or expired lease"
            )

            return

        # These are simulated durable records,
        # not emails or actual invoice issuance.
        for invoice in (
            "INV-101",
            "INV-102",
            "INV-103",
        ):

            connection.execute(
                """
                INSERT OR IGNORE INTO effects
                VALUES (?,?,?)
                """,
                (
                    DAY,
                    invoice,
                    "PREPARED_NOT_SENT",
                ),
            )

        if not crash:

            connection.execute(
                """
                UPDATE runs
                SET state = 'COMPLETED'
                WHERE job = ?
                  AND business_day = ?
                  AND owner = ?
                  AND fence = ?
                """,
                (
                    JOB,
                    DAY,
                    owner,
                    fence,
                ),
            )

    if crash:

        print(
            f"{owner}: Simulated lost completion "
            "acknowledgment; durable effects "
            "exist, but run remains RUNNING"
        )

    else:

        print(
            f"{owner}: COMPLETED; "
            "duplicate effect inserts ignored"
        )


def finish(owner, fence, at):

    with db() as connection:

        connection.execute("BEGIN IMMEDIATE")

        result = connection.execute(
            """
            UPDATE runs
            SET state = 'COMPLETED'
            WHERE job = ?
              AND business_day = ?
              AND owner = ?
              AND fence = ?
              AND state = 'RUNNING'
              AND lease_until > ?
            """,
            (
                JOB,
                DAY,
                owner,
                fence,
                at,
            ),
        )

        if result.rowcount:

            print(f"{owner}: COMPLETED")

        else:

            print(
                f"{owner}: DENIED stale token, "
                "lease or state"
            )


def status():

    with db() as connection:

        runs = connection.execute(
            "SELECT * FROM runs"
        ).fetchall()

        effects = connection.execute(
            """
            SELECT *
            FROM effects
            ORDER BY invoice_id
            """
        ).fetchall()

    print(
        "Runs:",
        [dict(row) for row in runs],
    )

    print(
        "Effects:",
        [dict(row) for row in effects],
    )


def dst():

    zone = ZoneInfo("Europe/Vilnius")

    for year, month, day in (
        (2026, 3, 29),
        (2026, 10, 25),
    ):

        local = datetime(
            year,
            month,
            day,
            3,
            30,
        )

        choices = []

        for fold in (0, 1):

            proposed = local.replace(
                tzinfo=zone,
                fold=fold,
            )

            utc = proposed.astimezone(
                timezone.utc
            )

            back = utc.astimezone(zone)

            valid = (
                back.replace(tzinfo=None)
                == local
            )

            choices.append(
                (utc.isoformat(), valid)
            )

        if not any(
            value[1] for value in choices
        ):

            classification = "NONEXISTENT"

        elif (
            choices[0][1]
            and choices[1][1]
            and choices[0][0] != choices[1][0]
        ):

            classification = "AMBIGUOUS"

        else:

            classification = "UNIQUE"

        print(
            f"{local} Europe/Vilnius: "
            f"{classification}"
        )

        print(
            "UTC candidates:",
            choices,
        )


parser = argparse.ArgumentParser()

sub = parser.add_subparsers(
    dest="cmd",
    required=True,
)

sub.add_parser("init")
sub.add_parser("status")
sub.add_parser("dst")

for command in (
    "claim",
    "process",
    "finish",
):

    item = sub.add_parser(command)

    item.add_argument("owner")

    item.add_argument(
        "at",
        type=int,
    )

    if command != "claim":

        item.add_argument(
            "fence",
            type=int,
        )

    if command == "process":

        item.add_argument(
            "--crash",
            action="store_true",
        )


args = parser.parse_args()


if args.cmd == "init":

    init()

elif args.cmd == "claim":

    claim(args.owner, args.at)

elif args.cmd == "process":

    process(
        args.owner,
        args.fence,
        args.at,
        args.crash,
    )

elif args.cmd == "finish":

    finish(
        args.owner,
        args.fence,
        args.at,
    )

elif args.cmd == "status":

    status()

elif args.cmd == "dst":

    dst()
```

The example treats `runs` as the durable ownership record and `effects` as the authoritative local demonstration of prepared invoice records.

The unique key on `effects` prevents duplicate records for the same invoice and business day.

This is not a general guarantee of exactly-once external execution.

---

# Lab 2 — Two Schedulers Compete

Initialize the lab.

```bash id="s32503cmd1"
python studio.py init
```

Worker A attempts to claim the scheduled occurrence at logical time 1000.

```bash id="s32503cmd2"
python studio.py claim A 1000
```

The simulated lease lasts thirty seconds.

It expires at logical time 1030.

Now Worker B attempts to claim at time 1005.

```bash id="s32503cmd3"
python studio.py claim B 1005
```

### Predict

Should B succeed?

Why or why not?

### Inspect

```bash id="s32503cmd4"
python studio.py status
```

The expected owner is A, with fencing token 1.

### Required explanation

What prevents B from claiming?

What does the database transaction contribute?

Why would a naive read-then-write ownership check be unsafe under real concurrency?

---

# Lab 3 — The Worker Completes Effects but Loses Acknowledgment

Worker A processes the occurrence.

The operation writes three simulated invoice-preparation records.

But it deliberately leaves the run in the `RUNNING` state.

```bash id="s32503cmd5"
python studio.py process A 1010 1 --crash
```

Now inspect the database.

```bash id="s32503cmd6"
python studio.py status
```

### Observe

The three effect records exist.

The occurrence remains `RUNNING`.

### Questions

Did the business records commit?

Did the scheduler record completion?

Can we infer from the missing completion flag that the invoice records don't exist?

If another worker executes the occurrence, what prevents duplicate database records?

### Acceptance criteria

You distinguish durable business effects from completion acknowledgment.

---

# Lab 4 — Failover and Fencing

The logical clock advances beyond A's lease expiration.

Worker B claims the unfinished occurrence.

```bash id="s32503cmd7"
python studio.py claim B 1035
```

B receives fencing token 2.

Now imagine that Worker A resumes.

It attempts to mark the occurrence completed using its old token.

```bash id="s32503cmd8"
python studio.py finish A 1 1036
```

### Predict

Should the old owner succeed?

The database should reject the stale completion attempt.

### Investigation

Explain why A's previous ownership isn't sufficient.

What changed when B acquired the new lease?

Where is the fencing token enforced?

### Important limitation

In this simulation, the database checks the fencing token before accepting the operation.

If A had directly sent an email through an external service, the database check wouldn't automatically retract or prevent that email.

The external effect would need its own safety mechanism.

---

# Lab 5 — Recover Without Duplicating Business Records

Worker B processes the same logical occurrence.

```bash id="s32503cmd9"
python studio.py process B 1040 2
```

Inspect the final state.

```bash id="s32503cmd10"
python studio.py status
```

The occurrence should be `COMPLETED`.

Exactly three simulated invoice-preparation records should exist.

Worker B retried the logical work, but the unique business identity prevented duplicate records.

Now try to claim the completed occurrence again.

```bash id="s32503cmd11"
python studio.py claim A 1041
```

The claim should be denied.

### Required explanation

Which mechanism prevents duplicate occurrence creation?

Which prevents competing active ownership?

Which rejects stale ownership?

Which prevents duplicate business records?

These are separate protections.

---

# Lab 6 — The Daylight-Saving Experiment

The database isn't needed for this part.

Run:

```bash id="s32503cmd12"
python studio.py dst
```

The script examines local 03:30 in Europe/Vilnius on two dates.

### March 29, 2026

The script should classify local 03:30 as nonexistent.

Neither candidate maps back to the requested local wall-clock time.

### October 25, 2026

The script should classify local 03:30 as ambiguous.

Two different UTC instants correspond to the same local wall-clock time.

### Your task

Design a daily business job scheduled at 03:30 Europe/Vilnius.

Specify what should happen on each transition date.

Explain whether the operation's business identity should be tied to the local date, the first occurrence, the second occurrence, or something else.

### Extra challenge

Suppose the requirement changes to:

"Execute every twenty-four hours."

How would the interpretation differ?

Why shouldn't you simply assume that daily local scheduling and fixed elapsed intervals are equivalent?

---

# Lab 7 — Kubernetes CronJob Review

Consider this conceptual Kubernetes CronJob configuration.

It schedules a job every day at 03:30 Europe/Vilnius.

```yaml id="s32503k8s"
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-invoice-preparation
spec:
  schedule: "30 3 * * *"
  timeZone: "Europe/Vilnius"
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 3600
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: Never
          containers:
            - name: worker
              image: example/invoice-worker:1.0
```

This is a structural teaching example.

The image is illustrative, not a published workload you should deploy.

### Task A — Explain the schedule

What does the cron expression mean?

Which timezone is used?

### Task B — Explain the concurrency policy

What happens when a previous Job remains active?

Does `Forbid` guarantee that an invoice can never be prepared twice?

### Task C — Explain the starting deadline

What happens if the controller misses a scheduled start?

How does the one-hour deadline affect whether the late Job may still be created?

### Task D — Explain the missing business logic

Which important requirements are not represented by this YAML?

Your answer should include occurrence identity, business idempotency, and authoritative completion verification.

---

# Lab 8 — The Missed-Day Policy

## Scenario

Mercury has three scheduled tasks.

**Task A:** Refresh a disposable hotel-summary cache every five minutes.

**Task B:** Prepare daily invoice records.

**Task C:** Send a promotional reminder before a booking begins.

The scheduler is unavailable for four hours.

### Your task

Define a catch-up policy for each task.

Consider whether to:

- Skip missed occurrences.
- Execute only the latest occurrence.
- Catch up every missed occurrence.
- Apply a deadline.
- Request human review.

### Challenge

The invoice-preparation job has missed forty days.

Should the system launch forty full database jobs simultaneously?

Explain how to preserve completeness without overwhelming production.

---

# Lab 9 — The Overlapping Job

A job runs every five minutes.

Each execution takes eight minutes.

### Task A

Describe what happens if overlapping executions are allowed.

### Task B

Describe what happens if new occurrences are skipped while the previous one remains active.

### Task C

Describe what happens if the scheduler replaces the active execution.

### Task D

Design a queue-based approach that preserves all required occurrences with bounded concurrency.

### Business distinction

Choose appropriate policies for a disposable cache refresh and a required financial reconciliation.

Explain why the same choice may be wrong for the other task.

---

# Lab 10 — The External Email Problem

## Starting symptom

The daily invoice-preparation job creates the correct records.

It then sends three emails through an external email provider.

The provider accepts the requests.

The worker times out before receiving confirmations.

The scheduler retries the occurrence.

The database prevents duplicate invoice records.

But customers receive duplicate emails.

### Your task

Explain why the database uniqueness constraint wasn't sufficient.

Design a durable notification obligation.

Determine what kind of idempotency, provider message identity, or reconciliation capability you need.

Describe what happens when the email provider cannot prove whether a particular message was accepted.

### Required limitation

Do not claim that a local `sent=true` flag automatically guarantees exactly-once delivery.

The flag and the external send cannot ordinarily be committed in one database transaction.

---

# Final Incident — The Nightly Billing Mystery

## Business context

Mercury prepares invoice records for each completed business day.

It operates two scheduler replicas for availability.

The system must tolerate restarts and missed execution windows.

## Observed symptoms

Finance reports duplicate invoices for one day.

The following business day has no invoice records.

Scheduler logs show a leader failover.

One worker resumed after losing ownership.

A completion acknowledgment was lost.

A scheduled run was missed during an outage.

### Required incident report

Explain:

**Occurrence identity:** How is each business day represented?

**Scheduling policy:** What happens when a required run is missed?

**Ownership:** How do workers claim an occurrence?

**Failover:** What happens when ownership expires?

**Fencing:** How are stale workers prevented from committing invalid results?

**Business idempotency:** How are duplicate invoice records prevented?

**External effects:** How are email or payment side effects reconciled?

**Time semantics:** Which timezone determines the business period?

**Monitoring:** How do you discover missing or duplicate occurrences?

**Recovery:** How do you restore complete, correct business state without blindly replaying everything?

### Senior-level challenge

Your interviewer says:

"Why are we building all these controls? Kubernetes CronJob already supports `Forbid`. Surely that's enough."

Explain the difference between preventing some overlapping Job launches and guaranteeing the correctness of a distributed financial workflow.

---

# STOP — Independent Investigation Ends Here

Do not read the following notes until you've completed the exercises.

The objective is to develop a reliable scheduling model rather than memorize a particular cron implementation.

---

# Lab Diagnostic Notes

## Competing Claims

Worker A acquires the occurrence first.

Worker B's claim is rejected while the lease remains valid.

The database transaction protects the ownership decision.

## Lost Completion

Worker A writes durable simulated effects but leaves the occurrence marked running.

The missing completion acknowledgment doesn't mean the business records are absent.

## Fencing

Worker B acquires a newer ownership generation after A's lease expires.

The database rejects A's stale token.

This prevents an old owner from changing the protected database state.

## Idempotent Recovery

Worker B processes the same logical occurrence.

The database's unique business-effect key prevents duplicate records.

The occurrence can then be marked completed.

## Timezone Behavior

The spring transition makes local 03:30 nonexistent.

The autumn transition makes it ambiguous.

A scheduling system needs an explicit policy for these conditions.

The business-period identity should not be inferred solely from an attempt's start time.

## Kubernetes

CronJob concurrency policies control scheduling behavior for the relevant CronJob.

They don't replace business idempotency.

A Job can be retried, recreated, or duplicated under failure conditions.

The application should tolerate uncertain execution.

## Catch-Up

Disposable refreshes can often skip obsolete periods.

Financial work may need every missing business period reconciled.

Late work should be admitted through bounded capacity rather than an uncontrolled catch-up storm.

## External Effects

A local invoice uniqueness constraint doesn't prove that an external email was delivered only once.

The application needs a separate durable-effect and reconciliation strategy.

## Production Mental Model

Occurrence identity establishes what work is due.

Ownership controls which worker should perform it.

Fencing helps reject stale actors.

Business idempotency makes repeated attempts safe.

Catch-up policy decides what to do after outages.

Reconciliation establishes whether required effects actually occurred.

---

# Further Reading

Primary references:

- **Google SRE — Distributed Periodic Scheduling with Cron:** https://sre.google/sre-book/distributed-periodic-scheduling/
- **Kubernetes — CronJob Concepts:** https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/
- **Kubernetes — CronJob API Reference:** https://kubernetes.io/docs/reference/kubernetes-api/batch/cron-job-v1/
- **AWS EventBridge Scheduler — Schedule Types:** https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html
- **AWS EventBridge Scheduler — Flexible Time Windows:** https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-schedule-flexible-time-windows.html
- **PostgreSQL — Explicit and Advisory Locking:** https://www.postgresql.org/docs/current/explicit-locking.html
- **Python — `zoneinfo`: IANA Timezone Support:** https://docs.python.org/3/library/zoneinfo.html
- **Python — `datetime`: Aware and Naive Objects:** https://docs.python.org/3/library/datetime.html
- **Python — `sqlite3`: SQLite Database Interface:** https://docs.python.org/3/library/sqlite3.html
- **Martin Kleppmann — How to Do Distributed Locking:** https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html

Related programme chapters:

- SE320-L03 — Queues, Workers, and Asynchronous Workflows
- CS430-L01 — Distributed Systems and Partial Failure
- CS430-L05 — Designing Reliable Business Workflows
- CS330-L03 — Transactions and Isolation
- SE325-L02 — Bulk Imports, Exports, and Background Data Operations
- SE325-L04 — Production Data Repair, Audit, and Lifecycle
- SE440-L02 — Reliability Engineering and Incident Response
- SE450-L02 — Pods, Deployments, Jobs, and Controllers

---

# Dense Cheatsheet — Interview Glance Card

*The following card is fenced for voice-reader skipping and screen-based revision.*

```text id="s32503card"
SE325-L03 — SCHEDULED JOBS AND DISTRIBUTED EXECUTION
=====================================================

THREE RESPONSIBILITIES

SCHEDULE:
  When is work due?

OWNERSHIP:
  Which worker may execute it?

CORRECTNESS:
  Did the intended business effect occur?

A cron expression solves only
part of the first question.

TIME CONCEPTS
-------------
Instant:
  Absolute point on timeline

Duration:
  Elapsed time

Local date:
  Calendar period in a timezone

Scheduled occurrence:
  Intended execution slot

Business period:
  Data interval being processed

Execution timestamp != business period.

CRON
----
Traditional Unix cron:
  minute hour day month weekday

Other schedulers use different syntax.

Always verify:
  implementation
  timezone
  DST behavior
  missed-run policy
  overlap policy

OCCURRENCE IDENTITY
-------------------
job + business period

Example:
  invoice-preparation / 2026-10-28

One logical occurrence.
Potentially many attempts.

MULTIPLE REPLICAS
-----------------
Every application replica may
initialize its own timer.

Scaling 1 -> 4 replicas can
produce four launch attempts.

COORDINATION
------------
Unique occurrence record.
Atomic claim.
Owner identity.
Lease expiration.
Recovery after failure.

LEASE
-----
Temporary ownership.
Expires after deadline.
May be renewed.

Lease expiry permits recovery.

But old worker may resume.

FENCING
-------
Monotonically increasing token.

New owner gets higher token.

Destination rejects stale tokens.

Token must be enforced by
the operation's actual receiver.

External services may not support it.

IDEMPOTENCY
-----------
Scheduler ID != sufficient
business-effect identity.

Use stable domain identity.

Example:
  invoice / booking / accounting day

Unique DB effect may be enforceable.

External sends still need
their own safety strategy.

LOST ACKNOWLEDGMENT
-------------------
Operation may have committed.
Worker crashes before recording success.

Missing acknowledgment != failure.

Inspect authoritative effects.

AT-MOST-ONCE LAUNCH
-------------------
Lower duplicate-launch risk.
May miss work after failure.

AT-LEAST-ONCE ATTEMPT
---------------------
Improves recovery.
Requires safe repeated execution.

EXACTLY-ONCE BUSINESS EFFECT
----------------------------
Requires end-to-end correctness,
idempotency, or reconciliation.

Cron alone cannot guarantee it.

MISSED RUNS
-----------
Possible policies:

Skip
Run latest
Catch up all
Bound backlog
Apply deadline
Manual review

Choose by business meaning.

DST
---
Nonexistent local time:
  Spring clock jump

Ambiguous local time:
  Autumn repeated hour

UTC instant != local schedule.

Every 24 hours !=
same local clock time every day.

OVERLAP
-------
Allow:
  concurrent occurrences

Forbid:
  skip or delay overlap

Replace:
  terminate existing work

Queue:
  preserve occurrences with
  bounded execution capacity

Choose by business semantics.

KUBERNETES CRONJOB
------------------
schedule
timeZone
concurrencyPolicy
startingDeadlineSeconds
jobTemplate

Approximate creation.
Duplicates/misses possible.

Forbid is not end-to-end
business exactly-once.

EVENTBRIDGE SCHEDULER
---------------------
Cron/rate/one-time schedules.
Timezone support.
Retry configuration.
Flexible invocation windows.

Managed triggering still needs
safe business execution.

ADVISORY LOCKS
--------------
Coordinate current ownership.

Session and transaction locks
have different lifetimes.

Lock != durable job history.

LONG-RUNNING JOBS
-----------------
Renew lease safely.
Checkpoint completed units.
Protect against old owners.
Allow cooperative cancellation.
Define overlap/catch-up behavior.

MONITORING
----------
Expected occurrences
Created occurrences
Claim latency
Schedule lag
Run duration
Retry count
Lease expirations
Stale-token rejections
Business completeness
Missing periods

RECONCILIATION
--------------
Enumerate expected business periods.

Compare with authoritative effects.

Resume missing or incomplete work.

Do not blindly replay all side effects.

FAILURE QUESTIONS
-----------------
Scheduler down?
Two replicas active?
Worker crashed?
Lease expired?
Old worker resumed?
Business effect committed?
Acknowledgment lost?
Clock repeated or skipped?
Previous run still active?
Provider outcome uncertain?

SENIOR MENTAL MODEL
-------------------
Calendar decides WHAT is due.

Coordinator decides WHO acts.

Business system decides
WHAT actually happened.

Reconciliation closes the gaps.

NEXT
----
SE325-L04
Production Data Repair,
Audit, and Lifecycle
```
