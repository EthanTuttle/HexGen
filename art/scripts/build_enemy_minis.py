"""Builds the scripted low-poly enemy minis and saves art/minis/enemies/enemy_minis_vN.blend.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_enemy_minis.py

Same contract as the stand-ins (build_standin_minis.py): a flat-top hex base 0.9 across the flats, pivot at the base
centre on the ground, facing -Y in Blender (+Z in the glb), shared kit material with the colours in vertex colours.
No animation: the engine moves a mini whole (hop, recoil), so each pose has to read on its own.

  enemy_wolf          plain wolf, stalking
  enemy_wolf_elite    bigger and darker, hackles up, a spiked iron collar
  enemy_spider        plain giant spider, all feet down
  enemy_spider_elite  bigger, red hourglass mark, spines down its back, front legs raised

An elite shows on the model itself, with no mark on its base (design/07). Stats and the roster are still open.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_standin_minis as sm  # noqa: E402  (base() and the base colours)
import hexkit as hk  # noqa: E402

hk.PALETTE.update({
    "wolf_back": "#7D7871",
    "wolf": "#A8A299",
    "wolf_belly": "#D3CBBC",
    "wolf_dark": "#3B3835",
    "elite_back": "#2F2C2B",
    "elite_coat": "#4A4543",
    "elite_belly": "#8C857C",
    "elite_mane": "#C9C2B4",
    "mouth": "#8E2F2B",
    "fang": "#F4EFE2",
    "eye_amber": "#F2B233",
    "eye_red": "#E8402E",
    "spider_body": "#4A3429",
    "spider_back": "#35251E",
    "spider_band": "#B08A5E",
    "spider_mark": "#D9B98A",
    "spider_elite_body": "#2A2230",
    "spider_elite_back": "#1E1923",
    "spider_elite_band": "#A8352C",
    "spider_elite_mark": "#E2483A",
})

Z0 = sm.BASE_H + 0.005  # top of the base
SIDE = sm.BASE_FLATS / 2


# --- Faceted shapes ---------------------------------------------------------

def loft(p, rings, paint):
    """Skins rings of equal size into a faceted body. A ring of one point closes that end to a tip, a longer end ring
    gets a flat cap. paint(centre, normal) names each face's colour, which is what gives the flat-colour look."""
    bm = p.bm
    verts = [[bm.verts.new(q) for q in ring] for ring in rings]
    middle = sum((rings_centre(r) for r in rings), Vector((0, 0, 0))) / len(rings)
    faces = []
    for a, b in zip(verts, verts[1:]):
        n = max(len(a), len(b))
        for i in range(n):
            j = (i + 1) % n
            if len(a) == 1:
                faces.append((a[0], b[i], b[j]))
            elif len(b) == 1:
                faces.append((a[i], a[j], b[0]))
            else:
                faces.append((a[i], a[j], b[j], b[i]))
    for end in (verts[0], verts[-1]):
        if len(end) > 2:
            faces.append(tuple(end))
    for vs in faces:
        f = bm.faces.new(vs)
        f.normal_update()
        c = f.calc_center_median()
        n = f.normal.copy()
        if n.dot(c - middle) < 0:
            n = -n
        f.material_index = p._slot(paint(c, n))


def rings_centre(ring):
    return sum(ring, Vector((0, 0, 0))) / len(ring)


def polyline_at(points, t):
    """The point a share t of the way along a polyline, by length."""
    lengths = [(b - a).length for a, b in zip(points, points[1:])]
    left = t * sum(lengths)
    for a, b, d in zip(points, points[1:], lengths):
        if left <= d:
            return a.lerp(b, left / d)
        left -= d
    return points[-1].copy()


def section(at, w, h, along=Vector((0, -1, 0)), up=Vector((0, 0, 1)), ridge=1.0, keel=1.0, sides=6):
    """A cross-section at `at`, square to `along`: w half wide, h half tall. ridge and keel sharpen the top and belly."""
    along = along.normalized()
    right = along.cross(up).normalized()
    upn = right.cross(along).normalized()
    pts = []
    for i in range(sides):
        a = 2 * math.pi * i / sides
        s, c = math.sin(a), math.cos(a)
        z = c * (ridge if c > 0 else keel)
        pts.append(at + right * (s * w) + upn * (z * h))
    return pts


def limb(p, points, radii, paints, sides=4):
    """A tube along a polyline, turning smoothly at the joints; a radius of 0 ends in a point. paints: one per segment."""
    rings = []
    for i, q in enumerate(points):
        if radii[i] <= 0:
            rings.append([q])
            continue
        d0 = (q - points[max(i - 1, 0)])
        d1 = (points[min(i + 1, len(points) - 1)] - q)
        d = (d0.normalized() + d1.normalized()).normalized() if d0.length and d1.length else (d0 + d1).normalized()
        ref = Vector((0, 1, 0)) if abs(d.y) < 0.8 else Vector((1, 0, 0))
        u = d.cross(ref).normalized()
        v = d.cross(u).normalized()
        rings.append([q + (u * math.cos(2 * math.pi * k / sides) + v * math.sin(2 * math.pi * k / sides)) * radii[i]
                      for k in range(sides)])
    bm = p.bm
    verts = [[bm.verts.new(q) for q in ring] for ring in rings]
    for s, (a, b) in enumerate(zip(verts, verts[1:])):
        slot = p._slot(paints[min(s, len(paints) - 1)])
        for i in range(max(len(a), len(b))):
            j = (i + 1) % max(len(a), len(b))
            if len(b) == 1:
                vs = (a[i], a[j], b[0])
            elif len(a) == 1:
                vs = (a[0], b[i], b[j])
            else:
                vs = (a[i], a[j], b[j], b[i])
            bm.faces.new(vs).material_index = slot
    if len(verts[0]) > 2:
        bm.faces.new(tuple(verts[0])).material_index = p._slot(paints[0])


def enemy_base(p):
    sm.base(p, "ring_enemy")


# --- Wolf -------------------------------------------------------------------

def wolf(col, elite=False):
    p = hk.Piece("enemy_wolf_elite" if elite else "enemy_wolf")
    enemy_base(p)
    wolf_shape(p, elite)
    return p.finish(col)


def wolf_shape(p, elite=False):
    """The wolf itself, without a base (build_giant_minis.py resizes it)."""
    back, coat, belly = ("elite_back", "elite_coat", "elite_belly") if elite else ("wolf_back", "wolf", "wolf_belly")
    sx, sy, sz = (1.24, 1.1, 1.3) if elite else (1.0, 1.0, 1.0)

    def at(x, y, z):
        return Vector((x * sx, y * sy, Z0 + z * sz))

    def fur(c, n):
        return back if n.z > 0.55 else belly if n.z < -0.25 else coat

    def head_fur(c, n):
        # Pale muzzle and throat under a dark brow, as on the body.
        if n.z < -0.1 or c.y < at(0, -0.41, 0).y and n.z < 0.6:
            return belly
        return back if n.z > 0.5 else coat

    # Body: deep chest, tucked waist, rump a touch lower than the shoulders.
    body = [(0.34, 0.34, 0.04, 0.04), (0.28, 0.35, 0.125, 0.13), (0.09, 0.37, 0.125, 0.125),
            (-0.08, 0.37, 0.155, 0.18), (-0.20, 0.41, 0.14, 0.15)]
    loft(p, [section(at(0, y, z), w * sx, h * sz, ridge=1.1, keel=1.0) for y, z, w, h in body], fur)

    # A thick ruffed neck runs forward, with the big head held out level with the back: the stalking pose.
    turn = 0.14  # head turned a little to his right, so he doesn't read as a straight bar from above
    def hx(y):
        return turn * max(0.0, -0.2 - y)
    neck = [(-0.17, 0.43, 0.13, 0.15), (-0.27, 0.46, 0.11, 0.12)]
    head = [(-0.30, 0.47, 0.105, 0.09), (-0.355, 0.46, 0.09, 0.075), (-0.42, 0.425, 0.045, 0.04),
            (-0.475, 0.41, 0.034, 0.03)]
    d = Vector((0, -1, -0.25))
    loft(p, [section(at(hx(y), y, z), w * sx, h * sz, along=d) for y, z, w, h in neck + head], head_fur)
    nose = at(hx(-0.47), -0.488, 0.42)
    p.box(nose, (0.04 * sx, 0.018, 0.03 * sz), "wolf_dark")

    # Open jaw: dark red mouth wedge with a pale lower jaw under it, and two fangs.
    jaw = [section(at(hx(-0.34), -0.34, 0.40), 0.065 * sx, 0.024 * sz, along=d),
           section(at(hx(-0.45), -0.45, 0.345), 0.03 * sx, 0.014 * sz, along=d)]
    loft(p, jaw, lambda c, n: "mouth" if n.z > 0.4 else belly)
    for s in (-1, 1):
        root = at(hx(-0.455) + s * 0.024, -0.455, 0.40)
        hk.spike_up(p, root, root + Vector((0, -0.004, -0.05)), 0.011, "fang", segments=3)

    # Ears, pricked; eyes on the sides of the brow.
    for s in (-1, 1):
        root = at(hx(-0.30) + s * 0.062, -0.295, 0.53)
        hk.spike_up(p, root, root + Vector((s * 0.02, 0.03, 0.11 * sz)), 0.04, back, segments=3)
        eye = at(hx(-0.375) + s * 0.07, -0.375, 0.478)
        p.box(eye, (0.018, 0.03, 0.018), "eye_red" if elite else "eye_amber")

    # Legs: a stalking step, near fore paw forward, off fore back, hind legs bent and loaded.
    for s, y_paw in ((-1, -0.30), (1, -0.13)):
        x = 0.105 * sx * s
        pts = [Vector((x, -0.15 * sy, Z0 + 0.33 * sz)), Vector((x * 1.06, (-0.15 * sy + y_paw) / 2, Z0 + 0.18 * sz)),
               Vector((x * 1.12, y_paw + 0.012, Z0 + 0.06)), Vector((x * 1.12, y_paw - 0.02, Z0 + 0.022))]
        limb(p, pts, [0.075, 0.052, 0.038, 0.042], [coat, coat, belly])
    for s, y_paw in ((-1, 0.31), (1, 0.21)):
        x = 0.105 * sx * s
        pts = [Vector((x, 0.25 * sy, Z0 + 0.32 * sz)), Vector((x * 1.08, 0.16 * sy, Z0 + 0.2 * sz)),
               Vector((x * 1.12, y_paw + 0.05, Z0 + 0.11 * sz)), Vector((x * 1.12, y_paw, Z0 + 0.022))]
        limb(p, pts, [0.09, 0.062, 0.036, 0.042], [coat, coat, belly])

    # Tail: low and out behind, off to one side, the dark tip keeping inside the cell.
    tail = [at(0, 0.32, 0.38), at(0.04, 0.385, 0.31), at(0.08, 0.415, 0.2), at(0.095, 0.42, 0.08)]
    limb(p, tail, [0.045, 0.07, 0.052, 0.0], [coat, coat, back])

    if elite:
        # A spiked iron collar on the neck.
        ring = [section(at(0, y, 0.45), 0.135 * sx, 0.135 * sz, along=d, sides=8) for y in (-0.205, -0.25)]
        loft(p, ring, lambda c, n: "steel")
        for k in range(5):
            a = 0.5 + k * 0.54
            spike = at(math.cos(a) * 0.135, -0.228, 0.45 + math.sin(a) * 0.135)
            hk.spike_up(p, spike, spike + Vector((math.cos(a), -0.1, math.sin(a))) * 0.1, 0.022, "steel", segments=3)
        # Hackles: pale fur raised up the neck and along the spine, lying back, the part of him that reads from the camera.
        for y, z, height, width in [(-0.255, 0.555, 0.10, 0.052), (-0.17, 0.555, 0.13, 0.058), (-0.08, 0.525, 0.12, 0.055),
                                    (0.02, 0.475, 0.10, 0.048), (0.12, 0.465, 0.08, 0.042)]:
            for s in (-1, 1):
                r = at(s * 0.035, y, z)
                hk.spike_up(p, r, r + Vector((s * 0.03, height * 0.75, height)), width, "elite_mane", segments=3)


# --- Spider -----------------------------------------------------------------

def tip_reach(angle):
    """How far from the centre a foot can stand along `angle` (radians from +X) and stay on the hex base."""
    nearest = min(abs(((angle - math.radians(a) + math.pi) % (2 * math.pi)) - math.pi) for a in range(30, 360, 60))
    return SIDE * 0.93 / math.cos(nearest)


LEG_ANGLES = (27, 62, 112, 152)


def spider(col, elite=False):
    p = hk.Piece("enemy_spider_elite" if elite else "enemy_spider")
    enemy_base(p)
    spider_shape(p, elite)
    return p.finish(col)


def spider_shape(p, elite=False, reach_of=tip_reach, angles=LEG_ANGLES):
    """The spider itself, without a base. reach_of(angle): how far a foot may stand from the centre that way."""
    body, back = ("spider_elite_body", "spider_elite_back") if elite else ("spider_body", "spider_back")
    band, mark = ("spider_elite_band", "spider_elite_mark") if elite else ("spider_band", "spider_mark")
    grow = 1.32 if elite else 1.0

    def at(y, z, x=0.0):
        return Vector((x, y, Z0 + z))

    def shell(c, n):
        return back if n.z > 0.45 else body

    # Head and thorax, front and low.
    head = [(-0.215, 0.215, 0.050, 0.040), (-0.175, 0.235, 0.088, 0.066), (-0.07, 0.25, 0.108, 0.078),
            (0.03, 0.26, 0.062, 0.05)]
    loft(p, [section(at(y, z), w, h) for y, z, w, h in head], shell)

    # Abdomen behind and above it, the big shape. Rings run back along it, and the rings' top faces carry the bands.
    rows = [(0.0, 0.31, 0.07, 0.07), (0.07, 0.36, 0.165, 0.145), (0.17, 0.39, 0.205, 0.175),
            (0.28, 0.385, 0.185, 0.155), (0.36, 0.355, 0.105, 0.095), (0.405, 0.335, 0.0, 0.0)]
    rings = []
    for y, z, w, h in rows:
        y, z, w, h = y * (grow * 0.96), z * (0.98 + 0.12 * elite), w * grow, h * grow
        rings.append([at(y, z)] if w == 0 else section(at(y, z), w, h, along=Vector((0, 1, 0.18)), sides=8))

    loft(p, rings, lambda c, n: back if n.z > 0.35 else body)

    if elite:  # Spines down its back, like armour.
        for r in rings[1:4]:
            for sd in (-1, 1):
                c = rings_centre(r) + Vector((sd * 0.12, 0, 0.13))
                hk.spike_up(p, c, c + Vector((sd * 0.05, 0.05, 0.16)), 0.035, mark, segments=3)

    # The mark: a thin plate along the abdomen's crest, its width changing along the length. It's a shape of its own
    # because whole facets are too coarse for it. Plain: a pale folium. Elite: a red hourglass.
    crest = [r[0] for r in rings]
    widths = ((0.14, 0.10), (0.30, 0.025), (0.46, 0.10), (0.64, 0.025), (0.80, 0.075), (0.92, 0.0)) if not elite else (
        (0.18, 0.12), (0.42, 0.02), (0.68, 0.125), (0.72, 0.0))
    plate = []
    for t, w in widths:
        q = polyline_at(crest, t)
        w *= grow
        plate.append([q + Vector((0, 0, 0.012))] if w == 0 else
                     [q + Vector((0, 0, 0.022)), q + Vector((w, 0, -0.28 * w + 0.012)), q + Vector((0, 0, -0.03)),
                      q + Vector((-w, 0, -0.28 * w + 0.012))])
    loft(p, plate, lambda c, n: mark)

    # Eight legs, each with a high knee, then down to a point on the base. Angles from straight ahead (-Y).
    # The elite lifts its front pair, threatening; the plain one keeps all eight feet down.
    for s in (-1, 1):
        for i, ang in enumerate(angles):
            a = math.radians(-90 + s * ang)
            d = Vector((math.cos(a), math.sin(a), 0))
            reach = reach_of(a) * (1.0 if not elite else 1.06)
            root = at(-0.15 + 0.055 * i, 0.235) + Vector((s * 0.075, 0, 0))
            knee_z = (0.50, 0.555, 0.54, 0.50)[i] * (1.08 if elite else 1.0)
            if elite and i == 0:
                points = [root, root + d * 0.11 + Vector((0, 0, 0.27)), root + d * 0.17 + Vector((0, -0.02, 0.48)),
                          root + d * 0.235 + Vector((0, -0.05, 0.60))]
            else:
                points = [root, d * (reach * 0.56) + Vector((0, 0, Z0 + knee_z)),
                          d * (reach * 0.86) + Vector((0, 0, Z0 + 0.255)), d * reach + Vector((0, 0, Z0 + 0.008))]
            limb(p, points, [0.04, 0.036, 0.025, 0.0], [body, band, body], sides=4)

    # Fangs and palps in front, eyes on the brow.
    for s in (-1, 1):
        root = at(-0.215, 0.19, s * 0.026)
        hk.spike_up(p, root, root + Vector((-s * 0.004, -0.03, -0.09)), 0.021, "fang" if elite else band, segments=4)
        palp = [at(-0.19, 0.225, s * 0.05), at(-0.27, 0.275, s * 0.09), at(-0.315, 0.20, s * 0.095)]
        limb(p, palp, [0.016, 0.015, 0.0], [body, band], sides=3)
        for ex, ez in ((0.018, 0.0), (0.038, -0.012)):
            p.box(at(-0.245, 0.244 + ez, s * ex), (0.013, 0.012, 0.013), "eye_red" if elite else "eye_amber")


def triangles(obj):
    return sum(len(f.vertices) - 2 for f in obj.data.polygons)


def build():
    hk.empty_scene()
    col = hk.new_collection("minis")
    made = [wolf(col), wolf(col, elite=True), spider(col), spider(col, elite=True)]
    for obj in made:
        tops = [v.co.z for v in obj.data.vertices]
        span = max(max(abs(v.co.x), abs(v.co.y)) for v in obj.data.vertices)
        print(f"TRIS {obj.name}: {triangles(obj)} top {max(tops):.2f} widest {span:.2f} mats {[m.name for m in obj.data.materials]}")
    path = hk.next_version(os.path.join(hk.ART, "minis", "enemies"), "enemy_minis")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    hk.STANDS_ALONE = True  # a mini is seen whole from every side
    build()
