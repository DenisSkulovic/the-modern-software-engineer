---
id: CS320-L06
course: CS320
title: "Concurrency, Event Loops, and Cancellation"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: [CS101-S09]
prev: CS320-L05
next: CS320-L07
---




# CS320 — Operating Systems and Concurrency

## Lecture 06: Concurrency, Event Loops, and Cancellation

*One JavaScript thread. Two customers. One remaining hotel room. Both receive confirmations. Meanwhile, a supposedly faster supplier integration overwhelms its dependencies, and a canceled search continues consuming resources. Welcome to concurrency: where every operation can be individually reasonable and the system can still be catastrophically wrong.*

# Part I — Intuition

## The picture to carry in your head

Imagine a restaurant with one exceptionally capable waiter.

He takes orders, sends instructions to the kitchen, serves customers, handles payments, and coordinates deliveries.

He doesn't cook every meal himself. Once he submits an order to the kitchen, he can serve another table while the food is being prepared.

He manages many activities whose progress overlaps.

That's **concurrency**.

Now imagine hiring a second waiter. They can physically serve different tables at the same instant.

That's **parallelism**.

These concepts are related, but they aren't identical.

One waiter can coordinate many concurrent orders. Several waiters can execute work in parallel. And neither arrangement guarantees that the restaurant operates correctly.

Suppose only one portion of lobster remains.

Customer A asks for it.

The waiter checks the inventory board. One portion remains.

He sends a question to the kitchen, then turns to another customer while waiting.

Customer B also asks for lobster.

The waiter checks the board again. It still says one portion remains.

He tells B the lobster is available.

The kitchen answers A's question. The waiter confirms A's order and subtracts one portion from inventory.

Then he confirms B's order and subtracts another.

Inventory now reads minus one.

There was only one waiter.

Nobody performed two inventory updates at precisely the same instant.

Yet the restaurant sold the same remaining portion twice.

How?

Because the waiter allowed another operation to progress between checking the inventory and updating it.

**Concurrency creates opportunities for other operations to change the world between your observations and your decisions.**

That is the central problem of this lecture.

## 1. `await` creates a place where the world can change

Our Node.js booking service has one remaining hotel room.

Two customers submit reservation requests.

Each request checks availability, waits for some asynchronous work, and then attempts to confirm the reservation.

The first request observes that one room remains.

But while it waits, the second request can also observe the same availability.

Both then proceed using information that was true when observed but no longer sufficient to justify their decisions.

This is a race condition.

A race occurs when an outcome depends on the relative ordering of operations, and the system hasn't adequately constrained the order required for correctness.

A single JavaScript execution thread does not eliminate this problem.

Within one thread, ordinary synchronous instructions execute sequentially. But asynchronous operations can suspend and resume at different times, allowing multiple logical transactions to interleave.

The dangerous boundary is often not a literal simultaneous write.

It is the gap between a check and an action that depends on that check.

## 2. The event loop is a dispatcher, not a second processor

In CS320-L05, we examined how operating-system facilities make nonblocking I/O possible.

Now consider what happens when a network response becomes available.

The runtime receives an event or operation result.

Eventually, a JavaScript callback can execute.

That callback may settle a Promise.

The Promise may cause an awaiting function to resume.

The event loop coordinates opportunities for these pieces of JavaScript work to run.

But it doesn't make one JavaScript thread execute several ordinary callbacks simultaneously.

An `async` function also doesn't automatically run in a background thread.

It begins executing synchronously when called. When it reaches an `await`, its continuation is suspended until the awaited value is available and the runtime schedules the continuation.

Other work can progress during that suspension.

The result is concurrency without necessarily having parallel JavaScript execution.

And because suspended functions resume later, any facts they observed before suspension may need to be checked again.

## 3. The supplier integration that became too fast

Our booking platform also communicates with external suppliers.

Suppose one hotel-search request must contact twenty independent supplier services.

Calling them sequentially might take several seconds.

So the developer launches them concurrently.

Good idea.

Now imagine increasing the number of suppliers from twenty to two hundred.

Or serving a thousand customer searches at the same time.

The number of in-flight operations becomes enormous.

The external services impose connection limits.

The database pool becomes saturated.

Requests wait in increasingly large queues.

Memory use rises because each pending operation retains state.

Some suppliers begin rejecting requests.

The application retries them.

Now the system performs even more work.

The problem wasn't that concurrency was inherently wrong.

It was that the application allowed more concurrent work than its dependencies could usefully handle.

A fast way to start work is not necessarily a fast way to finish it.

We need **bounded concurrency**: the deliberate restriction of how many operations can be active simultaneously.

## 4. The cancel button that doesn't cancel

Now a customer starts a hotel search.

The backend launches fifty supplier requests.

After two seconds, the customer changes the destination.

The frontend cancels the original request and starts another.

What happens to the first fifty supplier operations?

Not necessarily anything.

The client may stop waiting for the response.

The server may still be working.

The supplier requests may still be in flight.

Some may eventually complete and update caches or trigger other effects.

Cancellation is not automatically retroactive.

A JavaScript Promise represents a future result. Rejecting one Promise or abandoning its result does not inherently terminate the operation it represents.

To stop work safely, the cancellation request must reach components that support it.

Even then, some operations may already have committed side effects.

Cancellation is a **lifecycle protocol**, not a magical undo command.

## 5. Four distinct concurrency problems

The restaurant and booking examples expose four separate questions.

**Correctness:** Can overlapping operations violate an invariant, such as selling more rooms than exist?

**Capacity:** Can the system accept more concurrent work than its resources can support?

**Lifetime:** Who owns an operation, and what happens when its result is no longer needed?

**Completion:** How does the application know that all necessary work has finished, failed, or been safely abandoned?

These questions need different mechanisms.

A database transaction can protect an inventory invariant, but it doesn't necessarily limit concurrent supplier requests.

A semaphore can limit the number of active requests, but it doesn't make a distributed reservation transaction correct.

An AbortSignal can request cancellation, but it doesn't guarantee that a remote payment was reversed.

And `Promise.all` can coordinate results, but it doesn't automatically solve the other three problems.

## Three questions before the Deep Dive

1. Why can a single JavaScript thread produce a race condition even though two JavaScript callbacks aren't executing simultaneously on that thread?
2. Why can increasing the number of concurrent supplier requests reduce useful throughput?
3. What is the difference between no longer wanting a result and knowing that the underlying operation has stopped?

The picture to retain is a single dispatcher coordinating overlapping work. Correctness depends on controlling which operations may overlap, what state they may change, and who remains responsible for their completion.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The last room was sold twice

Our booking platform has a simplified inventory record.

One hotel has one room remaining.

Two customers submit reservation requests nearly simultaneously.

Each request follows the same procedure.

First, read the available-room count.

Second, determine whether a room can be sold.

Third, perform an asynchronous operation.

Fourth, decrement the count and confirm the reservation.

Each function looks reasonable in isolation.

The bug appears when their executions overlap.

Anna's request begins and reads an available count of one.

Anna reaches an `await`.

Her function suspends.

David's request begins and reads the same count of one.

David also suspends.

Anna's continuation resumes, decrements the count, and confirms her reservation.

David's continuation resumes, decrements again, and confirms his.

The count becomes minus one.

This is not a data race in the precise shared-memory sense we'll study in L07, where unsynchronized threads access memory under a language's concurrency memory model.

Here, the JavaScript operations can be perfectly sequential at the instruction level.

The race is **logical**: two operations observe state and make decisions based on a relationship that wasn't preserved between observation and update.

The business invariant is that confirmed reservations must not exceed available inventory.

The implementation failed to enforce it.

### Why removing `await` sometimes seems to fix the bug

Suppose the availability check and decrement happen together in one uninterrupted synchronous JavaScript execution segment.

Within a single Node.js event-loop thread, another ordinary JavaScript callback cannot interleave between those statements.

For a purely process-local demonstration, this can prevent the particular race.

But our actual booking platform runs several application replicas.

Each process has separate memory.

Even if each replica updates its local counter synchronously, they do not share one authoritative inventory state.

A process-local fix cannot enforce a distributed business invariant.

The correctness boundary must include all operations that can modify authoritative inventory.

That usually means an appropriate database transaction, atomic conditional update, locking strategy, or another durable coordination mechanism.

We'll return to this shortly.

## 2. Concurrency versus parallelism, precisely

Let's separate the concepts.

Concurrency means multiple activities can be in progress during overlapping periods, even if their individual instructions execute at different times.

Parallelism means work actually executes simultaneously on different execution resources.

A single-threaded event loop can coordinate concurrent I/O operations.

Several worker threads can execute CPU-intensive calculations in parallel on a multicore machine.

A distributed system can have many independently executing processes, each with its own concurrency mechanisms.

But increasing parallel execution capacity doesn't automatically fix concurrency correctness.

Two processes can run in parallel and still conflict over one database row.

One process can execute JavaScript sequentially and still interleave logical operations across asynchronous waits.

The key question is not merely how many processors are involved.

It is **which operations can overlap in time, which state they observe, and which invariants must remain true regardless of ordering**.

### Why asynchronous work can overlap efficiently

A network request may spend most of its lifetime waiting for a remote service.

The JavaScript thread doesn't need to execute instructions continuously during that wait.

The runtime and kernel manage the underlying I/O.

Meanwhile, the event loop can execute other callbacks.

This makes concurrency particularly valuable for I/O-bound services.

But CPU-intensive work behaves differently.

If a callback performs a large synchronous calculation on the main JavaScript thread, other ordinary callbacks must wait.

An `async` keyword doesn't change the amount of processor work required.

And wrapping synchronous computation inside a Promise doesn't automatically move that computation onto another thread.

For actual parallel JavaScript computation in Node.js, we may use worker threads or separate processes.

That choice introduces execution, communication, and resource-management costs of its own.

## 3. How the event loop decides when code executes

Now examine the event loop from the application's perspective.

JavaScript begins by executing the current call stack.

Functions run synchronously until they return, throw, or suspend through a mechanism such as `await`.

The runtime also maintains queues and scheduling mechanisms for deferred work.

Some callbacks are associated with I/O events.

Others are associated with timers.

Some are associated with `setImmediate`.

Promise reactions and async-function continuations run through microtask processing.

Node.js also has its own `process.nextTick` scheduling mechanism.

These mechanisms don't all have identical priority or timing rules.

### Timers are eligibility thresholds

Suppose we schedule a timer for ten milliseconds.

That does not mean its callback will execute exactly ten milliseconds later.

It means the callback becomes eligible after the relevant timer threshold.

If the event-loop thread is busy, the callback may execute later.

If the operating system delays the thread because of CPU scheduling or cgroup throttling, it may execute later.

If substantial higher-priority continuation work remains, it may execute later.

A timer is not an independent real-time thread.

It is a scheduling request within the runtime's execution model.

### Node.js event-loop phases

Node.js organizes important categories of callback work into phases, including timer callbacks, pending callbacks, poll-related I/O processing, check-phase callbacks, and close callbacks.

The poll phase is particularly relevant to I/O processing.

The check phase handles `setImmediate` callbacks.

Timer callbacks execute when their timing conditions and the event-loop's scheduling rules permit.

The exact phase ordering and interactions depend on runtime version and execution context.

For instance, starting with Node.js 20 and libuv 1.45, timer handling changed to run after the poll phase in the normal loop iteration, affecting some timing relationships involving `setImmediate`.

Don't memorize an old event-loop diagram as though it were a timeless law of nature.

The durable model is that **callbacks become eligible through different mechanisms, and eligibility does not guarantee immediate execution**.

### An important ordering trap

At top level, scheduling `setTimeout(fn, 0)` and `setImmediate(fn)` does not give a universally fixed order between those two callbacks.

Within an appropriate I/O callback, `setImmediate` commonly executes before a newly scheduled zero-delay timer.

This matters when debugging subtle ordering problems.

But if your business correctness depends on whether a timer or immediate callback happens first, the design probably needs a more explicit synchronization contract.

A scheduler's incidental ordering is not a substitute for an invariant.

## 4. Microtasks: small continuations with large consequences

Promises introduce another scheduling layer.

When a Promise settles, its registered reactions are scheduled for asynchronous execution.

In JavaScript, Promise reactions are processed as microtasks.

This allows a function to suspend at `await` and later resume after the awaited result is available.

Consider an async function that logs a message, awaits an already-fulfilled Promise, and logs another message.

The first log executes synchronously.

The second executes later as a continuation.

Even though the Promise was already fulfilled, `await` still creates an asynchronous continuation boundary.

That is important.

The suspension isn't necessarily caused by network latency or kernel I/O.

It's part of JavaScript's execution semantics.

### Microtasks are not ordinary timers

After the current JavaScript execution yields at an appropriate checkpoint, Promise microtasks are processed before the runtime proceeds to other event-loop work.

That gives Promise continuations relatively prompt execution.

But there is a danger.

If each microtask schedules another microtask, the queue can keep replenishing itself.

The runtime may spend an extended period executing microtasks before returning to I/O-related callbacks or timers.

This is **microtask starvation**.

The program is doing work.

The main thread may be busy.

Yet network responses and timer callbacks can experience substantial delay.

The same broad problem occurs with excessive recursive scheduling through Node.js `process.nextTick`.

### `process.nextTick` is Node-specific

In ordinary CommonJS execution, Node.js generally processes `process.nextTick` callbacks before Promise microtasks at the relevant checkpoint.

But there are context-dependent details, including differences when an ES module's top-level evaluation itself runs within microtask processing.

So don't teach a universal ordering rule without specifying the context.

For a senior engineering interview, the most important principle is not remembering every exotic combination.

It's recognizing that callbacks, next-tick callbacks, and Promise continuations have different scheduling semantics, and aggressively replenishing these queues can starve other work.

### Why `await Promise.resolve()` isn't a reliable fairness mechanism

A developer notices a long-running computation and inserts occasional `await Promise.resolve()` calls.

They hope this allows the server to process incoming I/O.

But resuming through Promise microtasks does not necessarily allow the event loop to return to its I/O phases.

A repeatedly replenished microtask chain can still starve those phases.

If genuine cooperative yielding to the event loop is required, use an appropriate scheduling mechanism, such as a suitable immediate callback or timers-based yielding API, while recognizing that it adds overhead.

For substantial CPU-intensive work, a worker thread or separate process may be more appropriate.

Yielding changes scheduling opportunities.

It doesn't create more computing capacity.

## 5. The race is between observations and state transitions

Return to the double-booking incident.

The bug wasn't that the JavaScript engine failed to execute a decrement correctly.

It was that availability was checked separately from the authoritative state transition.

The desired operation is:

Reserve one room **only if** one remains available, and make the availability decision and reservation update consistent under concurrent requests.

That is a business invariant.

The application must enforce it over the appropriate state boundary.

### Atomicity at the database boundary

Suppose our inventory model has a row containing an available-room count.

PostgreSQL can perform a conditional decrement as a single statement:

Update the count only where it is greater than zero, and return the updated row.

Concurrent transactions updating the same row are coordinated according to the database's locking and isolation semantics.

Only an operation that actually updates a qualifying row should count as acquiring the remaining inventory.

That's far stronger than reading the count into JavaScript, waiting, and then writing a new value.

However, actual hotel reservations may involve multiple dates, room types, pricing rules, reservation records, and payment workflows.

One conditional counter update may not protect every required invariant.

A real design needs a transaction or coordination strategy covering the complete authoritative state transition.

### What a local mutex can and cannot do

A mutex enforces mutual exclusion among participants that actually share and obey that mutex.

Inside one application process, a mutex may protect a process-local critical section.

But if there are five Node.js replicas, each with its own mutex, those locks do not automatically coordinate across replicas.

All five can independently believe they've acquired exclusive local access.

A distributed business invariant needs coordination at the durable shared boundary.

Usually, that means the database or another explicitly designed coordination service.

The lesson is to choose the **scope of synchronization** to match the scope of the invariant.

## 6. `Promise.all`: useful coordination, not unlimited capacity

Now turn to our supplier integration.

One hotel search needs results from several independent providers.

A sequential implementation waits for Supplier A, then B, then C.

If each takes approximately two hundred milliseconds, the total waiting time may approach six hundred milliseconds.

Starting the independent requests concurrently can reduce elapsed time substantially.

`Promise.all` is useful for this.

It returns a Promise that fulfills after all input Promises fulfill, preserving results in input order.

If any input Promise rejects, the aggregate rejects with that reason.

But the behavior has two important implications.

### Fail-fast is not cancel-all

Suppose the supplier requests have already started.

Supplier A rejects after one hundred milliseconds.

The Promise returned by `Promise.all` rejects.

That does not automatically cancel requests B and C.

They can continue using sockets, memory, connection-pool capacity, and other resources.

They may produce side effects.

The aggregate Promise settling does not mean the entire group of underlying operations has stopped.

This is especially dangerous when code assumes a failed batch has been rolled back.

A Promise aggregation failure is not a transaction rollback.

### `allSettled` changes observation, not execution

`Promise.allSettled` waits until every input Promise has fulfilled or rejected, then reports their outcomes.

That is useful when we need to account for all results.

But it doesn't automatically limit concurrency or cancel operations either.

It changes how we wait for and observe completion.

It does not change the resource capacity available to the underlying tasks.

### Eagerly creating thousands of promises

Suppose we call an asynchronous supplier function ten thousand times and immediately pass all the returned Promises into `Promise.all`.

Those function calls may initiate work immediately.

The event loop doesn't wait until the aggregate is awaited to start the work.

We have potentially created ten thousand in-flight operations before applying any control.

That can overwhelm connections, memory, rate limits, or downstream services.

`Promise.all` is not a concurrency limiter.

To enforce a limit, the application must control when underlying operations are started.

## 7. Bounded concurrency: permits before starting work

Imagine we decide that each Node.js replica may have no more than eight active supplier requests at one time.

A semaphore is one mechanism for expressing that constraint.

It maintains a set of permits.

Before starting an operation, a task acquires a permit.

If no permits are available, it waits.

When the operation finishes, the permit is released.

A properly implemented semaphore ensures that no more than the configured number of participants hold permits simultaneously.

### Why release belongs in `finally`

Suppose an operation acquires a permit and then throws an exception.

If the program forgets to release the permit, available capacity decreases permanently.

After enough failures, the system may stop admitting new work.

That's a resource leak, even if no heap object grows without bound.

The operation's permit should be released through a guaranteed cleanup path, typically a `finally` block.

Cancellation and timeouts make that discipline even more important.

A request canceled while waiting for a permit should not accidentally consume one.

A request canceled after acquiring a permit should release it only when the protected work's lifecycle actually permits release.

If the underlying operation continues after the caller abandons it, prematurely releasing the permit can allow more real work than intended.

### The scope of the limit

Now suppose we have ten replicas.

Each permits eight simultaneous supplier operations.

Our nominal application-wide maximum may be eighty, not eight.

And autoscaling from ten replicas to twenty can double the potential concurrency.

This is why a process-local semaphore is not automatically a global dependency budget.

A complete design may need global admission control, distributed coordination, upstream rate limits, or capacity planning based on the total number of replicas.

The appropriate mechanism depends on what resource we're protecting.

The core principle is that **a concurrency limit is meaningful only when its scope matches the capacity constraint**.

## 8. Concurrency limits, rate limits, and queue limits

These three controls are frequently confused.

A concurrency limit bounds the number of operations active at once.

A rate limit bounds the number of operations admitted over time.

A queue limit bounds how much waiting work we are willing to retain.

They are not interchangeable.

### Concurrency is not request rate

Imagine allowing ten active requests at once.

If each finishes in ten milliseconds, the system might complete a large number of requests per second.

If each takes ten seconds, the same concurrency limit permits a much lower throughput.

A rate limit of one hundred requests per second describes a different constraint.

A third-party API may impose both a request-rate limit and an in-flight request limit.

The application must respect whichever constraints apply.

### A bounded active set can still have an unbounded waiting room

Suppose our semaphore permits eight active operations.

Incoming requests continue arriving faster than the eight operations can finish.

The semaphore's waiting queue grows.

Each queued request may retain closures, arguments, buffers, timeouts, and application state.

The active operation count remains eight.

Memory consumption can still grow indefinitely.

Therefore, limiting active work without limiting waiting work is not a complete overload strategy.

A robust service needs an admission policy.

Perhaps the queue has a maximum capacity.

Perhaps requests expire while waiting.

Perhaps low-priority work is rejected under pressure.

Perhaps the API returns a retryable overload response.

A system that can accept an infinite backlog isn't truly capacity-controlled.

### Little's Law as a diagnostic tool

A useful relationship from queueing theory is Little's Law: average work in the system equals average throughput times average time in the system, under the relevant stable-system assumptions.

If a service completes fifty requests per second and the average operation spends two seconds in the system, the average number of operations present is approximately one hundred.

If latency increases while throughput remains similar, in-flight work tends to grow.

That is why slow dependencies can cause memory pressure even when incoming request rates haven't increased.

The growing number of pending tasks is itself a resource demand.

We'll examine the deeper quantitative treatment in performance engineering. For now, remember the causal relationship: **longer lifetimes create larger populations of unfinished work**.

## 9. Backpressure: when the consumer must influence the producer

Our supplier aggregator produces results.

Other components process and store them.

What happens if results arrive faster than the next stage can handle?

Without control, the producer keeps generating work.

Buffers grow.

Queues grow.

Memory pressure rises.

Eventually, something fails.

**Backpressure** means downstream capacity influences how quickly upstream work is produced or admitted.

It's broader than one particular Node.js stream API.

At the stream level, a writable stream can signal that its buffering threshold has been reached.

The producer should wait for the appropriate opportunity to resume instead of pushing data without bound.

At the task level, a worker pool can restrict active operations.

At the service boundary, an overloaded backend may reject requests or ask callers to retry later.

At the queue level, consumers may control how many messages are delivered or remain unacknowledged.

These mechanisms exist at different layers, but their purpose is similar.

Don't allow upstream demand to silently exceed downstream capacity.

### Why buffering is not a permanent solution

Buffers absorb temporary mismatches between production and consumption.

They're extremely useful.

But buffering doesn't create throughput.

If the producer continuously generates one thousand units per second and the consumer can process only five hundred, the backlog increases by roughly five hundred units per second until some limit is reached.

A larger buffer postpones the failure.

It doesn't remove the capacity mismatch.

The correct intervention may be to reduce admission, increase useful processing capacity, shed low-priority work, or change the workload.

This is why overload handling is part of correctness and availability, not merely performance tuning.

## 10. Cancellation: who owns unfinished work?

Now return to the customer who cancels a hotel search.

The frontend no longer needs the original result.

What happens to the supplier operations?

The answer depends on whether the application propagates the cancellation request.

Node.js and modern JavaScript APIs commonly use `AbortController` and `AbortSignal`.

A controller can signal that an operation should be aborted.

APIs that support a signal can observe it and react according to their own contracts.

For example, a fetch request can accept an AbortSignal.

But the signal doesn't automatically cancel every operation in the program.

The application must pass it through the relevant layers.

### Cancellation must follow ownership

Imagine a request handler starts fifty supplier operations.

The handler owns the customer-facing search.

If the client disconnects or the request deadline expires, the handler may determine that its work is no longer useful.

But the supplier operations still exist.

A well-designed operation tree propagates cancellation from the parent request to appropriate child operations.

The children should either stop safely, complete and be accounted for, or continue under explicitly transferred ownership.

Unmanaged background work shouldn't silently outlive its purpose.

### Combining cancellation conditions

A search might be canceled for several reasons.

The customer disconnects.

The request exceeds its deadline.

The server begins shutdown.

A higher-level operation decides the search is no longer useful.

In supported Node.js versions, `AbortSignal.timeout` provides a timeout-driven signal.

`AbortSignal.any` can combine multiple signals so the combined signal aborts when one of them does.

That is useful for expressing several cancellation conditions without inventing complicated ad hoc timer logic.

But the resulting signal still needs to reach APIs that understand it.

### What if an operation cannot be canceled?

Some operations don't support cancellation.

Others have already passed the point where stopping is safe.

The application may need to allow them to finish, then discard their result or reconcile the outcome.

That is better than pretending they disappeared.

A robust system explicitly distinguishes work that has stopped from work that is merely no longer awaited.

## 11. Timeouts do not establish remote failure

Cancellation becomes particularly dangerous when operations have side effects.

Imagine our backend sends a payment request to a provider.

The local request times out after three seconds.

Did the payment fail?

We don't know.

The provider might have received and processed the payment but failed to return a response before the deadline.

The local timeout tells us that our waiting policy expired.

It does not establish the remote operation's final state.

Retrying with an entirely new business identity can accidentally create a duplicate payment.

The correct system may need an idempotency key, a durable operation record, provider status lookup, or reconciliation workflow.

This is not an operating-system issue alone.

It's a distributed correctness problem.

But the lesson follows directly from concurrency and cancellation semantics.

**Stopping your wait is not proof that the external operation stopped.**

### Cancellation cannot roll back history

Even a successfully propagated cancellation request cannot undo effects that already occurred.

A database transaction may already have committed.

A message may already have been published.

A payment provider may already have charged the customer.

Cancellation must therefore be combined with appropriate business-state design.

We shouldn't confuse a clean cancellation API with a globally atomic cancellation guarantee.

## 12. Structured concurrency: tasks should have owners

One conceptual improvement is to treat related operations as a group with an explicit lifetime.

Imagine a parent hotel-search operation.

It starts several supplier requests.

It may establish a shared deadline and cancellation policy.

It knows which children are active.

Before the parent considers itself fully finished, it accounts for their outcomes according to the application's requirements.

This is the general idea behind **structured concurrency**.

Different languages and frameworks provide different implementations.

Python has task groups in `asyncio`.

Java has structured-concurrency facilities whose exact availability and status depend on the platform version.

JavaScript's built-in Promises don't automatically enforce the same task-tree lifetime discipline.

A Node.js application may need explicit orchestration, supporting libraries, or carefully designed abstractions.

### Why structure matters

Without clear ownership, a request handler may initiate work and then return while its child operations continue independently.

That can cause several problems.

Errors may be lost.

Cancellation may not propagate.

Resources may outlive the request.

A retry may begin while the original operation is still active.

The system may declare success without accounting for relevant child failures.

Structured task ownership makes these questions explicit.

Who started the work?

Who can cancel it?

Who waits for it?

Who handles its failure?

When may the parent release its resources?

The design becomes easier to reason about when those answers are deliberate.

### Not everything must die with its HTTP request

There is an important exception.

Sometimes the request starts durable background work that should continue after the client disconnects.

For example, a customer may submit a report-generation job.

The server records the job durably and returns an accepted response.

A background worker processes the job independently.

The HTTP request no longer owns the job's entire lifetime.

Ownership has been transferred to the durable workflow.

That's legitimate.

The problem isn't work outliving a request.

The problem is work outliving its owner accidentally, without explicit lifecycle or recovery semantics.

## 13. Testing concurrency: control the interleaving

Concurrency bugs can be difficult to reproduce.

They depend on timing.

A test that launches two requests simultaneously may pass a thousand times, then fail unexpectedly in production.

But we can do better than hoping to get lucky.

For our double-booking example, the crucial event is that both requests observe availability before either updates it.

We can deliberately construct that ordering.

A controlled test can pause both operations after their checks, then release their continuations.

If both confirm the last room, the invariant is broken.

This is far more informative than running thousands of uncontrolled requests and hoping the dangerous timing occurs.

### Test invariants, not just responses

A test might assert that both HTTP requests returned status 200.

That could pass even when the system is catastrophically wrong.

The important assertion is that confirmed reservations do not exceed inventory.

For a database-backed booking workflow, the test should inspect authoritative state after the concurrent operations.

It should verify that at most one reservation acquired the final unit of inventory.

This principle generalizes.

For payment workflows, ensure an operation isn't charged twice.

For inventory systems, ensure stock doesn't become negative.

For queue consumers, ensure retries don't violate business invariants.

Concurrency testing should focus on **properties that remain true under every permitted interleaving**.

## 14. The production incident, reconstructed

We can now return to our three failures.

### Failure A: the double booking

The application checked inventory and updated it in separate steps.

An asynchronous suspension allowed another logical operation to make a decision based on the same old state.

The remedy is to enforce the invariant within the appropriate authoritative state boundary.

For a simple inventory counter, that may be a conditional database update.

For a more complex reservation, it may require transactional coordination across several records.

The fix isn't to add random delays or hope JavaScript requests arrive in a convenient order.

### Failure B: the supplier overload

The service started too many external operations without respecting downstream capacity.

The initial performance gain from concurrency disappeared under contention, retries, queue growth, and resource limits.

The remedy is to introduce appropriate concurrency and rate controls, bounded waiting, and overload behavior.

But the limits must be scoped correctly across replicas.

A process-local limit can be useful without being sufficient.

### Failure C: the canceled search

The frontend stopped waiting, but the backend and supplier operations continued.

Cancellation wasn't propagated or owned through the operation tree.

The remedy is to establish an explicit lifetime contract.

Supported operations should receive cancellation signals, unnecessary work should stop safely, and operations with possible side effects must be reconciled rather than assumed undone.

### The common cause

These incidents look different.

One violates an inventory invariant.

One overloads dependencies.

One wastes resources after the customer has left.

But they share a deeper problem.

The application allowed work to progress without adequately defining the constraints on that progress.

Correct concurrency requires rules governing **state, capacity, and lifetime**.

Without those rules, a system can be highly asynchronous and remarkably unreliable.

---

# The Oral Examination

Answer each question aloud before reading the solutions. Aim for an explanation you could give in a senior backend interview.

**Question 1 — The single-threaded race**

How can two Node.js request handlers both reserve the last available room when ordinary JavaScript executes on one main thread?

**Question 2 — The microtask trap**

Why might repeatedly awaiting `Promise.resolve()` inside a long computation fail to keep network callbacks responsive?

**Question 3 — `Promise.all` and cancellation**

Five supplier requests are started concurrently. One rejects immediately. What happens to the aggregate Promise, and what happens to the other four operations?

**Question 4 — The eight-permit semaphore**

A service has ten replicas, each allowing eight concurrent supplier calls. Can we conclude the entire deployment has a maximum of eight supplier calls? What other controls might be needed?

**Question 5 — Bounded concurrency, unbounded memory**

A semaphore limits active operations to ten, yet memory consumption grows continually under load. Explain a plausible cause.

**Question 6 — The cancel button**

A customer cancels a search, and the frontend aborts the HTTP request. Why might the backend still be communicating with suppliers?

**Question 7 — Timeout versus remote outcome**

A payment request times out. Can we safely infer that the provider did not charge the customer? What does the application need to do next?

**Question 8 — Concurrency versus parallelism**

Would adding Node.js worker threads automatically fix an overselling bug in PostgreSQL? Why or why not?

**Question 9 — Designing the investigation**

After increasing supplier concurrency, average response time improves slightly, but p99 latency, memory use, and rate-limit errors all rise. How would you investigate and correct the system?

---

# Solutions and Discussion

## Solution 1 — Interleaving across asynchronous suspension

One handler can read inventory, suspend at `await`, and allow another handler to observe the same inventory before the first updates it.

The JavaScript instructions are sequential, but the logical operations interleave.

Correctness requires enforcing the inventory invariant at the authoritative shared-state boundary, commonly through an appropriate database operation or transaction.

## Solution 2 — Microtask starvation

Awaiting an already-fulfilled Promise schedules a continuation through microtask processing.

A chain that continually replenishes the microtask queue may prevent the event loop from returning promptly to I/O and timer work.

Genuine cooperative yielding requires an appropriate event-loop scheduling mechanism, while CPU-heavy computation may belong in a worker thread or separate process.

## Solution 3 — Fail-fast aggregation isn't cancellation

The Promise returned by `Promise.all` rejects when an input rejects.

The other already-started operations aren't automatically canceled.

They may continue consuming resources or producing side effects.

Explicit cancellation, ownership, and cleanup are separate responsibilities.

## Solution 4 — The limit is process-local

Each replica can permit eight active operations, so ten replicas can collectively initiate as many as eighty under the simplified model.

A global downstream budget may require coordination, distributed admission control, rate limiting, or carefully designed capacity allocation across replicas.

The limit's scope must match the resource it protects.

## Solution 5 — The waiting queue is unbounded

A semaphore may restrict active operations while allowing arbitrarily many waiting requests.

Those pending requests retain memory and other resources.

The system needs bounded queueing, deadlines, rejection, or another explicit admission policy.

A limit on active work is not automatically a limit on total retained work.

## Solution 6 — Cancellation wasn't propagated

Canceling the frontend's wait doesn't necessarily stop server-side work.

Even if the HTTP connection closes, the backend may continue executing requests unless it detects the condition and propagates cancellation.

Some downstream operations may not support cancellation or may already have completed side effects.

## Solution 7 — Remote outcome is uncertain

A timeout means the local waiting deadline expired.

The provider might have processed the charge but failed to return a timely response.

Use a durable operation identity, idempotency support, status lookup, or reconciliation according to the provider's contract.

Do not blindly retry an ambiguous payment as a new operation.

## Solution 8 — Parallelism doesn't enforce database correctness

Worker threads provide additional execution contexts.

They don't automatically coordinate authoritative database updates.

The overselling invariant must be protected through an appropriate shared-state mechanism regardless of whether the application uses one thread, many threads, or several processes.

## Solution 9 — Separate useful capacity from excessive in-flight work

Measure actual supplier latency, request rate, active concurrency, pending queues, connection-pool utilization, retries, and error rates.

Test lower concurrency levels and observe useful throughput and tail latency.

Introduce appropriate per-replica and global limits, bounded waiting, and retry policies.

The objective is sustainable successful throughput, not the largest possible number of outstanding Promises.

---

# The Mental Model Worth Keeping

Every concurrent operation creates three responsibilities.

**State:** What must remain true regardless of how operations interleave?

**Capacity:** How much overlapping work can the system and its dependencies actually support?

**Lifetime:** Who owns the work, who can cancel it, and when is it truly finished?

The event loop coordinates execution opportunities. Promises coordinate results. Neither automatically enforces those three responsibilities.

**Concurrency is not merely allowing several things to happen. It is allowing several things to happen without losing control of what must remain true.**

# Next Lecture — Threads, Atomics, and Memory Ordering

We've examined logical races caused by overlapping asynchronous operations.

But what happens when two threads really do execute simultaneously and access the same memory?

Can one thread observe a flag indicating that data is ready while still seeing an older value of the data itself?

Why can the compiler or processor rearrange certain operations without violating single-threaded behavior?

And what is the precise difference between atomicity, visibility, and ordering?

In CS320-L07, we'll descend into shared-memory concurrency: mutexes, atomic operations, compare-and-swap, happens-before relationships, and the memory-ordering rules that determine which observations are actually safe.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Lab — Concurrency That You Can Break Deliberately

**Environment:** Node.js 20 or newer. The examples are intended for a disposable local development environment.

## Lab A — Reproduce the single-threaded booking race

Create `booking-race.mjs`:

```javascript
let availableRooms = 1;

async function reserve(customer) {
  if (availableRooms <= 0) {
    return `${customer}: sold out`;
  }

  await Promise.resolve();

  availableRooms -= 1;

  return `${customer}: confirmed`;
}

const results = await Promise.all([
  reserve("Anna"),
  reserve("David")
]);

console.log(results);
console.log("Rooms left:", availableRooms);
```

Both handlers observe availability before either continuation decrements the count.

The result can confirm both customers and leave the inventory negative.

**Questions:** Where is the interleaving boundary? Why doesn't single-threaded execution prevent this logical race?

For a purely process-local demonstration, move the availability check and decrement together without an asynchronous suspension between them.

Then explain why this is still insufficient for multiple independent backend replicas sharing a database.

## Lab B — Protect the database invariant

For a simplified PostgreSQL inventory table, consider the following statement:

```sql
UPDATE room_inventory
SET available = available - 1
WHERE room_type_id = $1
  AND available > 0
RETURNING available;
```

Only a successful update returning a row should count as acquiring inventory.

In a production reservation workflow, the corresponding reservation record and any related authoritative changes need appropriate transactional coordination.

**Challenge:** Explain why reading `available` in one database operation and later issuing an unconditional decrement is weaker than a conditional update.

## Lab C — Microtasks versus timers

Create `microtasks.mjs`:

```javascript
console.log("A");

setTimeout(() => console.log("Timer"), 0);

Promise.resolve().then(() => {
  console.log("Promise microtask");
});

console.log("B");
```

Predict the ordering before executing it.

Now examine a finite microtask chain:

```javascript
let remaining = 50_000;

setTimeout(() => {
  console.log("Timer executed");
}, 0);

function continueMicrotasks() {
  if (--remaining > 0) {
    queueMicrotask(continueMicrotasks);
  }
}

queueMicrotask(continueMicrotasks);
```

The chain is deliberately finite.

Observe that processing a large number of microtasks can delay timer execution.

**Question:** Why isn't microtask scheduling an equivalent replacement for yielding to the event loop?

## Lab D — A bounded supplier worker pool

This example limits active operations and starts tasks only when a worker slot is available.

Create `bounded-concurrency.mjs`:

```javascript
import { setTimeout as sleep } from "node:timers/promises";

async function mapBounded(items, concurrency, task) {
  if (!Number.isInteger(concurrency) || concurrency < 1) {
    throw new RangeError("concurrency must be positive");
  }

  const results = new Array(items.length);
  let nextIndex = 0;

  async function worker() {
    while (nextIndex < items.length) {
      const index = nextIndex++;

      try {
        results[index] = {
          ok: true,
          value: await task(items[index], index)
        };
      } catch (error) {
        results[index] = {
          ok: false,
          error: String(error)
        };
      }
    }
  }

  const workers = Array.from(
    { length: Math.min(concurrency, items.length) },
    () => worker()
  );

  await Promise.all(workers);
  return results;
}

let active = 0;
let maximumObserved = 0;

async function supplierCall(id) {
  active++;
  maximumObserved = Math.max(maximumObserved, active);

  try {
    await sleep(100);
    return `Supplier ${id}: success`;
  } finally {
    active--;
  }
}

const suppliers = Array.from({ length: 20 }, (_, i) => i + 1);

const results = await mapBounded(
  suppliers,
  3,
  supplierCall
);

console.log("Maximum active:", maximumObserved);
console.log("Completed:", results.length);
```

This is a teaching implementation, not a complete production admission controller.

It limits active operations but still retains the input collection and result array. It doesn't enforce a global limit across processes, nor does it implement cancellation of queued work.

**Question:** Why must the supplied `task` be called inside the worker loop rather than eagerly invoked for every input before entering the limiter?

## Lab E — Cancellation with `AbortSignal`

A supplier request can receive a signal that combines a parent cancellation condition with a deadline.

```javascript
async function fetchSupplier(url, parentSignal) {
  const deadline = AbortSignal.timeout(1500);

  const signal = AbortSignal.any([
    parentSignal,
    deadline
  ]);

  const response = await fetch(url, { signal });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}
```

The parent can signal cancellation through its own `AbortController`.

The deadline signal aborts after the configured duration.

The combined signal aborts when either condition occurs.

**Challenge:** Explain why aborting the fetch doesn't prove that the remote server never received the request or performed a side effect.

## Lab F — The `Promise.all` fail-fast trap

Create `promise-failure.mjs`:

```javascript
import { setTimeout as sleep } from "node:timers/promises";

async function task(name, delay, fail = false) {
  await sleep(delay);

  console.log(`${name}: underlying work finished`);

  if (fail) {
    throw new Error(`${name}: failed`);
  }

  return name;
}

try {
  await Promise.all([
    task("A", 20, true),
    task("B", 100),
    task("C", 150)
  ]);
} catch (error) {
  console.log("Aggregate rejected:", error.message);
}

await sleep(250);
```

Observe that the aggregate rejects when A fails, while B and C can still finish afterward.

**Question:** If B and C represented payment operations, what additional correctness mechanisms would be required before safely retrying the overall workflow?

## Lab G — Controlled concurrency examination

Consider this hypothetical incident:

```text
Deployment:
  12 Node.js replicas
  Supplier concurrency per replica: 20

Observed:
  Active supplier requests can reach ~240
  Supplier documented maximum: 80 concurrent requests
  p50 latency: improved slightly
  p99 latency: increased from 450 ms to 4.2 s
  429 responses: increasing
  Retry rate: increasing
  Pending task memory: increasing

Cancellation:
  Frontend aborts requests
  Backend supplier calls continue
```

Prepare a short incident diagnosis.

Explain the difference between the per-replica limit and the supplier's global limit. Identify how retries can create positive feedback. Propose bounded queueing and overload behavior. Then define how the parent request's cancellation should propagate to child operations.

Finish by identifying the conditions under which a supplier operation should continue after the customer has disconnected.

The goal is a defensible lifecycle and capacity design, not simply a smaller number in a concurrency configuration.

---

# Further Reading

Primary references:

1. Node.js — Event Loop, Timers, and `process.nextTick`  
   https://nodejs.org/en/learn/asynchronous-work/event-loop-timers-and-nexttick

2. Node.js — Don't Block the Event Loop (or the Worker Pool)  
   https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop

3. Node.js — Global `AbortController` and `AbortSignal`  
   https://nodejs.org/api/globals.html

4. MDN — `Promise.all()`  
   https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/all

5. MDN — `Promise.allSettled()`  
   https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/allSettled

6. Node.js — Worker Threads  
   https://nodejs.org/api/worker_threads.html

7. PostgreSQL — Transaction Isolation  
   https://www.postgresql.org/docs/current/transaction-iso.html

8. Python — `asyncio.TaskGroup`, for a contrasting structured-concurrency model  
   https://docs.python.org/3/library/asyncio-task.html

Related programme chapters:

- CS220-L02 — JavaScript Semantics and TypeScript Reality
- CS220-L06 — Managed Runtimes: Node.js, CPython, and the JVM
- CS320-L05 — System Calls, File Descriptors, and Asynchronous I/O
- CS320-L07 — Threads, Atomics, and Memory Ordering
- CS430-L05 — Designing Reliable Business Workflows

---

## Dense Cheatsheet — Interview Glance Card

```text
CS320-L06 — CONCURRENCY, EVENT LOOPS, CANCELLATION

FOUNDATIONS
  Concurrency = overlapping progress of logical operations
  Parallelism = simultaneous execution on different resources
  Async != parallel
  Promise != thread
  await != global lock
  Single JS thread can have logical races across await

EVENT LOOP
  Current synchronous JavaScript executes first
  Deferred callbacks run through runtime scheduling phases
  Timers have eligibility thresholds, not exact deadlines
  Poll = I/O-related processing
  Check = setImmediate callbacks
  Promise reactions = microtasks
  process.nextTick = Node-specific scheduling queue
  Ordering depends on execution context / runtime version
  Node 20+ changed timers relative to poll phase

MICROTASKS
  await fulfilled Promise still schedules continuation
  Promise reactions run at microtask checkpoints
  Repeated microtask replenishment may starve I/O/timers
  await Promise.resolve() != guaranteed event-loop yielding
  CPU-intensive work may need worker threads/processes

LOGICAL RACE
  A reads available=1, then awaits
  B reads available=1, then awaits
  A confirms/decrements; B confirms/decrements
  Result: oversell, even on one JS thread
  Race = outcome depends on unconstrained interleaving
  Not necessarily a shared-memory data race

INVARIANTS
  Define what must always remain true
  Protect check + state transition at authoritative boundary
  Local mutex != cross-replica coordination
  DB conditional update / transaction may enforce inventory
  Correct scope of synchronization is critical

PROMISE ALL
  Aggregates results of already-started Promise operations
  Fulfilled results preserve input order
  Rejects when one input rejects
  Rejection DOES NOT cancel other work
  allSettled waits for outcomes, does not limit concurrency
  Eagerly creating 10k operations can overload resources

SEMAPHORE / LIMITER
  Acquire permit BEFORE initiating bounded work
  Release in finally when actual work is finished
  Handle cancellation while waiting for permit
  Process-local permits != deployment-wide capacity budget
  N replicas × per-replica limit = possible aggregate demand

THREE CAPACITY CONTROLS
  Concurrency limit = maximum active work
  Rate limit = work admitted over time
  Queue limit = maximum waiting work
  Active bound without queue bound can still exhaust memory
  Buffers absorb bursts but cannot create throughput

BACKPRESSURE
  Producer rate > consumer capacity -> growing backlog
  Downstream capacity must influence upstream production
  Streams / queues / request admission are different layers
  More buffering delays overload; doesn't eliminate it
  Load shedding can protect useful throughput

CANCELLATION
  Parent operation should own/track child lifetimes
  AbortSignal requests cancellation through supported APIs
  AbortSignal.timeout = deadline-driven abort
  AbortSignal.any = combined abort conditions
  Cancellation != retroactive rollback
  Canceling wait != proof underlying work stopped
  Side effects may have completed before cancellation

STRUCTURED CONCURRENCY
  Explicit task ownership and lifecycle
  Parent accounts for child completion/failure/cancellation
  Detached durable jobs require explicit ownership transfer
  Unmanaged fire-and-forget work creates uncertainty

TIMEOUTS / DISTRIBUTED CORRECTNESS
  Timeout = local deadline expired
  Remote success/failure may remain UNKNOWN
  Payment retries need durable operation identity
  Idempotency and reconciliation protect external effects
  Promise rejection != distributed transaction rollback

TESTING
  Control the dangerous interleaving
  Test invariants, not only HTTP response statuses
  Booking: confirmed reservations <= capacity
  Payment: no duplicate charge under retries
  Probe concurrent failures and cancellation races
  Reproduce with deterministic scheduling barriers

PRODUCTION DIAGNOSIS
  1. Define invariant and operation ownership
  2. Measure active work, queue size, completion rate
  3. Inspect dependency capacity, latency and 429s
  4. Check retries, cancellations, leaked pending work
  5. Distinguish process-local from global limits
  6. Apply bounded admission / backpressure
  7. Verify p99, throughput, resource usage, correctness

SENIOR INTERVIEW ANSWER
  "I'd distinguish overlapping tasks from parallel execution,
   identify any state invariants that interleavings can violate,
   bound in-flight and queued work according to actual downstream
   capacity, then define cancellation and ownership so unfinished
   operations cannot silently escape the request lifecycle."

MENTAL MODEL
  STATE: what must remain true?
  CAPACITY: how much may overlap?
  LIFETIME: who owns the work until it truly finishes?
```
