# Place scenes kit hand-off

One scene kit per place you enter (design/07 → Town screen → Each place gets its own scene). Each one is a copy of the market square's kit (`town_scenes_kit.md`), with the same 19-hex board and rules: everything stands on a floor hex, the party's spots are checked clear, and the backs aren't dressed. Godot's `PlaceStage` loads a kit by its line in `Places.KITS`, so a new kit needs no code.

**Status:** fortified town v1, made Nov 10, 2026, waiting on Ethan's review. Not in Godot yet.

## What each kit hands Godot

- **Model:** `art/export/place_<id>.glb` is one mesh, `place_<id>`, at scale 1. It's exported from `art/places/place_<id>_vN.blend` with `export_gltf.py`.
- **Data:** `art/export/place_<id>.json` has the same keys as `town_scenes.json`:
  - `hexes`: the 19 hexes' middles.
  - `spots` and `keepers`, keyed by `<id>`.
  - `<id>_places`: where the services stand.
  - `backdrop`: `""` means the map's day and night.
  - `lights`: `[q, r, x, y, z, colour, day, night, flicker]`. The offsets are from that hex's middle in Godot's frame, the energies are in Blender watts, and 0 means off.
- **Own materials:** `ts_glow` (windows), `ts_water` (the well). The braziers' embers are the kit's plain `ember` colour.
- **Scripts:**
  - `art/scripts/build_place_<id>.py` builds a kit.
  - `art/scripts/render_place_scenes.py -- <id>` renders the previews. `-- <id> check` runs the checks: everything stands on the floor, every spot is clear by 0.42 or more, and the triangles are within budget. It exits 1 on a failure.
- **Previews:** `art/preview/place_<id>_{day,night}_none_vN.png`, `_day_shop_`, `_day_board_` (at the town kit's 21 m preview camera) and `_wide_` (at PlaceStage's 33 m), plus `place_<id>_sheet_vN.png`.

## Fortified town (`fortified_town`, v1)

**Look:** grey flagstones and stone houses under slate. The town wall runs down both sides, with towers and the garrison's red banners on its inner face. The Keep, the town's landmark, stands over the back of the square with its gate toward it (Ethan, Nov 9, 2026: a town variant's landmark is part of its square). It's the village kit's Keep at 1.15×. From the 21 m preview camera only its gatehouse shows, but from PlaceStage's 33 m it shows whole.

**Services:** the same places and spot sets as the market square, so the party's moves are the same. The props are new looks on the same pieces.

| Place | Hex | Here |
| --- | --- | --- |
| `well` | (0, 0) | Stone well under slate |
| `shop` | (-1, 0) | The armourer's stall: red-and-cream awning, metal goods, with spears, shields on a rail and arrows beside it. The shopkeeper stands behind it, as in the square |
| `board` | (1, 0) | The militia's notice board, under slate |
| `inn` | (1, -2) | The market square's inn in stone and slate, with the inn's blue sign. It opens the shared `town_inn` |
| `keep` | (0, -5) | The Keep's gate, off the 19 hexes, for reference only: there's no card for it yet |

**Spots** are the square's: `none`, `shop`, `board`, `inn`, on the same hexes (`town_scenes_kit.md` → Party spots). The nearest anything stands to a spot is 0.44, at (2, 0), from the brazier.

**Props reused:**
- From `variants.py` (the village kit): `keep`, `stone_wall`, `wall_tower`, `fort_banner`, and `spear_rack` through `yard_spears`.
- From `build_village_cells.py`: `yard_shields`, `yard_armour`, `yard_arrows`, `yard_brazier`, `bale`.
- From the town kit: the well, stall, board, inn, houses, cart and barrels, with their colours swapped to stone and slate.
- Nothing new was modelled.

**Lights** (all placeholders, warm, at night only; they're also in the JSON):
- the two braziers by the stall and the board: #FF9A4A, 34 W, flicker;
- the inn's door: #FFC27A, 32 W;
- the Keep's gate: #FF9A4A, 40 W, flicker.

**Triangles:** 11,455 of the placeholder 20,000.

## Not checked

- Nothing has run in Godot.
- Turned cameras: behind the back row and outside the walls is plain.
- No guard minis: the only keeper is the shopkeeper. Guards would be keeper-style stand-ins, and aren't in the kit.
