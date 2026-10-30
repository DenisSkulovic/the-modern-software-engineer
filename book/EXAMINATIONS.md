# Course Examinations — Retrieval, Integration, and Interview Readiness

## Purpose

Course examinations are reusable, standalone oral-practice papers for the Modern Software Engineer programme. They sit between lectures and the live Interview Lab:

- **Lectures** introduce and systematize ideas.
- **Course examinations** demand recall, connections, judgment, and explanations across a whole subject.
- **Interview Lab** rehearses adaptive, job-specific human conversations, follow-ups, and pressure.

An examination is **not** a recap of one lecture, a mandatory homework sheet, a certification test, or a disguised LeetCode contest. It can be useful **before, during, or after** studying the course. A question the learner cannot answer yet is an opportunity to learn through its model solution, not proof of failure.

This document supplements `STUDY-INTENT.md` and `interview-lab/PROTOCOL.md`; it does not replace them. The existing listen-first, breadth-first, European product-company interview priorities remain in force.

## Repository layout and identity

Place exam papers inside their own course, without treating them as curriculum lectures:

```text
book/
├── EXAMINATIONS.md
├── CS/
│   └── CS230-computer-networks/
│       ├── CS230-L01-....md
│       └── exams/
│           ├── CS230-EX01.md
│           ├── CS230-EX02.md
│           └── CS230-EX03.md  (when requested)
└── SE/
    └── SE320-backend-services/
        └── exams/
            └── SE320-EX01.md (when requested)
```

Use `<COURSE>-EX<NN>.md` with two-digit sequential variants. Exam numbers are **editions of practice**, not a difficulty ladder or academic years. Each variant must stand on its own, and there is no fixed number of exams. Do not add exam files to `curriculum.yaml`: its entries and manuscript progress statuses describe **lectures**, not practice papers. Do not update the personal Study Ledger automatically because someone opened or completed a paper.

## How to use an examination

1. Open the paper and read or listen to **Part I — Questions**. Pause after each question and try to explain the answer, preferably aloud, in roughly 30–120 seconds. Notes or looking things up are allowed, especially during the refresh phase.
2. Continue to **Part II — Model Answers**. Compare your explanation with the reasoning rather than expecting verbatim wording. If a topic is unfamiliar, simply learn from the answer.
3. If one issue seems important and unresolved, revisit that lecture or ask for a targeted explanation. There is no obligation to complete an exercise or repair every weakness immediately.
4. Request another independent variant whenever useful. Switch to the live Interview Lab to practice adaptive follow-ups, technical discussion, debugging, architecture, or HR interviews.

The answers intentionally appear **after all the questions**, to preserve a genuine retrieval attempt. Solution headings repeat the question's concept and ID so a learner can navigate without losing their place. This also makes the documents usable by text-to-speech readers. The reader can stop at `Part II` to avoid spoilers.

## Format of each examination

A typical paper has **16–20 independent questions** across three progressively demanding bands:

- **Foundations (approximately 25%)** — explain essential mechanisms and vocabulary in plain language.
- **Working engineering judgment (approximately 40%)** — compare approaches, explain trade-offs, predict behavior, and connect mechanisms.
- **Production scenarios and unfamiliar twists (approximately 35%)** — reason from ambiguous symptoms, request useful evidence, and propose proportionate interventions.

These are guides, not quotas. An exam should feel like a thoughtful senior engineer probing whether another engineer understands the system—not an obscure trivia competition. Questions should be challenging enough to make retrieval effortful, but realistic enough to repay that effort.

Every paper contains:

1. A concise title, scope and usage note, with a rough active-practice duration.
2. **Part I — Questions**, numbered `Q01`, `Q02`, etc., escalating in difficulty.
3. A clearly marked **stop point before answers**.
4. **Part II — Model Answers**, matching the question numbers exactly.
5. Optional very short closing guidance for further study. No compulsory score, checklist, or pass mark.

Strong model answers:

- Give the essential mechanism first, then the important distinctions and trade-offs.
- State assumptions when a scenario is under-specified, rather than confidently inventing a single root cause.
- Show what observation would distinguish plausible explanations.
- Explain why a tempting but wrong answer is wrong when that teaches something substantial.
- Are substantial enough to teach a forgotten or entirely new concept, but concise enough for oral/TTS study; usually 1–3 solid paragraphs, longer only for rich cases.
- May offer multiple defensible solutions where architecture or operational context matters.
- Avoid requiring code execution, infrastructure access, handwritten subnet exercises, or compulsory labs.

## Course coverage and the real-world extension rule

**Exam the discipline, not the manuscript index.** Before authoring a paper, inspect `curriculum.yaml`, the course folder, and the actual contents of **all existing lectures** in that course; do not assume a lecture title reveals everything it teaches. Build a private coverage map of its foundational mechanisms, engineering trade-offs, and practical failure modes.

Select questions to cover the whole course **over the paper**, without forcing a one-question-per-lecture mapping. Integrative questions should often draw on several lectures. Rotate subtopics, situations, terminology and difficulty across variants. Avoid copying the lecture's existing oral-exam questions verbatim, and avoid cosmetic changes to the preceding variant.

Then go beyond the manuscript. Approximately **10–20%** of questions may explore closely adjacent, realistic concepts that an interviewer could reasonably bring up even if the course did not teach them. Mark these as **Extension** in the question heading or prompt, and give a self-contained explanation in Part II. Extension is not a license to jump into obscure protocol trivia, Staff/Principal architecture expectations, or unrelated algorithm problems.

For example, a networking exam can naturally connect to browser CORS, container egress policy, or retry amplification; a database exam can connect to API pagination, migration safety, or distributed consistency. Such extensions should be useful even if the learner never encounters them in a specific interview.

## Variation rules

When asked for the next paper in course `X`:

1. Read this protocol and the course's present catalogue and lecture content.
2. Inspect existing `X-EX*.md` papers so the next one is **substantively new**: new situations, combinations, angles, and misunderstandings, not paraphrased old questions.
3. Preserve broad course coverage and the practical engineering emphasis.
4. Use the next unused sequential exam ID. Do not overwrite previous exams unless specifically asked.
5. Keep questions and solutions in the same file, solutions strictly in the second part.
6. If content was not covered by the lectures, identify the important gap as an **Extension**, and teach it in the answer. Do not retroactively claim that it appears in a lecture.
7. If the course is mostly stubs or partially unwritten, assess the declared topic domain responsibly, label extensions generously, and avoid fabricating nonexistent lecture coverage.
8. Avoid generating a hundred papers in advance. Create a new paper when the learner wants one.

Variation is not a ban on recurring fundamentals. TCP reliability, transaction isolation, or React rendering may deserve repeated testing; what must change is the **reasoning path and situation**, not the importance of the principle.

## Relation to Interview Lab

Static exams are **open-answer study material**. Interview Lab is **interactive simulation**. Do not merge their files or pretend reading a model answer is the same as defending an answer against a follow-up.

If the learner asks, “Examine me on CS230,” choose whether they mean a new static paper or an interactive oral session based on context. For a live session, the Interview Lab rules take precedence: one question at a time, adaptive follow-up, no premature model answers in Realistic/Strict mode. Static exam variants can be used as inspiration, not as a script to recite.

## Personal attempt history (optional)

Course examinations must **not** be logged as fake lecture events in `activity.yaml`. That would distort lecture exposure.

When an attempt is worth remembering, append a qualitative entry to `students/<id>/exam-attempts.yaml` (template under `students/_template/`). Incomplete papers are fine. Fields are human-readable: date, course, exam id, mode, coverage, outcome, optional strengths/gaps/suggested lectures, and a short next step. No scores, rankings, deadlines, or automatic fluency promotion.

`progress_render.py` shows a **Recent course examinations** strip on `progress.md`. Lecture phases and settled% stay unchanged.

## Editorial standard

Use clear professional prose and practical examples, not lecture-length repetition. Make the questions concise, specific, and answerable without hidden data. Prefer conceptual understanding, mechanistic explanations, boundary awareness, trade-offs, and production diagnosis. If the best answer is “it depends,” explain precisely **what it depends on and how to find out**.

**Do not give away the answer inside the question.** Prefer a situation that forces independent recall (“private app cannot reach an external supplier — what could explain this, and how would you investigate?”) over a prompt that lists the mechanisms to name (“where do routes, NAT, security groups, and allowlists fit?”). Follow-ups may introduce specific machinery later.

Ask for a plausible diagnosis **and the next discriminating observation**, not only the name of a failure mode. Reward correct mental models, reasonable uncertainty, production judgment, and honest limits. Model answers are exemplars, not the only allowed wording.

Prioritize practical full-stack/backend engineering judgment over specialist trivia. A good paper can teach via its model answers; skipping questions carries no penalty. No scoring pressure, mandatory attempt counts, or retake deadlines.

**North star: listen to acquire concepts; examine to retrieve and connect them; simulate to defend them; apply for jobs without waiting for perfection.**
