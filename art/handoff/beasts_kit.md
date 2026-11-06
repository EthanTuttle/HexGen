# Ally beasts kit

The Companion ranger's beasts (design/03 → Companion ranger's beast), in the hero kit's style. Ethan approved all four (Nov 5, 2026): wolf v7, bear v3, panther v3, hawk v3, with their scarves, faces and colour options.

- **Models:** `art/export/beasts.glb` (from `art/minis/heroes/beasts_v1.blend`, a copy of `beast_minis_v17.blend` named for the export). One shared `kit` material with vertex colours, like the other minis. Four nodes at the origin.
- **Scripts:** `art/scripts/build_beast_minis.py` (pieces, `BEAST_SWATCHES`, `BEAST_EYES`), `art/scripts/render_beast_minis.py` (review sheets).
- **Previews (`art/preview/`):** solo sheets `beast_wolf_solo_v4.png`, `beast_bear_solo_v2.png`, `beast_panther_solo_v3.png`, `beast_hawk_solo_v3.png` (front, three-quarter, side, back, combat camera, face). Of the final meshes: the six colour options `beast_wolf_colours_v5.png`, `beast_bear_colours_v2.png`, `beast_panther_colours_v2.png`, `beast_hawk_colours_v3.png`, and line-ups beside the ranger with the combat camera `beast_wolf_v5.png`, `beast_bear_v2.png`, `beast_panther_v2.png`, `beast_hawk_v3.png`.

## Pieces

| Piece | Triangles | Height over the ground | Pose |
|---|---:|---:|---|
| `beast_wolf` | 864 | 0.87 at the ear tips | Alert, head up, tail out straight. The scarf round its neck, one tail down the chest, one along the back |
| `beast_bear` | 954 | 0.75 at the head | Broad and heavy on all fours, head up. The scarf |
| `beast_panther` | 1,070 | 0.59 at the head | Long and low, heavy shoulders, head level, tail curling to one side, rosettes. The scarf as a collar, its tail flat along the spine |
| `beast_hawk` | 958 | 1.10 at the wingtips | Landing on a flight stand: wings raised and arched, tail fanned, talons thrust forward, head down. A band on each leg and a short tie from the right one |

Each piece includes the standard hex base with the green ally ring (`#7FBF7A`), the same base as the hero kit's `hero_base`. Triangle counts include the base. A beast is one piece: nothing to assemble, only its colours to swap.

## Scale and facing

- **One cell each.** The pivot is at the base's centre on the ground. A beast faces +Z in the glb's frame (-Y in Blender), as heroes and enemies do.
- **Sizes against a human hero of about 1.3:** the wolf is the enemy wolf's size (back about 0.43). The bear is kept to one cell, so it's shorter than a real bear (hump about 0.66); if it needs to be bigger, the only room is upward. The panther stands about the wolf's size. The hawk's body rides at about 0.86 on its stand.
- Nothing needs scaling in the engine: sizes are in the mesh.

## The hawk's stand

- A stump with a twig on the base and a thick dark rod up to the hawk's belly, all in the one piece (`stand_wood` #5E4430). It's part of the mini, not a separate node.
- Its shadow is painted on the base as flat shapes just above it (`hawk_shadow` #5E4330): wings, body, head and fanned tail as seen from above. So the cell reads as the hawk's wherever the light falls. Keep the engine's own shadow on as well; the painted one doesn't replace it.
- Its wings reach close to the cell's edge (about 0.43 from the centre with the fingers). It's the tallest mini in the kits so far.

## Colours

Beasts use the hero kit's marks and the same swap: see `art/handoff/hero_kit.md` → What Godot needs → 3. The colours. Run that step over a beast's vertex colours once per beast and per change. For a beast the four zones mean:

| Zone | Mark (red ÷ 20) | On a beast |
|---|---:|---|
| `skin` | 1 | The coat (shades for the back, belly side, mouth and rosettes) |
| `hair` | 2 | Markings: pale muzzle, chest, belly, inner ears; the hawk's breast, thighs and underwings |
| `eyes` | 3 | The eyes |
| `cloth` | 4 | The scarf (wolf, bear, panther) or the leg bands and tie (hawk), in the ranger's cloth |

**Checked:** all four zones decode in every beast from the exported glb. Fixed colours (noses, pupils, beak, claws, talons, the stand and the painted shadow) stay as they are.

### Eyes (Ethan, Nov 5, 2026)

**A beast's eye colour is one of four only:** gold `#C9A24A`, green `#4F7A33`, brown `#7A5230`, pale blue `#9CC4DE`. **Never red or violet**: on an animal they read as a foe's. Godot's picker offers only these four for a beast, not the hero kit's full eye list.

### Coats and markings

Six options per beast, each a coat with its markings, as shown on the approved colour sheets. `BEAST_SWATCHES` in the script holds the same values.

| Beast | Coat / markings |
|---|---|
| Wolf | grey `#8E8A84` / `#E4DDD0`; brown `#6B5444` / `#C9B48E`; black `#3A3836` / `#7E7A74`; white `#D8D4CC` / `#F4F1EA`; red `#B0703E` / `#E8CFA6`; fawn `#A89A82` / dark `#5A4E40` |
| Bear | brown `#6B4A32` / `#B08A62`; black `#2F2B29` / `#A88A66`; cinnamon `#9A5E34` / `#D2A878`; grizzly `#7E6650` / `#CDB896`; pale `#DCD4C2` / `#F2EEE4`; ash `#6A625C` / `#A69C90` |
| Panther | black `#2A282E` / `#45414A`; leopard gold `#C9984A` / `#EFDDB4`; tawny `#A97E52` / `#E4D2B0`; snow `#C8C6C0` / `#EEEDE8`; jaguar brown `#8A5A2E` / `#D9BC8E`; slate `#5A5E66` / `#8E929A` |
| Hawk | red-tail brown `#7A5234` / `#E9DCC2`; dark `#3A3532` / `#8A847E`; goshawk grey `#6E7378` / `#DCDDDA`; golden `#8A5E2E` / `#C9A266`; white `#E2DFD8` / `#FAF8F2`; rust `#A85A30` / `#E6C9A0` |

- The panther's rosettes are a dark shade of the coat (`skin` at 0.62), so they all but vanish on black, as on a real black panther.
- **Cloth** is the ranger's own cloth colour from the hero kit's swatches, so beast and ranger match.
- A beast as a description: `{beast: wolf | bear | panther | hawk, colours: {skin, hair, eyes, cloth}}`, with `skin` and `hair` one of that beast's pairs, `eyes` one of the four above, `cloth` the ranger's. Saves and multiplayer send the description.

## Checks

- Winding: `check_winding.py` on `beasts_v1.blend` finds no piece over the limit (CULL 0 of 12).
- Round trip: re-imported from the glb, every node keeps its name, triangle count, bounds and vertex colours, with its pivot at the origin.
- Not done: anything in Godot, and a phone test for triangle counts.

## Weak spots

- The hawk's wings are seen edge-on from straight ahead at eye level, as a real wing would be. From the combat camera they read as broad wings.
- The panther's mouth line barely shows on a black coat except close up.
- The hawk's underwings are its markings colour, not barred as on a real red-tail.
