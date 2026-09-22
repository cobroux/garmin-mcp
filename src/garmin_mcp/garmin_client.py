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

    On first use it logs in with GARMIN_EMAIL/GARMIN_PASSWORD and stores the resulting
    session token in DEFAULT_TOKEN_STORE, so subsequent calls (and future runs of the
    server) resume the session without needing the password again, until it expires.
    """
    global _client
    with _lock:
        if _client is not None:
            return _client

        client = Garmin()
        try:
            client.login(str(DEFAULT_TOKEN_STORE))
        except (FileNotFoundError, GarminConnectAuthenticationError):
            email = os.environ.get("GARMIN_EMAIL")
            password = os.environ.get("GARMIN_PASSWORD")
            if not email or not password:
                raise GarminAuthError(
                    "No cached Garmin session found and GARMIN_EMAIL/GARMIN_PASSWORD "
                    "are not set. Set both environment variables and retry."
                ) from None
            try:
                client = Garmin(email=email, password=password, return_on_mfa=True)
                result = client.login()
                if isinstance(result, tuple) and result and result[0] == "needs_mfa":
                    raise GarminAuthError(
                        "Garmin account requires MFA, which this server does not support "
                        "interactively. Disable MFA for this account or log in once with "
                        "python-garminconnect's CLI to seed a cached token."
                    )
                DEFAULT_TOKEN_STORE.parent.mkdir(parents=True, exist_ok=True)
                client.garth.dump(str(DEFAULT_TOKEN_STORE))
            except GarminConnectAuthenticationError as exc:
                raise GarminAuthError(f"Garmin login failed: {exc}") from exc
        except GarminConnectConnectionError as exc:
            raise GarminAuthError(f"Could not reach Garmin Connect: {exc}") from exc

        _client = client
        return _client
