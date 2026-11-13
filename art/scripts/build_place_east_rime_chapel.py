"""East Rime Chapel, the Acolyte's starting tile, as a place scene (design/07 -> Town screen -> Each place gets its own scene;
plan in the shared notes, place-scenes/plan.md), from the approved start tile (tiles_v89, start_tiles.py: 07 -> Starting
tiles, "a hilltop chapel with walled graves"). Dunfaire Tower's kit (build_place_dunfaire_tower.py) for the 19 hexes, the
floor, the checks and the view 2 rows back. v2 (Ethan, Nov 10, 2026) made it a close look at the chapel's walled courtyard
on the levelled hilltop, the hill stepping down in terraces beyond the wall, as on the hills combat maps. v3 (Ethan, Nov 12,
2026: 07 -> Built for the zoom) builds every piece here at scene scale, in metres against the 1.3 m minis, and lays the
yard out on the hexes: the paths are runs of worn and paved cells, the wall runs along hex edges, and the chapel's raised
plinth, its steps, the graves, the beds, the well and the shrine each fill whole cells.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_place_east_rime_chapel.py
Writes art/places/place_east_rime_chapel_vN.blend (mesh place_east_rime_chapel) and art/export/place_east_rime_chapel.json.
Export the glb with export_gltf.py. Previews and checks: render_place_scenes.py -- east_rime_chapel [check].
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build_place_dunfaire_tower as dt  # noqa: E402
import build_place_fortified_town as pf  # noqa: E402
import build_town_scenes as bs  # noqa: E402
import hexkit as hk  # noqa: E402
import town_scene_studies as ts  # noqa: E402

ID = "east_rime_chapel"
MESH = f"place_{ID}"
R, A, hx, HEXES, FLOOR_Z = ts.R, ts.A, ts.hx, ts.HEXES, bs.FLOOR_Z

# The view and the party's spots as Dunfaire Tower's (Ethan, Nov 10, 2026: the place is the focus, so it must be in view).
VIEW_SHIFT = dt.VIEW_SHIFT
# PLACEHOLDER: the chapel's cards (Rest and Swap party, Nov 10, 2026) aren't hooked up. "none" as Dunfaire's; "chapel"
# gathers the party on the paved forecourt before the steps.
SPOTS = {ID: {"none": dt.SPOTS[dt.ID]["none"], "chapel": [[1, -2], [0, -2], [2, -2], [1, -1]]}}
KEEPERS = {ID: {}}
PLACES = {"chapel": [1, -3]}
FLOOR = pf.FLOOR
STEP = 0.3             # each terrace down from the hilltop
# The god's colours and symbol follow the god the player chose (Ethan, Nov 12, 2026): their own materials, so the engine
# can swap them. PLACEHOLDER colours until the gods' colours are set.
hk.PALETTE.update({"god_cloth": "#F2EEE2", "god_trim": "#3F6C9B", "god_symbol": "#E8C04A"})
hk.OWN_MATERIAL = set(hk.OWN_MATERIAL) | {"god_cloth", "god_trim", "god_symbol"}

# The yard, cell by cell. Inside the wall: every floor hex from row 1 back to row -6 within 4.8 m of the middle.
COURT = {h for h in FLOOR if -6 <= h[1] <= 1 and abs(hx(*h).x) <= 4.8}
GAP = (-1, 2)          # the cell outside the wall's front gap, where the path leaves the yard
CELLS = {}
for _kind, _cells in (
        ("earth", ((-1, 2), (-1, 1), (0, 1), (0, 0), (-1, 0), (2, -1))),        # worn paths: gate to forecourt, to the graves, to the well
        ("paved", ((0, -1), (1, -1), (0, -2), (1, -2), (2, -2))),               # the forecourt before the steps
        ("step", ((1, -3), (2, -3))),
        ("plinth", ((1, -4), (2, -4), (3, -4), (1, -5), (2, -5), (3, -5), (4, -5), (2, -6), (3, -6), (4, -6))),
        ("grave", ((-3, 1), (-2, 1), (-2, 0), (-2, -1), (-1, -1), (-1, -2), (-1, -3), (0, -3), (0, -4), (1, -6))),
        ("tomb", ((0, -5),)),
        ("bed", ((1, 1), (2, 1), (2, 0), (4, -3))),
        ("well", ((3, -1),)), ("shrine", ((3, -2),)), ("wood", ((5, -5),))):
    for _h in _cells:
        CELLS[_h] = _kind
RAISE = {"step": 0.22, "plinth": 0.45, "shrine": 0.28}
PLINTH_Z = FLOOR_Z + RAISE["plinth"]
CH_Y, CH_W, CH_D, CH_H = 6.0, 4.8, 4.4, 3.3   # the chapel on its plinth: front face, width, depth, wall height
# Lights (Blender's frame and watts, as the town kit's), at night: the door's lantern, the lamps at the wall's gap, the
# shrine's candles (flickering); the windows glow.
LIGHTS = [(Vector((1.0, CH_Y - 0.35, PLINTH_Z + 2.0)), "#FFD27A", 0.0, 30.0, False),
          (Vector((-1.1, -2.4, 1.7)), "#FFD27A", 0.0, 22.0, False), (Vector((1.1, -2.4, 1.7)), "#FFD27A", 0.0, 22.0, False),
          (hx(3, -2) + Vector((0, -0.7, 0.7)), "#FFB25A", 0.0, 14.0, True)]
BACKDROP = ""
NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))


def levels():
    """Each floor hex's drop below the hilltop: the yard level, then a terrace per hex out from it, four at most."""
    out = {h: 0 for h in COURT}
    ring = list(out)
    while ring:
        nxt = []
        for q, r in ring:
            for dq, dr in NEIGHBOURS:
                h = (q + dq, r + dr)
                if h in FLOOR and h not in out:
                    out[h] = min(out[(q, r)] + 1, 4)
                    nxt.append(h)
        ring = nxt
    return out


LEVEL = levels()


def z_at(x, y):
    """The ground's height under (x, y): the top of the floor hex it stands on."""
    q, r = min(FLOOR, key=lambda h: (hx(*h) - Vector((x, y, 0))).length)
    return FLOOR_Z - STEP * LEVEL[(q, r)] + RAISE.get(CELLS.get((q, r)), 0.0)


def outline(c, k, z=None):
    return [c + Vector((R * k * math.cos(math.radians(60 * j + 30)), R * k * math.sin(math.radians(60 * j + 30)), 0)) for j in range(6)]


def slabs(p, rng, c, z, mats):
    """Paving on a cell: a flower of seven hex slabs, a little uneven, the dark ground showing between them as joints."""
    for k in range(7):
        at = c if k == 0 else c + Vector((0.6 * math.cos(math.radians(60 * k)), 0.6 * math.sin(math.radians(60 * k)), 0))
        s = rng.uniform(0.27, 0.31)
        p.prism(outline(at, s / R), z - 0.02, z + 0.025 + rng.uniform(0, 0.015), rng.choice(mats))


def cells(p, rng):
    """The floor, cell by cell (build_town_scenes.floor's prisms): each at its terrace's height, the drops faced in hill
    rock; worn earth and paved cells for the paths, the steps and the chapel's plinth raised in stone."""
    for q, r in FLOOR:
        c, dz = hx(q, r), -STEP * LEVEL[(q, r)]
        kind = CELLS.get((q, r), "grass")
        p.prism(outline(c, 0.992), -2.0, -0.015 + dz, "ts_base_d", side_mat="rock_dark")
        top = FLOOR_Z + dz + RAISE.get(kind, 0.0)
        if kind in RAISE:
            p.prism(outline(c, 0.985), -0.34 + dz, top, "stone_step" if kind != "shrine" else "stone_block", side_mat="st_stone_d")
            if kind != "plinth":
                slabs(p, rng, c, top, ("st_stone_l", "stone_step", "stone_tan"))
            continue
        mat = {"earth": "path_earth", "paved": "flagstone"}.get(kind) or ("ts_grass_d" if random.Random(q * 101 + r).random() < 0.22 else "ts_grass")
        p.prism(outline(c, 0.965), -0.34 + dz, top, mat, side_mat="ts_base_d")
        if kind == "paved":
            slabs(p, rng, c, top, ("st_stone_l", "stone_step", "stone_tan"))
        elif kind == "earth":  # bare earth worn by feet, a few stones, grass creeping in at the rim
            for j in rng.sample(range(6), 2):
                a = math.radians(60 * j + 30)
                p.cone(c + Vector((0.72 * math.cos(a), 0.72 * math.sin(a), 0)), 0.12, 0.16, "ts_grass_d", segments=5, z=top)
            for _ in range(3):
                at = c + Vector((rng.uniform(-0.55, 0.55), rng.uniform(-0.5, 0.5), 0))
                p.blob(at, rng.uniform(0.05, 0.08), "rock", z=top, squash=0.5)


def wall_edge(p, rng, a, b):
    """One hex edge of the dry-stone wall: two courses of uneven stones under flat coping, on a footing that runs down past
    the terrace below."""
    along = (b - a).normalized()
    spin = math.atan2(along.y, along.x)
    length = (b - a).length
    p.box((a + b) / 2, (length, 0.44, 0.9), "rock_light", z=FLOOR_Z - 0.9, spin=spin)
    for zz, hh, off in ((0.0, 0.34, 0.0), (0.32, 0.3, 0.27)):
        cut = length * rng.uniform(0.4, 0.6) if off == 0 else length * rng.uniform(0.25, 0.4)
        for t0, t1 in ((0, cut), (cut, length)):
            at = a + along * (t0 + t1) / 2
            p.box(at, ((t1 - t0) * 0.96, 0.44, hh), rng.choice(("rock_light", "stone_block", "rock", "stone_tan")), z=FLOOR_Z + zz,
                  spin=spin + rng.uniform(-0.04, 0.04))
    for t0, t1 in ((0, length / 2), (length / 2, length)):
        p.box(a + along * (t0 + t1) / 2, ((t1 - t0) * 0.95, 0.52, 0.12), rng.choice(("stone_block_dark", "rock")), z=FLOOR_Z + 0.62,
              spin=spin + rng.uniform(-0.05, 0.05))


def courtyard_wall(p, rng):
    """The wall round the yard along its hex edges, with a plain gap at the front where the path leaves (Ethan, Nov 12,
    2026: no lychgate), a round stone post at each corner and lamp posts either side of the gap."""
    corners = set()
    for c in sorted(COURT):
        for dq, dr in NEIGHBOURS:
            n = (c[0] + dq, c[1] + dr)
            if n in COURT or n == GAP:
                continue
            m = (hx(*c) + hx(*n)) / 2
            d = (hx(*n) - hx(*c)).normalized()
            side = Vector((-d.y, d.x, 0)) * R / 2
            wall_edge(p, rng, m - side, m + side)
            corners |= {(round((m - side).x, 2), round((m - side).y, 2)), (round((m + side).x, 2), round((m + side).y, 2))}
    for x, y in corners:
        p.cylinder(Vector((x, y, 0)), 0.26, 0.78, "stone_block", segments=6, z=FLOOR_Z)
    gate = [hx(*GAP) + Vector((sx * A, 0.55, 0)) for sx in (-1, 1)]
    for g in gate:
        lamp_post(p, g.x * 1.15, g.y + 0.3, FLOOR_Z)


def extrude(p, pts, a0, a1, mat, axis="y"):
    """A convex outline in the wall's own plane (u across, z up), pushed from a0 to a1 along the axis: gables, arches,
    lancets."""
    def v(u, z, a):
        return (u, a, z) if axis == "y" else (a, u, z)
    front = [p.bm.verts.new(v(u, z, a0)) for u, z in pts]
    back = [p.bm.verts.new(v(u, z, a1)) for u, z in pts]
    i = p._slot(mat)
    p.bm.faces.new(front).material_index = i
    p.bm.faces.new(list(reversed(back))).material_index = i
    n = len(pts)
    for k in range(n):
        j = (k + 1) % n
        p.bm.faces.new((front[k], back[k], back[j], front[j])).material_index = i


def lancet(cx, z0, w, h, n=3):
    """A pointed arch's outline: straight sides, then two arcs meeting at the top."""
    out = [(cx - w / 2, z0), (cx + w / 2, z0)]
    spring = z0 + h - w * 0.75
    out += [(cx + w / 2 * math.cos(math.radians(a)), spring + w * 0.75 * math.sin(math.radians(a))) for a in range(0, 90, 90 // n)][:: 1]
    out.append((cx, z0 + h))
    out += [(cx - w / 2 * math.cos(math.radians(a)), spring + w * 0.75 * math.sin(math.radians(a))) for a in range(90 - 90 // n, -1, -90 // n)]
    return out


def chapel(p):
    """The chapel on its raised plinth of hexes: pale stone with darker course bands and a stone gable under slate, stepped
    buttresses, an arched oak door with iron straps, lancet windows and a round window that glow, the bell cote on the
    front gable with its bell and rope, banners in the god's colours either side of the door, and a lantern."""
    z, fy, w, d, h = PLINTH_Z, CH_Y, CH_W, CH_D, CH_H
    by = fy + d / 2
    p.box(Vector((0, by, 0)), (w + 0.16, d + 0.16, 0.3), "st_stone_d", z=z - 0.05)
    p.box(Vector((0, by, 0)), (w, d, h), "st_stone_l", z=z)
    for k in range(1, 6):  # a band of darker course stones every few rows, so it reads as masonry
        p.box(Vector((0, by, 0)), (w + 0.03, d + 0.03, 0.07), "st_stone", z=z + k * 0.55)
    top = z + h
    extrude(p, [(-w / 2, top), (w / 2, top), (0, top + 2.3)], fy, fy + 0.4, "st_stone_l")
    p.gable_roof(Vector((0, by, 0)), d + 0.5, w + 0.7, 2.45, "st_slate", z=top - 0.12, spin=math.pi / 2)
    p.box(Vector((0, by, 0)), (0.16, d + 0.5, 0.14), "slate_dark", z=top + 2.3)
    for sx in (-1, 1):
        for yy in (fy, fy + d):
            x = sx * (w / 2 + 0.2)
            p.box(Vector((x, yy, 0)), (0.46, 0.56, h * 0.62), "st_stone", z=z - 0.05)
            p.box(Vector((x - sx * 0.04, yy, 0)), (0.38, 0.46, h * 0.3), "st_stone", z=z - 0.05 + h * 0.62)
    # the door: a stone arch round an oak door of planks with iron straps and a ring
    extrude(p, lancet(0, z, 1.7, 2.75), fy - 0.12, fy + 0.05, "st_stone")
    extrude(p, lancet(0, z, 1.25, 2.4), fy - 0.16, fy - 0.1, "gate_wood")
    for k in range(-2, 3):
        p.box(Vector((k * 0.25, fy - 0.17, 0)), (0.02, 0.02, 2.0), "plank_dark", z=z)
    for zz in (0.5, 1.5):
        p.box(Vector((0, fy - 0.19, 0)), (1.15, 0.03, 0.08), "iron", z=z + zz)
    p.cylinder(Vector((0.35, fy - 0.2, 0)), 0.07, 0.03, "iron", segments=8, z=z + 1.05)
    # lancet windows each side of the door and down the sides, a round window over the door
    for sx in (-1, 1):
        extrude(p, lancet(sx * 1.55, z + 1.0, 0.7, 1.8), fy - 0.1, fy + 0.05, "st_stone")
        extrude(p, lancet(sx * 1.55, z + 1.1, 0.48, 1.55), fy - 0.14, fy - 0.08, "ts_glow")
        p.box(Vector((sx * 1.55, fy - 0.16, 0)), (0.03, 0.03, 1.4), "iron", z=z + 1.12)
        for yy in (fy + 1.3, fy + 3.1):
            extrude(p, lancet(yy, z + 1.0, 0.7, 1.8), sx * (w / 2 + 0.1), sx * (w / 2 - 0.05), "st_stone", axis="x")
            extrude(p, lancet(yy, z + 1.1, 0.48, 1.55), sx * (w / 2 + 0.14), sx * (w / 2 + 0.08), "ts_glow", axis="x")
    ring = [(0.62 * math.cos(math.radians(a)), top + 0.85 + 0.62 * math.sin(math.radians(a))) for a in range(0, 360, 30)]
    extrude(p, ring, fy - 0.08, fy + 0.05, "st_stone")
    extrude(p, [(u * 0.72, top + 0.85 + (v - top - 0.85) * 0.72) for u, v in ring], fy - 0.12, fy - 0.07, "ts_glow")
    for a in range(0, 180, 45):
        p.box_rot(Vector((0, fy - 0.13, top + 0.85)), (0.9, 0.03, 0.04), "st_stone", Matrix.Rotation(math.radians(a), 3, "Y"))
    # the bell cote on the gable's peak: two piers, a little slate roof, the bell on its beam, its rope down the front
    bz = top + 2.0
    for sx in (-1, 1):
        p.box(Vector((sx * 0.55, fy + 0.15, 0)), (0.28, 0.45, 1.35), "st_stone_l", z=bz)
    p.box(Vector((0, fy + 0.15, 0)), (1.4, 0.5, 0.18), "st_stone", z=bz + 1.35)
    p.gable_roof(Vector((0, fy + 0.15, 0)), 1.6, 0.8, 0.55, "st_slate", z=bz + 1.53)
    p.box(Vector((0, fy + 0.15, 0)), (0.9, 0.1, 0.1), "plank_dark", z=bz + 1.15)
    p.cone(Vector((0, fy + 0.15, 0)), 0.36, 0.6, "bell", segments=10, z=bz + 0.55)
    p.cylinder(Vector((0, fy + 0.15, 0)), 0.36, 0.08, "bell", segments=10, z=bz + 0.52)
    p.cylinder(Vector((0, fy + 0.15, 0)), 0.18, 0.32, "bell", segments=10, z=bz + 0.85)
    p.box(Vector((0.42, fy - 0.08, 0)), (0.025, 0.025, bz + 0.6 - (z + 0.9)), "rope", z=z + 0.9)
    # the god's banners either side of the door: cloth, a stripe and the symbol in their own materials
    for sx in (-1, 1):
        x = sx * 1.55
        p.box(Vector((x, fy - 0.22, 0)), (0.8, 0.04, 0.05), "plank_dark", z=top - 0.25)
        p.box(Vector((x, fy - 0.22, 0)), (0.62, 0.02, 1.25), "god_cloth", z=top - 1.5)
        p.box(Vector((x, fy - 0.235, 0)), (0.62, 0.02, 0.09), "god_trim", z=top - 0.5)
        extrude(p, [(x + 0.16 * math.cos(math.radians(a)), top - 0.95 + 0.16 * math.sin(math.radians(a))) for a in range(0, 360, 45)],
                fy - 0.245, fy - 0.235, "god_symbol")
        extrude(p, [(x - 0.31, top - 1.5), (x + 0.31, top - 1.5), (x, top - 1.75)], fy - 0.23, fy - 0.21, "god_cloth")
    lantern(p, Vector((1.0, fy - 0.35, z + 1.8)), hang=True)


def lantern(p, at, hang=False):
    """A small iron lantern with a lit glass: on a bracket from a wall, or on top of a post."""
    if hang:
        p.box(Vector((at.x, at.y + 0.17, 0)), (0.04, 0.38, 0.04), "iron", z=at.z + 0.42)
    p.box(Vector((at.x, at.y, 0)), (0.22, 0.22, 0.04), "iron", z=at.z)
    p.box(Vector((at.x, at.y, 0)), (0.17, 0.17, 0.26), "ts_glow", z=at.z + 0.04)
    p.cone(Vector((at.x, at.y, 0)), 0.17, 0.14, "iron", segments=4, z=at.z + 0.3, spin=math.pi / 4)


def lamp_post(p, x, y, z):
    p.box(Vector((x, y, 0)), (0.12, 0.12, 1.55), "plank_dark", z=z)
    lantern(p, Vector((x, y, z + 1.55)))


def candle(p, at, z, h=0.18):
    p.cylinder(at, 0.035, h, "st_white", segments=6, z=z)
    p.cone(at, 0.025, 0.07, "ts_glow", segments=4, z=z + h)


def flowers(p, rng, at, z, n=3):
    for _ in range(n):
        f = at + Vector((rng.uniform(-0.12, 0.12), rng.uniform(-0.08, 0.08), 0))
        p.box(f, (0.02, 0.02, 0.18), "herb_a", z=z)
        p.box(f, (0.08, 0.08, 0.06), rng.choice(("flower_red", "flower_white", "flower_yellow", "flower_pink")), z=z + 0.18)


def grave_cell(p, rng, c):
    """Two graves side by side in a cell: warm headstones (arched, pointed or square, some leaning) at the back, a grass
    mound before each, most of them tended with flowers or a candle."""
    for sx in (-1, 1):
        x, y = c.x + sx * 0.42 + rng.uniform(-0.05, 0.05), c.y + 0.42
        w, h = rng.uniform(0.38, 0.5), rng.uniform(0.55, 0.85)
        shape = rng.choice(("round", "round", "point", "flat"))
        if shape == "round":
            pts = [(x - w / 2, 0), (x + w / 2, 0)] + [(x + w / 2 * math.cos(math.radians(a)), h - w / 2 + w / 2 * math.sin(math.radians(a))) for a in range(0, 181, 30)]
        elif shape == "point":
            pts = [(x - w / 2, 0), (x + w / 2, 0), (x + w / 2, h - 0.15), (x, h), (x - w / 2, h - 0.15)]
        else:
            pts = [(x - w / 2, 0), (x + w / 2, 0), (x + w / 2, h), (x - w / 2, h)]
        m0 = len(p.bm.verts)
        extrude(p, [(u, FLOOR_Z - 0.1 + zz) for u, zz in pts], y - 0.06, y + 0.06, rng.choice(("st_stone_l", "stone_tan", "stone_tan", "grave", "stone_moss")))
        lean = rng.uniform(-0.1, 0.1)
        p.bm.verts.ensure_lookup_table()
        for v in p.bm.verts[m0:]:
            v.co.y += (v.co.z - FLOOR_Z) * lean
        mound = [Vector((x + 0.2 * math.cos(math.radians(a)), c.y - 0.1 + 0.42 * math.sin(math.radians(a)), 0)) for a in range(0, 360, 45)]
        p.prism(mound, FLOOR_Z - 0.05, FLOOR_Z + 0.1, "grave_mound", side_mat="grave_mound")
        roll = rng.random()
        if roll < 0.5:
            flowers(p, rng, Vector((x, y - 0.2, 0)), FLOOR_Z)
        elif roll < 0.85:
            candle(p, Vector((x + rng.uniform(-0.12, 0.12), y - 0.2, 0)), FLOOR_Z)


def tomb(p, c):
    """A stone tomb filling its cell, lid and carved panel."""
    p.box(c, (1.0, 1.5, 0.7), "st_stone", z=FLOOR_Z)
    p.box(c, (1.15, 1.65, 0.14), "stone_block_dark", z=FLOOR_Z + 0.7)
    p.box(c + Vector((0, -0.76, 0)), (0.6, 0.04, 0.35), "stone_moss", z=FLOOR_Z + 0.18)
    candle(p, c + Vector((0.3, -0.95, 0)), FLOOR_Z)
    flowers(p, random.Random(int(c.x * 10)), c + Vector((-0.25, -0.95, 0)), FLOOR_Z)


def bed(p, rng, c):
    """A raised herb bed filling its cell: a hexagonal plank frame of dark soil in rows of greens, some flowering."""
    p.prism(outline(c, 0.86), FLOOR_Z - 0.05, FLOOR_Z + 0.3, "plank")
    p.prism(outline(c, 0.76), FLOOR_Z + 0.2, FLOOR_Z + 0.31, "soil_dark")
    crop = rng.choice((("herb_a", "leaf"), ("hedge", "herb_a"), ("leaf_green", "herb_a")))
    for row in range(-2, 3):
        y = c.y + row * 0.27
        span = 0.62 - abs(row) * 0.14
        for k in range(int(span / 0.22) * 2 + 1):
            x = c.x - span + k * 0.22 + (0.11 if row % 2 else 0)
            if abs(x - c.x) > span:
                continue
            at = Vector((x, y, 0))
            p.cone(at, rng.uniform(0.09, 0.13), rng.uniform(0.18, 0.28), crop[(k + row) % 2], segments=5, z=FLOOR_Z + 0.3, spin=rng.uniform(0, 1))
            if rng.random() < 0.15:
                p.box(at, (0.06, 0.06, 0.05), rng.choice(("flower_yellow", "flower_white")), z=FLOOR_Z + 0.5)


def well(p, c):
    """A stone well in the middle of its cell: a round wall, two oak posts, a windlass with its rope and bucket, a slate roof."""
    p.cylinder(c, 0.62, 0.75, "stone_block", segments=10, z=FLOOR_Z)
    p.cylinder(c, 0.68, 0.1, "stone_block_dark", segments=10, z=FLOOR_Z + 0.75)
    p.cylinder(c, 0.48, 0.02, "cave_dark", segments=10, z=FLOOR_Z + 0.82)
    for sx in (-1, 1):
        p.box(c + Vector((sx * 0.6, 0, 0)), (0.12, 0.12, 1.55), "gate_wood", z=FLOOR_Z + 0.6)
    p.log(c, 0.07, 1.25, "plank", spin=0.0, z=FLOOR_Z + 1.45)
    p.box(c, (0.02, 0.02, 0.5), "rope", z=FLOOR_Z + 0.95)
    p.cylinder(c + Vector((0.45, -0.6, 0)), 0.14, 0.24, "plank", segments=8, z=FLOOR_Z)
    p.gable_roof(c, 1.6, 1.1, 0.45, "st_slate", z=FLOOR_Z + 2.15)


def shrine(p, rng, c):
    """The god's statue on its raised cell: a hooded, robed figure with arms raised on a stone base, the god's symbol on its
    breast (its own material, swapped per god), offerings along the cell's front edge: bowls of fruit, flowers, candles."""
    z = FLOOR_Z + RAISE["shrine"]
    p.box(c, (0.8, 0.8, 0.45), "st_stone", z=z)
    s = z + 0.45
    p.cone(c, 0.42, 1.6, "stone_statue", segments=8, z=s)
    p.cylinder(c, 0.3, 1.1, "stone_statue", segments=8, z=s)
    p.blob(c, 0.2, "stone_statue", z=s + 1.45)
    p.cone(c, 0.24, 0.35, "stone_statue", segments=8, z=s + 1.45)
    for sx in (-1, 1):
        p.box_rot(c + Vector((sx * 0.33, -0.05, s + 1.25)), (0.13, 0.13, 0.6), "stone_statue", Matrix.Rotation(sx * 0.5, 3, "Y"))
    extrude(p, [(c.x + 0.13 * math.cos(math.radians(a)), s + 1.0 + 0.13 * math.sin(math.radians(a))) for a in range(0, 360, 45)],
            c.y - 0.33, c.y - 0.3, "god_symbol")
    for k, dx in enumerate((-0.5, -0.25, 0.0, 0.25, 0.5)):
        at = c + Vector((dx, -0.62, 0))
        if k % 2:
            p.cylinder(at, 0.1, 0.06, "offering", segments=8, z=z + 0.03)
            p.blob(at, 0.05, "apple", z=z + 0.11)
        else:
            candle(p, at, z + 0.03, h=0.12 + 0.04 * (k % 3))
    flowers(p, rng, c + Vector((-0.45, -0.35, 0)), z, n=4)
    flowers(p, rng, c + Vector((0.45, -0.35, 0)), z, n=4)


def woodpile(p, rng, c):
    """Split logs stacked under a lean-to in its cell, against the wall, a chopping block and axe before it."""
    for row in range(4):
        for k in range(5):
            p.log(c + Vector((-0.5 + (row % 2) * 0.12 + k * 0.22, 0.3, 0)), 0.1, 0.55, rng.choice(("trunk", "plank", "trunk_old")),
                  spin=math.pi / 2, z=FLOOR_Z + 0.1 + row * 0.18, segments=6)
    p.box_rot(c + Vector((0, 0.35, FLOOR_Z + 1.0)), (1.4, 0.85, 0.05), "plank_dark", Matrix.Rotation(-0.35, 3, "X"))
    for sx in (-1, 1):
        p.box(c + Vector((sx * 0.62, -0.02, 0)), (0.08, 0.08, 0.92), "plank_dark", z=FLOOR_Z)
    b = c + Vector((0.2, -0.55, 0))
    p.cylinder(b, 0.22, 0.4, "trunk", segments=8, z=FLOOR_Z)
    p.box_rot(b + Vector((0.05, 0, FLOOR_Z + 0.58)), (0.04, 0.04, 0.5), "plank", Matrix.Rotation(0.5, 3, "X"))
    p.box(b + Vector((0.05, -0.12, 0)), (0.16, 0.03, 0.12), "iron", z=FLOOR_Z + 0.42)


def bench(p, x, y, spin=0.0):
    """An oak bench, seat and back on two stone legs."""
    rot = Matrix.Rotation(spin, 3, "Z")
    c = Vector((x, y, 0))
    for sx in (-1, 1):
        p.box(c + rot @ Vector((sx * 0.55, 0, 0)), (0.12, 0.38, 0.4), "stone_block", z=FLOOR_Z, spin=spin)
    p.box(c, (1.4, 0.42, 0.07), "plank", z=FLOOR_Z + 0.4, spin=spin)
    p.box(c + rot @ Vector((0, 0.2, 0)), (1.4, 0.06, 0.4), "plank", z=FLOOR_Z + 0.5, spin=spin)


def outcrop(p, rng, x, y, size):
    """A grey boulder outcrop at scene scale: a big faceted boulder with smaller ones huddled against it, moss on top."""
    a0, z = rng.uniform(0, 2 * math.pi), z_at(x, y)
    for k, (r, off) in enumerate(((0.42, 0.0), (0.27, 0.48), (0.2, 0.46), (0.14, 0.62))):
        a = a0 + k * 2.1
        at = Vector((x + math.cos(a) * off * size, y + math.sin(a) * off * size, 0))
        p.blob(at, r * size, ("rock", "rock_dark")[k % 2], z=z + r * size * 0.2, squash=0.75)
    p.blob(Vector((x, y, 0)), 0.3 * size, "moss", z=z + 0.42 * size * 0.62, squash=0.25)


def tree(p, rng, x, y, h, pine):
    """A pine of three stacked tiers, or a broadleaf of clustered crowns, at scene scale (a mini is 1.3 m)."""
    z = z_at(x, y)
    c = Vector((x, y, 0))
    if pine:
        p.cylinder(c, 0.18, h * 0.3, "trunk", segments=6, z=z)
        for k, (r, t) in enumerate(((0.36, 0.45), (0.28, 0.4), (0.19, 0.38))):
            p.cone(c, r * h, t * h, ("pine_deep", "leaf_dark", "pine_deep")[k], segments=8, z=z + h * (0.2 + 0.27 * k), spin=k * 0.4)
    else:
        p.cylinder(c, 0.2, h * 0.5, "trunk", segments=6, z=z)
        for k in range(4):
            a = rng.uniform(0, 2 * math.pi)
            off = 0 if k == 0 else h * 0.18
            p.blob(c + Vector((math.cos(a) * off, math.sin(a) * off, 0)), h * rng.uniform(0.2, 0.28), ("leaf", "leaf_dark", "leaf_green")[k % 3],
                   z=z + h * (0.65 + (0.12 if k == 0 else rng.uniform(-0.05, 0.05))))


def square():
    p = hk.Piece(MESH)
    rng = random.Random(31)
    cells(p, rng)
    courtyard_wall(p, rng)
    chapel(p)
    for h, kind in sorted(CELLS.items()):
        c = hx(*h)
        if kind == "grave":
            grave_cell(p, rng, c)
        elif kind == "tomb":
            tomb(p, c)
        elif kind == "bed":
            bed(p, rng, c)
        elif kind == "well":
            well(p, c)
        elif kind == "shrine":
            shrine(p, rng, c)
        elif kind == "wood":
            woodpile(p, rng, c)
    bench(p, *hx(3, -3).xy, 0.0)
    bench(p, *hx(4, -4).xy, -math.pi / 2)
    for sx in (-1, 1):  # lamps on the plinth's front corners, either side of the steps
        lamp_post(p, sx * 2 * A, CH_Y - 0.3, PLINTH_Z)
    # outcrops and trees on the terraces beyond the wall
    for x, y, size in ((-7.4, -1.4, 1.3), (7.5, 1.2, 1.4), (-7.6, 6.6, 1.3), (7.5, 8.0, 1.2), (-7.5, 3.2, 1.0), (2.6, 12.6, 1.6),
                       (-3.4, 12.9, 1.3), (7.6, -3.4, 1.0)):
        outcrop(p, rng, x, y, size)
    for x, y, h, pine in ((7.9, -1.6, 4.2, False), (-7.9, 0.6, 4.8, True), (7.9, 4.6, 5.0, True), (-7.6, 10.0, 4.6, True),
                          (5.4, 12.4, 4.4, False), (-7.8, -3.6, 4.0, False), (-6.0, 12.6, 4.0, False), (8.2, 10.4, 4.6, True)):
        tree(p, rng, x, y, h, pine)
    return p


def lights():
    """[q, r, x, y, z, colour, day, night, flicker] for Godot: offsets from the nearest of the 19 hexes, in its frame (y up,
    toward the back is minus z)."""
    out = []
    for at, colour, day, night, flicker in LIGHTS:
        q, r = min(HEXES, key=lambda h: (hx(*h) - Vector((at.x, at.y, 0))).length)
        d = at - hx(q, r)
        out.append([q, r, round(d.x, 3), round(d.z, 3), round(-d.y, 3), colour, day, night, flicker])
    return out


def data():
    return {
        "hex_radius": R, "floor_z": FLOOR_Z, "board": "the party's spots stay on these 19 hexes; the floor runs on past them",
        "hexes": {f"{q},{r}": [round(hx(q, r).x, 4), round(hx(q, r).y, 4)] for q, r in HEXES},
        "spots": SPOTS, "keepers": KEEPERS, f"{ID}_places": PLACES, "backdrop": BACKDROP, "lights": lights(),
        "view_shift": [round(VIEW_SHIFT.x, 3), round(VIEW_SHIFT.z, 3), round(-VIEW_SHIFT.y, 3)],  # added to PlaceStage's VIEW_AT
    }


def build():
    hk.empty_scene()
    col = hk.new_collection(MESH)
    square().finish(col)
    path = hk.next_version(os.path.join(hk.ART, "places"), MESH)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    with open(os.path.join(hk.ART, "export", f"{MESH}.json"), "w") as f:
        json.dump(data(), f, indent=1)
    print("SAVED", path)


if __name__ == "__main__":
    build()
