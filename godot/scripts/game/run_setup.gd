class_name RunSetup
extends RefCounted
## What a campaign starts from (design/06 -> First playable). The title and character creator fill one in and set RunSetup.next, then load the game scene; start_run reads it.
## The checks and the demo use test(): four in the party, the wide deck, one seed, no rolls and no goal, so their numbers hold still.

## The run the game scene starts next. Null: Game works it out from the launch (for_launch).
static var next: RunSetup

## A background's terrain (design/05 -> Starting decks) and its starting place (design/01 -> Backgrounds).
const BACKGROUNDS := {
	"soldier": {"terrain": "ruins", "place": "Dunfaire Tower"},
	"acolyte": {"terrain": "hills", "place": "East Rime Chapel"},
	"criminal": {"terrain": "river", "place": "Monto Town"},
	"sage": {"terrain": "desert", "place": "Sternbrunn Spire"},
	"folk_hero": {"terrain": "forest", "place": "The Oak & Lantern"},
	"noble": {"terrain": "farmland", "place": "Weizenhof Estate"},
}
const CLASS_TERRAINS := {"fighter": ["plains", "desert"]}
const CARDS_EACH := 5
const ONE_OF_EACH := ["forest", "plains", "farmland", "village", "river", "hills", "swamp", "desert", "ruins"]   # design/06: so all can be built

var hero_name := "[Hero name]"
var klass := "fighter"
var race := ""                 # a look and a name for now (design/06)
var background := "soldier"
var appearance := {}           # for the mini, from the creator
var seed_text := ""            # "" rolls one
var party_size := 2            # the hero and Fluffy (design/06). Recruiting comes later
var goal_regions := 3          # finish this many, then the end panel; 0: no goal
var spawn_rolls := true        # encounters on the clock (design/02); off: a placement may spawn one, as the checks expect
var safety_net := true
var wide_deck := false


static func for_launch() -> RunSetup:
	if Hero.current != null:
		return from_hero(Hero.current)
	if next != null:
		var run := next
		next = null
		return run
	var args := OS.get_cmdline_user_args()
	var run: RunSetup
	if Array(args).any(func(a): return (a.ends_with("check") and a != "--playcheck") or a in ["--demo", "--touchtest", "--forest", "--phonecheck", "--forestperf", "--phonelist"] or a.begins_with("--combatmap")) or PhoneCheck.wanted():
		run = test()
	else:
		run = RunSetup.new()
	for a: String in args:
		if a.begins_with("--seed="):
			run.seed_text = a.split("=")[1]
	return run


static func from_hero(hero: Hero) -> RunSetup:
	var run := RunSetup.new()
	run.hero_name = hero.name
	run.klass = hero.klass
	run.race = hero.race
	run.background = hero.background
	run.appearance = hero.appearance
	return run


static func test() -> RunSetup:
	var run := RunSetup.new()
	run.seed_text = "1"
	run.party_size = 4
	run.goal_regions = 0
	run.spawn_rolls = false
	run.safety_net = false
	run.wide_deck = true
	return run


## The starting map deck: class terrains and the background's, 5 each, stacking if they overlap (design/05 -> Starting decks).
func deck_cards() -> Dictionary:
	if wide_deck:
		return Rules.STARTING_DECK
	var cards := {}
	var terrains: Array = CLASS_TERRAINS[klass] + [BACKGROUNDS[background].terrain]
	for t: String in terrains:
		cards[t] = cards.get(t, 0) + CARDS_EACH
	for t: String in ONE_OF_EACH:
		cards[t] = cards.get(t, 0) + 1
	return cards
