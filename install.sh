#!/bin/bash

set -e

PROJECT_NAME="versions"
INSTALL_DIR="/opt/$PROJECT_NAME"
VENV_DIR="$INSTALL_DIR/venv"
SERVICE_USER="${PROJECT_NAME}"
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

echo "Installing $PROJECT_NAME on $OS_TYPE..."

echo "Creating installation directory..."
mkdir -p "$INSTALL_DIR"

echo "Copying project files..."
cp -r "$CURRENT_DIR"/*.py "$INSTALL_DIR/"
cp -r "$CURRENT_DIR"/requirements.txt "$INSTALL_DIR/"

echo "Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"

echo "Installing dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

if [[ "$OS_TYPE" == "linux" ]]; then
    echo "Creating service user..."
    if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
        useradd -r -s /bin/false -d "$INSTALL_DIR" "$SERVICE_USER"
    fi
    
    echo "Setting permissions..."
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    
    echo "Installing systemd service..."
    cat > /etc/systemd/system/${PROJECT_NAME}.service << EOF
[Unit]
Description=Versions File Tracking Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python $INSTALL_DIR/watcher.py /path/to/watch
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    echo "Reloading systemd and enabling service..."
    systemctl daemon-reload
    systemctl enable ${PROJECT_NAME}.service
    
    echo ""
    echo "Installation complete!"
    echo "To configure the watch path, edit /etc/systemd/system/${PROJECT_NAME}.service"
    echo "Then run: sudo systemctl start ${PROJECT_NAME}"
    echo "To check status: sudo systemctl status ${PROJECT_NAME}"
    echo "To view logs: sudo journalctl -u ${PROJECT_NAME} -f"
    
elif [[ "$OS_TYPE" == "macos" ]]; then
    echo "Setting permissions..."
    chown -R $(whoami) "$INSTALL_DIR"
    
    echo "Installing launchd service..."
    PLIST_PATH="/Library/LaunchDaemons/com.${PROJECT_NAME}.plist"
    cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.${PROJECT_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/python</string>
        <string>$INSTALL_DIR/watcher.py</string>
        <string>/path/to/watch</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/${PROJECT_NAME}.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/${PROJECT_NAME}.error.log</string>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
</dict>
</plist>
EOF

    echo ""
    echo "Installation complete!"
    echo "To configure the watch path, edit $PLIST_PATH"
    echo "Then run: sudo launchctl load $PLIST_PATH"
    echo "To check status: sudo launchctl list | grep ${PROJECT_NAME}"
    echo "To view logs: tail -f /var/log/${PROJECT_NAME}.log"
fi

echo ""
echo "To uninstall, run: sudo $INSTALL_DIR/uninstall.sh"