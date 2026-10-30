#!/usr/bin/env python3
"""Render a study dashboard from the activity log.

Current status is a fold of activity.yaml. The course strip is that fold.
The calendar and course-by-week tables are counts over the same events.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta

from curriculum_lib import BOOK_ROOT, load_manifest
from progress_lib import (
    PASS_ACTIONS,
    PHASES,
    STUDENTS,
    activity_path,
    course_of,
    events_by_lecture,
    fold_core,
    heat_cell,
    intervals_from,
    iso_week_label,
    lecture_index,
    ledger_path,
    load_events,
    load_exam_attempts,
    load_narrative_listens,
    load_queue,
    load_yaml,
    md_cell,
    normalize_queue_item,
    parse_day,
    queue_item_state,
    week_start,
)

STATUS_ORDER = list(PHASES)

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

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


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


def show_day(value) -> str:
    day = parse_day(value)
    return day.isoformat() if day else "—"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--student", required=True)
    args = parser.parse_args()

    ledger_file = ledger_path(args.student)
    if not ledger_file.is_file():
        raise SystemExit(f"Missing {ledger_file} — run progress_init.py first")
    activity_file = activity_path(args.student)
    if not activity_file.is_file():
        raise SystemExit(
            f"Missing {activity_file} — run progress_log.py --migrate-ledger "
            "or progress_init.py"
        )

    ledger = load_yaml(ledger_file)
    events = load_events(activity_file)
    if ledger.get("lectures") and not events:
        raise SystemExit(
            "ledger.yaml still has a lectures snapshot and the activity log is empty. "
            f"Run: python tools/progress_log.py --student {args.student} --migrate-ledger"
        )
    if ledger.get("lectures"):
        print(
            "warning: ledger.yaml lectures map is ignored; activity.yaml is the source of truth"
        )

    manifest = load_manifest()
    today = date.today()
    intervals = intervals_from(ledger)
    lectures = fold_core(events, manifest, intervals)
    catalog = lecture_index(manifest)
    counts = Counter(e.get("status", "unopened") for e in lectures.values())

    encore_due: list[tuple[str, dict]] = []
    for lid, entry in lectures.items():
        st = entry.get("status")
        due = parse_day(entry.get("next_encore"))
        if st == "fading" or st == "encore" or (due and due <= today):
            encore_due.append((lid, entry))

    code_to_lectures: dict[str, list[str]] = {}
    for course in manifest["courses"]:
        if course.get("type") != "core":
            continue
        ids = [lec["id"] for lec in (course.get("lectures") or [])]
        code_to_lectures[course["code"]] = ids

    queue = load_queue(args.student)
    by_lecture = events_by_lecture(events)

    # Fallback only when there is no curated queue: walk catalogue study_order.
    suggested: list[str] = []
    if queue is None:
        for block in manifest.get("study_order") or []:
            for code in block.get("courses") or []:
                for lid in code_to_lectures.get(code, []):
                    st = (lectures.get(lid) or {}).get("status", "unopened")
                    if st in {
                        "unopened",
                        "wandering",
                        "studying",
                        "labbing",
                        "encore",
                        "fading",
                    }:
                        suggested.append(lid)
                    if len(suggested) >= 5:
                        break
                if len(suggested) >= 5:
                    break
            if len(suggested) >= 5:
                break

    latest_event = max((e["at"] for e in events), default=None)
    updated = parse_day(ledger.get("updated"))
    if latest_event and (updated is None or latest_event > updated):
        updated = latest_event

    lines: list[str] = []
    name = ledger.get("display_name") or ledger.get("student") or args.student
    lines.append(f"# Study Ledger — {name}")
    lines.append("")
    lines.append(
        f"**Student:** `{ledger.get('student')}` · "
        f"**Curriculum:** v{ledger.get('curriculum_version')} · "
        f"**Updated:** {show_day(updated)} · "
        f"**Rendered:** {today.isoformat()}"
    )
    lines.append("")
    lines.append(
        "Personal learning tracker (not manuscript status). "
        "Lecture history is the append-only [`activity.yaml`](activity.yaml); "
        "course exams are [`exam-attempts.yaml`](exam-attempts.yaml); "
        "stories are [`narrative-listens.yaml`](narrative-listens.yaml). "
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
    exposed = sum(1 for e in lectures.values() if (e.get("passes") or 0) > 0)
    total = sum(counts.values()) or 1
    lines.append(
        f"Exposed (any pass logged): **{exposed}/{total}**. "
        f"Settled+fluent: **{settled_ish}/{total}** "
        f"({100 * settled_ish // total}%) — optional for a listen-first refresh."
    )
    lines.append("")
    lines.append(
        "Counts cover every core lecture currently in the catalogue. "
        "A lecture with no events is `unopened`. Electives appear in the queue and activity log."
    )
    lines.append("")

    append_listen_queue(lines, queue, by_lecture, catalog, lectures, suggested)

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
                f"{show_day(entry.get('next_encore'))} | "
                f"{md_cell(entry.get('notes') or '', 60)} |"
            )
    lines.append("")

    exam_attempts = load_exam_attempts(args.student)
    append_exam_attempts(lines, exam_attempts)

    narrative_listens = load_narrative_listens(args.student)
    append_narrative_listens(lines, narrative_listens)

    lines.append("## Course status strip")
    lines.append("")
    lines.append(
        "Current phase of each lecture, in catalogue order. "
        "This is not a timeline — the calendar below is."
    )
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

    append_calendar(lines, events, today)
    append_course_weeks(lines, events, catalog, manifest)
    append_recent(lines, events, catalog)

    lines.append("## Full ledger")
    lines.append("")
    lines.append(
        "Folded snapshot. Passes count listen, read, skim, lab, oral, and review events. "
        "The note is the latest one; earlier notes stay in the log."
    )
    lines.append("")
    lines.append("| ID | Status | Conf | Passes | Last | Next encore | Notes |")
    lines.append("| --- | --- | ---: | ---: | --- | --- | --- |")
    for lid in sorted(lectures.keys()):
        e = lectures[lid]
        lines.append(
            f"| `{lid}` | `{e.get('status')}` | {e.get('confidence', 0)} | "
            f"{e.get('passes', 0)} | {show_day(e.get('last_touched'))} | "
            f"{show_day(e.get('next_encore'))} | {md_cell(e.get('notes') or '', 40)} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "_Source: [`activity.yaml`](activity.yaml), "
        "[`exam-attempts.yaml`](exam-attempts.yaml), "
        "[`narrative-listens.yaml`](narrative-listens.yaml), "
        "profile [`ledger.yaml`](ledger.yaml). "
        f"Regenerate: `python tools/progress_render.py --student {args.student}`._"
    )

    out = STUDENTS / args.student / "progress.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out.relative_to(BOOK_ROOT)}")


def append_exam_attempts(lines: list[str], attempts: list[dict]) -> None:
    lines.append("## Recent course examinations")
    lines.append("")
    lines.append(
        "Qualitative history only — not grades. "
        "Does not change lecture phases. Protocol: [`../../EXAMINATIONS.md`](../../EXAMINATIONS.md)."
    )
    lines.append("")
    if not attempts:
        lines.append(
            "_No exam attempts yet. Append to [`exam-attempts.yaml`](exam-attempts.yaml) when useful._"
        )
        lines.append("")
        return
    lines.append("| When | Exam | Mode | Outcome | Next |")
    lines.append("| --- | --- | --- | --- | --- |")
    for entry in attempts:
        exam = f"`{entry['exam']}`"
        if entry.get("title"):
            exam += f" {md_cell(entry['title'], 36)}"
        lines.append(
            f"| {entry['at'].isoformat()} | {exam} | `{entry.get('mode') or '—'}` | "
            f"{md_cell(entry.get('outcome') or '', 72)} | "
            f"{md_cell(entry.get('next') or '', 56)} |"
        )
    lines.append("")


def append_narrative_listens(lines: list[str], listens: list[dict]) -> None:
    lines.append("## Recent narrative stories")
    lines.append("")
    lines.append(
        "Optional audio stories — not lecture events. "
        "Catalogue: [`../../narrative-cases/README.md`](../../narrative-cases/README.md)."
    )
    lines.append("")
    if not listens:
        lines.append(
            "_No story listens yet. Append to [`narrative-listens.yaml`](narrative-listens.yaml) when useful._"
        )
        lines.append("")
        return
    lines.append("| When | Story | Shelf | Note |")
    lines.append("| --- | --- | --- | --- |")
    for entry in listens:
        story = f"`{entry['story']}`"
        if entry.get("title"):
            story += f" {md_cell(entry['title'], 40)}"
        shelf = entry.get("shelf") or "—"
        lines.append(
            f"| {entry['at'].isoformat()} | {story} | {shelf} | "
            f"{md_cell(entry.get('note') or '', 72)} |"
        )
    lines.append("")


def append_listen_queue(
    lines: list[str],
    queue: dict | None,
    by_lecture: dict,
    catalog: dict,
    lectures: dict,
    suggested: list[str],
) -> None:
    lines.append("## Listen queue")
    lines.append("")

    if queue is None:
        lines.append(
            "_No curated [`queue.yaml`](queue.yaml). "
            "Falling back to catalogue study order — add a queue for interview-focused picks._"
        )
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
        return

    goal = " ".join((queue.get("goal") or "").split())
    if goal:
        lines.append(goal)
        lines.append("")

    updated = parse_day(queue.get("updated"))
    if updated:
        lines.append(f"_Queue updated {updated.isoformat()}. Not a calendar — pick by mood/mode._")
        lines.append("")

    walk = queue.get("walk_pack") or []
    items = queue.get("items") or []
    overflow = queue.get("overflow") or []
    if not walk and not items and not overflow:
        lines.append("_Queue is empty — add lectures to `queue.yaml`._")
        lines.append("")
        return

    def render_section(title: str, raw_items: list) -> tuple[int, int]:
        lines.append(f"### {title}")
        lines.append("")
        if not raw_items:
            lines.append("_None._")
            lines.append("")
            return 0, 0
        lines.append("| # | State | Mode | Lecture | Why |")
        lines.append("| ---: | --- | --- | --- | --- |")
        open_n = 0
        done_n = 0
        for i, raw in enumerate(raw_items, start=1):
            item = normalize_queue_item(raw, where=f"queue {title} item {i}")
            state = queue_item_state(item, by_lecture)
            if state == "open":
                open_n += 1
                glyph = "○"
            elif state == "skipped":
                glyph = "—"
            else:
                done_n += 1
                glyph = "●"
            meta = catalog.get(item["lecture"]) or {}
            title_text = meta.get("title") or ""
            lecture_cell = f"`{item['lecture']}`"
            if title_text:
                lecture_cell += f" {md_cell(title_text, 42)}"
            why = item.get("why") or ""
            approx = raw.get("approx_min_at_1_5x") if isinstance(raw, dict) else None
            if approx is not None:
                why = f"~{approx}m@1.5× — {why}" if why else f"~{approx}m@1.5×"
            lines.append(
                f"| {i} | {glyph} `{state}` | `{item['mode']}` | "
                f"{lecture_cell} | {md_cell(why, 72)} |"
            )
        lines.append("")
        return open_n, done_n

    open_walk, done_walk = render_section("Walk pack (audio-first)", walk)
    open_main, done_main = render_section("Priority listens", items)
    open_over, done_over = render_section("Overflow (extra appetite)", overflow)
    open_n = open_walk + open_main + open_over
    done_n = done_walk + done_main + done_over
    total = len(walk) + len(items) + len(overflow)
    lines.append(
        f"{done_n} done · {open_n} open · {total} listed. "
        "Glyphs: `○` open, `●` done (logged pass or `status: done`), `—` skipped."
    )
    lines.append("")
    lines.append(
        "Edit [`queue.yaml`](queue.yaml) to reshuffle. "
        "Logging a listen/read/skim marks the matching item done on next render."
    )
    lines.append("")


def append_calendar(lines: list[str], events: list[dict], today: date) -> None:
    lines.append("## Activity calendar")
    lines.append("")
    if not events:
        lines.append("_No events yet._")
        lines.append("")
        return

    per_day: Counter[date] = Counter(e["at"] for e in events)
    first = min(per_day)
    last = max(max(per_day), today)
    lines.append(
        "Each cell is how many events fell on that day. "
        "The glyph is intensity; the digit is the count."
    )
    lines.append("")
    lines.append("| Week of | " + " | ".join(WEEKDAYS) + " |")
    lines.append("| --- | " + " | ".join("---" for _ in WEEKDAYS) + " |")
    monday = week_start(first)
    end_monday = week_start(last)
    while monday <= end_monday:
        cells = []
        for offset in range(7):
            cells.append(heat_cell(per_day.get(monday + timedelta(days=offset), 0)))
        lines.append(f"| {monday.isoformat()} | " + " | ".join(cells) + " |")
        monday += timedelta(days=7)
    lines.append("")
    lines.append(
        "Intensity: `·` 0, `░` 1, `▒` 2, `▓` 3–4, `█` 5+."
    )
    active_days = sum(1 for n in per_day.values() if n)
    lines.append("")
    lines.append(
        f"{len(events)} events across {active_days} days, "
        f"from {first.isoformat()}."
    )
    lines.append("")


def append_course_weeks(lines: list[str], events: list[dict], catalog: dict, manifest: dict) -> None:
    lines.append("## Course by week")
    lines.append("")
    sessions = [e for e in events if e["action"] in PASS_ACTIONS]
    if not events:
        lines.append("_No events yet._")
        lines.append("")
        return

    weeks = sorted({week_start(e["at"]) for e in events})
    counts: dict[str, Counter] = defaultdict(Counter)
    for event in sessions:
        counts[course_of(event["lecture"], catalog)][week_start(event["at"])] += 1

    order: list[str] = []
    seen: set[str] = set()
    for block in manifest.get("study_order") or []:
        for code in block.get("courses") or []:
            if code in counts and code not in seen:
                order.append(code)
                seen.add(code)
    for code in sorted(counts):
        if code not in seen:
            order.append(code)

    if not order:
        lines.append("_Events so far are notes only — no listen, read, lab, or review sessions._")
        lines.append("")
        return

    headers = [iso_week_label(w) for w in weeks]
    lines.append(
        "Session counts per course (listen, read, skim, lab, oral, review). "
        "`note` events stay in the log and are omitted here."
    )
    lines.append("")
    lines.append("| Course | " + " | ".join(headers) + " |")
    lines.append("| --- | " + " | ".join("---:" for _ in headers) + " |")
    for code in order:
        cells = [str(counts[code].get(w, 0)) for w in weeks]
        lines.append(f"| `{code}` | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append(
        "Week labels are ISO weeks. "
        + ", ".join(f"{iso_week_label(w)} starts {w.isoformat()}" for w in weeks)
        + "."
    )
    lines.append("")


def append_recent(lines: list[str], events: list[dict], catalog: dict) -> None:
    lines.append("## Recent events")
    lines.append("")
    if not events:
        lines.append("_No events yet._")
        lines.append("")
        return
    lines.append(
        "Newest day first. A later session does not replace an earlier one."
    )
    lines.append("")
    lines.append("| When | Lecture | Action | Phase | Conf | Note |")
    lines.append("| --- | --- | --- | --- | ---: | --- |")
    ordered = sorted(events, key=lambda e: (e["at"], e.get("_i", 0)), reverse=True)
    for event in ordered:
        title = (catalog.get(event["lecture"]) or {}).get("title")
        lecture = f"`{event['lecture']}`"
        if title:
            lecture += f" {md_cell(title)}"
        conf = event["confidence"] if event.get("confidence") is not None else "—"
        lines.append(
            f"| {event['at'].isoformat()} | {lecture} | `{event['action']}` | "
            f"{event.get('phase') or '—'} | {conf} | {md_cell(event.get('note') or '')} |"
        )
    lines.append("")


if __name__ == "__main__":
    main()
