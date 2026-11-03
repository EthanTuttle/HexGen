extends SceneTree
## Compares scripts/gorge.gd and the rapids parts of water.gd with art/scripts/gorge.py on the cases from tools/gorge_cases.py:
##   godot --headless --path godot --script res://tools/gorge_check.gd -- <cases.json>

const CLOSE := 0.003
var bad := 0
var checked := 0
var kinds := {}


func _init() -> void:
	var cases: Array = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	var t0 := Time.get_ticks_usec()
	var slowest := 0
	var most := 0
	for c in cases:
		var t1 := Time.get_ticks_usec()
		var n := _case(c)
		slowest = maxi(slowest, Time.get_ticks_usec() - t1)
		most = maxi(most, n)
	print("GORGE CHECK: %d values, %d differ, %d cases; %.1f ms a tile on average, %.1f ms at worst, most triangles %d; %s" % [checked, bad, cases.size(), (Time.get_ticks_usec() - t0) / 1000.0 / cases.size(), slowest / 1000.0, most, kinds])
	quit()


func _say(what: String, c: Dictionary) -> void:
	bad += 1
	var kind := what.split(" ")[0]
	kinds[kind] = kinds.get(kind, 0) + 1
	if kinds[kind] < 6:
		print("DIFF %s: %s %s %s" % [what, c.mask, c.seed, c.widths])


func _num(a: float, b: float, what: String, c: Dictionary) -> void:
	checked += 1
	if absf(a - b) > CLOSE and absf(absf(a - b) - TAU) > CLOSE:
		_say("%s %f %f" % [what, a, b], c)


func _line(a: Array, b, what: String, c: Dictionary) -> void:
	if a.size() != b.size():
		_say("%s size %d %d" % [what, a.size(), b.size()], c)
		return
	for k in a.size():
		_num(a[k][0], b[k].x, what, c)
		_num(a[k][1], b[k].y, what, c)
		if a[k].size() > 2:
			_num(a[k][2], b[k].z, what, c)


func _case(c: Dictionary) -> int:
	var mask: Array = c.mask
	var widths: Array = c.widths
	var seed: String = c.seed
	var near: Array = c.near
	var w2 := Water.with_falls(Water.edge_widths("rapids", near), mask, int(c.q), int(c.r))
	for i in 6:
		_num(w2[i], widths[i], "widths", c)
	var w := Water.tile_water(mask, seed, widths, "rapids")
	if w.kind != c.kind or w.outlines.size() != c.outlines.size():
		_say("kind %s %s" % [w.kind, c.kind], c)
		return 0
	for k in w.outlines.size():
		_line(c.outlines[k], w.outlines[k], "outline", c)
	var r := Water.water_routes(mask, seed, widths, "rapids")
	_num(c.hub[0], r.hub.x, "hub", c)
	_num(c.hub[1], r.hub.y, "hub", c)
	if r.lines.size() != c.lines.size():
		_say("lines", c)
	for e in r.lines:
		if c.lines.has(str(e)):
			_line(c.lines[str(e)], r.lines[e], "line", c)
	var g := Gorge.build(mask, seed, widths, c.landmark)
	if g.cut.size() != c.cut.size():
		_say("cut count", c)
		return 0
	for k in g.cut.size():
		_line(c.cut[k], g.cut[k], "cut", c)
	# Which triangles an ear clip leaves on points a hair apart can differ: same areas, nearly the same count.
	checked += 1
	if absi(g.tris.size() - int(c.tris)) > 3:
		_say("tris %d %d" % [g.tris.size(), c.tris], c)
	var area := {}
	for t in g.tris:
		var m0: String = "plains" if t[3] == "ground" else t[3]
		area[m0] = area.get(m0, 0.0) + absf((t[1].x - t[0].x) * (t[2].y - t[0].y) - (t[1].y - t[0].y) * (t[2].x - t[0].x)) / 2.0
	for m in c.area:
		checked += 1
		if absf(area.get(m, 0.0) - c.area[m]) > 0.01:
			_say("area %s %f %f" % [m, area.get(m, 0.0), c.area[m]], c)
	if g.walks.size() != c.walks.size():
		_say("walks %s %s" % [g.walks.keys(), c.walks.keys()], c)
	else:
		for e in g.walks:
			_line(c.walks[str(e)], g.walks[e], "walk %d" % e, c)
	if (c.spot == null) != g.spot.is_empty():
		_say("spot", c)
	elif c.spot != null:
		_num(c.spot.middle[0], g.spot.middle.x, "spot", c)
		_num(c.spot.middle[1], g.spot.middle.y, "spot", c)
		_num(c.spot.angle, g.spot.angle, "spot angle", c)
		if c.spot.routes.size() != g.spot.routes.size():
			_say("spot routes", c)
		else:
			for e in g.spot.routes:
				_line(c.spot.routes[str(e)], g.spot.routes[e], "spot route", c)
	if g.falls.size() != c.falls.size():
		_say("falls", c)
	else:
		for k in g.falls.size():
			var f: Array = c.falls[k]
			_num(f[0][0], g.falls[k].top.x, "fall", c)
			_num(f[1][1], g.falls[k].foot.y, "fall", c)
			_num(f[2], g.falls[k].top_half, "fall", c)
			_num(f[3], g.falls[k].half, "fall", c)
	var marks := Water.rapids_marks(mask, seed, widths, int(c.band))
	_num(c.foam, marks.foam.size(), "foam", c)
	_num(c.boulders, marks.boulders.size(), "boulders", c)
	var rapids := near.map(func(x): return x == "rapids")
	var flow := Water.flow_in(int(c.q), int(c.r), mask, rapids, c.flow_own)
	for i in 6:
		checked += 1
		if flow[i] != c.flow[i]:
			_say("flow", c)
	checked += 1
	if Water.landmark_fits("trollbridge", mask, seed, widths) != c.fits:
		_say("fits", c)
	for z in c.z:
		_num(z[2], Gorge.water_z(mask, widths, Vector2(z[0], z[1])), "water_z", c)
	return g.tris.size() + g.water.size()
