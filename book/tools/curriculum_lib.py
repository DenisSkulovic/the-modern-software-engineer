"""Shared helpers for curriculum.yaml tools."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

BOOK_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BOOK_ROOT / "curriculum.yaml"

OLD_COURSE_CODES = ("CS101", "WEB201", "BACK301", "ENG401", "AI501")
OLD_COURSE_RE = re.compile(r"\b(?:CS101|WEB201|BACK301|ENG401|AI501)\b")
# Do not match "Session 100,000" (numbers with commas / more digits glued on)
SESSION_RE = re.compile(r"\b[Ss]ession\s+(\d{1,2})(?!,|\d)\b")
SESSION_OF_RE = re.compile(
    r"\b[Ss]ession\s+(\d{1,2})\s+of\s+(\d{1,2})\b"
)
PROGRESS_LINE_RE = re.compile(
    r"^.*\b(?:progress:\s*\d+\s*/\s*\d+|Programme progress:|Overall programme:|"
    r"sessions generated|Core Curriculum Complete)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def iter_lectures(manifest: dict[str, Any], *, types: set[str] | None = None):
    """Yield (course, lecture, lecture_index, lecture_count) for courses with lectures."""
    for course in manifest["courses"]:
        if types is not None and course.get("type") not in types:
            continue
        lectures = course.get("lectures") or []
        n = len(lectures)
        for i, lec in enumerate(lectures):
            yield course, lec, i, n


def enrich_prev_next(manifest: dict[str, Any]) -> None:
    """Set prev/next on each lecture dict in place (course-local)."""
    for course in manifest["courses"]:
        lectures = course.get("lectures") or []
        for i, lec in enumerate(lectures):
            lec["prev"] = lectures[i - 1]["id"] if i > 0 else None
            lec["next"] = lectures[i + 1]["id"] if i + 1 < len(lectures) else None
            lec["course"] = course["code"]
            lec["index"] = i + 1
            lec["count"] = len(lectures)
            lec["path"] = (
                f"{course['dir']}/{lec['id']}-{lec['slug']}.md"
            )


def build_indexes(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build lookup tables for migration and reference rewriting."""
    enrich_prev_next(manifest)

    by_id: dict[str, dict] = {}
    by_legacy: dict[str, dict] = {}
    # legacy_course -> session_num(int) -> new lecture record
    session_map: dict[str, dict[int, dict]] = {}
    course_by_code: dict[str, dict] = {
        c["code"]: c for c in manifest["courses"]
    }

    for course, lec, _i, _n in iter_lectures(manifest):
        rec = {**lec, "course_meta": course}
        by_id[lec["id"]] = rec
        for lid in lec.get("legacy_ids") or []:
            by_legacy[lid] = rec
            # CS101-S09 -> course CS101, session 9
            m = re.match(r"^([A-Z]+\d+)-S(\d+)$", lid)
            if m:
                old_course, sess = m.group(1), int(m.group(2))
                session_map.setdefault(old_course, {})[sess] = rec

    return {
        "by_id": by_id,
        "by_legacy": by_legacy,
        "session_map": session_map,
        "course_by_code": course_by_code,
    }


def core_lecture_count(manifest: dict[str, Any]) -> int:
    return sum(
        1
        for c in manifest["courses"]
        if c.get("type") == "core"
        for _ in (c.get("lectures") or [])
    )


def lecture_destination(course: dict, lec: dict) -> Path:
    return BOOK_ROOT / course["dir"] / f"{lec['id']}-{lec['slug']}.md"


def parse_legacy_id(legacy_id: str) -> tuple[str, int]:
    m = re.match(r"^([A-Z]+\d+)-S(\d+)$", legacy_id)
    if not m:
        raise ValueError(f"Bad legacy id: {legacy_id}")
    return m.group(1), int(m.group(2))


def frontmatter_block(course: dict, lec: dict) -> str:
    legacy = lec.get("legacy_ids") or []
    legacy_yaml = "[" + ", ".join(legacy) + "]"
    prev = lec.get("prev")
    nxt = lec.get("next")
    prev_s = "null" if prev is None else prev
    next_s = "null" if nxt is None else nxt
    title = lec["title"].replace('"', '\\"')
    manuscript = lec.get("manuscript", "manuscript")
    edition = lec.get("edition", "2.0.0")
    return (
        "---\n"
        f"id: {lec['id']}\n"
        f"course: {course['code']}\n"
        f'title: "{title}"\n'
        f"type: {course.get('type', 'core')}\n"
        f"manuscript: {manuscript}\n"
        f'edition: "{edition}"\n'
        f"legacy_ids: {legacy_yaml}\n"
        f"prev: {prev_s}\n"
        f"next: {next_s}\n"
        "---\n\n"
    )


def strip_existing_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5 :]
    return text


def lecture_number_label(lec: dict) -> str:
    """L01 -> 01 display helper."""
    m = re.search(r"-L(\d+)$", lec["id"])
    return m.group(1) if m else str(lec.get("index", ""))


def rewrite_headers(body: str, course: dict, lec: dict) -> str:
    """Replace leading H1/H2 course/session titles."""
    lines = body.splitlines(keepends=True)
    if not lines:
        return body

    # Skip blank lines at start
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1

    # Replace first H1 if it looks like a course header
    if i < len(lines) and lines[i].startswith("# "):
        lines[i] = f"# {course['code']} — {course['title']}\n"
        i += 1
        while i < len(lines) and lines[i].strip() == "":
            i += 1
        # Replace following H2 session header
        if i < len(lines) and lines[i].startswith("## "):
            num = lecture_number_label(lec)
            lines[i] = f"## Lecture {num}: {lec['title']}\n"

    return "".join(lines)


def rewrite_session_refs(body: str, legacy_course: str, indexes: dict) -> str:
    """Replace Session N with new lecture IDs, scoped to the legacy course."""
    smap = indexes["session_map"].get(legacy_course, {})

    def repl_session_of(m: re.Match) -> str:
        n = int(m.group(1))
        rec = smap.get(n)
        if rec:
            return rec["id"]
        return m.group(0)

    def repl_session(m: re.Match) -> str:
        n = int(m.group(1))
        rec = smap.get(n)
        if rec:
            return rec["id"]
        return m.group(0)

    # "Session 12 of 12" first
    body = SESSION_OF_RE.sub(repl_session_of, body)
    body = SESSION_RE.sub(repl_session, body)
    return body


def rewrite_old_course_codes(body: str, course: dict, lec: dict, indexes: dict) -> str:
    """
    Replace old mega-course codes.
    Heuristic: map each old code mention to the new course of the lecture
    that absorbed that session when resolvable; otherwise to this file's new course
    if the mention matches this file's legacy course; else to a multi-course phrase.
    """
    legacy_ids = lec.get("legacy_ids") or []
    this_legacy_course = parse_legacy_id(legacy_ids[0])[0] if legacy_ids else None

    # Which new courses absorbed each old course?
    absorbed: dict[str, list[str]] = {}
    for old in OLD_COURSE_CODES:
        codes: list[str] = []
        for _sess, rec in sorted(indexes["session_map"].get(old, {}).items()):
            c = rec["course"]
            if c not in codes:
                codes.append(c)
        absorbed[old] = codes

    def repl(m: re.Match) -> str:
        old = m.group(0)
        if old == this_legacy_course:
            return course["code"]
        codes = absorbed.get(old, [])
        if len(codes) == 1:
            return codes[0]
        if len(codes) > 1:
            # Comma list — never an en-dash range (numbers are not contiguous)
            if len(codes) == 2:
                return f"{codes[0]} and {codes[1]}"
            return ", ".join(codes[:-1]) + f", and {codes[-1]}"
        return old

    return OLD_COURSE_RE.sub(repl, body)


def rewrite_pocket_and_see_you(body: str, lec: dict) -> str:
    """Normalize pocket card / see-you lines that still say Session after ID rewrite failed patterns."""
    num = lecture_number_label(lec)
    body = re.sub(
        rf"POCKET CARD — {re.escape(lec['id'])}",
        f"POCKET CARD — {lec['id']}",
        body,
    )
    body = re.sub(
        r"POCKET CARD — Session \d+",
        f"POCKET CARD — {lec['id']}",
        body,
    )
    body = re.sub(
        rf"POCKET CARD — Lecture {num}",
        f"POCKET CARD — {lec['id']}",
        body,
    )
    return body


def strip_progress_and_legacy_end_markers(body: str, course: dict, lec: dict) -> str:
    body = PROGRESS_LINE_RE.sub("", body)
    body = re.sub(
        r"\*\*The Modern Software Engineer — Core Curriculum Complete\.\*\*",
        "",
        body,
    )
    body = re.sub(r"\*\*Course completed:.*?\*\*", "", body, flags=re.IGNORECASE)
    # Stale mega-course / wrong-course end banners
    body = re.sub(
        rf"\*\*End of {re.escape(course['code'])} — (?!{re.escape(lec['title'])}).*?\*\*",
        "",
        body,
    )
    body = re.sub(
        r"^\*Next course:.*\*$",
        "",
        body,
        flags=re.MULTILINE,
    )
    body = re.sub(
        rf"^# End of {re.escape(course['code'])}\s*$",
        "",
        body,
        flags=re.MULTILINE,
    )
    # Duplicate short "Next session" blocks left beside canonical Next Lecture
    body = re.sub(
        r"^## Next session\s*\n(?:.*?\n)*?(?=^## Next Lecture\b)",
        "",
        body,
        flags=re.MULTILINE,
    )
    return body


def rewrite_next_footer(body: str, course: dict, lec: dict, indexes: dict) -> str:
    """Ensure a single canonical next/end footer; strip legacy navigation."""
    by_id = indexes["by_id"]
    nxt_id = lec.get("next")
    body = strip_progress_and_legacy_end_markers(body, course, lec)

    if nxt_id:
        nxt = by_id[nxt_id]
        nxt_course = nxt["course_meta"]
        replacement = (
            f"## Next Lecture — {nxt_id}: {nxt['title']}\n\n"
            f"Continue in **{nxt_course['code']} — {nxt_course['title']}**.\n"
        )
    else:
        if course["code"] == "SE490" and lec["id"] == "SE490-L05":
            replacement = (
                "## Next Steps — Beyond the Core Curriculum\n\n"
                "The core catalogue is complete. Continue with planned electives "
                "(see `curriculum.yaml` / `curriculum.md`), revisit studio workshops, "
                "or apply the material in interviews and production work.\n"
            )
        else:
            replacement = (
                f"## End of {course['code']}\n\n"
                f"**{course['code']} — {course['title']}** is complete. "
                f"See the recommended study order in `README.md` for natural next courses.\n"
            )

    # Remove ALL existing navigation footers, then append one canonical block
    # before Further Reading if present, else at end.
    nav_pat = re.compile(
        r"(?:"
        r"^## Next Session\b.*?(?=^## |\Z)|"
        r"^## Next:.*?(?=^## |\Z)|"
        r"^## Next Lecture\b.*?(?=^## |\Z)|"
        r"^## Next Steps\b.*?(?=^## |\Z)|"
        r"^## End of \w+\b.*?(?=^## |\Z)|"
        r"^# Next Course\b.*?(?=^# |\Z)|"
        r"^# \d+\. Where We Go Next\b.*?(?=^# |\Z)"
        r")",
        re.MULTILINE | re.DOTALL,
    )
    body = nav_pat.sub("", body)

    # Remove trailing "**End of CODE, ID.**" style lines (keep one clean footer)
    body = re.sub(
        rf"\*\*End of {re.escape(course['code'])},?\s*{re.escape(lec['id'])}\.?\*\*",
        "",
        body,
    )
    body = re.sub(
        rf"\*\*End of {re.escape(course['code'])} — {re.escape(lec['id'])}\*\*",
        "",
        body,
    )
    body = re.sub(
        rf"^\*{re.escape(course['code'])} — {re.escape(lec['id'])} complete\.\*$",
        "",
        body,
        flags=re.MULTILINE,
    )

    fr = re.search(r"^## Further Reading\b|^# Further Reading\b", body, re.MULTILINE)
    block = "\n---\n\n" + replacement + "\n"
    if fr:
        body = body[: fr.start()] + block + body[fr.start() :]
    else:
        if not body.endswith("\n"):
            body += "\n"
        body += block

    body = re.sub(r"\n{4,}", "\n\n\n", body)
    return body


def transform_lecture_text(
    text: str,
    course: dict,
    lec: dict,
    indexes: dict,
) -> str:
    body = strip_existing_frontmatter(text)
    legacy_ids = lec.get("legacy_ids") or []
    legacy_course, _ = parse_legacy_id(legacy_ids[0])

    body = rewrite_headers(body, course, lec)
    body = rewrite_session_refs(body, legacy_course, indexes)
    body = rewrite_old_course_codes(body, course, lec, indexes)
    body = rewrite_pocket_and_see_you(body, lec)
    body = rewrite_next_footer(body, course, lec, indexes)

    # Fix "See you in <id>" style lines already rewritten from Session N
    nxt = lec.get("next")
    if nxt:
        body = re.sub(
            r"See you in [A-Z]+\d+-L\d+\.",
            f"See you in {nxt}.",
            body,
        )
        body = re.sub(
            r"See you in Session \d+\.",
            f"See you in {nxt}.",
            body,
        )

    return frontmatter_block(course, lec) + body
