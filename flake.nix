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
        
        pythonEnv = pkgs.python311.withPackages (ps: with ps; [
          (ps.buildPythonPackage rec {
            pname = "Owlready2";
            version = "0.38";
            src = ps.fetchPypi {
              inherit pname version;
              sha256 = "sha256-DROEH8nS8QkbB/0PhYSIMChuYGU9S2S5LkThMCSz6/w=";
            };
            pyproject = true;
            build-system = [ ps.setuptools ps.wheel ];
            nativeBuildInputs = [ ps.setuptools ps.wheel ];
            doCheck = false;
          })
          pywatchman
          flask
          werkzeug
        ]);

        versions = pkgs.stdenv.mkDerivation {
          pname = "versions";
          version = "1.0.0";
          
          src = self;
          
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
            perUserServices = mkOption {
              type = types.attrsOf (types.submodule {
                options = {
                  enable = mkEnableOption "Versions file tracking service for this user";
                  
                  watchPaths = mkOption {
                    type = types.listOf types.str;
                    default = [];
                    description = "Paths to watch for changes";
                    example = [ "/home/user/projects" "/home/user/documents" ];
                  };
                };
              });
              default = {};
              description = "Per-user versions services";
              example = literalExpression ''
                {
                  alice = {
                    enable = true;
                    watchPaths = [ "/home/alice/projects" ];
                  };
                  bob = {
                    enable = true;
                    watchPaths = [ "/home/bob/code" "/home/bob/documents" ];
                  };
                }
              '';
            };
          };
          
          config = mkIf (cfg.perUserServices != {}) {
            # Increase inotify limits for watchman
            boot.kernel.sysctl = {
              "fs.inotify.max_user_watches"   = 1048576;  # default 8192
              "fs.inotify.max_user_instances" = 8192;     # default 128
            };
            
            # Create a user service for each user with versions enabled
            systemd.services = mkMerge (
              flatten (mapAttrsToList (username: userCfg: 
                map (watchPath: 
                  let 
                    pathHash = builtins.substring 0 8 (builtins.hashString "sha256" watchPath);
                    serviceName = "versions-${username}-${pathHash}";
                  in
                  mkIf userCfg.enable {
                    ${serviceName} = {
                      description = "Versions tracking ${watchPath} for ${username}";
                      after = [ "network.target" ];
                      wantedBy = [ "multi-user.target" ];
                      
                      path = [ pkgs.watchman ];
                      
                      environment = {
                        HOME = "/home/${username}";
                      };
                      
                      serviceConfig = {
                        Type = "simple";
                        User = username;
                        ExecStart = "${self.packages.${pkgs.system}.default}/bin/versions ${watchPath}";
                        Restart = "always";
                        RestartSec = 10;
                      };
                    };
                  }
                ) userCfg.watchPaths
              ) cfg.perUserServices)
            );
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