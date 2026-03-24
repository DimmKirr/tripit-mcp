"""Tests for MCP server tools using FastMCP in-memory client."""

from unittest.mock import patch

from fastmcp import Client

from tripit_mcp.server import mcp


MOCK_CLIENT_LIST_RESULT = {
    "trips": [
        {
            "uuid": "abc-123",
            "display_name": "Prague Trip",
            "start_date": "2025-06-01",
            "end_date": "2025-06-05",
            "primary_location": "Prague, Czech Republic",
            "is_private": "false",
        }
    ],
    "pagination": {"page_num": 1, "page_size": 25, "max_page": 1},
}

MOCK_CLIENT_GET_RESULT = {
    "uuid": "abc-123",
    "display_name": "Prague Trip",
    "start_date": "2025-06-01",
    "end_date": "2025-06-05",
}


class TestListTripsTool:
    async def test_list_trips_returns_formatted_response(self, mock_tripit_client):
        mock_tripit_client.list_trips.return_value = MOCK_CLIENT_LIST_RESULT
        with patch("tripit_mcp.server.get_client", return_value=mock_tripit_client):
            async with Client(mcp) as c:
                result = await c.call_tool("list_trips", {"past": False})
                data = result.data
                assert len(data["trips"]) == 1
                assert data["trips"][0]["uuid"] == "abc-123"
                assert data["pagination"]["max_page"] == 1

    async def test_list_trips_passes_params(self, mock_tripit_client):
        mock_tripit_client.list_trips.return_value = MOCK_CLIENT_LIST_RESULT
        with patch("tripit_mcp.server.get_client", return_value=mock_tripit_client):
            async with Client(mcp) as c:
                await c.call_tool("list_trips", {"past": True, "page_num": 2, "page_size": 10})
                mock_tripit_client.list_trips.assert_called_once_with(past=True, page_num=2, page_size=10)


class TestGetTripTool:
    async def test_get_trip_returns_trip(self, mock_tripit_client):
        mock_tripit_client.get_trip.return_value = MOCK_CLIENT_GET_RESULT
        with patch("tripit_mcp.server.get_client", return_value=mock_tripit_client):
            async with Client(mcp) as c:
                result = await c.call_tool("get_trip", {"trip_id": "abc-123"})
                data = result.data
                assert data["trip"]["uuid"] == "abc-123"

    async def test_get_trip_error_handling(self, mock_tripit_client):
        mock_tripit_client.get_trip.side_effect = RuntimeError("Trip xyz not found")
        with patch("tripit_mcp.server.get_client", return_value=mock_tripit_client):
            async with Client(mcp) as c:
                result = await c.call_tool("get_trip", {"trip_id": "xyz"})
                assert "error" in result.data
