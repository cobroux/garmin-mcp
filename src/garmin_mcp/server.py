"""MCP server exposing Garmin Connect data as tools."""

from __future__ import annotations

import datetime as dt
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from garmin_mcp.garmin_client import GarminAuthError, get_client

LOGIN_PAGE = """<!doctype html>
<html><head><title>garmin-mcp</title></head>
<body style="font-family: sans-serif; max-width: 420px; margin: 80px auto;">
<h2>garmin-mcp</h2>
<p>Enter the app password to authorize this client.</p>
<form method="post" action="/login">
<input type="hidden" name="pending" value="{pending}">
<input type="password" name="password" autofocus
  style="width:100%;padding:8px;margin-bottom:12px;box-sizing:border-box;"
  placeholder="App password">
<button type="submit" style="width:100%;padding:8px;">Authorize</button>
{error}
</form>
</body></html>"""


def _build_mcp() -> FastMCP:
    public_url = os.environ.get("MCP_PUBLIC_URL")
    if not public_url:
        return FastMCP("garmin-mcp")

    from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions

    from garmin_mcp.oauth_provider import SingleUserOAuthProvider

    if not os.environ.get("MCP_APP_PASSWORD"):
        raise RuntimeError("MCP_PUBLIC_URL is set but MCP_APP_PASSWORD is not - refusing to start an open server.")

    provider = SingleUserOAuthProvider()
    auth_settings = AuthSettings(
        issuer_url=public_url,
        resource_server_url=public_url,
        client_registration_options=ClientRegistrationOptions(
            enabled=True, valid_scopes=["garmin"], default_scopes=["garmin"]
        ),
        revocation_options=RevocationOptions(enabled=True),
    )
    server = FastMCP(
        "garmin-mcp",
        auth_server_provider=provider,
        auth=auth_settings,
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
    )
    _register_auth_routes(server, provider)
    return server


def _register_auth_routes(server: FastMCP, provider: "SingleUserOAuthProvider") -> None:
    @server.custom_route("/health", methods=["GET"])
    async def health(_request: Request) -> Response:
        return JSONResponse({"status": "ok"})

    @server.custom_route("/login", methods=["GET"])
    async def login_form(request: Request) -> Response:
        pending = request.query_params.get("pending", "")
        return HTMLResponse(LOGIN_PAGE.format(pending=pending, error=""))

    @server.custom_route("/login", methods=["POST"])
    async def login_submit(request: Request) -> Response:
        form = await request.form()
        pending = str(form.get("pending", ""))
        password = str(form.get("password", ""))
        redirect_url = provider.complete_login(pending, password)
        if redirect_url is None:
            return HTMLResponse(
                LOGIN_PAGE.format(pending=pending, error='<p style="color:red">Incorrect password or expired link.</p>'),
                status_code=401,
            )
        return RedirectResponse(redirect_url, status_code=303)


mcp = _build_mcp()


def _today() -> str:
    return dt.date.today().isoformat()


def _call(fn, *args, **kwargs) -> Any:
    try:
        client = get_client()
        return getattr(client, fn)(*args, **kwargs)
    except GarminAuthError as exc:
        return {"error": str(exc)}


@mcp.tool()
def get_user_profile() -> Any:
    """Get the authenticated Garmin Connect user's profile (name, id, unit preferences)."""
    return _call("get_user_profile")


@mcp.tool()
def get_activities(limit: int = 10, start: int = 0) -> Any:
    """List recent Garmin activities (runs, rides, workouts, etc).

    Args:
        limit: max number of activities to return.
        start: offset for pagination.
    """
    return _call("get_activities", start, limit)


@mcp.tool()
def get_activity_details(activity_id: str) -> Any:
    """Get full details for a single activity by its Garmin activity id
    (as returned by get_activities)."""
    return _call("get_activity", activity_id)


@mcp.tool()
def get_daily_summary(date: str | None = None) -> Any:
    """Get the daily summary for a given date: steps, calories, distance, floors, intensity minutes.

    Args:
        date: ISO date (YYYY-MM-DD). Defaults to today.
    """
    return _call("get_user_summary", date or _today())


@mcp.tool()
def get_steps(date: str | None = None) -> Any:
    """Get step count time series for a given date (YYYY-MM-DD, defaults to today)."""
    return _call("get_steps_data", date or _today())


@mcp.tool()
def get_sleep(date: str | None = None) -> Any:
    """Get sleep data (stages, duration, sleep score) for the night ending on the given date
    (YYYY-MM-DD, defaults to today)."""
    return _call("get_sleep_data", date or _today())


@mcp.tool()
def get_heart_rate(date: str | None = None) -> Any:
    """Get heart rate data (resting HR and intraday values) for a given date
    (YYYY-MM-DD, defaults to today)."""
    return _call("get_heart_rates", date or _today())


@mcp.tool()
def get_stress(date: str | None = None) -> Any:
    """Get stress level data for a given date (YYYY-MM-DD, defaults to today)."""
    return _call("get_stress_data", date or _today())


@mcp.tool()
def get_body_battery(date: str | None = None) -> Any:
    """Get Body Battery energy levels for a given date (YYYY-MM-DD, defaults to today)."""
    return _call("get_body_battery", date or _today())


@mcp.tool()
def get_body_composition(start_date: str | None = None, end_date: str | None = None) -> Any:
    """Get body composition (weight, body fat %, muscle mass, BMI) over a date range.

    Args:
        start_date: ISO date, defaults to today.
        end_date: ISO date, defaults to start_date.
    """
    start = start_date or _today()
    end = end_date or start
    return _call("get_body_composition", start, end)


@mcp.tool()
def get_training_readiness(date: str | None = None) -> Any:
    """Get Garmin Training Readiness score and contributing factors for a given date
    (YYYY-MM-DD, defaults to today)."""
    return _call("get_training_readiness", date or _today())


@mcp.tool()
def get_race_predictions() -> Any:
    """Get Garmin's predicted race times (5K, 10K, half marathon, marathon)."""
    return _call("get_race_predictions")


def main() -> None:
    transport = "streamable-http" if os.environ.get("MCP_PUBLIC_URL") else "stdio"
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
