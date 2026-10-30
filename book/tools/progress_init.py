#!/usr/bin/env python3
"""Create a personal study profile and an empty activity log.

The log starts empty. Learning history is appended with progress_log.py.
There is no per-lecture snapshot to edit.
"""

from __future__ import annotations

import argparse

from curriculum_lib import BOOK_ROOT, load_manifest
from progress_lib import (
    STUDENTS,
    activity_path,
    dump_yaml,
    empty_activity,
    exam_attempts_path,
    ledger_path,
    load_events,
    narrative_listens_path,
    profile_ledger,
    write_empty_exam_attempts,
    write_empty_narrative_listens,
    write_events,
)


def write_templates(manifest: dict | None = None) -> None:
    manifest = manifest if manifest is not None else load_manifest()
    template_dir = STUDENTS / "_template"
    template_dir.mkdir(parents=True, exist_ok=True)
    template = profile_ledger("YOUR_ID", display_name="Your Name", manifest=manifest)
    dump_yaml(template_dir / "ledger.yaml", template)
    write_events(template_dir / "activity.yaml", [])
    write_empty_exam_attempts(template_dir / "exam-attempts.yaml")
    write_empty_narrative_listens(template_dir / "narrative-listens.yaml")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--student", required=True, help="Folder id, e.g. dskul")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite ledger.yaml. Refuses to erase an activity log that already has events.",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    dest_dir = STUDENTS / args.student
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = ledger_path(args.student)
    act = activity_path(args.student)

    if dest.exists() and not args.force:
        raise SystemExit(f"{dest} already exists (use --force to overwrite the profile)")

    if act.exists() and args.force:
        existing = load_events(act)
        if existing:
            raise SystemExit(
                f"{act} already has {len(existing)} events; refusing to erase the log"
            )

    ledger = profile_ledger(args.student, manifest=manifest)
    dump_yaml(dest, ledger)
    if not act.exists() or args.force:
        write_events(act, empty_activity()["events"])

    exams = exam_attempts_path(args.student)
    if not exams.exists():
        write_empty_exam_attempts(exams)

    stories = narrative_listens_path(args.student)
    if not stories.exists():
        write_empty_narrative_listens(stories)

    write_templates(manifest)

    print(f"Wrote {dest.relative_to(BOOK_ROOT)}")
    print(f"Wrote {act.relative_to(BOOK_ROOT)}")
    if exams.exists():
        print(f"Wrote {exams.relative_to(BOOK_ROOT)}")
    if stories.exists():
        print(f"Wrote {stories.relative_to(BOOK_ROOT)}")
    print(f"Wrote {(STUDENTS / '_template' / 'ledger.yaml').relative_to(BOOK_ROOT)}")
    print(f"Wrote {(STUDENTS / '_template' / 'activity.yaml').relative_to(BOOK_ROOT)}")
    print(f"Wrote {(STUDENTS / '_template' / 'exam-attempts.yaml').relative_to(BOOK_ROOT)}")
    print(f"Wrote {(STUDENTS / '_template' / 'narrative-listens.yaml').relative_to(BOOK_ROOT)}")
    print(
        "Next: python tools/progress_log.py --student "
        f"{args.student} --lecture <id> --action listen --phase studying"
    )


if __name__ == "__main__":
    main()
