# Curriculum tools

Requires Python 3 + `pyyaml` (`pip install pyyaml`).

| Script | Purpose |
| --- | --- |
| `curriculum_migrate.py --dry-run` | Print old→new map (one-shot migration helper) |
| `curriculum_migrate.py --apply` | Move/rename, inject frontmatter, rewrite refs |
| `curriculum_migrate.py --rewrite-only` | Re-transform files already at new paths |
| `sync_manuscript_meta.py` | Ensure `manuscript` + `edition` in yaml; sync frontmatter; course rollups |
| `curriculum_validate.py` | Manifest ↔ disk; manuscript/edition; no bare `Session N` / old codes in bodies |
| `curriculum_render.py` | Regenerate `../curriculum.md` from yaml |
| `progress_init.py --student <id>` | Create personal Study Ledger under `students/<id>/` |
| `progress_render.py --student <id>` | Render `students/<id>/progress.md` dashboard |

Shared logic: `curriculum_lib.py`. Status design: [`../STATUS.md`](../STATUS.md).
