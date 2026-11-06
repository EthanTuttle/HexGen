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
from mathutils import Matrix, Vector  # noqa: E402

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
    ("Greatsword", "two-handed", "Point planted on the base, hands on the pommel", "greatsword", None, {}, "ROUND 3: turned so the edge faces forward"),
    ("Longsword", "one-handed", "Point forward, aimed at the foe", "longsword", None, {}, "ROUND 3 (1): chest high, the point forward at the foe"),
    ("Longsword", "two-handed", "High guard, blade raised above the head", "longsword", None, {"two": True}, "ROUND 3 (2): the edge forward, not the flat"),
    ("Shortsword", "one-handed", "Backhand slash ready", "shortsword", None, {}, "ROUND 3 (3): laid back over the off shoulder, pointing behind, edge out"),
    ("Rapier", "one-handed", "En garde, fencer's stance", "rapier", None, {}, "ROUND 3 (4): the back arm out, the forearm leaning forward"),
    ("Scimitar", "one-handed", "Mid-spin", "scimitar", None, {}, "ROUND 3 (5): the old shortsword pose, curved edge forward"),
    ("Dagger", "one-handed", "Reverse grip, low crouch", "dagger", None, {}, "ROUND 4 (1): the blade angled about 45 degrees out from the body"),
    ("Battleaxe", "one-handed", "Held low and loose", "battleaxe", None, {}, "ROUND 4 (2): same body; the head up, the hand a third down the haft, edge forward"),
    ("Battleaxe", "two-handed", "Executioner's raise, axe lifted overhead", "battleaxe", None, {"two": True}, "ROUND 3 (7): drawn back behind the head, edge forward"),
    ("Greataxe", "two-handed", "Carried on the shoulder", "greataxe", None, {}, "CHANGED (8): haft on the shoulder, one hand up, one low"),
    ("Mace", "one-handed", "Raised high (Chelmsford, minis v2a)", "mace", None, {}, f"kept; {ALL}"),
    ("Warhammer", "two-handed", "Head resting on the ground, a resting pose rather than a swing", "warhammer", None, {}, "CHANGED (9): a bigger, heavier head"),
    ("Spear", "one-handed", "Upright at attention, like the halberd", "spear", None, {}, f"kept; {ALL}"),
    ("Spear", "two-handed", "Braced pike, point forward", "spear", None, {"two": True}, "NEW (10): braced pike, level, into the next cell"),
    ("Halberd", "two-handed", "Upright at attention", "halberd", None, {}, f"kept; {ALL}"),
    ("Glaive", "two-handed", "Mid-sweep", "glaive", None, {}, "ROUND 5: the front hand back on the haft below the socket, its arm bent; sweep kept"),
    ("Staff", "caster, hand empty", "Staff planted, free hand raised as if casting", "staff", None, {"caster": True}, "NEW (12): casting pose, palm out"),
    ("Staff", "two-handed", "Quarterstaff guard, held across the body", "staff", None, {}, f"kept (martials); {ALL}"),
    ("Wand", "one-handed", "Arm extended, wand pointed at the foe", "wand", None, {}, "CHANGED (13): angled forward and out"),
    ("Shortbow", "two-handed", "Drawn to the cheek, arrow nocked, body side-on; shared with the longbow", "shortbow", None, {}, "ROUND 4 (3): the drawing forearm straight from the elbow along the arrow, hand at the jaw"),
    ("Longbow", "two-handed", "The same drawn pose as the shortbow", "longbow", None, {}, "ROUND 4 (3): the same fix"),
    ("Crossbow", "two-handed", "Stock at the shoulder, aiming", "crossbow", None, {}, f"kept; {ALL}"),
    ("Gauntlets", "both hands (fist)", "High guard, fists at the face", "gauntlets", None, {}, "CHANGED (15): fists at the chin, below the eyes"),
    ("Brass knuckles", "both hands (fist)", "Haymaker wind-up, one fist pulled back", "brass_knuckles", None, {}, "ROUND 5: the rear elbow dropped behind and below the fist, cocked punch and twist kept"),
    ("Wraps", "both hands (fist)", "Martial-arts stance, palm forward, other hand at the hip", "wraps", None, {}, "ROUND 5: a new open hand, wrapped palm and wrist, bare fingers and thumb"),
    ("Offhand: shield", "on a longsword", "Held low at the side, facing forward", "longsword", "shield", {}, "ROUND 3: the longsword's new pose"),
    ("Offhand: second weapon", "a dagger, on a longsword", "Held back, ready, behind the main weapon", "longsword", "dagger", {}, "ROUND 3: the longsword's new pose, the dagger edge forward"),
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


def sheet(stems, n, gap=16, out="pose_check"):
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
    out = f"{out}_{n}"
    im = bpy.data.images.new(out, W, h, alpha=True)
    im.pixels[:] = pixels.ravel().tolist()
    im.filepath_raw = os.path.join(hk.ART, "preview", f"{out}_v{rp.next_n(out)}.png")
    im.file_format = "PNG"
    im.save()
    print("SHEET", im.filepath_raw)


def glaive_closeup(stem="pose_check_glaive_closeup"):
    """The glaive alone, close on its blade: flat on, edge on and from above, then in the hero's hands; side by side."""
    tiles = []
    for k, (spin, pitch, hand) in enumerate(((0, 4, False), (90, 4, False), (0, 80, False), (-45, 18, True))):
        hk.empty_scene()
        t = rp.load_templates(rp.latest(os.path.join("minis", "heroes"), "hero_kit"))
        for o in t.values():
            o.hide_render = True
        col = hk.new_collection("line")
        hk.PALETTE["hero_ground"] = rh.GROUND
        rh.floor(col)
        if hand:
            desc = rh.hero("human", "average", "a", "short", S["skin"]["human"][1], S["hair"][1], S["eyes"][1], S["cloth"][1], "light", "glaive", None)
            rh.stand(t, col, desc, "h", at=(0, 0, 0), spin=spin)
            target, dist = Vector((0, 0, 0.6)), 3.4
        else:
            ob = t["hero_glaive"].copy()
            ob.hide_render = False
            col.objects.link(ob)
            ob.location, ob.rotation_euler.z = Vector((0, 0, 0.1)), math.radians(spin)
            target, dist = Vector((0, 0, 1.25)), 1.1
        view = f"{stem}_view{k}"
        rh.shot(view, target, dist, pitch, (TILE, H_SHOT))
        tiles.append(latest(view))
    pixels = np.ones((H_SHOT, TILE * len(tiles), 4), dtype=np.float32)
    for k, tile in enumerate(tiles):
        pixels[:, k * TILE:(k + 1) * TILE] = tile
    im = bpy.data.images.new(stem, TILE * len(tiles), H_SHOT, alpha=True)
    im.pixels[:] = pixels.ravel().tolist()
    im.filepath_raw = os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem)}.png")
    im.file_format = "PNG"
    im.save()
    print("SHEET", im.filepath_raw)


def wraps_hand(stem="pose_check_wraps_hand"):
    """The wraps hero's open hand, close: front, side, palm (from the foe's side) and back; side by side."""
    tiles = []
    desc = rh.hero("human", "average", "a", "short", S["skin"]["human"][1], S["hair"][1], S["eyes"][1], S["cloth"][1], "light", "wraps", None)
    hand = None
    for k, (spin, pitch) in enumerate(((0, 8), (-90, 8), (0, 60), (180, 8))):  # palm (toward the foe), side, above, back
        hk.empty_scene()
        t = rp.load_templates(rp.latest(os.path.join("minis", "heroes"), "hero_kit"))
        for o in t.values():
            o.hide_render = True
        col = hk.new_collection("line")
        hk.PALETTE["hero_ground"] = rh.GROUND
        rh.floor(col)
        rh.stand(t, col, desc, "h", at=(0, 0, 0), spin=0)
        if hand is None:  # the open hand: the +x hand of the stance, in the assembler's own layout
            right, _, _, pose = hb.grip_layout("human", "average", "wraps", None)
            f = hb.frame("human", "average")
            hip, drop, twist = f["hip"], pose.get("drop", 0.0), math.radians(pose.get("twist", 0))
            upper = Matrix.Translation(Vector((0, 0, -drop))) @ Matrix.Translation(hip) @ Matrix.Rotation(twist, 4, "Z") @ Matrix.Translation(-hip)
            k_ = hb.RACES["human"]["k"]
            full = Matrix.Translation(Vector((0, 0, hb.Z0))) @ Matrix.Diagonal((k_, k_, k_, 1)) @ Matrix.Translation(Vector((0, 0, -hb.Z0)))
            hand = full @ (upper @ right)
        for o in col.objects:
            if o.type == "MESH" and o.name != "ground":
                o.rotation_euler.z = math.radians(spin)
        target = Matrix.Rotation(math.radians(spin), 4, "Z") @ hand
        view = f"{stem}_view{k}"
        rh.shot(view, target, 0.42, pitch, (TILE, H_SHOT))
        tiles.append(latest(view))
    pixels = np.ones((H_SHOT, TILE * len(tiles), 4), dtype=np.float32)
    for k, tile in enumerate(tiles):
        pixels[:, k * TILE:(k + 1) * TILE] = tile
    im = bpy.data.images.new(stem, TILE * len(tiles), H_SHOT, alpha=True)
    im.pixels[:] = pixels.ravel().tolist()
    im.filepath_raw = os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem)}.png")
    im.file_format = "PNG"
    im.save()
    print("SHEET", im.filepath_raw)


if __name__ == "__main__":
    if "glaive" in sys.argv:
        glaive_closeup()
        sys.exit()
    if "hand" in sys.argv:
        wraps_hand()
        sys.exit()
    if "round5" in sys.argv:  # the changed panels of round 5 and their sheet
        rows = (16, 24, 25)
        for i in rows:
            name, grip, pose, weapon, offhand, extra, change = ROWS[i - 1]
            shot(weapon, offhand, extra, f"pose_check_panel_{i:02d}")
            text_strip([(f"{i}. {name}, {grip}", 0.62), (f"07: {pose}", 0.5), (kit_text(weapon, offhand, extra), 0.5), (change, 0.5)], f"pose_check_panel_{i:02d}_text")
        sheet([f"pose_check_panel_{i:02d}" for i in rows], 1, out="pose_check_round5")
        sys.exit()
    if "round4" in sys.argv:  # the changed panels of round 4 and their sheets
        rows = (7, 8, 16, 20, 21, 24)
        for i in rows:
            name, grip, pose, weapon, offhand, extra, change = ROWS[i - 1]
            if i != 16:  # the glaive panel is already rendered with this kit
                shot(weapon, offhand, extra, f"pose_check_panel_{i:02d}")
            text_strip([(f"{i}. {name}, {grip}", 0.62), (f"07: {pose}", 0.5), (kit_text(weapon, offhand, extra), 0.5), (change, 0.5)], f"pose_check_panel_{i:02d}_text")
        stems = [f"pose_check_panel_{i:02d}" for i in rows]
        for n in range(math.ceil(len(stems) / 3)):
            sheet(stems[n * 3:n * 3 + 3], n + 1, out="pose_check_round4")
        sys.exit()
    if "round3" in sys.argv:  # the captions of this round's rows, then sheets of just those panels
        rows = (1, 2, 3, 4, 5, 6, 7, 8, 9, 20, 21, 24, 25, 26, 27)
        for i in rows:
            name, grip, pose, weapon, offhand, extra, change = ROWS[i - 1]
            text_strip([(f"{i}. {name}, {grip}", 0.62), (f"07: {pose}", 0.5), (kit_text(weapon, offhand, extra), 0.5), (change, 0.5)], f"pose_check_panel_{i:02d}_text")
        stems = [f"pose_check_panel_{i:02d}" for i in rows]
        for n in range(math.ceil(len(stems) / 3)):
            sheet(stems[n * 3:n * 3 + 3], n + 1, out="pose_check_round3")
        sys.exit()
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
