class_name Fight
extends Node3D
## A small turn-based fight on the encounter tile's radius-4 combat board
## (design/03 Classes & combat.md -> Turns, AP and health; Combat; Coin checks).
## Turns go side by side: all allies act in any order, then all enemies. Every character has 3 AP.
## Basic actions cost 1 AP: Move and Attack repeat, Defend once per turn. The hero also has the
## Ranger's level-1 card Hunter's Mark (1 AP, once per turn, one mark at a time).
## Controls: click a portrait or ally to act with them, pick an action, click a cell or foe; End ends
## the allies' phase.

signal finished(won: bool)

const PARTY_CELLS := [Vector2i(0, 2), Vector2i(-1, 3), Vector2i(1, 2), Vector2i(0, 3)]   # PLACEHOLDER line-up
const ENEMY_CELLS := [Vector2i(0, -3), Vector2i(1, -3), Vector2i(-1, -2), Vector2i(2, -3)]
const ACTIONS := {
	"move": {"label": "Move", "ap": 1, "use": "Repeatable", "text": "Step up to %d hexes. Rocks and other minis block; trees don't." % Rules.MOVE_HEXES},
	"attack": {"label": "Attack", "ap": 1, "use": "Repeatable", "text": "Basic attack on an adjacent foe."},
	"defend": {"label": "Defend", "ap": 1, "use": "Once per turn", "text": "Brace: take %d less damage per hit until your next turn." % Rules.DEFEND_REDUCTION},
	"hunters_mark": {"label": "Hunter's Mark", "ap": 1, "use": "Once per turn", "text": "Mark a foe: it takes %d extra damage from you for the fight. One mark at a time." % Rules.MARK_BONUS},
}

var active := false
var game: Game
var rng: RandomNumberGenerator
var board := CombatBoard.new()
var units: Array[Dictionary] = []
var current: Dictionary = {}
var action := ""
var phase := "Allies"
var rocks: Array = []
var _busy := false
var _log := ""

var ui := CanvasLayer.new()
var phase_label := Label.new()
var end_button := Button.new()
var portraits := VBoxContainer.new()
var hotbar := HBoxContainer.new()
var details := Label.new()
var confirm := PanelContainer.new()
var confirm_text := Label.new()
var _overlays: Array[Node3D] = []
var _hex_mesh: Mesh
var _mat_reach: StandardMaterial3D
var _mat_foe: StandardMaterial3D
var _mat_current: StandardMaterial3D
var _press := Vector2.ZERO
var _press_ms := 0


func _ready() -> void:
	add_child(board)
	var p := Piece.new()
	var hexagon := Hex.hex_corners(Hex.CELL_RADIUS * 0.86, false)
	hexagon.reverse()
	p.flat(hexagon, 0.02, Color.WHITE)
	_hex_mesh = p.mesh()
	_mat_reach = _overlay_mat(Color(0.75, 0.95, 0.6, 0.55))     # PLACEHOLDER UI colours
	_mat_foe = _overlay_mat(Color(1.0, 0.8, 0.2, 0.6))
	_mat_current = _overlay_mat(Color(1.0, 1.0, 1.0, 0.6))
	_build_ui()
	ui.visible = false


static func _overlay_mat(c: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return m


## Runs one fight to the end. Returns true if the party won.
func run(g: Game, terrain: String, tile: Vector2i, foes: int) -> bool:
	game = g
	rng = g.rng
	active = true
	_log = ""
	units.clear()
	# The board grows out of the map tile: its terrain sets the trees and rocks (PLACEHOLDER counts).
	var free: Array = CombatBoard.cells().filter(func(c): return not (c in PARTY_CELLS or c in ENEMY_CELLS))
	var local := RandomNumberGenerator.new()
	local.seed = hash("%d,%d" % [tile.x, tile.y])
	var trees := []
	rocks = []
	for k in Rules.BOARD_TREES.get(terrain, 0) + Rules.BOARD_ROCKS.get(terrain, 0):
		var c = free.pop_at(local.randi_range(0, free.size() - 1))
		(trees if k < Rules.BOARD_TREES.get(terrain, 0) else rocks).append(c)
	board.setup(trees, rocks)
	for i in game.party.size():
		var m: Dictionary = game.party[i]
		_add_unit(m, PARTY_CELLS[i], true)
	for i in foes:
		var e: Dictionary = Rules.ENEMY.duplicate()
		e.max_hp = e.hp
		e.name = "%s %d" % [e.name, i + 1]
		_add_unit(e, ENEMY_CELLS[i], false)
	ui.visible = true
	_start_allies()
	var won: bool = await finished
	# HP carries back to the map.
	for u in units:
		if u.ally:
			u.member.hp = maxi(u.hp, 0)
	ui.visible = false
	_clear_overlays()
	active = false
	return won


func _add_unit(m: Dictionary, c: Vector2i, ally: bool) -> void:
	var mini := board.add_mini(m.mini, c, Vector2(0, -1) if ally else Vector2(0, 1))
	var u := {name = m.name, mini = mini, cell = c, hp = m.hp, max_hp = m.max_hp, score = m.score,
			ability = m.ability, ally = ally, down = m.hp <= 0, ap = 0, defending = false, used = {},
			cards = m.get("cards", []), mark = null, member = m}
	var l := Label3D.new()
	l.font_size = 32
	l.pixel_size = 0.007
	l.outline_size = 10
	l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	l.no_depth_test = true
	l.position = Vector3(0, 1.75, 0)
	l.modulate = Color(0.15, 0.3, 0.1) if ally else Color(0.7, 0.1, 0.05)
	mini.add_child(l)
	u.label = l
	units.append(u)
	if u.down:
		mini.get_node("body").quaternion = Quaternion(Vector3.RIGHT, deg_to_rad(-80))
	_update_label(u)


func _update_label(u: Dictionary) -> void:
	u.label.text = "%s%d/%d" % ["MARKED  " if _is_marked(u) else "", maxi(u.hp, 0), u.max_hp] if not u.down else "down"


func _is_marked(u: Dictionary) -> bool:
	for a in units:
		if a.ally and a.mark == u:
			return true
	return false


# --- UI ----------------------------------------------------------------------

func _build_ui() -> void:
	add_child(ui)
	var theme := Theme.new()
	theme.default_font_size = 17
	theme.set_color("font_color", "Label", Color(0.2, 0.17, 0.13))
	var root := Control.new()
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = theme
	ui.add_child(root)
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

	# Party tray (left): phase and End on top, then a portrait per character with HP and AP.
	var tray := PanelContainer.new()
	tray.position = Vector2(16, 16)
	tray.add_theme_stylebox_override("panel", Game._box(Color(0.55, 0.4, 0.28, 0.95), 10))
	root.add_child(tray)
	var tv := VBoxContainer.new()
	tv.add_theme_constant_override("separation", 8)
	tray.add_child(tv)
	phase_label.add_theme_color_override("font_color", Color(1, 0.97, 0.9))
	tv.add_child(phase_label)
	end_button.text = "End phase"
	end_button.pressed.connect(end_phase)
	tv.add_child(end_button)
	tv.add_child(portraits)

	# Hotbar (bottom).
	hotbar.add_theme_constant_override("separation", 10)
	root.add_child(hotbar)
	hotbar.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM, Control.PRESET_MODE_MINSIZE, 16)
	hotbar.grow_horizontal = Control.GROW_DIRECTION_BOTH
	hotbar.grow_vertical = Control.GROW_DIRECTION_BEGIN

	# Details panel (right).
	var right := PanelContainer.new()
	right.add_theme_stylebox_override("panel", Game._box(Color(0.98, 0.95, 0.88, 0.95), 14))
	root.add_child(right)
	right.set_anchors_preset(Control.PRESET_RIGHT_WIDE)
	right.offset_left = -330
	right.offset_right = -16
	right.offset_top = 16
	right.offset_bottom = -16
	var rv := VBoxContainer.new()
	right.add_child(rv)
	details.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	details.custom_minimum_size.x = 280
	details.add_theme_font_size_override("font_size", 16)
	rv.add_child(details)

	# End phase confirmation when allies still have AP (DOCS: Combat screen).
	confirm.set_anchors_preset(Control.PRESET_CENTER)
	confirm.grow_horizontal = Control.GROW_DIRECTION_BOTH
	confirm.grow_vertical = Control.GROW_DIRECTION_BOTH
	confirm.add_theme_stylebox_override("panel", Game._box(Color(0.98, 0.95, 0.88, 0.97), 18))
	var cv := VBoxContainer.new()
	cv.add_theme_constant_override("separation", 12)
	confirm.add_child(cv)
	confirm_text.add_theme_color_override("font_color", Color(0.2, 0.17, 0.13))
	cv.add_child(confirm_text)
	var cb := HBoxContainer.new()
	cb.alignment = BoxContainer.ALIGNMENT_CENTER
	cb.add_theme_constant_override("separation", 12)
	cv.add_child(cb)
	var keep := Button.new()
	keep.text = "Keep playing"
	keep.pressed.connect(func(): confirm.visible = false)
	cb.add_child(keep)
	var end := Button.new()
	end.text = "End phase"
	end.pressed.connect(func():
		confirm.visible = false
		_enemy_phase())
	cb.add_child(end)
	confirm.visible = false
	root.add_child(confirm)
	confirm.set_anchors_and_offsets_preset(Control.PRESET_CENTER, Control.PRESET_MODE_MINSIZE)


func _refresh() -> void:
	phase_label.text = phase
	end_button.disabled = _busy or phase != "Allies"
	for c in portraits.get_children():
		portraits.remove_child(c)
		c.queue_free()
	for u in units:
		if not u.ally:
			continue
		var b := Button.new()
		var pips := "●".repeat(u.ap) + "○".repeat(maxi(Rules.AP - u.ap, 0))
		b.text = "%s\nHP %d/%d   AP %s%s" % [u.name, maxi(u.hp, 0), u.max_hp, pips, "   (down)" if u.down else ""]
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.custom_minimum_size = Vector2(230, 0)
		b.disabled = u.down or _busy or phase != "Allies"
		if u == current:
			b.add_theme_stylebox_override("normal", Game._box(Color(1, 0.93, 0.7), 8))
			b.add_theme_stylebox_override("disabled", Game._box(Color(1, 0.93, 0.7), 8))
			b.add_theme_color_override("font_color", Color(0.2, 0.15, 0.1))
			b.add_theme_color_override("font_disabled_color", Color(0.2, 0.15, 0.1))
		b.pressed.connect(select.bind(u))
		portraits.add_child(b)
	for c in hotbar.get_children():
		hotbar.remove_child(c)
		c.queue_free()
	if not current.is_empty():
		for key in ["move", "attack", "defend"] + Array(current.cards):
			var a: Dictionary = ACTIONS[key]
			var b := Button.new()
			b.text = "%s\n%d AP" % [a.label, a.ap]
			b.custom_minimum_size = Vector2(120, 64)
			b.disabled = _busy or phase != "Allies" or not _can_use(current, key)
			if key == action:
				b.add_theme_stylebox_override("normal", Game._box(Color(1, 0.75, 0.4), 8))
			b.pressed.connect(choose.bind(key))
			hotbar.add_child(b)
	_show_details()
	_show_overlays()


func _show_details() -> void:
	var s := ""
	if not current.is_empty() and action != "":
		var a: Dictionary = ACTIONS[action]
		s += "%s · %d AP · %s\n%s\n" % [a.label, a.ap, a.use, a.text]
		if action == "attack":
			s += "\nFlip: %d coins · %s · needs %d heads\nDamage on a hit: %d%s\n" % [current.score, current.ability,
					Rules.HEADS_TO_HIT, current.score, " (+%d on your mark)" % Rules.MARK_BONUS if current.mark else ""]
		s += "\nPick a target on the board.\n" if action in ["move", "attack", "hunters_mark"] else ""
	elif not current.is_empty():
		s += "%s · %d AP left\nPick an action.\n" % [current.name, current.ap]
	s += "\n" + _log
	details.text = s


func _can_use(u: Dictionary, key: String) -> bool:
	if u.down or u.ap < ACTIONS[key].ap:
		return false
	if ACTIONS[key].use == "Once per turn" and u.used.has(key):
		return false
	return true


func log_line(text: String) -> void:
	_log = text + "\n" + _log
	var lines := _log.split("\n")
	if lines.size() > 14:
		_log = "\n".join(lines.slice(0, 14))


# --- Overlays ----------------------------------------------------------------

func _clear_overlays() -> void:
	for o in _overlays:
		o.queue_free()
	_overlays.clear()


func _overlay(c: Vector2i, mat: Material) -> void:
	var mi := MeshInstance3D.new()
	mi.mesh = _hex_mesh
	mi.material_override = mat
	mi.position = Hex.to3(Hex.cell_position(c.x, c.y), 0.005)
	board.add_child(mi)
	_overlays.append(mi)


func _show_overlays() -> void:
	_clear_overlays()
	if current.is_empty() or phase != "Allies" or _busy:
		return
	_overlay(current.cell, _mat_current)
	if action == "move":
		for c in reachable(current).keys():
			_overlay(c, _mat_reach)
	elif action == "attack":
		for u in foes_of(current):
			if Rules.hex_distance(u.cell, current.cell) == 1:
				_overlay(u.cell, _mat_foe)
	elif action == "hunters_mark":
		for u in foes_of(current):
			_overlay(u.cell, _mat_foe)


# --- Board helpers -------------------------------------------------------------

func unit_at(c: Vector2i) -> Dictionary:
	for u in units:
		if u.cell == c and not (not u.ally and u.down):
			return u
	return {}


func foes_of(u: Dictionary) -> Array:
	return units.filter(func(o): return o.ally != u.ally and not o.down)


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


## Shortest open path from u to any cell next to target (for the foes' moves).
func path_next_to(u: Dictionary, target: Dictionary) -> Array:
	var came := {u.cell: u.cell}
	var todo: Array = [u.cell]
	var end = null
	while not todo.is_empty():
		var c: Vector2i = todo.pop_front()
		if Rules.hex_distance(c, target.cell) == 1:
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


# --- The allies' phase -------------------------------------------------------

func _start_allies() -> void:
	phase = "Allies"
	for u in units:
		if u.ally:
			u.ap = 0 if u.down else Rules.AP
			u.used = {}
			u.defending = false      # Defend lasts until your next turn
	current = {}
	for u in units:
		if u.ally and not u.down:
			current = u
			break
	action = ""
	_refresh()


func select(u: Dictionary) -> void:
	if _busy or u.down or not u.ally or phase != "Allies":
		return
	current = u
	action = ""
	game.rig.ease_to(board.global_position + u.mini.position * 0.5, game.rig.distance, game.rig.yaw_deg)
	_refresh()


func choose(key: String) -> void:
	if _busy or current.is_empty() or not _can_use(current, key):
		return
	action = key
	if key == "defend":
		current.ap -= 1
		current.used["defend"] = true
		current.defending = true
		log_line("%s braces (Defend)." % current.name)
		action = ""
	_refresh()


func click_cell(c: Vector2i) -> void:
	if _busy or phase != "Allies":
		return
	var u := unit_at(c)
	if action == "move" and reachable(current).has(c):
		_busy = true
		current.ap -= 1
		var path: Array = reachable(current)[c]
		_refresh()
		current.cell = c
		await board.step_along(current.mini, path)
		_busy = false
		if current.ap < 1:
			action = ""
		_refresh()
	elif action == "attack" and not u.is_empty() and not u.ally and Rules.hex_distance(c, current.cell) == 1:
		current.ap -= 1
		await _attack(current, u)
		if not active:
			return
		if current.is_empty() or not _can_use(current, "attack"):
			action = ""
		_refresh()
	elif action == "hunters_mark" and not u.is_empty() and not u.ally:
		current.ap -= 1
		current.used["hunters_mark"] = true
		var old = current.mark
		current.mark = u
		if old:
			_update_label(old)
		_update_label(u)
		log_line("%s marks %s (Hunter's Mark)." % [current.name, u.name])
		action = ""
		_refresh()
	elif not u.is_empty() and u.ally:
		select(u)


func end_phase() -> void:
	if _busy or phase != "Allies":
		return
	var left := PackedStringArray()
	for u in units:
		if u.ally and not u.down and u.ap > 0:
			left.append("%s: %d AP" % [u.name, u.ap])
	if left.is_empty():
		_enemy_phase()
	else:
		confirm_text.text = "Some allies still have AP:\n" + "\n".join(left)
		confirm.visible = true


# --- Attacks -------------------------------------------------------------------

## Weapon attacks flip coins to hit (DOCS): coins = the attack's ability score, 1 heads hits.
## PLACEHOLDER: damage = that score, +2 on the attacker's mark, -1 if the target defends.
func _attack(a: Dictionary, t: Dictionary) -> void:
	_busy = true
	_refresh()
	var coins := Coins.flip(rng, a.score)
	var hit := Coins.heads(coins) >= Rules.HEADS_TO_HIT
	var dmg := 0
	if hit:
		dmg = a.score + (Rules.MARK_BONUS if a.mark == t else 0) - (Rules.DEFEND_REDUCTION if t.defending else 0)
		dmg = maxi(dmg, 0)
	log_line("%s attacks %s: %d coins (%s) %s → %s" % [a.name, t.name, a.score, a.ability, Coins.text(coins),
			"hit, %d damage" % dmg if hit else "miss"])
	_show_details()
	await board.attack(a.mini, t.mini, hit)
	_float(t.mini, "-%d" % dmg if hit else "miss", Color(0.8, 0.1, 0.05) if hit else Color(0.3, 0.3, 0.3))
	if hit:
		t.hp -= dmg
		if t.hp <= 0:
			t.down = true
			log_line("%s is down." % t.name)
			await board.fall(t.mini)
	_update_label(t)
	_busy = false
	_check_end()


func _float(mini: Node3D, text: String, col: Color) -> void:
	var l := Label3D.new()
	l.text = text
	l.font_size = 48
	l.pixel_size = 0.007
	l.outline_size = 12
	l.modulate = col
	l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	l.no_depth_test = true
	l.position = mini.position + Vector3(0, 2.1, 0)
	board.add_child(l)
	var tw := create_tween().set_parallel()
	tw.tween_property(l, "position:y", l.position.y + 0.8, 1.0)
	tw.tween_property(l, "modulate:a", 0.0, 1.0).set_delay(0.4)
	tw.chain().tween_callback(l.queue_free)


func _check_end() -> void:
	if not active:
		return
	var allies_up := units.any(func(u): return u.ally and not u.down)
	var foes_up := units.any(func(u): return not u.ally and not u.down)
	if not foes_up or not allies_up:
		_busy = true
		phase = "Victory" if not foes_up else "Defeat"
		current = {}
		_refresh()
		await get_tree().create_timer(1.2).timeout
		_busy = false
		finished.emit(not foes_up)


# --- The enemies' phase ------------------------------------------------------

## PLACEHOLDER foe behaviour: each foe walks toward the nearest standing ally and attacks while it has AP.
func _enemy_phase() -> void:
	phase = "Enemies"
	current = {}
	action = ""
	_busy = true
	_refresh()
	for e in units.duplicate():
		if e.ally or e.down:
			continue
		e.defending = false
		e.ap = Rules.AP
		while e.ap > 0 and active and phase == "Enemies":
			var targets := foes_of(e)
			if targets.is_empty():
				break
			targets.sort_custom(func(a, b): return Rules.hex_distance(a.cell, e.cell) < Rules.hex_distance(b.cell, e.cell))
			var t: Dictionary = targets[0]
			if Rules.hex_distance(t.cell, e.cell) == 1:
				e.ap -= 1
				await _attack(e, t)
				_busy = true
			else:
				var path := path_next_to(e, t)
				if path.is_empty():
					break
				e.ap -= 1
				path = path.slice(0, Rules.MOVE_HEXES)
				e.cell = path[-1]
				await board.step_along(e.mini, path)
		await get_tree().create_timer(0.25).timeout
	_busy = false
	if active and phase == "Enemies":
		_start_allies()


# --- Input -------------------------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if not active:
		return
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_press = event.position
			_press_ms = Time.get_ticks_msec()
		elif event.position.distance_to(_press) < Game.TAP_PIXELS and Time.get_ticks_msec() - _press_ms < Game.TAP_MS:
			click_cell(cell_at(game.ground_point(event.position) - Vector2(position.x, -position.z)))
	elif event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_ESCAPE:
		action = ""
		_refresh()
