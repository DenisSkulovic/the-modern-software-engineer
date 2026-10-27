#!/usr/bin/env python3
"""Validate curriculum.yaml against on-disk lecture files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from curriculum_lib import (
    ACTIVE_COURSE_TYPES,
    BOOK_ROOT,
    MANIFEST_PATH,
    OLD_COURSE_RE,
    SESSION_RE,  # already excludes Session 100,000-style
    build_indexes,
    core_lecture_count,
    elective_lecture_count,
    iter_lectures,
    lecture_destination,
    load_manifest,
    strip_existing_frontmatter,
)

FRONTMATTER_ID_RE = re.compile(r"^id:\s*(\S+)", re.MULTILINE)
FRONTMATTER_MANUSCRIPT_RE = re.compile(r"^manuscript:\s*(\S+)", re.MULTILINE)
FRONTMATTER_EDITION_RE = re.compile(r'^edition:\s*"?([^"\n]+)"?', re.MULTILINE)
VALID_MANUSCRIPT = {
    "planned",
    "stub",
    "draft",
    "manuscript",
    "revised",
    "polished",
}


def validate(strict_body: bool = True) -> int:
    manifest = load_manifest()
    indexes = build_indexes(manifest)
    errors: list[str] = []
    warnings: list[str] = []

    core_n = core_lecture_count(manifest)
    elective_n = elective_lecture_count(manifest)

    seen_ids: set[str] = set()
    seen_legacy: set[str] = set()
    on_disk: set[Path] = set()

    for course, lec, _i, _n in iter_lectures(manifest, types=set(ACTIVE_COURSE_TYPES)):
        lid = lec["id"]
        ctype = course.get("type", "core")
        if lid in seen_ids:
            errors.append(f"Duplicate lecture id: {lid}")
        seen_ids.add(lid)

        for legacy in lec.get("legacy_ids") or []:
            if legacy in seen_legacy:
                errors.append(f"Duplicate legacy id: {legacy}")
            seen_legacy.add(legacy)

        dest = lecture_destination(course, lec)
        if not dest.is_file():
            errors.append(f"Missing file for {lid}: {dest.relative_to(BOOK_ROOT)}")
            continue
        on_disk.add(dest.resolve())

        ms = lec.get("manuscript")
        if ms not in VALID_MANUSCRIPT:
            errors.append(f"{lid}: invalid manuscript status {ms!r}")
        if not lec.get("edition"):
            errors.append(f"{lid}: missing edition in manifest")
        if ms == "planned":
            errors.append(
                f"{lid}: active {ctype} lecture still marked manuscript:planned "
                "(use stub+ or keep course type:planned)"
            )

        text = dest.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            errors.append(f"{lid}: missing YAML frontmatter")
        else:
            m = FRONTMATTER_ID_RE.search(text)
            if not m or m.group(1) != lid:
                errors.append(f"{lid}: frontmatter id mismatch")
            mm = FRONTMATTER_MANUSCRIPT_RE.search(text)
            if not mm:
                errors.append(f"{lid}: frontmatter missing manuscript")
            elif ms and mm.group(1) != ms:
                errors.append(
                    f"{lid}: frontmatter manuscript {mm.group(1)!r} != manifest {ms!r}"
                )
            ed = FRONTMATTER_EDITION_RE.search(text)
            if not ed:
                errors.append(f"{lid}: frontmatter missing edition")
            # Frontmatter type should match course type for active courses
            tm = re.search(r"^type:\s*(\S+)", text, re.MULTILINE)
            if tm and tm.group(1) != ctype:
                errors.append(
                    f"{lid}: frontmatter type {tm.group(1)!r} != course type {ctype!r}"
                )

        if strict_body:
            body = strip_existing_frontmatter(text)
            # Allow old codes only inside fenced legacy discussion? Plan says none in bodies.
            for m in OLD_COURSE_RE.finditer(body):
                errors.append(
                    f"{lid}: old course code {m.group(0)!r} in body "
                    f"(offset {m.start()})"
                )
            for m in SESSION_RE.finditer(body):
                errors.append(
                    f"{lid}: bare Session reference {m.group(0)!r} in body "
                    f"(offset {m.start()})"
                )

    # Unexpected .md under CS/SE/AI that aren't in active (core/elective) manifest
    for disc in ("CS", "SE", "AI"):
        root = BOOK_ROOT / disc
        if not root.is_dir():
            continue
        for path in root.rglob("*.md"):
            if path.resolve() not in on_disk:
                warnings.append(
                    f"Extra markdown not in active catalogue: {path.relative_to(BOOK_ROOT)}"
                )

    # Planned courses should not claim generated files yet (optional check)
    for course in manifest["courses"]:
        if course.get("type") != "planned":
            continue
        if course.get("lectures"):
            warnings.append(
                f"Planned course {course['code']} already has lectures listed"
            )
        dest_dir = BOOK_ROOT / course["dir"]
        if dest_dir.is_dir() and any(dest_dir.rglob("*.md")):
            warnings.append(
                f"Planned course {course['code']} has on-disk markdown under {course['dir']}"
            )

    print(f"Manifest: {MANIFEST_PATH}")
    print(f"Core lectures: {core_n}")
    print(f"Elective lectures: {elective_n}")
    print(f"Unique ids: {len(seen_ids)}")
    print(f"Legacy ids: {len(seen_legacy)}")
    for w in warnings:
        print(f"WARNING: {w}")
    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors[:80]:
            print(f"  ERROR: {e}")
        if len(errors) > 80:
            print(f"  ... and {len(errors) - 80} more")
        return 1
    print("OK")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-strict-body",
        action="store_true",
        help="Skip Session/old-code body checks",
    )
    args = parser.parse_args()
    sys.exit(validate(strict_body=not args.no_strict_body))


if __name__ == "__main__":
    main()
