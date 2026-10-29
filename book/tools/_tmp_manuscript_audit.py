#!/usr/bin/env python3
"""One-shot audit: catalogue manuscript status vs on-disk substance."""

from __future__ import annotations

import re
from collections import Counter

from curriculum_lib import (
    BOOK_ROOT,
    iter_lectures,
    lecture_destination,
    load_manifest,
    strip_existing_frontmatter,
)


def main() -> None:
    manifest = load_manifest()
    rows = []
    for course, lec, _i, _n in iter_lectures(manifest, types={"core", "elective"}):
        dest = lecture_destination(course, lec)
        if not dest.is_file():
            rows.append(
                {
                    "id": lec["id"],
                    "course": course["code"],
                    "yaml": lec.get("manuscript"),
                    "fm": None,
                    "words": 0,
                    "part_i": False,
                    "part_ii": False,
                    "todoish": False,
                    "missing": True,
                }
            )
            continue
        text = dest.read_text(encoding="utf-8").replace("\r\n", "\n")
        body = strip_existing_frontmatter(text)
        words = len(re.findall(r"\w+", body))
        part_i = bool(re.search(r"(?im)^##\s+Part I\b", body))
        part_ii = bool(re.search(r"(?im)^##\s+Part II\b", body))
        # Only treat early-body TODO/placeholder as stub signal
        head = body[:2500]
        todoish = bool(
            re.search(
                r"(?i)\b(TODO|TBD|placeholder|to be written|outline only|stub lecture)\b",
                head,
            )
        )
        fm = re.search(r"^manuscript:\s*(\S+)", text, re.M)
        rows.append(
            {
                "id": lec["id"],
                "course": course["code"],
                "yaml": lec.get("manuscript"),
                "fm": fm.group(1) if fm else None,
                "words": words,
                "part_i": part_i,
                "part_ii": part_ii,
                "todoish": todoish,
                "missing": False,
            }
        )

    print("=== yaml stub but looks like full manuscript ===")
    print("(words>=2500 or Part I+II present)")
    promote = []
    for r in rows:
        if r["yaml"] != "stub":
            continue
        looks_full = r["words"] >= 2500 or (r["part_i"] and r["part_ii"])
        if looks_full and not r["todoish"]:
            promote.append(r)
            print(
                f"{r['id']:12} words={r['words']:5} parts={r['part_i']}/{r['part_ii']}"
            )

    print("\n=== yaml manuscript/revised/polished but looks thin ===")
    for r in rows:
        if r["yaml"] not in {"manuscript", "revised", "polished"}:
            continue
        if r["words"] < 800 and not r["part_ii"]:
            print(
                f"{r['id']:12} words={r['words']:5} yaml={r['yaml']} todoish={r['todoish']}"
            )

    print("\n=== yaml vs frontmatter mismatch ===")
    mismatches = [r for r in rows if r["fm"] and r["yaml"] and r["fm"] != r["yaml"]]
    if not mismatches:
        print("(none)")
    for r in mismatches:
        print(f"{r['id']:12} yaml={r['yaml']} fm={r['fm']}")

    print("\n=== all current yaml stubs ===")
    stubs = [r for r in rows if r["yaml"] == "stub"]
    for r in stubs:
        flag = "PROMOTE?" if r in promote else "maybe-real-stub"
        print(
            f"{r['id']:12} words={r['words']:5} parts={r['part_i']}/{r['part_ii']} "
            f"todoish={r['todoish']} {flag}"
        )

    print("\n=== status counts ===")
    print(dict(Counter(r["yaml"] for r in rows)))
    print(f"promote candidates: {[r['id'] for r in promote]}")


if __name__ == "__main__":
    main()
