"""Google Sheets sync module — fetches schedule data from a public sheet."""

import re
from typing import Optional


def extract_spreadsheet_id(url: str) -> str:
    """Extract the spreadsheet ID from a Google Sheets URL."""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        raise ValueError(f"Cannot extract spreadsheet ID from URL: {url}")
    return match.group(1)


def _parse_time(time_str: str):
    """Parse 'HH:MM-HH:MM' into (start, end) or return None."""
    if not time_str:
        return None
    time_str = time_str.replace("\u2013", "-").replace("\u2014", "-").strip()
    parts = time_str.split("-")
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return None


def _clean_room(room: str) -> str:
    """Clean room value — strip annotations, keep first room number."""
    if not room:
        return ""
    # "461 STARTS ON 07/02" → "461"
    room = re.sub(r"\s*STARTS.*$", "", room, flags=re.IGNORECASE).strip()
    # "317 STARTS AT 11:00 EXCEPT 27/04" → "317"
    room = re.sub(r"\s*EXCEPT.*$", "", room, flags=re.IGNORECASE).strip()
    # "101 (209 ON 22/09)" → "101"
    room = re.sub(r"\s*\(.*?\)", "", room).strip()
    room = room.split("/")[0].split("|")[0].strip()
    return room


def _is_room_like(s: str) -> bool:
    if not s:
        return False
    # Room numbers: "108", "102/103/104", "106 / 107", "317 STARTS AT 11:00"
    # "461 STARTS ON 07/02", "101 (209 ON 22/09)"
    if re.match(r"^\d{2,4}\s*(STARTS|ON|/|$|\()", s, re.IGNORECASE):
        return True
    if re.match(r"^[\d/|()\s]+$", s):
        return True
    return False


# Mapping from English day names to Russian abbreviations
DAY_EN_TO_RU = {
    "MONDAY": "Пн",
    "TUESDAY": "Вт",
    "WEDNESDAY": "Ср",
    "THURSDAY": "Чт",
    "FRIDAY": "Пт",
    "SATURDAY": "Сб",
    "SUNDAY": "Вс",
}


def _is_day_marker(s: str) -> Optional[str]:
    if not s:
        return None
    m = re.match(r"^(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)", s, re.IGNORECASE)
    if m:
        day_en = m.group(1).upper()
        return DAY_EN_TO_RU.get(day_en)
    return None


def _is_time_range(s: str) -> bool:
    return bool(re.match(r"^\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}$", s))


def _is_group_header(s: str) -> bool:
    """Check if cell is a group label like 'B25-CSE-05 (27)' or 'B25-DSAI-01 (26)'."""
    return bool(re.match(r"^B\d{2}-[A-Z\d]+-\d{2}\s*\(\d+\)$", s))


def _parse_subject_line(s: str):
    """Parse 'Subject (type) [Teacher]' or 'Subject (type)' → (subject, lesson_type, teacher_rest)."""
    m = re.match(r"^(.+?)\s*\((lec|tut|lab)\)\s*(.*)?$", s, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip(), m.group(2).strip().lower(), (m.group(3) or "").strip()
    return None, None, None


def _parse_row0_cell(cell: str, group: str) -> tuple[str, str, str]:
    """Parse Row 0 cell which has format: 'BS - Year 1 B25-CSE-01 (27) Subject (type) Teacher'.
    
    Returns: (subject_with_type, teacher, room_or_empty)
    """
    if not cell:
        return None, None, None
    
    # Remove super-category prefix like "BS - Year 1 " or "MS - Year 1 "
    cell = re.sub(r"^(BS|MS|PhD)\s*-\s*Year\s*\d+\s*", "", cell).strip()
    
    # Remove group header if present (e.g., "B25-CSE-01 (27)")
    cell = re.sub(r"^B\d{2}-[A-Z\d]+-\d{2}\s*\(\d+\)\s*", "", cell).strip()
    cell = re.sub(r"^M\d{2}-[A-Z\d]+-\d{2}\s*\(\d+\)\s*", "", cell).strip()
    cell = re.sub(r"^PhD\s*\(\d+\)\s*", "", cell).strip()
    
    if not cell:
        return None, None, None
    
    # Now parse what remains as subject (type) teacher
    subj, ltype, teacher_rest = _parse_subject_line(cell)
    if subj and ltype:
        return f"{subj} ({ltype})", teacher_rest or None, None
    
    # If no (type) marker, treat entire cell as subject
    return cell, None, None


# ---------------------------------------------------------------------------
# Sheet-specific group column mappings
# ---------------------------------------------------------------------------
GROUP_MAPS = {
    # Old sheet
    "1GlRGsy6-UvdI": {
        "bs_year1": [1, 9],
    },
    # New sheet
    "1qetU56NwowMgHS": {
        "b25-cse-01": [1],
        "b25-cse-02": [2],
        "b25-cse-03": [3],
        "b25-cse-04": [4],
        "b25-cse-05": [5],
        "b25-dsai-01": [6],
        "b25-dsai-02": [7],
        "b25-dsai-03": [8],
        "b25-dsai-04": [9],
        "b25-dsai-05": [10],
    },
}


def _detect_sheet_id_prefix(url: str) -> str:
    """Return the full spreadsheet ID for GROUP_MAPS lookup."""
    return extract_spreadsheet_id(url)


def _get_data_cols(url: str, group: str) -> list[int]:
    prefix = _detect_sheet_id_prefix(url)
    maps = GROUP_MAPS.get(prefix, {})
    cols = maps.get(group)
    if cols is not None:
        return cols
    return [1, 9]


def fetch_schedule(sheet_url: str, group: str = "b25-cse-05") -> list[dict]:
    """Fetch lessons from Google Sheets."""
    import urllib.request
    import csv
    from io import StringIO

    spreadsheet_id = extract_spreadsheet_id(sheet_url)
    csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv"

    try:
        with urllib.request.urlopen(csv_url, timeout=10) as response:
            raw = response.read().decode("utf-8")
    except Exception as e:
        raise ConnectionError(f"Failed to fetch Google Sheet: {e}") from e

    reader = csv.reader(StringIO(raw))
    rows = list(reader)

    if len(rows) < 3:
        return []

    data_cols = _get_data_cols(sheet_url, group)
    lessons = []
    current_day = ""
    current_time = None

    # Track consumed rows per column to avoid re-parsing teacher/room rows as subjects
    consumed = set()  # set of (row_idx, col) tuples

    for row_idx, row in enumerate(rows):
        # --- Day / time from col 0 ---
        col0 = row[0].strip() if len(row) > 0 else ""
        day = _is_day_marker(col0)
        if day:
            current_day = day

        time_in_col0 = _parse_time(col0) if _is_time_range(col0) else None
        if not time_in_col0:
            tm = re.search(r"(\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})", col0)
            if tm:
                time_in_col0 = _parse_time(tm.group(1))

        if time_in_col0:
            current_time = time_in_col0

        # --- Process each data column ---
        for dc in data_cols:
            if dc >= len(row):
                continue

            key = (row_idx, dc)
            if key in consumed:
                continue

            cell = row[dc].strip()
            if not cell:
                continue

            # Handle Row 0 specially - it has merged cells with super-category + group + subject + teacher
            # Detect if this is a Row 0 cell (has super-category or group header with subject)
            is_row0 = bool(re.match(r"^(BS|MS|PhD)\s*-\s*Year\s*\d+", cell))
            
            if is_row0:
                # Parse the complex Row 0 cell
                subject_with_type, teacher_from_cell, _ = _parse_row0_cell(cell, group)
                
                if not subject_with_type:
                    continue
                
                # Look for room in next row
                room = None
                if (row_idx + 1, dc) not in consumed:
                    nxt = rows[row_idx + 1][dc].strip() if row_idx + 1 < len(rows) and dc < len(rows[row_idx + 1]) else ""
                    if nxt and _is_room_like(nxt):
                        room = _clean_room(nxt)
                        consumed.add((row_idx + 1, dc))
                
                # If teacher not found in cell, look in next non-room row
                teacher = teacher_from_cell
                if not teacher:
                    for offset in [1, 2]:
                        ri = row_idx + offset
                        if ri < len(rows) and dc < len(rows[ri]) and (ri, dc) not in consumed:
                            nxt = rows[ri][dc].strip()
                            if nxt and not _is_room_like(nxt):
                                teacher = nxt
                                consumed.add((ri, dc))
                                break
                
                if current_day and current_time:
                    lessons.append({
                        "day": current_day,
                        "time_start": current_time[0],
                        "time_end": current_time[1],
                        "subject": subject_with_type,
                        "room": room,
                        "teacher": teacher,
                        "week_type": "both",
                        "synced_at": None,
                    })
                continue

            # Skip pure group headers (e.g., "B25-CSE-05 (26)")
            if _is_group_header(cell):
                continue

            # Normal rows parsing (rows 1+)
            subj, ltype, teacher_rest = _parse_subject_line(cell)

            if subj and ltype:
                # Subject with (type)
                teacher = teacher_rest
                room = ""

                if not teacher and (row_idx + 1, dc) not in consumed:
                    nxt = rows[row_idx + 1][dc].strip() if row_idx + 1 < len(rows) and dc < len(rows[row_idx + 1]) else ""
                    if nxt and not _is_room_like(nxt):
                        teacher = nxt
                        consumed.add((row_idx + 1, dc))

                # Look for room in next rows
                for offset in [1, 2]:
                    ri = row_idx + offset
                    if ri < len(rows) and dc < len(rows[ri]) and (ri, dc) not in consumed:
                        nxt = rows[ri][dc].strip()
                        if _is_room_like(nxt):
                            room = _clean_room(nxt)
                            consumed.add((ri, dc))
                            break

                if current_day and current_time:
                    lessons.append({
                        "day": current_day,
                        "time_start": current_time[0],
                        "time_end": current_time[1],
                        "subject": f"{subj} ({ltype})",
                        "room": room or None,
                        "teacher": teacher or None,
                        "week_type": "both",
                        "synced_at": None,
                    })

            elif not _is_room_like(cell) and not _is_day_marker(cell) and not _is_time_range(cell):
                # Subject without (type) marker — e.g. "Foreign Language"
                teacher = None
                room = None

                # Look for teacher in next row
                if (row_idx + 1, dc) not in consumed:
                    nxt = rows[row_idx + 1][dc].strip() if row_idx + 1 < len(rows) and dc < len(rows[row_idx + 1]) else ""
                    if nxt and not _is_room_like(nxt):
                        teacher = nxt
                        consumed.add((row_idx + 1, dc))

                # Look for room
                for offset in [1, 2]:
                    ri = row_idx + offset
                    if ri < len(rows) and dc < len(rows[ri]) and (ri, dc) not in consumed:
                        nxt = rows[ri][dc].strip()
                        if _is_room_like(nxt):
                            room = _clean_room(nxt)
                            consumed.add((ri, dc))
                            break

                if current_day and current_time:
                    lessons.append({
                        "day": current_day,
                        "time_start": current_time[0],
                        "time_end": current_time[1],
                        "subject": cell,
                        "room": room,
                        "teacher": teacher,
                        "week_type": "both",
                        "synced_at": None,
                    })

    # Deduplicate
    seen = set()
    unique = []
    for l in lessons:
        key = (l["day"], l["time_start"], l["time_end"], l["subject"])
        if key not in seen:
            seen.add(key)
            unique.append(l)

    return unique


def sync_from_sheet(sheet_url: str, db_conn, group: str = "b25-cse-05") -> dict:
    """Fetch from Google Sheets and update the local database."""
    from datetime import datetime
    from . import database

    lessons = fetch_schedule(sheet_url, group=group)

    if not lessons:
        return {"status": "no_data", "message": "No lessons found in the sheet"}

    deleted = database.clear_lessons(db_conn)
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
