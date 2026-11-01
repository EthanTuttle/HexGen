# Plains kit hand-off (tiles_v38)

This kit holds tier 0 plains, rolling meadows with the Nomad Camp (tier 1), steppe/battlefield with the Old Battlefield and stormy plains with the Thunderbird Nest (tier 2), and tourney fields with the Training Grounds (class variant). Everything below can be followed from the repo alone.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v38.blend`.
- **Path data, effect points and no-cover circles:** in the glb as node extras, and in `art/export/tiles_paths.json`.
- **Looks:** `design/07 Presentation.md` → Art direction → Region variant looks and Landmark tiles.
- **Engine rules:** `design/06 Multiplayer & tech.md` → Tile build.
- **Build notes per piece:** `art/README.md` → Units and pieces.
- **Previews:** `art/preview/plains_t0_v1.png`, `plains_meadows_landmark_v4.png`, `plains_nomadcamp_closeup_v4.png`, `plains_t2_steppe_landmark_v3.png`, `plains_t2_oldbattlefield_closeup_v3.png`, `plains_t2_stormy_landmark_v3.png`, `plains_t2_thunderbirdnest_closeup_v3.png`, `plains_t2_tourney_landmark_v2.png`, `plains_t2_traininggrounds_closeup_v3.png`, `plains_t2_tourney_stations_*_v1.png`.

## No trail pieces in this kit

**None of the plains variants has trails or trail pieces**: no `edge_trail`, `edge_trail_in` or `edge_landmark`, and no tracks. They lead the eye by density instead (design/06 → Tile build: not every terrain needs paths), and the party walks its usual curved route. Skip `landmark_flow.trail_edges` for them.

## Pieces

Every piece sits on `base_plains`, with its top recoloured to the ground colour shown. Triangle counts are per piece. Pieces marked "empty" have no triangles; if the node is missing or empty, place nothing.

| Variant / landmark | Ground | Pieces (triangles) |
| --- | --- | --- |
| `plains` (tier 0) | `plains` #A8CF7E | centre 64, centre_b 84, edge_same and edge_other empty |
| `meadows` (tier 1) | `plains` | centre 308, centre_b 192, centre_mid 384, centre_near 784, edge_same and edge_other empty |
| `nomadcamp` (landmark) | `plains` | centre 1,342 |
| `battlefield` (tier 2) | `steppe` #B4B97C | centre 78, centre_b 56, centre_mid 458, centre_near 1,122, edge_same_b 16, edge_same and edge_other empty |
| `oldbattlefield` (landmark) | `steppe` | centre 1,916 |
| `stormy_plains` (tier 2) | `stormy` #8FC4A6 | centre 112, centre_b 64, centre_mid 220, centre_near 440, edge_same and edge_other empty |
| `thunderbirdnest` (landmark) | `stormy` | centre 672 |
| `tourney_fields` (class) | `mown` #B9DE8E | centre 708, centre_b 476, centre_mid 633, centre_near 1,199, edge_other 214, edge_same empty |
| `traininggrounds` (landmark) | `mown` | centre 956 |

All materials are the shared `kit`, with colours in the vertex colours. No piece here has an own material. All four landmarks are a centre piece only (`variants.LANDMARK_CENTRES`): their tile uses its variant's wedges and ground colour (`variants.wedges_of`). The heaviest full tile is the Old Battlefield at 1,916, far under deep forest's 4,816.

## Choosing pieces

Reference: `art/scripts/render_preview.py` → `build_map`, and `art/scripts/landmark_flow.py`.

1. **Density bands:** run `landmark_flow.flow(region, landmark)` once, when the region finishes, using the game's real region tiles. It gives each tile's step distance and toward neighbour.
   - **Distance 1:** `<variant>_centre_near`.
   - **Distance 2:** `<variant>_centre_mid`.
   - **Farther:** the ordinary centres below.
2. **Turning band pieces:** `landmark_flow.toward_edge(tile, toward)` gives the edge the tile's toward step crosses. Turn `centre_near` and `centre_mid` by 60° × that edge. Their props gather on their +X side, so this makes the density lean toward the landmark. It's what makes the flow read: with random turns the bands look evenly spread.
3. **Ordinary centres:** use `<variant>_centre_b` when `hash01(q, r, 13) < 0.5`, else `<variant>_centre`, and turn it by 60° × `int(hash01(q * 31 + 7, r * 17 + 3, 14) * 6)`, as for the farms. This applies to `plains` too, which has no bands.
4. **Edge pieces:** these stay on their own edges, picked by the terrain, as everywhere.
   - **`edge_same`:** empty on every plains variant, because a prop on it would repeat round all six edges and swamp the far tiles.
   - **`battlefield_edge_same_b`:** the one alternate, a broken spear, on a joined edge `i` when `hash01(q * 6 + i, r, 8) < 0.5`. Plains terrain counts as joined with its variants.
   - **`tourney_fields_edge_other`:** a line of bunting along the whole edge, corner to corner, so it runs on round the grounds' edge.
5. **Landmark turn:** as in the forest kit: `landmark_flow.turn(landmark, dist, toward)` turns the landmark's centre piece so its entrance on edge 0 faces the farthest tile's direction. Ties use `hash01(q, r, 10)`.

Everything is fixed once the region finishes, so nothing moves as the map grows.

## Entrances and path data

Every landmark's entrance is on edge 0, with **no drawn approach**: the Nomad Camp's gap between tents, the Old Battlefield's gap in the palisade, the Thunderbird Nest's cleft, the Training Grounds' gate with sand out to the stands' edge. Their `paths` in the data are for the party reaching the entrance, not drawn tracks:

- **Nomad Camp, Old Battlefield:** a line along edge 0's middle (x 1.754 inward) to a ring round the middle.
- **Thunderbird Nest:** the line to the cleft, and a ring round the spire.
- **Training Grounds:** a ring outside the arena (r 2.4) and a spur from it through the gate to the floor.

These don't join anything on the neighbouring tiles, because the variants have no wedge paths. The curved route has to reach them on its own.

## Effects (engine, not in the models)

| Kind or effect | Where |
| --- | --- |
| `fire`, `smoke` (effect points) | the Nomad Camp's central fire |
| `crackle` (effect points; new) | the Thunderbird Nest, faint crackling in the charred logs |
| Lightning strikes on random tiles, gust ripple through the grass | stormy plains (design/07); no drawn storm clouds |

Effect points are in the `effects` list for each piece, as `{"kind": ..., "at": [x, y, z]}` in the piece's own frame (Y-up), and turn with it.

## `art/scripts/ground_cover.py` changes

- **`DENSITY`:**

  | Name | Density |
  | --- | --- |
  | `meadows` | 0.85 (was 0.6) |
  | `nomadcamp` | 0.0 |
  | `battlefield` | 0.22 |
  | `oldbattlefield` | 0.03 |
  | `stormy_plains` | 0.5 |
  | `thunderbirdnest` | 0.1 |
  | `tourney_fields` | 0.05 |
  | `traininggrounds` | 0.0 |

  Every terrain, variant and landmark name needs an entry, or the scatter stops with an error.
- **Meadows flowers:** more of them (`k < 0.3 + 0.85 * drift`) and bigger boxes (0.14 × 0.14 × 0.17), so meadows clearly differ from plain plains.
- **`TUFT`:** `battlefield` and `oldbattlefield` use `tuft_steppe`; `stormy_plains` and `thunderbirdnest` use `tuft_storm`.
- **`NO_FLOWERS`:** adds those four, plus `tourney_fields` and `traininggrounds`.
- **`BENT` (new):** `stormy_plains` and `thunderbirdnest`. Tufts lean hard one way, in one fixed world direction (+X), not per tile, so the wind reads across the region. The engine's gust ripple should match it.
- **`no_cover` (new):** pieces can list circles the ground cover keeps off (`hexkit.Piece.no_cover`), so tufts don't poke through burns, feathers or landmark yards. They're in the node extra `no_cover` and in the `no_cover` list per piece in `tiles_paths.json`, as `{"at": [x, y, z], "r": radius}` in the piece's own frame. Turn them with the piece into world space and pass them as `scatter(terrains, water_shapes, clear)`, where `clear` is `(x, y, radius)` tuples. Used by `nomadcamp`, `oldbattlefield`, `thunderbirdnest` and `stormy_plains`' centres.

## `art/scripts/landmark_flow.py` addition

`toward_edge(tile, toward)` (see Choosing pieces). `flow()`, `turn()` and the rest are unchanged.

## Still not working

- **Not tested in an engine:** `toward_edge`, `centre_mid`, `BENT`, `no_cover` and the `crackle` points haven't been tried in Godot yet.
- **Tourney stations seen end-on:** a station is laid out in one direction and its tile turns, so from a given camera some archery ranges show their butts edge-on. Turning the camera shows them; a row of three still reads as a row.
- **Repeats in big tourney regions:** all tiles at the same distance use one `centre_mid` or `centre_near` piece, so several look alike apart from their turn.
- **Stormy feathers:** small at map zoom.
- **Far steppe tiles:** nearly empty on purpose, so the gradient reads; a lone far tile looks almost plain.
- **Placeholder colours:** `steppe`, `stormy`, `mown` and the prop colours are still placeholders where design/07 doesn't name them.
