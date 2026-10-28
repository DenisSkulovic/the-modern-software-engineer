"""One-shot SE215 stubs + editorial TODOs. Delete after use."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SE215 = ROOT / "SE" / "SE215-software-engineering-ecosystem"
SE215.mkdir(parents=True, exist_ok=True)

lectures = [
    {
        "id": "SE215-L01",
        "num": "01",
        "title": "The People and Teams Behind Software",
        "slug": "the-people-and-teams-behind-software",
        "prev": None,
        "next": "SE215-L02",
        "opening": (
            "A company wants to launch a new booking feature. The developer receives a ticket "
            "but gradually discovers that delivering the feature requires product decisions, "
            "UX design, security considerations, testing, deployment, monitoring, and business measurement."
        ),
        "objective": (
            "Understand how a software product moves from business requirement to operating system, "
            "and which people or teams contribute at each stage."
        ),
        "coverage": (
            "What product managers, engineering managers, tech leads, UX/UI designers, QA engineers, "
            "DevOps engineers, platform engineers, SREs, security engineers, data engineers, analysts, "
            "and technical writers do. Responsibilities, ownership boundaries, handoffs, "
            "cross-functional collaboration, and how organizational structures differ between startups "
            "and larger companies."
        ),
        "boundary": (
            "This is an organizational map, not a detailed course in Scrum, cloud infrastructure, "
            "design, or data engineering. Those subjects have their own lectures."
        ),
        "expected": (
            "Given a new feature, identify its relevant stakeholders, shared responsibilities, "
            "dependencies, and potential coordination failures."
        ),
        "exercise": (
            "Map the people involved in releasing a hotel-booking feature and explain who owns each decision."
        ),
    },
    {
        "id": "SE215-L02",
        "num": "02",
        "title": "How Engineering Work Gets Planned and Delivered",
        "slug": "how-engineering-work-gets-planned-and-delivered",
        "prev": "SE215-L01",
        "next": "SE215-L03",
        "opening": (
            "A team completes every sprint but repeatedly misses its product commitments. "
            "Engineers are busy, tickets are being closed, and yet important features remain unfinished."
        ),
        "objective": (
            "Understand how engineering organizations plan, coordinate, measure, and improve software delivery."
        ),
        "coverage": (
            "Agile principles versus Agile ceremonies; Scrum, Kanban, and hybrid workflows; backlogs, "
            "stories, epics, tasks, acceptance criteria, sprint planning, estimation, story points, "
            "work in progress, cycle time, lead time, blockers, dependencies, priorities, roadmaps, "
            "and retrospectives. Why estimation is uncertain, why activity is not the same as delivery, "
            "and why reducing work in progress can improve throughput. Introduce Jira and similar tools "
            "as implementations of workflows rather than as the workflows themselves."
        ),
        "boundary": (
            "Avoid Scrum certification trivia and lengthy descriptions of ceremonies. Focus on practical "
            "engineering decisions and common interview questions about team processes."
        ),
        "expected": (
            "Explain Scrum versus Kanban, defend a task breakdown, identify delivery bottlenecks, "
            "and discuss changing priorities professionally."
        ),
        "exercise": "Convert a vague feature request into an incrementally deliverable backlog.",
    },
    {
        "id": "SE215-L03",
        "num": "03",
        "title": "Git, Pull Requests, and Collaborative Delivery",
        "slug": "git-pull-requests-and-collaborative-delivery",
        "prev": "SE215-L02",
        "next": "SE215-L04",
        "opening": (
            "Three engineers develop features simultaneously. One urgent production fix must ship "
            "while two unfinished features remain in progress. The team's branching and release strategy "
            "determines whether delivery is straightforward or chaotic."
        ),
        "objective": "Understand the collaboration and release consequences of common Git workflows.",
        "coverage": (
            "Git as a distributed version-control system; commits, branches, merges, rebases, cherry-picks, "
            "conflicts, trunk-based development, feature branching, pull requests, branch protection, "
            "code-review etiquette, commit hygiene, release tags, and feature flags. Trade-offs between "
            "merge commits, rebasing, and squash merges. Why small changes are easier to review and release, "
            "and how Git workflows interact with CI/CD."
        ),
        "boundary": (
            "Not a beginner command-by-command Git tutorial. Assume familiarity with basic add, commit, "
            "push, pull, and branching."
        ),
        "expected": (
            "Choose a sensible branching/review strategy for a team, explain trade-offs, "
            "and handle common collaborative development scenarios."
        ),
        "exercise": (
            "Design a safe workflow for an urgent hotfix while multiple incomplete features exist."
        ),
    },
    {
        "id": "SE215-L04",
        "num": "04",
        "title": "Repositories, Monorepos, and Build Systems",
        "slug": "repositories-monorepos-and-build-systems",
        "prev": "SE215-L03",
        "next": "SE215-L05",
        "opening": (
            "A company has a frontend, backend API, background workers, shared TypeScript packages, "
            "and deployment tooling. Engineers disagree about whether they belong in one repository or five."
        ),
        "objective": (
            "Understand the trade-offs behind repository organization and tooling in multi-application "
            "software projects."
        ),
        "coverage": (
            "Monorepos versus multirepos; project and package boundaries; directory organization; "
            "dependency graphs; package managers and workspaces; npm, pnpm, Yarn, Nx, Turborepo; "
            "task orchestration; incremental builds; caching; shared contracts; generated clients; "
            "code ownership; independent versioning and releases; CI implications. When a monorepo is "
            "useful and when it becomes cumbersome. Distinguish repository structure, application "
            "architecture, and deployment architecture."
        ),
        "boundary": (
            "Do not repeat Clean Architecture, DDD, or microservice fundamentals from SE330 and CS430. "
            "Refer to them when discussing dependency and deployment boundaries. A monorepo does not "
            "imply a monolith, and a multirepo does not imply microservices."
        ),
        "expected": (
            "Defend a monorepo or multirepo choice and explain how changes, builds, tests, "
            "and deployments flow through it."
        ),
        "exercise": (
            "Design a repository layout for a TypeScript frontend, Node.js API, Python worker, "
            "shared API schemas, and infrastructure code."
        ),
    },
    {
        "id": "SE215-L05",
        "num": "05",
        "title": "Cloud Platforms and Service Models",
        "slug": "cloud-platforms-and-service-models",
        "prev": "SE215-L04",
        "next": "SE215-L06",
        "opening": (
            "A startup wants to deploy a conventional SaaS application. Three consultants propose AWS, "
            "Google Cloud, and Microsoft Azure. All claim their preferred platform is the obvious choice."
        ),
        "objective": (
            "Develop a cloud-provider-neutral mental model of how ordinary applications are hosted and operated."
        ),
        "coverage": (
            "IaaS, PaaS, serverless, managed services, shared responsibility, regions, availability zones, "
            "networking, identity, compute, object storage, managed databases, queues, observability, "
            "and pricing. Equivalent service categories in AWS, GCP, and Azure. Why comparing products by "
            "names alone can be misleading. Vendor lock-in, portability, regional availability, "
            "and cost surprises at a high level."
        ),
        "boundary": (
            "SE340-L03 already teaches AWS architecture in depth. Do not regenerate that chapter under "
            "a different title. This lecture is a conceptual provider comparison."
        ),
        "expected": (
            "Sketch how a conventional SaaS could be deployed on any of the three major providers and "
            "identify what the application team would still be responsible for."
        ),
        "exercise": "Map a simple Node.js/PostgreSQL application to an AWS, GCP, and Azure architecture.",
    },
    {
        "id": "SE215-L06",
        "num": "06",
        "title": "DevOps, Platform Engineering, and Operational Ownership",
        "slug": "devops-platform-engineering-and-operational-ownership",
        "prev": "SE215-L05",
        "next": "SE215-L07",
        "opening": (
            "Developers say their code works locally. The platform team says deployment configuration "
            "is correct. The application repeatedly fails in production, and nobody considers the entire "
            "delivery path their responsibility."
        ),
        "objective": (
            "Understand the operational organization surrounding software delivery and which "
            "responsibilities remain with application engineers."
        ),
        "coverage": (
            "DevOps as an approach to collaboration and delivery; responsibilities of developers, "
            "infrastructure engineers, DevOps engineers, platform teams, and SREs; self-service platforms; "
            "environments; CI/CD workflows; infrastructure as code; GitOps; deployment ownership; secrets; "
            "observability; on-call responsibility; SLOs; incident response; and operational readiness. "
            "Distinguish platform engineering from SRE and from conventional infrastructure administration."
        ),
        "boundary": (
            "SE340 already covers CI/CD and Terraform mechanisms. SE450 covers Kubernetes and GitOps. "
            "SE440 covers reliability and SRE practices. This lecture connects the responsibilities and "
            "workflows rather than repeating their technical details."
        ),
        "expected": (
            "Explain what a DevOps/platform team actually provides, what a developer should own, "
            "and how to investigate a deployment problem collaboratively."
        ),
        "exercise": (
            "Design a responsibility map for an application progressing through build, testing, staging, "
            "production deployment, monitoring, and incident recovery."
        ),
    },
    {
        "id": "SE215-L07",
        "num": "07",
        "title": "Owning End-to-End Testing",
        "slug": "owning-end-to-end-testing",
        "prev": "SE215-L06",
        "next": "SE215-L08",
        "opening": (
            "An application has excellent unit-test coverage, yet customers cannot complete checkout "
            "after a deployment. The team has E2E tests, but they either rely on mocked APIs or fail "
            "unpredictably."
        ),
        "objective": (
            "Understand how to design and maintain an E2E suite that verifies meaningful user workflows "
            "without becoming unreliable or excessively slow."
        ),
        "coverage": (
            "Browser E2E testing in practice using Playwright as the principal example; test-suite "
            "architecture; fixtures; test data; authentication setup; browser contexts; stable selectors; "
            "accessibility-oriented locators; synchronization; retries; parallel execution; test isolation; "
            "mocked versus real backends; local and CI environments; trace artifacts; screenshots; "
            "flakiness investigation; smoke suites; regression suites; and ownership of failures. "
            "Distinguish browser-component testing, browser-based integration testing, and full-system "
            "E2E testing."
        ),
        "boundary": (
            "SE240-L06 and SE440-L03 already cover the testing philosophy and test layers. This lecture "
            "emphasizes practical ownership and implementation."
        ),
        "expected": (
            "Design a Playwright test strategy for a full-stack application, choose what to mock, "
            "prepare test data, and diagnose flaky tests."
        ),
        "exercise": (
            "Build a small Playwright suite for a booking flow, including deterministic test data, "
            "successful checkout, validation failure, and one network-failure scenario. The practical "
            "lab may be substantially longer than the spoken lecture."
        ),
    },
    {
        "id": "SE215-L08",
        "num": "08",
        "title": "Technical SEO and Web Discoverability",
        "slug": "technical-seo-and-web-discoverability",
        "prev": "SE215-L07",
        "next": "SE215-L09",
        "opening": (
            "A company rebuilds its public hotel catalogue using a modern JavaScript application. "
            "The pages look better and load quickly for users, yet organic search traffic begins falling."
        ),
        "objective": (
            "Understand how a technically functioning web application can fail to become discoverable "
            "through search engines."
        ),
        "coverage": (
            "Search-engine crawling, rendering, indexing, crawlability, indexability, robots.txt, "
            "XML sitemaps, canonical URLs, redirects, HTTP statuses, meta robots directives, page titles "
            "and descriptions, structured data, internal linking, duplicate URLs, internationalization "
            "and hreflang, mobile usability, performance, Core Web Vitals, and search diagnostics. "
            "How CSR, SSR, and static generation affect discoverability. Google Search Console and "
            "diagnostic workflows. Distinguish developer-owned technical SEO from content strategy "
            "and marketing."
        ),
        "boundary": (
            "SE240-L04 already explains rendering strategies and their SEO implications. Preserve that "
            "discussion; this lecture owns the broader technical SEO overview."
        ),
        "expected": (
            "Diagnose common technical SEO problems and communicate effectively with SEO specialists "
            "and product teams."
        ),
        "exercise": (
            "Audit a small public website's indexing directives, metadata, canonical URLs, sitemap, "
            "and structured data."
        ),
    },
    {
        "id": "SE215-L09",
        "num": "09",
        "title": "Data Engineering for Application Developers",
        "slug": "data-engineering-for-application-developers",
        "prev": "SE215-L08",
        "next": "SE215-L10",
        "opening": (
            "A booking application records reservations correctly in PostgreSQL, but the analytics "
            "dashboard reports conflicting revenue totals. The data team says the pipeline is working, "
            "while application developers say the database is correct."
        ),
        "objective": (
            "Understand the complete journey from operational data to reliable analytical information."
        ),
        "coverage": (
            "OLTP versus analytical workloads; ETL and ELT; event production; change data capture; "
            "batch processing; stream processing; message brokers; warehouses; data lakes; lakehouses; "
            "data transformation; orchestration; backfills; schema evolution; data contracts; lineage; "
            "data quality; deduplication; late-arriving events; and reconciliation. Technologies through "
            "responsibilities: Kafka, Airflow, dbt, analytical databases, and managed data-platform "
            "services. Follow one business event from the application database through ingestion and "
            "transformation into an analytical report."
        ),
        "boundary": (
            "CS340 already covers storage engines, specialized data systems, analytical databases, "
            "replication, CDC, and source-of-truth questions. This lecture connects those components "
            "into a data-engineering workflow rather than repeating database theory."
        ),
        "expected": (
            "Sketch an operational-to-analytical pipeline, recognize common failure modes, and explain "
            "the developer's responsibility for producing trustworthy data."
        ),
        "exercise": (
            "Design a booking-events pipeline and identify where duplicates, missing events, late events, "
            "and schema changes must be handled."
        ),
    },
    {
        "id": "SE215-L10",
        "num": "10",
        "title": "Working With Product, Design, and Analytics",
        "slug": "working-with-product-design-and-analytics",
        "prev": "SE215-L09",
        "next": None,
        "opening": (
            "A designer creates a beautiful booking flow, a developer implements it exactly, and the "
            "product manager declares the feature complete. Conversion nevertheless falls after release."
        ),
        "objective": (
            "Understand how software developers participate in product outcomes beyond coding a "
            "completed specification."
        ),
        "coverage": (
            "Product discovery versus delivery; translating business goals into requirements; functional "
            "and nonfunctional requirements; user journeys; wireframes; prototypes; Figma and developer "
            "handoff; design systems; design tokens; responsive behavior; accessibility; component "
            "consistency; product analytics; funnels; conversion; retention; A/B testing; experimentation; "
            "feature rollout; and post-release learning."
        ),
        "boundary": (
            "Do not teach professional visual design, detailed Figma operation, or advanced statistical "
            "experimentation. Refer to CS120 for statistical reasoning and SE240 for frontend implementation."
        ),
        "expected": (
            "Translate a design and product objective into a deliverable feature, identify relevant "
            "measurements, and participate intelligently in discussions about usability and conversion."
        ),
        "exercise": (
            "Take a booking-flow redesign and construct a plan covering implementation, accessibility, "
            "release, instrumentation, and success measurement."
        ),
    },
]


def stub_text(L: dict) -> str:
    prev = "null" if L["prev"] is None else L["prev"]
    nxt = "null" if L["next"] is None else L["next"]
    return f"""---
id: {L['id']}
course: SE215
title: "{L['title']}"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: {prev}
next: {nxt}
---

# SE215 — The Software Engineering Ecosystem
## Lecture {L['num']}: {L['title']}

*{L['opening']}*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

**Pedagogical model:** short orientation elective. Target spoken duration ordinarily 18–25 minutes (~2,800–4,000 spoken words). Conceptual and practically informed; not a specialist qualification. Structure: Part I — Intuition, Part II — Deep Dive, oral examination, solutions, one Mental Model, Next Lecture hook; practical material after the spoken-end marker; Dense Cheatsheet at the end.

### Learning Objective

{L['objective']}

### Opening Problem

{L['opening']}

### Planned Coverage

{L['coverage']}

### Scope Boundaries

{L['boundary']}

### Expected Understanding

{L['expected']}

### Suggested Exercise / Lab

{L['exercise']}

### Planned Manuscript Structure

1. Narrative hook and sustained engineering case study.
2. Technical development of the underlying mechanisms.
3. Practical trade-offs and realistic failure scenarios.
4. Oral examination.
5. Solutions and discussion.
6. The Mental Model Worth Keeping.
7. Next Lecture or course-completion transition.
8. Optional Practical Lab, after the spoken lecture ends.
9. Further Reading.
10. Dense Cheatsheet — Interview Glance Card, last, inside one fenced text block.

### Cross-references (for future authorship)

Refer to deeper curriculum coverage by lecture ID rather than duplicating technical depth. SE215 is a gateway into the existing library, not a replacement for it.

<!-- Full manuscript to be generated later. -->
"""


for L in lectures:
    path = SE215 / f"{L['id']}-{L['slug']}.md"
    path.write_text(stub_text(L), encoding="utf-8", newline="\n")
    print("wrote", path.relative_to(ROOT))


TODOS = [
    (
        "SE/SE240-frontend-engineering/SE240-L04-delivering-modern-web-applications.md",
        """<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE215-L08
Existing section teaches rendering strategy and introductory SEO.
After SE215-L08 exists, add a concise cross-reference to its broader
technical SEO coverage. Preserve the current rendering explanation.
Do not duplicate or move the entire section.
-->""",
    ),
    (
        "SE/SE240-frontend-engineering/SE240-L06-testing-and-reliability-in-the-frontend.md",
        """<!--
EDITORIAL-TODO: P2 / SCOPE_AND_DEDUPLICATE / SE215-L07
Keep the conceptual treatment of unit, component, integration, and E2E testing,
including test confidence, flakiness, and accessibility.
When SE215-L07 exists, compare the practical Playwright examples and remove
only unnecessary repetition if appropriate.
SE215-L07 should own hands-on browser-test infrastructure, fixtures, test data,
and CI practices.
Do not weaken the existing explanation of testing strategy.
-->""",
    ),
    (
        "SE/SE440-production-reliability/SE440-L03-testing-strategies-for-complex-systems.md",
        """<!--
EDITORIAL-TODO: P2 / SCOPE_AND_CROSS_REFERENCE / SE215-L07
Preserve broad testing strategy: contracts, integration boundaries, concurrency,
asynchronous workflows, property-based tests, and resilience.
Cross-reference SE215-L07 for practical browser E2E ownership.
Avoid duplicating a full Playwright tutorial inside this general testing-strategy lecture.
-->""",
    ),
    (
        "SE/SE340-cloud-and-delivery/SE340-L03-cloud-infrastructure-and-aws-architecture.md",
        """<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE215-L05
Keep this as the detailed AWS architecture chapter.
After SE215-L05 is authored, cross-reference it for the AWS/GCP/Azure conceptual comparison.
Do not duplicate the AWS-specific service explanations in the new survey lecture.
-->""",
    ),
    (
        "SE/SE340-cloud-and-delivery/SE340-L04-cicd-and-infrastructure-as-code.md",
        """<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE215-L06, SE215-L03
Keep detailed CI/CD, Terraform, infrastructure state, and deployment mechanics here.
Cross-reference SE215-L06 for DevOps and platform-team responsibilities, and SE215-L03
for collaborative Git/release workflows.
Do not move Terraform's technical content into the survey course.
-->""",
    ),
    (
        "SE/SE450-kubernetes-and-platform/SE450-L07-releases-gitops-and-platform-observability.md",
        """<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE215-L06
Preserve Kubernetes-specific deployment controllers, Helm, GitOps reconciliation,
and progressive-delivery mechanics.
Cross-reference SE215-L06 for the wider DevOps/platform engineering organizational context.
Do not expand the SE215 lecture into another Kubernetes course.
-->""",
    ),
    (
        "SE/SE330-software-architecture/SE330-L02-architecture-patterns-and-their-consequences.md",
        """<!--
EDITORIAL-TODO: P2 / CLARIFY_BOUNDARY / SE215-L04
This manuscript should remain the primary treatment of modular monoliths, internal
module boundaries, layered architecture, vertical slices, hexagonal architecture, and DDD.
When SE215-L04 exists, add an explicit distinction between codebase/repository
organization and runtime/deployment architecture.
A monorepo is not synonymous with a monolith.
Cross-reference CS430-L04 for distributed service boundaries and microservices.
-->""",
    ),
    (
        "CS/CS430-distributed-systems/CS430-L04-microservices-events-and-service-boundaries.md",
        """<!--
EDITORIAL-TODO: P2 / CLARIFY_BOUNDARY / SE215-L04
This manuscript should remain the primary treatment of microservice architecture,
service autonomy, data ownership, distributed communication, outbox patterns, sagas,
and distributed-monolith failure modes.
Cross-reference SE330-L02 for in-process modular architecture and SE215-L04 for
repository topology.
Do not create a second introductory microservices lecture in SE215.
-->""",
    ),
    (
        "CS/CS340-data-systems-beyond-relational/CS340-L06-specialized-data-systems.md",
        """<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE215-L09
Preserve the technical introduction to Redis, DynamoDB, Elasticsearch/OpenSearch,
analytical stores, and specialized data models.
When SE215-L09 exists, cross-reference it for data-engineering pipelines and
organizational responsibilities.
Do not repeat the Elasticsearch introduction in the SEO lecture. Search-engine
infrastructure and search-engine optimization are distinct subjects.
-->""",
    ),
    (
        "CS/CS340-data-systems-beyond-relational/CS340-L07-the-data-architecture-workshop.md",
        """<!--
EDITORIAL-TODO: P2 / CROSS_REFERENCE / SE215-L09
Retain the architectural workshop and its source-of-truth, data synchronization,
and analytics decisions.
Cross-reference SE215-L09 once that lecture introduces the complete
operational-to-analytical data pipeline.
Do not move the advanced data-architecture decisions into the survey lecture.
-->""",
    ),
    (
        "SE/SE240-frontend-engineering/SE240-L02-frontend-architecture-beyond-components.md",
        """<!--
EDITORIAL-TODO: P3 / CROSS_REFERENCE / SE215-L10, SE215-L04
Preserve feature organization, dependency direction, composables, stores, services,
and frontend module boundaries.
Cross-reference SE215-L10 for design systems, Figma handoff, product collaboration,
and measurement.
Cross-reference SE215-L04 where repository/package organization affects frontend architecture.
-->""",
    ),
    (
        "SE/SE330-software-architecture/SE330-L03-maintaining-and-evolving-real-software.md",
        """<!--
EDITORIAL-TODO: P3 / CROSS_REFERENCE / SE215-L02, SE215-L03
Keep architectural evolution, technical debt, refactoring economics, and team incentives.
Cross-reference SE215-L02 for planning and delivery processes and SE215-L03 for
collaborative code-change practices.
Avoid turning this architectural-maintenance chapter into an Agile-process manual.
-->""",
    ),
    (
        "CS/CS230-computer-networks/CS230-L07-the-life-of-a-network-connection.md",
        """<!--
EDITORIAL-TODO: P3 / AUDIT_DENSITY
Original spoken length previously measured at approximately 69 minutes.
Future TODO: Review whether the lecture can be shortened or divided into clearer
conceptual segments without losing TCP state, socket behavior, failure ambiguity,
and important connection-lifecycle details.
Avoid duplicating material now handled by CS320-L05.
Do not automatically remove technical depth. Do not apply automatic word-count reductions.
First identify repeated claims, overlapping examples, and unnecessary restatements.
Measure spoken length before and after any revision and verify subject coverage.
-->""",
    ),
    (
        "CS/CS230-computer-networks/CS230-L08-tls-and-the-architecture-of-trust.md",
        """<!--
EDITORIAL-TODO: P3 / AUDIT_DENSITY
Previously measured at approximately 64 spoken minutes.
Future TODO: Examine repetitive introductions to cryptographic primitives versus
necessary explanations of handshake mechanics, identity verification, certificate
chains, trust, and termination boundaries.
Maintain a coherent cryptographic mental model.
Do not apply automatic word-count reductions.
-->""",
    ),
    (
        "CS/CS230-computer-networks/CS230-L11-network-forensics-for-software-engineers.md",
        """<!--
EDITORIAL-TODO: P3 / AUDIT_DENSITY
Previously measured at approximately 60 spoken minutes.
Future TODO: Preserve its distinct diagnostic cases but review whether repeated
investigative principles can be consolidated.
A capstone can legitimately be longer than an ordinary lecture.
Do not apply automatic word-count reductions.
-->""",
    ),
    (
        "CS/CS110-foundations-of-computation/CS110-L05-searching-sorting-and-finding-shortcuts.md",
        """<!--
EDITORIAL-TODO: P3 / AUDIT_DENSITY
Previously measured at approximately 53 spoken minutes.
Future TODO: Review for unnecessary introductory repetition after CS360 is complete.
Keep CS110 focused on algorithmic understanding; CS360 should focus on active
interview problem solving.
Do not strip foundational algorithms from CS110 simply because CS360 contains
related exercises.
Do not apply automatic word-count reductions.
-->""",
    ),
    (
        "SE/SE450-kubernetes-and-platform/SE450-L04-scheduling-resources-and-autoscaling.md",
        """<!--
EDITORIAL-TODO: P3 / AUDIT_DENSITY
Previously measured at approximately 52 spoken minutes.
Future TODO: Review overlap with CS320-L02 on CPU quotas and contention, and with
CS320-L04 on memory pressure and cgroups.
Keep the Kubernetes scheduler, placement, resource-request, and autoscaling details here.
Consider replacing repeated OS explanations with concise reminders and cross-references.
Do not apply automatic word-count reductions.
-->""",
    ),
]


def insert_todo(rel: str, comment: str) -> None:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    if "EDITORIAL-TODO" in text and comment.splitlines()[1] in text:
        print("skip (already present)", rel)
        return
    if not text.startswith("---"):
        raise SystemExit(f"no frontmatter: {rel}")
    end = text.find("\n---", 3)
    if end < 0:
        raise SystemExit(f"no closing frontmatter: {rel}")
    close = end + len("\n---")
    # insert immediately after closing delimiter
    new = text[:close] + "\n\n" + comment + "\n" + text[close:]
    # collapse accidental triple blank runs later if needed
    path.write_text(new, encoding="utf-8", newline="\n")
    print("todo", rel)


for rel, comment in TODOS:
    insert_todo(rel, comment)

print("housekeeping script finished")
