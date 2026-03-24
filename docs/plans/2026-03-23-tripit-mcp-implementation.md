# TripIt MCP Server Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an MCP server exposing TripIt travel data via the undocumented v2 API with OAuth2 ROPC (spoofed iOS client).

**Architecture:** Three-layer design — auth (`auth.py`) manages OAuth2 tokens, client (`client.py`) wraps the TripIt v2 HTTP API, server (`server.py`) exposes FastMCP v2 tools. All HTTP uses async httpx with iPhone user-agent spoofing.

**Tech Stack:** Python 3.10+, FastMCP v2, httpx (async), uvicorn, pytest + pytest-asyncio

**Linear tickets:** DIMM-37 (smoke test), DIMM-38 (scaffolding + auth), DIMM-39 (list_trips), DIMM-40 (get_trip)

---

## Task 1: Smoke Test Script (DIMM-37)

**Files:**
- Create: `scripts/smoke_test.py`

**Step 1: Write the smoke test script**

This script tests the v2 API endpoints with real credentials. It requires env vars to be set.

```python
#!/usr/bin/env python3
"""Smoke test: verify TripIt v2 API works with OAuth2 ROPC + spoofed iOS client."""

import os
import sys
import json
import httpx

TRIPIT_BASE_URL = "https://api.tripit.com"

HEADERS = {
    "user-agent": "Tripit/18.1.0.2310191134 iPhone/17.0.2",
    "accept-language": "en-GB,en;q=0.9",
    "X-TRIPIT-APP-INFO": "iOS/18.1.0",
    "accept": "*/*",
}


def get_token() -> str:
    """Authenticate via OAuth2 ROPC and return access token."""
    r = httpx.post(
        f"{TRIPIT_BASE_URL}/oauth2/token",
        headers=HEADERS,
        data={
            "client_id": os.environ["TRIPIT_CLIENT_ID"],
            "client_secret": os.environ["TRIPIT_CLIENT_SECRET"],
            "scope": "openid offline_access email",
            "grant_type": "password",
            "username": os.environ["TRIPIT_USERNAME"],
            "password": os.environ["TRIPIT_PASSWORD"],
        },
    )
    print(f"[AUTH] Status: {r.status_code}")
    if r.status_code != 200:
        print(f"[AUTH] FAILED: {r.text}")
        sys.exit(1)
    token_data = r.json()
    print(f"[AUTH] Token type: {token_data['token_type']}, expires_in: {token_data['expires_in']}")
    return f"{token_data['token_type']} {token_data['access_token']}"


def test_list_trips(auth: str) -> str | None:
    """Test /v2/list/trip — known working endpoint. Returns first trip uuid."""
    url = f"{TRIPIT_BASE_URL}/v2/list/trip"
    params = {"format": "json", "page_size": "2", "past": "true", "include_objects": "false"}
    r = httpx.get(url, headers={**HEADERS, "authorization": auth}, params=params)
    print(f"\n[LIST /v2] Status: {r.status_code}")
    if r.status_code != 200:
        print(f"[LIST /v2] FAILED: {r.text}")
        return None
    data = r.json()
    trips = data.get("Trip", [])
    if isinstance(trips, dict):
        trips = [trips]
    print(f"[LIST /v2] Found {len(trips)} trip(s), max_page={data.get('max_page')}")
    if trips:
        t = trips[0]
        print(f"[LIST /v2] First trip: uuid={t.get('uuid')}, name={t.get('display_name')}")
        return t.get("uuid")
    return None


def test_get_trip(auth: str, trip_uuid: str):
    """Test /v2/get/trip — unconfirmed endpoint. Try multiple URL patterns."""
    patterns = [
        f"/v2/get/trip/uuid/{trip_uuid}",
        f"/v2/get/trip?format=json&uuid={trip_uuid}",
        f"/v2/get/trip?format=json&id={trip_uuid}",
        f"/v1/get/trip?format=json&id={trip_uuid}",
    ]
    for pattern in patterns:
        url = f"{TRIPIT_BASE_URL}{pattern}"
        if "?" in pattern:
            r = httpx.get(url, headers={**HEADERS, "authorization": auth})
        else:
            r = httpx.get(url, headers={**HEADERS, "authorization": auth}, params={"format": "json", "include_objects": "true"})
        print(f"\n[GET] {pattern} -> Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if "Trip" in data:
                trip = data["Trip"]
                name = trip.get("display_name") if isinstance(trip, dict) else trip[0].get("display_name")
                print(f"[GET] SUCCESS! Trip: {name}")
                print(f"[GET] Response keys: {list(data.keys())}")
                return pattern
            else:
                print(f"[GET] 200 but no Trip key. Keys: {list(data.keys())}")
        else:
            print(f"[GET] Response: {r.text[:200]}")
    return None


def test_without_cookies(auth: str):
    """Test if requests work without Akamai cookies."""
    headers_no_cookie = {k: v for k, v in HEADERS.items() if k != "Cookie"}
    r = httpx.get(
        f"{TRIPIT_BASE_URL}/v2/list/trip",
        headers={**headers_no_cookie, "authorization": auth},
        params={"format": "json", "page_size": "1", "past": "true"},
    )
    print(f"\n[NO-COOKIE] Status: {r.status_code}")
    if r.status_code == 200:
        print("[NO-COOKIE] Works WITHOUT Akamai cookies!")
    else:
        print(f"[NO-COOKIE] Failed: {r.text[:200]}")


def main():
    for var in ["TRIPIT_USERNAME", "TRIPIT_PASSWORD", "TRIPIT_CLIENT_ID", "TRIPIT_CLIENT_SECRET"]:
        if not os.environ.get(var):
            print(f"Missing env var: {var}")
            sys.exit(1)

    auth = get_token()
    trip_uuid = test_list_trips(auth)

    if trip_uuid:
        working_pattern = test_get_trip(auth, trip_uuid)
        if working_pattern:
            print(f"\n=== RESULT: get_trip works via: {working_pattern} ===")
        else:
            print("\n=== RESULT: get_trip FAILED on all patterns ===")
    else:
        print("\n=== RESULT: list_trips returned no trips ===")

    test_without_cookies(auth)


if __name__ == "__main__":
    main()
```

**Step 2: Run the smoke test**

Requires real credentials:
```bash
source .env  # or export TRIPIT_USERNAME=... etc.
python scripts/smoke_test.py
```

Expected output: confirms which `/v2/get/trip` pattern works and whether Akamai cookies are required.

**Step 3: Document findings**

Update DIMM-37 with results. Key findings to record:
- Which get_trip URL pattern works
- Whether cookies are required
- Any data contract differences (uuid vs id)

**Step 4: Commit**

```bash
git add scripts/smoke_test.py
git commit -m "feat: add v2 API smoke test script (DIMM-37)"
```

---

## Task 2: Project Scaffolding (DIMM-38, part 1)

**Files:**
- Create: `pyproject.toml`
- Create: `setup.py`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `tripit_mcp/__init__.py`
- Create: `tripit_mcp/__main__.py`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "tripit-mcp"
version = "0.1.0"
description = "MCP server for TripIt API v2"
requires-python = ">=3.10"

dependencies = [
    "fastmcp>=2.3.3",
    "httpx>=0.28.0",
    "uvicorn>=0.23.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.23.0",
    "black>=22.1.0",
    "ruff>=0.0.138",
]

[build-system]
requires = ["setuptools>=61.0.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

**Step 2: Create setup.py**

```python
from setuptools import setup, find_packages

setup(
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "tripit-mcp=tripit_mcp.__main__:main",
        ],
    },
)
```

**Step 3: Create .env.example**

```
TRIPIT_USERNAME=your_email@example.com
TRIPIT_PASSWORD=your_password
TRIPIT_CLIENT_ID=your_client_id
TRIPIT_CLIENT_SECRET=your_client_secret
```

**Step 4: Create .gitignore**

```
__pycache__/
*.pyc
*.pyo
.pytest_cache/
*.egg-info/
dist/
build/
.env
.venv/
venv/
.idea/
.vscode/
data/
*.shelve
```

**Step 5: Create tripit_mcp/__init__.py**

```python
"""TripIt MCP server — exposes TripIt travel data via Model Context Protocol."""

__version__ = "0.1.0"
```

**Step 6: Create tripit_mcp/__main__.py**

```python
#!/usr/bin/env python3
"""Entry point for the TripIt MCP server."""

import argparse
import os
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="TripIt MCP Server")
    parser.add_argument(
        "--mode",
        choices=["stdio", "http"],
        default="stdio",
        help="Server mode (default: stdio)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port (default: 8000)")
    return parser.parse_args()


def main():
    args = parse_args()

    required = ["TRIPIT_USERNAME", "TRIPIT_PASSWORD", "TRIPIT_CLIENT_ID", "TRIPIT_CLIENT_SECRET"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        sys.stderr.write(f"Missing required env vars: {', '.join(missing)}\n")
        sys.exit(1)

    from tripit_mcp.server import start_server

    sys.stderr.write(f"Starting TripIt MCP server in {args.mode} mode\n")
    start_server(mode=args.mode, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
```

**Step 7: Commit**

```bash
git add pyproject.toml setup.py .env.example .gitignore tripit_mcp/__init__.py tripit_mcp/__main__.py
git commit -m "feat: project scaffolding (DIMM-38)"
```

---

## Task 3: Auth Client (DIMM-38, part 2)

**Files:**
- Create: `tripit_mcp/auth.py`
- Create: `tests/__init__.py`
- Create: `tests/test_auth.py`

**Step 1: Write auth tests**

```python
"""Tests for TripIt OAuth2 ROPC auth client."""

import time
import httpx
import pytest
from unittest.mock import AsyncMock, patch

from tripit_mcp.auth import TripItAuth


@pytest.fixture
def auth():
    return TripItAuth(
        username="test@example.com",
        password="testpass",
        client_id="test-client-id",
        client_secret="test-client-secret",
    )


def make_token_response(expires_in=3600):
    return httpx.Response(
        200,
        json={
            "access_token": "test-access-token",
            "token_type": "Bearer",
            "expires_in": expires_in,
        },
    )


class TestTripItAuth:
    async def test_get_token_fetches_new_token(self, auth):
        with patch.object(auth._client, "post", new_callable=AsyncMock, return_value=make_token_response()):
            token = await auth.get_token()
            assert token == "Bearer test-access-token"

    async def test_get_token_caches_token(self, auth):
        mock_post = AsyncMock(return_value=make_token_response())
        with patch.object(auth._client, "post", mock_post):
            await auth.get_token()
            await auth.get_token()
            assert mock_post.call_count == 1

    async def test_get_token_refreshes_expired_token(self, auth):
        mock_post = AsyncMock(return_value=make_token_response(expires_in=0))
        with patch.object(auth._client, "post", mock_post):
            await auth.get_token()
            # Force expiry
            auth._token_expiry = time.time() - 1
            await auth.get_token()
            assert mock_post.call_count == 2

    async def test_get_token_raises_on_auth_failure(self, auth):
        error_response = httpx.Response(401, json={"error": "invalid_grant"})
        with patch.object(auth._client, "post", new_callable=AsyncMock, return_value=error_response):
            with pytest.raises(RuntimeError, match="OAuth2 token request failed"):
                await auth.get_token()

    async def test_headers_include_iphone_user_agent(self, auth):
        assert "iPhone" in auth.base_headers["user-agent"]
```

**Step 2: Run tests to verify they fail**

```bash
uv pip install -e ".[dev]" && pytest tests/test_auth.py -v
```

Expected: FAIL — `tripit_mcp.auth` module not found.

**Step 3: Write auth.py**

```python
"""OAuth2 ROPC auth client for TripIt v2 API (spoofed iOS client)."""

import time
import httpx

TRIPIT_BASE_URL = "https://api.tripit.com"

BASE_HEADERS = {
    "user-agent": "Tripit/18.1.0.2310191134 iPhone/17.0.2",
    "accept-language": "en-GB,en;q=0.9",
    "X-TRIPIT-APP-INFO": "iOS/18.1.0",
    "accept": "*/*",
}


class TripItAuth:
    """Manages OAuth2 ROPC tokens with in-memory caching."""

    def __init__(self, username: str, password: str, client_id: str, client_secret: str):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_headers = dict(BASE_HEADERS)
        self._client = httpx.AsyncClient(timeout=30.0)
        self._access_token: str | None = None
        self._token_type: str = "Bearer"
        self._token_expiry: float = 0

    async def get_token(self) -> str:
        """Return a valid Bearer token, refreshing if expired."""
        if self._access_token and time.time() < self._token_expiry:
            return f"{self._token_type} {self._access_token}"

        response = await self._client.post(
            f"{TRIPIT_BASE_URL}/oauth2/token",
            headers=self.base_headers,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "openid offline_access email",
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
            },
        )

        if response.status_code != 200:
            raise RuntimeError(f"OAuth2 token request failed: {response.status_code} {response.text}")

        data = response.json()
        self._access_token = data["access_token"]
        self._token_type = data.get("token_type", "Bearer")
        # Use expires_in / 10 as safety margin (matches tripit-export approach)
        self._token_expiry = time.time() + float(data["expires_in"]) / 10

        return f"{self._token_type} {self._access_token}"

    async def close(self):
        await self._client.aclose()
```

**Step 4: Run tests**

```bash
pytest tests/test_auth.py -v
```

Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add tripit_mcp/auth.py tests/__init__.py tests/test_auth.py
git commit -m "feat: OAuth2 ROPC auth client with caching (DIMM-38)"
```

---

## Task 4: TripIt API Client + list_trips (DIMM-39)

**Files:**
- Create: `tripit_mcp/client.py`
- Create: `tests/test_client.py`

**Step 1: Write client tests**

```python
"""Tests for TripIt v2 API client."""

import httpx
import pytest
from unittest.mock import AsyncMock, patch

from tripit_mcp.client import TripItClient

# Matches real v2 API response structure
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


@pytest.fixture
def client():
    return TripItClient(
        username="test@example.com",
        password="testpass",
        client_id="test-id",
        client_secret="test-secret",
    )


def mock_get(response_json, status=200):
    return AsyncMock(return_value=httpx.Response(status, json=response_json))


class TestListTrips:
    async def test_returns_trips_with_pagination(self, client):
        with patch.object(client._auth, "get_token", new_callable=AsyncMock, return_value="Bearer tok"):
            with patch.object(client._http, "get", mock_get(MOCK_LIST_RESPONSE)):
                result = await client.list_trips(past=True)
                assert len(result["trips"]) == 1
                assert result["trips"][0]["uuid"] == "abc-123"
                assert result["pagination"]["max_page"] == 3

    async def test_single_trip_returned_as_dict(self, client):
        with patch.object(client._auth, "get_token", new_callable=AsyncMock, return_value="Bearer tok"):
            with patch.object(client._http, "get", mock_get(MOCK_LIST_SINGLE_TRIP)):
                result = await client.list_trips()
                assert len(result["trips"]) == 1
                assert result["trips"][0]["uuid"] == "single-trip"

    async def test_empty_trips(self, client):
        with patch.object(client._auth, "get_token", new_callable=AsyncMock, return_value="Bearer tok"):
            with patch.object(client._http, "get", mock_get(MOCK_LIST_EMPTY)):
                result = await client.list_trips()
                assert result["trips"] == []

    async def test_passes_pagination_params(self, client):
        mock = mock_get(MOCK_LIST_RESPONSE)
        with patch.object(client._auth, "get_token", new_callable=AsyncMock, return_value="Bearer tok"):
            with patch.object(client._http, "get", mock):
                await client.list_trips(past=True, page_num=2, page_size=10)
                call_kwargs = mock.call_args
                params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
                assert params["page_num"] == "2"
                assert params["page_size"] == "10"
                assert params["past"] == "true"

    async def test_http_error_raises(self, client):
        error_resp = AsyncMock(return_value=httpx.Response(401, json={"error": "unauthorized"}))
        with patch.object(client._auth, "get_token", new_callable=AsyncMock, return_value="Bearer tok"):
            with patch.object(client._http, "get", error_resp):
                with pytest.raises(RuntimeError, match="TripIt API error"):
                    await client.list_trips()
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_client.py -v
```

Expected: FAIL — `tripit_mcp.client` not found.

**Step 3: Write client.py**

```python
"""TripIt v2 API client with async httpx."""

from typing import Any, Optional

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
        page_num: Optional[int] = None,
        page_size: Optional[int] = None,
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
        """Get trip details. trip_id is the trip uuid."""
        params: dict[str, str] = {"format": "json"}
        if include_objects:
            params["include_objects"] = "true"

        # NOTE: The exact URL pattern for v2 get/trip must be confirmed by smoke test (DIMM-37).
        # Update this endpoint based on findings.
        data = await self._request("GET", f"get/trip/uuid/{trip_id}", params=params)

        if "Trip" not in data:
            raise RuntimeError(f"Trip {trip_id} not found")

        return data["Trip"] if isinstance(data["Trip"], dict) else data["Trip"][0]

    async def close(self):
        await self._auth.close()
        await self._http.aclose()
```

**Step 4: Run tests**

```bash
pytest tests/test_client.py -v
```

Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add tripit_mcp/client.py tests/test_client.py
git commit -m "feat: TripIt v2 API client with list_trips (DIMM-39)"
```

---

## Task 5: FastMCP Server + list_trips Tool (DIMM-39, part 2)

**Files:**
- Create: `tripit_mcp/server.py`
- Create: `tests/test_server.py`

**Step 1: Write MCP tool tests**

```python
"""Tests for MCP server tools using FastMCP in-memory client."""

import pytest
from unittest.mock import AsyncMock, patch

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


class TestListTripsTool:
    async def test_list_trips_returns_formatted_response(self):
        with patch("tripit_mcp.server.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.list_trips = AsyncMock(return_value=MOCK_CLIENT_LIST_RESULT)
            mock_get_client.return_value = mock_client
            async with Client(mcp) as c:
                result = await c.call_tool("list_trips", {"past": False})
                data = result.data
                assert len(data["trips"]) == 1
                assert data["trips"][0]["uuid"] == "abc-123"
                assert data["pagination"]["max_page"] == 1

    async def test_list_trips_passes_params(self):
        with patch("tripit_mcp.server.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.list_trips = AsyncMock(return_value=MOCK_CLIENT_LIST_RESULT)
            mock_get_client.return_value = mock_client
            async with Client(mcp) as c:
                await c.call_tool("list_trips", {"past": True, "page_num": 2, "page_size": 10})
                mock_client.list_trips.assert_called_once_with(past=True, page_num=2, page_size=10)
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_server.py -v
```

Expected: FAIL — `tripit_mcp.server` not found.

**Step 3: Write server.py**

```python
"""FastMCP v2 server exposing TripIt tools."""

import os
import sys
import logging
from typing import Any, Optional

from fastmcp import FastMCP

from tripit_mcp.client import TripItClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s", stream=sys.stderr)

mcp = FastMCP(
    title="TripIt MCP Server",
    description="Access your TripIt travel data via MCP",
)

_client: TripItClient | None = None


def get_client() -> TripItClient:
    global _client
    if _client is None:
        _client = TripItClient(
            username=os.environ["TRIPIT_USERNAME"],
            password=os.environ["TRIPIT_PASSWORD"],
            client_id=os.environ["TRIPIT_CLIENT_ID"],
            client_secret=os.environ["TRIPIT_CLIENT_SECRET"],
        )
    return _client


@mcp.tool(description="List trips with pagination. Returns past or upcoming trips.")
async def list_trips(
    past: bool = False,
    page_num: Optional[int] = None,
    page_size: Optional[int] = None,
) -> dict[str, Any]:
    """List trips with pagination support.

    Args:
        past: If True, returns past trips. If False, returns upcoming trips.
        page_num: Page number (starts at 1).
        page_size: Trips per page.
    """
    try:
        client = get_client()
        return await client.list_trips(past=past, page_num=page_num, page_size=page_size)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool(description="Get detailed information about a specific trip, including flights, lodging, etc.")
async def get_trip(trip_id: str) -> dict[str, Any]:
    """Get details for a specific trip.

    Args:
        trip_id: The trip UUID (from list_trips results).
    """
    try:
        client = get_client()
        trip = await client.get_trip(trip_id)
        return {"trip": trip}
    except Exception as e:
        return {"error": str(e)}


def start_server(mode: str = "stdio", host: str = "0.0.0.0", port: int = 8000):
    if mode == "stdio":
        import asyncio
        sys.stderr.write("Starting stdio mode\n")
        asyncio.run(mcp.run_stdio_async())
    else:
        import uvicorn
        uvicorn.run(mcp, host=host, port=port, log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                }
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": "INFO"},
            },
        })
```

**Step 4: Run tests**

```bash
pytest tests/test_server.py -v
```

Expected: All 2 tests PASS.

**Step 5: Commit**

```bash
git add tripit_mcp/server.py tests/test_server.py
git commit -m "feat: FastMCP server with list_trips tool (DIMM-39)"
```

---

## Task 6: get_trip Tool Tests (DIMM-40)

**Files:**
- Modify: `tests/test_server.py`
- Modify: `tests/test_client.py`

**Step 1: Add get_trip client tests to tests/test_client.py**

Append to the file:

```python
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


class TestGetTrip:
    async def test_returns_trip_details(self, client):
        with patch.object(client._auth, "get_token", new_callable=AsyncMock, return_value="Bearer tok"):
            with patch.object(client._http, "request", mock_get(MOCK_GET_TRIP_RESPONSE)):
                result = await client.get_trip("abc-123")
                assert result["uuid"] == "abc-123"

    async def test_not_found_raises(self, client):
        with patch.object(client._auth, "get_token", new_callable=AsyncMock, return_value="Bearer tok"):
            with patch.object(client._http, "request", mock_get(MOCK_GET_TRIP_NOT_FOUND)):
                with pytest.raises(RuntimeError, match="not found"):
                    await client.get_trip("nonexistent")
```

**Step 2: Add get_trip MCP tool tests to tests/test_server.py**

Append to the file:

```python
MOCK_CLIENT_GET_RESULT = {
    "uuid": "abc-123",
    "display_name": "Prague Trip",
    "start_date": "2025-06-01",
    "end_date": "2025-06-05",
}


class TestGetTripTool:
    async def test_get_trip_returns_trip(self):
        with patch("tripit_mcp.server.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_trip = AsyncMock(return_value=MOCK_CLIENT_GET_RESULT)
            mock_get_client.return_value = mock_client
            async with Client(mcp) as c:
                result = await c.call_tool("get_trip", {"trip_id": "abc-123"})
                data = result.data
                assert data["trip"]["uuid"] == "abc-123"

    async def test_get_trip_error_handling(self):
        with patch("tripit_mcp.server.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_trip = AsyncMock(side_effect=RuntimeError("Trip xyz not found"))
            mock_get_client.return_value = mock_client
            async with Client(mcp) as c:
                result = await c.call_tool("get_trip", {"trip_id": "xyz"})
                assert "error" in result.data
```

**Step 3: Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests PASS (auth: 5, client: 7, server: 4).

**Step 4: Commit**

```bash
git add tests/test_client.py tests/test_server.py
git commit -m "feat: get_trip tool with tests (DIMM-40)"
```

---

## Task 7: Docker + Final Wiring (DIMM-38 completion)

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

**Step 1: Create Dockerfile**

```dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml setup.py /app/
RUN uv venv --path /app/.venv --python python3.10 && \
    . /app/.venv/bin/activate && \
    uv pip install -e .

COPY . /app/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["python", "-m", "tripit_mcp"]
```

**Step 2: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  tripit-mcp:
    build: .
    ports:
      - "8000:8000"
    environment:
      - TRIPIT_USERNAME=${TRIPIT_USERNAME}
      - TRIPIT_PASSWORD=${TRIPIT_PASSWORD}
      - TRIPIT_CLIENT_ID=${TRIPIT_CLIENT_ID}
      - TRIPIT_CLIENT_SECRET=${TRIPIT_CLIENT_SECRET}
    restart: unless-stopped
    command: python -m tripit_mcp --mode http --host 0.0.0.0 --port 8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Step 3: Run all tests one final time**

```bash
pytest tests/ -v
```

Expected: All 16 tests PASS.

**Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: Docker support (DIMM-38)"
```

---

## Summary

| Task | Ticket | Files | Tests |
|------|--------|-------|-------|
| 1. Smoke test | DIMM-37 | `scripts/smoke_test.py` | Manual (real API) |
| 2. Scaffolding | DIMM-38 | pyproject.toml, setup.py, .env.example, .gitignore, __init__.py, __main__.py | — |
| 3. Auth client | DIMM-38 | `tripit_mcp/auth.py` | 5 tests |
| 4. API client + list_trips | DIMM-39 | `tripit_mcp/client.py` | 5 tests |
| 5. MCP server + list_trips tool | DIMM-39 | `tripit_mcp/server.py` | 2 tests |
| 6. get_trip tool | DIMM-40 | modify test files | 4 tests |
| 7. Docker | DIMM-38 | Dockerfile, docker-compose.yml | — |

**Total: 16 automated tests + 1 manual smoke test**

## Post-Plan Notes

- **DIMM-37 must run first** — the `get_trip` endpoint URL pattern in `client.py` is a guess (`/v2/get/trip/uuid/{uuid}`). Update based on smoke test findings.
- After smoke test, update CLAUDE.md with confirmed v2 API details.
- MCP Inspector (`npx @modelcontextprotocol/inspector`) is useful for manual validation after all code is in place.
