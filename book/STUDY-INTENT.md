# Study intent — priorities for humans and agents

Authoritative for **how this library is used**, not how manuscripts are written.
Manuscript voice/structure rules stay separate. Interview simulation mechanics live in [`interview-lab/`](interview-lab/).

If an agent’s advice conflicts with this file, **this file wins** unless the user explicitly overrides it in the conversation.

---

## Who this is for

Experienced **senior** full-stack / AI-systems engineer refreshing knowledge for **European product-company interviews** (and continuing to learn) — not a first-time CS student and not a multi-year degree redo.

Real production experience is assumed; see [`interview-lab/profiles/CANDIDATE-baseline.md`](interview-lab/profiles/CANDIDATE-baseline.md) for lab calibration (kept high-level — this repo is public). The catalogue **reactivates and systematizes** that experience; it does not replace it.

---

## North star

**Warm up a solid foundation → apply with confidence → keep learning while the pipeline runs → sharpen to a company when a calendar invite appears.**

During the refresh, prefer **breadth and architectural intuition** over indiscriminate memorization. Use [`engineering-decision-map.md`](engineering-decision-map.md) to reconnect siloed topics. The catalogue is a **reference library**, not a completion checklist — listen across domains; let Interview Lab and real job requirements decide where to go deep.

Success is interview competence and continued growth, **not** finishing every course, every lab, or reaching `fluent` on the ledger.

> The curriculum serves the learner. The learner does not serve the curriculum.

---

## Stages (default path)

| Stage | What matters | What does *not* matter yet |
| --- | --- | --- |
| **1. Refresh / warm-up** | Listen (or read) diversified lectures; rebuild vocabulary and mental models; optional shortlist in `students/<id>/queue.yaml` | Completing labs; course %; Duolingo-style gamification |
| **2. Apply + practice** | Applications; Interview Lab (HR + technical); keep light listening in parallel | Waiting for perfect confidence before applying |
| **3. Invite-driven** | JD, company, date on the calendar → focused mocks; short DSA only if that process needs it | Premature algorithm grind; rewriting the whole study system |
| **4. Ongoing** | Feedback from real interviews; selective deep dives; optional hands-on when useful | Treating any single interview as the whole story |

Applications can start **before** the listening queue is empty. Recruitment lag is real.

---

## What “studying” means here

### Primary: expose and systematize

- **Listening** (voice read-aloud, often at 1.25–1.5×) is the default study mode. Code in a lecture is an illustration for the screen; the prose around it is supposed to carry the point, so a code-heavy lecture is still a listen once that prose exists. Labs stay screen work. Manuscript authoring: [`.cursor/rules/manuscript-voice-structure.mdc`](../.cursor/rules/manuscript-voice-structure.mdc).
- Diversify subjects across sessions (university-style). Do not binge one course for days.
- Prefer a curated **listen queue** over rigid catalogue `study_order` when preparing for interviews.
- A first-pass confidence around **2/5** is a normal refresh signal, not incomplete work.
- Logging a listen with phase `studying` means “serious pass of the prose,” not “mastered.”

### Secondary: demonstrate under pressure

- **Interview Lab** (simulated HR, technical, architecture, debugging conversations) is the main *active* practice.
- That is how “exposed” becomes “interview-ready” — not by clearing lecture exercise checklists.
- Optional: short verbal recall (“explain X without notes”) when useful; not a mandatory spaced-repetition product.

### Optional / later: hands-on

- Labs, challenges, and end-of-lecture tasks are **optional**.
- Vibecoding, cloud console time, and deep electives are welcome when energy or a specific role warrants them — never as a gate before applying.

---

## Lecture exercises, labs, and oral prompts

Manuscripts include exercises, labs, oral-exam style prompts, and cheatsheets **on purpose**.

| They are for | They are *not* for |
| --- | --- |
| Reference while studying | Mandatory homework for every lecture |
| Inspiration for Interview Lab questions and drills | A mandatory completion checklist |
| Optional deepening when curiosity or a JD demands it | Proof that listening “didn’t count” |
| Cheatsheet / mental-model revisit before a mock | Blocking progress until `labbing` → `settled` |

**Agent rule:** Do not require labs after every listen. Suggest hands-on work only when the user asks or a mock shows a concrete topic worth revisiting.

When running Interview Lab, agents **may** mine lecture oral prompts / challenges as question inspiration — that is a primary use of those sections.

---

## Ledger phases — how to interpret them

Full vocabulary: [`STATUS.md`](STATUS.md). Practical reading for this programme:

| Phase / signal | Meaning in *this* programme |
| --- | --- |
| `studying` after listen/read | Exposed / refreshed — success for stage 1 |
| `wandering` / skim | Partial; fine to defer (e.g. cloud without console time) |
| `labbing` | Optional path; not expected by default |
| `settled` / `fluent` | Nice if earned via mocks or real work; **not** targets for the refresh week |
| Dashboard settled% during listen-first prep | Secondary; exposure and mock practice matter more |
| “Exposed” count / queue progress | Better stage-1 signals than settled% |

Encore automation is secondary to revisits driven by mocks and real interview feedback.

---

## What agents must not optimize for

- Finishing courses in catalogue order as the default plan
- Lab completion rates or exercise checklists
- Building study recommenders or tracking systems unless the user asks
- Premature LeetCode / P5 algorithm drills for European product roles
- Non-default market rituals or FAANG puzzle defaults (see Interview Lab rule)
- Treating skipped labs as lack of experience
- Delaying applications until the curriculum looks “complete”

---

## What agents should optimize for

- Diversified, interview-relevant listens (audio vs screen when it matters)
- Short curated queues (`students/<id>/queue.yaml`) over giant schedules
- Starting Interview Lab early; using lecture tasks as **question banks**, not homework
- Aligning mocks to European product full-stack (P1) unless evidence says otherwise
- Company/JD-specific prep **after** an invitation exists
- Mock feedback → optional targeted re-listen (not “do all exercises for that chapter”)

---

## Key files

| File | Role |
| --- | --- |
| This file | Priorities and stages |
| [`engineering-decision-map.md`](engineering-decision-map.md) | Cross-discipline architecture navigation |
| [`students/<id>/queue.yaml`](students/dskul/queue.yaml) | Short-term listen shortlist |
| [`students/<id>/activity.yaml`](students/dskul/activity.yaml) | What was actually studied |
| [`interview-lab/PROTOCOL.md`](interview-lab/PROTOCOL.md) | How to run mocks |
| [`STATUS.md`](STATUS.md) | Manuscript vs learning status mechanics |
| [`README.md`](README.md) | Library overview and catalogue philosophy |

---

## One-line reminder for agents

**Listen to systematize experience → mock to retrieve under pressure → apply in parallel → sharpen when invited. Labs are reference material, not the programme.**
