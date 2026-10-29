---
id: CS350-L04
course: CS350
title: "Online Migrations and the Database Incident Studio"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS350-L03
next: null
---


# CS350 — Advanced PostgreSQL Engineering
## Lecture 04: Online Migrations and the Database Incident Studio

*The migration takes twelve milliseconds in development. In production, it blocks hundreds of requests. The team rolls back the application, but the database no longer understands the old code.*

---

# Part I — Intuition

## 1. The Migration That Took Production Down

Imagine you're working at a hotel-booking company.

The reservations service has operated successfully for several years. Its PostgreSQL database contains millions of bookings, and the application handles a steady stream of searches, reservations, cancellations, and payment events.

The product team introduces a small requirement.

The booking table currently contains a column called `guest_email`. The new application will use `contact_email` instead.

The change looks trivial.

A developer updates the application code, writes a migration that renames the column, and tests everything locally.

The migration finishes almost instantly.

The new application works.

The pull request passes CI.

The release begins.

Then the monitoring dashboard turns red.

Some application instances are still running the previous version. They execute SQL referencing `guest_email`.

PostgreSQL responds that the column no longer exists.

The deployment system notices the elevated error rate and automatically rolls back the application.

Unfortunately, the rollback makes things worse.

Now all application instances expect `guest_email`, but the database contains only `contact_email`.

The application rollback succeeded.

The system rollback failed.

This is one of the most important principles in production database engineering:

**An application and its database schema must remain compatible across the actual deployment sequence, not merely at the final intended state.**

## 2. A Database Migration Is a Distributed Deployment

It is tempting to imagine a release as one atomic event.

The old application disappears, the new application appears, and the database changes at exactly the same moment.

Real deployments rarely work this way.

In a Kubernetes environment, application instances may be replaced gradually.

Old and new versions can coexist during a rolling deployment.

Background workers may run code from another version.

Scheduled jobs may execute during the rollout.

A deployment rollback may restore an earlier application image while leaving the database schema unchanged.

The database itself may have replicas and downstream consumers.

Even though PostgreSQL supports transactional DDL for many operations, it cannot atomically coordinate every application instance, worker, deployment controller, and external consumer.

This creates a compatibility problem.

### Visual anchor 1 — The deployment overlap

```text
Time ─────────────────────────────────►

Application v1  ███████████████
Application v2          ███████████████

Database schema A ███████
Database schema B        ███████████████

Overlap period:
  v1 and v2 may both access schema B
```

If schema B immediately removes something required by v1, the rollout is unsafe.

If the deployment is automatically rolled back, that incompatibility can become even more visible.

The solution is to design schema changes as a sequence of compatible transitions.

## 3. Expand, Migrate, Contract

Imagine renovating a hotel while guests continue staying there.

You wouldn't demolish the only elevator before the replacement was operational.

You would install the new elevator, verify that it works, redirect traffic, and only then remove the old one.

Database evolution follows a similar pattern.

**Expand:** Introduce the new schema without removing the old interface.

**Migrate:** Move data and application behavior toward the new representation while maintaining required compatibility.

**Contract:** Remove the old schema only after every relevant consumer has stopped depending on it.

For our email-column change, the expansion phase adds `contact_email` while preserving `guest_email`.

The application can then deploy a compatibility version that maintains both representations.

Existing records can be backfilled.

Once the new data is complete and consistent, the application can switch its reads to `contact_email`.

Only after the rollback compatibility window closes should the old column be considered for removal.

### Visual anchor 2 — A safe transition

```text
Schema A
  guest_email

       EXPAND
          |
          v

Schema B
  guest_email
  contact_email

       MIGRATE
          |
          v

Both columns maintained
Old and new versions compatible

       CONTRACT
          |
          v

Schema C
  contact_email
```

The middle stage may look redundant.

That redundancy is intentional.

It buys operational compatibility.

## 4. Schema Changes Have Physical Costs

Now consider another migration.

The application needs a new index to accelerate hotel availability searches.

A developer runs `CREATE INDEX` against a table containing twenty million rows.

The index is useful.

The SQL is correct.

But building it requires reading the table and constructing an index structure.

A conventional index build blocks concurrent writes to the table while the build runs.

For a heavily used reservation table, that may be unacceptable.

PostgreSQL supports `CREATE INDEX CONCURRENTLY`, which permits ordinary inserts, updates, and deletes to continue during the build.

However, the concurrent operation is more complicated.

It performs multiple phases, interacts with concurrent transactions, and may take longer.

If it fails, an invalid index may remain behind.

This illustrates another principle:

**A migration's logical correctness tells you very little about its operational safety.**

## 5. The Twelve-Millisecond Lock That Blocks a Website

A third incident is even stranger.

The migration adds a nullable column.

PostgreSQL doesn't need to rewrite millions of existing rows.

The actual schema modification might take milliseconds once it obtains the necessary lock.

Yet the application experiences a major outage.

How?

An earlier reporting transaction holds a lock compatible with ordinary reads.

The schema migration requests an `ACCESS EXCLUSIVE` lock.

It must wait.

Meanwhile, new application queries arrive.

PostgreSQL's lock queue may prevent those later queries from bypassing the pending exclusive request.

The application begins accumulating blocked requests.

The migration hasn't actually started changing the table.

It is merely waiting for permission.

### Visual anchor 3 — The lock queue

```text
Session A:
  Holds ACCESS SHARE
           |
           v
Session B:
  Requests ACCESS EXCLUSIVE
  Waits for A
           |
           v
Session C:
  Requests ACCESS SHARE
  May queue behind B

Result:
  Ordinary reads can become blocked
```

This is why a seemingly harmless metadata-only change can still cause a serious incident.

The time required to perform the operation is not the same as the time required to obtain the lock.

## 6. Backfills Are Production Workloads

Suppose the new `contact_email` column exists.

We now need to populate it for five million existing bookings.

A developer writes one enormous update.

PostgreSQL processes millions of rows.

The transaction generates new tuple versions, WAL, index maintenance, and potentially substantial replication lag.

It may hold row locks for a long time.

Other operations compete for I/O.

The database grows while the team attempts to complete a cleanup-oriented migration.

This is not surprising once we understand PostgreSQL's physical model.

An update is not merely an assignment to a variable.

It is a transactional modification involving storage and recovery mechanisms.

A more operationally controlled approach processes records in bounded batches.

Each batch commits separately.

The application can observe progress, pause if necessary, and resume later.

This reduces the size of each transaction and gives the system opportunities to recover between batches.

But batching is not magic.

A badly designed batch process can still overload the database.

And a backfill that competes with live application writers can create correctness problems if their ownership rules are unclear.

## 7. Rollback Is Not Time Travel

Imagine the new application has already begun writing data using a new representation.

Then the team decides to roll back.

Can we simply reverse the migration?

Sometimes.

But not always.

Suppose the new representation stores normalized lowercase email addresses while the old representation preserves original capitalization.

Reversing the transformation may not restore the exact original data.

A deleted column may have contained information that no longer exists elsewhere.

A new application version may have introduced business states that the old version doesn't understand.

And external operations—payments, messages, notifications—cannot be rolled back merely because a database transaction is reversed.

A robust migration plan therefore distinguishes two possible recovery strategies.

**Backward rollback:** Restore an earlier compatible state.

**Forward recovery:** Deploy a corrective change that restores functionality while preserving the new data.

Sometimes the second approach is safer.

### A tiny comprehension check

A migration adds a nullable column to a large table.

Is it automatically safe because PostgreSQL can perform the metadata change quickly?

No. Lock acquisition and transaction lifetime still matter.

A migration uses `CREATE INDEX CONCURRENTLY`.

Does that guarantee the operation cannot fail or interfere with production?

No. It can consume resources, wait on transactions, and leave an invalid index after failure.

The central principle is that database evolution must be designed around **compatibility, physical work, and recovery**.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 8. Three Independent Dimensions of Migration Safety

A production migration has at least three dimensions.

**Logical correctness:** Does the resulting schema represent the intended data and constraints?

**Operational safety:** Can the migration execute under the expected traffic without unacceptable locks, I/O, memory use, WAL growth, or replication lag?

**Deployment compatibility:** Can the relevant application versions and background consumers operate correctly before, during, and after the change?

A migration can satisfy one or two dimensions while failing the third.

Adding a perfectly valid constraint might block traffic while validating millions of rows.

A carefully optimized index build might still be incompatible with the deployment tooling.

A fast column rename might break an older worker.

These are different failure modes.

A strong migration review evaluates them separately.

## 9. PostgreSQL DDL Is Transactional, but That Isn't Enough

PostgreSQL supports transactional behavior for many DDL operations.

A developer can begin a transaction, perform suitable schema changes, and roll them back if necessary.

This is valuable.

But it creates an important trap.

Locks acquired by a transaction are generally held until the transaction ends.

Imagine a migration script that begins a transaction, adds a column, performs a large backfill, validates data, and commits.

Even if the column addition itself takes milliseconds, its associated lock may remain held while the transaction performs the expensive backfill.

The developer has combined a short schema operation with a long-running data operation.

The resulting lock lifetime can be disastrous.

### 9.1 Separate operations according to lock requirements

A safer approach often separates metadata changes from long-running data transformations.

The metadata change runs in a short transaction.

The backfill runs later in bounded transactions.

Constraint validation occurs when the data and application behavior are ready.

This is not universally mandatory.

Some related DDL actions benefit from atomic grouping.

But the transaction boundary must reflect the lock and failure implications.

### 9.2 Not every DDL command supports transaction blocks

`CREATE INDEX CONCURRENTLY` is a notable exception.

It cannot execute inside a transaction block.

The same applies to `DROP INDEX CONCURRENTLY`.

This matters because many migration frameworks automatically wrap migration files in transactions.

A concurrent index build may fail immediately if the migration runner attempts to execute it inside such a wrapper.

The migration system must support an explicitly nontransactional step.

Do not assume that the database's general support for transactional DDL applies to every command.

## 10. Lock Acquisition Is Part of the Migration

Different PostgreSQL schema changes require different lock modes.

Many forms of `ALTER TABLE` acquire `ACCESS EXCLUSIVE` unless the documentation specifies a weaker lock.

Other operations, including some constraint validation steps, can use less restrictive locks.

The exact lock requirement depends on the subcommand.

### 10.1 A fast change can wait indefinitely

Consider adding a nullable column.

The physical change may be nearly instantaneous.

But the migration cannot proceed until it obtains the required lock.

If a long transaction retains a conflicting lock, the DDL waits.

The waiting migration may then influence subsequent lock acquisition.

The resulting outage can be much longer than the operation itself.

### 10.2 Lock queues explain surprising outages

Imagine Session A holds an `ACCESS SHARE` lock.

Session B requests `ACCESS EXCLUSIVE` and waits.

Session C requests another `ACCESS SHARE` lock.

Although A and C's lock modes are compatible, C may wait because B's earlier conflicting request is queued.

This is an important production behavior.

A pending DDL statement can affect queries that would otherwise coexist.

### 10.3 Timeouts limit damage

A migration can establish a short `lock_timeout`.

If the required lock isn't available within the configured interval, the statement fails rather than waiting indefinitely.

This is often preferable to allowing a migration to create an expanding queue of blocked requests.

`statement_timeout` provides a separate upper bound on statement execution duration.

Neither setting makes a migration intrinsically safe.

A successful lock acquisition may still lead to expensive work.

But timeouts are useful containment mechanisms.

### 10.4 Keep lock-owning transactions short

An application or migration shouldn't hold a strong table lock while performing unrelated network calls, sleeping, or executing a long backfill unless the implications are explicitly understood.

When reviewing a migration, ask not only which lock it obtains, but **how long the transaction will retain that lock**.

## 11. Adding Columns: Fast Does Not Mean Free

PostgreSQL can add a nullable column without rewriting every existing row.

This can be a useful expansion step.

For example:

`ALTER TABLE bookings ADD COLUMN contact_email text`

Existing rows initially have null values in that column.

The operation is generally a metadata change.

But it still requires the appropriate table lock.

### 11.1 Constant defaults can be optimized

Modern PostgreSQL can add a column with a nonvolatile constant default without physically rewriting every existing row at that moment.

The database can represent the missing value through metadata until a later rewrite or update.

This is a major improvement over older approaches that required rewriting existing rows.

But don't generalize to every default expression.

A volatile default, such as one evaluated differently for each row, can require rewriting the table.

The physical consequences depend on the expression and PostgreSQL version.

### 11.2 Type changes can be expensive

Some column type changes are metadata-only or can avoid a table rewrite.

Others require converting every existing row.

For example, changing a text representation into a different storage format may require substantial work.

The `USING` clause can define how values should be transformed.

But a logically valid conversion doesn't guarantee an operationally cheap migration.

Always establish whether the proposed type change rewrites the table and which indexes or constraints may need rebuilding.

## 12. Constraint Validation Without Holding a Strong Lock for the Entire Scan

Suppose we want `contact_email` to be mandatory.

A direct `SET NOT NULL` may need to verify that every existing row satisfies the requirement.

On a large table, the validation scan can be expensive.

PostgreSQL supports a useful migration pattern involving a check constraint.

First, backfill the data.

Then add a check constraint requiring a non-null value, initially marked `NOT VALID`.

The new constraint is enforced for subsequent inserts and updates, while PostgreSQL postpones verification of all existing rows.

Later, `VALIDATE CONSTRAINT` checks the existing data using a weaker lock than many direct schema changes.

### 12.1 Why this helps

The short initial operation establishes the new write invariant.

The longer validation scan can occur separately.

The database can permit ordinary data modifications during the validation under the relevant lock rules.

After a valid check constraint proves the column cannot contain nulls, PostgreSQL can often avoid an additional full scan when setting the column's formal `NOT NULL` attribute.

### 12.2 The dangerous timing mistake

Suppose the old application is still writing null into the new column.

You add the check constraint.

Those old writes begin failing.

The migration has introduced a compatibility defect.

Therefore, constraint enforcement belongs after the application has adopted a compatible write path and the existing data has been repaired.

The order matters.

## 13. Online Index Builds

A conventional `CREATE INDEX` operation generally prevents concurrent writes to the target table while the index builds.

For a large, write-heavy table, this can be disruptive.

`CREATE INDEX CONCURRENTLY` is designed to allow ordinary writes to continue.

But it performs additional synchronization work.

### 13.1 Concurrent builds are not free

PostgreSQL must coordinate the index build with transactions that may be modifying the table.

The operation performs multiple scans and waits for relevant transactions at particular phases.

It can consume CPU, storage bandwidth, memory, and WAL-related resources.

The application may continue writing, but latency can still be affected by resource competition.

### 13.2 Only one concurrent index build per table

PostgreSQL places restrictions on concurrent index builds.

For example, only one concurrent index build can operate on a given table at a time.

Other schema changes may also conflict.

A migration planner should not blindly launch many concurrent index builds against the same busy relation.

### 13.3 Invalid indexes after failure

If a concurrent index build fails, PostgreSQL may leave an index marked invalid.

The planner cannot use an incomplete invalid index for ordinary query access.

However, that index can still consume storage and maintenance work.

A failed concurrent unique index is particularly subtle because uniqueness enforcement may already have begun before the build successfully completed.

An invalid unique index may continue enforcing uniqueness.

Therefore, failure handling must include inspecting the catalog and cleaning up or rebuilding the invalid index safely.

### 13.4 Concurrent does not mean lock-free

The word *concurrently* means that ordinary table modifications can proceed under the documented locking model.

It does not mean PostgreSQL takes no locks, waits on no transactions, or consumes no resources.

This is exactly the sort of distinction interviewers expect experienced engineers to understand.

## 14. Backfills: Transforming Millions of Rows Safely

A backfill populates or repairs existing records after a schema or business-model change.

Imagine adding `contact_email` to five million bookings.

The application needs every existing booking to receive a normalized email address.

A naive approach executes one enormous update.

That can create a large transaction, considerable WAL generation, dead tuple churn, index maintenance, and replica lag.

The database may remain under pressure long after the statement finishes.

### 14.1 Bounded batches

A safer approach processes a limited number of rows per transaction.

For example, update five thousand bookings, commit, then continue.

This limits the size and lifetime of individual transactions.

It also gives the system opportunities to observe progress and respond to changing load.

But five thousand isn't a universal ideal batch size.

The appropriate size depends on row width, indexes, trigger behavior, storage capacity, replication lag, and application traffic.

### 14.2 Idempotency and resumability

A backfill may fail halfway through.

It must be possible to restart it without corrupting already migrated rows.

One pattern updates only records where the new field is still null.

This is useful when the initial source value is stable and the new field is populated only by the migration or compatible application writers.

But if old application instances can continue changing the source field, a null-only backfill is insufficient.

A row may already contain a non-null destination value that has become stale relative to the old authoritative field.

The migration must account for concurrent writes and source-of-truth ownership.

### 14.3 `SKIP LOCKED`

PostgreSQL supports `FOR UPDATE SKIP LOCKED`, allowing a worker to skip rows currently locked by other transactions.

This can be useful for dividing work among concurrent backfill workers.

But it produces an intentionally inconsistent view of which rows are available.

That is acceptable for some work-queue-like operations.

It is not automatically suitable for arbitrary business queries.

And a worker finding no available rows does not necessarily prove all work is complete if other workers still hold locks.

The final validation must occur after the relevant workers have completed and the write path is stable.

### 14.4 Backfill correctness is a separate concern from performance

A fast backfill that overwrites newer user data is a failure.

A backfill that leaves a small percentage of records inconsistent is also a failure.

The migration needs a clear source of truth, conflict policy, and verification step.

The backfill algorithm must preserve the intended business meaning.

## 15. WAL, Replication, and the Hidden Costs of Large Changes

Every substantial update creates storage work.

PostgreSQL generates WAL to support recovery and replication.

Updating millions of rows can therefore generate substantial WAL volume.

Replicas may need time to replay the changes.

A logical replication consumer may process them more slowly than the primary generates them.

If replication slots retain WAL, storage pressure can increase.

### 15.1 Disk headroom matters

A migration may require additional storage for new indexes, row versions, WAL, and temporary files.

A table rewrite can require substantial temporary disk capacity.

Starting an expensive migration when the disk is nearly full is dangerous.

The operation intended to improve the system may exhaust its remaining storage.

### 15.2 Monitor the right metrics

Before and during a large migration, monitor:

- WAL generation rate.
- Retained WAL and replication lag.
- Table and index growth.
- Active transactions and lock waits.
- Query latency and application error rates.
- I/O pressure.
- Backfill progress and throughput.

These measurements help establish whether the operation remains within the system's operating envelope.

### 15.3 Throttling is an operational control

A backfill can deliberately pause between batches or reduce its concurrency when production latency rises.

This sacrifices completion speed to preserve service availability.

That is often the correct trade-off.

A migration is successful when the data is transformed safely while the system remains acceptably operational—not when the script finishes as quickly as possible.

## 16. The Expand–Migrate–Contract Sequence in Detail

Return to our email-column migration.

The old application reads and writes `guest_email`.

The new application will eventually use `contact_email`.

A robust transition can proceed in several stages.

### Stage 1 — Expand the schema

Add the new nullable column.

Do not remove the old column.

The old application continues working.

### Stage 2 — Deploy compatibility writers

Deploy an application version that maintains the old and new representations.

While the old column remains authoritative, compatible writers can update both columns.

The application may continue reading the old field during this stage.

This avoids switching to incomplete data prematurely.

### Stage 3 — Backfill existing records

Populate the new column for historical rows.

Use bounded transactions.

Make the process resumable.

Track progress and failures.

### Stage 4 — Eliminate incompatible old writers

Verify that no old application instances or background workers continue writing only the old column.

This is particularly important when data can change after the initial backfill.

Perform a final reconciliation against the authoritative source.

### Stage 5 — Switch reads

Deploy a version that reads the new column.

Continue maintaining the old representation for as long as rollback compatibility is required.

### Stage 6 — Validate and enforce

Verify the new representation is complete.

Add appropriate constraints.

Validate them.

Ensure new writes satisfy the established invariants.

### Stage 7 — Contract

After the rollback window closes and all consumers have migrated, remove the old representation.

This is the destructive step.

It should happen only when the organization accepts that the old application version may no longer be directly deployable.

### 16.1 Mixed-version writers create a subtle hazard

Suppose an old application instance updates `guest_email` while the new application reads `contact_email`.

If the old instance does not also update the new column, the representations diverge.

A completed backfill doesn't prevent this.

The deployment must explicitly manage the period when old and new writers coexist.

Potential strategies include a compatibility release, application-level dual writes, carefully designed database mechanisms, or temporarily restricting incompatible writers.

Each has trade-offs.

The important requirement is that the data flow remains correct throughout the transition.

## 17. Why Rollbacks Fail

A common deployment system treats rollback as redeploying the previous application artifact.

For code-only changes, that can be effective.

For schema changes, it may be insufficient.

### 17.1 The old code expects a removed column

Application v1 queries `guest_email`.

The migration drops that column.

Application v2 works.

A rollback restores v1.

Now v1 fails because its expected schema no longer exists.

### 17.2 The old code doesn't understand new data states

Suppose application v2 introduces a new booking status called `awaiting_supplier_confirmation`.

Application v1 has an exhaustive status parser that doesn't recognize it.

Even if the schema still contains all the old columns, rolling back the code may fail on newly written data.

Compatibility therefore includes **data semantics**, not just column names.

### 17.3 The transformation may be irreversible

Some migrations discard information.

If the new representation cannot reconstruct the original values, reversing the schema may not restore the old application's expectations.

Backups can help recover data, but restoring a database snapshot may also discard legitimate transactions that occurred after the snapshot.

That's a major operational decision.

### 17.4 Forward recovery may be safer

Sometimes the safest response is to deploy a new application version that corrects the defect while preserving the current schema and data.

A forward fix avoids attempting a destructive reversal of a partially completed migration.

This isn't universally preferable.

The recovery choice depends on what changed and what can safely be restored.

The important lesson is to design recovery before beginning the migration.

## 18. Deployment Ordering Is a Technical Contract

Consider a rolling deployment with twenty application pods.

You deploy the new code while the database is still on the old schema.

Will the new pods work?

Perhaps they expect a new column that doesn't yet exist.

Now reverse the order.

You migrate the database before the new application is deployed.

Will the old pods work?

Perhaps the migration removed something they still require.

A safe deployment order must account for both directions.

This is why the expanded schema should usually support both old and new application behavior.

### 18.1 Background consumers matter

Web application pods are not the only database clients.

Workers, scheduled jobs, data exporters, analytics pipelines, and administrative scripts may reference the old schema.

A migration can appear successful in the web application while breaking an overlooked background consumer hours later.

A proper migration inventory identifies all relevant readers and writers.

### 18.2 Compatibility windows are deliberate

Maintaining old and new columns temporarily creates redundancy.

But removing that redundancy too early can eliminate rollback options.

The compatibility window should be long enough to cover the actual deployment and recovery process.

After it closes, the organization can deliberately contract the schema.

## 19. A Production Migration Review Checklist

Before approving a migration, ask:

**What changes logically?**

Which schema objects, constraints, and data representations are affected?

**Which versions depend on the old representation?**

Include web services, workers, jobs, and external consumers.

**What physical work will PostgreSQL perform?**

Will it scan, rewrite, index, validate, or update large numbers of rows?

**Which locks will be acquired?**

How long might acquisition take, and how long will they be held?

**How much WAL and disk space could the operation require?**

Consider both generation and retention.

**Can the operation be paused or resumed?**

If it fails halfway through, what state remains?

**What is the recovery plan?**

Can the application roll back safely, or is forward recovery required?

**What evidence determines success?**

Schema presence alone is not enough. Verify data correctness, application compatibility, and operational health.

## 20. The Senior Engineer's Role During a Migration

A senior engineer should not merely know the SQL syntax for `ALTER TABLE`.

They should understand the risk envelope.

A schema change may be logically correct but operationally disruptive.

A backfill may complete successfully while creating replication lag.

A concurrent index build may fail and leave maintenance overhead.

A rollback may restore old code that cannot interpret the new data.

The engineering responsibility is to anticipate these interactions and design a sequence that can be observed, interrupted, and recovered.

The strongest migration is not the cleverest SQL statement.

It is the one whose effects and failure modes are understood before execution.

---

# The Oral Examination

Answer aloud before reading the solutions.

### Question 1 — The Metadata Lock

A nullable column addition takes only a few milliseconds once PostgreSQL acquires its lock.

Why can it still cause a multi-minute outage?

### Question 2 — Transactional DDL

A migration begins a transaction, adds a column, then performs a large update before committing.

Why might this be dangerous even if adding the column is fast?

### Question 3 — Concurrent Indexes

Why use `CREATE INDEX CONCURRENTLY` instead of ordinary `CREATE INDEX` on a busy table?

What important limitations and failure modes remain?

### Question 4 — Invalid Indexes

A concurrent unique index build fails because existing data contains duplicates.

What may remain in the database?

What should the engineer inspect before retrying?

### Question 5 — Backfill Strategy

A table contains ten million rows requiring a new derived field.

Why might bounded batches be preferable to one enormous update?

What makes a backfill resumable?

### Question 6 — The Mixed-Writer Problem

An old application writes only `guest_email`.

A new application reads `contact_email`.

The migration backfilled `contact_email` yesterday.

Why can the data still become inconsistent today?

### Question 7 — Constraint Validation

How can a `NOT VALID` check constraint help introduce a new invariant without performing the entire validation scan during the initial schema change?

When does it begin enforcing new writes?

### Question 8 — Deployment Rollback

Application v2 uses a new column.

The migration removes the old column.

The new application fails in production, and the deployment system restores v1.

Why can the rollback fail?

### Question 9 — WAL Pressure

A backfill causes replication lag and rapid WAL growth.

Would adding more backfill workers necessarily help?

What should be measured?

### Question 10 — Recovery Judgment

A migration is halfway complete.

The system is slow, but data remains consistent.

Would you immediately reverse the migration?

Explain what evidence you need before deciding whether to pause, roll back, or recover forward.

---

# Solutions and Discussion

### Solution 1 — The Metadata Lock

The DDL may wait for a conflicting lock held by an existing transaction.

While the exclusive lock request is queued, subsequent ordinary operations may also wait behind it.

The short execution time does not bound lock acquisition time.

### Solution 2 — Transactional DDL

Locks acquired by the schema operation may remain held until the surrounding transaction commits.

A large backfill inside the same transaction can extend the lock lifetime dramatically.

Separate short DDL transactions from long-running data transformations where appropriate.

### Solution 3 — Concurrent Indexes

Concurrent builds allow ordinary reads and writes to continue under their documented lock model.

However, they can take longer, use additional resources, wait on transactions, and leave invalid indexes after failure.

They cannot run inside a transaction block.

### Solution 4 — Invalid Indexes

An invalid index may remain.

It can consume storage and update overhead.

A failed concurrent unique index can also have unexpected uniqueness-enforcement consequences.

Inspect `pg_index` and the index definition.

Clean up or rebuild the invalid index deliberately before retrying.

### Solution 5 — Backfill Strategy

Batches limit transaction size, lock lifetime, and bursts of WAL and tuple churn.

A resumable backfill can identify unfinished records and safely continue after interruption.

Correctness also requires a clear source of truth and conflict policy for concurrent writes.

### Solution 6 — The Mixed-Writer Problem

The old application can update the authoritative old field without updating the new field.

The new representation then becomes stale.

A one-time historical backfill doesn't establish ongoing synchronization.

The deployment must eliminate incompatible writers or maintain the representations safely.

### Solution 7 — Constraint Validation

A `NOT VALID` constraint skips the initial scan of existing rows.

It is enforced for subsequent inserts and updates.

Later, `VALIDATE CONSTRAINT` checks the historical rows under a less restrictive lock than many direct schema operations.

### Solution 8 — Deployment Rollback

The old application references a column that no longer exists.

Restoring the previous container image does not restore the previous database schema or data.

A compatibility window or appropriate forward recovery is needed.

### Solution 9 — WAL Pressure

More workers can increase write concurrency, WAL generation, lock contention, and replication lag.

Measure WAL generation, retained WAL, replica replay progress, database I/O, transaction duration, and application latency.

Reduce concurrency or batch size when appropriate.

### Solution 10 — Recovery Judgment

First establish which changes committed, which operations are still running, whether data is consistent, and whether the old application remains compatible.

Determine whether the process can safely pause or resume.

Evaluate whether rollback would lose data or create additional incompatibility.

Choose the recovery path based on evidence rather than assuming reversing the SQL is always safe.

---

# The Mental Model Worth Keeping

A production migration is not one SQL statement.

It is a sequence of changes across database schema, stored data, application versions, and operational infrastructure.

Every step must preserve the required compatibility and business invariants.

The central questions are:

**What changes? What locks or physical work does it require? Which application versions must remain compatible? What happens if it fails halfway through? How will we verify and recover?**

Expand before replacing.

Backfill deliberately.

Validate before enforcing assumptions.

Contract only after old consumers and rollback requirements are retired.

---

# Course Completion — From SQL Fluency to Production Judgment

This completes the four CS350 manuscripts.

CS350-L01 established independent SQL composition.

CS350-L02 introduced measured query-plan investigation.

CS350-L03 examined PostgreSQL's operational machinery.

CS350-L04 brings those mechanisms together in schema evolution and incident response.

The course is written, but writing the manuscripts does not establish learning proficiency.

A meaningful completion requires independently solving the SQL exercises, interpreting actual plans, diagnosing physical database behavior, and reasoning through migration failure scenarios.

The next recommended specialist course is **CS345 — MongoDB Production Query Engineering**, building on the database investigation skills developed here.

*The spoken lecture ends here. The following practical investigations are designed for an isolated PostgreSQL environment. Do not run them against shared or production data.*

---

# Optional Practical Lab — The Database Migration Incident Studio

## Studio Rules

This laboratory contains deliberate faults.

You will encounter blocked DDL, failed index builds, large updates, and incompatible application versions.

Use a disposable PostgreSQL database only.

The intended process is:

**Predict → Reproduce → Inspect → Diagnose → Correct → Verify → Defend.**

Do not read the solution key before your first attempt.

Actual timings and storage effects depend on hardware, PostgreSQL version, and configuration.

No exact plan or latency result is guaranteed.

---

# Lab Setup — The Booking Table

## 1. Start PostgreSQL

Reuse the disposable PostgreSQL container from earlier CS350 lectures when possible.

Otherwise create one:

```bash
docker run --name cs350-postgres \
  -e POSTGRES_PASSWORD=labpass \
  -e POSTGRES_DB=cs350 \
  -p 5433:5432 \
  -d postgres:18
```

If the container already exists but is stopped:

```bash
docker start cs350-postgres
```

Connect using:

```bash
docker exec -it cs350-postgres \
  psql -U postgres -d cs350
```

For investigations requiring multiple sessions, open separate terminal windows with independent `psql` connections.

## 2. Create the fixture

The following commands reset only the dedicated migration-lab schema.

```sql
DROP SCHEMA IF EXISTS cs350_migration CASCADE;

CREATE SCHEMA cs350_migration;

CREATE TABLE cs350_migration.bookings (
    booking_id bigint PRIMARY KEY,
    guest_email text NOT NULL,
    status text NOT NULL,
    amount_eur numeric(12,2) NOT NULL,
    created_at timestamptz NOT NULL
);
```

Generate 120,000 bookings.

```sql
INSERT INTO cs350_migration.bookings (
    booking_id,
    guest_email,
    status,
    amount_eur,
    created_at
)
SELECT
    g,
    'Guest' || g || '@Example.COM',
    CASE
        WHEN g % 10 < 8 THEN 'confirmed'
        ELSE 'cancelled'
    END,
    (50 + g % 500)::numeric(12,2),
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
        + g * INTERVAL '10 seconds'
FROM generate_series(1, 120000) AS s(g);

ANALYZE cs350_migration.bookings;
```

Verify the fixture:

```sql
SELECT COUNT(*)
FROM cs350_migration.bookings;
```

Expected result: 120,000 rows.

The fixture is deliberately large enough to generate measurable work but small enough for ordinary local hardware.

---

# Incident 1 — The Twelve-Millisecond Migration That Blocks Reads

## Starting Symptom

An engineer adds a nullable column.

The operation is normally fast.

But the migration waits, and unrelated requests begin blocking.

The interviewer asks:

"Why is a metadata-only change affecting normal reads?"

## Session A — Hold an ordinary read transaction

Open the first `psql` session.

```sql
SET application_name = 'migration_lab_A';

BEGIN;

SELECT COUNT(*)
FROM cs350_migration.bookings;
```

Leave the transaction open.

The transaction retains its table-level `ACCESS SHARE` lock until it ends.

## Session B — Attempt the schema change

Open a second connection.

```sql
SET application_name = 'migration_lab_B';
SET lock_timeout = '60s';

ALTER TABLE cs350_migration.bookings
ADD COLUMN migration_marker text;
```

The command should wait for Session A's conflicting lock while that transaction remains open.

Do not commit Session A yet.

## Session C — Attempt another ordinary read

Open a third connection.

```sql
SET application_name = 'migration_lab_C';
SET lock_timeout = '60s';

SELECT COUNT(*)
FROM cs350_migration.bookings;
```

Observe whether this read waits behind the pending exclusive lock request.

## Session D — Inspect the lock queue

Open a fourth connection.

```sql
SELECT
    pid,
    application_name,
    state,
    wait_event_type,
    wait_event,
    pg_blocking_pids(pid) AS blocking_pids,
    query
FROM pg_stat_activity
WHERE application_name LIKE 'migration_lab_%'
ORDER BY application_name;
```

### Investigation

Identify which session holds the original lock.

Which session requests `ACCESS EXCLUSIVE`?

Why can Session C wait even though its requested lock would otherwise be compatible with Session A?

What happens when Session A commits?

### Recovery

Return to Session A and run:

```sql
COMMIT;
```

Observe Sessions B and C.

If a statement timed out, record the error and cleanly end any failed transaction before continuing.

### Acceptance criteria

You can explain why lock acquisition time matters more than the intrinsic duration of the metadata change.

You can identify the blocking relationships through PostgreSQL evidence.

You can explain why a short `lock_timeout` is useful in production migration tooling.

---

# Incident 2 — The Backfill That Creates More Work Than Expected

## Starting Symptom

The team adds `contact_email` to the booking table.

The new field should contain a lowercase normalization of `guest_email`.

The first engineer proposes updating all 120,000 rows in one transaction.

You are asked to design a safer approach.

## Step 1 — Expand

Add the nullable destination column.

```sql
ALTER TABLE cs350_migration.bookings
ADD COLUMN contact_email text;
```

The old application remains compatible because `guest_email` still exists.

## Step 2 — Establish baseline observations

Record the current WAL location.

```sql
SELECT pg_current_wal_lsn();
```

Record the relation size:

```sql
SELECT
    pg_size_pretty(
        pg_total_relation_size('cs350_migration.bookings')
    ) AS total_size;
```

Copy the values into your investigation notes.

## Step 3 — Construct a bounded batch

The following query updates at most 5,000 unfinished rows.

It uses a CTE to select work and then updates the corresponding bookings.

```sql
WITH batch AS (
    SELECT booking_id
    FROM cs350_migration.bookings
    WHERE contact_email IS NULL
    ORDER BY booking_id
    LIMIT 5000
    FOR UPDATE SKIP LOCKED
),
changed AS (
    UPDATE cs350_migration.bookings b
    SET contact_email = lower(b.guest_email)
    FROM batch
    WHERE b.booking_id = batch.booking_id
    RETURNING b.booking_id
)
SELECT COUNT(*) AS changed_rows
FROM changed;
```

### Prediction

How many rows should the first batch update?

What happens if you execute it a second time?

Why does each batch need a committed transaction boundary?

What happens if the process crashes after twelve completed batches?

## Step 4 — Run the backfill repeatedly

You can execute the batch manually several times to observe the behavior.

For a complete automated run, use a small Python script with Psycopg.

Install the dependency in a disposable virtual environment:

```bash
python -m pip install "psycopg[binary]"
```

Create `backfill.py`:

```python
import time
import psycopg

DSN = "postgresql://postgres:labpass@localhost:5433/cs350"

BATCH_SQL = """
WITH batch AS (
    SELECT booking_id
    FROM cs350_migration.bookings
    WHERE contact_email IS NULL
    ORDER BY booking_id
    LIMIT 5000
    FOR UPDATE SKIP LOCKED
),
changed AS (
    UPDATE cs350_migration.bookings b
    SET contact_email = lower(b.guest_email)
    FROM batch
    WHERE b.booking_id = batch.booking_id
    RETURNING b.booking_id
)
SELECT COUNT(*) FROM changed
"""

def main():
    total = 0

    with psycopg.connect(DSN, autocommit=True) as conn:
        for batch_number in range(1, 101):
            with conn.cursor() as cur:
                cur.execute(BATCH_SQL)
                count = cur.fetchone()[0]

            total += count
            print(
                f"Batch {batch_number}: "
                f"{count} rows, total {total}"
            )

            if count == 0:
                break

            time.sleep(0.05)

    print("Backfill loop complete.")

if __name__ == "__main__":
    main()
```

This laboratory script uses autocommit so that each batch is its own transaction.

The iteration limit prevents an accidental unbounded loop.

The short delay is illustrative rather than an optimal production throttle.

For concurrent workers, a zero-row batch result may mean rows were temporarily locked rather than that all work is complete. Final validation must occur separately.

## Step 5 — Verify correctness

After all workers finish:

```sql
SELECT COUNT(*) AS remaining
FROM cs350_migration.bookings
WHERE contact_email IS NULL;
```

Expected result: zero.

Verify the transformation:

```sql
SELECT COUNT(*) AS mismatches
FROM cs350_migration.bookings
WHERE contact_email IS DISTINCT FROM lower(guest_email);
```

Expected result: zero, provided no incompatible concurrent application writers changed the source during the experiment.

## Step 6 — Inspect physical consequences

Measure table size again.

Inspect WAL advancement using the baseline LSN recorded before the backfill:

```sql
SELECT pg_wal_lsn_diff(
    pg_current_wal_lsn(),
    'REPLACE_WITH_BASELINE_LSN'::pg_lsn
) AS wal_bytes_since;
```

Also inspect table update statistics:

```sql
SELECT
    n_tup_upd,
    n_tup_hot_upd,
    n_dead_tup
FROM pg_stat_user_tables
WHERE schemaname = 'cs350_migration'
  AND relname = 'bookings';
```

### Questions

Why did a column population create new row versions?

Why did WAL increase?

Could the updated tuples qualify for HOT updates?

What changes if the new column is indexed before the backfill?

Why would adding ten parallel backfill workers not necessarily improve the system?

### Acceptance criteria

The backfill is resumable.

Each batch has a bounded transaction lifetime.

The final data is correct.

You can explain the physical work generated by the update.

---

# Incident 3 — Enforcing a Constraint Without One Giant Validation Lock

## Starting Symptom

The backfill has completed.

The application now guarantees that all new bookings contain `contact_email`.

You want to enforce the non-null invariant.

The interviewer asks:

"How would you introduce the constraint without unnecessarily holding a strong lock during a large validation scan?"

## Step 1 — Add a check constraint without initial validation

```sql
ALTER TABLE cs350_migration.bookings
ADD CONSTRAINT contact_email_present
CHECK (contact_email IS NOT NULL)
NOT VALID;
```

The constraint now applies to subsequent inserts and updates.

Existing rows have not yet been fully validated by the constraint mechanism.

## Step 2 — Inspect constraint state

```sql
SELECT
    conname,
    convalidated
FROM pg_constraint
WHERE conrelid = 'cs350_migration.bookings'::regclass
  AND conname = 'contact_email_present';
```

### Prediction

What should `convalidated` indicate?

Can a new row with null `contact_email` be inserted?

Does the database already consider every historical row formally validated?

## Step 3 — Validate existing data

```sql
ALTER TABLE cs350_migration.bookings
VALIDATE CONSTRAINT contact_email_present;
```

Inspect the catalog again.

### Step 4 — Set the column formally NOT NULL

```sql
ALTER TABLE cs350_migration.bookings
ALTER COLUMN contact_email SET NOT NULL;
```

PostgreSQL can use a suitable valid check constraint to avoid an additional complete table scan for the non-null proof.

The final metadata operation still has its own lock requirements.

## Step 5 — Consider the mixed-version deployment

Suppose old application instances still insert bookings using only `guest_email`.

Would they continue working after the constraint is added?

Explain why not.

### Acceptance criteria

You understand the difference between installing a constraint and validating historical rows.

You can explain the ordering requirements between application deployment, backfill, and constraint enforcement.

---

# Incident 4 — Concurrent Index Build Failure

## Starting Symptom

The team wants an index supporting a frequently used status-and-date query.

A conventional index build could block writes.

The team chooses a concurrent build.

## Step 1 — Build a valid index concurrently

Execute the following command outside any explicit transaction block:

```sql
CREATE INDEX CONCURRENTLY bookings_status_date_idx
ON cs350_migration.bookings (
    status,
    created_at DESC
);
```

This command may complete quickly on the fixture.

On larger datasets, its progress can be observed using:

```sql
SELECT
    pid,
    phase,
    blocks_done,
    blocks_total,
    tuples_done,
    tuples_total
FROM pg_stat_progress_create_index;
```

If the build finishes before you query the progress view, that is normal.

## Step 2 — Inspect the index

```sql
SELECT
    indexrelid::regclass AS index_name,
    indisvalid,
    indisready
FROM pg_index
WHERE indrelid = 'cs350_migration.bookings'::regclass;
```

Find the newly created index.

Verify that it is valid.

## Step 3 — Deliberately create a failing unique index

The `status` column contains many duplicate values.

Attempting to enforce uniqueness on it is incorrect.

Run this only in the disposable lab:

```sql
CREATE UNIQUE INDEX CONCURRENTLY bookings_status_unique_bad
ON cs350_migration.bookings (status);
```

The operation should fail because duplicate statuses exist.

### Investigation

What remains after the failure?

Inspect `pg_index`.

Does the failed index appear?

Is it marked valid?

Why is an invalid index not necessarily harmless?

## Step 4 — Clean up

Run outside a transaction block:

```sql
DROP INDEX CONCURRENTLY IF EXISTS
cs350_migration.bookings_status_unique_bad;
```

### Acceptance criteria

You can explain why concurrent index creation permits ordinary writes but still has operational costs.

You understand why the command cannot run inside a transaction block.

You can identify and clean up a failed invalid index.

You recognize that a failed concurrent unique index may have begun enforcing uniqueness before becoming valid.

---

# Incident 5 — RELEASE-01: The Rollback That Cannot Understand the Schema

## Starting Symptom

Application v1 reads and writes `guest_email`.

Application v2 reads and writes `contact_email`.

The team completes its migration and removes `guest_email`.

Then an unrelated bug forces an application rollback.

The old application fails immediately.

## Phase A — Reproduce the dangerous contract

After completing the backfill and constraint exercises, verify that both email columns exist.

Run an old-version query:

```sql
SELECT booking_id, guest_email
FROM cs350_migration.bookings
WHERE booking_id = 42;
```

Run a new-version query:

```sql
SELECT booking_id, contact_email
FROM cs350_migration.bookings
WHERE booking_id = 42;
```

Both should work.

Now simulate a premature contraction:

```sql
ALTER TABLE cs350_migration.bookings
DROP COLUMN guest_email;
```

Run the old query again.

### Investigation

What error occurs?

Would redeploying application v1 fix the database schema?

What information would you need to reconstruct the removed column?

Is the transformation reversible without losing information?

## Phase B — Design the correct release sequence

Without immediately writing SQL, create a deployment plan that includes:

1. Schema expansion.
2. Compatibility-version deployment.
3. Backfill.
4. Final reconciliation.
5. Read-path cutover.
6. Constraint validation.
7. Compatibility window.
8. Destructive contraction.

For every phase, describe which application versions can safely operate.

## Phase C — Mixed writers

Suppose application v1 remains deployed during the backfill.

It updates `guest_email` for booking 42.

Application v2 reads `contact_email`.

Explain why the values can diverge.

Would repeating a backfill that updates only null values necessarily repair the problem?

What source-of-truth policy would you use during the transition?

## Phase D — Recovery choice

Imagine the old column has already been dropped in production.

The new application is failing for an unrelated reason.

Choose between:

- Restoring the old schema and data.
- Deploying a corrected new application version.
- Restoring from backup.
- A more carefully staged recovery.

Explain what evidence is required before making that choice.

### Acceptance criteria

You can explain why application rollback and database rollback are different operations.

You can design a compatibility-preserving release sequence.

You recognize that dual writes, backfills, and cutover ordering have correctness requirements.

---

# Final Studio — The Migration Incident Review

## Scenario

A PostgreSQL database contains twenty million reservations.

The engineering team plans to:

- Add a new non-null field.
- Backfill all historical records.
- Create a composite index.
- Deploy application v2.
- Drop the old field.

The original proposal is one migration script:

```sql
BEGIN;

ALTER TABLE bookings
ADD COLUMN contact_email text;

UPDATE bookings
SET contact_email = lower(guest_email);

ALTER TABLE bookings
ALTER COLUMN contact_email SET NOT NULL;

CREATE INDEX bookings_contact_email_idx
ON bookings (contact_email);

ALTER TABLE bookings
DROP COLUMN guest_email;

COMMIT;
```

The migration is logically plausible.

It may even work on a small development database.

Your task is to review it for production safety.

## Required Review

Identify:

**Lock risk:** Which operations can hold strong locks?

**Transaction risk:** What happens when everything is inside one transaction?

**Backfill risk:** How much update work might the operation create?

**Index risk:** What happens while the index is built?

**Compatibility risk:** Can application v1 continue working?

**Rollback risk:** What happens if v2 fails after the schema change?

**Storage risk:** How much additional heap, index, and WAL activity might occur?

**Recovery risk:** What state remains if the deployment fails partway through?

Then propose a corrected sequence.

Do not merely say "use `CONCURRENTLY`."

The solution must address all relevant failure mechanisms.

---

# STOP — End of Independent Studio

Do not read the following diagnostic notes until you've attempted the incidents.

The goal is to reason from evidence rather than recognize a previously supplied answer.

---

# Studio Diagnostic Notes

## Incident 1 — Lock Queue

Session A holds an `ACCESS SHARE` lock.

Session B requests `ACCESS EXCLUSIVE` and waits.

Session C may be queued behind B even though its lock mode would otherwise be compatible with A.

The incident demonstrates that a short metadata operation can cause widespread blocking during lock acquisition.

A bounded lock timeout can prevent indefinite waiting.

## Incident 2 — Backfill

Bounded batches reduce transaction size and make progress observable.

The update still generates row versions and WAL.

The null-only predicate makes the script resumable under the fixture's assumptions.

A production migration requires a compatible write path and final reconciliation before relying on the new data.

## Incident 3 — Constraint Validation

A `NOT VALID` check constraint skips the initial historical scan but enforces subsequent writes.

`VALIDATE CONSTRAINT` verifies existing rows separately.

A valid non-null check can support setting the formal `NOT NULL` attribute without another full table scan.

The deployment must ensure old application writers no longer violate the new rule.

## Incident 4 — Concurrent Index

Concurrent index creation permits ordinary DML during the build but uses multiple phases and may wait on transactions.

Failure can leave an invalid index.

An invalid unique index can still have unexpected enforcement consequences.

Inspect and clean up failed artifacts before retrying.

## Incident 5 — Rollback

Dropping the old column breaks application v1.

Redeploying v1 does not restore that column.

The safest sequence maintains an overlap period where the schema supports both versions.

The compatibility release, backfill, cutover, and contraction must be coordinated.

When contraction has already occurred, forward recovery may be safer than attempting to reconstruct an old representation.

## Final Studio — Corrected Migration Strategy

A strong proposal separates the work into phases.

First, add the nullable column through a short schema migration.

Second, deploy compatible application writers and retain the old read path.

Third, backfill existing rows in bounded, resumable transactions.

Fourth, eliminate incompatible writers and reconcile any divergence.

Fifth, switch reads while maintaining rollback-compatible writes.

Sixth, introduce and validate constraints.

Seventh, build required indexes concurrently in separate nontransactional migration steps.

Finally, remove the old column only after compatibility requirements have ended.

The sequence should include monitoring, timeouts, rollback decisions, and explicit verification gates between phases.

The exact deployment order may vary with the application's data ownership and operational environment.

The important invariant is that each intermediate state remains safe.

---

# Further Reading

1. **PostgreSQL — ALTER TABLE**  
   https://www.postgresql.org/docs/18/sql-altertable.html

2. **PostgreSQL — CREATE INDEX**  
   https://www.postgresql.org/docs/18/sql-createindex.html

3. **PostgreSQL — Explicit Locking**  
   https://www.postgresql.org/docs/18/explicit-locking.html

4. **PostgreSQL — UPDATE**  
   https://www.postgresql.org/docs/18/sql-update.html

5. **PostgreSQL — Progress Reporting**  
   https://www.postgresql.org/docs/18/progress-reporting.html

6. **PostgreSQL — Monitoring Statistics**  
   https://www.postgresql.org/docs/18/monitoring-stats.html

7. **PostgreSQL — Transaction Isolation**  
   https://www.postgresql.org/docs/18/transaction-iso.html

8. **PostgreSQL — Write-Ahead Logging**  
   https://www.postgresql.org/docs/18/wal-intro.html

9. **PostgreSQL — Routine Vacuuming**  
   https://www.postgresql.org/docs/18/routine-vacuuming.html

10. **PostgreSQL — CREATE STATISTICS and Planner Statistics**  
    https://www.postgresql.org/docs/18/planner-stats.html

Cross-reference CS330-L03 for transaction isolation, CS350-L01 for SQL correctness, CS350-L02 for query plans, CS350-L03 for MVCC and operational pressure, SE340 for deployment engineering, and `production-cases/RELEASE-01.md` for the rollback incident.

---

# Dense Cheatsheet — Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text
CS350-L04 — ONLINE MIGRATIONS & INCIDENTS
================================================

THREE DIMENSIONS
----------------
1. Logical correctness
2. Operational safety
3. Deployment compatibility

A migration must satisfy all three.

EXPAND — MIGRATE — CONTRACT
--------------------------
EXPAND:
  Add new schema without breaking old code.

MIGRATE:
  Compatible writers
  Backfill existing data
  Reconcile
  Switch reads
  Validate invariants

CONTRACT:
  Remove old schema after rollback window.

COMPATIBILITY
-------------
Old and new app versions may coexist.

Database schema must support
the actual deployment overlap.

Web pods aren't the only consumers.
Include workers, jobs, ETL, integrations.

LOCKS
-----
Many ALTER TABLE forms require
ACCESS EXCLUSIVE unless noted.

Metadata-only != lock-free.

A pending exclusive lock can
cause later ordinary queries to wait.

Use bounded lock_timeout.
Keep lock-owning transactions short.

DDL TRANSACTIONS
----------------
Many DDL operations are transactional.
Locks generally persist until commit.

Avoid wrapping short metadata changes
and huge backfills in one transaction.

CREATE INDEX CONCURRENTLY
-------------------------
Allows ordinary DML to proceed.

Costs:
- multiple scans
- transaction waits
- I/O and WAL
- possible invalid index on failure

Cannot run inside transaction block.

DROP INDEX CONCURRENTLY
also requires nontransactional execution.

INVALID INDEX
-------------
pg_index.indisvalid
pg_index.indisready

Failed concurrent build may leave index.
Can consume write overhead.

Failed unique build may already
enforce uniqueness.

Inspect and clean up safely.

BACKFILLS
---------
Use bounded batches.
Commit each batch.
Measure progress.
Support restart.
Throttle if necessary.

SKIP LOCKED can divide worker jobs
but empty batch != always complete.

Correctness requires source-of-truth
and concurrent-writer policy.

PHYSICAL WRITE COST
-------------------
UPDATE creates tuple versions.
Can generate WAL and index churn.
May cause replica lag and bloat.

More workers != guaranteed faster.

CONSTRAINTS
-----------
ADD CHECK ... NOT VALID:
  skips initial scan
  enforces new writes

VALIDATE CONSTRAINT:
  checks historical rows
  uses weaker lock than many DDL forms

Valid CHECK may prove NOT NULL
and avoid redundant table scan.

DEPLOYMENT PHASES
-----------------
1. Expand schema
2. Deploy compatible writers
3. Backfill
4. Drain incompatible writers
5. Reconcile
6. Switch reads
7. Enforce constraints
8. Wait through rollback window
9. Contract schema

ROLLBACK
--------
Code rollback != database rollback.

Dropped columns can break old code.
New data states can break old parsers.
Some transformations lose information.

Sometimes forward recovery is safer.

WAL AND DISK
------------
Large changes generate WAL.

Monitor:
- WAL generation
- retained WAL
- replication lag
- table and index size
- I/O
- active transactions

Do not run large rewrites with
insufficient disk headroom.

PRODUCTION MIGRATION REVIEW
---------------------------
What does one step change?
Which locks are needed?
How long can it wait?
How long are locks held?
Will it scan or rewrite data?
What storage/WAL will it create?
Which application versions still run?
Can it pause and resume?
What remains after failure?
How will correctness be verified?
How will the system recover?

ANTI-PATTERNS
-------------
"Works on my local database."
"ALTER TABLE is always instant."
"Transactional DDL means zero downtime."
"CONCURRENTLY means no locks or waits."
"Backfill all rows in one giant UPDATE."
"Drop the old column with the new release."
"Rollback the container, problem solved."
"More backfill workers always helps."
"Ignore invalid indexes after failure."
"Migration succeeded, so release is safe."

COURSE COMPLETION
-----------------
CS350-L01:
  SQL fluency and relational correctness

CS350-L02:
  Query-plan evidence and performance

CS350-L03:
  MVCC, vacuum, WAL, locks, connections

CS350-L04:
  Online schema changes and recovery

MENTAL MODEL
------------
A migration is a distributed,
multi-stage compatibility operation.

Preserve invariants at every stage.
Measure physical costs.
Plan failure and recovery in advance.

NEXT SPECIALIST COURSE
----------------------
CS345 — MongoDB Production Query Engineering
```
