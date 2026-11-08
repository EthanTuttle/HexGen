# Attack motions

Whole-mini moves plus effects, one per kind of action (07 → Characters are tabletop-style minis). Ethan picked these on Nov 7, 2026 (verdicts in `art/reviews.md`). This is the recipe for rebuilding them in Godot as tweens. The source is `art/scripts/render_attack_motions.py`: each `k_<kind>` function holds the exact curves, and the picked option is the branch named below. The previews are in the shared notes folder under `attack-motions/` (`attack_<kind>_v1.mp4`, `attack_cone_v2.mp4`).

**Cone:** Ethan picked cone v2 B, together (Nov 7, 2026): see the last section.

## Ground rules

- **Units:** a cell is 1.0 across its flats, and a mini stands about 1.3 tall. Times are seconds from the move's start, which is once the coins have finished flipping (07 → Combat flips come first).
- **Only the whole mini moves.** It can move, lean, spin, scale and hop. There's no limb animation.
- **Leaning** tips the mini toward a direction. Past about 4° it rocks on the base's edge on that side, 0.42 from the centre. The pivot slides out from the centre: `pivot = dir * 0.42 * min(1, degrees / 4)`. A hop's lean stays on the centre.
- **Curves:**
  - `bump(u) = sin(πu)`
  - `out(u) = 1 - (1-u)²`
  - `in(u) = u²`
  - `smooth(u) = u²(3 - 2u)`
  - `settle(v) = (1-v)² · cos(1.5πv)`: 1 down to 0, with one small overshoot
  - here `u` is the share of a step's time that has passed
- **Effects** are unlit flat colours that fade by alpha and cast no shadows. Bursts and sparks sit 0.22 toward the camera from their point, so the minis don't hide them.
- **Effect pieces:**
  - **star:** low-poly spikes from a point, splayed outward and a little up; each spike is a four-sided pyramid
  - **ring:** a flat band on the ground
  - **puff:** a low-poly ball (icosphere, 0–1 subdivisions)
  - **zigzag:** a jagged stroke of 5 segments
  - **crescent:** a flat arc band that tapers to nothing at its tail
- **Flash:** a burst that grows from 40% to 100% of its size with `out` and fades as `1 - u^1.5`, over 0.18 s unless given.
- **Dust:** a ring of N puffs pushing out with `out(u)` to a spread, rising a little, shrinking to 40% and fading as `1 - u²`. Colour `#D8CBB0`, lit, unless given.

## Shared moves

| Move | Recipe |
|---|---|
| **Hop** (basic melee) | 0.32 s. `bump` curve: up 0.35, toward the target 0.3, lean 10° on the base's centre. The hit lands at 0.16, at the top |
| **Recoil** (hit A) | Starts at the hit. Tips 16° away from the blow on the far edge and slides 0.12 away. It gets there in 0.07 s (`out`), then settles over 0.35 s (`settle`). A recoil restarts on each new hit |
| **Charge** (every spell with a cast) | Lasts 0.14 s (the summon: 0.14; the burst: 0.12). The caster rises 0.1 with `out`, holds 0.1 s, then drops back over 0.25 s (`smooth`). A ring (width 0.07) round its base shrinks from radius 0.75 to 0.5 in the spell's main colour. It fades in fast, then fades out over 0.12 s once the charge ends |

## The picked motions

| Kind | Pick | Mini | Effects |
|---|---|---|---|
| Basic melee | A, hop | Hop at 0; the target recoils at 0.16 | None |
| Sweep (Sweeping Arc, Whirl) | A, spin | Spins one full turn clockwise over 0.45 (`smooth`), lifting 0.08 (`bump`). The blade starts on the mini's left (facing + 90°) | A white crescent (radius 0.5–0.78, spanning 150°, thickest at the blade) at height 0.45 rides with the blade, trailing behind it. Alpha `min(1, 4u)·(1 - u³)`. Each foe recoils (away from the hero) when the blade passes its bearing |
| Thrust / reach | B, pivot jab | Leans 26° toward the target on its front edge: in by 0.08 (`out`), holds to 0.13, back by 0.33 (`smooth`). Hit at 0.08 | A white streak (6-sided, radius 0.028) at height 0.6 runs along the line to the target from 0.04 to 0.20, shortening from 1.0 to 0.5 long, alpha `1 - u`. A star of 7 spikes, 0.26 long, `#FFF4C8`, flashes at the target. Target recoil 15° |
| Heavy blow | A, big hop slam | Rises 0.6 by 0.26 (`out`), moving 0.32 toward the target (linear) and leaning 10° back. Hangs to 0.30. Drops by 0.38 (`in`), leaning to 22° forward on the front edge. Back home by 0.58 (`smooth`). Hit at 0.38 | A ground ring `#F4E6C0` (width 0.1) at the target's near edge grows from radius 0.25 to 0.85 over 0.3 s, alpha `1 - u`. Dust: 8 puffs, 0.35 s, spread 0.35, size 0.06. A star of 9 spikes, 0.28 long, `#FFE9A8`, over 0.2 s. Target recoil 26°, push 0.2, settle 0.45 |
| Ranged shot | A, straight | Leans back 7° (`bump`) from 0.08 to 0.28 | The arrow (about 0.63 long: wood, iron head, pale fletching) leaves at 0.08 from height 0.55 and flies straight to the target at height 0.42 in 0.18 s. Behind it runs a white trail, 0.016 radius and up to 0.75 long, alpha 0.8. Hit at 0.26: target recoil 14°, dust of 5 puffs `#E8E0CC`, 0.25 s, spread 0.12, size 0.035 |
| Thrown | A, snap throw | Leans 12° forward by 0.08 (`out`), back by 0.30 (`smooth`) | The dagger (about 0.42 long) leaves at 0.08 from height 0.62. It flies 0.26 s on an arc 0.18 high to the target at height 0.5, turning end over end 2.5 times. Hit at 0.34: target recoil 14°, star of 7 spikes, 0.24 long, `#FFF4C8` |
| Firebolt | Orb | Charge (ring `#FF8A2A`) | An orb (radius 0.13, `#FFD24A`) flies straight from height 0.75 to the target at 0.5, from 0.14 to 0.36. Five trailing orbs `#FF8A2A` (radius 0.1, then 15% smaller each) follow 5%, 10% … of the flight behind it, alpha 0.9. Hit at 0.36: a star of 9 spikes, 0.34 long, `#FFD24A`, over 0.2 s; then from 0.38 a star of 7 spikes, 0.44 long, `#FF8A2A`, over 0.25 s. Standard recoil |
| Frost Ray | Ray | Charge (ring `#8FD8FF`) | At 0.14 a beam from the caster (height 0.75) to the target (0.5) reaches full length in 0.05 s (`out`). Its core is 6-sided, radius 0.03, `#E6F7FF`, flickering ±25% (`sin(90t)`). Round it is an outer glow, radius × 2.2, `#8FD8FF`, alpha 0.45. Both thin out from 0.36 to 0.46. Hit at 0.19: a star of 9 spikes, 0.3 long, `#E6F7FF`, over 0.3 s. Standard recoil |
| Magic Bolt | Darts | Charge (ring `#B07CFF`) | Three darts (orbs radius 0.1, `#EBDDFF`) leave at 0.14, 0.20 and 0.26, each flying 0.22 s. The outer two curve out ±0.55 to the sides (`bump`); the middle one arcs up 0.15. Hits at 0.36, 0.42, 0.48: recoils of 8°, 8°, 10°. Star of 9 spikes, `#EBDDFF`, at 60% size, 0.15 s, on the first hit; star of 7 spikes, `#B07CFF`, at 60% size, 0.18 s, on the last |
| Touch (Shocking Grasp) | B, charge then tap | Four small zigzags circle the caster, then it hops: start 0.22, 0.24 s long, up 0.16, toward 0.3, lean 12°. Hit at 0.34 | The circling zigzags are `#9FE3FF`, 0.16 long, at heights 0.3, 0.42, 0.54 and 0.66, radius 0.26. They go round twice from 0 to 0.22 and fade out from 0.24 to 0.30. At the hit, five zigzags `#BFEFFF`, 0.4 long, radiate from the contact point. They grow from 60% to 120% over 0.2 s while fading, and flicker at random to 60%. With them, a white core (radius 0.06, at 160% size) flashes for 0.12 s. The foe recoils 12° and shivers sideways ±0.025 at 140 rad/s, dying away over 0.25 s |
| Area burst (Flame Burst) | A, lob + dome | Charge (0.12, ring `#FF8A2A`) | An orb (radius 0.12, `#FFD24A`) is lobbed from 0.12 to 0.32 to the area's centre, on an arc 0.6 high. At 0.32 a dome rises on the centre: an icosphere scaled (1.5, 1.5, 0.9) × `out`, `#FFB347`, alpha `0.75·(1 - u²)` over 0.35 s. The area's cells light as flat hex plates `#FF9A3C`, alpha `0.85·bump` over 0.45 s. Each foe recoils away from the centre at 0.35 |
| Buff / heal (Bless, Healing Word) | A, rising ring | The caster bobs up 0.08 (`bump`) from 0 to 0.24. The ally hops 0.1 (`bump`) from 0.30 to 0.55 | A gold open tube (`#FFD45A`, radius 0.38, height 0.13) rises from the ally's base to 0.87 high from 0.12 to 0.5 (`smooth`). It narrows to 70% and fades as `1 - u³`. Twelve motes (radius 0.055, `#FFF3B8` and `#FFD45A` by turns) set round a circle of radius 0.3 rise from height 0.2 to 1.0, each over 0.35 s, starting 0.02 s apart from 0.2, fading as they go |
| Summon | B, drops in | Charge (ring `#B07CFF`). The summon appears at 0.12, falls from 1.4 high to the cell by 0.34 (`in`), then bounces 0.12 (`bump`) up to 0.46 | The cell lights as a hex plate `#C9A6FF`, alpha `0.8·bump`, from 0.05 to 0.45. Dust on landing at 0.34: 10 puffs, 0.35 s, spread 0.45, size 0.06 |
| Being hit | A, tip back | The recoil above | None |
| Miss | A, sidestep | The target slides 0.3 sideways (across the attack, toward the camera's side) and 0.04 away, leaning 6° that way on its centre. Out by 0.18 from 0.08 (`out`), holds to 0.32, back by 0.55 (`smooth`) | A white whiff crescent (radius 0.16–0.22, spanning 120°) sweeps through where the target stood from 0.14 to 0.30, alpha `0.7·(1 - u)`. A little dust where the target lands: 5 puffs `#E8E0CC`, 0.25 s, spread 0.18, size 0.03 |

## Cone (Breath Weapon): v2 B, together

The breather leans 8° forward and rises 0.06: in by 0.10 (`out`), held to 0.45, back by 0.60. Fourteen puffs (icospheres, `#FF9A3C`, every third one `#FFD27A`) roll out across the cone's ±30°, each over 0.32 s, starting 0.025 s apart. They travel from 0.45 to 3.05 out (`out`), grow from 0.08 to 0.30, sink from height 0.55 to 0.30 and fade as `0.9·(1 - u²)`. The cone's cells light as hex plates `#FF9A3C`, alpha 0.85: on in 0.06 s, held, then off from +0.3 to +0.5. Each foe recoils 14° when the first puffs reach it.

**Picked, B (together):** the puffs start at 0.06, and each cell lights as the first puffs reach it, at about `0.06 + 0.32 · (1 - √(1 - r))`, where r is how far out the cell is (0 at the mouth, 1 at the far edge). Not picked: A, which lit the cells first in a 0.12 s sweep, with the puffs starting 0.12 s later.
