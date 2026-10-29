---
id: SE325-L02
course: SE325
title: "Bulk Imports, Exports, and Background Data Operations"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE325-L01
next: SE325-L03
---

# SE325 — Backends in the Wild: Production Field Guide
## Lecture 02: Bulk Imports, Exports, and Background Data Operations

*One customer requests an enormous property-catalogue export. Ten minutes later, the shared database connection pool is exhausted. Meanwhile, a supplier's million-row import has stopped at row 412,883, and nobody can determine whether restarting it will duplicate the first 412,882 records.*

---

# Part I — Intuition

## 1. The Spreadsheet That Nearly Took Down the Booking Platform

Imagine you're working at Mercury, a hotel-booking platform.

The company works with several large accommodation suppliers. Each supplier maintains thousands of properties, room categories, seasonal prices, availability rules, and promotional offers.

Some integrations use APIs.

Others still exchange CSV files.

One Monday morning, a supplier uploads a file containing one million nightly room rates.

The operations team clicks Import.

Your backend begins processing the file.

The first hundred thousand records arrive successfully. Then another hundred thousand. The application appears to be making progress.

At row 412,883, something goes wrong.

A price is negative.

The database rejects it.

The import job crashes.

Operations receives an error saying that the import failed.

They ask a reasonable question:

"Can we run it again?"

You look at the implementation.

It reads the file from the beginning and inserts records one by one.

There is no persistent checkpoint.

Some records were committed.

Some may have been updated.

One row failed.

And you cannot immediately establish which changes are already present.

Meanwhile, another customer requests an export of every property in their account.

The export launches a huge database query, retrieves hundreds of thousands of records into application memory, and begins generating a spreadsheet.

Several exports start at once.

Now your booking API is running out of database connections.

Customers trying to reserve rooms receive timeouts.

The import and export features aren't the most important business operations on the platform.

Yet they've managed to interfere with the operations that actually generate revenue.

This is the central problem of bulk processing.

**A small operation should complete correctly. A large operation must also survive partial completion, consume bounded resources, and avoid damaging everything around it.**

## 2. A Million Records Are Not One Operation

Let's begin with an important distinction.

Suppose a customer changes their telephone number.

The backend performs one authorized update.

It either commits or fails.

Now suppose a supplier submits one million room-rate updates.

Should those updates form one enormous transaction?

Sometimes atomic publication of the complete dataset is a genuine business requirement.

But that doesn't necessarily mean processing every row inside one gigantic database transaction.

The system can separate preparing data from making it authoritative.

For example, it might process records into a staging area, validate the resulting dataset, and then activate a particular version.

Other workflows may permit partial success.

Perhaps valid rows can be imported while invalid rows are quarantined for correction.

The correct behavior depends on the business contract.

### Visual anchor 1 — One file, many controlled operations

The first diagram shows how a large file can become a sequence of bounded processing steps.

```text id="s3252a"
Supplier CSV
1,000,000 records
       |
       v
  Stream parser
       |
       v
  Validate rows
       |
       v
  Batch 1
  Batch 2
  Batch 3
    ...
  Batch N
       |
       v
 Import result:
 accepted / rejected / completed
```

The important insight is that the file's size doesn't have to determine the size of one transaction or one in-memory data structure.

## 3. Checkpoints Are Bookmarks

Imagine reading a thousand-page book.

You finish four hundred pages.

Then somebody takes the book away.

If you have a bookmark, you can resume where you stopped.

Without a bookmark, you have to begin again—or guess.

A processing checkpoint serves a similar purpose.

It records how much work has been safely completed.

Suppose the importer processes records in batches of one thousand.

After the first batch commits, it records a checkpoint.

After the second batch commits, it advances the checkpoint.

If the worker crashes after batch 412, another worker can resume from the next unprocessed batch.

But there is a catch.

The bookmark must accurately represent committed work.

If the application records progress *before* the database commits and then crashes, it may permanently skip records that were never saved.

If it commits database changes and crashes *before* recording the checkpoint, it may process those records again.

That means a reliable importer needs a relationship between its checkpoint and the business effects of processing.

### Visual anchor 2 — The checkpoint and commit

```text id="s3252b"
Process batch 412
        |
        v
Begin DB transaction
        |
        +-- Apply valid records
        +-- Record rejected rows
        +-- Advance checkpoint
        |
        v
Commit transaction
        |
        v
Batch 412 is durable
```

When the data changes and checkpoint live in the same database transaction, they can be committed together.

When external services are involved, that guarantee may no longer be available.

## 4. A Failed Row Is a Business Decision

Return to row 412,883.

The supplier provides a nightly rate of negative five euros.

What should happen?

We could reject the entire million-row file.

We could skip the invalid row.

We could store it in a quarantine table and continue.

We could stop after a maximum number of errors.

Or we could reject the entire import *as an authoritative dataset* while preserving the staging results for correction.

Each option is defensible in certain circumstances.

For example, importing financial settlement records might require strict consistency.

Importing a large catalogue of descriptive attributes might allow isolated validation failures.

A supplier price feed could tolerate some rejected rows—but publishing an incomplete pricing catalogue without warning might be commercially dangerous.

The essential requirement is to define the policy before the job runs.

**A processing system cannot decide whether partial success is acceptable without understanding what the data means.**

## 5. Streaming Saves Memory, Not Automatically the Database

Now consider the export problem.

A developer writes a query that retrieves one million booking records.

The application stores all the rows in an array.

Then it converts them into a CSV file.

The resulting memory consumption can become enormous.

Streaming the query results into an output file can reduce application-memory pressure.

But streaming doesn't automatically make the database query cheap.

The database may still need to scan, join, sort, or aggregate large amounts of data.

A query can return records incrementally while consuming significant database CPU, I/O, temporary storage, or a long-lived transaction snapshot.

Streaming solves one resource problem.

It doesn't eliminate the others.

## 6. The Export Is Competing with Paying Customers

Picture a restaurant with ten cooks.

During normal service, eight cooks handle customers' meals and two prepare ingredients for tomorrow.

Now the manager assigns all ten cooks to prepare a giant catering order.

The catering order is important.

But suddenly, nobody can prepare food for the customers already sitting in the restaurant.

A production database faces similar resource competition.

Interactive booking requests need low latency.

Bulk exports often value throughput more than immediate responsiveness.

If both workloads share the same connection pool and resource budget without limits, one large background operation can degrade the entire application.

### Visual anchor 3 — Shared capacity is the danger

```text id="s3252c"
                 Database
              20 connections
                    |
          +---------+---------+
          |                   |
   Booking requests       Bulk exports
   need low latency       need throughput
          |                   |
          +---------+---------+
                    |
             Shared limit
```

The solution isn't necessarily a larger database.

It may involve bounded concurrency, separate connection pools, read replicas, query budgets, job admission controls, or scheduled capacity allocation.

## 7. Progress Is More Than a Percentage

Suppose your import UI says:

"87% complete."

What does that mean?

Maybe 87% of the file has been read.

Maybe 87% of the rows have been validated.

Maybe 87% have been committed.

Maybe 87% of the expected runtime has elapsed.

Those are different measurements.

A supplier who sees 100% uploaded may understandably believe that their rates are already available to customers.

But the file may still be undergoing validation.

A truthful status display distinguishes the stages.

For example:

Upload complete.

Import processing.

412,000 records examined.

411,995 accepted.

Five rejected.

Publication pending.

That tells the operator what actually happened.

## 8. Cancellation Isn't Time Travel

The operations team notices that the uploaded rate file belongs to the wrong supplier.

They click Cancel.

What should happen?

The worker should stop beginning new work.

But what about the 300,000 records already committed?

Cancellation doesn't automatically undo them.

Perhaps the importer writes into an isolated staging dataset that can be discarded safely.

Perhaps it updates authoritative records directly, in which case recovery may require reconciliation or compensating operations.

The architecture must decide what cancellation means.

For a bulk job, cancellation usually means **stop future processing at a safe boundary**, not magically reverse every completed effect.

### A tiny comprehension check

An import worker commits records and then crashes before acknowledging its queue message. What must the system tolerate?

A retry of work that may already have committed.

A CSV export streams rows using a database cursor. Does this guarantee that the database isn't under heavy load?

No. Streaming reduces client memory pressure but doesn't eliminate expensive query execution or transaction costs.

A job reports 100% of rows examined, but 300 rows were rejected. Is the dataset necessarily ready for publication?

No. Publication depends on the agreed acceptance policy.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 9. The Real Unit of Work Is a Business Decision

SE320-L03 introduced queues, workers, retries, and idempotency.

Here we assume that foundation.

Our concern is what happens *inside* a long-running data job and how its work affects the rest of production.

Start by defining the operation's business contract.

A supplier submits a file containing one million rate updates.

What does one row represent?

Perhaps one rate for a particular room type, date, currency, and sales channel.

That identity matters.

If we read the same row twice, should we create two rates?

Probably not.

If the same room and date appear several times with different prices, which value wins?

The answer isn't automatically "the last row."

Perhaps duplicates are invalid.

Perhaps the supplier provides revision numbers.

Perhaps the most recently published rate is authoritative.

Until we define the identity and conflict policy, the importer cannot reliably decide what it means to process a row twice.

### 9.1 Distinguish logical records from file rows

A million-row CSV may contain fewer than a million distinct business entities.

Some rows may be repeated.

Others may update earlier values.

The UI should not confuse rows accepted with distinct records inserted.

For example, an importer can successfully accept 999,999 valid rows but finish with 995,000 distinct database records because many rows updated the same keys.

Both counts may be correct.

They answer different questions.

### 9.2 Treat supplier data as untrusted input

Even a long-established integration can produce malformed files.

Schema changes, encoding differences, unexpected delimiters, missing columns, and incorrectly formatted prices are normal operational possibilities.

The application should verify the file's structure and relevant business constraints before allowing its contents to affect authoritative data.

## 10. A File Has a Processing Lifecycle After Upload

SE325-L01 covered file transfer and object storage.

A completed upload only establishes that the bytes arrived and passed the applicable transport-integrity checks.

Bulk processing adds another lifecycle.

The file may be uploaded but not yet validated.

It may be valid but waiting for an available worker.

It may be partially processed.

It may have completed processing but still be awaiting publication.

It may contain rejected rows requiring review.

A useful job state machine might include:

`QUEUED`

`VALIDATING`

`RUNNING`

`PAUSED`

`CANCEL_REQUESTED`

`CANCELLED`

`FAILED`

`PROCESSED`

`PUBLISHED`

The exact names depend on the business workflow.

The important distinction is between preparing records and making those records authoritative for customer-facing behavior.

### 10.1 The job should have an identity

A durable job record should contain a job ID, tenant ID, source-file identity, processing policy version, lifecycle state, checkpoint, counters, and relevant timestamps.

Without a stable job identity, retries may accidentally start independent imports of the same logical operation.

### 10.2 The source should be immutable

Suppose a worker processes the first 400,000 records.

It crashes.

An operator replaces the CSV file at the same storage path with a corrected version.

The worker resumes at row 400,001.

That's potentially disastrous.

The checkpoint belongs to the original file, not the new one.

A safe design binds the job to an immutable object version or verified content digest.

A changed source requires an explicit new operation or carefully designed reconciliation procedure.

## 11. Streaming CSV Correctly

CSV looks simple.

It's text separated by commas.

But a production parser must account for quoted fields, embedded delimiters, line breaks inside quoted values, encoding, empty fields, and malformed records.

### 11.1 Don't split on commas

A description such as `"Room with balcony, city view"` contains a comma that belongs to one field.

A line-oriented split implementation may parse it incorrectly.

Use a proper CSV parser.

### 11.2 Logical records aren't physical lines

CSV supports quoted fields containing line breaks.

Therefore, "record number 412,883" is not necessarily equivalent to physical line 412,884.

That matters for checkpoints and error reporting.

A checkpoint based on raw line numbers can become incorrect if the parser's record boundaries are different.

### 11.3 Validate the schema explicitly

Check the expected columns.

Reject unexpected missing or duplicate headers according to the import contract.

Define whether column order matters.

Decide how to interpret empty strings versus null values.

Do not silently guess date formats or currency units when incorrect interpretation could change business meaning.

### 11.4 Bound individual fields

Even a streaming parser may allocate memory for an individual field.

A malicious or corrupted file could contain one extraordinarily large field.

Configure appropriate parser limits and validate the maximum permissible length of relevant values.

### 11.5 Streaming still has a CPU and I/O cost

Reading a million rows incrementally prevents one giant in-memory list.

But parsing and validating a million rows still consumes computation.

Streaming makes the operation more manageable, not free.

## 12. Choose the Atomicity Contract Before Choosing the Batch Size

There are two very different requirements an import might have.

**Partial publication:** Valid records can become visible as they are committed, even if later rows fail.

**Atomic dataset publication:** Consumers must see either the previous complete dataset or the newly accepted dataset, not a mixture.

These requirements imply different architectures.

### 12.1 Partial publication

A supplier's independent product descriptions may be updated in bounded batches.

If one record fails validation, the others can be applied.

The job reports partial success.

This can be useful when each record is operationally independent.

### 12.2 Atomic publication

Suppose a hotel supplier sends a complete replacement price catalogue.

The existing catalogue should remain authoritative until the new one is ready.

Publishing 30% of the replacement file could create an inconsistent set of prices.

A safer approach is often to ingest into a versioned staging dataset.

The system validates the complete candidate.

Then it atomically changes which version consumers use, or performs another carefully designed publication step.

### 12.3 Batch commits and atomic publication can coexist

The staging dataset may be populated through thousands of small transactions.

The final logical publication can still be atomic.

This is a powerful architectural distinction.

**The size of the processing transaction and the size of the business publication don't have to be the same.**

## 13. Batching: Neither One Row nor One Million Rows

Consider three approaches.

Inserting one record per transaction produces a great deal of transaction overhead.

Inserting one million records in one transaction can create long-running locks, large transaction state, prolonged failure recovery, and substantial database-resource consumption.

Processing bounded batches provides a middle ground.

But the ideal batch size is workload-dependent.

### 13.1 What affects batch size?

Row width.

Index-maintenance cost.

Validation complexity.

Transaction duration.

Network round trips.

Database capacity.

Contention with interactive workloads.

Failure recovery requirements.

### 13.2 A numerical example

Suppose one million rows require processing.

A batch size of one thousand produces one thousand batches.

If each batch takes 200 milliseconds, the database work alone amounts to approximately 200 seconds, before accounting for reading, validation, and coordination overhead.

But if those batches take five seconds under load, the situation changes drastically.

The right batch size cannot be selected from row count alone.

Measure transaction duration and resource impact.

### 13.3 An adaptive strategy

An importer can begin with a conservative batch size.

It can measure transaction latency, error rates, and database pressure.

If the system remains healthy, throughput may be increased.

If interactive latency rises, batch size or worker concurrency can be reduced.

The important objective is maintaining bounded resource consumption rather than maximizing raw import speed at any cost.

## 14. The Atomic Checkpoint Pattern

Now examine the crash window.

Suppose a worker processes rows 100,001 through 101,000.

It commits the changes.

Before updating its checkpoint, it crashes.

The next worker sees the old checkpoint and processes the same batch again.

If that produces duplicate business effects, the job is incorrect.

### 14.1 Commit data and checkpoint together

When processing and checkpoints use the same transactional database, they can be updated in one transaction.

The transaction applies the valid records, records rejected rows, and advances the checkpoint.

Either all these changes commit or none do.

This creates a useful guarantee:

The checkpoint never advances past changes that failed to commit in that transaction.

### 14.2 The scope of that guarantee

The guarantee applies to operations covered by the database transaction.

If processing a row also sends an email or calls a supplier API, those external effects aren't automatically rolled back if the database transaction aborts.

Use appropriate durable intent, outbox, reconciliation, or idempotent effect handling for those boundaries.

### 14.3 Queued work can repeat

A worker may commit a batch and then crash before acknowledging its message.

The queue may redeliver the batch.

The database checkpoint can recognize that the committed work is already complete.

But the queue's delivery semantics and the business idempotency contract must still agree.

The checkpoint is useful because it makes repetition observable and safe within the intended processing model.

## 15. A Row Number Is Not Always a Good Checkpoint

It's tempting to record:

"Last processed row: 412,000."

For a simple immutable CSV that is processed sequentially, this can work.

But it has limitations.

### 15.1 Rescanning can be expensive

A streaming parser restarting at row 412,001 may need to parse the preceding 412,000 records to reach the checkpoint.

This can be acceptable for smaller files.

For enormous files, repeated rescanning adds cost.

### 15.2 Byte offsets require care

An alternative is recording a byte offset.

But CSV record boundaries can span multiple physical lines, and text encoding and buffering affect where it's safe to resume.

A byte offset must correspond to a verified parser boundary.

Arbitrarily seeking into the middle of a quoted field can corrupt parsing.

### 15.3 Chunk identities are another approach

An ingestion pipeline can partition an immutable source into independently identified chunks.

Each chunk has its own identity and processing status.

Workers can resume unfinished chunks.

This supports parallel processing and failure recovery.

But parallelism introduces ordering and conflict questions.

### 15.4 Choose based on the business data

If later rows are allowed to overwrite earlier rows, parallel processing may change the result.

If rows are independent and keyed idempotently, chunk-level parallelism may be simpler.

The business semantics determine the safe scheduling strategy.

## 16. Idempotency: What Does Reprocessing Mean?

Imagine a rate update with the identity:

Tenant Alpha.

Hotel 482.

Room type Deluxe.

Date November 20.

Currency EUR.

The supplier declares the price is 149 euros.

The worker applies the update.

Then it crashes.

On retry, it sees the same logical operation.

A reasonable idempotent behavior is to recognize the business key and avoid creating a duplicate rate.

### 16.1 Upsert is useful but not automatically sufficient

An upsert can insert a new record or update an existing one.

This supports safe replay when the same input has the same intended effect.

But consider an incremental adjustment:

"Increase the price by five euros."

Applying that twice produces a different result from applying it once.

An upsert that simply increments a value isn't idempotent.

### 16.2 Different kinds of duplicate

A CSV may contain two rows for the same business key.

A worker may replay one row after a crash.

Two independent uploads may contain overlapping updates.

These are distinct situations.

The first may be a file-validity question.

The second is an execution-retry question.

The third is a versioning and source-authority question.

Don't solve all three merely by silently overwriting whatever row already exists.

### 16.3 Versions and ordering

Suppose an older supplier feed arrives after a newer one.

If the application blindly applies the late feed, it may overwrite valid prices with stale information.

A robust integration may include source revision numbers, effective dates, or publication generations.

Then it can reject stale updates according to a defined ordering policy.

## 17. Rejection, Quarantine, and Partial Success

Suppose row 412,883 contains an invalid negative price.

A strict importer might abort.

A best-effort importer might skip it.

A more operationally useful design often records a rejection entry.

That entry can identify the import job, logical row, relevant business key, reason code, and safe diagnostic context.

### 17.1 Rejection is not necessarily failure

An import can complete processing while containing rejected rows.

For example:

One million examined.

999,900 accepted.

One hundred rejected.

The job's processing phase has completed.

But whether it should be published depends on the business policy.

### 17.2 Define tolerances

A catalogue importer might permit up to a small proportion of invalid rows.

A financial settlement importer might require zero unexplained rejects.

A price-feed importer might allow isolated errors but reject the file if a critical hotel has no valid pricing left.

The acceptance rule should consider business impact, not merely an arbitrary count.

### 17.3 Don't discard the evidence

A rejected row should have a usable explanation.

The operator needs to distinguish malformed dates, unknown property IDs, price violations, missing required fields, and duplicate-record conflicts.

A generic "Import failed" message provides little operational value.

### 17.4 Don't retain unnecessary sensitive data

Quarantine records may contain customer details or confidential supplier information.

Store only what is needed for diagnosis and correction.

Apply access controls and retention policies.

A diagnostic system can become a data-exposure risk if it indiscriminately stores entire rejected records.

## 18. PostgreSQL `COPY`: Fast Loading Isn't the Whole Workflow

PostgreSQL provides `COPY` for transferring data between files or streams and tables.

It can be much more efficient for bulk loading than issuing enormous numbers of individual insert statements.

### 18.1 Bulk transfer versus business validation

`COPY` solves a database-ingestion problem.

It doesn't automatically solve all the application-level requirements around validation, partial success, tenant authorization, retries, publication, or reconciliation.

### 18.2 Current error-handling options

Modern PostgreSQL supports options such as `ON_ERROR` and `REJECT_LIMIT` for certain input-conversion error handling.

These features can be useful.

But skipping an input-conversion error is not equivalent to implementing an arbitrary business-validation policy.

A row that violates a complex business invariant or references an unknown hotel may need staging validation and explicit rejection reporting.

The exact behavior and options also depend on the PostgreSQL version.

### 18.3 Staging tables

A common pattern is loading raw rows into a staging table.

Then SQL transformations and validation rules produce an accepted dataset and rejection records.

This separates efficient byte transfer from business correctness.

### 18.4 Index and transaction costs remain

Bulk loading can still consume substantial I/O, generate transaction logs, update indexes, and compete with normal workloads.

Fast ingestion isn't resource-free ingestion.

## 19. The Export Problem Is Not Just the Opposite of Import

A large export seems easier.

Read records and write a CSV.

But this creates its own correctness and performance questions.

Which records belong in the export?

At what point in time?

Does the customer expect a consistent snapshot?

Should rows updated during the export contain old or new values?

What happens if an export fails after writing 80% of the output?

### 19.1 Don't load all rows into memory

A naive export executes a query and uses a method that retrieves the entire result set.

Then it constructs a large array and serializes it.

Application memory rises with the size of the export.

Streaming or batched retrieval can reduce that pressure.

### 19.2 Keyset pagination

Instead of repeatedly issuing large `OFFSET` queries, an export can advance through records using a stable ordered key.

For example:

"Give me the next hundred records after ID 842,000."

This avoids the growing cost of skipping many earlier records.

But keyset pagination alone doesn't guarantee a consistent snapshot.

### 19.3 Define export consistency

Suppose a booking is updated after the export starts but before its row is read.

Should the export contain the old value or the new one?

For an operational support export, a best-effort current view may be acceptable.

For a financial audit, the requirement may be much stronger.

The data-consistency contract must be explicit.

## 20. Server-Side Cursors and Long-Lived Snapshots

PostgreSQL supports cursors that allow applications to retrieve portions of a query result at a time.

This can reduce client-memory pressure.

But there are important operational consequences.

### 20.1 A cursor isn't a free stream

The database still executes the query.

Depending on the plan, it may perform expensive sorting or materialization before producing results.

A cursor can limit how much data the client receives at once without eliminating database work.

### 20.2 Transactions can remain open

A normal PostgreSQL cursor generally belongs to a transaction.

Keeping a transaction open for a lengthy export can affect resource usage and interfere with vacuum's ability to clean obsolete row versions.

This is especially relevant on high-write tables.

### 20.3 Held cursors have costs too

PostgreSQL supports holdable cursors that can survive a successful commit.

But their result data may be materialized in temporary storage or memory.

Changing the cursor lifetime changes the resource trade-off.

### 20.4 Read replicas

Some organizations run expensive exports against read replicas.

That can protect primary database capacity.

But it introduces replica lag, consistency, and operational considerations.

An export requiring the latest committed data or strict cross-service consistency may not be adequately served by an asynchronously replicated system.

## 21. A High-Water Mark Is Not a Snapshot

Suppose an export begins with the largest current record ID: one million.

The exporter decides to retrieve all records with IDs up to one million.

This prevents later inserts with higher IDs from appearing.

That's useful.

But consider an existing record with ID 500,000.

It changes while the export is running.

If the exporter hasn't read that row yet, it may see the new value.

The export can therefore contain records observed at different moments.

A high-water mark bounds a key range.

It doesn't automatically preserve an entire historical database view.

### 21.1 Consistent snapshot approaches

A database snapshot or appropriately isolated transaction can provide stronger consistency for a particular database.

But a long-running snapshot may have operational costs.

Another approach is exporting from a versioned, immutable, or precomputed dataset.

The right solution depends on whether the export is a convenience feature or an authoritative financial record.

### 21.2 Cross-service exports are harder

If an export combines booking data from PostgreSQL, payment data from another service, and activity data from an analytical store, a single database snapshot may not establish global consistency.

The application needs a clearly defined data-cutoff or reconciliation contract.

## 22. Export Publication Is Another Transaction Boundary

Imagine writing a large CSV file.

The worker processes 80% of the records.

Then it crashes.

Should users be able to download the partial file?

Usually not if the export is supposed to be complete.

A useful design writes the output to a temporary object or path.

After successful generation and validation, the job marks the output available.

### 22.1 Temporary file then atomic rename

On a local filesystem, writing to a temporary file and renaming it within a suitable filesystem can prevent consumers from seeing a partially written final file.

The exact durability properties depend on the filesystem and flushing behavior.

### 22.2 Object storage

Cloud object storage doesn't generally expose a traditional POSIX rename operation.

The application can upload the completed result under a unique object key and then update an authoritative database record or manifest to publish its availability.

### 22.3 The publication record is authoritative

A client should not assume that a generated object is ready merely because a storage key exists.

The export job should establish whether the content was completely generated and approved for download.

## 23. Cancellation Means Stop at a Safe Boundary

Suppose a user cancels an export.

The worker may currently be reading a database batch, serializing rows, or uploading part of a result.

The cancellation request should be durable.

The worker should observe it and stop at a defined safe point.

### 23.1 Cooperative cancellation

A common design has the control plane set a cancellation-requested status.

The worker checks it between batches.

It finishes or rolls back the current bounded operation.

Then it stops scheduling more work.

### 23.2 Cancellation latency

If one batch takes thirty minutes, checking cancellation only between batches may mean waiting thirty minutes.

Batch size affects both performance and operational responsiveness.

### 23.3 Cancellation and committed effects

For imports that already changed authoritative records, cancellation doesn't erase completed changes.

If all-or-nothing publication is required, staging provides a cleaner way to discard uncommitted candidate datasets.

### 23.4 What about a worker crash?

A cancellation request must survive a worker crash.

The next worker should inspect the durable job state before resuming.

A cancellation flag kept only in the memory of the original process is inadequate.

## 24. Progress Reporting Without Fiction

Progress reporting should distinguish what is known from what is estimated.

For a structured CSV file, the importer may know the total byte count before processing.

It may not know the exact number of logical records without scanning the file.

### 24.1 Bytes processed

Byte progress can be useful for the reading phase.

But it doesn't establish that the same proportion of database work has completed.

Later rows may be more expensive to validate or write.

### 24.2 Rows examined

This can tell an operator how far the parser has advanced.

It should not be labeled "rows imported" if some rows were rejected.

### 24.3 Rows committed

This reflects durable processing progress.

It may differ from the count of distinct database records because of updates and duplicates.

### 24.4 Rejected rows

This count helps the operator understand data quality.

The job can also report rejection categories and a downloadable diagnostic report.

### 24.5 Estimated completion time

Estimated time remaining can be useful, but it is inherently uncertain.

Throughput may change due to database load, variable row costs, or other tenant workloads.

The UI should distinguish measurement from estimation.

### 24.6 The final 100% problem

A progress indicator reaching 100% of input bytes read doesn't mean the job is published.

It may still need to commit a final transaction, reconcile counts, validate the dataset, or publish the result.

Report phase transitions explicitly.

## 25. Multi-Tenant Fairness: Don't Let One Export Own the Database

Return to Mercury.

A major supplier requests a very large export.

Another supplier starts three imports.

At the same time, customers are attempting to book hotels.

All workloads use a shared PostgreSQL cluster.

The background operations may consume significant connections, CPU, I/O, and memory.

### 25.1 Connection pools are finite

Suppose the application has twenty database connections available.

If ten exports each hold a connection for an extended period, only ten remain for other work.

Increasing the pool blindly may overload the database with even more concurrent operations.

### 25.2 Separate resource budgets

A dedicated worker pool can limit the number of simultaneous bulk jobs.

The application can allocate separate database connection pools or concurrency budgets.

The objective is to avoid bulk workloads consuming all resources needed for interactive traffic.

### 25.3 Per-tenant admission control

Without tenant fairness, one customer can submit hundreds of exports and monopolize the system.

A scheduler may limit active jobs per tenant.

It may also apply global limits and queue additional work.

### 25.4 Priority isn't always preemption

Booking requests usually need better latency protection than an export.

But that doesn't necessarily mean terminating every export when interactive traffic increases.

A good system can admit fewer new bulk jobs, reduce concurrency, or slow batch processing.

The details depend on the database workload and available infrastructure.

### 25.5 Measure the real bottleneck

A growing queue doesn't automatically mean the worker count is too low.

The database may already be saturated.

Adding more workers can increase contention and make completion slower.

**More concurrency is not a cure for an overloaded shared dependency.**

## 26. Protect the Database, Not Just Worker Memory

A background job can use very little application memory and still devastate database performance.

Consider an export that scans millions of records with an expensive sort.

The application retrieves results one hundred at a time.

The memory graph looks healthy.

But the database performs a large amount of work to find and order the records.

The interface may stall because the shared database is under heavy load.

### 26.1 Query plans still matter

CS330 and CS350 cover indexing and query-plan analysis.

For bulk jobs, we apply those skills to understand whether a query uses an appropriate access path and whether pagination or sorting creates unnecessary work.

### 26.2 Operational scheduling matters

Even a reasonably efficient query can be too expensive when many copies run simultaneously.

Capacity planning must consider per-job cost and admitted concurrency.

### 26.3 Avoid holding a connection while doing unrelated work

An exporter shouldn't unnecessarily hold a database connection while spending minutes uploading previously fetched data to object storage.

Fetch bounded data, release resources appropriately, and manage output transfer separately where practical.

This requires a clear consistency model, because opening fresh short transactions may observe different database states.

## 27. Backfills: Bulk Jobs Against Existing Production Truth

Now imagine the team adds a new derived field to every reservation.

Perhaps an API currently computes a customer-facing booking category through a complicated query.

To simplify future reads, the team wants to materialize that category.

There are fifty million historical reservations.

This is a backfill.

### 27.1 Backfills are not ordinary migrations

Adding a nullable column may be relatively straightforward.

Populating fifty million rows can be operationally expensive.

The backfill may generate write amplification, transaction logs, index updates, and contention.

### 27.2 Version the computation

Suppose the derived value is calculated using business logic version 1.

Halfway through the backfill, an engineer changes the calculation.

If the job silently resumes with version 2, the final dataset may contain inconsistent interpretations.

Record the transformation version or another suitable processing identity.

### 27.3 Handle concurrent writes

While the backfill runs, new reservations are created and existing reservations change.

A one-time scan may not produce a permanently correct derived field.

The application may need to write the new representation for new changes and reconcile historical records.

### 27.4 Make the operation resumable

Partition the work into stable ranges or chunks.

Record completed chunks.

Use safe update predicates or version checks so reruns don't corrupt newer information.

### 27.5 Avoid unnecessary rewrites

Updating a row that already contains the correct derived value can still create database work.

Make updates conditional where possible.

The goal is to correct the required records, not maximize the number of rows touched.

## 28. The Failure Matrix

A good bulk-processing design should be able to explain what happens at several distinct failure points.

### 28.1 Before a batch begins

No business changes from the batch have occurred.

A retry can begin normally.

### 28.2 During a database transaction

If the transaction fails and rolls back, its changes and checkpoint should not become durable.

The next attempt can retry the batch.

### 28.3 After commit, before acknowledgment

The data and checkpoint are durable.

The queue message may be redelivered.

The worker must recognize the completed work.

### 28.4 During export output generation

A temporary output may be incomplete.

The system must avoid publishing it as a successful result.

### 28.5 After output finalization, before metadata publication

The completed file may exist without an application record marking it available.

Reconciliation should determine whether it can safely publish or clean up the object.

### 28.6 During cancellation

Some previous batches may be committed.

The current batch should reach a safe boundary.

New work should not begin.

The job status must accurately describe the final state.

## 29. A Reference Architecture for Bulk Processing

Let's combine the mechanisms.

The client uploads an immutable source file to object storage.

The backend creates a durable import job referencing that file's identity.

A scheduler admits the job when the appropriate worker and database capacity are available.

The worker streams the file through a parser.

It validates records and processes bounded batches.

Each transaction commits the relevant data changes, rejection records, and checkpoint together where possible.

The job records processing metrics.

If the worker crashes, another worker verifies the source and processing policy, reads the checkpoint, and resumes safely.

When processing finishes, the system evaluates the publication policy.

For an atomic replacement feed, the accepted staging dataset becomes the new authoritative generation.

For a partial-success feed, the system records the final accepted and rejected counts and makes the appropriate result available.

A cleanup process manages temporary files, incomplete jobs, and expired outputs.

This architecture isn't necessarily dozens of microservices.

A small backend, one database, a queue, a worker, and object storage may be sufficient.

The important properties are explicit failure boundaries and resource limits.

## 30. Diagnosing the Opening Incident

Return to the supplier's million-row import.

The worker stopped at row 412,883 because of an invalid price.

The operations team asks whether it can retry.

The first question is not whether the queue library supports retries.

It's whether the import has an immutable source, an established business key, a durable checkpoint, and safe repeated-write semantics.

Next, determine whether partial publication is acceptable.

If the import updates live prices directly, the accepted portion may already be visible.

If it writes into a staging generation, the current production catalogue may remain unchanged.

Then inspect rejection policy.

Should this row be quarantined and processing continue?

Or does the file violate a requirement that prevents publication?

Now investigate the export incident.

Which queries are running?

How many connections are occupied?

Are exports streaming or buffering?

Are they operating with long-lived transactions?

Are tenants subject to concurrency limits?

Is the database itself saturated?

A responsible fix addresses both correctness and operational isolation.

It doesn't merely rerun the import and increase the export timeout.

## 31. What an Experienced Backend Engineer Should Be Able to Do

You don't need to write a new distributed workflow engine to understand bulk processing.

But you should be able to design a job that doesn't lose its place, duplicate irreversible effects, silently discard bad records, or monopolize production resources.

You should understand the trade-offs between staging and direct publication.

You should distinguish bytes read from records committed.

You should recognize that streaming to a client doesn't guarantee a cheap database query.

And you should know that cancellation, failure, and successful completion have different implications for already committed work.

These are common backend responsibilities in companies of almost any meaningful scale.

A senior engineer's judgment appears in the decisions made before the worker starts processing row one.

---

# The Oral Examination

Answer aloud before reading the solutions.

## Question 1 — The Crash Window

An importer commits one thousand rows and crashes before acknowledging the batch.

What must be true for the batch to be safely retried?

## Question 2 — The Wrong Checkpoint Order

A worker writes the checkpoint before committing data.

Then it crashes.

What failure can occur?

## Question 3 — The Invalid Price

A million-row supplier feed contains one negative price.

Should the entire job fail?

What information is necessary to decide?

## Question 4 — Duplicate Business Keys

Two rows refer to the same hotel, room type, and date but have different prices.

Does a database upsert automatically tell us which price should win?

## Question 5 — The Large Export

A developer streams CSV rows from a PostgreSQL cursor.

Application memory remains low, but booking latency explodes.

How is this possible?

## Question 6 — The Snapshot

An export uses keyset pagination with a maximum ID captured at the start.

Can existing records still change while the export runs?

Does the maximum ID guarantee a consistent historical snapshot?

## Question 7 — Cancellation

An operator cancels an import after 300,000 rows were committed.

Does cancellation undo them?

How can staging change the answer?

## Question 8 — Progress Reporting

The parser has read all the input bytes, but database publication hasn't finished.

Should the UI say the import is fully complete?

## Question 9 — The Worker Count

The bulk-job queue grows.

The database is already saturated.

Should the team add twenty more workers?

## Question 10 — The Backfill

A background job computes a new derived field for fifty million rows.

Halfway through, the calculation logic changes.

What must the team consider before resuming?

## Question 11 — The Quarantine

The import has accepted 999,800 records and rejected 200.

What does "completed successfully" mean?

## Question 12 — The Senior Design

Design a resumable supplier-rate importer that can safely process large files while protecting interactive bookings.

Explain data identity, batching, checkpoints, rejection policy, publication, observability, and recovery.

---

# Solutions and Discussion

## Solution 1 — Safe Replay

The job must identify completed work durably and make repeated processing safe.

An atomic database checkpoint and idempotent writes can support this.

External side effects require their own retry and idempotency strategy.

## Solution 2 — Lost Records

The checkpoint may advance even though the data never committed.

A later worker skips the missing work.

Where possible, commit data changes and checkpoint in one transaction.

## Solution 3 — Business Policy

The answer depends on whether partial acceptance is safe.

A catalogue may permit bounded rejects; a financial operation may require stricter handling.

The job should record the rejection and apply an explicit acceptance policy.

## Solution 4 — Conflict Semantics

No.

An upsert defines a database conflict operation, not the correct business precedence.

The source's ordering, revision, and identity rules must determine which update is authoritative.

## Solution 5 — Database Pressure

A streaming cursor still executes database work and may hold a connection or transaction for a long period.

Heavy scans, sorting, I/O, and concurrent exports can degrade interactive queries.

## Solution 6 — High-Water Mark

Yes.

A maximum ID can bound which newly inserted records are included but doesn't freeze values of existing records.

A consistent snapshot requires additional mechanisms and operational trade-offs.

## Solution 7 — Cancellation

Already committed work remains unless the application has a deliberate compensation mechanism.

Staging allows partially prepared data to be discarded before atomic publication.

## Solution 8 — Truthful Progress

No.

Report the completed phase accurately.

Reading all bytes doesn't establish that validation, commits, and publication are complete.

## Solution 9 — Capacity

Not automatically.

Additional workers may increase contention.

Investigate the bottleneck and control admitted background concurrency.

## Solution 10 — Transform Version

A resumed backfill must not silently mix incompatible transformation versions.

The team needs a consistent interpretation, migration or reconciliation plan, and safe handling of concurrent writes.

## Solution 11 — Partial Success

Processing completed, but publication depends on the defined rejection tolerance and business impact.

The status should distinguish accepted records, rejected rows, and final publication.

## Solution 12 — System Design

Use immutable source identity, stable business keys, bounded processing, atomic checkpointing where possible, explicit rejection records, controlled publication, resource budgets, and durable job state.

Verify source identity before resuming and treat downstream side effects separately from database transactions.

---

# The Mental Model Worth Keeping

A bulk job isn't one enormous request.

It's a durable sequence of bounded operations.

The source must remain identifiable.

Every record must have defined business semantics.

Progress must correspond to committed work.

Retries must not create unintended duplicate effects.

Failures must leave enough evidence for recovery.

Exports must distinguish streaming from database cost and snapshot consistency.

Cancellation must stop future work without pretending earlier commits never happened.

And background throughput must never be allowed to consume all the resources needed by interactive customers.

The five questions worth remembering are:

**What exactly is one logical record or operation?**

**Which work is durably committed?**

**What happens if the worker executes it again?**

**What does completion mean to the business?**

**How much production capacity may this job consume?**

---

# Next Lecture — SE325-L03: Scheduled Jobs, Time, and Distributed Execution

We've studied jobs that process large amounts of data.

The next challenge is deciding *when* they run.

Imagine a nightly billing process scheduled for midnight.

The scheduler is down at midnight and recovers at 03:17.

Should the missed job run immediately?

Now imagine two scheduler replicas both believe they own the execution.

Should both send invoices?

And what does midnight mean when a region enters or leaves daylight-saving time?

SE325-L03 will investigate recurring schedules, calendar time, missed runs, duplicate launches, leases, catch-up policies, and idempotent business effects.

*The spoken lecture ends here. The following material is a practical investigation. The laboratory uses an isolated SQLite database and generated CSV file; no cloud account or production database is required.*

---

# Optional Practical Lab — The Import That Crashed After Committing

## Lab Contract

This laboratory demonstrates a checkpointed importer and bounded export.

It uses Python's standard library and SQLite.

No PostgreSQL server, queue broker, Docker installation, or cloud credentials are required.

The example source contains 1,200 records rather than one million, so it can be run quickly on an ordinary computer.

The same correctness issues exist at larger scales.

The fixture deliberately includes:

- One invalid negative price.
- One duplicate business key.
- A worker crash after two committed batches.
- A durable checkpoint.
- Safe repetition of a deterministic database upsert.
- Rejected-row quarantine.
- A cancellation request.
- Tenant-scoped exports.
- A deliberately limited export-consistency guarantee.

The reference implementation assumes one active import worker. Production systems need proper worker ownership or leasing, stricter job-state concurrency, resource budgets, and authentication.

The parser's row-number checkpoint requires rescanning the earlier source records after restart. That is acceptable for this small demonstration, but should not be assumed efficient for very large files.

## Lab 1 — Create the Workspace

Create a directory named `se325-bulk-lab`.

Inside it, save the following script as `studio.py`.

The script generates a dedicated subdirectory named `se325_bulk_lab`.

The `init` command replaces that subdirectory only if it contains the expected laboratory marker.

### The reference implementation

The importer commits each batch's accepted records, rejected-row entries, and checkpoint in one SQLite transaction. It can deliberately terminate the process after commit to reproduce the acknowledgment-loss window.

```python id="bu325py"
import argparse
import csv
import hashlib
import os
import shutil
import sqlite3

from pathlib import Path


ROOT = Path("se325_bulk_lab")
MARKER = ROOT / ".se325-lab"
FILE = ROOT / "rates.csv"
DB = ROOT / "studio.sqlite3"

BATCH_SIZE = 100


def require_lab():
    if not MARKER.is_file():
        raise SystemExit(
            "Run init first; refusing to touch "
            "an unmarked directory"
        )


def file_digest():
    h = hashlib.sha256()

    with FILE.open("rb") as f:
        for part in iter(
            lambda: f.read(65536),
            b"",
        ):
            h.update(part)

    return h.hexdigest()


def connect():
    require_lab()

    conn = sqlite3.connect(
        DB,
        timeout=5,
    )

    conn.row_factory = sqlite3.Row
    return conn


def init():
    if ROOT.exists():
        if not MARKER.is_file():
            raise SystemExit(
                "Refusing to replace "
                "unmarked directory"
            )

        shutil.rmtree(ROOT)

    ROOT.mkdir()

    MARKER.write_text(
        "disposable teaching exercise\n"
    )

    with FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "tenant",
            "external_id",
            "price_cents",
        ])

        for n in range(1, 1201):

            tenant = (
                "alpha" if n <= 900
                else "beta"
            )

            external_id = f"rate-{n:04d}"
            price = 5000 + n

            if n == 417:
                price = -1

            if n == 800:
                external_id = "rate-0100"
                price = 12345

            writer.writerow([
                tenant,
                external_id,
                price,
            ])

    with sqlite3.connect(DB) as conn:

        conn.executescript("""
            CREATE TABLE jobs (
                id TEXT PRIMARY KEY,
                source_sha TEXT NOT NULL,
                next_row INTEGER NOT NULL,
                processed INTEGER NOT NULL,
                accepted INTEGER NOT NULL,
                rejected INTEGER NOT NULL,
                state TEXT NOT NULL
            );

            CREATE TABLE rates (
                tenant TEXT NOT NULL,
                external_id TEXT NOT NULL,
                price_cents INTEGER NOT NULL,
                from_row INTEGER NOT NULL,
                PRIMARY KEY (
                    tenant,
                    external_id
                )
            );

            CREATE TABLE rejections (
                job_id TEXT NOT NULL,
                row_no INTEGER NOT NULL,
                reason TEXT NOT NULL,
                PRIMARY KEY (
                    job_id,
                    row_no
                )
            );
        """)

        conn.execute(
            "INSERT INTO jobs VALUES "
            "(?,?,?,?,?,?,?)",
            (
                "rates-v1",
                file_digest(),
                1,
                0,
                0,
                0,
                "PENDING",
            ),
        )

    print(
        "Created 1,200 records; "
        "row 417 invalid; "
        "row 800 updates an existing key."
    )


def validate(row):
    tenant = row["tenant"]
    external_id = row["external_id"]
    price = int(row["price_cents"])

    if tenant not in ("alpha", "beta"):
        raise ValueError("unknown tenant")

    if (
        not external_id.startswith("rate-")
        or len(external_id) > 32
    ):
        raise ValueError("invalid external ID")

    if not 0 <= price <= 1000000:
        raise ValueError("price out of range")

    return tenant, external_id, price


def process(conn, group):
    good = 0
    bad = 0

    # Changes AND checkpoint commit
    # inside the same DB transaction.
    with conn:

        for n, row in group:

            try:
                tenant, ext, price = validate(row)

            except (
                ValueError,
                KeyError,
                TypeError,
            ) as error:

                conn.execute(
                    "INSERT OR IGNORE INTO "
                    "rejections VALUES (?,?,?)",
                    (
                        "rates-v1",
                        n,
                        str(error)[:120],
                    ),
                )

                bad += 1

            else:

                conn.execute("""
                    INSERT INTO rates
                    VALUES (?,?,?,?)
                    ON CONFLICT(
                        tenant,
                        external_id
                    )
                    DO UPDATE SET
                        price_cents =
                            excluded.price_cents,
                        from_row =
                            excluded.from_row
                """, (
                    tenant,
                    ext,
                    price,
                    n,
                ))

                good += 1

        conn.execute("""
            UPDATE jobs
            SET
                next_row = ?,
                processed = processed + ?,
                accepted = accepted + ?,
                rejected = rejected + ?,
                state =
                    CASE
                        WHEN state = 'CANCEL_REQUESTED'
                        THEN state
                        ELSE 'RUNNING'
                    END
            WHERE id = ?
        """, (
            group[-1][0] + 1,
            len(group),
            good,
            bad,
            "rates-v1",
        ))


def run(
    max_batches=None,
    crash_after=None,
):
    conn = connect()

    job = conn.execute(
        "SELECT * FROM jobs WHERE id=?",
        ("rates-v1",),
    ).fetchone()

    if file_digest() != job["source_sha"]:
        raise SystemExit(
            "Source changed: do not resume "
            "against different bytes"
        )

    if job["state"] in (
        "CANCEL_REQUESTED",
        "CANCELLED",
    ):

        if job["state"] == "CANCEL_REQUESTED":

            with conn:
                conn.execute(
                    "UPDATE jobs SET "
                    "state='CANCELLED' "
                    "WHERE id='rates-v1'"
                )

        raise SystemExit(
            "Job cancelled; no new "
            "batches processed"
        )

    if job["state"] == "COMPLETED":
        print("Already completed")
        return

    groups = 0
    group = []

    with FILE.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as f:

        reader = csv.DictReader(f)

        if reader.fieldnames != [
            "tenant",
            "external_id",
            "price_cents",
        ]:
            raise SystemExit(
                "Unexpected CSV header"
            )

        for n, row in enumerate(
            reader,
            start=1,
        ):

            if n < job["next_row"]:
                continue

            # Cooperative cancellation
            # between batches.
            if not group:

                current = conn.execute(
                    "SELECT state FROM jobs "
                    "WHERE id='rates-v1'"
                ).fetchone()[0]

                if current == "CANCEL_REQUESTED":

                    with conn:
                        conn.execute(
                            "UPDATE jobs SET "
                            "state='CANCELLED' "
                            "WHERE id='rates-v1'"
                        )

                    print(
                        "Cancelled between batches; "
                        "previous commits remain"
                    )

                    return

            group.append((n, row))

            if len(group) >= BATCH_SIZE:

                process(conn, group)
                groups += 1
                group = []

                if crash_after == groups:
                    # Simulate process death
                    # AFTER a committed batch.
                    os._exit(77)

                if (
                    max_batches is not None
                    and groups >= max_batches
                ):

                    with conn:
                        conn.execute(
                            "UPDATE jobs SET "
                            "state='PAUSED' "
                            "WHERE id='rates-v1'"
                        )

                    print(
                        f"Paused after {groups} "
                        "committed batches"
                    )

                    return

        if group:

            process(conn, group)
            groups += 1

            if crash_after == groups:
                os._exit(77)

        with conn:
            conn.execute(
                "UPDATE jobs SET "
                "state='COMPLETED' "
                "WHERE id='rates-v1'"
            )

    print(
        f"Completed: {groups} batches "
        "in this invocation"
    )


def cancel():
    with connect() as conn:

        conn.execute("""
            UPDATE jobs
            SET state='CANCEL_REQUESTED'
            WHERE id='rates-v1'
              AND state NOT IN (
                  'COMPLETED',
                  'CANCELLED'
              )
        """)

    print(
        "Cancellation requested; "
        "already committed data remains"
    )


def status():
    with connect() as conn:

        job = dict(
            conn.execute(
                "SELECT * FROM jobs"
            ).fetchone()
        )

        totals = dict(
            conn.execute("""
                SELECT
                (SELECT COUNT(*) FROM rates)
                    AS distinct_rates,
                (SELECT COUNT(*) FROM rejections)
                    AS quarantine_rows
            """).fetchone()
        )

    print({
        key: job[key]
        for key in (
            "state",
            "next_row",
            "processed",
            "accepted",
            "rejected",
        )
    })

    print(totals)


def export(tenant):
    conn = connect()

    # A high-water mark, NOT
    # a consistent snapshot.
    bound = conn.execute(
        "SELECT COALESCE(MAX(rowid),0) "
        "FROM rates WHERE tenant=?",
        (tenant,),
    ).fetchone()[0]

    output_dir = ROOT / "exports"
    output_dir.mkdir(exist_ok=True)

    temp = output_dir / f"{tenant}.csv.part"
    final = output_dir / f"{tenant}.csv"

    last = 0
    count = 0

    with temp.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "tenant",
            "external_id",
            "price_cents",
        ])

        while True:

            rows = conn.execute("""
                SELECT
                    rowid,
                    tenant,
                    external_id,
                    price_cents
                FROM rates
                WHERE tenant = ?
                  AND rowid > ?
                  AND rowid <= ?
                ORDER BY rowid
                LIMIT 100
            """, (
                tenant,
                last,
                bound,
            )).fetchall()

            if not rows:
                break

            for row in rows:
                writer.writerow((
                    row["tenant"],
                    row["external_id"],
                    row["price_cents"],
                ))

            last = rows[-1]["rowid"]
            count += len(rows)

    os.replace(temp, final)

    print(
        f"Exported {count} rows "
        f"for {tenant} to {final}"
    )

    print(
        "Note: high-water mark avoids "
        "later inserts, not updates "
        "to earlier rows."
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser("init")

    command_run = sub.add_parser("run")

    command_run.add_argument(
        "--max-batches",
        type=int,
    )

    command_run.add_argument(
        "--crash-after",
        type=int,
    )

    sub.add_parser("status")
    sub.add_parser("cancel")

    command_export = sub.add_parser("export")

    command_export.add_argument(
        "tenant",
        choices=["alpha", "beta"],
    )

    args = parser.parse_args()

    if args.command == "init":
        init()

    elif args.command == "run":
        run(
            args.max_batches,
            args.crash_after,
        )

    elif args.command == "status":
        status()

    elif args.command == "cancel":
        cancel()

    else:
        export(args.tenant)
```

## Lab 2 — Inspect the Source

Initialize the fixture.

```bash id="bu325init"
python studio.py init
python studio.py status
```

The generated input contains 1,200 CSV records.

Rows 1 through 900 belong to tenant Alpha.

Rows 901 through 1,200 belong to tenant Beta.

Row 417 contains an invalid negative price.

Row 800 repeats the business key from row 100 but supplies a new price.

### Before processing

Predict the final counts.

How many source records are there?

How many should pass validation?

How many should be rejected?

How many distinct business keys should remain after the duplicate update?

Write down your predictions.

## Lab 3 — The Crash After Commit

The worker will process two batches of one hundred records each.

Then it will terminate deliberately.

Run:

```bash id="bu325crash"
python studio.py run --crash-after 2
```

The process exits with code 77.

That is intentional.

Inspect the state.

```bash id="bu325status"
python studio.py status
```

Expected durable progress:

Two hundred records examined.

Two hundred accepted.

No rejected rows yet.

The next unprocessed row is 201.

### Your task

Explain why the checkpoint survived the worker crash.

Would the same result be guaranteed if the checkpoint were written before the business transaction?

Would the same result be guaranteed if the batch sent external API requests unrelated to the SQLite transaction?

## Lab 4 — Resume Safely

Run:

```bash id="bu325resume"
python studio.py run
python studio.py status
```

The job should finish the remaining work.

The intended final counters are:

- 1,200 records examined.
- 1,199 valid rows accepted.
- One invalid row rejected.
- 1,198 distinct rate records stored.

Why are the accepted and distinct counts different?

Because row 800 updates the existing business key introduced by row 100.

The importer counts the update as a successful accepted row, but it doesn't create a second distinct rate.

### Investigation

Inspect the `rates` table with a SQLite browser or a short Python query.

Verify that tenant Alpha's `rate-0100` contains the later price.

Would this last-write-wins rule be safe for every supplier feed?

What if file rows were processed in parallel?

What if a delayed older import arrived after a newer supplier revision?

## Lab 5 — Quarantine

Inspect the rejected-row table.

The intended rejection is row 417.

It should report that the price is outside the accepted range.

### Questions

Why is a rejection record more useful than silently skipping the row?

Should every invalid price fail the entire import?

What additional business context would be needed to make that decision?

How would you prevent quarantine records from unnecessarily storing sensitive information?

### Acceptance criteria

You can distinguish processing completion from acceptance of the entire imported dataset.

## Lab 6 — Cancellation

Reset the lab.

```bash id="bu325reset"
python studio.py init
```

Process two batches and pause.

```bash id="bu325pause"
python studio.py run --max-batches 2
python studio.py status
```

Request cancellation.

```bash id="bu325cancel"
python studio.py cancel
```

Now attempt to run the worker again.

```bash id="bu325cancelrun"
python studio.py run
python studio.py status
```

The worker should refuse to process more records.

The existing committed records remain in the database.

### Your task

Explain why cancellation isn't equivalent to transaction rollback.

Design a system that would allow cancellation of a large replacement feed without changing the currently published prices.

Hint: consider staging and an explicit publication step.

## Lab 7 — Tenant-Scoped Exports

Reset and complete the import.

```bash id="bu325exportinit"
python studio.py init
python studio.py run
```

Generate separate exports.

```bash id="bu325export"
python studio.py export alpha
python studio.py export beta
```

The expected results are:

Tenant Alpha: 898 distinct data records.

Tenant Beta: 300 distinct data records.

The resulting CSV files include one header row each.

### Investigation

Why does the exporter use a tenant filter on every query?

What would happen if a client could choose an arbitrary tenant identifier without an authorization check?

Does generating a temporary file before renaming it help avoid publishing incomplete outputs?

Does this strategy automatically provide a consistent database snapshot?

### Critical distinction

The simulator uses a high-water mark for row IDs.

It can exclude later insertions with higher IDs.

But it doesn't guarantee that an existing row won't change while the export is running.

A real financial or compliance export may require stronger snapshot semantics.

## Lab 8 — Design a Production Importer

The local simulator demonstrates several correctness properties but omits production infrastructure.

Design the real Mercury importer.

Your plan must address:

**Source identity:** Immutable object key, version, or digest.

**Job identity:** Stable job ID associated with the tenant.

**Worker ownership:** Prevent competing workers from processing the same chunk unsafely.

**Checkpointing:** Atomic commit with business effects when feasible.

**Business keys:** Define deterministic upsert or version precedence.

**Validation:** Separate malformed rows from business-rule violations.

**Quarantine:** Store useful rejection context safely.

**Publication:** Decide partial-success versus atomic replacement.

**Resource control:** Limit concurrent jobs and database work.

**Recovery:** Resume interrupted processing without inventing duplicate effects.

**Cancellation:** Stop future work at a safe boundary.

**Metrics:** Report committed progress and operational impact.

### Interviewer challenge

"Why not simply use PostgreSQL `COPY` and avoid all this complexity?"

Explain what `COPY` solves and what it leaves to application design.

## Lab 9 — The Export That Exhausted the Pool

## Scenario

Mercury's shared database has a connection pool with twenty available connections.

Eight large exports begin.

Each holds a database connection for several minutes while generating output.

Another four exports are queued inside the application.

Interactive booking requests begin waiting for available connections.

The application has low CPU utilization.

The database CPU is only moderately high.

But p99 booking latency rises sharply.

### Your task

Diagnose the likely waiting resource.

Explain why scaling the application CPU may not help.

Determine which measurements you would inspect.

Propose a concurrency budget for bulk exports.

Explain when a separate pool or read replica might be appropriate.

### Additional challenge

The product manager says:

"These are enterprise customers. We can't make them wait."

Propose a business-friendly response that preserves fair access and provides useful progress information.

## Lab 10 — Design a Consistent Export

The finance team requires a report of confirmed booking revenue as of a particular cutoff.

The export takes thirty minutes.

Bookings and refunds continue changing throughout that period.

### Your assignment

Define what "as of the cutoff" means.

Choose an approach that can satisfy the requirement.

Consider:

- A suitable database snapshot.
- A versioned analytical dataset.
- An authoritative event or ledger model.
- Reconciliation with the operational source.

Explain the consistency and operational trade-offs.

### Interviewer challenge

"Can't we just capture the maximum booking ID and export everything below it?"

Explain why that doesn't guarantee the values of existing records remained unchanged.

## Lab 11 — The Fifty-Million-Row Backfill

The booking service introduces a derived field called `booking_category`.

The system needs to populate it for historical reservations.

There are fifty million records.

### Your task

Design the backfill.

It must support:

- Stable chunk identities.
- Bounded transactions.
- Safe restart.
- Concurrent application writes.
- Transformation versioning.
- Minimal unnecessary updates.
- Progress reporting.
- Cancellation.
- Verification and reconciliation.

### Complication

Halfway through the backfill, the business changes the classification logic.

What should happen to already processed records?

Explain why silently resuming with a different implementation can create inconsistent interpretations.

---

# Final Incident — The Million-Row Supplier Feed

## Starting symptom

A supplier uploads a million-row rate file.

The importer processes approximately 412,000 records.

One row fails validation.

The worker stops.

Operations retries the job.

Meanwhile, a customer requests a very large catalogue export.

Several workers and exports compete for a shared database pool.

Interactive booking latency rises dramatically.

### Required incident report

Prepare a concise report addressing the following.

**Business contract:** What is the intended meaning of the supplier feed?

**Source identity:** Which exact file and processing rules were used?

**Durable progress:** Which rows or chunks are confirmed committed?

**Repeated execution:** What happens when completed work runs again?

**Invalid records:** Should they be quarantined, skipped, or block publication?

**Database pressure:** Which bulk workloads consume shared capacity?

**Export semantics:** Does the exported dataset need a consistent snapshot?

**Cancellation:** What happens to already committed changes?

**Containment:** How would you protect interactive booking traffic immediately?

**Recovery:** How would you safely resume or reprocess the import?

**Verification:** What measurements prove the system is healthy again?

### Senior-level challenge

Your interviewer says:

"The importer is too slow, and the export queue keeps growing. Why don't we double the worker count and run bigger SQL batches?"

Explain why increasing concurrency and batch size may improve throughput in some situations but can also amplify contention, transaction duration, and database saturation.

---

# STOP — Independent Investigation Ends Here

Do not read the following diagnostic notes until you've attempted the exercises.

---

# Lab Diagnostic Notes

## Crash Recovery

The simulator commits each batch's database changes and checkpoint together.

The deliberate process crash occurs after a transaction has committed.

On restart, the worker resumes from the next recorded row.

The crash does not require reprocessing the previous committed batch.

The implementation assumes one active worker and a fixed immutable source.

## Accepted Versus Distinct Records

The input contains 1,200 rows.

One row is invalid.

One valid row updates an existing business key.

Therefore, 1,199 rows are accepted but only 1,198 distinct rate records remain.

These counts have different meanings.

## Quarantine

The negative price is rejected and recorded.

The job may continue processing because the local demonstration uses a permissive processing policy.

A production system must define whether rejected rows prevent publication.

## Cancellation

Cancellation prevents additional batches from being processed.

It doesn't undo the earlier committed batches.

A staging-and-publication model can provide cleaner all-or-nothing visibility.

## Exports

The exporter writes bounded batches and publishes a final local file after completion.

It filters by tenant and uses keyset pagination.

But it doesn't maintain one consistent database snapshot across all batches.

This limitation is intentional.

## Database Contention

Bulk jobs can exhaust shared connection capacity or create expensive database work.

Streaming reduces client-memory pressure but doesn't remove query execution costs.

Resource budgets and admission controls are necessary.

## Production Design

A strong production importer binds processing to immutable source identity, validates records, commits progress safely, handles repeated execution, and protects shared resources.

If atomic dataset publication is required, processing should generally be separated from the step that makes the new dataset authoritative.

---

# Further Reading

Primary references:

- **PostgreSQL — COPY:** https://www.postgresql.org/docs/current/sql-copy.html
- **PostgreSQL — DECLARE and Cursors:** https://www.postgresql.org/docs/current/sql-declare.html
- **PostgreSQL — FETCH:** https://www.postgresql.org/docs/current/sql-fetch.html
- **PostgreSQL — Progress Reporting:** https://www.postgresql.org/docs/current/progress-reporting.html
- **PostgreSQL — Transaction Isolation:** https://www.postgresql.org/docs/current/transaction-iso.html
- **PostgreSQL — Routine Vacuuming:** https://www.postgresql.org/docs/current/routine-vacuuming.html
- **Python — CSV Module:** https://docs.python.org/3/library/csv.html
- **Python — SQLite Interface:** https://docs.python.org/3/library/sqlite3.html
- **Amazon S3 — Multipart Upload Overview:** https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html
- **AWS — Builders' Library:** https://aws.amazon.com/builders-library/
- **Google SRE — Handling Overload:** https://sre.google/sre-book/handling-overload/

Related programme chapters:

- SE325-L01 — Files, Uploads, and Object Storage
- SE320-L03 — Queues, Workers, and Asynchronous Workflows
- CS330-L03 — Transactions and Isolation
- CS350-L02 — PostgreSQL Query Plan Forensics
- CS350-L04 — Online Migrations and Database Incident Studio
- CS430-L03 — Scaling and Load Management
- SE325-L03 — Scheduled Jobs, Time, and Distributed Execution
- SE325-L04 — Production Data Repair, Audit, and Lifecycle
- SE325-L06 — API Protection and Multi-Tenant Fairness

---

# Dense Cheatsheet — Interview Glance Card

*This card is fenced so voice readers can skip it during the spoken lecture.*

```text id="se325l02card"
SE325-L02 — BULK IMPORTS, EXPORTS, BACKFILLS
================================================

CORE PROBLEM
------------
A million rows are not one small request.

Large jobs need:
  bounded resource usage
  durable progress
  safe retries
  explicit partial-failure policy
  truthful reporting
  isolation from interactive traffic

SOURCE IDENTITY
---------------
Immutable file/object version
Content digest
Tenant identity
Job identity
Processing policy version

Checkpoint must belong to
the SAME source and rules.

CSV
---
Use real parser, not split(",").
Quoted delimiters and newlines matter.
Logical record != physical line.
Bound individual field sizes.
Validate schema explicitly.

BATCHING
--------
Avoid:
  one-row-per-transaction overhead
  one-million-row transaction

Choose batch size using:
  transaction latency
  index cost
  DB load
  contention
  memory
  recovery granularity

ATOMIC CHECKPOINT
-----------------
BEGIN
  apply accepted records
  record rejected rows
  advance checkpoint
COMMIT

Data and checkpoint together.

External effects require
separate idempotency/recovery.

RETRY
-----
Crash after commit before ack:
  batch may be retried

Use stable business identity.
Repeated work must be safe.

UPSERT
------
Useful for deterministic state setting.

Does not automatically make
incremental side effects idempotent.

LAST-WRITE-WINS
---------------
A business policy, not a universal truth.

Define source ordering,
revision and conflict rules.

REJECTED ROWS
-------------
Quarantine with:
  job identity
  row identity
  reason
  safe diagnostic context

Separate:
  examined
  accepted
  rejected
  distinct resulting records

PUBLICATION
-----------
Partial publish:
  committed records visible incrementally

Atomic dataset publish:
  ingest into staging generation
  validate
  activate one complete version

Batch commit != business publication.

POSTGRESQL COPY
---------------
Efficient bulk data transfer.
Current versions have some
ON_ERROR / REJECT_LIMIT support.

Not a replacement for business
validation and publication policy.

EXPORTS
-------
Avoid fetchall for huge outputs.

Use bounded retrieval/streaming.
Keyset pagination where suitable.
Publish only completed outputs.

STREAMING != CHEAP SQL.

HIGH-WATER MARK
---------------
Bounds key range.
Does NOT freeze existing row values.

CONSISTENCY
-----------
Best-effort export
vs
consistent snapshot
vs
versioned analytical dataset

Choose by business meaning.

POSTGRESQL CURSORS
------------------
Fetch results incrementally.
Can keep transactions open.
Held cursors may materialize data.
Long snapshots have MVCC costs.

CANCELLATION
------------
Durable cancellation request.
Check between safe boundaries.
Already committed work remains.

Cancellation != rollback.

BACKFILLS
---------
Stable chunks.
Transformation version.
Bounded updates.
Concurrent-write strategy.
Resume and reconcile.
Avoid unnecessary rewrites.

PROGRESS
--------
Bytes read
Rows examined
Rows committed
Rows rejected
Distinct affected rows
Dataset published

These are DIFFERENT measurements.

MULTI-TENANT FAIRNESS
---------------------
Global concurrency limit
Per-tenant active-job limit
Background DB pool/budget
Queue admission
Query and transaction monitoring
Optional suitable read replica

More workers can worsen overload.

FAILURE WINDOWS
---------------
Before transaction:
  safe to retry

During transaction:
  rollback expected

After commit / before ack:
  repeated execution possible

During export writing:
  partial artifact

After final output / before publish:
  reconciliation needed

INTERVIEW QUESTIONS
-------------------
What is one logical record?
Which file is this checkpoint for?
What is durably committed?
What if the batch runs twice?
What is the rejection policy?
When is the dataset authoritative?
What does progress measure?
What resources does the job occupy?
How is tenant fairness enforced?
How do we resume safely?

SENIOR MENTAL MODEL
-------------------
Bulk work is a durable sequence
of bounded, retryable operations.

Correctness of the data,
correctness of the checkpoint,
and protection of production
capacity are separate obligations.

NEXT
----
SE325-L03
Scheduled Jobs, Time,
and Distributed Execution
```
