---
id: CS350-L03
course: CS350
title: "PostgreSQL Under Production Pressure"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS350-L02
next: CS350-L04
---

# CS350 — Advanced PostgreSQL Engineering
## Lecture 03: PostgreSQL Under Production Pressure

*The team deletes three million records. The database gets no smaller. Queries become slower, disk usage keeps rising, and somewhere an application connection has been sitting inside a transaction for six hours.*

---

# Part I — Intuition

## 1. The Database That Refused to Lose Weight

Imagine you're working on a booking platform that has operated for several years.

The reservations database contains millions of completed bookings, historical availability records, temporary quotations, and background processing events.

One particular table has grown to 80 gigabytes.

Most of its oldest records are no longer needed in the primary operational database. The company has already retained the necessary business history elsewhere, so an approved retention job deletes several million obsolete rows.

The job completes successfully.

PostgreSQL reports that millions of rows were deleted.

The developers check the table's logical row count. It has fallen dramatically.

Then they inspect the database's disk usage.

The table still occupies almost the same space.

A few hours later, the disk is even fuller.

Someone suggests running `VACUUM`.

Someone else proposes `VACUUM FULL`.

A third engineer suggests increasing the database's disk allocation and forgetting about the whole thing.

All three ideas might be relevant in different circumstances.

But none is a diagnosis.

To understand what happened, we need to look beneath SQL's logical model and examine how PostgreSQL physically maintains data.

## 2. Deleting a Row Is Not Erasing It Immediately

In an ordinary programming language, deleting an object might suggest that its memory can eventually be reclaimed.

In PostgreSQL, removing a row is more complicated.

The database must support concurrent transactions.

Imagine two customers using the booking application.

Transaction A begins reading a set of reservation records.

Transaction B deletes some of those records.

Should Transaction A suddenly lose access to information that was visible in its established snapshot?

Under PostgreSQL's multiversion concurrency control, or MVCC, different transactions can observe different versions of the database.

The physical row version that Transaction B deleted may still be needed by Transaction A.

PostgreSQL therefore cannot always remove that version immediately.

A delete marks the row as deleted through transaction metadata. The physical space remains until PostgreSQL can determine that the old version is no longer required.

Updates follow a related principle.

Rather than simply overwriting a row in place, PostgreSQL ordinarily creates a new row version and makes the old version obsolete according to transaction visibility rules.

The result is a database containing current data alongside historical physical row versions that eventually become unnecessary.

### Visual anchor 1 — One logical row, multiple physical versions

```text
Logical booking 482
        |
        v
Version 1: pending
        |
        | UPDATE
        v
Version 2: confirmed
        |
        | UPDATE
        v
Version 3: cancelled

Different transactions may temporarily
need different versions.

Obsolete versions can be reclaimed
only when no relevant snapshot needs them.
```

The diagram is conceptual. PostgreSQL stores additional transaction metadata and manages visibility through its internal tuple representation.

The essential idea is that **logical deletion and physical space reclamation are different operations**.

## 3. Vacuum Is the Database's Garbage Collector

PostgreSQL needs a process that identifies obsolete row versions and makes their storage available for reuse.

That process is called vacuuming.

Ordinary `VACUUM` reclaims dead tuples and maintains related storage structures.

PostgreSQL also has an autovacuum system that performs maintenance automatically under suitable conditions.

Think of a warehouse with shelves.

A clerk marks some boxes as obsolete. But the boxes cannot be removed while another department still needs to inspect them.

Later, the cleanup crew confirms which boxes nobody needs and makes their shelf positions available for new boxes.

The warehouse can now receive new inventory without necessarily expanding.

But the building itself hasn't become smaller.

That distinction explains our first mystery.

Ordinary vacuuming generally makes space reusable inside the existing relation files.

It does not normally return that space to the operating system.

There are exceptions, such as truncating suitable empty pages at the end of a table, but routine vacuuming primarily supports reuse.

### Visual anchor 2 — Reuse versus shrinking

```text
BEFORE DELETE
[Live][Live][Live][Live][Live]

AFTER DELETE
[Live][Dead][Dead][Live][Dead]

AFTER VACUUM
[Live][Free][Free][Live][Free]

The file may remain the same size.
New rows can reuse free space.
```

If the business expects the database file to physically shrink, that is a different objective.

PostgreSQL can rewrite a table into a more compact form through operations such as `VACUUM FULL`.

But rewriting an actively used table has significant operational consequences.

## 4. Why an Old Transaction Can Stop Cleanup

Return to our booking platform.

At 09:00, a reporting service opens a transaction and reads historical reservations.

For some reason, its connection remains open.

At 10:00, the retention job deletes old reservations.

At 11:00, vacuum runs.

But the old reporting transaction still holds a snapshot that may need to see the deleted row versions.

PostgreSQL cannot reclaim those versions as though nobody needed them.

The retention job was correct.

The delete committed.

Vacuum ran.

And the storage cannot yet be fully reclaimed.

This is why an apparently harmless idle connection can cause serious database problems.

The connection might consume little CPU.

It may not be executing a query at all.

Yet an open transaction with an old snapshot can hold back cleanup.

The important resource is not just CPU time or memory.

It is the database's ability to advance the boundary beyond which old row versions are no longer needed.

### Visual anchor 3 — An old snapshot holds back cleanup

```text
09:00  Transaction A establishes snapshot
          |
10:00     |    Transaction B deletes rows
          |
11:00     |    VACUUM tries cleanup
          |          |
          |          v
          |    Some versions still needed
          |
13:00  Transaction A ends
          |
          v
      Cleanup can advance
```

This is a simplified illustration of transaction horizons. The real oldest-visible boundary can also be affected by other sessions, replication slots, and replication-related behavior.

## 5. Database Disk Usage Is Several Different Things

Suppose the PostgreSQL data directory grows by twenty gigabytes.

That does not necessarily mean the live tables grew by twenty gigabytes.

Disk space may be consumed by several categories.

Heap files store table data.

Indexes maintain searchable structures.

TOAST storage holds certain large values outside the main row representation.

Temporary files may appear during large sorts or hashes.

Write-ahead log files record changes needed for recovery and replication.

Different symptoms require different investigations.

If a table is bloated with reusable dead space, the issue involves table storage and vacuuming.

If the `pg_wal` directory is growing because a replication consumer is lagging, rewriting the table may do absolutely nothing useful.

If temporary files are consuming disk during a massive sort, the solution is not to vacuum the table.

**Disk usage is a symptom. The first task is identifying which physical category is consuming the space.**

## 6. WAL: Every Change Has Another Cost

PostgreSQL uses write-ahead logging, usually abbreviated WAL.

Before modified database pages need to be persisted, PostgreSQL records sufficient information in the write-ahead log to support crash recovery.

This allows the database to recover changes after a crash without requiring every modified table page to be flushed at each transaction commit.

It also supports replication and backup recovery mechanisms.

But WAL means that modifying data creates additional write activity.

A large delete does not merely change logical row counts.

It modifies database structures and generates WAL records.

A massive update can generate substantial WAL, touch many heap pages, and cause index maintenance.

If a replication consumer falls behind, the primary may need to retain WAL that the consumer still requires.

Thus a cleanup operation intended to free storage can temporarily increase storage pressure.

This is not contradictory.

Deleting rows and reclaiming physical storage are different processes, each with its own costs.

## 7. Locks and Connections Create Invisible Queues

Suppose a booking update normally takes five milliseconds.

Today it takes eight seconds.

The query plan has not changed.

The table isn't unusually large.

The CPU is mostly idle.

What happened?

Perhaps the query is waiting for another transaction.

Transaction A updates a booking but does not commit.

Transaction B tries to update the same booking.

Transaction B must wait for the conflicting operation to finish.

The eight-second request may involve almost no actual query execution during those eight seconds.

It is waiting for permission to proceed.

Now imagine hundreds of application requests waiting for database connections, while those connections are themselves waiting for locks.

The application appears slow.

The database may report low CPU usage.

The real problem is resource coordination.

We need to distinguish execution time, lock wait time, and connection-pool wait time.

## 8. The Main Operational Principle

An individual query is only one part of a database system.

PostgreSQL is constantly maintaining row versions, indexes, transaction visibility, logs, locks, and connections.

A query that performs well in isolation can behave poorly when these surrounding mechanisms are under pressure.

The correct investigation begins by identifying the resource or dependency that limits progress.

### A tiny comprehension check

A retention job deletes five million rows.

The table's logical row count decreases.

Ordinary vacuum runs successfully.

The table file remains almost the same size.

Is that necessarily a failure?

No.

The reclaimed space may now be available for future reuse without reducing the physical file.

Now suppose a separate report shows that WAL files are growing rapidly.

Would running `VACUUM FULL` necessarily solve that?

No.

WAL retention and table bloat are different mechanisms.

This distinction is the foundation of operational PostgreSQL engineering.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 9. MVCC Is a Concurrency Mechanism with Physical Consequences

We previously explored transaction isolation and MVCC in CS330-L03.

Here we're interested in their physical costs.

PostgreSQL stores tuples containing transaction visibility information.

A newly inserted tuple is associated with the transaction that created it.

When a row is deleted or superseded by an update, PostgreSQL records the relevant transaction information rather than immediately removing every trace of the previous version.

A reader's visibility rules determine which row versions it can observe.

This allows ordinary readers and writers to proceed concurrently under many circumstances without requiring readers to block every update.

But the physical versions occupy storage.

That storage has to be maintained.

### 9.1 Updates create new versions

Consider a booking row containing its status, guest count, and total price.

The application changes its status from pending to confirmed.

PostgreSQL ordinarily creates a replacement tuple version.

The previous version may remain physically present until it is safe to reclaim.

Now imagine an operational table where the same rows are updated repeatedly.

A worker changes a task from pending to running, then to retrying, then running again, then completed.

Those updates can create substantial tuple churn.

A table with one million logical tasks may have generated many millions of physical row versions over its lifetime.

Vacuum and other page-cleanup mechanisms must manage that churn.

### 9.2 Dead is relative to transaction visibility

A row version is not safely removable merely because the latest application view no longer considers it current.

PostgreSQL must establish that no transaction snapshot or other relevant retention horizon still needs it.

A long-running transaction can therefore delay cleanup of versions that were deleted after its snapshot was established.

Not every idle transaction necessarily holds an old data snapshot for its entire duration.

The actual impact depends on its isolation level, snapshot lifetime, transaction state, and other database mechanisms.

In operational investigations, inspect the relevant transaction and snapshot information rather than assuming every idle connection blocks vacuum equally.

## 10. Ordinary Vacuum: Reclamation, Visibility, and Maintenance

Vacuum has several responsibilities.

The most obvious is making obsolete tuple space available for reuse.

But vacuum also performs index-related cleanup, maintains visibility information, and participates in protecting the database against transaction ID wraparound.

These responsibilities explain why vacuum is essential even when disk space appears healthy.

### 10.1 Reclaiming dead tuples

When PostgreSQL determines that a tuple version is no longer required, ordinary vacuum can reclaim its space.

That space can then support later inserts or updates.

But it often remains inside the table's allocated storage.

The operating system may continue reporting a large file.

That is expected.

### 10.2 Index cleanup

Updates and deletes can also leave obsolete index references.

Vacuum may need to clean those entries.

The amount of index maintenance depends on the workload, index types, and PostgreSQL's cleanup decisions.

A heavily updated table with many indexes can require substantial maintenance work.

### 10.3 The visibility map

PostgreSQL maintains information about heap pages whose tuples are visible to all transactions.

This is important for index-only scans.

An index-only scan can avoid visiting some heap pages when the visibility map establishes that the relevant pages are all-visible.

Otherwise, PostgreSQL may still need heap access to verify visibility.

Vacuum helps maintain that information.

Thus vacuuming can affect query performance even when it doesn't shrink the database.

### 10.4 Why vacuum can compete with application traffic

Vacuum consumes I/O and CPU resources.

On a busy database, aggressive maintenance can interfere with other work.

PostgreSQL provides cost-based vacuum throttling and operational controls to balance maintenance with application load.

The solution is not to disable maintenance indefinitely.

It is to maintain a sustainable balance between row-version creation and cleanup.

## 11. Autovacuum: The Cleanup System Must Keep Up with the Workload

PostgreSQL normally uses an autovacuum launcher and workers to perform routine maintenance.

Autovacuum decides when tables need attention according to statistics, thresholds, and configuration.

The system considers activity such as updates, deletes, inserts, and transaction-age maintenance requirements.

A common simplified threshold for update/delete-driven vacuuming combines a fixed threshold with a fraction of the estimated table size.

The actual rules include additional settings, and newer PostgreSQL versions expose further controls.

The important principle is that **maintenance must be proportional to how quickly obsolete data is created**.

### 11.1 A hot table can overwhelm default maintenance

Imagine a table with fifty million rows.

Only a small subset is frequently updated, but those rows change thousands of times per minute.

The table can accumulate substantial dead tuple churn before a default proportional threshold triggers vacuum.

The background worker may also be constrained by available workers, throttling, I/O, or competing tables.

A large table's default settings are not necessarily appropriate for every update pattern.

PostgreSQL allows table-specific autovacuum settings.

But tuning should follow evidence.

### 11.2 Disabling autovacuum is usually a bad shortcut

An engineer sees autovacuum consuming resources and disables it to make production faster.

The immediate workload may improve.

Then dead versions accumulate, indexes become less efficient, and transaction-age maintenance becomes urgent.

The underlying problem has been deferred rather than solved.

PostgreSQL can still perform certain emergency anti-wraparound maintenance even when normal autovacuum is disabled.

But relying on emergency behavior is not an operating strategy.

### 11.3 When manual vacuum is appropriate

Manual vacuum may be useful after a known large delete or when diagnosing specific maintenance behavior.

It can supplement autovacuum.

But it doesn't automatically remove tuples that are still protected by an old snapshot.

And it doesn't turn a fundamentally unsustainable write workload into a sustainable one without understanding the source of churn.

## 12. HOT Updates: Why Some Updates Are Cheaper

PostgreSQL provides an optimization called Heap-Only Tuple updates, usually abbreviated HOT.

An ordinary update can require changes to both heap storage and indexes.

HOT can reduce index-maintenance work when suitable conditions are met.

The important conditions include:

- The update does not change columns referenced by ordinary indexes, subject to special treatment for summarizing indexes such as BRIN.
- The heap page containing the old tuple has enough free space for the new version.

When HOT applies, PostgreSQL can represent the new row version without creating new entries in ordinary indexes.

That can reduce index churn.

### 12.1 An innocent index can increase update costs

Imagine a worker table with a status column updated frequently.

The team adds an index on status to accelerate dashboard filtering.

Now status updates change an indexed column.

Those updates may no longer qualify for HOT.

The index can improve reads while increasing write and maintenance costs.

This is not an argument against indexing status.

It is an argument for evaluating indexes against the complete workload.

### 12.2 Fillfactor and available page space

PostgreSQL's `fillfactor` setting influences how densely heap pages are initially filled.

Leaving additional free space can increase the opportunity for HOT updates.

But lower fillfactor also means the same logical dataset may initially occupy more pages.

There is a trade-off between storage density and update efficiency.

HOT is not guaranteed merely because an update leaves indexed columns unchanged.

Sufficient space must also be available on the relevant page.

### 12.3 Measuring HOT behavior

PostgreSQL exposes table statistics including `n_tup_upd` and `n_tup_hot_upd`.

These counters help determine how many updates used the HOT optimization.

They are cumulative statistics, not perfectly instantaneous measurements.

Interpret them over an observation interval and understand when the counters were last reset.

## 13. Why Deleting Millions of Rows Doesn't Shrink the Table

Now we can explain the original incident precisely.

The retention job commits a large delete.

The affected tuples become obsolete to newer transactions.

When cleanup is safe, ordinary vacuum reclaims space for reuse.

But the physical heap file often retains its allocated pages.

PostgreSQL can reuse empty space inside those pages for future data.

This is desirable for tables that continue receiving inserts and updates.

Repeatedly shrinking and expanding the file would introduce additional work.

### 13.1 Table size versus live data

A table may contain relatively little live data while occupying a large file.

That doesn't automatically mean the database is wasting all that space permanently.

Some space may be immediately reusable.

Other space may still contain dead tuples awaiting cleanup.

Some may belong to indexes or TOAST storage.

A complete investigation distinguishes these categories.

### 13.2 When ordinary vacuum can shrink a file

Ordinary vacuum may truncate empty pages at the end of a relation under suitable conditions.

That can return some space to the operating system.

But it does not generally compact live rows from arbitrary pages into a smaller file.

Therefore, one shouldn't promise a particular reduction in file size after ordinary vacuum.

### 13.3 `VACUUM FULL`

`VACUUM FULL` rewrites the table into a compact representation.

It can return unused storage to the operating system.

But it requires an `ACCESS EXCLUSIVE` lock on the affected table.

That conflicts with ordinary reads and writes.

It also requires additional disk space while the replacement relation is constructed.

For a large production table, the operation may be long and disruptive.

**Running `VACUUM FULL` as an emergency response to low disk space can make the incident worse if insufficient temporary space remains or the lock blocks important traffic.**

It is a deliberate maintenance operation, not a routine garbage-collection button.

## 14. Table Bloat and Index Bloat Are Related but Different

Table bloat refers broadly to physical table storage exceeding what is needed for the live data and appropriate free-space headroom.

Index bloat concerns unused or inefficient space within index structures.

These can grow for different reasons.

A large delete may leave reusable space in the heap.

Frequent updates may generate obsolete index entries.

A workload may leave an index with poorly utilized pages.

A table can therefore have reasonable heap storage while one of its indexes is disproportionately large.

### 14.1 Why indexes need their own investigation

Suppose the table's heap occupies 15 GB but indexes occupy another 40 GB.

Running a table-focused investigation without examining index sizes misses much of the storage problem.

The database may have several large composite indexes serving overlapping workloads.

Some may be valuable.

Others may be redundant or rarely used.

But dropping an index requires understanding all queries and constraints that depend on it.

An index used by a critical query once a day may appear unimportant in a short statistics window.

A production decision must account for workload history, not just a snapshot of counter values.

### 14.2 Bloat estimates are not exact truth

System views such as `pg_stat_user_tables` expose useful estimates of live and dead tuples.

They are not exact physical inventories.

Some measurements are updated asynchronously.

For more detailed investigations, extensions such as `pgstattuple` can provide additional information when available and permitted.

But installing diagnostic extensions or scanning huge tables can itself have operational costs.

Use the least intrusive evidence necessary.

## 15. Long-Running Transactions: The Invisible Retention Boundary

Let's reconstruct a particularly dangerous incident.

A reporting service opens a transaction using Repeatable Read.

It executes a query, establishing a snapshot.

The service then waits for an external operation while keeping the transaction open.

Meanwhile, a retention job deletes millions of rows.

Those deleted row versions may still be visible to the old reporting snapshot.

Vacuum cannot reclaim them as though no active snapshot needed them.

The database continues accumulating obsolete versions.

### 15.1 `idle in transaction`

PostgreSQL's activity statistics distinguish sessions that are active, idle, and idle in transaction, among other states.

An `idle in transaction` session has an open transaction but is not currently executing a query.

That can be dangerous.

It may hold locks and other resources.

If it retains a sufficiently old snapshot or transaction horizon, it can delay cleanup.

A session can be operationally harmful while consuming almost no CPU.

### 15.2 The transaction horizon

PostgreSQL must establish which transaction IDs or snapshots may still need old row versions.

The oldest relevant visibility horizon restricts which versions can be safely removed.

A long-running transaction is one possible contributor.

Replication mechanisms can also retain relevant horizons.

Therefore, a vacuum problem may persist even when no ordinary application transaction appears unusually old.

### 15.3 Why killing sessions blindly is dangerous

If an old session is holding important locks or a snapshot, terminating it may release the blocking condition.

But it may also abort legitimate work.

Before terminating anything, identify the connection owner, transaction age, current state, and business consequences.

A production incident response should establish whether the session is abandoned, whether its work can be retried safely, and whether application-level cleanup is required.

The durable fix is often correcting transaction lifetime in application code.

For example, don't hold a database transaction open while waiting for a remote API or user interaction unless the design specifically requires it and its consequences are understood.

## 16. Locks: Waiting Is Not Executing

An application request can appear slow because its SQL statement is waiting on a lock.

Consider two transactions updating the same booking.

Transaction A updates the booking but does not commit.

Transaction B attempts to update that same row.

Transaction B waits.

Its SQL execution plan might be excellent.

Its actual database work might be tiny.

Yet the request latency is large.

### 16.1 Row-level and table-level locks

PostgreSQL has multiple lock modes.

Ordinary updates acquire relevant table-level and row-level locking behavior.

An update to one row does not generally block unrelated ordinary reads across the entire table.

But conflicting updates to the same row must coordinate.

Certain schema changes require stronger table-level locks.

An operation requesting `ACCESS EXCLUSIVE` can block normal table access while the lock is held.

### 16.2 Lock queues

Imagine Transaction A holds a lock needed by Transaction B.

Transaction B waits.

Now another operation requires a lock that conflicts with an already waiting lock request.

Lock queues can produce wider disruption than the original transaction's direct conflict might suggest.

This is why a migration can create an incident even before it acquires the strong lock it wants.

The pending lock request may affect the progress of later operations.

### 16.3 Diagnosing blockers

PostgreSQL exposes `pg_stat_activity`, `pg_locks`, and the `pg_blocking_pids()` function.

The latter identifies backend process IDs blocking a particular backend.

A useful investigation asks:

Which session is waiting?

What is it waiting for?

Which session blocks it?

How long has the blocking transaction been open?

What operation is the blocker performing, or has it become idle in transaction?

This is far more useful than merely observing that one SQL query has taken ten seconds.

## 17. Deadlocks Versus Ordinary Waiting

Waiting for a lock is not automatically a deadlock.

Suppose Transaction A holds a lock and Transaction B waits.

If A eventually commits, B can continue.

A deadlock occurs when transactions form a circular dependency.

For example:

Transaction A locks booking 101 and then waits for booking 102.

Transaction B locks booking 102 and then waits for booking 101.

Neither can progress without the other releasing a lock.

PostgreSQL detects deadlocks and aborts one participating transaction.

### 17.1 Why retries matter

A deadlock error is not necessarily evidence that the database is broken.

It can arise from legitimate concurrent operations acquiring locks in conflicting orders.

Applications may need to retry the entire failed transaction under appropriate conditions.

But retrying blindly without understanding the underlying contention can amplify load.

A good prevention strategy is often to acquire resources in a consistent order.

### 17.2 Lock timeouts versus statement timeouts

PostgreSQL supports a `lock_timeout` for limiting how long a statement waits to acquire a lock.

It also supports `statement_timeout` for limiting statement duration more generally.

These are different controls.

A statement can be slow because it is executing expensive work rather than waiting for a lock.

A lock timeout doesn't solve that.

Conversely, increasing a statement timeout may simply allow a blocked request to wait longer.

Timeouts are safety mechanisms, not substitutes for root-cause analysis.

## 18. Connections: The Database Has a Finite Number of Seats

PostgreSQL handles client connections using server-side processes and associated resources.

Connections consume memory and operational capacity.

A large number of application replicas can therefore create substantial database connection pressure.

Imagine a service deployed with twelve pods.

Each pod has a connection pool configured for twenty connections.

The theoretical aggregate is 240 connections.

Now add background workers, administrative tools, other services, and monitoring connections.

The database may not be configured to support that total.

### 18.1 More application replicas can worsen database pressure

A team sees slow API responses and doubles the number of service replicas.

Each replica starts its own database connection pool.

The total potential number of connections increases.

If the database was already the bottleneck, the scaling action may make the problem worse.

This resembles what happens when adding RabbitMQ workers to a system whose database pool is already saturated.

More concurrency does not necessarily create more throughput.

Sometimes it creates longer queues and greater contention.

### 18.2 Pool exhaustion versus database exhaustion

A request might wait inside the application's connection pool because all pool connections are busy.

In that case, PostgreSQL may never see the waiting request.

Alternatively, the application may have available pool slots but PostgreSQL may reject additional connections because server limits have been reached.

These symptoms require different evidence.

Application pool metrics help identify pool acquisition waits.

PostgreSQL activity views help identify server-side connection use.

Both are necessary for a complete diagnosis.

### 18.3 Idle does not mean harmless, but not all idle sessions are equivalent

An ordinary idle connection may be waiting for the next query.

It consumes some resources but doesn't necessarily hold an open transaction.

An `idle in transaction` connection is different.

It has an unfinished transaction and may retain locks or a visibility horizon.

Treating all idle connections as identical obscures important operational behavior.

### 18.4 Connection pooling strategies

Application-level pools reuse connections.

External poolers such as PgBouncer can reduce the number of PostgreSQL backend connections needed for large client populations.

But different pooling modes have different semantics.

Transaction pooling, for example, does not preserve a dedicated server connection across an entire client session.

Applications relying on session-specific state or connection-local behavior must account for this.

Pooling is not simply a setting that can be enabled without checking application assumptions.

## 19. WAL: Durability, Replication, and Storage Pressure

Write-ahead logging is fundamental to PostgreSQL's crash recovery.

When a transaction changes data, PostgreSQL generates WAL records describing changes needed for recovery.

The system can then replay these records after a crash to restore consistency.

WAL is also central to physical replication and recovery workflows.

### 19.1 A large delete generates WAL

A delete modifies database state.

It therefore produces WAL.

A large update can create new tuples, modify indexes, and generate substantial WAL activity.

A maintenance operation that rewrites a relation can also create substantial write traffic.

This explains why a large cleanup can temporarily increase total I/O and storage usage.

The heap may eventually become more reusable while WAL activity rises during the operation.

### 19.2 WAL generation versus WAL retention

These are separate concepts.

**WAL generation** is how much logging the workload produces.

**WAL retention** is how much WAL PostgreSQL must keep available.

A busy write workload can generate WAL quickly.

But WAL may also accumulate because a replication or archiving consumer cannot advance.

For example, a replication slot may require retaining WAL from an older log sequence number.

If the consuming replica or logical decoding process remains behind, old WAL segments may be retained.

### 19.3 Replication slots

PostgreSQL exposes replication-slot information through `pg_replication_slots`.

Relevant fields include whether the slot is active and its `restart_lsn`.

The restart LSN indicates the oldest WAL location still potentially needed by the consumer.

Some slots also retain transaction visibility horizons through `xmin` or `catalog_xmin`, affecting vacuum cleanup.

This means a neglected replication slot can create more than one operational problem.

It may contribute to WAL retention, and certain slot types or configurations may also hold back tuple cleanup.

### 19.4 Never manually delete WAL files as a cleanup shortcut

A dangerously tempting response to a full `pg_wal` directory is to remove files manually.

Do not do that.

PostgreSQL manages WAL according to its recovery and replication requirements.

Deleting required WAL segments can damage recovery capability or disrupt replication.

Investigate the underlying retention reason, the replication configuration, and the safety of any proposed intervention.

A limit such as `max_slot_wal_keep_size` can restrict slot-related WAL retention under its documented semantics, but exceeding the limit may leave a consumer unable to continue without recovery or resynchronization.

That is an operational trade-off, not free space recovery without consequences.

## 20. Measuring Storage Correctly

Let's return to our 80 GB table.

Before discussing remediation, establish where the space is allocated.

PostgreSQL provides functions such as:

`pg_relation_size()` for a relation's main fork by default.

`pg_table_size()` for table storage including associated auxiliary storage, but excluding indexes.

`pg_indexes_size()` for the table's indexes.

`pg_total_relation_size()` for the combined relation storage.

These help distinguish heap and auxiliary table storage from index storage.

### 20.1 A database can grow outside the target table

Suppose the target table's total size is stable.

Meanwhile, the PostgreSQL data directory grows rapidly.

You should investigate other databases, other relations, temporary files, WAL retention, and auxiliary storage.

Do not conclude that the target table is responsible merely because it was recently modified.

Correlation is not proof of causation.

### 20.2 Logical row count versus physical allocation

`COUNT(*)` describes logical rows visible to the querying transaction.

It does not describe how many obsolete row versions occupy physical storage.

It also does not report index size or WAL retention.

A database can therefore report fewer visible rows while consuming the same or more physical space.

That is precisely the behavior MVCC makes possible.

## 21. Reading PostgreSQL's Operational Views

PostgreSQL provides several important system views.

Each answers a different question.

### 21.1 `pg_stat_user_tables`

This view exposes table activity statistics.

Useful fields include estimated live and dead tuples, insert/update/delete counters, HOT update counts, vacuum history, and autovacuum history.

These statistics help identify high-churn tables.

But they are estimates and cumulative counters.

A low `n_dead_tup` value does not prove that a table is physically compact.

A high count should prompt further investigation, not an immediate destructive operation.

### 21.2 `pg_stat_activity`

This view helps investigate current sessions.

Useful fields include process ID, state, transaction start time, wait-event type, wait event, and current or recent query information.

It is particularly valuable for identifying long transactions and waiting sessions.

Query visibility depends on privileges.

An administrator may see details that an ordinary application role cannot.

### 21.3 `pg_locks` and `pg_blocking_pids`

These help explain lock contention.

The practical question is not merely how many locks exist.

PostgreSQL uses locks constantly.

The important question is whether a session is waiting for a conflicting lock and which backend is responsible.

### 21.4 `pg_stat_progress_vacuum`

When a normal vacuum operation is running, PostgreSQL can expose its progress.

This helps distinguish a vacuum that is actively processing a large table from one that is not currently running.

Progress views are snapshots of active operations.

A fast vacuum may finish before you inspect it.

### 21.5 `pg_stat_wal`

This view exposes cumulative WAL activity statistics, including WAL bytes generated.

It can help estimate the rate of WAL generation over time.

But WAL generation counters do not tell you the current physical size of the `pg_wal` directory.

Retention and generation must be investigated separately.

### 21.6 `pg_stat_io`

This view provides I/O statistics broken down by backend type, object, and I/O context.

It can help investigate broad storage activity.

Its interpretation requires care because the counters describe particular database I/O operations, not necessarily every physical disk operation in the operating system.

## 22. Production Incident: The Connection Pool That Amplified a Lock

Imagine an API endpoint updating booking status.

Normally, each request takes 20 milliseconds.

One transaction becomes stuck while holding a row lock.

Subsequent requests attempt to update the same booking or related records.

Several database connections begin waiting.

The application connection pool fills.

New HTTP requests wait to acquire database connections.

The API's latency increases dramatically.

The team adds more application replicas.

Now more pools compete for the same database.

The underlying lock remains.

This is an example of a local database contention problem becoming a service-wide capacity problem.

### 22.1 The misleading metrics

CPU utilization may remain modest.

The average query execution plan may be efficient.

The database may have no unusual sequential scans.

Yet application response latency is terrible.

The missing evidence is wait time.

### 22.2 The correct diagnostic sequence

First establish whether requests wait inside the application pool or inside PostgreSQL.

Then identify active database sessions and wait events.

For lock waits, use blocking-process information.

Find the oldest relevant transaction and determine what it owns.

Only after understanding the blocker should you decide whether to wait, cancel a query, terminate a session, or change application behavior.

### 22.3 The durable fix

If the root cause is a transaction left open across a remote API call, shorten the transaction boundary.

If the application retries aggressively against the same lock, introduce bounded retry behavior.

If many workers contend on the same record, reconsider the concurrency model.

If pools are oversized relative to database capacity, adjust aggregate connection budgets.

The correct fix may involve application design rather than PostgreSQL configuration.

## 23. Production Incident: The WAL Directory That Kept Growing

A second incident begins with a different symptom.

The database reports healthy table sizes.

But the PostgreSQL data directory keeps growing.

Investigation shows that the `pg_wal` directory is unusually large.

A logical replication consumer has stopped progressing.

Its replication slot retains an old restart LSN.

The database continues generating WAL as application traffic proceeds.

PostgreSQL must retain segments still required by the slot, subject to configured limits.

### 23.1 The wrong response

Running `VACUUM FULL` on large tables is unrelated to the immediate WAL-retention cause.

It may even generate substantial additional WAL and I/O.

Deleting WAL files manually is unsafe.

### 23.2 The correct response

Confirm the WAL-retention source.

Inspect replication slots, archive status, replication lag, and relevant configuration.

Determine whether the consumer can resume safely.

If a slot is permanently obsolete, removing it may be appropriate, but that can sacrifice the consumer's ability to continue from its previous position.

Such changes require explicit operational ownership.

### 23.3 Prevent recurrence

Monitor WAL generation and retained WAL size separately.

Track replication lag and inactive slots.

Establish an operational process for abandoned replication consumers.

And ensure that cleanup procedures account for recovery and replication requirements.

## 24. Production Incident: The Delete That Didn't Free Disk

We can now reconstruct the original incident with a complete diagnostic model.

The retention job deletes millions of rows.

The delete commits.

Logical row counts fall.

Disk usage remains high.

The engineer investigates table and index sizes.

The engineer checks whether vacuum has run and whether dead row estimates remain high.

They inspect long-running transactions and replication-related retention horizons.

They determine whether the space is now reusable inside the table or still blocked from cleanup.

They also examine WAL and temporary storage to explain overall disk growth.

Only then do they evaluate whether physical compaction is necessary.

### 24.1 Three very different outcomes

**Outcome A — Space is reusable.**

Vacuum reclaimed dead versions, and the table can reuse the existing allocation.

The file didn't shrink, but ongoing growth may stabilize.

No immediate rewrite is necessary.

**Outcome B — Cleanup is blocked.**

An old transaction or another retention horizon prevents removal of obsolete versions.

The blocking condition must be resolved before vacuum can reclaim the space.

Repeated vacuuming alone may not help.

**Outcome C — Physical shrinkage is required.**

The organization needs to return substantial allocated storage to the operating system.

A planned rewrite or other appropriate maintenance strategy may be justified.

That decision must account for locks, disk headroom, replicas, WAL, and business availability.

These outcomes require different actions.

The initial symptom—high disk usage—is not enough to distinguish them.

## 25. The Operational Investigation Framework

When PostgreSQL behaves poorly under load, follow a disciplined process.

**First: Define the symptom precisely.**

Is the problem latency, throughput, connection errors, disk usage, replication lag, or blocked maintenance?

**Second: Identify the constrained resource.**

Look for CPU, I/O, memory, locks, connections, WAL retention, or transaction horizons.

**Third: Separate cause from consequence.**

A large connection count may be the result of slow lock waits rather than the original cause.

Growing table files may be a consequence of vacuum being held back.

**Fourth: Inspect the relevant evidence.**

Use query plans for execution costs, activity views for sessions and waits, table statistics for churn, size functions for allocation, and replication views for WAL retention.

**Fifth: Form a causal hypothesis.**

Explain why the mechanism would produce the observed symptom.

**Sixth: Test the smallest safe correction.**

Prefer targeted changes over broad configuration switches.

**Seventh: Verify both immediate recovery and long-term behavior.**

A temporary drop in disk usage is not a durable fix if the same churn will recreate the problem tomorrow.

The goal is sustainable operation, not merely passing an incident's first health check.

---

# The Oral Examination

Answer aloud before reading the solutions.

### Question 1 — The Delete

A table contains ten million rows.

A retention job deletes eight million.

After ordinary vacuum, the table file remains almost the same size.

Is vacuum broken? Explain.

### Question 2 — The Old Snapshot

A Repeatable Read transaction establishes a snapshot and remains open.

Another transaction deletes rows and commits.

Why might vacuum be unable to reclaim those row versions?

### Question 3 — The Index Maintenance Trap

A frequently updated status column is indexed.

How might that index affect HOT update eligibility and write amplification?

### Question 4 — The Empty CPU

An API endpoint takes eight seconds, but PostgreSQL CPU usage is low and the execution plan appears efficient.

What should you investigate before rewriting the query?

### Question 5 — Connection Multiplication

Twelve application replicas each have a connection pool with a maximum size of twenty.

How many connections could they collectively attempt to maintain?

Why can adding replicas make database performance worse?

### Question 6 — WAL Growth

The `pg_wal` directory grows rapidly while table sizes remain relatively stable.

What are three plausible causes or contributors?

Would `VACUUM FULL` necessarily help?

### Question 7 — Statistics

A table reports a large estimated number of dead tuples.

Does that prove a specific number of physical dead row versions currently exists?

What other evidence would you collect?

### Question 8 — Lock Wait Versus Deadlock

Transaction A holds a lock.

Transaction B waits for that lock.

Is this a deadlock?

What additional condition creates a deadlock?

### Question 9 — Vacuum Full

Why can `VACUUM FULL` be dangerous during an incident involving low disk space and high application traffic?

### Question 10 — The Senior Incident Response

Your database has high disk usage, rising request latency, and a large number of idle-in-transaction connections.

Describe the investigation and explain why you would not immediately increase the connection limit, disable autovacuum, or rewrite the largest table.

---

# Solutions and Discussion

## Solution 1 — The Delete

Ordinary vacuum generally makes dead-tuple space available for reuse inside the relation.

It does not normally compact the entire table and return its allocated pages to the operating system.

The stable file size may therefore be expected.

Investigate whether the space is reusable and whether future growth stabilizes.

## Solution 2 — The Old Snapshot

The old transaction may still need to observe row versions that another transaction deleted.

PostgreSQL cannot safely reclaim versions while a relevant snapshot or transaction horizon requires them.

Ending the old transaction can allow cleanup to advance, assuming no other retention horizon remains.

## Solution 3 — HOT Updates

HOT updates generally require that ordinary indexed columns remain unchanged and that sufficient room exists on the original heap page.

Updating an indexed status column can prevent HOT eligibility.

That can increase index maintenance and write amplification.

The index may still be worthwhile for read workloads.

## Solution 4 — The Empty CPU

Investigate lock waits, connection-pool waits, I/O waits, and other resource contention.

A slow request does not necessarily mean the query is actively consuming CPU for its entire duration.

Use activity and wait-event evidence.

## Solution 5 — Connection Multiplication

The twelve pools could collectively attempt up to 240 connections.

Additional services and workers may increase the total.

Adding replicas can increase connection pressure and contention when the database is already the constrained resource.

## Solution 6 — WAL Growth

Possible contributors include a high rate of updates or deletes, an inactive or lagging replication slot, and failed or delayed WAL archiving.

Other configuration and recovery requirements may also affect retention.

`VACUUM FULL` does not directly solve a replication-retention problem and may generate additional write activity.

## Solution 7 — Statistics

No.

`n_dead_tup` is an estimate maintained by PostgreSQL's statistics system.

Inspect vacuum history, transaction horizons, table sizes, workload activity, and more detailed tuple statistics when necessary.

## Solution 8 — Lock Wait Versus Deadlock

Ordinary waiting is not a deadlock.

A deadlock requires a cycle of dependencies in which participants wait on resources held by one another.

PostgreSQL detects deadlocks and aborts one participating transaction.

## Solution 9 — Vacuum Full

It requires an exclusive lock, rewrites the relation, and needs additional disk space during the rewrite.

It can block application traffic and worsen storage pressure if attempted without sufficient headroom and planning.

## Solution 10 — Senior Incident Response

Identify whether the immediate problem is transaction visibility, lock contention, connection pressure, table bloat, index bloat, or WAL retention.

Inspect old transactions, blocking relationships, table statistics, relation sizes, and WAL activity.

Resolve the causal blocker where safe.

Then choose appropriate maintenance and capacity changes based on evidence.

Blindly increasing limits or disabling maintenance can amplify the underlying problem.

---

# The Mental Model Worth Keeping

PostgreSQL is not just a SQL execution engine.

It maintains multiple row versions, transaction visibility, indexes, free space, WAL, locks, and connections while application traffic continues.

A logical operation can have several physical consequences.

Deleting a row creates cleanup work.

Updating a row can create a new version and index maintenance.

Holding a transaction open can delay reclamation.

Adding workers can saturate connections.

A replication consumer can retain WAL.

The diagnostic question is:

**Which resource or retention boundary is preventing PostgreSQL from making progress?**

Identify that mechanism before choosing the intervention.

---

# Next Lecture — CS350-L04: Online Migrations and the Database Incident Studio

We now understand why PostgreSQL can suffer from dead-tuple accumulation, vacuum pressure, WAL growth, long transactions, and lock contention.

The final lecture combines those mechanisms into one of the most dangerous operational activities: changing a production database schema while the application remains online.

A migration that works perfectly on a local database can hold an unexpected lock in production.

A backfill can generate enormous WAL volume.

A newly added index can increase write amplification.

An application rollback can become incompatible with a schema that has already changed.

CS350-L04 will turn these problems into a practical incident studio.

The objective is to design, execute, observe, and recover from database changes without treating migrations as harmless deployment scripts.

*The spoken lecture ends here. The following exercises require a disposable PostgreSQL environment and are intended for independent investigation.*

---

# Optional Practical Lab — PostgreSQL Operational Forensics

## Safety and Learning Contract

This lab deliberately generates dead tuples, performs large deletes, holds transactions open, and creates lock contention.

**Run it only against a disposable local PostgreSQL instance.**

Do not point these commands at a shared development, staging, or production database.

Some experiments create changes that cannot be undone merely by rolling back a later transaction.

`VACUUM` cannot run inside a transaction block.

WAL generation and allocated storage are physical effects that are not simply erased by rolling back another transaction.

The lab follows:

**Predict → Reproduce → Inspect → Diagnose → Correct → Verify.**

Do not read the diagnostic notes until after your first independent attempt.

## Lab 1 — Create an Operational Dataset

Use the PostgreSQL container from previous CS350 exercises if available.

Otherwise, create a disposable PostgreSQL 18 container.

```bash
docker run --name cs350-postgres \
  -e POSTGRES_PASSWORD=labpass \
  -e POSTGRES_DB=cs350 \
  -p 5433:5432 \
  -d postgres:18
```

If the container exists but is stopped:

```bash
docker start cs350-postgres
```

Connect:

```bash
docker exec -it cs350-postgres \
  psql -U postgres -d cs350
```

Create a dedicated schema and table.

Autovacuum is disabled on this one disposable table so that the experiments are easier to reproduce without background cleanup changing the results.

Do not generalize this configuration to production.

```sql
DROP SCHEMA IF EXISTS cs350_ops CASCADE;
CREATE SCHEMA cs350_ops;

CREATE TABLE cs350_ops.events (
    event_id bigint PRIMARY KEY,
    account_id integer NOT NULL,
    status text NOT NULL,
    touched_at timestamptz NOT NULL,
    payload text NOT NULL
) WITH (
    autovacuum_enabled = false
);

CREATE INDEX events_account_idx
ON cs350_ops.events (account_id);

CREATE INDEX events_status_idx
ON cs350_ops.events (status);
```

Populate 200,000 events.

```sql
INSERT INTO cs350_ops.events (
    event_id,
    account_id,
    status,
    touched_at,
    payload
)
SELECT
    g,
    (g % 1000) + 1,
    'pending',
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
        + g * INTERVAL '1 second',
    repeat(md5(g::text), 4)
FROM generate_series(1, 200000) AS s(g);

ANALYZE cs350_ops.events;
```

### Establish a baseline

Measure the logical row count and physical storage allocation.

```sql
SELECT COUNT(*)
FROM cs350_ops.events;

SELECT
    pg_size_pretty(
        pg_relation_size('cs350_ops.events')
    ) AS heap_size,
    pg_size_pretty(
        pg_table_size('cs350_ops.events')
    ) AS table_storage,
    pg_size_pretty(
        pg_indexes_size('cs350_ops.events')
    ) AS index_storage,
    pg_size_pretty(
        pg_total_relation_size('cs350_ops.events')
    ) AS total_storage;
```

Record the values.

Your exact file sizes depend on PostgreSQL's storage representation and the local environment.

---

# Lab 2 — PG-02: The Delete That Doesn't Shrink the File

## Starting Symptom

The table contains 200,000 events.

The retention job deletes the oldest 100,000.

The logical row count falls.

The physical file may remain large.

### Task 1 — Predict

Before executing the delete, answer:

Will the row count decrease?

Will the heap file necessarily shrink?

Will WAL be generated?

Can PostgreSQL immediately reclaim every deleted tuple version?

### Task 2 — Delete old rows

```sql
DELETE FROM cs350_ops.events
WHERE event_id <= 100000;
```

The command should affect 100,000 rows.

Now inspect row count and relation sizes again.

```sql
SELECT COUNT(*)
FROM cs350_ops.events;

SELECT
    pg_size_pretty(
        pg_relation_size('cs350_ops.events')
    ) AS heap_size,
    pg_size_pretty(
        pg_indexes_size('cs350_ops.events')
    ) AS indexes_size,
    pg_size_pretty(
        pg_total_relation_size('cs350_ops.events')
    ) AS total_size;
```

### Task 3 — Inspect dead-tuple estimates

```sql
SELECT
    relname,
    n_live_tup,
    n_dead_tup,
    n_tup_del,
    last_vacuum,
    vacuum_count
FROM pg_stat_user_tables
WHERE schemaname = 'cs350_ops';
```

Statistics may not reflect every operation instantaneously.

Interpret them as indicators, not exact inventories.

### Task 4 — Vacuum the table

Run ordinary vacuum as a standalone command, outside an explicit transaction.

```sql
VACUUM (VERBOSE, ANALYZE) cs350_ops.events;
```

Inspect the output.

Then measure the table and index sizes again.

### Task 5 — Explain the result

Did the logical row count change during vacuum?

Did the relation file shrink?

Did PostgreSQL reclaim space internally?

Could new inserts reuse some of the available space?

### Acceptance criteria

You can explain the distinction between logical deletion and physical reclamation.

You can explain why ordinary vacuum does not guarantee a smaller table file.

You have not run `VACUUM FULL` merely to force the experiment to show a smaller size.

---

# Lab 3 — An Old Snapshot Prevents Cleanup

## Objective

Reproduce a long-running transaction that can hold back dead-tuple reclamation.

This experiment requires two separate PostgreSQL sessions.

Reset and repopulate the lab table first using Lab 1's setup.

Do not run this experiment after the deletion lab without resetting the fixture.

### Session A — Establish an old snapshot

Open the first `psql` session.

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ;

SELECT COUNT(*)
FROM cs350_ops.events
WHERE event_id <= 100000;
```

Do not commit.

Leave the session open.

The query establishes a transaction snapshot.

### Session B — Delete rows

Open another `psql` session.

```sql
DELETE FROM cs350_ops.events
WHERE event_id <= 100000;
```

Because this session uses normal autocommit behavior, the delete commits when the statement completes.

Confirm that the new transaction sees 100,000 remaining rows.

### Session B — Attempt vacuum

Run:

```sql
VACUUM (VERBOSE, ANALYZE) cs350_ops.events;
```

Inspect the verbose output.

Look for indications that dead tuples could not yet be removed.

### Session A — Verify snapshot behavior

Return to Session A.

Run the original count again.

Explain why the old snapshot may still see the rows deleted by Session B.

Then commit:

```sql
COMMIT;
```

### Session B — Vacuum again

Run:

```sql
VACUUM (VERBOSE, ANALYZE) cs350_ops.events;
```

Compare the output.

### Acceptance criteria

You can explain why the old snapshot restricted tuple cleanup.

You can distinguish the delete's logical success from the physical removal of obsolete versions.

You understand why an abandoned long-running transaction can create database-wide operational consequences.

---

# Lab 4 — Find the Old Transaction

## Objective

Use PostgreSQL's activity views to identify an open transaction.

Repeat the beginning of Lab 3 if necessary, leaving Session A open after establishing its snapshot.

Open a third session and inspect active connections.

```sql
SELECT
    pid,
    usename,
    application_name,
    state,
    clock_timestamp() - xact_start AS transaction_age,
    backend_xmin,
    wait_event_type,
    wait_event,
    query
FROM pg_stat_activity
WHERE datname = current_database()
  AND xact_start IS NOT NULL
ORDER BY xact_start;
```

### Tasks

Identify Session A.

Determine how long its transaction has been open.

Inspect its state.

Look at `backend_xmin`.

Explain why an old transaction can matter even when it is not actively consuming CPU.

Then commit Session A and observe how the activity view changes.

### Acceptance criteria

You can identify a long-running transaction using database evidence.

You do not confuse an ordinary idle connection with an idle-in-transaction connection.

You can explain which information would be useful before terminating a session in production.

---

# Lab 5 — Reproduce a Lock Wait

## Objective

Create a predictable row-level lock conflict.

Use three sessions.

### Session A — Hold a row lock

```sql
BEGIN;

UPDATE cs350_ops.events
SET status = 'processing'
WHERE event_id = 150001;
```

Do not commit.

### Session B — Attempt a conflicting update

Use a separate connection.

Set a local safety timeout and attempt to modify the same row.

```sql
BEGIN;

SET LOCAL lock_timeout = '30s';

UPDATE cs350_ops.events
SET status = 'completed'
WHERE event_id = 150001;
```

The update should wait for Session A, unless A releases its lock first.

### Session C — Inspect blocking relationships

While Session B is waiting, run:

```sql
SELECT
    pid,
    state,
    wait_event_type,
    wait_event,
    pg_blocking_pids(pid) AS blocking_pids,
    clock_timestamp() - query_start AS query_age,
    query
FROM pg_stat_activity
WHERE datname = current_database()
  AND wait_event_type = 'Lock';
```

### Tasks

Identify the blocked session.

Find the blocking process ID.

Determine which transaction holds the relevant lock.

Then commit Session A.

Observe whether Session B continues.

If Session B reaches its lock timeout, roll back its failed transaction before continuing.

### Acceptance criteria

You can distinguish lock wait time from query execution work.

You can identify the blocking session.

You understand why low CPU utilization does not rule out database contention.

You have not terminated unrelated database sessions.

---

# Lab 6 — Measure WAL Generation

## Objective

Observe that modifying data creates write-ahead log activity.

Use the same disposable database.

First record the current WAL location:

```sql
SELECT pg_current_wal_lsn() AS before_lsn;
```

Copy the returned value.

Perform a batch update:

```sql
UPDATE cs350_ops.events
SET payload = payload || '-updated'
WHERE event_id BETWEEN 150001 AND 160000;
```

Then inspect the new WAL position:

```sql
SELECT pg_current_wal_lsn() AS after_lsn;
```

Calculate the approximate WAL distance using the previously recorded LSN:

```sql
SELECT pg_wal_lsn_diff(
    pg_current_wal_lsn(),
    'REPLACE_WITH_BEFORE_LSN'::pg_lsn
) AS wal_bytes_since;
```

### Questions

Why does an update generate WAL?

Why might the WAL distance include activity unrelated to this one statement?

Why doesn't WAL generated automatically equal the current size of the `pg_wal` directory?

What would change if the workload performed many indexed-column updates?

### Additional observation

Inspect cumulative WAL statistics:

```sql
SELECT
    wal_records,
    wal_fpi,
    wal_bytes,
    stats_reset
FROM pg_stat_wal;
```

These statistics describe generated WAL activity since their reset point.

They are not an exact measurement of WAL currently retained on disk.

### Acceptance criteria

You can distinguish WAL generation from WAL retention.

You understand why an operation intended to reduce logical data can temporarily increase storage activity.

---

# Lab 7 — Investigate HOT Updates

## Objective

Observe how index design can affect update costs.

Create a separate table with free space reserved for updates.

```sql
CREATE TABLE cs350_ops.hot_demo (
    id integer PRIMARY KEY,
    mutable_value integer NOT NULL,
    payload text NOT NULL
) WITH (fillfactor = 70);

INSERT INTO cs350_ops.hot_demo (
    id,
    mutable_value,
    payload
)
SELECT
    g,
    0,
    repeat(md5(g::text), 2)
FROM generate_series(1, 20000) AS s(g);

ANALYZE cs350_ops.hot_demo;
```

Update the non-indexed value:

```sql
UPDATE cs350_ops.hot_demo
SET mutable_value = mutable_value + 1;
```

Inspect statistics:

```sql
SELECT
    relname,
    n_tup_upd,
    n_tup_hot_upd
FROM pg_stat_user_tables
WHERE schemaname = 'cs350_ops'
  AND relname = 'hot_demo';
```

Now create an index on the frequently updated column.

```sql
CREATE INDEX hot_demo_mutable_idx
ON cs350_ops.hot_demo (mutable_value);
```

Perform another update:

```sql
UPDATE cs350_ops.hot_demo
SET mutable_value = mutable_value + 1;
```

Inspect the statistics again.

### Tasks

Compare the HOT update counters.

Explain why changing an indexed column affects HOT eligibility.

Discuss why an index that improves one read query might increase the cost of a write-heavy workload.

### Important qualification

The exact number of HOT updates is not guaranteed.

Page free space, tuple layout, and the table's physical state affect eligibility.

The goal is to understand the mechanism and inspect actual evidence.

---

# Lab 8 — Connection Capacity and Pool Arithmetic

## Objective

Investigate connection pressure without deliberately exhausting the local database.

First inspect the configured connection limit.

```sql
SHOW max_connections;
```

Then inspect existing sessions.

```sql
SELECT
    state,
    COUNT(*) AS connections
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY state
ORDER BY connections DESC;
```

### Scenario

Your service has:

- Twelve application replicas.
- Twenty maximum database connections per replica.
- Four background-worker replicas.
- Ten maximum connections per background worker.

Calculate the theoretical aggregate connection demand.

Then consider other services, administrative connections, and monitoring.

### Questions

What happens if the aggregate potential demand exceeds the database's practical capacity?

How could connection-pool acquisition wait time affect HTTP latency?

Would increasing `max_connections` automatically improve throughput?

When might an external pooler help?

### Acceptance criteria

You can distinguish database connection limits from application pool limits.

You understand why scaling application replicas can amplify database pressure.

You can propose a connection budget rather than independently configuring every service pool.

---

# Lab 9 — PG-02 Incident Report

## Starting Symptom

A PostgreSQL database grows rapidly after a retention job deletes millions of old rows.

The application also reports increasing latency.

The team wants to run `VACUUM FULL` immediately.

### Your task

Prepare a short incident report based on evidence from the preceding experiments.

It should include:

**Business context:** What data was deleted, and why?

**Observed symptoms:** What changed in logical row counts, storage allocation, and latency?

**Possible mechanisms:** Dead tuples, held-back cleanup, index bloat, WAL growth, and lock contention.

**Evidence:** Which PostgreSQL views and measurements distinguish these mechanisms?

**Root-cause hypothesis:** Which mechanism best explains the observed behavior?

**Immediate response:** What should be done safely first?

**Long-term prevention:** Which application or database changes would reduce recurrence?

**Verification:** How would you know the problem was actually resolved?

### Required defense

Your interviewer says:

"The disk is almost full. Why not just run `VACUUM FULL` now?"

Explain the risks.

Then describe circumstances in which a planned table rewrite might be justified.

---

# Lab Diagnostic Notes

**Do not read until after completing the independent investigations.**

## Lab 2 — Delete and Vacuum

The delete removes logical rows from visibility to new transactions.

Ordinary vacuum can reclaim dead-tuple space for reuse.

The physical file often remains similar in size.

This does not imply that vacuum failed.

## Lab 3 — Old Snapshot

The Repeatable Read transaction retains a snapshot established before the delete.

That snapshot may still need old row versions.

Vacuum cannot reclaim them until the relevant horizon advances.

After the transaction commits, cleanup can make further progress.

## Lab 4 — Activity Inspection

`pg_stat_activity` helps identify open transactions, their ages, and relevant wait or snapshot information.

An idle-in-transaction session can retain operational resources without actively executing a query.

Not every idle session has the same consequences.

## Lab 5 — Lock Wait

Session A holds a conflicting lock.

Session B waits.

The blocker can be identified through `pg_blocking_pids()`.

The wait is not automatically a deadlock.

Committing Session A allows the waiting operation to proceed, unless it has already timed out.

## Lab 6 — WAL

Updates generate WAL because PostgreSQL must record changes needed for crash recovery and replication.

The WAL LSN distance captures log advancement over the observation interval.

It may include other activity.

Current WAL directory size depends on retention and recycling behavior, not only bytes recently generated.

## Lab 7 — HOT

Updating a non-indexed column may allow HOT updates when suitable page space exists.

Updating an indexed column generally prevents that form of HOT optimization.

The observed counters demonstrate how physical layout and index design interact with write costs.

## Lab 8 — Connection Budget

Twelve replicas with twenty connections each can demand 240 connections.

Four worker replicas with ten each add another forty.

The combined theoretical maximum is 280 connections before administrative and other service usage.

Increasing application concurrency does not guarantee database throughput increases.

## Lab 9 — Incident Response

The correct response begins by separating storage categories and identifying the actual source of pressure.

Check whether dead tuples remain unreclaimed because of transaction horizons.

Inspect WAL retention and replication status.

Investigate lock waits and connection-pool pressure.

Use ordinary vacuum where appropriate.

Only consider disruptive table rewrites after evaluating disk headroom, locking consequences, and operational necessity.

---

# Further Reading

1. **PostgreSQL — Routine Vacuuming**  
   https://www.postgresql.org/docs/18/routine-vacuuming.html

2. **PostgreSQL — VACUUM**  
   https://www.postgresql.org/docs/18/sql-vacuum.html

3. **PostgreSQL — Multiversion Concurrency Control**  
   https://www.postgresql.org/docs/18/mvcc.html

4. **PostgreSQL — Heap-Only Tuples (HOT)**  
   https://www.postgresql.org/docs/18/storage-hot.html

5. **PostgreSQL — Monitoring Database Activity**  
   https://www.postgresql.org/docs/18/monitoring.html

6. **PostgreSQL — Cumulative Statistics System**  
   https://www.postgresql.org/docs/18/monitoring-stats.html

7. **PostgreSQL — Explicit Locking**  
   https://www.postgresql.org/docs/18/explicit-locking.html

8. **PostgreSQL — Vacuum Configuration**  
   https://www.postgresql.org/docs/18/runtime-config-vacuum.html

9. **PostgreSQL — Write-Ahead Logging**  
   https://www.postgresql.org/docs/18/wal-intro.html

10. **PostgreSQL — Replication Configuration**  
    https://www.postgresql.org/docs/18/runtime-config-replication.html

11. **PostgreSQL — Replication Slots**  
    https://www.postgresql.org/docs/18/view-pg-replication-slots.html

12. **PostgreSQL — Database Object Size Functions**  
    https://www.postgresql.org/docs/18/functions-admin.html

13. **PostgreSQL — PgBouncer Documentation**  
    https://www.pgbouncer.org/features.html

Cross-reference CS330-L03 for MVCC and transaction isolation, CS350-L02 for query-plan analysis, `production-cases/PG-02.md` for the disk-growth incident, and SE335 for queue and worker concurrency diagnostics.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text
CS350-L03 — POSTGRESQL UNDER PRESSURE
================================================

THE CENTRAL DISTINCTION
-----------------------
Logical row deletion != physical shrinkage.

DELETE:
  marks row versions deleted

VACUUM:
  reclaims safely dead versions
  usually makes space reusable

VACUUM FULL:
  rewrites relation
  may return disk space
  requires ACCESS EXCLUSIVE lock
  needs temporary disk headroom

MVCC
----
Readers observe transaction snapshots.

UPDATE generally creates new row version.
DELETE does not erase tuple immediately.

Old snapshots can retain obsolete versions.

VACUUM
------
Reclaims dead tuple space.
Cleans index-related dead entries.
Maintains visibility map information.
Helps protect against XID wraparound.

Autovacuum is essential maintenance.

DISK CATEGORIES
---------------
Heap storage
Indexes
TOAST
Temporary files
WAL
Other databases and relations

Useful:
pg_relation_size()
pg_table_size()
pg_indexes_size()
pg_total_relation_size()

HOT UPDATES
-----------
Eligible when ordinary indexed
columns are not changed and
sufficient same-page space exists.

Reduces index-maintenance cost.

Inspect:
n_tup_upd
n_tup_hot_upd

LONG TRANSACTIONS
-----------------
Old snapshot can block cleanup.
Idle-in-transaction may hold locks
and transaction visibility horizons.

Inspect:
pg_stat_activity
xact_start
backend_xmin
state
wait_event_type
wait_event

LOCKS
-----
A lock wait is not necessarily a deadlock.

Use:
pg_locks
pg_blocking_pids(pid)
pg_stat_activity

Distinguish:
execution time
lock wait time
pool acquisition wait

DEADLOCK
--------
Circular wait dependency.

PostgreSQL detects and aborts
one participating transaction.

Retry safely when appropriate.
Prefer consistent lock ordering.

CONNECTIONS
-----------
Total possible demand =
sum(replica_count × pool_size)

More replicas can increase contention.

Application pool wait !=
PostgreSQL lock wait.

Idle != idle in transaction.

POOLING
-------
Application pools reuse connections.
PgBouncer can reduce backend demand.

Transaction pooling changes
session-affinity assumptions.

WAL
---
Write-Ahead Log supports recovery.
Writes generate WAL.

WAL generation != WAL retention.

Generated:
pg_stat_wal.wal_bytes

Retention:
replication slots, archiving,
recovery and checkpoint requirements

Never manually delete WAL files.

REPLICATION SLOTS
-----------------
pg_replication_slots

Important:
active
restart_lsn
xmin
catalog_xmin

Lagging slots may retain WAL.
Some slots can hold cleanup horizons.

AUTOVACUUM DIAGNOSIS
--------------------
pg_stat_user_tables:
n_live_tup
n_dead_tup
n_tup_ins
n_tup_upd
n_tup_del
last_autovacuum
autovacuum_count

These are statistics/estimates,
not exact physical tuple inventories.

VACUUM PROGRESS
---------------
pg_stat_progress_vacuum

Normal vacuum may work alongside DML.
VACUUM FULL requires exclusive access.

TABLE BLOAT VS INDEX BLOAT
--------------------------
Investigate separately.

A table can have:
- little live data
- reusable empty space
- large indexes
- outstanding dead tuples

No single metric proves bloat.

PRODUCTION INCIDENT LOOP
------------------------
1. Define exact symptom.
2. Identify constrained resource.
3. Separate cause and consequence.
4. Inspect relevant system views.
5. Identify transaction/lock/WAL horizon.
6. Form a causal hypothesis.
7. Choose smallest safe intervention.
8. Verify recovery and steady state.

NEVER DO BLINDLY
----------------
Disable autovacuum.
Run VACUUM FULL during peak traffic.
Delete pg_wal files.
Increase max_connections indefinitely.
Terminate unknown production sessions.
Add application replicas to fix DB waits.
Assume low CPU means no DB bottleneck.
Assume DELETE immediately frees disk.

INTERVIEW DIAGNOSTIC QUESTIONS
------------------------------
What physically grew?
What still needs old row versions?
Is vacuum running or blocked?
Is space reusable or truly retained?
Are locks blocking requests?
Are pools exhausted?
Is WAL generated or retained?
What are the consequences of remediation?

FINAL MENTAL MODEL
------------------
PostgreSQL preserves multiple versions
and maintains the physical machinery
required for concurrency and durability.

Identify the resource or retention
boundary preventing progress.

NEXT
----
CS350-L04 — Online Migrations
and the Database Incident Studio
```
