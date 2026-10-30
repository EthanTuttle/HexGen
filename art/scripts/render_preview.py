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
import ground_cover as gc  # noqa: E402
import sand  # noqa: E402
import water as wt  # noqa: E402

# Pointy-top axial (q, r) -> terrain. Two forests touch, a river runs into a lake, villages join.
MAP = {
    (0, 0): "forest", (1, -1): "forest", (1, 0): "forest",
    (0, 1): "plains", (-2, 0): "plains",
    (-1, 0): "village", (-1, -1): "village",
    (2, -1): "farmland", (2, -2): "farmland", (1, -2): "farmland", (0, -2): "farmland",
    # a lake (four touching tiles), a river running out of it with a bend, ending in a spring
    (-2, 1): "river", (-2, 2): "river", (-1, 1): "river", (-1, 2): "river",
    (0, 2): "river", (1, 1): "river", (2, 0): "river", (3, 0): "river",
    # a pond: a water tile with no water neighbours
    (0, -1): "river",
}

# Every terrain, keeping the banned pairs apart (design/02 Map & exploration.md -> Placement): a hills range,
# desert by the river, a swamp beside the forest, ruins between hills and plains.
TERRAIN_MAP = {
    (-1, -2): "hills", (0, -2): "hills", (1, -2): "hills", (2, -2): "plains", (3, -2): "desert", (4, -2): "desert",
    (-1, -1): "forest", (0, -1): "hills", (1, -1): "ruins", (2, -1): "plains", (3, -1): "desert",
    (-2, 0): "forest", (-1, 0): "forest", (0, 0): "plains", (1, 0): "ruins", (2, 0): "river",
    (-2, 1): "swamp", (-1, 1): "swamp", (0, 1): "river", (1, 1): "river", (2, 1): "plains",
    (-3, 2): "swamp", (-2, 2): "swamp", (-1, 2): "river", (0, 2): "village", (1, 2): "farmland",
    (3, 0): "hills",  # a lone hills tile, for its own peak
}

# Farms and villages count as joined: the farm track meets the village street, with no border between them.
LINKED = {frozenset(("farmland", "village"))}
BORDERED = {"farmland", "village"}


def linked(a, b):
    return a == b or frozenset((a, b)) in LINKED


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
    return obj


def build_map(templates, animated=False, tiles=None, desert="swells"):
    """Places the test map. With animated=True, water tiles get banks and dressing only and are
    returned as (q, r, position, mask) so the animation can build moving water and bobbing boats.
    desert picks the sand style (sand.STYLES)."""
    MAP = tiles or globals()["MAP"]
    water_tiles = []
    col = hk.new_collection("map")
    for (q, r), terrain in MAP.items():
        at = hk.tile_position(q, r)
        place(templates, f"base_{terrain}", col, at)
        if terrain == "river":
            # Water is drawn per tile from its own water neighbours, the way the engines will.
            mask = [MAP.get((q + dq, r + dr)) == "river" for dq, dr in hk.NEIGHBOURS]
            p = hk.Piece(f"water_{q}_{r}")
            wt.add_water(p, mask, f"{q},{r}", plates=not animated, boats=not animated)
            p.finish(col, at)
            water_tiles.append((q, r, at, mask))
            continue
        place(templates, f"{terrain}_centre", col, at)
        if terrain == "desert":
            # The sand is shaped in world space, the way the engines will.
            p = hk.Piece(f"sand_{q}_{r}")
            sand.add_sand(p, MAP, q, r, desert)
            p.finish(col, at)
        joined = [linked(terrain, MAP.get((q + dq, r + dr))) for dq, dr in hk.NEIGHBOURS]
        if terrain == "hills":
            # One mountain per group: a lone tile's own peak; a third on each corner where three hills tiles
            # meet; otherwise half on each edge shared with one other hills tile.
            triple = [joined[i] and joined[(i + 1) % 6] for i in range(6)]  # corner i: between edges i and i + 1
            if not any(joined):
                place(templates, "hills_peak", col, at)
            for i in range(6):
                if triple[i]:
                    place(templates, "hills_mountain_corner", col, at, math.radians(60 * i))
                elif joined[i] and not triple[(i - 1) % 6]:
                    place(templates, "hills_mountain_edge", col, at, math.radians(60 * i))
        for i in range(6):
            place(templates, f"{terrain}_edge_{'same' if joined[i] else 'other'}", col, at, math.radians(60 * i))
            # Carry a neighbouring edge's border out to this joined edge, so borders run on between tiles.
            if terrain in BORDERED and joined[i] and "border_join_l" in templates:
                if not joined[(i + 1) % 6]:
                    place(templates, "border_join_l", col, at, math.radians(60 * i))
                if not joined[(i - 1) % 6]:
                    place(templates, "border_join_r", col, at, math.radians(60 * i))
    # Small ground cover across the whole map, the way the engines will scatter it.
    p = hk.Piece("ground_cover")
    gc.add_ground_cover(p, MAP)
    p.finish(col)
    # Pale empty slots around the land.
    slots = {(q + dq, r + dr) for (q, r) in MAP for dq, dr in hk.NEIGHBOURS} - set(MAP)
    for q, r in slots:
        p = hk.Piece("slot")
        p.flat([c for c in hk.hex_corners(hk.TILE_RADIUS * 0.94, pointy=True)][::-1], 0.02, "slot")
        p.finish(col, hk.tile_position(q, r) - Vector((0, 0, 0.3)))
    return water_tiles


def stage(target, distance, elevation_deg, lens=50):
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
    # Show colours as authored (Blender's default AgX transform greys flat colours out).
    scene.view_settings.view_transform = "Standard"
    # The pastel backdrop: full strength where the camera sees it, softer as light on the scene.
    world = bpy.data.worlds.new("backdrop")
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    colour = hk.material("backdrop").diffuse_color
    seen, light = nodes["Background"], nodes.new("ShaderNodeBackground")
    seen.inputs["Color"].default_value = light.inputs["Color"].default_value = colour
    seen.inputs["Strength"].default_value, light.inputs["Strength"].default_value = 1.0, 0.5
    mix, path = nodes.new("ShaderNodeMixShader"), nodes.new("ShaderNodeLightPath")
    links.new(path.outputs["Is Camera Ray"], mix.inputs["Fac"])
    links.new(light.outputs["Background"], mix.inputs[1])
    links.new(seen.outputs["Background"], mix.inputs[2])
    links.new(mix.outputs["Shader"], nodes["World Output"].inputs["Surface"])
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
    # --terrains renders TERRAIN_MAP (every terrain) instead, with --desert=swells or --desert=ripples.
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    flags = dict(a[2:].partition("=")[::2] for a in args if a.startswith("--"))
    args = [a for a in args if not a.startswith("--")]
    tiles = args[0] if args else latest("tiles", "tiles")
    cells = args[1] if len(args) > 1 else latest("combat", "combat_cells")
    if "terrains" in flags:
        hk.empty_scene()
        style = flags.get("desert") or "swells"
        build_map(load_templates(tiles), tiles=TERRAIN_MAP, desert=style)
        stage(Vector((4, -1, 0)), 82, 45)
        render(f"terrains_{style}")
        sys.exit(0)
    hk.empty_scene()
    build_map(load_templates(tiles))
    stage(Vector((2, -2, 0)), 74, 45)
    render("map_preview")
    hk.empty_scene()
    build_board(load_templates(cells))
    stage(Vector((0, -0.4, 0)), 20, 48)
    render("combat_preview")
