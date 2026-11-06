"""Renders heroes built from the export alone, heroes.glb and heroes_placements.json, by the hand-off's rules (export_hero_kit.from_table),
to compare with the approved pose sheets; and checks each against the kit's own assembly (triangles and bounds).

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_hero_export.py
Writes art/preview/hero_export_check_vN.png (front three-quarter) and hero_export_check_back_vN.png.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_hero_kit as hb  # noqa: E402
import export_hero_kit as ex  # noqa: E402
import hexkit as hk  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_hero_kit as rh  # noqa: E402
import render_preview as rp  # noqa: E402

S = hb.SWATCHES
H, E, C = S["hair"], S["eyes"], S["cloth"]
HEROES = [  # one of each approved pose family, across races, builds and armour
    rh.hero("human", "average", "a", "short", S["skin"]["human"][1], H[1], E[1], C[1], "light", "glaive"),
    rh.hero("dwarf", "broad", "b", "short", S["skin"]["dwarf"][2], H[2], E[2], C[0], "medium", "brass_knuckles"),
    rh.hero("elf", "slim", "c", "long", S["skin"]["elf"][1], H[3], E[0], C[2], "none", "wraps"),
    rh.hero("halfling", "average", "a", "topknot", S["skin"]["halfling"][0], H[0], E[1], C[3], "light", "shortbow"),
    rh.hero("dragonborn", "broad", "a", None, hb.DRAGON_TYPES["blue"], H[1], E[3], C[4], "heavy", "greatsword"),
    rh.hero("tiefling", "slim", "b", "long", S["skin"]["tiefling"][2], H[4], E[4], C[5], "light", "dagger"),
    dict(rh.hero("golem", "average", "a", None, S["skin"]["golem_metal"][0], H[1], E[1], C[1], "heavy", "battleaxe"), two=True),
    rh.hero("human", "broad", "d", "spiky", S["skin"]["human"][3], H[5], E[2], C[2], "heavy", "longsword", "dagger"),
    dict(rh.hero("elf", "average", "b", "tail", S["skin"]["elf"][0], H[2], E[0], C[0], "none", "staff"), caster=True),
    rh.hero("human", "average", "c", "crest", S["skin"]["human"][0], H[3], E[1], C[4], "medium", "battleaxe"),
]


def glb_templates():
    bpy.ops.import_scene.gltf(filepath=os.path.join(hk.ART, "export", "heroes.glb"))
    for m in list(bpy.data.materials):  # the importer's own "kit"; the hero takes the kit's material, as in Godot
        m.name = "imported_" + m.name
    t = {}
    for o in list(bpy.data.objects):
        if o.type == "MESH":
            src = o.data.color_attributes[0]  # the importer's float layer: copy it to a byte one, so bmesh reads sRGB bytes as Godot's linear_to_srgb gives
            dst = o.data.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
            for a, b_ in zip(src.data, dst.data):
                b_.color = a.color
            o.data.color_attributes.remove(o.data.color_attributes[src.name])
            o.hide_render = True
            t[o.name] = o
    return t


def main():
    with open(ex.PATH) as f:
        T = json.load(f)
    kit_layout = hb.layout
    # Kit's own assembly, for the numbers.
    hk.empty_scene()
    kit = rp.load_templates(rp.latest(os.path.join("minis", "heroes"), "heroes"))
    col = hk.new_collection("kit")
    want = []
    for i, d in enumerate(HEROES):
        ob, n = hb.assemble(kit, d, f"kit{i}", col)
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        want.append((n, tuple(round(min(v[k] for v in bb), 3) for k in range(3)) + tuple(round(max(v[k] for v in bb), 3) for k in range(3))))
    # From the export alone.
    back = ex.Y_UP.inverted()

    def from_export(d):
        return [(n, hb.Matrix.Identity(4) if m is None else back @ _mat(m) @ ex.Y_UP) for n, m in ex.from_table(T, d)]
    hb.layout = from_export
    for spin, tag in ((-28, ""), (152, "_back")):
        hk.empty_scene()
        t = glb_templates()
        col = hk.new_collection("line")
        hk.PALETTE["hero_ground"] = rh.GROUND
        rh.floor(col)
        for i, d in enumerate(HEROES):
            ob, n = hb.assemble(t, d, f"exp{i}", col)
            if not tag:
                bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
                got = (n, tuple(round(min(v[k] for v in bb), 3) for k in range(3)) + tuple(round(max(v[k] for v in bb), 3) for k in range(3)))
                same = got[0] == want[i][0] and max(abs(a - b) for a, b in zip(got[1], want[i][1])) < 2e-3
                print("HERO", d["race"], d["build"], d["main"], d.get("offhand"), "tris", got[0], "kit", want[i][0], "MATCH" if same else "DIFFERENT")
            ob.location = Vector((1.05 * (i - (len(HEROES) - 1) / 2), 0, 0))
            ob.rotation_euler.z = math.radians(spin)
        rh.shot(f"hero_export_check{tag}", Vector((0, 0, 0.6)), 16, 10, (3200, 760))
    hb.layout = kit_layout


def _mat(m):
    return hb.Matrix(((m[0], m[3], m[6], m[9]), (m[1], m[4], m[7], m[10]), (m[2], m[5], m[8], m[11]), (0, 0, 0, 1)))


if __name__ == "__main__":
    main()
