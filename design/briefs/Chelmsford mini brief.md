# Chelmsford mini — 3D artist brief

Last updated Oct 21, 2026 · @Ethan · Part of the [Index](../00 Index.md)

> **Superseded (Oct 29, 2026):** minis are now made with AI image-to-3D and cleaned up in Blender instead of by a 3D artist ([Presentation](../07 Presentation.md) → Art direction). Kept for reference: its notes on pose, gear, attach points and the base still apply to the cleanup.

What we need sculpted, and what's already decided. Everything here comes from the design docs; items still open are marked **Open** and must be agreed before or during sculpting. Rules live in the linked docs; this brief only gathers them.

## The game in one paragraph

HexGen is a card-driven, D&D-style hex-crawl RPG for PC and mobile. The world is built from hex tiles in a stylised, low-poly look inspired by Dorfromantik. Characters appear as tabletop-style miniatures standing on that board, in exploration and on a tactical hex grid in combat. (Art direction: [Presentation](../07 Presentation.md) → Art direction.)

## Who Chelmsford is

| | |
| --- | --- |
| Role | Companion on the Folk Hero path ([World & story](../01 World & story.md) → Folk Hero path cast) |
| Race | Blue (lightning) dragonborn ([Classes & combat](../03 Classes & combat.md) → Races) |
| Class | Cleric, default subclass Order of Good (support: buffs, healing, protection) |
| God | Aurora, the sun goddess; her sun is his emblem |
| Personality | A British chap whose mother the hero saved years ago; he has sworn loyalty to the hero |
| Home | The Keep (a fortified town) |

## Look and fidelity

- **Fidelity target:** a sculpted, high-detail tabletop miniature, like Reference 3 in [Presentation](../07 Presentation.md) → Art direction: distinct armour plates, chainmail and scale textures, cloth with texture, clawed feet and a sculpted tail. Reference 3 is a commercial mini used for detail level only; Chelmsford must be an original design.
- **Proportions:** heroic tabletop. The head, hands and gear are slightly oversized so he reads at small size.
- **Pose:** fixed (minis are not animated). For this loadout: mace raised high in his right hand, round shield on his left arm, a steady stance. Because weapons can be swapped, poses follow the weapon category held, not the character; this is his mace pose with the shield arm variant. Poses are authored once on a simple posing skeleton (no animation) and shared across body types, so build him on that skeleton. Cleric weapons mean he also needs these poses from the pose library: warhammer (head resting on the ground), staff one-handed (staff planted, free hand raised as if casting) and staff two-handed (quarterstaff guard, held across the body). The shield arm variant holds the shield raised in front, across the chest; with no shield, his free hand keeps the base pose. See [Presentation](../07 Presentation.md) → Art direction and Pose library. Only the active weapon set shows, and belt consumables don't show.
- **Reads at small size:** in combat on a phone he is about 30–50 px tall, so the silhouette must be clear on its own: horns, snout, raised mace, round shield and curled tail.

## Gear and details

**Gear is swappable.** Minis show the gear a character has equipped, everything except amulets and rings: weapons, shield, armour, helmet, leggings, boots and gloves ([Presentation](../07 Presentation.md) → Art direction). Build the mace, shield and armour pieces as separate parts that fit his body type, with attach points (hands, forearm, back), not sculpted into the body. Enchantments (e.g. fire, ice, lightning on a weapon) are added by the game as effects on the part.

Mockup loadout to sculpt first (from the combat and gear mockups); Clerics can use maces, warhammers and staves, light and medium armour, and shields ([Weapons & gear](../04 Weapons & gear.md) → Class gear).

- Head: dragon head with a snout, cream horns swept back, a lighter scaled throat, small spines down the back of the head.
- Body: medium armour (steel) under a cream cleric's tabard with Aurora's gold sun on the front **and on the back**; leather belt with a gold buckle; steel pauldrons.
- Right hand: a flanged mace, raised.
- Left arm: a round shield with a gold rim and Aurora's sun on the front; the back is plain wood with leather straps over his forearm.
- Tail: blue, curling out to his left behind the legs.
- Legs: armoured greaves and boots.

## Base

- A plain wooden **hex** base sized to fill one hex of the combat grid, with a thin coloured ring around its top edge.
- **Open:** whether the ring colour marks the character (his colour is light blue) or the side (ally/enemy).
- The model's pivot is the centre of the base, at ground level: the game stands the mini on the centre of its hex and rotates the board around it.

## How he's built

Follow the mini production pipeline in [Presentation](../07 Presentation.md) → Art direction:

1. Dragonborn base mesh in the shared A-pose, with a tail bone.
2. The shared skeleton, resized to dragonborn proportions.
3. His poses from the pose library (mace with the shield arm variant first).
4. Gear as separate meshes: mace and shield attached to hand and forearm points; armour, tabard, greaves and boots bound to the skeleton and fitted to the dragonborn body (helmets must clear his horns).
5. High-detail sculpt baked onto a lighter game model for mobile.

## Motion (done in the game, not in the model)

- No rig or skeletal animation. The whole mini moves as one piece.
- Attacking: a small hop. Taking a hit: a short recoil. These are engine tweens, so the model only needs a sensible pivot at the base.
- **Open:** how minis move between hexes (slide, small hops, or lift and set down) and how spells, healing, misses and being downed read.

## Reference art

- Turnaround: the HexGen · Minis (working) canvas, artboards **Chelmsford v3a** (interactive, rotates in 60° steps) and **v3b** (turnaround sheet). Drawn views: front three-quarter, right side, back three-quarter; the other three are mirrors, so the mace and shield swap hands in them and are not true references.
- Proportions and pose: artboard **v2a**.
- Lighting in reference art: from the top left.

## Open before sculpting

- [ ] **Paint:** painted, unpainted resin (like Reference 3), or mixed. This decides whether textures carry colour or just a single material.
- [ ] **Technical budget for PC and mobile:** polygon count, levels of detail, texture size and format, and file format. Not decided; to agree with the artist and the engine choice.
- [ ] **Base ring colour:** the character's colour or the side's colour.
- [ ] **Missing reference views:** a true left side and back for the mirrored angles, if the artist needs them.
