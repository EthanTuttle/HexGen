"""Renders true-scale encounter figures with their kind's badge drawn over the frame, as Godot would draw it: a HexShape in the HUD (art/handoff/encounters_kit.md).

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_encounter_badges.py [-- --curve]
Writes art/preview/encounter_badges<width>_<shot>_vN.png, the side-by-side sheets encounter_badges_sizes_vN.png and encounter_glade_<light>_vN.png, and encounter_badges_swords_vN.png.

The badge isn't in the 3D scene: each frame is rendered without one, then the hex is painted in layout points at twice the 844 x 390 layout, so it's unlit and over the trees by nature.
"""
import math
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from mathutils import Vector  # noqa: E402

import render_encounter_figures as ef  # noqa: E402
import render_preview as rp  # noqa: E402

PIXELS = 2  # pixels per layout point
SAMPLES = 4
SMALLEST, SHRINK_END, FADE = 0.75, 18, (12, 24)  # Ethan, Nov 4, 2026: the first curve (0.55, 24, (18, 30)) shrank too hard
ICON = 0.66  # of the badge's width
HEX_RATIO = 51 / 44  # the app's hexes, tall for their width
GAP = 4  # points between the anchor and the badge's foot
LIFT = 0.35  # metres from the scene's top up to the anchor, clear of figures further back
# Fill, edge under the token and icon, from the app's colours. Social's edge is ours: the app has no dark blue edge.
KINDS = {"fight": ("#8E3B2E", "#5A2A22", "#FFF8EE", "swords_solid", True),
         "social": ("#225C91", "#163E63", "#FFF8EE", "bubble", True),
         "discovery": ("#E4B54C", "#A67A1F", "#24302C", "sparkle", True)}
RIM = "#FCF7EE"


def solid_swords():
    """Two crossed swords as filled shapes, all wound one way so they join where they cross. Printed for Icons.PATHS."""
    sword = (((0, 14.2), (2.3, 10.4), (2.3, -3.4), (-2.3, -3.4), (-2.3, 10.4)),  # blade
             ((5.8, -3.2), (5.8, -6.2), (-5.8, -6.2), (-5.8, -3.2)),  # guard
             ((1.7, -6), (1.7, -10), (-1.7, -10), (-1.7, -6)),  # grip
             ((2.6, -9.8), (2.6, -12.6), (-2.6, -12.6), (-2.6, -9.8)))  # pommel
    out = []
    for turn in (math.radians(45), math.radians(-45)):
        c, s = math.cos(turn), math.sin(turn)
        for shape in sword:
            pts = [(12 + x * c + y * s, 12 + x * s - y * c) for x, y in shape]
            area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))
            pts = pts if area > 0 else pts[::-1]
            out.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "z")
    return " ".join(out)


PATHS = {"swords": "M5 5l11 11 M19 5L8 16 M14 18l4-4 M10 18l-4-4 M17 17l3 3 M7 17l-3 3",
         "swords_solid": solid_swords(),
         "bubble": "M7 4h10c2.2 0 4 1.8 4 4v4c0 2.2-1.8 4-4 4h-5l-5 4.5V16c-2.2 0-4-1.8-4-4V8c0-2.2 1.8-4 4-4z",
         "sparkle": "M12 2c.8 5.6 3.4 8.2 10 10-6.6 1.8-9.2 4.4-10 10-.8-5.6-3.4-8.2-10-10 6.6-1.8 9.2-4.4 10-10z"}


def width_at(d, far):
    """The badge's width in layout points at camera distance d: far from 58 m out, then easing to SMALLEST of that at SHRINK_END as the figures grow."""
    return far * (SMALLEST + (1 - SMALLEST) * min(1.0, max(0.0, (d - SHRINK_END) / (58 - SHRINK_END))))


def alpha_at(d):
    return min(1.0, max(0.0, (d - FADE[0]) / (FADE[1] - FADE[0])))


def srgb(colour):
    return np.array([int(colour[k:k + 2], 16) / 255 for k in (1, 3, 5)], dtype=np.float32)


def flatten(path):
    """Polylines from an SVG path of M, L, H, V, C and Z, as x, y in its 24 box."""
    out, here, start, cmd = [], np.zeros(2), np.zeros(2), None
    tokens = re.findall(r"[MmLlHhVvCcZz]|-?\d*\.?\d+", path)
    i = 0

    def number():
        nonlocal i
        i += 1
        return float(tokens[i - 1])

    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
        rel = cmd.islower()
        c = cmd.upper()
        if c == "Z":
            out[-1].append(start.copy())
            here = start.copy()
        elif c == "M":
            at = np.array((number(), number()))
            here = here + at if rel else at
            start = here.copy()
            out.append([here.copy()])
            cmd = "l" if rel else "L"
        elif c == "L":
            at = np.array((number(), number()))
            here = here + at if rel else at
            out[-1].append(here.copy())
        elif c in "HV":
            k = 0 if c == "H" else 1
            at = number()
            here = here.copy()
            here[k] = here[k] + at if rel else at
            out[-1].append(here.copy())
        elif c == "C":
            pts = [np.array((number(), number())) for _ in range(3)]
            if rel:
                pts = [here + p for p in pts]
            for t in np.linspace(0, 1, 13)[1:]:
                out[-1].append((1 - t) ** 3 * here + 3 * (1 - t) ** 2 * t * pts[0] + 3 * (1 - t) * t ** 2 * pts[1] + t ** 3 * pts[2])
            here = pts[2]
    return out


def fill(xs, ys, poly):
    """Inside the polygon, by crossings."""
    inside = np.zeros(xs.shape, bool)
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if a[1] == b[1]:
            continue
        spans = (ys >= min(a[1], b[1])) & (ys < max(a[1], b[1]))
        inside ^= spans & (xs < a[0] + (ys - a[1]) * (b[0] - a[0]) / (b[1] - a[1]))
    return inside


def stroke(xs, ys, lines, width):
    """Within width / 2 of the lines, so round caps and joins."""
    best = np.full(xs.shape, 1e9, np.float32)
    for line in lines:
        for a, b in zip(line, line[1:]):
            d = b - a
            t = np.clip(((xs - a[0]) * d[0] + (ys - a[1]) * d[1]) / max(d @ d, 1e-9), 0, 1)
            best = np.minimum(best, np.hypot(xs - a[0] - t * d[0], ys - a[1] - t * d[1]))
    return best <= width / 2


def hexagon(cx, top, w, h):
    return [np.array(p) for p in ((cx, top), (cx + w / 2, top + h * 0.25), (cx + w / 2, top + h * 0.75), (cx, top + h), (cx - w / 2, top + h * 0.75), (cx - w / 2, top + h * 0.25))]


def paint(pixels, cx, foot, kind, width, alpha=1.0, icon_override=None):
    """A badge on a top-down float image, all sizes in pixels, as HexShape draws it: edge below, rim, face, icon."""
    if alpha <= 0:
        return
    face, edge, ink, icon, solid = KINDS[kind]
    if icon_override:
        icon, solid = icon_override, False
    w = width * PIXELS
    h = w * HEX_RATIO
    drop = 2 * PIXELS
    top = foot - h - drop
    x0, y0 = int(cx - w / 2 - 2), int(top - 2)
    nx, ny = int(w) + 5, int(h + drop) + 5
    H, W, _ = pixels.shape
    if x0 < 0 or y0 < 0 or x0 + nx >= W or y0 + ny >= H:
        return
    grid = (np.arange(nx * SAMPLES) + 0.5) / SAMPLES + x0, (np.arange(ny * SAMPLES) + 0.5) / SAMPLES + y0
    xs, ys = np.meshgrid(*grid)
    inset = max(1.5, 0.09 * w)
    icon_size = ICON * w
    scale = icon_size / 24
    place = lambda p: np.array((cx - icon_size / 2 + p[0] * scale, top + h / 2 - icon_size / 2 + p[1] * scale))  # noqa: E731
    lines = [[place(p) for p in line] for line in flatten(PATHS[icon])]
    icon_mask = np.any([fill(xs, ys, line[:-1]) for line in lines], axis=0) if solid else stroke(xs, ys, lines, 2.6 * scale)
    for mask, colour in ((fill(xs, ys, hexagon(cx, top + drop, w, h)), edge), (fill(xs, ys, hexagon(cx, top, w, h)), RIM),
                         (fill(xs, ys, hexagon(cx, top + inset, w - 2 * inset, h - 2 * inset)), face), (icon_mask, ink)):
        cover = mask.reshape(ny, SAMPLES, nx, SAMPLES).mean(axis=(1, 3))[..., None] * alpha
        area = pixels[y0:y0 + ny, x0:x0 + nx, :3]
        area[:] = area * (1 - cover) + srgb(colour) * cover


def shot(trial, target, d, night, stem, far):
    """Renders without badges, paints them, saves one preview."""
    scene = bpy.context.scene
    trial.light(night)
    trial.look(target, d)
    bpy.context.view_layer.update()
    path = os.path.join(hk_temp, "frame.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    pixels = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1].copy()
    for (ob, badge), (_, kind, _) in zip(trial.scenes, ef.SCENES):
        top = ob.location + Vector((0, 0, max(v.co.z for v in ob.data.vertices) + LIFT))
        at = world_to_camera_view(scene, trial.cam, top)
        if 0 < at.x < 1 and 0 < at.y < 1:
            paint(pixels, at.x * w, (1 - at.y) * h - GAP * PIXELS, kind, width_at(d, far), alpha_at(d))
    out = bpy.data.images.new(stem, w, h, alpha=True)
    out.pixels[:] = pixels[::-1].ravel().tolist()
    out.filepath_raw = os.path.join(rp.hk.ART, "preview", f"{stem}_v{rp.next_n(stem)}.png")
    out.file_format = "PNG"
    out.save()
    print("RENDERED", out.filepath_raw, "badge", round(width_at(d, far), 1), "pt, alpha", round(alpha_at(d), 2))
    bpy.data.images.remove(im)
    return stem


def swords_sheet():
    """The line swords against the solid ones at the sizes they're seen, on forest and on grass. Twice real size, so the pixels show."""
    widths = (18, 22, 26, 32, 40)
    h, w = 260, 840
    pixels = np.zeros((h, w, 4), np.float32)
    pixels[..., 3] = 1
    pixels[:, :, :3] = srgb("#A8CF7E")
    pixels[h // 2:, :, :3] = srgb("#4B7A4C")
    for row in range(2):
        x = 40
        for width in widths:
            for icon in ("swords", None):
                paint(pixels, x, 125 + row * 130, "fight", width, icon_override=icon)
                x += width * PIXELS + 14
    big = np.repeat(np.repeat(pixels, 2, axis=0), 2, axis=1)
    save(big, "encounter_badges_swords")


def save(pixels, stem):
    h, w, _ = pixels.shape
    out = bpy.data.images.new(stem, w, h, alpha=True)
    out.pixels[:] = pixels[::-1].ravel().tolist()
    out.filepath_raw = os.path.join(rp.hk.ART, "preview", f"{stem}_v{rp.next_n(stem)}.png")
    out.file_format = "PNG"
    out.save()
    print("RENDERED", out.filepath_raw)


def clear_or_restore(trial, tile_at, glade_ob, cleared):
    """Swaps the forest tile's centre for the glade piece, and back."""
    for ob in bpy.data.objects:
        if ob.get("piece") == "forest_centre" and (ob.location - tile_at).length < 0.1:
            ob.hide_render = cleared
    glade_ob.hide_render = not cleared


if __name__ == "__main__":
    hk_temp = tempfile.mkdtemp()
    print("SWORDS", PATHS["swords_solid"])
    trial = ef.Trial()
    trial.scale(1)
    for _, badge in trial.scenes:
        badge.hide_render = True
    wolves, drinkers, bandits, trader, treasure = [ob for ob, _ in trial.scenes]
    import render_forest_maps as fm
    if "--curve" in sys.argv:
        # The first curve on the left, the eased one on the right.
        stems = []
        for d in (58, 40, 30, 24, 18, 12):
            for name, curve in (("first", (0.55, 24, (18, 30))), ("eased", (0.75, 18, (12, 24)))):
                SMALLEST, SHRINK_END, FADE = curve
                stems.append(shot(trial, drinkers.location, d, False, f"encounter_badge_curve_{name}_{d}m", 32))
        fm.sheet(stems, "encounter_badge_curve", cols=2)
        SMALLEST, SHRINK_END, FADE = 0.75, 18, (12, 24)
        shot(trial, bandits.location, 30, True, "encounter_badge_curve_night_30m", 32)
        sys.exit()
    sized = []
    for spec in ((ef.GROUND, 110, False, "map_day_110m"), (ef.GROUND, 58, False, "map_day_58m"), (ef.GROUND, 58, True, "map_night_58m"), (bandits.location, 40, False, "open_day_40m"),
                 (bandits.location, 30, False, "open_day_30m"), (bandits.location, 24, False, "open_day_24m")):
        for far in (32, 40):
            sized.append(shot(trial, spec[0], spec[1], spec[2], f"encounter_badges{far}_{spec[3]}", far))
    fm.sheet(sized, "encounter_badges_sizes", cols=2)
    # The forest tile as it is, against the glade, at the same zooms. Badges at 32.
    glade = rp.place(bpy.data.objects, "forest_centre_glade", bpy.data.collections["encounters"], wolves.location.copy())
    centre = next(ob for ob in bpy.data.objects if ob.get("piece") == "forest_centre" and (ob.location - wolves.location).length < 0.1)
    glade.rotation_euler.z = centre.rotation_euler.z
    for night, light in ((False, "day"), (True, "night")):
        stems = []
        for d in (58, 40, 30, 24, 18, 12):
            for cleared, how in ((False, "current"), (True, "glade")):
                clear_or_restore(trial, wolves.location, glade, cleared)
                stems.append(shot(trial, wolves.location, d, night, f"encounter_glade_{how}_{light}_{d}m", 32))
        fm.sheet(stems, f"encounter_glade_{light}", cols=2)
    # Every scene in the glade, as the trader's cart is the widest.
    clear_or_restore(trial, wolves.location, glade, True)
    fits = []
    spot = wolves.location.copy()
    for ob, _ in trial.scenes:
        home = ob.location.copy()
        ob.location, wolves.location = spot.copy(), home.copy() if ob is not wolves else spot.copy()
        fits.append(shot(trial, spot, 24, False, f"encounter_glade_fit_{ob.name.split('.')[0][4:]}", 32))
        wolves.location, ob.location = spot.copy(), home
    fm.sheet(fits, "encounter_glade_fit", cols=3)
