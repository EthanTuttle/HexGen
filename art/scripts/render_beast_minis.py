"""Renders an ally beast for review: front and turned beside a hero mini and the enemy wolf, its colour options, and the three at
the combat camera's height and distance.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_beast_minis.py [-- wolf bear panther hawk]
Options built beside a beast (beast_wolf_band) join the combat-camera row.
Uses the latest beast_minis, hero_kit and enemy_minis. Writes art/preview/beast_<beast>_*_vN.png and the sheet beast_<beast>_vN.png.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build_beast_minis as bb  # noqa: E402
import build_hero_kit as hb  # noqa: E402
import hexkit as hk  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_hero_kit as rh  # noqa: E402
import render_preview as rp  # noqa: E402

S = hb.SWATCHES
# The Companion ranger beside it: an elf with a shortbow, as on the hero sheets.
RANGER = rh.hero("elf", "slim", "c", "long", S["skin"]["elf"][1], S["hair"][3], S["eyes"][0], S["cloth"][2], "light", "shortbow")


def looks(beast):
    """Six colour options: each coat with its markings, the hero kit's cloth in turn, and the beast eyes in turn."""
    sw = bb.BEAST_SWATCHES[beast]
    return [dict(skin=sw["coat"][i], hair=sw["markings"][i], eyes=bb.BEAST_EYES[i % 4], cloth=S["cloth"][i]) for i in range(6)]


def start():
    hk.empty_scene()
    t = rp.load_templates(rp.latest(os.path.join("minis", "heroes"), "hero_kit"))
    t.update(rp.load_templates(rp.latest(os.path.join("minis", "heroes"), "beast_minis")))
    t.update(rp.load_templates(rp.latest(os.path.join("minis", "enemies"), "enemy_minis")))
    for o in t.values():
        o.hide_render = True
    col = hk.new_collection("line")
    hk.PALETTE["hero_ground"] = rh.GROUND
    rh.floor(col)
    return t, col


def beast(t, piece, colours, name, col, at, spin):
    """One piece with its marks turned into colours, through the hero assembler."""
    layout, hb.layout = hb.layout, lambda desc: [(piece, Matrix.Identity(4))]
    try:
        ob, n = hb.assemble(t, {"colours": colours}, name, col)
    finally:
        hb.layout = layout
    ob.location, ob.rotation_euler.z = Vector(at), math.radians(spin)
    return ob, n


def enemy(t, piece, col, at, spin):
    ob = t[piece].copy()
    ob.hide_render = False
    col.objects.link(ob)
    ob.location, ob.rotation_euler.z = Vector(at), math.radians(spin)
    return ob


# What each beast stands beside: its enemy kind where there is one, else the approved ally wolf.
BESIDE = {"wolf": "enemy_wolf", "bear": "beast_wolf_band", "panther": "beast_wolf_band", "hawk": "beast_wolf_band"}


def other(t, beast_name, col, at, spin):
    piece = BESIDE[beast_name]
    if piece.startswith("enemy_"):
        enemy(t, piece, col, at, spin)
    else:
        beast(t, piece, looks(piece.split("_")[1])[0], piece, col, at, spin)


def line_up(beast_name, colours, spin):
    t, col = start()
    ranger, _ = rh.stand(t, col, RANGER, "ranger", at=(-1.15, 0, 0), spin=spin)
    _, n = beast(t, f"beast_{beast_name}", colours, beast_name, col, (0, 0, 0), spin)
    other(t, beast_name, col, (1.15, 0, 0), spin)
    return n


def render(beast_name):
    stems = []
    first = looks(beast_name)[0]
    for spin, tag in ((-28, "front"), (152, "back"), (-90, "side")):
        n = line_up(beast_name, first, spin)
        stem = f"beast_{beast_name}_{tag}"
        rh.shot(stem, Vector((0, 0, 0.5)), 5.6, 12, (1500, 760))
        stems.append(stem)
    print("BEASTTRIS", beast_name, n)
    # Colour options, front three-quarter.
    t, col = start()
    for i, c in enumerate(looks(beast_name)):
        beast(t, f"beast_{beast_name}", c, f"{beast_name}_{i}", col, (1.0 * (i - 2.5), 0, 0), -28)
    stem = f"beast_{beast_name}_colours"
    rh.shot(stem, Vector((0, 0, 0.4)), 9.0, 12, (1500, 760))
    stems.append(stem)
    fm.sheet(stems, f"beast_{beast_name}", cols=2)
    # The game's combat camera: about 50 degrees down, at 18 and 30 m. Options (beast_<name>_<option>) stand between it and the foe.
    t, col = start()
    options = sorted(k for k in t if k.startswith(f"beast_{beast_name}_") and k != BESIDE[beast_name])
    row = ["ranger", f"beast_{beast_name}"] + options + ["other"]
    for i, piece in enumerate(row):
        x = 1.15 * (i - (len(row) - 1) / 2)
        if piece == "ranger":
            rh.stand(t, col, RANGER, "ranger", at=(x, 0, 0), spin=0)
        elif piece == "other":
            other(t, beast_name, col, (x, 0, 0), 0)
        else:
            beast(t, piece, first, piece, col, (x, 0, 0), 0)
    print("COMBATROW", row)
    # Close, at the same angle, for judging what reads: facing the camera, then turned 60 degrees as after a move.
    rh.shot(f"beast_{beast_name}_combat_close", Vector((0, 0, 0.4)), 8, 50, (1500, 600))
    for o in col.objects:
        if o.type == "MESH" and o.name != "ground":
            o.rotation_euler.z = math.radians(60)
    rh.shot(f"beast_{beast_name}_combat_close_turned", Vector((0, 0, 0.4)), 8, 50, (1500, 600))
    for d in (18, 30):
        rh.shot(f"beast_{beast_name}_combat_{d}m", Vector((0, 0, 0.4)), d, 50, (1500, 700))


if __name__ == "__main__":
    for name in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["wolf"]):
        render(name)
