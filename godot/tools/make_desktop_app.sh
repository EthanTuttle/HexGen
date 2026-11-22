#!/bin/bash
# Builds "Play Heads or Hexes.app" on the Desktop. Double-click it to pull main, build the
# Mac debug app (godot/tools/build_mac.sh) and open it. A Terminal window shows the build;
# it closes nothing on its own, so errors stay readable.
#
# Run it from the shared checkout (HexGen/HexGen), not a worktree, since the app
# remembers the folder it was built from. Rerun it if the repo moves.
#
#   bash godot/tools/make_desktop_app.sh [where]   # default: ~/Desktop
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
DEST="${1:-$HOME/Desktop}/Play Heads or Hexes.app"
ICON_SRC="$REPO/godot/icon_mac_placeholder.png"
TMP="$(mktemp -d)"

cat > "$TMP/main.applescript" <<EOF
set repo to "$REPO"
set cmd to "cd " & quoted form of repo & " && godot/tools/build_mac.sh && open -a 'Heads or Hexes'"
tell application "Terminal"
	activate
	do script cmd
end tell
EOF

rm -rf "$DEST"
osacompile -o "$DEST" "$TMP/main.applescript"

# Icon: the game's placeholder Mac icon, if it's there
if [ -f "$ICON_SRC" ]; then
  SET="$TMP/icon.iconset"
  mkdir "$SET"
  for s in 16 32 128 256 512; do
    sips -z $s $s "$ICON_SRC" --out "$SET/icon_${s}x${s}.png" >/dev/null
    sips -z $((s*2)) $((s*2)) "$ICON_SRC" --out "$SET/icon_${s}x${s}@2x.png" >/dev/null
  done
  iconutil -c icns "$SET" -o "$DEST/Contents/Resources/applet.icns"
  # newer macOS prefers the asset catalog's icon over applet.icns
  rm -f "$DEST/Contents/Resources/Assets.car"
  /usr/libexec/PlistBuddy -c "Delete :CFBundleIconName" "$DEST/Contents/Info.plist" 2>/dev/null || true
  touch "$DEST"
fi
# the edits above break osacompile's signature; sign it again (ad hoc, this Mac only)
codesign --force --deep -s - "$DEST" 2>/dev/null
rm -rf "$TMP"
echo "Made $DEST (builds and opens the game from $REPO)"
