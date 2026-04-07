# Schedule Bot

AI-powered schedule assistant built with **nanobot**. Answers natural-language questions about classes, rooms, and teachers — even when offline.

## Features

- **Natural language queries**: "Что сейчас?", "Где математика?", "Расписание на среду"
- **Offline resilience**: Data is mirrored from Google Sheets into a local SQLite database. If the sheet is unreachable, the bot works with cached data.
- **Auto-sync**: Fetches latest schedule on startup. Manual sync via `sync_schedule` tool.
- **Web chat**: WebSocket-based chat interface via nanobot webchat channel.

## Architecture

```
[Web Chat] → [Nanobot Agent] → [LLM API]
                      |
              [Schedule MCP Server]
                      |
              [Local SQLite DB] ← syncs from ← [Google Sheets]
```

### Components

| Component | Description |
|-----------|-------------|
| **nanobot** | AI agent framework — runs the agent loop, manages tools and channels |
| **Schedule MCP Server** | Python MCP server with tools: `get_now`, `get_schedule`, `get_room`, `get_teacher`, `get_week`, `sync_schedule` |
| **SQLite Database** | Local cache of schedule data (`data/schedule.db`) |
| **Google Sheets** | Primary data source — synced on startup and on demand |

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Access to an OpenAI-compatible LLM API (Ollama, vLLM, OpenAI, etc.)

### Local Development

1. **Clone and set up:**
   ```sh
   cd schedule-bot
   cp .env.example .env
   # Edit .env with your LLM credentials
   ```

2. **Install dependencies:**
   ```sh
   uv sync
   ```

3. **Run the MCP server directly (for testing):**
   ```sh
   cd mcp/mcp_schedule
   SCHEDULE_SHEET_URL="https://docs.google.com/spreadsheets/d/1GlRGsy6-UvdIqj_E-iT9UBz9gvBNba5qHTjfm-npyjI/" \
     uv run python -m mcp_schedule
   ```

4. **Run nanobot:**
   ```sh
   cd nanobot
   uv run nanobot gateway
   ```

5. **Open the web chat** at `http://localhost:8765` (or wherever nanobot webchat is exposed).

### Docker Deployment

1. **Configure environment:**
   ```sh
   cp .env.example .env
   # Edit .env with your LLM credentials
   ```

2. **Build and run:**
   ```sh
   docker compose up --build -d
   ```

3. **Access the web chat** at `http://<your-host>:8765`.

## MCP Tools

| Tool | Description |
|------|-------------|
| `get_now` | Current lesson (based on system time) |
| `get_schedule(day, week_type)` | Full schedule for a day |
| `get_room(subject)` | Classroom for a subject |
| `get_teacher(subject)` | Teacher for a subject |
| `get_week(week_type)` | Full week schedule |
| `sync_schedule` | Refresh data from Google Sheets |

## Project Structure

```
schedule-bot/
├── mcp/
│   └── mcp_schedule/          # MCP server package
│       ├── src/mcp_schedule/
│       │   ├── __init__.py
│       │   ├── server.py      # MCP server + tool definitions
│       │   ├── database.py    # SQLite operations
│       │   └── sync.py        # Google Sheets sync
│       └── pyproject.toml
├── nanobot/
│   ├── config.json            # Nanobot configuration
│   ├── entrypoint.py          # Docker entrypoint
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── workspace/
│       └── skills/
│           └── schedule/
│               └── SKILL.md   # Agent skill prompt
├── data/                      # Local SQLite database (gitignored)
├── docker-compose.yml
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

## License

MIT
