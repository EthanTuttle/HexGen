# Combat art brief

Set up Nov 2, 2026 · @Ethan · Part of the [Index](../00 Index.md)

For the Combat Art session: enemy minis and combat map art, drafted with Blender scripts. It works the same way as the tile art session.

## Read first

- `art/README.md`, especially Rules for the art session. They all apply here.
- `design/07 Presentation.md`: Art direction, minis, scale, and the combat screens.
- `design/06 Multiplayer & tech.md` → Engine prototype: units and tile build.
- `design/01 World & story.md` → Enemies, and `design/02 Map & exploration.md` → Region variants.
- `art/combat/combat_cells_v1.blend`, `art/minis/standins/`, and `art/handoff/forest_kit.md` for how a finished kit is handed off.

## How to work

- Own branch and worktree from main: `claude/art-combat`, in `../HexGen-claude-art-combat`. Don't touch the old Unity branch; Unity is no longer being built.
- Hand-off goes through the planner session, never directly to Godot. Ethan reviews previews before anything reaches the engine.
- Never overwrite: versioned files only. The tile art session also uses `art/`, so keep your scripts and files separate from its (`art/minis/enemies/`, `art/combat/`) and don't use its `tiles_vN` numbers.
- Content comes from Ethan. Where the docs don't decide a look, offer options through the planner rather than settling it.

## First job: enemy minis

Wolves and giant spiders. The enemy roster is still open, so these are the first to be made, not a settled roster with stats.

- Scripted low-poly, final quality, in the tile art's flat vertex-colour style, using the shared kit material.
- True scale. Minis stand on the same hex base as the stand-ins, with the pivot at the base centre at ground level and the same facing. Oversized creatures may need more than one cell: flag it rather than deciding.
- No animation. Minis are moved whole (hop, recoil), so a pose has to read on its own from the combat camera.
- Variation: try a plain and an elite version, for Ethan to judge.
- Report triangles per mini. How many enemies a fight can hold isn't decided, so keep them light for the phone and propose a budget.

Previews: a line-up beside a stand-in hero, close-ups, and on the board from the combat camera.

## Forest combat maps

Changed Nov 2, 2026: a fight is an animated zoom into the hex, but it really happens on a separate map outside that hex. Combat maps are custom built to look interesting and give their own tactical challenges, themed to the terrain and variant.

- Maps vary in overall size for more dynamic scenes; cells are flat-top, 1.0 across the flats. The cell base stays a simple, solid shape: never punch it into thin strips or holes. Props and terrain limit the fighting area, not the base's outline (Ethan, Nov 2, 2026).
- Rock can be walkable high ground: thick, clearly stepped raised cells, with a way up. Rules direction in 03: longer ranged range from high ground, and climbing costs AP or a check. No map thinner than the Gorge map, and that thin only with a reason in the scene (a cliff wall along it).
- Don't hold back on trees: full-bodied trees, not thin poles standing between hexes. Obstacles should be varied and can be big, spanning several cells: groves, fallen trunks, big boulders, cliffs, stumps, ruins.
- Build several distinct layouts per forest variant, each with a clear tactical idea (a choke point, a clearing, cover lanes), reusing the cell and prop kit. Say what the idea of each is.
- The combat camera rotates, so tall obstacles such as map-height trees are fine, as long as every cell can be seen from at least one angle of the rotation. Check this for each map (a test would be good). Blocked cells must look blocked.
- The board sits on the combat backdrop, with its soil sides. The zoom into the hex is an engine animation.

Previews: each map from the combat camera with minis on it, plus the kit laid out.

## Report back

Preview paths, triangles and materials, what you decided and what's left for Ethan, and what doesn't work yet. Critique your own previews before reporting, up to 3 passes per round.
