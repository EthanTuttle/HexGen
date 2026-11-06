class_name Ambush
extends RefCounted
## Ambush and unaware (design/03 -> Combat -> Ambush, Unaware; Ethan, Nov 6, 2026). Before a fight the hero flips alone,
## Stealth (DEX) or Deceive (CHA), needing the heads of the group's highest role (as Sneak past: Foes.sneak_heads). On a
## pass every foe starts unaware of the whole party; on a fail the foes go first. Foes that started unaware act on their
## first turn with 1 AP less. Unaware ends per character: any hostile action a character aims at a foe (not Hunter's
## Mark) ends its unawareness of that character only. Hidden characters are unaware-of too, once hiding exists.

const LOST_AP := 1


## At the fight's start, after an ambush: on a pass every foe is unaware of every ally. Returns whether the foes go first.
static func apply(units: Array, passed: bool) -> bool:
	var names := units.filter(func(u): return u.ally).map(func(u): return String(u.member.name))
	for u: Dictionary in units:
		if not u.ally:
			u.unaware = names.duplicate() if passed else []
			u.ambushed = passed
	return not passed


## Whether `foe` is unaware of `who` (for Sneak Attack, Assassinate, Fake Surrender, and the status icon).
static func is_unaware(foe: Dictionary, who: Dictionary) -> bool:
	if foe.is_empty() or who.is_empty() or foe.ally or not who.ally:
		return false
	return who.get("hidden", false) or String(who.member.name) in foe.get("unaware", [])


## `who` aimed a hostile action at `foe`: it notices them (and only them).
static func noticed(foe: Dictionary, who: Dictionary) -> void:
	if foe.is_empty() or who.is_empty() or foe.ally or not who.ally:
		return
	foe.get("unaware", []).erase(String(who.member.name))


## The AP a foe loses at the start of its turn for having been ambushed: on its first turn only.
static func first_turn_ap(foe: Dictionary) -> int:
	if not foe.get("ambushed", false):
		return 0
	foe.ambushed = false
	return LOST_AP
