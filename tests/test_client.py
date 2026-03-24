"""Tests for TripIt v2 API client."""

import httpx
import pytest
from unittest.mock import AsyncMock, patch


MOCK_LIST_RESPONSE = {
    "page_num": "1",
    "page_size": "25",
    "max_page": "3",
    "Trip": [
        {
            "uuid": "abc-123",
            "display_name": "Prague, Czech Republic",
            "start_date": "2025-06-01",
            "end_date": "2025-06-05",
            "primary_location": "Prague, Czech Republic",
            "is_private": "false",
            "PrimaryLocationAddress": {
                "city": "Prague",
                "country": "CZ",
                "latitude": "50.0755",
                "longitude": "14.4378",
            },
        },
    ],
}

MOCK_LIST_SINGLE_TRIP = {
    "page_num": "1",
    "page_size": "25",
    "max_page": "1",
    "Trip": {
        "uuid": "single-trip",
        "display_name": "Solo Trip",
        "start_date": "2025-01-01",
        "end_date": "2025-01-02",
        "primary_location": "Nowhere",
        "is_private": "false",
    },
}

MOCK_LIST_EMPTY = {
    "page_num": "1",
    "page_size": "25",
    "max_page": "1",
}

MOCK_GET_TRIP_RESPONSE = {
    "Trip": {
        "uuid": "abc-123",
        "display_name": "Prague, Czech Republic",
        "start_date": "2025-06-01",
        "end_date": "2025-06-05",
        "primary_location": "Prague, Czech Republic",
    },
    "AirObject": [{"display_name": "Flight to Prague"}],
}

MOCK_GET_TRIP_NOT_FOUND = {"timestamp": "123456"}


def mock_response(response_json, status=200):
    return AsyncMock(return_value=httpx.Response(status, json=response_json))


class TestListTrips:
    async def test_returns_trips_with_pagination(self, client):
        with patch.object(client._auth, "get_token", new_callable=AsyncMock, return_value="Bearer tok"):
            with patch.object(client._http, "request", mock_response(MOCK_LIST_RESPONSE)):
                result = await client.list_trips(past=True)
                assert len(result["trips"]) == 1
                assert result["trips"][0]["uuid"] == "abc-123"
                assert result["pagination"]["max_page"] == 3

    async def test_single_trip_returned_as_dict(self, client):
        with patch.object(client._auth, "get_token", new_callable=AsyncMock, return_value="Bearer tok"):
            with patch.object(client._http, "request", mock_response(MOCK_LIST_SINGLE_TRIP)):
                result = await client.list_trips()
                assert len(result["trips"]) == 1
                assert result["trips"][0]["uuid"] == "single-trip"

    async def test_empty_trips(self, client):
        with patch.object(client._auth, "get_token", new_callable=AsyncMock, return_value="Bearer tok"):
            with patch.object(client._http, "request", mock_response(MOCK_LIST_EMPTY)):
                result = await client.list_trips()
                assert result["trips"] == []

    async def test_passes_pagination_params(self, client):
        mock = mock_response(MOCK_LIST_RESPONSE)
        with patch.object(client._auth, "get_token", new_callable=AsyncMock, return_value="Bearer tok"):
            with patch.object(client._http, "request", mock):
                await client.list_trips(past=True, page_num=2, page_size=10)
                call_kwargs = mock.call_args
                params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
                assert params["page_num"] == "2"
                assert params["page_size"] == "10"
                assert params["past"] == "true"

    async def test_http_error_raises(self, client):
        with patch.object(client._auth, "get_token", new_callable=AsyncMock, return_value="Bearer tok"):
            with patch.object(client._http, "request", mock_response({"error": "unauthorized"}, status=401)):
                with pytest.raises(RuntimeError, match="TripIt API error"):
                    await client.list_trips()


class TestGetTrip:
    async def test_returns_trip_details(self, client):
        with patch.object(client._auth, "get_token", new_callable=AsyncMock, return_value="Bearer tok"):
            with patch.object(client._http, "request", mock_response(MOCK_GET_TRIP_RESPONSE)):
                result = await client.get_trip("abc-123")
                assert result["uuid"] == "abc-123"

    async def test_not_found_raises(self, client):
        with patch.object(client._auth, "get_token", new_callable=AsyncMock, return_value="Bearer tok"):
            with patch.object(client._http, "request", mock_response(MOCK_GET_TRIP_NOT_FOUND)):
                with pytest.raises(RuntimeError, match="not found"):
                    await client.get_trip("nonexistent")
