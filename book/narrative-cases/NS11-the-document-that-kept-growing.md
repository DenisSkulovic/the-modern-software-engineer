# NS11 — The Document That Kept Growing

*Focus: MongoDB data modeling, querying, indexing, and production judgment. A discovery-through-work story, not a database certification lecture.*

All people, companies, figures, and events are fictional. Technical situations are deliberately realistic, with illustrative sizes and timings.

## The first month — A beautifully simple document

At Northline Fleet, the product was simple to explain and difficult to operate. Small logistics companies installed GPS devices in delivery vans. Dispatchers opened a map, selected a vehicle, and saw its last position, route history, engine alerts, and maintenance notes. The sales demonstration lasted four minutes. The engineering system behind it had been growing for four years.

When Nadia joined as a full-stack developer, the lead engineer, Tomas, showed her a MongoDB document on a call. It had the vehicle identification number, current location, driver assignment, a list of maintenance notes, and an array of recent GPS positions. At first glance it was delightful. One API call could deliver almost everything the vehicle details page required. No complicated joins. The entire thing looked remarkably like the JSON that the React frontend expected.

“Why did you pick MongoDB?” Nadia asked.

“Because the unit we usually read is a vehicle,” Tomas answered. “The document gives us a convenient unit to retrieve and update. That was a good reason. Then we got carried away.”

The original developers had taken a real advantage of a document database and turned it into an article of faith. When a customer added a maintenance note, it went into an array inside the vehicle document. When an engine sensor reported a warning, it went into another array. GPS devices sent positions every few seconds, and those went into the history array. For an early customer with twelve vehicles, this was wonderfully convenient. For a company with thousands of vans operating around the clock, the document became something closer to a personal diary written by a hyperactive robot.

Nadia asked whether a document was simply a database row with curly braces. Tomas shook his head. MongoDB stored BSON documents, which could hold nested structures and arrays and had data types beyond ordinary JSON. The practical distinction was not punctuation. It was the **boundary of a thing**. If several fields were usually read together, changed together, and had a bounded life together, putting them in one document might be sensible. If one component grew without limit, had its own lifecycle, or was independently queried millions of times, embedding it indefinitely could become a liability.

The word *bounded* stuck with her. A vehicle had one registration number and maybe six current maintenance reminders. It did not have a bounded number of GPS observations. Its position history was a stream, potentially hundreds of thousands of records per vehicle, and the company retained years of it. That alone was reason to reconsider the shape.

“MongoDB doesn't force you to store an entire family tree in one document,” Tomas said. “It gives you the option. Options have costs.”

## The second month — An update that was too large to be innocent

The first customer incident arrived in a spreadsheet, not an alert. Dispatchers in Rotterdam said the details page for older vehicles sometimes took several seconds to load. Newly registered vehicles were fast. Nadia suspected the map component. It displayed a complex route and perhaps drew too many markers. She disabled the map. The page still took too long.

She looked at the network waterfall. The API request spent most of its time waiting for a response. The response itself was enormous, full of coordinates the screen did not currently need. The page wanted the most recent position and ten maintenance notes. The server returned the vehicle's accumulated history, including a mountain of data nobody would look at until opening a separate archive view.

The team could have tried faster serialization or a larger application server. Instead, they asked a simpler question: why was this request reading the history at all?

They planned to keep a compact vehicle document for relatively stable identity and latest operational state, while storing position observations in a separate collection. Each observation had a vehicle identifier and timestamp, perhaps additional sensor fields. The vehicle page could retrieve a small document. The route-history page could query a time range. Deleting old telemetry no longer meant rewriting a giant vehicle record.

That did not mean every array was wrong. The current set of tire-pressure readings was bounded and naturally belonged with vehicle state. A handful of favorite routes might also be fine. The point was not “always reference, never embed.” It was that ownership, growth, and access patterns should determine the boundary.

A new engineer, Pavel, asked whether MongoDB had joins. He had heard people say that document databases couldn't do them. Nadia explained that an aggregation pipeline could use a lookup stage to combine records across collections. But a lookup wasn't free simply because a database supported it. If retrieving a simple page required performing a large join for every row, they might have made the data model inconvenient for their actual workload.

They wrote down three questions on the meeting room glass: What does the user read? What changes together? What grows independently? It was the beginning of a useful design conversation, and not a single MongoDB slogan survived it intact.

## Tuesday, 11:40 — The fastest twenty results in a five-million-document room

Separating telemetry improved the details page, but the dispatch dashboard had its own problem. Managers wanted to filter all fleet alerts for one customer, sort by most severe and most recent, and view twenty at a time. The first page loaded quickly. Deep pages were painfully slow.

The API did exactly what its name promised: filter, sort, skip thousands of matches, and return twenty. “But we only return twenty,” Pavel said, staring at the monitoring graph. “Why does the database have to work so hard?”

Nadia remembered a lecture from the previous week. Returning twenty things and *finding* the right twenty things were different tasks. If a restaurant asks a chef for the twentieth most popular dish, the chef may have to rank a great many dishes before delivering that single plate. A small result does not imply a small amount of work.

They used an explain plan. Instead of asking only how long the query took, they asked how many documents and index keys it examined. Those numbers were far larger than the returned count. In some cases a blocking sort had to consider a huge candidate set. In others a skip-based page required moving past many matching records before reaching the requested twenty.

An index, Tomas explained, was another organization of the data. Imagine a library with its books arranged on one shelf by arrival date and a separate catalogue arranged by subject and author. A librarian can answer some questions quickly using the catalogue. But the catalogue does not make every possible question cheap. If the query filters customer, severity, and time, then sorts the survivors, the order of fields in an index matters. A useful compound index needs to match the shapes of important queries, not merely contain all the words that appear in them.

The team had an index on vehicle identifier and timestamp, excellent for route history. It was almost irrelevant to a cross-vehicle alert dashboard sorted by severity. Another index included the customer identifier but could not efficiently satisfy the requested ordering. MongoDB was not failing to recognize an obvious truth; it was choosing among the physical paths they had made available.

They designed a compound index for the dominant alert query, tested it against real-looking distributions, and inspected the execution plan rather than trusting a green check mark. They also discussed using seek-based pagination for large browsing sequences. Instead of saying “skip the first hundred thousand,” the client could carry a stable cursor based on the last sort position, with a tie-breaker to avoid ambiguous ordering. This would not allow an arbitrary jump to page 5,000 as naturally, but it matched how dispatchers actually browsed an incident feed.

The team did not remove jump-to-page support blindly. Product explained that auditors sometimes jumped directly to an old month. A date-range filter could serve that need better than a page number based on an unstable ordering of a growing dataset. An engineering optimization became a conversation about what the user actually wanted.

## Wednesday — The aggregation that multiplied reality

A different report counted alerts by manufacturer. The developer who built it had joined vehicles to alerts, unwound arrays, grouped results, and sorted again. It worked correctly for a pilot tenant. For a large tenant, memory use surged and the query became expensive.

Nadia opened the aggregation stages one by one. Each stage operated on the documents flowing out of the previous one. A match could reduce the number of candidates. A lookup could bring in related data. An unwind could turn one document containing many array elements into many pipeline documents. A group could reduce rows again, but only after the earlier work had happened. A sort could require retaining a substantial working set, depending on the plan and available optimizations.

“Think of it as a factory line,” Nadia told Pavel. “If you copy a thousand boxes into a million boxes at station three, station four doesn't get to pretend there were only a thousand.”

They realized that the alert collection already stored a manufacturer identifier derived from the authoritative vehicle record at alert creation time. The report did not need to perform that join for every request if the business question was “manufacturer at the moment of the alert.” In fact, dynamically looking up the vehicle's current manufacturer could produce historically misleading results after corrections or vehicle transfers.

They kept a historical snapshot on the alert and documented what it meant. This was deliberate duplication, not casual inconsistency. A historical fact should not change simply because today's source record was edited. Another report, asking for the current manufacturer of active vehicles, still needed to use current vehicle data. The difference was semantic, not purely technical.

Once that distinction was clear, the aggregation could match the tenant and time window early, group the relevant alerts, and avoid the massive repeated lookup. The query became faster partly because it did less work, and partly because the data model now matched the actual question.

Tomas laughed when Pavel suggested adding six more indexes just in case. Indexes occupied storage, consumed memory, and made writes more expensive because the database had to maintain additional structures. The right response to every slow query was not to keep building indexes until the storage bill requested a management meeting.

## Thursday — The count that disappeared

Nadia was pleased with the performance improvements until a customer reported a more disturbing symptom. Two dispatchers acknowledged the same alert almost simultaneously. The dashboard displayed the acknowledgment count as one, although both had clicked.

The application had implemented a classic read, modify, write sequence. It read the document with count zero. One request calculated one and wrote it. The other also calculated one and wrote it. Two users, one visible increment.

“Isn't MongoDB atomic?” Pavel asked.

“A single-document write is atomic,” Nadia answered. “That doesn't make a sequence of separate reads and writes one atomic decision.”

For a counter, they could use an atomic increment rather than calculating a new value in application memory. For an acknowledgment that should happen only once per user, the business rule was more specific. A conditional update or a separately keyed acknowledgment record could enforce the invariant. If two workers race, one must not quietly create a second copy of the same fact. For more complicated operations spanning multiple documents, MongoDB offered transactions, but the team should understand their scope and cost before making every operation a multi-document transaction.

They also noticed that a client timeout could make the result uncertain. The server might have successfully acknowledged the alert even though the response never reached the browser. Retrying a request should therefore have an appropriate operation identity or conditional logic. “Atomic” and “idempotent” were different properties. One answered whether a write was indivisible. The other answered whether repeating the logical operation would create an unwanted second effect.

The fix was small. The conversation mattered more than the patch, because the same mistake appeared in inventory reservations, usage counters, and job status changes throughout the system.

## Friday — The replica that remembered yesterday

Northline's product was growing internationally. To reduce load on the primary database, the team routed some reporting reads to a secondary replica. The change looked good in load testing. Then an operations manager modified a vehicle assignment and immediately reloaded the page. The old driver appeared again for a brief interval.

This was not necessarily a lost write. A replica could lag behind the primary, especially if replication was asynchronous. The manager had updated the authoritative copy, then read a delayed copy. In other words, the system had made a choice about *how fresh* the next read needed to be, without explaining that choice to the person using it.

Nadia resisted the suggestion to “make all replicas strongly consistent.” That sentence hid several different trade-offs. Some reports tolerated a few seconds of lag. An assignment screen did not. The team could route correctness-sensitive reads to the primary, use session-aware consistency features where appropriate, or make the interface display a pending transition while confirming the new state. Whatever they chose had to match both the database's guarantees and the user's expectations.

Pavel asked whether they should shard next. Tomas answered with the least fashionable architectural recommendation of the quarter: not yet. Sharding was about distributing data and load across partitions; replication was about maintaining additional copies of the same logical data. They solved different problems. Sharding would also create new decisions about shard keys, query routing, hot customers, migrations, and scatter-gather queries. If most expensive queries didn't restrict by the shard key, they might simply spread an expensive operation across more machines.

The team had not even exhausted the simpler improvements: better schema boundaries, better queries, retention rules, measurement, and work distribution. Adding a distributed architecture before understanding the workload would be like hiring three warehouse managers when the problem was that every package was labeled “miscellaneous.”

## The next Monday — The index that helped everyone except the busiest customer

The new compound index made the alert feed fast in staging. In production, most tenants improved immediately, but the largest account still had long, erratic response times. Its data occupied a disproportionate share of the collection, and its dispatchers filtered on “active” far more often than everyone else.

The team had done something subtle during testing. They used a representative number of documents but not a representative distribution. Their synthetic dataset gave every customer roughly the same number of alerts. In reality, most customers had a few thousand and one giant customer had several million. An index can be effective for a selective query and less helpful when a filter matches most of the data. The planner weighs alternatives using its statistics and estimates. Those estimates are useful, but they are not magic prophecies about every tenant and every combination of conditions.

Nadia put the explain output from two customers side by side. The small customer's query examined a few dozen index entries. The large customer's query examined many thousands. Both returned twenty records. She refused to call one good and the other bad until they defined which filtering and sorting the product actually required.

The operations manager wanted “active critical alerts, newest first.” Their current route allowed selecting a broad history window, grouped by vehicle, then sorting by severity. The implementation had accumulated features with different query shapes. One index could not satisfy them all equally. They considered a narrower index for the dominant operational view and an alternative path for historical analysis. A partial index might help if the query reliably included its predicate, but it was not guaranteed to help arbitrary filters. Another option was to maintain a compact current-alert view and keep historical alerts in the larger collection.

Tomas insisted they write down the costs. A new index took space. On every inserted alert, the database maintained the relevant index entries. Building it on a busy collection required planning and monitoring. Some queries were inherently expensive because the product asked to rank huge sets. If the team hid that cost by giving a different endpoint name, it would remain expensive.

Their final solution was deliberately mixed. A highly used “live incidents” screen got a stable, well-indexed query with a small time horizon and a clear sort. Historical investigations got time-range navigation and asynchronous export for enormous result sets. Their support team documented the distinction so users were not surprised when an audit export worked differently from scrolling a live feed.

They had not discovered the one perfect MongoDB index. They had discovered that performance belongs to a *workload*, not to a database in the abstract.

## Two weeks later — The migration has two calendars

The schema split had been tested in development. The new vehicle document looked lean; position observations had moved into their own collection. Nadia proposed deploying it on Thursday. Tomas asked one irritating question: “What happens to old application instances still running when the new ones start writing the new shape?”

A fleet of application pods rarely changes version at one instant. A rolling deployment leaves old and new versions alive together. Background workers may be even slower to upgrade. They had also accumulated a few internal scripts that still expected `vehicle.positions` to exist. A one-shot migration followed immediately by removing that field could break a version nobody remembered was still running.

They designed a transition rather than a midnight flip. First, readers learned to understand both old and new structures. Then writers began using the new representation while preserving compatibility during the migration window. A backfill moved historical observations in bounded batches, checkpointing progress so it could restart without blindly duplicating records. The copied observations needed stable identifiers or a deduplication rule; otherwise a backfill retried after a crash could turn one GPS point into two. They compared counts by vehicle and date, sampled individual timelines, and tracked discrepancies before deleting any original data.

The migration exposed another distinction. An API returning success did not mean all derived data had caught up. Some reports read the new collection, while a support tool still read the embedded array. During overlap, one could seem ahead of the other. They considered a short dual-write period, but duplicating writes itself introduced failure modes: one write might succeed while the other failed. Rather than pretending those two writes were an indivisible unit, they built explicit validation and reconciliation into the transition plan.

“Isn't this too much ceremony for moving an array?” Pavel asked.

“It's a small code change,” Nadia replied. “It's a change to the meaning and location of millions of facts. Different category.”

The team removed the old field only after readers, workers, and backfills had reached the new shape and after a monitored safety window. Rollback was no longer just “deploy yesterday's image.” Once new records existed only in the new collection, old code needed compatibility to read them. They documented the earliest version to which rollback remained safe.

The migration had taught Nadia something no schema diagram could convey: a data model exists not only in space, across collections, but in *time*, across deployed versions, background jobs, and recovery procedures.


## The maintenance window — An index is also a write decision

The new alert index still had to be built on a large live collection. During planning, product asked why a query-performance improvement needed a maintenance discussion at all. Tomas explained that an index is a real structure the database has to construct and then maintain. Creating one consumes resources, and the sustained cost of keeping it up to date affects writes. Index changes on large collections should be tested and monitored against the real deployment's capabilities and traffic.

The team examined which queries would benefit, checked the collection's size and write rate, and staged the rollout rather than adding several speculative indexes at once. They also measured performance after the change, under both normal load and a synthetic burst. The new index improved the operational feed, but the alert-ingest service showed a modest increase in write work. That did not make the index a mistake; it made the trade-off visible.

Nadia noticed one query remained slow despite reporting that an index was used. It examined many index entries and then fetched many documents to evaluate a condition not well supported by the index. “Uses index” was not the same thing as “uses index efficiently.” They compared keys examined, documents examined, returned results, and observed latency. The team could now argue about evidence rather than using the word *indexed* as an incantation.

When the write-rate alert returned to normal, they closed the change ticket with two links: a before-and-after measurement and the plan for removing an obsolete overlapping index later. Infrastructure choices were no longer judged solely by whether the original ticket had turned green.


## Six months later — The smallest model that answered the right question

By autumn, the fleet platform was not dramatically different from the outside. Dispatchers still opened a map, selected a van, and investigated alerts. But the data had a more coherent structure. Vehicle documents held bounded, current state. Telemetry had an independent, time-oriented lifecycle. Alert records retained historical facts intentionally. The most important queries had indexes shaped to their access patterns. The team measured actual work performed, not just returned rows or happy-path latency.

They were not finished. A few expensive analytics workloads still belonged somewhere other than the transactional database. They had to decide how long to retain raw GPS points. They had to test a collection migration without breaking old application versions. Every improvement created another decision about ownership and guarantees.

At the end of a planning meeting, Nadia found the original document screenshot from her onboarding. The great nested monster, vehicle identity at the top and thousands upon thousands of observations below it. It looked so elegant when it contained ten coordinates.

She told Tomas she finally understood why he hadn't answered her first MongoDB question with a brand comparison.

“What did I say?” he asked.

“You said the document was the unit we read.”

“And?”

“We forgot to ask whether everything inside it had the same reason to exist.”

She had come expecting to learn MongoDB as a list of commands. Instead she'd learned a more transferable idea: a database is a machine for answering particular questions under particular correctness and cost constraints. The technology matters. The structure of the questions matters more.

*The spoken story ends here.*

## Behind the story — optional screen reference

**Shelf:** Focused · **Primary discipline:** Data systems / MongoDB · **Starting knowledge:** Basic understanding of APIs and data storage is enough.

**Relevant courses and lectures:** CS340-L01 (database selection), CS340-L02 (storage costs), CS340-L03 (document boundaries and atomic updates), CS340-L04 (query plans, aggregation, indexes, pagination), CS340-L05 (replication/sharding), CS340-L07 (data architecture), CS330-L02 (query-performance thinking), SE320-L01 (service boundaries).

**Important nuances:** Single-document atomicity does not make arbitrary read–modify–write sequences atomic. Historical snapshots are correct only when their time semantics are deliberate. The performance of specific compound indexes depends on filters, sort, distributions, and execution plans; no universal field-order recipe applies. Real deployments should benchmark proposed queries and index costs.

**Optional reflection:** What is the difference between returning twenty results and examining twenty records? Which facts should change when a vehicle is updated, and which should remain historical? When would sharding be justified rather than premature?
