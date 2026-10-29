# Status model — manuscripts vs learning

Two different questions. Keep them apart.

| Track | Asks | Lives in | Shared? |
| --- | --- | --- | --- |
| **Manuscript** | Is this lecture written? How mature is the text? Which edition? | `curriculum.yaml` + lecture frontmatter | Yes — part of the library |
| **Learning** | Have *I* studied it? How solid is it? When should I revisit? | `students/<you>/activity.yaml` | No — personal per student |

---

## 1. Manuscript status (library / content)

A lecture’s **production** state. Independent of whether anyone has studied it.

| Status | Meaning |
| --- | --- |
| `planned` | In the catalogue only — no file yet |
| `stub` | File exists; title/outline only |
| `draft` | Substantial prose, still incomplete |
| `manuscript` | Full lecture generated to programme standard |
| `revised` | Materially rewritten after the first manuscript |
| `polished` | Stable for the current major edition; prefer not to churn |

**Edition** is a semver-ish content wave, not a git tag:

- `edition: "2.0.0"` — written (or migrated) for curriculum v2.0
- Bump **patch** for typo/link fixes (`2.0.1`)
- Bump **minor** for substantial section rewrites without catalogue renumbering (`2.1.0`)
- Bump **major** with catalogue reshuffles that change IDs (`3.0.0`)

Course-level `status` in yaml is a rollup:

| Course status | Meaning |
| --- | --- |
| `planned` | No lectures written |
| `in_progress` | Some lectures stub/draft/manuscript, not all polished |
| `complete` | Every listed lecture is at least `manuscript` |
| `stable` | Every listed lecture is `polished` |

Frontmatter mirrors the manifest (kept in sync by tools):

```yaml
---
id: CS110-L01
…
manuscript: manuscript
edition: "2.0.0"
---
```

---

## 2. Learning status (personal Study Ledger)

Each student keeps a **Study Ledger** — a personal atelier log, not part of the published catalogue.

Metaphor: the lectures are museum rooms. Your ledger records how you walked them.

| Status | Meaning | Typical next step |
| --- | --- | --- |
| `unopened` | Never started | Open when the study order (or curiosity) says so |
| `wandering` | Skimmed / half-attention pass | Return for a serious `studying` pass |
| `studying` | Active first serious read | Finish prose → `labbing` |
| `labbing` | Working exercises, challenges, labs | Pocket the mental model → `settled` |
| `settled` | Finished once; sticky-note mental model held | Use in work/interviews; schedule encore |
| `fluent` | Can explain cold, teach, or defend in interview | Maintain with light encored |
| `fading` | Confidence dropping; details blurring | Promote to `encore` soon |
| `encore` | Scheduled revisit (spaced refresh) | Re-read hot spots → back to `settled`/`fluent` |

### Activity log (source of truth)

Each thing you do is one event in `activity.yaml`. A later session is a new event. It does not overwrite the earlier one, and nothing is stored as a running counter.

```yaml
- at: 2026-10-27          # calendar day; do not invent a clock time
  lecture: CS230-L06
  action: listen          # listen | read | skim | lab | oral | review | note
  phase: studying         # judgment after this session; vocabulary above
  confidence: 2           # optional 0–5
  note: "Full voice listen-through; one session."
```

`source: backfill` appears only on rows copied out of the old per-lecture snapshot.

```bash
python tools/progress_log.py --student dskul \
  --lecture CS230-L08 --action listen --phase studying --confidence 2 \
  --note "Full voice listen-through; one session."
```

`--at YYYY-MM-DD` records a past day. Unknown lecture ids are rejected. The tool appends; it has no edit or delete. A correction is a new event.

`ledger.yaml` is the profile only: who the student is, the status vocabulary, and the encore intervals. It has no per-lecture map.

### What the dashboard folds

`progress_render.py` queries the log. It does not read a snapshot you maintain by hand.

- no events → `unopened`
- phase and confidence → the latest event that set them
- passes → count of `listen`, `read`, `skim`, `lab`, `oral`, and `review` (`note` is kept and not counted)
- opened / last touched → earliest and latest `at`
- next encore → only for `settled`, `fluent`, `fading`, or `encore`: the date of the event that set that phase, plus the interval below

The **course status strip** is that current phase, one glyph per lecture. The **activity calendar** and **course by week** table count the events over time. **Recent events** lists the log, newest day first, notes included.

### Suggested encore intervals (defaults; applied when rendering)

| After reaching | First encore | Then |
| --- | --- | --- |
| `settled` | ~21–30 days | double if still solid |
| `fluent` | ~60–90 days | or before a relevant interview |
| `fading` | now / this week | short targeted re-read |
| `encore` | the `next_encore` date | mark `settled` or `fluent` again |

### Course rollups (computed when rendering)

- **Unopened** — every lecture `unopened`
- **Underway** — any `wandering`/`studying`/`labbing`/`encore`
- **Settled** — all lectures ≥ `settled` (and none `fading`/`encore`)
- **Fluent** — all lectures `fluent`
- **Needs encore** — any `fading` or overdue `encore`

---

## 3. Where files live

```
book/
├── STATUS.md                 ← this design
├── curriculum.yaml           ← manuscript + edition (shared)
├── students/
│   ├── README.md             ← how to use ledgers
│   ├── _template/
│   │   ├── ledger.yaml       ← profile only
│   │   ├── activity.yaml     ← empty log
│   │   └── queue.yaml        ← optional curated short-term listen queue
│   └── dskul/                ← example / primary student
│       ├── ledger.yaml       ← profile (not a snapshot of lectures)
│       ├── activity.yaml     ← append-only learning history
│       ├── queue.yaml        ← curated next listens (mood/mode, not calendar)
│       └── progress.md       ← rendered dashboard (optional commit)
└── tools/
    ├── sync_manuscript_meta.py
    ├── progress_lib.py
    ├── progress_init.py
    ├── progress_log.py
    └── progress_render.py
```

---

## 4. Workflow cheatsheet

**Authoring a new elective lecture**

1. Promote the course from `type: planned` to `type: elective` when stubs land (do not mark it `core`)
2. Add lecture entries in `curriculum.yaml` with `manuscript: stub`
3. Create stub files → write → `draft` → `manuscript`
4. `python tools/sync_manuscript_meta.py` then validate/render (validator covers core **and** elective)

**Studying**

1. `python tools/progress_init.py --student <your-id>` if the folder does not exist yet
2. Keep a short curated [`students/<id>/queue.yaml`](students/_template/queue.yaml) for the current stretch (interview refresh listens, etc.) — not a day-by-day schedule
3. Append what you did: `python tools/progress_log.py --student <your-id> --lecture <id> --action listen --phase studying`
4. `python tools/progress_render.py --student <your-id>`
5. Check **Listen queue**, **Encore due**, and the activity calendar before picking tonight’s room

Listening / reading is enough for an interview refresh pass. Labs (`labbing`) are optional unless you want them. Mock interviews in [`interview-lab/`](interview-lab/README.md) are how “exposed” becomes “interview-ready.”

**Interview practice**

Mock interviews are **not** a curriculum course and do not share manuscript/learning statuses. See [`interview-lab/`](interview-lab/README.md). Session reports are optional archives; they do not mark lectures fluent.

**Production cases**

Symptom-first incident packets live in [`production-cases/`](production-cases/README.md). They are practice artifacts for diagnostic electives (`CS345`, `CS350`, `SE335`, `SE360`) and Interview Lab — not lectures and not ledger entries unless you choose to log a personal note.
