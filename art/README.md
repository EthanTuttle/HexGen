# Prototype art

Art for the Godot and Unity engine prototypes. The decisions behind it (terrains, edge wedges, units, who does what) are in `design/06 Multiplayer & tech.md` → Engine prototype; scale and hex orientation are in `design/07 Presentation.md` → Art direction. Binary files (`.blend`, `.glb`, `.png`) go through Git LFS, so install it before pulling.

| Folder | What's in it |
| --- | --- |
| `scripts/` | Blender Python that builds the first drafts, exports and renders previews; `water.py` and `ground_cover.py` are references the engines copy |
| `tiles/` | Map tile kit, `tiles_vN.blend` |
| `combat/` | Combat cell kit, `combat_cells_vN.blend` |
| `minis/` | Minis (worked on in its own session); `minis/standins/` holds the low-poly stand-ins |
| `export/` | `.glb` files the engines import; always the latest version |
| `preview/` | Rendered test views, `*_vN.png` |

## Running the scripts

Blender is `/Applications/Blender.app/Contents/MacOS/Blender` on the Mac. Run from the repo root:

```bash
# First drafts (each run writes the next _vN.blend and never overwrites one)
Blender -b --factory-startup --python art/scripts/build_tiles.py
Blender -b --factory-startup --python art/scripts/build_combat_cells.py

# Export a kit for the engines (writes art/export/tiles.glb or combat_cells.glb)
Blender -b art/tiles/tiles_v1.blend --python art/scripts/export_gltf.py

Blender -b --factory-startup --python art/scripts/build_standin_minis.py
Blender -b art/minis/standins/standin_minis_v1.blend --python art/scripts/export_gltf.py

# Preview renders of a small map and a combat board, from the latest versions
Blender -b --factory-startup --python art/scripts/render_preview.py

# Stand-in minis: a line-up, on the combat board, and as a party on a map tile
Blender -b --factory-startup --python art/scripts/render_standin_minis.py

# A 6-second video of the map with moving water (add -- --still for one frame)
Blender -b --factory-startup --python art/scripts/render_animation.py
```

## Refining a kit by hand

1. Open the latest `tiles_vN.blend` and **Save As** the next version first (`tiles_v2.blend`), so earlier versions stay for reference.
2. Edit the pieces. Keep each piece's name, keep its origin at the tile centre at ground level, and keep edge pieces facing +X.
3. Run the export on your new version. The engines pick up `art/export/tiles.glb` without any other change.

## Units and pieces

1 unit = 1 metre; Z is up in Blender, and the export turns it Y-up for both engines.

- **Map tile:** pointy-top, 9.0 tall corner to corner, 7.79 wide. Each terrain has four pieces:
  - `base_<terrain>`: the slab, with its ground on top at z = 0 and soil sides down to −0.6. The top is subdivided so the engine's shader can fade the ground colour toward a neighbour's.
  - `<terrain>_centre`: the middle of the tile, inside an inner hexagon reaching 45% of the way to each edge.
  - `<terrain>_edge_same` and `<terrain>_edge_other`: the wedge between the centre and edge 0, which faces +X.
  - `river_corner` (tiles_v2 only): water filling the corner between edge 0 and edge 1. Superseded: water will be drawn by the engines (see Versions).
- **How the engines assemble a tile:** place the base and the centre. For each edge i (0 = +X, counting anticlockwise in 60° steps), place `edge_same` if the neighbour there has the same terrain, otherwise `edge_other`, rotated by 60° × i. Then, for a terrain with a corner piece, for each corner i (between edge i and edge i + 1), place the corner rotated by 60° × i if both of those neighbours have the same terrain. A chain of river tiles stays a narrow river; a clump opens into a lake.
- **Linked terrains and borders (from tiles_v4):** farmland and village count as the same terrain when choosing edge pieces, so a farm track meets a village street. Both have a border on their `edge_other` pieces at the same depth, corner to corner. For each joined edge i, if edge i + 1 isn't joined place `border_join_l`, and if edge i − 1 isn't joined place `border_join_r` (both rotated 60° × i): they carry the border out to the shared edge, where it meets the matching join on the next tile. `BORDER_STYLE` in `scripts/build_tiles.py` picks fence (default), block wall or stacked flat-stone wall. Axial neighbour offsets per edge are in `scripts/hexkit.py` (`NEIGHBOURS`), and `scripts/render_preview.py` does exactly this.
- **Combat cell:** flat-top, spaced 1.0 across the flats, drawn at 0.94 so a thin gap shows. A radius-4 board (61 cells) has a pointy-top outline the size of one map tile. Pieces: `cell_grass_a/b/c`, `cell_tree` (doesn't block), `cell_rock` (blocks).
- **Minis:** about 1.3 tall, on a base that fills one combat cell.
- **Stand-in minis** (`standin_minis_vN.blend`, exported as `export/standin_minis.glb`): super low-poly blockouts (70–290 triangles each) so the engines can test size and movement before the real minis exist. Each stands on a flat-top wooden hex base 0.9 across the flats and 0.08 tall, with a coloured ring and a notch on its front edge; the pivot is the base centre at ground level. They face −Y in Blender, which exports as +Z (glTF front, Unity forward, Godot `MODEL_FRONT`). Pieces: `standin_base` (no figure), `standin_hero` (1.3, sword raised), `standin_chelmsford` (1.3, snout, horns, tail, mace and shield), `standin_small` (1.0, halfling or small elf), `standin_fluffy` (the cat on all fours, about 0.6) and `standin_enemy` (1.3, spear, red ring). Only the 1.3 height comes from the docs; the other heights and the ring colours are test guesses.

Terrains: plains, forest, farmland, river (river/lake) and village, plus (from tiles_v5) hills, swamp, desert and ruins. Colours are the mockup placeholders, set in one table (`PALETTE` in `scripts/hexkit.py`).

- **Hills (from tiles_v5):** a heightfield over the whole tile, cut into the usual centre and edge pieces. Heights depend only on how deep a point is along its edge's normal and how far across the wedge it sits, so pieces meet without gaps however they're turned: the centre is a mound, an `edge_other` wedge slopes down to ground level at the edge (corners are always at ground level), and an `edge_same` wedge adds a ridge that meets the neighbour's at the edge's middle, so joined hills read as a range. Two styles to compare: `hills_*` (raised, smooth slopes) and `hills_terraced_*` (the same heights stepped into ledges with cliff faces). `hills_peak` / `hills_terraced_peak` is the rocky crag on top, placed at the mound's height (`hill_height(0, 0, "centre", style)` in `build_tiles.py`); the preview scales it 0.75 + 0.125 per joined hills neighbour, so peaks grow toward the middle of a range (placeholder rule).
- **Desert (from tiles_v5):** dunes on sand; the `edge_same` dune runs square into the edge's middle and evenly sided there, so it carries on into the next desert tile. `edge_other` has dry scrub, pebbles and patches of cracked hardpan instead of dunes.
- **Swamp (from tiles_v5):** murky pools with mud rims between grassy hummocks, reeds, lilies and dead trees. The `edge_same` piece holds half a pool on the edge's middle, and the neighbour holds the other half. The pools are plates in the kit (`bog_water`), for the engine's still-water shader; they aren't drawn like rivers.
- **Ruins (from tiles_v5):** crumbled stone on grass: a paved square with column stumps and a toppled column in the centre; `edge_same` carries a paved street lined with broken walls to the edge; `edge_other` has a wall stub and rubble. The engine's grass ground cover grows through them.

## Versions

- **tiles_v1:** the first draft; rivers as wide as a tile edge, villages on sand.
- **tiles_v2:** narrow river channels from a small pond, a corner piece that opens clumps into lakes, villages on cobblestone with garden strips at their borders.

- **Water (from map_preview_v4):** drawn per tile by `scripts/water.py`, the reference both engines copy. A tile's river curves, lake shore or pond depend only on which of its six neighbours are water, plus a seed per tile (rules: `design/07 Presentation.md` → Art direction → Water flows freely). Shape code is plain Python (no Blender) so it ports line by line to GDScript or C#; only `add_water()` uses Blender. The river pieces in `tiles_v2.blend` (`river_centre`, `river_edge_*`, `river_corner`) are no longer used; a river tile is just `base_river` plus the drawn water. The ripple, sparkle, foam and depth are left to the engines' water shader.

- **tiles_v5:** hills (raised and terraced), swamp, desert and ruins. Previews: `preview/terrains_raised_v1.png`, `preview/terrains_terraced_v1.png` (`render_preview.py -- --terrains --hills=raised|terraced`).
- **tiles_v4:** farms as four wheat plots (2×2, turned 30°) with dirt paths and tracks; farms link to villages; one wooden fence round farms and villages, with `border_join_l` / `border_join_r` pieces.
- **tiles_v3:** grass tufts and flowers taken out of the plains pieces (now engine ground cover, see below); trees no longer leave bare lines along the borders between a tile's pieces.
- **Ground cover (from map_preview_v5):** scattered by `scripts/ground_cover.py` across the whole map from one world-space pattern: one jittered candidate point per 0.55 m cell, kept if a hash of the cell is below the terrain's density, which fades toward the neighbour's density within 1.6 m of a tile edge. Points in water or on a river bank are skipped. Densities per terrain are placeholders at the top of the file.

Still rough: the preview backdrop renders grey, not the pastel. The real backdrop is the engines' job (time of day).
