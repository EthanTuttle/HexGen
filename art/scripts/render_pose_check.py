"""Pose check: every row of design/07 → Pose library against the hero kit as it renders now, with the offhand variants once.
Renders only; no mesh changes.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_pose_check.py
Uses the latest hero_kit. Each panel is one hero (human, average build, light armour, default colours) from the front, three-
quarter, side, above-behind and low, over a strip with 07's pose, the kit's grip and what this pass changed. Three panels to a
sheet: art/preview/pose_check_<n>_vN.png. Pass row numbers after -- to render only those panels (no sheets); -- 0 remakes the sheets only.
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
W, H_SHOT, H_TEXT = 2800, 900, 330
# Hands per grip.
HANDS = {"backhand": "one hand", "low": "one hand", "high": "two hands", "executioner": "two hands", "pike": "two hands", "cast": "one hand, the other raised","forward": "one hand", "raised": "one hand", "fencer": "one hand", "slash": "one hand", "reverse": "one hand", "point": "one hand",
         "planted": "two hands", "shoulder": "two hands", "sweep": "two hands", "upright": "one hand", "across": "two hands", "bow": "two hands",
         "aim": "two hands", "guard": "fists", "haymaker": "fists", "stance": "fists"}

# 07's rows in its order: (weapon, 07's grip, 07's pose, the kit's weapon or None, offhand, desc extras, what changed in this pass).
ALL = "legs and elbows posed"
ROWS = [
    ("Greatsword", "two-handed", "Point planted on the base, hands on the pommel", "greatsword", None, {}, f"kept; {ALL}"),
    ("Longsword", "one-handed", "Point forward, aimed at the foe", "longsword", None, {}, "CHANGED (1): chest high, angled up and across"),
    ("Longsword", "two-handed", "High guard, blade raised above the head", "longsword", None, {"two": True}, "NEW (2): two-handed high guard"),
    ("Shortsword", "one-handed", "Backhand slash ready", "shortsword", None, {}, "CHANGED (3): drawn back over the off shoulder"),
    ("Rapier", "one-handed", "En garde, fencer's stance", "rapier", None, {}, f"kept, with a lunge; {ALL}"),
    ("Scimitar", "one-handed", "Mid-spin", "scimitar", None, {}, "CHANGED (4): torso twisted, blade sweeping out, clear of the hair"),
    ("Dagger", "one-handed", "Reverse grip, low crouch", "dagger", None, {}, "CHANGED (5): low crouch, blade clear of the thigh"),
    ("Battleaxe", "one-handed", "Held low and loose", "battleaxe", None, {}, "CHANGED (6): low at the side, head forward"),
    ("Battleaxe", "two-handed", "Executioner's raise, axe lifted overhead", "battleaxe", None, {"two": True}, "NEW (7): executioner's raise"),
    ("Greataxe", "two-handed", "Carried on the shoulder", "greataxe", None, {}, "CHANGED (8): haft on the shoulder, one hand up, one low"),
    ("Mace", "one-handed", "Raised high (Chelmsford, minis v2a)", "mace", None, {}, f"kept; {ALL}"),
    ("Warhammer", "two-handed", "Head resting on the ground, a resting pose rather than a swing", "warhammer", None, {}, "CHANGED (9): a bigger, heavier head"),
    ("Spear", "one-handed", "Upright at attention, like the halberd", "spear", None, {}, f"kept; {ALL}"),
    ("Spear", "two-handed", "Braced pike, point forward", "spear", None, {"two": True}, "NEW (10): braced pike, level, into the next cell"),
    ("Halberd", "two-handed", "Upright at attention", "halberd", None, {}, f"kept; {ALL}"),
    ("Glaive", "two-handed", "Mid-sweep", "glaive", None, {}, "CHANGED (11): torso twisted, swung low and wide"),
    ("Staff", "caster, hand empty", "Staff planted, free hand raised as if casting", "staff", None, {"caster": True}, "NEW (12): casting pose, palm out"),
    ("Staff", "two-handed", "Quarterstaff guard, held across the body", "staff", None, {}, f"kept (martials); {ALL}"),
    ("Wand", "one-handed", "Arm extended, wand pointed at the foe", "wand", None, {}, "CHANGED (13): angled forward and out"),
    ("Shortbow", "two-handed", "Drawn to the cheek, arrow nocked, body side-on; shared with the longbow", "shortbow", None, {}, "CHANGED (14): drawn, string to the hand, arrow nocked, side-on"),
    ("Longbow", "two-handed", "The same drawn pose as the shortbow", "longbow", None, {}, "CHANGED (14): the same drawn pose"),
    ("Crossbow", "two-handed", "Stock at the shoulder, aiming", "crossbow", None, {}, f"kept; {ALL}"),
    ("Gauntlets", "both hands (fist)", "High guard, fists at the face", "gauntlets", None, {}, "CHANGED (15): fists at the chin, below the eyes"),
    ("Brass knuckles", "both hands (fist)", "Haymaker wind-up, one fist pulled back", "brass_knuckles", None, {}, "CHANGED (16): torso twisted, elbow behind the fist"),
    ("Wraps", "both hands (fist)", "Martial-arts stance, palm forward, other hand at the hip", "wraps", None, {}, "CHANGED (17): forward palm open, hip hand a fist"),
    ("Offhand: shield", "on a longsword", "Held low at the side, facing forward", "longsword", "shield", {}, f"kept; {ALL}"),
    ("Offhand: second weapon", "a dagger, on a longsword", "Held back, ready, behind the main weapon", "longsword", "dagger", {}, "CHANGED (18): the elbow bends naturally"),
]
# Five views: front, three-quarter, side, from above and behind, and from low in front.
VIEWS = ((0, 10, 3.4), (-45, 10, 3.4), (-90, 10, 3.4), (150, 45, 3.5), (-30, 1, 3.1))  # far enough for weapons held overhead
TILE = 560


def kit_text(weapon, offhand, extra):
    grip = hb.grip_of(weapon, offhand, extra.get("two", False), extra.get("caster", False))
    off = {"shield": ", shield", "dagger": ", second weapon (dagger)", None: ""}[offhand]
    return f"Kit: grip '{grip}', {HANDS.get(grip, 'two hands')}{off}"


def shot(weapon, offhand, extra, stem):
    """The hero alone, rendered from each of VIEWS, side by side: stem_vN.png."""
    tiles = []
    for k, (spin, pitch, dist) in enumerate(VIEWS):
        hk.empty_scene()
        t = rp.load_templates(rp.latest(os.path.join("minis", "heroes"), "hero_kit"))
        for o in t.values():
            o.hide_render = True
        col = hk.new_collection("line")
        hk.PALETTE["hero_ground"] = rh.GROUND
        rh.floor(col)
        desc = rh.hero("human", "average", "a", "short", S["skin"]["human"][1], S["hair"][1], S["eyes"][1], S["cloth"][1], "light", weapon, offhand)
        desc.update(extra)
        rh.stand(t, col, desc, "h", at=(0, 0, 0), spin=spin)
        view = f"{stem}_view{k}"
        rh.shot(view, Vector((0, 0, 0.78 if pitch < 30 else 0.6)), dist, pitch, (TILE, H_SHOT))
        tiles.append(latest(view))
    pixels = np.ones((H_SHOT, W, 4), dtype=np.float32)
    for k, tile in enumerate(tiles):
        pixels[:, k * TILE:(k + 1) * TILE] = tile
    im = bpy.data.images.new(stem, W, H_SHOT, alpha=True)
    im.pixels[:] = pixels.ravel().tolist()
    im.filepath_raw = os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem)}.png")
    im.file_format = "PNG"
    im.save()


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
    width = 28.0
    height = width * H_TEXT / W
    y = height / 2 - 0.75
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
    only = [int(a) for a in sys.argv[sys.argv.index("--") + 1:]] if "--" in sys.argv else None
    stems = []
    for i, (name, grip, pose, weapon, offhand, extra, change) in enumerate(ROWS):
        stem = f"pose_check_panel_{i + 1:02d}"
        stems.append(stem)
        if only and i + 1 not in only:
            continue
        shot(weapon, offhand, extra, stem)
        text_strip([(f"{i + 1}. {name}, {grip}", 0.62), (f"07: {pose}", 0.5), (kit_text(weapon, offhand, extra), 0.5), (change, 0.5)], stem + "_text")
    if not only or only == [0]:  # -- 0 remakes the sheets from the newest panels
        for n in range(math.ceil(len(stems) / 3)):
            sheet(stems[n * 3:n * 3 + 3], n + 1)
