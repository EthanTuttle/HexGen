class_name FightBot
extends RefCounted
## A plain player for the checks: Fluffy's bolts and frost when in reach, the hero's Shield Bash then attacks, Second Wind
## when hurt, heals on hurt allies, and the racial cards (design/03 -> Races): Breath Weapon down a line with foes and no
## allies, Faerie Fire then Lull on the nearest foe, Stone Throw, Scorch, Claw Swipe, Ember Mend and Lockdown when hurt.
## A test aid only.

var tree: SceneTree
var drunk := 0
var used := {}          # card id -> times played, for the race check's report


func _init(t: SceneTree) -> void:
	tree = t


func _wait(s: float) -> void:
	await tree.create_timer(s).timeout


## Plays the fight out. Returns {rounds, hp0, hp1, downs, wiped}.
func play(f: Fight) -> Dictionary:
	var hp0: int = f.allies().reduce(func(n, u): return n + u.hp, 0)
	var rounds := 0
	while f.active and f.phase != "over":
		if f.phase != "allies" or f.busy:
			await _wait(0.1)
			continue
		rounds += 1
		for u: Dictionary in f.allies():
			if not f.active or f.phase != "allies" or u.down:
				continue
			f.select(u)
			await _wait(0.1)
			await take_turn(f, u)
		if f.active and f.phase == "allies":
			f.end_phase()
			await _wait(0.2)
			if f.hud.confirm_open():
				f.confirm_end()
		await _wait(0.1)
		if rounds > 30:
			break
	var hp1: int = f.allies().reduce(func(n, u): return n + maxi(u.hp, 0), 0)
	return {rounds = rounds, hp0 = hp0, hp1 = hp1, downs = f.allies().filter(func(u): return u.down).size(),
			wiped = f.allies().all(func(u): return u.down)}


func _ready_card(f: Fight, u: Dictionary, id: String) -> bool:
	return id in u.cards and f.cant_use(u, Cards.get_card(id, u.weapon, u.sub)) == ""


func _settle(f: Fight) -> void:
	await _wait(0.2)
	while f.busy:
		await _wait(0.05)


## A direction whose breath line holds a foe and no ally, or -1.
func _breath_dir(f: Fight, u: Dictionary) -> int:
	for d in Hex.NEIGHBOURS.size():
		var line := f.breath_line(u, d)
		var hits := line.map(func(c): return f.unit_at(c)).filter(func(t): return not t.is_empty() and not t.down)
		if hits.any(func(t): return not t.ally) and not hits.any(func(t): return t.ally):
			return d
	return -1


func take_turn(f: Fight, u: Dictionary) -> void:
	var tries := 0
	while f.active and f.phase == "allies" and f.ap_left(u) > 0 and tries < 8:
		tries += 1
		var foes := f.foes_of(u)
		if foes.is_empty():
			return
		foes.sort_custom(func(a, b): return f.dist(a, u) < f.dist(b, u))
		var foe: Dictionary = foes[0]
		var picked := ""
		var hurt: Array = f.allies().filter(func(a): return not a.down and a.hp * 2 < a.max_hp and f.dist(a, u) <= Rules.RACIAL_RANGE)
		for heal in ["healing_word", "ember_mend"]:
			if picked == "" and _ready_card(f, u, heal) and not hurt.is_empty() and f.dist(hurt[0], u) <= Cards.get_card(heal).range:
				picked = heal
		if picked != "":
			f.pick_card(picked)
			await _wait(0.05)
			await f.click_cell(hurt[0].cell)
			await _wait(0.05)
			await f.press_button()
			used[picked] = used.get(picked, 0) + 1
			await _settle(f)
			continue
		if _ready_card(f, u, "breath") and f.ap_left(u) >= 2:
			var d := _breath_dir(f, u)
			if d >= 0:
				f.pick_card("breath")
				await _wait(0.05)
				await f.click_cell(u.cell + Hex.NEIGHBOURS[d])
				await f.press_button()
				used["breath"] = used.get("breath", 0) + 1
				await _settle(f)
				continue
		if u.hp * 2 < u.max_hp and _ready_card(f, u, "second_wind"):
			picked = "second_wind"
		elif u.hp * 2 < u.max_hp and _ready_card(f, u, "lockdown") and f.dist(foe, u) == 1:
			picked = "lockdown"
		elif u.hp * 2 < u.max_hp and f.cant_use(u, Cards.get_card("use_item")) == "":
			picked = "use_item"
			drunk += 1
		else:
			for id: String in ["faerie_fire", "lull", "firebolt", "frost_ray", "scorch", "stone_throw", "sacred_flame", "claw_swipe", "sneak_attack", "throw", "shield_bash", "attack"]:
				if _ready_card(f, u, id):
					var c := Cards.get_card(id, u.weapon)
					if f.in_reach(u, foe, c) and not (id == "lull" and foe.lull) and not (id == "faerie_fire" and f.on(foe, "glow")):
						picked = id
						break
		if picked == "":
			var options: Dictionary = f.reachable(u)
			var best := u.cell as Vector2i
			for c in options:
				if Rules.hex_distance(c, foe.cell) < Rules.hex_distance(best, foe.cell):
					best = c
			if best == u.cell:
				return
			f.pick_card("move")
			await _wait(0.05)
			await f.click_cell(best)
			await _wait(0.1)
			continue
		f.pick_card(picked)
		await _wait(0.05)
		if Cards.get_card(picked).kind in ["attack", "save"]:
			await f.click_cell(foe.cell)
			await _wait(0.05)
		await f.press_button()
		used[picked] = used.get(picked, 0) + 1
		await _settle(f)
