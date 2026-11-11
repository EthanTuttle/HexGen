#!/bin/zsh
# Builds the latest main as a Mac app and installs it, from the repo root:
#   godot/tools/build_mac.sh            # pull main, export build/mac/HexGen.app, copy it to /Applications
#   godot/tools/build_mac.sh --no-pull  # build what's checked out, without pulling
# Run it in the shared checkout (on main). Saves live in Godot's user folder, so they carry over to the new build.
set -e
cd "$(dirname "$0")/../.."
GODOT=/Applications/Godot.app/Contents/MacOS/Godot
APP=build/mac/HexGen.app
DEST=/Applications/HexGen.app

[[ "$(git branch --show-current)" == "main" ]] || { echo "Not on main: run this in the shared checkout"; exit 1; }
[[ "$1" == "--no-pull" ]] || git pull --ff-only
COMMIT="$(git log -1 --format='%h %ad %s' --date=format:'%b %-d %H:%M')"

mkdir -p build/mac
rm -rf "$APP"
"$GODOT" --headless --path godot --import
"$GODOT" --headless --path godot --export-release "macOS" "../$APP"
[[ -n "$(ls "$APP/Contents/MacOS" 2>/dev/null)" ]] || { echo "Export failed: no game in $APP"; exit 1; }

osascript -e 'quit app "HexGen"' 2>/dev/null || true
rm -rf "$DEST"
ditto "$APP" "$DEST"
echo "Installed $DEST from $COMMIT"
