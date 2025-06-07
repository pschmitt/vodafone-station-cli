{
  description = "CLI for interacting with Vodafone Station devices";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3;
        pythonPkgs = pkgs.python3Packages;

        aiovodafone = pythonPkgs.buildPythonPackage {
          pname = "aiovodafone";
          version = "1.1.0";
          pyproject = true;

          src = pkgs.fetchPypi {
            pname = "aiovodafone";
            version = "1.1.0";
            sha256 = "sha256-hQznCBW03vNVOzvViWuXrLQ9MFE5blvLMdQHyc8JJ84=";
          };
          propagatedBuildInputs = with pythonPkgs; [
            # build
            poetry-core
            setuptools
            wheel

            # deps
            aiohttp
            beautifulsoup4
          ];
          meta = with pkgs.lib; {
            description = "Async client for Vodafone Station devices";
            homepage = "https://pypi.org/project/aiovodafone/";
            license = licenses.mit;
            maintainers = [ maintainers.pschmitt ];
          };
        };

        vodafoneStationCliPkg = pythonPkgs.buildPythonApplication {
          pname = "vodafone-station-cli";
          version = "0.1.0";
          pyproject = true;
          src = ./.;
          propagatedBuildInputs = with pythonPkgs; [
            rich
            aiovodafone
          ];
          meta = with pkgs.lib; {
            description = "CLI for interacting with Vodafone Station devices";
            homepage = "https://github.com/pschmitt/vodafone-station-cli";
            license = licenses.gpl3Only;
            maintainers = [ maintainers.pschmitt ];
            platforms = platforms.all;
          };
        };

        # 3) Dev shell: include aiovodafone, correct PYTHONPATH
        devShell = pkgs.mkShell {
          name = "vodafone-station-cli-devshell";

          buildInputs = [
            python
            pythonPkgs.rich
            aiovodafone
          ];

          nativeBuildInputs = [
            pkgs.gh # GitHub CLI
            pkgs.git
            pythonPkgs.ipython
            pkgs.neovim
          ];

          shellHook = ''
            export PYTHONPATH=${
              self.packages.${system}.vodafone-station-cli
            }/lib/python${python.version}/site-packages
            echo -e "\e[34mWelcome to the vodafoneStationCli development shell!\e[0m"
          '';
        };
      in
      {
        packages.vodafone-station-cli = vodafoneStationCliPkg;
        defaultPackage = vodafoneStationCliPkg;
        devShells.default = devShell;
      }
    );
}
