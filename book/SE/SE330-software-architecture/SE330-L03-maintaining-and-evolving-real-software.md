---
id: SE330-L03
course: SE330
title: "Maintaining and Evolving Real Software"
type: core
manuscript: manuscript
edition: "2.0.0"
legacy_ids: [ENG401-S11]
prev: SE330-L02
next: null
---




# SE330 — Software Architecture and Evolution

## Lecture 03: Maintaining and Evolving Real Software

*Why successful software becomes difficult to change, why rewrites are seductive, and how experienced engineers keep systems alive without rebuilding them every three years.*

---

## 1. The Successful Application Nobody Wants to Touch

Your company operates a subscription SaaS platform that has been growing steadily for six years.

The application began as a relatively simple Node.js backend with PostgreSQL, Redis, and a Vue frontend. Over time, it accumulated billing functionality, multiple payment providers, customer administration, reporting, background workers, and dozens of third-party integrations.

Today, the platform serves 80,000 customers and generates substantial recurring revenue.

By conventional measures, it's a success.

But something peculiar has happened to the engineering organization.

Six years ago, three developers could implement a substantial feature in two weeks. Today, fourteen developers struggle to deliver comparable functionality within six weeks.

The company has hired more engineers, introduced better testing, migrated to TypeScript, improved deployment automation, and added monitoring.

Yet development is becoming slower.

A seemingly modest change to subscription cancellation requires modifying:

- A 2,400-line `SubscriptionService`.
- Three database repositories.
- Two payment-provider adapters.
- Several BullMQ workers.
- A shared `BillingUtils` module.
- Twelve tests built around mocked implementation details.
- A legacy webhook handler that nobody fully understands.

The developers aren't incompetent.

They understand the technologies and genuinely care about maintainability.

The problem is that the application contains six years of accumulated decisions, compatibility obligations, shortcuts, obsolete assumptions, and business rules that have gradually become entangled.

Management proposes a solution.

**Rewrite the whole thing.**

A new architecture. Modern frameworks. Better module boundaries. Clean abstractions. Perhaps microservices.

The estimated delivery time is eight months.

One engineer enthusiastically describes the rewrite as an opportunity to "finally do everything properly."

Another suggests that the team should avoid touching the existing system because it is too dangerous.

Both positions contain something understandable.

Both can also be catastrophically wrong.

The fundamental challenge of maintaining mature software is not merely producing clean code. It's making economically defensible changes to a system that already has real users, real data, real obligations, and real revenue.

**Software maintenance is the engineering of change under accumulated constraints.**

---

## 2. Why Software Becomes Harder to Change

Physical machinery deteriorates through wear, corrosion, and mechanical fatigue.

Software doesn't age in quite the same way.

A function that executed correctly in 2020 doesn't spontaneously become incorrect in 2026 because its source code has become old.

Yet software systems undeniably become harder to maintain.

Why?

Because the environment around them changes, and the system accumulates relationships that were not part of its original design.

### The expanding surface of responsibility

Consider the first version of a subscription platform.

```text id="8eg84f"
Customer
   │
   ▼
Subscription
   │
   ▼
Payment Provider
```

The business rules are straightforward.

A subscription has a plan, a renewal date, and a payment method.

Now introduce six years of product development:

```text id="a9c16y"
Subscription
    │
    ├── Multiple pricing models
    ├── Promotional discounts
    ├── Corporate billing
    ├── Tax jurisdictions
    ├── Trial periods
    ├── Grace periods
    ├── Subscription pauses
    ├── Partial refunds
    ├── Legacy customers
    ├── Payment-provider differences
    └── Historical reporting rules
```

Each requirement may be legitimate.

But interactions between requirements can produce surprising complexity.

Suppose an annual customer pauses a subscription during a promotional period, then upgrades to a corporate plan before renewal.

Which price applies? Does the pause extend the billing period? Can the promotional discount carry over? What happens to the invoice already generated?

These are real business questions, not necessarily poor engineering.

A system's complexity can grow because the business itself becomes more complicated.

### Essential versus accidental complexity

This distinction is useful.

**Essential complexity** arises from the actual requirements of the problem.

**Accidental complexity** arises from the particular implementation, tools, structure, and historical decisions.

A payment platform must handle uncertain external transaction outcomes. That's essential distributed-systems complexity.

Having seven modules independently implement different interpretations of payment status is accidental complexity.

An international billing system may need complicated tax handling. That's essential domain complexity.

Representing tax rules through a thousand-line conditional statement scattered across several unrelated services is accidental complexity.

Architecture and refactoring can substantially reduce accidental complexity.

They cannot eliminate legitimate business complexity without changing the business itself.

This is why experienced engineers are suspicious of promises that a new framework will make a genuinely complex domain simple.

A framework may improve how complexity is managed.

It cannot repeal accounting rules.

---

## 3. Technical Debt: A Useful Metaphor That Became a Buzzword

Technical debt is one of the most frequently abused expressions in software development.

Developers sometimes use it to describe anything they dislike:

- Old code.
- Missing abstractions.
- Duplicate logic.
- Unfashionable frameworks.
- Incomplete documentation.
- A design they would have implemented differently.

But not every imperfection is technical debt.

The term, associated with Ward Cunningham, uses financial debt as a metaphor for design choices that create future costs.

A shortcut may reduce implementation time today while making later changes more expensive.

### Principal and interest

Imagine a team needs to support one additional payment provider.

A quick implementation adds provider-specific conditionals throughout existing services.

This saves two weeks compared with establishing a cleaner boundary.

However, every subsequent payment feature now requires modifying several provider-specific branches.

Conceptually:

\[
C_{\text{debt}}
=
C_{\text{future extra work}}
+
C_{\text{additional risk}}
\]

The initial saving is analogous to borrowing.

The continuing additional work is analogous to interest.

Eventually, restructuring the payment boundary may be worth the cost.

But there is an important distinction from financial debt.

Technical debt doesn't necessarily accumulate at a fixed rate.

If the affected code is never modified again, the shortcut may produce very little future cost.

If the code becomes the center of the company's product strategy, the same shortcut may become extraordinarily expensive.

### Intentional and unintentional debt

Some debt is deliberate.

For example:

> We need to deliver a temporary supplier integration before a contractual deadline. We'll implement it directly, accept limited duplication, and revisit the design if the integration becomes permanent.

That may be a reasonable business decision.

Other debt emerges unintentionally through misunderstanding, changing requirements, or poor engineering practices.

The important question is not whether the original developer made a morally correct choice.

It's whether the current cost of the design justifies changing it.

### Debt versus ordinary maintenance

A dependency requiring a routine security update isn't automatically architectural debt.

A complex pricing module isn't necessarily debt if its complexity directly reflects legitimate pricing rules.

A slow query isn't necessarily debt if it only recently became problematic after data volume increased.

The debt metaphor is most useful when it identifies **an avoidable structural cost that makes future work more expensive**.

Calling every maintenance task "technical debt" removes the term's explanatory value.

---

## 4. Engineering Economics: When Is Refactoring Worth It?

Suppose a problematic module requires an additional three developer-days whenever the team implements a related feature.

The team expects to modify it eight times during the next year.

The expected additional cost is approximately:

\[
3 \times 8 = 24
\]

developer-days.

A refactoring is estimated to require ten developer-days, plus testing and release risk.

At first glance, the refactoring looks worthwhile.

But several uncertainties matter.

Will those eight features actually happen? Will the refactoring eliminate most of the extra work? Will it introduce regressions? Could a smaller improvement capture most of the benefit?

A more realistic decision model is:

\[
V_{\text{change}}
=
C_{\text{avoided future work}}
+
C_{\text{avoided failures}}
-
C_{\text{implementation}}
-
C_{\text{migration risk}}
\]

This is a conceptual framework rather than an exact financial formula.

Its purpose is to connect technical improvements to expected business value.

### Change frequency matters

A messy module that changes every week deserves more attention than an equally messy module that hasn't changed in five years.

This suggests a useful heuristic:

\[
\text{Refactoring priority}
\propto
\text{Change frequency}
\times
\text{Cost of change}
\times
\text{Risk}
\]

The formula isn't meant to produce an exact score.

It helps explain why some ugly code is economically harmless while other seemingly modest design problems are extremely expensive.

### The hotspot principle

A **hotspot** is an area where structural complexity and frequent modification coincide.

Imagine two files:

```text id="n6wyu7"
legacyTaxFormatter.ts
    1,800 lines
    Changed twice in three years

subscriptionService.ts
    900 lines
    Changed 47 times in six months
```

The first file looks worse by size.

But the second may be the more urgent maintenance problem because developers continually interact with it.

Git history can reveal these change patterns.

For example:

```bash id="o2tr8g"
git log --since="6 months ago" \
  --name-only \
  --pretty=format:
```

A more sophisticated analysis can combine modification frequency with complexity, defects, and ownership.

The important idea is that maintainability investment should follow actual development friction.

Don't begin by refactoring whichever file offends your aesthetic sensibilities most.

---

## 5. Refactoring: Changing Structure Without Changing Behavior

Martin Fowler's definition of refactoring centers on changing the internal structure of software without changing its externally observable behavior.

That distinction matters.

Adding corporate billing is a feature.

Fixing a duplicate-payment bug changes behavior.

Extracting payment-provider-specific code behind a stable interface, while preserving existing behavior, is refactoring.

In practice, engineers often combine these activities, but separating them conceptually makes risk easier to manage.

### A realistic example

Imagine this service:

```typescript id="a9jomu"
class SubscriptionService {
  async renew(subscriptionId: string) {
    const subscription =
      await this.repository.findById(subscriptionId);

    if (subscription.status !== "ACTIVE") {
      throw new Error("Cannot renew");
    }

    if (subscription.paymentProvider === "STRIPE") {
      // 80 lines of Stripe logic
    } else if (subscription.paymentProvider === "SYSTEMPAY") {
      // 90 lines of Systempay logic
    }

    // Another 100 lines of billing logic

    // Notification behavior

    // Persistence
  }
}
```

The class mixes several responsibilities:

- Subscription eligibility.
- Provider-specific payment execution.
- Billing calculations.
- Workflow coordination.
- Persistence.
- Notifications.

A useful refactoring might isolate the provider-specific behavior:

```typescript id="drjci0"
interface PaymentProcessor {
  requestCharge(
    request: ChargeRequest
  ): Promise<ChargeResult>;
}
```

The subscription workflow can now depend on a meaningful payment capability rather than implementing every provider's protocol internally.

But the refactoring should preserve actual behavior, including provider-specific outcomes and failure handling.

An abstraction that pretends asynchronous settlement is identical to immediate capture may make the code look cleaner while introducing correctness defects.

### Refactor in small, verifiable increments

A safer sequence might be:

1. Establish focused tests around the current behavior.
2. Identify the logic belonging to payment-provider integrations.
3. Extract one provider adapter without changing the public workflow.
4. Run tests and compare production-relevant behavior.
5. Extract the next adapter.
6. Remove obsolete branches.
7. Introduce clearer business contracts where needed.

Each change should be comprehensible and independently verifiable.

This reduces the uncertainty introduced by large transformations.

### The danger of simultaneous redesign

Suppose a developer decides to:

- Replace TypeORM.
- Convert services to functional programming.
- Rename domain concepts.
- Introduce event-driven workflows.
- Reorganize the repository.
- Replace the dependency-injection framework.

All in one pull request.

Even if the final design is superior, diagnosing regressions becomes difficult because too many assumptions changed simultaneously.

Small changes aren't always possible, but **separating structural improvement from unrelated behavioral change reduces migration risk**.

---

## 6. Architectural Erosion: The Slow Destruction of Good Boundaries

In SE330-L01, we discussed how architecture influences the cost of change.

Now consider what happens to a well-designed architecture after years of development.

Originally:

```text id="pxve6c"
Reservations
    │
    ▼
Payments Public API
    │
    ▼
Payment Infrastructure
```

The reservation module requests payment operations through a defined application boundary.

Then a developer needs one additional field from the payment database.

Importing the payment repository directly is faster than extending the public interface.

```typescript id="jve7gq"
import { PaymentEntity }
  from "../payments/infrastructure/entities";
```

The change works.

A second developer copies the pattern.

Later, reporting code begins updating payment records directly.

Eventually, the payment module no longer controls its own state.

This is architectural erosion: the gradual weakening of intended structural boundaries.

### Why erosion is difficult to prevent socially

Every individual shortcut may save time.

The cost is distributed across future changes and other developers.

The person making the shortcut experiences the immediate benefit, while the organization absorbs the cumulative maintenance cost.

This creates an incentive problem.

Code review helps, but relying entirely on human attention is fragile.

### Architecture fitness functions

Important boundaries can sometimes be verified automatically.

For example:

```text id="xm033m"
Rule:
reservations/* must not import
payments/infrastructure/*
```

Tools such as dependency-cruiser, ESLint rules, or package-boundary enforcement can detect violations.

A CI job can reject changes introducing prohibited dependencies.

These rules are useful because they turn important architectural decisions into executable constraints.

However, automation can verify only what has been expressed.

A module may obey every import rule while still violating another module's business responsibilities through a poorly designed public API.

Architecture requires both structural controls and human judgment.

---

## 7. Legacy Systems: Old Doesn't Mean Bad

Developers frequently describe old applications as legacy systems.

But age alone tells us little.

A ten-year-old PostgreSQL-backed monolith may be reliable, understandable, and inexpensive to operate.

A six-month-old microservice platform may already be difficult to maintain because of excessive distributed coordination.

The real problem isn't age.

It's the difficulty of understanding, changing, testing, and operating the system safely.

### Why legacy systems survive

A mature system often contains substantial undocumented business knowledge.

Imagine a billing function:

```typescript id="43b1bq"
if (
  customer.country === "DE" &&
  subscription.createdAt < LEGACY_CUTOFF &&
  customer.billingType === "CORPORATE"
) {
  // Special calculation
}
```

The condition looks suspicious.

Perhaps it is unnecessary historical debris.

But perhaps it represents a contractual obligation affecting several thousand customers whose billing arrangements cannot simply be changed.

Removing it without understanding the reason may introduce serious financial errors.

Legacy code can encode years of discovered edge cases and operational lessons.

A rewrite that ignores those lessons may recreate old bugs that were eliminated long ago.

### Characterization tests

When code is poorly understood, **characterization tests** record its current observable behavior.

For example, a billing module may receive a collection of representative historical invoices and calculate their outputs.

Tests preserve those outputs as a reference while engineers investigate or restructure the implementation.

This doesn't mean the existing behavior is necessarily correct.

A characterization test documents what the system currently does, not what the business ideally wants.

That distinction is crucial.

A known defect should not become permanent merely because it was captured in a test.

### The archaeology approach

Before modifying a mysterious legacy module, investigate:

- Its callers.
- Its data dependencies.
- Its historical changes.
- Its tests.
- Relevant incident reports.
- Existing business contracts.
- Production behavior.

Git history can be surprisingly informative.

A strange conditional introduced after a payment incident may have an excellent reason to exist.

The goal is to understand which complexity is obsolete and which still protects important behavior.

---

## 8. The Rewrite Temptation

Let's return to our opening company.

Its engineers are frustrated with the existing application, and management proposes an eight-month rewrite.

The appeal is obvious.

A new project can eliminate old abstractions, reorganize modules, upgrade frameworks, and design the ideal architecture without the burden of historical compatibility.

At least, that's the dream.

### Why rewrites are frequently underestimated

The existing application has six years of accumulated behavior.

Some of that behavior is documented.

Much of it is embedded in code, database constraints, integrations, operational procedures, and customer expectations.

A rewrite must rediscover or reproduce those behaviors.

Meanwhile, the old application continues serving customers.

Business requirements don't stop changing during the rewrite.

The new team may therefore need to maintain two systems simultaneously:

```text id="w0z5p7"
Existing System
    ├── Production incidents
    ├── Customer support
    ├── New business features
    └── Compliance changes

New System
    ├── Reimplementation
    ├── Data migration
    ├── Integration testing
    └── Feature parity
```

This creates a moving target.

The new system approaches feature parity, but the existing system continues evolving.

Eventually, management becomes frustrated because the rewrite has consumed substantial engineering capacity without delivering visible business value.

This failure pattern is common enough to deserve serious skepticism.

### The hidden correctness problem

Suppose the original payment code contains a subtle rule handling a supplier's delayed settlement responses.

The rewrite team regards that code as unnecessary complexity and replaces it with a cleaner implementation.

The new application is simpler.

It is also wrong.

A rewrite can remove accidental complexity while accidentally removing essential business behavior.

### When a rewrite is justified

A rewrite may still be the best choice when:

- The existing technology can no longer satisfy critical requirements.
- The system's design fundamentally prevents necessary evolution.
- Incremental migration is substantially more expensive or risky.
- The required functionality is now much narrower than the original application.
- The organization can control scope and verify equivalence.
- The migration can be executed within realistic business constraints.

For example, replacing a discontinued internal reporting system with a much smaller modern service may be straightforward.

Rebuilding a complex financial platform from scratch while preserving every historical behavior is an entirely different proposition.

The engineering decision should reflect those differences.

**A rewrite is a migration strategy with unusually large scope, not a magical escape from complexity.**

---

## 9. The Strangler Fig Pattern: Replacing a System Incrementally

Instead of replacing the entire application at once, engineers can gradually redirect selected capabilities toward new implementations.

This approach is commonly called the **Strangler Fig pattern**, popularized by Martin Fowler.

Imagine an existing monolith:

```text id="xjxjhh"
          Client
            │
            ▼
      Legacy Monolith
       ├── Billing
       ├── Payments
       ├── Reservations
       └── Reporting
```

The company wants to modernize reporting.

Instead of rewriting every domain, it extracts reporting behind a stable interface or routing boundary.

```text id="oq4hwo"
               Client
                 │
                 ▼
          Routing Boundary
             /       \
            ▼         ▼
      Legacy App   New Reporting
         │            │
    Other Domains   Reports
```

Over time, selected functionality moves into the new system.

The old application gradually becomes smaller.

### Why incremental migration is safer

Each extracted capability can be deployed and evaluated separately.

The team receives feedback before committing to a larger transformation.

Business functionality continues operating during the migration.

Failures affect a smaller scope than a complete cutover.

This also creates opportunities to stop migrating when the remaining legacy system is sufficiently maintainable.

The objective isn't necessarily to eliminate every line of old code.

It's to improve the system's ability to serve the business.

### The difficult part: data ownership

Extracting an HTTP endpoint is relatively easy compared with extracting authoritative state.

Suppose both the old billing module and new billing service modify the same invoice tables.

Who owns invoice state?

If both systems independently update the same records, the migration may create conflicting business behavior.

A safer design establishes clear ownership and synchronization rules.

During a transition, the legacy system might call the new service through an adapter, or the new system might initially remain read-only while its data model is validated.

Avoid permanent dual-writing arrangements without a durable reconciliation strategy.

The strangler approach reduces migration scope, but it doesn't eliminate distributed consistency problems when data ownership crosses process boundaries.

---

## 10. Database Evolution: The Hard Part of Long-Lived Systems

Application code is relatively easy to replace.

Persistent data is harder.

A production database may contain millions of records created under historical assumptions.

Changing the schema therefore requires compatibility with both old data and potentially old application versions.

We explored expand-and-contract migrations in SE340-L04.

Now consider a more substantial domain change.

### Splitting one overloaded table

Originally, the SaaS stores billing information directly in `subscriptions`:

```text id="mpd8r2"
subscriptions
    id
    customer_id
    plan_id
    status
    invoice_number
    amount_due
    payment_status
    payment_provider
```

Over time, invoices and payments become separate business concepts.

The team wants:

```text id="cyn9e1"
subscriptions
    id
    customer_id
    plan_id
    status

invoices
    id
    subscription_id
    amount_due
    status

payments
    id
    invoice_id
    provider
    external_id
    status
```

This is conceptually cleaner.

But existing records and application code depend on the old layout.

### A staged migration

A defensible plan could include:

**Stage 1:** Create the new tables without removing old columns.

**Stage 2:** Introduce code capable of reading or translating both representations, with a carefully defined source of truth.

**Stage 3:** Backfill historical invoices and payments in bounded batches.

**Stage 4:** Validate that migrated records preserve required business invariants.

**Stage 5:** Change authoritative writes to the new model through a controlled cutover or reliable synchronization strategy.

**Stage 6:** Migrate readers and background workers.

**Stage 7:** Stop maintaining obsolete representations and eventually remove old columns.

The difficult decisions concern intermediate states.

If old and new schemas both receive writes, how are they kept consistent?

If an old worker processes a delayed job, can it overwrite newer state?

If migration stops halfway, can it resume safely?

These are engineering questions that must be answered before executing the migration.

### Prefer idempotent migration operations

A data migration should ideally be safe to retry.

For example, inserting converted invoices using stable derived identifiers or carefully defined uniqueness constraints can prevent duplicates during repeated execution.

A migration can record progress and validate results incrementally.

For large datasets, engineers should also consider transaction sizes, lock duration, replication lag, write amplification, and operational monitoring.

A logically correct SQL migration may still be operationally disastrous if it monopolizes database resources for hours.

---

## 11. Framework and Dependency Upgrades

Not every maintenance project changes the business domain.

Sometimes the system simply needs a newer Node.js version, framework, database driver, or third-party library.

These upgrades can appear routine until compatibility problems emerge.

### Why upgrades become expensive

Suppose the application hasn't upgraded its major framework dependencies for four years.

Over that period:

- APIs have been deprecated.
- Dependencies have changed module formats.
- Runtime requirements have advanced.
- Type definitions have evolved.
- Security patches have accumulated.
- Third-party integrations have adapted to newer versions.

The longer the delay, the larger the compatibility gap may become.

This doesn't mean every dependency should be upgraded immediately when a new version appears.

But indefinite postponement can transform many small manageable upgrades into one enormous migration.

### Separate risk categories

A dependency upgrade can affect:

**Compile-time compatibility:** TypeScript definitions or exported APIs change.

**Runtime behavior:** Existing code compiles but behaves differently.

**Operational compatibility:** Startup, networking, memory, or deployment behavior changes.

**Security:** Vulnerabilities are fixed or new risks introduced.

**Performance:** Resource usage or execution characteristics change.

**Ecosystem compatibility:** Other libraries may not support the new version.

A successful TypeScript compilation verifies only part of this picture.

### A practical upgrade approach

For a major Node.js runtime upgrade:

1. Identify supported runtime versions for critical dependencies.
2. Run the existing test suite under the target version.
3. Build and run the production container image.
4. Exercise real database and external integrations in a controlled environment.
5. Compare performance and memory behavior.
6. Deploy gradually with rollback compatibility.
7. Monitor production before retiring the previous runtime.

Where feasible, keep the application close enough to supported versions that upgrades remain incremental.

But don't blindly update every dependency simultaneously.

Separating changes improves the ability to identify regressions.

### Build versus buy

Maintenance also includes deciding whether functionality should remain custom-built.

Suppose the company maintains its own email delivery infrastructure.

A managed email provider might reduce operational complexity, but introduce recurring cost, vendor dependency, and migration effort.

Similarly, adopting a managed authentication provider may remove substantial security-maintenance work while introducing integration and pricing constraints.

Build-versus-buy decisions should consider total cost, required differentiation, operational responsibility, and the consequences of vendor dependence.

Owning code provides control.

It also makes you responsible for maintaining that code indefinitely.

---

## 12. Deprecation: Removing Old Behavior Without Breaking Customers

A mature API cannot always change freely.

External customers and integrations may depend on particular endpoints or response formats.

Suppose the platform currently exposes:

```http id="0q39pg"
GET /api/v1/subscriptions
```

The company introduces a new contract:

```http id="25l5ac"
GET /api/v2/subscriptions
```

Can the old endpoint disappear immediately?

Not if customers still depend on it.

### Deprecation as a managed process

A responsible deprecation strategy may include:

- Announcing the replacement contract.
- Providing documentation and migration guidance.
- Establishing a realistic support window.
- Measuring usage of the old API.
- Identifying important consumers.
- Supporting both versions during transition.
- Removing the old behavior only when the consequences are understood.

Internal consumers matter too.

A forgotten background worker may use an API endpoint that the main frontend abandoned months ago.

### Compatibility has a cost

Maintaining multiple versions creates complexity.

But removing compatibility too aggressively shifts that cost to customers.

Good product engineering weighs both sides.

The goal should be to make compatibility obligations explicit rather than allowing old behavior to remain forever because nobody knows whether it is still used.

Usage telemetry, contract inventories, and ownership records help make deprecation decisions defensible.

### The danger of permanent compatibility layers

An adapter introduced for a temporary migration may become permanent.

Then another migration introduces a second adapter.

Eventually, new functionality passes through several generations of compatibility machinery.

Temporary architecture needs an exit plan.

Otherwise, the mechanisms intended to simplify change become another source of long-term complexity.

---

## 13. Architecture Decision Records: Preserving the Reasoning

A strange design choice is much easier to understand when its original context is available.

Suppose the team discovers that cancellation events are never published directly from the HTTP request handler.

Instead, they are written to an outbox table.

A new engineer may wonder why the application uses this additional complexity.

An Architecture Decision Record, or ADR, can explain:

```text id="z52vf1"
ADR-018: Use transactional outbox for cancellation events

Context:
Reservation cancellation and event publication must not
become inconsistent when the message broker is unavailable.

Decision:
Write cancellation state and the outbox record in one
PostgreSQL transaction. Publish asynchronously.

Consequences:
Improved durability and reconciliation.
Additional dispatcher infrastructure and duplicate-delivery
handling remain necessary.

Status:
Accepted.
```

This is more useful than a document stating only:

"We use the outbox pattern."

The valuable information is why the decision was made and which trade-offs were accepted.

### ADRs aren't permanent laws

An architectural decision may become obsolete when requirements change.

For example, the original system may have used one global Redis instance because traffic and operational requirements were modest.

Years later, tenant isolation and workload growth might justify different infrastructure.

The ADR helps engineers understand the original reasoning, then consciously supersede the decision.

### Don't document every trivial choice

An ADR for every helper function would bury important decisions in bureaucracy.

Use ADRs for choices with significant consequences involving structure, data ownership, infrastructure, operational behavior, or long-term compatibility.

The goal is institutional memory, not ceremonial documentation.

---

## 14. Maintaining Software Is Also a Team Problem

Architecture influences the cost of change, but organizational behavior can accelerate or slow deterioration.

Imagine a company where every developer is rewarded primarily for the number of features delivered.

Refactoring receives little recognition.

Documentation is considered optional.

Incidents interrupt planned work, and nobody receives time to address their underlying causes.

Developers are encouraged to take shortcuts even when those shortcuts create future costs.

The resulting technical debt is not merely an individual coding failure.

It's an outcome of the organization's incentives.

### Sustainable engineering practices

Useful practices include:

- Reserving capacity for high-value maintenance work.
- Addressing structural problems when modifying affected code.
- Recording significant architectural decisions.
- Keeping dependencies reasonably current.
- Maintaining fast and trustworthy test feedback.
- Reviewing incidents for systemic improvements.
- Establishing clear module and service ownership.

However, avoid the opposite extreme.

A team that spends half its time polishing abstractions without delivering business value can also fail.

Software quality serves the product's long-term economics.

It isn't an independent competition for aesthetic perfection.

### The boy scout principle—with judgment

A common guideline says to leave code cleaner than you found it.

This is useful when interpreted proportionately.

If you're modifying a module and encounter a confusing variable name, an unnecessary conditional, or a small duplication directly related to your work, improving it may be sensible.

But a two-line bug fix in a critical payment workflow is not necessarily the right occasion to redesign the entire payment architecture.

The scope of cleanup should reflect risk, context, and the actual value of the improvement.

**Professional maintainability is disciplined stewardship, not compulsive refactoring.**

---

## 15. Practical Lab — Modernizing a Troubled SaaS

You're the new technical lead of a mature Node.js platform.

The application has operated for seven years and supports subscriptions, billing, customer administration, reporting, and multiple payment providers.

The team has identified these problems:

| Problem | Evidence |
|---|---|
| SubscriptionService is 2,400 lines | Modified in 31 of the last 40 releases |
| Legacy report generator uses an old library | Modified once in three years |
| Payment providers share conditional-heavy logic | Three recent production regressions |
| PostgreSQL schema contains obsolete fields | Most are no longer read |
| Node.js runtime needs a major upgrade | Current runtime approaching support end |
| Several modules import another module's ORM entities | Changes frequently affect unrelated features |
| Billing integration tests use extensive mocks | Database issues escaped into production |

Management is considering an eight-month rewrite.

You have six weeks of engineering capacity available for targeted improvement.

### Investigation A — Rank the problems

Don't rank them by how ugly the code looks.

Consider:

- Change frequency.
- Recent incident history.
- Security and support risk.
- Cost of future modification.
- Migration difficulty.
- Expected business impact.

The frequently modified subscription service and payment integration regressions are strong candidates for early attention.

The old report generator may be relatively low priority unless its dependencies create a security or compatibility risk.

### Investigation B — Propose an incremental roadmap

A reasonable roadmap might look like:

```text id="9akca6"
Weeks 1–2
    Establish characterization tests
    and real integration coverage for critical
    payment and subscription behavior.

Weeks 2–3
    Extract payment-provider integration boundaries.
    Reduce dangerous cross-module dependencies.

Weeks 3–4
    Upgrade runtime in a controlled environment.
    Resolve compatibility issues.

Weeks 4–6
    Refactor the highest-friction subscription
    workflows incrementally.
    Add architecture enforcement and documentation.
```

This is illustrative, not a guaranteed delivery schedule.

The actual sequence depends on release commitments, test quality, team capacity, and the urgency of unsupported dependencies.

### Investigation C — Evaluate the rewrite proposal

Prepare a brief argument for management.

Compare:

**Option A: Complete rewrite**

Potential benefits:

- Opportunity for substantial architectural redesign.
- Removal of obsolete infrastructure.
- Clearer implementation of known requirements.

Risks:

- Long period without incremental business value.
- Hidden functionality rediscovery.
- Data migration complexity.
- Parallel maintenance of old and new systems.
- Large cutover risk.

**Option B: Incremental modernization**

Potential benefits:

- Smaller changes and continuous feedback.
- Reduced operational migration risk.
- Ability to prioritize expensive hotspots.
- Continued feature delivery.

Risks:

- Temporary compatibility complexity.
- Slower elimination of some systemic problems.
- Need for disciplined architectural boundaries.

Which option has a better expected economic outcome?

Don't answer through slogans.

Use the actual condition of the system.

### Investigation D — Identify a measurable success condition

Suppose the current average time required to implement subscription changes is twelve developer-days.

An improvement programme aims to reduce that cost without increasing production incidents.

Useful evidence might include:

- Median lead time for comparable changes.
- Number of modules modified per feature.
- Change failure rate.
- Time spent diagnosing regressions.
- Test execution time and reliability.
- Frequency of production incidents involving payment logic.

Metrics require careful interpretation because features differ in complexity.

Nevertheless, observed delivery friction is more meaningful than declaring success because the code now follows a preferred folder structure.

---

## 16. Engineering and Interview Challenges

### Challenge 1 — The rewrite decision

A ten-year-old monolith generates most of a company's revenue. Its code is difficult to navigate, but production availability is excellent and the business continues shipping features.

Management wants to rewrite it as microservices.

What evidence would justify the rewrite? What would you recommend initially?

### Challenge 2 — The ugly but stable module

A 3,000-line reporting module uses outdated coding conventions.

It has not changed for four years, contains no known security vulnerabilities, and performs its job reliably.

Would you refactor it?

### Challenge 3 — The database migration

A SaaS wants to split billing information from a large `subscriptions` table into dedicated invoice and payment tables.

The system cannot tolerate extended downtime.

How would you migrate data and application behavior without creating conflicting sources of truth?

### Challenge 4 — The framework upgrade

A Node.js backend depends on a framework version that no longer receives security updates.

Upgrading requires substantial application changes, and the team is already busy with customer commitments.

How would you prioritize and execute the upgrade?

### Challenge 5 — The refactoring proposal

A developer proposes replacing 300 lines of duplicated logic with a generic abstraction involving dynamic configuration, plugin registration, and a complex dependency-injection hierarchy.

The abstraction reduces the source-code line count.

Is that sufficient evidence that the design improves maintainability?

---

## 17. Solutions and Discussion

### Challenge 1 — Rewrite only when the economics justify it

The existing application has meaningful strengths: proven behavior, stable operation, and established business functionality.

I'd first investigate the actual barriers to change.

Are business modules tightly coupled? Are particular components impossible to test? Does the deployment model prevent necessary scaling or team autonomy?

Then I'd identify targeted improvements that could be introduced incrementally.

A complete rewrite might eventually be justified if the existing structure fundamentally prevents essential requirements and smaller migrations cannot reasonably address the problem.

But moving to microservices is not itself a business objective.

For a revenue-generating monolith that continues functioning reliably, incremental modernization is the stronger default recommendation.

### Challenge 2 — Probably leave it alone

The module is large and aesthetically unpleasant, but apparently stable.

If it rarely changes and creates no meaningful risk, refactoring may produce little economic benefit.

I'd ensure its dependencies remain secure and supported, and that the team can recover or replace it if necessary.

Beyond that, I'd prioritize more active sources of maintenance cost.

A three-thousand-line file is not a moral emergency.

### Challenge 3 — Establish ownership and migrate in stages

I'd introduce the new tables while preserving existing behavior.

Next, I'd backfill historical data and establish a controlled transition strategy for writes, ensuring there is one clearly defined authoritative representation at each stage.

Readers can migrate incrementally through adapters or compatibility paths.

Consistency checks should compare the old and new representations before switching authoritative reads.

Only after all relevant consumers use the new model would I remove obsolete columns.

The most dangerous stage is when both representations can change independently. That requires explicit synchronization or a design that prevents competing writes.

### Challenge 4 — Treat unsupported dependencies as risk, not cosmetic maintenance

A framework that no longer receives security updates creates an increasing operational and security concern.

I'd investigate known vulnerabilities, external exposure, compatibility requirements, and the expected cost of upgrading.

Then I'd establish a controlled migration plan, possibly separating runtime upgrades from framework API changes.

Critical test coverage, production-like integration verification, and a gradual deployment strategy reduce risk.

The upgrade should receive appropriate priority based on exposure and consequences, even when business feature commitments compete for engineering capacity.

Deferring all maintenance indefinitely is itself a business decision—with accumulating consequences.

### Challenge 5 — Fewer lines do not imply lower complexity

The proposed abstraction may reduce duplication while introducing substantial indirection.

I'd examine whether the duplicated logic genuinely represents the same business responsibility and tends to change for the same reasons.

If so, a focused shared abstraction may be valuable.

But a generic plugin framework can make simple modifications harder by requiring developers to understand configuration, registration, and runtime dispatch before changing behavior.

The correct metric is the effort and risk of understanding and modifying the system, not the number of lines eliminated.

Some duplication is preferable to an incorrect abstraction.

---

## Mental Model

When maintaining a mature system, ask:

1. **Change pressure:** Which components are modified frequently?
2. **Cost:** Which structures make those modifications expensive?
3. **Risk:** Which problems threaten correctness, security, or availability?
4. **Business value:** What would improving the design actually save or enable?
5. **Migration strategy:** Can the improvement be introduced incrementally?
6. **Compatibility:** Which historical behaviors, consumers, and data must remain supported?
7. **Verification:** How will we establish that the change improved the system?

**The central principle: Good maintenance reduces the future cost and risk of change without spending more on architectural perfection than the business can justify.**


---

## End of SE330

**SE330 — Software Architecture and Evolution** is complete. See the recommended study order in `README.md` for natural next courses.

## Further Reading

1. **Martin Fowler — [Technical Debt Quadrant](https://martinfowler.com/bliki/TechnicalDebtQuadrant.html)**. A useful distinction between deliberate, inadvertent, prudent, and reckless technical debt.

2. **Martin Fowler — [Strangler Fig Application](https://martinfowler.com/bliki/StranglerFigApplication.html)**. Incrementally replacing functionality without requiring a single high-risk rewrite.

3. **Martin Fowler — [Refactoring](https://refactoring.com/)**. The foundational approach to improving software structure through small behavior-preserving transformations.

4. **Michael Feathers — *Working Effectively with Legacy Code***. Practical techniques for introducing tests, understanding unfamiliar code, and modifying tightly coupled systems safely.

5. **Adam Tornhill — *Software Design X-Rays***. An evidence-based approach to identifying code hotspots through change history and structural analysis.

6. **Martin Fowler — [Branch by Abstraction](https://martinfowler.com/bliki/BranchByAbstraction.html)**. A practical technique for replacing implementations incrementally while preserving a functioning application.

7. **Martin Fowler — [Evolutionary Database Design](https://martinfowler.com/articles/evodb.html)**. Database refactoring, incremental schema changes, and continuous delivery of evolving data models.

8. **Michael Nygard — [Documenting Architecture Decisions](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions)**. Lightweight Architecture Decision Records and preserving engineering rationale.

9. **David Farley — *Modern Software Engineering***. An exploration of experimentation, feedback, modularity, and the economics of sustainable software development.

10. **John Ousterhout — *A Philosophy of Software Design***. A rigorous discussion of complexity, abstraction, interfaces, and designing software that remains understandable as it evolves.

---


