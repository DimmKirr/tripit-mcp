# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TripIt MCP Server — a Model Context Protocol (MCP) server that exposes TripIt travel data to AI assistants. Uses the undocumented TripIt v2 API with OAuth2 ROPC (spoofed iOS client). Built with Python 3.10+, FastMCP, and async httpx.

Reference implementations live in `.context/examples/`:
- `tripit-exporter/` — MCP server using v1 API + OAuth 1.0a (reference for MCP structure)
- `tripit-export/` — CLI exporter using v2 API + OAuth2 ROPC (reference for auth approach)

## Build & Run

Package manager: **uv**

```bash
# Install dependencies (uses uv.lock)
uv sync --dev

# Run server (stdio mode, default)
uv run tripit-mcp

# Run server (HTTP mode)
uv run tripit-mcp --mode http --host 0.0.0.0 --port 8000

# Docker
docker compose up --build
```

## Testing

```bash
# Run all tests (16 total: 5 auth + 7 client + 4 server)
pytest tests/ -v

# Run a single test file
pytest tests/test_auth.py -v

# Smoke test with real credentials (requires env vars)
python scripts/smoke_test.py
```

## Linting & Formatting

```bash
ruff check .
black .
```

## Environment Variables

Required as environment variables (see `.env.example`):
- `TRIPIT_USERNAME` — TripIt account email
- `TRIPIT_PASSWORD` — TripIt account password
- `TRIPIT_CLIENT_ID` — Spoofed iOS app client ID
- `TRIPIT_CLIENT_SECRET` — Spoofed iOS app client secret

## Architecture

**Three-layer design:**

1. **MCP Server** (`tripit_mcp/server.py`) — FastMCP app exposing two tools:
   - `list_trips(past, page_num, page_size)` — List trips with pagination
   - `get_trip(trip_id)` — Get trip details by UUID, includes child objects (flights, lodging, etc.)
   - Lazy client initialization via `get_client()` singleton

2. **API Client** (`tripit_mcp/client.py`) — `TripItClient` wraps the v2 API with async httpx:
   - `GET /v2/list/trip` — list trips with pagination
   - `GET /v2/get/trip/uuid/{uuid}` — get trip details (confirmed via smoke test)
   - Handles TripIt quirk: single item returned as dict, multiple as list

3. **Auth** (`tripit_mcp/auth.py`) — `TripItAuth` manages OAuth2 ROPC tokens:
   - `POST /oauth2/token` with password grant + spoofed iOS client credentials
   - In-memory token cache with conservative expiry (`expires_in / 10`)
   - iPhone user-agent spoofing headers (no Akamai cookies needed)

**Transport:** STDIO (default) or HTTP (uvicorn). All logging goes to stderr.

## TripIt v2 API Notes

- v2 is undocumented (mobile app API). v1 docs: https://github.com/tripit/api/tree/gh-pages/doc/v1
- v2 uses UUID exclusively — no numeric `id` field
- Akamai cookies are NOT required — iPhone user-agent headers are sufficient
- Token TTL is 600s; we use `expires_in / 10` (60s) as safety margin
- Single-item responses come as a dict; multi-item as a list (must normalize)

## Linear Project

[tripit-mcp](https://linear.app/hazelops/project/tripit-mcp-e4025624ee71) — Team: DIMM
