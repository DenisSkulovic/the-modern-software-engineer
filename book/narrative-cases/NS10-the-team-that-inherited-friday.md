# NS10 — The Team That Inherited Friday

*A new engineering team takes over a neglected SaaS product, and learns that the hardest system to understand is often the one made of people, commitments, and code no one trusts.*

This is a fictional engineering organization, not a portrayal of any particular employer. The practices and technical failures are realistic examples.

## Monday — The welcome meeting

The new hires at NorthstarOps arrived to find a whiteboard covered with colored rectangles. NorthstarOps sold compliance workflow software to medium-sized manufacturers. Customers uploaded evidence, assigned reviews, tracked deadlines, and exported audit packets. The product made money, but a string of rushed releases had left the engineering organization exhausted.

Gabe, the new engineering manager, introduced the team. Sana would lead frontend work, Oliver would own backend reliability, Evie would handle QA and release coordination, and Tomas from platform would help with infrastructure. Their immediate assignment was to stabilize the product while completing a customer-requested export feature.

The previous team had left a long README, a collection of architecture diagrams, and almost no agreement about which diagrams were current. The newest diagram showed six microservices. The cloud account contained eleven deployments, three old queues, two Redis instances, a PostgreSQL primary, a reporting replica, and a forgotten worker that still ran every night.

“Which of these is production?” Sana asked.

Nobody answered with confidence.

Gabe refused to launch a grand rewrite. First, the team needed to identify the system that actually served customers. They traced the browser request through the CDN, API gateway, Node.js application, database, queues, and report workers. They compared deployed image digests with repository tags and discovered that a deployment labeled `release-2026.10` pointed at an image built from a later hotfix commit. The naming was descriptive, not authoritative.

Tomas said they should start with evidence: running workloads, configuration, traffic, logs, and actual dependencies. The old diagrams were hypotheses about the system. Useful hypotheses, but still hypotheses.

## The one-hour walk through production

Gabe asked every engineer to narrate one customer journey without relying on the architecture diagram. Sana chose a reviewer opening an audit from the dashboard. The browser loaded a cached application bundle, authenticated the session, fetched the list of audits, and displayed permission-filtered projects. The user clicked a project, added a note, and requested an export. Each action crossed a different set of responsibilities.

Oliver found that the audit-list endpoint performed a database lookup for each project owner. It was an ordinary N-plus-one query pattern: one query fetched the projects, then a separate query loaded details for every row. With a small test account it looked harmless. With a customer holding thousands of audits, database round trips dominated response time even when the SQL in each query was individually fast.

The team changed the data-access shape so the endpoint fetched the required related information in a bounded number of queries, with an index supporting the actual filter and sort. They verified the plan using representative data rather than assuming that any existing index was sufficient. On page one, performance improved. On very deep pages, offset pagination still required the database to traverse many earlier results, so they considered cursor-based access for workflows where stable ordering and sequential navigation made sense.

Sana then profiled the browser. The API was no longer the largest delay. The frontend transformed and sorted a large response again on every interaction, and an unnecessary component state mirror caused redundant work. She moved derived values out of stored state, eliminated the duplicate sort, and measured the resulting interaction latency on a slower laptop.

Gabe wrote down the sequence: the page was slow, but not for one reason. The bottleneck moved as the team repaired it. End-to-end performance required observing the request path and the browser's work, not measuring only the handler. It was a useful practice for new hires because it reconnected frontend, backend, SQL, and observability into one customer action.

## Tuesday — The green pipeline with a red production

The team opened the CI/CD dashboard. Most builds had passed. Yet production incidents had followed several green releases. Evie asked a deceptively simple question: “What does passing mean here?”

The pipeline ran unit tests on isolated modules, type checks on the frontend, and a container build. It didn't exercise database migrations against representative data. It didn't verify that old and new APIs worked during a rolling deployment. It didn't test that report workers could consume new job payloads. And it published an image with a mutable tag that the deployment system could resolve later to a different build.

A passing pipeline proved that the tested steps passed against the inputs they used. It did not prove that production was safe under every combination of versions, state, and load.

Tomas changed image promotion to use immutable digests and made the deployment record include the exact commit and artifact. Evie introduced a small staging smoke test with realistic integration paths: login, open an audit, submit evidence, queue an export, and download the resulting file. She resisted demands for hundreds of fragile end-to-end tests. They needed a focused set of checks that would catch broken boundaries, complemented by faster unit and integration tests.

Oliver found an additional problem in the database migration script. A previous release had renamed a column while older application containers were still serving requests. It had worked in staging because staging had only one instance and little traffic. In production, an old instance crashed when it encountered the new schema.

The team adopted a rule: additive database changes first, compatible application rollout second, and removal of old schema only after obsolete writers had disappeared. Feature flags would control user-visible behavior, but wouldn't be misused as a magical rollback for incompatible migrations.

The team wrote a release checklist, not as a ritual of signatures, but as a shared understanding of what had to be true before and after a deployment.

## Wednesday — The export that worked for ten customers

The new feature seemed straightforward. A customer administrator chose a date range, clicked Export, and downloaded a ZIP containing audit evidence and a CSV summary. The old prototype handled small accounts synchronously: fetch relevant database rows, retrieve files from object storage, create a ZIP in memory, and send it as the HTTP response.

On a test account with ten files, it was fast. On a real manufacturer with several years of audits, it exhausted process memory and timed out. The CDN returned a gateway error while the server continued doing some work. Customers clicked again, creating competing exports and even more load.

Oliver proposed converting exports into background jobs. The HTTP API would validate the request, create a durable export resource, and enqueue work. The browser would receive an export ID and could check status later. Completed archives would be stored in object storage with controlled access and retention. This kept a long-running business operation from living inside one fragile request-response window.

Sana designed the UI to show queued, assembling, ready, and failed states. She deliberately avoided pretending that a `202 Accepted` response meant the ZIP existed. It meant the system had accepted responsibility for processing a request. The user could navigate away and return without losing the job.

Evie asked what happened when the same administrator clicked Export twice or retried after a network error. Oliver initially said the queue deduplicated job IDs. Then he reconsidered. Queue-level deduplication wouldn't necessarily protect repeated business operations across retries, retention windows, or different producers. They needed an idempotent export request model tied to account, request identity, and parameters, with safe handling of concurrent submissions.

The worker streamed source data and archive output where supported rather than collecting entire reports in process memory. It used bounded concurrency when fetching source files, protected the database from expensive unbounded queries, and recorded progress durably. Individual data records came from a snapshot policy the product team had to approve: was the export supposed to represent the account at job creation, job completion, or an explicitly selected point in time?

That question wasn't a performance optimization. It determined what the compliance document meant.

## The meeting about ownership that nobody scheduled

The new export workflow exposed friction between teams. Oliver was comfortable with backend state transitions; Sana understood the user journey; Evie understood where tests needed realistic state; Tomas understood cloud permissions and deployment behavior. Each could defend their own area, but nobody had a shared definition of when the feature was complete.

Gabe invited customer support and the compliance product owner into a review. They discovered that “export audit evidence” meant different things to different customers. One wanted a snapshot of evidence as it existed when an audit closed. Another wanted the latest documents even if they changed after export began. A third wanted an immutable archive suitable for an external auditor. Those choices affected database snapshot semantics, storage retention, access checks, and what the UI could promise.

The team chose explicit export types rather than pretending one implementation satisfied all interpretations. They wrote acceptance examples: an export begun just before a document was removed, an export interrupted after half the files were processed, a user losing access during generation, and a customer downloading an archive a month later. Some questions needed legal and product decisions, not creative code.

Sana said this was why she disliked requirements that arrived as a single screenshot of a button. A button was the visible end of a contract spanning several systems and teams. Gabe agreed, then added that engineers should resist solving uncertainty by inventing complexity. If an archive needed only a simple snapshot, it didn't require a general-purpose workflow engine with a dozen configurable policies.

The revised feature brief included one owner for the end-to-end outcome and named contributors for each boundary. It also stated what they would not build yet. Scope management was not bureaucracy; it was deciding which promises the team could safely make within the release window.

## Thursday — The permission everyone assumed was inherited

A pilot customer tested the new export and reported that a reviewer could download evidence from a project they could no longer access. The export had been created while the reviewer was authorized, but its download link remained valid after their permissions were revoked.

Sana initially looked at frontend routing. The download button was hidden for unauthorized users. Evie opened the same URL directly and reproduced the problem. Hiding a button was not access control. The backend had issued a long-lived object-storage URL that could be reused without asking the current application whether the requester still had permission.

The team defined an explicit authorization policy for export creation, job processing, and result download. In their selected model, downloads went through an authorization check and issued short-lived scoped access. A retained archive might contain private evidence whose visibility changed after creation. The system needed a clear policy for whether such an archive remained available and to whom.

Tomas reviewed the worker's cloud permissions too. It could read entire object-storage buckets, even though it needed only a specific set of tenant-scoped files for each export. They restricted its role and validated the source object identifiers against the authorized request. Least privilege reduced the damage that a bug or compromised worker could cause.

A colleague suggested letting the worker trust tenant IDs supplied in a queue message. Oliver said the message had been produced by application code, but messages could be stale, malformed, or created before permissions changed. The worker needed to validate the durable export resource and its allowed scope. Internal infrastructure isn't inherently trustworthy merely because it doesn't have a public URL.

The security incident exposed a useful design principle: authorization decisions live at the boundary where a protected resource is accessed, not only in the screen where the user clicked a button.

## The assistant that wrote convincing tests

One developer used an AI coding tool to generate additional tests for the export worker. It produced thorough-looking cases for successful file assembly, invalid input, and expected error responses. The tests passed. Evie noticed they mocked the database and object store so completely that the worker never crossed the boundaries where its real bugs lived.

She kept the generated unit tests for useful pure logic but added integration tests around durable job transitions and final publication. The team injected failure after a database commit but before message acknowledgment, simulated a repeated worker attempt, and checked whether a partial archive could become visible. These weren't arbitrary puzzles. They modeled the failure windows that had caused customer-facing defects.

Oliver explained the difference between test coverage and confidence. A hundred percent of lines executed in unit tests did not mean a distributed workflow was reliable. Coverage could reveal untested code, but it couldn't prove that the assertions represented important business invariants. Good engineering judgment lay in deciding which behaviors mattered enough to defend with tests.

The AI tool was still valuable. It wrote repetitive fixtures, suggested edge cases, and accelerated mechanical refactors. The engineers supplied the threat model, the concurrency assumptions, the acceptance criteria, and the review of what the code actually guaranteed. Gabe summarized it as “let the assistant type quickly, but don't outsource the reasons we believe the system works.”

## Friday — The customer report and the engineering report

The first pilot export of a large account succeeded after twenty-seven minutes. The support team received the link and celebrated. Then the customer opened the archive. Several files had been repeated, and one expected attachment was missing.

The worker had retried a partial batch after a transient object-storage failure. Its output assembly process appended files without keeping a durable manifest of what had already been incorporated. The retry was correct according to the queue—unfinished work should be attempted again—but unsafe according to the archive's semantics.

Evie constructed an integration test using interrupted downloads, duplicate message delivery, and a job restart. Oliver changed the export worker to generate and persist a deterministic manifest of selected evidence and to make final publication conditional on completed validation. A temporary archive wasn't exposed as ready until the expected files and summary matched the manifest. A failed attempt could restart without silently duplicating content.

Meanwhile, Sana found that the progress UI jumped backward after reconnecting. Old status events arrived after new ones and overwrote current state. She made the client compare job versions and refetch authoritative status after reconnection. Showing progress is not the same as owning the truth about progress.

The retrospective exposed a coordination issue too. The feature had passed individual team reviews, but nobody had been responsible for the end-to-end business outcome. Backend thought an accepted job was enough. Frontend thought a success event was enough. QA thought the test environment was representative. Platform thought the archive permissions were a product decision. Product assumed every step was covered.

Gabe made the owner of a feature responsible for its cross-boundary acceptance criteria without making one person implement every component. He also insisted that ownership could not mean hiding failures from the rest of the team. When the system failed, people needed clear escalation paths and shared evidence.

## The postmortem that changed how the team worked

Gabe brought the export incident to a retrospective and asked each participant what evidence had been available at the time. The API dashboard showed green because requests returned `202 Accepted`. The worker dashboard showed moderate CPU but hadn't reported memory peaks. The storage service recorded successfully uploaded archive fragments. Customer support saw complaints that downloads were missing files. Each team had an accurate local observation and an incomplete overall picture.

Evie proposed measuring one business milestone across the whole journey: from a user creating an export request to a validated archive becoming available. The team added a correlation identifier that followed the request through the database, queue, worker, and object-storage publication. They also recorded where jobs waited, not only where code executed, because long queue delays had been invisible to the API timer.

Tomas added deployment identity to error and job metadata. A worker consuming a job might not be the same version as the API that created it. Without knowing the running version, a failure could look like a random data issue when it was actually a contract mismatch introduced during rollout. A release now had an evidence trail connecting source commit, artifact digest, deployed configuration, and runtime behavior.

The retrospective also addressed human communication. The previous organization had used incidents to search for the person who made the last commit. That habit encouraged defensive behavior and incomplete reports. Gabe wanted accountability for decisions and fixes without assuming one engineer caused a complex failure alone. They recorded where review, testing, ownership, and escalation mechanisms had failed, alongside the specific code defect.

A newer developer admitted that they had noticed inconsistent export behavior in staging but thought it wasn't worth escalating because nobody else seemed worried. Evie made clear that uncertainty about a critical workflow was exactly what needed to be raised. A team that suppresses awkward observations may produce impeccable status meetings and terrible production systems.


## The engineer who asked a basic question

In the middle of onboarding, a developer named Ana asked what an API gateway actually did in their architecture. She had worked with backend code before but never configured a gateway herself. A few people began explaining routes, authentication, rate limits, TLS termination, and private network connectivity in a rush. Ana interrupted: “Which of those does ours actually do?”

Tomas opened the running configuration. Their gateway handled public routing and certain request limits. Authentication happened mostly in the application. TLS terminated before traffic reached some internal services, but not all paths shared the same arrangement. The old architecture diagram had attributed more responsibility to the gateway than the deployment really gave it.

Gabe liked the question because it made a fuzzy concept concrete. Knowing that a tool can perform ten tasks is different from knowing which task it performs in a given system. The team began recording ownership at each boundary and using that map during incident reviews. It reduced the tendency to blame “the infrastructure” whenever a request failed somewhere before a controller.

Ana later described the onboarding session as more helpful than memorizing a catalogue of cloud products. She could now follow one request from browser to backend to database, ask who owned each decision, and identify what evidence would show a failure. The map wasn't complete, but it was useful enough for real engineering conversations.


## The first month — Less ceremony, more truth

Over the next month, NorthstarOps retired unused workers, documented the real deployment topology, and made the CI pipeline both faster and more trustworthy. They added correlation identifiers from browser request to export job and object-storage operations. Monitoring now showed how long customers waited for completed exports, not just how quickly the HTTP API responded.

Gabe resisted a proposal to rewrite everything in a new framework. The team had discovered several genuine architectural faults—unclear data ownership, unsafe retry behavior, mutable release artifacts, weak authorization at download, and insufficient observability. None required replacing Node.js or React. The highest-value work was to define the contracts and correct the boundary failures.

Sana explained to a new hire why their folder structure mattered less than their dependency rules. A beautifully named `services` directory could still contain a network of circular imports and uncontrolled database access. A modular design made it clear which component could change which facts, how other components learned about them, and which behavior must stay correct when a dependency failed.

Evie documented a new test strategy: ordinary unit tests for pure domain rules, integration tests for database and queue boundaries, contract tests for APIs and event schemas, focused end-to-end tests for critical business flows, and release verification against actual deployed artifacts. No single test layer would prove everything. Combined, they made important classes of regression harder to miss.

One Friday, a pilot customer wrote: “The export took longer than the old one, but this time it was complete, and I knew what it was doing.”

Gabe read the message aloud at the team meeting. Nobody suggested adding the quote to an investor slide. It was more useful than that. It described an improvement in what the product promised and what the system could reliably deliver.

The team had inherited a Friday of mysterious deployments and undocumented expectations. By the next month, they had not built a glamorous new architecture. They had built something more valuable: a shared understanding of what was actually running, what every layer promised, and how to know when those promises were kept.

*The spoken story ends here.*

## Behind the story — optional screen reference

**Connections:** SE215-L01/L02/L03/L04/L06/L07/L11 (roles, delivery, Git, repo, platform, QA, release); SE310-L01/L02 (API contracts and auth); SE320-L01/L03 (backend lifecycle and queues); CS320-L04 (memory constraints); CS330-L02/L03 (query, snapshot); CS430-L01/L05 (partial failure and idempotency); SE240-L03 (client state); SE340-L02/L04 (containers, CI/CD); SE440-L01/L03 (observability and testing); SE330-L01/L03 (architecture and evolution).

**Technical caveats:** Export consistency semantics are a product requirement, not a universal database default. Immutable container digests make artifact identity clearer but don't replace deployment checks. Idempotent job scheduling and idempotent output publication are separate concerns. Access to an archive may require renewed authorization even after job creation.

**Optional reflections:** Which artifact proves what version is actually deployed? What should an HTTP response promise for a long-running export? Who owns the correctness of a workflow crossing four engineering teams?
