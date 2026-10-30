# HexGen · Unity engine prototype

The Unity half of the engine prototype (`design/06 Multiplayer & tech.md` → Engine prototype). It covers look tests 1–3 so far: the map board with edge blending, the pastel backdrop and light changing with the time of day, and stand-in minis on the map and on a combat board with the attack hop and recoil. Look test 4 (the exploration and combat UI from the mockups) isn't started.

Unity 6000.6.7f1, URP (the Universal 3D template), glTFast 6.20.0, the new Input System.

## Running it

- **Editor:** open `unity/` with Unity 6000.6.7f1, open `Assets/Scenes/Prototype.unity`, press Play. The first time the editor loads, `HexGen > Sync art from art/export` runs by itself and copies `art/export/*.glb` into `Assets/Resources/Art/`. That folder is gitignored: `art/` stays the source of truth, and a re-export there is picked up the next time the editor loads (or from the menu).
- **macOS build:** `HexGen > Build for macOS` writes `unity/Builds/HexGen Unity prototype.app` (not committed).
- **Screenshots:** `HexGen > Capture screenshots`, or from the shell:

  ```bash
  /Applications/Unity/Hub/Editor/6000.6.7f1/Unity.app/Contents/MacOS/Unity -batchmode -projectPath unity -executeMethod HexGen.EditorTools.Capture.Run -logFile -
  ```

  Add `-hexframes <folder>` for a 6-second, 24 fps PNG sequence of the moving water. `water_moving_v1.mp4` was put together from that sequence with Blender's video encoder, because this Mac has no ffmpeg.

**Controls:** Tab switches between the map and the combat board · drag pans · the wheel zooms · right-drag or Q/E rotates (it snaps to 60°) · F frames the view again · T starts or stops the day clock · `[` `]` scrub the time · 1–4 jump to dawn, midday, dusk and night · Space plays the next attack (they also loop by themselves).

## Screens (`screens/`)

| File | What it shows |
| --- | --- |
| `map_board_v1.png` | The test map, framed like `art/preview/map_preview_v6.png` (the same camera: 74 m, 45°, 50 mm, 1600×1000) |
| `map_game_camera_v1.png` | The same map from the game camera (50° tilt) at midday |
| `map_dawn_v1.png`, `map_dusk_v1.png`, `map_night_v1.png` | The time of day: backdrop and light |
| `water_anim_framing_v1.png` | The framing of `art/preview/water_anim_v3.mp4` |
| `water_closeup_v1.png` | A close-up of the river leaving the lake, with the party in view |
| `water_moving_v1.mp4` | 6 s of moving water, framed like `water_anim_v3.mp4` |
| `party_on_tile_v1.png` | The stand-in party as a loose cluster on a plains tile (framed like `standin_map_v1.png`) |
| `combat_board_v1.png` | The radius-4 combat board with the stand-ins (framed like `combat_preview_v2.png`) |
| `combat_hop_v1.png`, `combat_recoil_v1.png` | The hero mid-hop toward an enemy, then the enemy recoiling |
| `build_running_v1.png` | A screenshot taken by the macOS build while it was running (9 a.m.) |

## How it's built

Everything is built in code when the scene starts (`Assets/HexGen/Scripts`), so the scene file holds a single object.

| Piece | Reference it follows | File |
| --- | --- | --- |
| Map assembly: base + centre + six edge wedges, edge same/other, farm–village linking, border joins, pale empty slots | `render_preview.build_map` | `World.cs` |
| Water shapes: rivers, lake shores, the pond and the spring, banks, reeds, rocks, lilies, jetty, boats | `water.py` | `WaterShapes.cs`, `WaterBuilder.cs` |
| Ground cover scatter | `ground_cover.py` | `GroundCover.cs` |
| Ground colour fading toward the neighbour's | the same rule as the ground cover density (half-way at the edge, over 1.6 m) | `Ground.shader` |
| Water shader: flow-map ripples, bump, depth colour, breathing foam rim, sparkle | `render_animation.water_material` | `Water.shader` |
| Boats bobbing | `render_animation.bob_boats` | `BoatBob.cs` |
| Camera: tilt, zoom, 60° rotate, pan | `07 Presentation.md` → Camera and controls | `CameraRig.cs` |
| Backdrop and light by time of day | `07 Presentation.md` → Art direction | `DayCycle.cs` |
| Party cluster, combat board, attack hop and recoil | `render_standin_minis`, `render_preview.build_board` | `World.cs`, `MiniTweens.cs` |

## What matches the references

- **The map is the same map, piece for piece.** The edge choices, the links and the border joins follow `render_preview.py`'s rules exactly, so `map_board_v1.png` lines up with `map_preview_v6.png` from the same camera.
- **The water shapes are identical, not just similar.** The C# port includes Python's random number generator (Mersenne Twister, with Python's seeding from strings and floats), so every river curve, lake wobble, reed, lily, jetty and boat lands where Blender put it. The capture logs a check against `water.py`: the outline points and random draws match to six decimals.
- **The ground cover is the same pattern too**, down to each tuft's size and spin, because it uses the same hash and the same seeded random draws.
- **The colours match the preview.** Open plains measure (174, 213, 131) against the preview's (170, 214, 137). The imported tiles keep their glTF materials. Unity's tone mapping is off, so the flat colours stay as authored.
- **Units and orientation:** 1 unit = 1 m. Map tiles are pointy-top, 9.0 tall; combat cells are flat-top, 1.0 across. Minis face the camera. The light comes from the top left at midday, the same direction as the previews' sun.

## What differs

- **The water's depth and flow come from a texture, not mesh vertices.** The reference stores distance-to-shore and flow on each vertex of a dense mesh. Here they're baked once into a world-space texture (5 cm texels), and the water plates are plain triangulated outlines. It reads the same and is smooth per pixel. Making that dense constrained mesh in Unity would need a triangulation library.
- **The ripples are helped by hand.** In the Blender render, the ripples show mostly because the water reflects the bright pastel world. URP has no sky in this scene, so the shader shades the ripple pattern a little and blends in the backdrop colour at grazing angles. Blender's 4D Perlin noise and Voronoi nodes are swapped for small HLSL versions, so the pattern is similar but not identical.
- **The foam rim looks a bit wider and whiter** than in `water_anim_v3`. It's easy to tune.
- **Faint seams:** a hairline shows where the water plates and banks of two tiles meet, and faintly along some tile edges on the ground (the Blender preview has those too).
- **The time-of-day colours and light are placeholders** (`DayCycle.cs`). The docs only say "soft peach at dawn, pale sky-blue at midday, rose at dusk, a darker, cooler pastel at night", and the exact colours are an open question in `07 Presentation.md`. Midday uses the palette's backdrop colour (#CFE4F2). Dawn is #F8D9C2, dusk #EFC3CC and night #8F9BBE, with matching light colours and angles. They're shared with the Godot session in the side-session notes, so both prototypes can use the same values.
- **The hop and recoil sizes and timings are placeholders** (`MiniTweens.cs`): a hop of 0.35 m up and 0.3 m toward the target over 0.42 s, leaning 10°. The target tilts back 18° and slides 0.12 m, then settles. The demo's attack pairs don't check reach.
- **Camera limits are placeholders:** 50° tilt, zoom from 8 to 110 m.
- **Not done:** look test 4 (the "Game pieces" UI and the card hand), touch gestures, and card placement and the fight itself (this pass was look tests only).

## What was hard in Unity

- **Custom shaders under Forward+ lose the sun unless they ask for it.** The template's PC renderer uses Forward+. A hand-written URP shader that doesn't declare `#pragma multi_compile _ _CLUSTER_LIGHT_LOOP` gets its main light marked as culled, so it's lit by ambient light only. It doesn't log an error, it just looks dull. Shader Graph handles this for you.
- **The SRP Batcher drew every glTFast material in one colour** when rendering from a batch-mode editor script: trees, roofs and fields all came out trunk-brown. Turning the SRP Batcher off fixed it, and `Bootstrap.ConfigurePipeline` keeps it off for now. It may only affect batch rendering, but this wasn't checked.
- **Colour space:** colour properties are converted from sRGB, and vector arrays aren't. The water's linear colours had to become vector properties, and the ground's neighbour colours are converted by hand.
- **Axes:** Blender (right-handed, Z up) → glTF → Unity (left-handed, Y up) is a mirror. All the shape code works in Blender's ground plane and converts at the end, and triangle winding has to be flipped for procedural meshes.
- **Hand-written URP shaders are verbose.** Each one needs its own forward, shadow-caster, depth and depth-normals passes (the last one so SSAO works). A Godot spatial shader is much shorter.
- **The good parts:** batch-mode scripting is solid. One command imports, builds the world and renders every screenshot without opening the editor. glTFast imported the kits with their materials and node names as they are. URP's soft shadows and SSAO work out of the box.
