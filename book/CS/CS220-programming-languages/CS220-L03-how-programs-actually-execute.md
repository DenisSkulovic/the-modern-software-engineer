---
id: CS220-L03
course: CS220
title: "How Programs Actually Execute"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [CS101-S08]
prev: CS220-L02
next: CS220-L04
---





# CS220 — Programming Languages, Memory, and Execution
## Lecture 03: How Programs Actually Execute

*The machinery beneath the code: instructions, registers, caches, execution pipelines, JIT compilation, speculative optimization, and the art of understanding what a computer is actually doing.*

**Estimated study time:** 75–95 minutes, including practical experiments.

---

### How to listen to this lecture

Written for continuous listening first, then for on-screen re-reading. The theme today is simple: **what the machine is actually spending time doing.** Bold takeaways mark ideas worth pausing on, and short diagrams show the path from source to silicon. Near the end, answer the challenges **out loud** before reading the solutions. The timing and profiling experiments live after the spoken lecture ends — keep them for a screen session.

By the end, you should be able to explain why a fast CPU can still wait on memory, how pipelines and speculation hide latency until dependencies intervene, why V8 can speed up or deoptimize the same function, how wall-clock time differs from CPU time, and why measuring the hot path beats rearranging code by folklore.

---

# 1. The Mysterious Case of the Slower Code

It's Monday morning, and your team has deployed a modest update to a hotel reservation service.

The change is almost embarrassingly small.

Previously, your application calculated room prices from objects like this:

```typescript
{
  roomId: "R-101",
  basePrice: 120,
  tax: 24,
  discount: 10
}
```

A new integration partner has been added, and its pricing data looks slightly different.

Some records arrive without a discount field. Others contain additional metadata. A few contain numerical values represented as strings.

The developer handling the integration decides to normalize everything in a shared processing function.

It seems harmless.

The code remains readable.

The unit tests pass.

The application produces correct invoices.

Yet after deployment, something strange happens.

A CPU-heavy pricing operation takes substantially longer to complete.

The number of records hasn't increased.

The algorithm is still O(n).

The server hardware hasn't changed.

Even the business logic looks almost identical.

So why is execution slower?

An obvious possibility is that the new normalization code simply performs more work. But suppose profiling eventually reveals something subtler: a previously optimized operation is now taking a more general execution path because the runtime is encountering a wider variety of values and object structures.

That possibility is particularly interesting in JavaScript.

Because JavaScript engines don't always execute a particular function using exactly the same machine instructions throughout the lifetime of the program.

They can observe execution, learn about the values being processed, generate specialized machine code, and later abandon some of those optimizations when their assumptions stop being valid.

In a sense, the engine is constantly trying to make educated guesses about your program.

And when those guesses are useful, JavaScript can execute remarkably quickly.

But before we explore that machinery, there's a more fundamental question.

**What does it actually mean for a computer to execute a program?**

We spend our professional lives writing code, but the CPU never sees our TypeScript functions, interfaces, promises, or beautifully named domain objects in their original form.

Somewhere between our source code and the physical processor, an astonishing amount of translation takes place.

Today, we're going to follow that journey.

---

# 2. Your CPU Has Never Heard of TypeScript

Consider a simple function:

```typescript
function calculateTotal(
  basePrice: number,
  tax: number
): number {
  return basePrice + tax;
}
```

From your perspective, this is a function accepting two numbers and returning their sum. From the perspective of a JavaScript runtime, it is a piece of executable behavior with various language-level rules and assumptions.

From the perspective of a CPU, it eventually becomes a sequence of machine instructions operating on registers and memory. Let's strip away the abstractions.

## The CPU's instruction set

A conventional processor understands a defined collection of machine instructions. This collection is called an **instruction set architecture**, or ISA.

Examples include:

- x86-64, widely used in desktop computers and servers.
- ARM64, widely used in smartphones, Apple Silicon computers, and an increasing number of servers.
- RISC-V, an open instruction set architecture used in various systems.

Different instruction sets express operations differently, but they generally provide mechanisms for:

- Moving information between registers and memory.
- Performing arithmetic and logical operations.
- Comparing values.
- Changing execution flow.
- Interacting with privileged system functionality.

The processor does not understand the concept of a hotel reservation; it understands instructions. To see the distinction, imagine a simplified instruction sequence:

```text
LOAD  R1, [price]
LOAD  R2, [tax]
ADD   R3, R1, R2
STORE [total], R3
```

This is illustrative pseudocode, not exact x86-64 or ARM64 assembly. The meaning:

1. Load the price into a register.
2. Load the tax into another register.
3. Add the values.
4. Store the result.

A real JavaScript implementation of our original function may involve much more than these four operations. The engine may need to establish the types and representations of the operands, account for JavaScript's numerical rules, manage function invocation, and interact with runtime machinery.

An optimizing compiler may eliminate much of that overhead when conditions permit. But at the processor level, executable behavior ultimately depends on machine instructions.

## Registers: The CPU's immediate workspace

A register is a small storage location inside the processor. Registers are used to hold values that the CPU is actively manipulating. They are extremely fast compared with retrieving arbitrary information from main memory.

Imagine a chef preparing a meal. The kitchen contains enormous refrigerators, cupboards, and storage rooms. But the ingredients currently being chopped or mixed are kept immediately at hand.

Registers play a similar role: they're the CPU's immediate working storage. But registers are limited. You can't fit your entire PostgreSQL database into them. You can't even fit a substantial application object graph into them. So the processor needs to move information between registers and other levels of memory.

And that's where execution becomes more complicated.

---

# 3. The Fetch–Decode–Execute Cycle

At a simplified level, a CPU repeatedly performs three activities.

**Fetch an instruction. Decode what it means. Execute the required operation.**

Imagine a tiny program:

```text
1. LOAD R1, 5
2. LOAD R2, 7
3. ADD  R3, R1, R2
4. STORE result, R3
```

The processor needs to know which instruction comes next. Architectures have a register commonly described as the **program counter**, or instruction pointer, which identifies the current or next instruction location according to the architecture's execution model.

The processor fetches the instruction, interprets it, performs the operation, and continues. When the program reaches a conditional branch, the next instruction depends on some condition. For example:

```typescript
if (availableRooms > 0) {
  confirmReservation();
} else {
  rejectReservation();
}
```

At the machine level, this ultimately involves comparisons and control-flow instructions. The CPU doesn't understand a hotel being sold out. It understands a condition and a possible change in execution flow.

## Is that really all a modern CPU does?

Not remotely. The fetch–decode–execute model is a useful foundation, but modern processors are extraordinarily sophisticated. They can have multiple execution units. They can work on several instructions simultaneously.

They can predict future branches. They can reorder certain operations internally. They can execute instructions speculatively before knowing whether the results will ultimately be needed.

They use several levels of cache. They maintain sophisticated mechanisms for tracking dependencies and preserving architectural behavior.

So the simple picture:

"Fetch one instruction, finish it completely, fetch the next instruction"

isn't how a modern high-performance CPU necessarily operates internally. To understand why, let's investigate a central problem in computer architecture.

**What should the CPU do while it's waiting?**

---

# 4. A Processor That Executes Billions of Instructions Can Still Spend Time Waiting

Imagine that the CPU needs to calculate `const result = customer.balance + customer.creditLimit`.

The arithmetic is trivial. Adding two numbers is not particularly demanding. But the values must be available. Suppose the relevant customer data isn't currently in the CPU's cache.

The processor may need to retrieve it from another level of the memory hierarchy. That retrieval can take far longer than a simple arithmetic operation. And this produces a rather counterintuitive situation.

A powerful processor capable of executing enormous numbers of operations per second may be delayed by the comparatively mundane task of obtaining the next piece of data. This is one reason memory organization matters so much.

## The memory hierarchy

A simplified modern memory hierarchy looks like this: registers to L1 to L2 to L3 or last-level cache to main RAM to persistent storage — tiny and fastest at one end, huge and slowest at the other.

This is a conceptual hierarchy. Actual hardware designs vary, and persistent storage is accessed through a different set of mechanisms from ordinary cache-backed memory loads. The general pattern is that storage closer to the execution units tends to be faster and smaller. Storage farther away tends to be larger and slower: registers are tiny, L1 is small and fast, L2 is typically larger, a shared last-level cache may hold many megabytes, RAM holds gigabytes, and persistent storage potentially terabytes. But the difference isn't merely capacity.

**The time required to access the information can differ dramatically.**

That's why a processor's theoretical arithmetic capability doesn't directly determine the speed of an application. The processor needs to be supplied with instructions and data.

## Why caches exist

Suppose you're iterating through an array.

```typescript
let total = 0;

for (let i = 0; i < values.length; i++) {
  total += values[i];
}
```

The CPU accesses consecutive elements. Modern memory systems commonly transfer data in blocks called cache lines. A frequently used cache-line size on contemporary desktop and server CPUs is 64 bytes, although architectures differ.

If the application accesses one array element, nearby elements may arrive in the same cache line. When the program accesses the next element, some of the required data may already be in a fast cache.

This is **spatial locality**. Now compare that with a linked list. Each node points to the next node. Those nodes may be scattered across memory.

The CPU needs the next pointer before it knows where to find the following node. That can introduce a chain of dependent memory accesses. Both algorithms may be O(n).

But their actual execution characteristics can be quite different. We discussed this in CS110-L03, but now we can understand the physical reason. The algorithm isn't simply performing abstract operations.

It's asking a real processor to retrieve data from real memory. And the arrangement of that data matters.

---

# 5. Why the CPU Tries to Predict the Future

Let's return to a conditional statement.

```typescript
if (reservation.status === "confirmed") {
  sendConfirmation();
} else {
  handleIncompleteReservation();
}
```

The CPU eventually needs to execute instructions corresponding to one branch or the other. But modern processors use pipelines. Different stages of instruction processing can overlap.

While one instruction is executing, other instructions may already be decoded or prepared, which improves throughput. However, a branch creates uncertainty. Which instruction should come next? If the processor waits until every branch condition is fully resolved before preparing subsequent instructions, it may waste execution capacity.

So modern processors often make predictions.

## Branch prediction

Suppose your application processes one million reservations. Ninety-nine percent are confirmed; only one percent are incomplete. The CPU may learn that a particular conditional branch usually follows the confirmed path. It can predict that outcome and begin preparing subsequent operations.

When the prediction is correct, the processor avoids some of the delay associated with waiting for the branch condition. But what happens when the prediction is wrong? The processor may have to discard speculative work and resume along the correct path.

This is called a **branch misprediction**, and it introduces overhead. The exact cost depends on the processor, pipeline, surrounding instructions, and other architectural details. The interesting point is that two programs performing similar high-level operations can have different execution costs because their branches behave differently.

## Predictability matters

Imagine two loops. The first processes data where nearly every condition is true. The second processes data where the outcome is difficult to predict. Depending on the processor and generated machine code, the second loop may experience more branch mispredictions.

That can make it slower, even if both loops perform the same number of iterations. But don't turn this into a universal rule that every unpredictable condition causes a performance problem. Optimizing compilers can sometimes eliminate branches.

Some operations use conditional moves or vectorized instructions. Modern branch predictors are sophisticated. And in many applications, branch prediction is irrelevant compared with database or network latency.

The useful lesson is broader:

**The physical execution cost of an algorithm depends partly on how predictable its control flow and data access patterns are.**

This is one reason real performance engineering requires measurement. Big O can't tell you how a branch predictor will behave.

---

# 6. Out-of-Order Execution: The CPU Doesn't Always Do Things in Written Order

Here's another interesting surprise.

Consider these conceptual operations:

```text
A = load value from memory
B = calculate 10 + 20
C = calculate A * 2
D = calculate B + 5
```

Operation C depends on A. But B and D do not depend on A. Suppose the memory load in A is slow.

Does the CPU need to sit completely idle until A finishes? Not necessarily. A modern out-of-order processor may execute independent instructions while waiting for others to complete. It can calculate B, then D. Meanwhile, A may still be waiting for data. Once A completes, C can proceed.

This is **out-of-order execution**. The processor internally rearranges the execution of certain operations to keep its execution units productive. But there are important limits. It must preserve the program's required architectural behavior.

It cannot arbitrarily violate dependencies or externally observable ordering guarantees. A useful distinction is between:

- The order in which instructions appear in the program.
- The order in which internal execution work occurs.
- The order and state that the architecture guarantees will be observable.

These are not always identical.

## Why this matters

Imagine a computation where every operation depends on the previous result.

```typescript
let value = 1;

for (let i = 0; i < 1_000_000; i++) {
  value = transform(value);
}
```

Each iteration requires the preceding result. That dependency limits how much work can be performed simultaneously. Now imagine processing one million independent values.

```typescript
for (let i = 0; i < values.length; i++) {
  values[i] = transform(values[i]);
}
```

If the transformation is suitable and the implementation permits it, the processor or compiler may be able to exploit more parallelism. Different values don't necessarily depend on one another. This can enable instruction-level parallelism, vectorization, or other optimization strategies.

Of course, JavaScript semantics, the chosen data representation, and the generated machine code determine what actually happens. But the general idea is important.

**The dependency structure of a computation can determine how effectively a processor uses its execution capabilities.**

This connects directly to the performance mystery from CS110-L03. A program can leave substantial hardware capacity unused because its critical operations depend on one another. Adding more cores doesn't automatically remove those dependencies.

---

# 7. One Core, Eight Cores, and the Illusion of Infinite Parallelism

Let's imagine a service performing a CPU-heavy calculation. The workload takes ten seconds on one core. You have access to a machine with eight cores.

Can you reduce the execution time to 1.25 seconds simply by using all eight? Only if the work can be divided appropriately, the parallel execution is efficient, and coordination costs are negligible. Real workloads rarely satisfy all those conditions.

This leads us to a famous concept called **Amdahl's law**.

## The serial portion of a program

Suppose 90% of a program's execution time can be parallelized. The remaining 10% must remain serial. That serial portion might involve:

- Initialization and coordination.
- A dependency chain.
- Some unavoidable sequential algorithm.
- Final combination of results.

Now imagine distributing the parallelizable work across eight processors. The simplified speedup formula is:

`Speedup = 1 / ((1 - P) + P / N)`

Where:

- `P` is the fraction of execution time that can be parallelized.
- `N` is the number of processors.

For our example, `P = 0.9` and `N = 8`:

`1 / (0.1 + 0.9 / 8) ≈ 4.71`

An eight-core machine gives us a theoretical speedup of about 4.7 times under these assumptions. Not eight times. And actual performance can be worse because parallelism introduces overhead. Now imagine an unlimited number of processors. The parallelizable portion could theoretically approach zero execution time.

But the remaining 10% serial portion would still exist. So the maximum speedup approaches:

`1 / 0.1 = 10`

Ten times. Not infinity. That's Amdahl's law.

## Why this is useful outside academic parallel computing

Consider a Node.js endpoint.

It spends:

- 10 milliseconds validating a request.
- 400 milliseconds waiting for a database.
- 20 milliseconds processing the result.
- 30 milliseconds waiting for another service.
- 5 milliseconds serializing the response.

Suppose you make the 20-millisecond processing step ten times faster. You've saved 18 milliseconds. That's an improvement. But the endpoint originally took about 465 milliseconds. Now it takes about 447 milliseconds. The overall improvement is modest.

This is the same general reasoning behind Amdahl's law, although the example concerns a serial latency breakdown rather than parallel processors. Optimizing a small portion of the total work cannot produce an enormous improvement in overall response time.

That sounds obvious. Yet software teams routinely spend days optimizing functions that account for a tiny fraction of the actual latency.

The better question is:

**What portion of the total execution or response time can this change actually affect?**

That question can save a tremendous amount of wasted engineering effort.

---

# 8. Now Enter V8: The Engine That Learns About Your Code

So far, we've been discussing processors in general.

Let's return to JavaScript.

The CPU doesn't execute TypeScript interfaces or JavaScript source directly.

A JavaScript engine has to translate the program's behavior into executable operations.

In Node.js and Google Chrome, that engine is V8.

V8 is a sophisticated runtime containing several execution tiers.

The important design challenge is balancing two competing goals.

**Start executing code quickly.**

**Execute frequently used code as efficiently as possible.**

Those goals are not identical.

An aggressive optimizing compiler may produce excellent machine code, but compilation itself consumes time and CPU resources.

If a function runs only once, spending substantial time optimizing it could be counterproductive.

Conversely, if a function executes millions of times, investing in optimization may pay off handsomely.

Modern V8 addresses this with a multi-tiered execution system.

## The simplified V8 journey

Consider our pricing function:

```javascript
function totalPrice(room) {
  return room.basePrice + room.tax;
}
```

When V8 encounters the function, it parses the source and generates an internal representation.

A simplified progression is:

```text
       JAVASCRIPT SOURCE
              |
              v
         Parsing / AST
              |
              v
       IGNITION BYTECODE
              |
              v
        Initial execution
              |
              v
       Runtime feedback
              |
       +------+------+
       |             |
       v             v
    SPARKPLUG       MAGLEV
   Baseline code   Mid-tier optimization
                      |
                      v
             TURBOFAN / TURBOSHAFT
                Top-tier optimization
```

This is a conceptual map, not a requirement that every function passes through every tier in exactly that order.

The engine's decisions depend on runtime configuration, observed behavior, compilation budgets, and other implementation details.

But the main execution tiers are useful to understand.

### Ignition

Ignition is V8's bytecode interpreter.

It allows JavaScript to begin executing without first waiting for expensive optimization.

It also participates in gathering information that later compilation stages can use.

### Sparkplug

Sparkplug is a fast baseline compiler.

It can turn bytecode into machine code relatively quickly.

The objective is to improve execution speed without paying the full cost of sophisticated optimization.

### Maglev

Maglev is a mid-tier optimizing compiler.

It uses runtime feedback and more advanced analysis to generate efficient machine code.

It aims to provide a useful compromise between compilation speed and generated-code quality.

### TurboFan and Turboshaft

V8's top-tier optimizing machinery can perform more aggressive transformations.

Its compilation pipeline includes advanced optimization and code generation, with Turboshaft playing an important role in modern V8 implementations.

For frequently executed code, this can substantially improve performance.

The exact implementation evolves over time.

What's important is the underlying strategy: begin quickly, then invest optimization where execution makes it worthwhile — engineering economics inside the runtime.

---

# 9. How Can V8 Optimize JavaScript When JavaScript Is So Dynamic?

Let's examine something genuinely fascinating.

JavaScript allows this:

```javascript
function add(a, b) {
  return a + b;
}
```

What does `+` mean?

If `a` and `b` are numbers, addition generally occurs.

If either operand becomes a string through the relevant conversion rules, concatenation may occur.

Objects can also participate through primitive-conversion mechanisms.

So the engine can't simply assume that `add()` always means integer addition.

Now imagine a particular application calls the function millions of times:

```javascript
add(10, 20);
add(15, 30);
add(40, 50);
```

Every call uses numbers.

A runtime can observe that pattern.

It may then produce specialized machine code optimized for the numerical case.

But how does it preserve correctness if somebody later calls `add("Hello", " world")`?

This is where speculative optimization comes in.

## Speculation with guards

Conceptually, optimized code may contain logic resembling:

```text
If operands match the expected representation:
    Execute fast specialized arithmetic
Otherwise:
    Use an appropriate more general path
```

The exact generated instructions are more complicated.

But the principle is simple.

The engine makes an assumption based on observed execution.

Then it protects that assumption with checks where necessary.

If the assumptions remain valid, execution can be fast.

If they fail, the runtime must still preserve correct JavaScript behavior.

This may involve a fallback or a process called deoptimization.

## Deoptimization

Deoptimization occurs when optimized execution can no longer continue under its assumptions.

The runtime reconstructs the appropriate execution state and resumes through a less specialized tier or pathway.

This sounds expensive—and it can introduce overhead.

But it's also a remarkable engineering achievement.

It allows the engine to optimize code aggressively without permanently sacrificing the flexibility of JavaScript.

Consider what the engine is effectively saying:

"I've noticed how you've been using this function. I can make that common case faster. But if the situation changes, I still need to behave correctly."

That's speculative optimization.

And it explains why execution history can influence JavaScript performance.

---

# 10. Hidden Classes: Why Two Identical-Looking Objects May Behave Differently

Let's return to our opening mystery.

The hotel pricing system became slower after receiving objects from a new integration partner.

To understand one possible cause, we need to look at how V8 represents JavaScript objects.

Consider:

```javascript
const roomA = {
  id: "R-101",
  price: 120,
  tax: 24
};

const roomB = {
  id: "R-102",
  price: 140,
  tax: 28
};
```

These objects have the same property names, added in the same order.

V8 can represent their structure using an internal concept called a **hidden class**, also known as a shape or Map in V8 terminology.

This is not JavaScript's public `Map` collection.

It's internal metadata describing an object's structure.

Conceptually:

```text
Shape: Room
------------
id     → field location
price  → field location
tax    → field location
```

If many objects share the same shape, the engine can optimize how code accesses their properties.

For example:

```javascript
function getPrice(room) {
  return room.price;
}
```

Without useful optimization, property lookup must account for JavaScript's general object semantics.

Properties can exist in different locations.

They can be inherited.

Objects can have accessors.

Proxies can intercept operations.

Shapes can change.

But when a particular access site repeatedly sees objects with familiar shapes, V8 can cache useful information about how to retrieve the property.

This is called an **inline cache**.

## Inline caches

Suppose `getPrice()` receives hundreds of thousands of objects sharing one shape.

The engine may learn that `price` is consistently found using the same access strategy.

Later accesses can use an efficient specialized path rather than repeating a fully general lookup.

This is one reason seemingly ordinary object access can become extremely fast.

Now consider a different object:

```javascript
const roomC = {
  tax: 24,
  id: "R-103",
  price: 120
};
```

It contains the same properties.

But they were added in a different order.

Depending on the engine's internal shape transitions and other details, it may not share the same hidden class as `roomA`.

Now imagine receiving objects from several integration partners.

Some have extra properties.

Some omit optional properties.

Some construct objects incrementally.

Some use getters.

Some pass proxies.

The same property access site may encounter many different shapes.

That makes specialization more complicated.

## Monomorphic, polymorphic, and megamorphic

These terms describe important patterns in inline caching.

**Monomorphic:** A particular access site has primarily encountered one object shape.

**Polymorphic:** It has encountered several shapes, and the engine may support multiple specialized paths.

**Megamorphic:** It has encountered many shapes, making the optimization strategy more general.

You don't need to memorize the internal thresholds.

The useful idea is that predictable object structures can help the engine generate efficient property access.

But there's a crucial warning.

**Different object shapes do not automatically imply a performance problem.**

V8 is designed to handle dynamic JavaScript.

Its optimization strategies evolve.

Some polymorphic operations remain very fast.

And the cost of property access may be negligible compared with the surrounding work.

Don't spend your professional life rearranging object literals based on vague folklore.

Measure actual bottlenecks.

## Back to the hotel incident

Remember our pricing records?

Originally, all records had a consistent shape.

Later, the application began processing several different representations.

One possible consequence is that hot code now encounters a broader variety of shapes and value types.

This may reduce the effectiveness of certain optimizations or introduce additional work.

But it's only a hypothesis.

The new normalization logic itself might be expensive.

The application might allocate more objects.

It might perform more string-to-number conversions.

It might trigger garbage collection more frequently.

Or the bottleneck could be somewhere else entirely.

The correct next step is not to declare:

"Aha! Hidden classes!"

It's to profile the application.

And that brings us to perhaps the most practical part of today's lecture.

---

# 11. How to Find Out What Your Program Is Actually Doing

Imagine a developer saying:

"This function looks slow."

That's not evidence.

Another developer replies:

"Let's rewrite it using a faster loop."

Also not evidence.

A third developer says:

"Rust would fix this."

Congratulations. We now have three opinions and zero measurements. Professional performance engineering needs a different approach. We need to distinguish **wall-clock time**, **CPU time**, and **where CPU execution is concentrated**.

## Wall-clock time

Wall-clock time measures elapsed real time. Suppose you initiate an HTTP request at 10:00:00.000. The response completes at 10:00:01.500.

The request took 1.5 seconds. But that doesn't mean the application consumed 1.5 seconds of CPU execution. Perhaps it spent most of the time waiting for a database.

Or a network response.

Or an available connection from a pool.

Elapsed time includes waiting.

## CPU time

CPU time measures how much processor execution time the process or thread consumed. A single thread performing arithmetic continuously may consume nearly one second of CPU time during one second of wall-clock time.

A multithreaded process may accumulate more than one second of CPU time during one second of wall-clock time because several threads execute simultaneously. Conversely, a process waiting on I/O may consume very little CPU time while wall-clock time continues advancing.

This distinction is essential.

A service can be slow without consuming much CPU. And a service can consume enormous CPU resources without having high latency on every request.

## A small Node.js measurement

Node.js exposes `process.cpuUsage()`.

We can combine it with a high-resolution timer.

```javascript
const { performance } = require("node:perf_hooks");

async function measure(label, operation) {
  const startWall = performance.now();
  const startCPU = process.cpuUsage();

  const result = await operation();

  const wallMs =
    performance.now() - startWall;

  const cpu = process.cpuUsage(startCPU);

  const cpuMs =
    (cpu.user + cpu.system) / 1000;

  console.log(label, {
    wallMs: wallMs.toFixed(2),
    cpuMs: cpuMs.toFixed(2)
  });

  return result;
}
```

Now consider:

```javascript
await measure("Waiting", async () => {
  await new Promise(resolve =>
    setTimeout(resolve, 1000)
  );
});
```

The wall-clock time should be approximately one second. But the process shouldn't need to spend a full second of CPU time merely waiting for the timer. There will still be some CPU work, and other activity in the same process can affect the measurement.

But the distinction should be visible. Now compare a CPU-heavy calculation:

```javascript
await measure("CPU work", async () => {
  let total = 0;

  for (let i = 0; i < 100_000_000; i++) {
    total += Math.sqrt(i);
  }

  return total;
});
```

Here the process performs actual computation throughout the loop. The elapsed time and CPU time should have a much closer relationship on a mostly idle process, although the exact results vary. This is a useful demonstration.

But it still doesn't tell us *which functions* consumed the CPU time. For that, we need profiling.

---

# 12. CPU Profiling: Stop Guessing and Look at the Evidence

A CPU profiler samples or otherwise records information about where execution time is being spent. A common output is a representation of the call stacks observed during execution. The profiler may reveal that the majority of sampled CPU time is associated with a particular function or group of functions.

For example, imagine a profile indicating:

```text
Reservation processing
    |
    +── Price calculation
    |       |
    |       +── Normalization
    |       +── Tax computation
    |
    +── Response serialization
    |
    +── Logging
```

Suppose the profile reveals that normalization dominates the CPU samples. Now we have an actual lead. We can investigate that code and its inputs.

Perhaps it repeatedly parses complicated strings. Perhaps it performs expensive regular expressions. Perhaps it creates many temporary objects.

Perhaps the data format changed. Perhaps the runtime's optimized execution characteristics changed. The profile doesn't automatically tell us why.

But it shows us where to investigate. That's a substantial improvement over guessing.

## Node.js CPU profiling

Node.js supports a built-in CPU profiler. For a simple application, you can start it with `node --cpu-prof app.js`.

When the process exits normally, Node.js can write a CPU profile file. The resulting `.cpuprofile` can be opened in compatible developer tools, including Chrome DevTools. You can inspect execution samples and identify frequently observed call stacks.

There are important caveats.

Sampling profiles are statistical.

Very short functions may not appear prominently. Inlining and optimization can complicate the relationship between source functions and machine execution. Native work may require additional tools for deeper investigation.

And you should profile representative workloads rather than assuming an artificial benchmark reflects production. Still, this is an excellent starting point.

## A flame graph

You may have encountered flame graphs. A flame graph visualizes aggregated stack samples. Each box represents a function or stack frame.

Boxes are arranged according to call relationships. The horizontal width commonly represents the number of samples associated with that frame and its descendants, not necessarily chronological execution order. Wide boxes indicate where many samples accumulated.

The visual structure helps reveal expensive call paths. But be careful with interpretation. A wide parent box doesn't mean the parent function itself performed all that work.

Much of the time may belong to its children. This is why profilers often distinguish **self time** from **total time**. Self time concerns work attributed directly to a function.

Total time includes work performed through functions it invokes. For diagnosing expensive operations, both perspectives matter.

---

# 13. Why Microbenchmarks Can Lie

Now let's address something that trips up experienced developers. Suppose you want to compare two implementations.

You write:

```javascript
const start = performance.now();

for (let i = 0; i < 1_000_000; i++) {
  calculatePrice(room);
}

console.log(performance.now() - start);
```

The result looks impressive.

Then you change the implementation and run the test again. The second version is twice as fast! Or perhaps twice as slow.

Have you discovered a genuine improvement?

Maybe.

But there are several reasons to be cautious.

## Warmup and execution tiers

The JavaScript engine may initially execute code using a less optimized tier. After observing repeated execution, it may compile optimized machine code. So the beginning of a benchmark may behave differently from later iterations.

If two implementations receive different warmup conditions, the comparison may be misleading.

## Dead-code elimination

Optimizing compilers can sometimes recognize that certain computations have no observable effect. If you calculate a value and never use it, the engine may eliminate some of the work. That can make a benchmark measure less than you think.

A simple defense is to ensure that the result matters and is observed outside the measured loop. But careful benchmark design involves more than merely printing a value.

## Garbage collection

One implementation may allocate many temporary objects.

Another may reuse memory.

Garbage-collection activity can affect timings. A single run may happen to include a collection pause while another doesn't.

## CPU frequency and operating-system effects

Modern processors change their operating frequencies depending on power limits, temperature, and workload. Other processes compete for CPU time. The operating system schedules threads.

Background activity can affect cache contents. All of these can influence measurements.

## Input distribution

A function might be fast for uniform numerical data but slower for mixed values. A sorting algorithm might perform differently on already sorted input versus random input. A hash-based lookup might behave differently with different key distributions.

A benchmark using unrealistic data may teach you very little about the actual production workload.

## What a better experiment looks like

A useful benchmark should:

1. Use representative inputs.
2. Exercise the behavior you're actually investigating.
3. Allow relevant runtime warmup.
4. Repeat measurements.
5. Compare distributions rather than trusting one number.
6. Verify that the results remain correct.
7. Account for allocations and other relevant costs.
8. Confirm improvements against application-level measurements.

And perhaps most importantly:

**Don't optimize a function merely because you can demonstrate that another implementation is faster in isolation.**

Optimize it because the difference matters to the system. A function that consumes 0.01% of request latency is not an urgent target. Even if you manage to make it ten times faster.

---

# 14. A Fascinating Distinction: Throughput Versus Latency

We've discussed performance several times throughout this course. But it's worth connecting the concepts to actual execution. Imagine a backend service handling customer requests.

It can process 1,000 requests per second. Does that mean each request completes in one millisecond?

No.

Throughput and latency are different quantities.

**Throughput** measures completed work per unit of time.

**Latency** measures how long one operation takes to complete.

A service may handle many requests concurrently, producing high throughput even if individual requests take hundreds of milliseconds. Conversely, a service may complete individual operations quickly but support very few concurrent operations. This distinction matters enormously for Node.js.

## A simple example

Suppose a request involves:

- 5 milliseconds of CPU work.
- 100 milliseconds of database waiting.
- 5 milliseconds of CPU work.

The total latency is approximately 110 milliseconds. But the application spends only about 10 milliseconds performing CPU work for that request. If the waiting periods can overlap across independent requests, the service may support substantial concurrency without dedicating one CPU core to each waiting operation.

That's a major advantage of asynchronous I/O.

But here's the catch.

Imagine replacing the initial 5-millisecond CPU operation with a 500-millisecond synchronous calculation. Now every request that executes that calculation occupies the JavaScript execution thread for much longer.

In a conventional single-main-JavaScript-thread Node.js setup, this can delay the handling of other callbacks and incoming work. Asynchronous I/O does not magically make CPU-bound JavaScript operations parallel. That distinction becomes the central subject of CS320-L01.

For now, remember:

**Fast execution of individual CPU instructions is only one ingredient in application performance.**

The architecture of work, dependencies, waiting, and concurrency can matter even more.

---

# 15. What This Means for AI-Generated Code

Let's connect the lesson to modern development. An AI coding assistant can generate a function that looks beautifully optimized. Perhaps it eliminates an intermediate array.

Perhaps it replaces a loop with a clever functional expression. Perhaps it introduces typed arrays. Perhaps it creates a sophisticated caching layer.

Perhaps it refactors your object model. But what evidence do we have that the change improves performance? Without measurements, often very little.

This is particularly dangerous because AI-generated code can appear convincing. A generated explanation might say:

"This implementation improves performance by avoiding unnecessary allocations and optimizing CPU cache locality."

That sounds excellent.

But did it actually reduce allocations? Did it change memory locality? Did V8 already optimize the original version?

Did the change create more expensive object access? Did it improve the actual hot path? Did it introduce new correctness risks?

Those are empirical questions.

## Performance isn't a writing style

Fast-looking code isn't necessarily fast code. Short code isn't necessarily fast code. Low-level code isn't necessarily fast code.

And elaborate code isn't necessarily sophisticated code. What matters is the behavior of the resulting system. AI-assisted development makes this distinction more important.

When generating code becomes cheap, the limiting engineering skill increasingly shifts toward:

- Defining the right problem.
- Choosing the right algorithms.
- Understanding runtime behavior.
- Identifying bottlenecks.
- Measuring results.
- Validating correctness.
- Evaluating trade-offs.

You don't necessarily need to handwrite every loop. But you do need to understand whether the generated implementation is appropriate. And when something behaves unexpectedly, you need enough knowledge of the underlying machinery to investigate.

That's why studying runtime execution is worthwhile even if you never intend to write an interpreter or compiler.

---

# 16. The Oral Examination

We now have enough machinery to talk about execution like an engineer rather than guessing from the shape of the source.

Before reading the solutions, try answering these questions out loud. Imagine that a senior engineer is interviewing you and will challenge any hand-waving. Speak complete explanations, not fragments.

### Challenge A — The Slow Pricing Function

*Suggested time: 10 minutes.*

A Node.js pricing function performs poorly after a new integration partner is added.

The function processes objects with different property orders, optional fields, and sometimes different value types.

What are three possible explanations for the slowdown?

How would you distinguish additional application-level work from a change in runtime optimization behavior?

Would you immediately rewrite every object to have the same shape?

Why or why not?

### Challenge B — The Eight-Core Mystery

*Suggested time: 8 minutes.*

A simulation runs at an extremely low frame rate.

Your processor exposes eight logical CPUs.

Overall CPU utilization is approximately 20%.

GPU utilization is also low.

Could the simulation still be limited by CPU execution?

Explain how.

What measurements would help distinguish a serial CPU bottleneck from memory stalls, synchronization, or other limitations?

Why wouldn't adding more threads automatically solve the problem?

### Challenge C — The Dangerous Benchmark

*Suggested time: 8 minutes.*

A developer claims:

"I proved this function is three times faster. I ran it once with `performance.now()` and got a lower number."

What problems do you see with the claim?

What should a better benchmark include?

And how would you establish whether the improvement matters in production?

### Challenge D — The Unexpectedly Slow API

*Suggested time: 10 minutes.*

An HTTP endpoint takes 800 milliseconds to complete.

A distributed trace reveals:

- Request parsing and validation: 5 ms.
- Database operation: 600 ms.
- Application processing: 15 ms.
- External API call: 150 ms.
- Response serialization and remaining overhead: 30 ms.

A developer proposes rewriting the 15-millisecond processing function in a faster language.

Even if they make that function infinitely fast, what is the greatest possible reduction in endpoint latency under this sequential model?

What would you investigate instead?

Which parts of the request might be independent enough to overlap?

What correctness risks might arise from attempting to execute operations concurrently?

---

# 17. Solutions and Discussion

*Read this section after answering out loud. The coding lab appears after the spoken lecture ends.*

### Solution A — Slow pricing function

Possible explanations include:

- Additional string conversion or normalization work.
- More object allocations.
- Less effective optimized property access because of diverse object shapes.
- Different numerical representations.
- Increased garbage-collection activity.
- Additional logging or validation.

Begin with representative profiling and benchmarks.

Inspect where CPU time is concentrated.

Compare the old and new workloads.

Verify whether input differences influence the result.

Consistent object shapes can sometimes help V8, but blindly rewriting every object is not justified without evidence.

The slowdown might have nothing to do with hidden classes.

### Solution B — Eight-core mystery

Overall CPU utilization averages activity across the machine's available logical processors.

One critical execution thread can be saturated while other processors remain relatively idle.

The simulation may be unable to advance until that thread completes its work.

Memory latency, synchronization, and other dependencies can also limit progress.

Useful measurements include per-thread CPU utilization, CPU profiling, simulation-step timing, GPU frame timing, and relevant hardware performance counters.

Adding threads helps only when useful work can be divided and coordinated efficiently.

Parallelism introduces overhead and doesn't eliminate serial dependencies.

### Solution C — Dangerous benchmark

A single timing result is insufficient evidence of a stable performance improvement.

Potential problems include warmup differences, runtime optimization, garbage collection, other processes, input distribution, and measurement noise.

A better benchmark uses representative workloads, repeated measurements, controlled comparisons, output validation, and appropriate warmup.

Then the improvement should be evaluated within the actual application.

A dramatic speedup in a function that contributes almost nothing to total latency may have little practical value.

### Solution D — Slow API

The processing function accounts for 15 milliseconds of an 800-millisecond request.

Even eliminating that work entirely reduces the total from 800 milliseconds to 785 milliseconds.

That's a maximum improvement of 1.875% under the stated sequential model.

The database operation is a much larger contributor.

Investigate query execution plans, round trips, indexing, lock waits, connection-pool delays, and the actual source of its latency.

The external API also consumes significant time.

Independent operations might be overlapped, but only if their dependencies and side effects permit it.

For example, charging a customer and confirming inventory may require careful ordering or compensating workflows.

Executing business-critical operations concurrently without understanding their consistency requirements can produce serious bugs.

Performance improvements must preserve correctness.

---

# 18. The Mental Model Worth Keeping

The pricing service looked simple. The algorithm barely changed. Execution got slower. Source isn't machine code — and the slowdown lived in the machinery beneath the line that "looked the same."

Remember these durable distinctions:

**Arithmetic is cheap; getting data often isn't** — a fast CPU can still wait on the memory hierarchy.

**Pipelines, prediction, and out-of-order execution hide latency** — until dependencies, mispredictions, or cache misses intervene.

**More cores don't guarantee proportional speedups** — Amdahl's law: the serial fraction caps the win.

**V8 optimizes from runtime feedback** — shapes and types can specialize; when assumptions fail, deoptimization restores correctness at a cost.

**Wall-clock, CPU time, and profile samples answer different questions** — Big O alone cannot tell you where this request spent its second.

**Speed up the wrong 1% and accomplish little** — optimize what the machine is actually doing, not what looks inefficient on the page.

**Internals explain behavior; they aren't an invitation to rearrange literals for V8** — measure first; folklore second.

TypeScript sits atop parse, bytecode and JIT tiers, the CPU, the memory hierarchy, OS scheduling, and networks and databases. Most of the time `reservation.price + reservation.tax` simply works — triumph of abstraction. When something goes wrong, look beneath just far enough to find the constraint. Form hypotheses and test them.

> **The master sticky note**
>
> When a program becomes slow, don't merely ask which line of code looks inefficient. Ask what the machine is actually spending its time doing — and why.

That is why studying runtime execution remains valuable even when an assistant can generate the code. Someone still has to recognize which bottleneck is real, which measurement answers the question, and which change is safe.

You now have the JS/TS-centered vocabulary of languages, memory, and the path from source to silicon. Two lectures still widen the frame beyond one ecosystem.

---

# 19. Next Lecture — Type Systems, Ownership, and Language Design

L01–L03 stayed close to TypeScript, JavaScript, and V8. That is enough to debug a Node service — not enough to understand why other languages make different promises.

In **CS220-L04**, we compare type systems and memory-ownership designs across languages: what static types, nominal types, inference, mutability rules, and ownership can enforce at compile time — and what they still cannot. After that, **CS220-L05** runs the same program across several runtimes so concurrency and performance folklore meet measurement.

Networks (**CS230**) and operating-system concurrency (**CS320**) remain the natural Foundations follow-ons once CS220 is complete — see the recommended study order in `README.md`.

---

## Optional Practical Lab — Watch CPU Time and Wall Time Diverge

*The spoken lecture ends here. The remaining material is a screen-first investigation worksheet.*

For this session, one small practical investigation.

Create a file named `execution-lab.js`.

We'll compare waiting with computation, then capture a CPU profile.

**Suggested time: 15–20 minutes.**

> **Gym rules:** predict before you run. The oral challenges were in the spoken lecture; these labs are for your own eyes.

## Part A — Timing utility

This helper records wall-clock milliseconds with `performance.now()` and CPU milliseconds from `process.cpuUsage()`, then logs both for a labeled operation.

```javascript
const { performance } = require("node:perf_hooks");

async function measure(name, fn) {
  const wallStart = performance.now();
  const cpuStart = process.cpuUsage();

  const result = await fn();

  const wallMs = performance.now() - wallStart;
  const cpu = process.cpuUsage(cpuStart);

  console.log(name, {
    wallMs: Math.round(wallMs),
    cpuMs: Math.round(
      (cpu.user + cpu.system) / 1000
    )
  });

  return result;
}
```

## Part B — An operation dominated by waiting

This function awaits a one-second timer and does almost no computation while the clock advances.

```javascript
async function waitForOneSecond() {
  await new Promise(resolve =>
    setTimeout(resolve, 1000)
  );
}
```

## Part C — An operation dominated by calculation

This function loops a hundred million times, accumulating square roots — deliberate CPU work.

```javascript
function calculate() {
  let total = 0;

  for (let i = 0; i < 100_000_000; i++) {
    total += Math.sqrt(i);
  }

  return total;
}
```

## Part D — Run the comparison

Wire both operations through `measure`, then run the script and compare the logged wall and CPU times.

```javascript
async function main() {
  await measure("Waiting", waitForOneSecond);
  await measure("Calculation", calculate);
}

main().catch(console.error);
```

Before executing the program, predict:

1. Which operation will consume more CPU time?
2. Which operation will have wall time near one second?
3. Could the calculation complete in less than one second?
4. Would that mean it performed less computational work?
5. What would happen if the calculation were executed repeatedly?

The exact timings depend on your computer and runtime.

Don't expect identical measurements across machines.

The purpose is to understand the difference between consuming CPU resources and waiting for time to pass.

## Part E — Generate a CPU profile

Start the same lab under Node's built-in profiler with `node --cpu-prof execution-lab.js`.

Node.js should generate a `.cpuprofile` file on normal process exit.

Open it in a compatible profiler such as Chrome DevTools.

Inspect the sampled execution.

Which function dominates CPU activity?

Does the one-second timer appear as a similarly expensive CPU operation?

Why not?

This is the difference between latency and CPU work made visible.

## An optional extension

Create a second calculation function with different data representations.

For example, this loop sums every element of an array-like value — try it on a `Float64Array` and on an ordinary JavaScript array of similar numbers.

```javascript
function sumTypedArray(values) {
  let total = 0;

  for (let i = 0; i < values.length; i++) {
    total += values[i];
  }

  return total;
}
```

Compare processing a `Float64Array` with processing an ordinary JavaScript array containing similar numerical values.

Repeat measurements and verify outputs.

You may observe a difference.

You may not.

Different V8 versions and workloads can produce different results.

That's not a failure of the experiment.

It's an opportunity to learn the most important lesson of performance engineering:

**Measure first. Explain the result second.**

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
CS220-L03  HOW PROGRAMS EXECUTE — INTERVIEW GLANCE CARD

CORE MODEL
  CPU never sees TypeScript — ISA + registers + memory hierarchy
  Fetch–decode–execute is foundation; modern CPUs pipeline, predict, OoO, speculate
  Arithmetic often cheap; waiting for data often isn’t

MEMORY HIERARCHY
  Registers → L1 → L2 → LLC → RAM → storage (faster/smaller ↔ slower/larger)
  Cache lines (~64B common): spatial locality helps arrays; pointer-chasing lists hurt
  Same Big-O ≠ same wall time when access patterns differ

CONTROL FLOW & ILP
  Branch prediction: common path wins; mispredict discards speculative work
  Predictability of control/data patterns affects real cost (measure; not universal law)
  Out-of-order: independent ops progress while loads wait; dependencies limit ILP
  Program order ≠ internal exec order ≠ architecturally observable order

PARALLELISM CAP
  Amdahl: Speedup = 1 / ((1−P) + P/N); serial fraction caps win (P=0.9,N=8 ≈4.7×; ∞→10×)
  Same reasoning for latency budgets: speeding 20ms of a 465ms request ≈ tiny win
  Ask: what fraction of TOTAL time can this change affect?

V8 TIERS (conceptual)
  Source → Ignition bytecode → Sparkplug baseline → Maglev mid → TurboFan/Turboshaft top
  Start fast; invest optimization where hot
  Speculative opts + guards; assumption fail → deoptimize (correctness restored, cost)
  + means numbers / strings / coercions — history shapes specialized code

HIDDEN CLASSES / INLINE CACHES
  Shape (hidden class / Map internal) from property names & insertion order
  Inline cache learns access strategy at a site
  Monomorphic → polymorphic → megamorphic (more shapes → more general path)
  Trap: diverse partner shapes MAY slow hot property access — hypothesis, not verdict
  Don’t rearrange literals by folklore — profile first

MEASUREMENT
  Wall-clock   elapsed (includes waiting)
  CPU time     processor work (I/O-wait can be high wall, low CPU)
  Profile      where samples concentrate (self vs total time)
  node --cpu-prof → .cpuprofile; flame width ≈ sample weight, not timeline
  process.cpuUsage + performance.now to contrast wait vs compute

MICROBENCHMARK LIES
  Warmup/tiers · dead-code elim · GC pauses · CPU freq/OS noise · unrealistic inputs
  Better: representative data, repeats, distributions, correctness, app-level impact
  Don’t optimize the 0.01% of latency

THROUGHPUT vs LATENCY
  Throughput = work/time; latency = one op duration — not interchangeable
  Async I/O overlaps waits; sync CPU still occupies the JS thread (→ CS320)

AI / FOLKLORE TRAP
  “Looks optimized” / “cache locality” claims need evidence on the hot path

SENIOR LINE: when slow, ask what the machine is spending time doing — and why —
             not which source line looks inefficient.
```
