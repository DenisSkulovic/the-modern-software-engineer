# QUEUE-01 — More consumers, worse system

**Status:** planning stub  
**Linked:** SE335-L02/L03

## Starting symptom

Ops scales RabbitMQ consumers; latency and/or DB load worsen; queue may still grow.

## Deliverables before spoilers

Hypothesis → evidence → mechanism → change → verification.

## Progressive evidence (author later)

- Prefetch and ack behavior  
- Requeue / poison patterns  
- Downstream pool saturation  
- Retry amplification

## Solution notes

*Placeholder.* Concurrency is not free throughput.
