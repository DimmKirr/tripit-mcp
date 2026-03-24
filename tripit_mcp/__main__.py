#!/usr/bin/env python3
"""Entry point for the TripIt MCP server."""

import argparse
import os
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="TripIt MCP Server")
    parser.add_argument("--mode", choices=["stdio", "http"], default="stdio", help="Server mode (default: stdio)")
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
