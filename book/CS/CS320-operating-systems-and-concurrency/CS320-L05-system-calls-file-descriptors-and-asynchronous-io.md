---
id: CS320-L05
course: CS320
title: "System Calls, File Descriptors, and Asynchronous I/O"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: CS320-L04
next: CS320-L06
---


# CS320 — Operating Systems and Concurrency

## Lecture 05: System Calls, File Descriptors, and Asynchronous I/O

*Your Node.js server handles thousands of connections with one main JavaScript thread. Then someone adds a perfectly ordinary file-reading operation, and unrelated requests suddenly become hundreds of milliseconds slower. The network is healthy. The CPU isn't saturated. What happened?*

# Part I — Intuition

## The picture to carry in your head

Imagine an extremely busy railway station.

Thousands of passengers arrive, depart, change platforms, and wait for trains.

Yet the station doesn't need one employee permanently assigned to every passenger.

Instead, a small group of dispatchers coordinates the operation.

They receive information about incoming trains, update platform assignments, issue instructions, and respond when something requires attention.

The dispatchers don't personally drive every train.

They don't spend hours staring at one track while a train approaches from another city.

They coordinate events.

Now imagine that one dispatcher receives a request to retrieve a document from the station archives.

Instead of assigning the job to someone else, the dispatcher walks into the archive, searches through hundreds of boxes, and returns twenty minutes later.

During those twenty minutes, arriving trains still reach the station.

The tracks still exist.

The signaling infrastructure still operates.

But nobody is available to make certain dispatching decisions.

The entire station becomes less responsive because one dispatcher stopped coordinating and began performing a slow operation personally.

That is the intuition behind our production incident.

Our Node.js server receives network data through operating-system facilities. The kernel can manage many network connections while the main JavaScript thread is busy elsewhere.

But JavaScript callbacks still need execution time.

If one callback performs a long synchronous operation, other callbacks cannot run promptly on that same thread.

To understand how this happens—and how asynchronous I/O avoids it—we need to examine the machinery connecting a program to the operating system.

## 1. The operating system gives applications handles to resources

Suppose our server opens a network connection.

On Unix-like systems, the process receives a **file descriptor**.

A file descriptor is a small nonnegative integer that identifies an entry in the process's descriptor table.

That entry refers to kernel-managed state associated with an open resource.

The resource might be a regular file, a TCP socket, a pipe, a terminal, or something else supported by the descriptor abstraction.

This is rather elegant.

Programs can use a common family of operations to interact with many kinds of resources.

But similar interfaces don't mean identical behavior.

Reading from a regular file is not necessarily implemented like reading from a TCP socket.

And a descriptor is not a promise that data is already available.

It's a handle through which the process can ask the kernel to perform operations.

## 2. Blocking: the dispatcher waits for the train

Imagine our server asking the kernel to read from a socket.

No data has arrived yet.

With a blocking read, the calling thread may wait until the operation can make progress, reaches end-of-stream, fails, or is otherwise interrupted according to the API's rules.

The thread is not necessarily burning CPU during this wait.

The scheduler may let other threads execute.

But the particular calling thread cannot continue its ordinary instruction sequence until the blocking operation returns.

That matters enormously for Node.js.

If its main JavaScript thread enters a long blocking operation, that thread cannot execute other JavaScript callbacks during the wait.

The kernel can continue receiving network packets.

Other processes and threads can keep running.

But our main JavaScript execution lane is unavailable.

Blocking I/O is not inherently bad. A dedicated background thread may reasonably wait for one operation.

The problem appears when a thread responsible for coordinating many independent operations becomes occupied waiting for just one.

## 3. Nonblocking: check whether the train is ready

There's another way to interact with a socket.

Configure it for nonblocking I/O.

Now, if a read cannot presently make progress without waiting, the operation can return immediately with a condition such as `EAGAIN` or `EWOULDBLOCK`.

The application knows that the desired data isn't currently available.

But repeatedly asking the socket whether anything has arrived would be wasteful.

Our dispatcher would be running from platform to platform every second, checking whether a train had appeared.

Instead, the application can ask an event-notification facility to report when the socket becomes ready.

That gives us **readiness-based I/O**.

The kernel monitors appropriate resource conditions and reports relevant events.

The application can wait efficiently for activity across many sockets rather than dedicating a blocked thread to each connection.

When a socket becomes readable, the application attempts to read.

When it becomes writable, the application may attempt to send more data.

Crucially, readiness is not the same as completion.

The operating system may tell us that reading can make progress.

It does not guarantee that an entire HTTP request has arrived.

## 4. One thread can coordinate many waiting connections

Imagine ten thousand clients connected to our server.

Most of them are doing nothing at this precise moment.

They're waiting for responses, user actions, or new messages.

Creating one dedicated operating-system thread for every idle connection is possible in some designs, but it can be expensive.

Each thread has associated memory, scheduling state, and management overhead.

An event-driven server can instead register interest in relevant socket events.

Only connections that need attention produce useful work for the event loop.

The main JavaScript thread processes callbacks when appropriate work becomes available.

That's how one JavaScript thread can participate in thousands of concurrent network conversations.

But don't mistake concurrency for unlimited computational power.

If ten thousand connections all require expensive JavaScript calculations simultaneously, the main thread becomes a bottleneck.

And if one callback blocks for half a second, other callbacks must wait for that execution lane.

The efficiency comes from not dedicating a thread to every period of I/O waiting.

It doesn't come from making execution free.

## 5. The surprising part: asynchronous files can use threads

Now suppose our server needs to read a large PDF report from disk.

Why not simply use the same socket-readiness mechanism?

Because regular-file I/O and network-socket I/O don't expose exactly the same useful readiness behavior on traditional Unix-like systems.

A regular file is generally not monitored with Linux `epoll` in the same manner as a network socket.

So one common runtime strategy is to delegate filesystem operations to a native worker pool.

The main JavaScript thread submits the operation.

A native worker performs the relevant filesystem work, potentially blocking while doing so.

When the operation finishes, the runtime arranges for the result to become available to JavaScript.

From the JavaScript caller's perspective, the API is asynchronous.

But that does not imply that no thread waited.

The waiting simply occurred somewhere other than the main event-loop thread.

This gives us two broad mechanisms:

**Socket readiness:** the runtime monitors events and performs I/O when the resource can make progress.

**Worker-pool execution:** the runtime delegates operations to native threads and later reports their completion.

Both can support asynchronous JavaScript APIs.

Their performance characteristics differ.

## 6. A promise is not an operating-system mechanism

Consider an asynchronous JavaScript function.

It returns a Promise.

That tells us something about how the JavaScript caller receives a future result.

It does not, by itself, tell us how the underlying operation executes.

Perhaps the runtime monitors a nonblocking socket.

Perhaps it queues filesystem work to a native pool.

Perhaps it uses a platform-specific completion facility.

Or perhaps the function does expensive synchronous work before returning a Promise.

The word `async` doesn't automatically move arbitrary computation to another thread.

And a Promise doesn't automatically create a kernel operation.

**Language-level asynchrony and operating-system I/O mechanisms are separate layers.**

That's the distinction we need before descending into the actual implementation.

## Three questions before the Deep Dive

Try answering aloud.

1. How can a server maintain ten thousand network connections without creating ten thousand JavaScript threads?
2. What does socket readability guarantee—and what does it not guarantee?
3. Why can two asynchronous JavaScript APIs have completely different performance behavior even though both return Promises?

The mental picture is one dispatcher coordinating many operations, with different kinds of work progressing through different underlying mechanisms.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The file that froze a thousand connections

It's 11:42 on a Tuesday morning.

Our hotel-booking backend is behaving normally.

Customers search for accommodation, retrieve availability, and confirm reservations. The service maintains thousands of network connections and handles ordinary API traffic with moderate CPU consumption.

Then the company deploys a new feature.

Enterprise customers can download large PDF reports.

The implementation reads the report from a local filesystem path and sends it as an HTTP response.

The developer uses a synchronous file-reading function.

On the development machine, with a tiny cached report, the operation appears instantaneous.

In production, a customer requests a large report located on a slower storage path.

The read takes several hundred milliseconds.

Suddenly unrelated endpoints experience severe latency spikes.

Hotel-search requests take much longer.

Availability responses are delayed.

A lightweight health endpoint occasionally responds slowly.

PostgreSQL is healthy.

The network appears healthy.

CPU usage is not necessarily high.

But the JavaScript event-loop thread is occupied by the synchronous file operation.

Meanwhile, socket data continues arriving at the operating-system boundary.

The kernel can maintain connection state and receive bytes into appropriate buffers.

Yet the runtime cannot execute ordinary JavaScript callbacks on its main thread until the synchronous operation returns.

The problem isn't that every connection became slow independently.

It's that **one shared execution lane stopped servicing them**.

To understand this precisely, we need to follow an I/O operation from the JavaScript API down to the kernel.

## 2. The system-call boundary

In CS320-L01, we established that applications ordinarily execute in user mode, while the kernel manages protected resources.

That boundary matters for I/O.

A program cannot simply read arbitrary physical disk sectors or manipulate kernel socket structures without the appropriate interfaces.

Instead, it uses operating-system services.

On Linux, relevant system calls include operations such as opening files, reading and writing data, creating sockets, connecting, accepting connections, and controlling file descriptors.

But a high-level Node.js API call isn't necessarily equivalent to one system call.

Suppose JavaScript invokes a file-reading API.

The runtime might validate arguments, resolve paths, create a native request, queue work, open a file, perform several reads, handle partial results, and eventually deliver a response to JavaScript.

One application-level operation may involve multiple kernel interactions.

Conversely, many small application operations may use a shared kernel resource established earlier.

The crucial boundary is therefore not a one-to-one mapping between JavaScript functions and system calls.

It is the relationship between application intent, runtime machinery, and kernel-managed resources.

### The cost of crossing the boundary

Entering the kernel is not identical to an ordinary user-space function call.

It involves a controlled transition into privileged execution, with architecture-specific entry and return mechanisms.

That has overhead.

But we should not conclude that system calls are universally expensive or that the goal is to eliminate them.

Their cost depends on the operation, kernel state, hardware, and surrounding work.

A simple syscall might be relatively cheap.

A syscall that blocks waiting for storage can take vastly longer.

Often the expensive part is not the privilege transition itself but the operation requested.

That's why measuring an application's syscall count without examining what the calls do can be misleading.

## 3. File descriptors: the process's resource handles

A Unix-like file descriptor is an integer used to identify an open descriptor-table entry in a process.

For example, a process ordinarily begins with familiar standard descriptors:

Zero for standard input.

One for standard output.

Two for standard error.

Additional files and sockets receive other descriptor numbers.

The important detail is that the integer is a handle, not the underlying file or socket itself.

### Descriptors and open-file descriptions

Linux distinguishes descriptor entries from underlying open-file descriptions.

An open-file description contains relevant kernel-managed state, including file offset and file status flags for appropriate file types.

Multiple descriptors can refer to the same open-file description.

For example, duplicating a descriptor may produce another descriptor number referencing shared underlying state.

That means duplicate descriptors can share file offsets and status flags.

On the other hand, opening the same pathname independently can create distinct open-file descriptions with separate offsets.

This distinction is subtle but useful.

If two parts of a program unexpectedly influence one another's file position, check whether they share an open-file description rather than merely the same pathname.

### Descriptors are finite resources

Every open descriptor consumes some operating-system resources.

A process can also be subject to a descriptor limit.

If an application continually opens files or sockets without closing them appropriately, it may exhaust its allowed descriptors.

A new open operation can fail with `EMFILE`, meaning the process has reached its applicable open-descriptor limit.

This can make an otherwise healthy server unable to accept new connections or open new files.

And simply increasing the descriptor limit may only delay a leak.

We need to distinguish legitimate concurrent resource demand from descriptors whose lifetimes are no longer managed correctly.

### Closing and reusing descriptors

When a process closes a descriptor, its number can later be reused.

Consequently, the number itself is not a permanent identity for a particular network connection.

Application code that retains stale descriptor numbers or uses a descriptor concurrently with unsafe lifetime management can produce difficult bugs.

The general rule is that resources need explicit ownership and lifecycle discipline.

A descriptor represents a resource relationship.

It isn't merely a harmless integer.

## 4. Blocking I/O: one thread waits

Suppose our application reads from a TCP socket.

The socket has no data available.

In blocking mode, the calling thread may sleep until the read can make progress, encounters a relevant error, or otherwise returns.

The operating system can schedule other tasks during the wait.

So blocking I/O doesn't necessarily consume a full CPU continuously.

But the calling thread is unavailable for other application work.

That distinction explains why blocking is acceptable in some architectures and disastrous in others.

### One thread per connection

Imagine a server that dedicates one operating-system thread to each connection.

If a thread blocks waiting for its client, other connection threads may still execute.

The operating system schedules them independently.

This can be a straightforward programming model, especially when supported by appropriate runtime facilities.

But it carries resource costs.

Large numbers of threads require scheduling management, stack resources, and coordination.

Some modern runtimes provide lightweight user-space or virtual-thread abstractions that reduce certain costs, but they do not eliminate finite CPU, memory, and I/O capacity.

### One event-loop thread

Now consider the conventional Node.js design.

The main JavaScript thread is responsible for executing callbacks associated with many connections.

If this thread enters a blocking filesystem operation, the delay is shared across unrelated application tasks.

The key failure is not that blocking exists.

It's that blocking occurs on a thread responsible for many independent operations.

## 5. Nonblocking sockets and `EAGAIN`

Now switch the socket to nonblocking mode.

The application attempts to read.

If data is available, the operation may return some bytes.

If no data is currently available and the operation would otherwise block, it can return a condition such as `EAGAIN` or `EWOULDBLOCK`.

The application can then arrange to try again later.

### Partial reads

Suppose the sender transmits an HTTP request.

The receiver asks for four thousand bytes.

The kernel returns only six hundred.

That doesn't necessarily mean the request contains only six hundred bytes.

TCP is a byte-stream protocol.

The read operation may return whatever data is currently available, within the request and API semantics.

There is no guarantee that one network read corresponds to one application-level message.

The runtime or protocol parser must accumulate and interpret the bytes correctly.

### End-of-stream

For a stream socket, a read returning zero bytes under the ordinary end-of-stream condition indicates that the peer has closed its sending side and no further bytes remain to be read.

That is distinct from a nonblocking read reporting that no data is currently available.

`EAGAIN` means "try again when progress is possible."

End-of-stream means there is no more stream data from that sending direction.

Confusing these conditions can produce broken connection handling.

### Partial writes

Writes can also make partial progress.

A nonblocking socket may accept only some of the supplied data before its buffers become constrained.

The application must arrange to send the remaining data later.

This is why a socket being writable is not equivalent to having infinite output capacity.

The kernel provides a mechanism for progress.

The application must still manage the operation's state.

## 6. Why polling every socket is a bad idea

Imagine our server manages ten thousand connections.

It could repeatedly inspect every socket to see whether anything has arrived.

But most connections may be idle.

Continuously checking them wastes work.

A better design asks the operating system to notify the application when relevant conditions occur.

Historically, Unix-like systems have provided interfaces such as `select` and `poll`.

These allow applications to wait for readiness conditions across sets of file descriptors.

They are useful conceptual foundations.

The application identifies resources of interest.

The kernel waits for relevant events.

When the wait returns, the application examines which resources can make progress.

### Limitations of traditional polling interfaces

Traditional mechanisms can have scalability limitations associated with descriptor-set representation, per-call setup, and repeated scanning.

For large servers with many mostly idle connections, those costs matter.

Different operating systems developed more sophisticated event facilities to support large-scale event-driven workloads.

Linux provides `epoll`.

BSD-family systems and macOS provide `kqueue`.

Windows provides facilities including I/O Completion Ports, commonly called IOCP.

They do not all have identical semantics.

But they support the broader goal of efficiently coordinating many outstanding I/O interests and events.

## 7. Linux `epoll`: let the kernel remember the interests

The central advantage of `epoll` is that an application can establish a monitored interest set rather than rebuilding a complete large collection on every wait.

Conceptually, the sequence is straightforward.

First, create an epoll instance.

Second, register relevant file descriptors and desired events.

Third, wait for events.

Linux exposes interfaces such as `epoll_create1`, `epoll_ctl`, and `epoll_wait`.

For a network server, the monitored resources commonly include listening sockets and established connections.

When relevant readiness conditions occur, the application receives information about which monitored descriptors deserve attention.

### Follow one connection

A customer opens a TCP connection to our hotel-booking backend.

The kernel establishes the relevant socket state.

The runtime monitors the socket for appropriate events.

The customer sends an HTTP request.

The kernel receives bytes.

The socket becomes readable.

The event facility reports the relevant condition.

The runtime performs the required nonblocking reads and protocol processing.

Eventually, an HTTP request becomes available to JavaScript.

Only then does our request handler execute.

Notice the boundaries.

The packet's arrival is not the same event as a JavaScript callback beginning.

The kernel may have data ready before JavaScript gets an opportunity to process it.

That distinction is exactly why a blocked event loop produces latency even when network delivery itself remains healthy.

## 8. Level-triggered versus edge-triggered readiness

This distinction deserves special attention because it illustrates the discipline required by event-driven I/O.

Suppose a socket contains one thousand unread bytes.

### Level-triggered mode

In level-triggered operation, readiness can continue to be reported while the relevant condition remains true.

If the application reads only four hundred bytes, six hundred remain.

A subsequent readiness wait can report the socket as readable again.

The condition is still present.

### Edge-triggered mode

Edge-triggered operation emphasizes notifications associated with readiness changes or transitions rather than continually reporting an unchanged ready condition.

This can reduce redundant notifications.

But it imposes stricter requirements.

Suppose the application reads four hundred bytes from the thousand-byte buffer and then goes back to waiting without properly exhausting the available data.

It may fail to receive another notification for the bytes that remain.

The program could appear stuck despite already having readable data.

The standard safe approach is to use nonblocking descriptors and continue the appropriate read or write operation until it reports that no further progress can currently be made, commonly through `EAGAIN`.

Then wait for the next relevant event.

This isn't a universal instruction to perform unbounded work in one event-loop callback; production implementations also need fairness and appropriate handling of work budgets.

It is a statement about correctly tracking readiness state.

Most Node.js developers never call `epoll` directly.

That is one of the benefits of using mature runtime libraries.

They handle complex details of polling, readiness state, and platform behavior beneath higher-level APIs.

### Why ordinary files are different

An important caveat is that ordinary regular files aren't generally suitable for Linux `epoll` monitoring in the same way as network sockets.

Registering a regular file with `epoll` can fail with `EPERM`.

This is one reason we shouldn't assume a socket and a disk file use the same asynchronous execution mechanism merely because both have descriptors.

The descriptor abstraction is common.

The available I/O mechanisms depend on the resource.

## 9. Readiness and completion are different programming models

So far we've described readiness.

The kernel tells the application that an operation may make progress.

The application still performs the corresponding read or write and manages partial results.

But operating systems also support completion-oriented mechanisms.

In a completion-oriented model, the application arranges for an operation to be performed and later receives information about its result.

The distinction is:

**Readiness:** The resource can currently make progress.

**Completion:** A submitted operation has produced a result.

That sounds like a small difference.

Architecturally, it is significant.

In the first model, the application reacts to readiness and performs the I/O.

In the second, the application is informed about a particular operation's completion.

### `kqueue` and IOCP

On macOS and BSD-family operating systems, `kqueue` provides an event-notification facility supporting various event sources.

It is conceptually related to readiness-based event handling, although its supported filters and exact semantics differ from Linux `epoll`.

Windows IOCP supports completion-oriented asynchronous I/O patterns.

An application can associate suitable I/O handles with a completion port and receive completion notifications for operations.

The broader lesson isn't to memorize every platform-specific API.

It is to recognize that a cross-platform runtime must adapt to different operating-system facilities.

A JavaScript API can present a broadly consistent programming model while relying on different mechanisms underneath.

## 10. Linux `io_uring`: submitting operations to the kernel

Linux also offers `io_uring`.

Its central architecture uses submission and completion queues shared between user space and the kernel.

An application can describe supported operations through submission entries.

The kernel processes those requests according to the interface's rules.

Completion entries report results.

This design can reduce certain syscall and coordination overheads and support efficient asynchronous I/O under appropriate conditions.

But it isn't a universal performance cheat code.

### Not every operation is magically zero-copy

The existence of `io_uring` does not mean every data transfer avoids memory copies.

Nor does it mean every operation completes without any kernel worker involvement.

The actual behavior depends on the operation, kernel version, configuration, buffers, and execution path.

Some operations can benefit substantially.

Others may use different internal mechanisms.

### Not every runtime automatically uses it

Here's a particularly important version-sensitive detail.

Libuv has supported optional Linux `io_uring` integration for certain filesystem operations in some versions.

Its documented behavior also changed across releases, including a return to thread-pool operation by default in libuv 1.49, with specific configuration required for the optional `io_uring` path.

Therefore, we should not claim that modern Node.js automatically uses `io_uring` for every asynchronous file operation.

The operating-system feature may exist without the application using it.

If the distinction matters to a production performance investigation, examine the actual Node.js and libuv versions and configuration.

**Available kernel capability is not evidence of actual application execution path.**

## 11. Libuv: the bridge beneath Node.js

Now we can connect everything to Node.js.

Node.js uses libuv as a major part of its cross-platform event-loop and asynchronous I/O infrastructure.

Libuv supplies abstractions for networking, filesystem operations, event loops, timers, asynchronous work, and other integration with the operating system.

On Linux, suitable networking operations can use facilities such as `epoll`.

On macOS, the implementation can use `kqueue`.

On Windows, IOCP and other platform mechanisms are relevant.

Libuv hides many of these differences.

The JavaScript developer uses high-level APIs while the native runtime coordinates the lower-level work.

But libuv does not make every kind of I/O follow one identical path.

### Two routes to an asynchronous JavaScript result

Consider a TCP socket.

The runtime can use operating-system readiness notification, perform nonblocking I/O, and eventually make the received data available to JavaScript.

Now consider an asynchronous filesystem operation.

Under the conventional libuv filesystem path, the runtime delegates work to its native thread pool.

The worker performs the relevant operation, and completion is reported to the event loop.

Both cases eventually involve JavaScript callbacks or Promise continuations.

Yet the work may have progressed through very different mechanisms.

This is the essential distinction beneath the word `async`.

## 12. Why filesystem operations can occupy native threads

Suppose our server reads a large report using an asynchronous Node.js filesystem API.

The JavaScript caller doesn't synchronously wait for the file data.

Under the traditional libuv worker-pool path, the runtime submits work for native execution.

A worker can perform blocking filesystem operations without occupying the main JavaScript event-loop thread.

When the work completes, its result is eventually delivered through the runtime.

This is useful.

But it introduces a finite resource: worker-pool capacity.

### The default pool

Libuv's thread pool traditionally defaults to four workers, with supported configuration through `UV_THREADPOOL_SIZE`.

The pool is shared by operations using it.

It is not the total number of threads in the Node.js process.

And it is not the same thing as JavaScript `worker_threads`.

Those are separate mechanisms.

### The fifth operation

Imagine all four pool workers are occupied by expensive operations.

A fifth pool-dependent operation arrives.

It may wait until a worker becomes available.

The JavaScript Promise remains pending.

But the event-loop thread can still execute unrelated callbacks.

This is not an event-loop blockage.

It is native worker-pool queueing.

### Shared pool, unexpected interference

Now imagine that the report service performs expensive filesystem operations while another code path uses asynchronous cryptographic operations that also consume the libuv worker pool.

The tasks compete for the same finite native workers.

A slow filesystem operation can therefore delay apparently unrelated pool-backed work.

The effect may be especially surprising when everything is written using Promises.

The Promise abstraction does not reserve independent execution capacity for every operation.

### A DNS example

Node.js `dns.lookup()` commonly uses the system name-resolution path via the libuv worker pool.

By contrast, `dns.resolve()` uses a different DNS-resolution mechanism, based on network DNS queries rather than the same system resolver path.

Both APIs involve DNS-related behavior.

But they can differ in implementation and performance characteristics.

This reinforces the central lesson.

Two functions with similar JavaScript interfaces can depend on different native resources.

## 13. Incident A: the event loop is blocked

We can now reconstruct our original failure precisely.

A customer requests a report.

The handler calls a synchronous filesystem-read API.

The main JavaScript thread enters the operation and cannot continue ordinary callback execution until the read returns.

Meanwhile, other HTTP requests arrive.

The kernel can receive their network bytes.

Sockets may become readable.

Other native or kernel operations may complete.

But their JavaScript handlers cannot execute promptly because the event-loop thread is occupied.

### A simplified timeline

At time zero, the report handler begins a synchronous read.

Ten milliseconds later, customer B's request arrives.

Twenty milliseconds later, customer C's request arrives.

Thirty milliseconds later, a database operation associated with customer D finishes.

At two hundred fifty milliseconds, the synchronous report read finally returns.

Now the runtime can begin processing the accumulated JavaScript work.

Customer B didn't necessarily experience slow packet delivery.

Customer D's database query didn't necessarily become slower.

Their callbacks were delayed because the main execution thread was unavailable.

### What metrics would reveal it?

Event-loop delay may increase.

The affected endpoints may show correlated latency spikes.

The recently introduced synchronous operation may dominate the relevant request-handler timeline.

CPU utilization might remain modest if the synchronous read spends much of its time waiting for I/O.

A CPU profiler alone may not fully explain the delay if substantial time is spent blocked inside a native operation.

We need to combine runtime measurements, operation timing, and relevant operating-system evidence.

The proper explanation is **main-thread blockage**, not necessarily CPU saturation.

## 14. Incident B: the event loop is free, but the pool is busy

We replace the synchronous report read with an asynchronous filesystem operation.

The original widespread latency spikes disappear.

Lightweight endpoints respond normally.

But now some report downloads still take much longer than expected.

Why?

We investigate and find several expensive pool-backed operations already occupying native workers.

Other operations wait for capacity.

The event loop remains available.

The filesystem task hasn't completed.

These two incidents produce superficially similar outcomes—slow report responses—but very different patterns elsewhere.

In Incident A, unrelated JavaScript callbacks are delayed.

In Incident B, operations that depend on finite native workers may be delayed while unrelated event-loop work continues.

### Why increasing the pool isn't automatically the answer

Someone proposes raising `UV_THREADPOOL_SIZE` dramatically.

That could help in certain circumstances.

But more workers consume additional resources.

If filesystem operations are limited by the underlying storage device, increasing concurrency can create more I/O contention without increasing useful throughput.

If native tasks are CPU-intensive, more workers may compete for the same constrained CPU budget.

If operations allocate substantial memory, more simultaneous work may increase peak memory demand.

We have already studied CPU quotas and memory pressure.

Those resource limits still apply here.

A larger pool isn't new physical capacity.

It merely changes how much work can compete at once.

The correct investigation measures task durations, effective concurrency, queueing, and the actual limiting resource.

Then we can decide whether to adjust pool size, reduce task granularity, isolate work, or bound demand.

## 15. Asynchronous doesn't mean finished

Let's return to the network path.

The kernel reports that a socket is readable.

Does that mean an entire HTTP request has arrived?

No.

The socket may contain only a fragment of the incoming byte stream.

The runtime must read available bytes and the HTTP parser must assemble a valid message.

Now suppose a filesystem operation completes.

Does that mean the JavaScript callback has executed?

Again, no.

Completion can be reported to the event loop, but JavaScript execution still depends on the main thread being able to process the result.

Finally, suppose the server successfully writes response bytes into a local socket buffer.

Does that prove the client application processed the complete response?

No.

Local write completion, remote transport receipt, and application-level success are different boundaries.

This is an important general principle:

**Resource readiness, operation completion, callback execution, and business success are four different events.**

They may occur close together.

They are not equivalent.

A correct investigation names the boundary being measured.

## 16. Even nonblocking I/O has finite capacity

Asynchronous I/O makes waiting more efficient.

It doesn't make resources infinite.

Imagine our report endpoint generates a large response.

The client reads slowly.

The server can initially write data into operating-system and runtime buffers.

Eventually, those buffers may fill.

A nonblocking socket write cannot assume unlimited capacity.

The runtime must manage partial writes and future writability.

Higher-level stream APIs provide mechanisms for managing this pressure.

For example, Node.js writable streams can report that their internal buffering threshold has been reached.

When `write()` returns `false`, the producer should respect the stream's backpressure contract rather than continuing to enqueue data without bound.

The appropriate `drain` event allows the producer to resume when the stream can accept more data under its API semantics.

### Reading everything versus streaming

Compare two report-delivery designs.

The first loads the entire report into one large Buffer and then sends it.

The second streams file data through appropriately bounded buffers toward the HTTP response.

For large reports, streaming can reduce peak application memory and provide a natural place to respect downstream backpressure.

But not every workload can be streamed.

Some formats require complete input or random access.

And streaming still involves buffering, resource lifetime, and possible I/O delays.

The engineering question is whether the operation can make useful progress incrementally while keeping memory demand bounded.

This connects asynchronous I/O with our previous memory lesson.

Efficient waiting and bounded buffering solve different parts of the same resource problem.

## 17. Cancellation doesn't undo completed work

Suppose the client disconnects halfway through a report download.

The application should normally avoid continuing unnecessary processing when it is safe to stop.

But cancellation semantics require care.

An `AbortSignal` or equivalent mechanism requests cancellation through a particular API contract.

It doesn't universally guarantee that every native operation already submitted to the kernel or worker pool disappears instantly.

Some work may already have completed.

Some operations may not support immediate cancellation.

Some may report cancellation even though partial lower-level effects occurred.

A timed-out operation is similarly not proof that remote work never happened.

In this chapter, the important operating-system distinction is that the lifetime of a JavaScript Promise, the lifetime of a native request, and the lifetime of a kernel operation are related but not necessarily identical.

CS320-L06 will examine how applications coordinate cancellation, retries, bounded concurrency, and task lifetimes.

For now, remember that stopping an application's interest in a result is not automatically equivalent to undoing the underlying operation.

## 18. Diagnosing I/O latency by finding the waiting boundary

Imagine a production incident involving slow HTTP responses.

We should not begin by assuming the network is slow simply because customers are waiting for responses.

Instead, distinguish competing possibilities.

### Case one: all endpoints are delayed

If a report download causes unrelated lightweight endpoints to slow down, investigate main-thread blockage and event-loop behavior.

Measure the synchronous operation.

Inspect recent code changes.

Consider whether the thread is blocked in I/O, executing expensive JavaScript, or being delayed by operating-system scheduling.

### Case two: only filesystem-dependent operations stall

If lightweight endpoints remain responsive while filesystem operations are slow, inspect the file path, storage latency, native worker-pool dependence, and competing pool-backed tasks.

The event loop may be perfectly available.

### Case three: a particular network connection cannot send more data

Inspect whether the remote peer is consuming data, whether buffers are full, and whether the application respects backpressure.

The issue may be a slow consumer rather than a slow server CPU.

### Case four: operations fail with descriptor errors

Inspect open descriptors, limits, and resource cleanup.

A process that cannot open more sockets may be suffering descriptor exhaustion rather than network packet loss.

### Case five: operations complete in the kernel but callbacks are delayed

Inspect event-loop delay, scheduling restrictions, and long-running JavaScript callbacks.

A completion can wait before its result is handled by application code.

The most useful diagnostic question is:

**At which boundary has progress stopped, and what resource or event must become available before it can continue?**

This question is more productive than vague claims that "Node.js is slow" or "the network is bad."

## 19. Resolving the incident

We can now close both production cases.

### Incident A: the synchronous read

The first problem was caused by a synchronous file operation executing on the main JavaScript thread.

The correct remediation is to remove that blocking operation from the latency-sensitive path.

For a large report, an appropriate file stream may be preferable to reading the entire report into memory.

We should verify that the new implementation does not contain other long synchronous operations.

Then measure unrelated endpoint latency and event-loop delay under the same workload.

### Incident B: pool-backed contention

The second problem involved asynchronous operations waiting behind other native work.

We must identify which tasks occupy the pool and whether the limiting resource is worker availability, CPU, memory, or storage.

Possible interventions include bounding concurrent report generation, separating expensive workload classes, reducing unnecessary work, or making a measured adjustment to pool configuration.

A larger pool might be appropriate—but only after evidence supports it.

### The shared lesson

Both incidents produced delayed application responses.

One came from blocking the event-loop thread.

The other came from finite native execution capacity.

Neither necessarily indicated a problem with TCP, HTTP, or PostgreSQL.

Both became understandable once we traced the work through the JavaScript runtime, native I/O machinery, and kernel boundaries.

That's the operating-system knowledge a senior backend engineer needs.

---

# The Oral Examination

Answer each question aloud before reading the solutions. Explain the mechanisms and how you would investigate them.

**Question 1 — Ten thousand connections**

How can a Node.js server maintain thousands of TCP connections without creating one JavaScript thread per connection?

**Question 2 — The file-descriptor illusion**

What does a file descriptor identify? Is it the file itself? What can happen when a process exhausts its descriptor limit?

**Question 3 — Blocking versus nonblocking**

A socket contains no data. What differs between a blocking read and a nonblocking read?

**Question 4 — Readable isn't complete**

The operating system reports that a TCP socket is readable. Why might the application still lack a complete HTTP request?

**Question 5 — The missed edge**

An edge-triggered event loop reads only part of the available data, then goes back to sleep. Why can this lead to an apparent stall?

**Question 6 — Two asynchronous APIs**

Why might asynchronous socket I/O require no dedicated waiting thread per connection, while an asynchronous filesystem operation occupies a native worker?

**Question 7 — The two incidents**

All endpoints become slow during one report request. In a second incident, only filesystem-dependent operations are slow while lightweight endpoints remain responsive. What different bottlenecks would you investigate?

**Question 8 — The bigger pool proposal**

Why might increasing `UV_THREADPOOL_SIZE` make performance worse?

**Question 9 — Completion versus success**

A kernel write operation reports success. What does that tell you, and what does it not establish about the remote application?

---

# Solutions and Discussion

## Solution 1 — Readiness-based concurrency

The kernel can maintain many socket states while the runtime monitors relevant readiness events.

The main JavaScript thread responds to events and executes callbacks when work is available.

The server doesn't need a dedicated JavaScript thread permanently waiting for each socket.

However, callbacks still share finite execution capacity.

## Solution 2 — A handle to kernel-managed state

A file descriptor is an integer identifying an entry in the process's descriptor table.

That entry refers to an underlying open resource relationship.

Descriptors are finite and subject to process limits.

Exhaustion can produce failures such as `EMFILE`, preventing additional opens or socket creation.

Resource lifetimes and cleanup must be managed deliberately.

## Solution 3 — Waiting versus immediate return

A blocking read may wait until data, an error, end-of-stream, or another relevant condition allows it to return.

A nonblocking read can return immediately with `EAGAIN` or `EWOULDBLOCK` when progress would require waiting.

The application can then arrange to wait for readiness before retrying.

## Solution 4 — TCP is a byte stream

Readability means the socket can make progress on a read operation under its semantics.

It doesn't mean a complete application message has arrived.

The read may return only part of an HTTP request.

The protocol parser must accumulate and interpret the bytes.

## Solution 5 — Edge-triggered discipline

An edge-triggered notification may not be repeated simply because previously reported data remains unread.

If the application fails to consume available data appropriately, it may wait for another event that never arrives.

Nonblocking I/O and reading until `EAGAIN`, with correct event-state management, are central to safe edge-triggered designs.

## Solution 6 — Different kernel and runtime paths

Network sockets support useful nonblocking readiness mechanisms.

Regular-file I/O does not generally use the same readiness path through traditional Unix facilities.

Libuv commonly delegates asynchronous filesystem work to a native thread pool, allowing the main event loop to remain responsive.

Other platform facilities exist, but actual implementation depends on runtime version and configuration.

## Solution 7 — Main-thread versus worker-pool waiting

If unrelated lightweight endpoints stall, investigate long synchronous operations or other causes of main-thread unavailability.

If those endpoints remain responsive while pool-dependent work stalls, investigate native worker-pool saturation and underlying storage or CPU contention.

Use operation timelines, event-loop measurements, and resource evidence to distinguish them.

## Solution 8 — More competition isn't more capacity

Additional native workers consume memory and may increase competition for finite storage, CPU, or other resources.

If the bottleneck is already saturated, more concurrency can increase queueing, contention, and tail latency.

Measure task demand and useful throughput before changing the pool.

## Solution 9 — Local completion is not remote application success

A successful local write may establish that the operating system accepted data according to that API's semantics.

It does not prove the peer received, parsed, processed, or durably committed the corresponding application-level operation.

Those guarantees belong to higher protocol and application layers.

---

# The Mental Model Worth Keeping

Every asynchronous operation crosses several possible boundaries:

**Initiation:** The application requests work.

**Waiting or execution:** The operation progresses through kernel facilities, native workers, or other mechanisms.

**Readiness or completion:** The relevant system reports that progress is possible or that an operation has produced a result.

**Callback execution:** The runtime delivers the result to application code when execution is available.

**Application meaning:** The application decides what the result means and whether the broader operation succeeded.

When performance becomes mysterious, locate the stage where time is accumulating.

**Asynchrony is not the absence of waiting. It is the deliberate placement and coordination of waiting so that useful work can continue elsewhere.**

# Next Lecture — Concurrency, Event Loops, and Cancellation

We now understand the mechanisms enabling asynchronous I/O.

But those mechanisms do not automatically make an application correct.

Imagine launching a thousand supplier requests simultaneously.

The kernel can manage the sockets. The runtime can deliver their results. JavaScript can coordinate their Promises.

Yet one failed supplier may trigger a retry storm.

A customer may disconnect while the application continues expensive work.

And two individually correct requests may race to update the same business state.

In CS320-L06, we'll move from operating-system mechanisms to application concurrency: task scheduling, event loops, Promise fan-out, bounded concurrency, cancellation, backpressure, and the difference between overlapping operations and correct outcomes.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Lab — Following I/O Through the Runtime

All experiments are intended for local development environments. Do not intentionally exhaust resources on production systems.

## Lab A — Observe a file descriptor

On Linux:

```bash
echo "Shell PID: $$"
ls -l /proc/$$/fd
ulimit -n
```

Observe standard input, output, and error, along with any additional descriptors opened by your shell.

The `ulimit -n` value describes the applicable open-file descriptor limit under the shell's environment.

**Question:** Why isn't a descriptor number a globally unique resource identifier?

## Lab B — Reproduce the blocking event loop

Create `blocking-server.cjs`:

```javascript
const http = require("node:http");
const fs = require("node:fs");
const { performance } = require("node:perf_hooks");

const server = http.createServer((req, res) => {
  if (req.url === "/block") {
    const start = performance.now();

    // Demonstrates synchronous CPU-bound blocking.
    while (performance.now() - start < 500) {}

    // A synchronous file operation on the same thread.
    fs.readFileSync(__filename);

    res.end("Blocking operation finished");
    return;
  }

  res.end("pong");
});

server.listen(3000, "127.0.0.1");
```

Run it:

```bash
node blocking-server.cjs
```

From another terminal, start the blocking request and then probe the lightweight endpoint:

```bash
curl -s http://127.0.0.1:3000/block > /dev/null &
sleep 0.05
time curl -s http://127.0.0.1:3000/
wait
```

The deliberate half-second busy loop makes the event-loop blockage easy to reproduce. It does not isolate filesystem latency; the synchronous file read is included to show that both kinds of synchronous work occupy the same execution lane.

**Question:** Why can the lightweight endpoint be delayed even though its own handler performs almost no work?

## Lab C — Compare asynchronous filesystem behavior

Create `async-server.cjs`:

```javascript
const http = require("node:http");
const fs = require("node:fs/promises");

const server = http.createServer(async (req, res) => {
  if (req.url === "/file") {
    const content = await fs.readFile(__filename);
    res.end(content);
    return;
  }

  res.end("pong");
});

server.listen(3001, "127.0.0.1");
```

Run it and issue multiple requests to `/file` while also probing `/`.

For a small cached file, the difference may not be especially visible.

That is expected.

The important concept is that the asynchronous filesystem API need not block the main JavaScript thread while the underlying filesystem operation progresses.

**Question:** Why doesn't a Promise returned by `readFile` prove that the operation was performed without native worker threads?

## Lab D — Demonstrate native worker-pool contention

This experiment uses asynchronous PBKDF2 operations, which commonly use libuv's native worker pool.

Create `pool-contention.cjs`:

```javascript
const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const { performance } = require("node:perf_hooks");

function pbkdf2Job() {
  return new Promise((resolve, reject) => {
    crypto.pbkdf2(
      "password",
      "salt",
      750_000,
      32,
      "sha256",
      (err, result) => err ? reject(err) : resolve(result)
    );
  });
}

async function main() {
  const started = performance.now();

  const jobs = Array.from({ length: 4 }, () => pbkdf2Job());

  const fileStarted = performance.now();

  await fs.readFile(__filename);

  console.log(
    "File read resolved after",
    Math.round(performance.now() - fileStarted),
    "ms"
  );

  await Promise.all(jobs);

  console.log(
    "All tasks finished after",
    Math.round(performance.now() - started),
    "ms"
  );
}

main().catch(console.error);
```

Try:

```bash
UV_THREADPOOL_SIZE=4 node pool-contention.cjs
UV_THREADPOOL_SIZE=8 node pool-contention.cjs
```

Actual timing varies with CPU capacity, system load, Node.js version, and runtime behavior. PBKDF2 work may be substantial on a slower machine, so reduce the iteration count if necessary.

**Question:** Why might the file operation wait longer in the first experiment, and why might a larger pool fail to improve throughput on a CPU-constrained system?

## Lab E — Observe open sockets

On Linux, while the local HTTP server is running:

```bash
ss -ltnp
```

This displays listening TCP sockets, subject to permissions.

Compare the listening socket with established connections while issuing local HTTP requests.

**Question:** Why is a listening socket different from an accepted connected socket?

## Lab F — Observe system calls

On Linux, if `strace` is available and permitted, run a disposable Node.js program under syscall tracing:

```bash
strace -f -e trace=openat,read,write,close \
  node -e 'require("node:fs").readFileSync(__filename)'
```

The short example may fail because `__filename` has a special value in code executed with `node -e`; use a real readable path instead:

```bash
strace -f -e trace=openat,read,write,close \
  node -e 'require("node:fs").readFileSync("/etc/hosts")'
```

Observe that a simple JavaScript-level operation can involve multiple native and kernel interactions.

Do not interpret every syscall made during Node.js startup as part of the file read itself.

**Question:** Why would comparing the traced operations against a tiny source file be insufficient to estimate the performance of a large report read from slow storage?

## Lab G — Production incident exercise

Consider this hypothetical evidence:

```text
After deploying the report-download endpoint:

HTTP search p95:          35 ms -> 420 ms
HTTP report p95:          80 ms -> 600 ms
Database query p95:       unchanged
Host CPU utilization:    moderate
Event-loop delay p99:     sharply elevated

After replacing synchronous file reading:

HTTP search p95:          returns to baseline
HTTP report p95:          still occasionally 550 ms
Event-loop delay p99:     near baseline

Additional evidence:
  Four expensive native pool-backed tasks overlap
  Asynchronous file reads queue behind them
```

Write two separate diagnoses.

For each, identify the bottleneck, explain the execution mechanism, name an observation that supports it, and propose a testable remediation.

Do not treat the two incidents as one generic "Node.js is slow" problem.

---

# Further Reading

Authoritative references:

1. Linux Manual Pages — `epoll(7)`  
   https://man7.org/linux/man-pages/man7/epoll.7.html

2. Linux Manual Pages — `read(2)`  
   https://man7.org/linux/man-pages/man2/read.2.html

3. Linux Manual Pages — `fcntl(2)`  
   https://man7.org/linux/man-pages/man2/fcntl.2.html

4. Linux Manual Pages — `io_uring_setup(2)`  
   https://man7.org/linux/man-pages/man2/io_uring_setup.2.html

5. Libuv Documentation — Design Overview  
   https://docs.libuv.org/en/v1.x/design.html

6. Libuv Documentation — Thread Pool Work Scheduling  
   https://docs.libuv.org/en/v1.x/threadpool.html

7. Libuv Documentation — File System Operations  
   https://docs.libuv.org/en/v1.x/fs.html

8. Node.js — Don't Block the Event Loop (or the Worker Pool)  
   https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop

9. Node.js — The Event Loop  
   https://nodejs.org/en/learn/asynchronous-work/event-loop-timers-and-nexttick

Related programme chapters:

- CS220-L06 — Managed Runtimes: Node.js, CPython, and the JVM
- CS230-L07 — The Life of a Network Connection
- CS320-L02 — CPU Scheduling, Quotas, and Contention
- CS320-L04 — Memory Pressure, Cgroups, and OOM
- CS320-L06 — Concurrency, Event Loops, and Cancellation

---

## Dense Cheatsheet — Interview Glance Card

```text
CS320-L05 — SYSTEM CALLS, FILE DESCRIPTORS, ASYNC I/O

CENTRAL MODEL
  Application -> runtime -> kernel -> I/O resource
  Readiness != completion != callback != business success

SYSTEM CALLS
  Controlled user/kernel transition
  High-level API != necessarily one syscall
  Syscall overhead != underlying I/O latency
  File and socket operations invoke kernel facilities

FILE DESCRIPTORS
  fd = per-process integer handle
  Descriptor table entry -> open-file description/resource
  dup'd descriptors may share offsets/status flags
  close releases descriptor; number may be reused
  Leaks / high concurrency can hit EMFILE
  Descriptor number != global persistent resource identity

BLOCKING
  Caller may sleep waiting for operation
  Waiting thread usually need not burn CPU
  Blocking main JS event-loop thread delays other callbacks
  Blocking in dedicated worker has different consequences

NONBLOCKING
  Operation unable to proceed -> EAGAIN / EWOULDBLOCK
  Read/write may make partial progress
  TCP = byte stream, not message boundaries
  read = 0 at normal stream EOF; not equivalent to EAGAIN

READINESS
  Resource can make progress on relevant operation
  Does NOT guarantee complete HTTP message
  Does NOT guarantee future read/write remains ready
  Select/poll: traditional readiness monitoring

EPOLL
  Linux persistent interest set for supported descriptors
  epoll_create1 -> epoll_ctl -> epoll_wait
  Level-triggered: readiness may persist/reappear
  Edge-triggered: handle transition-driven notifications
  ET safe pattern: nonblocking, drain until EAGAIN
  Ordinary regular files generally not epoll-monitorable
  epoll EPERM possible for unsupported descriptor types

PLATFORM MECHANISMS
  Linux       epoll; io_uring for supported operations
  macOS/BSD   kqueue
  Windows     IOCP and other platform facilities
  Similar goals; different semantics

IO_URING
  Submission queue -> kernel work -> completion queue
  Reduces some syscall/coordination costs
  Not automatically zero-copy
  Not guaranteed zero-thread for every operation
  Actual Node/libuv use is version/config-dependent

LIBUV
  Cross-platform event-loop and I/O infrastructure
  Socket network path: readiness + nonblocking I/O
  Filesystem path: commonly native worker pool
  Async JS API does not reveal native implementation
  Threadpool default traditionally 4, configurable
  UV_THREADPOOL_SIZE != total threads in process
  Native pool != JavaScript worker_threads
  Pool shared by fs, some DNS, crypto, zlib operations
  dns.lookup() and dns.resolve() differ in native paths

INCIDENT A — MAIN THREAD BLOCKED
  fs.readFileSync in HTTP handler
  Event-loop thread occupied
  Socket packets may arrive; callbacks wait
  Unrelated endpoints suffer
  Event-loop delay elevated
  Fix blocking operation, verify system-wide latency

INCIDENT B — NATIVE POOL SATURATED
  Asynchronous API returns Promise
  Pool-backed task queued behind expensive tasks
  Main event loop remains available
  Unrelated lightweight endpoints may remain healthy
  Inspect pool-dependent work, storage/CPU, concurrency
  More workers != automatically more capacity

TIMING BOUNDARIES
  Request initiated
  Resource waits / performs native work
  Readiness or completion reported
  JS callback/Promise continuation executes
  Application validates and commits result

BACKPRESSURE
  Socket writable != infinite writable capacity
  Partial writes and buffering require lifecycle handling
  Stream.write false -> respect pressure contract
  Streaming can limit memory for suitable file transfers
  Async I/O != unbounded buffering allowed

CANCELLATION
  Abort request != instantaneous guaranteed kernel undo
  Promise settled != all lower-level side effects reversed
  Timeouts do not prove remote work never happened
  Resource cleanup and operation lifetime matter

FORENSICS
  1. Which endpoints are delayed?
  2. Is main event loop occupied/delayed?
  3. Which operations use native worker pool?
  4. Is actual storage/network resource slow?
  5. Are descriptors/buffers/queues bounded?
  6. Distinguish waiting from completion delivery
  7. Change one mechanism; compare before/after

SENIOR INTERVIEW ANSWER
  "I'd identify which execution boundary is accumulating time.
   Network readiness, native worker execution, event-loop callback
   delivery and application completion are different mechanisms.
   I'd measure them separately before changing concurrency or
   assuming the network is at fault."

MENTAL MODEL
  Asynchrony means waiting is coordinated differently.
  It does not mean the waiting vanished.
```
