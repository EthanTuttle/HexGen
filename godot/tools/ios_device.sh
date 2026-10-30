#!/bin/zsh
# Builds the prototype for a real iPhone and installs and launches it there, from the repo root:
#   HEXGEN_TEAM=<team id> godot/tools/ios_device.sh [device UDID]   (default: the first connected iPhone)
# The team is the Apple Developer team that signs it (a free Personal Team works: pick it once in Xcode's Signing &
# Capabilities, and Xcode makes the certificate on the first build). Signing is automatic. The phone needs
# Developer Mode on, and the developer trusted once after the first install (Settings > General > VPN & Device
# Management). Logs from the launch go to build/ios/device_launch.log.
set -e
cd "$(dirname "$0")/../.."
: ${HEXGEN_TEAM:?set HEXGEN_TEAM to the signing team ID}
GODOT=/Applications/Godot.app/Contents/MacOS/Godot
OUT=build/ios
DEVICE="${1:-$(xcrun devicectl list devices 2>/dev/null | grep -E "iPhone.*physical" | grep -v unavailable | head -1 | grep -oE "[0-9A-F]{8}-[0-9A-F]{16}")}"
echo "device $DEVICE"

echo "== 1. Export the Xcode project"
$GODOT --headless --path godot --export-debug "iOS Simulator" ../$OUT/HexGen.ipa

echo "== 2. Build for the phone (automatic signing)"
xcodebuild -project $OUT/HexGen.xcodeproj -scheme HexGen -configuration Debug -destination "id=$DEVICE" \
	-derivedDataPath $OUT/derived-device -allowProvisioningUpdates -allowProvisioningDeviceRegistration \
	DEVELOPMENT_TEAM=$HEXGEN_TEAM build | tail -3
APP=$OUT/derived-device/Build/Products/Debug-iphoneos/HexGen.app

echo "== 3. Install and launch"
xcrun devicectl device install app --device "$DEVICE" "$APP" | tail -2
xcrun devicectl device process launch --device "$DEVICE" --console --terminate-existing com.hexgen.prototype \
	> $OUT/device_launch.log 2>&1 &
sleep 20
tail -20 $OUT/device_launch.log
