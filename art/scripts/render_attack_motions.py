"""Attack motions by kind (07 → Characters are tabletop-style minis): whole-mini moves plus flat low-poly effects, 2-4 options per
kind, side by side in one short clip per kind for Ethan to pick from. Nothing here is decided: every move, colour and timing is a proposal.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_attack_motions.py -- OUT_DIR [kind ...]
Writes OUT_DIR/attack_<kind>_vN.mp4 and a still contact strip attack_<kind>_vN.png (the frame where each option lands). Each clip
plays its motions twice at real speed, then once at half speed. Times are in seconds from the move's start; the attacker's part
stays under 0.6 s, as asked, and effects and the hit mini's settle may run a little past it.
"""
import math
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector as V  # noqa: E402

import build_hero_kit as hb  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402

S = hb.SWATCHES
FPS = 60          # rendered; the clip plays at 30, so real speed takes every other frame and half speed takes them all
LEAD = 0.25       # still time before each move
CYCLE = 1.5       # one pass, still time included
PANE = (560, 380)
CHECK = os.environ.get("ATK_CHECK")  # a folder for a filmstrip of key moments, top to bottom, for checking
CHECK_TIMES = (0.0, 0.08, 0.14, 0.2, 0.28, 0.38, 0.5, 0.7)
SQ3 = math.sqrt(3)
GRASS = ("#A9CD84", "#9FC67B", "#B2D38D")
GAP = "#86AD6A"


# --- Easing -----------------------------------------------------------------

def seg(s, a, b):
    """0 before a, 1 after b, linear between."""
    return 0.0 if s <= a else 1.0 if s >= b else (s - a) / (b - a)


def out(u):
    return 1 - (1 - u) ** 2


def inn(u):
    return u * u


def smooth(u):
    return u * u * (3 - 2 * u)


def bump(u):
    """0 → 1 → 0 over u in 0..1."""
    return math.sin(math.pi * min(max(u, 0.0), 1.0))


def settle(v):
    """1 at v=0 easing to 0 at v=1 with one small overshoot."""
    v = min(max(v, 0.0), 1.0)
    return (1 - v) ** 2 * math.cos(1.5 * math.pi * v)


def cell(q, r):
    """Cells are 1.0 across their flats; neighbours lie along +X and at ±60°."""
    return V((q + r / 2, r * SQ3 / 2, 0))


# --- Materials and effect meshes --------------------------------------------

def lin(hexcol):
    return tuple(hk.srgb_to_linear(int(hexcol[i:i + 2], 16) / 255) for i in (1, 3, 5))


def glow(hexcol, name=None):
    """Flat unlit colour that can fade: emission mixed with transparency, its alpha set per frame."""
    m = bpy.data.materials.new(name or f"glow{hexcol}")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    em, tr, mix, outp = nt.nodes.new("ShaderNodeEmission"), nt.nodes.new("ShaderNodeBsdfTransparent"), nt.nodes.new("ShaderNodeMixShader"), nt.nodes.new("ShaderNodeOutputMaterial")
    em.inputs["Color"].default_value = (*lin(hexcol), 1)
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], outp.inputs["Surface"])
    mix.inputs[0].default_value = 1.0
    m.surface_render_method = "BLENDED"
    m.use_backface_culling = False
    m["mix"] = mix.name
    return m


def lit(hexcol):
    m = bpy.data.materials.new(f"lit{hexcol}")
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*lin(hexcol), 1)
    b.inputs["Roughness"].default_value = 0.9
    return m


def set_alpha(ob, a):
    for m in ob.data.materials:
        if "mix" in m:
            m.node_tree.nodes[m["mix"]].inputs[0].default_value = max(0.0, min(1.0, a))


def mesh_ob(name, bm, mats, col):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    ob.visible_shadow = False
    col.objects.link(ob)
    return ob


def ico(col, r, mat, sub=1, name="orb"):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    return mesh_ob(name, bm, [mat], col)


def spikes(col, n, length, width, mat, up=0.0, name="burst", seed=0):
    """A star of flat-shaded spikes from the origin, mostly outward and a bit up."""
    bm = bmesh.new()
    for k in range(n):
        a = 2 * math.pi * (k + 0.37 * ((k * 7 + seed) % 3)) / n
        d = V((math.cos(a), math.sin(a), up + 0.25 * ((k + seed) % 2))).normalized()
        side = d.cross(V((0, 0, 1))).normalized() * width
        if side.length < 1e-6:
            side = V((width, 0, 0))
        lift = d.cross(side).normalized() * width
        tip = d * length * (0.75 + 0.25 * ((k + seed) % 3) / 2)
        vs = [bm.verts.new(p) for p in (side, lift, -side, -lift, tip)]
        for i in range(4):
            bm.faces.new((vs[i], vs[(i + 1) % 4], vs[4]))
    return mesh_ob(name, bm, [mat], col)


def arc(col, r0, r1, a0, a1, mat, segs=14, z=0.0, taper=True, name="arc"):
    """A flat crescent in the XY plane from angle a0 to a1 (degrees), thickest at a1 (the leading end) when tapered."""
    bm = bmesh.new()
    inner, outer = [], []
    for k in range(segs + 1):
        u = k / segs
        a = math.radians(a0 + (a1 - a0) * u)
        w = (r1 - r0) * (u ** 0.8 if taper else 1.0)
        rr = (r0 + r1) / 2
        inner.append(bm.verts.new((math.cos(a) * (rr - w / 2), math.sin(a) * (rr - w / 2), z)))
        outer.append(bm.verts.new((math.cos(a) * (rr + w / 2), math.sin(a) * (rr + w / 2), z)))
    for k in range(segs):
        bm.faces.new((inner[k], inner[k + 1], outer[k + 1], outer[k]))
    return mesh_ob(name, bm, [mat], col)


def ring(col, r, width, mat, segs=24, name="ring"):
    return arc(col, r - width / 2, r + width / 2, 0, 360, mat, segs, taper=False, name=name)


def band(col, r, h, mat, segs=16, name="band"):
    """An open upright tube, base at z=0."""
    bm = bmesh.new()
    lo = [bm.verts.new((math.cos(2 * math.pi * k / segs) * r, math.sin(2 * math.pi * k / segs) * r, 0)) for k in range(segs)]
    hi = [bm.verts.new((v.co.x, v.co.y, h)) for v in lo]
    for k in range(segs):
        bm.faces.new((lo[k], lo[(k + 1) % segs], hi[(k + 1) % segs], hi[k]))
    return mesh_ob(name, bm, [mat], col)


def box(col, size, mat, name="box", at=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.translate(bm, vec=at, verts=bm.verts)
    return mesh_ob(name, bm, [mat], col)


def beam(col, mat, name="beam"):
    """A 6-sided prism of radius 1 from x=0 to x=1: scaled per frame."""
    bm = bmesh.new()
    a = [bm.verts.new((0, math.cos(k * math.pi / 3), math.sin(k * math.pi / 3))) for k in range(6)]
    b = [bm.verts.new((1, v.co.y, v.co.z)) for v in a]
    for k in range(6):
        bm.faces.new((a[k], a[(k + 1) % 6], b[(k + 1) % 6], b[k]))
    bm.faces.new(a[::-1])
    bm.faces.new(b)
    return mesh_ob(name, bm, [mat], col)


def zigzag(col, mat, length, seed, name="zap"):
    """A jagged lightning stroke along +X from 0 to length, thin and flat-shaded."""
    bm = bmesh.new()
    pts = [V((0, 0, 0))]
    n = 5
    for k in range(1, n):
        j = ((k * 37 + seed * 11) % 7 - 3) / 3
        pts.append(V((length * k / n, 0.06 * j, 0.05 * ((k + seed) % 3 - 1))))
    pts.append(V((length, 0, 0)))
    for p, q in zip(pts, pts[1:]):
        d = (q - p)
        side = d.cross(V((0, 0, 1))).normalized() * 0.022
        up = V((0, 0, 0.022))
        vs = [bm.verts.new(x) for x in (p + side, p + up, p - side, q - side, q + up, q + side)]
        bm.faces.new((vs[0], vs[1], vs[4], vs[5]))
        bm.faces.new((vs[1], vs[2], vs[3], vs[4]))
        bm.faces.new((vs[2], vs[0], vs[5], vs[3]))
    return mesh_ob(name, bm, [mat], col)


def arrow(col, name="arrow"):
    """Along +X, tip at x=0.42, nock at 0."""
    bm = bmesh.new()
    wood, iron, feather = lit("#8A6440"), lit("#6F7A82"), lit("#E8E2D4")
    me_parts = []
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.4, 0.014, 0.014), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0.2, 0, 0), verts=bm.verts)
    for f in bm.faces:
        f.material_index = 0
    head = bmesh.ops.create_cone(bm, segments=4, radius1=0.03, radius2=0.0, depth=0.07, cap_ends=True)
    hv = head["verts"]
    bmesh.ops.rotate(bm, verts=hv, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
    bmesh.ops.translate(bm, vec=(0.42, 0, 0), verts=hv)
    for f in {f for v in hv for f in v.link_faces}:
        f.material_index = 1
    for z in (1, -1):
        vs = [bm.verts.new(p) for p in ((0.0, 0, 0), (0.09, 0, 0), (0.02, 0, z * 0.04))]
        bm.faces.new(vs).material_index = 2
    _ = me_parts
    return mesh_ob(name, bm, [wood, iron, feather], col)


def dagger(col, name="dagger"):
    """Along +X, point at x=0.26."""
    bm = bmesh.new()
    steel, grip = lit("#C9CED2"), lit("#4A3426")
    blade = [bm.verts.new(p) for p in ((0.06, 0.03, 0), (0.26, 0, 0), (0.06, -0.03, 0), (0.06, 0, 0.01), (0.06, 0, -0.01))]
    bm.faces.new((blade[0], blade[3], blade[1]))
    bm.faces.new((blade[3], blade[2], blade[1]))
    bm.faces.new((blade[2], blade[4], blade[1]))
    bm.faces.new((blade[4], blade[0], blade[1]))
    g = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, vec=(0.07, 0.016, 0.016), verts=g)
    bmesh.ops.translate(bm, vec=(0.025, 0, 0), verts=g)
    for f in {f for v in g for f in v.link_faces}:
        f.material_index = 1
    return mesh_ob(name, bm, [steel, grip], col)


def hex_plate(col, mat, name="plate"):
    bm = bmesh.new()
    vs = [bm.verts.new((math.cos(math.radians(30 + 60 * k)) * 0.55, math.sin(math.radians(30 + 60 * k)) * 0.55, 0)) for k in range(6)]
    bm.faces.new(vs)
    return mesh_ob(name, bm, [mat], col)


# --- Actors -----------------------------------------------------------------

class Actor:
    """A whole mini: it can move, lean on a base edge, spin and scale, and nothing else."""

    def __init__(self, ob, home, face):
        self.ob, self.home, self.face = ob, V(home), face
        self.reset()

    def reset(self):
        self.off, self.lean_v, self.edge, self.spin, self.scale = V((0, 0, 0)), V((0, 0)), 0.0, 0.0, 1.0

    def move(self, d):
        self.off += V(d)

    def lean(self, deg, toward, edge=0.42):
        """Tip the top toward a world direction (degrees from +X), rocking on the base's edge on that side (edge 0: on its middle)."""
        a = math.radians(toward)
        self.lean_v += V((math.cos(a), math.sin(a))) * deg
        if abs(deg) > 1e-4:
            self.edge = edge if deg > 0 else -edge

    def apply(self):
        deg = self.lean_v.length
        d = self.lean_v.normalized() if deg > 1e-6 else V((1, 0))
        dd = V((d.x, d.y, 0))
        pv = dd * self.edge * min(1.0, deg / 4)  # rock on the edge once it really leans
        axis = V((0, 0, 1)).cross(dd)
        m = Matrix.Translation(self.home + self.off) @ Matrix.Translation(pv) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-pv)
        m = m @ Matrix.Rotation(math.radians(self.face + self.spin), 4, "Z") @ Matrix.Diagonal((self.scale,) * 3 + (1,))
        self.ob.matrix_world = m
        self.ob.hide_render = self.scale < 1e-3


class Fx:
    """An effect object: placed, scaled and faded per frame; hidden when not shown."""

    def __init__(self, ob):
        self.ob = ob
        self.hide()

    def show(self, at, scale=1.0, rot=None, alpha=1.0):
        s = V(scale) if isinstance(scale, (tuple, list, V)) else V((scale, scale, scale))
        r = rot if rot is not None else Matrix.Identity(4)
        self.ob.matrix_world = Matrix.Translation(V(at)) @ r @ Matrix.Diagonal((*s, 1))
        self.ob.hide_render = min(s) < 1e-4 or alpha <= 0.003
        set_alpha(self.ob, alpha)

    def hide(self):
        self.ob.hide_render = True


def rotz(deg):
    return Matrix.Rotation(math.radians(deg), 4, "Z")


def aim(d):
    """Rotation taking +X to direction d."""
    d = V(d).normalized()
    return d.to_track_quat("X", "Z").to_matrix().to_4x4()


# --- Shared moves -----------------------------------------------------------

def hop(a, s, t0, dur=0.32, h=0.35, reach=0.3, toward=0.0, lean=10.0):
    """Today's attack hop (Godot's combat_board: 0.35 up, 0.3 toward, 0.16 up and 0.16 down)."""
    u = seg(s, t0, t0 + dur)
    if 0 < u < 1:
        b = bump(u)
        d = V((math.cos(math.radians(toward)), math.sin(math.radians(toward)), 0))
        a.move(d * reach * b + V((0, 0, h * b)))
        a.lean(lean * b, toward, edge=0)


def recoil(a, s, t0, toward, tilt=16.0, push=0.12, rec=0.07, settle_t=0.35):
    """Today's recoil: tip away from the blow on the far edge and slide, then settle with a small overshoot."""
    if s < t0:
        return
    u = s - t0
    k = out(u / rec) if u < rec else settle((u - rec) / settle_t)
    d = V((math.cos(math.radians(toward)), math.sin(math.radians(toward)), 0))
    a.move(d * push * k)
    a.lean(tilt * k, toward)


def puff(fx_list, s, t0, at, dur=0.3, spread=0.22, size=0.07, up=0.12):
    """A ring of little flat puffs pushing out and fading."""
    u = seg(s, t0, t0 + dur)
    for k, f in enumerate(fx_list):
        if 0 < u < 1:
            a = 2 * math.pi * k / len(fx_list) + 0.4
            p = V(at) + V((math.cos(a), math.sin(a), 0)) * spread * out(u) + V((0, 0, up * out(u) * (0.5 + 0.5 * (k % 2))))
            f.show(p, size * (1 - 0.6 * u) * (0.8 + 0.4 * (k % 2)), alpha=1 - u ** 2)
        else:
            f.hide()


FRONT = V((0, -0.22, 0))  # effects sit a little toward the camera so the minis don't hide them


def flash(f, s, t0, at, dur=0.18, size=0.3, rot=None):
    """A burst that pops out fast and fades."""
    u = seg(s, t0, t0 + dur)
    if 0 < u < 1:
        f.show(V(at) + FRONT, size * (0.4 + 0.6 * out(u)), rot=rot, alpha=1 - u ** 1.5)
    else:
        f.hide()


def mini_top(a, h=0.62):
    return a.home + a.off + V((0, 0, h))


# --- Stage ------------------------------------------------------------------

class Pane:
    def __init__(self, scene, x0, label, span, centre=None):
        self.x0 = V((x0, 0, 0))
        self.label = label
        self.col = hk.new_collection(f"pane_{label[:1]}_{x0:.0f}")
        self.actors, self.fx, self.update = [], [], None
        board(self.col, self.x0)
        c = self.x0 + (V(centre) if centre is not None else V((span / 2, 0, 0))) + V((0, 0, 0.5))
        dist = 4.0 + span * 1.1
        el = math.radians(38)
        cam = bpy.data.objects.new(f"cam_{label}", bpy.data.cameras.new(f"cam_{label}"))
        cam.data.lens = 50
        cam.location = c + V((0, -dist * math.cos(el), dist * math.sin(el)))
        cam.rotation_euler = (math.pi / 2 - el, 0, 0)
        scene.collection.objects.link(cam)
        self.cam = cam
        txt = bpy.data.curves.new(f"lab_{label}", "FONT")
        txt.body = label
        txt.size = 0.055
        t = bpy.data.objects.new(f"lab_{label}", txt)
        t.data.materials.append(glow("#3A3532", f"labmat_{label}"))
        t.parent = cam
        t.location = (-0.69, 0.42, -2.0)
        t.visible_shadow = False
        scene.collection.objects.link(t)

    def at(self, p):
        return self.x0 + V(p)

    def add(self, ob, home, face):
        a = Actor(ob, self.at(home), face)
        self.actors.append(a)
        return a

    def fxo(self, ob):
        f = Fx(ob)
        self.fx.append(f)
        return f


def board(col, x0):
    g = hk.Piece("ground")
    g.box(V((x0.x + 1.5, 0, 0)), (14, 10, 0.02), "gapgreen", z=-0.03)
    g.finish(col)
    for q in range(-4, 7):
        for r in range(-3, 4):
            p = cell(q, r)
            if abs(p.y) > 2.7 or p.x < -2.6 or p.x > 5.6:
                continue
            c = hk.Piece("cell")
            pts = [V((x0.x + p.x + math.cos(math.radians(30 + 60 * k)) * 0.555, p.y + math.sin(math.radians(30 + 60 * k)) * 0.555)) for k in range(6)]
            c.prism(pts, -0.03, 0.0, f"grass{(q * 2 + r) % 3}")
            c.finish(col)


def hero(t, col, race, build, head, hair, main, off=None, tier="light", skin=1, hairc=1, cloth=1, two=False, caster=False):
    sk = S["skin"][race][skin] if race in S["skin"] else S["skin"]["human"][skin]
    if race == "dragonborn":
        sk = hb.DRAGON_TYPES["red"]
    d = dict(race=race, build=build, head=head, hair=hair, armour=tier, main=main, offhand=off, two=two, caster=caster,
             colours=dict(skin=sk, hair=S["hair"][hairc], eyes=S["eyes"][1], cloth=S["cloth"][cloth]))
    ob, _ = hb.assemble(t, d, f"hero_{race}_{main}", col)
    return ob


def recolour(ob, colours):
    """Turn a beast's colour marks into its swatches, as hb.assemble does for heroes (hero_kit.md → 3. The colours)."""
    swatch = {k: [hk.srgb_to_linear(int(c[i:i + 2], 16) / 255) for i in (1, 3, 5)] for k, c in colours.items()}
    me = ob.data.copy()
    bm = bmesh.new()
    bm.from_mesh(me)
    src = bm.loops.layers.color.get("Col") or bm.loops.layers.float_color.get("Col")
    dst = bm.loops.layers.float_color.new("Col2")
    for f in bm.faces:
        for lo in f.loops:
            c = lo[src]
            z = hb.decode(tuple(round(x * 255) for x in c[:3]))
            lo[dst] = (*([min(1.0, swatch[z[0]][i] * (z[1] ** 2.2)) for i in range(3)] if z else [hk.srgb_to_linear(x) for x in c[:3]]), 1.0)
    bm.to_mesh(me)
    bm.free()
    me.color_attributes.remove(me.color_attributes["Col"])
    me.color_attributes["Col2"].name = "Col"
    me.materials.clear()
    me.materials.append(hk.material("kit"))
    ob.data = me
    return ob


def place(templates, name, col):
    ob = bpy.data.objects.new(name, templates[name].data)
    col.objects.link(ob)
    return ob


# --- The kinds ---------------------------------------------------------------
# Each builder sets up its panes and gives each an update(s) that moves its actors and effects for s seconds after the move starts.

def k_melee(T, E, scene):
    panes = []
    specs = [("A  Hop (today's)", "hop"), ("B  Hop and chop", "chop"), ("C  Bump", "bump")]
    for i, (label, kind) in enumerate(specs):
        p = Pane(scene, i * 40, label, 1.0)
        h = p.add(hero(T, p.col, "human", "average", "a", "short", "longsword", "shield", tier="medium"), (0, 0, 0), 90)
        f = p.add(place(E, "enemy_bandit_melee", p.col), (1, 0, 0), 270)
        slash = p.fxo(arc(p.col, 0.2, 0.36, -70, 60, glow("#FFFFFF"), name="slash"))
        star = p.fxo(spikes(p.col, 7, 0.24, 0.03, glow("#FFF4C8"), up=0.2))

        def up(s, h=h, f=f, kind=kind, slash=slash, star=star, p=p):
            if kind == "hop":
                hop(h, s, 0)
                recoil(f, s, 0.16, 0)
            elif kind == "chop":
                hop(h, s, 0, dur=0.3, h=0.3, reach=0.34)
                u = seg(s, 0.12, 0.2)
                if 0 < u < 1:
                    h.lean(22 * bump(u), 0, edge=0)
                recoil(f, s, 0.17, 0, tilt=18)
                v = seg(s, 0.13, 0.27)
                if 0 < v < 1:
                    slash.show(p.at((0.85, -0.25, 0.62)), 1.5, rot=Matrix.Rotation(math.radians(70), 4, "Y") @ rotz(-90 + 150 * out(v)) @ rotz(0), alpha=1 - v ** 2)
                else:
                    slash.hide()
            else:
                u = seg(s, 0, 0.11)
                b = seg(s, 0.11, 0.33)
                k = out(u) if s < 0.11 else 1 - smooth(b)
                h.move((0.26 * k, 0, 0))
                h.lean(12 * k, 0)
                recoil(f, s, 0.11, 0, tilt=14, push=0.1)
                flash(star, s, 0.1, p.at((0.55, 0, 0.5)), size=1.0)
        p.update = up
        panes.append(p)
    return panes


def k_sweep(T, E, scene):
    panes = []
    specs = [("A  Spin", "spin"), ("B  Swing across", "swing"), ("C  Stomp ring", "stomp")]
    foes = [(1, 0), (0, 1), (-1, 1)]  # the three cells ahead of a hero facing 60°, all on the far side from the camera
    for i, (label, kind) in enumerate(specs):
        p = Pane(scene, i * 40, label, 1.0, centre=(0.0, 0.45, 0))
        h = p.add(hero(T, p.col, "human", "broad", "c", "crest", "glaive", tier="medium", skin=2, cloth=0), (0, 0, 0), 150)
        fs = []
        for (q, r), nm in zip(foes, ("enemy_skeleton", "enemy_bandit_melee", "enemy_zombie")):
            c = cell(q, r)
            fs.append((p.add(place(E, nm, p.col), c, math.degrees(math.atan2(-c.y, -c.x)) + 90), math.degrees(math.atan2(c.y, c.x))))
        trail = p.fxo(arc(p.col, 0.5, 0.78, 150, 0, glow("#FFFFFF"), segs=18, name="trail"))
        wide = p.fxo(arc(p.col, 0.55, 0.85, -80, 80, glow("#FFFFFF"), segs=18, name="wide"))
        shock = p.fxo(ring(p.col, 1.0, 0.16, glow("#FFF2C8")))
        dust = [p.fxo(ico(p.col, 1.0, lit("#D8CBB0"), sub=0, name="dust")) for _ in range(10)]

        def up(s, h=h, fs=fs, kind=kind, trail=trail, wide=wide, shock=shock, dust=dust, p=p):
            if kind == "spin":
                u = seg(s, 0, 0.45)
                h.spin = -360 * smooth(u)
                h.move((0, 0, 0.08 * bump(u)))
                ang = 150 - 360 * smooth(u)  # where the blade is, world degrees (the hero faces 60°; its blade starts on its left)
                if 0 < u < 1:
                    trail.show(p.at((0, 0, 0.45)), 1.0, rot=rotz(ang), alpha=min(1, 4 * u) * (1 - u ** 3))
                else:
                    trail.hide()
                for a, toward in fs:
                    hit = ((150 - toward) % 360) / 360  # the share of the turn when the blade reaches it
                    recoil(a, s, 0.45 * smooth_inv(hit), toward)
            elif kind == "swing":
                w = seg(s, 0, 0.14)
                sw = seg(s, 0.16, 0.34)
                bk = seg(s, 0.36, 0.55)
                yaw = 50 * out(w) if s < 0.16 else 50 - 110 * smooth(sw) if s < 0.36 else -60 * (1 - smooth(bk))
                h.spin = yaw
                h.lean(6 * bump(sw), 60, edge=0)
                if 0 < sw < 1 or (s >= 0.34 and s < 0.46):
                    fade = 1 - seg(s, 0.3, 0.46)
                    wide.show(p.at((0, 0, 0.45)), 1.0, rot=rotz(60), alpha=fade * min(1, 3 * sw))
                else:
                    wide.hide()
                for a, toward in fs:
                    recoil(a, s, 0.16 + 0.18 * (120 - toward) / 120, toward)
            else:
                hop(h, s, 0, dur=0.3, h=0.3, reach=0.0, lean=0)  # the stomp
                u = seg(s, 0.3, 0.6)
                if 0 < u < 1:
                    shock.show(p.at((0, 0, 0.02)), 0.4 + 0.8 * out(u), alpha=1 - u)
                else:
                    shock.hide()
                puff(dust, s, 0.3, p.at((0, 0, 0.02)), dur=0.32, spread=0.5, size=0.06, up=0.08)
                for a, toward in fs:
                    recoil(a, s, 0.38, toward)
        p.update = up
        panes.append(p)
    return panes


def smooth_inv(y):
    """The u at which smooth(u) = y (for when the spin reaches a foe)."""
    lo, hi = 0.0, 1.0
    for _ in range(30):
        mid = (lo + hi) / 2
        if smooth(mid) < y:
            lo = mid
        else:
            hi = mid
    return lo


def k_thrust(T, E, scene):
    panes = []
    specs = [("A  Lunge", "lunge"), ("B  Pivot jab", "jab"), ("C  Hop and jab", "hopjab")]
    for i, (label, kind) in enumerate(specs):
        p = Pane(scene, i * 40, label, 2.0)
        h = p.add(hero(T, p.col, "elf", "slim", "b", "tail", "spear", tier="light", skin=0, hairc=3, cloth=2), (0, 0, 0), 90)
        f = p.add(place(E, "enemy_bandit_melee", p.col), (2, 0, 0), 270)
        streak = p.fxo(beam(p.col, glow("#FFFFFF"), name="streak"))
        star = p.fxo(spikes(p.col, 7, 0.26, 0.035, glow("#FFF4C8"), up=0.1))

        def up(s, h=h, f=f, kind=kind, streak=streak, star=star, p=p):
            if kind == "lunge":
                k = out(seg(s, 0, 0.09)) if s < 0.14 else 1 - smooth(seg(s, 0.14, 0.36))
                h.move((0.34 * k, 0, 0))
                h.lean(15 * k, 0)
                hit = 0.09
            elif kind == "jab":
                k = out(seg(s, 0, 0.08)) if s < 0.13 else 1 - smooth(seg(s, 0.13, 0.33))
                h.lean(26 * k, 0)
                hit = 0.08
            else:
                hop(h, s, 0, dur=0.26, h=0.2, reach=0.2, lean=0)
                k = out(seg(s, 0.1, 0.16)) if s < 0.2 else 1 - smooth(seg(s, 0.2, 0.34))
                h.lean(20 * k, 0, edge=0)
                hit = 0.15
            v = seg(s, hit - 0.04, hit + 0.12)
            if 0 < v < 1:
                x0 = 0.55 + 0.9 * out(v) - 0.3
                streak.show(p.at((x0 - 0.5 * (1 - v), -0.12, 0.6)), (0.5 + 0.5 * (1 - v), 0.028, 0.028), alpha=1 - v)
            else:
                streak.hide()
            recoil(f, s, hit, 0, tilt=15)
            flash(star, s, hit, p.at((1.7, 0, 0.55)), size=1.0)
        p.update = up
        panes.append(p)
    return panes


def k_heavy(T, E, scene):
    panes = []
    specs = [("A  Big hop slam", "slam"), ("B  Wind-up lurch", "lurch")]
    for i, (label, kind) in enumerate(specs):
        p = Pane(scene, i * 40, label, 1.0)
        h = p.add(hero(T, p.col, "dwarf", "broad", "a", "short", "greataxe", tier="heavy", skin=2, hairc=5, cloth=0), (0, 0, 0), 90)
        f = p.add(place(E, "enemy_bandit_elite", p.col), (1, 0, 0), 270)
        shock = p.fxo(ring(p.col, 1.0, 0.1, glow("#F4E6C0")))
        star = p.fxo(spikes(p.col, 9, 0.28, 0.035, glow("#FFE9A8"), up=0.25))
        dust = [p.fxo(ico(p.col, 1.0, lit("#D8CBB0"), sub=0, name="dust")) for _ in range(8)]

        def up(s, h=h, f=f, kind=kind, shock=shock, star=star, dust=dust, p=p):
            if kind == "slam":
                rise = seg(s, 0, 0.26)
                fall = seg(s, 0.3, 0.38)
                back = seg(s, 0.42, 0.58)
                z = 0.6 * out(rise) if s < 0.3 else 0.6 * (1 - inn(fall)) if s < 0.38 else 0.0
                x = 0.32 * rise if s < 0.38 else 0.32 * (1 - smooth(back))
                h.move((x, 0, z))
                h.lean(-10 * out(rise) if s < 0.3 else -10 + 32 * fall if s < 0.38 else 22 * (1 - smooth(back)), 0, edge=0 if s < 0.38 else 0.42)
                hit = 0.38
                recoil(f, s, hit, 0, tilt=26, push=0.2, settle_t=0.45)
                u = seg(s, hit, hit + 0.3)
                if 0 < u < 1:
                    shock.show(p.at((0.6, 0, 0.02)), 0.25 + 0.6 * out(u), alpha=1 - u)
                else:
                    shock.hide()
                puff(dust, s, hit, p.at((0.6, 0, 0.02)), dur=0.35, spread=0.35, size=0.06)
                flash(star, s, hit, p.at((0.75, 0, 0.55)), size=1.0, dur=0.2)
            else:
                wind = seg(s, 0, 0.2)
                go = seg(s, 0.27, 0.35)
                back = seg(s, 0.4, 0.58)
                lean = -14 * smooth(wind) if s < 0.27 else -14 + 40 * out(go) if s < 0.4 else 26 * (1 - smooth(back))
                h.lean(lean, 0)
                h.move((0.3 * out(go) * (1 - smooth(back)), 0, 0))
                hit = 0.34
                recoil(f, s, hit, 0, tilt=26, push=0.2, settle_t=0.45)
                flash(star, s, hit, p.at((0.7, 0, 0.6)), size=1.15, dur=0.22)
                puff(dust, s, hit, p.at((1.0, 0, 0.02)), dur=0.3, spread=0.3, size=0.05)
        p.update = up
        panes.append(p)
    return panes


def k_shot(T, E, scene):
    panes = []
    specs = [("A  Straight shot", "flat"), ("B  Lobbed shot", "lob")]
    for i, (label, kind) in enumerate(specs):
        p = Pane(scene, i * 40, label, 3.0)
        h = p.add(hero(T, p.col, "halfling", "average", "a", "topknot", "longbow", tier="light", skin=0, hairc=2, cloth=2), (0, 0, 0), 90)
        f = p.add(place(E, "enemy_wolf", p.col), (3, 0, 0), 270)
        arw = p.fxo(arrow(p.col))  # scaled up a little so it reads at fight distance
        tr = p.fxo(beam(p.col, glow("#FFFFFF"), name="trail"))
        dust = [p.fxo(ico(p.col, 1.0, lit("#E8E0CC"), sub=0, name="dust")) for _ in range(5)]

        def up(s, h=h, f=f, kind=kind, arw=arw, tr=tr, dust=dust, p=p):
            rel = 0.08
            h.lean(-7 * bump(seg(s, rel, rel + 0.2)), 0)
            if kind == "flat":
                fly = 0.18
                u = seg(s, rel, rel + fly)
                a, b = p.at((0.3, 0, 0.55)), p.at((2.75, 0, 0.42))
                if 0 < u < 1:
                    pos = a.lerp(b, u)
                    arw.show(pos - V((0.6, 0, 0)), 1.5, rot=aim(b - a))
                    tr.show(pos - V((0.4 + 0.5 * min(1, u * 3), 0, 0)), (0.5 * min(1, u * 3), 0.016, 0.016), alpha=0.8)
                else:
                    arw.hide()
                    tr.hide()
                hit = rel + fly
            else:
                fly = 0.36
                u = seg(s, rel, rel + fly)
                a, b = p.at((0.3, 0, 0.6)), p.at((2.75, 0, 0.42))
                if 0 < u < 1:
                    pos = a.lerp(b, u) + V((0, 0, 0.75 * bump(u)))
                    vel = (b - a) + V((0, 0, 0.75 * math.pi * math.cos(math.pi * u)))
                    arw.show(pos - aim(vel).to_3x3() @ V((0.6, 0, 0)), 1.5, rot=aim(vel))
                else:
                    arw.hide()
                tr.hide()
                hit = rel + fly
            recoil(f, s, hit, 0, tilt=14)
            puff(dust, s, hit, p.at((2.75, 0, 0.42)), dur=0.25, spread=0.12, size=0.035, up=0.05)
        p.update = up
        panes.append(p)
    return panes


def k_thrown(T, E, scene):
    panes = []
    specs = [("A  Snap throw, spinning", "spin"), ("B  Hop throw, point first", "point")]
    for i, (label, kind) in enumerate(specs):
        p = Pane(scene, i * 40, label, 3.0)
        h = p.add(hero(T, p.col, "tiefling", "slim", "b", "long", "dagger", tier="light", skin=2, hairc=0, cloth=3), (0, 0, 0), 90)
        f = p.add(place(E, "enemy_bandit_ranged", p.col), (3, 0, 0), 270)
        dg = p.fxo(dagger(p.col))
        tr = p.fxo(beam(p.col, glow("#FFFFFF"), name="trail"))
        star = p.fxo(spikes(p.col, 7, 0.24, 0.03, glow("#FFF4C8"), up=0.1))

        def up(s, h=h, f=f, kind=kind, dg=dg, tr=tr, star=star, p=p):
            if kind == "spin":
                k = out(seg(s, 0, 0.08)) if s < 0.1 else 1 - smooth(seg(s, 0.1, 0.3))
                h.lean(12 * k, 0)
                rel, fly = 0.08, 0.26
                a, b = p.at((0.35, 0, 0.62)), p.at((2.78, 0, 0.5))
                u = seg(s, rel, rel + fly)
                if 0 < u < 1:
                    pos = a.lerp(b, u) + V((0, 0, 0.18 * bump(u)))
                    dg.show(pos, 1.6, rot=Matrix.Rotation(-math.radians(900 * u), 4, "Y") @ Matrix.Translation((-0.13, 0, 0)))
                else:
                    dg.hide()
                tr.hide()
            else:
                hop(h, s, 0, dur=0.28, h=0.22, reach=0.1, lean=6)
                rel, fly = 0.14, 0.17
                a, b = p.at((0.35, 0, 0.8)), p.at((2.78, 0, 0.5))
                u = seg(s, rel, rel + fly)
                if 0 < u < 1:
                    pos = a.lerp(b, u)
                    dg.show(pos - (b - a).normalized() * 0.4, 1.6, rot=aim(b - a))
                    tr.show(pos - (b - a).normalized() * (0.26 + 0.45 * min(1, u * 3)), (0.45 * min(1, u * 3), 0.016, 0.016), rot=aim(b - a), alpha=0.8)
                else:
                    dg.hide()
                    tr.hide()
            hit = rel + fly
            recoil(f, s, hit, 0, tilt=14)
            flash(star, s, hit, p.at((2.75, 0, 0.5)), size=1.0)
        p.update = up
        panes.append(p)
    return panes


def charge(a, s, ringfx, p, t0=0.0, dur=0.15, colour_alpha=1.0, rise=0.1):
    """A caster's wind-up: the mini lifts a little and a ring of light tightens round its base."""
    u = seg(s, t0, t0 + dur)
    k = out(u) if s < t0 + dur + 0.1 else 1 - smooth(seg(s, t0 + dur + 0.1, t0 + dur + 0.35))
    a.move((0, 0, rise * k))
    if 0 < u < 1 or (s < t0 + dur + 0.12 and s >= t0):
        ringfx.show(a.home + V((0, 0, 0.02)), 0.75 - 0.25 * u, alpha=colour_alpha * min(1, 3 * u) * (1 - seg(s, t0 + dur, t0 + dur + 0.12)))
    else:
        ringfx.hide()


def k_bolt(T, E, scene):
    panes = []
    specs = [("A  Orb with a trail (Firebolt)", "orb", "#FF8A2A", "#FFD24A"), ("B  Ray (Frost Ray)", "ray", "#8FD8FF", "#E6F7FF"),
             ("C  Darts (Magic Bolt)", "darts", "#B07CFF", "#EBDDFF")]
    for i, (label, kind, c1, c2) in enumerate(specs):
        p = Pane(scene, i * 40, label, 3.0)
        h = p.add(hero(T, p.col, "elf", "average", "c", "long", "staff", tier="none", skin=1, hairc=3, cloth=3, caster=True), (0, 0, 0), 90)
        f = p.add(place(E, "enemy_skeleton", p.col), (3, 0, 0), 270)
        rg = p.fxo(ring(p.col, 1.0, 0.07, glow(c1)))
        core = p.fxo(ico(p.col, 0.13, glow(c2)))
        tails = [p.fxo(ico(p.col, 0.1, glow(c1))) for _ in range(5)]
        bm_ = p.fxo(beam(p.col, glow(c2), name="ray"))
        bm2 = p.fxo(beam(p.col, glow(c1), name="rayglow"))
        burst = p.fxo(spikes(p.col, 9, 0.34, 0.05, glow(c2), up=0.3))
        burst2 = p.fxo(spikes(p.col, 7, 0.44, 0.045, glow(c1), up=0.2, seed=3))
        darts = [p.fxo(ico(p.col, 0.1, glow(c2))) for _ in range(3)]

        def up(s, h=h, f=f, kind=kind, rg=rg, core=core, tails=tails, bm_=bm_, bm2=bm2, burst=burst, burst2=burst2, darts=darts, p=p):
            charge(h, s, rg, p, dur=0.14)
            a, b = p.at((0.32, 0, 0.75)), p.at((2.75, 0, 0.5))
            if kind == "orb":
                rel, fly = 0.14, 0.22
                u = seg(s, rel, rel + fly)
                if 0 < u < 1:
                    core.show(a.lerp(b, u), 1.0)
                    for k, tl in enumerate(tails):
                        uu = u - 0.05 * (k + 1)
                        tl.show(a.lerp(b, max(uu, 0)), 0.9 - 0.15 * k, alpha=0.9 if uu > 0 else 0)
                else:
                    core.hide()
                    for tl in tails:
                        tl.hide()
                hit = rel + fly
                recoil(f, s, hit, 0)
                flash(burst, s, hit, b, size=1.0, dur=0.2)
                flash(burst2, s, hit + 0.02, b, size=1.0, dur=0.25)
            elif kind == "ray":
                rel = 0.14
                u = seg(s, rel, rel + 0.05)
                hold = seg(s, rel + 0.05, rel + 0.26)
                if s >= rel and s < rel + 0.32:
                    w = 0.03 * (1 + 0.25 * math.sin(s * 90)) * (1 - seg(s, rel + 0.22, rel + 0.32))
                    L = (b - a).length * out(u)
                    bm_.show(a, (L, w, w), rot=aim(b - a))
                    bm2.show(a, (L, w * 2.2, w * 2.2), rot=aim(b - a), alpha=0.45)
                else:
                    bm_.hide()
                    bm2.hide()
                _ = hold
                hit = rel + 0.05
                recoil(f, s, hit, 0)
                flash(burst, s, hit, b, size=0.9, dur=0.3)
                burst2.hide()
            else:
                rel = 0.14
                hits = []
                for k, d in enumerate(darts):
                    st, fly = rel + 0.06 * k, 0.22
                    u = seg(s, st, st + fly)
                    side = (k - 1) * 0.55
                    if 0 < u < 1:
                        pos = a.lerp(b, u) + V((0, side * bump(u), 0.15 * bump(u) * (1 - abs(k - 1))))
                        d.show(pos, 1.0)
                    else:
                        d.hide()
                    hits.append(st + fly)
                for k, hit in enumerate(hits):
                    if s >= hit:
                        last = hit
                recoil(f, s, hits[0], 0, tilt=8)
                recoil(f, s, hits[1], 0, tilt=8)
                recoil(f, s, hits[2], 0, tilt=10)
                flash(burst, s, hits[0], b, size=0.6, dur=0.15)
                flash(burst2, s, hits[2], b, size=0.6, dur=0.18)
        p.update = up
        panes.append(p)
    return panes


def k_touch(T, E, scene):
    panes = []
    specs = [("A  Zap lunge", "lunge"), ("B  Charge, then tap", "charge")]
    for i, (label, kind) in enumerate(specs):
        p = Pane(scene, i * 40, label, 1.0)
        h = p.add(hero(T, p.col, "human", "slim", "b", "spiky", "wand", tier="none", skin=3, hairc=4, cloth=1), (0, 0, 0), 90)
        f = p.add(place(E, "enemy_zombie", p.col), (1, 0, 0), 270)
        zaps = [p.fxo(zigzag(p.col, glow("#BFEFFF"), 0.4, k)) for k in range(5)]
        orbit = [p.fxo(zigzag(p.col, glow("#9FE3FF"), 0.16, k + 5)) for k in range(4)]
        core = p.fxo(ico(p.col, 0.06, glow("#FFFFFF")))

        def up(s, h=h, f=f, kind=kind, zaps=zaps, orbit=orbit, core=core, p=p):
            if kind == "lunge":
                k = out(seg(s, 0, 0.1)) if s < 0.18 else 1 - smooth(seg(s, 0.18, 0.4))
                h.move((0.26 * k, 0, 0))
                h.lean(10 * k, 0)
                hit = 0.1
                for o in orbit:
                    o.hide()
            else:
                cu = seg(s, 0, 0.22)
                for j, o in enumerate(orbit):
                    if 0 < cu < 1 or (s < 0.3):
                        a = 360 * cu * 2 + j * 90
                        o.show(h.home + h.off + V((0, 0, 0.3 + 0.12 * j)) + V((math.cos(math.radians(a)), math.sin(math.radians(a)), 0)) * 0.26, 1.0, rot=rotz(a + 90 + 40 * ((s * 60) % 2)), alpha=0.9 * (1 - seg(s, 0.24, 0.3)))
                    else:
                        o.hide()
                hop(h, s, 0.22, dur=0.24, h=0.16, reach=0.3, lean=12)
                hit = 0.34
            v = seg(s, hit, hit + 0.2)
            c = p.at((0.62, 0, 0.5))
            for j, z in enumerate(zaps):
                if 0 < v < 1:
                    a = j * 72 + 25 * math.sin(s * 70 + j)
                    z.show(c, (0.6 + 0.6 * out(v)) * (1 if (int(s * 60) + j) % 3 else 0.6), rot=rotz(a) @ Matrix.Rotation(math.radians(20 * (j % 3 - 1)), 4, "Y"), alpha=1 - v)
                else:
                    z.hide()
            flash(core, s, hit, c, size=1.6, dur=0.12)
            if s >= hit:
                recoil(f, s, hit, 0, tilt=12)
                u = s - hit
                if u < 0.25:  # a buzz: the hit mini shivers side to side
                    f.move((0, 0.025 * math.sin(u * 140) * (1 - u / 0.25), 0))
        p.update = up
        panes.append(p)
    return panes


def k_area(T, E, scene):
    panes = []
    specs = [("A  Burst: lob, then a dome", "dome"), ("B  Burst: flames from the cells", "erupt"), ("C  Cone: rolling puffs", "puffs"), ("D  Cone: a sweeping wedge", "wedge")]
    for i, (label, kind) in enumerate(specs):
        cone = kind in ("puffs", "wedge")
        p = Pane(scene, i * 40, label, 3.0, centre=(1.8, 0, 0))
        if cone:
            h = p.add(hero(T, p.col, "dragonborn", "broad", "a", None, "greatsword", tier="medium", cloth=4), (0, 0, 0), 90)
            cells = [(1, 0), (2, 0), (2, -1), (1, 1), (3, 0), (3, -1), (2, 1), (3, -2), (1, 2)]
            cells = [c for c in cells if abs(math.degrees(math.atan2(cell(*c).y, cell(*c).x))) <= 31]
        else:
            h = p.add(hero(T, p.col, "human", "average", "d", "short", "staff", tier="none", skin=1, hairc=5, cloth=0, caster=True), (0, 0, 0), 90)
            cells = [(3, 0), (2, 0), (4, 0), (3, -1), (2, 1), (3, 1), (4, -1)]
        foes = [(2, 0), (3, -1)] if not cone else [(1, 0), (3, 0), (2, -1)]
        fa = []
        for (q, r), nm in zip(foes, ("enemy_bandit_melee", "enemy_wolf", "enemy_skeleton")):
            c = cell(q, r)
            fa.append((p.add(place(E, nm, p.col), c, 270), cell(q, r)))
        plates = [(p.fxo(hex_plate(p.col, glow("#FF9A3C"))), cell(*c)) for c in cells]
        centre = cell(3, 0)
        dome = p.fxo(ico(p.col, 1.0, glow("#FFB347"), sub=1, name="dome"))
        lob = p.fxo(ico(p.col, 0.12, glow("#FFD24A")))
        rg = p.fxo(ring(p.col, 1.0, 0.07, glow("#FF8A2A")))
        flames = [p.fxo(spikes(p.col, 5, 0.55, 0.11, glow("#FF7A2A" if k % 2 else "#FFC24A"), up=4.0, seed=k)) for k in range(len(cells))]
        puffs = [p.fxo(ico(p.col, 1.0, glow("#FF9A3C" if k % 3 else "#FFD27A"), sub=1, name="puff")) for k in range(14)]
        wedge = p.fxo(arc(p.col, 0.35, 3.4, -30, 30, glow("#FF9A3C"), segs=10, taper=False, name="wedge"))

        def up(s, h=h, fa=fa, kind=kind, plates=plates, dome=dome, lob=lob, rg=rg, flames=flames, puffs=puffs, wedge=wedge, p=p, centre=centre):
            if kind == "dome":
                charge(h, s, rg, p, dur=0.12)
                rel, fly = 0.12, 0.2
                u = seg(s, rel, rel + fly)
                a, b = p.at((0.3, 0, 0.75)), p.at(centre) + V((0, 0, 0.1))
                if 0 < u < 1:
                    lob.show(a.lerp(b, u) + V((0, 0, 0.6 * bump(u))), 1.0)
                else:
                    lob.hide()
                hit = rel + fly
                v = seg(s, hit, hit + 0.35)
                if 0 < v < 1:
                    dome.show(p.at(centre), (1.5 * out(v), 1.5 * out(v), 0.9 * out(v)), alpha=0.75 * (1 - v ** 2))
                else:
                    dome.hide()
                for pl, c in plates:
                    w = seg(s, hit, hit + 0.45)
                    pl.show(p.at(c) + V((0, 0, 0.012)), 1.0, alpha=0.85 * bump(w) if 0 < w < 1 else 0)
                for a_, c in fa:
                    d = c - centre
                    recoil(a_, s, hit + 0.03, math.degrees(math.atan2(d.y, d.x)) if d.length > 0.1 else 0)
            elif kind == "erupt":
                charge(h, s, rg, p, dur=0.14)
                warn = seg(s, 0.05, 0.2)
                hit = 0.22
                for (pl, c), fl in zip(plates, flames):
                    pl.show(p.at(c) + V((0, 0, 0.012)), 1.0, alpha=(0.7 * warn if s < hit else 0.85 * (1 - seg(s, hit + 0.15, hit + 0.45))) if s > 0.05 else 0)
                    u = seg(s, hit, hit + 0.32)
                    if 0 < u < 1:
                        fl.show(p.at(c), (0.9, 0.9, 1.6 * bump(u)), alpha=1 - u ** 3)
                    else:
                        fl.hide()
                for a_, c in fa:
                    recoil(a_, s, hit + 0.02, 90 if c.y >= 0 else -90, tilt=12, push=0.06)
                    if s > hit:
                        a_.move((0, 0, 0.12 * bump(seg(s, hit, hit + 0.22))))
            elif kind == "puffs":
                k = out(seg(s, 0, 0.1)) if s < 0.45 else 1 - smooth(seg(s, 0.45, 0.6))
                h.lean(8 * k, 0)
                h.move((0, 0, 0.06 * k))
                for j, pf in enumerate(puffs):
                    st = 0.06 + 0.025 * j
                    u = seg(s, st, st + 0.32)
                    if 0 < u < 1:
                        ang = math.radians(((j * 37) % 11 - 5) * 5.5)
                        dist = 0.45 + 2.6 * out(u)
                        pf.show(p.at((math.cos(ang) * dist, math.sin(ang) * dist, 0.55 - 0.25 * u)), 0.08 + 0.22 * u, alpha=0.9 * (1 - u ** 2))
                    else:
                        pf.hide()
                for a_, c in fa:
                    recoil(a_, s, 0.06 + 0.32 * (c.length - 0.45) / 2.6 * 0.7, 0, tilt=14)
            else:
                k = out(seg(s, 0, 0.1)) if s < 0.4 else 1 - smooth(seg(s, 0.4, 0.56))
                h.lean(10 * k, 0)
                u = seg(s, 0.08, 0.38)
                if 0 < u < 1:
                    wedge.show(p.at((0, 0, 0.12)), (out(u), out(u), 1), alpha=0.8 * (1 - u ** 3))
                else:
                    wedge.hide()
                for pl, c in plates:
                    reach = (c.length - 0.35) / 3.05
                    w = seg(s, 0.08 + 0.3 * reach, 0.5 + 0.2 * reach)
                    pl.show(p.at(c) + V((0, 0, 0.012)), 1.0, alpha=0.8 * bump(w) if 0 < w < 1 else 0)
                for a_, c in fa:
                    recoil(a_, s, 0.08 + 0.3 * (c.length - 0.35) / 3.05, 0, tilt=14)
        p.update = up
        panes.append(p)
    return panes


def k_buff(T, E, scene):
    panes = []
    specs = [("A  Rising ring", "ring"), ("B  Falling motes", "motes"), ("C  Pulse to the ally", "pulse")]
    for i, (label, kind) in enumerate(specs):
        p = Pane(scene, i * 40, label, 1.0)
        h = p.add(hero(T, p.col, "human", "broad", "b", "long", "mace", "shield", tier="heavy", skin=0, hairc=3, cloth=4), (0, 0, 0), 90)
        ally = p.add(hero(T, p.col, "dwarf", "average", "b", "short", "battleaxe", "shield", tier="medium", skin=2, hairc=2, cloth=1), (1, 0, 0), 90)
        gold, pale = "#FFD45A", "#FFF3B8"
        rgc = p.fxo(ring(p.col, 1.0, 0.06, glow(gold)))
        bnd = p.fxo(band(p.col, 0.38, 0.13, glow(gold)))
        motes = [p.fxo(ico(p.col, 0.055, glow(pale if k % 2 else gold), sub=0, name="mote")) for k in range(12)]
        base = p.fxo(ring(p.col, 1.0, 0.1, glow(gold)))
        wave = p.fxo(ring(p.col, 1.0, 0.09, glow(pale)))

        def up(s, h=h, ally=ally, kind=kind, rgc=rgc, bnd=bnd, motes=motes, base=base, wave=wave, p=p):
            h.move((0, 0, 0.08 * bump(seg(s, 0, 0.24))))
            c = ally.home
            if kind == "ring":
                u = seg(s, 0.12, 0.5)
                if 0 < u < 1:
                    bnd.show(c + V((0, 0, 0.02 + 0.85 * smooth(u))), (1 - 0.3 * u, 1 - 0.3 * u, 1), alpha=1 - u ** 3)
                else:
                    bnd.hide()
                ally.move((0, 0, 0.1 * bump(seg(s, 0.3, 0.55))))
                for j, m in enumerate(motes):
                    v = seg(s, 0.2 + 0.02 * j, 0.55 + 0.02 * j)
                    if 0 < v < 1:
                        a = j * 30
                        m.show(c + V((math.cos(math.radians(a)) * 0.3, math.sin(math.radians(a)) * 0.3, 0.2 + 0.8 * v)), 1.0, alpha=1 - v)
                    else:
                        m.hide()
                rgc.hide()
            elif kind == "motes":
                for j, m in enumerate(motes):
                    v = seg(s, 0.08 + 0.025 * j, 0.42 + 0.025 * j)
                    if 0 < v < 1:
                        a = j * 47
                        r = 0.1 + 0.22 * ((j * 5) % 4) / 3
                        m.show(c + V((math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r, 1.3 - 1.1 * v)), 1.2, alpha=min(1, 4 * v) * (1 - v ** 4))
                    else:
                        m.hide()
                w = seg(s, 0.35, 0.65)
                if 0 < w < 1:
                    base.show(c + V((0, 0, 0.02)), 0.3 + 0.35 * out(w), alpha=1 - w)
                else:
                    base.hide()
                ally.move((0, 0, 0.08 * bump(seg(s, 0.4, 0.62))))
                bnd.hide()
            else:
                u = seg(s, 0.08, 0.36)
                if 0 < u < 1:
                    wave.show(h.home + V((0, 0, 0.02)), 0.3 + 1.0 * out(u), alpha=1 - u)
                else:
                    wave.hide()
                w = seg(s, 0.3, 0.6)
                if 0 < w < 1:
                    base.show(c + V((0, 0, 0.02)), 0.48 - 0.12 * w, alpha=bump(w))
                    bnd.show(c + V((0, 0, 0.02)), (1.0, 1.0, 1.0 + 6 * out(w)), alpha=0.6 * (1 - w))
                else:
                    base.hide()
                    bnd.hide()
                ally.move((0, 0, 0.1 * bump(seg(s, 0.3, 0.55))))
                ally.scale = 1.0 + 0.0
        p.update = up
        panes.append(p)
    return panes


def k_summon(T, E, scene):
    panes = []
    specs = [("A  Rises from the ground", "rise"), ("B  Drops in", "drop"), ("C  Pops in", "pop")]
    BT = rp.load_templates(os.path.join(hk.ART, "minis", "heroes", "beasts_v1.blend"))
    for i, (label, kind) in enumerate(specs):
        p = Pane(scene, i * 40, label, 1.0)
        h = p.add(hero(T, p.col, "tiefling", "average", "c", "topknot", "staff", tier="none", skin=0, hairc=0, cloth=5, caster=True), (0, 0, 0), 90)
        w = p.add(recolour(place(BT, "beast_wolf", p.col), dict(skin="#8E8A84", hair="#E4DDD0", eyes="#C9A24A", cloth=S["cloth"][5])), (1, 0, 0), 90)
        rg = p.fxo(ring(p.col, 1.0, 0.06, glow("#B07CFF")))
        plate = p.fxo(hex_plate(p.col, glow("#C9A6FF")))
        sparks = p.fxo(spikes(p.col, 10, 0.4, 0.03, glow("#EBDDFF"), up=0.6))
        dust = [p.fxo(ico(p.col, 1.0, lit("#D8CBB0"), sub=0, name="dust")) for _ in range(10)]

        def up(s, h=h, w=w, kind=kind, rg=rg, plate=plate, sparks=sparks, dust=dust, p=p):
            charge(h, s, rg, p, dur=0.14)
            c = w.home
            if kind == "rise":
                pu = seg(s, 0.05, 0.6)
                plate.show(c + V((0, 0, 0.012)), 1.0, alpha=0.85 * bump(pu) if 0 < pu < 1 else 0)
                u = seg(s, 0.15, 0.5)
                w.move((0, 0, -0.95 * (1 - out(u))))
                w.spin = -180 * (1 - out(u))
                w.scale = 1.0 if s > 0.15 else 0.0
                puff(dust, s, 0.15, c + V((0, 0, 0.02)), dur=0.4, spread=0.45, size=0.05, up=0.06)
                sparks.hide()
            elif kind == "drop":
                u = seg(s, 0.12, 0.34)
                if s < 0.12:
                    w.scale = 0.0
                elif s < 0.34:
                    w.move((0, 0, 1.4 * (1 - inn(u))))
                else:
                    w.move((0, 0, 0.12 * bump(seg(s, 0.34, 0.46))))
                puff(dust, s, 0.34, c + V((0, 0, 0.02)), dur=0.35, spread=0.45, size=0.06, up=0.08)
                plate.show(c + V((0, 0, 0.012)), 1.0, alpha=0.8 * bump(seg(s, 0.05, 0.45)) if 0.05 < s < 0.45 else 0)
                sparks.hide()
            else:
                u = seg(s, 0.15, 0.4)
                w.scale = 0.0 if s < 0.15 else (1.18 * out(seg(s, 0.15, 0.3)) if s < 0.3 else 1.18 - 0.18 * smooth(seg(s, 0.3, 0.42)))
                flash(sparks, s, 0.15, c + V((0, 0, 0.35)), size=1.0, dur=0.3)
                plate.show(c + V((0, 0, 0.012)), 1.0, alpha=0.8 * bump(seg(s, 0.05, 0.45)) if 0.05 < s < 0.45 else 0)
                for d in dust:
                    d.hide()
                _ = u
        p.update = up
        panes.append(p)
    return panes


def k_hit(T, E, scene):
    panes = []
    specs = [("A  Tip back (today's)", "tip"), ("B  Knocked back a step", "knock"), ("C  Shake with a flash", "shake")]
    for i, (label, kind) in enumerate(specs):
        p = Pane(scene, i * 40, label, 1.0)
        h = p.add(hero(T, p.col, "human", "average", "a", "short", "longsword", "shield", tier="medium"), (0, 0, 0), 90)
        f = p.add(place(E, "enemy_bandit_melee", p.col), (1, 0, 0), 270)
        star = p.fxo(spikes(p.col, 8, 0.2, 0.03, glow("#FFFFFF"), up=0.25))

        def up(s, h=h, f=f, kind=kind, star=star, p=p):
            hop(h, s, 0)
            hit = 0.16
            if kind == "tip":
                recoil(f, s, hit, 0)
                star.hide()
            elif kind == "knock":
                if s >= hit:
                    u = seg(s, hit, hit + 0.18)
                    back = 1 - smooth(seg(s, hit + 0.3, hit + 0.55))
                    f.move((0.3 * out(u) * back, 0, 0.12 * bump(u)))
                    f.lean(-8 * bump(u), 0, edge=0)
                star.hide()
            else:
                if s >= hit:
                    u = s - hit
                    if u < 0.3:
                        f.lean(9 * math.sin(u * 55) * (1 - u / 0.3), 90, edge=0)
                flash(star, s, hit, p.at((0.75, 0, 0.6)), size=1.0, dur=0.16)
        p.update = up
        panes.append(p)
    return panes


def k_miss(T, E, scene):
    panes = []
    specs = [("A  Sidestep", "side"), ("B  Lean away", "lean"), ("C  Hop back", "hopback")]
    for i, (label, kind) in enumerate(specs):
        p = Pane(scene, i * 40, label, 1.0)
        h = p.add(hero(T, p.col, "human", "average", "a", "short", "longsword", "shield", tier="medium"), (0, 0, 0), 90)
        f = p.add(place(E, "enemy_bandit_melee", p.col), (1, 0, 0), 270)
        whiff = p.fxo(arc(p.col, 0.16, 0.22, -60, 60, glow("#FFFFFF"), name="whiff"))
        dust = [p.fxo(ico(p.col, 1.0, lit("#E8E0CC"), sub=0, name="dust")) for _ in range(5)]

        def up(s, h=h, f=f, kind=kind, whiff=whiff, dust=dust, p=p):
            hop(h, s, 0)
            t0 = 0.08
            if kind == "side":
                k = out(seg(s, t0, t0 + 0.1)) if s < 0.32 else 1 - smooth(seg(s, 0.32, 0.55))
                f.move((0.04 * k, -0.3 * k, 0))
                f.lean(6 * k, -90, edge=0)
            elif kind == "lean":
                k = out(seg(s, t0, t0 + 0.08)) if s < 0.3 else 1 - smooth(seg(s, 0.3, 0.52))
                f.lean(22 * k, 0)
            else:
                u = seg(s, t0, t0 + 0.2)
                back = 1 - smooth(seg(s, 0.36, 0.6))
                f.move((0.22 * out(u) * back, 0, 0.12 * bump(u)))
            v = seg(s, 0.14, 0.3)
            if 0 < v < 1:
                whiff.show(p.at((0.95, 0, 0.6)), 1.4, rot=Matrix.Rotation(math.radians(70), 4, "Y") @ rotz(-90 + 150 * out(v)), alpha=0.7 * (1 - v))
            else:
                whiff.hide()
            puff(dust, s, 0.3 if kind == "hopback" else 0.2, f.home + V((0.0, -0.3 if kind == "side" else 0, 0.02)), dur=0.25, spread=0.18, size=0.03, up=0.04)
        p.update = up
        panes.append(p)
    return panes


def k_cone(T, E, scene):
    """Cone v2 (Ethan, Nov 7): C's rolling puffs with D's hexes lighting as they're hit. A lights the hexes first and the puffs roll over
    them; B lights each hex as the puffs reach it."""
    panes = []
    specs = [("A  Hexes light, then puffs roll over", "first"), ("B  Hexes light as the puffs reach them", "together")]
    for i, (label, kind) in enumerate(specs):
        p = Pane(scene, i * 40, label, 3.0, centre=(1.8, 0, 0))
        h = p.add(hero(T, p.col, "dragonborn", "broad", "a", None, "greatsword", tier="medium", cloth=4), (0, 0, 0), 90)
        cells = [c for c in [(1, 0), (2, 0), (2, -1), (1, 1), (3, 0), (3, -1), (2, 1)] if abs(math.degrees(math.atan2(cell(*c).y, cell(*c).x))) <= 31]
        fa = [(p.add(place(E, nm, p.col), cell(q, r), 270), cell(q, r)) for (q, r), nm in zip([(1, 0), (3, 0), (2, -1)], ("enemy_bandit_melee", "enemy_wolf", "enemy_skeleton"))]
        plates = [(p.fxo(hex_plate(p.col, glow("#FF9A3C"))), cell(*c)) for c in cells]
        puffs = [p.fxo(ico(p.col, 1.0, glow("#FF9A3C" if k % 3 else "#FFD27A"), sub=1, name="puff")) for k in range(14)]

        def up(s, h=h, fa=fa, kind=kind, plates=plates, puffs=puffs, p=p):
            k = out(seg(s, 0, 0.1)) if s < 0.45 else 1 - smooth(seg(s, 0.45, 0.6))
            h.lean(8 * k, 0)
            h.move((0, 0, 0.06 * k))
            lag = 0.12 if kind == "first" else 0.0  # puffs start this much after the hexes
            for j, pf in enumerate(puffs):
                st = 0.06 + lag + 0.025 * j
                u = seg(s, st, st + 0.32)
                if 0 < u < 1:
                    ang = math.radians(((j * 37) % 11 - 5) * 5.5)
                    dist = 0.45 + 2.6 * out(u)
                    pf.show(p.at((math.cos(ang) * dist, math.sin(ang) * dist, 0.55 - 0.25 * u)), 0.08 + 0.22 * u, alpha=0.9 * (1 - u ** 2))
                else:
                    pf.hide()
            for pl, c in plates:
                reach = (c.length - 0.45) / 2.6  # 0 at the mouth, 1 at the far edge
                if kind == "first":
                    on = 0.06 + 0.12 * reach  # a quick sweep outward, ahead of the puffs
                else:
                    on = 0.06 + 0.32 * (1 - (1 - reach) ** 0.5)  # when the first puffs get there (out() eased, inverted)
                w = seg(s, on, on + 0.5)
                pl.show(p.at(c) + V((0, 0, 0.012)), 1.0, alpha=0.85 * (out(seg(s, on, on + 0.06)) * (1 - seg(s, on + 0.3, on + 0.5))) if 0 < w < 1 else 0)
            for a_, c in fa:
                reach = (c.length - 0.45) / 2.6
                recoil(a_, s, 0.06 + lag + 0.32 * (1 - (1 - reach) ** 0.5), 0, tilt=14)
        p.update = up
        panes.append(p)
    return panes


# --- Single-target save spells (preview, Nov 8) ----------------------------------
# Saves, so nothing flies that can hit or miss: the effect always arrives. Every option uses the same lead-in (the bolt charge in the
# spell's colour), then delivers it a different way. Each pane plays a failed save, then a passed one: Sacred Flame on a pass is half
# damage (03 → a passed save against a damage spell takes half damage), so the flame comes at about half size with half the recoil;
# Faerie Fire and Lull on a pass do nothing, so the effect reaches the foe and breaks apart while it shakes it off.

SAVE_SPELLS = (  # name, main colour, core colour, deep colour (rings, pulses and letters, to read on the grass), caster, target, its head height
    ("Sacred Flame", "#FFE7A0", "#FFFBEA", "#FFC93A", "cleric", "enemy_skeleton", 0.7),
    ("Faerie Fire", "#7CF0B8", "#D8FFEC", "#2FCB8A", "elf", "enemy_bandit_melee", 0.7),
    ("Lull", "#9FA8FF", "#E2E5FF", "#6C78F0", "elf", "enemy_wolf", 0.5),
)


def tongues(col, mat, n=7, r=0.22, name="tongues"):
    """Flame tongues: upright four-sided spikes on a circle round the origin plus a taller one in the middle; 1.0 tall, scaled per frame."""
    bm = bmesh.new()
    for k in range(n + 1):
        if k < n:
            a = 2 * math.pi * k / n
            c, h, w = V((math.cos(a) * r, math.sin(a) * r, 0)), 0.7 + 0.3 * ((k * 5) % 3) / 2, 0.075
        else:
            c, h, w = V((0, 0, 0)), 1.0, 0.11
        vs = [bm.verts.new(c + V(d) * w) for d in ((1, 0, 0), (0, 1, 0), (-1, 0, 0), (0, -1, 0))]
        tip = bm.verts.new(c + V((0, 0, h)) + c * 0.25)
        for i in range(4):
            bm.faces.new((vs[i], vs[(i + 1) % 4], tip))
    return mesh_ob(name, bm, [mat], col)


def hull(col, target, hexcol, push=0.03):
    """A glow outline round a mini: its mesh pushed out along the normals and turned inside out, with back faces culled, so only a rim
    shows round the edge. Parented to the mini so it follows every move."""
    bm = bmesh.new()
    bm.from_mesh(target.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * push
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    m = glow(hexcol, f"hull{hexcol}")
    m.use_backface_culling = True
    ob = mesh_ob("hull", bm, [m], col)
    ob.parent = target
    return ob


def zee(col, mat):
    t = bpy.data.curves.new("zee", "FONT")
    t.body = "z"
    t.size = 0.22
    t.align_x, t.align_y = "CENTER", "CENTER"
    t.extrude = 0.006
    ob = bpy.data.objects.new("zee", t)
    ob.data.materials.append(mat)
    ob.visible_shadow = False
    col.objects.link(ob)
    return ob


def tag(p, text):
    """A caption in the pane's lower left, shown or hidden per frame."""
    c = bpy.data.curves.new(f"tag_{text}", "FONT")
    c.body = text
    c.size = 0.05
    ob = bpy.data.objects.new(f"tag_{text}", c)
    ob.data.materials.append(glow("#3A3532", f"tagmat_{text}"))
    ob.parent = p.cam
    ob.location = (-0.69, -0.45, -2.0)
    ob.visible_shadow = False
    bpy.context.scene.collection.objects.link(ob)
    return ob


def shake(a, s, t0, dur=0.32, deg=12.0):
    """Shaking a spell off: the mini twists side to side on the spot, dying away."""
    u = seg(s, t0, t0 + dur)
    if 0 < u < 1:
        a.spin += deg * math.sin(2 * math.pi * 3 * u) * (1 - u)


def k_savespell(T, E, scene):
    panes = []
    specs = [("A  Bloom on the target", "bloom"), ("B  Falls from above", "fall"), ("C  Pulse along the ground", "pulse")]
    for i, (label, kind) in enumerate(specs):
        for j, (spell, c1, c2, c0, who, foe, hh) in enumerate(SAVE_SPELLS):
            p = Pane(scene, (i * 3 + j) * 40, f"{label}  ·  {spell}", 3.0)
            if who == "cleric":
                hob = hero(T, p.col, "human", "broad", "b", "long", "mace", "shield", tier="heavy", skin=0, hairc=3, cloth=4)
            else:
                hob = hero(T, p.col, "elf", "average", "c", "long", "staff", tier="none", skin=1, hairc=3, cloth=3, caster=True)
            h = p.add(hob, (0, 0, 0), 90)
            f = p.add(place(E, foe, p.col), (3, 0, 0), 270)
            rg = p.fxo(ring(p.col, 1.0, 0.07, glow(c0)))
            orb = p.fxo(ico(p.col, 0.1, glow(c2)))
            trail = [p.fxo(ico(p.col, 0.085, glow(c1))) for _ in range(4)]
            conv = p.fxo(ring(p.col, 1.0, 0.08, glow(c0)))
            flare = p.fxo(ring(p.col, 1.0, 0.09, glow(c0)))
            waves = [p.fxo(ring(p.col, 1.0, 0.09, glow(c0))) for k in range(3)]
            fl = p.fxo(tongues(p.col, glow(c1)))
            fl2 = p.fxo(tongues(p.col, glow(c2), n=5, r=0.1, name="tongues_core"))
            star = p.fxo(spikes(p.col, 9, 0.3, 0.045, glow(c2), up=0.3))
            hl = p.fxo(hull(p.col, f.ob, c1))
            motes = [p.fxo(ico(p.col, 0.055, glow(c2 if k % 2 else c0), sub=0, name="mote")) for k in range(8)]
            zs = [p.fxo(zee(p.col, glow(c0))) for _ in range(3)]
            tags = [tag(p, "Failed save"), tag(p, "Passed save: half damage" if spell == "Sacred Flame" else "Passed save: no effect")]
            p.tags = tags

            def up(s, k=0, h=h, f=f, kind=kind, spell=spell, rg=rg, orb=orb, trail=trail, conv=conv, flare=flare, waves=waves, fl=fl, fl2=fl2,
                   star=star, hl=hl, motes=motes, zs=zs, tags=tags, hh=hh, p=p):
                for n_, tg in enumerate(tags):
                    tg.hide_render = n_ != k
                passed = k == 1
                charge(h, s, rg, p, dur=0.14)
                c = f.home
                rel = 0.14
                # Delivery: when and how the spell reaches the foe.
                if kind == "bloom":
                    land = 0.24
                    u = seg(s, rel, land)
                    if 0 < u < 1:
                        conv.show(c + V((0, 0, 0.02)), 0.75 - 0.4 * out(u), alpha=min(1, 4 * u))
                    else:
                        conv.hide()
                elif kind == "fall":
                    land = 0.30
                    u = seg(s, rel, land)
                    top, bot = c + V((0, 0, 2.2)), c + V((0, 0, 0.75 if spell != "Sacred Flame" else 0.3))
                    if 0 < u < 1:
                        orb.show(top.lerp(bot, inn(u)) + FRONT * 0.5, 1.0)
                        for n_, tl in enumerate(trail):
                            uu = max(0.0, u - 0.07 * (n_ + 1))
                            tl.show(top.lerp(bot, inn(uu)) + FRONT * 0.5, 0.85 - 0.15 * n_, alpha=0.85 if u > 0.07 * (n_ + 1) else 0)
                    else:
                        orb.hide()
                        for tl in trail:
                            tl.hide()
                else:
                    land = 0.36
                    a0, b0 = h.home + V((0.35, 0, 0.02)), c + V((-0.1, 0, 0.02))
                    for n_, w in enumerate(waves):
                        u = seg(s, rel + 0.03 * n_, land + 0.03 * n_)
                        if 0 < u < 1:
                            w.show(a0.lerp(b0, smooth(u)), 0.28 - 0.06 * n_, alpha=(1.0 - 0.3 * n_) * min(1, 5 * u))
                        else:
                            w.hide()
                v = seg(s, land, land + 0.22)  # a ring flares at the foe's feet as it lands
                if 0 < v < 1:
                    flare.show(c + V((0, 0, 0.02)), (0.35 + 0.15 * out(v)) if kind == "bloom" else (0.25 + 0.3 * out(v)), alpha=1 - v)
                else:
                    flare.hide()
                # The effect on the foe.
                if spell == "Sacred Flame":
                    size = 0.55 if passed else 1.0
                    v = seg(s, land, land + 0.42)
                    if 0 < v < 1:
                        grow = out(seg(s, land, land + 0.1))
                        a = 1 - seg(s, land + 0.16, land + 0.42) ** 1.5
                        fl.show(c + FRONT * 0.6, (size, size, 0.95 * size * grow * (1 + 0.08 * math.sin(s * 70))), alpha=0.9 * a)
                        fl2.show(c + FRONT * 0.7, (size, size, 1.1 * size * grow), alpha=a)
                    else:
                        fl.hide()
                        fl2.hide()
                    flash(star, s, land, c + V((0, 0, 0.5 * size)), size=size, dur=0.2)
                    recoil(f, s, land, 0, tilt=8 if passed else 16, push=0.06 if passed else 0.12)
                elif spell == "Faerie Fire":
                    if not passed:
                        if s >= land:
                            a = out(seg(s, land, land + 0.12)) * (0.75 + 0.2 * math.sin(2 * math.pi * 2.2 * (s - land)))
                            hl.ob.hide_render = False
                            set_alpha(hl.ob, a)
                        for n_, m in enumerate(motes):
                            ph = s - land - 0.05 * n_
                            if ph > 0:
                                ang = math.radians(n_ * 45 + 40 * ph)
                                tw = bump((ph * 1.6) % 1.0)
                                m.show(c + V((math.cos(ang) * 0.32, math.sin(ang) * 0.32, 0.2 + 0.09 * n_)) + FRONT * 0.3, 0.6 + 0.6 * tw, alpha=tw)
                        recoil(f, s, land, 0, tilt=5, push=0.03)
                    else:
                        v = seg(s, land, land + 0.18)
                        if 0 < v < 1:
                            hl.ob.hide_render = False
                            set_alpha(hl.ob, 0.8 * (1 - v) * (0.6 + 0.4 * math.sin(s * 120)))
                        for n_, m in enumerate(motes):
                            u = seg(s, land + 0.08, land + 0.4)
                            if 0 < u < 1:
                                ang = math.radians(n_ * 45)
                                r = 0.25 + 0.45 * out(u)
                                m.show(c + V((math.cos(ang) * r, math.sin(ang) * r, 0.25 + 0.07 * n_ + 0.1 * u)) + FRONT * 0.3, 1.0 - 0.5 * u, alpha=1 - u)
                        shake(f, s, land + 0.06)
                else:  # Lull
                    head = c + V((0, 0, hh))
                    for n_, m in enumerate(motes):
                        u = seg(s, land - 0.04, land + 0.3)
                        if 0 < u < 1:
                            ang = math.radians(n_ * 45 + 300 * u)
                            if not passed:
                                r, z, a = 0.45 - 0.3 * out(u), 0.25 - 0.2 * u, 1 - u ** 2
                            else:
                                r, z, a = 0.45 - 0.25 * out(min(1, 2 * u)) + 0.5 * max(0.0, u - 0.5) * 2, 0.25 - 0.1 * u, 1 - u ** 2
                            m.show(head + V((math.cos(ang) * r, math.sin(ang) * r, z)) + FRONT * 0.3, 1.0, alpha=a)
                    if not passed:
                        k_ = smooth(seg(s, land + 0.15, land + 0.55))
                        f.lean(16 * k_, 180, edge=0)  # nods off, its head drooping
                        f.move((0, 0, -0.03 * k_))
                        for n_, z in enumerate(zs):
                            u = seg(s, land + 0.3 + 0.25 * n_, land + 1.0 + 0.25 * n_)
                            if 0 < u < 1:
                                z.show(head + V((0.1 + 0.2 * u, 0, 0.12 + 0.45 * u)) + FRONT, 1.0 + 0.6 * u, rot=Matrix.Rotation(math.radians(52), 4, "X"), alpha=min(1, 5 * u) * (1 - u ** 2))
                    else:
                        shake(f, s, land + 0.12)
            p.update = up
            panes.append(p)
    return panes


k_savespell.passes = 2  # each pane plays a failed save, then a passed one
k_savespell.cols = 3


KINDS = {"melee": k_melee, "sweep": k_sweep, "thrust": k_thrust, "heavy": k_heavy, "shot": k_shot, "thrown": k_thrown, "bolt": k_bolt,
         "touch": k_touch, "area": k_area, "buff": k_buff, "summon": k_summon, "hit": k_hit, "miss": k_miss, "cone": k_cone,
         "savespell": k_savespell}


# --- Rendering ----------------------------------------------------------------

def setup():
    hk.empty_scene()
    for k, c in enumerate(GRASS):
        hk.PALETTE[f"grass{k}"] = c
    hk.PALETTE["gapgreen"] = GAP
    T = rp.load_templates(rp.latest(os.path.join("minis", "heroes"), "hero_kit"))
    E = rp.load_templates(os.path.join(hk.ART, "minis", "enemies", "humanoid_minis_v4.blend"))
    E.update(rp.load_templates(os.path.join(hk.ART, "minis", "enemies", "enemy_minis_v6.blend")))
    rp.stage(V((0, 0, 0)), 5, 40)
    for ob in [o for o in bpy.context.scene.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(ob)
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = PANE
    s.render.film_transparent = False
    s.eevee.taa_render_samples = 16
    return T, E, s


def render_kind(kind, out_dir):
    T, E, scene = setup()
    panes = KINDS[kind](T, E, scene)
    tmp = tempfile.mkdtemp(prefix=f"atk_{kind}_")
    passes = getattr(KINDS[kind], "passes", 1)
    n = int(round(CYCLE * FPS * passes))
    grid_cols = getattr(KINDS[kind], "cols", 2 if len(panes) == 4 else len(panes))
    grid_rows = (len(panes) + grid_cols - 1) // grid_cols
    W, H = PANE
    frames = []
    land = {}
    for fi in range(n):
        k = min(passes - 1, int(fi / FPS // CYCLE))
        s = fi / FPS - k * CYCLE - LEAD
        tiles = []
        for p in panes:
            for a in p.actors:
                a.reset()
            for f in p.fx:
                f.hide()
            s_ = max(s, -1.0) if s >= 0 else -1.0
            p.update(s_, k) if passes > 1 else p.update(s_)
            for a in p.actors:
                a.apply()
            scene.camera = p.cam
            path = os.path.join(tmp, "pane.png")
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            im = bpy.data.images.load(path)
            tiles.append(np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4))
            bpy.data.images.remove(im)
        g = np.ones((grid_rows * H + (grid_rows - 1) * 4, grid_cols * W + (grid_cols - 1) * 4, 4), dtype=np.float32)
        for k, t in enumerate(tiles):
            r, c = k // grid_cols, k % grid_cols
            y = (grid_rows - 1 - r) * (H + 4)
            g[y:y + H, c * (W + 4):c * (W + 4) + W] = t
        fp = os.path.join(tmp, f"f{fi:04d}.png")
        save_png(g, fp)
        frames.append(fp)
        if k == 0 and abs(s - 0.22) < 0.5 / FPS:
            land["still"] = fp
    if CHECK:
        for k in range(passes):
            strip = []
            for t in CHECK_TIMES:
                im = bpy.data.images.load(frames[min(len(frames) - 1, int(round((t + LEAD + k * CYCLE) * FPS)))])
                w, h = im.size
                strip.append(np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::2, ::2])
                bpy.data.images.remove(im)
            save_png(np.concatenate(strip[::-1], axis=0), os.path.join(CHECK, f"check_{kind}{'_' + str(k) if k else ''}.png"))
    # Twice at real speed (every other frame), then once at half speed (every frame), played at 30.
    seq = frames[::2] + frames[::2] + frames
    stem = f"attack_{kind}"
    v = max(hk.next_number(out_dir, stem, "mp4"), hk.next_number(out_dir, stem, "png"))
    mp4 = os.path.join(out_dir, f"{stem}_v{v}.mp4")
    encode(seq, mp4, g.shape[1], g.shape[0])
    shutil.copy(land.get("still", frames[len(frames) // 3]), os.path.join(out_dir, f"{stem}_v{v}.png"))
    shutil.rmtree(tmp, ignore_errors=True)
    print("CLIP", mp4)


def save_png(px, path):
    h, w, _ = px.shape
    im = bpy.data.images.new("tmp_save", w, h, alpha=True)
    im.pixels[:] = px.ravel().tolist()
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)


def encode(files, mp4, w, h):
    sc = bpy.data.scenes.new("encode")
    sc.render.resolution_x, sc.render.resolution_y = w - w % 2, h - h % 2
    sc.render.resolution_percentage = 100
    sc.render.fps = 30
    se = sc.sequence_editor_create()
    d = os.path.dirname(files[0])
    # Copy into a numbered run so the strip reads them in order (duplicates included).
    run = os.path.join(d, "run")
    os.makedirs(run, exist_ok=True)
    for k, f in enumerate(files):
        shutil.copy(f, os.path.join(run, f"r{k:04d}.png"))
    names = sorted(os.listdir(run))
    strip = se.strips.new_image("clip", os.path.join(run, names[0]), 1, 1)
    for nm in names[1:]:
        strip.elements.append(nm)
    sc.frame_start, sc.frame_end = 1, len(names)
    sc.render.image_settings.media_type = "VIDEO"
    sc.render.image_settings.file_format = "FFMPEG"
    sc.render.ffmpeg.format = "MPEG4"
    sc.render.ffmpeg.codec = "H264"
    sc.render.ffmpeg.constant_rate_factor = "HIGH"
    sc.render.filepath = mp4
    sc.view_settings.view_transform = "Standard"
    bpy.ops.render.render(animation=True, scene=sc.name)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    out_dir, kinds = args[0], args[1:] or list(KINDS)
    os.makedirs(out_dir, exist_ok=True)
    for k in kinds:
        render_kind(k, out_dir)
