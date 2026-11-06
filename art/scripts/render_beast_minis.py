"""Renders an ally beast for review: front and turned beside a hero mini and the enemy wolf, its colour options, and the three at
the combat camera's height and distance.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_beast_minis.py [-- wolf bear panther hawk | solo:wolf ...]
faces:<beast>:<v>:<v> puts two solo face views side by side. solo:<beast> renders beast_<beast>_solo_vN.png: the beast alone, large, from four sides and the combat camera.
Options built beside a beast (beast_wolf_band) join the combat-camera row.
Uses the latest beast_minis, hero_kit and enemy_minis. Writes art/preview/beast_<beast>_*_vN.png and the sheet beast_<beast>_vN.png.
"""
import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
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
BESIDE = {"wolf": "enemy_wolf", "bear": "beast_wolf", "panther": "beast_wolf", "hawk": "beast_wolf"}


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


# The piece each beast is, where the approved one isn't plain beast_<name>.
PIECE = {}


def solo(beast_name):
    """The beast alone in its default coat, large: front, three-quarter, side and back, close from the combat camera, and its face."""
    piece = PIECE.get(beast_name, f"beast_{beast_name}")
    stems = []
    views = ((0, "front", 12), (-35, "three", 12), (-90, "side", 12), (180, "back", 12), (-30, "combat", 50), (-25, "face", 6))
    for spin, tag, pitch in views:
        t, col = start()
        ob, n = beast(t, piece, looks(beast_name)[0], beast_name, col, (0, 0, 0), spin)
        pts = [ob.matrix_world @ v.co for v in ob.data.vertices if (ob.matrix_world @ v.co).z > 0.12]
        top = max(q.z for q in pts)
        target, distance = Vector((0, 0, top * 0.48)), {"side": 2.3, "combat": 2.2}.get(tag, 2.0)
        if tag == "face":  # the head: the points furthest forward in the beast's own frame, in its top quarter
            high = [q for q in pts if q.z > top * 0.72] or pts
            ahead = sorted(high, key=lambda q: (ob.matrix_world.inverted() @ q).y)[:max(6, len(high) // 4)]
            target, distance = sum(ahead, Vector()) / len(ahead), 0.75
        stem = f"beast_{beast_name}_solo_{tag}"
        rh.shot(stem, target, distance, pitch, (900, 900))
        stems.append(stem)
    print("SOLOTRIS", beast_name, n)
    sheet_full(stems, f"beast_{beast_name}_solo", cols=3)


def sheet_full(stems, out, cols):
    """The renders side by side at full size (fm.sheet halves them)."""
    tiles = []
    for stem in stems:
        im = bpy.data.images.load(max(glob.glob(os.path.join(hk.ART, "preview", f"{stem}_v*.png")), key=os.path.getmtime))
        w, h = im.size
        tiles.append(np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4))
    h, w, _ = tiles[0].shape
    rows = (len(tiles) + cols - 1) // cols
    pixels = np.ones((rows * h, cols * w, 4), dtype=np.float32)
    for i, tile in enumerate(tiles):
        y, x = (rows - 1 - i // cols) * h, (i % cols) * w
        pixels[y:y + h, x:x + w] = tile
    im = bpy.data.images.new(out, cols * w, rows * h, alpha=True)
    im.pixels[:] = pixels.ravel().tolist()
    im.filepath_raw = os.path.join(hk.ART, "preview", f"{out}_v{rp.next_n(out)}.png")
    im.file_format = "PNG"
    im.save()
    print("SHEET", im.filepath_raw)


def face_compare(beast_name, before, after):
    """The face close-up of two solo versions side by side: beast_<beast>_face_before_after_vN.png."""
    tiles = []
    for v in (before, after):
        im = bpy.data.images.load(os.path.join(hk.ART, "preview", f"beast_{beast_name}_solo_face_v{v}.png"))
        w, h = im.size
        tiles.append(np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4))
    pixels = np.ones((tiles[0].shape[0], tiles[0].shape[1] * 2 + 12, 4), dtype=np.float32)
    pixels[:, :tiles[0].shape[1]] = tiles[0]
    pixels[:, tiles[0].shape[1] + 12:] = tiles[1]
    out = f"beast_{beast_name}_face_before_after"
    im = bpy.data.images.new(out, pixels.shape[1], pixels.shape[0], alpha=True)
    im.pixels[:] = pixels.ravel().tolist()
    im.filepath_raw = os.path.join(hk.ART, "preview", f"{out}_v{rp.next_n(out)}.png")
    im.file_format = "PNG"
    im.save()
    print("SHEET", im.filepath_raw)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["wolf"]
    for name in args:
        if name.startswith("faces:"):  # faces:<beast>:<before>:<after>
            face_compare(*name.split(":")[1:2], *map(int, name.split(":")[2:]))
        elif name.startswith("solo:"):
            solo(name[5:])
        else:
            render(name)
