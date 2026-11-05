"""Every side of each starting tile, for the rule that one can always be walked across every side (design/06 -> First playable): each close up alone, and with farms and villages round it, whose fences must open onto it. East Rime also with six hills tiles round it.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b art/tiles/tiles_vN.blend --factory-startup --python art/scripts/render_start_sides.py
Writes art/preview/start_sides_<name>_<alone|fenced>_vN.png and start_sides_sheet_vN.png.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexkit as hk  # noqa: E402
import render_start_tiles as rs  # noqa: E402
import start_tiles as st  # noqa: E402

if __name__ == "__main__":
    rows, row = [], []
    for name in st.STARTS:
        world = {(0, 0): name}
        for k, d in enumerate(hk.NEIGHBOURS):
            world[d] = "village" if k % 2 else "farmland"
        row += [rs.shot(name, {(0, 0): name}, f"start_sides_{name}_alone", "Every side, alone", 17), rs.shot(name, world, f"start_sides_{name}_fenced", "Farms and villages round it", 24)]
        if len(row) == 4:
            rows.append(row)
            row = []
    hills = {(0, 0): st.RIME, **{d: "hills" for d in hk.NEIGHBOURS}}
    for k, d in enumerate(hk.NEIGHBOURS):
        for d2 in hk.NEIGHBOURS:
            hills.setdefault((d[0] + d2[0], d[1] + d2[1]), "hills" if k % 2 else "plains")
    row += [rs.shot(st.RIME, hills, f"start_sides_{st.RIME}_hills", "Hills all round: no mountains shut it in", 34)]
    while len(row) < 4:
        row.append(row[-1])
    rows.append(row)
    rs.SHEET_STEM = "start_sides_sheet"
    rs.sheet(rows)
