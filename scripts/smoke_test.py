#!/usr/bin/env python3
"""
TripIt v2 API Smoke Test

Tests OAuth2 ROPC authentication and various endpoint patterns to discover
which URL patterns work for get_trip on the undocumented v2 API.

Env vars required: TRIPIT_USERNAME, TRIPIT_PASSWORD, TRIPIT_CLIENT_ID, TRIPIT_CLIENT_SECRET
"""

import os
import sys
from datetime import datetime

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "https://api.tripit.com"

HEADERS = {
    "user-agent": "Tripit/18.1.0.2310191134 iPhone/17.0.2",
    "accept-language": "en-GB,en;q=0.9",
    "X-TRIPIT-APP-INFO": "iOS/18.1.0",
    "accept": "*/*",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def env_or_die(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        print(f"FATAL: environment variable {name} is not set")
        sys.exit(1)
    return val


def print_header(title: str) -> None:
    print(f"\n{'=' * 72}")
    print(f"  {title}")
    print(f"{'=' * 72}")


def print_result(label: str, status: int, body: str, success: bool) -> None:
    icon = "PASS" if success else "FAIL"
    print(f"\n  [{icon}] {label}")
    print(f"  Status: {status}")
    # Print a truncated body for readability
    if len(body) > 1500:
        print(f"  Body (first 1500 chars): {body[:1500]}...")
    else:
        print(f"  Body: {body}")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def authenticate(client: httpx.Client) -> str:
    """Authenticate via OAuth2 ROPC and return a Bearer token."""
    print_header("Step 1: OAuth2 ROPC Authentication")

    username = env_or_die("TRIPIT_USERNAME")
    password = env_or_die("TRIPIT_PASSWORD")
    client_id = env_or_die("TRIPIT_CLIENT_ID")
    client_secret = env_or_die("TRIPIT_CLIENT_SECRET")

    print(f"  Username:  {username}")
    print(f"  Client ID: {client_id}")

    resp = client.post(
        f"{BASE_URL}/oauth2/token",
        headers=HEADERS,
        data={
            "grant_type": "password",
            "username": username,
            "password": password,
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "openid offline_access email",
        },
    )

    print(f"  Status: {resp.status_code}")

    if resp.status_code != 200:
        print("  FATAL: authentication failed")
        print(f"  Body: {resp.text}")
        sys.exit(1)

    data = resp.json()
    token = data["access_token"]
    token_type = data.get("token_type", "Bearer")
    expires_in = data.get("expires_in", "?")

    print(f"  Token type: {token_type}")
    print(f"  Expires in: {expires_in}s")
    print(f"  Token (first 20): {token[:20]}...")
    print("  AUTH OK")

    return f"{token_type} {token}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_list_trips(client: httpx.Client, authorization: str) -> dict | None:
    """Test the known-working v2 list/trip endpoint. Returns first trip or None."""
    print_header("Step 2: GET /v2/list/trip (baseline — should work)")

    url = f"{BASE_URL}/v2/list/trip"
    params = {
        "format": "json",
        "page_size": "2",
        "past": "true",
    }

    resp = client.get(url, headers={**HEADERS, "authorization": authorization}, params=params)
    body = resp.text
    success = resp.status_code == 200

    print_result("v2/list/trip (past=true, page_size=2)", resp.status_code, body, success)

    if not success:
        print("  WARNING: baseline list/trip failed — all subsequent tests may fail too")
        return None

    data = resp.json()

    # Extract a trip UUID for get_trip tests
    trips = data.get("Trip", [])
    if isinstance(trips, dict):
        trips = [trips]

    if not trips:
        print("  WARNING: No trips returned. Cannot test get_trip patterns.")
        return None

    trip = trips[0]
    uuid = trip.get("uuid", "")
    trip_id = trip.get("id", "")
    display_name = trip.get("display_name", "?")

    print(f"\n  First trip: {display_name}")
    print(f"  UUID: {uuid}")
    print(f"  ID:   {trip_id}")

    return {"uuid": uuid, "id": trip_id, "display_name": display_name}


def test_list_trips_no_cookies(client: httpx.Client, authorization: str) -> None:
    """Test list/trip WITHOUT Akamai cookies to see if they're required."""
    print_header("Step 3: GET /v2/list/trip WITHOUT Akamai cookies")

    url = f"{BASE_URL}/v2/list/trip"
    params = {"format": "json", "page_size": "1", "past": "true"}

    # Use headers WITHOUT any Cookie header
    headers_no_cookies = {k: v for k, v in HEADERS.items() if k.lower() != "cookie"}
    headers_no_cookies["authorization"] = authorization

    resp = client.get(url, headers=headers_no_cookies, params=params)
    success = resp.status_code == 200

    print_result("v2/list/trip WITHOUT cookies", resp.status_code, resp.text, success)

    if success:
        print("  CONCLUSION: Akamai cookies are NOT required")
    else:
        print("  CONCLUSION: Akamai cookies may be required")


def test_get_trip_patterns(client: httpx.Client, authorization: str, trip: dict) -> None:
    """Try multiple URL patterns for get_trip to find which one works."""
    print_header("Step 4: GET /v2/get/trip — testing URL patterns")

    uuid = trip["uuid"]
    trip_id = trip["id"]

    patterns = [
        {
            "label": "/v2/get/trip/uuid/{uuid}?format=json&include_objects=true",
            "url": f"{BASE_URL}/v2/get/trip/uuid/{uuid}",
            "params": {"format": "json", "include_objects": "true"},
        },
        {
            "label": "/v2/get/trip?format=json&uuid={uuid}",
            "url": f"{BASE_URL}/v2/get/trip",
            "params": {"format": "json", "uuid": uuid},
        },
        {
            "label": "/v2/get/trip?format=json&id={uuid}",
            "url": f"{BASE_URL}/v2/get/trip",
            "params": {"format": "json", "id": uuid},
        },
        {
            "label": "/v2/get/trip?format=json&id={numeric_id}",
            "url": f"{BASE_URL}/v2/get/trip",
            "params": {"format": "json", "id": trip_id},
        },
        {
            "label": "/v2/get/trip/id/{numeric_id}?format=json&include_objects=true",
            "url": f"{BASE_URL}/v2/get/trip/id/{trip_id}",
            "params": {"format": "json", "include_objects": "true"},
        },
        {
            "label": "/v1/get/trip?format=json&id={numeric_id} (v1 fallback with Bearer)",
            "url": f"{BASE_URL}/v1/get/trip",
            "params": {"format": "json", "id": trip_id},
        },
        {
            "label": "/v1/get/trip/id/{numeric_id}?format=json (v1 path-style with Bearer)",
            "url": f"{BASE_URL}/v1/get/trip/id/{trip_id}",
            "params": {"format": "json"},
        },
    ]

    results = []

    for i, pat in enumerate(patterns, 1):
        print(f"\n  --- Pattern {i}/{len(patterns)} ---")
        print(f"  {pat['label']}")
        print(f"  URL: {pat['url']}")
        print(f"  Params: {pat['params']}")

        try:
            resp = client.get(
                pat["url"],
                headers={**HEADERS, "authorization": authorization},
                params=pat["params"],
            )
            body = resp.text
            success = resp.status_code == 200

            # Check if it actually contains trip data
            has_trip_data = False
            if success:
                try:
                    data = resp.json()
                    has_trip_data = "Trip" in data or "trip" in data or "display_name" in str(data)[:500]
                except Exception:
                    pass

            print_result(pat["label"], resp.status_code, body, success and has_trip_data)

            results.append({
                "pattern": pat["label"],
                "status": resp.status_code,
                "success": success,
                "has_trip_data": has_trip_data,
            })

        except Exception as e:
            print(f"  [ERROR] {pat['label']}: {e}")
            results.append({
                "pattern": pat["label"],
                "status": -1,
                "success": False,
                "has_trip_data": False,
            })

    # Summary
    print_header("RESULTS SUMMARY")

    working = [r for r in results if r["success"] and r["has_trip_data"]]
    http_ok = [r for r in results if r["success"] and not r["has_trip_data"]]
    failed = [r for r in results if not r["success"]]

    if working:
        print("\n  WORKING (200 + trip data):")
        for r in working:
            print(f"    [PASS] {r['pattern']}  (status {r['status']})")
    else:
        print("\n  NO PATTERNS returned trip data successfully")

    if http_ok:
        print("\n  HTTP 200 but no trip data:")
        for r in http_ok:
            print(f"    [PARTIAL] {r['pattern']}  (status {r['status']})")

    if failed:
        print("\n  FAILED:")
        for r in failed:
            print(f"    [FAIL] {r['pattern']}  (status {r['status']})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 72)
    print("  TripIt v2 API Smoke Test")
    print(f"  {datetime.now().isoformat()}")
    print("=" * 72)

    client = httpx.Client(timeout=30.0)

    try:
        # Step 1: Auth
        authorization = authenticate(client)

        # Step 2: Baseline list/trip
        trip = test_list_trips(client, authorization)

        # Step 3: Test without cookies
        test_list_trips_no_cookies(client, authorization)

        # Step 4: Test get_trip patterns
        if trip:
            test_get_trip_patterns(client, authorization, trip)
        else:
            print("\n  SKIPPING get_trip tests — no trip data available from list_trips")

    finally:
        client.close()

    print(f"\n{'=' * 72}")
    print("  Smoke test complete")
    print(f"{'=' * 72}\n")


if __name__ == "__main__":
    main()
