"""Cover data for the combat maps' own line pieces: which cells or cell edges each fence, barrier, wall or low edge stands on,
so the game can apply 03 → Combat → Cover. Data only: no mesh changes.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/cover_data.py [-- --check]
Reads each map's plan from its render script, writes the fields onto the map_ placements in art/export/combat_maps_*.json
(farmland, plains, hills, village), then checks them. --check only checks. fm.export calls annotate() too, so a re-export keeps them.

On a placement:
  "cover"  fence (a fence, slum fence, hedge or low monastery garden wall: partial), barrier (jousting barrier: partial), edge
           (plot edge or terrace curb: partial) or wall (town wall or palisade: blocks)
  "cells"  [[q, r], ...] for a piece standing on whole cells: a line's L cells; its gaps and gates are left out
  "edges"  [[[q1, r1], [q2, r2]], ...] for a piece along cell edges: the two cells it lies between, both on the board
The checks: every listed cell or edge is on the board, every line piece has data, the plan still matches the JSON's cells, and
the piece's mesh in the latest blend sits on what's listed (every vertex near a listed cell or edge, every cell or edge reached).
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexkit as hk  # noqa: E402

NEIGHBOURS = hk.NEIGHBOURS
FAMILIES = {"farmland": "render_farmland_maps", "plains": "render_plains_maps", "hills": "render_hills_maps", "village": "render_village_maps"}
LINE_KIND = {"farmland": "fence", "haunted_homesteads": "fence", "raided_farms": "fence", "windmill_country": "fence", "cider_orchards": "fence",
             "battlefield": "wall", "tourney_fields": "barrier", "monastery_heights": "fence",
             "fortified_town": "wall", "village": "fence", "slums": "fence", "scholars_town": "fence"}
PREFIX = {"battlefield": "palisade", "tourney_fields": "barrier", "monastery_heights": "wall", **{v: "line" for v in ("fortified_town", "village", "slums", "scholars_town")}}  # as each line_wall names its piece
LINE_PREFIX = ("fence_", "barrier_", "palisade_", "line_", "wall_")


def line_groups(marks):
    """Touching L cells, each set keyed by its smallest cell, as the line pieces are named."""
    groups, seen = {}, set()
    for c in sorted(marks):
        if marks[c] == "L" and c not in seen:
            group, todo = {c}, [c]
            while todo:
                a = todo.pop()
                for dq, dr in NEIGHBOURS:
                    n = (a[0] + dq, a[1] + dr)
                    if marks.get(n) == "L" and n not in group:
                        group.add(n)
                        todo.append(n)
            seen |= group
            groups[min(group)] = group
    return groups


def edge(a, b):
    return sorted([list(a), list(b)])


def pieces(name, variant, marks, z):
    """{piece suffix: fields} for a map: marks {(q, r): mark} from its plan, z {(q, r): height}."""
    out = {}
    if variant not in LINE_KIND:  # elsewhere a line is logs, rocks or a fissure: ob_ pieces with footprints, or not cover
        return out
    for anchor, group in line_groups(marks).items():
        out[f"{PREFIX.get(variant, 'fence')}_{anchor[0]}_{anchor[1]}"] = {"cover": LINE_KIND[variant], "cells": sorted(list(c) for c in group)}
    if variant == "fortified_town":  # the stretch from a wall's end cell to the tower beside it: both cells already block
        cells = {c for c, m in marks.items() if m == "L" and any(marks.get((c[0] + dq, c[1] + dr)) == "N" for dq, dr in NEIGHBOURS)}
        cells |= {(c[0] + dq, c[1] + dr) for c in set(cells) for dq, dr in NEIGHBOURS if marks.get((c[0] + dq, c[1] + dr)) == "N"}
        if cells:
            out["wall_to_towers"] = {"cover": "wall", "cells": sorted(list(c) for c in cells)}
    if variant == "monastery_heights":  # as render_hills_maps.terrace_curbs and plot_edges draw them; edges off the board are left out
        curbs, plots = set(), set()
        for c in marks:
            for dq, dr in NEIGHBOURS:
                n = (c[0] + dq, c[1] + dr)
                if n in marks and z.get(c, 0) - z.get(n, 0) > 0.4:
                    curbs.add(tuple(map(tuple, edge(c, n))))
                if marks[c] == "c" and n in marks and marks[n] != "c":
                    plots.add(tuple(map(tuple, edge(c, n))))
        out["terrace_curbs"] = {"cover": "edge", "edges": [[list(a), list(b)] for a, b in sorted(curbs)]}
        out["plot_edges"] = {"cover": "edge", "edges": [[list(a), list(b)] for a, b in sorted(plots)]}
    return out


def is_line(suffix):
    return suffix.startswith(LINE_PREFIX) or suffix in ("wall_to_towers", "terrace_curbs", "plot_edges")


def annotate(name, entry, marks):
    """Puts the cover fields onto entry's map_ placements. Returns the suffixes of line pieces left without data."""
    z = {(row["q"], row["r"]): row.get("z", 0) for row in entry["cells"]}
    found = pieces(name, entry["variant"], marks, z)
    missing = []
    for p in entry["placements"]:
        suffix = p["piece"][len(f"map_{name}_"):]
        if not p["piece"].startswith(f"map_{name}_") or not is_line(suffix):
            continue
        for k in ("cover", "cells", "edges"):
            p.pop(k, None)
        if suffix in found and entry["variant"] in LINE_KIND:
            p.update(found[suffix])
        else:
            missing.append(suffix)
    return missing


def check(name, entry):
    """Problems with a map's cover data: off the board, not touching, or a line piece without data."""
    board = {(row["q"], row["r"]) for row in entry["cells"]}
    bad = []
    for p in entry["placements"]:
        suffix = p["piece"][len(f"map_{name}_"):]
        if not is_line(suffix):
            continue
        if "cover" not in p or not (p.get("cells") or p.get("edges")):
            bad.append(f"{p['piece']}: no data")
            continue
        if p["cover"] not in ("fence", "barrier", "edge", "wall") or ("edges" in p) != (p["cover"] == "edge"):
            bad.append(f"{p['piece']}: cover {p['cover']} with {'edges' if 'edges' in p else 'cells'}")
        if p["cover"] == "wall" and entry["variant"] not in ("fortified_town", "battlefield"):  # only town walls and palisades block
            bad.append(f"{p['piece']}: wall on {entry['variant']}")
        for c in p.get("cells", []):
            if tuple(c) not in board:
                bad.append(f"{p['piece']}: cell {c} off the board")
        for a, b in p.get("edges", []):
            if tuple(a) not in board or tuple(b) not in board:
                bad.append(f"{p['piece']}: edge {a}-{b} off the board")
            if (b[0] - a[0], b[1] - a[1]) not in NEIGHBOURS:
                bad.append(f"{p['piece']}: edge {a}-{b} between cells that don't touch")
    return bad


def segment(a, b):
    """The edge between two touching cells, as its two corners."""
    ca, cb = hk.cell_position(*a).xy, hk.cell_position(*b).xy
    mid, along = (ca + cb) / 2, (cb - ca).normalized().orthogonal() * hk.CELL_RADIUS / 2
    return mid - along, mid + along


def dist(q, s):
    d = s[1] - s[0]
    t = max(0.0, min(1.0, (q - s[0]).dot(d) / d.length_squared))
    return (q - (s[0] + d * t)).length


def mesh_check(name, entry, objects):
    """Every vertex of each piece near a listed cell (inside its hex, with a little give) or edge, and every listed one reached."""
    bad = []
    board = {(row["q"], row["r"]) for row in entry["cells"]}
    for p in entry["placements"]:
        if "cover" not in p:
            continue
        ob = objects.get(p["piece"])
        if ob is None:
            bad.append(f"{p['piece']}: not in the blend")
            continue
        pts = [(ob.matrix_world @ v.co).xy for v in ob.data.vertices]
        if "cells" in p:
            centres = [hk.cell_position(*c).xy for c in p["cells"]]
            far = [q for q in pts if min((q - c).length for c in centres) > hk.CELL_RADIUS + 0.2]
            unreached = [cell for cell, c in zip(p["cells"], centres) if min((q - c).length for q in pts) > 0.3]
        else:
            segs = [segment(a, b) for a, b in p["edges"]]
            border = [segment(c, (c[0] + dq, c[1] + dr)) for c in board for dq, dr in NEIGHBOURS if (c[0] + dq, c[1] + dr) not in board]
            faces = [(ob.matrix_world @ f.center).xy for f in ob.data.polygons]  # a rail's long faces sit on its edge's middle
            far = [q for q in pts if min(dist(q, s) for s in segs) > 0.12 and min(dist(q, s) for s in border) > 0.12]  # plot edges on the board's outside edge aren't listed
            unreached = [e for e, s in zip(p["edges"], segs) if min(((q - (s[0] + s[1]) / 2).length for q in faces)) > 0.12]
        if far:
            bad.append(f"{p['piece']}: {len(far)} of {len(pts)} vertices away from what's listed, e.g. {tuple(round(x, 2) for x in far[0])}")
        if unreached:
            bad.append(f"{p['piece']}: no mesh at {unreached[:4]}")
    return bad


def run(write):
    import importlib

    import bpy
    import render_forest_maps as fm
    import render_preview as rp
    report, problems = [], []
    for family, module in FAMILIES.items():
        mod = importlib.import_module(module)
        path = os.path.join(hk.ART, "export", f"combat_maps_{family}.json")
        data = json.load(open(path))
        blend = rp.latest("combat", f"combat_maps_{family}")
        with bpy.data.libraries.load(blend) as (src, dst):
            dst.objects = [n for n in src.objects if any(n.startswith(f"map_{m}_") for m in data)]
        objects = {o.name: o for o in dst.objects if o is not None}
        for name, entry in data.items():
            marks = fm.parse(mod.MAPS[name]["plan"])
            kinds = {(row["q"], row["r"]) for row in entry["cells"]}
            if kinds != set(marks):
                problems.append(f"{name}: the plan no longer matches the JSON's cells")
                continue
            missing = annotate(name, entry, marks) if write else []
            problems += [f"{name}: {s} has no data" for s in missing]
            problems += check(name, entry) + mesh_check(name, entry, objects)
            got = [p for p in entry["placements"] if "cover" in p]
            if got:
                report.append((family, name, [(p["piece"][len(f"map_{name}_"):], p["cover"], len(p.get("cells", p.get("edges", []))), "cells" if "cells" in p else "edges") for p in got]))
        if write:
            with open(path, "w") as f:
                json.dump(data, f, separators=(",", ":"), sort_keys=True)  # as fm.export writes it
                f.write("\n")
    for family, name, rows in report:
        print("COVER", family, name, "; ".join(f"{s} {k} {n} {how}" for s, k, n, how in rows))
    print("COVERPIECES", sum(len(r) for _, _, r in report), "on", len(report), "maps")
    for p in problems:
        print("COVERPROBLEM", p)
    print("COVERPROBLEMS", len(problems))


if __name__ == "__main__":
    run(write="--check" not in sys.argv)
