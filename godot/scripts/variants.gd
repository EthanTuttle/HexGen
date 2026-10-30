class_name Variants
extends RefCounted
## Tier 1 region variants, from art/scripts/variants.py (VARIANTS) and render_preview.py (TIER1).
## A variant has the same pieces as its terrain under its own name; edge pieces are picked by the terrain.

## Each terrain's tier 1 variant (render_preview.TIER1).
const TIER1 := {"forest": "deep_forest", "plains": "meadows", "hills": "highlands", "farmland": "windmill_country",
	"village": "market_town", "river": "delta", "swamp": "bog", "desert": "wasteland", "ruins": "excavation"}

## Each variant's ground colour (variants.VARIANTS, third field): the engine recolours its terrain's base slab.
const GROUND := {"deep_forest": "deep_forest", "meadows": "plains", "highlands": "highland_grass",
	"windmill_country": "plains", "market_town": "cobble", "delta": "plains", "bog": "bog",
	"wasteland": "wasteland", "excavation": "plains"}

static var _base := {}


## The terrain a tile counts as (variants.terrain_of): a variant's terrain, else the name itself.
static func terrain_of(name) -> String:
	if name == null:
		return ""
	if _base.is_empty():
		for t in TIER1:
			_base[TIER1[t]] = t
	return _base.get(name, name)


static func is_water(name) -> bool:
	return terrain_of(name) == "river"
