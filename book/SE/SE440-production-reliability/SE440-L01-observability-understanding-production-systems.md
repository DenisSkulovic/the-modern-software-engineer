---
id: SE440-L01
course: SE440
title: "Observability: Understanding Production Systems"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [ENG401-S07]
prev: null
next: SE440-L02
---











# SE440 — Production Reliability and Quality Engineering

## Lecture 01: Observability: Understanding Production Systems

*How to investigate an application that insists everything is healthy while its customers are having a thoroughly miserable time.*

---

## 1. The Mystery of the Missing Ten Seconds

Your company operates a hotel-booking SaaS. Its backend consists of a Node.js API, PostgreSQL, Redis, background workers, and integrations with several external hotel suppliers.

Most customers receive search results within 200 milliseconds. But recently, a small percentage have started waiting between eight and twelve seconds.

The problem is intermittent, affecting approximately 2% of requests.

You open the monitoring dashboard.

```text
API CPU utilization:       18%
API memory utilization:    42%
PostgreSQL CPU:            24%
Redis latency:             < 2 ms
HTTP 5xx error rate:       0.1%
Average API latency:       298 ms
```

Nothing looks particularly alarming.

The API is running. Its health checks pass. Database queries appear fast, and no infrastructure resource is obviously exhausted.

You inspect a slow request's application logs:

```text
14:32:11.102  Request received
14:32:20.841  Reservation loaded
14:32:20.868  Response sent
```

The request took almost ten seconds, but the only visible database query completed in 27 milliseconds.

Where did the other 9.7 seconds go?

Perhaps the process was waiting for a database connection. Perhaps a remote supplier was slow. Perhaps a queue inside the application had accumulated work, or perhaps a synchronous operation temporarily blocked the Node.js event loop.

The available evidence doesn't distinguish these possibilities.

This is the central problem of production observability: **a system can report perfectly accurate information and still fail to provide the information necessary to explain its behavior.**

The challenge isn't merely collecting more data. It's constructing evidence that allows engineers to investigate unfamiliar failures without having predicted every possible failure in advance.

---

## 2. Monitoring Versus Observability

Monitoring and observability are closely related, but they emphasize different capabilities.

**Monitoring** establishes what a system is doing according to selected measurements and conditions.

For example:

- Is the service responding?
- What percentage of requests fail?
- How much memory is consumed?
- Is the database approaching its connection limit?
- How many background jobs are waiting?

These measurements can reveal that something is wrong.

**Observability** concerns how effectively engineers can infer the system's internal behavior from the information it exposes.

A highly observable system enables questions such as:

- Why are corporate customers experiencing greater latency than ordinary customers?
- Which dependency accounts for the delay?
- Did the problem begin with a deployment?
- Which step of the workflow failed?
- Are requests waiting for computation, I/O, locks, or available connections?

The distinction is not absolute. Good monitoring is part of good observability.

But installing dashboards and collecting thousands of measurements doesn't guarantee that engineers can explain what happened.

### The difference between symptoms and explanations

Suppose a dashboard reports:

```text
HTTP p99 latency: 9.8 seconds
```

That is an important symptom.

Now suppose a distributed trace reveals:

```text
Request duration                  9,800 ms

Authentication                       8 ms
Business validation                 14 ms
Waiting for DB connection        9,520 ms
Executing SQL query                 31 ms
Response serialization              12 ms
Other processing and overhead      215 ms
```

We now have a plausible explanation.

The database query itself isn't slow. Requests are waiting for permission to execute it.

Optimizing SQL would probably achieve very little.

The investigation should instead focus on the connection pool: its size, utilization, connection ownership, and the operations holding connections for unusually long periods.

This illustrates the practical value of observability.

**It converts an enormous space of possible explanations into a smaller set of hypotheses supported by evidence.**

---

## 3. The Three Major Observability Signals

Modern production systems commonly rely on three complementary categories of telemetry:

1. Logs.
2. Metrics.
3. Distributed traces.

They describe different aspects of the same system.

| Signal | Best at answering |
|---|---|
| Logs | What specific events occurred, and with what context? |
| Metrics | How frequently and severely is something happening? |
| Traces | Where did time go, and how did one operation move through the system? |

These signals are complementary, not competing alternatives.

A metric may show an increasing error rate. A trace may identify the failing dependency. Logs may reveal the precise error returned by that dependency.

The strongest investigations move between them.

Let's examine each signal in detail.

---

## 4. Logs: The Narrative of Individual Events

Logs are probably the oldest and most familiar form of application telemetry.

A developer writes:

```typescript
console.log("Processing reservation");
```

Then:

```typescript
console.log("Reservation processed");
```

This works reasonably well when debugging one process locally.

In production, however, the application may process hundreds of requests concurrently across dozens of instances.

The output becomes something like:

```text
Processing reservation
Processing reservation
Reservation processed
Processing reservation
Reservation processed
Reservation processed
```

Which messages belong to which request?

Which customer operation failed?

Which application version produced the message?

Without additional context, the logs tell us that activity occurred but provide little help reconstructing it.

### Structured logging

Instead of treating logs as arbitrary strings, production applications can emit structured records.

For example:

```json
{
  "timestamp": "2026-10-25T14:32:20.841Z",
  "level": "error",
  "service": "booking-api",
  "environment": "production",
  "version": "2.18.3",
  "request_id": "req-8f21",
  "trace_id": "a0892f3577b34da6a3ce929d0e0e4736",
  "operation": "reservation.load",
  "error_code": "DB_CONNECTION_TIMEOUT",
  "duration_ms": 9520
}
```

This format enables meaningful filtering.

An engineer can search for all database connection timeouts produced by version `2.18.3`, inspect the affected requests, and compare their behavior with the previous application version.

It also allows automated systems to aggregate or classify errors without unreliable string parsing.

### Log levels

Common log levels include:

| Level | Intended use |
|---|---|
| DEBUG | Detailed diagnostic information |
| INFO | Significant normal application events |
| WARN | Unexpected behavior that may not prevent operation |
| ERROR | Failed operations requiring investigation or handling |
| FATAL | Severe failure threatening continued process operation |

Different logging libraries use slightly different conventions.

The important part is consistency.

An expected business rejection such as "customer cannot cancel an expired reservation" should not automatically become an ERROR-level log.

If ordinary business validation produces thousands of errors, genuine infrastructure failures become harder to identify.

### Avoid logging everything

Logs have costs.

Every record consumes CPU time, storage, network bandwidth, ingestion capacity, and human attention.

A service that logs every successful SQL query, complete HTTP payload, and internal function call may generate enormous amounts of low-value telemetry.

Worse, excessive logging can expose sensitive information.

Payment tokens, customer documents, session cookies, authorization headers, and personal data must not be written casually into centralized log storage.

The goal is to record information that helps reconstruct important behavior, not to preserve an exhaustive transcript of the application's internal existence.

---

## 5. Correlation IDs: Making Concurrent Work Understandable

Suppose a reservation request passes through:

```text
API Gateway
     │
     ▼
Booking API
     │
     ▼
Payment Service
     │
     ▼
Notification Worker
```

Each component produces logs independently.

How do we determine which records belong to the same business operation?

One solution is a **correlation identifier**.

The initial request receives a unique ID:

```text
request_id = req-8f21
```

Subsequent operations include that identifier in their logs.

```text
14:32:11.102 booking-api
request_id=req-8f21
event=request_started

14:32:11.134 payment-service
request_id=req-8f21
event=payment_authorized

14:32:11.185 booking-api
request_id=req-8f21
event=reservation_confirmed
```

Now the events can be retrieved together.

### Propagating context in Node.js

Node.js provides `AsyncLocalStorage`, which can associate contextual data with asynchronous execution chains.

A simplified Express example:

```typescript
import { AsyncLocalStorage } from "node:async_hooks";
import { randomUUID } from "node:crypto";

type RequestContext = {
  requestId: string;
};

const requestContext =
  new AsyncLocalStorage<RequestContext>();

app.use((req, res, next) => {
  const requestId = randomUUID();

  res.setHeader("X-Request-ID", requestId);

  requestContext.run({ requestId }, next);
});

function log(
  level: string,
  message: string,
  extra: Record<string, unknown> = {}
) {
  const context = requestContext.getStore();

  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    level,
    message,
    requestId: context?.requestId,
    ...extra
  }));
}
```

Application code can now log without manually passing `requestId` through every function signature.

```typescript
log("info", "Loading reservation", {
  reservationType: "CORPORATE"
});
```

The contextual identifier is retrieved from the active asynchronous execution context.

This is useful, but it has limitations.

`AsyncLocalStorage` does not automatically propagate context between independent processes, external services, or durable queue messages.

Those boundaries require explicit context propagation or appropriate instrumentation.

Also, request IDs and trace IDs serve related but different purposes.

A request ID identifies an operation according to an application's chosen scheme. A distributed trace ID identifies a trace that may span several services and multiple nested operations.

We'll return to that distinction shortly.

---

## 6. Metrics: Understanding Patterns Across Millions of Operations

Logs describe individual events. Metrics summarize measurable behavior over time.

Suppose our application processes one million requests daily.

Searching logs to determine the average request rate would be inefficient, while a continuously updated metric can provide the answer directly.

Metrics are especially useful for:

- Measuring trends.
- Detecting anomalies.
- Comparing releases.
- Identifying saturation.
- Supporting alerting.
- Measuring service reliability.

### Counters

A counter represents a cumulative quantity that normally increases until its process or metric state resets.

For example:

```text
http_requests_total = 1842532
```

The absolute value may be less useful than its rate of change.

If the counter increases by 30,000 over five minutes, the average request rate during that interval is:

\[
\frac{30,000}{300} = 100
\]

Approximately 100 requests per second.

Prometheus-style monitoring systems provide functions such as `rate()` to calculate rates while accounting for ordinary counter resets.

### Gauges

A gauge represents a value that can increase or decrease.

Examples include:

```text
database_pool_active_connections = 18
database_pool_idle_connections   = 2
queue_waiting_jobs               = 720
nodejs_heap_used_bytes           = 184000000
```

Gauges describe current conditions or recent measurements.

A database connection gauge may remain near its maximum for a sustained interval, suggesting resource pressure.

However, a brief high value is not necessarily problematic. Interpretation requires context, workload expectations, and knowledge of the resource limit.

### Histograms

A histogram represents the distribution of observations.

Request latency is an excellent example.

Rather than storing only the average latency, the system records observations into duration buckets.

A simplified cumulative histogram might contain:

```text
Requests <= 100 ms:       7,000
Requests <= 250 ms:       9,200
Requests <= 500 ms:       9,700
Requests <= 1 second:     9,800
Requests <= 10 seconds:  10,000
```

These numbers describe 10,000 completed requests.

The histogram makes the slow tail visible.

It also supports questions such as, "What proportion of requests completed within our performance objective?"

Modern monitoring systems may use classic bucket histograms or more compact native histogram representations. Their mathematical details differ, but both aim to preserve useful information about distributions.

### Why histograms matter

Consider two services with identical average latency:

```text
Service A:
Almost every request takes 200 ms.

Service B:
Most requests take 20 ms.
A small fraction take several seconds.
```

Their averages might be similar, yet the customer experience is radically different.

Service B has a long latency tail.

Averages conceal this structure.

---

## 7. Percentiles: The Customers Hidden by the Average

Let's analyze our opening incident numerically.

Imagine 1,000 requests:

- 980 complete in 100 milliseconds.
- 20 complete in 10 seconds.

The average latency is:

\[
\frac{980(0.1) + 20(10)}{1000}
=
0.298 \text{ seconds}
\]

The dashboard reports 298 milliseconds.

That doesn't sound catastrophic.

But 2% of requests take ten seconds.

For a busy booking platform, those requests may represent thousands of frustrated customers daily.

### Understanding percentiles

A percentile indicates a position within a distribution.

The 50th percentile, or p50, is the median.

The 95th percentile, or p95, describes a latency threshold at or below which approximately 95% of observations fall.

The 99th percentile, or p99, similarly describes the threshold for approximately 99% of observations.

For our simplified distribution:

```text
p50  = 100 ms
p95  = 100 ms
p99  = 10,000 ms
```

The median and p95 look excellent.

The p99 exposes a severe tail.

Precise percentile values depend on the calculation convention, sample size, and whether histograms approximate the distribution.

### Percentiles are not automatically composable

Here's a subtle but important statistical mistake.

Suppose three API instances report:

```text
Instance A p99 = 200 ms
Instance B p99 = 400 ms
Instance C p99 = 900 ms
```

Can you calculate the overall p99 by averaging these values?

No.

Percentiles are nonlinear statistics. The overall percentile depends on the distribution and number of observations from every instance.

A simple average of per-instance p99 values can be misleading, especially if the instances receive different volumes of traffic.

This is one reason aggregatable histograms are useful. Compatible bucket data can be combined before estimating a fleet-wide percentile.

Another complication is that percentiles over tiny sample sizes may be unstable.

A p99 measurement derived from twenty requests tells you relatively little about rare behavior.

Percentiles must be interpreted with traffic volume and measurement windows in mind.

---

## 8. RED and USE: Two Ways to Examine a System

When investigating performance, engineers need a systematic starting point.

Otherwise, dashboards become sprawling collections of CPU graphs, network charts, and suspiciously decorative gauges.

Two useful monitoring approaches are **RED** and **USE**.

### RED: Examine the service

RED focuses on three characteristics:

- **Rate:** How many requests or operations are occurring?
- **Errors:** How frequently do they fail?
- **Duration:** How long do they take?

For an API:

```text
Request rate:       450 requests/second
Error rate:         0.3%
p95 latency:        180 ms
p99 latency:        9,500 ms
```

RED describes what the service is delivering.

The long-tail latency immediately suggests a customer-facing problem, even though the error rate remains low.

### USE: Examine the resources

USE stands for:

- **Utilization:** How busy is the resource?
- **Saturation:** Is demand exceeding its ability to serve work promptly?
- **Errors:** Is the resource reporting failures?

For a database connection pool:

```text
Pool utilization:   20 / 20 connections
Pool waiters:       83
Acquisition errors: 12 / minute
```

The connection pool is fully utilized and has a significant backlog.

For a CPU:

```text
CPU utilization:    92%
Runnable backlog:   Elevated
CPU errors:         Not generally a comparable signal
```

Not every resource exposes all USE categories in a directly measurable way.

The method encourages investigating resource contention rather than assuming that overall CPU or memory utilization explains every bottleneck.

### The four golden signals

Google's Site Reliability Engineering material emphasizes four closely related signals:

**Latency, traffic, errors, and saturation.**

RED focuses on service operations; USE focuses on resources. The golden signals provide a concise overall monitoring framework.

These approaches complement rather than replace each other.

For our mystery, RED identifies the slow requests, while USE helps reveal a saturated connection pool.

The next question is why the pool is saturated.

That's where distributed tracing becomes particularly valuable.

---

## 9. Distributed Tracing: Following One Operation Through the System

Imagine a reservation request that touches several components:

```text
Browser
   │
   ▼
Booking API
   │
   ├── Authentication
   ├── PostgreSQL
   ├── Supplier API
   └── Payment API
```

Traditional logs produce independent records from each component.

Metrics reveal aggregate behavior.

Distributed tracing attempts to reconstruct the causal structure and timing of a particular operation.

### Traces and spans

A **trace** represents an operation across one or more components.

A **span** represents an individual unit of work within that trace.

For example:

```text
Trace: POST /reservations
│
├── HTTP request                         980 ms
│   │
│   ├── Authentication                    12 ms
│   │
│   ├── Validate reservation              18 ms
│   │
│   ├── Check availability               610 ms
│   │   └── Supplier HTTP request        590 ms
│   │
│   ├── Database transaction              45 ms
│   │
│   └── Serialize response                 8 ms
```

Spans contain information such as:

- Operation name.
- Start time and duration.
- Trace and span identifiers.
- Parent relationship.
- Attributes describing the operation.
- Status and recorded events.

The trace can be displayed as a timeline, making dependencies and delays much easier to investigate.

### A trace is not just a tree of durations

Suppose two supplier requests execute concurrently:

```text
Request starts
   │
   ├── Supplier A: 500 ms
   │
   └── Supplier B: 700 ms
   │
Request continues
```

The total elapsed time may be slightly above 700 milliseconds, not 1,200 milliseconds.

Both operations overlap.

Therefore, adding child-span durations does not necessarily produce total request duration.

The important concept is the **critical path**: the chain of dependent operations determining how long the overall request must take.

A trace visualization makes this easier to understand than an unordered collection of timings.

### Missing spans are information too

Suppose a trace looks like this:

```text
POST /reservations              9,800 ms
   │
   ├── Authentication               8 ms
   │
   ├── Validate request            14 ms
   │
   └── PostgreSQL query            31 ms
```

There is an enormous gap between the short child operations and the total request duration.

The trace hasn't explained the delay yet.

But it has shown that the existing instrumentation is incomplete.

Possible missing operations include acquiring a database connection, waiting for a lock in application code, event-loop scheduling delay, queueing, or synchronous work outside the instrumented spans.

A good engineer does not interpret missing telemetry as proof that no work occurred.

They identify the unobserved interval and instrument it.

---

## 10. Trace Context: Connecting Multiple Processes

Distributed tracing requires a way to associate operations across process boundaries.

OpenTelemetry commonly uses the W3C Trace Context standard.

An HTTP request may contain a header resembling:

```text
traceparent:
00-a0892f3577b34da6a3ce929d0e0e4736-f03067aa0ba902b7-01
```

The header carries information including a trace ID, a parent span ID, and trace flags.

When Service A calls Service B, it can inject trace context into the outgoing request.

Service B extracts that context and starts a child span associated with the same trace.

```text
Service A                       Service B

Trace ID: XYZ                   Trace ID: XYZ
Span ID:  A1                    Span ID:  B1
                                 Parent:   A1
```

The shared trace identifier allows the tracing backend to connect operations.

### Propagation across asynchronous jobs

HTTP propagation is relatively straightforward because requests have headers.

Queues introduce another challenge.

Suppose the API publishes a BullMQ job:

```typescript
await queue.add("generate-invoice", {
  reservationId
});
```

The worker executes later, potentially in another process or even on another machine.

The original HTTP request may have finished long before the job begins.

To preserve causal context, the application can propagate suitable tracing metadata through the message's headers or payload metadata, depending on the queue technology and instrumentation.

For asynchronous work, tracing systems may use parent-child relationships or span links to express causality without pretending every operation belongs to one uninterrupted synchronous call.

This distinction matters for retries, batch processing, and jobs that combine information from several initiating operations.

### Correlation doesn't imply causation

Just because two log records share a trace ID does not mean one caused the other.

A trace describes relationships established by instrumentation.

Poor propagation or incorrect span parenting can create misleading representations.

Distributed tracing improves visibility into execution relationships, but it doesn't automatically establish a complete causal explanation of a production incident.

---

## 11. OpenTelemetry: Standardizing Instrumentation

If every application framework and monitoring vendor required a completely different instrumentation model, changing observability tools would become expensive.

**OpenTelemetry**, commonly abbreviated OTel, provides open APIs, SDKs, semantic conventions, and collection mechanisms for telemetry.

Its goal is to make instrumentation more consistent and less dependent on a particular monitoring backend.

An application can emit traces and metrics through OpenTelemetry without embedding every vendor's proprietary SDK throughout business logic.

### The architecture

```text
Node.js Application
       │
       ▼
OpenTelemetry SDK
       │
       ▼
OTLP Export
       │
       ▼
OpenTelemetry Collector
       │
       ├── Trace Backend
       ├── Metrics Backend
       └── Log Backend
```

OTLP is the OpenTelemetry Protocol used for transporting telemetry.

The Collector can receive data, process it, batch it, filter selected attributes, and export it to suitable backends.

Not every deployment needs a Collector initially, but it provides a useful separation between application instrumentation and telemetry infrastructure.

### Automatic instrumentation

OpenTelemetry provides instrumentation libraries for common Node.js frameworks and dependencies.

For example:

- HTTP servers and clients.
- Express and supported web frameworks.
- PostgreSQL clients.
- Redis clients.
- Selected messaging libraries.

Auto-instrumentation can create spans around supported library operations without developers manually adding tracing code to every function.

But it has an important limitation.

Automatic instrumentation usually understands technical operations, not the complete business semantics of your application.

It may recognize that an HTTP request was made to a hotel supplier, but it cannot automatically understand whether that request was an availability check, a reservation commitment, or a cancellation.

Those distinctions may require application-specific instrumentation.

### A minimal Node.js setup

Install the relevant packages:

```bash
npm install \
  @opentelemetry/api \
  @opentelemetry/sdk-node \
  @opentelemetry/auto-instrumentations-node \
  @opentelemetry/exporter-trace-otlp-http
```

Create `instrumentation.cjs`:

```javascript
const { NodeSDK } =
  require("@opentelemetry/sdk-node");

const { getNodeAutoInstrumentations } =
  require("@opentelemetry/auto-instrumentations-node");

const { OTLPTraceExporter } =
  require("@opentelemetry/exporter-trace-otlp-http");

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter(),
  instrumentations: [
    getNodeAutoInstrumentations()
  ]
});

sdk.start();

process.on("SIGTERM", () => {
  sdk.shutdown().catch(console.error);
});
```

Start the application with instrumentation loaded first:

```bash
node --require ./instrumentation.cjs dist/server.js
```

The default OTLP HTTP trace exporter expects a compatible receiving endpoint, commonly at `http://localhost:4318/v1/traces`. The example won't produce a useful remote trace visualization unless a Collector or compatible backend is running and reachable.

Loading instrumentation before the application is important because many libraries must be instrumented before their modules initialize.

### Manual business spans

Suppose a reservation operation contains an important business step:

```typescript
import { trace } from "@opentelemetry/api";

const tracer = trace.getTracer("booking-api");

async function confirmReservation(
  reservationId: string
) {
  return tracer.startActiveSpan(
    "reservation.confirm",
    async (span) => {
      try {
        span.setAttribute(
          "reservation.workflow",
          "standard"
        );

        return await executeConfirmation(
          reservationId
        );
      } catch (error) {
        if (error instanceof Error) {
          span.recordException(error);
        }

        throw error;
      } finally {
        span.end();
      }
    }
  );
}
```

The span identifies a meaningful application operation rather than merely an HTTP or database interaction.

In a real system, span status and error classification should also follow the selected instrumentation conventions.

Notice that we deliberately avoid attaching the raw reservation ID as a metric label. A span can carry contextual identifiers when privacy and access controls permit, but high-cardinality identifiers have very different consequences when used in metrics.

---

## 12. The Investigation: Finding the Missing Ten Seconds

We now have the tools to investigate our original incident.

Our API's p99 latency has increased dramatically, yet overall CPU, memory, and database query durations remain healthy.

A systematic investigation begins by narrowing the affected population.

### Step 1 — Identify the pattern

Metrics reveal:

```text
GET /hotels/search
    p99: 240 ms

GET /reservations/:id
    p99: 9,800 ms

POST /reservations
    p99: 310 ms
```

The problem is concentrated in reservation retrieval.

Further segmentation shows that the delays predominantly affect reservations associated with one particular supplier integration.

This is useful because it rules out several broad explanations.

If the entire application were suffering from CPU saturation, we would expect a wider range of operations to deteriorate.

### Step 2 — Examine a slow trace

A slow request reveals:

```text
GET /reservations/:id              9,800 ms
│
├── Authentication                    8 ms
│
├── Reservation authorization        12 ms
│
├── Load reservation              9,550 ms
│   │
│   ├── Acquire DB connection      9,510 ms
│   │
│   └── Execute SELECT                24 ms
│
└── Serialize response               11 ms
```

The database query executes quickly after acquiring a connection.

The major delay occurs in the application's database connection pool.

### Step 3 — Examine pool saturation

Metrics show:

```text
Pool maximum connections:       20
Pool active connections:        20
Pool idle connections:           0
Pool pending acquisitions:      86
Database query p95:            32 ms
```

The application has twenty connections checked out, while dozens of requests are waiting.

But PostgreSQL itself is relatively idle.

That suggests the application is holding connections without actively executing queries.

### Step 4 — Identify who holds the connections

Additional tracing and PostgreSQL session inspection reveal that many connections belong to a reservation-refresh workflow.

The code resembles:

```typescript
await dataSource.transaction(
  async (manager) => {
    const reservation = await manager.findOneBy(
      ReservationEntity,
      { id: reservationId }
    );

    const supplierStatus =
      await hotelSupplier.getReservationStatus(
        reservation.externalId
      );

    reservation.status = supplierStatus;

    await manager.save(reservation);
  }
);
```

Look carefully.

The application opens a database transaction, loads the reservation, and then awaits a remote supplier API.

While the external API is processing, the database connection remains associated with the transaction.

The supplier has recently begun experiencing intermittent ten-second delays.

Those slow calls keep database connections occupied, reducing the number available for unrelated requests.

Eventually, the connection pool becomes saturated.

The database isn't slow.

The application is holding database connections while waiting for something else.

### Step 5 — Correct the workflow

An obvious improvement is to avoid keeping a database transaction open while making an unrelated external HTTP request.

For example, the application may retrieve the necessary reservation identifiers, perform the supplier request outside the database transaction, and then apply an appropriate state transition.

However, this introduces an important correctness question: what if the reservation changes between the initial read and the later update?

The implementation may need optimistic concurrency checks, a version field, conditional updates, or a durable workflow depending on the business invariant.

We shouldn't trade connection-pool starvation for incorrect reservation state.

This is where observability connects directly to architecture and transaction design.

### Step 6 — Verify the improvement

After the fix, we measure:

```text
Database pool pending:      0–3
Connection acquisition p99: 18 ms
Reservation API p99:        410 ms
Supplier API p99:        9,500 ms
```

The external supplier remains slow for some operations.

But the delay no longer monopolizes the application's database connections.

The system has become more resilient because the slow dependency's effect is contained.

This is the kind of investigation that distinguishes a useful observability system from a wall of attractive graphs.

---

## 13. Dashboards, Alerts, and the Difference Between Data and Action

A dashboard helps engineers inspect system behavior.

An alert tells them that a condition requires attention.

These are not equivalent.

A dashboard with two hundred graphs may be useful during diagnosis but inappropriate as an alerting strategy.

### Alert on meaningful symptoms

Suppose PostgreSQL CPU usage reaches 85%.

Should someone be paged?

Not necessarily.

A database may operate correctly at relatively high utilization, depending on workload and available headroom.

Now suppose customers are experiencing a sustained 12% checkout failure rate.

That is clearly important.

Customer-facing symptoms often deserve higher alert priority than isolated resource measurements.

Resource alerts still matter, especially when they provide early warning of exhaustion, but their thresholds should connect to operational consequences.

### Alert fatigue

Imagine an on-call engineer receives 200 notifications daily.

Most are transient CPU spikes, brief queue fluctuations, or expected deployment effects.

Eventually, the engineer begins ignoring them.

The monitoring system has undermined its own purpose.

A useful alert should communicate:

- What is failing?
- How seriously are users affected?
- Is immediate human intervention necessary?
- What evidence supports the alert?
- Where should investigation begin?

Not every warning belongs on someone's phone at 03:00.

Some belong in dashboards, scheduled reviews, or automated remediation workflows.

### SLO-based monitoring

A more mature approach connects alerting to **Service-Level Objectives**, or SLOs.

Suppose the booking API has an objective that 99.9% of eligible requests succeed over a rolling thirty-day period.

The associated indicator might be:

\[
SLI =
\frac{\text{Successful eligible requests}}
{\text{Total eligible requests}}
\]

At one million eligible requests, a 99.9% objective permits approximately 1,000 unsuccessful requests within the window.

This is a request-based reliability objective, not a guarantee about exactly how many minutes of downtime are permitted.

Monitoring how quickly the system consumes its permitted failure budget can produce more meaningful alerts than checking isolated error spikes.

We'll examine SLOs, error budgets, and reliability policy in depth next session.

For now, the important distinction is that **good alerting reflects service impact and urgency, not merely unusual numbers**.

---

## 14. Observability Has Its Own Engineering Costs

Telemetry infrastructure isn't free.

A company with hundreds of services can generate enormous quantities of metrics, logs, and trace data.

Every signal must be transported, processed, stored, indexed, queried, and eventually deleted.

Several design decisions determine whether observability remains economically sustainable.

### Metric cardinality

Consider:

```text
http_requests_total{
  method="GET",
  route="/reservations/:id",
  status="200"
}
```

These labels have relatively bounded values.

Now imagine adding:

```text
customer_id="customer-193847"
```

If the platform has 500,000 customers, the number of distinct time series may grow dramatically.

This is **high cardinality**.

A metric isn't one value for all time. Distinct combinations of labels may create distinct time series, each requiring storage and processing.

Uncontrolled cardinality can overwhelm metrics backends or make them unnecessarily expensive.

Use labels such as route templates, operation categories, service names, and error classes when they provide meaningful aggregation.

Avoid using arbitrary user IDs, request IDs, full URLs with dynamic identifiers, or unbounded strings as metric labels.

### Trace sampling

Recording every span of every request can also be expensive.

Suppose an application processes 2,000 requests per second, each producing twenty spans.

That is:

\[
2,000 \times 20 = 40,000
\]

Approximately 40,000 spans per second.

A tracing platform may not need to retain every one of them.

**Head sampling** makes a sampling decision early in the trace lifecycle, often using a configured probability or parent sampling decision.

This reduces data volume efficiently, but it may discard rare failures before knowing they are interesting.

**Tail sampling** makes decisions after examining more of the completed trace.

It can prioritize slow or failed traces, but requires additional buffering, processing, and collector coordination.

The choice depends on traffic, cost, investigation requirements, and tracing architecture.

### Telemetry should not become the outage

An application should not ordinarily block customer operations while synchronously waiting for remote telemetry ingestion.

Telemetry SDKs and collectors commonly support batching and asynchronous export to reduce application overhead.

But queues and buffers have limits.

If the monitoring backend becomes unavailable, the application needs a sensible policy for dropping, buffering, or retrying telemetry without allowing observability failures to exhaust application resources.

The observability system must itself be monitored for dropped records, exporter failures, and ingestion delays.

Otherwise, missing telemetry may be mistaken for a healthy application.

### Security and privacy

Tracing and logging can accidentally expose:

- Access tokens.
- SQL parameters containing personal information.
- Sensitive HTTP headers.
- Customer documents.
- Payment information.
- Internal infrastructure details.

Telemetry deserves access controls, retention policies, data minimization, and appropriate redaction.

The information that makes an incident easy to diagnose can also be valuable to an attacker.

Observability is part of production security, not an exception to it.

---

## 15. Practical Lab — Create an Invisible Bottleneck

Let's reproduce the central idea of our investigation without PostgreSQL, Docker, or any external monitoring service.

We'll create a tiny Node.js server with a deliberately constrained resource pool.

The application will simulate requests that perform work quickly, except for two requests that hold scarce resources while waiting for an external operation.

### Part A — Create the server

Save this as `observability-lab.mjs`:

```javascript
import http from "node:http";
import { performance } from "node:perf_hooks";
import { randomUUID } from "node:crypto";

const sleep = (ms) =>
  new Promise((resolve) => setTimeout(resolve, ms));

const pool = {
  limit: 2,
  active: 0,
  waiters: [],

  async acquire() {
    const started = performance.now();

    if (this.active >= this.limit) {
      await new Promise((resolve) => {
        this.waiters.push(resolve);
      });
    }

    this.active++;

    const waitMs = performance.now() - started;

    return {
      waitMs,

      release: () => {
        this.active--;
        this.waiters.shift()?.();
      }
    };
  }
};

function log(record) {
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    ...record
  }));
}

const server = http.createServer(
  async (req, res) => {
    const requestId = randomUUID();
    const started = performance.now();

    const slow = req.url === "/slow";
    const resource = await pool.acquire();

    try {
      // Simulated work using a scarce resource.
      await sleep(slow ? 1200 : 30);

      res.writeHead(200);
      res.end("OK");

      log({
        requestId,
        route: slow ? "/slow" : "/fast",
        poolWaitMs: Math.round(resource.waitMs),
        durationMs: Math.round(
          performance.now() - started
        ),
        poolActive: pool.active,
        poolPending: pool.waiters.length
      });
    } finally {
      resource.release();
    }
  }
);

server.listen(3000, () => {
  console.log("Listening on port 3000");
});
```

This pool is a deliberately minimal simulation, not a production-ready concurrency primitive.

It illustrates how a resource bottleneck can emerge even when the application is doing almost no CPU-intensive work.

### Part B — Generate concurrent requests

Start the server:

```bash
node observability-lab.mjs
```

In another terminal, create `load.mjs`:

```javascript
const sleep = (ms) =>
  new Promise((resolve) => setTimeout(resolve, ms));

const request = async (path) => {
  const started = performance.now();

  await fetch(`http://localhost:3000${path}`);

  console.log(
    path,
    Math.round(performance.now() - started),
    "ms"
  );
};

await Promise.all([
  request("/slow"),
  request("/slow"),

  (async () => {
    await sleep(20);

    await Promise.all(
      Array.from(
        { length: 18 },
        () => request("/fast")
      )
    );
  })()
]);
```

Run:

```bash
node load.mjs
```

The two slow requests should acquire both available resource slots.

Other requests will queue until a slot becomes available.

Despite `/fast` requiring only approximately 30 milliseconds of simulated work, some of those requests will experience significantly greater end-to-end latency.

### Part C — Investigate the logs

Look for records resembling:

```json
{
  "route": "/fast",
  "poolWaitMs": 1180,
  "durationMs": 1211
}
```

The route's actual processing time is short.

Most of its latency comes from waiting for a scarce resource.

The application can exhibit this behavior while CPU usage remains low.

This is the same fundamental mechanism that can occur with database connection pools, worker concurrency limits, or other bounded resources.

### Part D — Modify the experiment

Try three variations.

**Variation 1:** Increase `pool.limit` from two to four.

Observe how this changes the waiting time.

**Variation 2:** Reduce the slow operation from 1,200 milliseconds to 200 milliseconds.

Observe whether the shorter resource-holding interval provides greater improvement than increasing capacity.

**Variation 3:** Release the resource before performing the slow simulated external operation, then reacquire it only when genuinely needed.

This approximates separating a slow external dependency from a database transaction.

Be careful: in real applications, changing when a transaction acquires and releases resources can affect consistency and correctness.

The goal is to understand the resource-lifetime trade-off.

### Part E — Define useful production instrumentation

Imagine turning this toy service into a real backend.

Which signals would you add?

A useful minimal set might include:

```text
http.server.request.duration
db.pool.active_connections
db.pool.pending_requests
db.pool.acquisition.duration
supplier.request.duration
supplier.request.errors
```

The first metric follows OpenTelemetry's HTTP semantic convention. The pool and supplier names are illustrative custom metrics whose exact design would depend on the selected library and instrumentation.

Now decide which of these measurements should be counters, gauges, or histograms.

Finally, identify which measurements should be attached to individual traces.

The lab is successful when you can explain why the requests were slow, demonstrate the evidence, and propose a fix without relying on arbitrary guesses about CPU utilization.

---

## 16. Engineering and Interview Challenges

### Challenge 1 — The misleading average

An API processes one million requests daily. Its average latency is 150 milliseconds, but customers regularly complain about ten-second responses.

Which measurements would you introduce, and why might p95 still fail to reveal the problem?

### Challenge 2 — The healthy database

An application's request latency suddenly triples.

PostgreSQL reports low CPU usage, and its SQL query execution metrics remain fast.

What database-related problems might still explain the slowdown?

### Challenge 3 — The broken trace

A request crosses API Gateway, Node.js, Redis, and a BullMQ worker.

The HTTP portion has a complete trace, but the worker creates a new unrelated trace.

How would you establish a meaningful relationship between them?

### Challenge 4 — The expensive metrics system

Your observability platform suddenly becomes dramatically more expensive.

Investigation reveals that developers added `user_id`, `reservation_id`, and complete request URLs as labels to several metrics.

Why is this dangerous, and how would you redesign the instrumentation?

### Challenge 5 — The alert that nobody trusts

Your engineering team receives dozens of alerts daily, mostly caused by brief CPU spikes and transient infrastructure fluctuations.

Meanwhile, an actual customer-facing incident goes unnoticed for twenty minutes.

How would you redesign the alerting strategy?

---

## 17. Solutions and Discussion

### Challenge 1 — Measure the distribution, not just the mean

I'd introduce request-duration histograms and inspect percentiles such as p95, p99, and potentially higher percentiles where traffic volume makes them meaningful.

If only 2% of requests are slow, p95 may still look excellent because 95% of requests complete before entering the slow tail.

I'd also segment latency by route, operation type, service version, and relevant low-cardinality business categories.

The objective is to determine whether the problem affects particular workflows rather than treating the entire API as one homogeneous population.

Histograms are preferable to averaging independently calculated instance percentiles.

### Challenge 2 — Query execution time isn't connection acquisition time

A request may spend several seconds waiting for a connection before PostgreSQL begins executing its SQL query.

Other possibilities include lock contention, network delays, transaction scheduling, or application code holding connections while performing unrelated work.

I'd inspect connection-pool utilization, pending acquisitions, acquisition-duration histograms, database session states, and traces showing the interval between requesting and executing database work.

A fast SQL query does not imply that the application accessed the database quickly.

### Challenge 3 — Propagate context through the queue

The enqueueing operation should record or propagate suitable trace context with the job metadata, using instrumentation supported by the queue library or explicit propagation.

The worker can extract that context and create a related span or trace, using parent-child relationships or span links according to the asynchronous workflow's semantics.

The worker should also include appropriate business correlation identifiers in its structured logs.

However, trace IDs are not substitutes for durable job identifiers or business operation IDs. A job may be retried, delayed, or executed after the initiating trace's ordinary lifetime.

### Challenge 4 — Control cardinality and separate telemetry purposes

Every unique combination of metric labels may create another time series.

Customer IDs and reservation IDs can generate enormous cardinality because their possible values grow with business activity.

I'd replace raw request URLs with route templates and use bounded labels such as operation type, response class, and service name.

Individual identifiers belong in appropriately protected logs or trace attributes when needed for investigation, subject to privacy and retention requirements.

Metrics should summarize behavior across meaningful populations rather than become a database of individual customer operations.

### Challenge 5 — Alert on user impact and actionable risks

I'd identify the service's most important customer-facing operations and define indicators such as success rate, latency, and processing delay.

Paging alerts should focus on significant user impact, rapidly deteriorating reliability, or imminent resource exhaustion that requires prompt intervention.

Less urgent anomalies should remain available through dashboards, lower-severity notifications, or scheduled reviews.

Every alert should have a clear owner, useful context, and an investigation path.

An alerting system succeeds when important incidents are noticed and acted upon—not when it produces the largest possible number of notifications.

---

## Mental Model

When investigating an unfamiliar production problem, move through five questions:

1. **Symptoms:** What are customers actually experiencing, and how widespread is it?
2. **Patterns:** Which metrics reveal when, where, and under what conditions the behavior occurs?
3. **Execution:** Which traces show where time or failures accumulate?
4. **Evidence:** Which logs and resource measurements explain the suspicious operations?
5. **Verification:** Does the proposed fix improve the relevant user-facing indicators without introducing new correctness risks?

Think of the three signals as complementary tools:

- **Metrics reveal patterns.**
- **Traces reveal execution paths.**
- **Logs reveal contextual events.**

**The central principle: Good observability makes unfamiliar failures investigable. It doesn't merely make familiar measurements visible.**


---

## Next Lecture — SE440-L02: Reliability Engineering and Incident Response

Continue in **SE440 — Production Reliability and Quality Engineering**.

## Further Reading

1. **Google — [Site Reliability Engineering: Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)**. The four golden signals, monitoring philosophy, alert design, and the distinction between symptoms and causes.

2. **Google — [The SRE Workbook: Monitoring](https://sre.google/workbook/monitoring/)**. Practical monitoring design, meaningful indicators, alerting, and production measurement techniques.

3. **OpenTelemetry — [Observability Primer](https://opentelemetry.io/docs/concepts/observability-primer/)**. The conceptual foundations of traces, metrics, logs, and observability signals.

4. **OpenTelemetry — [JavaScript Documentation](https://opentelemetry.io/docs/languages/js/)**. Node.js instrumentation, APIs, SDKs, automatic instrumentation, and exporting telemetry.

5. **OpenTelemetry — [Context Propagation](https://opentelemetry.io/docs/concepts/context-propagation/)**. How trace context moves across services and process boundaries.

6. **OpenTelemetry — [Collector Architecture](https://opentelemetry.io/docs/collector/architecture/)**. Receivers, processors, exporters, and vendor-independent telemetry pipelines.

7. **Prometheus — [Histograms and Summaries](https://prometheus.io/docs/practices/histograms/)**. Why percentiles require careful statistical treatment and how aggregatable histograms support fleet-wide latency analysis.

8. **Brendan Gregg — [The USE Method](https://www.brendangregg.com/usemethod.html)**. A systematic resource-analysis method based on utilization, saturation, and errors.

9. **Cindy Sridharan — *Distributed Systems Observability***. A focused examination of instrumentation, debugging, and the challenges of understanding distributed production software.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE440-L01  OBSERVABILITY — INTERVIEW GLANCE CARD

CORE MODEL
  Accurate metrics can still fail to explain behavior
  Monitoring = selected conditions; observability = infer internals
  Symptom (p99) → explanation (wait for DB conn 9.5s, query 31ms)

THREE SIGNALS
  Logs     What events / context?
  Metrics  How often / how severe?
  Traces   Where did time go across the path?
  Move between them; complementary

LOGS
  Structured JSON + request_id/trace_id/version/operation
  Levels consistent; business rejection ≠ ERROR spam
  Cost + privacy: don't log tokens/PII/payload dumps

CORRELATION
  Propagate request_id across services
  AsyncLocalStorage for in-process; explicit across queue/HTTP
  Request ID ≠ distributed trace ID

METRICS
  Counter (rate via Δ) · Gauge (level) · Histogram (distribution)
  Average hides tails; two services same mean, different pain

PERCENTILES
  p50/p95/p99 positions in distribution
  Don't average instance p99s — combine histograms
  Tiny samples → unstable percentiles; segment by route/version

RED / USE / GOLDEN
  RED: Rate, Errors, Duration (service)
  USE: Utilization, Saturation, Errors (resources)
  Golden: latency, traffic, errors, saturation

TRACING
  Trace = operation; span = unit of work; parent links
  Critical path ≠ sum of concurrent child durations
  Missing span gap = uninstrumented wait (pool, lock, event loop)
  W3C traceparent; inject/extract across HTTP; queue metadata/links
  Correlation ≠ causation if parenting wrong

OPENTELEMETRY
  API/SDK/OTLP/Collector → backends
  Auto-instr: tech ops; manual spans for business steps
  Load instrumentation before app modules
  IDs on spans OK; high-cardinality IDs as metric labels = danger

INVESTIGATION PATTERN
  Segment which route/population → slow trace → pool USE →
  who holds connections (txn open during supplier HTTP) → fix lifetime

ALERTS
  Page on user impact / burn, not every CPU blip
  Alert fatigue kills detection; SLO/error-budget alerts later (L02)
  Dashboards diagnose; alerts demand action

TELEMETRY COST / SAFETY
  Cardinality explosion (user_id labels)
  Head vs tail sampling; async export; don't block requests
  Redact secrets; monitor dropped telemetry

SENIOR LINE: Good observability makes unfamiliar failures
             investigable—not merely familiar graphs visible.
```

---


