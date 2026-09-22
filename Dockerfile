FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

# Session token cache, so a re-run doesn't need GARMIN_EMAIL/PASSWORD again
# as long as the volume below is mounted.
ENV GARMIN_TOKEN_STORE=/data/.garmin_mcp_tokens
VOLUME ["/data"]

# Only used when MCP_PUBLIC_URL is set (hosted HTTP mode); ignored for local
# stdio usage. Railway/most PaaS providers inject PORT themselves.
EXPOSE 8000

ENTRYPOINT ["garmin-mcp"]
