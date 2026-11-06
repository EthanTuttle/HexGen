class_name Hero
extends RefCounted
## Who the player made in the creator. Game reads Hero.current when it starts; null means a direct start, with the placeholder hero. The Screens session owns this file's growth;
## Game only needs name, klass, race, background and appearance. DOCS (First playable): race, background and looks are looks and names for now.

static var current: Hero

var name := "[Hero name]"
var klass := "fighter"
var race := ""                  # "Dwarf"
var background := "soldier"     # RunSetup.BACKGROUNDS' keys
var appearance := {}            # build, head, hair, skin, hair_colour, eyes, cloth; race, sub for the mini

var sub := ""                   # the sub-type, or "": "Shield dwarf"
var race_name := ""             # how the subtitle says it: "Shield dwarf"
var elf_spell := ""
var pronouns := ""
var scores := {}                # STR .. CHA
var proficiencies: Array = []   # the background's pick, the class's pick
var gear := {}                  # main, off, armour


## "Race Class · Lv" (DOCS: Screen text -> Character subtitles).
func subtitle(level := 1) -> String:
	return "%s %s · Lv %d" % [race_name, klass.capitalize(), level]


## This check's coins with the hero's score, and +1 if proficient (design/03 -> Checks outside combat). With no creator
## behind the run, the mockup's placeholder scores.
static func coins_for(ability: String, proficiency: String) -> int:
	if current == null:
		return {"STR": 2, "INT": 1, "CHA": 2}.get(ability, 1)
	var armoured := 1 if proficiency == "Stealth" and Weapons.armoured(current.gear.get("armour", "")) else 0   # 04 -> Armour
	return maxi(1, int(current.scores.get(ability, 1)) + (1 if proficiency in current.proficiencies else 0) - armoured)
