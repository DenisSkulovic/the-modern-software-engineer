# Study Ledgers (personal)

The course catalogue is shared. **Learning progress is not.**

Each student (or future clone of yourself-before-an-interview) gets a folder:

```
students/
├── _template/
│   ├── ledger.yaml         ← profile only (no lecture snapshot)
│   └── activity.yaml       ← empty log
└── <student-id>/
    ├── ledger.yaml         ← who you are, status vocabulary, encore intervals
    ├── activity.yaml       ← append-only history; this is the source of truth
    └── progress.md         ← generated dashboard
```

Do not edit past events, and do not keep a per-lecture status map. A later session is a new event. Current phase, confidence, and pass counts are a fold of the log.

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
- **Encore due** (spaced refresh, derived from the log)
- **Course status strip** — where each lecture stands now
- **Activity calendar** and **course by week** — when the work happened
- **Recent events** — the log itself, newest day first
- suggested next rooms from the recommended study order

## Learning statuses

See [`../STATUS.md`](../STATUS.md) for the full model.

Short form: `unopened` → `wandering` → `studying` → `labbing` → `settled` → `fluent`, with `fading` / `encore` for revisits. Those words are a `phase` on an event, not a cell you overwrite.

## Etiquette

- Do not put personal notes in lecture manuscripts or `curriculum.yaml`.
- Ledgers may be gitignored per preference; the template should stay in repo.
- Multiple ledgers are fine (`dskul`, `interview-2027`, …).
