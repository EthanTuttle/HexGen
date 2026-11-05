# Hero mini kit

Scripted hero minis for the first playable (design/06 → Hero minis), replaced later by 07's pipeline. Ethan approved the kit (Nov 4, 2026). Race shapes, heads, hair and armour looks came from proposals; swatches are v22b's, with the flags below still open.

- **Models:** `art/export/heroes.glb` (from `art/minis/heroes/heroes_v1.blend`, a copy of `hero_kit_v2.blend` named for the export), one shared `kit` material with vertex colours. 152 nodes at the origin, named as below. **Place them only through the assembler:** player colours are marks, which look wrong until swapped.
- **Placements:** `art/export/heroes_placements.json`, 554 KB. Parse once and keep it.
- **Scripts:** `art/scripts/build_hero_kit.py`, `export_hero_kit.py`, `render_hero_kit.py`. `assemble()` in the build script is the model for Godot's.
- **Previews (`art/preview/`):** `hero_kit_weapons_v1.png` (all 21 weapons, cycling races, gear and offhands), `hero_kit_dragon_heads_v1.png` (the 4 dragonborn heads from three sides), `hero_kit_dragon_look_v1.png` (5 dragon types at Look size), `hero_kit_look_v2.png`, `hero_kit_look_back_v2.png`, `hero_kit_faces_v2.png`, `hero_kit_builds_v2.png`, `hero_kit_hair_v2.png`. Map sizes, from before the new heads and weapons: `hero_kit_map_58m_v1.png`, `hero_kit_map_30m_v1.png`, `hero_kit_map_18m_v1.png`.

## A hero as a description

```
{race, build, head, hair, armour, main, offhand, colours: {skin, hair, eyes, cloth}}
```

Sub-types add no shape: they only set `colours.skin` (golem material, dragon type's default). `hair` is ignored on dragonborn and golem. `offhand` applies to one-handed weapons: `shield`, a second one-handed weapon, or empty.

## Pieces

| Piece | Count | Triangles | Notes |
|---|---:|---:|---|
| `hero_base` | 1 | 68 | The stand-in's hex base and ring |
| `hero_body_<race>_<build>` | 21 | 204-294 | Own shape per build. Final size, placed at the origin |
| `hero_armour_<light/medium/heavy>_<race>_<build>` | 63 | 80-230 | Over that body, placed at the origin |
| `hero_head_<race>_<a-d>` | 28 | 60-402 | Pivot at the head's middle. Horns, beards and faceplates are in the head |
| `hero_hair_<style>` | 6 | 82-154 | `short`, `long`, `topknot`, `spiky`, `tail`, `crest`. Pivot at the head's middle, scaled to the race |
| `hero_arm_upper_<kind>`, `hero_arm_fore_<kind>` | 8 | low | `bare`, `chain`, `plate`, `golem`. Length 1 along +Z, radius 1: scaled to fit |
| `hero_hand_<kind>` | 3 | 12-20 | `bare`, `gauntlet`, `golem` |
| Weapons and `hero_shield` | 22 | 24-92 | Below. Fist weapons are one piece, placed on each hand |

152 pieces. A whole hero came to **500-1,256 triangles** in the sheets (a golem lowest, a broad dragonborn with shield and heavy armour highest). Bandits are 386-557. Ethan accepts heavy armour and dragon heads being heaviest until a phone test says otherwise (Nov 4, 2026).

## Grips and weapons

All 21 of the Fighter's weapons have a mesh (Ethan, Nov 4, 2026). 07's Pose library has a pose per weapon; this shares a few between weapons and simplifies others, until the real pass.

| Grip | Weapons | Hands | Pose, against 07 |
|---|---|---|---|
| `forward` | `longsword`, `shortsword` | One | Point forward. Longsword as 07; shortsword isn't its backhand slash |
| `raised` | `mace`, `battleaxe` | One | Raised high. Mace as 07; battleaxe isn't held low |
| `fencer` | `rapier` | One | En garde, as 07, without the stance in the legs |
| `slash` | `scimitar` | One | Out to the side. 07's mid-spin, without turning the body |
| `reverse` | `dagger` | One | Reverse grip, low. 07's crouch isn't there |
| `point` | `wand` | One | Arm out, as 07 |
| `planted` | `greatsword`, `warhammer` | Two | Resting on the base, as 07 |
| `shoulder` | `greataxe` | Two | On the shoulder, as 07 |
| `sweep` | `glaive` | Two | Across the body, blade out and up. 07's mid-sweep, roughly |
| `upright` | `spear`, `halberd` | One | At attention. As 07 for the halberd; not the spear's wind-up or braced pike, as a pike reaches well past its cell. Both leave the left arm free |
| `across` | `staff` | Two | Guard, as 07. With an offhand it uses `upright`, as 07's planted staff |
| `bow` | `shortbow`, `longbow` | Two | Held out, drawn at the cheek. No arrow |
| `aim` | `crossbow` | Two | Stock at the shoulder, as 07 |
| `guard` | `gauntlets` | Fists | Fists up, lower than 07's "at the face", as they hid heads there |
| `haymaker` | `brass_knuckles` | Fists | One fist back, as 07 |
| `stance` | `wraps` | Fists | One forward, one at the hip, as 07 |

**Offhand:** `shield`, a second one-handed weapon, or empty, on the one-handed weapons, including `spear` and `staff`.

**Left out:** two-handed longsword, battleaxe and spear poses (they'd use their one-handed ones); poses that move the legs; helmets, leggings, boots and gloves as gear; enchantment looks; other classes.

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

A hero is one merged mesh, rebuilt from its description once per hero and per change. **Checked:** for 6 heroes, following the steps below from the glb and the table alone gave the same triangle counts and bounds as Blender's assembler, and every piece name exists. Not yet run in Godot.

**1. The parts.** With `T` the JSON, and `row = T.races[race].builds[build]`:

| Part | Piece | Matrix |
|---|---|---|
| Base | `hero_base` | identity |
| Body | `hero_body_<race>_<build>` | identity |
| Armour, unless `none` | `hero_armour_<tier>_<race>_<build>` | identity |
| Head | `hero_head_<race>_<head>` | `row.head` |
| Hair, unless `T.hairless` has the race or there's none picked | `hero_hair_<style>` | `row.hair` |
| Arms | `hero_arm_upper_<kind>`, `hero_arm_fore_<kind>`, `hero_hand_<fist>` | `pose.right` then `pose.left`, three each, in that order |
| Main weapon | `hero_<main>` | `pose.main` |
| Offhand | `hero_shield` or `hero_<offhand>` | `pose.offhand` |
| Fist weapon, instead of main | `hero_<main>`, twice | `pose.fists`, right then left |

- `pose = row.poses[main][none | shield | second]`. Only weapons in `T.one_handed` have `shield` and `second`. `second` holds whichever one-handed weapon is the offhand.
- `kind`: `golem` for a golem, otherwise `bare` for no or light armour, `chain` for medium, `plate` for heavy.
- `fist`: `golem` for a golem, `gauntlet` for heavy armour, otherwise `bare`.
- Weapon names in the data have `brass_knuckles` with an underscore.
- **Matrices** are 12 numbers: the basis's x, y and z columns, then the origin. They're in the glb's frame, which is Godot's: `Transform3D(Basis(Vector3(m0, m1, m2), Vector3(m3, m4, m5), Vector3(m6, m7, m8)), Vector3(m9, m10, m11))`.
- **Scale isn't uniform** on arms and planted weapons. Transform normals by the inverse transpose, or recompute them.
- A mini faces +Z in the glb's frame (-Y in Blender), with its pivot at the base's centre on the ground, as the enemy minis do.

**2. The colours.** After merging, go through the vertex colours, converting each from linear to sRGB bytes (`Color.linear_to_srgb()`):

- **Blue 253 or more is a mark.** Nothing else in the kit has it.
- **Zone:** red ÷ 20, rounded: 1 skin, 2 hair, 3 eyes, 4 cloth.
- **Shade:** green ÷ 100.
- **New colour,** in linear: the swatch's linear colour × shade^2.2, each clamped to 1. Alpha 1.
- Everything else stays as it is.

Godot may hold imported vertex colours in 8 bits, in linear, which loses precision at the dark end. Rounding the zone copes with that by my arithmetic, and the shade would be off by a few percent. Worth one test.

**3. Elsewhere.**

- **Same material as the other minis:** `Kit.combat_materials`, once.
- **Height:** `T.races[race].height` is included in all the pieces and matrices; don't scale again.
- **The Look step:** a rebuild on each pick. Its cost hasn't been measured. If it's slow, keep the pieces as separate nodes there, swapping colours per piece, and merge when done.
- **Dragon type and golem sub-type** change only `colours.skin`. Defaults are in `T.dragon_types` and `T.swatches.skin`.
- **Saves and multiplayer:** send the description, not the mesh.
- **`EncounterView` and the party** can both take a hero the same way later. Companions aren't in this kit.

## Weak spots

- At Look size these are still chunky low-poly, not Chelmsford's sculpted look.
- Hair is blotchy at the back of some heads, with a sliver of skin on the human's short style.
- Builds now differ, but slim is close to average. Tunics are flat.
- Small weapons (wand, dagger) barely read below Look size. Gauntlets are bulky on a broad or golem arm, and fists up partly crowd the head.
- Faces read well close up. At 58 m they're gone: only colour, height, horns and big gear show.
- Not done: anything in Godot, and a phone test for triangle counts. A hero tops out around 1,260.
