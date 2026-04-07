"""Google Sheets sync module — fetches schedule data from a public sheet."""

import os
import re
from typing import Optional

import gspread


def extract_spreadsheet_id(url: str) -> str:
    """Extract the spreadsheet ID from a Google Sheets URL."""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        raise ValueError(f"Cannot extract spreadsheet ID from URL: {url}")
    return match.group(1)


def fetch_schedule(sheet_url: str) -> list[dict]:
    """Fetch all lessons from a public Google Sheet.

    Expected columns (order matters, header row is skipped):
        Day | Time | Subject | Room | Teacher

    Time format: "HH:MM-HH:MM" (e.g. "08:30-10:00")
    Week type: inferred from a second sheet or a column if present.
    For simplicity, we assume a single sheet with week_type = 'both'.
    """
    gc = gspread.Client()
    # For public sheets, we can open by URL without auth
    # But gspread requires some auth. For public sheets, we use a workaround:
    # We'll fetch via the published CSV endpoint instead.
    import urllib.request
    import csv
    from io import StringIO

    spreadsheet_id = extract_spreadsheet_id(sheet_url)
    # Try to get the first sheet as CSV (public access)
    csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv"

    try:
        with urllib.request.urlopen(csv_url, timeout=10) as response:
            raw = response.read().decode("utf-8")
    except Exception as e:
        raise ConnectionError(f"Failed to fetch Google Sheet: {e}") from e

    reader = csv.reader(StringIO(raw))
    rows = list(reader)

    if len(rows) < 2:
        return []

    # First row is header — detect columns
    headers = [h.strip().lower() for h in rows[0]]

    # Map common column names
    col_map = {}
    for i, h in enumerate(headers):
        if h in ("день", "day", "день недели"):
            col_map["day"] = i
        elif h in ("время", "time", "часы"):
            col_map["time"] = i
        elif h in ("предмет", "subject", "название", "дисциплина"):
            col_map["subject"] = i
        elif h in ("кабинет", "room", "аудитория", "ауд"):
            col_map["room"] = i
        elif h in ("преподаватель", "teacher", "препод", "учитель"):
            col_map["teacher"] = i
        elif h in ("неделя", "week", "тип недели", "week_type"):
            col_map["week_type"] = i

    # Fallback: assume positional order if columns not detected
    if not col_map:
        # Assume: Day | Time | Subject | Room | Teacher
        col_map = {"day": 0, "time": 1, "subject": 2, "room": 3, "teacher": 4}

    lessons = []
    for row in rows[1:]:
        if not row or all(cell.strip() == "" for cell in row):
            continue

        day = row[col_map["day"]].strip() if col_map.get("day") is not None and col_map["day"] < len(row) else ""
        time_str = row[col_map["time"]].strip() if col_map.get("time") is not None and col_map["time"] < len(row) else ""
        subject = row[col_map["subject"]].strip() if col_map.get("subject") is not None and col_map["subject"] < len(row) else ""

        if not day or not time_str or not subject:
            continue

        # Parse time range
        time_parts = time_str.replace("–", "-").replace("—", "-").split("-")
        if len(time_parts) == 2:
            time_start = time_parts[0].strip()
            time_end = time_parts[1].strip()
        else:
            continue  # Skip rows without valid time range

        room = row[col_map["room"]].strip() if col_map.get("room") is not None and col_map["room"] < len(row) else ""
        teacher = row[col_map["teacher"]].strip() if col_map.get("teacher") is not None and col_map["teacher"] < len(row) else ""
        week_type = row[col_map["week_type"]].strip() if col_map.get("week_type") is not None and col_map["week_type"] < len(row) else "both"

        # Normalize week_type
        week_type_lower = week_type.lower()
        if "чёт" in week_type_lower or "even" in week_type_lower:
            week_type = "even"
        elif "нечёт" in week_type_lower or "odd" in week_type_lower:
            week_type = "odd"
        else:
            week_type = "both"

        lessons.append({
            "day": day,
            "time_start": time_start,
            "time_end": time_end,
            "subject": subject,
            "room": room or None,
            "teacher": teacher or None,
            "week_type": week_type,
            "synced_at": None,  # Will be set by the database module
        })

    return lessons


def sync_from_sheet(sheet_url: str, db_conn) -> dict:
    """Fetch from Google Sheets and update the local database.

    Returns a status dict with counts and last_sync timestamp.
    """
    from datetime import datetime
    from . import database

    lessons = fetch_schedule(sheet_url)

    if not lessons:
        return {"status": "no_data", "message": "No lessons found in the sheet"}

    # Clear and re-insert
    deleted = database.clear_lessons(db_conn)

    # Set synced_at timestamp
    now = datetime.now().isoformat()
    for lesson in lessons:
        lesson["synced_at"] = now

    inserted = database.insert_lessons(db_conn, lessons)

    return {
        "status": "synced",
        "deleted": deleted,
        "inserted": inserted,
        "last_sync": now,
    }
