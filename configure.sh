#!/bin/bash

set -e

PROJECT_NAME="versions"
INSTALL_DIR="/opt/$PROJECT_NAME"

if [[ "$EUID" -ne 0 ]]; then 
   echo "This script must be run as root (use sudo)" 
   exit 1
fi

if [ -z "$1" ]; then
    echo "Usage: $0 <path-to-watch>"
    echo "Example: $0 /home/user/projects"
    exit 1
fi

WATCH_PATH="$1"

if [ ! -d "$WATCH_PATH" ]; then
    echo "Error: Path '$WATCH_PATH' does not exist or is not a directory"
    exit 1
fi

OS_TYPE="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi

echo "Configuring $PROJECT_NAME to watch: $WATCH_PATH"

if [[ "$OS_TYPE" == "linux" ]]; then
    SERVICE_FILE="/etc/systemd/system/${PROJECT_NAME}.service"
    
    echo "Updating systemd service..."
    sed -i "s|/path/to/watch|$WATCH_PATH|g" "$SERVICE_FILE"
    
    echo "Reloading systemd..."
    systemctl daemon-reload
    
    echo "Restarting service..."
    systemctl restart ${PROJECT_NAME}
    
    echo ""
    echo "Configuration complete!"
    echo "Service status:"
    systemctl status ${PROJECT_NAME} --no-pager
    
elif [[ "$OS_TYPE" == "macos" ]]; then
    PLIST_PATH="/Library/LaunchDaemons/com.${PROJECT_NAME}.plist"
    
    echo "Unloading current service..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    
    echo "Updating launchd plist..."
    sed -i '' "s|/path/to/watch|$WATCH_PATH|g" "$PLIST_PATH"
    
    echo "Loading updated service..."
    launchctl load "$PLIST_PATH"
    
    echo ""
    echo "Configuration complete!"
    echo "Service status:"
    launchctl list | grep ${PROJECT_NAME}
fi