---
id: CS320-L07
course: CS320
title: "Threads, Atomics, and Memory Ordering"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: CS320-L06
next: CS320-L08
---



# CS320 — Operating Systems and Concurrency

## Lecture 07: Threads, Atomics, and Memory Ordering

*One worker calculates a hotel price, writes the result into shared memory, and announces that the data is ready. Another worker sees the announcement. But how does it know that the data itself is safe to read?*

# Part I — Intuition

## The picture to carry in your head

Imagine two employees working in separate rooms.

One prepares hotel-pricing reports. The other distributes those reports to customers.

They communicate through a shared notice board.

The first employee writes three values: the hotel identifier, the available-room count, and the calculated price. When the report is complete, she places a green card beside it.

The second employee has one instruction:

"When you see the green card, read the report."

The arrangement seems perfectly reasonable.

The first employee writes the information, then raises the flag. The second sees the flag, then reads the information.

But what makes that sequence reliable?

You might answer: "Because the data was written first."

That's the obvious answer. It is also incomplete.

We've already learned that concurrent operations can interleave. Now imagine these employees are not merely taking turns. They are genuinely working simultaneously, each on a different processor.

The processors have caches. They use buffers and speculative execution. The compiler may optimize the instructions. Different memory locations may become observable to other threads under rules that are not captured by a simple wall-clock story.

The question becomes more precise:

**What guarantee establishes that observing the ready flag also establishes the required visibility and ordering of the data written before it?**

That guarantee must come from a synchronization protocol.

Without such a protocol, the notice board is just shared memory with good intentions.

## 1. Shared memory creates a new kind of responsibility

In the previous lecture, we examined two asynchronous JavaScript operations that could interleave across `await`.

That was a logical race.

Even though only one main JavaScript thread executed the relevant instructions at a time, two reservations could act on outdated information.

Now we're dealing with a different situation.

Our pricing engine uses worker threads to execute calculations simultaneously.

Two threads can access the same shared memory while running on different logical processors.

One thread may be reading a location while another writes it.

There may be no common event loop deciding which instruction runs first.

This makes memory-level synchronization essential.

A process can contain several threads. Those threads generally share the process's address space, though they have their own execution stacks, register state, and scheduling contexts.

Sharing an address space makes communication efficient: data need not always be serialized into messages or transferred through a network.

But it also means shared mutable state must be coordinated.

## 2. One line of code may contain several operations

Suppose both workers increment a shared counter.

The source code says:

`counter = counter + 1`

That looks like one action.

But conceptually, the increment involves reading the existing value, adding one, and storing the result.

Imagine the counter begins at ten.

Worker A reads ten.

Worker B reads ten.

Worker A calculates eleven.

Worker B calculates eleven.

Worker A writes eleven.

Worker B writes eleven.

Two workers performed an increment, but the final value is eleven rather than twelve.

This is a **lost update**.

The problem is not that either worker misunderstood arithmetic.

It's that the combined read-modify-write operation wasn't coordinated as one indivisible transition.

For suitable shared counters, an atomic increment can solve this particular problem.

But before celebrating, we need to distinguish three related guarantees.

## 3. Atomicity, visibility, and ordering

**Atomicity** asks whether an operation behaves as an indivisible action under the applicable memory model.

For example, an atomic increment avoids two threads independently reading the same old value and losing one increment.

**Visibility** concerns which writes made by one thread another thread may observe.

A worker may have written a result, but the reader needs a defined synchronization relationship to know which values are safe to observe.

**Ordering** concerns the relationships that must hold between operations across threads.

The compiler and processor may be permitted to rearrange or overlap some internal work, provided the resulting behavior satisfies the language and architecture's guarantees.

These properties are related, but they aren't interchangeable.

An atomic ready flag may correctly change from zero to one.

That doesn't automatically mean the program has correctly published an entire mutable data structure.

The flag and the data must participate in a synchronization protocol with the necessary ordering and ownership guarantees.

## 4. The handshake that makes publication meaningful

Return to the notice board.

We need more than a green card.

We need an agreement about what placing and observing the green card means.

In languages exposing acquire and release memory ordering, a common publication pattern works conceptually like this.

The writer prepares the data.

Then it performs a **release** store to the ready flag.

The reader performs an **acquire** load of that same flag.

If the reader observes the value published by the release operation, the matching synchronization establishes an ordering relationship.

Under the language's rules, writes properly sequenced before publication become safely observable to the reader performing the corresponding accesses after acquisition, provided the surrounding data-sharing protocol is otherwise correct.

Think of release as officially handing over the completed report.

Acquire is accepting that handover.

The relationship is more precise than "one happened a few microseconds before the other."

It's a guarantee established by the memory model.

One crucial condition remains: the writer must not start modifying the supposedly completed snapshot again while the reader is using it without another synchronization arrangement.

A correct one-time publication does not automatically create a correct reusable shared buffer.

## 5. Why stronger ordering isn't a universal cure

You might wonder why we don't simply demand that every shared-memory operation execute in one globally agreed order.

Sometimes we do use a strong ordering model called **sequential consistency**.

It provides a particularly understandable way to reason about relevant atomic operations.

But even strong atomic ordering doesn't turn several independent fields into one indivisible snapshot.

Suppose a producer updates the price, inventory count, and hotel identifier separately.

A reader might access those fields while the producer is halfway through the next update.

Each individual atomic access can be perfectly correct.

The collection can still represent a mixture of versions.

We need to protect the invariant spanning the fields.

A mutex might be the simplest solution.

Alternatively, a carefully designed versioned publication scheme could work.

The important idea is that synchronization must match the scope of the state being protected.

## 6. The three questions we'll carry forward

Our notice-board story gives us three durable questions.

**Who owns the shared data while it is being modified?**

**Which synchronization operation makes the completed state available to another thread?**

**What prevents the data from changing while another thread assumes it is stable?**

Those questions are more useful than memorizing a list of atomic instructions.

Before moving on, explain aloud why an atomic ready flag is insufficient if the writer keeps modifying the published data without coordinating with the reader.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The pricing snapshot that was ready before it was safe

Our hotel-booking backend has moved its expensive pricing calculations off the main JavaScript thread.

The new architecture uses Node.js worker threads.

Each worker calculates prices for a collection of hotels. Instead of copying every result through messages, the team has introduced a shared memory region.

A worker writes a hotel identifier, the current inventory count, and a calculated price.

Then it marks the snapshot ready.

The main thread watches for ready snapshots and sends the results to customers.

The implementation performs well in benchmarks.

Then a production incident arrives.

Occasionally, the system publishes a hotel price associated with the wrong inventory version.

Sometimes the identifier and price appear to come from different updates.

The team suspects a race.

But which race?

Is the data being accessed without appropriate atomic operations?

Is the publication flag missing a synchronization guarantee?

Or is the writer beginning a new update while the consumer still reads the previous one?

These explanations are different.

The first is about conflicting shared-memory accesses.

The second is about memory ordering.

The third is about ownership and the consistency of a multi-field snapshot.

To diagnose the problem, we need a precise model of shared-memory execution.

## 2. Threads and shared address spaces

A process can contain several operating-system threads.

On Linux, those threads are schedulable execution contexts sharing selected process resources, including the same virtual address space.

Each has its own execution state and stack.

On a multicore machine, different threads can execute simultaneously.

That creates opportunities for genuine simultaneous memory access.

### Sharing does not mean everything is shared

In Node.js, `worker_threads` create additional JavaScript execution environments.

Ordinary JavaScript objects are not automatically shared as mutable objects between these environments.

Workers can communicate through message passing.

They can also share appropriate binary memory through `SharedArrayBuffer`.

That distinction matters.

If the main thread sends an ordinary object through the worker messaging API, the worker generally receives data through structured cloning or supported transfer semantics.

The same shared-object access problem doesn't automatically arise.

But if both threads access a typed-array view over the same `SharedArrayBuffer`, they can observe and modify the same underlying bytes.

Now synchronization matters directly.

### Native code can also share memory

This isn't only a JavaScript concern.

Native libraries, Java threads, Go goroutines executing concurrently, and Rust threads can all interact with shared memory under their language and runtime rules.

The underlying processors and caches are similar.

But the languages define different guarantees and expose different synchronization APIs.

We must respect those differences rather than assume every language behaves like C++ or JavaScript.

## 3. The lost increment: atomic read-modify-write

Begin with the simplest possible shared-state operation.

Two workers increment one counter.

A naïve implementation reads the old value, adds one, and writes the result.

As we saw in Part I, concurrent execution can lose updates.

An atomic read-modify-write operation performs the relevant change indivisibly under the language's memory model.

In JavaScript, `Atomics.add` can operate on an appropriate typed-array element backed by shared memory.

If two workers each perform one thousand atomic increments, the final result should reflect two thousand increments, assuming no overflow-related issue or other interfering operation changes the counter.

Each individual update participates in the required atomic ordering.

### Atomicity is scoped

Now suppose each worker must update two counters together.

One represents reservations processed.

The other represents the corresponding total revenue.

Atomically incrementing each counter separately doesn't automatically make the pair appear as one indivisible transaction.

A reader might observe the reservation count updated before the revenue count.

There may be no single consistent snapshot of both fields.

If the invariant requires the pair to change together, we need a synchronization mechanism protecting the pair as a logical unit.

This is the first principle of atomic programming:

**An atomic operation protects the operation it defines, not every larger sequence in which it appears.**

## 4. What is a data race?

The term *race condition* is broader than *data race*.

A race condition occurs when correctness depends on uncontrolled ordering.

A data race is a more specific concept defined by a programming language's memory model.

In C++ and Rust, for example, conflicting non-atomic accesses to the same memory location from different threads without appropriate ordering can constitute a data race, and such behavior is not permitted in well-defined safe concurrent programs.

In C++, a data race produces undefined behavior.

Rust's safe abstractions are designed to prevent data races, though unsafe code can violate the required invariants.

Java and Go define their own rules for incorrectly synchronized programs.

JavaScript also has a shared-memory model, but it should not be described as identical to C++'s undefined-behavior rules. Its ordinary shared typed-array accesses and atomic accesses have different semantics.

For learning purposes, the practical rule is straightforward:

When several execution agents can access the same mutable memory, use synchronization mechanisms appropriate to the language and ensure that all conflicting accesses follow the intended protocol.

### A logical race can exist without a data race

Our earlier double-booking example involved independent asynchronous operations accessing authoritative database state.

It was logically incorrect even without simultaneous unsynchronized memory writes.

Conversely, a program can be completely free of low-level data races and still produce a business-level race.

A thread-safe counter does not guarantee correct room reservations.

Memory correctness and business correctness are separate questions.

## 5. Happens-before: an ordering guarantee, not a clock reading

Here's the most important formal concept in the lecture.

A **happens-before relationship** is an ordering relationship defined by the language's concurrency model.

The name sounds temporal, but it isn't merely about which action happened first according to a stopwatch.

Imagine one thread writes a price at 10:00:00.001.

Another thread reads the price at 10:00:00.002.

Those timestamps don't establish that the reader has performed the synchronization needed under the programming language's rules.

The language must define which observations are allowed.

### Two ingredients

Happens-before relationships are commonly established through two categories of rules.

First, relevant operations within one thread have an ordering relationship defined by the language.

Second, synchronization operations can establish relationships between threads.

Examples include an appropriate mutex unlock followed by an acquisition, or a matching atomic release and acquire sequence.

The relationships compose transitively.

If operation A happens-before B, and B happens-before C, then A happens-before C.

This permits us to reason about data publication across several operations.

### Our pricing example

Suppose a producer prepares a snapshot and then publishes it through a release operation.

A consumer performs a corresponding acquire operation that observes the published value.

The synchronized handoff establishes the necessary relationship from the producer's prior writes to the consumer's subsequent reads, subject to the language's rules and correct ownership of the data.

The consumer is not merely guessing that sufficient time has elapsed.

It has observed a defined synchronization event.

This is the core difference between reliable shared-memory programming and relying on timing.

## 6. Why compilers and CPUs complicate visibility

Developers often imagine instructions executing exactly in source-code order.

Modern systems are more sophisticated.

Compilers optimize programs by rearranging, combining, or eliminating operations where allowed.

Processors use caches, store buffers, out-of-order execution, and speculative mechanisms to improve performance.

The result may not resemble a naïve instruction-by-instruction picture.

But there is a crucial qualification.

Compilers and processors are constrained by the behavior required by the relevant language and architecture.

They cannot arbitrarily violate the guarantees of properly synchronized code.

### The single-threaded illusion

Consider two independent calculations.

The compiler may perform them in a different internal order if the program's required observable behavior remains correct.

A single thread may never notice.

But another thread observing shared memory can expose differences if the program lacks the necessary synchronization.

The memory model determines which observations are permitted.

### Cache coherence isn't sufficient by itself

Modern multiprocessors generally maintain coherent caches for relevant memory.

That helps processors agree about modifications to individual memory locations.

But coherence does not automatically make an entire multi-field operation atomic.

Nor does it establish every cross-location ordering relationship a program might require.

Even if every processor eventually observes a new value, "eventually" is not an adequate contract for reading a fully initialized shared data structure.

### Architecture matters, but language guarantees come first

x86-64 and ARM processors have different memory-ordering characteristics.

Some ordering patterns that appear reliable on one architecture may expose missing synchronization more readily on another.

But a program shouldn't rely on accidental behavior of a particular CPU model when its programming language defines a stronger portability contract.

Correct concurrent code is written against the language memory model and synchronization primitives.

Hardware-specific optimization comes later.

## 7. The memory-ordering ladder

Languages such as C++ and Rust expose several memory-ordering modes for atomic operations.

Understanding their purpose helps us reason about concurrency without immediately becoming specialists in lock-free algorithms.

### Relaxed ordering

A relaxed atomic operation preserves atomicity for the accessed location without introducing the broader ordering constraints associated with acquire or release synchronization.

Imagine a statistics counter that merely tracks how many jobs have completed.

Several threads increment it.

We need every increment to be counted correctly.

But we're not using the counter to announce that a separate shared data structure is ready.

Relaxed atomic increments may be sufficient.

The counter is correct as an atomic variable.

It is not being used to publish another object.

### Release ordering

A release operation is used when a thread publishes preceding work.

Conceptually, the writer prepares the shared data and then performs a release store to the publication flag.

The release prevents the preceding operations from being treated as occurring after that publication in ways prohibited by the memory model.

### Acquire ordering

A corresponding acquire operation is used by the reader.

If it observes the value written by the matching release operation, the two operations establish synchronization.

The reader can then safely use the properly published data, assuming the data is otherwise managed without conflicting unsynchronized modification.

Release and acquire are complementary.

A release store is not a magic broadcast independent of what the reader observes.

The reader must participate in the appropriate synchronization relationship.

### Acquire-release

Atomic read-modify-write operations may need both effects.

For example, a thread might atomically update a synchronization variable while also receiving information published by earlier operations.

Acquire-release ordering provides the corresponding combined constraints for the relevant operation.

### Sequential consistency

Sequentially consistent atomic operations provide a stronger, simpler ordering model.

Roughly, the relevant operations participate in one total order consistent with the model's required relationships.

This is often easier to reason about.

But don't overinterpret it.

Sequential consistency of individual atomic accesses doesn't turn an entire shared data structure into one indivisible transaction.

And mixing operations with different ordering strengths requires understanding the precise language rules.

For ordinary application developers, the sensible default is to prefer well-established synchronization primitives and straightforward guarantees rather than prematurely selecting the weakest possible ordering for performance.

## 8. JavaScript's `Atomics` model is different

Now return to our Node.js pricing workers.

JavaScript exposes shared binary memory through `SharedArrayBuffer` and atomic operations through `Atomics`.

Its standard atomic operations are sequentially consistent.

Unlike Rust and C++, JavaScript doesn't provide API options to choose relaxed, acquire, or release ordering for these ordinary `Atomics` operations.

That is a meaningful simplification.

### A one-time publication protocol

Suppose the shared memory contains two integer positions.

The first holds the calculated result.

The second is a ready flag.

The producer uses `Atomics.store` to write the result.

Then it uses `Atomics.store` to set the ready flag to one.

The consumer uses `Atomics.load` to examine the ready flag.

Once it observes one, it loads the result through `Atomics.load`.

For this simple one-time publication, assuming only the designated producer publishes the value, the atomic operations provide a straightforward synchronization story.

The consumer observes the published state through the defined sequentially consistent ordering.

### Why use atomic access to the result too?

It makes the teaching example easier to reason about.

We avoid depending on the more subtle behavior of ordinary shared-memory accesses.

The result and ready flag participate in the atomic model.

But there is still a problem if the writer starts modifying the result again immediately after publication.

The consumer might observe the ready flag from one publication and read data belonging to the next update.

The atomic operations themselves could all be correct.

The surrounding protocol would still be wrong.

To reuse the buffer, we need an explicit ownership or versioning protocol, or we need to serialize access.

This is why a pair of correct atomic instructions is not automatically a correct shared-data architecture.

## 9. Waiting for shared state without wasting CPU

Imagine the consumer repeatedly checking the ready flag.

Still zero.

Still zero.

Still zero.

It performs millions of checks while waiting for the producer.

This is called **spinning** or busy waiting.

For extremely short expected waits in specialized algorithms, spinning can sometimes be useful.

But long or indefinite spinning wastes processor time and can create unnecessary contention.

### `Atomics.wait`

JavaScript provides `Atomics.wait` for suitable shared integer typed arrays in execution contexts that permit blocking waits.

The operation checks whether a shared location still contains an expected value.

If it does, the calling thread can wait until notification or timeout under the API's semantics.

Another thread can update the value and call `Atomics.notify` to wake waiters.

This can avoid continuously burning CPU.

However, blocking waits are generally inappropriate on a main event-loop thread.

Browsers prohibit `Atomics.wait` on their main thread. Node.js permits more threading arrangements, but blocking its main JavaScript thread would undermine responsiveness.

Worker threads are the natural place for this sort of blocking coordination.

An asynchronous alternative, `Atomics.waitAsync`, exists for supported environments and use cases.

### Notification isn't proof

Suppose a thread wakes after a notification.

It must still check the shared condition.

A notification may wake it even if the application-level condition it needs is no longer true.

This is conceptually similar to condition variables in other languages.

The correct pattern is to wait for a predicate, not to assume that receiving a notification means the desired state exists.

## 10. Mutexes: protect the entire invariant

Our snapshot becomes more complicated.

It now contains a hotel identifier, inventory count, price, discount, currency, and version number.

We could design a sophisticated atomic publication algorithm.

But perhaps we don't need one.

A **mutex** provides mutual exclusion.

A thread acquires the mutex before entering the protected critical section.

Other participating threads must wait until the lock is released.

If every read and write of the protected snapshot follows the same locking discipline, the reader can obtain a consistent view while holding the mutex.

### The lock must cover the real invariant

Suppose the writer locks only while updating the price.

Then it unlocks.

Later it locks while updating the inventory count.

A reader might acquire the mutex between those operations.

Each individual update was protected.

But the reader can still observe a mixture of snapshot versions.

The mutex wasn't defective.

The protected region was too small.

The correct critical section must cover the set of operations that must appear consistent together.

### Locks have costs

Mutexes serialize access to protected resources.

Under contention, threads may wait.

Long critical sections can reduce parallelism.

Holding a lock while performing slow I/O is especially dangerous because unrelated contenders may remain blocked.

But these costs don't make locks bad.

A simple correct mutex design is often preferable to a highly sophisticated lock-free structure that nobody on the team can safely maintain.

### Lock ownership matters

A mutex may have ownership requirements: the thread that acquires it is responsible for releasing it according to the primitive's rules.

A semaphore is related but not identical. It typically manages permits rather than exclusive ownership of one critical section.

Use the primitive that expresses the intended constraint.

## 11. Condition variables: wait for state changes

Now imagine a queue shared by several producer and consumer threads.

Producers add work.

Consumers remove work.

What should a consumer do when the queue is empty?

Repeatedly lock the queue, check it, unlock it, and try again?

That wastes resources.

Many threading libraries provide **condition variables**.

A consumer acquires the queue mutex and checks whether work is available.

If not, it waits on the condition variable.

The wait operation atomically releases the mutex and blocks under the primitive's semantics.

When awakened, the consumer reacquires the mutex before continuing.

Then it checks the queue condition again.

### Why the wait must release the mutex

Imagine the consumer keeps the mutex while sleeping.

The producer needs the same mutex to add work.

The producer cannot acquire it.

The consumer waits forever for work that the producer cannot insert.

A correctly used condition variable avoids this problem by releasing the lock as part of the wait operation.

### Why the condition must be checked in a loop

A notification doesn't guarantee that work remains available.

Another consumer may have acquired the mutex first and removed the item.

Some condition-variable implementations also permit spurious wakeups.

Therefore, the consumer checks the predicate again after waking.

The rule is not "wait until notified."

It's "wait until the condition protected by this mutex is true."

That difference is small in syntax and enormous in correctness.

## 12. Deadlocks: when correct locks form an incorrect system

Our pricing engine uses two mutexes.

One protects the snapshot cache.

The other protects shared statistics.

Worker A acquires the snapshot lock.

Then it attempts to acquire the statistics lock.

Worker B has already acquired the statistics lock.

It attempts to acquire the snapshot lock.

Now A waits for B.

B waits for A.

Neither can proceed.

This is a **deadlock**.

Each mutex works correctly.

The failure emerges from how the operations are composed.

### The classic conditions

Deadlocks are commonly explained through four necessary conditions in the traditional resource-allocation model:

Mutual exclusion: some resources can be held exclusively.

Hold and wait: a participant holds resources while waiting for others.

No preemption: resources aren't forcibly taken away in the relevant protocol.

Circular wait: participants form a cycle of dependencies.

Breaking an applicable condition can prevent the corresponding deadlock.

A particularly useful strategy is establishing a consistent global order for acquiring locks.

For example, always acquire the snapshot lock before the statistics lock.

If every relevant path obeys that order, the particular reversed-order cycle cannot occur.

### Deadlock isn't ordinary contention

A heavily contended mutex may delay many threads, but eventually the lock holder releases it and work proceeds.

In a deadlock, the participating operations cannot make progress under their current dependency cycle.

The distinction matters for diagnosis.

More CPU capacity may help ordinary contention if it allows lock holders to execute more promptly.

It doesn't solve a circular wait where no participant can reach the release operation.

### Priority inversion

Another synchronization-related scheduling problem occurs when a high-priority thread waits for a lock held by a lower-priority thread.

If other work prevents the lower-priority holder from executing, the high-priority thread remains blocked.

Some lock implementations support priority inheritance to mitigate this scenario.

But scheduling priority is not a substitute for sound lock design.

## 13. Compare-and-swap: conditional atomic updates

Now suppose we want to update a shared counter without acquiring a mutex for every operation.

A useful primitive is **compare-and-swap**, often abbreviated CAS.

Its conceptual contract is:

"Replace the current value with this new value, but only if it still equals the value I expected."

Suppose a counter contains five.

Worker A reads five and proposes six.

Worker B also reads five and proposes six.

A performs the conditional atomic update first.

The value becomes six.

B attempts the same operation but discovers that the current value is no longer five.

Its update fails.

B can read the new value, calculate another result, and retry.

This is optimistic concurrency at the memory level.

### CAS loops

Some algorithms repeatedly load a value, calculate a candidate replacement, and attempt a compare-and-swap.

If another participant changed the value, the operation retries.

These algorithms can avoid locking under certain conditions.

But retrying has a cost.

Under heavy contention, many threads may repeatedly fail their CAS attempts.

A theoretically lock-free design can consume substantial CPU and deliver disappointing throughput.

### The ABA problem

There's a subtle failure.

Suppose a thread reads value A.

Another thread changes it from A to B and then back to A.

The first thread performs compare-and-swap expecting A.

The comparison succeeds.

But the shared state changed in between.

If the algorithm assumed that seeing A means nothing changed, its assumption is false.

This is the **ABA problem**.

In simple counters, the intermediate history may not matter.

In lock-free pointers, queues, or resource-lifetime protocols, it can matter enormously.

Common solutions involve version tags, carefully designed reclamation, or other specialized algorithms.

CAS detects whether the current value matches.

It doesn't automatically prove that the object's history or identity remained unchanged.

## 14. Lock-free doesn't mean wait-free

The phrase *lock-free* sounds like a promise of speed.

It is not.

It describes a type of progress guarantee.

Roughly speaking, a lock-free algorithm guarantees system-wide progress under its model even when individual threads are delayed.

An individual participant may still fail repeatedly and starve.

**Wait-free** algorithms provide a stronger individual progress guarantee: each operation completes within a bounded number of its own steps under the defined assumptions.

These are technical properties.

They do not mean "uses no mutex-looking object" or "always outperforms locking."

### The hidden problem of memory reclamation

Imagine a lock-free linked structure.

A thread reads a pointer to a node.

Another thread removes that node.

When may the removed memory be freed?

If the first thread still holds a reference, freeing the node too early can lead to invalid memory access.

Lock-free data structures often require sophisticated memory-reclamation strategies, such as hazard pointers or epoch-based reclamation.

This is one reason implementing custom lock-free structures is difficult.

The atomic update may be the easy part.

Managing object lifetime under concurrent access is often the real challenge.

For application engineering, prefer mature concurrency primitives and proven libraries unless the workload genuinely justifies a specialized implementation.

## 15. False sharing: correct code, disappointing speed

Now imagine eight pricing workers.

Each maintains its own independent counter.

No worker modifies another worker's counter.

There is no logical need for synchronization between them.

Yet performance scales poorly.

One possibility is **false sharing**.

Processors manage cache coherence at a granularity commonly called a cache line.

A frequently encountered cache-line size is sixty-four bytes, although the actual value is architecture-dependent.

Suppose several independent counters occupy the same cache line.

Worker A repeatedly updates counter A.

Worker B repeatedly updates counter B.

Although the logical variables are different, the processors may need to coordinate ownership of the same cache line.

The line can move between cores or generate coherence traffic.

That increases execution overhead.

### False sharing isn't a data race

The counters may be correctly atomic or otherwise independently owned.

No worker needs another worker's value.

The problem is physical placement within the hardware's cache-coherence unit.

This is a performance problem, not necessarily a logical correctness problem.

### Possible mitigation

Separating frequently written fields onto different cache lines can reduce contention in appropriate workloads.

Padding, alignment, and layout changes are common techniques.

But blindly padding every field wastes memory and may harm cache efficiency elsewhere.

We should measure the relevant workload before changing layout.

This is another example of an important performance principle:

**Logical independence doesn't always imply physical independence.**

## 16. The same principles across languages

Now let's compare how several languages express these ideas.

The mechanisms are broadly similar, but the language contracts are different.

### Rust

Rust's ownership and borrowing system prevents many unsafe sharing patterns in safe code.

Its `Send` and `Sync` traits participate in the rules governing values transferred or shared across threads.

Rust provides mutexes, channels, and atomic types.

Its atomics support ordering choices such as Relaxed, Acquire, Release, AcqRel, and SeqCst.

Safe Rust aims to prevent memory data races.

But it cannot prevent every logical race, deadlock, capacity problem, or business invariant violation.

A Rust service can still double-book a hotel if its database workflow is incorrect.

### Java

Java has a defined memory model governing shared variables and synchronization.

The `synchronized` construct provides monitor-based mutual exclusion and relevant happens-before relationships.

A write to a `volatile` field can synchronize with subsequent reads of that field under the memory model's rules.

Java also provides atomic classes and higher-level concurrency utilities.

But `volatile` doesn't magically turn a multi-statement workflow into a transaction.

If several fields must form one consistent snapshot, their update and publication protocol still matters.

### Go

Go supports goroutines, mutexes, channels, and atomic operations.

Its memory model specifies synchronization relationships.

Channel sends and corresponding receives can establish happens-before guarantees.

The `sync/atomic` operations provide sequentially consistent atomic behavior under Go's specified semantics.

Go's documentation strongly encourages programs to avoid unsynchronized shared-memory races.

The common engineering advice is useful: share memory through communication where appropriate, rather than making every goroutine coordinate mutable state directly.

But channels and goroutines don't eliminate deadlocks or business-level races.

### JavaScript

JavaScript's ordinary main-thread execution model often avoids simultaneous access to the same JavaScript object from independent JavaScript threads.

Node.js worker threads introduce additional execution environments.

Explicitly shared binary memory through `SharedArrayBuffer` can be accessed from multiple workers.

The `Atomics` API provides sequentially consistent atomic operations for supported typed-array elements.

Message passing provides another communication model.

As in other languages, a correct atomic access doesn't automatically establish an entire application-level invariant.

The correct question remains: which state is shared, and what synchronization contract protects it?

## 17. Message passing: sometimes the best shared memory is none

Our pricing engine originally chose shared memory to avoid copying results.

That can be justified for large data structures or high-throughput computation.

But shared mutable memory introduces substantial coordination complexity.

What if each worker simply calculates its result and sends a message to the main thread?

The main thread receives the result and updates its own state.

Now each worker can own its working data until publication.

The main thread owns the final application-facing state.

The communication boundary is explicit.

### Advantages

Message passing can reduce shared mutable state.

It makes ownership easier to understand.

It can provide clearer task lifetimes and error-handling boundaries.

The programmer reasons about complete messages rather than partially updated memory regions.

### Costs

Messages may require serialization, structured cloning, copying, or transfer of ownership, depending on the API.

Large data structures can introduce overhead.

Communication queues need capacity control.

Messages can arrive in surprising orders.

If several workers produce versions of the same logical entity, the receiver still needs rules determining which version is authoritative.

Message passing is not a universal correctness guarantee.

It is often a useful way to simplify ownership and synchronization.

### The design choice

Use shared memory when the workload benefits significantly from low-overhead access and the team can maintain a correct protocol.

Use message passing when explicit ownership and manageable communication overhead make the system easier to understand.

For many application-level workloads, clarity is worth more than avoiding every memory copy.

## 18. Why atomics don't prevent double booking

We began this course with a booking race.

Let's close the conceptual loop.

Suppose our pricing worker has a perfectly synchronized shared-memory inventory counter.

All increments and decrements are atomic.

Excellent.

Now imagine the booking platform runs five backend replicas.

Each replica has its own processes and its own memory.

The authoritative inventory is stored in PostgreSQL.

Does a correct atomic counter inside one Node.js process prevent the entire system from overselling?

No.

The atomics protect local shared memory.

They don't automatically coordinate independent processes across machines.

A database transaction or another appropriate durable coordination mechanism must protect the actual booking invariant.

There are therefore several distinct correctness boundaries.

**Memory atomicity:** an operation on shared memory is indivisible under the language memory model.

**Application-state consistency:** a collection of local state changes respects its required invariant.

**Distributed business correctness:** operations across services, databases, and external systems preserve the intended business contract.

Success at one boundary doesn't imply success at the others.

This is why technology names are not answers.

"Use Rust."

"Use atomics."

"Use a mutex."

"Use Redis."

None of these statements explains what state is being protected, which participants can modify it, or what failure model must be handled.

A correct design starts with the invariant and its actual ownership boundary.

## 19. Diagnosing our pricing-snapshot failure

We now have a systematic investigation method.

Our pricing workers publish snapshots through shared memory.

The main thread occasionally observes inconsistent data.

First, identify exactly what is shared.

Is there a `SharedArrayBuffer`?

Are there multiple typed-array views over the same bytes?

Are ordinary objects transferred or cloned instead?

Does a native addon participate?

Second, list the writers and readers.

Which thread writes the hotel identifier?

Which writes the inventory count?

Which publishes the price?

Who sets the ready flag?

Can multiple workers write the same snapshot?

Third, examine the synchronization operations.

Are the accesses atomic where required?

Does the publication step establish the necessary ordering?

Does the reader actually observe the correct publication event?

Fourth, examine lifecycle and reuse.

Is the producer modifying the snapshot again before the consumer finishes reading it?

Does the reader have an ownership claim or a consistent versioning protocol?

Fifth, reduce the failure to a controlled experiment.

Instead of relying on thousands of random runs, force the producer and consumer to reach the relevant boundary at specific times.

A deterministic barrier can expose a particular invalid interleaving.

For native code, use suitable race-detection tools where available.

For JavaScript shared memory, construct targeted tests that exercise the actual ownership and publication contract.

### The incident's resolution

Suppose we discover that the ready flag was updated atomically, but the writer immediately reused the same buffer for the next result.

The consumer sometimes read fields after the next update began.

The atomic flag worked.

The protocol did not.

We can fix this by using a mutex around the complete snapshot, a carefully designed versioned buffer protocol, or message passing that transfers a completed result without concurrent mutation.

The best choice depends on performance requirements.

But the diagnosis is now precise.

We didn't merely have "a race somewhere."

We had a shared-memory ownership protocol that allowed a writer to mutate data while a reader assumed it was stable.

That's an actionable explanation.

---

# The Oral Examination

Answer aloud before reading the solutions. These questions are designed to distinguish memorized terminology from actual understanding.

**Question 1 — The lost increment**

Two threads each execute `counter = counter + 1` one thousand times. Why might the final counter be smaller than two thousand?

**Question 2 — The ready flag**

A worker writes three ordinary fields and sets a ready flag. Another thread sees the flag. Why is the publication protocol incomplete unless appropriate synchronization and data ownership rules are established?

**Question 3 — Atomicity versus snapshot consistency**

Every field of a six-field snapshot is individually atomic. Can a reader still observe a mixture of two different logical versions?

**Question 4 — Release and acquire**

Explain what relationship is established when an acquire load observes the value published by a matching release store. Why does this matter for preceding data writes?

**Question 5 — Relaxed ordering**

When might a relaxed atomic increment be appropriate? Why shouldn't a relaxed counter automatically be used as a publication flag for unrelated data?

**Question 6 — The condition variable**

A consumer waits for a queue to become nonempty. Why must waiting release the mutex, and why must the condition be checked again after waking?

**Question 7 — The deadlock**

Worker A holds lock X and waits for Y. Worker B holds Y and waits for X. Which design rule can prevent this particular cycle?

**Question 8 — Compare-and-swap**

What does CAS guarantee? Explain how the ABA problem can defeat an algorithm that assumes an unchanged value means unchanged history.

**Question 9 — False sharing**

Two threads update different counters, yet performance degrades because the counters occupy one cache line. Is this necessarily a data race? What's the hardware mechanism?

**Question 10 — The distributed boundary**

Why doesn't a perfect atomic counter inside a Node.js worker prevent double booking across several backend replicas using PostgreSQL?

---

# Solutions and Discussion

## Solution 1 — Read, modify, write can interleave

The increment involves reading the old value, computing a replacement, and storing it.

Two threads can read the same old value and both write the same new value.

One increment is effectively lost.

An appropriate atomic read-modify-write operation prevents this particular lost-update problem.

## Solution 2 — A flag needs a synchronization contract

The reader must use an appropriate synchronization mechanism to establish that preceding writes have been published safely.

The writer must also avoid conflicting mutation while the reader uses the data.

Atomicity of the flag alone does not make the entire snapshot stable.

## Solution 3 — Individual atomics don't create a multi-field transaction

Yes.

A reader may see some fields from one update and others from a later update if the protocol permits concurrent modification.

Protect the entire invariant using a mutex or a correctly designed publication/versioning mechanism.

## Solution 4 — Happens-before through synchronization

An appropriate release store and corresponding acquire load can establish a synchronizes-with relationship when the acquire observes the published value.

That orders preceding producer writes before subsequent consumer reads according to the language model.

The surrounding shared-data protocol must still avoid conflicting unsynchronized mutation.

## Solution 5 — Atomic counting without publication

Relaxed ordering can be suitable for an independent statistics counter when we need accurate atomic updates but don't use the counter to publish other state.

A publication protocol requires appropriate synchronization of the data being announced, not merely an atomic numeric update.

## Solution 6 — Release the lock and recheck the predicate

The wait must release the mutex so producers can acquire it and change the protected state.

After waking, the consumer reacquires the mutex and checks the condition again.

Another consumer may have taken the work, or a permitted spurious wakeup may have occurred.

Notification is not equivalent to the predicate being true.

## Solution 7 — Consistent lock ordering

Establish a global order for acquiring the relevant locks.

For example, always acquire X before Y.

If every participating code path follows that rule, this particular circular-wait pattern cannot occur.

## Solution 8 — CAS compares the current value, not its history

CAS atomically replaces a value only if it matches the expected value.

But another thread could change A to B and back to A before the comparison.

The value matches, yet the object or structure may have changed in a meaningful way.

Version tags and other specialized techniques can address ABA when necessary.

## Solution 9 — False sharing is hardware contention

Not necessarily a data race.

The variables may be independently owned or correctly atomic.

But writes to different values occupying the same cache line can require cache-coherence coordination between processors.

That can reduce throughput despite logical independence.

## Solution 10 — The wrong synchronization scope

Local atomics coordinate shared memory accessible to the participating threads.

Independent backend replicas don't automatically share that atomic location.

The authoritative inventory invariant must be enforced through the database or another appropriate durable coordination mechanism.

---

# The Mental Model Worth Keeping

When several threads access shared state, ask four questions:

**Ownership:** Who may read or modify the data at each point in its lifetime?

**Atomicity:** Which operations must be indivisible?

**Ordering:** What synchronization establishes that writes are safe for another thread to observe?

**Scope:** Does the mechanism protect the actual state and participants involved in the invariant?

An atomic variable is a building block. A mutex is a coordination mechanism. A correct concurrency protocol defines how all participants use them.

**Thread safety is not the presence of atomics or locks. It is the preservation of the required invariants under every execution ordering the system permits.**

# Next Lecture — Operating-System and Runtime Forensics

We've studied processes, scheduling, memory, I/O, application concurrency, and shared-memory synchronization.

Now imagine a production service that begins accumulating open sockets.

Retries increase.

Memory usage rises.

Latency deteriorates.

The CPU dashboard looks healthy.

Then containers begin restarting.

Which symptom is the cause?

Which is merely a consequence?

And which measurement will distinguish the competing explanations?

In CS320-L08, we'll bring the entire course together through one production incident. We'll follow the evidence through operating-system and runtime boundaries, identify the first broken contract, and build a defensible remediation.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Lab — Shared Memory Without Guesswork

These experiments are designed for Node.js 20 or newer and a local development machine.

They are not intended for production systems.

## Lab A — Demonstrate lost updates and atomic increments

Create a file named `shared-counter.mjs`:

```javascript
import {
  Worker,
  isMainThread,
  parentPort,
  workerData
} from "node:worker_threads";

const WORKERS = 4;
const INCREMENTS = 200_000;

if (isMainThread) {
  const buffer = new SharedArrayBuffer(4);
  const counter = new Int32Array(buffer);

  async function run(useAtomics) {
    Atomics.store(counter, 0, 0);

    await Promise.all(
      Array.from({ length: WORKERS }, () =>
        new Promise((resolve, reject) => {
          const worker = new Worker(
            new URL(import.meta.url),
            {
              workerData: {
                buffer,
                increments: INCREMENTS,
                useAtomics
              }
            }
          );

          worker.once("message", resolve);
          worker.once("error", reject);
          worker.once("exit", code => {
            if (code !== 0) {
              reject(new Error(`Worker exited: ${code}`));
            }
          });
        })
      )
    );

    return Atomics.load(counter, 0);
  }

  console.log("Expected:", WORKERS * INCREMENTS);
  console.log("Non-atomic:", await run(false));
  console.log("Atomic:", await run(true));
} else {
  const {
    buffer,
    increments,
    useAtomics
  } = workerData;

  const counter = new Int32Array(buffer);

  for (let i = 0; i < increments; i++) {
    if (useAtomics) {
      Atomics.add(counter, 0, 1);
    } else {
      counter[0] = counter[0] + 1;
    }
  }

  parentPort.postMessage("done");
}
```

The non-atomic result may be smaller than the expected count, but the exact result is nondeterministic. A particular run isn't guaranteed to exhibit a lost update.

The atomic version should account for all increments, provided no other operation modifies the counter and the numerical range remains appropriate.

**Questions:** Why is the ordinary increment unsafe? Why does `Atomics.add` protect this particular update? Would atomic increments of two separate fields automatically protect an invariant between them?

## Lab B — Publish a snapshot through shared memory

Create `snapshot.mjs`:

```javascript
import {
  Worker,
  isMainThread,
  parentPort,
  workerData
} from "node:worker_threads";

const RESULT = 0;
const READY = 1;

if (isMainThread) {
  const buffer = new SharedArrayBuffer(8);
  const shared = new Int32Array(buffer);

  const worker = new Worker(
    new URL(import.meta.url),
    { workerData: { buffer } }
  );

  worker.once("message", () => {
    console.log("Ready:", Atomics.load(shared, READY));
    console.log("Result:", Atomics.load(shared, RESULT));
  });

  worker.once("error", console.error);
} else {
  const shared = new Int32Array(workerData.buffer);

  Atomics.store(shared, RESULT, 42);
  Atomics.store(shared, READY, 1);

  parentPort.postMessage("published");
}
```

The example performs one publication without modifying the result again.

Its atomic operations make the shared-memory ordering straightforward.

The message indicates that the worker has completed publication; it isn't being used as a substitute for the shared-memory protocol itself.

**Challenge:** What would need to change if the worker reused the same two slots for a continuous stream of new snapshots?

## Lab C — Waiting for a condition

Consider a shared `Int32Array` location containing a ready flag.

A worker may wait while that flag remains zero:

```javascript
while (Atomics.load(shared, READY) === 0) {
  Atomics.wait(shared, READY, 0, 1000);
}
```

The producer can publish and notify:

```javascript
Atomics.store(shared, RESULT, 42);
Atomics.store(shared, READY, 1);
Atomics.notify(shared, READY, 1);
```

Use blocking waits only in an execution context where they are appropriate.

Do not put an indefinite blocking wait on the main event-loop thread.

**Questions:** Why does the consumer check the condition in a loop? What happens if the producer updates the flag before the consumer begins waiting? Why is a notification not itself proof of a particular value?

## Lab D — Diagnose a two-lock deadlock

Imagine this pseudocode:

```text
Worker A:
  acquire(snapshotLock)
  acquire(statsLock)
  update snapshot and statistics
  release(statsLock)
  release(snapshotLock)

Worker B:
  acquire(statsLock)
  acquire(snapshotLock)
  read snapshot and statistics
  release(snapshotLock)
  release(statsLock)
```

Do not execute this as an uncontrolled blocking experiment.

Instead, draw the wait-for relationships that arise when A acquires its first lock and B acquires its first lock before either attempts the second.

Then rewrite both operations using one consistent acquisition order.

**Question:** Why does a consistent lock order prevent this particular circular-wait pattern without necessarily eliminating all possible contention?

## Lab E — Reason about the ABA problem

Consider one atomic state variable.

Its value begins at 5.

Thread A reads 5 and prepares a compare-and-exchange operation.

Thread B changes the value to 9.

Thread B later changes it back to 5.

Thread A performs its conditional update expecting 5.

The comparison succeeds.

**Challenge:** Under what assumptions would this be harmless? Under what assumptions would it violate correctness? Design a versioned state representation that distinguishes the original 5 from a new state that happens to contain the value 5.

## Lab F — False sharing investigation

Design a benchmark with several worker threads, each updating a separate atomic counter.

In the first arrangement, counters occupy nearby locations in the same shared typed array.

In the second, place frequently modified counters far enough apart to reduce the likelihood that they share a hardware cache line.

Measure elapsed time over repeated runs.

Control for worker creation overhead, CPU contention, JIT warmup, and variability.

Do not assume the second layout must always be faster.

**Question:** Why can increasing the distance between independent counters improve performance without changing the number of arithmetic operations?

## Lab G — The senior engineering diagnosis

You are given this hypothetical production evidence:

```text
Service:
  Node.js pricing engine with four worker threads

Shared state:
  SharedArrayBuffer containing:
    hotelId
    roomCount
    price
    readyFlag

Observation:
  readyFlag is written through Atomics.store
  readyFlag is read through Atomics.load
  snapshot fields are updated repeatedly
  consumers sometimes report mismatched field versions

Additional evidence:
  writer begins next snapshot immediately after publishing
  reader has no ownership acknowledgment
  no snapshot-level mutex or versioning protocol exists
```

Prepare a diagnosis that answers:

1. Which parts of the existing implementation are individually correct?
2. Which guarantee is missing?
3. Why doesn't sequential consistency of the flag solve the problem?
4. How could a mutex protect the complete snapshot?
5. How could a versioned handoff or message-passing design remove the conflicting access?
6. What controlled test would prove the proposed fix?

The best answer should identify the ownership and publication protocol, not merely recommend "adding more atomics."

---

# Further Reading

Primary references:

1. MDN — JavaScript Execution Model and Shared Memory  
   https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Execution_model

2. MDN — `Atomics`  
   https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Atomics

3. MDN — `Atomics.wait()`  
   https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Atomics/wait

4. Node.js — Worker Threads  
   https://nodejs.org/api/worker_threads.html

5. Rust Standard Library — Atomic Ordering  
   https://doc.rust-lang.org/std/sync/atomic/enum.Ordering.html

6. C++ Reference — Memory Ordering  
   https://en.cppreference.com/w/cpp/atomic/memory_order

7. Java Language Specification — Threads and Locks  
   https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html

8. Go — The Go Memory Model  
   https://go.dev/ref/mem

Related programme chapters:

- CS220-L03 — Type Systems, Generics, Ownership, and Valid States
- CS220-L07 — Native Runtimes: Go, Rust, and Execution Trade-offs
- CS320-L06 — Concurrency, Event Loops, and Cancellation
- CS320-L08 — Operating-System and Runtime Forensics
- CS430-L05 — Designing Reliable Business Workflows

---

## Dense Cheatsheet — Interview Glance Card

```text
CS320-L07 — THREADS, ATOMICS, AND MEMORY ORDERING

CORE DISTINCTIONS
  Concurrency = overlapping progress
  Parallelism = simultaneous execution
  Logical race != necessarily shared-memory data race
  Thread shares process address space
  SharedArrayBuffer explicitly shares binary memory in JS

THREE GUARANTEES
  Atomicity = indivisible operation under memory model
  Visibility = what writes another thread may observe
  Ordering = required relationships among operations
  One atomic field != atomic multi-field snapshot

LOST UPDATE
  Read 10 -> A calculates 11
  Read 10 -> B calculates 11
  A writes 11; B writes 11
  Expected 12, actual 11
  Use appropriate atomic RMW or synchronization

HAPPENS-BEFORE
  Language-defined ordering, not wall-clock order
  Within-thread relationships + synchronization
  Transitive across related operations
  Release/acquire can publish preceding writes
  Acquire must observe corresponding release value
  Ownership must prevent conflicting later mutation

MEMORY ORDERING
  Relaxed = atomicity without wider publication ordering
  Release = publish preceding writes
  Acquire = consume matching publication
  AcqRel = combined effects for suitable RMW operations
  SeqCst = stronger total order for relevant atomics
  Strong ordering != multi-field transaction

JAVASCRIPT
  Atomics are sequentially consistent
  No explicit Relaxed/Acquire/Release selector
  Atomics.load/store/add/compareExchange
  SharedArrayBuffer + typed arrays share binary state
  Ordinary shared accesses have different semantics
  Atomic ready flag != safe reusable buffer automatically

WAIT / NOTIFY
  Atomics.wait can block suitable worker contexts
  Atomics.notify requests wakeup
  Check shared predicate in loop
  Notification != proof condition true
  Blocking main event-loop thread is inappropriate

MUTEX
  Mutual exclusion for protected critical section
  All relevant accesses must obey same lock
  Protect WHOLE invariant, not just one field
  Long lock hold -> contention/latency
  Mutex ownership differs from generic semaphore permits

CONDITION VARIABLE
  Check predicate under mutex
  Wait atomically releases mutex
  Wake reacquires mutex
  Recheck predicate after waking
  Spurious wakeups / competing consumers possible

DEADLOCK
  A holds X, waits Y
  B holds Y, waits X
  Circular wait prevents progress
  Consistent lock acquisition order can prevent pattern
  Deadlock != ordinary lock contention
  Priority inversion can delay lock holders

CAS
  Compare current with expected; conditionally replace
  Failed CAS may require retry
  Retries create contention under load
  ABA: A -> B -> A fools history assumptions
  Version tagging can distinguish states

LOCK-FREE
  System-wide progress guarantee under model
  Individual thread may starve
  Wait-free = stronger bounded individual progress
  Lock-free != always faster
  Memory reclamation is difficult

FALSE SHARING
  Independent variables share physical cache line
  Cache-coherence traffic hurts performance
  Not necessarily data race
  Alignment/padding can help, measure first

LANGUAGE DIFFERENCES
  Rust: ownership + Send/Sync + explicit atomic orderings
  Java: happens-before, volatile, synchronized, atomics
  Go: channels, mutexes, sequentially consistent atomics
  JS: SharedArrayBuffer + sequentially consistent Atomics
  Different APIs; same ownership/synchronization questions

MESSAGE PASSING
  Prefer explicit ownership when practical
  Clone/transfer/message instead of shared mutation
  Costs: copies, queues, ordering and lifecycle
  Message passing isn't automatic business correctness

THREE ATOMICITY SCOPES
  Atomic memory access
  Consistent local application state
  Distributed durable business invariant
  Local Atomics cannot protect PostgreSQL across replicas

DIAGNOSTIC FRAMEWORK
  1. Identify actual shared memory
  2. Map readers/writers
  3. Identify protected invariant
  4. Establish synchronization/happens-before
  5. Examine reuse and object lifetime
  6. Control dangerous interleavings in tests
  7. Prefer simple primitives and verify performance

SENIOR INTERVIEW ANSWER
  "I'd identify which memory is actually shared, define the
   invariant and ownership protocol, establish synchronization
   and happens-before relationships, and choose the simplest
   primitive protecting the entire state transition. Atomics
   protect individual operations; they don't automatically
   make a complex workflow correct."

MENTAL MODEL
  Who owns the data?
  Which operation is indivisible?
  How is completed state published?
  Which boundary does the guarantee actually protect?
```
