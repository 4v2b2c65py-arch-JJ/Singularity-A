#!/bin/bash
set -euo pipefail

PLIST_LABEL="com.qbprotocol.server"
PLIST_SRC="/Users/jjmarte/delta-stream/qb_protocol/deploy/com.qbprotocol.server.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
LOG_DIR="$HOME/Library/Logs"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

if [ ! -f "$PLIST_SRC" ]; then
  echo "Missing plist source at $PLIST_SRC" >&2
  exit 1
fi

cp "$PLIST_SRC" "$PLIST_DEST"

if launchctl list "$PLIST_LABEL" >/dev/null 2>&1; then
  launchctl bootout gui/$(id -u)/"$PLIST_LABEL" || true
fi

launchctl bootstrap gui/$(id -u) "$PLIST_DEST"
launchctl enable gui/$(id -u)/"$PLIST_LABEL" || true

echo "Installed and started $PLIST_LABEL"
echo "Logs: $LOG_DIR/qb_protocol_server.out.log"
echo "Logs: $LOG_DIR/qb_protocol_server.err.log"
