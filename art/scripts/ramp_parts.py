"""The ramp styles Ethan picked from the study (art/scripts/ramp_study.py), as parts anything can use: Run.timber (the Raider Stronghold) and Run.steps (cut-in steps). The canyon's cut path is canyon.py's own, on its real rock.

A Run is laid out in its own frame: s along the climb, d across it (edge(s) on the open side to inner(s) on the wall side), z up. Subclass it, set run and the three functions, map the frame to your piece's in W. Blender only.
"""
import math

from mathutils import Vector


class Run:
    run = 4.0
    deck_over = 0.25  # planks past the top of the climb
    inner_over = (0.1, 0.2)  # how far planks reach past inner(s), into the wall
    rail_from = 0.25
    foot_stones = 3
    flat_end = False  # a flat landing past the climb, standing on its own bent

    def __init__(self, piece, rng, rock=("canyon_side", "canyon_rust", "canyon_orange")):
        self.p, self.rng, self.rock = piece, rng, rock

    def W(self, s, d, z):
        return Vector((s, d, z))

    def edge(self, s):
        return 0.0

    def inner(self, s):
        return 1.2

    def path_z(self, s):
        return 0.0

    def on_floor(self, s, d):
        """Does a post at d stand on the floor, or is there rock there?"""
        return d < 0.02

    def poly(self, pts, mat, away=None):
        """One face, looking up, or away from a point inside its part."""
        q = [self.W(*x) for x in pts]
        if len(q) < 3:
            return
        n = Vector((0, 0, 0))
        for a, b in zip(q, q[1:] + q[:1]):
            n += a.cross(b)
        if away is not None:
            flip = n.dot(sum(q, Vector((0, 0, 0))) / len(q) - self.W(*away)) < 0
        else:
            flip = n.z < 0
        f = self.p.bm.faces.new([self.p.bm.verts.new(x) for x in (q[::-1] if flip else q)])
        f.material_index = self.p._slot(mat)
        self.p.surface.add(f)

    def chunk(self, s, d, z, r, h, mat, sides=5):
        """A broken stone: a leaning, uneven frustum with no bottom."""
        rng = self.rng
        a0 = rng.uniform(0, 6.28)
        lean = (rng.uniform(-0.25, 0.25) * r, rng.uniform(-0.25, 0.25) * r)
        rad = [r * rng.uniform(0.7, 1.15) for _ in range(sides)]
        low = [(s + rad[k] * math.cos(a0 + 6.283 * k / sides), d + rad[k] * math.sin(a0 + 6.283 * k / sides), z - 0.04) for k in range(sides)]
        up = [(s + lean[0] + 0.62 * rad[k] * math.cos(a0 + 6.283 * k / sides), d + lean[1] + 0.62 * rad[k] * math.sin(a0 + 6.283 * k / sides), z + h * rng.uniform(0.8, 1.15)) for k in range(sides)]
        for k in range(sides):
            j = (k + 1) % sides
            self.poly([low[k], low[j], up[j], up[k]], mat, away=(s, d, z + h / 2))
        self.poly(up, mat)

    def beam(self, a, b, r, mat, sides=4):
        """A squared timber between two points, closed at b."""
        a, b = Vector(a), Vector(b)
        ax = (b - a).normalized()
        u = ax.cross(Vector((0.01, 1, 0.3))).normalized()
        v = ax.cross(u)
        ring = lambda c: [tuple(c + r * (math.cos(6.283 * (k + 0.5) / sides) * u + math.sin(6.283 * (k + 0.5) / sides) * v)) for k in range(sides)]
        ra, rb = ring(a), ring(b)
        mid = tuple((a + b) / 2)
        for k in range(sides):
            j = (k + 1) % sides
            self.poly([ra[k], ra[j], rb[j], rb[k]], mat, away=mid)
        self.poly(rb, mat, away=mid)

    def block(self, s0, s1, d0, d1, z0, z1, mat, skew=0.0, side=None):
        """A rough block: its top, the face toward the open side and both ends."""
        j = lambda: self.rng.uniform(-skew, skew)
        t = [(s0 + j(), d0 + j(), z1 + j() * 0.5), (s1 + j(), d0 + j(), z1 + j() * 0.5), (s1 + j(), d1 + j(), z1 + j() * 0.5), (s0 + j(), d1 + j(), z1 + j() * 0.5)]
        b = [(x[0], x[1], z0) for x in t]
        mid = ((s0 + s1) / 2, (d0 + d1) / 2, (z0 + z1) / 2)
        side = side or mat
        self.poly(t, mat)
        self.poly([b[0], b[1], t[1], t[0]], side, away=mid)
        self.poly([b[1], b[2], t[2], t[1]], side, away=mid)
        self.poly([b[3], b[0], t[0], t[3]], side, away=mid)

    def timber(self):
        """Planks on a dark under-deck, two stringers, bents standing on the ground, and a rope rail on the open side."""
        rng = self.rng
        s = -0.05
        planks = ("ramp_plank", "ramp_plank_b", "ramp_plank_c")
        end = self.run + self.deck_over
        while s < end - 1e-3:
            s1 = min(end, s + rng.uniform(0.2, 0.27))
            z0, z1 = self.path_z(s), self.path_z(s1)
            mid = (s + s1) / 2
            e = self.edge(mid) - rng.uniform(0.04, 0.12)
            i = self.inner(mid) + rng.uniform(*self.inner_over)
            mat = planks[rng.randrange(3)]
            t = 0.05
            gap = 0.02
            self.poly([(s, e, z0), (s1 - gap, e, z1), (s1 - gap, i, z1), (s, i, z0)], mat)
            self.poly([(s, e, z0 - t), (s1 - gap, e, z1 - t), (s1 - gap, e, z1), (s, e, z0)], mat, away=(mid, (e + i) / 2, z0))
            self.poly([(s1 - gap, e, z1), (s1 - gap, i, z1), (s1 - gap, i, z1 - t), (s1 - gap, e, z1 - t)], mat, away=(s, (e + i) / 2, z0))
            ue, ui = self.edge(mid) + 0.02, self.inner(mid)  # seen through the gaps, and something to walk on over them
            self.poly([(s, ue, z0 - 0.04), (s1, ue, z1 - 0.04), (s1, ui, z1 - 0.04), (s, ui, z0 - 0.04)], "ramp_post")
            s = s1
        for f in (0.1, 0.9):
            line = [(s_, self.edge(s_) + (self.inner(s_) - self.edge(s_)) * f, self.path_z(s_) - 0.1) for s_ in (0.05 + (self.run - 0.1) * k / 5 for k in range(6))]
            for a, b in zip(line, line[1:]):
                self.beam(a, b, 0.05, "ramp_post")
        step = self.run * 0.2
        s = step
        while s < self.run - 0.1:
            z = self.path_z(s) - 0.12
            a, b = (s, self.edge(s) + 0.1, z), (s, self.inner(s) - 0.1, z)
            if z > 0.28:
                self.beam((s, self.edge(s) - 0.05, z), (s, self.inner(s) + 0.05, z), 0.05, "ramp_post")  # the cap
                self.beam((s, a[1] - 0.14, 0.0), a, 0.055, "ramp_post")
                if self.on_floor(s, b[1]):
                    self.beam((s, b[1] + 0.02, 0.0), b, 0.055, "ramp_post")
                self.beam((s, a[1] - 0.05, 0.05), (s, b[1], z - 0.02), 0.032, "ramp_plank_b")  # a brace
                if s - step > 0.2:
                    self.beam((s - step * 0.92, a[1], max(0.05, self.path_z(s - step) - 0.15)), (s, a[1], 0.08), 0.03, "ramp_plank_b")
            s += step
        z = self.path_z(self.run) - 0.12  # the last bent, under the end of the deck
        if z > 0.28 and self.flat_end:
            s = self.run - 0.15
            self.beam((s, self.edge(s) - 0.05, z), (s, self.inner(s) + 0.05, z), 0.05, "ramp_post")
            self.beam((s, self.edge(s) - 0.04, 0.0), (s, self.edge(s) + 0.1, z), 0.055, "ramp_post")
            self.beam((s, self.edge(s) - 0.05, 0.05), (s, self.inner(s) - 0.1, z - 0.02), 0.032, "ramp_plank_b")
        tops = []
        s = self.rail_from
        while s < self.run - 0.1:
            e = self.edge(s) - 0.02
            self.beam((s, e, self.path_z(s) - 0.15), (s, e, self.path_z(s) + 0.42), 0.035, "ramp_post")
            tops.append((s, e, self.path_z(s) + 0.36))
            s += self.run / 4.2
        for a, b in zip(tops, tops[1:]):
            m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2 - 0.07)
            self.beam(a, m, 0.012, "ramp_rope", sides=3)
            self.beam(m, b, 0.012, "ramp_rope", sides=3)
        for k in range(self.foot_stones):  # stones against the foot's open side, clear of the way on
            self.chunk(0.1 + 0.3 * k, self.edge(0) - 0.2 + rng.uniform(-0.04, 0.04), 0.0, rng.uniform(0.08, 0.13), 0.08, self.rock[k % 3], sides=4)

    def steps(self, rise_each=0.19):
        """Adobe treads, light on top, darker risers and sides, each straddling the climb so a mini's base is half a riser out at most."""
        rng = self.rng
        h = self.path_z(self.run)
        n = max(8, round(h / rise_each))
        rise = h / n

        def at(z):
            lo, hi = 0.0, self.run
            for _ in range(24):
                m = (lo + hi) / 2
                lo, hi = (m, hi) if self.path_z(m) < z else (lo, m)
            return lo

        risers = [at((k + 0.5) * rise) for k in range(n)] + [self.run + 0.1]
        for k in range(n):
            s0, s1 = risers[k], risers[k + 1]
            z1 = (k + 1) * rise
            mid = (s0 + s1) / 2
            e, i = self.edge(mid), self.inner(mid)
            tone = ("ramp_adobe", "ramp_adobe_c")[rng.randrange(2)]
            self.block(s0, s1 + 0.03, e - 0.03, i + 0.1, max(0.0, z1 - rise * 1.5), z1, tone, skew=0.014, side="ramp_adobe_b")
            if rng.random() < 0.55:  # a stone set in the tread's edge
                self.chunk(s0 + 0.06, rng.uniform(e + 0.12, i - 0.12), z1 - 0.02, 0.07, 0.035, self.rock[k % 3], sides=4)
