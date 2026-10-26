---
id: CS220-L02
course: CS220
title: "Memory: The Invisible Battlefield"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [CS101-S07]
prev: CS220-L01
next: CS220-L03
---



# CS220 — Programming Languages, Memory, and Execution
## Lecture 02: Memory: The Invisible Battlefield

*Stack, heap, references, garbage collection, memory leaks, and the hidden economics of keeping information alive.*

**Estimated study time:** 75–95 minutes, including practical experiments.

---

# 1. The Server That Was Slowly Eating Itself

It's 3:42 AM.

Your monitoring system wakes up the on-call engineer.

One of your Node.js services has just restarted.

The reason?

Out of memory.

That's strange. The application isn't doing anything especially demanding.

It receives customer requests, retrieves information from PostgreSQL, calls a few external APIs, and returns JSON.

No image processing.

No machine learning.

No enormous scientific calculations.

Just an ordinary backend service.

And yet the memory usage tells an alarming story.

| Time since deployment | Process memory |
|---|---:|
| 0 minutes | 140 MB |
| 30 minutes | 230 MB |
| 1 hour | 370 MB |
| 2 hours | 590 MB |
| 3 hours | 810 MB |
| 4 hours | 980 MB |
| Shortly afterward | Process terminated |

These are hypothetical measurements, but they describe a very real class of production incident.

You restart the service.

Memory drops back to 140 MB.

Everything works beautifully.

Four hours later, the problem returns.

Wonderful. You've invented a server that needs a coffee break every four hours.

Your colleague suggests increasing the memory limit.

Another suggests adding more application instances.

Someone proposes upgrading Node.js.

A particularly enthusiastic engineer recommends rewriting the service in Rust.

But before we start spending money or rewriting software, we should ask a more fundamental question.

**Why is the application keeping so much information in memory?**

After all, the requests have finished.

The responses have been sent.

The database connections are still healthy.

Surely the data belonging to completed requests should disappear?

And doesn't JavaScript have automatic garbage collection?

Shouldn't the runtime clean everything up?

This is where the story becomes interesting.

The garbage collector may be working perfectly.

It may be examining memory regularly, identifying objects that are no longer needed, and reclaiming them exactly as designed.

And the service may still be leaking memory.

How can both things be true?

To answer that, we need to understand what memory actually represents to a running program.

---

# 2. Memory Is Where a Program Keeps Its World

When a program executes, it needs to remember things. Some information exists for only a tiny fraction of a second; other information must survive for hours, days, or the entire lifetime of the process.

Consider a hotel reservation request.

The backend receives:

```typescript
{
  hotelId: "H-142",
  roomType: "deluxe",
  checkIn: "2026-11-10",
  checkOut: "2026-11-13"
}
```

The application might need to remember:

- The incoming request.
- The authenticated user.
- The current function's intermediate results.
- Available room inventory.
- A database query result.
- A price calculation.
- An external payment response.
- The reservation being created.
- Application-wide configuration.
- Cached information shared between requests.

Some of these values exist only while one function executes. Some need to survive across several asynchronous operations. Some remain available to future requests.

That leads us to three important questions about memory:

**Where does the information live?**

**How long must it remain available?**

**Who, or what, is responsible for releasing it?**

These questions appear in almost every programming language, although different languages answer them differently.

In C or C++, programmers may manage some memory explicitly.

In Rust, ownership and lifetime rules play a central role.

In Java, JavaScript, and many other managed languages, garbage collectors reclaim much of the memory automatically.

But automatic memory management doesn't eliminate the need to understand memory.

It changes the nature of your responsibility.

Instead of deciding exactly when to free every object, you must understand which objects remain reachable, which resources require explicit cleanup, and what prevents information from being discarded.

Let's start with the two memory concepts developers encounter most often: the stack and the heap.

---

# 3. The Call Stack: Where Execution Remembers How It Got Here

Imagine you're debugging a production exception. You open the stack trace and see something like:

```text
Error: Payment authorization failed

    at authorizePayment()
    at processReservation()
    at createBooking()
    at handleRequest()
```

Even without inspecting the code, you can reconstruct the sequence of calls.

The HTTP handler invoked `createBooking()`.

That called `processReservation()`.

Which called `authorizePayment()`.

And the error occurred there.

The structure behind this is the **call stack**.

## A stack is a last-in, first-out structure

We introduced stacks briefly in CS110-L04.

Imagine a pile of plates.

You put a new plate on top.

When you need one, you take the top plate.

Last in, first out.

A call stack follows the same general discipline.

When a function is called, execution creates a new call frame.

That frame contains information needed to execute the function and eventually return control to its caller.

Conceptually, it may include:

- The location to return to.
- Function arguments or their associated state.
- Local execution information.
- Temporary values.
- Information required by the runtime.

The exact contents and physical layout depend on the language implementation and optimization strategy. Let's examine a small example.

```typescript
function calculatePrice() {
  return applyDiscount(100, 0.15);
}

function applyDiscount(
  price: number,
  discount: number
) {
  return price - calculateReduction(price, discount);
}

function calculateReduction(
  price: number,
  discount: number
) {
  return price * discount;
}

calculatePrice();
```

When `calculateReduction()` is executing, the conceptual stack looks like this:

```text
        CALL STACK

    +---------------------+
    | calculateReduction  |  ← Currently executing
    +---------------------+
    | applyDiscount       |
    +---------------------+
    | calculatePrice      |
    +---------------------+
    | Program entry       |
    +---------------------+
```

When `calculateReduction()` returns, its frame is removed and execution resumes inside `applyDiscount()`. When that function returns, its frame is removed too, and eventually control returns to the original caller.

This nested structure is one reason a stack is such a natural mechanism for ordinary function execution.

## Why the stack is efficient

In a conventional implementation, stack allocation can be extremely cheap. The runtime often needs only to adjust a stack pointer or perform similarly simple bookkeeping when entering or leaving a function—no complicated search for a free memory block is necessarily required—and when a function returns, its frame's storage can become available for subsequent calls.

But here's an important qualification.

**The JavaScript language specification doesn't promise that every local variable lives physically on the stack.**

Modern JavaScript engines can store values in registers, stack frames, heap-allocated environments, or optimize their storage away entirely. The stack-and-heap distinction is a useful model of execution, not a rigid rule that says "primitives go on the stack and objects go on the heap."

That popular explanation is too simplistic. In fact, closures provide an excellent example of why it fails. We'll return to them shortly.

---

# 4. Why Recursive Functions Can Destroy the Stack

Consider this function:

```typescript
function countdown(n: number): number {
  if (n === 0) {
    return 0;
  }

  return countdown(n - 1);
}
```

Nothing unusual. But suppose we call:

```typescript
countdown(1_000_000);
```

What happens?

Every recursive call creates another invocation that must be accounted for, so the call stack grows deeper and deeper. Eventually, the runtime may run out of available stack space. In Node.js or a browser, this commonly produces an error such as:

`RangeError: Maximum call stack size exceeded`

This is a **stack overflow**.

It doesn't necessarily mean your computer has run out of RAM; it means the execution has exceeded the available call-stack capacity. Different runtimes have different limits and optimizations, and some languages and implementations support tail-call optimization, which can eliminate certain otherwise unnecessary stack growth.

But ordinary JavaScript code should not assume that deep recursion will be optimized away.

## Iteration can avoid the problem

Consider an iterative version:

```typescript
function countdown(n: number): number {
  while (n > 0) {
    n--;
  }

  return n;
}
```

This function doesn't need a million nested calls.

It uses one invocation and repeatedly updates a value.

The asymptotic time complexity is still O(n).

But the call-stack requirements are dramatically different.

This is why recursive algorithms may need iterative implementations when input depth is potentially enormous.

For example:

- Traversing a deeply nested JSON document.
- Walking a pathological tree structure.
- Processing a long chain of dependencies.
- Exploring a graph with extreme depth.

An explicit stack stored in an array can replace recursive function calls. That doesn't remove the need for memory, but it gives the program more control over how the traversal state is represented.

A useful distinction emerges:

**Time complexity and memory requirements are different dimensions of algorithmic cost.**

A recursive algorithm and an iterative algorithm can perform similar work while consuming memory differently.

---

# 5. The Heap: Where Objects Can Outlive Their Creators

Now let's move to the heap. In managed runtimes such as V8, the heap is a major area of memory used to store dynamically allocated objects and related data. Unlike a conventional call-stack frame, heap-allocated data isn't necessarily tied to the lifetime of one function invocation. An object can remain alive long after the function that created it has returned.

Consider:

```typescript
function createCustomer() {
  return {
    id: "C-42",
    name: "Anna",
    preferences: {
      language: "lt",
      notifications: true
    }
  };
}

const customer = createCustomer();
```

The function returns.

Its ordinary call frame no longer needs to remain active.

But the customer object still exists.

Why?

Because the program retains a reference to it through `customer`.

The object's lifetime isn't determined simply by when its creating function returned.

It's determined by whether the running program can still reach it.

That brings us to one of the most important concepts in JavaScript memory management.

## Variables and objects are not the same thing

Let's try something.

```javascript
const customerA = {
  id: 42,
  name: "Anna"
};

const customerB = customerA;

customerB.name = "Maria";

console.log(customerA.name);
```

The output is:

`Maria`

Why?

Because `customerA` and `customerB` refer to the same object. We haven't created two independent customer objects; we've created two bindings holding references to one object.

Conceptually:

```text
customerA ────┐
              |
              v
          +-------------+
          | id: 42      |
          | name: Maria |
          +-------------+
              ^
              |
customerB ────┘
```

Both bindings provide access to the same underlying data. This is called **aliasing**, and it's extremely common. It matters because changing an object through one reference can affect what other parts of the program observe.

## Reassignment versus mutation

Now compare:

```javascript
let customerA = {
  name: "Anna"
};

let customerB = customerA;

customerB = {
  name: "Maria"
};

console.log(customerA.name);
```

This prints:

`Anna`

Why? Because assigning a new object to `customerB` changes which object that binding refers to. It doesn't modify the old object.

The distinction is:

**Mutation changes an object.**

**Reassignment changes what a binding refers to.**

This may sound elementary, but it lies beneath many important behaviors:

- Shared mutable state.
- Reactivity systems.
- Caching.
- Object identity.
- Equality comparisons.
- Memory retention.
- Garbage collection.

And it helps explain why objects sometimes remain alive unexpectedly.

---

# 6. The Garbage Collector Doesn't Know What You Want

Let's return to our leaking Node.js service.

Suppose each request creates a large object. After responding to the customer, the program no longer needs it. Should the memory be reclaimed? Eventually, yes—provided nothing reachable continues to retain the object.

But the garbage collector doesn't understand the application's business purpose. It doesn't know that a request has finished, whether a reservation object remains useful, whether cached data is outdated, or whether a background job will ever resume. It works according to runtime-level reachability and collection rules, and that distinction is absolutely fundamental.

**Garbage collection does not mean removing objects that are no longer useful. It means identifying objects that are no longer reachable by the running program.**

And those aren't the same thing.

## Reachability

Imagine an object graph. Objects can hold references to other objects, and some references originate from places the runtime treats as roots—relevant active execution state, globals, and runtime-managed references.

A simplified graph might look like this:

```text
              GC ROOTS
                  |
                  v
          Application state
                  |
          +-------+--------+
          |                |
          v                v
      Cache Map       Active request
          |                |
          v                v
      Customer A       Customer B
          |
          v
      Preferences


      Customer C
          |
          v
      Old report
```

Customer A is reachable from the application state. Customer B is reachable from an active request. But Customer C and its old report have no path from a root. Assuming no other hidden or runtime-managed references exist, the garbage collector can regard Customer C and its report as garbage.

Now imagine the application no longer needs Customer A—perhaps that customer hasn't been active for six months—but the cache still contains a reference. The garbage collector sees that Customer A is reachable, so it retains the object.

From the collector's perspective, that's correct. From the application's perspective, it may be a memory leak. This is the central paradox.

**An object can be completely useless to your business logic and still be legitimately alive according to the garbage collector.**

## Mark and sweep

One basic garbage-collection technique is called **mark and sweep**. Conceptually, it works like this:

1. Start from known roots.
2. Follow references to reachable objects.
3. Mark those objects as alive.
4. Reclaim memory occupied by objects that weren't marked.

The actual implementation in V8 is more sophisticated, but this model is useful.

Notice something interesting. Suppose two objects reference each other.

```javascript
let a = {};
let b = {};

a.other = b;
b.other = a;

a = null;
b = null;
```

The two objects form a cycle: each references the other. Does that prevent garbage collection? Not in a tracing collector merely because the cycle exists. If neither object is reachable from the collector's roots, the entire cycle can be reclaimed. This distinguishes tracing garbage collection from simple reference-counting approaches, where cycles require special handling.

The important question isn't:

"Does any object reference this object?"

It's:

**"Is there a chain of relevant references from a root to this object?"**

That distinction explains an enormous amount of JavaScript memory behavior.

---

# 7. The Actual Bug: An Innocent-Looking Cache

Now let's find the memory leak in our imaginary SaaS service.

The developer responsible for the customer profile endpoint noticed that database queries were relatively expensive, so they introduced a cache. Here's a simplified version:

```typescript
const customerCache = new Map<string, CustomerProfile>();

async function getCustomerProfile(
  customerId: string
): Promise<CustomerProfile> {
  const cached = customerCache.get(customerId);

  if (cached) {
    return cached;
  }

  const profile = await loadProfileFromDatabase(customerId);

  customerCache.set(customerId, profile);

  return profile;
}
```

Looks reasonable.

And for a while, it works beautifully.

Frequently accessed customer profiles are retrieved from memory.

Database load decreases.

Latency improves.

Everyone congratulates the developer.

Then the customer base grows.

Ten thousand customer profiles enter the cache.

Then fifty thousand.

Then two hundred thousand.

And nothing ever leaves.

Every profile is stored in a Map that remains reachable for the lifetime of the process.

The garbage collector sees the Map.

The Map references its stored values.

Those values remain reachable.

Therefore, the collector keeps them.

Even if the application never accesses most of them again.

This is a classic **unbounded cache**.

And it's one of the easiest ways to leak memory in a garbage-collected language.

## Why the leak is subtle

The code isn't necessarily allocating absurd amounts of memory in one operation. Every request adds only a little—maybe a customer profile occupies a few kilobytes—and a single request barely changes process memory. But the application handles hundreds of thousands of customers, and over time the retained objects accumulate.

The resulting memory growth may correlate with unique customer traffic rather than raw request count. That's an important diagnostic clue.

If one million requests all access the same hundred customers, the cache might remain small. If one million requests access one million distinct customers, the cache could become enormous. Same endpoint, same request volume, completely different memory behavior.

## The solution isn't necessarily removing the cache

We can impose limits. For example:

- Maximum number of cached entries.
- Maximum estimated memory usage.
- Expiration times.
- Least-recently-used eviction.
- Explicit invalidation when records change.

Each approach has trade-offs. A time-to-live policy expires entries after some duration, but if a large number of unique entries arrive quickly, a TTL alone may still permit excessive memory growth. A maximum-size policy provides a stronger bound on entry count, but entry count doesn't necessarily bound memory tightly if entry sizes vary dramatically. A production cache may need both capacity limits and expiration rules.

And even after solving memory retention, we still need to consider consistency. A cached subscription plan may become stale. A cached authorization decision may become dangerous. A cached customer profile might contain sensitive data that shouldn't remain in memory unnecessarily.

Caching is therefore more than a performance optimization. It's a decision about retaining copies of information, how long those copies may live, and when they can be trusted. This connects back to our earlier lessons on representations, data structures, and system state.

---

# 8. The Closure That Kept a Giant Object Alive

Remember closures from CS220-L01?

A closure allows a function to access variables from its surrounding lexical environment even after the surrounding function has returned. That's incredibly useful, but now we can see the memory consequences more clearly.

Imagine a report-generation service. When a report is created, the application registers a callback that will send a notification whenever the report is viewed. Here's a simplified example:

```typescript
const callbacks = new Map<string, () => void>();

function registerReport(report: Report) {
  const onViewed = () => {
    console.log(
      `Report ${report.id} was viewed`,
      report.metadata.owner
    );
  };

  callbacks.set(report.id, onViewed);
}
```

What does the callback reference? The `report` object. And because the callback uses `report.id` and `report.metadata.owner`, the closure retains access to that object while the callback remains reachable.

Now suppose `Report` contains a huge dataset.

Perhaps thousands of rows or a large in-memory structure.

The report is generated.

It's saved to durable storage.

The HTTP request finishes.

The application no longer needs the original in-memory report.

But the callback remains in the global Map.

The callback retains access to the report.

And the report retains access to its large dataset.

So the entire structure may remain alive.

Conceptually:

```text
Global callbacks Map
        |
        v
   Callback function
        |
        v
   Captured report
        |
        v
   Large report dataset
```

The garbage collector isn't confused. Every object in that chain remains reachable.

## A better design

Instead of retaining the entire report, the callback could retain only the information it actually needs.

```typescript
function registerReport(report: Report) {
  const reportId = report.id;
  const owner = report.metadata.owner;

  callbacks.set(reportId, () => {
    console.log(
      `Report ${reportId} was viewed`,
      owner
    );
  });
}
```

Now the callback doesn't need to reference the original report object; it retains only the extracted values. This can substantially reduce retained memory.

But another issue remains. The callback itself is still stored in a global Map, and if callbacks are never removed, the Map continues growing. So we also need a lifecycle policy.

When should the callback be deleted? When the report expires? When the user logs out? After some period of inactivity? When an explicit unsubscribe operation occurs?

The general lesson is:

**Closures make it easy to preserve state without explicitly constructing objects to hold that state. But preserved state still has a lifetime and a memory cost.**

---

# 9. Event Listeners: The Memory Leak That Visits Both Frontend and Backend

Here's another extremely common source of memory leaks: event listeners. Suppose your Node.js service listens for an event whenever an integration becomes available.

```typescript
import { EventEmitter } from "node:events";

const events = new EventEmitter();
```

Now imagine registering a listener for each customer session.

```typescript
function startSession(session: CustomerSession) {
  events.on("integration-ready", () => {
    session.notifyIntegrationReady();
  });
}
```

Looks simple.

But what happens when the customer session finishes?

Nothing removes the listener.

The EventEmitter still holds the callback.

The callback still references the session.

The session may reference its user, cached data, active operations, and other objects.

So the session can remain alive long after it should have been discarded.

And every new session registers another listener.

Over time:

```text
EventEmitter
     |
     +── Listener 1 ── CS110-L01
     |
     +── Listener 2 ── CS110-L02
     |
     +── Listener 3 ── CS110-L03
     |
     +── ...
     |
     +── Listener 100,000 ── Session 100,000
```

Again, the garbage collector does exactly what it should: it preserves reachable objects. The application is responsible for detaching the listeners it no longer needs.

## Explicit cleanup

A better design gives each session a cleanup operation.

```typescript
function startSession(session: CustomerSession) {
  const onReady = () => {
    session.notifyIntegrationReady();
  };

  events.on("integration-ready", onReady);

  return function stopSession() {
    events.off("integration-ready", onReady);
  };
}
```

Now the caller receives a way to release the listener. The remaining responsibility is actually invoking that cleanup function when the session ends, including relevant error and cancellation paths.

This is closely related to **resource ownership**. Who registers the listener? Who removes it? Who guarantees cleanup happens? Those questions matter even in garbage-collected languages.

## The Vue connection

The same problem can appear in frontend applications. Imagine a Vue component registering a global browser event listener.

```typescript
import { onMounted, onUnmounted } from "vue";

function handleResize() {
  console.log(window.innerWidth);
}

onMounted(() => {
  window.addEventListener("resize", handleResize);
});

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
});
```

The component installs the listener when mounted.

And removes it when unmounted.

Without appropriate cleanup, repeated creation and destruction of components can accumulate listeners and retain associated state.

Vue automatically manages many effects created within its component lifecycle, but manually registered external listeners, timers, and similar resources still require attention.

This is particularly relevant in long-lived single-page applications.

A website might remain open for hours.

Users navigate between views.

Components appear and disappear.

Background subscriptions start and stop.

A small retention mistake repeated hundreds of times can gradually degrade performance.

## The subtle issue with timers

Timers introduce similar lifecycle concerns.

```typescript
const timer = setInterval(() => {
  refreshDashboard();
}, 5000);
```

If the timer belongs to a component, session, or temporary service, it should have a defined cleanup policy.

```typescript
clearInterval(timer);
```

A long-lived timer can keep its callback and associated state alive, even when the application no longer needs the repeated work.

And there's another important detail. Garbage collection manages memory. It doesn't automatically understand when a network connection, file descriptor, timer, or external subscription should be logically terminated. Releasing JavaScript objects and closing external resources are related but distinct responsibilities, which is why explicit cleanup remains essential.

---

# 10. How Modern Garbage Collection Avoids Freezing Your Application

At this point, you might imagine garbage collection as a periodic event in which the runtime stops the entire application, scans every object, and decides what to keep.

Some garbage collectors have historically behaved in broadly similar ways, but modern implementations are far more sophisticated.

Let's focus on V8, the JavaScript engine used by Node.js and Chrome. One of its central ideas is **generational garbage collection**.

## Most objects die young

This observation is surprisingly useful. Think about an ordinary HTTP request. The application might allocate:

- A request object.
- Temporary strings.
- Query parameters.
- Validation results.
- Intermediate arrays.
- A response object.

Most of those objects are short-lived.

They exist while processing the request, then become unreachable.

Meanwhile, other objects survive much longer.

Configuration.

Shared caches.

Module state.

Long-lived services.

Database connection management structures.

The runtime can take advantage of these different lifetime patterns.

This is often described as the **generational hypothesis**:

Most newly allocated objects become unreachable relatively quickly.

## Young and old generations

V8 organizes much of its managed heap into generations. New objects commonly begin in a young generation, and objects that survive enough collection cycles may be promoted into an older generation.

The young generation can be collected frequently because most of its objects are expected to be short-lived. The older generation is larger and generally requires more elaborate collection work. This is useful because the runtime doesn't need to treat every temporary object as though it will remain alive forever.

## Why garbage collection has a cost

Imagine an application allocating thousands of temporary objects per second. Even if most objects quickly become unreachable, the garbage collector still needs to manage allocation and reclamation. That work consumes CPU time and memory bandwidth.

Some garbage-collection operations may also pause the JavaScript execution thread, and long pauses can be particularly undesirable in interactive applications or latency-sensitive backend services. Modern V8 uses techniques including:

- Generational collection.
- Incremental marking.
- Concurrent marking and sweeping.
- Parallel collection work.
- Selective compaction.

The implementation can perform substantial garbage-collection work alongside application execution or divide it into smaller pieces. This reduces the duration of some pauses, but garbage collection isn't free, and the precise algorithms evolve across V8 versions.

You don't need to memorize their implementation details. The important principle is that garbage collection balances several goals:

**Reclaim memory efficiently.**

**Avoid excessive pauses.**

**Minimize CPU overhead.**

**Use available memory intelligently.**

Those goals can conflict. A runtime that collects very aggressively may reduce memory usage while spending more CPU time on collection. A runtime that allows the heap to grow may reduce collection frequency while consuming more memory. That's an engineering trade-off, and it explains why observing memory usage requires more nuance than simply checking whether the number is increasing.

---

# 11. Growing Memory Does Not Automatically Mean a Leak

Let's return to our monitoring dashboard.

The service's memory usage is increasing.

Does that prove a memory leak?

No.

Consider how garbage collection works over time.

An application allocates objects.

Memory usage rises.

Eventually, garbage collection runs.

Unreachable objects are reclaimed.

Memory usage falls.

Then allocation begins again.

The resulting graph often resembles a sawtooth.

```text
Memory
  ^
  |
  |         /\           /\           /\
  |        /  \         /  \         /  \
  |       /    \       /    \       /    \
  |      /      \     /      \     /      \
  |_____/        \___/        \___/        \____
  |
  +------------------------------------------> Time
```

The upward slopes represent allocations; the drops represent memory reclaimed during collection. This is normal.

Now imagine a different pattern.

```text
Memory
  ^
  |
  |                              /\ 
  |                        /\   /  \
  |                  /\   /  \_/
  |            /\   /  \_/
  |      /\   /  \_/
  |_____/  \_/
  |
  +------------------------------------------> Time
```

This time, the low points keep rising.

Even after collections, more memory remains in use.

That could indicate growing retained state.

Perhaps a cache.

Perhaps a queue.

Perhaps a listener leak.

Perhaps an increasing number of legitimate active sessions.

We need more evidence.

## Heap memory versus process memory

Node.js exposes useful measurements through:

```javascript
console.log(process.memoryUsage());
```

A typical result includes fields such as:

```javascript
{
  rss: ...,
  heapTotal: ...,
  heapUsed: ...,
  external: ...,
  arrayBuffers: ...
}
```

These values measure different things.

### heapUsed

Memory currently used within V8's managed heap, including many JavaScript objects and related managed structures. If retained JavaScript objects accumulate, this may increase.

### heapTotal

The amount of memory V8 has allocated for its managed heap. This is not identical to the amount currently occupied by live JavaScript objects.

### rss

Resident Set Size. This measures process memory resident in physical RAM, including more than the ordinary JavaScript heap: managed memory, native allocations, stacks, executable code, and other process-resident memory.

### external

Memory associated with native allocations bound to JavaScript-managed objects.

### arrayBuffers

Memory allocated for ArrayBuffers and SharedArrayBuffers, including Node.js Buffers. This is also accounted for within the external-memory reporting.

Now imagine a service whose `heapUsed` remains relatively stable while `rss` continues increasing. Would you immediately conclude that JavaScript objects are leaking?

No.

The growth may involve native memory, buffers, fragmentation, allocator behavior, or other memory categories. In fact, on some Linux systems, process RSS can continue increasing despite relatively stable V8 heap metrics because of native allocator fragmentation.

This is why **process memory and JavaScript heap memory are not interchangeable measurements**.

And why a diagnosis based on one monitoring number can be misleading.

---

# 12. The Memory Leak That Doesn't Live in the JavaScript Heap

Here's a particularly interesting Node.js example. Suppose your service downloads large files from an external API and temporarily stores them in memory using Node.js Buffers.

```typescript
const downloadedFiles: Buffer[] = [];

async function downloadFile(url: string) {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error("Download failed");
  }

  const bytes = Buffer.from(
    await response.arrayBuffer()
  );

  downloadedFiles.push(bytes);

  return bytes.length;
}
```

Notice the global array.

Every downloaded file is retained.

Now suppose each file occupies five megabytes.

After one hundred distinct downloads, the application may retain hundreds of megabytes of file contents.

But much of the Buffer's backing memory is accounted for outside V8's ordinary managed JavaScript heap.

So the growth may appear more clearly in `external`, `arrayBuffers`, and process RSS than in `heapUsed`.

A developer watching only `heapUsed` might miss the main source of memory pressure.

This is a real distinction in Node.js applications.

The JavaScript object representing a Buffer and the backing memory containing its bytes are related, but they aren't necessarily accounted for in the same memory category.

## Why this matters operationally

Imagine deploying a Node.js service inside a container with a one-gigabyte memory limit. You increase V8's heap limit because you think the application needs more memory. But the process also allocates large Buffers and other native resources, and those allocations count toward the container's overall memory consumption.

The process can exceed the container's limit even when V8's managed heap is nowhere near its configured maximum. Conversely, a V8 heap exhaustion error can occur while the process still has room below the container's overall memory limit. These are different failure modes.

The useful distinction is:

**A process has a total memory footprint. The JavaScript heap is only one part of it.**

This is especially important for services involving uploads, downloads, file processing, compression, networking, and native libraries.

---

# 13. Diagnosing the Leak Without Guessing

Let's return to our original service.

Memory rises from 140 MB to nearly a gigabyte in four hours.

Restarting fixes it temporarily.

We've learned enough to form hypotheses.

Perhaps the application retains customer profiles in an unbounded Map.

Perhaps it accumulates event listeners.

Perhaps unfinished operations are holding references.

Perhaps a queue is growing faster than workers can process it.

Perhaps Buffers are being retained.

Or perhaps memory growth is legitimate because the application is handling more simultaneous work than before.

How do we distinguish these possibilities?

We need evidence.

## Step one: Establish the pattern

Start by observing memory over time. Don't merely record the maximum value; compare memory usage at similar workload levels. Ask:

- Does usage stabilize?
- Does it continue increasing after traffic decreases?
- Does garbage collection reclaim meaningful amounts?
- Does the retained baseline rise after repeated workloads?
- Is growth correlated with request count, unique users, active jobs, or something else?

Suppose the service processes 100,000 requests.

Memory rises.

Traffic stops.

Garbage collection runs.

Memory remains far above its earlier baseline.

That suggests objects may still be retained.

But we still need to identify them.

## Step two: Separate memory categories

Inspect:

- `heapUsed`.
- `heapTotal`.
- `rss`.
- `external`.
- `arrayBuffers`.

If the managed heap is growing, investigate JavaScript object retention.

If external memory dominates, investigate Buffers, ArrayBuffers, and native resources.

If RSS increases without corresponding growth in these metrics, examine allocator behavior, native memory, and process-level memory accounting.

The correct investigation depends on which part of memory is changing.

## Step three: Reproduce the suspicious workload

Suppose the leak appears to correlate with customer profile lookups. Create a controlled test.

Start the service.

Record memory usage.

Send a large number of requests involving distinct customers.

Allow outstanding work to finish.

Record memory usage again.

Repeat.

If each batch permanently increases retained memory, we've narrowed the investigation.

## Step four: Inspect heap snapshots

Node.js can generate heap snapshots that can be opened in Chrome DevTools. A snapshot describes objects and references present in the managed heap at a particular moment.

You can compare snapshots taken before and after a suspicious workload.

Suppose the first snapshot contains 5,000 cached customer objects.

After another workload, the second contains 50,000.

You investigate those objects.

What retains them?

The tool may reveal a path resembling:

```text
Global environment
       |
       v
customerCache
       |
       v
Map entries
       |
       v
CustomerProfile objects
```

Now we have a concrete explanation: the objects remain reachable because the global cache retains them. This is much more useful than merely knowing that memory usage increased.

## Retained size

Heap profilers often distinguish between an object's own memory footprint and the memory retained through it. An object might occupy only a small number of bytes directly, but if it's the sole path keeping a large graph of objects alive, removing that reference could allow a much larger amount of memory to be reclaimed.

This is the intuition behind **retained size**. A tiny callback can retain an enormous report. A small Map entry can retain a large customer object graph. A single root reference can keep thousands of dependent objects alive. That's why inspecting reference relationships is often more revealing than sorting objects by their individual sizes.

## A practical warning

Heap snapshots are not free. Creating one can pause the application and consume substantial additional memory, and on a production process already close to its memory limit, snapshot generation can cause the process to fail. Use controlled staging environments or carefully isolated production instances when possible.

And remember that heap snapshots may contain sensitive application data, so they should be handled accordingly. The objective is not to collect as many snapshots as possible. It's to use them to answer a precise question:

**What is retaining the memory that should no longer be needed?**

---

# 14. WeakMap: When a Collection Shouldn't Own Its Keys

There's another interesting JavaScript feature worth understanding.

`WeakMap`.

At first glance, it resembles `Map`.

Both associate keys with values.

But their memory-retention behavior differs.

A normal Map holds strong references to its object keys.

As long as the Map itself is reachable, those keys remain reachable through it.

A WeakMap doesn't keep its object keys alive merely because they appear as keys.

This makes WeakMap useful for certain kinds of metadata.

## An example: Object-specific metadata

Imagine a system that attaches internal validation metadata to customer objects. You don't want to modify the customer objects themselves, so you use a collection:

```typescript
const metadata = new WeakMap<object, {
  validatedAt: number;
}>();

function markValidated(customer: object) {
  metadata.set(customer, {
    validatedAt: Date.now()
  });
}
```

If the application eventually stops referencing a customer object elsewhere, its presence as a WeakMap key doesn't by itself prevent collection.

The corresponding metadata can become collectible too. That's useful when the metadata should exist only while the original object exists.

## Why not use WeakMap for every cache?

Because WeakMap solves a specific problem. It doesn't provide ordinary enumeration of keys, so you can't simply ask for all entries. You can't use primitive strings as keys. And you can't rely on garbage collection happening at a predictable time.

For a cache indexed by customer IDs, which are strings, WeakMap isn't a direct replacement for Map. Nor does it guarantee that memory consumption will remain below a particular limit. If you need deterministic eviction, explicit capacity limits, or predictable expiration, you still need an appropriate cache-management strategy.

There are also APIs such as `WeakRef` and `FinalizationRegistry`, but their timing and behavior are intentionally not reliable enough for ordinary resource-lifecycle management.

Garbage collection is a memory-reclamation mechanism, not a scheduling API. A finalizer is not a substitute for explicitly closing a resource. That's the important practical distinction.

---

# 15. Memory Management Is Also a Performance Problem

So far, we've focused on preventing memory leaks. But memory behavior influences performance even when nothing leaks. Consider two approaches to processing one million database records.

## Approach A: Load everything

```typescript
const records = await repository.find();

for (const record of records) {
  await processRecord(record);
}
```

If the dataset is large, this may allocate a substantial collection of objects in memory. Even if every object becomes unreachable after processing, the application has still paid the cost of allocating them, the garbage collector must eventually manage them, and peak memory usage may be unnecessarily high.

## Approach B: Process in bounded batches

```typescript
for await (const batch of loadBatches(1000)) {
  for (const record of batch) {
    await processRecord(record);
  }
}
```

Here, the application processes smaller groups of records. Once a batch is no longer needed and no references retain it, its associated objects can become eligible for garbage collection. This can reduce peak memory requirements and may also improve stability under large workloads.

Of course, real pagination and streaming implementations must account for consistency, database query costs, cursor handling, and failure recovery. But the general principle is useful:

**Don't retain an entire dataset when the problem only requires a small portion at a time.**

## Allocation rate and garbage-collection pressure

Now imagine two services. Both retain 100 MB of live application state, but Service A allocates 10 MB of temporary objects per second while Service B allocates 500 MB. Even with similar long-term retained memory, Service B may create substantially more garbage-collection work, which can affect CPU usage and latency.

This is why performance engineering sometimes involves reducing unnecessary allocations rather than merely reducing retained heap size.

But beware of premature optimization. Modern garbage collectors are highly optimized for short-lived objects, and creating a small temporary object is often perfectly reasonable. You shouldn't turn every function into a maze of object pools and mutable buffers simply to avoid allocations. Measure first. Optimize where the allocation pattern actually matters.

## Large objects and memory pressure

Large arrays, buffers, and object graphs deserve particular attention.

They can increase peak memory consumption dramatically.

They may trigger more collection work.

They may remain alive longer than expected because of references from queues, closures, caches, or active asynchronous operations.

And if enough memory remains retained, the runtime may eventually be unable to allocate more.

This is when memory problems become availability problems.

A service that leaks memory isn't merely wasting RAM.

It's accumulating a future outage.

---

# 16. Practical Lab: Create and Repair a Memory Leak

Now let's make the problem visible.

You only need Node.js.

Create a file named:

`memory-lab.js`

The experiment will intentionally retain some arrays, measure memory usage, and then release them.

Run it locally, not inside a production service.

Start with:

```bash
node --expose-gc memory-lab.js
```

The flag exposes `global.gc()` for diagnostic purposes.

It doesn't make garbage collection perfectly deterministic, and it isn't a general recommendation for production applications.

## Part A — The measurement function

```javascript
function showMemory(label) {
  if (global.gc) {
    global.gc();
  }

  const memory = process.memoryUsage();

  const toMB = bytes =>
    (bytes / 1024 / 1024).toFixed(1);

  console.log(label, {
    heapUsedMB: toMB(memory.heapUsed),
    heapTotalMB: toMB(memory.heapTotal),
    rssMB: toMB(memory.rss)
  });
}
```

This function requests garbage collection before taking a measurement.

That's useful for our controlled experiment because we want to observe retained memory rather than only temporary allocation spikes.

But a manual GC request is not a promise that every possible reclaimable byte is immediately returned to the operating system.

## Part B — The accidental retention

```javascript
const cache = new Map();

function createEntries(start, count) {
  for (let i = start; i < start + count; i++) {
    const payload = new Array(20_000).fill(i);

    cache.set(`customer-${i}`, {
      id: i,
      payload
    });
  }
}
```

Each entry contains an array of 20,000 numbers.

The Map retains the entries.

Now run:

```javascript
showMemory("Initial");

createEntries(0, 100);
showMemory("After 100 customers");

createEntries(100, 100);
showMemory("After 200 customers");

createEntries(200, 100);
showMemory("After 300 customers");
```

Observe the values.

The exact measurements vary by runtime, operating system, and memory representation.

But retained heap usage should generally increase as we add unique entries.

Why?

Because the global Map continues referencing them.

## Part C — Release the objects

Now add:

```javascript
cache.clear();

showMemory("After clearing cache");
```

What happens?

The Map no longer retains the customer objects.

Assuming no other references remain, those objects can become eligible for collection.

The reported managed heap usage should generally decrease following collection.

But RSS may remain relatively high.

Why?

Because the runtime and native allocators don't necessarily return all available memory to the operating system immediately.

Freed memory may be retained for future allocations.

That's another reason memory measurements require interpretation.

## Part D — Make a prediction

Before running the experiment, predict the answers:

1. Why does the memory grow even though each function call finishes?
2. Why doesn't the garbage collector automatically delete old cache entries?
3. What does `cache.clear()` change about the object graph?
4. Why might `heapUsed` fall without an equally large drop in RSS?
5. What would happen if each cached entry also retained a large Buffer?

After running it, explain the behavior in terms of reachability rather than simply saying "JavaScript uses the heap."

That's the level of understanding we're aiming for.

---

# 17. Four Engineering Challenges

These exercises are closer to the problems you might encounter while operating or designing actual software.

## Challenge A — The Growing Queue

**Suggested time: 8 minutes**

A background worker receives jobs from a queue.

Each job contains an in-memory representation of a customer request.

The worker processes 100 jobs per second.

But the system receives 150 jobs per second.

What happens over time if the queue retains every pending job in memory?

Is this a memory leak?

How would you distinguish legitimate queue growth from accidental memory retention?

What architectural measures could prevent the service from running out of memory?

Think about backpressure, bounded queues, durable storage, and admission control.

## Challenge B — The Vue Dashboard

**Suggested time: 8 minutes**

A dashboard component registers:

- A window resize listener.
- A WebSocket subscription.
- A repeating timer.
- A callback that captures a large chart dataset.

The user navigates away from the dashboard.

The component disappears visually.

But memory usage doesn't fall.

What might be retaining the objects?

What should happen when the component is unmounted?

How would you investigate whether the component is genuinely unreachable?

## Challenge C — The Strange Memory Metrics

**Suggested time: 10 minutes**

A Node.js service reports:

| Metric | Before | After |
|---|---:|---:|
| heapUsed | 120 MB | 125 MB |
| heapTotal | 180 MB | 190 MB |
| external | 80 MB | 600 MB |
| rss | 270 MB | 820 MB |

What would you investigate first?

Would you immediately increase the V8 heap limit?

Why might this situation occur in a service that downloads and processes files?

What information would help confirm the cause?

## Challenge D — The Cache That Knows Too Much

**Suggested time: 10 minutes**

A SaaS service caches customer profiles.

The cache is limited to 10,000 entries.

A developer proudly announces:

"We've solved the memory leak. The cache is bounded."

Have they necessarily solved every memory problem?

Consider:

- Variable-sized cached objects.
- Closures referencing evicted entries.
- In-flight requests retaining old objects.
- Buffers associated with the profiles.
- Expiration and invalidation.
- Multiple cache instances.
- External libraries holding additional references.

What additional guarantees or measurements would you want?

---

# 18. Solutions and Discussion

*Read after attempting the challenges.*

## Challenge A — Growing queue

The queue receives 50 more jobs per second than it completes. If the arrival and processing rates remain constant, the backlog grows by roughly 3,000 jobs per minute, and if every job remains in memory, memory usage can grow continuously.

This is not necessarily a traditional memory leak—the jobs may still be legitimately pending—but the system is accumulating work faster than it can complete it. Operationally, the result can be just as dangerous as a leak.

Possible responses include:

- Increasing processing capacity where appropriate.
- Applying backpressure.
- Limiting queue length.
- Rejecting or deferring new work.
- Persisting jobs durably rather than retaining the entire backlog in process memory.
- Monitoring queue age and backlog size.
- Investigating why throughput is insufficient.

The deeper issue is capacity management.

Garbage collection cannot solve a workload that requires retaining more information than the system can safely hold.

## Challenge B — Vue dashboard

The component may be retained by external listeners, timers, subscriptions, callbacks, or other objects that still reference it or its data.

Unmounting the visual component doesn't automatically guarantee that every manually registered external resource has been released. Cleanup should remove listeners, unsubscribe from external streams, and stop timers, and the application should also release references to chart data that is no longer needed.

A browser heap snapshot can help identify retained objects and their reference paths, but a single snapshot doesn't prove a leak. Comparing behavior across repeated mount/unmount cycles is more informative.

## Challenge C — Memory metrics

The major change is in external memory and RSS; the managed JavaScript heap barely grows. This suggests investigating Buffer allocations, ArrayBuffers, native modules, or other externally accounted memory. A file-processing service is a plausible source, and increasing the V8 heap limit may not address the underlying cause.

Useful evidence includes Buffer allocation patterns, retained references, workload correlation, native-memory behavior, and repeated measurements after processing finishes.

## Challenge D — Bounded cache

Limiting the number of entries is useful, but it's not a complete guarantee of bounded memory usage.

An entry may contain a tiny object or a huge dataset. Other parts of the application may retain references to objects after cache eviction. There may be several independent caches, and a cache may also hold native or external memory.

The system needs an appropriate retention policy and observability. Depending on the application, that could include maximum memory budgets, entry-size accounting, expiration, eviction, and monitoring of retained heap and process memory.

A bounded entry count is one useful control—not proof that memory usage cannot become excessive.

---

# 19. The Bigger Picture: Memory Is About Responsibility

The call stack tracks active execution; deep recursion can exhaust it. Heap objects outlive the functions that created them while they remain reachable. References share identity — mutating through one alias affects others; reassignment is different from mutation.

GC follows reachability from roots: objects stay alive even without a business reason. Unbounded caches, callbacks, listeners, timers, and queues still leak. Memory isn't one resource — JS heap, native allocations, Buffers, and stacks contribute differently to metrics. Growth isn't always a leak. Efficiency affects latency. External resources need explicit cleanup.

When something won't disappear, ask: who still owns this?

Back to the leaking service. Raising the memory limit only postpones the outage if retention keeps growing — 200 MB per hour still fails later. Every value has a useful lifetime: request, session, workflow, process. The runtime manages physical allocation; the application owns intended business lifetime.

Long-running Node services, SPAs, and agent workflows cannot rely on frequent process death to clean up. AI can generate a cache without eviction or a subscription without cleanup. Consequences appear after enough time and state.

**In a garbage-collected language, you usually don't decide when memory is physically freed. But you still decide which objects remain reachable—and therefore which objects the runtime is required to keep alive.**

A growing memory graph becomes investigable. What is retained? Why reachable? Should it still be alive? Who owns its lifetime?

---


---

## Next Lecture — CS220-L03: How Programs Actually Execute

Continue in **CS220 — Programming Languages, Memory, and Execution**.

