# REDIS-01 — High hit ratio, database still overloaded

**Status:** planning stub  
**Linked:** SE335-L01/L03

## Starting symptom

Redis reports ~99% hits; primary DB CPU/connections scream.

## Deliverables before spoilers

Hypothesis → evidence → mechanism → change → verification.

## Progressive evidence (author later)

- Key patterns / cardinality  
- TTL and stampede behavior  
- Bypass paths / negative caching  
- Hot key metrics

## Solution notes

*Placeholder.* Hit ratio ≠ protected database.
