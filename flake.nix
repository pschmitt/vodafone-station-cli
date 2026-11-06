{
  description = "CLI for interacting with Vodafone Station devices";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pythonPkgs = pkgs.python3Packages;

        aiovodafone = pythonPkgs.buildPythonPackage {
          pname = "aiovodafone";
          version = "3.3.10";
          format = "wheel";

          src = pkgs.fetchurl {
            url =
              "https://files.pythonhosted.org/packages/1e/43/aaa4ad50fe2928c5ff4a85397019ad875c766f4f02ade9a11765009e4dd8/aiovodafone-3.3.10-py3-none-any.whl";
            hash = "sha256-85g5rT4le+q8zjY8R+iAzo147ALXwcD1KifEAOwOMiE=";
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
          nativeBuildInputs = with pythonPkgs; [ setuptools wheel ];
          propagatedBuildInputs = with pythonPkgs; [ rich aiovodafone ];
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
      in {
        packages.vodafone-station-cli = vodafoneStationCliPkg;
        packages.default = vodafoneStationCliPkg;
        devShells.default = devShell;
      });
}
