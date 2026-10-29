---
id: CS340-L06
course: CS340
title: "Specialized Data Systems"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: CS340-L05
next: CS340-L07
---

<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE215-L09
Preserve the technical introduction to Redis, DynamoDB, Elasticsearch/OpenSearch,
analytical stores, and specialized data models.
When SE215-L09 exists, cross-reference it for data-engineering pipelines and
organizational responsibilities.
Do not repeat the Elasticsearch introduction in the SEO lecture. Search-engine
infrastructure and search-engine optimization are distinct subjects.
-->

# CS340 — Data Systems Beyond Relational Databases

## Lecture 06: Specialized Data Systems

*Why Redis, DynamoDB, Elasticsearch, and analytical databases exist, what their architectures make possible, and why adding another database can be both a brilliant engineering decision and a spectacular mistake.*

---

# Part I — Intuition

*The same product can need a correct booking write, a reused hotel summary, a known-key lookup, a relevance search, and a historical aggregate. Those are different questions — and often different systems.*

This pass builds one mental picture. Part II develops the same picture with the mechanisms underneath.

### The picture to carry in your head

Imagine you're responsible for the backend of a hotel-booking website.

A customer opens the application and searches for a quiet hotel near the center of Berlin.

They compare several properties, open one hotel's details, examine the available rooms, and complete a reservation.

Later, the marketing team wants to know which countries generated the most booking revenue last month.

These activities belong to the same product, but they ask very different questions of its data.

The customer wants to find something relevant.

The hotel-details page wants information that has probably been retrieved thousands of times before.

The booking operation needs to modify important business records correctly.

The application may need to record enormous numbers of independent user events.

And the marketing report needs to summarize millions of historical facts.

You could try handling everything with PostgreSQL.

For many applications, that would be an excellent starting point.

But as workloads grow, particular operations may become sufficiently demanding that another kind of data system offers meaningful advantages.

That's why Redis, DynamoDB, Elasticsearch, and ClickHouse exist.

**They aren't simply four competitors trying to replace PostgreSQL. They are systems designed around different ways of storing, finding, and processing information.**

---

### 1. Begin with the ordinary database

Let's start with the booking itself.

The customer selects a room for three nights.

The application must verify availability, create a reservation, and record the relevant payment state.

This operation involves important relationships and business constraints.

The booking belongs to a customer.

It reserves particular inventory.

It may have payments, refunds, and cancellation policies.

If the operation fails halfway through, the application must not invent a successful booking or lose track of committed money.

A relational database such as PostgreSQL is a strong default for this kind of operational work.

MongoDB can also be suitable for many operational applications, particularly where document-oriented modeling fits the data and access patterns.

The important point is that we need a **reliable home for authoritative business facts**.

That database is our starting point.

We introduce specialized systems only when there is a concrete reason.

### 2. Redis — Don't do the same work a thousand times

Now imagine the customer opening a popular hotel's details page.

Its name, address, description, and amenities haven't changed since this morning.

Yet ten thousand users may request the same information.

Without caching, the application could repeatedly ask its primary database for the same result.

Wouldn't it be convenient to keep a reusable copy somewhere fast?

That's a common reason to use Redis.

Redis is an in-memory data store that provides operations over structures such as strings, hashes, sets, counters, and sorted sets.

One of its most familiar uses is caching.

The application can ask Redis whether it already has a hotel summary.

If the value exists and is valid, return it.

Otherwise, retrieve the information from the authoritative source and populate the cache.

Redis can also support rate limiting, session-related state, counters, and other low-latency coordination patterns.

But there's an important distinction.

**Redis is not synonymous with cache, and a cached value is not automatically an authoritative business fact.**

If a hotel description disappears from Redis, perhaps the application can regenerate it.

If an authoritative booking disappears, the consequences are far more serious.

That difference determines how we think about persistence, eviction, failure recovery, and data ownership.

### 3. DynamoDB — Find a known item at enormous scale

Now imagine Mercury begins collecting customer activity.

Every customer performs actions: opening properties, viewing offers, saving preferences, and starting booking sessions.

The platform records millions of these events.

Suppose an important access pattern is straightforward:

"Retrieve the activity associated with customer 482, ordered by time."

You already know which customer's records you need.

You aren't searching through natural-language descriptions.

You're accessing data through a predictable key.

Amazon DynamoDB is a managed, distributed NoSQL database designed for workloads built around key-value and document access patterns.

You define keys that determine how data can be distributed and retrieved efficiently.

AWS manages much of the database infrastructure, including partitioning and operational scaling.

This can be extremely useful when a workload grows very large and its access patterns are well understood.

But DynamoDB doesn't make every possible database query automatically fast.

If you've organized data for efficient access by customer ID, that doesn't automatically make an arbitrary report joining many unrelated entities easy.

The way you design the keys matters enormously.

Here's the distinction worth remembering:

**Redis is often used to keep useful values and data structures immediately accessible. DynamoDB can serve as a durable primary data store for applications built around well-designed distributed key access.**

They overlap in certain capabilities, but they are not interchangeable.

And a conventional database might still be entirely sufficient for Mercury's activity workload.

### 4. Elasticsearch — Find relevant things, not just matching records

Return to the customer's original hotel search.

They enter:

"Quiet boutique hotel near the center of Berlin with a balcony."

This isn't a request for a record with a known ID.

The customer is expressing an intention.

Perhaps the hotel's description uses the word *peaceful* rather than *quiet*.

Perhaps it describes a *private terrace* rather than a *balcony*.

Perhaps several hotels match, but some are much more relevant than others.

An ordinary relational database can perform text search, filtering, and ranking. PostgreSQL, for example, has useful full-text search capabilities.

But sophisticated search workloads may justify a dedicated search engine.

Elasticsearch and OpenSearch are systems built around indexing and retrieving information using techniques such as text analysis, relevance scoring, filtering, and other search methods.

One of the central techniques is the *inverted index*.

Instead of merely finding a document by its identifier, the search engine maintains structures that help find documents associated with particular terms.

It can then rank results according to relevance.

This is a fundamentally different question from:

"Retrieve booking 482."

The booking query asks for a particular business fact.

The search query asks which documents are the best matches for an expression of user intent.

And a search engine's indexed representation may be updated asynchronously from the authoritative source.

**Elasticsearch is often a specialized way to find and rank information, not the place where you should automatically store the only authoritative copy of a customer's reservation.**

### 5. ClickHouse — Ask questions about millions of historical facts

Now imagine the marketing manager opens an analytics dashboard.

They want to know:

"Which countries generated the most booking revenue over the past ninety days, broken down by week, traffic source, and device type?"

The answer may involve millions or billions of event records.

The database must examine large amounts of historical information, group records, and calculate aggregates.

This is different from processing one customer's reservation.

A normal transactional query might retrieve or update a handful of related records.

An analytical query may scan enormous datasets to calculate a comparatively small result.

ClickHouse is a column-oriented analytical database designed for this second category of work.

To understand why that's useful, imagine a table containing fifty fields per event.

Our report needs only four of them.

A row-oriented storage design generally keeps the fields of a record together.

A column-oriented storage design keeps values belonging to the same column together.

That allows the analytical engine to read the relevant columns without treating every full record as the natural unit of storage.

At large scale, this can substantially reduce the amount of data processed.

ClickHouse also uses execution techniques intended to make aggregation over large datasets efficient.

But those strengths don't mean it should automatically replace a transactional booking database.

**A system optimized for examining a billion historical events is solving a different problem from one optimized for safely modifying a single reservation.**

### Visual anchor 1 — One product, different questions

The following picture summarizes the distinct workloads we've encountered.

```text
Hotel-booking platform
         |
         +-- Save a booking correctly
         |      PostgreSQL / operational DB
         |
         +-- Reuse a popular hotel summary
         |      Redis
         |
         +-- Retrieve activity by known key
         |      DynamoDB
         |
         +-- Find relevant hotels from text
         |      Elasticsearch / OpenSearch
         |
         +-- Aggregate enormous event histories
                ClickHouse
```

These are examples of possible responsibilities, not a requirement to deploy five different systems.

The same application may handle several of these workloads perfectly well using PostgreSQL alone.

The question is whether the specialized system solves an important problem worth the additional complexity.

### 6. Different kinds of fast

There's a subtle idea hiding behind these technologies.

They can all be described as fast databases.

But *fast at what?*

Redis might retrieve a known cached value extremely quickly.

DynamoDB might access a well-partitioned record using a known key at enormous scale.

Elasticsearch might find and rank relevant documents from a large catalogue.

ClickHouse might calculate a revenue report across billions of events.

Those are different operations.

A database can be extremely fast for one and comparatively inefficient for another.

That's why choosing a data system by a general benchmark or marketing claim is dangerous.

You must know the operation you're optimizing.

### Visual anchor 2 — Three ways to access information

This picture separates the questions that specialized systems are designed to answer.

```text
KNOWN ID OR KEY
"Give me customer 482's activity"
                |
                v
         Key-based retrieval


SEARCH EXPRESSION
"Quiet hotel near Berlin"
                |
                v
      Find and rank matches


ANALYTICAL QUESTION
"Revenue by country and week"
                |
                v
    Scan, group, and aggregate
```

These access patterns may overlap in real products.

The distinction is about what each system emphasizes, not which features it exclusively possesses.

### 7. The hidden cost: now your systems must agree

Imagine the customer changes their reservation.

The authoritative booking record updates successfully.

But the related search index still contains the earlier availability.

The analytics system hasn't yet received the modification event.

Redis still holds an old summary.

Each system may be behaving correctly according to its own update schedule.

Yet the information they expose is temporarily inconsistent.

Now the company needs to decide which value is authoritative, how changes propagate, how long derived representations may be stale, and what happens when synchronization fails.

This is the hidden cost of introducing specialized data systems.

You aren't merely adding another database.

You're adding another representation of information that must be updated, monitored, and sometimes rebuilt.

### Visual anchor 3 — One source, several useful copies

```text
     Authoritative booking database
                  |
          Booking changes
                  |
        +---------+---------+
        |         |         |
        v         v         v
      Redis     Search    Analytics
      cache     index     database

   Different access patterns
   Different freshness policies
   Different recovery procedures
```

The architecture should be able to answer what happens if any of these update paths fails.

Some derived copies can be discarded and regenerated.

Others may need durable processing, reconciliation, or controlled backfills.

The source-of-truth relationship should be clear before the system becomes complicated.

### 8. Don't collect databases like trophies

Imagine an engineer presents an architecture containing PostgreSQL, MongoDB, Redis, DynamoDB, Elasticsearch, and ClickHouse.

It might be an excellent architecture for a sufficiently large and demanding system.

It might also be an unnecessary operational nightmare.

Every additional system has configuration, security, backups, monitoring, resource limits, failure modes, costs, and specialist knowledge.

Every additional derived representation can create synchronization responsibilities.

A strong engineer doesn't reject specialized technology on principle.

But they shouldn't introduce it merely because it is popular.

Before adding another data system, ask:

**What important workload cannot our existing system handle adequately?**

**Why does this particular technology handle that workload better?**

**What new consistency and operational responsibilities will it create?**

Those questions are more valuable than memorizing vendor comparisons.

#### Three questions before the Deep Dive

1. A hotel-details page repeatedly retrieves the same description. Which technology might help, and would you necessarily make it the source of truth? **Redis could provide fast reusable access. The authoritative information can remain elsewhere.**
2. A customer searches for hotels using a natural-language description. Why might a dedicated search engine be useful? **Because finding and ranking relevant text matches is a different access pattern from retrieving a known record by its key.**
3. A company introduces ClickHouse for analytics. Does that mean every booking write should now go directly to ClickHouse? **No. The analytical workload can use a derived representation of authoritative operational data, with an appropriate ingestion and consistency contract.**

You now have the conceptual map.

The deep dive will explain the mechanisms underneath it: Redis data structures and persistence, DynamoDB partition keys, Elasticsearch indexing, ClickHouse's column-oriented execution, and the synchronization problems created when these systems coexist.

*The intuition pass ends here.*

---

# Part II — Deep Dive

# 1. Five Databases, Three of Them Unnecessary

It's Wednesday afternoon at our hotel-booking company, and the infrastructure team is preparing for an architecture review.

The platform has grown considerably. It handles hotel reservations, customer accounts, supplier integrations, payment processing, property search, and an increasing amount of analytical data.

The engineering team has proposed a modernization programme.

The new architecture diagram contains PostgreSQL, MongoDB, Redis, DynamoDB, Elasticsearch, and ClickHouse.

Six different data systems.

Each has its own box, arrows, and enthusiastic explanation.

PostgreSQL will store reservations and payments.

MongoDB will store hotel catalogues.

Redis will accelerate frequently accessed information.

DynamoDB will store customer activity.

Elasticsearch will provide sophisticated search.

ClickHouse will power analytical dashboards.

The diagram looks impressive.

The CTO asks one question.

"What happens when a customer changes their reservation?"

An engineer explains that PostgreSQL updates the reservation. Redis invalidates its cached copy. DynamoDB receives an activity event. Elasticsearch updates the relevant indexed information. ClickHouse eventually receives the analytical event.

The CTO asks another question.

"What happens when one of those updates fails?"

Nobody answers immediately.

Someone suggests adding retries.

Another engineer mentions a message queue.

A third proposes a synchronization service to coordinate all six databases.

The architecture diagram acquires three more boxes.

And suddenly, a company that once had a perfectly understandable backend is contemplating a small distributed-systems research programme.

The individual technology choices aren't necessarily bad.

Redis really can accelerate certain operations.

DynamoDB really can scale predictable access patterns with comparatively little infrastructure administration.

Elasticsearch really does provide sophisticated information retrieval.

And column-oriented analytical systems really can perform some enormous aggregations far more efficiently than ordinary transactional databases.

The problem is that **every specialized capability comes with a new operational and consistency boundary**.

A technology can be excellent at its intended job while still being a terrible architectural decision for the company adopting it.

Today we'll investigate those decisions.

Not by memorizing vendor feature lists, but by understanding the workloads, physical mechanisms, guarantees, and failure modes that make specialized systems valuable.

By the end, you should be able to examine a proposed database architecture and answer three questions.

What important work does this technology perform better than our existing system?

What new responsibilities will we inherit by introducing it?

And is the advantage large enough to justify those responsibilities?

Those are the questions that separate an architecture from a collection of logos.

---

# 2. Specialization Means Giving Something Up

Let's establish the fundamental principle.

A general-purpose database attempts to support many kinds of operations reasonably well.

A specialized system prioritizes certain workloads, often by narrowing its interface, organizing data differently, or sacrificing capabilities that aren't central to its purpose.

This is not a weakness.

It's how specialization works.

Imagine a database required to support arbitrary joins, large transactional updates, full-text relevance ranking, real-time counters, geographic proximity searches, and billion-row analytical scans.

Each capability places different demands on storage layout, indexing, concurrency control, and resource management.

A physical organization that makes one operation efficient may make another expensive.

In CS340-L02, we investigated storage engines and the distinction between B-tree-oriented access and LSM-style write organization.

In CS340-L04, we discovered that an index only helps when the query's access pattern matches its physical organization.

Specialized data systems take those ideas further.

They design entire products around particular families of operations.

## 2.1 The four dimensions of specialization

There are four useful dimensions to consider.

**Data representation:** The system may expose strings, hashes, documents, vectors, events, or columns as its natural abstractions.

**Access patterns:** It may optimize exact-key lookups, ordered ranges, relevance-ranked searches, or aggregations across enormous datasets.

**Operational guarantees:** It may make different choices about transactions, durability, replication, freshness, and scaling.

**Physical execution:** It may use memory-oriented data structures, partitioned key access, inverted indexes, immutable segments, or columnar storage.

These dimensions overlap, but they aren't interchangeable.

Two systems can store similar-looking JSON documents while using fundamentally different indexing and durability mechanisms.

Two systems can support SQL while having radically different storage layouts.

And a highly efficient data structure does not automatically make the entire distributed system reliable.

We'll examine these distinctions through four technologies.

---

# 3. Redis: The Art of Keeping Useful Information Close

Let's begin with the easiest specialization to appreciate.

Our application frequently retrieves hotel summaries.

A popular property might be viewed thousands of times per hour, even though its name, address, and photographs rarely change.

Every request could query PostgreSQL or MongoDB.

But the result is often identical.

Why repeatedly perform the same work?

A cache stores a reusable representation closer to where it is needed.

Redis is commonly used for this purpose.

It primarily operates on in-memory data structures, making many ordinary operations extremely fast.

But calling Redis merely a cache misses much of its design.

Redis is a **data-structure server**.

It exposes useful operations directly over different kinds of values.

## 3.1 Strings, hashes, sets, and sorted sets

Imagine storing a hotel summary under a key derived from the hotel identifier.

The application requests the key and receives the cached representation.

This is the simplest kind of Redis usage.

Now imagine storing a customer's session attributes.

A Redis hash can represent a collection of related fields.

Or imagine tracking a set of unique users currently participating in a promotion.

A Redis set supports operations such as membership testing and set intersection.

Now suppose we need to rank hotels according to a popularity score.

A **sorted set** associates each member with a score and maintains an ordering useful for rank or score-range queries.

Instead of retrieving every hotel and sorting them in application code, the system can use operations designed around the ordered data structure.

The important insight is that Redis doesn't merely store arbitrary values quickly.

It exposes operations that match particular computational patterns.

That can remove work from the application.

## 3.2 The rate limiter

Suppose our API allows a customer to make one hundred requests during a rolling minute.

An implementation using an ordinary database might record every request and repeatedly count recent entries.

Redis offers several possible approaches.

A fixed-window limiter might use an atomic counter associated with a time interval.

A sliding-window implementation might use a sorted set whose scores represent request timestamps.

On each request, the system removes entries outside the active window, counts the remaining entries, and decides whether another request is permitted.

But there's a subtle concurrency problem.

If several application instances independently read the count and then update it, two requests might both observe that one slot remains.

Both could proceed.

Redis provides mechanisms such as Lua scripts or Redis Functions to execute related operations atomically within the relevant server execution context.

That allows us to combine the admission decision and state modification rather than performing an unsafe application-level check-then-write sequence.

However, this local atomicity does not automatically establish identical guarantees across every possible failover or distributed deployment.

A rate limiter's correctness still depends on its topology and failure requirements.

And a business-critical reservation lock should not be casually treated as equivalent to a short-lived API rate-limit counter.

The same tool can support different mechanisms.

The required guarantees determine whether the design is appropriate.

---

# 4. Redis Expiration Is Not Redis Eviction

Here's a distinction that repeatedly causes confusion.

Imagine storing a hotel summary with a time-to-live of five minutes.

After the configured lifetime, the key is logically expired and should no longer be treated as a valid cached value.

Redis manages expiration through mechanisms that identify expired keys during access and through background work.

But now imagine that memory becomes scarce before the five minutes have elapsed.

Should Redis preserve every cached entry until its expiration time?

Not necessarily.

Redis supports configurable **eviction policies**.

These policies determine which keys may be removed when configured memory limits are exceeded.

Expiration and eviction solve different problems.

## 4.1 Expiration expresses useful lifetime

A TTL answers a question about time.

"How long should this cached value remain eligible for reuse?"

For hotel search results, we might tolerate a short freshness window.

For a temporary authentication challenge, expiration may be part of the application's validity model.

But even then, the application should not confuse physical deletion timing with authoritative business time.

A key's expiration can make it unavailable through normal Redis access without requiring that the key have been physically removed at that exact instant.

## 4.2 Eviction responds to memory pressure

An eviction policy answers a different question.

"When memory pressure requires removing data, which eligible keys should go?"

For a disposable cache, an approximation of least-recently-used or least-frequently-used eviction can be sensible.

But imagine storing critical session state alongside disposable hotel thumbnails in the same Redis instance.

If an all-keys eviction policy is configured, the system might discard session information to make space for less important cached content.

Suddenly customers are logged out because the cache filled up.

The database is behaving according to configuration.

The architecture failed to distinguish two data classes with different importance.

A strong design may separate disposable caches from state with stronger retention requirements.

It may also configure memory limits, eviction policies, and persistence differently for each workload.

**Not all information stored in Redis should be treated as equally disposable.**

---

# 5. Redis Persistence: Fast Doesn't Mean Volatile by Definition

You may have heard that Redis stores everything in RAM, so it cannot be used for durable data.

That is too simplistic.

Redis supports persistence mechanisms.

Two particularly important approaches are RDB snapshots and the Append Only File, or AOF.

## 5.1 RDB snapshots

An RDB snapshot records a point-in-time representation of the dataset.

This can be convenient for backups and recovery.

But if snapshots happen periodically, writes performed after the most recent snapshot may be lost during a sudden failure.

The potential loss window depends on the configuration and circumstances.

For a reconstructable cache, this may be acceptable.

For authoritative financial information, it probably isn't.

## 5.2 Append-only logging

AOF records write operations so Redis can reconstruct data after a restart.

Its durability characteristics depend on the synchronization policy.

For example, synchronizing the log approximately every second offers different crash-loss characteristics from synchronizing each relevant batch more aggressively.

AOF can also be rewritten to reduce unnecessary historical operations.

This should sound familiar after CS340-L02.

The same fundamental tension appears repeatedly.

We want fast writes, but persistent recovery requires durable information somewhere.

The storage engine must decide when and how to perform that work.

## 5.3 Redis as a primary database

Can Redis store authoritative application data?

Yes, in architectures designed around its data model, persistence, replication, and operational guarantees.

But **possible** doesn't mean **appropriate by default**.

For a booking platform, PostgreSQL may offer a more natural combination of relational constraints, transactions, and long-lived business records.

Redis might be excellent for ephemeral coordination state, caching, and specialized low-latency operations.

The important question is what happens when Redis fails.

Can the information be regenerated?

If it disappears, does the application become slower, or does the business lose money?

Those are very different failure models.

## 5.4 The cache outage that overloaded PostgreSQL

Let's return to our company.

A Redis instance becomes unavailable.

The application uses cache-aside logic: attempt the cache first, and on a miss, query PostgreSQL.

That sounds resilient.

But imagine hundreds of application instances simultaneously discovering that the cache is unavailable.

Every request falls through to PostgreSQL.

The database suddenly receives ten times its normal read workload.

Its connection pool saturates.

Latency rises.

The entire booking platform begins failing.

The cache was introduced as an optimization.

Its disappearance caused a cascading outage.

A resilient design needs bounded fallback concurrency, reasonable timeout policies, and protection against synchronized cache misses.

Techniques may include request coalescing, controlled stale-data reuse where safe, TTL jitter, and load shedding.

But even those choices depend on the business meaning of the cached information.

A stale public hotel description may be tolerable.

Stale authoritative room availability must not be used to commit a reservation.

**A cache is useful only if the system remains correct when its contents are missing, stale, or unavailable.**

---

# 6. Redis Streams: When a Data Structure Starts Looking Like Infrastructure

Before leaving Redis, let's investigate one more capability.

Redis supports **Streams**, a data structure resembling an append-oriented sequence of entries.

Applications can append events, read them, and use consumer groups to coordinate processing.

This makes Streams useful for certain event-processing and work-distribution problems.

But a stream is not automatically a complete workflow engine.

Suppose a worker receives an event instructing it to send a booking confirmation email.

It sends the email.

Then it crashes before acknowledging the event.

The event may later be delivered for processing again.

If the worker blindly resends the email, the customer receives duplicates.

This is the familiar at-least-once delivery problem.

Redis Streams provide mechanisms for tracking delivered and pending entries, but application correctness still requires appropriate acknowledgment, retry, and idempotency behavior.

And if the queue represents work that absolutely must survive infrastructure failures, persistence and replication configuration become central.

The larger lesson is useful.

A database can provide queue-like operations.

That doesn't mean every queue should become a database, or every database stream should replace a dedicated messaging system.

Choose the operational abstraction according to the required delivery, ordering, retention, and recovery guarantees.

---

# 7. DynamoDB: Design the Question Before Storing the Answer

Now let's examine a very different system.

Our company operates a serverless service collecting user activity.

The workload is large but conceptually straightforward.

The application records events associated with customers and retrieves recent events for a particular customer.

It rarely needs arbitrary joins.

It knows its dominant access patterns in advance.

This is the kind of workload where DynamoDB may be attractive.

DynamoDB is a managed NoSQL database whose design emphasizes partitioned storage and predictable key-oriented access.

AWS manages substantial portions of the infrastructure lifecycle.

But DynamoDB rewards careful data modeling.

## 7.1 The primary key

Every DynamoDB item has a primary key.

A simple primary key consists of a partition key.

A composite primary key consists of a partition key and a sort key.

Imagine storing customer events.

The partition key might identify the customer.

The sort key might contain an event timestamp combined with a unique identifier.

This lets the application retrieve a customer's events within a time range using a query over the relevant key structure.

The partition key helps determine where data is placed.

The sort key organizes items sharing that partition-key value.

That's an important contrast with starting from a normalized relational schema and expecting arbitrary query combinations to emerge later.

In DynamoDB, **access-pattern design is a first-class part of data modeling**.

## 7.2 Query versus Scan

Suppose we want the latest events for customer 4812.

If the table is designed around that customer identifier, an appropriate Query operation can efficiently retrieve the relevant key range.

Now imagine asking for all events from customers in Lithuania whose browser language was French and whose purchase value exceeded 200 euros.

If the required access path was never designed, the application may need a broad scan or another index.

A Scan examines items across a table or index and can become expensive at scale.

A filter expression doesn't magically make that scan equivalent to a targeted primary-key query.

It can reduce the items returned while still consuming read capacity for examined data.

That's a subtle but important cost distinction.

An operation may return very little data while reading a great deal.

We've encountered the same principle with MongoDB query plans.

## 7.3 Secondary indexes

DynamoDB supports secondary indexes that provide additional access paths.

A **Global Secondary Index**, or GSI, can use a different partition and sort key from the base table.

This lets an application support additional query patterns.

A **Local Secondary Index**, or LSI, retains the base table's partition key while using an alternative sort key, subject to its own constraints.

But adding indexes introduces costs.

Indexed data consumes storage.

Writes may create work in relevant secondary indexes.

And GSI queries have different consistency characteristics from strongly consistent base-table reads.

An index isn't merely a declaration that a field should become faster.

It's another maintained representation of information.

---

# 8. DynamoDB Hot Partitions: On-Demand Doesn't Mean Unlimited

Our event-ingestion service initially uses a partition key derived from the current calendar date.

All events created on Tuesday receive the same partition-key value.

At low traffic, it works.

Then a marketing campaign causes an enormous burst of activity.

The table begins throttling writes.

The infrastructure team is confused.

The table uses on-demand capacity.

Shouldn't AWS automatically scale it?

The problem is that on-demand scaling doesn't abolish physical partition constraints.

DynamoDB distributes data and request processing across partitions, but a poor partition-key distribution can concentrate too much activity on a small part of the system.

## 8.1 The partition-key mistake

If every new event uses the same partition key, a large proportion of incoming traffic targets the same logical key space.

DynamoDB has adaptive-capacity mechanisms that help handle uneven workloads, but they cannot make every pathological key distribution scale without constraint.

A very hot individual item or an unsuitable partition design can still encounter throughput limits.

The application must choose keys that distribute its workload effectively.

This is the same lesson we encountered with MongoDB sharding, expressed through a different architecture.

## 8.2 Capacity modes

DynamoDB supports on-demand and provisioned capacity modes.

On-demand mode is attractive when workloads vary or the team wants AWS to manage capacity automatically within service limits and scaling behavior.

Billing depends substantially on actual request usage and other consumed resources.

Provisioned mode lets teams specify capacity and use mechanisms such as auto scaling.

It may be economically attractive for predictable, sustained workloads, depending on usage and pricing.

Neither mode rescues an inappropriate data model.

And neither removes the need to understand item sizes, access patterns, hot keys, and throughput limits.

The difference is how capacity is managed and charged.

The physical distribution problem remains.

---

# 9. DynamoDB Consistency: One Database, Several Read Guarantees

Now imagine writing a customer event.

Immediately afterward, the application queries it through a secondary access path.

The item doesn't appear.

Did DynamoDB lose the write?

Not necessarily.

DynamoDB supports eventually consistent and strongly consistent reads within documented boundaries.

Ordinary eventually consistent reads may temporarily return an older state.

Strongly consistent reads are supported for appropriate base-table and local-secondary-index operations.

But **Global Secondary Indexes do not support strongly consistent reads**.

Their indexed state is maintained asynchronously.

So an application that requires immediate visibility through a GSI cannot obtain that guarantee merely by requesting strong consistency on the GSI.

It may need a different data model or an alternate read path.

## 9.1 Transactions and conditional writes

DynamoDB also supports conditional writes and transactional APIs.

This matters because older stereotypes often describe key-value databases as incapable of enforcing meaningful correctness.

Imagine reserving a unique business operation ID.

A conditional PutItem operation can require that an item with the relevant key not already exist.

That condition can make the creation atomic within the documented operation semantics.

Transactional APIs can coordinate several operations where necessary, subject to their constraints.

This doesn't make DynamoDB identical to PostgreSQL.

It means we should evaluate actual guarantees instead of classifying entire products as consistent or inconsistent.

## 9.2 Multi-Region replication

DynamoDB Global Tables support replication across AWS Regions.

Modern Global Tables offer different consistency modes.

The ordinary multi-Region eventual-consistency mode replicates changes asynchronously and has defined conflict-resolution behavior.

Multi-Region strong consistency is also available in supported configurations, with different coordination and deployment constraints.

This is a useful reminder that database products evolve.

The statement "DynamoDB Global Tables can never support strong cross-Region consistency" is no longer universally correct.

But stronger coordination has costs and restrictions.

The appropriate mode depends on business requirements, geography, latency, and failure tolerance.

The engineering question remains:

**What must the application observe after a successful write, and which configuration actually guarantees it?**

---

# 10. Elasticsearch and OpenSearch: Search Is Its Own Kind of Computation

Our product team wants customers to search for hotels using ordinary language.

A customer types:

"Quiet apartment near old town with private parking."

The catalogue contains millions of hotel descriptions.

Some say "historic center."

Others say "city centre."

One says "peaceful property with underground garage."

We want results that are relevant, not merely exact text matches.

This is where Elasticsearch and OpenSearch become attractive.

These systems are built around search and indexing architectures derived from Apache Lucene, although the two products have their own development histories and features.

Their defining strength is not simply storing JSON documents.

It's organizing information so complex retrieval and ranking can be performed efficiently.

## 10.1 The inverted index

Consider a book.

If you know the page number, finding the content on that page is easy.

But what if you want every page containing the word "reservation"?

You need an index mapping the word to the pages where it appears.

An **inverted index** applies this principle to document collections.

Instead of storing only documents and repeatedly scanning their text, the search engine maintains mappings from terms to documents containing those terms.

Real systems also maintain information that supports relevance scoring, positional queries, and other retrieval operations.

A search analyzer can tokenize text, normalize terms, and apply language-aware transformations.

Different fields can use different analyzers.

That means search behavior depends not only on the data but also on how the data was indexed.

## 10.2 Relevance is not a boolean

A relational query often asks whether a record satisfies a predicate.

Search asks another question.

"Which matching documents are most useful for this query?"

Relevance scoring may consider term frequencies, document frequencies, document length, and other configured signals.

BM25 is a widely used probabilistic relevance-scoring approach.

A practical search application may combine textual relevance with business information such as availability, geography, rating, or popularity.

But we should be careful.

A highly relevant hotel isn't necessarily bookable.

And a search result isn't automatically an authoritative description of the current business state.

Search infrastructure answers discovery questions.

The transactional system should enforce transactional facts.

---

# 11. Near Real-Time Search: Indexed Does Not Mean Immediately Searchable

Let's return to our architecture.

A hotel changes its description.

The application updates the authoritative catalogue.

The indexing pipeline sends the new representation to Elasticsearch.

The indexing operation reports success.

Immediately afterward, the product manager searches for the new description.

It doesn't appear.

They conclude the indexing request failed.

But Elasticsearch has a mechanism called **refresh**.

New indexing operations become visible to ordinary search when the relevant refreshed search structures expose those changes.

The system is therefore commonly described as **near real-time**, not universally immediate-real-time search.

## 11.1 Indexing, refreshing, and durable commits are different events

Lucene organizes searchable information into segments.

Search engines can create new segments and make them available to searches through a refresh operation.

That is different from an ordinary application database's notion of one transaction becoming immediately visible to all reads.

It is also different from forcing every searchable change to be committed to durable storage at the exact moment the application receives an indexing acknowledgment.

The underlying engine uses its own logging, refresh, and persistence mechanisms.

The details depend on deployment and configuration.

For the application developer, the important distinction is simple.

**A successful indexing response does not universally guarantee that an immediately following search will see the new document.**

Elasticsearch offers mechanisms for waiting for refresh visibility when a workflow requires it.

But forcing immediate refreshes everywhere can damage indexing throughput and resource efficiency.

The right choice depends on the product.

A customer searching for hotel descriptions may tolerate a short delay.

An administrative workflow that needs to verify a just-submitted change may use an authoritative read path or an appropriate refresh-aware mechanism.

## 11.2 Updates can be physically expensive

Lucene segments are largely immutable.

When documents change, the search engine doesn't necessarily rewrite one tiny field in place.

It may represent the updated document through new index structures and mark older indexed representations as obsolete.

Background segment merging eventually consolidates data and reclaims obsolete storage.

This resembles some of the trade-offs we encountered in LSM-oriented storage systems.

Search indexes are optimized for retrieval.

Frequent small updates can create additional indexing and merge work.

That's one reason Elasticsearch isn't automatically the ideal primary database for a highly transactional booking system.

Its strengths lie elsewhere.

---

# 12. Vector Search Doesn't Replace Search Engineering

Modern search systems increasingly support vector embeddings.

A hotel description can be transformed into a numerical vector representing aspects of its meaning.

A query can also be represented as a vector.

A vector search engine retrieves items whose vectors are close according to a selected similarity measure.

This can help match queries and documents that use different words but express related ideas.

For example, "historic city centre" may be semantically relevant to a query mentioning "old town."

But vector search introduces its own trade-offs.

It may use approximate nearest-neighbor algorithms such as HNSW.

Approximate search can improve performance by avoiding exhaustive comparison against every stored vector.

The trade-off is that the nearest items are not always found with perfect recall.

And semantic similarity is not the same as business correctness.

A semantically relevant hotel might be in the wrong city or exceed the customer's budget.

Consequently, modern retrieval systems often combine exact filters, keyword ranking, vector similarity, and reranking.

This is called **hybrid search**.

The important principle is not that vector databases are a new universal category that should replace every search engine.

It's that different retrieval methods answer different aspects of the information need.

Sometimes PostgreSQL with an appropriate extension is sufficient.

Sometimes a dedicated search service is justified.

The correct architecture depends on retrieval quality, latency, scale, and operational complexity.

---

# 13. Analytical Databases: Why Reading Columns Can Be More Useful Than Reading Rows

The analytics team now enters the architecture meeting.

They want to examine hundreds of millions of customer events.

The questions sound simple.

What percentage of hotel searches become bookings?

Which destinations produce the highest revenue?

How does conversion differ by device type and country?

But answering these questions may involve scanning enormous quantities of historical data.

This is where systems such as ClickHouse become interesting.

ClickHouse is designed for analytical workloads, with column-oriented storage and execution strategies that exploit large scans, compression, and aggregation.

## 13.1 Why columns change the economics

Imagine an event record containing thirty fields.

A query calculating conversion rates might need only event type, country, device type, and timestamp.

In a row-oriented physical layout, values belonging to one record tend to be stored together.

That can be convenient when retrieving or updating complete individual records.

A column-oriented system stores values organized by column or column-oriented blocks.

The query can read relevant columns without necessarily retrieving every other field for every event.

This can dramatically reduce data movement for wide analytical scans.

Columnar data can also compress efficiently because values within one column often share types and patterns.

For example, a country column may contain repeated short codes.

Compression can exploit that repetition.

## 13.2 Vectorized execution

Modern analytical engines may process batches of values rather than repeatedly interpreting one row at a time.

This is commonly called **vectorized execution**.

Operations over batches can improve CPU efficiency through reduced interpretation overhead, cache-friendly processing, and suitable SIMD techniques.

The system can apply filters and aggregations to large groups of values efficiently.

The combined effect of columnar layout, compression, data skipping, and vectorized execution can be enormous.

But once again, specialization has a price.

A layout optimized for scanning selected columns across millions of records may be less convenient for frequently updating one complete row.

## 13.3 ClickHouse's MergeTree family

ClickHouse commonly uses MergeTree-family table engines.

These organize data into parts and use sorting keys, sparse indexes, and background merging.

That should sound familiar after CS340-L02.

A MergeTree table's ordering key influences how efficiently queries can skip irrelevant data.

A sparse primary index helps identify relevant granules rather than maintaining one index entry for every row.

Background merges reorganize stored parts.

This provides powerful analytical performance.

But it also means that physical ordering and background maintenance matter.

A poorly chosen ordering key can force queries to read far more data than necessary.

And extremely frequent tiny inserts or updates may create operational problems compared with well-batched analytical ingestion.

The design rewards workloads that fit its architecture.

---

# 14. Time-Series Databases: When Time Is More Than Another Column

Now consider telemetry.

Our application produces CPU measurements, API latency samples, request counters, event-loop delay measurements, and service-health information.

Every record has a timestamp.

New measurements arrive continuously.

Users frequently ask for recent values, trends over time, and aggregated windows.

This is a **time-series workload**.

Specialized time-series systems exploit those characteristics.

## 14.1 Append-heavy data

Many time-series workloads primarily append new observations.

Historical measurements are usually queried rather than modified repeatedly.

That makes append-oriented ingestion and time-based partitioning attractive.

Older data may be compressed, downsampled, or removed according to retention policies.

For example, we might retain high-resolution measurements for one week, minute-level aggregates for several months, and daily summaries for longer historical analysis.

The appropriate policy depends on business and operational requirements.

## 14.2 Time windows and aggregates

Imagine calculating the ninety-fifth percentile of API latency for each five-minute interval.

The system must group observations into time windows and compute a statistical summary.

A time-series database may provide efficient mechanisms for time bucketing, retention, and continuous aggregation.

But don't confuse all metrics with interchangeable data.

A counter records an accumulated quantity.

A gauge represents a value at a point in time.

A histogram represents an observed distribution.

These types require different aggregation semantics.

For example, simply averaging percentile values from several independent groups generally doesn't produce the correct percentile for their combined observations.

The system's analytical model must preserve enough information for the desired calculation.

## 14.3 High cardinality: The hidden bill

Suppose we label every HTTP latency measurement with a service name and endpoint.

That may be useful.

Now imagine also labeling each measurement with a unique request ID and customer ID.

The number of distinct label combinations can explode.

Many time-series and metrics systems index or otherwise maintain series according to those label combinations.

Excessive cardinality can create substantial memory, indexing, and storage costs.

A metric system intended to summarize millions of operations may become overloaded because the application created millions of essentially unique series.

Request-level identifiers are often better suited to traces or logs than to high-cardinality metric labels.

The deeper point is familiar.

**The shape of the data determines the physical work required to store and query it.**

Time-series specialization doesn't eliminate data-modeling decisions.

It makes certain decisions especially important.

---

# 15. The Real Problem: Who Owns the Truth?

We've now encountered Redis, DynamoDB, Elasticsearch, ClickHouse, and time-series systems.

Each can be excellent.

But let's return to our original architecture.

The hotel catalogue lives in MongoDB.

Search uses Elasticsearch.

The frontend uses Redis-backed caching.

Analytics uses ClickHouse.

Now a hotel changes its cancellation policy.

Which system owns the authoritative value?

The answer should be unambiguous.

Perhaps MongoDB owns the catalogue record.

Then Elasticsearch and Redis contain derived representations.

ClickHouse may eventually receive an event describing the change.

Those are different responsibilities.

## 15.1 The source of truth

For each business fact, one system or well-defined authoritative workflow must determine its accepted state.

A search index should not independently invent hotel pricing.

A cache should not become the authority on whether a room is available.

An analytical event stream should not silently override a committed financial record.

Multiple copies are fine.

Multiple uncoordinated authorities are dangerous.

The architecture must define how derived copies are produced and repaired.

## 15.2 The dual-write problem

Suppose our application performs two operations.

First, it updates the hotel's record in MongoDB.

Second, it sends the new representation to Elasticsearch.

What happens if the application crashes between those operations?

MongoDB contains the new policy.

Elasticsearch contains the old one.

The two writes cannot automatically be committed atomically just because the application executes them sequentially.

Reversing the order doesn't solve the problem.

If Elasticsearch updates first and MongoDB fails, search may advertise a change that never became authoritative.

This is the **dual-write problem**.

The order changes which inconsistency can occur.

It doesn't eliminate the failure window.

## 15.3 Change data capture

One approach is **change data capture**, or CDC.

Instead of asking every application path to independently synchronize every database, a process observes an authoritative system's committed changes and publishes them to downstream consumers.

For example, MongoDB change streams can expose supported data changes.

A downstream indexing worker can consume those changes and update Elasticsearch.

This reduces the amount of synchronization logic embedded in ordinary request handlers.

But CDC isn't magical.

The pipeline must handle interruptions, resumption, retries, ordering, and consumer failures.

It also needs a strategy for initial backfills.

If the indexer starts today but the database contains ten years of records, simply listening for new changes won't populate the historical index.

A correct design combines initial state synchronization with a reliable transition to ongoing changes.

---

# 16. The Transactional Outbox and the Problem of Duplicate Delivery

For some workflows, we need stronger coupling between a business change and a published event.

A common design is the **transactional outbox**.

Suppose PostgreSQL owns reservations.

In one database transaction, the application creates a reservation and inserts an outbox record describing the event.

Both changes commit together.

A separate publisher later reads the outbox and delivers events to downstream systems.

This solves an important failure window.

We no longer have a successfully committed reservation with no durable record of the obligation to publish its event.

But another problem remains.

## 16.1 The publisher can crash after sending

Imagine the publisher sends a reservation-created event to the analytics pipeline.

The downstream system processes it successfully.

Before the publisher records that delivery as completed, the publisher crashes.

When it restarts, it finds the event still pending.

It sends the event again.

Now the consumer receives a duplicate.

The outbox didn't fail.

It preserved the event so it wouldn't be silently lost.

But it doesn't universally provide exactly-once business effects across independent systems.

The downstream consumer needs an idempotency strategy.

For example, each event can carry a stable event ID.

The consumer can record which events it has processed, using suitable atomicity or versioning for its own data system.

If the same event arrives again, the consumer should avoid repeating an inappropriate side effect.

The exact implementation depends on the destination's guarantees.

## 16.2 Ordering is another problem

Suppose a hotel changes its name twice.

The first event says the name became "Old Town Residence."

The second says it became "Grand Old Town Residence."

If the events are processed out of order, the search index could end up with the older name.

Idempotency alone doesn't solve that.

The consumer may need version numbers, sequence information, or another ordering mechanism.

One practical approach is to include the authoritative record version with each update.

The derived store applies the change only when it represents an appropriate newer version.

But there are complications involving deletion, retries, partitioned processing, and concurrent updates.

The important idea is that **duplicate protection and ordering protection solve different problems**.

## 16.3 Reconciliation is not optional

Even carefully designed event pipelines can encounter bugs or operational failures.

A consumer might be misconfigured.

An index mapping could reject some documents.

A change-stream resume token might no longer be usable after a sufficiently long outage.

A deployment might accidentally discard an important field.

Therefore, a serious architecture includes reconciliation.

The system needs a way to compare derived representations with authoritative data and repair disagreements.

For search, that might involve rebuilding an index from a snapshot and replaying subsequent changes.

For analytics, it might involve reprocessing an event range.

For caches, invalidation and repopulation may be sufficient.

The correct repair process depends on what the derived system stores.

**A derived database is reliable only when we understand how to rebuild it.**

---

# 17. The Operational Tax: Every New System Wants Its Own On-Call Engineer

Now let's revisit the six-database architecture.

Suppose all the proposed products are technically appropriate.

There's still a cost.

Each system needs monitoring, access controls, backups or another recovery strategy, capacity planning, upgrades, configuration management, and incident response.

The team must understand different failure modes.

Redis may suffer from unexpected evictions or memory pressure.

DynamoDB may throttle a hot key or incur surprising request charges.

Elasticsearch may experience shard imbalance, indexing pressure, or delayed search visibility.

ClickHouse may accumulate too many small parts or struggle with an unsuitable ordering key.

A CDC pipeline may fall behind while every source database remains perfectly healthy.

And when an incident involves several systems, the team must determine which one owns the problem.

This is the **operational tax of specialization**.

## 17.1 Cost is more than the database invoice

Imagine Elasticsearch costs relatively little to operate at the expected scale.

That still doesn't mean introducing it is cheap.

Developers must maintain index mappings.

Deployments must account for schema and index evolution.

Someone must manage backfills and reindexing.

Monitoring must detect stale or missing indexed documents.

The system must handle search availability independently from reservation availability.

And engineers must understand enough of Lucene's indexing and merge behavior to diagnose production problems.

Those costs may be entirely justified.

But they belong in the decision.

## 17.2 Failure domains multiply

A simple architecture might have one primary database dependency.

A more specialized architecture has several.

Even if each system is individually reliable, the application can experience more combinations of partial failure.

Perhaps bookings remain operational while search is unavailable.

Perhaps analytics is delayed but customers can still pay.

Perhaps Redis disappears and threatens to overload PostgreSQL.

A well-designed system defines which capabilities can degrade independently.

It doesn't require every supporting data store to be healthy before customers can complete the most important business operations.

This is the principle of **failure containment**.

Specialization becomes more attractive when the architecture can isolate the resulting failures.

If one missing analytics database can bring down the payment API, the company has paid for specialization without achieving sensible separation.

---

# 18. The Architecture Review: What Should We Actually Keep?

We now return to the CTO's architecture meeting.

Six databases have been proposed.

The team needs a decision.

Let's evaluate each requirement rather than voting on products.

## 18.1 Reservations and payments

These operations require strong transactional correctness and durable business records.

PostgreSQL already provides a suitable foundation.

We keep it as the authoritative system for those workflows.

We do not move financial records to Redis merely because Redis is fast.

Nor do we distribute them across several databases without a compelling consistency design.

## 18.2 Hotel catalogue

Hotel descriptions are flexible and hierarchical.

MongoDB might be an appropriate system of record if the company already has a well-designed document-oriented catalogue and a team comfortable operating it.

But if PostgreSQL with JSONB adequately meets the requirements, a separate MongoDB deployment may provide insufficient benefit.

The decision depends on existing architecture and actual workload.

For our established platform, we'll assume MongoDB is already operating successfully and retain it for the catalogue.

That is a pragmatic decision, not a claim that MongoDB is always the best catalogue database.

## 18.3 Caching and sessions

Redis can serve useful roles involving low-latency key access, counters, sets, and other data structures.

We keep it where those capabilities demonstrably help.

But we separate disposable cached data from state requiring stronger retention guarantees.

We also design bounded fallback behavior so a Redis outage doesn't overwhelm the authoritative database.

## 18.4 Hotel search

The product requires sophisticated relevance ranking, multilingual search, and possibly hybrid keyword/vector retrieval.

These are credible reasons to consider a specialized search engine.

We approve a controlled Elasticsearch or OpenSearch integration, but treat the index as derived data.

The catalogue database remains authoritative.

Search indexing must support replay, backfill, and reconciliation.

And booking correctness never depends on a search result being perfectly fresh.

## 18.5 Customer activity

The original proposal uses DynamoDB for activity events.

But does the workload require DynamoDB specifically?

Perhaps not.

If events are primarily consumed by analytics, we might send them through a suitable durable ingestion pipeline toward the analytical system instead of introducing another operational database.

DynamoDB becomes more compelling if the product requires large-scale, predictable key-based access to customer activity as an operational feature.

For now, we reject the additional DynamoDB system.

Not because DynamoDB is bad.

Because this workload hasn't earned it.

## 18.6 Analytics

The analytics team performs large aggregations across high-volume event data.

Those queries interfere with operational workloads.

A separate column-oriented analytical system is a credible candidate.

We begin with a bounded proof of value: representative queries, expected data volume, freshness requirements, costs, and recovery design.

If ClickHouse materially improves the workload while keeping operational complexity acceptable, it earns its place.

Otherwise, simpler reporting infrastructure may remain sufficient.

## 18.7 The final architecture

Our platform now has clear responsibilities.

PostgreSQL owns reservations and payments.

MongoDB owns the flexible catalogue, assuming its existing operational role remains justified.

Redis accelerates specific operations and maintains selected short-lived state.

A search system provides specialized retrieval over derived catalogue data.

A column-oriented analytical system may process historical events.

DynamoDB isn't introduced without a concrete operational access pattern.

This may still sound like several systems.

But the number of systems is no longer the starting point.

Each has a defined responsibility, a reason to exist, and a failure model.

And if the company were smaller, we might consolidate further.

The goal is not minimal technology count at any cost.

It's **the least complexity necessary to satisfy real requirements**.

---

# 19. The Oral Examination

Before reading the solutions, answer these questions aloud. Explain the mechanism and the operational consequences, not merely the product feature.

## Challenge 1 — The disposable cache

A team stores cached hotel summaries and customer sessions in one Redis instance with an all-keys eviction policy.

Memory pressure rises, and users begin losing sessions.

What happened? How would you redesign the architecture?

## Challenge 2 — The disappearing Redis write

A Redis instance acknowledges an update.

The machine crashes shortly afterward, and the update is missing after recovery.

Does this prove Redis is broken?

Which persistence and replication details would you inspect?

## Challenge 3 — The DynamoDB hotspot

An on-demand DynamoDB table receives enormous traffic.

All new events use today's date as the partition key.

The table begins throttling.

Why doesn't on-demand capacity automatically solve this?

How would you reconsider the data model?

## Challenge 4 — The missing search document

Elasticsearch acknowledges an indexing operation.

An immediately following search doesn't return the document.

What mechanism explains this?

Would forcing a refresh after every write be an ideal universal solution?

## Challenge 5 — The wrong kind of search

Customers want multilingual full-text relevance, typo tolerance, and semantic matching.

A developer proposes creating ordinary B-tree indexes on hotel-description fields in PostgreSQL.

What capabilities are missing from that proposal?

What simpler and more specialized alternatives would you evaluate?

## Challenge 6 — The analytical disaster

A PostgreSQL database handles reservations reliably.

The analytics team introduces huge historical aggregation queries.

Customer-facing latency rises dramatically.

What architectural options would you consider, and why might column-oriented storage help?

## Challenge 7 — The broken synchronization pipeline

The catalogue database updates a hotel.

The search index update fails.

Customers continue seeing the old description.

What synchronization architecture would reduce the likelihood of silently losing the update?

Why are retries alone not a complete solution?

## Challenge 8 — The duplicate event

An outbox publisher sends an event.

The search-index consumer processes it successfully.

The publisher crashes before recording successful delivery.

After restart, the event is sent again.

How should the consumer behave?

What additional mechanism is needed when events for the same entity arrive out of order?

---

# 20. Solutions and Discussion

## Solution 1 — Cache and sessions

An all-keys eviction policy allows eligible keys to be evicted under memory pressure, including session state.

The system treated disposable cached summaries and authentication-related state as though they had the same retention requirements.

Separate workloads or adopt appropriate eviction, memory, and persistence policies. Define what happens when session storage becomes unavailable.

A cache outage should ideally degrade performance rather than violate business correctness.

## Solution 2 — Redis durability

Redis persistence is configurable.

RDB snapshots can lose writes performed after the last snapshot. AOF durability depends on synchronization policy. Replication and failover introduce additional guarantees and failure modes.

Inspect the actual persistence, journal synchronization, and replica acknowledgment configuration before claiming the database violated its contract.

An acknowledged command doesn't mean exactly the same thing under every deployment configuration.

## Solution 3 — Hot partition

DynamoDB partitions work according to the distribution of access to partition-key values and underlying physical capacity.

Concentrating writes on one date value can create a hot key range.

On-demand scaling and adaptive capacity help, but do not eliminate every local throughput constraint.

Redesign keys around access patterns and effective workload distribution, potentially using more granular or deliberately distributed write keys.

## Solution 4 — Near real-time indexing

Elasticsearch makes new changes visible to ordinary search through refresh behavior.

A successful indexing response doesn't always mean immediate search visibility.

Explicit refresh or refresh-aware waiting can help workflows requiring stronger immediate visibility, but excessive refreshes increase indexing and search-structure overhead.

Use authoritative reads or appropriate refresh policies according to the operation.

## Solution 5 — Search specialization

Ordinary B-tree indexes are not equivalent to full-text retrieval and relevance ranking.

Evaluate PostgreSQL's actual full-text capabilities, suitable extensions, and a dedicated search system.

Consider linguistic analysis, typo tolerance, relevance scoring, hybrid keyword/vector retrieval, data freshness, indexing complexity, and operational costs.

The right answer depends on required retrieval quality and scale.

## Solution 6 — OLTP versus OLAP

The analytical queries compete with customer-facing transactions for resources.

Possible solutions include query optimization, precomputed aggregates, suitable read replicas, workload isolation, or a dedicated analytical store.

Column-oriented systems can read selected columns efficiently across huge datasets, compress repetitive values, and execute aggregations using specialized algorithms.

But introducing another system creates ingestion and consistency responsibilities.

## Solution 7 — Synchronization

A reliable change-capture mechanism or transactional outbox can ensure that committed authoritative changes produce durable synchronization obligations.

Consumers should support retries, resumption, backfills, and reconciliation.

Retries alone don't help if the event was never durably recorded, can no longer be replayed, or is processed incorrectly after a schema change.

## Solution 8 — Duplicates and ordering

The consumer should use stable event identifiers or appropriate versioning to avoid applying duplicate events incorrectly.

For multiple updates to the same entity, the consumer may also need authoritative version numbers or sequence information so an older event cannot overwrite a newer state.

Idempotency prevents inappropriate repeated effects.

Ordering mechanisms prevent stale state from replacing newer state.

They solve different problems.

---

# 21. The Mental Model Worth Keeping

Specialized data systems exist because different workloads reward different physical organizations and guarantees.

**Redis** excels at low-latency access and operations over useful in-memory data structures.

**DynamoDB** rewards predictable partition-key access patterns and managed distributed operation.

**Elasticsearch and OpenSearch** organize information for retrieval, relevance ranking, and search-oriented workloads.

**Column-oriented analytical systems** optimize scanning, filtering, and aggregating large datasets.

**Time-series systems** specialize around timestamped observations, retention, and time-window calculations.

But choosing the right product is only half the architecture.

The other half is deciding which information is authoritative, which representations are derived, how changes move between systems, and how disagreements are repaired.

The central principle is:

**A specialized database earns its place when the value of its specialized operations exceeds the cost of maintaining another independent system and another copy of reality.**

Three questions recover most of this lecture:

What access pattern is this system unusually good at?

What guarantees and capabilities are we giving up or changing?

What happens when this system is stale, unavailable, overloaded, or inconsistent with its source?

If you can answer those questions, you can evaluate unfamiliar data technologies without knowing every command or proprietary feature.

That's a much more durable engineering skill than memorizing database logos.

---

# 22. Next Lecture — The Data Architecture Workshop

We've completed the theoretical portion of CS340.

We understand relational and non-relational data models, storage-engine trade-offs, MongoDB document boundaries, indexes, aggregation, replication, sharding, and specialized systems.

But real architecture decisions rarely arrive as neatly separated subjects.

A company presents a workload, a growth forecast, a set of reliability requirements, and a budget.

The technical lead must decide what to build.

In **CS340-L07 — The Data Architecture Workshop**, we'll take a growing SaaS platform and design its complete data architecture.

We'll choose sources of truth, defend indexing and partitioning decisions, investigate simulated failures, design synchronization pipelines, and explain what we deliberately refuse to introduce.

The challenge will not be naming every database technology we know.

It will be building the simplest data architecture that satisfies the business's real constraints.

The theory has given us the vocabulary.

Now we'll use it to make decisions.

---

## Optional Practical Lab — Specialized Data Systems in Action

*The spoken lecture ends here. The remaining material is intended for visual study, terminal experimentation, and interview revision.*

### Lab A — Explore Redis data structures

In a local development Redis instance, create a disposable cached hotel summary and a sorted set representing popularity rankings.

```bash
redis-cli SET hotel:1042 '{"name":"Old Town House"}' EX 300
redis-cli TTL hotel:1042
redis-cli GET hotel:1042

redis-cli ZADD hotel:popularity 450 hotel:1042
redis-cli ZADD hotel:popularity 725 hotel:2081
redis-cli ZREVRANGE hotel:popularity 0 9 WITHSCORES
```

Explain why the string and sorted set support different operations.

Observe the TTL behavior. Don't confuse expiration with eviction.

### Lab B — Inspect Redis memory and persistence

In a disposable local Redis environment, examine:

```bash
redis-cli INFO memory
redis-cli INFO stats
redis-cli INFO persistence
redis-cli CONFIG GET maxmemory
redis-cli CONFIG GET maxmemory-policy
redis-cli CONFIG GET appendonly
redis-cli CONFIG GET appendfsync
```

Identify memory usage, eviction counters, expiration counters, and persistence configuration.

Do not change eviction or persistence settings in production merely to reproduce a failure.

### Lab C — Design a safe rate limiter

Design a rolling-window limiter permitting one hundred requests per minute.

Consider using a Redis sorted set keyed by customer or API identity.

Your design must explain:

1. How old entries are removed.
2. How the current count is determined.
3. How admission and insertion become atomic.
4. What happens when Redis is unavailable.
5. Whether the limiter must remain correct across failover.

A correct design is more than a sequence of individually valid Redis commands.

### Lab D — Design DynamoDB keys

Imagine a service supporting these access patterns:

- Retrieve one event by its unique ID.
- Retrieve a customer's most recent events.
- Retrieve events from one customer during a time range.
- Retrieve events by event category across many customers.

Propose a primary key and any necessary secondary indexes.

Discuss which operations can be targeted and which may need another access path.

Explain how your design behaves when one customer generates one hundred times more traffic than an ordinary customer.

### Lab E — Compare DynamoDB read guarantees

Using the official documentation, distinguish eventual and strong reads for base tables, local secondary indexes, and global secondary indexes.

Then consider a write followed by a read through a GSI.

Can the application require the GSI query to be strongly consistent?

If not, what architectural alternative would satisfy a workflow requiring immediate authoritative visibility?

### Lab F — Observe Elasticsearch refresh behavior

Using a local Elasticsearch test environment, create a simple index, insert a document, and query it.

The following commands use a local HTTP endpoint for illustration.

```bash
curl -X PUT "http://localhost:9200/hotels"

curl -X PUT "http://localhost:9200/hotels/_doc/H-1042" \
  -H "Content-Type: application/json" \
  -d '{"name":"Old Town House","city":"Vilnius"}'

curl -X POST "http://localhost:9200/hotels/_search" \
  -H "Content-Type: application/json" \
  -d '{"query":{"match":{"name":"Old Town"}}}'
```

The exact deployment may require authentication and HTTPS.

Investigate the relationship between indexing acknowledgment, refresh, and search visibility.

Do not assume every successful search-result timing demonstrates the same refresh behavior.

### Lab G — Model an analytical table

Consider a ClickHouse MergeTree table storing hotel activity events.

A simplified design might be:

```sql
CREATE TABLE hotel_events
(
    event_id String,
    tenant_id String,
    event_time DateTime,
    event_type LowCardinality(String),
    country LowCardinality(String),
    revenue Decimal(12, 2)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_time)
ORDER BY (tenant_id, event_time, event_id);
```

Explain how the partition expression and ordering key serve different purposes.

What queries benefit from the chosen ordering?

What changes if nearly every query filters only by country and event time?

Why isn't an ordinary primary-key lookup the main workload this table is optimized for?

### Lab H — Design a CDC pipeline

Create a conceptual architecture connecting an authoritative catalogue to a search index and an analytical store.

Your design must handle:

- Initial backfill.
- Ongoing change capture.
- Duplicate events.
- Out-of-order updates.
- Consumer downtime.
- Schema changes.
- Deletions.
- Reconciliation after an extended outage.

Explain why one successful publish call is not enough to prove the derived stores will remain correct indefinitely.

### Lab I — The architecture review

Your company proposes PostgreSQL, MongoDB, Redis, DynamoDB, Elasticsearch, and ClickHouse.

Assume twelve engineers, moderate traffic, and a rapidly growing hotel catalogue.

For each system, defend whether it belongs in the initial deployment.

State the specific workload it serves, what would happen if it failed, and how its data would be recovered.

Reject at least two proposed systems unless the stated requirements genuinely justify all of them.

The goal is not to demonstrate enthusiasm for infrastructure.

It's to demonstrate restraint.

---

## Further Reading — Optional Technical References

1. [Redis — Data Types](https://redis.io/docs/latest/develop/data-types/) — Strings, hashes, sets, sorted sets, streams, and other structures.
2. [Redis — Key Eviction](https://redis.io/docs/latest/develop/reference/eviction/) — Memory limits and eviction policies.
3. [Redis — Persistence](https://redis.io/docs/latest/management/persistence/) — RDB snapshots, AOF, and durability trade-offs.
4. [Redis — Streams](https://redis.io/docs/latest/develop/data-types/streams/) — Stream storage and consumer processing.
5. [AWS — DynamoDB Data Modeling](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/data-modeling.html) — Designing around access patterns.
6. [AWS — Partition Key Design](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html) — Partition distribution and hot-key constraints.
7. [AWS — DynamoDB Read Consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html) — Eventual and strong reads.
8. [AWS — DynamoDB Capacity Modes](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/capacity-mode.html) — On-demand and provisioned throughput.
9. [Elastic — Near Real-Time Search](https://www.elastic.co/docs/manage-data/data-store/near-real-time-search) — Refresh and search visibility.
10. [Elasticsearch — Query DSL](https://www.elastic.co/docs/reference/query-languages/querydsl) — Full-text and structured retrieval.
11. [OpenSearch — Documentation](https://docs.opensearch.org/latest/) — Indexing, search, and operational mechanisms.
12. [ClickHouse — Why Columnar Databases Are Fast](https://clickhouse.com/resources/engineering/why-columnar-databases-are-fast) — Column storage and analytical execution.
13. [ClickHouse — MergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/mergetree) — Parts, ordering keys, and sparse indexes.
14. [MongoDB — Change Streams](https://www.mongodb.com/docs/manual/changeStreams/) — Consuming committed data changes.
15. [Debezium — Documentation](https://debezium.io/documentation/) — Change data capture and integration pipelines.
16. Martin Kleppmann, *Designing Data-Intensive Applications* — Data systems, storage, replication, and distributed consistency.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced for voice-reader skipping. Use this as the rapid visual reference; return to the lecture only when a distinction needs rebuilding.*

```text
CS340-L06 — SPECIALIZED DATA SYSTEMS / INTERVIEW GLANCE CARD

CORE DECISION
  Specialized systems optimize particular workloads.
  Benefit must exceed: operations + new failure domain + consistency pipeline.
  Ask: access pattern? guarantees? rebuild path? failure impact?

REDIS — LOW-LATENCY DATA STRUCTURES
  String       cached value, counter, binary/text payload
  Hash         field/value collection
  Set          unique membership, intersections
  Sorted set   scored ordering, rankings, sliding-window machinery
  Stream       append-oriented event log, consumer groups
  Atomicity    individual commands atomic; multi-step logic may need
               Lua/Functions/transactions or other coordination

  TTL         logical expiration by time
  EVICTION    memory-pressure removal under maxmemory policy
  allkeys-*   may remove any eligible cache key
  volatile-*  evicts among keys with expiration
  noeviction  rejects appropriate writes at memory limit
  DON'T mix disposable cache and critical retained state blindly.

  RDB         periodic snapshot; possible loss since last snapshot
  AOF         append-only changes; fsync policy controls crash-loss risk
  Replicas    copies; NOT universal zero-loss failover guarantee
  Cache-aside cache miss → query authority → populate
  Stampede    simultaneous misses hammer source
  Fixes       bounded fallback, TTL jitter, request coalescing,
              safe stale reuse where appropriate
  REDIS ≠ automatically disposable; design durability explicitly.

DYNAMODB — ACCESS-PATTERN-DRIVEN
  PK          partition key: distribution/routing dimension
  SK          sort key: ordered items under same PK
  GetItem     known complete primary key
  Query       targeted PK + suitable sort-key conditions
  Scan        broad item examination; filter ≠ free index
  GSI         alternate partition/sort key, async index maintenance
  LSI         same partition key, alternate sort; constraints apply

  On-demand   managed demand-based throughput/billing; NOT infinite
  Provisioned planned capacity with optional scaling
  Hot key     disproportionate traffic on one value/partition
  Bad key     date-only, status-only, giant single tenant
  Good key    aligns common queries AND distributes traffic

  Eventual read  may miss recent change
  Strong read    supported for base table and LSI, NOT GSI
  Conditional write  atomic expected-state check
  Transactions       supported within documented limits
  TTL deletion       asynchronous; not exact business deadline
  Global tables      MREC or supported MRSC modes;
                     mode and Region constraints matter

ELASTICSEARCH / OPENSEARCH — SEARCH
  Inverted index   term → matching document postings
  Analyzer         tokenize/normalize text at index/query time
  BM25             relevance scoring, not exact equality
  Structured filters + relevance → practical retrieval
  Segments         Lucene largely immutable indexed structures
  Refresh          makes changes searchable; not same as durable commit
  Index ACK        not guaranteed immediately visible to SEARCH
  refresh=wait_for when visibility must be coordinated (where supported)
  Forcing refresh after EVERY write can hurt performance
  Update           indexing/segment work; merges reclaim obsolete data
  Hybrid retrieval keyword + vector + filters/reranking
  HNSW ANN         approximate neighbor search; recall/latency trade-off
  Search index     often DERIVED, not booking/inventory authority

OLAP / COLUMNAR — CLICKHOUSE STYLE
  OLTP              small transactional records / updates / point reads
  OLAP              scans/grouping over enormous datasets
  Column store      reads selected fields over many rows efficiently
  Compression       similar values within a column compress well
  Vectorized        batched execution, SIMD/cache advantages
  MergeTree         immutable parts, background merges, sparse index
  ORDER BY          physical locality, critical to data skipping
  PARTITION BY      lifecycle/pruning, distinct from sort key
  Granules          coarse sparse-index units, not row-by-row B-tree
  Frequent single-row changes ≠ natural strength
  Strong use case   event/conversion analytics, aggregated telemetry

TIME SERIES
  Timestamp-heavy append workload
  Time buckets / rollups / retention / downsampling
  Counter != gauge != histogram
  Percentiles aren't generally averageable
  High-cardinality labels can explode series/storage costs
  Raw request IDs belong in traces/logs more than metric label sets

SYNC / OWNERSHIP
  Primary fact in ONE defined authority.
  Search index, cache, analytics = DERIVED representations.
  Dual write:
    save DB -> index -> crash = inconsistent.
    reverse order = different inconsistency.
  CDC         observes source changes, feeds consumers
  Outbox      business row + event obligation in ONE DB transaction
  Delivery    often at-least-once; idempotency required
  Ordering    version/sequence prevents stale overwrite
  Backfill    historical snapshot + catch-up changes
  Reconcile   compare/repair source vs derived views
  Rebuild     must be possible after lost offsets/consumer bugs

ARCHITECTURAL FAILURE QUESTIONS
  Redis down?      can origin survive miss storm?
  Dynamo hot?      key distribution/capacity constraints?
  Search stale?    what is authoritative; refresh lag acceptable?
  OLAP late?       can customers still book?
  CDC broken?      how detect lag and rebuild?
  Duplicate event? idempotent consumer?
  Old update late? version-aware apply?
  New datastore?   who owns on-call, backups, migrations, security?

WHEN TO CHOOSE WHAT
  Relational invariant / money         PostgreSQL (strong default)
  Bounded document aggregates         MongoDB or PostgreSQL JSONB
  Fast ephemeral lookup / data struct Redis
  Predictable distributed key access  DynamoDB
  Linguistic relevance / hybrid search Elasticsearch/OpenSearch
  Huge aggregate scans / time events  ClickHouse/analytical DB
  Timeseries telemetry & retention    appropriate TSDB/analytics stack

FIVE QUESTIONS BEFORE ADDING A DATABASE
  1. What measured workload can't the existing system satisfy?
  2. Why is this engine's physical design better?
  3. What correctness / freshness contract changes?
  4. How do we sync, observe, backfill, and rebuild its data?
  5. Does the benefit justify another production failure domain?

SENIOR LINE
  "I keep one clear authority for each business fact and introduce
   specialized derived systems only when their workload advantage
   outweighs synchronization, reliability, and operating costs."
```
