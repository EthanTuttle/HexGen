"""Builds the map encounter trial kit (design/07 -> Encounters, look on trial): small scenes that stand on a map tile, and a badge for each kind.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_encounter_figures.py
Saves art/encounters/encounters_vN.blend. Export with export_gltf.py to art/export/encounters.glb. Hand-off: art/handoff/encounters_kit.md.

Every scene is one mesh at true mini scale, its pivot on the ground at its middle. Version B places it as it is; version A is the same piece scaled up by the engine, so both looks share one kit.
  enc_fight_wolves       three wolves (the combat minis)
  enc_fight_bandits      three bandits (the combat minis)
  enc_social_trader      a trader beside a loaded cart
  enc_social_drinking    three drinkers round a table, mugs up, with a barrel
  enc_discovery_treasure a half-dug chest, a heap of earth and a spade
  enc_badge_fight, _social, _discovery   a hex plate with an icon and no text, standing upright, its pivot at its foot. Face it to the camera.
The trader, the drinkers and the treasure are stand-ins of ours, with their looks open to Ethan.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build_standin_minis as sm  # noqa: E402
import build_village_cells as vc  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402

hk.PALETTE.update({"ring_social": "#4FA3A0", "robe_trader": "#7C4F8E", "hat_trader": "#D9A93A", "drinker_a": "#B5533C", "drinker_b": "#4F7F58", "drinker_c": "#C8A24A",
                   "dug_earth": "#6E5137", "dug_dark": "#4E3926", "chest": "#7A4E2A", "chest_band": "#3F3A36", "coins": "#E9C04A", "mug": "#B98A54", "foam": "#F4EFE3",
                   "goods_red": "#B5533C", "badge_edge": "#3B3530", "badge_fight": "#B5362A", "badge_social": "#2F8F8A", "badge_discovery": "#D99A1E", "badge_icon": "#FBF6EA"})
GROUP = 1.08  # bases apart, so minis' bases don't overlap
ZERO = Vector((0, 0, 0))


def placed(p, at, turn, make):
    """Whatever make adds, turned and moved as one."""
    before = set(p.bm.verts)
    make()
    m = Matrix.Translation(at) @ Matrix.Rotation(turn, 4, "Z")
    for v in set(p.bm.verts) - before:
        v.co = m @ v.co


def figure(p, cloth, legs, ring, up=False, hat=None):
    """The stand-ins' body on a base: 1.3 tall, an arm down, and one raised if up. Returns the raised hand."""
    sm.base(p, ring)
    hip, shoulder, head_r, head_z, w = sm.biped(p, 1.3, cloth, "skin", legs)
    h = 1.3 - sm.BASE_H
    sm.arm_down(p, -1, shoulder, w, h, cloth)
    hand = sm.arm_up(p, 1, shoulder, w, h, cloth) if up else None
    if not up:
        sm.arm_down(p, 1, shoulder, w, h, cloth)
    if hat:
        p.cone(Vector((0, 0, 0)), head_r * 1.7, head_r * 1.3, hat, segments=6, z=head_z + head_r * 0.4)
    return hand


def trader():
    p = hk.Piece("enc_social_trader")
    placed(p, Vector((-0.62, -0.1, 0)), 0.2, lambda: figure(p, "robe_trader", "trousers", "ring_social", hat="hat_trader"))
    rng = hk.seeded(p.name)
    before = set(p.bm.verts)
    vr.grain_cart(p, rng, ZERO, 0.0, shafts=True, load="sack")
    for v in set(p.bm.verts) - before:  # the tiles' cart at a mini's scale
        v.co = v.co * 1.5 + Vector((0.42, 0.14, 0))
    # Goods heaped on top, so it reads as a trader's and not a farm's. Colours are a proposal.
    top = max(v.co.z for v in p.bm.verts)
    p.box(Vector((0.1, 0.14, 0)), (0.42, 0.42, 0.3), "chest", z=top - 0.04, spin=0.2)
    p.box(Vector((0.6, 0.24, 0)), (0.34, 0.34, 0.24), "goods_red", z=top - 0.04, spin=-0.3)
    p.box(Vector((0.56, -0.06, 0)), (0.34, 0.26, 0.2), "hat_trader", z=top - 0.04, spin=0.4)
    p.blob(Vector((0.14, 0.14, 0)), 0.2, "robe_trader", z=top + 0.28, squash=0.7)
    return p


def drinking():
    p = hk.Piece("enc_social_drinking")
    p.prism([Vector((math.cos(k * math.pi / 3), math.sin(k * math.pi / 3), 0)) * 0.34 for k in range(6)], 0.42, 0.48, "chest")
    p.cylinder(ZERO, 0.08, 0.42, "trunk", segments=5)
    for k, (x, y) in enumerate(((-0.16, 0.08), (0.16, 0.1), (0.0, -0.16))):
        at = Vector((x, y, 0.48))
        p.cylinder(at, 0.05, 0.1, "mug", segments=5)
        p.cylinder(at, 0.052, 0.02, "foam", segments=5, z=0.1)
    for k, (a, cloth) in enumerate(((math.radians(205), "drinker_a"), (math.radians(335), "drinker_b"), (math.radians(90), "drinker_c"))):
        def make(cloth=cloth, k=k):
            hand = figure(p, cloth, "trousers", "ring_social", up=True)
            p.cylinder(hand, 0.055, 0.12, "mug", segments=5, z=-0.02)
            p.cylinder(hand, 0.057, 0.025, "foam", segments=5, z=0.1)
        placed(p, Vector((math.cos(a), math.sin(a), 0)) * 0.72, a + math.pi / 2, make)
    vc.barrel(p, Vector((0.92, 0.62, 0)), r=0.17, h=0.5)
    return p


def treasure():
    p = hk.Piece("enc_discovery_treasure")
    p.prism(hk.hex_corners(0.72, pointy=False)[::-1], 0.0, 0.03, "dug_dark", side_mat="dug_earth")
    p.blob(Vector((-0.62, 0.42, 0)), 0.42, "dug_earth", squash=0.7)
    p.blob(Vector((-0.3, 0.62, 0)), 0.26, "dug_earth", squash=0.7)
    p.box(Vector((0.05, -0.02, 0)), (0.7, 0.46, 0.34), "chest", z=0.03, spin=0.25)
    for x in (-0.22, 0.22):
        p.box(vr.turn(Vector((x, 0, 0)), 0.25) + Vector((0.05, -0.02, 0)), (0.07, 0.48, 0.36), "chest_band", z=0.03, spin=0.25)
    # The lid thrown back, coins heaped up to it.
    p.blob(Vector((0.05, -0.02, 0)), 0.28, "coins", z=0.34, squash=0.5)
    p.box_rot(Vector((0.1, 0.24, 0.58)), (0.72, 0.42, 0.06), "chest", Matrix.Rotation(0.25, 4, "Z") @ Matrix.Rotation(math.radians(70), 4, "X"))
    p.box_rot(Vector((0.66, -0.42, 0.55)), (0.05, 0.05, 1.1), "trunk", Matrix.Rotation(math.radians(-16), 4, "Y"))
    p.box_rot(Vector((0.53, -0.42, 0.1)), (0.24, 0.05, 0.26), "steel", Matrix.Rotation(math.radians(-16), 4, "Y"))
    return p


def plate(p, outline, y0, y1, mat, side=None):
    """A shape drawn as (x, z), raised from y0 to y1: towards the viewer is -y."""
    before = set(p.bm.verts)
    p.prism([Vector((x, z, 0)) for x, z in outline], y0, y1, mat, side_mat=side)
    for v in set(p.bm.verts) - before:
        v.co = Vector((v.co.x, -v.co.z, v.co.y))


def rotated(points, a, at=(0, 0)):
    return [(at[0] + x * math.cos(a) - z * math.sin(a), at[1] + x * math.sin(a) + z * math.cos(a)) for x, z in points]


def badge(name, colour, icon):
    """A hex plate 1 wide with a dark edge, icon on both faces, standing on its point."""
    p = hk.Piece(f"enc_badge_{name}")
    mid = 0.58
    hexes = lambda r: [(r * math.cos(k * math.pi / 3 + math.pi / 6), mid + r * math.sin(k * math.pi / 3 + math.pi / 6)) for k in range(6)]  # noqa: E731
    plate(p, hexes(0.58), -0.04, 0.04, "badge_edge")
    plate(p, hexes(0.49), 0.04, 0.055, colour)
    plate(p, hexes(0.49), -0.055, -0.04, colour)
    for sgn in (-1, 1):
        for shape in icon():
            pts = [(x * sgn, z + mid) for x, z in shape]
            if sgn < 0:
                pts = pts[::-1]
            if sgn > 0:
                plate(p, pts, 0.05, 0.075, "badge_icon")
            else:
                plate(p, pts, -0.075, -0.05, "badge_icon")
    return p


def swords():
    out = []
    for a in (math.radians(40), math.radians(-40)):
        blade = [(-0.035, -0.12), (0.035, -0.12), (0.035, 0.26), (0, 0.33), (-0.035, 0.26)]
        guard = [(-0.11, -0.15), (0.11, -0.15), (0.11, -0.115), (-0.11, -0.115)]
        grip = [(-0.025, -0.28), (0.025, -0.28), (0.025, -0.15), (-0.025, -0.15)]
        out += [rotated(blade, a), rotated(guard, a), rotated(grip, a)]
    return out


def speech():
    round_part = [(0.3 * math.cos(k * math.pi / 5), 0.05 + 0.21 * math.sin(k * math.pi / 5)) for k in range(10)]
    tail = [(-0.15, -0.1), (0.02, -0.1), (-0.18, -0.3)]
    return [round_part, tail]


def sparkle():
    def star(r, cx, cz):
        waist = r * 0.22
        pts = []
        for k in range(8):
            a = k * math.pi / 4 + math.pi / 2
            d = r if k % 2 == 0 else waist
            pts.append((cx + d * math.cos(a), cz + d * math.sin(a)))
        return pts
    return [star(0.3, -0.03, -0.02), star(0.12, 0.23, 0.2)]


def scene_from_minis(col, t, name, parts):
    """Existing minis joined into one mesh, each where it stands."""
    objs = []
    for mini, x, y, turn in parts:
        ob = bpy.data.objects.new(name, t[mini].data.copy())
        ob.location = (x, y, 0)
        ob.rotation_euler.z = turn
        col.objects.link(ob)
        objs.append(ob)
    bpy.context.view_layer.update()
    with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs, selected_objects=objs):
        bpy.ops.object.join()
    objs[0].data.name = objs[0].name = name
    with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=[objs[0]], selected_objects=[objs[0]]):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=False)
    return objs[0]


def build():
    hk.empty_scene()
    hk.STANDS_ALONE = True  # seen whole from every side, as minis are
    col = hk.new_collection("encounters")
    t = {}
    for stem in ("enemy_minis", "humanoid_minis"):
        t.update(rp.load_templates(rp.latest(os.path.join("minis", "enemies"), stem)))
    a, b = GROUP / 2, GROUP * 0.433
    scene_from_minis(col, t, "enc_fight_wolves", [("enemy_wolf", -a, b, 0.5), ("enemy_wolf", a, b, -0.4), ("enemy_wolf_elite", 0, -b, 0.1)])
    scene_from_minis(col, t, "enc_fight_bandits", [("enemy_bandit_melee", -a, b, 0.3), ("enemy_bandit_ranged", a, b, -0.3), ("enemy_bandit_elite", 0, -b, 0.0)])
    for make in (trader, drinking, treasure):
        make().finish(col)
    badge("fight", "badge_fight", swords).finish(col)
    badge("social", "badge_social", speech).finish(col)
    badge("discovery", "badge_discovery", sparkle).finish(col)
    for o in sorted(col.objects, key=lambda o: o.name):
        o.data.calc_loop_triangles()
        size = [max(v.co[k] for v in o.data.vertices) - min(v.co[k] for v in o.data.vertices) for k in range(3)]
        print("TRIS", o.name, len(o.data.loop_triangles), "size", [round(x, 2) for x in size])
    path = hk.next_version(os.path.join(hk.ART, "encounters"), "encounters")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
