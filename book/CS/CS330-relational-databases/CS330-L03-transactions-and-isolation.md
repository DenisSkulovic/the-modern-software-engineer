---
id: CS330-L03
course: CS330
title: "Transactions: When Correct Operations Produce Incorrect Results"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [BACK301-S04]
prev: CS330-L02
next: null
---



# CS330 — Relational Databases and Transactions

## Lecture 03: Transactions: When Correct Operations Produce Incorrect Results

*Two customers. One remaining hotel room. Two successful transactions. An outcome that should have been impossible.*

---

# 1. The Hotel That Sold Its Last Room Twice

It's Friday evening. A hotel in Copenhagen has one Deluxe room remaining for Saturday night. Two customers are looking at the hotel's booking page.

Alice is in Germany. Bob is in Sweden.

At 19:42:07, Alice clicks **Confirm Reservation**. Almost simultaneously, Bob clicks the same button.

The booking system receives two requests. Both execute essentially the same backend code:

```typescript
async function createReservation(input: ReservationInput) {
  return dataSource.transaction(async manager => {
    const available = await checkAvailability(
      manager,
      input.roomTypeId,
      input.dates
    );

    if (!available) {
      throw new Error("No rooms available");
    }

    return manager.save(Reservation, {
      ...input,
      status: "confirmed",
    });
  });
}
```

Looks reasonable. We're using a transaction.

We check availability before making the reservation. If availability is insufficient, we throw an error.

And if anything fails during persistence, the transaction rolls back. What could possibly go wrong?

Here's what actually happens.

<escape>

```text
TIME       ALICE'S TRANSACTION       BOB'S TRANSACTION
────────────────────────────────────────────────────────

19:42:07   BEGIN
19:42:07                              BEGIN

19:42:07   Check available rooms
           Result: 1

19:42:07                              Check available rooms
                                      Result: 1

19:42:07   Insert reservation

19:42:07                              Insert reservation

19:42:07   COMMIT

19:42:07                              COMMIT

────────────────────────────────────────────────────────

FINAL RESULT:

Available rooms originally: 1
New confirmed reservations: 2
```

</escape>

Both transactions succeed. Both customers receive confirmation.

Both database inserts are valid. No database constraint is necessarily violated.

And the hotel has a problem. A rather physical problem, in fact. There are now two paying customers expecting to sleep in one bed.

The most disturbing part is that **PostgreSQL may have executed both transactions exactly according to its documented guarantees**. There was no database malfunction.

The problem was our understanding of what a transaction guarantees.

We assumed that placing several operations inside a transaction made the entire business operation safe against concurrency. It doesn't necessarily.

A transaction protects certain properties of database operations. Which properties it protects depends on the isolation level, the operations involved, and the constraints we've defined.

Today we're going to dismantle this mystery.

We'll examine the guarantees of transactions, the mechanics of MVCC, the anomalies created by concurrent execution, and the tools PostgreSQL provides to prevent them.

By the end, the objective is to understand something more valuable than how to write `BEGIN` and `COMMIT`.

We want to recognize **when two individually correct operations can interact to violate a shared invariant—and how to make the database prevent it**.

---

# 2. What Is a Transaction Actually Supposed to Do?

Let's begin with the familiar acronym: ACID. You've probably encountered it countless times.

Atomicity. Consistency. Isolation. Durability. Most developers can recite these four properties.

Fewer can explain exactly what they promise. And that distinction matters enormously.

## Atomicity: all or nothing

Imagine transferring €100 from Account A to Account B. The operation requires two changes:

```sql
UPDATE accounts
SET balance = balance - 100
WHERE id = 'A';

UPDATE accounts
SET balance = balance + 100
WHERE id = 'B';
```

If the first operation succeeds but the second fails, €100 disappears from the represented account balances. Atomicity allows us to group the operations:

```sql
BEGIN;

UPDATE accounts
SET balance = balance - 100
WHERE id = 'A';

UPDATE accounts
SET balance = balance + 100
WHERE id = 'B';

COMMIT;
```

If the transaction aborts, neither change is committed. If the transaction commits successfully, both changes are committed.

That's atomicity. But notice what atomicity *doesn't* promise.

It doesn't promise that Account A originally contained €100. It doesn't promise that the two account IDs represent legitimate accounts.

And it doesn't promise that another transaction cannot interfere with our business assumptions.

Atomicity concerns the indivisibility of the transaction's database effects, not whether the underlying business operation was sensible.

## Consistency: the database must remain valid

Consistency is probably the most misunderstood ACID property. It doesn't mean that every query always returns the latest data.

It doesn't mean replicas are synchronized. And it doesn't mean the database understands every business rule automatically.

Instead, consistency concerns preserving the database's defined integrity requirements. Consider:

```sql
CREATE TABLE accounts (
  id TEXT PRIMARY KEY,
  balance NUMERIC(12, 2) NOT NULL,
  CHECK (balance >= 0)
);
```

PostgreSQL enforces the declared balance constraint. A transaction cannot successfully commit a row with `balance = -50`.

But what if our application requires total money across a collection of accounts to be conserved? PostgreSQL does not automatically know that rule.

We must design the operations and constraints that enforce it.

**A transaction cannot preserve a business invariant that neither the application nor the database properly enforces.**

This explains part of our hotel-booking mystery. We believed reservations must never exceed available inventory.

But had we actually encoded that invariant anywhere capable of enforcing it under concurrency? Not yet.

## Isolation: concurrent transactions should not interfere in prohibited ways

This is where our investigation becomes interesting.

Isolation defines which effects of concurrent transactions may become visible to one another and which combined outcomes are permitted.

Different isolation levels make different promises. At weaker levels, transactions may observe changing snapshots of data.

At stronger levels, the database prevents additional anomalies, sometimes by forcing a transaction to abort.

But the important detail is that **isolation is not necessarily equivalent to running every transaction one at a time**. That stronger guarantee belongs to serializability.

We'll get there.

## Durability: committed work survives failures

Once a transaction has committed successfully, PostgreSQL normally ensures that the committed changes survive a database process or system crash, using mechanisms such as write-ahead logging and recovery.

The precise guarantee depends on configuration and storage behavior. For example, deliberately disabling synchronous commit changes the crash-loss window.

Also, durability does not mean that data survives every conceivable catastrophe. Backups, replication, and disaster recovery remain separate concerns.

And there's an especially subtle distinction. Suppose the database commits successfully, but the network connection fails before the application receives the confirmation.

The application doesn't know whether the transaction committed. The transaction may be perfectly durable.

The caller's knowledge of its outcome is not. We'll encounter this uncertainty again in the distributed-systems sessions.

For now, the critical observation is:

**ACID is a collection of distinct guarantees. Atomicity does not imply serializability, and durability does not imply that the client knows what happened.**

---

# 3. Concurrency Creates a Second Dimension of Correctness

Imagine two transactions executing on a database. If we ran them strictly one after another, we'd have two possible orders.

```text
Option A:

Transaction Alice
      |
      v
Transaction Bob
```

Or:

```text
Option B:

Transaction Bob
      |
      v
Transaction Alice
```

In either order, Bob or Alice would discover that the last room was already taken. One reservation succeeds.

The other fails. The invariant is preserved.

But production databases don't ordinarily serialize every transaction. That would waste substantial opportunities for concurrent work.

Instead, operations from different transactions may overlap and interleave.

```text
Alice:  READ availability -------- INSERT -------- COMMIT
Bob:          READ availability -------- INSERT -------- COMMIT
```

Now the result depends on what each transaction can observe and which operations conflict.

Computer science has a useful term for the order in which concurrent operations occur:

**An execution schedule**, sometimes called a history. Different schedules can produce different outcomes, even when each transaction runs the same code.

### The idea of serializability

Suppose multiple transactions execute concurrently.

Their execution is *serializable* if the resulting behavior is equivalent to some valid serial execution of those transactions.

Not necessarily the order in which they started. Not necessarily the order in which their first queries completed.

Just some serial ordering consistent with the database's serializability rules.

In our hotel example, no serial ordering permits two successful reservations for the one remaining room, assuming each transaction correctly checks and consumes availability.

Therefore, the observed result is not serializable. That's the essential distinction.

A transaction can be atomic, durable, and internally reasonable while participating in a nonserializable execution. So how does PostgreSQL decide what each transaction sees?

To understand that, we need to revisit a mechanism introduced briefly in our previous sessions. MVCC.

---

# 4. MVCC: The Database That Remembers Several Versions of Reality

Imagine a database where every update immediately overwrites the existing value. A reader is examining a customer record.

Meanwhile, another transaction wants to modify it. How can the database prevent the reader from encountering an inconsistent intermediate state?

One traditional approach relies heavily on locking. Readers and writers coordinate access to shared records, potentially blocking one another.

PostgreSQL uses a different central mechanism:

**Multi-Version Concurrency Control**, or MVCC. The idea is that updating a row doesn't simply destroy the old version and replace it in place.

PostgreSQL maintains row versions whose visibility depends on transaction state and snapshots. Consider:

```text
Reservation 10842

Version 1:
  status = pending

Version 2:
  status = confirmed
```

Suppose Transaction A started reading before Transaction B committed the status change.

Depending on the isolation level, Transaction A may continue seeing the earlier version while another transaction sees the newer one. Conceptually:

```text
                  TIME ─────────────────────>

Transaction A:
    Snapshot created
          |
          v
    Sees: pending ──────────────────────────

Transaction B:
                 UPDATE status = confirmed
                            |
                          COMMIT

Transaction C:
                                   Snapshot
                                      |
                                      v
                                Sees: confirmed
```

These versions are not magical copies of the entire database.

PostgreSQL maintains tuple versions and metadata that allow it to determine which versions are visible to a particular snapshot.

Transaction identifiers and transaction status help determine whether a row version should be visible. This design has a remarkable consequence.

**Ordinary readers generally do not block writers, and writers generally do not block ordinary readers.**

A long-running analytical query can read a consistent snapshot while updates continue elsewhere. That's enormously useful.

But it introduces the concept at the center of this lecture:

A transaction's view of the database is not necessarily identical to the latest globally committed state. It's determined by visibility rules.

And those rules change with the isolation level.

### The cost of keeping old versions

MVCC also has operational consequences. Old row versions cannot necessarily be discarded immediately.

A transaction may still need them. PostgreSQL therefore relies on vacuuming and related maintenance to reclaim reusable space and manage visibility information.

Long-running transactions can prevent old row versions from being cleaned up. This can contribute to table bloat and storage pressure.

So an application that begins a transaction and leaves it open for fifteen minutes isn't merely holding a connection. It may also interfere with database maintenance.

We won't explore vacuum internals today, but the connection is worth remembering:

**Concurrency guarantees have physical storage and operational costs.**

Now let's examine the isolation levels.

---

# 5. Read Committed: A New Snapshot for Every Statement

PostgreSQL's default transaction isolation level is **Read Committed**. It's appropriate for many ordinary application operations.

But understanding its limitations is essential.

In Read Committed, each ordinary `SELECT` statement sees a snapshot reflecting data committed before that statement began, along with the transaction's own changes.

Two successive statements within the same transaction can therefore see different committed database states. Let's reproduce the idea.

Transaction A begins:

```sql
BEGIN;

SELECT balance
FROM accounts
WHERE id = 'A';
```

Result:

```text
balance = 100
```

Meanwhile, Transaction B executes:

```sql
BEGIN;

UPDATE accounts
SET balance = 150
WHERE id = 'A';

COMMIT;
```

Transaction A executes the same query again:

```sql
SELECT balance
FROM accounts
WHERE id = 'A';
```

Now the result is:

```text
balance = 150
```

Transaction A has not committed or rolled back. Yet it has observed two different values for the same row.

This is called a **non-repeatable read**. Nothing is broken.

It's permitted by Read Committed.

### What about dirty reads?

A dirty read occurs when one transaction reads another transaction's uncommitted changes.

PostgreSQL does not permit dirty reads, even when you request the SQL-standard `READ UNCOMMITTED` isolation level.

In PostgreSQL, Read Uncommitted effectively behaves like Read Committed. That's an important PostgreSQL-specific detail.

### The phantom read

Now consider a query involving several rows.

```sql
SELECT COUNT(*)
FROM reservations
WHERE hotel_id = 482
  AND status = 'confirmed';
```

Transaction A receives:

```text
125 reservations
```

Transaction B inserts a new matching reservation and commits. Transaction A repeats its query.

Now it sees:

```text
126 reservations
```

The result set has changed because a new matching row appeared. This is a *phantom read*.

It illustrates why reasoning about concurrency requires more than tracking updates to existing rows. New rows can change the truth of a business condition.

And that is precisely what happened in our double-booking example. Both transactions asked:

> How many confirmed reservations already exist?

Both received an answer that was correct at the time of their respective queries. Neither answer guaranteed that the result would remain valid until the transaction committed.

---

# 6. Lost Updates: When Two Writers Disagree About the Past

Let's examine another classic anomaly. Suppose a hotel inventory record contains:

```text
remaining_rooms = 5
```

Two processes want to reserve one room. Both read the value.

Both receive 5. Both calculate:

```typescript
const newValue = remainingRooms - 1;
```

Both issue:

```sql
UPDATE inventory
SET remaining_rooms = 4
WHERE id = 1;
```

What happens? Both updates can eventually succeed under Read Committed.

The second writer may wait for the first writer's row lock to be released. But it's still assigning the stale value `4`.

The database ends up with four remaining rooms. Two reservations were made.

Only one unit was deducted. This is a form of **lost update**.

The problem is that the application calculated a new state using information that was no longer current.

### Not all updates have this problem

Now compare:

```sql
UPDATE inventory
SET remaining_rooms = remaining_rooms - 1
WHERE id = 1;
```

This is different. The arithmetic happens inside the database statement.

Under PostgreSQL Read Committed, concurrent updates to the same row coordinate through row locking.

If another transaction updates the row first, the waiting updater can proceed against the updated row version once the first transaction commits.

The second decrement therefore applies to the new value. Starting with five rooms, two successful decrements produce three.

That's what we wanted. This distinction is remarkably useful.

**Reading a value into application memory, modifying it, and writing it back is not equivalent to asking the database to atomically modify the current value.**

The second approach can avoid a whole category of stale-state problems. But we're not finished.

What if the inventory contains zero rooms? We don't want the value to become negative.

And we don't want to insert a reservation unless the inventory update succeeds. We need a stronger operation.

We'll design one shortly. First, let's examine what happens when we increase the isolation level.

---

# 7. Repeatable Read: A Stable Snapshot Can Still Lie About the Whole System

You might now propose a seemingly elegant solution. Why not change the isolation level to Repeatable Read?

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ;
```

In PostgreSQL, Repeatable Read provides a stable snapshot for the transaction.

The snapshot is established at the first relevant statement, rather than automatically at `BEGIN`.

Subsequent ordinary reads continue observing the same committed database state, together with the transaction's own changes. Non-repeatable reads disappear.

Phantom reads are also prevented in PostgreSQL's implementation, which is stronger in this respect than the SQL standard's minimum requirement for Repeatable Read. Excellent.

So our booking problem is solved? Not necessarily.

In fact, a stable snapshot can make the underlying danger easier to demonstrate.

### The two doctors problem

Imagine a hospital where at least one doctor must remain on duty. Two doctors are currently available:

```text
Doctor Alice: on_duty = true
Doctor Bob:   on_duty = true
```

Alice wants to leave. Her transaction checks whether another doctor is on duty.

Yes—Bob is available. So Alice marks herself off duty.

Simultaneously, Bob wants to leave. His transaction checks whether another doctor is on duty.

Yes—Alice is available. So Bob marks himself off duty.

Under Repeatable Read, both transactions may operate using snapshots in which both doctors are on duty. Alice updates her own row.

Bob updates his own row. They aren't modifying the same database row.

Both transactions can commit. Final state:

```text
Doctor Alice: on_duty = false
Doctor Bob:   on_duty = false
```

No doctors remain on duty. Each transaction made a locally reasonable decision.

Together they violated a global invariant. This anomaly is called **write skew**.

### Why row-level conflict detection doesn't save us

PostgreSQL's Repeatable Read prevents certain conflicting updates to the same row.

For example, if two transactions try to update the same existing row based on incompatible snapshots, one can receive a serialization failure.

But our doctors update different rows. The conflict lies in what each transaction *read* when deciding what to write.

Alice's decision depends on Bob's status. Bob's decision depends on Alice's status.

Their writes affect the truth of each other's earlier reads. That's the dangerous relationship.

And the same pattern can arise in hotel bookings. One transaction counts existing reservations.

Another does the same. Each inserts a different reservation row.

Neither updates an existing reservation row that the other is trying to modify. Both can commit under Repeatable Read.

**A stable snapshot is not the same thing as a serializable execution.**

This is one of the most important distinctions in practical database concurrency.

---

# 8. The Isolation Levels Compared

We now have enough context to compare PostgreSQL's isolation levels meaningfully.

| Isolation level | Dirty reads | Non-repeatable reads | Phantoms | Serialization anomalies |
|---|---|---|---|---|
| Read Uncommitted | Prevented in PostgreSQL | Possible | Possible | Possible |
| Read Committed | Prevented | Possible | Possible | Possible |
| Repeatable Read | Prevented | Prevented | Prevented | Possible |
| Serializable | Prevented | Prevented | Prevented | Prevented |

A few details deserve emphasis. Read Uncommitted is not a distinct weaker implementation in PostgreSQL; it behaves as Read Committed.

PostgreSQL's Repeatable Read is based on snapshot isolation and prevents phantoms, but can permit write skew.

Serializable provides the strongest isolation semantics, but the application must handle transaction failures and retries.

The table is useful, but don't memorize it as the entire subject. The real skill is recognizing the shape of an operation.

Are we updating one row? Are we deriving a write from an earlier read?

Are we checking a condition across multiple rows? Could another transaction insert a row that invalidates our decision?

These questions determine whether our chosen isolation and locking strategy is sufficient.

---

# 9. Serializable: The Database Refuses an Impossible History

Let's return to the two doctors. Alice's transaction reads Bob's availability and marks Alice off duty.

Bob's transaction reads Alice's availability and marks Bob off duty. If they executed sequentially, one would discover that the other had already left.

Both cannot successfully leave in a correct serial execution. PostgreSQL's Serializable isolation level detects conflicts that could produce such nonserializable outcomes.

It uses a mechanism called **Serializable Snapshot Isolation**, or SSI. The key idea is rather clever.

PostgreSQL doesn't simply force every transaction to execute one after another.

Instead, it allows considerable concurrency while tracking read/write dependencies that could make the committed history inconsistent with serial execution.

When it detects an unsafe situation, it aborts a transaction. The application may receive:

```text
ERROR: could not serialize access due to
read/write dependencies among transactions
```

With SQLSTATE:

```text
40001
```

That's `serialization_failure`. One transaction succeeds.

The other must retry. When retried, the operation obtains a new snapshot and reevaluates the business condition.

It can now discover that the invariant would be violated.

### Serializable is not a giant database lock

It's tempting to imagine Serializable as a mode that locks the entire database. That is not how PostgreSQL implements it.

Its SSI mechanism tracks dangerous dependencies using predicate-locking information and related concurrency machinery.

These predicate locks are not ordinary blocking row locks. Their purpose is to detect conflicts, not to stop every writer immediately.

This allows substantial concurrency. However, Serializable has costs.

Conflict tracking consumes resources. Some transactions must be retried.

Under contention, retries can increase latency and wasted work. The database may occasionally abort a transaction conservatively to prevent a possible anomaly.

And applications must be designed to recover from those failures.

### An essential qualification

Serializable reasoning applies to transactions participating appropriately in the relevant isolation and correctness strategy.

You cannot make one operation safe merely by changing its isolation level while unrelated write paths continue modifying the same business state without respecting the intended invariant.

A correctness strategy must cover **every operation capable of violating the rule**.

That might involve serializable transactions, database constraints, carefully coordinated locks, or atomic conditional updates.

The important goal is not to enable a prestigious-sounding isolation level. It's to enforce a particular invariant.

---

# 10. Pessimistic Locking: Take the Resource Before Somebody Else Does

Let's consider another approach. Suppose our hotel keeps a row describing available inventory for a particular room type and date.

```text
room_type_id = 42
night        = 2026-11-14
remaining    = 1
```

Instead of merely reading the row, we can lock it.

```sql
BEGIN;

SELECT remaining
FROM room_inventory
WHERE room_type_id = 42
  AND night = DATE '2026-11-14'
FOR UPDATE;
```

`FOR UPDATE` acquires a row-level lock that conflicts with other transactions attempting certain operations on the same row.

If Alice has locked the inventory row, Bob's conflicting lock request waits. Alice checks the inventory, creates the reservation, decrements availability, and commits.

Only then can Bob proceed. Under Read Committed, Bob's locking read can return the updated version of the row after waiting.

He discovers that no rooms remain. His booking fails.

That's **pessimistic concurrency control**. We're assuming contention is possible and coordinating access before performing the dependent operation.

### The power and limitations of row locks

Row-level locks are excellent when all competing operations share a clearly identified row. But suppose the business rule is:

> No more than ten reservations may exist for this category and date.

You query:

```sql
SELECT *
FROM reservations
WHERE room_type_id = 42
  AND night = DATE '2026-11-14'
FOR UPDATE;
```

What if there are currently no matching rows? There's nothing to lock.

Locking existing reservation rows does not automatically prevent another transaction from inserting a new matching row.

PostgreSQL does not turn every `SELECT FOR UPDATE` predicate into a general-purpose blocking range lock. This is a common mistake.

**A row lock protects a row. It does not automatically protect the absence of rows or every possible future row matching a condition.**

That's why a dedicated inventory row can be useful. Every transaction competing for the same room type and night can coordinate through the same record.

But all booking paths must respect that protocol.

If one integration bypasses inventory allocation and directly inserts confirmed reservations, the locking design no longer protects the business invariant.

---

# 11. The Atomic Conditional Update: Often the Simplest Good Solution

Let's improve our inventory design.

Instead of reading availability, locking manually, calculating a new value, and writing it back, we can ask PostgreSQL to perform the entire condition and modification atomically.

```sql
UPDATE room_inventory
SET remaining = remaining - 1
WHERE room_type_id = 42
  AND night = DATE '2026-11-14'
  AND remaining > 0
RETURNING remaining;
```

This is a powerful pattern. The statement means:

> Decrease availability by one, but only if the currently eligible row still has positive availability.

Suppose two transactions attempt this simultaneously. Initially:

```text
remaining = 1
```

Alice obtains the row lock and updates it to zero. Bob attempts the same update.

He waits for Alice's transaction. If Alice commits, PostgreSQL rechecks the update condition against the updated row under Read Committed.

Now:

```text
remaining > 0
```

is false. Bob updates zero rows.

The application can interpret that as unavailable inventory. No separate stale availability calculation is required.

### The transaction must still connect inventory and reservation

Of course, we don't want to decrement inventory without creating the reservation. So:

```sql
BEGIN;

UPDATE room_inventory
SET remaining = remaining - 1
WHERE room_type_id = 42
  AND night = DATE '2026-11-14'
  AND remaining > 0
RETURNING remaining;

-- Only continue if exactly one row was updated.

INSERT INTO reservations (
  room_type_id,
  check_in,
  check_out,
  status
)
VALUES (
  42,
  DATE '2026-11-14',
  DATE '2026-11-15',
  'confirmed'
);

COMMIT;
```

The application must verify that the update returned exactly one row before inserting.

If no row was updated, it should roll back or terminate the transaction without creating a reservation. If the insert fails, the inventory decrement rolls back.

For a multi-night booking, every night's inventory allocation must succeed within the transaction. If any night cannot be allocated, the entire allocation must be undone.

And concurrent multi-night bookings should lock inventory rows in a consistent order to reduce deadlocks.

### Why I like this approach

For inventory rows that represent authoritative remaining capacity, atomic conditional updates are often a better default than a separate availability read plus hope that isolation will save you. They coordinate through the shared resource itself and don't require Serializable merely to keep a counter non-negative—but they still depend on a sound inventory model. If capacity is computed dynamically from several tables, or inventory can be modified through many independent operations, the design may need additional coordination.

The correct concurrency mechanism follows the shape of the business invariant.

---

# 12. Optimistic Concurrency: Don't Lock Until You Know There's a Conflict

Pessimistic locking coordinates access before a contested modification. Optimistic concurrency control takes a different approach.

It allows operations to proceed based on an observed version, then rejects the write if that version is no longer current. Suppose a reservation has:

```text
id      = 10842
status  = pending
version = 7
```

The application reads it and prepares a change. Instead of:

```sql
UPDATE reservations
SET status = 'confirmed'
WHERE id = 10842;
```

we execute:

```sql
UPDATE reservations
SET
  status = 'confirmed',
  version = version + 1
WHERE id = 10842
  AND version = 7
RETURNING id, version;
```

If no other transaction changed the row, the update succeeds. The version becomes eight.

If another operation has already modified the reservation and incremented the version, the condition no longer matches. Zero rows are updated.

The application detects a conflict. This is commonly called **optimistic locking**, although it doesn't necessarily involve a database lock acquired during the initial read.

It's also a form of compare-and-swap behavior.

### When is it useful?

Imagine two hotel employees editing a reservation. Alice changes the check-in time.

Bob changes the guest count. Both opened the reservation when its version was seven.

Alice saves first. The version becomes eight.

Bob attempts to save his stale version-seven representation. The update fails.

Now Bob can refresh the record and decide how to merge or reapply his changes. Without version checking, Bob's stale update might overwrite Alice's work.

Optimistic concurrency is attractive when conflicting modifications are relatively rare. It avoids holding a database transaction open while a user thinks about an edit.

### Its limitation

A version column on an individual reservation protects that reservation against conflicting updates.

It doesn't automatically protect an invariant involving many different reservations.

If Alice inserts Reservation A and Bob inserts Reservation B, neither necessarily conflicts on a shared versioned row.

For aggregate rules, optimistic control must coordinate through a shared version, predicate-aware mechanism, constraint, or other enforcement strategy.

This is why the right question is not:

> Should I use optimistic or pessimistic locking?

It's:

> What exact shared state or invariant can competing operations invalidate?

Only then can you identify the correct coordination point.

---

# 13. Deadlocks: When Everyone Politely Waits Forever

Locks prevent many concurrency anomalies. But they introduce another kind of problem.

Imagine a reservation workflow that updates two inventory rows. Alice books nights Friday and Saturday.

Bob books the same nights. Alice locks Friday first.

Bob locks Saturday first. Then Alice attempts to lock Saturday.

She must wait for Bob. Bob attempts to lock Friday.

He must wait for Alice. Neither can proceed.

```text
Transaction Alice              Transaction Bob

Locks Friday                   Locks Saturday
     |                              |
     v                              v
Requests Saturday             Requests Friday
     |                              |
     +---------- WAIT --------------+
     |                              |
     +---------- WAIT --------------+
```

This is a **deadlock**. Fortunately, PostgreSQL doesn't allow such a cycle to remain unresolved indefinitely.

Its deadlock-detection machinery can identify the problem and abort one of the transactions. The application receives an error such as:

```text
SQLSTATE 40P01 — deadlock_detected
```

The surviving transaction can proceed.

### Avoiding deadlocks

One highly practical technique is acquiring locks in a consistent order. For example, always process inventory rows in ascending date order.

Then both Alice and Bob attempt Friday before Saturday. One waits for Friday.

The other proceeds through the dates and commits. No circular wait is created by that particular sequence.

Other useful practices include keeping transactions short, avoiding unnecessary locks, and acquiring the intended lock strength deliberately.

But deadlocks cannot always be eliminated. Complex systems have multiple transaction paths and competing resources.

A robust application should be prepared to retry appropriate deadlock failures.

### Don't confuse waiting with deadlocking

A transaction waiting for another transaction's row lock is not automatically deadlocked. Ordinary lock waiting is part of concurrency control.

A deadlock requires a circular dependency that prevents progress. Lock waiting can still cause serious latency, however.

PostgreSQL provides tools such as `pg_stat_activity` and `pg_locks` to investigate blocking and lock contention.

And this is where poor transaction boundaries become expensive.

A transaction that holds inventory locks while calling an external payment provider may block other bookings for several seconds.

The database isn't slow because its arithmetic is difficult. It's slow because one operation owns a resource that others need.

This brings us to transaction design at the application level.

---

# 14. Where Should a Transaction Begin and End?

Recall the architecture we developed in SE320-L01.

```text
HTTP Controller
      |
      v
Application Service
      |
      +-- Domain Logic
      |
      +-- Repositories
      |
      +-- External Services
```

Where does the transaction belong? Typically, around a coherent unit of database work required to preserve a business operation's invariants.

For example:

```typescript
await dataSource.transaction(
  "READ COMMITTED",
  async manager => {
    const inventory = await allocateInventory(
      manager,
      booking
    );

    if (!inventory.success) {
      throw new InventoryUnavailableError();
    }

    await createReservation(manager, booking);

    await recordOutboxEvent(manager, booking);
  }
);
```

The precise implementation depends on the domain, but the transaction encompasses the database changes that must succeed or fail together.

An important TypeORM detail: operations belonging to the transaction must use the transaction-provided entity manager or repositories derived from it.

If a nested service silently uses the global `dataSource.manager`, it may execute operations outside the intended transaction.

That's an excellent way to introduce bugs that only appear during failures.

### The dangerous external call

Now imagine:

```typescript
await dataSource.transaction(async manager => {
  await allocateInventory(manager, booking);

  await paymentProvider.chargeCustomer(payment);

  await createReservation(manager, booking);
});
```

This looks attractive. Everything appears to belong to one use case.

But the payment provider does not participate in your PostgreSQL transaction.

If the database rolls back after payment succeeds, PostgreSQL cannot reverse the charge automatically.

If the payment provider takes eight seconds to respond, your database transaction may hold locks and a connection for eight seconds.

And if the provider times out, you may not know whether the charge occurred.

The correct design often separates local atomic persistence from external side effects, using durable workflow state, idempotency, and reconciliation.

We'll investigate those patterns in Sessions 7 and 11. For now, a useful principle is:

**A database transaction should protect the smallest coherent unit of database state that must change atomically—not the entire duration of a complicated business process involving unreliable external systems.**

Small does not mean artificially splitting an operation that requires atomicity. It means avoiding unnecessary work while scarce database resources and locks are held.

---

# 15. Retrying Transactions Without Making Things Worse

Serializable transactions can fail with SQLSTATE `40001`. Deadlocks can fail with `40P01`.

These errors often justify retrying the transaction. But retrying correctly is more subtle than repeating the final SQL statement.

Suppose the original transaction:

1. Reads available inventory.
2. Determines a price.
3. Selects a particular room.
4. Inserts the reservation.

If the transaction fails because the concurrent world changed, retrying only the insert is not sufficient. The business decision must be reevaluated against fresh data.

PostgreSQL's guidance is to retry the **complete transaction**, including the logic that determines which statements and values to use. A simplified Node.js retry wrapper:

```typescript
const RETRYABLE_CODES = new Set([
  "40001", // serialization_failure
  "40P01", // deadlock_detected
]);

async function runWithRetry<T>(
  operation: () => Promise<T>,
  maxAttempts = 3
): Promise<T> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await operation();
    } catch (error: any) {
      const code = error?.driverError?.code ?? error?.code;

      if (
        !RETRYABLE_CODES.has(code) ||
        attempt === maxAttempts
      ) {
        throw error;
      }

      const delay =
        Math.min(100 * 2 ** (attempt - 1), 1000) *
        (0.5 + Math.random());

      await new Promise(resolve =>
        setTimeout(resolve, delay)
      );
    }
  }

  throw new Error("Unreachable");
}
```

This is a teaching-level wrapper: production code should also account for deadlines, cancellation, error classification, and the application's response contract.

Usage might look like:

```typescript
const reservation = await runWithRetry(() =>
  dataSource.transaction(
    "SERIALIZABLE",
    async manager => {
      return createReservationTransaction(
        manager,
        command
      );
    }
  )
);
```

Each attempt begins a fresh transaction. The complete decision process runs again.

The retry is bounded. And a little randomized delay reduces synchronized retry storms.

### The crucial warning

Never blindly retry a transaction callback that performs irreversible external side effects.

If the callback charges a payment card and then the database aborts, automatically retrying the entire callback might charge the customer again.

Retries must operate within clearly defined side-effect boundaries. A reliable workflow requires idempotency and durable coordination around external effects.

Also, not every database constraint error is transient.

A unique-key violation may represent a legitimate duplicate business request rather than a concurrency anomaly that should be retried.

Error classification is part of correctness.

---

# 16. Practical Lab: Make PostgreSQL Double-Book a Room

This is one of the most valuable experiments in the course. You need PostgreSQL and **two independent SQL sessions**.

For example, open two `psql` terminals connected to the same disposable database. We'll call them Terminal A and Terminal B.

The experiment uses one available room and an intentionally unsafe reservation strategy.

## Part A — Reproduce the double booking

First, run this setup once:

```sql
DROP TABLE IF EXISTS demo_bookings;

CREATE TABLE demo_bookings (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  hotel_id INTEGER NOT NULL,
  night DATE NOT NULL,
  customer TEXT NOT NULL
);
```

Assume the hotel has capacity for exactly one booking on November 14. In Terminal A:

```sql
BEGIN ISOLATION LEVEL READ COMMITTED;

SELECT COUNT(*)
FROM demo_bookings
WHERE hotel_id = 1
  AND night = DATE '2026-11-14';
```

Result:

```text
0
```

Don't commit yet. In Terminal B:

```sql
BEGIN ISOLATION LEVEL READ COMMITTED;

SELECT COUNT(*)
FROM demo_bookings
WHERE hotel_id = 1
  AND night = DATE '2026-11-14';
```

Result:

```text
0
```

Now both transactions believe the room is available. In Terminal A:

```sql
INSERT INTO demo_bookings (hotel_id, night, customer)
VALUES (1, DATE '2026-11-14', 'Alice');
```

In Terminal B:

```sql
INSERT INTO demo_bookings (hotel_id, night, customer)
VALUES (1, DATE '2026-11-14', 'Bob');
```

Now commit both transactions.

```sql
COMMIT;
```

Finally:

```sql
SELECT *
FROM demo_bookings;
```

You should see two bookings. Both transactions committed.

The business invariant failed.

## Part B — Try Repeatable Read

Reset the data after both earlier transactions have finished:

```sql
TRUNCATE demo_bookings RESTART IDENTITY;
```

Now repeat the experiment, but start both transactions with:

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ;
```

Have both sessions perform their `COUNT(*)` query before either commits. Then insert a booking in each transaction and commit both.

What happens? Both can still commit.

Why? Because the transactions insert different rows, and their stable snapshots don't establish the necessary serializability guarantee.

This is the anomaly we've been investigating.

## Part C — Try Serializable

Reset again:

```sql
TRUNCATE demo_bookings RESTART IDENTITY;
```

Start both sessions with:

```sql
BEGIN ISOLATION LEVEL SERIALIZABLE;
```

Again, both sessions query the booking count before either inserts. Both initially see zero.

Have each insert a booking. Then commit Terminal A.

Attempt to commit Terminal B. This time, PostgreSQL should reject one of the conflicting transactions with a serialization failure.

The exact point at which the failure becomes visible can depend on the execution, but PostgreSQL must prevent both conflicting transactions from committing as a nonserializable history.

The application would need to retry the aborted transaction. On retry, it would observe the existing booking and reject the attempt to reserve capacity beyond one.

Notice the critical difference:

Read Committed allowed both transactions to succeed. Repeatable Read could also allow both to succeed.

Serializable prevented the incompatible committed history.

## Part D — A simpler solution for explicit inventory

Let's try a different model.

```sql
CREATE TABLE demo_inventory (
  hotel_id INTEGER NOT NULL,
  night DATE NOT NULL,
  remaining INTEGER NOT NULL
    CHECK (remaining >= 0),

  PRIMARY KEY (hotel_id, night)
);

INSERT INTO demo_inventory
VALUES (1, DATE '2026-11-14', 1);
```

In Terminal A:

```sql
BEGIN;

UPDATE demo_inventory
SET remaining = remaining - 1
WHERE hotel_id = 1
  AND night = DATE '2026-11-14'
  AND remaining > 0
RETURNING remaining;
```

Result:

```text
remaining = 0
```

Don't commit yet. In Terminal B, run the same transaction and update.

Terminal B should wait on the conflicting row update. Now commit Terminal A.

Terminal B can proceed. Its update returns no rows because the condition `remaining > 0` is no longer true.

It cannot claim the room. Rollback or finish Terminal B without inserting a reservation.

We've enforced the inventory invariant without requiring Serializable isolation.

The difference is that both transactions now compete through a common, authoritative inventory row. That's a powerful design pattern.

### What this lab proves

It isn't enough to say:

> We use transactions.

You need to answer:

> Which state do competing transactions coordinate through, and what exact guarantee prevents an invalid combined outcome?

Sometimes the answer is a unique constraint. Sometimes an exclusion constraint.

Sometimes an atomic conditional update. Sometimes explicit locking.

Sometimes Serializable isolation. And sometimes a combination.

The appropriate mechanism depends on the invariant.

---

# 17. Choosing the Right Strategy in Real Systems

Let's consolidate the available techniques.

| Mechanism | Strong use case | Important limitation |
|---|---|---|
| Unique constraint | Preventing duplicate keys or identities | Doesn't express arbitrary business rules |
| Exclusion constraint | Preventing overlapping physical-room reservations | Not a general pooled-capacity solution |
| Atomic conditional update | Claiming limited inventory represented by shared rows | Requires a suitable shared-state model |
| `SELECT FOR UPDATE` | Coordinating modifications to existing rows | Doesn't lock absent rows |
| Optimistic version check | Preventing stale updates to existing entities | Doesn't automatically protect cross-row invariants |
| Repeatable Read | Stable transaction snapshots | Can permit write skew |
| Serializable | Preventing nonserializable committed histories | Requires retry handling and has overhead |

There's no universally superior option. But we can make practical recommendations.

### For simple counters and inventory allocations

Prefer an atomic conditional update when the business rule can be cleanly represented that way. It's often efficient, explicit, and easy to reason about.

### For entity editing

Optimistic concurrency using a version column is frequently an excellent choice. Especially when users may hold an editing screen open for minutes.

### For contested multi-row resources

Explicit row locking can work well if competing operations have a well-defined shared resource to coordinate through. Acquire locks consistently and keep transactions short.

### For complex predicate-based invariants

Serializable transactions are worth serious consideration. They can reduce the need to invent intricate manual locking protocols.

But the entire relevant workflow must participate appropriately, and retries must be handled correctly.

### For rules naturally expressible as database constraints

Use constraints.

An overlapping-room prohibition implemented through a PostgreSQL exclusion constraint can be stronger and simpler than relying entirely on application-level checks.

### What about distributed locks?

You might be tempted to introduce Redis locks for booking coordination.

For a business invariant that lives in PostgreSQL, I would generally avoid making an external distributed lock the primary correctness mechanism unless there's a compelling architectural reason.

Redis locking introduces another system whose availability, failure behavior, lease expiration, and ownership semantics must be understood. A process can pause.

A lock lease can expire. Another process can acquire the lock while the original process is still capable of writing.

Without appropriate fencing or database-side enforcement, the lock may not provide the guarantee you expected.

If PostgreSQL can directly enforce the invariant, that's usually a better place to begin. We'll revisit distributed coordination later.

---

# 18. Engineering and Interview Challenges

Now try applying the mechanisms to unfamiliar problems.

## Question 1 — The misleading transaction

Two customers attempt to purchase the final concert ticket. Each transaction performs:

1. `SELECT COUNT(*)` of existing ticket allocations.
2. Checks that the count is below capacity.
3. Inserts a new allocation.
4. Commits.

The database uses Read Committed. Why is wrapping the operation in a transaction insufficient?

What are two plausible fixes?

## Question 2 — Lost update or safe update?

Two transactions execute:

```sql
UPDATE accounts
SET balance = balance - 100
WHERE id = 1;
```

The original balance is €500. Will PostgreSQL necessarily lose one deduction under Read Committed?

How does this differ from reading €500 into application memory and later executing `SET balance = 400`?

## Question 3 — The empty result problem

You execute:

```sql
SELECT *
FROM reservations
WHERE room_id = 204
  AND check_in = DATE '2026-11-14'
FOR UPDATE;
```

No rows are returned. Does this prevent another transaction from inserting a matching reservation?

Why or why not?

## Question 4 — The dangerous retry

Your transaction:

1. Creates an inventory hold.
2. Charges a credit card through an external provider.
3. Writes a confirmed reservation.

The database reports a serialization failure. Your retry wrapper executes all three steps again.

What's wrong with this design?

## Question 5 — Optimistic locking

Two administrators load Reservation 10842 at version 7. One changes its status to confirmed.

The other changes its guest count. Both attempt to update using `WHERE version = 7`.

What happens? How should the application respond to the second update?

## Question 6 — Serializable everywhere?

A colleague proposes switching the entire PostgreSQL application to Serializable isolation to eliminate all concurrency bugs. Would you support this?

What guarantees would improve, and what problems would remain?

---

# 19. Solutions and Discussion

## 1. The count-and-insert operation has a concurrency gap

The transactions read a condition that can be invalidated by concurrent inserts. Their separate inserted rows need not conflict under Read Committed.

One solution is to represent the remaining ticket capacity in a shared inventory row and claim it through an atomic conditional update.

Another is to use Serializable transactions and retry failures, ensuring the relevant competing operations respect the same concurrency strategy.

For individually numbered seats, a unique constraint on event and seat identity may be even simpler.

The right design follows whether we're selling interchangeable capacity or identified resources.

## 2. The database-side decrement is different

PostgreSQL coordinates concurrent row updates. Under Read Committed, a waiting update can operate against the row version committed by the earlier updater.

Two successful `balance = balance - 100` operations can therefore reduce €500 to €300.

If both application processes previously read €500 and separately assign the calculated value €400, the second stale assignment can overwrite the effect of the first.

The difference is between modifying the current database value and assigning a previously calculated value.

For financial systems, additional conditions and ledger integrity rules would normally be necessary.

## 3. You cannot row-lock a nonexistent row

`SELECT FOR UPDATE` locks returned rows. If no matching rows exist, there is no matching row lock protecting that absence.

Another transaction may insert a row satisfying the condition.

You need a constraint, an appropriate shared coordination row, Serializable isolation, or another strategy that protects the intended invariant.

## 4. PostgreSQL cannot roll back the card charge

The external payment provider is not part of the PostgreSQL transaction.

A serialization failure can roll back the database work, but it cannot automatically undo an external charge. Retrying the entire callback may charge the customer again.

The workflow needs separate durable states, idempotency controls, and recovery logic for the payment operation. We will explore payment workflow correctness in CS430-L05.

## 5. The second update fails its version check

The first successful update changes the version from seven to eight. The second operation still requires version seven.

Its update affects zero rows.

The application should recognize a stale-state conflict and decide whether to refresh, merge, retry after reevaluating the change, or ask the user to resolve the conflict.

Silently overwriting the newer state defeats the purpose of optimistic concurrency.

## 6. Serializable is not a universal cure

Serializable prevents committed histories that are inconsistent with serial execution of appropriately participating transactions. That's a strong guarantee.

But it introduces serialization failures that applications must retry. It can increase overhead and latency under contention.

It doesn't automatically express business rules. It doesn't protect operations outside the relevant transactional protocol.

And it doesn't make external APIs participate atomically in PostgreSQL transactions. For straightforward single-row resource claims, a conditional update may be simpler.

For complex multi-row invariants, Serializable may be an excellent choice.

The correct decision depends on the workload and invariant, not a blanket preference for maximum isolation.

---

# 20. The Mental Model to Keep

Transactions are not magical protective bubbles around business logic. They provide particular guarantees about database operations.

And the most important insight from this session is that **correctness must be evaluated across concurrent operations, not merely within individual transactions**.

Here's the conceptual progression we've established. **Atomicity** makes a group of database changes succeed or fail together.

**MVCC** allows PostgreSQL to maintain multiple row versions and serve transaction-dependent snapshots.

**Read Committed** provides statement-level snapshots and prevents dirty reads, but allows changing observations and serialization anomalies.

**Repeatable Read** provides a stable snapshot, but doesn't prevent every invalid interaction between transactions.

**Serializable** prevents nonserializable committed histories, at the cost of possible transaction aborts and retries.

**Pessimistic locking** coordinates contested resources before modification. **Optimistic concurrency control** detects when the state an operation relied upon has changed.

**Atomic conditional updates** combine checking and modifying shared state into a single coordinated database operation.

**Constraints** can enforce certain invariants independently of which application code writes the data.

And **transaction boundaries** determine which database effects are coordinated atomically—and which external effects remain outside that protection.

When evaluating a concurrent workflow, the most useful questions are:

> What business invariant must always hold?

> Which concurrent operations can violate it?

> What shared data do those operations read or modify?

> Where is the authoritative enforcement mechanism?

> What happens when two operations reach that mechanism simultaneously?

> How does the application respond when one operation must wait, fail, or retry?

If you can answer those questions, you can reason about a remarkable range of production problems. Hotel inventory.

Concert tickets. Bank balances.

Coupon redemptions. Warehouse stock.

Subscription limits. Financial ledgers.

Appointment scheduling. Even distributed agent workflows coordinating access to limited resources.

The technologies differ, but the underlying problem often has the same shape. Several operations are trying to make decisions about shared mutable state.

And those decisions must remain valid when the operations overlap. That's the real subject of transaction engineering.

---

# Coming Next — SE320-L02: Caching — Trading Freshness for Speed

We've spent this session establishing how PostgreSQL can preserve correctness when many operations compete over shared state. Now imagine that we've succeeded.

Our reservation system no longer double-books rooms. Inventory updates are atomic.

Transactions are carefully designed. The database enforces important constraints.

Everything is correct. But there's a new problem.

The booking search API is becoming expensive.

Thousands of customers repeatedly request the same hotel descriptions, room types, availability summaries, and pricing information. The database performs many similar queries.

So we introduce Redis. Suddenly, response times fall dramatically.

The product feels faster. Database load decreases.

Everybody celebrates. Then something rather peculiar happens.

A room sells out. PostgreSQL correctly records that no inventory remains.

But Redis still contains the earlier availability information. The next customer sees the room as available.

Another customer sees it as sold out. Both responses come from functioning components.

And now the business must decide which data is authoritative, how stale information is tolerated, and what happens when caches disagree.

In SE320-L02, we'll explore **Redis, cache-aside, TTLs, invalidation, eviction, cache stampedes, and consistency boundaries**.

We'll discover why caching isn't merely a technique for making software faster. It's the deliberate introduction of additional copies of information that may disagree.

After today's investigation of database concurrency, that should sound just a little suspicious.

---


---

## End of CS330

**CS330 — Relational Databases and Transactions** is complete. See the recommended study order in `README.md` for natural next courses.

## Further Reading

Official PostgreSQL documentation:

- **Transaction Isolation:** https://www.postgresql.org/docs/current/transaction-iso.html
- **Explicit Locking:** https://www.postgresql.org/docs/current/explicit-locking.html
- **Data Consistency Checks:** https://www.postgresql.org/docs/current/applevel-consistency.html
- **Serialization Failure Handling:** https://www.postgresql.org/docs/current/mvcc-serialization-failure-handling.html
- **Concurrency Control:** https://www.postgresql.org/docs/current/mvcc.html
- **Constraints:** https://www.postgresql.org/docs/current/ddl-constraints.html

For an additional technical explanation of PostgreSQL's Serializable implementation:

- **PostgreSQL Wiki — Serializable Snapshot Isolation:** https://wiki.postgresql.org/wiki/SSI


---

