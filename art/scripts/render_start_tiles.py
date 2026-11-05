"""Previews of the starting tiles, built by the same build_map as every other terrain: each alone, as it first drops in, and with neighbours of its own and other terrains.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b art/tiles/tiles_vN.blend --factory-startup --python art/scripts/render_start_tiles.py
Writes art/preview/start_kit_<name>_<alone|near>_vN.png, Monto's other water, and the sheet start_kit_sheet_vN.png.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import canyon_takes as ct  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import start_tiles as st  # noqa: E402
import variants as vr  # noqa: E402,F401

TITLES = {st.DUNFAIRE: "Dunfaire Tower", st.RIME: "East Rime Chapel", st.MONTO: "Monto Town", st.SPIRE: "Sternbrunn Spire", st.OAK: "The Oak & Lantern", st.WEIZEN: "Weizenhof Estate"}
N = hk.NEIGHBOURS
SHEET_STEM = "start_kit_sheet"


def near_map(name):
    """Neighbours of its own terrain on two sides, other land on the rest."""
    own = st.STARTS[name]
    other = {"ruins": "plains", "hills": "forest", "river": "plains", "desert": "plains", "forest": "plains", "farmland": "plains"}[own]
    world = {(0, 0): name}
    for k, d in enumerate(N):
        world[d] = own if k in (1, 3, 4) else other
    if own == "hills":
        world[N[2]] = "plains"
    return world


def monto_map(edges):
    world = {(0, 0): st.MONTO}
    for k, d in enumerate(N):
        world[d] = "river" if k in edges else "plains"
    return world


def label(text, sub):
    cam = bpy.context.scene.camera
    cam.data.clip_start = 0.1
    mat = bpy.data.materials.new("label")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.02, 0.02, 0.025, 1)
    nt.links.new(em.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
    pale = mat.copy()
    next(n for n in pale.node_tree.nodes if n.type == "EMISSION").inputs["Color"].default_value = (1, 0.98, 0.92, 1)
    for k, (s, y, size) in enumerate(((text, 0.192, 0.026), (sub, 0.162, 0.021))):
        c = bpy.data.curves.new(f"lb{k}", "FONT")
        c.body = s
        c.size = size
        ob = bpy.data.objects.new(f"lb{k}", c)
        c.materials.append(mat)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = cam
        ob.location = (-0.345, y, -1.0)
        ob.visible_shadow = False
    me = bpy.data.meshes.new("lbbg")
    me.from_pydata([(-0.36, 0.15, -1.01), (0.02, 0.15, -1.01), (0.02, 0.225, -1.01), (-0.36, 0.225, -1.01)], [], [(0, 1, 2, 3)])
    me.materials.append(pale)
    ob = bpy.data.objects.new("lbbg", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = cam
    ob.visible_shadow = False


def shot(name, world, stem, sub, dist=30, turn=0.0):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    minis = rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis"))
    rp.build_map(templates, tiles=world)
    col = bpy.data.collections["map"]
    same = [bool(world.get(d)) and vr.terrain_of(world[d]) == st.STARTS[name] for d in N]
    x, y, z = st.stop(name, same)
    ct._mini_spots(col, minis, [((x, y, z + 0.02), math.radians(120))])
    d = bpy.data.materials.get("st_glow")
    if d:
        b = d.node_tree.nodes.get("Principled BSDF")
        b.inputs["Emission Color"].default_value = (*hk.linear("st_glow"), 1.0)
        b.inputs["Emission Strength"].default_value = 1.2
    rp.stage(Vector((0, -0.2, 0.7)), dist, 46)
    scene = bpy.context.scene
    if turn:  # the map camera turned about the tile
        target = Vector((0, -0.2, 0.7))
        rp.look_at(scene.camera, Matrix.Rotation(turn, 3, "Z") @ (scene.camera.location - target) + target, target)
    scene.render.resolution_x, scene.render.resolution_y = 800, 500
    label(TITLES[name], sub)
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


def sheet(rows):
    out_rows = []
    for row in rows:
        cells = []
        for path in row:
            img = bpy.data.images.load(path)
            w, h = img.size
            cells.append(np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4))
            bpy.data.images.remove(img)
        out_rows.append(np.concatenate(cells, axis=1))
    s = np.concatenate(out_rows[::-1], axis=0)
    h, w = s.shape[:2]
    out = bpy.data.images.new("sheet", w, h, alpha=False)
    out.pixels.foreach_set(s.ravel())
    out.filepath_raw = os.path.join(hk.ART, "preview", f"{SHEET_STEM}_v{rp.next_n(SHEET_STEM)}.png")
    out.file_format = "PNG"
    out.save()
    print("SHEET", out.filepath_raw)


if __name__ == "__main__":
    rows = []
    for name in st.STARTS:
        row = [shot(name, {(0, 0): name}, f"start_kit_{name}_alone", "Alone, as it first drops in", 22), shot(name, near_map(name), f"start_kit_{name}_near", "With neighbours", 34)]
        if name == st.MONTO:
            row.append(shot(name, monto_map((0, 3)), f"start_kit_{name}_river", "River straight through", 26))
        else:
            row.append(shot(name, {**near_map(name), **{d: st.STARTS[name] for d in N}}, f"start_kit_{name}_all", "All its own terrain round it", 34))
        rows.append(row)
    rows.append([shot(st.MONTO, monto_map(e), f"start_kit_{st.MONTO}_{s}", t, 26) for e, s, t in (((0, 1), "bend", "River bending past"), ((0, 2, 4), "fork", "Three channels"), ((0, 1, 2), "lake", "Lake on one side"))])
    sheet(rows)
