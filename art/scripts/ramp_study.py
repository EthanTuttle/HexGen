"""A ramp style study: not in the kit. Each style against a stand-in banded wall at the two real heights, a canyon entrance (1.9) and the
Raider Stronghold (2.3), in the two desert colours, with minis on it and at the foot.

Everything is built in wall space (s along the wall, d into it, z up), and W() maps that to the world, so a bent wall is the same code.

Run: Blender -b --factory-startup --python art/scripts/ramp_study.py -- [--styles=ABCDE] [--sheet=game,low,map,bend] [--measure]
Writes art/preview/ramp_study_<sheet>_vN.png, one row a style, and prints triangles, slopes and clipping with --measure.
"""
import math
import os
import random
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexkit as hk
from ramp_parts import Run

PI = math.pi
TILT = 26.0  # the route's steepest; the minis' limit is 28
WIDTH = 1.2  # the walkable lane
COLOURS = {
    "canyon": dict(bands=[(0.0, 0.8, "canyon_rust"), (0.8, 1.55, "canyon_orange"), (1.55, 9.0, "canyon_cream")], top="canyon_top", floor="canyon_floor",
                   worn=("ramp_worn", "ramp_worn_b", "ramp_worn_c"), rock=("canyon_side", "canyon_rust", "canyon_orange")),
    "badlands": dict(bands=[(0.0, 0.85, "mesa_a"), (0.85, 1.6, "mesa_b"), (1.6, 9.0, "mesa_c")], top="mesa_top", floor="badlands_ground",
                     worn=("ramp_worn_red", "ramp_worn_red_b", "ramp_worn_red_c"), rock=("mesa_b", "mesa_a", "mesa_c")),
}
LANES = {"A": (0.68, 0.72), "B": (0.62, 0.72), "C": (-0.75, 0.7), "D": (-0.95, 0.7), "E": (-0.72, 0.7)}  # the lane's centre at the foot and at the top
NAMES = {"A": "A cut path", "B": "B steps", "C": "C timber", "D": "D rubble", "E": "E dry stone"}


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class Bench(Run):
    def __init__(self, style, h, colour, bend=0.0):
        self.style, self.h, self.c, self.bend = style, h, COLOURS[colour], bend
        super().__init__(hk.Piece(f"bench_{style}_{colour}_{h}"), random.Random(f"{style}{h}{colour}"), COLOURS[colour]["rock"])
        self.tris = {"ramp": 0, "wall": 0}
        self.cat = "wall"
        self.run = h / math.tan(math.radians(TILT)) + 0.5  # eased over 0.5 at each end, so the middle is at TILT
        self.s0, self.s1 = -4.2, self.run + 3.4
        self.d0, self.d1 = -4.0, 3.4
        self.jag = {}
        self.stations = self._stations()

    # wall space to the world
    def W(self, s, d, z):
        if not self.bend:
            return Vector((s, d, z))
        R, a = 5.0, self.bend  # concave if a > 0: the wall wraps round the floor; the arc is at the ramp's upper half
        s_a = self.run * 0.5
        s_b = s_a + abs(a) * R
        k = 1 if a > 0 else -1
        def along(t):
            return (t, 0.0) if t <= s_a else None
        if s <= s_a:
            return Vector((s, d, z))
        th = min(s, s_b) - s_a
        th = th / R
        cx, cy = s_a, -k * R
        rad = R + k * d
        x, y = cx + rad * math.sin(th), cy + k * rad * math.cos(th)
        if s > s_b:
            over = s - s_b
            x += over * math.cos(th)
            y += k * over * math.sin(th)
        return Vector((x, y, z))

    def poly(self, pts, mat, away=None):
        if len(pts) >= 3:
            self.tris[self.cat] += len(pts) - 2
        super().poly(pts, mat, away)

    # the lane
    def path_z(self, s):
        """The route's height: flat, eased, straight at TILT, eased, flat."""
        e, slope = 0.5, math.tan(math.radians(TILT))
        if s <= 0:
            return 0.0
        if s >= self.run:
            return self.h
        if s < e:
            return slope * s * s / (2 * e)
        if s > self.run - e:
            u = self.run - s
            return self.h - slope * u * u / (2 * e)
        return slope * (s - e / 2)

    def centre(self, s):
        a, b = LANES[self.style]
        if s < 0:
            return a + (min(a, -0.7) - a) * smooth(-s / 1.2)  # coming in off the floor, clear of the wall
        if s > self.run:
            return b + 0.4 * smooth((s - self.run) / 0.9)  # and on over the top, clear of the edge
        return a + (b - a) * smooth((s - 0.25 * self.run) / (0.75 * self.run))

    def edge(self, s):
        return self.centre(s) - WIDTH / 2

    def inner(self, s):
        return self.centre(s) + WIDTH / 2

    def cut(self, s):
        """How far the wall above the lane is set back: nothing away from the ramp, opening over the foot."""
        return self.inner(s) + 0.12 if s >= self.foot_cut() else (self.inner(self.foot_cut()) + 0.12) * smooth((s - self.foot_cut() + 2.3) / 2.3)

    def foot_cut(self):
        """Where the cut has reached its full depth: the lane leaves the wall's face."""
        s = 0.0
        while self.inner(s) < 0.15 and s < self.run:
            s += 0.05
        return s

    # the wall
    def _stations(self):
        st, s = [], self.s0
        while s < self.s1:
            st.append(s)
            s += self.rng.uniform(0.32, 0.55)
        st.append(self.s1)
        for z in (b[1] for b in self.c["bands"] if b[1] < self.h):  # the lane crosses a band here
            lo, hi = 0.0, self.run
            for _ in range(30):
                m = (lo + hi) / 2
                lo, hi = (m, hi) if self.path_z(m) < z else (lo, m)
            st.append(lo)
        st += [0.0, self.foot_cut(), self.run]
        st = sorted(set(round(x, 4) for x in st))
        return [x for k, x in enumerate(st) if k == 0 or x - st[k - 1] > 0.03]

    def jagged(self, s, k):
        """The wall's face at a station in band k: each band set back a little further, on the same jagged line."""
        key = round(s, 4)
        if key not in self.jag:
            self.jag[key] = (self.rng.uniform(-0.09, 0.09), [self.rng.uniform(-0.05, 0.05) for _ in range(4)])
        j, each = self.jag[key]
        return j + each[k] + k * 0.13

    def bands(self):
        return [(lo, min(hi, self.h), m) for lo, hi, m in self.c["bands"] if lo < self.h]

    def banded(self, offset, zlo, zhi):
        """Banded rock between two height lines, band by band, column by column, each band's bottom and top clipped to them; ledges where a band sets back."""
        bands = self.bands()
        st = self.stations
        for s0, s1 in zip(st, st[1:]):
            for k, (lo, hi, mat) in enumerate(bands):
                d0, d1 = offset(s0) + self.jagged(s0, k), offset(s1) + self.jagged(s1, k)
                # in this column every line is straight, so take the corners
                a0, a1 = max(lo, zlo(s0)), max(lo, zlo(s1))
                b0, b1 = min(hi, zhi(s0)), min(hi, zhi(s1))
                if b0 <= a0 + 1e-4 and b1 <= a1 + 1e-4:
                    continue
                if b0 < a0:
                    b0 = a0
                if b1 < a1:
                    b1 = a1
                self.poly([(s0, d0, a0), (s1, d1, a1), (s1, d1, b1), (s0, d0, b0)], mat)
                if k + 1 < len(bands) and hi < self.h and b0 >= hi - 1e-4 and b1 >= hi - 1e-4:  # the ledge
                    u0, u1 = offset(s0) + self.jagged(s0, k + 1), offset(s1) + self.jagged(s1, k + 1)
                    self.poly([(s0, d0, hi), (s1, d1, hi), (s1, u1, hi), (s0, u0, hi)], mat)

    def build_wall(self):
        z = self.path_z
        h = self.h
        self.banded(lambda s: 0.0, lambda s: 0.0, lambda s: min(z(s), h))  # below the lane: the old face, untouched
        self.banded(lambda s: self.cut(s) if s <= self.run else 0.0, lambda s: z(s), lambda s: h)  # above it: the same strata, set back
        st = self.stations
        k_top = len(self.bands()) - 1
        for s0, s1 in zip(st, st[1:]):
            r0 = self.jagged(s0, k_top) if s0 >= self.run else self.cut(s0) + self.jagged(s0, k_top)
            r1 = self.jagged(s1, k_top) if s1 > self.run else self.cut(s1) + self.jagged(s1, k_top)
            self.poly([(s0, r0, h), (s1, r1, h), (s1, self.d1, h), (s0, self.d1, h)], self.c["top"])
            if s0 >= -0.05 and s1 <= self.run + 1e-3:  # the lane's inner side, to the foot of the cut, so no slit shows
                ka = max((k for k, b in enumerate(self.bands()) if b[0] <= (z(s0) + z(s1)) / 2), default=0)
                self.poly([(s0, self.inner(s0) - 0.02, z(s0)), (s1, self.inner(s1) - 0.02, z(s1)), (s1, self.cut(s1) + self.jagged(s1, ka) + 0.02, z(s1)), (s0, self.cut(s0) + self.jagged(s0, ka) + 0.02, z(s0))], self.c["worn"][1])
            # the lane's outer shoulder, from the old face to the lane's edge
            if z(s0) > 0.0 or z(s1) > 0.0:
                ka = max((k for k, b in enumerate(self.bands()) if b[0] <= (z(s0) + z(s1)) / 2), default=0)
                f0, f1 = self.jagged(s0, ka), self.jagged(s1, ka)
                e0, e1 = max(self.edge(s0), f0), max(self.edge(s1), f1)
                self.poly([(s0, f0, z(s0)), (s1, f1, z(s1)), (s1, e1, z(s1)), (s0, e0, z(s0))], self.bands()[ka][2])
        # past the lane's top the old face runs on to the top, and the rim closes over what the cut left
        s = self.run
        for s0, s1 in zip(st, st[1:]):
            self.poly([(s0, self.d0, 0), (s1, self.d0, 0), (s1, 2.0, 0), (s0, 2.0, 0)], self.c["floor"])
        for s_ in (self.s0, self.s1):
            for lo, hi, mat in self.bands():
                self.poly([(s_, 0, lo), (s_, self.d1, lo), (s_, self.d1, hi), (s_, 0, hi)], mat)

    def lane_surface(self, s_from, s_to, lanes=(0.0, 0.26, 0.74, 1.0), step=0.34):
        """The worn surface: three strips across, broken along its length into patches of uneven tone, with a loose, irregular edge."""
        worn = self.c["worn"]
        rng = self.rng
        s = s_from
        prev = None
        while s < s_to - 1e-3:
            nxt = min(s_to, s + rng.uniform(0.75, 1.25) * step)
            cuts = [(lanes[k] + (rng.uniform(-0.07, 0.07) if 0 < k < 3 else 0)) for k in range(4)]
            ends = self._lane_row(nxt, cuts)
            if prev is None:
                prev = self._lane_row(s, [lanes[k] for k in range(4)])
            for k in range(3):
                mat = worn[2] if k == 1 and rng.random() < 0.75 else worn[0] if k == 1 or rng.random() < 0.6 else worn[1]
                self.poly([prev[k], ends[k], ends[k + 1], prev[k + 1]], mat)
            prev, s = ends, nxt

    def _lane_row(self, s, cuts):
        z = self.path_z(s)
        a, b = self.edge(s), self.inner(s)
        return [(s, a + (b - a) * c, z + (0.015 * self.rng.uniform(-1, 1) if 0 < c < 1 else 0)) for c in cuts]

    # the styles
    def build(self):
        self.build_wall()
        self.cat = "ramp"
        getattr(self, "style_" + self.style)()
        self.cat = "wall"

    def lip(self, s_from, s_to, every=0.42, keep=0.72, h_=(0.1, 0.24)):
        """A low broken lip along the lane's outer edge: stones with gaps, none inside the lane."""
        rng = self.rng
        s = s_from
        while s < s_to:
            if rng.random() < keep:
                r = rng.uniform(0.09, 0.16)
                self.chunk(s, self.edge(s) - r * 0.3, self.path_z(s), r, rng.uniform(*h_), self.c["rock"][rng.randrange(3)])
            s += every * rng.uniform(0.7, 1.3)

    def style_A(self):
        self.lane_surface(-0.05, self.run + 0.2)
        self.lip(0.35, self.run - 0.05)
        rng = self.rng
        for k in range(5):  # fallen from the cut, at the foot of its inner wall
            s = rng.uniform(0.3, self.run - 0.4)
            self.chunk(s, self.inner(s) + 0.1, self.path_z(s), rng.uniform(0.08, 0.13), rng.uniform(0.08, 0.16), self.c["rock"][k % 3])

    def style_B(self):
        self.steps()

    def style_C(self):
        self.timber()

    def style_D(self):
        """A heap of broken rock: a rough grid of jittered points falling from the lane to the floor, wider than the lane, with blocks along both flanks."""
        rng = self.rng
        nu, nv = 13, 7
        c = self.c
        grid = {}
        for u in range(nu + 1):
            s = -0.7 + (self.run + 0.6) * u / nu
            for v in range(nv + 1):
                f = v / nv  # 0 at the outer foot, 1 at the wall
                lane_z = self.path_z(max(0.0, min(self.run, s)))
                e = self.edge(s) - 0.45 - 0.3 * (1 - lane_z / self.h)
                top = self.inner(s)
                d = e + (top - e) * f + rng.uniform(-0.07, 0.07)
                s = s if u in (0, nu) else s + rng.uniform(-0.09, 0.09)
                lane_z = self.path_z(max(0.0, min(self.run, s)))
                on_lane = d >= self.edge(s) - 0.02
                z = lane_z if on_lane else lane_z * smooth((d - e) / max(0.01, self.edge(s) - e)) ** 0.8
                if not on_lane and 0 < z:
                    z += rng.uniform(-0.05, 0.1)
                grid[u, v] = (s, d, max(0.0, z + (rng.uniform(-0.012, 0.012) if on_lane else 0)))
        for u in range(nu):
            for v in range(nv):
                q = [grid[u, v], grid[u + 1, v], grid[u + 1, v + 1], grid[u, v + 1]]
                mids = sum(p[1] for p in q) / 4
                s_ = sum(p[0] for p in q) / 4
                onlane = mids > self.edge(s_) and mids < self.inner(s_)
                mat = c["worn"][rng.randrange(3)] if onlane else c["rock"][rng.randrange(3)]
                if (u + v) % 2:
                    self.poly(q[:3], mat)
                    self.poly([q[0], q[2], q[3]], mat)
                else:
                    self.poly([q[0], q[1], q[3]], mat)
                    self.poly(q[1:], mat)
        for k in range(44):
            s = rng.uniform(-0.6, self.run - 0.1)
            lane_z = self.path_z(max(0, s))
            e = self.edge(s)
            d = rng.uniform(e - 0.75, e - 0.12)
            t = max(0.0, min(1.0, (d - (e - 0.8)) / 0.8))
            r = rng.uniform(0.12, 0.3) * (1.2 - t * 0.5)
            self.chunk(s, d, lane_z * t * t, r, r * rng.uniform(0.7, 1.4), c["rock"][rng.randrange(3)], sides=5)
        for k in range(6):
            s = rng.uniform(self.foot_cut() + 0.2, self.run - 0.1)
            self.chunk(s, self.inner(s) + 0.02, self.path_z(s), rng.uniform(0.09, 0.15), rng.uniform(0.1, 0.22), c["rock"][k % 3])

    def style_E(self):
        """A built ramp: the wedge's side becomes a laid wall of rough courses, its top line stepping up with the lane, with a packed lane and edge stones."""
        rng = self.rng
        c = self.c
        self.lane_surface(-0.2, self.run + 0.2)
        if self.h > 2:  # the raiders' mesa: stone of its own rock
            tones = ("mesa_a", "mesa_a", "mesa_c")
        else:
            tones = ("canyon_orange", "canyon_orange", "canyon_rust")
        st = [s_ for s_ in self.stations if 0 <= s_ <= self.run]
        for a, b in zip(st, st[1:]):
            if self.edge(a) < 0 or self.edge(b) < 0:
                self.poly([(a, self.edge(a) - 0.02, 0), (b, self.edge(b) - 0.02, 0), (b, self.edge(b) - 0.02, self.path_z(b)), (a, self.edge(a) - 0.02, self.path_z(a))], "canyon_side" if self.h < 2 else "mesa_b")
        row = 0
        z = 0.0
        ch = 0.27
        while z < self.h:
            s = rng.uniform(-0.22, 0.05) if row % 2 else 0.0
            # where this course meets the lane
            lo, hi = 0.0, self.run
            for _ in range(24):
                m = (lo + hi) / 2
                lo, hi = (m, hi) if self.path_z(m) < z + ch * 0.5 else (lo, m)
            start = lo
            s = start
            while s < self.run + 0.1:
                w = rng.uniform(0.5, 0.82)
                s1 = s + w
                e0 = self.edge(s + w / 2)
                if e0 < -0.02:
                    self.block(s, s1 - 0.012, e0 - 0.14 + rng.uniform(-0.03, 0.03), e0 - 0.01, z, z + ch - 0.02, tones[rng.randrange(3)], skew=0.006)
                s = s1
            z += ch
            row += 1
        self.lip(0.3, self.run - 0.05, every=0.36, keep=0.82, h_=(0.05, 0.13))


def add_label(text, scale=1.0, up=False):
    cam = bpy.context.scene.camera
    cu = bpy.data.curves.new("label", "FONT")
    cu.body = text
    cu.size = 0.055 * scale
    o = bpy.data.objects.new("label", cu)
    m = cam.rotation_euler.to_matrix()
    o.location = cam.location + m @ Vector((-0.31 * scale, (0.15 if up else -0.2) * scale, -1.0))
    o.rotation_euler = cam.rotation_euler
    cu.materials.append(hk.material("timber"))
    bpy.context.scene.collection.objects.link(o)


def route(b, n=60):
    """The line the minis walk: foot, up the lane, over the top."""
    out = []
    for k in range(n + 1):
        s = -1.2 + (b.run + 2.4) * k / n
        out.append((s, b.centre(s), b.path_z(s)))
    return out


def minis_on(b, minis, col):
    """One at the foot and one partway, one over the top; they stand as the engine stands them, upright on the route."""
    spots = [("standin_small", -0.55), ("standin_hero", b.run * 0.48), ("standin_fluffy", b.run + 0.55)]
    for kind, s in spots:
        o = bpy.data.objects.new(kind, minis[kind].data)
        o.location = b.W(s, b.centre(s), b.path_z(s))
        o.rotation_euler.z = 0.0
        col.objects.link(o)


def measure(b, obj, mini_r):
    """Walks a mini's round base up the route over the built surface: how far the ground comes up through it and how far it floats, and whether anything but the ground gets in the way."""
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(obj, dg)
    sinks, floats, hits = 0.0, 0.0, 0
    where_s = where_f = None
    prev = None
    steep = 0.0
    for s, d, z in route(b, 160):
        if prev:
            run = math.hypot(s - prev[0], d - prev[1])
            if run > 1e-6:
                steep = max(steep, math.degrees(math.atan2(abs(z - prev[2]), run)))
        prev = (s, d, z)
        heights = []
        for a in range(8):
            q = (s + mini_r * math.cos(a * PI / 4), d + mini_r * math.sin(a * PI / 4))
            hit = tree.ray_cast(b.W(q[0], q[1], z + 1.6), Vector((0, 0, -1)), 4.0)
            if hit[0] is not None:
                heights.append(hit[0].z - b.path_z(q[0]))
        if heights:
            if max(heights) > sinks:
                sinks, where_s = max(heights), (round(s, 2), round(d, 2))
            second = -sorted(heights)[1]  # one point down a plank's gap isn't a drop
            if second > floats:
                floats, where_f = second, (round(s, 2), round(d, 2))
        for hz in (0.5, 0.9):  # at body height, the wall of the lane or a rail
            for a in range(8):
                o_ = b.W(s, d, z + hz)
                t = b.W(s + 0.32 * math.cos(a * PI / 4), d + 0.32 * math.sin(a * PI / 4), z + hz)
                if tree.ray_cast(o_, (t - o_).normalized(), 0.32)[0] is not None:
                    hits += 1
    return dict(route_tilt=round(steep, 1), sinks=round(sinks, 3), floats=round(floats, 3), body_hits=hits, at_sink=where_s, at_float=where_f)


def stage_of(view, b):
    scene = bpy.context.scene
    from_rp = globals()["stage"]
    centre = b.W(b.run / 2, -0.6, b.h * 0.4)
    if view == "game":
        from_rp(centre, 13.5, 50)
    elif view == "map":
        from_rp(centre, 54, 50)
    elif view == "low":
        from_rp(centre, 10, 12, lens=26)
        cam = scene.camera
        eye = b.W(-2.7, -3.4, 0.75)
        at = b.W(b.run * 0.55, 0.1, b.h * 0.5)
        cam.location = eye
        cam.rotation_euler = (at - eye).to_track_quat("-Z", "Y").to_euler()


def stage(target, distance, elevation_deg, lens=50):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = CELL
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("backdrop")
    world.use_nodes = True
    nodes = world.node_tree.nodes
    nodes["Background"].inputs["Color"].default_value = hk.material("backdrop").diffuse_color
    nodes["Background"].inputs["Strength"].default_value = 0.75
    scene.world = world
    el = math.radians(elevation_deg)
    cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    cam.data.lens = lens
    cam.location = target + Vector((0, -distance * math.cos(el), distance * math.sin(el)))
    cam.rotation_euler = (PI / 2 - el, 0, 0)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.5
    sun.data.angle = math.radians(8)
    sun.rotation_euler = (math.radians(45), math.radians(-30), math.radians(-35))
    scene.collection.objects.link(sun)


CELL = (800, 500)
SETUPS = {"canyon": (1.9, "canyon"), "stronghold": (2.3, "badlands")}


def cell(style, setup, view, minis_path, bend=0.0, want_measure=False):
    hk.empty_scene()
    h, colour = SETUPS[setup]
    with bpy.data.libraries.load(minis_path, link=False) as (src, dst):
        dst.objects = list(src.objects)
    minis = {o.name: o for o in dst.objects}
    b = Bench(style, h, colour, bend)
    b.build()
    col = hk.new_collection("study")
    obj = finish(b.p, col)
    minis_on(b, minis, col)
    stage_of(view, b)
    if view == "map":
        bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1600, 1000
    add_label(f"{NAMES[style]}  {h}" + ("  bend in" if bend > 0 else "  bend out" if bend < 0 else ""), 0.5 if view == "map" else 1.0, up=view == "low")
    out = os.path.join(TMP, f"{style}_{setup}_{view}_{bend}.png")
    bpy.context.scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    if want_measure:
        r = measure(b, obj, MINI_R)
        plain = Bench(style, h, colour)
        plain.path_z, plain.cut = (lambda s: 0.0), (lambda s: 0.0)
        plain.build_wall()
        plain.p.bm.free()
        print("MEASURE", style, setup, "bend" if bend else "straight", "tris ramp", b.tris["ramp"], "wall extra", b.tris["wall"] - plain.tris["wall"], r, "run", round(b.run, 2))
    return out


def finish(piece, col):
    mesh = bpy.data.meshes.new(piece.name)
    piece.bm.to_mesh(mesh)
    piece.bm.free()
    for m in piece.mats:
        mesh.materials.append(hk.material(m))
    obj = bpy.data.objects.new(piece.name, mesh)
    col.objects.link(obj)
    return obj


def sheet(paths, cols, name):
    imgs = []
    for p in paths:
        im = bpy.data.images.load(p)
        px = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], im.channels)[:, :, :4]
        if im.size[0] > CELL[0]:  # the middle of a full frame
            y_, x_ = (im.size[1] - CELL[1]) // 2, (im.size[0] - CELL[0]) // 2
            px = px[y_:y_ + CELL[1], x_:x_ + CELL[0]]
        imgs.append(px)
        bpy.data.images.remove(im)
    h, w = imgs[0].shape[:2]
    rows = math.ceil(len(imgs) / cols)
    gap = 6
    full = np.ones(((h + gap) * rows - gap, (w + gap) * cols - gap, 4), dtype=np.float32)
    for k, im in enumerate(imgs):
        r, c = k // cols, k % cols
        y = (rows - 1 - r) * (h + gap)  # images run from the bottom
        full[y:y + h, c * (w + gap):c * (w + gap) + w] = im
    out_dir = os.path.join(hk.ART, "preview")
    n = hk.next_number(out_dir, name, "png")
    path = os.path.join(out_dir, f"{name}_v{n}.png")
    img = bpy.data.images.new(name, full.shape[1], full.shape[0], alpha=True)
    img.pixels = full.ravel().tolist()
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    print("SHEET", path)


TMP = os.environ.get("RAMP_TMP", "/tmp/ramp_study")
MINI_R = 0.5  # the stand-ins' hex base is 1.04 across

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    flags = dict(a[2:].split("=", 1) if "=" in a else (a[2:], True) for a in args)
    styles = flags.get("styles", "ABCDE")
    sheets = flags.get("sheet", "game,low,map").split(",")
    os.makedirs(TMP, exist_ok=True)
    minis_blend = os.path.join(hk.ART, "minis", "standins", "standin_minis_v1.blend")
    want = bool(flags.get("measure"))
    if "game" in sheets:
        sheet([cell(s, st, "game", minis_blend, want_measure=want) for s in styles for st in SETUPS], 2, "ramp_study_game")
    if "low" in sheets:
        sheet([cell(s, st, "low", minis_blend) for s in styles for st in SETUPS], 2, "ramp_study_low")
    if "map" in sheets:
        sheet([cell(s, st, "map", minis_blend) for s in styles for st in SETUPS], 2, "ramp_study_map")
    if "bend" in sheets:
        sheet([cell(s, "canyon", "game", minis_blend, bend=a, want_measure=want) for s in styles for a in (0.9, -0.9)], 2, "ramp_study_bend")
