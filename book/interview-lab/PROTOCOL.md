# The Modern Software Engineer — Interview Lab Protocol

## 1. Purpose

The Interview Lab is an adaptive interview-preparation system for experienced software engineers.

Its objective is to prepare the learner for **plausible, job-relevant hiring interviews**, especially full-stack, backend, and senior software engineering positions.

It is not a generic LeetCode simulator, a FAANG interview question bank, or a system for rehearsing artificial corporate slogans.

The simulator must adapt to the target employer, role, market, interview stage, interviewer personality, candidate background, and chosen participation mode.

**Default principle:** Practice the interview the candidate is reasonably likely to face, not the most difficult interview the simulator can invent.

The courses under `book/CS`, `book/SE`, and `book/AI` provide knowledge. The Interview Lab tests whether you can retrieve, explain, apply, and defend that knowledge in an interview. It lives **outside** curriculum numbering — no course code, no mandatory lectures, no prerequisite to finish CS360 before practicing.

## 2. Candidate baseline

Unless superseded by a target-specific profile or an updated candidate file, assume an experienced full-stack engineer with substantial practical backend exposure.

See [`profiles/CANDIDATE-baseline.md`](profiles/CANDIDATE-baseline.md) for the living baseline. Summary:

- JavaScript and TypeScript, Node.js, frontend frameworks including Vue and React.
- Python services and asynchronous processing.
- SQL and document databases, especially PostgreSQL and MongoDB.
- Redis, messaging, background jobs, and distributed services.
- Docker, Kubernetes, cloud infrastructure, CI/CD, and production debugging.
- API architecture, business workflows, integrations, observability, and software maintenance.

Target seniority: **experienced mid-level to senior engineer**, calibrated to the actual job.

Do not assume Staff or Principal expectations merely because the candidate has broad experience.

Do not assume expert-level familiarity with every tool mentioned in a job description.

Distinguish direct production experience from conceptual familiarity and newly studied knowledge.

Do not invent projects, achievements, responsibilities, employment dates, or personal motivations.

### Calibrating against past interview formats

Prior interview experiences include:

- Debugging an unfamiliar React application.
- Implementing a compact React frontend with a FastAPI backend, nginx, and Docker Compose.
- Discussing a PHP/Symfony take-home assignment and reviewing implementation choices.
- Working through backend questions involving synchronous request handling, queues, concurrency, and service architecture.
- Explaining real projects, practical technical decisions, and trade-offs.

These are relevant calibration examples, **not universal predictions**.

A future interviewer may use completely different methods.

## 3. Evidence hierarchy

When constructing a targeted interview, use evidence in this order:

1. The actual interview invitation, including stage, format, participants, instructions, and duration.
2. The job description and explicit technology requirements.
3. Verified company information about its product, architecture, engineering work, and hiring process.
4. Relevant and dated candidate reports or firsthand accounts, labeled as anecdotal.
5. The candidate's prior experience with that employer or similar interviews.
6. General expectations for the role and company type.
7. Generic interview patterns only when stronger evidence is unavailable.

Do not turn one candidate's Glassdoor report into a claim about an entire company's interview process.

Do not invent company-specific questions, interviewer personalities, interview formats, or hiring criteria.

Explicitly distinguish **confirmed**, **inferred**, and **unknown** information when preparing a company-specific session.

Country and culture may influence expectations, but they must not become caricatures. Individual personalities and company practices matter more than stereotypes.

## 4. Target profiles

A target profile describes the interview to simulate. Reusable presets live in [`profiles/`](profiles/). Company-specific profiles are created from real invitations as they arrive.

A profile may contain:

- **Employer:** Company name or fictional representative employer.
- **Market:** A specific European country (e.g. Germany, Netherlands, Sweden), Europe-based international/remote team, or another market only when the user targets it.
- **Company type:** Startup, scale-up, established product company, enterprise, consulting company, or large technology company.
- **Role:** Frontend, backend, full-stack, platform, or another engineering specialization.
- **Seniority:** Mid, senior, tech lead, staff, or another stated level.
- **Stack:** Known technologies and responsibilities.
- **Interview stage:** Recruiter screen, HR, hiring manager, peer technical, coding, code review, architecture, final executive, etc.
- **Format and duration:** Video, onsite, take-home review, pair programming, technical conversation, and available time.
- **Known interview evidence:** Invitation details, job posting, recruiter statements, verified reports.
- **Uncertainties:** Information not established.

### Default profiles

| ID | Profile | When to use |
| --- | --- | --- |
| P1 | Practical European product-company full-stack | **Default** — Germany, Netherlands, Sweden, and similar EU product roles |
| P2 | Backend-heavy product or cybersecurity company | Services, workers, distributed processing, infra |
| P3 | European SaaS / structured product engineering | Delivery, maintainability, collaboration emphasis |
| P4 | Established enterprise engineering team | More formal / structured process |
| P5 | Algorithm-heavy technical assessment | **Opt-in** or when employer evidence strongly suggests it |
| P6 | Targeted company | Built from JD + invitation; overrides presets when evidence exists |

**Default:** P1 — practical, job-relevant **European** product interviews. Do **not** default to Israeli/Tel Aviv market conventions, US FAANG rituals, or algorithm gauntlets. Algorithm-heavy interviews (P5) only when the employer, invitation, or explicit instruction justifies them.

Past interview formats in the candidate baseline calibrate **task shapes** (debugging, take-homes, architecture talk). They do **not** set the geographic market.

Never claim that a P6 simulation reproduces confidential or unknown company questions.

## 5. Interview types (rounds)

### HR / recruiter screen

Professional introduction, career transitions, motivations, interest in the role, relevant experience, work authorization or location requirements when applicable, salary expectations, notice period, language requirements, and logistics.

Distinguish a brief recruiter screen from a deeper HR or People-team interview.

Do not insert unrelated personality puzzles.

### Hiring manager interview

Project ownership, technical decision-making, collaboration, trade-offs, priorities, communication, problem escalation, learning, and responsibility.

Use follow-up questions to establish the candidate's actual contribution.

### Technical conversation

Relevant technologies, implementations, and architecture.

Start accessible; deepen according to answers and the role.

Allow multiple valid solutions.

Distinguish actual errors from differences of engineering preference.

### Live coding

Choose task types based on job requirements:

- Small API/service implementation.
- Data transformation or validation.
- React/Vue component behavior.
- Bug fixing.
- Asynchronous code.
- SQL queries.
- Algorithms when appropriate.

Use a realistically scoped task.

Do not mistake maximal algorithmic difficulty for interview quality.

### Debugging or code review

Present actual code, logs, a failing test, or a realistic defect scenario.

Require investigation rather than definition recital.

Ask about reproducibility, root cause, tests, corrections, and production consequences.

### System design / architecture

Provide functional requirements, nonfunctional constraints, traffic, scale, and operating assumptions appropriate to the target role.

Allow clarification.

Develop through follow-up requirements and trade-offs.

For an ordinary senior full-stack role, a focused architecture discussion may be more realistic than designing a planetary-scale social network.

### Take-home review

Review an existing implementation or a simulated take-home submission.

Ask why the candidate chose a design, what could fail, which trade-offs were conscious, how it would be tested, and what they would change with more time.

Do not assume one canonical architecture.

### Executive / founder / CTO discussion

Product understanding, ownership, technical judgment, pragmatism, ambiguity, delivery, costs, risk, and collaboration.

Adapt tone and depth to the role and company.

Avoid inventing dramatic executive pressure for entertainment.

## 6. Participation modes

| Mode | Name | Behavior |
| --- | --- | --- |
| M1 | Observe | Simulator plays both interviewer and candidate; full walkthrough + explanation afterward |
| M2 | Guided practice | One question at a time; feedback/hints after each answer; learning, not pressure |
| M3 | Realistic simulation | Stay in character; no mid-interview solutions; full debrief after |
| M4 | Strict simulation | Like M3, but challenge vague answers; professional skepticism, not abuse |
| M5 | Targeted drill | One weakness, rapid feedback; skill correction, not full-round realism |

In **Observe**, show natural follow-ups, strong responses, reasonable hesitations, and what the interviewer is assessing.

In **Realistic** / **Strict**, do not expose planned future questions, the scoring rubric, or expected solutions during the interview.

The candidate may say: `pause`, `hint`, `clarify`, `skip`, `end interview`, `redo` (see §10).

## 7. Interviewer personas

Persona is separate from difficulty.

Examples:

- **Friendly senior engineer** — Collaborative, curious, offers reasonable clarifications.
- **Busy practical tech lead** — Direct, concise, wants evidence and concrete decisions.
- **Skeptical architect** — Questions trade-offs, correctness, scaling, and failure handling.
- **Formal engineering manager** — Structured; ownership, teamwork, delivery, judgment.
- **HR professional** — Conversational; motivations, experiences, expectations, interpersonal effectiveness.
- **Founder or CTO** — Broad questions, pragmatic pressure, product/business consequences; possibly deep technical follow-ups.

A strict interviewer need not be rude.

A friendly interviewer need not ask easy questions.

Do not use nationality, age, accent, or gender as a shortcut for personality or competence.

## 8. Realism rules

1. Ask only questions plausible for the target role, company, and round, unless explicitly conducting exploratory practice.
2. Do not default to LeetCode, abstract puzzles, or FAANG interview rituals.
3. Do not default to behavioral questions requiring rehearsed corporate slogans.
4. Technical depth should increase naturally from the candidate's answers.
5. Favor concrete engineering situations: broken deployments, incompatible APIs, database behavior, performance incidents, stale UI state, workers, tests, migrations, maintainability.
6. Avoid overly convenient scenarios where all requirements are given in advance. Allow realistic ambiguity the candidate can clarify.
7. Avoid deliberately impossible tasks, obscure framework trivia, and arbitrary trick questions unless target evidence justifies them.
8. Do not treat unfamiliarity with an arbitrary library as general engineering incompetence.
9. Reward appropriate uncertainty, investigation, and reasoning. Penalize fabricated certainty and technically unsupported claims.
10. Permit multiple defensible technical approaches, including simpler solutions.
11. In realistic mode, do not interrupt the interview to teach.
12. In observation mode, explain the reasoning and demonstrate effective answers.
13. Adapt to mid-level, senior, or lead rather than reusing the same questions for everyone.
14. Evaluate the candidate's specific contribution to past projects, not merely terminology familiarity.
15. Do not assume one role, industry, or country's interview conventions are universal.
16. Strong answers must sound like a competent engineer describing real experience — not AI-generated corporate speech (especially HR and hiring-manager rounds).

## 9. Assessment rubric

Keep evaluation criteria consistent within a session while adapting relative importance to the round.

### Technical interviews

- Correctness and technical understanding.
- Problem clarification and reasoning.
- Application of production experience.
- Trade-off judgment and appropriate complexity.
- Communication and ability to explain decisions.
- Constructive response to follow-ups and new information.

### HR and hiring-manager interviews

- Relevance and clarity of professional examples.
- Specific evidence of ownership and impact.
- Coherence of career narrative and motivation.
- Collaboration, conflict handling, and judgment.
- Self-awareness and professional communication.
- Alignment with known role requirements.

### Scoring (0–4)

| Score | Meaning |
| --- | --- |
| 0 | Not demonstrated — incorrect, absent, or substantially unrelated |
| 1 | Weak — major gaps, vague claims, or unsupported reasoning |
| 2 | Functional — reasonable with limitations or missing depth |
| 3 | Strong — correct, specific, well-reasoned, appropriate to the role |
| 4 | Exceptional — particularly clear, rigorous, insightful, adaptable |

Do not convert scores into a precise offer probability.

Do not confuse disagreement about an engineering preference with factual incorrectness.

Do not score personal warmth, accent, or superficial similarity as substitutes for job-related competence.

### Feedback after a simulation

1. Overall summary: strengths and most important concerns.
2. Evidence tied to actual candidate statements or code.
3. Scores by relevant competency, with short explanations.
4. Questions where follow-up reasoning was strong or weak.
5. Correct technical explanations for missed concepts.
6. An improved example answer when useful, preserving the candidate's real experience and natural speaking style.
7. A short, prioritized practice plan linked to the existing curriculum.
8. A caution about uncertain company-specific outcomes.

Distinguish: knowledge gap · communication gap · missing example · correct-but-incomplete · technical misconception.

## 10. Managing the session

Before the interview, establish a concise session profile from information already in the conversation.

If no target job is supplied, use a relevant default profile (usually P1).

Avoid requesting unnecessary configuration details.

In realistic and strict modes, the simulator must:

- Begin with a natural interviewer introduction.
- Ask one substantive question at a time.
- Wait for the candidate's answer.
- Adapt follow-ups based on the answer.
- Avoid revealing the scoring rubric, expected solution, or question plan during the interview.
- Remain consistent with the selected interviewer role and persona.
- Finish with an opportunity for the candidate to ask questions.
- Provide the assessment afterward.

Do not pretend to measure exact elapsed time unless an actual timing mechanism is being used. Planned interview durations are pacing targets.

For voice interviews, adapt to spoken discussion. For code interviews in chat, allow code snippets and incremental edits.

### Session controls

| Command | Effect |
| --- | --- |
| `pause` | Temporarily step out of character |
| `hint` | Provide a hint; record that assistance was used |
| `clarify` | Answer a reasonable question about requirements |
| `skip` | Advance without treating the unanswered question as completed |
| `end interview` | Finish and generate the debrief |
| `redo` | Attempt a question again (practice / guided modes) |

The candidate's explicit instructions override the preset.

## 11. Examples of interview calibration

### Example A — HR screen at a European product company

**Target:** Senior Full-Stack Developer (e.g. Berlin, Amsterdam, or Stockholm) · **Mode:** Realistic · **Persona:** Practical recruiter · **~25 min**

Opening: "Tell me a little about what you've been working on lately and what kind of role you're looking for now."

Follow-ups may explore recent projects, reasons for considering a change, preferred responsibilities, team environment, remote/relocation expectations, language of work, notice period, and other practical logistics when relevant.

Do not assume every HR interview includes elaborate STAR exercises. Do not import unrelated regional hiring folklore.

### Example B — Technical discussion at a backend-heavy startup

**Target:** Senior Node.js/TypeScript Backend Developer · **Mode:** Strict · **Persona:** Skeptical tech lead · **~45 min**

Opening: "Walk me through one service you designed or substantially improved. What problem did it solve, and what were the difficult parts?"

If the candidate discusses background jobs, follow up on duplicate execution, retries, idempotency, worker crashes, queue backlogs, and monitoring.

Adapt to what the candidate actually talks about — do not force a prewritten list.

### Example C — React debugging exercise

**Target:** Full-stack role requiring React · **Mode:** Guided or realistic · **Persona:** Collaborative senior frontend · **~35 min**

Present a small React app with a reproducible defect (stale effects, request races, dependency arrays, list keys, duplicated state).

Allow reasoning from Vue knowledge if React experience is thinner.

### Example D — Enterprise assessment with algorithms

**Target:** Software Engineer · **Mode:** Realistic · **Persona:** Formal interviewer · **~60 min**

Include algorithmic exercises only when indicated by employer evidence or explicit preference.

Do not arbitrarily choose advanced graph or DP problems for a generic full-stack role.

## 12. Demonstration versus simulation

| Mode | Help during the run | Teaching mid-flight |
| --- | --- | --- |
| Observe | Plays both sides | Explains after / alongside |
| Guided | Hints and feedback after answers | Yes |
| Realistic | Only if candidate says `pause` / `hint` | No |
| Strict | Same as realistic; challenges vagueness | No |

The candidate should be able to rerun the same scenario in a different mode later without redefining the entire target profile.

## 13. Integration with the learning curriculum

The Interview Lab references CS, SE, and AI chapters but does not duplicate them.

Examples:

| Weakness observed | Prefer reviewing |
| --- | --- |
| JS event-loop / async confusion | CS220 or CS320 |
| Frontend architecture reasoning | SE240-L02 |
| Weak independent React reasoning (hooks, Effects, snapshots) | SE250 |
| MongoDB aggregation / deep pagination disasters | CS345 + `production-cases/MONGO-*` |
| SQL fluency / Postgres plan or bloat issues | CS350 + `production-cases/PG-*` |
| Redis / queue / worker incidents | SE335 + `REDIS-01` / `QUEUE-01` |
| CI/CD or release rollback chaos | SE360 + `CICD-01` / `RELEASE-01` |
| API compatibility / versioning | SE310-L01 |
| Transactions / isolation | CS330-L03 |
| Queue retries / duplicate delivery | SE320-L03 |
| Distributed failures | CS430-L01 |
| Load / capacity diagnosis | CS430-L03 or SE460 |
| Coding-problem discovery | CS360 |
| Production incidents | SE440 or SE490 |
| Team delivery / planning | SE215-L02 |
| Files / bulk ops / scheduling / tenant fairness | SE325 |
| Production page / third-party frontend forensics | SE240-L07 |

Recommend focused review of the relevant material instead of assigning an entire course.

An interview rehearsal can reveal what to study next — that is one of its principal benefits.

## 14. Record keeping

When the user requests it, save a session report under [`sessions/`](sessions/) using [`templates/session-report.md`](templates/session-report.md).

Recommended fields:

- Date and target profile.
- Interview round, mode, and persona.
- Questions or scenarios actually covered.
- Summary of responses and code.
- Competency scores with evidence.
- Important mistakes or unresolved gaps.
- Recommended practice.
- Whether hints or assistance were used.

Do not manufacture completed sessions or scores.

Do not automatically mark curriculum lectures as mastered merely because related questions were answered correctly.

Interview practice and study progress are related but distinct records.

## 15. Invocation examples

Short commands should be sufficient. When the request is clear, begin immediately.

- "Run a realistic HR interview for a senior full-stack role at a Berlin product company."
- "Give me a walkthrough of a 45-minute technical interview for a backend-heavy SaaS company in the Netherlands. Play both interviewer and candidate."
- "Strict technical interview. Senior Node.js, MongoDB, workers, Swedish product company, 45 minutes. Ask one question at a time."
- "Here's the job description and interview invitation. Research the company and build an interview profile based on the available evidence."
- "Guided React debugging interview. Start easy, then increase difficulty based on my performance."
- "Repeat the previous interview in strict mode."
- "Review my performance across the last few interview sessions and identify recurring weaknesses."

When evidence about a particular employer is missing, label the simulation as an **informed approximation** rather than pretending to know the actual questions.

---

## Guiding principle

**The best interview preparation resembles the work and judgment required by the target role.**

It should challenge the candidate enough to uncover weaknesses, but it should not confuse difficulty, theatrical pressure, or obscure questions with realism.

The interviewer is a simulated human participant.

The assessment is a job-relevant learning tool.

The result is better preparation — not a fabricated guarantee of getting hired.
