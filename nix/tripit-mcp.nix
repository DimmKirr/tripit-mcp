# tripit-mcp.nix — TripIt MCP server for Claude
# Usage: import in your home-manager configuration
# Pattern follows nixhome/modules/electronics.nix (kicad-mcp)
{pkgs, ...}: let
  tripitMcp = pkgs.python3Packages.buildPythonApplication {
    pname = "tripit-mcp";
    version = "0.1.0";
    src = pkgs.fetchFromGitHub {
      owner = "dimmkirr";
      repo = "tripit-mcp";
      rev = "v0.1.0"; # update to latest release tag
      hash = ""; # nix build will tell you the correct hash on first run
    };
    pyproject = true;
    build-system = [pkgs.python3Packages.setuptools];
    dependencies = with pkgs.python3Packages; [
      fastmcp
      httpx
      uvicorn
    ];
    doCheck = false;
  };
in {
  home.packages = [tripitMcp];

  devcell.managedMcp.servers."tripit-mcp" = {
    command = "tripit-mcp";
    args = [];
    # Reads from environment at runtime:
    # TRIPIT_USERNAME, TRIPIT_PASSWORD, TRIPIT_CLIENT_ID, TRIPIT_CLIENT_SECRET
  };
}
