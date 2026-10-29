---
id: CS345-L04
course: CS345
title: "The MongoDB Performance Incident Studio"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: CS345-L03
next: null
---

# CS345 — MongoDB Production Query Engineering
## Lecture 04: The MongoDB Performance Incident Studio

*The query is correct. The index exists. The API returns twenty documents. Production is still slow. Your interviewer opens the profiler and asks: "What would you investigate first?"*

---

# Part I — Intuition

## 1. The Incident Nobody Could Explain

Imagine joining a product engineering team responsible for a multi-tenant SaaS application.

The application maintains customer records and historical activity events. Its administrative interface allows account managers to rank customers by revenue, filter them by activity, and browse historical events.

Three incidents have accumulated in the engineering backlog.

The first concerns pagination.

Page one loads quickly. Page five thousand can take eighteen seconds.

The second concerns customer history.

An endpoint returning a customer's completed-event count becomes progressively slower as the customer's history grows.

The third concerns an administrative dashboard.

An endpoint returns twenty customers and an exact total count. Both values are correct, but MongoDB spends an alarming amount of time producing them.

A developer suggests increasing the Atlas cluster tier.

Another suggests caching the responses.

Someone else proposes adding indexes to every filter field.

Those are possible interventions.

But the team hasn't yet established what work the database performs or why it performs that work.

You are asked to investigate.

This studio tests whether you can turn vague performance complaints into specific, evidence-backed diagnoses.

## 2. Every Query Has an Invisible Workload

A frontend developer observes a response containing twenty customers.

A backend developer observes an aggregation pipeline.

MongoDB observes a sequence of data-access and processing operations.

Those perspectives are not equivalent.

A pipeline can return twenty customers after scanning thousands of index entries, examining hundreds of thousands of event documents, calculating aggregates, sorting thousands of intermediate results, and discarding almost everything.

The response payload measures what leaves the system.

It doesn't measure what happens inside it.

### Visual anchor 1 — The visible result and hidden work

```text
                    MongoDB

5,000 customers
       |
       v
Join historical events
       |
       v
Process 200,000 events
       |
       v
Calculate customer summaries
       |
       v
Sort thousands of customers
       |
       v
Skip previous pages
       |
       v
Return 20 customers
       |
       v
                  Small API response
```

A strong engineer investigates the internal operations before optimizing the final response.

## 3. A Performance Fix Must Preserve Meaning

Consider a pipeline that ranks customers by completed-event revenue.

It joins activity events, calculates revenue totals, sorts customers, and returns the first twenty.

You notice that the lookup is expensive.

A colleague proposes moving `$limit: 20` before the lookup.

The query becomes dramatically faster.

But the result is now wrong.

The database selects twenty customers before calculating their revenue.

It returns the highest-revenue customers among those twenty, not the highest-revenue customers in the tenant.

The performance improvement is real.

The business operation has changed.

That is not a successful optimization.

**Correctness is a constraint on performance engineering, not something to reconsider after the benchmark looks good.**

## 4. Query Performance Is More Than Execution Time

Suppose one query takes 80 milliseconds and another takes 110 milliseconds.

The second query uses fewer index keys and fetches fewer documents.

Which query is better?

We don't yet know.

The timing difference could reflect caching, measurement overhead, plan selection, or unrelated system activity.

We need representative measurements.

We also need to consider how often the query runs and what resources it consumes.

A slightly slower query that avoids scanning enormous amounts of data may scale more predictably.

But a theoretically elegant plan might still lose under the actual workload.

MongoDB's `explain("executionStats")` gives us useful evidence about the operations performed.

It is not a universal latency benchmark.

Explain ignores existing plan-cache entries and can differ from ordinary steady-state execution.

### Visual anchor 2 — Three forms of evidence

```text
Query correctness
    |
    | Same business result?
    v
Execution evidence
    |
    | Keys, documents, stages, spills?
    v
Production impact
    |
    | Latency, CPU, memory, I/O, writes?
    v
Defensible optimization
```

We need all three perspectives.

## 5. The First Trap: Fixing Reads and Hurting Writes

Imagine that the application needs to sort customers by completed revenue.

Computing revenue from historical events is expensive.

So we store `completedRevenue` on each customer document and index it.

Now the ranking query is fast.

But every completed event must update the corresponding customer summary.

And because the revenue field is indexed, those changes also require index maintenance.

If the application writes many events per second, the write-side cost can become significant.

An unusually active customer can turn their summary document into a contention point.

We have exchanged one cost for another.

This trade may be worthwhile.

But it must be measured.

A senior engineer does not stop after demonstrating that the read became faster.

They ask what work moved elsewhere.

## 6. The Second Trap: A Correct Index Can Still Support an Expensive Operation

Suppose we have the perfect compound index for the administrative ranking.

It begins with tenant ID, followed by completed revenue descending, and customer ID ascending.

That index supports the tenant filter and the required ordering.

Page one is efficient.

But page five thousand still uses a large offset.

MongoDB must account for the preceding ordered results.

The index avoids sorting.

It doesn't make skipping free.

Cursor pagination can improve sequential navigation by seeking relative to a known previous result.

But it also changes the product contract.

A cursor-based interface doesn't naturally support arbitrary jumps to page five thousand.

And changing ranking values can move customers across cursor boundaries between requests.

The problem is not merely index design.

It involves product behavior, data freshness, and navigation semantics.

## 7. The Third Trap: One Query Doesn't Mean One Cheap Operation

The administrative dashboard needs the current page and an exact total count.

A developer combines them through `$facet`.

One network request replaces two.

That sounds efficient.

But the count branch still needs to establish how many records qualify.

If qualification depends on revenue computed from historical events, the count may require the same expensive upstream computation.

A small response containing one page and one count doesn't prove the database performed little work.

Sometimes separate operations are more efficient.

Sometimes the exact total can be cached.

Sometimes the UI doesn't need an exact total at all.

The engineering decision begins with understanding the actual requirement.

### Visual anchor 3 — The count is work too

```text
Historical activity
        |
        v
Compute customer summaries
        |
        v
Filter qualifying customers
        |
        v
      $facet
       /   \
      /     \
     v       v
 Sort/page  Count all
     \       /
      \     /
       v   v
    One response
```

The single response hides two different computations.

## 8. What Makes This a Senior-Level Exercise?

The syntax isn't particularly exotic.

The difficult part is deciding what evidence matters.

You must distinguish data-access cost from aggregation cost.

You must distinguish query-plan improvements from changes in business meaning.

You must understand that the query planner can transform some aggregation stages automatically.

You must recognize when an index is useful but insufficient.

And you must assess the operational cost of a proposed materialized read model.

A capable engineer should be able to say:

"The existing index is appropriate for this access pattern, but the endpoint's deep-offset contract remains expensive. Here's the evidence, here's the alternative, and here's what changes for users."

That explanation is far more valuable than automatically adding another index.

### A tiny comprehension check

A pipeline returns twenty customers after calculating revenue for four thousand candidates.

Would a final `$limit: 20` prove that only twenty customers were processed?

No.

Would a stored and indexed revenue field reduce the need to calculate historical revenue during every ranking request?

Potentially, yes.

Would that remove the need to maintain the stored value when source events change?

Absolutely not.

That's the judgment this capstone is designed to test.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 9. The Studio Contract

This is a diagnostic studio, not another MongoDB reference chapter.

There are four incidents.

Each begins with a symptom and a deliberately problematic implementation.

Your first responsibility is to predict the behavior.

Then reproduce it, inspect execution evidence, and formulate a causal explanation.

Only after that should you implement a correction.

The sequence is:

**Hypothesis → Evidence → Mechanism → Change → Verification → Defense.**

For each incident, produce a short report.

The report should identify the business requirement, what MongoDB actually did, why it was expensive, which correction you selected, and what costs or failure modes remain.

Do not allow Cursor or another AI tool to diagnose the problem before your independent attempt.

AI can review the result afterward.

## 10. Incident A — MONGO-01: The Deep Page

The administrative customer ranking uses a pipeline with `$lookup`, computed revenue, `$sort`, `$skip`, and `$limit`.

Page one works.

Deep pages become increasingly expensive.

The superficial explanation is that pagination is slow.

The more precise investigation separates two mechanisms.

First, the revenue value is computed from historical events before the ranking can be established.

Second, a deep offset requires discarding a substantial portion of the ordered result.

Those mechanisms are related but distinct.

### 10.1 What evidence matters?

We need the full aggregation pipeline, representative tenant, page size, page offset, and execution statistics.

We need to know how many customers qualify.

We need to understand the historical-event work.

We need to inspect whether the sort can use an index or must operate on calculated values.

We also need to determine whether MongoDB has optimized `$sort`, `$skip`, and `$limit` into a bounded top-K operation.

MongoDB can combine a compatible sort and limit, increasing K by the skipped amount.

That reduces sorting-state requirements.

It does not necessarily reduce the upstream revenue calculation.

### 10.2 What is a valid correction?

Possible corrections include changing the pagination model, materializing revenue, or reducing the cost of the historical aggregation.

Each addresses a different component of the problem.

A valid correction must preserve the required ranking.

Limiting customers before calculating revenue is generally invalid.

If product requirements demand arbitrary page-number jumps, cursor pagination alone may be insufficient.

That trade-off belongs in your final recommendation.

## 11. Incident B — MONGO-02: The Growing History

A customer details endpoint returns a name, completed-event count, and completed revenue.

Its response remains compact.

But the customer accumulates more historical events.

The endpoint becomes slower.

This is a relationship-cardinality problem.

### 11.1 Locate versus process

A suitable foreign index lets MongoDB locate events belonging to the customer efficiently.

But if the calculation requires examining twenty thousand historical events, an index doesn't make those events disappear.

The executor still needs to process the relevant facts.

We need to determine whether the endpoint retrieves full event documents unnecessarily or can aggregate them inside the foreign lookup.

### 11.2 The optimizer complicates the story

MongoDB can coalesce certain `$lookup`, `$unwind`, and following `$match` stages.

Therefore, the pipeline text doesn't necessarily describe literal physical materialization.

A developer who sees a large lookup array in the source pipeline shouldn't immediately claim that the entire array is materialized before filtering.

Inspect the optimized execution plan.

The objective is identifying work MongoDB actually performs, not criticizing source-stage order for aesthetic reasons.

### 11.3 Historical data can require a different API

A customer profile may need a compact summary.

A history screen may need paginated events.

An audit export may need all events.

Trying to serve all three through one unbounded lookup is often a modeling mistake.

Separate access patterns can provide better performance and clearer contracts.

## 12. Incident C — The Exact-Count Trap

A dashboard requests one page of customers and the exact number of customers matching a derived-revenue threshold.

The pipeline uses `$facet`.

One branch sorts and returns the page.

Another counts all matching customers.

The count branch can be expensive because it requires knowing which customers satisfy the derived condition.

### 12.1 When the facet is useful

A facet can share upstream processing between multiple branches.

That may be efficient when the shared work is appropriate.

But it doesn't eliminate the cost of producing its input.

Nor does one network request automatically mean lower server work.

### 12.2 The limits matter

MongoDB's `$facet` stage has a 100 MB output-document limit that `allowDiskUse` cannot bypass.

The final BSON document is also subject to the 16 MiB document limit.

A facet returning an enormous array can fail even when other aggregation stages are allowed to spill.

### 12.3 Product constraints can be optimized

Does the UI need an exact count after every filter change?

Could it display whether another page exists?

Could the count be cached or computed less frequently?

Would a stored and indexed derived value make the count cheaper?

These are product and architecture questions, not just MongoDB syntax questions.

## 13. Incident D — The Index That Moved the Bottleneck

The team materializes completed revenue onto customer documents.

A compound index supports tenant filtering and revenue ordering.

The ranking becomes fast.

Then write latency increases.

The application updates customer totals frequently, and the indexed field changes with those updates.

### 13.1 Read and write costs must be measured separately

A compound index consumes storage.

It also requires maintenance when indexed values change.

A design with several overlapping indexes can amplify that work.

The correct comparison includes read latency, index storage, write throughput, update latency, and relevant contention.

### 13.2 The correctness problem is even more important

Materialized revenue can drift from authoritative event history.

A source event may be corrected without updating the summary.

A consumer may process the same event twice.

A backfill may overwrite a newer value.

A recovery process may repeat a non-idempotent increment.

A query can be extremely fast while returning stale or incorrect data.

The presence of a valid index doesn't establish business correctness.

### 13.3 Accepting the trade-off deliberately

Materialization may still be the right design.

But it requires an explicit consistency policy, safe update mechanism, reconciliation, and monitoring.

A senior-level answer must explain those obligations.

## 14. Why Several Common Fixes Are Wrong

Let's examine the interventions most likely to appear during the studio.

### "Add an index"

An index may help selective lookup or indexed ordering.

It cannot directly index a revenue total that only exists after a historical aggregation.

It doesn't eliminate deep-offset traversal.

And unnecessary indexes increase write costs.

### "Move `$limit` earlier"

This is only valid when it preserves the required result.

For global revenue rankings, limiting candidates before calculating revenue usually changes the answer.

### "Enable `allowDiskUse`"

Eligible aggregation stages can spill to temporary disk storage.

That may prevent some memory-limit errors.

It does not reduce the amount of historical work.

It also doesn't override `$facet` output limits.

### "Cache the endpoint"

Caching can reduce repeated work.

But the cache needs a correct key, invalidation policy, and freshness contract.

A cached incorrect ranking remains incorrect.

### "Store the score"

This can dramatically improve reads.

But the score must stay synchronized with source facts.

The design also moves work into the write path.

### "Upgrade the cluster"

More capacity may be necessary for legitimate load.

But it shouldn't be the first response to a query that performs unnecessary scans, joins, or sorts.

The most useful question is whether the system is performing unavoidable work efficiently.

## 15. How to Build a Defensible Performance Report

A useful report is concise but causal.

Begin with the business operation.

Explain what the endpoint must return.

State the observed failure.

Then describe the execution evidence.

For example:

"The endpoint returns twenty customers, but the aggregation calculates historical revenue for thousands of customer candidates before sorting. The deep page additionally requires a large skip. The observed workload is dominated by historical aggregation and pagination rather than response serialization."

Then describe the proposed change and what it addresses.

Perhaps the team stores maintained revenue and switches to cursor navigation.

Finally, describe what remains unresolved.

A materialized total requires safe maintenance.

Cursor navigation may not support arbitrary jumps.

Changing ranking values can affect pagination consistency.

This is what makes the recommendation credible.

## 16. The Course-Level Competence Test

CS345 has developed four related skills.

L01 taught how to read MongoDB execution evidence and understand index access.

L02 taught how aggregation pipelines transform cardinality and accumulate work.

L03 taught when expensive derived calculations might be materialized and how that creates consistency obligations.

L04 asks you to combine those skills.

The purpose isn't to recognize the exact same query you saw in a lecture.

It is to investigate unfamiliar code without relying on memorized fixes.

If you can establish the required result, trace the data processing, identify wasted work, propose a safe correction, and defend its cost, you're approaching practical MongoDB production fluency.

---

# The Oral Examination

Answer each question aloud before reading the solutions.

### Question 1 — Correct Result, Bad Performance

A MongoDB endpoint returns the correct twenty customers but takes several seconds.

What would you inspect before recommending a new index?

### Question 2 — The Index Exists

The query uses an index on `customerId`, yet the lookup becomes slower as a customer's event history grows.

Explain why both observations can be true.

### Question 3 — Deep Offset

An index supports the required sort.

The query uses `skip(100000).limit(20)`.

Why can it still be expensive?

### Question 4 — Early Limit

A global ranking is calculated from historical events.

Why might applying `$limit: 20` before the lookup produce incorrect results?

### Question 5 — Exact Count

A facet returns twenty results and an exact count.

Why can its upstream work remain expensive?

### Question 6 — Explain and the Plan Cache

Why shouldn't one `executionTimeMillis` value from `explain()` be treated as the endpoint's authoritative production latency?

### Question 7 — Materialized Revenue

A materialized customer revenue field makes the ranking query fast.

What new correctness and operational responsibilities appear?

### Question 8 — The Index Budget

A team proposes five compound indexes to support different combinations of administrative filters.

What evidence should determine whether those indexes are justified?

### Question 9 — The Failed Optimization

A rewrite reduces the query's execution time by ninety percent but changes which customers appear in the ranking.

How do you evaluate the change?

### Question 10 — Interview Judgment

You've never used a particular MongoDB query setting in production.

The interviewer asks whether it would solve the incident.

What is a credible response?

---

# Solutions and Discussion

### Solution 1

Capture the complete query shape and representative parameters.

Inspect `explain("executionStats")`, including examined keys and documents, index bounds, lookup behavior, sorting, cardinality, and pagination.

Identify the actual source of unnecessary work.

### Solution 2

The index improves how efficiently the database locates events.

It doesn't eliminate processing the relevant events.

A growing history can increase legitimate aggregation work even with an excellent index.

### Solution 3

MongoDB still needs to account for the preceding ordered results.

The index avoids a separate sort but doesn't make the offset free.

Cursor pagination can help with sequential navigation.

### Solution 4

The early limit selects a subset before calculating the global ranking.

The query may then return the best customers from that subset rather than the best across the entire tenant.

### Solution 5

The count requires knowing how many records qualify.

If qualification depends on expensive historical computation, the count branch still depends on that work.

A compact response doesn't imply a cheap aggregation.

### Solution 6

Explain ignores existing plan-cache entries and involves its own planning behavior.

Its timing also doesn't include all application-level costs.

Use it to understand physical work, then verify representative normal-request measurements.

### Solution 7

The system must maintain derived values through inserts, corrections, reversals, retries, and backfills.

It needs idempotency or suitable transactional coordination, reconciliation, observability, and a clear consistency policy.

### Solution 8

Evaluate real query frequency, selectivity, measured plans, index overlap, storage, write costs, and maintenance burden.

The objective is supporting important access patterns, not indexing every possible combination.

### Solution 9

Reject it as a correct replacement.

Performance is only meaningful under preserved business semantics.

The rewrite may be useful after correcting the semantic error.

### Solution 10

Acknowledge the uncertainty, identify the mechanism the setting affects, consult the relevant documentation, and test it under representative conditions.

Do not invent confidence about an unfamiliar feature.

---

# The Mental Model Worth Keeping

A production MongoDB query has three separate contracts.

**The result contract:** Which business facts must be returned?

**The execution contract:** What work does MongoDB perform to produce them?

**The maintenance contract:** What additional costs or correctness responsibilities does an optimization introduce?

A strong diagnosis addresses all three.

The objective is not merely to make a query faster.

It is to make the required business operation correct, efficient, and sustainable.

---

# Course Completion — From Query Plans to Production Diagnosis

This completes the four manuscripts of CS345 — MongoDB Production Query Engineering.

The course has established a progressive mental model:

First, understand how MongoDB finds documents.

Second, understand how aggregation pipelines process and multiply data.

Third, decide when to replace repeated computation with maintained derived representations.

Finally, demonstrate that you can diagnose unfamiliar performance incidents and defend corrections.

The manuscripts provide the educational foundation.

The studio provides an opportunity to demonstrate independent competence.

**Writing or listening to the course is not equivalent to mastering it.**

A meaningful completion requires investigating the runnable cases, interpreting actual execution evidence, and explaining the trade-offs without receiving the diagnosis in advance.

*The spoken lecture ends here. The remaining material is a practical incident studio. Attempt the cases before reading the answer key.*

---

# Optional Practical Lab — The MongoDB Performance Incident Studio

## Studio Rules

This capstone uses four incidents.

Each must produce:

1. A prediction.
2. Reproduction evidence.
3. A causal diagnosis.
4. A focused correction.
5. Correctness verification.
6. Performance comparison.
7. A short architectural defense.

Do not let AI write the diagnosis before your first attempt.

Cursor may help prepare files, execute scripts, or review the finished work.

The answer key is deliberately separated from the case packets.

## Environment

Use a disposable MongoDB 8.0 container.

If the container from CS345-L01 exists but is stopped:

```bash
docker start cs345-mongo
```

Otherwise create it:

```bash
docker run --name cs345-mongo \
  -p 27028:27017 \
  -d mongo:8.0
```

Connect with:

```bash
docker exec -it cs345-mongo mongosh cs345
```

### Fixture requirements

The lab builds on CS345-L02:

- `pipeline_customers`: 5,000 documents.
- `pipeline_events`: 200,000 documents.
- Mercury: 4,000 customers.
- Customer 733: 20,036 events.

If these collections don't exist, run the seed script from CS345-L02 first.

The studio creates separate collections, so previous exercises remain intact.

## Setup — Create Independent Studio Collections

The following commands discard and recreate only collections whose names start with `studio_`.

Do not run them against an unrelated database.

```javascript
const lab = db.getSiblingDB("cs345");

const sourceCustomers = lab.pipeline_customers;
const sourceEvents = lab.pipeline_events;

assert.eq(
  sourceCustomers.countDocuments({}),
  5000,
  "Run the CS345-L02 customer fixture first."
);

assert.eq(
  sourceEvents.countDocuments({}),
  200000,
  "Run the CS345-L02 event fixture first."
);

lab.studio_customers.drop();
lab.studio_events.drop();

sourceCustomers.aggregate([
  {
    $project: {
      _id: 1,
      tenantId: 1,
      name: 1,
      tier: 1,
      createdAt: 1
    }
  },
  { $out: "studio_customers" }
]).toArray();

sourceEvents.aggregate([
  {
    $project: {
      _id: 1,
      customerId: 1,
      tenantId: 1,
      status: 1,
      amountEur: 1,
      occurredAt: 1,
      payload: 1
    }
  },
  { $out: "studio_events" }
]).toArray();

const customers = lab.studio_customers;
const events = lab.studio_events;

events.createIndex(
  { customerId: 1, status: 1 },
  { name: "customer_status" }
);

printjson({
  customers: customers.countDocuments({}),
  events: events.countDocuments({}),
  mercury: customers.countDocuments({
    tenantId: "mercury"
  })
});
```

Expected counts: 5,000 customers, 200,000 events, 4,000 Mercury customers.

The copied data reflects the state of the previous laboratory. If earlier exercises deliberately modified an event, the copied data includes that change. Our studio comparisons use the current authoritative events rather than assuming fixed revenue totals.

---

# Incident A — MONGO-01: The Deep Page

## Business requirement

Return Mercury's customers ranked by completed-event revenue.

The result must include customers whose completed revenue is zero.

The user requests twenty records per page.

The system currently supports arbitrary page-number jumps.

## Starting symptom

The endpoint becomes increasingly slow on deep pages.

Page one is acceptable.

Page 151 is much slower.

The response still contains twenty customers.

## Broken implementation

The pipeline joins complete event histories, expands the joined events, groups by customer, calculates completed revenue, sorts the calculated totals, and applies offset pagination.

```javascript
const rankingPrefix = [
  {
    $match: {
      tenantId: "mercury"
    }
  },
  {
    $lookup: {
      from: "studio_events",
      localField: "_id",
      foreignField: "customerId",
      as: "history"
    }
  },
  {
    $unwind: {
      path: "$history",
      preserveNullAndEmptyArrays: true
    }
  },
  {
    $group: {
      _id: "$_id",
      name: { $first: "$name" },

      completedCount: {
        $sum: {
          $cond: [
            { $eq: ["$history.status", "completed"] },
            1,
            0
          ]
        }
      },

      completedRevenue: {
        $sum: {
          $cond: [
            { $eq: ["$history.status", "completed"] },
            "$history.amountEur",
            0
          ]
        }
      }
    }
  }
];

function rankingPage(skip) {
  return [
    ...rankingPrefix,
    {
      $sort: {
        completedRevenue: -1,
        _id: 1
      }
    },
    { $skip: skip },
    { $limit: 20 }
  ];
}
```

## Evidence A1 — Compare shallow and deep pages

Run both queries.

```javascript
const shallowPage = customers.aggregate(
  rankingPage(0),
  {
    allowDiskUse: true,
    maxTimeMS: 120000
  }
).toArray();

const deepPage = customers.aggregate(
  rankingPage(3000),
  {
    allowDiskUse: true,
    maxTimeMS: 120000
  }
).toArray();

printjson({
  shallowCount: shallowPage.length,
  deepCount: deepPage.length,
  deepIds: deepPage.map(row => row._id)
});
```

Both should return twenty customers.

Now inspect their execution plans.

```javascript
const shallowExplain = customers
  .explain("executionStats")
  .aggregate(rankingPage(0), {
    allowDiskUse: true,
    maxTimeMS: 120000
  });

const deepExplain = customers
  .explain("executionStats")
  .aggregate(rankingPage(3000), {
    allowDiskUse: true,
    maxTimeMS: 120000
  });

printjson(shallowExplain);
printjson(deepExplain);
```

## Evidence A2 — Trace the logical work

Answer before changing anything:

- How many customers qualify initially?
- How many historical events are potentially involved?
- Which stages establish the completed-revenue values?
- Can the customer collection's `_id` index provide the computed-revenue sort?
- Can MongoDB optimize the sort-plus-skip-plus-limit sequence?
- If so, how large is the effective top-K for the deep page?

## Evidence A3 — Propose competing corrections

Prepare two candidate designs.

**Candidate one:** Preserve dynamic calculation but change the pagination contract where possible.

**Candidate two:** Materialize completed revenue and support indexed ranking.

For each, state what cost it removes and which cost remains.

Do not implement a materialized field until you've written down its maintenance invariant.

## Acceptance criteria

Your result preserves the correct global ranking.

You can distinguish historical aggregation cost from deep-offset cost.

You understand why an early limit would change business semantics.

You explain whether arbitrary page jumps remain supported.

---

# Incident B — MONGO-02: The Growing History

## Business requirement

Return a customer profile containing:

- Customer ID.
- Customer name.
- Completed-event count.
- Completed-event revenue.

The endpoint does not need the full event history.

## Starting symptom

An ordinary customer's profile loads quickly.

Customer 733's profile is much slower.

The response format is identical.

## Evidence B1 — Compare the underlying history

```javascript
printjson({
  ordinary: events.countDocuments({
    customerId: 734
  }),
  unusual: events.countDocuments({
    customerId: 733
  })
});
```

In the seeded fixture, Customer 734 has thirty-six events, while Customer 733 has 20,036.

## Broken implementation

The endpoint retrieves the customer's complete event history and calculates the summary afterward.

```javascript
function customerProfile(customerId) {
  return [
    {
      $match: {
        _id: customerId
      }
    },
    {
      $lookup: {
        from: "studio_events",
        localField: "_id",
        foreignField: "customerId",
        as: "history"
      }
    },
    {
      $set: {
        completedEvents: {
          $filter: {
            input: "$history",
            as: "event",
            cond: {
              $eq: ["$$event.status", "completed"]
            }
          }
        }
      }
    },
    {
      $set: {
        completedCount: {
          $size: "$completedEvents"
        },
        completedRevenue: {
          $sum: "$completedEvents.amountEur"
        }
      }
    },
    {
      $project: {
        name: 1,
        completedCount: 1,
        completedRevenue: 1
      }
    }
  ];
}
```

## Evidence B2 — Explain both requests

```javascript
const ordinaryExplain = customers
  .explain("executionStats")
  .aggregate(customerProfile(734));

const unusualExplain = customers
  .explain("executionStats")
  .aggregate(customerProfile(733), {
    maxTimeMS: 120000
  });

printjson(ordinaryExplain);
printjson(unusualExplain);
```

Inspect foreign index usage and documents examined.

Look for available `$lookup` statistics, such as `indexesUsed`, `totalDocsExamined`, and `totalKeysExamined`.

## Evidence B3 — Ask what the endpoint actually needs

Does the endpoint need twenty thousand event objects?

Or does it need two aggregate values?

Create an alternative lookup that filters completed events and groups them inside the foreign pipeline.

Preserve customers with no completed events.

Compare the returned values and execution evidence.

## Acceptance criteria

Both implementations return the same customer summary.

You explain why a correctly indexed lookup can still become expensive for a customer with enormous history.

You can distinguish reducing transferred intermediate data from reducing the underlying events that must be processed.

---

# Incident C — The Exact-Count Trap

## Business requirement

The administrative page displays customers whose completed revenue is at least €1,000.

It returns twenty ranked customers and an exact total number of qualifying customers.

## Starting symptom

The page response is compact.

The aggregation remains expensive.

The developer argues that using one `$facet` is automatically better than running two queries.

## Broken implementation

The pipeline calculates every Mercury customer's revenue before applying the threshold and returning both page and count.

```javascript
const computedSummaries = [
  {
    $match: {
      tenantId: "mercury"
    }
  },
  {
    $lookup: {
      from: "studio_events",
      localField: "_id",
      foreignField: "customerId",
      pipeline: [
        {
          $match: {
            status: "completed"
          }
        },
        {
          $group: {
            _id: null,
            completedRevenue: {
              $sum: "$amountEur"
            },
            completedCount: {
              $sum: 1
            }
          }
        }
      ],
      as: "summary"
    }
  },
  {
    $set: {
      completedRevenue: {
        $ifNull: [
          {
            $arrayElemAt: [
              "$summary.completedRevenue",
              0
            ]
          },
          0
        ]
      },
      completedCount: {
        $ifNull: [
          {
            $arrayElemAt: [
              "$summary.completedCount",
              0
            ]
          },
          0
        ]
      }
    }
  },
  {
    $project: {
      name: 1,
      completedRevenue: 1,
      completedCount: 1
    }
  },
  {
    $match: {
      completedRevenue: { $gte: 1000 }
    }
  }
];

const facetedRanking = [
  ...computedSummaries,
  {
    $facet: {
      page: [
        {
          $sort: {
            completedRevenue: -1,
            _id: 1
          }
        },
        { $limit: 20 }
      ],
      count: [
        { $count: "total" }
      ]
    }
  }
];
```

## Evidence C1 — Execute

```javascript
const facetResult = customers.aggregate(
  facetedRanking,
  {
    allowDiskUse: true,
    maxTimeMS: 120000
  }
).toArray();

printjson({
  pageLength: facetResult[0].page.length,
  count: facetResult[0].count
});
```

## Evidence C2 — Inspect the plan

```javascript
const facetExplain = customers
  .explain("executionStats")
  .aggregate(facetedRanking, {
    allowDiskUse: true,
    maxTimeMS: 120000
  });

printjson(facetExplain);
```

## Investigation

Explain:

- Why the derived threshold can't be applied as an ordinary indexed filter on the original customer documents.
- Why the exact count requires determining which customers satisfy the threshold.
- Why the response size doesn't establish the amount of upstream work.
- Whether MongoDB can optimize the page branch's sort and limit.
- What the `$facet` memory and BSON-size limits imply.

## Required design decision

Compare three approaches:

**A:** Compute everything on demand.

**B:** Maintain completed revenue and index it.

**C:** Relax the requirement for a fresh exact count.

Your recommendation must include the product behavior and consistency trade-offs.

---

# Incident D — The Index That Helps Reads and Hurts Writes

## Business requirement

The administrative ranking is used frequently enough that the team considers materializing revenue on customer documents.

The stored value must equal the sum of completed event amounts.

## Part D1 — Build the materialized baseline

Initialize all customer summaries.

```javascript
customers.updateMany(
  {},
  {
    $set: {
      completedRevenue: 0,
      completedCount: 0
    }
  }
);
```

Recompute from the studio event collection.

```javascript
events.aggregate([
  {
    $match: {
      status: "completed"
    }
  },
  {
    $group: {
      _id: "$customerId",
      completedRevenue: {
        $sum: "$amountEur"
      },
      completedCount: {
        $sum: 1
      }
    }
  },
  {
    $merge: {
      into: "studio_customers",
      on: "_id",
      whenMatched: "merge",
      whenNotMatched: "discard"
    }
  }
], {
  allowDiskUse: true,
  maxTimeMS: 120000
}).toArray();
```

This is an offline laboratory rebuild. It does not establish a concurrency-safe production backfill.

Create the ranking index.

```javascript
customers.createIndex(
  {
    tenantId: 1,
    completedRevenue: -1,
    _id: 1
  },
  {
    name: "tenant_completed_revenue"
  }
);
```

## Evidence D1 — Read performance

Inspect the materialized ranking.

```javascript
const materializedExplain = customers
  .find({
    tenantId: "mercury"
  })
  .sort({
    completedRevenue: -1,
    _id: 1
  })
  .limit(20)
  .explain("executionStats");

printjson({
  returned:
    materializedExplain.executionStats.nReturned,
  keys:
    materializedExplain.executionStats.totalKeysExamined,
  docs:
    materializedExplain.executionStats.totalDocsExamined,
  executionMillis:
    materializedExplain.executionStats.executionTimeMillis
});
```

Compare the examined work with the original computed ranking.

## Part D2 — Compare write-side costs

Create two independent benchmark collections containing the same small customer summary documents.

The first will have only the `_id` index.

The second will have an additional revenue-ranking index.

```javascript
lab.studio_bench_plain.drop();
lab.studio_bench_indexed.drop();

const benchProjection = {
  $project: {
    _id: 1,
    tenantId: 1,
    completedRevenue: 1,
    completedCount: 1
  }
};

customers.aggregate([
  benchProjection,
  { $out: "studio_bench_plain" }
]).toArray();

customers.aggregate([
  benchProjection,
  { $out: "studio_bench_indexed" }
]).toArray();

const plain = lab.studio_bench_plain;
const indexed = lab.studio_bench_indexed;

indexed.createIndex(
  {
    tenantId: 1,
    completedRevenue: -1,
    _id: 1
  },
  {
    name: "revenue_ranking"
  }
);
```

Now benchmark equivalent updates.

```javascript
function measureUpdate(collection) {
  const started = Date.now();

  const result = collection.updateMany(
    { _id: { $lte: 4000 } },
    { $inc: { completedRevenue: 1 } }
  );

  return {
    milliseconds: Date.now() - started,
    matched: result.matchedCount,
    modified: result.modifiedCount
  };
}

printjson({
  plain: measureUpdate(plain),
  indexed: measureUpdate(indexed)
});
```

### Investigation

Inspect collection index inventories and storage sizes.

```javascript
printjson({
  plainIndexes: plain.getIndexes(),
  indexedIndexes: indexed.getIndexes(),

  plainIndexBytes:
    plain.stats().totalIndexSize,

  indexedIndexBytes:
    indexed.stats().totalIndexSize
});
```

Repeat the experiment on freshly initialized collections if you want more meaningful timing comparisons.

### Required explanation

The indexed collection maintains an additional index containing the changing revenue value.

What write-side work does that create?

Is one timing measurement enough to establish the magnitude of the overhead?

Would the result change with a much larger dataset or higher concurrency?

When would that cost be justified?

Do not claim a specific performance improvement or regression unless your measurements support it.

## Part D3 — Introduce a correctness failure

After materializing the customer totals, deliberately change an authoritative event without updating its customer summary.

Event 1 is completed in the original deterministic fixture. If it has already been modified in earlier experiments, reset the studio collections before this step.

```javascript
const eventBefore = events.findOne({
  _id: 1,
  status: "completed"
});

assert(
  eventBefore,
  "Expected completed Event 1; reset the studio fixture."
);

const customerId = eventBefore.customerId;

const storedBefore = customers.findOne({
  _id: customerId
});

const result = events.updateOne(
  {
    _id: eventBefore._id,
    status: "completed"
  },
  {
    $set: {
      status: "failed"
    }
  }
);

assert.eq(result.modifiedCount, 1);

printjson({
  eventBefore,
  storedBefore
});
```

Recalculate the authoritative revenue for the affected customer.

```javascript
const sourceTotals = events.aggregate([
  {
    $match: {
      customerId,
      status: "completed"
    }
  },
  {
    $group: {
      _id: "$customerId",
      completedRevenue: {
        $sum: "$amountEur"
      },
      completedCount: {
        $sum: 1
      }
    }
  }
]).toArray();

const authoritative = sourceTotals[0] ?? {
  completedRevenue: 0,
  completedCount: 0
};

const storedAfter = customers.findOne({
  _id: customerId
});

printjson({
  authoritative,
  stored: {
    completedRevenue:
      storedAfter.completedRevenue,
    completedCount:
      storedAfter.completedCount
  }
});
```

## Investigation

Why does the stored value disagree with history?

Does the ranking index detect the inconsistency?

Can MongoDB return an incorrectly ranked customer while using a perfectly efficient execution plan?

How would you repair the affected summary?

How would you prevent recurrence?

## Acceptance criteria

Your design addresses both read performance and write-side cost.

You can state the materialized-field invariant.

You recognize that an indexed value can be wrong even when the query plan is optimal.

Your proposed production design includes idempotency, reconciliation, and an explicit consistency policy.

---

# Integrated Interview Round

After completing the four incidents, select one without reviewing its answer key.

Use the Interview Lab's practical European product-company full-stack profile unless a real job description provides more specific requirements.

The interviewer should act as a technically demanding but collaborative senior engineer.

The format is:

**Opening:** Present the symptom and relevant code.

**Investigation:** Ask for hypotheses and evidence.

**Implementation:** Require a focused correction.

**Verification:** Challenge correctness and performance claims.

**Architecture:** Ask what the correction costs elsewhere.

**Debrief:** Assess the candidate's demonstrated reasoning.

The interviewer should not reveal the answer key or planned follow-up questions during a realistic session.

---

# Evaluation Rubric

Use the Interview Lab's zero-to-four scale.

| Competency | Strong performance |
|---|---|
| Query understanding | Identifies the exact required business result |
| Plan literacy | Interprets examined keys, documents, and stages correctly |
| Cardinality reasoning | Traces expansion, grouping, and blocking work |
| Diagnosis | Supports a causal explanation with evidence |
| Implementation | Produces a focused, correct change |
| Verification | Compares both results and measured work |
| Trade-off judgment | Considers indexes, writes, consistency, and product constraints |
| Communication | Explains the investigation clearly and handles uncertainty |

A strong candidate doesn't need to know every MongoDB internal detail from memory.

They do need to establish evidence, reason about the data, and distinguish a proven mechanism from a guess.

---

# STOP — End of Candidate-Facing Studio

**Do not read the following diagnostic notes until you've attempted at least one incident independently.**

The solution key is intended for review, not for constructing the initial diagnosis.

---

# Diagnostic Notes and Reference Solutions

## Incident A — Deep Pagination and Computed Sorting

The original ranking computes completed revenue from historical events.

This prevents the customer collection from providing the required ordering through a normal index on stored customer fields.

The aggregation must calculate revenue before determining the ranking.

A deep skip then requires accounting for many earlier ranked results.

MongoDB may coalesce `$sort`, `$skip`, and `$limit`, retaining a top-K of skip plus limit.

That reduces sorting-state requirements but doesn't eliminate upstream revenue calculation or offset cost.

A valid redesign may combine a materialized revenue field with an indexed ranking and cursor navigation.

However, arbitrary page-number jumps may require a different product contract or a separate navigation mechanism.

## Incident B — Growing History

The foreign index on customer ID can efficiently locate relevant events.

But an unusually active customer still has a large event history.

The endpoint doesn't need those full event documents.

A lookup subpipeline can calculate completed count and revenue before returning a compact summary to the outer customer pipeline.

This may reduce intermediate data volume.

It doesn't remove necessary historical-event processing.

For frequently requested summaries over unbounded history, a maintained read model may eventually be appropriate.

## Incident C — Exact Counts

The facet's count branch needs to determine how many customers satisfy the derived-revenue threshold.

That requires upstream revenue computation when the value isn't stored.

The compact response doesn't prove low database work.

If revenue is materialized and indexed, filtering, ranking, and counting can use a much cheaper data representation.

But exact counts still have consistency and performance requirements.

A product decision to relax exact-count freshness can also reduce work.

## Incident D — The Indexed Read Model

The materialized ranking avoids repeated historical aggregation during normal reads.

The compound index supports tenant filtering and revenue ordering.

But updates to the indexed revenue field require index maintenance.

The benchmark compares a collection with an additional index against one without it.

Exact timing differences vary by environment and should not be invented.

The deliberately modified event demonstrates a separate correctness failure.

The source history changed, but the customer summary did not.

The index faithfully orders the stale stored value.

A production solution needs coordinated updates or a reliable projection-maintenance workflow, plus reconciliation and monitoring.

## The Senior-Level Conclusion

The best correction depends on the business requirement and workload.

A database can be correct but inefficient.

An index can be present but insufficient.

A query can be fast but return incorrect results after a bad rewrite.

A materialized read model can be fast while its stored values drift from authoritative history.

The engineer's responsibility is to demonstrate correctness, identify the expensive mechanism, and evaluate the full cost of the proposed change.

---

# Further Reading

1. **MongoDB — Explain Results**  
   https://www.mongodb.com/docs/v8.0/reference/explain-results/

2. **MongoDB — Query Plans and Plan Cache**  
   https://www.mongodb.com/docs/v8.0/core/query-plans/

3. **MongoDB — Aggregation Pipeline Optimization**  
   https://www.mongodb.com/docs/v8.0/core/aggregation-pipeline-optimization/

4. **MongoDB — `$lookup`**  
   https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/lookup/

5. **MongoDB — `$facet`**  
   https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/facet/

6. **MongoDB — Aggregation Pipeline Limits**  
   https://www.mongodb.com/docs/v8.0/core/aggregation-pipeline-limits/

7. **MongoDB — cursor.skip()**  
   https://www.mongodb.com/docs/v8.0/reference/method/cursor.skip/

8. **MongoDB — Computed Pattern**  
   https://www.mongodb.com/docs/v8.0/data-modeling/design-patterns/handle-computed-values/

9. **MongoDB — Compound Indexes**  
   https://www.mongodb.com/docs/v8.0/core/indexes/index-types/index-compound/

10. **MongoDB — Transactions**  
    https://www.mongodb.com/docs/v8.0/core/transactions/

11. **MongoDB — `$merge`**  
    https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/merge/

12. **The Modern Software Engineer — Interview Lab Protocol**  
    `book/interview-lab/PROTOCOL.md`

Cross-reference CS345-L01 for query plans, CS345-L02 for aggregation cardinality, CS345-L03 for pagination and maintained derived data, and `production-cases/MONGO-01.md` and `MONGO-02.md` for the associated incident packets.

---

# Dense Cheatsheet — MongoDB Interview Glance Card

*Screen-only revision card. The fenced material can be skipped by voice readers.*

```text
CS345 — MONGODB PRODUCTION QUERY ENGINEERING
================================================

INVESTIGATION LOOP
------------------
1. Define business result.
2. Capture actual query/pipeline.
3. Identify parameters and dataset.
4. Inspect explain executionStats.
5. Measure cardinality and stage work.
6. Identify causal bottleneck.
7. Propose focused correction.
8. Verify identical results.
9. Measure normal workload.
10. Evaluate new write/consistency costs.

EXPLAIN
-------
db.collection
  .explain("executionStats")
  .aggregate(pipeline)

Explain ignores existing plan cache.
Explain timing != complete API latency.

CORE METRICS
------------
nReturned
totalKeysExamined
totalDocsExamined
executionTimeMillis

For lookup:
indexesUsed
collectionScans
foreign docs/keys examined

Stage paths vary with engine/version.

INDEXES
-------
IXSCAN != automatically efficient.
COLLSCAN != automatically wrong.

Compound indexes encode access patterns.

Equality, Sort, Range:
useful guideline, not universal law.

Indexes cost:
storage, builds, write maintenance.

AGGREGATION
-----------
$match:
  filter

$lookup:
  join foreign data

$unwind:
  expand arrays

$group:
  aggregate input

$sort:
  order, potentially blocking

$skip:
  discard preceding rows

$limit:
  cap output

$facet:
  parallel result branches

PIPELINE OPTIMIZER
------------------
Can reorder certain matches.
Can coalesce lookup/unwind/match.
Can optimize sort/skip/limit.

Inspect optimized execution,
not merely source stage order.

TOP-K
-----
Sort + skip + limit:

K = skip + limit

Deep offsets increase K.
Upstream computation may remain.

DEEP PAGINATION
---------------
skip(100000).limit(20)
can traverse enormous preceding range.

Cursor pagination:
seek relative to previous sort tuple.

Requires stable tie-breaker.
Does not guarantee frozen dataset.

GROWING LOOKUP
--------------
Foreign index helps locate events.

But an indexed lookup can still process
enormous histories.

Use lookup subpipeline or maintained
summary when justified.

FACET
-----
Exact count is not free.

$facet output:
100 MB stage-specific limit.

Final BSON:
16 MiB document limit.

allowDiskUse doesn't bypass facet limit.

MATERIALIZED REVENUE
--------------------
Read:
  fast indexed ranking.

Write:
  update summary and index.

Correctness invariant:
stored completedRevenue =
sum of authoritative completed events.

FAILURE MODES
-------------
Missed event update
Duplicate processing
Status correction
Amount correction
Backfill overwrite
Projection lag
Hot summary document
Index write amplification

CORRECTIONS
-----------
Transactions where appropriate.
Expected-state guards.
Idempotent processing.
Durable progress.
Reconciliation.
Versioned rebuilds.
Lag monitoring.

RED FLAGS
---------
"Twenty results means cheap query."
"Index exists, so no problem."
"Put limit earlier."
"One facet means cheap count."
"Explain time equals API time."
"Store the score, problem solved."
"More indexes always help."
"Fast query proves correct data."
"Allow disk use fixes bad cardinality."
"Upgrade the cluster first."

SENIOR ENGINEER'S QUESTIONS
---------------------------
What is authoritative?
What is derived?
What work is necessary?
What work is avoidable?
What happens to writes?
What happens under retries?
What happens during backfills?
What does the product actually need?
How will the fix be measured?
How will correctness be maintained?

CS345 COMPLETION
----------------
L01 — Query plans and indexes
L02 — Aggregation under pressure
L03 — Pagination and materialization
L04 — Integrated performance incidents

FINAL MODEL
-----------
Correct result.
Measured execution.
Sustainable maintenance.

All three must hold.
```
