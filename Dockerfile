FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

# Per-user session token cache, so a re-run doesn't need each user to
# reconnect, as long as a volume is mounted at /data (e.g.
# `docker run -v ...:/data`, or a Railway Volume attached at /data -
# Railway rejects a Dockerfile VOLUME instruction, so this is left to be
# configured at runtime).
ENV GARMIN_TOKEN_STORE=/data/.garmin_mcp_tokens

EXPOSE 8000

# REST API (multi-user, used by services like the Oltre backend) by default.
# Override with `--entrypoint garmin-mcp` to run the MCP stdio/HTTP server
# instead (single account via GARMIN_EMAIL/GARMIN_PASSWORD).
ENTRYPOINT ["garmin-mcp-api"]
