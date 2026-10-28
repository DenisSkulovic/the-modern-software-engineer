# RELEASE-01 — Rollback fails after schema change

**Status:** planning stub  
**Linked:** SE360-L03, CS350-L04

## Starting symptom

Rolling back the application causes errors because the database schema (or data shape) has already moved forward.

## Deliverables before spoilers

Hypothesis → evidence → mechanism → change → verification.

## Progressive evidence (author later)

- Migration order vs app version  
- Expand/migrate/contract gaps  
- Error signatures from old app + new schema  
- Whether forward fix vs true rollback is viable

## Solution notes

*Placeholder.* Compatibility windows beat “just roll back the container.”
