#!/bin/zsh
# Copies the test notes (scripts/test_notes.gd) into build/notes/<where>/, from the repo root:
#   godot/tools/collect_notes.sh mac              # this Mac's runs
#   godot/tools/collect_notes.sh phone [UDID]     # the iPhone over USB (default: the first connected)
# It only copies: nothing is removed from the phone or the Mac, so running it again is safe. Removing an app from the
# phone deletes its notes with it, so collect before ever uninstalling.
set -e
cd "$(dirname "$0")/../.."
WHERE="${1:?mac or phone}"
OUT="build/notes/$WHERE"
mkdir -p "$OUT"
if [[ "$WHERE" == "mac" ]]; then
	SRC="$HOME/Library/Application Support/Godot/app_userdata/HexGen Godot prototype/test_notes"
	[[ -d "$SRC" ]] && cp -pR "$SRC/" "$OUT/"
else
	DEVICE="${2:-$(xcrun devicectl list devices 2>/dev/null | grep -E "iPhone.*physical|available \(paired\)|connected" | grep -v unavailable | head -1 | grep -oE '[0-9A-F]{8}-[0-9A-F]{16}|[0-9A-F-]{36}' | head -1)}"
	: ${DEVICE:?no iPhone found: pass its UDID}
	xcrun devicectl device copy from --device "$DEVICE" --domain-type appDataContainer --domain-identifier com.hexgen.prototype --source Documents/test_notes --destination "$OUT"
fi
echo "$(ls "$OUT" | grep -c '\.json$' || true) notes in $OUT"
