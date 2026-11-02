class_name MapBoard
extends Node3D
## A map assembled by art/scripts/render_preview.py's rules (build_map): edge wedges same/other,
## farm-village linking, border joins, hills mountains and ranges; water drawn per tile; desert sand shaped in
## world space; ground cover scattered. A tile's name is a terrain or a region variant (Variants).

## Pointy-top axial (q, r) -> terrain. Copied from render_preview.py.
const MAP := {
	Vector2i(0, 0): "forest", Vector2i(1, -1): "forest", Vector2i(1, 0): "forest",
	Vector2i(0, 1): "plains", Vector2i(-2, 0): "plains",
	Vector2i(-1, 0): "village", Vector2i(-1, -1): "village",
	Vector2i(2, -1): "farmland", Vector2i(2, -2): "farmland", Vector2i(1, -2): "farmland", Vector2i(0, -2): "farmland",
	Vector2i(-2, 1): "river", Vector2i(-2, 2): "river", Vector2i(-1, 1): "river", Vector2i(-1, 2): "river",
	Vector2i(0, 2): "river", Vector2i(1, 1): "river", Vector2i(2, 0): "river", Vector2i(3, 0): "river",
	Vector2i(0, -1): "river",
}
## render_preview.TERRAIN_MAP: every terrain, keeping the banned pairs apart.
const TERRAIN_MAP := {
	Vector2i(-1, -2): "hills", Vector2i(0, -2): "hills", Vector2i(1, -2): "hills", Vector2i(2, -2): "plains",
	Vector2i(3, -2): "desert", Vector2i(4, -2): "desert",
	Vector2i(-1, -1): "forest", Vector2i(0, -1): "hills", Vector2i(1, -1): "ruins", Vector2i(2, -1): "plains",
	Vector2i(3, -1): "desert",
	Vector2i(-2, 0): "forest", Vector2i(-1, 0): "forest", Vector2i(0, 0): "plains", Vector2i(1, 0): "ruins",
	Vector2i(2, 0): "river",
	Vector2i(-2, 1): "swamp", Vector2i(-1, 1): "swamp", Vector2i(0, 1): "river", Vector2i(1, 1): "river",
	Vector2i(2, 1): "plains",
	Vector2i(-3, 2): "swamp", Vector2i(-2, 2): "swamp", Vector2i(-1, 2): "river", Vector2i(0, 2): "village",
	Vector2i(1, 2): "farmland",
	Vector2i(3, 0): "hills",  # a lone hills tile, for its own peak
}
const BORDERED := ["farmland", "village"]
const BLEND_WIDTH := 1.6   # ground colour fade width; no doc value yet, matches ground cover's BLEND

# render_animation.py
const RIVER_SPEED := 0.6
const LAKE_SPEED := 0.15
const GRID := 0.35

var terrains := {}         # (q, r) -> terrain of every placed tile
var water_shapes := {}     # (q, r) -> Water.tile_water() result
var boats: Array[Node3D] = []
var slot_nodes := {}       # (q, r) -> MeshInstance3D of each empty slot touching land

var _kit: Dictionary
var _ground: ShaderMaterial
var _ground_img: Image
var _ground_tex: ImageTexture
var _tile_nodes := {}
var _water_node: Node3D
var _slots_node: Node3D
var _slot_mesh: Mesh
var _slot_mat: Material
var _still_water: StandardMaterial3D
var _glow: StandardMaterial3D          # toadstools
var _lamp: StandardMaterial3D          # lanterns (tiles v12)
var _mist_mat: ShaderMaterial
var _fey: StandardMaterial3D           # fey wood's fairy rings and stepping caps, the Fey Court's stair
var _window: StandardMaterial3D        # the Fey Court's windows
var _web: StandardMaterial3D           # dark wood's and the Spider Nest's webs
## Landmark flow of every finished region with landmark art (LandmarkFlow), fixed once the region finishes.
var flow_dist := {}                    # tile -> steps to its region's landmark
var flow_toward := {}                  # tile -> the region neighbour one step closer
var landmark_turns := {}               # landmark tile -> 60 degree steps its centre piece turns
var gates := {}                        # fenced tile -> the edges that show a gate (FenceGates)
var lightning: Lightning               # stormy plains' strikes
var _faint: StandardMaterial3D         # the Abandoned Barn's light through its boards
var _graphs := {}                      # tile -> its drawn paths (TilePaths), built when asked for
## Raised regions (Cliffs; art/handoff/hills_kit.md -> Raised regions).
var raised := {}                       # every raised tile -> true
var raised_regions := {}               # key -> the tiles of that raised region
var lift := {}                         # raised tile -> how high it stands now (Variants.RAISE, once it's up)
var tiles_built := 0                   # counts tiles built, so anything remembering what stands where can tell
var streets := {}                      # village tile -> {edge: "main" or "side"} (VillageStreets)
var party_at = null                    # the party's tile: on raised ground it always has a ledge down (Cliffs.forced_climb)
var climbs := []                       # every region's Cliffs.climbs(), [tile, i]
var _outer := {}                       # raised tile -> its edges with a cliff
var _corners := {}                     # raised tile -> its corners with a pinnacle
var _ledges := {}                      # raised tile -> {edge -> "low", "mid" or "top"}
var _links := {}                       # Vector4i(a, b) of two neighbours -> the [tile, i] climb between them
var _shape := {}                       # raised tile -> what its cliffs were built from, to spot changes
var _lava: StandardMaterial3D          # volcanic cracks, craters, the den
var _lantern_red: StandardMaterial3D   # the slums' and Black Market's lanterns
var _clip_mats := {}                   # surface material -> its cut-off version while a region rises
## Set by the owner so toadstools glow at night (the bog's night glow is the engine's, not the art's).
var time_of_day: TimeOfDay


## render_preview.VARIANT_MAP: the terrains map with every region finished.
static func variant_map() -> Dictionary:
	var out := {}
	for t: Vector2i in TERRAIN_MAP:
		out[t] = Variants.TIER1[TERRAIN_MAP[t]]
	return out


## Joined for edge pieces: the same terrain (a region variant counts as its terrain), or linked terrains.
static func linked(a, b) -> bool:
	if a != null and b != null:
		var ka := Variants.wedges_of(a)
		var kb := Variants.wedges_of(b)
		if ka != kb and (ka in Cliffs.RAISED or kb in Cliffs.RAISED):
			return false   # a raised region shares no mountain with the land below it
	var ta := Variants.terrain_of(a)
	var tb := Variants.terrain_of(b)
	return tb != "" and (ta == tb or (ta in BORDERED and tb in BORDERED))


## Builds a whole map at once (the look-test map).
func build(map := MAP) -> void:
	_setup()
	terrains = map.duplicate()
	for t: Vector2i in terrains:
		_set_ground(t)
	_update_gates()
	_update_streets()
	_update_water()
	for t: Vector2i in terrains:
		_build_tile(t)
	for t: Vector2i in terrains:
		_add_cover(t)
	_build_slots()


## Places one tile and rebuilds what it touches: its neighbours' edge pieces, water, ground cover, slots.
func place(t: Vector2i, terrain: String) -> void:
	if _kit.is_empty():
		_setup()
	retile({t: terrain})


## Sets several tiles at once (placing, or a finished region turning into its variant) and rebuilds what
## they touch: their neighbours' edge pieces, sand and mountains, water, ground cover, slots.
func retile(changes: Dictionary) -> void:
	if _kit.is_empty():
		_setup()
	var t0 := Time.get_ticks_usec()
	var water_changed := false
	var touched := {}
	for t: Vector2i in changes:
		terrains[t] = changes[t]
		_set_ground(t)
		touched[t] = true
		if Variants.is_water(changes[t]):
			water_changed = true
		for n in Hex.NEIGHBOURS:
			if terrains.has(t + n):
				touched[t + n] = true
				if Variants.is_water(terrains[t + n]):
					water_changed = true
	if water_changed:
		_update_water()
	touched.merge(_update_raised())
	touched.merge(_update_gates())
	touched.merge(_update_streets())
	for t: Vector2i in touched:
		_build_tile(t)
	for t: Vector2i in touched:
		_add_cover(t)
	_update_smoke()
	_update_lightning()
	_build_slots()
	if "--perf" in OS.get_cmdline_user_args():
		print("PERF retile %d tile(s), %d rebuilt%s: %d ms" % [changes.size(), touched.size(),
				", water redrawn" if water_changed else "", (Time.get_ticks_usec() - t0) / 1000])


## Works out a finished region's trails to its landmark (LandmarkFlow.flow and turn), once, when it finishes.
## Call before retiling the region, so its tiles pick their trail and near pieces.
func set_flow(region: Array, landmark: Vector2i) -> void:
	var f := LandmarkFlow.flow(region, landmark)
	flow_dist.merge(f.dist, true)
	flow_toward.merge(f.toward, true)
	landmark_turns[landmark] = LandmarkFlow.turn(landmark, f.dist, f.toward)


## Works out the fence gates; returns the tiles whose gates changed, as they need rebuilding.
func _update_gates() -> Dictionary:
	var by_terrain := {}
	for t: Vector2i in terrains:
		by_terrain[t] = Variants.terrain_of(terrains[t])
	var now := FenceGates.gates(by_terrain, raised, climbs)
	var changed := {}
	for t: Vector2i in now:
		if now[t] != gates.get(t, []):
			changed[t] = true
	gates = now
	return changed


## Works out the village streets; returns the tiles whose streets changed, as they need rebuilding.
func _update_streets() -> Dictionary:
	var by_terrain := {}
	var trails := {}
	for t: Vector2i in terrains:
		by_terrain[t] = Variants.terrain_of(terrains[t])
		if by_terrain[t] == VillageStreets.VILLAGE:
			for i in LandmarkFlow.trail_edges(t, flow_toward):
				trails[[t, i]] = true
	var now := VillageStreets.streets(by_terrain, trails)
	var changed := {}
	for t: Vector2i in now:
		if now[t] != streets.get(t):
			changed[t] = true
	streets = now
	return changed


## Whether a party can step between neighbours a and b: fences are only crossed through a gate (DOCS: Walking), a
## cliff only by its ledge, and from one village tile to the next only by a street.
func edge_open(a: Vector2i, b: Vector2i) -> bool:
	if raised.has(a) != raised.has(b):
		return not climb_between(a, b).is_empty()
	if streets.has(a) and streets.has(b):
		return streets[a].has(Hex.NEIGHBOURS.find(b - a))
	if gates.has(a) == gates.has(b):
		return true
	var fenced := a if gates.has(a) else b
	var other := b if gates.has(a) else a
	return Hex.NEIGHBOURS.find(other - fenced) in gates[fenced]


## Works out which tiles are raised, their cliffs and ledges; returns the raised tiles whose cliffs changed.
func _update_raised() -> Dictionary:
	var before := _shape
	_shape = {}
	raised.clear()
	climbs.clear()
	_outer.clear()
	_corners.clear()
	_ledges.clear()
	_links.clear()
	for key in raised_regions:
		for t: Vector2i in raised_regions[key]:
			raised[t] = true
	if raised.is_empty():
		return {}
	var by_terrain := {}
	for t: Vector2i in terrains:
		by_terrain[t] = Variants.terrain_of(terrains[t])
	for key in raised_regions:
		var region: Array = raised_regions[key]
		for e in Cliffs.outer_edges(region, raised):
			_outer.get_or_add(e[0], []).append(e[1])
		climbs.append_array(Cliffs.climbs(region, by_terrain, raised))
	if party_at != null and raised.has(party_at):
		var plateau := _plateau(party_at)
		if not climbs.any(func(c): return c[0] in plateau):
			var down := Cliffs.forced_climb(plateau, by_terrain, raised)
			if not down.is_empty():
				climbs.append(down)
	for c in climbs:
		var t: Vector2i = c[0]
		var i: int = c[1]
		_ledges[t] = {posmod(i - 1, 6): "low", i: "mid", (i + 1) % 6: "top"}
		var low := Cliffs.beside(t, i - 1)
		_links[Vector4i(t.x, t.y, low.x, low.y)] = c
		_links[Vector4i(low.x, low.y, t.x, t.y)] = c
	for key in raised_regions:
		for e in Cliffs.outer_corners(raised_regions[key], raised):
			# No pinnacle at corners i - 1, i and i + 1 of a ledge: the same keys as its edges.
			if not _ledges.get(e[0], {}).has(e[1]):
				_corners.get_or_add(e[0], []).append(e[1])
	var changed := {}
	for t: Vector2i in raised:
		_shape[t] = [_outer.get(t, []).duplicate(), _corners.get(t, []).duplicate(), _ledges.get(t, {}).duplicate()]
		_shape[t][0].sort()
		_shape[t][1].sort()
		if _shape[t] != before.get(t):
			changed[t] = true
	return changed


## The raised tiles joined to t.
func _plateau(t: Vector2i) -> Array:
	var out: Array = [t]
	var seen := {t: true}
	var k := 0
	while k < out.size():
		for n in Hex.NEIGHBOURS:
			var c: Vector2i = out[k] + n
			if raised.has(c) and not seen.has(c):
				seen[c] = true
				out.append(c)
		k += 1
	return out


## The party has stopped on a tile: its way down, if it needs one, shows, and one it has left behind goes.
func party_moved(t: Vector2i) -> void:
	party_at = t
	if raised_regions.is_empty():
		return
	var touched := _update_raised()
	touched.merge(_update_gates())
	for c: Vector2i in touched:
		_build_tile(c)
		_add_cover(c)
	_update_smoke()


## Registers a region as raised and standing (the debug spawn: it needs no rise). Call before retiling it.
func set_raised(key: Variant, tiles: Array) -> void:
	raised_regions[key] = tiles.duplicate()
	for t: Vector2i in tiles:
		lift[t] = Variants.RAISE


## A region starts to rise, or grows. Its new tiles are built on their cliffs at the bottom of the rise; other raised
## tiles whose cliffs change keep their old pieces until finish_rise, so nothing opens up under them meanwhile.
## Returns {rising, later}.
func begin_rise(key: Variant, tiles: Array) -> Dictionary:
	raised_regions[key] = tiles.duplicate()
	var rising := tiles.filter(func(t): return not lift.has(t))
	var changed := _update_raised()
	var low := _update_gates()
	for t: Vector2i in rising:
		lift[t] = 0.0
		changed.erase(t)
		low.erase(t)
		_build_tile(t)
		_clip_cliffs(t, true)
	for t: Vector2i in low:
		changed.erase(t)
		_build_tile(t)
		_add_cover(t)
	_update_smoke()
	return {rising = rising, later = changed.keys()}


func set_lift(tiles: Array, y: float) -> void:
	for t: Vector2i in tiles:
		lift[t] = y
		tile_node(t).position.y = y


func finish_rise(r: Dictionary) -> void:
	set_lift(r.rising, Variants.RAISE)
	for t: Vector2i in r.rising:
		_clip_cliffs(t, false)
	for t: Vector2i in r.later:
		_build_tile(t)
	_update_smoke()


## Cuts a rising tile's cliff pieces off below the board's soil, or stops.
func _clip_cliffs(t: Vector2i, on: bool) -> void:
	var cliffs := tile_node(t).get_node_or_null("cliffs")
	if cliffs == null:
		return
	for mi: MeshInstance3D in cliffs.get_children():
		for k in mi.mesh.get_surface_count():
			mi.set_surface_override_material(k, _clip_of(mi.mesh.surface_get_material(k), t) if on else null)


func _clip_of(m: Material, t: Vector2i) -> ShaderMaterial:
	var key = [m, terrains[t]] if m == _ground else m
	if not _clip_mats.has(key):
		var c := ShaderMaterial.new()
		c.shader = load("res://shaders/cliff_rise.gdshader")
		var tint := Color.WHITE
		if m == _ground:
			tint = Hex.colour(Variants.GROUND[terrains[t]])
		elif m is BaseMaterial3D and not (m as BaseMaterial3D).vertex_color_use_as_albedo:
			tint = (m as BaseMaterial3D).albedo_color
		c.set_shader_parameter("tint", tint)
		_clip_mats[key] = c
	return _clip_mats[key]


## The climb between neighbours a and b ([tile, i]: its ledge rounds edges i - 1, i and i + 1 of tile), or [].
func climb_between(a: Vector2i, b: Vector2i) -> Array:
	return _links.get(Vector4i(a.x, a.y, b.x, b.y), [])


## The ledge of a climb from the foot up to where it comes out on the plateau: (plan x, plan y, height) with its corners
## rounded, sampled like the route's curves.
func ledge_line(t: Vector2i, i: int) -> PackedVector3Array:
	var kit := Variants.wedges_of(terrains[t])
	var at := Hex.tile_position(t.x, t.y)
	var corners := PackedVector3Array()
	var turn := i - 1
	for part in ["_cliff_path_low", "_cliff_path_mid", "_cliff_path_top"]:
		for poly in Kit.path_data(kit + part).paths:
			for p in poly:
				var plan := at + Vector2(p[0], -p[2]).rotated(deg_to_rad(60.0 * turn))
				var q := Vector3(plan.x, plan.y, p[1])
				if corners.is_empty() or corners[-1].distance_to(q) > 0.05:
					corners.append(q)
		turn += 1
	var out := PackedVector3Array([corners[0]])
	for k in range(1, corners.size()):
		var a := corners[k - 1]
		var b := corners[k]
		var r := minf(Rules.PATH_CORNER, a.distance_to(b) * 0.4)
		var to := b - (b - a).normalized() * r if k < corners.size() - 1 else b
		_ledge_run(out, to)
		if k < corners.size() - 1:
			var c := corners[k + 1]
			var off := b + (c - b).normalized() * minf(Rules.PATH_CORNER, b.distance_to(c) * 0.4)
			var from := out[-1]
			for u in range(1, 7):
				var w := u / 6.0
				out.append(from.lerp(b, w).lerp(b.lerp(off, w), w))
	return out


static func _ledge_run(out: PackedVector3Array, to: Vector3) -> void:
	var from := out[-1]
	var n := maxi(1, ceili(from.distance_to(to) / 0.25))
	for k in range(1, n + 1):
		out.append(from.lerp(to, float(k) / n))


## Whether a plan point on raised ground is too near a cliff's lip to walk or stand on.
func near_lip(p: Vector2) -> bool:
	var t := GroundCover.tile_at(p)
	if not raised.has(t):
		return false
	var local := p - Hex.tile_position(t.x, t.y)
	for i: int in _outer.get(t, []):
		if Hex.A - local.dot(Water.normal(i)) < Rules.LIP_CLEAR:
			return true
	return false


## How high a camera over this plan point must stay to clear the ground and what stands on it.
func camera_floor(p: Vector2) -> float:
	return Variants.RAISE + 5.45 if raised.has(GroundCover.tile_at(p)) else 0.0   # the kit's tallest: snowy's corner mountain


## One smoke per crater: a volcano's parts on two or three tiles each carry its point (hills kit -> Effects).
func _update_smoke() -> void:
	var seen := {}
	for t: Vector2i in _tile_nodes:
		if terrains.get(t) != "volcanic_peaks":
			continue
		var node: Node3D = _tile_nodes[t]
		for c in node.get_children():
			if c.name.begins_with("crater_smoke"):
				c.free()
		var at := Hex.tile_position(t.x, t.y)
		for mi in node.get_children():
			if not (mi is MeshInstance3D and mi.has_meta("piece")):
				continue
			for e in Kit.path_data(mi.get_meta("piece")).get("effects", []):
				if e.kind != "smoke":
					continue
				var p: Vector2 = Vector2(e.at[0], -e.at[2]).rotated(mi.rotation.y) + at
				var key := Vector2i((p * 5.0).round())
				if seen.has(key):
					continue
				seen[key] = true
				var fx := FarmFx.crater_smoke()
				fx.name = "crater_smoke"
				fx.position = Hex.to3(p, e.at[1])
				node.add_child(fx)


## Tile t's drawn paths (empty where its pieces have no path data).
func path_graph(t: Vector2i) -> TilePaths:
	if not _graphs.has(t):
		var pieces := []
		var node := tile_node(t)
		if node:
			for c in node.get_children():
				if c is MeshInstance3D and c.has_meta("piece") and not Kit.path_data(c.get_meta("piece")).is_empty():
					pieces.append([String(c.get_meta("piece")), posmod(roundi(rad_to_deg(c.rotation.y) / 60.0), 6)])
		_graphs[t] = TilePaths.build(pieces, Hex.tile_position(t.x, t.y))
	return _graphs[t]


## Whether the edge between neighbours a and b is a landmark trail edge with a drawn trail. Plains variants have
## no trail pieces: they flow by density, so the party keeps its usual curved route there. Hills trail pieces only
## show the way; monastery's have path data, which the route follows anyway.
func trail_edge(a: Vector2i, b: Vector2i) -> bool:
	if not (flow_toward.get(a) == b or flow_toward.get(b) == a):
		return false
	if Variants.terrain_of(terrains.get(a)) == "hills":
		return false
	return _has_trail(terrains.get(a)) or _has_trail(terrains.get(b))


func _has_trail(name) -> bool:
	return name != null and (_kit.has(name + "_edge_trail") or _kit.has(Variants.wedges_of(name) + "_edge_trail"))


## The ground cover of tile t, kept off its and its neighbours' pieces' no_cover circles (plans, world space).
func _add_cover(t: Vector2i) -> void:
	if raised.has(t):
		return   # raised ground holds no cover, not even tufts fading in from neighbours
	var clear := []
	for c: Vector2i in [t, t + Hex.NEIGHBOURS[0], t + Hex.NEIGHBOURS[1], t + Hex.NEIGHBOURS[2], t + Hex.NEIGHBOURS[3],
			t + Hex.NEIGHBOURS[4], t + Hex.NEIGHBOURS[5]]:
		var node := tile_node(c)
		if node == null:
			continue
		for mi in node.get_children():
			if mi is MeshInstance3D and mi.has_meta("piece"):
				for circle in Kit.path_data(mi.get_meta("piece")).get("no_cover", []):
					var p := Hex.tile_position(c.x, c.y) + Vector2(circle.at[0], -circle.at[2]).rotated(mi.rotation.y)
					clear.append([p.x, p.y, circle.r])
	tile_node(t).add_child(GroundCover.build_tile(terrains, water_shapes, t, clear))


func _update_lightning() -> void:
	var stormy: Array[Vector2i] = []
	for t: Vector2i in terrains:
		if terrains[t] in ["stormy_plains", "thunderbirdnest"]:
			stormy.append(t)
	if lightning == null and not stormy.is_empty():
		lightning = Lightning.new()
		lightning.name = "lightning"
		add_child(lightning)
	if lightning:
		lightning.tiles = stormy


## The plan angle a landmark tile's entrance faces (its centre piece's edge 0, turned), or NAN if t isn't one.
func entrance_angle(t: Vector2i) -> float:
	if not Variants.LANDMARKS.has(terrains.get(t)):
		return NAN
	return deg_to_rad(60.0 * landmark_turns.get(t, 0))


## The node holding tile t's pieces (for transitions).
func tile_node(t: Vector2i) -> Node3D:
	return _tile_nodes.get(t)


func _setup() -> void:
	_kit = Kit.meshes("res://art/tiles.glb")
	_ground_img = Image.create(64, 64, false, Image.FORMAT_RGBA8)
	_ground_img.fill(Color(0, 0, 0, 0))
	_ground_tex = ImageTexture.create_from_image(_ground_img)
	_ground = ShaderMaterial.new()
	_ground.shader = load("res://shaders/ground.gdshader")
	_ground.set_shader_parameter("terrain_map", _ground_tex)
	_ground.set_shader_parameter("blend_width", BLEND_WIDTH)
	var p := Piece.new()
	var hexagon := Hex.hex_corners(Hex.R * 0.94, true)
	hexagon.reverse()
	p.offset = Vector3(0, 0, -0.3)
	p.flat(hexagon, 0.02, Hex.colour("slot"))
	_slot_mesh = p.mesh()
	_slot_mat = Piece.material()
	_setup_materials()


## Engine-side looks the art leaves to us: still water for the swamp's pools (PLACEHOLDER: a glossy
## material, not a shader), toadstools and lanterns that glow at night, and the bog's mist material.
func _setup_materials() -> void:
	_still_water = StandardMaterial3D.new()
	_still_water.roughness = 0.12
	_still_water.metallic_specular = 0.9
	_glow = StandardMaterial3D.new()
	_glow.albedo_color = Hex.colour("toadstool")
	_glow.emission_enabled = true
	_glow.emission = Hex.colour("toadstool")
	_glow.emission_energy_multiplier = 0.0
	_lamp = _glow.duplicate() as StandardMaterial3D
	_lamp.albedo_color = Hex.colour("lantern")
	_lamp.emission = Hex.colour("lantern")
	for mesh: Mesh in _kit.values():
		for k in mesh.get_surface_count():
			var name := Kit.material_name(mesh, k)
			if name in ["hill_grass", "highland_grass", "snow_ground", "ash_ground"]:
				# tiles v10: the hills pieces' ground (they cover the base slab) fades like the base slabs' tops
				mesh.surface_set_material(k, _ground)
				continue
			if name in ["bog_water", "bog_dark"]:
				var m := _still_water.duplicate() as StandardMaterial3D
				m.albedo_color = (mesh.surface_get_material(k) as BaseMaterial3D).albedo_color
				mesh.surface_set_material(k, m)
			elif name == "toadstool":
				mesh.surface_set_material(k, _glow)
			elif name == "lantern":
				mesh.surface_set_material(k, _lamp)
			elif name == "kit":
				# tiles v9: one shared material, the colours in the vertex colours (glTF COLOR_0, linear)
				var m := mesh.surface_get_material(k) as BaseMaterial3D
				m.vertex_color_use_as_albedo = true
				m.albedo_color = Color.WHITE
	# Tiles v23 (forest kit): the fairy rings and the Fey Court's windows glow at night; webs are see-through.
	_fey = _glow.duplicate() as StandardMaterial3D
	_fey.albedo_color = Hex.colour("fey_mushroom")
	_fey.emission = Hex.colour("fey_mushroom")
	_window = _glow.duplicate() as StandardMaterial3D
	_window.albedo_color = Hex.colour("window_glow")
	_window.emission = Hex.colour("window_glow")
	_faint = _glow.duplicate() as StandardMaterial3D
	_faint.albedo_color = Hex.colour("window_faint")
	_faint.emission = Hex.colour("window_faint")
	_lantern_red = _glow.duplicate() as StandardMaterial3D
	_lantern_red.albedo_color = Hex.colour("lantern_red")
	_lantern_red.emission = Hex.colour("lantern_red")
	_lava = _glow.duplicate() as StandardMaterial3D
	_lava.albedo_color = Hex.colour("lava")
	_lava.emission = Hex.colour("lava")
	_web = StandardMaterial3D.new()
	_web.albedo_color = Color(Hex.colour("web"), 0.3)   # hexkit.WEB_ALPHA
	_web.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_web.cull_mode = BaseMaterial3D.CULL_DISABLED
	for mesh: Mesh in _kit.values():
		for k in mesh.get_surface_count():
			match Kit.material_name(mesh, k):
				"fey_mushroom": mesh.surface_set_material(k, _fey)
				"window_glow": mesh.surface_set_material(k, _window)
				"web": mesh.surface_set_material(k, _web)
				"window_faint": mesh.surface_set_material(k, _faint)
				"lava": mesh.surface_set_material(k, _lava)
				"lantern_red": mesh.surface_set_material(k, _lantern_red)
	_mist_mat = ShaderMaterial.new()
	_mist_mat.shader = load("res://shaders/mist.gdshader")


## A bog tile's low mist: two flat layers of drifting haze (PLACEHOLDER heights and look; three layers at
## 0.3 strength hid the bog at dawn and dusk).
func _mist(at: Vector2) -> Node3D:
	var node := Node3D.new()
	node.name = "mist"
	for k in 2:
		var mi := MeshInstance3D.new()
		var quad := PlaneMesh.new()
		quad.size = Vector2(9.5, 10.5)
		mi.mesh = quad
		var m := _mist_mat.duplicate() as ShaderMaterial
		m.set_shader_parameter("layer", float(k))
		mi.material_override = m
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.position = Hex.to3(at, 0.15 + 0.2 * k)
		node.add_child(mi)
	return node


## Ground colour per tile in a small lookup texture; the shader fades it toward the neighbours.
## The colour of each terrain is the top material of its base slab in the kit.
func _set_ground(t: Vector2i) -> void:
	var name: String = terrains[t]
	var c: Color
	if Variants.GROUND.has(name):
		c = Hex.colour(Variants.GROUND[name])
	elif name == "hills":
		c = Hex.colour("hill_grass")   # the mound's grass covers the whole tile, so that's the ground to fade
	else:
		c = ((_kit["base_" + name] as Mesh).surface_get_material(0) as BaseMaterial3D).albedo_color
	_ground_img.set_pixel(t.x + 32, t.y + 32, Color(c.r, c.g, c.b, 1))
	_ground_tex.update(_ground_img)


func _build_tile(t: Vector2i) -> void:
	tiles_built += 1
	if _tile_nodes.has(t):
		_tile_nodes[t].free()
	_graphs.erase(t)
	var node := Node3D.new()
	node.name = "tile_%d_%d" % [t.x, t.y]
	add_child(node)
	_tile_nodes[t] = node
	# name is a terrain or a region variant; the variant's pieces carry its name, and edge pieces are
	# picked by its terrain.
	var name: String = terrains[t]
	var terrain := Variants.terrain_of(name)
	var at := Hex.tile_position(t.x, t.y)
	var high := raised.has(t)
	node.position.y = lift.get(t, 0.0)
	if not high:   # raised ground covers the tile, and a base's soil would stick out of the cliff
		var base := Kit.place(node, _kit, "base_" + terrain, at)   # variants recolour their terrain's base
		base.set_surface_override_material(0, _ground)
	if terrain == "river":
		return
	var centre := "_centre"
	if flow_dist.get(t) == 1 and _kit.has(name + "_centre_near"):
		centre = "_centre_near"  # next to the landmark: the variant's look played up
	elif flow_dist.get(t) == 2 and _kit.has(name + "_centre_mid"):
		centre = "_centre_mid"   # two steps from the landmark: on the way to it
	if centre == "_centre" and _kit.has(name + "_centre_b") and GroundCover.hash01(t.x, t.y, 13) < 0.5:
		centre = "_centre_b"     # a second version of the centre, so a big group doesn't repeat
	if _kit.has(name + "_centre_mill") and GroundCover.hash01(t.x, t.y, 7) < 0.5:
		centre = "_centre_mill"  # windmills stand on about half the tiles (the preview's placeholder rule)
	# A landmark's centre turns so its entrance (edge 0) faces its longest trail; a farm's turns by a hash of the
	# tile, so yards don't line up. Wedges stay put.
	var turn: int = landmark_turns.get(t, 0)
	if _kit.has(name + "_centre_b"):
		turn = int(GroundCover.hash01(t.x * 31 + 7, t.y * 17 + 3, 14) * 6)
	if centre in ["_centre_mid", "_centre_near"] and _kit.has(name + "_centre_mid"):
		turn = LandmarkFlow.toward_edge(t, flow_toward)   # density bands lean toward the landmark
	var spin := deg_to_rad(60.0 * turn)
	Kit.place(node, _kit, name + centre, at, spin)
	if centre == "_centre_mill":   # the small mill goes where the turned yard is, but doesn't turn itself
		Kit.place(node, _kit, "windmill_small", at + Variants.SMALL_MILL_SPOT.rotated(spin))
	if name == "greatwindmill":
		node.add_child(_sails(at, spin))
	var farm_fx := FarmFx.for_piece(name + centre, at, turn) if terrain != "village" else null   # towns: _town_smoke
	if farm_fx:
		node.add_child(farm_fx)
	if terrain == "desert":
		node.add_child(Sand.build_tile(terrains, t))
	if name == "bog":
		node.add_child(_mist(at))
	var fx := ForestFx.for_tile(name, at, t, landmark_turns.get(t, 0))
	if fx:
		node.add_child(fx)
	var joined := []
	for n in Hex.NEIGHBOURS:
		joined.append(linked(name, terrains.get(t + n)))
	if terrain == "hills":
		# One mountain per group: a lone tile's own peak; a third on each corner where three hills tiles
		# meet; otherwise half on each edge shared with one other hills tile. A landmark has none of this, its
		# neighbours leave it out, and no mountain stands on a trail edge, so the range opens into a pass.
		var clear_near: bool = flow_dist.get(t, 3) > 2
		if not Variants.LANDMARKS.has(name) and clear_near and not range(6).any(func(i): return _ranges(t, i)):
			Kit.place(node, _kit, name + "_peak", at)
		var parts := _mountain_parts(t)
		for part in parts:
			Kit.place(node, _kit, name + "_mountain_" + part[0], at, deg_to_rad(60.0 * part[1]))
		# In bigger groups the mountains join into a range: ridges from this tile's middle to each of them. None
		# within two steps of a landmark (clear ground), nor where steps run (they'd bury them).
		if parts.size() >= 2 and clear_near and not _kit.has(Variants.wedges_of(name) + "_steps_centre"):
			Kit.place(node, _kit, name + "_ridge_knot", at)
			for part in parts:
				Kit.place(node, _kit, name + "_ridge_" + part[0], at, deg_to_rad(60.0 * part[1]))
	var kit := Variants.wedges_of(name)   # a centre-only landmark takes its variant's wedges
	# Stone walls in place of the fence, at the edges of the region itself (fortified town): a neighbour that's a plain
	# village or farm is walled off too, so it doesn't carry the border on.
	var walled: bool = _kit.has(kit + "_border_join_l")
	var kin := []
	for i in 6:
		var near = terrains.get(t + Hex.NEIGHBOURS[i])
		kin.append(joined[i] and (not walled or Variants.wedges_of(near) == kit))
	var trails := LandmarkFlow.trail_edges(t, flow_toward)
	for i in 6:
		var angle := deg_to_rad(60.0 * i)
		var edge := _edge_piece(t, name, kit, i, joined[i], trails)
		if i in _outer.get(t, []):
			var part: String = _ledges.get(t, {}).get(i, "")
			edge = kit + {"low": "_edge_climb_low", "mid": "_edge_climb", "top": "_edge_climb_top", "": "_edge_rim"}[part]
		Kit.place(node, _kit, edge, at, angle)
		if i in trails and _kit.has(kit + "_steps_centre"):   # the stair's flight on the centre, one per trail edge
			if not Variants.LANDMARKS.has(name):
				Kit.place(node, _kit, kit + "_steps_centre", at, angle)
			elif i != landmark_turns.get(t, 0):   # the entrance edge's steps are in the landmark's own piece
				Kit.place(node, _kit, kit + "_steps_rise", at, angle)
		# Carry a neighbouring edge's border out to this joined edge, so borders run on between tiles.
		if terrain in BORDERED and kin[i]:
			var join := kit + "_border_join" if walled else "border_join"
			if not kin[(i + 1) % 6]:
				Kit.place(node, _kit, join + "_l", at, angle)
			if not kin[posmod(i - 1, 6)]:
				Kit.place(node, _kit, join + "_r", at, angle)
	if terrain == "village":
		_town_smoke(node, at)
	if terrain in ["hills", "desert"]:
		_add_ground_collision(node, terrain == "hills", high)
	if high:
		_add_cliffs(t, node, kit, at)


## The shared mountains on tile t: ["corner", i] where corner i has one, ["edge", i] where edge i has.
func _mountain_parts(t: Vector2i) -> Array:
	var ranged := []
	var triple := []
	for i in 6:
		ranged.append(_ranges(t, i))
	for i in 6:   # corner i: between edges i and i + 1; every copy of the third must be drawn
		triple.append(ranged[i] and ranged[(i + 1) % 6] and _ranges(t + Hex.NEIGHBOURS[i], (i + 2) % 6))
	var parts := []
	for i in 6:
		if triple[i]:
			parts.append(["corner", i])
		elif ranged[i] and not triple[posmod(i - 1, 6)]:
			parts.append(["edge", i])
	return parts


## Whether ridges wall edge a of tile t off from edge b: ridges run from the middle out to each mountain, so one on
## each side of the way between them makes a wall (hills kit -> Still not working: far ridges).
func ridge_wall(t: Vector2i, a: int, b: int) -> bool:
	var name = terrains.get(t)
	if Variants.terrain_of(name) != "hills" or flow_dist.get(t, 3) <= 2 or _kit.has(Variants.wedges_of(name) + "_steps_centre"):
		return false
	var parts := _mountain_parts(t)
	if parts.size() < 2:
		return false
	var left := false
	var right := false
	var span := float(posmod(b - a, 6))
	for part in parts:
		var at := fposmod(float(part[1]) + (0.5 if part[0] == "corner" else 0.0) - a, 6.0)
		if at > 0.0 and at < span:
			left = true
		elif at > span:
			right = true
	return left and right


## A town tile's chimneys, from its centre and wedges, in one particle node.
func _town_smoke(node: Node3D, at: Vector2) -> void:
	var points := []
	for mi in node.get_children():
		if mi is MeshInstance3D and mi.has_meta("piece"):
			for e in Kit.path_data(mi.get_meta("piece")).get("effects", []):
				if e.kind == "smoke":
					var p: Vector2 = Vector2(e.at[0], -e.at[2]).rotated(mi.rotation.y) + at
					points.append(Hex.to3(p, e.at[1]))
	if not points.is_empty():
		var fx := FarmFx.town_smoke(points)
		fx.name = "town_smoke"
		node.add_child(fx)


## Do tile t and its neighbour on edge i share a mountain? (render_preview.build_map: ranges)
func _ranges(t: Vector2i, i: int) -> bool:
	var n: Vector2i = t + Hex.NEIGHBOURS[i]
	var a = terrains.get(t)
	var b = terrains.get(n)
	return linked(a, b) and not i in LandmarkFlow.trail_edges(t, flow_toward) and not Variants.LANDMARKS.has(a) \
			and not Variants.LANDMARKS.has(b)


## The cliffs round a raised tile, at ground level whatever height the tile stands at: they're children of the tile's
## node at -RAISE, so they come up with it, and their lip stays on its ground.
func _add_cliffs(t: Vector2i, node: Node3D, kit: String, at: Vector2) -> void:
	if not _outer.has(t):
		return
	var cliffs := Node3D.new()
	cliffs.name = "cliffs"
	cliffs.position.y = -Variants.RAISE
	node.add_child(cliffs)
	for i: int in _outer[t]:
		var part: String = _ledges.get(t, {}).get(i, "")
		var piece := "_cliff_path_" + part if part != "" else "_cliff_edge_b" if GroundCover.hash01(t.x * 6 + i, t.y, 8) < 0.5 else "_cliff_edge"
		Kit.place(cliffs, _kit, kit + piece, at, deg_to_rad(60.0 * i))
	for i: int in _corners.get(t, []):
		Kit.place(cliffs, _kit, kit + "_cliff_corner", at, deg_to_rad(60.0 * i))


## The Great Windmill's sails, at its hub (variants.MILL_HUB) turned with the landmark, spinning about their own X.
func _sails(at: Vector2, spin: float) -> Spinner:
	var s := Spinner.new()
	s.name = "sails"
	s.axis = Vector3.RIGHT
	s.speed = Rules.SAIL_SPEED
	var hub := Vector2(Variants.MILL_HUB.x, Variants.MILL_HUB.y).rotated(spin)
	s.position = Hex.to3(at + hub, Variants.MILL_HUB.z)
	s.rotation.y = spin
	var mi := MeshInstance3D.new()
	mi.mesh = _kit["greatwindmill_sails"]
	s.add_child(mi)
	return s


## The wedge on edge i (render_preview.build_map, tiles v34): toward the Tree of Life, heartwood's landmark wedge;
## on a trail edge, the landmark's own trail wedge or its kit's (edge_trail_in on the tile closer to the landmark);
## on a gate edge, edge_gate; on a landmark's fence edge, edge_other_lm where it exists; on a joined edge, edge_same,
## or the alternate edge_same_b where the kit has one and hash01(q * 6 + i, r, 8) < 0.5; otherwise edge_other.
func _edge_piece(t: Vector2i, name: String, kit: String, i: int, joined: bool, trails: Array) -> String:
	var near = terrains.get(t + Hex.NEIGHBOURS[i])
	if joined and _kit.has(kit + "_border_join_l") and Variants.wedges_of(near) != kit:
		# A wall at the region's edge: a gatehouse where a street leaves it.
		if streets[t].has(i):
			return kit + "_edge_gate"
		return kit + ("_edge_other_lm" if Variants.LANDMARKS.has(name) else "_edge_other")
	if Variants.LANDMARKS.get(near) == name and _kit.has(name + "_edge_landmark"):
		return name + "_edge_landmark"
	if i in trails:
		if LandmarkFlow.heads_in(t, i, flow_dist) and _kit.has(kit + "_edge_trail_in"):
			return kit + "_edge_trail_in"
		if _kit.has(name + "_edge_trail"):
			return name + "_edge_trail"
		if _kit.has(kit + "_edge_trail"):
			return kit + "_edge_trail"
	if not joined and i in gates.get(t, []) and _kit.has(kit + "_edge_gate"):
		return kit + "_edge_gate"
	if not joined and _kit.has(kit + "_edge_other_b") and GroundCover.hash01(t.x * 6 + i, t.y, 8) < 0.5:
		return kit + "_edge_other_b"   # trees: a wedge facing other land is the only one clear of rock
	if not joined and Variants.LANDMARKS.has(name) and _kit.has(kit + "_edge_other_lm"):
		return kit + "_edge_other_lm"
	if joined and _kit.has(kit + "_edge_block"):   # a town: a street only where this edge has one
		match streets[t].get(i, ""):
			"main": return kit + "_edge_same"
			"side": return kit + "_edge_side"
		if Variants.LANDMARKS.has(name) and _kit.has(kit + "_edge_block_lm"):
			return kit + "_edge_block_lm"   # without the house toward the middle: the landmark's yard lies there
		return kit + "_edge_block"
	if joined and _kit.has(kit + "_edge_same_b") and GroundCover.hash01(t.x * 6 + i, t.y, 8) < 0.5:
		return kit + "_edge_same_b"
	return kit + ("_edge_same" if joined else "_edge_other")


## Collision for the ground the party walks on (PartyWalker.ground raycasts it): the hills pieces' grass
## (their `hill_grass` / `highland_grass` surfaces, not their trees or rocks), whole peaks, mountains and ridges,
## and the desert's sand. Everything else is flat at height 0. Peaks, mountains and ridges are marked, so the
## party's route goes round them.
static var _shapes := {}


func _add_ground_collision(node: Node3D, hills: bool, high: bool) -> void:
	for c in node.get_children():
		if not c is MeshInstance3D:
			continue
		var mi := c as MeshInstance3D
		var n: String = mi.get_meta("piece", String(mi.name))   # not the node name: repeats are renamed
		var whole := n == "sand" or n.ends_with("_peak") or "_mountain_" in n or "_ridge_" in n
		if not whole and not hills:
			continue
		var key := [mi.mesh, whole]
		if not _shapes.has(key):
			var faces := PackedVector3Array()
			for k in mi.mesh.get_surface_count():
				if whole or mi.mesh.surface_get_material(k) == _ground:   # the hills' grass (_setup_materials)
					var arrays := mi.mesh.surface_get_arrays(k)
					var v: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
					var idx = arrays[Mesh.ARRAY_INDEX]
					if idx is PackedInt32Array and idx.size() > 0:
						for q in idx:
							faces.append(v[q])
					else:
						faces.append_array(v)
			var shape := ConcavePolygonShape3D.new()
			shape.set_faces(faces)
			_shapes[key] = shape if faces.size() > 0 else null
		if _shapes[key] == null:
			continue
		var body := StaticBody3D.new()
		var cs := CollisionShape3D.new()
		cs.shape = _shapes[key]
		body.set_meta("mountain", whole and n != "sand")   # the party walks round these (PartyWalker.blocked)
		body.collision_layer = 2 if high else 1            # raised ground, felt only by a mini up there
		body.add_child(cs)
		mi.add_child(body)


# --- Water -------------------------------------------------------------------

func _update_water() -> void:
	water_shapes.clear()
	for t: Vector2i in terrains:
		if Variants.is_water(terrains[t]):
			var near := []
			var mask := []
			for n in Hex.NEIGHBOURS:
				near.append(terrains.get(t + n))
				mask.append(Variants.is_water(near[-1]))
			var w := Water.tile_water(mask, "%d,%d" % [t.x, t.y], Water.edge_widths(terrains[t], near))
			w.delta = terrains[t] == "delta"
			water_shapes[t] = w
	if _water_node:
		_water_node.free()
	boats.clear()
	_water_node = Node3D.new()
	_water_node.name = "water"
	add_child(_water_node)
	if not water_shapes.is_empty():
		_build_water()


func _build_water() -> void:
	var dressing := Piece.new()
	var shores := []        # [world plan points, flow sign, speed]
	var outlines := []      # world plan outlines
	var bank := Hex.colour("bank")
	for t: Vector2i in water_shapes:
		var w: Dictionary = water_shapes[t]
		var at := Hex.tile_position(t.x, t.y)
		var seed := "%d,%d" % [t.x, t.y]
		var h := Water.downhill(t.x, t.y)
		var inflow := []
		for n in Hex.NEIGHBOURS:
			inflow.append(Water.downhill(t.x + n.x, t.y + n.y) < h)
		var speed := RIVER_SPEED if w.kind in ["river", "spring"] else LAKE_SPEED
		var signs := Water.flow_signs(w.ends, inflow)
		for k in w.shores.size():
			var pts := PackedVector2Array()
			for p in w.shores[k]:
				pts.append(at + p)
			shores.append([pts, signs[k], speed])
		for poly: PackedVector2Array in w.outlines:
			var pts := PackedVector2Array()
			for p in poly:
				pts.append(at + p)
			outlines.append(pts)
		# Banks and dressing (water.add_water with plates=False, boats=False)
		dressing.offset = Vector3(at.x, at.y, 0)
		for curve: PackedVector2Array in w.shores:
			for quad in Water.bank_strip(curve, 0.22):
				dressing.flat(quad, 0.025, bank)
		_add_dressing(dressing, w, seed, at)
	_water_node.add_child(dressing.instance("water_dressing"))
	var mi := MeshInstance3D.new()
	mi.name = "water_surface"
	mi.mesh = _water_mesh(outlines, shores)
	mi.material_override = load("res://shaders/water.tres")
	_water_node.add_child(mi)


func _add_dressing(p: Piece, w: Dictionary, seed: String, at: Vector2) -> void:
	var d := Water.dressing(w.outlines, w.shores, w.kind, seed)
	var rng := PyRandom.new(seed + "-props")
	for r: Vector2 in d.reeds:
		for _k in 3:
			var jx := rng.uniform(-0.12, 0.12)
			var jy := rng.uniform(-0.12, 0.12)
			p.cone(Vector3(r.x + jx, r.y + jy, 0), 0.05, rng.uniform(0.35, 0.6), Hex.colour("reed"), 4)
	for r: Vector2 in d.rocks:
		p.blob(Vector3(r.x, r.y, 0), rng.uniform(0.12, 0.2), Hex.colour("rock"), 0.0, 0.6)
	for r: Vector2 in d.lilies:
		p.cylinder(Vector3(r.x, r.y, 0), rng.uniform(0.14, 0.22), 0.02, Hex.colour("lily"), 7, 0.03)
	for j in d.jetties:
		var ang: float = j[1]
		var dir := Vector2(cos(ang), sin(ang))
		var tip: Vector2 = j[0] + dir * 0.7
		p.box(Vector3(tip.x, tip.y, 0), Vector3(1.6, 0.45, 0.06), Hex.colour("trunk"), 0.12, ang)
		for s in [-1, 1]:
			var post: Vector2 = tip + dir * (0.6 * s)
			p.cylinder(Vector3(post.x, post.y, 0), 0.05, 0.2, Hex.colour("trunk"))
	var boat_spots: Array = d.boats
	if w.get("delta", false):
		# The river delta's islands, boats, jetty and crates (water.add_water(..., delta=True)).
		var dd := Water.delta_dressing(w.outlines, w.shores, w.kind, seed)
		boat_spots = boat_spots + dd.boats
		for poly: PackedVector2Array in dd.islands:
			p.flat(poly, 0.036, Hex.colour("sandbar"))
			for k in range(0, poly.size(), 5):
				var q := (poly[k] + poly[0]) * 0.5
				p.cone(Vector3(q.x, q.y, 0), 0.05, rng.uniform(0.35, 0.55), Hex.colour("reed"), 4, 0.03)
		for j in dd.jetties:
			var ang: float = j[1]
			var dir := Vector2(cos(ang), sin(ang))
			var tip: Vector2 = j[0] + dir * 0.5
			p.box(Vector3(tip.x, tip.y, 0), Vector3(1.2, 0.45, 0.06), Hex.colour("trunk"), 0.12, ang)
			for s in [-1, 1]:  # cargo crates on the bank beside it
				var crate: Vector2 = j[0] - (dir * 0.45 + Vector2(-dir.y, dir.x) * (0.45 * s))
				p.box(Vector3(crate.x, crate.y, 0), Vector3(0.3, 0.3, 0.28), Hex.colour("crate"), 0.0, ang + 0.2 * s)
	# Boats are their own nodes so they can bob (render_animation.bob_boats).
	for b in boat_spots:
		var piece := Piece.new()
		var ang: float = b[1]
		piece.box(Vector3.ZERO, Vector3(0.9, 0.36, 0.14), Hex.colour("trunk"), 0.03, ang)
		piece.box(Vector3.ZERO, Vector3(0.5, 0.26, 0.06), Hex.colour("boat"), 0.17, ang)
		var boat := Node3D.new()
		boat.name = "boat"
		boat.position = Hex.to3(at + b[0])
		boat.add_child(piece.instance("hull"))
		_water_node.add_child(boat)
		boats.append(boat)


var _time := 0.0


func _process(delta: float) -> void:
	_time += delta   # engine time, so movie recordings at a fixed frame rate stay in step
	if time_of_day and _glow and time_of_day.sun:
		# Toadstools glow as the light fades (PLACEHOLDER strength): 0 at midday, full at night.
		var night := clampf((1.18 - time_of_day.sun.light_energy) / (1.18 - 0.35), 0.0, 1.0)
		_glow.emission_energy_multiplier = 2.5 * night
		_lamp.emission_energy_multiplier = 0.3 + 3.5 * night   # PLACEHOLDER: lit a little by day, bright at night
		_fey.emission_energy_multiplier = 0.15 + 1.6 * night   # PLACEHOLDER: "glow softly at night"
		_window.emission_energy_multiplier = 0.4 + 3.0 * night  # PLACEHOLDER: warm light inside
		_faint.emission_energy_multiplier = 0.1 + 0.9 * night   # PLACEHOLDER: dimmer than the windows
		_lantern_red.emission_energy_multiplier = 0.3 + 3.5 * night   # PLACEHOLDER: like the lanterns
		_lava.emission_energy_multiplier = (0.75 + 0.25 * sin(TAU * _time / 4.0)) * (0.8 + 2.0 * night)   # PLACEHOLDER: pulses slowly, glows at night
		ForestFx.set_night(night)
		(load("res://shaders/water.tres") as ShaderMaterial).set_shader_parameter("night", night)
	var s := _time
	for k in boats.size():
		boats[k].position.y = 0.03 * sin(TAU * s / 2.0 + k)
		boats[k].rotation.x = 0.05 * sin(TAU * s / 3.0 + k)


static func _seg_dist(p: Vector2, a: Vector2, b: Vector2) -> float:
	var ab := b - a
	var l2 := ab.length_squared()
	var t := clampf((p - a).dot(ab) / (l2 if l2 != 0.0 else 1.0), 0.0, 1.0)
	return (p - (a + ab * t)).length()


## One mesh for all water, with depth (UV.x) and flow (UV2, world XZ) per vertex, like
## render_animation.water_mesh(): outline points, a staggered grid inside, Delaunay triangles.
func _water_mesh(outlines: Array, shores: Array) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for raw: PackedVector2Array in outlines:
		var poly := PackedVector2Array()
		for k in raw.size():
			var a := raw[k]
			var b := raw[(k + 1) % raw.size()]
			var steps := maxi(1, int((b - a).length() / GRID))
			for j in steps:
				poly.append(a.lerp(b, float(j) / steps))
		var pts := poly.duplicate()
		var lo := Vector2(INF, INF); var hi := Vector2(-INF, -INF)
		for p in poly:
			lo = lo.min(p); hi = hi.max(p)
		var y := lo.y + GRID / 2
		while y < hi.y:
			var x := lo.x + GRID / 2 + (GRID / 2 if int((y - lo.y) / GRID) % 2 else 0.0)
			while x < hi.x:
				var p := Vector2(x, y)
				if Water.point_in(poly, p) and _min_dist(p, poly) > GRID * 0.4:
					pts.append(p)
				x += GRID
			y += GRID
		# Godot has no constrained Delaunay: triangulate all points, keep triangles inside the outline.
		var tris := Geometry2D.triangulate_delaunay(pts)
		for k in range(0, tris.size(), 3):
			var a := pts[tris[k]]; var b := pts[tris[k + 1]]; var c := pts[tris[k + 2]]
			if not Water.point_in(poly, (a + b + c) / 3.0):
				continue
			if (b - a).cross(c - a) < 0:
				var tmp := b; b = c; c = tmp
			for p in [a, c, b]:   # clockwise for Godot's front face
				var df := _depth_flow(p, shores)
				st.set_uv(Vector2(df.x, 0))
				st.set_uv2(Vector2(df.y, df.z))
				st.set_normal(Vector3.UP)
				st.add_vertex(Hex.to3(p, 0.03))
	return st.commit()


static func _min_dist(p: Vector2, poly: PackedVector2Array) -> float:
	var best := INF
	for k in poly.size():
		best = minf(best, _seg_dist(p, poly[k - 1], poly[k]))
	return best


## Distance to the nearest shore, and the flow there (x, z in Godot world).
static func _depth_flow(p: Vector2, shores: Array) -> Vector3:
	var best := INF
	var tangent := Vector2.ZERO
	var sign := 0
	var speed := 0.0
	for s in shores:
		var pts: PackedVector2Array = s[0]
		for k in range(1, pts.size()):
			var d := _seg_dist(p, pts[k - 1], pts[k])
			if d < best:
				best = d
				tangent = (pts[k] - pts[k - 1]).normalized()
				sign = s[1]
				speed = s[2]
	var fade := 1.0 if speed == RIVER_SPEED else maxf(0.0, 1.0 - best / 2.5)
	var f := tangent * (sign * speed * fade)
	return Vector3(minf(best, 10.0), f.x, -f.y)


## Pale empty slots around the land, one node each so the game can light them up.
func _build_slots() -> void:
	if _slots_node:
		_slots_node.free()
	slot_nodes.clear()
	_slots_node = Node3D.new()
	_slots_node.name = "slots"
	add_child(_slots_node)
	for t: Vector2i in terrains:
		for n in Hex.NEIGHBOURS:
			var s: Vector2i = t + n
			if not terrains.has(s) and not slot_nodes.has(s):
				var mi := MeshInstance3D.new()
				mi.mesh = _slot_mesh
				mi.position = Hex.to3(Hex.tile_position(s.x, s.y))
				_slots_node.add_child(mi)
				slot_nodes[s] = mi
