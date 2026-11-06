# Hero mini kit

Scripted hero minis for the first playable (design/06 → Hero minis), replaced later by 07's pipeline. Ethan approved the kit (Nov 4, 2026) and every weapon pose in the pose pass (rounds 1–6, Nov 5, 2026; verdicts in `art/reviews.md`). Race shapes, heads, hair and armour looks came from proposals; swatches are v22b's, with the flags below still open.

**Changed in the pose pass (kit v10), for the assembler:** every pose now moves the whole hero, so the matrix table is new and nothing but the base is at identity.
- The torso (body and armour) twists and sinks per pose, and the head and hair turn with it: `pose.torso`, `pose.head`, `pose.hair` replace the old identity and per-build head and hair matrices.
- Legs are separate posed parts: `hero_leg_upper_<kind>`, `hero_leg_lower_<kind>`, a `hero_leg_greave` in heavy armour, and a boot, per leg. The bodies lost their legs, so they're smaller.
- Arms are solved per pose with real elbows (IK in the build script); the table holds the results, so Godot does no IK.
- New grips, the two-handed and casting variants (`two`, `caster` in the description), and open palms; the wraps' open hand is its own piece, `hero_hand_open_wraps`.
- The table: `T.races[race].builds[build].poses[main][variant]`, with `torso`, `head`, `hair`, `legs`, `arms`, `main`, `offhand`. Section "What Godot needs" has the whole recipe.

**Hair fix (kit v11, from the phone test's note 071357):** the skull no longer shows through the hair at the back, on any head, race or style. The caps cover the widest of the four heads and have one more ring, so each hair piece has 16 more triangles. Elves and tieflings now get full-width hair, so only their `pose.hair` matrices changed. The table's format is the same.

- **Models:** `art/export/heroes.glb` (from `art/minis/heroes/heroes_v3.blend`, a copy of `hero_kit_v11.blend` named for the export), one shared `kit` material with vertex colours. 163 nodes at the origin, named as below. **Place them only through the assembler:** player colours are marks, which look wrong until swapped.
- **Placements:** `art/export/heroes_placements.json`, 1.5 MB (it was 554 KB: each pose now holds the whole body). Parse once and keep it.
- **Scripts:** `art/scripts/build_hero_kit.py`, `export_hero_kit.py` (writes the table; `from_table()` is the recipe below in code, the model for Godot's assembler), `render_hero_kit.py`, `render_pose_check.py` (the pose sheets), `render_hero_export.py` (heroes built from the export alone).
- **Previews (`art/preview/`):** `hero_kit_weapons_v1.png` (all 21 weapons, cycling races, gear and offhands), `hero_kit_dragon_heads_v1.png` (the 4 dragonborn heads from three sides), `hero_kit_dragon_look_v1.png` (5 dragon types at Look size), `hero_kit_look_v2.png`, `hero_kit_look_back_v2.png`, `hero_kit_faces_v2.png`, `hero_kit_builds_v2.png`, `hero_kit_hair_v2.png`. Map sizes, from before the new heads and weapons: `hero_kit_map_58m_v1.png`, `hero_kit_map_30m_v1.png`, `hero_kit_map_18m_v1.png`. **The poses:** the approved panels are in `pose_check_*` and `pose_check_round3_*` to `pose_check_round6_*`; `hero_export_check_v1.png` and `_back_v1.png` show ten heroes built from the glb and table alone, one per pose family. **Hair from behind:** `hero_hair_check_<race>_v1.png` (human `_v2`): every style on every head, from behind and three-quarter back. `hero_hair_worst_v1.png` and `_v2.png` show the worst cases before and after the fix.

## A hero as a description

```
{race, build, head, hair, armour, main, offhand, two, caster, colours: {skin, hair, eyes, cloth}}
```

Sub-types add no shape: they only set `colours.skin` (golem material, dragon type's default). `hair` is ignored on dragonborn and golem. `offhand` applies to one-handed weapons: `shield`, a second one-handed weapon, or empty. `two` (optional) holds a versatile weapon in both hands: `longsword`, `battleaxe`, `spear`, with no offhand. `caster` (optional) gives a staff with an empty offhand the casting pose.

## Pieces

| Piece | Count | Triangles | Notes |
|---|---:|---:|---|
| `hero_base` | 1 | 68 | The stand-in's hex base and ring |
| `hero_body_<race>_<build>` | 21 | 84-190 | Own shape per build, final size, without legs (they're parts). Placed by `pose.torso` |
| `hero_armour_<light/medium/heavy>_<race>_<build>` | 63 | 80-168 | Over that body, by the same `pose.torso` |
| `hero_head_<race>_<a-d>` | 28 | 60-402 | Pivot at the head's middle. Horns, beards and faceplates are in the head |
| `hero_hair_<style>` | 6 | 100-170 | `short`, `long`, `topknot`, `spiky`, `tail`, `crest`. Pivot at the head's middle, scaled to the race |
| `hero_arm_upper_<kind>`, `hero_arm_fore_<kind>` | 8 | low | `bare`, `chain`, `plate`, `golem`. Length 1 along +Z, radius 1: scaled to fit |
| `hero_hand_<kind>` | 3 | 12-20 | `bare`, `gauntlet`, `golem`. An open palm is the same piece, flattened by its matrix |
| `hero_hand_open_wraps` | 1 | 180 | The wraps' open hand: wrapped palm and wrist, bare finger slab and thumb. Replaces the hand where `hand_piece` is `open_wraps` |
| `hero_leg_upper_<kind>`, `hero_leg_lower_<kind>` | 6 | 12-20 | `cloth`, `scaled` (dragonborn), `golem`. Unit tubes along +Z, placed by matrix like the arms |
| `hero_leg_greave` | 1 | 20 | Over the shin in heavy armour, not on a golem |
| `hero_boot_<kind>` | 2 | 32 | `leather`, `golem` |
| Weapons and `hero_shield` | 23 | 24-96 | Below. Fist weapons are one piece, placed on each fist. `hero_wraps_open` is no longer used (the open hand replaced it); ignore it |

163 pieces. A whole hero comes to **472-1,342 triangles** (a golem with a spear and no armour lowest, a broad dragonborn in heavy armour with wraps highest). Bandits are 386-557. Ethan accepts heavy armour and dragon heads being heaviest until a phone test says otherwise (Nov 4, 2026).

## Grips and weapons

All 21 of the Fighter's weapons have a mesh and an approved pose (Ethan, pose pass, Nov 5, 2026). The rules for each pose are 07's Pose library; this is how the kit names them.

| Grip | Weapon (variant) | Hands | Pose |
|---|---|---|---|
| `forward` | `longsword` | One | Point forward at the foe, chest high |
| `high` | `longsword` (`two`) | Two | High guard, blade above the head, edge forward |
| `backhand` | `shortsword` | One | Laid back over the off shoulder, edge out |
| `fencer` | `rapier` | One | En garde, the back arm raised out behind |
| `slash` | `scimitar` | One | Raised beside the head at the off shoulder, curved edge forward |
| `reverse` | `dagger` | One | Reverse grip in a crouch, the blade angled out from the body |
| `raised` | `mace` | One | Raised high |
| `low` | `battleaxe` | One | Held low and loose, head up, the hand a third down the haft |
| `executioner` | `battleaxe` (`two`) | Two | Drawn back behind the head, edge forward |
| `planted` | `greatsword`, `warhammer` | Two | Resting on the base. The greatsword shows its flat, the one exception to the edge-forward rule |
| `shoulder` | `greataxe` | Two | Haft on the shoulder, one hand up, one low |
| `upright` | `spear`, `halberd`, `staff` (with an offhand) | One | At attention, planted |
| `pike` | `spear` (`two`) | Two | Braced level, point into the next cell |
| `sweep` | `glaive` | Two | Mid-sweep, torso twisted, blade down and forward, both hands on the haft |
| `across` | `staff` | Two | Quarterstaff guard across the body |
| `cast` | `staff` (`caster`) | One | Planted, the free hand raised, an open palm |
| `point` | `wand` | One | Arm out, angled forward and out |
| `bow` | `shortbow`, `longbow` | Two | Side-on, drawn to the cheek, arrow nocked, the drawing forearm along the arrow |
| `aim` | `crossbow` | Two | Stock at the shoulder |
| `guard` | `gauntlets` | Fists | Fists at the chin |
| `haymaker` | `brass_knuckles` | Fists | Torso twisted, the rear arm pulled back level at shoulder height |
| `stance` | `wraps` | Fists | Open wrapped palm forward, the other fist at the hip |

**Offhand:** `shield` or a second one-handed weapon on the one-handed weapons. Not with `two`, nor with the `high`, `executioner`, `pike`, `across` or `cast` grips; a staff with an offhand takes `upright`. Every blade's edge faces forward, never the flat, except the greatsword.

**Left out:** helmets, leggings and gloves as gear; enchantment looks; other classes.

## Race shapes (proposals)

| Race | Height | Shape | Head |
|---|---:|---|---|
| Human | 1.0 | The middle of everything | Skin, four faces |
| Elf | 1.0 | Long legs, narrow, thin arms | Narrow, tall pointed ears, slightly bigger eyes |
| Dwarf | 0.84 | Wide shoulders and hips, thick limbs, short legs | Wide, big nose, a beard per head in the hair colour |
| Halfling | 0.74 | Small, a big head for its size | Big eyes, small nose, slightly pointed ears |
| Golem | 1.04 | Blocks at shoulders and fists, seam at the waist, a cloth at the waist | Four faceplates, glowing eyes |
| Dragonborn | 1.08 | Tall, deep chest, pale belly and throat, heavy tail to the left | A skull with a brow, then a step down to a long, blunt muzzle with its own nose, over a separate paler jaw. Big eyes, swept horns, cheek fins, spines. Four snout and horn shapes |
| Tiefling | 1.0 | Lean, thin spade tail | Glowing eyes with no whites, horns per head in a dark shade of the skin |

## Swatches (proposals)

Unchanged from v22b, six each: `SWATCHES` in the script holds skin per race, the golem's three materials, hair, eyes and cloth. Dragon types default to `red` #B8463A, `blue` #4E7FB8, `white` #DCE3E8, `black` #3A3A40, `green` #5E9A5A. The dragonborn's sixth, gold #C9A24A, has no type in the docs.

**Flags, still open:** `white` dragonborn is close to steel. The sixth tiefling colour #E3B9A0 reads as human skin. Gold has no dragon type in the docs.

## What Godot needs

A hero is one merged mesh, rebuilt from its description once per hero and per change. **Checked:** for 400 random heroes, the recipe below (`from_table()` in `export_hero_kit.py`) gave exactly the assembler's piece names and matrices; ten built from the glb and table alone matched its triangles and bounds and render as the approved poses (`hero_export_check_v1.png`). Not yet run in Godot.

**1. The pose.** With `T` the JSON: `pose = T.races[race].builds[build].poses[main][variant]`, where `variant` is:

- `cast` for a `staff` with `caster` and no offhand;
- `two` for a weapon in `T.two_grip` with `two` and no offhand;
- `shield` with a shield, `second` with any one-handed weapon as the offhand (all share one matrix), else `none`.

**2. The parts,** in this order (the order only matters for matching Blender's output):

| Part | Piece | Matrix |
|---|---|---|
| Base | `hero_base` | identity |
| Body | `hero_body_<race>_<build>` | `pose.torso` |
| Armour, unless `none` | `hero_armour_<tier>_<race>_<build>` | `pose.torso` |
| Head | `hero_head_<race>_<head>` | `pose.head` |
| Hair, unless `T.hairless` has the race or there's none picked | `hero_hair_<style>` | `pose.hair` |
| Each leg, `pose.legs[0]` then `[1]` | `hero_leg_upper_<leg>`, `hero_leg_lower_<leg>`, then `hero_leg_greave` in heavy armour unless a golem, then `hero_boot_<boot>` | `upper`, `lower`, `greave`, `boot` |
| Each arm, `pose.arms[0]` (right) then `[1]` (left) | `hero_arm_upper_<kind>`, `hero_arm_fore_<kind>`, then the hand: `hero_hand_open_wraps` if `hand_piece` is `open_wraps`, else `hero_hand_<fist>`; then the fist weapon `hero_<main>` if the arm has `fist_weapon` | `upper`, `fore`, `hand`, `fist_weapon` |
| Main weapon, unless a fist weapon | `hero_<main>` | `pose.main` |
| Offhand | `hero_shield` or `hero_<offhand>` | `pose.offhand` |

- `leg`: `golem` for a golem, `scaled` for a dragonborn, otherwise `cloth`. `boot`: `golem` for a golem, otherwise `leather`.
- `kind`: `golem` for a golem, otherwise `bare` for no or light armour, `chain` for medium, `plate` for heavy.
- `fist`: `golem` for a golem, `gauntlet` for heavy armour, otherwise `bare`. `hand_piece` `palm` uses this same piece; its matrix flattens it into an open hand.
- A fist weapon goes only on a closed fist: the wraps' open hand has none.
- `pose.grip` names the grip, for anything else that wants it (sounds, animation later).
- Weapon names in the data have `brass_knuckles` with an underscore.
- **Matrices** are 12 numbers: the basis's x, y and z columns, then the origin. They're in the glb's frame, which is Godot's: `Transform3D(Basis(Vector3(m0, m1, m2), Vector3(m3, m4, m5), Vector3(m6, m7, m8)), Vector3(m9, m10, m11))`.
- **Scale isn't uniform** on arms, legs, open palms and planted weapons. Transform normals by the inverse transpose, or recompute them. A matrix with a negative determinant flips the piece: reverse its faces' winding.
- A mini faces +Z in the glb's frame (-Y in Blender), with its pivot at the base's centre on the ground, as the enemy minis do.

**3. The colours.** After merging, go through the vertex colours, converting each from linear to sRGB bytes (`Color.linear_to_srgb()`):

- **Blue 253 or more is a mark.** Nothing else in the kit has it.
- **Zone:** red ÷ 20, rounded: 1 skin, 2 hair, 3 eyes, 4 cloth.
- **Shade:** green ÷ 100.
- **New colour,** in linear: the swatch's linear colour × shade^2.2, each clamped to 1. Alpha 1.
- Everything else stays as it is.

Godot may hold imported vertex colours in 8 bits, in linear, which loses precision at the dark end. Rounding the zone copes with that by my arithmetic, and the shade would be off by a few percent. Worth one test.

**4. Elsewhere.**

- **Same material as the other minis:** `Kit.combat_materials`, once.
- **Height:** `T.races[race].height` is included in all the matrices; don't scale again.
- **The Look step:** a rebuild on each pick. Its cost hasn't been measured. If it's slow, keep the pieces as separate nodes there, swapping colours per piece, and merge when done.
- **Dragon type and golem sub-type** change only `colours.skin`. Defaults are in `T.dragon_types` and `T.swatches.skin`.
- **Saves and multiplayer:** send the description, not the mesh.
- **`EncounterView` and the party** can both take a hero the same way later. The ranger's ally beasts are in `beasts_kit.md`; other companions aren't in this kit.

## Weak spots

- At Look size these are still chunky low-poly, not Chelmsford's sculpted look.
- Hair from behind is clean on every head (kit v11). Ears and horns pass through hair by design.
- Builds now differ, but slim is close to average. Tunics are flat.
- Small weapons (wand, dagger) barely read below Look size. Gauntlets are bulky on a broad or golem arm, and fists up partly crowd the head.
- Faces read well close up. At 58 m they're gone: only colour, height, horns and big gear show.
- The glaive's butt rises behind the off shoulder in its tightened sweep; the open wrapped hand is the heaviest hand at 180 triangles.
- Not done: anything in Godot, and a phone test for triangle counts. A hero tops out around 1,360.
