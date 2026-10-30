class_name Fight
extends Node3D
## A small turn-based fight on the encounter tile's radius-4 combat board
## (design/03 Classes & combat.md -> Turns, AP and health; Combat; Coin checks). The screen and its flow
## follow Combat v14 (mockups/combat/Combat-v14-AllyTargets.dc.html): pick a character in the party tray
## (or on the board), pick a card on the hotbar, tap a target, then press Flip coins / Cast / Use.
## Turns go side by side: all allies act in any order, then all foes. 3 AP each, up to 6 with bonus AP.

signal finished(won: bool)

const PARTY_CELLS := [Vector2i(0, 2), Vector2i(-1, 3), Vector2i(1, 2), Vector2i(0, 3)]   # PLACEHOLDER line-up
const ENEMY_CELLS := [Vector2i(0, -3), Vector2i(1, -3), Vector2i(-1, -2), Vector2i(2, -3)]
const LABELS := ["A", "B", "C", "D"]

var active := false
var game: Game
var rng: RandomNumberGenerator
var board := CombatBoard.new()
var units: Array[Dictionary] = []
var current: Dictionary = {}     # the ally acting
var sel := "attack"              # the picked card
var target: Dictionary = {}      # picked foe
var ally_target: Dictionary = {} # picked ally (for ally cards)
var result: Dictionary = {}      # last flip / cast: {coins, title, sub, good}
var self_done := ""              # a self card just used
var moved := 0                   # hexes moved by the last Move
var phase := "allies"
var rocks: Array = []
var trees: Array = []
var busy := false
var hud: CombatHud

var _overlays: Array[Node3D] = []
var _hex_mesh: Mesh
var _disc_mesh: Mesh
var _mats := {}
var _wired := false


func _ready() -> void:
	add_child(board)
	var p := Piece.new()
	var hexagon := Hex.hex_corners(Hex.CELL_RADIUS * 0.94, false)
	hexagon.reverse()
	p.flat(hexagon, 0.02, Color.WHITE)
	_hex_mesh = p.mesh()
	var d := Piece.new()
	d.cylinder(Vector3.ZERO, 0.62, 0.02, Color.WHITE, 24)
	_disc_mesh = d.mesh()
	# Combat v14 colours: active ally rim, foes in reach (gold), the target (orange), allies in reach
	# (light green circle), the ally target (dark green), hexes a Move can reach.
	for k in [["active", "#FCF7EE"], ["reach", "#F2C14E"], ["target", "#B5532F"], ["ally", "#A8DC8C"],
			["ally_target", "#2E8A47"], ["move", "#D3EBC1"], ["move_tree", "#86B97E"]]:
		var m := StandardMaterial3D.new()
		m.albedo_color = Color(k[1])
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		_mats[k[0]] = m


## Runs one fight to the end. Returns true if the party won.
func run(g: Game, terrain: String, tile: Vector2i, foes: int) -> bool:
	game = g
	rng = g.rng
	_wire()
	active = true
	units.clear()
	result = {}
	# The board grows out of the map tile: its terrain sets the trees and rocks (PLACEHOLDER counts).
	var free: Array = CombatBoard.cells().filter(func(c): return not (c in PARTY_CELLS or c in ENEMY_CELLS))
	var local := RandomNumberGenerator.new()
	local.seed = hash("%d,%d" % [tile.x, tile.y])
	trees = []
	rocks = []
	for k in Rules.BOARD_TREES.get(terrain, 0) + Rules.BOARD_ROCKS.get(terrain, 0):
		var c = free.pop_at(local.randi_range(0, free.size() - 1))
		(trees if k < Rules.BOARD_TREES.get(terrain, 0) else rocks).append(c)
	board.setup(trees, rocks)
	for i in game.party.size():
		_add_unit(game.party[i], PARTY_CELLS[i], true, "")
	for i in foes:
		var e: Dictionary = Rules.ENEMY.duplicate()
		e.max_hp = e.hp
		e.name = e.name % LABELS[i]
		_add_unit(e, ENEMY_CELLS[i], false, LABELS[i])
	if hud == null:
		hud = CombatHud.new(self)
		game.safe.add_child(hud)
		game.popup.move_to_front()
	hud.visible = true
	game.rig.frame(position, 22.0, 52.0)
	game.rig.focus = Vector2(368, 150)
	_start_allies()
	var won: bool = await finished
	for u in units:
		if u.ally:
			u.member.hp = maxi(u.hp, 0)
	hud.visible = false
	_clear_overlays()
	game.rig.focus = Vector2(378, 200)
	active = false
	return won


func _add_unit(m: Dictionary, c: Vector2i, ally: bool, label: String) -> void:
	var mini := board.add_mini(m.mini, c, Vector2(0, -1) if ally else Vector2(0, 1))
	var u := {name = m.name, initial = m.get("initial", label), color = m.get("color", "#8E3B2E"), mini = mini,
			cell = c, hp = m.hp, max_hp = m.max_hp, score = m.score, ability = m.ability, ally = ally,
			down = m.hp <= 0, ap = 0, bonus = 0, defending = false, used = {}, used_fight = {},
			blessed = false, poison = false, weapon = m.get("weapon", "spear"),
			hot = m.get("hot", []), cards = m.get("cards", []), member = m}
	units.append(u)
	if u.down:
		mini.get_node("body").quaternion = Quaternion(Vector3.RIGHT, deg_to_rad(-80))


func allies() -> Array:
	return units.filter(func(u): return u.ally)


func foes_of(u: Dictionary) -> Array:
	return units.filter(func(o): return o.ally != u.ally and not o.down)


func card(id := "") -> Dictionary:
	return Cards.get_card(sel if id == "" else id, current.get("weapon", ""))


# --- Rules for using a card --------------------------------------------------------

func ap_left(u: Dictionary) -> int:
	return u.ap + u.bonus


func spent(u: Dictionary, c: Dictionary) -> bool:
	return (c.limit == "turn" and u.used.has(c.id)) or (c.limit == "fight" and u.used_fight.has(c.id))


## Why u can't use card c right now, or "" (Combat v14's notes under the button).
func cant_use(u: Dictionary, c: Dictionary) -> String:
	if c.ap < 0:
		return "AP cost not set yet"
	if spent(u, c):
		return "Once per fight: already used" if c.limit == "fight" else "Once per turn: already used"
	if ap_left(u) < c.ap:
		return "Not enough AP"
	if c.get("effect", "") == "item":
		return "No consumable equipped"    # PLACEHOLDER: no consumables in the loop yet
	return ""


func in_reach(u: Dictionary, foe: Dictionary, c: Dictionary) -> bool:
	return c.kind in ["attack", "save"] and not foe.down and not foe.ally and Rules.hex_distance(u.cell, foe.cell) <= c.get("range", 1)


func ally_in_reach(u: Dictionary, a: Dictionary, c: Dictionary) -> bool:
	return c.kind == "ally" and a.ally and not a.down and Rules.hex_distance(u.cell, a.cell) <= c.get("range", 1)


func _pay(u: Dictionary, c: Dictionary) -> void:
	var from_bonus := mini(u.bonus, c.ap)     # bonus AP is spent first (DOCS)
	u.bonus -= from_bonus
	u.ap -= c.ap - from_bonus
	if c.limit == "turn":
		u.used[c.id] = true
	elif c.limit == "fight":
		u.used_fight[c.id] = true


# --- Board helpers -----------------------------------------------------------------

func unit_at(c: Vector2i) -> Dictionary:
	for u in units:
		if u.cell == c and not (not u.ally and u.down):
			return u
	return {}


func _open(c: Vector2i) -> bool:
	return c in _all_cells() and not (c in rocks) and unit_at(c).is_empty()


var _cells_cache: Array[Vector2i] = []


func _all_cells() -> Array[Vector2i]:
	if _cells_cache.is_empty():
		_cells_cache = CombatBoard.cells()
	return _cells_cache


## Cells within one Move of u, with the path to each (BFS; DOCS: rocks and minis block, trees don't).
func reachable(u: Dictionary) -> Dictionary:
	var came := {u.cell: null}
	var depth := {u.cell: 0}
	var todo: Array = [u.cell]
	while not todo.is_empty():
		var c: Vector2i = todo.pop_front()
		if depth[c] >= Rules.MOVE_HEXES:
			continue
		for n in Hex.NEIGHBOURS:
			var m: Vector2i = c + n
			if not came.has(m) and _open(m):
				came[m] = c
				depth[m] = depth[c] + 1
				todo.append(m)
	var out := {}
	for c in came:
		if c == u.cell:
			continue
		var path: Array = []
		var k = c
		while k != u.cell:
			path.push_front(k)
			k = came[k]
		out[c] = path
	return out


func path_next_to(u: Dictionary, goal: Dictionary) -> Array:
	var came := {u.cell: u.cell}
	var todo: Array = [u.cell]
	var end = null
	while not todo.is_empty():
		var c: Vector2i = todo.pop_front()
		if Rules.hex_distance(c, goal.cell) == 1:
			end = c
			break
		for n in Hex.NEIGHBOURS:
			var m: Vector2i = c + n
			if not came.has(m) and _open(m):
				came[m] = c
				todo.append(m)
	if end == null:
		return []
	var path: Array = []
	var k = end
	while k != u.cell:
		path.push_front(k)
		k = came[k]
	return path


static func cell_at(p: Vector2) -> Vector2i:
	var q := p.x / (1.5 * Hex.CELL_RADIUS)
	var r := -p.y / Hex.CELL_FLATS - q / 2.0
	var s := -q - r
	var rq := roundf(q); var rr := roundf(r); var rs := roundf(s)
	var dq := absf(rq - q); var dr := absf(rr - r); var ds := absf(rs - s)
	if dq > dr and dq > ds:
		rq = -rr - rs
	elif dr > ds:
		rr = -rq - rs
	return Vector2i(int(rq), int(rr))


# --- Overlays on the board --------------------------------------------------------

func _clear_overlays() -> void:
	for o in _overlays:
		o.queue_free()
	_overlays.clear()


func _overlay(c: Vector2i, mat: String, disc := false) -> void:
	var mi := MeshInstance3D.new()
	mi.mesh = _disc_mesh if disc else _hex_mesh
	mi.material_override = _mats[mat]
	mi.position = Hex.to3(Hex.cell_position(c.x, c.y), 0.004 if not disc else 0.012)
	board.add_child(mi)
	_overlays.append(mi)


func _show_overlays() -> void:
	_clear_overlays()
	if current.is_empty() or phase != "allies":
		return
	var c := card()
	if c.kind == "move" and not busy and ap_left(current) >= 1:
		for cell in reachable(current).keys():
			_overlay(cell, "move_tree" if cell in trees else "move")
	_overlay(current.cell, "active")
	for u in units:
		if in_reach(current, u, c):
			_overlay(u.cell, "target" if u == target else "reach")
		if ally_in_reach(current, u, c):
			_overlay(u.cell, "ally_target" if u == ally_target else "ally", true)


func refresh() -> void:
	_show_overlays()
	hud.refresh()


# --- The allies' phase -------------------------------------------------------------

func _start_allies() -> void:
	phase = "allies"
	for u in units:
		if u.ally:
			u.ap = 0 if u.down else Rules.AP
			u.bonus = 0
			u.used = {}
			u.defending = false      # Defend lasts until your next turn
			u.poison = false
	current = {}
	game.rig.player_moved = false   # PLACEHOLDER ("the next action" isn't decided): a new turn centres again
	for u in units:
		if u.ally and not u.down:
			select(u)
			break
	refresh()


## Make u the acting character (portrait or token); the camera pans to them (DOCS: Combat screen -> Camera).
func select(u: Dictionary) -> void:
	if busy or u.down or not u.ally or phase != "allies":
		return
	current = u
	sel = "attack"
	target = {}
	ally_target = {}
	result = {}
	self_done = ""
	moved = 0
	if not game.rig.player_moved:   # the player's camera wins until the next turn (DOCS)
		game.rig.ease_to(global_position + u.mini.position, game.rig.distance, game.rig.yaw_deg)
	refresh()


func pick_card(id: String) -> void:
	if busy or current.is_empty():
		return
	sel = id
	result = {}
	self_done = ""
	ally_target = {}
	moved = 0
	if not target.is_empty() and not in_reach(current, target, card()):
		target = {}
	refresh()


func click_cell(c: Vector2i) -> void:
	if busy or phase != "allies" or current.is_empty():
		return
	var u := unit_at(c)
	var k := card()
	if not u.is_empty() and in_reach(current, u, k):
		target = u
		result = {}
		refresh()
	elif not u.is_empty() and ally_in_reach(current, u, k):
		ally_target = u
		result = {}
		refresh()
	elif not u.is_empty() and u.ally:
		select(u)
	elif k.kind == "move" and reachable(current).has(c) and cant_use(current, k) == "":
		await _move(current, reachable(current)[c])


func _move(u: Dictionary, path: Array) -> void:
	busy = true
	_pay(u, card("move"))
	u.cell = path[-1]
	moved = path.size()
	refresh()
	await board.step_along(u.mini, path)
	if not game.rig.player_moved:
		game.rig.ease_to(global_position + u.mini.position, game.rig.distance, game.rig.yaw_deg)
	busy = false
	refresh()


## The panel's main button: Flip coins (attacks), Cast (saves and ally spells) or Use (self cards).
func press_button() -> void:
	if busy or current.is_empty():
		return
	var k := card()
	if cant_use(current, k) != "":
		return
	match k.kind:
		"attack":
			if target.is_empty():
				return
			_pay(current, k)
			await _attack(current, target, k)
		"save":
			if target.is_empty():
				return
			_pay(current, k)
			await _save_spell(current, target, k)
		"ally":
			if ally_target.is_empty():
				return
			_pay(current, k)
			_ally_spell(current, ally_target, k)
		"self":
			_pay(current, k)
			_use_self(current, k)
	if active:
		refresh()


## Weapon attacks and attack spells flip the attacker's coins to hit (DOCS). Bless adds a coin.
## PLACEHOLDER damage: the attack's score; +2 for Sneak Attack on a flanked foe; +1 per hit under
## Poison Blade; -1 if the target defends.
func _attack(a: Dictionary, t: Dictionary, k: Dictionary) -> void:
	busy = true
	refresh()
	var n: int = a.score + (1 if a.blessed else 0)
	a.blessed = false
	var coins := Coins.flip(rng, n)
	var heads := Coins.heads(coins)
	var hit := heads >= Rules.HEADS_TO_HIT
	var dmg := 0
	if hit:
		dmg = a.score
		if k.get("effect", "") == "sneak" and _flanked(a, t):
			dmg += Rules.SNEAK_BONUS
		if a.poison:
			dmg += Rules.POISON_BONUS
		if t.defending:
			dmg -= Rules.DEFEND_REDUCTION
		dmg = maxi(dmg, 0)
	if a.ally:
		result = {coins = coins, title = "Hit!" if hit else "Miss", good = hit,
				sub = "%d heads (needs %d). %s" % [heads, Rules.HEADS_TO_HIT, "Damage: %d [placeholder, set by %s]" % [dmg, a.ability] if hit else "No damage."]}
		hud.refresh()
	await board.attack(a.mini, t.mini, hit)
	hud.float_text(t, "-%d" % dmg if hit else "Miss", hit)
	if hit:
		await _hurt(t, dmg)
	busy = false
	_check_end()


func _flanked(a: Dictionary, t: Dictionary) -> bool:
	for u in units:
		if u != a and u.ally == a.ally and not u.down and Rules.hex_distance(u.cell, t.cell) == 1:
			return true
	return false


## Save spells (Sacred Flame): the foe flips to save; a save halves the damage and ignores riders (DOCS).
func _save_spell(a: Dictionary, t: Dictionary, k: Dictionary) -> void:
	busy = true
	refresh()
	var coins := Coins.flip(rng, Rules.ENEMY_SAVE_COINS)
	var heads := Coins.heads(coins)
	var saved := heads >= 1
	var dmg: int = Rules.SPELL_DAMAGE / 2 if saved else Rules.SPELL_DAMAGE
	result = {coins = coins, title = "Saved: half damage" if saved else "Failed save!", good = not saved,
			sub = "%s flipped %d heads (needs 1 to save). %s" % [t.name, heads, "Riders are ignored. Damage: %d" % dmg if saved else "Full damage: %d [placeholder, set by WIS]" % dmg]}
	hud.refresh()
	await board.attack(a.mini, t.mini, true)
	hud.float_text(t, "-%d" % dmg, true)
	await _hurt(t, dmg)
	busy = false
	_check_end()


func _ally_spell(a: Dictionary, t: Dictionary, k: Dictionary) -> void:
	if k.effect == "heal":
		var before: int = t.hp
		t.hp = mini(t.max_hp, t.hp + Rules.HEAL)
		result = {coins = [], title = "Healed", good = true, sub = "%s heals %d HP. [amount set by WIS; placeholder]" % [t.name, t.hp - before]}
		hud.float_text(t, "+%d" % (t.hp - before), false, true)
	else:
		t.blessed = true
		result = {coins = [], title = "Blessed", good = true, sub = "%s flips an extra coin on their next check." % t.name}


func _use_self(a: Dictionary, k: Dictionary) -> void:
	self_done = k.id
	match k.get("effect", ""):
		"surge":
			# +3 bonus AP, but never more than 6 AP in a turn; the rest is lost (DOCS).
			a.bonus += maxi(0, mini(3, Rules.AP_CAP - ap_left(a)))
		"heal":
			var before: int = a.hp
			a.hp = mini(a.max_hp, a.hp + Rules.HEAL)
			hud.float_text(a, "+%d" % (a.hp - before), false, true)
		"poison":
			a.poison = true
		"defend":
			a.defending = true


func self_message(id: String) -> String:
	return {"action_surge": "+3 bonus AP this turn. Bonus AP is spent first and lost at the end of the turn.",
		"second_wind": "Healed %d HP. [amount not set; placeholder]" % Rules.HEAL,
		"poison_blade": "Hits this turn poison (+%d damage each; placeholder)." % Rules.POISON_BONUS,
		"defend": "Bracing: %d less damage per hit until your next turn. [placeholder]" % Rules.DEFEND_REDUCTION}.get(id, "")


func _hurt(t: Dictionary, dmg: int) -> void:
	t.hp -= dmg
	if t.hp <= 0 and not t.down:
		t.down = true
		if t == target:
			target = {}
		await board.fall(t.mini)


func end_phase() -> void:
	if busy or phase != "allies":
		return
	var left := allies().filter(func(u): return not u.down and ap_left(u) > 0)
	if left.is_empty():
		_enemy_phase()
	else:
		hud.show_confirm(left)


func confirm_end() -> void:
	hud.hide_confirm()
	_enemy_phase()


func _check_end() -> void:
	if not active:
		return
	var allies_up := units.any(func(u): return u.ally and not u.down)
	var foes_up := units.any(func(u): return not u.ally and not u.down)
	if not foes_up or not allies_up:
		busy = true
		phase = "over"
		refresh()
		await get_tree().create_timer(1.0).timeout
		busy = false
		finished.emit(not foes_up)


# --- The enemies' phase -------------------------------------------------------------

## PLACEHOLDER foe behaviour: each foe walks toward the nearest standing ally and attacks while it has AP.
func _enemy_phase() -> void:
	phase = "enemies"
	busy = true
	target = {}
	ally_target = {}
	result = {}
	refresh()
	await get_tree().create_timer(0.5).timeout
	for e in units.duplicate():
		if e.ally or e.down or not active or phase != "enemies":
			continue
		e.defending = false
		e.ap = Rules.AP
		while e.ap > 0 and active and phase == "enemies":
			var targets := foes_of(e)
			if targets.is_empty():
				break
			targets.sort_custom(func(a, b): return Rules.hex_distance(a.cell, e.cell) < Rules.hex_distance(b.cell, e.cell))
			var t: Dictionary = targets[0]
			if Rules.hex_distance(t.cell, e.cell) == 1:
				e.ap -= 1
				await _attack(e, t, Cards.get_card("attack", "spear"))
				busy = true
			else:
				var path := path_next_to(e, t)
				if path.is_empty():
					break
				e.ap -= 1
				path = path.slice(0, Rules.MOVE_HEXES)
				e.cell = path[-1]
				await board.step_along(e.mini, path)
		await get_tree().create_timer(0.25).timeout
	busy = false
	if active and phase == "enemies":
		_start_allies()


# --- Input --------------------------------------------------------------------------

## Board gestures (Gestures, on the camera rig): a tap acts on a cell; a long-press, or a resting mouse,
## shows a token's details (DOCS: Camera and controls -> Long-press on the board).
func _wire() -> void:
	if _wired:
		return
	_wired = true
	var g := game.rig.gestures
	g.tap.connect(func(pos: Vector2):
		if active:
			game.popup.visible = false
			click_cell(_cell_under(pos)))
	g.long_press.connect(func(pos: Vector2):
		if active:
			_details(pos))
	g.hover.connect(func(pos: Vector2):
		if active:
			_details(pos))


func _cell_under(pos: Vector2) -> Vector2i:
	return cell_at(game.ground_point(pos) - Vector2(position.x, -position.z))


## An enemy's name, HP and what it does; an ally's HP, AP and status.
func _details(pos: Vector2) -> void:
	var u := unit_at(_cell_under(pos))
	if u.is_empty():
		game.popup.visible = false
		return
	var lines := ["HP %d / %d%s" % [maxi(u.hp, 0), u.max_hp, " · down" if u.down else ""]]
	if u.ally:
		lines[0] += " · AP %d%s" % [u.ap, " + %d bonus" % u.bonus if u.bonus > 0 else ""] if phase == "allies" else ""
		var status := []
		if u.defending:
			status.append("Defending")
		if u.blessed:
			status.append("Blessed (+1 coin)")
		if u.poison:
			status.append("Poison Blade")
		lines.append("Status: " + (", ".join(status) if not status.is_empty() else "ready"))
	else:
		# PLACEHOLDER enemy behaviour, as the loop plays it (no enemy AI in the docs yet).
		lines.append("%s %d · spear" % [u.ability, u.score])
		lines.append("Walks to the nearest ally and attacks")
	game.popup.show_at(pos, u.name, lines)
