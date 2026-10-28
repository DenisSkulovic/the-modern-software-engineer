---
id: CS220-L05
course: CS220
title: "From Source Code to Machine Code: Compilers and JITs"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: [CS101-S08]
prev: CS220-L04
next: CS220-L06
---



# CS220 — Languages, Types, Memory, and Runtimes

## Lecture 05: From Source Code to Machine Code — Compilers and JITs

*The pricing algorithm hasn't changed. Every test passes. The numbers are correct. Yet processing one hundred thousand hotel quotations suddenly takes twice as long. To explain why, we must follow the program beyond its source code.*

---

# Part I — Intuition

## The picture to carry in your head

Imagine a hotel-booking platform that regularly calculates prices for hundreds of thousands of accommodation offers.

Every quotation contains a base price, a discount, and a number of nights.

A TypeScript function calculates the final price.

The function has been stable for months.

Then the team integrates a new supplier.

The supplier's data is validated and normalized into the expected structure. The same pricing function continues receiving numbers in the correct fields.

All tests pass. The calculated prices remain correct.

But performance deteriorates.

The original workload required roughly forty milliseconds of CPU time in the team's controlled benchmark. The new one requires considerably more.

An engineer compares the source code before and after the integration.

The pricing function is unchanged.

Another engineer says, "Perhaps Node.js is slow. We should rewrite the calculation in Rust."

But that conclusion is premature.

Before changing languages, we need to understand what the existing JavaScript engine actually does when it executes the function.

## 1. Your processor doesn't know TypeScript

Think of a factory receiving an architectural drawing.

The drawing describes the desired building.

But the factory machinery doesn't operate directly on architectural ideas. It needs machine-specific instructions.

Programming is similar.

You write source code.

Tools parse it, check selected properties, and translate it into representations that other components can execute or transform.

At the bottom sits a processor.

The processor executes instructions defined by its architecture.

Those instructions manipulate registers, perform arithmetic, access memory, compare values, and change execution flow.

It doesn't natively understand TypeScript interfaces, JavaScript Promises, or hotel reservations.

Those concepts must eventually be represented through operations the machine can execute.

## 2. The same recipe can be executed in several ways

Imagine a chef working from a recipe.

One approach is to read each instruction and perform it immediately.

Another is to translate the recipe into a sequence of simpler instructions for kitchen workers.

A third is to study the recipe, identify repeated work, and prepare a more efficient production process.

Modern programming-language implementations use related strategies.

An interpreter executes instructions represented in a form it understands.

A compiler translates one representation into another.

A just-in-time compiler, or JIT, performs compilation during program execution.

An ahead-of-time compiler prepares executable code before ordinary runtime execution.

These strategies can coexist.

JavaScript isn't simply interpreted forever.

Nor does every line of JavaScript necessarily become highly optimized machine code before its first execution.

A modern engine can begin with relatively inexpensive execution machinery and spend additional optimization effort on code that proves important.

## 3. The engine learns from behavior

Our pricing function receives quotation objects.

At first, every object has the same predictable structure.

The engine observes many calls.

It learns that the function repeatedly accesses properties in familiar locations, performs numeric operations, and returns a numeric result.

The engine may optimize that common pattern.

Instead of repeatedly performing a fully general property lookup, it can generate a faster path based on assumptions about the objects it has observed.

But assumptions require checks.

Now the new supplier begins constructing quotation objects differently.

The fields still exist.

The values are still valid.

But some objects have different internal shapes.

The engine's previously useful assumptions may no longer apply to every call.

It can fall back to more general behavior, create new optimized paths, or discard an optimization and continue through another execution tier.

The program remains correct.

Its execution cost can change.

**A JIT optimizes observed behavior under guarded assumptions. It doesn't promise that every logically equivalent input representation costs the same amount to process.**

## 4. There are two ways to wait for the processor

Now imagine that the price calculation performs a million arithmetic operations.

The processor is extremely fast.

Why might the calculation still take a noticeable amount of time?

Because performing arithmetic isn't the only cost.

The processor needs data.

It needs to fetch instructions.

It may need to retrieve objects from memory.

And memory isn't uniformly fast.

A value already in a CPU register is much cheaper to access than data requiring a trip through several cache levels to main memory.

A calculation involving scattered objects can spend substantial time waiting for data.

Another implementation using compact, contiguous values may run much faster even when its arithmetic is similar.

This is why algorithmic complexity isn't a complete performance model.

Two implementations can both perform work proportional to the number of quotations and still have very different execution costs.

## 5. The processor also makes predictions

Modern processors don't necessarily wait for one instruction to finish completely before beginning all work related to subsequent instructions.

They use pipelines, branch prediction, and other techniques to keep execution resources busy.

Imagine a conditional statement executed a million times.

If the outcome is highly predictable, the processor may efficiently prepare subsequent work.

If the outcomes are difficult to predict, the processor may occasionally pursue the wrong path and discard speculative work.

Likewise, dependencies between instructions can limit how much work the processor executes concurrently.

The source code doesn't reveal these costs directly.

A short function can interact poorly with the processor's execution machinery.

A longer-looking function can compile into efficient machine instructions.

## 6. The performance detective's first mistake

Our engineer sees the slow pricing calculation and immediately starts rewriting loops.

But what if the actual delay comes from database queries?

Or garbage collection?

Or a CPU quota?

Or a large object allocation that didn't exist before?

Optimizing the multiplication operator won't help.

The first responsibility is to establish where time is actually spent.

This requires distinguishing elapsed time from CPU time, and source-code appearance from executed work.

A profiler can show which functions consume CPU samples.

A benchmark can compare controlled implementations.

But both need careful interpretation.

Measurements can be distorted by warmup, garbage collection, scheduling, input distribution, and the benchmark itself.

### The journey we'll investigate

```text
TypeScript source
       |
       v
JavaScript output
       |
       v
Parsing and bytecode
       |
       v
Interpreter / JIT tiers
       |
       v
Machine instructions
       |
       v
Registers, caches, memory
       |
       v
Measured runtime behavior
```

The specific intermediate stages vary across engines and versions. The diagram expresses the conceptual journey.

### Three questions before the Deep Dive

1. Why can a JavaScript engine optimize a function using assumptions that it later has to abandon?
2. Why can two algorithms with the same Big O complexity run at different speeds?
3. Why should a senior engineer profile the application before rewriting a slow function in another language?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The Pricing Function That Became Slower Without Changing

Our hotel platform calculates prices for a large catalogue.

Originally, the quotation-normalization layer constructed objects consistently.

The pricing engine received predictable numeric fields.

A supplier integration introduces a new normalization path. The output still satisfies the application's semantic contract, but some objects are constructed with different property insertion orders and optional fields.

In a controlled benchmark, the pricing calculation now consumes substantially more CPU time.

The team suspects V8 optimization behavior.

That's a reasonable hypothesis, but not yet a diagnosis.

We need evidence.

The function may have become slower because of object shapes, allocation overhead, changed input distributions, cache locality, or an unrelated execution cost.

To investigate, we'll trace the machinery from JavaScript source to actual processor behavior.

## 2. Source Code, Intermediate Representations, and Machine Code

We established in L01 that a programming language specifies semantics while an implementation chooses how to execute them.

Now examine the implementation pipeline more closely.

Consider a TypeScript function calculating a discounted price.

The source includes type annotations.

The TypeScript toolchain checks or transforms the program according to its configuration.

The resulting JavaScript no longer contains ordinary TypeScript type annotations.

A JavaScript engine receives executable JavaScript source.

### Parsing

The engine parses the source into a structured representation.

This identifies expressions, functions, declarations, operators, and control-flow relationships.

Parsing is necessary because the engine can't treat an arbitrary string of source characters as machine instructions.

### Bytecode

V8 commonly compiles JavaScript source into bytecode for its interpreter, Ignition.

Bytecode is a lower-level representation designed for execution by the virtual machine.

It isn't native machine code.

The processor doesn't ordinarily execute Ignition bytecode directly as its own instruction set.

Instead, the interpreter performs the operations described by those bytecodes.

### Intermediate representations

Optimizing compilers commonly use intermediate representations, abbreviated IR.

An IR makes program structure and data relationships available for analysis and transformation.

The compiler can identify operations, control-flow branches, dependencies, and opportunities for simplification.

Some IR forms resemble explicit instruction sequences.

Others use graphs of operations and dependencies.

The exact representation matters to compiler engineers because it affects what optimizations are practical and how much compilation costs.

For application engineers, the important distinction is between the source-language program and the internal forms used to generate executable instructions.

### Machine code

Eventually, some execution path involves native instructions compatible with the processor architecture.

On a typical x86-64 machine, that means x86-64 machine instructions.

On an ARM64 machine, it means ARM64 instructions.

The same JavaScript function can therefore execute through different machine-code implementations on different CPUs while preserving its required language behavior.

**The source describes what the program means; the generated instructions are one implementation of that meaning.**

## 3. The CPU's Immediate World: Instructions and Registers

Let's move to the processor itself.

A CPU executes instructions from its instruction set architecture, or ISA.

Instructions can perform arithmetic, load or store data, compare values, and control execution.

The processor has registers: small, extremely fast storage locations used during instruction execution.

A calculation may keep intermediate numeric values in registers rather than repeatedly writing them to main memory.

This is one reason compilers care about register allocation.

### Register allocation

Imagine a function with many intermediate calculations.

The compiler would like to keep frequently used values in registers.

But the number of available registers is limited.

If too many values need to remain live simultaneously, some may need to be stored temporarily in memory.

This is called spilling.

Spilling can introduce extra loads and stores.

Different instruction schedules and register-allocation strategies can therefore affect performance, even when the source-level calculation is identical.

### Instruction selection

The compiler must also choose machine instructions.

A simple arithmetic expression may map efficiently onto hardware instructions.

A dynamic language operation may require type checks, representation conversion, or calls to runtime helpers.

The actual instruction sequence depends on what the compiler knows about the values involved.

This is where JavaScript's dynamic behavior becomes important.

The engine may be able to turn a general numeric-looking operation into efficient specialized instructions—but only when its assumptions are justified and guarded.

## 4. Fetch, Decode, Execute—and Why That's Only the Beginning

A familiar introductory model describes the processor as repeatedly fetching an instruction, decoding it, and executing it.

That model captures the basic idea.

But modern processors are substantially more sophisticated.

They use pipelines so different stages of multiple instructions can overlap.

They may decode instructions into internal micro-operations.

They can execute independent work out of order.

They predict branches and speculatively prepare execution paths.

And they use multiple cache levels to reduce the cost of memory access.

### The pipeline

Imagine processing luggage at an airport.

One worker checks documents.

Another scans bags.

A third loads luggage onto conveyors.

Instead of completing one passenger's entire journey before beginning another, the airport processes multiple passengers through different stages simultaneously.

A CPU pipeline uses a related strategy.

While one instruction is executing, another may be decoded and another fetched.

The goal is to keep execution resources busy.

### Dependencies limit overlap

Suppose instruction B needs the result of instruction A.

B can't use that result before it's available.

Even a processor capable of executing many instructions concurrently remains constrained by data dependencies.

A long dependency chain can limit performance.

This helps explain why more execution resources don't always translate into proportionally faster processing.

## 5. The Memory Hierarchy: Arithmetic Is Cheap, Waiting Is Expensive

Imagine our price calculation processes one million offers.

Each offer contains prices, dates, flags, and metadata.

The arithmetic itself may be simple.

But the program needs to retrieve those values.

Modern processors use a memory hierarchy.

Registers provide extremely fast access to a small number of values.

CPU caches provide progressively larger but generally slower storage levels.

Main memory offers much greater capacity but higher access latency.

The details vary by processor architecture.

The principle remains: **where data is located affects how expensive it is to use**.

### Cache locality

Suppose one implementation stores prices in a compact numeric array.

The processor accesses elements in sequence.

This can benefit from spatial locality: nearby values reside in nearby memory locations.

Hardware prefetching and cache behavior may make sequential access efficient.

Now suppose another implementation stores each price inside a separate nested JavaScript object.

The processor may need to follow references to locate the required values.

The object representation may involve additional metadata and indirections.

That can create more memory traffic and less predictable access patterns.

The second implementation isn't necessarily slow in every workload.

But it may perform more work to retrieve each value.

### Temporal locality

If an application repeatedly uses the same small set of data, that data may remain in cache.

An operation using recently accessed values can be faster than one that constantly touches new memory locations.

This explains why a benchmark repeatedly processing one tiny array may behave differently from production code processing millions of distinct records.

### The allocation connection

We studied object allocation and garbage collection in L04.

Now we can see another consequence.

Allocation decisions influence data layout.

Data layout influences cache behavior.

Cache behavior influences CPU execution time.

A program's performance therefore depends partly on how values are represented and accessed, not merely how many arithmetic operators appear in the source.

## 6. Branch Prediction and Speculative Work

Consider a conditional inside the price calculator.

If an offer is refundable, apply one policy.

Otherwise, apply another.

The processor must choose which instructions to execute.

Modern CPUs use branch prediction to anticipate likely control flow.

When a prediction is correct, the processor may keep its pipeline supplied with useful work.

When a prediction is wrong, speculative work along the incorrect path may need to be discarded.

That incurs a cost.

### Predictability matters

Suppose 99 percent of offers use the same pricing branch.

The branch may be highly predictable.

Now consider a dataset where outcomes alternate irregularly.

The processor may have more difficulty predicting which path will be taken.

The performance effect depends on the generated machine code, processor, data distribution, and surrounding workload.

Not every conditional produces a large branch penalty.

Compilers may eliminate branches or use alternative instruction patterns.

But branch behavior is one reason input distribution can influence runtime speed even when the number of processed records remains unchanged.

### Out-of-order execution

Processors may execute ready instructions before earlier instructions whose operands are still unavailable, while preserving the required architectural behavior.

This helps exploit instruction-level parallelism.

But the processor can't arbitrarily violate observable program semantics.

It must still produce results consistent with the relevant execution rules and memory model.

This distinction is especially important when reasoning about concurrency.

Compilers and processors may reorder operations internally, but shared-memory synchronization requires explicit guarantees.

We'll examine those guarantees in CS320.

For now, recognize that the source-code order is not a literal frame-by-frame movie of physical instruction execution.

## 7. One Core, Eight Cores, and the Serial Bottleneck

Suppose our pricing function processes offers sequentially on one JavaScript execution thread.

The machine has eight cores.

Will the function automatically use all eight?

No.

A single serial execution path can't generally execute its own dependent instructions on eight independent cores simultaneously.

Modern CPUs can exploit instruction-level parallelism within a core, but that is different from distributing independent work across cores.

### Parallelizable work

If offers can be processed independently, the application may divide the dataset into chunks and distribute work across multiple execution threads or processes.

That can increase throughput when the workload is sufficiently CPU-bound and parallelizable.

But there are costs.

Workers must be created or maintained.

Data may need to be copied or shared.

Results must be combined.

Synchronization or messaging may be required.

### Amdahl's law

Suppose 80 percent of an operation can be parallelized and 20 percent remains serial.

Even with unlimited processors, the theoretical speedup is bounded by the serial fraction.

In this simplified case, the upper bound is five times, not infinity.

With eight processors, the idealized Amdahl speedup is approximately:

\[
S(8)=\frac{1}{0.2+\frac{0.8}{8}}
\approx 3.33
\]

Real systems also pay communication, scheduling, and memory-contention costs.

Parallel processing may therefore achieve less than the idealized estimate.

The lesson isn't that parallelism is ineffective.

It's that hardware core count doesn't automatically determine application throughput.

## 8. V8's Execution Tiers: Spend Optimization Where It Pays

Now return to JavaScript.

A modern JavaScript engine must solve a difficult engineering problem.

It needs to begin executing code promptly.

But it also wants efficient execution of frequently used functions.

Deep optimization takes time and CPU resources.

Compiling every function with the most expensive optimization pipeline immediately would often waste effort.

Many functions run only once or a few times.

V8 therefore uses multiple execution tiers.

The precise pipeline evolves across engine versions and environments, but several important components illustrate the strategy.

### Ignition

Ignition is V8's bytecode interpreter.

It provides a way to execute JavaScript without requiring expensive machine-code optimization for every function before execution.

### Sparkplug

Sparkplug is a fast baseline compiler.

It can translate bytecode into machine code relatively quickly without applying the full optimization effort of higher tiers.

This can improve execution speed while keeping compilation cost low.

### Maglev

Maglev is an optimizing compiler designed to occupy the space between fast baseline compilation and more expensive peak optimization.

It can use runtime feedback to generate useful specialized code without spending as much compilation time as a deeper optimizer.

### TurboFan and Turboshaft

TurboFan has long served as V8's optimizing compiler infrastructure.

Its implementation has evolved substantially.

Turboshaft is a newer compiler intermediate-representation and backend infrastructure used in V8's optimization pipeline.

Don't memorize an old diagram as though the internal architecture were frozen.

The durable idea is that V8 balances startup cost, compilation effort, runtime feedback, and execution speed through tiered compilation.

### A useful mental picture

```text
JavaScript source
       |
       v
Ignition bytecode
       |
       +--> Interpreter execution
       |
       +--> Sparkplug baseline machine code
       |
       +--> Maglev optimized code
       |
       +--> Higher-tier optimized code
            through evolving V8 infrastructure
```

This is conceptual, not a guarantee that every function passes sequentially through every tier.

The engine makes decisions based on workload behavior, internal heuristics, and implementation details.

**V8 doesn't need to optimize every function maximally. It needs to spend compilation effort where that effort is likely to pay for itself.**

## 9. Runtime Feedback: The Engine Observes Your Program

Our pricing function repeatedly accesses fields such as `baseCents`, `discountRate`, and `nights`.

JavaScript permits objects with many possible shapes and values.

At first glance, this flexibility seems to make efficient optimization difficult.

How can a compiler generate fast property access instructions if an object can gain new properties or change its structure dynamically?

The answer is that the engine uses information gathered during execution.

### Observed types

Suppose the same arithmetic operation consistently receives numbers.

The engine can record that pattern.

An optimizing compiler may choose a representation and machine-code path specialized for numeric operations.

It still needs to preserve JavaScript semantics if another value type appears later.

### Observed object shapes

Suppose the same function repeatedly receives objects with the same property layout.

The engine can use shape information to optimize access.

Instead of a completely general property search every time, it may generate a fast load from a known location after checking that the object has an expected shape.

### Guarded assumptions

The key word is **guarded**.

Optimized code may assume that a certain condition holds because execution feedback indicates it is common.

But the engine needs a way to verify that assumption.

If the condition fails, execution must still produce the behavior required by JavaScript.

That leads us to one of the most important mechanisms in dynamic-language optimization: deoptimization.

## 10. Hidden Classes: Object Shapes Become Execution Information

V8 uses internal structures often called hidden classes, or Maps in V8 terminology, to describe object shapes.

These aren't JavaScript's public `Map` objects.

They're internal metadata describing aspects of an object's layout and properties.

Imagine two quotation objects.

Both contain `baseCents`, `discountRate`, and `nights`.

If they are constructed with compatible layouts, V8 may associate them with the same internal shape.

That can make repeated property access efficient.

### The shape transition

Suppose an object begins empty.

The program adds `baseCents`.

Then `discountRate`.

Then `nights`.

The engine may track transitions between internal shapes as properties are added.

A different construction sequence can lead to different shapes even when the final visible property names are identical.

This is why property insertion order can sometimes matter for performance.

Not because JavaScript says the objects are semantically different, but because the implementation may use different internal layouts.

### Inline caches

An inline cache records information useful for accelerating repeated operations at a particular execution site.

For example, a property access may repeatedly encounter the same shape.

The engine can specialize that operation.

When the site observes several shapes, it may use a polymorphic strategy.

If it encounters many unrelated shapes, a more general lookup path may become preferable.

These strategies are implementation-specific.

The terms monomorphic, polymorphic, and megamorphic describe different degrees of observed variability at an access site.

### Why our supplier integration matters

The old normalization path produced consistent quotation shapes.

The new path produces several shapes.

The same pricing function now encounters more variability.

That could affect inline-cache behavior and optimization opportunities.

But do not jump from that observation to a guaranteed slowdown.

V8 may handle the shapes efficiently.

Other factors may dominate.

**Object-shape variability is a performance hypothesis to test, not a universal reason to rewrite every object constructor.**

## 11. Deoptimization: The Engine Can Change Its Mind

Suppose V8 has optimized the pricing function for a common object shape.

Then it encounters a quotation with a different shape.

What happens?

The engine must preserve correct JavaScript behavior.

If the optimized code's assumptions no longer hold, V8 may use a fallback path or deoptimize.

Deoptimization transfers execution from optimized code into a representation capable of handling the more general case.

### How can the engine recover the program state?

This is a fascinating compiler problem.

Optimized machine code may have eliminated intermediate objects, reorganized calculations, or stored values in different representations.

To resume execution through a less specialized tier, the engine needs enough metadata to reconstruct the relevant logical execution state.

Modern optimizing compilers generate information that supports this transition.

The implementation is complex, but the principle is straightforward.

The compiler may optimize aggressively only if it can still recover correct observable behavior when an assumption fails.

### Deoptimization isn't necessarily a disaster

A deoptimization event may have a cost.

Repeated instability can affect performance.

But deoptimization is also part of what allows the engine to optimize dynamic code safely.

One unexpected shape doesn't automatically mean the entire application becomes slow forever.

The engine may collect new feedback, compile different code, or adapt.

The engineering question is whether these effects meaningfully contribute to a measured performance problem.

### Don't confuse source changes with optimizer changes

Our pricing function's source code is unchanged.

But its runtime inputs have changed.

That can alter optimization decisions.

This is one reason a benchmark based on different data distributions may produce different results without any source-level algorithm change.

## 12. Arrays and Element Representations

V8 also distinguishes different internal representations for array elements.

An array containing small integers can be represented differently from one containing floating-point numbers or object references.

Arrays with densely populated indices may be treated differently from sparse arrays with gaps.

These internal categories are often called elements kinds.

### Packed versus holey

A packed array contains elements in the expected contiguous positions.

A holey array has missing indexed properties.

Why might that matter?

Reading a missing array index can involve additional language semantics, including the possibility of inherited properties.

An engine can often optimize packed arrays more directly because the absence-related cases don't need to be considered in the same way.

### Numeric specialization

An array containing compatible small integers may be optimized differently from one containing general floating-point numbers or objects.

The engine can sometimes store compact numeric representations and avoid unnecessary boxing or general object access.

But implementation details change.

For example, V8's exact elements-kind transition behavior has evolved across versions.

Don't build correctness on the assumption that an array must permanently remain in one internal representation.

### Practical implication

If a critical numerical workload processes millions of values, data representation can matter.

A compact typed array may be worth evaluating.

But rewriting ordinary application arrays into specialized representations without profiling is rarely a sensible first step.

Measure the cost and preserve the application's actual semantics.

## 13. The Performance Investigation: Wall Time, CPU Time, and Waiting

We've now identified several mechanisms that could influence the pricing function.

How do we determine which one actually explains the production slowdown?

Start with measurement boundaries.

### Wall-clock time

Wall-clock time measures elapsed real time.

If an operation starts at 12:00:00 and finishes at 12:00:02, its wall-clock duration is two seconds.

But those two seconds may include CPU execution, waiting for I/O, scheduling delays, timer delays, or time spent blocked on other resources.

### CPU time

CPU time measures time spent executing on processors.

A single-threaded computation may consume roughly one second of CPU time during one second of wall time when continuously running.

A multithreaded process can accumulate more CPU time than wall time because several threads execute simultaneously.

Conversely, a process waiting for a network response may consume very little CPU while wall time advances.

### The difference matters

Suppose our quotation batch takes 500 milliseconds of wall time.

The CPU profiler shows only a small amount of application execution.

The rest may involve database waiting or scheduling.

Optimizing JavaScript arithmetic is unlikely to provide the largest improvement.

Now suppose nearly all the wall time corresponds to active CPU execution in the calculation itself.

Then investigating data representation and optimized code becomes more plausible.

### CPU usage percentages can mislead

A machine with eight cores can show low aggregate CPU utilization while one serial execution path saturates one core.

The process may be CPU-bound even though the system-wide dashboard looks comfortable.

Similarly, a container with a CPU quota can be throttled while the host has idle capacity.

We'll study those operating-system scheduling mechanics in CS320.

For now, don't mistake low average machine CPU utilization for proof that a particular code path isn't CPU-limited.

## 14. CPU Profiling: Look at Executed Work

A CPU profiler samples execution over time and associates samples with functions or call stacks where possible.

This can reveal which code paths consume substantial CPU.

For Node.js, V8 profiling facilities are available through runtime tooling.

A profile can be examined in suitable developer tools.

### The flame graph

A flame graph visualizes sampled call stacks.

Wider regions often correspond to more samples associated with particular call paths under the chosen representation.

The width isn't necessarily the duration of one individual function invocation.

It represents aggregated sampled execution.

A wide function may be invoked many times rather than being individually slow.

### Inclusive versus exclusive time

Inclusive time accounts for a function and the work performed through its callees.

Exclusive time focuses on work attributed directly to the function itself.

If `processBatch` calls `calculatePrice` one million times, `processBatch` may have substantial inclusive cost even if its own loop overhead is small.

The distinction helps identify where optimization effort should go.

### The profiler doesn't show all waiting

A CPU profiler focuses on active execution.

A process waiting for a network response may not accumulate many JavaScript CPU samples.

That doesn't mean the request was fast.

It means the performance problem may be outside the sampled CPU execution path.

Combine CPU profiling with wall-clock timing, application spans, event-loop measurements, and relevant I/O metrics.

**Profile the resource you suspect is limiting the operation. Don't ask a CPU profiler to explain every kind of latency.**

## 15. Microbenchmarks: A Laboratory Can Lie

Suppose we want to compare two quotation representations.

We write a small benchmark.

Version A uses homogeneous objects.

Version B uses several different object shapes.

The benchmark reports that A is three times faster.

Should we immediately restructure production data?

No.

We first need to verify that the benchmark measured the intended work.

### Warmup

A JavaScript function may execute through different tiers over time.

The first invocation can include parsing, compilation, and initialization costs.

Later invocations may benefit from optimized code.

If the benchmark measures only the first call, it may primarily measure startup behavior.

If it measures only a highly warmed-up loop, it may ignore costs relevant to short-lived processes.

Both measurements can be useful, but they answer different questions.

### Dead-code elimination

Suppose the benchmark computes a price but never uses the result.

An optimizing compiler may remove unnecessary calculations if it can establish that they have no observable effect.

The benchmark might report astonishing performance because the intended computation was partly eliminated.

A reliable benchmark must preserve meaningful observable results without introducing a dominant measurement overhead.

### Constant inputs

If every iteration receives the same values, the optimizer may discover opportunities that don't exist with varied production data.

This can be useful for measuring a specific fast path.

But it may not represent the actual workload.

### Garbage collection

One benchmark may allocate substantially more memory than another.

The measured time may include different garbage-collection costs.

The results can be valid, but you need to understand what they include.

### Measurement overhead

Timing each individual tiny operation can add significant overhead relative to the operation itself.

A better approach often measures batches of work and divides by a meaningful count, while preserving the result.

### Environmental noise

CPU frequency scaling, background processes, thermal limits, container quotas, and operating-system scheduling can influence measurements.

Use multiple runs.

Report distributions rather than one lucky number.

And benchmark the deployed runtime version and representative hardware where possible.

## 16. The Controlled Experiment That Settles the Argument

Let's return to our supplier integration.

We now have two hypotheses.

The first says the new supplier's object construction patterns create more shape variability and reduce optimization efficiency.

The second says the new supplier simply produces a larger or more complex workload.

How do we distinguish them?

Create controlled datasets containing the same number of quotations and equivalent numeric values.

Construct one dataset with consistent object layouts.

Construct another with the variations observed in production.

Run the same calculation against both.

Measure wall time and CPU time under comparable conditions.

Collect a CPU profile.

Repeat across fresh processes and steady-state runs.

### What would support the shape hypothesis?

A measurable performance difference that persists under comparable input sizes and numeric distributions would be consistent with the hypothesis.

Profiling might reveal greater cost around property access, generic operations, or runtime execution paths.

V8 diagnostic output may reveal optimization or deoptimization behavior under suitable tooling, although such internal tracing is version-specific and not always needed.

### What would weaken it?

If performance is nearly identical under controlled shapes, the shape differences may not be important.

If the new supplier produces more quotations, more allocations, or additional validation work, those may be the actual reasons for increased CPU usage.

If the original benchmark used different warmup or process states, the comparison may be invalid.

### The actual fix

In our fictional investigation, controlled measurements reveal that the new normalization path produces inconsistent object layouts and incurs additional property-access overhead in the critical loop.

The team changes the normalization boundary so the pricing engine receives a stable internal representation.

This reduces shape variability and simplifies downstream assumptions.

The improvement is measured using the production-like input distribution.

Importantly, the change also improves code organization.

The pricing calculation no longer needs to understand supplier-specific representation differences.

The team didn't rewrite the system in another language.

It corrected the data boundary that was making the runtime work harder.

### Don't generalize the result too far

This case doesn't prove that all JavaScript objects must share identical shapes.

Nor does it establish that stable shapes always produce dramatic speedups.

V8's optimizations are sophisticated and workload-dependent.

The lesson is to recognize a plausible mechanism, construct an experiment that isolates it, and measure whether it matters.

## 17. Throughput and Latency Are Different Performance Questions

Suppose our pricing service handles one thousand batches per minute.

We optimize the calculation and reduce CPU time per batch.

Does user-visible latency necessarily fall by the same percentage?

No.

The request might also spend time waiting for database queries, network responses, and other dependencies.

If CPU calculation was only a small portion of the critical path, optimizing it may produce limited latency improvement.

### Throughput

Throughput measures work completed per unit time.

Reducing CPU cost per quotation can improve maximum processing capacity if CPU was the limiting resource.

### Latency

Latency measures the time taken for an individual operation.

A lower CPU cost can improve latency, but the effect depends on where the time was spent and how the system behaves under load.

### The utilization effect

A small reduction in CPU demand can produce a large latency benefit when a system operates near saturation.

Why?

Because queues can grow rapidly when work arrives nearly as fast as the system can process it.

Reducing the service time slightly may lower utilization enough to reduce waiting substantially.

This is an important bridge between runtime optimization and queueing theory.

We'll study the deeper models in the performance-engineering course.

For now, remember that a benchmark showing ten percent faster computation doesn't automatically translate into ten percent faster HTTP responses.

The bottleneck and workload determine the result.

## 18. What AI-Generated Code Changes—and What It Doesn't

Modern development increasingly involves code generated or modified with AI assistance.

This can make implementation faster.

It can also make performance assumptions easier to overlook.

A generated function may be correct and readable while allocating unnecessary arrays.

A refactor may introduce repeated conversions.

A helper abstraction may hide additional work inside a hot loop.

A seemingly elegant expression may result in different runtime behavior under real data distributions.

The correct response is not to distrust every generated line.

It's to apply the same engineering discipline to generated and handwritten code.

### Review semantics first

Does the transformation preserve the intended behavior?

Are numeric and data-representation assumptions explicit?

Are external values validated?

### Review algorithmic complexity

Does the new implementation perform substantially more work as input size grows?

An algorithmic improvement usually matters more than a small machine-level optimization.

### Review allocation and data layout

Does the hot path create or retain significantly more objects?

Are large datasets processed in bounded batches?

### Measure the real application

Does profiling show the proposed optimization addresses the actual bottleneck?

Does the improvement survive representative data and production-like conditions?

Generated source code is still source code.

The processor executes its resulting machine instructions, not the aesthetic intentions behind the original text.

## 19. The Oral Examination

Answer these aloud before reading the solutions. The objective is to explain execution mechanisms, not memorize optimization jargon.

### Challenge 1 — The Same Algorithm, Different Speed

A TypeScript pricing function hasn't changed, but a new integration makes it slower.

List three possible causes that don't require the algorithm's Big O complexity to change.

### Challenge 2 — Compiled or Interpreted?

An engineer says, "JavaScript is interpreted, so it never becomes machine code."

What is wrong with that statement?

### Challenge 3 — The Hidden-Class Hypothesis

Two objects contain the same properties, but their properties were added in different orders.

Why might V8 treat them differently internally?

Why would that not automatically prove one is slower?

### Challenge 4 — The Deoptimization Mystery

V8 has optimized a function based on common observed values.

A new value violates the optimized path's assumptions.

How can the engine preserve correct JavaScript behavior?

### Challenge 5 — Eight Cores, One Busy Thread

A CPU-heavy function saturates one execution thread on an eight-core machine.

The dashboard reports modest aggregate CPU utilization.

Why doesn't the function automatically use the remaining cores?

### Challenge 6 — The Misleading Benchmark

A microbenchmark reports that an implementation performs a billion operations in almost no time.

The result is never used.

Why might the measurement be invalid?

### Challenge 7 — The Memory-Layout Comparison

One program processes prices stored in a compact numeric array.

Another follows references through a large graph of objects.

Both perform a linear number of operations.

Why might their measured execution times differ?

### Challenge 8 — The Profiler Shows Nothing

An HTTP request takes four seconds.

The CPU profile shows little time in the application's handler.

What does that suggest, and what measurements should come next?

## 20. Solutions and Discussion

### Solution 1 — Runtime cost depends on more than asymptotic work

Possible explanations include different object shapes affecting optimization, increased allocation or garbage-collection cost, changed data locality, different input distributions, CPU throttling, or additional hidden work in the surrounding pipeline.

The investigation should isolate these possibilities through representative profiling and controlled comparisons.

### Solution 2 — Modern JavaScript engines use compilation

V8 parses JavaScript, produces bytecode, and can generate native machine code through several compilation tiers.

Some code may execute through the interpreter; other code may execute through baseline or optimizing compiled code.

"Interpreted" is not a complete description of modern JavaScript execution.

### Solution 3 — Internal shape metadata can differ

V8 tracks object structures using internal Maps or hidden classes.

Different construction sequences can lead to different shapes.

That may affect inline caches and optimization opportunities.

But V8 may handle both shapes efficiently, and other costs may dominate.

Only measurement establishes whether the difference matters.

### Solution 4 — Guards and deoptimization preserve semantics

Optimized code can check assumptions about values or object shapes.

If an assumption fails, the engine can use a more general execution path or deoptimize.

Metadata helps reconstruct the relevant execution state so the language's required behavior remains correct.

### Solution 5 — Serial work doesn't distribute itself across cores

A single sequential execution path cannot automatically use all available cores.

Parallel execution requires the workload to be divided into suitable independent pieces and executed through appropriate threads or processes.

That introduces coordination and data-transfer costs.

### Solution 6 — The optimizer may remove unobservable work

If a calculation has no observable effect, an optimizing compiler may eliminate some or all of it.

A benchmark must retain meaningful results and avoid measuring an operation that the compiler has optimized away.

Warmup, measurement overhead, and environmental variation also matter.

### Solution 7 — Locality and representation affect cost

Compact numeric data can benefit from contiguous storage, fewer indirections, and favorable cache behavior.

Object graphs may require pointer chasing, metadata access, or additional loads.

Both programs can have linear time complexity while using different amounts of CPU time and memory bandwidth.

### Solution 8 — The latency may be waiting, not CPU execution

The handler may be waiting on a database, network, timer, lock, or another dependency.

A CPU profile focuses on active execution and may not explain wall-clock waiting.

Measure request spans, dependency latency, event-loop behavior, resource contention, and timeouts to identify the actual delay.

## 21. The Mental Model Worth Keeping

Source code is a description of behavior, not a literal schedule of machine instructions.

Compilers and runtimes transform that description into executable operations.

JIT compilers use runtime observations to optimize common cases while preserving language semantics through guards and deoptimization.

Processors execute those operations using registers, caches, pipelines, speculation, and finite memory bandwidth.

And measured performance depends on algorithms, data representations, runtime behavior, operating-system constraints, and actual workloads.

When code becomes slow, ask:

**What work is the program really doing? Which instructions and memory accesses does that work produce? What does the runtime know about the values? And which measurement proves where time is being spent?**

Those questions are considerably more useful than arguing about whether one programming language is inherently fast.

## 22. Next Lecture — CS220-L06: Managed Runtimes — Node.js, CPython, and the JVM

We've followed one JavaScript program from source code through bytecode, optimization, and machine execution.

Now we'll compare different runtime philosophies.

Node.js combines a JavaScript engine with event-driven host capabilities.

CPython traditionally executes Python bytecode through an interpreter and has historically used a Global Interpreter Lock in ordinary builds, while newer free-threaded configurations change important assumptions.

The JVM uses bytecode, runtime profiling, JIT compilation, managed memory, and a mature concurrency ecosystem.

These runtimes solve different engineering problems.

The next lecture will ask how they manage execution, concurrency, memory, startup costs, and optimization—and why the same workload can behave so differently across them.

We've learned what an execution engine does.

Next we'll compare the machines that programming-language ecosystems build around those engines.

*The spoken lecture ends here. The remaining material is for experiments and screen-based revision.*

---

## Optional Practical Lab — Watch a JavaScript Runtime Execute and Optimize

**Objective:** Measure a CPU-bound function, observe the impact of input representation, produce a CPU profile, and identify misleading benchmarks.

Use a recent Node.js installation. Exact results depend on hardware, operating system, Node.js and V8 versions.

The experiment is deliberately bounded. It doesn't require native compiler tooling or modifications to V8.

### Lab A — Inspect the runtime

Check the Node.js version and its embedded V8 version:

```bash
node --version
node -p "process.versions.v8"
```

Different Node.js versions bundle different V8 releases. Internal optimizers and diagnostic flags may therefore differ.

Do not assume that an experiment produces identical timings on every machine.

### Lab B — Build a CPU-bound pricing calculation

Create `pricing-benchmark.mjs`:

```javascript
import { performance } from "node:perf_hooks";

function calculatePrice(quote) {
  const discounted =
    quote.baseCents * (1 - quote.discountRate);

  return Math.round(discounted) * quote.nights;
}

function homogeneousQuotes(count) {
  return Array.from({ length: count }, (_, index) => ({
    baseCents: 10000 + (index % 250),
    discountRate: (index % 5) / 100,
    nights: (index % 7) + 1,
  }));
}

function variedQuotes(count) {
  return Array.from({ length: count }, (_, index) => {
    const baseCents = 10000 + (index % 250);
    const discountRate = (index % 5) / 100;
    const nights = (index % 7) + 1;

    switch (index % 3) {
      case 0:
        return { baseCents, discountRate, nights };

      case 1:
        return { nights, baseCents, discountRate };

      default:
        return {
          discountRate,
          nights,
          baseCents,
          supplierTag: "partner",
        };
    }
  });
}

function processQuotes(quotes, repetitions) {
  let checksum = 0;

  for (let repetition = 0; repetition < repetitions; repetition++) {
    for (const quote of quotes) {
      checksum += calculatePrice(quote);
    }
  }

  return checksum;
}

function measure(label, quotes, repetitions) {
  // Warm up the measured code path.
  processQuotes(quotes, 10);

  const started = performance.now();
  const checksum = processQuotes(quotes, repetitions);
  const elapsedMs = performance.now() - started;

  console.log({
    label,
    elapsedMs: elapsedMs.toFixed(2),
    checksum,
  });
}

const count = 50_000;
const repetitions = 25;

measure(
  "homogeneous",
  homogeneousQuotes(count),
  repetitions
);

measure(
  "varied-shapes",
  variedQuotes(count),
  repetitions
);
```

Run:

```bash
node pricing-benchmark.mjs
```

Both datasets contain the same number of quotations and equivalent numeric values.

They differ in object construction patterns.

**Question:** Is one consistently faster? Does the difference persist across repeated fresh-process runs?

Do not assume the homogeneous version must win. The actual result depends on V8 and the workload.

### Lab C — Repeat across fresh processes

Run the script several times.

On a Unix-like shell:

```bash
for i in 1 2 3 4 5; do
  node pricing-benchmark.mjs
done
```

On Windows PowerShell:

```powershell
1..5 | ForEach-Object {
    node pricing-benchmark.mjs
}
```

Compare the timing distributions.

Notice whether one run differs substantially from the others.

**Question:** Which environmental or runtime factors could explain variability?

### Lab D — Capture a CPU profile

Node.js provides a built-in CPU-profiler option.

Create a directory:

```bash
mkdir profiles
```

Run the benchmark with profiling enabled:

```bash
node --cpu-prof --cpu-prof-dir=./profiles pricing-benchmark.mjs
```

The runtime should write a `.cpuprofile` file when the process exits normally.

Open the resulting profile using a compatible developer-tool CPU profiler, such as Chrome DevTools.

Look for the calculation and batch-processing functions.

**Questions:**

1. Which functions account for substantial CPU samples?
2. Is most time spent in the calculation or surrounding iteration?
3. What does the profile not tell you about possible network or database waiting?

### Lab E — Compare numeric arrays with objects

Create a second benchmark where prices are stored in a `Float64Array`.

Process the values through a simple numeric loop.

Compare the result with a version using arrays of objects containing equivalent values.

Keep the number of computations and their semantic meaning comparable.

Do not claim the difference is solely due to CPU cache locality unless the experiment isolates competing explanations.

Differences could involve property lookup, allocation, representation, JIT optimization, and memory access.

**Question:** Which performance mechanisms might contribute, and what additional evidence would separate them?

### Lab F — The warmup experiment

Modify `measure()` to record separately:

- The first execution.
- Several warmup executions.
- A later steady-state execution.

Compare the results.

**Question:** Why might a short-lived command-line program and a long-running backend service experience different optimization benefits?

### Lab G — Avoid the dead-code benchmark

Consider this benchmark:

```javascript
function uselessWork() {
  let total = 0;

  for (let i = 0; i < 1_000_000; i++) {
    total += i;
  }

  return total;
}
```

Now compare a benchmark that discards the return value with one that consumes it observably.

Don't assume V8 will eliminate this particular loop in every version or configuration.

Instead, explain which transformations would be legal if the optimizer could prove the work had no relevant observable effects.

**Question:** Why is a benchmark measuring unobservable computation a poor basis for production decisions?

### Lab H — The performance incident report

You receive the following evidence:

- The pricing function's source code didn't change.
- A new supplier normalization path was introduced.
- Input values remain numerically valid.
- The new path constructs objects with several different layouts.
- Controlled profiling suggests increased CPU cost around the pricing loop.
- A rewritten normalization boundary produces a measurable improvement.

Prepare a short engineering report explaining:

1. The leading hypothesis.
2. The controlled experiment.
3. The results that support or weaken the hypothesis.
4. Why a full language rewrite is not justified.
5. How to verify that the optimization improves real production workload behavior.

The answer should discuss execution machinery without claiming that hidden classes are responsible for every JavaScript performance problem.

---

## Further Reading

1. [V8 — Sparkplug](https://v8.dev/blog/sparkplug) — Fast baseline compilation.
2. [V8 — Maglev](https://v8.dev/blog/maglev) — Mid-tier optimizing compilation.
3. [V8 — Leaving the Sea of Nodes](https://v8.dev/blog/leaving-the-sea-of-nodes) — The evolution toward Turboshaft compiler infrastructure.
4. [V8 — Fast Properties](https://v8.dev/blog/fast-properties) — Object layouts and property representations.
5. [V8 — Hidden Classes](https://v8.dev/docs/hidden-classes) — Maps, shape transitions, and optimization.
6. [V8 — Elements Kinds](https://v8.dev/blog/elements-kinds) — Array element representations.
7. [Node.js — Command-Line Options](https://nodejs.org/api/cli.html) — `--cpu-prof` and related profiling options.
8. [Node.js — Flame Graphs](https://nodejs.org/en/learn/diagnostics/flame-graphs) — CPU profiling and interpretation.
9. [MDN — JavaScript Performance](https://developer.mozilla.org/en-US/docs/Learn_web_development/Extensions/Performance/JavaScript) — Practical performance considerations.
10. [Web.dev — Rendering Performance](https://web.dev/articles/rendering-performance) — A browser-oriented example of translating low-level performance into user experience.

---

## Dense Cheatsheet — Interview Glance Card

*This reference is fenced for screen-based revision rather than voice playback.*

```text
CS220-L05 — SOURCE CODE, COMPILERS, JITS, AND CPU EXECUTION

THE EXECUTION JOURNEY

  TypeScript source
    -> Type checking / transformation
    -> JavaScript
    -> Engine parse/bytecode
    -> Interpreter or JIT machine code
    -> CPU instructions
    -> Registers / caches / memory
    -> Observed performance

SOURCE VS MACHINE

  Source:
    Describes program semantics

  Machine code:
    ISA-specific executable instructions

  Different implementations may preserve
  the same semantics with different costs.

COMPILATION

  Parsing:
    Source -> structured program representation

  IR:
    Intermediate representation for analysis/optimization

  AOT:
    Compile before ordinary program execution

  JIT:
    Compile during program execution

  Interpretation:
    Execute through interpreter machinery

  Compiled vs interpreted is not binary.

CPU

  ISA:
    Processor instruction set

  Registers:
    Small, fast working storage

  Pipeline:
    Overlap instruction-processing stages

  Branch prediction:
    Predict likely control flow

  Out-of-order execution:
    Execute available independent instructions
    while preserving required architectural behavior

  Register spilling:
    Temporarily place live values in memory

MEMORY HIERARCHY

  Registers -> CPU caches -> main memory

  Access costs vary substantially.

  Spatial locality:
    Nearby memory accessed close together

  Temporal locality:
    Recently used memory accessed again

  Contiguous data can outperform pointer-heavy
  representations in suitable workloads.

SERIAL VS PARALLEL

  Eight cores do not automatically accelerate
  one serial JavaScript execution path.

  Parallelization requires independent work,
  execution resources, and coordination.

AMDAHL'S LAW

  S(N) = 1 / (s + (1-s)/N)

  s = serial fraction
  N = processor count

  Parallel speedup bounded by serial work
  plus practical coordination overhead.

V8 EXECUTION TIERS

  Ignition:
    Bytecode interpreter

  Sparkplug:
    Fast baseline compiler

  Maglev:
    Mid-tier optimizing compiler

  TurboFan / Turboshaft:
    Higher-tier optimization infrastructure

  Actual tiering varies by version and workload.
  Not every function uses every tier.

RUNTIME FEEDBACK

  Observed value types
  Observed object shapes
  Repeated property access patterns

  JIT may specialize based on feedback.

HIDDEN CLASSES / MAPS

  Internal V8 object-shape metadata
  Not JavaScript's public Map collection

  Property construction order can affect shape
  Shape checks can enable fast property loads

INLINE CACHES

  Monomorphic:
    One common shape

  Polymorphic:
    Several observed shapes

  Megamorphic:
    Many shapes / more general handling

  Shape variation may affect performance,
  but only measurement establishes its impact.

DEOPTIMIZATION

  Optimized code uses guarded assumptions.

  If assumptions fail:
    Fallback or deoptimization
    Reconstruct relevant execution state
    Preserve JavaScript semantics

  Deoptimization is normal runtime machinery.

ARRAY REPRESENTATIONS

  Packed vs holey elements
  Integer / double / object element kinds
  Dense vs sparse representations

  More specialized representation may improve
  performance in suitable workloads.

  Internal details are version-dependent.

PERFORMANCE MEASUREMENTS

  Wall time:
    Elapsed real duration

  CPU time:
    Actual processor execution

  Throughput:
    Work completed per unit time

  Latency:
    Duration of one operation

  Low average host CPU != not CPU-bound.

CPU PROFILING

  Samples executed call stacks
  Identifies active CPU hotspots
  Does not explain all I/O waiting

  Inclusive time:
    Function plus callees

  Exclusive time:
    Function's directly attributed work

  Flame graph width:
    Aggregated samples, not one call's duration

MICROBENCHMARK TRAPS

  Cold start vs warmed-up tiers
  Dead-code elimination
  Constant inputs
  Unrealistic data distribution
  GC differences
  Timing overhead
  CPU frequency / background load
  Container throttling
  One lucky run

  Use representative data and repeated runs.

INVESTIGATION METHOD

  1. Confirm slowdown and business impact
  2. Separate wall time from active CPU
  3. Collect CPU profile
  4. Form competing hypotheses
  5. Control data distribution and work volume
  6. Benchmark comparable implementations
  7. Preserve observable results
  8. Verify improvement in realistic workload

AI-GENERATED CODE

  Correct-looking source can hide:
    Extra allocations
    Poor data layouts
    Repeated conversions
    Accidental O(n²) work
    Hot-loop abstractions

  Review semantics, complexity, profiling evidence.

SENIOR QUESTIONS

  What work actually executes?
  Is the program CPU-bound or waiting?
  Which data representations reach the hot path?
  What has the JIT learned about those values?
  What does the CPU profiler show?
  Does the optimization improve useful throughput?

SENIOR LINE

  "I don't infer performance from source-code appearance
   or language labels. I distinguish compilation tiers,
   generated execution costs, data locality, CPU time,
   wall time, and workload distribution, then validate
   optimizations with representative profiling."
```
    