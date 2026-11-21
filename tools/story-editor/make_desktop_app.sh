#!/bin/bash
# Builds "Story Editor.app" on the Desktop. Double-click it to open the story editor:
# the server runs in the background (no Terminal window) and stops on its own
# 10 minutes after the last editor tab closes.
#
# Run it from the shared checkout (HexGen/HexGen), not a worktree, since the app
# remembers the folder it was built from. Rerun it if the repo moves.
#
#   bash tools/story-editor/make_desktop_app.sh [where]   # default: ~/Desktop
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
DEST="${1:-$HOME/Desktop}/Story Editor.app"
ICON_SRC="$REPO/godot/icon_mac_placeholder.png"
TMP="$(mktemp -d)"

cat > "$TMP/main.applescript" <<EOF
set repo to "$REPO"
do shell script "cd " & quoted form of repo & " && /usr/bin/python3 tools/story-editor/server.py --idle-exit 600 >> \$HOME/Library/Logs/StoryEditor.log 2>&1 &"
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
echo "Made $DEST (opens the editor from $REPO)"
