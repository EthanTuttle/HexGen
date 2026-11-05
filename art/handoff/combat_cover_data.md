# Combat maps: cover data on line pieces

Which cells or cell edges each map's own fence, barrier, wall and low-edge piece stands on, so the game can apply
[03 → Combat → Cover](../../design/03%20Classes%20%26%20combat.md). The data is in the map JSONs. No meshes changed and the glbs weren't re-exported.

## Where it is

On each `map_<map>_<piece>` placement in `art/export/combat_maps_{farmland,plains,hills,village}.json`:

| Field | Meaning |
|---|---|
| `cover` | `fence` (fence, slum fence, hedge or low monastery garden wall), `barrier` (jousting barrier) or `edge` (plot edge or terrace curb): partial cover. `wall` (town wall or palisade): blocks |
| `cells` | `[[q, r], ...]`: the cells the piece stands on. Gaps and gates aren't listed, so shots pass there |
| `edges` | `[[[q1, r1], [q2, r2]], ...]`: the two cells the piece lies between. Both cells are always on the board |

A piece has either `cells` or `edges`. The `[q, r]` values are axial, as in the map's `cells` list.

## Pieces

| Piece | Maps | Data | Cover |
|---|---|---|---|
| `fence_*` | 12 farmland maps (50 pieces) | cells | fence |
| `barrier_*` | tourney_fields_lists | cells | barrier |
| `palisade_*` | battlefield_palisade | cells | wall |
| `wall_*` | monastery_heights climb, gardens, walled (low garden walls, about 0.54 high) | cells | fence |
| `terrace_curbs`, `plot_edges` | the 4 monastery_heights maps | edges | edge |
| `line_*` | fortified_town (wall), slums_fences (fence), village_gardens (picket fence), scholars_town court and walk (hedge, tagged `fence`) | cells | as shown |
| `wall_to_towers` | fortified_town breach and corner | cells | wall |

- `wall_to_towers` is the short stretch from a wall's end cell to the tower beside it. Its cells are those end cells and the tower cells. All of them already block: the wall's `line_*` and the tower's own `ob_` piece.
- Plot edges along the board's outside edge aren't listed, since no shot crosses them.
- Pieces that aren't covered here: `gates` (open gateways, nothing to block), `quad_joins` (scholars' hedge ends, cloister runs and tower links, on cells whose own pieces already block or give cover), and tracks and plates.

## Scripts

- `art/scripts/cover_data.py` writes the data from each map's plan and checks it. Pass `-- --check` to check only. The check confirms:
  - every listed cell and edge is on the board, and every line piece has data
  - each kind has the right form (`edge` with edges, the rest with cells), and `wall` appears only on fortified_town and battlefield maps
  - each map's plan still matches its JSON's cells
  - each piece's mesh in the latest blend sits on what's listed: every vertex lies near a listed cell or edge, and every listed cell or edge has mesh on it
- The map export (`render_forest_maps.export`) calls `cover_data.annotate`, so a re-export keeps the data. It fails if a line piece is left without data.
- `art/scripts/render_cover_data.py` draws the data over maps seen from above, with a legend: `art/preview/cover_data_v2.png` (farm, walled town, monastery) and `cover_data_v2_monastery.png` (all four monastery maps). v1 is from before the garden walls became partial cover.
