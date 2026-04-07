FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Copy workspace MCP server
COPY mcp/mcp_schedule /app/mcp/mcp_schedule

# Copy nanobot project
COPY nanobot/pyproject.toml /app/nanobot/pyproject.toml

# Install dependencies
WORKDIR /app/nanobot
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /app/nanobot/.venv /app/.venv
COPY --from=builder /app/mcp/mcp_schedule /app/mcp/mcp_schedule

# Copy nanobot config and workspace
COPY nanobot/config.json /app/nanobot/config.json
COPY nanobot/entrypoint.py /app/nanobot/entrypoint.py
COPY nanobot/workspace /app/nanobot/workspace

# Create data directory
RUN mkdir -p /app/data

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/mcp/mcp_schedule/src"

ENTRYPOINT ["python", "/app/nanobot/entrypoint.py"]
