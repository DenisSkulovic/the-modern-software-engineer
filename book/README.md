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
├── README.md              ← you are here (philosophy + study order)
├── STATUS.md              ← manuscript vs learning status model
├── curriculum.yaml        ← source of truth (edit this to reshuffle)
├── curriculum.md          ← human-readable course catalogue
├── students/              ← personal Study Ledgers (per student)
├── tools/                 ← migrate / validate / render / progress
├── CS/                    ← Computer Science courses
├── SE/                    ← Software Engineering courses
└── AI/                    ← Artificial Intelligence courses
```

**3 disciplines · 16 core courses · 73 lectures** (most at manuscript status; `CS340` L01–L03 manuscript, L04–L07 still stubbed; edition `2.0.0`).

Lecture identity: `CS330-L03`. Frontmatter carries `id`, `manuscript`, `edition`, `legacy_ids`, `prev`/`next`.

**Two status tracks** (do not mix them):

1. **Manuscript** — is the text written? (`planned` → `stub` → `draft` → `manuscript` → `revised` → `polished`) + `edition`
2. **Learning** — have *you* studied it? Personal ledger under [`students/`](students/) (`unopened` → … → `fluent`, with `fading` / `encore` for revisits)

Details: [`STATUS.md`](STATUS.md).

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

## Electives

An elective is a **course you choose to take**, not a separate numbering scheme. Catalogue-only electives stay `type: planned` until stubs exist. Once lecture files are registered they become `type: elective` (still optional). Active electives today include `CS360`, `SE450`, and `SE460`; others (for example `CS350`, `CS370`) remain planned.

---

## How to study a lecture

Aim for roughly **60–100 minutes** of meaningful work (reading, thinking, optional labs). Familiar material can be faster.

Lectures are ordinarily **one file, two progressive parts** (already in place for `CS230`):

1. **Part I — Intuition** — short mental model, one story, a few diagrams (often 5–15 minutes)
2. **Part II — Deep Dive** — full mechanisms, trade-offs, oral exam, then lab / cheatsheet after the spoken end

If Part II starts to blur, return to Part I’s opening picture and narrate one complete journey in your own words before continuing.

**Teaching principles (unchanged from v1):** teach like an excellent lecturer; assume professional experience; open with a real problem; build mental models; explain trade-offs; stay concrete; no padding.

**Typical rhythm:** intuition → deep dive → exploration/lab → challenges → mental model → further reading.

---

## Interview preparation (alongside the catalogue)

- **Technical recall** (10–15 min): explain concepts without notes.
- **Coding** (20–30 min, a few times weekly): practical problems without AI assistance.
- **Senior discussion** (periodic): design systems, diagnose incidents, defend trade-offs out loud.

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
# edit students/dskul/ledger.yaml as you study
python tools/progress_render.py --student dskul
```

Dashboard: `students/dskul/progress.md` (encore due, heat map, suggested next rooms).

---

## Completion

A course is useful when you can explain its ideas in your own words, recognize them in real systems, reason about unfamiliar problems with them, and apply them in interviews or work.

**The curriculum serves the learner. The learner does not serve the curriculum.**
