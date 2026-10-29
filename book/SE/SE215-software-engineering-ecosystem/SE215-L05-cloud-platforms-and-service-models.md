---
id: SE215-L05
course: SE215
title: "Cloud Platforms and Service Models"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE215-L04
next: SE215-L06
---


# SE215 — The Software Engineering Ecosystem

## Lecture 05: Cloud Platforms and Service Models

*Three consultants examine the same SaaS application. One recommends AWS, another insists on Google Cloud, and the third declares Azure the sensible enterprise choice. Each produces an impressive architecture diagram filled with unfamiliar product names. Your CTO turns to you: "Forget the logos. What are we actually buying, and which parts will we still have to operate?"*

---

# Part I — Intuition

## The picture to carry in your head

Imagine you're launching Mercury, a small hotel-booking SaaS.

The application is already working locally.

It has a Vue frontend, a Node.js API, PostgreSQL, background workers, and a collection of hotel photographs.

You run everything through Docker Compose.

The frontend is available on your laptop.

The API connects to PostgreSQL.

A worker processes booking notifications.

Everything works.

Now the CTO asks you to make it available to customers across Europe.

Suddenly, Docker Compose is no longer the whole story.

Where will the application run?

Who will keep the computers functioning?

How will users connect to them?

Who will manage TLS certificates?

What happens when a machine disappears?

Where should the database store its data?

How do we protect credentials?

How do we replace the software without interrupting existing users?

And who wakes up when something breaks at three in the morning?

Cloud computing provides services that help answer these questions.

But understanding cloud computing starts with a much simpler idea.

**A cloud provider allows you to rent programmable infrastructure and managed capabilities rather than building and operating every underlying component yourself.**

That's the picture to carry through the lecture.

## 1. From owning the machine to choosing the responsibility

Imagine Mercury rents a physical server in a data center.

Someone must purchase or allocate hardware, replace failed disks, configure networking, install an operating system, manage software updates, and keep the machine running.

You can hire people to do some of that work.

You can outsource other parts.

But somebody remains responsible for everything.

Now Mercury rents a virtual machine from a cloud provider.

The provider manages the physical hardware and underlying virtualization.

Your team still configures the guest operating system, installs the application, manages many security settings, and decides how to recover when that virtual machine fails.

This arrangement is commonly called **Infrastructure as a Service**, or IaaS.

Now imagine Mercury chooses a managed application platform instead.

You supply the application code or a container image.

The provider manages more of the runtime environment, provisioning, and application hosting machinery.

This moves toward **Platform as a Service**, or PaaS.

Your team has less infrastructure to maintain, but also less control over the environment.

The trade-off is not fundamentally about old technology versus new technology.

It's about **which responsibilities your team keeps and which it delegates**.

## 2. Managed doesn't mean responsibility-free

Suppose Mercury uses a managed PostgreSQL service.

The cloud provider handles substantial parts of database provisioning, infrastructure maintenance, backups, and availability mechanisms according to the chosen service and configuration.

That sounds wonderful.

But who decides which tables to create?

Who writes efficient queries?

Who prevents two customers from booking the same room?

Who makes sure the application doesn't exhaust its database connections?

Who chooses a suitable backup-retention policy and tests that recovery meets the business requirements?

Those are still engineering responsibilities.

The provider manages a database service.

It doesn't know whether your reservation logic is correct.

This distinction is called the **shared responsibility model**.

The provider owns certain parts of the infrastructure and service operations.

You retain responsibility for your application, data, access decisions, configurations, and the behaviors that matter to your business.

The exact division depends on the service.

A virtual machine leaves you with more operational work than a fully managed application platform.

But neither transfers ownership of your business correctness to the provider.

## 3. Every cloud platform sells variations of the same building blocks

Now consider our Mercury application.

It needs somewhere to execute code.

It needs somewhere to store relational data.

It needs somewhere to store photographs and documents.

It needs a way to receive HTTP traffic.

It needs background processing.

It needs identities and permissions.

It needs monitoring.

And it needs a network connecting these components.

These are **capability categories**.

AWS, Google Cloud, and Microsoft Azure offer different products that fulfill them.

Their naming, behavior, configuration, and operational constraints vary.

But the underlying engineering questions remain recognizable.

For compute: what executes the code?

For networking: who can reach it?

For storage: where does durable data live?

For identity: who is permitted to do what?

For operations: how do we observe and recover the system?

Once you understand those categories, learning a new cloud provider becomes much less intimidating.

Instead of memorizing hundreds of service names, you ask which service implements the capability you already understand.

## 4. A cloud region is a business decision

Mercury's customers are primarily European.

Should we deploy the application in Europe or the United States?

The choice affects latency.

It can affect data residency, regulatory obligations, operating costs, and disaster-recovery planning.

Cloud providers divide their infrastructure into geographical regions.

Within many regions, they offer multiple availability zones or comparable failure-isolation arrangements.

These give us options for reducing dependence on one physical facility.

But deploying in one region doesn't automatically make an application resilient.

If the database exists only in one failure domain, losing that dependency may make all application instances useless.

Similarly, deploying two application containers doesn't help much if both depend on one exhausted database connection pool.

Redundancy needs to follow the real dependencies of the system.

## 5. The cloud changes the way we purchase capacity

Suppose Mercury has one hundred visitors per hour most nights, but ten thousand during a major holiday promotion.

Traditionally, the company might have to provision enough hardware for the busiest period and keep paying for unused capacity afterward.

Cloud platforms provide ways to allocate and release computing resources dynamically.

This is often described as elasticity.

But elasticity is not the same as infinite capacity.

The application may scale faster than the database.

The provider may impose quotas.

A queue may grow faster than workers can process it.

And automatic scaling can increase expenses.

The cloud makes capacity programmable.

**It doesn't make the laws of resource contention disappear.**

## 6. The choice of provider comes after the choice of architecture

Imagine the AWS consultant says:

"We should use Lambda, API Gateway, DynamoDB, and EventBridge."

The Google Cloud consultant says:

"We should use Cloud Run, Cloud SQL, Pub/Sub, and Cloud Storage."

The Azure consultant proposes Container Apps, Service Bus, Blob Storage, and managed PostgreSQL.

These are all plausible ingredients.

But they don't answer the most important questions.

What does Mercury actually need?

What is the workload?

How much operational complexity can a four-person engineering team support?

Does the business need relational transactions?

How predictable is traffic?

Which regions and compliance requirements matter?

What are the reliability objectives?

Once those constraints are clear, we can compare concrete offerings.

Otherwise, the architecture becomes a collection of attractive product names looking for problems to justify their existence.

### Three questions before the Deep Dive

1. Why is running an application on a cloud virtual machine different from deploying it to a managed container platform?
2. If a managed database handles backups and infrastructure maintenance, which important responsibilities remain with developers?
3. Why can automatically scaling an API make the entire application less reliable?

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. Start with the application, not the cloud provider

Let's define Mercury's requirements.

It operates a public hotel-search interface and an authenticated booking application.

The API uses Node.js and TypeScript.

PostgreSQL stores customers, reservations, and payment-operation records.

Python workers process notifications and supplier synchronization.

Hotel photographs and generated invoices need durable object storage.

The service must be accessible over HTTPS, survive ordinary instance failures, and support deployment without routinely interrupting customers.

The team consists of four engineers.

Traffic is moderate, with occasional peaks.

The company has no dedicated Kubernetes platform team.

Our first architecture should therefore be relatively simple.

Conceptually, the system contains a public website, an API, a relational database, an asynchronous work channel, workers, and object storage:

```text
Customer's browser
       |
       v
  HTTPS / CDN
       |
       +------> Static frontend assets
       |
       v
   Public API
       |
       +------> PostgreSQL
       |
       +------> Queue ------> Worker
       |
       +------> Object storage

Logs, metrics, traces, permissions,
secrets, backups, and deployment tools
support the whole system.
```

Notice what is absent from this diagram.

There is no requirement for microservices.

There is no requirement for Kubernetes.

There is no requirement for a particular cloud provider.

We're describing what the system needs before deciding how to rent those capabilities.

## 2. The compute spectrum: machines, platforms, containers, and functions

The most visible cloud decision concerns where application code runs.

But there are several distinct operating models.

### Virtual machines

A virtual machine gives us control over a guest operating system and its software environment.

On AWS, a familiar choice is **Amazon EC2**.

On Google Cloud, it is **Compute Engine**.

On Azure, it is **Azure Virtual Machines**.

All three provide cloud-hosted virtual machines, although their networking, identity, image, and management details differ.

A virtual machine is attractive when we need control over the operating system, specialized software, or a specific runtime environment.

But we also inherit responsibility for more of the system.

We need to consider OS updates, service supervision, deployment, instance replacement, capacity, and configuration.

For a small conventional SaaS, that operational work may be unnecessary.

### Managed application and container platforms

Now suppose we package the Node.js API into a container.

We'd like to give the provider the image, resource requirements, environment configuration, and networking policy.

Then we want the provider to execute it without requiring us to maintain virtual machines directly.

This category includes several related but not identical services.

On AWS, we could use **Amazon ECS with AWS Fargate**.

ECS orchestrates container workloads; Fargate provides managed compute capacity for those tasks.

On Google Cloud, **Cloud Run** is an attractive choice for HTTP services and certain job workloads.

On Azure, **Azure Container Apps** can host containerized applications while abstracting away much of the underlying infrastructure.

These services don't have identical execution models, scaling behavior, or networking contracts.

They're useful comparisons because they reduce the amount of infrastructure the application team must manage.

### Managed Kubernetes

Another possibility is Kubernetes.

AWS provides EKS.

Google Cloud provides GKE.

Microsoft provides AKS.

These platforms manage significant parts of Kubernetes infrastructure, but the application team still has to understand and configure workloads, networking, resources, security, and operational behavior.

Kubernetes is powerful when its orchestration model is genuinely useful.

But a small company with one API and two workers doesn't automatically need a Kubernetes cluster.

Our dedicated SE450 course explains the platform more deeply.

### Functions as a Service

Another option is executing code in response to events.

AWS Lambda and Azure Functions are familiar examples.

Google Cloud offers function-oriented execution through its Cloud Run ecosystem.

These models can be convenient for event-triggered tasks, transformations, and workloads with intermittent demand.

But choosing functions introduces their own constraints around execution lifecycle, state, concurrency, time limits, and integrations.

A function isn't necessarily a natural replacement for every long-running backend process.

### What would I choose for Mercury?

For the first production version, I'd seriously consider managed container hosting for the API and suitable workers.

It supports a conventional containerized application without introducing Kubernetes cluster ownership.

I wouldn't choose it because containers are fashionable.

I'd choose it because the application is already packaged this way and the team wants a manageable operational footprint.

## 3. Regions, zones, and failure boundaries

Now Mercury must select a region.

A region is a geographical area in which a provider offers infrastructure.

Availability zones typically represent separate infrastructure failure domains within a region, although the exact definitions and architecture vary among providers.

A deployment in one region with multiple failure-isolated instances can tolerate certain local failures.

But it cannot automatically tolerate every regional failure.

### The database question

Suppose Mercury has two API instances across two availability zones, but PostgreSQL is running in a nonredundant configuration in just one zone.

If that database becomes unavailable, both API instances may lose the ability to process reservations.

Adding API replicas didn't remove the database dependency.

The database's high-availability configuration matters independently.

And high availability doesn't mean the same thing as disaster recovery.

A standby may help the system recover from an instance failure.

It doesn't automatically protect against accidental deletion, corrupt application writes, or the need to restore an earlier consistent state.

### Don't overbuild on day one

The opposite mistake is deploying a complicated multi-region architecture before the product has meaningful traffic.

Multiple regions introduce data replication, consistency, failover, networking, deployment, and cost questions.

The correct availability design follows the business requirements.

Mercury should first define which failures it must survive and what recovery times are acceptable.

Then it should select the infrastructure necessary to meet those objectives.

## 4. Networks: public access and private dependencies

Our customer must reach the API over HTTPS.

But should every database and worker also be accessible from the public internet?

No.

A conventional design exposes a controlled entry point while restricting internal dependencies.

For example, public traffic may enter through a load balancer or managed service ingress.

The API then accesses PostgreSQL through suitable private connectivity and permissions.

The database doesn't need to accept arbitrary inbound traffic from the internet.

### Similar concepts, different networking models

AWS uses Virtual Private Clouds, or VPCs, with subnets, routing, and security controls.

Google Cloud also uses VPCs, but its VPC networks have different scope and subnet semantics from AWS's model.

Azure uses Virtual Networks, often abbreviated VNets, and associated network security and routing components.

Don't assume every product named "VPC" behaves identically.

At an interview, it's more valuable to explain the security requirement correctly:

"The API needs inbound access from the authorized public entry point and outbound connectivity to its database and other dependencies. The database should not be publicly reachable without a justified requirement."

Then discuss the provider-specific implementation.

### The outbound connectivity trap

Private application workloads may still need to contact external services.

Mercury's API calls payment providers and supplier systems.

Depending on the platform and network design, outbound internet access may require specific routing or managed network components.

Those components may have their own charges, availability characteristics, and operational constraints.

An application that can accept requests but cannot reach its payment provider isn't functioning correctly.

Network design must account for both incoming and outgoing dependencies.

## 5. Identity: who can perform cloud operations?

Networking answers which systems can communicate.

Identity and access management answers which principals are authorized to perform particular operations.

These are related but separate questions.

Suppose Mercury's API needs to upload an invoice to object storage.

A poor approach is embedding a powerful administrator access key in an environment variable.

A better approach is assigning the runtime an appropriate identity with the permissions required for that operation.

### Across providers

AWS uses IAM roles and policies.

Google Cloud uses IAM together with service identities, including service accounts.

Azure uses its identity and role-based access-control mechanisms, including managed identities for eligible workloads.

The naming differs, but the core principle is consistent.

The application should obtain an identity appropriate to its environment.

That identity should have only the permissions the workload actually needs.

### Least privilege in practice

The invoice service needs permission to write invoices to a designated storage location.

It doesn't need unrestricted access to every object storage bucket in the organization.

The worker that sends email notifications doesn't need to delete the production database.

The staging application shouldn't automatically have the same access as production.

Managed identity systems make credential management easier, but configuring permissions remains our responsibility.

This is a central example of shared responsibility.

The provider supplies the identity machinery.

We decide which permissions to grant.

## 6. Managed PostgreSQL: outsourcing operations, not data correctness

Mercury needs relational transactions.

Its reservation workflow has complex constraints.

So a managed PostgreSQL service is an attractive choice.

AWS offers PostgreSQL through Amazon RDS and related managed database options.

Google Cloud offers PostgreSQL through Cloud SQL and other database products with different capabilities.

Azure provides Azure Database for PostgreSQL.

These services reduce infrastructure-management work.

But they don't make databases infinitely scalable.

### The connection-pool surprise

Imagine Mercury's API currently runs two container instances.

Each maintains a database connection pool of twenty connections.

Now traffic increases and the cloud platform scales the API to thirty instances.

The theoretical aggregate application pool capacity has increased from forty connections to six hundred.

Did the database automatically acquire enough capacity to handle them?

Not necessarily.

The compute platform scales one part of the system.

The database has its own limits.

A production design must consider connection pooling, concurrency, query cost, transaction duration, and scaling behavior.

This is particularly important with highly elastic compute.

### Backups aren't a checked checkbox

Managed databases usually provide configurable backup and recovery capabilities.

But Mercury must still decide how much data loss is acceptable and how quickly service must be restored.

These are commonly described through the Recovery Point Objective and Recovery Time Objective.

The company should test recovery rather than merely assume the provider's backup configuration guarantees its business requirements.

And no managed backup system prevents the application from committing logically incorrect transactions.

## 7. Object storage: files are not database rows

Mercury stores photographs and generated invoices.

Should we store every file directly on the API container's local filesystem?

Usually not for a replicated, replaceable application.

A container instance may be restarted, replaced, or scaled down.

Local instance storage is not automatically durable shared storage.

A common choice is cloud object storage.

AWS offers S3.

Google Cloud offers Cloud Storage.

Azure offers Blob Storage.

These services store objects identified by keys or names and associated metadata.

They're suitable for many photographs, documents, exports, and other large binary assets.

### The operational implications

Object storage doesn't eliminate authorization.

An invoice belonging to one customer must not become accessible to another.

Access policies, signed access mechanisms, retention, lifecycle management, and encryption configurations need deliberate design.

Nor is object storage a conventional mounted filesystem with identical semantics for every operation.

An application shouldn't assume it can edit arbitrary bytes in place the way it might modify a local file.

The deeper subject of secure uploads, streaming, cleanup, and object lifecycles belongs in SE325-L01.

For this introductory lecture, the important distinction is that **object storage and relational storage solve different kinds of persistence problems**.

## 8. Messaging: separating the request from background work

A customer confirms a booking.

The API must record the booking correctly.

Then several follow-up operations may be needed.

Send an email.

Notify a supplier.

Update a reporting system.

Generate an invoice.

Some of these operations shouldn't delay the customer's HTTP response.

A queue or messaging service can separate the immediate request from asynchronous processing.

AWS provides SQS, SNS, and EventBridge for different messaging and event-integration patterns.

Google Cloud offers services such as Pub/Sub and Cloud Tasks.

Azure offers Service Bus and Event Grid.

These names appear comparable, but the messaging models differ.

### Queue versus publish-subscribe

Imagine the booking system wants one worker from a pool to process a notification job.

A work queue is a natural abstraction.

Now imagine several independent systems must each receive information about the booking.

An event publication or publish-subscribe model may be more suitable.

The distinction isn't always reflected neatly in one-to-one service-name comparisons.

For example, Google Cloud Pub/Sub and Azure Service Bus support messaging patterns with different delivery and subscription semantics.

AWS often uses combinations of services depending on the architecture.

We should choose a messaging pattern first, then identify the provider service that implements it.

### The important warning

A managed queue does not make a business operation exactly-once.

Messages may be retried or delivered more than once according to service semantics.

Workers still need durable operation identities, idempotent behavior where applicable, and appropriate handling of partial failure.

Our SE320-L03 and CS430 lectures explore these mechanisms in depth.

## 9. The three cloud implementations of Mercury

We now have enough concepts to sketch our application on the three major providers.

### AWS implementation

A plausible AWS architecture might use:

- Amazon S3 and CloudFront for suitable static frontend assets.
- An Application Load Balancer in front of an ECS service running on Fargate.
- Amazon RDS for PostgreSQL.
- Amazon SQS for background work.
- ECS tasks or other suitable compute for workers.
- IAM roles, a secrets-management service, and CloudWatch for supporting capabilities.

The application needs appropriate networking, TLS, access controls, high-availability settings, and deployment configuration.

This is one possible AWS architecture, not the only one.

Our existing SE340-L03 covers the AWS-specific components in much greater detail.

### Google Cloud implementation

A plausible Google Cloud architecture might use:

- Cloud Storage with suitable frontend hosting and CDN configuration.
- Cloud Run for the containerized API.
- Cloud SQL for PostgreSQL.
- Cloud Tasks for task-oriented asynchronous work, or Pub/Sub where its messaging model fits.
- Cloud Run jobs or services for suitable workers.
- IAM, Secret Manager, Cloud Logging, and Cloud Monitoring for supporting capabilities.

Network access to managed databases and private dependencies must be configured according to the selected services.

Cloud Run isn't literally ECS with a different logo.

It has its own execution, scaling, and networking model.

But it can solve a similar application-hosting problem.

### Azure implementation

A plausible Azure architecture might use:

- Blob Storage and an appropriate CDN or frontend-delivery service.
- Azure Container Apps for the containerized API.
- Azure Database for PostgreSQL.
- Azure Service Bus for suitable asynchronous messaging.
- Container Apps jobs or another appropriate service for workers.
- Managed identities, Key Vault, and Azure Monitor for supporting capabilities.

Azure also offers App Service and Azure Functions, among other compute choices.

The best combination depends on the workload rather than a requirement to mirror another cloud provider exactly.

### The useful comparison

Across all three implementations, our logical architecture barely changes.

We still have a frontend, API, database, workers, messages, and object storage.

The services implementing those responsibilities change.

Their configuration and operational contracts also change.

This is the right level of abstraction for someone learning the cloud ecosystem.

## 10. Why portability is harder than changing service names

Suppose Mercury decides to move from AWS to Google Cloud.

The application is containerized.

Does that make the migration trivial?

No.

The container may run on both platforms, but the surrounding system depends on cloud services.

How does the application obtain credentials?

How does it reach PostgreSQL?

How are secrets injected?

How are messages delivered and acknowledged?

How is external traffic routed?

How are logs collected?

How is the application scaled?

How are deployments managed?

The interfaces differ.

Some differences can be hidden behind application adapters or infrastructure tooling.

Others influence architecture and operations.

### Containers help, but don't solve everything

A portable container image is useful.

It reduces environment differences.

But the container still depends on networking, storage, permissions, and runtime configuration.

Kubernetes can provide a common orchestration API across providers, but operating Kubernetes introduces its own complexity and doesn't make managed databases, queues, or identity systems interchangeable.

### Avoid portability theater

Some teams introduce elaborate abstraction layers to avoid hypothetical vendor lock-in.

They create a universal cloud interface that exposes only the lowest common denominator of every provider.

Then they struggle to use the features they actually selected the cloud service for.

A more pragmatic approach is to identify the dependencies that would be expensive to replace.

Keep business logic reasonably separate from provider integrations.

Use well-understood protocols and formats where appropriate.

Document important assumptions.

But don't pay enormous complexity costs to prepare for a migration that may never happen.

Portability is a business trade-off, not an unconditional architectural virtue.

## 11. The cloud bill is part of the architecture

Mercury's application works.

The CTO is happy.

Then the first large infrastructure bill arrives.

Why is it so expensive?

Several possibilities.

The team provisioned a managed database significantly larger than necessary.

It configured redundant environments that are never used.

Container instances remain running when demand is low.

Cross-region traffic generates unexpected transfer charges.

Private networking components incur fixed or usage-based fees.

Logs are retained at high volume.

Background workers retry excessively.

Object storage retains abandoned exports.

Or an API endpoint causes expensive database operations during traffic spikes.

The cloud bill reflects the actual services, resources, and traffic patterns the architecture uses.

### Serverless isn't automatically cheap

Managed functions or containers can reduce idle infrastructure costs under suitable workloads.

But pricing models vary.

Some services charge for execution, provisioned resources, requests, networking, or minimum allocated capacity.

At sustained utilization, a different compute model may be more economical.

The correct approach is to estimate the workload and compare the relevant cost models.

Not to assume that "serverless" means inexpensive or that virtual machines are always cheaper.

### Cost and reliability interact

Adding redundancy costs money.

Reducing capacity can increase failure risk.

Running everything in one region may be economical but expose the system to certain failure scenarios.

The business must decide which risks are worth paying to reduce.

Engineering should make those trade-offs visible.

## 12. The most common cloud misconception

Let's return to our original requirement.

Mercury wants a reliable booking application.

A consultant proposes an architecture with several managed services, automatic scaling, multiple availability zones, and sophisticated infrastructure.

It sounds reliable.

But imagine one badly written API endpoint performs an expensive database operation.

Traffic increases.

The platform automatically launches more application instances.

They all send expensive queries to PostgreSQL.

Database performance collapses.

Requests time out.

Clients retry.

The queue grows.

More workers activate.

The system now applies even more pressure to its constrained dependencies.

Every cloud service is doing approximately what it was configured to do.

The application is still failing.

This is why the cloud must be understood as an infrastructure platform rather than a correctness guarantee.

It gives us mechanisms.

Our engineering decisions determine how those mechanisms interact.

## 13. How to approach a new cloud provider

Imagine tomorrow you join a company that uses Google Cloud instead of AWS.

You know AWS reasonably well, but you haven't operated Google Cloud professionally.

Should you panic?

No.

Start with your existing mental model.

Find the platform's compute options.

Identify its virtual networking structure.

Understand how workloads acquire identity.

Find the managed databases and their connectivity requirements.

Examine its messaging services.

Learn where logs, metrics, and traces appear.

Understand how deployment and configuration work.

Then investigate the provider-specific limits and failure modes relevant to your application.

You don't need to memorize the entire service catalogue.

You need to recognize the categories and know which details require investigation.

### A senior interview answer

Suppose an interviewer asks:

"Would you deploy this application on AWS or GCP?"

A weak response is to pick the provider whose product names you remember.

A better response is:

"I'd first establish the workload, operational constraints, regional requirements, existing team expertise, and managed services we need. A conventional containerized API with PostgreSQL and background jobs can be deployed on either platform. I'd compare the specific compute and database options, networking and IAM requirements, reliability guarantees, and costs. I wouldn't introduce Kubernetes or multi-region architecture without a requirement that justifies the added complexity."

That's not evading the question.

It's showing that you understand the decision.

You can then choose a concrete architecture once the assumptions are clear.

---

# The Oral Examination

Answer aloud before reading the solutions.

### Question 1 — IaaS versus managed platforms

What operational responsibilities does a team generally retain when deploying its application to a cloud VM? Which may be delegated when using a managed container platform?

### Question 2 — Shared responsibility

A managed PostgreSQL service performs automated backups. Does that mean the application team no longer needs to think about data loss or recovery?

### Question 3 — Scaling

An API's container platform scales from two instances to thirty. PostgreSQL begins timing out. Why might this happen?

### Question 4 — Networking and permissions

An API needs to write private invoices to object storage. What two distinct questions do network configuration and identity permissions answer?

### Question 5 — AWS, GCP, Azure

Name a plausible managed hosting option for a containerized HTTP API on each of the three providers.

### Question 6 — Messaging

Why shouldn't you assume SQS, Pub/Sub, and Service Bus are exactly equivalent products?

### Question 7 — Portability

Your application uses Docker. Does that make a migration between cloud providers straightforward?

### Question 8 — Choosing a provider

What information would you gather before selecting the cloud architecture for a new SaaS?

---

# Solutions and Discussion

## Solution 1 — Ownership of the runtime

With a cloud VM, the team generally manages more of the guest OS, installed software, deployment lifecycle, security configuration, and application capacity.

A managed container platform delegates more of the underlying infrastructure and execution orchestration, but the team still owns application correctness, configuration, security choices, resource behavior, and relevant operational requirements.

## Solution 2 — Backups are a mechanism

The application team still needs retention decisions, recovery objectives, restoration testing, and protection against incorrect application writes.

The provider supplies capabilities under specific service configurations. The team remains responsible for ensuring those capabilities satisfy the business requirements.

## Solution 3 — Independent scaling limits

Scaling the API can multiply database connections and concurrent queries.

PostgreSQL doesn't automatically scale with the API's number of instances.

Connection pools, workload admission, query efficiency, database capacity, and backpressure must be considered.

## Solution 4 — Connectivity versus authority

Networking determines which destinations are reachable through configured routes and security boundaries.

Identity and access permissions determine whether a principal is authorized to perform an operation.

Both matter, and neither automatically replaces the other.

## Solution 5 — Plausible compute choices

AWS: ECS with Fargate.

Google Cloud: Cloud Run.

Azure: Azure Container Apps.

These aren't feature-identical services. They are examples of platforms that can host suitable containerized applications while reducing server-management work.

## Solution 6 — Messaging semantics differ

The services provide different abstractions for queues, subscriptions, event distribution, delivery, acknowledgment, and integration.

Choose the required messaging behavior first.

Then examine which provider service implements it appropriately.

## Solution 7 — Containers solve only part of portability

The image may be portable, but the application still relies on identities, networking, storage, queues, monitoring, deployment systems, and provider-specific integrations.

Those dependencies can make migration expensive.

## Solution 8 — Decide from requirements

Investigate the workload, traffic, data model, consistency requirements, geographic needs, security and regulatory constraints, reliability targets, operational expertise, expected growth, and cost.

Only then select services.

---

# The Mental Model Worth Keeping

Cloud computing is a marketplace of programmable infrastructure and managed capabilities.

To understand any cloud service, ask:

**What capability does it provide?**

**Which responsibilities does it take away from my team?**

**Which responsibilities remain ours?**

**What are its scaling limits, failure modes, and cost model?**

And when comparing AWS, Google Cloud, and Azure, remember:

**Equivalent architectural roles do not imply identical product behavior.**

Choose the architecture for the application first.

Then choose the cloud services that implement it.

# Next Lecture — SE215-L06: DevOps, Platform Engineering, and Operational Ownership

Our Mercury application now has a cloud architecture.

But who actually maintains it?

The developers say they write application code.

The platform team provides infrastructure.

The security team defines policies.

The SRE team monitors production.

Then an application deployment fails because its readiness check reports success while its database migrations are still incompatible.

Every team claims its individual component behaved correctly.

Who owns the failure?

Next we'll examine how DevOps, platform engineering, SRE, and application development fit together, and why successful software delivery requires operational responsibilities to be explicit.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Workshop — Deploy Mercury on Three Clouds

## Exercise A — Translate one logical architecture

Start with:

- A static Vue frontend.
- A containerized Node.js API.
- PostgreSQL.
- Asynchronous notification jobs.
- Python workers.
- Object storage for invoices.
- Centralized logs and metrics.
- Workload identities and secret management.

Produce three possible service maps.

| Capability | AWS example | Google Cloud example | Azure example |
|---|---|---|---|
| Virtual machine | EC2 | Compute Engine | Virtual Machines |
| Managed API containers | ECS + Fargate | Cloud Run | Container Apps |
| Kubernetes | EKS | GKE | AKS |
| Managed PostgreSQL | RDS for PostgreSQL | Cloud SQL for PostgreSQL | Azure Database for PostgreSQL |
| Object storage | S3 | Cloud Storage | Blob Storage |
| Queue/task processing | SQS | Cloud Tasks | Service Bus |
| Event distribution | SNS / EventBridge | Pub/Sub | Service Bus topics / Event Grid |
| Virtual networking | VPC | VPC | Virtual Network |
| Workload identity | IAM roles | Service accounts / IAM | Managed identities / Azure RBAC |
| Observability | CloudWatch | Cloud Logging / Monitoring | Azure Monitor |

**Important:** The entries indicate comparable capability categories, not perfect feature equivalence. Implementations differ in topology, limits, authentication, delivery semantics, and cost.

For each provider, explain the likely application deployment path.

What is built?

Where is the image stored?

What runs the image?

How does traffic arrive?

How does it reach PostgreSQL?

How does background work start?

Where do errors and metrics appear?

## Exercise B — The architecture review

Mercury receives the following proposal:

```text
Customer
   |
   v
Public Load Balancer
   |
   v
API Containers — autoscale to 100 instances
   |
   +------ PostgreSQL (single instance)
   |
   +------ Queue
              |
              v
         100 Workers
```

The consultant claims the application will support almost any traffic spike because the API and workers scale automatically.

Identify at least five concerns before approving this architecture.

Consider:

1. Database connection pressure.
2. Database capacity and high availability.
3. Worker concurrency and downstream limits.
4. Retry amplification and backpressure.
5. Load testing and scaling policies.
6. Security and network boundaries.
7. Monitoring and cost controls.

You don't need to reject autoscaling.

You need to explain what autoscaling can and cannot guarantee.

## Exercise C — Shared responsibility matrix

For each responsibility, identify whether it primarily belongs to the cloud provider, application team, or is shared, depending on the selected service:

- Maintaining physical servers.
- Configuring the application's authorization rules.
- Fixing an SQL injection vulnerability.
- Choosing database backup retention.
- Implementing database backups according to the selected managed-service configuration.
- Writing correct booking transactions.
- Configuring workload identity.
- Applying guest OS security patches on a self-managed VM.
- Choosing safe application scaling limits.
- Investigating duplicate payment operations.

Then repeat the exercise for a managed platform instead of a VM.

Observe how some operational responsibilities move while business correctness remains with the application team.

## Exercise D — The cloud cost surprise

A small SaaS has unexpectedly high cloud costs.

You discover:

- An oversized database.
- Idle staging environments.
- Large volumes of retained logs.
- Repeatedly generated but never deleted export objects.
- An expensive outbound network path.
- Background workers that retry failed jobs aggressively.

Rank the likely investigation areas, specifying what measurements you'd request before proposing changes.

Do not assume every cost should be eliminated.

A redundant database or additional capacity may be justified by reliability requirements.

The objective is to distinguish useful spending from waste.

## Exercise E — Senior interview rehearsal

Answer in two or three minutes:

"We're building a SaaS with a React frontend, Node.js backend, PostgreSQL, and some background workers. Which cloud provider and services would you recommend?"

A strong answer should:

- Clarify workload and operational requirements.
- Select one reasonable provider and concrete architecture.
- Explain why the chosen hosting model fits the team.
- Discuss network and identity boundaries.
- Identify database and worker scaling limitations.
- Address backup, monitoring, deployment, and cost.
- Acknowledge viable alternatives without turning the answer into an endless catalogue.

**Do not evade the decision indefinitely.** Clarify assumptions, make a recommendation, and defend it.

---

# Further Reading

Official architecture and service-selection references:

- **AWS — Decision Guides:** https://docs.aws.amazon.com/decision-guides/
- **AWS — Choosing a Serverless Service:** https://docs.aws.amazon.com/decision-guides/latest/decision-guides/choosing-aws-serverless-service.html
- **AWS — Shared Responsibility:** https://aws.amazon.com/compliance/shared-responsibility-model/
- **Google Cloud — Choosing Compute Options:** https://docs.cloud.google.com/docs/compute-area/choose-compute-options
- **Google Cloud — Cloud Run:** https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run
- **Google Cloud — Architecture Center:** https://cloud.google.com/architecture
- **Microsoft Azure — Choosing a Compute Service:** https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/compute-decision-tree
- **Microsoft Azure — Architecture Center:** https://learn.microsoft.com/en-us/azure/architecture/
- **Microsoft Azure — Shared Responsibility:** https://learn.microsoft.com/en-us/azure/security/fundamentals/shared-responsibility

Related programme chapters:

- SE215-L04 — Repositories, Monorepos, and Build Systems
- SE215-L06 — DevOps, Platform Engineering, and Operational Ownership
- SE340-L02 — Containers and Modern Deployment
- SE340-L03 — Cloud Infrastructure and AWS Architecture
- SE340-L04 — CI/CD and Infrastructure as Code
- SE440-L02 — Reliability Engineering and Incident Response
- SE450 — Kubernetes and Platform Engineering
- CS430-L03 — Scaling and Load Management

---

## Dense Cheatsheet — Interview Glance Card

*Fenced for voice readers; use as a screen-based revision reference.*

```text
SE215-L05 — CLOUD PLATFORMS AND SERVICE MODELS

CORE MODEL
  Cloud = programmable infrastructure + managed capabilities
  Provider manages selected layers
  Customer retains application and business responsibility

SERVICE MODELS
  IaaS       Virtual machines, networks, infrastructure control
  PaaS       Managed application/runtime platform
  FaaS       Event-triggered function execution
  SaaS       Complete software service consumed by customers
  Serverless Means server management is abstracted;
             not absence of servers or operational limits

COMPUTE
  AWS        EC2 | ECS/Fargate | EKS | Lambda
  GCP        Compute Engine | Cloud Run | GKE
  Azure      VMs | Container Apps/App Service | AKS | Functions

DATABASES
  AWS        RDS PostgreSQL
  GCP        Cloud SQL PostgreSQL
  Azure      Azure Database for PostgreSQL

OBJECT STORAGE
  AWS        S3
  GCP        Cloud Storage
  Azure      Blob Storage

MESSAGING
  AWS        SQS, SNS, EventBridge
  GCP        Cloud Tasks, Pub/Sub
  Azure      Service Bus, Event Grid
  No automatic 1:1 semantics across products

NETWORK
  AWS        VPC, subnets, routes, security groups
  GCP        VPC, regional subnets, firewall policies
  Azure      VNet, subnets, NSGs, routing
  Public entry point != public database access
  Consider outbound connectivity and costs

IDENTITY
  AWS        IAM roles and policies
  GCP        IAM and service accounts
  Azure      Managed identities and Azure RBAC
  Network reachability != authorization
  Prefer workload identity over embedded static credentials

OBSERVABILITY
  AWS        CloudWatch
  GCP        Cloud Logging / Monitoring
  Azure      Azure Monitor
  Application must expose business-relevant signals

SHARED RESPONSIBILITY
  Provider: physical infrastructure, selected managed operations
  Customer: code, configuration, permissions, data governance,
            application security, business correctness
  Exact boundary depends on service model

REGIONS / ZONES
  Region = geographical infrastructure area
  Zones = failure-isolation arrangements within regions
  Multiple API instances != resilient database
  High availability != backups != disaster recovery

SCALING
  Autoscaling one component can overload another
  API replicas multiply connection-pool demand
  Queues buffer work but don't create infinite throughput
  Quotas and dependency capacity still apply
  Always consider backpressure

CLOUD COSTS
  Compute runtime, databases, storage, data transfer,
  networking, logs, replicas, idle environments
  Serverless != automatically cheapest
  Reliability may justify extra spending
  Measure before optimizing

PORTABILITY
  Containers help portability
  Runtime identity/network/storage/messaging still differ
  Managed platforms are not drop-in equivalents
  Kubernetes standardizes some orchestration, not all cloud APIs
  Avoid unnecessary provider abstraction

PRACTICAL DEFAULT FOR A SMALL SAAS
  Static frontend + CDN
  Managed container API
  Managed PostgreSQL with appropriate HA
  Queue + managed worker execution
  Object storage
  Workload identities and secret management
  Central observability and controlled deployments

INTERVIEW DECISION SEQUENCE
  1. Clarify application and traffic
  2. Identify data and correctness requirements
  3. Establish regions, security, reliability targets
  4. Assess team operational expertise
  5. Choose compute and persistence
  6. Design connectivity and identity
  7. Design asynchronous work
  8. Explain scaling and failure limits
  9. Estimate cost and operational burden
  10. Make and defend a concrete recommendation

MENTAL MODEL
  What capability am I buying?
  Which work does the provider assume?
  Which obligations remain ours?
  What can fail, saturate, or become expensive?
```
