class_name Cards
extends RefCounted
## Combat action cards as the combat mockup lists them (Combat v14: names, sources, AP, icons, text), with
## what each one does in the loop. Card rules: design/03 Classes & combat.md -> Combat; Martial class cards;
## the spell sections. ap = -1 means the AP cost isn't set in the docs (the card shows "?" and can't be used,
## as in the mockup).
##   kind: "move", "attack" (flip to hit), "save" (the foe flips to save), "ally" (no roll), "self"
##   limit: "" (repeatable basic), "turn" (once per turn: the default), "fight" (once per fight)

const SRC := {
	"basic": {"band": "#BFAE8E", "ink": "#5A5040", "label": "Basic", "icon_ink": "#33403B"},
	"weapon": {"band": "#5F7F99", "ink": "#3E5A70", "label": "Weapon", "icon_ink": "#3E5A70"},
	"klass": {"band": "#B5532F", "ink": "#9A4A12", "label": "Class", "icon_ink": "#9A4A12"},
}

const ALL := {
	"move": {"n": "Move", "src": "basic", "ap": 1, "kind": "move", "limit": "", "icon": "move", "desc": "Move a set number of hexes."},
	"attack": {"n": "Attack", "src": "basic", "ap": 1, "kind": "attack", "limit": "", "range": 1, "desc": "Basic attack with your %s."},
	"defend": {"n": "Defend", "src": "basic", "ap": 1, "kind": "self", "limit": "turn", "icon": "defend", "effect": "defend", "desc": "Defend or brace."},
	"use_item": {"n": "Use item", "src": "basic", "ap": 1, "kind": "self", "limit": "turn", "icon": "potion", "effect": "item", "desc": "Use an equipped consumable."},
	"parry": {"n": "Parry", "src": "weapon", "ap": -1, "kind": "self", "limit": "turn", "icon": "parry", "desc": "Longsword: block the next melee hit."},
	"block": {"n": "Block", "src": "weapon", "ap": -1, "kind": "self", "limit": "turn", "icon": "shield", "desc": "Shield: reduce damage this turn."},
	"shield_bash": {"n": "Shield Bash", "src": "weapon", "ap": -1, "kind": "attack", "limit": "turn", "range": 1, "icon": "bash", "desc": "Shield: push or stun."},
	"second_wind": {"n": "Second Wind", "src": "klass", "ap": 1, "kind": "self", "limit": "fight", "icon": "heart", "effect": "heal", "desc": "Fighter: heal yourself."},
	"action_surge": {"n": "Action Surge", "src": "klass", "ap": 1, "kind": "self", "limit": "fight", "icon": "bolt", "effect": "surge", "desc": "Fighter: gain 3 bonus AP this turn (net +2)."},
	"trip": {"n": "Trip", "src": "weapon", "ap": -1, "kind": "attack", "limit": "turn", "range": 1, "icon": "trip", "desc": "Staff: knock an enemy prone."},
	"ward": {"n": "Ward", "src": "weapon", "ap": -1, "kind": "self", "limit": "turn", "icon": "ward", "desc": "Staff: a small magic shield."},
	"firebolt": {"n": "Firebolt", "src": "klass", "ap": 1, "kind": "attack", "limit": "turn", "range": 5, "icon": "fire", "desc": "Blaster spell: one heavy-hitting shot. Flip to hit."},
	"frost_ray": {"n": "Frost Ray", "src": "klass", "ap": 1, "kind": "attack", "limit": "turn", "range": 5, "icon": "snow", "desc": "Blaster spell: damage, and the foe is slowed on a hit."},
	"bonebreaker": {"n": "Bonebreaker", "src": "weapon", "ap": -1, "kind": "attack", "limit": "turn", "range": 1, "icon": "mace", "desc": "Mace: lower enemy movement."},
	"sacred_flame": {"n": "Sacred Flame", "src": "klass", "ap": 1, "kind": "save", "limit": "turn", "range": 5, "save": "DEX", "icon": "flame", "desc": "Order of Light: radiant damage. The target makes a DEX save."},
	"bless": {"n": "Bless", "src": "klass", "ap": 1, "kind": "ally", "limit": "turn", "range": 5, "icon": "star", "effect": "bless", "desc": "Order of Good: an ally flips an extra coin on its next check."},
	"healing_word": {"n": "Healing Word", "src": "klass", "ap": 1, "kind": "ally", "limit": "turn", "range": 5, "icon": "heart", "effect": "heal", "desc": "Order of Good: heal an ally at range."},
	"backstab": {"n": "Backstab", "src": "weapon", "ap": -1, "kind": "attack", "limit": "turn", "range": 1, "icon": "dagger", "desc": "Dagger: bonus damage from behind."},
	"throw": {"n": "Throw", "src": "weapon", "ap": -1, "kind": "attack", "limit": "turn", "range": 4, "icon": "throw", "desc": "Dagger: a ranged attack with the dagger. It returns to your hand."},
	"sneak_attack": {"n": "Sneak Attack", "src": "klass", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "icon": "eye", "effect": "sneak", "desc": "Rogue: a weapon attack with bonus damage if the foe is flanked or unaware."},
	"poison_blade": {"n": "Poison Blade", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "icon": "drop", "effect": "poison", "desc": "Rogue: every hit for the rest of this turn poisons."},
}

## The basic attack's icon follows the weapon (Combat v14).
const WEAPON_ICON := {"longsword": "sword", "staff": "staff", "mace": "mace", "dagger": "dagger"}


static func get_card(id: String, weapon := "") -> Dictionary:
	var c: Dictionary = ALL[id].duplicate()
	c.id = id
	if id == "attack":
		c.icon = WEAPON_ICON.get(weapon, "sword")
		c.desc = c.desc % weapon
	return c


static func ap_text(c: Dictionary) -> String:
	return "?" if c.ap < 0 else str(c.ap)
