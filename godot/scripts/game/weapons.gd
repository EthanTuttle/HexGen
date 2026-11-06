class_name Weapons
extends RefCounted
## Weapon categories in play (DOCS: design/04 -> Weapon rules, Weapon category cards; numbers are Ethan's placeholders of
## Nov 5, 2026). Ids are the creator's (CreatorData.W). Each category gives:
##   ab: the score its attacks flip (04: STR for heavy weapons, DEX for finesse and ranged, INT or WIS for staves and wands)
##   hands: "1" one-handed, "v" versatile, "2" two-handed, "f" fist weapons (a pair)
##   range: the basic attack's reach in hexes (melee 1; Reach 2; bows); ranged: a ranged attack (the adjacent penalty)
##   cards: its category cards (Cards.ALL ids). Fighter-only categories whose cards aren't built yet give the basic attack only.
## PLACEHOLDER (04 doesn't sort them): longswords, spears, glaives and staves count as heavy (STR) or casting (INT) as listed.

const CAT := {
	"greatsword": {"ab": "STR", "hands": "2", "range": 1, "cards": []},
	"longsword": {"ab": "STR", "hands": "v", "range": 1, "cards": ["parry"]},
	"shortsword": {"ab": "DEX", "hands": "1", "range": 1, "cards": ["quick_slash"]},
	"rapier": {"ab": "DEX", "hands": "1", "range": 1, "cards": ["disarm"]},
	"scimitar": {"ab": "DEX", "hands": "1", "range": 1, "cards": ["dancing_step"]},
	"dagger": {"ab": "DEX", "hands": "1", "range": 1, "cards": ["throw"]},
	"battleaxe": {"ab": "STR", "hands": "v", "range": 1, "cards": ["throw"]},
	"greataxe": {"ab": "STR", "hands": "2", "range": 1, "cards": []},
	"mace": {"ab": "STR", "hands": "1", "range": 1, "cards": ["bonebreaker"]},
	"warhammer": {"ab": "STR", "hands": "2", "range": 1, "cards": []},
	"spear": {"ab": "STR", "hands": "v", "range": 2, "cards": ["throw"]},
	"halberd": {"ab": "STR", "hands": "2", "range": 2, "cards": []},
	"glaive": {"ab": "STR", "hands": "2", "range": 2, "cards": ["sweeping_arc"]},
	"staff": {"ab": "INT", "hands": "v", "range": 1, "cards": ["trip", "ward"]},
	"wand": {"ab": "INT", "hands": "1", "range": 1, "cards": []},
	"shortbow": {"ab": "DEX", "hands": "2", "range": 6, "ranged": true, "cards": ["double_shot"]},
	"longbow": {"ab": "DEX", "hands": "2", "range": 8, "ranged": true, "cards": ["aimed_shot"]},
	"crossbow": {"ab": "DEX", "hands": "2", "range": 6, "ranged": true, "point_blank": true, "cards": ["pinning_bolt"]},
	"gauntlets": {"ab": "STR", "hands": "f", "range": 1, "cards": ["guard_up"]},
	"knuckles": {"ab": "STR", "hands": "f", "range": 1, "cards": ["haymaker"]},
	"wraps": {"ab": "DEX", "hands": "f", "range": 1, "cards": ["step_strike"]},
}
const ARMOURED_HEADS := 1               # DOCS (04 -> Armour, Nov 5, 2026): Armoured needs 1 + half CON rounded up
const SHIELD_HEADS := 1                 # DOCS: +1 with a shield
const THROW_RANGE := 4                   # PLACEHOLDER (04): thrown daggers and spears
const VERSATILE_TWO_HANDED := 2          # PLACEHOLDER (04): +2 damage held two-handed, with the off hand empty
const CLASS_CARDS := {"fighter": ["second_wind", "action_surge"], "ranger": ["hunters_mark", "snare"], "rogue": ["sneak_attack", "poison_blade"]}   # DOCS (06 -> Start)
const CLASS_HP := {"fighter": 12, "ranger": 10, "rogue": 8}   # PLACEHOLDER (06 -> Start)


static func of(id: String) -> Dictionary:
	return CAT.get(id, CAT.longsword)


static func ranged(id: String) -> bool:
	return of(id).get("ranged", false)


## A member's cards from its class and gear (04): the basics, the class's cards, each weapon's category cards, and with a
## shield Block in Defend's place and Shield Bash.
static func cards_for(klass: String, main: String, off: String) -> Array:
	var out := ["move", "attack", "block" if off == "shield" else "defend", "use_item"]
	out.append_array(CLASS_CARDS.get(klass, []))
	for w in [main, off]:
		if CAT.has(w):
			for id in CAT[w].cards:
				if not id in out:
					out.append(id)
	if off == "shield":
		out.append("shield_bash")
	return out


## Armoured or in Clothes (04 -> Armour, reworked Nov 5, 2026): any armour the creator offers counts as Armoured.
static func armoured(armour: String) -> bool:
	return armour in ["Light", "Medium", "Heavy", "Armoured"]


## The heads a foe needs to hit this hero or companion (04): Armoured 1 + half CON rounded up, +1 with a shield; in Clothes
## half DEX rounded up.
static func defence_heads(m: Dictionary, clothes := false) -> int:
	if armoured(m.get("armour", "")) and not clothes:
		return ARMOURED_HEADS + ceili(Races.score(m, "CON") / 2.0) + (SHIELD_HEADS if m.get("off", "") == "shield" else 0)
	return maxi(ceili(Races.score(m, "DEX") / 2.0), 1)
