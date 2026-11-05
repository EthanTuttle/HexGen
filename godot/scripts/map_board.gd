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
const FOAM_SPEED := 1.8        # PLACEHOLDER: how fast a gorge's white water drifts, in metres a second
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
var _water_cache := {}     # (q, r) -> _water_info(), reused while what it depends on stays the same
var _water_mats := {}      # style -> its water material
var _troll_water := {}     # Troll Bridge tile -> {mask, widths} when it stood: its water is frozen from then on (design/02)
var _port_boats := []      # the River Port's boats, which bob
var _still_mists := []     # still waters' mist, shown at dawn
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
## The canyon (Canyon; art/handoff/desert_kit.md): generated once when a region finishes, and kept.
var canyons := {}                      # canyon tile -> {openset, entrances, landmark, turn} of its region
var canyon_stats := []                 # each generated region's triangles and times, for the check's report
var _canyon_meshes := {}               # canyon tile -> its mesh
var _canyon_dirty := {}                # canyon tiles with new rock, waiting to be rebuilt
var _canyon_mat: StandardMaterial3D    # marks the stencil, for the minis' silhouette through rock
var _gorge_rock: StandardMaterial3D    # the canyon's, marking the stencil, and two-sided
var _gorge_ground: ShaderMaterial      # a gorge's land: the ground's colours, and marks the stencil too
var _fall_mat: ShaderMaterial          # a waterfall: unlit, so it doesn't go grey in shade
var _gorge_foam_mat: ShaderMaterial   # a gorge's white water: unlit, so walls don't shade it grey
var _dressing_cache := {}              # water tile -> its banks, dressing and boats' spots
var _surface_cache := {}               # water tile -> [what its surface depends on, its surface]
var gorge_build_us := 0                # the slowest Gorge.build so far on the main thread, for the check's report
var marsh_job_ms := 0                  # the last region's wetland, off the main thread
var marsh_data_us := 0                 # test aid: time in marsh_of, and in all of _add_marsh
var marsh_build_us := 0
var marsh_cover_us := 0
var gorge_job_ms := 0                  # the last region's gorges, off the main thread
var _feywild := {}                     # Feywild tile -> {key, region, tile}: FeyLands' result and what it depended on
var fey_job_ms := 0                    # the last region's forest, off the main thread
var fey_build_us := 0                  # test aid: time in _add_fey
var _fey_material: StandardMaterial3D
var _fey_portal: Mesh
var _marsh := {}                       # swamp tile -> {key, tile}: SwampLands.marsh_tile's result and what it depended on
var _marsh_water: StandardMaterial3D
var _prop_arrays := {}                 # [piece, surface] -> its arrays
var _marsh_glow := {}                  # the swamp's glowing materials, by name
var _features := {}                    # badlands tile -> what stands at its corners (DesertLands.badlands_features)
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
	if Variants.is_canyon(a) or Variants.is_canyon(b):
		return false   # a canyon has no edge pieces, and meets other land as rock
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
	_update_badlands()
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
	touched.merge(_canyon_dirty)   # a far tile that had to take an entrance (Canyon._repair)
	_canyon_dirty.clear()
	if changes.values().any(func(n): return n in ["badlands", "raiderstronghold"]):
		_update_badlands()
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
## Call before retiling the region, so its tiles pick their trail and near pieces. variant: the Sphinx and Echo Cave turn to
## show their face, and the Stronghold its ramp, to the default camera. pool: an oasis has two tiles to thicken toward.
func set_flow(region: Array, landmark: Vector2i, variant := "", pool = null) -> void:
	var f := LandmarkFlow.flow(region, landmark)
	flow_dist.merge(f.dist, true)
	flow_toward.merge(f.toward, true)
	landmark_turns[landmark] = LandmarkFlow.turn(landmark, f.dist, f.toward)
	if variant in ["wasteland", "canyon"]:
		landmark_turns[landmark] = Sand.sphinx_turn(landmark, region)
	elif variant == "badlands":
		landmark_turns[landmark] = DesertLands.STRONGHOLD_TURN
	if pool != null:
		var g := LandmarkFlow.flow(region, pool)
		for t: Vector2i in g.dist:
			flow_dist[t] = mini(flow_dist.get(t, 99), g.dist[t])
		landmark_turns[pool] = LandmarkFlow.turn(pool, g.dist, g.toward)


## A region's canyon, generated here and now (the debug spawn). start_canyon does it off the main thread.
func generate_canyon(region: Array, landmark: Vector2i) -> void:
	_keep_canyon(Canyon.generate(region, landmark, landmark_turns.get(landmark, 0), GroundCover.hash01(landmark.x, landmark.y, 80)))


## Starts generating a finished region's canyon off the main thread. Poll canyon_done, then call finish_canyon.
func start_canyon(region: Array, landmark: Vector2i) -> Dictionary:
	var job := {result = null}
	var tiles := region.duplicate()
	var turn: int = landmark_turns.get(landmark, 0)
	var seed_value := GroundCover.hash01(landmark.x, landmark.y, 80)
	job.id = WorkerThreadPool.add_task(func(): job.result = Canyon.generate(tiles, landmark, turn, seed_value))
	return job


## Starts rebuilding a finished canyon that's growing, off the main thread (DOCS: design/02 -> Canyon walls). The maze is
## saved, never worked out again: Canyon.grow only adds to it. Only the new tiles and the old ones touching them come back.
func start_canyon_growth(old_tiles: Array, new_tiles: Array, landmark: Vector2i) -> Dictionary:
	var c: Dictionary = canyons[landmark]
	var grown := {tiles = old_tiles.duplicate(), openset = c.openset, entrances = c.entrances,
			mesas = c.mesas, grow = Canyon.grow(c.openset, c.entrances, old_tiles, new_tiles, landmark, terrains)}
	var tiles := old_tiles + new_tiles
	var turn: int = c.turn
	var seed_value := GroundCover.hash01(new_tiles[0].x, new_tiles[0].y, 81)
	var job := {result = null, rebuild = grown.grow.rebuild}
	job.id = WorkerThreadPool.add_task(func(): job.result = Canyon.generate(tiles, landmark, turn, seed_value, grown))
	return job


## Dust along a new canyon tile's edges, to cover the rock changing beside it (PLACEHOLDER: the tile comes up like any
## other, and its neighbours swap under the dust).
func canyon_dust(new_tiles: Array) -> void:
	var pts := PackedVector2Array()
	for t: Vector2i in new_tiles:
		var c := Hex.tile_position(t.x, t.y)
		for i in 6:
			var along := Water.normal(i).orthogonal()
			for u in [-1.5, 0.0, 1.5]:
				pts.append(c + Water.normal(i) * Hex.A + along * u)
	RiseDust.start(self, pts, 0.5)


func canyon_done(job: Dictionary) -> bool:
	return WorkerThreadPool.is_task_completed(job.id)


func finish_canyon(job: Dictionary) -> void:
	WorkerThreadPool.wait_for_task_completion(job.id)
	_keep_canyon(job.result)


func _keep_canyon(r: Dictionary) -> void:
	var t0 := Time.get_ticks_usec()
	var info := {openset = r.openset, entrances = r.entrances, landmark = r.landmark, turn = r.turn, mesas = r.mesas}
	for t: Vector2i in r.tiles:
		canyons[t] = info
		if r.pieces.has(t):
			_canyon_meshes[t] = (r.pieces[t] as Piece).mesh()
			_graphs.erase(t)
			_canyon_dirty[t] = true
	canyon_stats.append({tiles = r.tiles.size(), triangles = r.triangles, per_tile = r.per_tile, field_ms = r.field_ms, mesh_ms = r.mesh_ms,
			commit_ms = (Time.get_ticks_usec() - t0) / 1000.0, entrances = r.entrances.size(), rebuilt = r.pieces.size()})
	if "--perf" in OS.get_cmdline_user_args():
		print("PERF canyon %d tiles: %d triangles; field %d ms, mesh %d ms off the main thread, commit %d ms on it" % [r.tiles.size(), r.triangles, r.field_ms, r.mesh_ms, canyon_stats[-1].commit_ms])


## Whether tile t's edge i can be walked: a canyon's closed edges are rock (DOCS: design/02 -> Canyon walls).
func canyon_open(t: Vector2i, i: int) -> bool:
	var c: Dictionary = canyons[t]
	return Canyon.is_open(c.openset, c.entrances, t, i)


## Where the party walks in file on a line of its own: the canyon's corridors, and the landmarks with routes of their own.
func walks_in_file(t: Vector2i) -> bool:
	return canyons.has(t) or terrains.get(t) in ["sandstonesphinx", "raiderstronghold", "oasisbazaar", "oasispool"]


## The ground's height at a plan point where the tile gives it rather than collision, or NAN: on the canyon's lanes and
## floor (an entrance's height comes from its lane's line, everywhere else is the floor) and the Stronghold's ramp and top.
func walk_z(p: Vector2) -> float:
	var t := GroundCover.tile_at(p)
	if canyons.has(t):
		return _canyon_z(t, p - Hex.tile_position(t.x, t.y))
	if terrains.get(t) == "raiderstronghold":
		var local := Water.turned(p - Hex.tile_position(t.x, t.y), -landmark_turns.get(t, 0))
		var hit := _along_line(local, DesertLands.ramp_walk())
		return hit.y if hit.x < 0.8 else 0.0
	if SwampLands.LOOKS.has(terrains.get(t)):
		return _marsh_z(t, terrains[t], p)
	if water_shapes.has(t) and water_shapes[t].has("lane_lines"):
		var local := p - Hex.tile_position(t.x, t.y)
		for line: PackedVector3Array in water_shapes[t].lane_lines:
			var hit := _along_line(local, line)
			if hit.x < 0.35:
				return hit.y
	return NAN


## The water's height under a mini in a gorge, felt at q (a corner of its base) with its middle at centre; NAN if it isn't
## down in the cut. A corner over the wall or the land beyond counts as water, so a wader isn't lifted off the bed by a wall.
func wading_z(centre: Vector2, q: Vector2) -> float:
	var t := GroundCover.tile_at(centre)
	if not water_shapes.has(t) or not water_shapes[t].has("gorge"):
		return NAN
	var w: Dictionary = water_shapes[t]
	var local := centre - Hex.tile_position(t.x, t.y)
	if not Water.in_water(w.gorge.cut, local):
		return NAN
	var t2 := GroundCover.tile_at(q)
	if t2 != t and water_shapes.has(t2) and water_shapes[t2].has("gorge"):
		var l2 := q - Hex.tile_position(t2.x, t2.y)
		if Water.in_water(water_shapes[t2].gorge.cut, l2):
			return Gorge.water_z(water_shapes[t2].mask, water_shapes[t2].widths, l2)
	return Gorge.water_z(w.mask, w.widths, q - Hex.tile_position(t.x, t.y) if t2 == t else local)


func _canyon_z(t: Vector2i, local: Vector2) -> float:
	var c: Dictionary = canyons[t]
	var best := INF
	var z := Canyon.FLOOR
	for e: Vector3i in c.entrances:
		if e.x == t.x and e.y == t.y:
			var hit := _along_line(local, Canyon.ramp_line(t, e.z, c.landmark, c.turn))
			if hit.x < best:
				best = hit.x
				z = hit.y
	if best == INF:
		return Canyon.FLOOR
	for i in 6:   # nearer another corridor than the lane: that's floor
		if Canyon.is_open(c.openset, [], t, i):
			var line := Canyon.line_to_junction(t, i, c.landmark, c.turn)
			for k in range(1, line.size()):
				if Canyon.seg_dist(local, line[k - 1], line[k]) < best - 0.01:
					return Canyon.FLOOR
	return z


## (how far p is from a line of (x, y, z) points, the line's z at the nearest place).
static func _along_line(p: Vector2, line: PackedVector3Array) -> Vector2:
	var best := Vector2(INF, 0.0)
	for k in range(1, line.size()):
		var a := Vector2(line[k - 1].x, line[k - 1].y)
		var b := Vector2(line[k].x, line[k].y)
		var q := Geometry2D.get_closest_point_to_segment(p, a, b)
		var d := p.distance_to(q)
		if d < best.x:
			var f := 0.0 if a == b else a.distance_to(q) / a.distance_to(b)
			best = Vector2(d, lerpf(line[k - 1].z, line[k].z, f))
	return best


## Works out what stands at the badlands' corners, by the tile that holds each. Later tiles can change the corners they touch.
func _update_badlands() -> void:
	_features.clear()
	for f in DesertLands.badlands_features(terrains, flow_dist):
		_features.get_or_add(f[0], []).append(f)


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
	var edge: int = Hex.NEIGHBOURS.find(b - a)
	if (canyons.has(a) and not canyon_open(a, edge)) or (canyons.has(b) and not canyon_open(b, (edge + 3) % 6)):
		return false
	if _water_edge_shut(a, edge) or _water_edge_shut(b, (edge + 3) % 6):
		return false
	if raised.has(a) != raised.has(b):
		return not climb_between(a, b).is_empty()
	if a == Rules.START_TILE or b == Rules.START_TILE:
		return true   # no fence or street shuts a starting tile (design/06 -> First playable)
	if streets.has(a) and streets.has(b):
		return streets[a].has(Hex.NEIGHBOURS.find(b - a))
	if gates.has(a) == gates.has(b):
		return true
	var fenced := a if gates.has(a) else b
	var other := b if gates.has(a) else a
	return Hex.NEIGHBOURS.find(other - fenced) in gates[fenced]


## Rapids are crossing only (design/02 -> Bridges on rapids): nothing walks or floats in or out of a gorge by its water, over a
## waterfall or not. A land edge with no way down to the water or bridge over it is walked round.
func _water_edge_shut(t: Vector2i, edge: int) -> bool:
	if not water_shapes.has(t):
		return false
	var w: Dictionary = water_shapes[t]
	if not w.has("gorge"):
		return false
	return w.mask[edge] or (not w.gorge.walks.has(edge) and not w.get("bridge", {}).get("routes", {}).has(edge))


## Whether a party can ever stand on tile t: rapids with no land, or with land no lane or bridge reaches, it can't (design/02 ->
## Bridges on rapids). Encounters and anything else needing a visit skip those.
func can_visit(t: Vector2i) -> bool:
	if not water_shapes.has(t) or not water_shapes[t].has("gorge"):
		return true
	for e in 6:
		if not _water_edge_shut(t, e):
			return true
	return false


## Whether leaving water tile t by this edge, from where a party stands at p, means getting wet: a crossing, on rapids.
func wet_leaving(t: Vector2i, p: Vector2, edge: int) -> bool:
	if not water_shapes.has(t) or not water_shapes[t].has("gorge"):
		return false
	var g := path_graph(t)
	if not g.edge_node.has(edge) or g.nodes.is_empty():
		return false
	var way := g.route(g.nearest(p), g.edge_node[edge])
	for k in range(1, way.size()):
		if wet_at(way[k - 1].lerp(way[k], 0.5)):
			return true
	return false


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
	if not _graphs.has(t) and water_shapes.has(t):
		_graphs[t] = _water_graph(t)
	if not _graphs.has(t) and canyons.has(t):
		_graphs[t] = _canyon_graph(t)
	if not _graphs.has(t) and terrains.get(t) in ["sandstonesphinx", "raiderstronghold", "oasisbazaar", "oasispool"]:
		_graphs[t] = _desert_graph(t)
	if not _graphs.has(t) and SwampLands.LOOKS.has(terrains.get(t)):
		_graphs[t] = _marsh_graph(t)
	if not _graphs.has(t) and FeyLands.LOOKS.has(terrains.get(t)):
		_graphs[t] = _fey_graph(t)
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
	if raised.has(t) or canyons.has(t):
		return   # raised ground holds no cover, not even tufts fading in from neighbours; nor does the canyon's floor
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
	var marsh := {}
	if SwampLands.LOOKS.has(terrains.get(t)):
		marsh[t] = marsh_of(t)
	var t0 := Time.get_ticks_usec()
	tile_node(t).add_child(GroundCover.build_tile(terrains, water_shapes, t, clear, marsh))
	if not marsh.is_empty():
		marsh_cover_us += Time.get_ticks_usec() - t0


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
			elif name == "mist_low":   # colour and alpha both in COLOR_0 (art/handoff/swamp_kit.md): draws white without this
				(mesh.surface_get_material(k) as BaseMaterial3D).vertex_color_use_as_albedo = true
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
	# The swamp kit: what glows at night.
	_marsh_water = StandardMaterial3D.new()   # PLACEHOLDER: glossy still water, like the old pools
	_marsh_water.vertex_color_use_as_albedo = true
	_marsh_water.vertex_color_is_srgb = true
	_marsh_water.roughness = 0.12
	_marsh_water.metallic_specular = 0.9
	for mesh: Mesh in _kit.values():
		for k in mesh.get_surface_count():
			var mat_name := Kit.material_name(mesh, k)
			if mat_name in ["wisp", "wisp_green", "wisp_pool", "window_green"]:
				if not _marsh_glow.has(mat_name):
					var g := _glow.duplicate() as StandardMaterial3D
					var c := (mesh.surface_get_material(k) as BaseMaterial3D).albedo_color
					g.albedo_color = c
					g.emission = c
					_marsh_glow[mat_name] = g
				mesh.surface_set_material(k, _marsh_glow[mat_name])
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
	_ground_img.set_pixel(t.x + 32, t.y + 32, Color(c.r, c.g, c.b, 0.75 if FeyLands.LOOKS.has(name) else 1.0))   # its outer edges stay sharp (design/07)
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
	if Variants.is_canyon(name):   # no slab and no pieces: the region's generated rock is its ground
		if _canyon_meshes.has(t):
			var rock := MeshInstance3D.new()
			rock.name = "canyon"
			rock.mesh = _canyon_meshes[t]
			rock.material_override = _canyon_material()
			rock.position = Hex.to3(at)
			node.add_child(rock)
		return
	var dug := terrain == "river" and _is_gorge(t)   # rapids: no slab, what's left of the land is its ground
	if not high and not dug and name != "plaguepit":   # raised ground covers the tile, and a base's soil would stick out of the cliff; the Pit's piece is its ground
		var base := Kit.place(node, _kit, "base_" + terrain, at)   # variants recolour their terrain's base
		base.set_surface_override_material(0, _ground)
	if terrain == "river":
		if dug:
			_add_gorge(node, t, at)
		_place_water_pieces(node, t, at)
		return
	if SwampLands.LOOKS.has(name):
		_add_marsh(node, t, at)
		return
	if FeyLands.LOOKS.has(name):
		_add_fey(node, t, at)
		return
	var centre := "_centre"
	if flow_dist.get(t) == 1 and _kit.has(name + "_centre_near"):
		centre = "_centre_near"  # next to the landmark: the variant's look played up
	elif flow_dist.get(t) == 2 and _kit.has(name + "_centre_mid"):
		centre = "_centre_mid"   # two steps from the landmark: on the way to it
	if centre == "_centre" and _kit.has(name + "_centre_b") and GroundCover.hash01(t.x, t.y, 13) < 0.5:
		centre = "_centre_b"     # a second version of the centre, so a big group doesn't repeat
	if centre in ["_centre", "_centre_b"] and _kit.has(name + "_centre_d"):   # scholars: four features at the tile's middle
		centre = ["_centre", "_centre_b", "_centre_c", "_centre_d"][int(GroundCover.hash01(t.x, t.y, 13) * 4)]
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
	if name in Sand.LOOKS:
		node.add_child(Sand.build_tile(terrains, t, flow_dist.get(t), landmark_turns.get(t, 0)))
	if name == "oasis":
		_add_ripples(node, t, at)
	for f in _features.get(t, []):
		Kit.place(node, _kit, f[1], Vector2(f[2], f[3]), deg_to_rad(f[4]))
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
		if parts.size() >= 2 and clear_near and not _kit.has(Variants.wedges_of(name) + "_steps_centre") \
				and not Cliffs.ledge_tops(climbs).has(t):   # design/06: none where a ledge comes out
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
		if terrain in BORDERED and kin[i] and kit != "scholars_town":   # no fence round a scholars' town
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


## Tile t's wetland, from what it depends on: its look, which neighbours are marsh of which look, the region's flow. Kept while those hold.
func marsh_of(t: Vector2i, map := terrains) -> Dictionary:
	var key := _marsh_key(t, map)
	if not _marsh.has(t) or _marsh[t].key != key:
		_marsh[t] = {key = key, tile = _new_marsh(t, map)}
	return _marsh[t].tile


func _marsh_key(t: Vector2i, map: Dictionary) -> String:
	var near := []
	for n in Hex.NEIGHBOURS:
		near.append(SwampLands.LOOKS.get(map.get(t + n), ""))
	return "%s %s %s %s %s %s" % [map[t], near, LandmarkFlow.trail_edges(t, flow_toward), flow_toward.get(t), landmark_turns.get(t, 0), flow_dist.get(t, 9)]


func _new_marsh(t: Vector2i, map: Dictionary) -> Dictionary:
	var out = LandmarkFlow.toward_edge(t, flow_toward) if flow_toward.has(t) else null
	return SwampLands.marsh_tile(map, t.x, t.y, LandmarkFlow.trail_edges(t, flow_toward), out, landmark_turns.get(t, 0), flow_dist.get(t, 9))


## Works out a region's wetland off the main thread, before its tiles are rebuilt (a tile takes about 25 ms on the Mac). Returns a job for marsh_done.
func start_marsh(changes: Dictionary) -> Dictionary:
	var map := terrains.duplicate()
	map.merge(changes, true)
	var todo := []
	for t: Vector2i in changes:
		for c: Vector2i in [t, t + Hex.NEIGHBOURS[0], t + Hex.NEIGHBOURS[1], t + Hex.NEIGHBOURS[2], t + Hex.NEIGHBOURS[3], t + Hex.NEIGHBOURS[4], t + Hex.NEIGHBOURS[5]]:
			if SwampLands.LOOKS.has(map.get(c)) and not c in todo and (not _marsh.has(c) or _marsh[c].key != _marsh_key(c, map)):
				todo.append(c)
	if todo.is_empty():
		return {}
	SwampLands._grid_points()
	SwampLands._gaps()
	Sand._routes()
	var job := {ms = 0, out = {}, count = todo.size()}
	job.id = WorkerThreadPool.add_task(func():
		var t0 := Time.get_ticks_usec()
		for c: Vector2i in todo:
			job.out[c] = {key = _marsh_key(c, map), tile = _new_marsh(c, map)}
		job.ms = (Time.get_ticks_usec() - t0) / 1000)
	return job


func marsh_done(job: Dictionary) -> bool:
	if job.is_empty():
		return true
	if not WorkerThreadPool.is_task_completed(job.id):
		return false
	WorkerThreadPool.wait_for_task_completion(job.id)
	_marsh.merge(job.out, true)
	marsh_job_ms = job.ms
	return true


## The Feywild tiles joined to t.
func _fey_tiles(t: Vector2i, map: Dictionary) -> Dictionary:
	var tiles := {t: map[t]}
	var todo := [t]
	while not todo.is_empty():
		var c: Vector2i = todo.pop_back()
		for n: Vector2i in Hex.NEIGHBOURS:
			if not tiles.has(c + n) and FeyLands.LOOKS.has(map.get(c + n)):
				tiles[c + n] = map[c + n]
				todo.append(c + n)
	return tiles


func _fey_key(tiles: Dictionary) -> String:
	var parts := []
	for t: Vector2i in tiles:
		parts.append("%s %s %s %s" % [t, tiles[t], flow_toward.get(t), landmark_turns.get(t, 0)])
	parts.sort()
	return " ".join(parts)


## Works out a region and all its tiles. Keeps what they need for walking, not every tree's faces.
func _new_fey(tiles: Dictionary, key: String) -> Dictionary:
	var region := FeyLands.Region.new(tiles, flow_toward, landmark_turns)
	var out := {}
	for t: Vector2i in tiles:
		out[t] = {key = key, region = region, tile = FeyLands.fey_tile(region, t)}
	region.free_shapes()
	return out


## Tile t's Feywild layer, from its region. Kept while the region's tiles and flow hold.
func fey_of(t: Vector2i) -> Dictionary:
	var tiles := _fey_tiles(t, terrains)
	var key := _fey_key(tiles)
	if not _feywild.has(t) or _feywild[t].key != key:
		_feywild.merge(_new_fey(tiles, key), true)
	return _feywild[t]


## Works out the Feywild regions these changes make, off the main thread, before their tiles are rebuilt. Returns a job for fey_done.
func start_fey(changes: Dictionary) -> Dictionary:
	var map := terrains.duplicate()
	map.merge(changes, true)
	var regions := []
	var seen := {}
	for t: Vector2i in changes:
		if FeyLands.LOOKS.has(map.get(t)) and not seen.has(t):
			var tiles := _fey_tiles(t, map)
			seen.merge(tiles)
			regions.append([tiles, _fey_key(tiles)])
	if regions.is_empty():
		return {}
	var job := {ms = 0, out = {}}
	job.id = WorkerThreadPool.add_task(func():
		var t0 := Time.get_ticks_usec()
		for r: Array in regions:
			job.out.merge(_new_fey(r[0], r[1]), true)
		job.ms = (Time.get_ticks_usec() - t0) / 1000)
	return job


func fey_done(job: Dictionary) -> bool:
	if job.is_empty():
		return true
	if not WorkerThreadPool.is_task_completed(job.id):
		return false
	WorkerThreadPool.wait_for_task_completion(job.id)
	_feywild.merge(job.out, true)
	fey_job_ms = job.ms
	return true


## A Feywild tile (fey_lands.add_fey): its ground and trails in one mesh, what stands on it in another that casts shadows, both double-sided: a crown cut at a seam with
## winter is open on its winter side (DOCS: art/handoff/feywild_kit.md). The gate's portal has its own mesh; wisps and what falls are FeyFx.
func _add_fey(node: Node3D, t: Vector2i, at: Vector2) -> void:
	var t0 := Time.get_ticks_usec()
	var tile: Dictionary = fey_of(t).tile
	if _fey_material == null:
		_fey_material = Piece.material().duplicate() as StandardMaterial3D
		_fey_material.cull_mode = BaseMaterial3D.CULL_DISABLED
	var colours := {}
	for row: Array in [["fey_ground", tile.ground + tile.trail, false], ["fey_stand", tile.stand, true]]:
		var p := Piece.new()
		for f: Array in row[1]:
			if not colours.has(f[0]):
				colours[f[0]] = Color(f[0])
			p.poly(f[1], colours[f[0]])
		if not p.is_empty():
			var mi := p.instance(row[0])
			mi.mesh.surface_set_material(0, _fey_material)
			mi.position = Hex.to3(at)
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if row[2] else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			node.add_child(mi)
	if terrains[t] in FeyLands.GATES:
		var turn := deg_to_rad(60.0 * landmark_turns.get(t, 0))
		if _fey_portal == null:
			var two := FeyFx.split_gate(_kit["feygate_centre"])
			_kit["feygate_centre"] = two[0]
			_fey_portal = two[1]
		Kit.place(node, _kit, "feygate_centre", at, turn)
		var portal := MeshInstance3D.new()
		portal.name = "fey_portal"
		portal.mesh = _fey_portal
		portal.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		portal.position = Hex.to3(at)
		portal.rotation.y = turn
		node.add_child(portal)
		var wisps := FeyFx.wisps()
		wisps.position = Hex.to3(at)
		wisps.rotation.y = turn
		node.add_child(wisps)
	var falls := FeyFx.falls(t, tile.effects)
	if falls:
		falls.position = Hex.to3(at)
		node.add_child(falls)
	fey_build_us += Time.get_ticks_usec() - t0


## Where a party walks on a Feywild tile: round a gate's ring, or along a trail, or in along one spoke and out along another (DOCS: art/handoff/feywild_kit.md -> Walking).
func _fey_graph(t: Vector2i) -> TilePaths:
	var g := TilePaths.new()
	var at := Hex.tile_position(t.x, t.y)
	var region: FeyLands.Region = fey_of(t).region
	if terrains[t] in FeyLands.GATES:
		var routes: Dictionary = region.routes[t]
		for e: int in routes:
			g.add_line(routes[e], at)
			g.edge_node[e] = g._node(at + routes[e][0])
			g.stand = g._node(at + routes[e][-1])
		return g
	for i in 6:
		var line := FeyLands.spoke(i)
		g.add_line(line, at)
		g.edge_node[i] = g._node(at + line[0])
	g.stand = g._node(at)
	var edges: Array = region.edges[t]
	if edges.size() >= 2:
		var worn := []
		for a in edges.size():
			for b in range(a + 1, edges.size()):
				var line := SwampLands.trail_line(t.x, t.y, edges[a], edges[b])
				g.add_line(line, at)
				worn.append(line)
		g.weigh_wet(func(p: Vector2): return SwampLands.line_dist(p - at, worn) > 0.05, 3.0)   # a way along a trail wins over the spokes
	return g


## A swamp tile's wetland (swamp_lands.add_marsh): flat water, banks, tracks and planks, then its props, merged into one mesh a tile so a
## tile stays a few draw calls however many reeds it holds. Old swamp wedges and centres are empty, so a landmark's centre is all that's placed.
func _add_marsh(node: Node3D, t: Vector2i, at: Vector2) -> void:
	var t0 := Time.get_ticks_usec()
	var tile := marsh_of(t)
	marsh_data_us += Time.get_ticks_usec() - t0
	var look: Dictionary = SwampLands.VIEW[tile.look]
	var name: String = tile.name
	var turn: int = landmark_turns.get(t, 0)
	var pieces: Array = tile.props
	if Variants.LANDMARKS.has(name):
		Kit.place(node, _kit, name + "_centre", at, deg_to_rad(60.0 * turn))
		pieces = pieces + [[name + "_centre", 0.0, 0.0, deg_to_rad(60.0 * turn)]]
	var flat := Piece.new()
	_marsh_flats(flat, tile.bank, 0.012, Hex.colour(look.rim))
	if tile.look == "smugglers_bayou":
		var seed_: int = t.x * 6 + t.y * 36
		for k in tile.trails.size():
			_boards(flat, tile.trails[k][1], 0.045 - 0.004 * k, seed_ + k)
		for k in tile.spurs.size():
			_boards(flat, tile.spurs[k], 0.03, seed_ + 40 + k)
	else:
		var track: Color = Hex.colour(look.get("track", look.rim))
		for k in tile.trails.size():
			var pairs := SwampLands.ribbon(tile.trails[k][1], tile.half, 0.3 if tile.finish != null else 0.0)
			var z: float = 0.03 - 0.002 * k
			for m in range(1, pairs.size()):
				var l0: Vector2 = pairs[m - 1][0]
				var r0: Vector2 = pairs[m - 1][1]
				var l1: Vector2 = pairs[m][0]
				var r1: Vector2 = pairs[m][1]
				flat.tri(Vector3(r0.x, r0.y, z), Vector3(r1.x, r1.y, z), Vector3(l1.x, l1.y, z), track)
				flat.tri(Vector3(r0.x, r0.y, z), Vector3(l1.x, l1.y, z), Vector3(l0.x, l0.y, z), track)
		for pts: PackedVector2Array in tile.flecks:
			_marsh_fan(flat, pts, 0.029, track)
		for o: Array in tile.ooze:
			_marsh_fan(flat, o[1], 0.032, Hex.colour(o[0]))
	if not flat.is_empty():
		var mi := flat.instance("marsh")
		mi.position = Hex.to3(at)
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		node.add_child(mi)
	var water := Piece.new()
	_marsh_flats(water, tile.water, 0.022, Hex.colour(look.water))
	if not water.is_empty():
		var mi := water.instance("marsh_water")
		mi.mesh.surface_set_material(0, _marsh_water)
		mi.position = Hex.to3(at)
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		node.add_child(mi)
	_merge_props(node, tile.props, at)
	var fx := SwampFx.for_tile(tile.duplicate(), at, pieces)
	if fx:
		node.add_child(fx)
	marsh_build_us += Time.get_ticks_usec() - t0


func _marsh_flats(p: Piece, tris: Array, z: float, col: Color) -> void:
	for t: Array in tris:
		p.tri(Vector3(t[0].x, t[0].y, z), Vector3(t[1].x, t[1].y, z), Vector3(t[2].x, t[2].y, z), col)


func _marsh_fan(p: Piece, pts: PackedVector2Array, z: float, col: Color) -> void:
	for m in range(1, pts.size() - 1):
		p.tri(Vector3(pts[0].x, pts[0].y, z), Vector3(pts[m].x, pts[m].y, z), Vector3(pts[m + 1].x, pts[m + 1].y, z), col)


## The bayou's boardwalk: planks standing from the ground up to top.
func _boards(p: Piece, line: PackedVector2Array, top: float, seed_: int) -> void:
	for b: Array in SwampLands.planks(line, SwampLands.WALK_HALF, seed_):
		var col := Hex.colour(b[0])
		var v := [b[1], b[2], b[3], b[4]]
		var outline := PackedVector2Array(v)
		p.tri(Vector3(v[0].x, v[0].y, top), Vector3(v[1].x, v[1].y, top), Vector3(v[2].x, v[2].y, top), col)
		p.tri(Vector3(v[0].x, v[0].y, top), Vector3(v[2].x, v[2].y, top), Vector3(v[3].x, v[3].y, top), col)
		for j in 4:
			var a: Vector2 = outline[j]
			var c: Vector2 = outline[(j + 1) % 4]
			p.tri(Vector3(a.x, a.y, 0.0), Vector3(c.x, c.y, 0.0), Vector3(c.x, c.y, top), col)
			p.tri(Vector3(a.x, a.y, 0.0), Vector3(c.x, c.y, top), Vector3(a.x, a.y, top), col)


## Kit pieces joined into one mesh per material.
func _merge_props(node: Node3D, props: Array, at: Vector2) -> void:
	var buckets := {}
	for item: Array in props:
		var mesh: Mesh = _kit.get(item[0])
		if mesh == null:
			continue
		var xf := Transform3D(Basis(Vector3.UP, item[3]), Vector3(item[1], 0.0, -item[2]))
		var turn := Transform3D(xf.basis, Vector3.ZERO)
		for k in mesh.get_surface_count():
			var mat := mesh.surface_get_material(k)
			if not buckets.has(mat):
				buckets[mat] = {v = PackedVector3Array(), n = PackedVector3Array(), c = PackedColorArray(), i = PackedInt32Array()}
			var b: Dictionary = buckets[mat]
			var cached = _prop_arrays.get([item[0], k])
			if cached == null:   # reading a mesh's arrays back is slow
				cached = mesh.surface_get_arrays(k)
				_prop_arrays[[item[0], k]] = cached
			var arrays: Array = cached
			var base: int = b.v.size()
			b.v.append_array(xf * (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array))
			b.n.append_array(turn * (arrays[Mesh.ARRAY_NORMAL] as PackedVector3Array))
			if arrays[Mesh.ARRAY_COLOR] != null:
				b.c.append_array(arrays[Mesh.ARRAY_COLOR])
			var idx: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			for q in idx:
				b.i.append(q + base)
	var solid := ArrayMesh.new()
	var mist := ArrayMesh.new()   # see-through, but a blended material still casts a solid shadow
	for mat: Material in buckets:
		var b: Dictionary = buckets[mat]
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = b.v
		arrays[Mesh.ARRAY_NORMAL] = b.n
		if b.c.size() == b.v.size():
			arrays[Mesh.ARRAY_COLOR] = b.c
		arrays[Mesh.ARRAY_INDEX] = b.i
		var into := mist if mat.resource_name == "mist_low" else solid
		into.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		into.surface_set_material(into.get_surface_count() - 1, mat)
	if mist.get_surface_count() > 0:
		var low := MeshInstance3D.new()
		low.name = "marsh_mist"
		low.mesh = mist
		low.position = Hex.to3(at)
		low.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		node.add_child(low)
	if solid.get_surface_count() > 0:
		var mi := MeshInstance3D.new()
		mi.name = "marsh_props"
		mi.mesh = solid
		mi.position = Hex.to3(at)
		node.add_child(mi)


## The way along tile t's trail between two of its trail edges (world plan points), or empty: off a trail the party keeps its usual curve.
func marsh_way(t: Vector2i, in_edge: int, out_edge: int) -> PackedVector2Array:
	var way := PackedVector2Array()
	if not SwampLands.LOOKS.has(terrains.get(t)) or Variants.LANDMARKS.has(terrains[t]):
		return way
	var edges := LandmarkFlow.trail_edges(t, flow_toward)
	if in_edge == out_edge or not in_edge in edges or not out_edge in edges:
		return way
	var at := Hex.tile_position(t.x, t.y)
	for p in SwampLands.trail_line(t.x, t.y, in_edge, out_edge):
		way.append(at + p)
	return way


## The routes round a swamp landmark to its stop (swamp_lands.landmark_routes); other swamp tiles have no graph of their own.
func _marsh_graph(t: Vector2i) -> TilePaths:
	var g := TilePaths.new()
	var name: String = terrains[t]
	if not Variants.LANDMARKS.has(name):
		return g
	var at := Hex.tile_position(t.x, t.y)
	var routes := SwampLands.landmark_routes(name, landmark_turns.get(t, 0))
	for e: int in routes:
		var line := PackedVector2Array()
		for q: Vector3 in routes[e]:
			line.append(Vector2(q.x, q.y))
		g.add_line(line, at)
		g.edge_node[e] = g._node(at + line[0])
		g.stand = g._node(at + line[-1])
	return g


## The height a mini walks at on a swamp tile: up a stilt house's gangway, down the Plague Pit's lane, on the bayou's boardwalk; NAN elsewhere.
func _marsh_z(t: Vector2i, name: String, p: Vector2) -> float:
	var local := p - Hex.tile_position(t.x, t.y)
	if name == "witchhut" or name == "thievesguild":
		var hit := _along_line(Water.turned(local, -landmark_turns.get(t, 0)), PackedVector3Array([Vector3(SwampLands.RAMP_START, 0, 0), Vector3(SwampLands.RAMP_END, 0, SwampLands.STILT_Z), Vector3(0, 0, SwampLands.STILT_Z)]))
		return hit.y if hit.x < 0.8 else 0.0
	if name == "plaguepit":
		var line := PackedVector3Array(SwampLands.pit_lane())
		line.append(SwampLands.pit_turn())
		line.append(SwampLands.pit_stop())
		var hit := _along_line(Water.turned(local, -landmark_turns.get(t, 0)), line)
		return hit.y if hit.x < 0.8 else 0.0
	if SwampLands.LOOKS[name] == "smugglers_bayou" and _marsh.has(t):
		var tile: Dictionary = _marsh[t].tile
		if not tile.trail_lines.is_empty() and SwampLands.line_dist(local, tile.trail_lines) < SwampLands.WALK_HALF:
			return 0.045
	return NAN


## The oasis's wind ripples on this tile, all one way across the region (desert_lands.oasis_ripples), in one mesh rather than
## a node per oasis_ripple piece; each is that piece's plain strip.
func _add_ripples(node: Node3D, t: Vector2i, at: Vector2) -> void:
	var p := Piece.new()
	var col := Hex.colour("oasis_ripple")
	for r in DesertLands.oasis_ripples(terrains, t):
		p.box(Vector3(r[0] - at.x, r[1] - at.y, 0), Vector3(r[2], 0.05, 0.008), col, 0.01, deg_to_rad(DesertLands.RIPPLE_DEG))
	if not p.is_empty():
		var mi := p.instance("ripples")
		mi.position = Hex.to3(at)
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		node.add_child(mi)


## The canyon's material: the kit's vertex colours, and it marks the stencil, for the silhouette through rock.
func _canyon_material() -> StandardMaterial3D:
	if _canyon_mat == null:
		_canyon_mat = Piece.material().duplicate() as StandardMaterial3D
		_canyon_mat.stencil_mode = BaseMaterial3D.STENCIL_MODE_CUSTOM
		_canyon_mat.stencil_flags = BaseMaterial3D.STENCIL_FLAG_WRITE
		_canyon_mat.stencil_compare = BaseMaterial3D.STENCIL_COMPARE_ALWAYS
		_canyon_mat.stencil_reference = 1
	return _canyon_mat


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
	if parts.size() < 2 or Cliffs.ledge_tops(climbs).has(t):
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
	_port_boats = _port_boats.filter(func(b): return is_instance_valid(b))
	for t: Vector2i in terrains:
		if Variants.is_water(terrains[t]):
			water_shapes[t] = _water_info(t)
			_graphs.erase(t)
	if _water_node:
		_water_node.free()
	boats.clear()
	_water_node = Node3D.new()
	_water_node.name = "water"
	add_child(_water_node)
	if not water_shapes.is_empty():
		_build_water()


## [water edges, widths] of a tile called name, with pending's changes taken as made.
func _water_inputs(t: Vector2i, name: String, pending := {}) -> Array:
	var near := []
	var mask := []
	for i in 6:
		var n: Vector2i = t + Hex.NEIGHBOURS[i]
		near.append(pending.get(n, terrains.get(n)))
		mask.append(Variants.is_water(near[-1]) and not _frozen_shut(t, n, i))
	var widths := Water.edge_widths(name, near)
	for i in 6:   # both tiles keep the width the frozen tile has at their shared edge
		var n: Vector2i = t + Hex.NEIGHBOURS[i]
		if _troll_water.has(n) and mask[i]:
			var across: float = _troll_water[n].widths[(i + 3) % 6]
			widths[i] = Water.RIVER_WIDTH if across == Water.FALL_WIDTH else across
	if Water.FAMILY.get(name) == "rapids":
		widths = Water.with_falls(widths, mask, t.x, t.y)
	if _troll_water.has(t):
		return [_troll_water[t].mask, _troll_water[t].widths]
	return [mask, widths]


## Works out the gorges of tiles about to become rapids off the main thread, as Gorge.build keeps them: retile then finds
## them ready. Wait on gorges_done before anything else asks Gorge for a tile.
func start_gorges(changes: Dictionary) -> Dictionary:
	var todo := []
	for t: Vector2i in changes:
		if Water.FAMILY.get(changes[t]) == "rapids":
			var inputs := _water_inputs(t, changes[t], changes)
			if inputs[0].has(true):
				todo.append([inputs[0], "%d,%d" % [t.x, t.y], inputs[1], Variants.LANDMARK_CENTRES.has(changes[t])])
	if todo.is_empty():
		return {}
	var job := {ms = 0}
	job.id = WorkerThreadPool.add_task(func():
		var t0 := Time.get_ticks_usec()
		for a in todo:
			Gorge.build(a[0], a[1], a[2], a[3])
		job.ms = (Time.get_ticks_usec() - t0) / 1000)
	return job


func gorges_done(job: Dictionary) -> bool:
	if job.is_empty():
		return true
	if not WorkerThreadPool.is_task_completed(job.id):
		return false
	WorkerThreadPool.wait_for_task_completion(job.id)
	gorge_job_ms = job.ms
	return true


## One water tile's shape, routes, props and landmark spot; unchanged while what they depend on is.
func _water_info(t: Vector2i) -> Dictionary:
	var name: String = terrains[t]
	var band: int = flow_dist.get(t, 0) if flow_dist.get(t, 0) in [1, 2] else 0
	var inputs := _water_inputs(t, name)
	var mask: Array = inputs[0]
	var widths: Array = inputs[1]
	var key := [name, mask, widths, band]
	if _water_cache.has(t) and _water_cache[t].key == key:
		return _water_cache[t]
	var seed := "%d,%d" % [t.x, t.y]
	var style: String = Water.FAMILY.get(name, "")
	var w := Water.tile_water(mask, seed, widths, style)
	var landmark := Variants.LANDMARK_CENTRES.has(name)
	w.merge({key = key, style = style, mask = mask, widths = widths, seed = seed, band = band, landmark = landmark, dry = []})
	if style == "rapids" and mask.has(true):
		var t0 := Time.get_ticks_usec()
		w.gorge = Gorge.build(mask, seed, widths, landmark)
		gorge_build_us = maxi(gorge_build_us, Time.get_ticks_usec() - t0)
		w.cover_outlines = w.gorge.cut
		w.cover_shores = [Water._closed(w.gorge.cut[0])]
		w.lane_lines = _lane_lines(w.gorge.walks)
	w.props = Water.tile_props(mask, seed, widths, style, band, landmark)
	var turn := 0
	if name == "riverport":
		turn = Water.port_turn(mask, seed)
		var sh := Water.port_shape(mask, seed, widths, turn)
		var arc: PackedVector2Array = Water.port_water(turn)[1]
		w.outlines = sh.outlines
		w.quads = sh.quads
		w.walls = Water.port_walls(mask, seed, widths, turn)
		w.cover_shores = [arc]
		w.shores = w.shores + [arc]
		w.ends = w.ends + [[-1, -1]]
		landmark_turns[t] = turn
	elif name == "meditationrock":
		w.rock = Water.rock_routes(mask, seed, widths)
		landmark_turns[t] = maxi(w.rock.turn, 0)
		w.dry.append([Vector2.ZERO, Vector2.ZERO, Water.ROCK_R])
		for e in w.rock.land:
			var l: PackedVector2Array = w.rock.land[e]
			for k in l.size() - 1:
				w.dry.append([l[k], l[k + 1], 0.35])
	elif name == "serpentlair":
		var lt: int = landmark_turns.get(t, 0)
		w.dry.append([Water.turned(Water.LAIR_LAND, lt), Water.turned(Water.LAIR_STOP, lt), 0.5])
	elif name == "trollbridge":
		w.bridge = Water.rapids_spot(mask, seed, widths, true)
		w.bridge_piece = "trollbridge_centre"
		if not w.bridge.is_empty():   # it stands: from here its water is frozen (design/02)
			_troll_water[t] = {mask = mask, widths = widths}
	else:
		for prop in w.props:
			if prop[0] == "rapids_bridge":
				w.bridge = Water.rapids_spot(mask, seed, widths)
				w.bridge_piece = "rapids_bridge"
	if not w.get("bridge", {}).is_empty():
		var half := Water.TROLL_HALF if w.bridge_piece == "trollbridge_centre" else Water.BRIDGE_HALF
		var axis := Vector2.from_angle(w.bridge.angle)
		w.dry.append([w.bridge.middle - axis * half, w.bridge.middle + axis * half, 0.75])
	_water_cache[t] = w
	return w


## Once the Troll Bridge stands, a later water neighbour's channel doesn't reach it: the shared edge is land for both tiles.
func _frozen_shut(t: Vector2i, n: Vector2i, i: int) -> bool:
	return (_troll_water.has(t) and not _troll_water[t].mask[i]) or (_troll_water.has(n) and not _troll_water[n].mask[(i + 3) % 6])


func _is_gorge(t: Vector2i) -> bool:
	if not water_shapes.has(t):
		water_shapes[t] = _water_info(t)
	return water_shapes[t].has("gorge")


## The stretches of a gorge's walks that are on a lane, each once: from its top down to its foot, with their heights.
static func _lane_lines(walks: Dictionary) -> Array:
	var seen := {}
	for e: int in walks:
		var walk: PackedVector3Array = walks[e]
		var first := 0
		while first < walk.size() - 2 and walk[first + 1].z >= 0.0:
			first += 1
		seen[walk[-1]] = walk.slice(first, walk.size() - 1)
	return seen.values()


func _gorge_foam() -> ShaderMaterial:
	if _gorge_foam_mat == null:
		_gorge_foam_mat = ShaderMaterial.new()
		_gorge_foam_mat.shader = load("res://shaders/gorge_foam.gdshader")
	return _gorge_foam_mat


## A rapids tile's rock, its ground and any waterfall, one mesh each, kept with its shape.
func _add_gorge(node: Node3D, t: Vector2i, at: Vector2) -> void:
	var w: Dictionary = water_shapes[t]
	if not w.has("gorge_meshes"):
		var rock := Piece.new()
		var ground := Piece.new()
		var fall := Piece.new()
		for tri in w.gorge.tris:
			if tri[3] == "ground":
				ground.tri(tri[0], tri[1], tri[2], Color.WHITE)
			elif tri[3] in Gorge.FALL_MATS:
				fall.tri(tri[0], tri[1], tri[2], Hex.colour(tri[3]))
			else:
				rock.tri(tri[0], tri[1], tri[2], Hex.colour(tri[3]))
		for side in w.gorge.sides:
			rock.poly(side[0], Hex.colour(side[1]))
		w.gorge_triangles = rock.triangles + ground.triangles + fall.triangles
		w.gorge_meshes = [rock.mesh(), ground.mesh(), fall.mesh() if not fall.is_empty() else null]
	if _gorge_ground == null:
		_gorge_ground = ShaderMaterial.new()
		_gorge_ground.shader = load("res://shaders/ground_stencil.gdshader")
		_gorge_ground.set_shader_parameter("terrain_map", _ground_tex)
		_gorge_ground.set_shader_parameter("blend_width", BLEND_WIDTH)
		_fall_mat = ShaderMaterial.new()
		_fall_mat.shader = load("res://shaders/fall.gdshader")
	if _gorge_rock == null:   # both sides: a wall that folds at a tile's edge shows its back to a turned camera (the preview draws both)
		_gorge_rock = _canyon_material().duplicate() as StandardMaterial3D
		_gorge_rock.cull_mode = BaseMaterial3D.CULL_DISABLED
	var mats := [_gorge_rock, _gorge_ground, _fall_mat]
	for k in 3:
		if w.gorge_meshes[k] == null:
			continue
		var mi := MeshInstance3D.new()
		mi.name = ["gorge_rock", "gorge_ground", "gorge_fall"][k]
		mi.mesh = w.gorge_meshes[k]
		mi.material_override = mats[k]
		mi.position = Hex.to3(at)
		if k == 2:
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		node.add_child(mi)


## Whether a point is in the water, not on a bridge, stepping stones, a rock or the port's quay.
func wet_at(p: Vector2) -> bool:
	var t := GroundCover.tile_at(p)
	if not water_shapes.has(t):
		return false
	var w: Dictionary = water_shapes[t]
	var local := p - Hex.tile_position(t.x, t.y)
	if not Water.in_water(w.outlines, local):
		return false
	for d in w.dry:
		if Water.seg_dist(local, d[0], d[1]) <= d[2]:
			return false
	return true


## Whether going across water tile t, in by one edge and out by another (or to its stopping point, out -1), means
## getting wet. A bridge, the stepping stones and the port's alley don't.
func wet_between(t: Vector2i, in_edge: int, out_edge: int) -> bool:
	var g := path_graph(t)
	var a: int = g.edge_node.get(in_edge, -1)
	var b = g.stand_from(in_edge) if out_edge < 0 else g.edge_node.get(out_edge, -1)
	if a < 0 or b == null or b < 0:
		return true
	var way := g.route(a, b)
	for k in range(1, way.size()):
		for u in [0.25, 0.5, 0.75]:
			if wet_at(way[k - 1].lerp(way[k], u)):
				return true
	return false


## A canyon tile's walk corridors, each from an open edge's midpoint to the tile's junction (canyon.route).
func _canyon_graph(t: Vector2i) -> TilePaths:
	var g := TilePaths.new()
	var c: Dictionary = canyons[t]
	var at := Hex.tile_position(t.x, t.y)
	var lines := Canyon.tile_lines(t, c.openset, c.entrances, c.landmark, c.turn)
	for e: int in lines:
		g.add_line(lines[e], at)
		g.edge_node[e] = g._node(at + lines[e][0])
	g.stand = g._node(at + Canyon.junction(t, c.landmark, c.turn))
	return g


## The routes of the desert's landmarks, which aren't in their pieces' path data (desert_lands.py, sand.sphinx_routes).
func _desert_graph(t: Vector2i) -> TilePaths:
	var g := TilePaths.new()
	var at := Hex.tile_position(t.x, t.y)
	var turn: int = landmark_turns.get(t, 0)
	var name: String = terrains[t]
	if name == "oasispool":
		# PLACEHOLDER: the kit routes across the pool but gives no place to stop: on the ring, on the side toward the camera.
		var ring := DesertLands.pool_ring()
		for k in ring.size():
			g.add_line(PackedVector2Array([ring[k], ring[(k + 1) % ring.size()]]), at)
		for e in 6:
			var spoke := PackedVector2Array([Water.normal(e) * Hex.A, ring[e * 3]])
			g.add_line(spoke, at)
			g.edge_node[e] = g._node(at + spoke[0])
		g.stand = g._node(at + ring[13])
		return g
	var routes: Dictionary = Sand.sphinx_routes(turn) if name == "sandstonesphinx" else DesertLands.stronghold_routes(turn) if name == "raiderstronghold" else DesertLands.bazaar_routes(turn)
	for e: int in routes:
		var line := PackedVector2Array()
		for q in routes[e]:
			line.append(Vector2(q.x, q.y))
		g.add_line(line, at)
		g.edge_node[e] = g._node(at + line[0])
		g.stand = g._node(at + line[-1])
	return g


## The routes across a water tile, as a graph like a piece's drawn paths (water.py has them, not the glb).
func _water_graph(t: Vector2i) -> TilePaths:
	var g := TilePaths.new()
	var w: Dictionary = water_shapes[t]
	var at := Hex.tile_position(t.x, t.y)
	var name: String = terrains[t]
	var stand := Vector2.ZERO
	if name == "riverport":
		var turn: int = landmark_turns.get(t, 0)
		var r := Water.port_routes(w.mask, turn)
		stand = Water.turned(Water.PORT_STOP, turn)
		g.add_line(PackedVector2Array([Water.turned(Water.PORT_FLOAT, turn), stand]), at)
		for lines in [r.land, r.floats]:
			for e in lines:
				g.add_line(lines[e], at)
				g.edge_node[e] = g._node(at + lines[e][0])
	elif name == "serpentlair":
		var turn: int = landmark_turns.get(t, 0)
		var r := Water.lair_routes(turn)
		stand = Water.turned(Water.LAIR_STOP, turn)
		g.add_line(PackedVector2Array([Water.turned(Water.LAIR_LAND, turn), stand]), at)
		for e in r:
			g.add_line(r[e], at)
			g.edge_node[e] = g._node(at + r[e][0])
	elif name == "meditationrock" and w.rock.turn >= 0:
		for e in w.rock.land:
			g.add_line(w.rock.land[e], at)
			g.edge_node[e] = g._node(at + w.rock.land[e][0])
		for e in w.rock.floats:
			var l: PackedVector2Array = w.rock.floats[e]
			g.add_line(PackedVector2Array([l[0], l[1], Vector2.ZERO]), at)
			g.edge_node[e] = g._node(at + l[0])
	else:
		if w.style == "rapids":
			return _rapids_graph(t, w, at, g)
		var r := Water.water_routes(w.mask, w.seed, w.widths, w.style)
		stand = r.hub
		for e in r.lines:
			g.add_line(r.lines[e], at)
			g.edge_node[e] = g._node(at + r.lines[e][0])
		var lands := Water.landings(w.mask, w.seed, w.widths, w.style)
		for e in lands:
			g.add_line(PackedVector2Array([lands[e][0], lands[e][1], lands[e][2], r.hub]), at)
			g.edge_node[e] = g._node(at + lands[e][0])
	g.stand = g._node(at + stand)
	g.weigh_wet(wet_at, Rules.WET_ROUTE_WEIGHT)
	return g


## Rapids are crossing only (design/02 -> Bridges on rapids): each land edge has its way to its bank's stop, and a bank's lane
## runs down to the water, where it meets any other lane on the tile, so a crossing is bank to bank. No lines along the water,
## no stop in it. A bridge is walked with no check, from its land edges to its middle. A tile with no land edge has no way on.
func _rapids_graph(t: Vector2i, w: Dictionary, at: Vector2, g: TilePaths) -> TilePaths:
	g.dry_line = true
	if not w.has("gorge"):   # a lone tile, with a small pool: round it, not through it
		var n := 12
		var ring := PackedVector2Array()
		for k in n:
			ring.append(Vector2.from_angle(TAU * k / n) * 1.9)
		for k in n:
			g.add_line(PackedVector2Array([ring[k], ring[(k + 1) % n]]), at)
		for e in 6:
			var spoke := PackedVector2Array([Water.normal(e) * Water.A, ring[e * 2]])
			g.add_line(spoke, at)
			g.edge_node[e] = g._node(at + spoke[0])
		g.stand = g._node(at + ring[9])
		return g
	var bridge: Dictionary = w.get("bridge", {})
	var hub: Vector2 = Water.water_routes(w.mask, w.seed, w.widths, w.style).hub
	for e: int in w.gorge.walks:
		if not bridge.is_empty() and bridge.routes.has(e):
			continue
		var walk: PackedVector3Array = w.gorge.walks[e]
		var line := PackedVector2Array()
		var top := 0   # the lane's top, then the last land before it
		for k in walk.size():
			line.append(Vector2(walk[k].x, walk[k].y))
			if k < walk.size() - 1 and walk[k].z >= 0.0:
				top = k
		line.append(hub)
		g.add_line(line, at)
		g.edge_node[e] = g._node(at + line[0])
		g.edge_stand[e] = g._node(at + line[maxi(top - 1, 0)])
		g.stand = g.edge_stand[e]
	if not bridge.is_empty():
		for e in bridge.routes:
			g.add_line(bridge.routes[e], at)
			g.edge_node[e] = g._node(at + bridge.routes[e][0])
		var axis := Vector2.from_angle(bridge.angle)
		var half := Water.TROLL_HALF if w.bridge_piece == "trollbridge_centre" else Water.BRIDGE_HALF
		var top: Vector2 = bridge.middle
		g.add_line(PackedVector2Array([top - axis * half, top, top + axis * half]), at)
		for e in bridge.routes:
			g.edge_stand[e] = g._node(at + top)
		g.stand = g._node(at + top)
	g.weigh_wet(wet_at, Rules.WET_ROUTE_WEIGHT)
	return g


## What stands on a water tile: its props, a landmark's pieces, the ground the party walks on over the water, and effects.
func _place_water_pieces(node: Node3D, t: Vector2i, at: Vector2) -> void:
	if not water_shapes.has(t):
		water_shapes[t] = _water_info(t)
	var w: Dictionary = water_shapes[t]
	var name: String = terrains[t]
	for prop in w.props:
		var mi := Kit.place(node, _kit, prop[0], at + prop[1], prop[2])
		var z := Water.prop_z(prop[0])
		if mi:
			mi.position.y = z
		if prop[0] == "rapids_fall" and mi:
			for e in Kit.path_data("rapids_fall").get("effects", []):
				if e.kind == "spray":
					node.add_child(FarmFx.spray(Hex.to3(at + prop[1], z + e.at[1])))
		if prop[0] == "rapids_bridge":
			_deck(node, at, prop[0], w.bridge.middle, w.bridge.angle, 0.6)
	if w.has("gorge"):
		for f in w.gorge.falls:
			node.add_child(FarmFx.spray(Hex.to3(at + f.foot, -Gorge.DEPTH + 0.3)))
	var turn: int = landmark_turns.get(t, 0)
	if name == "serpentlair":
		Kit.place(node, _kit, "serpentlair_centre", at, deg_to_rad(60.0 * turn))
		_deck(node, at, "serpentlair_centre", Vector2.ZERO, deg_to_rad(60.0 * turn), 0.7)
	elif name == "meditationrock":
		Kit.place(node, _kit, "meditationrock_centre", at, deg_to_rad(60.0 * turn))
		_rock_ground(node, at, w)
	elif name == "trollbridge" and not w.bridge.is_empty():
		Kit.place(node, _kit, "trollbridge_centre", at + w.bridge.middle, w.bridge.angle)
		_deck(node, at, "trollbridge_centre", w.bridge.middle, w.bridge.angle, 0.7)
	elif name == "riverport":
		var spin := deg_to_rad(60.0 * turn)
		Kit.place(node, _kit, "riverport_centre", at, spin)
		for part in Variants.PORT_PARTS:
			var mi := Kit.place(node, _kit, part, at + Variants.PORT_PARTS[part].rotated(spin), spin)
			if mi:
				_port_boats.append(mi)
		for k in [2, 3, 4]:
			if w.mask[(k + turn) % 6]:
				Kit.place(node, _kit, "riverport_watergate", at, deg_to_rad(60.0 * (k + turn)))
		_town_smoke(node, at)
	if w.style == "still_waters":
		var mist := _mist(at)
		mist.visible = false
		node.add_child(mist)
		_still_mists.append(mist)


## Ground for the party over a piece's own path (a bridge's hump, the Lair's shelf): a strip it can feel.
func _deck(node: Node3D, at: Vector2, piece: String, middle: Vector2, angle: float, half: float) -> void:
	var faces := PackedVector3Array()
	for poly in Kit.path_data(piece).get("paths", []):
		for k in range(1, poly.size()):
			var a: Vector3 = _deck_point(poly[k - 1], at + middle, angle, half)
			var b: Vector3 = _deck_point(poly[k], at + middle, angle, half)
			var c: Vector3 = _deck_point(poly[k - 1], at + middle, angle, -half)
			var d: Vector3 = _deck_point(poly[k], at + middle, angle, -half)
			faces.append_array([a, b, c, b, d, c])
	_ground_body(node, faces)


static func _deck_point(p: Array, at: Vector2, angle: float, side: float) -> Vector3:
	return Hex.to3(at + Vector2(p[0], -p[2] + side).rotated(angle), p[1])


## Meditation Rock's top and the stepping stones, at their drawn heights (variants.meditation_rock, water.add_water).
func _rock_ground(node: Node3D, at: Vector2, w: Dictionary) -> void:
	var faces := PackedVector3Array()
	var cone := func(c: Vector2, r0: float, h0: float, r1: float, h1: float) -> void:
		for k in 16:
			var a := Vector2.from_angle(TAU * k / 16)
			var b := Vector2.from_angle(TAU * (k + 1) / 16)
			var i0 := Hex.to3(at + c + a * r0, h0)
			var i1 := Hex.to3(at + c + b * r0, h0)
			var o0 := Hex.to3(at + c + a * r1, h1)
			var o1 := Hex.to3(at + c + b * r1, h1)
			faces.append_array([i0, i1, o0, i1, o1, o0])
	cone.call(Vector2.ZERO, 0.0, 0.34, 0.82, 0.34)
	cone.call(Vector2.ZERO, 0.82, 0.34, 1.28, 0.16)
	cone.call(Vector2.ZERO, 1.28, 0.16, 1.45, 0.0)
	for stone in w.rock.stones:
		cone.call(stone[0], 0.0, 0.1, stone[1] + 0.3, 0.1)   # a base wider than a stone doesn't tip off it
	_ground_body(node, faces)


func _ground_body(node: Node3D, faces: PackedVector3Array) -> void:
	if faces.is_empty():
		return
	var shape := ConcavePolygonShape3D.new()
	shape.backface_collision = true
	shape.set_faces(faces)
	var cs := CollisionShape3D.new()
	cs.shape = shape
	var body := StaticBody3D.new()
	body.collision_layer = 1
	body.add_child(cs)
	node.add_child(body)


## The water's material for a style: the shared shader, with the kit's colour (PLACEHOLDER colours; deep is that darkened).
func _water_material(style: String) -> ShaderMaterial:
	if not Water.WATER_MAT.has(style):
		var plain := load("res://shaders/water.tres") as ShaderMaterial
		plain.set_shader_parameter("ripple_map", Water.ripple_texture())
		return plain
	if not _water_mats.has(style):
		var m := (load("res://shaders/water.tres") as ShaderMaterial).duplicate() as ShaderMaterial
		m.set_shader_parameter("ripple_map", Water.ripple_texture())
		var c := Hex.colour(Water.WATER_MAT[style]).srgb_to_linear()
		m.set_shader_parameter("shallow", Vector3(c.r, c.g, c.b))
		m.set_shader_parameter("deep", Vector3(c.r, c.g, c.b) * 0.7)
		if style == "great_lake":   # gentle waves
			m.set_shader_parameter("bump_strength", 3.0)
		elif style == "still_waters":
			m.set_shader_parameter("bump_strength", 0.6)
			m.set_shader_parameter("sparkle_strength", 1.0)
		elif style == "rapids":
			m.set_shader_parameter("period", 1.2)
			m.set_shader_parameter("deep", Vector3(c.r, c.g, c.b) * 0.85)
		_water_mats[style] = m
	return _water_mats[style]


func _build_water() -> void:
	var dressing_arrays := [PackedVector3Array(), PackedVector3Array(), PackedColorArray()]
	var foam_arrays := _foam_parts()   # a gorge's white water, unlit and moving
	var by_tile := {}           # water tile -> [its shores (world plan points, flow sign, speed), its flow signs]
	for t: Vector2i in water_shapes:
		var w: Dictionary = water_shapes[t]
		var at := Hex.tile_position(t.x, t.y)
		var near_rapids := []
		for n in Hex.NEIGHBOURS:
			near_rapids.append(Water.FAMILY.get(terrains.get(t + n)) == "rapids")
		var own := "rapids" if w.style == "rapids" else "lake" if w.kind in ["lake", "pond"] else "river"
		var speed := RIVER_SPEED if w.kind in ["river", "spring"] else LAKE_SPEED
		var signs := Water.flow_signs(w.ends, Water.flow_in(t.x, t.y, w.mask, near_rapids, own))
		var shores := []
		for k in w.shores.size():
			var pts := PackedVector2Array()
			for p in w.shores[k]:
				pts.append(at + p)
			shores.append([pts, signs[k], speed])
		by_tile[t] = [shores, signs]
	var groups := {}            # water style -> [vertices, depths, flows]
	for t: Vector2i in water_shapes:
		var w: Dictionary = water_shapes[t]
		var at := Hex.tile_position(t.x, t.y)
		var seed := "%d,%d" % [t.x, t.y]
		var style: String = w.style if Water.WATER_MAT.has(w.style) else ""
		var surface := _tile_surface(t, w, style, by_tile)
		var group: Array = groups.get_or_add(style, [PackedVector3Array(), PackedVector2Array(), PackedVector2Array()])
		for k in 3:
			group[k].append_array(surface[k])
		var parts := _tile_dressing(t, w, seed, at, by_tile[t])
		for k in 3:
			dressing_arrays[k].append_array(parts.dressing[k])
		for k in 5:
			foam_arrays[k].append_array(parts.foam[k])
		for b in parts.boats:
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
	_water_node.add_child(_flat_mesh("water_dressing", dressing_arrays, Piece.material()))
	if not foam_arrays[0].is_empty():
		var mi := _flat_mesh("gorge_foam", foam_arrays, _gorge_foam())
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.extra_cull_margin = 3.0   # it drifts in the shader
		_water_node.add_child(mi)
	for style in groups:
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = groups[style][0]
		arrays[Mesh.ARRAY_TEX_UV] = groups[style][1]
		arrays[Mesh.ARRAY_TEX_UV2] = groups[style][2]
		var normals := PackedVector3Array()
		normals.resize(groups[style][0].size())
		normals.fill(Vector3.UP)
		arrays[Mesh.ARRAY_NORMAL] = normals
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		var mi := MeshInstance3D.new()
		mi.name = "water_surface" if style == "" else "water_surface_" + style
		mi.mesh = mesh
		mi.material_override = _water_material(style)
		_water_node.add_child(mi)


## One mesh from a piece's [vertices, normals, colours].
func _flat_mesh(name: String, parts: Array, mat: Material) -> MeshInstance3D:
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = parts[0]
	arrays[Mesh.ARRAY_NORMAL] = parts[1]
	arrays[Mesh.ARRAY_COLOR] = parts[2]
	if parts.size() > 3:
		arrays[Mesh.ARRAY_TEX_UV] = parts[3]
		arrays[Mesh.ARRAY_TEX_UV2] = parts[4]
	var mi := MeshInstance3D.new()
	mi.name = name
	if not parts[0].is_empty():
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		mi.mesh = mesh
		mi.material_override = mat
	return mi


static func _piece_parts(p: Piece) -> Array:
	if p.is_empty():
		return [PackedVector3Array(), PackedVector3Array(), PackedColorArray()]
	var arrays := p.mesh().surface_get_arrays(0)
	return [arrays[Mesh.ARRAY_VERTEX], arrays[Mesh.ARRAY_NORMAL], arrays[Mesh.ARRAY_COLOR]]


## A tile's banks and dressing (water.add_water with plates=False, boats=False), kept while its shape stays the same.
func _tile_dressing(t: Vector2i, w: Dictionary, seed: String, at: Vector2, flow: Array) -> Dictionary:
	var key := [w.key, flow[1]]
	if _dressing_cache.has(t) and _dressing_cache[t].key == key:
		return _dressing_cache[t]
	var dressing := Piece.new()
	var foam := _foam_parts()
	var bank := Hex.colour("bank")
	dressing.offset = Vector3(at.x, at.y, 0)
	var boat_spots := []
	if w.has("gorge"):
		_add_gorge_dressing(dressing, foam, w, seed, at, flow[0])
	elif w.has("quads"):
		for quad: PackedVector2Array in w.quads:
			dressing.flat(quad, 0.025, bank)
		for wall in w.walls:   # the port's stone, where its land meets water
			var d: Vector2 = wall[1] - wall[0]
			var mid: Vector2 = (wall[0] + wall[1]) * 0.5
			dressing.box(Vector3(mid.x, mid.y, 0), Vector3(d.length(), 0.22, 0.17), Hex.colour("stone_block_dark"), 0.0, d.angle())
			dressing.box(Vector3(mid.x, mid.y, 0), Vector3(d.length() + 0.02, 0.26, 0.04), Hex.colour("stone_block"), 0.17, d.angle())
	else:
		for curve: PackedVector2Array in w.shores:
			for quad in Water.bank_strip(curve, 0.22):
				dressing.flat(quad, 0.025, bank)
		boat_spots = _add_dressing(dressing, w, seed)
	var out := {key = key, dressing = _piece_parts(dressing), foam = foam, boats = boat_spots}
	_dressing_cache[t] = out
	return out


## A tile's water surface, kept until its shape or flow, or a neighbour's, changes: only the shores of the tile and those
## round it can be the nearest to a point on it. [vertices, depths, flows].
func _tile_surface(t: Vector2i, w: Dictionary, style: String, by_tile: Dictionary) -> Array:
	var key := [w.key, by_tile[t][1]]
	var shores: Array = by_tile[t][0].duplicate()
	for n in Hex.NEIGHBOURS:
		var o: Vector2i = t + n
		if by_tile.has(o):
			var same: bool = (water_shapes[o].style if Water.WATER_MAT.has(water_shapes[o].style) else "") == style
			key.append([water_shapes[o].key, by_tile[o][1]])
			if same:
				shores.append_array(by_tile[o][0])
		else:
			key.append(null)
	if _surface_cache.has(t) and _surface_cache[t][0] == key:
		return _surface_cache[t][1]
	var at := Hex.tile_position(t.x, t.y)
	var outlines := []
	for poly: PackedVector2Array in w.outlines:
		var pts := PackedVector2Array()
		for p in poly:
			pts.append(at + p)
		outlines.append(pts)
	var surface := _water_surface(outlines, shores, [w.mask, w.widths, at] if w.has("gorge") else null)
	_surface_cache[t] = [key, surface]
	return surface


static func _foam_parts() -> Array:
	return [PackedVector3Array(), PackedVector3Array(), PackedColorArray(), PackedVector2Array(), PackedVector2Array()]


## One ring of foam, in the tile's plan frame, for shaders/gorge_foam.gdshader: UV its drift (world X, Z, metres a second),
## UV2 its middle (world X, Z), COLOR.r its phase, COLOR.g how its water rises per metre, COLOR.b its pace. No drift: it stays
## and churns (round a boulder, under a fall).
static func _foam_ring(parts: Array, ring: Array, middle: Vector2, at: Vector2, drift: Vector2, rise: float, hash_: Vector2) -> void:
	var col := Color(hash_.x, clampf(rise * 0.25 + 0.5, 0.0, 1.0), hash_.y, 1.0)
	var mid := Hex.to3(at + middle)
	for k in range(1, ring.size() - 1):
		for q: Vector3 in [ring[0], ring[k + 1], ring[k]]:   # clockwise for Godot's front face
			parts[0].append(Hex.to3(at + Vector2(q.x, q.y), q.z))
			parts[1].append(Vector3.UP)
			parts[2].append(col)
			parts[3].append(drift)
			parts[4].append(Vector2(mid.x, mid.z))


## What water.add_water puts on a gorge: foam where a waterfall lands and a rock either side of its top, the white water and
## boulders. The white water moves (Ethan, Nov 3, 2026): streaks drift along the flow, and foam held by a boulder or a fall churns.
func _add_gorge_dressing(p: Piece, white: Array, w: Dictionary, seed: String, at: Vector2, shores: Array) -> void:
	var rf := PyRandom.new(seed + "-falls")
	var rh := PyRandom.new(seed + "-foam")
	for f in w.gorge.falls:
		var d: Vector2 = f.foot - f.top
		var l := d.length()
		var into: Vector2 = d / (l if l != 0.0 else 1.0)
		var side := Vector2(-into.y, into.x)
		for k in 9:
			var q: Vector2 = f.foot + side * (f.half * (-0.8 + 1.6 * k / 8.0)) + into * rf.uniform(-0.05, 0.2)
			var ring := []
			for j in 7:
				var a := TAU * j / 7.0
				var x: float = q.x + rf.uniform(0.2, 0.34) * cos(a)
				var y: float = q.y + rf.uniform(0.14, 0.26) * sin(a)
				ring.append(Vector3(x, y, -Gorge.DEPTH + 0.02))
			_foam_ring(white, ring, q, at, Vector2.ZERO, 0.0, Vector2(rh.random(), rh.random()))
		for k in 6:
			var q: Vector2 = f.foot + side * (rf.uniform(-f.half, f.half) * 0.8) + into * rf.uniform(0.35, 1.05)
			var ring := []
			for j in 8:
				var a := TAU * j / 8.0
				var x: float = q.x + rf.uniform(0.2, 0.42) * cos(a)
				var y: float = q.y + rf.uniform(0.07, 0.16) * sin(a)
				ring.append(Vector3(x, y, -Gorge.DEPTH + 0.015))
			_foam_ring(white, ring, q, at, Vector2.ZERO, 0.0, Vector2(rh.random(), rh.random()))
		for sign_ in [-1, 1]:
			var q: Vector2 = f.top + side * (sign_ * (f.top_half + 0.06)) + into * 0.14
			p.blob(Vector3(q.x, q.y, -0.06), rf.uniform(0.15, 0.2), Hex.colour("rock_wet"), 0.0, 0.7)
	var marks := Water.rapids_marks(w.mask, seed, w.widths, w.band)
	for q in marks.foam:
		var z := Gorge.water_z(w.mask, w.widths, q[0]) + 0.012
		var ring := []
		for k in 8:
			var a := TAU * k / 8.0
			var pt: Vector2 = q[0] + Vector2(q[2] * cos(a), q[3] * sin(a)).rotated(q[1])
			ring.append(Vector3(pt.x, pt.y, z))
		var drift := Vector2.ZERO
		var rise := 0.0
		if not q[4]:   # q[4]: held by a boulder
			var df := _depth_flow(at + q[0], shores)
			var flow := Vector2(df.y, df.z)
			if flow.length() > 1e-4:
				drift = flow.normalized() * FOAM_SPEED
				var ahead: Vector2 = q[0] + Vector2(drift.x, -drift.y).normalized() * 0.3
				rise = (Gorge.water_z(w.mask, w.widths, ahead) - z + 0.012) / 0.3
		_foam_ring(white, ring, q[0], at, drift, rise, Vector2(rh.random(), rh.random()))
	var rr := PyRandom.new(seed + "-boulders")
	for q in marks.boulders:
		p.blob(Vector3(q[0].x, q[0].y, Gorge.water_z(w.mask, w.widths, q[0])), q[1], Hex.colour(["rock_wet", "rock_wet_dark"][rr.randbelow(2)]), 0.0, 0.75)


func _add_lens(p: Piece, at: Vector2, ang: float, long_: float, wide: float, col: String, z: float) -> void:
	var outline := PackedVector2Array()
	for k in 8:
		var a := TAU * k / 8
		outline.append(at + Vector2(long_ * cos(a), wide * sin(a)).rotated(ang))
	p.flat(outline, z, Hex.colour(col))


## Returns where its boats go: they're their own nodes, so they can bob (render_animation.bob_boats).
func _add_dressing(p: Piece, w: Dictionary, seed: String) -> Array:
	var d := Water.dressing(w.outlines, w.shores, w.kind, seed)
	var style: String = w.style
	var lands := Water.landings(w.mask, seed, w.widths, style)
	var lines: Dictionary = Water.water_routes(w.mask, seed, w.widths, style).lines
	d.reeds = Water.clear_of_landings(d.reeds, lands)
	d.rocks = Water.clear_of_landings(d.rocks, lands)
	d.boats = Water.clear_of_routes(d.boats, lines)
	# A jetty reaches into the water, so its tip stays off the routes too.
	d.jetties = d.jetties.filter(func(j): return Water._line_dist(j[0] + Vector2.from_angle(j[1]) * 1.1, lines) > 0.45)
	if Water.WATER_MAT.has(style):
		d.lilies = []
		d.jetties = []
		d.boats = []
	if style == "great_lake":
		for q in Water.lake_waves(w.outlines, w.shores, seed):
			_add_lens(p, q[0], q[1], q[2], q[3], "wave_light", 0.034)
	elif style == "still_waters":
		for q in Water.still_lilies(w.outlines, w.shores, seed, w.band):
			p.cylinder(Vector3(q[0].x, q[0].y, 0), q[1], 0.012, Hex.colour("lily"), 7, 0.032)
			if q[2] != "":
				p.cone(Vector3(q[0].x, q[0].y, 0), q[1] * 0.5, 0.11, Hex.colour(q[2]), 5, 0.044)
		if w.has("rock"):
			for q in w.rock.stones:
				p.cylinder(Vector3(q[0].x, q[0].y, 0), q[1], 0.08, Hex.colour("smooth_stone"), 7, 0.02)
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
	if style == "delta":
		# The river delta's islands, boats, jetty and crates (water.add_water(..., style="delta")).
		var dd := Water.delta_dressing(w.outlines, w.shores, w.kind, seed, w.band)
		boat_spots = boat_spots + Water.clear_of_routes(dd.boats, lines)
		for poly: PackedVector2Array in dd.islands:
			p.flat(poly, 0.036, Hex.colour("sandbar"))
			for k in range(0, poly.size(), 5):
				var q := (poly[k] + poly[0]) * 0.5
				p.cone(Vector3(q.x, q.y, 0), 0.05, rng.uniform(0.35, 0.55), Hex.colour("reed"), 4, 0.03)
		for j in Water.clear_of_routes(dd.jetties, lines, 0.45):
			var ang: float = j[1]
			var dir := Vector2(cos(ang), sin(ang))
			var tip: Vector2 = j[0] + dir * 0.5
			p.box(Vector3(tip.x, tip.y, 0), Vector3(1.2, 0.45, 0.06), Hex.colour("trunk"), 0.12, ang)
			for s in [-1, 1]:  # cargo crates on the bank beside it
				var crate: Vector2 = j[0] - (dir * 0.45 + Vector2(-dir.y, dir.x) * (0.45 * s))
				p.box(Vector3(crate.x, crate.y, 0), Vector3(0.3, 0.3, 0.28), Hex.colour("crate"), 0.0, ang + 0.2 * s)
	return boat_spots


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
		for g: StandardMaterial3D in _marsh_glow.values():
			g.emission_energy_multiplier = 0.3 + 2.5 * night   # PLACEHOLDER: lit a little by day
		SwampFx.set_night(night)
		FeyFx.set_night(night)
		_lava.emission_energy_multiplier = (0.75 + 0.25 * sin(TAU * _time / 4.0)) * (0.8 + 2.0 * night)   # PLACEHOLDER: pulses slowly, glows at night
		ForestFx.set_night(night)
		DesertFx.set_night(night)
		(load("res://shaders/water.tres") as ShaderMaterial).set_shader_parameter("night", night)
		for style in _water_mats:
			_water_mats[style].set_shader_parameter("night", night)
		if _fall_mat:
			_fall_mat.set_shader_parameter("night", night)
		if _gorge_foam_mat:
			_gorge_foam_mat.set_shader_parameter("night", night)
		for m in _still_mists:   # thin mist at dawn on still waters (PLACEHOLDER: while the light is low)
			if is_instance_valid(m):
				m.visible = night > 0.15 and night < 0.85
	var s := _time
	for k in boats.size():
		boats[k].position.y = 0.03 * sin(TAU * s / 2.0 + k)
		boats[k].rotation.x = 0.05 * sin(TAU * s / 3.0 + k)
	for k in _port_boats.size():   # the River Port's boats, each on its own tile's node
		if is_instance_valid(_port_boats[k]):
			_port_boats[k].position.y = 0.03 * sin(TAU * s / 2.0 + k)


static func _seg_dist(p: Vector2, a: Vector2, b: Vector2) -> float:
	var ab := b - a
	var l2 := ab.length_squared()
	var t := clampf((p - a).dot(ab) / (l2 if l2 != 0.0 else 1.0), 0.0, 1.0)
	return (p - (a + ab * t)).length()


## One tile's water, with depth (UV.x) and flow (UV2, world XZ) per vertex, like render_animation.water_mesh(): outline
## points, a staggered grid inside, Delaunay triangles. slope: a gorge's water, [mask, widths, tile], Gorge.water_z.
func _water_surface(outlines: Array, shores: Array, slope) -> Array:
	var verts := PackedVector3Array()
	var depths := PackedVector2Array()
	var flows := PackedVector2Array()
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
		var at_point := {}
		var tris := Geometry2D.triangulate_delaunay(pts)
		for k in range(0, tris.size(), 3):
			var a := pts[tris[k]]; var b := pts[tris[k + 1]]; var c := pts[tris[k + 2]]
			if not Water.point_in(poly, (a + b + c) / 3.0):
				continue
			if (b - a).cross(c - a) < 0:
				var tmp := b; b = c; c = tmp
			for p in [a, c, b]:   # clockwise for Godot's front face
				if not at_point.has(p):
					at_point[p] = _depth_flow(p, shores)
				var df: Vector3 = at_point[p]
				depths.append(Vector2(df.x, 0))
				flows.append(Vector2(df.y, df.z))
				verts.append(Hex.to3(p, 0.03 if slope == null else Gorge.water_z(slope[0], slope[1], p - slope[2])))
	return [verts, depths, flows]


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
