# Interview Assessments — realistic cross-disciplinary rounds

These are **simulated hiring rounds**, not course exams, actual employer interview questions, or predictions that a specific recruiter will choose a given format. They are designed from publicly described hiring methods and job-relevant duties for senior European product/full-stack roles. The employer-specific application mapping, if maintained, belongs in the private applications tracker, not here.

## First distinction: static paper versus live mock

Each paper is a **runbook** containing: candidate brief, interviewer pacing and staged reveals, concrete technical material, and a **separate interviewer key behind a STOP boundary**. In a self-study pass, read the candidate brief and stop before the key; in ChatGPT Interview Lab mode, ask the interviewer to reveal **one stage at a time**, and withhold the key until debrief. A static paper is not equivalent to a live, adaptive 90-minute interview.

Existing references: [Interview Lab protocol](../PROTOCOL.md), [course examinations](../../EXAMINATIONS.md), [candidate baseline](../profiles/CANDIDATE-baseline.md), and [assessment protocol](ASSESSMENT-PROTOCOL.md).

## Assessment families

| Track | Philosophy | Paper | Nominal duration | Primary evaluation |
| --- | --- | --- | --- | --- |
| 01 | Engineer-to-engineer discussion | [EC01 — What You Actually Owned](01-peer-conversation/EC01-what-you-actually-owned.md) | **60 min** (authentic to that round type) | Real project ownership, technical specificity, trade-offs |
| 02 | Product problem / CTO discussion | [PD01 — The Broken Building Signal](02-problem-discussion/PD01-building-signal.md) | **90 min** + optional 30-min individual thinking | Discovery, proportional architecture, challenge assumptions |
| 03 | Live debugging / code forensics | [DB01 — Wrong Customer, Wrong Results](03-live-debugging/DB01-wrong-customer-results.md) | **90 min** | Reading unfamiliar React/Node code, evidence, safe repair |
| 04 | Focused system design | [SD01 — Memberships and Entitlements](04-system-design/SD01-entitlements.md) | **90 min** | Data ownership, authorization, migration, reliability |
| 04 | Focused system design | [SD02 — Durable Commerce Integrations](04-system-design/SD02-commerce-integrations.md) | **90 min** | External APIs, workflows, idempotency, reconciliation |
| 05 | AI-assisted / spec-driven delivery | [AD01 — Review the Agent's Plan and Patch](05-ai-assisted-delivery/AD01-agent-patch-review.md) | **90 min** | Specifications, AI code review, product safety, validation |
| 06 | Live practical case / pair programming | [LC01 — Search and Select Orders](06-live-coding/LC01-order-search.md) | **90 min**, including 50-min implementation window | Bounded coding, state, async behavior, tests, collaboration |
| 07 | Pull-request review / maintainability | [PR01 — The Invoice List PR](07-code-review/PR01-invoice-list.md) | **90 min** | Risk-based code review, data isolation, API correctness |

**What is and is not grounded:** An employer may explicitly describe a conversation, live case, or no-code discussion. That can justify the *format*. The scenarios here are **fictional exercises** selected because their engineering challenges resemble the job descriptions; they are not leaked questions. When the invitation arrives, **its format and duration override these examples**. Do not conflate a typical 90-minute technical round with WeMaintain's distinct 60-minute engineering conversation.

## Recommended sequence (not eight mandatory exams)

1. **EC01** — see if you can explain actual engineering work rather than merely recognize techniques. No need to finish 90 minutes.
2. **DB01** or **PR01** — show code comprehension and useful debugging judgment, especially where React experience is AI-mediated.
3. **SD01** or **SD02** — end-to-end architecture grounded in business contracts.
4. **PD01** — dialogue with an ambiguous stakeholder problem, no premature diagram.
5. **AD01** — explicitly test modern AI-assisted engineering judgment.
6. **LC01** only if a hiring process announces practical coding or earlier simulations reveal a code-manipulation gap.

Rotate them. Do not turn all eight into a graduation checklist; each round must change what you know about your readiness.

## How to start in ChatGPT

"Use book/interview-lab/assessments/03-live-debugging/DB01-wrong-customer-results.md. Run a realistic mock, one prompt at a time. Don't reveal later clues or the answer key until I say end interview. I want a practical technical conversation, not trivia."

Or: "Walk me through PD01 in Observe mode, showing both interviewer and candidate, followed by a debrief."

## Design principles

- European *product engineering* baseline; not geography-based stereotypes and not FAANG algorithms by default.
- Each interview has informal opening, a central problem, reasonable follow-ups, time to ask questions, and a debrief. It **does not** contain 90 minutes of trivia.
- Strong responses include assumptions, evidence, trade-offs, simple alternatives, and failure modes. There is rarely one exact architecture.
- Interviewer must adapt to answers, skip branches when time is short, and permit "I haven't used that framework but I know the analogous mechanism."
- In no-code rounds, evaluate **verbal engineering reasoning**; do not sneak in a coding test.
- In coding rounds, state whether AI is allowed *before* beginning. Two optional modes exist, but do not claim which the real employer uses.
- After the round, reference relevant curriculum topics (SE250, CS350, CS430, SE320, SE310, SE440, AI410) **only where a concrete gap was observed**.
- Do not score a static self-study read as demonstrated interview competence.
