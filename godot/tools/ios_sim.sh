#!/bin/zsh
# Builds the prototype for the iOS Simulator and runs it there, from the repo root:
#   godot/tools/ios_sim.sh [device name]        (default: the newest available iPhone 15 Pro or later)
# Steps: export the Xcode project from Godot (preset "iOS Simulator" in godot/export_presets.cfg), build it for the
# Simulator (arm64, no signing), boot a Simulator, install, launch, and save a screenshot to build/ios/shots/.
# Needs Xcode with its first-launch setup done (sudo xcodebuild -runFirstLaunch) and an iOS Simulator runtime
# (xcodebuild -downloadPlatform iOS). The Simulator runs on the Mac's GPU: its frame rate says nothing about a phone.
set -e
cd "$(dirname "$0")/../.."
GODOT=/Applications/Godot.app/Contents/MacOS/Godot
OUT=build/ios
mkdir -p $OUT/shots

echo "== 1. Export the Xcode project"
$GODOT --headless --path godot --export-debug "iOS Simulator" ../$OUT/HexGen.ipa

echo "== 2. Build for the Simulator (arm64, no code signing)"
xcodebuild -project $OUT/HexGen.xcodeproj -scheme HexGen -configuration Debug \
	-sdk iphonesimulator -arch arm64 -derivedDataPath $OUT/derived \
	CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO DEVELOPMENT_TEAM= build | tail -5
APP=$(find $OUT/derived/Build/Products -name "HexGen.app" -maxdepth 3 | head -1)
echo "built $APP"

echo "== 3. Boot a Simulator"
DEVICE="${1:-}"
if [ -z "$DEVICE" ]; then
	DEVICE=$(xcrun simctl list devices available | grep -E "iPhone (1[5-9]|2[0-9]) Pro" | tail -1 | sed -E 's/^ *(.*) \(([0-9A-F-]+)\).*/\2/')
fi
echo "device $DEVICE"
xcrun simctl boot "$DEVICE" 2>/dev/null || true
open -a Simulator
xcrun simctl bootstatus "$DEVICE" -b

echo "== 4. Install and launch"
xcrun simctl install "$DEVICE" "$APP"
xcrun simctl launch "$DEVICE" com.hexgen.prototype
sleep 8
xcrun simctl io "$DEVICE" screenshot "$OUT/shots/launch.png"
echo "screenshot $OUT/shots/launch.png"
echo "Turn the phone with Device > Rotate Left / Rotate Right (Cmd-Left / Cmd-Right) to put the island on either side."
