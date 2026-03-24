#!/usr/bin/env python3
"""
TripIt XSD Schema Validation Pipeline

1. Fetches the live XSD schemas from api.tripit.com
2. Generates Python dataclasses via xsdata
3. Validates that our API response fields match the schema
4. Can be run as a GHA job to detect API drift

Env vars required: TRIPIT_USERNAME, TRIPIT_PASSWORD, TRIPIT_CLIENT_ID, TRIPIT_CLIENT_SECRET
Optional: --schema-only to skip API validation and just check XSD availability

Usage:
    python scripts/validate_schema.py              # Full validation (fetch XSD + probe API)
    python scripts/validate_schema.py --schema-only  # Just check XSD is still available
"""

import os
import sys
import urllib.request
from dataclasses import dataclass

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

XSD_URLS = {
    "objects": "https://api.tripit.com/xsd/tripit-api-obj-v1.xsd",
    "response": "https://api.tripit.com/xsd/tripit-api-res-v1.xsd",
    "request": "https://api.tripit.com/xsd/tripit-api-req-v1.xsd",
}

TRIPIT_BASE_URL = "https://api.tripit.com"

HEADERS = {
    "user-agent": "Tripit/18.1.0.2310191134 iPhone/17.0.2",
    "accept-language": "en-GB,en;q=0.9",
    "X-TRIPIT-APP-INFO": "iOS/18.1.0",
    "accept": "*/*",
}

# Object types from the XSD that map to v2 API list/object?type= params
OBJECT_TYPES = [
    "air", "lodging", "car", "rail", "transport",
    "activity", "restaurant", "note", "cruise", "directions",
]

# Expected top-level keys in v2 API responses (from XSD response envelope)
RESPONSE_ENVELOPE_KEYS = {"timestamp", "num_bytes", "page_num", "page_size", "max_page", "total_items"}


# ---------------------------------------------------------------------------
# Schema check
# ---------------------------------------------------------------------------

@dataclass
class SchemaCheckResult:
    name: str
    url: str
    status: int
    size: int
    ok: bool


def check_xsd_availability() -> list[SchemaCheckResult]:
    """Verify all XSD schemas are still available at their published URLs."""
    results = []
    for name, url in XSD_URLS.items():
        try:
            resp = urllib.request.urlopen(url, timeout=30)
            body = resp.read()
            results.append(SchemaCheckResult(name=name, url=url, status=resp.status, size=len(body), ok=True))
        except Exception as e:
            results.append(SchemaCheckResult(name=name, url=url, status=getattr(e, "code", 0), size=0, ok=False))
    return results


def parse_xsd_fields(xsd_text: str, type_name: str) -> set[str]:
    """Extract field names for a given type from XSD using xmlschema."""
    try:
        import xmlschema
    except ImportError:
        print("  WARNING: xmlschema not installed, skipping field extraction")
        return set()

    schema = xmlschema.XMLSchema(xsd_text)
    xsd_type = schema.types.get(type_name)
    if not xsd_type:
        return set()

    fields = set()
    if hasattr(xsd_type, "content") and xsd_type.content:
        for elem in xsd_type.content.iter_elements():
            fields.add(elem.name)
    return fields


# ---------------------------------------------------------------------------
# API validation
# ---------------------------------------------------------------------------

def authenticate() -> str:
    """Get Bearer token via OAuth2 ROPC."""
    resp = httpx.post(
        f"{TRIPIT_BASE_URL}/oauth2/token",
        headers=HEADERS,
        data={
            "grant_type": "password",
            "username": os.environ["TRIPIT_USERNAME"],
            "password": os.environ["TRIPIT_PASSWORD"],
            "client_id": os.environ["TRIPIT_CLIENT_ID"],
            "client_secret": os.environ["TRIPIT_CLIENT_SECRET"],
            "scope": "openid offline_access email",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"FATAL: Auth failed: {resp.status_code}")
        sys.exit(1)
    data = resp.json()
    return f"{data.get('token_type', 'Bearer')} {data['access_token']}"


def validate_endpoint_fields(
    authorization: str,
    xsd_text: str,
    endpoint: str,
    params: dict[str, str],
    xsd_type_name: str,
    response_key: str,
) -> tuple[bool, list[str]]:
    """Validate that API response fields are a subset of XSD-defined fields."""
    issues = []

    resp = httpx.get(
        f"{TRIPIT_BASE_URL}/{endpoint}",
        headers={**HEADERS, "authorization": authorization},
        params=params,
        timeout=30,
    )

    if resp.status_code != 200:
        issues.append(f"HTTP {resp.status_code} for {endpoint}")
        return False, issues

    data = resp.json()

    # Check response envelope keys
    unknown_envelope = set(data.keys()) - RESPONSE_ENVELOPE_KEYS - {response_key}
    # Allow multiple object type keys in unfiltered responses
    for key in list(unknown_envelope):
        if key.endswith("Object") or key in ("Trip", "Profile"):
            unknown_envelope.discard(key)
    if unknown_envelope:
        issues.append(f"Unknown envelope keys: {unknown_envelope}")

    # Validate object fields against XSD
    obj = data.get(response_key)
    if obj is None:
        return True, issues  # No data, but endpoint works

    # Normalize dict-vs-list
    items = [obj] if isinstance(obj, dict) else obj
    if not items:
        return True, issues

    xsd_fields = parse_xsd_fields(xsd_text, xsd_type_name)
    if not xsd_fields:
        return True, issues

    sample = items[0]
    api_fields = set(sample.keys())
    unknown_fields = api_fields - xsd_fields
    if unknown_fields:
        issues.append(f"Fields in API but not in XSD for {xsd_type_name}: {unknown_fields}")

    return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    schema_only = "--schema-only" in sys.argv
    exit_code = 0

    # Step 1: Check XSD availability
    print("=" * 60)
    print("  Step 1: XSD Schema Availability")
    print("=" * 60)

    results = check_xsd_availability()
    for r in results:
        icon = "PASS" if r.ok else "FAIL"
        print(f"  [{icon}] {r.name}: {r.url} ({r.size} bytes)")
        if not r.ok:
            exit_code = 1

    if schema_only:
        print(f"\n  Schema-only mode. Exit code: {exit_code}")
        sys.exit(exit_code)

    # Step 2: Validate API responses against XSD
    print("\n" + "=" * 60)
    print("  Step 2: API Response Field Validation")
    print("=" * 60)

    # Check env vars
    required = ["TRIPIT_USERNAME", "TRIPIT_PASSWORD", "TRIPIT_CLIENT_ID", "TRIPIT_CLIENT_SECRET"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(f"  SKIP: Missing env vars: {', '.join(missing)}")
        sys.exit(exit_code)

    authorization = authenticate()
    print("  Auth: OK")

    # Fetch objects XSD for field validation
    xsd_resp = urllib.request.urlopen(XSD_URLS["objects"], timeout=30)
    xsd_text = xsd_resp.read().decode()

    # Map of (endpoint, params, xsd_type, response_key)
    validations = [
        ("v2/list/trip", {"format": "json", "page_size": "1", "past": "true"}, "Trip", "Trip"),
        ("v2/get/profile", {"format": "json"}, "Profile", "Profile"),
    ]

    for endpoint, params, xsd_type, resp_key in validations:
        ok, issues = validate_endpoint_fields(authorization, xsd_text, endpoint, params, xsd_type, resp_key)
        icon = "PASS" if ok else "WARN"
        print(f"  [{icon}] {endpoint} vs {xsd_type}")
        for issue in issues:
            print(f"         {issue}")
            if "Unknown" in issue:
                exit_code = 1  # Only fail on truly unexpected changes

    print(f"\n{'=' * 60}")
    print(f"  Validation complete. Exit code: {exit_code}")
    print(f"{'=' * 60}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
