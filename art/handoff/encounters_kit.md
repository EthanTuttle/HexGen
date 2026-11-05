# Map encounter trial kit hand-off (encounters_v2)

A small test set for comparing two looks of map encounters (design/02 and design/07). Nothing ships from it yet, and nothing here decides between them. The trader, the drinkers, the treasure, the badges and their colours are stand-ins of ours, open to Ethan.

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
- **Badges:** upright, facing -Y in Blender, with the pivot at the foot and an icon on both faces. The trial renders turn them to the camera and float them 1.6 m wide above the scene. Their icons carry no text. Size on screen is untested in the engine.
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
