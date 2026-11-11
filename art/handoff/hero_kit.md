# Hero mini kit

Scripted hero minis for the first playable (design/06 → Hero minis), replaced later by 07's pipeline. Ethan approved the kit (Nov 4, 2026) and every weapon pose in the pose pass (rounds 1–6, Nov 5, 2026; verdicts in `art/reviews.md`). Race shapes, heads, hair and armour looks came from proposals; swatches are v22b's, with the flags below still open.

**Changed in the pose pass (kit v10), for the assembler:** every pose now moves the whole hero, so the matrix table is new and nothing but the base is at identity.
- The torso (body and armour) twists and sinks per pose, and the head and hair turn with it: `pose.torso`, `pose.head`, `pose.hair` replace the old identity and per-build head and hair matrices.
- Legs are separate posed parts: `hero_leg_upper_<kind>`, `hero_leg_lower_<kind>`, a `hero_leg_greave` in heavy armour, and a boot, per leg. The bodies lost their legs, so they're smaller.
- Arms are solved per pose with real elbows (IK in the build script); the table holds the results, so Godot does no IK.
- New grips, the two-handed and casting variants (`two`, `caster` in the description), and open palms; the wraps' open hand is its own piece, `hero_hand_open_wraps`.
- The table: `T.races[race].builds[build].poses[main][variant]`, with `torso`, `head`, `hair`, `legs`, `arms`, `main`, `offhand`. Section "What Godot needs" has the whole recipe.

**Golems (kit v14, Nov 10, 2026; approved by Ethan and merged to main):** each golem sub-type has its own shape, and the metal golem has its own long-arm placements. A description now carries `subtype` for a golem, its piece names carry the sub-type, and the table gains a `golem_metal` entry. Every other entry is unchanged, the old golem entry included. See Golems below.

**Hair fix (kit v11, from the phone test's note 071357):** the skull no longer shows through the hair at the back, on any head, race or style. The caps cover the widest of the four heads and have one more ring, so each hair piece has 16 more triangles. Elves and tieflings now get full-width hair, so only their `pose.hair` matrices changed. The table's format is the same.

- **Models:** `art/export/heroes.glb` (from `art/minis/heroes/heroes_v4.blend`, a copy of `hero_kit_v14.blend` named for the export), one shared `kit` material with vertex colours. 189 nodes at the origin, named as below. **Place them only through the assembler:** player colours are marks, which look wrong until swapped.
- **Placements:** `art/export/heroes_placements.json`, 1.7 MB (it was 554 KB: each pose now holds the whole body; the metal golem's entry added the rest). Parse once and keep it.
- **Scripts:** `art/scripts/build_hero_kit.py`, `export_hero_kit.py` (writes the table; `from_table()` is the recipe below in code, the model for Godot's assembler), `render_hero_kit.py`, `render_pose_check.py` (the pose sheets), `render_hero_export.py` (heroes built from the export alone).
- **Previews (`art/preview/`):** `hero_kit_weapons_v1.png` (all 21 weapons, cycling races, gear and offhands), `hero_kit_dragon_heads_v1.png` (the 4 dragonborn heads from three sides), `hero_kit_dragon_look_v1.png` (5 dragon types at Look size), `hero_kit_look_v2.png`, `hero_kit_look_back_v2.png`, `hero_kit_faces_v2.png`, `hero_kit_builds_v2.png`, `hero_kit_hair_v2.png`. Map sizes, from before the new heads and weapons: `hero_kit_map_58m_v1.png`, `hero_kit_map_30m_v1.png`, `hero_kit_map_18m_v1.png`. **The poses:** the approved panels are in `pose_check_*` and `pose_check_round3_*` to `pose_check_round6_*`; `hero_export_check_v1.png` and `_back_v1.png` show ten heroes built from the glb and table alone, one per pose family. **Hair from behind:** `hero_hair_check_<race>_v1.png` (human `_v2`): every style on every head, from behind and three-quarter back. `hero_hair_worst_v1.png` and `_v2.png` show the worst cases before and after the fix.

## A hero as a description

```
{race, build, head, hair, armour, main, offhand, two, caster, subtype, colours: {skin, hair, eyes, cloth}}
```

`subtype` is for golems only: `stone`, `wood` or `metal`, each its own shape (Golems, below). A dragon type adds no shape: it only sets `colours.skin` to that type's default. `hair` is ignored on dragonborn and golem. `offhand` applies to one-handed weapons: `shield`, a second one-handed weapon, or empty. `two` (optional) holds a versatile weapon in both hands: `longsword`, `battleaxe`, `spear`, with no offhand. `caster` (optional) gives a staff with an empty offhand the casting pose.

## Pieces

| Piece | Count | Triangles | Notes |
|---|---:|---:|---|
| `hero_base` | 1 | 68 | The stand-in's hex base and ring |
| `hero_body_<race>_<build>` | 18 | 84-190 | Own shape per build, final size, without legs (they're parts). Placed by `pose.torso`. Golems: `hero_body_golem_<subtype>_<build>`, 9 more |
| `hero_armour_<light/medium/heavy>_<race>_<build>` | 63 | 80-168 | Over that body, by the same `pose.torso` |
| `hero_head_<race>_<a-d>` | 24 | 60-402 | Pivot at the head's middle. Horns and beards are in the head. Golems: `hero_head_golem_<subtype>_<a-d>`, 12 more |
| `hero_hair_<style>` | 6 | 100-170 | `short`, `long`, `topknot`, `spiky`, `tail`, `crest`. Pivot at the head's middle, scaled to the race |
| `hero_arm_upper_<kind>`, `hero_arm_fore_<kind>` | 12 | 20-56 | `bare`, `chain`, `plate`, and per golem sub-type `golem_stone`, `golem_wood`, `golem_metal`. Length 1 along +Z, radius about 1 at the top: scaled to fit |
| `hero_hand_<kind>` | 5 | 20-76 | `bare`, `gauntlet`, `golem_stone`, `golem_wood`, `golem_metal`. An open palm is the same piece, flattened by its matrix |
| `hero_hand_open_wraps` | 1 | 180 | The wraps' open hand: wrapped palm and wrist, bare finger slab and thumb. Replaces the hand where `hand_piece` is `open_wraps` |
| `hero_leg_upper_<kind>`, `hero_leg_lower_<kind>` | 10 | 20-44 | `cloth`, `scaled` (dragonborn), `golem_stone`, `golem_wood`, `golem_metal`. Unit tubes along +Z, placed by matrix like the arms |
| `hero_leg_greave` | 1 | 20 | Over the shin in heavy armour, not on a golem |
| `hero_boot_<kind>` | 4 | 32-44 | `leather`, `golem_stone`, `golem_wood`, `golem_metal` |
| Weapons and `hero_shield` | 23 | 24-96 | Below. Fist weapons are one piece, placed on each fist. `hero_wraps_open` is no longer used (the open hand replaced it); ignore it |

189 pieces. A whole hero comes to at most **1,360 triangles**: a broad stone golem with head b, heavy armour and wraps. The heaviest dragonborn and the heaviest wood golem are 1,342. Bandits are 386-557. Ethan accepts heavy armour and dragon heads being heaviest until a phone test says otherwise (Nov 4, 2026).

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
| `bow` | `shortbow`, `longbow` | Two | Side-on, arrow nocked at shoulder height, the drawing hand just under the jaw, the drawing arm level with the elbow drawn back (Ethan, Nov 9, 2026) |
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
| Golem | 1.04 | One shape per sub-type: see Golems | Four heads per sub-type, glowing eyes |
| Dragonborn | 1.08 | Tall, deep chest, pale belly and throat, heavy tail to the left | A skull with a brow, then a step down to a long, blunt muzzle with its own nose, over a separate paler jaw. Big eyes, swept horns, cheek fins, spines. Four snout and horn shapes |
| Tiefling | 1.0 | Lean, thin spade tail | Glowing eyes with no whites, horns per head in a dark shade of the skin |

## Golems

Each sub-type has its own shape (Ethan, Nov 9, 2026; `art/preview/golem_set_v3.png`). The pieces come from `art/scripts/golem_kit.py`.

| Sub-type | Look | Arms |
|---|---|---|
| `stone` | A cairn of stacked rounded stones, moss in the cracks, the eyes lit in a chink | Standard |
| `wood` | A folk carving in bare wood, still alive: moss on the shoulders and back, leafy shoots, a bracket fungus on the hip, ivy round the forearms and shins, roots spreading from the feet. No paint | Standard |
| `metal` | The shell-back: stooped under a domed back like an old cupola, with a moss garden and a sapling on top. A small round head low and forward under its rim, verdigris, mitten hands | **Long** |

- **Colours:** the material is the skin zone, as before (`T.swatches.skin.golem_<subtype>`). No golem uses the cloth zone. Moss, leaves, the sapling, flowers, fungus and verdigris are fixed colours.
- **Heads:** four per sub-type, `a`-`d`, picked by Ethan from five candidates each (`art/preview/golem_heads_v1.png`, wood `golem_heads_v2.png`). All of them, on all three builds: `art/preview/golem_final_set_v1.png`.
- **Armour:** the golem armour pieces are shared by all three sub-types (`hero_armour_<tier>_golem_<build>`) and sit over each shape (`art/preview/golem_armour_v2.png`).
- **Triangles:** a whole golem with a longsword and no armour is about 910-1,000 (wood), 1,030-1,080 (metal) and 1,040-1,070 (stone). The worst case, broad with heavy armour and wraps, is 1,342 for wood, 1,340 for metal and 1,360 for stone.

### The metal golem's own arm placements

The shell-back has long arms (Ethan, Nov 9, 2026), so its arms, hands and held weapons sit differently in every pose. They have their own entry in the table, **`T.races.golem_metal`**: all 3 builds, every weapon and variant, in the same format as every other race.

- **Which entry to read:** a golem with `subtype` `metal` reads `T.races.golem_metal`. Stone and wood golems read `T.races.golem`. Everyone else reads `T.races[race]`. `T.long_arms` lists the sub-types with their own entry (`{"metal": 1.3}`), so the rule is: `golem_<subtype>` if the subtype is in `T.long_arms`, else the race.
- **What differs:** only `arms` (upper, fore, hand, fist weapon), `main` and `offhand`. `torso`, `head`, `hair` and `legs` match `T.races.golem` exactly. Height (`T.races.golem_metal.height`) is the golem's.
- **What the numbers do** (for reading the sheets, not for Godot to compute; the table already holds the results): the arm bones are 1.3 times longer. Each hand reaches 1.3 times as far from its shoulder, out and down but never higher, so raised weapons stay in the cell. Where both hands hold one weapon (`high`, `executioner`, `planted`, `shoulder`, `pike`, `sweep`, `across`, `bow`, `aim`), they move together, so the grip holds. A planted greatsword or warhammer stays on the ground, and a planted staff or spear stays planted, its hand sliding down the haft. `art/preview/golem_metal_poses_v1.png` shows every grip.
- **Pieces:** the same recipe as every hero (What Godot needs), with the sub-type in the piece names.
- **Checked:** `export_hero_kit.py -- check` builds random heroes of every race and golem sub-type from the table alone, by these rules, and matches the assembler's piece names and matrices: 400 heroes, 0 mismatched.

## Swatches (proposals)

Unchanged from v22b, six each: `SWATCHES` in the script holds skin per race, the golem's three materials, hair, eyes and cloth. Dragon types default to `red` #B8463A, `blue` #4E7FB8, `white` #DCE3E8, `black` #3A3A40, `green` #5E9A5A. The dragonborn's sixth, gold #C9A24A, has no type in the docs.

**Flags, still open:** `white` dragonborn is close to steel. The sixth tiefling colour #E3B9A0 reads as human skin. Gold has no dragon type in the docs.

## What Godot needs

A hero is one merged mesh, rebuilt from its description once per hero and per change. **Checked:** for 400 random heroes, the recipe below (`from_table()` in `export_hero_kit.py`) gave exactly the assembler's piece names and matrices; ten built from the glb and table alone matched its triangles and bounds and render as the approved poses (`hero_export_check_v1.png`). Not yet run in Godot.

**1. The pose.** With `T` the JSON: `pose = T.races[entry].builds[build].poses[main][variant]`. `entry` is `golem_metal` for a metal golem, else the race (Golems → The metal golem's own arm placements). `variant` is:

- `cast` for a `staff` with `caster` and no offhand;
- `two` for a weapon in `T.two_grip` with `two` and no offhand;
- `shield` with a shield, `second` with any one-handed weapon as the offhand (all share one matrix), else `none`.

**2. The parts,** in this order (the order only matters for matching Blender's output):

| Part | Piece | Matrix |
|---|---|---|
| Base | `hero_base` | identity |
| Body | `hero_body_<race>_<build>`; a golem `hero_body_golem_<subtype>_<build>` | `pose.torso` |
| Armour, unless `none` | `hero_armour_<tier>_<race>_<build>` | `pose.torso` |
| Head | `hero_head_<race>_<head>`; a golem `hero_head_golem_<subtype>_<head>` | `pose.head` |
| Hair, unless `T.hairless` has the race or there's none picked | `hero_hair_<style>` | `pose.hair` |
| Each leg, `pose.legs[0]` then `[1]` | `hero_leg_upper_<leg>`, `hero_leg_lower_<leg>`, then `hero_leg_greave` in heavy armour unless a golem, then `hero_boot_<boot>` | `upper`, `lower`, `greave`, `boot` |
| Each arm, `pose.arms[0]` (right) then `[1]` (left) | `hero_arm_upper_<kind>`, `hero_arm_fore_<kind>`, then the hand: `hero_hand_open_wraps` if `hand_piece` is `open_wraps`, else `hero_hand_<fist>`; then the fist weapon `hero_<main>` if the arm has `fist_weapon` | `upper`, `fore`, `hand`, `fist_weapon` |
| Main weapon, unless a fist weapon | `hero_<main>` | `pose.main` |
| Offhand | `hero_shield` or `hero_<offhand>` | `pose.offhand` |

- `leg`: `golem_<subtype>` for a golem, `scaled` for a dragonborn, otherwise `cloth`. `boot`: `golem_<subtype>` for a golem, otherwise `leather`.
- `kind`: `golem_<subtype>` for a golem, otherwise `bare` for no or light armour, `chain` for medium, `plate` for heavy.
- `fist`: `golem_<subtype>` for a golem, `gauntlet` for heavy armour, otherwise `bare`. `hand_piece` `palm` uses this same piece; its matrix flattens it into an open hand.
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
- **Dragon type** changes only `colours.skin`; defaults are in `T.dragon_types`. **Golem sub-type** is `subtype`, which picks its pieces (and, for metal, its table entry); its material colours are in `T.swatches.skin.golem_<subtype>`.
- **Saves and multiplayer:** send the description, not the mesh.
- **`EncounterView` and the party** can both take a hero the same way later. The ranger's ally beasts are in `beasts_kit.md`; other companions aren't in this kit.

## Weak spots

- At Look size these are still chunky low-poly, not Chelmsford's sculpted look.
- Hair from behind is clean on every head (kit v11). Ears and horns pass through hair by design.
- Builds now differ, but slim is close to average. Tunics are flat.
- Small weapons (wand, dagger) barely read below Look size. Gauntlets are bulky on a broad arm, and fists up partly crowd the head.
- Faces read well close up. At 58 m they're gone: only colour, height, horns and big gear show.
- The glaive's butt rises behind the off shoulder in its tightened sweep; the open wrapped hand is the heaviest hand at 180 triangles.
- Not done: anything in Godot, and a phone test for triangle counts. A hero tops out around 1,360.
