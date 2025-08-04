#!/bin/bash

set -e

PROJECT_NAME="versions"
INSTALL_DIR="/opt/$PROJECT_NAME"

if [[ "$EUID" -ne 0 ]]; then 
   echo "This script must be run as root (use sudo)" 
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

echo "Uninstalling $PROJECT_NAME..."

if [[ "$OS_TYPE" == "linux" ]]; then
    echo "Stopping and disabling systemd service..."
    systemctl stop ${PROJECT_NAME} 2>/dev/null || true
    systemctl disable ${PROJECT_NAME} 2>/dev/null || true
    
    echo "Removing systemd service file..."
    rm -f /etc/systemd/system/${PROJECT_NAME}.service
    
    echo "Reloading systemd..."
    systemctl daemon-reload
    
    echo "Removing service user..."
    userdel ${PROJECT_NAME} 2>/dev/null || true
    
elif [[ "$OS_TYPE" == "macos" ]]; then
    PLIST_PATH="/Library/LaunchDaemons/com.${PROJECT_NAME}.plist"
    
    echo "Unloading launchd service..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    
    echo "Removing launchd plist..."
    rm -f "$PLIST_PATH"
    
    echo "Removing log files..."
    rm -f /var/log/${PROJECT_NAME}.log
    rm -f /var/log/${PROJECT_NAME}.error.log
fi

echo "Removing installation directory..."
rm -rf "$INSTALL_DIR"

echo "Uninstallation complete!"