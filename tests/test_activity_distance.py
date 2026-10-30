from unittest.mock import MagicMock

from garmin_mcp.garmin_client import add_distance_km, build_activity_details


def test_distance_km_from_metres():
    client = MagicMock()
    client.get_activity.return_value = {"activityId": 1, "summaryDTO": {"distance": 10234.5, "averageSpeed": 3.1}}

    details = build_activity_details(client, "1")
    assert details["distance"] == 10234.5
    assert details["distance_km"] == 10.23
    assert details["averageSpeed"] == 3.1

    assert add_distance_km([{"distance": 5000.0}, {"distance": None}]) == [
        {"distance": 5000.0, "distance_km": 5.0},
        {"distance": None},
    ]
