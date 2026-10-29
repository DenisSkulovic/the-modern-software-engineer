# Curriculum tools

Requires Python 3 + `pyyaml` (`pip install pyyaml`).

| Script | Purpose |
| --- | --- |
| `curriculum_migrate.py --dry-run` | Print old→new map (one-shot migration helper) |
| `curriculum_migrate.py --apply` | Move/rename, inject frontmatter, rewrite refs |
| `curriculum_migrate.py --rewrite-only` | Re-transform files already at new paths |
| `sync_manuscript_meta.py` | Ensure `manuscript` + `edition` in yaml; sync frontmatter; course rollups |
| `curriculum_validate.py` | Manifest ↔ disk for `core` and `elective`; manuscript/edition; no bare `Session N` / old codes |
| `curriculum_render.py` | Regenerate `../curriculum.md` (core, active electives, planned electives) |
| `progress_init.py --student <id>` | Create a profile and an empty activity log under `students/<id>/` |
| `progress_log.py --student <id> --lecture <id> --action listen` | Append one study event. `--migrate-ledger` copies an old snapshot once |
| `progress_render.py --student <id>` | Fold the log (+ optional `queue.yaml`) into `students/<id>/progress.md` |

Shared logic: `curriculum_lib.py`, `progress_lib.py`. Status design: [`../STATUS.md`](../STATUS.md).
