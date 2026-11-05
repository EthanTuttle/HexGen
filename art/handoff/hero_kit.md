# Hero mini kit (draft, not exported)

Scripted hero minis for the first playable (design/06 → Hero minis), replaced later by 07's pipeline. **Not exported yet: this waits on the contact sheets.** Race shapes, heads, hair, armour looks and which weapons come first are proposals. Heights and swatches start from the v22b mockup.

- **Scripts:** `art/scripts/build_hero_kit.py`, `art/scripts/render_hero_kit.py`. Blend: `art/minis/heroes/hero_kit_v1.blend`.
- **Previews (`art/preview/`):** `hero_kit_look_v1.png` and `hero_kit_look_back_v1.png` (8 combos at Look size), `hero_kit_faces_v1.png` (all 28 heads), `hero_kit_builds_v1.png` (3 builds in 3 races, then the 4 armour tiers), `hero_kit_hair_v1.png`, `hero_kit_map_58m_v1.png`, `hero_kit_map_30m_v1.png`, `hero_kit_map_18m_v1.png` (with bandits, on a plains patch).

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
| `hero_head_<race>_<a-d>` | 28 | 60-332 | Pivot at the head's middle. Horns, beards and faceplates are in the head |
| `hero_hair_<style>` | 6 | 82-154 | `short`, `long`, `topknot`, `spiky`, `tail`, `crest`. Pivot at the head's middle, scaled to the race |
| `hero_arm_upper_<kind>`, `hero_arm_fore_<kind>` | 8 | low | `bare`, `chain`, `plate`, `golem`. Length 1 along +Z, radius 1: scaled to fit |
| `hero_hand_<kind>` | 3 | 12-20 | `bare`, `gauntlet`, `golem` |
| Weapons and `hero_shield` | 12 | 24-92 | Below |

A whole hero came to **500-1,184 triangles** in the 8 combos (golem lowest, dragonborn with shield and heavy armour highest). My 500-700 target didn't hold once faces got better. Bandits are 386-557.

## Grips and weapons

07's Pose library has a pose per weapon. This starts with 6 grips, which breaks that rule until the real pass.

| Grip | Weapons | Pose |
|---|---|---|
| `forward` | `longsword`, `shortsword` | One-handed, point forward |
| `raised` | `mace`, `battleaxe` | One-handed, raised high |
| `planted` | `greatsword`, `warhammer` | Both hands on top, resting on the base |
| `shoulder` | `greataxe` | Carried on the shoulder |
| `upright` | `spear`, `halberd` | Upright at attention. Not 07's braced spear, as a pike reaches well past its cell |
| `bow` | `shortbow`, `longbow` | Held out, drawn at the cheek. No arrow |

**Left out of poses (07's own poses wait):** two-handed longsword and battleaxe, spear braced or wound up, shortsword slash, battleaxe low.

**Left out of meshes:** rapier, scimitar, dagger, glaive, staff, wand, crossbow, gauntlets, brass knuckles, wraps. The Gear step offers Fighters all of them, so `FALLBACK` in the script shows a stand-in: short sword for rapier, scimitar, dagger and wand, halberd for glaive, spear for staff, short bow for crossbow, mace for the fist weapons. These are placeholders that will look wrong. Either the Gear step hides them for the first playable, or they get their own meshes next.

**Also left out:** helmets, leggings, boots and gloves as gear, enchantment looks, other classes.

## Race shapes (proposals)

| Race | Height | Shape | Head |
|---|---:|---|---|
| Human | 1.0 | The middle of everything | Skin, four faces |
| Elf | 1.0 | Long legs, narrow, thin arms | Narrow, tall pointed ears, slightly bigger eyes |
| Dwarf | 0.84 | Wide shoulders and hips, thick limbs, short legs | Wide, big nose, a beard per head in the hair colour |
| Halfling | 0.74 | Small, a big head for its size | Big eyes, small nose, slightly pointed ears |
| Golem | 1.04 | Blocks at shoulders and fists, seam at the waist, a cloth at the waist | Four faceplates, glowing eyes |
| Dragonborn | 1.08 | Tall, deep chest, heavy tail to the left | Long snout, soft jaw, big eyes, horns, spines; four snout and horn shapes |
| Tiefling | 1.0 | Lean, thin spade tail | Glowing eyes with no whites, horns per head in a dark shade of the skin |

## Swatches (proposals)

Unchanged from v22b, six each: `SWATCHES` in the script holds skin per race, the golem's three materials, hair, eyes and cloth. Dragon types default to `red` #B8463A, `blue` #4E7FB8, `white` #DCE3E8, `black` #3A3A40, `green` #5E9A5A. The dragonborn's sixth, gold #C9A24A, has no type in the docs.

Worth a look: `white` dragonborn is close to steel, and the sixth tiefling colour #E3B9A0 reads as human skin.

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
- Faces read well close up. At 58 m they're gone: only colour, height, horns and big gear show.
- Not done: the export and its table, runtime colour swap, anything in Godot.
