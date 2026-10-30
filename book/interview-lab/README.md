# Interview Lab

Adaptive mock interviews for this programme — **separate from** CS / SE / AI course numbering.

Courses teach. This lab checks whether you can retrieve, explain, apply, and defend that knowledge under interview conditions that match the job you are actually pursuing.

**Default:** practical, job-relevant interviews for **European product companies** (Germany, Netherlands, Sweden, and similar).  
**Not the default:** Israeli/Tel Aviv market conventions, FAANG-style LeetCode rituals, theatrical pressure, or corporate slogan drills.

Full rules: [`PROTOCOL.md`](PROTOCOL.md).  
Programme priorities (listen-first refresh; labs optional; mocks as interactive practice): [`../STUDY-INTENT.md`](../STUDY-INTENT.md).

Static course-wide practice papers (questions + model answers, not live sims) live under each course’s `exams/` folder — protocol: [`../EXAMINATIONS.md`](../EXAMINATIONS.md). Do not confuse those with Interview Lab sessions.

Lecture oral prompts, challenges, labs, and course-exam questions are fair **question inspiration** for sessions here — not homework the candidate must have completed first.

---

## Quick start

Say something like:

```text
Run a realistic HR interview for a senior full-stack role at a Berlin product company.
```

```text
Walkthrough: 45-minute technical interview, backend-heavy SaaS in the Netherlands.
Play both interviewer and candidate (Observe mode).
```

```text
Here's the JD and invitation. Build a P6 profile (confirmed vs inferred vs unknown),
then run a strict 45-minute technical interview. One question at a time.
```

Four settings every run should make explicit (or inherit from defaults):

| Setting | Controls | Defaults if omitted |
| --- | --- | --- |
| Target profile | Employer, market, stack, seniority, evidence | **P1** practical European product full-stack |
| Interview round | HR, hiring manager, technical, coding, debug, design, review | Inferred from your wording |
| Interviewer persona | Friendly collab, terse lead, skeptical architect, formal HR, … | Sensible for the round |
| Participation mode | Observe / Guided / Realistic / Strict / Drill | Realistic if you say “interview me”; Observe if you say “walkthrough” |

Session controls during a live sim: `pause` · `hint` · `clarify` · `skip` · `end interview` · `redo`

---

## Layout

```
interview-lab/
├── README.md                 ← you are here
├── PROTOCOL.md               ← binding rules for every simulation
├── profiles/
│   ├── CANDIDATE-baseline.md ← living candidate assumptions
│   ├── P1-….md … P5-….md     ← reusable presets
│   └── P6-_template.md       ← copy for a real company invitation
├── templates/
│   ├── session-brief.md      ← optional pre-flight card
│   └── session-report.md     ← post-interview debrief archive
└── sessions/                 ← completed reports (when you ask to save)
    └── README.md
```

Do **not** invent a giant question bank up front. Grow reusable profiles from real JDs and invitations. Use completed sessions to spot curriculum gaps.

---

## Modes at a glance

| ID | Mode | You do | Simulator does |
| --- | --- | --- | --- |
| M1 | Observe | Watch | Plays both sides; explains patterns after |
| M2 | Guided | Answer | Feedback / hints after each answer |
| M3 | Realistic | Answer | Stays in character; debrief only at end |
| M4 | Strict | Answer | Like M3 + challenges vagueness (still professional) |
| M5 | Drill | Repeat one skill | Rapid correction, not full-round realism |

---

## Profiles at a glance

| ID | Name | Algorithm-heavy? |
| --- | --- | --- |
| P1 | Practical European product-company full-stack (**default**) | Only if evidence says so |
| P2 | Backend-heavy product / cybersecurity | Rarely by default |
| P3 | European SaaS / structured product engineering | No assumption of LeetCode |
| P4 | Established enterprise team | Depends on employer evidence |
| P5 | Algorithm-heavy assessment | **Opt-in** or evidence-driven |
| P6 | Targeted company (from JD + invitation) | Overrides presets |

---

## Relation to study progress

- Interview sessions are **not** automatic study-ledger updates.
- Debriefs may recommend lectures (`SE320-L03`, `CS330-L03`, …) without marking them fluent.
- Optional: after a saved session, log a personal `note` in your Study Ledger if you want the calendar to show interview practice days.

---

## Agent rule

Cursor agents follow [`.cursor/rules/interview-lab.mdc`](../../.cursor/rules/interview-lab.mdc) whenever you ask for a mock / HR / technical interview simulation. The rule points here; **this protocol is authoritative**.
