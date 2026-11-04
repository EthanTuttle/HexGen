"""Finds sheets of faces wound into what's behind them, which an engine culls from outside though a both-sided preview shows them: backs to open air, fronts running into the piece.
Piece.finish turns open sheets the right way, so anything found here is a face built by hand the wrong way round, or a closed shape turned inside out, and needs looking at. fm.export stops on one.

Run on a blend: /Applications/Blender.app/Contents/MacOS/Blender -b <blend> --python art/scripts/check_winding.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import bmesh  # noqa: E402

import hexkit as hk  # noqa: E402


def report(objects=None):
    """Prints each mesh with inward sheets and returns {name: faces in them}."""
    bad = {}
    for ob in objects if objects is not None else bpy.data.objects:
        if ob.type != "MESH" or not ob.data.polygons or ob.data.name in bad:
            continue
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        webs = [k for k, m in enumerate(ob.data.materials) if m and m.name == "web"]  # see-through, and shown from both sides by its material
        count = sum(len(sheet) for sheet in hk.inward_sheets(bm, {f for f in bm.faces if f.material_index in webs}))
        bm.free()
        if count:
            bad[ob.data.name] = count
    for name, count in sorted(bad.items()):
        print(f"WINDING {name}: {count} faces")
    print(f"WINDING {len(bad)} pieces with inward faces, {sum(bad.values())} faces")
    return bad


if __name__ == "__main__":
    report()
