"""Renders a small test map from the latest tile kit, picking edge wedges the way the engines will.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_preview.py [-- path/to/tiles_vN.blend]
Writes art/preview/map_preview_vN.png (never overwrites).
"""
import glob
import math
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import hexkit as hk  # noqa: E402
import ground_cover as gc  # noqa: E402
import landmark_flow as lf  # noqa: E402
import cliffs  # noqa: E402
import desert_lands as dl  # noqa: E402
import fence_gates as fg  # noqa: E402
import json  # noqa: E402
import sand  # noqa: E402
import variants as vr  # noqa: E402
import village_streets as vs  # noqa: E402
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


def draw_effects(col, templates, thin=False):
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
            at = obj.matrix_world @ Vector((x, -z, y))
            if e["kind"] == "crackle":
                for k in range(4):
                    a_ = 2 * math.pi * k / 4
                    p.box(at + Vector((math.cos(a_) * 0.2, math.sin(a_) * 0.2, 0.15 * k)), (0.07, 0.07, 0.07), "ember")
            elif e["kind"] in ("glint", "shimmer"):
                pass  # engine effects, on the pool's surface and over open ground
            elif e["kind"] == "fire":
                p.cone(at, 0.14, 0.32, "ember", segments=5)
            elif e["kind"] == "spray":
                for k, (dx, dy) in enumerate(((0.1, -0.5), (-0.08, 0.05), (0.1, 0.55))):
                    p.blob(at + Vector((dx, dy, 0)), 0.13, "foam", z=0.05 * k)
            elif e["kind"] == "smoke":
                if thin:  # a town's many chimneys: a thin wisp each
                    for k in range(3):
                        p.blob(at + Vector((0.04 * k, 0.03 * k, 0)), 0.07 + 0.015 * k, "rock_light", z=0.1 + 0.2 * k)
                    continue
                for k in range(4):
                    p.blob(at + Vector((0.08 * k, 0.05 * k, 0)), 0.16 + 0.05 * k, "rock_light", z=0.4 + 0.42 * k)
            else:
                for k in range(5):
                    a_ = 2 * math.pi * k / 5
                    p.box(at + Vector((math.cos(a_) * 0.5, math.sin(a_) * 0.5, 0.1 * k)), (0.14, 0.04, 0.02), "crow")
    p.finish(col)


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
        lines = [[m @ Vector((x, -z, y)) for x, y, z in line] for line in json.loads(src.get("paths", "[]"))]
        for line in lines:
            for a, b in zip(line, line[1:]):
                d = b - a
                vr.frustum(p, a + Vector((0, 0, 0.14)), b + Vector((0, 0, 0.14)), 0.05, 0.05, "path_debug", segments=4)
        key = (round(m.translation.x, 1), round(m.translation.y, 1))
        for i, line in json.loads(src.get("path_spokes", "{}")).items():
            tiles.setdefault(key, {}).setdefault("spokes", []).append((int(i), [m @ Vector((x, -z, y)) for x, y, z in line]))
        if "path_hub" in src:
            x, y, z = json.loads(src["path_hub"])
            tiles.setdefault(key, {})["hub"] = m @ Vector((x, -z, y))
        tiles.setdefault(key, {}).setdefault("ends", []).extend(l[0] for l in lines)
    for t in tiles.values():  # spokes, only where a wedge path ends at the spoke's outer end
        for i, line in t.get("spokes", []):
            if any((e - line[0]).length < 0.05 for e in t.get("ends", [])):
                for a, b in zip(line, line[1:]):
                    vr.frustum(p, a + Vector((0, 0, 0.14)), b + Vector((0, 0, 0.14)), 0.05, 0.05, "path_debug", segments=4)
        for e in t.get("ends", []) if "hub" in t else []:
            d = e - t["hub"]
            if d.length < 2.2:  # a wedge path's inner end on this tile
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

# Village tier 0: a group of tiles in a loose shape with farms joined to it, and other land round it; market town's region.
VILLAGE_MAP = {**FLOW_RING, (0, 0): "village", (1, 0): "village", (0, 1): "village", (-1, 1): "village", (-1, 0): "village",
               (0, -1): "village", (1, -1): "farmland", (2, -1): "farmland", (-1, 2): "farmland"}
MARKET_MAP = {**FLOW_RING, **{t: ("tradinghouse" if t == LANDMARK_AT else "market_town") for t in LANDMARK_REGION}}

TOWN_T2 = {lm: {**FLOW_RING, **{t: (lm if t == LANDMARK_AT else v) for t in LANDMARK_REGION}}
           for lm, v in (("keep", "fortified_town"), ("blackmarket", "slums"), ("college", "scholars_town"))}
# A bigger fortified town, to show its works thinning away from the Keep.
FORT_12_MAP = {**{t: FLOW_RING.get(t, "plains") for r_ in DENSITY_REGION for t in ((r_[0] + dq, r_[1] + dr) for dq, dr in hk.NEIGHBOURS)},
               **{t: ("keep" if t == (0, 1) else "fortified_town") for t in DENSITY_REGION}}
# A fortified town's walls meeting a plain village and farms: gatehouses where streets leave the region.
FORT_JOIN_MAP = {**FLOW_RING, (0, 0): "fortified_town", (1, 0): "fortified_town", (0, 1): "fortified_town", (-1, 1): "village",
                 (-1, 0): "village", (0, -1): "farmland", (1, -1): "keep", (1, 1): "farmland"}

# River/lake tier 0: a lake, a river out of it with a bend and a fork, a spring, and a pond, among other land.
RIVER_T0_MAP = {**FLOW_RING, (0, 0): "river", (1, 0): "river", (0, 1): "river", (-1, 1): "river", (-1, 0): "plains", (1, -1): "farmland",
                (0, -1): "plains", (-1, 2): "river", (-2, 3): "river", (-2, 2): "plains", (0, 2): "plains", (2, -1): "river", (3, -1): "river", (2, 0): "plains", (-2, 0): "river"}
RAFT_AT = (-1, 2)
# Round 2: each water variant's region with its landmark on an outer tile, among land.
LAKE_MAP = {**FLOW_RING, **{t: ("serpentlair" if t == LANDMARK_AT else "great_lake") for t in LANDMARK_REGION}}
RAPIDS_MAP = {**FLOW_RING, (-1, 0): "plains", (0, -1): "plains", (1, 0): "plains", (-1, 1): "plains", (0, 1): "plains", (-1, 2): "plains", (1, -2): "plains", (0, 0): "trollbridge", (1, -1): "rapids", (2, -2): "rapids", (3, -3): "rapids", (0, 1): "rapids", (-1, 2): "rapids", (-2, 3): "rapids", (-1, 1): "plains", (-2, 2): "plains", (2, -3): "plains", (3, -2): "plains", (1, 2): "plains", (-1, 3): "plains", (-3, 3): "plains", (-3, 4): "plains", (-2, 4): "plains"}
STILL_MAP = {**FLOW_RING, (0, 0): "still_waters", (-1, 0): "still_waters", (0, 1): "still_waters", (-1, 1): "still_waters", (1, 0): "meditationrock", (1, -1): "plains", (0, -1): "plains", (2, -1): "plains", (2, 0): "plains", (1, 1): "plains"}
PORT_GATE_MAP = {**FLOW_RING, (1, 0): "plains", (0, -1): "plains", (-1, 2): "plains", (0, 2): "plains", (1, -1): "delta",
                 (2, -2): "delta", (-1, 0): "plains", (0, 1): "plains", (-1, 1): "delta", (-2, 2): "delta", (0, 0): "riverport"}
DELTA_MAP = {**FLOW_RING, (1, 0): "plains", (-1, 1): "plains", (0, -1): "plains", (-1, 2): "plains", (0, 2): "delta", (0, 3): "plains",
             (1, 2): "plains", (-1, 3): "plains", (-2, 0): "delta", (-3, 0): "plains", (-3, 1): "plains", (-2, -1): "plains",
             **{t: ("riverport" if t == LANDMARK_AT else "delta") for t in [(0, 0), (-1, 0), (0, 1), (1, -1)]}}

# Farmland tier 2: each variant's 7-tile region with its landmark on an outer tile, ringed by plains and forest.
FARM_T2_MAPS = {v: {**FLOW_RING, **{t: (lm if t == LANDMARK_AT else v) for t in LANDMARK_REGION}}
                for v, lm in (("haunted_homesteads", "abandonedbarn"), ("raided_farms", "militiabarn"),
                              ("cider_orchards", "harvestfestival"))}

# Farms and villages count as joined: the farm track meets the village street, with no border between them.
LINKED = {frozenset(("farmland", "village"))}
BORDERED = {"farmland", "village"}


def linked(a, b):
    """Joined for edge pieces: the same terrain (a region variant counts as its terrain), or linked terrains."""
    if b and vr.wedges_of(a) != vr.wedges_of(b) and (vr.wedges_of(a) in cliffs.RAISED or vr.wedges_of(b) in cliffs.RAISED):
        return False  # a raised region shares no mountain with the land below it
    if "canyon" in (vr.wedges_of(a), b and vr.wedges_of(b)):
        return dl.joins(a, b, vr.wedges_of, vr.LANDMARKS)  # gorges run only between canyon tiles
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


def build_map(templates, animated=False, tiles=None, raised_regions=(), flows=None, hollow=()):
    """Places the test map. With animated=True, water tiles get banks and dressing only and are
    returned as (q, r, position, mask) so the animation can build moving water and bobbing boats.
    raised_regions: the (tiles, variant) pairs that raise_region will raise, for the fence gates and the ridges at ledge tops. flows: landmark tile ->
    (dist, toward, turn) to keep from when its region finished, rather than working them out from the map. hollow: tiles left to the caller, with no empty slot drawn."""
    MAP = tiles or globals()["MAP"]
    water_tiles = []
    col = hk.new_collection("map")
    # Landmark flow (landmark_flow.py): each landmark's region is its variant's tiles joined to it. In the game
    # the region is known; here it's the connected group of the variant's tiles round the landmark.
    dist, toward, turns = {}, {}, {}
    for lm_at, lm in MAP.items():
        if flows and lm_at in flows:
            d, t, turns[lm_at] = flows[lm_at]
            dist.update(d)
            toward.update(t)
        elif lm in vr.LANDMARKS:
            region, todo = {lm_at}, [lm_at]
            while todo:
                q, r = todo.pop()
                for dq, dr in hk.NEIGHBOURS:
                    n = (q + dq, r + dr)
                    if n not in region and MAP.get(n) == vr.LANDMARKS[lm]:
                        region.add(n)
                        todo.append(n)
            d, t = lf.flow(region, lm_at)
            for k_, v_ in d.items():  # an oasis has two tiles to thicken toward
                dist[k_] = min(dist.get(k_, 99), v_)
            toward.update(t)
            turns[lm_at] = lf.turn(lm_at, d, t)  # the landmark's entrance faces its longest trail
            if lm in ("sandstonesphinx", "echocave"):
                turns[lm_at] = sand.sphinx_turn(lm_at, region)
            if lm == "raiderstronghold":
                turns[lm_at] = dl.STRONGHOLD_TURN
    # Fence gates round farm and village groups (fence_gates.py).
    raised = set(t for tiles_, _ in raised_regions for t in tiles_)
    terrains = {k: vr.terrain_of(n) for k, n in MAP.items()}
    all_ledges = [c for tiles_, _ in raised_regions for c in cliffs.climbs(set(tiles_), terrains, raised)]
    gates = fg.fence_gates(terrains, raised, all_ledges)
    ledge_tops = cliffs.ledge_tops(all_ledges)
    streets = vs.streets(terrains, [(t, i) for t in terrains for i in lf.trail_edges(t, toward)])
    for (q, r), name in MAP.items():
        # name is a terrain or a region variant (variants.py); the variant's pieces carry its name, and
        # edge pieces are picked by its terrain.
        terrain = vr.terrain_of(name)
        at = hk.tile_position(q, r)
        kit = vr.wedges_of(name)  # a centre-only landmark takes its variant's wedges and ground colour
        base = place(templates, f"base_{terrain}", col, at) if kit != "canyon" else None  # the canyon's pieces are its ground: a slab would cover the gorges
        if kit in vr.VARIANTS and base:
            # Variants use their terrain's base with their own ground colour on top (slot 0 is the top).
            base.material_slots[0].link = "OBJECT"
            base.material_slots[0].material = hk.material(vr.VARIANTS[kit][2])
        if terrain == "river":
            # Water is drawn per tile from its own water neighbours, the way the engines will.
            near = [MAP.get((q + dq, r + dr)) for dq, dr in hk.NEIGHBOURS]
            mask = [vr.terrain_of(n) == "river" if n else False for n in near]
            p = hk.Piece(f"water_{q}_{r}")
            seed = f"{q},{r}"
            port = wt.port_turn(mask, seed) if name == "riverport" else None
            band = dist.get((q, r), 0) if dist.get((q, r), 0) in (1, 2) else 0
            widths = wt.edge_widths(kit, [n and vr.wedges_of(n) for n in near])
            is_lm = name in vr.LANDMARK_CENTRES
            wt.add_water(p, mask, seed, plates=not animated, boats=not animated, widths=widths, style=wt.FAMILY.get(kit), near=band, port=port, landmark=is_lm)
            p.finish(col, at)
            water_tiles.append((q, r, at, mask))
            for prop, pt, ang in wt.tile_props(mask, seed, widths, wt.FAMILY.get(kit), band, is_lm):
                place(templates, prop, col, at + Vector((pt[0], pt[1], 0)), ang)
            if name == "serpentlair":
                place(templates, "serpentlair_centre", col, at, math.radians(60 * turns.get((q, r), 0)))
            elif name == "meditationrock":
                place(templates, "meditationrock_centre", col, at, math.radians(60 * (wt.rock_routes(mask, seed, widths)[3] or 0)))
            elif name == "trollbridge":
                mid, ang, _ = wt.bridge_spot(mask, seed, widths, wt.TROLL_HALF)
                place(templates, "trollbridge_centre", col, at + Vector((mid[0], mid[1], 0)), ang)
            if port is not None:  # the port's piece, its boats, and a water gate on each back edge with water beyond it
                spin = math.radians(60 * port)
                place(templates, f"{name}_centre", col, at, spin)
                for part, (_, hub) in vr.LANDMARK_PARTS.items():
                    if part.startswith(f"{name}_"):
                        place(templates, part, col, at + Matrix.Rotation(spin, 3, "Z") @ hub, spin)
                for k in (2, 3, 4):
                    if mask[(k + port) % 6]:
                        place(templates, f"{name}_watergate", col, at, math.radians(60 * (k + port)))
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
        if name in sand.LOOKS:
            # The sand is shaped in world space, the way the engines will.
            p = hk.Piece(f"sand_{q}_{r}")
            sand.add_sand(p, MAP, q, r, dist.get((q, r)), turns.get((q, r), 0))
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
            # None within two steps of a landmark (clear ground), nor where steps run (they'd bury them), nor where a ledge comes out.
            if len(parts) >= 2 and dist.get((q, r), 3) > 2 and f"{kit}_steps_centre" not in templates and (q, r) not in ledge_tops:
                place(templates, f"{name}_ridge_knot", col, at)
                for where, i in parts:
                    place(templates, f"{name}_ridge_{where}", col, at, math.radians(60 * i))
        walled = f"{kit}_border_join_l" in templates  # stone walls in place of the fence, at the region's edges
        kin = [joined[k] and (not walled or vr.wedges_of(MAP.get((q + hk.NEIGHBOURS[k][0], r + hk.NEIGHBOURS[k][1]))) == kit) for k in range(6)]
        for i in range(6):
            edge = f"{kit}_edge_{'same' if joined[i] else 'other'}"
            near = MAP.get((q + hk.NEIGHBOURS[i][0], r + hk.NEIGHBOURS[i][1]))
            neighbour = near and vr.wedges_of(near)
            if walled and joined[i] and neighbour != kit:  # a wall at the region's edge: a gatehouse where a street leaves it
                edge = f"{kit}_edge_gate" if i in streets[(q, r)] else f"{kit}_edge_other{'_lm' if name in vr.LANDMARKS else ''}"
            elif vr.LANDMARKS.get(near) == name and f"{name}_edge_landmark" in templates:
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
            elif joined[i] and f"{kit}_edge_block" in templates:  # a town: a street only where this edge has one
                edge = f"{kit}_{dict(main='edge_same', side='edge_side').get(streets[(q, r)].get(i), 'edge_block')}"
                if edge == f"{kit}_edge_block" and name in vr.LANDMARKS and f"{kit}_edge_block_lm" in templates:
                    edge = f"{kit}_edge_block_lm"  # without the house toward the middle: the landmark's yard lies there
            place(templates, edge, col, at, math.radians(60 * i))
            if i in trails and f"{kit}_steps_centre" in templates:  # the stair's flight on the centre, one per trail edge
                if name not in vr.LANDMARKS:
                    place(templates, f"{kit}_steps_centre", col, at, math.radians(60 * i))
                elif i != turns.get((q, r)):  # the entrance edge's steps are in the landmark's own piece
                    place(templates, f"{kit}_steps_rise", col, at, math.radians(60 * i))
            # Carry a neighbouring edge's border out to this joined edge, so borders run on between tiles.
            if terrain in BORDERED and kin[i] and "border_join_l" in templates:
                join = f"{kit}_border_join" if walled else "border_join"
                if not kin[(i + 1) % 6]:
                    place(templates, f"{join}_l", col, at, math.radians(60 * i))
                if not kin[(i - 1) % 6]:
                    place(templates, f"{join}_r", col, at, math.radians(60 * i))
    for piece, x, y, deg in dl.badlands_features(MAP, dist):  # the badlands' mesas and camps, per tile corner
        place(templates, piece, col, Vector((x, y, 0)), math.radians(deg))
    for piece, x, y, deg in dl.oasis_ripples(MAP):  # the oasis's ripples, one way across the region
        place(templates, piece, col, Vector((x, y, 0.01)), math.radians(deg))
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
    slots = {(q + dq, r + dr) for (q, r) in MAP for dq, dr in hk.NEIGHBOURS} - set(MAP) - set(hollow)
    for q, r in slots:
        p = hk.Piece("slot")
        p.flat([c for c in hk.hex_corners(hk.TILE_RADIUS * 0.94, pointy=True)][::-1], 0.02, "slot")
        p.finish(col, hk.tile_position(q, r) - Vector((0, 0, 0.3)))
    return water_tiles


def raise_region(templates, col, tiles_map, regions, progress=1.0):
    """The engine's raised regions (cliffs.py). regions: (tiles, variant) pairs, all raised. progress: how far through the
    rise, for a preview of it: tile pieces come up from the ground, cliffs from below it. Returns the climbs."""
    bpy.context.view_layer.update()
    centres = {t: hk.tile_position(*t) for t in tiles_map}
    terrains = {t: vr.terrain_of(n) for t, n in tiles_map.items()}
    raised = set(t for tiles, _ in regions for t in tiles)
    all_climbs = []

    def tile_of(obj):
        return next((t for t, c in centres.items() if (c - obj.location).xy.length < 0.01), None)

    def edge_piece(t, i):
        for obj in col.objects:
            if tile_of(obj) == t and "_edge_" in obj.get("piece", "") and round(math.degrees(obj.rotation_euler.z)) % 360 == 60 * i:
                return obj

    def swap(t, i, name):
        obj = edge_piece(t, i)
        obj.data = templates[name].data
        obj["piece"] = name

    for region, variant in regions:
        region = set(region)
        climbs = cliffs.climbs(region, terrains, raised)
        all_climbs += climbs
        ledge = {}
        for t, i in climbs:
            ledge[(t, (i - 1) % 6)] = "low"
            ledge[(t, i)] = "mid"
            ledge[(t, (i + 1) % 6)] = "top"
            if f"{variant}_steps_centre" in templates:  # the stair carries on to the tile's landing, or up the landmark's rise
                place(templates, f"{variant}_{'steps_centre' if tiles_map[t] == variant else 'steps_rise'}", col, centres[t],
                      math.radians(60 * ((i + 1) % 6)))
        for t, i in cliffs.outer_edges(region, raised):
            swap(t, i, f"{variant}_edge_{ {'low': 'climb_low', 'mid': 'climb', 'top': 'climb_top'}[ledge[(t, i)]] if (t, i) in ledge else 'rim'}")
    for obj in list(col.objects):
        if obj.name != "ground_cover" and tile_of(obj) in raised:
            if obj.get("piece", "").startswith("base_"):
                bpy.data.objects.remove(obj)  # the ground covers the tile
                continue
            obj.location.z += vr.RAISE * progress
        elif obj.name == "ground_cover":  # raised ground holds no cover: only tufts fading in from neighbours, which stay down
            mesh = obj.data.copy()
            bm = bmesh.new()
            bm.from_mesh(mesh)
            seen, gone = set(), []
            for v in bm.verts:
                if v in seen:
                    continue
                seen.add(v)
                isle = [v]
                for u in isle:
                    for e in u.link_edges:
                        w = e.other_vert(u)
                        if w not in seen:
                            seen.add(w)
                            isle.append(w)
                mid = obj.matrix_world @ (sum((u.co for u in isle), Vector()) / len(isle))
                if any(max((mid - centres[t]).dot(hk.edge_normal(k)) for k in range(6)) <= hk.TILE_APOTHEM for t in raised):
                    gone += isle
            bmesh.ops.delete(bm, geom=gone, context="VERTS")
            bm.to_mesh(mesh)
            bm.free()
            obj.data = mesh
    low = -vr.RAISE * (1 - progress)
    for region, variant in regions:
        region = set(region)
        ledge = {}
        skip = set()
        for t, i in (c for c in all_climbs if c[0] in region):
            ledge[(t, (i - 1) % 6)], ledge[(t, i)], ledge[(t, (i + 1) % 6)] = "low", "mid", "top"
            skip |= {(t, (i - 1) % 6), (t, i), (t, (i + 1) % 6)}
        for t, i in cliffs.outer_edges(region, raised):
            kind = f"cliff_path_{ledge[(t, i)]}" if (t, i) in ledge else "cliff_edge_b" if gc.hash01(t[0] * 6 + i, t[1], 8) < 0.5 else "cliff_edge"
            place(templates, f"{variant}_{kind}", col, centres[t] + Vector((0, 0, low)), math.radians(60 * i))
        for t, i in cliffs.outer_corners(region, raised):
            if (t, i) not in skip:
                place(templates, f"{variant}_cliff_corner", col, centres[t] + Vector((0, 0, low)), math.radians(60 * i))
    return all_climbs


def tile_report(col, label):
    """Triangles per tile, without the base, the way the budget counts them."""
    bpy.context.view_layer.update()
    per = {}
    for obj in col.objects:
        piece = obj.get("piece", "")
        if not piece or piece.startswith("base_"):
            continue
        obj.data.calc_loop_triangles()
        k = (round(obj.location.x, 1), round(obj.location.y, 1))
        per[k] = per.get(k, 0) + len(obj.data.loop_triangles)
    print(f"TRIS {label}: worst {max(per.values())}")


def look_at(cam, eye, target):
    cam.location = eye
    cam.rotation_euler = (target - eye).to_track_quat("-Z", "Y").to_euler()


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
    return hk.next_number(os.path.join(hk.ART, "preview"), stem, "png")


def render(stem):
    """Renders to preview/<stem>_vN.png, N one past the highest version (counting lettered options too)."""
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
    if "raised" in flags:
        # Raised regions (cliffs.py): 7 and 12 tiles from the map camera, from the foot of the cliff looking up, and a
        # close-up of a ledge. --only picks variants; --trial renders under a scratch name.
        prefix = "trial_" if "trial" in flags else ""
        for short, variant, lm in (("snowy", "snowy_peaks", "yeticave"), ("volcanic", "volcanic_peaks", "salamanderden")):
            if flags.get("only") and short not in flags["only"].split(","):
                continue
            for size, region, lm_at, view, far in (("7", LANDMARK_REGION, LANDMARK_AT, Vector((0.5, -1.5, 2.0)), 62),
                                                   ("12", DENSITY_REGION, (0, 1), DENSITY_VIEW + Vector((0, -1, 2.0)), 74)):
                ring = {t: FLOW_RING.get(t, "plains") for r_ in region for t in
                        ((r_[0] + dq, r_[1] + dr) for dq, dr in hk.NEIGHBOURS) if t not in region}
                tiles_map = {**ring, **{t: (lm if t == lm_at else variant) for t in region}}
                hk.empty_scene()
                templates = load_templates(tiles)
                build_map(templates, tiles=tiles_map, raised_regions=[(region, variant)])
                col = bpy.data.collections["map"]
                climbs = raise_region(templates, col, tiles_map, [(region, variant)])
                tile_report(col, f"{short} {size}")
                draw_effects(col, templates)
                stage(view, far, 50)
                print("CLIMBS", short, size, climbs)
                render(f"{prefix}hills_{short}_{size}_raised")
                cam = bpy.context.scene.camera
                t, i = next(((t, i) for t, i in climbs if hk.edge_normal(i).y < 0.1), climbs[0])
                n = hk.edge_normal(i)
                mid = hk.tile_position(*t) + n * hk.TILE_APOTHEM
                if size == "7":
                    cam.data.lens = 24  # from the foot of a cliff, looking up, as the party would
                    wall = min(cliffs.outer_edges(set(region)), key=lambda e: (hk.tile_position(*e[0]) + hk.edge_normal(e[1]) * hk.TILE_APOTHEM).y)
                    side = hk.tile_position(*wall[0]) + hk.edge_normal(wall[1]) * hk.TILE_APOTHEM
                    look_at(cam, side + Vector((0, -11, 1.0)), side + Vector((0, 8, vr.RAISE + 1.5)))
                    render(f"{prefix}hills_{short}_low_raised")
                    cam.data.lens = 36  # the ledge, its route drawn
                    draw_paths(col, templates)
                    look_at(cam, mid + n * 13 + Vector((0, 0, vr.RAISE * 0.5 + 6)), mid + Vector((0, 0, vr.RAISE * 0.45)))
                    render(f"{prefix}hills_{short}_climb_raised")
                # Every ledge's foot, low, from the land in front of it with the wall running away, and its top from the plateau.
                cam.data.lens = 24
                if size != "7":
                    draw_paths(col, templates)
                for k, (t, i) in enumerate(climbs):
                    centre = hk.tile_position(*t)
                    out, along = hk.edge_normal(i - 1), hk.edge_normal(i - 1 + 1.5)
                    foot = centre + out * vr.X1 + along * vr.foot_y()
                    look_at(cam, foot + out * 5.5 - along * 2.8 + Vector((0, 0, 1.3)), foot + along * 1.2 + Vector((0, 0, 1.3)))
                    render(f"{prefix}hills_{short}_{size}{'abcdef'[k]}_foot_raised")
                    out, along = hk.edge_normal(i + 1), hk.edge_normal(i + 1 + 1.5)
                    exit_ = centre + out * vr.LEDGE_X + along * vr.climb_heights()[2] + Vector((0, 0, vr.RAISE))
                    look_at(cam, exit_ - out * 1.5 - along * 7.5 + Vector((0, 0, 6.5)), exit_ + along * 0.5 - Vector((0, 0, 1.5)))
                    render(f"{prefix}hills_{short}_{size}{'abcdef'[k]}_top_raised")
        sys.exit(0)
    lair_turn = {}

    def water_lines(tiles_map):
        """The routes on water (red), and each walk on land to a landing, a bridge or stepping stones (yellow)."""
        p = hk.Piece("water_routes")
        for (q, r), name in tiles_map.items():
            if vr.terrain_of(name) != "river":
                continue
            near = [tiles_map.get((q + dq, r + dr)) for dq, dr in hk.NEIGHBOURS]
            mask = [vr.terrain_of(n) == "river" if n else False for n in near]
            kit = vr.wedges_of(name)
            widths = wt.edge_widths(kit, [n and vr.wedges_of(n) for n in near])
            at, seed = hk.tile_position(q, r), f"{q},{r}"

            def line(pts, mat):
                for a, b in zip(pts, pts[1:]):
                    vr.frustum(p, at + Vector((a[0], a[1], 0.16)), at + Vector((b[0], b[1], 0.16)), 0.05, 0.05, mat, segments=4)
            if name == "riverport":
                t = wt.port_turn(mask, seed)
                walk, floats = wt.port_routes(mask, t)
                for l_ in walk.values():
                    line(l_, "lantern")
                for l_ in floats.values():
                    line(l_, "path_debug")
                line([wt.turned(wt.PORT_FLOAT, t), wt.turned(wt.PORT_STOP, t)], "path_debug")
                continue
            if name == "serpentlair":
                for l_ in wt.lair_routes(lair_turn.get((q, r), 0)).values():
                    line(l_, "path_debug")
                line([wt.turned(wt.LAIR_LAND, lair_turn.get((q, r), 0)), wt.turned(wt.LAIR_STOP, lair_turn.get((q, r), 0))], "path_debug")
                continue
            if name == "meditationrock":
                walk, floats, _, _ = wt.rock_routes(mask, seed, widths)
                for l_ in walk.values():
                    line(l_, "lantern")
                for l_ in floats.values():
                    line(l_, "path_debug")
                continue
            _, lines = wt.water_routes(mask, seed, widths, wt.FAMILY.get(kit))
            for l_ in lines.values():
                line(l_, "path_debug")
            spot = wt.bridge_spot(mask, seed, widths, wt.TROLL_HALF if name == "trollbridge" else wt.BRIDGE_HALF) if kit == "rapids" else None
            if spot and (name == "trollbridge" or random.Random(f"{seed}-bridge").random() < wt.BRIDGE_CHANCE):
                for l_ in spot[2].values():
                    line(l_, "lantern")
                half_ = wt.TROLL_HALF if name == "trollbridge" else wt.BRIDGE_HALF
                d_ = (math.cos(spot[1]) * half_, math.sin(spot[1]) * half_)
                line([wt.sub(spot[0], d_), wt.add(spot[0], d_)], "lantern")
            else:
                for e, s, w_ in wt.landings(mask, seed, widths, wt.FAMILY.get(kit)).values():
                    line([e, s, w_], "lantern")
        p.finish(bpy.data.collections["map"])

    if "river" in flags:
        # River/lake round 1: tier 0 with the water routes and landings, the delta flowing to the River Port, the port up close,
        # and the party's raft on a river at map zoom and close to.
        prefix = "trial_" if "trial" in flags else ""

        def shot(stem):
            if not flags.get("only") or stem in flags["only"].split(","):
                render(f"{prefix}{stem}")

        def seat_party(at, ang, kinds=("standin_hero", "standin_chelmsford", "standin_small", "standin_fluffy")):
            """The raft on the water with four stand-in minis on its seats."""
            col = bpy.data.collections["map"]
            raft_t = templates["raft"]
            place({"raft": raft_t}, "raft", col, at, ang)
            minis = load_templates(max(glob.glob(os.path.join(hk.ART, "minis", "standins", "standin_minis_v*.blend")), key=lambda f: int(re.search(r"_v(\d+)", f).group(1))))
            for seat, kind in zip(json.loads(raft_t["effects"]), kinds):
                x, y, z = seat["at"]
                pos = Matrix.Rotation(ang, 3, "Z") @ Vector((x, -z, y))
                o = place(minis, kind, col, at + pos, ang + math.pi / 2)

        for stem, tiles_map, focus, dist in (("river_t0", RIVER_T0_MAP, Vector((0, -0.5, 0)), 62), ("river_delta", DELTA_MAP, Vector((0.5, -0.8, 0)), 56)):
            for paths in (True, False):
                hk.empty_scene()
                templates = load_templates(tiles)
                build_map(templates, tiles=tiles_map)
                draw_effects(bpy.data.collections["map"], templates, thin=True)
                if paths:
                    water_lines(tiles_map)
                stage(focus, dist, 50)
                shot(f"{stem}_{'paths' if paths else 'map'}")
            if stem == "river_delta":
                t = wt.port_turn([vr.terrain_of(tiles_map.get((LANDMARK_AT[0] + dq, LANDMARK_AT[1] + dr))) == "river" if tiles_map.get((LANDMARK_AT[0] + dq, LANDMARK_AT[1] + dr)) else False for dq, dr in hk.NEIGHBOURS], f"{LANDMARK_AT[0]},{LANDMARK_AT[1]}")
                a_, el = math.radians(60 * t), math.radians(35)
                cam = bpy.context.scene.camera
                at = hk.tile_position(*LANDMARK_AT)
                cam.location = at + Vector((13 * math.cos(el) * math.cos(a_), 13 * math.cos(el) * math.sin(a_), 1.5 + 13 * math.sin(el)))
                cam.rotation_euler = (math.pi / 2 - el, 0, a_ + math.pi / 2)
                shot("river_riverport_closeup")
        # the port with water behind it as well as in front: its water gate
        hk.empty_scene()
        templates = load_templates(tiles)
        build_map(templates, tiles=PORT_GATE_MAP)
        stage(Vector((0.5, -0.8, 0)), 50, 50)
        shot("river_port_gate_map")
        hub_t = (0, 0)
        mask = [vr.terrain_of(PORT_GATE_MAP.get((hub_t[0] + dq, hub_t[1] + dr))) == "river" if PORT_GATE_MAP.get((hub_t[0] + dq, hub_t[1] + dr)) else False for dq, dr in hk.NEIGHBOURS]
        t = wt.port_turn(mask, "0,0")
        back = next((k + t) % 6 for k in (2, 3, 4) if mask[(k + t) % 6])
        n_ = hk.edge_normal(back)
        cam = bpy.context.scene.camera
        at = hk.tile_position(*hub_t) + n_ * 3.9
        look_at(cam, at + n_ * 6.5 + Vector((0, 0, 4.5)), at + Vector((0, 0, 0.5)))
        shot("river_port_gate_closeup")
        # the raft on the river: at map zoom, then close to
        hk.empty_scene()
        templates = load_templates(tiles)
        build_map(templates, tiles=RIVER_T0_MAP)
        hub, lines = wt.water_routes([vr.terrain_of(RIVER_T0_MAP.get((RAFT_AT[0] + dq, RAFT_AT[1] + dr))) == "river" if RIVER_T0_MAP.get((RAFT_AT[0] + dq, RAFT_AT[1] + dr)) else False for dq, dr in hk.NEIGHBOURS], f"{RAFT_AT[0]},{RAFT_AT[1]}")
        l_ = next(iter(lines.values()))
        at = hk.tile_position(*RAFT_AT) + Vector((hub[0], hub[1], 0.03))
        seat_party(at, math.atan2(l_[-2][1] - hub[1], l_[-2][0] - hub[0]))
        stage(Vector((0, -0.5, 0)), 62, 50)
        shot("river_raft_map")
        cam = bpy.context.scene.camera
        look_at(cam, at + Vector((5, -7, 5)), at + Vector((0, 0, 0.6)))
        shot("river_raft_closeup")
        sys.exit(0)
    if "desert" in flags:
        # Tier 0 desert, and dunes/wasteland flowing by density to the Sandstone Sphinx. --only picks shots.
        def shot(stem):
            if not flags.get("only") or stem in flags["only"].split(","):
                render(stem)

        def spin_cam(focus_, dist_, ang):
            el = math.radians(50)
            cam = bpy.context.scene.camera
            cam.location = focus_ + Vector((dist_ * math.cos(el) * math.cos(ang), dist_ * math.cos(el) * math.sin(ang), dist_ * math.sin(el)))
            cam.rotation_euler = (math.pi / 2 - el, 0, ang + math.pi / 2)

        ring = {t: ("river" if t in ((2, -1), (2, 0)) else "ruins" if t == (-2, 0) else "plains") for t in FLOW_RING}
        t0 = {**ring, **{t: "desert" for t in LANDMARK_REGION}}
        hk.empty_scene()
        templates = load_templates(tiles)
        build_map(templates, tiles=t0)
        draw_effects(bpy.data.collections["map"], templates, thin=True)
        stage(Vector((0.5, -0.8, 0)), 54, 50)
        shot("desert_t0_map")
        # The Sphinx in the middle of its region, ruins thickening round it from all sides.
        for stem, region in (("desert_centre_7_map", [(0, 0)] + [(dq, dr) for dq, dr in hk.NEIGHBOURS]),
                             ("desert_centre_12_map", [(0, 0)] + [(dq, dr) for dq, dr in hk.NEIGHBOURS] + [(1, 1), (2, -1), (1, -2), (-1, 2), (-2, 1)])):
            if flags.get("only") and stem not in flags["only"].split(","):
                continue
            around_ = {t: "plains" for b_ in region for t in ((b_[0] + dq, b_[1] + dr) for dq, dr in hk.NEIGHBOURS) if t not in region}
            hk.empty_scene()
            templates = load_templates(tiles)
            build_map(templates, tiles={**around_, **{t: "wasteland" for t in region}, (0, 0): "sandstonesphinx"})
            draw_effects(bpy.data.collections["map"], templates, thin=True)
            stage(Vector((0, -0.5, 1.0)), 54 if len(region) == 7 else 66, 50)
            render(stem)
        wide = {t: "plains" for b_ in DENSITY_REGION for t in ((b_[0] + dq, b_[1] + dr) for dq, dr in hk.NEIGHBOURS) if t not in DENSITY_REGION}
        wide.update({t: "river" for t in ((2, -1), (2, 0)) if t in wide})
        waste = {**wide, **{t: "wasteland" for t in DENSITY_REGION}, LANDMARK_AT: "sandstonesphinx"}
        hk.empty_scene()
        templates = load_templates(tiles)
        build_map(templates, tiles=waste)
        col = bpy.data.collections["map"]
        draw_effects(col, templates, thin=True)
        stage(DENSITY_VIEW + Vector((0, -1, 0)), 74, 50)
        shot("desert_waste_map")
        spin_cam(DENSITY_VIEW, 74, math.radians(150))
        shot("desert_waste_turned")
        d_, to_ = lf.flow(set(DENSITY_REGION), LANDMARK_AT)
        t_ = sand.sphinx_turn(LANDMARK_AT, set(DENSITY_REGION))
        at = hk.tile_position(*LANDMARK_AT)
        a_ = math.radians(60 * t_)
        for stem, ang, far, el, lift in (("desert_sphinx_closeup", a_ + 0.55, 19, 28, 2.3), ("desert_sphinx_closeup_b", a_ + 2.4, 19, 40, 2.0), ("desert_sphinx_default", -math.pi / 2, 20, 42, 2.0), ("desert_sphinx_face", a_ + 0.25, 9, 12, 2.2)):
            el = math.radians(el)
            cam = bpy.context.scene.camera
            cam.location = at + Vector((far * math.cos(el) * math.cos(ang), far * math.cos(el) * math.sin(ang), lift + far * math.sin(el)))
            cam.rotation_euler = (math.pi / 2 - el, 0, ang + math.pi / 2)
            shot(stem)
        terrains_ = dict(waste)
        p = hk.Piece("routes_overlay")
        for line in sand.sphinx_routes(t_).values():
            pts = [Vector((at.x + x, at.y + y, sand.surface_z(terrains_, *LANDMARK_AT, at.x + x, at.y + y, t_) + 0.1)) for x, y in line]
            for a, b in zip(pts, pts[1:]):
                vr.frustum(p, a, b, 0.05, 0.05, "path_debug", segments=4)
        p.finish(col)
        stage(at, 34, 50)
        shot("desert_sphinx_routes")
        sys.exit(0)
    if "desert2" in flags:
        # Desert round 2: badlands, oasis and canyon, each a 12-tile region with its landmark, from the map camera, turned, and close to; the canyon from low down too, and rays looking for holes.
        def shot(stem):
            if not flags.get("only") or stem in flags["only"].split(","):
                render(stem)

        def view(focus_, dist_, el_deg, ang):
            el = math.radians(el_deg)
            cam = bpy.context.scene.camera
            cam.location = focus_ + Vector((dist_ * math.cos(el) * math.cos(ang), dist_ * math.cos(el) * math.sin(ang), dist_ * math.sin(el)))
            cam.rotation_euler = (math.pi / 2 - el, 0, ang + math.pi / 2)

        region = [(0, 0)] + list(hk.NEIGHBOURS) + [(1, 1), (2, -1), (1, -2), (-1, 2), (-2, 1)]
        ring = {t: ("river" if t == (3, -1) else "plains") for b_ in region for t in ((b_[0] + dq, b_[1] + dr) for dq, dr in hk.NEIGHBOURS) if t not in region}
        lm_at = (1, 0)
        for variant, lm in (("badlands", "raiderstronghold"), ("oasis", "oasisbazaar"), ("canyon", "echocave")):
            needs = [f"{variant}_{x}" for x in ("map", "turned", "landmark", "landmark_b", "low_a", "low_b", "side")]
            if flags.get("only") and not set(needs) & set(flags["only"].split(",")) and flags.get("holes") is None:
                continue
            hk.empty_scene()
            templates = load_templates(tiles)
            tiles_ = {**ring, **{t: variant for t in region}, lm_at: lm}
            if variant == "oasis":
                bazaar_, pool_ = dl.oasis_tiles(set(region))
                print("OASIS", bazaar_, pool_)
                tiles_ = {**ring, **{t: variant for t in region}, bazaar_: lm, pool_: "oasispool"}
            build_map(templates, tiles=tiles_)
            col = bpy.data.collections["map"]
            if variant == "canyon":
                # Holes: straight down over the whole region, a ray must hit ground; and along each edge from outside, a ray must hit a wall.
                bpy.context.view_layer.update()
                dg = bpy.context.evaluated_depsgraph_get()
                missed = hit = 0
                lowest = 0
                for t in region:
                    c = hk.tile_position(*t)
                    for ix in range(-20, 21):
                        for iy in range(-22, 23):
                            q = c + Vector((ix * 0.2 + 0.013, iy * 0.2 + 0.017, 0))  # off the lines where faces meet, which a ray can slip through
                            if gc.tile_at(q.x, q.y) != t:
                                continue
                            ok, loc, *_ = bpy.context.scene.ray_cast(dg, Vector((q.x, q.y, 20)), Vector((0, 0, -1)))
                            hit += ok
                            missed += not ok
                            if not ok:
                                print("HOLE", t, round(q.x - c.x, 2), round(q.y - c.y, 2))
                            lowest = min(lowest, loc.z) if ok else lowest
                print(f"HOLES {missed} of {missed + hit} rays down, lowest {lowest:.2f}")
            draw_effects(col, templates, thin=True)
            focus = Vector((0.5, -1.0, 0))
            stage(focus, 66, 50)
            shot(f"{variant}_map")
            view(focus, 62, 50, math.radians(150))
            shot(f"{variant}_turned")
            at = hk.tile_position(*(bazaar_ if variant == "oasis" else lm_at))
            view(at + Vector((0, 0, 1.0)), 19, 42, -math.pi / 2)
            shot(f"{variant}_landmark")
            view(at + Vector((0, 0, 1.0)), 19, 34, math.radians(20))
            shot(f"{variant}_landmark_b")
            if variant == "canyon":
                mid = hk.tile_position(0, 0)
                view(mid + Vector((0, 0, -0.5)), 24, 25, -math.pi / 2)
                shot("canyon_low_a")
                view(mid + Vector((0, 0, -0.5)), 20, 14, math.radians(-40))
                shot("canyon_low_b")
                view(Vector((0, 0, -0.5)), 44, 6, -math.pi / 2)
                shot("canyon_side")
        sys.exit(0)
    if "canyon-takes" in flags:
        # The two canyon takes for Ethan, each from the map camera and low, with a party on it and the Echo Cave. See canyon_takes.py.
        import canyon_takes as ct

        def shot(stem):
            if not flags.get("only") or stem in flags["only"].split(","):
                render(stem)

        def view(focus_, dist_, el_deg, ang):
            el = math.radians(el_deg)
            cam = bpy.context.scene.camera
            cam.location = focus_ + Vector((dist_ * math.cos(el) * math.cos(ang), dist_ * math.cos(el) * math.sin(ang), dist_ * math.sin(el)))
            cam.rotation_euler = (math.pi / 2 - el, 0, ang + math.pi / 2)

        region = [(0, 0)] + list(hk.NEIGHBOURS) + [(1, 1), (2, -1), (1, -2), (-1, 2), (-2, 1)]
        ring = {t: ("river" if t == (3, -1) else "plains") for b_ in region for t in ((b_[0] + dq, b_[1] + dr) for dq, dr in hk.NEIGHBOURS) if t not in region}
        lm_at = (1, 0)
        for take in flags.get("takes", "a,b").split(","):
            hk.empty_scene()
            templates = load_templates(tiles)
            minis = load_templates(max(glob.glob(os.path.join(hk.ART, "minis", "standins", "standin_minis_v*.blend")), key=lambda f: int(re.search(r"_v(\d+)", f).group(1))))
            build_map(templates, tiles=dict(ring), hollow=region)
            col = bpy.data.collections["map"]
            p = hk.Piece(f"canyon_{take}")
            rng = random.Random(7)
            at = hk.tile_position(*lm_at)
            if take == "a":
                t_ = sand.sphinx_turn(lm_at, set(region))
                ct.build_a(p, rng, region, lm_at, t_)
                p.finish(col)
                south = min(region, key=lambda t: (hk.tile_position(*t).y, t))
                spots = []
                for t, e, d in ((south, 5, 2.4), ((0, 0), 0, 1.7), ((-1, 0), 2, 1.2)):
                    c = hk.tile_position(*t)
                    q = wt.mul(wt.normal(e), d)
                    spots.append(((c.x + q[0], c.y + q[1], ct.floor_a(set(region), t, q)), math.radians(60 * e + 180)))
                q = wt.turned(ct.ECHO_STOP_A, t_)
                spots.append(((at.x + q[0], at.y + q[1], ct.floor_a(set(region), lm_at, q)), math.radians(60 * t_ + 180)))
            else:
                info = ct.build_b(p, rng, region, lm_at)
                p.finish(col)
                spots = []
                chain = [t for t in info["tiles"] if info["plan"].get(t, {}).get("bridge")]
                for t in chain[:2]:
                    a, b = info["plan"][t]["hubs"]
                    spots.append((((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0.0), math.atan2(b[1] - a[1], b[0] - a[0])))
                off = [t for t in region if t not in info["tiles"]]
                if off:
                    c = hk.tile_position(*off[0])
                    spots.append(((c.x, c.y, 0.0), 0.5))
                q = wt.turned((ct.ECHO_STOP_B[0], ct.ECHO_STOP_B[1] * info["flip"]), info["turn"])
                spots.append(((at.x + q[0], at.y + q[1], ct.FLOOR_B), math.radians(60 * info["turn"] + 180)))
                print("CHAIN", info["tiles"])
            ct._mini_spots(col, minis, spots)
            focus = Vector((0.5, -1.0, 0))
            stage(focus, 66, 50)
            shot(f"canyon_take_{take}_map")
            view(focus, 62, 50, math.radians(150))
            shot(f"canyon_take_{take}_turned")
            mid = hk.tile_position(0, 0)
            view(mid + Vector((0, 0, -0.5)), 24, 28, -math.pi / 2)
            shot(f"canyon_take_{take}_low")
            view(mid + Vector((0, 0, -0.5)), 18, 14, math.radians(-40))
            shot(f"canyon_take_{take}_lower")
            view(at + Vector((0, 0, 0.5)), 19, 40, math.radians(60 * (t_ if take == "a" else info["turn"])))
            shot(f"canyon_take_{take}_cave")
            view(Vector((0, 0, -0.5)), 44, 6, -math.pi / 2)
            shot(f"canyon_take_{take}_side")
        sys.exit(0)
    if "canyon-maze" in flags:
        # The canyon as chosen (canyon.py): a maze walked on the floor, with a party on it, from the map camera, turned, low and close; triangles per tile, and each entrance ramp's two ends against what's under them.
        import canyon as cn
        region = [(0, 0)] + list(hk.NEIGHBOURS) + [(1, 1), (2, -1), (1, -2), (-1, 2), (-2, 1)]
        ring = {t: ("river" if t == (3, -1) else "plains") for b_ in region for t in ((b_[0] + dq, b_[1] + dr) for dq, dr in hk.NEIGHBOURS) if t not in region}
        lm_at = (1, 0)
        turn_ = sand.sphinx_turn(lm_at, set(region))

        def shot(stem):
            if not flags.get("only") or stem in flags["only"].split(","):
                render(stem)

        def view(focus_, dist_, el_deg, ang):
            el = math.radians(el_deg)
            cam = bpy.context.scene.camera
            cam.location = focus_ + Vector((dist_ * math.cos(el) * math.cos(ang), dist_ * math.cos(el) * math.sin(ang), dist_ * math.sin(el)))
            cam.rotation_euler = (math.pi / 2 - el, 0, ang + math.pi / 2)

        hk.empty_scene()
        templates = load_templates(tiles)
        minis = load_templates(max(glob.glob(os.path.join(hk.ART, "minis", "standins", "standin_minis_v*.blend")), key=lambda f: int(re.search(r"_v(\d+)", f).group(1))))
        build_map(templates, tiles=dict(ring), hollow=region)
        col = bpy.data.collections["map"]
        import canyon_takes as ct
        p = hk.Piece("canyon")
        field = cn.build(p, random.Random(7), region, lm_at, turn_)
        tris = sum(len(f.verts) - 2 for f in p.bm.faces)
        print(f"CANYON {tris} triangles, {tris / len(region):.0f} a tile, entrances {field.entrances}")
        p.finish(col)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        bad_ = 0
        for t, i in field.entrances:
            c = hk.tile_position(*t)
            line = cn.ramp_line(t, i, lm_at, turn_)
            n = wt.normal(i)
            ok, loc, *_ = bpy.context.scene.ray_cast(dg, Vector((c.x + line[0][0] + n[0] * 0.15, c.y + line[0][1] + n[1] * 0.15, 20)), Vector((0, 0, -1)))
            ok2, loc2, *_ = bpy.context.scene.ray_cast(dg, Vector((c.x + line[-1][0] + 0.02, c.y + line[-1][1] + 0.02, 20)), Vector((0, 0, -1)))
            print("RAMP", t, i, "tilt", round(cn.ramp_tilt(line), 1), "outside ground", round(loc.z, 2) if ok else None, "foot floor", round(loc2.z, 2) if ok2 else None)
            if not ok or abs(loc.z) > 0.08 or not ok2 or abs(loc2.z - cn.FLOOR) > 0.08:
                bad_ += 1
        missed = 0
        for t in region:
            c = hk.tile_position(*t)
            for ix in range(-20, 21):
                for iy in range(-22, 23):
                    q = c + Vector((ix * 0.2 + 0.013, iy * 0.2 + 0.017, 0))
                    if gc.tile_at(q.x, q.y) == t and not bpy.context.scene.ray_cast(dg, Vector((q.x, q.y, 20)), Vector((0, 0, -1)))[0]:
                        missed += 1
        print(f"RAMPS NOT JOINED {bad_}; HOLES {missed}")
        spots = []
        t, i = field.entrances[0]
        c = hk.tile_position(*t)
        rl = cn.ramp_line(t, i, lm_at, turn_)
        q = rl[1]
        spots.append(((c.x + q[0], c.y + q[1], q[2]), math.atan2(rl[2][1] - q[1], rl[2][0] - q[0])))
        for t in sorted(region, key=lambda t_: -len(cn.tile_lines(t_, field.openset, field.entrances, lm_at, turn_)))[:3]:
            if t == lm_at:
                continue
            c = hk.tile_position(*t)
            jn = cn.junction(t)
            spots.append(((c.x + jn[0], c.y + jn[1], cn.FLOOR), 0.6))
        q = wt.turned(cn.STOP, turn_)
        at = hk.tile_position(*lm_at)
        spots.append(((at.x + q[0], at.y + q[1], cn.FLOOR), math.radians(60 * turn_ + 180)))
        ct._mini_spots(col, minis, spots)
        focus = Vector((0.5, -1.0, -0.5))
        stage(focus, 66, 50)
        shot("canyon_maze_map")
        view(focus, 62, 50, math.radians(150))
        shot("canyon_maze_turned")
        view(focus, 62, 50, math.radians(30))
        shot("canyon_maze_turned_b")
        mid = hk.tile_position(0, 0)
        view(mid + Vector((0, 0, -1.0)), 22, 28, -math.pi / 2)
        shot("canyon_maze_low")
        view(mid + Vector((0, 0, -1.0)), 22, 28, math.radians(90))
        shot("canyon_maze_low_turned")
        view(mid + Vector((0, 0, -1.0)), 15, 15, math.radians(-40))
        shot("canyon_maze_lower")
        view(mid + Vector((0, 0, -1.0)), 15, 15, math.radians(130))
        shot("canyon_maze_lower_turned")
        view(at + Vector((0, 0, -1.0)), 15, 32, math.radians(60 * turn_))
        shot("canyon_maze_cave")
        rq = hk.tile_position(*field.entrances[0][0])
        view(rq + Vector((0, 0, -0.5)), 13, 30, math.radians(60 * field.entrances[0][1] + 40))
        shot("canyon_maze_ramp")
        # each entrance's lane in the real rock: from the map camera close to, and low from inside the corridor looking up it toward the land
        for k_, (t_, i_) in enumerate(field.entrances[:3]):
            c_ = hk.tile_position(*t_)
            rl_ = cn.ramp_line(t_, i_, lm_at, turn_)
            mid_ = c_ + Vector((rl_[1][0], rl_[1][1], rl_[1][2]))
            view(mid_, 14, 50, -math.pi / 2)
            shot(f"canyon_lane_close_{k_}")
            foot_ = c_ + Vector((rl_[2][0], rl_[2][1], rl_[2][2] + 0.9))
            cam = bpy.context.scene.camera
            cam.data.lens = 24
            look_at(cam, foot_, mid_ + Vector((0, 0, 0.5)))
            shot(f"canyon_lane_up_{k_}")
            cam.data.lens = 50
        view(Vector((0, 0, -0.5)), 44, 6, -math.pi / 2)
        shot("canyon_maze_side")
        sys.exit(0)
    if "stronghold-alone" in flags:
        # The Raider Stronghold on its own, on a bare tile, from several angles.
        hk.empty_scene()
        templates = load_templates(tiles)
        col = hk.new_collection("map")
        base = place(templates, "base_desert", col, Vector((0, 0, 0)))
        base.material_slots[0].link = "OBJECT"
        base.material_slots[0].material = hk.material("badlands_ground")
        place(templates, "raiderstronghold_centre", col, Vector((0, 0, 0)), math.radians(60 * dl.STRONGHOLD_TURN))
        draw_effects(col, templates, thin=True)
        stage(Vector((0, 0, 1.0)), 14, 50)
        cam = bpy.context.scene.camera
        for stem, ang, elev, dist in (("front", -30, 25, 14), ("corner", 45, 30, 14), ("side", 120, 25, 14), ("back", 200, 30, 14), ("map", -90, 50, 16), ("low", -60, 8, 12), ("ramp", -110, 22, 10), ("ramp_low", -135, 5, 8)):
            a_, e_ = math.radians(ang), math.radians(elev)
            cam.location = Vector((dist * math.cos(e_) * math.cos(a_), dist * math.cos(e_) * math.sin(a_), 1.2 + dist * math.sin(e_)))
            look_at(cam, cam.location, Vector((0, 0, 1.4)))
            render(f"badlands_stronghold_alone_{stem}")
        sys.exit(0)
    if "river2" in flags:
        # River/lake round 2 (and the River Port's ground): each variant at map zoom with its routes, and its landmark close to.
        prefix = "trial_" if "trial" in flags else ""

        def shot(stem):
            if not flags.get("only") or stem in flags["only"].split(","):
                render(f"{prefix}{stem}")

        def needs(*stems):
            return not flags.get("only") or any(s_ in flags["only"].split(",") for s_ in stems)

        turned_map = lambda t_: [vr.terrain_of(n_) == "river" if n_ else False for n_ in t_]  # noqa: E731

        def close_to(at_, ang, dist_=13, el_=35):
            a_, el = ang, math.radians(el_)
            cam = bpy.context.scene.camera
            cam.location = at_ + Vector((dist_ * math.cos(el) * math.cos(a_), dist_ * math.cos(el) * math.sin(a_), 1.0 + dist_ * math.sin(el)))
            cam.rotation_euler = (math.pi / 2 - el, 0, a_ + math.pi / 2)

        def spin_cam(focus_, dist_, ang):
            """The map camera turned about the map's focus: the same height and distance, from another side."""
            el = math.radians(50)
            cam = bpy.context.scene.camera
            cam.location = focus_ + Vector((dist_ * math.cos(el) * math.cos(ang), dist_ * math.cos(el) * math.sin(ang), dist_ * math.sin(el)))
            cam.rotation_euler = (math.pi / 2 - el, 0, ang + math.pi / 2)

        # the River Port: the delta from the default camera and turned, close to, and with water at its back
        if needs("river_delta_map", "river_delta_map_turned", "river_riverport_closeup", "river_riverport_closeup_back"):
            hk.empty_scene()
            templates = load_templates(tiles)
            build_map(templates, tiles=DELTA_MAP)
            draw_effects(bpy.data.collections["map"], templates, thin=True)
            stage(Vector((0.5, -0.8, 0)), 56, 50)
            shot("river_delta_map")
            spin_cam(Vector((0.5, -0.8, 0)), 56, math.radians(150))
            shot("river_delta_map_turned")
            near_ = [DELTA_MAP.get((LANDMARK_AT[0] + dq, LANDMARK_AT[1] + dr)) for dq, dr in hk.NEIGHBOURS]
            t = wt.port_turn(turned_map(near_), f"{LANDMARK_AT[0]},{LANDMARK_AT[1]}")
            at = hk.tile_position(*LANDMARK_AT)
            close_to(at, math.radians(60 * t))
            shot("river_riverport_closeup")
            close_to(at, math.radians(60 * t + 180))
            shot("river_riverport_closeup_back")
        if needs("river_port_gate_map", "river_port_gate_closeup"):
            hk.empty_scene()
            templates = load_templates(tiles)
            build_map(templates, tiles=PORT_GATE_MAP)
            stage(Vector((0.5, -0.8, 0)), 50, 50)
            shot("river_port_gate_map")
            mask = turned_map([PORT_GATE_MAP.get((dq, dr)) for dq, dr in hk.NEIGHBOURS])
            t = wt.port_turn(mask, "0,0")
            back = next((k + t) % 6 for k in (2, 3, 4) if mask[(k + t) % 6])
            n_ = hk.edge_normal(back)
            at = n_ * 3.9
            look_at(bpy.context.scene.camera, at + n_ * 6.5 + Vector((0, 0, 4.5)), at + Vector((0, 0, 0.5)))
            shot("river_port_gate_closeup")
        for stem, tiles_map, focus, lm_at, lm in (("river_lake", LAKE_MAP, Vector((0, -0.5, 0)), LANDMARK_AT, "serpentlair"), ("river_rapids", RAPIDS_MAP, Vector((0, 0, 0)), (0, 0), "trollbridge"),
                                                  ("river_still", STILL_MAP, Vector((2, -1, 0)), (1, 0), "meditationrock")):
            for paths in (False, True):
                if not needs(f"{stem}_{'paths' if paths else 'map'}", f"{stem}_closeup", f"{stem}_closeup_b", f"{stem}_turned"):
                    continue
                hk.empty_scene()
                templates = load_templates(tiles)
                build_map(templates, tiles=tiles_map)
                draw_effects(bpy.data.collections["map"], templates, thin=True)
                near_ = [tiles_map.get((lm_at[0] + dq, lm_at[1] + dr)) for dq, dr in hk.NEIGHBOURS]
                mask = turned_map(near_)
                widths = wt.edge_widths(lm, [n_ and vr.wedges_of(n_) for n_ in near_])
                seed = f"{lm_at[0]},{lm_at[1]}"
                if paths:
                    if lm == "serpentlair":
                        region = {t_ for t_, n_ in tiles_map.items() if n_ in ("great_lake", lm)}
                        d_, to_ = lf.flow(region, lm_at)
                        lair_turn[lm_at] = lf.turn(lm_at, d_, to_)
                    water_lines(tiles_map)
                stage(focus, 62, 50)
                shot(f"{stem}_{'paths' if paths else 'map'}")
                if paths:
                    continue
                spin_cam(focus, 62, math.radians(150))
                shot(f"{stem}_turned")
                at = hk.tile_position(*lm_at)
                if lm == "serpentlair":
                    region = {t_ for t_, n_ in tiles_map.items() if n_ in ("great_lake", lm)}
                    d_, to_ = lf.flow(region, lm_at)
                    ang = math.radians(60 * lf.turn(lm_at, d_, to_))
                elif lm == "trollbridge":
                    mid, ang_, _ = wt.bridge_spot(mask, seed, widths, wt.TROLL_HALF)
                    at = at + Vector((mid[0], mid[1], 0))
                    ang = ang_ - math.pi / 2
                else:
                    ang = math.radians(60 * (wt.rock_routes(mask, seed, widths)[3] or 0))
                close_to(at, ang)
                shot(f"{stem}_closeup")
                close_to(at, ang + math.pi * 0.9)
                shot(f"{stem}_closeup_b")
        sys.exit(0)
    if "keep-alone" in flags:
        # The Keep on its own, on a bare tile, from several angles: its proportions without the town round it.
        prefix = "trial_" if "trial" in flags else ""
        hk.empty_scene()
        templates = load_templates(tiles)
        col = hk.new_collection("map")
        base = place(templates, "base_village", col, Vector((0, 0, 0)))
        place(templates, "keep_centre", col, Vector((0, 0, 0)))
        stage(Vector((0, 0, 1.0)), 14, 50)
        cam = bpy.context.scene.camera
        for stem, ang, elev, dist in (("front", 0, 25, 13), ("corner", 45, 30, 13), ("side", 90, 25, 13), ("back", 180, 30, 13),
                                      ("map", -60, 50, 15), ("low", 20, 8, 11)):
            a_, e_ = math.radians(ang), math.radians(elev)
            cam.location = Vector((dist * math.cos(e_) * math.cos(a_), dist * math.cos(e_) * math.sin(a_), 1.2 + dist * math.sin(e_)))
            look_at(cam, cam.location, Vector((0, 0, 1.2)))
            render(f"{prefix}village_keep_alone_{stem}")
        sys.exit(0)
    if "slum-option" in flags:
        # One ground option for the slums (build with env HEX_SLUM): the region at map zoom and a low look along a street.
        opt = flags["slum-option"]
        prefix = "trial_" if "trial" in flags else ""
        hk.empty_scene()
        templates = load_templates(tiles)
        build_map(templates, tiles=TOWN_T2["blackmarket"])
        draw_effects(bpy.data.collections["map"], templates, thin=True)
        stage(Vector((0.5, -0.8, 0)), 54, 50)
        render(f"{prefix}village_slums_ground_{opt}_map")
        cam = bpy.context.scene.camera
        el = math.radians(35)
        at = hk.tile_position(0, 0)
        cam.location = at + Vector((0, -11 * math.cos(el), 1.0 + 11 * math.sin(el)))
        cam.rotation_euler = (math.pi / 2 - el, 0, 0)
        render(f"{prefix}village_slums_ground_{opt}_closeup")
        sys.exit(0)
    if "village" in flags:
        # Village streets: a tier 0 group with farms beside it, with the paths drawn; market town flowing into the Trading
        # House, with the paths drawn; low close-ups of a street, a gate and the landmark.
        prefix = "trial_" if "trial" in flags else ""
        el = math.radians(38)

        def shot(stem):
            if not flags.get("only") or stem in flags["only"].split(","):
                render(f"{prefix}{stem}")

        def look(at, a, dist, elev=el, lift=0.6):
            cam = bpy.context.scene.camera
            cam.location = at + Vector((dist * math.cos(elev) * math.cos(a), dist * math.cos(elev) * math.sin(a), lift + dist * math.sin(elev)))
            cam.rotation_euler = (math.pi / 2 - elev, 0, a + math.pi / 2)

        for stem, tiles_map, focus, dist in (("village_t0", VILLAGE_MAP, Vector((0.5, -0.8, 0)), 58),
                                             ("village_market", MARKET_MAP, Vector((0.5, -0.8, 0)), 54),
                                             ("village_fortified", TOWN_T2["keep"], Vector((0.5, -0.8, 0)), 54),
                                             ("village_slums", TOWN_T2["blackmarket"], Vector((0.5, -0.8, 0)), 54),
                                             ("village_scholars", TOWN_T2["college"], Vector((0.5, -0.8, 0)), 54),
                                             ("village_fortified_join", FORT_JOIN_MAP, Vector((0.5, -0.8, 0)), 58),
                                             ("village_fortified_12", FORT_12_MAP, DENSITY_VIEW, 74)):
            for paths in (True, False):
                hk.empty_scene()
                templates = load_templates(tiles)
                build_map(templates, tiles=tiles_map)
                draw_effects(bpy.data.collections["map"], templates, thin=True)
                if paths:
                    draw_paths(bpy.data.collections["map"], templates)
                stage(focus, dist, 50)
                shot(f"{stem}_{'paths' if paths else 'map'}")
            if stem == "village_t0":
                ax = vs.axis(0, 0)  # along the main street, low, from the middle of the tile looking out
                look(hk.tile_position(0, 0) + hk.edge_normal(ax) * 7.5, math.radians(60 * ax), 8, math.radians(28), 0.4)
                shot("village_street_closeup")
                g = fg.fence_gates({k: vr.terrain_of(n) for k, n in tiles_map.items()})
                t, edges = next((t, e) for t, e in sorted(g.items()) if e and tiles_map[t] == "village")
                a = math.radians(60 * edges[0])
                look(hk.tile_position(*t) + Vector((math.cos(a), math.sin(a), 0)) * 3.3, a + math.pi, 9)
                shot("village_gate_closeup")
            else:
                lm = tiles_map.get(LANDMARK_AT)  # (only the 7-tile maps have it there)
                if lm in vr.LANDMARKS and stem in ("village_market", "village_fortified", "village_slums", "village_scholars"):
                    d, tw = lf.flow(set(t for t, n in tiles_map.items() if n in (vr.LANDMARKS[lm], lm)), LANDMARK_AT)
                    look(hk.tile_position(*LANDMARK_AT), math.radians(60 * lf.turn(LANDMARK_AT, d, tw)), 15, lift=1.2)
                    shot(f"village_{lm}_closeup")
        sys.exit(0)
    if "raised-scenes" in flags:
        # Raised regions meeting other things: tiles added to a finished region, two regions touching, a region with no
        # walkable land beside it, and the rise halfway through.
        prefix = "trial_" if "trial" in flags else ""

        def scene(stem, tiles_map, regions, progress=1.0, flows=None, foot=False, top=False):
            if flags.get("only") and stem not in flags["only"].split(","):
                return
            hk.empty_scene()
            templates = load_templates(tiles)
            build_map(templates, tiles=tiles_map, raised_regions=regions, flows=flows)
            col = bpy.data.collections["map"]
            climbs = raise_region(templates, col, tiles_map, regions, progress)
            print("CLIMBS", stem, climbs)
            draw_effects(col, templates)
            centre = sum((hk.tile_position(*t) for r_, _ in regions for t in r_), Vector()) / sum(len(r_) for r_, _ in regions)
            stage(centre + Vector((0, -1.5, 2.0)), 66 if len(regions) == 1 else 88, 50)
            render(f"{prefix}{stem}")
            if top:  # where each ledge comes out, from above the plateau
                cam = bpy.context.scene.camera
                cam.data.lens = 24
                for k, (t, i) in enumerate(climbs):
                    out, along = hk.edge_normal(i + 1), hk.edge_normal(i + 1 + 1.5)
                    exit_ = hk.tile_position(*t) + out * vr.LEDGE_X + along * vr.climb_heights()[2] + Vector((0, 0, vr.RAISE))
                    look_at(cam, exit_ - out * 1.5 - along * 7.5 + Vector((0, 0, 6.5)), exit_ + along * 0.5 - Vector((0, 0, 1.5)))
                    render(f"{prefix}{stem}_{'abcdefgh'[k]}_top")
            if foot:  # the gate in front of a ledge's foot, from behind the gate
                cam = bpy.context.scene.camera
                cam.data.lens = 24
                draw_paths(col, templates)
                t, i = climbs[0]
                out, along = hk.edge_normal(i - 1), hk.edge_normal(i - 1 + 1.5)
                at = hk.tile_position(*t) + out * vr.X1 + along * vr.foot_y()
                look_at(cam, at + out * 6 - along * 2.5 + Vector((0, 0, 3.5)), at + along * 1.0 + Vector((0, 0, 1.0)))
                render(f"{prefix}{stem}_foot")

        base = {**FLOW_RING, **{t: ("yeticave" if t == LANDMARK_AT else "snowy_peaks") for t in LANDMARK_REGION}}
        before = {t: n for t, n in base.items() if t not in ((-2, 1), (0, 2))}
        scene("hills_snowy_added_before_raised", before, [(LANDMARK_REGION, "snowy_peaks")])
        added = LANDMARK_REGION + [(-2, 1)]
        # The old tiles keep their trails and the landmark its turn; only the added tile gets its own (landmark_flow.extend).
        old_dist, old_toward = lf.flow(set(LANDMARK_REGION), LANDMARK_AT)
        old_turn = lf.turn(LANDMARK_AT, old_dist, old_toward)
        lf.extend((-2, 1), old_dist, old_toward)
        scene("hills_snowy_added_after_raised", {**before, (-2, 1): "snowy_peaks", (0, 2): "forest"}, [(added, "snowy_peaks")],
              flows={LANDMARK_AT: (old_dist, old_toward, old_turn)})
        second = [(q + 3, r) for q, r in LANDMARK_REGION]
        both = {**FLOW_RING, **{t: "plains" for s_ in second for t in ((s_[0] + dq, s_[1] + dr) for dq, dr in hk.NEIGHBOURS)},
                **{t: ("yeticave" if t == LANDMARK_AT else "snowy_peaks") for t in LANDMARK_REGION},
                **{t: ("salamanderden" if t == (4, -1) else "volcanic_peaks") for t in second}}
        scene("hills_touching_raised", both, [(LANDMARK_REGION, "snowy_peaks"), (second, "volcanic_peaks")])
        river = {**{t: "river" for t in FLOW_RING}, **{t: ("yeticave" if t == LANDMARK_AT else "snowy_peaks") for t in LANDMARK_REGION}}
        scene("hills_ringed_raised", river, [(LANDMARK_REGION, "snowy_peaks")], foot=True)  # a ledge's foot on the water
        scene("hills_snowy_rising_raised", base, [(LANDMARK_REGION, "snowy_peaks")], 0.5)
        fenced = {**{t: "farmland" for t in FLOW_RING}, **{t: ("yeticave" if t == LANDMARK_AT else "snowy_peaks") for t in LANDMARK_REGION}}
        # Ground-level hills beside a raised region: all the land round it, so every ledge's foot faces them.
        for stem, low in (("hills_snowy_beside_highlands_raised", "highlands"), ("hills_snowy_beside_tier0_raised", "hills"),
                          ("hills_volcanic_beside_monastery_raised", "monastery_heights")):
            up, lm = ("volcanic_peaks", "salamanderden") if "volcanic" in stem else ("snowy_peaks", "yeticave")
            scene(stem, {**{t: low for t in FLOW_RING}, **{t: (lm if t == LANDMARK_AT else up) for t in LANDMARK_REGION}},
                  [(LANDMARK_REGION, up)], foot=True)
        scene("hills_fenced_foot_raised", fenced, [(LANDMARK_REGION, "snowy_peaks")], foot=True)
        # A big region, so most tiles are far enough from the landmark for ridges: no ridges where a ledge comes out.
        big = [(q, r) for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3]
        rim = {t: "plains" for b_ in big for t in ((b_[0] + dq, b_[1] + dr) for dq, dr in hk.NEIGHBOURS) if t not in big}
        for stem, up, lm in (("hills_snowy_big_raised", "snowy_peaks", "yeticave"), ("hills_volcanic_big_raised", "volcanic_peaks", "salamanderden")):
            scene(stem, {**rim, **{t: (lm if t == (-3, 3) else up) for t in big}}, [(big, up)], top=True)
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
