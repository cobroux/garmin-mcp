"""MCP server exposing Garmin Connect data as tools."""

from __future__ import annotations

import datetime as dt
from typing import Any

from mcp.server.fastmcp import FastMCP

from garmin_mcp.garmin_client import GarminAuthError, get_client

mcp = FastMCP("garmin-mcp")


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
    mcp.run()


if __name__ == "__main__":
    main()
