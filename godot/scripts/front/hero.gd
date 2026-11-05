class_name Hero
extends RefCounted
## The hero a new campaign starts with: a plain description the character creator fills and the game reads.
## Empty when the game starts directly (`--direct`, or any check or demo), which means the loop's placeholder hero.
##
## Fields: name; pronouns; cls (always "Fighter" for now); race, sub (the sub-type, or ""), race_name ("Shield dwarf");
## elf_spell; background, start_place ("Dunfaire Tower"), start_terrain ("ruins"), scores {STR..CHA: int};
## proficiencies [background's, class's]; gear {main, off, armour}; look {build, head, hair, skin, hair_colour, eyes,
## cloth}. DOCS (First playable): race, background and looks are looks and names for now.

static var current := {}


## "Race Class · Lv" (DOCS: Screen text -> Character subtitles).
static func subtitle(h: Dictionary, level := 1) -> String:
	return "%s %s · Lv %d" % [h.race_name, h.cls, level]


## A finished hero with the mockups' first picks, for checks and for starting past the creator.
static func stand_in() -> Dictionary:
	return {
		"name": "[Hero name]", "pronouns": "They", "cls": "Fighter",
		"race": "Human", "sub": "", "race_name": "Human", "elf_spell": "",
		"background": "Noble", "start_place": "Weizenhof Estate", "start_terrain": "farmland",
		"scores": {"STR": 3, "DEX": 1, "CON": 2, "INT": 1, "WIS": 1, "CHA": 1},
		"proficiencies": ["Persuade", "Athletics"],
		"gear": {"main": "longsword", "off": "shield", "armour": "Medium"},
		"look": {"build": "Average", "head": 0, "hair": 0, "skin": "#F3D2B5", "hair_colour": "#2B211C",
			"eyes": "#4F7A33", "cloth": "#B5532F"},
	}
