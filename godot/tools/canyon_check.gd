extends SceneTree
## Checks the canyon, desert lands and sand ports (scripts/canyon.gd, desert_lands.gd, sand.gd) against art/scripts/canyon.py,
## desert_lands.py and sand.py on the same regions. Cases come from tools/canyon_cases.py, from the repo root:
##   python3 -I godot/tools/canyon_cases.py art/scripts /tmp/canyon_cases.json
##   godot --headless --path godot --script res://tools/canyon_check.gd -- /tmp/canyon_cases.json

var bad := 0
var mesas_seen := 0
var mesas_same := 0
var values_seen := 0
var values_off := 0


var mesa_stray := 0.0
var mesa_area := 0.0


func _area(m: PackedVector2Array) -> float:
	var total := 0.0
	for k in m.size():
		total += m[k - 1].x * m[k].y - m[k].x * m[k - 1].y
	return absf(total) / 2.0


func _close(a: PackedVector2Array, b: PackedVector2Array) -> bool:
	for k in a.size():
		if a[k].distance_to(b[k]) > 0.01:
			return false
	return true


func _diff(what: String, ok: bool, detail = "") -> void:
	if not ok:
		bad += 1
		if bad < 40:
			print("DIFF ", what, " ", detail)


func _init() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	var worst := {value = 0.0, width = 0.0, mouth = 0.0, sand = 0.0}
	for n in data.cases.size():
		var c: Dictionary = data.cases[n]
		var region: Array = c.region.map(func(t): return Vector2i(t[0], t[1]))
		var lm := Vector2i(c.landmark[0], c.landmark[1])
		var turn := Sand.sphinx_turn(lm, region)
		_diff("turn", turn == int(c.turn), n)
		var f := Canyon.Field.new(region, lm, turn)
		var mine := f.openset.keys().map(func(k: Vector3i): return [k.x, k.y, k.z])
		mine.sort()
		_diff("openset", str(mine) == str(c.openset.map(func(e): return [int(e[0]), int(e[1]), int(e[2])])), n)
		_diff("entrances", str(f.entrances.map(func(k: Vector3i): return [k.x, k.y, k.z])) == str(c.entrances.map(func(e): return [int(e[0]), int(e[1]), int(e[2])])), n)
		_diff("mesa count", f.mesas.size() == c.mesas.size(), [n, f.mesas.size(), c.mesas.size()])
		mesas_seen += c.mesas.size()
		for m in c.mesas:   # by shape, in case they come in another order; a corner can differ where the trace has a tie
			var theirs := PackedVector2Array()
			for q in m:
				theirs.append(Vector2(q[0], q[1]))
			var same := f.mesas.any(func(o): return o.size() == theirs.size() and _close(o, theirs))
			mesas_same += 1 if same else 0
			var mid := Vector2.ZERO
			for q in theirs:
				mid += q
			mid /= theirs.size()
			var best: PackedVector2Array = theirs
			var near := INF
			for o: PackedVector2Array in f.mesas:
				var om := Vector2.ZERO
				for q in o:
					om += q
				om /= o.size()
				if om.distance_to(mid) < near:
					near = om.distance_to(mid)
					best = o
			mesa_stray = maxf(mesa_stray, Canyon.outline_gap_most(best, theirs))
			mesa_area = maxf(mesa_area, absf(_area(best) - _area(theirs)) / _area(theirs))
		for p in c.values:
			var d := absf(f.value(p[0], p[1]) - p[2])
			worst.value = maxf(worst.value, d)
			values_seen += 1
			if d >= 0.01:
				values_off += 1
		for r in c.ramps:
			var t := Vector2i(r.tile[0], r.tile[1])
			var e: int = int(r.edge)
			var line := Canyon.ramp_line(t, e, lm, turn)
			_diff("ramp points", line.size() == r.line.size(), [n, t, e])
			for k in mini(line.size(), r.line.size()):
				_diff("ramp line", line[k].distance_to(Vector3(r.line[k][0], r.line[k][1], r.line[k][2])) < 0.001, [n, t, e, k])
			var secs := Canyon.ramp_sections(t, e, f, lm, turn)
			_diff("section count", secs.size() == r.sections.size(), [n, t, e, secs.size(), r.sections.size()])
			for k in mini(secs.size(), r.sections.size()):
				var a: Array = secs[k]
				var b: Array = r.sections[k]
				_diff("section place", Vector3(a[0], a[1], a[2]).distance_to(Vector3(b[0], b[1], b[2])) < 0.002, [n, t, e, k])
				var w := maxf(absf(a[5] - b[5]), absf(a[6] - b[6]))
				if k == 0:   # at z = 0 exactly: which side of a band's line a point is on comes down to float32 against double
					worst.mouth = maxf(worst.mouth, w)
					continue
				worst.width = maxf(worst.width, w)
				_diff("section width", w < 0.13, [n, t, e, k, a, b])
		# Badlands
		var terrains := {}
		for t: Vector2i in region:
			terrains[t] = "badlands"
		terrains[lm] = "raiderstronghold"
		var dist := {}
		for key in c.dist:
			var q: PackedStringArray = key.split(",")
			dist[Vector2i(int(q[0]), int(q[1]))] = int(c.dist[key])
		var feats := DesertLands.badlands_features(terrains, dist)
		_diff("feature count", feats.size() == c.features.size(), [n, feats.size(), c.features.size()])
		for k in mini(feats.size(), c.features.size()):
			var a: Array = feats[k]
			var b: Array = c.features[k]
			_diff("feature", a[1] == b[0] and Vector2(a[2], a[3]).distance_to(Vector2(b[1], b[2])) < 0.001 and absf(a[4] - b[3]) < 0.01, [n, a, b])
		if c.oasis != null:
			var two := DesertLands.oasis_tiles(region)
			_diff("oasis", two[0] == Vector2i(c.oasis[0][0], c.oasis[0][1]) and two[1] == Vector2i(c.oasis[1][0], c.oasis[1][1]), [n, two, c.oasis])
		# Sand
		var tiles := {}
		for t: Vector2i in region:
			tiles[t] = c.look
		if c.look == "wasteland":
			tiles[lm] = "sandstonesphinx"
		for t in c.plains:
			tiles[Vector2i(t[0], t[1])] = "plains"
		for s in c.sand:
			var t := Vector2i(s[0], s[1])
			var d := absf(Sand.surface_z(tiles, t, s[2], s[3], turn if tiles[t] == "sandstonesphinx" else 0) - s[4])
			worst.sand = maxf(worst.sand, d)
			_diff("sand", d < 0.001, [n, s])
		var pt := Vector2i(c.props_tile[0], c.props_tile[1])
		var props := Sand.props(tiles, pt, dist.get(pt))
		_diff("prop count", props.size() == c.props.size(), [n, props.size(), c.props.size()])
		for k in mini(props.size(), c.props.size()):
			var a: Array = props[k]
			var b: Array = c.props[k]
			_diff("prop", a[0] == b[0] and Vector2(a[1], a[2]).distance_to(Vector2(b[1], b[2])) < 0.001, [n, a, b])
	var fns := {sphinx = Sand.sphinx_routes, stronghold = DesertLands.stronghold_routes, bazaar = DesertLands.bazaar_routes}
	for name: String in fns:
		for t in 6:
			var mine: Dictionary = fns[name].call(t)
			var theirs: Dictionary = data.routes[name][str(t)]
			for key in theirs:
				var a = mine[int(key)]
				var b: Array = theirs[key]
				_diff(name + " route length", a.size() == b.size(), [t, key])
				for k in mini(a.size(), b.size()):
					_diff(name + " route", Vector2(a[k].x, a[k].y).distance_to(Vector2(b[k][0], b[k][1])) < 0.001, [t, key, k])
	print("CANYON MESAS: %d of %d the same outline; values off by over 0.01 bands: %d of %d; farthest corner from the other outline %.3f m, area differs by up to %.1f%%" % [mesas_same, mesas_seen, values_off, values_seen, mesa_stray, mesa_area * 100.0])
	print("CANYON COMPARE: %d cases, %d differ; worst value %.4f bands, lane width %.3f m (%.3f m in the first section), sand %.5f m" % [data.cases.size(), bad, worst.value, worst.width, worst.mouth, worst.sand])
	quit()
