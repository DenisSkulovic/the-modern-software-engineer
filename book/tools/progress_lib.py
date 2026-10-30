"""Study activity log: append-only events and the fold that reads them.

activity.yaml is the source of truth. Current phase, confidence, pass counts,
and encore dates are queries over that log, not fields that get overwritten.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from curriculum_lib import BOOK_ROOT, iter_lectures, load_manifest

STUDENTS = BOOK_ROOT / "students"

PASS_ACTIONS = ("listen", "read", "skim", "lab", "oral", "review")
ACTIONS = PASS_ACTIONS + ("note",)

PHASES = (
    "unopened",
    "wandering",
    "studying",
    "labbing",
    "settled",
    "fluent",
    "fading",
    "encore",
)

# Phases that schedule a revisit. Earlier phases record work without a due date.
ENCORE_PHASES = frozenset({"settled", "fluent", "fading", "encore"})

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

LEARNING_STATUSES = {
    "unopened": "Never started",
    "wandering": "Skimmed / light pass",
    "studying": "Serious first read in progress",
    "labbing": "Working labs and challenges",
    "settled": "Finished once; mental model held",
    "fluent": "Can explain cold / teach / interview",
    "fading": "Confidence dropping",
    "encore": "Scheduled revisit due or in progress",
}

ACTIVITY_HEADER = """\
# Append-only study activity. Source of truth for learning history.
# Append with: python tools/progress_log.py --student <id> --lecture CS230-L08 --action listen --phase studying
# Do not edit past events. A correction is a new event.
#
# Fields: at (YYYY-MM-DD), lecture, action (listen|read|skim|lab|oral|review|note),
# optional phase, confidence (0-5), note. source: backfill is only for migrated rows.
"""


def parse_day(value) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def iso_day(value) -> str | None:
    day = parse_day(value)
    return day.isoformat() if day else None


def student_dir(student: str) -> Path:
    return STUDENTS / student


def ledger_path(student: str) -> Path:
    return student_dir(student) / "ledger.yaml"


def activity_path(student: str) -> Path:
    return student_dir(student) / "activity.yaml"


def queue_path(student: str) -> Path:
    return student_dir(student) / "queue.yaml"


def exam_attempts_path(student: str) -> Path:
    return student_dir(student) / "exam-attempts.yaml"


def narrative_listens_path(student: str) -> Path:
    return student_dir(student) / "narrative-listens.yaml"


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"Missing {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must be a mapping")
    return data


def dump_yaml(path: Path, data: dict) -> None:
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
        newline="\n",
    )


def lecture_index(manifest: dict | None = None) -> dict[str, dict]:
    """id -> {title, course, core} for every lecture in the catalogue."""
    manifest = manifest if manifest is not None else load_manifest()
    by_id: dict[str, dict] = {}
    for course, lec, _i, _n in iter_lectures(manifest):
        by_id[lec["id"]] = {
            "title": lec["title"],
            "course": course["code"],
            "core": course.get("type") == "core",
        }
    return by_id


def core_lecture_ids(manifest: dict) -> list[str]:
    ids: list[str] = []
    for course, lec, _i, _n in iter_lectures(manifest, types={"core"}):
        ids.append(lec["id"])
    return ids


def load_events(path: Path) -> list[dict]:
    """Return events in file order. Missing file yields an empty log."""
    if not path.is_file():
        return []
    data = load_yaml(path)
    raw = data.get("events") or []
    if not isinstance(raw, list):
        raise SystemExit(f"{path} events must be a list")
    events: list[dict] = []
    for i, item in enumerate(raw):
        events.append(normalize_event(item, index=i, path=path))
    return events


def normalize_event(item, *, index: int, path: Path | None = None) -> dict:
    where = f"{path} event {index}" if path else f"event {index}"
    if not isinstance(item, dict):
        raise SystemExit(f"{where} must be a mapping")
    day = parse_day(item.get("at"))
    lecture = item.get("lecture")
    action = item.get("action")
    if day is None or not lecture or not action:
        raise SystemExit(f"{where} needs at, lecture, and action")
    if action not in ACTIONS:
        raise SystemExit(f"{where} has unknown action {action!r}")
    event = {
        "_i": index,
        "at": day,
        "lecture": str(lecture),
        "action": str(action),
    }
    phase = item.get("phase")
    if phase:
        if phase not in PHASES:
            raise SystemExit(f"{where} has unknown phase {phase!r}")
        event["phase"] = str(phase)
    if item.get("confidence") is not None:
        confidence = int(item["confidence"])
        if not 0 <= confidence <= 5:
            raise SystemExit(f"{where} confidence must be 0–5")
        event["confidence"] = confidence
    note = item.get("note")
    if note:
        event["note"] = str(note).strip()
    source = item.get("source")
    if source:
        event["source"] = str(source)
    return event


def event_payload(event: dict) -> dict:
    """Serializable event. Drops the in-memory index so dumps cannot rewrite history fields."""
    payload = {
        "at": event["at"].isoformat() if isinstance(event["at"], date) else iso_day(event["at"]),
        "lecture": event["lecture"],
        "action": event["action"],
    }
    if event.get("phase"):
        payload["phase"] = event["phase"]
    if event.get("confidence") is not None:
        payload["confidence"] = int(event["confidence"])
    if event.get("note"):
        payload["note"] = event["note"]
    if event.get("source"):
        payload["source"] = event["source"]
    return payload


def write_events(path: Path, events: list[dict]) -> None:
    body = yaml.safe_dump(
        {"events": [event_payload(e) for e in events]},
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ACTIVITY_HEADER + body, encoding="utf-8", newline="\n")


def empty_activity() -> dict:
    return {"events": []}


EXAM_ATTEMPTS_HEADER = """\
# Append-only course examination attempts. Separate from lecture activity.yaml.
# Do not invent lecture listen events from exams. No scores, grades, or pass marks.
# Incomplete papers are fine to log. A later attempt is a new entry; never edit past ones.
#
# Fields: at, course, exam, optional title, mode, coverage, outcome,
# optional strengths[], gaps[], suggested_lectures[], next.
# mode examples: independent | guided | open-book | mixed
"""


def load_exam_attempts(student: str) -> list[dict]:
    """Return exam attempts newest-first. Missing file yields []."""
    path = exam_attempts_path(student)
    if not path.is_file():
        return []
    data = load_yaml(path)
    raw = data.get("attempts") or []
    if not isinstance(raw, list):
        raise SystemExit(f"{path} attempts must be a list")
    attempts: list[dict] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise SystemExit(f"{path} attempt {i} must be a mapping")
        day = parse_day(item.get("at"))
        course = item.get("course")
        exam = item.get("exam")
        if day is None or not course or not exam:
            raise SystemExit(f"{path} attempt {i} needs at, course, and exam")
        entry = {
            "_i": i,
            "at": day,
            "course": str(course),
            "exam": str(exam),
            "title": str(item["title"]).strip() if item.get("title") else "",
            "mode": str(item.get("mode") or "—"),
            "coverage": " ".join(str(item.get("coverage") or "").split()),
            "outcome": " ".join(str(item.get("outcome") or "").split()),
            "next": " ".join(str(item.get("next") or "").split()),
            "suggested_lectures": [
                str(x) for x in (item.get("suggested_lectures") or []) if x
            ],
        }
        attempts.append(entry)
    attempts.sort(key=lambda e: (e["at"], e["_i"]), reverse=True)
    return attempts


def write_empty_exam_attempts(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        EXAM_ATTEMPTS_HEADER + "attempts: []\n",
        encoding="utf-8",
        newline="\n",
    )


NARRATIVE_LISTENS_HEADER = """\
# Append-only Narrative Systems Story listens. Separate from lecture activity.yaml.
# Do not invent lecture listen events from stories. Not graded; optional history only.
# A later listen of the same story is a new entry; never edit past ones.
#
# Fields: at, story (NSNN), optional title, action (listen|skim|partial),
# optional shelf (Discovery|Focused|Panoramic), optional note.
"""


def load_narrative_listens(student: str) -> list[dict]:
    """Return story listens newest-first. Missing file yields []."""
    path = narrative_listens_path(student)
    if not path.is_file():
        return []
    data = load_yaml(path)
    raw = data.get("listens") or []
    if not isinstance(raw, list):
        raise SystemExit(f"{path} listens must be a list")
    listens: list[dict] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise SystemExit(f"{path} listen {i} must be a mapping")
        day = parse_day(item.get("at"))
        story = item.get("story")
        if day is None or not story:
            raise SystemExit(f"{path} listen {i} needs at and story")
        listens.append(
            {
                "_i": i,
                "at": day,
                "story": str(story),
                "title": str(item["title"]).strip() if item.get("title") else "",
                "action": str(item.get("action") or "listen"),
                "shelf": str(item["shelf"]).strip() if item.get("shelf") else "",
                "note": " ".join(str(item.get("note") or "").split()),
            }
        )
    listens.sort(key=lambda e: (e["at"], e["_i"]), reverse=True)
    return listens


def write_empty_narrative_listens(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        NARRATIVE_LISTENS_HEADER + "listens: []\n",
        encoding="utf-8",
        newline="\n",
    )


def profile_ledger(student: str, *, display_name: str | None = None, manifest: dict | None = None) -> dict:
    manifest = manifest if manifest is not None else load_manifest()
    today = date.today().isoformat()
    return {
        "student": student,
        "display_name": display_name or student,
        "created": today,
        "updated": today,
        "curriculum_version": str(manifest.get("version")),
        "learning_statuses": dict(LEARNING_STATUSES),
        "defaults": {
            "encore_intervals_days": dict(DEFAULT_INTERVAL),
        },
    }


def intervals_from(ledger: dict) -> dict:
    defaults = (ledger.get("defaults") or {}).get("encore_intervals_days") or {}
    merged = dict(DEFAULT_INTERVAL)
    merged.update(defaults)
    return merged


def fold_lecture(events: list[dict], intervals: dict) -> dict:
    """Current state of one lecture. events may be in any order."""
    ordered = sorted(events, key=lambda e: (e["at"], e.get("_i", 0)))
    phase = "unopened"
    phase_on: date | None = None
    confidence = 0
    notes = ""
    passes = 0
    dates: list[date] = []
    for event in ordered:
        dates.append(event["at"])
        if event["action"] in PASS_ACTIONS:
            passes += 1
        if event.get("phase"):
            phase = event["phase"]
            phase_on = event["at"]
        if event.get("confidence") is not None:
            confidence = int(event["confidence"])
        if event.get("note"):
            notes = event["note"]
    next_encore = None
    if phase in ENCORE_PHASES and phase_on is not None:
        days = intervals.get(phase)
        if days:
            next_encore = phase_on + timedelta(days=int(days))
    return {
        "status": phase,
        "confidence": confidence,
        "passes": passes,
        "opened_on": min(dates) if dates else None,
        "last_touched": max(dates) if dates else None,
        "next_encore": next_encore,
        "notes": notes,
    }


def fold_core(events: list[dict], manifest: dict, intervals: dict) -> dict[str, dict]:
    """One folded row per core lecture. Lectures with no events stay unopened."""
    catalog = lecture_index(manifest)
    grouped: dict[str, list[dict]] = {}
    for event in events:
        grouped.setdefault(event["lecture"], []).append(event)
    folded: dict[str, dict] = {}
    for lid in core_lecture_ids(manifest):
        meta = catalog[lid]
        row = fold_lecture(grouped.get(lid, []), intervals)
        row["title"] = meta["title"]
        row["course"] = meta["course"]
        folded[lid] = row
    return folded


def course_of(lecture_id: str, catalog: dict[str, dict]) -> str:
    meta = catalog.get(lecture_id)
    if meta:
        return meta["course"]
    return lecture_id.split("-", 1)[0]


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def iso_week_label(day: date) -> str:
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def heat_glyph(count: int) -> str:
    if count <= 0:
        return "·"
    if count == 1:
        return "░"
    if count == 2:
        return "▒"
    if count <= 4:
        return "▓"
    return "█"


def heat_cell(count: int) -> str:
    if count <= 0:
        return "·"
    return f"{heat_glyph(count)}{count}"


def md_cell(text: str, limit: int | None = None) -> str:
    collapsed = " ".join((text or "").split())
    if limit is not None and len(collapsed) > limit:
        collapsed = collapsed[: limit - 1] + "…"
    return collapsed.replace("|", "\\|")


QUEUE_ITEM_STATUSES = frozenset({"open", "done", "skipped"})
QUEUE_MODES = frozenset({"audio", "screen", "either"})


def load_queue(student: str) -> dict | None:
    """Curated short-term listen queue, or None if the student has no queue.yaml."""
    path = queue_path(student)
    if not path.is_file():
        return None
    data = load_yaml(path)
    if not data:
        return None
    return data


def events_by_lecture(events: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for event in events:
        grouped.setdefault(event["lecture"], []).append(event)
    return grouped


def queue_item_state(item: dict, by_lecture: dict[str, list[dict]]) -> str:
    """Resolve open/done/skipped. Explicit status wins; else any pass action → done."""
    explicit = item.get("status")
    if explicit:
        if explicit not in QUEUE_ITEM_STATUSES:
            raise SystemExit(f"queue item {item.get('lecture')!r} has bad status {explicit!r}")
        return str(explicit)
    lid = item.get("lecture")
    if not lid:
        raise SystemExit("queue item needs lecture")
    for event in by_lecture.get(str(lid), []):
        if event["action"] in PASS_ACTIONS:
            return "done"
    return "open"


def normalize_queue_item(item, *, where: str) -> dict:
    if not isinstance(item, dict):
        raise SystemExit(f"{where} must be a mapping")
    lid = item.get("lecture")
    if not lid:
        raise SystemExit(f"{where} needs lecture")
    mode = item.get("mode") or "either"
    if mode not in QUEUE_MODES:
        raise SystemExit(f"{where} has unknown mode {mode!r}")
    out = {
        "lecture": str(lid),
        "mode": str(mode),
        "why": str(item.get("why") or "").strip(),
    }
    if item.get("status"):
        out["status"] = str(item["status"])
    return out
