---
id: SE215-L09
course: SE215
title: "Data Engineering for Application Developers"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE215-L08
next: SE215-L10
---


# SE215 — The Software Engineering Ecosystem

## Lecture 09: Data Engineering for Application Developers

*Your booking service is healthy. PostgreSQL contains the correct reservations, payment processing is working, and no customers are complaining. Yet the finance dashboard reports more revenue than the company actually collected. The data pipeline is green, all scheduled jobs completed successfully, and no messages appear to be missing. How can every technical component be working while the business numbers are wrong?*

# Part I — Intuition

## The picture to carry in your head

Imagine Mercury, our hotel-booking company, has become successful.

Thousands of customers search for hotels, make reservations, modify bookings, and occasionally request refunds.

The backend uses PostgreSQL to store reservations and payment operations.

This database is essential to running the business.

When a customer reserves a room, the application must determine whether inventory is available, record the reservation, and coordinate payment processing.

These operations require correctness under concurrency.

But management wants something different.

How many bookings did we make yesterday?

Which countries are growing fastest?

How much revenue did we collect this month?

Which acquisition campaigns bring customers who actually complete bookings?

What proportion of reservations are canceled?

And how does this compare with last year?

The application database contains much of the information needed to answer these questions.

So why not simply run SQL queries against PostgreSQL?

Because operational databases and analytical workloads have different priorities.

## 1. One database, two very different jobs

Imagine a restaurant during the evening rush.

The kitchen receives individual orders.

Each order needs to be processed accurately and promptly.

Now imagine a financial analyst walks into the kitchen and asks everyone to stop while they calculate how many dishes were sold across the last six months.

The analyst's question is legitimate.

But it's not the same kind of work as preparing the next customer's dinner.

Operational databases are optimized around executing business operations.

Analytical systems are optimized around examining large collections of historical information.

The terminology is **OLTP**, online transaction processing, versus **OLAP**, online analytical processing.

OLTP workloads commonly involve many relatively small reads and writes, transactional correctness, and low-latency responses.

OLAP workloads commonly scan, filter, aggregate, and compare large volumes of data.

These aren't absolute categories. PostgreSQL can perform analytics, and analytical databases can process fresh data.

But the workloads create different performance and architectural pressures.

Mercury doesn't want a complicated quarterly revenue report to compete with customers trying to complete reservations.

So the company builds a separate analytical environment.

## 2. Moving data creates a new kind of correctness problem

Suppose Mercury copies reservation data from PostgreSQL into a warehouse every night.

The warehouse contains a table of bookings.

Analysts use it to calculate revenue.

Everything seems straightforward.

Then a customer books a room on Monday and cancels on Tuesday.

The booking was real.

The cancellation was real.

The payment may have been authorized, captured, partially refunded, or fully refunded.

Which number belongs in Monday's revenue report?

Which number belongs in Tuesday's report?

And if management asks for net revenue over the entire week, how should those operations be combined?

The database can accurately record every operation while the report still answers the wrong question.

**Data correctness isn't only about copying values. It's also about preserving what those values mean.**

A reservation is not necessarily a completed sale.

A payment authorization is not necessarily captured money.

A refund is not merely a negative booking.

A canceled reservation may still incur a fee.

Analytical systems need explicit business definitions.

## 3. A successful pipeline can still produce bad information

Let's make the problem concrete.

Mercury processes one hundred successful payment captures.

Each is worth one hundred and twenty euros.

Gross captured payments total twelve thousand euros.

Four customers subsequently receive full refunds.

The net amount captured less refunds is therefore eleven thousand five hundred and twenty euros.

But the analytics pipeline accidentally processes four capture notifications twice.

The dashboard sums all the capture records and displays twelve thousand four hundred and eighty euros.

It also fails to subtract the refunds.

Now consider the pipeline's monitoring.

All messages were delivered.

Every transformation ran.

The warehouse accepted every row.

The reporting query completed successfully.

From an infrastructure perspective, the pipeline appears healthy.

From a financial perspective, it's wrong.

The mistake isn't that PostgreSQL forgot a booking.

It's that the analytical representation double-counted events and misunderstood which operations belong in the calculation.

## 4. The data journey

A useful mental model follows data through several responsibilities.

First, an application creates or modifies authoritative operational data.

Next, a mechanism extracts changes or business events.

Then a transport or ingestion system moves those records into another environment.

A transformation layer cleans, organizes, and combines the information.

An analytical database stores it in a form suitable for reporting.

Finally, dashboards and analysts query that information.

Conceptually:

```text
Business application
        |
        v
Operational PostgreSQL
        |
        v
Events / CDC / Batch Extraction
        |
        v
Ingestion and Storage
        |
        v
Transformations and Data Quality
        |
        v
Analytical Warehouse
        |
        v
Reports and Dashboards
```

Every boundary can introduce new failure modes.

Records can arrive twice.

They can arrive late.

A schema can change.

A transformation can incorrectly join two datasets.

A report can use an outdated definition.

And a successful job can produce an incomplete result.

Data engineering is the discipline of constructing and maintaining this journey reliably.

## 5. Developers are part of the data pipeline

It's tempting for application developers to say:

"We write the database records. The data team handles everything afterward."

But the data team cannot invent business semantics that the application never recorded.

Suppose the application emits an event called `bookingCompleted`.

What does that mean?

Was inventory reserved?

Was the supplier booking confirmed?

Was payment authorized?

Was payment captured?

Does a later cancellation change that fact?

If the event's meaning is ambiguous, downstream systems must guess.

The application developer is responsible for exposing meaningful, correctly identified business facts.

The data engineer is responsible for transporting, transforming, validating, and making those facts useful for analysis.

Their work is different, but neither side can provide trustworthy analytics alone.

### Three questions before the Deep Dive

1. How can an application database contain correct records while the analytical dashboard reports incorrect revenue?
2. Why might copying database rows be insufficient when the business needs a historical account of events?
3. If an event is delivered twice, should the analytical result necessarily count it twice?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. Begin with the business definition

Mercury's finance director reports that revenue is overstated.

Before investigating Kafka, SQL, or dashboards, we need to establish what revenue means.

This may sound like a business question rather than an engineering question.

It is both.

Suppose the company records these operations:

A customer creates a reservation for five hundred euros.

The payment provider authorizes five hundred euros.

Later, the provider captures five hundred euros.

A week afterward, the customer receives a refund of one hundred euros.

How many euros of revenue does this represent?

The answer depends on the metric.

Booking value may be five hundred.

Gross captured payment volume may be five hundred.

Net captured payments after refunds may be four hundred.

Recognized accounting revenue may follow additional rules involving service delivery, commissions, taxes, and contractual obligations.

These numbers describe different things.

We shouldn't call all of them simply "revenue."

### Define the grain

In data modeling, the **grain** describes what one row represents.

Consider an analytical table named `fact_payment_operations`.

Does one row represent a reservation?

A customer?

A payment attempt?

A captured charge?

A payment-provider notification?

Those are different grains.

If we don't establish the grain, aggregate queries become dangerous.

For example, a reservation may contain several payment operations.

Joining reservations directly to payment operations produces multiple rows for some reservations.

If we then sum the reservation's total price, we may count that price several times.

The SQL may be perfectly valid.

The business calculation is wrong.

The first rule of trustworthy analytics is therefore:

**Define what one record represents before deciding how to aggregate it.**

## 2. Extract, transform, load—or extract, load, transform?

Data must move from operational systems into an analytical environment.

Two familiar approaches are ETL and ELT.

### ETL

ETL means extract, transform, load.

Data is extracted from source systems, transformed into the desired representation, and loaded into the destination.

For example, Mercury might extract booking operations, normalize their formats, calculate certain fields, and insert the results into a reporting database.

### ELT

ELT means extract, load, transform.

Data is first loaded into an analytical system, where transformations are performed afterward.

This is common when the destination is a capable analytical warehouse.

Mercury could ingest operational records into a raw or staging area, then use SQL transformations to construct reporting tables.

The main distinction concerns where and when transformations occur.

It doesn't mean one approach is inherently modern and the other obsolete.

### Why retaining raw data can help

Suppose the business discovers that a revenue transformation was incorrect for the previous two months.

If the pipeline retained trustworthy source records, the team may be able to correct the transformation and rebuild the affected analytical data.

If the pipeline permanently discarded the source details, recovery becomes more difficult.

Raw data retention can improve reproducibility and auditing.

But it also introduces storage, privacy, governance, and retention obligations.

Preserving everything forever isn't automatically appropriate.

## 3. Batch processing versus streaming

Mercury has several possible ways to deliver information into analytics.

### Batch extraction

The simplest architecture might run a scheduled job every night.

The job queries reservations changed since the previous run and loads them into an analytical database.

This can work well when the business accepts daily reporting.

It is comparatively easy to understand.

But incremental extraction needs care.

If records are updated while the extraction runs, the job must avoid missing changes.

If the job crashes after loading some records but before recording completion, it must recover safely.

And timestamps alone are not always a sufficiently reliable change-tracking mechanism.

### Streaming

Alternatively, the application or database can produce a stream of changes.

Downstream consumers process the stream continuously or in frequent batches.

This can reduce reporting latency.

But it introduces additional concerns about ordering, duplicate delivery, consumer failures, retention, and replay.

Streaming isn't automatically superior.

If finance needs accurate numbers tomorrow morning, a well-designed batch pipeline may be simpler and more reliable than an elaborate real-time streaming architecture.

Choose freshness according to the business need.

## 4. Business events and change data capture are not the same thing

Now let's distinguish two important sources of analytical data.

### Business events

The application may publish an event such as:

`PaymentCaptured`.

That event expresses a business fact.

It can include a payment-operation ID, reservation ID, amount, currency, event timestamp, and versioned schema.

The application defines what the event means.

### Change Data Capture

Change Data Capture, commonly abbreviated CDC, observes changes to database records.

For PostgreSQL, one approach uses logical decoding of changes recorded in the database's write-ahead log.

A tool such as Debezium can capture changes and publish corresponding records downstream.

This reduces the need for application code to issue a second independent write solely for data replication.

But CDC and business events aren't interchangeable.

Suppose a row changes from `payment_status = authorized` to `payment_status = captured`.

CDC can report the row update.

A carefully designed business event can explicitly say that the payment capture succeeded and identify the corresponding business operation.

The difference is semantic.

A database mutation describes a change in stored state.

A business event describes something meaningful that occurred in the domain.

Sometimes the mapping is straightforward.

Sometimes several database changes participate in one business event.

### The dual-write problem

If application code commits a database transaction and separately publishes an event, a crash between the two operations can leave them inconsistent.

Our CS430 and SE320 lectures explain transactional outbox patterns for coordinating durable state changes with later event publication.

For analytical pipelines, the same principle applies.

A robust event source must account for what happens when the publisher crashes or delivery is repeated.

## 5. Kafka: transporting records isn't interpreting them

Mercury decides to use Apache Kafka for event distribution.

Kafka provides a distributed event-streaming platform.

Producers publish records to topics.

Consumers read those records.

Topics are partitioned to support scalable storage and consumption.

This is useful when multiple systems need access to a continuing stream of events.

For example, payment events may be consumed by analytics, fraud detection, and operational monitoring.

But we shouldn't treat Kafka as a universal correctness machine.

### Ordering depends on the partition

Kafka preserves ordering within an individual partition under its relevant guarantees.

It doesn't provide one globally ordered timeline across every partition of a topic.

If order matters for all events belonging to a reservation, the partitioning strategy deserves attention.

Using a suitable reservation identifier as the message key can help route related records consistently.

But an event that arrives after another event isn't necessarily semantically newer.

Source timestamps, versions, and operation identities may still matter.

### Delivery and duplicate processing

Consumers can fail after processing a record but before durably recording their progress.

The record may be processed again after recovery.

Kafka provides features supporting stronger processing guarantees in particular Kafka-to-Kafka workflows, but those guarantees do not automatically extend to an arbitrary external database or business side effect.

For analytics, we must deliberately manage duplicates and processing state.

The crucial distinction is:

**Reliable message transportation is not the same thing as correct analytical interpretation.**

## 6. Building a warehouse: raw, staging, and reporting data

Let's follow Mercury's payment events after ingestion.

A common architecture separates data into conceptual layers.

The first contains records resembling the original source.

A staging layer standardizes field names, data types, and basic validity.

A reporting layer organizes information into forms appropriate for analytics.

Not every company uses exactly these layers or names.

The useful idea is to separate source ingestion from business interpretation.

### Fact tables

A fact table represents measurable events or activities.

For Mercury, one fact table might contain payment operations.

Another might contain reservations.

Each needs an explicit grain.

For example, the payment fact table might contain one row per unique business payment operation.

Fields could include operation ID, reservation ID, operation type, amount, currency, and effective timestamp.

### Dimension tables

Dimensions provide descriptive context.

A hotel dimension might describe hotel identity, location, and category.

A customer dimension might describe relevant customer attributes, subject to privacy requirements.

A date dimension can support reporting by calendar periods.

These structures are often organized into star schemas.

We don't need to explore every modeling convention here.

The important point is that analytical models are organized around questions and measurements rather than merely copying the application's object model.

### Historical attributes

Suppose a hotel changes ownership or category.

Should last year's bookings be reported using the hotel's current category or the category that was valid at the time?

Both questions can be legitimate.

Historical dimension modeling provides ways to preserve earlier versions when necessary.

Again, the business question determines the data model.

## 7. Warehouses, data lakes, and lakehouses

Where should Mercury store analytical information?

An analytical warehouse is designed to support substantial analytical querying, often using column-oriented storage and execution techniques.

Common examples include BigQuery, Snowflake, Amazon Redshift, and analytical engines such as ClickHouse, although their architectures differ.

A data lake commonly stores files and datasets in object storage, often using formats such as Parquet.

A lakehouse combines aspects of lake-based storage with table-management and analytical capabilities, potentially including transactional metadata and schema evolution.

These categories overlap in modern systems.

We shouldn't assume every product fits a pure textbook definition.

### Why column-oriented storage helps

Imagine a reporting query that calculates the total captured amount across millions of payment operations.

It needs only a few fields.

A column-oriented analytical engine may read and process those columns efficiently rather than retrieving complete application-style records.

Our CS340-L06 chapter explains the underlying physical trade-offs.

For Mercury, the relevant decision is less about whether warehouses or lakehouses sound sophisticated and more about workload, integration, operational cost, governance, and team expertise.

A small company may start with a straightforward reporting database.

A large organization may need dedicated analytical infrastructure.

## 8. dbt: transformations become maintained software

Now Mercury has ingested payment records into its warehouse.

It needs to turn them into trustworthy business models.

A common tool for this work is **dbt**.

dbt lets teams define analytical transformations, commonly as SQL models, along with dependencies, tests, documentation, and other development conventions.

For example, a model might transform raw payment events into a table of unique payment operations.

Another might calculate daily net captured payments.

A third might aggregate results by hotel or country.

These transformations can be version-controlled and reviewed like application code.

### Analytical tests

Data transformations have assumptions.

Every payment operation should have an operation ID.

Certain fields should not be null.

An operation ID should be unique at the relevant grain.

Every reservation reference should connect to a valid reservation when the model requires that relationship.

dbt supports tests for assumptions such as uniqueness, non-null values, accepted values, and relationships.

But a passing uniqueness test doesn't prove the definition of revenue is correct.

Technical data tests and business reconciliation serve different purposes.

### Incremental models

Suppose Mercury's warehouse contains five years of payment history.

Recomputing every transformation from scratch each hour may be wasteful.

Incremental models process a selected portion of new or changed source data and update the target.

This can improve efficiency.

But now consider late refunds.

A refund for a booking from three months ago arrives today.

If the incremental transformation considers only booking dates from the last two days, it may never revisit the affected historical total.

Incremental processing requires careful attention to which timestamps determine updates.

The model may need a lookback window, merge behavior, version tracking, or another correction strategy.

Performance optimization must not silently invalidate historical accuracy.

## 9. Airflow: orchestration is not the computation itself

Mercury also needs to schedule and coordinate data operations.

For example:

Extract updated reservations.

Load new payment operations.

Run analytical transformations.

Execute data-quality tests.

Publish a dashboard-ready dataset.

These operations have dependencies.

The transformation shouldn't run before its required data arrives.

The dashboard shouldn't receive a new dataset if critical validation fails.

Apache Airflow is one tool for defining, scheduling, and monitoring such workflows.

Airflow represents workflows as directed acyclic graphs of tasks.

It can schedule runs, coordinate dependencies, retry selected tasks, and support historical backfills.

But Airflow isn't itself a database or an event-streaming broker.

And it isn't designed to be the engine for a continuously running infinite streaming computation.

A team might use Kafka to transport events, a warehouse to store analytical data, dbt to transform it, and Airflow to orchestrate recurring pipeline jobs.

Each tool fulfills a different responsibility.

### The green-run misconception

Suppose the Airflow dashboard shows every task succeeded.

What does that prove?

It proves that the tasks completed according to their configured success conditions.

If a SQL transformation incorrectly counts refunded payments as revenue, Airflow can run that transformation perfectly.

The resulting report will still be wrong.

Operational status and business correctness are separate dimensions.

## 10. Duplicates: one event, several possible identities

Let's revisit our original revenue error.

The payment provider sends a capture notification.

Mercury records it.

The analytical pipeline ingests it.

Then the message is delivered again.

Should the second delivery increase reported revenue?

No.

But detecting duplicates requires understanding identity.

There may be several identifiers.

A transport message ID identifies a delivery-related record.

A producer event ID identifies a particular emitted event.

A payment operation ID identifies the underlying business operation.

A reservation ID identifies the booking to which that operation belongs.

These identifiers aren't interchangeable.

### Two kinds of duplication

Suppose the same event is delivered twice with the same producer event ID.

Deduplicating by event ID can prevent counting the delivery twice.

But suppose an integration accidentally emits two distinct event records for the same payment capture.

Their event IDs differ.

Deduplicating only by event ID will not detect the repeated business fact.

A model defined as one row per captured payment operation needs a stable business-operation identity.

This is why the grain matters so much.

A data pipeline can be technically correct about message delivery while semantically wrong about what constitutes a distinct payment.

## 11. Late data and historical corrections

Now imagine that a customer books a hotel on Monday.

The reservation is recorded immediately.

The payment provider reports a final capture on Tuesday.

A refund occurs on Friday.

The analytics pipeline receives the refund event on Saturday because of an integration delay.

Which day should receive the correction?

There are several relevant times.

**Event time:** When the business operation actually occurred.

**Ingestion time:** When the analytical system received the record.

**Processing time:** When a transformation processed it.

These times can differ.

A reporting system must choose which time defines its metrics.

For example, a report of payment activity by operation date may attribute the refund to Friday even though the data arrived Saturday.

A report showing information known as of Friday evening may legitimately exclude an event that hadn't arrived yet.

Those are different questions.

### Backfills

A backfill processes historical data to populate missing or corrected results.

Suppose Mercury fixes a revenue calculation that was wrong for six months.

Rebuilding the affected period may require replaying historical events or reprocessing source records.

That work must be safe to repeat.

Otherwise, the repair can create new duplicates.

It also needs to coexist with new incoming events.

A backfill that overwrites yesterday's corrected records with older snapshots can make the system worse.

So historical rebuilding needs explicit ordering, identity, and reconciliation policies.

## 12. Schema evolution and data contracts

The application team decides to rename a field from `totalAmount` to `capturedAmount`.

The change looks harmless.

The API is updated.

The backend tests pass.

But the data pipeline still expects `totalAmount`.

The analytical job fails.

Or, more dangerously, it continues running while reading null or default values.

The failure may not be discovered until a financial report is published.

### Schema contracts

A data contract establishes expectations about the structure and semantics of information exchanged between producers and consumers.

It may specify field names, types, nullability, identifiers, event meaning, and compatibility requirements.

For example, a `PaymentCaptured` event should clearly identify the payment operation and currency.

The producer should not silently change the meaning of the amount field.

Additive fields may be compatible with consumers that tolerate unknown values.

Removing or changing a field may require a staged migration.

But schemas describe structure.

Business semantics also need documentation and review.

A field named `amount` is technically valid while remaining ambiguous about gross versus net, major versus minor currency units, or tax inclusion.

### The developer's responsibility

Application engineers should treat data consumers as real consumers of their interfaces.

Changing a database schema or event contract may affect analytics even when the application's API continues working.

The appropriate response is not freezing schemas forever.

It's evolving them deliberately and coordinating meaningful changes.

## 13. Data lineage and quality: can we trust this number?

Suppose Mercury's CEO asks:

"Why does the dashboard say twelve thousand four hundred and eighty euros?"

A useful analytical system should allow the team to trace that number backward.

Which reporting model produced it?

Which transformations fed that model?

Which source tables or events contributed?

When were they ingested?

Were any records rejected or duplicated?

This is **data lineage**: understanding where data came from and how it was transformed.

Lineage helps investigate errors, assess the effect of schema changes, and identify which downstream reports depend on a particular source.

### Data quality is more than schema validation

A source table may satisfy every declared schema constraint while still containing misleading data.

Consider these checks:

A payment-operation ID must not be null.

The operation ID should be unique in a table whose grain is one row per operation.

Currency codes must be recognized.

Refund amounts must follow the relevant domain rules.

Payment-operation totals should reconcile with an authoritative source within a defined tolerance and time window.

These checks operate at different levels.

Some verify structure.

Some verify domain invariants.

Some verify relationships.

Some compare analytical results against operational truth.

A useful quality strategy combines them.

### Freshness matters

Suppose the dashboard is accurate but forty-eight hours behind.

Is it correct?

For an annual financial report, perhaps that delay is acceptable.

For a live fraud-detection system, it may be disastrous.

Data quality therefore includes freshness and completeness, not just correct values.

A dashboard should communicate its reporting delay when that delay matters.

## 14. Reconciliation: returning to an authoritative source

Let's finally resolve the opening incident.

Mercury's dashboard reports twelve thousand four hundred and eighty euros of captured payments.

The operational source contains one hundred real captures worth twelve thousand euros.

Four full refunds worth four hundred and eighty euros reduce net captured payments to eleven thousand five hundred and twenty euros.

Our investigation reveals two defects.

First, the ingestion pipeline recorded duplicate deliveries of four capture events, adding four hundred and eighty euros to the gross-capture total.

Second, the reporting query ignored refunds entirely.

Both errors are semantic.

The pipeline ran.

The records were stored.

The reporting query completed.

But the calculation didn't represent the intended business metric.

### Repairing the pipeline

We first establish the authoritative identity of each payment operation.

Then we remove duplicate representations at the appropriate grain.

We separately represent capture and refund operations.

Next, we calculate gross captured payments and net captured payments according to explicit definitions.

Then we backfill the affected period using a controlled, repeatable process.

Finally, we reconcile the resulting totals against the authoritative payment records and, where appropriate, the payment provider's settlement information.

We also introduce tests to detect similar problems in the future.

The goal isn't simply getting today's dashboard to match the expected number.

It's ensuring the computation has a defensible meaning and can be reproduced.

## 15. What the experienced application developer should understand

An application developer doesn't need to become a full-time data engineer to work effectively with a data team.

But they should recognize how operational design affects downstream analytical reliability.

An ambiguous event name can create years of reporting confusion.

An unstable identifier can make deduplication difficult.

A careless schema change can break historical processing.

A missing timestamp can make late-event attribution impossible.

A source system that overwrites important historical facts may prevent accurate reconstruction.

And an application that emits an event without a durable publication strategy may silently lose information.

Conversely, the data engineer needs to understand which operational records represent authoritative business facts and which are merely intermediate technical states.

The most productive relationship is a shared understanding of contracts, identity, time, and business meaning.

A senior developer should be able to explain the journey from transaction to report, identify where duplication and inconsistency can arise, and participate intelligently in diagnosing incorrect data.

That's the practical purpose of this lecture.

---

# The Oral Examination

Answer aloud before reading the solutions.

### Question 1 — OLTP versus OLAP

Why might Mercury move reporting queries away from its primary PostgreSQL database even though PostgreSQL can execute the required SQL?

### Question 2 — The revenue discrepancy

Mercury has one hundred captures worth twelve thousand euros and four refunds totaling four hundred and eighty euros. Its analytics system reports twelve thousand four hundred and eighty euros. What different problems might explain that discrepancy?

### Question 3 — Change Data Capture

What's the difference between a database change event and a domain event such as `PaymentCaptured`?

### Question 4 — Kafka delivery

A Kafka consumer processes a payment event but crashes before recording its consumer progress. What might happen after restart? How should the reporting model handle it?

### Question 5 — A misleading join

A reservation has three payment operations. A report joins reservations to payments and sums the reservation price. What danger does this introduce?

### Question 6 — Incremental transformations

A refund for a three-month-old booking arrives today. Why might a transformation that processes only the latest booking dates fail to update the correct historical results?

### Question 7 — Airflow and dbt

What distinct responsibilities might Airflow and dbt fulfill in one data pipeline?

### Question 8 — Data contracts

Why is adding a new JSON field usually easier than changing the meaning of an existing field, even when both changes are syntactically valid?

### Question 9 — Reconciliation

All data-pipeline jobs are green, but finance reports incorrect totals. What evidence would you collect and which systems would you compare?

---

# Solutions and Discussion

## Solution 1 — Different workloads and resource priorities

Operational queries usually need low latency and transactional correctness.

Analytical queries may scan and aggregate large historical datasets.

Separating workloads can prevent heavy reporting from contending with critical booking operations and allow analytical infrastructure to be optimized independently.

## Solution 2 — Duplicates and business definitions

Possible causes include duplicated capture records, failure to subtract refunds, incorrect join cardinality, currency handling, or confusion between booking value and captured funds.

The correct investigation begins by defining the target metric and identifying the grain of each input.

## Solution 3 — Storage changes versus business facts

CDC reports changes to database state.

A domain event expresses a business occurrence with a defined meaning.

One business operation may involve several database mutations, so CDC records aren't always direct substitutes for domain events.

## Solution 4 — The record may be processed again

Consumer recovery can cause repeated processing when progress wasn't durably recorded.

The analytical system needs appropriate idempotency or deduplication based on stable identities.

Transport guarantees alone don't establish correct business-level counts.

## Solution 5 — Row multiplication

Joining one reservation to three payment operations produces three joined rows.

Summing the reservation's price across those rows may count it three times.

Define the intended grain and aggregate at the correct level.

## Solution 6 — Historical data can change today

The booking date is old, but the refund event is new.

An incremental process driven only by recent booking dates may never revisit that booking.

Use an appropriate update strategy based on changed records, late-event handling, or historical correction windows.

## Solution 7 — Orchestration versus transformation

Airflow can coordinate and schedule pipeline tasks and monitor their execution.

dbt can define and maintain analytical transformations, dependencies, tests, and documentation.

They may work together without fulfilling identical roles.

## Solution 8 — Existing consumers depend on meaning

Adding a compatible field may allow existing consumers to continue functioning.

Changing what an existing field means can silently alter calculations without producing a schema error.

Semantic compatibility matters alongside structural compatibility.

## Solution 9 — Follow the data backward

Identify the report's metric definition and transformation lineage.

Inspect source records, ingestion identity, duplicate handling, timestamps, join cardinalities, and quality checks.

Reconcile the analytical output against the authoritative business operations within a clearly defined reporting window.

---

# The Mental Model Worth Keeping

A trustworthy analytical number has a traceable journey.

**Source:** Which system owns the underlying business truth?

**Identity:** What does one record represent, and how are duplicates identified?

**Movement:** How does data reach the analytical system, and what can be lost, repeated, or delayed?

**Transformation:** Which business rules convert raw records into meaningful measures?

**Verification:** Can the result be explained and reconciled against authoritative evidence?

A green pipeline means its configured operations completed successfully.

It doesn't necessarily mean the resulting business report is correct.

**Data engineering isn't merely moving information between systems. It's preserving and reconstructing trustworthy meaning across time, transformations, and organizational boundaries.**

# Next Lecture — SE215-L10: Working With Product, Design, and Analytics

Mercury has reliable production systems and a functioning analytical platform.

The product team now proposes a redesigned booking flow.

The designer produces a beautiful interface.

The frontend team implements it.

The backend supports the required operations.

The tests pass, and the new experience is deployed.

Yet booking conversion falls.

Was the implementation wrong?

Did customers misunderstand the design?

Did the team optimize the wrong metric?

Or did the experiment produce misleading evidence?

In the next lecture, we'll examine how software engineers work with product managers, designers, researchers, and analysts to turn business objectives into useful features—and how to determine whether those features actually worked.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Workshop — Repair Mercury's Revenue Pipeline

## Lab A — Construct the misleading data

Imagine the ingestion system receives these payment-operation events.

| Event ID | Operation ID | Type | Amount EUR | Comment |
|---|---|---|---:|---|
| EVT-001 | CAP-101 | Capture | 120 | First payment |
| EVT-002 | CAP-102 | Capture | 120 | Second payment |
| EVT-003 | CAP-103 | Capture | 120 | Third payment |
| EVT-003 | CAP-103 | Capture | 120 | Redelivery |
| EVT-004 | REF-103 | Refund | 120 | Full refund for third payment |

A naïve query that sums every capture row reports four hundred and eighty euros.

But only three distinct captures occurred.

After accounting for the refund, net captured payments equal two hundred and forty euros.

The first task is to reproduce the incorrect calculation.

Then repair it.

## Lab B — Write the reconciliation query

Use a disposable PostgreSQL environment or adapt this example to an analytical SQL engine.

```sql
WITH raw_events (
  event_id,
  operation_id,
  operation_type,
  amount_eur
) AS (
  VALUES
    ('EVT-001', 'CAP-101', 'capture', 120),
    ('EVT-002', 'CAP-102', 'capture', 120),
    ('EVT-003', 'CAP-103', 'capture', 120),
    ('EVT-003', 'CAP-103', 'capture', 120),
    ('EVT-004', 'REF-103', 'refund', 120)
),
deduplicated AS (
  SELECT DISTINCT
    event_id,
    operation_id,
    operation_type,
    amount_eur
  FROM raw_events
)
SELECT
  SUM(
    CASE
      WHEN operation_type = 'capture'
      THEN amount_eur
      ELSE 0
    END
  ) AS gross_captured_eur,

  SUM(
    CASE
      WHEN operation_type = 'capture'
      THEN amount_eur
      WHEN operation_type = 'refund'
      THEN -amount_eur
      ELSE 0
    END
  ) AS net_captured_eur

FROM deduplicated;
```

Expected output:

```text
gross_captured_eur | net_captured_eur
-------------------+-----------------
360                | 240
```

This simplified query assumes repeated deliveries retain identical event identifiers and payloads.

In production, blindly using `DISTINCT` is not a complete deduplication design.

Two different event IDs might refer to the same business operation.

Conversely, two records sharing an event ID but containing conflicting payloads indicate a data-integrity problem rather than something to silently discard.

**Challenge:** Modify the dataset so that a duplicate business capture arrives with a different event ID. How would you enforce one row per payment operation while still retaining legitimate separate refunds?

## Lab C — The dangerous join

Imagine a reservation table:

```text
reservation_id | booking_value_eur
---------------+------------------
R-101          | 500
R-102          | 300
```

And payment operations:

```text
operation_id | reservation_id | type
-------------+----------------+--------
OP-1         | R-101          | authorize
OP-2         | R-101          | capture
OP-3         | R-101          | refund
OP-4         | R-102          | capture
```

Now consider:

```sql
SELECT SUM(r.booking_value_eur)
FROM reservations r
JOIN payment_operations p
  ON p.reservation_id = r.reservation_id;
```

The result is not the total booking value of eight hundred euros.

The join duplicates the first reservation across three payment rows.

**Tasks:**

1. Predict the incorrect total.
2. Explain the joined row cardinality.
3. Rewrite the query to calculate total booking value without multiplication.
4. Separately design a correct report of payment operations.

The fourth question matters. Fixing the booking-value query doesn't automatically define financial revenue.

## Lab D — Design the event contract

Create a versioned event schema for `PaymentCaptured`.

It should include meaningful fields such as:

- Event ID.
- Event schema version.
- Payment operation ID.
- Reservation ID.
- Captured amount in minor currency units.
- Currency.
- Business event timestamp.

Decide whether the event needs additional identifiers for the payment provider or source system.

Now define a corresponding `PaymentRefunded` event.

Consider partial refunds, repeated delivery, out-of-order arrival, and changes in producer schema.

**Challenge:** Which fields identify the event, which identify the business operation, and which identify the reservation? Why should these not be treated as the same concept?

## Lab E — The missing historical refund

Suppose Mercury performs an incremental transformation every hour.

Its filter selects records where `booking_created_at` is within the previous twenty-four hours.

A refund arrives today for a booking created three months ago.

The refund does not affect the output.

Diagnose why.

Then propose two alternative strategies, such as processing changes by operation timestamps or maintaining an incremental fact table keyed by business-operation identity.

Explain how the analytical model can update historical aggregates safely.

## Lab F — Design a production pipeline

Draw one plausible architecture connecting:

- PostgreSQL reservations and payment operations.
- CDC or application-produced business events.
- A durable ingestion mechanism.
- Raw or staging storage.
- Analytical transformations.
- A warehouse.
- A dashboard.
- Data-quality and reconciliation checks.

You may use Kafka, Debezium, dbt, and Airflow where justified.

But don't add tools merely because they're familiar names.

For every component, explain:

1. Which problem it solves.
2. Which failure it might introduce.
3. How the pipeline recovers from repeated or delayed data.
4. How historical records are rebuilt.
5. How the business verifies the final numbers.

## Lab G — The senior interview scenario

An interviewer tells you:

"The data team says Kafka isn't losing messages, Airflow is green, dbt runs successfully, and the warehouse queries return results. But the finance dashboard is wrong. How would you investigate?"

Answer aloud.

A strong response should first clarify the reported metric and its grain, then follow the data lineage through transformations and ingestion.

It should distinguish duplicates, missing records, incorrect joins, late events, and business-definition mismatches.

Avoid immediately blaming Kafka or recommending a database replacement.

The objective is to isolate the point where authoritative business facts stopped being represented correctly.

---

# Further Reading

Official references:

- **Apache Kafka — Introduction:** https://kafka.apache.org/documentation/
- **Confluent — Kafka Delivery Semantics:** https://docs.confluent.io/kafka/design/delivery-semantics.html
- **Debezium — PostgreSQL Connector:** https://debezium.io/documentation/reference/stable/connectors/postgresql.html
- **Apache Airflow — Documentation:** https://airflow.apache.org/docs/apache-airflow/stable/
- **dbt — Incremental Models:** https://docs.getdbt.com/docs/build/incremental-models
- **dbt — Data Tests:** https://docs.getdbt.com/docs/build/data-tests
- **dbt — Incremental Models and Snapshots:** https://docs.getdbt.com/best-practices/how-we-handle-cdc/2-choosing-incremental-or-snapshots

Related programme chapters:

- SE215-L10 — Working With Product, Design, and Analytics
- CS330-L01 — Relational Database Design
- CS340-L06 — Specialized Data Systems
- CS340-L07 — The Data Architecture Workshop
- CS430-L04 — Microservices, Events, and Service Boundaries
- CS430-L05 — Designing Reliable Business Workflows
- SE320-L03 — Queues, Workers, and Asynchronous Workflows
- SE325-L02 — Bulk Imports, Exports, and Background Data Operations

---

## Dense Cheatsheet — Interview Glance Card

```text
SE215-L09 — DATA ENGINEERING FOR APPLICATION DEVELOPERS

CORE MODEL
  Application truth -> Ingestion -> Transformation
  -> Analytical storage -> Reporting -> Reconciliation

OLTP
  Operational database workload
  Transactions, correctness, individual application operations
  Frequently small reads/writes, low latency

OLAP
  Historical analysis, aggregates, scanning, reporting
  Often large datasets and column-oriented execution

ETL
  Extract -> Transform -> Load

ELT
  Extract -> Load -> Transform
  Frequently used with analytical warehouses

DATA SOURCES
  Batch extraction
  Application domain events
  Change Data Capture (CDC)

CDC VS DOMAIN EVENT
  CDC = database row changed
  Domain event = business fact occurred
  Related but not interchangeable

KAFKA
  Producers, topics, partitions, consumers
  Ordering is partition-scoped
  Replays and duplicate processing require consideration
  Transport guarantees != business-level uniqueness

AIRFLOW
  Workflow orchestration and scheduling
  DAGs, task dependencies, retries, backfills
  Primarily finite batch-oriented workflows
  Green DAG != correct business report

DBT
  SQL-based analytical transformations
  Model dependencies, testing, documentation
  Incremental materializations and historical processing
  Uniqueness/not-null/relationship tests
  Data tests != complete business correctness

STORAGE
  Warehouse = analytical querying
  Lake = file/object-based data storage
  Lakehouse = managed analytical tables over lake-style storage
  Technologies overlap; choose for workload

ANALYTICAL MODELING
  Fact tables = measurable events/activities
  Dimension tables = descriptive context
  Grain = what one row represents
  Join multiplication can overcount totals
  Historical dimensions may preserve past attribute values

TIMESTAMPS
  Event time
  Ingestion time
  Processing time
  Different reporting questions use different clocks

DUPLICATES
  Delivery ID != event ID != business operation ID
  Deduplicate according to the model's grain
  Replayed message should not duplicate a business fact
  Distinct event IDs can still describe duplicate operations

LATE EVENTS
  Refund today may affect older booking
  Incremental processing must revisit relevant history
  Use appropriate watermarks, changes, merges, backfills
  Don't equate recent event time with recent business object

SCHEMA EVOLUTION
  Structure and meaning are both contracts
  Additive changes often easier than incompatible removals
  Changing field semantics can silently corrupt metrics
  Coordinate producers and downstream consumers

DATA QUALITY
  Uniqueness
  Non-null requirements
  Accepted values
  Relationships
  Freshness and completeness
  Business invariants
  Reconciliation against authoritative facts

DATA LINEAGE
  Trace reports -> models -> staging -> source records
  Important for debugging and change impact

REVENUE EXAMPLE
  100 captures x EUR 120 = EUR 12,000 gross captured
  4 full refunds x EUR 120 = EUR 480 refunds
  Net captured less refunds = EUR 11,520
  Four repeated captures may overstate gross by EUR 480
  Gross, net, booked value, recognized revenue are distinct

PRODUCTION INVESTIGATION
  1. Define the reported metric precisely
  2. Identify authoritative operational sources
  3. Define event/row grain
  4. Inspect joins and aggregation cardinality
  5. Check duplicates and missing events
  6. Examine event, ingestion, processing times
  7. Verify incremental updates and late-data handling
  8. Trace model lineage
  9. Reconcile actual business operations
 10. Backfill safely and add regression checks

MENTAL MODEL
  Source — who owns truth?
  Identity — what is one record?
  Movement — what can be lost, delayed, repeated?
  Transformation — what business meaning is applied?
  Verification — does it reconcile?

FINAL PRINCIPLE
  A successfully executed data pipeline can produce
  completely incorrect business information.
```
