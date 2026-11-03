extends SceneTree
## Compares scripts/water.gd with art/scripts/water.py on the cases from tools/water_cases.py:
##   godot --headless --path godot --script res://tools/water_check.gd -- <cases.json>

const CLOSE := 0.002
var bad := 0
var checked := 0


func _init() -> void:
	var cases: Array = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	for c in cases:
		_case(c)
	print("WATER CHECK: %d values, %d differ, %d cases" % [checked, bad, cases.size()])
	quit()


func _say(what: String, c: Dictionary) -> void:
	bad += 1
	if bad < 30:
		print("DIFF %s: %s %s %s" % [what, c.mask, c.seed, c.style])


func _num(a: float, b: float, what: String, c: Dictionary) -> void:
	checked += 1
	if absf(a - b) > CLOSE and absf(absf(a - b) - TAU) > CLOSE:   # an angle of pi can come out as -pi
		_say("%s %f %f" % [what, a, b], c)


## Points on the clipping line can fall either side of it in 32-bit floats: one or two points, a hair apart.
func _squeeze(pts: Array) -> Array:
	var out := []
	for p in pts:
		var q := Vector2(p[0], p[1]) if p is Array else p as Vector2
		if out.is_empty() or out[-1].distance_to(q) > CLOSE:
			out.append(q)
	return out


func _pts(a0: Array, b0, what: String, c: Dictionary) -> void:
	var a := _squeeze(a0)
	var b := _squeeze(Array(b0))
	if a.size() != b.size():
		_say("%s size %d %d" % [what, a.size(), b.size()], c)
		return
	for k in a.size():
		_num(a[k].x, b[k].x, what, c)
		_num(a[k].y, b[k].y, what, c)


func _many(a: Array, b: Array, what: String, c: Dictionary) -> void:
	if a.size() != b.size():
		_say("%s count %d %d" % [what, a.size(), b.size()], c)
		return
	for k in a.size():
		if what.begins_with("port"):
			_same_points(_squeeze(a[k]), _squeeze(Array(b[k])), what, c)
		else:
			_pts(a[k], b[k], what, c)


## The port's clipped shapes can start at a different point of the same outline, for the same reason.
func _same_points(a: Array, b: Array, what: String, c: Dictionary) -> void:
	for pair in [[a, b], [b, a]]:
		for p: Vector2 in pair[0]:
			checked += 1
			if not pair[1].any(func(q): return q.distance_to(p) < CLOSE * 3.0):
				_say("%s %s" % [what, p], c)


func _lines(a: Dictionary, b: Dictionary, what: String, c: Dictionary) -> void:
	if a.size() != b.size():
		_say("%s keys" % what, c)
		return
	for k in b:
		if not a.has(str(k)):
			_say("%s key %s" % [what, k], c)
		else:
			_pts(a[str(k)], b[k], what, c)


## Rows of numbers: a Python row [x, y, rest...], a Godot row [Vector2, rest...].
func _rows(a: Array, b: Array, what: String, c: Dictionary) -> void:
	if a.size() != b.size():
		_say("%s count %d %d" % [what, a.size(), b.size()], c)
		return
	for k in a.size():
		_num(a[k][0], b[k][0].x, what, c)
		_num(a[k][1], b[k][0].y, what, c)
		for j in range(2, a[k].size()):
			if a[k][j] is String:
				if a[k][j] != b[k][j - 1]:
					_say(what, c)
			else:
				_num(a[k][j], b[k][j - 1], what, c)


func _case(c: Dictionary) -> void:
	var mask: Array = c.mask
	var seed: String = c.seed
	var widths: Array = c.widths
	var style: String = c.style
	var near := int(c.near)
	var w := Water.tile_water(mask, seed, widths, style)
	_many(c.outlines, w.outlines, "outlines", c)
	_many(c.shores, w.shores, "shores", c)
	if c.kind != w.kind:
		_say("kind", c)
	var r := Water.water_routes(mask, seed, widths, style)
	_pts([c.hub], [r.hub], "hub", c)
	_lines(c.lines, r.lines, "lines", c)
	var lands := Water.landings(mask, seed, widths, style)
	_lines(c.lands, lands, "lands", c)
	var props := Water.tile_props(mask, seed, widths, style, near, c.landmark)
	if props.size() != c.props.size():
		_say("props %d %d" % [c.props.size(), props.size()], c)
	else:
		for k in props.size():
			if props[k][0] != c.props[k][0]:
				_say("prop name", c)
			_num(c.props[k][1], props[k][1].x, "prop", c)
			_num(c.props[k][2], props[k][1].y, "prop", c)
			_num(angle_difference(c.props[k][3], props[k][2]), 0.0, "prop angle", c)
	_rows(c.waves, Water.lake_waves(w.outlines, w.shores, seed), "waves", c)
	_rows(c.lilies, Water.still_lilies(w.outlines, w.shores, seed, near), "lilies", c)
	var names := ["riverport", "meditationrock", "trollbridge", "serpentlair"]
	for k in 4:
		if c.fits[k] != Water.landmark_fits(names[k], mask, seed, widths):
			_say("fits %s" % names[k], c)
	var d := Water.delta_dressing(w.outlines, w.shores, w.kind, seed, near)
	_many(c.delta.islands, d.islands, "islands", c)
	_rows(c.delta.boats, d.boats, "boats", c)
	_rows(c.delta.jetties, d.jetties, "jetties", c)
	if style == "rapids":
		var m := Water.rapids_marks(mask, seed, widths, near)
		_rows(c.foam, m.foam, "foam", c)
		_rows(c.boulders, m.boulders, "boulders", c)
		for pair in [["bridge", Water.BRIDGE_HALF], ["troll", Water.TROLL_HALF]]:
			var s := Water.bridge_spot(mask, seed, widths, pair[1])
			var want = c[pair[0]]
			if (want == null) != s.is_empty():
				_say("%s fits" % pair[0], c)
			elif want != null:
				_pts([want.middle], [s.middle], "bridge", c)
				_num(angle_difference(want.angle, s.angle), 0.0, "bridge angle", c)
				_lines(want.routes, s.routes, "bridge routes", c)
	if style == "still_waters":
		var s := Water.rock_routes(mask, seed, widths)
		_lines(c.rock.land, s.land, "rock land", c)
		_lines(c.rock.floats, s.floats, "rock floats", c)
		_rows(c.rock.stones, s.stones, "stones", c)
		if int(c.rock.turn) != s.turn:
			_say("rock turn", c)
	if style == "delta":
		var t := Water.port_turn(mask, seed)
		if int(c.port.turn) != t:
			_say("port turn", c)
		var sh := Water.port_shape(mask, seed, widths, t)
		_many(c.port.outlines, sh.outlines, "port outlines", c)
		_many(c.port.quads, sh.quads, "port quads", c)
		_many(c.port.walls, Water.port_walls(mask, seed, widths, t), "port walls", c)
		var pr := Water.port_routes(mask, t)
		_lines(c.port.land, pr.land, "port land", c)
		_lines(c.port.floats, pr.floats, "port floats", c)
	if style == "great_lake":
		_lines(c.lair, Water.lair_routes(near), "lair", c)
