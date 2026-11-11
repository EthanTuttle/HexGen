# Place scenes kit hand-off

One scene kit per place you enter (design/07 → Town screen → Each place gets its own scene). Each one is a copy of the market square's kit (`town_scenes_kit.md`), with the same 19-hex board and rules: everything stands on a floor hex, the party's spots are checked clear, and the backs aren't dressed. Godot's `PlaceStage` loads a kit by its line in `Places.KITS`, so a new kit needs no code.

**Status:** fortified town v4, approved by Ethan on Nov 10, 2026, and on main. Slums v1, approved by Ethan on Nov 10, 2026, and on main. Scholars' town v2, made Nov 10, 2026, waiting on Ethan's review (v1 wasn't quite right). None is in Godot yet.

## What each kit hands Godot

- **Model:** `art/export/place_<id>.glb` is one mesh, `place_<id>`, at scale 1. It's exported from `art/places/place_<id>_vN.blend` with `export_gltf.py`.
- **Data:** `art/export/place_<id>.json` has the same keys as `town_scenes.json`:
  - `hexes`: the 19 hexes' middles.
  - `spots` and `keepers`, keyed by `<id>`.
  - `<id>_places`: where the services stand.
  - `backdrop`: `""` means the map's day and night.
  - `lights`: `[q, r, x, y, z, colour, day, night, flicker]`. The offsets are from that hex's middle in Godot's frame, the energies are in Blender watts, and 0 means off.
- **Own materials:** `ts_glow` (windows, and the scholars' town's lantern pillars), `ts_water` (the well, and the scholars' town's fountains), `ts_fire` (the fortified town's brazier flames, so Godot flickers them). The slums' red lanterns are the village kit's `lantern_red`, which PlaceStage doesn't glow yet. The red light comes from the kit's lamps.
- **Scripts:**
  - `art/scripts/build_place_<id>.py` builds a kit.
  - `art/scripts/render_place_scenes.py -- <id>` renders the previews. `-- <id> check` runs the checks: everything stands on the floor, every spot is clear by 0.42 or more, and the triangles are within budget. It exits 1 on a failure.
- **Previews:** `art/preview/place_<id>_{day,night}_none_vN.png`, `_day_shop_`, `_day_board_` (at the town kit's 21 m preview camera) and `_wide_` (at PlaceStage's 33 m), plus `place_<id>_sheet_vN.png`.

## Fortified town (`fortified_town`, v4)

**Look:** grey flagstones and stone houses under slate. The town wall runs down both sides, with towers and the garrison's red banners on its inner face. The Keep, the town's landmark, stands over the back of the square (Ethan, Nov 9, 2026: a town variant's landmark is part of its square). Its gate faces a lane between the left back house and the inn, with braziers at the lane's mouth.

**Scale** (v2 and v3, Ethan: in v1 the Keep and houses were too small next to the party). Everything is sized against the 1.3 m minis:
- **Houses:** the market square's townhouses at 1.75×, with doors and windows to match. Their walls are 1.9–2.6 m.
- **Inn:** 2×.
- **Town wall:** 1.45×.
- **The Keep:** 2.4×, close behind the inn, with towers about 7.5 m tall (Ethan, Nov 10, 2026: v3's layout at v2's size).
  - From PlaceStage's 33 m view only its gatehouse wall and a banner show over the inn. The towers and battlements are out of frame.
  - Aiming the camera higher would show more of it. That's a Godot choice.
  - Earlier takes: v2 had it at 2.4× and further back; v3 at 1.9×, close.

**Services:** the same places and spot sets as the market square, so the party's moves are the same. The props are new looks on the same pieces.

| Place | Hex | Here |
| --- | --- | --- |
| `well` | (0, 0) | Stone well under slate |
| `shop` | (-1, 0) | The armourer's stall: red-and-cream awning, metal goods, with spears, shields on a rail and arrows beside it. The shopkeeper stands behind it, as in the square |
| `board` | (1, 0) | The militia's notice board, under slate |
| `inn` | (1, -2) | The market square's inn in stone and slate, with the inn's blue sign. It opens the shared `town_inn` |
| `keep` | (0, -5) | The Keep's gate, off the 19 hexes, for reference only: there's no card for it yet |

**Spots** are the square's: `none`, `shop`, `board`, `inn`, on the same hexes (`town_scenes_kit.md` → Party spots). The nearest anything stands to a spot is 0.44, at (2, 0), from the brazier. Every other spot is clear by 0.85 or more.

**Props reused:**
- From `variants.py` (the village kit): `keep`, `stone_wall`, `wall_tower`, `fort_banner`, and `spear_rack` through `yard_spears`.
- From `build_village_cells.py`: `yard_shields`, `yard_armour`, `yard_arrows`, `yard_brazier`, `bale`.
- From the town kit: the well, stall, board, inn, houses, cart and barrels, with their colours swapped to stone and slate.
- Nothing new was modelled.

**Lights** (all placeholders, warm, at night only; they're also in the JSON):
- the brazier at the lane's mouth and the one by the board: #FF9A4A, 34 W, flicker (the third brazier is unlit);
- the inn's door: #FFC27A, 32 W;
- the Keep's gate: #FF9A4A, 40 W, flicker.

**Triangles:** 16,274 of the placeholder 20,000.

## Slums (`slums`, v1)

**Look** (07 → Region variants → Slums):
- Lopsided, patched shacks with sagging tin roofs on warm tan dirt, with faint damp patches.
- Around the square's edges: weeds, two vegetable plots, scraggly trees, heaps of crates with a broken cart, and barrels.
- A washing line across the Black Market's lane, and red lanterns on posts.

The Black Market, the town's landmark, stands over the back of the square: its tangle of patched awnings over a narrow lane, with red lanterns under them. The lane's mouth opens between the left back shack and the inn, where the fortified town's lane to the Keep is. The town kit's chimney smoke isn't in the kit: a place kit has no effect points yet.

**Scale:** as the fortified town's. The shacks are the village kit's at 3×, with a door and one lit window each added; their walls are 1.7–2.2 m. The inn is 2×, junk, plots and weeds 2×, the Black Market 2.4×, and the trees 2.4×. Like the Keep, the Black Market is cropped above its lower awnings at 33 m.

**Services:** the same places and spot sets as the market square and the fortified town.

| Place | Hex | Here |
| --- | --- | --- |
| `well` | (0, 0) | Wooden well under tin |
| `shop` | (-1, 0) | A stall under red-and-ochre patched cloth; the shopkeeper stands behind it |
| `board` | (1, 0) | The notice board under tin |
| `inn` | (1, -2) | The market square's inn in weathered planks under tin. It opens the shared `town_inn` |
| `black_market` | (0, -3) | The Black Market's lane mouth, off the 19 hexes, for reference only: there's no card for it yet |

**Spots** are the square's. The nearest anything stands to a spot is 0.87, at (1, -1), from the inn.

**Props reused:**
- From `variants.py` (the village kit): `shack`, `black_market`, `washing_line`, `lantern_post`, `junk`, `weed_patch`, `veg_plot`, `scraggly_tree`.
- From the town kit: the well, stall, board, inn and barrels.
- Nothing new was modelled.

**Lights** (placeholders, at night only, none flickering):
- the two red lantern posts: #E5432D, 30 W;
- the inn's door: #FFC27A, 32 W;
- the Black Market's lane: #E5432D, 44 W.

**Triangles:** 14,458 of the placeholder 20,000.

## Scholars' town (`scholars_town`, v2)

**v2** (Ethan on v1: "isn't quite right", so it was rebuilt to read like the approved map tile, `village_scholars_map_v8.png` from tiles_v75, and the scholars' combat maps). v1 was a generic square with houses.

**Look** (07 → Region variants → Scholars' town):
- **Spoke walks** of pale paving run along the hex grid's three lines through the middle, out to the scene's edges and up to the inn's door. Every other hex is mown lawn.
- **The great fountain** stands at the middle, where the walks meet. It stands for the well (the `well` place, on the same hex).
- **Four lawn quads** lie between the side walks, each edged in a waist-high clipped hedge along its walk. The two back quads are wrapped in a cream hall, a cloister arcade and a tower. The left one holds a small fountain and a lawn panel; the right one a scholar's statue and a bench.
- **The front quads** hold a little roofed stage for players on the right, and the founder's statue on the left, with a tower in each.
- **Lantern pillars** stand at the walks' ends. The two at the College walk's foot and by the board are lit.
- There are no row houses. More halls and towers stand out behind.

The College, the town's landmark, stands over the back of the square on its own paved hex: its domed hall with a colonnaded front, cloister and performers' stage. Its walk runs up the grid's line from the middle, between the left back hall and the inn, lined with clipped hedges and a scholar's statue each side (07 → College's flow). From PlaceStage's 33 m view, its colonnade and pediment show over the inn, with the dome out of frame.

**Scale:** as the fortified town's. The halls are the village kit's at 2.3× (walls 2.1–2.6 m), the towers 2.4× (about 4.5 m to the roof), and the arcades 3.4× (columns about 2 m). The great fountain is 2×, the inn 2×, the hedges, benches, lawns, statues and small fountain 2.2×, the founder's statue 1.5×, the stage 1.35×, and the College 2.4×.

**Services:** the same places and spot sets as the market square.

| Place | Hex | Here |
| --- | --- | --- |
| `well` | (0, 0) | The great fountain where the walks meet |
| `shop` | (-1, 0) | A stall under blue-and-cream stripes; the shopkeeper stands behind it |
| `board` | (1, 0) | The notice board under slate blue |
| `inn` | (1, -2) | The market square's inn in cream stone under slate blue. It opens the shared `town_inn` |
| `college` | (0, -3) | The College's walk, off the 19 hexes, for reference only: there's no card for it yet |

**Spots** are the square's. Some stand on lawn hexes, as in the combat maps. The nearest anything stands to a spot is 0.69, at (2, 0), from the lantern pillar; the fountain leaves its ring of spots 0.79.

**Props reused:**
- From `variants.py` (the village kit): `great_fountain`, `fountain`, `cloister_run`, `scholar_house`, `quad_tower`, `college`, `clipped_hedge`, `scholar_statue`, `great_statue`, `quad_bench`, `lawn_panel`, `bandstand`, `lantern_pillar`. Their `window_glow` and `lantern` become `ts_glow`, and their `water` becomes `ts_water`.
- From the town kit: the stall, board and inn.
- Nothing new was modelled.

**Lights** (placeholders, warm, at night only, none flickering):
- the two lit lantern pillars: #FFD27A, 28 W;
- the inn's door: #FFC27A, 32 W;
- the College's front: #FFD27A, 44 W.

**Triangles:** 11,202 of the placeholder 20,000.

**Comparison:** `art/preview/place_scholars_town_compare_v2.png` puts v2 (21 m and 33 m) beside the map tile and the approved court combat map.

## Not checked

- Nothing has run in Godot.
- Turned cameras: behind the back row and outside the walls (fortified) or past the outer shacks and halls (slums, scholars' town) is plain.
- No guard minis: the only keeper is the shopkeeper. Guards would be keeper-style stand-ins, and aren't in the kit.
