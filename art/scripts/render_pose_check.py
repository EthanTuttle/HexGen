"""Pose check: every row of design/07 → Pose library against the hero kit as it renders now, with the offhand variants once.
Renders only; no mesh changes.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_pose_check.py
Uses the latest hero_kit. Each panel is one hero (human, average build, light armour, default colours) from the front, three-
quarter and side, over a strip with 07's pose and the kit's grip; rows the kit has no pose for get an empty panel. Three panels
to a sheet: art/preview/pose_check_<n>_vN.png.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_hero_kit as hb  # noqa: E402
import hexkit as hk  # noqa: E402
import render_hero_kit as rh  # noqa: E402
import render_preview as rp  # noqa: E402

S = hb.SWATCHES
W, H_SHOT, H_TEXT = 1500, 900, 230
# Hands per grip, as art/handoff/hero_kit.md's grip table gives them.
HANDS = {"forward": "one hand", "raised": "one hand", "fencer": "one hand", "slash": "one hand", "reverse": "one hand", "point": "one hand",
         "planted": "two hands", "shoulder": "two hands", "sweep": "two hands", "upright": "one hand", "across": "two hands", "bow": "two hands",
         "aim": "two hands", "guard": "fists", "haymaker": "fists", "stance": "fists"}

# 07's rows in its order: (weapon, 07's grip, 07's pose, the kit's weapon or None where it has no pose, offhand).
ROWS = [
    ("Greatsword", "two-handed", "Point planted on the base, hands on the pommel", "greatsword", None),
    ("Longsword", "one-handed", "Point forward, aimed at the foe", "longsword", None),
    ("Longsword", "two-handed", "High guard, blade raised above the head", None, None),
    ("Shortsword", "one-handed", "Backhand slash ready", "shortsword", None),
    ("Rapier", "one-handed", "En garde, fencer's stance", "rapier", None),
    ("Scimitar", "one-handed", "Mid-spin", "scimitar", None),
    ("Dagger", "one-handed", "Reverse grip, low crouch", "dagger", None),
    ("Battleaxe", "one-handed", "Held low and loose", "battleaxe", None),
    ("Battleaxe", "two-handed", "Executioner's raise, axe lifted overhead", None, None),
    ("Greataxe", "two-handed", "Carried on the shoulder", "greataxe", None),
    ("Mace", "one-handed", "Raised high (Chelmsford, minis v2a)", "mace", None),
    ("Warhammer", "two-handed", "Head resting on the ground, a resting pose rather than a swing", "warhammer", None),
    ("Spear", "one-handed", "Javelin wind-up", "spear", None),
    ("Spear", "two-handed", "Braced pike, point forward", None, None),
    ("Halberd", "two-handed", "Upright at attention", "halberd", None),
    ("Glaive", "two-handed", "Mid-sweep", "glaive", None),
    ("Staff", "one-handed", "Staff planted, free hand raised as if casting", "staff", "shield"),
    ("Staff", "two-handed", "Quarterstaff guard, held across the body", "staff", None),
    ("Wand", "one-handed", "Arm extended, wand pointed at the foe", "wand", None),
    ("Shortbow", "two-handed", "Nocking quickly, arrow half-drawn", "shortbow", None),
    ("Longbow", "two-handed", "Full draw, steady aim", "longbow", None),
    ("Crossbow", "two-handed", "Stock at the shoulder, aiming", "crossbow", None),
    ("Gauntlets", "both hands (fist)", "High guard, fists at the face", "gauntlets", None),
    ("Brass knuckles", "both hands (fist)", "Haymaker wind-up, one fist pulled back", "brass_knuckles", None),
    ("Wraps", "both hands (fist)", "Martial-arts stance, palm forward, other hand at the hip", "wraps", None),
    ("Offhand: shield", "on a longsword", "Raised in front, across the chest (as in minis v2a)", "longsword", "shield"),
    ("Offhand: second weapon", "a dagger, on a longsword", "Held back, ready, behind the main weapon", "longsword", "dagger"),
]


def kit_text(weapon, offhand):
    if weapon is None:
        return "Kit: no pose for this grip (the one-handed pose is used)"
    grip = "upright" if weapon == "staff" and offhand else hb.GRIP_OF[weapon]
    hands = HANDS[grip]
    off = {"shield": ", shield", "dagger": ", second weapon (dagger)", None: ", offhand empty" if weapon in hb.ONE_HANDED and grip != "across" else ""}[offhand]
    note = " (the staff takes 'upright' only with an offhand; empty, it's 'across')" if weapon == "staff" and offhand else ""
    return f"Kit: grip '{grip}', {hands}{off}{note}"


def shot(weapon, offhand, stem):
    hk.empty_scene()
    t = rp.load_templates(rp.latest(os.path.join("minis", "heroes"), "hero_kit"))
    for o in t.values():
        o.hide_render = True
    col = hk.new_collection("line")
    hk.PALETTE["hero_ground"] = rh.GROUND
    rh.floor(col)
    if weapon:
        desc = rh.hero("human", "average", "a", "short", S["skin"]["human"][1], S["hair"][1], S["eyes"][1], S["cloth"][1], "light", weapon, offhand)
        for x, spin in ((-1.35, 0), (0, -45), (1.35, -90)):
            rh.stand(t, col, desc, f"h{spin}", at=(x, 0, 0), spin=spin)
    rh.shot(stem, Vector((0, 0, 0.9)), 6.3, 10, (W, H_SHOT))  # tall enough for weapons held overhead


def text_strip(lines, stem):
    """Lines of text on white, rendered flat: the panel's caption."""
    hk.empty_scene()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("white")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    scene.world = world
    ink = bpy.data.materials.new("ink")
    ink.use_nodes = True
    nodes = ink.node_tree.nodes
    nodes.clear()
    em_ = nodes.new("ShaderNodeEmission")
    em_.inputs[0].default_value = (0.08, 0.08, 0.1, 1)
    out = nodes.new("ShaderNodeOutputMaterial")
    ink.node_tree.links.new(em_.outputs[0], out.inputs[0])
    width = 15.0
    height = width * H_TEXT / W
    y = height / 2 - 0.55
    for k, (text, size) in enumerate(lines):
        curve = bpy.data.curves.new(f"line{k}", "FONT")
        curve.body, curve.size = text, size
        ob = bpy.data.objects.new(f"line{k}", curve)
        ob.location = (-width / 2 + 0.3, y, 0)
        ob.data.materials.append(ink)
        scene.collection.objects.link(ob)
        y -= size * 1.35
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type, cam_data.ortho_scale = "ORTHO", width
    cam = bpy.data.objects.new("cam", cam_data)
    cam.location = (0, 0, 10)
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = W, H_TEXT
    rp.render(stem)


def latest(stem):
    path = os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")
    im = bpy.data.images.load(path)
    w, h = im.size
    return np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)


def sheet(stems, n, gap=16):
    """Panels stacked top to bottom, each its shot over its caption."""
    blocks = []
    for stem in stems:
        blocks += [latest(stem), latest(stem + "_text")]
        blocks.append(None)
    blocks = blocks[:-1]
    h = sum(b.shape[0] if b is not None else gap for b in blocks)
    pixels = np.ones((h, W, 4), dtype=np.float32)
    y = h
    for b in blocks:
        if b is None:
            pixels[y - gap:y] = (0.75, 0.75, 0.75, 1)
            y -= gap
            continue
        pixels[y - b.shape[0]:y] = b
        y -= b.shape[0]
    out = f"pose_check_{n}"
    im = bpy.data.images.new(out, W, h, alpha=True)
    im.pixels[:] = pixels.ravel().tolist()
    im.filepath_raw = os.path.join(hk.ART, "preview", f"{out}_v{rp.next_n(out)}.png")
    im.file_format = "PNG"
    im.save()
    print("SHEET", im.filepath_raw)


if __name__ == "__main__":
    stems = []
    for i, (name, grip, pose, weapon, offhand) in enumerate(ROWS):
        stem = f"pose_check_panel_{i + 1:02d}"
        shot(weapon, offhand, stem)
        text_strip([(f"{i + 1}. {name}, {grip}" + ("   (NOT IN THE KIT)" if weapon is None else ""), 0.46),
                    (f"07: {pose}", 0.36), (kit_text(weapon, offhand), 0.36)], stem + "_text")
        stems.append(stem)
    for n in range(math.ceil(len(stems) / 3)):
        sheet(stems[n * 3:n * 3 + 3], n + 1)
