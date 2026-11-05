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
static var band_heads := [0, 0, 0]           # added to the heads it takes to hit
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
static func roster(scene: String, roles: Array, at_band: int) -> Array:
	var out := []
	for role: String in roles:
		var r: Dictionary = ROLES[role]
		var look: Array = MIX.get(scene, MIX.enc_fight_bandits)[role]
		var hp: int = roundi(r.hp * band_hp[at_band - 1])
		out.append({name = look[1], mini = look[0], role = role, ability = "STR", hp = hp, max_hp = hp, score = r.coins + band_coins[at_band - 1], damage = roundi(r.damage * band_damage[at_band - 1]),
				heads = 1 + (1 if role == "elite" else 0) + band_heads[at_band - 1]})
	return out


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
