extends SceneTree
## Compares FeyLands with the art's fey_lands.py on the cases tools/fey_cases.py writes.
##   godot --headless --path . --script res://tools/fey_check.gd -- /tmp/fey_cases.json

var bad := {}
var shown := 0


func _fail(kind: String, what: String) -> void:
	bad[kind] = bad.get(kind, 0) + 1
	if shown < 14:
		shown += 1
		print(kind, ": ", what)


func _initialize() -> void:
	var cases: Array = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	var tiles_seen := 0
	var worst := 0
	var spent := 0
	for c: Dictionary in cases:
		var terrains := {}
		for row: Array in c.tiles:
			terrains[Vector2i(int(row[0]), int(row[1]))] = row[2]
		var toward := {}
		for row: Array in c.toward:
			toward[Vector2i(int(row[0]), int(row[1]))] = Vector2i(int(row[2]), int(row[3]))
		var t0 := Time.get_ticks_usec()
		var region := FeyLands.Region.new(terrains, toward, {Vector2i(int(c.gate[0]), int(c.gate[1])): int(c.turn)})
		if region.placed_trees != int(c.trees):
			_fail("trees", "%d here, %d in the art" % [region.placed_trees, c.trees])
		if region.number != int(c.things):
			_fail("things", "%d here, %d in the art" % [region.number, c.things])
		if region.items.size() != int(c.items):
			_fail("items", "%d here, %d in the art" % [region.items.size(), c.items])
		for row: Dictionary in c.tile:
			var t := Vector2i(int(row.t[0]), int(row.t[1]))
			var tile := FeyLands.fey_tile(region, t)
			tiles_seen += 1
			worst = maxi(worst, FeyLands.face_tris(tile.ground) + FeyLands.face_tris(tile.trail) + FeyLands.face_tris(tile.stand))
			if tile.season != row.season:
				_fail("season", "%s %s here, %s in the art" % [t, tile.season, row.season])
			for key: String in ["ground", "trail", "stand"]:
				if tile[key].size() != int(row[key]):
					_fail(key, "%s %d here, %d in the art" % [t, tile[key].size(), row[key]])
			var area := 0.0
			var colours := {}
			for f: Array in tile.stand:
				var u: Vector3 = f[1][1] - f[1][0]
				var v: Vector3 = f[1][2] - f[1][0]
				area += absf(u.x * v.y - u.y * v.x)
				colours[f[0]] = colours.get(f[0], 0) + 1
			if absf(area - row.area) > 0.05:
				_fail("area", "%s %.3f here, %.3f in the art" % [t, area, row.area])
			for k: String in row.colours:
				if absi(int(colours.get(k, 0)) - int(row.colours[k])) > 2:   # a face or two: Vector3 is 32-bit, and a face's colour hashes its middle
					_fail("colour", "%s %s: %d here, %d in the art" % [t, k, colours.get(k, 0), row.colours[k]])
			if Array(region.edges[t]) != Array(row.edges).map(func(e): return int(e)):
				_fail("edges", "%s %s here, %s in the art" % [t, region.edges[t], row.edges])
			if tile.trails.size() != row.trails.size():
				_fail("trails", "%s %d here, %d in the art" % [t, tile.trails.size(), row.trails.size()])
			else:
				for k in tile.trails.size():
					var line: PackedVector2Array = tile.trails[k][0]
					var want: Array = row.trails[k]
					if line.size() != want.size():
						_fail("trail points", "%s %d here, %d in the art" % [t, line.size(), want.size()])
					elif line[line.size() / 2].distance_to(Vector2(want[want.size() / 2][0], want[want.size() / 2][1])) > 0.01:
						_fail("trail line", "%s" % t)
		spent += Time.get_ticks_usec() - t0
	print("FEY COMPARE %d tiles, worst %d triangles, %.0f ms a region (GDScript, main thread); differences: %s" % [tiles_seen, worst, spent / 1000.0 / cases.size(), bad])
	quit(0 if bad.is_empty() else 1)
