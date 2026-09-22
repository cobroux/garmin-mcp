FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

# Session token cache, so a re-run doesn't need GARMIN_EMAIL/PASSWORD again
# as long as a volume is mounted at /data (e.g. `docker run -v ...:/data`,
# or a Railway Volume attached at /data - Railway rejects a Dockerfile
# VOLUME instruction, so this is left to be configured at runtime).
ENV GARMIN_TOKEN_STORE=/data/.garmin_mcp_tokens

# Only used when MCP_PUBLIC_URL is set (hosted HTTP mode); ignored for local
# stdio usage. Railway/most PaaS providers inject PORT themselves.
EXPOSE 8000

ENTRYPOINT ["garmin-mcp"]
