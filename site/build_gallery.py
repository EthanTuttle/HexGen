#!/usr/bin/env python3
"""Builds site/gallery.js, the data behind the showcase page.

Run from anywhere:  python3 site/build_gallery.py

What goes in:
- Approved art: every file in an "approved" row of art/reviews.md that exists on disk.
- Evolution: for each approved render, the earlier versions of the same view
  (same name without _vN), oldest first, with Ethan's notes from reviews.md.
- Combat maps: the in-use maps from art/combat/maps/README.md, with their tactical idea.
- Game screenshots: every image in site/shots/ (copied from Godot runs).

site/picks.json lets you hand-tune it: featured files, hidden files, and titles.
Thumbnails (site/thumbs/, not committed) are made with sips, so this needs a Mac.
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
THUMBS = SITE / "thumbs"
IMAGE = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO = {".mp4"}

# First keyword match wins; anything else counts as the map.
SECTIONS = [
    ("minis", ("beast", "hero", "golem", "pose_check", "minis", "giant", "enemy")),
    ("places", ("place_", "town_", "household", "weizenhof", "monto", "shack", "start_tiles")),
    ("combat", ("_maps_", "village_map_", "combat", "_close", "lane", "ramp", "landing", "allround",
                "ways_up", "cover_data", "crop_")),
]


def section_of(name):
    for section, keys in SECTIONS:
        if any(k in name for k in keys):
            return section
    return "map"


def stem_of(name):
    """oasis_map_v4.png -> oasis_map"""
    return re.sub(r"_v\d+$", "", Path(name).stem)


def version_of(name):
    m = re.search(r"_v(\d+)$", Path(name).stem)
    return int(m.group(1)) if m else 0


# Render-name words that say how a shot was taken, not what it shows.
SHOT_WORDS = {"map", "maps", "all", "sheet", "close", "wide", "solo", "compare", "beside", "tile",
              "day", "none", "kit", "shot", "front", "study", "baked", "x1", "58m", "r3", "b", "c", "a"}


def title_of(name):
    words = stem_of(name).split("_")
    before_after = "before" in words and "after" in words
    words = [w for w in words if w not in SHOT_WORDS | {"before", "after"}] or words[:1]
    if words[0] == "village" and len(words) > 1:
        words = words[1:]
    if words[0] in ("place", "household") and len(words) > 1:
        words = words[1:]
    words = [w for i, w in enumerate(words) if i == 0 or w != words[i - 1]]
    text = " ".join(words)
    text = text[:1].upper() + text[1:]
    return text + (" (before and after)" if before_after else "")


def added_dates():
    """Commit date each file was first added, so versions sort by when they were made."""
    out = subprocess.run(
        ["git", "log", "--diff-filter=A", "--name-only", "--format=@%as", "--",
         "art/preview", "art/combat/maps"],
        cwd=ROOT, capture_output=True, text=True).stdout
    dates, current = {}, None
    for line in out.splitlines():
        if line.startswith("@"):
            current = line[1:]
        elif line.strip():
            dates[line.strip()] = current  # git log is newest first; keep the oldest add
    return dates


def review_rows():
    rows = []
    for line in (ROOT / "art/reviews.md").read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[2] not in ("approved", "rejected"):
            continue
        date, files, verdict, note = cells
        paths, folder = [], None
        for f in re.findall(r"`([^`]+)`", files):
            if "/" in f:
                folder = str(Path(f).parent)
            elif folder:
                f = f"{folder}/{f}"
            else:
                continue
            paths.append(f)
        rows.append({"date": date, "files": paths, "verdict": verdict, "note": note})
    return rows


def thumb(rel):
    """Makes a 900px JPEG beside the page; returns its path relative to site/."""
    src = ROOT / rel
    out = THUMBS / (rel.replace("/", "__").rsplit(".", 1)[0] + ".jpg")
    if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "78",
                        "-Z", "900", str(src), "--out", str(out)],
                       capture_output=True)
    return str(out.relative_to(SITE)) if out.exists() else "../" + rel


def entry(rel, **extra):
    kind = "video" if Path(rel).suffix.lower() in VIDEO else "image"
    item = {"src": "../" + rel, "kind": kind, "title": title_of(rel)}
    if kind == "image":
        item["thumb"] = thumb(rel)
    item.update(extra)
    return item


def combat_maps():
    """In-use maps from the combat map catalogue, grouped by terrain and variant."""
    text = (ROOT / "art/combat/maps/README.md").read_text()
    terrain = variant = None
    maps = []
    for line in text.splitlines():
        if line.startswith("## "):
            terrain = line[3:].strip()
        elif line.startswith("### "):
            variant = line[4:].strip()
        elif line.startswith("| `"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            map_id, status, idea = cells[0].strip("`"), cells[1], cells[4]
            rel = f"art/combat/maps/{map_id}.png"
            if status == "in use" and (ROOT / rel).exists():
                maps.append(entry(rel, title=title_of(map_id), terrain=terrain,
                                  variant=variant, note=idea))
    return maps


def main():
    picks = json.loads((SITE / "picks.json").read_text())
    hidden = set(picks.get("hide", []))
    titles = picks.get("titles", {})
    dates = added_dates()
    rows = review_rows()

    notes = {}  # file -> (verdict, date, note)
    for r in rows:
        for f in r["files"]:
            notes[f] = (r["verdict"], r["date"], r["note"])

    approved, seen = [], set()
    for r in rows:
        if r["verdict"] != "approved":
            continue
        for f in r["files"]:
            if f in seen or f in hidden or not (ROOT / f).exists():
                continue
            if Path(f).suffix.lower() not in IMAGE | VIDEO:
                continue
            seen.add(f)
            approved.append(entry(f, date=r["date"], note=r["note"],
                                  section=section_of(Path(f).name),
                                  title=titles.get(f, title_of(f))))

    # Evolution: earlier versions of an approved view, if at least two exist.
    evolution, done = [], set()
    preview = ROOT / "art/preview"
    for item in reversed(approved):  # newest approval of a view wins
        rel = item["src"][3:]
        if not rel.startswith("art/preview/") or item["kind"] != "image":
            continue
        stem = stem_of(rel)
        if stem in done:
            continue
        done.add(stem)
        versions = [p for p in preview.glob(f"{Path(stem).name}_v*.png")
                    if stem_of(p.name) == Path(stem).name]
        if len(versions) < 3:
            continue
        rels = sorted((f"art/preview/{p.name}" for p in versions),
                      key=lambda r: (dates.get(r, "9999"), version_of(r)))
        rels = rels[: rels.index(rel) + 1] if rel in rels else rels
        if len(rels) < 3:
            continue
        # Keep the first, the last and up to three in between.
        if len(rels) > 5:
            step = (len(rels) - 1) / 4
            rels = [rels[round(i * step)] for i in range(5)]
        steps = []
        for s in rels:
            verdict, date, note = notes.get(s, (None, dates.get(s), ""))
            steps.append(entry(s, date=date, verdict=verdict or "", note=note,
                               version=version_of(s)))
        evolution.insert(0, {"title": item["title"], "section": item["section"], "steps": steps})

    # Two views can share a title (beast_wolf and beast_wolf_solo); keep the longer story.
    by_title = {}
    for evo in evolution:
        if len(evo["steps"]) > len(by_title.get(evo["title"], {"steps": []})["steps"]):
            by_title[evo["title"]] = evo
    evolution = [e for e in evolution if by_title.get(e["title"]) is e]

    shots = []
    for p in sorted((SITE / "shots").glob("*")):
        if p.suffix.lower() in IMAGE | VIDEO:
            rel = str(p.relative_to(ROOT))
            shots.append(entry(rel, title=titles.get(rel, title_of(p.name))))

    featured = [entry(f, title=titles.get(f, title_of(f))) for f in picks.get("featured", [])
                if (ROOT / f).exists()]

    data = {"featured": featured, "approved": approved, "evolution": evolution,
            "combatMaps": combat_maps(), "shots": shots}
    (SITE / "gallery.js").write_text(
        "// Generated by build_gallery.py; don't edit by hand.\nwindow.GALLERY = "
        + json.dumps(data, indent=1) + ";\n")
    print(f"{len(approved)} approved, {len(evolution)} evolutions, "
          f"{len(data['combatMaps'])} combat maps, {len(shots)} shots, {len(featured)} featured")


if __name__ == "__main__":
    main()
