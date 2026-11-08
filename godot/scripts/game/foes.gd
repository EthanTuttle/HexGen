class_name Foes
extends RefCounted
## Who a fight is against (design/06 -> First playable; coins: design/03 -> Hit chance scaling). All PLACEHOLDER until the combat balance pass, except the coins.

## defence: the heads it takes to hit, printed by role (DOCS: 03 -> Hit chance scaling, Ethan, Nov 7, 2026); Sneak past
## and Ambush need the toughest foe's. Bosses aren't rolled yet. xp: per foe, times the region tier (05 -> XP; PLACEHOLDER).
const ROLES := {
	"minion": {"hp": 4, "damage": 1, "coins": 2, "xp": 2, "defence": 1},
	"soldier": {"hp": 6, "damage": 2, "coins": 3, "xp": 4, "defence": 1},
	"elite": {"hp": 10, "damage": 3, "coins": 4, "xp": 8, "defence": 2},
	"boss": {"hp": 16, "damage": 4, "coins": 5, "xp": 16, "defence": 3},   # PLACEHOLDER hp, damage and xp: no boss is rolled yet
}
## A scene's foes by role: their mini and name. Giants stay out of early fights.
const MIX := {
	"enc_fight_wolves": {"minion": ["enemy_wolf", "[Wolf %s]"], "soldier": ["enemy_wolf", "[Dire wolf %s]"], "elite": ["enemy_wolf_elite", "[Alpha wolf %s]"]},
	"enc_fight_bandits": {"minion": ["enemy_bandit_ranged", "[Bandit archer %s]"], "soldier": ["enemy_bandit_melee", "[Bandit %s]"], "elite": ["enemy_bandit_elite", "[Bandit chief %s]"]},
}


## By region tier, 1 to 3 (DOCS: 02 -> Encounters, Ethan, Nov 7, 2026: toughness from region tier and enemy type, not distance
## or the hero's level). PLACEHOLDER: the old near, mid and far numbers, until the enemy balance pass; play_check's --tune
## can override each, to compare.
static var tier_hp := [1.5, 2.0, 2.5]        # role HP times this
static var tier_damage := [1.5, 1.5, 2.0]    # role damage times this, rounded
static var tier_coins := [0, 1, 2]           # added to the role's coins
static var tier_count := [[3, 3], [3, 3], [3, 4]]
static var pair_count := [2, 3]              # tier 1, while it's only the hero and Fluffy
static var attacks_per_turn := 1   # PLACEHOLDER: the rest of its AP goes on moving
static var debug_tier := 0   # a test aid: every fight at this tier


## A tile's tier for its foes: a finished region's own (1 to 3); any other tile counts as tier 1 (02 -> Encounters).
static func tier(g: Node, t: Vector2i) -> int:
	if debug_tier > 0:
		return debug_tier
	return clampi(int(g.regions[g.finished[t]].tier), 1, 3) if g.finished.has(t) else 1


## One elite from tier 2 on (PLACEHOLDER, as the old mid band); how many by tier_count.
static func roll_roles(at_tier: int, rng: RandomNumberGenerator, party_size := 4) -> Array:
	var counts: Array = pair_count if at_tier == 1 and party_size <= 2 else tier_count[at_tier - 1]
	var count := rng.randi_range(counts[0], counts[1])
	var roles := []
	if at_tier >= 2:
		roles.append("elite")
	while roles.size() < count:
		roles.append("minion" if rng.randf() < 0.5 else "soldier")
	return roles


## The units a fight adds, in the shape Rules.ENEMY has.
static func roster(scene: String, roles: Array, at_tier: int) -> Array:
	var out := []
	for role: String in roles:
		var r: Dictionary = ROLES[role]
		var look: Array = MIX.get(scene, MIX.enc_fight_bandits)[role]
		var hp: int = roundi(r.hp * tier_hp[at_tier - 1])
		var damage: int = roundi(r.damage * tier_damage[at_tier - 1])
		out.append({name = look[1], mini = look[0], role = role, ability = "STR", hp = hp, max_hp = hp, score = r.coins + tier_coins[at_tier - 1], damage = damage,
				heads = r.defence})
	return out


## XP for a won fight: per foe by role, times the tier (05 -> XP). Gold is the same amount (06 -> First playable). Wins only.
static func reward(roles: Array, at_tier: int) -> int:
	var total := 0
	for role: String in roles:
		total += ROLES[role].xp * at_tier
	return total


## The heads Sneak past and Ambush need: the toughest foe's defence (03 -> Ambush).
static func sneak_heads(roles: Array) -> int:
	var most := 1
	for role: String in roles:
		most = maxi(most, ROLES[role].defence)
	return most
