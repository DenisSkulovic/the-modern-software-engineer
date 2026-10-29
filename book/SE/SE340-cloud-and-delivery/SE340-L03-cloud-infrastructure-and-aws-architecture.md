---
id: SE340-L03
course: SE340
title: "Cloud Infrastructure and AWS Architecture"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [ENG401-S05]
prev: SE340-L02
next: SE340-L04
---

<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE215-L05
Keep this as the detailed AWS architecture chapter.
After SE215-L05 is authored, cross-reference it for the AWS/GCP/Azure conceptual comparison.
Do not duplicate the AWS-specific service explanations in the new survey lecture.
-->










# SE340 — Linux, Cloud Infrastructure, and Delivery

## Lecture 03: Cloud Infrastructure and AWS Architecture

*How the cloud made computing resources elastic, infrastructure programmable, and architectural mistakes spectacularly scalable.*

---

## 1. The Serverless Application That Scaled Itself to Death

Your company operates a hotel-booking SaaS built primarily on AWS.

Its backend uses API Gateway, Lambda functions, PostgreSQL on Amazon RDS, S3, and several background workers. Traffic is moderate, deployments are uncomplicated, and the infrastructure rarely requires manual intervention.

One afternoon, an influential travel website recommends the product.

Traffic increases from 50 requests per second to 1,500.

AWS Lambda responds magnificently. Instead of overwhelming a single application server, the platform creates additional execution environments to handle the increasing demand.

CPU capacity is available. API Gateway continues receiving requests. Lambda scales within its configured quotas.

And then PostgreSQL collapses.

Database connections multiply, response times increase, queries begin timing out, and the API starts returning errors. Hundreds of Lambda executions sit waiting for database connections while additional requests continue arriving.

The application has successfully scaled its compute layer far beyond the capacity of its persistence layer.

The engineers had assumed that because Lambda scales automatically, the application would scale automatically.

They had confused the scalability of one component with the scalability of the system.

This distinction is fundamental to cloud architecture.

**The cloud makes infrastructure resources easier to acquire. It does not eliminate the constraints governing those resources or the dependencies between them.**

To understand why, we'll build an AWS environment from the ground up—not by memorizing a catalog of services, but by examining which engineering responsibilities each service addresses.

---

## 2. What Cloud Computing Actually Changes

Before cloud platforms became widespread, deploying a production application often required purchasing or renting physical servers.

An organization needed to estimate capacity, procure hardware, configure networking, install operating systems, arrange storage, and maintain the infrastructure over time.

The difficulty wasn't merely financial. Capacity planning required predicting future demand before the infrastructure existed.

Buying too little meant poor performance during growth. Buying too much meant paying for machines that remained largely idle.

Cloud computing changes the acquisition and management model.

Instead of purchasing physical infrastructure, engineers request computing resources through software interfaces.

A virtual server can be provisioned through an API. Storage capacity can expand without installing disks. A managed database can be created from configuration, and an additional application instance can be started automatically when demand increases.

Three characteristics are particularly important:

**On-demand provisioning:** Resources can be requested and released programmatically.

**Elasticity:** Allocated capacity can increase or decrease in response to demand, within service limits and available capacity.

**Managed infrastructure:** The provider can assume responsibility for selected operational tasks.

However, *managed* is not synonymous with *fully managed*, and *serverless* does not literally mean there are no servers.

Someone still operates physical computers. The question is which responsibilities belong to AWS and which remain with your engineering team.

### The spectrum of responsibility

Consider three deployment models.

| Model | You primarily manage | Provider primarily manages |
|---|---|---|
| EC2 virtual machine | OS, runtime, application, deployment, patching | Physical infrastructure and virtualization |
| ECS with Fargate | Container image, application, task configuration, deployment | Underlying compute hosts and container execution infrastructure |
| Standard Lambda functions | Function code, configuration, dependencies, application behavior | Execution environments, scaling infrastructure, supported runtime operations |

All three still require application security, monitoring, correct data handling, and suitable capacity planning.

Moving from EC2 to Lambda reduces certain infrastructure responsibilities. It also reduces control over the execution environment and introduces a different set of operational constraints.

A service abstraction transfers work; it doesn't make that work irrelevant.

---

## 3. Regions and Availability Zones: Geography Becomes Architecture

Suppose your European SaaS operates primarily from AWS's Frankfurt Region.

AWS organizes much of its infrastructure geographically into **Regions**, each containing multiple **Availability Zones**, or AZs.

An Availability Zone represents one or more physically separate data centers with independent infrastructure characteristics, interconnected with other AZs through high-performance networking.

Conceptually:

```text
AWS Region: eu-central-1
             │
     ┌───────┼────────┐
     ▼       ▼        ▼
    AZ-A    AZ-B     AZ-C
     │       │        │
    App     App      App
```

The essential idea is the **failure domain**.

If all your application instances run in one AZ, a significant disruption affecting that AZ may render the application unavailable.

Distributing instances across multiple AZs reduces exposure to a single-zone failure.

But there is a catch.

### Multi-AZ applications can still have single points of failure

Consider:

```text
       Application Load Balancer
              /       \
             ▼         ▼
          App A       App B
           AZ-A        AZ-B
             \         /
              ▼       ▼
           PostgreSQL
              AZ-A
```

The application tier is distributed, but the database remains a single point of failure.

A managed RDS Multi-AZ configuration can maintain a standby or multiple database instances, depending on the selected deployment model, to support failover.

However, even a Multi-AZ database does not make the entire architecture immune to outages, incorrect schema migrations, corrupted data, or regional service disruptions.

A Region-wide failure is a different scenario from an AZ failure. Multi-region disaster recovery introduces additional complexity involving replication, routing, consistency, and data residency.

For many SaaS companies, one carefully designed region with multi-AZ resilience is a sensible starting point.

Deploying across three continents merely because AWS makes it possible is not automatically good engineering.

---

## 4. VPC: Building a Private Network Inside AWS

Now imagine creating several EC2 instances, a database, and application containers.

How do they communicate? Which resources can reach the internet? Which can accept incoming connections from customers?

AWS provides **Virtual Private Cloud**, or VPC, as a fundamental networking abstraction.

A VPC defines a logically isolated network environment with address ranges, subnets, routing, and network-security controls.

Imagine assigning the VPC:

```text
10.20.0.0/16
```

This CIDR block represents an IPv4 address range containing 65,536 addresses, although subnet reservations and practical allocation constraints reduce what individual workloads can use.

We subdivide the network:

```text
VPC: 10.20.0.0/16

Public subnet A:   10.20.1.0/24
Public subnet B:   10.20.2.0/24

Private app A:     10.20.11.0/24
Private app B:     10.20.12.0/24

Private data A:    10.20.21.0/24
Private data B:    10.20.22.0/24
```

Each subnet belongs to one Availability Zone.

The distinction between public and private is especially important.

### What makes a subnet public?

A public subnet has a route to an internet gateway for the relevant IP protocol.

For IPv4, a typical route is:

```text
Destination      Target

10.20.0.0/16     local
0.0.0.0/0        internet-gateway
```

The first route handles traffic within the VPC.

The second routes other IPv4 destinations toward the internet gateway.

But a route alone does not make an individual EC2 instance publicly reachable. For ordinary IPv4 connectivity, that instance also needs appropriate public addressing and security rules.

A private subnet typically lacks a direct route to the internet gateway.

This doesn't necessarily prevent outbound internet access.

### NAT gateways and outbound connectivity

Suppose application containers run in private subnets but need to contact an external hotel supplier's API.

They need outbound network access without requiring public inbound reachability.

For ordinary IPv4 egress, a NAT gateway can provide this capability.

```text
Private Application
        │
        ▼
    NAT Gateway
        │
        ▼
  Internet Gateway
        │
        ▼
 External Supplier
```

The private application's route table sends relevant outbound traffic toward the NAT gateway.

The NAT service translates the connection's source addressing so replies can return through the established connection.

A NAT gateway is not an inbound reverse proxy.

It doesn't ordinarily allow arbitrary internet clients to initiate connections to your private application.

### The financial surprise

Managed NAT gateways can be a meaningful recurring expense, including hourly resource charges and data-processing charges.

A small application that uses very little compute may still accumulate a noticeable networking bill if its architecture includes multiple NAT gateways and substantial traffic through them.

For high-availability designs, architects also consider the failure domain of the NAT gateways and whether traffic unnecessarily crosses AZ boundaries.

Some AWS services can be reached through VPC endpoints instead, potentially avoiding NAT for those particular destinations.

This creates an important distinction:

**Network topology is simultaneously a security decision, an availability decision, and a cost decision.**

---

## 5. Security Groups: A Programmable Network Firewall

Let's say the application tier must connect to PostgreSQL on port 5432.

We could expose PostgreSQL broadly and trust database authentication.

That would be a poor default.

Instead, AWS security groups allow us to control network traffic associated with supported resources.

Consider three security groups:

```text
SG-LOAD-BALANCER
  Inbound:
    HTTPS 443 from allowed clients

SG-APPLICATION
  Inbound:
    TCP 3000 from SG-LOAD-BALANCER

SG-DATABASE
  Inbound:
    TCP 5432 from SG-APPLICATION
```

This creates a deliberate network boundary:

```text
Internet
   │
 HTTPS
   ▼
Load Balancer
   │
 Port 3000
   ▼
Application
   │
 PostgreSQL 5432
   ▼
Database
```

Notice that the database rule refers to the application's security group rather than maintaining a fixed list of application IP addresses.

This is especially useful when application instances scale or are replaced.

### Security groups versus network ACLs

Security groups are stateful: permitted traffic can receive corresponding return traffic without separately authorizing the reverse direction.

Network access control lists, or NACLs, operate at the subnet boundary and are stateless, requiring appropriate rules for traffic in both directions.

For many application architectures, security groups provide the primary network-access controls. NACLs can supply additional subnet-level restrictions when justified.

Neither replaces application authorization.

Allowing a Node.js service to connect to PostgreSQL doesn't establish that its business logic should access every tenant's data.

That distinction leads to a different AWS security mechanism.

---

## 6. IAM: Who Is Allowed to Do What?

VPC security groups govern network connectivity.

**Identity and Access Management**, or IAM, governs permissions to perform AWS actions.

Suppose a Lambda function needs to upload invoices to one S3 bucket.

A poor solution is granting it broad administrative privileges.

A better solution is assigning an execution role with only the necessary permissions.

For example:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::company-invoices/*"
    }
  ]
}
```

This permits the relevant action on objects matching the specified resource ARN, subject to all other applicable policy evaluation rules.

It doesn't inherently grant permission to list all buckets, delete arbitrary objects, or administer AWS resources.

### Roles rather than embedded credentials

An application running on Lambda, EC2, or ECS can use an appropriate IAM role to obtain temporary AWS credentials.

This is substantially preferable to hardcoding long-lived access keys into application configuration.

In Node.js, the AWS SDK's default credential-provider chain can discover credentials supplied through its execution environment.

```typescript
import {
  S3Client,
  PutObjectCommand
} from "@aws-sdk/client-s3";

const s3 = new S3Client({
  region: "eu-central-1"
});

await s3.send(new PutObjectCommand({
  Bucket: "company-invoices",
  Key: "invoice-123.pdf",
  Body: pdfBuffer,
  ContentType: "application/pdf"
}));
```

The application does not need an embedded AWS access key.

The environment provides credentials associated with its authorized role.

### IAM permission evaluation

IAM is more complicated than simply checking whether a role contains an `Allow` statement.

AWS evaluates applicable policies, which can include identity-based policies, resource-based policies, permissions boundaries, organizational policies, and session policies.

Some policies grant permissions, while others constrain the maximum permissions available.

A fundamental rule is that an applicable **explicit deny overrides an allow**.

For example, an execution role might allow `s3:PutObject`, but a bucket policy could explicitly deny writes that fail to satisfy particular security requirements.

Cross-account access and policies that grant permissions directly to particular sessions introduce additional evaluation nuances.

The practical lesson is that IAM permissions must be reasoned about as an authorization system, not as a list of independent checkboxes.

### Separate network reachability from AWS authority

A Lambda function may have IAM permission to read an S3 object but lack a working network path to a required endpoint under its particular configuration.

Conversely, an EC2 instance may have network access to an S3 endpoint but lack permission to retrieve the object.

Both conditions matter.

**Connectivity answers whether a request can reach its destination. IAM answers whether the AWS operation is authorized.**

---

## 7. Choosing Compute: EC2, ECS/Fargate, or Lambda?

We've established networking and permissions.

Now we need somewhere to execute our application.

AWS offers many compute options, but three form a useful practical spectrum.

### EC2: A virtual machine under your control

Amazon EC2 provides virtual servers.

You choose an instance type, operating-system image, storage, networking, and deployment approach.

This resembles operating a Linux server from SE340-L01, except that hardware acquisition and much of the underlying virtualization are handled by AWS.

EC2 is useful when you need substantial environmental control, specialized software, predictable long-running workloads, or particular hardware configurations.

But your team retains responsibilities for OS updates, runtime configuration, deployment, instance health, and capacity management.

Auto Scaling Groups can automate instance replacement and capacity adjustments, but they don't remove the need to understand the operating system.

### ECS with Fargate: Run containers without managing hosts

Amazon Elastic Container Service, or ECS, orchestrates containerized workloads.

With Fargate, AWS manages the underlying compute capacity used to run tasks.

Your team supplies container images, task resource allocations, networking, IAM configuration, and deployment settings.

```text
Application Image
        │
        ▼
   ECS Service
        │
        ▼
   Fargate Tasks
     /       \
    ▼         ▼
 Container  Container
```

This is attractive for conventional Node.js APIs, background workers, and services that benefit from persistent processes or custom container environments.

You can scale the number of tasks, distribute them across AZs, and integrate them with load balancers.

Unlike standard Lambda functions, a Fargate task can remain active and serve many requests during its lifetime.

### Lambda: Event-driven execution

Standard AWS Lambda functions execute code in response to events.

Events may arrive from API Gateway, S3, SQS, EventBridge, and other services.

```text
HTTP Request
     │
     ▼
API Gateway
     │
     ▼
Lambda Function
     │
     ▼
DynamoDB / RDS / External API
```

Lambda handles execution-environment provisioning and scaling within configured quotas and service limits.

For standard Lambda functions, each execution environment ordinarily handles one invocation at a time, although warm environments may be reused for subsequent invocations.

Modern Lambda also includes additional execution and workflow options, but the classic event-function model remains a useful architectural baseline.

An ordinary Lambda invocation has a maximum duration of fifteen minutes. Long-running work therefore needs a different execution model or workflow design.

### Which one should you choose?

| Characteristic | EC2 | ECS/Fargate | Standard Lambda |
|---|---|---|---|
| Compute abstraction | Virtual machine | Managed container execution | Event-driven function |
| Operating-system control | High | Moderate | Limited |
| Persistent application process | Yes | Yes | Not guaranteed |
| Scaling unit | Instances | Tasks | Concurrent executions |
| Typical fit | Custom or sustained workloads | APIs and long-running workers | Short event-driven operations |
| Major responsibility retained | Host operation | Container and service configuration | Function behavior and downstream constraints |

These distinctions matter more than declaring one service universally superior.

For a small, bursty API, Lambda may offer excellent operational simplicity.

For a continuously busy Node.js service maintaining substantial connection pools and long-lived application state, Fargate may be easier to reason about or more economical.

For specialized workloads requiring deep OS control, EC2 may remain appropriate.

AWS's current compute decision guidance explicitly treats workload pattern, execution duration, concurrency, control, and pricing as factors in choosing between Lambda and Fargate.

---

## 8. API Gateway and Load Balancers: The Front Door

Suppose our hotel-booking API needs to accept HTTPS requests.

There are several possible front-door designs.

With ECS/Fargate, we might use an **Application Load Balancer**, or ALB.

```text
Client
   │
   ▼
Application Load Balancer
   │
   ├── API Task A
   ├── API Task B
   └── API Task C
```

The ALB can terminate TLS, route HTTP requests, perform health checks, and distribute traffic among registered targets.

With Lambda, API Gateway is a common entry point.

```text
Client
   │
   ▼
API Gateway
   │
   ▼
Lambda Integration
```

API Gateway offers HTTP API and REST API options with differing capabilities and pricing structures, including features relating to routing, authorization, request handling, and throttling.

### The important distinction

API Gateway isn't simply a load balancer with a more expensive name.

It provides API-management and integration capabilities, while an ALB primarily handles application-layer traffic distribution and routing.

There is some feature overlap, and either may be appropriate in particular architectures.

The choice should reflect integration requirements, authentication design, traffic patterns, operational needs, and cost.

### Throttling is not a nuisance

Suppose traffic suddenly increases tenfold.

Without admission control, every request could attempt to consume a database connection or trigger an expensive external API call.

Throttling limits the rate or concurrency at which work enters the system.

This may deliberately reject some requests, but it can protect the remaining service from complete collapse.

A controlled HTTP 429 response may be significantly better than accepting every request until all customers receive timeouts.

Cloud scalability often requires knowing when **not** to accept additional work.

---

## 9. The Lambda–PostgreSQL Trap

We can now solve the incident from our opening section.

The API normally receives 50 requests per second. Each request holds a database connection for an average of 200 milliseconds.

A rough application-level concurrency estimate follows Little's Law:

\[
L = \lambda W
\]

where:

- \(L\) is average concurrent work,
- \(\lambda\) is arrival rate,
- \(W\) is average time spent in the measured stage.

Under steady-state assumptions:

\[
L = 50 \times 0.2 = 10
\]

Approximately ten database operations would be in progress concurrently if each request uses one connection for that interval.

Now traffic rises to 1,500 requests per second:

\[
L = 1500 \times 0.2 = 300
\]

We now expect approximately 300 concurrently occupied database connections under those same assumptions.

That's already substantial.

But imagine each Lambda execution environment creates a database pool configured with a maximum of ten connections.

During a burst, many execution environments may exist simultaneously, each with its own pool.

The aggregate potential connection demand can become much larger than the number of concurrent queries.

This doesn't mean every pool immediately opens all ten connections. It means the architecture permits a large multiplication of connection capacity without coordinating it against the database's limits.

### Why PostgreSQL cannot scale like Lambda

PostgreSQL connections consume server resources.

Each backend connection has memory and scheduling overhead, and the database must coordinate queries, transactions, locks, buffers, and storage access.

Increasing `max_connections` is not a universal solution.

At some point, the database becomes limited by CPU, memory, I/O, locking contention, query throughput, or other internal resources.

A larger connection limit may merely allow more work to compete for the same bottleneck.

### RDS Proxy

Amazon RDS Proxy can manage and pool database connections between applications and supported RDS databases.

```text
Many Lambda Executions
          │
          ▼
       RDS Proxy
          │
          ▼
    Bounded Database
    Connection Pool
          │
          ▼
       PostgreSQL
```

The proxy can reduce the pressure created by numerous short-lived or frequently changing client connections.

However, proxying doesn't increase the database's fundamental query-processing capacity.

Transactions or session behavior may also require connections to remain associated with particular clients, reducing opportunities for multiplexing.

If the actual database is already saturated by expensive queries, a proxy alone won't solve the problem.

### A defensible solution

I'd investigate and potentially combine:

1. Efficient connection reuse within warm Lambda execution environments.
2. Appropriate pool sizing and RDS Proxy where justified.
3. Reserved concurrency or other admission controls to limit database pressure.
4. Query optimization and database capacity measurements.
5. Caching for read-heavy operations that tolerate it.
6. Asynchronous queues for work that need not complete during the request.
7. Appropriate database scaling only after understanding the bottleneck.

The important design principle is to place explicit limits between elastic upstream compute and finite downstream capacity.

**An infinitely ambitious producer is not an architecture. It's a denial-of-service attack with excellent intentions.**

---

## 10. S3 and CloudFront: Separating Files From Application Servers

Now suppose our hotel-booking SaaS serves uploaded hotel images, customer documents, and a Vue frontend.

Storing all these assets on individual application servers would complicate deployments and horizontal scaling.

If a customer uploads a file through API Task A but the next request reaches Task B, how does Task B retrieve it?

A shared durable storage system solves this problem.

### Amazon S3

Amazon Simple Storage Service, or S3, is an object-storage service.

An object consists of data and associated metadata, identified within a bucket by a key.

For example:

```text
Bucket: hotel-assets

Key: properties/123/images/main.webp
Key: properties/123/images/lobby.webp
Key: invoices/2026/INV-8392.pdf
```

S3 does not behave like a conventional shared POSIX filesystem.

It offers object-oriented operations rather than arbitrary in-place file modifications through ordinary filesystem APIs.

S3 now provides strong read-after-write consistency for supported object operations, including new writes, overwrites, deletes, and listings.

Nevertheless, object consistency is not the same as a multi-object database transaction.

You should not assume that updating several related objects creates one atomic business operation.

### Amazon CloudFront

CloudFront is AWS's content delivery network.

It caches suitable content at edge locations closer to clients and forwards cache misses to configured origins.

```text
User in Stockholm
        │
        ▼
 CloudFront Edge
        │
        ├── Cached image? Return it
        │
        └── Cache miss
                │
                ▼
             S3 Origin
```

This reduces repeated origin requests and can improve content-delivery latency.

For a Vue single-page application, a common pattern is:

```text
Vue Build
   │
   ▼
Private S3 Bucket
   │
   ▼
CloudFront
   │
   ▼
Browser
```

CloudFront Origin Access Control can authorize CloudFront to retrieve objects from a private S3 bucket without making the bucket publicly readable.

But caching introduces consistency considerations of its own.

Replacing `app.js` at the same URL can leave clients or edge locations temporarily using older cached content, depending on caching configuration.

Content-hashed filenames and appropriate cache headers help make deployments predictable.

For example:

```text
assets/app.a84f1c.js
assets/app.21bc09.js
```

Each deployed version has a distinct asset identity.

S3 provides the authoritative object; CloudFront maintains cached copies according to its delivery and caching configuration.

---

## 11. RDS Versus DynamoDB: Choose the Data Model, Not the Logo

AWS offers multiple database services because different workloads have fundamentally different requirements.

Two especially relevant options are RDS and DynamoDB.

### Amazon RDS

RDS manages supported relational database engines, including PostgreSQL.

It provides capabilities such as managed provisioning, automated backups, monitoring integrations, maintenance tooling, and availability options.

You still own schema design, query quality, transactions, indexes, connection management, and many performance decisions.

RDS is particularly attractive for business systems involving rich relationships, transactional constraints, and flexible queries.

Hotel reservations, invoices, payments, and customer accounts often fit relational modeling naturally.

### DynamoDB

DynamoDB is a managed NoSQL database supporting key-value and document-style access patterns.

Rather than designing normalized relational tables and relying on arbitrary joins, engineers usually model access around partition keys, sort keys, and appropriate secondary indexes.

For example, a simple access pattern might retrieve all events for a particular conversation:

```text
Partition key: CONVERSATION#123

Sort key: EVENT#2026-10-25T10:00:00
Sort key: EVENT#2026-10-25T10:01:00
Sort key: EVENT#2026-10-25T10:02:00
```

With an appropriate key design, related items can be retrieved efficiently.

DynamoDB can scale very effectively for suitable workloads, but poor partition-key choices can concentrate activity on particular partitions.

### The access-pattern question

Suppose you're designing storage for AI agent conversation events.

You primarily need:

- Append events to a conversation.
- Retrieve events belonging to one conversation.
- Retrieve recent items in order.
- Retrieve metadata by known identifiers.

DynamoDB may be a reasonable candidate.

Now consider financial reporting that requires complex joins across customers, subscriptions, invoices, payments, and refund records.

PostgreSQL may be considerably more natural.

DynamoDB supports transactional capabilities, but its query model and data modeling trade-offs remain different from a relational database.

Choosing DynamoDB merely because it is "serverless and scalable" is a mistake.

Choosing PostgreSQL for every possible workload without considering access patterns can also be a mistake.

The right database depends on data relationships, query patterns, consistency requirements, scale, operational economics, and team expertise.

---

## 12. SQS and EventBridge: Decoupling Workloads

Let's imagine a customer uploads a document that requires thirty seconds of processing.

Holding the HTTP request open during processing creates unnecessary coupling between the user's connection and the background workload.

A better design might be:

```text
Client
  │
  ▼
API Gateway / API
  │
  ├── Store document in S3
  │
  ├── Record processing job
  │
  └── Enqueue work
           │
           ▼
          SQS
           │
           ▼
      Worker Fleet
           │
           ▼
      Process Document
```

### Amazon SQS

Simple Queue Service stores messages for asynchronous processing.

Workers consume messages, perform operations, and delete successfully processed messages.

SQS's standard queue model generally provides at-least-once delivery, so consumers must tolerate duplicate delivery.

The visibility timeout temporarily hides a received message from other consumers while processing is underway.

If a worker fails without deleting the message, it can become available for another attempt.

This is useful for reliability but requires careful idempotency.

A failed worker must not cause the same customer to be charged twice.

### EventBridge

Amazon EventBridge supports event routing between producers and consumers according to configured rules and integration capabilities.

It's useful when a business occurrence should notify several independent consumers.

For example:

```text
SubscriptionActivated
        │
        ▼
    EventBridge
        │
    ┌───┼────────┐
    ▼   ▼        ▼
 Analytics  Email  Onboarding
```

But EventBridge is not merely SQS with a different interface.

Queues are especially useful for buffering and distributing units of work to consumers. Event routing is useful for distributing occurrences to interested destinations.

An architecture may use both: EventBridge routes a business event to one or more SQS queues, and workers consume buffered workloads at controlled rates.

This arrangement is powerful when traffic arrives in bursts.

However, queues do not eliminate capacity constraints. They relocate excess demand into a backlog that must eventually be processed.

A growing queue may protect the API while simultaneously revealing that worker throughput cannot keep up.

---

## 13. A Coherent AWS Architecture for a Production SaaS

Let's assemble the major components into a plausible architecture.

Our requirements:

- Vue frontend.
- Node.js API.
- PostgreSQL for transactional business data.
- Background document processing.
- Third-party hotel supplier integrations.
- Private customer documents.
- Moderate traffic with occasional bursts.
- Availability across an AZ failure.
- Small engineering team.

A defensible initial design might look like this:

```text
                        USERS
                          │
                          ▼
                       Route 53
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
        CloudFront               HTTPS API
             │                         │
             ▼                         ▼
        Private S3              Application
        Vue Assets              Load Balancer
                                       │
                              ┌────────┴────────┐
                              ▼                 ▼
                         Fargate API       Fargate API
                            AZ-A              AZ-B
                              │                 │
                              └────────┬────────┘
                                       │
                              ┌────────┴────────┐
                              ▼                 ▼
                           RDS PG              SQS
                           Multi-AZ             │
                                                ▼
                                          Worker Tasks
                                                │
                                         ┌──────┴──────┐
                                         ▼             ▼
                                    Private S3     External APIs
```

This is a conceptual diagram, not a complete networking specification. A real implementation also needs explicit subnets, routing, IAM roles, security groups, secrets, monitoring, and backup arrangements.

### Why choose Fargate for the API?

A continuously running API with database connections and moderate traffic is a straightforward fit for persistent containers.

Lambda could also work, but Fargate allows a stable application process with explicit connection-pool sizing and task-level capacity management.

That doesn't mean Fargate will always be cheaper or more reliable.

We would compare actual workload characteristics before committing.

### Why keep PostgreSQL?

Reservations, payments, invoices, and customer accounts involve relational constraints and transactional behavior.

PostgreSQL is an appropriate default for such a domain.

DynamoDB could still support particular high-volume event or metadata access patterns if justified, but introducing a second database isn't necessary merely for architectural variety.

### Why use SQS?

Document processing can take significantly longer than an ordinary API request.

A durable queue decouples request handling from worker throughput, allows controlled retries, and protects the API from processing bursts.

### Why use private subnets?

The application containers and database don't need arbitrary inbound internet reachability.

The internet-facing load balancer provides the controlled entry point, while application and data workloads remain behind their intended network boundaries.

### Why not Kubernetes?

Nothing in the stated requirements clearly demands Kubernetes.

ECS/Fargate provides much of the required deployment and scaling functionality with less platform-management overhead for this particular team.

Choosing not to introduce Kubernetes is an architectural decision, not evidence of insufficient ambition.

---

## 14. The Cloud Bill Is an Architectural Document

Cloud services convert many infrastructure expenses into usage-dependent or recurring operational costs.

That is convenient, but it also means architectural mistakes can accumulate charges continuously.

Consider several possibilities.

**Oversized databases:** A database instance remains provisioned continuously, whether it is busy or idle.

**NAT gateways:** Hourly charges and processed data can become significant relative to a small application's compute bill.

**Excessive logging:** High-volume application logs, long retention periods, and expensive queries can generate substantial observability costs.

**Cross-AZ traffic:** Moving data between availability zones can introduce data-transfer charges depending on the services and traffic paths.

**Uncontrolled retries:** A failing external dependency can cause repeated Lambda executions, queue processing attempts, and downstream API calls.

**Inefficient object storage:** Large collections of infrequently accessed files may remain in unnecessarily expensive storage classes.

### Fixed and variable costs

A simplified cost model might be:

\[
C_{\text{total}}
=
C_{\text{baseline}}
+
C_{\text{compute}}
+
C_{\text{storage}}
+
C_{\text{requests}}
+
C_{\text{data transfer}}
+
C_{\text{operations}}
\]

The categories overlap in some real AWS pricing models, but the decomposition is useful for reasoning.

A provisioned database contributes significant baseline cost. Lambda generally contributes usage-related compute cost, while Fargate charges for allocated resources over task runtime.

Some services charge separately for requests, stored data, provisioned capacity, throughput, or data movement.

A major architectural consideration is how costs behave as traffic grows.

If a service's revenue grows linearly with customer activity but infrastructure costs grow disproportionately, the business may face serious scaling economics.

### Cost is not only the AWS invoice

Operating infrastructure consumes engineering time.

An EC2 deployment that saves €150 monthly but requires frequent manual patching and maintenance may be more expensive overall than a managed alternative.

Similarly, a sophisticated Kubernetes platform may consume a substantial share of a small team's engineering capacity.

The meaningful objective is **total operational economics**, not minimizing one line item on the cloud bill.

Cost optimization also should not compromise necessary security, availability, or data durability merely to achieve small savings.

---

## 15. Practical Lab — Review a Cloud Architecture Before Deploying It

This session's lab can be completed entirely as a design exercise, without creating billable AWS resources.

You're reviewing an existing SaaS deployment:

```text
Internet
    │
    ▼
API Gateway
    │
    ▼
Lambda
    │
    ├── PostgreSQL RDS
    ├── S3 Bucket
    └── External Payment API
```

The application has several known characteristics:

- Average traffic is 40 requests per second.
- Short peaks reach 500 requests per second.
- Lambda is configured for a high concurrency ceiling.
- Each execution environment initializes a PostgreSQL pool with a maximum of ten connections.
- Database connection usage occasionally approaches the instance limit.
- Customer documents are stored in S3.
- The Lambda execution role has broad S3 permissions.
- All workloads run in one Region.
- The database has automated backups but no tested restoration procedure.

### Investigation A — Identify failure domains

Draw the architecture and mark which components can independently fail.

Consider:

- A Lambda concurrency surge.
- PostgreSQL becoming unavailable.
- The payment provider responding slowly.
- S3 authorization failures.
- An Availability Zone disruption.
- A deployment introducing an incompatible database schema.

For each scenario, ask whether the system should reject requests, retry work, degrade functionality, or initiate recovery.

Avoid assuming that AWS automatically coordinates application-level recovery.

### Investigation B — Find the dangerous scaling relationship

Estimate database connection pressure.

Assume the average request lasts 400 milliseconds and traffic reaches 500 requests per second.

Under steady-state assumptions:

\[
L = 500 \times 0.4 = 200
\]

Approximately 200 requests may be executing concurrently.

If each execution environment can create a pool of ten database connections, the potential aggregate connection configuration is much larger than the concurrent request count.

Explain why this is a risk even though not every pool necessarily fills.

Propose an admission-control strategy and a connection-management approach.

### Investigation C — Repair IAM

Replace the broad S3 permission with a narrowly scoped policy.

For example, suppose the application should only read and write documents inside:

```text
s3://customer-documents/tenant-uploads/
```

A simplified policy could be:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::customer-documents/tenant-uploads/*"
    }
  ]
}
```

Now identify what this still doesn't solve.

In particular, an IAM permission scoped to a prefix does not automatically enforce tenant-level isolation if application code can choose arbitrary keys within that prefix.

The backend still needs to authorize which tenant owns each requested object.

### Investigation D — Design a more resilient database layer

Evaluate whether the application would benefit from:

- RDS Proxy.
- Database connection limits.
- Improved query performance.
- Multi-AZ database deployment.
- Restore testing.
- Asynchronous work queues.
- Read caching.

Don't implement all of them reflexively.

Rank improvements according to evidence, consequences, and engineering effort.

### Investigation E — Estimate cost drivers

Without searching for exact prices, identify which components have baseline costs and which are primarily driven by usage.

Consider Lambda, RDS, NAT gateways, S3, CloudWatch logs, and data transfer.

Then ask how the cost structure changes if traffic grows by a factor of ten.

The goal is not to calculate a precise invoice.

It is to learn to recognize the economic consequences of architectural choices.

---

## 16. Engineering and Interview Challenges

### Challenge 1 — The private subnet mystery

A Lambda function has been configured to access PostgreSQL inside a VPC.

Database queries work, but calls to a public payment API begin timing out.

The Lambda execution role has the necessary AWS permissions.

What changed, and how would you investigate?

### Challenge 2 — Multi-AZ doesn't mean invincible

Your application runs across two Availability Zones, and PostgreSQL uses an RDS Multi-AZ deployment.

A developer accidentally executes a destructive database migration.

Will Multi-AZ infrastructure prevent the resulting data loss?

What mechanisms are actually relevant?

### Challenge 3 — Lambda versus Fargate

You need to deploy a Node.js API receiving a stable 300 requests per second.

It uses PostgreSQL, has moderately expensive startup initialization, and requires persistent application-level connection pooling.

Would you choose Lambda or Fargate?

What additional information would influence the decision?

### Challenge 4 — The unsafe S3 policy

An application's IAM role can read every object in a customer-document bucket.

The backend uses a tenant ID in the S3 key prefix and trusts the frontend to supply the correct tenant ID.

Is this secure? What are the distinct infrastructure and application risks?

### Challenge 5 — The queue that never empties

Your document-processing architecture uses SQS and Fargate workers.

During peak hours, the queue grows from 100 to 50,000 messages. The API remains responsive, and no messages appear to be permanently lost.

Has the architecture handled the traffic surge successfully?

What measurements and decisions are now necessary?

---

## 17. Solutions and Discussion

### Challenge 1 — VPC connectivity changes network behavior

Connecting a Lambda function to a customer-managed VPC changes the networking available to its execution environment.

If the function uses private subnets without a suitable outbound path, it may reach private PostgreSQL but fail to reach external public endpoints.

I'd inspect subnet route tables, NAT configuration, security groups, DNS resolution, and connection errors.

For public IPv4 destinations, a private subnet often needs appropriate NAT-based egress. Relevant AWS services may instead be reached through VPC endpoints.

IAM permission alone cannot create a network route to an external payment API.

### Challenge 2 — High availability isn't backup

RDS Multi-AZ improves resilience against certain infrastructure failures through supported standby or multi-instance arrangements.

It does not protect against every form of logical corruption or accidental deletion.

A destructive migration can affect the authoritative database state and be reflected through replication.

Recovery requires appropriate backups, point-in-time recovery capabilities where configured, tested restoration procedures, and a recovery plan that meets the application's RPO and RTO.

Availability mechanisms help keep a service running. Recovery mechanisms help restore acceptable state after damage.

Both matter.

### Challenge 3 — Fargate is a strong candidate

Given sustained traffic, relatively expensive initialization, and a preference for persistent connection pooling, I'd seriously favor ECS/Fargate as the initial candidate.

A continuously running Node.js process can serve many requests while maintaining controlled application resources.

However, the answer still depends on latency requirements, actual request duration, traffic variability, operating cost, scaling behavior, and team familiarity.

Lambda remains technically viable for many PostgreSQL-backed APIs when connections and concurrency are managed appropriately.

The decision should be based on workload characteristics and measured economics rather than an assumption that serverless functions are always cheaper.

### Challenge 4 — The frontend is not an authorization authority

The design is unsafe if users can influence tenant identifiers without server-side authorization.

An attacker might modify the requested tenant ID and trick the backend into retrieving another customer's documents.

IAM limits the backend's AWS authority but does not automatically determine which customer may access which object.

I'd enforce tenant ownership on the server, derive authorization context from trusted authentication state, and use appropriately scoped S3 permissions.

Presigned URLs, if used, must be generated only after authorization and should have suitable scope and expiration.

Network security, IAM authorization, and application-level tenant isolation are separate layers.

### Challenge 5 — Buffering succeeded; throughput may have failed

The queue has absorbed the traffic burst without immediately overwhelming the API, which is a genuine architectural benefit.

But a growing backlog means incoming work is exceeding completed processing over the observed period.

I'd inspect queue age, arrival rate, processing throughput, error rates, retry behavior, worker utilization, and downstream bottlenecks.

Scaling workers may help if sufficient external and internal capacity exists. If every worker is blocked by the same rate-limited supplier, adding workers could make the situation worse.

The critical user-facing question is whether the queue can return to an acceptable processing delay within the required time.

A queue that retains every message for three days is not necessarily a successful system if customers expect results within five minutes.

---

## Mental Model

When evaluating an AWS architecture, reason through seven boundaries:

1. **Geography:** Which Regions and Availability Zones contain the workload?
2. **Networking:** Which resources can communicate, through which routes and security controls?
3. **Identity:** Which principals may perform which AWS operations?
4. **Compute:** Which workloads need virtual machines, persistent containers, or event-driven functions?
5. **Data:** Which storage systems match the required data models and consistency guarantees?
6. **Capacity and failure:** Where can demand exceed downstream limits, and what happens when dependencies fail?
7. **Economics:** Which costs are baseline, which scale with usage, and which consume engineering effort?

**The central principle: Cloud services remove selected infrastructure responsibilities, but the system's reliability, security, performance, and economics still emerge from how those services are connected.**


---

## Next Lecture — SE340-L04: CI/CD and Infrastructure as Code

Continue in **SE340 — Linux, Cloud Infrastructure, and Delivery**.

## Further Reading

1. **AWS — [Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/)**. The six architectural pillars and the trade-offs underlying reliable cloud workloads.

2. **AWS — [Amazon VPC User Guide](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)**. Subnets, route tables, internet gateways, NAT, security groups, and network boundaries.

3. **AWS — [IAM Policy Evaluation Logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)**. The interaction between identity policies, resource policies, boundaries, organizational controls, and explicit denies.

4. **AWS — [Fargate or Lambda?](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/fargate-or-lambda.html)**. Current AWS guidance for choosing between managed containers and event-driven functions.

5. **AWS — [Using Lambda with Amazon RDS](https://docs.aws.amazon.com/lambda/latest/dg/services-rds.html)**. Database connectivity, RDS Proxy, connection pooling, and serverless concurrency considerations.

6. **AWS — [Amazon S3 User Guide](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)**. Object storage, consistency, permissions, durability, and storage architecture.

7. **AWS — [Amazon SQS Developer Guide](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html)**. Message delivery, visibility timeouts, retries, and asynchronous workloads.

8. **AWS — [Pricing Calculator](https://calculator.aws/)**. Model the actual financial consequences of a proposed infrastructure design rather than guessing from service names.

---

## Dense Cheatsheet — Interview Glance Card

*Fenced so voice readers skip it. Skim on screen when revising; open sections above only when a row fails to spark.*

```text
SE340-L03  AWS ARCHITECTURE — INTERVIEW GLANCE CARD

CORE MODEL
  Cloud eases acquiring resources; doesn't erase constraints
  Scaling compute ≠ scaling the system (Lambda vs RDS connections)
  Managed ≠ fully managed; serverless ≠ no servers

GEOGRAPHY
  Region → AZs (failure domains)
  Multi-AZ app + single-AZ DB = SPOF remains
  Multi-AZ ≠ immune to bad migrations / corruption / regional outage

VPC / NETWORK
  Subnets per AZ; public = IGW route (+ addressing/SG)
  Private + NAT for IPv4 egress without inbound exposure
  NAT cost + AZ design; VPC endpoints can avoid NAT for AWS APIs
  Topology = security + availability + cost

SECURITY GROUPS / IAM
  SG stateful; reference other SGs (scale-friendly)
  NACL subnet/stateless secondary
  IAM: least privilege roles, temporary creds, no long-lived keys
  Explicit deny overrides allow; connectivity ≠ authorization
  Prefix IAM ≠ tenant isolation — app still authorizes keys

COMPUTE SPECTRUM
  EC2          VM control; you patch/deploy
  ECS/Fargate  persistent containers; managed hosts
  Lambda       event-driven; concurrency unit; 15m max classic
  Choose by duration, control, pooling, cost, pattern

FRONT DOOR
  ALB = L7 distribute/health/TLS; API Gateway = API features/throttle
  Throttle: controlled 429 > accept until total collapse

LAMBDA–POSTGRESQL TRAP
  L = λW concurrency estimate; many envs × pool size explode conns
  RDS Proxy helps pooling; ≠ more query capacity
  Admission control + reuse + optimize + cache/async as needed

DATA / ASYNC
  S3 objects (strong consistency ≠ multi-object txn); CloudFront CDN
  Content-hash assets; OAC for private origins
  RDS/PG for relational txn; DynamoDB for key/access patterns
  SQS at-least-once + visibility timeout; EventBridge routes events
  Queue buffers ≠ infinite capacity; backlog age matters

COST
  Baseline (RDS, NAT) vs usage (Lambda, transfer, logs)
  Retries/cross-AZ/logging can dominate; total eng cost counts

SEVEN BOUNDARIES
  Geography · Networking · Identity · Compute · Data
  · Capacity/failure · Economics

SENIOR LINE: Reliability/security/perf/cost emerge from how
             services are connected—not from logos alone.
```

---


