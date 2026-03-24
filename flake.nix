{
  description = "TripIt MCP Server — TripIt travel data via Model Context Protocol";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};

      tripitMcp = pkgs.python3Packages.buildPythonApplication {
        pname = "tripit-mcp";
        version = "0.1.0";
        src = ./.;
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
      packages = {
        default = tripitMcp;
        tripit-mcp = tripitMcp;
      };

      # Dev shell with test dependencies
      devShells.default = pkgs.mkShell {
        packages = [
          (pkgs.python3.withPackages (ps: with ps; [
            fastmcp
            httpx
            uvicorn
            pytest
            pytest-asyncio
            black
          ]))
          pkgs.ruff
        ];
      };
    });
}
