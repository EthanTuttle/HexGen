extends SceneTree
## Compares SwampLands with the art's swamp_lands.py on the cases tools/swamp_cases.py writes, and times it.
##   godot --headless --path . --script res://tools/swamp_check.gd -- /tmp/swamp_cases.json

var bad := {}
var shown := 0


func _fail(kind: String, what: String) -> void:
	bad[kind] = bad.get(kind, 0) + 1
	if shown < 12:
		shown += 1
		print("  ", kind, ": ", what)


func _same_line(a: PackedVector2Array, b: Array, tol := 0.002) -> bool:
	if a.size() != b.size():
		return false
	for k in a.size():
		if a[k].distance_to(Vector2(b[k][0], b[k][1])) > tol:
			return false
	return true


func _area(tris: Array) -> float:
	var s := 0.0
	for t: Array in tris:
		s += absf((t[1] - t[0]).cross(t[2] - t[0])) / 2.0
	return s


func _initialize() -> void:
	var path: String = OS.get_cmdline_user_args()[0]
	var cases: Array = JSON.parse_string(FileAccess.get_file_as_string(path))
	var worst := 0
	var total := 0
	var built := []
	for c: Dictionary in cases:
		var terrains := {}
		for e: Array in c.terrains:
			terrains[Vector2i(int(e[0]), int(e[1]))] = e[2]
		var edges := []
		for e in c.edges:
			edges.append(int(e))
		var t0 := Time.get_ticks_usec()
		var tile := SwampLands.marsh_tile(terrains, int(c.q), int(c.r), edges, null if c.out == null else int(c.out), int(c.turn), int(c.near))
		var us := Time.get_ticks_usec() - t0
		total += us
		worst = maxi(worst, us)
		built.append(us)
		var at := "%s (%d, %d)" % [tile.name, c.q, c.r]
		if tile.water.size() != int(c.water):
			_fail("water tris", "%s %d against %d" % [at, tile.water.size(), c.water])
		if tile.bank.size() != int(c.bank):
			_fail("bank tris", "%s %d against %d" % [at, tile.bank.size(), c.bank])
		if absf(_area(tile.water) - c.water_area) > 0.002:
			_fail("water area", "%s %.4f against %.4f" % [at, _area(tile.water), c.water_area])
		if absf(_area(tile.bank) - c.bank_area) > 0.002:
			_fail("bank area", "%s %.4f against %.4f" % [at, _area(tile.bank), c.bank_area])
		if tile.trails.size() != c.trails.size():
			_fail("trails", "%s %d against %d" % [at, tile.trails.size(), c.trails.size()])
		else:
			for k in tile.trails.size():
				if not _same_line(tile.trails[k][0], c.trails[k][0]) or not _same_line(tile.trails[k][1], c.trails[k][1]):
					_fail("trail line", "%s trail %d" % [at, k])
		if tile.spurs.size() != c.spurs.size():
			_fail("spurs", at)
		else:
			for k in tile.spurs.size():
				if not _same_line(tile.spurs[k], c.spurs[k]):
					_fail("spur line", at)
		if tile.props.size() != c.props.size():
			_fail("prop count", "%s %d against %d" % [at, tile.props.size(), c.props.size()])
		else:
			for k in tile.props.size():
				var a: Array = tile.props[k]
				var b: Array = c.props[k]
				if a[0] != b[0] or absf(a[1] - b[1]) > 0.001 or absf(a[2] - b[2]) > 0.001 or absf(a[3] - b[3]) > 0.001:
					_fail("prop", "%s #%d %s against %s" % [at, k, a, b])
					break
		if tile.ooze.size() != c.ooze.size():
			_fail("ooze", at)
		if tile.flecks.size() != int(c.flecks):
			_fail("flecks", at)
		if tile.effects.size() != c.effects.size():
			_fail("effects", at)
		if (tile.finish == null) != (c.finish == null):
			_fail("finish", at)
		if SwampLands.tile_tris(tile) != int(c.tris):
			_fail("tile tris", "%s %d against %d" % [at, SwampLands.tile_tris(tile), c.tris])
		if c.routes != null:
			var r := SwampLands.landmark_routes(tile.name, int(c.turn))
			for e in c.routes:
				var line: Array = r[int(e)]
				var want: Array = c.routes[e]
				if line.size() != want.size():
					_fail("route size", "%s edge %s" % [at, e])
				else:
					for k in line.size():
						if (line[k] as Vector3).distance_to(Vector3(want[k][0], want[k][1], want[k][2])) > 0.002:
							_fail("route", "%s edge %s point %d" % [at, e, k])
							break
		if not tile.trails.is_empty() and SwampLands.planks(tile.trails[0][1], 0.52, 3).size() != int(c.planks):
			_fail("planks", at)
	built.sort()
	print("SWAMP COMPARE %d tiles: %s" % [cases.size(), bad if not bad.is_empty() else "all match"])
	print("SWAMP marsh_tile: %.1f ms average, %.1f median, %.1f slowest" % [total / 1000.0 / cases.size(), built[built.size() / 2] / 1000.0, worst / 1000.0])
	quit()
