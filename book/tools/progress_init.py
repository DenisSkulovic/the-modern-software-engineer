#!/usr/bin/env python3
"""Create a personal Study Ledger from the curriculum + template defaults."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import yaml

from curriculum_lib import BOOK_ROOT, build_indexes, iter_lectures, load_manifest

STUDENTS = BOOK_ROOT / "students"
DEFAULT_INTERVAL = {
    "unopened": None,
    "wandering": 14,
    "studying": 14,
    "labbing": 21,
    "settled": 30,
    "fluent": 75,
    "fading": 7,
    "encore": 14,
}


def build_ledger(student: str, *, seed_status: str) -> dict:
    manifest = load_manifest()
    build_indexes(manifest)
    lectures: dict = {}
    for course, lec, _i, _n in iter_lectures(manifest, types={"core"}):
        lectures[lec["id"]] = {
            "course": course["code"],
            "title": lec["title"],
            "status": seed_status,
            "confidence": 0 if seed_status == "unopened" else 1,
            "passes": 0,
            "opened_on": None,
            "settled_on": None,
            "last_touched": None,
            "next_encore": None,
            "encore_interval_days": DEFAULT_INTERVAL.get(seed_status),
            "notes": "",
        }
    return {
        "student": student,
        "display_name": student,
        "created": date.today().isoformat(),
        "updated": date.today().isoformat(),
        "curriculum_version": str(manifest.get("version")),
        "learning_statuses": {
            "unopened": "Never started",
            "wandering": "Skimmed / light pass",
            "studying": "Serious first read in progress",
            "labbing": "Working labs and challenges",
            "settled": "Finished once; mental model held",
            "fluent": "Can explain cold / teach / interview",
            "fading": "Confidence dropping",
            "encore": "Scheduled revisit due or in progress",
        },
        "defaults": {
            "encore_intervals_days": DEFAULT_INTERVAL,
        },
        "lectures": lectures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--student", required=True, help="Folder id, e.g. dskul")
    parser.add_argument(
        "--seed-status",
        default="unopened",
        choices=list(DEFAULT_INTERVAL.keys()),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing ledger.yaml",
    )
    args = parser.parse_args()

    dest_dir = STUDENTS / args.student
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "ledger.yaml"
    if dest.exists() and not args.force:
        raise SystemExit(f"{dest} already exists (use --force to overwrite)")

    ledger = build_ledger(args.student, seed_status=args.seed_status)
    dest.write_text(
        yaml.safe_dump(ledger, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
        newline="\n",
    )

    # Keep template in sync shape
    template_dir = STUDENTS / "_template"
    template_dir.mkdir(parents=True, exist_ok=True)
    template = build_ledger("YOUR_ID", seed_status="unopened")
    template["display_name"] = "Your Name"
    (template_dir / "ledger.yaml").write_text(
        yaml.safe_dump(template, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
        newline="\n",
    )

    print(f"Wrote {dest.relative_to(BOOK_ROOT)}")
    print(f"Wrote {(template_dir / 'ledger.yaml').relative_to(BOOK_ROOT)}")
    print(f"Next: python tools/progress_render.py --student {args.student}")


if __name__ == "__main__":
    main()
