# Study Ledgers (personal)

The course catalogue is shared. **Learning progress is not.**

Each student (or future clone of yourself-before-an-interview) gets a folder:

```
students/
├── _template/ledger.yaml   ← copy this
└── <student-id>/
    ├── ledger.yaml         ← edit this
    └── progress.md         ← generated dashboard
```

## Quick start

```bash
python tools/progress_init.py --student dskul
# edit students/dskul/ledger.yaml as you study
python tools/progress_render.py --student dskul
```

Open `progress.md` for:

- counts by learning status
- **Encore due** (spaced refresh)
- per-course heat map
- suggested next rooms from the recommended study order

## Learning statuses

See [`../STATUS.md`](../STATUS.md) for the full model.

Short form: `unopened` → `wandering` → `studying` → `labbing` → `settled` → `fluent`, with `fading` / `encore` for revisits.

## Etiquette

- Do not put personal notes in lecture manuscripts or `curriculum.yaml`.
- Ledgers may be gitignored per preference; the template should stay in repo.
- Multiple ledgers are fine (`dskul`, `interview-2027`, …).
