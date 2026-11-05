"""Renders the hero kit assembled from descriptions: every head up close, the combos at the Look step's size, builds, and the map's sizes.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_hero_kit.py [-- faces | look | map | weapons | dragons]
Writes art/preview/hero_kit_*_vN.png.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_hero_kit as hb  # noqa: E402
import hexkit as hk  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_preview as rp  # noqa: E402

GROUND = "#A9CD84"
S = hb.SWATCHES
H, E, C = S["hair"], S["eyes"], S["cloth"]


def hero(race, build, head, hair, skin, hair_c, eyes, cloth, tier, main, off=None):
    return dict(race=race, build=build, head=head, hair=hair, armour=tier, main=main, offhand=off, colours=dict(skin=skin, hair=hair_c, eyes=eyes, cloth=cloth))


COMBOS = [
    ("human", hero("human", "average", "a", "short", S["skin"]["human"][1], H[1], E[1], C[1], "heavy", "longsword", "shield")),
    ("elf", hero("elf", "slim", "c", "long", S["skin"]["elf"][1], H[3], E[0], C[2], "light", "shortbow")),
    ("dwarf", hero("dwarf", "broad", "b", "crest", S["skin"]["dwarf"][2], H[5], E[2], C[0], "heavy", "warhammer")),
    ("halfling", hero("halfling", "average", "d", "topknot", S["skin"]["halfling"][3], H[0], E[3], C[4], "light", "mace", "shield")),
    ("golem", hero("golem", "broad", "a", None, S["skin"]["golem_stone"][0], H[0], E[3], C[0], "none", "greataxe")),
    ("dragonborn", hero("dragonborn", "broad", "a", None, hb.DRAGON_TYPES["red"], H[0], E[3], C[4], "heavy", "greatsword")),
    ("tiefling", hero("tiefling", "average", "b", "tail", S["skin"]["tiefling"][2], H[0], E[3], C[5], "medium", "halberd")),
    ("blue", hero("dragonborn", "broad", "b", None, hb.DRAGON_TYPES["blue"], H[0], E[3], C[4], "heavy", "mace", "shield")),
]


def start():
    hk.empty_scene()
    t = rp.load_templates(rp.latest(os.path.join("minis", "heroes"), "hero_kit"))
    col = hk.new_collection("line")
    hk.PALETTE["hero_ground"] = GROUND
    return t, col


def floor(col):
    g = hk.Piece("ground")
    g.box(Vector((0, 0, 0)), (160, 160, 0.02), "hero_ground", z=-0.02)
    g.finish(col)


def shot(stem, target, distance, pitch, size):
    for ob in [o for o in bpy.context.scene.objects if o.type in ("LIGHT", "CAMERA")]:  # stage adds its own each time
        bpy.data.objects.remove(ob)
    rp.stage(target, distance, pitch)
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = size
    rp.render(stem)


def stand(t, col, desc, name, at=(0, 0, 0), spin=-28):
    ob, n = hb.assemble(t, desc, name, col)
    ob.location = Vector(at)
    ob.rotation_euler.z = math.radians(spin)
    return ob, n


def faces():
    """Each race's four heads on the shoulders of a plain body, close."""
    plain = {"human": (S["skin"]["human"][1], "short"), "elf": (S["skin"]["elf"][1], "long"), "dwarf": (S["skin"]["dwarf"][2], "short"), "halfling": (S["skin"]["halfling"][0], "topknot"), "golem": (S["skin"]["golem_metal"][0], None), "dragonborn": (hb.DRAGON_TYPES["blue"], None), "tiefling": (S["skin"]["tiefling"][2], "long")}
    stems = []
    for race in hb.RACES:
        for head in hb.HEADS:
            t, col = start()
            floor(col)
            desc = hero(race, "average", head, plain[race][1], plain[race][0], H[1], E[3] if race in ("dragonborn", "tiefling", "golem") else E[1], C[1], "medium", "shortsword")
            stand(t, col, desc, "h", spin=-24)
            k = hb.RACES[race]["k"]
            stem = f"hero_kit_face_{race}_{head}"
            top = hb.full(race, hb.head_point(race, "average"))
            shot(stem, top, 1.15, 8, (420, 420))
            stems.append(stem)
            _ = k
    fm.sheet(stems, "hero_kit_faces", cols=8)


def look():
    stems, rows = [], []
    for spin, tag in ((-28, "front"), (152, "back")):
        for name, desc in COMBOS:
            t, col = start()
            floor(col)
            _, n = stand(t, col, desc, name, spin=spin)
            if spin == -28:
                rows.append((name, n))
            stem = f"hero_kit_{tag}_{name}"
            shot(stem, Vector((0, 0, 0.8)), 3.0, 12, (640, 900))
            stems.append(stem)
    print("HEROTRIS", rows)
    fm.sheet(stems[:8], "hero_kit_look", cols=4)
    fm.sheet(stems[8:], "hero_kit_look_back", cols=4)
    # Builds of two races, in the same gear.
    stems = []
    for race, skin, hair in (("human", S["skin"]["human"][2], "short"), ("dwarf", S["skin"]["dwarf"][1], "short"), ("dragonborn", hb.DRAGON_TYPES["green"], None)):
        for build in hb.BUILDS:
            t, col = start()
            floor(col)
            stand(t, col, hero(race, build, "a", hair, skin, H[1], E[1], C[1], "medium", "longsword"), "b", spin=-18)
            stem = f"hero_kit_build_{race}_{build}"
            shot(stem, Vector((0, 0, 0.72)), 3.0, 12, (560, 760))
            stems.append(stem)
    for tier in ("none", "light", "medium", "heavy"):
        t, col = start()
        floor(col)
        stand(t, col, hero("human", "average", "a", "short", S["skin"]["human"][2], H[1], E[1], C[0], tier, "spear"), "b", spin=-18)
        stem = f"hero_kit_tier_{tier}"
        shot(stem, Vector((0, 0, 0.8)), 3.0, 12, (560, 760))
        stems.append(stem)
    fm.sheet(stems, "hero_kit_builds", cols=3)
    stems = []
    for style in hb.HAIRSTYLES:
        t, col = start()
        floor(col)
        stand(t, col, hero("human", "average", "a", style, S["skin"]["human"][1], H[hb.HAIRSTYLES.index(style)], E[1], C[1], "light", "longsword"), "b", spin=-40)
        stem = f"hero_kit_hair_{style}"
        shot(stem, hb.full("human", hb.head_point("human", "average")), 1.4, 8, (420, 420))
        stems.append(stem)
    fm.sheet(stems, "hero_kit_hair", cols=6)


def weapons():
    """Every weapon, cycling the races to test the fit: a shield or second weapon where it's one-handed, every third."""
    cast = [("human", S["skin"]["human"][1], "short", H[1]), ("elf", S["skin"]["elf"][0], "long", H[3]), ("dwarf", S["skin"]["dwarf"][2], "crest", H[5]), ("halfling", S["skin"]["halfling"][3], "topknot", H[0]),
            ("golem", S["skin"]["golem_metal"][0], None, H[0]), ("dragonborn", hb.DRAGON_TYPES["blue"], None, H[0]), ("tiefling", S["skin"]["tiefling"][1], "tail", H[0])]
    stems = []
    for i, weapon in enumerate(hb.GRIP_OF):
        race, skin, hair, hc = cast[i % len(cast)]
        off = ("shield", None, "dagger")[i % 3] if weapon in hb.ONE_HANDED else None
        t, col = start()
        floor(col)
        _, n = stand(t, col, hero(race, "average", "abcd"[i % 4], hair, skin, hc, E[3] if race in ("golem", "dragonborn", "tiefling") else E[1], C[i % 6], ("light", "medium", "heavy")[i % 3], weapon, off), "w", spin=-25)
        print("WEAPONTRIS", weapon, race, n)
        stem = f"hero_kit_weapon_{weapon}"
        shot(stem, Vector((0, 0, 0.85)), 3.6, 12, (560, 820))
        stems.append(stem)
    fm.sheet(stems, "hero_kit_weapons", cols=7)


def dragons():
    """The four heads close from the front and from the side, with Chelmsford's colours, then whole at the Look step's size."""
    stems = []
    for spin, tag in ((-30, "three"), (-90, "side"), (0, "front")):
        for head in hb.HEADS:
            t, col = start()
            floor(col)
            stand(t, col, hero("dragonborn", "broad", head, None, hb.DRAGON_TYPES["blue"], H[0], E[3], C[4], "heavy", "shortsword"), "d", spin=spin)
            stem = f"hero_kit_dragon_{tag}_{head}"
            shot(stem, hb.full("dragonborn", hb.head_point("dragonborn", "broad")) + Vector((0, 0, 0.02)), 1.5, 8, (460, 420))
            stems.append(stem)
    fm.sheet(stems, "hero_kit_dragon_heads", cols=4)
    stems = []
    looks = [("a", "blue", "broad", "heavy", "mace", "shield", C[4]), ("b", "red", "average", "medium", "greatsword", None, C[0]), ("c", "green", "broad", "light", "greataxe", None, C[2]), ("d", "white", "slim", "heavy", "longsword", "shield", C[1]), ("a", "black", "average", "none", "glaive", None, C[3])]
    for head, kind, build, tier, main, off, cloth in looks:
        t, col = start()
        floor(col)
        stand(t, col, hero("dragonborn", build, head, None, hb.DRAGON_TYPES[kind], H[0], E[3], cloth, tier, main, off), "d", spin=-28)
        stem = f"hero_kit_dragon_look_{kind}"
        shot(stem, Vector((0, 0, 0.85)), 3.2, 12, (560, 820))
        stems.append(stem)
    fm.sheet(stems, "hero_kit_dragon_look", cols=5)


def on_map():
    """On a real patch: plains and forest, with enemies beside them, at 58, 30 and 18 m from the game's camera."""
    hk.empty_scene()
    t = rp.load_templates(rp.latest("tiles", "tiles"))
    near = {(q, r) for q in range(-2, 3) for r in range(-2, 3) if abs(q + r) <= 2}
    rp.build_map(t, tiles={at: "plains" for at in near})
    kit = rp.load_templates(rp.latest(os.path.join("minis", "heroes"), "hero_kit"))
    col = hk.new_collection("line")
    for i, (name, desc) in enumerate(COMBOS):
        stand(kit, col, desc, name, at=(1.7 * ((i % 4) - 1.5), 1.2 - 2.2 * (i // 4), 0), spin=0)
    en = rp.load_templates(rp.latest(os.path.join("minis", "enemies"), "humanoid_minis"))
    rp.place(en, "enemy_bandit_melee", col, Vector((5.2, 0, 0)))
    rp.place(en, "enemy_bandit_elite", col, Vector((5.2, -1.6, 0)))
    for d in (58, 30, 18):
        shot(f"hero_kit_map_{d}m", Vector((0.4, 0, 0.6)), d, 50, (1688, 780))
    fm.sheet(["hero_kit_map_58m", "hero_kit_map_30m", "hero_kit_map_18m"], "hero_kit_map", cols=3)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["faces", "look", "map", "weapons", "dragons"]
    if "faces" in args:
        faces()
    if "look" in args:
        look()
    if "map" in args:
        on_map()
    if "weapons" in args:
        weapons()
    if "dragons" in args:
        dragons()
