---
id: SE215-L01
course: SE215
title: "The People and Teams Behind Software"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: null
next: SE215-L02
---


# SE215 — The Software Engineering Ecosystem

## Lecture 01: The People and Teams Behind Software

*Your manager assigns you a simple feature: let customers change their hotel reservation dates. You understand the frontend, the backend, and the database. Two weeks later, you're discussing payment reconciliation, UX research, deployment procedures, customer-support scripts, and data pipelines. Welcome to software engineering beyond the codebase.*

# Part I — Intuition

## The picture to carry in your head

Imagine you're a full-stack developer working for a hotel-booking platform.

It's Monday morning. Your product manager introduces a new feature.

Customers should be able to change their reservation dates without contacting customer support.

It sounds straightforward. You need a date picker, an API endpoint, and a database update.

You estimate three days.

Your product manager is delighted.

Then somebody asks what happens when the new dates cost more.

You propose calculating the difference and charging the customer's card.

But what happens if the payment succeeds and the reservation update fails?

The backend lead points out that changing dates requires releasing inventory for the old nights and claiming inventory for the new ones. Those changes must be coordinated so that another customer cannot claim the same scarce room capacity.

The designer asks what happens when a customer chooses unavailable dates. Should they see alternatives? Should the original booking remain reserved while they consider a change?

The security engineer asks whether a logged-in customer can modify someone else's reservation by changing an identifier in the request.

The QA engineer asks how to reproduce a payment timeout or a concurrent inventory conflict reliably.

The platform engineer asks how the database migration will behave while old and new application versions coexist.

The data analyst asks whether changing a reservation should count as a new booking or a modification of an existing one.

Customer support wants to know how agents can explain a failed date change to an angry customer.

Suddenly, your three-day feature has become a discussion involving half the company.

The problem wasn't that everybody decided to complicate a simple task.

The original task was never as simple as its description.

**A feature is not merely a piece of code. It is a change to a product, a business process, and an operating system of people and technology.**

That's the mental model for this lecture.

## 1. The company is another system you need to understand

We spend enormous amounts of time learning how software systems coordinate.

An HTTP request travels between services.

A database transaction protects related changes.

A message queue separates producers and consumers.

A deployment pipeline moves an artifact toward production.

But there's another system surrounding all of this: the engineering organization.

Different people hold different information, permissions, responsibilities, and priorities.

Product managers understand commercial goals and user needs.

Designers investigate how people interact with the product.

Engineers build and maintain its behavior.

Security specialists identify ways the system could be misused.

QA specialists develop methods for finding defects.

Platform teams provide reliable infrastructure and delivery capabilities.

Data engineers make operational information usable for analysis.

Support teams encounter customer problems that rarely appear in engineering test environments.

No single participant necessarily possesses the complete picture.

That is why a mature engineering organization needs collaboration, not merely excellent individual contributors.

## 2. Job titles describe responsibilities imperfectly

There's a trap here.

You might imagine every company has one product manager, one designer, one QA engineer, one DevOps engineer, and a neat organizational chart assigning each responsibility to exactly one person.

Real companies are messier.

At a small startup, a full-stack engineer might write the application, configure infrastructure, develop automated tests, and investigate production incidents.

At a larger company, those responsibilities may be distributed among specialized teams.

Some organizations have separate frontend and backend teams.

Others organize engineers around business capabilities, with each team owning an entire feature from interface to database.

Some companies employ dedicated QA automation engineers.

Others expect application developers to own most test automation, with quality specialists advising on test strategy and difficult scenarios.

The titles matter less than the responsibilities being performed.

**When encountering an unfamiliar role, ask what problem it owns, what decisions it makes, and how its work interacts with yours.**

## 3. Handoffs are where assumptions become defects

Imagine the designer creates a beautiful date-change screen.

The frontend developer implements it.

The backend developer exposes an endpoint.

The QA engineer tests the happy path.

The feature passes every test.

But nobody clarified what happens if the payment provider returns a timeout after successfully charging the customer.

The frontend assumes the request failed.

The backend doesn't know whether payment succeeded.

The customer retries.

Now the customer may have been charged twice.

This is not necessarily a failure of any single engineer's technical competence.

It's a missing agreement across several boundaries.

The designer needed to represent an uncertain outcome.

The backend needed a durable operation identity and recovery behavior.

The payment integration needed idempotency and reconciliation.

The tests needed to exercise the ambiguous response.

The product team needed to decide what the user should see.

The problem crossed responsibilities, and the contract between them was incomplete.

You already know this pattern from software architecture.

Two individually correct components can form an incorrect system.

The same thing happens between teams.

## Three questions before the Deep Dive

1. Why can a feature be correctly implemented according to its ticket and still fail the business?
2. How can two companies assign the same responsibility to completely different job titles?
3. When you discover an important requirement nobody mentioned, is your job simply to implement it yourself?

Keep those questions in mind as we follow our reservation-date feature through the organization.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 1. Product management: are we building the right thing?

Our feature begins with a product manager.

The product manager's central responsibility is generally deciding what product problems deserve attention and helping establish the desired outcomes.

Why do customers need self-service reservation changes?

Perhaps thirty percent of customer-support contacts involve date modifications.

Perhaps those calls are expensive.

Perhaps customers abandon bookings because they're uncertain whether dates can be changed later.

Perhaps competitors already offer the capability.

These are different business motivations, and they may lead to different product decisions.

If the goal is to reduce support volume, we care about how many customers can successfully complete their changes without contacting an agent.

If the goal is to improve booking conversion, we care about whether flexible changes make customers more willing to book in the first place.

If the goal is customer satisfaction, reducing confusion and failed change attempts may matter more than the raw number of completed changes.

### Output versus outcome

"Ship a date-change button" is an output.

"Reduce date-related support contacts while maintaining booking correctness" is an outcome.

A product manager should help connect the two.

This doesn't mean product managers always know the correct solution.

They may be working with incomplete information, commercial pressure, stakeholder disagreements, and uncertain user behavior.

A good developer can contribute by identifying technical constraints and possible alternatives.

For example, perhaps the company can deliver a simpler first version supporting changes only when no additional payment is required.

That may capture much of the value while postponing a complex payment-reconciliation workflow.

This is a product and engineering trade-off.

### Product owner isn't necessarily a separate job

You may also encounter the title *product owner*, particularly in Scrum-oriented organizations.

In Scrum, Product Owner is an accountability associated with maximizing product value and managing the Product Backlog.

Some companies employ someone with that literal title.

Others assign those responsibilities to a product manager or another person.

Don't assume the vocabulary maps perfectly to every organizational chart.

The important question is who prioritizes product decisions and resolves competing requirements.

## 2. Engineering management: can the team deliver sustainably?

Now the feature receives approval.

The engineering manager becomes involved.

An engineering manager often focuses on team effectiveness, staffing, professional development, delivery coordination, and organizational constraints.

They may ask whether the team has enough capacity.

Are two developers already committed to another release?

Does the payment integration require expertise the team lacks?

Will the new feature create additional on-call responsibilities?

Is the estimate realistic given the current workload?

The engineering manager's responsibilities are not identical to the product manager's.

The product manager is generally concerned with product direction and value.

The engineering manager is generally concerned with the engineering team's ability to deliver and operate that value effectively.

The boundary varies across companies, but the distinction is useful.

### What about the tech lead?

A technical lead commonly guides technical design and engineering decisions for a team or project.

For our reservation feature, the tech lead might ask which service owns inventory, where the transaction boundary belongs, and how the API should expose uncertainty.

They may coordinate reviews and mentor developers working on unfamiliar components.

In some organizations, the tech lead is also the engineering manager.

Elsewhere, the roles are separate.

And in some teams, senior engineers share technical leadership without a formal lead title.

The practical lesson is that *technical leadership* is a responsibility, not merely a promotion label.

## 3. UX and product design: what will the customer experience?

Our designer starts examining the date-change workflow.

A junior interpretation of design might be: choose colors, arrange buttons, and provide a Figma file.

That's a small part of the work.

A product designer considers how users understand and complete a task.

What information do they need?

What mistakes are they likely to make?

What happens when the task fails?

How does the interface communicate uncertainty?

How can it remain usable across different devices and accessibility needs?

### Follow the customer's decisions

Imagine the customer opens an existing reservation.

They select new dates.

The system calculates a price difference.

Now the customer needs to know whether the new reservation is guaranteed, whether the original dates remain protected, and whether an additional charge will occur.

A well-designed interface should make those commitments clear.

It must also handle unavailable inventory, price changes during confirmation, errors, and ambiguous payment outcomes.

These aren't merely visual states.

They're representations of real business behavior.

### UX research isn't the same as UI design

UX researchers may study how people actually use the product.

They can conduct interviews, observe task completion, evaluate prototypes, and identify recurring usability problems.

A product designer may perform some of this work directly.

In a larger organization, research and design may be specialized roles.

Their findings can challenge engineering assumptions.

Perhaps customers don't want to edit reservation dates through a complicated calendar at all.

Perhaps they primarily need a clear explanation of whether a booking is refundable or changeable.

A developer who understands this distinction can contribute to solving the real user problem rather than merely implementing the first proposed interface.

## 4. Application engineers: turning the product into behavior

Now the development team gets to work.

A frontend engineer implements the customer-facing interaction.

A backend engineer handles inventory allocation, reservation state, and payment coordination.

A full-stack engineer may own substantial portions of both.

But those labels don't determine the architecture.

A company can have separate frontend and backend specialists within one product team.

Or a cross-functional engineering team may own the complete feature.

### The frontend responsibility

The frontend must display current reservation information, accept new dates, and communicate operation state.

It must distinguish between selecting new dates and successfully changing a booking.

It must also handle loading, invalid inputs, rejected changes, and an uncertain remote outcome.

These concerns belong in actual frontend engineering, not merely presentation code.

### The backend responsibility

The backend must validate the customer's authority, check business rules, coordinate inventory changes, and maintain durable booking state.

If payments are involved, it must account for external failures and idempotency.

The backend also defines contracts that allow the frontend to represent those situations correctly.

### The shared boundary

Neither team should invent the API contract independently.

Suppose the backend represents an uncertain booking result as a generic HTTP 500 error.

The frontend might interpret that as a definite failure.

But a failed HTTP response doesn't necessarily prove that the underlying booking wasn't committed.

A more deliberate operation contract can preserve the necessary distinction.

This is where frontend and backend engineers should agree on behavior before implementing their respective halves.

The API is a technical interface and a team interface.

## 5. QA and test engineering: what have we actually verified?

The feature is implemented.

Now someone must determine whether it works.

A traditional approach assigns all testing responsibility to a separate QA department.

A more collaborative approach treats quality as a shared engineering responsibility, with QA and test specialists contributing expertise in risk analysis, test design, automation, exploratory testing, and verification strategy.

Neither organizational model is universally superior.

But there's a strong argument for developers owning the automated tests directly related to their code.

They understand the implementation.

They can reproduce failures locally.

They can fix regressions without waiting for another team to diagnose the issue.

### Different tests answer different questions

A unit test might verify how the date-change price difference is calculated.

An integration test might verify that inventory changes and reservation persistence succeed or fail atomically.

A browser E2E test might verify that a customer can initiate a date change and receive the appropriate final state.

An exploratory tester might discover that the interface becomes confusing when a customer changes dates twice in quick succession.

These tests provide different kinds of evidence.

No one test layer proves the entire system is correct.

### What does a QA specialist contribute?

An experienced QA engineer may be especially good at discovering overlooked scenarios.

What happens with a reservation whose new dates cross a daylight-saving transition?

What if the customer has multiple rooms but wants to change only one?

What if the payment succeeds and the browser disconnects?

What if the reservation becomes unavailable between displaying the quote and confirming the change?

These cases often expose gaps in requirements and architecture.

The value isn't simply producing more automated test files.

It's improving the team's understanding of risk.

A developer should see QA as a collaborator in defining correctness, not merely a final checkpoint before release.

## 6. Security engineering: could the feature be abused?

The security engineer reviews the proposed API.

It accepts a reservation identifier and new dates.

The frontend hides the date-change button unless the logged-in user owns the reservation.

Is that enough?

No.

The backend must independently enforce authorization.

A malicious client can send arbitrary requests without using the intended interface.

If changing the reservation identifier allows one customer to modify another customer's booking, we have a serious authorization vulnerability.

### Threat modeling

Security engineers often help identify how an attacker might interact with a feature.

Which identities can invoke the operation?

Which resources can they affect?

Which data crosses trust boundaries?

What happens when someone manipulates request parameters?

Could a user repeat an operation to trigger multiple charges or refunds?

Are sensitive details exposed in logs?

This process is called threat modeling.

It can be lightweight or formal depending on the risk.

### Security isn't one team's private responsibility

A security specialist can establish standards, review high-risk designs, and provide tooling and guidance.

But application developers remain responsible for writing secure code.

A security review doesn't transfer ownership of every authorization decision away from the feature team.

The most effective organizational model is usually one in which security expertise influences engineering practice before defects reach production.

## 7. DevOps and platform engineering: how does the feature reach production?

The team finishes implementation.

Tests pass.

Now the software needs to be deployed.

You may hear someone say, "DevOps handles deployment."

That statement hides several different responsibilities.

### DevOps is broader than a job title

DevOps originally emphasizes reducing the separation between development and operations through shared responsibility, automation, fast feedback, and reliable delivery.

Many companies also have employees with the literal title *DevOps engineer*.

Their practical work may include cloud infrastructure, CI/CD pipelines, deployment automation, monitoring systems, networking, or other operational responsibilities.

The job title is common, but it doesn't define one universal organizational model.

### Platform engineering

A platform engineering team builds internal capabilities that help application teams deliver and operate software.

It might provide a standardized way to create services, obtain environments, configure secrets, run tests, deploy applications, and observe production behavior.

The platform is a product for internal developers.

A good platform reduces repetitive infrastructure work while giving application engineers enough control to perform their jobs.

For example, our booking team may not need to understand every Kubernetes manifest.

It still needs to specify resource requirements, health behavior, configuration, and deployment expectations.

The platform team can provide the machinery.

The application team must describe what a healthy application actually means.

### Our date-change migration

Suppose the feature introduces a new reservation-state field.

The database migration must be compatible with application versions running during rollout.

The platform team may provide migration tooling and deployment controls.

But only the application developers may fully understand the business meaning of the new field.

A reliable deployment requires both kinds of expertise.

Automation cannot compensate for an incorrect application contract.

## 8. SRE and operations: will the feature remain healthy?

The feature reaches production.

Customers begin using it.

Who knows whether it is behaving correctly?

This is where reliability engineering becomes important.

A Site Reliability Engineer, or SRE, applies software-engineering approaches to operating reliable systems.

Depending on the organization, SRE responsibilities may include service-level objectives, monitoring, incident response, capacity planning, automation, and improving operational resilience.

Some SRE teams operate shared infrastructure.

Others work closely with product teams on particular services.

### Deployment success isn't product success

Suppose Kubernetes reports a successful rollout.

All pods are running.

The API responds to health checks.

Yet five percent of date changes now fail after payment authorization.

The infrastructure is functioning as configured.

The business operation is not.

The application team must expose meaningful indicators of success.

How many changes were attempted?

How many completed?

How many entered an uncertain state?

How many required manual reconciliation?

How many caused duplicate payment attempts?

An SRE or platform engineer can help build reliable measurement and alerting infrastructure.

But domain-aware monitoring depends on application engineers understanding what successful behavior means.

### Incident ownership is collaborative

If the new feature causes an incident, the engineering organization needs a clear response process.

Someone coordinates mitigation.

Someone investigates the application.

Someone examines infrastructure evidence.

Someone handles customer communication.

These responsibilities may overlap, but they should not be ambiguous when the service is failing.

A well-run incident is not a contest to determine which team deserves blame.

It's an effort to restore service, understand the failure mechanism, and reduce the chance of recurrence.

## 9. Data engineering and analytics: did the feature actually help?

The date-change feature has been available for a month.

The product manager wants to know whether it succeeded.

Customer-support contacts have decreased.

Excellent.

But did booking modifications become easier?

Did refunds or payment problems increase?

Did customers begin changing reservations more often because the process became convenient?

Did the feature improve retention or reduce abandonment?

We need reliable information to answer these questions.

### Application data isn't automatically analytical data

Our PostgreSQL database stores reservations and their current states.

That's operational data.

An analyst may want historical facts about changes over time.

When was a change requested?

Which dates were originally selected?

Was it approved or rejected?

Did the customer abandon the process?

What price difference was shown?

These facts may need explicit events or historical records.

A current reservation row cannot necessarily reconstruct every previous state.

### Data engineers build reliable information flows

A data engineer might help move operational events and database changes into an analytical environment.

They may manage ingestion, transformation, schema contracts, data quality, orchestration, and recovery from processing failures.

The result could be a warehouse table that analysts use to measure the feature's performance.

But the application developers have an important responsibility.

They must produce meaningful, stable data.

If the backend emits an event called `booking_created` every time dates change, the analytics pipeline may interpret each modification as a completely new booking.

The data engineer can process that event perfectly.

The resulting report can still be wrong.

The event's semantics were incorrect at the source.

This is another example of a technically valid integration that fails at the boundary between teams.

## 10. Customer support, documentation, and other stakeholders

Not every contributor is an engineer.

Customer-support teams see where product behavior diverges from customer expectations.

They may discover that customers cannot understand a cancellation rule or that an error message instructs them to repeat an operation that must not be repeated.

Technical writers and documentation specialists help make product behavior understandable to users and internal teams.

Legal, privacy, compliance, and finance specialists may be involved when changes affect contracts, personal data, payments, or regulated activity.

For our reservation-date feature, customer support needs to answer practical questions.

Did the original reservation survive the failed change?

Was the customer charged?

When will an additional charge appear?

Can an agent safely retry the operation?

A technically correct implementation with no coherent customer-facing explanation may still create substantial operational pain.

This doesn't mean every small feature needs approval from every department.

It means the feature team should identify which stakeholders are relevant to the particular risks and decisions involved.

## 11. How the same feature changes across company sizes

Let's compare three organizations.

### A small startup

One product-minded founder defines the feature.

One designer works part-time on the interface.

Two full-stack engineers implement the system, write automated tests, deploy the application, and respond to incidents.

An external accountant and payment provider handle specialized financial responsibilities.

The work still exists.

There are simply fewer people performing it.

### A growing SaaS company

A product manager coordinates requirements.

A cross-functional engineering team owns the feature.

Design and QA specialists work closely with the team.

A platform group provides deployment infrastructure.

Security reviews are risk-based.

A data team maintains analytical pipelines.

This can give specialists more focus while preserving product ownership within one team.

### A large enterprise

Responsibilities may be split across several departments.

Frontend and backend teams may have separate planning cycles.

A central identity platform may enforce authorization patterns.

Changes may require coordination with security, compliance, infrastructure, and data governance.

Specialization can create valuable expertise.

But excessive handoffs can increase lead time and make ownership unclear.

The critical lesson is that organizational structure creates trade-offs, just like software architecture.

A highly specialized company may have deep expertise but slower coordination.

A small team may move quickly but lack redundancy and specialist knowledge.

There is no single universally correct organization chart.

## 12. The handoff problem: responsibilities need interfaces

Consider how many teams have touched our feature.

Product defines the intended outcome.

Design defines the customer interaction.

Engineering implements the behavior.

QA develops verification strategies.

Security reviews important trust boundaries.

Platform engineering provides delivery capabilities.

SRE helps establish reliability.

Data engineering supports measurement.

Customer support handles operational consequences.

A naïve organization might define these as a strict sequence.

Product finishes its work and hands a specification to design.

Design finishes and hands mockups to engineering.

Engineering finishes and hands the feature to QA.

QA approves and hands it to operations.

Each department declares its stage complete.

But software changes rarely behave like independent factory steps.

A technical constraint can invalidate a design assumption.

A usability study can reveal a new requirement.

A security concern can change an API.

An operational limitation can change the rollout plan.

Waiting until the previous group is completely finished before discovering these conflicts creates expensive rework.

### Collaboration is an engineering optimization

A better approach brings relevant specialists into discussions when their expertise can still influence the design.

The product manager and designer may clarify the desired behavior with engineering before creating final specifications.

The backend developer may explain uncertain payment outcomes before the UI is implemented.

The QA engineer may identify important failure cases while the API contract is being designed.

The platform engineer may flag deployment compatibility requirements before the migration is written.

This isn't collaboration for its own sake.

It's an attempt to discover incorrect assumptions while they're still cheap to correct.

### Ownership versus consultation

Not everyone needs to approve every decision.

That would make the organization painfully slow.

A useful distinction is between who owns a decision and who should be consulted.

The product manager may own prioritization.

The engineering team may own technical implementation.

Security may establish mandatory requirements for sensitive operations.

Platform engineering may own shared infrastructure interfaces.

The team must decide how to coordinate these responsibilities without creating endless approval chains.

Some organizations formalize responsibilities through approaches such as RACI, which distinguishes responsible, accountable, consulted, and informed participants.

Such tools can help when ownership is confusing.

But they should clarify work, not replace normal conversation with bureaucracy.

## 13. What a senior full-stack developer should contribute

Now imagine you're the developer responsible for our feature.

You don't need to become a professional product manager, designer, security engineer, and data engineer simultaneously.

But you should understand enough of those domains to ask useful questions.

You should recognize that a date-change workflow has financial and inventory implications.

You should identify when a frontend state cannot represent uncertainty.

You should understand how an E2E test differs from a mocked component test.

You should recognize that a database migration has deployment compatibility concerns.

You should know when an event schema may distort business analytics.

And you should know which colleague can help resolve a question outside your expertise.

This is one of the characteristics that separates an experienced application programmer from a mature engineer.

The programmer sees the implementation.

The mature engineer sees the system of consequences surrounding it.

### Practical judgment beats universal expertise

Sometimes the correct contribution is implementing the solution yourself.

Sometimes it is raising a question early.

Sometimes it is involving a specialist.

Sometimes it is proposing a smaller first release.

And sometimes it is refusing to declare a feature complete until a crucial business invariant has been addressed.

The objective isn't to take over everyone else's work.

It's to prevent important knowledge from falling between responsibilities.

---

# The Oral Examination

Answer each question aloud before reading the solutions.

### Question 1 — Product versus engineering

A product manager wants a new booking feature released this week. The engineering manager believes the team cannot deliver it safely without dropping another commitment.

What different concerns do these roles represent, and how should the disagreement be approached?

### Question 2 — Design isn't decoration

A date-change screen looks beautiful but provides no way to represent a payment whose outcome is unknown.

Is this a design problem, a backend problem, or both?

### Question 3 — Quality ownership

A company has dedicated QA automation engineers. Should application developers still write automated tests? Why?

### Question 4 — DevOps versus platform engineering

What is the difference between DevOps as an engineering approach and a platform team as an organizational capability?

### Question 5 — Production responsibility

A Kubernetes deployment completes successfully, but the new feature produces invalid booking outcomes.

Which team owns the problem?

### Question 6 — Data contracts

A data-engineering pipeline accurately processes every event, yet the analytics dashboard counts reservation modifications as new bookings.

Where did the defect originate?

### Question 7 — The senior engineer's contribution

You're assigned an apparently simple feature but discover payment, security, inventory, and analytics implications that were absent from the ticket.

What should you do?

---

# Solutions and Discussion

## Solution 1 — Different constraints, shared decision

The product manager is concerned with business priorities and expected value.

The engineering manager is concerned with sustainable team capacity and delivery risks.

They should make the trade-off explicit: reduce scope, adjust timing, reprioritize existing work, or accept a clearly understood risk within appropriate constraints.

Neither role automatically wins merely because of its title.

## Solution 2 — The interface must represent real system states

Both disciplines are involved.

The backend must provide a coherent operation contract and a way to discover the authoritative outcome.

The design must communicate uncertainty and guide the customer safely.

Implementing either side independently can create an incorrect experience.

## Solution 3 — Developers still own quality

Dedicated QA specialists contribute testing expertise, risk analysis, exploratory investigation, and automation.

Developers should still write and maintain tests relevant to their code and collaborate on important integration and end-to-end scenarios.

Quality is a property of the delivered system, not a document handed to one department.

## Solution 4 — Philosophy versus internal product capability

DevOps emphasizes collaboration, automation, and shared responsibility across development and operations.

A platform team creates internal services and tools that help developers build, deploy, and operate software.

A platform team may support DevOps principles, but the two concepts aren't synonymous.

## Solution 5 — Cross-functional incident, clear coordination

A successful infrastructure rollout doesn't guarantee business correctness.

The application team must investigate its business logic and invariants.

Platform or SRE specialists may help with evidence, mitigation, and operational tooling.

Someone should coordinate incident response, but responsibility for restoring correct behavior is shared across the relevant technical boundaries.

## Solution 6 — The application event was semantically wrong

The pipeline faithfully processed an event whose meaning did not match the underlying business action.

The source application and data consumers need a shared event contract.

Perfect data processing cannot repair incorrect business semantics without additional information.

## Solution 7 — Surface the dependencies early

Clarify the relevant requirements, identify the risks, involve the appropriate specialists, and propose a defensible scope and delivery plan.

Do not silently implement speculative behavior or simply declare the ticket impossible.

A mature engineer translates newly discovered complexity into decisions the team can make.

---

# The Mental Model Worth Keeping

A software organization is a network of responsibilities, information, and decisions.

To understand a neighboring discipline, ask three questions:

**What problem does this discipline solve?**

**Which decisions or systems does it typically own?**

**Where does its work intersect with mine?**

And when delivering a feature, ask:

**Who knows something important that our current implementation plan may be missing?**

The senior engineer's advantage isn't knowing every technology or performing every specialist role.

**It's understanding the whole delivery system well enough to recognize missing contracts, involve the right expertise, and prevent local success from becoming global failure.**

# Next Lecture — SE215-L02: How Engineering Work Gets Planned and Delivered

We've met the people and responsibilities involved in delivering software.

Now suppose all those people are working hard, every sprint looks busy, and tickets are constantly being completed—yet the product repeatedly misses important deadlines.

Why?

Perhaps the team is accepting more work than it can finish.

Perhaps dependencies remain hidden until too late.

Perhaps estimates are being treated as promises.

Perhaps Scrum ceremonies are performed religiously while actual bottlenecks go unexamined.

In the next lecture, we'll examine how engineering work gets planned, prioritized, coordinated, and improved through approaches such as Scrum, Kanban, and continuous delivery.

The aim won't be to memorize Agile terminology.

It will be to understand how a team can deliver meaningful software predictably without turning development into a bureaucratic obstacle course.

*The spoken lecture ends here. The remaining material is for practical investigation and screen-based revision.*

---

# Optional Practical Workshop — Map a Feature Across Teams

## Exercise A — Identify the responsible participants

Take the self-service reservation-date feature from the lecture.

Build a small responsibility map for the following decisions:

| Decision | Likely primary owner | Participants to consult |
|---|---|---|
| Why build the feature? | Product management | Customers, support, engineering |
| How should the interaction work? | Product/UX design | Engineering, research, accessibility |
| How is inventory protected? | Backend engineering | Technical lead, database specialists |
| How are sensitive operations authorized? | Application engineering | Security |
| How is the customer journey tested? | Feature team | QA/test specialists |
| How does it reach production? | Application/platform teams | SRE, security |
| How is service health monitored? | Service owners | SRE/platform |
| How is product success measured? | Product/analytics | Data engineering, application team |

This is illustrative, not a universal RACI chart. Adapt it for a startup with four employees and for an enterprise with twenty specialized teams.

**Question:** Which responsibilities remain necessary even when there is no dedicated specialist with the corresponding title?

## Exercise B — Improve the feature requirements

The original ticket reads:

"Allow customers to change reservation dates."

Rewrite it into a short specification covering:

- Which reservations may be modified.
- Who is authorized to modify them.
- How availability is checked and claimed.
- What happens when prices change.
- How payment and refund outcomes are handled.
- What the customer sees during an uncertain outcome.
- How failures are recovered.
- What events or metrics are needed to evaluate success.

Then distinguish which statements are product decisions, which are technical decisions, and which require cross-functional agreement.

## Exercise C — Identify the first broken handoff

Consider this release:

1. Product approves a date-change feature.
2. Design provides the success screen and ordinary error screen.
3. Backend implements date changes and additional payments.
4. Frontend treats every HTTP timeout as a failed booking change.
5. QA tests the normal success path.
6. Deployment completes without infrastructure errors.
7. Customers report duplicate payment attempts.

Prepare a five-minute explanation identifying the earliest missing agreements, the participating responsibilities, and what should change in the development process.

Don't simply blame the QA engineer for missing a test. Ask why the ambiguous outcome was never properly modeled.

## Exercise D — Senior interview rehearsal

Practice answering:

"Tell me about a time you collaborated with another team to deliver a feature or resolve a technical problem."

A strong response should establish the problem, the teams involved, the conflicting constraints, your personal contribution, the decision reached, and its result.

Avoid vague statements such as "we communicated regularly."

Explain what information crossed the team boundary and how that changed the technical outcome.

---

# Further Reading

For deeper perspectives on engineering organizations and professional responsibilities:

- **Google SRE Book** — https://sre.google/sre-book/table-of-contents/
- **DORA — DevOps Research and Assessment** — https://dora.dev/
- **Team Topologies**, Matthew Skelton and Manuel Pais — https://teamtopologies.com/
- **The Scrum Guide** — https://scrumguides.org/
- **Atlassian Agile Resources** — https://www.atlassian.com/agile

Related programme chapters:

- SE215-L02 — How Engineering Work Gets Planned and Delivered
- SE215-L06 — DevOps, Platform Engineering, and Operational Ownership
- SE215-L07 — Owning End-to-End Testing
- SE215-L09 — Data Engineering for Application Developers
- SE215-L10 — Working With Product, Design, and Analytics
- SE330-L03 — Maintaining and Evolving Real Software
- SE440-L02 — Reliability Engineering and Incident Response

---

## Dense Cheatsheet — Interview Glance Card

```text
SE215-L01 — THE PEOPLE AND TEAMS BEHIND SOFTWARE

CORE PRINCIPLE
  A feature is a change to a product, business process,
  technical system, and engineering organization.

PRODUCT MANAGEMENT
  What problem is worth solving?
  What outcome matters?
  Scope, priorities, stakeholders, success criteria
  Output != outcome

PRODUCT OWNER
  Scrum accountability for product value/backlog
  May overlap with product manager role
  Titles differ across organizations

ENGINEERING MANAGEMENT
  Team capacity, staffing, sustainable delivery,
  professional development, coordination

TECHNICAL LEADERSHIP
  Technical decisions, architecture, engineering quality,
  technical risks, mentoring and design coordination
  Responsibility may be distributed across senior engineers

UX / DESIGN
  User journeys, interaction models, usability, accessibility,
  prototypes, design systems, failure and uncertainty states
  UX research studies actual user behavior
  Design != merely attractive screens

FRONTEND ENGINEERING
  Interface behavior, client state, interaction,
  accessibility, API integration, error/uncertain states

BACKEND ENGINEERING
  Domain rules, persistence, authorization,
  transactions, business invariants, external integrations

QA / TEST ENGINEERING
  Test strategy, risk analysis, exploratory testing,
  automated verification, failure scenarios
  Quality is shared responsibility
  Mocked E2E != full-system E2E

SECURITY ENGINEERING
  Threat modeling, trust boundaries, authorization,
  least privilege, sensitive data, abuse prevention
  Security specialists advise; developers still own secure code

DEVOPS
  Collaboration, automation, feedback, shared delivery
  and operational responsibility
  Philosophy/practices != one universal job title

PLATFORM ENGINEERING
  Internal developer platform and self-service capabilities
  Build/deploy infrastructure, environments, standardization
  Platform is an internal product for development teams

SRE
  Reliability, SLOs, monitoring, capacity, incidents,
  operational automation and resilience
  Infrastructure healthy != business operation healthy

DATA ENGINEERING
  Operational events -> ingestion -> transformation -> analytics
  Data quality, orchestration, lineage, recovery
  Accurate pipeline + incorrect event meaning = wrong report

PRODUCT ANALYTICS
  Measure outcomes, not merely completed features
  Conversion, task completion, support volume, retention,
  failed workflows and user experience

CUSTOMER SUPPORT
  Real customer problems, recovery guidance,
  communication, product feedback
  Critical source of overlooked failure scenarios

SMALL VS LARGE COMPANIES
  Same responsibilities, different role distribution
  Startup: generalists wear many hats
  Growing SaaS: cross-functional teams + shared specialists
  Enterprise: greater specialization, more coordination costs

TEAM BOUNDARIES
  Ownership = who decides or maintains
  Consultation = who supplies necessary expertise
  Handoff = where information and assumptions cross
  Missing contracts cause cross-team failures
  RACI can clarify responsibility; don't bureaucratize everything

DELIVERY FAILURE
  Product ticket says "change booking dates"
  But feature also changes inventory, payments, authorization,
  UX states, tests, deployment, analytics and support
  Local correctness may still produce system failure

SENIOR ENGINEER'S ROLE
  See consequences beyond implementation
  Surface missing requirements early
  Identify cross-functional risks
  Involve specialists appropriately
  Make trade-offs explicit
  Don't attempt to own every profession

INTERVIEW FRAMEWORK
  Problem -> stakeholders -> conflicting constraints ->
  your contribution -> technical/product decision ->
  delivery outcome -> lesson learned

DURABLE MENTAL MODEL
  What problem does this role solve?
  Which decisions or systems does it own?
  Where does its work intersect with mine?

FINAL PRINCIPLE
  Mature engineers understand enough of the whole
  delivery system to recognize when something important
  is falling between responsibilities.
```
