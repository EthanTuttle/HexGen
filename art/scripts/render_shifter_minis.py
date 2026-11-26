"""Renders a Shifter form for review: the hero beside their form (in the hero's own colours) and the matching ally beast, from three
sides; the form in three heroes' colours; the form alone, large; and the line-up at the combat camera.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_shifter_minis.py [-- werewolf | builds | races | golems]
Uses the latest shifter_minis, hero_kit and beast_minis. Writes art/preview/shifter_<form>_*_vN.png and the sheets
shifter_<form>_vN.png (line-ups and colours) and shifter_<form>_solo_vN.png.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_hero_kit as hb  # noqa: E402
import build_standin_minis as sm  # noqa: E402
import hexkit as hk  # noqa: E402
import render_beast_minis as rb  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_hero_kit as rh  # noqa: E402
import render_preview as rp  # noqa: E402

S = hb.SWATCHES
# The Shifter: a human ranger with a shortbow in light armour, brown hair, so their wolf is brown.
SHIFTER = rh.hero("human", "average", "a", "short", S["skin"]["human"][1], S["hair"][1], S["eyes"][3], S["cloth"][2], "light", "shortbow")
# Three more heroes' colours for the form: black hair, blond, grey; each with their own cloth and eyes.
OTHERS = [dict(skin=S["skin"]["human"][3], hair=S["hair"][0], eyes=S["eyes"][0], cloth=S["cloth"][0]),
          dict(skin=S["skin"]["elf"][0], hair=S["hair"][3], eyes=S["eyes"][1], cloth=S["cloth"][1]),
          dict(skin=S["skin"]["human"][0], hair=S["hair"][4], eyes=S["eyes"][2], cloth=S["cloth"][3])]


# The ally beast each form stands beside, so the two read apart.
ALLY = {"werewolf": "wolf", "werebear": "bear", "werecat": "panther"}


def start():
    t, col = rb.start()
    t.update(rp.load_templates(rp.latest(os.path.join("minis", "heroes"), "shifter_minis")))
    for o in t.values():
        o.hide_render = True
    return t, col


def line_up(form, spin):
    t, col = start()
    rh.stand(t, col, SHIFTER, "hero", at=(-1.15, 0, 0), spin=spin)
    _, n = rb.beast(t, f"shifter_{form}_average", SHIFTER["colours"], form, col, (0, 0, 0), spin)
    ally = ALLY[form]
    rb.beast(t, f"beast_{ally}", rb.looks(ally)[0], "ally", col, (1.15, 0, 0), spin)
    return t, col, n


def render(form):
    stems = []
    for spin, tag in ((-28, "front"), (152, "back"), (-90, "side")):
        _, _, n = line_up(form, spin)
        stem = f"shifter_{form}_{tag}"
        rh.shot(stem, Vector((0, 0, 0.6)), 5.6, 12, (1500, 760))
        stems.append(stem)
    print("FORMTRIS", form, n)
    t, col = start()
    for i, c in enumerate([SHIFTER["colours"]] + OTHERS):
        rb.beast(t, f"shifter_{form}_average", c, f"{form}_{i}", col, (1.0 * (i - 1.5), 0, 0), -28)
    stem = f"shifter_{form}_colours"
    rh.shot(stem, Vector((0, 0, 0.6)), 6.6, 12, (1500, 760))
    stems.append(stem)
    fm.sheet(stems, f"shifter_{form}", cols=2)
    # The combat camera, about 50 degrees down: close, then at 18 m.
    line_up(form, 0)
    rh.shot(f"shifter_{form}_combat_close", Vector((0, 0, 0.5)), 8, 50, (1500, 600))
    rh.shot(f"shifter_{form}_combat_18m", Vector((0, 0, 0.5)), 18, 50, (1500, 700))
    solo(form)


def solo(form):
    """The form alone in the Shifter's colours, large: front, three-quarter, side, back, the combat camera, and its face."""
    stems = []
    for spin, tag, pitch in ((0, "front", 12), (-35, "three", 12), (-90, "side", 12), (180, "back", 12), (-30, "combat", 50), (-25, "face", 6)):
        t, col = start()
        ob, _ = rb.beast(t, f"shifter_{form}_average", SHIFTER["colours"], form, col, (0, 0, 0), spin)
        pts = [ob.matrix_world @ v.co for v in ob.data.vertices if (ob.matrix_world @ v.co).z > 0.12]
        top = max(q.z for q in pts)
        target, distance = Vector((0, 0, top * 0.5)), {"side": 2.8, "combat": 2.7}.get(tag, 2.5)
        if tag == "face":
            high = [q for q in pts if q.z > top * 0.72] or pts
            ahead = sorted(high, key=lambda q: (ob.matrix_world.inverted() @ q).y)[:max(6, len(high) // 4)]
            target, distance = sum(ahead, Vector()) / len(ahead), 1.0
        stem = f"shifter_{form}_solo_{tag}"
        rh.shot(stem, target, distance, pitch, (900, 900))
        stems.append(stem)
    rb.sheet_full(stems, f"shifter_{form}_solo", cols=3)


def builds():
    """Each form in the slim, average and broad builds, beside the human hero in the same three builds, three-quarter
    and side on, and the whole set at the combat camera: shifter_builds_vN.png."""
    stems = []
    for form in ALLY:
        for spin, tag in ((-28, "three"), (-90, "side")):
            t, col = start()
            for i, b in enumerate(hb.BUILDS):
                if tag == "three":  # the hero in the same build beside each form; side on, the forms alone
                    rh.stand(t, col, dict(SHIFTER, build=b), f"hero_{b}", at=(2.3 * (i - 1) - 0.55, 0.0, 0), spin=spin)
                    at_ = (2.3 * (i - 1) + 0.55, 0, 0)
                else:
                    at_ = (1.3 * (i - 1), 0, 0)
                rb.beast(t, f"shifter_{form}_{b}", SHIFTER["colours"], f"{form}_{b}", col, at_, spin)
            stem = f"shifter_builds_{form}_{tag}"
            rh.shot(stem, Vector((0, 0, 0.6)), 10.5 if tag == "three" else 7.0, 12, (1800, 700))
            stems.append(stem)
    fm.sheet(stems, "shifter_builds", cols=2)
    t, col = start()
    for j, form in enumerate(ALLY):
        for i, b in enumerate(hb.BUILDS):
            rb.beast(t, f"shifter_{form}_{b}", SHIFTER["colours"], f"{form}_{b}", col, (1.0 * (i - 1) + 3.3 * (j - 1), 0, 0), 0)
    rh.shot("shifter_builds_combat", Vector((0, 0, 0.5)), 14, 50, (1800, 600))


# The races from shortest to tallest (build_hero_kit.RACES k), each hero as a light-armoured ranger with a shortbow.
RACE_ORDER = sorted(hb.RACES, key=lambda r: (hb.RACES[r]["k"], r))


def race_hero(race):
    skin = hb.DRAGON_TYPES["red"] if race == "dragonborn" else S["skin"]["golem_stone"][0] if race == "golem" else S["skin"][race][1]
    hair = None if race in hb.HAIRLESS else "short"
    desc = rh.hero(race, "average", "a", hair, skin, S["hair"][1], S["eyes"][3], S["cloth"][2], "light", "shortbow")
    if race == "golem":
        desc["subtype"] = "stone"
    return desc


def form_at_race(t, col, form, race, name, at, spin):
    """The average form in the race's hero's colours, scaled to the race's height as the hero kit scales its bodies
    (build_hero_kit.full: everything above the base, k times about the base's top). Dragonborn fur takes the dragon type's
    colour (07); golems use the furred form as a stand-in until their material forms exist."""
    desc = race_hero(race)
    colours = dict(desc["colours"])
    if race == "dragonborn":
        colours["hair"] = colours["skin"]
    elif race == "golem":
        colours["skin"] = S["skin"]["human"][1]
    ob, _ = rb.beast(t, f"shifter_{form}_average", colours, name, col, at, spin)
    top, k = sm.BASE_H + 0.004, (hb.RACES[race]["k"] + 1) / 2  # eased halfway toward human (Ethan, Nov 26, 2026); shifter_races_v1 used the full factor
    z0 = sm.BASE_H + 0.005
    for v in ob.data.vertices:
        if v.co.z > top:
            v.co = Vector((v.co.x * k, v.co.y * k, z0 + (v.co.z - z0) * k))
    return ob


def races():
    """Each form's average build at every race's height, beside that race's hero, shortest to tallest, then the werebear
    (the biggest) at every race from the combat camera: shifter_races_vN.png."""
    stems = []
    for form in ALLY:
        t, col = start()
        for i, race in enumerate(RACE_ORDER):
            x = 1.75 * (i - (len(RACE_ORDER) - 1) / 2)
            rh.stand(t, col, race_hero(race), f"hero_{race}", at=(x - 0.45, 0.0, 0), spin=-28)
            form_at_race(t, col, form, race, f"{form}_{race}", (x + 0.45, 0, 0), -28)
        stem = f"shifter_races_{form}"
        rh.shot(stem, Vector((0, 0, 0.6)), 17.5, 8, (2400, 560))
        stems.append(stem)
    t, col = start()
    for i, race in enumerate(RACE_ORDER):
        x = 1.75 * (i - (len(RACE_ORDER) - 1) / 2)
        rh.stand(t, col, race_hero(race), f"hero_{race}", at=(x - 0.45, 0.0, 0), spin=0)
        form_at_race(t, col, "werebear", race, f"werebear_{race}", (x + 0.45, 0, 0), 0)
    rh.shot("shifter_races_combat", Vector((0, 0, 0.5)), 19, 50, (2400, 560))
    stems.append("shifter_races_combat")
    fm.sheet(stems, "shifter_races", cols=1)
    print("RACES", RACE_ORDER)


def golems(material="stone"):
    """The golem forms in one material: the golem hero beside each form at the golem's eased height, three-quarter and side
    on, each form close up, and the line-up from the combat camera: shifter_golem_<material>_vN.png."""
    hero = dict(race_hero("golem"), subtype=material)
    hero["colours"]["skin"] = S["skin"][f"golem_{material}"][0]
    k = (hb.RACES["golem"]["k"] + 1) / 2
    z0 = sm.BASE_H + 0.005

    def form(t, col, name, at, spin, build="average"):
        ob, _ = rb.beast(t, f"shifter_{name}_golem_{material}_{build}", hero["colours"], f"{name}_{build}", col, at, spin)
        for v in ob.data.vertices:
            if v.co.z > sm.BASE_H + 0.004:
                v.co = Vector((v.co.x * k, v.co.y * k, z0 + (v.co.z - z0) * k))
        return ob
    stems = []
    for spin, tag in ((-28, "three"), (-90, "side")):
        t, col = start()
        rh.stand(t, col, hero, "golem", at=(-1.65, 0, 0), spin=spin)
        for i, name in enumerate(ALLY):
            form(t, col, name, (1.1 * i - 0.45, 0, 0), spin)
        stem = f"shifter_golem_{material}_{tag}"
        rh.shot(stem, Vector((0, 0, 0.6)), 7.0, 12, (1800, 700))
        stems.append(stem)
    for name in ALLY:
        t, col = start()
        form(t, col, name, (0, 0, 0), -30)
        stem = f"shifter_golem_{material}_{name}_close"
        rh.shot(stem, Vector((0, 0, 0.7)), 2.8, 14, (900, 900))
        stems.append(stem)
    t, col = start()
    rh.stand(t, col, hero, "golem", at=(-1.65, 0, 0), spin=0)
    for i, name in enumerate(ALLY):
        form(t, col, name, (1.1 * i - 0.45, 0, 0), 0)
    rh.shot(f"shifter_golem_{material}_combat", Vector((0, 0, 0.5)), 9, 50, (1800, 700))
    t, col = start()  # the builds: each form slim, average and broad
    for j, name in enumerate(ALLY):
        for i, b in enumerate(hb.BUILDS):
            form(t, col, name, (0.95 * (i - 1) + 3.1 * (j - 1), 0, 0), -28, b)
    rh.shot(f"shifter_golem_{material}_builds", Vector((0, 0, 0.6)), 14.5, 12, (1800, 700))
    fm.sheet(stems[:2] + [f"shifter_golem_{material}_builds", f"shifter_golem_{material}_combat"], f"shifter_golem_{material}", cols=1)
    rb.sheet_full(stems[2:], f"shifter_golem_{material}_close", cols=3)


if __name__ == "__main__":
    for name in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["werewolf"]):
        {"builds": builds, "races": races, "golems": golems}.get(name, lambda: render(name))()
