"""FastMCP server exposing TripIt tools."""

import os
import sys
import logging
from typing import Any

from fastmcp import FastMCP

from tripit_mcp.client import TripItClient

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s", stream=sys.stderr)

mcp = FastMCP(
    "TripIt MCP Server",
    instructions="Access your TripIt travel data via MCP",
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
    page_num: int | None = None,
    page_size: int | None = None,
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
        log.exception("list_trips failed")
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
        log.exception("get_trip failed for %s", trip_id)
        return {"error": str(e)}


def start_server(mode: str = "stdio", host: str = "0.0.0.0", port: int = 8000):
    import asyncio

    if mode == "stdio":
        log.info("Starting stdio mode")
        asyncio.run(mcp.run_stdio_async())
    else:
        log.info("Starting HTTP mode on %s:%d", host, port)
        asyncio.run(mcp.run_http_async(host=host, port=port))
