# HexGen · Godot prototype

The Godot half of the engine prototype ([design/06 Multiplayer & tech.md](../design/06%20Multiplayer%20&%20tech.md) → Engine prototype). It starts with the look tests, not gameplay: the map board, water, camera and backdrop, and minis on the combat board. Godot 4.7.2, Forward+ renderer, judged on PC.

## Running it

Open `godot/project.godot` in Godot 4.7, or from the repo root:

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path godot
```

| Input | Does |
| --- | --- |
| Tab | Switch between the map board and the combat board |
| Left-drag | Pan |
| Wheel, trackpad pinch, + / − | Zoom |
| Right-drag | Rotate; snaps to the nearest 60° on release |
| Q / E | Rotate 60° |
| F | Frame the board again |
| T | Start or stop the day clock (a whole day in 90 s) |
| [ / ] | Clock back or on by an hour |
| Space (combat) | Play the next attack (they also play by themselves) |

Screenshots and recordings (they open a window; headless can't render):

```bash
# All screenshots into godot/screens/
/Applications/Godot.app/Contents/MacOS/Godot --path godot -- --shots

# A recording: a PNG sequence from Godot's movie maker, then an .mp4 (no ffmpeg needed)
/Applications/Godot.app/Contents/MacOS/Godot --path godot --write-movie /tmp/frames/frame.png --fixed-fps 30 --quit-after 240 -- --view=water_anim --nohud
swift godot/tools/png_to_mp4.swift /tmp/frames godot/screens/water_movie.mp4 30
```

Other arguments after `--`: `--view=map|water|water_anim|combat|party`, `--hour=6.5`, `--look=x,y,distance,pitch[,yaw]` for any framing (plan coordinates).

## Art

`godot/art/*.glb` are symlinks to `art/export/*.glb`, so the art stays in one place and the engine re-imports whenever it changes. They link the files, not the folder, so Godot's `.import` files land in `godot/art/` and nothing is written into `art/`.

## What's in it

| Step | Where | Notes |
| --- | --- | --- |
| Map board | `scripts/map_board.gd` | `MAP` from `render_preview.py`, assembled by the same rules: base and centre, `edge_same` / `edge_other` per neighbour, farms and villages linked, `border_join_l` / `_r` |
| Water shapes | `scripts/water.gd` | `water.py` line by line: edge stretches, shores, springs, ponds, lakes, banks, reeds, rocks, lilies, jetties, boats |
| Same random numbers | `scripts/py_random.gd` | Python's `random.Random` (Mersenne Twister with SHA-512 string seeding and float-hash seeding), so every seeded curve and prop comes out identical to Blender's |
| Ground cover | `scripts/ground_cover.gd` | `ground_cover.py`: the same world-space hash grid, densities and edge fade, built into one mesh |
| Ground colour fade | `shaders/ground.gdshader` | Look test 1. World-space shader on the base slabs' tops; see "What differs" |
| Water shader | `shaders/water.gdshader` | `render_animation.py`'s material: two-phase flow-map ripples, sparkle cells, breathing foam rim, depth colour; depth and flow per vertex as in `water_mesh()` |
| Camera | `scripts/camera_rig.gd` | Tilted camera (50° by default, the preview framings in screenshots), zoom, 60° rotation steps, pan |
| Backdrop and light by time of day | `scripts/time_of_day.gd` | Look test 2 |
| Stand-ins and attacks | `scripts/minis.gd`, `scripts/combat_board.gd` | Look test 3: the party as a cluster on a map tile; the radius-4 board; hop and recoil as tweens |

## Screens

| File | What |
| --- | --- |
| `screens/map_board.png` | The test map, framed like `art/preview/map_preview_v6.png` (1600×1000, 50 mm, target (2, −2), 74 m, 45°) |
| `screens/water_closeup.png` | The lake and river mouth up close |
| `screens/combat_board.png` | The combat board, framed and lined up like `art/preview/standin_combat_v1.png` |
| `screens/party_closeup.png` | The party on a plains tile, framed like `art/preview/standin_map_v1.png` |
| `screens/map_dawn.png`, `map_dusk.png`, `map_night.png` | The map at other times of day (placeholder colours) |
| `screens/water_movie.mp4` | 8 s of moving water, framed like `art/preview/water_anim_v3.mp4` |
| `screens/combat_movie.mp4` | 10 s of attacks on the combat board |

## What matches the references

- **Map layout and pieces:** every tile, wedge, fence and join lands where `render_preview.py` puts it; side by side with `map_preview_v6.png` the two line up.
- **Water shapes and dressing:** identical, not just similar. The river bends, lake shore wobble, pond, spring, reeds, lilies and boats come out the same because the Python random generator is ported exactly.
- **Ground cover:** the same points, sizes and turns as Blender's (the hash is ported exactly, and so is the float seeding of each prop).
- **Colours and light at midday:** sampled pixels on the combat board come within about 3% of `standin_combat_v1.png` in sunlit cells, shade, minis and backdrop.
- **Combat board and party:** the same cells, trees, rocks and minis in the same spots as `render_standin_minis.py`.
- **Water motion:** the same rules and numbers (2 s flow period, 0.6 m/s rivers, 0.15 m/s lake drift near shores, sparkle cells at scale 2.6 with 35% able to glint every 3.5–6 s, foam at 0.05 ± 0.03 m breathing at 1.6 rad/s, depth colour from 0.2 to 2.2 m), and boats bob as in `bob_boats()`.

## What differs

- **Ground colour fade (look test 1):** the brief says to fade like `ground_cover.py`, edge by edge. In colour that rule leaves a visible seam along part of an edge wherever three different terrains meet at a corner (each side adds a different share of the third terrain). The shader instead weights each placed neighbour by its distance to that neighbour's whole hexagon: 1 at the shared edge, 0 at 1.6 m, with the own tile always 1. Edges still meet at the average of both colours, and it's continuous at corners. The 1.6 m width is borrowed from ground cover; the docs don't set one.
- **Soft shadows:** Blender's sun has an 8° disc. Godot's matching soft shadows (PCSS, `light_angular_distance`) came out grainy and washed most shadows out, so the sun uses ordinary filtered shadows (PCF with blur). They're a little crisper than Blender's.
- **Noise textures:** Blender's Noise, Voronoi and White Noise textures are replaced by shader code with the same scales, octaves and thresholds, so ripples and sparkles follow the same rules but not the same exact pattern.
- **Water tuning by eye:** with Blender's numbers the ripples barely showed and the shore glared white. The bump is raised from 0.7 to 2.0, and the reflectance is halved (Blender lights reflections with the backdrop at half strength, Godot at full).
- **Water triangles:** Godot has no constrained Delaunay, so the water mesh triangulates all points and drops triangles whose centre falls outside the shore.
- **Times of day other than midday are placeholders:** the docs give the idea (peach dawn, pale sky-blue midday, rose dusk, darker cooler night) but the exact colours are an open question (`design/07 Presentation.md`). Midday is the previews' `#CFE4F2` with the previews' sun; the dawn, dusk and night colours, sun angles and light colours in `time_of_day.gd` are guesses for the look test, there to be replaced.
- **Hop and recoil numbers** (0.35 m hop, 16° tilt, timings) and the attack order are placeholders; the docs only say the attacker hops and the target recoils.
- **Look test 4 (the exploration and combat UI, the card hand)** isn't built yet.

## What was hard in Godot

- **Matching Python's random numbers.** Godot's hashing stops at SHA-256, so SHA-512 is written out in GDScript with 64-bit wraparound maths. Worth it: the shapes are identical to the reference without storing them.
- **Soft sun shadows**, as above.
- **Shaders read flat colours as sRGB but expect linear albedo,** so the ground lookup texture is converted by hand in the shader; the water's colours were already linear in Blender.
- **No constrained triangulation** in `Geometry2D`; Delaunay plus a centre test was enough here.
- **Screenshots need a window.** `--headless` has no renderer, so capture runs a real window for a few seconds. Godot's movie maker writes PNG frames or MJPEG `.avi` (not `.mp4`), so a small Swift script turns frames into `.mp4`.
- Otherwise it went smoothly: glTF import kept every piece name and material, scenes and scripts are plain text, and tweens made the hop and recoil a few lines each.

## Not checked yet

- Performance on the iPhone (the water shader does a 27-cell Voronoi and six fBm noise lookups per pixel; fine on an M1 Pro, likely too much for phones as is).
- The Mobile and Compatibility renderers.
