# Technology and Topic Atlas

Searchable reference for *The Modern Software Engineer* — **not a lecture** and not part of the study progression.

Use this document to answer:

- What is this technology or field?
- What problem does it solve?
- Where does it fit in a software system or organization?
- Where is it already taught in this curriculum?
- Is the coverage introductory, detailed, or practical?
- Is there a planned lecture for further study?

**Coverage levels**

| Level | Meaning |
| --- | --- |
| orientation | Conceptual map; professional fluency without specialist depth |
| working understanding | Enough to reason, design, and discuss trade-offs |
| practical | Hands-on workflows, tooling, or labs |
| planned | Stub or catalogue entry; manuscript not yet authored |
| mention | Named or lightly touched; not a full treatment |

A brief mention and a full technical explanation have different coverage levels. Do not treat a tool as comprehensively taught merely because its name appears somewhere in a manuscript.

Catalogue source of truth: [`curriculum.yaml`](curriculum.yaml). Course listings: [`curriculum.md`](curriculum.md).

---

## 1. Programming languages, runtimes, and frameworks

| Topic or technology | Purpose | Typical developer interaction | Existing | Planned | Coverage |
| --- | --- | --- | --- | --- | --- |
| JavaScript / TypeScript semantics | How JS values, async, and TS types behave at runtime | Write and debug application code | CS220-L02 | — | working understanding |
| Type systems, generics, ownership | Encode valid states and catch illegal ones early | Design APIs and domain models | CS220-L03 | — | working understanding |
| Memory, GC, leaks | Understand allocation and retention failures | Diagnose production memory issues | CS220-L04 | — | working understanding |
| Compilers and JITs | How source becomes executable work | Reason about language/runtime trade-offs | CS220-L05 | — | working understanding |
| Managed vs native runtimes | Trade-offs of VM-backed and native execution | Choose languages and debug runtime behavior | CS220-L06, CS220-L07 | — | working understanding |
| Vue / frontend frameworks (core) | Build interactive browser UIs | Component design, state, delivery | SE240 | SE250 (planned elective) | working understanding |
| React (planned specialization) | Framework literacy when changing stacks | Port mental models between frameworks | — | SE250 | planned |

---

## 2. Frontend, browser, design, and SEO

| Topic or technology | Purpose | Typical developer interaction | Existing | Planned | Coverage |
| --- | --- | --- | --- | --- | --- |
| Browser internals / rendering | How HTML/CSS/JS become pixels and events | Debug layout, network, and scripting costs | SE240-L01 | — | working understanding |
| Frontend architecture | Feature boundaries beyond components | Structure modules, stores, services | SE240-L02 | SE215-L04 (repo/packages), SE215-L10 (design collab) | working understanding |
| State and reactivity | Keep UI consistent with changing data | Choose local vs shared state patterns | SE240-L03 | — | working understanding |
| CSR / SSR / SSG delivery | How apps are built, shipped, and rendered | Choose rendering strategies for product needs | SE240-L04 | — | working understanding |
| Technical SEO | Make public pages crawlable and indexable | Fix metadata, canonicals, sitemaps, diagnostics | SE240-L04 (rendering + intro SEO) | SE215-L08 | orientation → planned practical |
| Frontend performance | Why fast code can still feel slow | Measure Core Web Vitals and perceived latency | SE240-L05 | — | working understanding |
| Frontend testing | Confidence in UI behavior | Unit/component/integration/E2E strategy | SE240-L06 | SE215-L07 | working understanding + planned practical |
| Production page forensics | How mature sites actually load and operate | Resource hints, fonts, third-party scripts, caches, DevTools audits | SE240-L07 (stub) | SE310-L02 (CSP/cookies), SE215-L08/L10 (SEO/analytics context) | planned capstone |
| Design systems / Figma handoff | Turn designs into consistent UI | Tokens, components, accessibility, collaboration | SE240 (implementation concepts) | SE215-L10 | mention → planned orientation |
| Product analytics / conversion | Measure whether features achieve outcomes | Instrument funnels, experiments, rollouts | CS120 (experiments), app examples | SE215-L10 | orientation → planned |

---

## 3. Backend APIs, messaging, and asynchronous processing

| Topic or technology | Purpose | Typical developer interaction | Existing | Planned | Coverage |
| --- | --- | --- | --- | --- | --- |
| Frontend–backend contracts | Stable API boundaries | Design and version HTTP APIs | SE310-L01 | — | working understanding |
| Web API security | Authenticate, authorize, and protect interfaces | Threat modeling and secure defaults | SE310 | SE370 (planned) | working understanding |
| Backend services | Build request/response and domain services | Structure services and failure handling | SE320 | — | working understanding |
| Queues, workers, async workflows | Decouple slow or unreliable work | Design jobs, retries, idempotency | SE320-L03 | — | working understanding |
| Files / uploads / object storage | Ingest and serve large documents safely | Multipart uploads, signed URLs, cleanup | — | SE325-L01 | planned elective |
| Bulk imports / exports | Move large datasets without melting interactive traffic | Checkpoints, partial success, cancellation | — | SE325-L02 | planned elective |
| Scheduled / distributed cron | Run periodic work safely under failover and clock weirdness | Leases, catch-up, DST, idempotent effects | — | SE325-L03 | planned elective |
| Production data repair / lifecycle | Fix or erase production facts across stores | Audited repairs, retention, erasure | — | SE325-L04 | planned elective |
| Third-party integration maintenance | Survive vendor drift and ambiguous sync outcomes | Tokens, webhooks, backfills, observability | CS430-L01/L05 (theory) | SE325-L05 | planned elective |
| API protection / tenant fairness | Protect shared backends from noisy neighbors | Quotas, expensive budgets, shedding | CS430-L03 (overload) | SE325-L06 | planned elective |
| Kafka / message brokers | Move events between producers and consumers | Publish domain events; reason about ordering | Distributed/data references | SE215-L09 | mention → planned orientation |

---

## 4. Databases, search, analytics, and data engineering

| Topic or technology | Purpose | Typical developer interaction | Existing | Planned | Coverage |
| --- | --- | --- | --- | --- | --- |
| Relational design / SQL | Model and query OLTP data | Schema design, transactions, performance | CS330 | CS350 (planned) | working understanding / revised |
| Transactions and isolation | Correct concurrent updates | Choose isolation levels; debug anomalies | CS330-L03 | — | working understanding |
| Storage engines | How data is persisted and retrieved | Reason about indexes, WAL, compaction | CS340-L02 | — | working understanding |
| Document databases / MongoDB | Flexible document storage trade-offs | Choose when documents fit the domain | CS340-L03 | — | working understanding |
| Specialized stores (Redis, DynamoDB, search, analytics) | Fit specialized access patterns | Select and operate non-relational systems | CS340-L06 | — | working understanding |
| Elasticsearch / OpenSearch | Full-text and structured search infrastructure | Index documents; query relevance | CS340-L06 | — | working understanding |
| Data architecture / source of truth | Decide where truth lives and how it syncs | Workshop analytics and synchronization decisions | CS340-L07 | SE215-L09 | working understanding + planned orientation |
| Data pipelines / ETL–ELT | Move operational data into analytical form | Design ingestion, transforms, quality checks | CS340-L07 (partial) | SE215-L09 | planned orientation |
| Data warehouses / lakes | Store analytical workloads | Feed dashboards and reports | CS340-L06 | SE215-L09 | working understanding + planned orientation |
| Airflow | Orchestrate batch data workflows | Schedule DAGs; handle backfills | — | SE215-L09 | planned orientation |
| dbt | Transform warehouse data with versioned SQL | Model marts; test data quality | — | SE215-L09 | planned orientation |
| CDC | Capture database changes for downstream systems | Emit trustworthy change streams | CS340 | SE215-L09 | working understanding + planned orientation |

---

## 5. Cloud, containers, networking, and infrastructure

| Topic or technology | Purpose | Typical developer interaction | Existing | Planned | Coverage |
| --- | --- | --- | --- | --- | --- |
| Computer networks | How packets, DNS, HTTP, and TLS behave | Diagnose connectivity and protocol failures | CS230 | — | working understanding |
| Operating systems / processes / memory | How the machine runs your code | Debug CPU, memory, I/O contention | CS320 | CS240 (planned) | working understanding |
| Linux for application engineers | Deeper OS internals for production work | Inspect processes, cgroups, networking | CS320, SE340 | CS240 | planned |
| AWS architecture | Design and operate on Amazon Web Services | Map apps to VPC, compute, data, IAM | SE340-L03 | SE215-L05 (provider comparison) | working understanding + planned orientation |
| GCP | Google Cloud service categories | Same SaaS pattern on GCP | — | SE215-L05 | planned orientation |
| Azure | Microsoft Azure service categories | Same SaaS pattern on Azure | — | SE215-L05 | planned orientation |
| Cloud service models (IaaS/PaaS/serverless) | Choose shared-responsibility boundaries | Decide what the team still owns | SE340 | SE215-L05 | working understanding + planned orientation |
| Containers / Kubernetes | Schedule and reconcile containerized workloads | Deploy, configure, observe clusters | SE450 | SE215-L06 (org context) | practical / manuscript + planned orientation |
| Terraform / IaC | Declare and version infrastructure | Manage state, modules, and delivery pipelines | SE340-L04 | SE215-L06 (context), SE360 (planned) | working understanding / planned specialization |

---

## 6. CI/CD, DevOps, SRE, and platform engineering

| Topic or technology | Purpose | Typical developer interaction | Existing | Planned | Coverage |
| --- | --- | --- | --- | --- | --- |
| CI/CD | Automate build, test, and release | Write pipelines; gate merges and deploys | SE340-L04 | SE215-L06 | working understanding + planned orientation |
| DevOps / platform ownership | Share delivery responsibility end to end | Collaborate on environments, deploy, on-call | SE340, SE440, SE450 | SE215-L06 | working understanding + planned orientation |
| GitOps | Reconcile desired state from Git | Operate progressive delivery on Kubernetes | SE450-L07 | SE215-L06 | working understanding + planned orientation |
| Reliability / SRE practices | Keep systems available under change | SLOs, incidents, operational readiness | SE440 | SE215-L06 | working understanding + planned orientation |
| Observability | Understand system behavior from signals | Use logs, metrics, traces in incidents | SE440, SE450-L07 | — | working understanding |
| Performance engineering | Measure and improve system performance | Experiment, diagnose bottlenecks, budget | SE460 (stubs) | — | planned |

---

## 7. Testing, QA, security, and observability

| Topic or technology | Purpose | Typical developer interaction | Existing | Planned | Coverage |
| --- | --- | --- | --- | --- | --- |
| Test strategy / layers | Choose confidence vs cost | Unit through system and contract tests | SE240-L06, SE440-L03 | — | working understanding |
| Playwright / browser E2E | Verify real user workflows in browsers | Own fixtures, data, flakiness, CI | SE240-L06, SE440-L03 | SE215-L07 | mention/strategy → planned practical |
| Application security | Reduce exploitability of software | Threat model; secure APIs and configs | SE310 | SE370 (planned) | working understanding / planned |
| Incident response | Recover and learn from production failures | On-call, blameless analysis, follow-ups | SE440-L02 | — | working understanding |

---

## 8. Architecture, repositories, and build systems

| Topic or technology | Purpose | Typical developer interaction | Existing | Planned | Coverage |
| --- | --- | --- | --- | --- | --- |
| Modular monolith / in-process architecture | Structure one deployable with clear modules | Boundaries, layers, hexagonal, DDD | SE330-L02 | SE215-L04 (repo vs runtime distinction) | working understanding |
| Microservices / service boundaries | Distribute autonomy with communication costs | Events, outbox, sagas, data ownership | CS430-L04 | — | working understanding |
| Distributed systems fundamentals | Consistency, failure, coordination | Design for partial failure | CS430 | — | working understanding |
| Monorepos / multirepos / build systems | Organize code and builds across apps | Workspaces, caching, ownership, CI | Scattered mentions | SE215-L04 | planned orientation |
| Git collaboration / PRs | Coordinate concurrent change safely | Branching, review, hotfix, release tags | Scattered delivery references | SE215-L03 | planned orientation |
| Architecture evolution / debt | Change systems without collapsing them | Refactor economics and incentives | SE330-L03 | SE215-L02, SE215-L03 | working understanding + planned orientation |
| Architecture studio | Integrated design workshops | Defend end-to-end designs | SE490 | — | practical |

---

## 9. Product management, design collaboration, and work organization

| Topic or technology | Purpose | Typical developer interaction | Existing | Planned | Coverage |
| --- | --- | --- | --- | --- | --- |
| Cross-functional roles | Know who owns which decisions | Collaborate across PM, design, QA, ops, data | — | SE215-L01 | planned orientation |
| Agile / Scrum / Kanban | Plan and improve delivery flow | Break work down; manage WIP and priorities | Scattered team practices | SE215-L02 | planned orientation |
| Product discovery vs delivery | Build the right thing, then ship it | Requirements, journeys, success metrics | — | SE215-L10 | planned orientation |
| Figma / design handoff | Translate design intent into software | Review prototypes, tokens, accessibility | — | SE215-L10 | planned orientation |
| People and teams map | See the path from ticket to operating system | Identify stakeholders and handoff risks | — | SE215-L01 | planned orientation |

---

## 10. Artificial intelligence, LLM tooling, and agents

| Topic or technology | Purpose | Typical developer interaction | Existing | Planned | Coverage |
| --- | --- | --- | --- | --- | --- |
| Language models in products | Use LLMs as components with failure modes | Prompt, evaluate, constrain, monitor | AI310 | — | working understanding |
| Retrieval / RAG | Ground model answers in trusted data | Build retrieval pipelines and evaluations | AI310 | — | working understanding |
| Agentic systems | Compose tools and workflows with models | Design agents; evaluate nondeterminism | AI410 | AI450 (planned) | working understanding / planned |
| AI security, reliability, economics | Operate AI systems responsibly | Cost, abuse, evaluation under change | AI410-L07 | — | working understanding |

---

## Related orientation elective

[`SE215 — The Software Engineering Ecosystem`](SE/SE215-software-engineering-ecosystem/) is the short-format elective that expands professional literacy across several rows above. It is optional, not a prerequisite for the core programme.

When deciding whether a new full course is needed, prefer updating this atlas and assessing SE215 coverage first.
