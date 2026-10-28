# Production Case Library

Realistic incident packets for study and Interview Lab drills — **not** a numbered course.

Ordinary lectures explain mechanisms. These cases hand you a symptom and evidence and require diagnosis **before** the solution.

## How to use a case

1. Read **Business context** and **Starting symptom** only.
2. Form a hypothesis.
3. Unlock **Evidence** sections in order (do not jump to the solution).
4. State mechanism → proposed change → how you would verify.
5. Only then open **Solution notes**.
6. Optional: run the matching studio lab when the linked elective manuscript exists.

## Contract

- Diagnosis precedes spoilers.
- Multiple remediations may be valid; naive fixes may be wrong on purpose.
- Cases do not auto-update Study Ledger fluency.
- Interview Lab may present a case as an interviewer packet (confirmed/inferred artifacts labeled).

## Catalogue

| ID | Starting symptom | Linked electives (stubs) |
| --- | --- | --- |
| [MONGO-01](MONGO-01.md) | Admin page 1 ~150 ms; page 5,000 ~18 s | CS345 |
| [MONGO-02](MONGO-02.md) | `$lookup` endpoint slows as history grows | CS345 |
| [PG-01](PG-01.md) | Query uses an index but loses to seq scan | CS350 |
| [PG-02](PG-02.md) | Disk climbs despite deleting millions of rows | CS350 |
| [REDIS-01](REDIS-01.md) | ~99% hit ratio with serious DB overload | SE335 |
| [QUEUE-01](QUEUE-01.md) | More RabbitMQ consumers make the system slower | SE335 |
| [CICD-01](CICD-01.md) | CI reports success; production runs unexpected version | SE360 |
| [RELEASE-01](RELEASE-01.md) | App rollback errors because schema already changed | SE360, CS350 |

## Relation to the curriculum

- **CS340 / CS330 / SE320 / SE340** — conceptual foundations (keep; do not regenerate for these cases).
- **CS345 / CS350 / SE335 / SE360** — diagnostic-first electives that own the labs.
- **SE325 / SE460** — adjacent (bulk ops / cross-layer performance); do not duplicate their syllabi here.
- **Interview Lab** — may draw cases as live investigation prompts.

## Status

Case files below are **planning stubs** (symptom + outline). Runnable fixtures and full progressive evidence land with the matching elective manuscripts.
