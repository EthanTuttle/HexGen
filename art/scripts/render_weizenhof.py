"""Weizenhof Estate: its drive and tracks, front and turned, alone and surrounded.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b art/tiles/tiles_vN.blend --factory-startup --python art/scripts/render_weizenhof.py
Writes art/preview/weizenhof_<case>[_turned]_vN.png and weizenhof_sheet_vN.png.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexkit as hk  # noqa: E402
import render_start_tiles as rs  # noqa: E402
import start_tiles as st  # noqa: E402

N = hk.NEIGHBOURS
ALONE = {(0, 0): st.WEIZEN}
FARMS = {(0, 0): st.WEIZEN, **{d: "farmland" for d in N}}
LAND = {(0, 0): st.WEIZEN, **{d: ("plains" if k % 2 else "forest") for k, d in enumerate(N)}}
CASES = (("alone", ALONE, "Alone", 17), ("farms", FARMS, "Farms all round", 25), ("land", LAND, "Other land all round", 25))

if __name__ == "__main__":
    rows = []
    for turn, tag, note in ((0.0, "", ""), (math.radians(120), "_turned", ", turned")):
        rows.append([rs.shot(st.WEIZEN, world, f"weizenhof_{key}{tag}", sub + note, dist, turn) for key, world, sub, dist in CASES])
    rs.SHEET_STEM = "weizenhof_sheet"
    rs.sheet(rows)
