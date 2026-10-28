---
id: CS430-L02
course: CS430
title: "Consistency, Replication, and Availability"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [BACK301-S08]
prev: CS430-L01
next: CS430-L03
---







# CS430 — Distributed Systems and Reliable Workflows

## Lecture 02: Consistency, Replication, and Availability

*How two perfectly healthy database servers can return different answers—and why making a system more available can make its behavior considerably harder to reason about.*

---

# 1. The Reservation That Disappeared After Being Confirmed

It's Monday afternoon, and your hotel-booking SaaS is experiencing a rather unusual production incident.

A customer books a room in Stockholm. The backend validates the reservation, allocates inventory, and commits the transaction to PostgreSQL.

Everything succeeds.

The API returns:

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "reservationId": "R-10842",
  "status": "confirmed"
}
```

The frontend navigates to the reservation details page.

That page immediately makes another request:

```http
GET /api/reservations/R-10842
```

The backend responds:

```http
HTTP/1.1 404 Not Found
```

The customer stares at the screen.

A moment ago, the system proudly announced that the reservation had been confirmed. Now it claims the reservation doesn't exist.

Naturally, the customer assumes something went wrong. Perhaps the booking failed. Perhaps the payment didn't go through. Perhaps they should try again.

You investigate.

The reservation definitely exists in PostgreSQL. Its inventory allocation succeeded, and its transaction committed.

The application logs show no exceptions. Every database query completed successfully.

But then you notice something interesting about your infrastructure.

A month earlier, the team introduced a PostgreSQL read replica to reduce load on the primary database.

The architecture now looks like this:

```text
                    APPLICATION
                         |
                 +-------+-------+
                 |               |
              WRITES            READS
                 |               |
                 v               v
            POSTGRESQL       POSTGRESQL
             PRIMARY          REPLICA
                 |               ^
                 |               |
                 +-- Replication-+
```

The booking request wrote to the primary.

The subsequent details request read from the replica.

And at that moment, the replica hadn't yet received and applied the transaction that created the reservation.

A few milliseconds later, replication caught up. Refreshing the page returned the expected booking.

Both databases were healthy. Neither executed an incorrect query.

They simply represented different moments in the database's history.

This is the central mystery of replication: **once information exists in multiple places, those places cannot always change simultaneously**.

Someone must decide when a change is considered committed, how replicas learn about it, which copies can answer requests, and what happens when communication between them fails.

Those decisions define the system's consistency and availability guarantees.

Today we'll investigate how these mechanisms work, beginning with PostgreSQL replication and eventually arriving at one of distributed computing's most famous—and most frequently misrepresented—ideas: the CAP theorem.

---

# 2. Why Replicate a Database?

Before examining the complications, let's establish why anyone would introduce replication in the first place.

A single PostgreSQL server can be remarkably capable. With sensible schema design, indexes, connection management, and adequate hardware, it can support workloads far beyond what many ordinary SaaS applications ever require.

So why add another database server?

There are several legitimate reasons.

### Read capacity

Suppose your application handles 2,000 reads per second but only 100 writes. Some read operations—reporting, customer history, dashboards—consume significant resources.

Moving selected read traffic onto replicas can reduce pressure on the primary.

```text
                    APPLICATION
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
          PRIMARY     REPLICA A   REPLICA B
           Writes      Reads       Reads
```

This doesn't automatically triple database capacity. Replicas still need resources to process incoming replication changes, and the primary still handles the writes.

But for suitable read-heavy workloads, they can help substantially.

### High availability

If the primary database fails, a replica may be promoted to become the new primary.

This can reduce downtime compared with restoring a database from an older backup.

However, having a replica isn't equivalent to having automatic, safe failover. Promotion, routing, coordination, and recovery must all be designed.

### Geographic proximity

An application serving customers across several continents might want database reads close to users.

A replica in another region can reduce network latency for certain operations, though database replication delay and the additional operational complexity must be considered.

### Workload isolation

Large analytical queries can compete with transaction processing for CPU, memory, and I/O.

A dedicated read replica may allow expensive reports to run without consuming as much of the primary's query-execution capacity.

However, it still must replay changes arriving from the primary, and certain long-running queries can interfere with replication recovery.

The common motivation is that copying data creates new possibilities for performance and fault tolerance.

The price is synchronization.

---

# 3. How PostgreSQL Replication Actually Works

Let's examine conventional PostgreSQL **physical streaming replication**.

PostgreSQL maintains a Write-Ahead Log, commonly called WAL.

When database pages are modified, PostgreSQL records the necessary changes in WAL so that committed operations can be recovered after a crash.

The database doesn't need to immediately flush every modified table page to permanent storage before acknowledging each committed transaction. WAL provides the durable record required for recovery, subject to the configured durability guarantees.

This same stream of changes can be delivered to another PostgreSQL server.

```text
               PRIMARY POSTGRESQL
                       |
                  SQL Writes
                       |
                       v
                  WAL Records
                       |
                       v
                  WAL Sender
                       |
                 Network Stream
                       |
                       v
                  WAL Receiver
                       |
                       v
                 WAL Written
                       |
                       v
                  WAL Replay
                       |
                       v
               STANDBY POSTGRESQL
```

The standby replays WAL records to reconstruct the primary's database changes.

This isn't the application executing each original SQL statement again. Physical replication operates on PostgreSQL's lower-level database change records.

A **hot standby** can also serve read-only queries while replaying WAL.

### The three stages worth distinguishing

Imagine Transaction T commits on the primary.

For that transaction to become visible on a standby, several things must happen:

1. The primary produces the necessary WAL records.
2. The standby receives the records, potentially writes and flushes them to durable storage.
3. The standby replays the records, making the committed transaction visible to its queries.

These stages don't happen simultaneously.

A replica may already have received a transaction's WAL without having replayed it.

That's an important distinction because **having the data necessary to reconstruct a change is not the same as currently exposing that change to queries**.

PostgreSQL tracks progress using Log Sequence Numbers, or LSNs.

An LSN identifies a position in the WAL stream.

Conceptually:

```text
PRIMARY WAL POSITION:  0/58A0100

REPLICA RECEIVED:      0/58A0100

REPLICA REPLAYED:      0/589F000
```

The replica has received changes that it hasn't fully applied.

The difference between these positions indicates that replay is behind receipt.

LSNs provide a useful measure of replication progress, and we'll use them later to design stronger read-after-write behavior.

---

# 4. Asynchronous Replication: Fast Commits, Delayed Agreement

PostgreSQL streaming replication is asynchronous by default.

Under this model, the primary can acknowledge a committed transaction without waiting for a standby to receive or replay it.

That keeps write latency relatively independent of replica network delay.

Consider:

```text
TIME       PRIMARY                      REPLICA
────────────────────────────────────────────────────

T1         INSERT reservation

T2         COMMIT

T3         Return success to API

T4                                      Receives WAL

T5                                      Replays WAL

T6                                      Reservation visible
```

Between T3 and T6, the primary and replica disagree about the reservation's existence.

That's not a bug. It's a consequence of the replication contract.

The lag might be tiny under normal circumstances. But it may increase if network bandwidth is constrained, the standby is overloaded, WAL replay falls behind, or a long-running standby query creates recovery conflicts.

If the primary produces changes faster than the replica can apply them, the difference can grow.

### Two different risks

Asynchronous replication creates two distinct concerns.

The first is **stale reads**: a replica returns an older database state.

The second is **possible data loss during failover**.

Suppose the primary commits Transaction T and acknowledges success, but crashes before T's WAL reaches the standby.

If the standby is promoted, it may not contain T.

From the application's perspective, a previously acknowledged write has disappeared from the new primary's history.

That's much more serious than a temporary stale read.

The amount of potentially lost committed work depends on the replication state at failover.

This introduces two important operational concepts:

**Recovery Point Objective (RPO):** How much data loss the business can tolerate during recovery.

**Recovery Time Objective (RTO):** How long the business can tolerate the service being unavailable.

A zero-data-loss objective requires architectural and operational guarantees capable of supporting it. An asynchronously replicated standby does not automatically provide that guarantee.

For some workloads, a few seconds of potential data loss may be acceptable.

For acknowledged financial transactions or confirmed hotel reservations, the requirements may be much stricter.

---

# 5. Synchronous Replication: Make the Primary Wait

One way to strengthen replication guarantees is to require the primary to wait for a standby before acknowledging a transaction.

This is **synchronous replication**.

However, the exact meaning of acknowledgment matters.

PostgreSQL provides several relevant `synchronous_commit` behaviors.

| Mode | What a committing transaction waits for |
|---|---|
| `local` | Local WAL flush, not standby confirmation |
| `remote_write` | Synchronous standby has written WAL to its operating system |
| `on` | Synchronous standby has flushed WAL durably |
| `remote_apply` | Synchronous standby has replayed the transaction |
| `off` | Doesn't wait for local WAL flush; weaker crash durability |

These modes interact with the configuration of synchronous standbys.

Simply specifying `synchronous_commit = 'remote_apply'` doesn't magically create a synchronous replica. PostgreSQL must also have an appropriate `synchronous_standby_names` configuration and participating standby.

### Why `remote_apply` is special

Suppose the primary waits until the synchronous standby has replayed the transaction.

Then, when the primary acknowledges the commit, the relevant standby has already made that transaction visible.

That can support stronger read-after-write behavior when subsequent reads are routed to the actual participating standby.

But don't generalize the guarantee to every replica in the fleet.

An asynchronous replica elsewhere may still be behind.

Nor does this configuration solve every failover, routing, or split-brain problem.

### What does synchronization cost?

Imagine the primary is in Frankfurt and the synchronous standby is in Stockholm.

A transaction's commit latency now depends partly on communication with the standby and the selected acknowledgment level.

If the standby becomes unavailable and no suitable replacement participates, commits requiring synchronous acknowledgment can wait.

You've traded some write availability and latency for stronger replication guarantees.

This is not necessarily bad.

For business-critical state, that trade may be entirely justified.

But synchronous replication shouldn't be enabled casually under the assumption that it provides more safety at no cost.

The system has to decide what happens when the standby cannot be reached.

And that decision takes us toward the central availability trade-off.

---

# 6. Consistency Is Not One Single Guarantee

Developers frequently describe databases as either strongly consistent or eventually consistent.

Those terms are useful, but they're incomplete.

Different applications need different consistency guarantees, and it's possible to satisfy some without satisfying others.

Consider a customer booking a room.

### Read-your-writes consistency

After successfully creating a reservation, the same customer should be able to retrieve it.

```text
Customer writes Reservation R-10842
                    |
                    v
Customer reads Reservation R-10842
                    |
                    v
Should see their own completed write
```

This is called **read-your-writes consistency**.

Our opening incident violated it.

An immediately stale replica returned 404.

### Monotonic reads

Suppose a customer retrieves a reservation and sees:

```text
status = confirmed
```

A second request is routed to a lagging replica and returns:

```text
status = pending
```

The customer has moved backward in the observable history of their reservation.

A monotonic-read guarantee prevents a session from observing progressively older states in this way.

This matters when requests are load-balanced across several replicas with different replication progress.

### Consistent prefix

Imagine a sequence of dependent events:

```text
1. Order created
2. Payment authorized
3. Order shipped
```

A client shouldn't observe a history that includes shipping while omitting causally prior information necessary to understand it.

Consistent-prefix guarantees preserve an appropriate ordering of observed events.

The details depend on the system's model of ordering and causality.

### Linearizability

Linearizability is a stronger consistency model.

It requires operations on a shared object to behave as though they occurred atomically in a single order that respects real-time precedence.

If one write completes before a later read begins, that later read must reflect the write or a subsequent change.

For a single-copy abstraction, the system must not appear to move backward behind an already completed operation.

Linearizability is particularly useful for reasoning about operations such as acquiring a unique resource, updating an authoritative counter, or coordinating shared state.

But note an important distinction:

**Linearizability and transaction serializability are not the same property.**

Serializability asks whether concurrent transactions behave equivalently to some serial transaction order.

Linearizability additionally imposes real-time ordering constraints on operations.

A database's transactional isolation level and a replicated system's external consistency guarantees need to be considered separately.

---

# 7. Eventual Consistency: A Promise With Conditions

An eventually consistent system allows replicas to temporarily disagree, while promising that they converge under appropriate conditions.

For example, if updates stop and communication continues successfully, replicas eventually reach the same relevant state.

The crucial qualifications are often omitted from casual explanations.

Eventual consistency doesn't mean all replicas converge regardless of failures.

Convergence depends on assumptions about message delivery, recovery, conflict resolution, and continued progress.

If a replica permanently loses connectivity, it can't learn new changes.

If different replicas accept conflicting writes, they need an appropriate method to reconcile those writes.

And if a system discards necessary replication history, catching up may require a full resynchronization.

### The product consequence

Suppose a customer's profile picture takes a few seconds to update on every server.

That's probably tolerable.

Now suppose a customer has just paid for a hotel reservation and is told the reservation doesn't exist.

That's considerably less tolerable.

The difference is not merely technical.

It's the relationship between consistency and the business promise.

A useful design principle is to assign consistency requirements **per operation or data domain**, rather than declaring the entire application strongly or eventually consistent.

A hotel platform might permit stale hotel descriptions while requiring authoritative inventory allocation and reliable reservation confirmation.

One product can—and frequently should—use several different consistency strategies.

---

# 8. How to Guarantee Read-After-Write in Practice

Let's return to the disappearing reservation.

The simplest solution is also often the best.

### Strategy A — Read from the primary

Immediately after creating a reservation, route the details request to the primary database.

```text
POST /reservations ---> PRIMARY

GET /reservations/R-10842 ---> PRIMARY
```

Assuming the primary remains authoritative and the second read starts after the successful commit, it can see the committed reservation under an appropriate transaction context.

This avoids replica lag for that read.

For many SaaS applications, this is entirely sufficient.

You don't need a sophisticated distributed-consistency protocol just to ensure that a customer can view a reservation they created one second earlier.

### Strategy B — Temporarily pin a session to the primary

An application might route reads to the primary for a short period after a write.

For example, after modifying a user profile, subsequent reads from that user's session could use the primary for several seconds.

This reduces the chance of stale reads.

But a fixed time window isn't a strict guarantee.

A replica can lag longer than the chosen period.

This strategy is a practical heuristic, not proof that replication has caught up.

### Strategy C — Wait for replication progress

A more precise strategy uses WAL positions.

After a successful commit, the application can obtain a conservative WAL position on the primary and associate it with the operation's subsequent reads.

On a standby, PostgreSQL exposes its replay position through:

```sql
SELECT pg_last_wal_replay_lsn();
```

The application can wait until the standby has replayed at least the required position before routing the read there.

Conceptually:

```text
Required WAL position: 0/58A0100

Replica replay position: 0/589F000
                  |
                  v
                WAIT
                  |
                  v
Replica replay position: 0/58A0100
                  |
                  v
           Safe to perform read
```

There are implementation subtleties.

The application must obtain the required position appropriately after commit. A position captured through a separate `pg_current_wal_lsn()` call may include additional transactions, making it a conservative threshold rather than an exact marker for the original transaction.

LSN comparisons must also be meaningful for the same replication history or timeline; failover can complicate that assumption.

And waiting cannot continue indefinitely. The application needs a deadline and a fallback policy.

If the replica doesn't catch up quickly enough, the system may route the request to the primary or report temporary unavailability, depending on the required guarantee.

### Which strategy would I choose?

For ordinary CRUD SaaS applications, I'd default to reading critical immediately-updated entities from the primary.

I'd introduce replica-aware session routing or LSN-based waiting when read scaling and consistency requirements genuinely justified the additional complexity.

The elegant-looking solution isn't always the sensible one.

---

# 9. Replicas Are Not Automatically Independent Capacity

Read replicas are often presented as a straightforward scaling solution.

Add two replicas, distribute read traffic, enjoy faster queries.

Reality is more complicated.

A physical standby must continuously receive and replay WAL changes from its primary.

That consumes CPU, memory, storage bandwidth, and I/O capacity.

Now imagine running a large analytical query on the standby.

The query uses a snapshot that depends on row versions the primary has already made obsolete.

Meanwhile, incoming WAL replay may need to perform cleanup operations that conflict with the standby query.

PostgreSQL must decide how to resolve that conflict.

Depending on configuration, it may delay replay or cancel the query.

### Standby query conflicts

A read replica may return errors because replay needs to progress.

This can surprise developers who assume that read-only queries on a replica are isolated from primary-side changes.

PostgreSQL provides settings such as `max_standby_streaming_delay` and `hot_standby_feedback` to influence the behavior.

But those settings introduce trade-offs.

Allowing long queries to delay replay increases replica lag.

Sending standby feedback to prevent certain cleanup conflicts can contribute to table bloat on the primary.

There is no free lunch here—although databases are generous enough to provide several varieties of bill.

### Read replicas don't scale writes

Suppose the primary processes 5,000 writes per second.

Adding five physical read replicas doesn't move those writes off the primary.

The primary still executes the write transactions and generates WAL.

In fact, it now has additional replication responsibilities.

If write throughput is the actual bottleneck, read replicas might not help.

They can sometimes indirectly improve write performance by moving expensive read queries away, but they don't create independent write capacity.

This distinction becomes essential when discussing horizontal scaling in CS430-L03.

---

# 10. Failover: When the Replica Becomes the Primary

Suppose your primary database suffers a hardware failure.

The application loses its write connection.

Fortunately, a standby exists.

You promote it.

```text
BEFORE FAILURE

Application
    |
    v
Primary A ----replication----> Standby B


AFTER FAILURE

Application
    |
    v
Promoted Primary B

Old Primary A: unavailable
```

This seems straightforward until we ask two questions.

First: was B fully caught up with A?

Second: what happens if A comes back online?

### Losing acknowledged writes

In asynchronous replication, A may have acknowledged transactions that B never received.

When B becomes primary, those transactions may be absent.

This is a nonzero recovery-point problem.

A stronger synchronous replication setup can reduce or eliminate this risk for properly acknowledged transactions, but only if the failover selects a node that satisfies the required durability condition.

A configuration setting alone doesn't guarantee that the failover controller will select the correct candidate.

### The returning primary

Now imagine A wasn't destroyed.

It was merely isolated by a network failure.

The failover system couldn't reach it and promoted B.

A few seconds later, the network recovers.

A still believes it's primary.

B is also primary.

You now have two systems potentially accepting writes.

```text
               NETWORK PARTITION

       Primary A          Primary B
          |                  |
       Accepts writes     Accepts writes
          |                  |
          v                  v
      History A            History B
```

This is a **split-brain** situation.

The two database histories can diverge.

Simply reconnecting the servers doesn't automatically merge conflicting PostgreSQL physical replication histories.

The system must ensure that an old primary cannot continue accepting authoritative writes after another node has taken over.

### Fencing

Fencing means preventing a former owner from continuing operations that could conflict with the new owner.

That might involve terminating the old database process, isolating its storage or network access, revoking its ability to receive application traffic, or using infrastructure-level mechanisms that prevent concurrent primary ownership.

A robust failover system combines reliable leader selection with enforcement that prevents competing leaders from both acting authoritatively.

Merely changing a DNS record isn't necessarily sufficient. Existing connections, cached addresses, and isolated nodes may continue behaving unexpectedly.

And a database failover isn't complete merely because the standby has been promoted.

Applications must reconnect, routing must change, and the old primary must be reintegrated safely—often by rewinding or rebuilding it from the new primary's history.

---

# 11. Why Three Nodes Can Be Better Than Two

Imagine two database nodes, A and B.

A network partition prevents them from communicating.

A cannot tell whether B has crashed or is merely unreachable.

B has the same uncertainty about A.

If both independently promote themselves, split-brain becomes possible.

How do we prevent that?

One widely used approach to distributed coordination is a **quorum**.

Instead of allowing any isolated node to declare itself leader, leadership requires support from a majority of voting participants.

For three voters, a majority requires two.

```text
Voting nodes: A, B, C

Partition:

A + B | C

A + B = majority
C     = minority
```

The majority side can potentially continue coordinating leadership.

The isolated minority cannot independently establish a new authoritative leader.

This works because two different majorities must overlap.

With three voters, any group of two shares at least one member with every other group of two.

But don't confuse three voting nodes with three full database copies.

A deployment might use two database nodes and an independent witness or coordination service as part of its high-availability design.

The precise safety properties depend on the election protocol, persistent terms or epochs, fencing, and how leadership authority is enforced.

Also, quorum does not magically make the majority side available under every failure.

If fewer than the required voters can communicate, progress may stop.

That's a deliberate trade-off made to preserve safety.

The general idea appears in consensus algorithms such as Raft and in many distributed coordination systems.

We don't need to implement Raft here. The important insight is that **a leader must possess authority that competing partitions cannot simultaneously claim**.

---

# 12. CAP: The Most Famous Misleading Triangle in Software Engineering

You've almost certainly encountered the CAP theorem.

It is commonly summarized as:

> Consistency, Availability, Partition tolerance: pick two.

This phrasing has caused an extraordinary amount of confusion.

Let's examine the actual issue.

Imagine a replicated database with two nodes, A and B.

A network partition prevents communication between them.

```text
        NODE A                 NODE B
          |                      |
          X---- NO NETWORK ------X
          |                      |
      Client Alice           Client Bob
```

Alice submits a write to A:

```text
balance = €100
```

Bob asks B to read the balance.

B cannot communicate with A.

What should B return?

Suppose B's last known value is €50.

It has no way to know whether A has received a newer write.

### Option 1 — Preserve strong consistency

B refuses or delays the read because it cannot establish a sufficiently current answer.

This preserves the relevant strong-consistency requirement at the cost of serving Bob's request.

### Option 2 — Preserve availability

B answers using its locally available information.

Bob receives €50 even though Alice's write may already have completed on A.

This preserves the ability to respond but can violate a linearizable consistency guarantee.

The dilemma arises because B lacks information.

No clever implementation can reconstruct a remote event whose existence cannot be determined through the available communication.

### What CAP actually says

In the classic formalization, consistency refers to atomic or linearizable consistency for a replicated read/write object.

Availability means that every request received by a non-failing node eventually receives a response.

Partition tolerance means the system's guarantees must be considered even when communication between groups of nodes is lost or indefinitely delayed.

The theorem establishes that we cannot guarantee both linearizable consistency and that form of availability in every execution while tolerating arbitrary partitions.

This is considerably more precise than "pick two of three."

### Why the triangle is misleading

Partition tolerance isn't normally an optional feature you disable by choosing a "CA database."

If your system spans communicating machines, network partitions are a failure mode you must account for.

When communication is healthy, a distributed system can often provide both strong consistency and availability.

The hard trade-off becomes unavoidable in particular partition scenarios.

Nor does CAP say that a strongly consistent system must always be slow, or that an eventually consistent system is always available.

Real systems involve additional considerations: latency, replication strategy, quorum size, durability, workload, recovery, and failure assumptions.

### The useful takeaway

CAP is most valuable as a reasoning tool.

When part of the system becomes unreachable, ask:

**Can this component safely answer the request without learning what happened elsewhere?**

If the answer is no, preserving a strong consistency requirement may mean refusing to proceed.

For a social-media like counter, returning an older number may be acceptable.

For allocating the last available hotel room, independently accepting writes in disconnected partitions could create an impossible business commitment.

The choice follows the meaning of the operation.

---

# 13. Consistency Versus Availability: The Business Decision

Let's compare several operations in our hotel-booking platform.

| Operation | Typical consistency requirement | Reason |
|---|---|---|
| Display hotel description | Stale reads often acceptable | Low consequence of temporary disagreement |
| Show search availability | Brief staleness possible | Booking must revalidate |
| Display newly created reservation | Read-your-writes desirable | Prevent customer confusion and unsafe retries |
| Allocate final room | Strong authoritative coordination | Prevent overselling |
| View historical analytics | Lag may be acceptable | Reporting freshness can be defined |
| Record captured payment | Strict correctness and durable recovery | Financial consequences |
| Show review count | Eventual consistency often sufficient | Small discrepancies usually harmless |

Notice that we haven't classified the whole application as CP or AP.

Instead, we're making decisions around individual invariants and user-facing guarantees.

That's considerably more useful.

A system can intentionally expose stale hotel descriptions while refusing to confirm a booking if authoritative inventory cannot be reached.

It can serve old analytics during a database incident while temporarily disabling new financial operations.

This is a form of graceful degradation.

The product remains useful where safe, rather than pretending every function has identical consistency requirements.

### Availability doesn't mean returning HTTP 200

There's also a subtle but important distinction between responding and fulfilling a requested operation.

Suppose the inventory database is unavailable, so the API returns:

```http
HTTP/1.1 200 OK

{
  "reservationStatus": "confirmed"
}
```

without actually reserving anything.

The server is technically responding, but the business operation isn't being performed correctly.

It's misleading to treat that as meaningful availability.

Real reliability must preserve the service's declared semantics.

Sometimes the appropriate response during an outage is an honest `503 Service Unavailable`.

That can be vastly better than accepting commitments the system cannot fulfill.

---

# 14. Monitoring Replication: What Would You Actually Inspect?

Let's imagine our opening incident is happening in production.

Customers occasionally receive 404 immediately after successful reservation creation.

How would we determine whether replica lag is responsible?

PostgreSQL provides several useful views and functions.

### On the primary

```sql
SELECT
  application_name,
  state,
  sync_state,
  sent_lsn,
  write_lsn,
  flush_lsn,
  replay_lsn,
  write_lag,
  flush_lag,
  replay_lag
FROM pg_stat_replication;
```

This exposes information about connected replication standbys from the primary's perspective.

The different LSN fields help distinguish WAL transmission, writing, flushing, and replay progress.

The lag fields require careful interpretation. They are not universal predictions of how long catching up will take, and may become null when a fully caught-up system is idle.

### On the standby

```sql
SELECT
  pg_is_in_recovery() AS is_standby,
  pg_last_wal_receive_lsn() AS received_lsn,
  pg_last_wal_replay_lsn() AS replayed_lsn,
  pg_last_xact_replay_timestamp() AS last_replayed_commit;
```

`pg_is_in_recovery()` helps identify whether the server is operating in standby recovery mode.

The receive and replay positions reveal whether the standby has applied the WAL it received.

But be careful with the last replayed transaction timestamp.

If the primary has been idle for an hour, the timestamp may be an hour old even though the replica is completely caught up.

An old replay timestamp alone doesn't prove a replica is lagging.

### The operational questions

A useful investigation should determine whether lag comes from transmission, disk flushing, or replay.

Are replicas connected?

Is WAL generation unusually high?

Are standby resources saturated?

Are long-running queries delaying replay?

Are replication slots retaining excessive WAL?

Is the problem isolated to one replica, or does it affect all of them?

And most importantly, are consistency-sensitive requests routed to replicas without appropriate guarantees?

Monitoring replica health is useful. But fixing the opening incident may ultimately require changing read routing rather than improving replication speed.

Even a very fast asynchronous replica is still asynchronous.

---

# 15. Replication Slots: A Safety Mechanism That Can Fill Your Disk

PostgreSQL supports replication slots to help retain WAL needed by replication consumers.

Without appropriate retention, the primary might recycle WAL files before a disconnected standby has received them.

Then the standby could be unable to catch up through ordinary streaming and require another recovery path.

A replication slot records progress so PostgreSQL knows which WAL remains necessary.

That sounds excellent.

But imagine the standby becomes unavailable for several days.

Meanwhile, the primary continues accepting writes and generating WAL.

If the replication slot continues retaining everything the disconnected standby needs, WAL files may accumulate.

Eventually, the primary's storage could fill.

A mechanism introduced to protect replication recovery can now threaten primary availability.

PostgreSQL provides controls such as `max_slot_wal_keep_size`, but limiting retention means a sufficiently lagging standby may lose the WAL needed to continue and require rebuilding.

This illustrates a recurring distributed-systems trade-off:

**Retaining enough history for recovery consumes finite resources. Discarding history too aggressively can make recovery impossible without rebuilding state.**

Replication slots should therefore be monitored, not merely configured once and forgotten.

The same underlying tension appears in message queues, change-data-capture pipelines, and durable event logs.

---

# 16. Physical Versus Logical Replication

Before moving to the practical investigation, let's distinguish two PostgreSQL capabilities that are often grouped under the same word.

### Physical replication

Physical replication uses WAL to maintain a standby representing the database cluster's physical state.

It's commonly used for read replicas and high availability.

The standby normally operates as a read-only replica until promoted.

### Logical replication

Logical replication communicates changes to selected database objects using a higher-level representation.

PostgreSQL supports publications and subscriptions, allowing selected tables and changes to be replicated.

```text
             PUBLISHER
                 |
          Selected Tables
                 |
                 v
          Logical Changes
                 |
                 v
             SUBSCRIBER
```

This can support migrations, selective data distribution, and certain integration architectures.

Logical replication doesn't automatically reproduce every aspect of the source database's schema or infrastructure configuration.

For example, schema changes must be managed appropriately on subscribers.

And application writes made independently on both publisher and subscriber can introduce conflicts.

The important distinction is that physical replication primarily maintains a standby database, while logical replication can distribute selected data changes for more specialized purposes.

Neither should be mistaken for a general-purpose conflict-free multi-primary architecture.

---

# 17. Practical Lab: Simulate a Lagging Replica and an Unsafe Failover

Running a real PostgreSQL primary and standby requires more environment setup than we need for one conceptual experiment.

Instead, we'll build a tiny simulation in Node.js that makes replication delay visible and reproduces the two problems we've been investigating:

1. A successful write followed by a stale read.
2. A failover that loses an acknowledged write.

This is a deterministic educational model, not an implementation of PostgreSQL replication.

Create `replication-lab.mjs`:

```javascript
const primary = {
  version: 0,
  reservations: new Map()
};

const replica = {
  version: 0,
  reservations: new Map()
};

const pendingWal = [];

function commitReservation(id) {
  primary.version++;

  const reservation = {
    id,
    status: "confirmed"
  };

  primary.reservations.set(id, reservation);

  pendingWal.push({
    version: primary.version,
    reservation: { ...reservation }
  });

  console.log(
    `Committed ${id} at version ${primary.version}`
  );

  return primary.version;
}

function replayOne() {
  const change = pendingWal.shift();

  if (!change) return;

  replica.reservations.set(
    change.reservation.id,
    change.reservation
  );

  replica.version = change.version;

  console.log(
    `Replica replayed version ${replica.version}`
  );
}

function read(database, id) {
  return database.reservations.get(id) ?? null;
}

function readWithRequiredVersion(id, requiredVersion) {
  if (replica.version >= requiredVersion) {
    return read(replica, id);
  }

  // Fall back to the authoritative primary.
  return read(primary, id);
}

// 1. Commit to primary.
const version = commitReservation("R-10842");

// 2. Read before replication.
console.log(
  "Immediate replica read:",
  read(replica, "R-10842")
);

// 3. Read with a freshness requirement.
console.log(
  "Consistent application read:",
  readWithRequiredVersion("R-10842", version)
);

// 4. Apply replication.
replayOne();

console.log(
  "Replica after replay:",
  read(replica, "R-10842")
);

// 5. Commit another reservation without replication.
commitReservation("R-10843");

// 6. Simulate promoting the lagging replica.
console.log(
  "Promoted replica contains R-10843:",
  read(replica, "R-10843")
);
```

Run:

```bash
node replication-lab.mjs
```

Expected observations:

```text
Committed R-10842 at version 1

Immediate replica read: null

Consistent application read:
{ id: 'R-10842', status: 'confirmed' }

Replica replayed version 1

Replica after replay:
{ id: 'R-10842', status: 'confirmed' }

Committed R-10843 at version 2

Promoted replica contains R-10843: null
```

We've reproduced the essential phenomena.

The first reservation was committed but initially invisible on the replica.

A version-aware read fell back to the primary.

After replay, the replica contained the reservation.

But the second reservation was acknowledged by the primary and absent from the replica when we simulated promotion.

### Investigation A — Multiple replicas

Introduce `replicaA` and `replicaB`.

Let A replay quickly while B remains behind.

Now alternate read requests between them.

Can you make a customer observe:

```text
confirmed -> pending
```

even though no one changed the reservation backward?

This demonstrates why monotonic-read guarantees matter when load-balancing across replicas.

### Investigation B — Simulated synchronous commit

Change the commit function so it doesn't acknowledge success until `replayOne()` has applied the corresponding change.

What improves?

The selected replica contains the transaction when the application receives its commit acknowledgment.

What happens if replication is paused indefinitely?

The caller must wait or abandon the operation, exposing the availability and latency cost of synchronous coordination.

### Investigation C — Business-specific routing

Imagine implementing these routes:

```text
GET /hotels/482/description
GET /reservations/R-10842
POST /reservations
GET /analytics/hotel/482
```

Decide which should use the primary, which can use replicas, and which may tolerate stale results.

Don't answer based on whether the HTTP method is GET or POST.

Answer based on the data's consistency requirements.

### Optional PostgreSQL investigation

If you have access to a PostgreSQL instance with physical replication configured, inspect:

```sql
SELECT
  pg_is_in_recovery(),
  pg_last_wal_replay_lsn();
```

On the primary, examine `pg_stat_replication`. On the standby, examine `pg_stat_wal_receiver`.

Compare the reported WAL positions while generating ordinary database writes.

You don't need to deliberately break production replication or trigger failover to learn from these metrics.

The exercise is about connecting the abstract idea of replication progress to observable database state.

---

# 18. Engineering and Interview Challenges

## Question 1 — The missing reservation

Your API creates a reservation on PostgreSQL's primary and immediately reads it from an asynchronous replica.

Occasionally, the replica returns 404.

What caused this? Give two reasonable solutions and explain their trade-offs.

## Question 2 — The synchronous standby

A colleague claims that enabling synchronous replication means every replica will always return the latest data.

Is that true? What does PostgreSQL's `remote_apply` mode actually guarantee?

## Question 3 — Failover with data loss

Your primary acknowledges a successful payment record but crashes before replicating it.

A lagging standby is promoted.

What might happen, and what architectural or operational choices could reduce the risk?

## Question 4 — The two isolated servers

Two nodes become unable to communicate.

Both continue accepting writes to the same account balance.

What could go wrong? How might quorum and fencing help?

## Question 5 — CAP explained properly

A developer says:

> PostgreSQL is a CA database, while Cassandra is an AP database. CAP says you can pick only two properties.

What's misleading about this explanation?

## Question 6 — The full disk

Your primary's WAL directory grows rapidly after a replica has been offline for two days.

Database write volume hasn't changed significantly.

What replication mechanism could explain the growth, and what should you investigate before deleting files?

---

# 19. Solutions and Discussion

### 1. The replica hasn't replayed the committed transaction

The opening failure is a read-after-write consistency violation caused by replication lag.

The simplest solution is routing critical follow-up reads to the primary.

Another approach is waiting until the replica has replayed a suitable WAL position before reading.

Primary routing is simpler but keeps more load on the primary. LSN-based waiting can preserve replica usage but introduces coordination, latency, and fallback complexity.

A short primary-pinning window is a practical heuristic, though not a strict freshness guarantee.

### 2. Synchronous replication doesn't make all replicas instantly consistent

Synchronous replication applies to configured participating standby acknowledgments.

It doesn't force every asynchronous standby in the fleet to keep pace.

With `remote_apply`, a transaction's commit acknowledgment waits until the selected synchronous standby or required standby quorum has replayed the relevant transaction.

This can support read-after-write consistency when the application reads from an appropriate participating standby.

Other replicas may still lag, and correctness during failover still depends on orchestration and candidate selection.

### 3. An acknowledged transaction can disappear after unsafe failover

With asynchronous replication, the primary may acknowledge changes not yet received by the standby.

Promoting that standby can produce a new primary history that lacks previously acknowledged transactions.

Synchronous durability requirements, appropriate failover candidate selection, and robust high-availability coordination can reduce this risk.

For financial operations, reconciliation and durable business identifiers remain important even with strong database replication.

### 4. Independent writes create divergent histories

If both isolated nodes accept authoritative updates, they can produce incompatible states.

When connectivity returns, simply combining those changes may not preserve the business invariant.

Quorum-based leadership can prevent a minority partition from independently becoming authoritative.

Fencing prevents a former leader from continuing to write after leadership has transferred.

Both mechanisms must be implemented and enforced correctly; they aren't just configuration labels.

### 5. CAP isn't a permanent classification into three product categories

The theorem concerns a specific impossibility involving strong consistency and availability when network partitions prevent communication.

Partition tolerance isn't normally something a distributed deployment can wish away.

A system's behavior also depends on the particular operation, deployment, consistency model, and failure assumptions.

Calling an entire database technology permanently CA or AP obscures these details.

A better explanation describes which operations remain available under which partition scenarios and what consistency guarantees they retain.

### 6. Replication slots may be retaining WAL

A disconnected replica using a replication slot can cause the primary to retain WAL that the replica still needs.

If the backlog grows unchecked, storage can fill.

Investigate replication-slot state, retained WAL volume, the replica's health, available disk space, and configured retention limits.

Do not casually delete PostgreSQL WAL files from the filesystem.

The safe recovery strategy depends on whether the replica can catch up, whether required WAL remains available, and whether rebuilding the replica is necessary.

---

# 20. Mental Model

Replication creates multiple copies of database state, but those copies do not automatically advance through history together.

When designing a replicated system, ask:

- **Where do writes become authoritative?** Identify the primary or coordination mechanism.
- **When is a write acknowledged?** Distinguish local commit, remote receipt, durable replication, and replay.
- **What freshness does a read require?** Choose primary routing, replica reads, or explicit read-after-write coordination.
- **What happens during a network partition?** Decide which operations may continue safely.
- **What happens during failover?** Account for replication lag, acknowledged writes, leader selection, and fencing.
- **How is replication health measured?** Monitor WAL progress, standby replay, recovery conflicts, and retained replication history.

The principle to remember is:

**Replication improves what a system can survive and how much work it can distribute, but every additional copy creates a question about which version of reality a caller is allowed to observe.**

Good distributed architecture answers that question according to the business operation, not through a universal slogan about strong or eventual consistency.

---

# Next Session — Scaling and Load Management

Your PostgreSQL primary is overloaded, so you add more application servers. Surprisingly, API latency becomes worse. Each new server opens another database connection pool, and the database spends increasing amounts of time coordinating work rather than completing it.

In **CS430-L03 — Scaling and Load Management**, we'll investigate why adding capacity can make a system slower, how bottlenecks migrate under load, and what throughput, saturation, backpressure, and queueing theory reveal about production performance.

---


---

## Next Lecture — CS430-L03: Scaling and Load Management

Continue in **CS430 — Distributed Systems and Reliable Workflows**.

## Further Reading

- **PostgreSQL — High Availability, Load Balancing, and Replication:** https://www.postgresql.org/docs/current/high-availability.html
- **PostgreSQL — Log-Shipping Standby Servers:** https://www.postgresql.org/docs/current/warm-standby.html
- **PostgreSQL — Replication Configuration:** https://www.postgresql.org/docs/current/runtime-config-replication.html
- **PostgreSQL — Hot Standby:** https://www.postgresql.org/docs/current/hot-standby.html
- **PostgreSQL — Monitoring Statistics:** https://www.postgresql.org/docs/current/monitoring-stats.html
- **PostgreSQL — Logical Replication:** https://www.postgresql.org/docs/current/logical-replication.html
- **Seth Gilbert and Nancy Lynch — Perspectives on the CAP Theorem:** https://dspace.mit.edu/entities/publication/dfcb6512-af44-4fc9-8e8b-1a8f28f1b53a

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
CS430-L02  CONSISTENCY, REPLICATION & AVAILABILITY — INTERVIEW GLANCE CARD

OPENING INCIDENT
  POST writes primary → 201; immediate GET on async replica → 404
  Both DBs healthy; different moments in history
  Multiple copies cannot always change simultaneously

WHY REPLICATE
  Read capacity / HA promotion / geo latency / isolate analytics
  Price = synchronization; replica ≠ free capacity (still replays WAL)

POSTGRESQL PHYSICAL STREAMING
  WAL → sender → network → receiver → write/flush → replay → visible
  Received WAL ≠ yet query-visible; track with LSNs
  Hot standby: read-only while replaying

ASYNC VS SYNC
  Async (default): fast commits; stale reads; failover may lose acked writes
  RPO = data-loss tolerance; RTO = downtime tolerance
  Sync waits for configured standby ack — needs synchronous_standby_names
  synchronous_commit modes (conceptual):
    local | remote_write | on (flush) | remote_apply | off
  remote_apply: ack after replay on participating standby — not every replica
  Sync trades write latency/availability for stronger replication guarantees

CONSISTENCY SPECTRUM (not one slogan)
  Read-your-writes   after my write, I see it
  Monotonic reads    don't move backward across replicas
  Consistent prefix  don't observe effects without causal priors
  Linearizability    real-time atomic single-copy illusion
  Linearizability ≠ transaction serializability
  Eventual consistency: converge under delivery/progress assumptions —
    not "always eventually fine despite permanent partitions"

READ-AFTER-WRITE FIXES
  A Read critical follow-ups from primary (often best SaaS default)
  B Temporary primary pin (heuristic; lag can exceed window)
  C Wait until replica replay LSN ≥ required; deadline + fallback

REPLICA LIMITS
  Replay uses CPU/IO; standby query conflicts with cleanup/replay
  max_standby_streaming_delay / hot_standby_feedback trade lag vs bloat
  Read replicas don't scale WRITES; primary still owns write + WAL

FAILOVER
  Promote lagging standby → missing previously acked txs (async)
  Split-brain: old + new primary both accept writes after partition heal
  Fencing: prevent former owner from authoritative writes
  DNS flip alone ≠ complete failover; reconnect + reintegrate old primary

QUORUM
  Majority needed for leadership → overlapping majorities prevent dual leaders
  3 voters: minority alone cannot claim authority
  Quorum can stop progress to preserve safety; witness ≠ full DB copy

CAP (USEFUL, OFTEN MISSTATED)
  Formal: linearizable consistency + availability under partitions — impossible
  "Pick 2 of 3" misleading; P not optional for multi-machine systems
  Healthy network can often provide C+A; partition forces the hard choice
  Not a permanent CA/AP product tattoo — reason per operation

BUSINESS MATRIX (examples)
  Hotel description / review count     often tolerate stale
  Search availability                  brief stale OK; booking revalidates
  New reservation details              read-your-writes desirable
  Last room allocate / captured payment strong authoritative coordination
  Availability ≠ lying 200 confirming unpaid bookings; prefer honest 503

OPS
  pg_stat_replication (sent/write/flush/replay + lag fields — interpret carefully)
  Standby: pg_is_in_recovery, receive vs replay LSN; idle primary ≠ lag
  Replication slots retain WAL for consumers — disconnected replica can fill disk
  max_slot_wal_keep_size: limit retention ↔ may force rebuild
  Physical = cluster standby; logical = publications/subscriptions (selective)
  Logical ≠ free multi-primary; schema/conflict management still needed

SENIOR LINE: every extra copy asks which version of reality a caller may see.
```

