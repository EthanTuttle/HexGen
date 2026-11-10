class_name Gear
extends RefCounted
## The one gear reference every screen reads (Ethan's phone note of Nov 8, 2026): the creator's Gear step, the gear screen
## once it's built, and combat. What each item is (name, icon, hands), the armour choices and which class may use what live
## here; a weapon's fight numbers (score, range, cards) stay in Weapons.CAT, keyed by the same ids.
## DOCS: 04 -> Weapon and armor categories (class gear), Armour (flat since Nov 5-7, 2026: Clothes or Armoured, plus a
## shield), Starting gear (Humans ignore class limits).
## Class armour from 04's table (Ethan, Nov 9, 2026): Fighters and Clerics Armoured with shields, Rangers Armoured, Bards
## in Clothes until the Leader subclass, Rogues and Wizards in Clothes; a Human may be Armoured.

## hands: "1" one-handed, "v" versatile, "2" two-handed, "f" a fist-weapon pair. i: the icon (CreatorData.IC key).
const WEAPONS := [
	{"id": "greatsword", "n": "Greatsword", "hands": "2", "i": "w_greatsword"},
	{"id": "longsword", "n": "Longsword", "hands": "v", "i": "w_longsword"},
	{"id": "shortsword", "n": "Shortsword", "hands": "1", "i": "w_shortsword"},
	{"id": "rapier", "n": "Rapier", "hands": "1", "i": "w_rapier"},
	{"id": "scimitar", "n": "Scimitar", "hands": "1", "i": "w_scimitar"},
	{"id": "dagger", "n": "Dagger", "hands": "1", "i": "w_dagger"},
	{"id": "battleaxe", "n": "Battleaxe", "hands": "v", "i": "w_battleaxe"},
	{"id": "greataxe", "n": "Greataxe", "hands": "2", "i": "w_greataxe"},
	{"id": "mace", "n": "Mace", "hands": "1", "i": "w_mace"},
	{"id": "warhammer", "n": "Warhammer", "hands": "2", "i": "w_warhammer"},
	{"id": "spear", "n": "Spear", "hands": "v", "i": "w_spear"},
	{"id": "halberd", "n": "Halberd", "hands": "2", "i": "w_halberd"},
	{"id": "glaive", "n": "Glaive", "hands": "2", "i": "w_glaive"},
	{"id": "staff", "n": "Staff", "hands": "v", "i": "w_staff"},
	{"id": "wand", "n": "Wand", "hands": "1", "i": "w_wand"},
	{"id": "shortbow", "n": "Shortbow", "hands": "2", "i": "w_shortbow"},
	{"id": "longbow", "n": "Longbow", "hands": "2", "i": "w_longbow"},
	{"id": "crossbow", "n": "Crossbow", "hands": "2", "i": "w_crossbow"},
	{"id": "gauntlets", "n": "Gauntlets", "hands": "f", "i": "w_gauntlets"},
	{"id": "knuckles", "n": "Brass knuckles", "hands": "f", "i": "w_knuckles"},
	{"id": "wraps", "n": "Wraps", "hands": "f", "i": "w_wraps"},
]
const SHIELD := {"id": "shield", "n": "Shield", "i": "shield"}
const EMPTY_HAND := {"id": "none", "n": "Empty hand", "i": "none"}
## The armour slot (04 -> Armour): Clothes (an empty slot reads Clothes) or Armoured. Ids are what a run and a save keep.
const CLOTHES := {"id": "none", "n": "Clothes", "i": "none"}
const ARMOURED := {"id": "armoured", "n": "Armoured", "i": "armour"}
## Older runs, saves and test args name the old tiers; each counts as Armoured.
const OLD_ARMOUR := ["light", "medium", "heavy"]

## 04 -> Class gear. weapons: ids or "all"; armoured: may wear armour; shield: may hold a shield.
const CLASS_GEAR := {
	"fighter": {"weapons": "all", "armoured": true, "shield": true},
	"rogue": {"weapons": ["shortsword", "rapier", "scimitar", "dagger", "shortbow", "crossbow", "gauntlets", "knuckles", "wraps"],
			"armoured": false, "shield": false},
	"wizard": {"weapons": ["dagger", "staff", "wand"], "armoured": false, "shield": false},
	"cleric": {"weapons": ["mace", "warhammer", "staff"], "armoured": true, "shield": true},
	"ranger": {"weapons": ["longsword", "shortsword", "scimitar", "dagger", "spear", "glaive", "shortbow", "longbow", "crossbow",
			"gauntlets", "knuckles", "wraps"], "armoured": true, "shield": false},
	"bard": {"weapons": ["longsword", "shortsword", "rapier", "dagger", "shortbow", "crossbow"], "armoured": false, "shield": false},
}
## What a subclass adds to its class's gear: Leader bards gain Armoured and polearms (03 -> Bard subclasses, 04 -> Class gear).
const SUBCLASS_GEAR := {
	"leader": {"weapons": ["spear", "halberd", "glaive"], "armoured": true},
}


## A weapon's entry, or {} (the shield and an empty hand too, by id).
static func item(id: String) -> Dictionary:
	if id == SHIELD.id:
		return SHIELD
	for w: Dictionary in WEAPONS:
		if w.id == id:
			return w
	return {}


static func _class(klass: String) -> Dictionary:
	return CLASS_GEAR.get(klass.to_lower(), {})


static func _sub(subclass: String) -> Dictionary:
	return SUBCLASS_GEAR.get(subclass.to_lower(), {})


## The weapons a hero of this class (and subclass, once picked) may pick; a Human may pick any (Versatile, 03 -> Races).
static func weapons_for(klass: String, human := false, subclass := "") -> Array:
	var g := _class(klass)
	if g.is_empty():
		return []
	if human or str(g.weapons) == "all":
		return WEAPONS.duplicate()
	var ids: Array = g.weapons + _sub(subclass).get("weapons", [])
	return WEAPONS.filter(func(w): return w.id in ids)


static func shield_for(klass: String, human := false) -> bool:
	return human or _class(klass).get("shield", false)


## The armour slot's choices: Clothes, and Armoured where the class, its subclass or a Human may wear armour.
static func armour_for(klass: String, human := false, subclass := "") -> Array:
	var may: bool = human or _class(klass).get("armoured", false) or _sub(subclass).get("armoured", false)
	return [CLOTHES, ARMOURED] if may else [CLOTHES]


## What the offhand can hold beside a main weapon: nothing beside a two-handed weapon or a fist pair; else an empty hand,
## a shield where allowed, and a one-handed weapon beside a one-handed one.
static func off_for(klass: String, human: bool, main: String, subclass := "") -> Array:
	var hands: String = item(main).get("hands", "")
	if hands != "1" and hands != "v":
		return []
	var out := [EMPTY_HAND]
	if shield_for(klass, human):
		out.append(SHIELD)
	if hands == "1":
		out.append_array(weapons_for(klass, human, subclass).filter(func(w): return w.hands == "1"))
	return out


## Armoured or in Clothes (04 -> Armour): "armoured", or an old tier from an older run or save.
static func armoured(armour: String) -> bool:
	return armour.to_lower() == ARMOURED.id or armour.to_lower() in OLD_ARMOUR


## The armour slot's name for a run's value ("Clothes" or "Armoured").
static func armour_name(armour: String) -> String:
	return ARMOURED.n if armoured(armour) else CLOTHES.n
