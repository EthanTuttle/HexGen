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
from mathutils import Matrix, Vector  # noqa: E402

import hexkit as hk  # noqa: E402
import ground_cover as gc  # noqa: E402
import landmark_flow as lf  # noqa: E402
import massif  # noqa: E402
import build_tiles as bt  # noqa: E402
import fence_gates as fg  # noqa: E402
import json  # noqa: E402
import sand  # noqa: E402
import variants as vr  # noqa: E402
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

# The same map with every region finished: each tile shows its terrain's tier 1 variant.
TIER1 = {"forest": "deep_forest", "plains": "meadows", "hills": "highlands", "farmland": "windmill_country",
         "village": "market_town", "river": "delta", "swamp": "bog", "desert": "wasteland", "ruins": "excavation"}
VARIANT_MAP = {k: TIER1[t] for k, t in TERRAIN_MAP.items()}

# Forest tier 2: plain forest in the middle, ringed by finished deep forest, fey wood, dark wood and heartwood
# regions, so every pair of forest looks shares an edge somewhere; plains round part of it for the outer edges.
FOREST_T2_MAP = {
    (0, 0): "forest", (1, -2): "forest",
    (1, 0): "deep_forest", (1, -1): "deep_forest", (2, -1): "deep_forest", (-2, 0): "deep_forest",
    (0, -1): "fey_wood", (-1, 0): "fey_wood", (-1, -1): "fey_wood",
    (-1, 1): "dark_wood", (-2, 1): "dark_wood", (-2, 2): "dark_wood",
    (0, 1): "heartwood", (1, 1): "heartwood", (0, 2): "heartwood", (0, -2): "heartwood",
    (2, 0): "plains", (2, 1): "plains", (-1, 2): "plains", (1, 2): "plains", (-3, 2): "plains", (-3, 1): "plains",
}
FOREST_T2_CLOSEUPS = {"fey_wood": [(0, -1), (-1, 0), (-1, -1)], "dark_wood": [(-1, 1), (-2, 1), (-2, 2)],
                      "heartwood": [(0, 1), (1, 1), (0, 2)]}

# The Tree of Life in a heartwood group: four heartwood neighbours (four paths), one plain forest and one
# plains neighbour (roots ending before the edge), and a lone hills tile beyond to compare its height.
TREEOFLIFE_MAP = {
    (0, 0): "treeoflife",
    (1, 0): "heartwood", (1, -1): "heartwood", (0, 1): "heartwood", (-1, 1): "heartwood", (1, 1): "heartwood",
    (-1, 0): "forest", (0, -1): "plains", (-1, -1): "plains", (-2, 1): "plains", (-1, 2): "plains",
    (0, 2): "plains", (2, -1): "plains", (2, -2): "hills", (2, 0): "plains", (1, -2): "plains",
}

# The forest tier 2 map with a landmark in each tier 2 group: the Hidden Shrine among deep forest, the Fey
# Court in fey wood, the Spider Nest in dark wood (the Tree of Life has its own map above).
LANDMARK_MAP = {**FOREST_T2_MAP, (1, -1): "hiddenshrine", (-1, 0): "feycourt", (-2, 1): "spidernest"}

# Each forest variant's 7-tile region with its landmark on an outer tile, so the trails show, ringed by plains
# and a little plain forest.
LANDMARK_REGION = [(0, 0), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
LANDMARK_AT = (1, -1)
FLOW_RING = {(2, -2): "plains", (2, -1): "plains", (2, 0): "forest", (1, 1): "plains", (0, 2): "plains",
             (-1, 2): "plains", (-2, 2): "forest", (-2, 1): "plains", (-2, 0): "plains", (-1, -1): "forest",
             (0, -2): "plains", (1, -2): "plains"}
FLOW_MAPS = {v: {**FLOW_RING, **{t: (lm if t == LANDMARK_AT else v) for t in LANDMARK_REGION}}
             for v, lm in (("heartwood", "treeoflife"), ("fey_wood", "feycourt"), ("dark_wood", "spidernest"),
                           ("deep_forest", "hiddenshrine"))}

# Farmland: a farm group with a village beside it, a river along one side (no gates open onto water) and other
# land round it, so the gates show; and a windmill country region with the Great Windmill on an outer tile.
FARM_MAP = {
    (0, 0): "farmland", (1, 0): "farmland", (0, 1): "farmland", (-1, 1): "farmland", (1, -1): "farmland",
    (-1, 0): "village", (0, -1): "village",
    (2, -1): "plains", (2, 0): "plains", (1, 1): "forest", (0, 2): "plains", (-1, 2): "river", (-2, 2): "river",
    (-2, 1): "river", (-2, 0): "plains", (-1, -1): "forest", (1, -2): "plains", (0, -2): "plains", (2, -2): "plains",
}
WINDMILL_MAP = {**{k: v for k, v in FLOW_RING.items()},
                **{t: ("greatwindmill" if t == LANDMARK_AT else "windmill_country") for t in LANDMARK_REGION}}


LIFT_POINT = lambda at: 0.0  # noqa: E731  # set by apply_massif, so overlays rise with the pieces


def draw_effects(col, templates):
    """Stand-ins for the engine's effects at each placed piece's effect points: a fire (orange cone), smoke (a
    grey column) or circling crows (black specks), so a preview shows where they go."""
    bpy.context.view_layer.update()
    p = hk.Piece("effects_overlay")
    for obj in list(col.objects):
        src = templates.get(obj.get("piece", ""))
        if src is None or "effects" not in src:
            continue
        for e in json.loads(src["effects"]):
            x, y, z = e["at"]
            at = obj.matrix_world @ Vector((x, -z * obj.get("tower", 1.0), y))
            at.z += LIFT_POINT(at)
            if e["kind"] == "crackle":
                for k in range(4):
                    a_ = 2 * math.pi * k / 4
                    p.box(at + Vector((math.cos(a_) * 0.2, math.sin(a_) * 0.2, 0.15 * k)), (0.07, 0.07, 0.07), "ember")
            elif e["kind"] == "fire":
                p.cone(at, 0.14, 0.32, "ember", segments=5)
            elif e["kind"] == "smoke":
                for k in range(4):
                    p.blob(at + Vector((0.08 * k, 0.05 * k, 0)), 0.16 + 0.05 * k, "rock_light", z=0.4 + 0.42 * k)
            else:
                for k in range(5):
                    a_ = 2 * math.pi * k / 5
                    p.box(at + Vector((math.cos(a_) * 0.5, math.sin(a_) * 0.5, 0.1 * k)), (0.14, 0.04, 0.02), "crow")
    p.finish(col)


def lifted_line(line, step=0.5):
    """A polyline with the massif lift added, sampled finely enough to follow the lift's creases."""
    out = []
    for a, b in zip(line, line[1:]):
        n = max(1, math.ceil((b - a).length / step))
        out += [a.lerp(b, k / n) for k in range(n)]
    out.append(line[-1])
    return [q + Vector((0, 0, LIFT_POINT(q))) for q in out]


def draw_paths(col, templates):
    """Draws every placed piece's path centrelines (and hub spokes) as thin red strips, to check the routing data."""
    bpy.context.view_layer.update()  # so the placed objects' matrix_world is current
    p = hk.Piece("paths_overlay")
    tiles = {}
    for obj in list(col.objects):
        src = templates.get(obj.get("piece", ""))
        if src is None:
            continue
        m = obj.matrix_world
        lines = [lifted_line([m @ Vector((x, -z, y)) for x, y, z in line]) for line in json.loads(src.get("paths", "[]"))]
        for line in lines:
            for a, b in zip(line, line[1:]):
                d = b - a
                vr.frustum(p, a + Vector((0, 0, 0.14)), b + Vector((0, 0, 0.14)), 0.05, 0.05, "path_debug", segments=4)
        key = (round(m.translation.x, 1), round(m.translation.y, 1))
        for i, line in json.loads(src.get("path_spokes", "{}")).items():
            tiles.setdefault(key, {}).setdefault("spokes", []).append((int(i), lifted_line([m @ Vector((x, -z, y)) for x, y, z in line])))
        if "path_hub" in src:
            x, y, z = json.loads(src["path_hub"])
            hub = m @ Vector((x, -z, y))
            tiles.setdefault(key, {})["hub"] = hub + Vector((0, 0, LIFT_POINT(hub)))
        tiles.setdefault(key, {}).setdefault("ends", []).extend(l[0] for l in lines)
    for t in tiles.values():  # spokes, only where a wedge path ends at the spoke's outer end
        for i, line in t.get("spokes", []):
            if any((e - line[0]).length < 0.05 for e in t.get("ends", [])):
                for a, b in zip(line, line[1:]):
                    vr.frustum(p, a + Vector((0, 0, 0.14)), b + Vector((0, 0, 0.14)), 0.05, 0.05, "path_debug", segments=4)
        for e in t.get("ends", []) if "hub" in t else []:
            d = e - t["hub"]
            if d.length < 2.6:  # a wedge path's inner end on this tile
                vr.frustum(p, e + Vector((0, 0, 0.14)), t["hub"] + Vector((0, 0, 0.14)), 0.05, 0.05, "path_debug", segments=4)
    p.finish(col)

# Plains tier 0: a group of plains among forest, farms, a village and hills, to judge it beside full tiles.
PLAINS_MAP = {**{t: "plains" for t in LANDMARK_REGION},
              (2, -2): "forest", (2, -1): "forest", (2, 0): "plains", (1, 1): "farmland", (0, 2): "farmland",
              (-1, 2): "farmland", (-2, 2): "village", (-2, 1): "plains", (-2, 0): "plains", (-1, -1): "hills",
              (0, -2): "hills", (1, -2): "plains"}
# A bigger region, so density flows show all their bands: far corner three steps from the landmark and more.
DENSITY_REGION = LANDMARK_REGION + [(1, 1), (0, 2), (-1, 2), (-2, 2), (-2, 1)]


DENSITY_VIEW = sum((hk.tile_position(*t) for t in DENSITY_REGION), Vector()) / len(DENSITY_REGION)


def density_map(variant, landmark):
    return {**FLOW_RING, **{t: (landmark if t == LANDMARK_AT else variant) for t in DENSITY_REGION}}


MEADOWS_MAP = density_map("meadows", "nomadcamp")

# Hills tier 0 beside full forests and farms: a group, a pair and a lone tile.
HILLS_MAP = {(-1, 0): "hills", (0, 0): "hills", (0, -1): "hills", (-1, 1): "hills", (1, 0): "hills", (0, 1): "hills",
             (2, -1): "plains", (1, -1): "forest", (-1, -1): "forest", (-2, 1): "plains", (-2, 0): "plains",
             (-1, 2): "farmland", (0, 2): "farmland", (1, 1): "plains", (2, 0): "hills", (2, 1): "hills",
             (3, -1): "plains", (3, 0): "plains", (1, 2): "farmland", (0, -2): "plains", (1, -2): "hills"}
HIGHLANDS_MAP = {**FLOW_RING, **{t: ("clanhall" if t == LANDMARK_AT else "highlands") for t in LANDMARK_REGION}}

# Farmland tier 2: each variant's 7-tile region with its landmark on an outer tile, ringed by plains and forest.
FARM_T2_MAPS = {v: {**FLOW_RING, **{t: (lm if t == LANDMARK_AT else v) for t in LANDMARK_REGION}}
                for v, lm in (("haunted_homesteads", "abandonedbarn"), ("raided_farms", "militiabarn"),
                              ("cider_orchards", "harvestfestival"))}

# Farms and villages count as joined: the farm track meets the village street, with no border between them.
LINKED = {frozenset(("farmland", "village"))}
BORDERED = {"farmland", "village"}


def linked(a, b):
    """Joined for edge pieces: the same terrain (a region variant counts as its terrain), or linked terrains."""
    if b and vr.wedges_of(a) != vr.wedges_of(b) and (vr.wedges_of(a) in massif.MASSIF or vr.wedges_of(b) in massif.MASSIF):
        return False  # a region that rises inward ends at ground level on every side, even against other hills
    a, b = vr.terrain_of(a), vr.terrain_of(b) if b else b
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
    obj["piece"] = name  # which kit piece it is, for draw_paths
    obj.location = at
    obj.rotation_euler.z = angle
    col.objects.link(obj)
    return obj


def build_map(templates, animated=False, tiles=None):
    """Places the test map. With animated=True, water tiles get banks and dressing only and are
    returned as (q, r, position, mask) so the animation can build moving water and bobbing boats."""
    MAP = tiles or globals()["MAP"]
    water_tiles = []
    col = hk.new_collection("map")
    # Landmark flow (landmark_flow.py): each landmark's region is its variant's tiles joined to it. In the game
    # the region is known; here it's the connected group of the variant's tiles round the landmark.
    dist, toward, turns = {}, {}, {}
    for lm_at, lm in MAP.items():
        if lm in vr.LANDMARKS:
            region, todo = {lm_at}, [lm_at]
            while todo:
                q, r = todo.pop()
                for dq, dr in hk.NEIGHBOURS:
                    n = (q + dq, r + dr)
                    if n not in region and MAP.get(n) == vr.LANDMARKS[lm]:
                        region.add(n)
                        todo.append(n)
            d, t = lf.flow(region, lm_at)
            dist.update(d)
            toward.update(t)
            turns[lm_at] = lf.turn(lm_at, d, t)  # the landmark's entrance faces its longest trail
    # Fence gates round farm and village groups (fence_gates.py).
    gates = fg.fence_gates({k: vr.terrain_of(n) for k, n in MAP.items()})
    for (q, r), name in MAP.items():
        # name is a terrain or a region variant (variants.py); the variant's pieces carry its name, and
        # edge pieces are picked by its terrain.
        terrain = vr.terrain_of(name)
        at = hk.tile_position(q, r)
        base = place(templates, f"base_{terrain}", col, at)
        kit = vr.wedges_of(name)  # a centre-only landmark takes its variant's wedges and ground colour
        if kit in vr.VARIANTS:
            # Variants use their terrain's base with their own ground colour on top (slot 0 is the top).
            base.material_slots[0].link = "OBJECT"
            base.material_slots[0].material = hk.material(vr.VARIANTS[kit][2])
        if terrain == "river":
            # Water is drawn per tile from its own water neighbours, the way the engines will.
            near = [MAP.get((q + dq, r + dr)) for dq, dr in hk.NEIGHBOURS]
            mask = [vr.terrain_of(n) == "river" if n else False for n in near]
            p = hk.Piece(f"water_{q}_{r}")
            wt.add_water(p, mask, f"{q},{r}", plates=not animated, boats=not animated,
                         widths=wt.edge_widths(name, near), delta=name == "delta")
            p.finish(col, at)
            water_tiles.append((q, r, at, mask))
            continue
        centre = "centre"
        if dist.get((q, r)) == 1 and f"{name}_centre_near" in templates:
            centre = "centre_near"  # next to the landmark: the variant's look played up
        elif dist.get((q, r)) == 2 and f"{name}_centre_mid" in templates:
            centre = "centre_mid"  # two steps from the landmark: on the way to it
        if centre == "centre" and f"{name}_centre_b" in templates and gc.hash01(q, r, 13) < 0.5:
            centre = "centre_b"  # a second version of the centre, so a big group doesn't repeat
        if f"{name}_centre_mill" in templates and gc.hash01(q, r, 7) < 0.5:
            centre = "centre_mill"  # windmills stand on about half the tiles (placeholder rule)
        spin = math.radians(60 * turns.get((q, r), 0))
        if f"{name}_centre_b" in templates:  # a farm's centre turns by a hash of the tile, so yards don't line up
            spin = math.radians(60 * int(gc.hash01(q * 31 + 7, r * 17 + 3, 14) * 6))
        if centre in ("centre_mid", "centre_near") and f"{name}_centre_mid" in templates:
            spin = math.radians(60 * lf.toward_edge((q, r), toward))  # density bands lean toward the landmark
        place(templates, f"{name}_{centre}", col, at, spin)
        if centre == "centre_mill":  # the small mill goes where the turned yard is, but doesn't turn itself
            place(templates, "windmill_small", col, at + Matrix.Rotation(spin, 3, "Z") @ vr.SMALL_MILL_SPOT)
        for part, (_, hub) in vr.LANDMARK_PARTS.items():  # e.g. the Great Windmill's sails, turned with it
            if part.startswith(f"{name}_"):
                place(templates, part, col, at + Matrix.Rotation(spin, 3, "Z") @ hub, spin)
        if terrain == "desert":
            # The sand is shaped in world space, the way the engines will.
            p = hk.Piece(f"sand_{q}_{r}")
            sand.add_sand(p, MAP, q, r)
            p.finish(col, at)
        joined = [linked(name, MAP.get((q + dq, r + dr))) for dq, dr in hk.NEIGHBOURS]
        trails = lf.trail_edges((q, r), toward)
        if terrain == "hills":
            # One mountain per group: a lone tile's own peak; a third on each corner where three hills tiles
            # meet; otherwise half on each edge shared with one other hills tile.
            # A landmark has none of this, and its neighbours leave it out, so it keeps clear ground.
            # No mountain on a trail edge either: the range opens into a pass along the way to the landmark.
            def ranges(t, i):  # do tile t and its neighbour on edge i share a mountain?
                n = (t[0] + hk.NEIGHBOURS[i][0], t[1] + hk.NEIGHBOURS[i][1])
                return (linked(MAP[t], MAP.get(n)) and i not in lf.trail_edges(t, toward)
                        and MAP[t] not in vr.LANDMARKS and MAP.get(n) not in vr.LANDMARKS)
            ranged = [ranges((q, r), i) for i in range(6)]

            def corner_shared(i):  # all three tiles round corner i must share: every copy of the third must be drawn
                n = (q + hk.NEIGHBOURS[i][0], r + hk.NEIGHBOURS[i][1])
                return ranged[i] and ranged[(i + 1) % 6] and ranges(n, (i + 2) % 6)
            triple = [corner_shared(i) for i in range(6)]  # corner i: between edges i and i + 1
            if name in vr.LANDMARKS:
                ranged = triple = [False] * 6
            elif not any(ranged) and dist.get((q, r), 3) > 2:
                place(templates, f"{name}_peak", col, at)
            parts = []
            for i in range(6):
                if triple[i]:
                    parts.append(("corner", i))
                elif ranged[i] and not triple[(i - 1) % 6]:
                    parts.append(("edge", i))
            for where, i in parts:
                place(templates, f"{name}_mountain_{where}", col, at, math.radians(60 * i))
            # In bigger groups the mountains join into a range: ridges from this tile's middle to each of them.
            # None within two steps of a landmark (clear ground), nor where steps run (they'd bury them).
            if len(parts) >= 2 and dist.get((q, r), 3) > 2 and f"{kit}_steps_centre" not in templates:
                place(templates, f"{name}_ridge_knot", col, at)
                for where, i in parts:
                    place(templates, f"{name}_ridge_{where}", col, at, math.radians(60 * i))
        for i in range(6):
            edge = f"{kit}_edge_{'same' if joined[i] else 'other'}"
            near = MAP.get((q + hk.NEIGHBOURS[i][0], r + hk.NEIGHBOURS[i][1]))
            if vr.LANDMARKS.get(near) == name and f"{name}_edge_landmark" in templates:
                edge = f"{name}_edge_landmark"  # a variant's edge toward its landmark: its look carries on
            elif i in trails and (f"{name}_edge_trail" in templates or f"{kit}_edge_trail" in templates):  # a trail toward the landmark: the landmark's own trail piece, or its kit's
                edge = f"{name}_edge_trail" if f"{name}_edge_trail" in templates else f"{kit}_edge_trail"
                if lf.heads_in((q, r), i, dist) and f"{kit}_edge_trail_in" in templates:
                    edge = f"{kit}_edge_trail_in"  # the closer tile's side: carts heading in, toward the mill
            elif not joined[i] and i in gates.get((q, r), ()) and f"{kit}_edge_gate" in templates:
                edge = f"{kit}_edge_gate"  # a gate in the fence, the track running out through it
            elif not joined[i] and f"{kit}_edge_other_b" in templates and gc.hash01(q * 6 + i, r, 8) < 0.5:
                edge = f"{kit}_edge_other_b"  # trees: a wedge facing other land is the only one clear of rock
            elif not joined[i] and name in vr.LANDMARKS and f"{kit}_edge_other_lm" in templates:
                edge = f"{kit}_edge_other_lm"  # the fence wedge without the lane fill: the landmark's yard lies there
            elif joined[i] and f"{kit}_edge_same_b" in templates and gc.hash01(q * 6 + i, r, 8) < 0.5:
                edge = f"{kit}_edge_same_b"  # a second edge_same piece, alternated so the edges don't repeat
            place(templates, edge, col, at, math.radians(60 * i))
            if i in trails and f"{kit}_steps_centre" in templates:  # the stair's flight on the centre, one per trail edge
                if name not in vr.LANDMARKS:
                    place(templates, f"{kit}_steps_centre", col, at, math.radians(60 * i))
                elif i != turns.get((q, r)):  # the entrance edge's steps are in the landmark's own piece
                    place(templates, f"{kit}_steps_rise", col, at, math.radians(60 * i))
            # Carry a neighbouring edge's border out to this joined edge, so borders run on between tiles.
            if terrain in BORDERED and joined[i] and "border_join_l" in templates:
                if not joined[(i + 1) % 6]:
                    place(templates, "border_join_l", col, at, math.radians(60 * i))
                if not joined[(i - 1) % 6]:
                    place(templates, "border_join_r", col, at, math.radians(60 * i))
    # Small ground cover across the whole map, the way the engines will scatter it.
    # Circles the pieces keep the ground cover off (burns, yards), in world space.
    bpy.context.view_layer.update()
    clear = []
    for obj in col.objects:
        src = templates.get(obj.get("piece", ""))
        if src is not None and "no_cover" in src:
            for c in json.loads(src["no_cover"]):
                x, y, z = c["at"]
                w = obj.matrix_world @ Vector((x, -z, y))
                clear.append((w.x, w.y, c["r"]))
    p = hk.Piece("ground_cover")
    gc.add_ground_cover(p, MAP, clear)
    p.finish(col)
    # Pale empty slots around the land.
    slots = {(q + dq, r + dr) for (q, r) in MAP for dq, dr in hk.NEIGHBOURS} - set(MAP)
    for q, r in slots:
        p = hk.Piece("slot")
        p.flat([c for c in hk.hex_corners(hk.TILE_RADIUS * 0.94, pointy=True)][::-1], 0.02, "slot")
        p.finish(col, hk.tile_position(q, r) - Vector((0, 0, 0.3)))
    return water_tiles


def apply_massif(col, region, landmark, scale=1.0, tower=massif.TOWER):
    """The engine's massif lift (massif.py) on the placed map: every vertex of every piece moves up with the ground,
    mountains and ridges also grow taller. Each placed piece gets its own copy of the mesh, as the engine would bake."""
    global LIFT_POINT
    bpy.context.view_layer.update()
    lifts = massif.region_lifts(region, scale)
    centres = {t: hk.tile_position(*t) for t in region}

    def point(at):
        for t, c in centres.items():
            x, y = at.x - c.x, at.y - c.y
            if max(x * hk.edge_normal(i).x + y * hk.edge_normal(i).y for i in range(6)) <= hk.TILE_APOTHEM + 1e-4:
                return massif.lift_at(lifts[t], x, y, flat=t == landmark)
        return 0.0
    LIFT_POINT = point
    kinds = ("mountain_edge", "mountain_corner", "peak", "ridge_edge", "ridge_corner", "ridge_knot")
    for obj in list(col.objects):
        if obj.type != "MESH":
            continue
        m, inv = obj.matrix_world.copy(), obj.matrix_world.inverted()
        tall = 1.0
        kind = next((k for k in kinds if obj.get("piece", "").endswith("_" + k)), None)
        if kind:
            t = min(centres, key=lambda c: (centres[c] - obj.location).length)
            if (centres[t] - obj.location).length < 0.1:
                tall = massif.tower_of(lifts[t], kind, round(math.degrees(obj.rotation_euler.z) / 60) % 6, tower)
        obj["tower"] = tall
        mesh = obj.data.copy()
        for v in mesh.vertices:
            w = m @ v.co
            w.z = w.z * tall + point(w)
            v.co = inv @ w
        mesh.update()
        obj.data = mesh


def slope_report(col, label):
    """Walking ground only (each variant's own ground material), by kind of piece: the share by area steeper than the
    minis' 28 degrees, and the worst face."""
    grounds = {"highland_grass", "snow_ground", "ash_ground", "hill_grass"}
    stats = {}
    for obj in col.objects:
        piece = obj.get("piece", "") if obj.type == "MESH" else ""
        kind = "centre" if "_centre" in piece else "same" if "_edge_same" in piece else "other" if "_edge_other" in piece else "trail" if "_edge_trail" in piece else None
        if not kind:
            continue
        s_ = stats.setdefault(("landmark " if piece.split("_centre")[0] in vr.LANDMARK_CENTRES else "") + kind, [0.0, 0.0, 0.0])
        for poly in obj.data.polygons:
            if obj.data.materials[poly.material_index].name not in grounds:
                continue
            a = math.degrees(math.acos(min(1.0, abs(poly.normal.z))))
            s_[0] += poly.area
            s_[1] += poly.area if a > 28 else 0.0
            s_[2] = max(s_[2], a)
    print(f"SLOPES {label}: " + ", ".join(f"{k} {100 * v[1] / max(v[0], 1e-6):.0f}% over, worst {v[2]:.0f}" for k, v in sorted(stats.items())))


def route_report(region, lm_at, label):
    """Straight along each trail: tile middle to edge midpoint to the next tile's middle, on the kit's ground plus the lift."""
    d, tw = lf.flow(set(region), lm_at)
    worst = 0.0
    with vr.low_ground():
        for t in region:
            c = hk.tile_position(*t)
            for i in lf.trail_edges(t, tw):
                n = hk.edge_normal(i)
                zs = []
                for k in range(0, 21):
                    x = hk.TILE_APOTHEM * k / 20
                    ground = bt.hill_height(x, 0, "same" if x > bt.X0 else "centre")
                    zs.append(ground + LIFT_POINT(c + n * x))
                for a, b in zip(zs, zs[1:]):
                    worst = max(worst, math.degrees(math.atan(abs(b - a) / (hk.TILE_APOTHEM / 20))))
    print(f"ROUTE {label}: steepest along a trail {worst:.1f} deg")


def top_height(col, label):
    best = max(((obj.matrix_world @ v.co).z, obj.get("piece", obj.name)) for obj in col.objects if obj.type == "MESH" for v in obj.data.vertices)
    print(f"TALLEST {label}: {best[0]:.2f} on {best[1]}")


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


def next_n(stem):
    out = os.path.join(hk.ART, "preview")
    n = 1
    while glob.glob(os.path.join(out, f"{stem}_v{n}.png")) + glob.glob(os.path.join(out, f"{stem}_v{n}[a-z].png")):
        n += 1
    return n


def render(stem):
    """Renders to preview/<stem>_vN.png, N the first version not taken (counting lettered options too)."""
    out = os.path.join(hk.ART, "preview")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"{stem}_v{next_n(stem)}.png")
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
    # --terrains renders TERRAIN_MAP (every terrain) instead; --variants renders it with every region finished;
    # --forest-t2 renders FOREST_T2_MAP and a close-up of each forest tier 2 variant; --treeoflife renders
    # TREEOFLIFE_MAP and a close-up of the Tree of Life; --landmarks a close-up of the Hidden Shrine,
    # the Fey Court and the Spider Nest; --flow each forest variant's region flowing into its landmark;
    # --farmland the farm gates, the path data and the windmill country region with the Great Windmill;
    # --markettown-gates the farm map with market towns, to show their gates; --farmland-t2 the farmland tier 2
    # regions and their landmarks; --plains plains tier 0 options and meadows with the Nomad Camp.
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    flags = dict(a[2:].partition("=")[::2] for a in args if a.startswith("--"))
    args = [a for a in args if not a.startswith("--")]
    tiles = args[0] if args else latest("tiles", "tiles")
    cells = args[1] if len(args) > 1 else latest("combat", "combat_cells")
    if "variants" in flags:
        hk.empty_scene()
        build_map(load_templates(tiles), tiles=VARIANT_MAP)
        stage(Vector((4, -1, 0)), 82, 45)
        render("variants")
        sys.exit(0)
    if "forest-t2" in flags:
        # The forest tier 2 map, then a close-up of each variant's region and its neighbours.
        hk.empty_scene()
        build_map(load_templates(tiles), tiles=FOREST_T2_MAP)
        stage(Vector((-0.5, -1, 0)), 66, 45)
        render("forest_t2")
        cam = bpy.context.scene.camera
        for variant, group in FOREST_T2_CLOSEUPS.items():
            target = sum((hk.tile_position(q, r) for q, r in group), Vector()) / len(group)
            el = math.radians(40)
            cam.location = target + Vector((0, -24 * math.cos(el), 24 * math.sin(el)))
            cam.rotation_euler = (math.pi / 2 - el, 0, 0)
            render(f"closeup_{variant}")
        sys.exit(0)
    if "treeoflife" in flags:
        # The Tree of Life landmark in a heartwood group, then a close-up of it.
        hk.empty_scene()
        build_map(load_templates(tiles), tiles=TREEOFLIFE_MAP)
        stage(Vector((0.5, -0.5, 0)), 52, 45)
        render("treeoflife")
        cam = bpy.context.scene.camera
        el = math.radians(38)
        cam.location = Vector((0, 0, 0.8)) + Vector((0, -20 * math.cos(el), 20 * math.sin(el)))
        cam.rotation_euler = (math.pi / 2 - el, 0, 0)
        render("closeup_treeoflife")
        sys.exit(0)
    if "landmarks" in flags:
        # A close-up of each landmark on LANDMARK_MAP, in its own variant's group.
        hk.empty_scene()
        build_map(load_templates(tiles), tiles=LANDMARK_MAP)
        stage(Vector((-0.5, -1, 0)), 66, 45)
        cam = bpy.context.scene.camera
        el = math.radians(40)
        for (q, r), name in LANDMARK_MAP.items():
            if name in vr.LANDMARKS:
                cam.location = hk.tile_position(q, r) + Vector((0, -15 * math.cos(el), 0.6 + 15 * math.sin(el)))
                cam.rotation_euler = (math.pi / 2 - el, 0, 0)
                render(f"closeup_{name}")
        sys.exit(0)
    if "flow" in flags:
        # Each forest variant's region flowing into its landmark, then a close-up of the landmark.
        for variant, tiles_map in FLOW_MAPS.items():
            hk.empty_scene()
            build_map(load_templates(tiles), tiles=tiles_map)
            stage(Vector((1.5, -1.0, 0)), 50, 50)
            render(f"{variant}_landmark")
            cam = bpy.context.scene.camera
            el = math.radians(40)
            at = hk.tile_position(*LANDMARK_AT)
            # looking at the entrance, which the landmark turns to face its longest trail
            region = [t for t, n in tiles_map.items() if n in (variant, tiles_map[LANDMARK_AT])]
            d, t = lf.flow(set(region), LANDMARK_AT)
            a = math.radians(60 * lf.turn(LANDMARK_AT, d, t))
            cam.location = at + Vector((17 * math.cos(el) * math.cos(a), 17 * math.cos(el) * math.sin(a),
                                        0.8 + 17 * math.sin(el)))
            cam.rotation_euler = (math.pi / 2 - el, 0, a + math.pi / 2)
            render(f"closeup_{tiles_map[LANDMARK_AT]}_landmark")
        sys.exit(0)
    if "plains" in flags:
        # Plains tier 0 as it is and with each option, then meadows flowing into the Nomad Camp, and a close-up.
        def plains_map(tiles_map, stem, paths=False, dist=62, el=50):
            hk.empty_scene()
            templates = load_templates(tiles)
            build_map(templates, tiles=tiles_map)
            col = bpy.data.collections["map"]
            draw_effects(col, templates)
            if paths:
                draw_paths(col, templates)
            stage(DENSITY_VIEW, dist, el)
            render(stem)
        plains_map(MEADOWS_MAP, "plains_meadows_landmark")
        region = [t for t, n in MEADOWS_MAP.items() if n in ("meadows", "nomadcamp")]
        d, tw = lf.flow(set(region), LANDMARK_AT)
        a = math.radians(60 * lf.turn(LANDMARK_AT, d, tw))
        el = math.radians(40)
        cam = bpy.context.scene.camera
        cam.location = hk.tile_position(*LANDMARK_AT) + Vector((15 * math.cos(el) * math.cos(a),
                                                                15 * math.cos(el) * math.sin(a), 1 + 15 * math.sin(el)))
        cam.rotation_euler = (math.pi / 2 - el, 0, a + math.pi / 2)
        render("plains_nomadcamp_closeup")
        sys.exit(0)
    if "plains-t2" in flags:
        # Plains tier 2 and class variant: each region flowing into its landmark, its path data, and a close-up.
        el = math.radians(40)
        for short, variant, lm, with_paths in (("steppe", "battlefield", "oldbattlefield", False),
                                               ("stormy", "stormy_plains", "thunderbirdnest", False),
                                               ("tourney", "tourney_fields", "traininggrounds", False)):
            tiles_map = density_map(variant, lm)
            for paths in ((True, False) if with_paths else (False,)):
                hk.empty_scene()
                templates = load_templates(tiles)
                build_map(templates, tiles=tiles_map)
                col = bpy.data.collections["map"]
                draw_effects(col, templates)
                if paths:
                    draw_paths(col, templates)
                stage(DENSITY_VIEW, 62, 55 if paths else 50)
                render(f"plains_t2_{short}_{'paths' if paths else 'landmark'}")
            d, tw = lf.flow(set(t for t, n in tiles_map.items() if n in (variant, lm)), LANDMARK_AT)
            a = math.radians(60 * lf.turn(LANDMARK_AT, d, tw))
            cam = bpy.context.scene.camera
            cam.location = hk.tile_position(*LANDMARK_AT) + Vector((16 * math.cos(el) * math.cos(a), 16 * math.cos(el) * math.sin(a),
                                                                    1.2 + 16 * math.sin(el)))
            cam.rotation_euler = (math.pi / 2 - el, 0, a + math.pi / 2)
            render(f"plains_t2_{lm}_closeup")
        sys.exit(0)
    if "tourney-stations" in flags:
        # Close-ups of the tourney stations: each centre piece alone on its base, unturned.
        el = math.radians(42)
        for piece in ("centre", "centre_b", "centre_mid", "centre_near"):
            hk.empty_scene()
            templates = load_templates(tiles)
            col = hk.new_collection("map")
            base = place(templates, "base_plains", col, Vector((0, 0, 0)))
            base.material_slots[0].link = "OBJECT"
            base.material_slots[0].material = hk.material("mown")
            place(templates, f"tourney_fields_{piece}", col, Vector((0, 0, 0)))
            stage(Vector((0, 0, 0)), 15, 42)
            render(f"plains_t2_tourney_stations_{piece}")
        sys.exit(0)
    if "hills" in flags:
        # Hills tier 0 beside full tiles, then highlands flowing into the Clan Hall, with a close-up.
        def hills_map(tiles_map, stem, target, paths=False):
            hk.empty_scene()
            templates = load_templates(tiles)
            build_map(templates, tiles=tiles_map)
            col = bpy.data.collections["map"]
            draw_effects(col, templates)
            if paths:
                draw_paths(col, templates)
            stage(target, 54, 50)
            render(stem)
        hills_map(HILLS_MAP, "hills_t0", Vector((3, 0, 0)))
        hills_map(HIGHLANDS_MAP, "hills_highlands_landmark", Vector((0.5, -0.8, 0)))
        region = [t for t, n in HIGHLANDS_MAP.items() if n in ("highlands", "clanhall")]
        d, tw = lf.flow(set(region), LANDMARK_AT)
        a = math.radians(60 * lf.turn(LANDMARK_AT, d, tw))
        el = math.radians(38)
        cam = bpy.context.scene.camera
        cam.location = hk.tile_position(*LANDMARK_AT) + Vector((16 * math.cos(el) * math.cos(a), 16 * math.cos(el) * math.sin(a),
                                                                2.2 + 16 * math.sin(el)))
        cam.rotation_euler = (math.pi / 2 - el, 0, a + math.pi / 2)
        render("hills_clanhall_closeup")
        sys.exit(0)
    if "height" in flags:
        # Hills variants rising inward (massif.py): a 7-tile and a 12-tile region of each, the landmark inward and on an
        # outer tile. --lift and --tower try other values; --only picks a variant; --trial renders under a scratch name.
        scale, tower = float(flags.get("lift") or 1.0), float(flags.get("tower") or massif.TOWER)
        prefix = "trial_" if "trial" in flags else ""
        el = math.radians(38)
        for short, variant, lm in (("highlands", "highlands", "clanhall"), ("snowy", "snowy_peaks", "yeticave"),
                                   ("volcanic", "volcanic_peaks", "salamanderden"), ("monastery", "monastery_heights", "library")):
            if flags.get("only") and short not in flags["only"].split(","):
                continue
            for size, region, lm_at, view, dist_ in (("7", LANDMARK_REGION, (0, 0), Vector((0.5, -0.8, 1.5)), 54),
                                                     ("7out", LANDMARK_REGION, LANDMARK_AT, Vector((0.5, -0.8, 1.5)), 54),
                                                     ("12", DENSITY_REGION, (0, 1), DENSITY_VIEW + Vector((0, 0, 1.5)), 66)):
                ring = {t: FLOW_RING.get(t, "plains") for r_ in region for t in
                        ((r_[0] + dq, r_[1] + dr) for dq, dr in hk.NEIGHBOURS) if t not in region}
                tiles_map = {**ring, **{t: (lm if t == lm_at else variant) for t in region}}
                hk.empty_scene()
                templates = load_templates(tiles)
                build_map(templates, tiles=tiles_map)
                col = bpy.data.collections["map"]
                apply_massif(col, set(region), lm_at, scale, tower)
                draw_effects(col, templates)
                stem = f"{prefix}hills_{short}_{size}"
                slope_report(col, stem)
                route_report(region, lm_at, stem)
                top_height(col, stem)
                if short == "monastery" and size == "7":
                    draw_paths(col, templates)
                stage(view, dist_, 50)
                render(f"{stem}_{'paths_' if short == 'monastery' and size == '7' else ''}height")
                if size == "7out" or short == "monastery" and size == "12":
                    continue
                if size == "12":
                    continue
                d, tw = lf.flow(set(region), lm_at)
                a = math.radians(60 * lf.turn(lm_at, d, tw))
                cam = bpy.context.scene.camera
                z = LIFT_POINT(hk.tile_position(*lm_at))
                cam.location = hk.tile_position(*lm_at) + Vector((22 * math.cos(el) * math.cos(a), 22 * math.cos(el) * math.sin(a), z + 2.2 + 22 * math.sin(el)))
                cam.rotation_euler = (math.pi / 2 - el, 0, a + math.pi / 2)
                render(f"{prefix}hills_{short}_{lm}_height")
        sys.exit(0)
    if "hills-t2" in flags:
        # Hills tier 2 and class variant: each region flowing into its landmark, and a close-up; monastery's paths.
        el = math.radians(38)
        for short, variant, lm, with_paths in (("snowy", "snowy_peaks", "yeticave", False),
                                               ("volcanic", "volcanic_peaks", "salamanderden", False),
                                               ("monastery", "monastery_heights", "library", True)):
            if "snowy-only" in flags and short != "snowy":
                continue
            tiles_map = {**FLOW_RING, **{t: (lm if t == LANDMARK_AT else variant) for t in LANDMARK_REGION}}
            for paths in ((True, False) if with_paths else (False,)):
                hk.empty_scene()
                templates = load_templates(tiles)
                build_map(templates, tiles=tiles_map)
                col = bpy.data.collections["map"]
                draw_effects(col, templates)
                if paths:
                    draw_paths(col, templates)
                stage(Vector((0.5, -0.8, 0)), 54, 50)
                render(f"hills_t2_{short}_{'paths' if paths else 'landmark'}")
            d, tw = lf.flow(set(t for t, n in tiles_map.items() if n in (variant, lm)), LANDMARK_AT)
            a = math.radians(60 * lf.turn(LANDMARK_AT, d, tw))
            cam = bpy.context.scene.camera
            cam.location = hk.tile_position(*LANDMARK_AT) + Vector((16 * math.cos(el) * math.cos(a), 16 * math.cos(el) * math.sin(a),
                                                                    2.2 + 16 * math.sin(el)))
            cam.rotation_euler = (math.pi / 2 - el, 0, a + math.pi / 2)
            render(f"hills_t2_{lm}_closeup")
        sys.exit(0)
    if "farmland-t2" in flags:
        # Farmland tier 2: each region flowing into its landmark (with the engine's effects stood in), the same
        # with the path data drawn, and a close-up of each landmark looking at its entrance.
        el = math.radians(40)
        short = {"haunted_homesteads": "haunted", "raided_farms": "raided", "cider_orchards": "cider"}
        for variant, tiles_map in FARM_T2_MAPS.items():
            lm = tiles_map[LANDMARK_AT]
            for paths in (True, False):  # the plain map last, so the close-up below is shot without the paths
                hk.empty_scene()
                templates = load_templates(tiles)
                build_map(templates, tiles=tiles_map)
                col = bpy.data.collections["map"]
                draw_effects(col, templates)
                if paths:
                    draw_paths(col, templates)
                stage(Vector((0.5, -0.8, 0)), 50, 55 if paths else 50)
                render(f"farmland_t2_{short[variant]}_{'paths' if paths else 'landmark'}")
            region = [t for t, n in tiles_map.items() if n in (variant, lm)]
            d, tw = lf.flow(set(region), LANDMARK_AT)
            a = math.radians(60 * lf.turn(LANDMARK_AT, d, tw))
            cam = bpy.context.scene.camera
            at = hk.tile_position(*LANDMARK_AT)
            cam.location = at + Vector((14 * math.cos(el) * math.cos(a), 14 * math.cos(el) * math.sin(a),
                                        1.0 + 14 * math.sin(el)))
            cam.rotation_euler = (math.pi / 2 - el, 0, a + math.pi / 2)
            render(f"farmland_t2_{lm}_closeup")
        sys.exit(0)
    if "markettown-gates" in flags:
        # The farm map with its villages finished as market towns, to show their gates.
        hk.empty_scene()
        build_map(load_templates(tiles), tiles={k: ("market_town" if v == "village" else v) for k, v in FARM_MAP.items()})
        stage(Vector((0.5, -0.8, 0)), 50, 50)
        render("farmland_markettown_gates")
        tiles_map = {k: ("market_town" if v == "village" else v) for k, v in FARM_MAP.items()}
        g = fg.fence_gates({k: vr.terrain_of(n) for k, n in tiles_map.items()})
        t, edges = next((t, e) for t, e in sorted(g.items()) if e and tiles_map[t] == "market_town")
        a = math.radians(60 * edges[0])
        el = math.radians(40)
        at = hk.tile_position(*t) + Vector((math.cos(a), math.sin(a), 0)) * 3.3
        cam = bpy.context.scene.camera
        cam.location = at + Vector((-8 * math.cos(el) * math.cos(a), -8 * math.cos(el) * math.sin(a), 8 * math.sin(el)))
        cam.rotation_euler = (math.pi / 2 - el, 0, a - math.pi / 2)
        render("farmland_markettown_gate_closeup")
        sys.exit(0)
    if "farmland" in flags:
        # Farmland: the farm and village group with its gates, the same with the path data drawn over it, the
        # windmill country region flowing into the Great Windmill, and close-ups of a gate and the mill.
        el = math.radians(40)
        for stem, tiles_map, paths in (("farmland_gates", FARM_MAP, False), ("farmland_paths", FARM_MAP, True),
                                       ("farmland_windmill_landmark", WINDMILL_MAP, False),
                                       ("farmland_windmill_paths", WINDMILL_MAP, True)):
            hk.empty_scene()
            templates = load_templates(tiles)
            build_map(templates, tiles=tiles_map)
            if paths:
                draw_paths(bpy.data.collections["map"], templates)
            stage(Vector((0.5, -0.8, 0)), 50, 55 if paths else 50)
            render(stem)
            cam = bpy.context.scene.camera
            if stem == "farmland_gates":  # close-up of a gate (the first one found on the map)
                g = fg.fence_gates({k: vr.terrain_of(n) for k, n in tiles_map.items()})
                t, edges = next((t, e) for t, e in sorted(g.items()) if e and tiles_map[t] == "farmland")
                a = math.radians(60 * edges[0])
                at = hk.tile_position(*t) + Vector((math.cos(a), math.sin(a), 0)) * 3.3
                cam.location = at + Vector((-8 * math.cos(el) * math.cos(a), -8 * math.cos(el) * math.sin(a),
                                            8 * math.sin(el)))
                cam.rotation_euler = (math.pi / 2 - el, 0, a - math.pi / 2)
                render("farmland_gate_closeup")
            if stem == "farmland_windmill_landmark":  # close-up of the mill, looking at its door
                region = [t for t, n in tiles_map.items() if n in ("windmill_country", "greatwindmill")]
                d, tw = lf.flow(set(region), LANDMARK_AT)
                a = math.radians(60 * lf.turn(LANDMARK_AT, d, tw))
                at = hk.tile_position(*LANDMARK_AT)
                cam.location = at + Vector((15 * math.cos(el) * math.cos(a), 15 * math.cos(el) * math.sin(a),
                                            1.5 + 15 * math.sin(el)))
                cam.rotation_euler = (math.pi / 2 - el, 0, a + math.pi / 2)
                render("farmland_greatwindmill_closeup")
        sys.exit(0)
    if "terrains" in flags:
        hk.empty_scene()
        build_map(load_templates(tiles), tiles=TERRAIN_MAP)
        stage(Vector((4, -1, 0)), 82, 45)
        render("terrains")
        sys.exit(0)
    hk.empty_scene()
    build_map(load_templates(tiles))
    stage(Vector((2, -2, 0)), 74, 45)
    render("map_preview")
    hk.empty_scene()
    build_board(load_templates(cells))
    stage(Vector((0, -0.4, 0)), 20, 48)
    render("combat_preview")
