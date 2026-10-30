# The Modern Software Engineer

**Version 2.0** — a personal computer science refresher and senior interview preparation programme.

**Audience:** Experienced full-stack developer  
**Goal:** Strengthen foundations, deepen architectural understanding, master modern engineering concepts, and prepare for senior software engineering interviews.

This is not a bootcamp, a degree, or a certification programme. It turns practical experience into a coherent model of how computers, applications, networks, databases, infrastructure, and modern AI systems actually work.

**Depth where it matters. Brevity where it doesn't. Curiosity throughout.**

---

## Library layout

```
book/
├── README.md                    ← you are here (philosophy + study order)
├── STUDY-INTENT.md              ← how this library is used (listen-first, mocks)
├── engineering-decision-map.md  ← architecture joints across the catalogue
├── STATUS.md                    ← manuscript vs learning status model
├── curriculum.yaml              ← source of truth (edit this to reshuffle)
├── curriculum.md                ← human-readable course catalogue
├── technology-atlas.md          ← searchable topic / technology index
├── interview-lab/               ← mock interviews (protocol, profiles, sessions)
├── production-cases/            ← diagnostic incident packets (not a course)
├── students/                    ← personal Study Ledgers (per student)
├── tools/                       ← migrate / validate / render / progress
├── CS/                          ← Computer Science courses
├── SE/                          ← Software Engineering courses
└── AI/                          ← Artificial Intelligence courses
```

**3 disciplines · 17 core courses · 91 core lectures** (edition `2.0.0`; most core manuscripts complete, including `CS340`; `SE240-L07` is a planning stub). Active electives add further lecture stubs and manuscripts outside the mandatory core.

Lecture identity: `CS330-L03`. Frontmatter carries `id`, `manuscript`, `edition`, `legacy_ids`, `prev`/`next`.

**Two status tracks** (do not mix them):

1. **Manuscript** — is the text written? (`planned` → `stub` → `draft` → `manuscript` → `revised` → `polished`) + `edition`
2. **Learning** — have *you* studied it? Personal ledger under [`students/`](students/) (`unopened` → … → `fluent`, with `fading` / `encore` for revisits)

**How this library is used for interview prep** (priorities, stages, optional labs): [`STUDY-INTENT.md`](STUDY-INTENT.md) — agents should follow that over assuming a homework-driven degree path.

**Architecture navigation** (how layers and trade-offs connect; links into lectures): [`engineering-decision-map.md`](engineering-decision-map.md). The catalogue is a reference library — not a required completion checklist. Prefer breadth and systems intuition; go deep when mocks or job requirements expose a gap.

Details: [`STATUS.md`](STATUS.md). Topic lookup across the library: [`technology-atlas.md`](technology-atlas.md).

---

## Recommended study order

The catalogue is not a reading sequence. Course numbers describe scope and difficulty, not a rigid calendar.

1. **Foundations** — `CS110` → `CS120` → `CS220` → `CS230` → `CS320`
2. **Application and data engineering** — `SE240` → `SE310` → `SE320` → `CS330` → `CS340`
3. **Advanced systems and production** — `CS430` → `SE330` → `SE340` → `SE440`
4. **Modern AI engineering** — `AI310` → `AI410`
5. **Architecture studio** — `SE490` (five integrated design workshops)

Several courses can be studied in parallel. Studio workshops can be revisited whenever the necessary foundations are in place.

Full course and lecture listings: [`curriculum.md`](curriculum.md).

---

## Educational goals

The catalogue distinguishes three goals:

1. **Foundations** — how software and computing systems work (mostly CS core).
2. **Engineering proficiency** — build, debug, operate, and improve real systems (mostly SE/AI core and deep electives).
3. **Professional literacy** — adjacent disciplines, organizational responsibilities, and how modern software work is coordinated (short orientation electives such as `SE215`).

Breadth should make the learner more capable — not make the curriculum impossible to finish.

## Electives

An elective is a **course you choose to take**, not a separate numbering scheme. Catalogue-only electives stay `type: planned` until stubs exist. Once lecture files are registered they become `type: elective` (still optional).

Three shapes appear in the catalogue:

- **Core education** — mandatory study programme (`type: core`).
- **Specialist electives** — deeper optional courses (for example `CS360`, `SE250`, `CS345`, `CS350`, `SE325`, `SE335`, `SE360`, `SE450`, `SE460`).
- **Short orientation electives** — survey lectures for professional fluency without another full semester (`SE215`; ordinarily ~18–25 minutes spoken per lecture).
- **Production Case Library** — [`production-cases/`](production-cases/README.md): symptom-first incident packets (Mongo, Postgres, Redis, queues, CI/CD) used by studios and Interview Lab — not a numbered course.

Active electives today include `SE215`, `CS360`, `SE250`, `CS345`, `CS350`, `SE325`, `SE335`, `SE360`, `SE450`, and `SE460`. Others (for example `CS370`, `SE350`) remain planned.

**Manuscript priority (stubs first, generate selectively):** `SE250` → `CS345` → `CS350` → `SE335` → `SE360`. Keep foundations; add diagnostic-first electives above them. Do not duplicate `SE325` / `SE460` scopes.

---

## How to study a lecture

**Default for interview refresh:** listen or read the prose (often voice + optional 1.25–1.5×). That counts. Labs and end-of-lecture tasks are **optional reference** — useful inspiration for Interview Lab questions, not mandatory homework. Full priorities and stages: [`STUDY-INTENT.md`](STUDY-INTENT.md).

A serious listen is often **~40–70 minutes @1×** of spoken material (less wall-clock at higher speed). Familiar material can be faster.

Code samples stay in the lecture. They are illustrations: a voice reader skips fenced code, so the paragraphs around each sample have to carry why it is there, what to notice, and what follows. Stop the voice reader at *The spoken lecture ends here* — labs and the glance card are for the screen. A lecture whose point still lives only inside the fences is not listenable yet; the fix is to rewrite the prose, not to remove the code.

Lectures are ordinarily **one file, two progressive parts**:

1. **Part I — Intuition** — short mental model, one story, a few diagrams (often 5–15 minutes)
2. **Part II — Deep Dive** — full mechanisms, trade-offs, then oral prompts / lab / cheatsheet after the spoken end

If Part II starts to blur, return to Part I’s opening picture and narrate one complete journey in your own words before continuing.

**Teaching principles (unchanged from v1):** teach like an excellent lecturer; assume professional experience; open with a real problem; build mental models; explain trade-offs; stay concrete; no padding.

**Manuscript rhythm (authoring):** intuition → deep dive → exploration/lab → challenges → mental model → further reading.  
**Learner rhythm (this programme):** intuition → deep dive (listen/read) → optional cheatsheet glance → **Interview Lab** when ready. Skip labs freely.

---

## Interview preparation (alongside the catalogue)

Knowledge lives in the courses. **Retrieval under hiring pressure** lives in the [Interview Lab](interview-lab/README.md) — the main *active* practice for this programme (profiles, modes, evidence hierarchy). Lecture exercises may feed mock questions; clearing exercise lists does not.

- **Intent / stages:** [`STUDY-INTENT.md`](STUDY-INTENT.md)
- **Protocol:** [`interview-lab/PROTOCOL.md`](interview-lab/PROTOCOL.md)
- **Defaults:** practical European product-company full-stack (P1: Germany / Netherlands / Sweden and similar); algorithm-heavy (P5) only when evidence or you opt in
- **Apply in parallel** with listening once the foundation feels less cold — do not wait for curriculum completion
- **Company-specific** prep when a real invitation/date exists; short DSA bursts only if that process needs them
- **Mocks:** HR and technical simulations; save reports under `interview-lab/sessions/` only if useful

Interview practice does **not** automatically update Study Ledger fluency.

---

## Reshuffling later (do this, not a scavenger hunt)

1. Edit [`curriculum.yaml`](curriculum.yaml) (paths, titles, `legacy_ids`, course membership).
2. `python tools/curriculum_migrate.py --dry-run`
3. `python tools/curriculum_migrate.py --apply` (or `--rewrite-only` if paths already match)
4. `python tools/sync_manuscript_meta.py`
5. `python tools/curriculum_validate.py`
6. `python tools/curriculum_render.py`

Cross-references in prose should use lecture IDs (`CS110-L04`), never bare “Session N”.

## Personal learning tracker

```bash
python tools/progress_init.py --student dskul
python tools/progress_log.py --student dskul --lecture CS230-L08 --action listen --phase studying
python tools/progress_render.py --student dskul
```

History is `students/dskul/activity.yaml` (append events; do not overwrite them). Short-term listen shortlist: `students/dskul/queue.yaml`. Dashboard: `students/dskul/progress.md` (listen queue, encore due, activity calendar, status strip).

---

## Completion

A course is useful when you can explain its ideas in your own words, recognize them in real systems, reason about unfamiliar problems with them, and apply them in interviews or work.

**The curriculum serves the learner. The learner does not serve the curriculum.**
