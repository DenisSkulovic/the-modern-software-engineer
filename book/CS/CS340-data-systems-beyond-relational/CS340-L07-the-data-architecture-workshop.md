---
id: CS340-L07
course: CS340
title: "The Data Architecture Workshop"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: CS340-L06
next: null
---






# CS340 — Data Systems Beyond Relational Databases

## Lecture 07: The Data Architecture Workshop

*You're the technical lead. The product is growing, the requirements keep changing, and the database architecture is now your responsibility. Choose carefully—because every clever decision comes with a bill.*

---

# 1. Monday, 09:00 — Congratulations, You're Responsible

The meeting begins with a familiar sentence.

"We need to redesign our data architecture."

You're the new technical lead of a travel platform called Meridian Stays. The company connects travelers with hotels and accommodation suppliers across Europe.

The existing system works. Customers search properties, select rooms, create reservations, and pay. Hotels can update their descriptions and amenities, while suppliers periodically synchronize pricing and inventory.

But the platform is growing, and management believes the current architecture won't survive another year.

The CTO presents a diagram.

PostgreSQL stores reservations and payments. MongoDB contains hotel descriptions. Redis caches popular properties. A few background workers synchronize supplier data.

The product team wants Elasticsearch for search. Analytics wants ClickHouse. One engineer wants DynamoDB for events. Another recommends sharding MongoDB immediately.

The CTO turns toward you.

"You're responsible for the new architecture. What do we build?"

This is a surprisingly difficult assignment, not because you lack technologies to choose from, but because you have too many.

You could construct an impressive architecture involving six databases, several messaging systems, sophisticated change-data-capture pipelines, and elaborate distributed coordination.

You could also build something much simpler.

Both might work.

But only one might be appropriate for the company's actual requirements.

Today, we won't study another database in isolation. We'll use everything learned in CS340 to make engineering decisions under realistic constraints.

The exercise is divided into several rounds.

First, we'll establish what the system must do.

Then we'll choose authoritative data stores and derived representations.

Management will introduce new requirements.

Production will experience failures.

And we'll have to revise our decisions without abandoning correctness.

There is no one architecture that is always right. But there are certainly architectures that are unjustifiably complicated, dangerously inconsistent, or based on assumptions nobody has tested.

Our job is to avoid them.

---

# 2. The Brief: What Are We Actually Building?

Before touching the architecture diagram, you ask for numbers.

The product team provides an initial workload estimate.

The platform lists approximately eighty thousand properties. Several million historical reservations exist in PostgreSQL. The public catalogue is stored in MongoDB, with descriptions, amenities, photographs, and property characteristics.

On an ordinary day, the application handles several dozen public search requests per second, with much higher peaks during campaigns.

Reservation creation is considerably less frequent but much more consequential.

The catalogue receives supplier updates throughout the day.

The analytics pipeline collects millions of browsing and product-interaction events daily.

The engineering team consists of twelve developers and a small infrastructure group.

The company operates primarily from one European cloud region.

Management expects traffic to increase significantly during the coming year, but the exact growth is uncertain.

These facts should already influence our decisions.

An eighty-thousand-property catalogue is not automatically a sharding problem.

Several million reservations aren't inherently beyond PostgreSQL's capabilities.

And a forecast of future growth isn't proof that the current architecture needs immediate replacement.

Our first question should be:

**Which requirements are already failing, and which are merely predictions?**

## 2.1 Establish the correctness requirements

The CTO asks you to identify operations that must never produce an incorrect result.

Reservation creation is the obvious one.

The system must not promise inventory it cannot legitimately allocate.

Financial records must accurately represent completed payment operations.

A confirmed reservation must not silently disappear because of an ordinary database failover.

Historical prices and agreed terms must remain reconstructable even when the current hotel catalogue changes.

These are business invariants.

Now consider public hotel search.

A newly added property might take several seconds to appear in search results.

Is that unacceptable?

Probably not.

A hotel's updated description might appear slightly late in a CDN cache.

Again, perhaps acceptable.

Analytics might be delayed by several minutes without affecting customer-facing operations.

Different parts of the platform therefore require different guarantees.

This is our first major design decision.

We should not impose the strongest available consistency requirements on every operation merely because strong consistency sounds reassuring.

Nor should we accept eventual consistency for operations that require authoritative decisions.

**Correctness must be specified per business operation, not assigned indiscriminately to an entire technology stack.**

## 2.2 Establish measurable operating requirements

Management says the platform should be "fast and highly available."

That is not yet a requirement.

Fast compared with what?

Available under which failure conditions?

You propose concrete engineering targets for review.

For example, the company might aim for ninety-five percent of ordinary catalogue API requests to complete within a few hundred milliseconds under defined traffic conditions.

Reservation creation can have a different latency budget because it performs transactional work and interacts with external systems.

Availability objectives should also be defined separately for browsing, booking, and internal analytics.

Recovery requirements deserve equal attention.

The **Recovery Point Objective**, or RPO, expresses how much data loss the business can tolerate during a specified recovery scenario.

The **Recovery Time Objective**, or RTO, expresses how quickly service should be restored.

For committed reservations, the company may require essentially no acknowledged transaction loss under an ordinary single-node failure.

For disposable analytics events, a small, explicitly accepted loss window might be tolerable.

But do not invent these commitments without business approval.

Our numbers are design assumptions until management accepts the cost of meeting them.

That distinction is essential.

Architecture begins with negotiated promises, not database configuration.

---

# 3. First Decision: Who Owns Reality?

You draw five words on the whiteboard.

**One fact. One authority. Many possible copies.**

This doesn't mean every piece of information must physically exist in only one database.

Quite the opposite.

Modern applications routinely maintain caches, search indexes, read replicas, historical snapshots, and analytical datasets.

The problem is allowing independently updated copies to become competing sources of truth.

Let's classify our information.

## 3.1 Reservations and payments

PostgreSQL already maintains these records.

It has appropriate relational constraints, transaction support, and an established operational history within the company.

There is no compelling reason to migrate reservations to MongoDB simply because MongoDB handles other application data.

We retain PostgreSQL as the authoritative store for reservation state, inventory commitments, and the application's financial records.

External payment providers remain authoritative for facts about payment operations performed within their own systems, so our local records must be reconciled against those external facts when outcomes are uncertain.

The boundary is explicit.

PostgreSQL owns our booking state.

The payment provider owns its external payment-processing outcome.

The workflow must keep them consistent through appropriate state transitions and reconciliation.

## 3.2 Hotel catalogue

MongoDB already stores hotel profiles.

The document model fits bounded property descriptions, localized text, amenity arrays, and other flexible attributes reasonably well.

The team understands the technology, and there is no evidence that the catalogue workload exceeds its capacity.

We keep MongoDB as the authoritative catalogue store.

But we explicitly separate public hotel metadata from rapidly changing inventory and reservation records.

Just because all this information concerns the same hotel doesn't mean it belongs in one enormous document.

This is the aggregate-boundary lesson from CS340-L03.

## 3.3 Search results

Search results are different.

A search index contains a representation of catalogue information optimized for retrieval.

It is not the authority on whether a room can be sold.

It may also lag behind the catalogue.

This is acceptable if the system treats search as discovery, not confirmation.

The search system can identify promising properties.

The booking workflow must validate authoritative inventory and pricing before creating a commitment.

## 3.4 Analytics

Analytics describes historical activity and aggregated measurements.

It may be acceptable for analytical reports to be delayed.

That makes it a candidate for asynchronous ingestion and a specialized analytical store.

But the raw event stream and derived aggregates need defined ownership and recovery behavior.

Otherwise, a dashboard can silently become a collection of numbers nobody can explain.

## 3.5 The architecture without unnecessary decoration

The initial logical design is now fairly simple.

PostgreSQL owns bookings and financial application state.

MongoDB owns property catalogue information.

Other systems may hold derived views.

This is not yet a complete physical architecture.

We haven't selected every cache, search engine, or event pipeline.

That's deliberate.

**First define authoritative boundaries. Then decide which physical optimizations are necessary.**

---

# 4. The Booking Workflow: The Part That Must Be Correct

The CTO gives you a scenario.

Two customers attempt to reserve the final available room for the same five-night period.

One request originates from France.

The other originates from Lithuania.

Both reach different Node.js application instances.

How do you prevent double booking?

A developer suggests a Redis lock.

Another proposes sending all booking requests to one application instance.

Neither should be our first answer.

The invariant belongs to authoritative booking state, not to the process memory of a particular server.

## 4.1 Inventory is a transactional decision

Suppose availability is represented by inventory records for each room type and date.

A five-night reservation must claim capacity across five dates.

The application cannot safely read availability, make a decision in memory, and later issue unconditional updates.

Concurrent requests could both observe the same available unit.

Instead, the database operation must enforce the condition that sufficient inventory remains.

For a single inventory record, a conditional atomic update may suffice.

For a multi-night reservation, we may need a transaction coordinating the required inventory updates and reservation record.

The exact schema and locking strategy depend on whether inventory represents interchangeable units, specific physical rooms, or supplier-provided capacity.

But the principle is stable.

**The database must enforce the critical condition at the moment the state changes.**

## 4.2 The transaction must have a clear scope

Imagine one database transaction that claims availability and creates a reservation in a provisional state.

Those changes commit together.

Now the application needs to contact an external payment provider.

Should we hold the PostgreSQL transaction open while waiting for the provider?

Usually, that's a poor idea.

The network call may take seconds or fail ambiguously.

A long-running transaction can hold locks, retain resources, and increase contention.

Instead, the reservation workflow can use explicit states.

For example, a reservation might be pending, held, confirmed, cancelled, or expired according to carefully defined transition rules.

Inventory holds need expiration and recovery policies.

Payment operations need durable identities.

And confirmation should occur only when the required business conditions have been established.

This is not merely database design.

It is the point where database correctness becomes distributed-workflow correctness.

## 4.3 A retry is not a new booking

Suppose the API sends a reservation request to the backend.

The backend commits the reservation.

Then the response disappears.

The customer retries.

If the backend treats every retry as a new operation, it may create a duplicate reservation.

We need an idempotency mechanism tied to the intended business operation.

A unique operation identifier can be stored and enforced transactionally.

When a repeated request arrives, the system can locate the existing operation and return its known result or current status.

An idempotency key shouldn't merely be checked in a cache before inserting a reservation.

That would create another check-then-act race.

The durable booking store must enforce the relevant uniqueness and operation-identity requirements.

We now have a defensible foundation.

PostgreSQL protects booking invariants.

The application protects business workflow identity.

And uncertain external payment outcomes are reconciled rather than guessed.

---

# 5. Second Decision: Should Search Get Its Own Database?

The product manager introduces new requirements.

Customers should search for "quiet apartments near the old town with secure parking."

The system must tolerate spelling mistakes, understand synonyms, and rank relevant results.

The existing MongoDB queries perform structured filtering adequately, but relevance quality is limited.

Now specialized search becomes plausible.

Before approving Elasticsearch or OpenSearch, however, you ask for evidence.

How complex is the required linguistic search?

How large is the catalogue?

What is the measured latency of existing approaches?

Could MongoDB's available search features satisfy the requirement?

Could the existing relational system's text-search capabilities be sufficient if the catalogue were stored there?

The goal isn't to delay every decision indefinitely.

It's to establish why another system is justified.

## 5.1 A derived search index

Suppose the evaluation demonstrates that a dedicated search engine materially improves relevance and supports the expected workload.

We approve it.

But we explicitly classify the search index as a derived representation.

MongoDB remains authoritative for catalogue records.

The search system receives selected fields needed for retrieval.

It may contain normalized text, tokenized terms, geographical information, structured filters, and vector representations.

It does not become responsible for deciding whether a reservation is valid.

Nor should every private catalogue attribute automatically be copied into a publicly queryable index.

The indexing pipeline must define which fields are authorized to appear.

## 5.2 The first synchronization failure

A supplier updates a hotel's cancellation policy in MongoDB.

The application then attempts to update the search index.

MongoDB succeeds.

The search update fails.

Now the two systems disagree.

A naïve implementation might simply retry in the HTTP handler.

But what if the process crashes before recording the need to retry?

The search update can be silently lost.

A more robust design uses durable change propagation.

Because MongoDB owns the catalogue, a change-stream-based indexing process is a natural candidate.

It can consume authoritative changes and update the derived search representation.

The consumer needs durable progress tracking, retries, and recovery procedures.

And it must handle the possibility that its saved resume position becomes unusable after an extended outage.

MongoDB change-stream resumption depends on the availability of sufficient oplog history.

If that history is no longer available, the indexer may need to rebuild or resynchronize from an authoritative snapshot.

So our design includes a rebuild path before the first incident occurs.

## 5.3 Initial backfill is not optional

There's another subtle problem.

The search engine starts empty.

MongoDB already contains eighty thousand hotels.

A change stream only observing new updates doesn't automatically index every historical document.

We need an initial backfill.

But while we're copying the existing catalogue, suppliers continue changing data.

If we simply read every document and then begin watching for changes, updates occurring during the backfill can fall into a gap.

A robust process needs an appropriate snapshot or change-capture coordination strategy.

It must establish a reliable relationship between the baseline and subsequent changes.

Different CDC technologies implement that handoff differently.

The conceptual requirement is universal.

**The derived index must contain the baseline plus every relevant subsequent change, without an unobserved interval.**

## 5.4 Versions prevent stale overwrites

Now suppose a hotel changes its name twice.

The first event describes version 41.

The second describes version 42.

Because of retries or asynchronous processing, version 42 reaches the search index first.

Version 41 arrives afterward.

If the consumer blindly applies both events, the older name overwrites the newer one.

The indexer therefore needs suitable ordering or version checks.

An authoritative record version can allow the consumer to reject stale updates.

But deletions deserve equal attention.

A delayed old update should not recreate a hotel that has already been deleted.

The synchronization protocol must represent deletion and replacement semantics correctly.

Our search architecture now has an authority, update mechanism, idempotency policy, ordering strategy, and recovery path.

That's considerably more meaningful than drawing an arrow labeled "sync" between two database logos.

---

# 6. Third Decision: Do We Need Redis?

The engineering team wants Redis.

Their argument is familiar.

"Redis is fast."

Correct.

But that isn't yet a reason to introduce it.

What workload is currently too slow?

Which operations would Redis accelerate?

What happens when its contents disappear?

We examine the actual application.

Popular hotel profiles receive many repeated reads.

Some public responses could be cached safely.

Certain rate-limiting and short-lived state operations might also benefit from Redis data structures.

Those are legitimate candidates.

But perhaps the existing CDN already handles most public catalogue caching effectively.

Perhaps PostgreSQL and MongoDB are nowhere near their resource limits.

Perhaps the additional Redis layer would save very little latency while creating another dependency.

For the first deployment, we may decide not to introduce Redis at all.

That isn't technological conservatism for its own sake.

It's avoiding infrastructure that hasn't demonstrated a meaningful benefit.

## 6.1 What would change our mind?

Suppose a production load test reveals that a relatively small set of read-heavy catalogue operations repeatedly consumes database resources.

The responses are safe to cache for a short period.

And a carefully designed Redis cache provides a measurable improvement.

Now Redis has earned its role.

But we still need a cache policy.

What constitutes the cache key?

Does locale affect the result?

Does currency affect the result?

Could authenticated customer information accidentally be shared?

What is the TTL?

How are important changes invalidated?

And what happens during an outage?

The cache should not become the source of truth for inventory.

## 6.2 The fallback trap

Imagine Redis becomes unavailable.

Every application instance falls back to the authoritative database.

The database is suddenly flooded with requests that would normally have been served from cache.

The cache outage now threatens the entire platform.

We need to bound fallback concurrency and protect the source database.

Request coalescing, controlled stale reuse where safe, and admission limits may help.

The correct behavior depends on the data.

A stale hotel description might be acceptable.

A stale final booking decision is not.

The general rule is:

**A performance optimization must not become an uncontrolled dependency that destroys the system when it disappears.**

---

# 7. Management Changes the Workload

Two months later, the company signs a large partnership.

A marketing campaign is expected to increase search traffic dramatically for a short period.

The CTO asks whether the system needs sharding.

Before answering, you request new measurements.

The existing catalogue contains eighty thousand properties.

Search workload is expected to surge, but the catalogue itself isn't suddenly growing by a hundredfold.

Reservation volume will rise, but nowhere near the same proportion as anonymous searches.

That distinction matters.

Search traffic and authoritative booking writes exercise different systems.

Scaling the booking database because public search traffic is rising may be an expensive mistake.

## 7.1 Protect the booking path

The first priority is preserving booking correctness and availability.

Search results can be cached, degraded, or temporarily limited more readily than committed reservations.

We should prevent high-volume browsing traffic from exhausting database connections or application resources needed for booking operations.

Depending on the architecture, this may involve resource isolation, connection-pool limits, workload-specific service capacity, and admission control.

We do not necessarily need another database.

We need to understand which workload threatens which shared resource.

## 7.2 Scale the component that owns the bottleneck

Suppose the search index is saturated.

Adding PostgreSQL replicas won't solve that.

Suppose the Node.js application is CPU-bound while preparing responses.

Sharding MongoDB won't solve that.

Suppose a cache stampede floods the origin.

Adding another cache without correcting cache-miss behavior may simply create a more elaborate failure.

The right intervention follows from measurements.

Which component owns the latency?

What work is it performing?

Can we reduce that work?

And only then, does adding capacity make sense?

This principle should feel familiar from CS230.

The system's visible symptom doesn't necessarily identify the failing layer.

---

# 8. The Sharding Proposal

A database engineer now recommends sharding MongoDB.

Their argument is that distributed infrastructure is the natural next step for a growing business.

You ask a simple question.

"What measurable problem will sharding solve today?"

The answer is unclear.

The current catalogue fits comfortably within the deployed system's resources.

Queries are reasonably indexed.

Write volume is manageable.

Failover is already supported through the replica set.

Adding shards would introduce routing metadata, data-placement decisions, balancing, and potentially distributed queries.

It would also create shard-key constraints that the team must understand.

Without a current scaling problem, the proposal may be premature.

## 8.1 When sharding becomes reasonable

Now imagine a different future.

The event system grows to billions of records.

One storage group can no longer meet sustained throughput or capacity requirements.

Workload isolation and partitioning become genuinely necessary.

Then we evaluate shard keys.

A timestamp-only range shard key could concentrate new writes at the advancing end.

A tenant-ID key might support tenant-specific queries but create a hotspot for an unusually large customer.

A hashed event identifier might distribute writes effectively while making time-range queries span many shards.

The decision depends on actual access patterns.

There is no universal best shard key.

## 8.2 The critical question is routing

A useful shard key should help distribute both data and work.

But query routing matters too.

If most important queries include the shard key, the router may contact a limited set of shards.

If queries omit it, the cluster may perform scatter-gather work across several shards.

An index on every shard can make local lookups efficient without solving inefficient global routing.

These are separate optimization problems.

Before sharding, we should simulate expected read and write distributions.

That is more valuable than admiring how many nodes appear in the architecture diagram.

---

# 9. The Analytics Team Wants Everything

Our next requirement comes from analytics.

The company now collects millions of browsing events daily.

Analysts want to compare conversion by country, device type, campaign, and supplier.

Some reports scan enormous historical datasets.

Running those queries against operational databases begins interfering with customer-facing workloads.

This is a credible reason to separate OLTP from OLAP.

But what architecture should we choose?

## 9.1 Begin with the actual questions

Does the team need real-time dashboards updated every second?

Or are figures delayed by several minutes acceptable?

Do they need raw event history indefinitely?

What are the retention requirements?

How often are historical events corrected?

Which dimensions are queried?

These questions determine the data architecture.

A column-oriented analytical system becomes attractive when the workload genuinely involves large scans and aggregations.

ClickHouse may be a strong candidate.

But it isn't automatically necessary.

For modest workloads, precomputed aggregates or a carefully isolated reporting database might suffice.

## 9.2 The event pipeline

Suppose we approve a separate analytical store.

Events are produced by application services and collected through a durable ingestion mechanism appropriate to the required reliability.

The pipeline validates event formats, assigns stable identifiers, and delivers data to the analytical system.

Consumers must handle duplicates and retries.

They must also support schema evolution.

For example, an older event might omit a country code that newer events include.

The analytical system needs an explicit interpretation for historical data.

But we should distinguish operational business facts from raw behavioral events.

A completed reservation used for financial reporting should be derived from authoritative booking records or a reliable record of their committed state.

It shouldn't depend solely on an untrusted browser event claiming that a booking succeeded.

The browser's observation and the database's business fact are different information sources.

## 9.3 Retention and recovery

Now imagine the analytics consumer falls behind for several hours.

Can the event source retain unconsumed information long enough?

What happens if the consumer resumes and processes events twice?

What if its saved checkpoint no longer corresponds to retained source history?

The system needs monitoring for ingestion lag and a reprocessing strategy.

Historical backfills should be possible without inventing new event identities that accidentally double-count activity.

Once again, the derived store must be rebuildable.

An analytics database is not merely a faster place to execute GROUP BY.

It's a complete information-processing subsystem.

---

# 10. Incident Review: Three Things Break at Once

Six months later, Meridian Stays is preparing for a major travel promotion.

Then production experiences three incidents.

The CTO asks you to lead the investigation.

The interesting part is that all three appear to involve missing or incorrect data.

But their mechanisms are different.

## 10.1 Incident A — The hotel that wouldn't change its name

A supplier updates its hotel name.

MongoDB shows the new name.

The public search still displays the old one.

The indexing worker is running.

What do we investigate?

First, establish whether the authoritative update was committed.

It was.

Next, inspect the change-capture and indexing pipeline.

We discover that the worker consumed an older change after a newer one and overwrote the search document with stale information.

The problem is event ordering, not query cache freshness alone.

The fix requires version-aware application of changes and a reconciliation procedure.

We also need to verify that deletions cannot be undone by delayed updates.

This is a data synchronization problem.

## 10.2 Incident B — The reservation lost after failover

A customer's reservation was acknowledged shortly before a database failover.

After the failover, it is missing.

But our reservations are stored in PostgreSQL, not MongoDB.

Does the same general principle apply?

Yes.

Imagine PostgreSQL has a primary and an asynchronously replicated standby.

The primary commits the transaction locally and acknowledges the client.

Before the standby receives the necessary WAL information, the primary is permanently lost.

The standby is promoted.

Its state lacks the acknowledged transaction.

The physical details differ from MongoDB's replica-set rollback process.

But the underlying issue is similar.

**Local commit acknowledgment does not automatically mean the transaction reached a future failover target.**

We need to examine the database's replication and failover configuration, durability objectives, and the business contract.

Synchronous replication arrangements can provide stronger guarantees when correctly configured, but they introduce availability and latency trade-offs.

A company claiming zero acknowledged-write loss under a specified failover scenario must prove that its architecture actually meets that claim.

## 10.3 Incident C — Analytics shows twice as many bookings

A reporting dashboard suddenly shows a suspicious increase in booking conversions.

Actual revenue hasn't changed.

The analytics pipeline experienced a consumer restart.

Some events were delivered twice.

The consumer inserted both copies into the analytical dataset without appropriate deduplication.

The resulting dashboard inflated the count.

The fix isn't to weaken booking transactions or restart PostgreSQL.

The authoritative booking data remains correct.

The derived analytics representation is wrong.

We need stable event identities, suitable deduplication, and a way to recompute affected aggregates.

These three incidents demonstrate why data ownership matters.

One problem involved stale derived search state.

Another involved durability across failover.

The third involved duplicate analytical processing.

All three looked like "missing or wrong data."

The correct solutions came from identifying the actual consistency boundary.

---

# 11. The Requirement Nobody Mentioned: Disaster Recovery

The CEO now asks a question the architecture review should have addressed earlier.

"What happens if our entire cloud region becomes unavailable?"

This is not the same as losing one database process.

A local replica set doesn't necessarily protect against regional failure if all members share the affected region.

A backup stored in the same failure domain may also become unavailable.

The answer requires an explicit disaster-recovery design.

## 11.1 Recovery objectives drive the architecture

We return to RPO and RTO.

How much acknowledged business data loss is acceptable after regional destruction?

How quickly must booking operations resume?

Different answers imply different architectures and costs.

A multi-region database with synchronous cross-region coordination may provide stronger durability guarantees but introduce latency and operational complexity.

Asynchronous cross-region replication may reduce normal write latency while permitting some data loss after an abrupt disaster.

Backups and point-in-time recovery provide another layer of protection against corruption or destructive mistakes.

But replication is not the same as backup.

If the application accidentally deletes a collection and replication faithfully copies the deletion, the replicas agree on a disaster.

## 11.2 Test recovery rather than admire the design

A disaster-recovery plan is not complete because the documentation says backups exist.

The team must be able to restore data.

It must know which credentials and dependencies are required.

It must understand how to redirect application traffic.

It must verify that restored systems are mutually consistent enough to resume the intended workflows.

And it needs to measure whether the recovery process meets the promised time and data-loss objectives.

For our company, a sensible initial plan might prioritize reliable backups, tested restoration, and appropriate regional redundancy before attempting a fully active-active global architecture.

The exact decision depends on approved recovery objectives.

More complicated disaster-recovery infrastructure is not automatically safer if nobody can operate it correctly.

---

# 12. What We Deliberately Refuse to Build

We've made several choices.

Now the CTO asks what we aren't building.

This is one of the most revealing questions in an architecture interview.

A weak candidate tends to add technologies until every hypothetical requirement has a solution.

A strong candidate can explain why certain capabilities aren't yet worth their cost.

We decline to shard the hotel catalogue without a demonstrated distribution problem.

We decline to adopt DynamoDB merely because the company already uses AWS.

We decline to use Redis as the ultimate authority for committed inventory.

We decline to make Elasticsearch the authoritative source for reservation correctness.

We decline to build an elaborate active-active multi-region booking system before its consistency requirements and recovery objectives are defined.

And we decline to create a separate graph database merely because fraud investigations involve relationships.

Those are not permanent prohibitions.

They're decisions based on current requirements.

## 12.1 What would justify revisiting them?

Sharding becomes appropriate when the data or workload genuinely requires distribution beyond the current deployment's sustainable capacity.

A dedicated graph system becomes attractive when complex relationship traversals are central enough to justify it.

DynamoDB becomes compelling when predictable partition-key-oriented access, managed scale, and its specific guarantees align with an operational workload.

Redis becomes valuable when a measured low-latency access pattern benefits sufficiently from its data structures.

A separate analytical platform becomes attractive when operational and analytical workloads interfere or analytical scale clearly exceeds the economical capabilities of simpler approaches.

Good architecture therefore includes **decision triggers**.

Not merely what we chose, but what evidence would cause us to choose differently.

That gives the architecture a path for evolution without pretending we can predict every future requirement.

---

# 13. The Final Architecture Review

The CTO returns to the meeting room.

Six months have passed in our fictional exercise.

The company has grown.

Some requirements changed.

Several incidents revealed weaknesses.

You're asked to summarize the architecture.

Your answer should be considerably simpler than the accumulated discussion.

PostgreSQL remains authoritative for booking and financial application state.

Its critical transactions are protected by appropriate constraints and concurrency control.

Its replication and recovery settings are selected according to explicit business durability requirements.

MongoDB owns the property catalogue, using bounded document aggregates and indexes aligned with common access patterns.

The search engine maintains a derived, rebuildable representation of selected catalogue data.

A reliable change-capture mechanism updates the search index, with version-aware consumers and reconciliation.

Redis is used only where measured access patterns justify it, and cached data is never treated as an unquestionable business authority.

A dedicated analytical pipeline processes selected events and committed business facts into an analytical store where the workload requires it.

The architecture separates browsing workload from critical booking work, imposes meaningful concurrency limits, and protects shared dependencies.

Monitoring tracks not only service availability but also replication lag, synchronization lag, cache behavior, indexing failures, query work, and business invariants.

Finally, the architecture has explicit recovery procedures and a plan for evolving data placement when actual growth justifies it.

None of this requires claiming that one database technology is universally superior.

Each system has a job.

Each business fact has an authority.

Each derived representation has an update and recovery strategy.

And each important promise has a mechanism capable of enforcing it.

That's the essence of a coherent data architecture.

---

# 14. The Oral Examination — Defend Your Design

Now it's your turn to act as the technical lead.

Answer the following questions aloud before reading the discussion.

A strong answer should state its assumptions, explain the trade-offs, and identify what evidence could change the decision.

## Challenge 1 — Why not one database?

A CTO asks:

"Why can't PostgreSQL handle reservations, catalogue documents, search, and analytics?"

Give a defensible answer without claiming PostgreSQL is incapable of any of those workloads.

Explain when one versatile database is preferable and when specialization becomes justified.

## Challenge 2 — The consistency contract

A customer creates a booking and immediately opens its confirmation page.

The write was acknowledged, but the read is served from an asynchronous replica.

What could go wrong?

How would you design the read path to satisfy the customer-facing guarantee?

## Challenge 3 — The hot customer

A multi-tenant event system uses tenant ID as its partition key.

One enterprise customer generates nearly half the traffic.

The storage system throttles or becomes saturated on that customer's partition.

Why did adding more nodes fail to solve the problem?

What alternative partitioning or workload-isolation strategies would you consider?

## Challenge 4 — The unreliable search pipeline

MongoDB owns property descriptions.

Elasticsearch contains searchable copies.

A change-stream consumer has been offline longer than the retained oplog history permits reliable resumption.

How would you restore the search index without permanently missing changes made during recovery?

## Challenge 5 — The cache becomes the outage

Redis fails.

Hundreds of application instances begin querying PostgreSQL directly.

Database connections saturate.

What architectural mistake amplified the incident?

Which protections would you introduce?

## Challenge 6 — A supposedly successful payment

A payment provider processes a request, but the application times out before receiving the response.

The local reservation remains in a pending state.

Should the backend issue a fresh payment request?

What persistent information and reconciliation process are needed?

## Challenge 7 — The architecture must survive regional failure

Management demands essentially no acknowledged reservation loss during a specified regional disaster.

The current PostgreSQL deployment replicates asynchronously to another region.

Does the architecture satisfy the requirement?

What trade-offs would a stronger design introduce?

## Challenge 8 — The six-database proposal

Your team proposes PostgreSQL, MongoDB, Redis, DynamoDB, Elasticsearch, and ClickHouse.

For each proposed system, explain what evidence would justify it.

Then identify at least two systems you would decline to introduce immediately.

Your answer should include operating cost, correctness, and data ownership—not merely performance.

---

# 15. Solutions and Discussion

## Solution 1 — One database versus specialization

PostgreSQL can support relational transactions, JSONB documents, text search, and analytical queries.

A small team should often begin with such a versatile platform rather than introduce several independently operated systems.

Specialization becomes justified when a particular workload's requirements or measured resource costs are materially better served elsewhere.

Examples include sophisticated retrieval and relevance ranking, very large analytical scans, or specialized low-latency data-structure operations.

The additional system must earn its complexity through measurable value.

## Solution 2 — Read-after-write behavior

An asynchronous replica may lag behind the primary.

A successful write acknowledgment doesn't automatically make the result visible on every replica.

For a booking confirmation page, a read from the authoritative primary or another appropriately consistent read path may be preferable.

The precise solution depends on the database's replication and read-consistency guarantees.

The application should not promise immediate visibility while intentionally using a read path that doesn't provide it.

## Solution 3 — Hot tenant

Partitioning by tenant ID concentrates all traffic for one tenant into the corresponding partitioning unit.

Adding capacity elsewhere doesn't automatically distribute one unusually active key.

Possible improvements include more granular partition keys, separately partitioning large tenants' data, or isolating major customers onto dedicated infrastructure.

The design must preserve useful query targeting and avoid creating excessive scatter-gather work.

## Solution 4 — Rebuilding the search index

The indexer cannot assume an expired change-stream resume token still identifies available history.

A safe recovery needs a consistent baseline and a change-capture handoff with no unobserved interval.

One strategy is to build a new index from an authoritative snapshot while capturing subsequent changes from a valid position, then replay and reconcile those changes before switching queries to the new index.

The exact implementation depends on the source database's snapshot and change-stream guarantees.

Versioning, duplicate handling, and deletion semantics are necessary.

## Solution 5 — Cache fallback overload

The system allowed unbounded cache-miss traffic to flood the authoritative database.

A cache failure therefore became a database overload incident.

Use bounded fallback concurrency, request coalescing, sensible timeouts, load shedding, and controlled stale responses where business semantics permit.

Separate disposable caching from correctness-critical state.

The source database must be protected even when the cache is unavailable.

## Solution 6 — Uncertain payment

A timeout doesn't prove the payment failed.

The provider may have completed the operation before the response was lost.

The application should preserve the original payment-operation identifier and use provider-supported idempotency or status-reconciliation mechanisms.

The reservation state machine should represent pending or uncertain outcomes honestly.

Blindly creating a new payment operation risks duplicate charges.

## Solution 7 — Regional durability

Asynchronous cross-region replication may leave acknowledged primary writes absent from the standby at the moment of catastrophic primary-region loss.

It therefore cannot automatically satisfy an essentially zero-loss regional disaster requirement.

Stronger synchronous or coordinated cross-region durability mechanisms may be necessary, depending on the precise commitment.

They can introduce additional write latency, reduced availability during network partitions, and higher operating costs.

The chosen architecture must be tested against an explicitly defined failure scenario rather than a vague promise of "multi-region resilience."

## Solution 8 — Technology selection

PostgreSQL is justified by transactional booking and financial records.

MongoDB may be justified by an existing flexible catalogue with access patterns that benefit from document aggregates.

Redis requires demonstrated value for caching, sessions, coordination, or specialized data-structure operations.

DynamoDB requires a clear key-oriented operational workload that benefits from its scaling and managed-service properties.

Elasticsearch or OpenSearch requires sufficiently advanced search and relevance requirements.

ClickHouse or another analytical system requires large-scale analytical workloads whose benefits outweigh ingestion and operational costs.

A reasonable initial decision might retain PostgreSQL and MongoDB, defer DynamoDB, and introduce search or analytics only after validating their workloads.

The correct answer isn't the maximum number of technologies.

It's the smallest architecture capable of satisfying the accepted requirements with appropriate reliability.

---

# 16. The Mental Model Worth Keeping

A data architecture is not a diagram of database products.

It is a set of decisions about where information lives, who is allowed to change it, how it is retrieved, which guarantees operations require, and what happens when systems fail.

Seven questions recover most of this course.

**What is the authoritative fact?** Every critical piece of business information needs a defined owner.

**What is the dominant access pattern?** Point lookup, transaction, document retrieval, text search, relationship traversal, or analytical scan?

**What must be correct together?** Choose atomicity and transaction boundaries around actual business invariants.

**What may be temporarily stale?** Derived search results and analytics often have different requirements from booking commitments.

**What physical work does the query cause?** Understand indexes, storage layout, partitioning, and the amount of data examined.

**How does the system fail?** Consider crashes, replication lag, ambiguous outcomes, overload, and lost synchronization.

**How do we recover?** Backups, event replay, reindexing, reconciliation, and tested restoration are part of the architecture.

The deepest principle is:

**The best data architecture is not the one with the most sophisticated technology. It is the simplest architecture whose mechanisms actually enforce the business's promises.**

Everything else is a trade-off.

And every trade-off should have an explanation.

---

# 17. Where We Go Next — Distributed Systems and Production Engineering

We've completed CS340.

We began by asking why different kinds of databases exist.

We examined storage engines, document modeling, indexes, replication, sharding, and specialized systems.

Finally, we used those ideas to design a coherent architecture under changing requirements and failure conditions.

The next natural step is **CS430 — Distributed Systems and Reliable Workflows**.

That course investigates the broader problems created when independent services and machines must cooperate: partial failure, uncertain outcomes, consistency, replication, scaling, events, and durable business workflows.

Many of those mechanisms appeared during today's workshop.

CS430 develops them in greater depth and beyond the boundaries of databases.

Later, SE340 and SE440 will connect those ideas to cloud infrastructure, deployment, reliability, testing, and incident response.

At this point, you don't need to remember every MongoDB command, DynamoDB capacity detail, or ClickHouse engine setting.

You need something more valuable.

When confronted with a new data problem, you should be able to recognize which family of mechanisms is relevant, identify the guarantees you need, and know which implementation details deserve investigation.

That's what a strong foundation feels like.

Not certainty about everything.

A reliable sense of where the important questions are.

---

## Optional Practical Lab — The Complete Data Architecture Studio

*The spoken lecture ends here. The exercises below are intended for screen-based design work, diagrams, implementation experiments, and later interview revision.*

### Lab A — Draw the data ownership map

Construct a diagram representing the following responsibilities:

- Reservation state.
- Authoritative inventory.
- Payment-operation state.
- Hotel catalogue.
- Search index.
- Cache.
- Raw analytics events.
- Analytical aggregates.

Use distinct arrows for authoritative writes, derived-data updates, and read operations.

The following is an illustrative logical map, not a prescribed deployment.

```text
                       CLIENTS
                          |
                          v
                    APPLICATION API
                     /           \
                    v             v
              PostgreSQL        MongoDB
             reservations       catalogue
              inventory           |
               payments           | CDC
                  |               v
                  |          Search index
                  |               |
                  v               v
             Business events   Search queries
                  |
                  v
           Event ingestion
                  |
                  v
           Analytical store

         Redis: optional derived cache
         with explicit source ownership
```

For every arrow, specify what happens if the destination is unavailable.

### Lab B — State the invariants

Write five invariants the system must preserve.

For example:

- Confirmed reservations must correspond to valid inventory commitments.
- The same logical payment operation must not be processed twice accidentally.
- Historical booking prices must remain reconstructable.
- Customers may access only their own private reservation data.
- Search results must never become authoritative booking decisions.

For each invariant, identify the database constraint, transaction, state machine, or authorization mechanism enforcing it.

### Lab C — Design the booking transaction

Consider an inventory table containing one record per hotel, room type, and date.

A customer requests five consecutive nights.

Design a transaction that claims all five dates only if sufficient inventory remains for each.

Explain your locking or conditional-update approach and how it prevents competing bookings.

Then explain why the transaction should not remain open while waiting for an external payment API.

### Lab D — Model a transactional outbox

For a PostgreSQL-backed reservation service, design an outbox table holding events to publish after a reservation commits.

A simplified schema might look like this:

```sql
CREATE TABLE outbox_events (
    event_id UUID PRIMARY KEY,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    aggregate_version BIGINT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ
);
```

Explain why inserting the reservation and outbox event in one transaction closes the ordinary dual-write failure window.

Then describe what happens when the publisher delivers an event but crashes before recording its completion.

Design idempotent consumer behavior.

### Lab E — Define a search-index event

Create a versioned catalogue-update event.

For example:

```json
{
  "eventId": "event-8821",
  "hotelId": "HOTEL-1042",
  "version": 42,
  "eventType": "hotel.updated",
  "occurredAt": "2026-10-27T12:00:00Z",
  "payload": {
    "name": "Grand Old Town Residence",
    "city": "Vilnius"
  }
}
```

Now simulate arrival in this order: version 42, version 41, version 42 again.

Explain how the consumer preserves the newest state and avoids duplicate effects.

Add a deletion event and explain how you would prevent delayed older updates from resurrecting the deleted hotel.

### Lab F — Evaluate a shard key

Assume a tenant-event collection receives several million events daily.

Most tenants are small, but a few generate disproportionate traffic.

Evaluate these candidate keys:

- Tenant ID.
- Event timestamp.
- Hashed event ID.
- A compound key combining tenant identity with an appropriate additional distribution dimension.

For each, examine write distribution, query targeting, hotspots, cardinality, and operational complexity.

Do not select a key merely because it distributes inserts evenly.

Explain what happens to the most important read queries.

### Lab G — Define the failure matrix

Construct a matrix for the following failures:

- Redis unavailable.
- Search index unavailable.
- MongoDB primary election.
- PostgreSQL primary loss.
- Analytics ingestion delayed.
- CDC consumer offline beyond retained history.
- One cloud availability zone unavailable.
- Entire cloud region unavailable.

For each, specify whether browsing, booking, catalogue administration, and analytics remain available.

Then identify which failures risk data loss, which merely cause stale derived data, and which require reconciliation.

### Lab H — Design a recovery procedure

Choose one derived system, such as Elasticsearch.

Assume its entire index has been lost.

Write a recovery procedure that:

1. Establishes a trustworthy authoritative baseline.
2. Captures changes occurring during the rebuild.
3. Recreates the index.
4. Applies outstanding changes.
5. Verifies completeness and consistency.
6. Switches production reads safely.

Explain what evidence would persuade you that the rebuilt index is ready.

### Lab I — Present the architecture to management

Prepare a ten-minute oral architecture review.

Your presentation must explain:

- The problem being solved.
- The systems retained and introduced.
- Data ownership.
- Correctness and durability requirements.
- Query and indexing strategy.
- Synchronization and recovery.
- Scaling triggers.
- Operating costs.
- The technologies deliberately rejected.

Assume the CTO interrupts halfway through and asks you to reduce infrastructure costs by thirty percent.

What would you simplify first without sacrificing critical business correctness?

The goal is not to present a beautiful diagram.

It's to defend an engineering decision.

---

## Further Reading — Optional Technical References

1. [PostgreSQL — Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html) — Database isolation and transactional behavior.
2. [PostgreSQL — Warm Standby and Streaming Replication](https://www.postgresql.org/docs/current/warm-standby.html) — Replication and failover trade-offs.
3. [MongoDB — Data Modeling](https://www.mongodb.com/docs/manual/data-modeling/) — Document boundaries and access patterns.
4. [MongoDB — Change Streams](https://www.mongodb.com/docs/manual/changeStreams/) — Change capture, resumption, and relevant limitations.
5. [MongoDB — Replica Set Rollbacks](https://www.mongodb.com/docs/manual/core/replica-set-rollbacks/) — Divergent histories and acknowledgment guarantees.
6. [MongoDB — Sharding](https://www.mongodb.com/docs/manual/sharding/) — Data placement and query routing.
7. [AWS — DynamoDB Read Consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html) — Eventual and strong reads.
8. [Elastic — Near Real-Time Search](https://www.elastic.co/docs/manage-data/data-store/near-real-time-search) — Search refresh visibility.
9. [Redis — Key Eviction](https://redis.io/docs/latest/develop/reference/eviction/) — Expiration, memory limits, and eviction policies.
10. [ClickHouse — MergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/mergetree) — Columnar analytical storage and ordering.
11. [Debezium — Documentation](https://debezium.io/documentation/) — Change data capture and derived data pipelines.
12. Martin Kleppmann, *Designing Data-Intensive Applications* — Storage, replication, consistency, partitioning, and distributed data architecture.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced for voice-reader skipping. Use this card for rapid interview revision and return to the relevant sections only when a concept needs rebuilding.*

```text
CS340-L07 — DATA ARCHITECTURE WORKSHOP / INTERVIEW GLANCE CARD

FIRST QUESTIONS
  What is the product? Which operations matter most?
  What scale NOW vs forecast?
  Latency / throughput / availability requirements?
  RPO / RTO agreed with business?
  Which invariants must NEVER be violated?
  Which data can be stale, lost, or rebuilt?
  Which workloads are already bottlenecked?

AUTHORITY
  One business fact → one defined authority/workflow.
  PostgreSQL  reservations / inventory / financial application state
  MongoDB     current hotel catalogue (if existing system justified)
  Search      DERIVED view of catalogue
  Redis       optional cache or specialized short-lived state
  Analytics   DERIVED events and aggregates
  Payment API external payment outcome; reconcile with local workflow

  Derived copies != competing sources of truth.
  Deletion, updates, replay, and backfill must be defined.

BOOKING CORRECTNESS
  Read inventory → unconditional write = RACE.
  Conditional atomic update or transaction enforces capacity.
  Multi-date booking → coordinate every required inventory record.
  Keep external payment request OUTSIDE long DB transaction.
  Reservation states: pending/held/confirmed/cancelled/expired.
  Idempotency key + durable unique operation identity.
  Timeout != failed payment or reservation.
  Reconcile uncertain external outcomes.
  Historical agreed price/terms must survive catalogue changes.

CONSISTENCY & DURABILITY
  Local durable commit != remote replica has committed it.
  Async failover can lose acknowledged primary writes.
  Stronger replication/ack requirements may cost latency/availability.
  Secondary read can be stale.
  Read-your-writes needs suitable read path/session consistency.
  Replication != backup.
  Backups need verified restoration and agreed RPO/RTO.
  More replicas ≠ unlimited write scale.

DOCUMENT BOUNDARIES
  Embed bounded, owned, jointly read/updated attributes.
  Reference independent, unbounded, frequently updated entities.
  100k reviews inside one hotel document = bad aggregate.
  Historical booking snapshot = intentional duplication.
  Atomic document update ≠ atomic arbitrary read-modify-write.
  Conditional update/version guard prevents stale writes.

INDEXES & QUERY WORK
  Query shape determines useful access path.
  Selectivity + sort + range + projection matter.
  Index used ≠ index efficient.
  EXPLAIN keys examined / docs examined / returned.
  Compound prefix order matters.
  Multikey array semantics may require $elemMatch.
  Blocking sort/group/unwind/lookup can magnify work.
  Every index adds write/storage/maintenance cost.

SHARDING
  Replication = copies; sharding = data distribution.
  Only shard when measured workload/capacity requires it.
  Shard key: cardinality, frequency, monotonicity, query patterns.
  Timestamp range → new-write hotspot risk.
  Tenant ID → large tenant hotspot risk.
  Hashing distributes suitable keys, weakens original range locality.
  Targeted query uses shard key.
  Missing shard key → scatter-gather even with local indexes.
  Cross-shard transaction → coordination cost.
  Resharding possible, not free.

CACHING
  Cache is derived, not authoritative booking state.
  Cache key must include relevant variation/isolation.
  TTL expiration vs memory-pressure eviction.
  Cache miss storm can crush source database.
  Bounded fallback, coalescing, safe stale reuse, load shedding.
  Never trust cached search availability as booking authority.

SEARCH / CDC
  Search index = derived representation, possibly stale.
  Relevance != authoritative inventory.
  Source commit + direct index update = dual-write failure window.
  Change stream/CDC captures authoritative changes.
  Initial backfill + ongoing capture must have NO GAP.
  Resume token may expire with source history.
  Consumer must handle duplicates, ordering, deletions.
  Version-aware updates prevent old event overwriting new state.
  Rebuild/reconcile path is mandatory.

ANALYTICS
  OLTP = transactions; OLAP = large historical scans/aggregations.
  Columnar store reads selected fields efficiently.
  Browser "booking succeeded" event != authoritative sale.
  Stable event IDs for dedupe.
  Ingestion lag and replay need monitoring.
  Retention, backfill, schema evolution must be planned.
  Analytical outage shouldn't block reservations.

INCIDENT IDENTIFICATION
  Hotel old name in search → derived index lag/order, not booking DB.
  Booking missing after failover → ack/replication/recovery boundary.
  Analytics double count → duplicate delivery/idempotency.
  Redis down + DB collapse → uncontrolled fallback/cache stampede.
  Hot shard → data distribution, not total machine count.
  High query time → examine physical work BEFORE adding servers.

EVOLUTION TRIGGERS
  Add Redis         measured reusable low-latency access pattern
  Add search engine linguistic ranking beyond current tools
  Add analytical DB huge scans interfering with OLTP
  Add DynamoDB      predictable key-oriented workload benefits
  Add sharding      measured per-node capacity/throughput limitation
  Add multi-region  approved recovery / availability requirement
  Add graph DB      important repeated multi-hop traversal workloads

WHAT NOT TO DO
  Don't introduce a technology merely because it's fashionable.
  Don't confuse replica count with write capacity.
  Don't use cache as reservation authority.
  Don't assume CDC equals exactly-once delivery.
  Don't assume majority/local durability covers every disaster.
  Don't optimize hypothetical future load before measuring.
  Don't call an architecture complete without recovery testing.

SEVEN QUESTIONS
  1. Who owns the truth?
  2. What access patterns dominate?
  3. What must change atomically?
  4. What staleness is acceptable?
  5. Which physical operations determine cost?
  6. How does each boundary fail?
  7. How can every critical or derived state be recovered?

SENIOR LINE
  "I start with business invariants and access patterns, keep clear
   authoritative ownership, introduce specialized derived systems only
   when their benefits justify the operational cost, and design for
   synchronization failure and recovery from the beginning."
```
