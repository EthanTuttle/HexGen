class_name Rules
extends RefCounted
## Rule numbers for the playable loop. Each one says where it comes from:
##   DOCS        - from the design docs (design/), which are canon
##   PLACEHOLDER - the docs don't set it (or the loop needs it simpler); not a design decision
## Every PLACEHOLDER is also listed in godot/README.md.

# --- Deck and hand (design/05 Cards & progression.md) ------------------------

## DOCS: the deck is 5 cards of each class terrain plus 5 of the background's: a Fighter (the mockups' hero)
## has plains and desert, a Noble farmland.
## PLACEHOLDER: 5 of each of the other six terrains are added, so every terrain's tier 1 region variant can be
## reached in play (45 cards instead of the docs' 15). The banned pairs still apply.
const STARTING_DECK := {"plains": 5, "desert": 5, "farmland": 5,
	"forest": 5, "village": 5, "river": 5, "hills": 5, "swamp": 5, "ruins": 5}
const HAND_LIMIT := 7                    # DOCS: checked only at rest
const STARTING_HAND := 7                 # PLACEHOLDER: the docs don't say how many cards the campaign starts with
const DRAW_EASY_FIGHT := 3               # DOCS: an easy fight or tier 1 region draws 3
const DRAW_TIER2_REGION := 5             # DOCS: a tough fight, quest or tier 2 region draws 5

# --- Touch and pointer (design/07 Presentation.md -> Camera and controls) ------------

## PLACEHOLDER (the docs' mockup thresholds): a press that moves less than this and lets go within this time
## is a tap; moving further is a drag; holding still past the time is a long-press (details).
const TAP_PIXELS := 8.0                  # in the 844 x 390 layout's units, about 1 pt on an iPhone
const TAP_MS := 350
## PLACEHOLDER (Apple's guideline, from the touch brief; not in the docs): the smallest tap target. Controls
## drawn smaller keep their look and get a bigger hit area.
const FINGER := 44.0
## PLACEHOLDER (DOCS: a fixed step, size for playtesting): how far the nav button's rotate buttons (and Q / E)
## turn the view. Twisting and right-dragging rotate freely, with no snapping (DOCS).
const ROTATE_STEP := 60.0

# --- Map (design/02 Map & exploration.md) ------------------------------------

const START_TILE := Vector2i(0, 0)
## PLACEHOLDER: the Noble's starting hex is a Story card (a farm estate) with no art yet, so a farmland tile
## stands in. It also stands in for the party's camp (no camp kits yet). It doesn't count toward regions.
const START_TERRAIN := "farmland"
## DOCS: banned neighbours (design/02 Map & exploration.md -> Placement).
const BANNED := [["desert", "swamp"], ["desert", "forest"], ["swamp", "hills"], ["farmland", "desert"], ["farmland", "swamp"]]
const REGION_TIER1 := 5                  # DOCS: a terrain's first region needs 5+ hexes
const REGION_TIER2 := 7                  # DOCS: later regions of that terrain need 7+
const GOAL_SHOWS_AT := 2                 # PLACEHOLDER: "when a placed tile grows a cluster to a few hexes"
const SIGHT_RANGE := 2                   # DOCS: night building only within sight 2 of the party
const MAP_LIMIT := 28                    # PLACEHOLDER: the endless map is capped by the ground-colour lookup texture

# --- Day clock (design/02 -> Day and night; numbers as in Explore v8b) ------------

## The clock counts real minutes through a 30-minute day (DOCS: about 30 real minutes a day, night about 10).
const DAY_MINUTES := 30.0
const NIGHT_AT := 20.0                   # DOCS: night is the last 10 minutes
const DAWN_UNTIL := 5.0                  # PLACEHOLDER (Explore v8b): dawn, midday and dusk boundaries
const MIDDAY_UNTIL := 15.0
const START_MINUTE := 6.0                # PLACEHOLDER: the campaign starts early in the midday phase
const PLACE_MINUTES := 0.5               # PLACEHOLDER (Explore v8b): "placing a card costs a little real time"
const STEP_MINUTES := 1.0                # PLACEHOLDER (Explore v8b): walking one hex
const DAY_MAX_ZOOM := 110.0              # PLACEHOLDER: how far out the camera can zoom by day (m)
const NIGHT_MAX_ZOOM := 60.0             # PLACEHOLDER: and at night (DOCS: it can't zoom all the way out)
const ZOOM_LIMIT_SECONDS := 1.5          # PLACEHOLDER: the limit eases between them over this long
const SUN_STEP_HOURS := 0.1              # PLACEHOLDER: the sun moves in steps this many light-hours apart (a few s)
const SUN_BLEND_SECONDS := 0.6           # PLACEHOLDER: each step blends over this long
const LIGHT_EASE_SECONDS := 0.8          # PLACEHOLDER: the light eases after a clock jump (placing, walking, resting)

# --- How the party moves (DOCS: Exploration screen -> Walking -> How the party moves; every number a
# PLACEHOLDER, tuned by eye in the prototype) -----------------------------------------------------------
const WALK_SPEED := 4.5                  # m/s on open ground (a hex is 7.8 m across: about 1.7 s a hex)
const TERRAIN_SPEED := {"swamp": 0.55, "bog": 0.5, "forest": 0.7, "deep_forest": 0.6}   # x WALK_SPEED
const WALK_EASE_IN := 1.5                # m to reach full speed
const WALK_EASE_OUT := 2.2               # m to slow to a stop
const FOLLOW_DELAY := 0.32               # s each companion trails the one ahead on the leader's path
const STAND_SPREAD := 1.35              # the standing cluster, x the render's spots (they "spread out a little")
const WALK_SPREAD := 0.3                 # share of the standing formation's sideways spread kept while walking
const LOOK_AHEAD := 1.3                  # m ahead on the path a mini faces, so it turns before a corner
const TURN_RATE := 7.0                   # how fast a mini turns toward that (1/s)
const WADDLE_STRIDE := 1.1               # m per side-to-side rock (one rock left and right is two strides)
const WADDLE_DEG := 9.0                  # how far a mini rocks onto each side at full speed
const WADDLE_BOB := 0.012                # m it lifts as it rocks, on top of tipping up off its low edge
const SETTLE_DEG := 6.0                  # the wobble on stopping
const SETTLE_SECONDS := 0.9
const LOOK_AROUND_DEG := 35.0            # on arrival, each looks this far aside and back
const IDLE_LOOK_EVERY := Vector2(4.0, 9.0)   # s between one mini looking elsewhere while they stand
const IDLE_LOOK_DEG := 55.0
const GRASS_PART_RADIUS := 0.75          # m around a mini that the ground cover bends away
const WADE_DEPTH := 0.07                 # m a mini sinks in a ford
const FOOTPRINT_SECONDS := 14.0          # how long a footprint stays in the sand
# DOCS: the route goes round peaks, mountains and ridges, staying on the hills' grass.
const MOUNTAIN_CLEARANCE := 0.7          # m the route keeps from a peak, mountain or ridge (a base is 0.52 m to its corners)
const ROUTE_GRID := 0.25                 # m between the points the detour is searched on (not a look)
# DOCS: each mini's base tilts to lie flat on the slope, like a real mini on a sloped board, never cutting in.
const BASE_MARGIN := 0.04                # m past a base's rim that the ground is felt for (its tilt and height)
const MAX_TILT_DEG := 28.0               # the steepest a base tilts
const TILT_RATE := 12.0                  # how fast a base settles onto a new slope (1/s), so facet edges don't jitter
const HEIGHT_RATE := 14.0                # how fast a mini sinks to lower ground (1/s); it never trails below ground
const SQUEEZE_RATE := 2.5                # how fast a companion pushed in toward the route by a mountain spreads back out (1/s)
const REST_MINUTES := 10.0               # DOCS: resting fast-forwards 8 in-game hours (8/24 of a 30-minute day)

# --- Encounters (design/02 -> Hex contents and encounters) --------------------

const ENCOUNTER_CHANCE := 0.4            # PLACEHOLDER: chance a placement spawns one in its region
const ENCOUNTERS_PER_REGION := 1         # PLACEHOLDER: "each region can hold a set number of active encounters"
const ENCOUNTER_LIFETIME := 900.0        # DOCS: they disappear after about 15 minutes (half a day) if not dealt with

# --- Combat (design/03 Classes & combat.md) -----------------------------------

const AP := 3                            # DOCS
const HEADS_TO_HIT := 1                  # DOCS: at low levels the target is mostly 1
const MOVE_HEXES := 2                    # PLACEHOLDER: the combat mockups' 2-hex Move; the docs don't set it
const DEFEND_REDUCTION := 1              # PLACEHOLDER: defend/brace exists but has no number
## PLACEHOLDER (Explore v8b's text): Sneak past is a group check where everyone flips one coin and 1 heads passes.
const SNEAK_COINS_EACH := 1

## The party and their cards as in the combat mockup (Combat v14): [Hero name] the Fighter (longsword and
## shield), Fluffy (wizard, staff), Chelmsford (cleric, mace and shield) and Mel (rogue, dagger), with the
## mockup's scores (coins). PLACEHOLDER: HP; the docs set scores but not HP or damage.
const PARTY := [
	{"name": "[Hero name]", "initial": "H", "color": "#E9C46A", "mini": "standin_hero", "ability": "STR", "score": 3, "hp": 12,
		"weapon": "longsword", "hot": ["move", "attack", "parry", "shield_bash", "second_wind", "action_surge"],
		"cards": ["move", "attack", "defend", "use_item", "parry", "block", "shield_bash", "second_wind", "action_surge"]},
	{"name": "Fluffy", "initial": "F", "color": "#C9B3E6", "mini": "standin_fluffy", "ability": "INT", "score": 3, "hp": 8,
		"weapon": "staff", "hot": ["move", "attack", "firebolt", "frost_ray", "trip", "ward"],
		"cards": ["move", "attack", "defend", "use_item", "trip", "ward", "firebolt", "frost_ray"]},
	{"name": "Chelmsford", "initial": "C", "color": "#8EC3F2", "mini": "standin_chelmsford", "ability": "STR", "score": 2, "hp": 14,
		"weapon": "mace", "hot": ["move", "attack", "sacred_flame", "bless", "bonebreaker", "block"],
		"cards": ["move", "attack", "defend", "use_item", "bonebreaker", "block", "shield_bash", "sacred_flame", "bless", "healing_word"]},
	{"name": "Mel", "initial": "M", "color": "#F4B6A8", "mini": "standin_small", "ability": "DEX", "score": 3, "hp": 8,
		"weapon": "dagger", "hot": ["move", "attack", "backstab", "throw", "sneak_attack", "poison_blade"],
		"cards": ["move", "attack", "defend", "use_item", "backstab", "throw", "sneak_attack", "poison_blade"]},
]
const ENEMY := {"name": "[Enemy %s]", "mini": "standin_enemy", "ability": "STR", "score": 2, "hp": 6}
const ENEMY_SAVE_COINS := 2              # PLACEHOLDER (Combat v14): a foe's save flips 2 coins, 1 heads saves
const SPELL_DAMAGE := 2                  # PLACEHOLDER: Sacred Flame's full damage (halved on a save)
const HEAL := 4                          # PLACEHOLDER: Second Wind and Healing Word
const SNEAK_BONUS := 2                   # PLACEHOLDER: Sneak Attack's bonus when another ally flanks the foe
const POISON_BONUS := 1                  # PLACEHOLDER: Poison Blade's extra damage per hit this turn
const AP_CAP := 6                        # DOCS: no more than 6 AP in a turn
const ENEMIES_BASE := 2                  # PLACEHOLDER: foes per fight ...
const ENEMIES_PER_DISTANCE := 3          # ... plus one per this many hexes from the start (enemies scale with distance: DOCS)
const ENEMIES_MAX := 4
## PLACEHOLDER: how the board's cells follow the map tile's terrain.
const BOARD_TREES := {"forest": 12, "plains": 2, "farmland": 0, "village": 0, "river": 1,
	"hills": 1, "swamp": 4, "desert": 0, "ruins": 0}
const BOARD_ROCKS := {"forest": 2, "plains": 3, "farmland": 1, "village": 2, "river": 3,
	"hills": 6, "swamp": 1, "desert": 4, "ruins": 6}
## PLACEHOLDER: after a won fight, downed allies get back up at 1 HP; after a wipe the party wakes at camp at 1 HP
## (the docs' companion injuries aren't modelled).
const REVIVE_HP := 1

## The first (tier 1) region of each terrain and its landmark, as the exploration mockup names them
## (examples from the docs and mockup placeholders); later regions show the mockup's placeholders.
const REGION_NAMES := {
	"plains": ["Rolling meadows", "Nomad Camp"], "forest": ["Deep, old forest", "Hidden Shrine"],
	"farmland": ["Windmill country", "Great Windmill"], "village": ["Market town", "Trading House"],
	"river": ["River delta", "River Port"],
	"hills": ["Highlands", "Clan Hall"], "swamp": ["Bog/fen", "Witch's Hut"],
	"desert": ["Dunes/wasteland", "Sandstone Sphinx"], "ruins": ["Excavation", "Dig Site"],
}

const NAMES := {"forest": "Forest", "plains": "Plains", "farmland": "Farmland", "village": "Village", "river": "River/lake",
	"hills": "Hills", "swamp": "Swamp", "desert": "Desert", "ruins": "Ruins"}


static func banned(a: String, b: String) -> bool:
	for pair in BANNED:
		if (pair[0] == a and pair[1] == b) or (pair[0] == b and pair[1] == a):
			return true
	return false


static func hex_distance(a: Vector2i, b: Vector2i) -> int:
	var d := a - b
	return (absi(d.x) + absi(d.y) + absi(d.x + d.y)) / 2


static func is_night(minute: float) -> bool:
	return minute >= NIGHT_AT


static func phase_name(minute: float) -> String:
	if minute >= NIGHT_AT:
		return "Night"
	return "Dawn" if minute < DAWN_UNTIL else ("Midday" if minute < MIDDAY_UNTIL else "Dusk")


## The lighting hour (TimeOfDay) for a clock minute, so each phase gets its own light and backdrop.
static func light_hour(minute: float) -> float:
	if minute < DAWN_UNTIL:
		return remap(minute, 0, DAWN_UNTIL, 5.5, 8.0)
	if minute < MIDDAY_UNTIL:
		return remap(minute, DAWN_UNTIL, MIDDAY_UNTIL, 8.0, 16.5)
	if minute < NIGHT_AT:
		return remap(minute, MIDDAY_UNTIL, NIGHT_AT, 16.5, 19.5)
	return fmod(remap(minute, NIGHT_AT, DAY_MINUTES, 19.5, 29.5), 24.0)
