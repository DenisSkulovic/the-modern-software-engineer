#!/usr/bin/env python3
"""
Ensure every lecture in curriculum.yaml has manuscript + edition,
sync those fields into on-disk frontmatter, and fix course rollup status.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

from curriculum_lib import (
    BOOK_ROOT,
    MANIFEST_PATH,
    build_indexes,
    frontmatter_block,
    iter_lectures,
    lecture_destination,
    load_manifest,
    normalize_newlines,
    strip_existing_frontmatter,
)

VALID_MANUSCRIPT = {
    "planned",
    "stub",
    "draft",
    "manuscript",
    "revised",
    "polished",
}

DEFAULT_EDITION = "2.0.0"


def rollup_course_status(lectures: list[dict]) -> str:
    if not lectures:
        return "planned"
    states = [lec.get("manuscript", "planned") for lec in lectures]
    if all(s == "planned" for s in states):
        return "planned"
    if all(s == "polished" for s in states):
        return "stable"
    if all(s in {"manuscript", "revised", "polished"} for s in states):
        return "complete"
    return "in_progress"


def enrich_yaml(path: Path, *, default_manuscript: str, edition: str) -> None:
    text = path.read_text(encoding="utf-8")
    # Insert schema comment block after title line if missing
    if "manuscript_statuses:" not in text:
        schema = '''
# Manuscript production statuses (see STATUS.md):
#   planned | stub | draft | manuscript | revised | polished
manuscript_statuses:
  planned: "Catalogue only — no file yet"
  stub: "File exists; outline / placeholder"
  draft: "Substantial but incomplete prose"
  manuscript: "Full lecture to programme standard"
  revised: "Materially rewritten after first manuscript"
  polished: "Stable for current major edition"

default_edition: "2.0.0"

'''
        # After updated: line
        text = re.sub(
            r'(updated: "[^"]*"\n)',
            rf"\1{schema}",
            text,
            count=1,
        )

    data = yaml.safe_load(text)
    data.setdefault("default_edition", edition)

    for course in data["courses"]:
        lectures = course.get("lectures") or []
        for lec in lectures:
            lec.setdefault("manuscript", default_manuscript)
            lec.setdefault("edition", data.get("default_edition", edition))
            if lec["manuscript"] not in VALID_MANUSCRIPT:
                raise SystemExit(
                    f"Invalid manuscript status for {lec['id']}: {lec['manuscript']}"
                )
        if course.get("type") == "planned" and not lectures:
            course["status"] = "planned"
        else:
            course["status"] = rollup_course_status(lectures)

    # Dump loses comments — instead patch lecture blocks in original text
    # Prefer rewriting whole file with yaml.dump for reliability of structure.
    # Keep header comments by prepending a banner.
    banner = (
        "# The Modern Software Engineer — curriculum source of truth\n"
        "# Edit this file, then run tools/curriculum_migrate.py / sync_manuscript_meta.py\n"
        "# See STATUS.md for manuscript vs learning status model.\n\n"
    )
    body = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        width=100,
        default_flow_style=False,
    )
    path.write_text(banner + body, encoding="utf-8", newline="\n")
    print(f"Updated {path.relative_to(BOOK_ROOT)}")


def sync_frontmatter(manifest: dict) -> int:
    build_indexes(manifest)
    n = 0
    for course, lec, _i, _n in iter_lectures(manifest, types={"core", "elective"}):
        dest = lecture_destination(course, lec)
        if not dest.is_file():
            continue
        raw = normalize_newlines(dest.read_text(encoding="utf-8"))
        body = strip_existing_frontmatter(raw)
        # Preserve H1 if present; only refresh frontmatter
        new = frontmatter_block(course, lec) + body
        if new != raw:
            dest.write_text(new, encoding="utf-8", newline="\n")
            n += 1
    return n


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--default-manuscript",
        default="manuscript",
        choices=sorted(VALID_MANUSCRIPT),
        help="Status to set on lectures missing manuscript (default: manuscript)",
    )
    parser.add_argument(
        "--edition",
        default=DEFAULT_EDITION,
        help="Default edition for lectures missing edition",
    )
    parser.add_argument(
        "--frontmatter-only",
        action="store_true",
        help="Do not rewrite curriculum.yaml; only sync frontmatter from current yaml",
    )
    args = parser.parse_args()

    if not args.frontmatter_only:
        enrich_yaml(
            MANIFEST_PATH,
            default_manuscript=args.default_manuscript,
            edition=args.edition,
        )

    manifest = load_manifest()
    # Ensure in-memory defaults even if yaml already had fields
    for course, lec, _i, _n in iter_lectures(manifest):
        lec.setdefault("manuscript", args.default_manuscript)
        lec.setdefault(
            "edition",
            manifest.get("default_edition", args.edition),
        )
    n = sync_frontmatter(manifest)
    print(f"Synced frontmatter on {n} lecture file(s)")


if __name__ == "__main__":
    main()
