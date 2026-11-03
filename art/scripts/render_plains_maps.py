"""Renders the custom plains combat maps from the combat camera with minis on them, and checks each plan. Same plan format,
checks and export as the forest maps (render_forest_maps.py).

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_plains_maps.py
Pass names after -- to render only those maps, --check to run the checks without rendering, --sheets to redo the sheets from
the newest renders, --close for close views of two maps, --kit for the props laid out, and --export for art/combat/combat_maps_plains_vN.blend and
art/export/combat_maps_plains.json. Uses the latest combat_plains, enemy_minis, humanoid_minis and standin_minis.
Writes art/preview/plains_map_<map>_vN.png and the sheets plains_maps_<variant>_vN.png, plains_maps_all_vN.png.

Letters as in render_forest_maps.py (. , c T O R G L B K H ^ / and the minis), plus n bare ground (walkable), and per variant:
  meadows         D herd (3)   N felt tent   P big felt tent (3)   J rug rack   I spirit pole   Y fire
  battlefield     D heap of wreckage (3)   J wreckage   I tattered banner   P collapsed tent (3)   Y row of graves (3 in a line)   L palisade (any line)
  stormy_plains   T split tree   G split trees (2 or 3)   Q rock spire with its nest (7)   L charred trunk (2 or 3 in a line)
  tourney_fields  N pavilion   P big pavilion (3)   Q grand pavilion (7)   D stands (3 in a line)   J archery butt   I dummy
                  Y quintain   L tilt barrier (any line)   seven n cells in a flower get a roped ring

A map's "foes" say which mini w, v and x stand for: samples, as enemy mixes aren't decided. Herds, wreckage and the rest count
as obstacles in the plans, which nobody has decided.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402,F401
from mathutils import Matrix, Vector  # noqa: E402

import build_forest_cells as fc  # noqa: E402
import build_plains_cells as pc  # noqa: E402
import hexkit as hk  # noqa: E402
import map_catalogue as mc  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402

fm.WALKABLE += "n"
LINE_WALLS = {"battlefield", "tourney_fields"}  # L runs along any line of cells in these, and is a fallen trunk elsewhere
BANDITS = {"w": "enemy_bandit_melee", "x": "enemy_bandit_ranged", "v": "enemy_bandit_elite", "W": "enemy_bandit_melee", "X": "enemy_bandit_ranged", "V": "enemy_bandit_elite"}
UNDEAD = {"w": "enemy_skeleton", "x": "enemy_ghost", "v": "enemy_skeleton_elite", "X": "enemy_ghost", "W": "enemy_skeleton"}
TURNED = {"meadows_tents", "battlefield_palisade", "stormy_plains_outcrop", "tourney_fields_lists"}

MAPS = {
    "meadows_herds": {"size": "wide oval", "idea": "Wide open grass with nothing to hide behind but herds, lone trees and drifts of tall flowers. Ranged shine here; the herds are the only walls.", "plan": """
  . . T . . v . .  
 . D . . . . w . . 
. D . . c . . . T .
 . D . . c . . D . 
. . . . . . . x D .
 . . . . D . . D . 
T . c . D . . . c .
 . c . . D . . . . 
. . . . . . T . . .
 . h . . . . . , . 
  k . s . . . T .  """},
    "meadows_rise": {"size": "medium hex", "idea": "A grassy rise in the middle of the meadow, a way up on its north and south. Whoever holds the top looks down on everything; everyone else fights for the steps or goes round.", "foes": BANDITS, "plan": """
    T    
   . .   
  . v .  
 T w . T 
. . ^ . .
 . . . . 
. . X . .
 R H H . 
. H H H .
 . H H R 
. . H . .
 . . . . 
. c ^ c .
 T . . T 
  h . s  
   k .   
    .    """},
    "meadows_tents": {"size": "tall rectangle", "idea": "A long walk up a strip of meadow past outlying tents and rug racks, with a herd at one side. Short walls and no real line: every tent is a corner to step round.", "foes": BANDITS, "plan": """
. . T . .
 I . w . 
. . . . .
 N . v . 
. . . J .
 . x . N 
. . . . .
 D . c . 
D . c . .
 D . . N 
. . . . .
 . J . . 
. N . . .
 . . . I 
. . . . .
 . h k . 
. T s . .
 . . . T """},
    "battlefield_palisade": {"size": "big oval", "idea": "Two old palisade lines across a wide field, their gaps not lined up, with banners, wreckage and a collapsed tent between and behind them. An advance has to zigzag from one breach to the next while ranged shoot along the lines.", "foes": BANDITS, "plan": """
    . . v . w .    
   . , . x . . .   
  . . . . I . . .  
 L L . L L L . L L 
L L L . L L . . L L
 . . . , . . . D . 
. . . . I . J D . .
 . L L L . L L D . 
. . L L . . L L L .
 . c P . . , . . . 
  . P h . k . . .  
   , P s . . J .   
    . . . . . .    """},
    "battlefield_mound": {"size": "small hex", "idea": "A small field with a raised mound in the middle, two stepped ways up its south side, a banner at its foot. Nowhere is far from the top, so the fight is over who stands on it.", "foes": UNDEAD, "plan": """
   .   
  v .  
 w . I 
. . . .
 . H . 
. H H .
 . W . 
. H H .
 ^ H ^ 
. . . .
 . c . 
  h k  
   s   """},
    "battlefield_graves": {"size": "tall rectangle", "idea": "A long narrow stretch of old field, rows of graves running up it in staggered blocks, with banners among them. Easy to walk a lane, slow to change lanes, and the dead can be waiting in any of them.", "foes": UNDEAD, "plan": """
. . v . .
 . w . . 
. . . x .
 . I . . 
. Y . Y .
 . . . . 
. Y . Y .
 . . . . 
. Y . Y .
 . x . . 
. . Y . .
 J . . . 
. . Y . .
 . . . I 
. . Y . .
 . . . . 
. . . . .
 . c . . 
. h . k .
 . s . . 
. . , . .
 . . . . """},
    "stormy_plains_outcrop": {"size": "medium hex", "idea": "A big rock outcrop fills the middle of the map and blocks everything behind it. The fight circles it, with split trees and boulders closing the ring in places.", "plan": """
    .    
   . v   
  T . .  
 . w , . 
. . . . T
 R . . . 
. . K . .
 . K K . 
. . K . .
 . K K . 
. . K . x
 , . . R 
T . . . .
 . c . . 
  . h .  
   k s   
    .    """},
    "stormy_plains_scarp": {"size": "rectangle", "idea": "A cliff at the north with a broad terrace of raised ground under it, stepped down to the burnt field. Enemies hold the terrace; there are two stepped ways up, a long way apart.", "foes": BANDITS, "plan": """
K K K K K K K K K
 K K K K K K K K 
H H H H H . T . .
 H H X H . . x . 
H H W H . . . T .
 H H ^ . . R . . 
^ . . . . . . . .
 . c . T . . T . 
. . . . . , . . .
 . . h . . . T . 
. k . s . . . . .
 T . . . . c . T """},
    "stormy_plains_trunks": {"size": "round oval", "idea": "Lightning has dropped trunks all over a round field, and split trees stand in clumps. Short broken lines everywhere: lots of corners, no long sight lines.", "plan": """
   . v .   
  T . x .  
 . L . . . 
. . L . G .
 . . L . . 
T . . . G .
 . , . w . 
. . O . . T
 . . . L . 
. G . L . .
 G . L . . 
. G . . . T
 . . h . . 
  k . s .  
   . T .   """},
    "tourney_fields_lists": {"size": "tall rectangle", "idea": "Jousting lists: a tilt barrier down the middle with one crossing, and stands closing both sides. Two long lanes side by side; you can see across the barrier but only meet at the gap.", "foes": BANDITS, "plan": """
D . v . D
 w . . x 
D . L . D
 . . . . 
D . L . D
 . , . . 
. . L . .
 Y . . Y 
. . . . .
 . . . . 
D . L . D
 . . . . 
D . L . D
 . . . . 
D . L . D
 . h . . 
. . . k .
 . s . . 
. N . N .
 . . . . """},
    "tourney_fields_camp": {"size": "big oval", "idea": "The knights' camp, spread wide: a grand pavilion with big ones either side wall off the north, and a roped sparring ring stands open on the party's side. Narrow lanes between canvas, an open floor to fall back on.", "foes": BANDITS, "plan": """
    . . v . w . .    
   . . . . . x . .   
  . . T . Q . T . .  
 . . P . Q Q . P . . 
. . P . . Q . . P . .
 . . P . Q Q . P . . 
. . . n . Q . . . N .
 . . n n . . . . . . 
N . . n . . . N . . .
 . . n n . . . . J . 
  . . n . . h . . .  
   . . . . k . s .   
    T . . . . N .    """},
    "tourney_fields_range": {"size": "small rectangle", "idea": "A small archery range: butts side by side at the far end of an open lane, dummies and quintains in rows either side. Cross the open lane, or creep along behind the rows.", "foes": BANDITS, "plan": """
. x . . x .
 . J J J . 
. I . . Y .
 . . w . . 
. I . . Y .
 . . . . . 
. I . . Y .
 . . . . . 
. . . . . .
 . h . k . 
T . s . . N
 . . . . . """},
}


def variant_of(name):
    return next(v for v in pc.VARIANTS if name.startswith(v))


def hk_other_end(anchor, along):
    """The cell at the far end of a line of cells, given the line's vector from this one."""
    q = round(along.x / (1.5 * hk.CELL_RADIUS))
    return anchor[0] + q, anchor[1] + round(-along.y / hk.CELL_FLATS - q / 2)


def line_wall(col, v, group):
    """A palisade or tilt barrier joining touching cells of a line."""
    p = hk.Piece(f"{'palisade' if v == 'battlefield' else 'barrier'}_{min(group)}")
    rng = hk.seeded(p.name)
    for c in sorted(group):
        a = hk.cell_position(*c)
        for dq, dr in fm.NEIGHBOURS[:3]:
            n = (c[0] + dq, c[1] + dr)
            if n in group:
                b = hk.cell_position(*n)
                if v == "battlefield":
                    vr.stakes(p, rng, a, b, 2, h=rng.uniform(0.8, 1.2), r=0.1)
                else:
                    d = b - a
                    p.box((a + b) / 2, (d.length, 0.1, 0.1), "trunk", z=0.86, spin=math.atan2(d.y, d.x))
                    p.box((a + b) / 2, (d.length * 0.94, 0.2, 0.56), "banner" if (c[0] + c[1]) % 2 else "ribbon_blue", z=0.3, spin=math.atan2(d.y, d.x))
        if v == "battlefield":
            vr.stakes(p, rng, a + Vector((-0.15, 0, 0)), a + Vector((0.15, 0, 0)), 1, h=1.05, r=0.1)
        else:
            p.box(a, (0.24, 0.24, 1.0), "trunk")
    p.finish(col)


def track(col, v, cells):
    """A path map's road: a strip joining its bare cells across the gaps between them, so it reads as one road."""
    p = hk.Piece("track")
    for c, mark in cells.items():
        if mark == "n":
            a = hk.cell_position(*c)
            for dq, dr in fm.NEIGHBOURS[:3]:
                n = (c[0] + dq, c[1] + dr)
                if cells.get(n) == "n":
                    b = hk.cell_position(*n)
                    d = b - a
                    p.box((a + b) / 2, (d.length, 0.62, 0.004), f"cell_{v}_track", spin=math.atan2(d.y, d.x))
    p.finish(col)


def build_map(t, col, name):
    return build_from_plan(t, col, name, MAPS[name], variant_of(name), pc.KIT[variant_of(name)], line_wall, LINE_WALLS, {"battlefield": "J"})


def build_from_plan(t, col, name, m, v, kit, wall, wall_variants, free_turn):
    """Builds one map from its plan and a kit. wall makes L in wall_variants; free_turn: for each variant, single props that may turn."""
    cells = fm.parse(m["plan"])
    fm.check_reach(name, m, cells)
    p = hk.Piece("plate")
    fc.plate(p, cells)
    p.finish(col)
    for c, mark in cells.items():
        n = rb.hash_cell(c)
        if mark == "c":
            piece = f"cell_{v}_brush"
        elif mark == ",":
            piece = f"cell_{v}_litter"
        elif mark == "n":
            piece = f"cell_{v}_bare"
        elif mark == "R":
            piece = f"cell_{v}_block_{'ab'[n % 2]}"
        elif mark in fm.RAMPS:
            continue
        elif mark in "BKLOQDNPJIY" or mark == "G":
            piece = f"cell_{v}_floor"
        elif mark == "T":
            piece = f"cell_{v}_floor" if v == "stormy_plains" else f"cell_{v}_cover"
        else:
            piece = f"cell_{v}_ground_{'abc'[(c[0] - c[1]) % 3]}"
        rp.place(t, piece, col, hk.cell_position(*c) + Vector((0, 0, fm.ground_z(mark))), math.radians(60 * (n % 6)) if mark in "R,c" or v == "meadows" else 0.0)
    k = 0
    for c, mark in cells.items():
        turn = math.radians(60 * (rb.hash_cell(c) % 6))
        if mark == "T":
            rp.place(t, f"ob_{v}_{kit['T'][0]}" if "T" in kit else f"ob_{v}_tree_{'abc'[k % 3]}", col, hk.cell_position(*c), turn)
            k += 1
        elif mark == "O":
            rp.place(t, f"ob_{v}_stump", col, hk.cell_position(*c), turn)
        elif mark in kit and len(kit[mark][1]) == 1:
            # Tents, pavilions and props keep their doors and faces to the south; heaps can turn.
            rp.place(t, f"ob_{v}_{kit[mark][0]}", col, hk.cell_position(*c), turn if mark in free_turn.get(v, "") else 0.0)
    for mark, group in fm.groups(cells, "BG" + "".join(m_ for m_, s in kit.items() if len(s[1]) > 1)):
        if mark == "B":
            piece, foot = f"ob_{v}_boulder_3", fc.TRIANGLE
        elif mark == "G":
            piece, foot = f"ob_{v}_grove_{len(group)}", {2: fc.LINE2, 3: fc.TRIANGLE}[len(group)]
        else:
            piece, foot = f"ob_{v}_{kit[mark][0]}", kit[mark][1]
        anchor, turn = fm.fit(group, foot)
        if v == "tourney_fields" and mark == "D":  # stands face into the map: their back, on the piece's +side, away from its middle
            along = Matrix.Rotation(math.radians(60 * turn), 3, "Z") @ (hk.cell_position(*foot[-1]) - hk.cell_position(*foot[0]))
            mid = fm.middle_of(group)
            if Vector((-along.y, along.x, 0)).dot(fm.middle_of(cells) - mid) > 0:
                anchor, turn = hk_other_end(anchor, along), (turn + 3) % 6
        rp.place(t, piece, col, hk.cell_position(*anchor), math.radians(60 * turn))
    for _, group in fm.groups(cells, "L"):
        if v in wall_variants:
            wall(col, v, group)
        else:
            anchor, turn = fm.fit(group, {2: fc.LINE2, 3: fc.LINE3}[len(group)])
            rp.place(t, f"ob_{v}_log_{len(group)}", col, hk.cell_position(*anchor), math.radians(60 * turn))
    if m.get("kind") == "path":
        track(col, v, cells)
    for mark, group in fm.groups(cells, "K"):
        fm.shaped_piece(col, v, group, mark)
    for _, group in fm.groups({c: "H" for c, mark in cells.items() if mark in fm.RAISED}, "H"):
        fm.raised_piece(col, v, group, cells)
    for c, mark in cells.items():
        if mark in fm.RAMPS:
            fm.ramp_piece(col, v, cells, c)
    fm.notched_cells(t, col, v, cells)
    for _, group in fm.groups(cells, "n"):
        if v == "tourney_fields" and len(group) == 7:
            rp.place(t, "tourney_fields_ring", col, fm.middle_of(group))
    return cells


def templates():
    t = {}
    for folder, stem in (("combat", "combat_plains"), (os.path.join("minis", "enemies"), "enemy_minis"), (os.path.join("minis", "enemies"), "humanoid_minis"),
                         (os.path.join("minis", "standins"), "standin_minis")):
        t.update(rp.load_templates(rp.latest(folder, stem)))
    return t


def make_sheets():
    for v in pc.VARIANTS:
        fm.sheet([f"plains_map_{n}" for n in MAPS if n.startswith(v)], f"plains_maps_{v}")
    fm.sheet([f"plains_map_{n}_turned" for n in MAPS if n in TURNED], "plains_maps_turned", 2)
    fm.sheet([f"plains_map_{n}" for n in MAPS], "plains_maps_all", 3)


def kit_sheet(t, col):
    """Every prop by variant, on its cells, beside a hero for size."""
    for row, v in enumerate(pc.VARIANTS):
        x, y = -13.5, 7.0 * (1.5 - row)
        kinds = [(k, cells) for k, cells, _ in pc.KIT[v].values()] + [("boulder_3", fc.TRIANGLE), ("grove_3", fc.TRIANGLE), ("log_3", fc.LINE3)]
        for kind, foot in kinds:
            at = Vector((x, y, 0))
            for q, r in foot:
                rp.place(t, f"cell_{v}_floor", col, at + hk.cell_position(q, r))
            rp.place(t, f"ob_{v}_{kind}", col, at)
            x += 3.0 + 1.0 * (len(foot) > 3)
        rp.place(t, "standin_hero", col, Vector((x, y, 0)), rb.FACE_NORTH + 0.5)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only_check = "--check" in args
    if "--sheets" in args:
        make_sheets()
        sys.exit()
    if "--close" in args:
        names = [a for a in args if not a.startswith("--")]
        for name, at, dist in (("battlefield_graves", (3.46, -4.5), 11), ("tourney_fields_lists", (3.46, -7.5), 12)):
            if names and name not in names:
                continue
            hk.empty_scene()
            col = hk.new_collection("map")
            t = templates()
            cells = build_map(t, col, name)
            fm.place_minis(t, col, MAPS[name], cells)
            rp.stage(Vector((at[0], at[1], 0.4)), dist, fm.PITCH)
            rp.render(f"plains_close_{name}")
        sys.exit()
    if "--export" in args:
        fm.export(MAPS, build_map, templates, variant_of, "combat_maps_plains")
        sys.exit()
    if "--kit" in args:
        hk.empty_scene()
        kit_sheet(templates(), hk.new_collection("kit"))
        rp.stage(Vector((-0.5, -0.3, 0.6)), 92, fm.PITCH, lens=100)
        rp.render("plains_obstacles")
        sys.exit()
    wanted = [a for a in args if not a.startswith("--")] or list(MAPS)
    failed = []
    for name in wanted:
        hk.empty_scene()
        col = hk.new_collection("map")
        t = templates()
        cells = build_map(t, col, name)
        if not fm.visibility(name, cells):
            failed.append(name)
        without = fm.triangles(col)
        fm.place_minis(t, col, MAPS[name], cells)
        print(f"TRIS {name}: map {without}, with minis {fm.triangles(col)}")
        if not only_check:
            target, distance = fm.framing(cells)
            rp.stage(target, distance, fm.PITCH)
            rp.render(f"plains_map_{name}")
            mc.keep_image("plains_map_", name)
            if name in TURNED:
                rb.turn_camera(180, target)
                rp.render(f"plains_map_{name}_turned")
    if not only_check and wanted == list(MAPS):
        make_sheets()
    if not only_check:
        mc.write()
    print("TOO HIDDEN" if failed else "ALL CELLS SEEN", failed)
