class_name Fight
extends Node3D
## A small turn-based fight on an approved combat map (CombatMap), or the radius-4 board where a tile has no maps yet
## (design/03 Classes & combat.md -> Turns, AP and health; Combat; Coin checks). The screen and its flow
## follow Combat v14 (mockups/combat/Combat-v14-AllyTargets.dc.html): pick a character in the party tray
## (or on the board), pick a card on the hotbar, tap a target, then press Flip coins / Cast / Use.
## Turns go side by side: all allies act in any order, then all foes. 3 AP each, up to 6 with bonus AP.

signal finished(won: bool)

const PARTY_CELLS := [Vector2i(0, 2), Vector2i(-1, 3), Vector2i(1, 2), Vector2i(0, 3)]   # PLACEHOLDER line-up
const ENEMY_CELLS := [Vector2i(0, -3), Vector2i(1, -3), Vector2i(-1, -2), Vector2i(2, -3)]
const LABELS := ["A", "B", "C", "D", "E", "F", "G", "H"]

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
var grid := {}                   # cell -> {kind, z, way_up}
var map_id := ""                 # the map this fight is on; "" on the old board
var map_tris := 0
var map_build_ms := 0.0
var open_distance := 22.0
var rocks: Array = []
var trees: Array = []
var busy := false
var hud: CombatHud

var _overlays: Array[Node3D] = []
var _hex_mesh: Mesh
var _lifted := {}                # which of a cell's sides lie under steps -> its highlight, lifted over them
var _arrow_mesh: Mesh
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
			["ally_target", "#2E8A47"], ["move", "#D3EBC1"], ["move_tree", "#86B97E"], ["up", "#2E8A47"]]:   # up: PLACEHOLDER
		var m := StandardMaterial3D.new()
		m.albedo_color = Color(k[1])
		m.cull_mode = BaseMaterial3D.CULL_DISABLED
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		_mats[k[0]] = m


## Runs one fight to the end, on map id, or on the old board if it's "". Returns true if the party won.
func run(g: Game, terrain: String, tile: Vector2i, foes: int, id := "") -> bool:
	game = g
	rng = g.rng
	_wire()
	active = true
	units.clear()
	result = {}
	map_id = id
	if id == "":
		_setup_board(terrain, tile, foes)
	else:
		_setup_map(id)
	if hud == null:
		hud = CombatHud.new(self)
		game.safe.add_child(hud)
		game.popup.move_to_front()
	hud.visible = true
	game.rig.focus = Rules.FIGHT_FOCUS
	var view := opening()
	open_distance = view.distance
	game.rig.limits = _pan_limits()
	game.rig.frame(view.target, open_distance * Rules.ZOOM_IN_FROM, 52.0)
	_start_allies()
	game.rig.player_moved = true   # the opening's own: whoever acts first is already in it
	_arrive_camera(view.target)
	var won: bool = await finished
	for u in units:
		if u.ally:
			u.member.hp = maxi(u.hp, 0)
	hud.visible = false
	_clear_overlays()
	game.rig.focus = Vector2(378, 200)
	game.rig.limits = Rect2()
	active = false
	return won


## The camera comes in over the map as the fight fades up, and stays on the opening until a new turn or a pick moves it.
func _arrive_camera(at: Vector3) -> void:
	await game.rig.fly_to(at, open_distance, Rules.ZOOM_SECONDS)
	if game.rig.distance == open_distance:
		game.rig.home = {target = at, distance = open_distance, pitch = 52.0, yaw = 0.0}
		game.rig.player_moved = false


## Where a fight's camera opens (DOCS: starts close on the party and first foes, and players pan to see the rest). Fits whoever acts first,
## then the rest of the party, then foes from the nearest, as far as they fit in the open area between the panels within the distance
## limit. A foe left out means the limit, and draws the view its way as far as what's framed stays in. framed: how many foes made it.
func opening() -> Dictionary:
	var allies := units.filter(func(u): return u.ally and not u.down)
	var from: Vector3 = allies[0].mini.position if not allies.is_empty() else Vector3.ZERO
	var foes := units.filter(func(u): return not u.ally and not u.down)
	foes.sort_custom(func(a, b): return a.mini.position.distance_squared_to(from) < b.mini.position.distance_squared_to(from))
	var box := Rect2(_plan(from), Vector2.ZERO)
	var framed := 0
	var missed = null
	for u: Dictionary in allies + foes:
		var more := box.expand(_plan(u.mini.position))
		if _distance_to_fit(more) <= Rules.FIGHT_DISTANCE_MAX:
			box = more
			framed += 0 if u.ally else 1
		elif missed == null and not u.ally:
			missed = _plan(u.mini.position)
	var d: float = Rules.FIGHT_DISTANCE_MAX if missed != null else clampf(_distance_to_fit(box), Rules.FIGHT_DISTANCE_MIN, Rules.FIGHT_DISTANCE_MAX)
	var half := Vector2(Rules.FIGHT_OPEN.x, Rules.FIGHT_OPEN.y / sin(deg_to_rad(52.0))) * 0.5 * _per_unit() * d
	var cells := _cells_box()
	var want: Vector2 = missed if missed != null else box.get_center()
	if missed == null:   # with room to spare, more of the map and less of what's past it
		want = Vector2(_inside(want.x, cells.position.x + half.x, cells.end.x - half.x), _inside(want.y, cells.position.y + half.y, cells.end.y - half.y))
	var at := Vector2(_inside(want.x, box.end.x + PAD_SIDE - half.x, box.position.x - PAD_SIDE + half.x),
			_inside(want.y, box.end.y + PAD_FAR - half.y, box.position.y - PAD_NEAR + half.y))
	var target: Vector3 = position + Hex.to3(at)
	return {target = target + Vector3(0, from.y, 0), distance = d, framed = framed}


const PAD_SIDE := 0.6    # PLACEHOLDER: room round the framed minis, in metres; the far side for what stands on the far row
const PAD_NEAR := 0.5
const PAD_FAR := 1.2


func _plan(p: Vector3) -> Vector2:
	return Vector2(p.x, -p.z)


func _per_unit() -> float:
	return 2.0 * 0.36 / 844.0   # metres of width per layout unit, per metre of distance


func _distance_to_fit(box: Rect2) -> float:
	var wide := (box.size.x + 2.0 * PAD_SIDE) / (_per_unit() * Rules.FIGHT_OPEN.x)
	var deep := (box.size.y + PAD_NEAR + PAD_FAR) * sin(deg_to_rad(52.0)) / (_per_unit() * Rules.FIGHT_OPEN.y)
	return maxf(wide, deep)


## a held between lo and hi, or their middle if they cross.
func _inside(a: float, lo: float, hi: float) -> float:
	return (lo + hi) * 0.5 if lo > hi else clampf(a, lo, hi)


func _cells_box() -> Rect2:
	var box := Rect2(Hex.cell_position(grid.keys()[0].x, grid.keys()[0].y), Vector2.ZERO)
	for c: Vector2i in grid:
		box = box.expand(Hex.cell_position(c.x, c.y))
	return box


## The world x, z the camera's target can pan within: the map's cells and a little past them.
func _pan_limits() -> Rect2:
	var box := _cells_box().grow(Rules.FIGHT_PAN_MARGIN)
	return Rect2(position.x + box.position.x, position.z - box.end.y, box.size.x, box.size.y)


## The old board, for tiles with no maps yet (tier 0 forest, plains and farmland, and terrains not built). Grows out of the map tile:
## its terrain sets the trees and rocks (PLACEHOLDER counts).
func _setup_board(terrain: String, tile: Vector2i, foes: int) -> void:
	var free: Array = CombatBoard.cells().filter(func(c): return not (c in PARTY_CELLS or c in ENEMY_CELLS))
	var local := RandomNumberGenerator.new()
	local.seed = hash("%d,%d" % [tile.x, tile.y])
	trees = []
	rocks = []
	for k in Rules.BOARD_TREES.get(terrain, 0) + Rules.BOARD_ROCKS.get(terrain, 0):
		var c = free.pop_at(local.randi_range(0, free.size() - 1))
		(trees if k < Rules.BOARD_TREES.get(terrain, 0) else rocks).append(c)
	board.setup(trees, rocks)
	board.heights = {}
	grid = {}
	for c in CombatBoard.cells():
		grid[c] = {kind = "blocked" if c in rocks else "open", z = 0.0, way_up = false}
	for i in game.party.size():
		_add_unit(game.party[i], PARTY_CELLS[i], true, "")
	for i in foes:
		var e: Dictionary = Rules.ENEMY.duplicate()
		e.max_hp = e.hp
		e.name = e.name % LABELS[i]
		_add_unit(e, ENEMY_CELLS[i], false, LABELS[i])


## An approved map. The party takes the sample starts of its stand-ins, anyone else the nearest free cell; every enemy start is
## used, with the one stat line. PLACEHOLDER: start spots beyond the samples, enemy mixes and enemy stats (design/03, 01).
func _setup_map(id: String) -> void:
	var t0 := Time.get_ticks_usec()
	map_tris = board.setup_map(id)
	trees = []
	rocks = []
	grid = CombatMap.grid_of(id)
	board.heights = {}
	for c: Vector2i in grid:
		if grid[c].z != 0.0:
			board.heights[c] = grid[c].z
	var starts: Array = CombatMap.all()[id].starts
	var foes_at := Vector2.ZERO
	var party_at := Vector2.ZERO
	var foe_count := 0
	for st: Dictionary in starts:
		var p := Hex.cell_position(int(st.q), int(st.r))
		if String(st.mini).begins_with("standin_"):
			party_at += p
		else:
			foes_at += p
			foe_count += 1
	foes_at /= maxi(foe_count, 1)
	party_at /= maxi(starts.size() - foe_count, 1)
	var waiting := []
	for m: Dictionary in game.party:
		var at := starts.filter(func(st): return st.mini == m.mini)
		if at.is_empty():
			waiting.append(m)
		else:
			_add_unit(m, Vector2i(int(at[0].q), int(at[0].r)), true, "", foes_at)
	for m: Dictionary in waiting:
		_add_unit(m, _free_near(party_at), true, "", foes_at)
	var n := 0
	for st: Dictionary in starts:
		if not String(st.mini).begins_with("standin_"):
			var e: Dictionary = Rules.ENEMY.duplicate()
			e.max_hp = e.hp
			e.name = e.name % LABELS[n]
			e.mini = st.mini
			_add_unit(e, Vector2i(int(st.q), int(st.r)), false, LABELS[n], party_at, int(st.get("turn", 0)))
			n += 1
	map_build_ms = (Time.get_ticks_usec() - t0) / 1000.0


## The free level cell nearest a point.
func _free_near(p: Vector2) -> Vector2i:
	var best := Vector2i.ZERO
	var d := INF
	for c: Vector2i in grid:
		var far := Hex.cell_position(c.x, c.y).distance_to(p)
		if far < d and _open(c) and grid[c].z == 0.0:
			d = far
			best = c
	return best


## A cell's middle at its height, in the fight's own space.
func cell_point(c: Vector2i) -> Vector3:
	return Hex.to3(Hex.cell_position(c.x, c.y), grid[c].z if grid.has(c) else 0.0)


func _add_unit(m: Dictionary, c: Vector2i, ally: bool, label: String, look_at_plan := Vector2.INF, turn := 0) -> void:
	var facing := Vector2(0, -1) if ally else Vector2(0, 1)
	if look_at_plan != Vector2.INF and look_at_plan != Hex.cell_position(c.x, c.y):   # a base stays lined up with its cell
		facing = Vector2.from_angle(PI / 6.0 + snappedf((look_at_plan - Hex.cell_position(c.x, c.y)).angle() - PI / 6.0, PI / 3.0))
	var mini := board.add_mini(m.mini, c, facing)
	mini.position.y = grid[c].z
	var foot: Array[Vector2i] = []
	if String(m.mini).begins_with("giant_"):
		var pivot := Vector2.ZERO
		var cells := Minis.footprint(m.mini)
		for off: Vector2i in cells:
			var k := CombatMap.turned(off, turn / 60)
			foot.append(k)
			pivot += Hex.cell_position(k.x, k.y)
		pivot /= cells.size()
		mini.set_meta("pivot", pivot)
		mini.rotation.y = deg_to_rad(turn)   # PLACEHOLDER: stays fixed (design/03: turning is open)
		mini.position += Hex.to3(pivot)
	else:
		foot.append(Vector2i.ZERO)
	var u := {foot = foot, name = m.name, initial = m.get("initial", label), color = m.get("color", "#8E3B2E"), mini = mini,
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
	return c.kind in ["attack", "save"] and not foe.down and not foe.ally and dist(u, foe) <= c.get("range", 1)


func ally_in_reach(u: Dictionary, a: Dictionary, c: Dictionary) -> bool:
	return c.kind == "ally" and a.ally and not a.down and dist(u, a) <= c.get("range", 1)


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
		if not (not u.ally and u.down):
			for off: Vector2i in u.foot:
				if u.cell + off == c:
					return u
	return {}


## The cells a unit stands on.
func cells_of(u: Dictionary) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	for off: Vector2i in u.foot:
		out.append(u.cell + off)
	return out


## How far apart two units are, by their nearest cells (design/03 -> Giant enemies: any of a giant's cells can be attacked, and it melees from any).
func dist(a: Dictionary, b: Dictionary) -> int:
	return _dist_from(a, a.cell, b)


func _dist_from(a: Dictionary, at: Vector2i, b: Dictionary) -> int:
	var best := 1 << 20
	for p: Vector2i in a.foot:
		for q: Vector2i in b.foot:
			best = mini(best, Rules.hex_distance(at + p, b.cell + q))
	return best


func _open(c: Vector2i) -> bool:
	return grid.has(c) and grid[c].kind != "blocked" and unit_at(c).is_empty()


## What a step from cell a to its neighbour b costs u, or -1 if it can't (design/03 -> open question on slopes: uphill costs one more,
## a sheer rise needs stairs; a way-up's landing is an ordinary rise). A giant's whole body must fit on free cells at every step;
## PLACEHOLDER: it stays on level ground (design/03: slopes and ways up are open).
func step_cost(u: Dictionary, a: Vector2i, b: Vector2i) -> int:
	if not grid.has(b):
		return -1
	var rise: float = grid[b].z - grid[a].z
	if u.foot.size() > 1:
		for off: Vector2i in u.foot:
			var c: Vector2i = b + off
			if not grid.has(c) or grid[c].kind == "blocked" or grid[c].z != grid[a].z or grid[c].way_up:
				return -1
			var there := unit_at(c)
			if not there.is_empty() and there != u:
				return -1
		return 1
	if not _open(b) or absf(rise) >= Rules.SHEER_RISE:
		return -1
	return 1 + (Rules.UPHILL_COST if rise >= Rules.UPHILL_RISE else 0)


## Cells within one Move of u, with the path to each (DOCS: rocks and minis block, trees don't).
func reachable(u: Dictionary) -> Dictionary:
	var came := _spread(u, Rules.MOVE_HEXES, Callable())
	var out := {}
	for c in came:
		if c != u.cell:
			out[c] = _path_to(u, came, c)
	return out


## The cheapest ways out from u's cell, up to `budget` of movement or until `stop` says a cell will do (`_stop_at` then holds it). Cell -> where from.
var _stop_at = null


func _spread(u: Dictionary, budget: int, stop: Callable) -> Dictionary:
	var came := {u.cell: u.cell}
	var cost := {u.cell: 0}
	var todo: Array = [u.cell]
	_stop_at = null
	while not todo.is_empty():
		var best := 0
		for k in todo.size():
			if cost[todo[k]] < cost[todo[best]]:
				best = k
		var c: Vector2i = todo.pop_at(best)
		if stop.is_valid() and stop.call(c):
			_stop_at = c
			break
		for n in Hex.NEIGHBOURS:
			var m: Vector2i = c + n
			var step := step_cost(u, c, m)
			if step < 0 or cost[c] + step > budget or cost[c] + step >= cost.get(m, 1 << 20):
				continue
			cost[m] = cost[c] + step
			came[m] = c
			if not m in todo:
				todo.append(m)
	return came


func _path_to(u: Dictionary, came: Dictionary, c: Vector2i) -> Array:
	var path: Array = []
	var k: Vector2i = c
	while k != u.cell:
		path.push_front(k)
		k = came[k]
	return path


func path_next_to(u: Dictionary, goal: Dictionary) -> Array:
	var came := _spread(u, 1 << 19, func(c: Vector2i): return _dist_from(u, c, goal) == 1)
	return [] if _stop_at == null else _path_to(u, came, _stop_at)


## As much of a path as one Move pays for.
func _one_move(u: Dictionary, path: Array) -> Array:
	var out := []
	var at: Vector2i = u.cell
	var left := Rules.MOVE_HEXES
	for c: Vector2i in path:
		left -= step_cost(u, at, c)
		if left < 0:
			break
		out.append(c)
		at = c
	return out


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
	mi.mesh = _disc_mesh if disc else _lifted_mesh(c)
	mi.material_override = _mats[mat]
	var z: float = grid[c].z if grid.has(c) else 0.0
	mi.position = Hex.to3(Hex.cell_position(c.x, c.y), z + (Rules.CELL_TOP if map_id != "" else 0.0) + (0.004 if not disc else 0.012))
	board.add_child(mi)
	_overlays.append(mi)


## A cell's highlight, climbing over the treads of any way up beside it (art/handoff/combat_forest_kit.md -> Ways up in the engine).
func _lifted_mesh(c: Vector2i) -> Mesh:
	var mask := 0
	for i in 6:
		var n: Vector2i = c + Hex.NEIGHBOURS[i]
		if grid.has(n) and grid.has(c) and grid[n].way_up and grid[n].z > grid[c].z:
			mask |= 1 << i
	if mask == 0:
		return _hex_mesh
	if not _lifted.has(mask):
		var corners := Hex.hex_corners(Hex.CELL_RADIUS * 0.94, false)
		var height := func(p: Vector2) -> float:
			var h := 0.02
			for i in 6:
				if mask & (1 << i):
					var out := Hex.cell_position(Hex.NEIGHBOURS[i].x, Hex.NEIGHBOURS[i].y).normalized()
					h = maxf(h, Rules.STEPS_HIGH * (1.0 - (0.5 - p.dot(out)) / Rules.STEPS_REACH))
			return h
		var verts := PackedVector3Array()
		var rings := 5
		for k in 6:
			var a: Vector2 = corners[k]
			var b: Vector2 = corners[(k + 1) % 6]
			for ring in rings:
				var i0 := float(ring) / rings
				var i1 := float(ring + 1) / rings
				for tri: Array in [[a * i0, a * i1, b * i1], [a * i0, b * i1, b * i0]]:
					for p: Vector2 in tri:
						verts.append(Hex.to3(p, height.call(p)))
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = verts
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		_lifted[mask] = mesh
	return _lifted[mask]


## A small arrow over a cell a Move goes up to, as the steps run every way and don't show it. PLACEHOLDER look.
func _up_arrow(c: Vector2i) -> void:
	if _arrow_mesh == null:
		var verts := PackedVector3Array()
		var tip := Vector3(0, 0.26, 0)
		for k in 3:
			var a := Vector2.from_angle(k * TAU / 3.0) * 0.14
			var b := Vector2.from_angle((k + 1) * TAU / 3.0) * 0.14
			verts.append_array(PackedVector3Array([Hex.to3(a), tip, Hex.to3(b)]))
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = verts
		_arrow_mesh = ArrayMesh.new()
		(_arrow_mesh as ArrayMesh).add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var mi := MeshInstance3D.new()
	mi.mesh = _arrow_mesh
	mi.material_override = _mats.up
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.position = cell_point(c) + Vector3(0, 0.12, 0)
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
			if grid[cell].z - grid[current.cell].z >= Rules.UPHILL_RISE:
				_up_arrow(cell)
	_overlay(current.cell, "active")
	for u in units:
		if in_reach(current, u, c):
			for cell in cells_of(u):
				_overlay(cell, "target" if u == target else "reach")
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
				sub = "Damage: %d [placeholder]" % dmg if hit else ""}   # the coins show the heads
		hud.refresh()
	await board.attack(a.mini, t.mini, hit)
	hud.float_text(t, "-%d" % dmg if hit else "Miss", hit)
	if hit:
		await _hurt(t, dmg)
	busy = false
	_check_end()


func _flanked(a: Dictionary, t: Dictionary) -> bool:
	for u in units:
		if u != a and u.ally == a.ally and not u.down and dist(u, t) == 1:
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
			sub = "Damage: %d [placeholder]" % dmg}   # the coins show the heads
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
		result = {coins = [], title = "Healed", good = true, sub = ""}   # no message: the HP bar shows it
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
			targets.sort_custom(func(a, b): return dist(a, e) < dist(b, e))
			var t: Dictionary = targets[0]
			if dist(t, e) == 1:
				e.ap -= 1
				await _attack(e, t, Cards.get_card("attack", "spear"))
				busy = true
			else:
				var path := _one_move(e, path_next_to(e, t))
				if path.is_empty():
					break
				e.ap -= 1
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


## The cell under a screen point: raised ground stands in the way of what's behind it, so its heights go first.
func _cell_under(pos: Vector2) -> Vector2i:
	var cam := game.rig.camera
	var o := cam.project_ray_origin(pos)
	var d := cam.project_ray_normal(pos)
	if absf(d.y) < 1e-4:
		return Vector2i(1 << 20, 0)
	var levels := {0.0: true}
	for c: Vector2i in board.heights:
		levels[board.heights[c]] = true
	var heights := levels.keys()
	heights.sort()
	heights.reverse()
	for z: float in heights:
		var p := o + d * ((z - o.y) / d.y)
		var c := cell_at(Vector2(p.x - position.x, -p.z + position.z))
		if grid.has(c) and grid[c].z == z:
			return c
	var p := o + d * (-o.y / d.y)
	return cell_at(Vector2(p.x - position.x, -p.z + position.z))


## A unit's effects for its portrait, as [name, what it does] pairs: the states the loop tracks. PLACEHOLDER
## numbers, as in _attack; the docs' injuries and other conditions aren't modelled.
func effects(u: Dictionary) -> Array:
	var fx := []
	if u.down:
		fx.append(["Down", "0 HP, can't act"])
	if u.defending:
		fx.append(["Defending", "takes %d less damage until their next turn" % Rules.DEFEND_REDUCTION])
	if u.blessed:
		fx.append(["Blessed", "+1 coin on their next attack"])
	if u.poison:
		fx.append(["Poison Blade", "hits this turn deal +%d damage" % Rules.POISON_BONUS])
	return fx


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
