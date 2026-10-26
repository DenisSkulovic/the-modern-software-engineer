#!/usr/bin/env python3
"""Render curriculum.md from curriculum.yaml."""

from __future__ import annotations

from pathlib import Path

from curriculum_lib import BOOK_ROOT, build_indexes, load_manifest

OUT = BOOK_ROOT / "curriculum.md"


def main() -> None:
    m = load_manifest()
    build_indexes(m)
    lines: list[str] = []
    lines.append(f"# {m['title']} — Course Catalogue")
    lines.append(f"\n**Version:** {m['version']} — {m.get('updated', '')}  ")
    lines.append(
        f"**Default manuscript edition:** `{m.get('default_edition', '2.0.0')}`  "
    )
    lines.append(
        "**Machine-readable source of truth:** [`curriculum.yaml`](curriculum.yaml)  "
    )
    lines.append(
        "**Programme guide / study order:** [`README.md`](README.md)  "
    )
    lines.append(
        "**Status model (manuscript vs learning):** [`STATUS.md`](STATUS.md)  "
    )
    lines.append(
        "**Personal study ledgers:** [`students/`](students/)\n"
    )
    lines.append("---\n")
    lines.append("## Manuscript statuses\n")
    lines.append(
        "Library/content state — not whether you have studied the lecture. "
        "See [`STATUS.md`](STATUS.md).\n"
    )
    ms = m.get("manuscript_statuses") or {
        "planned": "Catalogue only",
        "stub": "Placeholder file",
        "draft": "Incomplete prose",
        "manuscript": "Full lecture",
        "revised": "Rewritten after first manuscript",
        "polished": "Stable for this edition",
    }
    lines.append("| Status | Meaning |")
    lines.append("| --- | --- |")
    for key, meaning in ms.items():
        lines.append(f"| `{key}` | {meaning} |")
    lines.append("")
    lines.append("## Disciplines\n")
    lines.append("| Code | Discipline | Scope |")
    lines.append("| --- | --- | --- |")
    for code, meta in m["disciplines"].items():
        lines.append(f"| {code} | {meta['name']} | {meta['scope']} |")
    lines.append("")
    lines.append("## Course levels\n")
    lines.append("| Level | Meaning |")
    lines.append("| --- | --- |")
    lines.append("| 100 | Foundations and essential concepts |")
    lines.append("| 200 | Core technical mechanisms and engineering techniques |")
    lines.append("| 300 | Advanced applied engineering and specialized systems |")
    lines.append(
        "| 400 | Complex systems, architecture, advanced integration, and capstones |"
    )
    lines.append(
        "| 500 | Reserved for future specialized / research-oriented material |"
    )
    lines.append("")
    lines.append(
        "Lecture IDs look like `CS330-L03`. Electives use the same scheme "
        "(they are courses with `type: planned` or `elective`, not a separate numbering universe).\n"
    )

    core = [c for c in m["courses"] if c.get("type") == "core"]
    planned = [c for c in m["courses"] if c.get("type") == "planned"]

    lines.append("## Core courses (15 · 60 lectures)\n")
    by_disc: dict[str, list] = {"CS": [], "SE": [], "AI": []}
    for c in core:
        by_disc.setdefault(c["discipline"], []).append(c)

    for disc in ("CS", "SE", "AI"):
        dname = m["disciplines"][disc]["name"]
        lines.append(f"### {disc} — {dname}\n")
        for c in by_disc.get(disc, []):
            n = len(c.get("lectures") or [])
            lines.append(
                f"#### {c['code']} — {c['title']}\n"
            )
            lines.append(
                f"{c['level']}-level · {n} lectures · course status `{c.get('status')}` · `{c['dir']}/`\n"
            )
            lines.append("| ID | Lecture | Manuscript | Edition | Legacy |")
            lines.append("| --- | --- | --- | --- | --- |")
            for lec in c.get("lectures") or []:
                legacy = ", ".join(lec.get("legacy_ids") or [])
                lines.append(
                    f"| `{lec['id']}` | {lec['title']} | "
                    f"`{lec.get('manuscript', '—')}` | "
                    f"`{lec.get('edition', '—')}` | `{legacy}` |"
                )
            lines.append("")

    lines.append("## Planned electives\n")
    lines.append(
        "Elective status means optional in the programme — not a different ID scheme. "
        "Each starts with one lecture when written; courses may grow organically.\n"
    )
    lines.append("| Code | Title | Status | Builds on | Notes |")
    lines.append("| --- | --- | --- | --- | --- |")
    for c in planned:
        builds = ", ".join(f"`{x}`" for x in (c.get("builds_on") or [])) or "—"
        notes = c.get("notes") or ""
        lines.append(
            f"| `{c['code']}` | {c['title']} | `{c.get('status', 'planned')}` | {builds} | {notes} |"
        )
    lines.append("")
    lines.append("## Maintenance\n")
    lines.append(
        "1. Edit [`curriculum.yaml`](curriculum.yaml).\n"
        "2. Run `python tools/sync_manuscript_meta.py` after changing manuscript/edition fields.\n"
        "3. Run `python tools/curriculum_migrate.py --dry-run` then `--apply` or `--rewrite-only` for reshuffles.\n"
        "4. Run `python tools/curriculum_validate.py`.\n"
        "5. Re-render this file: `python tools/curriculum_render.py`.\n"
        "6. Personal learning: `python tools/progress_init.py --student <id>` then "
        "`progress_render.py`.\n"
    )
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(BOOK_ROOT)}")


if __name__ == "__main__":
    main()
