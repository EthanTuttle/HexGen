# Prototype art

Art for the Godot and Unity engine prototypes. The decisions behind it (terrains, edge wedges, units, who does what) are in `design/06 Multiplayer & tech.md` → Engine prototype; scale and hex orientation are in `design/07 Presentation.md` → Art direction. Binary files (`.blend`, `.glb`, `.png`) go through Git LFS, so install it before pulling.

| Folder | What's in it |
| --- | --- |
| `scripts/` | Blender Python that builds the first drafts, exports and renders previews |
| `tiles/` | Map tile kit, `tiles_vN.blend` |
| `combat/` | Combat cell kit, `combat_cells_vN.blend` |
| `minis/` | Minis (worked on in its own session) |
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

# Preview renders of a small map and a combat board, from the latest versions
Blender -b --factory-startup --python art/scripts/render_preview.py
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
- **How the engines assemble a tile:** place the base and the centre. For each edge i (0 = +X, counting anticlockwise in 60° steps), place `edge_same` if the neighbour there has the same terrain, otherwise `edge_other`, rotated by 60° × i. Axial neighbour offsets per edge are in `scripts/hexkit.py` (`NEIGHBOURS`), and `scripts/render_preview.py` does exactly this.
- **Combat cell:** flat-top, spaced 1.0 across the flats, drawn at 0.94 so a thin gap shows. A radius-4 board (61 cells) has a pointy-top outline the size of one map tile. Pieces: `cell_grass_a/b/c`, `cell_tree` (doesn't block), `cell_rock` (blocks).
- **Minis:** about 1.3 tall, on a base that fills one combat cell.

Terrains: plains, forest, farmland, river (river/lake) and village. Colours are the mockup placeholders, set in one table (`PALETTE` in `scripts/hexkit.py`).

## Known rough edges in the v1 drafts

- Rivers are as wide as a tile edge, so a chain reads as a broad channel more than a river. A narrow river needs pieces that know about both neighbours at a corner.
- The village ground is the mockup's sand colour; Dorfromantik puts houses on grass.
- The preview backdrop renders grey, not the pastel. The real backdrop is the engines' job (time of day).
