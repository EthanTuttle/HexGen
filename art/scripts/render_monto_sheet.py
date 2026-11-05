"""Monto Town with its fixed water: alone, with a river at both mouths, a river at one, and land at both, from the map camera and turned.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b art/tiles/tiles_vN.blend --factory-startup --python art/scripts/render_monto_sheet.py
Writes art/preview/monto_water_<case>[_turned]_vN.png and monto_water_sheet_vN.png.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_start_tiles as rs  # noqa: E402
import start_tiles as st  # noqa: E402

CASES = (("alone", {(0, 0): st.MONTO}, "Alone", 18), ("both", rs.monto_map((0, 3)), "River at both mouths", 24), ("one", rs.monto_map((0,)), "River at one, land at the other", 24), ("land", rs.monto_map(()), "Land at both mouths", 24))

if __name__ == "__main__":
    rows = []
    for turn, tag, note in ((0.0, "", ""), (math.radians(120), "_turned", ", turned")):
        rows.append([rs.shot(st.MONTO, world, f"monto_water_{key}{tag}", sub + note, dist, turn) for key, world, sub, dist in CASES])
    rs.SHEET_STEM = "monto_water_sheet"
    rs.sheet(rows)
