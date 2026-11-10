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
const NO_ARMOUR_ARG := "--noarmour"   # test aid: the whole party in Clothes, for the balance comparison
static var NO_ARMOUR: bool = NO_ARMOUR_ARG in OS.get_cmdline_user_args()
var phase_no := 0                # counts phases (allies, enemies, allies ...): riders last until the end of a given one
var breath_dir := -1             # Breath Weapon's aim: which of Hex.NEIGHBOURS, or -1
var cell_target = null           # Glimmerstep's empty hex, or null
var cover := {}                  # cell -> "partial" or "full" (design/03 -> Combat -> Cover); missing: none
var snares := {}                 # owner's name -> the hidden Snare's cell (03 -> Ranger)
var _snare_marks := {}           # owner's name -> its marker, which only the party sees (PLACEHOLDER look)
var edge_cover := {}             # [cell, cell] sorted -> "partial": a low edge between two cells (plot edges, terrace curbs)
var circles := {}                # caster's name -> Warding Circle {cells, node} (03 -> Ritualist)
var night := false               # a night fight: natural night, 1 fewer coin on every attack (03 -> Darkness); no light gear yet

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
			["ally_target", "#2E8A47"], ["move", "#D3EBC1"], ["move_lava", "#F2B27A"], ["move_tree", "#86B97E"], ["up", "#2E8A47"], ["range", "#F4E6BC"]]:   # up, range: PLACEHOLDER
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
	for z: Dictionary in circles.values():
		if is_instance_valid(z.node):
			z.node.queue_free()
	circles = {}
	result = {}
	night = Rules.is_night(g.minute)
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
	if game.party.any(func(m): return Progression.feat(m) == "rallying_presence"):
		for u in allies():   # Rallying Presence: a little temporary HP for every ally (05)
			u.temp = Rules.RALLY_WARD
	var foes_first: bool = game.ambush >= 0 and Ambush.apply(units, game.ambush == 1)   # 03 -> Ambush
	game.ambush = -1
	if foes_first:
		_enemy_phase()
	else:
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
			blessed = false, poison_blade = false, weapon = m.get("weapon", "spear"),
			hot = m.get("hot", []), cards = m.get("cards", []), member = m, damage = m.get("damage", -1), heads = Weapons.defence_heads(m, NO_ARMOUR) if ally else m.get("heads", Rules.HEADS_TO_HIT), role = m.get("role", ""),
			parry = false, ward = 0, lost_ap = 0, sub = m.get("sub", ""),
			glow = -1, slowed = -1, slow_hexes = 0, acid = -1, poison = [], bleed_turns = 0, lull = false, lockdown = false,
			facing = _dir_of(facing), backstabbed = false,
			off = m.get("off", ""),
			snared = -1, unaware = [], ambushed = false, guard = false, guard_counter = false, quick_ready = false, dance_ready = false, mark = {}, disarmed = false,
			summon_of = m.get("summon_of", ""), decoy = m.get("decoy", ""), copy_of = m.get("copy_of", ""), conc = {},
			# levels 2-5 (Progression): Rage, Sidestep, Arcane Shield, Bring It, Raise the Stakes, Flowing Strike, Opening
			# Strike; on foes: taunted by, Holy Brand, Curse of Frailty and of Ruin, drowsy, Exposing Disarm, Marrowbreaker
			rage = -1, sidestep = -1, arcane_shield = false, bring_it = false, stakes = false, flowing = false, opened = false,
			taunt = {}, taunt_until = -1, branded = false, frail = -1, ruin = -1, drowsy = -1, exposed = false, marrow = false,
			taunts = m.get("taunt", false), temp = 0, riposte = false}
	units.append(u)
	if u.down:
		mini.get_node("body").quaternion = Quaternion(Vector3.RIGHT, deg_to_rad(-80))


## The party and its summons; decoys aren't allies (03 -> Deceiver: they don't count for flanking or foes' targets).
func allies() -> Array:
	return units.filter(func(u): return u.ally and u.decoy == "")


## Who u can go for: the other side, standing, never a decoy (foes only go for decoys that fool them: _enemy_phase).
func foes_of(u: Dictionary) -> Array:
	return units.filter(func(o): return o.ally != u.ally and not o.down and o.decoy == "")


static func is_summon(u: Dictionary) -> bool:
	return u.summon_of != ""


func card(id := "") -> Dictionary:
	return Progression.card_for(current.get("member", {}), Cards.get_card(sel if id == "" else id, current.get("weapon", ""), current.get("sub", "")))


# --- Rules for using a card --------------------------------------------------------

func ap_left(u: Dictionary) -> int:
	return u.ap + u.bonus


func spent(u: Dictionary, c: Dictionary) -> bool:
	var uses: int = Progression.card_for(u.get("member", {}), c.duplicate()).get("uses", 1) if u.ally else 1   # Second Wind+ (03)
	return (c.limit == "turn" and u.used.has(c.id)) or (c.limit == "fight" and int(u.used_fight.get(c.id, 0)) >= uses)


## Why u can't use card c right now, or "" (Combat v14's notes under the button).
## What a card costs u now: Quick Slash is free right after a shortsword hit, and moving Hunter's Mark off a downed foe is free (04, 03).
func ap_cost(u: Dictionary, c: Dictionary) -> int:
	if c.id == "quick_slash" and u.quick_ready:
		return 0
	if c.id == "hunters_mark" and not u.mark.is_empty() and u.mark.down:
		return 0
	if u.flowing and c.src == "weapon" and Weapons.of(u.weapon).hands == "f":
		return maxi(c.ap - Rules.FLOWING_LESS, 0)   # Flowing Strike (04)
	return c.ap


func cant_use(u: Dictionary, c: Dictionary) -> String:
	if c.ap < 0:
		return "AP cost not set yet"
	if not c.get("built", true):
		return "Not built yet"   # PLACEHOLDER (Progression: the docs define it, the prototype doesn't have its rule yet)
	if c.get("two_handed", false) and not u.get("off", "") in ["", "none"]:
		return "_two_handed"   # Blademaster cards work only two-handed (04); no note, the card dims
	if c.get("effect", "") == "unbind" and u.conc.get("unit", {}).is_empty():
		return "_no_summon"
	if c.id == "hunters_mark" and not u.mark.is_empty() and u.mark.down and not u.used.has(c.id + "_free"):
		pass   # moving the mark off a downed foe is free, and doesn't count as the turn's use
	elif spent(u, c):
		return "Once per fight: already used" if c.limit == "fight" else "Once per turn: already used"
	if c.id == "dancing_step" and not u.dance_ready:
		return "_scimitar"   # only after a scimitar attack this turn; no note (the card shows it)
	if ap_left(u) < ap_cost(u, c):
		return "Not enough AP"
	if u.hp <= c.get("hp", 0):   # a blood art can't take you to 0 (03 -> Wizard level-1 placeholders)
		return "Not enough HP"
	if c.get("effect", "") == "item" and game.potions <= 0:
		return "No consumable equipped"
	return ""


func in_reach(u: Dictionary, foe: Dictionary, c: Dictionary) -> bool:
	if foe.down or foe.ally:
		return false
	if c.kind == "mark":   # any foe you can see (03)
		return cover_between(u, foe) != "full"
	if c.kind not in ["attack", "save"]:
		return false
	if c.get("effect", "") == "killing" and (u.get("mark", {}) != foe or foe.hp * 2 >= foe.max_hp):
		return false   # Killing Shot: a marked foe below half HP (03)
	if c.has("step") and dist(u, foe) > 1:   # Step and Strike: a free hex next to it within its move
		return not _step_path(u, foe, c.step).is_empty()
	return dist(u, foe) <= c.get("range", 1) and (c.get("pierce", false) or cover_between(u, foe) != "full")


## The way to a free hex next to foe within `budget` of movement, or [].
func _step_path(u: Dictionary, foe: Dictionary, budget: int) -> Array:
	var came := _spread(u, budget, Callable())
	var best: Array = []
	for c: Vector2i in came:
		if c != u.cell and _dist_from(u, c, foe) == 1:
			var path := _path_to(u, came, c)
			if best.is_empty() or path.size() < best.size():
				best = path
	return best


## The hexes a card with a range reaches from u, tinted when it's picked (07 -> Combat): attacks, save spells and ally
## cards; cards that light their own cells (Move, breath, arcs, cells) and cards with no range (self, any visible foe) don't.
func range_cells(u: Dictionary, c: Dictionary) -> Array:
	if busy or not c.kind in ["attack", "save", "ally"]:
		return []
	var reach: int = c.get("range", 1)
	var out := []
	for cell: Vector2i in grid:
		var d := Rules.hex_distance(cell, u.cell)
		if d >= 1 and d <= reach:
			out.append(cell)
	return out


func ally_in_reach(u: Dictionary, a: Dictionary, c: Dictionary) -> bool:
	if c.get("summons_only", false) and a.get("summon_of", "") != u.name:
		return false   # Soul Swap: one of your summons (03)
	return c.kind == "ally" and a.ally and a.decoy == "" and not a.down and dist(u, a) <= c.get("range", 1) and (a != u or c.kind != "ally" or c.get("effect", "") != "swap")


func _pay(u: Dictionary, c: Dictionary) -> void:
	var cost := ap_cost(u, c)
	var free_mark: bool = c.id == "hunters_mark" and cost == 0
	if c.id != "quick_slash":
		u.quick_ready = false   # "right after" a shortsword hit
	var from_bonus := mini(u.bonus, cost)     # bonus AP is spent first (DOCS)
	u.bonus -= from_bonus
	u.ap -= cost - from_bonus
	if c.get("hp", 0) > 0:   # Blood Bolt's HP, paid as it's cast (03)
		u.hp -= c.hp
		hud.float_text(u, "-%d" % c.hp, true)
	if free_mark:
		u.used[c.id + "_free"] = true
		return
	if c.limit == "turn":
		u.used[c.id] = true
	elif c.limit == "fight":
		u.used_fight[c.id] = int(u.used_fight.get(c.id, 0)) + 1   # Second Wind+ twice (03)
	if u.flowing and c.src == "weapon" and Weapons.of(u.weapon).hands == "f" and c.id != "step_strike":
		u.flowing = false   # Flowing Strike's cheaper card is spent


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
	if u.get("member", {}).get("flies", false):   # the Wisp flies (03): over lava and rises alike, never through rock or anyone
		return 1 if _open(b) else -1
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


## Hexes one Move goes: 2, +1 for every DEX point above 1 (allies; foes have no DEX yet), a wood elf one more, less while
## slowed (Frost Ray, Bonebreaker, white breath), never below 0 (design/03 -> Combat, Races; 04; 06 -> First playable -> Races).
func move_hexes(u: Dictionary) -> int:
	if u.lockdown:
		return 0
	var dex: int = Races.score(u.member, "DEX") - 1 if u.ally and not Rules.old("move") else 0
	if on(u, "snared"):
		return 0   # rooted: Snare, Pinning Bolt
	return maxi(Rules.MOVE_HEXES + Rules.MOVE_PER_DEX * dex + Races.move_bonus(u.member) + (Progression.move_bonus(u.member) if u.ally else 0) - (u.slow_hexes if on(u, "slowed") else 0), 0)


## Which of Hex.NEIGHBOURS points most nearly along a plan direction.
static func _dir_of(v: Vector2) -> int:
	var best := 0
	for i in Hex.NEIGHBOURS.size():
		var n: Vector2i = Hex.NEIGHBOURS[i]
		var b: Vector2i = Hex.NEIGHBOURS[best]
		if Hex.cell_position(n.x, n.y).normalized().dot(v.normalized()) > Hex.cell_position(b.x, b.y).normalized().dot(v.normalized()):
			best = i
	return best


## The direction from cell a toward cell b.
static func _dir_toward(a: Vector2i, b: Vector2i) -> int:
	return _dir_of(Hex.cell_position(b.x, b.y) - Hex.cell_position(a.x, a.y))


## Whether a stands in the hex behind t: opposite the way t faces, which is whoever it last moved toward or attacked
## (04 -> Backstab). The minis already turn the same way as they step and strike.
func behind(a: Dictionary, t: Dictionary) -> bool:
	return a.cell == t.cell - Hex.NEIGHBOURS[t.facing]


## A slow until t's next turn ends; the bigger of two at once.
func _slow(t: Dictionary, hexes: int) -> void:
	t.slow_hexes = maxi(hexes, t.slow_hexes if on(t, "slowed") else 0)
	t.slowed = _until_next_turn_of(t)


## Shield Bash: the foe goes 1 hex straight away from the attacker. PLACEHOLDER (told to the planner): if that hex is off the
## board, blocked, taken, a sheer rise away, or the foe is a giant, it stays put; the hit still lands. Lava burns as walking in does.
func _push(a: Dictionary, t: Dictionary, hexes := 1) -> void:
	if t.foot.size() > 1 or t.down or Rules.hex_distance(a.cell, t.cell) != 1:
		return
	var way: Vector2i = t.cell - a.cell
	for _i in hexes:
		var dest: Vector2i = t.cell + way
		if step_cost(t, t.cell, dest) < 0:
			return
		t.cell = dest
		await board.step_along(t.mini, [dest])
		if grid[dest].kind == "lava":
			await _burn(t)
			return


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
	if c.kind == "arc" and not busy:
		for cell: Vector2i in grid:
			var d := Rules.hex_distance(cell, current.cell)
			if d >= 1 and d <= c.range and not cell in arc_cells(current, cell_target if cell_target != null else Vector2i(1 << 20, 0)):
				_overlay(cell, "reach")
		if cell_target != null:
			for cell in arc_cells(current, cell_target):
				_overlay(cell, "target")
	if c.kind == "cell" and not busy:
		var ring: Array = circle_cells(cell_target) if c.get("effect", "") == "circle" and cell_target != null else []
		for cell in cell_options(current, c):
			_overlay(cell, "target" if cell == cell_target or cell in ring else "move")
	_overlay(current.cell, "active")
	var lit := {}
	for u in units:
		if in_reach(current, u, c) or ally_in_reach(current, u, c):
			for cell in cells_of(u):
				lit[cell] = true
	for cell in range_cells(current, c):   # every hex the card reaches (07 -> Combat: range shows on the board, Nov 9, 2026)
		if not lit.has(cell):
			_overlay(cell, "range")
	for u in units:
		if in_reach(current, u, c):
			for cell in cells_of(u):
				_overlay(cell, "target" if u == target else "reach")
		if ally_in_reach(current, u, c):
			_overlay(u.cell, "ally_target" if u == ally_target else "ally", true)


## Faerie Fire's lasting glow follows the units' state (CombatBoard.glow). Only changes are passed on, so the motion that
## starts it isn't undone.
var _looks := {}


func _process(_delta: float) -> void:
	if not active or board == null:
		return
	for u in units:
		if not is_instance_valid(u.mini):
			continue
		var g: bool = on(u, "glow") and not u.down
		if g != _looks.get(u.mini, false):
			board.glow(u.mini, g)
		_looks[u.mini] = g


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
			u.ap = 0 if u.down or u.decoy != "" else (Rules.SUMMON_AP if is_summon(u) else Rules.AP)
			u.bonus = 0
			u.used = {}
			u.defending = false      # Defend lasts until your next turn
			u.parry = false
			u.ward = 0
			u.poison_blade = false
	for u in units.duplicate():
		if u.ally and not u.down and u.decoy == "":
			await _turn_starts(u)
	_check_end()
	if not active or phase != "allies":
		return
	current = {}
	game.rig.player_moved = false   # PLACEHOLDER ("the next action" isn't decided): a new turn centres again
	for u in units:
		if u.ally and not u.down and u.decoy == "":
			select(u)
			break
	refresh()


## Make u the acting character (portrait or token); the camera pans to them (DOCS: Combat screen -> Camera).
func select(u: Dictionary) -> void:
	if busy or u.down or not u.ally or u.decoy != "" or phase != "allies":
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
	if (k.kind == "cell" and c in cell_options(current, k)) or (k.kind == "arc" and Rules.hex_distance(c, current.cell) in range(1, k.range + 1)):
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
var _acting := {}   # the ally whose card is resolving: whoever it hurts notices them (03 -> Ambush)


func press_button() -> void:
	if busy or current.is_empty():
		return
	var k := card()
	if cant_use(current, k) != "":
		return
	_acting = current
	var aimed := target
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
			await _use_self(current, k)
		"breath":
			if breath_dir < 0:
				return
			_pay(current, k)
			await _breath(current, breath_dir)
		"cell":
			if cell_target == null:
				return
			_pay(current, k)
			match k.get("effect", ""):
				"snare":
					_set_snare(current, cell_target)
				"dance":
					await _dance(current, cell_target)
				"summon":
					_summon(current, cell_target, k)
				"circle":
					_circle(current, cell_target)
				"phantom":
					_phantom(current, cell_target)
				_:
					await _blink(current, cell_target)
		"mark":
			if target.is_empty():
				return
			_pay(current, k)
			current.mark = target   # one mark at a time: marking another moves it (03)
			self_done = k.id
			result = {coins = [], title = "Used", good = true, sub = ""}
		"arc":
			if cell_target == null:
				return
			_pay(current, k)
			await _arc(current, cell_target)
	if k.kind in ["attack", "save"] and k.get("effect", "") != "surrender":   # Hunter's Mark is quiet (03 -> Ambush); Fake Surrender is the point
		Ambush.noticed(aimed, _acting)
	_acting = {}
	if active:
		refresh()


## The score an attack flips: a racial card's own (Stone Throw STR, Claw Swipe DEX, Scorch CHA), else the weapon's or the
## caster's (DOCS: design/06 -> First playable -> Races: scores drive play). A foe's one stat line.
func attack_score(a: Dictionary, k: Dictionary) -> int:
	return Races.score(a.member, k.get("ab", a.ability)) if a.ally else a.score


## An attack's coins: the score plus its modifiers (attack_mods). Armour takes no coins (04, Nov 5, 2026). May go below
## the heads needed: the long shot.
func attack_coins(a: Dictionary, t: Dictionary, k: Dictionary) -> int:
	var n: int = attack_score(a, k)
	for m: Dictionary in attack_mods(a, t, k):
		n += m.n
	return maxi(n, 0)


## Every situational modifier on an attack, as coins (DOCS: 03 -> Coin checks -> Readable flips, Ethan, Nov 7, 2026: they
## change coins, never heads), each {n, icon, why}: Bless, the forge dwarf's coin on Attack and weapon cards, a glowing
## (Faerie Fire) or acid-burned (black breath) target, less cover (03 -> Combat -> Cover), a ranged attack with a foe next
## to the attacker, except a crossbow's (Point Blank; 04 -> Ranged), and natural night (03 -> Darkness).
func attack_mods(a: Dictionary, t: Dictionary, k: Dictionary) -> Array:
	var out := []
	if a.blessed:
		out.append({n = 1, icon = "bless", why = "bless"})
	if a.ally and Races.forge_coin(a.member, k) > 0:
		out.append({n = Races.forge_coin(a.member, k), icon = "forge", why = "forge"})
	if a.ally and not a.opened and Progression.feat(a.member) == "opening_strike":
		out.append({n = Rules.OPENING_COINS, icon = "opening", why = "opening"})   # the first attack each fight (05)
	if on(a, "drowsy"):
		out.append({n = -1, icon = "drowsy", why = "drowsy"})   # Sleeping Draught (03)
	if t.is_empty():
		return out
	if on(t, "glow"):
		out.append({n = 1, icon = "glow", why = "glow"})
	if on(t, "acid"):
		out.append({n = 1, icon = "acid", why = "acid"})
	if on(t, "frail"):
		out.append({n = Rules.FRAILTY_COINS, icon = "frail", why = "frail"})   # Curse of Frailty (03)
	if t.disarmed and t.exposed:
		out.append({n = Rules.EXPOSED_COINS, icon = "exposed", why = "exposed"})   # Exposing Disarm (04)
	if not k.get("pierce", false) and cover_between(a, t) == "partial":   # Aimed Shot ignores cover (04)
		out.append({n = -Rules.COVER_COINS, icon = "cover", why = "cover"})
	if close_shot(a, k):
		out.append({n = -Rules.RANGED_ADJACENT, icon = "close", why = "close"})
	if night:
		out.append({n = -Rules.NIGHT_COINS, icon = "night", why = "night"})
	return out


## A ranged attack with a foe next to the attacker (04 -> Ranged), except a crossbow's own attacks (Point Blank).
func close_shot(a: Dictionary, k: Dictionary) -> bool:
	if a.is_empty() or Rules.old("ranged") or not k.get("ranged", false):
		return false
	if Weapons.of(a.weapon).get("point_blank", false) and (k.id == "attack" or k.src == "weapon"):
		return false
	return foes_of(a).any(func(o): return dist(o, a) == 1)


## A save's coins: a foe's set number, or an ally's own score in the save's ability. Saves ignore cover (03 -> Cover,
## Ethan, Nov 7, 2026).
func save_coins(t: Dictionary, ability: String) -> int:
	return Races.score(t.member, ability) if t.ally else Rules.ENEMY_SAVE_COINS


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
## score (PLACEHOLDER: doubled by Sneak Attack on a flanked foe; -1 if the target defends), less a
## metal golem's reduction.
func _attack(a: Dictionary, t: Dictionary, k: Dictionary) -> void:
	busy = true
	refresh()
	if k.has("step") and dist(a, t) > 1:   # Step and Strike: move first, then strike
		await _walk(a, _step_path(a, t, k.step))
	var hit := false
	for shot in k.get("shots", 1):   # Double Shot: two flips at normal damage
		if t.down or a.down:
			break
		hit = await _one_attack(a, t, k) or hit
	if hit and not t.down and not a.down and _offhand_ready(a, k):
		a.used["offhand_hit"] = true   # once a turn (04 -> Dual-wielding)
		var off := offhand_card(a)
		if dist(a, t) <= off.range:
			await _one_attack(a, t, off)
	busy = false
	_check_end()


## Whether a dual-wields (04 -> Dual-wielding): a one-handed weapon in each hand, or fist weapons (worn as a pair).
static func dual_wields(a: Dictionary) -> bool:
	if Weapons.of(a.weapon).hands == "f":
		return true
	return Weapons.CAT.has(a.weapon) and Weapons.of(a.weapon).hands == "1" and Weapons.CAT.has(a.off) and Weapons.of(a.off).hands == "1"


## The free offhand hit is due: once a turn, right after a main-hand hit with any weapon attack (04; Ethan, Nov 6, 2026).
func _offhand_ready(a: Dictionary, k: Dictionary) -> bool:
	return a.ally and dual_wields(a) and weapon_attack(k) and not k.get("offhand", false) and not a.used.has("offhand_hit")


## The offhand's free attack: a basic attack with the offhand weapon (fist weapons: the pair), flipping its own score.
func offhand_card(a: Dictionary) -> Dictionary:
	var w: String = a.weapon if Weapons.of(a.weapon).hands == "f" else a.off
	var k := Cards.get_card("attack", w)
	k.ab = Weapons.of(w).ab
	k.offhand = true
	return k


## One attack flip and its damage; whether it hit.
func _one_attack(a: Dictionary, t: Dictionary, k: Dictionary) -> bool:
	busy = true
	var r := await _attack_flip(a, t, k)
	await board.attack(a.mini, t.mini, r.hit, motion_kind(a, t, k))
	await _attack_land(a, t, k, r.hit, r.dmg)
	busy = false
	_check_end()
	return r.hit


## An attack's flip and its damage and riders, before any motion plays: {hit, dmg}.
func _attack_flip(a: Dictionary, t: Dictionary, k: Dictionary) -> Dictionary:
	var check := flip_check(attack_coins(a, t, k), heads_needed(t, a, k))
	var mods := attack_mods(a, t, k)   # shown as coins in the flip
	var long_shot: bool = attack_coins(a, t, k) < heads_needed(t, a, k)
	a.blessed = false
	var need: int = check.need
	var shown: Array[bool] = await hud.flip_coins(a, check.coins, need, Rules.COIN_STEP if a.ally else Rules.COIN_STEP_FOE,
			mods, long_shot)
	var coins: Array[bool] = await lucky(a if a.ally else t, a, check.coins, need)
	var lucked: bool = coins != check.coins
	if lucked:
		shown = coins
	var hit: bool = Coins.heads(coins) >= need
	var dmg := 0
	if hit:
		dmg = k.dmg if k.has("dmg") else (a.damage if a.damage >= 0 else attack_score(a, k) + k.get("bonus", 0))
		if a.ally and weapon_attack(k) and Weapons.of(a.weapon).hands == "v" and a.off in ["", "none"]:
			dmg += Weapons.VERSATILE_TWO_HANDED   # a versatile weapon held two-handed (04)
		dmg *= k.get("times", 1)   # Aimed Shot 4x, Haymaker 2x (04)
		if a.stakes:
			dmg *= Rules.STAKES_TIMES   # Raise the Stakes (03)
		if k.get("effect", "") == "sneak" and sneak_applies(a, t):   # not on the offhand's free hit (04)
			dmg *= Rules.SNEAK_TIMES   # Sneak Attack doubles the weapon's damage, before the flat bonuses (Backstab, the Mark) (03)
		if k.id == "quick_slash" and a.quick_ready:
			dmg -= Rules.QUICK_SLASH_LESS
		dmg += _level_damage(a, t, k)
		if a.ally and not a.mark.is_empty() and a.mark == t:
			dmg += Rules.MARK_DAMAGE   # Hunter's Mark (03)
		if t.guard:
			dmg -= Rules.GUARD_UP_LESS
		if a.poison_blade and Rules.old("poison"):
			dmg += 1   # test aid: Poison Blade's old +1 a hit
		if not Rules.old("backstab") and a.ally and a.weapon == "dagger" and (k.id in ["attack", "sneak_attack"] or k.src == "weapon") and not k.get("offhand", false) and not a.backstabbed and behind(a, t):
			dmg += Rules.BACKSTAB + (Rules.BACKSTAB_PLUS if Progression.trained(a.member, "backstab_plus") else 0)   # Backstab (04), Backstab+
			a.backstabbed = true
		if t.defending:
			dmg -= Rules.DEFEND_REDUCTION
		dmg -= reduction(t)
		dmg -= _level_reduction(a, t)
		if t.parry and k.get("range", 1) <= 1:   # the next melee hit (DOCS: design/04 -> Longsword)
			t.parry = false
			dmg = 0
			if t.ally and Progression.trained(t.member, "riposte"):
				t.riposte = true   # Riposte: a free counterattack (04), after the motion
		var warded := mini(t.ward, maxi(dmg, 0))
		t.ward -= warded
		dmg = maxi(dmg - warded, 0)
		var held := mini(t.temp, dmg)   # Rallying Presence's temporary HP
		t.temp -= held
		dmg -= held
		match k.get("rider", ""):
			"slow":
				if k.id == "bonebreaker" and a.ally and Progression.trained(a.member, "marrowbreaker") and not t.marrow:
					t.marrow = true   # Marrowbreaker: STR lowered for the fight (04); a foe's one score
					t.score = maxi(t.score - Rules.MARROW_STR, 0)
				if not Rules.old("slows"):
					_slow(t, k.slow)
				elif k.id == "frost_ray":
					t.lost_ap = maxi(t.lost_ap, Rules.PRONE_AP)   # test aid: Frost Ray's old prone
			"prone":
				t.lost_ap = maxi(t.lost_ap, Rules.PRONE_AP)
			"bleed":
				t.bleed_turns = Rules.DOT_TURNS
			"snare":
				t.snared = _until_next_turn_of(t)   # Pinning Bolt roots (04)
			"disarm":
				if holds_weapon(t):   # Disarm: it loses 1 AP next turn recovering it, the larger with Haymaker's (04)
					t.lost_ap = maxi(t.lost_ap, Rules.DISARM_AP)
					t.disarmed = true
					t.exposed = a.ally and Progression.trained(a.member, "exposing_disarm")
		if a.poison_blade and not Rules.old("poison"):   # Poison Blade: each hit poisons, and the poisons stack (03, Ethan, Nov 5, 2026)
			_blade_hit(a, t)
	if a.ally:
		result = {coins = shown, title = "Hit!" if hit else "Miss", good = hit, lucky = lucked,
				sub = "Damage: %d [placeholder]" % dmg if hit else ""}   # the coins show the heads
		hud.refresh()
	if a.ally and k.kind != "save":
		a.opened = true   # Opening Strike: only the fight's first attack
		a.stakes = false   # Raise the Stakes: the next attack, hit or miss
	if hit and a.ally and k.id == "step_strike" and Progression.trained(a.member, "flowing_strike"):
		a.flowing = true
	a.facing = _dir_toward(a.cell, t.cell)   # it faces whoever it last attacked
	if a.ally and a.weapon == "scimitar" and weapon_attack(k):
		a.dance_ready = true   # Dancing Step, after any scimitar attack (04)
	if hit and a.ally and weapon_attack(k) and a.weapon == "shortsword" and k.id != "quick_slash":
		a.quick_ready = true
	return {hit = hit, dmg = dmg}


## After the motion: the damage lands, then the push, Haymaker's save and Guard Up's hit back.
func _attack_land(a: Dictionary, t: Dictionary, k: Dictionary, hit: bool, dmg: int) -> void:
	hud.float_text(t, "-%d" % dmg if hit else "Miss", hit)
	if hit:
		await _hurt(t, dmg)
		if k.get("rider", "") == "push" and (Rules.old("bash") or Rules.bash() == "stun"):
			t.lost_ap = Rules.AP   # test aid: Shield Bash's old stun
		elif k.get("rider", "") == "push":
			await _push(a, t, 2 if Rules.bash() == "push2" else Rules.PUSH_HEXES)
			if Rules.bash() == "hold" and not t.down:   # test aid: the push, and the foe loses its next Move
				t.snared = _until_next_turn_of(t)
		if k.get("rider", "") == "rend" and not t.down:   # Rend: a failed CON save and it bleeds (04)
			var rend := flip_check(save_coins(t, "CON"), Rules.SAVE_HEADS)
			await hud.flip_coins(t, rend.coins, rend.need, Rules.COIN_STEP_FOE)
			if Coins.heads(rend.coins) < rend.need:
				t.bleed_turns = Rules.DOT_TURNS
		if k.get("rider", "") == "haymaker" and not t.down:   # a failed CON save: it loses 1 AP next turn (04)
			var harder := 1 if a.ally and Progression.trained(a.member, "haymaker_stun") else 0   # Haymaker+ (Bruiser)
			var save := flip_check(save_coins(t, "CON"), Rules.SAVE_HEADS + harder)
			await hud.flip_coins(t, save.coins, save.need, Rules.COIN_STEP_FOE)
			if Coins.heads(save.coins) < save.need:
				t.lost_ap = maxi(t.lost_ap, Rules.HAYMAKER_AP)
	var counter: bool = t.guard_counter and (hit or (t.ally and Progression.trained(t.member, "guard_up_plus")))   # Guard Up+ on a miss too (04)
	if (counter or t.get("riposte", false)) and not a.down and not t.down:   # Guard Up: the first foe to hit you takes a normal hit back; Riposte
		if counter:
			t.guard_counter = false
		t.riposte = false
		var back: int = attack_score(t, Cards.get_card("attack", t.weapon))
		hud.float_text(a, "-%d" % back, true)
		await _hurt(a, back)


## Levels 2-5 (Progression): extra damage on a hit from mastery passives and upgrades, feats, Rage, Raise the Stakes,
## Holy Brand, Curse of Ruin and Trophy Mark. Amounts: Rules (PLACEHOLDER).
func _level_damage(a: Dictionary, t: Dictionary, k: Dictionary) -> int:
	var n := 0
	if a.ally:
		var m: Dictionary = a.member
		var two_handed: bool = a.off in ["", "none"]
		if k.id == "attack" and a.weapon == "greatsword" and Progression.trained(m, "heavy_blade"):
			n += Rules.HEAVY_BLADE
		if k.id == "throw" and a.weapon in ["spear", "battleaxe"] and Progression.trained(m, "throw_plus"):
			n += Rules.THROW_PLUS_DAMAGE
		if k.id == "quick_slash" and Progression.trained(m, "quick_slash_plus"):
			n += Rules.QUICK_SLASH_PLUS
		if a.weapon == "battleaxe" and two_handed and weapon_attack(k) and t.hp < t.max_hp and Progression.trained(m, "headhunter"):
			n += Rules.HEADHUNTER
		if k.id == "haymaker" and Progression.trained(m, "haymaker_damage"):
			n += Rules.HAYMAKER_PLUS
		if k.id == "attack" and Weapons.of(a.weapon).ab == "STR" and Progression.feat(m) == "heavy_hitter":
			n += Rules.HEAVY_HITTER
		if not a.mark.is_empty() and a.mark == t and Progression.sub(m) == "Hunter" and String(t.member.get("mini", "")).begins_with("giant_"):
			n += Rules.TROPHY_MORE   # Trophy Mark: more against large foes (03)
	if on(a, "rage"):
		n += Rules.RAGE_MORE
	if on(t, "rage"):
		n += Rules.RAGE_MORE   # a raging hero takes more too (04)
	if t.branded:
		n += Rules.BRAND_DAMAGE
	if on(t, "ruin"):
		n += Rules.RUIN_MORE
	return n


## Raise the Stakes doubles a hit, after the flat bonuses; less damage taken: Arcane Shield, Bring It against a taunted foe,
## and Drilled (an adjacent ally defending).
func _level_reduction(a: Dictionary, t: Dictionary) -> int:
	var n := 0
	if t.arcane_shield:
		n += Rules.ARCANE_SHIELD_LESS
	if t.bring_it and a.get("taunt", {}) == t:
		n += Rules.BRING_IT_LESS
	if t.ally and allies().any(func(o): return o != t and o.defending and dist(o, t) == 1 and Progression.feat(o.member) == "drilled"):
		n += Rules.DRILLED_LESS
	return n


## A hit under Poison Blade, as the Rogue's subclass has it (03): poison (Poison Blade+ deadlier), drowsy (Sleeping Draught),
## or a random status (Wild Card: poison, bleed or slow; blind isn't built, PLACEHOLDER).
func _blade_hit(a: Dictionary, t: Dictionary) -> void:
	match Progression.sub(a.member):
		"Con Artist":
			t.drowsy = _until_next_turn_of(t)
		"Gambler":
			match rng.randi_range(0, 2):
				0:
					t.poison.append(Rules.DOT_TURNS)
				1:
					t.bleed_turns = Rules.DOT_TURNS
				2:
					_slow(t, Rules.FROST_SLOW)
		"Assassin":
			for i in Rules.POISON_PLUS:   # each entry ticks DOT_DAMAGE, so this many is the deadlier poison
				t.poison.append(Rules.DOT_TURNS)
		_:
			t.poison.append(Rules.DOT_TURNS)


## Whether a foe holds a weapon to knock away (Disarm, 04). PLACEHOLDER: every foe but beasts (wolves).
func holds_weapon(t: Dictionary) -> bool:
	var mini_id: String = t.member.get("mini", "")
	return not t.ally and not Rules.UNARMED_MINIS.any(func(p): return mini_id.begins_with(p))


## A metal golem's damage reduction on hits and Breath Weapon, doubled under Lockdown (design/03 -> Races), and Warding
## Circle's for an ally inside one (03 -> Ritualist).
func reduction(t: Dictionary) -> int:
	if not t.ally:
		return 0
	return Races.reduction(t.member, game.level) * (2 if t.lockdown else 1) + (Rules.WARDING_LESS if warded(t) else 0)


## What an attack on t needs: its defence (DOCS: 03 -> Hit chance scaling; heroes 04 -> Armour). Modifiers change coins,
## not heads (attack_mods).
func heads_needed(t: Dictionary, a := {}, _k := {}) -> int:
	var n: int = t.get("heads", Rules.HEADS_TO_HIT)
	if on(t, "sidestep"):
		n += Rules.SIDESTEP_HEADS   # Sidestep (04)
	if not a.is_empty() and a.get("stakes", false):
		n += 1   # Raise the Stakes: one more heads (03)
	return n


## Which attack motion a's attack on t plays (art/handoff/attack_motions.md). The hand-off names the kinds; PLACEHOLDER:
## which cards play which (Scorch the orb, Blood Bolt and wand hits the darts, Haymaker and Bonebreaker the heavy blow),
## and foes hop next to a hero and jab from 2 away.
func motion_kind(a: Dictionary, t: Dictionary, k: Dictionary) -> String:
	match k.id:
		"sweeping_arc":
			return "sweep"
		"firebolt", "scorch":
			return "orb"
		"frost_ray":
			return "ray"
		"blood_bolt":
			return "darts"
		"shocking_grasp":
			return "touch"
		"throw", "stone_throw":
			return "thrown"
		"haymaker", "bonebreaker":
			return "heavy"
	if not a.ally:
		return "thrust" if dist(a, t) >= 2 else "melee"
	var w := Weapons.of(a.weapon)
	if k.get("ranged", false) or (weapon_attack(k) and w.get("ranged", false)):
		return "darts" if a.weapon in ["wand", "summon_wisp"] else "shot"
	if weapon_attack(k) and a.weapon in ["spear", "halberd", "glaive"]:
		return "thrust"
	if weapon_attack(k) and a.weapon in ["greatsword", "greataxe", "warhammer"]:
		return "heavy"
	return "melee"


## Whether a hits with this card's weapon (the basic attack, weapon cards, Sneak Attack).
static func weapon_attack(k: Dictionary) -> bool:
	return k.id in ["attack", "sneak_attack"] or k.src == "weapon"


## Sneak Attack's bonus applies (03): the foe is flanked or unaware of the Rogue (03 -> Ambush).
func sneak_applies(a: Dictionary, t: Dictionary) -> bool:
	return _flanked(a, t) or Ambush.is_unaware(t, a)


## Another of a's side next to t: summons count, decoys don't (03 -> Summoner, Ethan, Nov 6, 2026).
func _flanked(a: Dictionary, t: Dictionary) -> bool:
	for u in units:
		if u != a and u.ally == a.ally and not u.down and u.decoy == "" and dist(u, t) == 1:
			return true
	return false


## When a rider put on t now ends: at the end of t's next turn (design/06 -> First playable -> Races).
func _until_next_turn_of(t: Dictionary) -> int:
	return phase_no + (2 if t.ally == (phase == "allies") else 1)


## Save spells: the foe flips to save. Sacred Flame: a save halves the damage and ignores riders (DOCS). Faerie Fire and
## Lull: a save means no effect.
func _save_spell(a: Dictionary, t: Dictionary, k: Dictionary) -> void:
	if k.get("effect", "") in ["burst", "chain"]:
		await _save_area(a, _spell_targets(a, t, k), k)
		return
	busy = true
	refresh()
	var check := flip_check(save_coins(t, k.save), Rules.SAVE_HEADS)
	var coins: Array[bool] = await hud.flip_coins(t, check.coins, check.need, Rules.COIN_STEP_FOE)
	var saved: bool = Coins.heads(check.coins) >= check.need
	match k.get("effect", ""):
		"glow", "lull":
			result = {coins = coins, title = "Saved" if saved else "Failed save!", good = not saved, sub = ""}
			hud.refresh()
			await board.bloom(a.mini, t.mini, k.effect, saved)
			if not saved and k.effect == "glow":
				t.glow = phase_no + 1   # until the caster's next turn
			elif not saved:
				t.lull = true
		"bleed", "brand", "frailty", "ruin", "surrender", "mage_hand", "siphon_str":
			result = {coins = coins, title = "Saved" if saved else "Failed save!", good = not saved, sub = ""}
			hud.refresh()
			await board.bloom(a.mini, t.mini, "flame", saved)   # PLACEHOLDER look: the save curses and riders have no motion of their own yet
			if not saved:
				_save_rider(a, t, k)
		_:
			var full := _spell_damage(a, t, k)
			var dmg: int = full / 2 if saved else full
			result = {coins = coins, title = "Saved: half damage" if saved else "Failed save!", good = not saved,
					sub = "Damage: %d [placeholder]" % dmg}   # the coins show the heads
			hud.refresh()
			await board.bloom(a.mini, t.mini, "flame", saved)
			hud.float_text(t, "-%d" % dmg, true)
			await _hurt(t, dmg)
			if k.get("effect", "") == "siphon" and not a.down:   # Soul Siphon heals the caster what it drains (03)
				var before: int = a.hp
				a.hp = mini(a.max_hp, a.hp + dmg)
				hud.float_text(a, "+%d" % (a.hp - before), false, true)
	busy = false
	_check_end()


## A save spell's full damage (half on a save): the INT spells (PLACEHOLDER, as the level-1 wizard spells: INT plus the
## card's bonus), Psychic Spike more on a foe unaware of you, Toll the Dead more on a hurt foe; the rest Sacred Flame's.
func _spell_damage(a: Dictionary, t: Dictionary, k: Dictionary) -> int:
	var n: int = Rules.SPELL_DAMAGE
	if k.get("ab", "") == "INT":
		n = Races.score(a.member, "INT") + k.get("bonus", 0) + Rules.SPELL3_DAMAGE
	match k.get("effect", ""):
		"psychic":
			if not t.is_empty() and a.name in t.unaware:
				n += Rules.PSYCHIC_UNAWARE
		"toll":
			if not t.is_empty() and t.hp < t.max_hp:
				n += Rules.TOLL_HURT
	return n


## What a failed save leaves on the foe (03): Hemorrhage bleeds, Holy Brand marks it for the fight, the curses last until
## the end of its next turn, Fake Surrender makes it unaware of you, Mage Hand disarms it, Siphon Strength takes STR.
func _save_rider(a: Dictionary, t: Dictionary, k: Dictionary) -> void:
	match k.effect:
		"bleed":
			t.bleed_turns = Rules.DOT_TURNS
		"brand":
			t.branded = true
		"frailty":
			t.frail = _until_next_turn_of(t)
		"ruin":
			t.ruin = _until_next_turn_of(t)
		"surrender":
			if not a.name in t.unaware:
				t.unaware.append(a.name)
		"mage_hand":
			if holds_weapon(t):
				t.lost_ap = maxi(t.lost_ap, Rules.DISARM_AP)
				t.disarmed = true
		"siphon_str":   # PLACEHOLDER: only the foe's loss; the ally's gain isn't built
			t.score = maxi(t.score - Rules.SIPHON_STR, 0)


## Who an area or chain spell reaches (03): Flame Burst and Fireball everyone within their radius of the target, allies
## too; Chain Spark and Chain Lightning the target, then the nearest other foe within CHAIN_RANGE of the last, foes only.
func _spell_targets(a: Dictionary, t: Dictionary, k: Dictionary) -> Array:
	if k.effect == "burst":
		return units.filter(func(o): return not o.down and Rules.hex_distance(o.cell, t.cell) <= k.radius)
	var out := [t]
	for i in k.jumps:
		var last: Dictionary = out[-1]
		var next := foes_of(a).filter(func(o): return not o in out and dist(o, last) <= Rules.CHAIN_RANGE)
		if next.is_empty():
			break
		next.sort_custom(func(x, y): return dist(x, last) < dist(y, last))
		out.append(next[0])
	return out


## Several targets each flip their save, then the effect lands on each (Ground Pound, Dawn Pulse, Unbind, Flame Burst,
## Fireball, the chains): damage halved on a save, or knocked prone on a fail (Ground Pound). Chain Lightning weakens by 1
## a jump.
func _save_area(a: Dictionary, targets: Array, k: Dictionary) -> void:
	busy = true
	refresh()
	for i in targets.size():
		var t: Dictionary = targets[i]
		if t.down:
			continue
		var check := flip_check(save_coins(t, k.save), Rules.SAVE_HEADS)
		await hud.flip_coins(t, check.coins, check.need, Rules.COIN_STEP_FOE)
		var saved: bool = Coins.heads(check.coins) >= check.need
		if k.get("effect", "") == "pound":
			await board.bloom(a.mini, t.mini, "flame", saved)   # PLACEHOLDER look
			if not saved:
				t.lost_ap = maxi(t.lost_ap, Rules.PRONE_AP)
			continue
		var full: int = maxi(_spell_damage(a, t, k) - k.get("weaken", 0) * i, 0)
		var dmg: int = full / 2 if saved else full
		await board.bloom(a.mini, t.mini, "flame", saved)
		hud.float_text(t, "-%d" % dmg, true)
		await _hurt(t, dmg)
	if a.ally:
		result = {coins = [], title = "Used", good = true, sub = ""}
	busy = false
	refresh()
	_check_end()


func _ally_spell(a: Dictionary, t: Dictionary, k: Dictionary) -> void:
	if k.effect != "swap":
		board.buff(a.mini, t.mini)   # the rising ring; the result shows meanwhile
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
		"blood_ward":   # a new one replaces the old (03)
			t.ward = Rules.BLOOD_WARD
			result = {coins = [], title = "Used", good = true, sub = ""}
		"stone_skin":
			t.defending = true   # PLACEHOLDER (03: "less damage this turn"): as Defend
			result = {coins = [], title = "Used", good = true, sub = ""}
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
			if a.ally and Progression.sub(a.member) == "Tactician":
				for o in allies():   # Battle Surge: every ally +1 bonus AP (03)
					if o != a and not o.down:
						o.bonus += maxi(0, mini(1, Rules.AP_CAP - ap_left(o)))
		"heal":
			var before: int = a.hp
			a.hp = mini(a.max_hp, a.hp + Rules.HEAL)
			hud.float_text(a, "+%d" % (a.hp - before), false, true)
			match Progression.sub(a.member) if a.ally and k.id == "second_wind" else "":
				"Holy Defender":   # Blessed Wind: adjacent allies heal too (03)
					for o in allies():
						if o != a and not o.down and dist(o, a) == 1:
							var was: int = o.hp
							o.hp = mini(o.max_hp, o.hp + Rules.HEAL)
							hud.float_text(o, "+%d" % (o.hp - was), false, true)
				"Arcane Knight":   # Second Ward: and a ward (03)
					a.ward = maxi(a.ward, Rules.SECOND_WARD)
		"poison":
			a.poison_blade = true
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
		"guard":
			a.guard = true   # Guard Up: 2 less damage until its next turn, and a hit back on the first foe to hit it (04)
			a.guard_counter = true
		"guide":
			pass   # DOCS (06): plays, and reveals nothing until hidden foes and traps exist
		"mirror":
			_mirror(a)
		"sidestep":
			a.sidestep = _until_next_turn_of(a)
		"rage":
			a.rage = _until_next_turn_of(a)
		"arcane_shield":
			a.arcane_shield = true
		"stakes":
			a.stakes = true
		"bring_it":   # adjacent foes must attack you until their next turn ends (03)
			a.bring_it = true
			for e in foes_of(a):
				if dist(e, a) == 1:
					e.taunt = a
					e.taunt_until = _until_next_turn_of(e)
		"vanish":   # hidden: every foe loses track of you (PLACEHOLDER: hidden is unaware, 03 -> Ambush)
			for e in foes_of(a):
				if not a.name in e.unaware:
					e.unaware.append(a.name)
		"life_tap":
			a.bonus += maxi(0, mini(2, Rules.AP_CAP - ap_left(a)))
		"pound":
			await _save_area(a, foes_of(a).filter(func(e): return dist(e, a) == 1), k)
		"pulse":
			await _save_area(a, foes_of(a).filter(func(e): return dist(e, a) <= Rules.PULSE_RANGE), k)
		"unbind":
			var s: Dictionary = a.conc.get("unit", {})
			var around := units.filter(func(o): return o != s and o != a and not o.down and o.decoy == "" and dist(o, s) == 1)
			_vanish(s)
			_end_conc(a)
			await _save_area(a, around, k)
		"mass_heal", "plenty":
			for o in allies():
				if not o.down and (k.effect == "plenty" or dist(o, a) <= Rules.MASS_HEAL_RANGE):
					var before: int = o.hp
					o.hp = mini(o.max_hp, o.hp + (Rules.HEAL if k.effect == "mass_heal" else Rules.PLENTY_HEAL))
					hud.float_text(o, "+%d" % (o.hp - before), false, true)
		"purify":
			for o in allies():
				o.poison = []
				o.bleed_turns = 0
				o.slowed = -1
				o.snared = -1
				o.drowsy = -1


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
	result = {coins = [], title = "", good = true, sub = "", rows = []}   # each target's save and damage, for the panel
	refresh()
	var took := []   # [unit, damage]: everyone flips first, then the cone plays and the damage lands (07 -> Combat flips come first)
	for c: Vector2i in line:
		var t := unit_at(c)
		if not t.is_empty() and not t.down and t != a:
			var check := flip_check(save_coins(t, "DEX"), Rules.SAVE_HEADS)
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
						_slow(t, Rules.WHITE_SLOW)
					"Black":
						t.acid = _until_next_turn_of(t)
					"Green":
						t.poison.append(Rules.DOT_TURNS)
			result.rows.append({name = t.name, coins = coins, dmg = dmg, lucky = coins != check.coins})
			hud.refresh()
			took.append([t, dmg])
	var toward := Hex.to3(Hex.cell_position(line[-1].x, line[-1].y) - Hex.cell_position(a.cell.x, a.cell.y)) if not line.is_empty() else Vector3.FORWARD
	await board.cone(a.mini, toward, line.map(func(c): return board.global_transform * cell_point(c)),
			took.filter(func(e): return e[1] > 0).map(func(e): return e[0].mini))
	for e: Array in took:
		hud.float_text(e[0], "-%d" % e[1], true)
		await _hurt(e[0], e[1])
	busy = false
	refresh()
	_check_end()


## Where a ground card can go: Glimmerstep's landing spots, the Snare's hexes (an empty walkable hex up to 3 away, brush
## too, never lava: 03), or Dancing Step's (up to 2 hexes of movement).
func cell_options(u: Dictionary, k: Dictionary) -> Array[Vector2i]:
	match k.get("effect", ""):
		"snare":
			var out: Array[Vector2i] = []
			for c: Vector2i in grid:
				if Rules.hex_distance(c, u.cell) <= Rules.SNARE_RANGE and grid[c].kind in ["open", "brush"] and unit_at(c).is_empty() and c != u.cell:
					out.append(c)
			return out
		"dance":
			var out: Array[Vector2i] = []
			for c in _spread(u, Rules.DANCE_HEXES, Callable()):
				if c != u.cell:
					out.append(c)
			return out
		"summon", "phantom":   # a summon on an empty hex beside you; Phantom Ally on one within 5 (03)
			var out: Array[Vector2i] = []
			for c: Vector2i in grid:
				if Rules.hex_distance(c, u.cell) in range(1, k.range + 1) and grid[c].kind in ["open", "brush"] and unit_at(c).is_empty():
					out.append(c)
			return out
		"circle":   # Warding Circle's middle hex, within 5 (03)
			var out: Array[Vector2i] = []
			for c: Vector2i in grid:
				if Rules.hex_distance(c, u.cell) <= k.range and grid[c].kind != "blocked":
					out.append(c)
			return out
	return blink_cells(u)


func _set_snare(u: Dictionary, c: Vector2i) -> void:
	_clear_snare(u.name)   # one at a time: setting another moves it (03)
	snares[u.name] = c
	var ring := MeshInstance3D.new()   # PLACEHOLDER look: a dark ring on the hex, which only the party sees
	var mesh := TorusMesh.new()
	mesh.inner_radius = 0.22
	mesh.outer_radius = 0.3
	ring.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color("#4A3A28")
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	ring.material_override = mat
	ring.position = cell_point(c) + Vector3(0, Rules.CELL_TOP + 0.03, 0)
	add_child(ring)
	_snare_marks[u.name] = ring
	self_done = "snare"
	cell_target = null


func _clear_snare(owner: String) -> void:
	snares.erase(owner)
	if _snare_marks.has(owner):
		_snare_marks[owner].queue_free()
		_snare_marks.erase(owner)


## Dancing Step: a free short move after a scimitar attack.
func _dance(u: Dictionary, c: Vector2i) -> void:
	busy = true
	self_done = "dancing_step"
	cell_target = null
	await _walk(u, _path_to(u, _spread(u, Rules.DANCE_HEXES, Callable()), c))
	busy = false
	refresh()


## Sweeping Arc's hexes: the aimed one (1 or 2 away) and the two beside it at the same distance (04).
func arc_cells(u: Dictionary, c: Vector2i) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	var k := card(sel if not current.is_empty() and Cards.ALL.get(sel, {}).get("kind", "") == "arc" else "sweeping_arc")
	var d := Rules.hex_distance(c, u.cell)
	if d < 1 or d > k.range:
		return out
	if k.id == "sweeping_arc" and Progression.trained(u.member, "sweeping_circle"):   # Sweeping Circle: every hex at that distance (04)
		for e: Vector2i in grid:
			if Rules.hex_distance(e, u.cell) == d:
				out.append(e)
		return out
	out.append(c)
	for n in Hex.NEIGHBOURS:
		var e: Vector2i = c + n
		if Rules.hex_distance(e, u.cell) == d and grid.has(e) and out.size() < 3:
			out.append(e)
	return out


## Sweeping Arc: one flip for each foe in the arc, all first; then one spin, each foe reacting as the trail passes it, and
## the damage lands (Ethan, Nov 8).
func _arc(a: Dictionary, c: Vector2i) -> void:
	busy = true
	var k := card(sel if Cards.ALL.get(sel, {}).get("kind", "") == "arc" else "sweeping_arc")
	self_done = k.id
	var cells := arc_cells(a, c)
	cell_target = null
	var flips := []   # [foe, {hit, dmg}]
	for cell in cells:
		var t := unit_at(cell)
		if not t.is_empty() and not t.ally and not t.down and not flips.any(func(f): return f[0] == t):
			flips.append([t, await _attack_flip(a, t, k)])
	if not flips.is_empty():
		a.facing = _dir_toward(a.cell, flips[0][0].cell)
		await board.sweep(a.mini, flips.map(func(f): return f[0].mini), flips.map(func(f): return f[1].hit))
	for f: Array in flips:
		if not f[0].down:
			await _attack_land(a, f[0], k, f[1].hit, f[1].dmg)
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
	if Rules.old("cover"):
		return "none"   # test aid
	var to: Vector2i = t.cell
	for c in cells_of(t):
		if Rules.hex_distance(a.cell, c) < Rules.hex_distance(a.cell, to):
			to = c
	var n := Rules.hex_distance(a.cell, to)
	var out := "none"
	var za: float = grid[a.cell].z if grid.has(a.cell) else 0.0
	var zt: float = grid[to].z if grid.has(to) else 0.0
	var prev: Vector2i = a.cell
	for i in range(1, n + 1):
		var f := float(i) / n
		var c := _cube_round(Vector3(a.cell.x, a.cell.y, -a.cell.x - a.cell.y).lerp(Vector3(to.x, to.y, -to.x - to.y), f) + Vector3(1e-4, 2e-4, -3e-4))
		# A low edge crossed between two cells (03: partial; a terrace curb is ignored by a shot from its top).
		var key := [prev, c] if prev < c else [c, prev]
		if edge_cover.has(key) and not (grid.has(prev) and grid.has(c) and grid[prev].z != grid[c].z and za >= maxf(grid[prev].z, grid[c].z) - Rules.HEIGHT_SLACK):
			out = "partial"
		prev = c
		if i == n:
			break
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
## low props on a cell, give partial cover; anything else that blocks a cell blocks fully (rocks, walls, buildings). Map pieces with
## `cover` data (fences, barriers, low edges, walls) set their own cells or edges. DOCS (03,
## Ethan picked option A): which props count as low. A map piece without cover data leaves its cells blocking fully.
const PARTIAL_COVER := ["tree", "grove", "thicket", "roots", "hedge", "fence", "stump", "log", "hay", "crates", "sacks", "baskets",
	"butt", "benches", "graves", "scarecrow", "washing", "well", "fire", "mushrooms", "junk", "goods", "wares", "rugs", "racks",
	"arms", "flags", "banner", "dummy", "quintain", "spirit_pole", "lantern_heap", "herd", "brush"]


func _cover_of_map(id: String) -> void:
	cover = {}
	edge_cover = {}
	var data: Dictionary = CombatMap.all()[id]
	for c: Vector2i in grid:
		if grid[c].kind == "brush":
			cover[c] = "partial"
		elif grid[c].kind == "blocked":
			cover[c] = "full"
	for p: Dictionary in data.placements:
		var name := String(p.piece)
		if p.has("cover"):   # a map piece's line (art/handoff/combat_cover_data.md): walls block, fences, barriers and edges don't
			var kind := "full" if p.cover == "wall" else "partial"
			for c in p.get("cells", []):
				var cell := Vector2i(int(c[0]), int(c[1]))
				if grid.has(cell):
					cover[cell] = kind
			for e in p.get("edges", []):
				var c1 := Vector2i(int(e[0][0]), int(e[0][1]))
				var c2 := Vector2i(int(e[1][0]), int(e[1][1]))
				edge_cover[[c1, c2] if c1 < c2 else [c2, c1]] = kind
			continue
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
	var sprung := ""
	if not u.ally:   # a foe walks into a hidden Snare as if it weren't there, and its move ends there (03)
		var stop := -1
		for i in path.size():
			for owner: String in snares:
				if snares[owner] == path[i] and sprung == "":
					sprung = owner
					stop = i
		if stop >= 0:
			path = path.slice(0, stop + 1)
	if sprung != "":
		await _walk_on(u, path)
		_clear_snare(sprung)
		var setter := allies().filter(func(a): return a.name == sprung)
		if not setter.is_empty():
			Ambush.noticed(u, setter[0])   # the Snare's damage is the Ranger's hostile action (03 -> Ambush)
		if not u.down:
			u.snared = _until_next_turn_of(u)
			hud.float_text(u, "-%d" % Rules.SNARE_DAMAGE, true)
			await _hurt(u, Rules.SNARE_DAMAGE)
		return
	await _walk_on(u, path)


func _walk_on(u: Dictionary, path: Array) -> void:
	u.facing = _dir_toward(path[-2] if path.size() > 1 else u.cell, path[-1])   # it faces the way it last moved
	u.cell = path[-1]
	refresh()
	if u.get("member", {}).get("flies", false) or not path.any(func(c): return grid[c].kind == "lava"):
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
	return not u.down and grid.has(u.cell) and grid[u.cell].kind == "lava" and not u.get("member", {}).get("flies", false)


func _hurt(t: Dictionary, dmg: int) -> void:
	if t.decoy != "":   # any hit pops a decoy, area spells and breath included (03 -> Deceiver)
		_vanish(t)
		return
	Ambush.noticed(t, _acting)
	if dmg > 0:
		t.lull = false   # any damage wakes it, poison, bleed and lava too (Ethan, Nov 5, 2026)
	t.hp -= dmg
	if t.hp <= 0 and not t.down:
		t.down = true
		if t == target:
			target = {}
		if is_summon(t):   # a summon is gone once destroyed, and its caster's concentration with it
			var caster := _caster_of(t)
			if not caster.is_empty() and caster.conc.get("unit", {}) == t:
				caster.conc = {}
			_vanish(t)
			return
		await board.fall(t.mini, not t.ally)
		if not t.conc.is_empty():   # going down breaks concentration (03, Ethan, Nov 6, 2026)
			_end_conc(t)


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
	var allies_up := units.any(func(u): return u.ally and not u.down and u.decoy == "" and not is_summon(u))
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
	u.backstabbed = false
	u.arcane_shield = false   # Arcane Shield and Bring It last until your next turn (03)
	u.bring_it = false
	u.flowing = false
	u.guard = false
	u.guard_counter = false
	u.quick_ready = false
	u.dance_ready = false
	if not u.poison.is_empty() and not u.down:   # each poison ticks: they stack
		var dmg: int = Rules.DOT_DAMAGE * u.poison.size()
		u.poison = u.poison.map(func(n): return n - 1).filter(func(n): return n > 0)
		hud.float_text(u, "-%d" % dmg, true)
		await _hurt(u, dmg)
	if u.bleed_turns > 0 and not u.down:
		u.bleed_turns -= 1
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
	_acting = {}   # a card cancelled mid-pick leaves no one acting
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
		e.ap = maxi(Rules.AP - e.lost_ap - Ambush.first_turn_ap(e), 0)   # stunned or prone; ambushed, its first turn
		e.lost_ap = 0
		e.disarmed = false   # its weapon recovered
		await _turn_starts(e)
		if e.down:
			_check_end()
			continue
		var attacks := 0
		var lure := await _fooled_by_phantom(e)
		while e.ap > 0 and not e.down and active and phase == "enemies":
			var targets := foes_of(e)
			if targets.is_empty():
				break
			targets.sort_custom(func(a, b): return dist(a, e) < dist(b, e))
			var t: Dictionary = targets[0]
			if not lure.is_empty() and not lure.down and lure in units:   # fooled: it goes for the phantom instead (03)
				t = lure
			var taunter := _taunter(e)
			if not taunter.is_empty():   # Bring It and Stone Sentinel: it must attack them (03)
				t = taunter
			if dist(t, e) == 1:
				if attacks >= Foes.attacks_per_turn:
					break
				attacks += 1
				e.ap -= 1
				if e.lull:   # Lull: it loses its next attack, and wakes
					e.lull = false
					continue
				var copy := await _fooled_by_copy(e, t)
				if not copy.is_empty():   # it hits a copy instead, which pops (03 -> Mirror Image)
					await board.attack(e.mini, copy.mini, true)
					hud.float_text(copy, "Hit!", true)
					_vanish(copy)
				else:
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


# --- Summons, decoys and concentration (03 -> Wizard spells; Wizard level-1 placeholders) ----------------

## Who a foe must attack: whoever taunted it with Bring It, until its turn ends, or a Stone Sentinel near it (03; PLACEHOLDER:
## "nearby" is within 2 hexes), or {}.
func _taunter(e: Dictionary) -> Dictionary:
	if not e.taunt.is_empty() and not e.taunt.down and e.taunt in units and e.taunt_until >= phase_no:
		return e.taunt
	for o in units:
		if o.ally and o.taunts and not o.down and dist(o, e) <= 2:
			return o
	return {}


## The caster a summon or copy belongs to, by name, or {}.
func _caster_of(u: Dictionary) -> Dictionary:
	var who: String = u.summon_of if u.summon_of != "" else u.copy_of
	for o in units:
		if o.name == who and o.ally and o.decoy == "" and not is_summon(o):
			return o
	return {}


## The summon u has out, or {}.
func summon_of(u: Dictionary) -> Dictionary:
	var s: Dictionary = u.conc.get("unit", {})
	return s if not s.is_empty() and s in units and not s.down else {}


## A new concentration effect ends the old one (03). Both card kinds: a summon and Warding Circle.
func _concentrate(u: Dictionary, k: Dictionary, what := {}) -> void:
	if not u.conc.is_empty():
		_end_conc(u)
	u.conc = {id = k.id, unit = what}


## Ending one: the summon goes, or the circle fades.
func _end_conc(u: Dictionary) -> void:
	var s: Dictionary = u.conc.get("unit", {})
	u.conc = {}
	if circles.has(u.name):
		circles[u.name].node.queue_free()
		circles.erase(u.name)
	if not s.is_empty() and s in units:
		_vanish(s)


## A summon, copy or phantom leaves the board: it sinks away and is gone from the fight.
func _vanish(u: Dictionary) -> void:
	if not u in units:
		return
	u.down = true
	u.hp = 0
	if u == target:
		target = {}
	if u == current:
		current = {}
	units.erase(u)
	var tw: Tween = u.mini.create_tween()
	tw.tween_property(u.mini, "scale", Vector3(0.05, 0.05, 0.05), 0.3)
	tw.tween_callback(u.mini.queue_free)
	refresh()


## Animated Blade or Wisp on an empty hex beside the caster: the player's to act with, from this turn (03).
func _summon(u: Dictionary, c: Vector2i, k: Dictionary) -> void:
	var s: Dictionary = Rules.SUMMONS[k.id]
	var m := {name = s.name, initial = s.initial, color = u.color, mini = s.mini, ability = "INT", hp = s.hp, max_hp = s.hp,
			damage = s.damage, weapon = s.weapon, armour = "none", flies = s.get("flies", false), summon_of = u.name, taunt = s.get("taunt", false),
			scores = {"INT": Races.score(u.member, "INT")}, cards = ["move", "attack"], hot = ["move", "attack"]}
	_concentrate(u, k)
	_add_unit(m, c, true, s.initial, Hex.cell_position(u.cell.x, u.cell.y) * 2.0 - Hex.cell_position(c.x, c.y))
	var unit: Dictionary = units[-1]
	board.summon(u.mini, unit.mini)   # it drops onto its cell
	unit.ap = Rules.SUMMON_AP if phase == "allies" else 0
	u.conc.unit = unit
	self_done = k.id
	cell_target = null


## Warding Circle: a hex and its 6 neighbours (03).
func circle_cells(c) -> Array:
	if c == null:
		return []
	var out := [c]
	for n in Hex.NEIGHBOURS:
		if grid.has(c + n):
			out.append(c + n)
	return out


func warded(t: Dictionary) -> bool:
	return t.decoy == "" and circles.values().any(func(z): return t.cell in z.cells)


func _circle(u: Dictionary, c: Vector2i) -> void:
	_concentrate(u, card("warding_circle"))
	var node := Node3D.new()   # PLACEHOLDER look: a pale blue glow on its hexes
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color("#8EC3F2", 0.5)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	var cells := circle_cells(c)
	for cell: Vector2i in cells:
		var mi := MeshInstance3D.new()
		mi.mesh = _lifted_mesh(cell)
		mi.material_override = mat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.position = Hex.to3(Hex.cell_position(cell.x, cell.y), grid[cell].z + (Rules.CELL_TOP if map_id != "" else 0.0) + 0.008)
		node.add_child(mi)
	board.add_child(node)
	circles[u.name] = {cells = cells, node = node}
	self_done = "warding_circle"
	cell_target = null


## A decoy: the caster's own mini, faded (Mirror Image), or a fake party member (Phantom Ally). PLACEHOLDER looks. It pops
## after one hit, so 1 HP; it never acts.
func _decoy(u: Dictionary, c: Vector2i, kind: String) -> Dictionary:
	var m := {name = u.name if kind == "mirror" else "Phantom ally", initial = u.initial if kind == "mirror" else "P",
			color = u.color if kind == "mirror" else "#9FB8D9", mini = u.member.mini if kind == "mirror" else "standin_small",
			ability = "INT", hp = 1, max_hp = 1, scores = {}, armour = "none", decoy = kind, copy_of = u.name, cards = []}
	_add_unit(m, c, true, m.initial)
	var d: Dictionary = units[-1]
	var body: MeshInstance3D = d.mini.get_node("body")
	for i in body.mesh.get_surface_count():   # see-through, and the phantom pale blue
		var mat := body.mesh.surface_get_material(i) as BaseMaterial3D
		if mat:
			var faded := mat.duplicate() as BaseMaterial3D
			faded.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			faded.albedo_color = Color(1, 1, 1, 0.55) if kind == "mirror" else Color(0.72, 0.84, 1.0, 0.5)
			body.set_surface_override_material(i, faded)
	return d


## Mirror Image: 2 copies on free hexes beside you; a new cast replaces the old ones (03).
func _mirror(u: Dictionary) -> void:
	for o in units.duplicate():
		if o.decoy == "mirror" and o.copy_of == u.name:
			_vanish(o)
	var spots: Array = []
	for n in Hex.NEIGHBOURS:
		var c: Vector2i = u.cell + n
		if grid.has(c) and grid[c].kind in ["open", "brush"] and unit_at(c).is_empty() and spots.size() < Rules.MIRROR_COPIES:
			spots.append(c)
	for c: Vector2i in spots:
		_decoy(u, c, "mirror")


func _phantom(u: Dictionary, c: Vector2i) -> void:
	for o in units.duplicate():   # one at a time: a new one replaces it (PLACEHOLDER)
		if o.decoy == "phantom" and o.copy_of == u.name:
			_vanish(o)
	_decoy(u, c, "phantom")
	self_done = "phantom_ally"
	cell_target = null


## A foe's INT save against an illusion (03): flipped over it; true if it fails and is fooled.
func _fooled(e: Dictionary) -> bool:
	var check := flip_check(save_coins(e, "INT"), Rules.SAVE_HEADS)
	await hud.flip_coins(e, check.coins, check.need, Rules.COIN_STEP_FOE)
	return Coins.heads(check.coins) < check.need


## At a foe's turn start, with a Phantom Ally out: on a failed INT save it goes for the phantom this turn (03).
func _fooled_by_phantom(e: Dictionary) -> Dictionary:
	for o in units:
		if o.decoy == "phantom" and not o.down:
			return o if await _fooled(e) else {}
	return {}


## A foe attacking someone with Mirror Image copies out: on a failed INT save it hits a copy (03).
func _fooled_by_copy(e: Dictionary, t: Dictionary) -> Dictionary:
	for o in units:
		if o.decoy == "mirror" and o.copy_of == t.name and not o.down:
			return o if await _fooled(e) else {}
	return {}


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
	if u.poison_blade:
		fx.append(["Poison Blade", "hits this turn poison"])
	if is_summon(u):
		fx.append(["Summoned", "Summoned by %s" % u.summon_of])
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
	if not u.poison.is_empty():
		out.append(["skull", "Poisoned", "%d damage at the start of its turn" % Rules.DOT_DAMAGE])
	if on(u, "slowed"):
		out.append(["snow", "Slowed", "1 hex less per Move"])
	if on(u, "acid"):
		out.append(["acid", "Acid-burned", "attacks on it flip 1 extra coin"])
	if u.lockdown:
		out.append(["lock", "Lockdown", "damage reduction doubled; can't move"])
	if not u.ally and allies().any(func(a): return a.mark == u):
		out.append(["mark", "Marked", "+%d damage from the Ranger's hits" % Rules.MARK_DAMAGE])
	if u.disarmed:
		out.append([CreatorData.IC.w_rapier, "Disarmed", "loses %d AP next turn" % Rules.DISARM_AP])
	if Ambush.is_unaware(u, current):
		out.append(["eye", "Unaware", "Hasn't noticed %s" % current.name])   # PLACEHOLDER icon (03 -> Ambush: text checked)
	if on(u, "snared"):
		out.append(["snare", "Rooted", "can't move until the end of its next turn"])   # Snare and Pinning Bolt alike (Ethan, Nov 5, 2026)
	if not u.conc.is_empty():   # PLACEHOLDER icons (Ethan, Nov 6, 2026: the lines)
		out.append([CONC_ICON, "Concentrating", "Keeping %s going" % Cards.ALL[u.conc.id].n])
	if u.ally and warded(u):
		out.append([Cards.ALL.warding_circle.icon, "Warded", "Takes %d less damage" % Rules.WARDING_LESS])
	# Levels 2-5 (PLACEHOLDER icons; names and lines to the Screen text check)
	if on(u, "rage"):
		out.append(["flame", "Raging", "Deals and takes %d more damage" % Rules.RAGE_MORE])
	if on(u, "sidestep"):
		out.append([CreatorData.IC.w_rapier, "Sidestepping", "Harder to hit"])
	if u.arcane_shield:
		out.append(["ward", "Arcane Shield", "Takes %d less damage" % Rules.ARCANE_SHIELD_LESS])
	if u.stakes:
		out.append(["fight_once", "Raised stakes", "Next attack: 1 more heads, %dx damage" % Rules.STAKES_TIMES])
	if not u.ally and not _taunter(u).is_empty():
		out.append(["swords", "Taunted", "Must attack %s" % _taunter(u).name])
	if u.branded:
		out.append(["star", "Branded", "Takes %d more damage from each hit" % Rules.BRAND_DAMAGE])
	if on(u, "frail"):
		out.append(["drop", "Frail", "Attacks on it flip %d extra coin" % Rules.FRAILTY_COINS])
	if on(u, "ruin"):
		out.append(["drop", "Ruined", "Takes %d more damage from each hit" % Rules.RUIN_MORE])
	if on(u, "drowsy"):
		out.append(["moon", "Drowsy", "Flips 1 fewer coin"])
	return out


const CONC_ICON := "M12 4a8 8 0 1 0 0 16 8 8 0 1 0 0-16 M12 8a4 4 0 1 0 0 8a4 4 0 1 0 0-8"


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
		if u.poison_blade:
			status.append("Poison Blade")
		lines.append("Status: " + (", ".join(status) if not status.is_empty() else "ready"))
	else:
		# PLACEHOLDER enemy behaviour, as the loop plays it (no enemy AI in the docs yet).
		lines.append("%s %d · spear" % [u.ability, u.score])
		lines.append("Walks to the nearest ally and attacks")
	game.popup.show_at(pos, u.name, lines)
