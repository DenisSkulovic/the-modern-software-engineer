#!/usr/bin/env python3
"""Render a personal Study Ledger dashboard to students/<id>/progress.md."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import yaml

from curriculum_lib import BOOK_ROOT, load_manifest

STUDENTS = BOOK_ROOT / "students"

STATUS_ORDER = [
    "unopened",
    "wandering",
    "studying",
    "labbing",
    "settled",
    "fluent",
    "fading",
    "encore",
]

STATUS_GLYPH = {
    "unopened": "·",
    "wandering": "~",
    "studying": ">",
    "labbing": "*",
    "settled": "✓",
    "fluent": "★",
    "fading": "?",
    "encore": "↻",
}


def parse_day(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value)[:10])


def course_rollup(statuses: list[str]) -> str:
    if not statuses:
        return "empty"
    if any(s in {"fading", "encore"} for s in statuses):
        return "needs_encore"
    if all(s == "fluent" for s in statuses):
        return "fluent"
    if all(s in {"settled", "fluent"} for s in statuses):
        return "settled"
    if all(s == "unopened" for s in statuses):
        return "unopened"
    return "underway"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--student", required=True)
    args = parser.parse_args()

    ledger_path = STUDENTS / args.student / "ledger.yaml"
    if not ledger_path.is_file():
        raise SystemExit(f"Missing {ledger_path} — run progress_init.py first")

    with ledger_path.open(encoding="utf-8") as f:
        ledger = yaml.safe_load(f)

    manifest = load_manifest()
    today = date.today()
    lectures = ledger.get("lectures") or {}
    counts = Counter(e.get("status", "unopened") for e in lectures.values())

    encore_due: list[tuple[str, dict]] = []
    for lid, entry in lectures.items():
        st = entry.get("status")
        due = parse_day(entry.get("next_encore"))
        if st == "fading":
            encore_due.append((lid, entry))
        elif st == "encore":
            encore_due.append((lid, entry))
        elif due and due <= today:
            encore_due.append((lid, entry))

    # Suggested next: first unopened/wandering/studying/labbing in study_order
    suggested: list[str] = []
    code_to_lectures: dict[str, list[str]] = {}
    for course in manifest["courses"]:
        if course.get("type") != "core":
            continue
        ids = [lec["id"] for lec in (course.get("lectures") or [])]
        code_to_lectures[course["code"]] = ids

    for block in manifest.get("study_order") or []:
        for code in block.get("courses") or []:
            for lid in code_to_lectures.get(code, []):
                st = (lectures.get(lid) or {}).get("status", "unopened")
                if st in {"unopened", "wandering", "studying", "labbing", "encore", "fading"}:
                    suggested.append(lid)
                if len(suggested) >= 5:
                    break
            if len(suggested) >= 5:
                break
        if len(suggested) >= 5:
            break

    lines: list[str] = []
    name = ledger.get("display_name") or ledger.get("student") or args.student
    lines.append(f"# Study Ledger — {name}")
    lines.append("")
    lines.append(
        f"**Student:** `{ledger.get('student')}` · "
        f"**Curriculum:** v{ledger.get('curriculum_version')} · "
        f"**Updated:** {ledger.get('updated', today.isoformat())} · "
        f"**Rendered:** {today.isoformat()}"
    )
    lines.append("")
    lines.append(
        "Personal learning tracker (not manuscript status). "
        "Design: [`../../STATUS.md`](../../STATUS.md)."
    )
    lines.append("")
    lines.append("## At a glance")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("| --- | ---: |")
    for st in STATUS_ORDER:
        lines.append(f"| `{st}` {STATUS_GLYPH.get(st, '')} | {counts.get(st, 0)} |")
    lines.append(f"| **Total** | **{sum(counts.values())}** |")
    lines.append("")

    settled_ish = counts.get("settled", 0) + counts.get("fluent", 0)
    total = sum(counts.values()) or 1
    lines.append(
        f"Progress through core lectures (settled+fluent): "
        f"**{settled_ish}/{total}** ({100 * settled_ish // total}%)."
    )
    lines.append("")

    lines.append("## Encore due")
    lines.append("")
    if not encore_due:
        lines.append("_Nothing overdue. Nice._")
    else:
        lines.append("| Lecture | Status | Next encore | Notes |")
        lines.append("| --- | --- | --- | --- |")
        for lid, entry in sorted(
            encore_due,
            key=lambda x: (str(x[1].get("next_encore") or ""), x[0]),
        ):
            lines.append(
                f"| `{lid}` | `{entry.get('status')}` | "
                f"{entry.get('next_encore') or '—'} | "
                f"{(entry.get('notes') or '')[:60]} |"
            )
    lines.append("")

    lines.append("## Suggested next rooms")
    lines.append("")
    if not suggested:
        lines.append("_Study order looks clear — consider electives or fluent maintenance._")
    else:
        for lid in suggested:
            e = lectures[lid]
            lines.append(
                f"- `{lid}` — {e.get('title')} "
                f"(`{e.get('status')}`, confidence {e.get('confidence', 0)})"
            )
    lines.append("")

    lines.append("## Course heat map")
    lines.append("")
    lines.append("| Course | Rollup | Pattern |")
    lines.append("| --- | --- | --- |")
    for block in manifest.get("study_order") or []:
        for code in block.get("courses") or []:
            ids = code_to_lectures.get(code, [])
            statuses = [
                (lectures.get(i) or {}).get("status", "unopened") for i in ids
            ]
            pattern = "".join(STATUS_GLYPH.get(s, "?") for s in statuses)
            lines.append(
                f"| `{code}` | `{course_rollup(statuses)}` | `{pattern}` |"
            )
    lines.append("")
    lines.append(
        "Glyphs: "
        + ", ".join(f"`{STATUS_GLYPH[s]}`={s}" for s in STATUS_ORDER)
    )
    lines.append("")

    lines.append("## Full ledger")
    lines.append("")
    lines.append("| ID | Status | Conf | Passes | Last | Next encore | Notes |")
    lines.append("| --- | --- | ---: | ---: | --- | --- | --- |")
    for lid in sorted(lectures.keys()):
        e = lectures[lid]
        lines.append(
            f"| `{lid}` | `{e.get('status')}` | {e.get('confidence', 0)} | "
            f"{e.get('passes', 0)} | {e.get('last_touched') or '—'} | "
            f"{e.get('next_encore') or '—'} | {(e.get('notes') or '')[:40]} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        f"_Source: [`ledger.yaml`](ledger.yaml). "
        f"Regenerate: `python tools/progress_render.py --student {args.student}`._"
    )

    out = STUDENTS / args.student / "progress.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {out.relative_to(BOOK_ROOT)}")


if __name__ == "__main__":
    main()
