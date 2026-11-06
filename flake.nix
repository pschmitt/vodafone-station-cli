{
  description = "CLI for interacting with Vodafone Station devices";

  inputs = {
    # Keep Intel macOS supported alongside the other default systems.
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-26.05-darwin";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    { nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pythonPkgs = pkgs.python3Packages;

        aiovodafone = pythonPkgs.buildPythonPackage {
          pname = "aiovodafone";
          # Later releases require Python dependencies newer than this package
          # set. Keep their version checks enabled rather than relaxing them.
          version = "3.3.0";
          format = "wheel";

          src = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/a5/c8/e417a60be466c85ee97aa0335c2f480a2fcaf382c386f182c584da28e2d8/aiovodafone-3.3.0-py3-none-any.whl";
            hash = "sha256-JdmGD1vTMjfLVDVg63a9W1SDuJvsURNHo9b6AhPuMzw=";
          };
          propagatedBuildInputs = with pythonPkgs; [
            # deps
            aiohttp
            beautifulsoup4
            orjson
            pycryptodome
            segno
          ];
          meta = {
            description = "Async client for Vodafone Station devices";
            homepage = "https://pypi.org/project/aiovodafone/";
            license = pkgs.lib.licenses.asl20;
            maintainers = [ pkgs.lib.maintainers.pschmitt ];
          };
        };

        vodafoneStationCliPkg = pythonPkgs.buildPythonApplication {
          pname = "vodafone-station-cli";
          version = "0.1.0";
          pyproject = true;
          src = ./.;
          nativeBuildInputs = with pythonPkgs; [
            setuptools
            wheel
          ];
          propagatedBuildInputs = with pythonPkgs; [
            rich
            aiovodafone
          ];
          pythonImportsCheck = [ "cli" ];
          installCheckPhase = ''
            cd "$src"
            python -m unittest discover -s tests -v
          '';
          meta = {
            description = "CLI for interacting with Vodafone Station devices";
            homepage = "https://github.com/pschmitt/vodafone-station-cli";
            license = pkgs.lib.licenses.gpl3Only;
            maintainers = [ pkgs.lib.maintainers.pschmitt ];
            platforms = pkgs.lib.platforms.all;
          };
        };

        # 3) Dev shell: include aiovodafone, correct PYTHONPATH
        devShell = pkgs.mkShell {
          name = "vodafone-station-cli-devshell";

          inputsFrom = [ vodafoneStationCliPkg ];

          nativeBuildInputs = [
            pkgs.gh # GitHub CLI
            pkgs.git
            pythonPkgs.ipython
            pkgs.neovim
          ];

          shellHook = ''
            export PYTHONPATH="$PWD''${PYTHONPATH:+:$PYTHONPATH}"
            echo -e "\e[34mWelcome to the vodafoneStationCli development shell!\e[0m"
          '';
        };
      in
      {
        packages.vodafone-station-cli = vodafoneStationCliPkg;
        packages.default = vodafoneStationCliPkg;
        devShells.default = devShell;
      }
    );
}
