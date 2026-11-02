# PD01 — The Broken Building Signal

**Format:** 90-minute *no-code* CTO/senior engineer product-case discussion. Optional **30 minutes alone beforehand** to think through the one-paragraph problem; no deck or deliverable.  
**Role archetype:** product-minded senior full-stack, real-world IoT / operations / event-driven workflow  
**Evidence basis:** based on the format of publicly described "problem to think about, then discuss" rounds; **this is a fictional case, not any company's actual task**.  
**Interviewer stance:** curious about product framing and operational usefulness; will challenge premature abstractions.

## Part I — Candidate packet and staged interview

### Optional pre-read (30 minutes maximum)

> A maintenance operator manages thousands of elevators across several countries. Each device emits vendor-specific alarms. Some alarms are duplicates; others are misleading. Technicians receive noisy notifications and sometimes attend the wrong equipment. Propose a **first useful product increment** that translates raw alarms into actionable work while preserving traceability. You do not have to invent an ML system, a perfect taxonomy, or a global platform.

The candidate may make reasonable assumptions and write private notes. **No slides, coding, or diagrams required.**

### 0–10 min — Context and clarification

**Interviewer:** "How would you frame the problem before proposing an architecture? Who is affected, and what does 'better' mean?"

Answer reasonable candidate questions with these **staged facts**:
- Customers are facility operators; technicians use mobile apps; dispatchers use a dashboard.
- There are 12,000 connected devices, about 250,000 alarm events/day, spikes up to 200 events/second.
- Three manufacturers supply differing alarm formats. Only about 40 alarm codes have verified operational meanings today, among thousands.
- Network connection may disappear for hours. A technician sometimes has no data connection on site.
- An existing contract database tracks which clients and sites own devices, and their service levels.

Do **not** present all facts as a shopping list unless the candidate asks; reveal the relevant subset.

### 10–30 min — Define V1

Ask: "What exactly ships in the first eight weeks? What will a technician experience differently?"

Explore:
- What counts as a distinct alarm versus a repeated signal?
- Do we show a confidence level / raw message when mapping is uncertain?
- What happens with an unmapped code?
- Would you let a low-confidence mapping automatically dispatch a technician?
- What metrics tell us if noisy alarms became useful work?
- How are technicians and dispatchers involved in testing the product?

Good alternatives include a human-reviewed rule mapping service and a simple incident timeline. AI is optional, not assumed.

### 30–55 min — Follow the data

"Draw verbally how a single device message becomes something the technician can act upon."

Expected boundaries to consider: ingestion, device identity, event idempotency, raw event retention, versioned normalization, state/incident correlation, alert policy, contract/SLA lookup, UI access and audit trail. Let the candidate decide whether to start with one service plus a queue or multiple deployables.

**Follow-up constraint:** Two events have the same vendor event ID on *different devices*. Some devices resend the same event with a different transport delivery ID after reconnecting. What identity assumptions change? Which data should never be destructively overwritten?

### 55–70 min — Inject an operational surprise

> After rollout, the on-call team observes 10× more "critical" incidents on one manufacturer's devices, but no corresponding increase in technician-confirmed failures. A firmware update happened yesterday. One large customer says the dashboard is now unusable.

Ask for an investigation with **competing hypotheses and observations**. Does the classifier need retraining? How might a vendor mapping version, thresholds, or firmware rollout be implicated? What is a safe rollback/containment move?

### 70–82 min — Product and organizational pushback

**Interviewer:** "Our commercial lead wants automatic dispatch next sprint and wants AI to classify the unknown codes. Your lead technician says half the old alarms were noise. What do you propose?"

Discuss phased automation, confidence and manual override, auditability, bounded rollout and measurable success. Include different countries' regulatory or service obligations only if the candidate brings them up, with no fictional legal requirements.

### 82–90 min — Candidate questions and wrap

Allow candidate questions about real work, user contact, safety expectations, engineering ownership, monitoring, or the company's appetite for a small V1.

---

# STOP — INTERVIEWER KEY / DEBRIEF ONLY

## What makes this realistic

This is not "design an IoT platform for a billion devices." It is an ambiguous operational problem where correct *product scoping* may dominate architecture. The 12k devices and 250k events/day are plausible fictional exercise inputs, not reported employer metrics.

## Reference approach

**Problem:** Reduce false urgency, preserve technician trust, and improve time from useful signal to appropriate action. Define baseline metrics before promising ML accuracy: events per incident, false-dispatch rate, technician acknowledgment/confirmation, time to triage, mapping coverage, and missed-critical incidents.

**V1 scope:** Ingest from one or two vendors; preserve immutable raw alarms, device identity, origin timestamp and ingest timestamp; version human-approved mapping rules for known high-value codes; correlate events into incidents with bounded windows and hysteresis; show raw evidence and mapping confidence; let dispatcher/technician correct outcomes. Make failure to classify a visible "unknown" state rather than an invented diagnosis. Keep manual dispatch approval initially.

**Minimal architecture:** Authenticated ingestion endpoint / broker → durable raw-event store → normalization processor → incident state or append-only transitions → notification/read API → dispatcher/technician UI. A small deployment may be enough. Dedupe should be scoped by manufacturer, device, event identity and semantics; transport IDs alone are unreliable. Offline uploads require ordering tolerance, event-time versus processing-time distinction, and deterministic reconciliation; a late signal shouldn't silently rewind current state. Device site and contract/SLA data are references, not copied uncritically into every event.

**Incident evidence:** Segment by firmware version, vendor code, device cohort and mapping version. Compare raw event rates with normalized severity and actual technician confirmations. Roll back or gate the suspect mapping rather than discarding raw data or declaring all firmware broken. Avoid automatically dispatching based on the unverified surge. Provide alert-throttling and an emergency manual operations path.

**Product negotiation:** Map unknown codes with labeled data and human-in-the-loop review. AI may help group descriptions, but confidence/traceability, measurable false positives, and careful launch controls matter more than whether the model is fashionable.

## Follow-up branches

- If candidate suggests Kafka + Kubernetes immediately, ask what a simpler single-service + durable queue would fail at this workload.
- If candidate suggests only UI filtering, ask about duplicated processing, missed severe alarms and an audit trail.
- If candidate suggests automatic dispatch, ask who carries the cost of a false positive and how to turn it off.
- If candidate asks for device firmware details, provide enough to describe the schema contract, not secret invented implementation facts.

## Rubric cues

Strong: scopes a useful V1; distinguishes source, normalized event and actionable incident; clarifies stakeholder value; names failure modes and evidence; deploys safely. Weak: claims a perfect taxonomy or zero false positives; treats event receipt as proof of hardware failure; uses LLM classification as an unverified correctness boundary; chases massive scale theatrically.

**Related studies only after observed gaps:** SE320-L03, CS430-L01/L05, SE330-L02, SE440-L01, AI410-L06 (only if discussing AI classification).
