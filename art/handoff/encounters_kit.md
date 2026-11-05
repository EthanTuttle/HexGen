# Map encounter kit hand-off (encounters_v2)

Ethan chose true-scale figures with badges (Nov 4, 2026; design/07): place every scene at scale 1. The oversized look and the measurements for it stay below as the trial's record. The badge look is still being reviewed. The trader, the drinkers, the treasure, the badges and their colours are stand-ins of ours, open to Ethan.

- **Models:** `art/export/encounters.glb` (from `art/encounters/encounters_v2.blend`), the shared `kit` material with vertex colours.
- **Scripts:** `art/scripts/build_encounter_figures.py`, `art/scripts/render_encounter_figures.py`.
- **Previews:** `art/preview/encounters_x<scale>_<light>_<distance>m_v1.png`, `encounters_x1_day_58m_swapped_v1.png` and `encounters_x2.5_day_58m_swapped_v1.png` (wolves in the open, bandits in the forest), `encounters_badges_<light>_58m_v1.png`, `encounters_close_all_v1.png`.

## Pieces

| Piece | What it is | Triangles | Footprint (m) | Height (m) | Largest scale inside a tile |
|---|---|---:|---:|---:|---:|
| `enc_fight_wolves` | two wolves, one elite (the combat minis) | 1,312 | 2.0 x 2.0 | 0.95 | x3.9 |
| `enc_fight_bandits` | melee, ranged, elite (the combat minis) | 1,421 | 2.1 x 1.9 | 1.78 | x3.8 |
| `enc_social_trader` | a trader beside a loaded cart | 320 | 2.9 x 1.1 | 1.81 | x2.7 |
| `enc_social_drinking` | three drinkers at a table, mugs up, a barrel | 814 | 2.3 x 2.0 | 1.38 | x3.3 |
| `enc_discovery_treasure` | a half-dug open chest, earth, a spade | 152 | 1.8 x 1.5 | 1.38 | x4.3 |
| `enc_badge_fight` | crossed swords on red | 220 | 1.0 wide | 1.16 | n/a |
| `enc_badge_social` | speech bubble on teal | 148 | 1.0 wide | 1.16 | n/a |
| `enc_badge_discovery` | sparkle on gold | 172 | 1.0 wide | 1.16 | n/a |

Largest scale: the widest span against the tile's 7.79 m flats.

## Placing them

- **Scenes:** one mesh each, at true mini scale, with the pivot on the ground at its middle. Version B places it at scale 1. Version A is the same mesh at a larger uniform scale, so its triangle count is the same.
- **Trial badge meshes (`enc_badge_*`):** don't use them. They only served the trial, and the badges below replace them.
- **What the trial meshes were:** upright, facing -Y in Blender, with the pivot at the foot and an icon on both faces. The trial renders turn them to the camera and float them 1.6 m wide above the scene. Their icons carry no text. Size on screen is untested in the engine.
- **Materials:** the glb holds `kit` and `kit.001`, one from the minis and one from the new pieces. Both are the same vertex-colour material.
- **In a forest:** trees cover a badge low on the tile. It needs to float above the canopy or be drawn on top (`encounters_badges_night_58m_v1.png` shows the problem).

## On-screen height at the game's map camera

Whole scene, in layout points on the 844 x 390 layout (pitch 50, 50 mm lens). The map opens at 58 m and zooms to 110 m by day and 60 m at night.

| Scene | Scale | 30 m | 40 m | 58 m | 110 m |
|---|---:|---:|---:|---:|---:|
| Wolves | 1 | 65 | 49 | 34 | 18 |
| | 2 | 131 | 98 | 68 | 36 |
| | 2.5 | 165 | 123 | 84 | 44 |
| Bandits | 1 | 77 | 58 | 40 | 21 |
| | 2 | 158 | 117 | 80 | 42 |
| | 2.5 | 199 | 147 | 100 | 52 |
| Drinkers | 1 | 83 | 62 | 42 | 22 |
| | 2 | 169 | 125 | 86 | 45 |
| | 2.5 | 213 | 158 | 108 | 56 |
| Trader | 1 | 73 | 54 | 37 | 20 |
|  | 2 | 150 | 111 | 76 | 39 |
|  | 2.5 | 191 | 140 | 95 | 49 |
| Treasure | 1 | 51 | 38 | 26 | 14 |
| | 2 | 104 | 77 | 53 | 28 |
| | 2.5 | 130 | 97 | 67 | 35 |

These include the ground a scene covers. A single 1.3 m figure is about 17 points tall at 58 m at scale 1, so about 34 at 2 and 43 at 2.5.

## Badges: draw them in the HUD (proposed, under review)

Use a `HexShape` in `explore_hud.gd`'s map markers, not a sprite in the world or a mesh. The `"encounter"` marker there already follows its tile with `unproject_position`, so swap its rounded panel for the hex. That makes a badge unlit and over the trees with no extra work, keeps it sharp at any zoom, and adds no triangles or art files.

`art/scripts/render_encounter_badges.py` paints the stills by these numbers, in layout points on the 844 wide layout, following `HexShape._draw` by hand. Godot hasn't drawn them yet.

| Kind | Face | Edge underneath | Icon | Icon drawn as |
|---|---|---|---|---|
| Fight | `UI.RED` #8E3B2E | `UI.RED_EDGE` #5A2A22 | `UI.WHITE_WARM` #FFF8EE | `swords` (already in `Icons.PATHS`), stroke 2.6 |
| Social | #225C91 | #163E63 (new, ours) | `UI.WHITE_WARM` #FFF8EE | `bubble` (new), `fill = true` |
| Discovery | `UI.GOLD` #E4B54C | `UI.GOLD_EDGE` #A67A1F | `UI.INK` #24302C | `sparkle` (new), `fill = true` |

The rim is `UI.CREAM_LIGHT` #FCF7EE on all three. #225C91 is the app's Rare colour, so it's a proposal, like #163E63.

New icons for `Icons.PATHS`:

```
"bubble": "M7 4h10c2.2 0 4 1.8 4 4v4c0 2.2-1.8 4-4 4h-5l-5 4.5V16c-2.2 0-4-1.8-4-4V8c0-2.2 1.8-4 4-4z",
"sparkle": "M12 2c.8 5.6 3.4 8.2 10 10-6.6 1.8-9.2 4.4-10 10-.8-5.6-3.4-8.2-10-10 6.6-1.8 9.2-4.4 10-10z",
```

Size and fade by camera distance `d`:

```
var w := lerpf(14.0, 22.0, clampf((d - 24.0) / 34.0, 0.0, 1.0))   # steady from 58 m out, 14 at 24 m and closer
var alpha := clampf((d - 18.0) / 12.0, 0.0, 1.0)                  # solid from 30 m out, gone at 18 m
var h := w * 51.0 / 44.0                                          # the app's hex proportions
var inset := maxf(0.75, 0.09 * w)                                 # the rim
var icon_size := 0.62 * w
```

| Camera distance | 110 m | 58 m | 40 m | 30 m | 24 m | 18 m |
|---|---:|---:|---:|---:|---:|---:|
| Badge width (pt) | 22 | 22 | 18 | 15 | 14 | 14 |
| Opacity | 1 | 1 | 1 | 1 | 0.5 | 0 |
| One figure's height (pt) | 9 | 17 | 25 | 33 | 41 | 55 |

- **Build:** `HexShape.make(w, h, rim, face, inset).with_icon(name, ink, icon_size, stroke, fill).with_shadow(edge, 2.0)`, faded with `modulate.a`. Hide it at opacity 0.
- **Anchor:** the tile's scene, 0.35 m above its highest point, unprojected. The badge's lowest point, its edge included, sits 4 points above that, centred.
- **Icon textures:** `UI.icon` makes and keeps a texture for each size, so a size that changes every frame would pile them up. Draw one texture scaled, or step the width to whole points.
- **Input:** leave `mouse_filter` on ignore, so a tap still reaches the tile.
- **Rendered at night:** the same colours, since badges are unlit. Night zoom stops at 60 m, so 110 m is a day view only.
- **Previews:** `art/preview/encounter_badges_map_<light>_<distance>m_v1.png`, the zoom sheets `encounter_badges_zoom_forest_v1.png`, `encounter_badges_zoom_open_v1.png` and `encounter_badges_zoom_forest_held_v1.png`. Each zoom sheet runs 40, 30, 24, 18 and 12 m by day, then 30 m at night. The held sheet is 18 and 12 m.
