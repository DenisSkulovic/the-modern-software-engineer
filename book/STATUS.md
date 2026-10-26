# Status model — manuscripts vs learning

Two different questions. Keep them apart.

| Track | Asks | Lives in | Shared? |
| --- | --- | --- | --- |
| **Manuscript** | Is this lecture written? How mature is the text? Which edition? | `curriculum.yaml` + lecture frontmatter | Yes — part of the library |
| **Learning** | Have *I* studied it? How solid is it? When should I revisit? | `students/<you>/ledger.yaml` | No — personal per student |

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

### Ledger fields (per lecture)

```yaml
CS110-L01:
  status: studying
  confidence: 2          # 0–5 gut check
  passes: 1              # full serious passes completed
  opened_on: 2026-10-26
  settled_on: null
  last_touched: 2026-10-26
  next_encore: null      # ISO date when a refresh is due
  encore_interval_days: 30
  notes: "Heap vs BST trade-off still fuzzy"
```

### Suggested encore intervals (defaults; override per lecture)

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
│   │   └── ledger.yaml       ← copy me
│   └── dskul/                ← example / primary student
│       ├── ledger.yaml       ← source of truth for learning
│       └── progress.md       ← rendered dashboard (optional commit)
└── tools/
    ├── sync_manuscript_meta.py
    ├── progress_init.py
    └── progress_render.py
```

---

## 4. Workflow cheatsheet

**Authoring a new elective lecture**

1. Add course/lecture to `curriculum.yaml` with `manuscript: planned`
2. Create stub file → `stub` → write → `draft` → `manuscript`
3. `python tools/sync_manuscript_meta.py` then validate/render

**Studying**

1. Copy `students/_template` → `students/<your-id>/` if needed
2. Edit `ledger.yaml` statuses as you go (or bump with notes)
3. `python tools/progress_render.py --student <your-id>`
4. Check **Encore due** on the dashboard before picking tonight’s room
