# Hero mini kit (draft, not exported)

Scripted hero minis for the first playable (design/06 → Hero minis), replaced later by 07's pipeline. **Not exported yet: this waits on the contact sheets.** Race shapes, heads, hair, armour looks and which weapons come first are proposals. Heights and swatches start from the v22b mockup.

- **Scripts:** `art/scripts/build_hero_kit.py`, `art/scripts/render_hero_kit.py`. Blend: `art/minis/heroes/hero_kit_v2.blend`.
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

1. **Assembler:** place each piece at its matrix and merge into one mesh per hero, once per hero and per change. `assemble()` in the script is the model. On the Look step that's a rebuild on each pick; its cost hasn't been measured.
2. **Placements:** `layout()` in the script gives the list. At export it becomes a table (race, build, weapon, offhand → pieces and matrices), so Godot needs no pose maths.
3. **Colour marks:** in sRGB, a vertex colour with blue 255 and red a multiple of 20 is a mark: red ÷ 20 is the zone (1 skin, 2 hair, 3 eyes, 4 cloth), green ÷ 100 is the shade (in Blender: swatch x shade^2.2 in linear). All other colours stay. Colours in the glb are linear, so convert first. Marks look wrong if a piece is drawn unassembled.
4. **Non-uniform scale:** arms are stretched, and planted weapons a little, so normals must be recomputed, not just moved.
5. **Saves and multiplayer:** the description, not the mesh.

## Weak spots

- At Look size these are still chunky low-poly, not Chelmsford's sculpted look.
- Hair is blotchy at the back of some heads, with a sliver of skin on the human's short style.
- Builds now differ, but slim is close to average. Tunics are flat.
- Small weapons (wand, dagger) barely read below Look size. Gauntlets are bulky on a broad or golem arm, and fists up partly crowd the head.
- Faces read well close up. At 58 m they're gone: only colour, height, horns and big gear show.
- Not done: the export and its table, runtime colour swap, anything in Godot.
