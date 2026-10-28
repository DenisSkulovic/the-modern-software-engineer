---
id: CS340-L02
course: CS340
title: "Inside a Storage Engine"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: CS340-L01
next: CS340-L03
---






# CS340 — Data Systems Beyond Relational Databases

## Lecture 02: Inside a Storage Engine

*Why databases don't simply save records to disk, how write-ahead logging makes crashes survivable, and why B-trees and LSM trees have such different performance personalities.*

---

# 1. The Database That Got Slower While Doing Nothing

It's Thursday afternoon at our hotel-booking company, and a curious production incident is unfolding.

Three months ago, the engineering team introduced a new event-ingestion service.

Every time a customer searches for a hotel, opens a property description, selects a filter, or begins a booking, the frontend generates an event. These events are collected by a backend service and stored for later analytics.

The system was designed to handle several thousand events per second.

And initially, it performed beautifully.

Average write latency remained below ten milliseconds. CPU utilization was modest. The database had plenty of memory, and disk capacity was nowhere near exhausted.

Then the data accumulated.

After several weeks, something strange began happening.

For most of the day, writes remained fast. But every so often, latency increased dramatically. The ninety-ninth percentile climbed from a few milliseconds to several hundred milliseconds. Occasionally, incoming writes stalled almost completely.

The database eventually recovered, only to repeat the pattern later.

You investigate.

There are no long-running analytical queries. No unusual traffic spike coincides with the slowdown. The application hasn't changed its write logic.

And then you notice something even stranger.

During the periods when incoming writes become slow, the database is performing enormous amounts of disk I/O.

Yet the application is not requesting that work.

Where is all this disk activity coming from?

The answer is that the database is reorganizing its own storage.

Its background **compaction** processes are merging previously written data, eliminating obsolete versions, and maintaining the internal structures that allow future queries to remain efficient.

The application writes one logical record.

The storage engine may eventually write information associated with that record several times.

And when the rate of incoming changes exceeds the engine's ability to reorganize existing data, background maintenance can begin interfering with foreground operations.

This isn't a defect in the application.

It is a consequence of the storage engine's design.

But now we have an even more interesting question.

Why would a database deliberately choose an architecture that creates this problem?

Why not simply write each record directly to its permanent position on disk?

To understand that, we need to investigate what a database actually does when your application executes something as innocent as an INSERT, an UPDATE, or a document write.

By the end of this lecture, we'll understand the relationship between memory and persistent storage, the purpose of write-ahead logging, how B-tree and LSM-tree engines organize data, and why durability and performance often pull their designs in different directions.

We're going beneath SQL, beneath MongoDB's document interface, and beneath the reassuring simplicity of a database client library.

We're opening the engine room.

---

# 2. Why Saving Data Is Surprisingly Difficult

Imagine writing a simple Node.js application that stores customer records in a JSON file.

Whenever a customer changes their address, the application reads the file, modifies the relevant object, and writes the updated contents back to disk.

For a small local utility, this might be perfectly reasonable.

But now imagine that the file contains ten million customers.

And hundreds of application requests are updating different customers concurrently.

And the computer might lose power at any moment.

And the system must continue answering queries while writes are happening.

Our simple JSON-file approach suddenly looks less attractive.

## 2.1 The problem of rewriting data

Suppose the database contains one hundred gigabytes of information.

A customer changes their phone number.

The logical change might involve twenty bytes.

Should the database rewrite the entire hundred-gigabyte dataset?

Obviously not.

It needs a way to locate and modify a small part of the stored information efficiently.

But even changing a few bytes is more complicated than it appears.

Storage devices operate through blocks or other access units. Filesystems organize data into structures of their own. Operating systems cache data in memory. Databases often maintain separate caches and write buffers.

Your application sees an object changing.

Underneath, that operation might involve several memory structures, metadata updates, index modifications, log records, and eventual writes to persistent storage.

The database must coordinate these changes without producing inconsistent results.

## 2.2 What if the computer crashes halfway through?

Imagine that creating a reservation requires modifying several records.

The system records the new reservation.

Then it updates availability.

Then it writes the payment state.

What happens if power disappears between those operations?

Without a suitable transactional mechanism, the database may retain only part of the intended change.

Now the reservation exists, but availability wasn't updated.

Or the payment was recorded, but the reservation wasn't.

A storage engine needs techniques for surviving interruptions without leaving its durable structures in an invalid state.

This doesn't mean the storage engine alone implements every high-level transaction guarantee. A complete database system includes concurrency control, transaction management, and other components.

But the storage engine must provide the physical foundations that make those guarantees possible.

## 2.3 Durability and speed seem to disagree

There is a fundamental tension.

Memory is fast, but ordinary volatile memory loses its contents when power disappears.

Persistent storage survives restarts, but accessing it costs time and I/O capacity.

If every tiny database change requires immediately rewriting several persistent data structures, writes may become expensive.

If changes remain only in memory, the database may lose acknowledged work during a crash.

Modern storage engines solve this tension by carefully separating three things:

**The logical change requested by the application.**

**The representation currently being used in memory.**

**The persistent information required to reconstruct a correct database after failure.**

That separation is the foundation of everything we're about to explore.

---

# 3. Pages: The Database Doesn't Think in Individual Objects

Let's begin with physical organization.

Suppose PostgreSQL stores a table containing millions of hotel reservations.

At the SQL level, the table consists of rows.

But the storage engine doesn't typically manage each row as a completely independent file.

Instead, PostgreSQL organizes table and index storage into fixed-size **pages**.

A standard PostgreSQL installation commonly uses eight-kilobyte pages.

Other databases and storage engines may use different page or block sizes.

Why organize storage this way?

Because managing millions of tiny independent storage operations would create enormous overhead.

Pages provide a manageable unit for storage, caching, modification, and I/O.

## 3.1 What lives inside a page?

Imagine one database page containing several reservation records.

The page needs more than the raw field values.

It also contains metadata describing its internal layout, information about where records are located, and free space available for changes.

PostgreSQL heap pages, for example, contain a page header and item identifiers that locate individual tuples within the page.

A row's physical location can be represented using a page identifier together with an item position.

This explains why an index entry doesn't necessarily contain the complete record.

It may identify where the database should find the corresponding row.

Now imagine updating a reservation.

The operation may affect a page already loaded into memory.

The database can modify its in-memory representation and mark the page as changed.

Such a page is commonly called a **dirty page**.

The word dirty doesn't imply corruption.

It simply means the in-memory version contains changes not yet reflected in the corresponding persistent data page.

## 3.2 Why page size matters

Page size creates trade-offs.

Larger pages may allow more data to be retrieved in one storage operation and can reduce some metadata overhead.

But they may also increase the amount of data moved when only a small portion is needed.

Smaller pages can make individual reads and writes more granular, but potentially increase metadata and tree-navigation overhead.

The best choice depends on workload, storage hardware, record sizes, caching behavior, and implementation details.

Most application engineers will never need to configure a custom page size.

Still, understanding pages changes how you think about databases.

A query asking for one row might cause an entire page to be read.

An update touching one logical field might mark a containing page dirty.

And a collection of randomly distributed records can generate considerably more storage activity than a similarly sized collection of sequentially organized records.

This is our first glimpse of **locality**.

Where data lives relative to other data can matter almost as much as how much data exists.

---

# 4. The Buffer Pool: Why Databases Love Memory

Our PostgreSQL server has a large amount of RAM.

How does it use that memory to improve performance?

One important mechanism is the **buffer pool**, or buffer cache.

The database maintains in-memory copies of frequently accessed pages.

Imagine a customer repeatedly opening the same popular hotel's availability information.

If the relevant pages are already in memory, the database may avoid reading them from persistent storage again.

That can make subsequent operations much faster.

But memory is finite.

The database needs policies for deciding which pages to retain and which to evict when space becomes scarce.

## 4.1 Cache hits and misses

Suppose a query needs a particular index page.

If that page is in the database's buffer pool, the engine can access it directly.

That's a cache hit.

If it isn't there, the system must obtain it from a lower storage layer.

That's a cache miss.

The cost difference can be substantial.

However, operating systems also maintain filesystem caches.

A database's cache miss doesn't necessarily imply that the hardware storage device must perform a physical read. The required data might still be available in the operating system's page cache.

Some database engines deliberately manage much of their own caching.

Others rely more heavily on the operating system.

MongoDB's WiredTiger engine, for example, uses an internal cache alongside the filesystem cache.

These details matter when interpreting memory metrics.

An application can consume significant memory without leaking it.

A database can intentionally retain pages in RAM because doing so improves performance.

## 4.2 The hot working set

Imagine that our database occupies two terabytes on disk.

But ninety percent of application requests access information contained within a relatively small collection of popular hotels and recent reservations.

That frequently accessed portion is the **hot working set**.

If the relevant pages fit comfortably in memory, the database may perform very well despite having far more total data than RAM.

Now imagine the product team introduces an endpoint that scans old reservation history randomly.

The workload begins pulling many additional pages into memory.

Those pages may displace more useful frequently accessed data.

The original customer-facing queries become slower because their pages no longer remain cached as reliably.

Nothing is wrong with the SQL syntax.

The application has changed the memory-access pattern of the database.

This is why understanding working sets is more useful than simply comparing database size against available RAM.

## 4.3 Dirty pages introduce a new problem

Suppose a customer updates a reservation.

The database changes a page in memory.

The page is now dirty.

When should the database write it to persistent storage?

If it immediately synchronizes every dirty page, small transactions may generate excessive random storage activity.

If it waits, a crash could destroy the in-memory change.

The engine needs a way to provide durability without rewriting all affected data pages at every commit.

And that leads to one of the most important mechanisms in database engineering.

The write-ahead log.

---

# 5. Write-Ahead Logging: Save the Promise Before Rebuilding the World

Imagine a hotel reservation transaction modifies several data pages.

One page contains the reservation record.

Another contains inventory information.

A third contains an index entry.

We want the transaction to become durable without forcing every modified page to be rewritten immediately.

The essential idea behind **write-ahead logging**, or WAL, is to record enough information about changes in a persistent log before allowing the corresponding data-page modifications to become durable.

The log provides a recoverable history of changes.

If the database crashes before all the data pages are written, it can use that log to reconstruct the necessary state.

## 5.1 Why a log is easier to write

Imagine that one transaction modifies pages scattered across a large database.

Without a logging mechanism, committing the transaction might require writing several separate locations on persistent storage.

That can involve expensive I/O.

A write-ahead log is generally organized for append-oriented writing.

Instead of immediately synchronizing many scattered data pages, the database can append records describing the necessary changes and flush the relevant log information.

Sequential or append-oriented I/O is often easier to coordinate efficiently than many small independent updates.

The exact performance difference depends on hardware and implementation, but the architecture creates a useful opportunity for batching and reduced commit overhead.

## 5.2 The order is everything

Let's imagine a transaction that updates a reservation.

The database modifies the relevant in-memory structures and generates corresponding WAL records.

Before the transaction can be acknowledged as durably committed under the chosen durability settings, the necessary log information must reach an appropriate persistent state.

The database doesn't necessarily have to write every dirty data page to its final on-disk location at that moment.

Instead, it can rely on the durable log for recovery.

This means a transaction may commit successfully while some corresponding data pages remain dirty in RAM.

That sounds dangerous until you understand the recovery mechanism.

If the server crashes, the database can reconstruct changes from the persistent log.

The log is effectively the evidence needed to restore the database's durable state.

The crucial rule is:

**Before a modified data page is allowed to reach durable storage, the log records required to recover that modification must already be durable.**

This is the write-ahead ordering requirement.

It protects the database against reaching an unrecoverable condition where persistent data pages contain changes that the recovery system cannot reconstruct consistently.

## 5.3 What does flushing actually mean?

Here's a subtle but extremely important distinction.

Writing bytes through an operating-system interface does not necessarily mean those bytes have reached durable storage.

The operating system may hold them in memory.

Storage devices may also maintain their own caches.

A database can request that data be synchronized using mechanisms such as `fsync` or related platform-specific operations.

But the ultimate guarantee depends on the operating system, storage stack, device behavior, and correct configuration.

If the storage hardware falsely reports that data is persistent, software cannot magically compensate for every such failure.

This is why database durability is not merely a property of an INSERT statement.

It is a contract spanning application configuration, database software, operating system, and storage infrastructure.

## 5.4 Group commit

Imagine one hundred transactions completing at almost the same moment.

Should the database perform one expensive log synchronization for every transaction independently?

Not necessarily.

A technique called **group commit** allows multiple transactions to share some of the synchronization cost.

The database can flush enough WAL to cover several transactions together.

Each transaction still needs its required commit information to be durably represented before receiving the acknowledgment promised by its durability policy.

But the physical synchronization work can be amortized.

This is one reason a database can process many small transactions efficiently without immediately rewriting every modified data page.

The database is exploiting the difference between logical operations and physical storage operations.

And it's doing so without necessarily sacrificing its promised durability semantics.

---

# 6. Checkpoints: Why the Database Cannot Live in Its Log Forever

If the write-ahead log is so useful, why not keep writing to it forever?

Because the log isn't intended to replace every other storage structure.

The database still needs its normal data files, indexes, and recoverable persistent layout.

Imagine that our server runs for a year, recording every modification in an ever-growing log.

Then it crashes.

Would recovery need to replay an entire year of changes?

That would be rather inconvenient.

Databases therefore use **checkpoints** or related persistence milestones.

A checkpoint establishes that a sufficiently consistent portion of the database's state has been reflected in persistent data structures, allowing recovery to begin from a more recent position.

## 6.1 Checkpoints are not ordinary commits

This distinction is fundamental.

A transaction commit establishes its promised transactional outcome under the selected configuration.

A checkpoint advances the persistent storage state used for recovery.

Those events need not happen together.

A database may acknowledge thousands of durable commits between two checkpoints.

If a crash occurs, recovery can use the most recent suitable checkpoint and subsequent WAL information to reconstruct the required state.

The fact that a transaction's data pages weren't all flushed at the moment of commit does not, by itself, imply that the committed transaction will be lost.

## 6.2 The cost of checkpointing

Checkpoints perform real work.

Dirty pages must eventually be written.

Depending on the database and configuration, checkpoint activity can produce substantial storage I/O.

If that I/O competes with foreground queries and transactions, latency may increase.

A system that checkpoints too frequently may waste resources repeatedly writing data or generate additional logging overhead.

A system that checkpoints too infrequently may accumulate more recovery work and require greater log retention.

The database therefore needs to balance normal performance, storage consumption, and recovery time.

PostgreSQL, for example, spreads checkpoint writes across time to reduce sudden I/O spikes.

The precise implementation is more sophisticated than one giant periodic disk flush.

But the underlying trade-off is easy to understand.

**Work deferred from the transaction's critical path doesn't disappear. The database must perform it somewhere else.**

That principle will return when we investigate LSM-tree compaction.

---

# 7. Crash Recovery: Reconstructing a Transaction That Wasn't Fully Written

Let's stage a failure.

Our booking service creates a reservation.

The database records the necessary transaction information and acknowledges success.

Some changed pages are still dirty in memory.

Two seconds later, the database server loses power.

The memory contents disappear.

When the machine restarts, the database's ordinary data files may not yet contain every modification associated with the acknowledged transaction.

How can the database recover?

## 7.1 Replaying the log

The recovery process identifies a suitable checkpoint and examines subsequent log records.

Those records contain information needed to reconstruct relevant changes that may not have been fully reflected in the data files.

The database applies the required recovery actions and restores its persistent structures to a valid state.

In PostgreSQL, this process uses WAL-based redo recovery together with the database's transactional and multiversion visibility mechanisms.

Not every system performs identical recovery steps. Some storage engines use explicit undo records as well as redo records. Others rely on copy-on-write structures or different persistence strategies.

The principle is broader than one implementation.

A database preserves enough durable information to restore consistency after incomplete physical writes.

## 7.2 What about uncommitted changes?

Imagine that another transaction was halfway through when power disappeared.

Its changes should not suddenly become a successful business operation merely because some log records reached storage.

The database must distinguish committed work from incomplete work and restore the appropriate transaction state.

Different storage engines and transaction managers achieve this through different combinations of logging, visibility rules, rollback mechanisms, and recovery metadata.

This is why WAL and transactions are related but not identical concepts.

The WAL contributes to recoverability and durability.

The transaction system decides which logical operations are committed and visible according to its rules.

## 7.3 The torn-page problem

There's another unpleasant failure mode.

Imagine that the database is rewriting an eight-kilobyte page when power disappears.

The storage system may have persisted only part of the new page.

The page now contains an inconsistent mixture of old and new information.

This is called a **torn write**.

PostgreSQL's full-page-write mechanism can protect against relevant torn-page failures by recording an appropriate complete page image in WAL when required, notably for the first modification after a checkpoint.

During recovery, that information can help restore a consistent page.

But this mechanism has costs.

Full-page images increase WAL volume.

That means checkpoint frequency, logging volume, and storage performance are interconnected.

Once again, durability isn't free.

The database pays for it through carefully designed physical operations.

---

# 8. B-Trees: Keeping Data Searchable While It Changes

Now let's investigate how databases organize data for efficient access.

Imagine a table containing fifty million reservations.

You want to retrieve one reservation by ID.

Scanning every record would be absurdly expensive.

We need an index.

One of the most important index structures in database systems is the **B-tree** family.

B-trees are balanced search trees designed to work efficiently with storage pages.

Their descendants and variations are widely used in relational and non-relational storage engines.

## 8.1 Why not use a binary search tree?

In an ordinary binary search tree, each node may have at most two children.

That can be useful in memory, but imagine storing such a tree on disk.

Following many pointers could require many small storage reads.

Persistent storage access is expensive relative to simple CPU comparisons.

A B-tree addresses this problem by allowing each node to contain many keys and references to many children.

A single page can guide the search toward one of many possible subtrees.

This gives the tree a high branching factor.

## 8.2 A three-level index can cover enormous datasets

Imagine an index page containing hundreds of separator keys and child references.

The root page points toward hundreds of lower pages.

Each of those pages points toward hundreds more.

And the leaves contain large numbers of actual indexed entries.

Even a relatively shallow tree can organize millions of keys.

To find one reservation, the database begins at the root, follows the relevant child page, and continues until reaching the appropriate leaf.

Instead of examining millions of records, it performs a small number of page-level navigation steps.

The exact number depends on key sizes, page occupancy, tree implementation, and data volume.

But the important intuition is that the tree stays shallow because each page organizes many possible keys.

## 8.3 B-trees and B+ trees

You'll often encounter the term **B+ tree**.

In a B+ tree, internal nodes primarily direct searches, while the leaf level contains the actual indexed entries or relevant record references.

Many database indexes use B+ tree-like designs, often with additional implementation-specific structures.

PostgreSQL's B-tree indexes, for example, use pages organized into a balanced index structure with sibling links and other mechanisms supporting navigation and concurrency.

The exact implementation is more sophisticated than a textbook B+ tree diagram.

For our purposes, the central property is that keys remain organized in searchable order.

This supports both point lookups and ordered range scans.

## 8.4 Why range queries are so natural

Suppose you want reservations created between two timestamps.

An ordered tree index can locate the beginning of the range, then move through relevant leaf entries in key order.

This is more efficient than scanning every reservation when the range is selective and the index suits the query.

It also helps explain why the order of columns in a composite index matters.

An index ordered first by hotel ID and then by reservation date groups keys differently from one ordered first by date and then by hotel ID.

The structure defines which ranges are adjacent.

SQL query optimization is therefore deeply connected to physical ordering.

But B-trees also need to handle writes.

And that is where their costs become interesting.

---

# 9. What Happens When a B-Tree Changes?

Suppose the database inserts a new reservation.

Its index key belongs somewhere in the existing ordered structure.

The engine locates the appropriate leaf page and inserts the entry.

If the page has sufficient free space, the update may be relatively straightforward.

But what if the page is full?

The tree must make room while preserving its ordering and balance invariants.

This can involve splitting a page and updating parent-level information.

Such operations require appropriate concurrency and recovery machinery.

## 9.1 Why writes can affect several pages

One logical INSERT might modify the table's data storage and several indexes.

Each index needs to reflect the new record.

An UPDATE might also require index changes, depending on which fields changed and the database's implementation.

In PostgreSQL, for instance, heap tuples and index entries are maintained through an MVCC-aware storage model, with optimizations such as HOT updates possible under suitable conditions.

The details are complex, but one principle is already visible.

The cost of a write is not determined solely by the number of bytes in the new record.

It also depends on which physical structures must be maintained.

More indexes may make reads faster.

They also increase write work, storage usage, and maintenance obligations.

This is why adding an index isn't a free performance improvement.

## 9.2 Random versus sequential access

Imagine inserting records with randomly distributed index keys.

The affected leaf pages may be scattered across the stored index.

The buffer pool can absorb much of this activity when relevant pages remain in memory.

But if the working set exceeds memory capacity, the engine may need to fetch and eventually write many different pages.

That creates a different I/O pattern from appending large quantities of information sequentially.

On modern SSDs, random access is much less punishing than it was on spinning disks.

But it still has costs involving I/O operations, device queues, cache locality, write endurance, and throughput limits.

Hardware changes the magnitude of the trade-off.

It doesn't erase the trade-off.

## 9.3 B-trees are excellent, but not free

B-tree-family storage is well suited to many mixed read/write workloads.

It provides efficient point lookups and ordered ranges.

It can update relevant pages without rewriting the entire dataset.

And mature database systems have spent decades optimizing tree concurrency, caching, page layout, and recovery.

But maintaining sorted, mutable page structures imposes work during inserts, updates, page splits, and maintenance.

What if we adopted a radically different philosophy?

What if we stopped trying to place every write directly into an existing persistent ordered structure?

That leads us to the Log-Structured Merge Tree.

---

# 10. LSM Trees: Make Writing Easy, Reorganize Later

Imagine designing a storage engine for extremely heavy write traffic.

Our event-ingestion service receives thousands of small updates every second.

Rather than immediately modifying many scattered persistent tree pages, we want to accumulate changes efficiently and organize them into large sorted files.

This is the central idea behind **Log-Structured Merge Tree**, commonly abbreviated LSM tree.

The architecture separates accepting new changes from the more expensive work of consolidating stored data.

## 10.1 First stop: the memtable

When the application writes a key-value pair, the storage engine records the change in an in-memory structure called the **memtable**.

The memtable is commonly maintained in an order that supports efficient lookup and eventual sorted output.

RocksDB's default memtable implementation uses a skip list, although other implementations are available.

The application does not need to wait for the entire persistent dataset to be rearranged on every write.

The new information enters the in-memory write structure.

But memory alone isn't durable.

So LSM-based engines often use a write-ahead log as well.

The memtable provides a fast working representation.

The WAL provides recoverable information under the engine's selected durability policy.

The precise acknowledgment guarantees depend on configuration. In RocksDB, for example, WAL logging and synchronization behavior can be controlled, so a successful write isn't automatically equivalent to a power-loss-durable write under every setting.

This is the same fundamental distinction we examined earlier.

Accepting a write, logging it, synchronizing it, and organizing it into final data files are different events.

## 10.2 The memtable becomes immutable

Eventually, the memtable reaches a configured size.

Instead of continuing to modify it, the engine marks it immutable and begins using a new memtable for incoming writes.

The old memtable can then be written to persistent storage as a sorted file.

In LSM terminology, these files are often called **SSTables**, or Sorted String Tables.

Despite the name, they are not ordinary SQL tables.

They are immutable files containing sorted key-value information and supporting metadata.

RocksDB uses SST files as a central part of its persistent storage architecture.

## 10.3 Why immutable files are attractive

Once an SST file is written, the engine generally doesn't modify it in place.

New changes go into newer structures.

This has several advantages.

Large sequential writes can be efficient.

Immutable files can be easier to reason about during background processing.

Readers can use existing files while new files are being generated.

And the engine can merge sorted files into new sorted files without requiring every individual update to rewrite the same persistent pages immediately.

But this design creates a problem.

If we never modify old files, what happens when the same key is updated repeatedly?

We may have several versions of that key spread across different files.

And if we continue flushing memtables, the number of files grows.

Eventually, reads become more expensive.

The solution is compaction.

---

# 11. Reading From an LSM Tree: Which Version Is the Real One?

Suppose our event database stores a key representing a customer's latest search session.

The key has been updated several times.

A newer value may exist in the current memtable.

An older version may exist in a recently flushed SST file.

An even older version may exist in a deeper storage level.

When the application reads the key, the engine must identify the correct visible version.

It cannot simply open one arbitrary file and return the first matching value.

The search must account for the ordering and freshness of the stored structures.

## 11.1 The read path

A typical LSM-based read path may examine the active memtable first.

If the key isn't found there, it may inspect immutable memtables awaiting flush.

Then it searches relevant SST files.

The engine uses metadata describing file key ranges and other indexing structures to avoid unnecessary work.

Some implementations organize files into several levels.

The rules governing overlap and search order depend on the compaction strategy.

But the central challenge remains:

**A logical key may have information distributed across several physical structures.**

The storage engine must interpret them consistently.

## 11.2 Bloom filters: Avoiding pointless disk reads

Imagine trying to find a key inside an SST file.

We would like to know whether the file might contain it before performing more expensive lookup work.

A **Bloom filter** provides a compact probabilistic membership test.

It can tell us that a key is definitely absent from a particular represented set, assuming correct construction and operation.

Or it can tell us that the key might be present.

That second answer is not a guarantee.

Bloom filters can produce false positives.

They should not produce false negatives under their intended operating assumptions.

This asymmetry is useful.

If the filter says the key is absent, the engine can skip the corresponding lookup.

If the filter says the key might exist, the engine performs the necessary additional work.

Why tolerate false positives?

Because the filter consumes relatively little memory and can eliminate many unnecessary storage accesses.

It's an elegant trade-off between memory and I/O.

The filter doesn't need perfect knowledge.

It only needs to avoid enough expensive misses to be worthwhile.

## 11.3 Negative lookups can be unexpectedly costly

Now imagine a workload dominated by requests for nonexistent keys.

Without suitable filters and indexing, the engine may need to inspect several structures before establishing that the key is absent.

That can be more expensive than finding a key in a recent memtable.

This is one reason storage-engine performance depends on the distribution of read operations.

A benchmark testing only successful point lookups may not reveal the cost of missing-key queries.

And a workload dominated by range scans has different characteristics again.

The storage engine's data structures must serve all these patterns while maintaining acceptable write behavior.

That is not an easy balancing act.

---

# 12. Compaction: The Background Work That Eventually Comes Due

Our LSM database has been accepting writes efficiently.

Memtables fill and become sorted files.

Newer and older files accumulate.

Some keys have multiple versions.

Some keys have been deleted.

Eventually, the engine needs to consolidate this information.

That process is called **compaction**.

## 12.1 What compaction actually does

Imagine two sorted files.

One contains keys A through M.

Another contains overlapping keys H through Z.

Compaction can read relevant files, merge their sorted entries, resolve obsolete versions where safe, and produce new sorted files.

The result may contain fewer files and less redundant data.

The engine can then retire old files when they are no longer needed by readers, snapshots, or other mechanisms.

Compaction improves future access efficiency and reclaims storage occupied by obsolete information.

But look carefully at what just happened.

The application did not request a new write of those surviving records.

The storage engine rewrote them because its physical organization needed maintenance.

This is the origin of **write amplification**.

## 12.2 Write amplification

Imagine an application writes one gigabyte of logical updates.

The storage engine eventually writes several gigabytes to persistent storage while logging, flushing, compacting, and reorganizing that information.

The ratio between physical storage writes and logical application writes is one way to measure write amplification.

Different systems define and measure this ratio at different levels, so comparisons require care.

But the general concept is straightforward.

**One logical write can cause multiple physical writes.**

LSM trees intentionally defer and reorganize work to make foreground writes efficient.

The price is additional background I/O.

B-tree systems also experience write amplification, through logging, page modification, index maintenance, and other mechanisms.

The difference is how the systems organize and distribute that work.

## 12.3 Read amplification

Now consider reads.

A logical key lookup might require examining several structures or files.

If the engine performs multiple physical operations to answer one logical request, we can describe that overhead as read amplification.

An LSM engine can reduce this through Bloom filters, caches, file-level metadata, and compaction strategies.

A B-tree lookup may traverse several pages and fetch a separate data page.

Neither architecture has zero overhead.

Both are optimizing the physical work required to answer logical requests.

## 12.4 Space amplification

There's a third dimension.

How much physical storage does the database require relative to the live logical information?

An LSM engine may temporarily retain overlapping file versions during compaction.

Old versions may remain necessary for snapshots or readers.

Deleted data may not disappear from disk immediately.

B-tree systems can also retain obsolete information or unused space and require maintenance.

The result is **space amplification**.

Now we have three useful dimensions:

Read amplification.

Write amplification.

Space amplification.

Improving one can make another worse.

For example, a compaction strategy that minimizes the number of overlapping files searched during reads may perform more rewriting.

A strategy that reduces rewriting may retain more overlapping files or consume more temporary space.

The physical architecture is a set of trade-offs, not a universal optimization.

---

# 13. The Compaction Debt That Caused Our Incident

We're finally ready to solve the mysterious performance problem from the beginning.

Our event-ingestion service uses an LSM-based storage engine.

Incoming writes first enter memory-backed structures and their corresponding logging path.

Memtables are periodically flushed into immutable sorted files.

Background compaction processes reorganize those files.

For weeks, this works beautifully.

Then the sustained write workload grows.

## 13.1 Writes arrive faster than cleanup can finish

Imagine that incoming data arrives at a rate requiring substantial background merging.

Initially, the compaction workers keep up.

The engine flushes new files and gradually merges them into the appropriate levels.

But as the dataset grows, compaction has more work to perform.

The actual cost depends on the compaction strategy, key distribution, update patterns, storage bandwidth, and other configuration choices.

At some point, the system's sustained incoming write rate exceeds the rate at which it can flush and compact data while maintaining its storage invariants.

New sorted files accumulate faster than the engine can reorganize them.

The database has developed **compaction debt**.

## 13.2 Why the engine starts slowing application writes

An engine cannot allow the backlog to grow without limit.

It has finite memory and storage resources.

It may therefore deliberately slow or stall incoming writes when thresholds are reached.

RocksDB, for example, has mechanisms for slowing or stopping writes when certain conditions indicate that its background storage pipeline cannot keep up.

This is not necessarily a bug.

It is a form of backpressure.

The engine is preventing unchecked foreground work from overwhelming its internal storage organization.

From the application's perspective, however, write latency suddenly becomes terrible.

The API may time out.

Queues begin accumulating pending events.

And if the ingestion pipeline doesn't handle backpressure correctly, memory usage can grow elsewhere in the application architecture.

One storage-engine bottleneck can propagate through the entire system.

## 13.3 What would we measure?

A good investigation begins by distinguishing foreground request volume from background storage activity.

We inspect write latency over time and compare it with compaction activity.

We examine SST file counts, level sizes, compaction backlog, write-stall counters, and storage throughput where the engine exposes them.

We check whether flush and compaction workers are keeping up with incoming writes.

We examine free disk space, storage IOPS, throughput limits, CPU utilization, and the effect of concurrent reads.

We also consider whether particular key patterns create hotspots or unusual update behavior.

The objective is to establish whether write latency rises when the engine accumulates or processes internal maintenance work.

If that relationship is reproducible, compaction pressure becomes a credible explanation rather than a guess.

## 13.4 What should we change?

There is no universal setting that magically eliminates compaction costs.

Possible interventions include adjusting write-buffer sizes, compaction concurrency, level configuration, storage capacity, and workload patterns.

Some systems may benefit from faster storage or more appropriate resource allocation.

Others may need reduced ingestion concurrency, better batching, retention policies, or changes to key design.

The correct intervention depends on the actual bottleneck.

Adding memory may help absorb bursts, but if sustained incoming data exceeds the storage engine's long-term compaction capacity, larger buffers merely postpone the problem.

Similarly, adding CPU may accomplish little if persistent storage bandwidth is saturated.

The important distinction is between **burst capacity** and **sustainable throughput**.

A system might accept one million writes very quickly while accumulating enormous maintenance work.

That doesn't prove it can sustain the same write rate forever.

This is why serious benchmarks must run long enough to expose background maintenance costs.

A database can be extraordinarily fast for the first minute and much slower after an hour.

Both measurements may be correct.

Only one describes the sustained workload.

---

# 14. B-Trees Versus LSM Trees: Which One Should We Choose?

Now we can compare the architectures more intelligently.

A B-tree-oriented system maintains searchable page structures that can be updated as data changes.

An LSM-oriented system emphasizes accepting changes into memory and immutable sorted files, then consolidating those files through background compaction.

Both can provide efficient lookups.

Both can be durable.

Both can use write-ahead logging, caching, compression, and sophisticated concurrency control.

The difference isn't simply that one is old and the other is new.

It's how they organize persistent information and distribute physical work over time.

## 14.1 Consider the workload, not the acronym

Suppose we have a transactional application performing frequent point lookups, moderate updates, and range queries over indexed fields.

A mature B-tree-based architecture may perform very well.

Now suppose we have a high-volume event ingestion workload with large quantities of writes and relatively predictable read patterns.

An LSM-based design may offer advantages by organizing writes into append-oriented and immutable-file operations.

But suppose that same LSM workload requires frequent scans across broad key ranges or a very high proportion of missing-key lookups.

The engine's file organization, filters, compaction, and caching become increasingly important.

Neither design guarantees superior performance in every environment.

## 14.2 Modern SSDs changed the economics

Historically, avoiding random disk access was extremely important because spinning disks incurred mechanical seek costs.

SSDs dramatically reduced random-access latency.

But random access still consumes device operations and can interact with caching, queue depth, write endurance, and throughput constraints.

Sequential and batched I/O can remain advantageous.

At the same time, modern B-tree engines have become highly optimized for SSD workloads.

Consequently, simplistic claims such as "LSM trees are always faster for writes" are unreliable.

The actual result depends on implementation and workload.

A well-tuned B-tree engine can outperform a poorly configured LSM engine.

And vice versa.

The design tells us what trade-offs to investigate.

It doesn't replace measurement.

## 14.3 Database products aren't identical to storage-engine categories

Here's one last misconception to eliminate.

MongoDB is a document database.

That describes its logical data model.

Its commonly used WiredTiger storage engine relies on B-tree-family structures, among other mechanisms.

RocksDB is a key-value storage engine built around an LSM architecture.

PostgreSQL uses heap-organized tables and B-tree indexes by default for many common operations, while supporting other index methods.

These are different layers of description.

A document database doesn't necessarily use an LSM tree.

A relational database isn't automatically implemented as one giant B-tree.

And the presence of a write-ahead log doesn't tell you whether the main storage structure is B-tree-based or LSM-based.

We must distinguish the application-facing data model from the physical mechanisms beneath it.

That distinction is central to understanding modern data systems.

---

# 15. Durability, Replication, and Backups Are Three Different Promises

Before concluding, we need to connect storage-engine internals to distributed architecture.

Suppose our PostgreSQL primary acknowledges a committed transaction.

Under appropriate durability settings and correct storage behavior, the relevant local WAL information has been persisted.

Does that mean the transaction exists on every replica?

Not necessarily.

Replication may be asynchronous.

The primary might acknowledge the transaction before a replica receives or applies the corresponding changes.

If the primary is then destroyed and an outdated replica is promoted, an acknowledged transaction may be absent from the newly promoted system.

That's a replication and failover guarantee issue.

It is separate from whether the primary's local storage engine wrote its WAL correctly.

## 15.1 Local durability versus replicated durability

Local durability concerns what survives relevant failures of the local database process or machine, under the system's configured guarantees.

Replicated durability concerns how many independent systems have received or persisted the required state.

A system can be locally durable but lose acknowledged writes during a poorly configured failover.

Conversely, a replicated system can still be vulnerable to correlated failures, software defects, or incorrect application logic.

Replication is not automatically a backup.

## 15.2 Why backups remain necessary

Imagine an administrator accidentally deletes an important table.

Replication faithfully distributes that deletion to other nodes.

Now every replica agrees that the table is gone.

The system is highly consistent about a disastrous mistake.

A backup provides a different capability: recovering information from an earlier point or an independent protected copy.

Point-in-time recovery systems may combine base backups with archived logs to reconstruct a previous database state.

But that requires correctly configured retention, storage, recovery procedures, and testing.

A collection of backup files is not a recovery strategy until someone has demonstrated that the files can actually restore the required information.

## 15.3 What an acknowledged write really promises

A mature engineer should never treat the word *acknowledged* as a universal durability guarantee.

The meaning depends on the database and its settings.

In PostgreSQL, synchronous-commit behavior affects when commit acknowledgment is returned relative to WAL synchronization and, in relevant configurations, replication.

In MongoDB, write concern determines which acknowledgment conditions the operation requests, including behavior related to journaling and replica acknowledgment.

The specific guarantees require reading the database documentation and understanding the deployed topology.

When an interviewer asks, "Can this database lose acknowledged writes?" the correct response often begins with:

"Under which write concern, durability settings, replication configuration, and failure scenario?"

That's not evasive.

It's the difference between answering a marketing slogan and answering an engineering question.

---

# 16. The Oral Examination

We've reached the point where you should be able to reconstruct the mechanisms from first principles.

Try answering these questions aloud before reading the solutions.

## Challenge 1 — The committed transaction that wasn't in the data file

A PostgreSQL transaction commits successfully.

Immediately afterward, the machine loses power.

Some relevant table pages had not been flushed to disk before the crash.

How can PostgreSQL recover the committed transaction?

What role does WAL play?

## Challenge 2 — The suspiciously large index

A database contains fifty million reservations.

A query retrieves one reservation by indexed ID without scanning all fifty million rows.

Explain how a B-tree-family index makes this possible.

Why are its nodes organized into pages containing many keys rather than one key per page?

## Challenge 3 — The cost of adding indexes

Your backend frequently updates customer records.

An engineer adds eight indexes to accelerate several reporting queries.

Write latency increases noticeably.

Explain why.

What alternatives might reduce the conflict between transactional updates and analytical access?

## Challenge 4 — The LSM write stall

An event-ingestion service writes data to an LSM-based engine.

It performs extremely well during short benchmarks but develops severe write stalls after sustained traffic.

CPU utilization remains moderate.

What mechanisms would you investigate?

Why might adding more RAM merely postpone the problem?

## Challenge 5 — The missing key

An LSM engine contains many SST files.

Applications frequently query keys that don't exist.

Read performance becomes unexpectedly poor.

How can Bloom filters help?

What guarantee do they provide, and what do they not guarantee?

## Challenge 6 — The enormous storage footprint

A database contains approximately one hundred gigabytes of live logical data.

Yet its storage directory occupies considerably more space.

Is that necessarily evidence of a memory leak or corruption?

What mechanisms might explain the difference?

## Challenge 7 — MongoDB versus PostgreSQL

An interviewer asks:

"Is MongoDB faster than PostgreSQL because MongoDB stores documents while PostgreSQL uses B-trees?"

Identify the misconceptions in this statement.

What measurements and workload characteristics would you need to make a meaningful comparison?

## Challenge 8 — The lost reservation after failover

A primary database acknowledges a reservation transaction.

The primary then fails permanently.

A replica is promoted, but the reservation is missing.

Does this necessarily prove that the primary's storage engine failed to honor local durability?

Explain how replication configuration can produce this outcome.

---

# 17. Solutions and Discussion

## Solution 1 — WAL recovery

Under normal durable commit settings, PostgreSQL ensures that the required WAL information is persisted before acknowledging the transaction as durably committed.

The affected data pages may remain dirty in memory.

After a crash, PostgreSQL uses checkpoint information and subsequent WAL records to redo changes required for recovery.

The database's transaction and visibility mechanisms preserve the distinction between committed and incomplete operations.

The key insight is that committed data doesn't have to reach every final data page before the transaction can be durable.

## Solution 2 — B-tree lookup

A B-tree-family index maintains ordered keys in a balanced hierarchy.

Internal pages direct searches toward narrower key ranges.

Because each page contains many entries, the tree can have a high branching factor and remain shallow even for large datasets.

The engine follows only a small number of relevant pages rather than scanning every row.

Leaf entries ultimately identify the relevant indexed data or record references, depending on the implementation.

## Solution 3 — Index write overhead

Every additional index may require maintenance when rows are inserted, deleted, or updated in ways affecting that index.

Index updates can modify multiple pages, generate WAL, consume cache space, and introduce additional I/O.

Possible alternatives include selecting fewer or more targeted indexes, using partial indexes where appropriate, precomputing specific aggregates, moving analytical reads to a suitable separate system, or redesigning access patterns.

The correct response depends on measured query and write costs.

## Solution 4 — LSM compaction pressure

Investigate memtable flush rates, SST file counts, compaction backlog, write-stall counters, storage throughput, and relevant CPU and memory metrics.

If sustained incoming writes exceed the engine's long-term ability to flush and compact data, background maintenance accumulates.

Larger memory buffers can absorb more temporary work, but they cannot eliminate an ongoing mismatch between input rate and sustainable storage-processing capacity.

The solution may require changing compaction resources, storage capacity, ingestion rate, key distribution, or configuration.

## Solution 5 — Bloom filters

Bloom filters can efficiently rule out files or structures that definitely do not contain a requested key, assuming correct construction and operation.

They can produce false positives, so a positive result means the key might exist.

They are useful for avoiding unnecessary storage reads, especially when nonexistent-key lookups are common.

They do not replace actual lookup logic or guarantee that every positive result corresponds to a present key.

## Solution 6 — Storage amplification

Physical storage may contain indexes, logs, obsolete versions, free space within pages, temporary compaction output, snapshots, metadata, or other internal structures.

An LSM engine may temporarily retain overlapping files during compaction.

An MVCC database may retain older row versions until appropriate cleanup.

The correct investigation separates live logical data, indexes, logs, temporary files, and maintenance-related storage.

Large storage usage isn't automatically corruption.

## Solution 7 — Data model versus storage engine

MongoDB's document model doesn't imply one universal physical storage architecture.

Its widely used WiredTiger engine employs B-tree-family storage structures.

PostgreSQL also uses B-tree indexes for many workloads, but its table and indexing architecture is not equivalent to one single tree.

Performance depends on access patterns, indexing, transaction requirements, data distribution, cache behavior, durability settings, hardware, and implementation.

A meaningful comparison requires a defined workload and measurement methodology.

## Solution 8 — Asynchronous replication

A primary may acknowledge a locally durable transaction before an asynchronous replica has received or persisted it.

If the primary is permanently lost and a lagging replica is promoted, the newly active database may lack the transaction.

This does not necessarily mean the primary's local WAL or durability machinery failed.

It means the replicated system's acknowledgment and failover guarantees allowed a gap.

The correct architecture depends on the required relationship between commit acknowledgment, replica durability, and availability.

---

# 18. The Mental Model Worth Keeping

A storage engine is the machinery translating logical data operations into physical memory and storage work.

**Pages** organize persistent data into manageable units.

**Buffer pools** keep useful pages in memory and defer expensive storage access.

**Write-ahead logs** preserve recoverable changes without requiring every data page to be synchronized at each transaction commit.

**Checkpoints** advance persistent state and limit the amount of work required during recovery.

**B-tree-family structures** maintain ordered, searchable pages while handling updates through controlled modifications.

**LSM-tree structures** accept writes into memory and immutable sorted files, then reorganize those files through compaction.

The major trade-offs can be understood through read amplification, write amplification, space amplification, and the cost of maintaining durability.

No architecture eliminates physical work.

It decides when that work happens and which operations pay for it.

The most important principle is:

**A fast database write isn't necessarily a small amount of work. It may be a small amount of foreground work followed by a much larger amount of background work.**

That is why sustainable throughput, latency distributions, storage pressure, and recovery behavior matter more than attractive short benchmarks.

Once you understand these mechanisms, storage engines become much less mysterious.

You can reason about their performance rather than treating them as black boxes with different product logos.

---

# 19. Next Lecture — Document Databases and MongoDB

We've examined the machinery beneath database operations.

But databases also make decisions about what information belongs together.

Should a customer, their addresses, and their payment preferences live in separate structures or within one document?

When is embedding related information more efficient than referencing it?

Why do document updates have particular atomicity boundaries?

And how does MongoDB use indexes, transactions, and its WiredTiger storage engine to support application workloads?

In **CS340-L03 — Document Databases and MongoDB**, we'll return to the application layer, armed with a much better understanding of the physical costs hiding underneath it.

We'll design a real document model for our travel platform, investigate common modeling mistakes, and discover why schema flexibility is useful only when the application still knows what its data means.

The engine room has done its job.

Now let's decide what kind of information we're asking it to manage.

---

# Optional Practical Lab — Inspecting Storage Engines

*The spoken lecture ends here. The remainder is intended for visual study, terminal experimentation, and later revision.*

## Lab A — Inspect PostgreSQL storage layout

Using a local PostgreSQL development database, create a table and index:

```sql
CREATE TABLE storage_lab (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_storage_lab_customer
ON storage_lab (customer_id);
```

Insert a representative set of test records.

Then inspect storage usage:

```sql
SELECT
    pg_size_pretty(pg_relation_size('storage_lab')) AS table_size,
    pg_size_pretty(pg_indexes_size('storage_lab')) AS indexes_size,
    pg_size_pretty(pg_total_relation_size('storage_lab')) AS total_size;
```

Explain why the index consumes storage separately from the table.

Then investigate how the sizes change after inserting more rows.

## Lab B — Observe index access

Run a query against the indexed column:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM storage_lab
WHERE customer_id = 42;
```

Examine the selected query plan and buffer usage.

The planner may choose a sequential scan for small tables or workloads where scanning is cheaper.

That's expected.

As the dataset grows, compare plans and physical work.

Explain why a B-tree index can reduce the number of pages the engine needs to examine.

## Lab C — Inspect PostgreSQL WAL settings

Query relevant configuration:

```sql
SHOW wal_level;
SHOW synchronous_commit;
SHOW fsync;
SHOW full_page_writes;
SHOW checkpoint_timeout;
SHOW max_wal_size;
```

Explain what each setting influences.

Do not disable `fsync` or `full_page_writes` on a production database.

The purpose is to understand how the database's durability and recovery configuration shapes its physical behavior.

## Lab D — Observe PostgreSQL checkpoints

On a suitable modern PostgreSQL installation, inspect checkpoint statistics through the available monitoring views.

For PostgreSQL versions exposing `pg_stat_checkpointer`, examine:

```sql
SELECT *
FROM pg_stat_checkpointer;
```

Older versions expose related checkpoint information differently.

Look for evidence of checkpoint activity and associated writes or synchronization work.

Discuss why checkpoints need not coincide with individual application transaction commits.

## Lab E — Explore MongoDB's storage engine

On a local MongoDB deployment, inspect server status:

```javascript
db.serverStatus().wiredTiger
```

Depending on the version and configuration, the output exposes cache, transaction, and storage-engine statistics.

Inspect cache-related counters and discuss what they reveal.

Do not assume that WiredTiger's internal cache represents the process's complete memory usage.

MongoDB may also use filesystem caching and additional process memory.

## Lab F — Simulate an LSM pipeline

Without requiring RocksDB, build a conceptual simulation.

Begin with a small in-memory map of key-value pairs.

Every time it reaches a fixed number of entries, sort the entries and write them to a new file.

Continue performing updates to existing keys.

Then implement a read operation that searches the newest structures first.

Finally, implement a simple compaction procedure that merges two sorted files and retains the appropriate latest values.

Answer:

1. Why can a key exist in multiple physical files?
2. Why must the read path account for update order?
3. What changes when a key is deleted?
4. Why does compaction consume I/O despite no new logical write?
5. What happens if incoming writes create files faster than compaction can merge them?

This exercise models selected LSM concepts, not a production storage engine.

Real implementations need crash-safe manifests, version visibility, concurrency control, and many other mechanisms.

## Lab G — The benchmark that lies

Design two experiments.

The first writes a large number of records during a short interval.

The second sustains the same intended write rate for an extended period while collecting storage and latency metrics.

For each experiment, measure:

- Logical write throughput.
- Median and high-percentile write latency.
- Physical storage read and write throughput.
- Background maintenance activity.
- Memory usage and flush behavior.
- Available disk space.
- Error and stall counts.

Explain why the results may differ substantially.

Discuss how to distinguish burst capacity from sustainable throughput.

## Lab H — Architecture review

Your company has two workloads.

**Workload A:** A transactional booking system with millions of reservations, frequent ID lookups, moderate updates, and strict business correctness requirements.

**Workload B:** An event-ingestion system collecting thousands of timestamped events per second, with periodic analytical processing and substantial write volume.

Would you automatically choose the same storage engine for both?

Would you automatically choose different engines?

Prepare a recommendation based on access patterns, durability, write amplification, range queries, operational costs, and the availability of mature database implementations.

The objective is to reason about physical mechanisms without confusing a storage-engine choice with the entire database product.

---

## Further Reading — Optional Technical References

1. [PostgreSQL — Database Page Layout](https://www.postgresql.org/docs/current/storage-page-layout.html) — Physical pages, tuple identifiers, and data organization.
2. [PostgreSQL — Write-Ahead Logging](https://www.postgresql.org/docs/current/wal-intro.html) — WAL ordering, durability, and crash recovery.
3. [PostgreSQL — WAL Configuration](https://www.postgresql.org/docs/current/wal-configuration.html) — Checkpoints, WAL volume, and performance trade-offs.
4. [PostgreSQL — B-Tree Indexes](https://www.postgresql.org/docs/current/btree.html) — B-tree index behavior and implementation details.
5. [MongoDB — WiredTiger Storage Engine](https://www.mongodb.com/docs/manual/core/wiredtiger/) — Caching, checkpoints, journaling, compression, and concurrency.
6. [RocksDB — Overview](https://github.com/facebook/rocksdb/wiki/RocksDB-Overview) — Memtables, sorted files, compaction, and storage-engine architecture.
7. [RocksDB — MemTable](https://github.com/facebook/rocksdb/wiki/MemTable) — In-memory write structures and flushing.
8. [RocksDB — Write-Ahead Log](https://github.com/facebook/rocksdb/wiki/Write-Ahead-Log-%28WAL%29) — Logging and recoverability in an LSM-based engine.
9. [SQLite — Write-Ahead Logging](https://www.sqlite.org/wal.html) — An accessible comparison of logging, concurrency, checkpoints, and durability.
10. Martin Kleppmann, *Designing Data-Intensive Applications* — Storage engines, indexing, logs, and distributed-system trade-offs.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
CS340-L02  INSIDE A STORAGE ENGINE — INTERVIEW GLANCE CARD

CORE TENSION
  Memory fast / volatile; disk durable / slower
  Separate: logical change | in-memory representation | durable recovery info
  Fast foreground write often = deferred background physical work

PAGES AND BUFFER POOL
  Fixed-size pages (~8 KiB PG) — unit of I/O, cache, modification
  Dirty page = in-memory changes not yet on durable data page
  Buffer pool / cache: hit vs miss; OS page cache may still serve "miss"
  Hot working set ≪ total DB size → RAM fit matters more than disk size
  Locality: random vs sequential access shapes I/O cost

WRITE-AHEAD LOG (WAL)
  Append recoverable change records BEFORE relying on data-page durability
  Commit can succeed while dirty pages remain in RAM
  Write-ahead rule: log for a modification durable before that page is
  fsync/sync ≠ OS write; durability spans app/DB/OS/device config
  Group commit amortizes sync cost across txs
  Checkpoint advances recoverable persistent state; ≠ every commit
  Deferred work must still happen — checkpoints/compaction create I/O

CRASH RECOVERY
  Replay from checkpoint + subsequent WAL (redo); distinguish committed vs not
  Torn page: partial page write; PG full_page_writes protect (WAL volume cost)
  WAL ≠ transaction system; both cooperate for durability + visibility

B-TREE FAMILY
  High branching factor → shallow trees; pages hold many keys
  B+ style: internal navigate; leaves hold entries / references
  Point lookup + ordered range scans natural
  Writes: leaf insert; full page → split / parent updates
  One logical write may touch heap + many indexes (HOT when eligible)
  Excellent mixed R/W; not free under random write + many indexes

LSM TREES
  Memtable (ordered in-memory) + WAL for durability policy
  Flush → immutable SSTables; new writes go to newer structures
  Read path: memtable → immutable memtables → SST levels (newest first)
  Bloom filter: definite ABSENCE or maybe present (false positives OK)
  Missing-key lookups can be expensive without filters
  Compaction merges sorted files, drops obsolete versions → write amp
  Amplification triad: read / write / space — improve one, worsen another

COMPACTION DEBT (INCIDENT PATTERN)
  Sustained ingest > flush+compact capacity → file backlog
  Engine may stall/slow writes (backpressure) — not always a "bug"
  Measure: flush rates, SST counts, stall counters, storage IOPS vs latency
  More RAM absorbs bursts; cannot invent sustainable throughput
  Burst capacity ≠ sustained throughput — long benchmarks matter

B-TREE VS LSM — WORKLOAD, NOT ACRONYM
  B-tree: frequent lookups, moderate updates, range queries (classic OLTP)
  LSM: heavy write ingest, append/immutable-file friendly patterns
  SSDs change magnitude of random I/O trade-off — still measure
  Product ≠ engine: MongoDB docs + WiredTiger B-trees; RocksDB LSM;
    PG heap + B-tree indexes — model layer ≠ storage layer

THREE DIFFERENT PROMISES
  Local durability     survives local crash under configured sync
  Replicated durability enough independent copies / sync policy
  Backup / PITR        recover earlier state; replication can copy deletes
  "Acknowledged write" depends on sync_commit / write concern / topology
  Async replica promote → may lose primary-acked txs (failover gap)

SENIOR LINE: a fast write may be small foreground work + large background bill.
```
