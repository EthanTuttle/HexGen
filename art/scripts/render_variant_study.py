"""Variant study: each terrain group's variants side by side at the comparison camera, to see how they differ.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_variant_study.py [-- <group> ...]
Each region is render_region_compare.world (its landmark, if it has one, in the middle, six of its tiles round it, its
plain terrain beyond and a few plains), from the latest kit; the trapped vault (not in a kit yet) is built live as
render_ruin_structure.py builds it. Writes art/preview/study_<region>_map_vN.png and study_<group>_sheet_vN.png.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import render_region_compare as rc  # noqa: E402
import render_ruin_structure as rrs  # noqa: E402
import render_start_tiles as rst  # noqa: E402
import ruin_structure as rs  # noqa: E402
import variants as vr  # noqa: E402

# group -> [(region, its plain terrain, title)]
GROUPS = {
    "forest": [("forest", "forest", "Forest"), ("deep_forest", "forest", "Deep forest"), ("fey_wood", "forest", "Fey wood"),
               ("dark_wood", "forest", "Dark wood"), ("heartwood", "forest", "Heartwood")],
    "village": [("village", "village", "Village"), ("market_town", "village", "Market town"), ("fortified_town", "village", "Fortified town"),
                ("slums", "village", "Slums"), ("scholars_town", "village", "Scholars' town")],
    "farmland": [("farmland", "farmland", "Farmland"), ("windmill_country", "farmland", "Windmill country"), ("haunted_homesteads", "farmland", "Haunted homesteads"),
                 ("raided_farms", "farmland", "Bandit-raided farms"), ("cider_orchards", "farmland", "Cider orchards")],
    "desert": [("desert", "desert", "Desert"), ("wasteland", "desert", "Dunes / wasteland"), ("badlands", "desert", "Badlands"),
               ("oasis", "desert", "Oasis"), ("canyon", "desert", "Canyon")],
    "swamp": [("swamp", "swamp", "Swamp"), ("bog", "swamp", "Bog / fen"), ("wisp_marsh", "swamp", "Will-o'-wisp marsh"),
              ("rot_swamp", "swamp", "Rot swamp"), ("smugglers_bayou", "swamp", "Smugglers' bayou")],
    "river": [("river", "river", "River / lake"), ("delta", "river", "River delta"), ("great_lake", "river", "Great lake"),
              ("rapids", "river", "Rapids"), ("still_waters", "river", "Still waters")],
    "hills": [("hills", "hills", "Hills"), ("highlands", "hills", "Highlands"), ("snowy_peaks", "hills", "Snowy peaks"),
              ("volcanic_peaks", "hills", "Volcanic peaks"), ("monastery_heights", "hills", "Monastery heights")],
    "plains": [("plains", "plains", "Plains"), ("meadows", "plains", "Meadows"), ("battlefield", "plains", "Steppe / battlefield"),
               ("stormy_plains", "plains", "Stormy plains"), ("tourney_fields", "plains", "Tourney fields")],
    "ruins": [("ruins", "ruins", "Ruins"), ("overrun_outpost", "ruins", "Overrun outpost"), ("haunted_ruins", "ruins", "Haunted ruins"),
              ("basilisk_ruins", "ruins", "Basilisk ruins"), ("trapped_vault", "ruins", "Trapped vault (round 1)")],
}


def world(region, plain):
    if region == "trapped_vault":
        w = rc.world("haunted_ruins", plain)
        return {t: "vault" if v == "crypt" else "trapped_vault" if v == "haunted_ruins" else v for t, v in w.items()}
    w = rc.world(region, plain)
    if region == "rapids":   # the Troll Bridge needs a river course this little map doesn't lay out: the rapids alone
        w[(0, 0)] = "rapids"
    return w


def shot(region, plain, title):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    w = world(region, plain)
    if region == "trapped_vault":   # live, wired as render_ruin_structure.vault_shot does
        templates.update(rrs.build_vault())
        vr.VARIANTS["trapped_vault"] = ("ruins", rs.vault_ground, "tv_ground", ("edge_same_b", "edge_other_b"))
        vr.LANDMARKS["vault"] = "trapped_vault"
        vr.LANDMARK_CENTRES["vault"] = rs.vault
        vr.BASE["trapped_vault"] = vr.BASE["vault"] = "ruins"
        vr.rl.LOOKS.add("trapped_vault")
        rp.gc.DENSITY["trapped_vault"] = rp.gc.DENSITY["vault"] = 0.1
        vr.rl.tile_props = lambda name, q, r, ww=None: (rs.vault_props(w, q, r) if name == "trapped_vault" else rrs.ORIGINAL_PROPS(name, q, r, ww))
    rp.build_map(templates, tiles=w)
    vr.rl.tile_props = rrs.ORIGINAL_PROPS
    rp.stage(hk.tile_position(1, -1) * 0.5 + Vector((0, -2, 0)), 62, 45)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1000, 625
    rst.label(title, "Its region, at the map camera, by day")
    stem = f"study_{region}_map"
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for group in args or GROUPS:
        cells = [shot(*cell) for cell in GROUPS[group]]
        pad = rc.blank()
        cells += [pad] * (6 - len(cells))
        rst.SHEET_STEM = f"study_{group}_sheet"
        rst.sheet([cells[:3], cells[3:]])
        os.remove(pad)
