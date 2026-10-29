---
id: SE340-L01
course: SE340
title: "Linux and the Server Environment"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [ENG401-S03]
prev: null
next: SE340-L02
---











# SE340 — Linux, Cloud Infrastructure, and Delivery

## Lecture 01: Linux and the Server Environment

*What actually happens when your perfectly good application meets the operating system—and the operating system refuses to cooperate.*

---

## 1. The Server That Had Plenty of Resources

It's 14:37 on a perfectly ordinary Tuesday. Your company's Node.js API has been running without incidents for three months.

Suddenly, customers begin reporting failed requests. Some receive HTTP 500 responses, while others experience connection timeouts. The monitoring dashboard shows an increasing error rate, and several background workers have stopped processing jobs.

You connect to the production server and examine its resources.

```text
CPU usage:           12%
Memory usage:        43%
Disk usage:          28%
Network utilization: Low
```

Everything appears healthy.

You inspect the application logs and find:

```text
Error: EMFILE: too many open files
```

A background worker reports:

```text
Error: spawn /usr/bin/convert EAGAIN
```

Meanwhile, attempts to establish new database connections fail intermittently.

The machine has plenty of CPU capacity, available RAM, and disk space. Yet the application cannot reliably open files, create processes, or establish connections.

How can a computer have abundant resources and still refuse to perform basic operations?

The explanation lies in a distinction that developers sometimes overlook: **having available hardware capacity is not the same as having permission or capacity to consume a particular operating-system resource.**

A Linux process operates within a complex environment of resource limits, file descriptors, users, permissions, kernel-managed objects, process hierarchies, and network sockets.

Understanding that environment is the difference between treating a server as a mysterious box and being able to investigate what it is actually doing.

---

## 2. Your Application Is a Linux Process

From a developer's perspective, an application is source code, dependencies, configuration, and perhaps a deployment artifact.

From Linux's perspective, a running application is primarily one or more **processes**.

When you execute:

```bash
node dist/server.js
```

Linux does not understand that you are launching a sophisticated SaaS backend. It understands that a process must execute a program, receive access to certain resources, and participate in the operating system's scheduling and isolation mechanisms.

A process has several important properties:

- A process identifier, or PID.
- A virtual address space.
- One or more execution threads.
- Open file descriptors.
- User and group credentials.
- Environment variables.
- A current working directory.
- Resource limits.
- Signal-handling behavior.
- Relationships with parent and child processes.

These properties help determine what the application can do, independently of whether its business logic is correct.

### Process creation

On traditional Unix-like systems, process creation involves two important mechanisms.

`fork()` creates a new process derived from an existing process, initially inheriting much of its execution context. `execve()` replaces the currently executing program image with another executable.

A shell launching Node.js may use these mechanisms, or related optimized alternatives such as `posix_spawn()` depending on the implementation.

Conceptually:

```text
Shell Process
     │
     ├── Create child process
     │
     └── Execute Node.js program
                  │
                  ▼
             Node Process
                  │
                  ├── JavaScript runtime
                  ├── V8 heap
                  ├── Event loop
                  ├── Open sockets
                  └── Worker threads / thread pool
```

The Node.js runtime manages JavaScript execution and asynchronous operations, but the underlying process remains subject to Linux's rules.

When Node.js reads a file, opens a TCP connection, or creates a child process, it ultimately relies on operating-system facilities.

### System calls: crossing into the kernel

User applications generally cannot manipulate hardware or protected kernel structures directly. Instead, they request operations through **system calls**.

Common Linux system calls include:

| System call | Purpose |
|---|---|
| `openat()` | Open a file relative to a directory descriptor |
| `read()` / `write()` | Read or write data |
| `socket()` | Create a networking endpoint |
| `connect()` | Initiate a socket connection |
| `accept()` | Accept an incoming connection |
| `clone()` | Create a task or thread-like execution context |
| `execve()` | Execute a program |
| `mmap()` | Establish memory mappings |
| `epoll_wait()` | Wait for I/O readiness events |

Node.js hides much of this machinery behind convenient APIs.

For example:

```typescript
const content = await fs.promises.readFile(
  "/app/config.json",
  "utf8"
);
```

At a lower level, the runtime coordinates file opening, reading, and closing through operating-system interfaces, often using libuv's worker pool for ordinary filesystem operations.

The kernel checks whether the operation is permitted, allocates or accesses the relevant resources, and returns a result.

If something prevents the operation, the kernel reports an error. Node.js converts many such errors into familiar JavaScript exceptions carrying codes such as `EACCES`, `ENOENT`, `EMFILE`, or `ECONNREFUSED`.

Understanding these codes gives you clues about which operating-system mechanism rejected the request.

---

## 3. Processes, Threads, and Scheduling

A process is not necessarily a single stream of execution.

A Node.js process commonly contains multiple threads: the main JavaScript execution thread, V8 support threads, and threads used by libuv or other native components.

This matters when interpreting CPU utilization.

Suppose a server has eight logical CPUs. A single CPU-intensive JavaScript loop might occupy one logical CPU almost completely while the operating system reports approximately 12.5% overall CPU utilization.

The machine appears mostly idle, yet the JavaScript event loop is effectively blocked.

Other threads and other application instances may remain healthy, but the blocked event loop cannot promptly process ordinary callbacks.

### Investigating processes

A useful starting command is:

```bash
ps aux
```

It displays running processes with information such as their owners, CPU and memory usage, commands, and process identifiers.

To focus on Node.js:

```bash
ps aux | grep '[n]ode'
```

For an interactive view:

```bash
top
```

Or, if installed:

```bash
htop
```

These tools help identify resource-consuming processes and investigate whether activity is concentrated in particular tasks.

To inspect threads belonging to a process:

```bash
ps -L -p 1234 -o pid,tid,stat,pcpu,comm
```

Replace `1234` with the actual PID.

The distinction between PID and TID becomes relevant when diagnosing CPU-heavy native workers, thread pools, or multithreaded applications.

### What does process state mean?

Linux exposes process scheduling states, commonly represented by letters:

| State | Meaning |
|---|---|
| `R` | Running or runnable |
| `S` | Interruptible sleep, often waiting for an event |
| `D` | Uninterruptible sleep, commonly associated with kernel I/O waits |
| `T` | Stopped or being traced |
| `Z` | Zombie: terminated but not yet reaped by its parent |

A process in state `S` is not necessarily unhealthy. Most servers spend considerable time waiting for network activity, timers, and other events.

A process repeatedly observed in state `D` may warrant investigation into storage or filesystem operations, although the state alone does not establish the cause.

A zombie is particularly interesting: the process has already terminated, but its parent has not collected its exit status. It no longer executes application code, yet it retains a process-table entry until reaped.

Persistent zombie accumulation usually indicates a problem with how child processes are managed.

### Load average is not CPU percentage

Linux's load average describes a smoothed measure of demand from runnable tasks and tasks in uninterruptible sleep.

It is not simply a CPU utilization percentage.

For example, a machine may show high load averages because many processes are waiting in uninterruptible I/O states, even when its CPUs aren't especially busy.

Interpreting load averages requires knowing the available CPU count and examining the processes contributing to the load.

This is why a single metric rarely explains a production incident.

---

## 4. File Descriptors: The Resource Nobody Notices Until It Runs Out

Let's return to our mysterious production failure.

The application reports:

```text
EMFILE: too many open files
```

What counts as a file?

In Unix-like systems, the concept is broader than an ordinary file on disk.

Processes use **file descriptors** to reference open kernel-managed I/O objects, including:

- Regular files.
- TCP sockets.
- Unix domain sockets.
- Pipes.
- Terminal devices.
- Certain event-notification mechanisms.
- Various special devices.

A file descriptor is usually represented by a small nonnegative integer.

By convention, processes start with:

```text
0  → standard input
1  → standard output
2  → standard error
```

Additional descriptors are allocated as needed.

Imagine a Node.js backend maintaining 200 active network connections, several log files, pipes to child processes, and connections to external services.

These resources consume descriptors.

### Inspecting descriptors

Linux exposes information about processes through the virtual `/proc` filesystem.

For a particular PID:

```bash
ls -l /proc/1234/fd
```

You'll see symbolic links representing the process's open descriptors.

To count them:

```bash
ls -1 /proc/1234/fd | wc -l
```

This provides a useful approximate snapshot, although descriptors may open or close while you're inspecting them.

You can also use:

```bash
lsof -p 1234
```

`lsof` lists open files and other descriptor-backed resources associated with a process.

### The resource limit

Each process has resource limits, including a limit on the number of file descriptors it may hold.

Examine the current shell:

```bash
ulimit -n
```

But be careful: this reports the shell's limit, not necessarily the limit inherited by a production service.

For the actual application:

```bash
cat /proc/1234/limits
```

Look for:

```text
Max open files    1024    524288    files
```

These values are illustrative.

The first is the *soft limit*, which normally governs the process's current allowed usage. The second is the *hard limit*, which determines how far an unprivileged process may raise its soft limit.

The precise semantics are defined by Linux's resource-limit mechanisms, including `RLIMIT_NOFILE`.

### Why increasing the limit isn't always the solution

Suppose the application has a limit of 1,024 descriptors and crashes after several hours.

Increasing it to 65,536 may make the incident disappear temporarily.

But what if the application leaks descriptors by opening connections without closing them?

The new limit merely allows the leak to grow larger before failure.

A better investigation examines descriptor counts over time.

```text
09:00   120 descriptors
10:00   240 descriptors
11:00   510 descriptors
12:00   870 descriptors
12:30   1,020 descriptors
12:31   EMFILE
```

That pattern suggests progressive resource accumulation.

Now compare it with:

```text
09:00   120 descriptors
10:00   130 descriptors
11:00   125 descriptors
12:00   128 descriptors
12:30   1,020 descriptors
12:31   EMFILE
```

The second pattern suggests a sudden burst, perhaps a connection storm or an operation creating many concurrent resources.

Different patterns imply different causes and different remedies.

**A resource limit is often where a problem becomes visible, not where it originates.**

---

## 5. Memory: Available RAM Doesn't Guarantee Successful Allocation

Memory has similarly deceptive behavior.

A developer checks:

```bash
free -h
```

The output shows several gigabytes of available memory.

Nevertheless, a process suddenly disappears or reports allocation failures.

To understand this, distinguish several different concepts.

### Virtual memory versus physical memory

A Linux process operates within a virtual address space. Its memory mappings do not correspond directly to a permanently reserved, equally sized collection of physical RAM pages.

The kernel manages mappings, page allocation, shared memory, file-backed pages, and swapping according to its memory-management mechanisms.

This is why process memory metrics require interpretation.

`VIRT` commonly represents virtual address-space size, while `RES` or RSS refers to resident physical memory, though shared mappings complicate attribution.

A Node.js process may reserve a substantial virtual address range without actively occupying an equivalent amount of physical RAM.

### Linux uses memory for caching

Linux uses otherwise available RAM to cache filesystem data and improve I/O performance.

Consequently, the amount shown as simply *free* is often much smaller than the memory that could become available to applications.

The `available` estimate in `free` is usually more useful than interpreting low free memory as an imminent crisis.

A machine with little unused RAM may be perfectly healthy.

### Memory limits can exist below the host level

Processes may be constrained by mechanisms such as:

- Per-process resource limits.
- Cgroup memory limits.
- Container resource restrictions.
- Application-runtime heap limits.
- System-wide physical memory pressure.

A process can therefore exhaust its permitted memory while the host still has substantial free capacity.

This becomes especially relevant with containers, which we'll investigate next session.

### The OOM killer

When the kernel cannot satisfy memory requirements and recovery mechanisms are insufficient, it may invoke the out-of-memory killer to terminate selected processes.

A service that abruptly disappears may have been killed because of memory pressure rather than because JavaScript threw an exception.

System logs can provide evidence:

```bash
journalctl -k
```

On systems where permitted:

```bash
dmesg
```

Look for out-of-memory and killed-process messages.

Cgroup-level OOM events may also be visible through cgroup accounting or a service manager's diagnostics.

However, not every abrupt termination is an OOM kill, and logs aren't always available or retained.

An exit status commonly displayed as `137` may indicate termination by `SIGKILL`, because shells conventionally report signal termination using `128 + signal number`. It does not, by itself, prove an OOM event.

A human administrator or supervisor could have sent the same signal.

### Application memory versus system memory

A Node.js application has additional memory-management behavior inside the process.

For example:

```typescript
console.log(process.memoryUsage());
```

This reports fields including RSS, V8 heap usage, and external memory accounting.

Growing heap usage may indicate retained JavaScript objects. Growing RSS with comparatively stable heap usage may point toward native allocations, buffers, allocator behavior, or other process memory components.

The numbers are clues, not diagnoses.

A good investigation connects application metrics to operating-system behavior rather than assuming either view is sufficient.

---

## 6. The Filesystem: Paths, Permissions, and Surprising Failures

Consider an application configured to write generated invoices to:

```text
/var/lib/billing/invoices/
```

It works when launched manually by a developer but fails as a production service.

The logs report:

```text
EACCES: permission denied
```

The first instinct may be to change the directory permissions until the error disappears.

That is often the wrong approach.

### Users and groups

Linux assigns processes user and group credentials, commonly identified by numerical UIDs and GIDs.

Inspect your current identity:

```bash
id
```

Inspect a file:

```bash
ls -l /var/lib/billing
```

The output might resemble:

```text
drwxr-x---  billing billing  invoices
```

The owner has read, write, and execute permissions. Members of the owning group have read and execute permissions. Other users have no access.

For directories, the permission bits have special practical meanings:

- `r` allows listing directory entries.
- `w` allows modifying directory entries, subject to other rules.
- `x` allows traversing or searching the directory.

To create a file inside a directory, the process normally needs write and search permissions on that directory.

A process may therefore have permission to read a particular file but still be unable to reach it through an inaccessible parent directory.

### Why root is not the answer

Running the application as root often makes permission errors disappear.

It also grants the process far more authority than ordinary application behavior requires.

If the application is compromised, those privileges can expand the consequences dramatically.

A better approach is to run the service under a dedicated unprivileged account and give that account access only to the directories and resources it needs.

For example, a billing service might receive write access to its own state directory but not to unrelated application directories or system configuration.

Linux also supports access-control lists, capabilities, and additional security mechanisms beyond ordinary owner/group/mode bits.

The essential principle is **least privilege**: don't grant broad authority merely because precise permissions require a little more thought.

### Filesystems have multiple exhaustion conditions

A server may report plenty of free disk space while file creation fails.

Why?

A filesystem can run out of **inodes**, which represent filesystem objects such as files and directories.

Inspect disk blocks:

```bash
df -h
```

Inspect inode availability:

```bash
df -i
```

An application producing millions of tiny temporary files can exhaust available inodes before exhausting disk capacity.

Another interesting case occurs when a large log file is deleted while a process still holds it open.

The filename may disappear, but the filesystem's allocated storage can remain occupied until the final open reference is released.

You might then observe a puzzling difference between the space reported by `df` and the apparent file sizes counted by `du`.

```bash
du -sh /var/log
```

To investigate deleted but still-open files:

```bash
sudo lsof +L1
```

Permissions and visibility depend on the system.

This illustrates an important operating-system distinction: removing a directory entry is not necessarily equivalent to immediately releasing every resource associated with the underlying file.

---

## 7. Environment Variables and the Illusion of Identical Environments

A familiar deployment story begins with:

"It works when I run it manually."

The developer connects over SSH and starts:

```bash
node dist/server.js
```

Everything works.

Then systemd starts the same executable, and the application fails.

Both executions use the same source code and dependencies. Why do they behave differently?

Because a process inherits an **execution environment**, and that environment is not determined solely by the executable.

Relevant differences include:

- Environment variables.
- Working directory.
- User and group credentials.
- File permissions.
- Resource limits.
- Available executable paths.
- Shell initialization behavior.
- Network and filesystem namespaces.

### Environment variables

Inspect the current shell:

```bash
printenv
```

A Node.js application reads environment variables through:

```typescript
const port = Number(process.env.PORT ?? 3000);
```

But environment variables are inherited when a process is created. Changing a shell variable afterward does not retroactively modify an already-running service's environment.

Similarly, a service started by systemd does not automatically receive every variable defined in your interactive shell's `.bashrc` or `.profile`.

This explains many configuration mysteries.

### The current working directory

Consider:

```typescript
fs.readFileSync("./config/settings.json");
```

That relative path resolves against the process's current working directory, not automatically against the location of the JavaScript source file.

If the application is launched from a different directory, it may attempt to open the wrong path.

Inspect the working directory of a Linux process:

```bash
readlink /proc/1234/cwd
```

This is one reason production applications should make resource-path assumptions explicit.

### Environment variables are not a security vault

Secrets are often supplied through environment variables because doing so is convenient and avoids hardcoding them.

However, environment variables can be exposed through process inspection under appropriate permissions, diagnostic dumps, logging, inherited child environments, and operational tooling.

They should not be treated as inherently secret merely because they are outside the Git repository.

Secure deployments need deliberate secret distribution, access controls, rotation procedures, and careful handling of accidental exposure.

We'll explore this in depth during the security session.

---

## 8. Signals: How Linux Communicates With Processes

Suppose a deployment system needs to replace an old Node.js instance with a new version.

How does it ask the old process to stop?

On Linux, a common mechanism is a **signal**.

Signals are notifications delivered to processes or threads, often indicating events or requesting particular behavior.

Important examples include:

| Signal | Common meaning |
|---|---|
| `SIGTERM` | Request termination |
| `SIGINT` | Interrupt, commonly generated by Ctrl+C |
| `SIGKILL` | Force termination; cannot be caught or ignored |
| `SIGHUP` | Historically terminal hangup; sometimes used for reload conventions |
| `SIGUSR1` / `SIGUSR2` | Application-defined uses, with runtime-specific exceptions |
| `SIGCHLD` | Child process changed state |

The distinction between `SIGTERM` and `SIGKILL` is especially important.

`SIGTERM` allows an application to handle the request and perform cleanup. `SIGKILL` prevents application-level cleanup because the process cannot catch it.

### Graceful shutdown in Node.js

A minimal HTTP server might register:

```typescript
import http from "node:http";

const server = http.createServer((req, res) => {
  res.end("Hello");
});

server.listen(3000);

let shuttingDown = false;

process.on("SIGTERM", () => {
  if (shuttingDown) return;
  shuttingDown = true;

  console.log("Shutdown requested");

  server.close((error) => {
    if (error) {
      console.error(error);
      process.exitCode = 1;
    }
  });
});
```

Calling `server.close()` stops accepting new connections and closes the server after its applicable existing connections have finished. Exact connection behavior depends on the Node.js version and protocol handling.

A production application needs additional considerations:

- Stop accepting new work.
- Allow in-flight operations to complete within a reasonable deadline.
- Stop or transfer background work safely.
- Close database connections and other resources.
- Avoid leaving business operations in ambiguous states.
- Ensure the process eventually terminates.

A shutdown handler must not wait forever if a downstream dependency has become unresponsive.

A supervisor may eventually escalate termination if the configured shutdown deadline expires.

Also, registering a `SIGTERM` handler changes Node.js's default termination behavior on POSIX systems. The handler must actually arrange for the process to finish.

### Why not immediately call `process.exit()`?

Because `process.exit()` forces termination without waiting for outstanding asynchronous operations to complete.

Logs may remain unwritten, network operations may be interrupted, and cleanup promises may never settle.

Setting `process.exitCode` and allowing the event loop to drain is generally safer when graceful termination is feasible.

For durable background workers, successful shutdown also requires understanding which jobs must be retried or reclaimed after interruption.

The operating system can request termination; it cannot guarantee that your business workflow reaches a correct state.

---

## 9. systemd: Who Keeps the Application Alive?

Running an application manually through SSH is useful for experimentation.

It is not usually an adequate production deployment strategy.

If the shell session closes, the process may receive a hangup signal or otherwise lose its expected execution context, depending on how it was launched.

Production services need supervision, startup configuration, logging, and controlled restart behavior.

On many Linux distributions, **systemd** performs these responsibilities.

### A systemd service unit

Consider a Node.js API installed at `/opt/billing-api`.

A simplified unit file might look like:

```ini
# /etc/systemd/system/billing-api.service

[Unit]
Description=Billing API
After=network.target

[Service]
Type=simple
User=billing
Group=billing
WorkingDirectory=/opt/billing-api
Environment=NODE_ENV=production
ExecStart=/usr/bin/node /opt/billing-api/dist/server.js
Restart=on-failure
RestartSec=3
LimitNOFILE=4096
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

This configuration tells systemd which program to start, which user should run it, and how failures should be handled.

`Restart=on-failure` instructs systemd to restart the service after qualifying failure conditions, subject to restart-rate limiting and other service-manager rules.

`LimitNOFILE` configures the service's file-descriptor resource limit.

`TimeoutStopSec` influences how long systemd allows the service's stop sequence before escalating according to its termination configuration.

Notice that `After=network.target` specifies ordering relative to that target; it does not guarantee that every network dependency or external service is reachable.

If a service genuinely needs stronger network-online ordering, additional configuration and a properly enabled network-online mechanism may be necessary. Even then, an external dependency may fail later.

### Operating the service

After installing or editing the unit:

```bash
sudo systemctl daemon-reload
```

Start it:

```bash
sudo systemctl start billing-api
```

Check its status:

```bash
systemctl status billing-api
```

Enable automatic startup:

```bash
sudo systemctl enable billing-api
```

Follow logs:

```bash
journalctl -u billing-api -f
```

Inspect recent entries:

```bash
journalctl -u billing-api --since "30 minutes ago"
```

The journal is particularly useful because logs can be associated with service units and other metadata.

### Restarting is not recovering

Suppose a worker repeatedly crashes because it encounters a malformed message.

The service manager restarts it, the worker reads the same message, and it crashes again.

The result is a restart loop.

The supervisor is performing its responsibility correctly, but the application remains unhealthy.

Similarly, automatically restarting an API can restore service after a transient failure, yet it cannot repair lost transactions, corrupted files, or an unavailable database.

A supervisor provides process lifecycle management.

Application correctness and business recovery remain separate concerns.

---

## 10. Networking: Listening Isn't the Same as Being Reachable

Another familiar incident:

The Node.js application logs:

```text
Server listening on port 3000
```

A developer runs:

```bash
curl http://localhost:3000/health
```

It works.

Yet customers cannot connect.

A listening application is only one element of the networking path.

### Addresses and ports

A TCP server binds to a local address and port.

For example:

```typescript
server.listen(3000, "127.0.0.1");
```

This binds to the IPv4 loopback interface. Remote hosts cannot directly reach that listener through an external network interface.

Compare:

```typescript
server.listen(3000, "0.0.0.0");
```

This requests listening on all local IPv4 interfaces.

However, being bound to a network interface does not guarantee reachability. Firewalls, routing rules, cloud security groups, proxies, and network isolation may still block connections.

Inspect listeners with:

```bash
ss -ltnp
```

The flags mean:

- `-l`: listening sockets.
- `-t`: TCP sockets.
- `-n`: numerical addresses and ports.
- `-p`: associated processes, when permitted.

For a specific port:

```bash
ss -ltnp 'sport = :3000'
```

### Distinguishing failure categories

Suppose:

```bash
curl -v http://127.0.0.1:3000/health
```

returns `Connection refused`.

This commonly means no listener accepted the attempted connection at that address and port, or something actively rejected it.

A timeout suggests that packets or responses are not completing the connection in the expected period. The cause could involve routing, filtering, network failure, or an overloaded endpoint.

An HTTP 503 means something successfully handled enough of the HTTP exchange to return a service-unavailable response. That points to a different failure layer.

These distinctions are diagnostically important.

```text
Client
   │
   ▼
DNS Resolution
   │
   ▼
Network Routing / Firewall
   │
   ▼
Reverse Proxy / Load Balancer
   │
   ▼
Listening Socket
   │
   ▼
Application Request Handler
   │
   ▼
Database / External Services
```

A failure at each layer produces different evidence.

### Established connections and socket states

Inspect active TCP connections:

```bash
ss -tan
```

You'll encounter states such as `LISTEN`, `ESTAB`, and `TIME-WAIT`.

`TIME-WAIT` is part of TCP's normal connection lifecycle. Its presence alone does not indicate a leak.

However, excessive connection churn or poor connection reuse may create operational pressure involving descriptors, ephemeral ports, kernel socket resources, or downstream connection limits.

The correct response isn't to blindly modify obscure TCP kernel parameters.

First determine whether application connection-management behavior is appropriate.

---

## 11. SSH and Remote Administration

SSH is the standard secure remote-access mechanism on many Linux servers.

A typical connection:

```bash
ssh developer@example-server
```

SSH establishes an encrypted connection and authenticates the remote endpoint and user according to its configuration.

For production administration, public-key authentication is generally preferable to relying on reusable passwords alone, especially when supported by strong key protection and appropriate organizational access controls.

But the more important operational question is what happens **after** authentication.

An engineer with unrestricted root access can accidentally damage the environment as effectively as an attacker with the same privileges.

### Useful habits

Before modifying a production service, establish which host and user you are operating as:

```bash
hostname
whoami
pwd
```

Inspect the target service before changing it:

```bash
systemctl status billing-api
```

Prefer narrow, reversible changes over unexplained global configuration modifications.

For example, don't increase system-wide file descriptor limits because one service reports `EMFILE` without establishing whether the failure is caused by a leak or an inappropriate per-service limit.

Similarly, avoid restarting every service merely because one endpoint has become slow.

A restart can destroy valuable evidence, interrupt healthy work, and conceal the underlying cause.

**Production administration is an exercise in controlled intervention, not enthusiastic command execution.**

---

## 12. A Systematic Production Investigation

Let's return to our opening incident.

Customers receive errors. CPU and memory utilization look acceptable. The logs report `EMFILE`, and a worker occasionally reports `EAGAIN` when attempting to create child processes.

A mature investigation follows evidence rather than a favorite troubleshooting ritual.

### Step 1 — Establish the affected process

Find the relevant service and PID:

```bash
systemctl status booking-api
```

Or:

```bash
ps aux | grep '[n]ode'
```

Confirm whether the process is running, repeatedly restarting, or being replaced by a supervisor.

If the service is unstable, inspect recent logs before restarting it.

### Step 2 — Verify the actual descriptor limit

```bash
cat /proc/1234/limits
```

Suppose the soft open-file limit is 1,024.

Now inspect descriptor usage:

```bash
ls -1 /proc/1234/fd | wc -l
```

Suppose the process currently holds 1,019 descriptors.

We have established that descriptor exhaustion is a plausible immediate cause of the `EMFILE` errors.

But we still don't know why the process accumulated so many descriptors.

### Step 3 — Investigate descriptor composition

```bash
lsof -p 1234
```

And:

```bash
ss -tanp
```

Perhaps we discover that hundreds of connections point to the same external supplier API.

The application introduced a new HTTP client during the last deployment, and that client creates connections repeatedly without managing their lifecycle correctly.

The growing descriptor count explains why file operations and new connections begin failing even though CPU and memory remain healthy.

### Step 4 — Investigate process-creation failures separately

`EAGAIN` during process creation can arise from limits or unavailable resources, including process/task constraints.

Inspect relevant limits and task counts:

```bash
cat /proc/1234/limits
ps -eLf | wc -l
```

Also inspect the service's cgroup constraints where applicable.

An important possibility is that excessive thread or child-process creation has exhausted a task limit. On Linux, process-related limits can count threads as well as conventional processes.

But `EAGAIN` alone does not prove which constraint was reached.

The descriptor issue and process-creation issue may share a cause, or they may be separate failures occurring under the same workload.

Avoid inventing a single explanation merely because the symptoms appeared together.

### Step 5 — Apply a controlled mitigation

If descriptor exhaustion threatens the service, a restart might temporarily restore availability by releasing resources held by the old process.

But first consider user impact, in-flight operations, evidence preservation, and whether a replacement instance is available.

Increasing the descriptor limit might be appropriate as temporary capacity relief if the workload legitimately needs more connections.

Neither action should substitute for fixing the connection lifecycle if a leak is established.

### Step 6 — Establish prevention

Once the root cause is identified, introduce appropriate safeguards:

- Correct connection reuse and cleanup.
- Limits on concurrent outbound operations.
- Monitoring of open descriptor counts.
- Monitoring of process/task counts.
- Alerting on sustained growth toward relevant limits.
- Load tests that reproduce the failure pattern.
- A runbook describing how to investigate recurrence.

The incident has now produced more than a workaround.

It has improved the system's future diagnosability and resilience.

---

## 13. Practical Lab — Reproduce Resource Exhaustion Safely

This experiment intentionally triggers file-descriptor exhaustion **inside a disposable Node.js process**.

Run it on a local Linux machine, a Linux virtual machine, or WSL. Do not run it inside an existing production service or under a shared production workload.

### Part A — Create a descriptor exhaustion script

Save as `fd-lab.mjs`:

```javascript
import fs from "node:fs";

const descriptors = [];

try {
  for (let i = 0; i < 1000; i++) {
    const fd = fs.openSync("/dev/null", "r");
    descriptors.push(fd);
  }
} catch (error) {
  console.log("Allocation failed:");
  console.log(error.code, error.message);
}

console.log("Opened descriptors:", descriptors.length);
console.log("PID:", process.pid);

setInterval(() => {
  // Keep the process alive for inspection.
}, 1000);
```

Launch it in a shell with a deliberately reduced soft descriptor limit:

```bash
(ulimit -n 64; node fd-lab.mjs)
```

The parentheses create a subshell, so the limit change does not persist in your original shell.

You should eventually see an error resembling:

```text
EMFILE: too many open files
```

The exact number of successfully opened descriptors will vary because Node.js itself uses descriptors.

### Part B — Inspect the process

From another Linux terminal, locate the PID and inspect its limits:

```bash
cat /proc/<PID>/limits
```

Replace `<PID>` with the printed process ID.

Inspect open descriptors:

```bash
ls -l /proc/<PID>/fd
```

You may find that even inspection becomes somewhat awkward near exhaustion, because the application can no longer obtain additional descriptors for its own operations.

Observe that the process can remain alive with very low CPU usage while being unable to open another file.

The limitation is unrelated to raw computational capacity.

### Part C — Terminate the process

Send a termination request:

```bash
kill -TERM <PID>
```

Because this example doesn't install a custom signal handler, Node.js should terminate according to its default behavior.

The operating system then releases the descriptors owned by the terminated process.

### Part D — Investigate a real service configuration

On a Linux system using systemd, inspect a service you are allowed to examine:

```bash
systemctl show ssh.service -p MainPID -p User -p LimitNOFILE
```

The exact service name may vary by distribution.

Compare its configured descriptor limit with the limits shown in `/proc/<PID>/limits` for its running process.

If they differ, investigate whether you're inspecting the correct PID and whether inherited limits or service configuration account for the difference.

The purpose is to establish that a production process's environment must be investigated directly rather than inferred from an interactive shell.

### Optional extension — Make shutdown observable

Modify the lab script to handle `SIGTERM`:

```javascript
process.on("SIGTERM", () => {
  console.log("Closing descriptors");

  for (const fd of descriptors) {
    fs.closeSync(fd);
  }

  console.log("Cleanup completed");
  process.exitCode = 0;
});
```

Send the signal again and observe the difference.

This is a simple demonstration of orderly cleanup, not a complete model of graceful shutdown for a network server with active transactions.

---

## 14. Engineering and Interview Challenges

### Challenge 1 — The misleading CPU dashboard

A Node.js API runs on a machine with sixteen logical CPUs. Overall CPU utilization is 8%, but HTTP requests sometimes take fifteen seconds to complete.

What operating-system and runtime behavior could explain this? How would you investigate?

### Challenge 2 — The disappearing disk space

A Linux server's log directory originally contains 80 GB of logs.

An administrator deletes a 50 GB log file, but `df -h` reports almost no increase in available disk space.

What could explain this, and how would you verify it?

### Challenge 3 — The mysterious permission failure

An application works when started manually through SSH. When launched through systemd, it reports:

```text
EACCES: permission denied, open './data/cache.json'
```

The file exists and is readable by your SSH user.

What should you inspect before modifying permissions?

### Challenge 4 — The repeatedly dying worker

A background worker processing images disappears after several large files are uploaded.

The application contains no obvious unhandled exception. Its supervisor restarts it, after which the same problem eventually recurs.

How would you distinguish an application crash, an OOM kill, a resource-limit violation, and an external termination?

### Challenge 5 — The unreachable API

A Node.js API reports that it is listening on port 8080. Requests from the same server succeed, but requests from another machine time out.

Describe a systematic investigation that distinguishes binding problems, firewall problems, routing problems, and application-level failures.

---

## 15. Solutions and Discussion

### Challenge 1 — Investigate the event loop and thread-level utilization

Overall CPU utilization can hide saturation of an individual logical CPU.

A CPU-intensive JavaScript operation may monopolize Node.js's main event loop while most other logical CPUs remain idle. Alternatively, synchronous filesystem operations, excessive garbage collection, thread-pool contention, or a slow external dependency could explain the latency.

I'd inspect per-thread CPU usage, event-loop delay metrics, request traces, and application profiling data.

The critical question is whether the process is actively computing, blocked inside a synchronous operation, or waiting for an external resource.

### Challenge 2 — A deleted file may still be open

The file may have been unlinked from its directory while a logging process still holds an open descriptor referencing it.

Linux can retain the underlying storage until the last open reference is released.

I'd investigate with:

```bash
sudo lsof +L1
```

If the logging process retains the deleted file, a controlled log rotation or service restart may release the space.

I would not immediately restart every process on the machine, nor assume that deleting additional visible files will solve the discrepancy.

### Challenge 3 — Compare the execution environments

First, inspect the systemd unit's `User`, `Group`, and `WorkingDirectory` configuration.

Because the application uses a relative path, it may be resolving `./data/cache.json` against a different directory than expected.

Then inspect permissions along the entire path and the credentials under which the service runs.

The correct solution may be setting the working directory, configuring a dedicated writable state directory, or granting narrowly scoped permissions.

Changing everything to mode `777` is not an engineering solution.

### Challenge 4 — Gather termination evidence

I would inspect systemd status, recent journal entries, process exit status, kernel logs, and cgroup memory events where available.

An application crash may produce a JavaScript exception, a native crash signal, or other runtime evidence.

An OOM kill may leave kernel or cgroup records. A supervisor timeout or explicit `SIGKILL` may produce a similar visible exit status without involving memory exhaustion.

I would correlate termination timing with memory consumption, uploaded file sizes, native image-processing subprocesses, and configured resource limits.

Only then would I decide whether the remedy is memory optimization, workload concurrency limits, increased resources, or changes to process management.

### Challenge 5 — Follow the connection path

I'd begin by confirming the actual listener:

```bash
ss -ltnp 'sport = :8080'
```

If the application is bound only to `127.0.0.1`, remote requests cannot directly reach it through an external interface.

If it is bound appropriately, I'd test connectivity to the server's relevant interface address, inspect local firewall rules, verify routing, and examine any cloud firewall or security-group configuration.

I'd then distinguish TCP connection failures from HTTP responses and application timeouts.

A local successful request establishes that part of the application is functioning. It does not prove the external network path is working.

---

## Mental Model

When diagnosing a Linux-hosted application, think in layers:

1. **Process:** Is it running, blocked, restarting, or terminated?
2. **Identity:** Which user, group, and permissions govern its operations?
3. **Resources:** Are CPU, memory, descriptors, tasks, disk blocks, or inodes exhausted?
4. **Environment:** What configuration, working directory, and limits did the process inherit?
5. **Networking:** Where is it listening, and which network boundaries separate it from clients?
6. **Lifecycle:** Which supervisor controls startup, termination, logging, and recovery?
7. **Evidence:** What do `/proc`, system logs, process tools, and socket inspection actually establish?

**The central principle: An application doesn't run directly on hardware. It runs inside a collection of operating-system abstractions, permissions, and limits—and any one of them can become the bottleneck.**


---

## Next Lecture — SE340-L02: Containers and Modern Deployment

Continue in **SE340 — Linux, Cloud Infrastructure, and Delivery**.

## Further Reading

1. **Michael Kerrisk — [The Linux Programming Interface and Linux Manual Pages](https://man7.org/linux/man-pages/)**. Authoritative explanations of system calls, processes, filesystems, signals, resource limits, and kernel interfaces.

2. **Linux Manual — [Process Resource Limits](https://man7.org/linux/man-pages/man2/getrlimit.2.html)**. The mechanics of soft and hard limits, including `RLIMIT_NOFILE` and process-related constraints.

3. **Linux Manual — [The `/proc` Process Limits Interface](https://man7.org/linux/man-pages/man5/proc_pid_limits.5.html)**. How to inspect resource limits for individual Linux processes.

4. **systemd — [Service Unit Documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)**. Official reference for service execution, process supervision, restarts, and shutdown behavior.

5. **systemd — [journalctl](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html)**. Investigating logs from services and the operating system.

6. **Node.js — [Process API](https://nodejs.org/api/process.html)**. Signals, environment variables, process information, and runtime lifecycle behavior.

7. **Brendan Gregg — [Linux Performance](https://www.brendangregg.com/linuxperf.html)**. A detailed reference for performance investigation and Linux observability tools.

8. **Brian Ward — *How Linux Works, 3rd Edition***. An accessible, mechanism-oriented explanation of Linux processes, filesystems, devices, networking, and system administration.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE340-L01  LINUX / SERVER — INTERVIEW GLANCE CARD

CORE MODEL
  Hardware free ≠ OS permission/capacity for a resource
  App runs as process(es) under limits, FDs, creds, sockets
  Syscalls cross into kernel; Node maps errors (EMFILE, EACCES…)

PROCESS / SCHEDULING
  PID, address space, threads, FDs, UID/GID, env, cwd, limits, signals
  fork/exec (or spawn); Node = event loop + libuv pool + threads
  One hot JS loop can stall requests while host CPU % looks low
  States: R runnable · S sleep · D uninterruptible I/O · Z zombie
  Load avg ≠ CPU % (includes uninterruptible waiters)

FILE DESCRIPTORS
  Files, TCP/Unix sockets, pipes, devices…
  EMFILE = too many open; inspect /proc/PID/fd, lsof, limits
  Soft vs hard RLIMIT_NOFILE; ulimit -n = shell, not service
  Raising limit ≠ fix leak; watch growth pattern (leak vs burst)

MEMORY
  VIRT vs RES; Linux cache uses “free” RAM — prefer available
  Limits: process, cgroup, container, heap, host pressure
  OOM killer; exit 137 = SIGKILL hint, not proof of OOM
  process.memoryUsage() clues (heap vs RSS)

FILESYSTEM / PERMS
  UID/GID; dir x = traverse; least privilege > run as root
  Inode exhaustion vs block space (df -h vs df -i)
  Deleted-but-open file still holds space (lsof +L1)

ENVIRONMENT
  Same binary ≠ same env: vars, cwd, user, limits, PATH
  Relative paths use process cwd (readlink /proc/PID/cwd)
  Env vars not a security vault

SIGNALS
  SIGTERM handleable cleanup; SIGKILL cannot catch
  Graceful: stop accept → drain with deadline → close resources
  process.exit() abrupts async work; prefer exitCode + drain

SYSTEMD
  Unit: User, WorkingDirectory, ExecStart, Restart, LimitNOFILE,
  TimeoutStopSec; After= ≠ dependency healthy
  journalctl -u; restart ≠ recover business correctness
  Restart loops on poison messages

NETWORKING
  Listen ≠ reachable; 127.0.0.1 vs 0.0.0.0
  ss -ltnp; refuse ≠ timeout ≠ HTTP 503 (different layers)
  TIME-WAIT normal; don't blind-tune kernel first

INVESTIGATION LAYERS
  Process → identity → resources → environment → network
  → supervisor → evidence (/proc, logs, sockets)

SENIOR LINE: App doesn't run on bare metal — it runs inside OS
             abstractions, permissions, and limits.
```

---


