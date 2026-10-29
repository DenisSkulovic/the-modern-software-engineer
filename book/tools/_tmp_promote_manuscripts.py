#!/usr/bin/env python3
"""Promote catalogue stub → manuscript for lectures that are already full prose."""

from __future__ import annotations

import re
from datetime import date

from sync_manuscript_meta import rollup_course_status
from curriculum_lib import MANIFEST_PATH, load_manifest

PROMOTE = {
    "SE215-L11",
    "SE215-L12",
    "CS345-L01",
    "CS345-L02",
    "CS345-L03",
    "CS345-L04",
    "CS350-L01",
    "CS350-L02",
    "CS350-L03",
    "CS350-L04",
    "SE250-L01",
    "SE250-L02",
    "SE250-L03",
    "SE250-L04",
    "SE250-L05",
    "SE250-L06",
    "SE335-L01",
    "SE335-L02",
    "SE335-L03",
}

COURSE_CODES = ("SE215", "CS345", "CS350", "SE250", "SE335")


def main() -> None:
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    changed: list[str] = []
    for lid in sorted(PROMOTE):
        pattern = rf"(- id: {re.escape(lid)}\n(?:  .*\n)*?    manuscript: )stub(\n)"
        new_text, n = re.subn(pattern, r"\1manuscript\2", text, count=1)
        if n != 1:
            raise SystemExit(f"Failed to promote {lid} (matches={n})")
        text = new_text
        changed.append(lid)

    text, n = re.subn(
        r"(^updated: )'[0-9-]+'",
        rf"\1'{date.today().isoformat()}'",
        text,
        count=1,
        flags=re.M,
    )
    if n != 1:
        raise SystemExit("Failed to bump updated date")

    MANIFEST_PATH.write_text(text, encoding="utf-8", newline="\n")

    # Roll up course status from the updated manifest without rewriting the whole file.
    data = load_manifest()
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    for code in COURSE_CODES:
        course = next(c for c in data["courses"] if c["code"] == code)
        new_status = rollup_course_status(course.get("lectures") or [])
        pattern = rf"(- code: {re.escape(code)}\n(?:  .*\n)*?  status: )\S+(\n)"
        text, n = re.subn(pattern, rf"\1{new_status}\2", text, count=1)
        if n != 1:
            raise SystemExit(f"Failed to set status for {code}")
        print(f"{code} status → {new_status}")

    MANIFEST_PATH.write_text(text, encoding="utf-8", newline="\n")
    print(f"Promoted {len(changed)} lectures")


if __name__ == "__main__":
    main()
