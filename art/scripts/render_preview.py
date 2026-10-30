"""Renders a small test map from the latest tile kit, picking edge wedges the way the engines will.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_preview.py [-- path/to/tiles_vN.blend]
Writes art/preview/map_preview_vN.png (never overwrites).
"""
import glob
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import hexkit as hk  # noqa: E402

# Pointy-top axial (q, r) -> terrain. Two forests touch, a river runs into a lake, villages join.
MAP = {
    (0, 0): "forest", (1, -1): "forest", (1, 0): "forest",
    (0, -1): "plains", (0, 1): "plains",
    (-1, 0): "village", (-1, -1): "village", (-2, 0): "village",
    (2, -1): "farmland", (2, -2): "farmland", (1, -2): "farmland", (0, -2): "farmland",
    # a lake (four touching tiles) with a river running out of it
    (-2, 1): "river", (-2, 2): "river", (-1, 1): "river", (-1, 2): "river",
    (0, 2): "river", (1, 1): "river", (2, 0): "river",
}


def latest(folder, stem):
    files = glob.glob(os.path.join(hk.ART, folder, f"{stem}_v*.blend"))
    return max(files, key=lambda f: int(re.search(r"_v(\d+)\.blend$", f).group(1)))


def load_templates(path):
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = list(src.objects)
    return {o.name: o for o in dst.objects}


def place(templates, name, col, at, angle=0.0):
    obj = bpy.data.objects.new(name, templates[name].data)
    obj.location = at
    obj.rotation_euler.z = angle
    col.objects.link(obj)


def build_map(templates):
    col = hk.new_collection("map")
    for (q, r), terrain in MAP.items():
        at = hk.tile_position(q, r)
        place(templates, f"base_{terrain}", col, at)
        place(templates, f"{terrain}_centre", col, at)
        for i, (dq, dr) in enumerate(hk.NEIGHBOURS):
            same = MAP.get((q + dq, r + dr)) == terrain
            place(templates, f"{terrain}_edge_{'same' if same else 'other'}", col, at, math.radians(60 * i))
        # Corner pieces (rivers): where the neighbours across edge i and edge i+1 both match.
        if f"{terrain}_corner" in templates:
            for i in range(6):
                pair = [hk.NEIGHBOURS[i], hk.NEIGHBOURS[(i + 1) % 6]]
                if all(MAP.get((q + dq, r + dr)) == terrain for dq, dr in pair):
                    place(templates, f"{terrain}_corner", col, at, math.radians(60 * i))
    # Pale empty slots around the land.
    slots = {(q + dq, r + dr) for (q, r) in MAP for dq, dr in hk.NEIGHBOURS} - set(MAP)
    for q, r in slots:
        p = hk.Piece("slot")
        p.flat([c for c in hk.hex_corners(hk.TILE_RADIUS * 0.94, pointy=True)][::-1], 0.02, "slot")
        p.finish(col, hk.tile_position(q, r) - Vector((0, 0, 0.3)))


def stage(target, distance, elevation_deg, lens=50):
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
    world = bpy.data.worlds.new("backdrop")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = hk.material("backdrop").diffuse_color
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    scene.world = world
    # Camera from the south, tilted down; light from the top left of the view.
    el = math.radians(elevation_deg)
    cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    cam.data.lens = lens
    cam.location = target + Vector((0, -distance * math.cos(el), distance * math.sin(el)))
    cam.rotation_euler = (math.pi / 2 - el, 0, 0)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.5
    sun.data.angle = math.radians(8)
    sun.rotation_euler = (math.radians(45), math.radians(-30), math.radians(-35))
    scene.collection.objects.link(sun)


def render(stem):
    out = os.path.join(hk.ART, "preview")
    os.makedirs(out, exist_ok=True)
    n = 1
    while os.path.exists(os.path.join(out, f"{stem}_v{n}.png")):
        n += 1
    path = os.path.join(out, f"{stem}_v{n}.png")
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path)


def build_board(templates, radius=4):
    """The combat board a map tile grows into: radius 4, 61 flat-top cells, some trees and rocks."""
    col = hk.new_collection("board")
    trees = {(1, -3), (2, -3), (-3, 1), (-2, 2), (3, 0)}
    rocks = {(0, 2), (-1, -1), (2, 1)}
    for q in range(-radius, radius + 1):
        for r in range(max(-radius, -q - radius), min(radius, -q + radius) + 1):
            name = ("cell_tree" if (q, r) in trees else "cell_rock" if (q, r) in rocks
                    else f"cell_grass_{'abc'[(q - r) % 3]}")
            place(templates, name, col, hk.cell_position(q, r))


if __name__ == "__main__":
    # Optional args after --: a tiles .blend, then a combat_cells .blend.
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    tiles = args[0] if args else latest("tiles", "tiles")
    cells = args[1] if len(args) > 1 else latest("combat", "combat_cells")
    hk.empty_scene()
    build_map(load_templates(tiles))
    stage(Vector((0, -2, 0)), 72, 45)
    render("map_preview")
    hk.empty_scene()
    build_board(load_templates(cells))
    stage(Vector((0, -0.4, 0)), 20, 48)
    render("combat_preview")
