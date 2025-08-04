{
  description = "Versions - File tracking service with ontology-based snapshots";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        pythonEnv = pkgs.python3.withPackages (ps: with ps; [
          (ps.buildPythonPackage rec {
            pname = "owlready2";
            version = "0.38";
            src = ps.fetchPypi {
              inherit pname version;
              sha256 = "sha256-n7afRw7FpFp9TQo5exq5OeCUBNRLkT1vcno6Kn9l8n0=";
            };
            doCheck = false;
          })
          pywatchman
          flask
          werkzeug
        ]);

        versions = pkgs.stdenv.mkDerivation {
          pname = "versions";
          version = "1.0.0";
          
          src = ./.;
          
          buildInputs = [ pythonEnv ];
          
          installPhase = ''
            mkdir -p $out/bin $out/share/versions
            
            # Copy Python files
            cp *.py $out/share/versions/
            
            # Create wrapper script
            cat > $out/bin/versions << EOF
            #!${pkgs.bash}/bin/bash
            exec ${pythonEnv}/bin/python $out/share/versions/watcher.py "\$@"
            EOF
            chmod +x $out/bin/versions
          '';
        };
      in
      {
        packages.default = versions;
        
        apps.default = flake-utils.lib.mkApp {
          drv = versions;
        };
        
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            pythonEnv
            watchman
          ];
        };
      }
    ) // {
      nixosModules.default = { config, lib, pkgs, ... }:
        with lib;
        let
          cfg = config.services.versions;
        in
        {
          options.services.versions = {
            enable = mkEnableOption "Versions file tracking service";
            
            watchPath = mkOption {
              type = types.str;
              description = "Path to watch for changes";
              example = "/home/user/projects";
            };
            
            user = mkOption {
              type = types.str;
              default = "versions";
              description = "User under which the service runs";
            };
            
            group = mkOption {
              type = types.str;
              default = "versions";
              description = "Group under which the service runs";
            };
            
            snapshotPath = mkOption {
              type = types.str;
              default = "/var/lib/versions/snapshots";
              description = "Path where snapshots are stored";
            };
          };
          
          config = mkIf cfg.enable {
            users.users.${cfg.user} = {
              isSystemUser = true;
              group = cfg.group;
              home = "/var/lib/versions";
              createHome = true;
            };
            
            users.groups.${cfg.group} = {};
            
            systemd.services.versions = {
              description = "Versions File Tracking Service";
              after = [ "network.target" ];
              wantedBy = [ "multi-user.target" ];
              
              environment = {
                HOME = "/var/lib/versions";
              };
              
              serviceConfig = {
                Type = "simple";
                User = cfg.user;
                Group = cfg.group;
                ExecStart = "${self.packages.${pkgs.system}.default}/bin/versions ${cfg.watchPath}";
                Restart = "always";
                RestartSec = 10;
                
                # Create necessary directories
                StateDirectory = "versions versions/snapshots";
                StateDirectoryMode = "0750";
              };
            };
          };
        };
        
      darwinModules.default = { config, lib, pkgs, ... }:
        with lib;
        let
          cfg = config.services.versions;
        in
        {
          options.services.versions = {
            enable = mkEnableOption "Versions file tracking service";
            
            watchPath = mkOption {
              type = types.str;
              description = "Path to watch for changes";
              example = "/Users/user/projects";
            };
            
            logPath = mkOption {
              type = types.str;
              default = "/var/log/versions.log";
              description = "Path for log output";
            };
          };
          
          config = mkIf cfg.enable {
            launchd.daemons.versions = {
              serviceConfig = {
                Label = "com.versions";
                ProgramArguments = [
                  "${self.packages.${pkgs.system}.default}/bin/versions"
                  cfg.watchPath
                ];
                RunAtLoad = true;
                KeepAlive = true;
                StandardOutPath = cfg.logPath;
                StandardErrorPath = "${cfg.logPath}.error";
              };
            };
          };
        };
    };
}