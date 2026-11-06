class_name Foes
extends RefCounted
## Who a fight is against (design/06 -> First playable; coins: design/03 -> Hit chance scaling). All PLACEHOLDER until the combat balance pass, except the coins.

const ROLES := {
	"minion": {"hp": 4, "damage": 1, "coins": 2, "reward": 2, "sneak": 1},
	"soldier": {"hp": 6, "damage": 2, "coins": 3, "reward": 4, "sneak": 2},
	"elite": {"hp": 10, "damage": 3, "coins": 4, "reward": 8, "sneak": 3},
}
## A scene's foes by role: their mini and name. Giants stay out of early fights.
const MIX := {
	"enc_fight_wolves": {"minion": ["enemy_wolf", "[Wolf %s]"], "soldier": ["enemy_wolf", "[Dire wolf %s]"], "elite": ["enemy_wolf_elite", "[Alpha wolf %s]"]},
	"enc_fight_bandits": {"minion": ["enemy_bandit_ranged", "[Bandit archer %s]"], "soldier": ["enemy_bandit_melee", "[Bandit %s]"], "elite": ["enemy_bandit_elite", "[Bandit chief %s]"]},
}
const NEAR_UP_TO := 4
const MID_UP_TO := 9


## By band, near to far. PLACEHOLDER until the combat balance pass; play_check's --bands can override each, to compare.
static var band_hp := [1.5, 2.0, 2.5]        # role HP times this
static var band_damage := [1.5, 1.5, 2.0]    # role damage times this, rounded
static var band_coins := [0, 1, 2]           # added to the role's coins
static var band_heads := [0, 0, 1]           # added to the heads it takes to hit: DOCS (03 -> Hit chance scaling) far +1
static var far_from_level := 8               # the far +1 counts from this hero level (03 -> Hit chance scaling, Ethan, Nov 6, 2026; --tune farfrom:N)
static var elite_heads := 1                  # DOCS (03): elites add +1 (bosses too, when there are any)
## The level curve (03 -> Hit chance scaling: a direction to test, Nov 5, 2026): heads added to each role's target from the
## hero's level, at the score steps (levels 1, 4, 8, 12, 16). PLACEHOLDER: no steps until Ethan sets them; --tune's
## "level" tries one, e.g. level:elite=0,0,1,1,2.
const LEVEL_STEPS := [1, 4, 8, 12, 16]
static var level_heads := {"minion": [0, 0, 0, 0, 0], "soldier": [0, 0, 0, 0, 0], "elite": [0, 0, 0, 0, 0]}
## Foes grow with the hero's level (06 -> Levels, Ethan, Nov 6, 2026): HP and damage times 1 + these per level above 1,
## by band (near, mid, far), tuned so a full party loses about 10% of mid fights and 40% of far fights at its level.
## --tune's "growhp" and "growdmg" try others.
## Measured Nov 6, 2026 (Fighter and Rangers, levels 3-8): mid 0.32 for both; far 0.25 HP, 0.1 damage. Near doesn't grow.
static var grow_hp := [0.0, 0.32, 0.25]
static var grow_damage := [0.0, 0.32, 0.1]
static var band_count := [[3, 3], [3, 3], [3, 4]]
static var near_pair_count := [2, 3]         # near, while it's only the hero and Fluffy
static var attacks_per_turn := 1   # PLACEHOLDER: the rest of its AP goes on moving
static var debug_band := 0   # a test aid: every fight at this band


## 1 near, 2 mid, 3 far, by tiles from the start.
static func band(t: Vector2i) -> int:
	if debug_band > 0:
		return debug_band
	var away := Rules.hex_distance(t, Rules.START_TILE)
	return 1 if away <= NEAR_UP_TO else 2 if away <= MID_UP_TO else 3


## One elite from mid on, as design/06; how many by band_count.
static func roll_roles(at_band: int, rng: RandomNumberGenerator, party_size := 4) -> Array:
	var counts: Array = near_pair_count if at_band == 1 and party_size <= 2 else band_count[at_band - 1]
	var count := rng.randi_range(counts[0], counts[1])
	var roles := []
	if at_band >= 2:
		roles.append("elite")
	while roles.size() < count:
		roles.append("minion" if rng.randf() < 0.5 else "soldier")
	return roles


## The units a fight adds, in the shape Rules.ENEMY has.
static func roster(scene: String, roles: Array, at_band: int, level := 1) -> Array:
	var out := []
	for role: String in roles:
		var r: Dictionary = ROLES[role]
		var look: Array = MIX.get(scene, MIX.enc_fight_bandits)[role]
		var hp: int = roundi(r.hp * band_hp[at_band - 1] * (1.0 + grow_hp[at_band - 1] * (level - 1)))
		var damage: int = roundi(r.damage * band_damage[at_band - 1] * (1.0 + grow_damage[at_band - 1] * (level - 1)))
		out.append({name = look[1], mini = look[0], role = role, ability = "STR", hp = hp, max_hp = hp, score = r.coins + band_coins[at_band - 1], damage = damage,
				heads = 1 + (elite_heads if role == "elite" else 0) + (band_heads[at_band - 1] if level >= far_from_level else 0) + level_add(role, level)})
	return out


## The level curve's heads for this role at this hero level.
static func level_add(role: String, level: int) -> int:
	var add := 0
	for i in LEVEL_STEPS.size():
		if level >= LEVEL_STEPS[i]:
			add = level_heads[role][i]
	return add


## Gold and XP alike: per foe by role, times the band (design/06). Wins only.
static func reward(roles: Array, at_band: int) -> int:
	var total := 0
	for role: String in roles:
		total += ROLES[role].reward * at_band
	return total


## The heads Sneak past needs: by the toughest foe's role.
static func sneak_heads(roles: Array) -> int:
	var most := 1
	for role: String in roles:
		most = maxi(most, ROLES[role].sneak)
	return most
