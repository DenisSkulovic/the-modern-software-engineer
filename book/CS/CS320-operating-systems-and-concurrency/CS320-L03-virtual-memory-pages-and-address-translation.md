---
id: CS320-L03
course: CS320
title: "Virtual Memory, Pages, and Address Translation"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: []
prev: CS320-L02
next: CS320-L04
---


# CS320 — Operating Systems and Concurrency

## Lecture 03: Virtual Memory, Pages, and Address Translation

*Two processes can use exactly the same memory address without accessing the same physical memory. A process can reserve several gigabytes without possessing several gigabytes of RAM. And copying a process doesn't necessarily copy its memory. How can all three statements be true?*

# Part I — Intuition

## The picture to carry in your head

Imagine an enormous hotel.

Every guest receives a room directory. The directory contains room numbers, descriptions, and access permissions.

But here's the strange part: the room numbers are not the building's actual physical room numbers.

Guest A might receive a directory listing room 1204 as a private office.

Guest B might also have a room 1204, but its directory points somewhere completely different.

Meanwhile, two guests may have different room numbers that lead to the same shared library.

The hotel management maintains the mapping between the room numbers guests use and the physical rooms that actually exist.

This arrangement sounds unnecessarily complicated—until you realize what it achieves.

Guests can navigate familiar addresses without knowing the building's physical layout. They cannot automatically enter each other's private rooms. Shared facilities can be exposed deliberately. The hotel can rearrange physical assignments without requiring everyone to rewrite their directories.

This is the essential idea behind **virtual memory**.

A running process uses virtual addresses. Those addresses are interpreted through mappings established by the operating system and enforced by the processor's memory-management hardware.

The application does not normally know which physical RAM locations contain its data.

And that's a very good thing.

## 1. The memory address isn't the physical location

Let's return to our document-processing service.

The application receives PDFs, extracts information, and compares the results against a large reference dataset.

To accelerate processing, the service loads the reference dataset into memory.

It then launches several worker processes.

Each worker performs the same analysis on different documents.

Now imagine that two workers both reference a memory address with the same numerical value.

Does that mean they access the same data?

Not necessarily.

Each process ordinarily has its own virtual address space.

The same numerical virtual address can map to different physical memory in different processes.

The address identifies a location within the process's memory environment, not a universal location in the machine.

This is one reason separate processes can safely execute the same program simultaneously.

They don't need to negotiate a unique global address for every variable or object.

The operating system and hardware handle the translation.

## 2. Pages: the hotel manages rooms in blocks

Our imaginary hotel could maintain a separate mapping for every square centimeter of every room.

That would be absurdly complicated.

Instead, it manages whole rooms.

Virtual memory uses a similar strategy.

Memory is divided into fixed-size units called **pages**.

A common base page size on many Linux systems is four kibibytes, or 4,096 bytes, although actual page sizes depend on the architecture and configuration.

Rather than independently mapping every byte, the system maps virtual pages to physical page frames or other backing arrangements.

An address therefore has two conceptual parts.

One part identifies the virtual page.

The other identifies the position, or offset, within that page.

The operating system maintains the mapping between virtual pages and their underlying physical frames.

The processor uses this information to access the correct data.

That mapping information is organized in **page tables**.

But here's the critical distinction: page tables do not have to contain a present physical frame for every address a process might legitimately use.

Some pages may be reserved or mapped without yet having resident physical memory.

## 3. Reserving space isn't the same as occupying it

Suppose our document processor requests a virtual region large enough to address four gigabytes.

Does the machine immediately need four gigabytes of physical RAM?

Not necessarily.

The operating system can establish an address range without immediately backing every page with a separate physical frame.

The application might touch only a small fraction of that region.

Physical backing may be established as pages are accessed, according to the mapping and allocation policies.

It's like reserving room numbers in the hotel's directory without furnishing every room immediately.

This is called **demand paging** when the system establishes or retrieves needed pages in response to accesses.

It explains why a process can have a very large virtual memory size while its actual resident memory remains much smaller.

Virtual address space and physical RAM consumption are different things.

## 4. A page fault isn't necessarily a disaster

Now imagine a guest visiting a room for the first time.

The directory says the room belongs to the guest, but it hasn't yet been prepared.

Management receives a notification, arranges the room, updates the directory, and allows the guest to continue.

A page fault can work similarly.

When the processor encounters a memory access that cannot currently be completed through the established translation and protection state, it raises a page-fault exception.

The kernel examines the situation.

Perhaps the address is valid but needs a fresh physical page.

Perhaps a file-backed page must be brought into memory.

Perhaps the process is writing to a page that is currently shared using copy-on-write.

Or perhaps the access really is invalid.

The first three situations may be handled successfully, after which the faulting instruction can be retried.

The last may result in an error signal and process termination.

This is why **page fault does not automatically mean segmentation fault**.

Many page faults are normal mechanisms through which the operating system makes memory available.

## 5. The TLB: a shortcut for the address book

There's an obvious concern.

If every memory access needs an address translation, won't all those lookups make execution terribly slow?

They would be expensive if the processor had to repeatedly walk several levels of page tables for every access.

Modern processors therefore maintain caches of recently used translations, called **translation lookaside buffers**, or TLBs.

A TLB entry allows the processor to reuse an appropriate translation without performing the full page-table walk again.

This is a hardware-level optimization.

A TLB miss doesn't necessarily mean a page fault.

It may simply mean the processor must consult the page tables to obtain a translation that is already valid and present.

We'll examine the distinction in the Deep Dive.

## 6. The copy that hasn't happened yet

Now return to our document-processing service.

It has loaded a large reference dataset.

The application creates several child processes using a fork-like mechanism.

At first glance, each child seems to inherit the parent's memory contents.

Does that mean creating four children immediately produces four additional physical copies of every page?

Usually not.

Linux commonly uses **copy-on-write**.

The parent and child can initially share suitable physical pages, with the necessary protections in place.

If one process later attempts to modify a shared copy-on-write page, the kernel can allocate a separate physical page and preserve the original contents for the other process.

The copy occurs when required by a write, rather than eagerly copying everything during process creation.

This can make process creation substantially cheaper.

It also means memory usage can rise unexpectedly when child processes begin modifying previously shared pages.

The same mechanism explains both efficient sharing and surprising memory growth.

## Three questions before the Deep Dive

1. If two processes both access virtual address `0x1000`, must they be accessing the same physical memory?
2. Why can a process reserve a large virtual address range without immediately consuming an equivalent amount of RAM?
3. Why might writing to a previously shared page increase physical memory consumption even though the application hasn't explicitly created a new object?

The picture to retain is this: every process has its own address directory. The processor translates addresses using mappings maintained by the kernel. Physical pages can be supplied lazily, shared deliberately, and copied when necessary.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The four-worker memory mystery

Our document-processing service has evolved.

The application now loads a large read-mostly reference dataset and creates four worker processes to analyze incoming documents.

Each worker needs access to the same reference information.

The dataset occupies approximately six hundred mebibytes once populated in memory.

The parent loads it before creating the children.

After the workers start, an engineer examines process memory statistics and notices something alarming.

The parent appears to have hundreds of mebibytes of resident memory.

Each child also appears to have hundreds of mebibytes.

Adding the reported resident sets produces a number far larger than the original dataset.

Someone declares that process creation has quadrupled memory consumption.

Yet the machine's actual physical memory use hasn't risen by anything close to that amount.

Later, the workers begin making small modifications to their inherited data structures.

Now physical memory consumption grows more substantially.

And certain first accesses are noticeably slower than repeated accesses.

Three observations need explanation:

**First**, why do several processes appear to contain the same large dataset without requiring separate physical copies of it?

**Second**, why do writes make memory consumption increase?

**Third**, why can the first access to a valid memory address be slower than later accesses?

All three become understandable once we examine the separation between virtual addresses and physical memory.

## 2. What virtual memory actually solves

Imagine a computer without virtual memory.

Every application refers directly to physical RAM addresses.

Program A expects its data to occupy one particular location. Program B expects to use overlapping addresses.

Now we need to coordinate memory placement manually.

Relocating applications becomes awkward. Isolating memory becomes difficult. Sharing selected regions while protecting everything else requires additional machinery.

A bug in one application could potentially overwrite another application's data.

Virtual memory changes the contract.

A process works with virtual addresses. The operating system establishes mappings between those addresses and physical memory.

This provides three important capabilities.

### Isolation

Each process can have a private address space.

Two processes using the same numerical virtual address may refer to entirely different physical pages.

One process ordinarily cannot read another's private memory merely by guessing an address.

### Flexible placement

A program doesn't generally need to know the precise physical location of its data.

The kernel can establish appropriate physical mappings while the application continues operating with virtual addresses.

### Controlled sharing

Different processes can deliberately map the same underlying physical memory where appropriate.

This permits shared libraries, shared-memory communication, and efficient copy-on-write arrangements.

Virtual memory therefore isn't merely a way to pretend that more RAM exists.

It is a fundamental mechanism for isolation, flexible allocation, and sharing.

## 3. A virtual address, dissected

Let's make the mechanism concrete.

Assume a system using 4,096-byte pages.

That page size equals two to the twelfth power.

Consequently, the lowest twelve bits of a virtual address describe the byte offset within a page.

The remaining higher bits identify the virtual page.

Consider the virtual address `0x12345`.

In this simplified example, the virtual page number is `0x12`, and the offset within that page is `0x345`.

The processor must determine which physical frame corresponds to virtual page `0x12`.

Suppose the mapping identifies physical frame `0xABC`.

The physical address is formed using that frame and the original offset.

The important point is that the offset stays the same.

The page mapping changes which physical frame contains the data, not the byte's relative position within the page.

```text
VIRTUAL ADDRESS
+-------------------+--------------+
| Virtual page 0x12 | Offset 0x345 |
+-------------------+--------------+
          |
          | Page-table translation
          v
+-------------------+--------------+
| Physical frame ABC| Offset 0x345 |
+-------------------+--------------+
```

This is a conceptual address translation, not a claim about an actual machine's physical addresses.

The mechanism generalizes to different page sizes and architectures.

A four-kibibyte page gives twelve offset bits. A larger page uses more offset bits.

The division between page number and offset is what makes page-granular mapping possible.

### Why page size matters

Smaller pages provide relatively fine-grained memory management.

A process can establish mappings, permissions, and physical backing in smaller units.

But a large memory region may require many individual page translations.

Larger pages can reduce translation overhead and page-table complexity for suitable workloads.

They can also introduce greater granularity costs.

We'll return to that trade-off when discussing huge pages.

## 4. Page tables and the memory-management unit

Where are virtual-to-physical mappings stored?

The operating system maintains data structures commonly called **page tables**.

Modern page tables are generally hierarchical.

Instead of maintaining one enormous flat mapping array covering every theoretically possible virtual address, the system uses multiple levels of tables.

Large unused areas can remain unpopulated.

This is especially important for large virtual address spaces, most of which may not correspond to actively used memory.

### The hardware side

The processor contains memory-management hardware commonly called the **MMU**, or Memory Management Unit.

When an instruction accesses memory, the MMU handles the relevant address translation.

It may find a usable translation in a TLB.

If not, it may perform a page-table walk to retrieve the mapping and associated permissions.

The kernel configures and maintains the page tables, but ordinary successful address translation is handled in hardware.

That's crucial.

Imagine invoking a kernel system call for every variable read or write.

Application performance would be disastrous.

Instead, the common path is designed to be efficient.

The kernel becomes involved when mappings must be established or changed, or when an access triggers an exception requiring operating-system handling.

### What a page-table entry describes

Conceptually, a page-table entry can describe more than a physical frame.

It also participates in the access-control and mapping state.

For example, it may indicate whether an appropriate translation is present, whether a mapping is writable, and whether execution is permitted.

Real architectures contain additional flags and implementation details.

The important lesson is that translation and protection are closely related.

The MMU doesn't merely answer, "Where is this address?"

It also helps enforce, "Is this kind of access permitted?"

## 5. Mapped addresses versus populated pages

We need to distinguish two levels of memory state.

At one level, the operating system maintains the process's virtual memory regions.

A region may describe an address range associated with anonymous memory, a file mapping, or another supported backing arrangement.

It also carries relevant permissions and mapping properties.

On Linux, such regions are represented through virtual-memory-area structures, commonly called VMAs.

At another level, page tables describe the translations needed for individual pages or larger mapped blocks.

These layers are related but not identical.

### The reservation that doesn't occupy RAM

Suppose our process establishes an anonymous mapping covering one gigabyte.

The kernel may record that this range is valid and eligible for particular accesses.

But physical pages need not all be allocated immediately.

As the application touches the region, the kernel can establish backing where necessary.

A large virtual region is therefore not synonymous with a fully resident physical allocation.

However, don't interpret this as a guarantee that every large reservation is free or safe.

Address-space limits, allocation policies, overcommit behavior, and resource-accounting rules can affect whether mappings succeed and what happens when they are used.

The distinction remains: creating a mapping and populating its physical backing are separate events.

## 6. The TLB: why translation is usually fast

Let's return to the MMU.

It must translate virtual addresses frequently.

Reading an array, following a pointer, executing an instruction, and accessing stack memory all involve address translation.

If each access required several additional memory accesses just to walk page tables, translation overhead would be substantial.

The TLB provides a shortcut.

It caches recently used translations, allowing the processor to avoid repeating the full page-table walk when a suitable entry is available.

### TLB hit

The processor finds a usable cached translation.

It can proceed without performing the full page-table walk.

### TLB miss

The required translation isn't available in the relevant translation cache.

The processor must obtain the mapping through the appropriate translation mechanism, commonly a hardware page-table walk on modern server CPUs.

If the mapping is valid and present, the operation can proceed.

No page-fault exception is necessarily required.

### Page fault

The processor cannot complete the access using the current mapping and protection state.

It raises a page-fault exception for the operating system to handle.

That might be because a needed page isn't currently present, because a copy-on-write operation must be resolved, or because the access violates a protection rule.

**TLB miss and page fault are not synonyms.**

A TLB miss may be an ordinary hardware cache miss with no kernel exception.

A page fault requires operating-system handling of a memory-access condition.

### Translation caches must stay coherent with mappings

Suppose the kernel changes a page's mapping or permissions.

A processor may still possess an older translation in its TLB.

The kernel must use the architecture's appropriate invalidation and synchronization mechanisms so that stale translations don't remain usable incorrectly.

This is one reason memory-management operations can have costs beyond simply modifying an entry in RAM.

The processor's cached understanding of the address space must remain consistent with the kernel's intended protections.

## 7. Page faults: the normal, the expensive, and the fatal

Let's follow an actual memory access that triggers a page fault.

The processor attempts to access a virtual address.

The current translation state cannot satisfy that access.

The processor raises a fault.

The kernel identifies the relevant address-space region and examines the mapping, permissions, and fault conditions.

Several outcomes are possible.

### Case A: first access to anonymous memory

Our process has established a valid anonymous memory region.

It accesses a page for the first time.

The kernel may need to provide suitable backing and establish a page-table translation.

For example, it may arrange a zero-filled physical page when a writable private page is needed.

For certain read accesses, implementations can use shared zero-page mappings instead of immediately allocating a separate private page.

After resolving the fault, execution continues.

This is normal demand-paging behavior.

The application may never notice except through timing or page-fault statistics.

### Case B: a file-backed page already in memory

Our process maps part of a file.

The necessary physical page is already in the operating system's page cache.

The kernel may establish the process's mapping to that cached page without needing to read the data from storage again.

The page fault is resolved, but no physical disk read is required for that data.

### Case C: a file-backed page must be retrieved

Now imagine the data is not resident and requires storage I/O.

The kernel must obtain the relevant contents before the access can complete.

This can be significantly more expensive than establishing a mapping to an already resident page.

Linux distinguishes **minor** and **major** page faults.

Broadly, a minor fault is resolved without requiring disk I/O to bring in the needed page.

A major fault requires such I/O.

But a minor fault is not necessarily free, and a major-fault count is not a universal measure of all memory-related delays.

### Case D: the address or access is invalid

Suppose the process accesses an unmapped address or performs an operation forbidden by the mapping's permissions.

If the kernel cannot legitimately resolve the fault, it can deliver an appropriate signal to the process.

On Linux, invalid memory accesses commonly lead to `SIGSEGV`. Certain failures involving mapped objects may produce `SIGBUS`.

This is the scenario people often associate with the phrase "segmentation fault."

But now we can see why treating every page fault as a crash is incorrect.

A page fault is an exception requiring a decision.

The kernel may resolve it successfully.

## 8. Memory protection: why another process's memory is not yours

Virtual memory is also a security and correctness boundary.

Each process ordinarily possesses its own address-space mappings.

A process cannot simply use a numerical address from another process and expect the same physical memory to appear.

The address must be meaningful in its own address space.

Page mappings also carry access permissions.

A region might be readable but not writable.

Another might be readable and executable.

Some regions may be deliberately inaccessible.

### Why code pages are often not writable

An executable program contains machine instructions.

In ordinary execution, those instructions should generally not be modified by arbitrary application writes.

Operating systems and runtime loaders can establish appropriate permissions to separate writable data from executable code.

The security principle commonly called write-xor-execute, or W^X, aims to avoid unnecessarily allowing memory regions to be writable and executable simultaneously.

There are legitimate exceptions and transitions, such as those involved in JIT compilation.

But those require deliberate memory-permission management.

The important distinction is that memory protection is enforced at a lower level than JavaScript or TypeScript's type checking.

TypeScript might prevent an invalid operation during static analysis.

The MMU helps prevent unauthorized memory accesses during machine-code execution.

They are different kinds of protection.

### Guard pages

An operating system or runtime can place inaccessible pages near certain memory regions.

If execution crosses an intended boundary, an access can fault instead of silently corrupting neighboring data.

Guard pages are particularly useful for detecting some forms of stack overflow or invalid memory access.

They don't prevent every memory-safety problem, but they illustrate how virtual-memory permissions support runtime safety.

## 9. File mappings: accessing storage through an address space

So far, we've mostly discussed anonymous memory.

But virtual memory can also map file contents.

On Linux, the `mmap` interface allows a process to create a mapping associated with a file or another supported object.

Rather than explicitly issuing a separate file read for every piece of data, an application can access mapped contents through memory addresses.

The kernel manages the relationship between the virtual pages and the underlying backing object.

This can be useful for large datasets, executable images, database storage mechanisms, and other workloads.

### Mapping doesn't mean loading everything immediately

Suppose our document processor maps a multi-gigabyte reference file.

Creating the mapping does not necessarily read the entire file into RAM.

The process establishes a virtual address range associated with that file.

As pages are accessed, the kernel can provide the relevant backing from already cached data or storage as needed.

This makes memory mapping attractive for workloads that access only selected portions of large files.

However, memory mapping isn't automatically faster than every ordinary file-I/O strategy.

Access patterns, page-fault overhead, cache behavior, and workload characteristics all matter.

### Shared versus private mappings

Two common mapping styles are particularly important.

A **shared mapping** permits modifications to be visible through other compatible shared mappings, according to the relevant memory and synchronization rules.

For file-backed shared mappings, updates can also be propagated to the underlying file.

A **private mapping** uses copy-on-write semantics.

Changes made through a private mapping do not become modifications to the underlying mapped file.

This is a useful distinction because a process can read shared file-backed data without every process needing an independent physical copy.

Yet it can obtain private modified pages when appropriate.

### A persistence warning

A writable memory mapping does not eliminate filesystem durability concerns.

Changes visible in memory aren't automatically guaranteed to survive power loss at every instant.

The relevant synchronization and durability interfaces, such as `msync` and filesystem synchronization mechanisms, matter according to the required persistence contract.

Memory mapping changes how an application accesses data.

It does not magically make persistent storage infallible.

## 10. Copy-on-write: the heart of our production mystery

We can now reconstruct the behavior of our worker processes.

The parent loads a six-hundred-mebibyte reference dataset.

Then it creates child processes using `fork`.

In a conventional Linux fork arrangement, the child inherits a virtual address-space layout derived from the parent.

But Linux does not need to eagerly duplicate every physical page.

Instead, suitable pages can remain shared under copy-on-write protections.

The parent and child have distinct address-space mappings, but some mappings initially refer to the same physical frames.

### Before the write

Suppose the parent has a virtual page containing reference-data records.

The child inherits the corresponding contents.

Both processes can read the same underlying physical page without needing an immediate copy.

The kernel maintains the relevant mapping and sharing state.

For private writable pages, protections ensure that a later write will be handled appropriately.

### During the first write

Now the child modifies a record.

The processor encounters a write that cannot proceed directly through the current protected copy-on-write mapping.

The kernel handles the fault.

Where necessary, it provides a private physical page containing the appropriate previous contents, updates the child's mapping, and permits the write.

The parent continues seeing its own logical contents.

The child sees its modified contents.

The two processes have diverged.

This is copy-on-write.

### Why this is efficient

Many forked processes do not modify most of the memory they inherit.

A child may execute another program shortly after being created.

Or several workers may read a shared dataset without modifying it.

Eagerly duplicating all memory would waste time and RAM.

Copy-on-write postpones duplication until changes require separate physical storage.

But it isn't free.

Forking still has process-management and page-table-related costs, and subsequent writes can require copying pages and updating mappings.

For applications with very large address spaces, these costs can become significant.

### The surprising amplification effect

Suppose the dataset spans many pages.

Each worker modifies a small number of bytes.

If those writes touch a few pages, the extra physical cost may be relatively modest.

But if each worker modifies one byte on every page, each may cause private copies of a very large fraction of the dataset.

The amount of application data changed may be small.

The number of physical pages copied can be enormous.

This is because copy-on-write operates at page granularity, not necessarily at the granularity of a single object field or byte.

That is the key to our mystery.

**The size and distribution of writes matter, not merely the number of bytes modified.**

## 11. RSS, PSS, and why summing process memory can mislead

Our workers now have a large virtual address-space footprint.

We inspect the resident memory of each process.

The measurements seem to show the shared reference dataset in every process.

Did we really allocate multiple independent copies?

Not necessarily.

We need to distinguish three common measurements.

### Virtual size

Virtual memory size describes the total extent of a process's mapped virtual address space under the tool's accounting conventions.

It can include areas without currently resident physical backing.

A large virtual size is not automatically a large RAM footprint.

### Resident Set Size

RSS measures memory pages resident in RAM and mapped into a process, according to the relevant operating-system accounting.

But shared physical pages can contribute to the RSS of multiple processes.

If four processes map the same resident data, adding their RSS values may count some of the same physical pages several times.

Therefore, the sum of process RSS values does not necessarily equal total physical RAM consumption.

### Proportional Set Size

PSS attempts to distribute the cost of shared resident pages proportionally among the processes mapping them.

If a physical page is shared among four relevant mappings, each receives an appropriate fraction under PSS accounting.

This can make PSS more useful than summed RSS when investigating workloads with substantial shared memory.

It is still a measurement with defined scope and accounting rules, not a complete universal measure of all memory consumption.

For our forked workers, PSS helps distinguish shared data from private physical copies.

When workers begin writing inherited pages, private-memory growth may become visible.

We will use these accounting distinctions more extensively in the next lecture, which focuses on memory pressure and resource limits.

Today, they explain why a process can appear large without owning a separate physical copy of every resident page.

## 12. Huge pages and the cost of translation

We have another practical problem to consider.

Our reference dataset is large.

If the system uses four-kibibyte pages, a one-gibibyte region spans 262,144 base pages.

That can require a substantial number of translations.

TLBs have limited capacity.

If an application frequently accesses memory spread across many pages, translation-cache misses can become costly.

### Huge pages

Many processors support larger page mappings.

For example, common x86-64 configurations support two-mebibyte mappings, and certain arrangements support even larger pages.

A larger mapping covers more address space with one translation entry.

That can reduce TLB pressure.

Linux supports mechanisms including explicit HugeTLB pages and Transparent Huge Pages, or THP.

Transparent Huge Pages allow the kernel to use larger mappings in suitable circumstances without requiring applications to manage every huge-page allocation explicitly.

### The trade-off

Larger pages aren't universally better.

They can increase allocation and copy granularity, affect memory utilization, and introduce costs when pages need to be split or manipulated.

Some workloads benefit substantially from fewer TLB misses.

Others see little improvement or experience undesirable latency and memory effects.

Modern Linux also supports multiple transparent huge-page sizes on suitable configurations.

The important engineering principle is not "always enable huge pages."

It is to understand why page size influences translation performance and to evaluate the workload before changing memory policy.

## 13. Memory locality: the performance consequence

Now imagine two algorithms performing the same number of computations.

The first walks through an array sequentially.

The second follows pointers scattered unpredictably across a very large data structure.

Both might perform similar arithmetic.

But their memory-access behavior can be dramatically different.

Sequential traversal often benefits from data-cache locality, predictable access patterns, and hardware prefetching.

Scattered traversal can cause more data-cache misses and potentially more TLB misses if the working set spans many pages.

These are separate effects that can interact.

A program can be CPU-bound while spending substantial execution time stalled on memory access.

Adding threads may not solve a memory-bandwidth or locality bottleneck.

Likewise, changing the language may be less important than changing how data is organized and accessed.

This connects operating-system memory machinery to algorithmic thinking.

Data structures aren't merely about big-O complexity.

They also determine how execution interacts with caches, pages, and physical memory.

## 14. What this means for Node.js, Python, and native programs

The concepts we've studied aren't limited to C or C++.

A Node.js application operates within a process with virtual memory mappings.

V8 manages JavaScript objects, but the underlying process still uses operating-system memory facilities.

Native buffers, executable code, runtime structures, thread stacks, and memory mappings all participate in the broader process address space.

Python similarly manages language-level objects while relying on the operating system for memory mappings and process isolation.

Native programs also operate within the same general virtual-memory framework on conventional Linux systems.

The language runtime manages one layer of allocation and object lifetimes.

The operating system and processor manage another layer involving pages, mappings, physical memory, and protection.

### A crucial distinction from CS220

In CS220-L04, we studied references, garbage collection, and application-level memory leaks.

Those subjects answer questions such as:

"Why is this JavaScript object still reachable?"

"Why does this cache retain thousands of customer profiles?"

"Why does a listener keep an object alive?"

This lecture answers different questions:

"Where does the process's memory address point?"

"Why can a mapping exist without a resident physical page?"

"Why did the first access fault?"

"Why did a forked process share memory until it wrote to a page?"

The layers interact, but they must not be confused.

A perfect garbage collector does not remove the need for virtual memory.

And virtual-memory protection does not prevent an application from retaining objects indefinitely.

## 15. Diagnosing the worker incident

Let's reconstruct the original production mystery with what we now know.

Our document processor loads a large reference dataset, then forks four workers.

The parent and children begin with virtual mappings that may refer to shared physical pages.

Each process can report a substantial resident set, even though some of those resident pages are shared.

Summing RSS overstates the amount of unique physical memory represented by those mappings.

Now the workers begin modifying inherited data.

Copy-on-write causes suitable pages to become private when modifications require independent physical storage.

As more distinct pages are modified, physical memory consumption rises.

Meanwhile, the first access to a valid mapped page may trigger a page fault to establish backing or a page-table translation.

Later accesses may avoid that work when the page is present and the translation is cached or can be obtained without a fault.

This explains why an initialization or warmup phase may exhibit different behavior from steady-state processing.

### The investigator's sequence

First, identify whether the workload uses separate processes, threads, or both.

Second, inspect the virtual mappings and determine whether large regions are anonymous, file-backed, private, or shared.

Third, compare virtual size, RSS, PSS, and private-memory information rather than blindly adding process RSS values.

Fourth, determine whether memory growth correlates with writes after forking or other allocation activity.

Fifth, if performance is the concern, distinguish minor faults, major faults, TLB behavior, and ordinary data-cache effects.

Finally, choose an intervention supported by the evidence.

For a read-mostly dataset, preserving sharing may be valuable.

For frequently modified per-worker state, independent allocation might be more predictable.

For scattered access patterns, improving data locality may be more productive than changing page size.

There is no universal answer without knowing the workload.

What we now possess is the model needed to investigate intelligently.

---

# The Oral Examination

Answer each question aloud before reading its solution. Explain why the behavior occurs, not merely what the terminology means.

**Question 1 — The identical address**

Two unrelated processes access virtual address `0x1000`. Why does that not mean they access the same physical RAM?

**Question 2 — The enormous allocation**

A program creates a large virtual anonymous mapping but initially uses little physical memory. How is that possible, and what may happen when it starts writing to the pages?

**Question 3 — The TLB confusion**

What is the difference between a TLB miss and a page fault? Does every TLB miss require entering the kernel?

**Question 4 — The harmless fault**

A process experiences thousands of minor page faults during startup but continues normally. Why isn't that automatically a bug?

**Question 5 — The forbidden write**

A process attempts to write into a read-only mapping. What mechanisms detect the violation, and what outcomes are possible?

**Question 6 — The forked workers**

A parent loads a large read-mostly dataset, then forks several children. Why doesn't this necessarily require an immediate complete physical copy for every child?

**Question 7 — The one-byte disaster**

Four forked workers each modify only one byte in each page of a large inherited region. Why can this consume far more additional memory than the number of bytes logically changed?

**Question 8 — The misleading dashboard**

Four processes each report a large RSS, but their summed PSS is much smaller. What does this suggest?

**Question 9 — The performance puzzle**

Two algorithms perform the same number of arithmetic operations, but one accesses memory sequentially while the other follows scattered pointers. Why might the first be substantially faster?

---

# Solutions and Discussion

## Solution 1 — Process-specific translation

Virtual addresses are interpreted through the process's address-space mappings.

Two identical numerical virtual addresses can map to different physical frames because the processes have different page tables and mapping contexts.

Only deliberate sharing or another appropriate arrangement allows access to the same underlying physical memory.

## Solution 2 — Mapping before residency

The operating system can establish a valid virtual address range without immediately providing a separate physical page for every page in the range.

On access, demand paging may establish the required backing.

Writes can therefore increase resident physical memory consumption.

Actual behavior depends on allocation policy, mappings, and resource limits.

## Solution 3 — Cache miss versus mapping exception

A TLB miss means an appropriate translation isn't currently available in the processor's translation cache.

A page-table walk may find a valid mapping without entering the kernel.

A page fault occurs when the access cannot be completed under the current translation/protection state and requires exception handling.

They are different events.

## Solution 4 — Normal demand paging

Minor page faults can occur while establishing mappings or physical backing without requiring disk I/O to retrieve the needed page.

They may be normal during startup, first-touch allocation, or copy-on-write handling.

Their frequency and cost should be interpreted in workload context rather than treated as automatic evidence of failure.

## Solution 5 — Permission enforcement

The MMU checks the relevant translation and protection state.

An unauthorized write can raise a page-fault exception.

The kernel examines whether a legitimate mechanism, such as copy-on-write, can resolve the situation.

If the access is truly forbidden, the process may receive an error signal such as `SIGSEGV`.

## Solution 6 — Copy-on-write

Suitable inherited pages can initially remain physically shared.

The parent and children have their own virtual mappings, but those mappings can reference the same physical frames.

Private copies are created when writes require the processes' contents to diverge.

This avoids unnecessary eager duplication.

## Solution 7 — Page-granularity copying

Copy-on-write generally operates at page granularity.

Changing one byte can require a private copy of the page containing it.

If each worker modifies data on many distinct pages, substantial physical copying may occur even though only a tiny number of individual bytes were changed.

## Solution 8 — Shared resident memory

RSS can count the same physical pages in multiple processes.

PSS accounts for shared pages proportionally.

A much smaller summed PSS suggests that a substantial amount of resident memory is shared, rather than independently allocated to every process.

## Solution 9 — Memory locality

Sequential access often benefits from cache locality, hardware prefetching, and efficient translation behavior.

Scattered accesses may trigger more data-cache and TLB misses.

The algorithms may have similar arithmetic complexity but very different hardware execution costs.

---

# The Mental Model Worth Keeping

**A virtual address is a promise of an address-space location, not a declaration of ownership over a particular physical RAM location.**

Four distinct questions determine what happens when a program uses that address:

1. **Is the address part of a valid mapping?**
2. **What permissions apply to the attempted access?**
3. **Is the required physical backing and translation already available?**
4. **Is the backing private, shared, or subject to copy-on-write?**

The kernel establishes the rules. The MMU enforces ordinary translations and protections. Page faults allow the kernel to resolve exceptional accesses when appropriate.

Once these distinctions are clear, much of memory management stops looking mysterious.

# Next Lecture — Memory Pressure, Cgroups, and OOM

We've discovered how a process obtains a virtual address space and how that space can be backed by physical memory.

But physical memory is finite.

What happens when processes demand more resident memory than the system can comfortably provide?

Why does Linux use RAM for file caching? Why can reclaim cause latency spikes? Why does swapping sometimes help and sometimes make performance miserable?

And why can a Node.js application be killed for exceeding its container's memory budget while its JavaScript heap appears perfectly healthy?

In CS320-L04, we'll descend from address translation into the operational economics of physical memory: resident sets, page cache, reclaim, swap, cgroup accounting, and out-of-memory behavior.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Lab — Watch Virtual Memory Behave

These experiments are intended for a local Linux environment. On Windows or macOS, use a suitable Linux virtual machine or container where the relevant `/proc` interfaces are available.

The experiments use modest allocations and do not require changing kernel settings or running as root.

## Experiment A — Inspect your process's memory map

On Linux, examine your shell's mappings:

```bash
cat /proc/$$/maps | head -30
```

The output describes mapped virtual address ranges and their properties.

You may see executable segments, shared libraries, heap-related regions, stacks, and other mappings.

Look at the permission field.

Common characters include `r` for readable, `w` for writable, `x` for executable, and `p` for private or `s` for shared mapping semantics.

**Question:** Why might one process have multiple mappings referring to the same executable file, but with different permissions?

## Experiment B — Reserve memory, then touch it

This Python program establishes an anonymous memory mapping, then writes one byte on each base-page-sized interval.

```python
import mmap
import os
import resource

MIB = 1024 * 1024
SIZE = 64 * MIB
PAGE = os.sysconf("SC_PAGE_SIZE")

def faults():
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_minflt, r.ru_majflt

def rss_kib():
    with open("/proc/self/smaps_rollup") as f:
        for line in f:
            if line.startswith("Rss:"):
                return int(line.split()[1])
    return None

print("Page size:", PAGE)
print("Before:", faults(), rss_kib())

region = mmap.mmap(-1, SIZE)

print("After mapping:", faults(), rss_kib())

for offset in range(0, SIZE, PAGE):
    region[offset] = 1

print("After touching pages:", faults(), rss_kib())

region.close()
```

Depending on the kernel, allocator behavior, page size, and environment, the observations may vary.

The expected conceptual pattern is that establishing the virtual region and populating its physical backing are distinguishable operations.

First-touch writes often cause minor faults and additional resident memory.

**Question:** Why is the difference between the second and third measurement more interesting than merely examining the mapping size?

## Experiment C — Observe shared versus private mappings

Create a temporary file and map it privately.

```python
import mmap
import os
import tempfile

with tempfile.TemporaryFile() as f:
    f.write(b"HELLO" + b"\0" * 4091)
    f.flush()

    private = mmap.mmap(
        f.fileno(),
        4096,
        flags=mmap.MAP_PRIVATE,
        prot=mmap.PROT_READ | mmap.PROT_WRITE,
    )

    print("Mapped before:", private[:5])

    private[:5] = b"WORLD"

    f.seek(0)
    print("Mapped after:", private[:5])
    print("File after:", f.read(5))

    private.close()
```

The private mapping can diverge from the file's contents without rewriting the underlying file.

**Question:** Where did the modified bytes go conceptually, and why do they not represent a persisted update to the original file?

## Experiment D — Observe copy-on-write after fork

This experiment uses `os.fork`, so it is intended for Unix-like systems, particularly Linux.

It creates a populated region before forking. The child modifies pages while the parent remains alive.

```python
import os
import time

MIB = 1024 * 1024
PAGE = os.sysconf("SC_PAGE_SIZE")

region = bytearray(32 * MIB)

# Ensure the region has been written before fork.
for i in range(0, len(region), PAGE):
    region[i] = 1

def show_memory(label):
    with open("/proc/self/smaps_rollup") as f:
        lines = [
            line.strip()
            for line in f
            if line.startswith((
                "Rss:",
                "Pss:",
                "Private_Dirty:",
                "Shared_Dirty:"
            ))
        ]
    print(label, os.getpid(), *lines, sep="\n", flush=True)

show_memory("Parent before fork")

pid = os.fork()

if pid == 0:
    show_memory("Child before writes")
    time.sleep(1)

    for i in range(0, len(region), PAGE):
        region[i] = 2

    show_memory("Child after writes")
    os._exit(0)

os.waitpid(pid, 0)
show_memory("Parent after child exits")
```

This experiment does not attempt to isolate every allocator and runtime effect.

It illustrates the difference between shared resident pages and private pages produced by writes after fork.

**Question:** Why can the child's private memory grow even though the number of logical bytes in its `bytearray` is unchanged?

## Experiment E — Separate fault types

Use the earlier anonymous-mapping example and measure `ru_minflt` and `ru_majflt`.

Then repeat some reads and writes over the same already-populated pages.

Compare fault-counter changes.

You should normally expect first-touch behavior to differ from repeatedly accessing valid resident pages, though the exact counts depend on the environment.

**Question:** Why should you avoid concluding that every memory-performance problem is caused by major page faults?

---

# Further Reading

Primary technical references:

1. Linux Kernel Documentation — Memory Management Concepts  
   https://docs.kernel.org/admin-guide/mm/concepts.html

2. Linux Kernel Documentation — Page Tables  
   https://docs.kernel.org/mm/page_tables.html

3. Linux Manual Pages — `mmap(2)`  
   https://man7.org/linux/man-pages/man2/mmap.2.html

4. Linux Manual Pages — Process Memory Mappings  
   https://man7.org/linux/man-pages/man5/proc_pid_maps.5.html

5. Linux Manual Pages — Detailed Mapping Statistics  
   https://man7.org/linux/man-pages/man5/proc_pid_smaps.5.html

6. Linux Kernel Documentation — Transparent Hugepage Support  
   https://docs.kernel.org/admin-guide/mm/transhuge.html

Related programme chapters:

- CS220-L04 — References, Garbage Collection, and Memory Leaks
- CS320-L01 — The Kernel, Processes, and Containers
- CS320-L02 — CPU Scheduling, Quotas, and Contention
- CS320-L04 — Memory Pressure, Cgroups, and OOM

---

## Dense Cheatsheet — Interview Glance Card

```text
CS320-L03 — VIRTUAL MEMORY AND ADDRESS TRANSLATION

CORE IDEA
  Virtual address != physical address
  Each process ordinarily has its own virtual address space
  Kernel manages mappings; MMU translates and enforces access
  Same virtual number can map to different physical pages
  Different virtual addresses can map to shared physical data

WHY VIRTUAL MEMORY?
  Process isolation
  Flexible placement and relocation
  Controlled sharing
  Sparse mappings and demand paging
  Hardware-enforced memory protection

PAGES
  Base page often 4 KiB, architecture/config dependent
  Virtual address = page number + offset
  Physical address = frame number + same offset
  4 KiB page = 12-bit offset
  Pages can be private, shared, file-backed, anonymous

PAGE TABLES
  Hierarchical translation structures
  Map virtual pages to physical frames or other states
  Store relevant presence and protection information
  Sparse hierarchy avoids huge flat tables
  VMA = valid region and its mapping properties
  Page-table entry = more granular translation state
  Valid mapping != every page physically resident

MMU / TLB
  MMU = hardware translation and protection
  TLB = cached virtual-to-physical translations
  TLB hit = translation reused
  TLB miss = translation must be obtained
  TLB miss != page fault
  Page-table changes need appropriate TLB invalidation

PAGE FAULTS
  Fault = access cannot complete using current mapping state
  Kernel decides whether access is valid and resolvable
  Anonymous first-touch -> establish backing
  File mapping -> map cached page or retrieve data
  Copy-on-write -> private page when required
  Invalid access -> commonly SIGSEGV or sometimes SIGBUS
  Minor = no disk I/O needed to bring in page
  Major = disk I/O needed for page
  Page fault != automatically a crash

MEMORY PROTECTION
  Read / write / execute permissions
  User process cannot freely access arbitrary kernel memory
  Different processes have separate mappings
  Read-only region rejects unauthorized writes
  W^X reduces unnecessary writable+executable memory
  Guard pages can detect certain invalid accesses

MAPPING
  mmap = establish mapping in virtual address space
  Anonymous mapping = not backed by ordinary file contents
  File mapping = file-associated virtual pages
  MAP_SHARED = compatible mappings can observe writes
  MAP_PRIVATE = private copy-on-write changes
  Mapping != full eager file read
  Visible memory write != guaranteed durable persistence

COPY-ON-WRITE
  fork may initially share suitable physical pages
  Write to shared COW page -> fault + private backing as needed
  Parent and child logically diverge
  Saves eager copying costs
  Many small writes across distinct pages can copy many pages
  Copy granularity generally page-based, not byte-based
  COW may increase physical memory as writes occur

MEMORY MEASUREMENT
  VSS / virtual size = mapped address-space extent
  RSS = resident pages mapped into process
  Shared pages can count in multiple processes' RSS
  PSS = proportional accounting of shared resident pages
  Sum(RSS) may double-count shared physical memory
  Private memory growth may reveal COW activity
  V8 heap != entire process address space or RSS

HUGE PAGES
  Larger mappings cover more memory per translation
  May reduce TLB misses and translation overhead
  Transparent Huge Pages can be managed by kernel
  Benefits depend on workload
  Trade-offs: copy/fragmentation/granularity/latency costs

PERFORMANCE
  Sequential access often improves locality and prefetching
  Scattered pointer chasing may increase cache/TLB misses
  Equal big-O != equal hardware execution cost
  First access may fault; repeated resident access often won't
  TLB miss, page fault, data-cache miss = DIFFERENT events

DIAGNOSTIC SEQUENCE
  1. Is the address mapping valid?
  2. What permissions apply?
  3. Is physical backing present?
  4. Is mapping private/shared/COW?
  5. Are fault counts significant in context?
  6. Compare VSS, RSS, PSS, private/shared pages
  7. Check access locality and page size when relevant

SENIOR INTERVIEW LINE
  "I'd distinguish the process's virtual address space from
   resident physical memory, examine mapping permissions and
   page-fault behavior, then account for sharing and COW before
   assuming process memory statistics represent independent RAM."

MENTAL MODEL
  Virtual address is a location in a process-specific map.
  MMU translates it; kernel manages it.
  Page faults establish, retrieve, copy, or reject backing.
```
