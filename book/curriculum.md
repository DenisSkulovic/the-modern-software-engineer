# The Modern Software Engineer — Course Catalogue

**Version:** 2.0 — 2026-10-27  
**Default manuscript edition:** `2.0.0`  
**Machine-readable source of truth:** [`curriculum.yaml`](curriculum.yaml)  
**Programme guide / study order:** [`README.md`](README.md)  
**Status model (manuscript vs learning):** [`STATUS.md`](STATUS.md)  
**Personal study ledgers:** [`students/`](students/)

---

## Manuscript statuses

Library/content state — not whether you have studied the lecture. See [`STATUS.md`](STATUS.md).

| Status | Meaning |
| --- | --- |
| `planned` | Catalogue only — no file yet |
| `stub` | File exists; outline / placeholder |
| `draft` | Substantial but incomplete prose |
| `manuscript` | Full lecture to programme standard |
| `revised` | Materially rewritten after first manuscript |
| `polished` | Stable for current major edition |

## Disciplines

| Code | Discipline | Scope |
| --- | --- | --- |
| CS | Computer Science | Computation, languages, operating systems, networks, databases, distributed systems |
| SE | Software Engineering | Web applications, backend services, architecture, infrastructure, production operations |
| AI | Artificial Intelligence | Language models, retrieval, agents, evaluation, production AI |

## Course levels

| Level | Meaning |
| --- | --- |
| 100 | Foundations and essential concepts |
| 200 | Core technical mechanisms and engineering techniques |
| 300 | Advanced applied engineering and specialized systems |
| 400 | Complex systems, architecture, advanced integration, and capstones |
| 500 | Reserved for future specialized / research-oriented material |

Lecture IDs look like `CS330-L03`. Electives use the same scheme (they are courses with `type: planned` or `elective`, not a separate numbering universe).

## Core courses (16 · 73 lectures)

### CS — Computer Science

#### CS110 — Foundations of Computation and Algorithms

100-level · 5 lectures · course status `complete` · `CS/CS110-foundations-of-computation/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `CS110-L01` | What Is Computation, Really? | `manuscript` | `2.0.0` | `CS101-S01` |
| `CS110-L02` | Everything Is Numbers — Until It Isn't | `manuscript` | `2.0.0` | `CS101-S02` |
| `CS110-L03` | Algorithms and the Cost of Computation | `manuscript` | `2.0.0` | `CS101-S03` |
| `CS110-L04` | Data Structures: Choosing How to Remember Things | `manuscript` | `2.0.0` | `CS101-S04` |
| `CS110-L05` | Searching, Sorting, and Finding Shortcuts | `manuscript` | `2.0.0` | `CS101-S05` |

#### CS220 — Programming Languages, Memory, and Execution

200-level · 3 lectures · course status `complete` · `CS/CS220-programming-languages/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `CS220-L01` | Programming Languages and Abstraction | `manuscript` | `2.0.0` | `CS101-S06` |
| `CS220-L02` | Memory: The Invisible Battlefield | `manuscript` | `2.0.0` | `CS101-S07` |
| `CS220-L03` | How Programs Actually Execute | `manuscript` | `2.0.0` | `CS101-S08` |

#### CS230 — Computer Networks and Web Protocols

200-level · 9 lectures · course status `in_progress` · `CS/CS230-computer-networks/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `CS230-L01` | The Journey of a Web Request | `manuscript` | `2.0.0` | `WEB201-S01` |
| `CS230-L02` | Networking for Software Engineers | `manuscript` | `2.0.0` | `WEB201-S02` |
| `CS230-L03` | HTTP: The Protocol That Runs the Web | `manuscript` | `2.0.0` | `WEB201-S03` |
| `CS230-L04` | DNS: The Internet's Distributed Naming System | `manuscript` | `2.0.0` | `` |
| `CS230-L05` | IP Addressing, Subnets, Routing, and NAT | `manuscript` | `2.0.0` | `` |
| `CS230-L06` | The Life of a Network Connection | `manuscript` | `2.0.0` | `` |
| `CS230-L07` | TLS and the Architecture of Trust | `manuscript` | `2.0.0` | `` |
| `CS230-L08` | Proxies, Load Balancers, and Modern Web Transport | `manuscript` | `2.0.0` | `` |
| `CS230-L09` | Network Forensics for Software Engineers | `manuscript` | `2.0.0` | `` |

#### CS320 — Operating Systems, Concurrency, and Runtimes

300-level · 3 lectures · course status `complete` · `CS/CS320-operating-systems-and-concurrency/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `CS320-L01` | Concurrency, Parallelism, and Asynchrony | `manuscript` | `2.0.0` | `CS101-S09` |
| `CS320-L02` | Operating Systems: The Manager Behind the Curtain | `manuscript` | `2.0.0` | `CS101-S10` |
| `CS320-L03` | JavaScript and TypeScript Under the Microscope | `manuscript` | `2.0.0` | `CS101-S11` |

#### CS330 — Relational Databases and Transactions

300-level · 3 lectures · course status `complete` · `CS/CS330-relational-databases/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `CS330-L01` | Relational Database Design | `manuscript` | `2.0.0` | `BACK301-S02` |
| `CS330-L02` | SQL and Query Performance | `manuscript` | `2.0.0` | `BACK301-S03` |
| `CS330-L03` | Transactions: When Correct Operations Produce Incorrect Results | `manuscript` | `2.0.0` | `BACK301-S04` |

#### CS340 — Data Systems Beyond Relational Databases

300-level · 7 lectures · course status `draft` · `CS/CS340-data-systems-beyond-relational/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `CS340-L01` | The Database That Didn't Fit Into Tables | `manuscript` | `2.0.0` | `` |
| `CS340-L02` | Inside a Storage Engine | `stub` | `2.0.0` | `` |
| `CS340-L03` | Document Databases and MongoDB | `stub` | `2.0.0` | `` |
| `CS340-L04` | Indexes, Queries, and Aggregation Beyond SQL | `stub` | `2.0.0` | `` |
| `CS340-L05` | Replication, Consistency, and Sharding in Practice | `stub` | `2.0.0` | `` |
| `CS340-L06` | Specialized Data Systems | `stub` | `2.0.0` | `` |
| `CS340-L07` | The Data Architecture Workshop | `stub` | `2.0.0` | `` |

#### CS430 — Distributed Systems and Reliable Workflows

400-level · 5 lectures · course status `complete` · `CS/CS430-distributed-systems/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `CS430-L01` | Distributed Systems and Partial Failure | `manuscript` | `2.0.0` | `BACK301-S07` |
| `CS430-L02` | Consistency, Replication, and Availability | `manuscript` | `2.0.0` | `BACK301-S08` |
| `CS430-L03` | Scaling and Load Management | `manuscript` | `2.0.0` | `BACK301-S09` |
| `CS430-L04` | Microservices, Events, and Service Boundaries | `manuscript` | `2.0.0` | `BACK301-S10` |
| `CS430-L05` | Designing Reliable Business Workflows | `manuscript` | `2.0.0` | `BACK301-S11` |

### SE — Software Engineering

#### SE240 — Browser and Frontend Engineering

200-level · 6 lectures · course status `complete` · `SE/SE240-frontend-engineering/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `SE240-L01` | Inside the Browser | `manuscript` | `2.0.0` | `WEB201-S04` |
| `SE240-L02` | Frontend Architecture Beyond Components | `manuscript` | `2.0.0` | `WEB201-S05` |
| `SE240-L03` | State Management and Reactive Applications | `manuscript` | `2.0.0` | `WEB201-S06` |
| `SE240-L04` | Delivering Modern Web Applications | `manuscript` | `2.0.0` | `WEB201-S09` |
| `SE240-L05` | Performance: Why Fast Code Can Feel Slow | `manuscript` | `2.0.0` | `WEB201-S10` |
| `SE240-L06` | Testing and Reliability in the Frontend | `manuscript` | `2.0.0` | `WEB201-S11` |

#### SE310 — Web APIs, Identity, and Security

300-level · 3 lectures · course status `complete` · `SE/SE310-web-apis-and-security/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `SE310-L01` | The Frontend–Backend Contract | `manuscript` | `2.0.0` | `WEB201-S07` |
| `SE310-L02` | Authentication and Browser Security | `manuscript` | `2.0.0` | `WEB201-S08` |
| `SE310-L03` | Application and Infrastructure Security | `manuscript` | `2.0.0` | `ENG401-S09` |

#### SE320 — Backend Services and Asynchronous Processing

300-level · 3 lectures · course status `complete` · `SE/SE320-backend-services/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `SE320-L01` | The Anatomy of a Backend Service | `manuscript` | `2.0.0` | `BACK301-S01` |
| `SE320-L02` | Caching: Trading Freshness for Speed | `manuscript` | `2.0.0` | `BACK301-S05` |
| `SE320-L03` | Queues, Workers, and Asynchronous Workflows | `manuscript` | `2.0.0` | `BACK301-S06` |

#### SE330 — Software Architecture and Evolution

300-level · 3 lectures · course status `complete` · `SE/SE330-software-architecture/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `SE330-L01` | The Art of Software Architecture | `manuscript` | `2.0.0` | `ENG401-S01` |
| `SE330-L02` | Architecture Patterns and Their Consequences | `manuscript` | `2.0.0` | `ENG401-S02` |
| `SE330-L03` | Maintaining and Evolving Real Software | `manuscript` | `2.0.0` | `ENG401-S11` |

#### SE340 — Linux, Cloud Infrastructure, and Delivery

300-level · 4 lectures · course status `complete` · `SE/SE340-cloud-and-delivery/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `SE340-L01` | Linux and the Server Environment | `manuscript` | `2.0.0` | `ENG401-S03` |
| `SE340-L02` | Containers and Modern Deployment | `manuscript` | `2.0.0` | `ENG401-S04` |
| `SE340-L03` | Cloud Infrastructure and AWS Architecture | `manuscript` | `2.0.0` | `ENG401-S05` |
| `SE340-L04` | CI/CD and Infrastructure as Code | `manuscript` | `2.0.0` | `ENG401-S06` |

#### SE440 — Production Reliability and Quality Engineering

400-level · 3 lectures · course status `complete` · `SE/SE440-production-reliability/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `SE440-L01` | Observability: Understanding Production Systems | `manuscript` | `2.0.0` | `ENG401-S07` |
| `SE440-L02` | Reliability Engineering and Incident Response | `manuscript` | `2.0.0` | `ENG401-S08` |
| `SE440-L03` | Testing Strategies for Complex Systems | `manuscript` | `2.0.0` | `ENG401-S10` |

#### SE490 — Architecture and Systems Design Studio

400-level · 5 lectures · course status `complete` · `SE/SE490-architecture-studio/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `SE490-L01` | Putting It Together: Understanding a Running Application | `manuscript` | `2.0.0` | `CS101-S12` |
| `SE490-L02` | Architecture Workshop: Design a Modern Web Product | `manuscript` | `2.0.0` | `WEB201-S12` |
| `SE490-L03` | System Design Workshop: Build for 100× Traffic | `manuscript` | `2.0.0` | `BACK301-S12` |
| `SE490-L04` | Senior Engineer Workshop: Architecture Review | `manuscript` | `2.0.0` | `ENG401-S12` |
| `SE490-L05` | Architecture Workshop: Design a Production Agentic SaaS | `manuscript` | `2.0.0` | `AI501-S12` |

### AI — Artificial Intelligence

#### AI310 — Language Models and Retrieval Engineering

300-level · 4 lectures · course status `complete` · `AI/AI310-language-models-and-retrieval/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `AI310-L01` | How Modern Language Models Actually Work | `manuscript` | `2.0.0` | `AI501-S01` |
| `AI310-L02` | Engineering Applications Around LLMs | `manuscript` | `2.0.0` | `AI501-S02` |
| `AI310-L03` | Embeddings, Semantic Search, and Retrieval | `manuscript` | `2.0.0` | `AI501-S03` |
| `AI310-L04` | Retrieval-Augmented Generation | `manuscript` | `2.0.0` | `AI501-S04` |

#### AI410 — Agentic AI Systems and Production Engineering

400-level · 7 lectures · course status `complete` · `AI/AI410-agentic-ai-systems/`

| ID | Lecture | Manuscript | Edition | Legacy |
| --- | --- | --- | --- | --- |
| `AI410-L01` | Tool Calling and Connecting AI to Software | `manuscript` | `2.0.0` | `AI501-S05` |
| `AI410-L02` | Agents: From Model Calls to Autonomous Workflows | `manuscript` | `2.0.0` | `AI501-S06` |
| `AI410-L03` | Agent Memory, Context, and State | `manuscript` | `2.0.0` | `AI501-S07` |
| `AI410-L04` | MCP and the Agent Integration Ecosystem | `manuscript` | `2.0.0` | `AI501-S08` |
| `AI410-L05` | Multi-Agent Systems and Orchestration | `manuscript` | `2.0.0` | `AI501-S09` |
| `AI410-L06` | Evaluating Nondeterministic Software | `manuscript` | `2.0.0` | `AI501-S10` |
| `AI410-L07` | Security, Reliability, and Economics of AI Systems | `manuscript` | `2.0.0` | `AI501-S11` |

## Planned electives

Elective status means optional in the programme — not a different ID scheme. Each starts with one lecture when written; courses may grow organically.

| Code | Title | Status | Builds on | Notes |
| --- | --- | --- | --- | --- |
| `CS350` | Advanced PostgreSQL Engineering | `planned` | `CS330` | First lecture candidate: PostgreSQL Internals — MVCC, Vacuum, and Bloat |
| `CS360` | Algorithms and Coding Interview Lab | `planned` | `CS110` | Algorithmic patterns for senior engineering interviews — distinct from listening to CS110 theory. Development priority #3 after CS340 and CS320 reorganization. |
| `CS370` | Game Engines and Simulation Systems | `planned` | `CS220`, `CS320` | Independent exploration — game loops, entities, simulation time |
| `SE250` | Modern Frontend Frameworks | `planned` | `SE240` | React for Vue Developers as first lecture candidate |
| `SE350` | Advanced Software Design Patterns | `planned` | `SE330` |  |
| `SE450` | Kubernetes and Platform Engineering | `planned` | `SE340`, `SE440` | Practical platform knowledge beyond SE340's Docker/AWS intro. Development priority #4 among planned electives (after CS340, CS320 expansion, CS360). |
| `SE460` | Performance Engineering | `planned` | `CS320`, `SE440` |  |
| `AI450` | Advanced Agentic Systems | `planned` | `AI410` | Durable agents, workflow engines, advanced evaluations |
| `SE360` | Practical Terraform and Cloud Delivery | `planned` | `SE340` |  |
| `CS240` | Linux Internals for Application Engineers | `planned` | `CS320`, `SE340` |  |
| `SE370` | Application Security Deep Dive | `planned` | `SE310` |  |
| `OPEN110` | Mobile Application Architecture | `planned` | — | Independent elective — not forced under a core course |

## Maintenance

1. Edit [`curriculum.yaml`](curriculum.yaml).
2. Run `python tools/sync_manuscript_meta.py` after changing manuscript/edition fields.
3. Run `python tools/curriculum_migrate.py --dry-run` then `--apply` or `--rewrite-only` for reshuffles.
4. Run `python tools/curriculum_validate.py`.
5. Re-render this file: `python tools/curriculum_render.py`.
6. Personal learning: `python tools/progress_init.py --student <id>` then `progress_render.py`.

