# MONGO-01 — Deep page latency after “efficient” aggregation

**Status:** planning stub  
**Linked:** CS345-L02/L03/L04

## Business context

Hotel admin customers list for a large tenant. UI requests page size 20 with high page numbers for “jump to end.”

## Starting symptom

Page 1 loads in ~150 ms. Page ~5,000 takes ~18 seconds. Response payload is still only ~20 documents.

## What you must produce (before spoilers)

1. Hypothesis  
2. Evidence you would collect  
3. Suspected mechanism  
4. Corrective change(s)  
5. Verification plan  

## Progressive evidence (author later)

- Pipeline text (`$match` → `$lookup` → computed `$addFields` → `$sort` → `$skip` → `$limit`)
- `explain("executionStats")` snapshots for shallow vs deep pages
- Index inventory
- Cardinality / spill hints

## Solution notes (do not read first)

*Placeholder.* Expect: deep `$skip` after expensive compute/sort; possible denormalized/indexed sort key; cursor pagination; sync/backfill trade-offs. Measure before/after.

## Anti-patterns to catch

“It only returns 20 docs, so it can’t be expensive.”  
“Just add `$limit` earlier” without understanding sort requirements.
