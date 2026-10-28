---
id: CS220-L04
course: CS220
title: "References, Garbage Collection, and Memory Leaks"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: [CS101-S07]
prev: CS220-L03
next: CS220-L05
---



# CS220 — Languages, Types, Memory, and Runtimes

## Lecture 04: References, Garbage Collection, and Memory Leaks

*The garbage collector is running. Memory is being reclaimed. The application has no obvious infinite loop. Yet its memory consumption grows relentlessly until the process dies. How can a perfectly functioning garbage collector allow a memory leak?*

---

# Part I — Intuition

## The picture to carry in your head

Imagine a hotel-booking platform running in Node.js.

One service retrieves customer profiles. It combines information from PostgreSQL, reservation history, loyalty preferences, and external providers.

Each profile request involves several database queries, so the team introduces a cache.

The results are impressive.

Repeated profile requests become faster. Database load falls. Customers notice more responsive pages.

Then something peculiar happens.

At 09:00, the service uses approximately 150 megabytes of memory.

By noon, it uses 500 megabytes.

By late afternoon, the process is approaching its configured memory limit.

Eventually, a container is terminated and restarted.

Everything returns to normal.

For a few hours.

Then the same pattern repeats.

The on-call engineer suspects a garbage-collection defect.

"Node.js must be forgetting to clean up its objects."

But the garbage collector might be behaving exactly as intended.

To understand why, we need to think about what memory management actually promises.

## 1. Memory is a building full of rooms

Imagine a large office building.

Each room contains files, furniture, and equipment.

Employees are constantly bringing new objects into the building.

Some objects are temporary.

Others are supposed to remain for years.

A maintenance team regularly removes things that are no longer accessible or owned by anyone in the organization.

Now imagine that one department keeps a registry of every customer file ever created.

Even after customers leave, the registry continues listing their files as active.

The maintenance team sees that registry.

It concludes that the files are still needed.

So it leaves them alone.

The building fills up.

Is the maintenance team broken?

Not necessarily.

It is following the information available to it.

The problem is that the department continues claiming ownership of objects it no longer needs.

A garbage collector works through a related idea.

It identifies objects that are still reachable through the running program's references.

It can reclaim objects that are no longer reachable.

But it cannot automatically decide that a reachable customer profile is no longer useful to the business.

**Reachable and useful are two different properties.**

## 2. A variable isn't necessarily the object itself

Imagine a function that creates a customer profile.

The profile contains a name, preferences, and a list of recent reservations.

The function returns the profile.

The caller stores it in a variable.

When that variable is later assigned another value, what happens to the original profile?

It depends on whether anything else still references it.

If no relevant references remain, the profile may become eligible for garbage collection.

But perhaps the profile was also inserted into a global Map.

The variable can disappear.

The function can return.

The HTTP request can finish.

The Map still refers to the profile.

From the garbage collector's perspective, the profile remains alive.

The important mental shift is to stop imagining that an object's lifetime necessarily belongs to the function that created it.

An object can outlive its creator.

Its lifetime depends on the references and ownership relationships that remain.

## 3. The stack and heap play different roles

Programming languages and runtime implementations organize execution state in different ways.

Two concepts are particularly useful.

The **call stack** tracks active function execution, including information required to resume callers and manage local execution state.

The **heap** provides storage for dynamically allocated objects whose lifetime isn't necessarily tied to one active function call.

These are conceptual categories, not promises that every JavaScript value is stored in one particular physical memory location.

Modern engines optimize representation and allocation aggressively.

But the distinction helps us reason about lifetime.

A function can create an object, return a reference to it, and finish.

The stack frame associated with that function is no longer active.

The object can remain reachable through the returned reference.

Now add a cache that retains another reference.

The object can survive long after the original request ends.

## 4. The cache that remembers too much

Our service has a Map containing customer profiles.

The cache keys are customer identifiers.

Every time the application encounters a new customer, it stores the assembled profile.

A later request for that customer can reuse the cached result.

This is useful—until we ask what causes a cache entry to disappear.

Nothing.

There is no expiration policy.

No maximum capacity.

No eviction strategy.

The cache doesn't distinguish frequently used customers from those who haven't visited in months.

Every new customer increases the retained population.

The garbage collector can repeatedly examine this structure.

It still cannot reclaim the profiles because the Map continues referring to them.

This is a memory leak in the application sense.

The runtime is preserving data the program says is reachable.

The application has failed to define when that data should stop being retained.

## 5. Closures and listeners can make ownership invisible

Caches are an obvious way to retain objects.

Other references are harder to notice.

A callback may capture an object through its closure.

An event listener may remain registered after the operation that created it has finished.

A timer may continue referring to data that is no longer relevant.

An unresolved background operation may preserve state while waiting.

The visible request ends, but some other component continues holding a reference.

This makes memory leaks feel mysterious.

The code that allocated the large object may be perfectly reasonable.

The real problem may be a small callback registration elsewhere.

The correct investigation must discover **what still holds the object alive**, not merely where it was created.

## 6. More memory does not automatically mean a leak

Now imagine that the service begins processing a large batch of requests.

Memory usage rises.

Later, the batch completes.

The garbage collector eventually reclaims many objects.

The runtime may retain previously acquired memory for future allocations rather than immediately returning it to the operating system.

A monitoring dashboard may therefore show elevated process memory even after the workload has quieted.

That is not necessarily a leak.

Likewise, a cache that fills to a fixed maximum and then remains approximately stable may be operating as designed.

The difference is whether the amount of retained memory continues growing in a way that isn't justified by the application's intended state.

### Visual anchor — three memory patterns

```text id="n4m01"
TEMPORARY ALLOCATION

Memory
  |       /\       /\
  |      /  \_____/  \____
  +------------------------> Time


BOUNDED CACHE

Memory
  |        _____________
  |       /
  |______/
  +------------------------> Time


UNBOUNDED RETENTION

Memory
  |                  /
  |              ___/
  |          ___/
  |______ __/
  +------------------------> Time
```

These are conceptual shapes. Real memory metrics fluctuate, garbage collection is asynchronous, and the observed process memory may not match any one sketch exactly.

## The minute-long mental replay

An application allocates objects.

Other objects, variables, closures, collections, and runtime structures can retain references to them.

A garbage collector determines which objects are reachable.

Objects that are unreachable can eventually be reclaimed.

Objects that remain reachable are ordinarily preserved, even when the business no longer needs them.

A cache without eviction can therefore leak memory while garbage collection works correctly.

The same applies to callbacks, event listeners, timers, and growing queues.

And memory measurements must be interpreted carefully: JavaScript heap usage is not identical to total process memory.

### Three questions before the Deep Dive

1. How can a request finish while an object created during that request remains alive?
2. Why can't a garbage collector automatically delete an obsolete entry from a Map?
3. Why doesn't a rising process-memory graph alone prove a memory leak?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The Server That Was Slowly Eating Itself

At 03:42, an alert wakes the on-call engineer.

A Node.js customer-profile service has restarted for the third time this week.

The application runs in a container with a fixed memory budget.

Its request rate is ordinary. CPU usage is not remarkable. PostgreSQL is healthy.

Yet the service's memory usage has been growing for hours.

The team restarts it manually.

Memory consumption falls.

The application begins serving requests normally.

This seems to confirm that the problem is inside the Node.js process.

But it tells us little about the mechanism.

It could be retaining JavaScript objects.

It could be accumulating Buffers.

It could have a growing queue of outstanding work.

A native dependency might be retaining memory outside the ordinary JavaScript heap.

Or the process might have changed its working set and be legitimately holding more data.

The fact that a restart reduces memory consumption is consistent with many explanations.

We need a more precise model.

## 2. The Call Stack: Execution State Has a Lifetime

Imagine a function called `handleRequest`.

It invokes `loadProfile`.

That function invokes `queryReservations`.

When the database query completes, execution returns to `loadProfile`.

Eventually, the assembled profile is returned to `handleRequest`.

This familiar nested execution can be modeled as a call stack.

A function call establishes an execution context containing information needed to perform the call and eventually resume its caller.

The runtime may maintain local execution state, return information, and other implementation-specific structures.

### Why stacks are useful

A stack follows a last-in, first-out relationship.

The most recently entered function returns before its caller can complete.

This matches ordinary nested function execution.

Stack allocation and stack-frame management can be efficient because their lifetimes follow a structured pattern.

But JavaScript execution introduces complications.

Functions can return closures.

Asynchronous functions can suspend and resume.

Runtime implementations can optimize frames, inline functions, or represent state differently.

Therefore, don't imagine every local variable as a neat physical box on one permanent stack.

The stack is a useful model of active execution, not a complete map of every byte used by a JavaScript runtime.

### Recursion and stack exhaustion

Consider a recursive function calling itself repeatedly without reaching a terminating condition.

Each additional call may require more execution state.

Eventually, the runtime reaches a call-stack limit and throws an error such as `RangeError: Maximum call stack size exceeded`.

This is distinct from the ordinary memory leak we are investigating.

A recursive function can exhaust its call stack without retaining millions of heap objects.

Conversely, a service can retain enormous amounts of heap data while its current call stack is shallow.

The type of memory pressure matters.

## 3. The Heap: Objects Can Outlive Functions

The heap is a major region of memory used for dynamic allocations.

JavaScript engines commonly allocate ordinary objects and arrays using managed heap structures.

The implementation may optimize some allocations, eliminate unnecessary objects, or store certain values in special representations.

But for application reasoning, the important point is that object lifetime isn't necessarily bound to one function invocation.

Suppose `loadProfile` constructs an object containing customer information and returns it.

Its caller can retain that object.

Another function can store the reference in a Map.

A callback can capture it.

A Promise continuation can retain it.

The original function has completed, but the object remains accessible.

### Variables and objects are not identical things

A variable can refer to an object.

Several variables can refer to the same object.

Reassigning one variable doesn't necessarily destroy the object or affect the other references.

This is the aliasing model we encountered in CS220-L03.

Now we're interested in its memory consequences.

If any relevant path from a live program root still reaches the object, the garbage collector ordinarily treats the object as live.

### The reference graph

Imagine each object as a node in a graph.

References are directed edges.

A Map points to its entries.

An entry points to a customer profile.

That profile points to a reservation array.

Each reservation may point to nested metadata.

The entire reachable graph can be retained through one seemingly modest reference.

This is why a single Map entry can account for far more memory than the Map's key and value pointers.

## 4. Garbage Collection: Reachability Is the Contract

A garbage collector manages memory according to its implementation's rules.

Many JavaScript garbage collectors fundamentally reason about object reachability.

They begin with roots.

Roots may include relevant execution state, runtime-managed references, and other values known to be live.

The collector traces references from those roots.

Objects reachable through the resulting graph are considered live for collection purposes.

Unreachable objects can be reclaimed.

### Mark and sweep

A simplified tracing collector can be described in two phases.

First, mark objects reachable from roots.

Second, reclaim allocations that weren't marked.

Real collectors use considerably more sophisticated machinery, but the underlying concept remains useful.

### What the collector cannot know

Return to our customer cache.

The Map remains reachable because it belongs to a long-lived application module.

The Map references every cached profile.

Therefore, the profiles remain reachable.

The collector does not know that a particular customer hasn't logged in for six months.

It doesn't know that their profile is now stale.

It doesn't know that PostgreSQL could regenerate the result.

Those are application facts.

The runtime's memory-safety goal is not to guess whether cached information remains economically valuable.

It preserves reachable objects according to its collection semantics.

### The crucial distinction

A **garbage-collection failure** would involve the collector violating its own memory-management behavior.

An **application memory leak** can exist even when the collector behaves correctly.

The application continues retaining objects that are no longer useful.

Most practical Node.js memory leaks belong to the second category.

## 5. The Actual Bug: An Unbounded Customer Cache

Let's inspect the service's cache.

The developer introduced a module-level Map:

`const customerCache = new Map<string, CustomerProfile>()`

Whenever a customer profile is requested, the application checks the Map.

If a profile exists, it returns the cached result.

Otherwise, it queries the database, constructs the profile, and inserts it into the Map.

This is a perfectly reasonable optimization in principle.

But consider a busy SaaS application serving hundreds of thousands of customers.

Every distinct customer adds another entry.

The cache has no upper bound.

It has no expiration.

It has no eviction.

### Why this can remain invisible for weeks

In development, the application sees only a few customers.

The cache remains tiny.

In staging, integration tests repeatedly use the same handful of test accounts.

The cache still remains small.

In production, new customer identifiers arrive continuously.

The retained population grows.

A load test that repeatedly uses one test account may fail to reproduce the problem, even when it generates enormous request volume.

This reveals a fundamental testing distinction.

**Request count and distinct-key cardinality aren't the same workload characteristic.**

If memory growth depends on the number of unique customer IDs, a test using one customer can completely miss the failure.

### The retention chain

The source of retention is the Map.

The Map references a profile object.

The profile references nested reservations and metadata.

The total retained graph grows as new entries are inserted.

The garbage collector preserves the graph because it remains reachable.

### The correct fix isn't necessarily removing the cache

Caching may still provide valuable performance benefits.

We need to establish a retention policy.

A cache may have a maximum entry count.

It may expire values after a bounded lifetime.

It may evict least-recently-used entries.

It may include a memory budget rather than only an entry count.

It may store smaller projections instead of entire customer profiles.

The correct policy depends on object size, request distribution, freshness requirements, and acceptable database load.

### Entry count versus memory budget

Imagine a cache limited to one thousand entries.

One customer profile contains two reservations.

Another contains ten thousand.

A fixed entry count doesn't guarantee a fixed memory footprint.

A production cache with highly variable values may need a size-aware eviction strategy.

This is a reminder that cardinality, memory consumption, and usefulness are related but distinct dimensions.

## 6. Eviction, Expiration, and Staleness

A cache must answer two questions.

When should an entry stop being useful?

When should it stop occupying memory?

These questions overlap, but they aren't identical.

### Time-to-live

An entry may expire after a defined period.

This limits how long the cache considers it fresh.

But an implementation that merely marks entries expired without promptly removing them can still retain significant memory.

Some caches delete expired entries lazily when they're accessed again.

If old entries are never accessed, they may remain allocated unless another cleanup mechanism exists.

Therefore, a TTL is not automatically a hard memory limit.

### Least-recently-used eviction

An LRU cache gives preference to entries used recently.

When capacity is reached, it removes less recently used entries.

This can work well when recently accessed data is more likely to be requested again.

But not every workload has that property.

A large one-time scan may churn through many unique records and evict useful hot entries.

The eviction policy should reflect actual access patterns.

### Freshness and security

Customer profiles are not ordinary public reference data.

A cached profile may become stale after an account update.

Authorization rules may change.

A customer may lose access to a particular organization.

Therefore, even a memory-bounded cache can be incorrect if its invalidation and authorization semantics are wrong.

A cache key based only on customer ID may be insufficient when the result also depends on tenant, permissions, or selected fields.

Memory management and data correctness intersect here.

The caching strategy must satisfy both retention and business-access requirements.

## 7. Closures: An Invisible Retention Path

Now suppose the report generator creates a large report object.

It registers a callback that will notify someone when the report is viewed.

The callback refers to the report.

The callback is then stored in a long-lived registry.

The function that created the report finishes.

The report remains reachable.

Why?

Because the stored callback retains access to relevant variables from its lexical environment.

Those references can keep objects alive.

### A closure isn't inherently a leak

Closures are ordinary and useful JavaScript mechanisms.

They allow functions to remember configuration and state.

They make callbacks, factories, and encapsulated state possible.

The problem arises when a closure remains reachable longer than intended.

Suppose the notification registry should remove its callback when the report is finalized.

If it never does, the callback may remain registered indefinitely.

The objects it retains can also remain alive.

### Retain only what the callback needs

Imagine the callback only needs a report ID.

But it captures the entire report object, including a large attachment buffer and a list of findings.

A smaller design would capture only the stable identifier.

When invoked, the callback can look up the necessary current information through an appropriate service.

This may reduce retention.

But it introduces an external lookup and its associated failure semantics.

The design trade-off should be explicit.

### The hidden architectural question

When creating a callback, ask:

Who owns it?

How long should it remain registered?

What data does it retain?

Who removes it?

Those questions are often more useful than merely recognizing that the callback is a closure.

## 8. Event Listeners: The Leak That Hides in Plain Sight

JavaScript applications frequently use events.

Node.js provides `EventEmitter`.

Browsers provide event targets and event listeners.

Frameworks such as Vue and React manage component lifecycles with their own patterns.

Consider a Node.js service subscribing to a shared event emitter whenever a report starts.

The listener captures the report's metadata.

When the report finishes, the application forgets to remove the listener.

The shared emitter remains alive.

Its listener collection grows.

Each listener may retain a closure and the data reachable through it.

### Why a listener is a strong reference

Registering a callback usually means that the event source retains the callback.

As long as that event source remains reachable and the callback remains registered, the callback remains reachable.

Its captured data may remain reachable too.

The request that created the listener can finish without changing that relationship.

### The EventEmitter warning

Node.js commonly warns when more than ten listeners are added for one event on an EventEmitter, unless the listener limit is adjusted.

This can be a useful diagnostic signal.

But it isn't proof of a memory leak.

Some applications legitimately have many listeners.

And a leak can exist with far fewer than ten listeners per event.

Increasing the listener limit to silence a warning doesn't repair an unintended retention path.

The correct investigation asks whether listeners are accumulating and whether their lifetime matches the intended design.

### Explicit cleanup

A listener registered for a temporary operation should normally have an appropriate removal path.

For example, the application may unregister it when the operation ends.

A one-time listener may be suitable when the expected event occurs exactly once and cleanup is otherwise handled.

But even one-time registration needs lifecycle reasoning if the event may never occur.

A listener waiting forever for an event that never arrives can remain registered indefinitely.

### Frontend relevance

The same problem occurs in frontend components.

A component registers a global window listener.

The component unmounts.

The listener remains active and retains state associated with the old component.

Repeated navigation creates additional listeners.

The browser has garbage collection.

The component can still leak memory because a long-lived event source retains its callback.

The pattern is the same as the Node.js incident, despite a different host environment.

## 9. Timers, Promises, and Background Operations

Not every retained object sits inside a Map or event emitter.

Timers can retain callbacks.

Callbacks can retain captured data.

Outstanding operations may retain closures, buffers, or other state needed for eventual completion.

Suppose a worker starts a timeout for every request.

The timeout callback captures the entire request object.

The request finishes, but the timer is not cleared.

Until the timer fires or is cancelled, the associated callback and captured state may remain reachable.

### A Promise is not automatically a leak

An unresolved Promise doesn't necessarily consume large amounts of memory by itself.

The concern is what remains reachable through its surrounding execution and bookkeeping.

A pending operation managed by a long-lived queue or registry may retain large data.

A Promise created and then abandoned without remaining references may not create the same retention problem.

The important question is the reference graph.

### A queue is a memory-retention mechanism

Imagine a scanner worker receiving tasks faster than it processes them.

The application stores pending tasks in an in-memory queue.

Each task includes a large payload.

If new tasks arrive at a sustained rate higher than completion rate, the queue grows.

For example, if thirty new tasks arrive per second and only twenty-five complete, the backlog increases by five per second.

That's eighteen thousand additional tasks per hour.

If each pending task retains 20 KiB of data, the backlog alone represents hundreds of mebibytes after an hour, before overhead.

This isn't necessarily an accidental reference leak.

The application may be intentionally keeping all pending tasks.

But the result is the same: unbounded memory demand.

### The proper remedy

The system needs bounded admission, backpressure, load shedding, or durable external queuing according to its business requirements.

Increasing the garbage-collection frequency won't solve a queue whose live data population is growing faster than work completes.

The collector can't discard pending tasks that the application still requires.

This connects memory management to queueing and system capacity.

## 10. How Generational Garbage Collection Works

We've treated garbage collection as a reachability problem.

Now let's examine why modern engines don't simply stop the program and scan every object after each allocation.

Most application objects are short-lived.

A request constructs temporary arrays, strings, and intermediate objects.

The response is generated.

Many of those objects become unreachable quickly.

Garbage collectors can exploit this pattern.

V8 uses generational garbage collection, among other sophisticated mechanisms.

### Young generation

New objects typically begin in a young generation.

This region is designed for allocations that are likely to die quickly.

A minor collection can reclaim unreachable young objects efficiently.

Objects that survive enough collection cycles may be promoted into older regions.

The exact implementation changes over time, so avoid treating a particular V8 heap layout as an eternal specification.

The underlying principle is that short-lived and long-lived objects have different collection characteristics.

### Old generation

Long-lived objects occupy older heap regions.

A full or major collection involves more substantial work to discover and reclaim unreachable objects across relevant areas of the heap.

Modern V8 uses techniques including incremental, concurrent, and parallel garbage-collection work to reduce pauses and improve throughput.

But garbage collection still consumes resources.

It uses CPU time.

It can require additional memory.

And some work may pause application execution.

### Why the cache is especially costly

The unbounded customer cache doesn't merely retain memory.

Its entries survive collections and tend to become long-lived objects.

As the retained graph grows, the collector has more live state to account for.

Major collection work can become increasingly expensive.

The application may experience memory pressure and garbage-collection overhead simultaneously.

This is why an application that retains unnecessary data can suffer latency problems long before it reaches a memory limit.

### What GC optimization cannot do

A faster collector can reduce certain overheads.

It cannot make reachable objects disappear without violating its semantics.

Changing GC flags is therefore not the first response to an application that retains an ever-growing Map.

Fix the retention behavior before trying to tune the collector around it.

## 11. Allocation Rate Versus Retained Size

Memory behavior has at least two useful dimensions.

**Allocation rate:** How quickly does the program create new objects?

**Retained size:** How much allocated data remains reachable over time?

These are different.

Imagine a function that creates a thousand temporary objects per request.

Most become unreachable immediately.

The allocation rate may be high, producing garbage-collection work.

But the retained population may remain small.

Now imagine another function that allocates just one profile per request and stores it permanently in a Map.

The allocation rate might be lower.

But the retained population grows continuously.

### Why this distinction matters for performance

A high allocation rate can increase GC frequency and CPU overhead.

A high retained population increases memory demand and can increase the cost of collecting long-lived heap regions.

A workload may suffer from one problem, both, or neither.

The correct optimization depends on evidence.

### Avoid allocation superstition

Developers sometimes try to eliminate every object allocation.

That can make code complicated without improving meaningful performance.

Modern JavaScript engines are designed to handle many short-lived allocations efficiently.

An extra small object in a noncritical code path may be irrelevant.

Conversely, retaining a large object graph indefinitely can be disastrous.

Measure the actual workload.

Optimize for observed cost, not aesthetic discomfort with allocation.

## 12. Heap Memory Is Not Total Process Memory

Now return to the monitoring dashboard.

The process appears to use 900 MiB of memory.

A developer logs `process.memoryUsage().heapUsed`.

It reports only 250 MiB.

"Where did the other memory go?"

This isn't necessarily a contradiction.

Node.js exposes several memory measurements.

They describe related but different parts of process memory.

### `heapUsed`

This represents memory currently used within V8's managed heap accounting.

It's important when investigating ordinary JavaScript object retention.

But it is not the entire process footprint.

### `heapTotal`

This describes the amount of memory currently allocated for the relevant V8 heap spaces, not simply the useful payload inside them.

It can exceed `heapUsed`.

The difference doesn't necessarily indicate a leak.

The runtime may reserve or maintain heap capacity for future allocations.

### `external`

This reports memory associated with certain objects and allocations outside the ordinary V8 JavaScript heap.

Native resources and backing stores can contribute to this category.

### `arrayBuffers`

This measures memory associated with ArrayBuffers and SharedArrayBuffers, including Node.js Buffers, under Node's reporting semantics.

It is included within `external`, so don't add the two together as though they were independent categories.

### `rss`

Resident Set Size describes the process's resident memory footprint.

It includes more than the ordinary JavaScript heap, such as code, stacks, native allocations, and other resident pages.

It isn't simply `heapUsed + external`.

These metrics have overlapping and implementation-dependent accounting boundaries.

### A useful investigation

If `heapUsed` grows substantially with each batch of unique customer profiles, JavaScript object retention becomes a strong hypothesis.

If `arrayBuffers` and `external` grow while ordinary heap usage remains relatively stable, investigate Buffer-backed data and native memory relationships.

If RSS rises while the other measurements remain comparatively stable, consider allocator behavior, native allocations, fragmentation, and other process-memory components.

These observations narrow the investigation.

None alone proves a particular leak.

## 13. The Buffer Leak Outside the Ordinary JavaScript Heap

Imagine that our service downloads large files from external providers.

For convenience, the developer stores completed downloads in an array of Node.js Buffers.

The application later needs only a small summary of each file.

But the original Buffers remain in the array.

This can produce substantial memory retention without a proportional increase in ordinary V8 heap usage.

### Buffer objects and backing memory

A Node.js Buffer is represented through JavaScript-accessible objects, but its data storage is accounted for in ways that differ from ordinary JavaScript object fields.

Large Buffer backing stores can increase `arrayBuffers` and `external` measurements.

The JavaScript wrapper may be small compared with the data it keeps alive.

A heap snapshot can help identify references that retain Buffer objects, but it may not present external backing-store memory as if it were ordinary JavaScript object fields.

### The misleading fix

An engineer sees low `heapUsed` and concludes there is no memory problem.

They increase the container memory limit.

The application survives longer.

But the array continues retaining downloaded files.

The underlying design remains unbounded.

A better approach may process files incrementally, retain only required summaries, or store durable artifacts externally.

The correct strategy depends on whether the original bytes must remain available.

**When process memory grows, determine which memory category is growing before deciding what to optimize.**

## 14. Growing Memory Isn't Always Leaking Memory

Suppose a Node.js process begins at 150 MiB RSS.

After sustained load, it reaches 400 MiB.

The workload quiets down.

RSS remains near 400 MiB.

Is this a leak?

Not necessarily.

A runtime or memory allocator may retain previously acquired memory for future reuse.

The heap may have grown to support peak demand.

Garbage collection may have reclaimed objects without immediately returning all underlying memory pages to the operating system.

Similarly, caches may intentionally warm up.

A service may legitimately retain a fixed set of frequently used records.

### Look at the post-collection baseline

For ordinary JavaScript heap investigations, a useful signal is whether the amount of live data after comparable garbage-collection cycles continues increasing.

Imagine a sawtooth graph.

Heap usage rises as objects are allocated.

Collection reclaims unreachable data.

Usage falls.

If the post-collection baseline keeps climbing under a comparable workload, something may be accumulating.

But even this is not universal proof of a bug.

The application may be building a legitimate in-memory index.

The question is whether retained growth matches an intended bounded state.

### Working-set changes

Suppose the service begins handling more unique customers.

Its cache fills.

Eventually it reaches a configured limit and stabilizes.

This can be correct.

Memory rises during warmup but doesn't continue increasing indefinitely.

An unbounded cache, by contrast, has no natural ceiling imposed by its policy.

This is why the shape of memory growth over a representative workload matters more than a single snapshot.

## 15. Diagnosing the Leak: Build Competing Hypotheses

We now have several possible explanations for rising memory.

An unbounded customer cache.

Accumulating event listeners.

Callbacks retaining report objects.

Growing in-memory queues.

Buffer-backed downloads.

Allocator behavior.

Legitimate cache warmup.

Which one is responsible?

The investigation should begin with measurements and predictions.

### Hypothesis A: unbounded Map

Prediction: memory retention should correlate strongly with the number of distinct customer identifiers processed.

Repeating requests for existing customers should produce much less additional retained state.

### Hypothesis B: listener accumulation

Prediction: the number of registered listeners should grow as relevant operations execute, particularly if their cleanup paths are missing.

Retained callbacks may reference completed requests or report data.

### Hypothesis C: pending queue growth

Prediction: memory consumption should correlate with the number and size of outstanding tasks.

If work completion catches up with arrivals, the retained queue should shrink.

### Hypothesis D: Buffer retention

Prediction: `arrayBuffers` and related external-memory measurements may grow disproportionately compared with ordinary JavaScript heap usage.

### Hypothesis E: runtime memory reuse

Prediction: after a representative warmup, memory usage may reach a stable plateau even as requests continue.

The retained object population should not grow without bound.

The point of having hypotheses is to make the next experiment informative.

A heap snapshot is useful only when you know what you're looking for and how to interpret the result.

## 16. Heap Snapshots: Find Who Keeps the Object Alive

Node.js supports V8 heap snapshots.

A snapshot captures information about the JavaScript heap and relationships among objects at a particular moment.

It can help identify retained objects and the references keeping them reachable.

A common workflow compares snapshots taken before and after a representative workload.

### A safe investigative sequence

Start a disposable local or staging instance.

Let it complete ordinary initialization.

Exercise the relevant endpoint until the system reaches a meaningful baseline.

Capture a heap snapshot.

Then execute additional requests that represent the suspected leak-producing workload.

Capture another snapshot.

Compare the object populations and retained paths.

The goal is to identify which objects accumulated and which references continue keeping them alive.

### Shallow size versus retained size

An object's shallow size describes memory directly associated with that object under the profiler's accounting.

Its retained size estimates the amount of memory that would become eligible for reclamation if that object and its exclusive retention relationships were removed, under the snapshot's reachability analysis.

A small Map entry may have a modest shallow size while retaining an enormous graph of customer profiles, arrays, and nested metadata.

The retained graph is often more important than the visible size of one object.

### Follow the retaining path

Suppose a snapshot shows a large collection of customer profiles.

Finding those objects isn't enough.

Why are they still alive?

The retaining path might lead from:

A runtime root to a module environment.

From the module environment to the customer cache.

From the cache to profile objects.

From the profiles to reservation arrays.

That chain identifies the ownership mistake.

The fix belongs at the cache retention policy, not necessarily at the profile constructor.

### A production safety warning

Taking a heap snapshot can pause the application's main thread and consume substantial additional memory.

On a large heap, the process may become unresponsive or crash.

Snapshots can also contain sensitive application data.

Use controlled environments or explicitly approved production procedures.

Avoid exposing an inspector endpoint publicly.

The objective is to diagnose a leak, not create a new production incident or data-exposure problem.

## 17. WeakMap: Metadata Without Owning the Key's Lifetime

JavaScript provides `WeakMap`.

It resembles a Map in that it associates keys with values.

But it has an important difference.

A WeakMap does not keep its object keys alive solely because they are present as keys.

When a key becomes unreachable through other relevant references, its WeakMap association does not prevent the key from being collected.

This makes WeakMap useful for metadata associated with objects whose lifetime should be determined elsewhere.

### A typical use

Imagine an application attaching cached metadata to a DOM element or a particular in-memory object.

The metadata should exist while that object exists.

When the object is no longer used, the application doesn't want a separate metadata registry to preserve it forever.

A WeakMap can express that relationship.

### Why WeakMap isn't a universal cache solution

Our customer cache uses string identifiers as keys.

A WeakMap cannot simply replace that ordinary string-keyed Map.

WeakMap keys must be of supported weakly held key types, principally objects.

Also, WeakMap does not expose ordinary enumeration of its entries.

The program cannot rely on observing exactly which entries remain alive, because garbage collection timing isn't deterministic.

This makes WeakMap inappropriate for many caches that require explicit capacity management, iteration, expiration policies, or statistics.

### Finalization isn't normal cleanup

JavaScript also provides WeakRef and FinalizationRegistry mechanisms.

These can support specialized memory-sensitive designs.

But garbage collection and finalization timing are nondeterministic.

A finalizer may not run before process exit, and an application must not depend on it for critical correctness or timely resource release.

Don't use finalization as a substitute for explicit cleanup of sockets, files, timers, or business resources.

**Weak references can change retention relationships. They do not create reliable lifecycle scheduling.**

## 18. Streaming and Bounded Work: The More Important Performance Fix

Suppose our service processes a large customer export.

One implementation loads all one million records into memory before doing anything.

Another reads records in bounded batches.

The second approach may keep a much smaller working set.

It doesn't require the entire dataset to remain live simultaneously.

### Why streaming helps

A streaming design can process a piece of data, write the result, and release references before reading much more input.

This reduces peak retained memory when implemented with appropriate backpressure.

But merely using an API named `stream` doesn't guarantee bounded memory.

If the consumer stores every emitted record in an array, memory still grows.

If the producer outruns the consumer and buffering is unbounded, memory still grows.

The application must actually limit retained work.

### Memory and latency

A smaller working set can improve garbage-collection behavior and reduce resource pressure.

But it may also increase per-item overhead or complicate processing.

Batch size is a trade-off.

Very large batches increase memory demand.

Tiny batches can create excessive network round trips or processing overhead.

The correct size depends on workload measurements.

### When caching and streaming meet

Sometimes the right design is to cache summaries instead of complete datasets.

For example, rather than storing every reservation object for each customer, the application might cache a small derived profile and retrieve full history on demand.

This reduces retained memory while preserving much of the performance benefit.

The deeper optimization is to ask:

What information must remain immediately available?

What can be recomputed?

What can be fetched again?

What should be stored durably elsewhere?

Memory management becomes easier when data lifetime follows business requirements explicitly.

## 19. Why More Memory Isn't Always the Right Fix

Imagine the unbounded cache causes the service to exceed its container's memory limit.

An engineer proposes doubling that limit.

Would the problem disappear?

Not permanently.

The application would have more room to retain unnecessary profiles.

If the incoming distinct-key population remains unbounded, the same failure may return later.

Increasing memory can be an appropriate temporary mitigation when it reduces immediate customer impact.

But it doesn't repair the retention policy.

### JavaScript heap limits versus container limits

Node.js can be configured with V8 heap-size options, such as `--max-old-space-size`.

These influence the JavaScript heap's configured memory budget.

They do not directly represent the complete process-memory footprint.

External allocations, Buffers, stacks, code, and other native memory still matter.

Similarly, a container's memory limit is a separate operating-system resource boundary.

A process may encounter a V8 heap allocation failure before reaching a container memory limit.

Or it may be terminated under container memory enforcement even when ordinary JavaScript heap usage appears comparatively modest.

We'll examine virtual memory, cgroups, and OOM behavior in CS320.

For this course, the important lesson is that memory budgets exist at several layers.

Increasing one budget doesn't make unbounded retention correct.

## 20. Reconstructing the Production Incident

Let's close the investigation.

The team collects memory metrics over several hours.

Ordinary JavaScript heap usage grows steadily.

The number of unique customer profiles processed also grows.

Repeating requests for existing customers produces relatively little additional retained growth.

A controlled staging reproduction generates thousands of distinct customer identifiers.

The heap grows.

A snapshot comparison shows increasing numbers of customer-profile objects.

The retaining paths lead to one module-level Map.

The Map has no capacity limit or eviction policy.

We have our cause.

### The fix

The team replaces the unbounded cache with a deliberately bounded implementation.

It establishes a maximum memory budget and an appropriate eviction policy.

It defines freshness and invalidation requirements for customer data.

It avoids retaining large reservation histories when a compact summary is sufficient.

The revised service is tested with representative distinct-key traffic rather than repeatedly requesting one customer.

The post-warmup retained heap stabilizes under the expected workload.

Memory consumption remains within the intended resource budget.

The original performance benefit is largely preserved.

### The lesson

The garbage collector wasn't broken.

The customer-profile constructor wasn't inherently broken.

The database wasn't responsible.

The container runtime wasn't leaking memory.

The application had created a retention policy without an exit condition.

The correct fix was to change which data the application continued claiming ownership of.

That is why **memory leaks are often ownership and lifecycle problems disguised as allocation problems**.

## 21. The Oral Examination

Answer these aloud before reading the solutions. For each scenario, distinguish the observed symptom from the mechanism that could explain it.

### Challenge 1 — The Perfect Garbage Collector

A Node.js service stores every customer profile it encounters in a global Map.

The process's heap usage grows continuously.

Why doesn't garbage collection remove old entries?

### Challenge 2 — The Cache That Appears Healthy in Testing

A load test sends one million requests using the same customer ID.

Memory remains stable.

Production processes a large number of unique customer IDs and eventually runs out of memory.

Why did the load test miss the problem?

### Challenge 3 — The Invisible Closure

A report-generation function creates a large object and registers a callback that refers to it.

The function returns, but the object remains alive.

What reference path could explain the retention?

### Challenge 4 — The Listener Warning

Node.js reports an EventEmitter warning about too many listeners.

A developer increases the listener limit to silence it.

What might be wrong with that response?

### Challenge 5 — The Strange Memory Metrics

A process reports:

- `heapUsed`: 180 MiB.
- `external`: 500 MiB.
- `arrayBuffers`: 450 MiB.
- `rss`: 800 MiB.

What does this suggest?

Why shouldn't the four values simply be added together?

### Challenge 6 — The Growing Queue

A worker receives fifty tasks per second but completes only forty.

Every pending task retains a sizable payload in memory.

Why won't a faster garbage collector solve the problem?

### Challenge 7 — The WeakMap Proposal

A developer suggests replacing a string-keyed customer cache with WeakMap to fix unbounded memory retention.

Is this a suitable direct replacement?

### Challenge 8 — The Persistent RSS Plateau

A process's RSS rises during warmup, then remains elevated while heap usage and workload remain stable.

Does this necessarily demonstrate a leak?

### Challenge 9 — The Dangerous Snapshot

An engineer proposes taking a full heap snapshot of a memory-stressed production process during peak traffic.

What risks should be considered?

### Challenge 10 — The Senior Investigation

A long-running Node.js service gradually consumes more memory until its container restarts.

What sequence of measurements and experiments would you use before proposing a permanent fix?

## 22. Solutions and Discussion

### Solution 1 — Reachability prevents collection

The global Map remains reachable.

Its entries retain the customer-profile objects.

The collector cannot know that the application no longer needs old profiles.

A bounded cache with appropriate eviction or expiration addresses the retention problem.

### Solution 2 — Distinct-key cardinality drives growth

The test exercises one cache key repeatedly.

The cache population remains approximately constant.

Production introduces new keys continuously.

A representative load test should model both request rate and the distribution of unique cache keys.

### Solution 3 — The callback retains the object

The callback is stored in a long-lived registry.

Its closure retains access to the report object.

The registry retains the callback.

Therefore, the report remains reachable even after its creating function returns.

Explicit cleanup or capturing less state may solve the problem.

### Solution 4 — A warning is evidence, not a fix

Increasing the limit doesn't remove unintended listeners.

The developer should determine whether listeners are accumulating and whether they are removed when their owning operations finish.

Some high listener counts are legitimate; the warning alone isn't proof of a leak.

### Solution 5 — Buffer-backed or external memory deserves attention

Large `external` and `arrayBuffers` values suggest memory associated with Buffers, ArrayBuffers, or other external allocations.

`arrayBuffers` is included within `external`, so adding them double-counts part of the footprint.

RSS is a broader resident-memory measure with overlapping components, not an independent category to sum.

### Solution 6 — The retained workload keeps increasing

The queue grows by ten tasks per second.

Those tasks remain reachable because the application intends to process them.

Garbage collection cannot discard pending work.

The solution requires capacity, backpressure, bounded admission, external durability, or another deliberate workload-management strategy.

### Solution 7 — WeakMap isn't a direct string-keyed cache replacement

WeakMap primarily uses objects as weakly held keys.

A cache keyed by strings requires another design.

Even with object keys, WeakMap doesn't provide ordinary enumeration or a deterministic capacity and eviction policy.

A bounded Map or dedicated cache implementation may be more appropriate.

### Solution 8 — RSS can reflect retained runtime capacity

The runtime or memory allocator may retain previously acquired memory for reuse.

A stable post-warmup plateau isn't automatically a leak.

Investigate whether live object populations continue growing and whether memory usage remains bounded under representative traffic.

### Solution 9 — Snapshots can disrupt production and expose data

Heap snapshots can pause execution and require substantial additional memory.

A stressed process may become unresponsive or crash.

Snapshots may contain sensitive application values.

Prefer controlled reproduction or an explicitly approved diagnostic procedure with appropriate security and availability precautions.

### Solution 10 — Build evidence before changing limits

First establish the trend and its relationship to workload.

Separate heap, external, ArrayBuffer, and process-resident memory observations.

Check unique-key counts, cache sizes, listener populations, queues, and other retained structures.

Reproduce the pattern with controlled traffic.

Use snapshot comparisons when appropriate and safe.

Identify the retaining path.

Then change the relevant ownership or retention policy and verify that memory stabilizes while the application still performs its intended work.

## 23. The Mental Model Worth Keeping

A garbage collector doesn't know what your application needs.

It knows which values remain reachable under its memory-management model.

That distinction explains why an application can leak memory while garbage collection works perfectly.

Whenever a service's memory grows, ask:

**What is being allocated? What remains reachable? Who retains it? How long should it remain alive? Which memory category is growing?**

Then compare the observed behavior with the intended lifetime of the data.

An object that remains reachable indefinitely needs a reason to exist indefinitely.

If no such reason exists, the problem is probably not garbage collection.

It's the application's ownership and lifecycle design.

## 24. Next Lecture — CS220-L05: From Source Code to Machine Code — Compilers and JITs

We've investigated what happens to objects while a program runs.

Now we'll look deeper into execution itself.

Your processor doesn't directly understand TypeScript, Python, Java, or Rust.

It executes machine instructions.

But the journey from source code to those instructions can involve parsing, intermediate representations, bytecode, interpretation, ahead-of-time compilation, JIT compilation, and runtime optimization.

A JavaScript engine may optimize frequently executed code based on observed value patterns.

A compiler may reorganize operations while preserving language semantics.

And a seemingly faster source-level implementation may produce worse machine-level behavior because of memory access patterns, branch prediction, or hidden allocation.

In the next lecture, we'll build the mental bridge from source code to actual processor execution, preparing us to compare language runtimes without falling into simplistic "compiled versus interpreted" arguments.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

## Optional Practical Lab — Create, Measure, and Repair a Bounded Memory Leak

**Objective:** Reproduce a controlled cache-retention problem, compare Node.js memory metrics, repair the retention policy, and inspect the heap safely.

This lab intentionally uses a limited number of small objects. It is designed for a local development machine and should not exhaust system memory.

Do not run heap-snapshot experiments against production services or expose the Node.js inspector to untrusted networks.

### Lab A — Create the test application

Create a file named `memory-lab.mjs`.

The program simulates customer-profile data with nested reservation information. It stores profiles in one of two cache implementations.

The first retains every customer.

The second evicts older entries when its capacity is reached.

```javascript
const mode = process.argv[2] ?? "leaky";

const cache = new Map();
const MAX_ENTRIES = 150;

function buildProfile(customerId) {
  return {
    customerId,
    reservations: Array.from({ length: 120 }, (_, index) => ({
      reservationId: `R-${customerId}-${index}`,
      amountCents: (customerId + index) * 3,
      hotelId: `H-${index % 20}`,
      nights: (index % 7) + 1,
    })),
  };
}

function insertProfile(customerId) {
  const profile = buildProfile(customerId);

  cache.set(customerId, profile);

  if (mode === "bounded") {
    while (cache.size > MAX_ENTRIES) {
      const oldest = cache.keys().next().value;
      cache.delete(oldest);
    }
  }
}

function toMiB(bytes) {
  return Math.round((bytes / 1024 / 1024) * 10) / 10;
}

function reportMemory(batch) {
  if (global.gc) {
    global.gc();
  }

  const usage = process.memoryUsage();

  console.log({
    batch,
    entries: cache.size,
    heapUsedMiB: toMiB(usage.heapUsed),
    externalMiB: toMiB(usage.external),
    arrayBuffersMiB: toMiB(usage.arrayBuffers),
    rssMiB: toMiB(usage.rss),
  });
}

for (let batch = 1; batch <= 40; batch++) {
  for (let offset = 0; offset < 50; offset++) {
    const customerId = (batch - 1) * 50 + offset;
    insertProfile(customerId);
  }

  reportMemory(batch);
}
```

The program creates a fixed maximum of two thousand simulated customer profiles during one run.

The nested arrays make retained memory visible without requiring uncontrolled allocation.

### Lab B — Run the unbounded version

Start the script with garbage collection exposed for controlled measurement:

```bash
node --expose-gc memory-lab.mjs leaky
```

Observe how the number of cache entries increases with every batch.

Pay attention to `heapUsedMiB` after the optional explicit collection.

Exact memory values will differ by Node.js version, architecture, and runtime behavior.

**Question:** Why does heap usage tend to increase as the distinct customer population grows?

### Lab C — Run the bounded version

Now use the bounded policy:

```bash
node --expose-gc memory-lab.mjs bounded
```

Observe the number of entries.

After reaching the capacity limit, the cache should continue replacing older entries rather than growing indefinitely.

Compare the memory trend with the unbounded version.

**Question:** Why might RSS remain elevated even when the retained cache population is bounded?

### Lab D — Distinguish request rate from distinct-key count

Modify the workload so every batch repeatedly requests the same fifty customer IDs instead of introducing new ones.

Run the unbounded cache again.

Compare the result.

A large number of requests to a small stable key set doesn't necessarily create a large cache.

**Question:** Which characteristic of the production workload did a repeated-key load test fail to represent?

### Lab E — Observe Buffer-backed memory

Create `buffer-lab.mjs`:

```javascript
const retained = [];

function metrics() {
  const memory = process.memoryUsage();

  return {
    heapUsedMiB: +(memory.heapUsed / 1048576).toFixed(1),
    externalMiB: +(memory.external / 1048576).toFixed(1),
    arrayBuffersMiB: +(memory.arrayBuffers / 1048576).toFixed(1),
    rssMiB: +(memory.rss / 1048576).toFixed(1),
  };
}

console.log("Before:", metrics());

for (let i = 0; i < 100; i++) {
  const buffer = Buffer.alloc(128 * 1024, i % 256);
  retained.push(buffer);
}

console.log("After:", metrics());
console.log("Retained buffers:", retained.length);
```

Run:

```bash
node buffer-lab.mjs
```

The program retains approximately 12.5 MiB of Buffer payload data, plus any overhead.

Compare the changes in `heapUsed`, `external`, `arrayBuffers`, and RSS.

**Question:** Why isn't the JavaScript heap-used measurement a complete representation of the process's memory footprint?

### Lab F — Reproduce listener retention

Create `listeners.mjs`:

```javascript
import { EventEmitter } from "node:events";

const events = new EventEmitter();

function registerReportListener(reportId) {
  const report = {
    id: reportId,
    findings: Array.from({ length: 100 }, (_, i) => ({
      id: i,
      severity: "low",
    })),
  };

  const listener = () => {
    console.log("Report viewed:", report.id);
  };

  events.on("viewed", listener);

  return listener;
}

const listeners = [];

for (let i = 0; i < 12; i++) {
  listeners.push(registerReportListener(i));
}

console.log("Listeners:", events.listenerCount("viewed"));

for (const listener of listeners) {
  events.off("viewed", listener);
}

console.log("After cleanup:", events.listenerCount("viewed"));
```

Run the script.

You may observe a MaxListeners warning when the listener count exceeds the configured threshold.

Then observe the listener count after cleanup.

**Question:** Why does raising the maximum listener limit not actually remove unintended retained references?

### Lab G — Inspect a heap snapshot

Run the bounded or unbounded memory lab using the Node.js inspector on your own machine.

For example:

```bash
node --inspect-brk=127.0.0.1:9229 --expose-gc memory-lab.mjs leaky
```

Use a compatible Chromium DevTools inspector to connect locally.

Step through the program or adjust it to pause at a useful point after a workload batch.

Capture a heap snapshot in the controlled environment.

Look for the Map and the customer-profile objects it retains.

A useful investigation asks which reference chain keeps those profiles alive.

Be aware that a snapshot can pause the process and consume substantial additional memory.

Do not expose the inspector port publicly, and do not capture production-sensitive data without authorization.

### Lab H — Design a production cache policy

Your real customer-profile service has these characteristics:

- Most customers request their profiles infrequently.
- A small group of active customers generates much of the traffic.
- Profiles range from a few kilobytes to several hundred kilobytes.
- Customer permissions can change.
- Database access is moderately expensive.
- The application runs several independent Node.js processes.

Design a cache policy.

Specify a maximum size or memory budget, expiration and eviction behavior, authorization-aware cache keys, invalidation strategy, and whether cache state is process-local or shared.

Then answer the critical question:

**What guarantees that the cache's retained memory remains bounded, even when the number of distinct customers grows indefinitely?**

---

## Further Reading

1. [MDN — JavaScript Memory Management](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Memory_management) — Reachability and garbage-collection concepts.
2. [V8 — Garbage Collection](https://v8.dev/blog/trash-talk) — Generational, incremental, concurrent, and parallel GC mechanisms.
3. [Node.js — Understanding and Tuning Memory](https://nodejs.org/en/learn/diagnostics/memory/understanding-and-tuning-memory) — Node memory categories and measurements.
4. [Node.js — Using Heap Snapshots](https://nodejs.org/en/learn/diagnostics/memory/using-heap-snapshot) — Snapshot collection and comparison.
5. [Node.js — Using GC Traces](https://nodejs.org/en/learn/diagnostics/memory/using-gc-traces) — Garbage-collection observations.
6. [Node.js — `process.memoryUsage()`](https://nodejs.org/api/process.html#processmemoryusage) — Heap, external, ArrayBuffer, and RSS metrics.
7. [MDN — WeakMap](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/WeakMap) — Weak keys and object-associated metadata.
8. [MDN — FinalizationRegistry](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/FinalizationRegistry) — Nondeterministic finalization behavior.
9. [Node.js — Events](https://nodejs.org/api/events.html) — EventEmitter listeners and lifecycle.
10. [Node.js — Streams](https://nodejs.org/api/stream.html) — Streaming and backpressure for bounded data processing.

---

## Dense Cheatsheet — Interview Glance Card

*This final reference is intentionally fenced for rapid screen-based revision.*

```text
CS220-L04 — REFERENCES, GARBAGE COLLECTION, AND MEMORY LEAKS

CORE PRINCIPLE

Garbage collector:
  Reclaims unreachable managed objects.

Application:
  Decides which data should remain useful.

REACHABLE != USEFUL

STACK

  Active function execution state
  Call/return structure
  Stack overflow from excessive recursion
  Not a universal map of all JS values

HEAP

  Dynamic allocation
  Objects can outlive creating functions
  Runtime may optimize physical representation

REFERENCE GRAPH

  Roots -> objects -> nested objects

  As long as an object remains reachable,
  it ordinarily remains live for GC.

COMMON ROOTS / RETAINERS

  Module-level collections
  Global references
  Closures
  Event listeners
  Timers
  Outstanding operations
  Runtime-managed structures

GARBAGE COLLECTION

  Roots
    -> Trace reachable objects
    -> Reclaim unreachable allocations

  Mark/sweep is a simplified mental model.

  GC does NOT understand:
    Customer relevance
    Cache freshness
    Business expiration
    Whether a queued job is obsolete

APPLICATION MEMORY LEAK

  Data remains reachable longer than intended.

  GC can function perfectly while leak continues.

UNBOUNDED MAP

  Every unique customer ID creates entry.
  No eviction -> retained graph grows.

  Request count != unique key cardinality.

BOUNDED CACHE

  Capacity limit
  Memory budget
  TTL + actual expiration cleanup
  LRU or another eviction policy
  Correct invalidation
  Authorization-aware keys

  Entry count is not always memory bound
  when values have variable sizes.

CLOSURES

  Retain access to lexical environment.

  Long-lived callback can retain:
    Report objects
    Request state
    Large payloads

  Capture only needed data when practical.

EVENT LISTENERS

  Emitter retains registered callbacks.
  Callbacks may retain captured objects.

  Clean up when operation ends.
  MaxListeners warning != definitive leak.
  Raising warning threshold != cleanup.

TIMERS / PENDING OPERATIONS

  Callback and bookkeeping can retain state.
  Cancel/clear when no longer needed.
  Unresolved Promise alone != universal leak.

QUEUE MEMORY

  Arrival rate > completion rate
    -> backlog grows
    -> retained work grows

  Faster GC cannot discard useful pending work.

  Use bounded queues, backpressure,
  durable external storage or capacity controls.

V8 GC

  Generational collection
  Young generation for many short-lived objects
  Promotion of surviving objects
  Major collection for longer-lived regions

  Incremental/concurrent/parallel mechanisms
  reduce some pauses and overhead.

ALLOCATION VS RETENTION

  High allocation rate:
    Can create GC CPU cost

  High retained size:
    Can create memory pressure / major GC cost

  Different problems, different remedies.

NODE MEMORY METRICS

  heapUsed:
    Used V8 heap memory

  heapTotal:
    Allocated V8 heap capacity

  external:
    Certain native/backing-store allocations

  arrayBuffers:
    ArrayBuffer/SharedArrayBuffer/Buffer memory
    Included in external

  rss:
    Broad resident process memory

  Do NOT add all values together.

BUFFER MEMORY

  Buffer data can increase external/arrayBuffers.
  heapUsed may remain comparatively small.

  Low heapUsed != low process memory.

MEMORY PATTERNS

  Sawtooth:
    Allocation followed by GC

  Plateau:
    May indicate bounded working set/cache

  Rising post-GC baseline:
    Possible growing retained population

  RSS stays high:
    Can reflect allocator/runtime memory reuse

  One graph alone != proof of leak.

HEAP SNAPSHOTS

  Compare similar workload points.
  Inspect object counts and retaining paths.
  Shallow size != retained size.

  Find who holds object alive,
  not merely where it was constructed.

  Production risk:
    Pause
    Extra memory
    Possible crash
    Sensitive data exposure

WEAKMAP

  Weakly held object keys
  Key doesn't stay alive solely due to WeakMap.
  Useful for object-associated metadata.

  Not a drop-in string-keyed cache.
  Not enumerable.
  No deterministic eviction/size contract.

FINALIZATION

  GC timing nondeterministic.
  Finalizers not reliable for critical cleanup.
  Use explicit lifecycle management.

MEMORY BUDGETS

  V8 heap limits
    !=
  Complete process memory
    !=
  Container memory limit

  Increasing limits may delay an unbounded leak,
  not repair it.

DIAGNOSTIC SEQUENCE

  1. Establish memory trend and workload
  2. Compare heapUsed/external/arrayBuffers/rss
  3. Identify growing cache/queue/listener populations
  4. Reproduce with representative unique keys
  5. Compare heap snapshots safely
  6. Trace retaining paths
  7. Correct ownership/retention policy
  8. Verify bounded memory and useful performance

FIVE SENIOR QUESTIONS

  What is being allocated?
  What remains reachable?
  Who retains it?
  How long should it remain alive?
  Which memory category is growing?

SENIOR LINE

  "A garbage collector reclaims unreachable objects;
   it doesn't know which reachable objects are obsolete.
   I distinguish allocation rate from retained size,
   identify retaining paths, measure the right memory
   categories, and enforce explicit lifetime and
   capacity policies."
```
