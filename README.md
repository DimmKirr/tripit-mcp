# TripIt MCP Server

An [MCP](https://modelcontextprotocol.io/) server that gives AI assistants access to your TripIt travel data — trips, flights, hotels, and more.

Uses the undocumented TripIt v2 mobile API with OAuth2 password grant.

## Quick Start

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tripit": {
      "command": "tripit-mcp",
      "env": {
        "TRIPIT_USERNAME": "your@email.com",
        "TRIPIT_PASSWORD": "your_password",
        "TRIPIT_CLIENT_ID": "your_client_id",
        "TRIPIT_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

### Install

```bash
# From source
git clone https://github.com/dimmkirr/tripit-mcp.git && cd tripit-mcp
uv sync

# Docker (HTTP mode)
cp .env.example .env  # edit with your credentials
docker compose up -d
```

### Nix (home-manager)

See [`nix/tripit-mcp.nix`](nix/tripit-mcp.nix) for a home-manager module using `devcell.managedMcp`.

## Configuration

Four environment variables are required:

| Variable | Description |
|----------|-------------|
| `TRIPIT_USERNAME` | TripIt account email |
| `TRIPIT_PASSWORD` | TripIt account password |
| `TRIPIT_CLIENT_ID` | iOS app client ID |
| `TRIPIT_CLIENT_SECRET` | iOS app client secret |

Pass them via your MCP client config, shell environment, or `.env` file (for Docker).

## Tools

| Tool | Description |
|------|-------------|
| `list_trips` | List past or upcoming trips with pagination |
| `get_trip` | Get trip details — flights, hotels, car rentals, etc. |

## Development

```bash
uv sync --dev
pytest tests/ -v            # 16 unit tests
python scripts/smoke_test.py  # real API smoke test (needs credentials)
ruff check . && black .
```

## License

MIT
