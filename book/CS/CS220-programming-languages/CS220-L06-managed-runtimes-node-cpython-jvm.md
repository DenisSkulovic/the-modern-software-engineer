---
id: CS220-L06
course: CS220
title: "Managed Runtimes: Node.js, CPython, and the JVM"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: CS220-L05
next: CS220-L07
---


# CS220 — Languages, Types, Memory, and Runtimes

## Lecture 06: Managed Runtimes — Node.js, CPython, and the JVM

*Three teams implement the same hotel-pricing service. Their algorithms are equivalent, their outputs agree, and all three applications work in development. Under load, one stops responding to new requests, another barely uses its available CPU cores, and the third handles thousands of connections but still overwhelms its database. The language syntax won't explain these failures. The runtime architecture will.*

---

# Part I — Intuition

## The picture to carry in your head

Imagine a hotel-booking platform that aggregates offers from fifty accommodation suppliers.

A customer searches for a hotel in the French Alps.

Your backend needs to contact several suppliers, retrieve prices and room availability, calculate the best offers, and return the results.

There are two very different kinds of work in this operation.

First, the backend spends time waiting for suppliers.

A supplier may respond in 200 milliseconds, another in 800, and another in two seconds.

During that waiting time, the backend doesn't need to perform continuous arithmetic. The supplier is doing something elsewhere, and the network is carrying the response.

Second, once all the data arrives, the backend performs a large pricing calculation.

It applies commission rules, discounts, occupancy conditions, currency conversions, and ranking criteria across hundreds of thousands of offers.

That work actually needs processor time.

Now suppose three engineering teams implement this workflow.

One uses Node.js.

Another uses CPython.

The third uses Java on the JVM.

All three can build the application.

But they organize execution differently, and those differences become visible under load.

## 1. Waiting and working are different resources

Imagine a restaurant kitchen.

A chef receives fifty orders.

Some require food to cook in an oven for twenty minutes.

Others require three minutes of active chopping and preparation.

Would it make sense for the chef to stand motionless in front of one oven until the food is ready?

No.

The chef can start several independent cooking operations and work on other tasks while waiting.

That's the principle behind asynchronous I/O.

The program initiates an operation, then allows other work to progress until the result becomes available.

But now imagine the chef must chop ten thousand vegetables.

Starting ten thousand asynchronous promises doesn't make the chopping itself happen faster.

Someone must perform the physical work.

To accelerate that portion, the restaurant needs more workers, better tools, or a more efficient process.

**Concurrency helps organize overlapping work. Parallelism allows multiple pieces of computation to execute simultaneously.**

The distinction applies to all three runtimes.

## 2. Node.js: one main conversation, many things in flight

Node.js is often described as single-threaded.

That description is both useful and misleading.

By default, an ordinary Node.js application executes its main JavaScript callbacks on one event-loop thread.

But Node.js can have many network operations in flight.

It uses operating-system I/O facilities and other supporting runtime machinery so that one JavaScript thread doesn't need to block while every remote service responds.

This makes Node.js particularly comfortable for applications that coordinate many relatively short computations around network requests.

But what happens when the callback for one request performs five seconds of uninterrupted CPU-intensive JavaScript?

The main event loop is occupied.

Other callbacks have to wait.

Incoming requests may be accepted and buffered by lower layers, but their application handlers can't run normally until the blocking computation yields or finishes.

An asynchronous function doesn't magically solve this.

A function can be declared `async` and still perform blocking CPU work.

The word async changes how a function reports eventual completion. It doesn't create an additional processor.

## 3. CPython: several ways to organize work

Python supports ordinary threads, asynchronous coroutines, and separate processes.

But the execution model depends on the Python implementation and build.

Traditional CPython builds use the Global Interpreter Lock, commonly called the GIL.

The GIL ordinarily prevents two threads in the same interpreter from executing Python bytecode simultaneously.

That doesn't mean Python threads are useless.

If one thread is waiting for a network response and releases the GIL during the blocking operation, another can perform work.

This makes threads useful for many I/O-bound workloads.

For CPU-intensive pure-Python work, however, ordinary threads in a GIL-enabled build don't automatically use several CPU cores.

Separate processes can.

And free-threaded CPython builds now provide another option: they can run Python threads concurrently on multiple cores when the GIL is disabled.

That's a major development, but it doesn't remove synchronization requirements or guarantee faster execution for every workload.

## 4. The JVM: threads, bytecode, and runtime optimization

Java usually reaches execution through a different route.

Java source is compiled into bytecode.

A JVM loads classes, checks and prepares code, and executes bytecode through its runtime machinery, including interpretation and JIT compilation.

The JVM also manages memory and provides a mature threading environment.

Traditional Java platform threads correspond closely to operating-system threads.

That makes simultaneous CPU execution natural when work is distributed among threads and enough cores are available.

But maintaining very large numbers of blocked platform threads has resource costs.

Modern Java also provides virtual threads.

A virtual thread lets the application use a familiar blocking programming style while the runtime manages scheduling onto a smaller set of underlying platform threads.

When a supported blocking operation suspends a virtual thread, the underlying carrier thread can be used for other work.

That makes large numbers of waiting tasks more economical.

But a virtual thread performing heavy CPU computation still needs CPU execution time.

Virtual threads increase the scalability of certain concurrency patterns; they don't make arithmetic free.

## 5. All three runtimes manage objects, but differently

In Node.js, V8 manages ordinary JavaScript objects through tracing garbage collection.

In CPython, reference counting is central to ordinary object lifetime management, supplemented by mechanisms that collect reference cycles.

The JVM uses garbage collectors that trace and reclaim managed objects through their chosen algorithms.

These strategies have different consequences for allocation, object lifetime, pauses, throughput, and memory overhead.

But all three have an important limitation.

A runtime cannot reclaim objects that the application deliberately continues retaining under its memory-management model.

An unbounded cache can leak memory in Node.js.

It can leak memory in Python.

It can leak memory in Java.

The implementation differs. The ownership mistake is the same.

## 6. The right question is about the workload

Now return to the supplier aggregator.

If most request time is spent waiting for network responses, the ability to handle many concurrent operations with modest resource overhead matters.

If the application performs heavy CPU calculations, actual multi-core execution and computational efficiency matter.

If the workload creates enormous numbers of objects, memory representation and collection behavior matter.

If the application is frequently started and stopped, startup and warmup costs matter.

And if developers need to diagnose production failures, tooling and operational familiarity matter.

The question isn't simply which language is fastest.

It's what each runtime makes inexpensive, what it makes expensive, and which costs dominate the application.

### The two workload paths

```text id="cs22006-picture"
WORKLOAD A — SUPPLIER AGGREGATION

Send request 1 ---- wait ---- response
Send request 2 -- wait -- response
Send request 3 ------ wait ------ response

Opportunity: overlap waiting


WORKLOAD B — PRICING CALCULATION

Calculate batch A
Calculate batch B
Calculate batch C

Opportunity: efficient CPU execution
             or genuine parallel work
```

Both workloads can be implemented in all three runtimes.

But efficient implementations may use different mechanisms.

### Three questions before the Deep Dive

1. Why can Node.js manage thousands of simultaneous I/O operations while one CPU-intensive callback blocks the main JavaScript thread?
2. Why can traditional CPython threads help with I/O while providing limited parallelism for pure-Python CPU work?
3. Why do Java virtual threads improve some server workloads without making individual calculations run faster?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. One Booking Platform, Three Different Failures

The company has decided to benchmark three implementations of its supplier-and-pricing service.

The first uses Node.js with TypeScript.

The second uses CPython with an asynchronous web framework.

The third uses Java on the JVM.

Each exposes the same logical operation.

The client submits destination, dates, and occupancy.

The application contacts suppliers.

It normalizes their responses.

It calculates and ranks offers.

It returns the best choices.

All three pass functional tests.

Then the load tests begin.

### The Node.js incident

The service handles supplier requests efficiently until a large pricing batch begins.

During the batch, unrelated health and API requests become sluggish.

The host has available processor cores.

But the main JavaScript thread is spending long periods computing prices.

### The Python incident

The engineering team attempts to accelerate the pricing batch by adding ordinary threads.

Their traditional CPython deployment shows little speedup for the pure-Python computation.

Some threads may spend time waiting for the GIL rather than executing Python bytecode simultaneously.

### The Java incident

The JVM handles many concurrent requests.

After adopting virtual threads, the team can support many waiting operations with fewer platform-thread resources.

But the number of simultaneous database queries rises dramatically.

The database connection pool saturates.

Request latency increases.

All three incidents have the same underlying lesson.

The runtime provides ways to schedule work.

It does not provide infinite resources or automatically enforce sensible application concurrency.

Let's understand the mechanisms precisely.

## 2. A Runtime Is More Than an Interpreter

When people say "Node.js," "CPython," or "JVM," they often mean an entire execution environment.

That environment typically includes several responsibilities.

It loads and executes program code.

It provides memory-management machinery.

It interfaces with operating-system facilities.

It supports libraries and native functionality.

It implements concurrency and scheduling mechanisms.

And it exposes diagnostic information needed to investigate failures.

This is more than translating source code into instructions.

### Execution engine versus surrounding runtime

V8 is a JavaScript engine.

Node.js embeds V8 and provides server-oriented runtime capabilities, including networking, filesystem access, timers, and other host APIs.

CPython is both an implementation of Python's language semantics and an execution environment providing standard libraries, native extension interfaces, memory management, and interpreter machinery.

The JVM defines a virtual-machine execution environment for bytecode. HotSpot is a widely used JVM implementation, and Java applications also depend on the Java standard library and other runtime facilities.

These distinctions matter because performance or concurrency characteristics often belong to the combination of engine, runtime, library, and operating system.

A language specification doesn't dictate every implementation choice.

## 3. Node.js: V8 Plus an Event-Driven Host

We studied V8's compilation and optimization machinery in L05.

Now we need to understand what Node.js adds.

A typical Node.js process has a main JavaScript execution thread associated with its event loop.

Node.js uses libuv and operating-system facilities to coordinate asynchronous operations.

The application can initiate a network request, continue handling other events, and later process the response.

### What happens during an outbound HTTP request?

Imagine one customer request requiring thirty supplier calls.

The application starts an HTTP request toward Supplier A.

The networking implementation manages the socket and waits for the relevant I/O events.

The JavaScript thread doesn't need to sit inside a blocking read call until A responds.

The application can initiate Supplier B's request.

And Supplier C's.

Eventually, the network stack indicates that data is available.

The runtime schedules appropriate callbacks and Promise continuations.

The JavaScript thread processes those completions as it becomes available.

### The useful property

Many in-flight network operations don't necessarily require one dedicated JavaScript thread apiece.

This makes event-driven concurrency economical for workloads where most operations spend substantial time waiting.

### The limit

When a callback executes, its ordinary JavaScript code occupies the main JavaScript thread until it returns, yields through an appropriate mechanism, or otherwise completes.

If that callback performs extensive synchronous work, other JavaScript callbacks wait.

An event loop is a scheduling mechanism, not a machine that executes arbitrary JavaScript in parallel.

## 4. The Event Loop: Where Ready Work Gets a Turn

Let's follow the supplier results.

A supplier's network response becomes ready.

The operating system and libuv participate in making the event available to Node.js.

The relevant callback eventually runs.

That callback may settle a Promise.

The Promise's continuation executes according to JavaScript and Node.js scheduling rules.

The next piece of business logic processes the supplier's response.

### Event-loop phases

Node.js has event-loop phases for categories of work such as timers, I/O callbacks, polling, immediates, and close callbacks.

Promise microtasks and Node-specific scheduling facilities such as `process.nextTick()` interact with those phases.

The exact ordering rules are important when debugging subtle timing behavior.

But we don't need to reproduce the entire event-loop specification here; CS320 will give scheduling and event-loop internals their own treatment.

For this lecture, retain three facts.

A callback executes on a particular JavaScript execution thread.

A completed I/O operation doesn't force its callback to execute instantly.

And long-running JavaScript work can delay unrelated callbacks even when the I/O itself completed earlier.

### The production symptom

Suppose Supplier A responds after 100 milliseconds.

But the Node.js main thread has begun a two-second synchronous pricing calculation.

The response may be available in lower-level buffers.

The application doesn't process its completion callback until JavaScript execution becomes available again.

The supplier wasn't necessarily slow.

The callback was delayed.

That's why server-side latency analysis must separate external dependency time from local event-loop scheduling delay.

## 5. Node.js Has More Than One Thread

The statement "Node.js is single-threaded" often produces incorrect architectural conclusions.

Node.js can use several kinds of threads.

V8 may use background threads for its own implementation work.

Libuv maintains a worker pool for certain operations that aren't conveniently handled through nonblocking operating-system I/O facilities.

Applications can create worker threads using the `worker_threads` module.

Native addons can use threading under their own implementation rules.

And multiple Node.js processes can run side by side.

### The libuv worker pool

Some asynchronous Node.js APIs use libuv's worker pool.

Common examples include portions of filesystem operations, certain cryptographic functions, compression, and selected DNS-related APIs.

The exact path depends on the API and platform.

Not every asynchronous operation uses a worker-pool thread.

Normal socket readiness is commonly managed through operating-system event notification rather than assigning a worker thread to every socket.

### Worker-pool saturation

Imagine many requests performing expensive password derivation or compression operations.

If those operations use the libuv worker pool, they may compete for its finite capacity.

The main JavaScript thread can remain relatively responsive while work accumulates in the pool.

Adding more asynchronous calls can increase the queue without increasing useful throughput.

This is different from main-thread CPU blocking.

The symptoms and remedies differ.

### Worker threads

Node.js also supports application-created worker threads.

These provide additional JavaScript execution contexts and can execute CPU-intensive JavaScript in parallel on available cores.

Workers have their own V8 execution environments and ordinary JavaScript heaps.

Communication can occur through messages, transferred data, and supported shared-memory mechanisms.

### The right use

A large independent pricing batch may be suitable for a worker pool.

A normal HTTP request waiting for a remote supplier generally doesn't require a separate worker thread merely to remain asynchronous.

Creating one worker per tiny task can be expensive because startup, messaging, copying, and coordination all have costs.

A persistent, bounded worker pool is often more appropriate for repeated CPU jobs.

### Two forms of parallelism

It's useful to distinguish Node's internal worker pool from application worker threads.

The internal pool serves particular runtime operations.

Application worker threads run JavaScript code explicitly assigned to them.

Increasing a libuv worker-pool setting doesn't automatically make a CPU-heavy JavaScript loop run on additional cores.

You need to choose the mechanism that actually handles the limiting work.

## 6. Why `async` Doesn't Make CPU Work Parallel

Consider an asynchronous function that calculates prices.

It loops over half a million offers and performs several operations for each one.

Suppose the function contains no meaningful asynchronous suspension during the calculation.

Declaring it `async` means it returns a Promise.

It doesn't automatically create another execution thread.

And wrapping the function in `Promise.all()` doesn't change that.

### The Promise misconception

Imagine launching three CPU-heavy async functions.

If each one immediately begins a long synchronous calculation, they may execute sequentially on the main JavaScript thread until each reaches a suspension point or completes.

Promises represent asynchronous results.

They do not by themselves represent independent CPU execution resources.

### Yielding is not parallelism

You can divide a large calculation into chunks and yield between them.

That can improve responsiveness because other callbacks receive opportunities to execute.

But it doesn't make the total CPU work run simultaneously on several cores.

The same work still needs processor time.

Yielding improves fairness and latency.

Parallel workers can improve throughput for suitable independent tasks.

Those are different goals.

### The supplier aggregator decision

For thirty network calls, event-driven asynchronous I/O is appropriate.

For a heavy CPU batch, use an efficient algorithm and consider worker threads or separate processes if measurements justify parallelization.

For a small calculation, doing the work directly may be faster than introducing inter-thread overhead.

A mature application doesn't choose one concurrency mechanism for every task.

## 7. CPython: Bytecode, Objects, and an Interpreter

Now examine the Python implementation.

CPython compiles Python source into bytecode and executes it through interpreter machinery.

Python values are represented by runtime objects that carry type information and other implementation-specific metadata.

Operations such as addition, attribute access, and function calls follow Python semantics through the runtime's execution machinery.

### Dynamic operations have costs

A Python expression may involve more interpreter and object-management work than an equivalent operation compiled directly into specialized native arithmetic.

That can contribute to performance differences in tight loops.

But the comparison depends on the actual workload and implementation.

Modern CPython includes adaptive specialization mechanisms, and optional JIT capabilities have been developing.

It's no longer accurate to describe CPython as one completely unchanging interpreter implementation.

The broad architecture still differs from a conventional ahead-of-time native executable.

### The native-library surprise

Imagine a Python pricing system that performs a numerical calculation using a library implemented in optimized native code.

The surrounding application is Python.

But much of the expensive computation executes inside native routines.

The result may be much faster than an equivalent pure-Python loop.

The language used at the top of the program doesn't determine the implementation language of every operation beneath it.

This is especially relevant in scientific computing, data processing, and AI workloads.

When benchmarking Python, identify whether you're measuring Python-level loops, native numerical kernels, database waiting, or some combination.

## 8. CPython Memory: Reference Counting and Cycle Collection

We studied tracing garbage collection in L04.

CPython commonly uses a different combination of mechanisms.

Reference counting is central to ordinary object lifetime management.

When an object gains a strong reference, its reference count is adjusted.

When a strong reference disappears, the count is reduced.

When an object's reference count reaches zero, the runtime can typically begin deallocating it promptly.

### A useful consequence

Many ordinary objects are reclaimed soon after their final strong reference disappears.

But reference counting alone has a problem.

Consider two objects that reference each other.

No other part of the program refers to either object.

Each object still has a nonzero reference count because the other references it.

Neither count reaches zero.

This is a reference cycle.

### Cyclic garbage collection

CPython uses cyclic garbage-collection mechanisms to handle many unreachable reference cycles.

The collector can identify groups of objects that remain mutually referenced but are no longer reachable from meaningful external ownership paths.

The exact implementation has evolved over Python versions.

The important distinction is that CPython combines reference counting with additional cycle collection.

### The performance trade-off

Reference counting introduces bookkeeping as references change.

Object representation and allocation also have costs.

Tracing collectors make different trade-offs concerning pauses, throughput, memory overhead, and object-lifetime timing.

Neither strategy can eliminate application-level retention mistakes.

A Python dictionary retaining every customer profile will prevent those profiles from being reclaimed, just as a JavaScript Map can.

The retention policy remains an application responsibility.

## 9. The GIL: A Lock With a Precise Scope

The Python implementation experiences limited CPU scaling when adding ordinary threads.

To understand why, we need the Global Interpreter Lock.

In a traditional GIL-enabled CPython interpreter, a thread generally must hold the GIL to execute Python bytecode and interact with Python objects through the relevant interpreter APIs.

This means multiple ordinary Python threads in that interpreter don't simultaneously execute arbitrary Python bytecode on several CPU cores.

### Why the GIL existed

CPython historically relied heavily on reference counting and internal shared runtime state.

A global lock simplified important aspects of thread safety and implementation.

It reduced the need for fine-grained synchronization around many runtime operations.

But it also constrained certain forms of CPU parallelism.

### The I/O exception

When a Python thread performs a blocking I/O operation, the runtime can release the GIL around the wait.

Another Python thread can then execute.

So a traditional CPython program can use threads effectively for workloads that spend substantial time waiting for external resources.

This is why saying "Python threads are useless" is wrong.

### Native extensions

Some native libraries release the GIL while performing work.

For example, suitable numerical routines may execute substantial native computation outside ordinary Python bytecode execution.

That can allow concurrent native work under appropriate conditions.

But behavior depends on the specific extension and operation.

Do not assume every native function releases the GIL.

### The booking-platform consequence

If the Python service spends most of its time waiting for supplier HTTP responses, threads can overlap those waits.

If it spends most of its time executing a large pure-Python pricing loop, ordinary threads in a GIL-enabled interpreter may not produce useful multi-core speedup.

The distinction is about the executed work, not simply whether the source contains threads.

## 10. Free-Threaded CPython Changes the Calculation

The GIL is not the entire modern Python story.

CPython introduced experimental free-threaded builds in Python 3.13.

Starting with Python 3.14, free-threaded CPython became an officially supported, optional build configuration rather than merely experimental.

These builds can run with the GIL disabled, allowing Python threads to execute Python code in parallel across available cores.

This is a significant change.

### But the build matters

A standard GIL-enabled CPython installation doesn't become free-threaded merely because the application imports `threading`.

The interpreter must support free threading, and the GIL must actually be disabled at runtime.

Free-threaded builds can also run with the GIL enabled in certain configurations.

Some extension modules that haven't declared appropriate free-threading support can cause the GIL to be re-enabled.

Therefore, a deployment needs to verify the actual runtime configuration rather than relying on the installed Python version alone.

### Thread safety becomes more important

Removing a global lock doesn't make application data races disappear.

It makes real parallel access to Python objects possible.

That can expose shared-state bugs that were less likely to appear under traditional execution.

Python's standard libraries and built-in containers have implementation-specific thread-safety behavior, but developers shouldn't use incidental internal locks as substitutes for deliberate synchronization.

If two threads modify a shared booking counter, the application still needs a correctness strategy.

### Performance trade-offs

Free-threaded execution introduces additional synchronization and runtime bookkeeping requirements.

Some workloads can benefit substantially from parallel CPU execution.

Others may show little improvement or additional overhead.

Native extension compatibility, memory usage, and deployment support matter.

So the modern engineering conclusion is nuanced.

**Traditional CPython's GIL limits parallel pure-Python thread execution. Free-threaded builds offer another model, but the application's algorithm, synchronization, libraries, and workload still determine whether it benefits.**

## 11. Python Concurrency: Threads, Asyncio, Processes, and Interpreters

Python offers several ways to organize work.

They solve related but distinct problems.

### Threads

Threads are useful when ordinary blocking operations spend considerable time waiting and can release the GIL.

They share a process's memory, which makes communication convenient but introduces synchronization responsibilities.

On free-threaded builds, threads can also provide real parallel Python execution under suitable conditions.

### Asyncio

Python's `asyncio` uses cooperative asynchronous tasks coordinated through an event loop.

An async coroutine can suspend while awaiting an operation and allow another task to run.

This resembles the concurrency principle we discussed for Node.js.

But asynchronous Python functions don't automatically execute CPU-heavy work on several cores.

An `asyncio` task performing long synchronous computation without yielding can block the event loop.

### Processes

Python can use separate processes for CPU-intensive work.

Each process has its own interpreter and memory context.

On traditional CPython deployments, this avoids the single-interpreter GIL limitation for pure-Python CPU parallelism.

But data must be communicated across process boundaries.

Serialization, process startup, memory duplication, and scheduling impose costs.

### Multiple interpreters

Modern CPython also provides facilities for running work in multiple interpreters.

For example, `InterpreterPoolExecutor`, introduced in Python 3.14, uses interpreter isolation to support parallel execution with separate interpreter GILs in suitable configurations.

The model creates additional constraints around communication and shared state.

It is not automatically a simpler replacement for processes or threads.

### Choosing the mechanism

If supplier requests mostly wait on network I/O, asyncio or suitable threaded I/O may be appropriate.

If pricing calculations are CPU-intensive pure Python, process pools, supported free-threaded execution, native computation, or multiple interpreters may be candidates.

Benchmarking is necessary because coordination costs and library behavior differ.

There's no universal answer called "use async."

## 12. Structured Concurrency: The Lifetime of a Task Matters

Imagine the Python supplier aggregator starts thirty asynchronous requests.

One fails.

The customer cancels the search.

What happens to the remaining tasks?

Are they still running?

Will their errors be observed?

Will they continue consuming supplier API quotas after the customer is gone?

These are lifecycle questions.

### Task groups

Python's `asyncio.TaskGroup` provides a structured way to manage related asynchronous tasks.

Tasks created within the group are associated with a defined scope.

The context manager waits for its tasks to finish according to the group's semantics.

It also provides coordinated behavior when a task fails.

This is stronger than casually creating tasks and forgetting their references.

### Cancellation is cooperative

When an asyncio task is cancelled, cancellation is normally delivered through an exception at an appropriate suspension point.

A coroutine that never yields or deliberately suppresses cancellation may continue doing work.

And cancellation doesn't reverse remote side effects already committed by an external service.

A cancelled supplier request may already have reached the supplier.

A cancelled payment operation may already have charged the customer.

The runtime can manage local task lifetime.

The application must still handle business uncertainty.

### The broader principle

Related concurrent operations should have an explicit owner and lifecycle.

A request-scoped supplier search shouldn't silently create unbounded background work.

This applies to Node.js, Python, and Java, although their language and library mechanisms differ.

## 13. The JVM: Bytecode and Adaptive Execution

Now turn to the Java implementation.

Java source is commonly compiled into JVM bytecode.

The bytecode contains instructions for a virtual machine rather than for one specific hardware ISA.

A JVM implementation loads classes, verifies relevant properties, prepares runtime structures, and executes the program.

HotSpot can interpret bytecode and compile important methods into optimized native machine code.

### Runtime profiling

Like V8, HotSpot can use runtime information to guide optimization.

Frequently executed methods may receive greater compilation effort.

The optimizer can inline methods, simplify operations, eliminate some unnecessary allocations under suitable conditions, and optimize code based on observed behavior.

### Tiered compilation

HotSpot uses a tiered compilation architecture combining different levels of compilation effort.

The precise behavior depends on JVM version and configuration.

The essential trade-off is familiar from L05.

Compiling and optimizing code costs resources.

But optimized machine code can reduce repeated execution cost.

The runtime attempts to balance startup and warmup against long-term throughput.

### Why warmup matters

A Java service may exhibit different performance immediately after startup than after sustained execution.

Class loading, initialization, runtime compilation, cache warmup, and other activities contribute.

A benchmark that measures only the first few requests may produce a different ranking from one measuring steady-state throughput.

Neither measurement is inherently meaningless.

But each answers a different question.

A short-lived command-line utility may care greatly about startup.

A continuously running backend may care more about warmed-up execution and steady-state latency.

## 14. Java Memory Management: Managed Doesn't Mean Free

The JVM provides garbage-collected memory management for ordinary Java objects.

HotSpot supports several garbage collectors with different design goals and operational trade-offs.

The selection and tuning options depend on the JVM version and application requirements.

### Throughput and pause time

Garbage collectors must balance competing objectives.

How much total CPU work should collection consume?

How long can application execution be paused?

How much additional memory may the collector use?

How quickly must allocation continue?

Different collectors make different trade-offs.

### The heap isn't the entire process

A Java process also consumes memory outside the ordinary Java heap.

This can include thread stacks, code caches, native libraries, class metadata, direct buffers, and other runtime structures.

Therefore, a Java heap size limit isn't identical to the container's total memory consumption.

The same conceptual warning applied to Node.js in L04.

### Allocation isn't inherently disastrous

Modern JVM implementations are highly optimized for common allocation patterns.

Short-lived objects may be inexpensive to allocate and collect under suitable conditions.

Trying to avoid every object can make code more complex without improving real performance.

The important distinction is between allocation rate, retained state, and the workload's actual memory budget.

### Application leaks still exist

A Java HashMap retaining every customer profile can grow without bound.

The garbage collector must preserve the reachable entries.

A thread-local value may retain data longer than intended.

An unbounded queue may accumulate tasks.

Managed memory reduces certain manual memory-management risks.

It doesn't absolve the application of lifecycle and capacity design.

## 15. Java Platform Threads: Direct CPU Parallelism With Costs

Traditional Java platform threads are closely associated with operating-system threads.

The JVM can schedule Java work on several cores using multiple platform threads.

This makes CPU parallelism natural when the workload is divided appropriately.

### The benefit

Suppose the pricing batch can be partitioned into independent chunks.

Several platform threads can process those chunks simultaneously, subject to available CPU resources.

The JVM doesn't need to funnel all Java execution through a GIL-like global interpreter lock.

### The cost

Platform threads consume operating-system and runtime resources.

Each thread needs stack space and scheduler management.

Creating enormous numbers of threads can increase memory usage and context-switching overhead.

If most of those threads spend their time blocked on external services, dedicating a platform thread to every waiting request may become inefficient.

This is one of the motivations for virtual threads.

## 16. Java Virtual Threads: Make Waiting Less Expensive

A virtual thread is a Java Thread managed by the JVM rather than being permanently bound one-to-one to an operating-system platform thread.

Virtual threads execute on underlying carrier threads.

When a virtual thread reaches a supported blocking operation, the JVM can suspend it and release its carrier thread for other work.

Later, the virtual thread can resume.

### The familiar programming style

Imagine each supplier request is represented by code that reads naturally:

Call the supplier.

Wait for the response.

Process the result.

The source code can use blocking-style APIs while the JVM schedules many virtual threads efficiently around supported blocking operations.

This can make thread-per-request designs more scalable for I/O-intensive workloads.

### What virtual threads don't provide

A virtual thread performing CPU-intensive Java code needs a carrier thread and CPU time.

If many virtual threads simultaneously execute heavy calculations, they compete for finite processor resources.

Creating one million virtual threads doesn't create one million CPU cores.

### Database bottlenecks remain

Our Java service adopts virtual threads.

It can now keep far more supplier and database operations in flight.

But the database connection pool permits only a finite number of simultaneous connections.

The application begins more operations than the pool or database can handle efficiently.

Requests queue.

Latency increases.

The runtime has reduced the cost of waiting threads.

It has not increased the database's processing capacity.

### Pinning and modern Java

Early virtual-thread implementations had notable pinning limitations involving certain blocking operations inside synchronized regions.

JDK 24 introduced JEP 491, which significantly improved this behavior by allowing virtual threads to release carriers for common synchronized blocking scenarios.

Some circumstances, including particular native or foreign-function interactions, can still constrain virtual-thread scheduling.

Avoid repeating outdated advice that every synchronized block necessarily pins a virtual thread on modern JVMs.

The correct details depend on the JDK version and operation.

### The senior distinction

Virtual threads solve a scalability problem around representing many concurrent waiting tasks.

They aren't a general-purpose CPU accelerator.

And they don't make bounded dependencies infinite.

## 17. Three Approaches to the Same Supplier Workload

Now compare the runtimes with one concrete operation.

The booking service must call thirty suppliers.

Each request spends most of its lifetime waiting for a remote response.

### Node.js

An event-driven implementation can initiate many supplier requests concurrently.

One main JavaScript thread processes completions and performs the associated application logic.

The architecture is economical when callbacks remain short and the concurrency level is appropriately bounded.

### Python

An asyncio-based implementation can achieve a similar overlap of network waiting.

A threaded implementation may also work well because blocking I/O can release the GIL in traditional CPython.

The choice depends on library support, framework conventions, and application structure.

### Java

Virtual threads can represent each supplier request using a straightforward blocking style while the JVM manages many waiting threads efficiently.

An asynchronous HTTP client is another option.

Java doesn't require virtual threads for all concurrent I/O.

### The shared limit

Suppose the supplier permits only ten concurrent requests.

Launching thirty simultaneously may cause throttling or rejection.

The runtime's ability to initiate more operations doesn't imply that doing so improves the business result.

All three applications need a concurrency policy.

This is a key architectural point:

**Runtime concurrency determines how work can overlap. Application capacity policy determines how much work should overlap.**

## 18. Three Approaches to the Same CPU Workload

Now consider the second stage.

The application must process half a million quotations using a substantial amount of pure application logic.

The workload is CPU-bound.

### Node.js

A serial pricing loop occupies one JavaScript execution thread.

To use several cores, the application may divide the work among worker threads or processes.

The chunks must be large enough to justify messaging and coordination overhead.

### Traditional CPython

A pure-Python loop executing through ordinary threads in a GIL-enabled interpreter doesn't generally gain true multi-core Python-bytecode parallelism.

Process-based parallelism can help when the work is sufficiently large.

Suitable native libraries may provide faster computation or their own parallel execution.

### Free-threaded CPython

With an appropriate build and compatible dependencies, threads can perform Python work concurrently across cores.

But the application must account for synchronization, memory overhead, and the actual performance of its workload.

### Java

Ordinary platform threads or suitable parallel-execution facilities can distribute independent CPU work across available cores.

Virtual threads don't provide a special speed advantage for CPU-bound calculations.

### The shared bottleneck

All three systems remain limited by the processor, memory bandwidth, algorithmic complexity, synchronization, and container resource constraints.

The ideal strategy is to choose the simplest mechanism that gives adequate performance under the actual workload.

## 19. Why Benchmarking Across Runtimes Is Difficult

Suppose the company asks a direct question.

"Which implementation processes the pricing batch fastest?"

That sounds like an objective benchmark.

But first we need to define what *the same workload* means.

### Numeric semantics

JavaScript's ordinary number type uses IEEE 754 double-precision floating-point values.

Python integers can represent arbitrarily large integers, within available resources.

Java has fixed-width primitive integer types and additional arbitrary-precision or decimal classes.

If the application uses different numeric representations, the computations may not be equivalent.

For money, a comparison should define consistent cent-based or decimal arithmetic semantics, overflow behavior, rounding, and valid input ranges.

### Data structures

A JavaScript array of objects, a Python list of dictionaries, and a Java array of primitive values aren't equivalent memory representations.

One may require more indirections or allocations than another.

If the goal is to compare idiomatic applications, these differences matter.

If the goal is to isolate runtime execution overhead, the experiment needs tighter controls.

### Native libraries

A Python implementation using NumPy may perform most arithmetic in native code.

A Java implementation may use optimized primitive arrays.

A Node.js implementation may use typed arrays.

A benchmark comparing these is measuring entire implementations, not merely interpreter overhead.

### Warmup

JIT-based runtimes may need warmup to reach their optimized execution paths.

Startup-oriented benchmarks and steady-state benchmarks answer different questions.

### Concurrency and resources

A process limited to two CPUs cannot use eight cores simply because the machine has eight physical cores.

Thread and worker counts must be compared against actual available processing capacity.

### The correct outcome

A useful benchmark reports the precise workload, input distribution, runtime versions, configuration, resource limits, and observed latency or throughput distribution.

It doesn't produce one universal ranking of programming languages.

## 20. The Operational Contract of a Runtime

Performance isn't the only reason to choose a runtime.

A backend also has to start reliably, remain observable, shut down correctly, and fit within production resource budgets.

### Startup and warmup

Short-lived jobs may care about process startup and initialization cost.

Long-running services may tolerate more warmup in exchange for strong steady-state throughput.

The trade-off depends on deployment frequency, autoscaling behavior, and workload lifetime.

### Memory footprint

A runtime carries metadata, heaps, interpreter or JIT machinery, thread stacks, native libraries, and other structures.

The memory footprint affects how many replicas fit on a machine and how close the process operates to its memory limit.

But memory use should be judged in relation to useful throughput and latency, not as a standalone contest.

### Diagnostics

Node.js provides CPU profiling, heap snapshots, event-loop metrics, and runtime diagnostics.

Python provides profilers, tracing facilities, memory tools, and ecosystem-specific observability.

The JVM offers mature facilities such as Java Flight Recorder, thread dumps, memory diagnostics, and garbage-collection logs.

These tools have different strengths.

Operational familiarity affects the speed at which a team can diagnose incidents.

### Dependency compatibility

A runtime's ecosystem matters.

Python may be natural for scientific and AI libraries.

Node.js may be convenient for teams sharing TypeScript across browser and backend development.

Java may offer strong existing enterprise libraries and mature operational infrastructure.

But these are tendencies, not rules that determine every architecture.

The correct decision includes the team's actual dependencies and expertise.

## 21. The Capacity Trap: More Concurrency Can Make Everything Slower

Let's revisit the Java incident.

After adopting virtual threads, the team can represent thousands of supplier calls without dedicating thousands of heavyweight platform threads.

This appears to be a victory.

Then the database starts timing out.

What happened?

The application increased the number of concurrent operations it could initiate.

The database didn't gain proportional capacity.

The connection pool remains bounded.

Queries queue.

Locks and disk activity increase.

Response times rise.

Callers retry.

The system becomes slower despite a more scalable runtime mechanism.

### The same failure in Node.js

An engineer replaces a sequential loop with `Promise.all()` over ten thousand supplier calls.

The JavaScript event loop can represent many in-flight requests.

But the suppliers and local connection pools cannot necessarily sustain that fan-out.

The system may overwhelm its dependencies.

### The same failure in Python

An asyncio application creates tens of thousands of tasks without a semaphore or concurrency policy.

The event loop can schedule them.

But the underlying network, external API limits, and memory budget remain finite.

### The shared solution

Bound concurrency according to available capacity and business priorities.

Apply appropriate deadlines and backpressure.

Monitor queue lengths and dependency behavior.

Use retries carefully, especially during overload.

The runtime offers mechanisms for concurrency.

Architecture determines which concurrency levels are safe.

## 22. The Senior Engineer's Runtime Decision Framework

Suppose the company is choosing a runtime for a new service.

Before discussing language popularity, ask what the workload actually does.

### Is it mostly waiting?

If the service coordinates many network requests, prioritize efficient I/O concurrency and reliable lifecycle management.

Node.js, Python asyncio, traditional Python threads for suitable I/O, and Java virtual threads can all be reasonable choices.

The surrounding libraries and team experience matter.

### Is it mostly computing?

If the service spends substantial time executing CPU-intensive code, examine algorithmic efficiency, native-library options, and real parallel-execution mechanisms.

Node worker threads, Python multiprocessing or free-threaded execution, and Java threads may all be candidates.

### Does it move large amounts of data?

Memory representation, serialization, allocation, and copying may dominate.

The fastest arithmetic implementation may still lose if the application spends most of its time transforming data between representations.

### Is it latency-sensitive?

Measure the critical path.

A high-throughput implementation may still have unacceptable tail latency.

Garbage collection, event-loop blocking, thread scheduling, and dependency queues can matter.

### Is it short-lived or long-lived?

Startup and warmup costs may matter differently for command-line jobs, serverless functions, batch workers, and permanently running services.

### Can the team operate it?

Look at deployment tooling, observability, libraries, debugging expertise, and maintenance costs.

A runtime decision should improve the complete service, not merely win a synthetic benchmark.

### The practical conclusion

For our hotel platform, a Node.js API might continue coordinating supplier requests while a dedicated pricing worker handles expensive computation.

Or the team might use Python for a specialized model supported by mature native libraries.

Or Java might be the best fit for a service already integrated into a JVM-based ecosystem.

Different parts of one application can use different runtimes.

But introducing an additional runtime also creates operational cost.

A performance hypothesis alone doesn't justify a new language boundary.

## 23. Returning to the Three Incidents

We can now explain the original failures.

### The Node.js service

Its main JavaScript event loop was occupied by a large synchronous pricing calculation.

Other request callbacks were delayed.

The appropriate fix might involve optimizing the calculation, dividing it into responsive chunks, or moving substantial CPU work to a bounded worker pool.

The correct choice depends on profiling.

### The Python service

The team used ordinary threads for pure-Python CPU computation in a traditional GIL-enabled CPython runtime.

That did not produce the desired multi-core execution.

A process pool, suitable native computation, supported free-threaded execution, or another implementation strategy could address the limitation.

The decision requires benchmark evidence and compatibility checks.

### The Java service

Virtual threads reduced the overhead of representing many waiting operations.

But the application increased concurrent database demand beyond a healthy capacity.

The fix required bounded access, connection-pool discipline, query optimization, and dependency-aware admission control.

Not abandoning virtual threads.

### The connecting lesson

All three runtimes worked according to their models.

The teams made incorrect assumptions about what their concurrency mechanisms guaranteed.

The real skill is identifying which layer controls the limiting resource.

## 24. The Oral Examination

Answer each question aloud before reading the solutions.

### Challenge 1 — The Node.js Stall

A Node.js API coordinates many supplier requests successfully. When a large pricing calculation begins, unrelated requests become slow.

Why can one CPU-heavy function affect otherwise independent network operations?

### Challenge 2 — The Hidden Worker Pool

A Node.js application performs many asynchronous cryptographic operations. JavaScript CPU usage looks moderate, but operations queue up.

Which runtime resource might be saturated, and how does it differ from application worker threads?

### Challenge 3 — The Python Threading Mystery

A traditional CPython process launches eight threads performing pure-Python arithmetic.

CPU throughput barely improves over one thread.

Why?

Why might the result differ for network I/O or native numerical libraries?

### Challenge 4 — Free-Threaded Python

A colleague claims that Python 3.14 and later always execute Python threads in parallel.

What is inaccurate about this statement?

What must be verified in the deployed interpreter?

### Challenge 5 — The Reference Cycle

Two Python objects reference each other, but nothing else refers to either.

Why may reference counting alone fail to reclaim them?

Which additional mechanism addresses this?

### Challenge 6 — The Virtual-Thread Misconception

A Java service replaces platform threads with virtual threads.

A CPU-intensive calculation still takes approximately the same time.

Does that mean virtual threads are broken?

### Challenge 7 — The Database Collapse

A JVM application handles far more concurrent requests after adopting virtual threads, but database latency worsens.

Explain the likely resource mismatch and propose a response.

### Challenge 8 — The False Benchmark

A Python implementation uses a native numerical library. A Node implementation uses an ordinary JavaScript loop. A Java implementation uses primitive arrays.

The Python version wins.

What can we conclude, and what can we not conclude?

## 25. Solutions and Discussion

### Solution 1 — The event loop is occupied

Ordinary main-thread JavaScript callbacks execute on one thread.

A long synchronous calculation delays other callbacks and Promise continuations.

Asynchronous networking allows many operations to remain in flight, but their application-level completion processing still requires execution time.

A suitable worker pool or more efficient computation may address the bottleneck.

### Solution 2 — Libuv worker-pool capacity

Certain Node.js asynchronous APIs perform work through libuv's finite worker pool.

If that pool becomes saturated, operations can queue even while the main JavaScript thread remains responsive.

Application worker threads are a separate mechanism for executing JavaScript computations in parallel.

The solution depends on identifying which pool or execution resource is actually overloaded.

### Solution 3 — The traditional GIL limits simultaneous Python bytecode execution

In a GIL-enabled CPython interpreter, ordinary threads cannot generally execute pure-Python bytecode in parallel on multiple cores.

Threads can still overlap blocking I/O when the GIL is released.

Suitable native extensions may also release the GIL during computation.

Different work therefore produces different results.

### Solution 4 — Free-threading is optional and configuration-dependent

Python 3.14 made free-threaded builds officially supported, but they are not the universal default in every installation.

The interpreter must be built with free-threading support, and the GIL must be disabled at runtime.

Extension-module behavior, synchronization overhead, and workload characteristics affect actual parallel performance.

### Solution 5 — Reference cycles keep counts nonzero

Each object holds a reference to the other, so neither reference count reaches zero.

CPython's cyclic garbage collector can identify many unreachable cycles and reclaim them according to its rules.

This supplements reference counting.

### Solution 6 — Virtual threads aren't faster CPU threads

Virtual threads are designed primarily to make large numbers of concurrent waiting operations more economical.

CPU-intensive Java code still executes on actual processors.

The calculation remains limited by computational cost and available CPU resources.

Virtual threads may improve concurrency scalability without reducing the execution time of one CPU-bound task.

### Solution 7 — The database has finite capacity

The runtime can initiate more requests than the database can process efficiently.

Connection pools, locks, query execution, and storage resources become limiting factors.

Use bounded concurrency, appropriate connection-pool settings, query optimization, deadlines, and observability.

More cheap waiting tasks do not create more database capacity.

### Solution 8 — The whole implementations were compared

We can conclude that the Python-based implementation performed best for that particular experiment under its conditions.

We cannot conclude that all Python code is faster than all JavaScript or Java code.

The implementations use different data representations, libraries, and execution machinery.

A fair architecture decision must consider the actual application workload and operational constraints.

## 26. The Mental Model Worth Keeping

A managed runtime determines how source-level operations become executable work and how that work interacts with memory, threads, I/O, and the operating system.

Node.js makes event-driven I/O concurrency natural while requiring deliberate mechanisms for heavy parallel JavaScript computation.

CPython offers interpreter-based execution, multiple concurrency models, and different GIL configurations with important consequences for CPU parallelism.

The JVM combines runtime optimization, managed memory, and threading facilities—including virtual threads for scalable waiting-intensive applications.

But none of these mechanisms creates unlimited CPU, memory, database capacity, or network bandwidth.

When choosing or debugging a runtime, ask:

**Is the operation waiting or computing? Who actually executes the work? How many operations can progress simultaneously? Which resource is saturated? And what does the runtime guarantee about completion and memory?**

Those questions explain far more than language stereotypes.

## 27. Next Lecture — CS220-L07: Native Runtimes — Go, Rust, and Execution Trade-offs

We've examined three managed execution environments.

Next, we'll move toward native compilation and different runtime philosophies.

Go produces native code but includes a runtime scheduler, garbage collection, and lightweight goroutines.

Rust commonly produces native code with ownership-based memory management, without requiring a tracing garbage collector for ordinary values.

Both can be effective for backend services, but their trade-offs differ in memory management, concurrency, startup, binary size, deployment, and developer ergonomics.

We'll also revisit the claim that a compiled language is automatically faster.

A native executable can still spend most of its time waiting for PostgreSQL.

A Rust program can still use a poor algorithm.

A Go service can still overload a dependency with too many goroutines.

And a managed runtime can still execute selected computations extremely efficiently.

Next we'll see what native compilation changes—and what it doesn't.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

## Optional Practical Lab — One Workload, Three Runtime Models

**Objective:** Observe event-loop blocking, thread execution, free-threading configuration, and virtual-thread behavior without introducing production infrastructure.

The exercises use small bounded workloads. They are educational demonstrations, not a universal language benchmark.

### Lab A — Node.js: Event-loop delay under CPU work

Create `node-event-loop.mjs`:

```javascript id="labn01"
import { performance } from "node:perf_hooks";

function cpuWork(iterations) {
  let result = 0;

  for (let i = 0; i < iterations; i++) {
    result += Math.sqrt(i + 1);
  }

  return result;
}

const started = performance.now();

setTimeout(() => {
  const elapsed = performance.now() - started;

  console.log(
    "Timer observed after:",
    elapsed.toFixed(1),
    "ms"
  );
}, 100);

console.log("Starting CPU work");

const result = cpuWork(25_000_000);

console.log("CPU result:", result);
```

Run:

```bash id="labn02"
node node-event-loop.mjs
```

The timer's callback cannot execute until the main JavaScript thread is available.

Depending on your machine, the CPU work may finish before or after the timer's minimum threshold. Adjust the bounded iteration count if necessary for a visible demonstration.

**Question:** Why doesn't the timer execute at exactly 100 milliseconds?

### Lab B — Node.js: Separate CPU work into a worker

Create `cpu-worker.mjs`:

```javascript id="labn03"
import { parentPort, workerData } from "node:worker_threads";

let result = 0;

for (let i = 0; i < workerData.iterations; i++) {
  result += Math.sqrt(i + 1);
}

parentPort.postMessage({ result });
```

Create `node-worker-main.mjs`:

```javascript id="labn04"
import { Worker } from "node:worker_threads";
import { performance } from "node:perf_hooks";

const started = performance.now();

setTimeout(() => {
  console.log(
    "Timer observed after:",
    (performance.now() - started).toFixed(1),
    "ms"
  );
}, 100);

const worker = new Worker(
  new URL("./cpu-worker.mjs", import.meta.url),
  { workerData: { iterations: 25_000_000 } }
);

worker.on("message", ({ result }) => {
  console.log("Worker result:", result);
});

worker.on("error", console.error);
```

Run:

```bash id="labn05"
node node-worker-main.mjs
```

Compare main-thread timer responsiveness.

The worker performs its CPU work in another JavaScript execution context.

**Question:** Does the worker reduce the amount of calculation, or change where that calculation executes?

For a production application, prefer a bounded, reusable worker pool for repeated tasks rather than creating a new worker for every small request.

### Lab C — Python: Determine the actual GIL configuration

Run:

```bash id="labp01"
python -VV
```

Then:

```python id="labp02"
import sys
import sysconfig

print("Python:", sys.version)
print(
    "Free-threading build support:",
    sysconfig.get_config_var("Py_GIL_DISABLED"),
)

if hasattr(sys, "_is_gil_enabled"):
    print("GIL currently enabled:", sys._is_gil_enabled())
else:
    print("Runtime GIL-status API not available")
```

This distinguishes a free-threading-capable build from its current runtime GIL state where the relevant API is supported.

**Question:** Why is checking only the Python version insufficient to establish whether Python threads can execute Python bytecode in parallel?

### Lab D — Python: Threads versus processes

Create `python-parallel.py`:

```python id="labp03"
from concurrent.futures import (
    ThreadPoolExecutor,
    ProcessPoolExecutor,
)
from time import perf_counter

def calculate(limit: int) -> int:
    total = 0

    for number in range(limit):
        total += number * number

    return total

def benchmark(executor_type, tasks: int, limit: int):
    started = perf_counter()

    with executor_type(max_workers=4) as executor:
        results = list(
            executor.map(
                calculate,
                [limit] * tasks,
            )
        )

    return perf_counter() - started, sum(results)

if __name__ == "__main__":
    tasks = 4
    limit = 2_000_000

    for executor_type in (
        ThreadPoolExecutor,
        ProcessPoolExecutor,
    ):
        elapsed, checksum = benchmark(
            executor_type,
            tasks,
            limit,
        )

        print(
            executor_type.__name__,
            round(elapsed, 3),
            checksum,
        )
```

Run:

```bash id="labp04"
python python-parallel.py
```

Compare the results on your actual interpreter.

A traditional GIL-enabled CPython build may show limited benefit from threading for this pure-Python CPU workload.

A free-threaded build may behave differently.

Process startup and task serialization also affect measurements.

Repeat with larger and smaller workload sizes before drawing conclusions.

### Lab E — Python: Async I/O concurrency

Create `python-async.py`:

```python id="labp05"
import asyncio
from time import perf_counter

async def supplier(name: str, delay: float):
    await asyncio.sleep(delay)
    return f"{name} completed"

async def main():
    started = perf_counter()

    async with asyncio.TaskGroup() as group:
        tasks = [
            group.create_task(
                supplier(f"supplier-{i}", 0.2)
            )
            for i in range(10)
        ]

    results = [task.result() for task in tasks]

    print(results)
    print("Elapsed:", round(perf_counter() - started, 3))

asyncio.run(main())
```

Run:

```bash id="labp06"
python python-async.py
```

The tasks overlap their asynchronous waits.

This doesn't mean ten Python computations run simultaneously on ten CPU cores.

**Question:** Which part of this example benefits from concurrency?

### Lab F — Java: Platform threads and virtual threads

With a JDK supporting virtual threads, create `ThreadComparison.java`:

```java id="labj01"
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

public class ThreadComparison {

    static void runWorkload(boolean virtual) throws Exception {
        long started = System.nanoTime();

        try (var executor = virtual
                ? Executors.newVirtualThreadPerTaskExecutor()
                : Executors.newFixedThreadPool(20)) {

            for (int i = 0; i < 200; i++) {
                executor.submit(() -> {
                    Thread.sleep(100);
                    return null;
                });
            }
        }

        double elapsedMs =
            (System.nanoTime() - started) / 1_000_000.0;

        System.out.printf(
            "%s: %.1f ms%n",
            virtual ? "Virtual threads" : "20 platform threads",
            elapsedMs
        );
    }

    public static void main(String[] args) throws Exception {
        runWorkload(false);
        runWorkload(true);
    }
}
```

Compile and run using a compatible JDK:

```bash id="labj02"
javac ThreadComparison.java
java ThreadComparison
```

The example creates 200 short waiting operations.

It does not perform significant CPU calculation.

The fixed platform-thread pool limits concurrent tasks to twenty, while the virtual-thread executor creates a virtual thread for each task.

The comparison illustrates scheduling and waiting overhead, not superior computational speed.

**Question:** What result would you expect if the task performed heavy CPU arithmetic instead of sleeping?

### Lab G — The database overload thought experiment

Suppose all three implementations can maintain 5,000 concurrent waiting tasks.

The database safely handles 80 concurrent queries.

A team removes the application-level semaphore or limiter because the runtime supports cheap tasks.

Explain why latency may worsen.

Design a bounded-concurrency policy that considers the database connection pool, deadlines, queue capacity, and overload behavior.

### Lab H — Runtime architecture review

You are designing three services:

**Service A:** A browser-facing API that coordinates dozens of remote supplier requests.

**Service B:** A batch worker calculating prices for millions of offers.

**Service C:** An internal payment integration requiring strict idempotency, reliability, and clear operational diagnostics.

For each service, propose a suitable runtime and concurrency model.

You may use Node.js, CPython, Java, or a combination.

Defend your design using actual workload and operational requirements, not a generic claim that one language is faster than another.

---

## Further Reading

1. [Node.js — The Event Loop](https://nodejs.org/en/learn/asynchronous-work/event-loop-timers-and-nexttick) — Event-loop behavior and scheduling.
2. [Node.js — Don't Block the Event Loop](https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop) — Event-loop and worker-pool capacity.
3. [Node.js — Worker Threads](https://nodejs.org/api/worker_threads.html) — Parallel JavaScript execution.
4. [Python — Free-Threading Support](https://docs.python.org/3/howto/free-threading-python.html) — Supported configurations and compatibility constraints.
5. [Python — Thread States and the GIL](https://docs.python.org/3/c-api/threads.html) — Traditional and free-threaded interpreter behavior.
6. [Python — asyncio Tasks](https://docs.python.org/3/library/asyncio-task.html) — Async tasks, task groups, and cancellation.
7. [Python — concurrent.futures](https://docs.python.org/3/library/concurrent.futures.html) — Thread, process, and interpreter executors.
8. [Java — Virtual Threads](https://docs.oracle.com/en/java/javase/27/core/virtual-threads.html) — Virtual-thread behavior and use cases.
9. [JEP 491 — Synchronize Virtual Threads without Pinning](https://openjdk.org/jeps/491) — Modern virtual-thread pinning improvements.
10. [Java HotSpot VM Guide](https://docs.oracle.com/en/java/javase/27/vm/index.html) — JVM execution and optimization.
11. [Java HotSpot GC Tuning Guide](https://docs.oracle.com/en/java/javase/27/gctuning/) — JVM garbage-collection trade-offs.

---

## Dense Cheatsheet — Interview Glance Card

*This final reference is fenced for screen-based revision rather than continuous voice playback.*

```text id="cs22006card"
CS220-L06 — MANAGED RUNTIMES: NODE.JS, CPYTHON, JVM

THE CENTRAL QUESTION

  Is the workload WAITING or COMPUTING?

I/O CONCURRENCY
  Overlap operations waiting for external results.

CPU PARALLELISM
  Execute computations simultaneously on cores.

ASYNC != PARALLEL
THREAD COUNT != CPU COUNT

RUNTIME RESPONSIBILITIES

  Code execution
  Compilation / interpretation
  Memory management
  I/O and OS integration
  Scheduling / concurrency
  Diagnostics and tooling

NODE.JS

  V8 JavaScript engine
  libuv / OS integration
  Main JavaScript event loop
  Many concurrent in-flight I/O operations

  Long synchronous JS blocks main event loop.

  Promise.all doesn't create CPU cores.

NODE THREADING

  Main JS thread:
    Ordinary callbacks and application logic

  libuv worker pool:
    Certain fs, crypto, zlib, DNS operations

  worker_threads:
    Parallel application JavaScript
    Separate execution environments
    Message passing / transfer / shared memory

  Internal pool != application workers

NODE FAILURE MODES

  Event-loop blocked by CPU work
  Worker-pool saturation
  Unbounded Promise fan-out
  Unbounded queues / dependencies
  Excessive worker creation

CPYTHON

  Python source -> bytecode -> interpreter
  Dynamic object model
  Adaptive execution capabilities
  Native extensions may do expensive computation

MEMORY: CPYTHON

  Reference counting
  Prompt reclamation in many ordinary cases
  Cyclic GC for unreachable reference cycles

GIL: TRADITIONAL CPYTHON

  Only one thread generally executes Python bytecode
  at a time per GIL-enabled interpreter.

  Blocking I/O can release GIL.
  Some native extensions release GIL.

  Threads useful for I/O-bound work.
  Threads limited for pure-Python CPU parallelism.

FREE-THREADED CPYTHON

  Experimental in 3.13
  Officially supported optional build from 3.14

  Requires:
    Free-threading-capable build
    GIL disabled at runtime
    Compatible extensions

  Real CPU parallelism possible.
  No automatic thread safety.
  No universal speedup.

PYTHON CONCURRENCY

  threading:
    OS threads, shared process memory

  asyncio:
    Cooperative tasks and event loop
    Efficient I/O overlap
    CPU code still blocks unless offloaded/yields

  ProcessPoolExecutor:
    Separate processes, CPU parallelism
    Serialization and startup costs

  InterpreterPoolExecutor:
    Multiple interpreters, separate interpreter GILs
    Isolation / communication trade-offs

  TaskGroup:
    Structured lifetime and failure handling

JVM

  Java source -> bytecode
  Class loading / verification
  Interpreter + HotSpot JIT
  Managed memory / garbage collection

HOTSPOT

  Runtime profiling
  Tiered compilation
  Optimization after warmup
  Startup != steady-state performance

JVM MEMORY

  Java heap
  GC-managed ordinary objects
  Native memory
  Class metadata
  Code cache
  Thread stacks
  Direct buffers

  Heap size != whole process footprint

JAVA PLATFORM THREADS

  Closely map to OS threads
  Parallel CPU execution possible
  Significant per-thread resources at scale

JAVA VIRTUAL THREADS

  JVM-managed threads
  Scheduled on carrier platform threads
  Supported blocking I/O can unmount carrier
  Cheap representation of many waiting tasks

  Not faster for individual CPU computations.
  Not infinite database or network capacity.

  JDK 24 JEP 491 improved synchronized pinning.
  Version-specific native limitations remain.

TWO BOOKING WORKLOADS

SUPPLIER HTTP REQUESTS:
  Primarily I/O waiting

  Node:
    Event-driven async I/O

  Python:
    asyncio or suitable threads

  Java:
    Virtual threads or async clients

PRICING BATCH:
  Primarily CPU computation

  Node:
    Optimized loop / worker pool

  Traditional CPython:
    Processes / native libraries

  Free-threaded CPython:
    Compatible parallel threads

  Java:
    Parallel CPU work on platform threads
    or suitable execution facilities

  Virtual threads aren't special CPU accelerators.

CONCURRENCY TRAP

  Cheap tasks let you initiate more work.

  They DON'T increase:
    Database capacity
    Supplier rate limits
    CPU cores
    Network bandwidth
    Memory budget

  Bound concurrency to dependency capacity.

BENCHMARK FAIRNESS

  Equivalent arithmetic semantics
  Equivalent input distribution
  Equivalent work performed
  Account for native libraries
  Account for warmup and startup
  Control CPU and memory limits
  Report latency / throughput distribution
  Don't claim one language universally wins

OPERATIONAL CONSIDERATIONS

  Startup / warmup
  Memory footprint
  GC behavior
  Thread and worker overhead
  Profiling / tracing
  Deployment ecosystem
  Library compatibility
  Team expertise

SENIOR QUESTIONS

  What is the bottleneck?
  Who executes the computation?
  Is work waiting or actively running?
  How many cores can really be used?
  Which pool or queue is saturated?
  Does more concurrency increase useful throughput?
  What is the cost of cross-thread/process communication?

SENIOR LINE

  "I choose concurrency mechanisms by workload:
   event-driven or lightweight waiting for I/O,
   real parallel execution for CPU-heavy work,
   and explicit limits for downstream capacity.
   I evaluate runtimes through measured execution
   and operational characteristics, not stereotypes
   about interpreted or compiled languages."
```
