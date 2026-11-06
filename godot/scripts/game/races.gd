class_name Races
extends RefCounted
## What a character's race does in play (DOCS: design/03 -> Races and Racial spells; scope and amounts: design/06 -> First
## playable -> Races). Members are Rules.PARTY's dictionaries, with race and sub ("Wood elf", "Metal", "Blue", "Hayes").
## Not here: the level-7 tiefling spells and Human's Versatile (a Fighter already uses every weapon and armour).

## The high elf's spells by the creator's name, and the tieflings' set spell by bloodline (DOCS: Racial spells).
const ELF_SPELLS := {"Glimmerstep": "glimmerstep", "Faerie Fire": "faerie_fire", "Lull": "lull"}
const BLOODLINE := {"Hayes": "scorch", "Conley": "ember_mend", "Keegan": "guiding_ember"}


## The racial cards and level-1 racial spells a member gets (DOCS: Races -> Racial action cards).
static func cards(m: Dictionary) -> Array:
	var out := []
	match String(m.get("race", "")):
		"Halfling":
			out.append("duck_behind")
		"Dragonborn":
			out.append("breath")
		"Golem":
			if m.get("sub", "") == "Metal":
				out.append("lockdown")
			elif m.get("sub", "") == "Stone":
				out.append("stone_throw")
		"Fluffy":
			out.append("claw_swipe")
		"Elf":
			if m.get("sub", "") == "High elf" and ELF_SPELLS.has(m.get("spell", "")):
				out.append(ELF_SPELLS[m.spell])
		"Tiefling":
			if BLOODLINE.has(m.get("sub", "")):
				out.append(BLOODLINE[m.sub])
	return out


static func is_sub(m: Dictionary, sub: String) -> bool:
	return m.get("sub", "") == sub


static func lucky(m: Dictionary) -> bool:
	return m.get("race", "") == "Halfling"


static func score(m: Dictionary, ability: String) -> int:
	return int(m.get("scores", {}).get(ability, 1))


## Extra hexes per Move in combat (wood elf).
static func move_bonus(m: Dictionary) -> int:
	return Rules.WOOD_ELF_MOVE if is_sub(m, "Wood elf") else 0


## Damage taken off hits and Breath Weapon (metal golem), before Lockdown doubles it.
static func reduction(m: Dictionary, level: int) -> int:
	return Rules.METAL_REDUCTION + level / Rules.METAL_EVERY if m.get("race", "") == "Golem" and is_sub(m, "Metal") else 0


## HP healed at the start of each of its turns (wood golem's Regrowth).
static func regrowth(m: Dictionary, level: int) -> int:
	if m.get("race", "") != "Golem" or not is_sub(m, "Wood"):
		return 0
	return Rules.REGROWTH_BIGGER if level >= Rules.REGROWTH_BIGGER_AT else Rules.REGROWTH


## Extra max HP from being a shield dwarf, at this level.
## Max HP a level adds (06 -> Levels, Ethan, Nov 6, 2026, PLACEHOLDER): the class's amount plus half CON rounded up.
static func level_hp(m: Dictionary) -> int:
	return int(Rules.HP_PER_LEVEL.get(m.get("klass", Rules.COMPANION_CLASS.get(m.get("name", ""), "fighter")), 0)) + ceili(score(m, "CON") / 2.0)


static func extra_hp(m: Dictionary, level: int) -> int:
	return Rules.SHIELD_DWARF_HP + Rules.SHIELD_DWARF_HP_LEVEL * (level - 1) if is_sub(m, "Shield dwarf") else 0


## The forge dwarf's extra coin, on Attack and weapon cards only.
static func forge_coin(m: Dictionary, k: Dictionary) -> int:
	return 1 if is_sub(m, "Forge dwarf") and (k.id == "attack" or k.src == "weapon") else 0


## Breath Weapon's damage and line length for a member's dragon type.
static func breath_damage(m: Dictionary, level: int) -> int:
	return Rules.BREATH_DAMAGE + (Rules.BREATH_RED if is_sub(m, "Red") else 0) + level / Rules.BREATH_EVERY


static func breath_reach(m: Dictionary) -> int:
	return Rules.BREATH_LINE + (Rules.BREATH_BLUE if is_sub(m, "Blue") else 0)


## Any wood elf in the party (Mel too) makes it walk faster and spend less clock per hex.
static func wood_elf_in(party: Array) -> bool:
	return party.any(func(m): return is_sub(m, "Wood elf"))


## The hero's member from a run: race, sub, spell and scores from the creator, or HERO_DEFAULT; the racial cards join the
## All actions list only (the default hotbars stay as they are for now).
static func make_hero(m: Dictionary, run: RunSetup) -> void:
	# Gear counts in play (06 -> Start): the weapon sets the attack's score and cards, a shield gives Block and Shield Bash,
	# armour sets defence; the class gives its cards and HP.
	m.weapon = run.main if run.main != "" else Rules.HERO_DEFAULT.main
	m.off = run.off if run.main != "" else Rules.HERO_DEFAULT.off
	m.armour = run.armour if run.main != "" else Rules.HERO_DEFAULT.armour
	m.ability = Weapons.of(m.weapon).ab
	m.klass = run.klass
	m.cards = Weapons.cards_for(run.klass, m.weapon, m.off)
	m.hp = Weapons.CLASS_HP.get(run.klass, m.hp)
	m.race = run.race if run.race != "" else Rules.HERO_DEFAULT.race
	m.sub = run.sub if run.race != "" else Rules.HERO_DEFAULT.sub
	m.spell = run.elf_spell
	m.scores = run.scores.duplicate() if not run.scores.is_empty() else Rules.HERO_DEFAULT.scores.duplicate()
	Hero.live = m.scores
	m.proficiencies = run.proficiencies.duplicate()


## The starting hotbar (DOCS: design/07 -> Combat screen -> Starting hotbar, Ethan, Nov 5, 2026): Move, Attack, the racial
## card, class cards and spells, weapon arts, then Defend and Use item if slots are left. Passives take no slot; the rest
## stay in All actions. Racial spells count with the racial card.
static func starting_bar(m: Dictionary) -> Array:
	var order := ["move", "attack"]
	order.append_array(cards(m))
	for src in ["klass", "weapon"]:
		for id: String in m.cards:
			if Cards.ALL[id].src == src and not id in order and id != "block":
				order.append(id)
	order.append_array(["defend", "block", "use_item"])   # Block is Defend with a shield (04 -> Shields)
	return order.filter(func(id): return id in m.cards).slice(0, Rules.HOTBAR_SLOTS)


## Racial cards join the card list, the starting hotbar is set, and the hero's HP and Lucky charges are set once on joining.
static func join(m: Dictionary, level: int) -> void:
	if Rules.old("scores"):   # test aid: the companions' old one-score lines (Fluffy INT 3, Chelmsford STR 2, Mel DEX 3)
		m.scores = {"Fluffy": {"INT": 3}, "Chelmsford": {"STR": 2}, "Mel": {"DEX": 3}}.get(m.name, m.scores)
	if Rules.old("throw"):   # test aid: Throw and Bonebreaker before they had an AP cost (unusable)
		m.cards = m.cards.filter(func(id): return not id in ["throw", "bonebreaker"])
	if Rules.old("racial") and m.name in ["Fluffy", "Chelmsford", "Mel"]:   # test aid: companions without racial cards
		m.hot = starting_bar(m)
		m.max_hp = m.hp
		return
	for id in cards(m):
		if not id in m.cards:
			m.cards.append(id)
	m.hot = starting_bar(m)
	for l: int in Rules.SCORE_LEVELS:   # joining late: the points already passed, on the main score, capped (03, Ethan, Nov 6, 2026)
		if l <= level:
			m.scores[m.ability] = mini(score(m, m.ability) + 1, LevelPick.CAP)
	m.hp += extra_hp(m, level) + level_hp(m) * (level - 1)   # joining at the party's level, with its levels' HP
	m.max_hp = m.hp
	if lucky(m):
		m.lucky = Rules.LUCKY_CHARGES
