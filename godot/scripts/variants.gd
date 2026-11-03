class_name Variants
extends RefCounted
## Region variants, from art/scripts/variants.py (VARIANTS, LANDMARKS, LANDMARK_CENTRES) and render_preview.py
## (TIER1). A variant has the same pieces as its terrain under its own name; edge pieces are picked by the terrain.
## A landmark tile's name is the landmark's (e.g. "treeoflife"); it counts as its variant's terrain.

## Each terrain's tier 1 variant (render_preview.TIER1).
const TIER1 := {"forest": "deep_forest", "plains": "meadows", "hills": "highlands", "farmland": "windmill_country",
	"village": "market_town", "river": "delta", "swamp": "bog", "desert": "wasteland", "ruins": "excavation"}

## Tier 2 variants with art (DOCS: design/02 -> Region variants and locations; the class variant is in the
## pool too). Terrains not listed have no tier 2 art yet and keep their terrain's look.
const TIER2 := {"forest": ["fey_wood", "dark_wood", "heartwood"],
	"farmland": ["haunted_homesteads", "raided_farms", "cider_orchards"],
	"plains": ["battlefield", "stormy_plains", "tourney_fields"],
	"hills": ["snowy_peaks", "volcanic_peaks", "monastery_heights"],
	"village": ["fortified_town", "slums", "scholars_town"],
	"river": ["great_lake", "rapids", "still_waters"]}

## Display names of the tier 2 variants and their core locations (DOCS: design/02 -> Region variants and locations).
const TIER2_NAMES := {"fey_wood": ["Fey wood", "Fey Court"], "dark_wood": ["Dark wood", "Spider Nest"],
	"heartwood": ["Heartwood", "Tree of Life"], "haunted_homesteads": ["Haunted homesteads", "Abandoned Barn"],
	"raided_farms": ["Bandit-raided farms", "Militia Barn"], "cider_orchards": ["Cider orchards", "Harvest Festival"],
	"battlefield": ["Steppe/battlefield", "Old Battlefield"], "stormy_plains": ["Stormy plains", "Thunderbird Nest"],
	"tourney_fields": ["Tourney fields", "Training Grounds"], "snowy_peaks": ["Cold, snowy peaks", "Yeti Cave"],
	"volcanic_peaks": ["Volcanic peaks", "Salamander Den"], "monastery_heights": ["Monastery heights", "Library"],
	"fortified_town": ["Fortified town", "Keep"], "slums": ["Slums", "Black Market"],
	"scholars_town": ["Scholars' town", "College"], "great_lake": ["Great lake", "Lake Serpent's Lair"],
	"rapids": ["Rapids", "Troll Bridge"], "still_waters": ["Still waters", "Meditation Rock"]}

## Each variant's core landmark piece (variants.LANDMARKS, inverted). Variants not listed have no landmark art yet.
const LANDMARK_OF := {"deep_forest": "hiddenshrine", "fey_wood": "feycourt", "dark_wood": "spidernest",
	"heartwood": "treeoflife", "windmill_country": "greatwindmill", "haunted_homesteads": "abandonedbarn",
	"raided_farms": "militiabarn", "cider_orchards": "harvestfestival", "meadows": "nomadcamp",
	"battlefield": "oldbattlefield", "stormy_plains": "thunderbirdnest", "tourney_fields": "traininggrounds",
	"highlands": "clanhall", "snowy_peaks": "yeticave", "volcanic_peaks": "salamanderden",
	"monastery_heights": "library", "market_town": "tradinghouse", "fortified_town": "keep", "slums": "blackmarket",
	"scholars_town": "college", "delta": "riverport", "great_lake": "serpentlair", "rapids": "trollbridge",
	"still_waters": "meditationrock"}

## Landmark -> its variant (variants.LANDMARKS).
const LANDMARKS := {"treeoflife": "heartwood", "hiddenshrine": "deep_forest", "feycourt": "fey_wood",
	"spidernest": "dark_wood", "greatwindmill": "windmill_country", "abandonedbarn": "haunted_homesteads",
	"militiabarn": "raided_farms", "harvestfestival": "cider_orchards", "nomadcamp": "meadows",
	"oldbattlefield": "battlefield", "thunderbirdnest": "stormy_plains", "traininggrounds": "tourney_fields",
	"clanhall": "highlands", "yeticave": "snowy_peaks", "salamanderden": "volcanic_peaks",
	"library": "monastery_heights", "tradinghouse": "market_town", "keep": "fortified_town", "blackmarket": "slums",
	"college": "scholars_town", "riverport": "delta", "serpentlair": "great_lake", "trollbridge": "rapids",
	"meditationrock": "still_waters"}

## Landmarks that are a centre piece only: their tile uses the variant's wedges (variants.LANDMARK_CENTRES).
const LANDMARK_CENTRES := ["feycourt", "spidernest", "greatwindmill", "abandonedbarn", "militiabarn", "harvestfestival",
	"nomadcamp", "oldbattlefield", "thunderbirdnest", "traininggrounds", "clanhall", "yeticave", "salamanderden",
	"library", "tradinghouse", "keep", "blackmarket", "college", "riverport", "serpentlair", "trollbridge", "meditationrock"]

## How much higher a raised region's pieces stand (variants.RAISE), and where a ledge's top path comes out.
const RAISE := 5.0

## Where the small mill stands in a centre_mill's yard (variants.SMALL_MILL_SPOT), and the Great Windmill's sails
## in its centre's frame (variants.MILL_HUB): plan x, y, then height.
## The River Port's parts that bob, in its frame (variants.LANDMARK_PARTS).
const PORT_PARTS := {"riverport_cog": Vector2(1.28, 1.35), "riverport_barge": Vector2(1.3, -1.85), "riverport_raft": Vector2(1.62, -0.72)}
const SMALL_MILL_SPOT := Vector2(0, 1.66)
const MILL_HUB := Vector3(0.8, 0, 3.15)

## Each variant's (and landmark's) ground colour (variants.VARIANTS, third field): the engine recolours its
## terrain's base slab.
const GROUND := {"deep_forest": "deep_forest", "meadows": "plains", "highlands": "highland_grass",
	"windmill_country": "plains", "market_town": "cobble", "delta": "plains", "bog": "bog",
	"wasteland": "wasteland", "excavation": "plains",
	"fey_wood": "fey_wood", "dark_wood": "dark_wood", "heartwood": "heartwood",
	"treeoflife": "heartwood", "hiddenshrine": "deep_forest", "feycourt": "fey_wood", "spidernest": "dark_wood",
	"haunted_homesteads": "haunted", "raided_farms": "raided", "cider_orchards": "orchard_grass",
	"battlefield": "steppe", "stormy_plains": "stormy", "tourney_fields": "mown", "nomadcamp": "plains",
	"oldbattlefield": "steppe", "thunderbirdnest": "stormy", "traininggrounds": "mown",
	"greatwindmill": "plains", "abandonedbarn": "haunted", "militiabarn": "raided", "harvestfestival": "orchard_grass",
	"snowy_peaks": "snow_ground", "volcanic_peaks": "ash_ground", "monastery_heights": "hill_grass",
	"clanhall": "highland_grass", "yeticave": "snow_ground", "salamanderden": "ash_ground", "library": "hill_grass",
	"fortified_town": "cobble", "slums": "mud_ground", "scholars_town": "pale_paving", "tradinghouse": "cobble",
	"keep": "cobble", "blackmarket": "mud_ground", "college": "pale_paving", "great_lake": "plains", "rapids": "plains",
	"still_waters": "plains", "riverport": "plains", "serpentlair": "plains", "trollbridge": "plains", "meditationrock": "plains"}

static var _base := {}


## The terrain a tile counts as (variants.terrain_of): a variant's or landmark's terrain, else the name itself.
static func terrain_of(name) -> String:
	if name == null:
		return ""
	if _base.is_empty():
		for t in TIER1:
			_base[TIER1[t]] = t
		for t in TIER2:
			for v in TIER2[t]:
				_base[v] = t
		for lm in LANDMARKS:
			_base[lm] = _base[LANDMARKS[lm]]
	return _base.get(name, name)


## Whose wedges a tile uses: its own, or its variant's for a centre-only landmark (variants.wedges_of).
static func wedges_of(name: String) -> String:
	return LANDMARKS[name] if name in LANDMARK_CENTRES else name


static func is_water(name) -> bool:
	return terrain_of(name) == "river"
