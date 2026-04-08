FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn[standard] jinja2 python-multipart

# Copy MCP schedule module (needed as dependency)
COPY mcp/mcp_schedule /app/mcp/mcp_schedule

# Copy webapp
COPY webapp /app/webapp

# Copy project pyproject for workspace resolution
COPY pyproject.toml /app/pyproject.toml

WORKDIR /app/webapp

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
