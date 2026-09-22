"""Thin wrapper around python-garminconnect handling auth and token caching."""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
)

DEFAULT_TOKEN_STORE = Path(os.environ.get("GARMIN_TOKEN_STORE", "~/.garmin_mcp_tokens")).expanduser()

_client: Garmin | None = None
_lock = Lock()


class GarminAuthError(RuntimeError):
    pass


def get_client() -> Garmin:
    """Return an authenticated Garmin client, logging in and caching the session token on disk.

    Garmin.login(tokenstore_path) already handles both cases in one call: it
    loads a cached session from tokenstore_path if present and still valid,
    and otherwise logs in with the client's email/password and writes the
    resulting session there - so future calls (and future runs of the
    server) resume the session without needing the password again, until it
    expires.
    """
    global _client
    with _lock:
        if _client is not None:
            return _client

        email = os.environ.get("GARMIN_EMAIL")
        password = os.environ.get("GARMIN_PASSWORD")
        if not email or not password:
            raise GarminAuthError("GARMIN_EMAIL and GARMIN_PASSWORD environment variables must be set.")

        client = Garmin(email=email, password=password)
        try:
            DEFAULT_TOKEN_STORE.parent.mkdir(parents=True, exist_ok=True)
            client.login(str(DEFAULT_TOKEN_STORE))
        except GarminConnectAuthenticationError as exc:
            raise GarminAuthError(f"Garmin login failed: {exc}") from exc
        except GarminConnectConnectionError as exc:
            raise GarminAuthError(f"Could not reach Garmin Connect: {exc}") from exc

        _client = client
        return _client
