---
id: CS320-L01
course: CS320
title: "The Kernel, Processes, and Containers"
type: core
manuscript: revised
edition: "2.1.0"
legacy_ids: [CS101-S10]
prev: null
next: CS320-L02
---

# CS320 — Operating Systems and Concurrency

## Lecture 01: The Kernel, Processes, and Containers

*Your application does not run directly on a computer. It runs inside a world constructed and governed by an operating system. Understanding that world explains a remarkable number of production mysteries.*

# Part I — Intuition

## The picture to carry in your head

Imagine that you've developed a document-processing service.

Customers upload PDF files. Your Node.js backend receives them, extracts information, stores results in PostgreSQL, and occasionally generates downloadable reports.

On your laptop, the application works perfectly.

Then you put it into a Docker container.

Three strange things happen.

First, the application announces that it is listening on port 3000, but requests from outside the container cannot reach it.

Second, a document saved successfully to a local directory disappears after a deployment replaces the container.

Third, when the deployment platform asks the application to terminate, the process sometimes refuses to shut down cleanly.

Your JavaScript hasn't fundamentally changed. The HTTP framework hasn't changed. PostgreSQL is still PostgreSQL.

So what changed?

The environment in which your application exists.

The central idea of this lecture is that **a running program exists inside an operating-system-managed execution environment**, and that environment determines what the program can see, what it can access, and how it participates in the rest of the machine.

To understand containers, we first need to understand processes.

## 1. A program is a description; a process is an execution

Think of a recipe and a restaurant kitchen.

The recipe describes how to make a meal. But the recipe itself doesn't cook anything.

Someone must provide a kitchen, ingredients, tools, workspace, and a cook who actually performs the instructions.

A program is similar to the recipe. Its source code and executable files describe operations, but they are not, by themselves, a running execution.

When you start Node.js, the operating system establishes a process.

That process has an identity, a virtual address space, access to open resources, security credentials, and one or more threads of execution. It also has a working directory, environment variables, and relationships with other processes.

The JavaScript runtime operates within that process.

Two processes can execute the same Node.js program simultaneously while maintaining separate memory, different environment variables, and different open connections.

The program is the same. The running worlds are different.

This distinction is the first foundation of operating-system reasoning.

## 2. The kernel is the authority behind the abstractions

Imagine several restaurants operating inside one large building.

Each restaurant has its own kitchen and employees, but none is allowed to rewire the building's electricity, move another restaurant's equipment, or take over the elevators.

A building management authority controls the shared infrastructure.

In a computer, much of that authority belongs to the operating-system kernel.

Your application may request access to a file, create a network connection, allocate memory, or start another process. But it cannot simply command arbitrary hardware resources without going through the appropriate mechanisms.

The kernel provides controlled interfaces.

It creates and manages processes, participates in memory management, mediates access to devices and filesystems, and coordinates execution on available processors.

Applications ordinarily run in **user mode**, with restricted privileges. The kernel operates with elevated privileges, protected from ordinary application code.

When an application needs a protected service, it crosses the boundary through a system call.

You don't normally write those system calls directly in TypeScript. Node.js and its libraries provide higher-level interfaces.

But the underlying boundary still exists.

The runtime makes the operating system convenient. It does not make the operating system disappear.

## 3. A container changes the world a process experiences

Now imagine that our restaurant building has movable walls.

Management can give each restaurant a different entrance, a different directory of rooms, and a different view of the building. One restaurant might not even know another restaurant exists.

Yet all the restaurants still occupy the same building.

That is a useful first approximation of Linux containers.

A typical Linux container is not a miniature virtual machine with an independent operating-system kernel.

It contains ordinary processes executing under the host's Linux kernel.

What changes is the environment exposed to those processes.

Linux provides mechanisms called **namespaces**, which can give different groups of processes different views of selected system resources.

A process may see a particular set of process identifiers, network interfaces, filesystem mounts, or hostnames.

Another process can see a different arrangement.

These separate views allow a container to behave like an independent environment without requiring an independent kernel.

But isolation of what you see is only part of the story.

## 4. Isolation is not the same thing as a resource budget

Imagine that each restaurant has its own entrance and private kitchen.

That does not prevent one restaurant from consuming almost all the electricity in the building.

We need another mechanism to govern resources.

Linux provides **control groups**, generally called cgroups.

Cgroups organize processes into hierarchies and support resource accounting and control.

Depending on the controllers and configuration, they can govern CPU allocation, memory consumption, process counts, and other resource behavior.

Here's the distinction worth memorizing:

**Namespaces influence the environment and identities a process sees. Cgroups influence how resources are accounted for and controlled.**

Neither replaces the other.

A process can have a private network view but no meaningful CPU restriction.

A process can be constrained by a memory cgroup without being placed inside a separate network namespace.

Container runtimes combine multiple kernel mechanisms to construct the desired environment.

The container isn't one magical operating-system feature.

It's an engineered arrangement of ordinary features.

## 5. Why localhost is not the place you thought it was

Return to our document processor.

It starts a server on `127.0.0.1:3000`.

Inside the container, the server responds successfully.

From outside, nothing.

The reason is that `127.0.0.1` is a loopback address associated with the current network namespace.

Our process is listening on its own loopback interface.

Other network namespaces have their own loopback contexts.

They don't automatically share ours.

Even publishing the container's port does not necessarily make an application bound only to container loopback reachable through the container's non-loopback address.

The application generally needs to listen on an appropriate interface, commonly `0.0.0.0` for IPv4, when it is intended to accept connections arriving through the container's network interface.

The important lesson isn't a Docker command.

It's that **an address is meaningful within a network environment**.

A name or address that works inside one process's environment may refer to something different—or nothing useful—from another.

## 6. A container is also a lifecycle arrangement

The third mystery was shutdown.

A container has a main process whose lifecycle matters to the runtime managing the container.

In an ordinary private PID namespace, the first process receives PID 1.

On Linux, this position carries special process-management behavior.

If that namespace's init process terminates, the kernel terminates the remaining processes in that PID namespace. Orphaned children may also need to be reaped by the appropriate parent or subreaper.

Signals introduce another complication.

A process can ordinarily receive a termination request such as `SIGTERM`, install a handler, and perform cleanup.

But if a shell is the container's main process and the actual Node.js application is its child, the signal might not reach the intended recipient.

Even if it does, the application still needs an effective shutdown procedure.

The operating system can deliver a termination request. It cannot automatically finish an interrupted database transaction, safely acknowledge a background job, or determine whether a customer payment completed.

Those are application responsibilities.

## The intuition pass: three questions

Before continuing, try answering these without looking backward.

1. If two containers use the same Linux kernel, how can each appear to have its own processes and network interfaces?
2. Why doesn't a private network namespace automatically prevent a process from consuming excessive CPU?
3. Why might a perfectly valid Node.js application behave differently when launched as a container's PID 1?

If you can explain the distinctions, you have the foundation. Now we can investigate the actual mechanisms.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The operating system is part of your application's behavior

Let's return to our document-processing service.

Its essential architecture is simple.

An HTTP endpoint receives a document. The backend validates the request, stores or processes the file, calls PostgreSQL, and returns a result.

We might think of the application as a collection of functions and dependencies.

But that description misses an important layer.

The application runs in a process, and the process exists inside an operating-system environment.

That environment determines whether a network address is reachable, whether a path refers to a persistent location, whether a file is readable, and how the process responds to termination.

This is why identical application code can behave differently on two machines.

Sometimes the difference is a dependency version or environment variable.

Sometimes the difference is a kernel-enforced permission, namespace, resource restriction, or filesystem arrangement.

When investigating deployment failures, we must distinguish **what the application requested** from **what the operating system permitted and provided**.

That distinction is our organizing principle.

## 2. A process is more than a running function

When we execute `node server.js`, the operating system creates or transforms a process so that it executes the Node.js program.

This process has several relevant categories of state.

Its **address space** describes the virtual memory addresses available to its code and data. Its **threads** provide execution contexts. Its **open file descriptors** refer to resources such as files, sockets, and pipes.

It also has credentials, an environment, a working directory, signal dispositions, and various resource limits.

These properties are not merely documentation.

They affect behavior.

Suppose two copies of our document processor run on one machine.

Both execute the same JavaScript files.

But one process runs with credentials allowing access to `/srv/documents`, while the other lacks that permission.

One process has an environment variable pointing to the production database, while the other points to a testing database.

One has a TCP socket listening on a particular address; the other doesn't.

The same program can produce profoundly different results because its process environments differ.

### Processes versus threads

A process is commonly described as a resource and protection boundary.

A thread is an execution context within that process.

Multiple threads in one conventional process share much of the process's address space and many other resources, but each has its own execution state, including a stack and processor register state.

Two threads can therefore operate on shared memory while following different execution paths.

Two separate processes normally cannot read each other's private memory simply by possessing the same virtual address.

They require some permitted sharing or interprocess communication mechanism.

This distinction is fundamental.

A multithreaded process is not equivalent to several independent processes, even if both arrangements can execute work concurrently.

The kernel's scheduler ultimately manages schedulable execution entities, which on Linux commonly correspond to threads.

But we will study the scheduler itself in the next lecture.

For now, retain the distinction between the execution environment and the execution contexts living within it.

## 3. Creating a process: inheritance and replacement

A process must come from somewhere.

On traditional Unix-like systems, two important mechanisms illustrate the model: `fork` and `exec`.

A fork creates a new process derived from an existing process. The new process initially inherits many aspects of its parent's state, according to the relevant operating-system rules.

An exec operation replaces the program image executed within an existing process.

Conceptually, a shell can create a child and have that child execute Node.js.

The result is a new process running the Node.js executable.

Modern implementations may use related process-creation facilities and optimizations instead of literally performing this exact two-call sequence, but the conceptual distinction remains useful.

**Creating an execution context and selecting the program it executes are different operations.**

This also explains why process identity and program identity are not synonymous.

A process may replace its executable image while retaining its process identity.

And multiple processes may execute the same executable simultaneously.

### Parent and child relationships

Processes also participate in lifecycle relationships.

A parent may create a child, observe its termination, and collect its exit status.

On Unix-like systems, terminated children can temporarily remain as zombies until their termination status is collected.

A zombie isn't a running process consuming ordinary CPU time. It is retained process metadata awaiting collection.

For our document processor, this becomes relevant if the application launches child processes for PDF conversion, image manipulation, or external utilities.

Someone must manage their lifetimes.

If the application launches children and never waits for them appropriately, process-management problems can accumulate.

A container's main process may therefore need to behave as more than a passive JavaScript runner.

## 4. User mode and kernel mode: why applications must ask

Your JavaScript can create an object without directly requesting permission from the kernel for every property assignment.

But when the application needs to open a file or create a network socket, lower-level facilities eventually request kernel services.

This brings us to the system-call boundary.

A system call is a controlled entry point from user-space execution into the kernel.

For example, Linux exposes operations for opening files, reading data, creating sockets, mapping memory, and managing processes.

The kernel validates the request according to its rules and current state.

A file operation might succeed, or it might fail because the path doesn't exist, credentials lack permission, the filesystem is read-only, or some relevant resource limit has been reached.

The application receives a result or error reflecting that operation.

It does not receive an unconditional guarantee that the requested action will succeed simply because the code is syntactically valid.

### The important distinction between APIs and system calls

A high-level runtime API isn't necessarily a single system call.

Consider reading a file using Node.js.

The JavaScript API may perform validation, translate arguments, coordinate asynchronous work, invoke native libraries, and eventually interact with operating-system facilities.

Several lower-level operations may contribute to one high-level call.

Likewise, a single system call might be wrapped by several layers of software.

The practical mental model is:

Application code expresses intent. The runtime translates that intent into lower-level operations. The kernel mediates the protected resources.

In the dedicated I/O lecture, we will examine file descriptors, blocking and nonblocking operations, readiness notification, completion mechanisms, and how Node.js uses libuv.

For now, the kernel boundary is what matters.

## 5. Permissions: identity is not authority

Our document processor needs access to an uploaded file.

The path exists.

But opening it fails with a permission error.

A common debugging mistake is to focus entirely on the path.

We should also ask: **Which identity is making the request, and what authority does that identity possess?**

Linux processes operate with user and group credentials and related security state.

Filesystem access is influenced by ownership, permission bits, access-control mechanisms, mount options, and applicable security policies.

A process running as a particular user does not automatically gain access to files owned by another user.

A containerized process is still subject to these rules.

### Root inside a container

Now consider a container whose process runs as user ID zero.

Developers often call this root.

But root inside a container is not automatically equivalent to unlimited authority over the host.

User namespaces can map identities differently, and Linux capabilities and other security restrictions can constrain available operations.

Conversely, a badly configured container may receive privileges or mounts that expose highly sensitive host resources.

This is why container isolation should never be treated as an unconditional security guarantee.

We need to know the actual identities, permissions, capabilities, namespace arrangement, and security controls.

For now, the lesson is simple: a process has an identity, and identity participates in decisions about authority.

Later courses will teach how to configure those boundaries safely in deployment environments.

## 6. Namespaces: changing the view without changing the kernel

The most surprising container behavior often comes from namespaces.

A namespace can isolate a particular category of system resources so that processes experience different views.

The important word is **view**.

The kernel hasn't necessarily created an entirely separate physical resource.

It has established a boundary governing what is visible or how resources are identified.

### PID namespaces

Consider two processes.

From the host's perspective, one might have PID 18520 and another PID 18641.

Inside separate PID namespaces, each could appear to have PID 1.

This does not mean Linux assigned the same globally meaningful process identity twice.

Process identifiers are interpreted within namespace contexts.

A process can have different PID values as observed through different layers of the namespace hierarchy.

The parent namespace can generally observe processes in descendant PID namespaces, subject to other permission and visibility rules.

But processes inside a child PID namespace cannot simply enumerate all processes belonging to its ancestors.

This is useful for containers because it lets each isolated workload experience a relatively self-contained process tree.

However, a PID namespace does not inherently create a new kernel or CPU.

The same kernel continues managing execution.

### Network namespaces

A network namespace isolates substantial networking state, including interfaces, addressing, routing, and sockets.

Two processes in separate network namespaces can each listen on the same port number without necessarily conflicting.

The port belongs to a specific network context.

This is why two containers can both run HTTP servers on port 3000.

The host cannot simply assume that every port numbered 3000 refers to one unique global listening socket.

The namespace and addressing environment matter.

### Mount namespaces

A mount namespace controls the view of mounted filesystems.

Two processes may observe different filesystem mount arrangements even though the same underlying storage devices and kernel exist beneath them.

Container runtimes combine mount namespaces with root filesystem construction and other filesystem mechanisms to create the familiar container directory layout.

The important implication is that seeing a path does not tell you where its underlying storage physically lives or how long that storage will remain available.

### Other namespace categories

Linux also provides namespaces for user identities, hostnames and related information, certain interprocess communication facilities, cgroup hierarchy visibility, and selected time-related state.

We do not need to memorize every namespace interface today.

The useful question is: **Which category of system state does this namespace isolate, and what does the process observe from inside it?**

## 7. The localhost incident: trace the actual boundary

Our service announces:

`Listening on 127.0.0.1:3000`

Inside the container, we can successfully connect to that address.

But the container's published port isn't reachable.

Let's distinguish three things.

First, the application has created a listening socket.

Second, that socket is associated with a local address and the container's networking context.

Third, the surrounding container runtime may establish a host-to-container forwarding arrangement.

These are related but separate facts.

Publishing a port does not make every listening socket inside a container reachable through every address.

If our application listens only on container loopback, connections addressed to the container's non-loopback interface will generally not match that listening socket.

Binding to `0.0.0.0` makes the server listen on all local IPv4 interfaces in that network namespace.

That permits connections arriving through appropriate interfaces, assuming the surrounding routing, publishing, and security configuration allows them.

It does not mean the application has bypassed the container's network isolation.

Nor does it imply that any remote machine can necessarily connect.

There may still be firewalls, routing constraints, host port-publishing rules, or other network boundaries.

### The same problem in service-to-service communication

Suppose PostgreSQL runs in another container with its own network namespace.

Our Node.js process tries to connect to `localhost:5432`.

Which environment does localhost identify?

The Node.js process's network namespace.

Not the PostgreSQL container's namespace.

The appropriate solution normally involves the database service's reachable address or service name on a configured network.

A subtle exception is worth recognizing: containers in a Kubernetes Pod ordinarily share a network namespace and can therefore communicate through localhost.

That isn't a contradiction.

It demonstrates the rule.

**Localhost follows the network namespace, not the marketing concept of a container.**

This is the sort of distinction that separates memorized Docker advice from genuine operating-system understanding.

## 8. The filesystem incident: visibility is not durability

Now our document processor successfully saves a customer upload to `/app/uploads`.

The next deployment replaces the container.

The file disappears.

Did Linux lose the data?

Not necessarily.

The application may have written to storage associated with the previous container's writable filesystem layer.

When that container was removed and replaced, the new container did not necessarily inherit the old writable layer.

The new process sees its own filesystem arrangement.

A successful file write is therefore not a guarantee that the same path will preserve that file across container replacement.

This is a lifecycle and storage-design question.

### Three different properties

A useful distinction is between **visibility**, **permissions**, and **durability**.

Visibility asks whether a process can resolve a path in its filesystem environment.

Permissions ask whether the process is allowed to perform an operation on the resolved resource.

Durability asks whether the data survives the relevant failures or lifecycle changes.

A path can be visible and writable while still being unsuitable for persistent customer data.

Conversely, a mounted persistent volume may preserve data beyond the lifetime of the individual container.

Our application needs an explicit storage contract.

For temporary scratch files, a disposable writable layer may be perfectly reasonable.

For customer uploads or authoritative records, we normally need appropriately managed persistent storage—perhaps a mounted volume, object storage, or another durable service.

The operating system helps implement filesystem operations.

It does not decide the application's persistence requirements for us.

## 9. Cgroups: where the resource boundaries come from

Namespaces explain why two processes can see different environments.

But what prevents one workload from consuming too much of a shared machine?

Enter cgroups.

A cgroup is part of Linux's hierarchical resource-management mechanism.

Processes can be organized into groups, and resource controllers provide relevant accounting and control.

For example, a container runtime may configure CPU or memory restrictions for a group of processes.

The kernel enforces applicable limits independently of the application's programming language.

This is why a perfectly healthy host can contain a process that is constrained by its own resource budget.

### An important production distinction

Imagine a host with sixteen logical CPUs.

Our document processor has a configured CPU quota equivalent to a fraction of one CPU's capacity over the relevant accounting interval.

The host dashboard can report abundant unused CPU capacity.

Yet our process can still experience throttling because it has consumed its allowed quota.

Likewise, a memory restriction can cause a workload to encounter an out-of-memory condition within its cgroup without the entire host being out of RAM.

These situations aren't paradoxes.

They involve different resource boundaries.

The kernel enforces a limit attached to the relevant group, not merely a global limit on the machine.

There is a reason we're introducing cgroups conceptually here rather than immediately studying every controller.

The next lecture will examine CPU scheduling, quotas, runnable waiting, and contention.

Later, we'll examine memory accounting, reclamation, and out-of-memory behavior.

Today's responsibility is understanding that a process can have a resource budget that differs from the capacity visible elsewhere on the host.

## 10. Containers are assembled boundaries, not security force fields

At this point we can give a more rigorous definition of a typical Linux container.

It is an execution environment constructed by combining processes, namespace arrangements, filesystem configuration, cgroups, permissions, and additional runtime and security controls.

That collection of mechanisms can provide meaningful isolation.

But the quality of the isolation depends on how those mechanisms are configured.

A process running with broad privileges, sensitive host mounts, or dangerous capabilities may have far more authority than an ordinary restricted container process.

Linux also provides mechanisms such as capabilities and seccomp filters that can restrict particular kinds of privileged operations or system calls.

Other security facilities may enforce additional policies.

A container runtime selects and configures a set of such mechanisms, while the kernel enforces the applicable operating-system boundaries.

### Why sharing a kernel matters

Conventional virtual machines normally have independent guest kernels.

Ordinary Linux containers generally share the host's Linux kernel.

This is one reason containers can be relatively lightweight.

But it also means that a serious kernel vulnerability or unsafe container configuration can potentially undermine isolation.

A container is useful for packaging, process isolation, resource control, and deployment workflows.

It is not automatically sufficient as the sole security boundary for arbitrary untrusted code.

That distinction becomes especially important for systems executing third-party code, security-scanning tools, customer-supplied programs, or AI-generated commands.

The question is not simply whether an application runs inside Docker.

The question is which kernel-enforced boundaries constrain it.

## 11. Signals, PID 1, and graceful termination

Our document processor is now running successfully.

Then the deployment platform needs to replace it.

How does one component request that another process stop?

On Unix-like systems, signals are one important mechanism.

A signal communicates an event or requests behavior according to operating-system rules.

`SIGTERM` commonly requests orderly termination.

`SIGINT` commonly represents an interactive interruption.

`SIGKILL` forces termination and cannot be caught or ignored.

Applications may install handlers for catchable signals.

But receiving a termination request does not itself guarantee a clean shutdown.

### The special role of PID 1

In a private Linux PID namespace, its first process is the namespace's init process and has PID 1.

That position has special signal-handling and lifecycle behavior.

In particular, Linux applies special rules to certain signals whose default action would ordinarily terminate a process. An init process that hasn't installed appropriate handlers may therefore behave differently from an ordinary application process.

PID 1 may also become responsible for reaping orphaned child processes within its namespace.

The exact operational consequences depend on the application and how the container is launched.

### The shell-form problem

Consider a container whose startup command causes a shell to launch Node.js.

The shell may become PID 1, with Node.js running as its child.

If the container runtime sends a termination signal to its main process, that signal may reach the shell without being forwarded correctly to Node.js.

The application doesn't receive the shutdown request it expects.

Using an exec-form container command can avoid an unnecessary intermediary shell, allowing the application itself to become the main process.

But this isn't the whole solution.

If the application creates children, it may still need appropriate process supervision or a minimal init process.

### Shutdown is a protocol

Imagine our document processor is halfway through a customer job when termination is requested.

A robust shutdown procedure should stop accepting new work, allow selected in-flight operations to finish within a bounded deadline, release appropriate resources, and make unfinished work recoverable.

But suppose the job already committed a database update and hasn't yet acknowledged the queue message.

If termination occurs, another worker may eventually process that same message.

The operating system cannot decide whether repeating the job is safe.

That requires application-level correctness mechanisms, such as durable state, idempotency, or appropriate transaction boundaries.

The operating system controls process termination.

The application controls the meaning of an interrupted business operation.

These are different layers of correctness.

## 12. Investigating the three incidents without guessing

We can now revisit our original production failures.

### Incident A: the server is listening but unreachable

We should establish where the process is listening, which address it has bound, and which network namespace owns the socket.

Then inspect the surrounding forwarding and routing arrangement.

If the process listens only on container loopback but the incoming request targets its non-loopback interface, we have a concrete explanation.

We don't need to randomly disable firewalls until the error disappears.

### Incident B: the upload disappears

First establish where the file was written.

Was it on a container-specific writable layer, a mounted persistent volume, or an external storage service?

Then determine what happened when the container was replaced.

The problem might be entirely consistent with the storage arrangement.

Fixing it requires selecting storage with the correct persistence contract, not merely repeating the write.

### Incident C: the application doesn't terminate cleanly

Identify the container's main process.

Is it Node.js, a shell, or an init process?

Which process receives the termination request, and what handlers exist?

Does the application stop accepting work? Does it have a bounded shutdown path? Are child processes handled?

The investigation should distinguish failure to deliver a signal from failure to respond to a delivered signal.

Those are different mechanisms requiring different fixes.

### An investigation habit worth developing

For any unfamiliar operating-system failure, identify the relevant boundary.

Ask what the application believes its environment contains.

Then determine what the kernel actually exposes or permits.

Only after those facts are established should you begin changing configuration.

That habit will remain useful throughout this course.

## 13. What we deliberately haven't studied yet

We've introduced processes, threads, address spaces, system calls, namespaces, and cgroups.

But we've left many mechanisms intentionally unresolved.

We haven't explained how the scheduler chooses a runnable thread, why a CPU quota can produce bursts of delay, or how context switching affects throughput.

We haven't examined how virtual addresses map to physical memory, how page faults work, or how the kernel reclaims memory under pressure.

We haven't explored readiness notification, asynchronous I/O implementation, or shared-memory synchronization.

These aren't omissions from the curriculum.

They are the subjects of the chapters that follow.

This lecture gives us the vocabulary and execution model needed to understand them properly.

---

# The Oral Examination

Try answering these aloud before reading the solutions. Don't aim for a memorized definition; explain the mechanism and its consequences.

**Question 1 — One program, two processes**

Two Node.js processes run the same server source code. Why can they have different memory contents, environment variables, and open network connections?

**Question 2 — Container versus virtual machine**

What does it mean to say that ordinary Linux containers share a kernel? Which parts of their execution environments can nevertheless be isolated?

**Question 3 — Namespace versus cgroup**

A process has a private network namespace but no CPU quota. What has been isolated, and what has not?

**Question 4 — The localhost trap**

An API in container A connects to `localhost:5432`, expecting PostgreSQL in container B. Why does this generally fail, and under what arrangement might localhost actually work?

**Question 5 — Permission denied**

A file path exists inside a container, but the application cannot read it. Which categories of operating-system state would you investigate?

**Question 6 — The disappearing upload**

A process successfully writes a customer document inside its container. The document vanishes after replacement. Explain why a successful write did not guarantee persistence.

**Question 7 — The stubborn container**

A container receives a termination request but does not shut down properly. Explain two distinct failure mechanisms involving its main process and application lifecycle.

**Question 8 — The resource paradox**

A host has spare CPU and memory. Yet a container experiences CPU throttling or an out-of-memory kill. How is that possible?

---

# Solutions and Discussion

## Solution 1 — Program identity versus process state

The executable and source code determine much of the behavior a process can perform, but each process has its own operating-system-managed execution environment.

Memory mappings and contents, environment values, descriptors, credentials, and other resources can differ even when both processes execute the same program.

The program is a description of behavior. The process is one concrete execution with its own state.

## Solution 2 — Kernel sharing and isolation

Ordinary Linux containers execute under the host Linux kernel rather than booting separate guest kernels.

Namespaces can isolate selected views of process IDs, networking, mounts, user identities, and other state. Cgroups can account for and control resources, while permissions and security mechanisms constrain authority.

The resulting environment can appear independent without possessing an independent kernel.

## Solution 3 — Visibility versus resource control

A network namespace changes networking context, such as interfaces, routing state, and local sockets.

It does not automatically impose a CPU quota.

CPU restrictions require appropriate resource-control mechanisms and configuration, commonly involving cgroups.

Isolation of one category of state does not imply isolation of every other category.

## Solution 4 — The meaning of localhost

Localhost refers to the loopback context of the current network namespace.

If containers A and B use different network namespaces, A's localhost does not refer to B.

The application normally needs a reachable service address or name.

However, containers intentionally sharing a network namespace—such as ordinary containers in one Kubernetes Pod—can communicate through shared localhost.

## Solution 5 — Permissions and identity

Investigate the process's user and group credentials, the file's ownership and permissions, any relevant access-control mechanisms, mount properties, and mandatory security restrictions.

Also verify that the path resolves to the expected object in the process's mount environment.

A correct path does not imply permission to access it.

## Solution 6 — Filesystem persistence

The file may have been written into a writable layer associated with the previous container.

Replacing the container can create a new filesystem environment without that former layer's contents.

Persistence requires an explicit storage arrangement that survives the relevant lifecycle changes.

Visibility, successful writing, and durability are different properties.

## Solution 7 — Signal delivery versus application shutdown

One failure is signal delivery: an intermediary shell may receive the termination request without forwarding it correctly to Node.js.

Another is application behavior: Node.js may receive the signal but fail to finish its shutdown procedure because of missing handlers, unbounded waiting, child-process problems, or unresolved background work.

PID 1's special Linux behavior can also affect termination handling.

Diagnose which mechanism failed before changing the container configuration.

## Solution 8 — The relevant resource boundary

A container's process group can be subject to CPU or memory restrictions that are smaller than the host's total capacity.

The kernel enforces these restrictions according to applicable cgroup controllers.

Therefore, unused global capacity does not necessarily mean a constrained process can consume more resources.

The resource boundary being measured matters as much as the resource quantity.

---

# The Mental Model Worth Keeping

A running application is not merely code executing on a CPU.

It is a collection of execution contexts and resources governed by the operating system.

When reasoning about it, ask four questions:

**What is running?** Identify the process, threads, and relevant runtime.

**What can it see?** Identify the namespaces and filesystem/network environment.

**What can it do and consume?** Identify permissions, kernel interfaces, and resource controls.

**How does it live and die?** Identify its parent relationships, main-process responsibilities, signals, and shutdown contract.

Those four questions explain a surprising number of production failures before we've even opened a profiler.

# Next Lecture — CPU Scheduling, Quotas, and Contention

We now understand that the operating system governs the execution of processes and threads.

But there's a mystery waiting beneath that statement.

A machine has sixteen logical CPUs. Our application needs only a small amount of computation per request. The CPU dashboard looks mostly green.

And yet requests are painfully slow.

In the next lecture, we'll follow a runnable thread through the kernel scheduler, learn why wall time and CPU time tell different stories, and discover how a process can starve for execution while the host appears to have abundant capacity.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Lab — Observe the Boundaries

These exercises are intended for a local Linux environment or a machine with Docker available. They should not be run against production workloads.

## Experiment A — Your shell is a process

On Linux:

```bash
echo $$
ps -o pid,ppid,stat,comm -p $$
cat /proc/self/status | head -25
```

Observe the shell's process identity, its parent, and selected process information.

The `/proc` filesystem is a kernel-provided interface exposing information about processes and other system state.

**Question:** Which displayed properties describe the process rather than the shell program's source code?

## Experiment B — Namespace identities

On a Linux system:

```bash
ls -l /proc/self/ns
```

This exposes namespace references associated with the calling process.

You can compare namespace identities for different processes when permissions allow.

If Docker is available, start a disposable container:

```bash
docker run --rm alpine sh -c \
  'echo "Container PID: $$"; ls -l /proc/self/ns; cat /proc/self/cgroup'
```

Compare this with the host's namespace and cgroup information.

On Docker Desktop, remember that the Linux container kernel normally belongs to a managed Linux VM.

**Question:** Which identities differ, and which might be shared?

## Experiment C — The localhost boundary

First start a disposable Node.js HTTP server in a container, binding specifically to container loopback:

```bash
docker run -d --rm --name cs320-loopback \
  -p 127.0.0.1:8080:3000 \
  node:22-alpine \
  node -e 'require("http").createServer((req,res)=>res.end("hello")).listen(3000,"127.0.0.1")'
```

Attempt to connect from the Docker host:

```bash
curl --max-time 3 http://127.0.0.1:8080
```

In a conventional Docker bridge-network configuration, this should not reach a server that listens only on container loopback.

Clean up:

```bash
docker rm -f cs320-loopback
```

Now repeat with the server listening on all container IPv4 interfaces:

```bash
docker run -d --rm --name cs320-listen \
  -p 127.0.0.1:8080:3000 \
  node:22-alpine \
  node -e 'require("http").createServer((req,res)=>res.end("hello")).listen(3000,"0.0.0.0")'
```

Try:

```bash
curl --max-time 3 http://127.0.0.1:8080
docker rm -f cs320-listen
```

**Question:** What changed inside the network namespace, and what stayed the same in the host port-publishing configuration?

If the observation differs, inspect Docker's network mode and forwarding arrangement rather than assuming the predicted behavior is universal.

## Experiment D — Main-process identity

Run a disposable container that displays process information:

```bash
docker run --rm --init alpine sh -c \
  'ps; echo "Current shell PID: $$"'
```

Compare with:

```bash
docker run --rm alpine sh -c \
  'ps; echo "Current shell PID: $$"'
```

The `--init` option inserts a small init process that can forward signals and reap children.

**Question:** Why might an additional init process be helpful even when a container contains only one main application?

## Experiment E — Investigate resource controls

Inside a Linux environment using cgroup v2, inspect the available interfaces:

```bash
cat /proc/self/cgroup
cat /sys/fs/cgroup/cgroup.controllers
```

Depending on the environment and mount arrangement, relevant cgroup files may include:

```text
cpu.max
cpu.stat
memory.current
memory.max
memory.events
pids.max
```

Do not assume every controller is enabled or that every file will appear at the same path in every container.

**Question:** Which interfaces describe resource accounting, which describe restrictions, and why might a container's results differ from host-level metrics?

## Practical completion criterion

You should now be able to explain why a process's apparent environment can differ from the host environment without assuming that the process has its own kernel.

You should also be able to identify which operating-system boundary to inspect when a container cannot reach a service, access a file, retain data, or shut down cleanly.

---

# Further Reading

Primary technical references:

1. Michael Kerrisk, *Linux manual pages — namespaces(7)*: https://man7.org/linux/man-pages/man7/namespaces.7.html
2. *Linux manual pages — pid_namespaces(7)*: https://man7.org/linux/man-pages/man7/pid_namespaces.7.html
3. *Linux Kernel Documentation — Control Group v2*: https://docs.kernel.org/admin-guide/cgroup-v2.html
4. *Docker Documentation — Port Publishing*: https://docs.docker.com/engine/network/port-publishing/
5. *Docker Documentation — Dockerfile Reference*: https://docs.docker.com/reference/dockerfile/
6. *Kubernetes Documentation — About cgroup v2*: https://kubernetes.io/docs/concepts/architecture/cgroups/

Related programme chapters:

- CS220-L04 — References, Garbage Collection, and Memory Leaks
- CS220-L06 — Managed Runtimes: Node.js, CPython, and the JVM
- SE340-L01 — Linux and the Server Environment
- SE340-L02 — Containers and Modern Deployment
- SE450-L06 — Security, Isolation, and Multi-Tenancy

The related chapters approach the same machinery from language-runtime, deployment, or platform-security perspectives. They are complements rather than prerequisites for this foundational lecture.

---

## Dense Cheatsheet — Interview Glance Card

```text
CS320-L01 — KERNEL, PROCESSES, CONTAINERS

THE EXECUTION MODEL
  Program       = instructions / executable description
  Process       = running execution environment + resources
  Thread        = schedulable execution context within process
  Kernel        = privileged OS core managing protected resources
  User mode     = restricted application execution
  System call   = controlled entry into kernel service

PROCESS STATE
  PID, virtual address space, threads, descriptors,
  credentials, working directory, environment,
  signal state, resource limits, parent/child relationships

PROCESS CREATION
  fork          = create child process with inherited state
  exec          = replace executing program image
  PID != executable identity
  Same program can run in many distinct processes

NAMESPACES = ISOLATE SELECTED VIEWS
  PID           = process identifier visibility
  Network       = interfaces, sockets, routing context
  Mount         = mount-point visibility
  User          = user/group ID mapping
  UTS           = hostname-related state
  IPC           = selected IPC resources
  Others        = cgroup namespace, time namespace

CGROUPS = RESOURCE ORGANIZATION AND CONTROL
  CPU           = scheduling capacity / quota / weight
  Memory        = accounted memory and restrictions
  PIDs          = task-count limits
  Other controllers may govern additional resources
  Host free capacity != unrestricted container capacity

CONTAINERS
  Ordinary Linux containers share host Linux kernel
  Container != VM with independent guest kernel
  Runtime assembles namespaces + cgroups + filesystem
  + credentials + capabilities + security controls
  Isolation is configuration-dependent

NETWORKING
  localhost = loopback in CURRENT network namespace
  127.0.0.1 binding != all interface binding
  0.0.0.0 = all local IPv4 interfaces in namespace
  Published host port != automatically reachable app
  Containers can intentionally share network namespaces
  Kubernetes Pod containers ordinarily share localhost

FILESYSTEMS
  Path visibility != permission
  Successful write != persistence after replacement
  Writable container layer may be disposable
  Durable data needs an appropriate storage contract

SECURITY
  UID 0 inside container != universally unrestricted host
  Capabilities / seccomp / namespaces / mounts matter
  Privileged mode and sensitive host mounts weaken isolation
  Container alone != arbitrary-untrusted-code sandbox guarantee

LIFECYCLE
  PID 1 = namespace init with special Linux behavior
  Container main process must receive/handle termination
  Shell form may interfere with signal forwarding
  Exec form often avoids unnecessary shell intermediary
  Child processes may need reaping
  SIGTERM = catchable termination request
  SIGKILL = uncatchable forced termination
  Graceful shutdown needs bounded drain and recovery logic
  Signal delivery != business transaction correctness

INCIDENT QUESTIONS
  Unreachable API?
    Check bind address, network namespace, published path
  Permission denied?
    Check credentials, mounts, file permissions, policies
  Disappearing file?
    Check writable layer and persistence arrangement
  Won't terminate?
    Check PID 1, signal routing, handlers, child processes
  Healthy host, unhealthy container?
    Check the relevant cgroup resource boundary

SENIOR MENTAL MODEL
  What is running?
  What can it see?
  What can it do and consume?
  How does it live and die?
```
