---
id: CS330-L03
course: CS330
title: "Transactions: When Correct Operations Produce Incorrect Results"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: [BACK301-S04]
prev: CS330-L02
next: null
---

# CS330 — Relational Databases and Transactions

## Lecture 03: Transactions — When Correct Operations Produce Incorrect Results

*Two customers. One remaining hotel room. Two database transactions. Every SQL statement succeeds. Both transactions commit. Yet the hotel has confirmed two reservations for one room. How can a database execute everything correctly and still allow an impossible business outcome?*

# Part I — Intuition

## The picture to carry in your head

It's Friday evening.

A hotel has exactly one Deluxe room remaining for Saturday night.

Alice opens the booking website from Berlin. At almost the same moment, Bob opens it from Stockholm.

Both select the same room category. Both click Book.

Our backend receives the requests and processes them independently.

Alice's request asks the database how many rooms remain.

The answer is one.

Bob's request asks the same question.

The answer is also one.

Alice creates a reservation.

Bob creates a reservation.

Both database transactions commit successfully.

The hotel now has two confirmed reservations for one remaining room.

What's disturbing is that the database hasn't necessarily done anything contrary to its rules.

Each transaction inserted a valid reservation record.

Each foreign key was valid.

Each date range was valid.

And each availability query returned a result that was true when observed.

The problem wasn't inside any single statement.

It was the relationship between the statements executed by two concurrent transactions.

**Two operations can be individually correct and jointly violate a business invariant.**

That is the problem transaction isolation exists to address.

## 1. A transaction isn't a magic pause button

When developers first learn transactions, they often imagine them as protective bubbles.

Begin a transaction.

Execute several statements.

Commit.

Everything inside the bubble is now safe.

But safe from what?

A transaction can ensure that its own database changes succeed or fail together.

That is atomicity.

It doesn't automatically mean other transactions were prevented from observing relevant data or making competing decisions.

The behavior depends on the database's isolation rules and the synchronization performed by the operations themselves.

In PostgreSQL, the default isolation level is Read Committed.

Under Read Committed, one transaction can read an availability count while another transaction is preparing to change the underlying state.

Both may make decisions based on observations that do not remain valid until their respective commits.

The mere presence of `BEGIN` and `COMMIT` doesn't solve that problem.

We must define which concurrent histories are acceptable.

## 2. Imagine several versions of reality

Suppose Alice reads a reservation whose status is pending.

Meanwhile, another transaction changes that status to confirmed and commits.

Should Alice continue seeing pending?

Or should she see confirmed the next time she reads?

Both behaviors can be useful in different circumstances.

PostgreSQL uses **Multi-Version Concurrency Control**, or MVCC, to support multiple versions of database rows and determine which versions are visible to different transactions.

It's like giving readers snapshots of a changing document.

One reader may continue seeing an earlier version while another sees a newer committed version.

This allows ordinary readers and writers to coexist efficiently.

But it also means that a transaction's view of the database may not represent the latest globally committed state.

The isolation level determines when that view is established and how it changes.

## 3. A stable snapshot can still produce an impossible result

You might propose fixing the booking problem by giving every transaction a stable view of the database.

If Alice sees one remaining room, she continues seeing that original state throughout her transaction.

Bob does the same.

That sounds predictable.

But predictability isn't necessarily correctness.

Alice and Bob can each hold an internally consistent snapshot that predates the other's reservation.

Each believes the room is available.

Each inserts a different reservation row.

Because they modify different rows, neither necessarily encounters a direct conflicting update.

Both can commit under PostgreSQL's Repeatable Read isolation, depending on the operation.

This is a form of **serialization anomaly**, closely related to write skew.

A stable snapshot guarantees consistency of what the transaction sees.

It doesn't guarantee that all concurrent transactions produce an outcome equivalent to some valid one-at-a-time execution.

That's the essential difference between Repeatable Read and Serializable.

## 4. Give the decision an authoritative moment

How can we prevent overselling?

One approach is to make the availability claim itself an indivisible database operation.

Imagine one row representing available Deluxe inventory for Saturday night.

It currently contains one remaining unit.

Alice attempts to decrement the count, but only if the count is still positive.

Bob attempts the same operation.

The database coordinates their conflicting updates to that row.

If Alice successfully changes the count from one to zero and commits, Bob's conditional update cannot also claim a room.

The condition is re-evaluated against the relevant current row under PostgreSQL Read Committed rules.

Bob updates zero rows.

He cannot honestly confirm a reservation.

We've created a common authoritative point where competing operations must coordinate.

Notice that we didn't need to lock the whole database or automatically choose the strongest isolation level.

We modeled the contested resource explicitly and used an operation appropriate to that model.

**The right concurrency mechanism depends on the shape of the invariant.**

## 5. The transaction ends at the database boundary

Now suppose Alice successfully claims the room.

Our backend calls a payment provider to charge her card.

Should we make that external call while keeping the PostgreSQL transaction open?

That creates a new problem.

The payment provider doesn't participate in the PostgreSQL transaction.

If the charge succeeds but the database transaction later rolls back, PostgreSQL cannot undo the card charge.

And if the provider takes eight seconds to respond, our transaction may retain locks and a database connection for eight seconds.

The database transaction is a boundary around database state.

It isn't an automatic transaction across every external service involved in the business workflow.

For payments, messaging, and other remote side effects, we need durable workflow state, idempotency, and recovery mechanisms.

We'll study those more deeply in distributed systems.

For now, distinguish the things PostgreSQL can atomically commit from the things it cannot control.

## 6. A retry must make a new decision

One more complication.

Under stronger isolation or competing locks, PostgreSQL may abort a transaction to preserve correctness.

The application receives an error.

What should it do?

Sometimes it should retry.

But it must retry the **complete decision**, using a fresh transaction and appropriate current data.

If Alice's first transaction failed, she cannot blindly reuse the assertion that one room remained available.

That fact may no longer be true.

A retry is not simply re-executing the final SQL statement.

It is giving the business operation another opportunity to make a valid decision.

And if the attempted operation includes an irreversible external charge, we must never blindly repeat that side effect.

## Three questions before the Deep Dive

1. Why can two transactions each use `BEGIN` and `COMMIT`, yet still oversell the final available room?
2. Why isn't a stable transaction snapshot the same as guaranteeing a valid serial execution?
3. Why is a conditional inventory decrement often a simpler solution than applying Serializable isolation to every booking operation?

Keep one mental picture: two customers competing for the same scarce resource. The database must establish a point at which one claim succeeds and the other cannot.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The booking that should have been impossible

Our booking platform has a table of reservations.

A hotel offers one remaining Deluxe room for November 14.

The backend checks how many confirmed reservations already exist for that room category and date.

If the count is below capacity, it inserts a reservation.

Each operation is wrapped in a transaction.

Alice begins first and counts the existing bookings.

The count is zero.

Bob begins before Alice commits and counts the same bookings.

His count is also zero.

Alice inserts one reservation.

Bob inserts another.

Because the two transactions insert different rows, there may be no direct row-update conflict.

Both commit.

The invariant—at most one confirmed booking for the remaining unit—has been violated.

We need to understand what a transaction actually guarantees, and which guarantee this workflow failed to obtain.

## 2. ACID is four different promises

The acronym ACID describes four important properties of database transactions.

But these properties protect different things.

### Atomicity

A transaction's database changes succeed or fail as one unit.

Suppose we decrement inventory and insert a reservation inside one transaction.

If the reservation insert fails and the transaction rolls back, the inventory decrement is rolled back too.

That's the guarantee we need to avoid permanently consuming inventory for a reservation that wasn't created.

Atomicity doesn't imply that the transaction's decision was sensible.

An atomic transaction can still record a booking that violates a business rule the database never enforced.

### Consistency

A transaction moves the database between states satisfying the applicable integrity rules.

But the database cannot preserve a rule it doesn't know about.

If the schema permits unlimited reservation inserts and no transactional mechanism enforces capacity, PostgreSQL has no basis for rejecting our second booking merely because the hotel actually has one room left.

Database consistency is not the same as complete business correctness.

The relevant invariants must be expressed through constraints, transactional logic, and the application's design.

### Isolation

Isolation determines how concurrent transactions may observe and affect one another.

Different isolation levels permit or prevent different anomalies.

At weaker levels, transactions may observe changes at different times or make competing decisions based on incomplete views of the concurrent workload.

At Serializable isolation, successfully committed transactions must have effects consistent with some serial ordering.

This is the part of ACID most relevant to our double-booking incident.

### Durability

Once a transaction commits, its effects are intended to survive failures according to the database's durability guarantees and configuration.

But durability doesn't mean the client necessarily knows whether a commit succeeded.

Imagine PostgreSQL commits a booking and the network connection breaks before the client receives the confirmation.

The application may not know whether the transaction committed.

That uncertainty matters for retries.

It is possible for the database to be correct while the caller lacks knowledge of the outcome.

These four promises are valuable, but they are not interchangeable.

**Atomicity protects a transaction's database changes. Isolation governs their interaction with concurrent transactions. Neither automatically makes an entire multi-service business process atomic.**

## 3. MVCC: why readers and writers can coexist

PostgreSQL uses Multi-Version Concurrency Control.

Rather than simply overwriting every row in place and forcing all readers to wait, PostgreSQL maintains row versions and visibility information.

Suppose a reservation initially has status pending.

Transaction A begins reading.

Transaction B changes the status to confirmed and commits.

Depending on A's isolation level and snapshot, A may continue seeing the earlier version while a newer transaction sees confirmed.

Each reads a version appropriate to its visibility rules.

This is why ordinary PostgreSQL reads generally don't block ordinary writes, and ordinary writes generally don't block ordinary reads.

That is a major concurrency advantage.

### Visibility depends on snapshots

A snapshot determines which row versions are visible to a statement or transaction.

It considers the relevant transaction state and visibility rules.

The reader does not simply see "whatever is physically latest in memory."

This allows a query to observe a consistent database state while other transactions continue committing changes.

But the exact duration of that view depends on isolation.

### MVCC has a physical cost

Old row versions cannot always be discarded immediately.

A long-running transaction may still need to see them.

PostgreSQL uses vacuuming and related mechanisms to make obsolete row-version storage reusable and maintain visibility information.

Long-running transactions can delay cleanup and contribute to table bloat.

So leaving a transaction open for fifteen minutes isn't merely an application-level inconvenience.

It can affect storage maintenance and resource usage.

The principle is straightforward:

**Isolation is implemented by real machinery, with real operational costs.**

## 4. Read Committed: the world may change between statements

PostgreSQL's default isolation level is Read Committed.

For an ordinary `SELECT`, the statement sees data committed before that statement begins, together with the transaction's own relevant changes.

The next statement can obtain a newer snapshot.

Consider an account balance.

Transaction A begins and reads a balance of one hundred.

Transaction B updates the balance to one hundred fifty and commits.

Transaction A reads the balance again.

Under Read Committed, it can now see one hundred fifty.

The same transaction observed two different committed values in two statements.

That's a **non-repeatable read**.

Nothing is malfunctioning.

Read Committed allows this behavior.

### Dirty reads are different

A dirty read means observing changes another transaction hasn't committed.

PostgreSQL does not allow dirty reads, even if you request the SQL-standard Read Uncommitted isolation level.

In PostgreSQL, Read Uncommitted behaves like Read Committed.

This is a PostgreSQL-specific detail worth remembering.

### Phantoms: rows can appear between queries

Now suppose Transaction A counts all confirmed bookings for one hotel and date.

It finds one hundred.

Transaction B inserts another matching reservation and commits.

Transaction A repeats the count.

Under Read Committed, it may now find one hundred and one.

The result set has changed because another qualifying row appeared.

That's a **phantom read**.

It is closely related to our booking problem.

The first count was correct when observed.

It was not a promise that the count would remain unchanged until A committed.

### Read Committed isn't automatically unsafe

Many applications work perfectly well under Read Committed.

The key is to use operations that coordinate correctly for the invariant involved.

For example, two transactions updating the same inventory row can be coordinated safely using an appropriate conditional update.

We should not confuse a relatively weak default isolation level with a database that cannot enforce correctness.

Correctness depends on the combination of isolation, operations, constraints, and shared state.

## 5. The lost update: two writers reuse one old value

Let's examine a simpler anomaly.

An inventory row says five rooms remain.

Alice reads five into application memory.

Bob also reads five.

Both calculate the new value as four.

Alice executes an update setting the count to four.

Bob executes an update setting the count to four.

Under Read Committed, both updates can complete, coordinating through the row's write lock as necessary.

But the second update still assigns the stale absolute value four.

Two reservations were made.

Only one unit was deducted.

That's a lost update.

### Database-side arithmetic changes the situation

Now compare a different operation.

Instead of calculating four in application memory, both transactions ask PostgreSQL to decrement the current stored value by one.

The expression uses the row's current value in the database.

Under Read Committed, when a concurrent updater has committed a change to the row, the waiting updater can proceed against the updated row version.

Starting at five, two successful decrements yield three.

That is fundamentally different from two stale absolute assignments.

### But what happens at zero?

If the count is zero, an unconditional decrement would produce a negative value.

So we need one more part of the operation.

Decrement only when the current count is positive.

Then inspect whether an update actually occurred.

This is an atomic conditional update.

It turns the inventory claim into an operation the database can coordinate directly.

We'll build the complete pattern shortly.

## 6. Repeatable Read: a stable view isn't enough

Suppose we increase the isolation level to Repeatable Read.

In PostgreSQL, a transaction uses a stable snapshot beginning with its first relevant statement.

Its later ordinary reads continue seeing the corresponding committed state, together with its own changes.

Non-repeatable reads disappear.

PostgreSQL's Repeatable Read also prevents phantom reads, exceeding the SQL standard's minimum requirement for that isolation level.

That sounds powerful.

But it can still permit serialization anomalies.

### The two doctors

Consider a hospital that must always have at least one doctor on duty.

Alice and Bob are both currently on duty.

Alice wants to go home.

Her transaction checks whether another doctor remains on duty.

Bob is available.

So Alice updates her own row to off duty.

At the same time, Bob wants to go home.

His transaction checks whether another doctor remains on duty.

Alice appears available in Bob's snapshot.

So Bob updates his own row to off duty.

The two transactions update different rows.

Neither necessarily encounters a conflicting write to the same row.

Both can commit under PostgreSQL Repeatable Read.

The final state has zero doctors on duty.

Every transaction worked from a stable snapshot.

The combined outcome violates the invariant.

This is **write skew**.

### Why this isn't a normal lost update

In a lost update, two operations compete to modify the same logical state and one overwrites or fails to incorporate another's change.

In the doctors example, Alice updates Alice's row and Bob updates Bob's row.

The dangerous relationship is between what each transaction read and what the other transaction wrote.

Alice's decision depended on Bob remaining on duty.

Bob's decision depended on Alice remaining on duty.

Their writes changed the truth of each other's earlier assumptions.

Neither transaction tried to update the same row.

That is why row-update conflict detection alone doesn't solve the problem.

### The booking equivalent

Our original booking example has the same shape.

Alice counts the reservations.

Bob counts the reservations.

Each inserts a different new reservation.

The inserted rows don't directly conflict.

But each insertion invalidates the other transaction's earlier capacity assessment.

A stable snapshot does not make those two transactions equivalent to a valid one-at-a-time execution.

**Repeatable Read preserves the transaction's view. Serializable protects the validity of the committed concurrent history.**

## 7. Serializable: when the database must reject a history

Now imagine executing the doctors' transactions one at a time.

Alice checks that Bob is still on duty and leaves.

Bob then checks the remaining doctors.

He discovers that Alice has left.

Bob cannot also leave without violating the rule.

Alternatively, Bob could leave first, forcing Alice to remain.

Either serial order preserves at least one doctor.

But the concurrent Repeatable Read execution allowed both to leave.

The outcome wasn't equivalent to either valid serial order.

Serializable isolation prevents such a committed history.

### PostgreSQL's Serializable Snapshot Isolation

PostgreSQL implements Serializable using **Serializable Snapshot Isolation**, commonly abbreviated SSI.

It doesn't simply force every transaction to execute one after another.

Instead, it allows substantial concurrency while tracking dependencies that can reveal dangerous interactions among reads and writes.

When an execution would create an unsafe serialization outcome, PostgreSQL can abort a transaction.

The application may receive SQLSTATE `40001`, meaning `serialization_failure`.

One transaction succeeds.

Another may need to retry from the beginning.

On retry, the operation observes a new transaction state and reevaluates its business condition.

### Serializable isn't one enormous lock

PostgreSQL uses predicate-locking information and conflict tracking to detect relevant serialization hazards.

These are not merely ordinary blocking row locks applied to the entire database.

SSI is designed to preserve serializable behavior without serializing every operation through one giant mutex.

But it still introduces costs.

Tracking dependencies consumes resources.

Conflicting transactions can be aborted.

Retries consume additional work.

Under heavy contention, throughput and latency may be affected.

Serializable is powerful, but not free.

### A qualification that matters

Serializable guarantees apply to the participating database transactions and their applicable correctness contract.

They don't automatically make external HTTP calls or payment-provider actions part of PostgreSQL's transaction.

Nor can a correctness strategy ignore independent write paths that bypass the rules on which the invariant depends.

If some code inserts confirmed reservations without participating in the required inventory or consistency protocol, the broader application may remain incorrect.

The mechanism must cover every operation capable of violating the invariant.

## 8. The isolation levels, without memorizing a useless chart

We can now summarize the practical differences.

**Read Uncommitted:** In PostgreSQL, this behaves like Read Committed. Dirty reads are not permitted.

**Read Committed:** The default. Ordinary statements receive current committed snapshots. Non-repeatable reads, phantoms, and serialization anomalies are possible.

**Repeatable Read:** A stable transaction snapshot. PostgreSQL prevents non-repeatable reads and phantoms, but write skew and other serialization anomalies remain possible.

**Serializable:** Successful committed transactions have effects consistent with a serial execution, subject to the database's documented guarantees. Applications must handle serialization failures.

The purpose of knowing these levels is not to select the strongest one automatically.

It's to recognize what your operation requires.

Are you modifying one known row?

Are you comparing a version before saving an edit?

Are you checking a condition across several records?

Can another transaction insert a row that invalidates your earlier count?

Different shapes of invariants require different coordination strategies.

## 9. Pessimistic locking: coordinate on an existing resource

Let's return to our hotel.

Instead of counting existing reservations, suppose we store an inventory row for each room type and date.

The row for Deluxe rooms on November 14 has one remaining unit.

A transaction can lock that row using `SELECT ... FOR UPDATE`.

The lock prevents another conflicting transaction from modifying or acquiring an incompatible lock on the row until the first transaction ends.

Alice locks the inventory row.

Bob tries to lock it and waits.

Alice checks availability, decrements the count, inserts the reservation, and commits.

Bob can then proceed.

Under Read Committed, the locking read can return the updated row version after waiting.

Bob sees that no rooms remain.

He cannot complete the booking.

This is **pessimistic concurrency control**.

We coordinate competing operations before allowing them to proceed through their critical state transition.

### The important limitation: absent rows

Suppose instead of locking an inventory row, Alice runs a query selecting all existing reservations for a particular room and date with `FOR UPDATE`.

What if no reservation rows exist yet?

There may be no rows to lock.

Bob can perform the same query and also find nothing.

Both can then attempt to insert a reservation.

PostgreSQL does not turn every row-locking predicate into a general blocking lock on all rows that might match in the future.

A row lock protects an existing row.

It doesn't automatically protect the absence of matching rows.

That's why a dedicated inventory row can be a useful coordination point.

Everyone competing for the same room type and night attempts to update or lock the same authoritative record.

But that works only if all relevant booking paths obey the protocol.

## 10. Atomic conditional updates: often the simplest correct solution

Now let's improve our inventory model.

Instead of selecting the row, calculating a new count, and updating it separately, issue one conditional update.

The statement means:

"Subtract one from remaining capacity, but only if the current row still has positive remaining capacity."

PostgreSQL can enforce this operation under Read Committed.

If Alice updates the row first, Bob may wait for the conflicting update.

After Alice commits, PostgreSQL rechecks Bob's update condition against the updated row.

If the remaining count is zero, the predicate is false.

Bob updates zero rows.

The application must interpret that as unavailable inventory.

### Connect the claim to the reservation

Now suppose Alice successfully decrements inventory.

What if inserting her reservation fails?

We must not permanently lose one room of availability.

Therefore, the inventory decrement and reservation creation belong in the same database transaction.

If the insert fails, the transaction rolls back both changes.

If the conditional update returns zero rows, no reservation should be created.

This produces a straightforward correctness contract.

Inventory is claimed only by a successful conditional update.

The reservation is committed atomically with that claim.

### What about multi-night stays?

A guest books three nights.

The transaction must claim capacity for every required night.

Suppose the first two nightly claims succeed but the third fails.

The transaction must roll back the earlier claims.

Otherwise, the customer receives no booking while two nights remain artificially unavailable.

This is precisely why transaction atomicity matters.

For multi-row allocation, we should also use a consistent ordering when acquiring or updating inventory rows.

That helps reduce deadlock risk.

The essential lesson is:

**A simple atomic conditional update can protect a counter-shaped invariant more directly than a separate availability query plus a sophisticated isolation setting.**

It isn't universally applicable.

If capacity is computed dynamically from many different records, or several operations can affect inventory through independent paths, stronger coordination may still be required.

The mechanism follows the data model.

## 11. Optimistic concurrency: detect stale decisions

Not every operation should lock its data while a user thinks about an edit.

Imagine two hotel employees editing the same reservation.

Alice opens reservation 10842.

Bob opens the same reservation.

Both see version seven.

Alice changes the check-in time and saves.

Bob changes the guest count and saves a minute later.

Without coordination, Bob's stale representation might overwrite Alice's changes.

A common solution is **optimistic concurrency control**.

Store a version number with the reservation.

When updating, require the version to equal the one originally read.

Increment it during the update.

Alice's version-seven update succeeds and advances the version to eight.

Bob's version-seven update matches no row.

The application detects that the reservation changed since Bob loaded it.

Bob can refresh, reconsider, and apply an appropriate merged update.

### When optimistic control is attractive

This approach works well when conflicting edits are relatively rare.

It avoids holding a transaction and lock open while a user spends minutes on an editing form.

The database performs the authoritative version check at write time.

### What it doesn't protect

A version on one reservation doesn't automatically protect a capacity rule involving several different reservations.

Alice inserting reservation A and Bob inserting reservation B don't necessarily conflict on one shared versioned row.

If the invariant spans many records, the optimistic-control scheme must coordinate through suitable shared state or another mechanism.

Once again, choose the scope of protection to match the scope of the business rule.

## 12. Deadlocks: when two valid locking decisions form a cycle

Locks solve one problem and introduce another.

Suppose Alice books Friday and Saturday.

Bob also books Friday and Saturday.

Alice's transaction locks Friday first.

Bob's transaction locks Saturday first.

Alice now tries to lock Saturday.

She waits for Bob.

Bob tries to lock Friday.

He waits for Alice.

Neither can continue while holding the lock the other needs.

That's a deadlock.

PostgreSQL can detect the cycle and abort one of the transactions.

The application may receive SQLSTATE `40P01`, meaning `deadlock_detected`.

The other transaction can proceed.

### Preventing common deadlocks

A practical technique is to acquire shared resources in a consistent order.

For nightly inventory, always process dates from earliest to latest.

Now Alice and Bob both attempt to lock Friday before Saturday.

One waits for the first lock while the other proceeds.

The particular reversed-order cycle is prevented.

Short transactions, deliberate lock acquisition, and minimizing unnecessary locked work also help.

But deadlocks can still occur in complex systems.

Applications need appropriate error handling.

### Waiting isn't automatically deadlock

A transaction waiting behind another row lock may simply be experiencing ordinary contention.

Eventually the first transaction commits or rolls back, and the waiter proceeds.

Deadlock requires a dependency cycle that prevents progress.

Both situations can increase latency, but the diagnosis differs.

PostgreSQL exposes tools such as `pg_stat_activity` and `pg_locks` to investigate blocking and lock ownership.

## 13. The dangerous transaction around a payment

We can now design the boundary of a booking transaction.

The core database operation may involve:

Claim inventory.

Insert the reservation.

Record the new booking state.

Perhaps insert an outbox event for later delivery.

Those changes need a coherent atomic database boundary.

But a payment-provider call is different.

Suppose we charge the customer's card while holding the inventory transaction open.

The provider takes eight seconds.

During those eight seconds, our database transaction may retain a connection and row locks.

Other booking attempts wait unnecessarily.

Worse, the payment can succeed while the database transaction later aborts.

PostgreSQL cannot roll back an external card charge.

### A safer conceptual architecture

The service commits coherent local database state.

It records the need for external work durably.

A separate workflow performs the payment or other remote action under an appropriate idempotency contract.

The workflow records the outcome and reconciles ambiguous failures.

One implementation technique is a transactional outbox: write business state and an outgoing event record in the same database transaction, then publish the event separately with reliable retry and deduplication behavior.

An outbox doesn't make delivery exactly once, and it doesn't automatically solve the payment workflow.

But it addresses one important problem: avoiding a gap where business state commits but the intention to notify another system is lost.

Distributed systems require additional coordination beyond one database transaction.

We'll study that architecture later.

For now, retain this boundary:

**Keep the database transaction around the database state that must change atomically. Don't stretch it across slow, unreliable external calls merely because they belong to the same user request.**

## 14. Retrying a transaction means retrying its reasoning

Suppose PostgreSQL aborts a Serializable transaction with `40001`.

Or detects a deadlock and aborts a transaction with `40P01`.

A retry may be appropriate.

But what exactly should be retried?

Imagine the failed transaction originally did the following:

It read inventory.

It selected a room.

It calculated a price.

It inserted a reservation.

If the concurrent world changed, simply repeating the insert is not enough.

The selected room may no longer be available.

The price may depend on current inventory or other business rules.

The transaction must begin again and reevaluate the relevant decisions.

PostgreSQL's guidance is to retry the **complete transaction**, including the logic determining the values and statements used.

### Bound the retries

A production retry policy should limit attempts.

It should respect the overall request deadline.

It may use backoff and jitter to avoid synchronized retry storms.

It must classify errors.

A serialization failure often suggests a fresh attempt.

A unique-key violation might represent a genuine duplicate booking request, not a transient scheduling conflict.

Blindly retrying every database error can make the situation worse.

### Don't replay irreversible side effects

Suppose the transaction callback charges a credit card before committing.

The database aborts.

An automatic retry reruns the callback.

The customer may be charged twice.

This is a serious failure of transaction-boundary design.

Retried database work must not blindly repeat external effects without an appropriate idempotency and workflow strategy.

### What if the client loses the commit response?

Another subtle case arises when PostgreSQL commits successfully but the network connection fails before the application receives confirmation.

The client cannot automatically assume the transaction rolled back.

Retrying as an entirely new booking may create a duplicate.

A durable request or business-operation identifier can help the application recognize that the logical booking may already have been completed.

This is one reason idempotency matters even when the database itself is fully transactional.

## 15. Choosing the right mechanism for the invariant

We now have several tools.

How should we choose?

### Unique constraints

Use them when the rule is that a value or key combination must not be duplicated.

For example, one booking operation may have a unique external idempotency key.

### Exclusion constraints

Use them for suitable overlap restrictions, such as preventing two confirmed stays from occupying the same physical room during intersecting date ranges.

### Atomic conditional updates

Use them when the scarce resource can be represented as a shared row with a condition checked and modified in one database statement.

This is often excellent for explicit inventory counters.

### Explicit row locking

Use it when competing operations must coordinate through existing rows before performing a multi-step state transition.

Be mindful that locking existing rows doesn't automatically protect the absence of rows.

### Optimistic versions

Use them to detect conflicting updates to an existing entity when contention is usually low.

They're particularly useful for human-driven edits.

### Serializable transactions

Use them when correctness depends on complex relationships across reads and writes that would be difficult to protect reliably through simpler shared-row or constraint mechanisms.

Plan for serialization failures and retries.

### What about Redis locks?

You might propose a distributed Redis lock around every booking.

That adds another system with lease expiry, ownership rules, network failures, and recovery behavior.

A process may pause long enough for its lease to expire, while remaining capable of writing when it resumes.

Without appropriate fencing or authoritative database enforcement, the lock may not provide the expected guarantee.

For invariants whose authoritative state lives in PostgreSQL, begin by asking whether PostgreSQL can enforce them directly.

External distributed locks can be useful in some architectures.

But they shouldn't be introduced merely because the application runs across several replicas.

The correct question is always:

**What exact state must competing operations coordinate through, and which mechanism makes violating the invariant impossible or detectable?**

## 16. The senior interview answer

Imagine an interviewer asks:

"We have two customers booking the last room concurrently. Both requests run inside database transactions. How would you prevent overselling?"

A weak answer is:

"Use transactions."

A slightly better but incomplete answer is:

"Use Serializable."

A stronger answer starts by clarifying the inventory model.

Are we assigning one identified physical room?

Or selling pooled category capacity across several nights?

If it's a physical room, an exclusion constraint may be appropriate.

If it's a category with explicit nightly inventory rows, an atomic conditional update or explicit locking protocol can coordinate competing claims.

The reservation insert and inventory allocation must be part of one atomic transaction.

For multiple nights, the entire allocation must succeed or roll back.

If the invariant depends on complex predicates across several tables, Serializable may be appropriate, with correct retry handling.

And if payment occurs through an external provider, it must be coordinated separately with durable state and idempotency rather than assuming PostgreSQL can roll it back.

That is a much stronger answer.

Not because it mentions more technologies.

Because it identifies the invariant and chooses the mechanism that actually protects it.

---

# The Oral Examination

Answer each question aloud before reading the solution.

**Question 1 — The misleading transaction**

Two requests each count existing reservations, observe one room available, insert separate reservation rows, and commit. Both operations use `BEGIN` and `COMMIT`. Why can the database allow overselling under Read Committed?

**Question 2 — Lost update versus safe decrement**

Two applications read `remaining = 5`, calculate four, and both execute an absolute assignment. Compare this with two transactions executing `remaining = remaining - 1` in PostgreSQL.

**Question 3 — The stable snapshot**

Why can PostgreSQL Repeatable Read prevent non-repeatable reads and phantoms while still allowing the two-doctors write-skew anomaly?

**Question 4 — Serializable and retries**

How does PostgreSQL Serializable prevent an impossible committed history? What must the application do if it receives SQLSTATE `40001`?

**Question 5 — The empty-row trap**

Why doesn't `SELECT ... FOR UPDATE` on currently matching reservation rows automatically prevent another transaction from inserting a new matching reservation?

**Question 6 — The conditional inventory claim**

Two transactions attempt to decrement the same remaining-inventory row from one to zero under Read Committed, using `WHERE remaining > 0`. What happens to the losing claim, and why?

**Question 7 — The outside payment**

A payment provider successfully charges the customer, but the local database transaction rolls back. Why doesn't transaction atomicity repair the situation?

**Question 8 — The stale editing form**

Two hotel employees edit the same reservation after both loading version seven. How can optimistic concurrency prevent one employee's save from silently overwriting the other's changes?

**Question 9 — The production strategy**

You need to reserve a category of interchangeable rooms across five nights. What must the transaction protect, and what additional design choices reduce deadlock and retry risks?

---

# Solutions and Discussion

## Solution 1 — Atomicity isn't sufficient isolation

Each transaction inserts a valid row based on a count observed earlier.

The inserts affect different rows, and no enforced invariant prevents the combined capacity excess.

Read Committed doesn't guarantee a serial execution of the count-and-insert workflow.

The business rule needs an appropriate constraint, shared resource, locking protocol, or stronger isolation strategy.

## Solution 2 — Stale assignment versus current-row arithmetic

Both absolute assignments can write four, losing one decrement.

Database-side arithmetic uses the relevant current row value under PostgreSQL's update and locking rules.

The second successful decrement can apply after the first, producing three.

For scarce capacity, add a positive-remaining predicate and verify whether the update returned a row.

## Solution 3 — Snapshot isolation isn't serializability

Each doctor reads a stable snapshot showing the other on duty.

Each updates a different row.

The transactions can both commit without a direct same-row write conflict, even though their combined effect violates the cross-row invariant.

Stable snapshots don't guarantee equivalence to a valid serial order.

## Solution 4 — Detect unsafe dependencies and retry

PostgreSQL Serializable uses SSI to detect dangerous concurrent read/write dependencies and can abort a transaction rather than allow a nonserializable committed result.

The application should start a fresh transaction and retry the complete decision, not merely repeat the last SQL statement.

Retries must be bounded and must not blindly replay external side effects.

## Solution 5 — A row lock doesn't lock nonexistent rows

`FOR UPDATE` locks rows that exist and are selected under its semantics.

It doesn't automatically create a blocking lock over every possible future row satisfying the predicate.

Another transaction may still insert a new qualifying row.

A dedicated inventory row, suitable constraint, or Serializable strategy may be needed.

## Solution 6 — One claim succeeds

The first transaction updates the row to zero.

The second waits for the conflicting update to finish.

After the first commits, PostgreSQL rechecks the condition against the updated row under Read Committed.

Since remaining capacity is zero, the second update affects no rows.

No reservation should be created for that unsuccessful claim.

## Solution 7 — Different transaction boundaries

PostgreSQL can roll back its own uncommitted database changes.

It cannot reverse an external payment-provider action that already succeeded.

The application needs durable workflow state, idempotency, and reconciliation for the external side effect.

Holding the database transaction open during the provider call doesn't make that remote operation atomic.

## Solution 8 — Version-conditional update

Each employee saves with a condition requiring version seven.

The first successful update increments the version to eight.

The second update matches no row and reports a conflict.

The application can refresh and decide how to reapply the intended change rather than silently overwriting another edit.

## Solution 9 — Claim all nights atomically

The booking must claim capacity for all five nights and insert the reservation within one coherent transaction.

If any night cannot be allocated, the transaction should roll back all claims.

Use a consistent row acquisition order, such as ascending date, to reduce deadlock risk.

Handle serialization or deadlock errors through bounded complete-transaction retries, and keep external payment actions outside the retried database transaction.

---

# The Mental Model Worth Keeping

A database transaction is not a magic bubble around business logic.

Its guarantees are specific.

**Atomicity:** Do the database changes succeed or fail together?

**Visibility:** Which committed state does each operation see?

**Coordination:** What prevents concurrent operations from violating the invariant?

**Scope:** Does the transaction cover all relevant database changes without incorrectly including external side effects?

**Recovery:** What happens if the database aborts, or the client cannot determine whether the commit succeeded?

The durable principle is:

**Correct transaction design begins with the business invariant and the set of operations that can violate it—not with an isolation-level setting.**

# Next Course — Data Systems Beyond Relational Databases

We've now explored relational modeling, query performance, and transactional correctness.

But modern systems rarely store all information in one relational database.

A search engine organizes information for relevance and full-text discovery.

A document database groups data into document-oriented aggregates.

A key-value system favors direct access through keys.

A queue stores work waiting to be processed.

Analytical databases optimize large-scale aggregation rather than ordinary transactional updates.

In CS340, we'll explore why these systems make different trade-offs, how their storage and consistency models work, and how to choose the right data system without turning an application into an unnecessary collection of databases.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Lab — Make PostgreSQL Double-Book a Room

**Environment:** PostgreSQL, a disposable database, and two independent SQL sessions. Open two `psql` terminals connected to the same database. We'll call them Terminal A and Terminal B.

The goal is to observe transaction anomalies rather than merely read about them.

## Experiment A — A business invariant that the database doesn't know

Create a simple booking table. We deliberately do not encode the one-room capacity invariant.

```sql
DROP TABLE IF EXISTS demo_bookings;

CREATE TABLE demo_bookings (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  hotel_id INTEGER NOT NULL,
  night DATE NOT NULL,
  customer TEXT NOT NULL
);
```

Assume Hotel 1 has capacity for exactly one booking on November 14.

In Terminal A:

```sql
BEGIN ISOLATION LEVEL READ COMMITTED;

SELECT COUNT(*)
FROM demo_bookings
WHERE hotel_id = 1
  AND night = DATE '2026-11-14';
```

The result should be zero.

Keep the transaction open.

In Terminal B, execute the same `BEGIN` and `SELECT`.

The result is also zero.

Now insert Alice in Terminal A:

```sql
INSERT INTO demo_bookings (hotel_id, night, customer)
VALUES (1, DATE '2026-11-14', 'Alice');
```

Insert Bob in Terminal B:

```sql
INSERT INTO demo_bookings (hotel_id, night, customer)
VALUES (1, DATE '2026-11-14', 'Bob');
```

Commit both transactions.

Now query the table.

Both bookings can exist.

The database didn't violate a declared constraint. The application failed to enforce the actual capacity rule.

**Question:** Which business invariant was missing from the transactional design?

## Experiment B — Repeatable Read doesn't automatically fix it

Reset the table after finishing all prior transactions:

```sql
TRUNCATE demo_bookings RESTART IDENTITY;
```

Repeat Experiment A, except both transactions begin with:

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ;
```

Make sure both sessions execute their count queries before either inserts or commits.

Each transaction observes zero existing reservations in its stable snapshot.

Because they insert different rows and do not necessarily have conflicting writes, both transactions can commit.

This demonstrates why stable snapshots don't imply Serializable behavior.

**Question:** Which information did each transaction read that the other transaction's write later made invalid?

## Experiment C — Serializable prevents the impossible history

Reset the table again:

```sql
TRUNCATE demo_bookings RESTART IDENTITY;
```

Now both sessions begin with:

```sql
BEGIN ISOLATION LEVEL SERIALIZABLE;
```

Have both sessions perform the count query before either inserts.

Then insert Alice and Bob in their respective sessions.

Commit one transaction, then the other.

PostgreSQL should prevent both transactions from committing this nonserializable history. One may fail with SQLSTATE `40001`.

The exact point of failure can vary.

The important property is that the database refuses the invalid combined committed outcome.

After the failure, retry the aborted booking in a new transaction.

It can now observe that capacity has been consumed.

**Question:** Why must the second attempt repeat the availability decision rather than merely repeat the insertion?

## Experiment D — A simpler model: explicit nightly inventory

Create an inventory table:

```sql
CREATE TABLE demo_inventory (
  hotel_id INTEGER NOT NULL,
  night DATE NOT NULL,
  remaining INTEGER NOT NULL CHECK (remaining >= 0),

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

The update should return a row with remaining equal to zero.

Do not commit yet.

In Terminal B, begin a transaction and execute the same update.

Terminal B should wait for the conflicting update to complete.

Commit Terminal A.

Terminal B can then proceed under Read Committed.

Its condition no longer matches, so the update returns no rows.

Rollback or finish Terminal B without creating a reservation.

**Question:** What shared row forces these two competing claims to coordinate?

## Experiment E — Complete the atomic booking

Extend the conditional inventory claim so that a successful claim and the corresponding reservation insert occur within the same transaction.

Use a returned-row check to ensure that an unsuccessful claim cannot produce a confirmed reservation.

Then deliberately introduce an error after the successful inventory decrement but before the reservation insert commits.

Rollback the transaction.

Verify that the inventory count returns to its earlier value.

**Question:** Which ACID property makes the rollback behavior possible, and which concurrency property prevents two successful claims of the last unit?

## Experiment F — Optimistic version checking

Create a simple versioned reservation:

```sql
CREATE TABLE demo_reservations (
  id BIGINT PRIMARY KEY,
  status TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1
);

INSERT INTO demo_reservations (id, status, version)
VALUES (10842, 'pending', 7);
```

Suppose two editors both load version seven.

The first attempts:

```sql
UPDATE demo_reservations
SET status = 'confirmed',
    version = version + 1
WHERE id = 10842
  AND version = 7
RETURNING id, status, version;
```

It succeeds and advances the version to eight.

The second attempts another update requiring version seven.

It matches zero rows.

The application should report a conflict instead of silently overwriting current state.

**Question:** Why doesn't this technique automatically prevent two independent new reservations from consuming the same remaining room?

## Experiment G — Inspect lock contention

In a test environment, start one transaction that locks an inventory row:

```sql
BEGIN;

SELECT *
FROM demo_inventory
WHERE hotel_id = 1
  AND night = DATE '2026-11-14'
FOR UPDATE;
```

Leave the transaction open.

In another session, try locking the same row.

Observe the waiting behavior.

From a third session, inspect relevant activity:

```sql
SELECT
  pid,
  state,
  wait_event_type,
  wait_event,
  pg_blocking_pids(pid) AS blocking_pids
FROM pg_stat_activity
WHERE datname = current_database();
```

Then commit the first transaction and watch the second continue.

**Question:** Why is ordinary lock waiting not automatically a deadlock?

## Experiment H — The transaction-design interview

A hotel has ten interchangeable Deluxe rooms for each night.

Reservations can span multiple nights.

Payments are handled by an external provider.

Your task is to propose a booking workflow that prevents overselling while tolerating retries, timeouts, and process crashes.

Your answer should address the following:

- How authoritative nightly capacity is represented.
- How all nights are claimed atomically.
- What happens if the final night has no capacity.
- How conflicting transactions are coordinated.
- How the system handles database deadlocks or serialization failures.
- Why the external payment isn't placed inside a long-running database transaction.
- How a retry avoids accidentally creating a second booking or charge.

The objective is a correct and recoverable design, not merely an impressive list of database features.

---

# Further Reading

Official PostgreSQL documentation:

- **Transaction Isolation:** https://www.postgresql.org/docs/current/transaction-iso.html
- **Explicit Locking:** https://www.postgresql.org/docs/current/explicit-locking.html
- **Data Consistency Checks:** https://www.postgresql.org/docs/current/applevel-consistency.html
- **Serialization Failure Handling:** https://www.postgresql.org/docs/current/mvcc-serialization-failure-handling.html
- **Concurrency Control:** https://www.postgresql.org/docs/current/mvcc.html
- **Constraints:** https://www.postgresql.org/docs/current/ddl-constraints.html

Additional technical reading:

- **PostgreSQL Wiki — Serializable Snapshot Isolation:** https://wiki.postgresql.org/wiki/SSI

Related programme chapters:

- CS330-L01 — Relational Database Design
- CS330-L02 — SQL and Query Performance
- CS340-L05 — Replication, Consistency, and Sharding in Practice
- CS430-L02 — Consistency, Replication, and Availability
- CS430-L05 — Designing Reliable Business Workflows

---

## Dense Cheatsheet — Interview Glance Card

```text
CS330-L03 — TRANSACTIONS AND ISOLATION

CENTRAL PROBLEM
  Two transactions read "one room left"
  Both insert separate reservations and commit
  Individual statements valid; combined outcome invalid
  BEGIN/COMMIT != automatic business-level serializability

ACID
  Atomicity   DB changes commit or roll back together
  Consistency DB preserves defined integrity constraints
  Isolation   controls concurrent visibility/anomalies
  Durability  committed state survives per DB guarantees
  Atomicity != Serializable
  Database consistency != all business invariants magically known
  Client losing commit response != proof of rollback

MVCC
  PostgreSQL retains row versions
  Snapshot determines visible versions
  Ordinary readers/writers generally don't block each other
  Long transactions can hinder vacuum and create bloat

ISOLATION LEVELS — POSTGRESQL
  Read Uncommitted = behaves as Read Committed
  Read Committed = default, new snapshot per ordinary statement
  Repeatable Read = stable snapshot, also prevents phantoms in PG
  Serializable = committed history equivalent to serial execution

ANOMALIES
  Dirty read = observing uncommitted changes; PG prevents
  Non-repeatable read = row changes between statements; RC permits
  Phantom = new matching row appears between queries; RC permits
  Lost update = stale absolute value overwrites newer state
  Write skew = two transactions update different rows based on
               mutually invalidated snapshot assumptions

CRITICAL DISTINCTION
  Stable snapshot != Serializable execution
  PostgreSQL Repeatable Read can allow write skew
  Serializable uses SSI to detect dangerous dependencies
  Serialization failure SQLSTATE = 40001

READ COMMITTED UPDATE
  Concurrent updates coordinate on affected row
  Waiting update can re-evaluate WHERE against updated version
  Bad:  SET remaining = 4   (stale value from app)
  Good: SET remaining = remaining - 1
  Best for claim: decrement WHERE remaining > 0 RETURNING row
  Zero rows returned = claim failed

ATOMIC BOOKING
  Begin transaction
  Claim required nightly inventory conditionally
  Verify all required claims succeeded
  Insert reservation
  Commit together
  Any failed claim/insert -> rollback entire allocation
  Lock inventory dates consistently to reduce deadlocks

LOCKS
  SELECT FOR UPDATE protects selected existing rows
  Does NOT automatically lock nonexistent/future matching rows
  Ordinary lock wait != deadlock
  Deadlock = circular wait
  PostgreSQL deadlock error SQLSTATE 40P01
  Consistent lock ordering reduces common cycles

OPTIMISTIC CONCURRENCY
  UPDATE ... WHERE id = ? AND version = ?
  SET version = version + 1
  Zero rows = stale edit/conflict
  Good for low-contention entity edits
  Local version != protection of arbitrary cross-row invariant

SERIALIZABLE
  Prevents nonserializable committed histories
  Not one giant blocking database lock
  SSI tracks read/write dependencies
  Aborted transaction needs complete-decision retry
  Can add contention/retry overhead
  All relevant invariant-changing paths need coherent enforcement

RETRY RULES
  40001 -> usually retry entire transaction
  40P01 -> appropriate deadlock retry
  Bound attempts and total deadline
  Use backoff/jitter where appropriate
  Reevaluate business decisions with fresh data
  Unique violation may mean real duplicate, not transient retry
  Never blindly replay irreversible external side effects

TRANSACTION BOUNDARIES
  Include coherent DB changes that must commit together
  Avoid slow external calls while holding DB locks
  PostgreSQL cannot roll back payment-provider charges
  Outbox can durably record intention to publish
  Distributed workflow needs idempotency and reconciliation
  Commit succeeded but ACK lost -> remote outcome ambiguous

MATCH THE TOOL TO THE INVARIANT
  Unique key/identity           UNIQUE constraint
  Physical-room overlap         Exclusion constraint
  Explicit inventory counter    Conditional atomic UPDATE
  Existing contested rows       SELECT FOR UPDATE
  Rare conflicting entity edits Optimistic version
  Complex predicate invariant   Serializable + retry
  Cross-service operation       Durable workflow/idempotency

SENIOR INTERVIEW ANSWER
  "I'd first define the inventory invariant and authoritative
   state. For explicit nightly capacity, I'd use conditional
   updates in one transaction with the reservation insert.
   For more complex cross-row predicates I'd consider
   Serializable and full-transaction retries. External payments
   need separate durable coordination and idempotency."

MENTAL MODEL
  What invariant?
  Which transactions can violate it?
  Which shared state forces coordination?
  What happens when a transaction fails?
  Which side effects lie outside the database?
```
