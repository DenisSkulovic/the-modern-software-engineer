---
id: SE440-L02
course: SE440
title: "Reliability Engineering and Incident Response"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [ENG401-S08]
prev: SE440-L01
next: SE440-L03
---


<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE325-L04
Preserve incident response, SLOs, runbooks, and backup/recovery theory here.
When SE325-L04 exists, connect backup/recovery concepts to the operational
data-repair and lifecycle workflow (approvals, audit, multi-store consistency).
Do not turn this lecture into a data-repair handbook.
-->










# SE440 — Production Reliability and Quality Engineering

## Lecture 02: Reliability Engineering and Incident Response

*Why redundant systems still fail, why backups are not recovery plans, and how engineers learn to make failure less catastrophic.*

---

## 1. The Highly Available System That Went Down Anyway

Your company operates a hotel-booking SaaS serving several thousand businesses across Europe.

Its infrastructure looks reassuringly professional:

- Three Node.js API instances distributed across two AWS Availability Zones.
- An Application Load Balancer.
- PostgreSQL on RDS with Multi-AZ failover.
- Redis for caching.
- SQS for background processing.
- Automated database backups.
- ECS services configured to replace unhealthy containers.

The architecture has redundancy, health checks, automated recovery, and managed infrastructure.

Management proudly describes it as *highly available*.

Then, at 11:42 on a Monday morning, the primary database instance experiences an infrastructure failure.

Amazon RDS initiates failover to its standby.

This is exactly the scenario the architecture was designed to survive.

Yet the application becomes unavailable for 38 minutes.

What happened?

The initial database interruption caused API requests to fail. Each API instance retried its queries several times, and some requests were also retried by upstream clients.

The retry traffic increased pressure on the recovering database.

Meanwhile, the application's health endpoint performed a database query. When that query failed, the endpoint returned HTTP 503.

ECS interpreted the failing health checks as evidence that application tasks were unhealthy and began replacing them.

New tasks started, opened fresh database connection pools, and immediately attempted to reconnect.

The recovering database received a wave of connection attempts from both existing requests and newly started application instances.

To make matters worse, the cache had recently expired for several popular search results. Requests that would ordinarily have been satisfied from Redis began hitting PostgreSQL.

The infrastructure's redundancy worked reasonably well. The database failover itself was not the main reason customers experienced 38 minutes of disruption.

The application's **recovery behavior amplified the original failure**.

This is one of the most important lessons of reliability engineering:

**A system's reliability is determined not only by whether its components can fail, but by how the rest of the system behaves when they do.**

Let's investigate how engineers design systems that fail less often, limit the consequences of failure, and recover without turning small incidents into large ones.

---

## 2. Reliability and Availability Are Not the Same Thing

These terms frequently appear together, but they describe different properties.

**Reliability** concerns the ability of a system to perform its intended functions correctly over a specified period and under specified conditions.

**Availability** concerns whether the system is accessible and capable of providing the required service when needed.

A service can be available but unreliable.

Imagine a payment API that responds successfully to every request but occasionally charges customers twice. Its HTTP availability may be excellent, but its business behavior is unacceptable.

Conversely, a service may implement transactions and business rules correctly but become inaccessible during frequent infrastructure outages.

High correctness does not compensate for being unreachable.

### Availability as a measurable property

A simple time-based availability calculation is:

\[
A = \frac{\text{Time available}}{\text{Total observed time}}
\]

For example, if a service is unavailable for 60 minutes during a 30-day period:

\[
A = \frac{43,200 - 60}{43,200}
\approx 99.861\%
\]

But this model raises important questions.

Is the application unavailable when one endpoint fails? When only corporate customers are affected? When requests take fifteen seconds instead of 200 milliseconds?

Modern systems often use request-based or event-based availability indicators rather than treating the entire service as simply up or down.

For example:

\[
A_{\text{requests}} =
\frac{\text{Successful eligible requests}}
{\text{Total eligible requests}}
\]

If the booking API successfully processes 999,000 of one million eligible requests, its measured request success ratio is 99.9%.

This doesn't imply that every minute was equally reliable or that every customer experienced the same service quality.

The definition of *successful* matters enormously.

An HTTP 200 response containing an invalid reservation confirmation is not meaningful business success.

### Durability is another distinct property

Durability concerns the preservation of data once the system has acknowledged that data as successfully stored.

A database can remain available while silently losing acknowledged writes because of a serious defect or incorrect storage configuration.

Likewise, a database may become temporarily unavailable without losing any committed data.

Availability, reliability, and durability overlap, but they should not be treated as interchangeable engineering objectives.

---

## 3. Why Redundancy Sometimes Does Nothing

Redundancy is one of the oldest techniques for improving reliability.

If one component may fail, create another capable of taking over.

Suppose an API instance has 99% availability during a particular observation period.

Under an extremely simplified mathematical model, if two instances fail independently and either one is sufficient to provide service, the probability that both are unavailable simultaneously is:

\[
P(\text{both fail}) = 0.01 \times 0.01 = 0.0001
\]

The resulting theoretical availability would be:

\[
A = 1 - 0.0001 = 99.99\%
\]

Two instances have improved theoretical availability from 99% to 99.99%.

Impressive.

Unfortunately, the calculation relies on assumptions that frequently do not hold.

### Independence is the difficult part

What happens if both instances depend on the same PostgreSQL database?

```text id="c9t2pv"
API Instance A ──┐
                 ├── PostgreSQL
API Instance B ──┘
```

If PostgreSQL becomes unavailable, both instances may lose the ability to process important requests.

The application instances are redundant, but the complete request path isn't.

Now imagine both API instances also use the same:

- Broken configuration.
- Expired credential.
- Defective deployment artifact.
- External authentication provider.
- Network gateway.
- Regional infrastructure dependency.

These shared dependencies create **correlated failures**.

A single event can affect multiple supposedly independent components.

### Failure domains

A failure domain is a boundary within which a particular failure may affect multiple resources.

Examples include:

| Failure domain | Potential impact |
|---|---|
| One process | One application instance |
| One host | All workloads running on that machine |
| One Availability Zone | Resources dependent on that AZ |
| One AWS Region | Regional workloads and dependencies |
| One shared database | Every operation requiring that database |
| One deployment artifact | Every instance running defective code |
| One shared credential | Every component depending on that credential |

Distributing API instances across AZs reduces their exposure to a single-zone infrastructure failure.

But if every instance runs the same defective software version, geographical redundancy offers little protection.

**Redundancy is valuable when it removes a meaningful shared failure mode, not merely when it increases the number of components.**

### Serial dependencies can reduce availability

Suppose an operation requires three independent services, each available 99% of the time.

If all three must succeed and their failures are independent, theoretical end-to-end availability is:

\[
0.99^3 \approx 97.03\%
\]

Adding mandatory dependencies may reduce the complete operation's availability even when each component is individually reliable.

Real systems are more complicated because requests have different paths, dependencies can degrade, and failures are often correlated.

Nevertheless, the principle is important: a request is only as available as the combination of resources its successful completion actually requires.

---

## 4. Failure Prevention, Containment, and Recovery

Reliability engineering becomes easier to reason about when we divide mechanisms into three broad categories.

**Prevention** reduces the likelihood that a failure occurs.

**Containment** reduces the scope or severity of a failure after it occurs.

**Recovery** restores acceptable operation after the system has been affected.

Consider PostgreSQL.

Using reliable infrastructure, correct configuration, tested migrations, and appropriate maintenance practices helps prevent certain failures.

Limiting database concurrency and isolating expensive workloads can prevent one problem from exhausting capacity for every customer.

Multi-AZ failover, backups, and restoration procedures help recover from different categories of failure.

These strategies work together.

| Mechanism | Primary benefit |
|---|---|
| Automated tests | Prevent selected defects reaching production |
| Redundant instances | Survive certain instance failures |
| Timeouts | Bound waiting on unresponsive operations |
| Circuit breakers | Limit repeated calls to failing dependencies |
| Bulkheads | Contain resource consumption across workloads |
| Graceful degradation | Preserve reduced functionality during failures |
| Automated failover | Restore service after supported infrastructure failures |
| Backups | Enable recovery from data loss or corruption |
| Runbooks | Reduce uncertainty during incident response |

Many mechanisms serve more than one category.

For example, a circuit breaker helps contain dependency failure and can also assist recovery by reducing pressure on the dependency.

The important point is to avoid expecting one mechanism to solve every problem.

A backup cannot make a running application highly available. A redundant API instance cannot restore corrupted data. A load balancer cannot correct a duplicate payment.

Reliability requires several different kinds of protection.

---

## 5. SLI, SLO, and SLA: Turning Reliability Into a Decision

How reliable should an application be?

The reflexive answer is often "as reliable as possible."

That sounds admirable but provides little guidance for engineering investment.

Achieving 99.9% availability may require one set of mechanisms. Pursuing 99.99% or 99.999% may require substantially greater investment, operational sophistication, and constraints on change.

A company needs a way to decide how much reliability matters.

### Service-Level Indicators

A **Service-Level Indicator**, or SLI, is a quantitative measurement of service behavior.

For example:

\[
SLI_{\text{availability}} =
\frac{\text{Successful checkout requests}}
{\text{Eligible checkout requests}}
\]

Or:

\[
SLI_{\text{latency}} =
\frac{\text{Requests completed within 500 ms}}
{\text{Eligible requests}}
\]

These indicators reflect different customer experiences.

A checkout API may have a latency objective and a correctness or success objective.

A background invoice-processing service might instead measure the fraction of invoices completed within five minutes.

The indicator should match something customers or downstream systems genuinely care about.

### Service-Level Objectives

A **Service-Level Objective**, or SLO, defines a target for an SLI over a particular measurement window.

For example:

> At least 99.9% of eligible reservation-creation requests must succeed during each rolling 30-day period.

Or:

> At least 99% of accepted invoice jobs must complete within five minutes over a rolling seven-day period.

These objectives turn vague reliability aspirations into measurable expectations.

They also require precise definitions.

If clients submit invalid requests, should those failures count against API availability? Usually, deliberately rejected invalid requests are classified differently from server failures.

If a payment provider declines a card correctly, is that an API failure? Generally not, even if the business transaction doesn't complete.

An SLI must distinguish expected business outcomes from failures of the service to perform its responsibilities.

### Service-Level Agreements

An **SLA** is a contractual commitment concerning service levels, potentially including commercial consequences when commitments are not met.

An internal engineering SLO and an externally promised SLA need not use identical thresholds.

For example, a company might operate internally against a 99.95% availability objective while contractually committing to a lower threshold.

The internal target can provide operational headroom.

An SLA is primarily a contractual instrument. An SLO is an engineering decision tool.

---

## 6. Error Budgets: Reliability Has an Economic Limit

Suppose your booking API has an SLO of 99.9% successful requests over thirty days.

That means the permitted unsuccessful fraction is:

\[
1 - 0.999 = 0.001
\]

Or 0.1%.

If the service receives one million eligible requests during the period, its error budget is:

\[
1,000,000 \times 0.001 = 1,000
\]

The system can experience approximately 1,000 unsuccessful requests while still meeting this particular request-based objective.

That's its **error budget**.

This doesn't mean engineers are encouraged to deliberately produce 1,000 failures.

It means the organization recognizes that perfect reliability is usually unattainable or economically irrational, and establishes a measurable tolerance for failure.

### The familiar availability table

For a time-based objective over exactly thirty days, the approximate unavailable time is:

| Availability target | Allowed unavailability |
|---|---|
| 99% | 7 hours 12 minutes |
| 99.9% | 43 minutes 12 seconds |
| 99.95% | 21 minutes 36 seconds |
| 99.99% | 4 minutes 19 seconds |
| 99.999% | 26 seconds |

These are mathematical equivalents for time-based availability, not automatic conversions for request-based SLOs.

A request-based objective can be violated during a short, extremely busy outage, while a relatively long low-traffic disruption may consume less of the request error budget.

### Why budgets change engineering priorities

Imagine two teams.

Team A has a reliable service that has consumed only 5% of its monthly error budget. It wants to ship an important feature through a controlled canary release.

Team B has consumed 95% of its budget after several major incidents. It also wants to ship a risky feature.

Should both teams follow identical release policies?

Probably not.

Team A may reasonably accept controlled deployment risk.

Team B may need to prioritize stability, incident remediation, and reducing the risk of another major failure.

This is the business value of error budgets: they create a shared language for negotiating feature velocity and reliability investment.

### Burn rate

An error budget also lets us measure how quickly reliability is deteriorating.

Suppose the SLO permits a 0.1% error rate, but the service currently experiences a 1% error rate.

The burn rate is:

\[
\frac{1\%}{0.1\%} = 10
\]

The system is consuming budget ten times faster than the rate that would evenly exhaust it over the whole SLO window.

A sustained burn rate of ten would consume a full thirty-day budget in approximately three days, assuming comparable traffic and measurement conditions.

Modern SRE alerting often combines multiple time windows and burn-rate thresholds to detect severe short incidents without ignoring slower, persistent deterioration.

A useful reliability objective is therefore not simply "never fail."

It is to understand which failures matter, how much reliability they consume, and when reducing risk should take priority over further changes.

---

## 7. Graceful Degradation: Being Partially Useful Is Better Than Being Completely Dead

Consider an e-commerce platform with these capabilities:

- Browse products.
- Search the catalog.
- View product reviews.
- Check inventory.
- Place orders.
- Complete payments.

Suppose the reviews service becomes unavailable.

Should the entire application return HTTP 503?

Obviously not.

Product reviews are useful, but customers can still browse products and place orders without them.

A sensible architecture might omit reviews temporarily while preserving the essential shopping experience.

This is **graceful degradation**: maintaining useful partial functionality when certain dependencies fail.

### Classify critical and optional dependencies

For a booking platform:

| Dependency | Example failure response |
|---|---|
| Payment provider | Disable payment-dependent checkout, preserve browsing |
| Recommendation engine | Hide personalized recommendations |
| Email provider | Confirm booking, queue notification for later |
| Analytics service | Continue business operation, buffer or drop noncritical telemetry |
| One hotel supplier | Show available results from other suppliers |
| Authoritative inventory database | Reject operations that cannot safely verify availability |

The last example is important.

Graceful degradation is not permission to violate business correctness.

If the system cannot establish that a room is available, it should not silently sell that room based on outdated assumptions unless the business has explicitly designed a safe reservation model for such uncertainty.

### Timeouts bound the damage

Suppose an API requests availability from three hotel suppliers.

One supplier occasionally takes thirty seconds to respond.

Without an appropriate timeout, the entire request may wait unnecessarily.

A timeout establishes a limit on how long the application is willing to wait for a particular operation.

```typescript id="tqg7lh"
const response = await fetch(supplierUrl, {
  signal: AbortSignal.timeout(2000)
});
```

This requests cancellation when the configured deadline expires.

However, cancellation is not guaranteed to undo any remote operation that has already occurred.

For an availability search, retrying or abandoning the request may be straightforward.

For a payment capture, a timeout creates uncertainty: the payment provider may have completed the operation even though the response never arrived.

The application must distinguish bounded waiting from transactional certainty.

### Cascading deadlines

Imagine the customer-facing API has a total response budget of three seconds.

Inside that request, the application calls two services sequentially, each with a three-second timeout.

The worst-case wait could already exceed the original budget.

A stronger design propagates an overall deadline and allocates appropriate portions to downstream operations.

This prevents layers of individually reasonable timeouts from producing an unreasonable end-to-end experience.

---

## 8. Circuit Breakers, Bulkheads, and Retry Storms

Three mechanisms are particularly valuable when dependencies become unreliable.

### Circuit breakers

A circuit breaker tracks failures associated with an operation or dependency and temporarily prevents additional calls when a configured failure condition is reached.

Conceptually:

```text id="s3u4pm"
CLOSED
  │
  ├── Calls normally allowed
  │
  └── Failure threshold reached
               │
               ▼
             OPEN
               │
       Calls fail fast
               │
       Recovery interval
               ▼
           HALF-OPEN
               │
        Limited trial calls
           /         \
       Success      Failure
          │            │
          ▼            ▼
        CLOSED        OPEN
```

When a hotel supplier is clearly unavailable, the circuit breaker can prevent thousands of requests from repeatedly waiting for it.

This reduces latency and protects application resources.

But a circuit breaker requires careful configuration. Opening unnecessarily may reject healthy requests, while closing too aggressively may overwhelm a recovering dependency.

It is a feedback-control mechanism, not a substitute for understanding failure behavior.

### Bulkheads

Ships use watertight compartments to prevent one flooded section from sinking the entire vessel.

Software bulkheads apply the same principle to resource isolation.

Suppose an API has a maximum of 100 concurrent outbound operations.

If one slow supplier can occupy all 100 slots, every other supplier may become inaccessible even when healthy.

Instead, allocate separate limits:

```text id="0es2jw"
Supplier A: 20 concurrent operations
Supplier B: 30 concurrent operations
Supplier C: 30 concurrent operations
Other:      20 concurrent operations
```

These allocations are illustrative rather than universally correct.

The important property is that Supplier A cannot automatically consume all capacity reserved for unrelated operations.

Bulkheads may use separate connection pools, worker pools, queues, process boundaries, or concurrency limits.

### Retries can become an attack

Retries are essential for transient failures, but they multiply demand.

Suppose 1,000 requests fail and each client retries three additional times.

A system already under pressure may receive up to 4,000 attempts instead of 1,000, before accounting for retries performed by intermediate services.

If API Gateway, the application, and a downstream SDK each independently retry, the total amplification can become much worse.

Useful retry controls include:

- Retry only appropriate failures.
- Use exponential backoff with jitter.
- Enforce retry budgets.
- Limit total attempts.
- Respect operation deadlines.
- Preserve idempotency for side-effecting operations.
- Avoid retrying work when the dependency is already overloaded.

Randomized jitter prevents large groups of clients from retrying simultaneously after identical delays.

The most important principle is that **recovery traffic must not become more destructive than the original failure**.

---

## 9. Health Checks: When Helpful Automation Becomes Dangerous

Return to our opening incident.

The Node.js containers were healthy enough to run code and respond to HTTP requests.

But their health endpoint executed:

```typescript id="71gmiv"
app.get("/health", async (_req, res) => {
  try {
    await database.query("SELECT 1");
    res.sendStatus(200);
  } catch {
    res.sendStatus(503);
  }
});
```

When PostgreSQL became temporarily unavailable, every application instance began failing its health check.

The orchestrator then attempted to replace those instances.

But the applications were not fundamentally broken.

The shared dependency was unavailable.

Restarting healthy application processes didn't repair PostgreSQL. It merely created additional connection attempts and removed potentially useful warm application instances.

This illustrates why different health questions should be separated.

### Liveness

**Is this process functioning sufficiently to remain running?**

A liveness failure may justify restarting a process that has become irrecoverably stuck.

For example, a deadlocked application may need process replacement.

But transient database unavailability generally should not cause every application process to be classified as irrecoverably dead.

### Readiness

**Can this instance currently serve the traffic that would be routed to it?**

An application may be alive but not ready.

Perhaps it is still initializing, loading essential configuration, or recovering from a local failure.

An orchestrator can remove an unready instance from normal traffic without necessarily restarting it.

### Startup

**Has the application completed its startup procedure?**

Some workloads take significant time to initialize.

A separate startup probe can prevent liveness checks from repeatedly killing an application before initialization completes.

Kubernetes explicitly distinguishes liveness, readiness, and startup probes, although other platforms expose related capabilities through different mechanisms.

### The shared-dependency trap

Should readiness depend on PostgreSQL?

Sometimes.

If every meaningful operation requires the database, reporting that the service cannot accept traffic may be appropriate.

But making every application instance unready simultaneously can leave a load balancer with no usable targets, and recovery may become harder if traffic behavior or deployment automation responds poorly.

A better strategy requires distinguishing local instance failure from shared infrastructure failure.

For example, an API serving cached catalog pages may remain partially useful during a database outage.

A payment endpoint requiring authoritative transaction state may need to reject operations until the database recovers.

Health checks should reflect actual service capabilities and orchestrator behavior.

They should not blindly trigger process restarts whenever any downstream dependency experiences trouble.

---

## 10. Recovery Objectives: How Much Damage Can the Business Tolerate?

Imagine a database failure requiring restoration from backups.

The engineering team discovers that the latest usable recovery point is twenty minutes old.

The business loses twenty minutes of reservation changes.

Was the recovery successful?

That depends on the business requirements.

Two metrics are central to disaster recovery planning.

### Recovery Time Objective

**RTO** is the target maximum time allowed to restore an acceptable level of service after a qualifying disruption.

For example:

> The reservation platform must restore its core booking capability within thirty minutes after a database infrastructure failure.

The RTO describes a recovery objective, not a guarantee that the recovery mechanism will achieve it.

### Recovery Point Objective

**RPO** is the target maximum acceptable data-loss interval, usually measured relative to the time of disruption.

For example:

> After recovery, the restored reservation records may be no more than five minutes behind the last durable state before the incident.

This implies that losing twenty minutes of acknowledged reservations would violate the objective.

### RTO and RPO describe different things

Consider:

```text id="75cs0t"
10:00 ─────────────── 10:20 ─────────────── 10:50
 Last recoverable    Failure             Service restored
 state
```

The service was restored thirty minutes after the failure.

But the restored data reflects the state twenty minutes before the failure.

In this scenario:

```text id="jn6s4a"
Observed recovery time: 30 minutes
Observed recovery gap:  20 minutes
```

Whether these outcomes satisfy the system's objectives depends on the agreed RTO and RPO.

A system may recover quickly while losing too much data.

Alternatively, it may preserve every committed transaction but require several hours to become operational again.

Neither outcome is universally acceptable.

### Different components need different objectives

A payment ledger may require extremely strong durability and a carefully defined reconciliation process.

A product recommendation cache may be safely rebuilt from authoritative data.

An analytics dashboard might tolerate delayed data processing.

A customer-facing booking API may need faster restoration than a historical reporting system.

Applying the strictest recovery requirements to every component is expensive and often unnecessary.

Recovery objectives should reflect the consequences of losing or delaying each capability.

---

## 11. Backups Are Not Recovery Plans

A company proudly reports:

> We take automated database backups every day.

That's useful.

But it doesn't establish that the company can recover from a serious failure.

Several additional questions matter:

- Are the backups actually completing?
- Are they retained long enough?
- Can they be restored successfully?
- Are they protected from accidental or malicious deletion?
- How long does restoration take?
- Is the restored data internally consistent?
- Can the application connect to the restored database?
- How are new writes reconciled after recovery?

A backup is an input to a recovery process.

It isn't the process itself.

### Snapshots and point-in-time recovery

Amazon RDS supports automated backups and point-in-time recovery for supported configurations.

Point-in-time recovery can restore a database to an available recovery point within the configured retention window.

Importantly, restoring an RDS DB instance to a point in time creates a new instance rather than simply rewinding the existing database in place.

This means recovery may involve:

1. Restoring the database.
2. Validating the restored state.
3. Reconfiguring application connectivity.
4. Reconciling externally completed operations.
5. Resuming traffic under controlled conditions.

A successful restoration operation is only one step.

### Replication is not backup

Suppose a developer accidentally executes:

```sql id="jgi45a"
DELETE FROM reservations;
```

If the deletion commits on a primary database, replication may faithfully propagate it to the standby.

The standby is not inherently an untouched historical copy.

Replication improves certain availability and recovery characteristics, but it does not replace versioned backups or point-in-time recovery.

Similarly, a highly available system may preserve corrupted application data across every replica.

### Immutable and isolated backups

A stronger recovery strategy may include backup retention controls, restricted deletion permissions, backup isolation, and copies outside the primary failure domain.

This can reduce exposure to incidents involving compromised credentials, accidental deletion, or regional infrastructure failures.

However, the appropriate design depends on cost, recovery targets, compliance requirements, and the actual threat model.

### Test restoration, not just backup creation

A meaningful recovery drill should demonstrate that engineers can restore a usable system.

For example:

- Restore PostgreSQL into an isolated environment.
- Verify critical tables and constraints.
- Start a compatible application version.
- Execute representative business queries.
- Measure elapsed recovery time.
- Document any missing configuration or credentials.
- Confirm whether the available data meets the recovery objective.

If the first time your company attempts restoration is during a major production outage, the disaster-recovery plan is largely theoretical.

**A backup you have never restored is a hypothesis about recoverability.**

---

## 12. Capacity Headroom and the N+1 Principle

Suppose a service runs on three application instances.

Each instance can reliably handle 500 requests per second under the relevant workload.

Normal traffic is 900 requests per second.

The deployment has theoretical capacity of:

\[
3 \times 500 = 1500
\]

requests per second.

That appears comfortable.

Now one instance fails.

Remaining capacity becomes:

\[
2 \times 500 = 1000
\]

The application can still handle normal traffic, but only with limited headroom.

A small traffic spike may push the remaining instances into saturation.

### N+1 capacity

The N+1 principle generally means provisioning enough additional capacity to tolerate the failure of one required unit while maintaining an acceptable service level.

For our three-instance example, we should evaluate whether the remaining two instances can support expected traffic and performance objectives.

But the real calculation must account for:

- Uneven traffic distribution.
- Startup and warmup delays.
- Scaling response time.
- Database capacity.
- CPU and memory contention.
- Connection pools.
- Peak rather than average workload.

Autoscaling may restore capacity eventually, but it cannot guarantee immediate replacement.

If new instances take ninety seconds to become useful, surviving instances must withstand that interval.

### Failure can create more work

During an outage, several behaviors can increase demand:

- Retries.
- Replayed queue messages.
- Cache misses.
- Reconnection storms.
- Recovery scans.
- Rescheduled background jobs.

The infrastructure may need more capacity during recovery than during normal operation.

This is why load testing only the happy path at normal traffic levels is insufficient.

A useful reliability test asks how the system behaves when one major component disappears while the remaining system continues receiving ordinary customer traffic.

---

## 13. Incident Response: Managing the Failure Without Making It Worse

Let's imagine that our booking API experiences a major outage.

Customers cannot complete reservations. The on-call engineer receives several alerts, operations teams begin asking questions, and management wants to know when the issue will be resolved.

At this moment, technical knowledge matters enormously.

But coordination matters too.

An unstructured incident can produce several engineers independently changing configuration, restarting services, or applying database fixes without understanding what others are doing.

The result may be more damaging than the original failure.

### Establish incident roles

For a significant incident, a practical structure distinguishes three responsibilities.

**Incident commander:** Maintains the overall picture, coordinates decisions, assigns responsibilities, and keeps the response focused.

**Technical responders:** Investigate evidence, propose mitigations, and execute controlled changes.

**Communications owner:** Provides accurate updates to stakeholders and affected customers.

Small teams may combine roles, but the responsibilities should remain clear.

This prevents every engineer from simultaneously debugging, debating strategy, and answering messages from management.

### Stabilize before fully explaining

During an active outage, the immediate priority is reducing customer impact.

If disabling a new feature restores service safely, that may be preferable to spending another hour establishing the precise source-code defect.

If a recent deployment is clearly implicated and rollback is compatible with persistent state, rollback may be appropriate.

If retry traffic is overwhelming a recovering database, temporarily reducing concurrency may be necessary.

Diagnosis and mitigation are related but different activities.

**A reliable incident response prioritizes restoring acceptable service while preserving enough evidence to understand what happened.**

### An incident timeline

A useful response timeline might look like:

```text id="sf1w7e"
11:42  Database failover begins

11:44  API error-rate alert fires

11:46  Incident declared
       Technical response coordinated

11:49  Connection pool saturation identified

11:52  Excessive retries detected

11:55  Retry concurrency reduced
       Background jobs temporarily paused

12:00  Database connections stabilize

12:04  Reservation API recovers

12:09  Background processing resumes gradually

12:13  Customer-facing incident resolved

Later  Root-cause analysis and corrective actions
```

This structure helps distinguish observations from interventions.

It also creates a useful record of what the team knew at each moment.

Avoid rewriting the timeline afterward as though everyone knew the eventual root cause from the beginning.

Real incidents involve incomplete information, uncertainty, and changing hypotheses.

### Communication is an engineering responsibility

A useful status update communicates:

- Which functionality is affected.
- When the issue began, if known.
- Whether mitigation is underway.
- What customers should or should not do.
- When the next update will be provided, if appropriate.

It should not invent a recovery estimate merely to sound reassuring.

Customers and internal stakeholders need accurate information, not theatrical confidence.

---

## 14. Postmortems: Learning Without Hunting for Villains

The application has recovered.

It's tempting to declare victory and return to feature development.

But without further investigation, the next database failover may produce the same cascading failure.

A **postmortem** examines what happened, why the system behaved as it did, how the incident was handled, and what should change.

A useful postmortem might contain:

```text id="7udcrb"
Incident:
Reservation API unavailable for 38 minutes

Impact:
Approximately 14,000 failed or timed-out requests

Trigger:
RDS primary failover

Contributing factors:
- Aggressive application retry policy
- Health checks tied to shared database availability
- Connection pools created during task replacement
- Insufficient database connection headroom
- Cache misses amplified database traffic

Detection:
API error-rate alert

Mitigation:
Reduced retries and stabilized application tasks

Follow-up:
- Separate liveness and readiness behavior
- Introduce retry budgets
- Test failover under representative load
- Add connection acquisition metrics
- Create database-failover runbook
```

The important part is distinguishing the trigger from contributing conditions.

The RDS failure initiated the incident, but the prolonged outage resulted from several interacting architectural behaviors.

### Blameless doesn't mean accountability-free

A blameless postmortem avoids reducing a complex incident to "Developer X made a mistake."

Instead, it examines why the system allowed the mistake to produce the observed consequences.

Perhaps a dangerous migration passed review because no compatibility check existed. Perhaps engineers couldn't detect connection starvation because the relevant metric wasn't collected.

Individuals remain responsible for participating professionally and improving their practices.

But blame-focused investigations often discourage honest reporting and obscure systemic weaknesses.

### Avoid the corrective-action avalanche

After a serious outage, teams sometimes produce forty improvement tasks.

Six months later, nearly all remain unfinished.

A useful postmortem prioritizes a small set of improvements according to expected risk reduction and implementation cost.

For our incident, separating health-check responsibilities and controlling retry behavior may offer more immediate value than introducing a complicated new orchestration platform.

Not every incident justifies rebuilding the architecture.

The best corrective actions reduce the probability, duration, or impact of the failure modes that actually matter.

---

## 15. Runbooks and Chaos Testing: Practicing Before the Emergency

A **runbook** is an operational guide for investigating or responding to a known class of problem.

For database connection exhaustion, a useful runbook might contain:

- How to identify the affected database and application instances.
- Which metrics indicate connection saturation.
- How to inspect PostgreSQL session states.
- How to distinguish slow queries from pool acquisition waits.
- Which mitigations are safe under specified conditions.
- Which actions require approval.
- How to verify recovery.

A runbook should make the on-call engineer more effective without pretending that every incident follows an identical script.

### Fault injection

Reliability assumptions should be tested.

If the architecture claims to tolerate one application instance disappearing, deliberately terminate one instance in a controlled environment and observe what happens.

If the system claims that queued jobs survive worker termination, kill a worker during processing and verify that unfinished work becomes recoverable.

If RDS failover is part of the architecture, conduct an appropriate controlled failover exercise and observe client reconnection and transaction behavior.

This practice is commonly associated with **chaos engineering**.

The objective isn't random destruction.

It is testing hypotheses about how a system behaves under failure.

### Formulate a hypothesis

For example:

> If one API task stops unexpectedly, the load balancer will route requests to surviving tasks without violating the checkout availability SLO.

Then define:

- The environment.
- The expected steady-state behavior.
- The fault being introduced.
- The measurements.
- The abort conditions.
- The recovery procedure.

Start with low-risk experiments and expand only when the team has sufficient control and observability.

Randomly terminating production databases without a recovery plan isn't chaos engineering.

It's just chaos.

### What a useful experiment might reveal

Perhaps replacing one API task works perfectly.

But replacing several tasks during peak traffic causes database connection exhaustion.

The experiment reveals that task-level recovery is correct while downstream capacity planning is inadequate.

That finding is valuable because it appears before an uncontrolled real-world incident forces the same lesson.

---

## 16. Practical Lab — Design for Failure, Not Just Success

This session's lab has two parts: a small Node.js fault-injection experiment and a disaster-recovery tabletop exercise.

### Part A — Build a deliberately fragile API

Create `reliability-lab.mjs`:

```javascript id="r81l2u"
import http from "node:http";

let dependencyHealthy = true;

const sleep = (ms) =>
  new Promise((resolve) => setTimeout(resolve, ms));

async function callRecommendationService() {
  if (!dependencyHealthy) {
    await sleep(2000);
    throw new Error("Recommendation service unavailable");
  }

  await sleep(40);

  return ["Hotel A", "Hotel B"];
}

const server = http.createServer(async (req, res) => {
  if (req.url === "/fail") {
    dependencyHealthy = false;
    res.end("Dependency failed");
    return;
  }

  if (req.url === "/recover") {
    dependencyHealthy = true;
    res.end("Dependency recovered");
    return;
  }

  if (req.url === "/health") {
    res.writeHead(dependencyHealthy ? 200 : 503);
    res.end("Health check");
    return;
  }

  if (req.url === "/hotels") {
    try {
      const recommendations =
        await callRecommendationService();

      res.setHeader("Content-Type", "application/json");
      res.end(JSON.stringify({ recommendations }));
    } catch {
      res.writeHead(503);
      res.end("Service unavailable");
    }

    return;
  }

  res.writeHead(404);
  res.end();
});

server.listen(3000, () => {
  console.log("Reliability lab listening on 3000");
});
```

Run:

```bash id="huxnhb"
node reliability-lab.mjs
```

Test the normal operation:

```bash id="07tmx4"
curl -i http://localhost:3000/hotels
```

Now simulate a dependency failure:

```bash id="nu1elx"
curl http://localhost:3000/fail
curl -i http://localhost:3000/hotels
curl -i http://localhost:3000/health
```

Notice two behaviors.

The hotel endpoint waits approximately two seconds before failing.

The health endpoint reports that the entire application is unhealthy even though its HTTP server remains fully operational.

An orchestrator using that endpoint as liveness evidence might unnecessarily restart the application.

### Part B — Introduce graceful degradation

Modify the `/hotels` handler so recommendation failure doesn't prevent the API from returning a useful result.

For example, replace its catch block with:

```javascript id="6x0ebo"
} catch {
  res.setHeader("Content-Type", "application/json");

  res.end(JSON.stringify({
    recommendations: [],
    recommendationsAvailable: false
  }));
}
```

The endpoint now returns a degraded but valid response.

This is appropriate if recommendations are optional.

It would not be appropriate if the missing dependency were responsible for authoritative inventory verification.

Next, separate health concepts.

A simple liveness endpoint might be:

```javascript id="8q3yvn"
if (req.url === "/live") {
  res.writeHead(200);
  res.end("Alive");
  return;
}
```

The existing dependency check can remain a diagnostic endpoint or contribute to a readiness decision where appropriate.

Now ask whether the application's inability to provide recommendations should affect readiness for the entire hotel catalog.

It probably shouldn't.

### Part C — Introduce a circuit-breaker concept

The dependency takes two seconds to fail every time.

What if we recognize repeated failures and temporarily stop making the expensive call?

Implement a simplified state variable recording whether the recommendation dependency should be called.

After several consecutive failures, skip requests to the dependency for a short interval and immediately return the degraded response.

After the interval, permit a limited trial request.

Do not treat this toy implementation as production-ready. Real circuit breakers require careful concurrency handling, failure classification, metrics, and recovery behavior.

The experiment demonstrates why a service can become more responsive during dependency failure by deliberately making fewer downstream calls.

### Part D — Disaster-recovery tabletop

Now imagine the same SaaS running on AWS.

At 14:00, a destructive database operation removes several thousand reservations.

The deletion replicates successfully to the standby database.

Your business requirements are:

```text id="62s5xg"
RTO: 60 minutes
RPO:  5 minutes
```

Your RDS environment has automated backups and point-in-time recovery enabled.

Design the recovery procedure.

You must decide:

1. How to stop additional damaging writes.
2. Which recovery point to select.
3. Whether restoring the database is preferable to selectively recovering deleted records.
4. How to handle reservations created after the chosen recovery point.
5. How to reconcile payments completed by external providers.
6. How to verify restored data before reopening normal operation.
7. How to measure whether the RTO and RPO were satisfied.

This is deliberately not a simple "restore the database" exercise.

If a customer successfully paid at 13:59 but the restored database no longer contains the reservation, the application must address the discrepancy.

A production recovery procedure requires both infrastructure restoration and business reconciliation.

### Part E — Prioritize reliability improvements

Assume your team has two weeks of engineering capacity.

Which changes would you prioritize?

| Candidate improvement | Primary benefit |
|---|---|
| Add a third API instance | More instance-level capacity |
| Fix database-dependent liveness checks | Prevent unnecessary restart cascades |
| Introduce retry budgets | Reduce overload amplification |
| Add another AWS Region | Improve resilience to some regional failures |
| Test database restoration | Validate actual recoverability |
| Increase connection-pool size | Potentially increase concurrency, or worsen DB pressure |

Rank these according to the failure modes we've investigated.

A strong answer should prioritize **risk reduction per unit of engineering effort**, rather than the number of technologies introduced.

---

## 17. Engineering and Interview Challenges

### Challenge 1 — The redundant system

A SaaS operates four API instances across two Availability Zones. All four connect to one PostgreSQL primary, and every API instance has a health check that queries the database.

During database failover, all four instances become unhealthy.

What is wrong with the reliability design? Would adding four more instances solve the problem?

### Challenge 2 — The availability target

A service processes two million eligible requests per month with a 99.9% request-success SLO.

During one incident, 8,000 requests fail.

What fraction of the monthly error budget has been consumed? What does that imply for engineering priorities?

### Challenge 3 — The backup illusion

A team uses RDS Multi-AZ and daily snapshots. Management believes the application is protected from almost any database disaster.

What failure categories remain? What evidence would establish that the recovery plan is adequate?

### Challenge 4 — The retry dilemma

A payment provider sometimes times out after processing a charge.

A developer proposes retrying every timed-out operation three times with a 100-millisecond delay.

What's wrong with the proposal, and what should a reliable payment workflow do instead?

### Challenge 5 — The incident commander

A production outage is underway.

Three engineers have different theories. One wants to restart PostgreSQL, another wants to roll back the application, and a third wants to disable the background workers.

How should the incident be coordinated? What evidence should determine the next action?

---

## 18. Solutions and Discussion

### Challenge 1 — Redundancy must address shared failure modes

All instances depend on the same database, and their health checks turn a shared dependency failure into apparent failure of every application instance.

Adding more API instances would not eliminate the database dependency and could increase reconnection pressure during recovery.

I'd distinguish process liveness from readiness and shared-dependency health, then investigate database failover behavior, client reconnection, pool management, and retry amplification.

I would also ensure the database's availability configuration meets the business requirements and that the application can tolerate the expected failover interval.

The main objective is to prevent one failure from unnecessarily triggering several others.

### Challenge 2 — The budget is exhausted several times over

At 99.9% success, the allowed failure fraction is 0.1%.

For two million requests:

\[
2,000,000 \times 0.001 = 2,000
\]

The monthly error budget is 2,000 failed requests.

An incident causing 8,000 failures consumes:

\[
\frac{8,000}{2,000} = 4
\]

That's 400% of the monthly budget.

The service has already violated its SLO, assuming the requests and measurement window match its definition.

The team should investigate the incident's causes and prioritize effective reliability improvements. It may also need to limit risky changes until the system demonstrates acceptable stability.

But the response shouldn't become an indefinite ban on feature development. Engineering decisions should reflect the actual risks, available mitigations, and business priorities.

### Challenge 3 — Replication doesn't protect every form of damage

RDS Multi-AZ improves resilience against supported infrastructure failures.

It does not automatically protect against destructive SQL, application-level data corruption, compromised administrative credentials, or every regional disaster.

Snapshots provide potential recovery points, but the actual recoverability depends on retention, backup integrity, restoration time, available credentials, infrastructure configuration, and business reconciliation.

I'd require a tested restoration exercise measuring RTO and RPO against realistic scenarios.

A recovery plan that has never been executed successfully is not strong evidence of disaster readiness.

### Challenge 4 — A timeout doesn't prove failure

The payment provider may have charged the customer even though the response was lost.

Blind retries could generate duplicate financial operations if the provider doesn't recognize them as the same logical request.

A reliable workflow should use stable idempotency identifiers supported by the provider, persist operation state, distinguish known failures from uncertain outcomes, and reconcile ambiguous transactions.

Retries should use appropriate backoff, deadlines, and limits.

The objective is not simply to obtain a successful HTTP response.

It is to establish the correct financial outcome.

### Challenge 5 — Coordinate and mitigate based on evidence

An incident commander should establish one shared operational picture and prevent conflicting interventions.

The team should identify customer impact, recent changes, service metrics, database state, and any evidence linking the outage to a specific dependency or deployment.

If a recent application release is clearly responsible and rollback remains compatible, rollback may be appropriate.

If background workers are saturating PostgreSQL, temporarily reducing their concurrency could be a safer mitigation than restarting the database.

Every major intervention should have an owner, an expected result, a verification step, and an understanding of its risks.

The goal is to restore service without turning an uncertain diagnosis into an irreversible production experiment.

---

## Mental Model

Think about production reliability through six questions:

1. **Objectives:** What level of availability, correctness, and recovery does the business actually require?
2. **Failure domains:** Which components share dependencies that can fail together?
3. **Containment:** Can timeouts, bulkheads, circuit breakers, and graceful degradation limit damage?
4. **Recovery:** What are the RTO and RPO, and have recovery procedures been tested?
5. **Operations:** Can engineers detect, coordinate, and mitigate an incident effectively?
6. **Learning:** Which improvements reduce the probability or impact of future incidents?

**The central principle: Reliable systems are not systems that never fail. They are systems designed so that failures remain contained, important work stays correct, and recovery is predictable.**


---

## Next Lecture — SE440-L03: Testing Strategies for Complex Systems

Continue in **SE440 — Production Reliability and Quality Engineering**.

## Further Reading

1. **Google — [Site Reliability Engineering](https://sre.google/sre-book/table-of-contents/)**. The foundational collection on production reliability, monitoring, risk, incident response, and balancing operational stability against development velocity.

2. **Google — [Implementing SLOs](https://sre.google/workbook/implementing-slos/)**. Practical methods for defining service indicators, establishing objectives, and building reliability policy around user experience.

3. **Google — [Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)**. Error-budget burn rates, multiple alerting windows, and avoiding ineffective threshold-based alerting.

4. **Google — [Incident Management Guide](https://sre.google/resources/practices-and-processes/incident-management-guide/)**. Incident coordination, mitigation, communication, and blameless learning.

5. **AWS — [RDS Multi-AZ Failover](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.Failover.html)**. What managed database failover provides, its expected behavior, and its operational limitations.

6. **AWS — [RDS Backup and Recovery](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_CommonTasks.BackupRestore.html)**. Automated backups, snapshots, point-in-time recovery, and database restoration.

7. **Kubernetes — [Liveness, Readiness, and Startup Probes](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/)**. How container health signals influence traffic routing, restarts, and recovery.

8. **Michael T. Nygard — *Release It!, Second Edition***. A highly practical exploration of stability patterns, cascading failures, circuit breakers, bulkheads, and operating real software under stress.

9. **Casey Rosenthal and Nora Jones — *Chaos Engineering***. The principles and organizational practices of testing production-system resilience through controlled failure experiments.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE440-L02  RELIABILITY / INCIDENTS — INTERVIEW GLANCE CARD

CORE MODEL
  Redundancy can still fail if recovery behavior amplifies the fault
  Reliability = correct intended function over time/conditions
  Availability = accessible when needed (can be available but wrong)
  Durability = keep acknowledged data — distinct from A/R
  Prefer request-based success ratios over naïve “up/down minutes”

REDUNDANCY LIMITS
  Independence assumption fails on shared DB/config/artifact/cred/region
  Failure domains: process → host → AZ → region → shared DB/deploy
  Serial deps: A_end ≈ Π A_i when all required → adding hops hurts
  Redundancy valuable when it removes a shared failure mode

PREVENT / CONTAIN / RECOVER
  Tests, timeouts, breakers, bulkheads, degrade, failover, backups, runbooks
  One mechanism ≠ all categories (backup ≠ availability)

SLI / SLO / SLA
  SLI = measured indicator (success ratio, latency fraction…)
  SLO = target over window; define eligible/success carefully
  SLA = contractual; often looser than internal SLO headroom
  Error budget = allowed failure fraction (e.g. 0.1% of requests)
  Burn rate = current_error / budget_rate → prioritize stability vs change

GRACEFUL DEGRADATION
  Optional deps fail → reduced UX; critical inventory can't invent stock
  Timeouts bound wait; timeout ≠ remote undone (payments uncertain)
  Cascade deadlines: overall budget > sum of layer timeouts

BREAKERS / BULKHEADS / RETRIES
  Circuit: closed → open (fail fast) → half-open trials
  Bulkhead: isolate concurrency pools so one supplier can't starve all
  Retry storms amplify load; backoff+jitter, budgets, idempotency
  Recovery traffic must not out-damage the original failure

HEALTH CHECKS
  Liveness (restart stuck) ≠ readiness (take traffic) ≠ startup
  Don't restart every task because shared DB SELECT 1 failed
  Shared-dep failure ≠ local process death

RTO / RPO
  RTO = time to restore service; RPO = max acceptable data-loss gap
  Fast restore with large gap ≠ meet both; component-specific targets

BACKUPS ≠ RECOVERY
  Completing / retaining / restoring / protecting / reconciling matter
  Replication can propagate DELETE; ≠ historical backup
  PITR often new instance; test restoration drills
  Untested backup = recoverability hypothesis

CAPACITY
  N+1: survive one unit loss under peak + warmup lag
  Failure creates extra work (retries, cache miss, reconnect storms)

INCIDENTS / POSTMORTEMS
  Roles: commander · technical · communications
  Stabilize impact before perfect root cause; preserve evidence
  Blameless ≠ no accountability; trigger ≠ only contributing factors
  Few high-leverage follow-ups > 40 unfinished tasks
  Runbooks + chaos/fault injection practice assumptions

SENIOR LINE: Reliable systems contain failures, keep important work
             correct, and recover predictably—not “never fail.”
```

---


