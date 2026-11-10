class_name RuinHalls
extends RefCounted
## Port of art/scripts/ruin_structure.py's block_props and outpost_props (tiles v92 corner halls, v93 Overrun outpost;
## art/handoff/ruins_kit.md): a third of a roofless hall at each of a ruins tile's six corners, reaching the tile's edge on a
## side where the ruins carry on. An outpost tile stands the same halls recoloured, with one or two dug into a burrow.
## Worked out from the map, so a tile re-picks its halls whenever it's rebuilt (a neighbour placed or a region finishing).

## Tiles that stand halls and count as ruins for their neighbours (ruin_lands.LOOKS). Haunted ruins aren't ported yet.
const LOOKS := ["ruins", "overrun_outpost", "haunted_ruins"]
const VARIANTS := 3          # ruin_structure.VARIANTS_PER_TAKE
const BURROW_TWO := 0.5      # share of outpost tiles with two burrows
const BURROW_AT := Vector2(3.5, 0.0)   # in a hall's frame; the burrow's mouth turns to face the tile's middle


## (piece, x, y, spin) for tile t's halls, tile-local plan coordinates, or [] for a tile that stands none.
static func props(name: String, terrains: Dictionary, t: Vector2i) -> Array:
	if name == "ruins":
		return halls(terrains, t)
	if name == "overrun_outpost":
		return outpost(terrains, t)
	return []


## block_props: corner c's variant by a hash; lo and hi, whether the neighbours across edges c and c + 1 are ruins.
static func halls(terrains: Dictionary, t: Vector2i) -> Array:
	var out := []
	for c in 6:
		var lo := int(terrains.get(t + Hex.NEIGHBOURS[c]) in LOOKS)
		var hi := int(terrains.get(t + Hex.NEIGHBOURS[(c + 1) % 6]) in LOOKS)
		var n := int(GroundCover.hash01(t.x * 6 + c, t.y, 51) * VARIANTS)
		out.append(["ruin_hall_%d_%d%d" % [n, lo, hi], 0.0, 0.0, deg_to_rad(30.0 + 60.0 * c)])
	return out


## outpost_props: the plain halls recoloured; the corners with the lowest hashes dig a burrow.
static func outpost(terrains: Dictionary, t: Vector2i) -> Array:
	var count := 2 if GroundCover.hash01(t.x, t.y, 54) < BURROW_TWO else 1
	var corners := range(6)
	corners.sort_custom(func(a, b): return GroundCover.hash01(t.x * 6 + a, t.y, 52) < GroundCover.hash01(t.x * 6 + b, t.y, 52))
	var dug := corners.slice(0, count)
	var out := []
	var c := 0
	for h: Array in halls(terrains, t):
		var n_join: String = h[0].trim_prefix("ruin_hall_")
		var spin: float = h[3]
		if c in dug:
			out.append(["outpost_hall_%s_burrow" % n_join, 0.0, 0.0, spin])
			var at := BURROW_AT.rotated(spin)
			var kind := "scrap" if GroundCover.hash01(t.x * 6 + c, t.y, 53) < 0.5 else "timber"
			out.append(["outpost_burrow_" + kind, at.x, at.y, spin + PI])
		else:
			out.append(["outpost_hall_" + n_join, 0.0, 0.0, spin])
		c += 1
	return out
