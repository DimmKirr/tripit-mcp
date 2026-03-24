# TripIt MCP Server — Linear Tickets

Project: [tripit-mcp](https://linear.app/hazelops/project/tripit-mcp-e4025624ee71)

## Ticket 1: Viability — Smoke test v2 API with spoofed iOS client
**Size: Small | Priority: High**

Verify `/v2/get/trip` works with OAuth2 ROPC + spoofed iOS client credentials before building the full MCP server.

**Context:**
- `/v2/list/trip` is proven (tripit-export uses it)
- `/v2/get/trip` on v2 is unconfirmed — tripit-exporter uses `/v1/get/trip` with OAuth 1.0a
- v2 trips use `uuid` instead of `id` — need to confirm how `get/trip` references them

**Tasks:**
- [ ] Write standalone script: authenticate via OAuth2 ROPC (`POST /oauth2/token`)
- [ ] Test `GET /v2/list/trip` — confirm working (baseline)
- [ ] Test `GET /v2/get/trip/id/{id}` and/or `GET /v2/get/trip/uuid/{uuid}`
- [ ] Document v2 data contract differences vs v1
- [ ] Test with and without Akamai cookies to understand requirement

---

## Ticket 2: Project scaffolding + OAuth2 auth client
**Size: Small (mostly copy/paste) | Priority: High | Blocked by: #1**

Set up project structure and port the OAuth2 ROPC auth from tripit-export.

**Tasks:**
- [ ] Package structure: `tripit_mcp/__init__.py`, `__main__.py`, `server.py`, `auth.py`, `client.py`
- [ ] `pyproject.toml` — deps: `fastmcp>=2.3.3`, `httpx>=0.28.0`, `uvicorn>=0.23.0`
- [ ] `Dockerfile`, `docker-compose.yml` (adapt from tripit-exporter)
- [ ] `.env.example` with `TRIPIT_USERNAME`, `TRIPIT_PASSWORD`, `TRIPIT_CLIENT_ID`, `TRIPIT_CLIENT_SECRET`
- [ ] `auth.py`: OAuth2 ROPC token management — port `get_auth()` from tripit-export, use in-memory cache with expiry, add token refresh
- [ ] iPhone user-agent headers + Akamai cookie constants
- [ ] STDIO + HTTP transport mode support in `__main__.py`

---

## Ticket 3: `list_trips` MCP tool
**Size: Medium | Priority: High | Blocked by: #2**

Implement the first MCP tool: listing trips via v2 API.

**Tasks:**
- [ ] `client.py`: `TripItClient` class — async httpx, v2 base URL, Bearer token auth
- [ ] `list_trips()` method with params: `past`, `page_num`, `page_size`, `traveler`
- [ ] Handle TripIt quirk: single trip returned as dict, multiple as list
- [ ] FastMCP v2 `@app.tool` registration with proper description and type hints
- [ ] Response formatting: extract key fields (uuid, display_name, start/end_date, primary_location, etc.)
- [ ] Pagination metadata in response (`page_num`, `page_size`, `max_page`)
- [ ] Unit tests with mocked responses

---

## Ticket 4: `get_trip` MCP tool
**Size: Medium | Priority: High | Blocked by: #3**

Implement trip detail retrieval with child objects.

**Tasks:**
- [ ] `get_trip(trip_id)` method in `TripItClient` — use endpoint confirmed in ticket #1
- [ ] FastMCP v2 `@app.tool` registration
- [ ] Return full trip detail including child objects (flights, lodging, car, etc.)
- [ ] Error handling for not-found trips
- [ ] Unit tests

---

## Ticket 5: Extended MCP tools — list/get travel objects
**Size: Large | Priority: Normal | Blocked by: #4**

Add tools for specific travel object types.

**Candidate tools (verify v2 support for each):**
- [ ] `list_flights(trip_id)` — AirObject segments
- [ ] `list_lodging(trip_id)` — LodgingObject
- [ ] `list_transport(trip_id)` — car, rail, transport, cruise
- [ ] `list_activities(trip_id)` — ActivityObject
- [ ] `list_notes(trip_id)` — NoteObject
- [ ] Generic `list_objects(trip_id, type?)` — unified endpoint

**Or** a single `get_trip_details(trip_id)` that returns everything organized by type.

Scope TBD based on what v2 actually supports (findings from ticket #1).

---

## Ticket 6: Akamai cookie automation via Playwright
**Size: Medium | Priority: Normal | Blocked by: #3**

The hardcoded Akamai bot-detection cookies (`ak_bmsc`, `bm_sv`, `_abck`, `bm_sz`) expire. Automate cookie refresh.

**Tasks:**
- [ ] Playwright-based flow: navigate to tripit.com, extract cookies
- [ ] Cookie refresh strategy: on auth failure? periodic? on startup?
- [ ] Store cookies in memory with TTL
- [ ] Fallback: attempt requests without cookies first, use Playwright only if needed
- [ ] Add `playwright` to optional dependencies

---

## Environment Variables

| Var | Required | Notes |
|-----|----------|-------|
| `TRIPIT_USERNAME` | yes | TripIt account email |
| `TRIPIT_PASSWORD` | yes | TripIt account password |
| `TRIPIT_CLIENT_ID` | yes | Spoofed iOS app client ID |
| `TRIPIT_CLIENT_SECRET` | yes | Spoofed iOS app client secret |

## Architecture Decision

- **v2 API** (undocumented, mobile app) with **OAuth2 ROPC** (password grant)
- NOT v1 + OAuth 1.0a (requires browser-based 3-legged flow)
- Spoofed iOS client: `user-agent: Tripit/18.1.0.2310191134 iPhone/17.0.2`
- FastMCP v2 framework, async httpx, STDIO + HTTP transport
