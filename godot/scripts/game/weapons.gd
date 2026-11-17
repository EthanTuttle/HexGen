class_name Weapons
extends RefCounted
## Weapon categories in play (DOCS: design/04 -> Weapon rules, Weapon category cards; numbers are Ethan's placeholders of
## Nov 5, 2026). Ids are the gear reference's (Gear.WEAPONS). Each category gives:
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
	"wand": {"ab": "INT", "hands": "1", "range": 5, "ranged": true, "cards": []},   # Magic Bolt, the basic attack (04; range PLACEHOLDER)
	"shortbow": {"ab": "DEX", "hands": "2", "range": 6, "ranged": true, "cards": ["double_shot"]},
	"longbow": {"ab": "DEX", "hands": "2", "range": 8, "ranged": true, "cards": ["aimed_shot"]},
	"crossbow": {"ab": "DEX", "hands": "2", "range": 6, "ranged": true, "point_blank": true, "cards": ["pinning_bolt"]},
	"gauntlets": {"ab": "STR", "hands": "f", "range": 1, "cards": ["guard_up"]},
	"knuckles": {"ab": "STR", "hands": "f", "range": 1, "cards": ["haymaker"]},
	"wraps": {"ab": "DEX", "hands": "f", "range": 1, "cards": ["step_strike"]},
	# A summon's own attack (03 -> Wizard level-1 placeholders): not gear, so the creator never offers them.
	"summon_blade": {"ab": "INT", "hands": "1", "range": 1, "cards": []},
	"summon_wisp": {"ab": "INT", "hands": "1", "range": 4, "ranged": true, "cards": []},
}
## The Wizard's level-1 spells by school, in the Spells step's columns (03 -> Wizard spells).
const WIZARD_SPELLS := {"Summoner": ["animated_blade", "wisp"], "Blaster": ["firebolt", "frost_ray", "shocking_grasp"],
	"Deceiver": ["mirror_image", "phantom_ally"], "Ritualist": ["blood_bolt", "warding_circle"]}
## The Cleric's level-1 spells by order and the Bard's by school (03 -> Cleric spells, Bard spells), and every caster's.
const CLERIC_SPELLS := {"Order of Light": ["sacred_flame", "searing_touch"], "Order of Night": ["shadow_bolt", "dread"],
	"Order of Good": ["bless", "shield_of_faith"], "Order of Evil": ["bane", "hex"]}
const BARD_SPELLS := {"Narrator": ["mockery", "heroic_tale"], "Musician": ["rousing_tune", "soothing_melody"],
	"Dancer": ["dazzle", "blade_twirl"], "Leader": ["rallying_strike", "war_cry"]}
const SPELLS_1 := {"wizard": WIZARD_SPELLS, "cleric": CLERIC_SPELLS, "bard": BARD_SPELLS}
const SPELL_PICKS := 2                   # DOCS (03): casters pick 2 spells at level 1
const CLOTHES_HEADS := 1                # DOCS (04 -> Armour, flat since Nov 7, 2026): Clothes 1, Armoured 2, +1 with a shield
const ARMOURED_HEADS := 2
const SHIELD_HEADS := 1
const THROW_RANGE := 4                   # PLACEHOLDER (04): thrown daggers and spears
const VERSATILE_TWO_HANDED := 2          # PLACEHOLDER (04): +2 damage held two-handed, with the off hand empty
const CLASS_CARDS := {"fighter": ["second_wind"], "ranger": ["hunters_mark"], "rogue": ["sneak_attack"]}   # DOCS (06 -> Start, Nov 9, 2026: the level-3 cards come at level 3, Progression)
const CLASS_HP := {"fighter": 12, "ranger": 10, "rogue": 8, "wizard": 6, "cleric": 10, "bard": 8}   # PLACEHOLDER (06 -> Start; Cleric and Bard Nov 12, 2026)


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


## Armoured or in Clothes (04 -> Armour, reworked Nov 5, 2026): the gear reference decides (Gear).
static func armoured(armour: String) -> bool:
	return Gear.armoured(armour)


## The heads a foe needs to hit this hero or companion, flat so players never work out halves (04 -> Armour, Ethan,
## Nov 7, 2026): Clothes 1, Armoured 2, +1 with a shield.
static func defence_heads(m: Dictionary, clothes := false) -> int:
	var base := ARMOURED_HEADS if armoured(m.get("armour", "")) and not clothes else CLOTHES_HEADS
	return base + (SHIELD_HEADS if m.get("off", "") == "shield" else 0)
