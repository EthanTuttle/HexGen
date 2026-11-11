---
name: refresh-build
description: Rebuild the game from the latest main and install it as /Applications/Heads or Hexes.app on this Mac. Use only when Ethan asks to refresh, rebuild or update the installed Mac build.
disable-model-invocation: true
---

# Refresh the Mac build

Ethan runs this by hand when he wants the installed game brought up to date. Nothing updates on its own.

1. Run the script from the shared checkout (`HexGen/HexGen`, which stays on `main`), in the background, as an export takes a few minutes:

   ```bash
   godot/tools/build_mac.sh
   ```

   It pulls `main` (fast-forward only), imports, exports a debug `build/mac/Heads or Hexes.app` (report button and debug menu on) with the **macOS** preset in `godot/export_presets.cfg`, quits the game if it's open, and replaces `/Applications/Heads or Hexes.app`.

2. When it finishes, tell Ethan the last line (`Installed … from <commit>`), so he knows which commit he's playing.

If it fails:

- **Pull fails** (local changes or a diverged `main`): don't stash, reset or switch branches in the shared checkout, since other sessions use it. Tell Ethan what's in the way.
- **Export fails**: show the Godot errors. Don't edit game code to make it build; say what broke.

Only work merged to `main` is in the build. If Ethan expects something from an open branch, say it isn't merged yet.
