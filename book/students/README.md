# Study Ledgers (personal)

The course catalogue is shared. **Learning progress is not.**

Each student (or future clone of yourself-before-an-interview) gets a folder:

```
students/
├── _template/
│   ├── ledger.yaml         ← profile only (no lecture snapshot)
│   ├── activity.yaml       ← empty lecture log
│   ├── exam-attempts.yaml  ← empty course-exam log
│   └── queue.yaml          ← optional curated short-term listen queue
└── <student-id>/
    ├── ledger.yaml         ← who you are, status vocabulary, encore intervals
    ├── activity.yaml       ← append-only lecture history; source of truth for phases
    ├── exam-attempts.yaml  ← append-only course-exam history (qualitative)
    ├── queue.yaml          ← curated next listens for the current stretch
    └── progress.md         ← generated dashboard
```

Do not edit past events, and do not keep a per-lecture status map. A later session is a new event. Current phase, confidence, and pass counts are a fold of the lecture log.

`queue.yaml` is the short-term study plan: a shuffled shortlist of lectures with preferred mode (`audio` / `screen` / `either`) and a one-line why. It is not a calendar and not Duolingo. Edit it when your stretch goal changes. A logged pass marks the matching queue item done on the next render.

`exam-attempts.yaml` records optional course-examination sessions (complete or partial). It never invents lecture listens and never stores grades. Protocol: [`../EXAMINATIONS.md`](../EXAMINATIONS.md).

## Quick start

```bash
python tools/progress_init.py --student dskul
python tools/progress_log.py --student dskul \
  --lecture CS230-L08 --action listen --phase studying --confidence 2 \
  --note "Full voice listen-through; one session."
python tools/progress_render.py --student dskul
```

`--at YYYY-MM-DD` records a past day. Actions: `listen`, `read`, `skim`, `lab`, `oral`, `review`, `note`.

Open `progress.md` for:

- counts by current phase
- **Listen queue** — curated next listens from `queue.yaml` (falls back to catalogue study order if missing)
- **Encore due** (spaced refresh, derived from the log)
- **Recent course examinations** — qualitative exam attempts (if any)
- **Course status strip** — where each lecture stands now
- **Activity calendar** and **course by week** — when the work happened
- **Recent events** — the lecture log itself, newest day first

## Learning statuses

See [`../STATUS.md`](../STATUS.md) for the full model. Programme priorities: [`../STUDY-INTENT.md`](../STUDY-INTENT.md).

Short form: `unopened` → `wandering` → `studying` → `labbing` → `settled` → `fluent`, with `fading` / `encore` for revisits. Those words are a `phase` on an event, not a cell you overwrite.

In the current interview-refresh use of this library, a listen logged as `studying` is a successful expose. `labbing` is optional. Interview Lab is the main interactive practice; lecture exercises and course exams are reference / retrieval practice, not homework.

## Etiquette

- Do not put personal notes in lecture manuscripts or `curriculum.yaml`.
- Ledgers may be gitignored per preference; the template should stay in repo.
- Multiple ledgers are fine (`dskul`, `interview-2027`, …).
- Mock interviews belong in [`../interview-lab/`](../interview-lab/) (protocol + session reports). Do not treat a good mock answer as automatic lecture mastery; optionally log a `note` event if you want interview-practice days on the calendar.
- Course exams belong under each course’s `exams/` folder; attempts go in `exam-attempts.yaml`, never as fake lecture activity.
