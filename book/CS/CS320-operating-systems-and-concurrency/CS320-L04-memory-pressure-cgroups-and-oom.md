---
id: CS320-L04
course: CS320
title: "Memory Pressure, Cgroups, and OOM"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: CS320-L03
next: CS320-L05
---




# CS320 — Operating Systems and Concurrency

## Lecture 04: Memory Pressure, Cgroups, and OOM

*Your Node.js service has a memory limit of 512 mebibytes. Its JavaScript heap uses only 94. The host has several gigabytes of available RAM. Yet the kernel kills your process for running out of memory. What exactly ran out?*

# Part I — Intuition

## The picture to carry in your head

Imagine a busy logistics warehouse.

The warehouse contains shelves holding merchandise, temporary packing stations, delivery equipment, and a large collection of frequently requested products kept near the entrance.

The warehouse manager tries to make good use of every square meter.

Empty space is not particularly useful. If there's room to store products that might be needed tomorrow, the manager stores them there.

But the warehouse serves several companies, and each company has its own allocation.

Company A might be entitled to only five hundred square meters, even though the entire building contains twenty thousand.

Now imagine Company A beginning an enormous shipping operation.

It needs packing tables, temporary storage, workers, equipment, and room for unpacked merchandise.

Its manager checks the number of boxes currently on the main shelves and announces:

"We're fine! We're using only twenty percent of our storage capacity."

But the packing stations, equipment, and temporary inventory consume space too.

The company runs out of its assigned area.

Meanwhile, the building still has enormous amounts of unused capacity.

This is approximately the problem our document-processing service faces.

Its JavaScript heap is only one part of its memory usage. The operating system accounts for other kinds of memory, including native allocations, cached file data, and relevant kernel resources.

And the container may have a memory budget far smaller than the host's total physical RAM.

Our goal today is to understand that warehouse well enough to explain exactly when it becomes slow, when it can recover, and when the operating system decides that something must die.

## 1. Memory isn't one number

In CS320-L03, we learned that applications operate within virtual address spaces.

A virtual address does not necessarily correspond to a physical page currently resident in RAM.

Now we need to ask a different question.

When physical memory is actually consumed, what is occupying it?

Some memory holds ordinary application data.

Some holds the application's executable code and runtime structures.

Some belongs to native libraries and buffers.

Some contains thread stacks.

Some is used by the kernel itself.

And some holds cached filesystem data so that repeated reads can avoid expensive storage operations.

A Node.js application sees part of this world through its runtime's memory measurements.

But the JavaScript heap is not the complete process footprint.

And the process footprint is not necessarily the entire amount accounted to its container.

These are different layers of observation.

Think of three accountants.

The first tracks JavaScript-managed objects.

The second tracks resident pages mapped into a process.

The third tracks memory charged to a resource-control group.

Their reports overlap, but they do not describe identical boundaries.

If you add their totals together, you may count the same memory several times.

The important question isn't simply, "How many megabytes?"

It's **"Which boundary does this measurement describe?"**

## 2. Why Linux deliberately fills RAM with cache

Let's return to our warehouse.

A product may be stored in a distant building, requiring an expensive delivery every time someone requests it.

If customers repeatedly order the same product, it makes sense to keep a copy nearby.

Linux does something similar with file data.

The operating system can retain recently accessed file pages in physical memory. This is the **page cache**.

A file that has already been read may be available from RAM on the next access.

That can be much faster than retrieving it from storage.

Consequently, a Linux machine with very little entirely unused RAM isn't necessarily unhealthy.

Some memory may be occupied by useful caches that the operating system can reclaim when necessary.

But not every cached page is equally easy to discard.

A clean page whose contents already exist in its backing file can often be reclaimed relatively cheaply.

A dirty page contains changes that may require writeback first.

And some memory cannot simply be thrown away because doing so would destroy information the application still needs.

That brings us to memory pressure.

## 3. Reclaim: the warehouse begins clearing space

Suppose the document processor begins decoding a large PDF.

It needs additional physical memory.

The kernel must find room for the requested pages.

If sufficient usable memory is available, the allocation can proceed.

If not, the kernel may try to reclaim memory.

It can identify suitable cached pages to discard, arrange writeback where required, or use other memory-management mechanisms.

But reclaim is not necessarily instantaneous.

Finding pages costs work.

Writing dirty data takes time.

And discarding pages that the application needs again shortly can cause those pages to be retrieved repeatedly.

This means memory scarcity can produce a performance problem long before it produces a crash.

The system might spend substantial time reclaiming and reloading memory instead of performing useful application work.

When that cycle becomes severe, we call it **thrashing**.

The warehouse manager is spending the entire day moving boxes out of the building and bringing the same boxes back.

Everybody is busy.

Almost nothing useful gets shipped.

## 4. A container has its own memory budget

Our document processor runs inside a container with a memory limit of 512 MiB.

The host has sixteen gigabytes of RAM.

Why can't the container simply use another gigabyte?

Because resource allocation is not necessarily determined by global physical availability.

Linux cgroups provide hierarchical accounting and control of resource consumption.

For memory, a cgroup can have a hard maximum.

The kernel accounts relevant memory consumption to the group.

When new demand approaches the hard boundary, the kernel may attempt to reclaim suitable memory.

If the demand cannot be satisfied within the applicable restrictions, an out-of-memory condition can occur.

The kernel may then kill a process.

This can happen even when the host has substantial memory available outside the container's budget.

The policy boundary is real.

It isn't a reflection of how many physical memory chips happen to be installed.

## 5. Memory pressure and OOM are different stages

Imagine our document processor gradually increasing its memory usage.

At first, everything works normally.

Then the operating system begins reclaiming cached data more aggressively.

Latency rises.

Later, the application repeatedly needs pages that were recently reclaimed.

Performance becomes unstable.

Finally, if the relevant limit cannot be satisfied through reclaim and the applicable mechanisms, an out-of-memory kill may occur.

These aren't necessarily four distinct steps that every system experiences in exactly this order.

A sudden allocation spike can produce a rapid failure. Some systems encounter reclaim pressure without an eventual kill. Others can swap inactive pages and continue operating acceptably.

But the progression illustrates a critical idea:

**Memory pressure is a performance condition. Out-of-memory termination is a possible failure outcome.**

You should not wait for an OOM kill before treating memory pressure as important.

And an OOM kill doesn't automatically prove the application has a memory leak.

A perfectly correct application can legitimately require more memory than its allocated budget.

## Three questions before the Deep Dive

1. Why doesn't a stable JavaScript heap prove that a container's total memory use is stable?
2. Why might Linux intentionally keep useful data in RAM even when applications aren't actively using that data?
3. How can a container run out of memory while the host still has gigabytes available?

If you can explain all three, you understand the essential relationship between application memory, kernel-managed memory, and resource limits.

Now we'll trace the mechanisms precisely.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The document processor that disappeared

It's Wednesday, 14:37.

Our PDF-processing service is running normally.

It accepts customer documents, extracts text, decodes embedded images, builds structured results, and stores those results in PostgreSQL.

The application runs in Kubernetes, inside a container with a 512-MiB memory limit.

At 14:38, a customer uploads an unusually image-heavy PDF.

While it's being processed, three additional documents arrive.

The worker begins decoding several documents concurrently.

A few seconds later, the container terminates.

Kubernetes starts a replacement.

There is no ordinary JavaScript exception in the application logs. The final log message reports that another image-decoding stage has started.

The previous container's termination reason is recorded as `OOMKilled`.

An engineer opens the dashboard.

The JavaScript heap had recently been using only 94 MiB.

The container limit was 512 MiB.

The host also appeared to have several gigabytes of available RAM.

Someone concludes that Kubernetes must be wrong.

Another engineer suspects a memory leak.

A third proposes increasing V8's heap limit.

All three reactions are premature.

We haven't yet established what was consuming the container's memory budget.

The central investigative question is:

**Which memory was being charged to the container immediately before termination, and what workload caused that demand?**

## 2. The three accounting boundaries

Let's begin with the measurements.

Our service exposes Node.js memory statistics, Linux process statistics, and container-level metrics.

Each describes a different aspect of memory behavior.

### The runtime's view

Node.js exposes `process.memoryUsage()`.

Several fields are especially relevant.

`heapUsed` describes memory used within V8's managed heap.

`heapTotal` describes the size of the managed V8 heap allocation under the metric's semantics.

`external` reports certain C++-associated memory managed through V8-related accounting.

`arrayBuffers` describes memory allocated for ArrayBuffers and SharedArrayBuffers, including Node.js Buffers under the documented tracking behavior.

Importantly, `arrayBuffers` is included in `external`.

The two fields are not independent buckets.

Now imagine that our PDF parser creates a large Node.js Buffer.

The Buffer is represented by a JavaScript object, but its backing memory is not simply another ordinary collection of JavaScript object properties occupying the managed heap.

The runtime may therefore show much greater growth in external or ArrayBuffer-related memory than in `heapUsed`.

A native image-decoding library may also allocate memory through native mechanisms.

Some of that memory may not be fully represented by the runtime's external-memory counters.

Therefore, a small V8 heap doesn't imply a small process.

A subtle additional point: in a process using Node.js worker threads, `rss` is process-wide, while several other `process.memoryUsage()` fields describe the current JavaScript thread's isolate. Comparing them without understanding scope can introduce yet another misleading interpretation.

### The process's view

Linux exposes measurements such as virtual memory size, RSS, and PSS.

We encountered these in L03.

Virtual size describes mapped address-space extent, not necessarily resident physical RAM.

**Resident Set Size**, or RSS, describes resident physical pages mapped into the process, under the relevant accounting conventions.

It can include JavaScript-related pages, native allocations, stacks, code, and mapped file pages.

**Proportional Set Size**, or PSS, accounts for shared resident pages proportionally.

This matters when multiple processes map the same physical memory.

Adding their RSS values can count shared physical pages several times.

But even process RSS is not the whole container story.

### The cgroup's view

The memory cgroup accounts relevant consumption associated with a group of processes and kernel-managed resources.

Depending on the kernel and workload, that includes anonymous memory, file-backed cache, and kernel memory categories.

Some charged pages aren't reflected as resident pages mapped into one application's address space.

Some pages are shared between processes or groups.

And a cgroup can contain multiple processes.

Consequently, the cgroup's charged-memory total is not simply the sum of V8 heap sizes or process RSS values.

We now have three overlapping views.

The runtime helps explain language-managed and runtime-related memory.

The process view helps explain resident mappings.

The cgroup view helps explain the budget enforced by the kernel.

For our incident, the cgroup boundary is decisive because that is where the memory limit applies.

## 3. Why adding memory metrics produces nonsense

Imagine an engineer collecting these illustrative numbers:

The JavaScript heap reports 94 MiB.

External memory reports 170 MiB.

ArrayBuffers report 145 MiB.

Process RSS reports 390 MiB.

The engineer adds them all together and announces that the application is consuming 799 MiB.

That calculation is invalid.

The ArrayBuffer figure is already included in the external-memory figure.

Resident memory associated with the managed heap and external allocations also contributes to process RSS when those pages are resident.

Adding them again double-counts memory.

Similarly, parts of process RSS may already correspond to pages charged within the container's memory cgroup.

The correct approach isn't to construct one enormous sum.

It's to use the measurements to explain one another.

A large gap between `heapUsed` and RSS suggests substantial memory outside the ordinary managed heap.

A large gap between process RSS and the cgroup's charged total suggests examining other processes, file cache, kernel charges, accounting scope, and shared resources.

But don't assume the difference between two numbers represents one independently measurable bucket.

**Memory metrics overlap. Their relationships must be interpreted, not blindly added.**

This is one of the most useful lessons to remember during production investigations.

## 4. The page cache: useful memory that can become contested

Our service repeatedly reads large PDFs.

Linux may retain file-backed pages in the page cache.

The intention is straightforward: avoid repeated storage operations when the same data is requested again.

Suppose an application reads a hundred-mebibyte file.

Some of its contents may remain cached after the file-reading operation finishes.

If another request accesses those pages, the kernel may satisfy the read from RAM.

This improves performance.

But the cached data occupies physical memory and may contribute to the relevant cgroup's accounting.

### Clean pages

A clean file-backed page matches data that can be obtained from the backing object.

If the page is eligible for reclaim, the kernel can often discard the resident copy.

Later access can retrieve it again.

This makes clean file cache a useful source of reclaimable memory.

However, reclaiming an actively used page may be a poor performance decision.

If the application immediately needs it again, the kernel must retrieve or reestablish the page.

The page was reclaimable, but perhaps not cheaply reclaimable from the workload's perspective.

### Dirty pages

A dirty file-backed page contains modifications not yet written to the backing storage.

Before reclaim, the kernel may need to arrange writeback.

That introduces storage work and potentially waiting.

Dirty data is not simply disposable.

### A crucial complication: not all 'file' accounting is ordinary disk cache

Linux cgroup v2's `memory.stat` field named `file` includes filesystem-cache categories and also certain tmpfs and shared-memory accounting.

Those are not all identical in reclaim behavior.

A tmpfs-backed temporary file, for example, uses memory-backed filesystem storage. Its pages may be swap-backed under relevant configurations rather than simply discarded and reread from a persistent disk file.

Therefore, seeing a large `file` value is not sufficient to conclude that all of it can be reclaimed cheaply.

Our PDF worker may write temporary decoded images into a tmpfs mount.

That can create substantial memory pressure even though the application developer describes the operation as "writing temporary files."

The storage abstraction doesn't eliminate the underlying memory cost.

## 5. Reclaim: when free memory stops being enough

Now imagine the container's charged memory approaching its configured limit.

The application asks for more physical backing.

The kernel must determine whether it can satisfy the demand under the applicable memory constraints.

One response is reclaim.

The kernel identifies pages that may be released or moved out of physical memory.

It may reclaim eligible clean file-backed pages.

It may arrange writeback for dirty pages.

Under appropriate configuration, it may swap eligible anonymous pages.

Or it may perform other reclaim operations and adjustments.

But reclaim can be expensive.

### Background versus direct reclaim

Linux can perform reclaim work in the background through kernel mechanisms such as `kswapd`.

It can also require allocating tasks to participate in reclaim when an allocation cannot proceed without obtaining memory.

This is commonly called direct reclaim.

Imagine our request handler attempting to allocate memory for decoded image data.

Instead of immediately receiving the requested pages, it may spend time in memory-reclaim activity.

The user sees a slow request.

But the application didn't necessarily execute more JavaScript instructions.

Some of the elapsed time was consumed trying to make memory available.

This is another example of why wall-clock time and useful application execution aren't interchangeable.

### Reclaim can damage the working set

Now suppose our service repeatedly accesses a reference dataset.

Under memory pressure, the kernel reclaims some of the dataset's resident pages.

The application soon needs them again.

They must be brought back or reestablished.

Then memory pressure causes more reclaim.

The same pages move repeatedly between useful and reclaimed states.

The system spends substantial effort managing memory instead of processing customer documents.

This is the intuition behind **thrashing**.

It's not simply "RAM is ninety-five percent full."

It's "the workload's active memory demand cannot be served efficiently with the memory currently available."

## 6. The working set is the real capacity question

A useful concept is the **working set**: the collection of memory pages a workload actively needs over a relevant period.

The exact definition depends on the time window and measurement approach.

But its engineering significance is substantial.

A process may have a large address space while actively touching only a small portion.

That can be perfectly efficient.

Another process may have a smaller resident footprint but repeatedly touch almost every page.

If its active working set doesn't fit within available memory, reclaim can become extremely costly.

Now consider our PDF processor.

Each document may require temporary decoded images, parsing structures, buffers, and application objects.

One document may fit comfortably inside the container's memory budget.

Four documents concurrently may not.

The application doesn't necessarily leak memory.

It may simply have a working set that grows with concurrent workload.

### A simple capacity estimate

Suppose our service has a baseline memory demand of approximately 150 MiB.

Each active image-heavy document adds roughly 110 MiB of peak charged demand under a representative workload.

With one active document, the rough peak is 260 MiB.

With two, approximately 370 MiB.

With three, approximately 480 MiB.

With four, approximately 590 MiB.

Our configured limit is 512 MiB.

These are illustrative planning figures, not a claim that real cgroup charges always add linearly. Shared pages, caching, timing, and other memory behavior complicate the measurement.

But the arithmetic reveals the design problem.

The application was sized for ordinary operation but permitted a concurrency level that could exceed its memory budget.

Even if all temporary memory were eventually released, the peak might already be fatal.

**A process can have perfectly bounded long-term memory use and still be killed because its temporary peak is too large.**

That distinction matters enormously for backend services.

## 7. Swapping: a bigger virtual world with a storage bill

We've learned that anonymous memory cannot necessarily be discarded like clean file cache.

Consider a page containing an in-memory data structure modified by the application.

If the kernel simply throws the page away, the process loses information.

One possible alternative is swap.

When configured and permitted, Linux can move eligible anonymous-memory contents out of RAM and preserve them in swap storage or use relevant compressed swap mechanisms.

If the process later accesses the page, the system must restore the contents.

This can involve substantial additional work.

### Swap isn't universally bad

It's tempting to say that swapping always indicates a broken system.

That's too simplistic.

If a process has a large amount of genuinely inactive memory, moving some of those pages out of RAM may free capacity for more useful data.

Occasional swap activity can therefore be reasonable.

The real problem appears when a workload repeatedly accesses pages that have been swapped out.

Now physical memory pressure turns into repeated storage operations and long delays.

The application may make very little useful progress.

### Swap changes the failure mode

Suppose our PDF processor has a 512-MiB memory budget and access to a controlled amount of swap.

Swapping eligible pages might help the workload survive certain temporary pressures.

But it could also turn an otherwise rapid failure into severe latency if the active working set is simply too large.

Swap is not a substitute for understanding resource demand.

Nor does the presence of host swap guarantee that an individual container is allowed to use it.

Linux cgroup v2 provides swap-related controls, including `memory.swap.current` and `memory.swap.max`.

The latter constrains swap usage under the controller's semantics.

A system may also use compressed swap facilities, with their own resource costs and configuration.

The exact behavior depends on the kernel, deployment platform, and cgroup hierarchy.

For a production service, the important questions are whether swap is available, whether the workload benefits from it, and whether the resulting latency is acceptable.

## 8. Cgroup v2: the boundary that killed our container

Now we reach the decisive mechanism.

A Linux container typically runs processes associated with one or more cgroups.

The memory controller accounts relevant usage and enforces configured resource policies.

In cgroup v2, several interfaces are particularly useful.

### `memory.current`

This reports the current memory usage charged to the cgroup and its descendants under the controller's rules.

It is not simply the JavaScript heap size.

Nor is it necessarily equal to the sum of process RSS values.

For our incident, this is much closer to the resource quantity whose limit we're investigating.

### `memory.max`

This defines a hard memory limit for the cgroup.

Our container's maximum is configured to 512 MiB.

As charged usage approaches the hard limit, the kernel attempts applicable reclaim and allocation handling.

If the memory demand cannot be satisfied within the relevant restrictions, the cgroup may encounter an out-of-memory condition.

The kernel may invoke the OOM killer.

Memory limits are not necessarily enforced by rejecting every access at the exact instant a counter reaches the configured number. Certain temporary overages and reactive behavior are possible.

But `memory.max` establishes the important hard budget.

### `memory.high`

This is different from the hard maximum.

`memory.high` establishes a threshold associated with reclaim pressure and throttling.

When usage exceeds it, processes may be forced into more aggressive reclaim behavior and delayed.

Crossing `memory.high` does not, by itself, invoke the OOM killer.

This is an extremely useful distinction.

A service may become painfully slow because of memory-related throttling without ever hitting a hard OOM condition.

### `memory.low` and `memory.min`

These provide forms of memory protection against reclaim.

Broadly, `memory.low` offers best-effort protection within the effective configured boundary.

`memory.min` provides stronger protection under its documented rules.

Both interact with cgroup hierarchy and available resources.

We do not need to memorize their complete kernel algorithms in this course.

We do need to recognize that memory resource controls are not merely a single maximum-value knob.

They can influence how competing workloads experience reclamation pressure.

### Hierarchical constraints

Cgroups are hierarchical.

A process may belong to a group that itself exists beneath other resource-control groups.

A limit or restriction at an ancestor can influence descendants.

This means an apparently generous setting at one level doesn't necessarily guarantee freedom from a tighter effective restriction elsewhere.

When diagnosing resource behavior, identify the actual hierarchy and relevant enforcement boundary.

## 9. `memory.stat`: finding where the budget went

Our service has died, but suppose we've retained sufficient memory telemetry leading up to the incident.

We know charged memory approached the configured limit.

What was consuming it?

The cgroup v2 interface `memory.stat` provides a breakdown of relevant memory-accounting categories.

Some especially useful fields include:

**`anon`** — accounting related to anonymous memory.

**`file`** — filesystem-backed cache and related categories, including tmpfs and shared-memory cases under the documented semantics.

**`kernel`** — relevant kernel-memory charges.

**`pagetables`** — memory used for page tables.

**`sock`** — relevant network socket-buffer charges.

There are also fields for dirty data, writeback activity, active and inactive memory, and other details.

The exact set depends on kernel version and configuration.

### Don't treat the fields as an accounting spreadsheet

Some fields describe subsets of other fields.

Some describe current page-list state rather than disjoint ownership categories.

Some represent particular activity or behavior.

Therefore, adding every visible field will not produce a valid total.

Instead, use the fields to identify trends and dominant categories.

If anonymous memory rises sharply during image decoding, investigate application and native allocation demand.

If file-backed memory grows with temporary files, investigate cache and tmpfs behavior.

If kernel-related charges rise, inspect the relevant resources and kernel accounting.

The purpose is to locate the mechanism, not to manufacture a single perfect number from overlapping counters.

## 10. `memory.events`: separating pressure from termination

Another interface, `memory.events`, records important memory-controller events.

Its counters are particularly useful when the application logs don't contain a complete explanation.

Several fields matter.

**`high`** records relevant events associated with exceeding the high threshold and undergoing reclaim or throttling behavior.

**`max`** records occasions when the group was about to exceed its hard memory boundary.

**`oom`** records certain out-of-memory situations where allocation was about to fail under the controller's semantics.

**`oom_kill`** records processes belonging to the cgroup killed by an OOM killer.

These fields are related but not equivalent.

### An increase in `max` isn't proof of a kill

Suppose the cgroup approaches its hard maximum.

The kernel attempts reclaim.

Enough memory becomes available.

The allocation succeeds.

The event counter may record pressure against the maximum, but no OOM kill was required.

### An increase in `oom` isn't automatically the same as `oom_kill`

Out-of-memory accounting and process termination are distinct observations.

Not every allocation failure or OOM-related event produces the same outcome.

The kernel documentation defines the counters precisely, and some allocation contexts behave differently.

### Hierarchical versus local events

`memory.events` is hierarchical by default: its counters can include events from descendant cgroups.

`memory.events.local` provides a local perspective.

This matters when investigating nested workload structures.

And because counters accumulate, we usually care about how they change during the relevant interval.

A counter showing ten historical OOM kills doesn't prove the current incident caused all ten.

We need timing.

## 11. The process may become slow before it dies

Now imagine we collect the following illustrative evidence.

At 14:38, memory usage begins rising.

At 14:38:04, memory-pressure measurements become elevated.

At 14:38:06, the number of high-threshold events increases.

At 14:38:08, request latency rises sharply.

At 14:38:10, usage approaches the hard maximum.

At 14:38:11, the kernel records an OOM kill.

This sequence suggests that the application experienced reclaim-related distress before termination.

The early latency isn't necessarily explained by JavaScript garbage collection.

It may reflect kernel memory-management work, including reclaim and stalled allocations.

### Pressure Stall Information

Linux exposes **Pressure Stall Information**, or PSI.

Memory PSI helps quantify time during which tasks are stalled because of memory-related resource conditions.

At system level, it is available through `/proc/pressure/memory` on supporting systems.

At cgroup level, `memory.pressure` provides a relevant group-level view when available.

The `some` measure represents periods during which at least some tasks experience relevant stalls.

The `full` measure represents periods in which all non-idle tasks in the observed scope are stalled simultaneously.

These measurements provide a different perspective from memory utilization.

A container may use much of its budget without experiencing severe stalls.

Another may experience repeated reclaim pressure and high latency even when its memory-use percentage alone appears unremarkable.

**Utilization says how much memory is charged. Pressure helps explain whether the workload is suffering because of memory scarcity.**

This is the memory equivalent of our CPU lesson: consumption and waiting are not the same thing.

## 12. OOMKilled, SIGKILL, and application heap failures

Our incident reports `OOMKilled`.

What exactly does that mean?

We need to distinguish several different termination mechanisms.

### V8 heap exhaustion

Node.js can encounter a fatal error when V8 cannot satisfy managed-heap allocation requirements within the applicable runtime constraints.

This can produce diagnostic output associated with JavaScript heap exhaustion and result in process termination.

It is a runtime-level failure.

The container may still have memory available under its cgroup budget.

### Cgroup OOM

A memory cgroup reaches a condition where the relevant memory demand cannot be satisfied under its hard restriction and applicable reclaim rules.

The kernel may invoke an OOM decision within that group.

A process is selected for termination according to the relevant policy and kernel behavior.

The host need not be globally out of RAM.

### Global OOM

The host itself may experience memory exhaustion severe enough for the kernel to invoke global OOM handling.

That is a different resource boundary from a container-specific hard limit.

### Kubernetes eviction

Kubernetes may evict a Pod because a node is experiencing resource pressure.

This is not automatically the same event as a container-specific cgroup OOM kill.

The kubelet's eviction decisions, node conditions, container termination reasons, and kernel evidence help distinguish these cases.

### Exit code 137

A process commonly reports exit code 137 when terminated by signal 9, `SIGKILL`, following the conventional shell encoding of 128 plus the signal number.

But SIGKILL can arise from more than one cause.

A user or supervisor can send it.

A container runtime can use it after a termination grace period expires.

An OOM killer can also use it.

Therefore, exit code 137 alone is not proof of an OOM condition.

An explicit `OOMKilled` termination reason is much stronger evidence, but we still need the relevant memory and workload timeline to understand why it happened.

### Which process gets killed?

A cgroup can contain several processes.

Depending on the configuration and kernel decisions, an OOM event may kill a selected process rather than automatically terminating every task in the group.

The memory controller also supports `memory.oom.group`, which can change how an affected cgroup is treated for group OOM handling.

For ordinary application diagnosis, the important point is that killing a process is a kernel response to an unsatisfied memory condition.

It does not necessarily identify which line of application code caused the excessive demand.

## 13. Why increasing the JavaScript heap limit can make things worse

Return to our engineer's proposed fix.

"The heap is only 94 MiB. Let's increase the heap limit."

But our container has a 512-MiB hard memory budget.

Giving V8 permission to consume more managed-heap memory does not increase that budget.

The process still needs memory for native allocations, buffers, stacks, executable code, and other resident data.

The container still needs memory for relevant file-backed and kernel charges.

Increasing a runtime limit may allow the JavaScript heap to grow further, reducing the space available for everything else.

Sometimes changing the heap limit is appropriate.

For example, a workload may legitimately need a larger managed heap, and its container might have enough total capacity.

But changing the V8 limit without examining process and cgroup memory is not a reliable remedy for a container OOM.

It's possible to move the failure from one boundary to another without improving the application.

The correct question is not "How large can we make the heap?"

It's "What is the actual peak working set, and how should the memory budget be divided among the workload's components?"

## 14. The real cause: too much overlapping work

Now we examine the application's processing workflow.

The service accepts documents concurrently.

For each document, it loads input data, decodes images, builds temporary structures, and writes results.

The document-processing library uses native memory.

The application also retains some input and intermediate buffers while processing is in progress.

One document is manageable.

Four image-heavy documents overlap.

Their peak working sets accumulate.

The JavaScript heap remains relatively stable because the largest temporary allocations occur outside the ordinary managed heap.

The process RSS and cgroup charged memory increase.

Reclaim may initially free some cache pages.

But the active memory demand remains high.

Eventually the hard limit cannot be satisfied.

The kernel kills a process.

This explanation fits the observations without requiring a JavaScript object leak.

### An important distinction

A memory leak is a problem of retained resources or allocations that are no longer needed but remain live or otherwise unreleased.

Memory pressure can arise from completely legitimate allocations that are needed right now.

A high-memory workload isn't automatically buggy.

But the application architecture must account for its resource requirements.

Permitting more concurrent work than the allocated memory can support is an operational correctness problem even if each individual document-processing function behaves as intended.

The container didn't fail because its garbage collector forgot how to collect garbage.

It failed because the system permitted a peak memory demand exceeding its budget.

## 15. Designing a fix that survives production

We now know the likely failure mechanism.

What should we change?

### Bound memory-intensive concurrency

The most immediate structural improvement is to limit how many image-heavy documents can be processed simultaneously within one memory budget.

A worker pool or admission-control mechanism can enforce that limit.

But we shouldn't simply choose the number of logical CPU cores.

Memory-intensive work may require a smaller concurrency level than CPU capacity would otherwise permit.

If each active document has a substantial peak memory footprint, memory can become the binding constraint long before CPU.

Use measured peak demand, baseline consumption, and headroom to choose the limit.

### Reduce unnecessary simultaneous buffers

Inspect the document-processing pipeline.

Does the service retain the original PDF while holding decoded page images, intermediate transformations, and final output all in memory?

Are those buffers necessary at the same time?

Can the application release one stage's data before constructing the next stage?

Can images be processed incrementally?

Sometimes streaming or chunking substantially reduces peak memory.

But not every parser supports true incremental processing, and some formats require random access or large intermediate state.

We should use these techniques where the actual algorithm permits them.

### Separate ordinary and expensive workloads

A two-page text document and a thousand-page image-heavy document are not equivalent resource demands.

We might classify documents by size, page count, image properties, or estimated complexity.

Ordinary documents can use a standard processing pool.

Expensive documents can use a separate pool with lower concurrency and a larger memory budget.

This prevents rare extreme inputs from destabilizing the common workload.

It also makes capacity planning and admission control more predictable.

### Limit input amplification

A compressed input file can expand dramatically when decoded.

A small file size does not necessarily imply a small processing footprint.

For user-controlled uploads, consider explicit limits on decoded image dimensions, page count, processing complexity, decompressed data, and execution resources.

These limits are relevant to reliability and security.

An attacker should not be able to convert a tiny upload into unbounded memory consumption merely because the parser accepts the format.

### Increase the budget when justified

There are situations where the correct answer really is to allocate more memory.

If the workload legitimately needs a larger working set, the current limit may simply be insufficient.

But capacity increases should follow measurement.

A larger limit should accommodate realistic peaks, leave appropriate safety margins, and fit within the node's overall resource plan.

Otherwise, we may simply replace a predictable container-level failure with broader node pressure.

### Verify the fix

After making the change, reproduce representative heavy workloads.

Test several concurrent image-heavy documents.

Observe peak memory charges, process memory, reclaim pressure, event counters, throughput, and latency.

Confirm that the service no longer exceeds its budget under the supported workload.

Also ensure that the fix hasn't merely created an unbounded queue somewhere else.

A service that stops crashing but accumulates jobs forever isn't healthy.

It's just failing more politely.

## 16. A senior engineer's memory investigation

Let's turn the incident into a reusable diagnostic procedure.

An interviewer asks:

"Our Node.js service gets OOM-killed, but heap usage looks normal. What would you investigate?"

A strong answer should unfold in stages.

### First: identify the termination mechanism

Inspect the previous container's termination status and relevant events.

Was the process killed by a cgroup OOM condition?

Was there a V8 fatal heap error?

Did the node experience pressure and evict the Pod?

Was the process sent SIGKILL for another reason?

The first job is establishing what actually happened.

### Second: identify the enforcement boundary

What memory limit applies?

Which cgroup contains the relevant processes?

Are there ancestor restrictions?

Does the workload have access to swap?

What does the orchestration platform report?

Without identifying the boundary, memory numbers are easy to misinterpret.

### Third: compare the different accounting layers

Inspect runtime memory metrics.

Then inspect process RSS and relevant mapping statistics.

Then examine cgroup usage, peak usage, and category breakdowns.

Do not add overlapping values.

Ask which category is growing and which metrics describe it.

### Fourth: inspect pressure and event history

Examine `memory.events`, pressure metrics, and any retained time-series data.

Did the workload experience reclaim-related stalls?

Was usage repeatedly approaching the hard limit?

Were there OOM events or OOM kills?

Did the memory increase occur gradually or as a brief spike?

### Fifth: reconstruct the workload

Was a large document uploaded?

Did several jobs overlap?

Did the application decode images, allocate Buffers, create temporary files, or invoke native libraries?

Was a new deployment configured with greater concurrency?

Did the input format expand dramatically during processing?

Resource metrics without workload context are incomplete.

### Sixth: choose a discriminating experiment

If you suspect concurrent native allocations, reproduce with one heavy document, then two, then more, within a safe isolated environment.

Measure peak charged memory and runtime memory categories.

If memory demand grows with active document count, that supports the concurrency hypothesis.

If memory keeps growing after work completes and resources should have been released, investigate retention, allocator behavior, and possible leaks.

If reclaim pressure dominates despite modest anonymous memory, examine file-cache and storage behavior.

The best experiment is the one that most clearly distinguishes competing explanations.

### Seventh: verify the remediation

Don't stop at seeing fewer crashes.

Verify that the new design has sufficient memory headroom, acceptable tail latency, predictable throughput, and bounded backlog growth.

A successful fix addresses the underlying resource contract.

Not merely the most visible symptom.

---

# The Oral Examination

Answer aloud before reading the solutions. Treat each question as a miniature production investigation.

**Question 1 — The tiny heap**

A Node.js service reports `heapUsed` of 90 MiB, process RSS of 380 MiB, and cgroup usage near 500 MiB. Its container limit is 512 MiB. Explain why the figures are compatible.

**Question 2 — The misleading sum**

An engineer adds `heapUsed`, `external`, `arrayBuffers`, RSS, and cgroup memory usage together. What's wrong with that calculation?

**Question 3 — The full cache**

A Linux host reports substantial RAM consumed by filesystem cache. Does this automatically indicate memory pressure? What determines whether cache reclaim will be inexpensive?

**Question 4 — The slow but living service**

A container's memory-pressure metrics rise and `memory.events` reports increasing `high` events, but no OOM kill occurs. Explain the likely mechanism.

**Question 5 — The hard limit**

A container has a 512-MiB memory limit. The host has eight gigabytes available. The container encounters an OOM kill. How can that happen?

**Question 6 — The exit code**

A process terminates with exit code 137. Why isn't that sufficient to diagnose a memory problem?

**Question 7 — Swap as a rescue plan**

Would enabling more swap necessarily make a memory-constrained service faster and more reliable? Explain the trade-offs.

**Question 8 — The four-document failure**

One PDF processes successfully. Four concurrent image-heavy PDFs cause OOM termination. The JavaScript heap remains stable. What would you measure, and how would you redesign the workload?

**Question 9 — The incomplete dashboard**

Memory usage is sampled once per minute. The container dies during a five-second allocation spike. Why might the dashboard fail to reveal the peak, and which other evidence would you seek?

---

# Solutions and Discussion

## Solution 1 — Three accounting layers

The V8 heap is only one portion of process memory. RSS includes resident pages from native allocations, buffers, stacks, executable mappings, and other categories.

Cgroup accounting can also include relevant file cache, kernel memory, and additional processes or resources.

The measurements have different scopes, so the figures are compatible without any one of them being incorrect.

## Solution 2 — Overlapping categories

ArrayBuffer-related memory is included in Node.js external-memory accounting.

Resident heap and native pages already contribute to RSS where resident.

Some resident and kernel-managed pages also contribute to cgroup charges.

Adding the metrics double-counts memory. They must be interpreted according to their accounting boundaries.

## Solution 3 — Cache isn't automatically wasted memory

Linux intentionally uses available RAM to cache useful file data.

Clean eligible file-backed pages may often be reclaimed without writing them back.

Dirty pages may require writeback. Tmpfs, shared-memory pages, and frequently reused pages may have different costs.

Pressure depends on active demand, reclaimability, and resulting stalls—not simply on the percentage of RAM containing cached data.

## Solution 4 — Pressure without termination

The group may exceed its `memory.high` threshold, causing tasks to experience reclaim and throttling behavior.

This can increase latency even without reaching an unsatisfied hard-limit allocation.

`memory.high` and `memory.max` have different semantics.

A rise in pressure does not automatically imply an OOM kill.

## Solution 5 — The cgroup is the boundary

The container has its own enforced memory budget.

When charged usage reaches the relevant hard restriction and applicable reclaim cannot satisfy the demand, a cgroup OOM condition can occur.

The host's available memory does not override that allocation policy.

## Solution 6 — SIGKILL has multiple causes

Exit code 137 commonly indicates termination by signal 9.

The signal may come from an OOM killer, a supervisor, a container runtime after a grace period, or another permitted sender.

Inspect termination reasons and supporting kernel or orchestration evidence before concluding that memory exhaustion caused the kill.

## Solution 7 — Swap trades physical memory pressure for other costs

Swap may free RAM by moving eligible inactive pages elsewhere.

That can help certain workloads.

But repeatedly accessing swapped-out pages can create severe latency and thrashing.

Container swap controls and deployment configuration also matter.

More swap isn't automatically the right remedy for an oversized active working set.

## Solution 8 — Peak concurrent demand

Measure runtime memory, process RSS, cgroup charged memory, relevant `memory.stat` categories, and peak usage under controlled concurrency.

Investigate native buffers and decoded image memory.

Then bound concurrent heavy operations, reduce unnecessary intermediate retention, separate expensive workload classes, and allocate a larger budget if legitimate demand requires it.

Verify the outcome under representative heavy inputs.

## Solution 9 — Sampling can miss the decisive moment

A short memory spike may occur and trigger termination entirely between dashboard samples.

The last recorded value can therefore be far below the actual peak.

Seek higher-resolution telemetry, `memory.peak` where available, memory-event counters, pressure history, kernel evidence, and the previous container's termination status.

Also reproduce the allocation pattern under controlled conditions.

---

# The Mental Model Worth Keeping

When diagnosing memory behavior, always ask:

**What memory is being used?** Distinguish managed heap, process-resident pages, file-backed cache, native allocations, and kernel charges.

**Who accounts for it?** Distinguish runtime metrics, process memory statistics, and cgroup accounting.

**Can it be reclaimed?** Understand whether pages can be discarded, written back, swapped, or must remain resident for the active workload.

**Which limit applies?** Identify the effective cgroup and host constraints.

**What happens under pressure?** Distinguish normal usage, reclaim stalls, throttling, allocation failure, and OOM termination.

The durable principle is:

**Memory exhaustion is not one number becoming too large. It is demand that cannot be satisfied within a particular resource boundary under the applicable memory-management rules.**

# Next Lecture — System Calls, File Descriptors, and Asynchronous I/O

We now understand how the operating system manages execution and physical memory.

But modern servers spend much of their lives waiting for something else.

A network packet arrives. A file becomes readable. A socket can accept more data. A disk operation completes.

How can one Node.js thread coordinate thousands of network connections without creating one JavaScript thread for every connection?

Why does reading a file asynchronously sometimes involve a worker thread, while network I/O can use readiness notifications?

And why can a single synchronous filesystem operation freeze an otherwise healthy event-driven server?

In CS320-L05, we'll investigate the interface between application runtimes and the kernel: system calls, file descriptors, blocking and nonblocking operations, readiness, completion, and the machinery beneath asynchronous I/O.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Lab — Investigating Memory Without Crashing Your Machine

These experiments are intended for a disposable local Linux environment or Docker container.

The goal is to observe memory behavior, not deliberately exhaust the host's RAM. Avoid performing destructive memory-pressure experiments on production systems.

## Lab A — Observe Node.js memory categories

Create `memory-observe.js`:

```javascript
const MiB = 1024 * 1024;

function report(label) {
  const m = process.memoryUsage();

  console.log(label, {
    heapUsedMiB: +(m.heapUsed / MiB).toFixed(1),
    heapTotalMiB: +(m.heapTotal / MiB).toFixed(1),
    externalMiB: +(m.external / MiB).toFixed(1),
    arrayBuffersMiB: +(m.arrayBuffers / MiB).toFixed(1),
    rssMiB: +(m.rss / MiB).toFixed(1),
  });
}

report("before");

const buffers = [];

for (let i = 0; i < 8; i++) {
  buffers.push(Buffer.alloc(4 * MiB, 1));
}

report("after 32 MiB of Buffer allocations");

console.log("Retained buffers:", buffers.length);
```

Run it using Node.js.

Observe which metrics increase.

The expected pattern is that Buffer-related memory contributes to external and ArrayBuffer accounting without requiring an equivalent increase in ordinary V8 `heapUsed`.

The exact measurements vary with runtime version and allocator behavior.

**Question:** Why would adding `arrayBuffers` to `external` overstate memory consumption?

## Lab B — Read cgroup memory controls

On a Linux system using cgroup v2:

```bash
cat /proc/self/cgroup
cat /sys/fs/cgroup/memory.current
cat /sys/fs/cgroup/memory.max
cat /sys/fs/cgroup/memory.high
cat /sys/fs/cgroup/memory.events
```

Depending on the environment, the displayed cgroup filesystem may belong to a container namespace or a broader group.

Some controls may be unavailable or disabled.

Interpret each value according to its documented semantics.

**Question:** Why can `memory.current` remain substantially greater than one application's `heapUsed`?

## Lab C — Inspect cgroup memory categories

Where available:

```bash
cat /sys/fs/cgroup/memory.stat
```

Look for fields including:

```text
anon
file
kernel
pagetables
sock
file_dirty
file_writeback
```

These fields do not all represent mutually exclusive categories.

Compare their meaning with the definitions in the Linux kernel documentation.

**Question:** Why might a document-processing service have substantial file-related charges even if its JavaScript objects are being collected normally?

## Lab D — Observe memory allocation safely inside Docker

This example uses a 256-MiB container limit and allocates a bounded 48-MiB Buffer. It is intended to remain comfortably below the limit under ordinary Node.js runtime conditions, although the exact runtime footprint depends on the environment.

```bash
docker run --rm --memory=256m node:22-alpine node -e '
const fs = require("node:fs");
const MiB = 1024 * 1024;

function show(label) {
  const m = process.memoryUsage();
  console.log(label, {
    heapUsed: Math.round(m.heapUsed / MiB),
    external: Math.round(m.external / MiB),
    rss: Math.round(m.rss / MiB)
  });

  for (const name of [
    "memory.current",
    "memory.max",
    "memory.peak"
  ]) {
    const path = "/sys/fs/cgroup/" + name;
    if (fs.existsSync(path)) {
      console.log(name, fs.readFileSync(path, "utf8").trim());
    }
  }
}

show("before");

const data = Buffer.alloc(48 * MiB, 1);

show("after");

console.log("Buffer retained:", data.length);
'
```

The `memory.peak` file may not be available on every kernel.

Compare the runtime's memory metrics with the relevant cgroup usage.

Do not expect the differences to equal exactly 48 MiB because process initialization, page residency, allocators, and other accounting behavior contribute to the measurements.

## Lab E — Inspect memory pressure

On a supporting Linux host:

```bash
cat /proc/pressure/memory
```

For cgroup-level information, where available:

```bash
cat /sys/fs/cgroup/memory.pressure
```

Look at the `some` and `full` fields.

Their moving averages describe resource-stall time, not memory-utilization percentages.

A low pressure value alongside substantial memory usage may be perfectly normal.

**Question:** Why can a system show high memory usage without experiencing significant pressure?

## Lab F — Inspect process RSS and PSS

Choose a process you control.

```bash
PID=$$

grep -E 'VmSize|VmRSS|VmHWM|RssAnon|RssFile|RssShmem|VmSwap' \
  /proc/"$PID"/status
```

Where supported:

```bash
cat /proc/"$PID"/smaps_rollup
```

Identify RSS and PSS.

Explain why summing RSS values from several processes can overcount shared resident pages.

Then explain why a cgroup's memory usage isn't necessarily equal to that sum.

## Lab G — Follow the evidence of a Kubernetes memory failure

In a development Kubernetes cluster, inspect the workload and previous termination information using the appropriate namespace and Pod name.

```bash
kubectl describe pod <pod-name> -n <namespace>

kubectl logs <pod-name> -n <namespace> \
  --previous --container <container-name>
```

Inspect the reported termination reason, exit code, and container resource configuration.

If an OOM kill is reported, identify what additional metrics would be needed to determine whether the underlying issue was a leak, temporary peak, excessive concurrency, or insufficient legitimate capacity.

Do not treat the termination reason as a complete root-cause explanation.

## Lab H — The incident-room exercise

Consider this hypothetical evidence:

```text
Container memory limit: 512 MiB

Before heavy uploads:
  V8 heapUsed:         78 MiB
  Process RSS:        195 MiB
  Cgroup current:     238 MiB

During concurrent processing:
  V8 heapUsed:         94 MiB
  Process RSS:        425 MiB
  Cgroup current:     505 MiB

Observed:
  Four image-heavy documents processing
  memory.events max increasing
  memory.events oom_kill increased
  Previous termination: OOMKilled
  Host has several GiB available
```

Write a short investigation report that answers:

1. What is known for certain?
2. Which conclusions are strongly supported but still require additional evidence?
3. What are the most plausible sources of the memory not explained by V8 `heapUsed`?
4. Which workload change would you test first?
5. How would you verify that the remediation addresses peak memory demand rather than merely hiding the problem?

A successful answer should distinguish observations, hypotheses, discriminating tests, and permanent remediation.

---

# Further Reading

Primary technical references:

1. Linux Kernel Documentation — Control Group v2  
   https://docs.kernel.org/admin-guide/cgroup-v2.html

2. Linux Kernel Documentation — Memory Management Concepts  
   https://docs.kernel.org/admin-guide/mm/concepts.html

3. Linux Kernel Documentation — Pressure Stall Information  
   https://docs.kernel.org/accounting/psi.html

4. Node.js Documentation — `process.memoryUsage()`  
   https://nodejs.org/api/process.html#processmemoryusage

5. Kubernetes Documentation — Resource Management for Pods and Containers  
   https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/

6. Linux Manual Pages — Process Memory Status  
   https://man7.org/linux/man-pages/man5/proc_pid_status.5.html

Related programme chapters:

- CS220-L04 — References, Garbage Collection, and Memory Leaks
- CS320-L03 — Virtual Memory, Pages, and Address Translation
- CS320-L05 — System Calls, File Descriptors, and Asynchronous I/O
- SE450-L04 — Scheduling, Resources, and Autoscaling

---

## Dense Cheatsheet — Interview Glance Card

```text
CS320-L04 — MEMORY PRESSURE, CGROUPS, AND OOM

CORE IDEA
  Runtime heap != process RSS != cgroup charged memory
  Physical memory demand must fit the effective resource budget
  High usage != automatically pressure
  Pressure != automatically OOM
  OOM != automatically application memory leak

RUNTIME METRICS (NODE.JS)
  heapUsed      V8 managed-heap usage
  heapTotal     V8 heap allocation
  external      relevant V8-associated C++/external memory
  arrayBuffers  Buffer / ArrayBuffer-related memory
  rss           process-wide resident memory
  arrayBuffers is included in external
  Runtime fields overlap with process RSS
  Native allocations may be outside ordinary V8 heap
  Worker-thread fields can have different reporting scopes

PROCESS MEMORY
  Virtual size  mapped virtual address-space extent
  RSS           resident pages mapped into process
  PSS           proportional resident-page accounting
  Shared pages can be counted in several process RSS figures
  Process RSS != complete cgroup charge

CGROUP ACCOUNTING
  Includes relevant anonymous, file-backed, and kernel charges
  Hierarchical: ancestor constraints may also apply
  Memory ownership/charges do not equal arbitrary RSS sums

PAGE CACHE
  File data cached in RAM for faster reuse
  Clean eligible page: may be discarded/retrieved later
  Dirty page: may require writeback
  Reclaimable != free to reclaim without performance cost
  tmpfs/shmem not equivalent to ordinary clean disk cache
  memory.stat file includes more than simple disk-file cache

MEMORY PRESSURE
  Demand approaches available / permitted backing
  Reclaim tries to free usable pages
  Background reclaim and direct reclaim both matter
  Reclaim can stall application allocations
  Repeated eviction + refault = thrashing
  Working set = pages actively required over relevant interval
  Legitimate peak demand can exceed budget without a leak

SWAP
  Preserves eligible anonymous contents outside ordinary RAM
  May free RAM for other work
  Repeated swap-in/out can destroy latency
  memory.swap.current / memory.swap.max govern swap accounting
  Availability/configuration vary by environment

CGROUP V2 FILES
  memory.current   current charged memory
  memory.peak      recorded peak where supported
  memory.max       hard memory boundary
  memory.high      reclaim/throttling threshold, not OOM by itself
  memory.low       best-effort reclaim protection
  memory.min       stronger reclaim protection
  memory.stat      category and activity breakdown
  memory.events    hierarchical event counters
  memory.events.local   local-only events
  memory.pressure  group memory-stall statistics

MEMORY EVENTS
  high      threshold exceeded, reclaim/throttle
  max       attempted pressure against hard boundary
  oom       relevant OOM condition/allocation failure risk
  oom_kill  processes in group killed by OOM killer
  max != guaranteed kill
  oom != identical to oom_kill
  Compare deltas and relevant timeline

MEMORY.STAT HINTS
  anon         anonymous-memory charges
  file         file cache, tmpfs and related categories
  kernel       relevant kernel memory
  pagetables   page-table memory
  sock         socket-buffer memory
  file_dirty   modified cached file data
  file_writeback  data undergoing writeback
  Fields may overlap or be subcategories: do NOT sum all

PSI
  some = at least some tasks stalled on memory resource
  full = all non-idle tasks in observed scope stalled
  Pressure is about stalled progress, not simply bytes used

TERMINATION MODES
  V8 heap OOM    runtime-level allocation failure
  Cgroup OOM     effective cgroup hard boundary unsatisfied
  Global OOM     host-level memory exhaustion
  Pod eviction   kubelet action under node resource pressure
  Exit 137       usually SIGKILL, NOT proof of OOM
  OOMKilled      stronger termination evidence, not full root cause
  memory.oom.group can influence group-kill behavior

DOCUMENT PROCESSOR FAILURE
  Small JS heap + large native buffers + overlapping jobs
  => process/cgroup memory rises
  => reclaim and possible stalls
  => hard boundary unsatisfied
  => OOM kill possible
  No leak required

REMEDIATION
  Measure actual peak, not only steady state
  Bound memory-intensive concurrency
  Reduce unnecessary simultaneous buffers
  Stream/chunk where algorithm supports it
  Separate heavy from ordinary workload classes
  Limit decoded input amplification
  Increase resource budget only with evidence + headroom
  Verify performance AND stability after change

INVESTIGATION
  1. Verify termination reason
  2. Identify cgroup and effective limits
  3. Compare runtime, RSS/PSS, and cgroup metrics
  4. Inspect memory.stat and event deltas
  5. Look for PSI/reclaim stalls before termination
  6. Correlate peak memory with exact workload
  7. Run controlled discriminating experiment
  8. Remediate and validate worst-case concurrency

SENIOR INTERVIEW ANSWER
  "I wouldn't equate a small JavaScript heap with a small
   container footprint. I'd first verify the OOM mechanism,
   identify the effective cgroup limit, compare runtime,
   process and cgroup memory accounting, then correlate
   peaks and pressure with workload concurrency before
   changing the memory allocation or application design."

DURABLE MENTAL MODEL
  What uses the memory?
  Who accounts for it?
  Can it be reclaimed?
  What boundary limits it?
  What does the workload do when pressure increases?
```
