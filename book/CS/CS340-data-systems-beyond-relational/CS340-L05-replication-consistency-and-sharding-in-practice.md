---
id: CS340-L05
course: CS340
title: "Replication, Consistency, and Sharding in Practice"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: CS340-L04
next: CS340-L06
---





# CS340 — Data Systems Beyond Relational Databases

## Lecture 05: Replication, Consistency, and Sharding in Practice

*Why a successful database write can disappear, why replicas sometimes disagree, and how distributing information across machines turns ordinary data operations into coordination problems.*

---

# 1. The Reservation That Disappeared After Being Confirmed

It's Friday evening, and our hotel-booking platform is experiencing a problem that should be impossible.

A customer reserves a room in Berlin.

The backend receives the request, checks availability, creates the reservation in MongoDB, and receives an acknowledgment indicating that the database write succeeded.

The application returns a confirmation.

The customer sees their reservation number.

Everything looks correct.

Twenty seconds later, the customer refreshes the page.

The reservation has disappeared.

Customer support searches for the reservation identifier and finds nothing.

The application logs clearly show that the insert operation succeeded. MongoDB returned an acknowledgment. No exception was thrown.

One developer suspects a frontend caching bug. Another believes someone accidentally deleted the record. A third wants to investigate the ORM, although we're not even using one.

Then the infrastructure team reports that a database server restarted shortly after the reservation was created.

That sounds suspicious, but it still doesn't fully explain the disappearance.

A database should survive a server restart.

After all, isn't durability one of the fundamental reasons we use databases?

The answer is that **local durability and replicated durability are not identical guarantees**.

Our application uses a MongoDB replica set.

The write reached the primary node, but the application had requested acknowledgment after only that node accepted the operation. Before the write propagated to another replica, the primary became unavailable.

The remaining members elected a new primary that had never received the reservation.

When the original primary eventually rejoined the replica set, it had to reconcile its divergent history with the newly established authoritative history.

The unreplicated write was rolled back.

The application had received a successful acknowledgment under the guarantee it requested.

That guarantee was weaker than the business operation required.

This incident introduces a crucial distinction.

**A successful database operation means that certain conditions were satisfied. It does not tell you which conditions unless you understand the acknowledgment contract.**

Today we'll investigate those contracts.

We'll follow writes through MongoDB replica sets, examine how elections work, discover why secondary reads can return outdated information, and learn how applications choose between freshness, durability, and availability.

Then we'll tackle a separate problem.

What happens when one database server no longer has enough storage or processing capacity for the workload?

We'll introduce sharding, explore how MongoDB distributes collections across machines, and discover why the wrong shard key can make a large cluster behave like one overloaded server.

By the end, you should understand why adding machines does not automatically make data safer, fresher, or faster.

It creates possibilities.

Correctness depends on how we use them.

---

# 2. Replication: Several Copies of One Logical Database

Let's begin with the simplest possible database deployment.

One server stores the data.

Every application request communicates with that server.

This architecture is easy to understand.

But it has obvious limitations.

If the machine fails, the application may lose database availability until the machine recovers or another recovery mechanism restores service.

If storage is permanently lost, recovery depends on backups and any other durable copies.

And if all reads and writes must be processed by one machine, its resources may eventually become a bottleneck.

**Replication** creates additional copies of data on other machines.

Instead of having one server holding the only relevant database state, several servers maintain representations of the same logical dataset.

This can improve resilience and support certain read-distribution strategies.

But replication immediately creates a new question.

If several machines store the data, how do they agree on what the data actually is?

## 2.1 Three copies are not necessarily three independent opinions

Imagine three database servers.

Each stores the reservation collection.

A customer creates a reservation.

Should the application send the write independently to all three?

And what if one server accepts it while another rejects it?

What if two customers attempt conflicting updates at the same moment?

If every copy can independently become authoritative, the system needs rules for reconciling concurrent changes.

Different database architectures solve this problem differently.

Some use leader-based replication. Others use leaderless or multi-leader approaches, each with its own conflict-resolution mechanisms.

MongoDB replica sets use a leader-based model.

One member normally acts as the **primary**, and other data-bearing members act as **secondaries**.

The primary receives ordinary write operations.

Secondaries replicate and apply changes originating from the primary.

The application therefore has one ordinary write authority for each replica set at a given time, rather than several independently writable copies.

That simplifies certain consistency problems.

But it does not eliminate distributed-system failure.

## 2.2 The MongoDB replica set

Consider three members named A, B, and C.

A is the primary.

B and C are secondaries.

The client sends a reservation insert to A.

A applies the write and records the relevant replication operation in its **oplog**, short for operations log.

The secondaries obtain operations from the replication stream and apply them to their own data.

Conceptually:

```text
                 Application
                      |
                    WRITE
                      |
                      v
               A — PRIMARY
                /         \
          Replication   Replication
              /             \
             v               v
       B — SECONDARY    C — SECONDARY
```

The oplog allows secondary members to follow the sequence of operations needed to maintain their copies.

But don't confuse the oplog with the storage engine's ordinary recovery journal.

In CS340-L02, we examined write-ahead logging and local crash recovery.

MongoDB's replication oplog serves a different purpose: communicating changes between replica set members.

The underlying storage engine also has mechanisms for local durability.

These are related, but distinct layers.

One concerns recovering a node's local state.

The other concerns keeping multiple nodes synchronized.

---

# 3. The Dangerous Gap Between Writing and Replicating

Now consider the customer's reservation.

The primary receives the insert.

At that moment, there are several possible states.

The primary may have accepted the operation locally.

It may have recorded the corresponding oplog entry.

One secondary may have received the entry.

Another may not.

The replication information may be durable on some members but not others, depending on configuration and progress.

Eventually, all healthy members may converge on the same state.

But the interval between the initial write and wider replication is important.

## 3.1 Replication is not instantaneous

Imagine that A applies a write.

B receives the corresponding operation five milliseconds later.

C receives it twenty milliseconds later.

For a short period, the members hold different states.

A knows about the reservation.

B may know about it.

C might still show the old database state.

This is **replication lag**.

Even when the network is fast, the secondaries must receive and process operations.

Under load, lag can become more substantial.

A secondary might have slower storage, limited CPU capacity, or insufficient replication throughput.

The application should not assume that every replica contains a new write immediately after the primary accepts it.

## 3.2 The primary disappears at the worst possible moment

Return to our three-node example.

A receives a reservation write.

The application requests acknowledgment under a weak write concern.

A acknowledges the operation.

Before B or C receives it, A becomes isolated.

B and C can communicate with one another.

They form a majority of the replica set's voting membership and can elect a new primary.

Suppose B becomes the new primary.

B's history doesn't contain the reservation.

Neither does C's.

From the surviving majority's perspective, that operation never became part of the replicated history they are continuing.

When A rejoins, it must reconcile its divergent history.

The reservation may be rolled back.

This is how a database can acknowledge a write and later remove it during failover.

The acknowledgment wasn't necessarily dishonest.

The application requested a guarantee that didn't require the write to survive this failure scenario.

The solution begins with understanding **write concern**.

---

# 4. Write Concern: What Must Happen Before the Database Says Success?

MongoDB's **write concern** describes the level of acknowledgment requested for a write operation.

It answers an essential question:

"How far must this operation progress before the client may treat the write as acknowledged?"

There are several configurations, but three ideas matter most.

## 4.1 Acknowledgment from the primary

A write concern of `w: 1` requests acknowledgment from one data-bearing member, normally the primary handling the write.

In a typical replica set, this does not require acknowledgment from a secondary.

It can provide lower acknowledgment latency than waiting for replication to multiple members.

But there's a cost.

If the primary becomes unavailable before the write is sufficiently replicated, the operation can be rolled back during failover.

For certain workloads, that risk might be acceptable.

Imagine an analytics event that can be regenerated or whose occasional loss doesn't materially harm the business.

A weaker acknowledgment policy might be considered, depending on the architecture.

But consider a confirmed hotel reservation or financial record.

Acknowledging a business operation that may disappear during ordinary failover is much harder to justify.

The appropriate choice depends on the business guarantee.

## 4.2 Majority acknowledgment

MongoDB supports write concern `w: "majority"`.

In a conventional three-member replica set with three voting data-bearing nodes, majority acknowledgment requires the write to reach the relevant majority acknowledgment condition—typically the primary and at least one secondary.

MongoDB's exact acknowledgment and journaling behavior depends on version and configuration.

With the usual journaling configuration, majority acknowledgment provides much stronger protection against losing acknowledged writes during ordinary replica-set failover.

Why?

Because a future primary must be elected through a voting majority.

Any two majorities of a fixed three-member set overlap.

A write sufficiently committed through the replica set's majority protocol cannot simply be replaced by an unrelated history chosen by another disjoint majority.

This is one of the deep mathematical ideas behind majority-based coordination.

**Majorities overlap, so a correctly enforced majority-commit protocol can preserve committed history across leadership changes.**

But don't assume that majority means "all replicas."

It doesn't.

One secondary may remain behind while the write is acknowledged.

Nor should we pretend majority acknowledgment protects against every conceivable disaster.

Correlated storage failures, incorrect durability configurations, destructive administrative operations, and other exceptional circumstances still require separate consideration.

## 4.3 Journaling and `j`

MongoDB write concern can also include a journaling requirement through the `j` option.

The purpose is to request acknowledgment related to the write reaching the on-disk journal.

This relates to local crash durability.

A write acknowledged in memory is not necessarily equivalent to one whose required persistent journal information has been synchronized.

With majority write concern, journaling behavior is also influenced by the replica set's `writeConcernMajorityJournalDefault` configuration, which normally defaults to true.

For ordinary deployments, a majority write concern with standard journaling settings provides a strong and practical durability baseline.

But remember the conceptual distinction.

The `w` setting concerns acknowledgment across members.

The `j` setting concerns journal persistence behavior.

A locally journaled write can still be rolled back if it hasn't become part of the history preserved through failover.

And a replicated write's durability depends on the exact acknowledgment and journal policies being used.

## 4.4 Write concern timeouts don't undo writes

Suppose the application requests majority acknowledgment.

The primary performs the write.

But a secondary is slow, and the majority acknowledgment condition isn't satisfied before the configured write-concern timeout.

MongoDB returns a write concern error.

Does that mean the write was undone?

No.

The primary may already have applied it.

It may eventually propagate successfully.

The write-concern timeout places a bound on how long the client waits for the requested acknowledgment.

It does not automatically reverse modifications already performed.

We've encountered this principle before.

**A timeout tells the caller that the required confirmation wasn't obtained in time. It does not necessarily tell the caller the operation failed.**

For reservation creation, that uncertainty must be handled through durable operation identities, idempotency, and reconciliation.

---

# 5. Elections: Who Gets to Become the New Primary?

Suppose our primary server fails.

We have two secondaries.

Which one becomes the new primary?

The process involves **replica set elections**.

Members exchange information about their state and availability.

Eligible members can vote in elections.

A candidate needs the required voting majority to become primary.

Election rules also consider conditions such as candidate eligibility and replication progress.

The details are more sophisticated than simply selecting whichever server responds first.

But the central purpose is understandable.

The replica set needs to establish a new write authority without allowing arbitrary disconnected minorities to independently create incompatible authoritative histories.

## 5.1 Why an odd number of voting members is useful

Imagine two voting members.

One is primary, and the other is secondary.

If one disappears, the remaining member alone does not form a majority of the original two-member voting configuration.

The set cannot simply elect a new primary using only one vote.

Now consider three voting members.

A majority is two.

If one member fails, the remaining two can still form a majority.

This is one reason three-member replica sets are a common production configuration.

But there is a nuance.

MongoDB supports **arbiters**, which participate in elections without storing a copy of the user data.

An arbiter can help voting topology, but it doesn't provide another durable data copy.

A primary-secondary-arbiter configuration therefore has different durability and write-availability characteristics from three data-bearing members.

In general, if the objective is stronger replication durability and resilience, three data-bearing members are more attractive than two data-bearing members and one arbiter, assuming the operational cost is acceptable.

## 5.2 The network partition problem

Imagine a five-member replica set divided into two groups.

Three members can communicate with one another.

The other two are isolated from that group.

The larger group can form a voting majority and elect a primary.

The smaller group cannot independently elect a new legitimate primary.

However, distributed systems have an uncomfortable property.

An old primary might not immediately realize that it has lost contact with the majority or that another member has been elected.

For a transient period, multiple nodes may believe they hold primary authority.

That is why the distinction between weak local write acknowledgment and majority acknowledgment is so important.

An isolated former primary might still acknowledge certain weaker writes before recognizing its changed state.

Those writes can later be rolled back.

But it cannot satisfy the legitimate majority write condition without the necessary participating members.

The system's safety comes from the coordination rules, not merely from each node's opinion about its role.

---

# 6. Read Preference: Which Copy Should Answer the Question?

We've discussed where writes go.

Now consider reads.

Our booking frontend retrieves a customer's reservation list.

Should it always read from the primary?

Or could it query a secondary?

MongoDB uses **read preference** to control which replica set members are eligible to handle a read.

The default preference is normally `primary`.

Other modes can prefer or require secondary reads, depending on the application's needs and deployment behavior.

This creates opportunities.

It also creates freshness problems.

## 6.1 Reading from a secondary

Suppose the primary has just accepted a new reservation.

Secondary B has received and applied the update.

Secondary C is still behind.

The frontend performs a read directed toward C.

It might receive a result that doesn't include the latest reservation.

Nothing has necessarily disappeared.

The replica simply hasn't applied the latest information yet.

This is a **stale read**.

The database is returning a state that was valid earlier.

For some workloads, that can be acceptable.

Imagine an administrative dashboard displaying approximate historical statistics.

A small amount of lag may be harmless.

But a customer who has just confirmed a reservation expects to see it immediately.

Reading from a lagging secondary can violate that expectation.

## 6.2 Why reading from the primary isn't an absolute freshness guarantee

It's tempting to solve the problem by saying:

"Read from the primary, and you'll always get the latest truth."

That is a useful default in many applications, but it isn't a universal guarantee under every failure scenario.

During a network partition and leadership transition, an old primary may temporarily believe it is still primary.

A read directed to that member may observe a state that isn't part of the newly established majority history.

For stronger real-time guarantees, we need to discuss **read concern**, not merely read preference.

The distinction is important.

Read preference chooses *where the read may execute*.

Read concern defines *which consistency properties the read requests*.

They're different dimensions.

---

# 7. Read Concern: Which Version of Reality May We Observe?

MongoDB supports several read concern levels.

We don't need to memorize every edge case, but we should understand the major guarantees they represent.

## 7.1 Local reads

Read concern `local` allows a read to return data from the selected member's local state, without requiring that the returned information has achieved majority-commit durability.

That can provide useful availability and performance properties.

But the result may include changes that could later be rolled back.

On a secondary, it may also be stale because replication is asynchronous.

For ordinary operational reads, local concern can be useful.

But it doesn't provide the strongest correctness guarantee.

## 7.2 Majority reads

Read concern `majority` returns data from a majority-committed view.

This helps avoid exposing operations that may later be rolled back during ordinary failover under the intended guarantees.

However, **majority does not mean freshest possible**.

A secondary may lag behind the latest committed state.

A majority read can therefore be consistent with an older majority-committed snapshot.

There's a particularly important MongoDB version detail here.

Starting with MongoDB 8.0, majority write acknowledgment can occur after the relevant oplog entries have been durably written by enough members, while secondary application of those operations continues asynchronously.

Consequently, a secondary queried immediately afterward may not yet expose the corresponding document changes.

Majority acknowledgment does not mean every secondary has already applied the write to its queryable collection state.

This is exactly why reading your own recent writes deserves explicit attention.

## 7.3 Linearizable reads

MongoDB also provides `linearizable` read concern for supported single-document read operations on the primary.

Under its requirements, it provides stronger real-time ordering guarantees relative to successfully majority-acknowledged writes that completed before the read began.

Conceptually, linearizability asks us to behave as though operations occurred in one order compatible with their real-time relationships.

If a qualifying write completed before a qualifying read began, the read should not act as though that write had never occurred.

But stronger guarantees have costs.

Linearizable reads may need additional coordination and can become slower or unavailable when the necessary replica-set conditions cannot be satisfied.

MongoDB recommends bounding such operations with an appropriate maximum execution time.

And the guarantee applies within the documented scope; it isn't a magic switch making every arbitrary distributed query globally linearizable.

The important lesson is that consistency guarantees have precise meanings.

Use them according to the operation's requirements.

---

# 8. Causal Consistency: The Customer Must See Their Own Reservation

Now let's solve a more realistic application problem.

A customer creates a reservation.

The request succeeds with majority write concern.

Immediately afterward, the frontend opens the reservation-details page.

The read may be served by a secondary.

The application wants to preserve a simple expectation:

"If I just created this reservation, I should be able to see it."

This is commonly called **read-your-writes consistency**.

It's one part of a broader concept called causal consistency.

## 8.1 What causality means

Imagine a sequence of operations.

First, a customer creates a reservation.

Second, the application queries that customer's reservations.

The second operation logically depends on the first.

A causally consistent system should not allow the second operation to observe a state that predates the first in a way that violates the supported causal ordering guarantee.

There are several related properties, including monotonic reads and monotonic writes.

Monotonic reads mean a client's later reads should not move backward in the causal history it has already observed.

Monotonic writes preserve the order of writes performed within the causal context.

These guarantees are useful when an application moves between replica members.

## 8.2 MongoDB sessions

MongoDB supports causally consistent client sessions.

When the application uses the documented requirements—including majority read concern and majority write concern—operations within a causally consistent session can preserve the relevant causal relationships.

The session communicates information about the causal history the client has already observed.

The database can use that information to ensure a subsequent read is not served from a state too old to satisfy the session's requirements.

The result may involve waiting for a secondary to catch up.

That is a trade-off.

The application asks for stronger consistency, and the system may need additional time to provide it.

There is also an architectural subtlety.

A database session object isn't automatically a business session in the web-application sense.

If a browser creates a reservation through one HTTP request and later opens another endpoint handled by a different application instance, the application must deliberately preserve whatever causal context the database guarantee requires.

Merely enabling causally consistent sessions somewhere in a driver does not automatically coordinate unrelated API requests.

## 8.3 When to read from the primary instead

For many ordinary transactional workflows, reading from the primary is a reasonable starting point.

It simplifies the architecture and avoids certain secondary-lag surprises.

But it doesn't eliminate the need to understand failure transitions or the exact guarantees required.

The right decision depends on the workload.

If the application needs strictly ordered observations of a particular document, stronger read semantics may be appropriate.

If a dashboard can tolerate a few seconds of staleness, secondary reads may be acceptable.

If the user must observe their own writes across different members, causal consistency can provide a suitable mechanism within its documented scope.

**Don't ask whether the database is strongly consistent. Ask which operation needs which guarantee, and how the application obtains it.**

---

# 9. Failover From the Application's Perspective

We've examined the database's internal behavior.

Now imagine what the Node.js backend experiences during an election.

The application has a connection pool.

It sends a reservation write.

The primary becomes unavailable.

Some operations fail.

Others may time out.

The driver discovers changes in the replica-set topology and attempts to identify the current primary.

For a period, the application may have no writable primary available.

Then a new member becomes primary.

Connectivity resumes.

From the application's perspective, this looks like an intermittent dependency outage.

But correctness requires more than reconnecting.

## 9.1 Retryable writes

MongoDB drivers support retryable writes for eligible operations under appropriate configurations.

The driver can retry certain failures using operation identifiers and server-side mechanisms designed to avoid unintended duplicate execution within the supported guarantees.

This is useful during transient network problems and failovers.

But not every operation is retryable, and not every error means the operation definitely failed.

Retry support has defined limits and conditions.

We should not assume that enabling retries turns an arbitrary business workflow into exactly-once execution.

For example, a reservation workflow might involve several database writes, an external payment provider, and a notification service.

Those side effects do not all become atomic because the database driver can retry one eligible write.

## 9.2 Unknown transaction outcomes

MongoDB transactions introduce another important category of uncertainty.

Imagine the application commits a transaction.

The server processes the commit.

But the connection fails before the client receives a definitive result.

The client may not know whether the transaction committed.

MongoDB drivers expose error labels and transaction APIs that help applications distinguish situations where retrying the transaction body or retrying commit is appropriate.

For example, `TransientTransactionError` and `UnknownTransactionCommitResult` convey different kinds of retry guidance.

Convenience transaction APIs can automate parts of this behavior.

But the business operation still needs a durable identity.

If the application abandons the original reservation operation and begins a new one with a different business identifier, it may still create duplicates or inconsistent external side effects.

Transport retries, database transaction retries, and business idempotency are related but distinct mechanisms.

## 9.3 Availability doesn't mean every operation must succeed

During failover, some writes may temporarily be unavailable.

A stronger write concern may require acknowledgment conditions that cannot currently be satisfied.

That's not necessarily a defect.

The system is refusing to claim a guarantee it cannot provide.

For an analytics event, the application might buffer data temporarily.

For reservation creation, it might return an honest pending or unavailable result rather than pretending that an unconfirmed operation succeeded.

Business correctness sometimes requires choosing temporary unavailability over falsely reporting success.

That is an architectural decision.

---

# 10. Replication Is Not Sharding

We've now covered replication.

Several machines maintain copies of the same logical data.

But suppose the dataset becomes enormous.

Our travel platform stores billions of events and hundreds of millions of other documents.

One server no longer has sufficient storage or processing capacity to handle the workload.

Would adding more replicas solve the problem?

Not necessarily.

Each ordinary replica set member stores the replicated dataset.

More replicas can improve fault tolerance and potentially support certain read workloads.

But every replica still needs enough capacity to store its copy.

And writes are still coordinated through the primary of that replica set.

If the goal is to distribute the underlying data across machines, we need a different mechanism.

**Sharding** partitions data.

Instead of every machine storing the same dataset, different machines store different subsets.

Imagine dividing the hotel catalogue geographically.

One shard might store some hotel records.

Another stores a different subset.

A third stores yet another.

Now the complete dataset is distributed across multiple storage groups.

This can improve total storage capacity and distribute workload.

But the partitioning rules become part of the application's performance and correctness model.

Replication asks:

"How do we maintain copies of data safely?"

Sharding asks:

"How do we divide data and work among multiple systems?"

A sophisticated deployment often combines both.

---

# 11. A MongoDB Sharded Cluster

MongoDB sharded clusters contain several important components.

First are the **shards**.

Each shard stores a subset of the sharded collection's data.

Modern MongoDB shards are deployed as replica sets, so each shard can have its own primary and secondary members.

Second are **mongos routers**.

Applications can connect through mongos, which uses sharding metadata to route operations toward the appropriate shards.

Third are **config servers**.

They maintain metadata describing the organization of sharded data, including which shard owns which key ranges.

MongoDB 8.0 also introduced configurations in which a config shard can combine certain metadata and application-data roles, but the conceptual responsibilities remain useful to distinguish.

The application therefore doesn't need to manually calculate a physical destination for every document.

MongoDB's routing layer can make that decision based on the collection's sharding configuration.

## 11.1 The shard key

A sharded collection uses a **shard key** to determine how its documents are distributed.

This may be one field or a compound set of fields, subject to MongoDB's rules.

The system partitions shard-key values into ranges.

Those ranges are associated with chunks or related data-placement structures managed by the cluster.

A balancer can move data between shards to improve distribution according to the system's balancing rules.

But this raises the most important design question in sharding.

**Which field should determine where a document lives?**

The answer affects not only storage distribution but also the efficiency of future reads and writes.

## 11.2 A shard key is a workload decision

Suppose our collection contains hotel-search events.

We could shard by event timestamp.

That sounds reasonable because the data is time-oriented.

But timestamps increase monotonically.

New events continually arrive with later timestamps.

In a simple range-based partitioning scheme, new writes tend to concentrate in the shard owning the highest active key range.

Instead of distributing incoming work evenly, the architecture creates a hot shard.

We have several servers.

But the newest writes are still focused on one location.

That's a design problem.

More machines don't automatically improve throughput when the partitioning rule sends most work to the same one.

---

# 12. Range-Based Versus Hashed Sharding

MongoDB supports different shard-key distribution approaches, including range-based and hashed sharding.

Each favors different access patterns.

## 12.1 Range-based sharding

Imagine using hotel ID as an ordered shard key.

One shard owns an earlier range of IDs.

Another owns the next range.

And so on.

A query asking for documents within a contiguous range can potentially target the shards owning those values.

This can be useful for range-oriented queries.

But if new IDs increase monotonically, new inserts may concentrate near the end of the key space.

The system needs to manage that concentration.

Range-based sharding preserves useful locality but can create hotspots.

## 12.2 Hashed sharding

Now imagine hashing a suitable shard-key value.

The hash transforms the original key into a value used for distribution.

Sequential original values can become spread across the hashed key space.

That can help distribute writes more evenly.

But hashing changes which queries can efficiently identify a small set of shards.

If the application frequently requests a contiguous range of original values, those values may be scattered across many hashed partitions.

The router may need to contact several shards.

We have improved distribution at the expense of some locality.

This is a classic engineering trade-off.

Range-based sharding can preserve useful ordering.

Hashed sharding can improve distribution for suitable workloads.

Neither is universally better.

## 12.3 The tenant-ID trap

Now consider a multi-tenant SaaS platform.

An engineer proposes sharding by tenant ID.

That could be useful because many queries naturally include the tenant identifier.

The router may be able to target the relevant shard.

But imagine that one customer is enormous.

That tenant generates more traffic than hundreds of smaller customers combined.

If all its records map to the same indivisible shard-key value, hashing the tenant ID doesn't automatically distribute that one tenant's workload.

The same hashed value still belongs to one place.

The system may need a more sophisticated partitioning strategy, perhaps involving a compound key or a model that divides large tenants' workloads deliberately.

But that introduces new query and consistency costs.

The correct shard key must reflect the distribution of actual work, not merely the distribution of customer names.

---

# 13. The Three Properties of a Useful Shard Key

When evaluating a MongoDB shard key, three concepts are especially valuable.

**Cardinality** describes how many distinct key values are available.

**Frequency** describes how often particular values occur.

**Monotonicity** describes whether new values tend to move continually in one direction.

These properties influence how effectively data and workload can be distributed.

## 13.1 High cardinality

Imagine sharding hotels by continent.

There are only a handful of possible values.

That limits the number of distinct key ranges that can be distributed effectively.

If millions of documents share one exact shard-key value, the system cannot divide that value arbitrarily between ordinary ranges without changing the partitioning design.

A key with more distinct values can provide more flexibility.

But high cardinality alone isn't sufficient.

## 13.2 Uneven frequency

Suppose hotel traffic is distributed across thousands of cities.

Most cities generate modest traffic.

But London and Paris account for a disproportionate share of requests.

A city-based shard key may distribute storage unevenly.

The hot cities can overload their respective shards.

The number of distinct city values might be large, yet a few values dominate the actual workload.

We must examine frequency, not just cardinality.

## 13.3 Monotonically increasing values

Now return to timestamps.

Every new event receives a later timestamp.

If the active insertion range belongs to one shard, incoming writes become concentrated there.

MongoDB can split and move ranges under appropriate conditions, but the underlying pattern still creates a hotspot tendency.

The cluster may continually chase the newest range.

This is why monotonically increasing shard keys deserve careful consideration.

A shard key determines not only where data exists today, but where future data will arrive.

---

# 14. Targeted Queries Versus Scatter-Gather

Now we arrive at one of the biggest surprises in sharded database performance.

Imagine our hotel collection is distributed across eight shards.

A customer requests a hotel by an appropriate shard-key value.

The mongos router can determine which shard owns the corresponding key range.

It sends the operation toward that shard.

This is a **targeted operation**.

Now imagine a query filtering only by a field unrelated to the shard key.

The router may not know which shard contains the matching documents.

It may need to send the query to every shard and combine the results.

This is called **scatter-gather**.

## 14.1 Why scatter-gather can become expensive

Imagine a query returning one hotel.

In a single-server database, a suitable index might find that hotel efficiently.

In an eight-shard cluster, if the router cannot identify the relevant shard from the query, it may send the request to all eight shards.

Each shard performs its own work.

The router waits for and combines responses.

Even if every shard has an appropriate local index, the operation has become a distributed query.

It consumes resources on several machines and introduces network and coordination overhead.

Sharding may increase total system capacity.

But it can also make individual queries more expensive when their access patterns don't align with the partitioning scheme.

## 14.2 Scatter-gather isn't always bad

For analytical operations that genuinely need data from every shard, parallel work can be useful.

Imagine calculating a global aggregate across the complete collection.

Each shard may compute part of the result.

The system can merge partial aggregates.

That can reduce elapsed time compared with executing all work on one server, depending on the workload and resources.

The problem isn't that contacting multiple shards is inherently wrong.

The problem is making a highly selective point lookup contact every shard because the routing architecture lacks enough information to target it.

**Sharding improves performance when data placement and query patterns cooperate.**

## 14.3 The index misconception

Here's another subtle point.

A collection may have an index on hotel ID inside every shard.

But if the collection is sharded by another field and the query doesn't provide shard-key information, the router may still need to consult multiple shards.

The local index makes each shard's work cheaper.

It doesn't automatically tell mongos which shard owns the requested hotel.

Query routing and local indexing are two different optimization problems.

This distinction is easy to miss if you've only worked with databases running on one machine.

---

# 15. Balancing, Jumbo Chunks, and the Cost of Changing Your Mind

Suppose our sharded cluster grows.

Some shards become larger than others.

MongoDB's balancing mechanisms can redistribute data to improve placement.

The cluster may move chunks or ranges between shards.

But moving data isn't free.

It consumes storage I/O, network bandwidth, and coordination work.

The system must preserve correctness while ownership changes.

## 15.1 When a range can't be split effectively

Imagine a shard-key value shared by an enormous number of documents.

If all those documents have the same complete shard-key value, there may be no suitable split point within that value.

The associated range can become unusually large.

MongoDB refers to certain oversized unsplittable ranges as **jumbo chunks**, and they can complicate balancing.

The system cannot solve every pathological data distribution by moving arbitrary portions of one indivisible key value.

That is why shard-key cardinality and frequency matter so much.

The data model determines which divisions are possible.

## 15.2 Can we change the shard key later?

Yes, MongoDB supports mechanisms for changing or refining shard-key strategies under appropriate conditions.

Resharding can redistribute data using a new shard key.

Refining a shard key can extend an existing key with additional fields.

But these operations have costs and operational requirements.

Changing the placement function for a large collection can require substantial data movement and coordination.

It's far better to evaluate realistic access patterns before choosing a shard key than to treat resharding as a free configuration edit.

On the other hand, don't imagine that shard keys are permanently immutable architectural decisions.

Modern database systems provide mechanisms for evolution.

The practical question is how expensive that evolution will be.

---

# 16. Transactions Across Shards: The Consistency Problem Returns

In CS340-L03, we examined document-level atomicity and multidocument transactions.

Sharding adds another dimension.

Suppose a booking workflow needs to modify inventory records located on different shards.

Now the transaction must coordinate changes across multiple distributed participants.

MongoDB supports distributed transactions for appropriate sharded deployments.

But coordinating a transaction across several shards is more complex than updating one document on one primary.

The system must preserve the relevant transactional guarantees while handling network communication, participant failures, and commit coordination.

## 16.1 Why distributed transactions cost more

Imagine a transaction involving two shards.

The database must coordinate the transaction's state across those participants.

Neither shard should independently declare a globally atomic operation committed in a way that violates the transaction's overall outcome.

This may require additional coordination and durable transaction-management work.

Latency can increase.

Failure handling becomes more complicated.

Long-running transactions can also hold resources and interfere with ordinary operations.

That doesn't mean distributed transactions should never be used.

They can be necessary for correctness.

But a design that scatters every common business operation across many shards may create unnecessary coordination costs.

## 16.2 Shard keys can influence transaction locality

Suppose reservations are usually accessed and updated by one customer or one booking aggregate.

A partitioning strategy that keeps common transactional work localized may reduce how often operations must involve several shards.

But perhaps the same data is also queried extensively by hotel ID.

Now the partitioning choice becomes a trade-off between different access patterns.

We cannot optimize every query simultaneously with one physical distribution.

This is the same fundamental problem we encountered with compound indexes.

The order and organization of data favor particular operations.

Sharding extends that decision across machines.

## 16.3 A transaction is not a universal distributed workflow

Even a successful multidocument or cross-shard MongoDB transaction doesn't automatically control an external payment provider.

If the database commits but the payment API responds ambiguously, the application still needs business-level reconciliation.

The database transaction protects the data operations within its supported scope.

It does not make unrelated services participate in one magical global transaction.

This is why CS430's ideas about idempotency, sagas, durable workflows, and partial failure remain essential.

---

# 17. The Architecture Review: Should We Shard Our Hotel Platform?

Let's return to our company.

The infrastructure team proposes sharding the hotel catalogue because the collection contains millions of documents.

Is that enough reason?

Not necessarily.

Millions of documents are not inherently beyond the capacity of one mature database server.

The relevant questions concern actual data size, memory working set, storage limits, query performance, write throughput, growth, and availability requirements.

Before introducing sharding, we should examine the existing bottlenecks.

Are queries properly indexed?

Is the data model reasonable?

Is the workload dominated by unnecessary scans?

Could archival or retention policies reduce storage pressure?

Are application operations generating excessive write amplification?

Does the current replica set have sufficient resources?

Sharding introduces considerable operational complexity.

It should solve an actual distribution problem.

## 17.1 Separate the workloads

Our platform has at least two different data workloads.

The hotel catalogue contains relatively stable descriptive information.

Search and profile retrieval dominate its usage.

The event-ingestion system receives large quantities of continuously generated records.

Those workloads may benefit from different architectures.

The catalogue might remain comfortable in an ordinary replica set.

The event-ingestion system might eventually require partitioning or a specialized analytical data platform.

Even then, the shard key must be selected according to expected query and write patterns.

## 17.2 The workload simulation

Suppose we consider sharding events by creation timestamp.

We predict concentrated writes at the newest end of the key space.

Suppose we hash event IDs.

That may distribute writes well, but queries retrieving all events from a recent time interval may need to contact many shards.

Suppose we partition by tenant ID.

That may target tenant-specific queries efficiently, but a few enormous tenants could dominate their respective shards.

The correct decision requires measuring actual distributions.

We might examine event volume per tenant, read queries by time range, common filtering dimensions, retention policies, and expected growth.

There may be no perfect shard key.

The goal is to choose one whose trade-offs align with the dominant workload.

---

# 18. Returning to the Disappearing Reservation

We've now explored replication and sharding.

Let's finally reconstruct the incident from the opening.

The booking API inserted a reservation into a MongoDB replica set.

The application received acknowledgment with write concern `w: 1`.

The primary then became isolated before the write was replicated to a sufficient portion of the set.

The other two data-bearing members elected a new primary.

Their authoritative history did not contain the reservation.

When the original primary rejoined, the divergent write was rolled back.

The customer had already received confirmation.

This was not simply a database bug.

It was a mismatch between the application's business promise and the database guarantee it requested.

## 18.1 Correct the write contract

For business-critical reservation writes, we require a suitable majority acknowledgment policy with appropriate journaling and durability configuration.

We ensure that the application doesn't return final confirmation until the necessary database operation has satisfied the selected write concern.

We also consider read consistency.

If the customer immediately loads their reservation, we need a read path that satisfies the intended user experience, potentially through primary reads, causal sessions, or stronger read semantics according to the workflow.

And we must handle ambiguous outcomes.

If acknowledgment times out, the application cannot automatically assume that no reservation exists.

It must preserve the operation identity and reconcile the final state.

## 18.2 Test failover behavior

The team should test replica-set failover in a controlled environment.

What happens when the primary becomes unavailable?

How long are writes interrupted?

How do drivers discover the new primary?

What errors reach the application?

Which operations are retried?

Do customer-facing workflows handle uncertainty appropriately?

And can operators determine whether acknowledged writes were rolled back?

The objective is not merely to confirm that another node eventually becomes primary.

It's to verify that the complete application behaves correctly during the transition.

## 18.3 The final lesson

Replicating data can improve resilience.

But it doesn't automatically make every acknowledged write durable across failover.

Reading from secondaries can distribute some workload.

But it doesn't automatically provide the freshest data.

Sharding can distribute data and processing.

But it doesn't automatically balance every access pattern.

Each technique introduces explicit coordination rules and failure modes.

**More machines create more opportunities for resilience and scale—but also more ways for different parts of the system to disagree.**

A senior engineer understands the guarantees needed by the business and configures the distributed system accordingly.

---

# 19. The Oral Examination

Before reading the solutions, explain each scenario aloud.

Don't answer with slogans such as "use majority" or "add more shards." Explain which mechanism produces the observed behavior and why the proposed correction addresses it.

## Challenge 1 — The acknowledged write

A three-member MongoDB replica set acknowledges a reservation insert with `w: 1`.

The primary fails before any secondary receives the write.

The other two members elect a new primary.

Can the reservation disappear? Why?

## Challenge 2 — The majority puzzle

A replica set has three voting data-bearing members.

A write is acknowledged with majority write concern under normal journaling settings.

One member then fails.

Why is the acknowledged history better protected than with `w: 1`?

Does majority mean all members have applied the document update?

## Challenge 3 — The stale confirmation page

A customer creates a reservation successfully using majority write concern.

The frontend immediately queries a secondary and doesn't see the reservation.

Is this necessarily evidence of data loss?

What mechanisms could preserve read-your-writes behavior?

## Challenge 4 — The two-member replica set

A company deploys one primary and one secondary.

The primary fails.

Why might the secondary be unable to elect itself as primary?

Would adding an arbiter provide the same durability benefit as adding another data-bearing member?

## Challenge 5 — The mysterious write timeout

A MongoDB write modifies the primary successfully but returns a write-concern timeout while waiting for replication.

Should the application immediately retry the entire booking operation with a new reservation ID?

Explain the risk and a safer strategy.

## Challenge 6 — The timestamp shard key

An event collection is sharded by an increasing timestamp.

All new writes tend to reach one shard.

Why does that happen?

How might hashed distribution help, and what query trade-off might it create?

## Challenge 7 — The enormous tenant

A multi-tenant collection is sharded by a hashed tenant ID.

One customer produces half the platform's traffic.

Why might that customer still overload one shard?

What alternative designs would you investigate?

## Challenge 8 — The indexed scatter-gather

A sharded collection has an index on hotel ID on every shard.

A query filters by hotel ID but omits the collection's shard key.

Why might mongos still contact every shard?

How are shard targeting and local indexing different?

---

# 20. Solutions and Discussion

## Solution 1 — Rollback after weak acknowledgment

Yes.

With `w: 1`, the primary may acknowledge the write before it is replicated to another member.

If the primary becomes unavailable and the surviving majority elects a new primary without that write, the original primary's divergent operation can be rolled back when it rejoins.

The application requested acknowledgment from one node, not majority-committed history.

## Solution 2 — Majority durability

A majority-based commit protocol protects history across ordinary leadership changes because voting majorities overlap.

With three voting data-bearing members, majority acknowledgment ordinarily requires the relevant commitment condition on two members.

Under standard journaling configuration, this provides stronger protection against losing acknowledged writes during failover.

It does not require every secondary to have applied the corresponding document changes at the time acknowledgment returns.

In particular, MongoDB 8.0 and later can acknowledge majority writes after durable oplog replication while secondary application continues asynchronously.

## Solution 3 — Secondary lag

No.

A secondary may not yet have applied the latest replicated operation.

Majority acknowledgment and immediate visibility on every secondary are separate guarantees.

Appropriate approaches include reading from the primary where suitable or using a causally consistent session with the required majority read and write concerns.

For operations requiring stricter real-time single-document guarantees, MongoDB's documented linearizable read concern may be relevant.

## Solution 4 — Elections and arbiters

A two-member voting replica set needs a majority of its voting members to elect a primary.

One surviving member cannot provide that majority alone.

An arbiter can participate in elections without storing user data.

It may improve election possibilities but does not provide another durable data copy or the same write-availability characteristics as a third data-bearing member.

A three-data-bearing-member configuration is generally stronger for durability and availability goals.

## Solution 5 — Ambiguous outcome

A write-concern timeout doesn't necessarily undo a write that already occurred on the primary.

Retrying with a new reservation identity risks creating duplicates.

The application should preserve the business operation identifier, use supported database retry semantics appropriately, and reconcile the existing operation's state before declaring failure or creating another reservation.

## Solution 6 — Monotonic shard key

Increasing timestamps concentrate new writes near the upper end of a range-partitioned key space.

The shard owning that range can become hot.

Hashed sharding can distribute suitable keys more evenly.

But time-range queries may then need to contact multiple shards rather than reading a contiguous range from a limited set of locations.

The choice depends on whether write distribution or time-range locality matters more.

## Solution 7 — Hot tenant

Hashing tenant ID distributes different tenant IDs, but a particular tenant ID still maps to one hashed key value.

One extremely active tenant can therefore concentrate its workload.

Alternatives may involve a more granular compound partitioning strategy, separately handling very large tenants, or redesigning access patterns and workload isolation.

Each option has query, operational, and consistency trade-offs.

## Solution 8 — Routing versus indexing

Mongos uses shard-key information and cluster metadata to identify which shards may contain matching documents.

An index on hotel ID inside each shard makes local lookup efficient.

But if the router cannot determine the owning shard from the query, it may need to broadcast the request.

Local indexing reduces work after a shard receives the query.

Shard-key-based targeting reduces the number of shards that must receive the query in the first place.

They are separate optimization layers.

---

# 21. The Mental Model Worth Keeping

Replication and sharding solve different problems.

**Replication maintains copies of data.**

**Sharding divides data across machines.**

Replica sets require rules for coordinating writes, electing leaders, and determining which history remains authoritative after failure.

Write concern defines which acknowledgment conditions must be satisfied before a write is reported as successful.

Read preference selects eligible locations for reads.

Read concern defines the consistency properties required from the returned data.

Causal consistency helps preserve relationships between operations, such as reading your own writes.

Sharding introduces a placement function based on shard keys.

Those keys determine which machines own particular documents and whether queries can be routed efficiently.

Three questions should guide your reasoning.

**What has been acknowledged?** One member, a majority, or a stronger specified durability condition?

**What can the reader observe?** A local version, a majority-committed snapshot, or a stronger ordered view?

**Where does the work go?** One targeted shard, several shards, or the entire cluster?

The deepest principle is:

**Distributing data does not eliminate correctness and performance constraints. It moves them into coordination, placement, and failure-recovery rules.**

Once you understand those rules, replica-set failovers, stale reads, rollbacks, hotspots, and scatter-gather queries stop being mysterious.

They become consequences you can predict.

---

# 22. Next Lecture — Specialized Data Systems

We've investigated relational storage, document modeling, indexing, storage engines, replication, and sharding.

But different application workloads still have very different needs.

Why would a company introduce Redis when it already has PostgreSQL?

What makes DynamoDB attractive for predictable key-based access at scale?

Why do Elasticsearch and OpenSearch organize information so differently from transactional databases?

And why can column-oriented analytical systems scan enormous event datasets much more efficiently than ordinary operational stores?

In **CS340-L06 — Specialized Data Systems**, we'll compare these architectures through real engineering decisions.

We'll also confront the less glamorous side of specialization: synchronization pipelines, duplicated state, recovery procedures, and the operational cost of introducing another database.

The question is no longer whether specialized systems are powerful.

They are.

The question is when they actually earn their place in the architecture.

---

# Optional Practical Lab — Exploring Replication and Sharding

*The spoken lecture ends here. The following exercises are intended for screen-based experiments, controlled development environments, and interview revision.*

## Lab A — Inspect a replica set

Connect to a local or authorized development MongoDB replica set.

Examine its current topology:

```javascript
rs.status()
db.hello()
```

Identify the primary, secondary members, voting configuration, and relevant replication information.

Do not perform failover experiments against a production replica set.

## Lab B — Compare write concerns

Using a development collection, perform one insert with primary-only acknowledgment and another with majority acknowledgment.

```javascript
use cs340_lab

db.reservations.insertOne(
  { _id: "BOOKING-001", status: "confirmed" },
  { writeConcern: { w: 1 } }
)

db.reservations.insertOne(
  { _id: "BOOKING-002", status: "confirmed" },
  { writeConcern: { w: "majority", wtimeout: 5000 } }
)
```

Discuss the acknowledgment conditions.

Under which failure scenario might the first operation be rolled back?

Why does the second request stronger protection?

Note that mongosh and driver APIs may express timeout settings differently; the example above uses the MongoDB write-concern command option `wtimeout`.

## Lab C — Inspect read concern

Run a read using majority read concern through the database command interface:

```javascript
db.runCommand({
  find: "reservations",
  filter: { _id: "BOOKING-002" },
  readConcern: { level: "majority" }
})
```

Compare the meaning of local and majority reads.

Then explain why choosing a secondary through read preference is not equivalent to selecting majority read concern.

## Lab D — Observe replication lag

On an authorized development replica set, inspect replication status and progress using available shell helpers and server status commands.

Depending on server version, useful information can include:

```javascript
rs.status()
rs.printSecondaryReplicationInfo()
```

Compare member progress and discuss how lag affects read freshness.

Avoid artificially overloading production secondaries merely to observe replication delay.

## Lab E — Tabletop failover experiment

Draw a three-member replica set.

A is primary. B and C are secondaries.

A receives a write under `w: 1`.

Before the operation replicates, A becomes unreachable.

B and C elect a new primary.

Explain which history survives and what may happen when A rejoins.

Repeat the scenario assuming the write was successfully majority-acknowledged under standard durability settings.

No live node termination is required for this exercise.

## Lab F — Design causal read behavior

Imagine these operations:

1. Create a reservation.
2. Redirect the customer to a reservation confirmation page.
3. Read reservation details from a secondary.

Explain what additional guarantees the application requires.

Design a suitable approach using read/write concerns, primary reads, or causally consistent sessions as appropriate.

Consider how causal context would survive separate HTTP requests processed by different backend instances.

## Lab G — Evaluate candidate shard keys

Consider an event collection containing:

```javascript
{
  tenantId: "TENANT-42",
  eventId: "EVENT-90210",
  createdAt: ISODate("2026-10-27T10:00:00Z"),
  eventType: "hotel_view"
}
```

Evaluate shard-key candidates based on tenant ID, timestamp, event ID, and suitable compound combinations.

For each candidate, discuss:

- Cardinality.
- Frequency distribution.
- Monotonically increasing behavior.
- Common query patterns.
- Hotspot risks.
- Targeted versus scatter-gather queries.
- Operational cost of future resharding.

## Lab H — Inspect a sharded cluster

If you have an authorized development sharded cluster, inspect its topology through mongos:

```javascript
sh.status()
```

Examine shard membership and collection placement.

If available in your version and environment, investigate shard-key analysis facilities.

Do not run sharding, resharding, balancing, or data-movement commands against production without an explicit operational plan.

## Lab I — Design a multi-tenant data architecture

Your SaaS platform contains ten thousand tenants.

Most are small.

Five tenants generate half the workload.

The application frequently retrieves data by tenant and time range.

Propose a sharding strategy.

Discuss why a hashed tenant ID alone might be insufficient.

Then consider whether separate infrastructure for exceptionally large tenants would be more practical than one universal partitioning rule.

The goal is to connect distribution mechanics to real workload patterns.

---

## Further Reading — Optional Technical References

1. [MongoDB — Replica Sets](https://www.mongodb.com/docs/manual/replication/) — Replication architecture and member roles.
2. [MongoDB — Replica Set Primary](https://www.mongodb.com/docs/manual/core/replica-set-primary/) — Primary writes, oplog replication, and elections.
3. [MongoDB — Write Concern](https://www.mongodb.com/docs/manual/reference/write-concern/) — Acknowledgment levels, journaling, and write-concern timeouts.
4. [MongoDB — Read Concern](https://www.mongodb.com/docs/manual/reference/read-concern/) — Read consistency levels.
5. [MongoDB — Read Preference](https://www.mongodb.com/docs/manual/core/read-preference/) — Routing reads to replica set members.
6. [MongoDB — Causal Consistency](https://www.mongodb.com/docs/manual/core/causal-consistency-read-write-concerns/) — Read-your-writes and operation ordering.
7. [MongoDB — Replica Set Rollbacks](https://www.mongodb.com/docs/manual/core/replica-set-rollbacks/) — Divergent histories and rollback.
8. [MongoDB — Sharding](https://www.mongodb.com/docs/manual/sharding/) — Distributed data placement and cluster architecture.
9. [MongoDB — Choose a Shard Key](https://www.mongodb.com/docs/manual/core/sharding-choose-a-shard-key/) — Cardinality, frequency, monotonicity, and query patterns.
10. [MongoDB — Routing with mongos](https://www.mongodb.com/docs/manual/core/sharded-cluster-query-router/) — Targeted and scatter-gather operations.
11. [MongoDB — Troubleshoot Shard Keys](https://www.mongodb.com/docs/manual/core/sharding-troubleshooting-shard-keys/) — Hotspots, jumbo chunks, and uneven distribution.
12. [MongoDB — Transactions in Applications](https://www.mongodb.com/docs/manual/core/transactions-in-applications/) — Transaction retries and unknown commit outcomes.
13. Martin Kleppmann, *Designing Data-Intensive Applications* — Replication, partitioning, coordination, and consistency models.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced for voice-reader skipping. Scan this when revising; return to the full lecture only when a distinction needs rebuilding.*

```text
CS340-L05  REPLICATION, CONSISTENCY & SHARDING — INTERVIEW GLANCE CARD

CORE DISTINCTION
  REPLICATION = several copies of SAME logical data
  SHARDING    = different machines own DIFFERENT data subsets
  Often combined: each shard is itself a replica set.

MONGODB REPLICA SET
  Primary       ordinary write authority; maintains replication oplog
  Secondary     follows oplog; applies replicated operations
  Election      requires voting majority + candidate eligibility
  Oplog         replication operation history
  Journal       local crash durability — NOT same as oplog
  Lag           secondaries may be behind primary

  3 data-bearing voting nodes: majority = 2
  2 voting nodes: losing 1 → no majority to elect new primary
  Arbiter: votes but stores NO user data
  P-S-S generally stronger durability/failover characteristics than P-S-A

WRITE CONCERN — WHAT WAS ACKNOWLEDGED?
  w:0          unacknowledged
  w:1          primary acknowledgment; MAY ROLLBACK on failover
  w:"majority" majority acknowledgment; stronger rollback protection
  j:true       requested on-disk journal durability
  wtimeout     wait deadline; error DOES NOT UNDO applied write

  Default write concern commonly majority, but CONFIG/TOPOLOGY MATTER.
  Arbiters can alter implicit default and availability conditions.
  writeConcernMajorityJournalDefault controls journaling behavior.

  MongoDB 8.0+ nuance:
    majority acknowledgment may follow durable oplog replication,
    while secondary application to collections happens ASYNCHRONOUSLY.
    Majority-ACK != every secondary immediately queryable with new data.

ROLLBACK EXAMPLE
  A primary receives reservation insert with w:1.
  A acknowledges before B/C replicate.
  A becomes isolated; B+C elect new primary.
  New primary lacks insert; A later rejoins and divergent write rolls back.
  Business bug: acknowledged write guarantee < promised confirmation.

MAJORITY IDEA
  Voting majorities overlap.
  Correct majority-commit protocol protects committed history through
  ordinary leadership changes.
  Majority != all nodes.
  Majority != backup.
  Durability depends on configured journal/storage guarantees.

READ PREFERENCE — WHERE?
  primary            default; read primary
  primaryPreferred   primary if possible, otherwise eligible secondary
  secondary          only secondaries
  secondaryPreferred prefer secondary; possible stale data
  nearest            choose eligible low-latency members
  Secondary lag and selection policies matter.

READ CONCERN — WHAT CAN YOU OBSERVE?
  local       member's local data; may include rollback-prone state
  majority    majority-committed snapshot; NOT necessarily latest
  linearizable (supported single-doc primary reads) stronger real-time
             guarantee w/ majority writes; cost + availability trade-offs
  snapshot    consistent snapshot semantics for supported operations

  READ PREFERENCE != READ CONCERN.
  A secondary with majority read concern may still lag.

CAUSAL CONSISTENCY
  read-your-writes     later read sees your previous acknowledged write
  monotonic reads      don't move backwards within causal history
  monotonic writes     preserve operation order
  writes-follow-reads  later writes respect observed causal state
  MongoDB: causally consistent sessions + majority reads/writes.
  Separate HTTP requests need appropriate session/causal context handling.
  Session != web login session.

FAILOVER / RETRIES
  Election → temporary write unavailability possible.
  Driver discovers new primary and updates topology.
  Retryable writes help eligible operations; not universal exactly-once.
  Transaction transient error → retry transaction as documented.
  Unknown commit result → retry commit / reconcile, don't invent new
                          business operation ID.
  Timeout != operation failed.
  Payment/refund/reservation → business idempotency still required.

SHARDED CLUSTER
  Shards        store subsets; typically replica sets
  mongos        query router
  Config server metadata maps shard-key ranges/chunks to shards
  Balancer      redistributes data; costs I/O/network
  Shard key     determines data placement AND efficient query routing

RANGE vs HASHED SHARDING
  Range         preserves range locality; monotonic writes may hotspot
  Hashed        distributes suitable values; weakens contiguous range
                locality for original key
  Neither automatically balances skewed individual key values.

SHARD KEY QUALITY
  Cardinality   many distinct values allow more split flexibility
  Frequency     hot repeated value concentrates workload
  Monotonicity  increasing key pushes new writes to active edge range
  Query shape   shard-key filter enables targeted routing
  Tenant ID     good targeting, but one huge tenant can remain hot
  Time key      natural ranges, but timestamp-only writes may hotspot

TARGETED vs SCATTER-GATHER
  Query includes usable shard key → targeted shard(s)
  Query missing routing key → broadcast to all relevant shards
  Local index makes each shard's work cheaper;
  shard key determines which shards must receive request.
  Some analytics benefit from parallel all-shard work.

BALANCING & JUMBO CHUNKS
  Hot chunk     traffic concentrated on one range
  Jumbo/indivisible range  too much data sharing unsplittable key values
  Balancing moves ranges but can't cure every bad key distribution.
  Resharding supported; NOT free; can require major data movement.
  Refine shard key by adding fields where appropriate.

TRANSACTIONS
  Single-document atomic write remains useful.
  Multi-document transactions exist.
  Cross-shard transactions add coordination, latency, failure handling.
  Shard placement affects transaction locality.
  External payments remain OUTSIDE database transaction guarantee.

SENIOR DIAGNOSTIC QUESTIONS
  1. Which write concern was requested and actually satisfied?
  2. Where did the read execute? What read concern?
  3. How far behind are secondaries?
  4. Could the write have rolled back?
  5. Which node is primary? Can a majority communicate?
  6. Which shard key distributes the workload?
  7. Is the query targeted or scatter-gather?
  8. Are hotspots caused by key frequency or monotonicity?
  9. What do operation timeouts leave uncertain?

INTERVIEW IN ONE LINE
  "Replication protects availability and data copies; sharding distributes
   capacity. Correctness depends on explicit acknowledgment and read
   guarantees, while performance depends on placing data according to
   actual access patterns."
```
