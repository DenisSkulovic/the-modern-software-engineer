---
id: SE325-L04
course: SE325
title: "Production Data Repair, Audit, and Lifecycle"
type: elective
manuscript: manuscript
edition: "2.0.0"
legacy_ids: []
prev: SE325-L03
next: SE325-L05
---

# SE325 — Backends in the Wild: Production Field Guide
## Lecture 04: Production Data Repair, Audit, and Lifecycle

*Support needs one broken booking fixed. An engineer proposes a production SQL UPDATE. The row is wrong in PostgreSQL—but the same information also exists in Redis, a search index, yesterday's analytics export, a backup, and tomorrow's scheduled reconciliation job. Which one are you actually fixing?*

---

# Part I — Intuition

## 1. The Reservation That Wouldn't Stay Fixed

Imagine you're working at Mercury, a hotel-booking platform.

A customer completed a reservation yesterday. Their payment succeeded, and the external hotel supplier confirmed the room.

But Mercury's administrative interface still shows the reservation as pending.

Support has been investigating the issue for several hours. The customer has a confirmation from the hotel, but the booking platform appears to disagree.

Eventually, an engineer discovers the relevant PostgreSQL record.

Its status is `PENDING`.

The engineer knows the reservation should be `CONFIRMED`.

The obvious solution is to run an SQL update.

Change the status.

Refresh the support page.

Problem solved.

For about ten minutes, everything looks correct.

Then the booking becomes pending again.

The engineer checks PostgreSQL.

The status has reverted.

Was the database transaction rolled back?

No.

Did another engineer undo the repair?

No.

A scheduled reconciliation job ran.

It retrieved an old status from a supplier synchronization table and obediently wrote `PENDING` back into the booking record.

The manual repair corrected one value.

It didn't correct the process that was producing the wrong value.

Now another problem appears.

A customer-facing page still displays the old status because Redis contains a cached representation.

An internal search index also contains the stale version.

An analytics report has already classified the booking as unconfirmed.

The booking exists in several places, and each place has its own relationship with reality.

**Fixing a row is not necessarily the same thing as fixing a business fact.**

## 2. One Fact Can Have Many Representations

Imagine a government office maintaining an official record of a person's address.

That address might also appear in several other systems.

A postal service uses it for deliveries.

A school uses it for correspondence.

A bank has its own copy.

An analytics department includes it in regional statistics.

Correcting the official register doesn't instantly correct every other system.

Software applications face the same problem.

The booking database might be authoritative for reservation state.

Redis may cache a representation.

Elasticsearch may maintain a searchable copy.

A data warehouse may store events or derived records.

A scheduled job may import status updates from an external provider.

Those systems aren't necessarily broken when they disagree temporarily.

They may be working according to different synchronization rules.

But the application needs to know which representation is authoritative and how the others converge toward it.

### Visual anchor 1 — One booking, several copies

```text id="dp4a01"
              Hotel supplier
                    |
                    v
           Reconciliation feed
                    |
                    v
         PostgreSQL bookings
            Authoritative
                    |
         +----------+----------+
         |          |          |
         v          v          v
       Redis      Search     Analytics
       cache      index      warehouse
```

In this example, the supplier feed is another source of evidence. It isn't automatically authorized to overwrite every newer business decision in the booking database.

That distinction will become important.

## 3. A Repair Is a Business Operation

Suppose the booking status is wrong.

What exactly are you authorized to change?

The current status?

The payment state?

The customer's invoice?

The supplier confirmation reference?

The reservation inventory?

Those fields represent different business facts.

Changing a status from `PENDING` to `CONFIRMED` may be safe if authoritative evidence establishes that the booking is already confirmed and the update merely corrects Mercury's stale representation.

But suppose the supplier never confirmed the booking.

Changing the status would create the appearance of a successful reservation without establishing the underlying business fact.

The SQL command would execute correctly.

The business would become less correct.

A safe repair therefore begins with evidence.

What happened in the real world?

What does the database currently say?

Why do those disagree?

What is the intended correction?

What other operations depend on the value?

What could overwrite the correction later?

This isn't merely database administration.

It's domain logic performed under unusual operational circumstances.

## 4. The Repair Must Know What It Is Changing

Imagine the engineer prepares a command that changes booking 482 from pending to confirmed.

Before execution, they verify that the booking belongs to the correct tenant, is currently pending, and corresponds to the verified supplier confirmation.

But while the engineer is reviewing the command, another process updates the booking.

The original assumption is no longer true.

A safer repair doesn't blindly proceed.

It checks that the expected state still exists when the change is committed.

This is similar to optimistic concurrency control.

The repair states:

"Update this one record only if it is still the record and version I examined."

If the condition no longer holds, stop and investigate.

### Visual anchor 2 — The guarded repair

```text id="dp4a02"
Evidence:
  Supplier confirmed booking
             |
             v
Precondition:
  Booking 482 is PENDING, version 5
             |
             v
Conditional update:
  Set CONFIRMED, version 6
             |
       +-----+------+
       |            |
       v            v
   One match      No match
       |            |
       v            v
    Commit      Stop and
                investigate
```

The number of affected rows matters.

For a targeted single-booking repair, updating zero rows or several rows may both indicate that the intended assumptions were wrong.

## 5. A Repair Needs a Memory

Suppose support returns the following month with another inconsistent reservation.

The previous engineer is no longer with the company.

Nobody remembers why booking 482 was manually changed.

There is no ticket linked to the database operation.

No audit record.

No evidence of who approved the correction.

The database contains the new value, but not the explanation.

This is an operational weakness.

A good repair process should record enough information to reconstruct what happened.

The identity of the affected business record.

The reason for the correction.

The evidence supporting it.

The actor and approval.

The expected and resulting versions.

The time of execution.

And the verification outcome.

However, an audit trail should not become an indiscriminate storage facility for sensitive customer information.

Often the relevant metadata and a reference to restricted evidence are more appropriate than copying an entire personal-data record into immutable logs.

## 6. Now the Customer Wants Their Data Deleted

A week later, another request reaches support.

A customer asks Mercury to delete their account and personal information.

The developer opens the customer table.

There is a record containing their name and email address.

Surely deleting that record is enough?

Not necessarily.

The email address may also exist in booking records, customer-support messages, Redis caches, search indexes, analytics exports, log entries, and object storage.

Backups may contain older snapshots.

An email provider may have received the address.

A third-party analytics service may hold event data.

And some financial records may be subject to legally required retention.

The question isn't merely how to execute a database `DELETE`.

It is what information the organization holds, for what purpose, under which legal obligations, and how all affected systems should respond.

### Visual anchor 3 — The personal-data footprint

```text id="dp4a03"
             Customer identity
                    |
     +--------------+--------------+
     |              |              |
     v              v              v
 Application      Search         Support
 database          index          records
     |              |              |
     +--------+-----+-------+------+
              |             |
              v             v
          Analytics       Backups
              |
              v
       External recipients
```

Some representations can be deleted immediately.

Some may require controlled retention.

Some may be aggregated or genuinely anonymized.

Others may remain in protected backups until their established retention lifecycle completes, subject to applicable requirements.

**Deleting data is a coordinated lifecycle operation, not simply a SQL statement.**

## 7. Soft Deletion Is Not Erasure

Many applications have a field such as `deleted_at`.

When an account is deleted, the system records a timestamp and hides the account from ordinary queries.

This is called soft deletion.

Soft deletion can support recovery, auditability, and business workflows.

But the personal data may still exist.

A soft-deleted record isn't necessarily erased.

Similarly, removing an object from an index doesn't mean its bytes have disappeared from all backups or previous versions.

We need to distinguish several concepts.

**Hiding:** The application no longer displays the record.

**Deactivating:** The account or resource cannot be used normally.

**Soft deletion:** The record remains stored but is marked deleted.

**Erasure:** Personal information is removed or otherwise handled to satisfy the applicable erasure requirements.

**Anonymization:** Information is transformed so that individuals are no longer identifiable under the relevant standard and circumstances.

These concepts shouldn't be used interchangeably.

## 8. A Backup Can Resurrect the Past

Imagine that Mercury processes the customer's erasure request.

The live database no longer contains their email address.

Caches and search indexes have been updated.

The privacy workflow reports completion.

Then production suffers a serious database failure.

The company restores a backup from last week.

That backup contains the customer's old email address.

Unless the recovery process accounts for completed erasure obligations, the supposedly removed information can reappear in the live environment.

This is one reason deletion and disaster recovery cannot be designed independently.

A system needs a way to preserve relevant erasure obligations across restoration and prevent restored historical information from being republished improperly.

A deletion ledger or restricted tombstone record may help, but that mechanism has its own data-minimization and protection requirements.

The principle is straightforward.

**Restoring an old backup should not silently reverse newer privacy decisions.**

## 9. The Practical Mental Model

We now have two related problems.

Correcting an incorrect business fact.

Removing information that should no longer be retained or used.

Both require more than modifying one row.

Both involve identifying the authoritative state, tracking where copies exist, coordinating changes, recording evidence, and verifying the outcome.

Both can be undone unintentionally by background processes or old data.

And both require careful limits on who may perform the operation.

### A tiny comprehension check

An engineer changes a booking to confirmed, and Redis still reports pending. Does that automatically mean the PostgreSQL repair failed?

No. The cache may still hold a stale representation.

The same repair is overwritten by a scheduled job. What must the team investigate?

The authority and ordering of the data that the scheduled job uses.

A customer's account is marked `deleted_at = now()`. Has the company necessarily erased the customer's personal data?

No. Soft deletion can leave the information stored across several systems.

*The intuition pass ends here.*

---

# Part II — Deep Dive

## 10. Production Data Repairs Are Controlled Mutations

In ordinary application development, domain operations are performed through established code paths.

An API validates the request.

It checks authorization.

It enforces business rules.

It updates the database.

It records relevant events.

It returns a result.

A manual production repair can bypass much of that logic.

That's why a direct database update deserves more care than the simplicity of its SQL syntax suggests.

### 10.1 The repair's fundamental contract

Every repair should establish four things.

**Evidence:** Why do we believe the current state is incorrect?

**Scope:** Which exact records are affected?

**Preconditions:** What must remain true when the correction executes?

**Postconditions:** What must be true after the correction and its downstream effects finish?

This makes the repair reviewable and testable.

### 10.2 A repair is not a migration

A schema migration changes the structure or constraints of data.

A production repair corrects particular business records or a defined population of incorrect data.

The operations can overlap.

For example, a bug may require a schema correction followed by a backfill.

But a one-off booking repair shouldn't automatically become an undocumented schema migration.

### 10.3 Prefer normal domain operations where possible

If a safe, authorized business operation already exists, it may be preferable to executing custom SQL.

The normal path may enforce invariants and produce the required downstream events.

But the normal path may also be responsible for the bug.

Or the current invalid state may be impossible to process through ordinary application logic.

The decision should be deliberate.

A privileged repair tool is justified when it solves a real operational need with better controls than ad hoc database access.

## 11. Establish the Source of Truth

Return to booking 482.

The database says pending.

The external supplier says confirmed.

Which one is authoritative?

The answer requires understanding the business workflow.

Perhaps the supplier's confirmation is definitive evidence that the accommodation was reserved.

Perhaps a pending state means payment capture is incomplete.

Perhaps the supplier confirmed the stay but Mercury hasn't fulfilled an additional business condition.

There may not be one universal source of truth for every field.

### 11.1 Authority can be field-specific

The supplier may be authoritative for hotel confirmation.

Mercury may be authoritative for the customer's internal booking workflow.

The payment provider may be authoritative for the payment's actual capture state.

An analytics database may be authoritative for none of those operational facts.

The repair must identify which underlying reality it is correcting.

### 11.2 Don't treat every replica as a vote

Suppose PostgreSQL says confirmed while Redis, Elasticsearch, and the warehouse all say pending.

That doesn't mean three systems outvote one.

Those three systems may all contain copies derived from an earlier PostgreSQL state.

Data authority is not a popularity contest.

### 11.3 Record evidence provenance

If a supplier confirmation supports the repair, preserve a reference to the relevant supplier operation or verified response.

Don't invent proof simply because a customer says the booking should be confirmed.

Support information is valuable evidence, but the corresponding authoritative systems may need investigation.

## 12. Find the Cause Before Applying the Correction

A production value usually becomes incorrect through some process.

Possibilities include:

A failed integration.

An out-of-order event.

A concurrent update.

An application bug.

An incomplete migration.

A stale reconciliation feed.

A manual administrative action.

A delayed retry.

Correcting the symptom without understanding the cause invites recurrence.

### 12.1 The reconciliation overwrite

Suppose the current booking has revision 6 and status confirmed.

A scheduled reconciler retrieves supplier information representing revision 5.

If it blindly overwrites the booking, the status moves backward.

The problem is not merely stale data.

It is the absence of a suitable ordering or authority rule.

### 12.2 Version-aware updates

A controlled synchronization process can compare incoming and current revisions when those revisions have meaningful ordering semantics.

An older revision may be rejected.

But beware of a subtle assumption.

Two independently generated version counters are not automatically comparable.

A supplier revision number and Mercury's internal row-version number may describe different histories.

A reliable design needs an explicit mapping, source sequence, or authority policy.

### 12.3 Repair the mechanism too

The immediate booking repair may restore customer service.

The durable fix may involve correcting event ordering, reconciliation conditions, or source-state interpretation.

These are related but separate changes.

## 13. The Dry Run

Before changing production, determine which records match the repair conditions.

A dry run should identify the intended target population and expected effects.

For a one-record correction, it should confirm exactly one qualifying record.

For a large repair, it should identify the complete target set, counts by category, and potential downstream consequences.

### 13.1 Count alone isn't enough

A script expecting to update one thousand rows might find exactly one thousand.

That doesn't prove they're the intended rows.

The filters may be wrong in a way that happens to return the expected count.

A strong dry run validates representative identities, boundaries, and expected state.

### 13.2 Match the production query

An especially dangerous pattern is reviewing one query and executing another.

For example, the dry run filters by tenant and status.

The actual update omits the tenant condition.

The review provides false confidence.

Ideally, the repair tool derives the preview and execution from one defined selection and precondition model.

### 13.3 Preview the consequences

If the correction affects cached or indexed representations, the plan should identify the expected downstream updates.

If it affects an audit or financial record, appropriate owners should review the consequences.

The dry run should answer more than "how many rows?"

It should answer "what will this operation mean?"

## 14. Guarded Updates and Optimistic Concurrency

A production repair should normally include explicit state preconditions.

Consider a booking that is pending at revision 5.

The repair aims to move it to confirmed at revision 6.

A guarded update checks the booking identity, tenant, current status, and version before changing it.

This protects against the state changing between investigation and execution.

### 14.1 Why the row count matters

PostgreSQL's `UPDATE` reports the number of rows affected.

It also supports `RETURNING` to expose the resulting values.

For a targeted repair, the tool can verify that exactly the expected record changed.

A zero-row result can mean the state no longer matches.

That should usually trigger investigation rather than automatic relaxation of the filters.

### 14.2 Don't overinterpret affected-row counts

PostgreSQL may count matched rows even when a value is updated to the same value.

Triggers can also affect update behavior.

The repair should define the expected precondition and resulting state explicitly rather than treating a successful SQL command as complete proof of correctness.

### 14.3 Transaction boundaries

If the repair updates several related records in one database, an appropriate transaction may preserve their joint consistency.

But it doesn't automatically update Redis or an external supplier system.

The database transaction boundary is real.

Other systems remain separate.

## 15. Repair Plans Should Be Immutable Decisions

Imagine an engineer reviews a repair against booking version 5.

They approve the intended change.

An hour later, the script executes against version 7.

Should the approval still apply?

Not automatically.

The reviewed assumptions may no longer hold.

A robust tool can bind the approved plan to the target identities, expected versions, intended corrections, and relevant evidence.

If the execution context differs, the plan should be reconsidered.

### 15.1 Operator identity

A production repair should be attributable to an authenticated actor or controlled automation identity.

The actor should have permission for the particular operation.

A generic shared database password makes accountability much harder.

### 15.2 Approval

High-risk repairs may require independent approval.

The approval should describe the intended business effect and relevant risk.

For low-risk operations, automation and predefined policies may be sufficient.

The appropriate control is proportional to impact.

### 15.3 Break-glass access

Emergency access can be necessary during incidents.

It should be time-bounded where possible, monitored, attributable, and reviewed afterward.

Break-glass access isn't an excuse to erase the audit trail.

## 16. The Outbox and the Propagation Problem

Suppose the booking database update commits successfully.

Redis and Elasticsearch still contain the old value.

How should the repair propagate?

One option is an application operation that updates the source and emits a durable change notification.

The transactional outbox pattern can help when source data and event obligations live in the same transactional database.

The transaction writes the corrected booking and an outbox record together.

A separate publisher processes the outbox.

### 16.1 Why not update everything in the SQL script?

Directly connecting the repair script to Redis, Elasticsearch, and the warehouse can produce a fragile series of side effects.

What if the database update commits but the Redis operation fails?

What if the search update succeeds but the process crashes before recording that fact?

A durable propagation workflow makes the recovery obligations explicit.

### 16.2 Outbox delivery can repeat

The publisher may deliver an event more than once.

Consumers should be safe under repeated delivery.

For a projection that stores the latest source revision, a consumer can avoid applying stale updates.

### 16.3 Ordering is essential

Imagine revision 6 says confirmed.

Revision 5 says pending.

If the event for revision 5 arrives after revision 6, a naive consumer may overwrite the correct state.

A version-aware projection can reject the older update when both revisions belong to the same coherent ordering scheme.

### 16.4 Invalidation versus update

A cache may be invalidated and later repopulated from the authoritative database.

A search index may require an explicit document update or reindexing operation.

An analytics system may need a correction event or a recomputation of historical facts.

These aren't identical synchronization mechanisms.

## 17. Why Cache Invalidation Can Still Fail

Suppose the repair commits at noon.

The application invalidates the Redis entry.

A concurrent request had already begun reading the old database state.

That request completes later and repopulates Redis with a stale value.

The cache now holds incorrect information despite the invalidation.

This is a cache race.

### 17.1 Version-aware cache values

A cached record can carry a source revision.

The application can refuse to replace a newer cached representation with an older one, if the cache-update mechanism enforces the comparison safely.

### 17.2 Read-through freshness

Some systems invalidate caches and rely on subsequent reads to populate them.

Others proactively update the cached representation.

The correct strategy depends on how much staleness the business can tolerate.

### 17.3 Critical facts deserve stronger boundaries

A stale hotel description may be inconvenient.

A stale reservation-confirmation status can mislead a customer into believing they have no room.

Freshness requirements should reflect business impact.

## 18. Search and Analytics Require Different Repairs

An Elasticsearch index may contain a derived representation of booking data.

If the authoritative booking changes, the indexed document should eventually reflect the new state.

The system needs a way to detect lag and failed updates.

### 18.1 Search indexes are not automatically authoritative

A search result may be stale while the booking database is correct.

Customer-facing actions should generally validate important current state against the authoritative source.

### 18.2 Analytical data may be historical

Suppose yesterday's report counted the booking as pending.

Today, we discover it was actually confirmed yesterday.

Should the analytics system modify history?

Perhaps.

But the answer depends on what the report measures.

If it represents the best current understanding of yesterday's booking status, a correction is appropriate.

If it records what the application believed at the time, that historical observation may need to remain distinguishable.

### 18.3 Corrections need semantics

An analytical correction can be expressed as a new event, a recalculated aggregate, or a revised derived table.

Blindly overwriting every historical record may destroy useful audit information.

The data contract must distinguish operational truth from historical observations.

## 19. A Repair Can Be Reversed by a Scheduled Job

Return to our opening incident.

The engineer changes booking 482 to confirmed.

At midnight, a synchronization task retrieves an old supplier record and changes it back to pending.

This is a classic ownership failure.

### 19.1 Find every writer

Before repairing an important field, identify which services and scheduled processes can write it.

The API isn't necessarily the only writer.

Background workers, administrative tools, data imports, and reconciliation jobs may modify the same record.

### 19.2 Don't disable reconciliation permanently

A broken reconciler may need temporary containment.

But simply disabling it forever can create a different problem: missing updates accumulate.

The correct response is to repair the authority and ordering logic, then resume reconciliation safely.

### 19.3 Use a repair generation when appropriate

A controlled correction can establish a new authoritative revision.

Incoming older information should not overwrite that revision merely because it arrives later.

A real implementation must ensure its versions represent comparable business history.

### 19.4 Reconciliation is necessary even after the fix

The corrected synchronization logic should be tested against real historical cases.

It should also identify records that were already corrupted by the old behavior.

Fixing the code doesn't automatically repair every affected record.

## 20. Repair at Scale: One Row Versus One Million

A single booking correction can be tightly scoped.

What happens when a production bug affected two million reservations?

Now the task resembles the bulk jobs from SE325-L02.

The repair needs stable target selection, bounded transactions, durable progress, cancellation, and resource budgets.

### 20.1 Don't lock the world

A huge transaction may hold resources for too long and create contention with interactive traffic.

Breaking the repair into controlled batches can reduce operational risk.

### 20.2 Preserve target identity

Each chunk should have a stable identity.

A retry must not apply the correction twice if the operation isn't naturally idempotent.

### 20.3 Record progress

The system should report how many records were examined, qualified, corrected, skipped due to changed preconditions, and left requiring investigation.

### 20.4 Limit concurrency

Production repair jobs can compete with ordinary application traffic.

Increasing worker count isn't automatically beneficial.

The objective is safe recovery, not simply finishing the SQL as quickly as possible.

### 20.5 Establish completion criteria

A repair is complete when the intended business invariants hold and required derived systems have converged, or when remaining exceptions are explicitly identified and owned.

An empty queue alone isn't sufficient proof.

## 21. Data Lifecycle Begins Before Deletion

Now shift from correcting data to managing its retention.

A well-designed application should know why it collects information and how long it needs to keep it.

A customer email address may support account access and booking notifications.

A financial transaction record may support accounting and legal obligations.

A temporary upload may be needed only during processing.

A diagnostic log may be useful for a limited operational period.

These have different purposes and retention needs.

### 21.1 Data classification

An organization should distinguish ordinary application data, personal information, sensitive information, financial records, security evidence, and temporary processing artifacts.

This doesn't mean every application needs a complicated enterprise classification engine.

It means developers should recognize that retention requirements depend on the data's purpose and risk.

### 21.2 Data minimization

A simple way to reduce erasure complexity is to avoid collecting or copying unnecessary personal information.

If a log only needs a request identifier, don't automatically include the customer's email and full request body.

If a metrics system needs a count, it may not need customer identity.

Every unnecessary copy becomes another data-lifecycle obligation.

## 22. The Right to Erasure Is Not an Unconditional Delete Command

In the European context, GDPR Article 17 establishes a right to erasure under specified circumstances.

The right is important, but not absolute.

For example, processing may remain necessary to comply with a legal obligation or establish, exercise, or defend legal claims.

A hotel-booking company may have legitimate requirements to retain certain financial records even after an account is closed.

### 22.1 Developers shouldn't invent retention law

The application developer shouldn't decide independently that every invoice must be kept for a particular number of years.

Applicable requirements depend on jurisdiction, data category, purpose, and legal obligations.

Those decisions belong in an agreed retention and privacy policy with appropriate legal or compliance involvement.

### 22.2 Separate identity from required business records

A booking may need to remain in accounting records without retaining every personal detail previously associated with the customer's account.

Where legally and technically appropriate, personal attributes may be removed or minimized while retaining the required business facts.

But pseudonymization isn't automatically equivalent to anonymization.

If a person remains identifiable through other information, the data can still be personal data.

### 22.3 Request handling is itself a workflow

A valid erasure request needs identity verification, scope assessment, applicable exception handling, execution, verification, and communication.

Under the GDPR, organizations generally must respond to individual-rights requests without undue delay and, in principle, within one month, subject to the regulation's rules.

The backend operation is only one part of that process.

## 23. The Data Erasure Map

Before implementing deletion, map where the information can exist.

Start with authoritative operational tables.

Then follow the data outward.

### 23.1 Related database records

Customer identity may appear in bookings, invoices, contact records, support cases, payment metadata, and audit records.

Foreign-key relationships may prevent a simple deletion.

Some data may need retention while other fields can be removed.

### 23.2 Caches

Redis may retain personal attributes.

Deleting the primary row doesn't necessarily invalidate every cache key.

The deletion workflow must know how to invalidate or expire relevant cached copies.

### 23.3 Search indexes

Search documents may contain names, email addresses, or other identifiers.

Those representations require appropriate deletion or redaction.

### 23.4 Analytical stores

Raw analytics events may contain identifiers.

Aggregated statistics may or may not remain personal data depending on whether individuals can reasonably be identified.

The workflow must distinguish the two.

### 23.5 Object storage

Invoices, identity documents, and uploaded files may reside in object storage.

Object keys and metadata can themselves contain personal information.

### 23.6 Logs and monitoring

Request payloads, URLs, traces, and exception reports may contain personal data.

Their retention and access policies matter.

### 23.7 External recipients

Email services, analytics vendors, support platforms, and other processors may hold copies.

Deletion may require coordinated downstream action under the relevant legal and contractual obligations.

### 23.8 Backups

Backups may retain historical copies for a defined period.

A recovery process needs to account for erasure obligations.

## 24. Soft Deletion, Hard Deletion, and Redaction

These are different operations.

### 24.1 Soft deletion

The record remains stored but is marked inactive or deleted.

This can support recovery and referential integrity.

It does not necessarily satisfy an erasure requirement.

### 24.2 Hard deletion

The record is removed from the live database's logical contents.

But other copies, logs, backups, or replicas may remain.

Physical storage reclamation may occur later.

### 24.3 Redaction

Selected attributes are removed or replaced.

For example, a booking may retain a non-personal accounting reference while removing an email address no longer required.

Whether the remaining data is personal depends on identifiability and the wider context.

### 24.4 Anonymization

True anonymization aims to make an individual no longer identifiable.

Simply replacing a customer's email with an internal customer ID may be insufficient if that ID can still be linked to the individual.

### 24.5 Cryptographic erasure

Some architectures encrypt data with appropriately scoped keys and can render encrypted content inaccessible by destroying relevant keys.

This can be useful but requires careful key isolation and lifecycle design.

Destroying one key doesn't prove erasure if plaintext, other keys, copies, or decrypted representations remain available elsewhere.

## 25. Tombstones and the Resurrection Problem

Suppose Mercury deletes a customer's profile.

The system later replays an old customer-created event.

A naive consumer recreates the profile.

Or a restored backup contains the original record.

The deletion has been undone.

### 25.1 A deletion tombstone

A tombstone is a record indicating that an entity was deleted or that older representations must not be recreated.

The application can use tombstones to reject stale updates.

### 25.2 Tombstones are not free

A tombstone may retain an identifier associated with the person.

That can itself constitute personal data.

The design should retain only what is necessary for a legitimate purpose, protect it appropriately, and define its own retention policy.

### 25.3 Deletion generation

An event stream can carry versions or generations.

If a deletion occurs at revision 7, a delayed update from revision 5 should not recreate the deleted personal details.

The same ordering principles used in ordinary data repair apply to erasure.

### 25.4 Restoration from backup

A restored database might predate the deletion.

Before that restored data becomes operational, the recovery process should account for erasure obligations recorded after the backup.

For example, a separately protected erasure ledger can be replayed against an isolated restoration before it is promoted.

That requires careful security and continuity planning.

## 26. Backups Are a Special Case

Backups exist precisely to preserve older data.

That creates tension with deletion.

An organization's ability to remove individual records from immutable or compressed backups may be limited.

But that doesn't mean backup copies can be ignored.

### 26.1 Retention policies

Backups should have defined retention periods and access controls.

Personal data shouldn't remain indefinitely merely because nobody implemented expiration.

### 26.2 Beyond-use controls

Depending on applicable requirements and technical circumstances, older backup copies may need to remain isolated, unavailable for ordinary processing, and subject to an established deletion schedule.

Regulatory guidance emphasizes that backup handling must be considered as part of erasure, not excluded from the workflow by default.

### 26.3 Restore safeguards

If a backup is restored, previously completed erasure obligations must not be silently reversed.

A controlled restoration process can identify and reapply relevant post-backup privacy operations before restored data becomes accessible.

### 26.4 No universal shortcut

It would be incorrect to promise that every historical backup can always be physically rewritten instantly.

It would also be incorrect to treat backup retention as an unlimited exemption from erasure obligations.

The organization needs an appropriate, documented, legally reviewed and technically enforceable approach.

## 27. Versioned Object Storage Has Its Own Deletion Trap

Suppose a customer's document is stored in a versioned S3 bucket.

An engineer issues an ordinary delete request without a version ID.

The object disappears from ordinary retrieval.

Has its content necessarily been permanently deleted?

No.

For an S3 bucket with versioning enabled, an ordinary delete generally creates a delete marker, while older object versions may remain stored.

Permanently removing versions requires the appropriate version-aware deletion or lifecycle operations.

Retention controls and legal holds may also restrict deletion.

### 27.1 Hidden isn't gone

This is similar to soft deletion in a database.

The current view no longer exposes the object.

But historical content may remain.

### 27.2 Object inventory matters

A deletion workflow should know which bucket, key, and versions contain the relevant information.

The application's storage abstraction should not assume one generic `deleteObject` call satisfies every retention or erasure contract.

### 27.3 Separate application policy from storage configuration

A customer request should enter an authorized application privacy workflow.

That workflow decides what the organization must do.

Storage-level operations then implement the relevant parts.

The storage API shouldn't determine the legal retention policy.

## 28. Auditability and Privacy Can Conflict

A repair needs evidence.

An erasure workflow may require personal data to be removed.

What happens when audit logs contain the personal data that must be erased?

This is an architectural tension.

### 28.1 Prefer metadata over raw payloads

An audit record might identify:

The type of operation.

A restricted internal subject reference.

The authorized actor.

A case or ticket reference.

The previous and resulting versions.

The operation time.

The outcome.

It may not need the full customer name, email address, identity document, or payment details.

### 28.2 Audit records need their own policy

Some audit information may have legitimate retention requirements.

Other diagnostic detail may not.

An audit log should not be treated as an automatically permanent exception to every erasure or minimization requirement.

### 28.3 Tamper resistance

A useful audit system should make unauthorized modification detectable or difficult.

For high-risk operations, append-only storage, external audit sinks, or other tamper-evident mechanisms may be appropriate.

But operational auditability and legal retention are separate questions.

### 28.4 Don't publish sensitive audit evidence

A support ticket or incident report shouldn't automatically contain full raw database rows.

Summaries, references, and appropriately restricted evidence are often safer.

## 29. The Data Repair Workflow

Let's assemble a disciplined procedure for correcting booking 482.

### Step 1 — Establish the incident

What customer-visible or business problem exists?

What is the intended correct state?

### Step 2 — Identify the authoritative evidence

Which supplier or payment records establish what actually happened?

Are those records current and trustworthy?

### Step 3 — Map the affected systems

Which source record, cached values, search documents, analytics records, and scheduled writers are relevant?

### Step 4 — Establish the target set

Which exact rows qualify for correction?

What are their current versions?

### Step 5 — Review the dry run

Verify the expected row count and identities.

Consider the downstream consequences.

### Step 6 — Obtain appropriate authorization

Use the organization's repair approval and operator access policy.

### Step 7 — Execute guarded changes

Apply a conditional update within the appropriate transaction.

Record the resulting version and audit metadata.

Create a durable downstream synchronization obligation where needed.

### Step 8 — Verify the primary invariant

Confirm that the authoritative booking now reflects the verified business reality.

### Step 9 — Verify derived systems

Check cache, search, analytics, and relevant external integrations according to their consistency contracts.

### Step 10 — Verify durability

Ensure the correction survives the next reconciliation cycle.

If the old mechanism can still overwrite it, the repair isn't complete.

## 30. The Erasure Workflow

Now consider the customer's deletion request.

### Step 1 — Authenticate the request

Verify the individual's identity according to an appropriate process.

Avoid disclosing whether unrelated accounts or records exist.

### Step 2 — Determine scope and lawful retention

Identify which information should be erased, which may need retention, and why.

This is a policy and legal decision as well as a technical one.

### Step 3 — Discover the data footprint

Map live databases, derived systems, object stores, external recipients, logs, and backups.

### Step 4 — Prevent re-creation

Ensure stale synchronization or replay processes cannot repopulate information that has been erased.

### Step 5 — Apply controlled live changes

Remove or appropriately redact relevant personal attributes from live systems.

Keep required business records only under the applicable retention justification.

### Step 6 — Propagate and verify

Update caches, indexes, analytics, and external systems according to the approved scope.

### Step 7 — Address historical storage

Apply backup retention, versioned-object, and restoration policies.

### Step 8 — Record a minimal outcome

Maintain sufficient evidence that the workflow was handled without unnecessarily retaining the erased personal details.

### Step 9 — Communicate appropriately

The organization should accurately describe the status and scope of the request, including relevant limitations or exceptions.

Do not claim universal physical erasure if known retained copies remain subject to an approved lifecycle.

## 31. The Difference Between Repair and Reconciliation

A repair corrects identified incorrect state.

Reconciliation checks whether related systems agree with authoritative expectations.

These operations are complementary.

### 31.1 Repair without reconciliation

The source changes, but derived systems remain stale.

### 31.2 Reconciliation without correct authority

A job faithfully copies incorrect old information back over the repair.

### 31.3 The complete solution

Establish the authoritative business outcome.

Correct the source.

Repair the writer or ordering mechanism that caused the inconsistency.

Propagate the new state.

Verify convergence.

And monitor for recurrence.

This is why the repair workflow must understand the surrounding architecture.

## 32. What Should Be Monitored?

An application with production repair and erasure capabilities needs operational evidence.

Useful repair metrics include:

Pending repair requests.

Approved but unexecuted repairs.

Precondition failures.

Unexpected affected-row counts.

Downstream synchronization lag.

Reconciliation disagreements.

Repeated corrections to the same business records.

Useful privacy-workflow metrics include:

Requests awaiting assessment.

Requests approaching applicable response deadlines.

Incomplete live-system actions.

Failed downstream deletion tasks.

Records restored from historical sources.

Outstanding backup lifecycle obligations.

### 32.1 Don't expose personal data in metrics

Metrics should ordinarily aggregate operational counts and states.

They shouldn't embed raw customer identifiers or sensitive values in high-cardinality labels.

### 32.2 Alert on stuck obligations

A failed cache invalidation may be transient.

A deletion workflow that remains incomplete beyond its allowed operational window needs attention.

An outbox that stops progressing can prevent both repairs and deletions from converging.

Monitoring should reflect the seriousness of the outstanding obligation.

## 33. The Small Company and the Large Company

In a small company, a developer may perform production repairs directly because there is no specialized operations team.

That makes safe tooling and review even more important.

A simple script with guarded updates, a dry run, a ticket reference, and a clear verification procedure may be a substantial improvement over an improvised SQL console session.

In a larger company, database administrators, support engineers, data engineers, privacy specialists, security engineers, and release managers may participate.

The process may involve more formal authorization.

But specialization shouldn't obscure the original business fact.

Someone must still understand why the booking is incorrect and what a valid correction means.

### 33.1 Don't overengineer routine repairs

Not every incorrect display label requires a multi-day approval process.

The right controls depend on risk.

### 33.2 Don't underengineer high-risk corrections

A repair touching payment records, customer authorization, or millions of rows can cause enormous damage.

Convenience is not a sufficient reason to bypass appropriate protections.

## 34. The Senior Engineer's Judgment

A senior engineer understands that production data is not merely a collection of rows.

It represents real-world commitments, customer actions, financial outcomes, and operational history.

They recognize that a database update can be locally correct while system-wide behavior remains wrong.

They know that every derived copy needs an ownership and consistency policy.

They understand that repairs should be guarded, attributable, and verifiable.

And they don't treat personal-data deletion as an ordinary implementation detail.

The most important engineering question isn't:

"How do I change this value?"

It is:

**"What real-world fact should this value represent, which systems depend on it, and how will I prove that the intended correction remains true?"**

---

# The Oral Examination

Answer aloud before reading the solutions.

## Question 1 — The One-Line Fix

Support requests an SQL update changing a booking from pending to confirmed.

What evidence and preconditions should you establish before executing it?

## Question 2 — The Reverting Repair

The booking becomes confirmed after the repair, then returns to pending overnight.

What mechanisms could explain the reversion?

What would you investigate?

## Question 3 — The Safe Update

Why is a conditional update checking the existing status and row version safer than an unconditional update by booking ID?

## Question 4 — The Derived Copies

The PostgreSQL row is correct, but Redis and Elasticsearch are stale.

What does that establish?

How should the correction propagate?

## Question 5 — The Outbox

Why might the repair transaction write an outbox record?

Does the outbox guarantee exactly-once delivery?

## Question 6 — The Analytics Record

Yesterday's analytical report counted the booking as pending.

Today you learn it was actually confirmed yesterday.

Should the historical report be changed automatically?

What determines the answer?

## Question 7 — The Soft Delete

A user requests erasure, and the application sets `deleted_at`.

Is that necessarily enough?

## Question 8 — Versioned Object Storage

A customer document is stored in a versioned S3 bucket.

An ordinary delete operation makes it disappear from normal retrieval.

Does that prove permanent erasure?

## Question 9 — The Backup Restore

The live database is redacted after a valid erasure request.

A week-old backup is restored.

How should the system prevent personal data from reappearing in ordinary use?

## Question 10 — Audit Versus Privacy

A correction requires an audit trail, but the customer also wants unnecessary personal information removed.

How can the system preserve useful auditability without retaining excessive sensitive data?

## Question 11 — The Million-Row Repair

A defect affected two million records.

What operational controls distinguish a safe bulk repair from an enormous uncontrolled SQL update?

## Question 12 — The Senior Design

Design a production repair and erasure system for a multi-tenant SaaS application with PostgreSQL, Redis, Elasticsearch, analytical data, object storage, and backups.

Explain authority, permissions, transactions, retries, verification, and retention.

---

# Solutions and Discussion

## Solution 1 — Establish Truth and Scope

Verify the customer, booking, tenant, supplier confirmation, payment implications, expected status, and current version.

Confirm that the requested state reflects actual business reality rather than merely a support expectation.

## Solution 2 — Find the Writer

A scheduled reconciler, late event, administrative process, or stale import may be overwriting the correction.

Inspect the write history, authority rules, event versions, and scheduled jobs.

Fix the mechanism rather than repeating the same manual correction indefinitely.

## Solution 3 — Guard Against Changed Assumptions

A conditional update prevents the repair from silently overwriting a record that has changed since investigation.

An unexpected affected-row count should trigger a fresh review.

## Solution 4 — Separate Source from Projection

The source may be correct while derived representations lag.

Use an appropriate invalidation, update, or replay process.

Verify that stale events cannot overwrite newer projection state.

## Solution 5 — Durable Propagation

An outbox records a downstream synchronization obligation in the same transaction as the primary repair.

Delivery can still repeat, so consumers need idempotency and ordering protection.

## Solution 6 — Define Analytical Meaning

If the report reflects the best current interpretation of historical business events, correction may be appropriate.

If it records what the system observed at the time, preserving the original observation may also be meaningful.

The data contract determines the proper approach.

## Solution 7 — Soft Deletion Isn't Automatically Erasure

The data may still exist in live tables, caches, logs, derived stores, and backups.

A valid erasure request requires scope assessment and execution under applicable legal obligations and exceptions.

## Solution 8 — Historical Versions

No.

A versioned S3 delete can create a delete marker while retaining noncurrent versions.

Permanent removal requires appropriate handling of object versions, retention rules, and legal holds.

## Solution 9 — Restore-Aware Erasure

Keep an appropriately protected record of post-backup erasure obligations and apply them to an isolated restored environment before promotion.

Backups also need defined retention and access policies.

## Solution 10 — Minimal Audit Evidence

Record operation type, approved actor, ticket, subject reference, versions, and outcome.

Avoid unnecessary raw personal-data payloads.

Audit retention needs its own policy and safeguards.

## Solution 11 — Safe Bulk Repair

Use immutable target selection, guarded batches, approvals, durable progress, resource budgets, cancellation, audit, and independent verification.

Avoid long-running transactions and uncontrolled repeated effects.

## Solution 12 — Full Lifecycle

Maintain a clear source of truth and system inventory.

Use governed repairs, durable propagation, version-aware reconciliation, and explicit data-lifecycle policies.

Verify both live-system convergence and the handling of historical storage and external recipients.

---

# The Mental Model Worth Keeping

Production data represents business reality, not merely database contents.

A repair is safe only when it corrects the right fact, under the right preconditions, and remains correct after other systems run.

An erasure workflow is complete only according to its defined legal and technical scope, not simply because one account row disappeared.

The durable questions are:

**What is the authoritative fact?**

**Why did it become incorrect?**

**Which exact records may change?**

**What can overwrite the correction later?**

**Where else does the information exist?**

**What evidence proves the required lifecycle operation succeeded?**

A good repair doesn't merely change state.

It restores and verifies the system's intended relationship with reality.

---

# Next Lecture — SE325-L05: Surviving Third-Party Integrations

We've discovered how a stale supplier feed can overwrite a perfectly valid production repair.

But what happens when the supplier is an external company whose API we don't control?

Tokens expire.

Pagination changes.

Rate limits appear during backfills.

Webhooks arrive twice, out of order, or not at all.

A vendor silently changes a date format, and the synchronization job continues reporting success while processing incorrect data.

SE325-L05 will investigate how to operate third-party integrations over years rather than merely getting the first API call to work.

*The spoken lecture ends here. The following practical investigation uses an isolated SQLite database with fictional data. Do not execute its deliberately unsafe example against a real database.*

---

# Optional Practical Lab — The Repair That Was Overwritten

## Lab Contract

This lab reproduces several common production-data lifecycle failures using Python's standard library and SQLite.

It requires no PostgreSQL server, cloud account, or external services.

The simulator includes:

- One authoritative booking record.
- A stale supplier synchronization feed.
- A verified supplier-confirmation record.
- Three derived representations.
- A deliberately unsafe manual update.
- A guarded, audited repair.
- A transactional outbox.
- A simple projection-reconciliation worker.
- A simulated personal-data redaction.
- A historical backup snapshot.

The lab uses a fictional email address and synthetic booking information.

**It is a teaching simulator, not a production repair tool or a GDPR compliance implementation.**

In particular, approval names are command-line labels, not authenticated identities. Audit rows are ordinary SQLite records rather than tamper-evident logs. Derived stores are represented by SQLite tables rather than real Redis, Elasticsearch, or analytical systems.

The verification command intentionally reports that retained backup data remains after live redaction. This is a lifecycle obligation, not a successful end-to-end erasure claim.

## Lab 1 — Create the Workspace

Create a dedicated directory named `se325-repair-lab`.

Save the following Python script as `studio.py`.

The simulator creates `se325_repair_lab.sqlite3` in the current directory. Initialization refuses to overwrite an existing database; only run it in a disposable lab directory.

### The simulator

```python id="se32504py"
import argparse
import hashlib
import sqlite3
from pathlib import Path


DB = Path("se325_repair_lab.sqlite3")


def connection():
    if not DB.exists():
        raise SystemExit("Run init first")

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init():
    if DB.exists():
        raise SystemExit(
            "Database exists; reset manually "
            "in your disposable lab"
        )

    with sqlite3.connect(DB) as con:
        con.executescript("""
          CREATE TABLE bookings(
            id INTEGER PRIMARY KEY,
            tenant TEXT NOT NULL,
            guest_id INTEGER NOT NULL,
            email TEXT,
            status TEXT NOT NULL,
            version INTEGER NOT NULL
          );

          CREATE TABLE source_feed(
            booking_id INTEGER PRIMARY KEY,
            status TEXT,
            version INTEGER
          );

          CREATE TABLE evidence(
            booking_id INTEGER PRIMARY KEY,
            status TEXT,
            version INTEGER,
            reference TEXT
          );

          CREATE TABLE cache(
            booking_id INTEGER PRIMARY KEY,
            email TEXT,
            status TEXT,
            version INTEGER
          );

          CREATE TABLE search_index(
            booking_id INTEGER PRIMARY KEY,
            email TEXT,
            status TEXT,
            version INTEGER
          );

          CREATE TABLE analytics(
            booking_id INTEGER PRIMARY KEY,
            email TEXT,
            status TEXT,
            version INTEGER
          );

          CREATE TABLE outbox(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER,
            kind TEXT,
            version INTEGER,
            processed INTEGER NOT NULL DEFAULT 0
          );

          CREATE TABLE audit(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER,
            kind TEXT,
            actor TEXT,
            ticket TEXT,
            old_version INTEGER,
            new_version INTEGER
          );

          CREATE TABLE tombstones(
            guest_id INTEGER PRIMARY KEY
          );

          CREATE TABLE backup_snapshot(
            booking_id INTEGER PRIMARY KEY,
            guest_id INTEGER,
            email TEXT
          );
        """)

        con.execute(
            "INSERT INTO bookings VALUES "
            "(42,'alpha',7,'guest@example.test','PENDING',5)"
        )

        con.execute(
            "INSERT INTO source_feed VALUES "
            "(42,'PENDING',5)"
        )

        con.execute(
            "INSERT INTO evidence VALUES "
            "(42,'CONFIRMED',6,"
            "'verified-supplier-confirmation')"
        )

        for table in (
            "cache",
            "search_index",
            "analytics",
        ):
            con.execute(
                f"INSERT INTO {table} VALUES "
                "(42,'guest@example.test','PENDING',5)"
            )

        con.execute(
            "INSERT INTO backup_snapshot VALUES "
            "(42,7,'guest@example.test')"
        )

    print("Created disposable lab with fictional data")


def view():
    with connection() as c:
        for table in (
            "bookings",
            "source_feed",
            "evidence",
            "cache",
            "search_index",
            "analytics",
            "tombstones",
        ):
            rows = [
                dict(r)
                for r in c.execute(
                    f"SELECT * FROM {table}"
                )
            ]

            print(table, rows)

        print(
            "outbox",
            [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM outbox"
                )
            ],
        )

        print(
            "audit",
            [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM audit"
                )
            ],
        )

        backup_count = c.execute(
            "SELECT COUNT(*) "
            "FROM backup_snapshot "
            "WHERE email IS NOT NULL"
        ).fetchone()[0]

        print(
            "backup residual rows",
            backup_count,
        )


def unsafe():
    with connection() as c:
        c.execute(
            "UPDATE bookings "
            "SET status='CONFIRMED' "
            "WHERE id=42"
        )

    print(
        "Manual update applied without "
        "revision, audit or outbox "
        "(deliberately defective)"
    )


def replay():
    with connection() as c:
        booking = c.execute(
            "SELECT status,version "
            "FROM bookings WHERE id=42"
        ).fetchone()

        feed = c.execute(
            "SELECT status,version "
            "FROM source_feed "
            "WHERE booking_id=42"
        ).fetchone()

        if feed["version"] >= booking["version"]:
            c.execute(
                "UPDATE bookings "
                "SET status=?, version=? "
                "WHERE id=42",
                (
                    feed["status"],
                    feed["version"],
                ),
            )

            print(
                "Legacy reconciler overwrote "
                "state from old feed"
            )

        else:
            print(
                "Legacy feed ignored: "
                "older than current revision"
            )


def plan():
    with connection() as c:
        booking = c.execute(
            "SELECT id,tenant,status,version "
            "FROM bookings WHERE id=42"
        ).fetchone()

        evidence = c.execute(
            "SELECT status,version,reference "
            "FROM evidence WHERE booking_id=42"
        ).fetchone()

        if not booking or not evidence:
            raise SystemExit(
                "No supported target or evidence"
            )

        fingerprint_input = (
            f"{booking['id']}:"
            f"{booking['tenant']}:"
            f"{booking['status']}:"
            f"{booking['version']}:"
            f"{evidence['status']}:"
            f"{evidence['version']}"
        )

        fingerprint = hashlib.sha256(
            fingerprint_input.encode()
        ).hexdigest()[:12]

        print(
            dict(booking),
            "verified evidence:",
            dict(evidence),
            "plan fingerprint:",
            fingerprint,
        )

        print(
            "Expected row count: 1; "
            "do not apply if tenant, "
            "state or revision differs"
        )


def repair(actor, ticket):
    if not actor or not ticket:
        raise SystemExit(
            "Nonempty approved-by and ticket "
            "required (demo labels, "
            "not authentication)"
        )

    with connection() as c:
        booking = c.execute(
            "SELECT tenant,status,version "
            "FROM bookings WHERE id=42"
        ).fetchone()

        evidence = c.execute(
            "SELECT status,version "
            "FROM evidence WHERE booking_id=42"
        ).fetchone()

        if (
            booking["tenant"] != "alpha"
            or booking["status"] != "PENDING"
            or booking["version"] != 5
            or evidence["version"] != 6
            or evidence["status"] != "CONFIRMED"
        ):
            raise SystemExit(
                "Preconditions changed; "
                "abort and investigate"
            )

        cursor = c.execute(
            "UPDATE bookings "
            "SET status='CONFIRMED',version=6 "
            "WHERE id=42 "
            "AND tenant='alpha' "
            "AND status='PENDING' "
            "AND version=5"
        )

        if cursor.rowcount != 1:
            raise SystemExit(
                "Not exactly one target; rollback"
            )

        c.execute(
            "INSERT INTO audit"
            "(booking_id,kind,actor,ticket,"
            "old_version,new_version) "
            "VALUES(42,?,?,?,?,?)",
            (
                "REPAIR",
                actor,
                ticket,
                5,
                6,
            ),
        )

        c.execute(
            "INSERT INTO outbox"
            "(booking_id,kind,version) "
            "VALUES(42,'REPAIR',6)"
        )

    print(
        "Repair, audit and outbox "
        "committed together"
    )


def erase(actor, ticket):
    if not actor or not ticket:
        raise SystemExit(
            "Nonempty approved-by and ticket "
            "required (demo labels, "
            "not authentication)"
        )

    with connection() as c:
        booking = c.execute(
            "SELECT guest_id,version,email "
            "FROM bookings WHERE id=42"
        ).fetchone()

        if (
            booking is None
            or booking["guest_id"] != 7
        ):
            raise SystemExit(
                "Wrong subject; abort"
            )

        if booking["email"] is None:
            print(
                "Already redacted; no new effect"
            )
            return

        c.execute(
            "INSERT OR IGNORE "
            "INTO tombstones VALUES(7)"
        )

        cursor = c.execute(
            "UPDATE bookings "
            "SET email=NULL,version=version+1 "
            "WHERE id=42 "
            "AND guest_id=7 "
            "AND email IS NOT NULL"
        )

        if cursor.rowcount != 1:
            raise SystemExit(
                "Expected exactly one row"
            )

        new_version = booking["version"] + 1

        c.execute(
            "INSERT INTO audit"
            "(booking_id,kind,actor,ticket,"
            "old_version,new_version) "
            "VALUES(42,?,?,?,?,?)",
            (
                "REDACTION",
                actor,
                ticket,
                booking["version"],
                new_version,
            ),
        )

        c.execute(
            "INSERT INTO outbox"
            "(booking_id,kind,version) "
            "VALUES(42,?,?)",
            (
                "REDACTION",
                new_version,
            ),
        )

    print(
        "Live primary redacted; "
        "derived stores still require sync; "
        "backups remain"
    )


def sync():
    with connection() as c:
        jobs = c.execute(
            "SELECT * FROM outbox "
            "WHERE processed=0 ORDER BY id"
        ).fetchall()

        for job in jobs:
            booking = c.execute(
                "SELECT * FROM bookings WHERE id=?",
                (job["booking_id"],),
            ).fetchone()

            for table in (
                "cache",
                "search_index",
                "analytics",
            ):
                c.execute(
                    f"UPDATE {table} "
                    "SET email=?,status=?,version=? "
                    "WHERE booking_id=? "
                    "AND version <= ?",
                    (
                        booking["email"],
                        booking["status"],
                        booking["version"],
                        booking["id"],
                        booking["version"],
                    ),
                )

            c.execute(
                "UPDATE outbox "
                "SET processed=1 WHERE id=?",
                (job["id"],),
            )

    print(
        "Synchronized queued events "
        "from primary record"
    )


def verify():
    with connection() as c:
        booking = c.execute(
            "SELECT * FROM bookings WHERE id=42"
        ).fetchone()

        drift = []

        for table in (
            "cache",
            "search_index",
            "analytics",
        ):
            row = c.execute(
                f"SELECT * FROM {table} "
                "WHERE booking_id=42"
            ).fetchone()

            expected = (
                booking["email"],
                booking["status"],
                booking["version"],
            )

            actual = (
                row["email"],
                row["status"],
                row["version"],
            )

            if actual != expected:
                drift.append(table)

        pending = c.execute(
            "SELECT COUNT(*) FROM outbox "
            "WHERE processed=0"
        ).fetchone()[0]

        backup_count = c.execute(
            "SELECT COUNT(*) FROM backup_snapshot "
            "WHERE email IS NOT NULL"
        ).fetchone()[0]

        print(
            "Primary",
            {
                "status": booking["status"],
                "version": booking["version"],
                "pii_present":
                    booking["email"] is not None,
            },
        )

        print(
            "Derived drift:",
            drift,
            "pending outbox:",
            pending,
            "backup retained PII rows:",
            backup_count,
        )

        if booking["email"] is None:
            print(
                "Redaction is NOT complete "
                "across backups; apply approved "
                "retention and restore-"
                "suppression policy"
            )


def restored():
    with connection() as c:
        count = c.execute(
            "SELECT COUNT(*) "
            "FROM backup_snapshot "
            "WHERE email IS NOT NULL"
        ).fetchone()[0]

        tombstone = c.execute(
            "SELECT COUNT(*) "
            "FROM tombstones "
            "WHERE guest_id=7"
        ).fetchone()[0]

    print(
        "Isolated restore preview: "
        "historical PII records:",
        count,
    )

    print(
        "Erasure tombstone present "
        "in CURRENT system:",
        bool(tombstone),
    )

    print(
        "Do NOT reconnect historical records "
        "to production. Reapply erasure "
        "obligations before restore promotion."
    )


parser = argparse.ArgumentParser()

subs = parser.add_subparsers(
    dest="cmd",
    required=True,
)

for command in (
    "init",
    "view",
    "unsafe-fix",
    "replay-feed",
    "plan",
    "sync",
    "verify",
    "restore-preview",
):
    subs.add_parser(command)

for command in ("repair", "erase"):
    item = subs.add_parser(command)

    item.add_argument(
        "--approved-by",
        required=True,
    )

    item.add_argument(
        "--ticket",
        required=True,
    )

args = parser.parse_args()

if args.cmd == "init":
    init()
elif args.cmd == "view":
    view()
elif args.cmd == "unsafe-fix":
    unsafe()
elif args.cmd == "replay-feed":
    replay()
elif args.cmd == "plan":
    plan()
elif args.cmd == "repair":
    repair(args.approved_by, args.ticket)
elif args.cmd == "erase":
    erase(args.approved_by, args.ticket)
elif args.cmd == "sync":
    sync()
elif args.cmd == "verify":
    verify()
elif args.cmd == "restore-preview":
    restored()
```

## Lab 2 — Inspect the Incorrect Booking

Initialize the lab.

```bash id="se32504init"
python studio.py init
python studio.py view
```

The initial state contains one booking.

Booking 42 belongs to tenant Alpha.

Its status is `PENDING`, version 5.

The supplier synchronization feed also contains `PENDING`, version 5.

A separate verified-evidence record reports `CONFIRMED`, version 6.

The three derived stores contain the old pending representation.

### Before changing anything

Answer:

Which system is the intended source of operational booking state?

What evidence supports the correction?

Which process might overwrite an update?

What preconditions should a safe repair require?

## Lab 3 — Reproduce the Unsafe Fix

The following command is deliberately defective.

It updates the booking without advancing its revision, recording an audit entry, or creating a downstream synchronization obligation.

Run it only in the disposable lab.

```bash id="se32504unsafe"
python studio.py unsafe-fix
python studio.py view
```

The primary booking now appears confirmed.

But its version remains 5.

The derived stores still show pending.

### Your prediction

What happens when the old supplier feed is replayed?

Run:

```bash id="se32504replay1"
python studio.py replay-feed
python studio.py view
```

The booking should return to pending.

### Required explanation

Why didn't the SQL update permanently correct the business state?

Which assumptions about revision ordering were violated?

Why would repeatedly running the same update be a poor solution?

---

# Lab 4 — Prepare a Guarded Repair

Run the planning command.

```bash id="se32504plan"
python studio.py plan
```

The plan displays:

The intended booking identity.

The tenant.

The current status.

The current revision.

The verified evidence.

A short fingerprint identifying that particular preview.

### Tasks

Explain why the tenant condition matters.

Explain why the expected current version matters.

What should happen if the booking changes to version 7 before execution?

Why is the plan fingerprint useful as a review aid but not a secure authorization signature?

### Acceptance criteria

You can describe a repair precondition without relying solely on the booking's numeric ID.

---

# Lab 5 — Execute the Controlled Repair

Apply the repair using fictional approval metadata.

```bash id="se32504repair"
python studio.py repair \
  --approved-by release-captain \
  --ticket CASE-42
```

The script should commit three things together.

The corrected booking status and revision.

An audit record.

An outbox record.

Inspect:

```bash id="se32504verify1"
python studio.py verify
```

The primary record is now confirmed at version 6.

The derived stores remain stale.

The outbox contains one pending synchronization obligation.

### Investigation

Why is this a legitimate intermediate state?

Why doesn't a successful primary database transaction guarantee Redis or search-index consistency?

What should the application do if the downstream synchronization worker is unavailable?

### Required limitation

The command's `--approved-by` value is a label, not real authentication.

A production system needs verified operator identity and actual approval controls.

---

# Lab 6 — The Stale Reconciler Returns

Now replay the old supplier feed.

```bash id="se32504replay2"
python studio.py replay-feed
python studio.py verify
```

The feed should be rejected because its revision is older than the corrected booking revision.

### Explain

What changed between the unsafe repair and the guarded repair?

Why does this particular simulation avoid the overwrite?

Under what circumstances would comparing revisions be unsafe?

Consider systems whose version counters are assigned independently.

### Acceptance criteria

You understand that version ordering is meaningful only when the versions belong to a coherent authority and ordering scheme.

---

# Lab 7 — Reconcile the Derived Stores

Run the synchronization worker.

```bash id="se32504sync"
python studio.py sync
python studio.py verify
```

The three derived representations should now agree with the authoritative booking.

The pending outbox count should be zero.

### Task

Describe how this mechanism would differ in a real system.

Redis might receive an invalidation.

Elasticsearch might receive a versioned document update.

An analytical warehouse might receive a correction event.

Why shouldn't all three necessarily use identical data-update semantics?

### Additional challenge

What if the synchronization worker receives the same event twice?

What if an older event arrives after the newer one?

How should consumers preserve the correct representation?

---

# Lab 8 — Plan a Personal-Data Erasure

The fictional guest associated with booking 42 requests deletion of personal information.

For this exercise, assume that the applicable business and privacy policy permits removing the email address while retaining a limited booking record.

That is a hypothetical policy assumption, not a legal conclusion about real reservation data.

### Your task

Before using the erasure command, inspect where the email address exists.

Identify the primary record, three derived stores, and historical backup snapshot.

Determine which data belongs in the erasure scope.

Describe what approval and identity verification would be necessary in production.

### Important distinction

Removing an email attribute does not necessarily make the remaining booking record anonymous.

The retained guest ID or other related records may still permit identification.

---

# Lab 9 — Redact the Live Primary Record

Execute the simulated redaction.

```bash id="se32504erase"
python studio.py erase \
  --approved-by privacy-reviewer \
  --ticket CASE-ERASE-7
```

Inspect the result.

```bash id="se32504verify2"
python studio.py verify
```

The booking's email attribute should now be null.

The booking revision has advanced.

A tombstone exists for the guest ID.

An audit entry and outbox record were written.

But the derived stores still contain the old value.

### Your task

Explain why the live primary update is not the whole erasure workflow.

What should happen to stale cache, search, and analytical copies?

Why does the system need to prevent old events from repopulating the email?

### Safety note

The simulated tombstone is a persistent guest identifier.

In production, such an identifier may itself be personal data. Its lawful purpose, access restrictions, and retention must be assessed.

---

# Lab 10 — Propagate Redaction

Run:

```bash id="se32504sync2"
python studio.py sync
python studio.py verify
```

The primary and derived live representations should now agree.

The live email value should no longer appear in those records.

But the backup snapshot still retains the old value.

### Required explanation

Can the system truthfully claim that every historical copy has been erased?

No.

What remaining obligations must be addressed?

Consider backup retention, access restrictions, applicable legal requirements, and restoration procedures.

---

# Lab 11 — The Backup Resurrection Risk

Run:

```bash id="se32504restore"
python studio.py restore-preview
```

This command doesn't actually restore anything.

It inspects the retained historical snapshot and reports whether old personal data is present.

The snapshot predates the simulated redaction.

### Your task

Design an isolated backup-restoration process.

It should:

1. Restore the backup into an appropriately restricted environment.
2. Identify erasure operations that occurred after the backup.
3. Reapply relevant deletion or redaction obligations.
4. Verify that outdated personal details are not exposed.
5. Prevent stale ingestion or replay from recreating them.
6. Promote the restored environment only after the relevant checks succeed.

### Additional question

How would the design change if the relevant information were stored in a versioned S3 bucket rather than a PostgreSQL backup?

Explain the difference between an ordinary delete marker and permanent removal of object versions.

---

# Lab 12 — The Million-Row Repair

## Scenario

A production bug classified two million booking records incorrectly.

The team has identified the affected population.

An engineer proposes one enormous SQL update.

### Your assignment

Prepare a safer workflow that includes:

A reproducible target selection.

A preview with representative records.

Version or state preconditions.

A staged rollout.

Bounded batch transactions.

A durable checkpoint.

Per-batch audit and error reporting.

Resource limits to protect interactive traffic.

Cancellation behavior.

Downstream reconciliation.

Final invariant verification.

### Interviewer challenge

"The WHERE clause is correct. Why not just run the update once?"

Explain why query correctness alone doesn't establish operational safety under load, concurrent writes, partial failure, and downstream synchronization.

---

# Final Incident — The Booking That Wouldn't Stay Correct

## Starting symptom

Support confirms that a customer's reservation should be confirmed.

PostgreSQL reports pending.

A manual update appears successful.

Ten minutes later, the value reverts.

Redis and Elasticsearch continue to report old state.

Analytics has already counted the booking incorrectly.

A separate customer erasure request reveals personal-data copies in logs, caches, object storage, and backups.

### Required incident report

**Authoritative evidence:** What proves the booking's intended status?

**First failure:** Why did the original database state become incorrect?

**Repeated failure:** Why did the repair get overwritten?

**Safe correction:** What preconditions and transaction boundaries are needed?

**Audit:** What evidence should be recorded, and what sensitive information should be omitted?

**Propagation:** How do derived systems receive the correction?

**Reconciliation:** How do you detect remaining disagreement?

**Erasure:** What information exists outside the live primary database?

**Historical storage:** How should backup and versioned-object copies be handled?

**Verification:** How do you establish that the business correction remains correct and the privacy workflow has satisfied its defined scope?

### Senior-level challenge

Your interviewer says:

"It's just one customer record. Why are you turning this into an architectural problem?"

Explain why the number of rows involved doesn't determine the complexity of the consistency, authorization, and data-lifecycle obligations.

---

# STOP — Independent Investigation Ends Here

Do not read the following notes until you've attempted the repair and erasure exercises.

The goal is to reconstruct the state transitions, identify the real failure boundaries, and defend a safe operational response.

---

# Lab Diagnostic Notes

## The Unsafe Repair

The direct SQL update changed the current status without establishing a newer authoritative revision.

The stale supplier feed was allowed to overwrite it.

The repair corrected a value but not the ownership and ordering mechanism.

## The Guarded Repair

The controlled update verified the expected tenant, status, version, and supplier evidence.

It advanced the revision and wrote an audit record and outbox obligation in the same transaction.

This made the intended correction durable within the simulator's database boundary.

## The Reconciler

The stale feed had revision 5.

After the guarded repair, the authoritative booking had revision 6.

The simulator rejected the older feed.

This relies on the fixture's assumption that the revisions represent a comparable ordering.

Real supplier and application version schemes may require more careful reconciliation.

## Derived Representations

Redis, search, and analytics were represented by local SQLite tables.

They remained stale until the outbox synchronization ran.

The simulation demonstrates a consistency boundary, not the actual APIs or delivery guarantees of those systems.

## Redaction

The live booking email was removed, and the derived representations were later synchronized.

The exercise did not establish complete anonymization or legal erasure.

The guest identifier and historical backup snapshot remained.

## Backups

The historical snapshot retained the earlier email value.

A restore could reintroduce it if the recovery process ignored later erasure obligations.

The exercise intentionally reports that the complete lifecycle obligation remains outstanding.

## Production Design

A reliable implementation combines authoritative business evidence, guarded updates, minimal audit metadata, durable propagation, version-aware consumers, ongoing reconciliation, and governed retention/erasure workflows.

The central lesson is that the correct business outcome must remain true after the rest of the system has acted.

---

# Further Reading

Primary references:

- **PostgreSQL — UPDATE:** https://www.postgresql.org/docs/current/sql-update.html
- **PostgreSQL — Returning Data from Modified Rows:** https://www.postgresql.org/docs/current/dml-returning.html
- **PostgreSQL — Transaction Isolation:** https://www.postgresql.org/docs/current/transaction-iso.html
- **PostgreSQL — Explicit Locking:** https://www.postgresql.org/docs/current/explicit-locking.html
- **European Commission — Individual Data Protection Rights:** https://commission.europa.eu/law/law-topic/data-protection/information-individuals_en
- **European Commission — Dealing with Individual Rights Requests:** https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/dealing-requests-individuals_en
- **GDPR — Official Regulation Text, Articles 5, 16, 17, and 19:** https://eur-lex.europa.eu/eli/reg/2016/679/oj
- **European Data Protection Board — 2025 Coordinated Enforcement Framework Report on the Right to Erasure:** https://www.edpb.europa.eu/system/files/2026-02/edpb_cef-report_2025_right-to-erasure_en.pdf
- **ICO — Right to Erasure, Including Backup Systems:** https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/individual-rights/right-to-erasure/
- **Amazon S3 — Deleting Object Versions:** https://docs.aws.amazon.com/AmazonS3/latest/userguide/DeletingObjectVersions.html
- **Amazon S3 — Lifecycle Configuration:** https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
- **OWASP — Logging Cheat Sheet:** https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html

Related programme chapters:

- CS330-L03 — Transactions: When Correct Operations Produce Incorrect Results
- CS340-L05 — Replication, Consistency, and Sharding in Practice
- CS340-L06 — Specialized Data Systems
- CS430-L05 — Designing Reliable Business Workflows
- SE310-L03 — Application and Infrastructure Security
- SE320-L02 — Caching: Trading Freshness for Speed
- SE320-L03 — Queues, Workers, and Asynchronous Workflows
- SE325-L02 — Bulk Imports, Exports, and Background Data Operations
- SE325-L03 — Scheduled Jobs, Time, and Distributed Execution
- SE325-L05 — Surviving Third-Party Integrations
- SE440-L02 — Reliability Engineering and Incident Response

---

# Dense Cheatsheet — Interview Glance Card

*The complete card is fenced for screen-based revision and voice-reader skipping.*

```text id="se32504card"
SE325-L04 — PRODUCTION DATA REPAIR AND LIFECYCLE
================================================

CORE PRINCIPLE
--------------
Correcting a database row !=
correcting the entire business system.

Data may exist in:
  authoritative DB
  Redis cache
  search index
  analytical store
  logs
  object storage
  external vendors
  backups
  scheduled reconciliation feeds

REPAIR CONTRACT
---------------
Evidence
Scope
Preconditions
Postconditions

What real-world fact is correct?
Which record represents it?
Which writers can overwrite it?
Which derived systems must converge?

SOURCE OF TRUTH
---------------
Authority can be field-specific.

Supplier:
  confirmation evidence

Payment provider:
  external payment outcome

Booking DB:
  internal operational state

Search/cache/analytics:
  often derived representations

Number of matching copies
does not determine authority.

DRY RUN
-------
Verify:
  target identities
  tenant scope
  current values
  row versions
  expected count
  representative records
  downstream consequences

Preview and apply must express
the same intended conditions.

GUARDED UPDATE
--------------
WHERE id = expected
AND tenant = expected
AND status = expected
AND version = expected

Verify affected-row count.
Use RETURNING where appropriate.

Zero or unexpected matches:
  stop and investigate.

APPROVAL
--------
Authenticated actor
Appropriate permission
Ticket/case
Reviewed intention
Risk assessment
Time-bounded access if needed

BREAK GLASS
-----------
Emergency access may be needed.
Keep attribution and review.

AUDIT
-----
Actor
Operation
Business reference
Reason
Approval/ticket
Old/new versions
Time
Outcome

Avoid unnecessary PII payloads.

OUTBOX
------
Primary correction and
propagation obligation
commit together.

Delivery may repeat.
Consumers need idempotency.

ORDERING
--------
Stale event must not overwrite
newer authoritative state.

Version numbers must belong
to a meaningful ordering scheme.

CACHE
-----
Invalidate or update.
Watch stale repopulation races.
Critical facts need freshness rules.

SEARCH
------
Derived index may lag.
Version-aware reindex/update.
Verify convergence.

ANALYTICS
---------
Historical observation !=
latest corrected business truth.

Correction semantics must
follow the data contract.

SCHEDULED WRITERS
-----------------
API
admin tools
supplier sync
reconcilers
imports
workers
migrations

Know all writers before repair.

BULK REPAIR
-----------
Stable target set
Guarded batches
Durable progress
Safe retry
Resource budgets
Cancellation
Audit
Reconciliation

Do not block production blindly.

DATA LIFECYCLE
--------------
Collection
Use
Retention
Restriction
Correction
Erasure
Backup expiration
Restoration safeguards

SOFT DELETE
-----------
Hide/deactivate record.
Personal data may remain.

HARD DELETE
-----------
Remove live logical record.
Copies may remain elsewhere.

REDACTION
---------
Remove selected attributes.
Remaining data may remain personal.

ANONYMIZATION
-------------
Person no longer identifiable
under applicable standard/context.

Pseudonymization !=
automatic anonymization.

GDPR RIGHT TO ERASURE
---------------------
Important but not absolute.

Assess:
  valid request
  identity
  data scope
  lawful grounds
  legal retention exceptions
  affected recipients
  response obligations

Engineers implement policy;
they don't invent legal rules.

ERASURE FOOTPRINT
-----------------
DB tables
Caches
Indexes
Warehouses
Logs/traces
Object storage
External recipients
Backups
Restored environments

TOMBSTONES
----------
Prevent stale replay
from recreating erased data.

But tombstones may themselves
contain personal identifiers.

Minimize and protect.

S3 VERSIONING
-------------
Ordinary delete may create
a delete marker.

Old versions may remain.

Permanent deletion requires
appropriate version/lifecycle
handling and retention review.

BACKUPS
-------
Restore can resurrect data.

Keep appropriate retention,
access and beyond-use controls.

Reapply post-backup erasure
obligations before promotion.

AUDIT VS ERASURE
----------------
Preserve necessary evidence.
Avoid retaining raw sensitive
data unnecessarily.

Audit logs have retention rules too.

VERIFY A REPAIR
---------------
1. Primary invariant correct
2. Stale writers cannot revert
3. Outbox progresses
4. Derived stores converge
5. Business behavior correct
6. Audit recorded
7. No unexpected side effects

VERIFY ERASURE
--------------
1. Approved scope established
2. Live data handled
3. Derived copies handled
4. External recipients addressed
5. Historical storage policy applied
6. Restore path preserves erasure
7. Outstanding obligations tracked
8. Communication accurate

ANTI-PATTERNS
-------------
"Just UPDATE this row."
"One affected row means safe."
"Redis agrees, so it is true."
"Re-run the repair every night."
"Outbox means exactly once."
"Soft deleted means erased."
"Immutable audit logs keep all PII."
"S3 DELETE removes every version."
"Backups don't count."
"Restoring a backup restores truth."
"Anonymized means replaced email
 with customer ID."
"Query succeeded, so repair complete."

SENIOR MENTAL MODEL
-------------------
A repair restores a business fact.

A lifecycle operation governs
how information may continue
to exist and be used.

Both require authority,
scope, controlled changes,
propagation and verification.

NEXT
----
SE325-L05
Surviving Third-Party Integrations
```
