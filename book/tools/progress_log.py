#!/usr/bin/env python3
"""Append one study event, or migrate a legacy per-lecture snapshot into the log.

Existing events are never edited. --migrate-ledger runs once: it copies each
touched lecture into activity.yaml, then deletes the snapshot from ledger.yaml.
"""

from __future__ import annotations

import argparse
from datetime import date

from curriculum_lib import BOOK_ROOT, load_manifest
from progress_lib import (
    ACTIONS,
    PHASES,
    activity_path,
    dump_yaml,
    iso_day,
    ledger_path,
    lecture_index,
    load_events,
    load_yaml,
    parse_day,
    write_events,
)


def require_ledger(student: str) -> dict:
    path = ledger_path(student)
    if not path.is_file():
        raise SystemExit(f"Missing {path} — run progress_init.py first")
    return load_yaml(path)


def bump_updated(ledger: dict) -> None:
    ledger["updated"] = date.today().isoformat()


def append_event(student: str, event: dict) -> None:
    path = activity_path(student)
    before = load_events(path)
    write_events(path, before + [event])
    ledger = require_ledger(student)
    bump_updated(ledger)
    dump_yaml(ledger_path(student), ledger)
    print(
        f"Appended {event['action']} {event['lecture']} on {iso_day(event['at'])} "
        f"({len(before) + 1} events)"
    )


def migrate_ledger(student: str) -> None:
    path = activity_path(student)
    existing = load_events(path) if path.is_file() else []
    if existing:
        raise SystemExit(
            f"{path} already has {len(existing)} events; refusing to migrate again"
        )

    ledger = require_ledger(student)
    lectures = ledger.get("lectures") or {}
    if not lectures:
        raise SystemExit(f"{ledger_path(student)} has no lectures snapshot to migrate")

    touched = []
    for lid, entry in lectures.items():
        status = (entry or {}).get("status") or "unopened"
        if status == "unopened":
            continue
        touched.append((lid, entry))

    events = []
    for index, (lid, entry) in enumerate(
        sorted(
            touched,
            key=lambda pair: (
                iso_day(pair[1].get("last_touched") or pair[1].get("opened_on")) or "",
                pair[0],
            ),
        )
    ):
        day = parse_day(entry.get("last_touched") or entry.get("opened_on"))
        if day is None:
            raise SystemExit(f"{lid} has status {entry.get('status')!r} but no date to keep")
        note = (entry.get("notes") or "").strip()
        event = {
            "_i": index,
            "at": day,
            "lecture": lid,
            "action": "listen",
            "phase": entry.get("status"),
            "source": "backfill",
        }
        if entry.get("confidence") is not None:
            event["confidence"] = int(entry["confidence"])
        if note:
            event["note"] = note
        events.append(event)

    write_events(path, events)
    ledger.pop("lectures", None)
    bump_updated(ledger)
    dump_yaml(ledger_path(student), ledger)
    print(f"Migrated {len(events)} listen sessions into {path.relative_to(BOOK_ROOT)}")
    print(f"Removed lectures snapshot from {ledger_path(student).relative_to(BOOK_ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--student", required=True)
    parser.add_argument("--lecture", help="Catalogue id, e.g. CS230-L08")
    parser.add_argument("--action", choices=ACTIONS)
    parser.add_argument("--phase", choices=PHASES)
    parser.add_argument("--confidence", type=int, help="0–5 gut check after this session")
    parser.add_argument("--note", default="", help="What this session was. Kept forever.")
    parser.add_argument("--at", help="YYYY-MM-DD. Default: today. Do not invent a clock time.")
    parser.add_argument(
        "--migrate-ledger",
        action="store_true",
        help="One-shot: copy non-unopened lecture rows into activity.yaml and drop them",
    )
    args = parser.parse_args()

    if args.migrate_ledger:
        migrate_ledger(args.student)
        print(f"Next: python tools/progress_render.py --student {args.student}")
        return

    if not args.lecture or not args.action:
        parser.error("--lecture and --action are required unless --migrate-ledger")

    manifest = load_manifest()
    catalog = lecture_index(manifest)
    if args.lecture not in catalog:
        raise SystemExit(f"Unknown lecture {args.lecture!r} — not in curriculum.yaml")

    if args.confidence is not None and not 0 <= args.confidence <= 5:
        raise SystemExit("--confidence must be 0–5")

    day = date.today() if not args.at else parse_day(args.at)
    if day is None:
        raise SystemExit(f"--at must be YYYY-MM-DD, got {args.at!r}")

    require_ledger(args.student)
    event = {
        "_i": 0,
        "at": day,
        "lecture": args.lecture,
        "action": args.action,
    }
    if args.phase:
        event["phase"] = args.phase
    if args.confidence is not None:
        event["confidence"] = args.confidence
    note = (args.note or "").strip()
    if note:
        event["note"] = note
    append_event(args.student, event)


if __name__ == "__main__":
    main()
