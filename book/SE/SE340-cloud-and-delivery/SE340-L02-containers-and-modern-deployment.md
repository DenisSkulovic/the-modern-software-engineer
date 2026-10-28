---
id: SE340-L02
course: SE340
title: "Containers and Modern Deployment"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [ENG401-S04]
prev: SE340-L01
next: SE340-L03
---







# SE340 — Linux, Cloud Infrastructure, and Delivery

## Lecture 02: Containers and Modern Deployment

*How Linux learned to pretend that a process has its own computer—and why that illusion transformed software deployment.*

---

## 1. The Application That Forgot Where It Was

Your company has developed a Node.js document-processing service. It accepts uploaded PDFs, extracts information, stores metadata in PostgreSQL, and saves generated files to disk.

On your development machine, everything works beautifully.

The application starts, connects to PostgreSQL, processes documents, and responds to API requests. Its automated tests pass, and the deployment pipeline successfully builds a Docker image.

Then the application starts inside its container.

The first error appears almost immediately:

```text
ECONNREFUSED 127.0.0.1:5432
```

The database is running. You can connect to it from your development machine without difficulty.

After modifying the database connection configuration, the application starts processing documents. Then another error appears:

```text
EACCES: permission denied, mkdir '/app/uploads'
```

You fix the permissions, restart the container, and successfully upload a document.

A few minutes later, you recreate the container during a deployment.

The uploaded document has vanished.

Three failures, three apparently unrelated causes, and one underlying theme: **the application was designed with assumptions about its execution environment that stopped being true inside a container.**

What exactly changed?

Did Docker create a miniature Linux computer? Did the application receive its own operating system? Where did its files go? Why did `localhost` suddenly refer to something different?

And perhaps the strangest question: if containers are isolated environments, why can you see their processes running directly on the host?

To answer these questions, we need to understand what a container actually is.

---

## 2. The Problem Containers Were Created to Solve

Before containerization became commonplace, deploying applications often meant preparing individual machines.

Imagine three services:

- A Node.js application requiring a particular runtime and native dependencies.
- A Java application requiring a specific JDK.
- A Python processing service depending on particular system libraries.

Each service expects its environment to contain compatible versions of its dependencies.

Installing everything on one machine may produce conflicts. Installing the services on separate machines wastes resources and increases administration.

Worse, developers and production servers may have different operating-system libraries, configuration files, environment variables, filesystem layouts, and permissions.

The resulting failures gave us the timeless engineering masterpiece:

"It works on my machine."

### Virtual machines offered one solution

A virtual machine provides an environment containing a guest operating system, supported by a hypervisor that virtualizes hardware resources.

Conceptually:

```text
Physical Hardware
        │
        ▼
Host OS / Hypervisor
        │
   ┌────┴────┐
   ▼         ▼
Virtual    Virtual
Machine A  Machine B
   │         │
Guest OS   Guest OS
   │         │
App A      App B
```

Virtual machines offer substantial isolation and independent operating-system environments.

However, each conventional VM includes a guest kernel and associated operating-system components. This introduces resource consumption, startup overhead, patching responsibilities, and additional operational complexity.

Containers approach the problem differently.

### Containers share the kernel

A Linux container runs ordinary Linux processes using the host Linux kernel, while restricting their view of the surrounding system.

```text
             Physical Hardware
                     │
                 Linux Kernel
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   Container A   Container B   Container C
       │             │             │
    Node.js       Java App      PostgreSQL
       │             │             │
   User-space     User-space     User-space
   libraries      libraries      libraries
```

Each container can have its own filesystem view, process namespace, network interfaces, and resource constraints.

But it does not ordinarily contain an independent Linux kernel.

This explains much of containerization's efficiency: running additional containers does not require booting additional guest operating systems.

The distinction is especially relevant on Windows and macOS. Docker Desktop commonly runs Linux containers inside a managed Linux virtual machine, because those operating systems do not natively provide the Linux kernel interfaces required by ordinary Linux containers.

From the application's perspective, it runs in a Linux environment. But the underlying Linux kernel belongs to that VM rather than directly to Windows or macOS.

**A container is an isolated execution environment for processes, not a complete virtual computer.**

---

## 3. Namespaces: Giving Processes Different Views of Reality

How does Linux make one process believe it exists inside a separate environment?

A major part of the answer is **namespaces**.

Namespaces allow groups of processes to see different representations of certain kernel-managed resources.

Consider process identifiers.

On an ordinary Linux host, a running Node.js application might have PID 18427. But inside a PID namespace, that same process might appear as PID 1.

The kernel hasn't created two processes. It is exposing different identifier mappings in different contexts.

### Important namespace types

| Namespace | What it isolates |
|---|---|
| PID | Process identifier visibility |
| Network | Network interfaces, routing tables, ports, and related network state |
| Mount | Filesystem mount-point views |
| UTS | Hostname and domain-name information |
| IPC | Certain interprocess communication resources |
| User | User and group identifier mappings and associated privileges |
| Cgroup | Visibility of parts of the cgroup hierarchy |
| Time | Selected time-related kernel interfaces |

Not every container configuration uses every namespace in exactly the same way.

Some namespaces can also be shared intentionally, and their isolation properties depend on the runtime configuration.

### PID namespaces

Imagine starting a container:

```bash
docker run --rm -it debian:stable-slim bash
```

Inside the container:

```bash
ps aux
```

Depending on the image, you may need to install process-inspection utilities first.

You'll typically see only a small collection of processes belonging to that container's PID namespace.

Meanwhile, the host can see those processes as ordinary Linux tasks with host-level PIDs.

This is an important asymmetry.

The containerized application sees a restricted world. The host retains broader visibility and control.

### Network namespaces

A network namespace provides an isolated network stack.

Two containers can each run a service listening on port 3000 without conflicting, because their listening sockets belong to different network namespaces.

```text
Container A                   Container B

127.0.0.1:3000                127.0.0.1:3000
     │                             │
  Node API                      Node API
```

Each container's `localhost` refers to its own network namespace.

This explains our opening database failure.

If PostgreSQL is running in another container, then:

```text
localhost:5432
```

inside the Node.js container ordinarily refers to port 5432 inside the Node.js container, not the database container.

The application is contacting the wrong machine—or, more precisely, the wrong network namespace.

We'll return to the correct solution shortly.

### Mount namespaces

A mount namespace controls which filesystem mounts processes can see.

A container might see:

```text
/
├── app/
├── bin/
├── etc/
├── usr/
└── var/
```

This filesystem view does not imply that these directories occupy an entirely separate physical disk.

The container runtime constructs the view using image filesystems, mounts, and other filesystem mechanisms.

The application sees a coherent root filesystem even though the host may store its contents through layers and backing storage elsewhere.

Namespaces are therefore primarily about **visibility and isolation of particular resources**.

They don't, by themselves, control how much CPU or memory a process may consume.

For that, Linux uses another mechanism.

---

## 4. Control Groups: Isolation Without Resource Limits Isn't Enough

Suppose we start ten containers on a powerful server.

Each has its own process and network namespaces. Their filesystems appear separate, and their applications cannot normally see one another's processes.

But one container contains a faulty background worker:

```typescript
while (true) {
  performExpensiveCalculation();
}
```

Or perhaps it continuously allocates memory until it exhausts the machine.

Namespaces don't inherently prevent the application from consuming excessive shared computing resources.

That's where **control groups**, usually abbreviated *cgroups*, enter the picture.

### What cgroups do

Linux cgroups organize processes into resource-management hierarchies.

Depending on the available controllers and configuration, they support mechanisms for:

- CPU accounting and bandwidth limits.
- Memory accounting and limits.
- Process and thread count limits.
- I/O accounting and control.
- Other resource-specific management policies.

Docker uses these facilities to constrain container workloads.

For example:

```bash
docker run \
  --memory=512m \
  --cpus=1.5 \
  --pids-limit=100 \
  my-api
```

This configures several independent limits.

The memory limit restricts the container's accounted memory consumption according to the kernel's cgroup memory controls.

The CPU configuration constrains CPU bandwidth. It does not necessarily mean the container is permanently assigned exactly 1.5 physical CPU cores.

The PID limit restricts the number of tasks within the relevant cgroup, helping contain excessive process or thread creation.

### CPU throttling

Suppose a container has enough work to consume four CPU cores continuously, but its configured CPU quota permits only the equivalent of one core over the quota period.

The kernel can throttle its execution once the permitted CPU time has been consumed.

The application may then experience increased latency even though the physical host has idle CPU capacity.

This is another example of the lesson from SE340-L01: resource availability must be evaluated within the process's actual constraints.

Host CPU usage alone may be misleading.

### Memory limits and OOM events

If a container exceeds its memory constraints and the kernel cannot reclaim enough memory, the workload may experience an out-of-memory kill.

A container that exits with code 137 may have received `SIGKILL`, potentially from an OOM event.

But exit code 137 alone doesn't establish the cause.

You should inspect container state, kernel or cgroup memory events, and relevant runtime logs.

```bash
docker inspect my-api
```

For a running workload:

```bash
docker stats
```

These commands provide useful information, but they don't replace investigation of application memory behavior.

A container with insufficient memory may fail despite abundant host RAM. A container with an overly generous memory limit can still threaten its neighbors through resource contention.

**Namespaces control aspects of what a process can see. Cgroups control aspects of what a process can consume.**

Together, they form much of the operating-system foundation for Linux containers.

---

## 5. Docker: The Machinery Around Containers

Containers existed conceptually before Docker became popular.

Docker's major contribution was to make container packaging, distribution, construction, and execution significantly more approachable and standardized.

A typical Docker environment involves several components:

```text
Docker CLI
    │
    ▼
Docker Engine / Daemon
    │
    ├── Image Management
    ├── Network Management
    ├── Volume Management
    │
    ▼
Container Runtime Infrastructure
    │
    ▼
Linux Kernel
    ├── Namespaces
    ├── Cgroups
    ├── Filesystems
    └── Networking
```

Modern Docker Engine uses components such as containerd and OCI-compatible runtimes to manage container execution.

The exact internal division of responsibilities can evolve, but the distinction between high-level container management and low-level process isolation remains important.

The Docker daemon is also a privileged operational component in common configurations.

Access to its control socket may effectively grant very broad authority over the host, which has serious security consequences.

Docker is not simply a program that executes your Node.js application. It manages the environment in which that application executes.

---

## 6. Images and Containers: Blueprint Versus Execution

One of the most important conceptual distinctions is between a **container image** and a **running container**.

An image is a packaged filesystem and configuration artifact describing an application execution environment.

A container is a runtime instance created from an image, with process state and writable storage associated with that instance.

A useful analogy is executable program versus running process.

One program can create many processes. Likewise, one image can create many containers.

```text
              Image: my-api:v1
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       Container A Container B Container C
          │          │          │
        PID 101     PID 205     PID 319
```

All three containers begin from the same image contents, but their runtime state is independent.

### Image layers

Docker images commonly use layered filesystem representations.

Consider:

```dockerfile
FROM node:24-bookworm-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

CMD ["node", "server.js"]
```

The build system constructs an image using filesystem changes and image metadata derived from the Dockerfile.

Conceptually:

```text
Base Node.js image
        │
        ▼
Application dependencies
        │
        ▼
Application source
        │
        ▼
Image configuration
```

Layers enable content reuse and efficient caching.

If the application source changes but `package.json` and its lockfile remain unchanged, the dependency-installation step may be reused from cache.

This is one reason Dockerfile instruction ordering matters.

### The writable container layer

Images are treated as immutable inputs. When a container runs, the runtime ordinarily provides a writable layer over the image's filesystem.

The application can create and modify files inside that container's writable view.

But those modifications do not change the original image.

If the container is removed and recreated from the image, its previous writable-layer changes are not automatically transferred.

Stopping and restarting the same existing container is different: its writable state normally remains until that container is removed.

This distinction explains why files may survive a restart but disappear during a deployment that recreates containers.

### Copy-on-write

Layered container filesystems often use copy-on-write behavior.

When a process modifies a file originating from a lower read-only image layer, the storage driver can arrange for a modified copy to exist in the container's writable layer.

The original image remains unchanged.

This is efficient for packaging and distributing application environments, but writable container layers are not a reliable substitute for deliberate persistent-data storage.

For application state that must survive container replacement, we need volumes or external storage.

---

## 7. Building a Production-Oriented Node.js Image

Let's create a more substantial Dockerfile for a TypeScript backend.

Assume the project contains:

```text
project/
├── src/
├── package.json
├── package-lock.json
├── tsconfig.json
└── Dockerfile
```

Its `npm run build` command compiles the application into `dist/`, and the entry point is `dist/server.js`.

We want an image that installs dependencies reproducibly, compiles TypeScript, avoids bundling development tools into the runtime environment, and runs without root privileges.

### A multi-stage Dockerfile

```dockerfile
# syntax=docker/dockerfile:1

# Stage 1: Compile the application
FROM node:24-bookworm-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY tsconfig.json ./
COPY src ./src

RUN npm run build


# Stage 2: Install runtime dependencies
FROM node:24-bookworm-slim AS production-deps

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force


# Stage 3: Runtime image
FROM node:24-bookworm-slim AS runtime

ENV NODE_ENV=production

WORKDIR /app

COPY --from=production-deps \
  --chown=node:node /app/node_modules ./node_modules

COPY --from=build \
  --chown=node:node /app/dist ./dist

COPY --chown=node:node package.json ./

USER node

EXPOSE 3000

CMD ["node", "dist/server.js"]
```

This is a practical starting point, not a universally perfect Dockerfile. Projects using generated ORM clients, native binaries, private package registries, workspaces, or runtime assets may require additional build steps.

Let's investigate the design choices.

### Why multi-stage builds?

The build stage needs TypeScript, development dependencies, and compilation tooling.

The runtime stage generally needs only compiled JavaScript, production dependencies, and the Node.js runtime.

By separating these responsibilities, we avoid carrying much of the build toolchain into the final image.

This usually reduces image size and attack surface.

There is also an operational benefit: fewer unnecessary components are present in the deployed environment.

### Why `npm ci`?

Unlike a normal dependency installation intended for interactive development, `npm ci` uses an existing lockfile and requires it to be consistent with the package manifest.

It is suited to automated builds because it rejects mismatched dependency definitions rather than silently updating the lockfile.

However, a lockfile does not eliminate every source of nondeterminism. Native compilation, package lifecycle scripts, external downloads, base image changes, and build-platform differences can still affect the result.

### Why copy dependencies before source code?

Docker's build cache can reuse expensive dependency installation when only application code changes.

If we copied all source files before installing dependencies, many ordinary code modifications would invalidate that earlier layer and trigger unnecessary installation work.

For very large projects, BuildKit cache mounts can further improve dependency installation performance.

### Why `USER node`?

The official Node.js image provides a non-root user.

Running the application under that account limits some of the authority available to a compromised application process.

However, this does not automatically establish strong isolation. Additional permissions, mounts, Linux capabilities, runtime privileges, and daemon configuration still matter.

It also means runtime directories must be writable by the selected user.

If the application tries to create `/app/uploads` without appropriate permissions, it may fail exactly as in our opening incident.

### Why use an explicit Node.js major version?

A tag such as `node:24-bookworm-slim` makes the intended major runtime and Linux distribution family clearer than an unqualified `node:latest`.

However, tags can still change when publishers release updates.

For stronger artifact reproducibility, production pipelines may pin image digests, verify provenance, scan dependencies, and apply a deliberate base-image update policy.

Pinning forever is not a security strategy either. An old, perfectly reproducible image may contain well-known vulnerabilities.

The objective is controlled updates, not permanent stagnation.

### Don't forget `.dockerignore`

The Docker build context should exclude unnecessary and sensitive files.

For example:

```gitignore
node_modules
dist
.git
.env
.env.*
coverage
*.log
```

This prevents irrelevant local material from being sent into the build context and accidentally copied into images.

Be careful with broad ignore rules if your application intentionally requires a particular file.

Also, `.dockerignore` is not a substitute for secure secret handling.

A secret copied into an earlier build layer may remain recoverable from that layer even if a later instruction deletes it. Build-time secrets should use appropriate secret-mount mechanisms rather than ordinary `COPY`, `ARG`, or image-baked environment variables.

---

## 8. Container Networking: Why Localhost Betrays You

Let's return to our Node.js and PostgreSQL example.

On your development machine, the backend might connect to:

```text
postgres://localhost:5432/app
```

But when Node.js and PostgreSQL run in separate containers, they occupy distinct network namespaces.

Each has its own loopback interface.

```text
Host Computer
    │
    ├── Node Container
    │     ├── localhost
    │     └── API :3000
    │
    └── PostgreSQL Container
          ├── localhost
          └── Database :5432
```

Inside the Node container, `localhost:5432` does not refer to PostgreSQL in the other container.

We need a network connecting them.

### Docker bridge networking

Docker commonly connects containers through bridge networks.

Within a Docker Compose project, services ordinarily share a default network and can resolve one another by service name.

For example:

```text
Node Container ─── Docker Network ─── PostgreSQL Container
     │                                      │
     └────────── db:5432 ──────────────────┘
```

The backend can connect using:

```text
postgres://app:password@db:5432/app
```

Here `db` is the Compose service name.

Docker's internal service discovery resolves that name to the appropriate network endpoint.

This is much more reliable than hardcoding container IP addresses, which can change when containers are recreated.

### Port publishing

Suppose your application listens on port 3000 inside the container.

You execute:

```bash
docker run -p 8080:3000 my-api
```

The mapping means:

```text
Host port 8080 → Container port 3000
```

A request to the host's published port can be forwarded to the container's listener, subject to address binding, platform behavior, and firewall rules.

The direction matters.

`-p 8080:3000` does not mean the application should listen on port 8080 inside the container.

For local development, a safer binding may be:

```bash
docker run -p 127.0.0.1:8080:3000 my-api
```

This restricts publication to the host's loopback address rather than deliberately exposing the port on all host interfaces.

Also remember that:

```dockerfile
EXPOSE 3000
```

is primarily image metadata documenting an intended port.

It does not publish that port to the host.

### Listening addresses matter

If the Node.js server explicitly binds only to:

```typescript
server.listen(3000, "127.0.0.1");
```

it may be unreachable through the container's network interface even when the port is published.

A common containerized configuration is:

```typescript
server.listen(3000, "0.0.0.0");
```

The application listens on available IPv4 interfaces inside its network namespace.

Docker then controls how the service is exposed beyond that namespace.

This is an important separation: **application binding, container networking, and external network exposure are different configuration layers.**

---

## 9. Docker Compose: A Small Multi-Service Environment

Individual containers are useful, but real applications often require several cooperating processes.

For our document-processing service:

- Node.js handles HTTP requests.
- PostgreSQL stores document metadata.
- Redis might coordinate background jobs.
- A separate worker executes processing tasks.

Docker Compose provides a declarative way to define and operate such a collection.

Here is a simplified development configuration:

```yaml
services:
  api:
    build: .
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      NODE_ENV: production
      DATABASE_URL: postgres://app:devpassword@db:5432/app
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:17
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: devpassword
      POSTGRES_DB: app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  postgres_data:
```

The password is deliberately a local-development placeholder. Production credentials should not be committed in plaintext configuration.

Start the environment:

```bash
docker compose up -d --build
```

Inspect it:

```bash
docker compose ps
```

Follow logs:

```bash
docker compose logs -f api
```

Compose creates the required containers, networking, and named volume.

The API can reach PostgreSQL through `db:5432` without publishing PostgreSQL to the host.

### Does `depends_on` solve startup ordering?

Partially.

With the `service_healthy` condition, Compose waits for the database service's configured health check to report healthy before starting the dependent service.

But this is not a guarantee that the database will remain available.

It also does not guarantee that every application-specific requirement—such as completed database migrations—is satisfied.

Your API still needs sensible connection retries, timeouts, and recovery behavior.

A database can disappear five minutes after startup. Successful initialization is not a permanent reliability guarantee.

### Why is PostgreSQL using a volume?

Without deliberate persistent storage, PostgreSQL data written into a container's writable layer can disappear when that container is removed and replaced.

The named volume:

```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
```

provides storage with a lifecycle separate from the individual database container.

Recreating the database container can preserve its stored data as long as the volume remains intact and appropriately mounted.

However, persistent storage is not the same thing as backup.

If an application corrupts its database, the volume faithfully preserves the corruption. If the underlying storage fails, the volume may disappear with it.

A production database still requires appropriate backup and recovery arrangements.

---

## 10. Volumes, Bind Mounts, and Disposable Storage

Container storage deserves a more precise distinction because mistakes here can destroy user data.

There are three common categories to understand.

### Container writable layers

These hold changes made to the container's own filesystem.

They are convenient for temporary runtime state but shouldn't be treated as durable storage across container replacement.

### Named volumes

Named volumes are managed by Docker.

They're useful for persistent application data that must survive container recreation, such as local development databases.

Their lifecycle is separate from that of individual containers, though administrators can still delete them.

### Bind mounts

A bind mount maps a specific host path into a container:

```bash
docker run \
  -v "$PWD/uploads:/app/uploads" \
  my-api
```

The application sees `/app/uploads`, while the underlying data is stored in the selected host directory.

Bind mounts are convenient for development and certain host-integrated workloads.

But they expose host filesystem content to the container according to the mount's permissions and configuration.

A writable bind mount therefore expands the consequences of a compromised or buggy application.

### The hidden mount behavior

Suppose the image already contains:

```text
/app/config/default.json
```

Now a host directory is mounted over `/app/config`.

The original image directory's contents are hidden at that mount point while the mount is active.

Developers sometimes interpret this as Docker mysteriously deleting files. The files remain in the image, but the mount changes the filesystem view presented to the application.

This is another direct consequence of Linux mount behavior.

### Where should production documents live?

For a production document-processing SaaS, storing uploaded customer files in a container's writable layer is usually a poor choice.

A managed object store such as S3 may offer better durability, lifecycle management, access controls, and compatibility with horizontally scaled application instances.

A local volume can still be appropriate for temporary processing, caching, or workloads with particular performance requirements.

The correct choice depends on durability, sharing, latency, compliance, and operational needs.

Don't confuse container persistence with data architecture.

---

## 11. Processes, Signals, and the PID 1 Problem

In SE340-L01, we discussed Linux signals and graceful shutdown.

Containers introduce an important variation: a container's main process may become **PID 1 inside its PID namespace**.

That process has special responsibilities and signal-related behavior.

In particular, PID 1 must properly handle child-process reaping, and Linux treats certain default signal actions differently for namespace init processes.

This can surprise applications that were originally developed as ordinary child processes.

### The importance of exec-form commands

Consider:

```dockerfile
CMD node dist/server.js
```

This is shell form.

Depending on the image and shell behavior, Docker may execute the command through a shell process:

```text
PID 1: /bin/sh
          │
          ▼
        node
```

Signals sent to the container's main process may not be forwarded to Node.js as expected.

Now compare:

```dockerfile
CMD ["node", "dist/server.js"]
```

This is exec form.

Node.js becomes the container's main process directly.

Its signal handlers can receive Docker's stop signal without relying on an intermediate shell to forward it.

### Docker stop behavior

When you execute:

```bash
docker stop my-api
```

Docker requests termination using the configured stop signal, ordinarily `SIGTERM` for Linux containers, and waits for a grace period.

If the process has not exited after that period, Docker normally escalates to `SIGKILL`.

Your Node.js service should respond to termination by stopping new work, handling in-flight requests, and releasing resources within the available deadline.

Background workers must also avoid acknowledging jobs prematurely or leaving unrecoverable intermediate states.

### Should every container contain an init system?

Not necessarily.

Many containers work perfectly well with one application process.

But applications that create child processes may need proper child reaping.

Docker provides an `--init` option that introduces a small init process to help handle signal forwarding and zombie reaping.

This can be useful for workloads that spawn subprocesses, such as document converters or image-processing utilities.

It doesn't replace correct application shutdown logic.

Containers do not exempt software from process lifecycle management. They make that lifecycle more explicit.

---

## 12. Container Security: Isolation Is Not Absolute

By now, containers sound rather impressive.

They isolate process visibility, networking, filesystem views, and resource consumption. They package application dependencies and support reproducible deployments.

So can we safely run arbitrary hostile code inside a container?

Not automatically.

**Container isolation is a security boundary, but it is not equivalent to a dedicated virtual machine or a guarantee against escape.**

Containers ordinarily share the host kernel. A vulnerability in an exposed kernel interface or a dangerous runtime configuration can undermine isolation.

The Docker daemon and its management interfaces also become sensitive security components.

### Root inside a container

A container process may run as UID 0, traditionally called root.

What does that mean?

Without user-namespace remapping, container root can correspond to UID 0 on the host, although Linux capabilities, namespaces, mounts, and other restrictions limit its effective authority.

With user namespaces, container UIDs can map to different, less-privileged host UIDs.

Docker also supports rootless operation, which runs the daemon and containers without ordinary host-root privileges, subject to platform requirements and limitations.

The exact security model depends on configuration.

Running an application as an unprivileged user is a useful defense, but not a complete security solution.

### Dangerous configurations

Several patterns deserve particular suspicion:

```bash
docker run --privileged ...
```

Privileged containers receive substantially expanded access to host capabilities and devices.

Similarly:

```bash
docker run \
  -v /var/run/docker.sock:/var/run/docker.sock \
  ...
```

Mounting the Docker control socket into a container can effectively allow that container to control the Docker daemon.

In a common rootful Docker configuration, this may amount to broad host-level authority.

Using containers does not make such configurations safe.

### Practical hardening

Production container security commonly involves:

- Running application processes as non-root users.
- Avoiding privileged containers.
- Limiting Linux capabilities.
- Restricting filesystem and network access.
- Using seccomp and other kernel security mechanisms.
- Making filesystems read-only where feasible.
- Managing secrets securely.
- Updating base images and dependencies.
- Scanning images for known vulnerabilities.
- Restricting access to container-management APIs.
- Applying resource limits.

For example:

```bash
docker run \
  --read-only \
  --tmpfs /tmp \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  my-api
```

This configuration restricts several capabilities, but it may not work unchanged for every application.

A program that legitimately writes to another location or requires a particular capability will need deliberate configuration.

Security controls should be tested against actual application behavior rather than copied blindly from a checklist.

---

## 13. Containers Improve Reproducibility, Not Universal Portability

A frequent claim is that containers allow software to run identically everywhere.

This is directionally useful but technically too strong.

A Docker image bundles much of the application's user-space environment, reducing differences between development, testing, and production.

However, it does not eliminate all environmental dependencies.

### CPU architecture

An image containing native binaries built for `amd64` may not run directly on an `arm64` host without compatible emulation or an alternative image variant.

Multi-platform images can provide architecture-specific variants under a common image reference.

This becomes relevant when developers use ARM-based laptops while production runs on x86 servers.

### Native libraries

Consider a Node.js application using a native image-processing dependency.

Its binaries may depend on the target CPU architecture and system libraries.

A module compiled against one environment may fail in another because of ABI incompatibility or missing shared libraries.

For example, Alpine Linux commonly uses musl libc, while Debian-based images use glibc.

These environments are not universally interchangeable for precompiled native dependencies.

A smaller image is not automatically a better image if it creates compatibility problems.

### The host kernel still matters

Containers share the Linux kernel provided by their environment.

Differences in kernel capabilities, security configuration, filesystem support, and cgroup behavior can influence application execution.

### External systems remain external

A container image does not package your production PostgreSQL data, AWS permissions, external API credentials, network routes, or availability guarantees.

Two deployments of the same image can behave differently because their environments differ.

This gives us a more accurate formulation:

**Containers make application packaging and execution environments more consistent. They do not eliminate environmental dependencies.**

That is still an enormously valuable achievement.

---

## 14. From Containers to Orchestration

Let's imagine our Node.js service becomes successful.

It now needs:

- Several application replicas.
- Automated replacement of failed instances.
- Load distribution.
- Controlled rolling deployments.
- Configuration and secret management.
- Resource-aware scheduling.
- Independent background workers.
- Monitoring of health and availability.

Running containers individually becomes operationally cumbersome.

A container orchestrator manages some of this complexity.

### The conceptual role of Kubernetes

Kubernetes is a widely used orchestration platform that manages containerized workloads through declarative configuration.

Its basic abstractions include:

**Pods:** The smallest deployable workload units in Kubernetes, containing one or more tightly coupled containers that share particular resources, including networking.

**Deployments:** Controllers that manage desired replica counts and support rolling updates for suitable stateless workloads.

**Services:** Stable networking abstractions for reaching groups of workloads whose individual Pod addresses may change.

**Nodes:** Machines, physical or virtual, that execute the scheduled workloads.

**Control plane:** Components responsible for coordinating the cluster's desired and observed state.

Conceptually:

```text
         Desired Configuration
                  │
                  ▼
       Kubernetes Control Plane
                  │
             Scheduling
                  │
         ┌────────┴────────┐
         ▼                 ▼
       Node A            Node B
         │                 │
      ┌──┴──┐           ┌──┴──┐
      ▼     ▼           ▼     ▼
     Pod   Pod         Pod   Pod
```

You describe the desired number of replicas and other workload requirements. Kubernetes controllers work to reconcile observed conditions with that desired state.

If a Pod disappears, the relevant controller may create a replacement.

If a node fails, workloads may be rescheduled elsewhere when the cluster has suitable capacity and the workload's constraints allow it.

### What Kubernetes doesn't solve

Kubernetes cannot guarantee that your application processes payments correctly, preserves transaction consistency, or recovers safely from partial business failures.

It cannot make PostgreSQL infinitely scalable.

It cannot compensate for a badly designed service boundary.

A container repeatedly crashing because of a deterministic application bug may simply enter a restart loop under orchestration.

And a deployment of several replicas does not guarantee high availability if every replica depends on the same failing database.

Kubernetes automates infrastructure coordination. It does not eliminate the need for application engineering.

### Do you actually need it?

For some organizations, absolutely.

Kubernetes can be valuable when many workloads require standardized scheduling, scaling, deployment, and operational management, especially when a capable platform team can support it.

For a small SaaS with a handful of services, managed platforms such as AWS ECS/Fargate, container-oriented application hosting, or even well-managed virtual machines may provide a better complexity-to-benefit ratio.

The right comparison is not "Docker versus Kubernetes."

Docker-style container packaging and Kubernetes orchestration operate at different levels.

The actual question is which deployment platform satisfies the application's operational requirements at an acceptable cost.

We'll examine AWS compute choices in SE340-L03.

---

## 15. Practical Lab — Investigate the Container Illusion

This experiment can run on Docker Desktop, Linux, or a suitable development environment with Docker installed.

We'll create a tiny Node.js service, containerize it, examine its process identity and filesystem behavior, then deliberately introduce a networking problem.

### Part A — Create the application

Create a directory and save this file as `server.mjs`:

```javascript
import http from "node:http";
import fs from "node:fs";
import os from "node:os";

const server = http.createServer((req, res) => {
  if (req.url === "/health") {
    res.writeHead(200);
    res.end("OK");
    return;
  }

  if (req.url === "/write") {
    fs.writeFileSync(
      "/tmp/container-demo.txt",
      new Date().toISOString()
    );

    res.end("File written");
    return;
  }

  res.setHeader("Content-Type", "application/json");

  res.end(JSON.stringify({
    pid: process.pid,
    hostname: os.hostname(),
    platform: process.platform,
    cwd: process.cwd()
  }));
});

server.listen(3000, "0.0.0.0");

process.on("SIGTERM", () => {
  console.log("Received SIGTERM");
  server.close();
});
```

Create a simple Dockerfile:

```dockerfile
FROM node:24-bookworm-slim

WORKDIR /app

COPY server.mjs ./

USER node

EXPOSE 3000

CMD ["node", "server.mjs"]
```

Build the image:

```bash
docker build -t container-lab .
```

### Part B — Start and inspect the container

```bash
docker run \
  --name container-lab \
  -p 127.0.0.1:3000:3000 \
  -d \
  container-lab
```

Visit:

```text
http://localhost:3000
```

Inspect the result.

Now execute:

```bash
docker exec container-lab node -p "process.pid"
```

Notice that the process identifiers you observe inside the container need not correspond to those shown by the host.

Inspect the container metadata:

```bash
docker inspect container-lab
```

Look for details such as its configured user, image, network settings, and process state.

### Part C — Investigate storage lifetime

Write a file:

```bash
curl http://localhost:3000/write
```

Inspect it:

```bash
docker exec container-lab \
  cat /tmp/container-demo.txt
```

Now stop and restart the same container:

```bash
docker stop container-lab
docker start container-lab
```

The file should ordinarily still exist.

Next, remove the container:

```bash
docker rm -f container-lab
```

Create a new container from the same image.

The file will no longer be present because it was written to the previous container's writable layer rather than included in the original image or persisted externally.

This distinction is more useful than memorizing the simplistic claim that "containers delete files when stopped."

They ordinarily do not.

### Part D — Add a resource constraint

Run the application again with memory and CPU limits:

```bash
docker run \
  --name limited-api \
  --memory=128m \
  --cpus=0.5 \
  -p 127.0.0.1:3000:3000 \
  -d \
  container-lab
```

Inspect resource usage:

```bash
docker stats limited-api
```

Then inspect its configured limits:

```bash
docker inspect limited-api
```

The purpose is to observe that the process remains an ordinary Node.js application while its permitted resource consumption is governed by container runtime configuration.

Do not intentionally exhaust memory on a shared or production system.

### Part E — Reproduce the networking mistake

Create a user-defined bridge network:

```bash
docker network create lab-network
```

Launch a PostgreSQL container:

```bash
docker run \
  --name lab-db \
  --network lab-network \
  -e POSTGRES_PASSWORD=devpassword \
  -d \
  postgres:17
```

Once PostgreSQL is ready, launch a temporary Node.js container on the same network:

```bash
docker run --rm \
  --network lab-network \
  node:24-bookworm-slim \
  node -e "
    const dns = require('node:dns');
    dns.lookup('lab-db', console.log);
  "
```

Docker's internal DNS should resolve `lab-db` to a container network address.

Now consider what happens if a Node application attempts to connect to `127.0.0.1:5432` instead.

That address points back into the Node container's own network namespace, not to PostgreSQL.

Finally, clean up:

```bash
docker rm -f limited-api lab-db
docker network rm lab-network
```

### What the lab should establish

You've observed several important properties directly:

- A container runs an ordinary Linux process.
- Process and hostname views can differ from those of the surrounding host.
- A container image is distinct from a container's runtime state.
- Writable-layer data survives ordinary restart but not container replacement.
- Resource limits can constrain an otherwise normal process.
- Containers have separate network identities and can communicate through configured networks.

These are the mechanisms behind Docker's practical behavior, not arbitrary conventions invented by its command-line interface.

---

## 16. Engineering and Interview Challenges

### Challenge 1 — The inaccessible application

A Node.js server runs successfully in Docker and reports:

```text
Listening on 127.0.0.1:3000
```

The container is started with:

```bash
docker run -p 8080:3000 my-api
```

Requests to `localhost:8080` on the host fail.

Why might this happen, and what is the correct fix?

### Challenge 2 — The mysteriously disappearing data

Your application writes generated reports to `/app/reports`.

The files remain available after `docker restart`, but disappear after your deployment pipeline replaces the container.

What is happening? Would a named volume solve every aspect of the problem?

### Challenge 3 — The memory paradox

A physical server has 32 GB of RAM and currently uses only 10 GB.

A Node.js container configured with a 512 MB memory limit is unexpectedly killed during a large document-processing operation.

How can this happen? What information would establish whether it was genuinely an OOM event?

### Challenge 4 — The Dockerfile security problem

Review the following:

```dockerfile
FROM node:latest

WORKDIR /app

COPY . .

ENV DATABASE_PASSWORD=supersecret

RUN npm install
RUN npm run build

EXPOSE 3000

CMD node dist/server.js
```

Identify architectural, operational, and security weaknesses. Which changes would you prioritize?

### Challenge 5 — The Kubernetes proposal

Your team maintains three Node.js services and one PostgreSQL database. Traffic is modest, deployments occur weekly, and there are five engineers.

A colleague proposes Kubernetes because the company needs "professional scalability and high availability."

What questions would you ask before accepting the proposal, and what alternatives might be preferable?

---

## 17. Solutions and Discussion

### Challenge 1 — Binding is separate from publishing

The application listens only on the loopback interface inside its container.

Docker's host port publishing ordinarily forwards traffic toward the container's network address, not the container's private loopback listener.

Configure the application to listen on `0.0.0.0`, then verify the container's listener and published port mapping.

Also inspect host binding and firewall settings if connectivity still fails.

The `-p` option cannot repair every incorrect application-level binding decision.

### Challenge 2 — The container writable layer isn't durable infrastructure

The application writes reports into the container's writable filesystem.

Restarting the same container retains that state, while removing and recreating the container ordinarily creates a new writable layer.

A named volume can preserve files independently of a particular container.

However, a named volume alone does not necessarily provide replication, multi-host availability, offsite backups, or shared access across independently scheduled replicas.

If reports must survive node failures or be accessible across multiple application instances, managed object storage may be a better design.

### Challenge 3 — The relevant memory limit is 512 MB

The process is constrained by its cgroup memory configuration, regardless of the host's unused RAM.

A large document-processing operation might allocate enough memory to exceed that limit.

I'd inspect Docker container state, relevant OOM indicators, cgroup memory events, kernel messages where available, and application memory metrics.

Exit code 137 may support the investigation but isn't sufficient proof by itself.

The correct remedy may involve reducing concurrent processing, changing memory-intensive algorithms, using separate workers, or allocating more memory based on measurements.

### Challenge 4 — Multiple avoidable weaknesses

The image uses a floating base tag, increasing build variability.

`COPY . .` may include development artifacts, local dependencies, or sensitive files unless the build context is carefully controlled.

The database password is baked into image configuration, making it potentially visible through image inspection and distribution.

`npm install` may update dependency resolution rather than enforcing the existing lockfile.

Build-time dependencies remain in the final image, and the application likely runs as root by default.

Finally, shell-form `CMD` may introduce signal-forwarding problems.

I would prioritize removing embedded credentials, using appropriate runtime secret management, adopting a deliberate dependency and base-image strategy, introducing a suitable `.dockerignore`, and using a multi-stage build with a non-root runtime.

The resulting image should then be tested for actual runtime compatibility.

### Challenge 5 — Requirements before orchestration

I'd begin with operational requirements rather than technology preferences.

Questions include:

- What availability objective does the business require?
- How frequently do deployments fail?
- What recovery time is acceptable?
- Do services need independent scaling?
- Is there sufficient expertise to operate a cluster?
- What infrastructure does the company currently use?
- What are the actual bottlenecks and costs?
- Is the database already a single point of failure?

Kubernetes may eventually be justified, but it isn't automatically the best choice for three services and five engineers.

AWS ECS/Fargate, a managed application platform, or a simpler container-hosting arrangement may satisfy the requirements with less operational burden.

High availability requires attention to databases, networking, deployment strategy, monitoring, and failure recovery—not merely the number of containers.

---

## Mental Model

Think of containerization as several mechanisms working together:

1. **Namespaces** provide restricted views of processes, networks, filesystems, and other kernel resources.
2. **Cgroups** account for and constrain resource consumption.
3. **Images** package user-space dependencies and application artifacts.
4. **Container runtimes** construct and manage isolated process environments.
5. **Networks and mounts** determine communication and storage behavior.
6. **Registries and build pipelines** distribute versioned artifacts.
7. **Orchestrators** manage placement, replication, updates, and lifecycle across infrastructure.

**The central principle: Containers package and isolate processes, but they do not remove the underlying operating-system, networking, security, persistence, or reliability constraints.**


---

## Next Lecture — SE340-L03: Cloud Infrastructure and AWS Architecture

Continue in **SE340 — Linux, Cloud Infrastructure, and Delivery**.

## Further Reading

1. **Docker — [Docker Engine Security](https://docs.docker.com/engine/security/)**. Official explanation of container isolation, namespaces, cgroups, daemon security, and kernel security controls.

2. **Docker — [Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)**. How to separate build environments from runtime artifacts and minimize unnecessary image contents.

3. **Docker — [Dockerfile Reference](https://docs.docker.com/reference/dockerfile/)**. Detailed documentation for Dockerfile instructions, image metadata, build mounts, caching, and runtime configuration.

4. **Docker — [Networking in Compose](https://docs.docker.com/compose/how-tos/networking/)**. Service discovery, bridge networking, host-versus-container ports, and multi-service communication.

5. **Docker — [Rootless Mode](https://docs.docker.com/engine/security/rootless/)**. The distinction between normal rootful Docker, user-namespace remapping, and rootless container operation.

6. **Linux Manual — [Namespaces](https://man7.org/linux/man-pages/man7/namespaces.7.html)**. The kernel mechanisms underlying process, network, mount, user, and other namespace isolation.

7. **Linux Kernel Documentation — [Control Groups v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)**. The actual kernel-level model for hierarchical resource control.

8. **Kubernetes — [Core Concepts](https://kubernetes.io/docs/concepts/)**. Pods, workloads, services, scheduling, storage, configuration, and cluster architecture.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE340-L02  CONTAINERS — INTERVIEW GLANCE CARD

CORE MODEL
  Container = isolated process environment sharing host kernel
  ≠ full VM with guest OS (Docker Desktop often nests Linux VM)
  “Works on my machine” → package user-space env consistently

NAMESPACES (visibility)
  PID · Network · Mount · UTS · IPC · User · Cgroup · Time
  Container localhost ≠ other container's DB (own netns)
  Host sees container processes; container sees restricted view

CGROUPS (consumption)
  CPU / memory / PIDs / I/O limits — independent of namespaces
  Throttle with idle host CPU; OOM at cgroup limit despite host RAM
  Exit 137 may be SIGKILL; confirm via inspect/logs/cgroup events

DOCKER MODEL
  Image = immutable blueprint (layers, copy-on-write)
  Container = runtime instance + writable layer
  Restart same container keeps writable state; recreate loses it
  Volumes/bind mounts for durable data; volume ≠ backup

PRODUCTION DOCKERFILE HABITS
  Multi-stage: build tools out of runtime
  npm ci + lockfile; copy deps before source (cache)
  USER non-root; pin major tags; digest for stronger identity
  .dockerignore; secrets via mounts — not COPY/ENV into layers
  EXPOSE = metadata; -p publishes; app bind 0.0.0.0 for reachability
  Exec-form CMD ["node",…] for PID1 signal handling

COMPOSE / NETWORKING
  Service DNS name (db:5432); bridge network
  depends_on healthy ≠ forever available; still need retries
  Named volume for PG data; bind mounts hide image paths under mount

SECURITY
  Isolation ≠ dedicated VM; shared kernel risk
  Avoid --privileged; docker.sock mount ≈ host control
  Harden: non-root, drop caps, read-only + tmpfs, no-new-privileges
  Not universal portability: arch, musl vs glibc, kernel, externals

ORCHESTRATION
  K8s: Pods, Deployments, Services, Nodes, control plane
  Automates placement/replicas/rollouts — not business correctness
  Small teams may prefer ECS/Fargate or managed hosts over K8s

SENIOR LINE: Containers package and isolate processes; they don't
             remove OS, network, security, persistence, or reliability limits.
```

---


