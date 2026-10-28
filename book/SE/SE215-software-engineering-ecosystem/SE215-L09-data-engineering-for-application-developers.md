---
id: SE215-L09
course: SE215
title: "Data Engineering for Application Developers"
type: elective
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: SE215-L08
next: SE215-L10
---


# SE215 — The Software Engineering Ecosystem
## Lecture 09: Data Engineering for Application Developers

*A booking application records reservations correctly in PostgreSQL, but the analytics dashboard reports conflicting revenue totals. The data team says the pipeline is working, while application developers say the database is correct.*

---

### Status — Planning Stub

Full voice-first manuscript not yet authored.

**Pedagogical model:** short orientation elective. Target spoken duration ordinarily 18–25 minutes (~2,800–4,000 spoken words). Conceptual and practically informed; not a specialist qualification. Structure: Part I — Intuition, Part II — Deep Dive, oral examination, solutions, one Mental Model, Next Lecture hook; practical material after the spoken-end marker; Dense Cheatsheet at the end.

### Learning Objective

Understand the complete journey from operational data to reliable analytical information.

### Opening Problem

A booking application records reservations correctly in PostgreSQL, but the analytics dashboard reports conflicting revenue totals. The data team says the pipeline is working, while application developers say the database is correct.

### Planned Coverage

OLTP versus analytical workloads; ETL and ELT; event production; change data capture; batch processing; stream processing; message brokers; warehouses; data lakes; lakehouses; data transformation; orchestration; backfills; schema evolution; data contracts; lineage; data quality; deduplication; late-arriving events; and reconciliation. Technologies through responsibilities: Kafka, Airflow, dbt, analytical databases, and managed data-platform services. Follow one business event from the application database through ingestion and transformation into an analytical report.

### Scope Boundaries

CS340 already covers storage engines, specialized data systems, analytical databases, replication, CDC, and source-of-truth questions. This lecture connects those components into a data-engineering workflow rather than repeating database theory.

### Expected Understanding

Sketch an operational-to-analytical pipeline, recognize common failure modes, and explain the developer's responsibility for producing trustworthy data.

### Suggested Exercise / Lab

Design a booking-events pipeline and identify where duplicates, missing events, late events, and schema changes must be handled.

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
