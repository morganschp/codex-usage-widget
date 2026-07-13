#!/bin/bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.local/share/codex-usage-widget"
SCRIPTABLE_DIR="$HOME/Library/Mobile Documents/iCloud~dk~simonbs~Scriptable/Documents"
PLIST="$HOME/Library/LaunchAgents/com.openai.codex-usage-widget.plist"
LABEL="com.openai.codex-usage-widget"
PYTHON="$(command -v python3 || true)"

if [[ -z "$PYTHON" ]]; then
  echo "python3 was not found. Install Apple Command Line Tools or Python 3 first."
  exit 1
fi

if [[ ! -x "/Applications/ChatGPT.app/Contents/Resources/codex" ]] \
  && [[ ! -x "/Applications/Codex.app/Contents/Resources/codex" ]] \
  && [[ ! -x "$HOME/Applications/ChatGPT.app/Contents/Resources/codex" ]] \
  && [[ ! -x "$HOME/Applications/Codex.app/Contents/Resources/codex" ]]; then
  echo "Could not find the Codex executable bundled with the ChatGPT/Codex app."
  echo "Move the app to Applications, open it, and sign in before rerunning this installer."
  exit 1
fi

mkdir -p "$INSTALL_DIR" "$HOME/Library/LaunchAgents" "$SCRIPTABLE_DIR"
cp "$PACKAGE_DIR/codex_usage_to_icloud.py" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/codex_usage_to_icloud.py"
cp "$PACKAGE_DIR/Codex Usage.js" "$SCRIPTABLE_DIR/Codex Usage.js"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>

  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$INSTALL_DIR/codex_usage_to_icloud.py</string>
  </array>

  <key>RunAtLoad</key>
  <true/>

  <key>StartInterval</key>
  <integer>900</integer>

  <key>StandardOutPath</key>
  <string>/tmp/codex-usage-widget.log</string>

  <key>StandardErrorPath</key>
  <string>/tmp/codex-usage-widget.err</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo
echo "Installed."
echo "Updater: $INSTALL_DIR/codex_usage_to_icloud.py"
echo "Widget:  $SCRIPTABLE_DIR/Codex Usage.js"
echo "Logs:    /tmp/codex-usage-widget.log and /tmp/codex-usage-widget.err"
echo
echo "Open Scriptable on your iPhone and run 'Codex Usage' once."
