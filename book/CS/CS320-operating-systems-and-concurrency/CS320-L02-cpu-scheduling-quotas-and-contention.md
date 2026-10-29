---
id: CS320-L02
course: CS320
title: "CPU Scheduling, Quotas, and Contention"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: CS320-L01
next: CS320-L03
---




# CS320 — Operating Systems and Concurrency

## Lecture 02: CPU Scheduling, Quotas, and Contention

*Sixteen processors. Eight percent CPU utilization. A worker that needs forty milliseconds of computation takes three hundred milliseconds to finish. Where did the missing time go?*

# Part I — Intuition

## The picture to carry in your head

Imagine an enormous workshop with sixteen workbenches.

Each workbench can accommodate one worker at a time. There are plenty of tools, the electricity works, and most of the workshop appears almost empty.

Yet one team keeps missing deadlines.

The team's problem is that it has access to only a fraction of the workshop's working time. It may be allowed to use several benches briefly, but once it has consumed its allowance, its workers must stop until the next allocation period.

Someone from management walks through the building and reports that everything is fine.

"Look! Fifteen benches are idle!"

The workers disagree.

Both observations are correct.

The building has spare capacity. The particular team does not have permission to use more of it.

This is the first mystery of CPU scheduling and resource restrictions.

A computer may possess substantial processing capacity, while one application has access to far less than the machine's total resources.

The discrepancy becomes especially interesting when we place applications inside containers.

But there's a second mystery: even if a process is allowed to execute, that doesn't mean it is executing right now.

To understand why, we need to separate three things that developers often confuse: **doing work, being ready to do work, and waiting for something that makes work possible.**

## 1. The three states of a worker

Let's return to our document-processing service from the previous lecture.

A customer uploads a PDF. Our Node.js backend dispatches the extraction work, and a worker starts analyzing the document.

Imagine observing that worker at three different moments.

First, it is executing instructions on a CPU. This is straightforward: the worker is running.

Next, it finishes a piece of work, but another eligible thread receives the processor. Our worker has more instructions ready to execute; it simply isn't receiving CPU time.

Now the worker is runnable but not running.

Finally, imagine the worker needs data from disk or must wait for another thread to release a lock. It cannot proceed until that condition changes.

Now it is blocked or sleeping.

These distinctions are foundational.

A runnable thread wants processor time. A blocked thread may need an entirely different resource.

If our PDF processor is slow, we must discover which situation explains the delay.

Giving additional CPU time to a thread blocked on a database connection will not make the database respond faster.

But increasing a database timeout will not help a thread that cannot obtain CPU service.

The engineering challenge is to identify which waiting line our work has joined.

## 2. Wall time is not CPU time

Suppose processing one document requires forty milliseconds of actual CPU execution.

On your laptop, it finishes in approximately forty milliseconds, ignoring minor overhead.

In production, it takes three hundred milliseconds.

Did the processor become seven times slower?

Not necessarily.

The worker might perform the same forty milliseconds of computation while spending another two hundred sixty milliseconds waiting.

That waiting could come from competing runnable tasks, resource throttling, locks, external dependencies, or a combination.

The distinction is between **CPU time**, which measures execution on a processor, and **wall-clock time**, which measures elapsed time.

Imagine a worker that spends twenty milliseconds executing, waits eighty milliseconds, and then executes another twenty milliseconds.

The total elapsed time is one hundred twenty milliseconds.

Its CPU time is forty milliseconds.

Nothing about the function's start and end timestamps tells us why the other eighty milliseconds passed.

This is why a slow operation is not automatically a computationally expensive operation.

And why the first performance question should not be "How do we optimize this function?"

It should be "What was this function actually doing during the elapsed time?"

## 3. Scheduling: assigning scarce execution capacity

Our workshop has sixteen benches, but suppose thirty employees are ready to work.

Someone must decide who gets a bench.

The operating-system scheduler performs an analogous job.

On Linux, schedulable entities normally correspond to threads, which may belong to one or several processes.

The scheduler decides when eligible tasks execute and on which logical processors.

It must balance competing objectives: fairness, responsiveness, throughput, priorities, processor locality, and various scheduling policies.

The operating system may interrupt one running task to let another execute.

That is called preemption.

Switching from one execution context to another requires saving and restoring relevant execution state. We call this a context switch.

Context switches have costs, but they also make general-purpose multitasking practical.

Without scheduling, one computationally expensive task could monopolize a processor indefinitely.

With scheduling, many tasks can make progress even when there are fewer execution slots than runnable tasks.

However, scheduling cannot create additional computing capacity.

It distributes what exists.

## 4. The sixteen-core illusion

Our production host has sixteen logical CPUs.

Someone checks the dashboard and sees eight percent utilization.

They conclude the server has abundant spare capacity.

But consider a single CPU-intensive JavaScript thread.

At any particular moment, that thread executes on one logical CPU.

If it continuously occupies one logical CPU while the other fifteen remain idle, aggregate utilization can appear close to 6.25 percent.

The thread is fully busy.

The host is mostly idle.

Both statements are correct.

Now imagine the process also has a CPU quota equivalent to half a logical CPU's runtime.

It may be prevented from executing continuously even though many other logical CPUs have nothing useful to do.

The application could be limited by its own configuration rather than by the physical machine.

This is why we must distinguish **host capacity, usable CPU placement, and allocated CPU time**.

They are not interchangeable.

## 5. Why more workers may make everything worse

Our team proposes increasing the number of document-processing workers.

More workers should mean more documents processed, right?

Only if useful execution capacity is available.

Suppose four workers can already consume the CPU time available to the service.

Adding another twenty workers creates additional competition without creating more CPU capacity.

The new workers may spend more time waiting to execute.

They may increase context switching, shared-state contention, and cache disruption.

Throughput might barely improve while latency becomes much worse.

For workloads that primarily wait on external services, additional concurrency may still help.

But a CPU-intensive task is not made faster simply by surrounding it with more CPU-intensive tasks.

The question is not "How many workers can we start?"

It is "How much useful work can our execution budget sustain?"

## The intuition pass ends with three questions

Before moving on, answer these aloud.

1. A process uses one logical CPU continuously on a sixteen-logical-CPU host. Why might the dashboard show only about six percent aggregate utilization?
2. How can a thread be ready to execute but make no progress?
3. Why might adding eight CPU-intensive workers decrease throughput instead of increasing it?

If you can explain the difference between being busy, being runnable, and being permitted to run, the scheduler's machinery will make much more sense.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The production incident: a fast computation with slow completion

Monday morning. Our document-processing service has developed a latency problem.

Customers upload documents to a Node.js API. A worker performs extraction and analysis, then the application stores the result in PostgreSQL.

Previously, the computational portion took approximately forty milliseconds.

Now the tail of the latency distribution occasionally approaches three hundred milliseconds.

The infrastructure dashboard reports about eight percent aggregate CPU utilization on a machine with sixteen logical CPUs.

Memory looks healthy. Storage isn't obviously overloaded. PostgreSQL response times are ordinary.

The application is running inside a Linux container.

Our investigation begins with competing explanations.

Perhaps the worker now performs more arithmetic.

Perhaps Node.js is experiencing garbage-collection pauses.

Perhaps the application is blocked on a lock.

Perhaps the operating system is delaying runnable work.

Or perhaps the container is exhausting an allocated CPU budget.

Each explanation predicts different evidence.

Our job is to find that evidence rather than select the first plausible story.

## 2. Account for elapsed time before optimizing code

The first distinction is between elapsed time and CPU execution time.

Consider a task that begins at time zero and finishes after three hundred milliseconds.

During that interval, it might execute for forty milliseconds and wait for the remaining two hundred sixty.

A simplified timeline could look like this:

```text
0 ms                                                  300 ms
|---------------------------------------------------------|
| RUN | WAITING........ | RUN | THROTTLED........ | RUN    |
    Total CPU execution: 40 ms
    Total elapsed time: 300 ms
```

The picture is illustrative rather than a trace from our actual service.

The essential point is that elapsed time can contain several qualitatively different kinds of delay.

**CPU execution** means the task's instructions are being run on a processor.

**Runnable waiting** means the task is eligible to execute but has not received processor service.

**Blocked waiting** means some condition must change before the task can execute again.

**Throttling** means a resource-control mechanism is restricting execution despite the existence of work that wants to run.

The distinctions are sometimes visible through task states, scheduler accounting, tracing, and cgroup statistics.

### A subtle measurement problem

Be careful with process-level CPU time.

A Node.js process may contain multiple threads: a main JavaScript thread, native runtime threads, and perhaps worker threads.

Process CPU time can accumulate across those threads.

Therefore, a process consuming eighty milliseconds of CPU during a forty-millisecond elapsed interval does not imply that one request executed twice as quickly.

It might mean several threads executed concurrently.

For a particular operation, distinguishing its CPU demand from other concurrent work may require targeted profiling, thread-level measurements, or controlled experiments.

This is why a single CPU-percentage number is often insufficient evidence.

## 3. Linux schedules threads, not abstract business requests

Our document processor handles jobs, but the kernel does not understand the notion of a customer document.

It understands schedulable tasks.

On Linux, threads within a process generally have their own scheduling state, even though they share the process's address space and other resources.

The kernel can schedule different threads on different logical processors.

This matters for Node.js.

One process can have several operating-system threads while ordinary JavaScript callbacks execute on its main JavaScript thread.

Moving a computationally intensive operation into a Node.js worker thread can allow that work to execute in parallel with other JavaScript work.

But the operating-system scheduler still decides when the relevant threads execute.

Creating a worker thread gives the application another execution context.

It does not grant that context an independent processor or guaranteed CPU time.

### Running, runnable, and sleeping

Linux exposes task states such as running/runnable, interruptible sleep, and uninterruptible sleep.

The state code `R` commonly includes both executing and runnable tasks.

That creates a common mistake: seeing a task in state `R` and assuming it was actively running during the entire observation.

In reality, it may have spent substantial time waiting for processor service.

Conversely, a sleeping task might be waiting for I/O, a lock, or another event.

It may be behaving exactly as designed.

We should distinguish the number of tasks that exist from the number that are ready to consume CPU.

A process with two hundred sleeping connections is not necessarily putting two hundred CPU-intensive tasks into competition.

A process with thirty continuously runnable worker threads probably is.

## 4. What the scheduler is trying to accomplish

Imagine three computational tasks sharing one logical CPU.

Task A requires one hundred milliseconds of computation.

Task B requires one thousand milliseconds.

Task C is an interactive request that needs only two milliseconds.

If the operating system always allowed the current task to finish before selecting another, Task C could sit behind Task B for an entire second.

That would be terrible responsiveness.

A preemptive scheduler can switch among runnable tasks, allowing short and interactive tasks to make progress without waiting for long computations to finish.

But switching after every instruction would waste enormous resources.

The scheduler must balance responsiveness with the overhead of switching execution contexts.

### Fair scheduling

Linux has long supported fair scheduling policies for ordinary workloads.

The historical Completely Fair Scheduler, or CFS, introduced the idea of tracking virtual runtime to approximate fair distribution of processor time among runnable tasks.

Virtual runtime is not simply wall-clock time. It reflects accounted execution adjusted by scheduling weights and relevant policy.

The purpose is to prevent one ordinary task from permanently monopolizing a processor while other eligible tasks starve.

Newer Linux kernels have transitioned toward **EEVDF**, meaning Earliest Eligible Virtual Deadline First, within the fair-scheduling implementation.

EEVDF uses accounting concepts including virtual runtime and lag to reason about whether a task has received more or less than its fair share. Among eligible tasks, virtual deadlines help determine which should execute next.

You do not need to memorize internal scheduler structures for a backend interview.

You should understand the contract: the scheduler is distributing finite execution time among eligible tasks, with fairness and responsiveness shaped by the scheduling policy.

### Fairness is not the same as equal time for everything

Scheduling weights and priorities influence the distribution.

Some tasks belong to real-time scheduling classes with behavior different from ordinary fair-scheduled tasks.

The kernel also supports scheduling policies appropriate for batch or specialized workloads.

Not every thread competes under identical rules.

But ordinary Node.js application work generally runs under normal scheduling policies unless the environment or application deliberately changes them.

Changing priorities without evidence is usually a poor first response to latency problems.

If the application is exhausting a CPU quota, raising a task's priority does not create additional quota.

If the application is blocked on PostgreSQL, favorable scheduling cannot make the database return early.

The scheduler's policy matters, but it is only one piece of the system.

## 5. Preemption and context switching

Suppose our document-processing worker is executing a CPU-intensive calculation.

Another thread becomes runnable.

Depending on scheduling policy and current conditions, the kernel may arrange for the existing thread to stop executing and another thread to run.

That is preemption.

The operating system must preserve the interrupted task's architectural state and restore the state needed by the next task.

A context switch may also affect caches, translation-related state, and processor locality.

Some of its costs are direct bookkeeping. Others are indirect, such as reduced cache efficiency after switching between working sets.

### Voluntary versus involuntary switches

A thread may voluntarily stop running when it blocks or yields.

Alternatively, it may be preempted involuntarily.

Monitoring tools often expose counts of these categories.

They are useful clues, but not diagnoses.

A network-heavy server may perform many voluntary switches because threads wait for events.

A heavily CPU-contended workload may experience more involuntary preemption.

Neither count, taken alone, proves that context switching is the performance bottleneck.

We need a relationship between observed switching, CPU usage, runnable delay, and useful throughput.

Optimizing away every context switch would be nonsense. Modern multitasking depends on them.

The problem is excessive overhead relative to productive work.

## 6. Sixteen logical CPUs do not guarantee sixteenfold speed

A machine has sixteen logical CPUs.

That does not mean a single thread can execute its next instruction on all sixteen simultaneously.

Ordinary sequential execution follows one instruction stream, subject to the processor's internal capabilities.

To exploit multiple logical processors, software generally needs multiple useful execution contexts or parallelizable work.

Imagine a calculation requiring forty milliseconds of execution on one logical CPU.

If the calculation is strictly sequential, adding fifteen idle CPUs does not automatically reduce the duration to two and a half milliseconds.

That's not a scheduling failure.

It's a property of the workload's parallelism.

### CPU affinity

Now consider a different restriction.

Linux supports CPU affinity, which controls the set of logical CPUs on which a thread may execute.

A thread restricted to one logical CPU cannot freely migrate to the other fifteen, even if they are idle.

Affinity can be configured explicitly or constrained through other mechanisms, including CPU sets.

This produces another version of the low-utilization mystery.

The host may have ample spare capacity, but the application is allowed to execute only within a smaller set of processors.

Before recommending more hardware, inspect the CPUs actually available to the workload.

### Logical CPUs versus physical cores

Another complication is simultaneous multithreading.

Two logical CPUs may share execution resources within one physical core.

Therefore, sixteen logical CPUs do not necessarily provide sixteen independent physical cores' worth of performance.

Real throughput depends on the workload, processor architecture, cache behavior, memory bandwidth, and other factors.

For application engineering, the lesson is to treat a CPU count as a capacity descriptor, not a guaranteed multiplier.

## 7. The container quota: our strongest suspect

Return to our document-processing incident.

We inspect the container's CPU configuration.

It has a quota corresponding to half a logical CPU's worth of aggregate runtime.

The Linux cgroup v2 interface `cpu.max` expresses this kind of maximum CPU bandwidth.

For example:

`50000 100000`

These values are measured in microseconds.

The first describes an allowed amount of CPU runtime. The second describes the associated period.

In this configuration, the group can consume fifty milliseconds of aggregate CPU execution per one-hundred-millisecond period, subject to applicable scheduling and hierarchical restrictions.

Its long-run CPU capacity is therefore equivalent to half of one logical CPU.

But here's the subtle part.

**A quota of half a CPU does not necessarily mean a thread runs continuously at half speed.**

It may run at ordinary execution speed when budget is available.

Then, if the group exhausts its allowed CPU runtime, its eligible fair-scheduled tasks can be throttled until the relevant budget becomes available.

That creates intervals of progress separated by intervals of enforced waiting.

### Two threads can exhaust the budget faster

Suppose two worker threads execute concurrently on two logical CPUs.

Each consumes twenty-five milliseconds of CPU runtime.

Together, they consume fifty milliseconds of aggregate CPU runtime.

If they do so during approximately twenty-five milliseconds of wall-clock time, they can exhaust the group's entire budget early in the accounting period.

The group can then face throttling for the remaining portion.

Our application has enough parallel work to use two processors briefly.

But it doesn't have the budget to use them continuously.

This distinction explains why adding threads may make the application appear faster for an instant, then produce worse latency tails.

The workload spends its budget more quickly and may hit the restriction sooner.

### An important qualification

The exact timing depends on the scheduler, hierarchy, periods, and available budget. Real systems also have details such as runtime distribution and optional burst allowances.

Don't infer an exact throttle duration from a simplified diagram.

What we can say reliably is that a bandwidth quota constrains aggregate CPU service over its accounting periods.

Unused CPUs elsewhere on the host do not override that constraint.

## 8. The utilization paradox, quantified

Our host has sixteen logical CPUs.

The container has long-run CPU capacity equivalent to half a CPU.

If that container continuously consumes its full allowance, how much of the host's theoretical aggregate execution capacity is it using?

Half divided by sixteen.

That's approximately 3.125 percent.

So a container can be completely saturated relative to its configured CPU budget while representing only a few percent of total host capacity.

The host dashboard reports eight percent CPU utilization because other activity also consumes resources.

Nothing in that number contradicts the container being severely constrained.

Now consider the document workload.

Each document needs approximately forty milliseconds of CPU execution.

With half a CPU of sustained capacity, the theoretical upper bound is approximately twelve and a half such jobs per second, before accounting for overhead and other CPU work.

That's a capacity ceiling, not a promise of sustained throughput.

If customers submit thirty such jobs per second, the incoming CPU demand is about 1.2 CPU-seconds per wall-clock second.

The service has only 0.5 CPU-seconds of capacity per wall-clock second.

The incoming demand exceeds the available service capacity.

The backlog must grow unless the service rejects work, sheds load, or changes the workload or capacity.

Even if the application could schedule a thousand threads, the arithmetic would not improve.

We have reached a capacity limit.

## 9. CPU quota and CPU weight are different controls

It is tempting to treat every CPU configuration value as a limit.

That is incorrect.

Linux cgroup v2 also provides `cpu.weight`.

A weight expresses relative CPU-sharing preference among relevant competing groups.

The default is commonly 100, within a larger permitted range.

Suppose two groups compete for processor time and one has twice the effective weight of the other.

Under relevant fair-scheduling conditions, the scheduler can use those relative weights to influence how CPU time is distributed.

But when the system is otherwise idle, a lower-weight group may be able to consume additional available capacity.

A hard CPU bandwidth quota behaves differently.

It can restrict execution even when another processor is idle.

The distinction is:

- **Weight:** How should contended CPU capacity be divided?
- **Quota:** How much CPU runtime may this group consume over the accounting period?

### Kubernetes implications

In Kubernetes, CPU requests and CPU limits have different roles.

Requests participate in scheduling and resource planning and commonly influence relative CPU allocation behavior.

Limits establish a maximum CPU allocation constraint, generally enforced through Linux cgroup CPU controls.

Therefore, a container may have a relatively small CPU request yet use more CPU when spare capacity is available, depending on its configuration.

But a restrictive CPU limit can produce throttling.

For this course, we care about the kernel mechanism.

Detailed Kubernetes placement, requests, limits, autoscaling, and resource-management policy belong to SE450.

The crucial diagnostic distinction remains the same: competition for available CPU versus enforcement of a configured maximum.

## 10. How do we know the container is being throttled?

We need evidence beyond a plausible configuration value.

Linux cgroup v2 exposes CPU usage and throttling statistics through `cpu.stat`.

Relevant fields can include total CPU usage, the number of quota periods, the number of periods in which throttling occurred, and accounted throttled time.

For example, we might observe that `nr_throttled` increases rapidly during a load test.

That supports the hypothesis that the group is reaching a bandwidth restriction.

But there are two cautions.

First, counters should normally be examined as changes over a measurement interval, not as isolated cumulative totals.

Second, throttling statistics describe group-level behavior. They do not directly identify how many milliseconds of one customer request were delayed.

When multiple tasks are throttled concurrently, accumulated throttling accounting can differ substantially from a simple wall-clock duration.

We need correlation between the throttling evidence, workload demand, and observed application latency.

### CPU pressure

Linux also exposes Pressure Stall Information, or PSI.

CPU pressure can help describe time when runnable tasks are stalled waiting for CPU service.

At system level, `/proc/pressure/cpu` provides relevant statistics. Cgroup-level CPU pressure can also be available.

The `some` measure indicates time in which at least some tasks experience CPU-related stalls.

This answers a different question from CPU utilization.

Utilization describes consumed processing capacity.

Pressure describes waiting for processing capacity.

Throttle counters identify a particular resource-control mechanism.

These measurements complement one another.

A sensible investigator should not collapse them into a single concept called "CPU usage."

## 11. Runnable waiting versus other kinds of waiting

Imagine our worker has been ready to execute for thirty milliseconds but has not received CPU service.

That is scheduler-related delay.

Now imagine it is blocked for thirty milliseconds waiting for a database result.

Those periods may produce identical increases in wall-clock latency, but the remedies are different.

For runnable waiting, we inspect CPU competition, permitted processors, scheduling policy, and applicable quota constraints.

For database waiting, we examine the network and database operation.

For lock waiting, we examine the synchronization dependency.

A CPU dashboard cannot distinguish all these situations by itself.

### Scheduler statistics

Depending on kernel configuration, Linux scheduler statistics can expose task runtime and run-queue waiting information.

The `/proc/<pid>/schedstat` interface is one example.

Its fields can include runtime, run-queue wait time, and scheduling counts.

Scheduler tracing and tools such as `perf sched` can provide more detailed information.

The distinction between aggregate process behavior and individual thread behavior remains important.

An application with many threads may need thread-specific observation.

### The event-loop trap

Now return to Node.js.

An elevated event-loop delay metric does not automatically mean Linux is failing to schedule the JavaScript thread.

The event loop may be occupied by long synchronous JavaScript execution.

The process may be waiting for a native worker-pool operation.

Or the main JavaScript thread may be runnable but delayed by operating-system scheduling or CPU throttling.

The same symptom can have different causes.

We should examine event-loop delay alongside CPU profiles, thread behavior, cgroup counters, and relevant external waits.

The principle is simple: **measure the boundary where progress stops.**

## 12. When more workers create more contention

Suppose management wants to increase our document-processing worker count from four to twenty-four.

Before making the change, ask whether the service is CPU-bound or primarily waiting on external resources.

If its workers spend most of their time doing CPU-intensive transformations, twenty-four workers sharing half a CPU create a severe mismatch between demand and execution capacity.

Most workers cannot make useful progress simultaneously.

Some may be runnable and waiting. Others may compete for locks or other shared resources.

Context switching and cache disruption may increase.

And the CPU quota still imposes the same long-run ceiling.

Now imagine the workers instead spend most of their time waiting for independent external HTTP requests.

Additional concurrency could improve useful throughput, at least until another resource becomes saturated.

This is why concurrency settings must reflect workload behavior.

### Parallelism has limits

There are also computations that cannot efficiently use unlimited parallelism.

A single serial critical path remains limited by sequential work.

Shared locks can serialize otherwise independent threads.

Memory bandwidth can become a bottleneck before nominal CPU capacity is fully exploited.

Parallel workers may spend significant time coordinating or moving data rather than performing the intended computation.

More threads do not automatically mean more useful processing.

### Priority inversion

One more failure mode deserves attention.

Imagine a low-priority thread acquires a lock.

A high-priority thread needs the lock and blocks.

Medium-priority threads continue consuming CPU, preventing the low-priority lock holder from running promptly.

The high-priority thread is effectively delayed by a lower-priority task.

This is priority inversion.

Some synchronization mechanisms support priority inheritance to help address such situations, but support and semantics depend on the lock primitive and operating system.

We won't dive into memory ordering or synchronization algorithms here. Those belong to CS320-L07.

For now, remember that scheduling dependencies can interact with shared-resource dependencies.

A thread with high scheduling priority may still be unable to proceed if another thread holds something it needs.

## 13. Reconstructing the incident

We now have enough information to investigate our document processor systematically.

The initial observations were:

- Sixteen logical CPUs on the host.
- Around eight percent aggregate CPU utilization.
- Approximately forty milliseconds of computation per document.
- Occasional wall-clock completion times around three hundred milliseconds.
- A container with a CPU quota equivalent to half a logical CPU.

These facts suggest throttling, but they don't prove it alone.

We formulate three competing explanations.

**Hypothesis A — CPU quota exhaustion.** Under burst load, the container consumes its permitted CPU runtime and experiences throttling. We predict rising cgroup throttling counters correlated with delayed processing.

**Hypothesis B — A serialized application bottleneck.** One worker or critical section is saturated, regardless of spare host CPU capacity. We predict concentrated per-thread CPU execution or lock waiting, without requiring substantial quota throttling.

**Hypothesis C — External or runtime waiting.** Processing spends substantial time waiting for another resource. We predict elapsed time growing without a corresponding increase in CPU consumption or scheduler-related delay.

How do we discriminate?

First, collect a representative request or job timeline and determine which stage dominates elapsed time.

Second, inspect per-thread or relevant process CPU behavior rather than relying only on host averages.

Third, inspect the container's `cpu.max`, `cpu.stat`, permitted CPUs, and applicable scheduling restrictions.

Fourth, examine whether throttling and latency increase together as load rises.

Fifth, run a controlled comparison with a different CPU quota or lower computational concurrency, where it is safe to do so.

Suppose we observe the following pattern in our test environment.

As document concurrency rises, the CPU bandwidth is exhausted repeatedly. Throttling counters grow, and tail latency increases sharply. Reducing concurrent CPU work or increasing the quota reduces the delay without changing the document-processing algorithm.

That is strong evidence for the quota and concurrency mismatch.

It does not prove every individual delayed request was throttled, but it supports the broader causal mechanism.

### Choosing a fix

Several interventions are possible.

We could increase CPU allocation if the workload genuinely needs more capacity and the infrastructure budget allows it.

We could reduce the number of simultaneously CPU-intensive tasks so that work enters the runnable set at a more controlled rate.

We could separate CPU-heavy background processing from latency-sensitive request handling.

We could improve the algorithm if profiling shows avoidable computation.

Or we could introduce admission control, queueing, or load shedding so that incoming work doesn't grow beyond sustainable capacity.

These interventions address different aspects of the problem.

Increasing the timeout does not increase CPU capacity.

Adding threads does not increase quota.

Buying a larger host does not automatically change the container's resource restrictions.

And removing the CPU limit might improve this service while creating an unacceptable noisy-neighbor problem elsewhere.

The right fix must account for both the application and its resource environment.

## 14. The diagnostic framework worth using in interviews

Suppose an interviewer asks:

"Our API is slow, but the production CPU dashboard says only ten percent. What would you investigate?"

A weak answer is to list random tools or immediately recommend more replicas.

A stronger answer begins by questioning what the measurement actually represents.

Ten percent of which capacity? The entire host? A process? One CPU? A container's allocated budget?

Then distinguish execution from waiting.

Is the application consuming CPU continuously on one thread? Is it runnable but delayed? Is it being throttled? Is it blocked on I/O or synchronization?

Next, choose measurements that distinguish these mechanisms.

Inspect per-thread CPU utilization, effective CPU affinity, applicable cgroup quotas, throttling counters, scheduler pressure, and application-level timing.

Finally, propose an intervention only after identifying the restriction.

That is a senior-level answer because it begins with the system's actual execution model rather than a collection of performance superstitions.

---

# The Oral Examination

Answer without looking back. Explain the mechanism and, when possible, what evidence you would collect.

**Question 1 — The six-percent mystery**

A single-threaded application continuously occupies one logical CPU on a sixteen-logical-CPU server. Aggregate CPU utilization is low. Is the application CPU-bound?

**Question 2 — Two clocks**

A job takes five hundred milliseconds of elapsed time but consumes only fifty milliseconds of CPU. Name at least three possible explanations for the difference.

**Question 3 — The half-CPU container**

A cgroup has `cpu.max` set to `50000 100000`. Two CPU-intensive threads run simultaneously. Explain how both can be throttled despite the host having idle processors.

**Question 4 — Weight versus quota**

What is the difference between configuring a lower CPU weight and configuring a restrictive CPU bandwidth quota?

**Question 5 — The pointless upgrade**

A serial computation occupies one logical CPU continuously. Why might upgrading the machine from eight to thirty-two logical CPUs produce little improvement?

**Question 6 — Too many workers**

A queue-processing service doubles its CPU-intensive worker count, and tail latency increases without significant throughput improvement. What might have happened?

**Question 7 — The misleading event loop**

A Node.js application reports high event-loop delay. Why is that insufficient to conclude that the operating-system scheduler is the problem?

**Question 8 — The production investigation**

A container is slow. Host CPU is low, but cgroup throttling counters rise during traffic bursts. What would you test next before permanently increasing CPU allocation?

---

# Solutions and Discussion

## Solution 1 — Saturation is relative to the execution path

Yes. The application's critical thread may be completely CPU-bound even if the host has unused processors.

A single continuously executing thread can occupy approximately one of sixteen logical CPUs, representing around 6.25 percent of theoretical aggregate capacity under simple normalization.

Global capacity is not equivalent to capacity usable by one sequential task.

## Solution 2 — Elapsed time includes waiting

Possible explanations include waiting for an external response, blocking on a lock, waiting on the run queue, or being throttled by a CPU quota.

The observed wall-clock interval does not identify which mechanism occurred.

We should compare CPU service time with evidence about the relevant waiting boundaries.

## Solution 3 — The quota is aggregate runtime

The cgroup allows fifty milliseconds of aggregate CPU runtime per one-hundred-millisecond period.

Two threads can execute concurrently on separate logical processors and consume that allowance together.

After the relevant budget is exhausted, eligible tasks may be throttled until more budget becomes available.

Idle processors elsewhere don't override the cgroup restriction.

## Solution 4 — Relative sharing versus maximum allocation

A CPU weight influences how relevant contended CPU capacity is distributed among groups.

A quota constrains the maximum CPU runtime allowed over its configured period.

A low-weight group may use idle CPU capacity when contention is absent.

A quota can cause throttling even when the machine has spare capacity.

## Solution 5 — Sequential work needs parallelism to use more processors

One sequential thread cannot automatically execute on multiple logical CPUs at the same instant.

Adding processors helps only if the workload can exploit additional parallel execution or benefits indirectly through reduced competition.

For a purely serial CPU-bound critical path, faster execution per thread or algorithmic improvements may be more valuable than additional cores.

## Solution 6 — More contention without more capacity

The additional workers may have increased runnable competition, scheduling overhead, cache disruption, or shared-resource contention.

The resource quota or actual CPU capacity did not increase.

Measure throughput, tail latency, runnable waiting, and resource restrictions before selecting a worker count.

## Solution 7 — Event-loop delay has multiple causes

The main JavaScript thread may be executing long synchronous callbacks, waiting to be scheduled, affected by CPU throttling, or delayed by other runtime behavior.

Event-loop delay describes a symptom at the runtime level.

It does not identify the operating-system mechanism.

Combine runtime profiling with scheduling and cgroup evidence.

## Solution 8 — Test the causal relationship

Compare latency and throttling under controlled workload levels.

Where safe, vary the CPU limit or reduce CPU-intensive concurrency while holding other conditions as constant as possible.

Check whether latency improves and whether cgroup throttling diminishes.

Also verify that no separate serial or external bottleneck dominates the critical path.

A quota increase is justified only when evidence shows that additional CPU capacity will address the actual restriction.

---

# The Mental Model Worth Keeping

When an application is slow, imagine every execution thread moving through three situations:

**Running:** It is receiving CPU service.

**Runnable but not running:** It has work ready, but CPU service isn't currently available or permitted.

**Blocked:** It needs another event or resource before it can continue.

Then ask which boundary is responsible: physical capacity, usable processors, scheduling competition, quota, or an unrelated dependency.

**CPU utilization measures work being performed. It does not, by itself, explain work waiting to be performed.**

# Next Lecture — Virtual Memory, Pages, and Address Translation

We've learned how the operating system gives execution time to processes and threads.

But a running program also believes it owns an enormous private world of memory addresses.

Two processes can use the same numerical address without accessing the same physical memory.

An allocation may exist in virtual memory without occupying a physical page yet.

And a memory access may cause the processor to enter the kernel even though the application has made no explicit system call.

In CS320-L03, we'll investigate the machinery that makes all of this possible: virtual address spaces, page tables, translation lookaside buffers, page faults, memory mappings, and copy-on-write.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Lab — See CPU Scheduling and Quotas Yourself

The following experiments are intended for a disposable local Linux or Docker environment. They don't require paid services.

## Lab A — Wall time versus CPU time

This Python experiment performs a short amount of CPU work, then deliberately sleeps.

```python
import time

start_wall = time.perf_counter()
start_cpu = time.process_time()

# Consume approximately 0.3 seconds of process CPU time.
until_cpu = start_cpu + 0.3
value = 0

while time.process_time() < until_cpu:
    value += 1

# Simulate an external wait.
time.sleep(0.5)

wall = time.perf_counter() - start_wall
cpu = time.process_time() - start_cpu

print(f"Wall time: {wall:.3f} s")
print(f"CPU time:  {cpu:.3f} s")
print(f"Counter:   {value}")
```

The measured values will vary.

The key observation is that sleeping increases elapsed time without consuming a corresponding amount of processor execution time.

**Question:** Why would a network-heavy backend demonstrate this distinction even when none of its own code explicitly calls `sleep()`?

## Lab B — Read the CPU budget

On a system using cgroup v2:

```bash
cat /sys/fs/cgroup/cpu.max
cat /sys/fs/cgroup/cpu.stat
cat /sys/fs/cgroup/cpu.weight
```

Depending on your environment, these files may be unavailable, may represent an ancestor cgroup, or may differ from the container's effective limits.

The `cpu.max` value `max 100000` generally indicates no local bandwidth maximum at that cgroup level, not necessarily an absence of limits anywhere in the hierarchy.

**Question:** What is the difference between the maximum runtime, the CPU weight, and the observed usage statistics?

## Lab C — Reproduce CPU quota effects in Docker

Compare a short CPU-bound Python task under two different CPU allocations.

First, run with a restrictive quota:

```bash
docker run --rm -i --cpus=0.5 python:3.12-alpine python - <<'PY'
import time

start_wall = time.perf_counter()
start_cpu = time.process_time()

while time.process_time() - start_cpu < 0.4:
    pass

print("Wall:", round(time.perf_counter() - start_wall, 3))
print("CPU:", round(time.process_time() - start_cpu, 3))
PY
```

Repeat the same experiment with a larger quota:

```bash
docker run --rm -i --cpus=1.5 python:3.12-alpine python - <<'PY'
import time

start_wall = time.perf_counter()
start_cpu = time.process_time()

while time.process_time() - start_cpu < 0.4:
    pass

print("Wall:", round(time.perf_counter() - start_wall, 3))
print("CPU:", round(time.process_time() - start_cpu, 3))
PY
```

The first experiment should often have noticeably greater elapsed time under ordinary Linux CPU-bandwidth enforcement.

The second experiment is still one CPU-bound thread. Raising the quota above one CPU does not automatically make that thread execute in parallel.

These are observations to investigate rather than guaranteed timings; host load, runtime initialization, and the particular Docker environment can affect the results.

**Question:** Why does a quota below one CPU constrain a single busy thread, while increasing the quota above one CPU may provide little additional benefit to the same thread?

## Lab D — Observe throttling counters

Run a disposable container with a restricted CPU allocation:

```bash
docker run --rm -i --cpus=0.5 python:3.12-alpine python - <<'PY'
import time
from pathlib import Path

stat = Path("/sys/fs/cgroup/cpu.stat")
budget = Path("/sys/fs/cgroup/cpu.max")

if budget.exists():
    print("CPU budget:", budget.read_text().strip())

print("Before:")
if stat.exists():
    print(stat.read_text())

start_cpu = time.process_time()
while time.process_time() - start_cpu < 1.0:
    pass

print("After:")
if stat.exists():
    print(stat.read_text())
PY
```

Where the CPU controller exposes throttling statistics, compare `nr_periods`, `nr_throttled`, and `throttled_usec` before and after.

Do not interpret cumulative `throttled_usec` as a direct stopwatch measurement for this script. Its accounting scope can include multiple runnable tasks and hierarchical restrictions.

## Lab E — Inspect task scheduling information

On Linux, for your own shell:

```bash
ps -o pid,ppid,stat,psr,pcpu,comm -p $$
taskset -pc $$
cat /proc/$$/schedstat
```

Availability depends on installed tools, permissions, and kernel configuration.

The affinity output describes which logical CPUs the task is permitted to use, subject to applicable restrictions.

Where scheduler statistics are available, `/proc/<pid>/schedstat` can expose runtime and run-queue waiting information.

**Question:** Why is looking at the affinity mask more informative than looking only at the number of processors installed in the machine?

## Lab F — The investigation worksheet

You are given the following hypothetical evidence:

```text
Host:
  Logical CPUs: 16
  Average CPU utilization: 8%

Worker:
  CPU demand per job: approximately 40 ms
  Job completion p95: 300 ms
  CPU-intensive worker threads: 8

Container:
  cpu.max: 50000 100000
  cpu.stat nr_throttled: increasing under load
  Effective CPU affinity: multiple logical CPUs
```

Write a short diagnosis containing:

1. Your leading hypothesis.
2. Two alternative explanations you would still consider.
3. One measurement that would distinguish each explanation.
4. One reversible experiment.
5. The smallest justified remediation.

Then explain why increasing the thread count to sixteen is unlikely to solve the CPU-capacity restriction.

The goal is not to guess the correct tuning value. The goal is to construct a defensible investigation.

---

# Further Reading

Authoritative references:

1. Linux Kernel Documentation — EEVDF Scheduler  
   https://docs.kernel.org/scheduler/sched-eevdf.html

2. Linux Kernel Documentation — CFS Scheduler (historical design and fair scheduling concepts)  
   https://docs.kernel.org/scheduler/sched-design-CFS.html

3. Linux Kernel Documentation — Control Group v2, CPU controller  
   https://docs.kernel.org/admin-guide/cgroup-v2.html

4. Linux Kernel Documentation — Scheduler Statistics  
   https://docs.kernel.org/scheduler/sched-stats.html

5. Linux Kernel Documentation — Pressure Stall Information  
   https://docs.kernel.org/accounting/psi.html

6. Linux Manual Pages — CPU Affinity  
   https://man7.org/linux/man-pages/man2/sched_setaffinity.2.html

7. Kubernetes Documentation — Resource Management for Pods and Containers  
   https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/

Related programme chapters:

- CS320-L01 — The Kernel, Processes, and Containers
- CS220-L06 — Managed Runtimes: Node.js, CPython, and the JVM
- CS430-L03 — Scaling and Load Management
- SE450-L04 — Scheduling, Resources, and Autoscaling

---

## Dense Cheatsheet — Interview Glance Card

```text
CS320-L02 — CPU SCHEDULING, QUOTAS, CONTENTION

THE CENTRAL QUESTION
  Where did the missing elapsed time go?

EXECUTION STATES
  Running      = executing on logical CPU
  Runnable     = ready but not currently executing
  Blocked      = waiting for event, I/O, lock, etc.
  Linux R      = running OR runnable
  Linux S/D    = different categories of sleep/wait

TWO CLOCKS
  Wall time    = elapsed real time
  CPU time     = accounted processor execution
  CPU time can exceed wall time for multithreaded process
  Process CPU time != request CPU time

SCHEDULING
  Kernel schedules tasks (commonly threads)
  Preemption   = running task interrupted for another
  Context swap = state preservation/restoration and overhead
  Fairness     = distribute finite CPU time under policy
  CFS          = historical vruntime-based fair scheduling
  EEVDF        = newer eligible/virtual-deadline selection
  Priorities   = scheduling policy, NOT extra CPU capacity

MULTICORE
  One busy thread on 16 CPUs ≈ 6.25% aggregate host use
  Serial work does not automatically use idle cores
  Affinity     = allowed logical CPU set for thread
  SMT          = logical CPUs may share physical core
  More cores   != proportional performance automatically

CGROUP V2 CPU
  cpu.max      = maximum aggregate runtime / period
  cpu.weight   = relative share under contention
  cpu.stat     = CPU usage and optional throttle counters
  cpu.pressure = CPU-related stall information

EXAMPLE
  cpu.max = 50000 100000
  => 50 ms CPU service per 100 ms accounting period
  => equivalent to 0.5 CPU long-run capacity

  2 parallel threads × 25 ms execution
  => 50 ms aggregate CPU runtime
  => quota may be exhausted early in period

HOST PARADOX
  0.5 CPU / 16 logical CPUs = 3.125% host capacity
  Container can be quota-saturated while host idle

THROTTLING
  Budget exhausted -> eligible tasks may wait for refill
  Latency spikes possible even when work CPU cost unchanged
  nr_throttled increasing = evidence of bandwidth restriction
  Throttle accounting != direct per-request delay

CPU WEIGHT VS QUOTA
  Weight: how competing eligible groups share capacity
  Quota: max allowed runtime over configured period
  Low weight may still use idle available CPU
  Restrictive quota may throttle even with idle host CPUs

KUBERNETES BRIDGE
  CPU request = scheduling/resource-share implications
  CPU limit   = CPU bandwidth ceiling, commonly cgroup-based
  Node CPU idle != container has available quota

CONTENTion
  Runnable wait = waiting for processor execution
  Lock wait     = waiting for synchronization resource
  I/O wait      = waiting for external/kernel operation
  Priority inversion = high-priority task waits for low-priority
                       lock holder delayed by other tasks

TOO MANY WORKERS
  More runnable tasks -> more scheduling competition
  Possible cache disruption, lock contention, queueing
  CPU-intensive workload needs usable CPU capacity
  I/O-bound workload may benefit from greater concurrency
  Benchmark throughput AND tail latency

DIAGNOSIS
  1. Define symptom and measure its scope
  2. Compare wall time with CPU consumption
  3. Inspect per-thread/core activity
  4. Inspect affinity and effective CPU constraints
  5. Read cpu.max, cpu.stat, CPU pressure
  6. Distinguish quota, runnable wait, locks, external waits
  7. Test one reversible change
  8. Verify latency AND resource behavior

BAD FIRST FIXES
  More threads without more CPU capacity
  More hardware without checking quota
  Longer timeout without reducing delay
  Blind priority or affinity manipulation
  Bigger CPU limit without understanding isolation costs

SENIOR INTERVIEW ANSWER
  "First I'd establish what CPU percentage is relative to.
   Then I'd separate CPU execution from runnable, blocked,
   and throttled time. I'd inspect per-thread utilization,
   affinity and cgroup accounting, and run a controlled test
   before changing worker concurrency or CPU allocation."

DURABLE MENTAL MODEL
  Running != runnable != blocked.
  Host capacity != task's usable CPU budget.
  CPU utilization != CPU availability.
```
