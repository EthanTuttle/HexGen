class_name GroundCover
extends RefCounted
## Port of art/scripts/ground_cover.py: tufts, flowers and pebbles scattered from one world-space
## pattern, with density per terrain fading toward the neighbour's within BLEND metres of an edge.

const CELL := 0.55
const BLEND := 1.6
## Share of cells that get a prop, per terrain (placeholders from ground_cover.py).
const DENSITY := {"plains": 0.5, "river": 0.3, "forest": 0.18, "farmland": 0.0, "village": 0.0,
	"hills": 0.0, "swamp": 0.22, "desert": 0.0, "ruins": 0.4,  # hills and swamp pieces hold their own
	# tier 1 region variants
	"deep_forest": 0.08, "meadows": 0.85, "highlands": 0.0, "windmill_country": 0.0, "market_town": 0.0,
	"delta": 0.3, "great_lake": 0.3, "rapids": 0.3, "still_waters": 0.3, "riverport": 0.3, "serpentlair": 0.3, "trollbridge": 0.3, "meditationrock": 0.3, "bog": 0.16, "wisp_marsh": 0.1, "rot_swamp": 0.14, "smugglers_bayou": 0.14, "witchhut": 0.16, "wisphollow": 0.1, "plaguepit": 0.08, "thievesguild": 0.14, "wasteland": 0.0, "excavation": 0.3,
	# tier 2 and class variants
	"fey_wood": 0.18, "dark_wood": 0.05, "heartwood": 0.12, "feywild_crossing": 0.0, "feygate": 0.0,
	# landmark tiles
	"treeoflife": 0.1, "hiddenshrine": 0.08, "feycourt": 0.18, "spidernest": 0.05,
	"greatwindmill": 0.0, "abandonedbarn": 0.0, "militiabarn": 0.0, "harvestfestival": 0.0,
	"nomadcamp": 0.0, "oldbattlefield": 0.03, "thunderbirdnest": 0.1, "traininggrounds": 0.0,
	# farmland tier 2 (farm pieces hold their own, like farmland)
	"haunted_homesteads": 0.0, "raided_farms": 0.0, "cider_orchards": 0.0,
	# plains tier 2 and class variant
	"battlefield": 0.22, "stormy_plains": 0.5, "tourney_fields": 0.05,
	# hills variants and landmarks (their pieces hold their own)
	"snowy_peaks": 0.0, "volcanic_peaks": 0.0, "monastery_heights": 0.0, "clanhall": 0.0, "yeticave": 0.0,
	"salamanderden": 0.0, "library": 0.0,
	# town variants and landmarks
	"tradinghouse": 0.0, "fortified_town": 0.0, "keep": 0.0, "slums": 0.0, "blackmarket": 0.0, "scholars_town": 0.0,
	"college": 0.0,
	# desert variants and landmarks (their pieces and sand hold their own; the canyon's floor is below the land)
	"dunfairetower": 0.2, "eastrimechapel": 0.0, "montotown": 0.15, "sternbrunnspire": 0.0, "oaklantern": 0.15, "weizenhof": 0.0,   # starting tiles: thinner than their terrains
	"sandstonesphinx": 0.0, "badlands": 0.0, "raiderstronghold": 0.0, "oasis": 0.0, "oasisbazaar": 0.0, "oasispool": 0.0,
	"canyon": 0.0, "echocave": 0.0}
## Tuft colour where it isn't the usual grass_ink; terrains in NO_FLOWERS get tufts instead of flowers.
const TUFT := {"swamp": "tuft_swamp", "bog": "tuft_bog", "witchhut": "tuft_bog", "wisp_marsh": "tuft_wisp", "wisphollow": "tuft_wisp", "rot_swamp": "tuft_rot", "plaguepit": "tuft_rot",
	"smugglers_bayou": "tuft_swamp", "thievesguild": "tuft_swamp", "dark_wood": "tuft_dark_wood", "spidernest": "tuft_dark_wood", "battlefield": "tuft_steppe",
	"oldbattlefield": "tuft_steppe", "stormy_plains": "tuft_storm", "thunderbirdnest": "tuft_storm"}
const NO_FLOWERS := ["swamp", "bog", "witchhut", "wisp_marsh", "wisphollow", "rot_swamp", "plaguepit", "smugglers_bayou", "thievesguild", "dark_wood", "spidernest", "battlefield", "oldbattlefield", "stormy_plains", "thunderbirdnest",
	"tourney_fields", "traininggrounds"]
## Tufts lean hard one way, +X in world space, the wind's direction. Their vertex alpha of 0 lets the gust ripple
## (shaders/grass.gdshader) find them, with no extra material.
const BENT := ["stormy_plains", "thunderbirdnest"]
const FLOWERS := ["flower", "flower_pink", "flower_white", "flower_blue"]

const R := Water.R
const A := Water.A


static var _grass: ShaderMaterial


## The ground cover's material: vertex colours, bending away from the minis (shaders/grass.gdshader; the
## party walker sets their positions).
static func grass_material() -> ShaderMaterial:
	if _grass == null:
		_grass = ShaderMaterial.new()
		_grass.shader = load("res://shaders/grass.gdshader")
		_grass.set_shader_parameter("radius", Rules.GRASS_PART_RADIUS)
		_grass.set_shader_parameter("minis", PackedVector3Array([Vector3(1e5, 0, 1e5), Vector3(1e5, 0, 1e5),
				Vector3(1e5, 0, 1e5), Vector3(1e5, 0, 1e5)]))
	return _grass


static func hash01(ix: int, iy: int, k: int) -> float:
	var h := (ix * 374761393 + iy * 668265263 + k * 1442695041) & 0xFFFFFFFF
	h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
	h ^= h >> 16
	return h / 4294967296.0


## Axial (q, r) of the pointy-top tile holding plan point p (hexkit.tile_position, inverted).
static func tile_at(p: Vector2) -> Vector2i:
	var r := -p.y / (1.5 * R)
	var q := p.x / (2 * A) - r / 2
	var s := -q - r
	var rq := roundf(q); var rr := roundf(r); var rs := roundf(s)
	var dq := absf(rq - q); var dr := absf(rr - r); var ds := absf(rs - s)
	if dq > dr and dq > ds:
		rq = -rr - rs
	elif dr > ds:
		rr = -rq - rs
	return Vector2i(int(rq), int(rr))


static func density(terrains: Dictionary, p: Vector2) -> float:
	var t := tile_at(p)
	if not terrains.has(t):
		return 0.0
	var local := p - Hex.tile_position(t.x, t.y)
	var d_own: float = DENSITY[terrains[t]]
	var dens := d_own
	for i in 6:
		var to_edge := A - local.dot(Water.normal(i))
		if to_edge < BLEND:
			var other = terrains.get(t + Hex.NEIGHBOURS[i])
			var d_other: float = DENSITY[other] if other != null else d_own
			dens += 0.5 * (1 - to_edge / BLEND) * (d_other - d_own)
	return maxf(0.0, dens)


## [kind, plan point, cell] for the whole map. water_shapes maps (q, r) -> tile_water() result.
static func scatter(terrains: Dictionary, water_shapes: Dictionary) -> Array:
	var x0 := INF; var x1 := -INF; var y0 := INF; var y1 := -INF
	for t: Vector2i in terrains:
		var c := Hex.tile_position(t.x, t.y)
		x0 = minf(x0, c.x); x1 = maxf(x1, c.x); y0 = minf(y0, c.y); y1 = maxf(y1, c.y)
	var out := []
	for ix in range(int(floor((x0 - A) / CELL)), int(ceil((x1 + A) / CELL))):
		for iy in range(int(floor((y0 - R) / CELL)), int(ceil((y1 + R) / CELL))):
			var p := Vector2((ix + hash01(ix, iy, 0)) * CELL, (iy + hash01(ix, iy, 1)) * CELL)
			var item := _keep(terrains, water_shapes, ix, iy, p)
			if not item.is_empty():
				out.append(item)
	return out


## [kind, point, cell] if cell (ix, iy) gets a prop, else [].
static func _keep(terrains: Dictionary, water_shapes: Dictionary, ix: int, iy: int, p: Vector2, clear := [], marsh := {}) -> Array:
	var dens := density(terrains, p)
	if hash01(ix, iy, 3) >= dens:
		return []
	for c in clear:   # a piece's no_cover circle: burns, yards. [x, y, radius]
		if p.distance_squared_to(Vector2(c[0], c[1])) < c[2] * c[2]:
			return []
	var t := tile_at(p)
	if SwampLands.cover_wet(terrains, marsh, p.x, p.y, t):   # the swamp's own water, mud, planks, tracks and finishes
		return []
	if water_shapes.has(t):
		var local := p - Hex.tile_position(t.x, t.y)
		var w: Dictionary = water_shapes[t]
		if w.get("cover_outlines", w.outlines).any(func(o): return Water.point_in(o, local)):
			return []
		if _near_shore(local, w.get("cover_shores", w.shores), 0.45):
			return []
	var k := hash01(ix, iy, 2)
	if terrains[t] == "meadows":
		# Wildflower drifts: a slow world-space wave decides where flowers crowd out the grass.
		var drift := 0.5 + 0.5 * sin(p.x / 3.1 + 0.4) * sin(p.y / 2.6 + p.x / 5.0)
		return ["flower" if k < 0.3 + 0.85 * drift else "tuft", p, Vector2i(ix, iy), true]
	if terrains[t] in NO_FLOWERS:
		return ["tuft" if k < 0.85 else "pebble", p, Vector2i(ix, iy)]
	return ["tuft" if k < 0.7 else "flower" if k < 0.93 else "pebble", p, Vector2i(ix, iy)]


## The tuft colour at p (ground_cover.tuft_colour). Within BLEND of an edge whose neighbour has another tuft
## colour, some tufts take the neighbour's, from none at BLEND to half right at the edge. k: hash stream 5.
static func tuft_colour(terrains: Dictionary, p: Vector2, k: float) -> String:
	var t := tile_at(p)
	var own: String = TUFT.get(terrains.get(t), "grass_ink")
	var local := p - Hex.tile_position(t.x, t.y)
	for i in 6:
		var to_edge := A - local.dot(Water.normal(i))
		var other = terrains.get(t + Hex.NEIGHBOURS[i])
		if to_edge < BLEND and other != null:
			var theirs: String = TUFT.get(other, "grass_ink")
			if theirs != own and k < 0.5 * (1 - to_edge / BLEND):
				return theirs
	return own


static func _near_shore(p: Vector2, shores: Array, d: float) -> bool:
	for c: PackedVector2Array in shores:
		for s in c:
			if (p - s).length() < d:
				return true
	return false


## The ground cover of one tile: the cells of the world-space pattern whose point lands in it.
## Gives the same props as the whole-map scatter, so tiles can be rebuilt one at a time.
static func build_tile(terrains: Dictionary, water_shapes: Dictionary, t: Vector2i, clear := [], marsh := {}) -> MeshInstance3D:
	var c := Hex.tile_position(t.x, t.y)
	var items := []
	for ix in range(int(floor((c.x - A) / CELL)), int(ceil((c.x + A) / CELL))):
		for iy in range(int(floor((c.y - R) / CELL)), int(ceil((c.y + R) / CELL))):
			var p := Vector2((ix + hash01(ix, iy, 0)) * CELL, (iy + hash01(ix, iy, 1)) * CELL)
			if tile_at(p) != t:
				continue
			var item := _keep(terrains, water_shapes, ix, iy, p, clear, marsh)
			if not item.is_empty():
				items.append(item)
	return _build(items, terrains)


static func build(terrains: Dictionary, water_shapes: Dictionary) -> MeshInstance3D:
	return _build(scatter(terrains, water_shapes), terrains)


static func _build(items: Array, terrains: Dictionary) -> MeshInstance3D:
	var piece := Piece.new()
	var rock := Hex.colour("rock")
	for item in items:
		var cell: Vector2i = item[2]
		var rng := PyRandom.new(hash01(cell.x, cell.y, 4))
		var at := Vector3(item[1].x, item[1].y, 0)
		match item[0]:
			"tuft":
				if terrains.get(tile_at(item[1])) in BENT:
					var h := rng.uniform(0.3, 0.45)
					var bent := Color(Hex.colour(tuft_colour(terrains, item[1], hash01(cell.x, cell.y, 5))), 0.0)
					piece.spike(at, at + Vector3(h * 0.85, h * 0.2, h * 0.6), rng.uniform(0.09, 0.13), bent)
					continue
				var radius := rng.uniform(0.12, 0.2)
				var height := rng.uniform(0.2, 0.35)
				var ink := Hex.colour(tuft_colour(terrains, item[1], hash01(cell.x, cell.y, 5)))
				piece.cone(at, radius, height, ink, 4, 0.0, rng.uniform(0, 1))
			"flower":
				# Meadows: one colour per drift; the same slow wave picks it, so colours come in patches.
				var hue := "flower"
				if item.size() > 3:
					var p: Vector2 = item[1]
					hue = FLOWERS[posmod(int((sin(p.x / 4.7) + sin(p.y / 3.9 + 1.0) + 2) * 1.999), 4)]
				# The meadows' flowers are bigger, so the drifts read.
				var size := Vector3(0.14, 0.14, 0.17) if item.size() > 3 else Vector3(0.08, 0.08, 0.12)
				piece.box(at, size, Hex.colour(hue), 0.0, rng.uniform(0, 1))
			_:
				piece.blob(at, rng.uniform(0.07, 0.12), rock, 0.0, 0.6)
	var mi := piece.instance("ground_cover")
	mi.material_override = grass_material()
	return mi
