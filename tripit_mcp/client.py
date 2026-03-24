"""TripIt v2 API client with async httpx."""

from typing import Any

import httpx

from tripit_mcp.auth import TripItAuth, BASE_HEADERS, TRIPIT_BASE_URL


class TripItClient:
    """Async client for TripIt v2 API."""

    def __init__(self, username: str, password: str, client_id: str, client_secret: str):
        self._auth = TripItAuth(username, password, client_id, client_secret)
        self._http = httpx.AsyncClient(timeout=30.0, headers=BASE_HEADERS)

    async def _request(self, method: str, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        token = await self._auth.get_token()
        headers = {"authorization": token}
        url = f"{TRIPIT_BASE_URL}/v2/{endpoint}"

        response = await self._http.request(method, url, params=params, headers=headers)

        if response.status_code != 200:
            raise RuntimeError(f"TripIt API error: {response.status_code} {response.text[:200]}")

        return response.json()

    async def list_trips(
        self,
        past: bool = False,
        page_num: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """List trips with pagination."""
        params: dict[str, str] = {
            "format": "json",
            "past": "true" if past else "false",
        }
        if page_num is not None:
            params["page_num"] = str(page_num)
        if page_size is not None:
            params["page_size"] = str(page_size)

        data = await self._request("GET", "list/trip", params=params)

        trips = data.get("Trip", [])
        if isinstance(trips, dict):
            trips = [trips]

        return {
            "trips": trips,
            "pagination": {
                "page_num": int(data.get("page_num", 1)),
                "page_size": int(data.get("page_size", 25)),
                "max_page": int(data.get("max_page", 1)),
            },
        }

    async def get_trip(self, trip_id: str, include_objects: bool = True) -> dict[str, Any]:
        """Get trip details by UUID."""
        params: dict[str, str] = {"format": "json"}
        if include_objects:
            params["include_objects"] = "true"

        data = await self._request("GET", f"get/trip/uuid/{trip_id}", params=params)

        if "Trip" not in data:
            raise RuntimeError(f"Trip {trip_id} not found")

        return data["Trip"] if isinstance(data["Trip"], dict) else data["Trip"][0]

    async def close(self):
        await self._auth.close()
        await self._http.aclose()
