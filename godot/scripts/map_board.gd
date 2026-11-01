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
	touched.merge(_update_gates())
	for t: Vector2i in touched:
		_build_tile(t)
	for t: Vector2i in touched:
		_add_cover(t)
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
	var now := FenceGates.gates(by_terrain)
	var changed := {}
	for t: Vector2i in now:
		if now[t] != gates.get(t, []):
			changed[t] = true
	gates = now
	return changed


## Whether a party can step between neighbours a and b: fences are only crossed through a gate (DOCS: Walking).
func edge_open(a: Vector2i, b: Vector2i) -> bool:
	if gates.has(a) == gates.has(b):
		return true
	var fenced := a if gates.has(a) else b
	var other := b if gates.has(a) else a
	return Hex.NEIGHBOURS.find(other - fenced) in gates[fenced]


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
## no trail pieces: they flow by density, so the party keeps its usual curved route there.
func trail_edge(a: Vector2i, b: Vector2i) -> bool:
	if not (flow_toward.get(a) == b or flow_toward.get(b) == a):
		return false
	return _has_trail(terrains.get(a)) or _has_trail(terrains.get(b))


func _has_trail(name) -> bool:
	return name != null and (_kit.has(name + "_edge_trail") or _kit.has(Variants.wedges_of(name) + "_edge_trail"))


## The ground cover of tile t, kept off its and its neighbours' pieces' no_cover circles (plans, world space).
func _add_cover(t: Vector2i) -> void:
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
			if name in ["hill_grass", "highland_grass"]:
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
	var farm_fx := FarmFx.for_piece(name + centre, at, turn)
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
		# meet; otherwise half on each edge shared with one other hills tile.
		var triple := []
		for i in 6:
			triple.append(joined[i] and joined[(i + 1) % 6])   # corner i: between edges i and i + 1
		if not joined.has(true):
			Kit.place(node, _kit, name + "_peak", at)
		var parts := []
		for i in 6:
			if triple[i]:
				parts.append(["corner", i])
			elif joined[i] and not triple[posmod(i - 1, 6)]:
				parts.append(["edge", i])
		for part in parts:
			Kit.place(node, _kit, name + "_mountain_" + part[0], at, deg_to_rad(60.0 * part[1]))
		# In bigger groups the mountains join into a range: ridges from this tile's middle to each of them.
		if parts.size() >= 2:
			Kit.place(node, _kit, name + "_ridge_knot", at)
			for part in parts:
				Kit.place(node, _kit, name + "_ridge_" + part[0], at, deg_to_rad(60.0 * part[1]))
	var kit := Variants.wedges_of(name)   # a centre-only landmark takes its variant's wedges
	var trails := LandmarkFlow.trail_edges(t, flow_toward)
	for i in 6:
		var angle := deg_to_rad(60.0 * i)
		var edge := _edge_piece(t, name, kit, i, joined[i], trails)
		Kit.place(node, _kit, edge, at, angle)
		# Carry a neighbouring edge's border out to this joined edge, so borders run on between tiles.
		if terrain in BORDERED and joined[i]:
			if not joined[(i + 1) % 6]:
				Kit.place(node, _kit, "border_join_l", at, angle)
			if not joined[posmod(i - 1, 6)]:
				Kit.place(node, _kit, "border_join_r", at, angle)
	if terrain in ["hills", "desert"]:
		_add_ground_collision(node)


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
	if not joined and Variants.LANDMARKS.has(name) and _kit.has(kit + "_edge_other_lm"):
		return kit + "_edge_other_lm"
	if joined and _kit.has(kit + "_edge_same_b") and GroundCover.hash01(t.x * 6 + i, t.y, 8) < 0.5:
		return kit + "_edge_same_b"
	return kit + ("_edge_same" if joined else "_edge_other")


## Collision for the ground the party walks on (PartyWalker.ground raycasts it): the hills pieces' grass
## (their `hill_grass` / `highland_grass` surfaces, not their trees or rocks), whole peaks, mountains and ridges,
## and the desert's sand. Everything else is flat at height 0. Peaks, mountains and ridges are marked, so the
## party's route goes round them.
static var _shapes := {}


func _add_ground_collision(node: Node3D) -> void:
	for c in node.get_children():
		if not c is MeshInstance3D:
			continue
		var mi := c as MeshInstance3D
		var n: String = mi.get_meta("piece", String(mi.name))   # not the node name: repeats are renamed
		var whole := n == "sand" or "_peak" in n or "_mountain_" in n or "_ridge_" in n
		if not whole and not (n.begins_with("hills_") or n.begins_with("highlands_")):
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
