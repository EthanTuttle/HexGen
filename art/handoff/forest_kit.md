# Forest kit hand-off (tiles_v23)

This kit holds the forest tier 2 variants, deep forest's flow pieces, and the four forest landmarks. Ethan approved it on Nov 1, 2026. Everything below can be followed from the repo alone.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v23.blend`.
- **Looks:** `design/07 Presentation.md` → Art direction → Region variant looks and Landmark tiles.
- **Engine rules:** `design/06 Multiplayer & tech.md` → Tile build.
- **Build notes per piece:** `art/README.md` → Units and pieces.
- **Previews:** `art/preview/*_landmark_v3.png`, plus the round 5 forest previews `art/preview/*_v5.png`.

## Pieces

Every piece sits on `base_forest`, with its top recoloured to the ground colour shown. Triangle counts are per piece.

| Variant / landmark | Ground colour | Pieces (triangles) |
| --- | --- | --- |
| `fey_wood` | `fey_wood` #5C9270 | `fey_wood_centre` 392, `fey_wood_centre_near` 708, `fey_wood_edge_same` 380, `fey_wood_edge_other` 212, `fey_wood_edge_trail` 584 |
| `dark_wood` | `dark_wood` #5B5F4F | `dark_wood_centre` 493, `dark_wood_centre_near` 532, `dark_wood_edge_same` 593, `dark_wood_edge_other` 534, `dark_wood_edge_trail` 507 |
| `deep_forest` (tier 1, now with flow pieces) | `deep_forest` #466F47 | `deep_forest_centre` 448, `deep_forest_centre_near` 368, `deep_forest_edge_same` 728, `deep_forest_edge_other` 448, `deep_forest_edge_trail` 584 |
| `heartwood` | `heartwood` #7AA052 | `heartwood_centre` 870, `heartwood_edge_same` 540, `heartwood_edge_same_b` 580, `heartwood_edge_other` 540, `heartwood_edge_trail` 688, `heartwood_edge_landmark` 632 (no near centre) |
| `treeoflife` (heartwood's landmark) | `heartwood` | `treeoflife_centre` 2,666, `treeoflife_edge_trail` 204, `treeoflife_edge_same` 164, `treeoflife_edge_other` 164 |
| `hiddenshrine` (deep forest's landmark) | `deep_forest` | `hiddenshrine_centre` 704, `hiddenshrine_edge_trail` 708, `hiddenshrine_edge_same` 616, `hiddenshrine_edge_other` 336 |
| `feycourt` (fey wood's landmark) | `fey_wood` | `feycourt_centre` 820 only; its tile uses fey wood's wedges |
| `spidernest` (dark wood's landmark) | `dark_wood` | `spidernest_centre` 935 only; its tile uses dark wood's wedges |

Every full tile is under deep forest's 4,816 triangles. For example, a full heartwood tile is 4,110, and the Tree of Life with six trail edges is 3,890.

## Materials of their own

Every other surface shares the `kit` material, with its colour in the vertex colours (COLOR_0). The list is `OWN_MATERIAL` in `art/scripts/hexkit.py`.

| Material | Used on | Engine needs |
| --- | --- | --- |
| `fey_mushroom` | fairy rings, trail stepping caps, the Fey Court's stair | night glow |
| `window_glow` | the Fey Court's windows and the light over its door | night glow (warm light inside) |
| `lantern` | the Tree of Life's crown, cords and entrance posts | night glow |
| `web` | dark wood's and the Spider Nest's webs | transparent: blended, alpha 0.3 (`WEB_ALPHA`), double-sided |

## Engine effects (not in the models)

- **Fey wood:** drifting motes of light.
- **Heartwood and the Tree of Life:** light shafts and floating seeds.
- **Hidden Shrine:** a shaft of light on its clearing (the clearing is left open for it).
- **Night glow:** on `fey_mushroom`, `window_glow` and `lantern`.

## Choosing pieces

Reference: `art/scripts/render_preview.py` → `build_map`, and `art/scripts/landmark_flow.py`. Edge `i` of tile `(q, r)` touches `(q, r) + NEIGHBOURS[i]` (`hexkit.NEIGHBOURS`). Wedges are placed turned by 60°·i.

1. **Normal tile:** a centre piece, plus a wedge per edge: `edge_same` toward the same terrain (a variant or landmark counts as its terrain), `edge_other` toward anything else.
2. **Alternate wedge:** where `<variant>_edge_same_b` exists (only heartwood has one), a joined edge `i` uses it when `hash01(q * 6 + i, r, 8) < 0.5` (`hash01` is in `art/scripts/ground_cover.py`).
3. **Landmark tiles:**
   - The Fey Court and the Spider Nest (`variants.LANDMARK_CENTRES`) are a centre piece only. Their tile uses the variant's wedges and ground colour (`variants.wedges_of`).
   - The Tree of Life and the Hidden Shrine have their own wedges.
   - `variants.LANDMARKS` maps each landmark to its variant.
4. **Trails:** run `landmark_flow.flow(region, landmark)` once, when the region finishes, using the game's real region tiles (the landmark included).
   - **What `flow()` does:** a breadth-first walk from the landmark gives each tile its step distance. Each other tile's "toward" neighbour is a region neighbour one step closer, with ties broken by `hash01(q, r, 9)`.
   - **Trail edges:** `trail_edges(tile, toward)` lists them. An edge is a trail edge when either tile's toward step crosses it.
   - **Which wedge:** on a trail edge, use `<landmark>_edge_trail` if the tile is a landmark with its own trail wedge, else `<variant>_edge_trail`.
   - **Next to the Tree of Life:** a heartwood tile's edge touching it uses `heartwood_edge_landmark` instead of its trail wedge. The Tree's roots and the path carry on there.
   - **Near centres:** tiles at distance 1 use `<variant>_centre_near` where it exists.
5. **Landmark turn:** `landmark_flow.turn(landmark, dist, toward)` returns how many 60° steps to turn the landmark's centre piece, anticlockwise, the way edge numbers go.
   - **The rule:** every landmark piece has its entrance on edge 0, and the turn makes it face the edge where the trail from the farthest tile arrives. Ties between equally far tiles are broken by `hash01(q, r, 10)`.
   - **Only the centre turns:** the wedges stay on their own edges, so the entrance edge always gets a trail wedge.
   - **Roots:** the Tree of Life's roots cross every edge at the same mirrored spot (y = ±0.65 from the edge's middle, radius 0.11, height 0.06), so they still meet after the turn.
   - **Regions with only the landmark:** `turn()` returns 0.

All of this is fixed once the region finishes, so nothing moves as the map grows.

## `art/scripts/landmark_flow.py` (new reference script)

Plain Python for the engine to copy, like `ground_cover.py`. It has three functions:
- `flow(region, landmark)` → `(dist, toward)`
- `trail_edges(tile, toward)` → the trail edges of a tile
- `turn(landmark, dist, toward)` → the landmark's turn in 60° steps

## `art/scripts/ground_cover.py` changes

- **`DENSITY` entries:**

  | Name | Density |
  | --- | --- |
  | `fey_wood` | 0.18 |
  | `dark_wood` | 0.05 |
  | `heartwood` | 0.12 |
  | `treeoflife` | 0.1 |
  | `hiddenshrine` | 0.08 |
  | `feycourt` | 0.18 |
  | `spidernest` | 0.05 |

  Every terrain, variant and landmark name needs an entry, or the scatter stops with an error.
- **`TUFT`:** `dark_wood` and `spidernest` use `tuft_dark_wood` (#53574A); everything else uses `grass_ink`.
- **`NO_FLOWERS`:** `dark_wood` and `spidernest` get tufts or pebbles instead of flowers.
- **`tuft_colour()`:** within `BLEND` of an edge whose neighbour has another tuft colour, some tufts take the neighbour's colour, up to half right at the edge (hash stream 5). The tuft colours mix across the border like the ground colour fade.

## Still not working

- **Not tested in an engine:** the `web` transparency, the alternate wedge, the trail rule and the landmark turn haven't been tried in Godot yet.
- **Heartwood's paths:** they show between the gates, but the crowns still cover parts of them from the 45° camera. At map zoom the gates do most of the work.
- **Regions in the preview:** `render_preview.py` treats each region as the connected group of the variant's tiles. The game should pass its real region tiles to `flow()`.
- **Regions with only the landmark:** the landmark faces edge 0, with nothing choosing that direction on purpose.
- **Heartwood's triangles:** heartwood is the heaviest forest variant. Its centre near the Tree of Life with trail edges stays under deep forest's count, but it has the least headroom if the phone budget tightens.
