#!/bin/bash
# install.sh - Automated service installer for Linux (systemd) and macOS (launchd)

set -e

OS_TYPE="$(uname -s)"
PROJECT_DIR="$(pwd)"
PYTHON_BIN="$(which python3 || which python)"

if [ -z "$PYTHON_BIN" ]; then
    echo "Error: Python was not found in your system PATH."
    exit 1
fi

if [ "$OS_TYPE" = "Darwin" ]; then
    # macOS launchd setup
    echo "Detected macOS (Darwin). Installing LaunchAgent daemon..."
    PLIST_NAME="com.fileorganizer.daemon.plist"
    LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
    mkdir -p "$LAUNCH_AGENTS_DIR"
    PLIST_PATH="$LAUNCH_AGENTS_DIR/$PLIST_NAME"

    # Create launchd plist file dynamically
    cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fileorganizer.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$PROJECT_DIR/organizer.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/file-organizer.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/file-organizer.log</string>
</dict>
</plist>
EOF

    # Unload if already loaded, then load and start
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    launchctl load -w "$PLIST_PATH"
    
    echo ""
    echo "=========================================================="
    echo "✔ Installation successful!"
    echo "✔ LaunchAgent registered to: $PLIST_PATH"
    echo "✔ Daemon started running in background."
    echo "=========================================================="
    echo "Manage the daemon using launchctl:"
    echo "  launchctl unload $PLIST_PATH (Stop)"
    echo "  launchctl load -w $PLIST_PATH (Start)"
    echo ""

elif [ "$OS_TYPE" = "Linux" ]; then
    # Linux systemd setup
    echo "Detected Linux. Installing systemd service..."
    SERVICE_NAME="local-file-organizer.service"
    SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
    mkdir -p "$SYSTEMD_USER_DIR"

    sed "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|g" "$SERVICE_NAME" > "$SYSTEMD_USER_DIR/$SERVICE_NAME"
    
    systemctl --user daemon-reload
    systemctl --user enable "$SERVICE_NAME"
    systemctl --user restart "$SERVICE_NAME"

    echo ""
    echo "=========================================================="
    echo "✔ Installation successful!"
    echo "✔ Service registered to: $SYSTEMD_USER_DIR/$SERVICE_NAME"
    echo "✔ Daemon started running in background."
    echo "=========================================================="
    echo "Manage the service using systemctl:"
    echo "  systemctl --user status $SERVICE_NAME"
    echo ""
else
    echo "Unsupported OS: $OS_TYPE"
    exit 1
fi
