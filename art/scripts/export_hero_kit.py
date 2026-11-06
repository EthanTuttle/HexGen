"""Writes the hero kit's placement table, art/export/heroes_placements.json, from build_hero_kit's layout. Run after building, with heroes.glb from the same kit:

/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/export_hero_kit.py [-- check]

Matrices are in the glb's Y-up frame, which is Godot's: 12 numbers, the basis's x, y and z columns, then the origin. Hand-off: art/handoff/hero_kit.md.
Since the weapon pose pass (kit v10) every pose moves the whole hero: the torso twists and sinks, the head turns, the legs are posed
parts, the arms are solved per pose. So each pose holds every matrix but the base's. `-- check` rebuilds random heroes from the
written table alone, by the hand-off's rules, and compares every piece name and matrix with the assembler's.
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Matrix  # noqa: E402

import build_hero_kit as hb  # noqa: E402
import hexkit as hk  # noqa: E402

Y_UP = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
PATH = os.path.join(hk.ART, "export", "heroes_placements.json")
SECOND = "dagger"  # any one-handed weapon held as the second takes the same matrix


def flat(m):
    g = Y_UP @ m @ Y_UP.inverted()
    return [round(g[r][c], 4) for c in range(4) for r in range(3)]


def desc(race, build, main, off=None, two=False, caster=False, tier="heavy", head="a", hair="short"):
    return dict(race=race, build=build, head=head, hair=hair, armour=tier, main=main, offhand=off, two=two, caster=caster, colours={})


# A pose's variants: the plain one, then shield and second weapon (one-handed weapons), both hands (versatile), casting (staff).
def variants(main):
    out = {"none": {}}
    if main in hb.ONE_HANDED:
        out.update({"shield": {"off": "shield"}, "second": {"off": SECOND}})
    if main in hb.TWO_GRIP:
        out["two"] = {"two": True}
    if main == "staff":
        out["cast"] = {"caster": True}
    return out


def pose_row(race, build, main, v):
    """Every matrix a hero needs in this pose, read off the assembler's own list (built in heavy armour, so the greaves are there)."""
    placed = hb.layout(desc(race, build, main, v.get("off"), v.get("two", False), v.get("caster", False)))
    grip = hb.grip_of(main, v.get("off"), v.get("two", False), v.get("caster", False))
    palms = hb.POSES[grip].get("palms", ())
    row = {"grip": grip, "legs": [], "arms": []}
    i = 1  # after the base
    while i < len(placed):
        name, m = placed[i]
        if name.startswith("hero_body_"):
            row["torso"] = flat(m)
        elif name.startswith("hero_armour_"):
            pass  # the torso's matrix
        elif name.startswith("hero_head_"):
            row["head"] = flat(m)
        elif name.startswith("hero_hair_"):
            row["hair"] = flat(m)
        elif name.startswith("hero_leg_upper_"):
            leg = {"upper": flat(m), "lower": flat(placed[i + 1][1])}
            i += 2
            if placed[i][0] == "hero_leg_greave":
                leg["greave"] = flat(placed[i][1])
                i += 1
            leg["boot"] = flat(placed[i][1])
            row["legs"].append(leg)
        elif name.startswith("hero_arm_upper_"):
            side = 1 if not row["arms"] else -1
            arm = {"upper": flat(m), "fore": flat(placed[i + 1][1]), "hand": flat(placed[i + 2][1]),
                   "hand_piece": "open_wraps" if placed[i + 2][0] == "hero_hand_open_wraps" else "palm" if side in palms else "fist"}
            i += 2
            if main in hb.FIST and i + 1 < len(placed) and placed[i + 1][0] == f"hero_{main}":
                arm["fist_weapon"] = flat(placed[i + 1][1])
                i += 1
            row["arms"].append(arm)
        elif name == f"hero_{main}" and "main" not in row and main not in hb.FIST:
            row["main"] = flat(m)
        else:
            row["offhand"] = flat(m)
        i += 1
    return row


def table():
    out = {"zones": hb.ZONES, "swatches": {k: (dict(v) if isinstance(v, dict) else list(v)) for k, v in hb.SWATCHES.items()}, "dragon_types": hb.DRAGON_TYPES,
           "grip_of": hb.GRIP_OF, "two_grip": hb.TWO_GRIP, "one_handed": list(hb.ONE_HANDED), "fist": list(hb.FIST), "hairless": list(hb.HAIRLESS),
           "hairstyles": list(hb.HAIRSTYLES), "heads": list(hb.HEADS), "builds": list(hb.BUILDS), "armour": list(hb.ARMOUR), "races": {}}
    for race in hb.RACES:
        out["races"][race] = {"height": hb.RACES[race]["k"], "builds": {}}
        for build in hb.BUILDS:
            out["races"][race]["builds"][build] = {"poses": {main: {k: pose_row(race, build, main, v) for k, v in variants(main).items()} for main in hb.GRIP_OF}}
    return out


def from_table(T, d):
    """A hero's pieces and matrices from the table alone, by the hand-off's rules (what Godot's assembler does)."""
    race, build, tier, main, off = d["race"], d["build"], d["armour"], d["main"], d.get("offhand")
    key = "cast" if main == "staff" and d.get("caster") and not off else "two" if d.get("two") and main in T["two_grip"] and not off else \
        "shield" if off == "shield" else "second" if off else "none"
    p = T["races"][race]["builds"][build]["poses"][main][key]
    golem = race == "golem"
    leg_kind = "golem" if golem else "scaled" if race == "dragonborn" else "cloth"
    kind = "golem" if golem else {"none": "bare", "light": "bare", "medium": "chain", "heavy": "plate"}[tier]
    fist = "golem" if golem else "gauntlet" if tier == "heavy" else "bare"
    out = [("hero_base", None), (f"hero_body_{race}_{build}", p["torso"])]
    if tier != "none":
        out.append((f"hero_armour_{tier}_{race}_{build}", p["torso"]))
    out.append((f"hero_head_{race}_{d['head']}", p["head"]))
    if race not in T["hairless"] and d.get("hair") and d["hair"] != "none":
        out.append((f"hero_hair_{d['hair']}", p["hair"]))
    for leg in p["legs"]:
        out += [(f"hero_leg_upper_{leg_kind}", leg["upper"]), (f"hero_leg_lower_{leg_kind}", leg["lower"])]
        if tier == "heavy" and not golem:
            out.append(("hero_leg_greave", leg["greave"]))
        out.append(("hero_boot_golem" if golem else "hero_boot_leather", leg["boot"]))
    for arm in p["arms"]:
        hand = "hero_hand_open_wraps" if arm["hand_piece"] == "open_wraps" else f"hero_hand_{fist}"
        out += [(f"hero_arm_upper_{kind}", arm["upper"]), (f"hero_arm_fore_{kind}", arm["fore"]), (hand, arm["hand"])]
        if "fist_weapon" in arm:
            out.append((f"hero_{main}", arm["fist_weapon"]))
    if "main" in p:
        out.append((f"hero_{main}", p["main"]))
    if off:
        out.append(("hero_shield" if off == "shield" else f"hero_{off}", p["offhand"]))
    return out


def check(n=400):
    with open(PATH) as f:
        T = json.load(f)
    rng = random.Random(7)
    bad = 0
    for _ in range(n):
        race, build, main = rng.choice(list(hb.RACES)), rng.choice(list(hb.BUILDS)), rng.choice(list(hb.GRIP_OF))
        off = rng.choice([None, "shield", rng.choice(hb.ONE_HANDED)]) if main in hb.ONE_HANDED else None
        two = main in hb.TWO_GRIP and not off and rng.random() < 0.5
        caster = main == "staff" and not off and rng.random() < 0.5
        d = desc(race, build, main, off, two, caster, rng.choice(["none", *hb.ARMOUR]), rng.choice(hb.HEADS), rng.choice([*hb.HAIRSTYLES, "none"]))
        want = [(nm, None if nm == "hero_base" else flat(m)) for nm, m in hb.layout(d)]
        got = from_table(T, d)
        names_ok = [a for a, _ in want] == [a for a, _ in got]
        mats_ok = names_ok and all(a is None or max(abs(x - y) for x, y in zip(a, b)) < 1e-3 for (_, a), (_, b) in zip(want, got))
        if not mats_ok:
            bad += 1
            if bad < 4:
                print("MISMATCH", d, [a for a, _ in want], [a for a, _ in got])
    print("CHECKED", n, "heroes,", bad, "mismatched")


if __name__ == "__main__":
    if "check" in sys.argv:
        check()
        sys.exit()
    with open(PATH, "w") as f:
        json.dump(table(), f, separators=(",", ":"))
    print("WROTE", PATH, os.path.getsize(PATH))
