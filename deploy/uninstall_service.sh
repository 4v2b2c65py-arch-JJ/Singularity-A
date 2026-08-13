#!/bin/bash
set -euo pipefail

PLIST_LABEL="com.qbprotocol.server"
PLIST_DEST="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"

if launchctl list "$PLIST_LABEL" >/dev/null 2>&1; then
  launchctl bootout gui/$(id -u)/"$PLIST_LABEL" || true
fi

rm -f "$PLIST_DEST"

echo "Uninstalled $PLIST_LABEL"
