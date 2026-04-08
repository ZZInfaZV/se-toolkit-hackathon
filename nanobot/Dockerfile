FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Copy entire workspace
COPY . /app/

# Create venv and install dependencies
RUN uv venv && \
    uv pip install ./mcp/mcp_schedule && \
    uv pip install ./nanobot-webchat && \
    uv pip install nanobot-ai

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /app/.venv /app/.venv

# Copy local package sources (direct URL installs reference source)
COPY --from=builder /app/nanobot-webchat/nanobot_webchat /app/.venv/lib/python3.11/site-packages/nanobot_webchat
COPY --from=builder /app/mcp/mcp_schedule/src/mcp_schedule /app/.venv/lib/python3.11/site-packages/mcp_schedule

# Copy nanobot config and workspace
COPY nanobot/config.json /app/nanobot/config.json
COPY nanobot/entrypoint.py /app/nanobot/entrypoint.py
COPY nanobot/workspace /app/nanobot/workspace

# Create data directory
RUN mkdir -p /app/data

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/mcp/mcp_schedule/src"

ENTRYPOINT ["python", "/app/nanobot/entrypoint.py"]
