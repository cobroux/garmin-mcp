"""Thin wrapper around python-garminconnect handling per-user auth and token caching.

Each Oltre user connects their own Garmin Connect account. Credentials are
only used once to log in; the resulting session is cached on disk under a
per-user directory and reused on subsequent calls until it expires. The
password itself is never persisted.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from threading import Lock

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
)

TOKEN_STORE_ROOT = Path(os.environ.get("GARMIN_TOKEN_STORE", "~/.garmin_mcp_tokens")).expanduser()

_clients: dict[str, Garmin] = {}
_lock = Lock()


class GarminAuthError(RuntimeError):
    pass


def _tokenstore_path(user_id: str) -> Path:
    return TOKEN_STORE_ROOT / user_id


def connect(user_id: str, email: str, password: str) -> None:
    """Log in to Garmin Connect with the given credentials and cache the
    resulting session for this user_id. Raises GarminAuthError on failure.

    Garmin.login(tokenstore) resumes a still-valid cached session from disk
    before it ever checks email/password - fine for the single-account MCP
    use case, but wrong here: this is the "verify and link this Garmin
    account" endpoint, so it must not let stale credentials silently pass
    just because *some* session (possibly logged in with different, older
    credentials) still happens to be cached for this user_id. Clear any
    existing session first to force a real credential check every time.
    """
    path = _tokenstore_path(user_id)
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)

    with _lock:
        _clients.pop(user_id, None)

    client = Garmin(email=email, password=password)
    try:
        client.login(str(path))
        # login() has been observed to return "successfully" without having
        # actually authenticated (some of its internal login strategies
        # silently fall through under Garmin's anti-bot challenges on
        # datacenter IPs like Railway's) - confirm with a real authenticated
        # call before trusting the session.
        client.get_user_profile()
    except GarminConnectAuthenticationError as exc:
        shutil.rmtree(path, ignore_errors=True)
        raise GarminAuthError(f"Garmin login failed: {exc}") from exc
    except GarminConnectConnectionError as exc:
        shutil.rmtree(path, ignore_errors=True)
        raise GarminAuthError(f"Could not reach Garmin Connect: {exc}") from exc
    except Exception as exc:
        shutil.rmtree(path, ignore_errors=True)
        raise GarminAuthError(f"Garmin login failed: {exc}") from exc

    with _lock:
        _clients[user_id] = client


def get_client(user_id: str) -> Garmin:
    """Return an authenticated Garmin client for this user_id, resuming the
    cached session from disk if it isn't already loaded in memory.

    Raises GarminAuthError if the user never connected, or their session has
    expired and needs reconnecting.
    """
    with _lock:
        client = _clients.get(user_id)
    if client is not None:
        return client

    path = _tokenstore_path(user_id)
    if not path.exists():
        raise GarminAuthError("No Garmin connection for this user. Connect a Garmin account first.")

    client = Garmin()
    try:
        client.login(str(path))
    except (GarminConnectAuthenticationError, GarminConnectConnectionError) as exc:
        raise GarminAuthError(f"Garmin session expired, please reconnect your account: {exc}") from exc

    with _lock:
        _clients[user_id] = client
    return client


def is_connected(user_id: str) -> bool:
    with _lock:
        if user_id in _clients:
            return True
    return _tokenstore_path(user_id).exists()


def disconnect(user_id: str) -> None:
    with _lock:
        _clients.pop(user_id, None)
    shutil.rmtree(_tokenstore_path(user_id), ignore_errors=True)


def build_activity_details(client: Garmin, activity_id: str) -> dict:
    """Normalized detail payload for one activity: summary stats, a GPS
    polyline (GPS-tracked activities only), per-lap splits, and strength
    exercise sets (strength activities only). Each piece is fetched and
    parsed independently and best-effort - most activity types don't have
    all of them, and a missing/unexpected shape on one must not take down
    the rest of the response.

    Shared by the REST API exposed in http_api.py and the duplicate REST
    routes mounted on the MCP server in server.py (the two services Railway
    actually deploys this project as) so they can't drift out of sync again.
    """
    try:
        summary = client.get_activity(activity_id)
    except Exception:
        summary = {}

    polyline = None
    try:
        details = client.get_activity_details(activity_id, maxpoly=2000)
        points = (details.get("geoPolylineDTO") or {}).get("polyline") or []
        parsed = [
            {"lat": p["lat"], "lon": p["lon"]}
            for p in points
            if p.get("lat") is not None and p.get("lon") is not None
        ]
        polyline = parsed or None
    except Exception:
        polyline = None

    splits: list[dict] = []
    try:
        splits_raw = client.get_activity_splits(activity_id)
        for lap in splits_raw.get("lapDTOs", []):
            splits.append({
                "distance": lap.get("distance"),
                "duration": lap.get("duration"),
                "elevationGain": lap.get("elevationGain"),
                "averageSpeed": lap.get("averageSpeed"),
                "averageHR": lap.get("averageHR"),
            })
    except Exception:
        splits = []

    exercise_sets: list[dict] = []
    try:
        sets_raw = client.get_activity_exercise_sets(activity_id)
        for s in sets_raw.get("exerciseSets", []):
            if s.get("setType") != "ACTIVE":
                continue
            exercises = s.get("exercises") or []
            name = exercises[0].get("name") if exercises else None
            weight = s.get("weight")
            exercise_sets.append({
                "name": name,
                "reps": s.get("repetitionCount"),
                "weightKg": (weight / 1000.0) if weight else None,
                "duration": s.get("duration"),
            })
    except Exception:
        exercise_sets = []

    activity_type = summary.get("activityType") or {}
    return {
        "activityId": summary.get("activityId", activity_id),
        "name": summary.get("activityName"),
        "sportType": activity_type.get("typeKey"),
        "startLocal": summary.get("startTimeLocal"),
        "distance": summary.get("distance"),
        "duration": summary.get("duration"),
        "elevationGain": summary.get("elevationGain"),
        "elevationLoss": summary.get("elevationLoss"),
        "calories": summary.get("calories"),
        "averageHR": summary.get("averageHR"),
        "maxHR": summary.get("maxHR"),
        "averageSpeed": summary.get("averageSpeed"),
        "maxSpeed": summary.get("maxSpeed"),
        "polyline": polyline,
        "splits": splits,
        "exerciseSets": exercise_sets,
    }
