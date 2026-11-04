"""A study outside the kit: hills_shoulder's layout on a hillside, to compare ways of slanting a whole map.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/hillside_study.py
Pass option letters after -- to render only those. Writes art/preview/hillside_<option>_<view>_vN.png and hillside_ridges_vN.png.

  a  flat-topped rising cells: each row 0.15 above the row downhill, so a cell's neighbour up the fall line is 0.3 above it
  b  tilted cells: the same fall as one continuous plane. As it stands, a flat base clips. bfix shears each base onto the slope
  c  a's flat cells and steps on a real hill's shape: a spur, a gully, a slope that turns, not a plane
  m  a mountainside: steeper, a cliff band across it and a broken stair through the band

Cell highlights show in the close views. Nothing here changes the kit, the plans or the map data.
Written against combat_hills_v1: the kit's ridge_3 has since gone, so a later kit needs the ridges option taken out. Ethan chose c, on Nov 3, 2026; render_hills_maps.py builds it.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build_forest_cells as fc  # noqa: E402
import build_hills_cells as hc  # noqa: E402
import hexkit as hk  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_hills_maps as rh  # noqa: E402
import render_preview as rp  # noqa: E402

V = "hills"
STEP = 0.15
BOARD_TOP = -0.12  # the soil block's top, under the lowest cells' line colour
FOES = rh.WOLVES
SHOULDER = """
. . . . . . . T .
 . . w . . . . x 
. . . . v . . . .
 . . . . . . c . 
. . . . . . . T .
 . Y . , . . R . 
. . Y . . P . . .
 c . Y . . P . . 
. . . . . P . . ,
 T . h . k . . T 
. . . s . . . . ."""
MOUNTAIN = """
. . . . . . . T .
 . . w . . . . x 
. . . . v . . . .
 . . . . . . c . 
K K K K K ^ K K K
 K K K K K ^ K K 
. . . . . . . . .
 c . Y . . R . . 
. . Y . . . . T .
 T . Y h . k . . 
. . . . . s . . ,"""
hk.PALETTE.update({"hillside_turf": fc.mix(hk.PALETTE["hill_grass"], "#2C4020", 0.42), "highlight_ring": "#FFD95A",
                   "highlight_fill": fc.mix(hk.PALETTE["hill_grass"], "#FFE27A", 0.5)})


def row_of(c):
    return 2 * c[1] + c[0]


def heights(option, cells):
    rows = [row_of(c) for c in cells]
    south, north = max(rows), min(rows)
    z = {}
    for c in cells:
        up = south - row_of(c)
        if option == "c":
            t, col = up / (south - north), c[0] - min(q for q, _ in cells)
            level = up + 2.6 * t * math.exp(-((col - 3.5) / 3.6) ** 2) - 2.4 * t * math.exp(-((col - 12) / 2.8) ** 2)
            z[c] = STEP * round(level)
        elif option == "m":
            lower = 0.2 * min(up, 4)
            z[c] = lower if up <= 4 else 0.8 + 1.3 + 0.2 * (up - 7) if up >= 7 else 0.8 if cells[c] == "K" else 0.8 + 0.65 * (up - 4)
        else:
            z[c] = STEP * up
    return z


def plane(cells, z):
    """The tilted option's surface, a function of x and y, through the cells' middles."""
    ys = {c: hk.cell_position(*c).y for c in cells}
    low = min(cells, key=lambda c: ys[c])
    high = max(cells, key=lambda c: ys[c])
    grad = (z[high] - z[low]) / (ys[high] - ys[low])
    return lambda q: z[low] + (q.y - ys[low]) * grad, grad


def link_at(p, col, z):
    p.finish(col)
    col.objects[p.name].location.z = z


def hillside(col, cells, z, skip=""):
    """What a kit cell can't give on a slope: under each cell, a hex of line colour, a wall on every edge above a lower neighbour, and the board's outer sides."""
    p = hk.Piece("hillside")
    rng = hk.seeded(p.name)
    for c in cells:
        at, top = hk.cell_position(*c), z[c] - 0.07
        corners = [at + fc.CORNERS[k] for k in range(6)]
        if cells[c] not in skip:
            p.bm.faces.new([p.bm.verts.new((q.x, q.y, top)) for q in corners]).material_index = p._slot("soil_dark")
        for k in range(6):
            a, b = corners[k], corners[(k + 1) % 6]
            mid = (a + b) / 2 - at
            n = next((c[0] + dq, c[1] + dr) for dq, dr in fm.NEIGHBOURS if (hk.cell_position(c[0] + dq, c[1] + dr) - at).dot(mid) > 0.3 and abs((hk.cell_position(c[0] + dq, c[1] + dr) - at).normalized().dot(mid.normalized()) - 1) < 0.01)
            if n in cells:
                if z[n] < z[c] - 0.001:
                    wall(p, a, b, z[n] - 0.07, top, "rock_dark" if cells[n] in "K^" or rng.random() < 0.25 else "hillside_turf")
            else:
                wall(p, a, b, BOARD_TOP, max(BOARD_TOP, top - 0.14), "soil_light")
                wall(p, a, b, max(BOARD_TOP, top - 0.14), top, "hillside_turf")
    p.finish(col)


def wall(p, a, b, z0, z1, mat):
    q = [p.bm.verts.new((u.x, u.y, h)) for u, h in ((a, z0), (b, z0), (b, z1), (a, z1))]
    p.bm.faces.new(q).material_index = p._slot(mat)


def surface_tilted(col, cells, at_z, grad):
    """The tilted option's cells: each hex's top on the plane, its outline a hex of line colour just under it."""
    p = hk.Piece("tilted")
    rng = hk.seeded(p.name)
    for c, mark in cells.items():
        at = hk.cell_position(*c)
        n = rb.hash_cell(c)
        top = "cell_hills_cover" if mark in "cT" else "cell_hills_block" if mark in "RYP" else f"cell_hills_{'abc'[(c[0] - c[1]) % 3]}"
        for k in range(1):
            line = [p.bm.verts.new((q.x, q.y, at_z(q) - 0.05)) for q in (at + fc.CORNERS[j] for j in range(6))]
            p.bm.faces.new(line).material_index = p._slot("soil_dark")
            inset = [p.bm.verts.new((q.x, q.y, at_z(q))) for q in (at + fc.CORNERS[j] * fc.GAP for j in range(6))]
            p.bm.faces.new(inset).material_index = p._slot(top)
        if mark == "c":
            for j in range(6):
                q = at + Vector((math.cos(j * 1.05 + n), math.sin(j * 1.05 + n), 0)) * rng.uniform(0.16, 0.36)
                q.z = at_z(q)
                p.cone(q, 0.1, 0.2, "grass_ink", segments=4, spin=rng.uniform(0, 1))
        if mark == ",":
            q = at.copy()
            q.z = at_z(q)
            p.cone(q, 0.1, 0.08, "rock", segments=5)
    corner = {}
    for c in cells:  # the outer sides
        at = hk.cell_position(*c)
        for k in range(6):
            a, b = at + fc.CORNERS[k], at + fc.CORNERS[(k + 1) % 6]
            key = tuple(sorted(((round(a.x, 3), round(a.y, 3)), (round(b.x, 3), round(b.y, 3)))))
            corner[key] = None if key in corner else (a, b)
    for pair in corner.values():
        if pair:
            a, b = pair
            q = [p.bm.verts.new((u.x, u.y, h)) for u, h in ((a, BOARD_TOP), (b, BOARD_TOP), (b, at_z(b) - 0.05), (a, at_z(a) - 0.05))]
            p.bm.faces.new(q).material_index = p._slot("soil_light")
    p.finish(col)


def ridge_mass(p, rng, centres, ground):
    """One solid back of rock along its cells instead of a row of spikes: a broad foot on the ground, shoulders, a worn crest that rises and falls gently, and two or three crags breaking it."""
    a, b = centres[0], centres[-1]
    along = (b - a).normalized()
    across = Vector((-along.y, along.x, 0))
    a, b = a - along * 0.42, b + along * 0.42
    rows, n = [], 7
    for k in range(n + 1):
        c = a.lerp(b, k / n)
        g = ground(c) - 0.08
        end = k in (0, n)
        crest = 0.3 if end else rng.uniform(0.82, 1.42)
        wob = across * rng.uniform(-0.05, 0.05)
        wide = 0.46 * (0.75 if end else rng.uniform(0.92, 1.05))
        rows.append([p.bm.verts.new(c - across * wide + Vector((0, 0, g))), p.bm.verts.new(c - across * 0.28 + wob + Vector((0, 0, g + crest * 0.6))),
                     p.bm.verts.new(c + wob + Vector((0, 0, g + crest))), p.bm.verts.new(c + across * 0.28 + wob + Vector((0, 0, g + crest * 0.6))),
                     p.bm.verts.new(c + across * wide + Vector((0, 0, g)))])
    for r0, r1 in zip(rows, rows[1:]):
        for j in range(4):
            top = j in (1, 2)
            mat = rng.choice(("rock", "rock", "rock_light", "rock_dark")) if top else rng.choice(("rock_dark", "rock_dark", "rock", "rock_shade"))
            for tri in ((r0[j], r1[j], r1[j + 1]), (r0[j], r1[j + 1], r0[j + 1])):
                p.bm.faces.new(tri).material_index = p._slot(mat)
    for r in (rows[0], rows[-1]):
        p.bm.faces.new(r[::-1] if r is rows[-1] else r).material_index = p._slot("rock_dark")
    for k in (2, 5):  # lumps of rock on its flanks, so it isn't a clean loaf
        side = across * (0.3 if k == 2 else -0.3)
        c = rows[k][2].co
        fc.rock(p, rng, Vector((c.x, c.y, 0)) + side, 0.24, "rock_dark", ground(Vector((c.x, c.y, 0))) + 0.12, 0.8)


def flight(col, c, d, z0, z1):
    """A stair through the cliff band: three even treads up along d on its cell, walled in by the rock on either side."""
    p = hk.Piece(f"flight_{c}")
    at = hk.cell_position(*c)
    d = d.normalized()
    spin = math.atan2(d.y, d.x)
    for k in range(3):
        q = at + d * (-0.33 + 0.33 * k)
        p.box(q, (0.36, 0.92, z0 + (z1 - z0) * (k + 1) / 3 + 0.07 - z0), "way_hills" if k % 2 else "way_hills_b", z=z0 - 0.07, spin=spin)
    p.finish(col)


def highlight(col, cells, z, at_z=None):
    """The hero's reach, as the engine would mark it: a filled cell with a bright ring, two steps out."""
    start = next(c for c, m in cells.items() if m == "h")
    reach, frontier = {start}, [start]
    for _ in range(2):
        frontier = [(c[0] + a, c[1] + b) for c in frontier for a, b in fm.NEIGHBOURS]
        frontier = [c for c in frontier if c in cells and cells[c] in fm.WALKABLE + "." and c not in reach]
        reach.update(frontier)
    reach.discard(start)
    p = hk.Piece("highlight")
    for c in reach:
        at = hk.cell_position(*c)
        lift = lambda q: (at_z(q) if at_z else z[c]) + 0.012  # noqa: E731
        outer = [at + fc.CORNERS[j] * fc.GAP for j in range(6)]
        inner = [at + fc.CORNERS[j] * (fc.GAP - 0.14) for j in range(6)]
        fill = [p.bm.verts.new((q.x, q.y, lift(q))) for q in inner]
        p.bm.faces.new(fill).material_index = p._slot("highlight_fill")
        for j in range(6):
            m = (j + 1) % 6
            ring = [p.bm.verts.new((q.x, q.y, lift(q) + 0.002)) for q in (outer[j], outer[m], inner[m], inner[j])]
            p.bm.faces.new(ring).material_index = p._slot("highlight_ring")
    p.finish(col)


def build(t, col, option):
    plan = MOUNTAIN if option == "m" else SHOULDER
    m = {"plan": plan, "foes": FOES}
    cells = fm.parse(plan)
    z = heights(option, cells)
    tilted = option in ("b", "bfix")
    at_z, grad = plane(cells, z) if tilted else (None, 0.0)
    p = hk.Piece("plate")
    loop = fc.cell_loop(cells)
    p.prism(loop, -0.3, BOARD_TOP, "soil_dark", side_mat="soil_light")
    p.prism(loop, hk.SOIL_BOTTOM, -0.3, "soil_dark")
    p.finish(col)
    fm.way_tones(V)
    if tilted:
        surface_tilted(col, cells, at_z, grad)
    else:
        hillside(col, cells, z, skip="K^")
    for c, mark in cells.items():
        at = hk.cell_position(*c)
        n = rb.hash_cell(c)
        if not tilted and mark not in "K^":
            piece = {"c": "brush", ",": "litter", "T": "cover", "R": f"block_{'ab'[n % 2]}"}.get(mark, "floor" if mark in "YP" else f"ground_{'abc'[(c[0] - c[1]) % 3]}")
            rp.place(t, f"cell_{V}_{piece}", col, at + Vector((0, 0, z[c])), math.radians(60 * (n % 6)) if mark in "R,c" else 0.0)
        if mark == "T":
            rp.place(t, f"ob_{V}_tree_{'abc'[n % 3]}", col, at + Vector((0, 0, z[c] - (0.1 if tilted else 0))), math.radians(60 * (n % 6)))
        if tilted and mark == "R":
            r = hk.Piece(f"rocks_{c}")
            fc.boulders(r, hk.seeded(r.name), *fc.ROCK[V][:2], top=fc.ROCK[V][2], tall=0.3)
            r.finish(col)
            o = col.objects[r.name]
            o.location = at + Vector((0, 0, z[c] - 0.05))
    for _, group in fm.groups(cells, "P"):
        anchor, turn = fm.fit(group, fc.TRIANGLE)
        rp.place(t, f"ob_{V}_peak_3", col, hk.cell_position(*anchor) + Vector((0, 0, min(z[c] for c in group) - (0.15 if tilted else 0.07))), math.radians(60 * turn))
    surface = at_z or (lambda q: z[min(cells, key=lambda c: (hk.cell_position(*c) - Vector((q.x, q.y, 0))).length)])
    for _, group in fm.groups(cells, "Y"):
        r = hk.Piece(f"ridge_{min(group)}")
        ridge_mass(r, hk.seeded(r.name), sorted((hk.cell_position(*c) for c in group), key=lambda q: q.x), surface)
        r.finish(col)
    if option == "m":
        h = fm.CLIFF_HEIGHT
        fm.CLIFF_HEIGHT = 1.4
        for _, group in fm.groups(cells, "K"):
            before = set(col.objects)
            fm.shaped_piece(col, V, group, "K")
            for o in set(col.objects) - before:
                o.location.z = 0.7
        fm.CLIFF_HEIGHT = h
        ups = sorted((c for c, mark in cells.items() if mark == "^"), key=row_of, reverse=True)
        for c, nxt, z0, z1 in ((ups[0], ups[1], 0.8, 1.45), (ups[1], None, 1.45, 2.1)):
            d = hk.cell_position(*nxt) - hk.cell_position(*c) if nxt else hk.cell_position(*c) - hk.cell_position(*ups[0])
            flight(col, c, d, z0, z1)
    fm.place_minis(t, col, m, cells)
    for o in col.objects:
        if o.get("piece", "").startswith(("enemy_", "standin_")):
            o.location.z = at_z(o.location) if tilted else z[min(cells, key=lambda c: (hk.cell_position(*c) - o.location.to_2d().to_3d()).length)]
    return m, cells, z, at_z, grad


def shear_bases(col, grad):
    """Godot's likely fix for tilted cells, as a vertex shader or mesh edit would do it: each base follows the slope, fading out up the legs, the body stays upright."""
    for o in list(col.objects):
        if not o.get("piece", "").startswith(("enemy_", "standin_")):
            continue
        mesh = o.data.copy()
        spin = Matrix.Rotation(o.rotation_euler.z, 3, "Z")
        for v in mesh.vertices:
            world = spin @ Vector((v.co.x, v.co.y, 0))
            fade = max(0.0, min(1.0, (0.34 - v.co.z) / 0.22))
            v.co.z += world.y * grad * fade
        o.data = mesh


def seen_share(col, cells, z, yaw_deg, top_z):
    """Each mini from the engine's camera, opening distance, this side: how much of its body has a clear line."""
    scene = bpy.context.scene
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    el, yaw = math.radians(fm.PITCH), math.radians(yaw_deg)
    target = fm.middle_of(cells) + Vector((0, 0, top_z))
    cam = target + Vector((-math.sin(yaw) * math.cos(el), -math.cos(yaw) * math.cos(el), math.sin(el))) * fm.ENGINE_DISTANCE
    out = []
    for o in col.objects:
        if not o.get("piece", "").startswith(("enemy_", "standin_")):
            continue
        body = [o.location + Vector((0, 0, h)) for h in (0.3, 0.55, 0.8, 1.05, 1.2)]
        clear = 0
        for at in body:
            to = cam - at
            hit, _, _, _, obj, _ = scene.ray_cast(deps, at, to.normalized(), distance=to.length)
            clear += (not hit) or obj.name == o.name
        out.append(f"{o['piece'].replace('enemy_', '').replace('standin_', '')} y{o.location.y:.1f} {round(100 * clear / len(body))}%")
    return out


def view(option, name, close=None, yaw=0, with_highlight=False):
    hk.empty_scene()
    col = hk.new_collection("map")
    t = rh.templates()
    m, cells, z, at_z, grad = build(t, col, option)
    if option == "bfix":
        shear_bases(col, grad)
    if with_highlight:
        highlight(col, cells, z, at_z)
    mean = sum(z.values()) / len(z)
    if close:
        at = hk.cell_position(*next(c for c, mk in cells.items() if mk == close))
        target, distance = at + Vector((0, 0.3, z[next(c for c, mk in cells.items() if mk == close)] + 0.4)), 11
    else:
        target, distance = fm.framing(cells)
        target = target + Vector((0, 0, mean))
    rp.stage(target, distance, fm.PITCH)
    if yaw:
        rb.turn_camera(yaw, target)
    rp.render(f"hillside_{option}_{name}")
    return col, cells, z, mean


def measure(option):
    hk.empty_scene()
    col = hk.new_collection("map")
    m, cells, z, at_z, grad = build(rh.templates(), col, option)
    total = fm.triangles(col)
    minis = [o for o in col.objects if o.get("piece", "").startswith(("enemy_", "standin_"))]
    tris_minis = 0
    for o in minis:
        o.data.calc_loop_triangles()
        tris_minis += len(o.data.loop_triangles)
    diffs = [abs(z[c] - z[(c[0] + a, c[1] + b)]) for c in z for a, b in fm.NEIGHBOURS if (c[0] + a, c[1] + b) in z and cells[c] not in "K^" and cells[(c[0] + a, c[1] + b)] not in "K^"]
    print(f"MEASURE {option}: rise {max(z.values()) - min(z.values()):.2f}, neighbour steps up to {max(diffs):.2f}, tris map {total - tris_minis}, with minis {total}")
    mean = sum(z.values()) / len(z)
    saved = fm.sample_z, fm.seen_default
    lift = 0.12 if at_z else 0.03
    fm.sample_z = lambda cs, c, mark: z[c] + (0.3 if mark == "c" else lift)

    def seen_default(scene, depsgraph, c, target, el, mark):
        cam = target + Vector((0, -math.cos(el), math.sin(el))) * fm.ENGINE_DISTANCE
        pt = hk.cell_position(*c) + Vector((0, 0, z[c] + lift))
        to = cam - pt
        return not scene.ray_cast(depsgraph, pt, to.normalized(), distance=to.length)[0]
    fm.seen_default = seen_default
    for o in minis:
        o.hide_viewport = True
    bpy.context.view_layer.update()
    fm.visibility(f"hillside_{option}", {c: ("." if mk in fm.MINI_MARKS else mk) for c, mk in cells.items()})
    for o in minis:
        o.hide_viewport = False
    fm.sample_z, fm.seen_default = saved
    for yaw in (0, 180):
        print(f"MINIS {option} from {yaw}:", "; ".join(seen_share(col, cells, z, yaw, mean)))


def ridges():
    """The kit's ridge beside the solid one, on flat cells, a hero beside them."""
    hk.empty_scene()
    col = hk.new_collection("map")
    t = rh.templates()
    cells = [(q + dq, r) for dq in (0, 5) for q, r in fc.LINE3]
    for q, r in cells:
        rp.place(t, f"cell_{V}_floor", col, hk.cell_position(q, r))
    rp.place(t, f"ob_{V}_ridge_3", col, hk.cell_position(0, 0))
    p = hk.Piece("mass")
    ridge_mass(p, hk.seeded("mass"), fc.centres([(5, 0), (6, 0), (7, 0)]), lambda q: 0.0)
    p.finish(col)
    rp.place(t, "standin_hero", col, hk.cell_position(4, 2), rb.FACE_NORTH)
    middle = sum((hk.cell_position(q, r) for q, r in cells), Vector((0, 0, 0))) / len(cells)
    rp.stage(middle + Vector((0, 0, 0.5)), 14, fm.PITCH)
    rp.render("hillside_ridges")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["a", "b", "bfix", "c", "m", "ridges"]
    for option in args:
        if option == "ridges":
            ridges()
            continue
        if option != "bfix":
            view(option, "front")
            view(option, "turned", yaw=180)
            view(option, "close_turned", close="h", yaw=180, with_highlight=True)
        view(option, "close", close="h", with_highlight=True)
        if option != "bfix":
            measure(option)
