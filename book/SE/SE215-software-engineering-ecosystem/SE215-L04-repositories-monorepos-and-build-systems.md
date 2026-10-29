---
id: SE215-L04
course: SE215
title: "Repositories, Monorepos, and Build Systems"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE215-L03
next: SE215-L05
---

# SE215 — The Software Engineering Ecosystem

## Lecture 04: Repositories, Monorepos, and Build Systems

*Your company has twelve Git repositories. A frontend change requires an API change, a shared library release, three pull requests, and two deployment approvals. Someone proposes moving everything into a monorepo. Another engineer declares that microservices must have separate repositories. A third wants Nx, a fourth wants Turborepo, and nobody can explain which problem these tools would actually solve.*

# Part I — Intuition

## The picture to carry in your head

Imagine a company that operates a hotel-booking platform called Mercury.

Its software consists of a Vue frontend, a Node.js API, several Python background workers, shared TypeScript libraries, a database, and infrastructure configuration.

When the company was small, everything lived in one Git repository.

That was convenient. A developer could modify the frontend and backend together, run the tests, and commit the change.

As the company grew, the engineering team decided to separate the code into repositories.

The frontend received its own repository.

The API received another.

The Python workers received a third.

Shared TypeScript interfaces moved into a published package.

Infrastructure lived somewhere else.

At first, the separation felt professional.

Each repository had a clear purpose. Each team had its own CI pipeline. Developers could work without constantly seeing unrelated files.

Then Mercury introduced a new reservation-pricing model.

Previously, the frontend expected a price as a number representing euros.

The backend now needed a richer representation containing an integer amount in minor currency units and a currency code.

That apparently simple change affected several repositories.

First, the backend team updated the API.

Then someone updated the shared TypeScript package and published a new version.

The frontend team changed its dependency version.

The worker team discovered it had a separate copy of the old data structure.

Tests passed in some repositories while others remained incompatible.

The engineering team spent more time coordinating the change than implementing it.

Someone finally asked:

"Why don't we put these projects back into one repository?"

That sounds attractive. But another developer immediately replies:

"Because we use microservices. Microservices require separate repositories."

Is that true?

No.

And understanding why gives us the foundation for today's lecture.

## 1. Three decisions that people keep confusing

There are three different questions.

**Repository organization:** Where do we store and version the source code?

**Application architecture:** How are responsibilities, modules, dependencies, and business capabilities organized?

**Deployment architecture:** Which components run independently, scale independently, and are released independently?

These questions influence one another, but they are not equivalent.

A single repository can contain ten independently deployed microservices.

Five repositories can contain different pieces of one tightly coupled application.

A modular monolith can have strong internal boundaries while living in one repository and being deployed as one application.

And a company can maintain multiple repositories while deploying every component together because their interfaces are too tightly coupled to permit independent releases.

**A repository boundary is not automatically a software architecture boundary.**

That distinction prevents a remarkable amount of confusion.

## 2. A monorepo changes coordination, not reality

A monorepo is a repository containing multiple projects, packages, or applications.

The simplest example might have a frontend application, a backend application, and a shared library in one Git repository.

The immediate advantage is visibility.

A developer can examine all three projects at the same revision.

They can update a shared interface and its consumers in one coordinated change.

They can potentially run integrated checks before merging.

But the monorepo doesn't automatically make the architecture good.

The frontend might still import backend internals it shouldn't know about.

The shared library might become a dumping ground for unrelated utilities.

Every application might depend on a single global configuration file.

And every change might cause every CI job to run.

Putting code together removes certain coordination problems and introduces others.

A monorepo is a tool for organizing collaboration, not a cure for poor dependency design.

## 3. Multiple repositories change the location of the contracts

Now consider the opposite approach.

Mercury keeps the frontend and backend in separate repositories.

The frontend depends on version 3.2 of a shared contracts package.

The backend publishes version 3.3.

Nothing forces the frontend to upgrade immediately.

This creates a potentially useful boundary.

Different teams can release at different times.

They can establish explicit package versions and compatibility policies.

But the organization must now manage publication, versioning, compatibility, and coordination across repositories.

The dependencies haven't disappeared.

They've become more explicit—and sometimes more expensive to change.

Neither arrangement guarantees independence.

A separate repository is useful when it supports a genuine team or product boundary.

It's less useful when it merely forces tightly coupled work to cross several pull requests.

## 4. The dependency graph matters more than the folder tree

Imagine Mercury's frontend depends on a shared UI package and a generated API client.

The API depends on a domain library and a database module.

The Python workers depend on their own runtime packages and consume the API's event schemas.

There is a graph connecting these projects.

The graph tells us what depends on what.

That matters for two reasons.

First, changes can propagate through dependencies.

Changing a shared contracts package may affect several consumers.

Second, build and test operations have an order.

If a frontend build needs a generated API client, that client may need to be generated first.

A good workspace knows these relationships.

A bad one merely contains a collection of directories.

## 5. Why build tooling becomes necessary

Suppose Mercury has twenty projects.

Running every test, rebuilding every application, and redeploying every service after every commit would be wasteful.

If a developer changes only a frontend component, why rebuild an unrelated Python worker?

If a shared contract changes, however, why skip testing the applications that consume it?

The answer requires understanding both the dependency graph and the tasks associated with each project.

Tools such as Nx and Turborepo help coordinate this work.

They can schedule tasks in dependency order, avoid unnecessary work, and reuse cached results when the relevant inputs haven't changed.

But they don't replace package managers, compilers, or test frameworks.

Their job is to organize how those tools run across a larger collection of projects.

## Three questions before the Deep Dive

1. Can two microservices live in the same Git repository while deploying independently?
2. Why might a shared library make changes easier in one situation and more dangerous in another?
3. If a build tool skips a task because its files haven't changed, what other information might still invalidate that decision?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. The architecture review: twelve repositories and one feature

Mercury's engineering manager calls a meeting.

The team has grown to eighteen developers.

It maintains a public web application, an internal administration interface, a Node.js API, two Python workers, shared schemas, deployment configuration, and several supporting libraries.

Some projects are released independently.

Others must be coordinated.

The team wants faster development and fewer integration problems.

One engineer proposes consolidating everything.

Another argues for preserving strict repository boundaries.

A third recommends introducing Nx immediately.

Before choosing, we need to identify what actually hurts.

Are developers repeatedly making coordinated changes across repositories?

Is publishing shared packages slow?

Do teams accidentally depend on one another's internal code?

Are CI pipelines expensive?

Are builds nondeterministic?

Do independent applications genuinely need independent release histories?

These questions describe the problem.

The repository arrangement is a possible solution.

Starting with a fashionable tool would reverse the reasoning.

## 2. Monorepo versus multirepo: the practical trade-off

A monorepo keeps multiple projects within one repository and shared history.

This can make coordinated changes easier.

For example, Mercury changes an API schema and the associated frontend consumer in the same pull request.

Reviewers can inspect both sides of the contract.

CI can validate the combined changes.

Nobody needs to publish an intermediate package release merely to test the new representation locally.

But the shared history and configuration introduce coordination costs.

A root dependency update may affect many projects.

CI must distinguish relevant work from unrelated work.

Permissions and code ownership may become complicated.

Developers may need specialized tooling to work comfortably in a large repository.

### The multirepo alternative

With multiple repositories, each project has its own history, dependency configuration, and potentially its own release workflow.

Teams can maintain separate access controls and governance.

A small service can use its preferred development tools without accommodating every other service's requirements in one workspace.

But cross-repository changes become distributed coordination tasks.

A shared library may need publication before consumers can use it.

A breaking API change must be introduced compatibly or deployed through a coordinated sequence.

A developer investigating an incident may need to locate several repositories and determine which versions were running together.

### The important distinction

A monorepo makes **source coordination** easier.

A multirepo can make **project isolation and independent lifecycle management** easier.

Neither grants architectural independence automatically.

The correct decision depends on the real coupling between projects, the organization, and its delivery needs.

## 3. Repository boundaries don't decide runtime boundaries

Let's imagine three applications in one repository.

The frontend is deployed to a CDN.

The API runs as containers.

The background workers run as independently scaled Kubernetes Jobs.

All three share a Git commit history.

Does that make them a monolith?

No.

They remain distinct deployment units.

Their communication happens through APIs, messages, or shared storage according to the architecture.

They can use separate images, release processes, runtime configurations, and scaling policies.

Now consider three repositories where frontend, API, and workers access the same tables, require synchronized code changes, and must always deploy together.

The repositories are separate, but the system remains operationally coupled.

A useful rule is:

**Judge architectural independence by contracts, data ownership, and operational behavior—not by the number of Git repositories.**

SE330-L02 examines modular monoliths and internal boundaries. CS430-L04 goes deeper into microservices, independent deployment, and distributed ownership.

Here we're focusing on source organization.

## 4. How a multi-project repository is actually structured

Mercury decides to try a single repository for related applications and shared packages.

The repository contains applications, reusable packages, and infrastructure configuration.

Conceptually:

```text
mercury/
├── apps/
│   ├── customer-web/
│   ├── admin-web/
│   ├── booking-api/
│   └── scanner-worker/
├── packages/
│   ├── api-contracts/
│   ├── api-client/
│   ├── ui/
│   └── shared-config/
├── infra/
│   ├── terraform/
│   └── kubernetes/
├── tools/
├── package.json
├── pnpm-workspace.yaml
└── pnpm-lock.yaml
```

The two frontend applications and booking API are TypeScript projects.

The scanner worker uses Python.

The `api-contracts` package contains schemas or generated types that appropriate consumers may use.

The `api-client` package provides the client interface used by browser applications.

The UI package contains reusable presentation components.

Infrastructure lives alongside the applications whose deployment requirements it describes.

But this is only one reasonable layout.

A company may organize by business domain instead of by applications and packages.

A large organization might prefer separate repositories for unrelated products.

The directory tree should help people find ownership and understand dependencies.

It shouldn't be treated as an architectural achievement in itself.

## 5. Package managers and workspaces

Let's distinguish several tools that are often grouped together.

A package manager installs and resolves dependencies.

In JavaScript ecosystems, common options include npm, pnpm, and Yarn.

These tools can also support workspaces, allowing multiple local packages to be managed together.

For example, our frontend depends on a local `api-client` package.

Without workspace support, the team might need to publish a package or use an awkward local-linking arrangement to test changes.

With a workspace, the package manager can resolve the local package as part of the repository's project collection.

### The lockfile

A lockfile records resolved dependency information so installation can reproduce the intended dependency graph under the relevant package manager and configuration.

This matters because dependency declarations often permit version ranges.

Two developers installing dependencies at different times shouldn't silently receive incompatible dependency versions merely because the package registry changed.

But a lockfile doesn't guarantee the entire system is reproducible.

Build tools, operating systems, environment variables, external downloads, and runtime configuration may also affect results.

A lockfile is a major piece of the reproducibility story, not the whole story.

### The workspace protocol

pnpm supports an explicit `workspace:` dependency protocol.

If `customer-web` declares a dependency on `@mercury/api-client` through that protocol, pnpm resolves it from the local workspace rather than unexpectedly downloading a similarly named package from a registry.

That creates a useful guarantee about dependency identity.

But it still doesn't determine whether the package's public interface is well designed.

The package manager resolves dependencies.

Engineers define appropriate dependencies.

## 6. Why shared packages become dangerous

Shared code seems attractive.

Mercury has two frontends, so creating one UI component library makes sense.

But what about a universal `shared` package?

Someone adds date formatting.

Another adds payment validation.

A third adds MongoDB connection utilities.

A fourth adds authentication middleware.

Soon every application depends on the same enormous package.

Now a change to an unrelated helper may invalidate builds across the entire repository.

A package intended to reduce duplication has become a source of coupling.

### Cohesion matters

A good package should have a meaningful responsibility.

A UI component package may be coherent.

A generated API client may be coherent.

A domain-specific pricing library may be coherent if its use and ownership are clear.

A package named `utils` containing unrelated business rules is often a warning sign.

The question is not merely whether code is shared.

It's whether the shared dependency reflects a stable, meaningful boundary.

### Public interfaces

Consumers should depend on a package's deliberate public interface rather than importing arbitrary internal files.

Otherwise, changing internal implementation details becomes a breaking change for external consumers.

For example, the frontend should import an exported API client rather than reach into the API server's internal repository classes.

A workspace makes internal files physically accessible.

That does not make them appropriate dependencies.

**Physical proximity should not weaken logical boundaries.**

## 7. Shared contracts: useful, but not magical

The team introduces shared API schemas.

This reduces a recurring problem: frontend developers and backend developers independently representing the same payload.

One approach is to define a schema in a language-neutral format, such as OpenAPI or JSON Schema, and generate appropriate clients or types.

Another approach, when both sides use TypeScript, may share runtime validation schemas under clear compatibility rules.

Either approach can reduce disagreement.

But sharing types isn't the same as verifying deployed behavior.

### The version mismatch

Suppose the main branch contains a frontend and backend that both understand a new `price` object.

The code compiles.

The integrated tests pass.

Then the frontend is deployed before the backend.

Production still serves the old representation.

The new frontend breaks.

The shared repository provided compile-time agreement for one revision.

It did not guarantee that both revisions would be deployed simultaneously.

This is especially important when services deploy independently.

### Make contract changes compatible

For distributed applications, compatible evolution usually matters more than synchronized source changes.

The backend may first introduce the new field while preserving the old representation.

The frontend may then learn to consume the new field.

After relevant consumers have migrated, the old field can be removed through a controlled process.

The exact sequence depends on which component owns the contract and what versions may coexist.

The lesson is that shared source code doesn't eliminate runtime version skew.

## 8. The dependency graph: what truly needs rebuilding?

Now Mercury has twenty projects.

A developer changes a button style inside the customer frontend.

Should the backend API be rebuilt?

Probably not.

A developer changes the schema package used by both frontend and backend.

Should both consumers be checked?

Very likely.

This can be represented as a dependency graph.

A consumer points toward the package it depends on.

For example:

```text
customer-web ─────► api-client ─────► api-contracts

admin-web ────────► api-client

booking-api ───────────────────────► api-contracts

customer-web ─────► ui

admin-web ────────► ui
```

If `ui` changes, the two web applications may be affected.

If `api-contracts` changes, the API client, frontends, and backend may need relevant verification.

If only a backend-specific internal module changes, frontend builds may not need to run.

But there's an important qualification.

Not every dependency is visible from imports alone.

A project might depend on a generated file, environment variable, configuration file, or external schema.

A useful build system needs to understand the inputs that actually influence each task.

## 9. Build tools and task orchestration

Let's say Mercury's frontend build needs the API client to be generated first.

That client depends on an API schema.

The logical sequence is:

Generate or validate schemas.

Generate the client.

Compile the frontend.

Run relevant tests.

A task orchestrator can encode these relationships.

Instead of relying on developers to remember the correct order, the tooling constructs a task graph and executes tasks accordingly.

### Nx

Nx models projects and tasks, tracks dependencies, and supports affected-task selection, caching, and task execution across a workspace.

It can integrate with different build tools and languages.

Its value is coordinating the work, not replacing every underlying compiler or test runner.

### Turborepo

Turborepo focuses on orchestrating tasks across packages, using dependency-aware task pipelines and caching.

A TypeScript monorepo might continue using Vite for the frontend, TypeScript for compilation, and Vitest for testing.

Turborepo can coordinate when those commands execute and reuse suitable results.

### When do we need them?

A repository with two small projects may not need sophisticated orchestration.

Package-manager workspaces and a few clear scripts may be enough.

As the number of projects and their dependency relationships grow, task coordination and caching become more valuable.

The correct question is not:

"Should we use Nx or Turborepo?"

It's:

"Which work is currently being repeated, scheduled incorrectly, or made unnecessarily difficult by our existing tooling?"

## 10. Build caching: reuse the result, not just the source

Suppose Mercury's API client has already been generated from a particular schema.

Nothing relevant has changed.

Why generate it again?

A build cache allows the system to reuse the result of a previous computation when the inputs that determine the result are equivalent.

A task can be modeled conceptually as:

Inputs plus tools and configuration produce outputs.

If those inputs are unchanged, the previous outputs may be reusable.

This is not simply checking whether source files changed.

### Hidden inputs break caches

Consider a build that reads `NODE_ENV`, a feature flag, and an API base URL.

If its cache key considers only source files, two builds with different runtime configuration may incorrectly be treated as equivalent.

Or imagine a code generator that downloads the latest remote schema during execution.

The local source files remain unchanged, but the generator's output can differ.

If the build system doesn't account for that external input, cached results may be incorrect.

### What makes a task cacheable?

A good candidate is deterministic for the declared inputs and produces identifiable outputs.

Compilation, code generation, linting, and many tests can be cacheable under suitable conditions.

A task that deploys to production should not be treated as an ordinary reusable computation.

Neither should a database migration.

Those operations perform effects on external systems.

Restoring a previous log saying "deployment successful" would not perform the required deployment.

**Caching a computation is different from skipping a side effect.**

## 11. Local and remote caches

A local cache preserves results on a developer's machine.

If the same task is run again with equivalent inputs, the result may be restored rather than recomputed.

A remote cache allows compatible results to be shared between machines, such as developers' laptops and CI runners.

This can substantially reduce repeated work.

For example, a CI pipeline builds a package and stores the result in a remote cache.

A second pipeline with equivalent inputs can reuse it.

But caching introduces questions of trust and correctness.

Who is allowed to publish cached results?

Can untrusted pull requests influence artifacts later used by privileged workflows?

Do the cache keys include relevant dependency versions, environment details, and configuration?

Are sensitive outputs accidentally being stored?

A poorly designed cache can make builds faster while making failures more confusing.

Speed is useful only when the reused result is trustworthy.

## 12. A monorepo doesn't mean every change runs every test

One common criticism of monorepos is that every commit requires rebuilding and testing everything.

That can be true of a naïve pipeline.

But it isn't an inherent property of monorepos.

An affected-task system examines what changed and which tasks depend on the changed inputs.

A change to the UI package may trigger relevant frontend tests and builds while leaving unrelated Python worker checks untouched.

A change to a shared schema may affect more applications.

A change to root dependency configuration or shared tooling may legitimately affect nearly everything.

### The dangerous shortcut

Suppose a project declares that its tests depend only on files in its own directory.

But the tests actually import a shared validation package.

A change to that package could affect behavior without causing the tests to run.

The CI system looks impressively efficient.

Unfortunately, it has become incorrect.

The dependency model must represent real relationships.

Otherwise, affected-only testing creates false confidence.

### A practical compromise

For fast pull-request feedback, run targeted checks based on dependency information.

For critical cross-cutting changes, run broader integration checks.

At appropriate intervals, run comprehensive verification.

The exact mix depends on risk, build cost, and how trustworthy the dependency analysis is.

The goal isn't minimizing CI duration at all costs.

It's achieving useful confidence for a reasonable amount of computation.

## 13. The Python worker complication

Mercury also has Python workers.

Can they live in the same monorepo as the TypeScript applications?

Of course.

Git doesn't require every project to use the same language.

But a JavaScript workspace manager isn't automatically a Python dependency manager.

The Python worker may use `pyproject.toml`, a lockfile supported by its chosen tooling, and its own virtual environment or container image.

Its tests may run through pytest.

Its packaging and deployment process may be independent of pnpm.

Nx or a more general CI orchestrator may be able to coordinate some of these tasks.

But the underlying Python tools still own Python dependency resolution and execution.

This is one reason polyglot monorepos can become complicated.

The repository is shared, while individual language ecosystems retain distinct conventions.

### Shared contracts across languages

Suppose the Node.js API publishes job messages that Python workers consume.

A shared TypeScript interface doesn't directly protect the Python consumer.

The team needs a language-neutral contract or a process for generating and verifying compatible representations.

JSON Schema, Protocol Buffers, or another appropriate contract format may help.

But runtime validation and compatibility testing remain necessary.

The source code can sit side by side while the actual services continue to communicate through serialized messages.

## 14. Versioning and releasing independently

Now consider two packages.

The first is an internal UI component library consumed only within Mercury's monorepo.

The second is a public SDK consumed by customers outside the repository.

Should they use the same versioning strategy?

Probably not.

### Internal packages

If the UI library and its consumers are always developed and tested together, the team may not need to publish a new registry version for every internal change.

Local workspace references can simplify coordinated development.

However, some monorepos intentionally publish internal packages because they need independent distribution or because other repositories consume them.

### Public or independently consumed packages

A public SDK has consumers that update on their own schedules.

Its releases should have identifiable versions.

Breaking changes require explicit compatibility consideration.

Documentation, migration guides, and release notes become important.

Semantic versioning can communicate intended compatibility, but it doesn't prove compatibility.

The team must still test and support the promised behavior.

### Independent application deployments

Even if every application uses one Git repository, each can produce a separate build artifact.

A frontend might deploy to static hosting.

The API might deploy as a container.

The worker might deploy to Kubernetes.

They can have different rollout schedules.

A useful release record should identify the source revision, artifact version, and configuration used for each deployed component.

Otherwise, one shared repository revision can still correspond to several different production states.

## 15. Ownership and permissions at scale

A monorepo makes it easy to find code, but that doesn't mean everyone should casually change every package.

Different teams may own different domains.

A security-sensitive authentication library may require specialist review.

A shared API contract may require approval from the owning team.

Infrastructure configuration may have separate deployment permissions.

Tools such as CODEOWNERS can help route review responsibility according to repository paths.

Dependency rules can restrict which packages may import one another.

These are useful protections.

But ownership shouldn't become a system where a single overburdened engineer must approve hundreds of unrelated changes.

The organizational design should support change rather than create permanent queues.

### The secret boundary

A final warning: repository permissions are not the same as runtime access controls.

Putting source code in a separate repository can simplify access management.

But it doesn't automatically protect production credentials.

And putting infrastructure code in a monorepo doesn't mean every developer should have permission to deploy it.

Secrets, deployment credentials, cloud permissions, and production controls need their own boundaries.

Source organization and operational authority are related but distinct decisions.

## 16. Choosing for Mercury

Let's return to the architecture meeting.

Mercury has two web applications, one Node.js API, Python workers, shared schemas, and infrastructure code.

Most feature work requires coordinated changes between the web applications and API.

The team complains about publishing shared packages and waiting for cross-repository pull requests.

The number of projects is manageable.

Under those conditions, I'd lean toward a monorepo for the tightly related product applications and shared contracts.

I'd begin with clear directory ownership, workspaces for TypeScript packages, a language-neutral contract mechanism for Python interoperability, and independent deployment pipelines.

I would not automatically introduce an elaborate build platform on day one.

If builds become slow or dependency relationships complicated, I'd evaluate tools such as Nx or Turborepo using actual measurements.

### What would change my mind?

Suppose Mercury also operates an unrelated data-processing product maintained by a different division.

It has different access requirements, different release schedules, and almost no shared code.

Keeping that product in a separate repository may be sensible.

Or imagine the infrastructure team's security policy requires different source-access boundaries for certain systems.

That may justify separation.

The objective isn't to achieve exactly one repository or exactly one repository per service.

It's to match repository boundaries to the real collaboration and lifecycle boundaries of the software.

## 17. What the senior engineer should be able to explain

If an interviewer asks whether you prefer monorepos or multirepos, don't answer with a slogan.

Ask what the organization is building.

How many projects exist?

How frequently do they change together?

Are their teams and release schedules independent?

Which packages are shared?

What does the current CI system cost?

Are cross-repository changes causing delay?

What access controls are required?

Then explain the trade-off.

A good senior engineer understands that these choices affect the entire development system.

Repository organization influences collaboration.

Dependency boundaries influence maintainability.

Build orchestration influences feedback speed.

Caching influences CI economics and correctness.

Versioning influences compatibility.

And deployment pipelines determine whether source changes become safe production releases.

Those relationships matter much more than knowing every option in a particular monorepo tool.

---

# The Oral Examination

Answer aloud before reading the solutions.

### Question 1 — Monorepo versus monolith

A company stores eight services in one Git repository. Each service has its own container image, database ownership, and release pipeline. Is the system a monolith?

### Question 2 — Shared contracts

The frontend and backend import the same TypeScript type. Both compile successfully on main. Why might production still break when the frontend is deployed?

### Question 3 — Build caching

A code-generation task reads a remote schema, but the cache key only includes local source files. What could go wrong?

### Question 4 — Workspace packages

What problem does a package-manager workspace solve? What problems does it not solve?

### Question 5 — Affected tests

A developer changes a shared validation package. The CI pipeline skips frontend tests because no files in the frontend directory changed. What is wrong with the dependency analysis?

### Question 6 — The Python worker

A company uses pnpm workspaces for TypeScript projects and has Python workers in the same repository. Does pnpm now manage the Python environment automatically?

### Question 7 — Choosing repository boundaries

One business domain changes together across frontend, backend, and workers. Another product has a separate team, separate security requirements, and almost no shared code. Would you necessarily put everything into one repository?

---

# Solutions and Discussion

## Solution 1 — Repository structure is not deployment architecture

No. One repository can contain multiple independently deployed services. Whether the system is a monolith or microservice architecture depends on runtime behavior, boundaries, data ownership, and deployment relationships.

## Solution 2 — Source agreement is not deployed-version agreement

The frontend may be built from a revision expecting a new contract while production still runs an older backend. Shared types do not eliminate runtime version skew. Compatible API evolution and appropriate deployment sequencing remain necessary.

## Solution 3 — Hidden inputs invalidate cached results

The remote schema can change while local files remain identical. A cache key that ignores the schema may reuse outdated generated code. The task's input model must capture relevant external inputs or treat the operation as unsuitable for that caching approach.

## Solution 4 — Workspaces coordinate local packages

Workspaces make it easier to resolve and develop related local packages together. They don't automatically establish good module boundaries, validate runtime contracts, orchestrate every build task, or guarantee independent deployment.

## Solution 5 — The task graph is incomplete

The frontend tests depend on behavior from the shared validation package. If the CI model ignores that relationship, it may skip tests affected by the change. The input and dependency model needs to reflect actual consumption.

## Solution 6 — Different ecosystems retain different tools

No. pnpm manages JavaScript/TypeScript package dependencies. Python workers still require appropriate Python dependency, build, and execution tooling, even when they live in the same repository.

## Solution 7 — Match boundaries to real relationships

Not necessarily. A monorepo may benefit closely related projects with frequent coordinated changes. A largely independent product may benefit from its own repository and governance. One repository policy need not fit the entire organization.

---

# The Mental Model Worth Keeping

When evaluating a repository strategy, separate five questions.

**Source:** Where does code live, and how do developers coordinate changes?

**Dependencies:** Which projects rely on which other projects?

**Build:** Which computations must execute, in what order, and which can be reused?

**Release:** Which artifacts can be versioned and deployed independently?

**Ownership:** Who is responsible for changes, compatibility, and operational safety?

A monorepo can simplify coordinated development.

A multirepo can strengthen independent lifecycle management.

Neither guarantees good architecture.

**The best repository design makes real dependencies visible and manageable without creating unnecessary coordination work.**

# Next Lecture — SE215-L05: Cloud Platforms and Service Models

We've organized Mercury's code and builds.

Now we need somewhere to run the resulting applications.

Should the API run on virtual machines, containers, or managed functions?

Where should PostgreSQL live?

How do public and private networking differ?

What does the cloud provider manage, and what remains our responsibility?

And how do AWS, Google Cloud, and Microsoft Azure express similar infrastructure concepts through different services?

Next we'll develop a provider-neutral mental map of cloud infrastructure, then translate one practical SaaS architecture across the three major platforms.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Workshop — Design a Repository for Mercury

## Exercise A — Choose the boundaries

Mercury has these components:

- `customer-web`: Vue and TypeScript.
- `admin-web`: React and TypeScript.
- `booking-api`: Node.js and TypeScript.
- `scanner-worker`: Python.
- `api-contracts`: shared language-neutral schema definitions.
- `api-client`: generated TypeScript client.
- `ui`: shared UI primitives where appropriate.
- `infra`: Terraform and Kubernetes configuration.

Draw a proposed repository structure.

Then answer:

Which components should be built independently?

Which components should deploy independently?

Which components have source dependencies?

Which share runtime contracts but not source dependencies?

Would you keep every component in one repository? Why?

## Exercise B — Create a minimal pnpm workspace

For a small TypeScript monorepo, declare the workspace packages and applications in `pnpm-workspace.yaml`:

```yaml
packages:
  - "apps/*"
  - "packages/*"
```

Give `packages/api-client/package.json` a package name such as `@mercury/api-client`.

Then declare it as a local dependency in `apps/customer-web/package.json`:

```json
{
  "name": "@mercury/customer-web",
  "private": true,
  "dependencies": {
    "@mercury/api-client": "workspace:*"
  }
}
```

After installing dependencies with pnpm, examine how the local package is resolved.

Then consider what happens if the package is renamed or removed.

**Question:** Why can an explicit workspace dependency be preferable to accidentally resolving a similarly named registry package?

These examples are intentionally minimal. A real workspace would need appropriate scripts, package entry points, compiler configuration, and project dependencies.

## Exercise C — Draw the dependency graph

Use this dependency model:

```text
customer-web -> api-client -> api-contracts
admin-web    -> api-client
customer-web -> ui
admin-web    -> ui
booking-api  -> api-contracts
scanner-worker -> api-contracts (schema consumption)
```

For each change, identify which projects should undergo relevant verification:

1. A CSS change inside `ui`.
2. An API schema change.
3. A Python-worker internal implementation change.
4. A root dependency lockfile update.
5. A shared TypeScript compiler configuration change.

Don't assume every dependent project needs the same task.

A source change may require testing but not necessarily rebuilding every artifact.

An input affecting the final output must be represented in the build model.

## Exercise D — The broken cache

A team configures build caching for a frontend application.

Its build reads an environment variable indicating which API origin to embed.

The task's cache key includes source files but not that environment variable.

CI builds the production configuration.

Later, another job restores the cached result while attempting to build a staging configuration.

The frontend points to the wrong API.

Explain:

What was missing from the task's input model?

Which kinds of environment values should influence build outputs?

Why is a deployment task not an ordinary computation to cache?

How would you verify the fix?

## Exercise E — Senior interview rehearsal

Prepare a two-minute answer to:

"Would you use a monorepo or separate repositories for a full-stack SaaS with two frontends, several backend services, and shared contracts?"

A good answer should cover coordinated development, dependency boundaries, builds, CI, versioning, independent releases, and team ownership.

Do not merely say that monorepos are easier or that microservices require separate repositories.

Make the choice depend on the requirements.

---

# Further Reading

Technical references:

- **pnpm Workspaces:** https://pnpm.io/workspaces/
- **npm Workspaces:** https://docs.npmjs.com/cli/using-npm/workspaces/
- **Nx — How Nx Works:** https://nx.dev/docs/getting-started/how-nx-works
- **Nx — Run Affected Tasks:** https://nx.dev/docs/features/ci-features/affected
- **Turborepo — Caching:** https://turborepo.dev/docs/crafting-your-repository/caching
- **TypeScript Project References:** https://www.typescriptlang.org/docs/handbook/project-references.html

Related programme chapters:

- SE215-L03 — Git, Pull Requests, and Collaborative Delivery
- SE215-L05 — Cloud Platforms and Service Models
- SE240-L02 — Frontend Architecture Beyond Components
- SE330-L02 — Architecture Patterns and Their Consequences
- SE340-L04 — CI/CD and Infrastructure as Code
- CS430-L04 — Microservices, Events, and Service Boundaries

---

## Dense Cheatsheet — Interview Glance Card

```text
SE215-L04 — REPOSITORIES, MONOREPOS, BUILD SYSTEMS

FIVE DIFFERENT QUESTIONS
  SOURCE        Where does code live?
  DEPENDENCIES  Which projects rely on others?
  BUILD         Which tasks must run and in what order?
  RELEASE       What versions and deploys independently?
  OWNERSHIP     Who controls and maintains changes?

MONOREPO
  One repository, multiple projects/packages/apps
  Benefits:
    Cross-project atomic source changes
    Shared history and visibility
    Local package development
    Coordinated tests
  Costs:
    Shared tooling and config complexity
    CI and dependency graph challenges
    Large shared blast radius
    More complex code ownership

MULTIREPO
  Multiple repositories with independent histories
  Benefits:
    Isolated governance and project lifecycle
    Independent tooling/release management
    Clear repository-level permissions
  Costs:
    Cross-repository coordination
    Package publishing/versioning
    More difficult integrated changes
    Version compatibility across repos

CRITICAL DISTINCTIONS
  Monorepo != monolith
  Multirepo != microservices
  Separate repo != independent deployment
  Shared source types != runtime contract compatibility

PACKAGE MANAGERS
  npm / pnpm / Yarn manage JS ecosystem dependencies
  Workspaces manage related local packages
  Lockfiles record resolved dependency graph
  workspace: in pnpm explicitly targets local package
  Workspaces do not define architecture by themselves

PROJECT GRAPH
  Projects connected by dependencies
  Change may affect downstream consumers
  Source imports are not the only dependencies
  Schemas, generated files, configs, and env also matter

TASK GRAPH
  Build, test, lint, generate, etc. as tasks
  Dependencies define execution order
  Example:
    schema -> api-client -> frontend build

BUILD CACHING
  Equivalent declared inputs -> reusable output
  Cache key must account for relevant inputs
  Local cache: reuse on same machine
  Remote cache: reuse across machines/CI
  Declare outputs to restore artifacts correctly
  Hidden inputs can cause incorrect cache hits
  Never treat external side-effect tasks as ordinary caches

AFFECTED TASKS
  Run checks influenced by changed inputs
  Shared package change may affect many apps
  Root config change can affect all
  Incomplete dependency model => false confidence
  Targeted checks + broader verification as needed

NX
  Project graph, task graph, affected tasks, caching
  Coordinates underlying build/test tools
  Useful for complex multi-project environments

TURBOREPO
  Task pipeline and dependency-aware orchestration
  Task output and log caching
  Often used in JS/TS monorepos

POLYGLOT REPOS
  Python may have pyproject.toml + separate dependency tools
  JS workspace tool doesn't manage Python automatically
  Share language-neutral contracts where needed
  Validate runtime serialization and compatibility

SHARED PACKAGES
  Good: coherent responsibility and public interfaces
  Bad: universal "shared" dumping ground
  Physical accessibility != permitted dependency
  Avoid importing package internals directly

CONTRACTS
  Generated clients reduce duplication
  API deploys may differ from source revision
  Backward compatibility needed across versions
  Source agreement != production agreement

VERSIONING
  Internal packages may use local workspace links
  Published packages need release/version discipline
  SemVer communicates intent, not proof
  Apps can build/deploy independently from one repo

OWNERSHIP
  CODEOWNERS and review policies
  Dependency boundary enforcement
  Clear package responsibilities
  Source access != production authority

WHEN CHOOSING
  How often do projects change together?
  Are releases independent?
  Are teams and access requirements independent?
  Are shared contracts frequent?
  Is CI a bottleneck?
  Is the dependency graph trustworthy?

MENTAL MODEL
  Organize source around collaboration.
  Organize modules around responsibility.
  Organize deployments around runtime needs.
  Organize builds around real dependencies.
```
