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


## 1 near, 2 mid, 3 far, by tiles from the start.
static func band(t: Vector2i) -> int:
	var away := Rules.hex_distance(t, Rules.START_TILE)
	return 1 if away <= NEAR_UP_TO else 2 if away <= MID_UP_TO else 3


## 2 or 3 foes, one elite from mid on.
static func roll_roles(at_band: int, rng: RandomNumberGenerator) -> Array:
	var count := rng.randi_range(2, 3)
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
		var hp: int = r.hp * at_band
		out.append({name = look[1], mini = look[0], role = role, ability = "STR", hp = hp, max_hp = hp, score = r.coins + 2 * (at_band - 1), damage = r.damage * at_band,
				heads = 1 + (1 if role == "elite" else 0) + (1 if at_band >= 3 else 0)})
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
