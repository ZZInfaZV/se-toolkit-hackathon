"""MCP server entry point — exposes schedule tools to nanobot."""

import os
import sys
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from . import database
from . import sync


def create_server() -> Server:
    """Create and configure the schedule MCP server."""
    server = Server("schedule")

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="get_now",
                description="Get the lesson that is happening right now. Returns the subject, room, teacher, and time. Returns null if there is no lesson at this moment.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="get_schedule",
                description="Get the full schedule for a specific day of the week. Use this when the user asks about a specific day (e.g. 'what do I have on Monday?', 'schedule for Wednesday').",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "day": {
                            "type": "string",
                            "description": "Day of the week in Russian: Пн, Вт, Ср, Чт, Пт, Сб. You can also accept 'today', 'tomorrow' and will resolve it.",
                        },
                        "week_type": {
                            "type": "string",
                            "description": "Week type: 'even' (чётная), 'odd' (нечётная), or null for both.",
                            "enum": ["even", "odd"],
                        },
                    },
                    "required": ["day"],
                },
            ),
            Tool(
                name="get_room",
                description="Get the room (classroom) for a specific subject. Use when the user asks 'where is X?', 'what room for Y?', 'кабинет для Z'.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "Subject name or part of it (e.g. 'Сети', 'математика').",
                        },
                    },
                    "required": ["subject"],
                },
            ),
            Tool(
                name="get_teacher",
                description="Get the teacher for a specific subject. Use when the user asks 'who teaches X?', 'преподаватель для Y'.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "Subject name or part of it.",
                        },
                    },
                    "required": ["subject"],
                },
            ),
            Tool(
                name="get_week",
                description="Get the full week schedule (Monday through Saturday). Use when the user asks for the entire week schedule or 'расписание на неделю'.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "week_type": {
                            "type": "string",
                            "description": "Week type: 'even' (чётная), 'odd' (нечётная), or null for both.",
                            "enum": ["even", "odd"],
                        },
                    },
                },
            ),
            Tool(
                name="sync_schedule",
                description="Manually sync the schedule from Google Sheets to the local database. Use this when the user asks to update/refresh the schedule, or when the data seems outdated. This tool fetches data from the remote sheet and replaces all local data.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        db_conn = database.init_db()

        if name == "get_now":
            lesson = database.get_now(db_conn)
            if lesson:
                return [TextContent(
                    type="text",
                    text=f"Сейчас: {lesson['subject']}\n"
                         f"Кабинет: {lesson['room'] or 'не указан'}\n"
                         f"Преподаватель: {lesson['teacher'] or 'не указан'}\n"
                         f"Время: {lesson['time_start']}–{lesson['time_end']}",
                )]
            else:
                return [TextContent(type="text", text="Сейчас нет занятий.")]

        elif name == "get_schedule":
            day = arguments.get("day", "")
            week_type = arguments.get("week_type")

            # Resolve relative day names
            day_map = {
                "сегодня": None,
                "завтра": None,
            }
            today_idx = datetime.now().weekday()
            ru_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

            if day.lower() == "сегодня":
                day = ru_days[today_idx]
            elif day.lower() == "завтра":
                day = ru_days[(today_idx + 1) % 7]

            lessons = database.get_schedule(db_conn, day, week_type)
            if not lessons:
                return [TextContent(type="text", text=f"Нет занятий на {day}.")]

            lines = [f"Расписание на {day}:"]
            for l in lessons:
                week_label = f" ({l['week_type']})" if l["week_type"] != "both" else ""
                lines.append(
                    f"  {l['time_start']}–{l['time_end']} | {l['subject']}{week_label}"
                    f" | Каб. {l['room'] or '—'} | {l['teacher'] or '—'}"
                )
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_room":
            subject = arguments.get("subject", "")
            result = database.get_room(db_conn, subject)
            if result:
                return [TextContent(
                    type="text",
                    text=f"{result['subject']} → Кабинет: {result['room'] or 'не указан'}",
                )]
            else:
                return [TextContent(type="text", text=f"Не найден кабинет для предмета '{subject}'.")]

        elif name == "get_teacher":
            subject = arguments.get("subject", "")
            result = database.get_teacher(db_conn, subject)
            if result:
                return [TextContent(
                    type="text",
                    text=f"{result['subject']} → Преподаватель: {result['teacher'] or 'не указан'}",
                )]
            else:
                return [TextContent(type="text", text=f"Не найден преподаватель для предмета '{subject}'.")]

        elif name == "get_week":
            week_type = arguments.get("week_type")
            week_data = database.get_week(db_conn, week_type)
            if not week_data:
                return [TextContent(type="text", text="Расписание на неделю пусто. Попробуйте sync_schedule.")]

            lines = ["Расписание на неделю:"]
            for day, lessons in week_data.items():
                lines.append(f"\n{day}:")
                for l in lessons:
                    week_label = f" ({l['week_type']})" if l["week_type"] != "both" else ""
                    lines.append(
                        f"  {l['time_start']}–{l['time_end']} | {l['subject']}{week_label}"
                        f" | Каб. {l['room'] or '—'}"
                    )
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "sync_schedule":
            sheet_url = os.environ.get("SCHEDULE_SHEET_URL")
            if not sheet_url:
                return [TextContent(
                    type="text",
                    text="Ошибка: переменная окружения SCHEDULE_SHEET_URL не установлена.",
                )]
            try:
                result = sync.sync_from_sheet(sheet_url, db_conn)
                return [TextContent(
                    type="text",
                    text=f"Синхронизация: {result['status']}\n"
                         f"Удалено: {result.get('deleted', 0)}\n"
                         f"Добавлено: {result.get('inserted', 0)}\n"
                         f"Последнее обновление: {result.get('last_sync', '—')}",
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Ошибка синхронизации: {e}\n"
                         f"Используются локальные данные из базы.",
                )]

        else:
            raise ValueError(f"Unknown tool: {name}")

    return server


def main():
    """Run the MCP server."""
    server = create_server()
    # Auto-sync on startup (best-effort)
    try:
        sheet_url = os.environ.get("SCHEDULE_SHEET_URL")
        if sheet_url:
            db_conn = database.init_db()
            result = sync.sync_from_sheet(sheet_url, db_conn)
            print(f"[schedule-mcp] Startup sync: {result['status']} — {result.get('inserted', 0)} lessons", flush=True)
        else:
            print("[schedule-mcp] SCHEDULE_SHEET_URL not set, skipping startup sync", flush=True)
    except Exception as e:
        print(f"[schedule-mcp] Startup sync failed: {e}", flush=True)

    import asyncio
    from mcp.server.stdio import stdio_server

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
