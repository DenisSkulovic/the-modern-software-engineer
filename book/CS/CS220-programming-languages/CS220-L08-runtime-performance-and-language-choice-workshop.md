---
id: CS220-L08
course: CS220
title: "Runtime Performance and Language Choice Workshop"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: CS220-L07
next: null
---





# CS220 — Languages, Types, Memory, and Runtimes

## Lecture 08: Runtime Performance and Language Choice Workshop

*The Rust prototype is faster. The Go prototype is simpler to deploy. Python already handles the business rules correctly. The Node.js API has terrible tail latency, and Java virtual threads have made the database problem worse. Management wants a language decision by Friday. Your task is to explain why that is probably the wrong question.*

---

# Part I — Intuition

## The picture to carry in your head

Imagine you've joined the architecture committee of a growing travel technology company.

The platform searches hotels from external suppliers, calculates prices, and generates customer reports.

Its backend contains three major services.

The public API is written in Node.js.

A pricing worker uses Python.

A report-processing service uses Java.

All three have performance problems.

The API's slowest requests take several seconds.

The Python worker takes too long to calculate large pricing batches.

And the Java service becomes unresponsive when too many reports are generated simultaneously.

Management has a proposal.

"Why don't we rewrite the backend in Rust? It's compiled, memory-safe, and fast."

Another engineer proposes Go.

A third argues that the team should keep its existing languages because changing runtimes introduces complexity.

Everyone has a plausible argument.

But nobody has yet established why the services are slow.

## 1. Performance is not a property of a language name

Imagine a delivery company.

It operates a fleet of expensive, powerful trucks.

Deliveries are consistently late.

The CEO proposes buying faster trucks.

But when an investigator examines the operation, they discover that the trucks spend most of their time waiting for loading docks.

A faster engine won't solve that.

Perhaps the company should improve its loading process, schedule deliveries differently, or add loading capacity.

Now consider a different delivery route.

The truck itself is overloaded, moves slowly, and consumes excessive fuel.

There, a better vehicle might genuinely improve the operation.

The lesson is that **a performance problem belongs to a particular resource constraint, not automatically to the technology that happens to contain it**.

A Node.js request can be slow because an external supplier is slow.

A Python calculation can be slow because its algorithm performs unnecessary work.

A Java service can be slow because it overwhelms a database.

Rewriting those services might change some overhead.

It won't necessarily change the actual constraint.

## 2. There are several kinds of slowness

When a developer says a service is slow, ask what they mean.

Perhaps an individual request takes too long to complete. That's a latency problem.

Perhaps the system cannot process enough requests per second. That's a throughput problem.

Perhaps the application consumes too much CPU per useful operation. That's an efficiency problem.

Perhaps a service becomes unstable at high concurrency. That's a capacity or overload problem.

Perhaps it performs well after warmup but starts too slowly. That's a startup problem.

These are related, but they aren't interchangeable.

A service can provide excellent throughput while occasionally producing terrible tail latency.

It can respond quickly to one request but collapse when many arrive simultaneously.

And it can use relatively little CPU because it's spending most of its time waiting for something else.

Before measuring performance, define which behavior needs to improve.

## 3. A benchmark is an experiment, not a competition

Suppose our Python team writes a pricing function.

The Rust team writes the same pricing function.

The Rust version runs faster.

What have we learned?

We've learned that one implementation was faster under the conditions of that experiment.

But perhaps the Python version used a list search inside every iteration while the Rust version used a dictionary-like lookup.

Perhaps one used a compact array and the other allocated millions of objects.

Perhaps the Python code used arbitrary-precision integers while the Rust code used fixed-width arithmetic that overflowed for certain inputs.

Perhaps the Rust version ran across four cores while Python used one.

A benchmark becomes useful only when we know what it actually compares.

The first rule is that both implementations must produce equivalent results.

The second is that differences in algorithms, representations, resource usage and execution configuration must be understood.

A faster incorrect program is not a successful optimization.

## 4. Fix the unnecessary work before changing the worker

Imagine a pricing calculation that processes millions of hotel offers.

For every offer, it searches through a list of discount rules to find the applicable discount.

Now imagine the developer replaces that repeated search with an appropriate indexed lookup.

The calculation becomes dramatically faster.

The language hasn't changed.

The runtime hasn't changed.

The program simply performs less unnecessary work.

This is often the most valuable performance improvement available.

A language rewrite may reduce the cost of each operation.

An algorithmic improvement can remove entire categories of operations.

### The two kinds of improvement

```text id="fp9q0a"
SAME WORK, FASTER EXECUTION

  1,000,000 operations
        |
        v
  Better runtime / representation
        |
        v
  Faster operations


LESS WORK

  1,000,000 operations
        |
        v
  Better algorithm / data structure
        |
        v
  100,000 operations
```

The numbers are illustrative. The central distinction is between reducing the cost per operation and reducing how much work must be performed.

Both can matter.

But they should be investigated separately.

## 5. The rewrite has its own price

Now imagine a team migrates the pricing worker from Python to Rust.

It must reimplement the calculation.

It must preserve every rounding rule, discount condition, and currency constraint.

It must validate the new implementation against real historical cases.

It must integrate the worker with the existing deployment and monitoring systems.

It may need new libraries and expertise.

It must maintain both implementations during the transition.

And production failures in the new runtime may initially take longer to diagnose.

A successful rewrite can be worthwhile.

But its benefit must justify that cost.

A two-second improvement in a background operation may be extremely valuable if it removes an important business bottleneck.

Or it may be irrelevant if the operation already meets its service-level objective and runs only a few times per hour.

The right answer depends on the actual requirements.

## 6. Our architecture committee needs evidence

Here's what the committee must establish.

For the Node.js API, which part of request latency is local execution and which part is supplier waiting?

For the Python pricing worker, how much work is algorithmically necessary and how much is overhead?

For the Java report processor, is the limiting resource the runtime, the database, or something else?

Then, for each proposed fix, we need to estimate the benefit, test the hypothesis, and compare the result against the cost of implementation and operation.

The language decision comes after those questions.

Not before.

### Three questions before the Deep Dive

1. Why might a faster runtime have almost no effect on a request that spends most of its time waiting for a supplier?
2. Why is an algorithmic improvement often more valuable than changing languages?
3. What information must a benchmark provide before it can justify an architecture decision?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. Monday Morning: You're Responsible for the Architecture

You arrive at the engineering office to find three incidents awaiting review.

The public API's p99 latency has climbed above its target.

The pricing batch is too slow for an upcoming product feature.

The Java report service is generating a growing backlog during peak activity.

Management wants one strategic answer.

Should the company consolidate on Go or Rust?

Before responding, you request the measurements.

The operations team provides an evidence packet.

For this exercise, the measurements are fictional but designed to represent realistic failure patterns. Treat them as observations from a controlled case study, not universal benchmark results for the languages involved.

The first lesson of the workshop is to resist choosing a solution before reading the evidence.

## 2. Define Success Before Inspecting the Code

The platform has three explicit performance requirements.

The customer search API should maintain p95 latency below two seconds under its expected peak workload.

The large pricing batch should finish within twenty seconds on its allocated compute resources.

The report service should process accepted work without generating an unbounded queue or allowing database waiting to produce unacceptable tail latency.

These requirements differ.

The first concerns user-visible response latency.

The second concerns batch completion time.

The third concerns sustained capacity and overload behavior.

A language change might help any of them, but only through specific mechanisms.

### The hidden business constraint

All implementations must preserve correctness.

Pricing must use the same monetary representation, rounding rules, and discount eligibility conditions.

Supplier results must be associated with the correct search.

Reports must not be silently lost or duplicated.

A performance improvement that violates those constraints is unacceptable.

We will therefore evaluate each proposed optimization along two dimensions:

Does it improve the measured performance requirement?

Does it preserve the intended business contract?

## 3. Evidence A: The Node.js Search API

The API runs four Node.js replicas, each with a one-vCPU resource limit.

Together, they handle approximately 140 hotel searches per second during the measurement window.

Each search contacts roughly eighteen external supplier endpoints.

The observed p95 latency is 2.5 seconds.

The p99 latency is 6.1 seconds.

Average CPU utilization per replica is around 38 percent of its allocated vCPU.

The measured event-loop delay remains relatively modest, with a p99 around 35 milliseconds during this observation window.

Supplier requests show a p95 duration of approximately 1.7 seconds.

And roughly nine percent of supplier requests receive rate-limiting responses.

### What does the evidence suggest?

The first instinct might be that Node.js is too slow.

But the CPU evidence doesn't strongly support a main-thread computation bottleneck.

The event-loop delay measurement also doesn't indicate sustained multi-second blocking.

Meanwhile, external supplier calls account for substantial elapsed time, and rate limiting is visible.

A plausible hypothesis is that the API is initiating too much supplier traffic without coordinating concurrency appropriately.

The runtime can keep many requests in flight.

The suppliers cannot necessarily accept that demand.

### The fan-out calculation

At 140 searches per second and eighteen supplier calls per search, the application initiates approximately 2,520 supplier requests per second if each search performs all eighteen calls.

That aggregate rate is distributed across suppliers and replicas, but it demonstrates the scale of the fan-out.

If requests are launched without global or per-supplier limits, an individual supplier may receive far more concurrency than it supports.

Rate limiting, retries and additional waiting can amplify the problem.

**The first hypothesis is excessive external fan-out, not slow JavaScript arithmetic.**

## 4. What Would a Rust Rewrite Actually Improve?

Imagine rewriting the API in Rust.

The local request-handling overhead may decrease in some parts of the system.

Memory representation may improve.

Startup or runtime characteristics may change.

But the supplier still takes 1.7 seconds at p95 under the observed conditions.

The supplier still rate-limits requests.

The network still has latency.

A faster local loop cannot make a remote service complete work sooner simply by executing fewer instructions.

### A critical-path calculation

Suppose a representative slow trace takes 2.4 seconds.

Of that, roughly two seconds involve the external supplier path and associated waiting.

Only twelve milliseconds are attributed to the local pricing and normalization computation in this particular trace.

Even eliminating those twelve milliseconds entirely would have a small direct effect on that trace's total latency.

This isn't a complete mathematical decomposition of the service's p95 or p99 distribution.

Percentiles can't generally be added or subtracted as though they were ordinary sequential durations.

The calculation is an illustration based on one trace.

But it reveals why optimizing a small local component is unlikely to solve a delay dominated by an external dependency.

### The better first intervention

Introduce explicit per-supplier concurrency and request-rate policies.

Use bounded queues with well-defined rejection or deferral behavior.

Apply appropriate deadlines.

Avoid retry amplification during overload.

And consider whether the user experience genuinely requires waiting for every supplier before returning anything useful.

Those changes address the observed source of latency and instability.

Rust might still be a valid implementation language.

But the data doesn't yet justify changing to it.

## 5. Global Limits Versus Per-Replica Limits

Now a subtle architecture issue appears.

The team proposes limiting each Node.js replica to fifty concurrent supplier requests.

There are four replicas.

The supplier's allowed concurrency budget is eighty requests across the entire customer account.

Does the proposed limit respect that budget?

No.

Four replicas each allowing fifty requests can collectively initiate up to two hundred.

A per-process limit isn't necessarily a global limit.

### The distributed coordination problem

The platform needs a way to enforce supplier-level budgets across replicas.

Possible approaches include a shared coordination mechanism, routing supplier calls through a bounded gateway, or partitioning ownership so that one controlled pool manages a particular supplier.

Each design has trade-offs involving failure recovery, latency, and operational complexity.

For a relatively small application, a conservative per-replica allocation might be sufficient.

For a system requiring strict account-wide rate compliance, more explicit coordination may be necessary.

The important point is that concurrency limits must be defined at the scope of the constrained resource.

### Rate versus concurrency

Another distinction matters.

Concurrency limits restrict how many operations are simultaneously in flight.

Rate limits restrict how many operations may begin during a time interval.

One doesn't automatically enforce the other.

If requests complete extremely quickly, a concurrency limit of ten may still permit a high request rate.

If requests take a long time, a low concurrency limit may restrict throughput substantially.

A robust supplier integration must understand which contractual limits apply.

This is a systems problem shared across runtimes.

## 6. Evidence B: The Python Pricing Worker

Now examine the pricing worker.

It processes four million quotation candidates in one batch.

The environment provides a four-vCPU resource allocation and a two-gibibyte memory limit.

The current implementation uses a single main pure-Python execution path for most of its calculation.

The batch takes approximately 68 seconds.

One CPU core remains heavily occupied while the others are mostly idle.

The initial profiling results suggest that repeated discount-rule lookup consumes the largest portion of active CPU time.

### The algorithmic clue

Each quotation needs an applicable discount rule.

The current code searches a list of rules repeatedly.

The work is conceptually simple.

For each quotation, examine candidate rules until one matches.

But repeated linear searches can create significant cost when the batch contains millions of quotations.

The profiler indicates that this lookup behavior deserves investigation before the team debates runtimes.

### The first proposed optimization

Build an appropriate index over the discount rules before processing the quotation batch.

Then look up eligible rules through the index rather than repeatedly scanning the entire rule list.

The actual design must account for precedence, overlapping eligibility, effective dates and other business conditions.

But if the rule semantics permit a useful index, the algorithm can perform substantially less work.

The first benchmark tests this change in Python itself.

No language migration required.

## 7. The First Benchmark Changes Everything

The team implements the indexed lookup in Python.

The benchmark uses the same input dataset and verifies that the output agrees with the original implementation.

The batch duration falls from approximately 68 seconds to 23 seconds.

That's a major improvement.

The runtime is unchanged.

The programming language is unchanged.

The algorithm and data access pattern changed.

### Why this matters for the decision

Management's original diagnosis was "Python is too slow."

But a large part of the observed cost came from an unnecessarily expensive repeated search.

The original benchmark would have compared an inefficient Python implementation with whatever algorithms the Go and Rust prototypes happened to use.

That wouldn't have isolated runtime performance.

### The profiling lesson

A profiler is useful because it directs attention toward expensive operations.

But even a profile shouldn't be treated as a complete explanation.

It identifies where CPU time is spent.

The engineer must still ask why that work is necessary and whether it can be reduced.

A slow function may be expensive because its implementation is inefficient.

Or it may be expensive because it is called far more often than required.

The correct optimization may change the algorithm, the data model, or the surrounding workflow.

**Before paying less for each operation, ask why the program performs so many operations.**

## 8. The Second Benchmark: A Native Numerical Kernel

The optimized Python worker now completes in 23 seconds.

The target is twenty seconds.

The team investigates the remaining CPU cost.

Some pricing operations can be expressed as bulk numerical transformations over validated arrays.

Instead of performing every operation through a Python-level loop, the implementation moves a suitable portion of the work into an optimized native numerical library.

The business rules remain unchanged.

Output equivalence is checked against the reference implementation.

The resulting batch duration falls to approximately 16.5 seconds.

The Python implementation now satisfies the twenty-second target under the measured conditions.

### What changed?

The application still uses Python.

But some expensive operations execute through native library code.

This can reduce interpreter-level overhead and take advantage of optimized data representations and compiled numerical routines.

The result demonstrates why a program's top-level language is not a complete description of the machine code performing its work.

### The new decision point

The team now has a working Python implementation that meets the requirement.

Should it stop?

Not automatically.

There may be other benefits to a different implementation.

Memory consumption, deployment size, future capacity, and operational simplicity could justify additional work.

But the burden of proof has changed.

A rewrite is no longer necessary merely to reach the stated batch-duration target.

The team should now ask whether a further improvement has enough business value to justify its cost.

## 9. The Go and Rust Prototypes Arrive

The Go team delivers a prototype.

It processes the batch in approximately 14.7 seconds.

The Rust team reports approximately 13.9 seconds.

The Rust implementation wins this fictional benchmark.

All implementations use comparable input datasets and are required to produce equivalent outputs.

The measurements use the same intended CPU resource budget.

For this particular comparison, the pricing kernel is kept single-worker where practical, so the study doesn't quietly compare one serial implementation with an aggressively parallel one.

The full benchmark records contain build versions, compilation settings and warmup conditions.

### What does the ranking tell us?

It tells us that the optimized Rust prototype was faster than the other measured implementations for this workload under those conditions.

It does not establish that Rust is universally faster than Go or Python.

It doesn't establish that the full service would improve by the same percentage.

And it doesn't yet include the complete cost of integrating and operating the replacement.

### The incremental benefit

The optimized Python version takes 16.5 seconds.

Rust takes 13.9 seconds.

The difference is 2.6 seconds per batch.

That's approximately a 15.8 percent reduction in batch duration relative to the optimized Python implementation.

This is a meaningful improvement for some workloads.

For others, it may be economically insignificant.

Now we must determine what the improvement is worth.

## 10. The Business Case for Another 2.6 Seconds

Suppose the company processes one large pricing batch every five minutes.

The batch already completes before its twenty-second deadline.

The remaining three-and-a-half-second margin provides some headroom.

Moving to Rust would increase that margin.

But the company must also pay for migration and maintenance.

### The migration cost

The pricing module contains subtle business rules.

Some discounts depend on dates and occupancy.

Some suppliers use special rounding behavior.

Some calculations require currency-specific precision.

The Python implementation is mature and heavily tested.

A Rust rewrite introduces implementation and validation work, new deployment artifacts, unfamiliar operational behavior, and potentially a new team skill requirement.

Management has allocated six weeks for the proposed migration.

Would those six weeks produce more business value than improving supplier reliability or report-service capacity?

That's an opportunity-cost question.

### When the answer might be yes

Suppose the batch runs continuously and consumes a large fraction of the company's compute budget.

A fifteen-percent reduction in resource demand may produce substantial recurring savings.

Or suppose the company plans a tenfold expansion in data volume.

The faster implementation may provide useful capacity headroom.

Or perhaps Rust's memory-safety guarantees are particularly valuable because the service parses untrusted binary inputs.

Those are legitimate reasons to consider the migration.

### When the answer might be no

If the batch runs infrequently, comfortably meets its deadline, and consumes little operational budget, the improvement may not justify a new runtime boundary.

The strongest decision is not always to choose the fastest measured implementation.

It's to choose the implementation that meets requirements at the best total engineering cost.

## 11. The Correctness Gate: Five Programs Must Compute the Same Thing

Before accepting the benchmark results, we need to check semantic equivalence.

This is especially important for financial software.

Imagine a nightly price of 199.95 euros.

The application applies a discount, a tax adjustment, and a service fee.

If the implementations use different rounding rules, they may disagree by one or more cents.

That may be unacceptable.

### Integer minor units

One approach represents monetary values using integer cents or another defined minor unit.

This avoids many ordinary binary floating-point representation problems.

But the chosen integer range must be large enough for the workload.

Overflow behavior differs across languages and representations.

The benchmark must check boundary values.

### Decimal rules

Some calculations require decimal fractions, currency conversion or intermediate precision beyond integer cents.

The business contract must define rounding modes, intermediate precision and conversion-rate snapshots.

The implementations should not independently invent their own interpretations.

### Stable ordering

Suppose several hotel offers have equal calculated prices.

The system may require a deterministic tie-breaking rule.

If one implementation changes result ordering, the user-visible outcome may differ even when all prices match.

Correctness comparison should include the meaningful output contract, not just an aggregate checksum.

### The golden dataset

A strong benchmark uses a versioned input dataset containing ordinary cases, edge cases, and historical production examples.

It verifies outputs against a trusted reference.

It includes invalid inputs and expected failure behavior where relevant.

For critical workflows, it can compare entire outputs or normalized records instead of relying solely on a checksum that might conceal differences.

**An optimization is eligible for production only after it preserves the defined behavior.**

## 12. The Fairness Problem: Are We Comparing Languages or Implementations?

Now suppose the Go implementation uses a compact slice of structs.

The Rust implementation uses a similarly compact representation.

The Python version uses ordinary dictionaries until its native numerical kernel begins.

What are we actually comparing?

We are comparing complete implementations.

Their representations, allocation behavior and execution strategies differ.

That is not automatically a bad benchmark.

An application-level benchmark should often compare realistic, idiomatic implementations.

But we must not claim it isolates one variable when it doesn't.

### Two legitimate benchmark designs

An **implementation benchmark** compares realistic versions of the complete workload.

It asks which implementation meets the application's requirements most effectively.

A **mechanism benchmark** isolates a narrower question.

For example, it may compare numeric loop execution under more closely controlled representations.

Both are useful.

They answer different questions.

### Startup versus steady state

A JVM or JavaScript engine may benefit from runtime warmup.

A short-lived job may care about first-run latency.

A permanently running backend may care about steady-state throughput.

The benchmark must specify which behavior matters.

### Parallelism

If one implementation uses four cores and another uses one, elapsed-time differences may reflect parallel execution rather than faster per-core computation.

That can still be a valid architecture comparison when resource costs are included.

But the study must disclose the difference.

### Repeated measurements

One run is not enough.

Benchmark results can vary because of CPU scheduling, garbage collection, compilation activity, memory pressure, and background load.

Use repeated runs, inspect distributions, and preserve the raw results.

A good benchmark is an experiment designed to distinguish explanations—not a race arranged to produce a preferred winner.

## 13. Evidence C: The Java Report Service

Now examine the third incident.

The company uses Java virtual threads to process report requests.

During peak activity, one service instance has approximately six hundred concurrent virtual threads involved in report-related operations.

The database connection pool permits thirty active connections.

The service's p99 response duration rises to approximately nine seconds.

Most of that time is spent waiting for database access or query completion rather than executing Java business logic.

Management proposes replacing the Java service with Go.

### Does Go solve the bottleneck?

Go can efficiently represent many waiting goroutines.

But the existing Java runtime already represents many waiting virtual threads efficiently.

The problem is not that waiting threads are expensive.

The problem is that the application admits much more database demand than its backend can process healthily.

Changing the type of lightweight task won't increase the database's processing capacity.

### The missing control

The service needs a bounded admission policy.

It should limit active database-dependent operations according to measured pool and database capacity.

It should avoid allowing an enormous uncontrolled queue to form.

It should define what happens when the system reaches capacity.

Perhaps requests wait within a bounded budget.

Perhaps background reports are durably queued.

Perhaps low-priority requests receive a clear overload response.

The correct policy depends on business semantics.

### The surprising result

After introducing appropriate concurrency limits and queue management, the Java service's latency stabilizes in the fictional follow-up test.

The service keeps using virtual threads.

The database remains the constrained resource, but demand is now managed.

The team didn't need another runtime.

It needed a better relationship between concurrency and capacity.

## 14. Little's Law: Why Waiting Work Accumulates

Let's add one mathematical tool.

Little's Law relates the average number of items in a stable system to throughput and average time spent in the system.

In its familiar form:

\[
L = \lambda W
\]

Here, \(L\) is the average number of items present.

\(\lambda\) is the average completion rate in a stable system.

\(W\) is the average time each item spends in the system.

### The intuition

Suppose a service completes one hundred operations per second.

Each operation spends an average of half a second in the system.

Then the average number of operations present is approximately fifty.

Now suppose the average duration rises to two seconds while the stable throughput remains one hundred operations per second.

The average number of in-flight operations rises to approximately two hundred.

More waiting time means more concurrent work remains present.

### Why this matters for lightweight tasks

Virtual threads and goroutines make it economical to represent many waiting operations.

But if waiting time increases, the number of in-flight tasks can grow substantially.

Each task still has some memory, scheduling state, and references to application data.

If the system accepts work faster than it can complete work, the backlog is not stable.

Little's Law's stable-system assumptions no longer justify treating average in-flight counts as bounded.

The queue can grow until admission control, memory limits, or another failure mechanism intervenes.

### The architectural implication

A lightweight concurrency model doesn't eliminate the need for queue and admission policies.

It may actually make overload harder to notice initially because the runtime can represent so many waiting tasks before failing.

This is a subtle but important lesson:

**Cheap waiting is not unlimited capacity. It can simply make an overloaded system appear healthy for longer.**

## 15. The Combined Architecture Decision

We now have enough evidence to make decisions.

Let's examine each service separately.

### Decision A — Keep the Node.js search API

The evidence points toward excessive supplier fan-out and external waiting, not a dominant JavaScript execution bottleneck.

Prioritize supplier-aware concurrency limits, rate control, deadlines, and better handling of partial supplier failures.

Retest user-visible latency after those changes.

A future runtime change remains possible, but isn't justified by the current observations.

### Decision B — Keep the optimized Python pricing worker

The original implementation took 68 seconds.

An algorithmic improvement reduced that to 23 seconds.

A native numerical kernel reduced it further to 16.5 seconds.

The twenty-second requirement is satisfied.

Go and Rust prototypes are somewhat faster, but the incremental benefit must be weighed against the migration cost.

For the current workload and stated deadline, retaining Python is the strongest default decision.

### Decision C — Keep the Java report service

Virtual threads aren't the observed limitation.

The database connection pool and admission behavior are.

Introduce bounded database concurrency, queue policies, and dependency-level observability.

Then measure again.

### The important caveat

These aren't universal declarations that Node.js, Python, and Java are the best languages for those tasks.

They're conclusions for this fictional platform, given its observed constraints and requirements.

If the workload changes, the decision may change.

Architecture is a response to requirements and evidence, not a permanent judgment about language superiority.

## 16. What Would Change Our Recommendation?

A good architecture decision should identify the evidence that would cause it to be reconsidered.

For the Node.js API, a future profile might reveal that local CPU work dominates request latency after supplier fan-out is corrected.

That would justify investigating worker threads, native modules, or an alternative service boundary.

For the Python worker, batch volume might grow enough that the 16.5-second implementation no longer meets its deadline.

Or CPU costs might become sufficiently high that a native implementation produces meaningful infrastructure savings.

For the Java report service, the workload may evolve toward CPU-intensive document transformations rather than database waiting.

That could change its concurrency and deployment strategy.

### Avoid irreversible language ideology

The goal isn't to defend the current implementation forever.

It's to avoid a premature rewrite while remaining open to future evidence.

A useful decision record should contain the present observations, accepted trade-offs, and conditions that would trigger reconsideration.

This makes architecture adaptable rather than dogmatic.

## 17. The Migration Cost Isn't Only Code

Suppose management still wants to move the pricing worker to Rust.

The team estimates six weeks for implementation.

Is that the entire cost?

No.

The new code needs a deployment pipeline.

It needs monitoring and tracing.

The team needs debugging expertise.

Libraries and native dependencies need patching.

The service contract needs compatibility testing.

The rollout needs a rollback strategy.

And both implementations may need to coexist during migration.

### The coexistence problem

Suppose the company runs Python and Rust versions side by side.

It compares outputs for every pricing batch.

That's a powerful migration technique.

But the team must ensure that shadow processing doesn't accidentally duplicate business side effects.

A pure pricing calculation is relatively safe to shadow.

A payment-creation operation is not.

Shadow tests should be designed around operations whose effects can be isolated or disabled appropriately.

### The rollback problem

If the Rust service produces incorrect results under an unexpected edge case, can the system return to Python without breaking in-flight work or data compatibility?

If both implementations use the same durable job format and authoritative state, rollback may be manageable.

If the migration also changes message formats, database schemas, and operational contracts, rollback becomes more complicated.

A language rewrite often creates a system migration.

That wider scope belongs in the cost estimate.

## 18. The Performance Review Meeting

It's Friday.

Management asks for a final recommendation.

One engineer presents a chart showing Rust as the fastest language in the pricing benchmark.

Another points out that Python now satisfies the required batch duration.

A third explains that the Node.js and Java incidents originated from external resource constraints.

The meeting is at risk of becoming a discussion about personal language preferences.

Your job is to return to the evidence.

### The opening statement

"Our three performance problems have different causes. We should not treat them as one programming-language problem."

Then explain the data.

The Node.js API has supplier latency and rate-limiting symptoms.

The Python pricing worker had an expensive algorithmic lookup and now meets its target after optimization.

The Java report service admitted more database work than its constrained dependency could handle efficiently.

These conclusions suggest three targeted engineering changes.

They don't support a platform-wide rewrite.

### The difficult question

A manager asks:

"But Rust is faster. Why not use the best technology?"

The answer should not be defensive.

Rust may indeed be the best technology for a particular workload.

But the available evidence supports a narrower conclusion.

The optimized Rust prototype is 2.6 seconds faster per pricing batch than the optimized Python implementation.

The team must evaluate how often that difference matters, whether it improves a business objective, and whether the benefit exceeds migration and operational costs.

If it does, the rewrite can be justified.

If it doesn't, rewriting would consume engineering resources without solving the highest-priority constraints.

### The architectural principle

**The best technology is the one that satisfies the system's requirements with acceptable total cost and risk—not necessarily the one that wins an isolated benchmark.**

## 19. A Senior Engineer's Optimization Hierarchy

Let's extract a practical approach from the case.

First, determine whether the operation needs optimization at all.

If it meets its requirements with comfortable margin, optimization may not be the best use of engineering time.

Second, identify the actual limiting resource.

Is the operation CPU-bound, memory-bound, I/O-bound, or limited by a downstream dependency?

Third, eliminate unnecessary work.

Improve algorithms, data access patterns, query plans, and redundant operations before changing the execution environment.

Fourth, improve the implementation within the current runtime.

Consider better data representations, native libraries, worker arrangements, and resource-lifetime policies.

Fifth, address concurrency and capacity.

Bound work according to the real resources being consumed.

Finally, consider a runtime or language migration when the remaining limitation materially affects the business and the migration's benefits justify its costs.

This isn't an absolute ordering for every incident.

A security-critical system may require a language change for reasons unrelated to performance.

A failing service may need immediate capacity mitigation before anyone can profile it.

But the hierarchy prevents one common mistake: treating the most dramatic intervention as the most intelligent one.

## 20. The Oral Examination — Defend Your Architecture

Answer each question as though a skeptical engineering manager were challenging you.

### Challenge 1 — The Slow Node.js API

A search API has p95 latency of 2.5 seconds, low-to-moderate CPU usage, modest event-loop delay, slow suppliers, and frequent supplier rate limiting.

What is the leading hypothesis?

What experiment would you run before suggesting a language rewrite?

### Challenge 2 — The Python Breakthrough

A pricing batch takes 68 seconds.

Replacing repeated discount-list searches with indexed lookup reduces it to 23 seconds.

What does this reveal about the original bottleneck?

Why doesn't it prove that Python is the fastest runtime?

### Challenge 3 — The Rust Victory

The optimized Python batch takes 16.5 seconds.

Go takes 14.7.

Rust takes 13.9.

The requirement is twenty seconds.

Should the team migrate immediately to Rust?

What additional facts would influence the decision?

### Challenge 4 — The Virtual-Thread Disaster

A Java service can represent hundreds of virtual threads, but its database pool allows thirty active connections.

Tail latency increases as more work is admitted.

Why doesn't switching to Go's goroutines solve the underlying problem?

### Challenge 5 — The Invalid Benchmark

The Rust prototype uses a fixed-width integer representation that wraps a sufficiently large value.

The Python implementation uses arbitrary-precision integers and produces the correct business result.

Rust is faster.

Is the benchmark acceptable for choosing the production implementation?

### Challenge 6 — The Global Concurrency Limit

Four API replicas each allow fifty concurrent requests to a particular supplier.

The supplier permits eighty concurrent requests for the entire account.

What is wrong with the configuration?

### Challenge 7 — The Misleading CPU Number

A container has a four-vCPU allocation, but its pure-Python pricing loop uses only one core in a traditional GIL-enabled CPython deployment.

Why might the other cores remain underutilized?

Which implementation strategies could use them?

### Challenge 8 — The Architecture Decision

You have six weeks of engineering capacity.

You may either rewrite the optimized Python pricing worker in Rust or implement supplier-aware limits and improve failure handling in the search API.

What evidence would you use to prioritize the work?

## 21. Solutions and Discussion

### Solution 1 — Investigate supplier fan-out first

The observed external latency and rate limiting are stronger clues than the runtime's local execution cost.

Measure concurrency per supplier, retry behavior, queue waiting, and the critical path of slow searches.

Introduce controlled concurrency and deadlines, then compare results.

A Rust rewrite should not be the starting intervention.

### Solution 2 — The algorithm was doing unnecessary work

The large improvement without changing languages demonstrates that repeated lookup was a significant cost.

It doesn't establish a universal Python performance ranking.

The new implementation may still have runtime overhead, but the most expensive avoidable work was reduced.

### Solution 3 — A faster prototype isn't automatically a better business decision

Rust is faster for the measured batch, but optimized Python already satisfies the requirement.

Evaluate batch frequency, infrastructure savings, projected growth, migration risk, correctness validation, operational expertise, and maintenance cost.

A migration may be justified under different business conditions, but the benchmark alone doesn't establish that conclusion.

### Solution 4 — Lightweight tasks don't expand database capacity

Java virtual threads and Go goroutines can both represent many waiting operations efficiently.

Neither increases the number of queries the database can process.

The service needs dependency-aware admission limits, bounded queues, and an overload policy.

### Solution 5 — The programs aren't equivalent

The Rust implementation violates the required arithmetic contract for some inputs.

Its faster result is not a valid replacement for the correct behavior.

The benchmark must enforce equivalent numeric and business semantics before comparing performance.

### Solution 6 — Per-replica limits exceed the global budget

Four replicas permitting fifty requests each can collectively allow two hundred.

The supplier permits eighty account-wide.

The application needs an appropriately coordinated global policy or a conservative allocation that respects the shared limit.

### Solution 7 — Traditional GIL-enabled CPython limits pure-Python thread parallelism

A single pure-Python execution path uses one core.

Adding threads within one traditional GIL-enabled interpreter doesn't generally provide simultaneous Python-bytecode execution across cores.

Possible alternatives include multiprocessing, suitable native numerical libraries, free-threaded CPython where supported, or dividing work among appropriately isolated execution environments.

### Solution 8 — Compare impact, not implementation glamour

Estimate how much the additional 2.6 seconds of pricing improvement is worth.

Compare that with the customer impact of the search API's slow requests and supplier failures.

Use business objectives, incident rates, workload frequency, engineering cost and risk.

If the search API is violating customer-facing latency requirements while pricing meets its target, supplier reliability work is likely the better priority.

## 22. The Mental Model Worth Keeping

Runtime selection is an engineering decision about workloads and constraints.

The source language affects execution overhead, memory management, concurrency mechanisms, tooling and developer experience.

But performance also depends on algorithms, data representation, hardware, external services, queueing, and the operating environment.

A good benchmark tells you which implementation performs better under specific conditions.

A good architecture review tells you whether that difference matters enough to justify changing the system.

Whenever someone proposes rewriting a slow service, ask:

**What is the measured bottleneck? What work can we eliminate? What improvement do we need? What does the new runtime actually change? And is the expected benefit worth the migration cost?**

Those questions are the foundation of defensible language choices.

## 23. End of CS220 — From Language Semantics to Engineering Judgment

We've completed a coherent journey.

We began by distinguishing language semantics from runtime execution and business correctness.

We examined the JavaScript behaviors that cause subtle production failures.

We studied structural and nominal types, generics, sum types, ownership and borrowing.

We investigated references, garbage collection, and memory retention.

We followed source code through compilation, JIT optimization, and machine execution.

Then we compared Node.js, CPython, Java, Go and Rust as actual execution environments rather than language stereotypes.

Finally, we applied those mechanisms to an architecture decision.

The next stage of the curriculum moves beneath these runtimes.

**CS320 — Operating Systems and Concurrency** will explain how the kernel allocates CPU time, manages virtual memory, exposes system calls, coordinates I/O, and constrains processes and containers.

CS220 asked what programming languages and runtimes promise.

CS320 will ask what happens when those promises meet the operating system and finite hardware.

*The spoken lecture ends here. The remaining material is for hands-on investigation and screen-based revision.*

---

## Optional Practical Lab — The Runtime Architecture Review

**Objective:** Reproduce the decision-making process from the lecture by separating workload measurements, optimizing an algorithm, evaluating benchmarks, and writing an architecture decision record.

The data in this lab is fictional. It is intended for engineering analysis rather than claims about real runtime performance.

### Lab A — The Evidence Packet

Review the following data.

| Service | Main observation | Candidate problem |
|---|---|---|
| Node.js API | p95 2.5 s, supplier p95 1.7 s, rate limiting | External fan-out |
| Python pricing worker | 68 s per four-million-offer batch | Repeated discount lookup |
| Java report service | Hundreds of virtual threads, DB pool 30, p99 9 s | Dependency saturation |

For each service, write two competing hypotheses.

Then identify a measurement that would distinguish them.

### Lab B — Calculate Supplier Fan-Out

The search platform processes 140 searches per second.

Each search launches eighteen supplier requests.

Calculate the expected aggregate supplier-request rate under those assumptions.

Then calculate the maximum number of concurrent requests if four replicas each allow fifty per-supplier operations.

Compare the result with a supplier account limit of eighty.

**Question:** Why must a shared supplier limit be enforced at the scope of the whole application rather than assumed from each replica's local configuration?

### Lab C — A Python Algorithmic Optimization

Consider a simplified pricing workload.

Each offer contains a discount-code string and an amount in cents.

Discount rules map codes to integer percentage reductions.

The original implementation searches a list of rules for every offer.

Create `pricing-lab.py`:

```python id="c22lab1"
from time import perf_counter

RULES = [
    (f"DISC-{i:03}", i % 21)
    for i in range(100)
]

OFFERS = [
    (f"DISC-{i % 100:03}", 10_000 + (i % 5_000))
    for i in range(100_000)
]

def slow_calculation(offers, rules):
    total = 0

    for code, amount_cents in offers:
        discount = 0

        for rule_code, percent in rules:
            if rule_code == code:
                discount = percent
                break

        total += amount_cents * (100 - discount) // 100

    return total

def indexed_calculation(offers, rules):
    lookup = dict(rules)
    total = 0

    for code, amount_cents in offers:
        discount = lookup.get(code, 0)
        total += amount_cents * (100 - discount) // 100

    return total

def benchmark(name, fn):
    started = perf_counter()
    result = fn(OFFERS, RULES)
    elapsed = perf_counter() - started

    print(name, round(elapsed, 4), "seconds", result)
    return result

slow = benchmark("linear lookup", slow_calculation)
fast = benchmark("indexed lookup", indexed_calculation)

assert slow == fast
```

Run:

```bash id="c22lab2"
python pricing-lab.py
```

This is a small demonstration, not the four-million-offer production simulation from the lecture.

Both implementations use equivalent integer-cent arithmetic and the same discount rules.

**Questions:**

1. What work did the indexed implementation remove?
2. Why should output equivalence be checked before declaring a performance victory?
3. What happens when the number of rules grows substantially?

### Lab D — Benchmark Correctness Before Speed

Extend the pricing calculation with edge cases:

- A zero-price offer.
- A maximum supported price.
- A one-hundred-percent discount.
- A missing discount code.
- A discount rule that applies only during certain dates.

Define the expected result for each case.

Then compare any alternate implementation against those outputs.

If introducing another language, make both implementations consume the same versioned dataset and produce the same normalized result.

Don't rely only on total-duration comparisons.

### Lab E — Compute the Incremental Speedup

Use the fictional benchmark results.

| Implementation | Batch duration |
|---|---:|
| Original Python | 68.0 s |
| Indexed Python | 23.0 s |
| Python with native numerical kernel | 16.5 s |
| Go prototype | 14.7 s |
| Rust prototype | 13.9 s |

Calculate:

1. The speedup from original Python to indexed Python.
2. The speedup from original Python to optimized Python.
3. The percentage duration reduction from optimized Python to Rust.
4. The fraction of the original duration saved by algorithmic and native-kernel optimization.

**Discussion:** Does the largest improvement come from the language rewrite or from changing the work performed within Python?

### Lab F — Inspect Runtime Benchmark Tools

Explore the tool appropriate for your environment.

For Go:

```bash id="c22lab3"
go test -bench=. -benchmem
```

For Python, pyperf can run repeated measurements with calibration and multiple worker processes. Consult its documented runner and analysis commands.

For Java, investigate JMH and its warmup, measurement, fork and state-management features.

For Node.js, use `node:perf_hooks` or a suitable benchmark harness, and combine results with CPU profiling when diagnosing real work.

**Question:** Which sources of measurement bias does each tool attempt to reduce, and which aspects of production workload must you still reproduce yourself?

### Lab G — Write an Architecture Decision Record

Prepare an ADR titled:

**ADR: Should the Hotel Platform Consolidate Backend Services on Rust?**

Include:

- Context and performance requirements.
- Measurements and their limits.
- Options considered.
- Correctness constraints.
- Decision for each service.
- Trade-offs and risks.
- How the decision will be verified.
- Conditions that would trigger reconsideration.

A useful decision should avoid declaring that one language is inherently best for the platform.

### Lab H — The Skeptical Interviewer

Imagine you're being interviewed for a senior backend role.

The interviewer says:

"Our Python worker is slow. We should rewrite it in Go."

Respond as though you have five minutes at a whiteboard.

Your answer should distinguish CPU-bound and I/O-bound workloads, algorithmic work and runtime overhead, concurrency and parallelism, benchmark equivalence, and migration cost.

Then handle the follow-up:

"What if the Rust prototype is fifteen percent faster?"

Explain what additional information is necessary before making the decision.

---

## Further Reading

1. [Go Wiki — Benchmarks](https://go.dev/wiki/Benchmarks) — Designing and interpreting Go benchmarks.
2. [Python pyperf — Running Benchmarks](https://pyperf.readthedocs.io/en/latest/run_benchmark.html) — Calibration, warmup, repeated measurements, and variance.
3. [Python Performance Benchmark Suite](https://pyperformance.readthedocs.io/) — Broader Python implementation benchmarks.
4. [OpenJDK JMH](https://github.com/openjdk/jmh) — Reliable JVM microbenchmarking.
5. [Node.js — Performance Measurement APIs](https://nodejs.org/api/perf_hooks.html) — Timers, event-loop metrics, and performance observations.
6. [Node.js — CPU Profiling](https://nodejs.org/en/learn/diagnostics/poor-performance/using-cpu-profiler) — Finding active CPU hotspots.
7. [Google SRE Book — Handling Overload](https://sre.google/sre-book/handling-overload/) — Resource limits, load shedding, and overload behavior.
8. [Google SRE Book — Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/) — Retry amplification and system stability.
9. [Martin Fowler — Strangler Fig Application](https://martinfowler.com/bliki/StranglerFigApplication.html) — Incremental replacement of existing systems.
10. [Architecture Decision Records](https://adr.github.io/) — Recording architectural choices and trade-offs.

---

## Dense Cheatsheet — Interview Glance Card

*The final reference is fenced for rapid screen-based revision.*

```text id="c22l08card"
CS220-L08 — RUNTIME PERFORMANCE AND LANGUAGE CHOICE WORKSHOP

CORE QUESTION

  What is the actual bottleneck,
  and does changing the runtime address it?

PERFORMANCE DIMENSIONS

  Latency:
    Time for one operation

  Throughput:
    Work completed per unit time

  Efficiency:
    Resources consumed per useful result

  Capacity:
    Sustained workload without overload

  Startup:
    Initialization and warmup cost

FIRST RULE

  Define the business requirement before optimizing.

SECOND RULE

  Measure the limiting resource.

THIRD RULE

  Remove unnecessary work before changing runtimes.

CASE A — NODE.JS API

  4 replicas
  140 searches/s
  18 suppliers/search
  2,520 supplier requests/s
  p95 2.5 s
  p99 6.1 s
  Supplier p95 1.7 s
  Rate limiting observed
  Modest CPU/event-loop delay

  Leading hypothesis:
    Excessive external fan-out / supplier limits

  Best first action:
    Supplier-aware concurrency, rate control,
    deadlines, bounded queues, retry discipline

  Rewriting in Rust doesn't make suppliers faster.

GLOBAL CONCURRENCY

  4 replicas x 50 requests = 200 potential in flight

  Supplier account limit = 80

  Local limit != global limit

  Concurrency != request rate

CASE B — PYTHON PRICING

  Baseline: 68.0 s
  Indexed algorithm: 23.0 s
  Python + native kernel: 16.5 s
  Go prototype: 14.7 s
  Rust prototype: 13.9 s

  Target: <=20 s

  Optimized Python meets target.

  Rust saves 2.6 s vs optimized Python.
  About 15.8% shorter batch duration.

  Further migration requires business justification.

ALGORITHMIC VS RUNTIME OPTIMIZATION

  Algorithm:
    Reduce number of operations

  Runtime:
    Reduce cost of operations

  Better algorithm may dominate language choice.

CASE C — JAVA REPORT SERVICE

  Hundreds of virtual threads
  DB pool size 30
  p99 latency 9 s
  Heavy database waiting

  Leading hypothesis:
    More admitted work than DB can process

  Best first action:
    Bounded admission / queue / dependency capacity

  Go goroutines wouldn't expand database capacity.

LITTLE'S LAW

  L = lambda x W

  L:
    Average number in system

  lambda:
    Stable completion rate

  W:
    Average time in system

  Longer waiting -> more in-flight work
  at the same stable throughput.

  Unstable overload can create growing queues.

MICROBENCHMARK VS SYSTEM BENCHMARK

  Microbenchmark:
    Isolate narrow operation/mechanism

  System benchmark:
    Measure useful end-to-end workload

  Both valid, different questions.

BENCHMARK CONTRACT

  Same input distribution
  Same business results
  Same rounding rules
  Same overflow behavior
  Same output ordering where required
  Comparable resource budget
  Known runtime/compiler versions
  Correct warmup and measurement horizon

  Faster wrong code is not better.

BENCHMARK TRAPS

  Different algorithms
  Different data layouts
  Different thread counts
  Different numeric semantics
  JIT warmup differences
  Debug vs release builds
  Dead-code elimination
  Garbage collection
  Container CPU limits
  Unrepresentative inputs
  One lucky measurement

AHDMAHL-STYLE REASONING

  If only a small fraction of latency is local CPU,
  even perfect CPU optimization has limited direct impact.

  Don't add/subtract independent p95 measurements
  as if they were one sequential trace.

MIGRATION COST

  Reimplementation
  Correctness validation
  New dependencies
  Team expertise
  Deployment/observability
  Parallel running
  Rollback
  Long-term maintenance

  Local speedup != total engineering value.

ARCHITECTURE DECISION

  Node:
    Fix supplier fan-out first

  Python:
    Keep optimized implementation under current SLO

  Java:
    Bound DB concurrency and queues

  Reconsider when workload/requirements change.

OPTIMIZATION HIERARCHY

  1. Confirm requirement
  2. Measure bottleneck
  3. Remove unnecessary work
  4. Improve current implementation
  5. Bound concurrency / resource demand
  6. Evaluate runtime migration if justified
  7. Verify production behavior

SENIOR REVIEW QUESTIONS

  What's slow: CPU, memory, I/O, dependency?
  Which metric proves that?
  Is the algorithm doing avoidable work?
  Which resource actually limits throughput?
  Is the benchmark semantically equivalent?
  Does the proposed change meet a business objective?
  What is the total cost and risk?
  What future evidence would change the decision?

SENIOR LINE

  "I don't choose runtimes from speed rankings.
   I establish the workload and its business target,
   isolate the limiting resource, remove unnecessary
   work, and compare equivalent implementations.
   A language migration is justified when its measured
   benefit exceeds its correctness, operational,
   and long-term maintenance costs."
```
