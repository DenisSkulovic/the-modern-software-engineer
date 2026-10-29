# Candidate baseline

Assumptions for Interview Lab simulations. Keep this file **neutral and public-repo safe**: useful for agents, unremarkable if a hiring reader opens GitHub.

Prefer the candidate’s public CV / LinkedIn and what they say in-session over inventing detail. Do not invent employers, dates, metrics, motivations, salary, visa, or notice period.

---

## Profile (high level)

- Senior software engineer — full-stack, with substantial backend and recent AI / agent-systems work
- Strongest day-to-day: TypeScript, Node.js, product-minded system design
- Target practice market for this lab: **European product companies** (see below)
- Calibrate seniority and depth to the **job under discussion** (typical senior IC / lead scope — not Staff-by-default)

## Stack (working familiarity unless noted)

- **Languages / runtimes:** TypeScript, JavaScript, SQL, Python
- **Backend & data:** Node.js, NestJS, REST, WebSockets, MongoDB, PostgreSQL, DynamoDB, Redis, async workflows, integrations, payment systems (e.g. Stripe)
- **Frontend:** Vue and React / Next.js in production contexts; Vue history is deeper — use `SE250` when a session needs React-specific refresh
- **AI / agentic:** LLM APIs, tool/agent orchestration, prompt and context architecture, retrieval, evaluation-minded iteration, orchestrator-style designs
- **Delivery:** GCP, AWS, Docker, Temporal, Nx, Jenkins/CI, Playwright and automated tests

Do not assume expert depth in every tool named on a JD.

## Experience shape (for story prompts)

Use categories, not a private CV dump. Pull specifics from what the candidate volunteers or from their public materials:

- End-to-end product ownership (including booking / payment style workflows)
- Security / risk-product engineering
- Platform and developer-experience improvements (monorepo, CI feedback, E2E)
- Technical lead ownership on AI / agent platform work
- Side projects that combine deterministic application state with LLM behavior

### Experience types

| Kind | Meaning |
| --- | --- |
| Direct production | Built / owned / operated in real work |
| Conceptual / studied | From this curriculum or reading — not claimed as years of ownership |
| Interview-exposed | Seen in past hiring processes |
| Side project | Personal/engineering project, not employer production |

## Hiring participation

Has taken part in hiring interviews as a panel / interviewer contributor. Not framed as hiring-manager or process owner unless they say so.

## Past interview formats (calibration only)

Formats already faced (shape only — not the default market):

- Debugging an unfamiliar React application
- Compact React + FastAPI + nginx + Docker Compose style exercise
- PHP/Symfony take-home discussion and code review
- Backend discussion: sync request handling, queues, concurrency, service architecture
- Explaining real projects, decisions, and trade-offs

```text
(none logged yet beyond the list above)
```

## Target markets (this lab’s default)

- Germany / DACH, Netherlands, Sweden / Nordics, and similar EU product teams
- Remote-first EU when the invitation says so
- **Not the simulation default:** Israeli/Tel Aviv hiring conventions, FAANG LeetCode rituals, or algorithm gauntlets — unless the user or evidence asks for that scenario

Past employers may span geographies; default **mock market** is still European product engineering.

## Notes for simulators

- Prefer concrete ownership and trade-offs over slogan answers
- Allow “I haven’t run that in production; here’s how I’d reason / what I studied”
- Prefer simpler correct designs over theatre-scale architecture unless the role demands it
- EU HR may touch logistics (remote, relocation, right-to-work, language) — ask; don’t invent drama
- Use AI/agent depth when the JD warrants it; don’t force every mock into LLM-land
- Keep written notes in this repo professional; put highly personal prep commentary in private chat, not in committed files
