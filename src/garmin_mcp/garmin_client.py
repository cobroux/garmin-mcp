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
