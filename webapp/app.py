"""Simple web app for schedule browsing — no LLM needed."""

import os
from pathlib import Path
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.gzip import GZipMiddleware
from jinja2 import Environment, FileSystemLoader
import sys

# Add MCP schedule package to path so we can reuse db/sync modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp" / "mcp_schedule" / "src"))

from mcp_schedule.database import init_db, get_schedule, get_week, get_now
from mcp_schedule.sync import sync_from_sheet, fetch_schedule

app = FastAPI(title="Schedule Viewer")

# Prevent browser from caching POST responses
@app.middleware("http")
async def no_cache(request: Request, call_next):
    response = await call_next(request)
    if request.method == "POST":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SHEET_URL = os.environ.get(
    "SCHEDULE_SHEET_URL",
    "https://docs.google.com/spreadsheets/d/1qetU56NwowMgHS4ZBSFDO5omeO6FHPYSIz6sde86yo/edit",
)
DB_PATH = os.environ.get("SCHEDULE_DB_PATH", "data/schedule.db")

GROUPS = [
    {"key": "b25-cse-01", "label": "CSE-01"},
    {"key": "b25-cse-02", "label": "CSE-02"},
    {"key": "b25-cse-03", "label": "CSE-03"},
    {"key": "b25-cse-04", "label": "CSE-04"},
    {"key": "b25-cse-05", "label": "CSE-05"},
    {"key": "b25-dsai-01", "label": "DSAI-01"},
    {"key": "b25-dsai-02", "label": "DSAI-02"},
    {"key": "b25-dsai-03", "label": "DSAI-03"},
    {"key": "b25-dsai-04", "label": "DSAI-04"},
    {"key": "b25-dsai-05", "label": "DSAI-05"},
]

DAYS = [
    {"key": "Пн", "label": "Понедельник"},
    {"key": "Вт", "label": "Вторник"},
    {"key": "Ср", "label": "Среда"},
    {"key": "Чт", "label": "Четверг"},
    {"key": "Пт", "label": "Пятница"},
    {"key": "Сб", "label": "Суббота"},
]

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
templates_path = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(str(templates_path)))


def render_template(name: str, context: dict) -> str:
    """Render a Jinja2 template and return HTML string."""
    template = env.get_template(name)
    return template.render(**context)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def get_db():
    """Get a database connection (creates DB file if missing)."""
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return init_db(db_path)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page — group + day selector."""
    context = {
        "request": request,
        "groups": GROUPS,
        "days": DAYS,
        "schedule": None,
        "selected_group": "",
        "selected_day": "",
        "mode": "day",
        "sync_status": None,
        "now_lesson": None,
    }
    return Response(content=render_template("index.html", context), media_type="text/html")


@app.post("/schedule", response_class=HTMLResponse)
async def show_schedule(
    request: Request,
    group: str = Form(default="b25-cse-05"),
    day: str = Form(default=""),
    mode: str = Form(default="day"),
):
    """Show schedule for selected group + day (or full week)."""
    conn = get_db()

    # Ensure data exists for this group — sync if DB is empty
    cursor = conn.execute("SELECT COUNT(*) as cnt FROM lessons")
    count = cursor.fetchone()["cnt"]
    sync_status = None
    if count == 0:
        try:
            result = sync_from_sheet(SHEET_URL, conn, group=group)
            sync_status = result
        except Exception as e:
            sync_status = {"status": "error", "message": str(e)}

    now_lesson = get_now(conn)

    if mode == "now":
        schedule = None
        if now_lesson:
            schedule = [now_lesson]
        context = {
            "request": request,
            "groups": GROUPS,
            "days": DAYS,
            "schedule": schedule,
            "selected_group": group,
            "selected_day": "",
            "mode": "now",
            "sync_status": sync_status,
            "now_lesson": now_lesson,
        }
        return Response(content=render_template("index.html", context), media_type="text/html")

    if mode == "week" or not day:
        week_data = get_week(conn)
        # Flatten week into a list with day headers
        schedule = []
        for day_key, day_label in DAYS:
            lessons = week_data.get(day_key, [])
            if lessons:
                schedule.append({"_day_header": day_label, "_is_header": True})
                for lesson in lessons:
                    lesson["_is_header"] = False
                    schedule.append(lesson)
        selected_day_label = "Вся неделя"
    else:
        lessons = get_schedule(conn, day)
        schedule = lessons
        selected_day_label = next((d["label"] for d in DAYS if d["key"] == day), day)

    group_label = next((g["label"] for g in GROUPS if g["key"] == group), group)

    context = {
        "request": request,
        "groups": GROUPS,
        "days": DAYS,
        "schedule": schedule,
        "selected_group": group,
        "selected_day": day,
        "mode": mode,
        "sync_status": sync_status,
        "now_lesson": now_lesson,
        "group_label": group_label,
        "day_label": selected_day_label,
    }
    return Response(content=render_template("index.html", context), media_type="text/html")


@app.post("/sync", response_class=HTMLResponse)
async def sync_schedule(
    request: Request,
    group: str = Form(default="b25-cse-05"),
):
    """Manually sync schedule from Google Sheets for a specific group."""
    conn = get_db()
    try:
        result = sync_from_sheet(SHEET_URL, conn, group=group)
    except Exception as e:
        result = {"status": "error", "message": str(e)}

    context = {
        "request": request,
        "groups": GROUPS,
        "days": DAYS,
        "schedule": None,
        "selected_group": group,
        "selected_day": "",
        "mode": "day",
        "sync_status": result,
        "now_lesson": None,
    }
    return Response(content=render_template("index.html", context), media_type="text/html")


@app.get("/api/schedule")
async def api_schedule(group: str = "b25-cse-05", day: str = ""):
    """JSON API — get schedule for a group + day."""
    conn = get_db()
    if day:
        lessons = get_schedule(conn, day)
    else:
        lessons = get_week(conn)
    return {"group": group, "day": day or "all", "lessons": lessons}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
