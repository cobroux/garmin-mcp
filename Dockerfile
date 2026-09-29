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
# This is a CMD, not an ENTRYPOINT, on purpose: a platform "custom start
# command" (e.g. Railway) replaces CMD but only appends to an ENTRYPOINT, so
# a second deployment of this same image can run the single-account MCP
# server instead (for the claude.ai connector) by overriding the start
# command to `garmin-mcp` - see README "Deux services distincts sur Railway".
CMD ["garmin-mcp-api"]
