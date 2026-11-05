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
var treads := {}                 # cell -> [mask of neighbours, height]: a hills map's long steps (CombatMap.treads_of)
var roster: Array = []           # who this fight is against (Foes.roster); empty: the checks' one stat line, as many as the map or the board has
var map_id := ""                 # the map this fight is on; "" on the old board
var map_tris := 0
var map_build_ms := 0.0
var open_distance := 22.0
var rocks: Array = []
var trees: Array = []
var busy := false
var hud: CombatHud
var phase_no := 0                # counts phases (allies, enemies, allies ...): riders last until the end of a given one
var breath_dir := -1             # Breath Weapon's aim: which of Hex.NEIGHBOURS, or -1
var cell_target = null           # Glimmerstep's empty hex, or null
var cover := {}                  # cell -> "partial" or "full" (design/03 -> Combat -> Cover); missing: none

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
			["ally_target", "#2E8A47"], ["move", "#D3EBC1"], ["move_lava", "#F2B27A"], ["move_tree", "#86B97E"], ["up", "#2E8A47"]]:   # up: PLACEHOLDER
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
	await get_tree().process_frame   # the panels' places, for the framing
	var view := opening()
	game.rig.focus = open_area().get_center()
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
	var box := Rect2(_plan(from, from.y), Vector2.ZERO)
	var framed := 0
	var missed = null
	for u: Dictionary in allies + foes:
		var more := box.expand(_plan(u.mini.position, from.y))
		if _distance_to_fit(more) <= Rules.FIGHT_DISTANCE_MAX:
			box = more
			framed += 0 if u.ally else 1
		elif missed == null and not u.ally:
			missed = _plan(u.mini.position, from.y)
	var d: float = Rules.FIGHT_DISTANCE_MAX if missed != null else clampf(_distance_to_fit(box), Rules.FIGHT_DISTANCE_MIN, Rules.FIGHT_DISTANCE_MAX)
	var open := open_area()
	var half := Vector2(open.size.x, open.size.y / sin(deg_to_rad(52.0))) * 0.5 * _per_unit() * d
	var cells := _cells_box()
	var want: Vector2 = missed if missed != null else box.get_center()
	if missed == null:   # with room to spare, more of the map and less of what's past it
		want = Vector2(_inside(want.x, cells.position.x + half.x, cells.end.x - half.x), _inside(want.y, cells.position.y + half.y, cells.end.y - half.y))
	var at := Vector2(_inside(want.x, box.end.x + PAD_SIDE - half.x, box.position.x - PAD_SIDE + half.x),
			_inside(want.y, box.end.y + PAD_FAR - half.y, box.position.y - PAD_NEAR + half.y))
	var target: Vector3 = position + Hex.to3(at)
	return {target = target + Vector3(0, from.y, 0), distance = d, framed = framed}


const PAD_SIDE := 1.0    # PLACEHOLDER: room round the framed minis, in metres; the far side for what stands on the far row
const PAD_NEAR := 0.5
const PAD_FAR := 1.2


## The open area between the panels, in the camera's 844-wide layout. Its size and middle set the framing.
func open_area() -> Rect2:
	if hud == null or not hud.is_inside_tree():
		return Rect2(145, 5, 510, 280)
	var r: Rect2 = hud.open_rect()
	var k := 844.0 / game.get_viewport().get_visible_rect().size.x
	return Rect2(r.position * k, r.size * k)


## Where p shows on the opening's ground plane at height y: higher things look further up the screen at this tilt.
func _plan(p: Vector3, y: float) -> Vector2:
	return Vector2(p.x, -p.z + (p.y - y) / tan(deg_to_rad(52.0)))


func _per_unit() -> float:
	return 2.0 * 0.36 / 844.0   # metres of width per layout unit, per metre of distance


func _distance_to_fit(box: Rect2) -> float:
	var open := open_area()
	var wide := (box.size.x + 2.0 * PAD_SIDE) / (_per_unit() * open.size.x)
	var deep := (box.size.y + PAD_NEAR + PAD_FAR) * sin(deg_to_rad(52.0)) / (_per_unit() * open.size.y)
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
	treads = {}
	grid = {}
	cover = {}
	for c in CombatBoard.cells():
		grid[c] = {kind = "blocked" if c in rocks else "open", z = 0.0, way_up = false}
		if c in rocks or c in trees:
			cover[c] = "full" if c in rocks else "partial"
	for i in game.party.size():
		_add_unit(game.party[i], PARTY_CELLS[i], true, "")
	for i in (roster.size() if not roster.is_empty() else foes):
		_add_unit(_foe(i), ENEMY_CELLS[i], false, LABELS[i])


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
	treads = CombatMap.treads_of(id, grid)
	_cover_of_map(id)
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
		_add_unit(m, _free_near(party_at, units[0] if not units.is_empty() else {}), true, "", foes_at)
	if roster.is_empty():
		var n := 0
		for st: Dictionary in starts:
			if not String(st.mini).begins_with("standin_"):
				var e := _foe(n)
				e.mini = st.mini
				_add_unit(e, Vector2i(int(st.q), int(st.r)), false, LABELS[n], party_at, int(st.get("turn", 0)))
				n += 1
	else:
		var slots := starts.filter(func(st): return not String(st.mini).begins_with("standin_") and not String(st.mini).begins_with("giant_"))
		for k in roster.size():
			var at := Vector2i(int(slots[k].q), int(slots[k].r)) if k < slots.size() else _free_near(foes_at, {})
			_add_unit(_foe(k), at, false, LABELS[k], party_at)
	map_build_ms = (Time.get_ticks_usec() - t0) / 1000.0


func _foe(k: int) -> Dictionary:
	var e: Dictionary = roster[k].duplicate() if k < roster.size() else Rules.ENEMY.duplicate()
	e.max_hp = e.hp
	e.name = e.name % LABELS[k]
	return e


## The free cell nearest a point that the first of the party can walk to, so a hillside's cliff doesn't cut anyone off. Never lava.
func _free_near(p: Vector2, first: Dictionary) -> Vector2i:
	var best := Vector2i.ZERO
	var d := INF
	var reach: Dictionary = _spread(first, 1 << 19, Callable()) if not first.is_empty() else grid
	for c: Vector2i in reach:
		var far := Hex.cell_position(c.x, c.y).distance_to(p)
		if far < d and _open(c) and grid[c].kind != "lava":
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
			cell = c, hp = m.hp, max_hp = m.max_hp, score = m.score if m.has("score") else Races.score(m, m.ability), ability = m.ability, ally = ally,
			down = m.hp <= 0, ap = 0, bonus = 0, defending = false, used = {}, used_fight = {},
			blessed = false, poison = false, weapon = m.get("weapon", "spear"),
			hot = m.get("hot", []), cards = m.get("cards", []), member = m, damage = m.get("damage", -1), heads = m.get("heads", Rules.HEADS_TO_HIT), role = m.get("role", ""),
			parry = false, ward = 0, lost_ap = 0, sub = m.get("sub", ""),
			glow = -1, slowed = -1, acid = -1, poison_turns = 0, bleed_turns = 0, lull = false, lockdown = false}
	units.append(u)
	if u.down:
		mini.get_node("body").quaternion = Quaternion(Vector3.RIGHT, deg_to_rad(-80))


func allies() -> Array:
	return units.filter(func(u): return u.ally)


func foes_of(u: Dictionary) -> Array:
	return units.filter(func(o): return o.ally != u.ally and not o.down)


func card(id := "") -> Dictionary:
	return Cards.get_card(sel if id == "" else id, current.get("weapon", ""), current.get("sub", ""))


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
	if c.get("effect", "") == "item" and game.potions <= 0:
		return "No consumable equipped"
	return ""


func in_reach(u: Dictionary, foe: Dictionary, c: Dictionary) -> bool:
	return c.kind in ["attack", "save"] and not foe.down and not foe.ally and dist(u, foe) <= c.get("range", 1) and cover_between(u, foe) != "full"


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
			if not grid.has(c) or grid[c].kind in ["blocked", "lava"] or grid[c].z != grid[a].z or grid[c].way_up:
				return -1
			var there := unit_at(c)
			if not there.is_empty() and there != u:
				return -1
		return 1
	if not _open(b) or absf(rise) >= Rules.SHEER_RISE - Rules.HEIGHT_SLACK:
		return -1
	return 1 + (Rules.UPHILL_COST if rise >= Rules.UPHILL_RISE - Rules.HEIGHT_SLACK else 0)


## Cells within one Move of u, with the path to each (DOCS: rocks and minis block, trees don't).
func reachable(u: Dictionary) -> Dictionary:
	if u.lockdown:
		return {}
	var came := _spread(u, move_hexes(u), Callable())
	var out := {}
	for c in came:
		if c != u.cell:
			out[c] = _path_to(u, came, c)
	return out


## The cheapest ways out from u's cell, up to `budget` of movement or until `stop` says a cell will do (`_stop_at` then holds it). Cell -> where from.
## Of ways that cost the same, the one through the least lava (a hundredth of a move a cell, which never changes what a budget reaches).
var _stop_at = null


func _spread(u: Dictionary, budget: int, stop: Callable) -> Dictionary:
	var came := {u.cell: u.cell}
	var cost := {u.cell: 0.0}
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
			if step < 0:
				continue
			var total: float = cost[c] + step + (0.01 if grid[m].kind == "lava" else 0.0)
			if floorf(total) > budget or total >= cost.get(m, 1 << 20):
				continue
			cost[m] = total
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


## Hexes one Move goes: a wood elf one more, a slowed one (white breath) one fewer (design/03 -> Races; 06 -> First playable -> Races).
func move_hexes(u: Dictionary) -> int:
	if u.lockdown:
		return 0
	return maxi(Rules.MOVE_HEXES + Races.move_bonus(u.member) - (1 if on(u, "slowed") else 0), 1)


## Whether a rider that lasts until the end of a phase is on now.
func on(u: Dictionary, key: String) -> bool:
	return u[key] >= phase_no


## As much of a path as one Move pays for.
func _one_move(u: Dictionary, path: Array) -> Array:
	var out := []
	var at: Vector2i = u.cell
	var left := move_hexes(u)
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
	var high := Rules.STEPS_HIGH
	var reach := Rules.STEPS_REACH
	for i in 6:
		var n: Vector2i = c + Hex.NEIGHBOURS[i]
		if grid.has(n) and grid.has(c) and grid[n].way_up and grid[n].z > grid[c].z:
			mask |= 1 << i
	if treads.has(c):
		mask = treads[c][0]
		high = treads[c][1] * 1.4
		reach = Rules.LIFT_REACH
	if mask == 0:
		return _hex_mesh
	var key := mask + (roundi(high * 100.0) << 8)
	if not _lifted.has(key):
		var corners := Hex.hex_corners(Hex.CELL_RADIUS * 0.94, false)
		var height := func(p: Vector2) -> float:
			var h := 0.02
			for i in 6:
				if mask & (1 << i):
					var out := Hex.cell_position(Hex.NEIGHBOURS[i].x, Hex.NEIGHBOURS[i].y).normalized()
					h = maxf(h, high * (1.0 - (0.5 - p.dot(out)) / reach))
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
		_lifted[key] = mesh
	return _lifted[key]


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
			_overlay(cell, "move_lava" if grid[cell].kind == "lava" else "move_tree" if cell in trees else "move")
			if grid[cell].z - grid[current.cell].z >= Rules.UPHILL_RISE - Rules.HEIGHT_SLACK:
				_up_arrow(cell)
	if c.kind == "breath" and not busy:
		for d in Hex.NEIGHBOURS.size():   # the 6 directions, lit; the aimed line turns orange
			var next: Vector2i = current.cell + Hex.NEIGHBOURS[d]
			if grid.has(next) and d != breath_dir:
				_overlay(next, "reach")
		if breath_dir >= 0:
			for cell in breath_line(current, breath_dir):
				_overlay(cell, "target")
	if c.kind == "cell" and not busy:
		for cell in blink_cells(current):
			_overlay(cell, "target" if cell == cell_target else "move")
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
	phase_no += 1
	for u in units:
		if u.ally:
			u.lockdown = false   # Lockdown lasts until your next turn
			u.ap = 0 if u.down else Rules.AP
			u.bonus = 0
			u.used = {}
			u.defending = false      # Defend lasts until your next turn
			u.parry = false
			u.ward = 0
			u.poison = false
	for u in units.duplicate():
		if u.ally and not u.down:
			await _turn_starts(u)
	_check_end()
	if not active or phase != "allies":
		return
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
	breath_dir = -1
	cell_target = null
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
	breath_dir = -1
	cell_target = null
	moved = 0
	if not target.is_empty() and not in_reach(current, target, card()):
		target = {}
	refresh()


func click_cell(c: Vector2i) -> void:
	if busy or phase != "allies" or current.is_empty():
		return
	var u := unit_at(c)
	var k := card()
	if k.kind == "breath" and Hex.NEIGHBOURS.has(c - current.cell):
		breath_dir = Hex.NEIGHBOURS.find(c - current.cell)
		self_done = ""
		refresh()
		return
	if k.kind == "cell" and c in blink_cells(current):
		cell_target = c
		self_done = ""
		refresh()
		return
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
	moved = path.size()
	await _walk(u, path)
	if not game.rig.player_moved and not u.down:
		game.rig.ease_to(global_position + u.mini.position, game.rig.distance, game.rig.yaw_deg)
	busy = false
	refresh()
	if u.down:
		_check_end()
		if active and phase == "allies":
			for a: Dictionary in units:
				if a.ally and not a.down:
					select(a)
					break


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
		"breath":
			if breath_dir < 0:
				return
			_pay(current, k)
			await _breath(current, breath_dir)
		"cell":
			if cell_target == null:
				return
			_pay(current, k)
			await _blink(current, cell_target)
	if active:
		refresh()


## The score an attack flips: a racial card's own (Stone Throw STR, Claw Swipe DEX, Scorch CHA), else the weapon's or the
## caster's (DOCS: design/06 -> First playable -> Races: scores drive play). A foe's one stat line.
func attack_score(a: Dictionary, k: Dictionary) -> int:
	return Races.score(a.member, k.get("ab", a.ability)) if a.ally else a.score


## An attack's coins: the score, Bless, the forge dwarf's coin on Attack and weapon cards, a glowing (Faerie Fire) or
## acid-burned (black breath) target, less cover (design/03 -> Combat -> Cover). May go below the heads needed: the long shot.
func attack_coins(a: Dictionary, t: Dictionary, k: Dictionary) -> int:
	var n: int = attack_score(a, k) + (1 if a.blessed else 0)
	if a.ally:
		n += Races.forge_coin(a.member, k)
	if not t.is_empty():
		n += (1 if on(t, "glow") else 0) + (1 if on(t, "acid") else 0)
		if cover_between(a, t) == "partial":
			n -= Rules.COVER_COINS
	return maxi(n, 0)


## A save's coins: a foe's set number, an ally's own score in the save's ability, +1 behind cover from whoever aims.
func save_coins(t: Dictionary, from: Dictionary, ability: String, cover_seen := false) -> int:
	var n: int = Races.score(t.member, ability) if t.ally else Rules.ENEMY_SAVE_COINS
	if cover_seen or (not from.is_empty() and cover_between(from, t) == "partial"):
		n += Rules.COVER_COINS
	return n


## A flip of n coins needing `need` heads, as coins and the heads they need. Fewer coins than heads: the long shot (DOCS:
## design/03 -> Coin checks -> The long shot), 1 coin needing heads in a row as many times as the target plus the coins
## short, shown as that many coins that all need heads.
func flip_check(n: int, need: int) -> Dictionary:
	if n >= need:
		return {coins = Coins.flip(rng, n), need = need}
	var times := need + (need - n)
	return {coins = Coins.flip(rng, times), need = times}


## Lucky (DOCS: design/03 -> Races -> Halfling): before anything else reads the flip, a halfling with a charge left reflips
## one coin that went against them, only when that one reflip could change the result: one of their own tails on a miss
## by 1 heads, or one of a foe's heads when it hits them with exactly the heads it needs. Shown with the clover over the
## halfling, and the coin flipped again over whoever flipped.
func lucky(who: Dictionary, flipper: Dictionary, coins: Array[bool], need: int) -> Array[bool]:
	if who.is_empty() or not who.ally or int(who.member.get("lucky", 0)) <= 0:
		return coins
	var heads := Coins.heads(coins)
	var own: bool = who == flipper
	var at := -1
	if own and heads == need - 1:
		at = coins.find(false)
	elif not own and heads == need:
		at = coins.rfind(true)
	if at < 0:
		return coins
	who.member.lucky -= 1
	var out := coins.duplicate()
	out[at] = Coins.flip(rng, 1)[0]
	hud.float_icon(who, "clover")
	await hud.flip_coins(flipper, [out[at]] as Array[bool], 1, Rules.COIN_STEP)
	return out


## Weapon attacks and attack spells flip the attacker's coins to hit (DOCS). Damage: a racial card's set amount, else the
## score (PLACEHOLDER: +2 for Sneak Attack on a flanked foe; +1 per hit under Poison Blade; -1 if the target defends), less a
## metal golem's reduction.
func _attack(a: Dictionary, t: Dictionary, k: Dictionary) -> void:
	busy = true
	refresh()
	var check := flip_check(attack_coins(a, t, k), heads_needed(t))
	a.blessed = false
	var need: int = check.need
	var shown: Array[bool] = await hud.flip_coins(a, check.coins, need, Rules.COIN_STEP if a.ally else Rules.COIN_STEP_FOE)
	var coins: Array[bool] = await lucky(a if a.ally else t, a, check.coins, need)
	if coins != check.coins:
		shown = coins
	var hit: bool = Coins.heads(coins) >= need
	var dmg := 0
	if hit:
		dmg = k.dmg if k.has("dmg") else (a.damage if a.damage >= 0 else attack_score(a, k) + k.get("bonus", 0))
		if k.get("effect", "") == "sneak" and _flanked(a, t):
			dmg += Rules.SNEAK_BONUS
		if a.poison:
			dmg += Rules.POISON_BONUS
		if t.defending:
			dmg -= Rules.DEFEND_REDUCTION
		dmg -= reduction(t)
		if t.parry and k.get("range", 1) <= 1:   # the next melee hit (DOCS: design/04 -> Longsword)
			t.parry = false
			dmg = 0
		var warded := mini(t.ward, maxi(dmg, 0))
		t.ward -= warded
		dmg = maxi(dmg - warded, 0)
		match k.get("rider", ""):
			"stun":
				t.lost_ap = Rules.AP
			"prone":
				t.lost_ap = maxi(t.lost_ap, Rules.PRONE_AP)
			"bleed":
				t.bleed_turns = Rules.DOT_TURNS
	if a.ally:
		result = {coins = shown, title = "Hit!" if hit else "Miss", good = hit,
				sub = "Damage: %d [placeholder]" % dmg if hit else ""}   # the coins show the heads
		hud.refresh()
	await board.attack(a.mini, t.mini, hit)
	hud.float_text(t, "-%d" % dmg if hit else "Miss", hit)
	if hit:
		await _hurt(t, dmg)
	busy = false
	_check_end()


## A metal golem's damage reduction on hits and Breath Weapon, doubled under Lockdown (design/03 -> Races).
func reduction(t: Dictionary) -> int:
	if not t.ally:
		return 0
	return Races.reduction(t.member, game.level) * (2 if t.lockdown else 1)


## What an attack on t needs (DOCS: design/03 -> Hit chance scaling).
func heads_needed(t: Dictionary) -> int:
	return t.get("heads", Rules.HEADS_TO_HIT)


func _flanked(a: Dictionary, t: Dictionary) -> bool:
	for u in units:
		if u != a and u.ally == a.ally and not u.down and dist(u, t) == 1:
			return true
	return false


## When a rider put on t now ends: at the end of t's next turn (design/06 -> First playable -> Races).
func _until_next_turn_of(t: Dictionary) -> int:
	return phase_no + (2 if t.ally == (phase == "allies") else 1)


## Save spells: the foe flips to save. Sacred Flame: a save halves the damage and ignores riders (DOCS). Faerie Fire and
## Lull: a save means no effect.
func _save_spell(a: Dictionary, t: Dictionary, k: Dictionary) -> void:
	busy = true
	refresh()
	var check := flip_check(save_coins(t, a, k.save), Rules.SAVE_HEADS)
	var coins: Array[bool] = await hud.flip_coins(t, check.coins, check.need, Rules.COIN_STEP_FOE)
	var saved: bool = Coins.heads(check.coins) >= check.need
	match k.get("effect", ""):
		"glow", "lull":
			if not saved and k.effect == "glow":
				t.glow = phase_no + 1   # until the caster's next turn
			elif not saved:
				t.lull = true
			result = {coins = coins, title = "Saved" if saved else "Failed save!", good = not saved, sub = ""}
			hud.refresh()
			await board.attack(a.mini, t.mini, not saved)
		_:
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
	match k.effect:
		"heal", "mend":
			var before: int = t.hp
			var amount: int = Rules.HEAL
			if k.effect == "mend":   # Ember Mend: more below half HP
				amount = Rules.EMBER_MEND_LOW if t.hp * 2 < t.max_hp else Rules.EMBER_MEND
			t.hp = mini(t.max_hp, t.hp + amount)
			result = {coins = [], title = "Healed", good = true, sub = ""}   # no message: the HP bar shows it
			hud.float_text(t, "+%d" % (t.hp - before), false, true)
		"swap":
			await _swap(a, t)
		_:
			t.blessed = true
			result = {coins = [], title = "Blessed", good = true, sub = "%s flips an extra coin on their next check." % t.name}


## Duck Behind: the two change places; lava burns whoever lands on it, as walking in does (Ethan, Nov 5, 2026).
func _swap(a: Dictionary, t: Dictionary) -> void:
	busy = true
	self_done = "duck_behind"
	var from: Vector2i = a.cell
	a.cell = t.cell
	t.cell = from
	refresh()
	board.step_along(t.mini, [t.cell])
	await board.step_along(a.mini, [a.cell])
	for u in [a, t]:
		if _in_lava(u):
			await _burn(u)
	busy = false
	refresh()
	_check_end()


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
		"item":
			game.potions -= 1
			var before: int = a.hp
			a.hp = mini(a.max_hp, a.hp + Rules.POTION_HEAL)
			hud.float_text(a, "+%d" % (a.hp - before), false, true)
		"parry":
			a.parry = true
		"ward":
			a.ward = Rules.WARD_POINTS
		"lockdown":
			a.lockdown = true   # until its next turn
		"guide":
			pass   # DOCS (06): plays, and reveals nothing until hidden foes and traps exist


# --- Racial cards that aim at the ground --------------------------------------------

## Breath Weapon's line from u in direction d: up to 3 hexes (blue 4), stopped by rock, walls and sheer rises; trees,
## fences, hedges, crops and brush let it through (design/03 -> Combat -> Cover).
func breath_line(u: Dictionary, d: int) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	var at: Vector2i = u.cell
	for i in Races.breath_reach(u.member):
		var next: Vector2i = at + Hex.NEIGHBOURS[d]
		if not grid.has(next) or cover.get(next, "") == "full" or absf(grid[next].z - grid[at].z) >= Rules.SHEER_RISE - Rules.HEIGHT_SLACK:
			break
		out.append(next)
		at = next
	return out


## Breath Weapon (design/03 -> Races -> Dragonborn): everyone in the line, allies included, flips a DEX save; a pass halves
## the damage and has no rider. Fluffy's Cat Reflexes: half on a fail, none on a pass. A metal golem's reduction counts.
## Riders until the target's next turn ends: white slows, black acid-burns, green poisons (design/06).
func _breath(a: Dictionary, d: int) -> void:
	busy = true
	self_done = "breath"
	var line := breath_line(a, d)
	breath_dir = -1
	refresh()
	var partial := false
	for c: Vector2i in line:
		var t := unit_at(c)
		if not t.is_empty() and not t.down and t != a:
			var check := flip_check(save_coins(t, {}, "DEX", partial), Rules.SAVE_HEADS)
			await hud.flip_coins(t, check.coins, check.need, Rules.COIN_STEP_FOE)
			var coins: Array[bool] = await lucky(t, t, check.coins, check.need)
			var saved: bool = Coins.heads(coins) >= check.need
			var dmg := Races.breath_damage(a.member, game.level)
			if t.ally and t.member.get("race", "") == "Fluffy":
				dmg = 0 if saved else dmg / 2
			elif saved:
				dmg /= 2
			dmg = maxi(dmg - reduction(t), 0)
			if not saved:
				match a.sub:
					"White":
						t.slowed = _until_next_turn_of(t)
					"Black":
						t.acid = _until_next_turn_of(t)
					"Green":
						t.poison_turns = Rules.DOT_TURNS
			await board.attack(a.mini, t.mini, true)
			hud.float_text(t, "-%d" % dmg, true)
			await _hurt(t, dmg)
		if cover.get(c, "") == "partial":
			partial = true
	busy = false
	refresh()
	_check_end()


## Glimmerstep's landing spots: empty hexes up to 3 away, never lava (design/03 -> Racial spells).
func blink_cells(u: Dictionary) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	for c: Vector2i in grid:
		if c != u.cell and Rules.hex_distance(c, u.cell) <= Rules.GLIMMERSTEP_RANGE and grid[c].kind in ["open", "brush"] and unit_at(c).is_empty():
			out.append(c)
	return out


## Vanish and reappear. PLACEHOLDER look: the mini hides while it slides there.
func _blink(u: Dictionary, c: Vector2i) -> void:
	busy = true
	self_done = "glimmerstep"
	cell_target = null
	u.cell = c
	u.mini.visible = false
	await board.step_along(u.mini, [c])
	u.mini.visible = true
	busy = false
	refresh()


# --- Cover (design/03 -> Combat -> Cover) ---------------------------------------------

## What stands between a and t: "full" if rock, a wall or a sheer rise is in the way, "partial" through a tree, fence,
## hedge, crops or brush, else "none". Cells strictly between, on the straight line from a's cell to t's nearest cell; a
## line along a cell edge is nudged one way. A sheer rise: a cell that stands a sheer rise (0.9 m) above the line between
## the two ends. PLACEHOLDER reading of "sheer rises block fully".
func cover_between(a: Dictionary, t: Dictionary) -> String:
	var to: Vector2i = t.cell
	for c in cells_of(t):
		if Rules.hex_distance(a.cell, c) < Rules.hex_distance(a.cell, to):
			to = c
	var n := Rules.hex_distance(a.cell, to)
	var out := "none"
	var za: float = grid[a.cell].z if grid.has(a.cell) else 0.0
	var zt: float = grid[to].z if grid.has(to) else 0.0
	for i in range(1, n):
		var f := float(i) / n
		var c := _cube_round(Vector3(a.cell.x, a.cell.y, -a.cell.x - a.cell.y).lerp(Vector3(to.x, to.y, -to.x - to.y), f) + Vector3(1e-4, 2e-4, -3e-4))
		var kind: String = cover.get(c, "")
		if kind == "full" or (grid.has(c) and grid[c].z - lerpf(za, zt, f) >= Rules.SHEER_RISE - Rules.HEIGHT_SLACK):
			return "full"
		if kind == "partial":
			out = "partial"
	return out


static func _cube_round(v: Vector3) -> Vector2i:
	var r := Vector3(roundf(v.x), roundf(v.y), roundf(v.z))
	var d := (r - v).abs()
	if d.x > d.y and d.x > d.z:
		r.x = -r.y - r.z
	elif d.y > d.z:
		r.y = -r.x - r.z
	return Vector2i(int(r.x), int(r.y))


## Which cells give cover, from the map's cells and what stands on them. Crops and brush cells, and trees, fences, hedges and
## low props on a cell, give partial cover; anything else that blocks a cell blocks fully (rocks, walls, buildings). DOCS (03,
## Ethan picked option A): which props count as low. Fences and walls drawn as map pieces carry no cells yet, so their
## cells block fully.
const PARTIAL_COVER := ["tree", "grove", "thicket", "roots", "hedge", "fence", "stump", "log", "hay", "crates", "sacks", "baskets",
	"butt", "benches", "graves", "scarecrow", "washing", "well", "fire", "mushrooms", "junk", "goods", "wares", "rugs", "racks",
	"arms", "flags", "banner", "dummy", "quintain", "spirit_pole", "lantern_heap", "herd", "brush"]


func _cover_of_map(id: String) -> void:
	cover = {}
	var data: Dictionary = CombatMap.all()[id]
	for c: Vector2i in grid:
		if grid[c].kind == "brush":
			cover[c] = "partial"
		elif grid[c].kind == "blocked":
			cover[c] = "full"
	for p: Dictionary in data.placements:
		var name := String(p.piece)
		if not name.begins_with("ob_"):
			continue
		var low := PARTIAL_COVER.any(func(w): return name.contains(w))
		var at := cell_at(Vector2(p.x, p.y))
		var foot: Array = Kit.path_data(name).get("footprint", [])
		var cells: Array[Vector2i] = [at]
		for off in foot:
			var k := CombatMap.turned(Vector2i(int(off[0]), int(off[1])), int(p.turn) / 60)
			if not at + k in cells:
				cells.append(at + k)
		for c in cells:
			if grid.has(c) and grid[c].kind == "blocked" and low:
				cover[c] = "partial"


## u walks a path, burning on each lava cell it enters (design/03 -> Lava) and stopping there if that downs it.
func _walk(u: Dictionary, path: Array) -> void:
	u.cell = path[-1]
	refresh()
	if not path.any(func(c): return grid[c].kind == "lava"):
		await board.step_along(u.mini, path)
		return
	for c: Vector2i in path:
		await board.step_along(u.mini, [c])
		if grid[c].kind == "lava":
			await _burn(u)
			if u.down:
				u.cell = c
				return


## Fire from lava. PLACEHOLDER: nobody is immune, and Defend doesn't reduce it (design/03: open).
func _burn(u: Dictionary) -> void:
	hud.float_text(u, "-%d" % Rules.LAVA_DAMAGE, true)
	await _hurt(u, Rules.LAVA_DAMAGE)
	refresh()


func _in_lava(u: Dictionary) -> bool:
	return not u.down and grid.has(u.cell) and grid[u.cell].kind == "lava"


func _hurt(t: Dictionary, dmg: int) -> void:
	if dmg > 0:
		t.lull = false   # any damage wakes it, poison, bleed and lava too (Ethan, Nov 5, 2026)
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


## At the start of a unit's turn: poison and bleed tick (1 damage, for 2 turns), and a wood golem's Regrowth heals.
func _turn_starts(u: Dictionary) -> void:
	for key in ["poison_turns", "bleed_turns"]:
		if u[key] > 0 and not u.down:
			u[key] -= 1
			hud.float_text(u, "-%d" % Rules.DOT_DAMAGE, true)
			await _hurt(u, Rules.DOT_DAMAGE)
	var heal := Races.regrowth(u.member, game.level) if u.ally else 0
	if heal > 0 and not u.down and u.hp < u.max_hp:
		var before: int = u.hp
		u.hp = mini(u.max_hp, u.hp + heal)
		hud.float_text(u, "+%d" % (u.hp - before), false, true)


# --- The enemies' phase -------------------------------------------------------------

## PLACEHOLDER foe behaviour: each foe walks toward the nearest standing ally and attacks while it has AP.
func _enemy_phase() -> void:
	phase = "enemies"
	phase_no += 1
	busy = true
	target = {}
	ally_target = {}
	result = {}
	refresh()
	await get_tree().create_timer(0.5).timeout
	for a in units.duplicate():   # the party's turn ends here
		if a.ally and _in_lava(a):
			await _burn(a)
	_check_end()
	for e in units.duplicate():
		if e.ally or e.down or not active or phase != "enemies":
			continue
		e.defending = false
		e.ap = maxi(Rules.AP - e.lost_ap, 0)   # stunned or prone
		e.lost_ap = 0
		await _turn_starts(e)
		if e.down:
			_check_end()
			continue
		var attacks := 0
		while e.ap > 0 and not e.down and active and phase == "enemies":
			var targets := foes_of(e)
			if targets.is_empty():
				break
			targets.sort_custom(func(a, b): return dist(a, e) < dist(b, e))
			var t: Dictionary = targets[0]
			if dist(t, e) == 1:
				if attacks >= Foes.attacks_per_turn:
					break
				attacks += 1
				e.ap -= 1
				if e.lull:   # Lull: it loses its next attack, and wakes
					e.lull = false
					continue
				await _attack(e, t, Cards.get_card("attack", "spear"))
				busy = true
			else:
				var path := _one_move(e, path_next_to(e, t))
				if path.is_empty():
					break
				e.ap -= 1
				await _walk(e, path)
		if _in_lava(e):
			await _burn(e)
		_check_end()
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
	for s in status_icons(u):
		fx.append([s[1], s[2]])
	return fx


## Race riders and states as icons over the mini (design/07: icons, not words; names only in tooltips). [icon, name, what it does].
## PLACEHOLDER icons.
func status_icons(u: Dictionary) -> Array:
	var out := []
	if on(u, "glow"):
		out.append(["spark", "Glowing", "attacks on it flip 1 extra coin"])
	if u.lull:
		out.append(["moon", "Dozing", "loses its next attack; any damage wakes it"])
	if u.bleed_turns > 0:
		out.append(["drop", "Bleeding", "%d damage at the start of its turn" % Rules.DOT_DAMAGE])
	if u.poison_turns > 0:
		out.append(["skull", "Poisoned", "%d damage at the start of its turn" % Rules.DOT_DAMAGE])
	if on(u, "slowed"):
		out.append(["snow", "Slowed", "1 hex less per Move"])
	if on(u, "acid"):
		out.append(["acid", "Acid-burned", "attacks on it flip 1 extra coin"])
	if u.lockdown:
		out.append(["lock", "Lockdown", "damage reduction doubled; can't move"])
	return out


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
