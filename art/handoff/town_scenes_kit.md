# Town scenes kit hand-off (town_scenes_v2)

The first playable's town square and inn interior, for `TownScene._frame`. **Not yet approved; not yet tried in Godot.** Looks: `design/07` → Town scenes, Town screen. Plan: `mockups/town/Town-v9-SwapDetails`.

- **Models:** `art/export/town_scenes.glb`, from `art/town/town_scenes_v2.blend`. Load with `Kit.meshes("res://art/town_scenes.glb")`, as `EncounterView` loads its kit: meshes `town_square` and `town_inn`, at scale 1, in Blender's frame turned Y-up by the export.
- **Data:** `art/export/town_scenes.json`: every hex's middle, the party's spots, the keepers and where the services stand.
- **Scripts:** `art/scripts/build_town_scenes.py`, `art/scripts/render_town_scenes.py` (`-- check` runs the checks). **Previews:** `art/preview/town_kit_{square,inn}_{day,night}_v2.png`, `town_kit_sheet_v2.png`.

**Triangles:** square 8,316, inn 6,524, both before minis. There's no agreed budget for a scene: I used 20,000 as a placeholder, about four map tiles. Godot should measure on a phone with the party on.

## Godot must do these

1. **Show a scene on its own**, away from the map, as the map isn't drawn behind it. Hexes are 1.1 from middle to corner, so a mini stands as it does on a fight's cell, only with more room.
2. **Camera:** previews hold on (0.3, 0.75, 0.6) (Blender's X, Y, Z) from 21 m at a 42° pitch, 50 mm. The usual scene camera controls can then turn it. Backs of houses and walls aren't dressed, so turn with care: see Not checked.
3. **Backdrop:** the inn on a flat dark warm #2A1C15 at any hour (Ethan). The square on the map's day-and-night backdrop.
4. **Own materials:** `ts_glow` (windows, lamps, candles), `ts_fire` and `ts_fire_b` (the hearth), `ts_water` (the well). Previews give the glows emission 0.4 by day in the square, 0.9 in the inn, and 1.6 at night (all placeholders). A slow flicker on the fire would help.
5. **Add the lights,** which aren't in the glb. All warm and placeholder, as Blender point lights:

| Where | Colour | Blender energy, day / night |
| --- | --- | --- |
| Inn: hearth, 0.5 out from its hex's middle, 0.9 up | #FF8C40 | 55 / 75 |
| Inn: over each table's hex, 1.2 up | #FFC27A | 8 / 16 |
| Inn: back wall, (0, -2) and (2, -2), +0.3, +0.9, 1.5 up | #FFC27A | 8 / 16 |
| Square, night only: by (-1, -1) and (2, 0), 1.8 up, and the inn's door, 0.9 up | #FFC27A | 32 |

Blender's energy isn't Godot's: match by eye against the previews.

6. **Inn windows at night:** `ts_win_day` is a plain lit colour in the kit, #9FC4DC. Previews darken it at night. If it isn't worth an own material, leave it.

## The plan

Axial hexes as in Town v9: `hex(q, r) = (2 * 0.9526 * (q + r / 2), -1.65 * r)`, with r growing toward the camera. The JSON holds them worked out. The floor's top is at 0.03: stand minis there.

**The floor runs on past the 19 hexes** (Ethan): everything in a scene stands on a hex, nothing on the backdrop. The party's spots stay on the 19. The check fails if anything stands off the floor.

**Square:** well (0, 0), stall (-1, 0), quest board post (1, 0), inn at the back (1, -2). Round them, houses, a far tower, a cart, a tree, bunting, barrels and lamps, all on the floor past the 19 hexes or at their back edge. Each service card matches its place, as v3a.

**Inn:** bar along (0, -2) to (2, -2) with the innkeeper behind it (Ethan), tables (0, 0) and (2, 0), hearth (-2, 1), rug by the fire, stair to the rooms on the right.

**Party spots** (`spots` in the JSON), checked clear of anything standing: nearest 0.42 or more.

| Scene | Set | Hexes | From v9? |
| --- | --- | --- | --- |
| Square | `none` | (0,1) (-1,1) (1,1) (0,2) | Same |
| Square | `shop` | (-1,1) (-2,1) (0,1) (-2,2) | Same |
| Square | `board` | (1,1) (2,0) (0,1) (1,2) | Same |
| Square | `inn` | (1,-1) (0,-1) (2,-1) (-1,-1) | **Changed:** v9's last spot, (0,0), is the well |
| Inn | `seats` | (1,0) (0,1) (-1,1) (1,-1) | Same |
| Inn | `waiting` | (1,1) (2,-1) (-1,0) (0,2) (-2,2) | Same |

**Keepers** (`keepers`): `[q, r, y offset, x offset]` from the hex's middle. Previews use a stand-in mini. **Changed from v9:** the innkeeper is on (1, -2), behind the bar, not (0, -1).

**Moved from v9:** houses that sat on (-2, 1), (-2, 2), (0, -2), (2, -2) and the tree on (2, -1) now stand off or behind those hexes, so all can be stood on. The icons on the mockup's hexes aren't here: the props are the place.

## Not checked

- Nothing has run in Godot.
- Turned cameras: previews only show the front. Behind the square's back row and outside the inn's walls is plain.
- Rest's night fall isn't a separate look: it's the night lighting above.
- Other kinds of town (design/07 wants their own scene each): this is the market town.
