# MONGO-02 — `$lookup` slows as history grows

**Status:** planning stub  
**Linked:** CS345

## Business context

Customer detail endpoint joins growing per-customer history.

## Starting symptom

Latency rises steadily as history documents accumulate; payload shape unchanged.

## Deliverables before spoilers

Hypothesis → evidence → mechanism → change → verification.

## Progressive evidence (author later)

- Pipeline / `$lookup` shape  
- Growth of foreign collection  
- Stage stats over time  
- Index on foreign key / pipeline placement of `$match`

## Solution notes

*Placeholder.* Expect: unbounded join work; pre-aggregation; tighter `$match`; schema redesign; not “buy a bigger Atlas tier” as first move.
