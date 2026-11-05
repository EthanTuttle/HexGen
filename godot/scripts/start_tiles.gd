class_name StartTiles
extends RefCounted
## Port of art/scripts/start_tiles.py's plain section (art/handoff/start_tiles_kit.md): the six starting tiles of the first playable, one per background
## (design/06 -> First playable, design/07 -> Starting tiles). Never turned: the door faces the map camera. Routes run in along a spoke to a ring, round it, and in to the stop.

const RING_R := 2.9
const STOP_R := 2.05
const STOP_EDGE := 5
const DECK_Z := 0.3         # Monto Town's bridge and boardwalks
const BRIDGE_FAR := 2       # its bridge runs from edge 5 to this edge, through the middle
const MOUTHS := [0, 3]      # Monto's river runs from edge 0 to edge 3; only these edges can touch a river or lake (design/02)
const MOUTH_WATER := [true, false, false, true, false, false]   # Monto's water, whatever its neighbours are
const WATER_SEED := "monto"
const APRON_X := Hex.A - 0.2   # the stone apron's walk at a land mouth
const APRON_Z := 0.06
const APRON_Y := -1.05         # the bank it reaches, in the mouth's own frame (edge along +x)

const MONTO := "montotown"
const STARTS := {"dunfairetower": "ruins", "eastrimechapel": "hills", "montotown": "river", "sternbrunnspire": "desert", "oaklantern": "forest", "weizenhof": "farmland"}
const GROUND := {"dunfairetower": "plains", "eastrimechapel": "hills", "montotown": "plains", "sternbrunnspire": "desert", "oaklantern": "forest", "weizenhof": "farmland"}
const BACKGROUND := {"soldier": "dunfairetower", "acolyte": "eastrimechapel", "criminal": "montotown", "sage": "sternbrunnspire", "folk_hero": "oaklantern", "noble": "weizenhof"}


static func is_start(name) -> bool:
	return STARTS.has(name)


## A tile next to a starting tile: it keeps clear ground, no mountain, ridge or peak, so a ring of hills can't shut the start in.
static func near_start(terrains: Dictionary, t: Vector2i) -> bool:
	for n: Vector2i in Hex.NEIGHBOURS:
		if STARTS.has(terrains.get(t + n)):
			return true
	return false


## Can a tile of this terrain go on Monto Town's edge i? A river or lake only at a mouth.
static func monto_allows(i: int, terrain: String) -> bool:
	return i in MOUTHS or terrain != "river"


## Spokes from each edge to the ring, the ring, and the way in to the stop, tile-local. Two edges join the short way round.
static func ring_lines() -> Array:
	var lines := []
	var ring := PackedVector2Array()
	for k in 24:
		ring.append(Vector2.from_angle(deg_to_rad(15.0 * k)) * RING_R)
	ring.append(ring[0])
	lines.append(ring)
	for i in 6:
		lines.append(PackedVector2Array([Water.normal(i) * Hex.A, Water.normal(i) * RING_R]))
	lines.append(PackedVector2Array([Water.normal(STOP_EDGE) * RING_R, stop()]))
	return lines


static func stop() -> Vector2:
	return Water.normal(STOP_EDGE) * STOP_R


## The bridge's height, u from the tile's middle along it: level, with a ramp at each end down to the edge's midpoint.
static func deck_z(u: float) -> float:
	return DECK_Z * minf(1.0, (Hex.A - u) / 0.7)


## Where edge i's side way meets the bridge: straight in from its midpoint to the nearest point of the bridge. [distance along it, point]
static func _monto_side(i: int) -> Array:
	var d := Water.normal(STOP_EDGE)
	var u := Water.normal(i).dot(d) * Hex.A
	return [u, d * u]


## The (x, y, z) walk on Monto Town from edge i to where it joins the bridge, and how far along the bridge that is. wet: a mouth with water beyond has no apron: straight out to the bank.
static func _monto_join(e: int, wet := false) -> Array:
	if e == STOP_EDGE:
		return [PackedVector3Array(), Hex.A]
	if e == BRIDGE_FAR:
		return [PackedVector3Array(), -Hex.A]
	var side := _monto_side(e)
	var q: Vector2 = side[1]
	var n := Water.normal(e)
	var line := PackedVector3Array()
	if e in MOUTHS:
		var frame := func(x: float, y: float) -> Vector2: return Vector2(n.x * x - n.y * y, n.y * x + n.x * y)
		line.append(_v3(frame.call(Hex.A, 0.0), 0.0))
		if not wet:
			line.append(_v3(frame.call(APRON_X, 0.0), APRON_Z))
			for k in range(1, 6):
				line.append(_v3(frame.call(APRON_X, APRON_Y * k / 5.0), APRON_Z))
		var bank: Vector2 = frame.call(APRON_X, APRON_Y)
		if wet:
			line.append(_v3(bank, APRON_Z))
		for k in range(1, 8):
			line.append(_v3(bank.lerp(q, k / 8.0), APRON_Z + (DECK_Z - APRON_Z) * smoothstep(0.5, 1.0, k / 8.0)))
		return [line, side[0]]
	for k in 12:
		line.append(_v3((n * Hex.A).lerp(q, k / 12.0), DECK_Z * smoothstep(0.5, 1.0, k / 12.0)))
	return [line, side[0]]


## Monto Town's bridge, tile-local, in small steps.
static func monto_bridge() -> PackedVector3Array:
	var d := Water.normal(STOP_EDGE)
	var line := PackedVector3Array()
	for k in 44:
		var u := Hex.A - 2.0 * Hex.A * k / 43.0
		line.append(_v3(d * u, deck_z(absf(u))))
	return line


## Monto's walks: every side way, then the bridge. wet[i]: a mouth with water beyond it.
static func monto_lines(wet: Array) -> Array:
	var lines := [monto_bridge()]
	for e in 6:
		var j: Array = _monto_join(e, wet[e])
		if not j[0].is_empty():
			var line: PackedVector3Array = j[0]
			line.append(_v3(_monto_side(e)[1], deck_z(absf(j[1]))))
			lines.append(line)
	return lines


static func _v3(p: Vector2, z: float) -> Vector3:
	return Vector3(p.x, p.y, z)
