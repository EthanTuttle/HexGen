"""Renders the map encounter trial on real tiles from the game's map camera: true scale against oversized, by day and at night, with a badge for each kind.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_encounter_figures.py
Pass --measure to only print each scene's height on screen, in layout points, at each camera distance and scale, and the largest scale that fits a tile.
Pass shots after -- as scale:light:distance, with :swap for wolves in the open; scale 0 is the badges alone.
Writes art/preview/encounters_x<scale>_<light>_<distance>m_vN.png and encounters_close_<scene>_vN.png.

Camera as in Godot: pitch 50, a 50 mm lens keeping width, a layout 844 wide, opening at 58 m. Night is the 07 table's sun and backdrop at this renderer's scale, so it is near, not exact.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from mathutils import Vector  # noqa: E402

import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402

PITCH, LAYOUT_W, LAYOUT_H = 50, 844, 390
OPENS_AT = 58
SCALES = (1, 1.5, 2, 2.5, 3)
DISTANCES = (30, 40, 58, 110)
TILE_FLATS = 7.79
BADGE_SIZE = 1.6
# Scene, kind's badge and where it stands in the frame, in metres from the view's middle. Wolves stand among trees, to show what a forest does to them.
SCENES = (("enc_fight_wolves", "fight", (-13, 4)), ("enc_social_drinking", "social", (0, 5)), ("enc_fight_bandits", "fight", (13, 4)),
          ("enc_social_trader", "social", (-6.5, -5)), ("enc_discovery_treasure", "discovery", (6.5, -5)))
GROUND = Vector((0, 0, 0))


def linear(colour):
    return [hk.srgb_to_linear(int(colour[k:k + 2], 16) / 255) for k in (1, 3, 5)]


def tile_near(x, y):
    return min(((q, r) for q in range(-8, 9) for r in range(-8, 9)), key=lambda t: (hk.tile_position(*t) - Vector((x, y, 0))).length)


def tiles():
    """Plains, a forest under the wolves and two more for company."""
    out = {t: "plains" for t in ((q, r) for q in range(-8, 9) for r in range(-8, 9)) if (hk.tile_position(*t) - GROUND).length < 34}
    for x, y in ((-13, 4), (-21, 4), (21, -3), (-20, -8)):
        out[tile_near(x, y)] = "forest"
    return out


class Trial:
    def __init__(self):
        hk.empty_scene()
        rp.build_map(rp.load_templates(rp.latest("tiles", "tiles")), tiles=tiles())
        t = rp.load_templates(rp.latest("encounters", "encounters"))
        col = hk.new_collection("encounters")
        self.scenes = []
        for name, kind, at in SCENES:
            spot = hk.tile_position(*tile_near(*at))
            ob = rp.place(t, name, col, spot.copy())
            badge = rp.place(t, f"enc_badge_{kind}", col, spot.copy())
            badge.rotation_euler.x = math.radians(-PITCH)
            badge.scale = (BADGE_SIZE,) * 3
            self.scenes.append((ob, badge))
        rp.stage(GROUND, OPENS_AT, PITCH)
        r = bpy.context.scene.render
        r.resolution_x, r.resolution_y = LAYOUT_W * 2, LAYOUT_H * 2
        self.cam = bpy.context.scene.camera

    def scale(self, k):
        for ob, badge in self.scenes:
            ob.scale = (k,) * 3
            top = max(v.co.z for v in ob.data.vertices) * k
            badge.location.z = ob.location.z + top + 0.3 + 0.35 * k  # clear of the figures behind

    def look(self, at, d):
        el = math.radians(PITCH)
        self.cam.location = at + Vector((0, -d * math.cos(el), d * math.sin(el)))

    def light(self, night):
        nodes = bpy.context.scene.world.node_tree.nodes
        back = linear("#A9AECB") if night else tuple(hk.material("backdrop").diffuse_color)[:3]
        for n in nodes:
            if n.type == "BACKGROUND":
                n.inputs["Color"].default_value = (*back[:3], 1)
        sun = next(o for o in bpy.context.scene.objects if o.type == "LIGHT")
        sun.data.energy = 3.5 * 0.35 / 1.18 if night else 3.5
        sun.data.color = linear("#AFC0E8") if night else (1, 1, 1)

    def points_tall(self, ob):
        bpy.context.view_layer.update()
        scene = bpy.context.scene
        ys = [world_to_camera_view(scene, self.cam, ob.matrix_world @ v.co).y for v in ob.data.vertices]
        return (max(ys) - min(ys)) * LAYOUT_H


def measure(trial):
    print("HEIGHTS scene, then points tall at", DISTANCES, "for each scale")
    for ob, _ in trial.scenes:
        span = max(max(v.co[k] for v in ob.data.vertices) - min(v.co[k] for v in ob.data.vertices) for k in (0, 1))
        for k in SCALES:
            trial.scale(k)
            row = []
            for d in DISTANCES:
                trial.look(ob.location, d)
                row.append(round(trial.points_tall(ob)))
            print("POINTS", ob.name, "x", k, row)
        print("FITS", ob.name, "span", round(span, 2), "largest scale inside the tile's flats", round(TILE_FLATS / span, 2))
    trial.look(GROUND, OPENS_AT)


def swap_fights(trial):
    """Wolves on the plains and bandits in the forest."""
    (wolves, wolf_badge), (bandits, bandit_badge) = trial.scenes[0], trial.scenes[2]
    wolves.location, bandits.location = bandits.location.copy(), wolves.location.copy()
    wolf_badge.location, bandit_badge.location = bandit_badge.location.copy(), wolf_badge.location.copy()


def shot(trial, k, night, d, swap=False):
    """k 0 is the badges alone on their tiles."""
    if swap:
        swap_fights(trial)
    trial.scale(k or 1)
    for ob, badge in trial.scenes:
        ob.hide_render = not k
        if not k:
            badge.location.z = ob.location.z + 0.4
    trial.light(night)
    trial.look(GROUND, d)
    rp.render(f"encounters_{'badges' if not k else f'x{k}'}_{'night' if night else 'day'}_{d}m" + ("_swapped" if swap else ""))
    if swap:
        swap_fights(trial)


def close(trial):
    """Each scene near, at true scale, wolves in the open, for what the figures are."""
    swap_fights(trial)
    trial.scale(1)
    trial.light(False)
    stems = []
    for ob, badge in trial.scenes:
        ob.hide_render = False
        trial.look(ob.location + Vector((0, 0, 0.8)), 13)
        stems.append(f"encounters_close_{ob.name.split('.')[0][4:]}")
        rp.render(stems[-1])
    swap_fights(trial)
    return stems


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    trial = Trial()
    measure(trial)
    if "--measure" in args:
        sys.exit()
    wanted = [a for a in args if not a.startswith("--")]
    for spec in wanted or [f"{k}:day:58" for k in SCALES] + ["1:night:58", "2.5:night:58", "1:day:110", "2.5:day:110", "1:day:58:swap", "2.5:day:58:swap", "0:day:58", "0:night:58"]:
        k, light, d, *swap = spec.split(":")
        shot(trial, float(k) if "." in k else int(k), light == "night", int(d), bool(swap))
    if not wanted or "--close" in args:
        import render_forest_maps as fm
        fm.sheet(close(trial), "encounters_close_all", cols=3)
