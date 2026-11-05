"""Writes the hero kit's placement table, art/export/heroes_placements.json, from build_hero_kit's layout. Run after building, with heroes.glb from the same kit:

/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/export_hero_kit.py

Matrices are in the glb's Y-up frame, which is Godot's: 12 numbers, the basis's x, y and z columns, then the origin. Hand-off: art/handoff/hero_kit.md.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Matrix  # noqa: E402

import build_hero_kit as hb  # noqa: E402
import hexkit as hk  # noqa: E402

Y_UP = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))


def flat(m):
    g = Y_UP @ m @ Y_UP.inverted()
    return [round(g[r][c], 4) for c in range(4) for r in range(3)]


def desc(race, build, main, off, head="a", hair="short", tier="light"):
    return dict(race=race, build=build, head=head, hair=hair, armour=tier, main=main, offhand=off, colours={})


def rows(race, build, main, off):
    """The placements a weapon and offhand need: each arm's upper, fore and hand, then what's held."""
    placed = hb.layout(desc(race, build, main, off))
    arms = [m for name, m in placed if name.startswith(("hero_arm_upper_", "hero_arm_fore_", "hero_hand_"))]
    held = [(n, m) for n, m in placed if not n.startswith(("hero_base", "hero_body", "hero_armour", "hero_head", "hero_hair", "hero_arm_", "hero_hand_"))]
    if main in hb.FIST:  # the same piece on each hand: right, then left
        return {"right": [flat(m) for m in arms[:3]], "left": [flat(m) for m in arms[3:6]], "fists": [flat(m) for _, m in held]}
    out = {"right": [flat(m) for m in arms[:3]], "left": [flat(m) for m in arms[3:6]], "main": flat(held[0][1])}
    if off:
        out["offhand"] = flat(held[1][1])
    return out


def table():
    out = {"zones": hb.ZONES, "swatches": {k: (dict(v) if isinstance(v, dict) else list(v)) for k, v in hb.SWATCHES.items()}, "dragon_types": hb.DRAGON_TYPES,
           "grip_of": hb.GRIP_OF, "one_handed": list(hb.ONE_HANDED), "fist": list(hb.FIST), "hairless": list(hb.HAIRLESS), "hairstyles": list(hb.HAIRSTYLES), "heads": list(hb.HEADS), "builds": list(hb.BUILDS), "armour": list(hb.ARMOUR), "races": {}}
    for race in hb.RACES:
        out["races"][race] = {"height": hb.RACES[race]["k"], "builds": {}}
        for build in hb.BUILDS:
            base = hb.layout(desc(race, build, "longsword", None))
            row = {"head": flat(next(m for n, m in base if n.startswith("hero_head_"))), "poses": {}}
            if race not in hb.HAIRLESS:
                row["hair"] = flat(next(m for n, m in base if n.startswith("hero_hair_")))
            for main in hb.GRIP_OF:
                offs = {"none": None}
                if main in hb.ONE_HANDED:
                    offs.update({"shield": "shield", "second": "shortsword"})
                row["poses"][main] = {k: rows(race, build, main, o) for k, o in offs.items()}
            out["races"][race]["builds"][build] = row
    return out


if __name__ == "__main__":
    path = os.path.join(hk.ART, "export", "heroes_placements.json")
    with open(path, "w") as f:
        json.dump(table(), f, separators=(",", ":"))
    print("WROTE", path, os.path.getsize(path))
