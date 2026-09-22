"""Plain REST API exposing Garmin Connect data, for services (like the Oltre
backend) that need per-user Garmin data over HTTP instead of MCP.

Each Oltre user connects their own Garmin Connect account via POST
/users/{user_id}/connect. Nothing here is protected by its own auth -
this service is meant to sit on a private network, only reachable from the
backend that calls it (e.g. the Oltre Spring Boot backend), never exposed
directly to the internet.
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from garmin_mcp.garmin_client import (
    GarminAuthError,
    connect as garmin_connect,
    disconnect as garmin_disconnect,
    get_client,
    is_connected,
)

app = FastAPI(title="garmin-mcp REST API")


class ConnectRequest(BaseModel):
    email: str
    password: str


def _today() -> str:
    return dt.date.today().isoformat()


def _client_or_401(user_id: str) -> Any:
    try:
        return get_client(user_id)
    except GarminAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/users/{user_id}/connect")
def connect_user(user_id: str, body: ConnectRequest) -> dict:
    try:
        garmin_connect(user_id, body.email, body.password)
    except GarminAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {"connected": True}


@app.get("/users/{user_id}/status")
def status(user_id: str) -> dict:
    return {"connected": is_connected(user_id)}


@app.delete("/users/{user_id}/connect")
def disconnect_user(user_id: str) -> dict:
    garmin_disconnect(user_id)
    return {"connected": False}


@app.get("/users/{user_id}/activities")
def activities(user_id: str, since: str | None = None, limit: int = 50, start: int = 0) -> Any:
    """List recent activities, optionally filtered to those starting on/after
    `since` (ISO date, e.g. the Monday of a given week)."""
    client = _client_or_401(user_id)
    acts = client.get_activities(start, limit)
    if since:
        cutoff = dt.date.fromisoformat(since)
        acts = [a for a in acts if dt.date.fromisoformat(a["startTimeLocal"][:10]) >= cutoff]
    return acts


@app.get("/users/{user_id}/daily-summary")
def daily_summary(user_id: str, date: str | None = None) -> Any:
    client = _client_or_401(user_id)
    return client.get_user_summary(date or _today())


def run() -> None:
    import uvicorn

    uvicorn.run(
        "garmin_mcp.http_api:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
    )
