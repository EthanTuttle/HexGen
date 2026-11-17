class_name Hero
extends RefCounted
## Who the player made in the creator. Game reads Hero.current when it starts; null means a direct start, with the placeholder hero. The Screens session owns this file's growth;
## Game only needs name, klass, race, background and appearance. DOCS (First playable): race, background and looks are looks and names for now.

static var current: Hero
static var live := {}           # the run hero's scores now, with level-up points (Game's party[0].scores); checks read these

var id := ""                    # the saves' folder (Saves): given at the first save, so two heroes of one name stay apart
var name := "[Hero name]"
var klass := "fighter"
var race := ""                  # "Dwarf"
var background := "soldier"     # RunSetup.BACKGROUNDS' keys
var appearance := {}            # build, head, hair, skin, hair_colour, eyes, cloth; race, sub for the mini

var sub := ""                   # the sub-type, or "": "Shield dwarf"
var race_name := ""             # how the subtitle says it: "Shield dwarf"
var elf_spell := ""
var spells: Array = []          # a caster's level-1 picks, as card ids
var god := ""                   # a Cleric's god: "Aurora"
var pronouns := ""
var scores := {}                # STR .. CHA
var proficiencies: Array = []   # the background's pick, the class's pick
var gear := {}                  # main, off, armour


## "Race Class (Subclass) · Lv" (DOCS: Screen text -> Character subtitles). The subclass comes at level 5; before it, "Race Class · Lv".
func subtitle(level := 1, subclass := "") -> String:
	return Hero.subtitle_of(race_name, klass.capitalize(), subclass, level)


static func subtitle_of(race_text: String, klass_text: String, subclass: String, level: int) -> String:
	return "%s %s%s · Lv %d" % [race_text, klass_text, " (%s)" % subclass if subclass != "" else "", level]


## This check's coins with the hero's score, and +1 if proficient (design/03 -> Checks outside combat). With no creator
## behind the run, the mockup's placeholder scores.
static func coins_for(ability: String, proficiency: String) -> int:
	if current == null:
		return {"STR": 2, "INT": 1, "CHA": 2}.get(ability, 1)
	var armoured := 1 if proficiency == "Stealth" and Weapons.armoured(current.gear.get("armour", "")) else 0   # 04 -> Armour
	return maxi(1, int((live if not live.is_empty() else current.scores).get(ability, 1)) + (1 if proficiency in current.proficiencies else 0) - armoured)
