{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/bd9b686c0168041aea600222be0805a0de6e6ab8";
    flake-utils.url = "github:numtide/flake-utils/ff7b65b44d01cf9ba6a71320833626af21126384";
    flake-compat = {
      url = "github:edolstra/flake-compat/35bb57c0c8d8b62bbfd284272c928ceb64ddbde9";
      flake = false;
    };
    flakes.url = "github:deemp/flakes/";
  };
  outputs = inputs: inputs.flakes.makeFlake
    {
      inputs = { inherit (inputs.flakes.all) devshell drv-tools nixpkgs; };
      perSystem = { inputs, system }:
        let
          pkgs = inputs.nixpkgs.legacyPackages.${system};
          inherit (inputs.drv-tools.lib.${system}) getExe mkShellApps;
          inherit (inputs.devshell.lib.${system}) mkShell mkCommands mkRunCommands;
          packages = mkShellApps {
            default = {
              runtimeInputs = [ pkgs.poetry ];
              text = ''
                export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath [
                  pkgs.stdenv.cc.cc.lib
                ]}
                poetry run python main.py --fetch
              '';
              description = ''run main'';
            };
          };
          devShells.default = mkShell {
            commands = (map (x: { package = x; }) [
              pkgs.poetry
            ]) ++ mkCommands "scripts" [ packages.default ];
          };
        in
        {
          inherit packages devShells;
        };
    };
}
