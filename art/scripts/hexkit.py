"""Shared helpers for the Heads or Hexes prototype art scripts (run inside Blender).

Units: 1 Blender unit = 1 glTF metre. Z is up; pivots sit at the centre, at ground level (z = 0).
Rules and numbers: design/06 Multiplayer & tech.md -> Engine prototype.
"""
import json
import math
import os
import random
import re

import bmesh
import bpy
from mathutils import Matrix, Vector

# --- Sizes -----------------------------------------------------------------

CELL_FLATS = 1.0                                  # combat cell, across its flats (flat-top)
CELL_RADIUS = CELL_FLATS / math.sqrt(3)           # centre to corner
TILE_RADIUS = 4.5                                 # map tile, centre to corner (pointy-top): 9.0 tall
TILE_APOTHEM = TILE_RADIUS * math.sqrt(3) / 2     # centre to edge: about 3.9, so about 7.8 wide
INNER = 0.45                                      # centre piece reaches this share of the apothem
SOIL_TOP, SOIL_BOTTOM = -0.15, -0.6               # tile sides: light band, then dark band

# --- Palette (placeholders: exploration v8b and combat v14 mockup colours) --

PALETTE = {
    "plains": "#A8CF7E",
    "forest": "#5E8F5A",
    "farmland": "#DCC562",
    "river": "#86BEDB",
    "village": "#E6C590",
    "hills": "#BFAE8E",
    "swamp": "#7F9A6E",
    "desert": "#EDD49A",
    "ruins": "#B3ADA4",
    "soil_light": "#8A6446",
    "soil_dark": "#6B4C35",
    # props
    "grass_ink": "#7FA95A",  # tufts: close to the grass, so open ground reads calm, not speckled
    "leaf": "#4E8049",
    "leaf_dark": "#3B6A3A",
    "trunk": "#7A5236",
    "field_a": "#DCC562",
    "field_b": "#C9A94A",
    "field_c": "#9DBF5E",
    "hedge": "#4F7A33",
    "water": "#86BEDB",
    "water_deep": "#5E9CC7",
    "fall_light": "#A8D5E2",
    "water_fast": "#6FAFC9",
    "water_still": "#93CFC7",
    "foam": "#F4FAF8",
    "wave_light": "#8FC2DE",
    "water_shade": "#4A6F86",
    "serpent": "#3E6F6B",
    "net": "#C8BEA0",
    "smooth_stone": "#BDB9AB",
    "bank": "#C9B58A",
    "reed": "#6E8F3E",
    "lily": "#5E9E4E",
    "boat": "#E9DCC0",
    "wall": "#EFE2C6",
    "roof": "#B5523B",
    "road": "#CDB58A",
    "cobble": "#BCB2A4",
    "cobble_dark": "#A69C8E",
    "street": "#DACFBB",
    "wall_warm": "#E8CFA6",
    "roof_brown": "#8F5A42",
    "banner_guild": "#3F6C9B",
    "timber_light": "#C8A579",
    "stone_block": "#A3A6A8",
    "stone_block_dark": "#85898C",
    "keep_stone": "#C2C4C2",
    "wall_stone_light": "#B6B8B8",
    "slate": "#5F6B78",
    "slate_dark": "#515C68",
    "banner_fort": "#A33A35",
    # the slums' ground: tan (Ethan's pick, Nov 2, 2026); env HEX_SLUM builds the options he chose from (SLUM_GROUND below)
    "mud_ground": "#CDB48A",
    "mud_street": "#B59C73",
    "mud_dark": "#A38A63",
    "mud_damp": "#BFA67E",
    "weed_ground": "#A3AE78",
    "weed": "#6F8A45",
    "shack_a": "#9C7B55",
    "shack_b": "#7E6547",
    "roof_tin": "#7E7468",
    "patch_red": "#A8483A",
    "patch_ochre": "#C9973F",
    "patch_teal": "#4F8A83",
    "patch_brown": "#7A5F45",
    "lantern_red": "#E5432D",
    "cream_stone": "#EDE3CC",
    "stone_pale_col": "#E3DBC8",
    "slate_blue": "#5E7A9A",
    "pale_paving": "#B7BF9F",
    "quad_paving": "#E4DCCB",
    "terracotta": "#C4683F",
    "flagstone": "#8B8783",
    "flower_red": "#D6455A",
    "flower_yellow": "#F0C53C",
    "paint_blue": "#4E7FB5",
    "paint_teal": "#3F8F8A",
    "paint_green": "#5C8F52",
    "paint_red": "#B0473A",
    "patch_cream": "#CDBE9F",
    "lawn": "#8FBF6A",
    "brass": "#C9A24A",
    "fence": "#8A6446",
    "rock": "#A9A39A",
    "rock_dark": "#8F897F",
    "rock_light": "#BEB8AE",
    "stone_tan": "#B8A88E",
    "stone_blue": "#8E959B",
    "stone_brown": "#9C8B78",
    "flower": "#F2D46B",
    # hills, desert, swamp, ruins
    "hill_grass": "#A3C47A",
    "cliff": "#A89F8E",
    "sand": "#F3DFAC",
    "cracked": "#D8BB7E",
    "scrub": "#9C9A5C",
    "cactus": "#6E9A5A",
    "bog_water": "#5F7F6C",
    "mist_low": "#E4EADF",
    "swamp_bank": "#6B6549",
    "bog_bank": "#585A42",
    "bayou_bank": "#5D5943",
    "mud": "#7A7152",
    "hummock": "#6F8E5C",
    "deadwood": "#7C6E5E",
    # tier 1 region variants
    "deep_forest": "#466F47",
    "pine_deep": "#3A6A41",
    "hide": "#8A6A4E",
    "hide_light": "#C9B79C",
    "flower_pink": "#E9A3B8",
    "flower_white": "#F4F1E8",
    "flower_blue": "#9DB4E0",
    "highland_grass": "#9FB07E",
    "heather": "#9C6FA0",
    "hay": "#D1B668",
    "stubble": "#D9C27A",
    "sail": "#EFE6D2",
    "timber": "#5E4532",
    "awning_a": "#C8553D",
    "awning_b": "#F2E8D5",
    "crate": "#A7825A",
    "fruit": "#D9822B",
    "sandbar": "#E3D3A8",
    "bog": "#6B8462",
    "bog_dark": "#3F5A4F",
    "mud_dark": "#4F4A3B",
    "tuft_swamp": "#64804F",
    "tuft_bog": "#4F6A4E",
    "tuft_wisp": "#5C8A73",
    "tuft_rot": "#5A6134",
    "track_bog": "#74795A",
    "herb": "#7E9A48",
    "cauldron": "#2E2C2A",
    "window_green": "#8CF56A",
    "thatch": "#A08A55",
    "thatch_dark": "#7D6A40",
    "thatch_light": "#B9A56C",
    "wisp_ground": "#6F9C86",
    "wisp_water": "#A2DCCD",
    "wisp_bank": "#A9B98F",
    "wisp_pool": "#C8F5E6",
    "wisp": "#E2FFF8",
    "wisp_green": "#BFF9B4",
    "track_wisp": "#94AE8C",
    "cattail": "#6B4A2C",
    "chest_wood": "#6A4A2A",
    "chest_band": "#4C3A25",
    "gold": "#E8C04A",
    "rot_ground": "#6E7440",
    "rot_water": "#A8A83E",
    "rot_mud": "#59522F",
    "track_rot": "#5F5F34",
    "ooze": "#C9E04A",
    "ooze_bright": "#E6F57A",
    "scum": "#8E9A3A",
    "slime": "#B7D45A",
    "fungus_pale": "#E6DFC2",
    "shelf": "#C9A97A",
    "rot_wood": "#5B4A33",
    "rot_stone": "#4E4C3A",
    "pit_wall": "#5E5A42",
    "pit_wall_b": "#6B6749",
    "pit_wall_dark": "#3F3E2E",
    "lane_rot_a": "#4C4A34",
    "lane_rot_b": "#5A5A3A",
    "lane_rot_c": "#676C3E",
    "bayou_ground": "#6C8258",
    "bayou_water": "#4F6E5E",
    "tarp": "#6B7A5A",
    "plank": "#9A7B52",
    "plank_dark": "#6F5638",
    "sign_board": "#7C5A36",
    "toadstool": "#F0C24E",
    "poison_purple": "#8E4FA6",
    "poison_yellow": "#E6D23F",
    "spiky": "#4F6B3A",
    "wasteland": "#E2CFA2",
    "badlands_ground": "#DDBD92",
    "mesa_top": "#E8C9A0",
    "mesa_a": "#D08A5A",
    "mesa_b": "#BC6F47",
    "mesa_c": "#E0A878",
    "oasis_ground": "#EAD9AE",
    "oasis_grass": "#8FBF6A",
    "oasis_water": "#4FC9C4",
    "palm_trunk": "#8A6A45",
    "palm_frond": "#4E9A52",
    "camel": "#C9A36E",
    "rug_a": "#B8433F",
    "rug_b": "#2F7F9E",
    "rug_c": "#D9A441",
    "dome": "#F0E4CC",
    "canyon_top": "#DBA877",
    "canyon_rust_top": "#C87A4E",
    "oasis_ripple": "#DFC99A",
    "canyon_lane_a": "#E7BF8D", "canyon_lane_b": "#E2B785", "canyon_lane_c": "#DEAF7E",
    "ramp_worn": "#C9A173", "ramp_worn_b": "#B48B5F", "ramp_worn_c": "#D7B487",
    "ramp_worn_red": "#B98258", "ramp_worn_red_b": "#A36F49", "ramp_worn_red_c": "#C8946A",
    "ramp_plank": "#A67E52", "ramp_plank_b": "#8C6A46", "ramp_plank_c": "#B8925F", "ramp_post": "#6B4F36", "ramp_rope": "#CDBB94",
    "ramp_adobe": "#E0B98A", "ramp_adobe_b": "#CFA273", "ramp_adobe_c": "#EAC99C",
    "canyon_deck": "#E2B487",
    "canyon_cream": "#F0CE96",
    "canyon_orange": "#E2914F",
    "canyon_rust": "#B85C35",
    "canyon_floor": "#EBC795",
    "canyon_side": "#8F5233",
    "adobe": "#D9AE7E",
    "cave_dark": "#1E1612",
    "sandstone": "#D6B484",
    "sphinx": "#C08D55",
    "sphinx_dark": "#A07043",
    "sphinx_light": "#DDBB86",
    "sphinx_shade": "#4A3524",
    "offering": "#B5412E",
    "bone": "#F1EBDD",
    "pit": "#6B5038",
    "pit_dark": "#3A2B20",
    "canvas": "#E2B98A",
    "lantern": "#F6D36B",
    "rope": "#C9B58A",
    # tier 2 forest variants (placeholders)
    "fey_wood": "#5C9270",
    "fey_teal": "#4FA6A0",
    "fey_violet": "#8F7BC6",
    "fey_rose": "#DB8FAA",
    "fey_mushroom": "#B47FE6",
    "fey_stem": "#E4DCCB",
    "dark_wood": "#5B5F4F",
    "bark_grey": "#57534E",
    "bark_black": "#2B2926",
    "bark_dark": "#403D39",
    "web": "#D6D4CF",
    "tuft_dark_wood": "#53574A",
    "bramble": "#6A3E34",
    "bramble_leaf": "#3F4A2F",
    "carcass": "#8C5E4B",
    "heartwood": "#7AA052",
    "moss": "#6B9440",
    "leaf_gold": "#8FAE3A",
    "leaf_green": "#5E9A36",
    "leaf_green_dark": "#467C30",
    "trunk_old": "#6E4A33",
    "stone_moss": "#7D8873",
    "path_earth": "#A88A64",
    "drag_scrape": "#7A6A57",
    "stone_statue": "#9DA394",
    "ivy": "#3E6B37",
    "fey_bark": "#9C8A96",
    "fey_door": "#5E4A5E",
    "window_glow": "#FFD27A",
    "rock_cave": "#6E6A64",
    "cave_dark": "#141210",
    "rock_wet": "#4B4D52",
    "rock_wet_dark": "#35373C",
    "rock_wet_moss": "#56704A",
    "gorge_lane_a": "#4F5155",
    "gorge_lane_b": "#575A5C",
    "gorge_lane_c": "#62655F",
    "gorge_lane_d": "#7B8A66",
    "cocoon": "#E6E1D6",
    "sack": "#D9C9A1",
    "rut": "#B39A70",
    "mill_stone": "#D8CDB8",
    "mill_door": "#5E4330",
    "barn": "#A9553E",
    "withered": "#A8A48E",
    "withered_dark": "#7E7B6C",
    "weed": "#77806A",
    "haunted": "#8C937C",
    "boards": "#8B7A66",
    "roof_old": "#6E5A50",
    "grave": "#A7A69E",
    "crow": "#26262A",
    "rag": "#9C8F7A",
    "window_faint": "#E6D79A",
    "raided": "#94A06A",
    "scorched": "#3B342C",
    "char": "#2E2925",
    "ember": "#E0773A",
    "barn_red": "#B23B2C",
    "barn_brown": "#86603F",
    "barn_grey": "#8F8B82",
    "apple": "#C9302C",
    "orchard_grass": "#7FAE57",
    "green": "#9CCB6E",
    "dead_earth": "#77715F",
    "turf": "#7E9A57",
    "ledge_snow_a": "#A9B8C5",
    "ledge_snow_b": "#BECAD5",
    "ledge_snow_c": "#D3DDE5",
    "ledge_snow_d": "#E5EBF0",
    "snow_ground": "#EEF3F7",
    "snow_light": "#F8FBFD",
    "ice": "#BCDDEB",
    "ice_rock": "#AEBBC6",
    "ice_rock_dark": "#8795A3",
    "print": "#B4C5D3",
    "ledge_ash_a": "#5A565D",
    "ledge_ash_b": "#65616A",
    "ledge_ash_c": "#706C6F",
    "ledge_ash_d": "#777372",
    "ash_ground": "#7C7876",
    "basalt": "#4B4750",
    "basalt_dark": "#35323A",
    "lava": "#F4792A",
    "shrub_red": "#A6372C",
    "ore": "#82E6D8",
    "stone_step": "#C9C2B2",
    "stone_pale": "#D7CFBD",
    "stone_dark": "#7D7768",
    "temple_roof": "#3F7472",
    "temple_roof_dark": "#2F5553",
    "bell": "#B08D3C",
    "herb_a": "#6FA046",
    "herb_b": "#9D84C2",
    "clan_a": "#3F6AA8",
    "clan_b": "#E4D9B8",
    "worn_track": "#C4BC82",
    "felt": "#EDE3CB",
    "felt_dark": "#D9CBA8",
    "camp_earth": "#BDB982",
    "steppe": "#B4B97C",
    "war_earth": "#84795C",
    "rust": "#8E5A3A",
    "shield_wood": "#9C7B52",
    "canvas_dirty": "#BDB19A",
    "grave_mound": "#7E7A58",
    "banner_dark": "#6E3A34",
    "tuft_steppe": "#8E9A5C",
    "stormy": "#8FC4A6",
    "tuft_storm": "#62A488",
    "scorch": "#3C3B38",
    "scorch_rim": "#6F8A7A",
    "scorch_earth": "#4B5550",
    "feather": "#A9B9C6",
    "feather_dark": "#4F6372",
    "mown": "#B9DE8E",
    "lane_mown": "#CDE9A6",
    "arena_sand": "#E4CD97",
    "stand_a": "#9A7450",
    "stand_b": "#86633F",
    "yard_dirt": "#B59A6E",
    "withered_soil": "#6E6A5A",
    "stake": "#9A7A55",
    "banner": "#C23A2E",
    "path_debug": "#E0303A",  # previews only: the path data drawn over a map
    "gate_wood": "#8E4A32",
    "iron": "#8C9196",
    "ribbon_red": "#C8553D",
    "ribbon_white": "#F2E8D5",
    "ribbon_blue": "#5F86C2",
    "slot": "#F6EFE4",
    "backdrop": "#CFE4F2",
    # combat cells
    "cell_grass_a": "#8DBB7A",
    "cell_grass_b": "#96C283",
    "cell_grass_c": "#88B575",
}

# Surfaces the engines treat specially keep their own material; everything else on a piece shares one "kit"
# material and carries its colour in the mesh's vertex colours (COLOR_0 in glTF), so a piece draws in one call.
# hill_grass and highland_grass are the ground of the hills pieces, which cover the base slab: the engine fades
# them toward the neighbours' ground colours like the base slabs' tops.
# lantern, toadstool, fey_mushroom (the fey wood's fairy rings), window_glow (the Fey Court's windows) and
# window_faint (the Abandoned Farmhouse's one lit window, dimmer) glow at night, so the engine needs to find them.
# lava (volcanic cracks, craters, the den) pulses and glows. snow_ground and ash_ground are hills ground, faded like
# hill_grass.
# web (the dark wood's webs) is thin and see-through: its own material blends at WEB_ALPHA, shown from both sides.
SLUM_GROUND = {"tan": ("#CDB48A", "#B59C73", "#A38A63", "#BFA67E"),
               "clay": ("#D2A566", "#BE9458", "#A9804A", "#C69C60"),
               "dun": ("#B9B083", "#A0976A", "#8D8559", "#ABA277")}
PALETTE.update(zip(("mud_ground", "mud_street", "mud_dark", "mud_damp"), SLUM_GROUND[os.environ.get("HEX_SLUM", "tan")]))
OWN_MATERIAL = {"mist_low", "wisp_water", "wisp_pool", "wisp", "wisp_green", "rot_water", "ooze", "ooze_bright", "bayou_water", "window_green", "lantern_red", "water", "water_deep", "water_fast", "water_still", "bog_water", "bog_dark", "toadstool", "lantern", "fey_mushroom", "web", "window_glow", "lava", "snow_ground", "ash_ground",
                "window_faint", "hill_grass", "highland_grass"}

WEB_ALPHA = 0.3

TERRAINS = ["plains", "forest", "farmland", "river", "village", "hills", "swamp", "desert", "ruins"]


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear(name):
    hexcol = PALETTE[name].lstrip("#")
    return [srgb_to_linear(int(hexcol[i:i + 2], 16) / 255) for i in (0, 2, 4)]


def material(name):
    """One flat-colour material per palette entry, made once. "kit" is the shared vertex-colour material."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    if name == "kit":
        mat = bpy.data.materials.new("kit")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        attr = nodes.new("ShaderNodeVertexColor")
        attr.layer_name = "Col"
        mat.node_tree.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.9
        return mat
    rgb = linear(name)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    mat.diffuse_color = (*rgb, 1.0)
    if name == "web":
        bsdf.inputs["Alpha"].default_value = WEB_ALPHA
        mat.surface_render_method = "BLENDED"
        mat.use_backface_culling = False
        mat.diffuse_color = (*rgb, WEB_ALPHA)
    if name == "mist_low":  # its alpha is in the vertex colours, so it fades to nothing at its edge. Colour too: glTF writes the two as one COLOR_0 only when both come from there
        attr = mat.node_tree.nodes.new("ShaderNodeVertexColor")
        attr.layer_name = "Col"
        mat.node_tree.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
        mat.node_tree.links.new(attr.outputs["Alpha"], bsdf.inputs["Alpha"])
        mat.surface_render_method = "BLENDED"
        mat.use_backface_culling = False
        mat.diffuse_color = (*rgb, 0.2)
    return mat


# --- Hex maths -------------------------------------------------------------

def hex_corners(radius, pointy, z=0.0):
    start = 90 if pointy else 0
    return [Vector((radius * math.cos(math.radians(start - 60 * i)),
                    radius * math.sin(math.radians(start - 60 * i)), z)) for i in range(6)]


def edge_normal(i):
    """Unit vector out of a pointy-top tile's edge i. Edge 0 faces +X; i counts anticlockwise in 60 degree steps."""
    a = math.radians(60 * i)
    return Vector((math.cos(a), math.sin(a), 0))


# Axial neighbour offsets for pointy-top tiles, matching edge_normal(i).
NEIGHBOURS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]


def tile_position(q, r):
    """World position of a pointy-top tile at axial (q, r); r grows southward (-Y)."""
    return Vector((2 * TILE_APOTHEM * (q + r / 2), -1.5 * TILE_RADIUS * r, 0))


def cell_position(q, r):
    """World position of a flat-top combat cell at axial (q, r)."""
    return Vector((1.5 * CELL_RADIUS * q, -CELL_FLATS * (r + q / 2), 0))


def in_centre(p, margin=0.0):
    """Inside the centre piece: the inner hexagon whose edges face the tile's edges."""
    return all(p.dot(edge_normal(i)) <= INNER * TILE_APOTHEM - margin for i in range(6))


def in_edge_wedge(p, x0=None, x1=None, margin=0.0, inner=None, side=None):
    """Inside edge 0's wedge (facing +X), between depths x0 and x1 along the edge normal.
    margin keeps clear of the far end (x1); inner and side (default: margin) keep clear of the centre
    piece and of the neighbouring wedges. Pass 0 for those to avoid bare lines between pieces."""
    x0 = INNER * TILE_APOTHEM if x0 is None else x0
    x1 = TILE_APOTHEM if x1 is None else x1
    inner = margin if inner is None else inner
    side = margin if side is None else side
    return (x0 + inner <= p.x <= x1 - margin
            and abs(p.y) <= p.x * math.tan(math.radians(30)) - side / math.cos(math.radians(30)))


def scatter(rng, inside, count, min_dist, bounds, tries=400):
    """Up to `count` points that pass `inside` and stay `min_dist` apart."""
    pts = []
    (x0, x1), (y0, y1) = bounds
    for _ in range(tries):
        if len(pts) >= count:
            break
        p = Vector((rng.uniform(x0, x1), rng.uniform(y0, y1), 0))
        if inside(p) and all((p - q).length >= min_dist for q in pts):
            pts.append(p)
    return pts


WEDGE_BOUNDS = ((INNER * TILE_APOTHEM, TILE_APOTHEM), (-TILE_RADIUS / 2, TILE_RADIUS / 2))
CENTRE_BOUNDS = ((-INNER * TILE_APOTHEM, INNER * TILE_APOTHEM), (-INNER * TILE_RADIUS, INNER * TILE_RADIUS))


def spike_up(piece, at, tip, r, mat_name, segments=4):
    """A thin cone from at to tip, for the ground cover's leaning tufts."""
    d = tip - at
    m = Matrix.Translation(at + d / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    v = bmesh.ops.create_cone(piece.bm, cap_ends=True, cap_tris=True, segments=segments, radius1=r, radius2=0.0,
                              depth=d.length, matrix=m)["verts"]
    piece._paint(v, mat_name)


def yup(v):
    """A point in glTF's Y-up axes, rounded, as the engines read the glb: (x, z, -y)."""
    return [round(v.x, 3) + 0.0, round(v.z, 3) + 0.0, round(-v.y, 3) + 0.0]  # + 0.0 turns -0.0 into 0.0


# --- Geometry builder ------------------------------------------------------

class Piece:
    """Builds one low-poly object out of flat-coloured parts."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.mats = []
        self.surface = set()  # open surfaces built facing up; finish() leaves their normals alone
        self.smooth = set()   # faces to shade smooth (the sand); everything else stays faceted
        # Walkable path centrelines for the engine's routing (design/07 -> Walking): polylines in the piece's own
        # frame, and an optional hub that the engine joins to every wedge path's inner end on the same tile.
        # finish() stores them on the object as glTF extras (Y-up, like the glb); export_gltf.py also writes them
        # to a JSON beside the glb.
        self.paths = []
        self.hub = None
        self.no_cover = []  # (centre, radius): circles the engine's ground cover keeps off (burns, yards, feathers)
        self.spokes = {}  # edge -> polyline: centre paths the engine uses only where that edge's wedge has a path
        self.alpha = {}  # (x, y) -> alpha in the vertex colours, for a material that fades (mist_low)
        self.effects = []  # (kind, point): where the engine adds an effect such as "fire", "smoke" or "crows"

    def _slot(self, mat_name):
        if mat_name not in self.mats:
            self.mats.append(mat_name)
        return self.mats.index(mat_name)

    def _paint(self, verts, mat_name):
        idx = self._slot(mat_name)
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = idx

    def prism(self, outline, z0, z1, mat_name, side_mat=None):
        """Extrude a convex outline (list of XY points, anticlockwise) from z0 up to z1."""
        bm = self.bm
        bottom = [bm.verts.new((p.x, p.y, z0)) for p in outline]
        top = [bm.verts.new((p.x, p.y, z1)) for p in outline]
        top_face = bm.faces.new(top)
        top_face.material_index = self._slot(mat_name)
        bm.faces.new(list(reversed(bottom))).material_index = self._slot(side_mat or mat_name)
        n = len(outline)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((bottom[i], bottom[j], top[j], top[i])).material_index = self._slot(side_mat or mat_name)
        return top_face

    def flat(self, outline, z, mat_name):
        """A thin plate lying on the ground (field strips, water, roads)."""
        return self.prism(outline, 0.0, z, mat_name)

    def cone(self, at, radius, height, mat_name, segments=6, z=0.0, spin=0.0):
        m = Matrix.Translation(at + Vector((0, 0, z + height / 2))) @ Matrix.Rotation(spin, 4, "Z")
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=True, segments=segments,
                                  radius1=radius, radius2=0.0, depth=height, matrix=m)
        self._paint(r["verts"], mat_name)

    def cylinder(self, at, radius, height, mat_name, segments=6, z=0.0):
        m = Matrix.Translation(at + Vector((0, 0, z + height / 2)))
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segments,
                                  radius1=radius, radius2=radius, depth=height, matrix=m)
        self._paint(r["verts"], mat_name)

    def blob(self, at, radius, mat_name, z=0.0, squash=1.0):
        m = Matrix.Translation(at + Vector((0, 0, z))) @ Matrix.Diagonal((1, 1, squash, 1))
        r = bmesh.ops.create_icosphere(self.bm, subdivisions=1, radius=radius, matrix=m)
        self._paint(r["verts"], mat_name)

    def box(self, at, size, mat_name, z=0.0, spin=0.0):
        m = (Matrix.Translation(at + Vector((0, 0, z + size[2] / 2))) @ Matrix.Rotation(spin, 4, "Z")
             @ Matrix.Diagonal((*size, 1)))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        self._paint(r["verts"], mat_name)

    def log(self, at, radius, length, mat_name, spin=0.0, z=None, segments=8):
        """A cylinder lying on its side along direction `spin` (toppled columns)."""
        z = radius if z is None else z
        m = (Matrix.Translation(at + Vector((0, 0, z))) @ Matrix.Rotation(spin, 4, "Z")
             @ Matrix.Rotation(math.pi / 2, 4, "Y"))
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segments,
                                  radius1=radius, radius2=radius, depth=length, matrix=m)
        self._paint(r["verts"], mat_name)

    def box_rot(self, at, size, mat_name, rot):
        """A box centred on `at`, turned by the 3x3 or 4x4 matrix `rot` (sails, ladders, tilted stones)."""
        m = Matrix.Translation(at) @ rot.to_4x4() @ Matrix.Diagonal((*size, 1))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        self._paint(r["verts"], mat_name)

    def gable_roof(self, at, w, d, h, mat_name, z, spin=0.0):
        """A triangular prism roof, ridge along the house's length (w)."""
        rot = Matrix.Rotation(spin, 4, "Z")
        pts = [(-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (w / 2, d / 2, 0), (-w / 2, d / 2, 0),
               (-w / 2, 0, h), (w / 2, 0, h)]
        v = [self.bm.verts.new(at + Vector((0, 0, z)) + rot @ Vector(p)) for p in pts]
        idx = self._slot(mat_name)
        for f in ((v[0], v[3], v[2], v[1]), (v[0], v[1], v[5], v[4]), (v[2], v[3], v[4], v[5]),
                  (v[0], v[4], v[3]), (v[1], v[2], v[5])):
            self.bm.faces.new(f).material_index = idx

    def finish(self, collection, location=(0, 0, 0), merge=True):
        """merge: one shared "kit" material with the colours in vertex colours (see OWN_MATERIAL).
        merge=False keeps one material per colour (the base slabs, whose top the engine recolours)."""
        bmesh.ops.recalc_face_normals(self.bm, faces=[f for f in self.bm.faces if f not in self.surface])
        self.bm.faces.index_update()
        smooth = {f.index for f in self.smooth if f.is_valid}
        mesh = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        if merge and self.mats:
            used = [m for m in self.mats if m in OWN_MATERIAL]
            keep = (["kit"] if any(m not in OWN_MATERIAL for m in self.mats) else []) + used
            colours = mesh.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
            rgba = {m: (*linear(m), 1.0) for m in self.mats}
            for poly in mesh.polygons:
                name = self.mats[poly.material_index]
                for li in poly.loop_indices:
                    colours.data[li].color = rgba[name]
                    if self.alpha:
                        co = mesh.vertices[mesh.loops[li].vertex_index].co
                        colours.data[li].color = (*rgba[name][:3], self.alpha.get((round(co.x, 4), round(co.y, 4)), 1.0))
                poly.material_index = keep.index(name if name in OWN_MATERIAL else "kit")
            self.mats = keep
        for m in self.mats:
            mesh.materials.append(material(m))
        for poly in mesh.polygons:
            poly.use_smooth = poly.index in smooth
        obj = bpy.data.objects.new(self.name, mesh)
        obj.location = location
        if self.paths:
            obj["paths"] = json.dumps([[yup(q) for q in line] for line in self.paths])
        if self.hub is not None:
            obj["path_hub"] = json.dumps(yup(self.hub))
        if self.spokes:
            obj["path_spokes"] = json.dumps({str(i): [yup(q) for q in line] for i, line in self.spokes.items()})
        if self.no_cover:
            obj["no_cover"] = json.dumps([{"at": yup(q), "r": round(r, 3)} for q, r in self.no_cover])
        if self.effects:
            obj["effects"] = json.dumps([{"kind": k, "at": yup(q)} for k, q in self.effects])
        collection.objects.link(obj)
        return obj


# --- Files -----------------------------------------------------------------

ART = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def empty_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def next_number(folder, stem, ext):
    """One past the highest version of stem in folder, counting lettered options, so numbers only go up."""
    pattern = re.compile(rf"{re.escape(stem)}_v(\d+)[a-z]?\.{re.escape(ext)}")
    found = [pattern.fullmatch(name) for name in os.listdir(folder)] if os.path.isdir(folder) else []
    return max((int(m.group(1)) for m in found if m), default=0) + 1


def next_version(folder, stem):
    """Path for the next version, e.g. tiles_v3.blend. Never overwrites an earlier file."""
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{stem}_v{next_number(folder, stem, 'blend')}.blend")


def new_collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def seeded(name):
    return random.Random(name)
