---
id: CS340-L05
course: CS340
title: "Replication, Consistency, and Sharding in Practice"
type: core
manuscript: stub
edition: "2.0.0"
legacy_ids: []
prev: CS340-L04
next: CS340-L06
---




# CS340 — Data Systems Beyond Relational Databases
## Lecture 05: Replication, Consistency, and Sharding in Practice

*How modern databases organize information, choose their trade-offs, and behave when real applications put them under pressure.*

**Estimated study time:** TBD once the spoken manuscript exists (target roughly 60–90 minutes including lab).

---

### Status — stub outline

This file is a writing scaffold. Full voice-first manuscript still to be authored.

**Learning objective:** Replica sets, read/write concerns, failover, partition keys, hotspots, and what happens when a node disappears.

**Complements:** CS330 (relational modeling, SQL performance, transactions). This course covers other data models, storage-engine trade-offs, and specialized systems — not a MongoDB certification track.

**Voice-first target when written:** spoken narrative first; diagrams and dense samples as screen aids with spoken captions; oral examination; mental model; optional lab only after *The spoken lecture ends here…*

### Planned spoken path

1. Hook — the read-after-write that saw yesterday's document
2. Replica sets — primary, secondaries, and failover reality
3. Write concern and read concern — durability versus freshness knobs
4. What a node failure looks like to the application
5. Sharding — partition keys as destiny
6. Hotspots, jumbo chunks, and uneven growth
7. Secondary indexes and scatter-gather across shards
8. Connecting CS330 transaction intuition to multi-node data systems
9. Oral examination · Mental model · Next lecture · Optional lab

<!-- Expand into full manuscript below; delete this stub scaffold when the lecture lands. -->
