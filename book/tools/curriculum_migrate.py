#!/usr/bin/env python3
"""
Migrate lectures according to curriculum.yaml.

Usage:
  python curriculum_migrate.py --dry-run
  python curriculum_migrate.py --apply
  python curriculum_migrate.py --rewrite-only   # after files already at new paths
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

from curriculum_lib import (
    BOOK_ROOT,
    build_indexes,
    iter_lectures,
    lecture_destination,
    load_manifest,
    transform_lecture_text,
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def build_plan(manifest: dict) -> list[dict]:
    indexes = build_indexes(manifest)
    plan = []
    for course, lec, _i, _n in iter_lectures(manifest, types={"core"}):
        src_rel = lec.get("source")
        if not src_rel:
            raise SystemExit(f"Missing source for {lec['id']}")
        src = BOOK_ROOT / src_rel
        dest = lecture_destination(course, lec)
        plan.append(
            {
                "course": course,
                "lec": lec,
                "src": src,
                "dest": dest,
                "src_rel": src_rel,
                "dest_rel": str(dest.relative_to(BOOK_ROOT)).replace("\\", "/"),
            }
        )
    return plan, indexes


def print_plan(plan: list[dict]) -> None:
    print(f"{'LEGACY SOURCE':<72} -> NEW PATH")
    print("-" * 120)
    for row in plan:
        print(f"{row['src_rel']:<72} -> {row['dest_rel']}")
    print("-" * 120)
    print(f"Total: {len(plan)}")


def apply_migrate(plan: list[dict], indexes: dict, *, rewrite_only: bool) -> None:
    if len(plan) != 60:
        raise SystemExit(f"Refuse to proceed: expected 60 mappings, got {len(plan)}")

    if not rewrite_only:
        missing = [r for r in plan if not r["src"].is_file()]
        if missing:
            for r in missing[:10]:
                print(f"MISSING SOURCE: {r['src_rel']}")
            raise SystemExit(f"{len(missing)} source file(s) missing")

    # Phase 1: copy/move to new locations (via temp write)
    written: list[tuple[Path, Path, str]] = []  # dest, src, checksum

    for row in plan:
        course, lec = row["course"], row["lec"]
        dest: Path = row["dest"]
        dest.parent.mkdir(parents=True, exist_ok=True)

        if rewrite_only:
            if not dest.is_file():
                raise SystemExit(f"rewrite-only but missing {row['dest_rel']}")
            raw = dest.read_text(encoding="utf-8")
            # Prefer re-reading original if still present for cleaner transform?
            # Use dest content (may already have frontmatter)
            text = transform_lecture_text(raw, course, lec, indexes)
            dest.write_text(text, encoding="utf-8", newline="\n")
            continue

        src: Path = row["src"]
        checksum = sha256(src)
        raw = src.read_text(encoding="utf-8")
        text = transform_lecture_text(raw, course, lec, indexes)

        if dest.resolve() == src.resolve():
            dest.write_text(text, encoding="utf-8", newline="\n")
        else:
            dest.write_text(text, encoding="utf-8", newline="\n")
            written.append((dest, src, checksum))

    if rewrite_only:
        print(f"Rewrote {len(plan)} lectures in place.")
        return

    # Verify destinations
    for dest, src, checksum in written:
        if not dest.is_file():
            raise SystemExit(f"Destination missing after write: {dest}")
        # Source unchanged checksum
        if sha256(src) != checksum:
            raise SystemExit(f"Source changed unexpectedly: {src}")

    # Delete sources only after all destinations exist
    deleted = 0
    for dest, src, _checksum in written:
        if src.exists() and src.resolve() != dest.resolve():
            src.unlink()
            deleted += 1

    # Remove empty Core trees and Electives
    cleanup_legacy_dirs()
    print(f"Migrated {len(plan)} lectures. Deleted {deleted} legacy source files.")


def cleanup_legacy_dirs() -> None:
    for rel in (
        "Core/CS101",
        "Core/WEB201",
        "Core/BACK301",
        "Core/ENG401",
        "Core/AI501",
        "Core",
        "Electives/CS101",
        "Electives/WEB201",
        "Electives/BACK301",
        "Electives/ENG401",
        "Electives/AI501",
        "Electives/OPEN",
        "Electives",
    ):
        path = BOOK_ROOT / rel
        if path.is_dir():
            # Only remove if empty or only .gitkeep / known electives meta we replace
            try:
                shutil.rmtree(path)
                print(f"Removed {rel}/")
            except OSError as e:
                print(f"Could not remove {rel}: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument(
        "--rewrite-only",
        action="store_true",
        help="Re-run text transforms on files already at new paths",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    plan, indexes = build_plan(manifest)
    print_plan(plan)

    if args.dry_run:
        missing = [r for r in plan if not r["src"].is_file()]
        if missing:
            print(f"\n{len(missing)} source(s) missing (will block --apply)")
            sys.exit(1)
        print("\nDry run OK — 60/60 sources present.")
        sys.exit(0)

    apply_migrate(plan, indexes, rewrite_only=args.rewrite_only)
    print("Done. Run curriculum_validate.py next.")


if __name__ == "__main__":
    main()
