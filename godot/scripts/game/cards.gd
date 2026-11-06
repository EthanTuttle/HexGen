class_name Cards
extends RefCounted
## Combat action cards as the combat mockup lists them (Combat v14: names, sources, AP, icons, text), with
## what each one does in the loop. Card rules: design/03 Classes & combat.md -> Combat; Martial class cards;
## the spell sections. ap = -1 means the AP cost isn't set in the docs (the card shows "?" and can't be used,
## as in the mockup).
##   kind: "move", "attack" (flip to hit), "save" (the foe flips to save), "ally" (no roll), "self", "breath" (a line,
##         aimed by a lit hex), "cell" (an empty hex: Glimmerstep)
##   limit: "" (repeatable basic), "turn" (once per turn: the default), "fight" (once per fight)
##   ab: the score an attack flips (default: the character's weapon ability); dmg: a set damage instead of the score
## Racial cards and racial spells (design/03 -> Races, Racial spells): text from the creator's (CreatorData), as the docs
## give it; amounts in Rules (design/06 -> First playable -> Races).

const SRC := {
	"basic": {"band": "#BFAE8E", "ink": "#5A5040", "label": "Basic", "icon_ink": "#33403B"},
	"weapon": {"band": "#5F7F99", "ink": "#3E5A70", "label": "Weapon", "icon_ink": "#3E5A70"},
	"klass": {"band": "#B5532F", "ink": "#9A4A12", "label": "Class", "icon_ink": "#9A4A12"},
	# PLACEHOLDER colours: the creator's racial card and elven spell bands, with class ink.
	"race": {"band": "#B5532F", "ink": "#9A4A12", "label": "Racial card", "icon_ink": "#9A4A12"},
	"elven": {"band": "#3E6F8C", "ink": "#2F5670", "label": "Elven spell", "icon_ink": "#2F5670"},
	"bloodline": {"band": "#3E6F8C", "ink": "#2F5670", "label": "Bloodline spell", "icon_ink": "#2F5670"},
}

const ALL := {
	"move": {"n": "Move", "src": "basic", "ap": 1, "kind": "move", "limit": "", "icon": "move", "desc": "Move a set number of hexes."},
	"attack": {"n": "Attack", "src": "basic", "ap": 1, "kind": "attack", "limit": "", "range": 1, "desc": "Basic attack with your %s."},
	"defend": {"n": "Defend", "src": "basic", "ap": 1, "kind": "self", "limit": "turn", "icon": "defend", "effect": "defend", "desc": "Defend or brace."},
	"use_item": {"n": "Use item", "src": "basic", "ap": 1, "kind": "self", "limit": "turn", "icon": "potion", "effect": "item", "desc": "Use an equipped consumable."},
	"parry": {"n": "Parry", "src": "weapon", "ap": 1, "kind": "self", "limit": "turn", "icon": "parry", "effect": "parry", "desc": "Longsword: block the next melee hit."},
	"block": {"n": "Block", "src": "weapon", "ap": 1, "kind": "self", "limit": "turn", "icon": "shield", "effect": "defend", "desc": "Shield: reduce damage this turn."},
	"shield_bash": {"n": "Shield Bash", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "icon": "bash", "rider": "push", "desc": "Shield: push the foe 1 hex away."},
	"second_wind": {"n": "Second Wind", "src": "klass", "ap": 1, "kind": "self", "limit": "fight", "icon": "heart", "effect": "heal", "desc": "Fighter: heal yourself."},
	"action_surge": {"n": "Action Surge", "src": "klass", "ap": 1, "kind": "self", "limit": "fight", "icon": "bolt", "effect": "surge", "desc": "Fighter: gain 3 bonus AP this turn (net +2)."},
	"trip": {"n": "Trip", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "icon": "trip", "rider": "prone", "desc": "Staff: knock an enemy prone."},
	"ward": {"n": "Ward", "src": "weapon", "ap": 1, "kind": "self", "limit": "turn", "icon": "ward", "effect": "ward", "desc": "Staff: a small magic shield."},
	"firebolt": {"n": "Firebolt", "src": "klass", "ap": 1, "kind": "attack", "limit": "turn", "range": 5, "ranged": true, "icon": "fire", "bonus": 1, "desc": "Blaster spell: one heavy-hitting shot. Flip to hit."},
	"frost_ray": {"n": "Frost Ray", "src": "klass", "ap": 1, "kind": "attack", "limit": "turn", "range": 5, "ranged": true, "icon": "snow", "rider": "slow", "slow": Rules.FROST_SLOW, "desc": "Blaster spell: damage, and the foe is slowed on a hit."},
	"bonebreaker": {"n": "Bonebreaker", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "icon": "mace", "rider": "slow", "slow": Rules.BONEBREAKER_SLOW, "desc": "Mace: lower enemy movement."},
	"sacred_flame": {"n": "Sacred Flame", "src": "klass", "ap": 1, "kind": "save", "limit": "turn", "range": 5, "save": "DEX", "icon": "flame", "desc": "Order of Light: radiant damage. The target makes a DEX save."},
	"bless": {"n": "Bless", "src": "klass", "ap": 1, "kind": "ally", "limit": "turn", "range": 5, "icon": "star", "effect": "bless", "desc": "Order of Good: an ally flips an extra coin on its next check."},
	"healing_word": {"n": "Healing Word", "src": "klass", "ap": 1, "kind": "ally", "limit": "turn", "range": 5, "icon": "heart", "effect": "heal", "desc": "Order of Good: heal an ally at range."},
	"throw": {"n": "Throw", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": Weapons.THROW_RANGE, "ranged": true, "icon": "throw", "desc": "Dagger: a ranged attack with the dagger. It returns to your hand."},
	"sneak_attack": {"n": "Sneak Attack", "src": "klass", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "icon": "eye", "effect": "sneak", "desc": "Rogue: a weapon attack with bonus damage if the foe is flanked or unaware."},
	"duck_behind": {"n": "Duck Behind", "src": "race", "ap": 1, "kind": "ally", "limit": "turn", "range": 1, "icon": "M7 7h11l-3-3 M17 17H6l3 3", "effect": "swap", "desc": "Swap places with an adjacent ally."},
	"breath": {"n": "Breath Weapon", "src": "race", "ap": 2, "kind": "breath", "limit": "turn", "save": "DEX", "icon": "M12 3c1 4 5 6 5 11a5 5 0 0 1-10 0c0-3 2-4 2-7 1 2 2 3 3 3 0-3-1-5 0-7z", "desc": "A line of 3 hexes in one of the 6 directions. Everyone in it, allies included, makes a DEX save (half damage on a pass). Damage grows with level."},
	"lockdown": {"n": "Lockdown", "src": "race", "ap": 1, "kind": "self", "limit": "turn", "icon": "M7 11V8a5 5 0 0 1 10 0v3 M5 11h14v9H5z", "effect": "lockdown", "desc": "Your damage reduction doubles until your next turn, but you can’t move."},
	"stone_throw": {"n": "Stone Throw", "src": "race", "ap": 1, "kind": "attack", "limit": "turn", "range": Rules.RACIAL_RANGE, "ranged": true, "ab": "STR", "dmg": Rules.RACIAL_DAMAGE, "icon": "M5 16l3-7 6-2 5 5-2 6-8 1z", "desc": "A ranged STR attack, usable whatever weapon you hold."},
	"claw_swipe": {"n": "Claw Swipe", "src": "race", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "ab": "DEX", "dmg": Rules.CLAW_DAMAGE, "rider": "bleed", "icon": "M6 5l3 14 M11 4l2 15 M17 5l-2 14", "desc": "A melee scratch that makes the foe bleed. DEX attack."},
	"glimmerstep": {"n": "Glimmerstep", "src": "elven", "ap": 1, "kind": "cell", "limit": "turn", "range": Rules.GLIMMERSTEP_RANGE, "icon": "glim", "effect": "blink", "desc": "Vanish and reappear in an empty hex up to 3 hexes away."},
	"faerie_fire": {"n": "Faerie Fire", "src": "elven", "ap": 1, "kind": "save", "limit": "turn", "range": Rules.RACIAL_RANGE, "save": "DEX", "icon": "spark", "effect": "glow", "desc": "The foe glows until your next turn: attacks against it flip 1 extra coin, and it can’t hide. DEX save."},
	"lull": {"n": "Lull", "src": "elven", "ap": 1, "kind": "save", "limit": "turn", "range": Rules.RACIAL_RANGE, "save": "WIS", "icon": "moon", "effect": "lull", "desc": "The foe dozes off and loses its next attack. Any hit wakes it. WIS save."},
	"scorch": {"n": "Scorch", "src": "bloodline", "ap": 1, "kind": "attack", "limit": "turn", "range": Rules.RACIAL_RANGE, "ranged": true, "ab": "CHA", "dmg": Rules.RACIAL_DAMAGE, "icon": "flame", "desc": "A lance of fire at one foe in range. Attack flip to hit."},
	"ember_mend": {"n": "Ember Mend", "src": "bloodline", "ap": 1, "kind": "ally", "limit": "turn", "range": Rules.RACIAL_RANGE, "icon": "heart", "effect": "mend", "desc": "Heal an ally a little, more if they’re below half HP."},
	"guiding_ember": {"n": "Guiding Ember", "src": "bloodline", "ap": 1, "kind": "self", "limit": "turn", "icon": "spark", "effect": "guide", "desc": "A small light drifts out and reveals hidden foes and traps within 3 hexes."},
	# Ranger class cards (03 -> Martial class cards) and the Ranger's weapon cards (04 -> Weapon category cards; text from CreatorData).
	"hunters_mark": {"n": "Hunter's Mark", "src": "klass", "ap": 1, "kind": "mark", "limit": "turn", "icon": "M12 3v4 M12 17v4 M3 12h4 M17 12h4 M12 8a4 4 0 1 0 0 8a4 4 0 1 0 0-8", "desc": "Ranger: a marked foe takes extra damage from you for the fight."},
	"snare": {"n": "Snare", "src": "klass", "ap": 1, "kind": "cell", "limit": "turn", "range": Rules.SNARE_RANGE, "effect": "snare", "icon": "M4 18h16 M7 18l5-9 5 9 M12 9V5", "desc": "Ranger: set a hidden trap on a hex; the first foe to step in is rooted."},
	"quick_slash": {"n": "Quick Slash", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "icon": "w_shortsword", "effect": "quick", "desc": "Shortsword: a cheap extra attack."},
	"dancing_step": {"n": "Dancing Step", "src": "weapon", "ap": 0, "kind": "cell", "limit": "turn", "range": Rules.DANCE_HEXES, "effect": "dance", "icon": "w_scimitar", "desc": "Scimitar: right after a scimitar attack, take a free short move."},
	"sweeping_arc": {"n": "Sweeping Arc", "src": "weapon", "ap": 1, "kind": "arc", "limit": "turn", "range": 2, "icon": "w_glaive", "desc": "Glaive: hit enemies in a wide arc."},
	"double_shot": {"n": "Double Shot", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 6, "ranged": true, "shots": 2, "icon": "w_shortbow", "desc": "Shortbow: two quick arrows."},
	"aimed_shot": {"n": "Aimed Shot", "src": "weapon", "ap": 3, "kind": "attack", "limit": "turn", "range": 8, "ranged": true, "times": Rules.AIMED_TIMES, "pierce": true, "icon": "w_longbow", "desc": "Longbow: one huge shot."},
	"pinning_bolt": {"n": "Pinning Bolt", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 6, "ranged": true, "rider": "snare", "icon": "w_crossbow", "desc": "Crossbow: root an enemy."},
	"guard_up": {"n": "Guard Up", "src": "weapon", "ap": 1, "kind": "self", "limit": "turn", "effect": "guard", "icon": "w_gauntlets", "desc": "Gauntlets: take less damage until your next turn and counter the first hit."},
	"haymaker": {"n": "Haymaker", "src": "weapon", "ap": 2, "kind": "attack", "limit": "turn", "range": 1, "times": 2, "rider": "haymaker", "save": "CON", "icon": "w_knuckles", "desc": "Brass knuckles: a big hit that can stun (CON save)."},
	"step_strike": {"n": "Step and Strike", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "step": Rules.STEP_STRIKE_HEXES, "icon": "w_wraps", "desc": "Wraps: move a short way and strike."},
	"poison_blade": {"n": "Poison Blade", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "icon": "drop", "effect": "poison", "desc": "Rogue: every hit for the rest of this turn poisons."},
}

## The basic attack's icon follows the weapon (Combat v14).
const WEAPON_ICON := {"longsword": "sword", "staff": "staff", "mace": "mace", "dagger": "dagger"}


## A card for whoever holds it: the basic attack's weapon, and Breath Weapon's dragon type (sub: "Blue"), as the creator shows it.
static func get_card(id: String, weapon := "", sub := "") -> Dictionary:
	var c: Dictionary = ALL[id].duplicate()
	c.id = id
	if id == "attack":
		c.icon = WEAPON_ICON.get(weapon, "w_" + weapon if CreatorData.IC.has("w_" + weapon) else "sword")   # the creator's weapon icon otherwise
		c.desc = c.desc % weapon
	if CreatorData.PI.has(c.get("icon", "")) and not Icons.PATHS.has(c.icon):
		c.icon = CreatorData.PI[c.icon]
	elif CreatorData.IC.has(c.get("icon", "")) and not Icons.PATHS.has(c.icon):
		c.icon = CreatorData.IC[c.icon]
	if id == "attack" or (id == "sneak_attack" and weapon != ""):   # a weapon attack's reach and ranged-ness follow the weapon (04, 03)
		c.range = Weapons.of(weapon).range
		c.ranged = Weapons.ranged(weapon)
	if id == "throw":
		c.desc = "%s: a ranged attack with the %s. It returns to your hand." % [weapon.capitalize(), weapon]
	if id == "breath" and CreatorData.DRI.has(sub):
		c.icon = CreatorData.PI[CreatorData.DRI[sub]]
		c.desc = "%s %s" % [c.desc, CreatorData.ELEM[sub]]
	return c


## Card names whose one word is too wide for a card, and where they break instead (Ethan, Nov 5, 2026: "Glimmer / step").
const NAME_BREAKS := {"Glimmerstep": "Glimmer step", "Bonebreaker": "Bone breaker"}


## A card name as the lines it's drawn in, on a card `width` wide: words, with the over-wide ones broken where NAME_BREAKS says.
static func name_lines(n: String, font: Font, size: int, width: float) -> PackedStringArray:
	if font.get_string_size(n, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x <= width:
		return PackedStringArray([n])
	var out := PackedStringArray()
	for w in n.split(" "):
		if font.get_string_size(w, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x > width and NAME_BREAKS.has(w):
			out.append_array(NAME_BREAKS[w].split(" "))
		else:
			out.append(w)
	return out


static func ap_text(c: Dictionary) -> String:
	return "?" if c.ap < 0 else str(c.ap)
