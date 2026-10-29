---
id: CS220-L07
course: CS220
title: "Native Runtimes: Go, Rust, and Execution Trade-offs"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: CS220-L06
next: CS220-L08
---

# CS220 — Languages, Types, Memory, and Runtimes

## Lecture 07: Native Runtimes — Go, Rust, and Execution Trade-offs

*One team rewrites a cybersecurity scanner in Go. Another chooses Rust. Both produce native executables. The Go service gradually accumulates thousands of goroutines. The Rust service consumes surprisingly little memory but still gets killed under load. Neither language has malfunctioned. The teams have simply discovered that native code doesn't abolish the operating system, resource limits, or bad architecture.*

---

# Part I — Intuition

## The picture to carry in your head

Imagine a cybersecurity platform that discovers external assets belonging to its customers.

A customer submits a domain name.

The platform discovers subdomains, resolves IP addresses, identifies web servers, inspects exposed services, and combines the findings into a report.

A single scan may produce thousands of independent tasks.

Some involve network requests that spend most of their time waiting.

Others perform expensive local computations, parsing large responses or analyzing collected data.

The platform originally uses a mixture of Python and Node.js.

Now the engineering team wants a dedicated scanner service.

Two proposals reach the architecture meeting.

One suggests Go.

The other suggests Rust.

Both languages commonly compile ahead of time into native machine code.

Both can execute across multiple CPU cores.

Both have mature networking ecosystems.

So what's the actual difference?

## 1. Native code is a destination, not an architecture

Imagine a company manufacturing machinery.

It builds two machines using the same high-quality metal.

One machine contains automated scheduling, maintenance, and inventory management.

The other gives the operator much more direct control over how resources are allocated and released.

Both are machines made from metal.

But their internal management systems differ enormously.

Go and Rust are similar in that sense.

Both commonly produce native executables.

But Go includes a substantial runtime that schedules goroutines, manages memory, and performs garbage collection.

Rust ordinarily relies on ownership-based resource lifetimes, without requiring a general-purpose tracing garbage collector.

A Rust application can still depend on an asynchronous scheduler, memory allocator, thread libraries, and operating-system facilities.

The fact that both eventually execute machine instructions tells us surprisingly little about their resource-management strategies.

## 2. Go gives you inexpensive concurrent activities

Imagine scanning one thousand web servers.

Most individual requests spend time waiting for a response.

Go allows the programmer to start a goroutine for each concurrent activity.

A goroutine is much lighter than dedicating one permanent operating-system thread to each request.

The Go runtime schedules goroutines onto operating-system threads.

When one goroutine waits for network I/O, others can make progress.

This makes concurrent network programming convenient.

But what if the scanner starts a million goroutines?

The runtime can't make the memory and scheduling overhead disappear.

Each goroutine needs state.

Blocked goroutines may retain objects.

The network has finite capacity.

Remote services have rate limits.

And the application has a finite memory budget.

Cheap concurrency is still not free concurrency.

## 3. Rust makes ownership a visible responsibility

Now imagine the Rust implementation.

The scanner receives a response buffer, parses it, extracts useful findings, and discards the original bytes.

Rust's ownership model helps establish who owns the buffer and when its resources can be released.

It can prevent important classes of use-after-free, double-free, and conflicting-access bugs in safe code.

That is valuable for software that handles large amounts of data, native resources, and concurrency.

But the compiler doesn't know whether the scanner should retain a response for five seconds or five days.

If the application deliberately stores every response in a growing collection, Rust will preserve those values as long as they're owned or otherwise kept alive.

Memory safety doesn't imply a memory budget.

## 4. Go and Rust approach asynchronous work differently

Here's a subtle distinction.

In Go, launching a goroutine starts a concurrent activity. It becomes eligible for scheduling and can progress independently.

In Rust, calling an ordinary `async` function creates a future.

That future is lazy.

It doesn't run to completion merely because the value exists.

Something must drive it—typically through an executor that polls it as progress becomes possible.

An async runtime such as Tokio can manage many such tasks.

Both languages can support efficient concurrent network I/O.

But the execution model differs.

A Go programmer must think about the lifetime of goroutines they've started.

A Rust async programmer must think about future polling, task ownership, and cancellation behavior.

Neither model automatically enforces application-level deadlines or bounded concurrency.

## 5. The two services fail in different ways

The Go implementation begins one goroutine per scan task.

A coordinator collects results from a channel.

When the customer cancels the scan, the coordinator stops receiving results.

Several worker goroutines remain blocked trying to send their findings.

They never finish.

The number of live goroutines grows after repeated cancelled scans.

The service's memory use rises.

The garbage collector works correctly but cannot reclaim data retained by those still-running goroutines.

Now consider the Rust implementation.

Its developers create a highly optimized native parser.

The parser processes each finding quickly.

But the application queues every unprocessed scan result in memory and launches more tasks than its container can sustain.

Eventually, the kernel enforces the container's memory limit.

The process dies.

Rust prevented unsafe memory access.

It didn't impose a limit on the amount of valid memory the program was allowed to use.

Both failures are architectural.

## 6. The right question isn't which language is safer or faster

Go prioritizes straightforward concurrency, productive tooling, and automatic memory management.

Rust prioritizes explicit ownership, strong static safety guarantees, and precise control over resource representation.

Both can produce excellent backend systems.

Both can produce disastrously inefficient ones.

The right decision depends on the workload.

Does it spend most of its time waiting for networks?

Does it process large data buffers?

Is predictable allocation important?

How much engineering complexity can the team reasonably absorb?

Which libraries and diagnostics will it need?

And most importantly, is the existing runtime actually responsible for the bottleneck the team wants to eliminate?

### The mental picture

```text
                    SOURCE CODE
                         |
              Ahead-of-time compilation
                         |
                  Native executable
                         |
              +----------+----------+
              |                     |
              v                     v
             GO                    RUST

       Runtime scheduler      Ownership and Drop
       Goroutines             Explicit resource design
       Tracing GC             No required tracing GC
       Channels               Threads, channels, futures
       Runtime services       Selected libraries/executors
              |                     |
              +----------+----------+
                         |
                         v
                Operating system
                         |
                         v
               Finite CPU, RAM, I/O
```

The differences live in the machinery and contracts between source code and available resources.

### Three questions before the Deep Dive

1. Why is it inaccurate to say that Go has no runtime because it compiles to native code?
2. Why can a Go program leak goroutines even when its garbage collector works correctly?
3. Why can safe Rust code still exhaust a container's memory?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The Scanner Architecture Meeting

Our security platform processes external-attack-surface scans.

A scan begins with a customer domain and expands into a graph of assets.

DNS records reveal names and addresses.

Ports expose services.

Web endpoints reveal technologies.

Supporting scanners collect evidence and produce findings.

The workload combines many small network operations with some heavier processing.

The existing Python workers perform adequately, but the team wants to simplify deployment and improve resource efficiency.

One proposal recommends rewriting the scanner in Go.

Another favors Rust.

The engineering manager asks a sensible question:

"Which one will make scanning faster?"

The answer depends on what scanning currently spends time doing.

If most wall time comes from network waiting, reducing arithmetic overhead may do little.

If parsing and transformation consume substantial CPU, native computation may help.

If the bottleneck is the number of outgoing connections, more lightweight tasks may make matters worse.

Before choosing a language, we need to understand what each implementation actually provides.

## 2. Native Compilation Doesn't Mean Runtime-Free Execution

Go and Rust commonly use ahead-of-time compilation.

Their compilers translate source through intermediate representations into machine code for a target architecture.

The resulting binary can execute without requiring a separate language virtual machine comparable to the ordinary JVM.

But this doesn't mean execution requires no runtime support.

### Go's runtime

A typical Go executable includes runtime machinery for:

- Goroutine scheduling.
- Memory allocation and garbage collection.
- Stack management.
- Integration with operating-system threads.
- Network polling.
- Timers and other execution services.

The compiled program and its runtime cooperate.

Go is therefore a compiled language with a substantial runtime.

Those statements are not contradictory.

### Rust's runtime dependencies

Ordinary Rust programs can execute without a general tracing garbage collector or a language-wide managed virtual machine.

But Rust applications may still depend on:

- A memory allocator.
- Operating-system threads and synchronization.
- Standard-library facilities.
- An asynchronous executor.
- Native system libraries.
- Runtime resource-management code.

Rust's compiler can generate machine code that performs operations directly, but the application still needs infrastructure to interact with its environment.

### Why terminology matters

If someone says Go is fast because it is compiled, ask what they actually mean.

Are they comparing pure computation?

Memory representation?

Startup costs?

Scheduler overhead?

Garbage-collection behavior?

Likewise, if someone says Rust is fast because it has no runtime, clarify that Rust has runtime behavior and supporting libraries, but doesn't require a general tracing GC for ordinary owned values.

The useful comparison concerns mechanisms, not slogans.

## 3. Go Goroutines: Lightweight Concurrent Execution

A goroutine is a unit of concurrent Go execution.

The language makes it easy to start one.

For example, a scanner can launch a goroutine that requests an HTTP endpoint while the coordinating function continues.

The goroutine doesn't require a permanently dedicated operating-system thread.

The Go runtime schedules runnable goroutines onto available execution resources.

### The G–M–P model

A common conceptual model of the Go scheduler uses three components.

**G** represents a goroutine.

**M** represents an operating-system thread managed or used by the runtime.

**P** represents a logical scheduling resource required to execute Go code.

The runtime associates runnable goroutines with execution resources and schedules them across threads.

This isn't a promise that the internal implementation will remain identical across every Go release.

It's a useful way to understand why goroutine count and operating-system thread count are different.

### Waiting versus running

Suppose a goroutine sends an HTTP request and waits for the response.

The runtime can allow other goroutines to execute while that network operation is pending.

The waiting goroutine still has state.

Its local values and references may remain reachable.

But it doesn't need to consume a full CPU core while waiting.

This is why Go is comfortable for network servers and concurrent scanners.

### CPU execution

Now suppose a goroutine performs expensive JSON transformations.

That computation needs CPU time.

Several runnable goroutines can execute simultaneously across available logical processors when the runtime and operating system permit it.

But having ten thousand runnable goroutines doesn't create ten thousand processors.

They compete for finite CPU execution capacity.

The distinction is identical in spirit to our Node.js and JVM discussions:

**Concurrency describes the number of activities that can be in progress. Parallelism describes the work that actually executes simultaneously.**

## 4. GOMAXPROCS: How Much Go Code Can Execute at Once?

Go exposes a runtime setting called `GOMAXPROCS`.

It controls how many logical processors can execute ordinary Go code simultaneously, subject to runtime-specific qualifications.

It is not the number of goroutines.

A service can have thousands of goroutines while its `GOMAXPROCS` value is four.

Some goroutines may be waiting.

Others may be runnable but waiting for execution time.

Only a bounded number can execute Go code in parallel.

### The container problem

Imagine deploying a Go scanner to Kubernetes.

The host machine has thirty-two logical processors.

The container has a CPU limit of two cores.

Historically, a Go runtime might choose a default parallelism based largely on the machine's available logical CPUs.

That could cause the program to attempt more simultaneous execution than its CPU quota comfortably supports.

The Linux kernel might then throttle the container.

The host could appear to have spare CPU while the scanner experiences significant latency from quota enforcement.

### A modern improvement

Starting with Go 1.25, the runtime's default `GOMAXPROCS` behavior can account for Linux cgroup CPU limits when an explicit override isn't in place.

It can also periodically update the default when relevant limits change.

The details depend on the runtime version and configuration.

Importantly, this behavior concerns CPU limits, not simply Kubernetes CPU requests.

A request and a limit have different scheduling implications.

### Why this doesn't solve every CPU problem

The runtime can choose a more container-aware default.

But it cannot guarantee that every workload remains efficient.

A process might still be throttled.

A poorly chosen explicit override may defeat the default behavior.

A large number of CPU-heavy goroutines may create scheduling overhead.

And memory bandwidth or downstream services may become bottlenecks.

Runtime defaults are useful.

They don't eliminate capacity engineering.

## 5. The Goroutine Leak: A Task With No Way to Finish

Our scanner's first production problem appears after customers begin cancelling scans.

A scan coordinator starts several goroutines.

Each worker scans a target and sends its result to a channel.

The coordinator collects results until the scan completes or the customer cancels.

On cancellation, the coordinator exits.

But some workers are still running.

One worker finishes its scan and attempts to send the result.

Nobody is receiving from the channel anymore.

The send blocks.

The goroutine remains alive.

More cancelled scans produce more blocked senders.

### Why garbage collection doesn't help

The goroutine still exists as an active runtime execution unit.

It may retain its stack state, references, response buffers, and other objects.

The garbage collector can't simply decide that the goroutine is no longer useful and terminate it.

A goroutine must reach a completion path or otherwise be terminated through the program's intended lifecycle mechanisms.

This is a goroutine leak.

It's closely related to the callback and queue retention problems we examined in CS220-L04.

The allocation might be perfectly legitimate.

The missing exit condition is the bug.

### The cancellation-aware design

A worker sending a result should be able to observe cancellation.

One common Go pattern uses a `select` statement with two possible operations.

The first attempts to send the result.

The second waits for the cancellation context to become done.

If the coordinator has stopped accepting results, the worker can abandon the send and exit.

The implementation must also ensure that network calls, timers, and other blocking operations participate in cancellation where supported.

### Context propagation

Go's `context.Context` provides a standard way to propagate cancellation, deadlines, and request-scoped metadata across API boundaries.

A scan can have a root context.

Worker operations can derive contexts from it.

When the scan is cancelled, downstream operations can observe that cancellation.

But a context doesn't forcibly terminate arbitrary code.

The code or library must cooperate.

And cancellation doesn't undo external actions already performed.

This is a general distributed-systems rule, not a weakness peculiar to Go.

## 6. Channels, Ownership, and Backpressure

Go channels provide communication between goroutines.

A sender can transmit a value.

A receiver can receive it.

The channel's capacity and state determine whether an operation can proceed immediately or must wait.

### Unbuffered channels

An unbuffered channel coordinates a send and a receive.

The sender cannot complete the send without a corresponding receiver participating.

This can be useful for synchronization.

But it can also create indefinite blocking if the receiver disappears.

Our goroutine leak is one example.

### Buffered channels

A buffered channel can hold a bounded number of values.

A sender can proceed while buffer capacity remains available.

When the buffer fills, additional sends normally block until space becomes available.

This can provide backpressure.

But a buffered channel isn't an automatic cancellation strategy.

If the receiver exits and the buffer eventually fills, senders can still become stuck.

### Buffering versus capacity

Suppose the scanning platform can process one hundred results per second.

Workers collectively produce five hundred.

Increasing the channel buffer from one thousand to ten thousand delays the point at which producers block.

It doesn't fix the sustained capacity mismatch.

Eventually, the buffer fills.

Or, if the application continually expands buffering elsewhere, memory demand grows.

The correct design must reconcile production rate, consumption capacity, and the business's desired handling of excess work.

### Channels aren't inherently superior to mutexes

Go's concurrency culture often emphasizes communicating through channels.

That's useful, but channels aren't the best solution for every shared-state problem.

A mutex may be simpler for protecting a small shared data structure.

A channel may be ideal for coordinating ownership of a stream of tasks.

The choice should follow the access pattern.

A design becomes difficult when it introduces complicated channel choreography for data that could be protected safely with a straightforward lock.

## 7. Go Garbage Collection: Convenience Has a Budget

Go uses tracing garbage collection for ordinary managed heap objects.

The runtime tracks reachable objects and reclaims unreachable allocations according to its collection algorithms.

This reduces the need for application code to manually release ordinary heap allocations.

But the collector consumes CPU and memory resources.

### Allocation and retention

Imagine each scanner worker allocates a response buffer.

The buffer is parsed.

A small finding is extracted.

If the worker releases its references to the response buffer, the buffer can become eligible for collection.

But if the scanner stores every complete response in a global results registry, those buffers remain reachable.

The collector can't reclaim them.

This is the same reachable-versus-useful distinction we studied in L04.

### GOGC

Go exposes a garbage-collection tuning parameter called `GOGC`.

Conceptually, it influences the heap growth target relative to the live heap after collection, along with the runtime's broader memory-management behavior.

A higher target may allow more allocation between collections at the cost of more heap memory.

A lower target can increase collection frequency and CPU overhead while reducing some heap-growth pressure.

The correct choice depends on the workload.

Tuning the collector without first understanding retention is usually a poor use of engineering time.

### GOMEMLIMIT

Go also supports a soft runtime memory limit through `GOMEMLIMIT` or the corresponding runtime API.

The limit covers memory managed by the Go runtime according to its documented accounting, not necessarily every byte the process or operating system can attribute to the application.

It is not a hard container memory limit.

Under heavy allocation pressure, the runtime may exceed the soft target rather than spend an unreasonable amount of CPU time attempting to collect memory.

### Why this matters in Kubernetes

Suppose a scanner container has a 512 MiB memory limit.

Setting `GOMEMLIMIT` to exactly 512 MiB doesn't guarantee that total process memory stays under the container limit.

Some memory use falls outside the runtime's accounting.

The application also needs headroom for stacks, native allocations, executable mappings, and other overhead.

More importantly, a soft memory limit cannot make an unbounded queue or registry logically bounded.

The collector can't discard live findings without violating the application's intended state.

**A garbage collector manages reclamation. It doesn't invent your application's retention policy.**

## 8. Go Native Compilation and Operational Simplicity

Go is commonly praised for producing convenient deployable binaries.

A typical Go service can be compiled into a native executable for a target operating system and architecture.

This can simplify deployment compared with environments requiring an separately installed language interpreter or VM.

But the details depend on the build.

### CGO and native dependencies

Go supports calling C code through cgo.

That can be useful when integrating native libraries.

It can also introduce linking, platform, cross-compilation, and deployment considerations.

A Go executable is not necessarily a fully static binary merely because the compiler produced one file.

Its dependency behavior depends on cgo usage, build configuration, and target platform.

### Cross-compilation

Go makes cross-compilation convenient for many ordinary targets.

You can often configure the target operating system and architecture through build settings.

But cross-compilation becomes more complicated when native dependencies are involved.

The target's C toolchain, system libraries, and ABI may matter.

### Startup and packaging

A Go server can often start without an expensive general-purpose VM initialization phase.

This may benefit short-lived jobs, command-line tools, and infrastructure utilities.

But actual startup depends on application initialization, configuration, database connections, and library behavior.

A native executable that downloads a large configuration file before serving requests can still start slowly.

Again, deployment format is one factor, not a full performance promise.

## 9. Rust: Native Code With Ownership-Based Resource Management

Now consider the Rust scanner.

The team wants tight control over parsing, memory allocation, and resource lifetimes.

Rust's ordinary compilation pipeline produces native machine code through compiler and backend infrastructure.

Its ownership and borrowing system helps enforce memory safety in safe code.

We studied the basic ownership rules in L03.

Here, the focus is how those rules affect application execution.

### Predictable scope-based cleanup

Suppose the scanner reads a file into a buffer.

It parses the data.

Then the owning value goes out of scope.

Rust's drop mechanism runs the appropriate destructor for that value.

Resources owned by it can be released through the relevant implementation.

This is deterministic resource management for ordinary scope-based lifetimes.

It differs from waiting for a tracing garbage collector to notice that a managed object has become unreachable.

### But not every resource belongs on the stack

A common misconception says Rust stores everything on the stack.

False.

Rust frequently uses heap allocations.

A `Vec` stores its elements in a heap allocation.

A `String` commonly owns heap-backed data.

`Box` provides heap allocation.

Shared ownership mechanisms such as `Rc` and `Arc` also exist.

Ownership rules describe who manages resources and how their lifetimes are controlled.

They don't imply that all data avoids the heap.

### Resource lifetimes can still be extended

An application may store a large `Vec` in a long-lived global or shared structure.

It remains alive until the relevant owner releases it.

A reference-counted cycle can also retain memory in certain designs.

Rust even provides mechanisms that intentionally avoid running ordinary destructors.

So ownership-based cleanup doesn't mean memory can never leak.

It means the language offers stronger tools for making ordinary resource lifetimes explicit and safe.

## 10. Rust Memory Safety and Its Limits

The compiler enforces many rules that prevent unsafe memory access in ordinary safe Rust.

For example, code cannot generally use a value after ownership has moved.

A reference cannot outlive the data it refers to under the relevant borrowing rules.

Conflicting mutable access is restricted.

These guarantees eliminate important classes of defects.

### Send and Sync

Rust uses marker traits called `Send` and `Sync` to express concurrency-related properties.

Very roughly, `Send` indicates that ownership of a value can safely be transferred between threads.

`Sync` indicates that shared references to a value can safely be used across threads.

These aren't merely documentation comments.

The compiler uses these properties when checking threaded code.

For example, ordinary non-atomic reference counting through `Rc` isn't suitable for unrestricted cross-thread sharing.

Rust provides `Arc`, which uses atomic reference counting for appropriate shared ownership across threads.

### Atomic ownership isn't mutable synchronization

An `Arc` allows multiple owners to refer to one allocation safely under its rules.

But it doesn't automatically make arbitrary mutation of the contained data safe.

For mutable shared state, a design may use `Arc<Mutex<T>>` or another synchronization mechanism.

The mutex protects access to the inner value.

The `Arc` manages shared ownership.

These are separate responsibilities.

### Safe Rust can deadlock

Suppose two threads acquire locks in opposite orders.

Thread A acquires lock 1 and waits for lock 2.

Thread B acquires lock 2 and waits for lock 1.

Both may wait indefinitely.

The memory accesses are properly synchronized.

The program is still wrong.

Likewise, safe Rust can have an infinite loop, allocate excessive memory, lose messages, or perform an unauthorized business operation.

Memory safety is a substantial guarantee.

It isn't total correctness.

## 11. Rust Async: Futures Need an Executor

Now consider the network-intensive part of the scanner.

The Rust team wants to run thousands of HTTP requests concurrently.

Rust supports async functions and futures.

But its model differs from Go's goroutines.

### Lazy futures

Calling an async Rust function produces a future representing a computation.

Ordinarily, that future doesn't begin performing its body simply because it was created.

It must be polled.

Awaiting a future arranges for it to be driven through the surrounding async execution context.

An executor manages how futures are scheduled and polled.

### Polling and readiness

A future implements behavior that can report either that its result is ready or that it remains pending.

When it can't make progress, it arranges for a suitable wakeup when progress may become possible.

The executor can then poll it again.

This cooperative design allows large numbers of asynchronous operations to share a smaller set of execution threads.

But it requires that asynchronous code cooperate with the model.

### Rust doesn't prescribe one universal async runtime

Rust's language and standard library define futures and related mechanisms.

Applications commonly use an async runtime such as Tokio or another executor and I/O ecosystem.

That runtime provides scheduling and integration with networking, timers, and task management.

The compiler doesn't automatically give every Rust program a global event loop.

This is an important distinction from Go, whose runtime provides goroutine scheduling as a standard execution facility.

### CPU work remains CPU work

An async Rust function that performs a long synchronous CPU calculation without yielding can occupy an executor worker.

Other tasks scheduled on that worker may be delayed.

For substantial CPU-intensive workloads, the application may use dedicated threads, a CPU-oriented executor, or an appropriate blocking-task facility.

The async keyword is not a parallelism switch in Rust any more than it is in Node.js or Python.

## 12. Cancellation: Goroutines and Futures Have Different Lifecycles

Our customers can cancel scans.

How does cancellation work in Go and Rust?

### Go's cooperative cancellation

In Go, a goroutine continues executing until its code returns or the process ends.

A cancellation context provides a signal and deadline information.

The goroutine must observe the signal, or use operations that support the context, and exit appropriately.

If it remains blocked on an unrelated channel operation without a cancellation path, the context alone won't rescue it.

This is how our goroutine leak occurred.

### Rust's future cancellation

In ordinary async Rust, dropping a future stops that particular future from being polled further.

Its owned state is dropped according to the applicable rules.

This makes cancellation closely connected to ownership.

But the details matter.

An async operation may have already spawned independent background tasks.

Dropping the original future doesn't necessarily stop those tasks.

A future might have initiated an external side effect before being cancelled.

### Cancellation safety

Imagine a future reading part of a message from a stream.

It receives some bytes and stores them in internal state.

Then it is cancelled.

If the future is dropped, that partial progress may be lost.

If the application recreates the operation from the beginning, the message may not be recoverable correctly.

This is why Rust async APIs sometimes document whether an operation is cancellation-safe.

The practical question is what happens if the future is dropped at an await point.

Does the operation leave external or shared state in a condition that permits safe retry or resumption?

### The common distributed boundary

Suppose the scanner sends an HTTP request that triggers a state-changing operation.

The client cancels before receiving the response.

The remote server may still have completed the operation.

Neither Go's context cancellation nor Rust's future dropping can guarantee rollback of that external action.

The application still needs idempotency and reconciliation where business correctness requires them.

**Cancellation controls local participation in an operation. It doesn't automatically reverse effects outside the process.**

## 13. CPU Work: Go and Rust Both Need Real Processors

Now consider the expensive parsing stage.

The platform has millions of collected findings.

Each finding must be classified, normalized, and inserted into an output structure.

Both Go and Rust can execute native machine code.

Both can distribute independent work across available processor cores.

But how that parallelism is expressed differs.

### Go

The application may divide findings among goroutines.

The Go scheduler maps runnable work onto available logical processors.

A bounded worker pool can provide reasonable task granularity and prevent enormous numbers of tiny goroutines.

The collector manages ordinary heap allocations produced during processing.

### Rust

The application may use operating-system threads or a suitable parallel-computation library.

Ownership rules can help partition data into independent chunks and restrict conflicting access.

The compiler can generate efficient native loops.

But performance depends on data layout, algorithmic design, synchronization, and build configuration.

### The task-granularity problem

Suppose each finding requires only a few hundred nanoseconds of computation.

Launching a separate scheduled task for every finding may cost more than performing the computation itself.

It can be better to assign batches of findings to a bounded number of workers.

This applies to Go and Rust.

Parallelism should increase useful work per unit time, not merely increase the number of scheduling objects.

### Memory bandwidth

Even if the computation is perfectly divisible, all workers may need to read large volumes of data from memory.

Eventually, memory bandwidth or cache behavior can limit scaling.

Adding more threads or goroutines may produce diminishing returns.

A faster language doesn't remove hardware resource limits.

## 14. Numeric Correctness: Same Algorithm, Different Results

Suppose the scanning platform calculates risk scores using integer arithmetic.

Or return to the booking platform's monetary calculations.

Go and Rust support fixed-width integer types.

But their overflow and conversion rules differ.

### Go integer behavior

Go provides signed and unsigned integer types of specified widths, along with `int` and `uint` whose widths depend on the target architecture.

Fixed-width integer arithmetic has defined rules, but exceeding the representable range can produce results different from mathematical integer arithmetic.

Signed overflow does not give the compiler a general license to assume that overflow can never occur.

The exact operation and type matter.

### Rust integer behavior

Rust provides explicit integer types such as `i32`, `u64`, and others.

Integer overflow checks depend on operation and build configuration.

Rust also provides explicit APIs for checked, wrapping, saturating, and overflowing arithmetic.

For example, checked arithmetic can report that a result doesn't fit the selected representation.

Wrapping arithmetic intentionally follows modular arithmetic.

Saturating arithmetic clamps results to representable bounds.

These mechanisms let developers express the required behavior more explicitly.

### Release versus debug

Rust development builds and optimized release builds may differ substantially in execution speed.

They may also differ in the default treatment of certain integer-overflow checks, subject to build configuration.

Therefore, a benchmark must define arithmetic semantics and compilation settings.

An implementation that silently wraps a monetary value while another reports an error is not performing the same business computation.

### The actual engineering decision

For money, choose a representation that preserves the required precision and range.

For risk scores, define the valid bounds and overflow policy.

For large counters, consider whether fixed-width arithmetic is sufficient.

Numeric correctness is part of the application contract.

A faster incorrect result isn't an optimization.

## 15. Native Performance: What Actually Makes a Program Fast?

Now we can revisit the original proposal.

"Rust is fast because it compiles to native code."

"Go is fast because it compiles to native code."

Both statements are too shallow.

Native compilation can remove some forms of runtime interpretation overhead.

But actual performance depends on the generated machine code and the work it performs.

### Algorithmic complexity

A Go implementation using an efficient index can outperform a Rust implementation repeatedly scanning a large array.

The improvement comes from the algorithm.

The language doesn't rescue unnecessary work.

### Data representation

A Rust program storing compact fixed-field structs may have favorable cache locality.

A Go program using slices of structs can also benefit from compact data.

Either language can instead create pointer-heavy object graphs that generate more memory traffic.

The representation matters.

### Allocation

A Rust program can allocate excessively.

A Go program can avoid unnecessary allocations.

Rust's ownership model doesn't automatically eliminate heap allocation.

Go's collector doesn't automatically make allocation expensive enough to dominate every workload.

### Synchronization

A heavily contended mutex can serialize computation in either language.

A channel pipeline can create unnecessary bottlenecks.

Atomic operations have costs and require correct memory-ordering semantics where applicable.

### I/O waiting

If 95 percent of a scan's latency is spent waiting for remote services, a faster local parser may have limited impact on end-to-end latency.

The runtime choice should address the actual limiting part of the workload.

**Native compilation can reduce some execution overhead. It cannot reduce work that the program still unnecessarily performs.**

## 16. Deployment: One Binary Isn't Always One Dependency

Both Go and Rust can produce native executables suitable for container deployment.

This can be attractive for infrastructure services.

But binary deployment has practical nuances.

### Target operating system and architecture

A binary is compiled for a target platform.

Linux AMD64 and Linux ARM64 are not the same target.

A binary built for one operating system doesn't generally run on another without appropriate compatibility facilities.

The build pipeline needs to select the right target.

### Linking

A program may be statically or dynamically linked, depending on toolchain configuration and dependencies.

A dynamically linked binary may require compatible system libraries in the runtime environment.

This matters for minimal container images.

A binary that runs on a developer's laptop may fail in a stripped-down container if required libraries aren't available.

### Go's native integration

Using cgo may introduce additional native linking and cross-compilation concerns.

For ordinary pure-Go applications, deployment can be simpler.

But don't assume every Go executable is completely self-contained under every configuration.

### Rust's native integration

Rust can target different architectures and standard-library environments.

Linking against glibc, musl, or other system libraries changes portability characteristics.

Native dependencies can complicate cross-compilation.

The build system must produce an artifact suitable for the intended deployment image.

### Operational consequences

Small deployment images and fast startup can be useful.

But they don't eliminate configuration management, certificate handling, observability, secret management, or vulnerability patching.

A native scanner still needs to be operated as a production service.

## 17. Observability: How Do You Investigate a Native Service?

Imagine the Go scanner's memory usage rises.

Imagine the Rust scanner's CPU utilization approaches its container limit.

How do we diagnose them?

### Go profiling

Go provides runtime profiling and tracing facilities.

CPU profiles can identify where active processor time is spent.

Heap profiles can reveal allocation and retention patterns.

Goroutine profiles can help identify large numbers of goroutines and their states.

Blocking and mutex profiles can provide evidence of synchronization costs.

Execution traces can reveal scheduling and activity patterns.

The `pprof` ecosystem is particularly important for production investigation.

### The goroutine leak signature

In our incident, the goroutine count increases after every cancelled scan.

Profiles show many goroutines blocked on channel sends.

The number of completed scans doesn't explain the growing population.

This is much stronger evidence than simply observing that RSS increased.

The stack traces point toward the missing cancellation path.

### Rust profiling

Rust can use native profilers, platform sampling tools, allocation instrumentation, and tracing libraries.

Optimized binaries may require suitable debug information to produce useful symbolized profiles.

An application can instrument request spans, task lifetimes, queue lengths, and memory allocation behavior.

### The async visibility problem

Async runtimes can make task-level behavior harder to reconstruct from ordinary operating-system thread stacks.

A single thread may execute many different async tasks over time.

Application-level tracing and executor instrumentation become important.

### What both languages need

Neither compiler can tell an on-call engineer which customer scan caused a backlog unless the application records relevant correlation information.

Both services need structured logging, metrics, trace context, and a clear model of task ownership.

Observability isn't an optional feature reserved for managed runtimes.

## 18. The Three Resource Budgets

Let's examine the scanner using three separate budgets.

### CPU budget

How much computation can the container perform?

The answer depends on actual CPU allocation, quota, runtime parallelism, and hardware behavior.

Go's `GOMAXPROCS` and Rust's worker-thread configuration can influence how the application uses available CPU capacity.

They don't override kernel-enforced limits.

### Memory budget

How much live state can the process retain?

Go's garbage collector manages reachable heap allocations.

Rust uses ownership-based cleanup and other explicit memory-management mechanisms.

But both can keep too much data alive.

The container limit is enforced outside the language runtime.

### I/O and concurrency budget

How many network operations should the scanner initiate?

How many connections can the remote services accept?

How many active jobs can the platform afford to track?

How much queueing is acceptable?

Neither lightweight goroutines nor efficient Rust futures eliminate these constraints.

The architecture must enforce concurrency limits and work admission policies.

### The real capacity equation

Useful throughput is determined by the slowest relevant resource constraint.

A scanner can have spare CPU but be limited by network latency.

It can have sufficient network capacity but be limited by parsing throughput.

It can process findings quickly but accumulate an unbounded queue because downstream storage cannot keep up.

Changing the language may alter one cost while leaving the bottleneck untouched.

This is why capacity planning begins with measurements rather than language selection.

## 19. When Would I Actually Choose Go?

Imagine the team needs a new network-oriented worker service.

It performs many concurrent HTTP and DNS operations.

The processing logic is moderately CPU-intensive but not dominated by extremely specialized numerical kernels.

The service must be easy to build, deploy, and investigate.

Go would be a credible choice.

Its standard library includes strong networking and concurrency facilities.

Goroutines provide a convenient model for representing concurrent activities.

The runtime scheduler handles mapping those activities onto execution threads.

Garbage collection simplifies ordinary object-lifetime management.

And the tooling provides useful profiling, testing, and race-detection capabilities.

### The trade-offs

Go doesn't eliminate data races.

Shared mutable state still requires synchronization.

Goroutine lifetimes still require cancellation and cleanup.

Garbage collection consumes resources.

And a simplified language model can sometimes require more explicit organization than developers expect from a highly expressive type system.

For a network scanner, those costs may be acceptable.

But the team must design bounded concurrency and robust task lifecycle management.

The language won't do that automatically.

## 20. When Would I Actually Choose Rust?

Now imagine a service that parses large volumes of untrusted binary data.

It needs strict memory-safety guarantees.

It has tight resource budgets.

It manipulates native memory and complex data structures.

And predictable resource lifetimes are important.

Rust could be an excellent choice.

The ownership and borrowing system helps prevent important classes of memory corruption and invalid access.

Its abstractions can compile into efficient machine code.

Its type system provides strong tools for modeling states and error handling.

The program can often avoid a general tracing garbage collector.

### The trade-offs

Rust's ownership and lifetime model can impose a steeper learning curve.

Some APIs require more deliberate data ownership and synchronization design.

Asynchronous programming involves futures, executors, and cancellation semantics that deserve careful understanding.

Compile times and dependency complexity can matter.

And not every application needs the same level of memory-control precision.

If the service spends almost all its time waiting on a remote database, the engineering cost of rewriting it in Rust may exceed the performance benefit.

Rust is most compelling when its guarantees or execution characteristics address a meaningful requirement.

## 21. The Architecture Decision: Don't Rewrite the Whole Platform

Our cybersecurity company has now completed its investigation.

The existing Node.js API coordinates customers, scan requests, and report delivery.

The Python ecosystem provides specialized analysis libraries and scanning modules.

The proposed native worker would handle a well-defined subset of scanning and processing work.

Should the team rewrite everything?

No.

The new service should have a narrow responsibility justified by observed requirements.

Perhaps the team chooses Go for large-scale network orchestration.

Perhaps it chooses Rust for a security-sensitive parser.

Perhaps it decides the current Python implementation already meets its performance targets after adding proper concurrency limits.

All three outcomes could be legitimate.

### The new service boundary has a cost

A separate runtime introduces deployment and operational responsibilities.

The system needs versioned contracts.

It needs error handling across process boundaries.

It needs idempotency when jobs are retried.

It needs tracing across services.

It needs an approach to upgrades and rollback.

A language rewrite may improve local performance while increasing distributed-system complexity.

This is why a measured performance improvement should be evaluated against the total engineering cost.

### The decision framework

Ask what the service spends time doing.

Measure CPU, memory, and I/O demands.

Identify the correctness guarantees that matter.

Evaluate library and tooling support.

Estimate migration and maintenance costs.

Then build a representative prototype.

The result should be judged by useful throughput, latency, resource cost, reliability, and developer productivity.

Not by language identity.

## 22. The Oral Examination

Answer each challenge aloud before reading the solutions.

### Challenge 1 — The Runtime-Free Myth

A developer claims that Go and Rust have no runtime because both compile to native executables.

What is inaccurate about this claim?

### Challenge 2 — Ten Thousand Goroutines

A scanner launches ten thousand goroutines on a container limited to two CPUs.

How many goroutines can execute ordinary Go code simultaneously?

How does this relate to `GOMAXPROCS`, and why might the remaining goroutines still consume resources?

### Challenge 3 — The Cancelled Scan

Workers send results on an unbuffered channel.

The coordinator exits when the scan is cancelled.

Several workers remain blocked forever.

Why doesn't garbage collection remove them, and how should cancellation be designed?

### Challenge 4 — The Rust Memory Failure

A safe Rust program continuously stores every scanned response in a growing Vec.

Its container is eventually killed for exceeding a memory limit.

Did Rust's memory-safety guarantees fail?

### Challenge 5 — The Lazy Future

A Rust function marked async is called, and its returned future is immediately discarded without polling.

What work should you generally expect the async function body to have performed?

How does this differ from launching a Go goroutine?

### Challenge 6 — The Shared Counter

Several Rust threads must update a shared counter.

Why might `Arc<Mutex<T>>` be appropriate?

What distinct responsibility does each wrapper provide?

### Challenge 7 — The Soft Memory Limit

A Go service sets `GOMEMLIMIT` equal to its container memory limit.

An engineer claims the container can no longer run out of memory.

Why is that conclusion incorrect?

### Challenge 8 — The Language Benchmark

An optimized Rust implementation processes quotations faster than a Go implementation.

But the Go version uses different data structures and performs additional allocations.

What can you conclude from the benchmark, and what additional experiment would make it more informative?

### Challenge 9 — The Three-Second Scan

A customer scan takes three seconds.

Only 50 milliseconds are spent in local CPU processing.

The rest is network waiting.

Would rewriting the local calculation in Rust necessarily improve user-visible latency substantially?

### Challenge 10 — The Architecture Choice

You're building two new components.

One orchestrates thousands of HTTP requests.

The other parses complex untrusted binary files under strict memory and safety requirements.

Which languages might you choose, and what evidence would determine the decision?

## 23. Solutions and Discussion

### Solution 1 — Native compilation doesn't remove runtime machinery

Go includes a substantial runtime for goroutine scheduling, memory management, network polling, and other execution services.

Rust doesn't require a general tracing garbage collector, but Rust programs still use allocators, operating-system facilities, libraries, and potentially async executors.

Both produce native machine code. Their runtime responsibilities differ.

### Solution 2 — Goroutine count isn't parallel execution capacity

`GOMAXPROCS` limits how many logical processors execute ordinary Go code simultaneously, subject to runtime-specific behavior.

A container with a two-CPU limit may use a corresponding default on modern Go versions when not explicitly overridden.

The remaining goroutines may be waiting or runnable.

They still consume scheduling state, memory, and references.

### Solution 3 — Goroutines need an exit path

The blocked senders remain active goroutines with live execution state.

The collector cannot arbitrarily terminate them.

Use cancellation-aware operations, appropriate context propagation, and worker lifecycle coordination.

Every potentially blocking send should have a defined behavior when the receiver exits.

### Solution 4 — Memory safety isn't bounded memory

The Rust program is managing its memory safely while deliberately retaining an unbounded amount of live data.

The kernel enforces the container's memory limit.

The fix is to establish a bounded retention or processing policy.

Rust's compiler cannot infer the application's desired maximum queue size.

### Solution 5 — Rust futures are lazy

Calling an ordinary async Rust function creates a future whose body doesn't generally execute merely through construction.

The future must be polled, directly or through an executor.

A Go goroutine begins an independent concurrent activity when launched.

The two mechanisms have different scheduling and lifecycle contracts.

### Solution 6 — Ownership and synchronization are separate

`Arc` provides shared ownership through atomic reference counting.

`Mutex` provides controlled mutable access to the contained value.

Together they can support shared mutable state across threads where the contained type meets the required trait bounds.

They don't prevent deadlocks or all higher-level logic errors.

### Solution 7 — GOMEMLIMIT is soft and doesn't cover everything

The Go runtime makes an effort to manage its own memory within the configured soft limit.

It doesn't guarantee that every allocation or every category of process memory remains below that value.

Container memory enforcement operates at another layer.

The application still requires headroom and bounded retained state.

### Solution 8 — The complete implementations were compared

The benchmark may establish that one implementation performs better for that workload under those conditions.

It doesn't isolate language execution cost.

Differences in allocation, data layout, algorithms, build settings, and parallelism may explain the result.

A useful follow-up would control those dimensions where practical.

### Solution 9 — A faster CPU path may barely affect total latency

If local computation accounts for only a small fraction of the critical path, even eliminating it entirely would save only that fraction under the simplified sequential model.

Network waiting dominates.

The team should investigate concurrency, remote latency, caching, or workflow design before assuming a language rewrite will help.

### Solution 10 — Match guarantees to workload

Go is a credible option for network orchestration because of goroutines, tooling, and straightforward concurrency facilities.

Rust is a credible option for security-sensitive parsing because of strong safe-code memory guarantees and control over representation.

But actual library availability, measured resource behavior, team competence, deployment requirements, and maintenance cost should determine the choice.

## 24. The Mental Model Worth Keeping

Native compilation gives the program machine code.

It doesn't eliminate resource management.

Go uses a runtime scheduler and tracing garbage collection to make concurrent application development convenient.

Rust uses ownership-based resource management and strong static safety rules, while relying on selected libraries and executors for many higher-level runtime services.

Both can execute efficiently.

Both can run many concurrent operations.

And both can leak resources, deadlock, overwhelm dependencies, or exhaust a container.

Whenever evaluating a native runtime, ask:

**Who schedules the work? Who owns the data? Who releases resources? How is cancellation handled? Which resource actually limits throughput?**

Those questions matter more than the language's reputation for speed.

## 25. Next Lecture — CS220-L08: Runtime Performance and Language Choice Workshop

We've now studied source-code semantics, type systems, memory management, compilation, machine execution, managed runtimes, and native runtimes.

The final challenge is to put them together.

Suppose a company asks:

"Our Python worker is slow. Should we rewrite it in Go?"

Or:

"Our Node.js service uses too much memory. Would Rust solve it?"

Or:

"Our Java service handles ten thousand requests, but latency keeps increasing. Should we change languages?"

These aren't questions with universal answers.

In the final CS220 lecture, we'll conduct an architecture review using measurements, workload classification, benchmark design, migration cost, and explicit correctness requirements.

We'll compare practical implementations rather than language stereotypes.

And we'll decide when a runtime change is justified—and when the best engineering decision is to keep the current language and fix the actual bottleneck.

*The spoken lecture ends here. The remaining material is for hands-on experiments and screen-based revision.*

---

## Optional Practical Lab — Go and Rust Under a Microscope

**Objective:** Observe Go's goroutine scheduling and cancellation, inspect runtime resource behavior, and compare Rust's ownership, threads, and explicit resource management.

The exercises are intentionally small and bounded. They require local Go or Rust toolchains only for the sections you choose to execute.

### Lab A — Go: Inspect the Runtime

Create `runtime-info.go`:

```go
package main

import (
    "fmt"
    "runtime"
)

func main() {
    fmt.Println("Go:", runtime.Version())
    fmt.Println("Logical CPUs:", runtime.NumCPU())
    fmt.Println("GOMAXPROCS:", runtime.GOMAXPROCS(0))
    fmt.Println("Goroutines:", runtime.NumGoroutine())
}
```

Run:

```bash
go run runtime-info.go
```

Compare the reported logical CPUs and `GOMAXPROCS`.

If you run inside a container, inspect whether the process has a CPU limit.

Remember that container-aware defaults depend on Go version and configuration.

**Question:** Why doesn't the goroutine count equal the number of available CPU cores?

### Lab B — Go: Bounded Concurrent Supplier Requests

Create `supplier-workers.go`:

```go
package main

import (
    "fmt"
    "sync"
    "time"
)

func main() {
    const total = 12
    const workers = 3

    jobs := make(chan int)
    results := make(chan string, total)

    var wg sync.WaitGroup

    for worker := 0; worker < workers; worker++ {
        wg.Add(1)

        go func() {
            defer wg.Done()

            for id := range jobs {
                time.Sleep(120 * time.Millisecond)
                results <- fmt.Sprintf("supplier-%d", id)
            }
        }()
    }

    started := time.Now()

    for id := 0; id < total; id++ {
        jobs <- id
    }

    close(jobs)
    wg.Wait()
    close(results)

    for result := range results {
        fmt.Println(result)
    }

    fmt.Println("Elapsed:", time.Since(started))
}
```

Run:

```bash
go run supplier-workers.go
```

The example simulates I/O waiting with a fixed number of workers.

Try changing the worker count from three to one, then to six.

**Question:** Why does additional concurrency reduce elapsed time in this example even though no supplier operation becomes individually faster?

### Lab C — Go: A Cancellation-Aware Send

Consider a worker that may finish after its coordinator has stopped accepting results.

A cancellation-aware send can use `select`:

```go
select {
case results <- finding:
    // Result delivered.
case <-ctx.Done():
    // Coordinator no longer wants this work.
    return
}
```

This assumes `ctx`, `results`, and `finding` are appropriately defined.

**Exercise:** Modify the supplier-worker example to create a cancellable context.

Cancel it after a defined interval.

Ensure workers can exit without becoming permanently blocked when the coordinator stops receiving results.

Then use a WaitGroup to verify that all workers eventually finish.

**Question:** Why is cancellation handling required even if every goroutine's code is memory-safe?

### Lab D — Go: Race Detection

Create `race.go`:

```go
package main

import (
    "fmt"
    "sync"
)

func main() {
    var counter int
    var wg sync.WaitGroup

    for i := 0; i < 100; i++ {
        wg.Add(1)

        go func() {
            defer wg.Done()
            counter++
        }()
    }

    wg.Wait()
    fmt.Println(counter)
}
```

Run:

```bash
go run -race race.go
```

Observe whether the race detector reports conflicting accesses.

Now repair the program using `sync.Mutex` or an appropriate atomic operation.

**Question:** Why doesn't Go's garbage collector make unsynchronized shared mutation safe?

### Lab E — Go: Collect a CPU Profile

Create a small CPU-intensive benchmark using the `testing` package.

For example, benchmark a deterministic calculation over a bounded collection.

Run:

```bash
go test -bench=. -benchmem -cpuprofile=cpu.prof
```

Then inspect the profile:

```bash
go tool pprof -top cpu.prof
```

Exact commands depend on the local Go project and test file.

**Question:** How does a CPU profile differ from a goroutine or heap profile?

### Lab F — Rust: Ownership and Deterministic Drop

Create a new Rust project:

```bash
cargo new rust-resource-lab
cd rust-resource-lab
```

Replace `src/main.rs`:

```rust
struct Report {
    id: String,
}

impl Drop for Report {
    fn drop(&mut self) {
        println!("Releasing report {}", self.id);
    }
}

fn main() {
    {
        let report = Report {
            id: String::from("R-42"),
        };

        println!("Processing {}", report.id);
    }

    println!("Report scope ended");
}
```

Run:

```bash
cargo run
```

Observe when the destructor runs.

**Question:** How does this differ conceptually from relying on the next garbage-collection cycle to reclaim a managed object?

### Lab G — Rust: Share Mutable State Safely

Create a program using threads and shared ownership:

```rust
use std::sync::{Arc, Mutex};
use std::thread;

fn main() {
    let total = Arc::new(Mutex::new(0_u64));

    let mut handles = Vec::new();

    for _ in 0..4 {
        let total = Arc::clone(&total);

        let handle = thread::spawn(move || {
            for _ in 0..1_000 {
                let mut value = total.lock().unwrap();
                *value += 1;
            }
        });

        handles.push(handle);
    }

    for handle in handles {
        handle.join().unwrap();
    }

    println!("Total: {}", *total.lock().unwrap());
}
```

Run the program.

Explain the difference between `Arc` and `Mutex`.

Then answer:

Does this protect a counter stored in a remote database and accessed by four independent application processes?

No—explain why.

### Lab H — Rust: Compare Debug and Release Builds

Create a CPU-intensive deterministic calculation in your Rust project.

Measure the execution time under:

```bash
cargo run
```

Then:

```bash
cargo run --release
```

Record the output checksum and elapsed time.

**Question:** Why is comparing a Rust debug build against a warmed-up Java or Node.js process a poor runtime benchmark?

### Lab I — Go and Rust Architecture Review

Your cybersecurity platform has these requirements:

- Thirty thousand potential network targets per customer scan.
- A maximum of 200 concurrent external connections.
- Large binary responses that must be parsed safely.
- Strict memory limits for worker containers.
- Customer-initiated cancellation.
- Durable scan progress stored outside the worker.
- Reliable retry behavior without duplicate findings.

Propose either a Go implementation, a Rust implementation, or a combination.

Explain your choice of task scheduling, concurrency limits, resource ownership, cancellation, durable state, and profiling tools.

The strongest answer will not rely on claims that Go is always more productive or Rust is always faster.

It will connect mechanisms to requirements.

---

## Further Reading

1. [Go — A Guide to the Garbage Collector](https://go.dev/doc/gc-guide) — GC costs, heap growth, and memory limits.
2. [Go — Container-Aware GOMAXPROCS](https://go.dev/blog/container-aware-gomaxprocs) — CPU-limit-aware runtime defaults.
3. [Go — Runtime Documentation](https://pkg.go.dev/runtime) — Scheduler, GOMAXPROCS, GOGC, and GOMEMLIMIT.
4. [Go — Pipelines and Cancellation](https://go.dev/blog/pipelines) — Goroutine lifetimes and cancellation.
5. [Go — Diagnostics](https://go.dev/doc/diagnostics) — Profiling, tracing, and runtime investigations.
6. [Go — Race Detector](https://go.dev/doc/articles/race_detector) — Detecting shared-memory data races.
7. [The Rust Programming Language — Ownership](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html) — Owned values and resource lifetimes.
8. [The Rust Programming Language — Shared-State Concurrency](https://doc.rust-lang.org/book/ch16-03-shared-state.html) — Mutex, Arc, and synchronization.
9. [The Rust Programming Language — Send and Sync](https://doc.rust-lang.org/book/ch16-04-extensible-concurrency-sync-and-send.html) — Thread-safe ownership and references.
10. [The Rust Programming Language — Futures and Async](https://doc.rust-lang.org/book/ch17-01-futures-and-syntax.html) — Lazy futures and asynchronous execution.
11. [Tokio — Cancellation Safety](https://docs.rs/tokio/latest/tokio/macro.select.html) — Dropped futures and partial progress.
12. [Rust Performance Book](https://nnethercote.github.io/perf-book/) — Practical profiling and optimization.

---

## Dense Cheatsheet — Interview Glance Card

*This final reference is deliberately fenced for screen-based revision.*

```text
CS220-L07 — NATIVE RUNTIMES: GO, RUST, EXECUTION TRADE-OFFS

CORE PRINCIPLE

  Native compilation != absence of runtime.

  Go:
    Native code + substantial runtime scheduler + GC

  Rust:
    Native code + ownership-based resource management
    No required general tracing GC

BOTH STILL NEED

  OS scheduling
  Memory allocation
  Networking
  Synchronization
  Resource limits
  Operational diagnostics

GO GOROUTINES

  Lightweight concurrent Go execution units

  Go runtime maps goroutines onto OS threads.
  Waiting goroutine != dedicated OS thread.

  Goroutine count != parallel CPU count.

G–M–P MODEL

  G = Goroutine
  M = OS thread
  P = Logical Go scheduling resource

  Useful conceptual model, implementation evolves.

GOMAXPROCS

  Maximum simultaneous logical execution
  of ordinary Go code

  Go 1.25+:
    Container CPU-limit-aware default on Linux
    when not overridden and conditions apply

  CPU limit != CPU request

  Host cores != container's usable CPU budget

GOROUTINE LEAK

  Worker blocked on channel send
  Coordinator has stopped receiving
  Worker never exits

  GC cannot reclaim active goroutine state.

  Fix:
    Context cancellation
    Cancellation-aware select
    Explicit worker lifecycle
    Bounded work queues

GO CHANNELS

  Unbuffered:
    Send/receive coordinate

  Buffered:
    Bounded queue capacity

  Full channel:
    Send may block

  Buffering != unlimited throughput
  Buffering != cancellation

GO GARBAGE COLLECTION

  Tracing GC
  Reclaims unreachable managed objects
  Doesn't reclaim reachable but obsolete data

GOGC

  Influences heap growth/collection work trade-off

GOMEMLIMIT

  Soft runtime memory limit
  Not hard container limit
  Not total process memory
  Does not fix unbounded retention

GO DEPLOYMENT

  Native executable
  Target OS/architecture matters
  cgo may introduce native dependencies
  Not every binary is fully static

RUST OWNERSHIP

  Values have ownership
  Moves transfer ownership
  Borrowing controls access
  Drop manages ordinary resource cleanup

  Rust still uses heap allocations.

RUST RESOURCE LIFETIME

  Scope exit -> Drop where applicable
  Reference-counted cycles can retain memory
  Explicit long-lived ownership retains data
  Safe code can exhaust memory

RUST THREAD SAFETY

  Send:
    Ownership may safely move across threads

  Sync:
    Shared references may safely cross threads

  Arc<T>:
    Atomic shared ownership

  Mutex<T>:
    Controlled mutable access

  Arc doesn't make arbitrary mutation safe.
  Safe Rust can still deadlock.

RUST ASYNC

  async fn returns lazy Future
  Future must be polled
  Executor drives futures
  Tokio is a common runtime, not universal language law

  Go goroutine:
    Concurrent activity begins when launched

  Rust Future:
    Lazy until driven

RUST CANCELLATION

  Dropping future stops that future's polling
  Spawned background tasks may continue
  Cancellation safety matters
  Partial progress may be lost
  External side effects aren't automatically rolled back

CPU WORK

  Go:
    Goroutines on logical processors

  Rust:
    Threads / parallel libraries

  Both:
    Need CPU cores and appropriately sized tasks

  More tasks != more throughput

PERFORMANCE

  Dominated by:
    Algorithm
    Data representation
    Cache locality
    Allocation
    Synchronization
    Memory bandwidth
    CPU availability
    I/O waiting

  Native != automatically fastest

NUMERIC SEMANTICS

  Go:
    Fixed-width integer types
    Defined overflow rules

  Rust:
    Fixed-width integer types
    Checked/wrapping/saturating APIs
    Build/configuration-dependent overflow checks

  Benchmark must preserve business correctness.

OPERATIONS

  Go:
    pprof
    Runtime traces
    Goroutine profiles
    Heap profiles
    Race detector

  Rust:
    Native CPU profiling
    Tracing instrumentation
    Allocation profiling
    Appropriate debug symbols

  Observability must identify task ownership.

RESOURCE BUDGETS

  CPU budget
  Memory budget
  I/O/concurrency budget

  Each can become the limiting resource.

WHEN GO IS ATTRACTIVE

  Network services
  Large-scale I/O orchestration
  Simple concurrency model
  Productive deployment/tooling
  Managed memory acceptable

WHEN RUST IS ATTRACTIVE

  Memory-safety-sensitive systems
  Binary parsing
  Precise resource control
  Native interoperability
  Tight resource/performance requirements

LANGUAGE REWRITE TEST

  What is the measured bottleneck?
  What specific guarantee would improve?
  How much useful work gets faster?
  What does migration cost?
  Could a narrow component solve the problem?

SENIOR QUESTIONS

  Who schedules execution?
  Who owns memory?
  How are resources released?
  What happens on cancellation?
  Where is backpressure enforced?
  Which resource limits throughput?
  What evidence justifies changing languages?

SENIOR LINE

  "I compare Go and Rust by execution model, ownership,
   concurrency lifecycle, memory costs, and measured
   workload behavior—not by native-code slogans.
   Go gives a convenient runtime scheduler and GC;
   Rust gives stronger static ownership control.
   Neither removes the need for bounded resources,
   cancellation, or correct distributed semantics."
```
