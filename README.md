# Versions

File system watcher that creates ontology-based snapshots using Watchman.

## Quick Install

### Traditional Install
```bash
sudo ./install.sh
sudo ./configure.sh /path/to/watch
```

### Nix Flake (NixOS/Darwin)

Add to your flake inputs:
```nix
{
  inputs.versions.url = "github:yourusername/versions";
}
```

Enable in configuration:
```nix
# NixOS
{
  imports = [ versions.nixosModules.default ];
  services.versions = {
    enable = true;
    watchPath = "/home/user/projects";
  };
}

# Darwin (macOS with nix-darwin)
{
  imports = [ versions.darwinModules.default ];
  services.versions = {
    enable = true;
    watchPath = "/Users/user/projects";
  };
}
```

Or run directly:
```bash
nix run .# -- /path/to/watch
```

## Manual Installation

### Linux (systemd)

```bash
sudo ./install.sh
sudo ./configure.sh /home/user/projects
sudo systemctl start versions
sudo systemctl status versions
journalctl -u versions -f
```

### macOS (launchd)

```bash
sudo ./install.sh
sudo ./configure.sh /Users/user/projects
sudo launchctl list | grep versions
tail -f /var/log/versions.log
```

## Configuration

Change watched directory:
```bash
sudo ./configure.sh /new/path/to/watch
```

## Uninstall

```bash
sudo ./uninstall.sh
```

## Service Management

### Linux
- Start: `sudo systemctl start versions`
- Stop: `sudo systemctl stop versions`
- Restart: `sudo systemctl restart versions`
- Status: `sudo systemctl status versions`
- Logs: `sudo journalctl -u versions -f`

### macOS
- Start: `sudo launchctl load /Library/LaunchDaemons/com.versions.plist`
- Stop: `sudo launchctl unload /Library/LaunchDaemons/com.versions.plist`
- Status: `sudo launchctl list | grep versions`
- Logs: `tail -f /var/log/versions.log`