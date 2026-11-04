class_name PhoneCheck
extends Node
## A check on a real phone (README -> iOS): when launched with HEXGEN_PHONECHECK=1 in the environment (devicectl:
## DEVICECTL_CHILD_HEXGEN_PHONECHECK=1) or `--phonecheck`, it writes the renderer, the screen and safe area and the
## frame rate to user://phonecheck/report.txt and saves screenshots there every few seconds (the app's own Documents
## folder, which `xcrun devicectl device copy from` can read), and logs touches (each finger down, the most
## fingers at once). The game plays normally meanwhile. A test aid only.
## With HEXGEN_FORESTPERF=1 too (devicectl: DEVICECTL_CHILD_HEXGEN_FORESTPERF=1), it spawns the four forest regions
## (Game.spawn_forest_regions) and measures them instead: frame rate, worst frame, draw calls and triangles, and the
## CPU and GPU time of a frame, at the opening zoom and zoomed all the way out, by day and at night, plus the worst
## frame across nightfall. Lines start "FOREST PERF"; shots are forest_*.png.

const SHOTS := [4.0, 10.0, 20.0, 35.0, 60.0]   # seconds after launch; then every 15 s for 5 minutes
var _t := 0.0
var _next := 0
var _frames := 0
var _lines := PackedStringArray()
var _dir := "user://phonecheck"
var _down := {}         # finger index -> held
var _touches := 0
var _most := 0
var _drags := 0
var _forest := false    # measuring the forest: no timed shots (saving one stalls a frame)


static func wanted() -> bool:
	return OS.get_environment("HEXGEN_PHONECHECK") == "1" or "--phonecheck" in OS.get_cmdline_args() \
			or "--phonecheck" in OS.get_cmdline_user_args()


func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(_dir)
	_say("model %s, %s %s" % [OS.get_model_name(), OS.get_name(), OS.get_version()])
	_say("renderer %s (%s), driver %s, adapter %s / %s" % [
		ProjectSettings.get_setting("rendering/renderer/rendering_method"),
		RenderingServer.get_current_rendering_method(), RenderingServer.get_current_rendering_driver_name(),
		RenderingServer.get_video_adapter_name(), RenderingServer.get_video_adapter_vendor()])
	_screen()
	if OS.get_environment("HEXGEN_FORESTPERF") == "1" or "--forestperf" in OS.get_cmdline_user_args():
		_forest = true
		_forest_perf.call_deferred()


func _process(delta: float) -> void:
	_t += delta
	_frames += 1
	var due: float = SHOTS[_next] if _next < SHOTS.size() else 60.0 + 15.0 * (_next - SHOTS.size() + 1)
	if due <= 300.0 and _t >= due and not _forest:
		_next += 1
		_shot.call_deferred("t%03d" % int(_t))


func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		var e := event as InputEventScreenTouch
		if e.pressed:
			_down[e.index] = true
			_touches += 1
			_most = maxi(_most, _down.size())
			_say("%.1f s: finger %d down at %s (%d down)" % [_t, e.index, e.position.round(), _down.size()])
		else:
			_down.erase(e.index)
	elif event is InputEventScreenDrag:
		_drags += 1


func _shot(tag: String) -> void:
	await StallWatch.drawn(get_tree())
	get_viewport().get_texture().get_image().save_png(_dir.path_join(tag + ".png"))
	_say("%s: shot, %.1f fps on average so far, %d fps now; touches %d, most fingers at once %d, drag events %d"
			% [tag, _frames / _t, Engine.get_frames_per_second(), _touches, _most, _drags])


func _forest_perf() -> void:
	var game := get_parent() as Game
	var vp := get_viewport().get_viewport_rid()
	RenderingServer.viewport_set_measure_render_time(vp, true)
	await get_tree().create_timer(3.0).timeout
	game.spawn_forest_regions()
	var hw: Vector2i = Game.DEBUG_FOREST.heartwood
	var views := {"opening": [Hex.to3(Hex.tile_position(hw.x, hw.y)), 58.0],
		"zoomed_out": [Hex.to3(Vector2.ZERO), Rules.DAY_MAX_ZOOM]}
	for time in ["day", "night"]:
		if time == "night":
			# Across nightfall: the clock runs on through it while the camera stays zoomed in (the night zoom limit
			# would pull a zoomed-out camera in anyway).
			game.rig.frame(views.opening[0], views.opening[1], 50.0)
			game.minute = Rules.NIGHT_AT - 0.15
			var worst := await _measure(vp, 14.0)
			_say("FOREST PERF across nightfall (opening zoom, clock running): worst frame %.1f ms, %.1f fps" % [
				worst.worst, worst.fps])
		for v in views:
			game.rig.frame(views[v][0], views[v][1], 50.0)
			# Measure the same view at night: the game would limit it to 60 m, so its process (the clock, the zoom
			# limit) pauses for this one.
			game.set_process(not (time == "night" and v == "zoomed_out"))
			game.rig.max_distance = Rules.DAY_MAX_ZOOM
			game.rig.distance = views[v][1]
			await get_tree().create_timer(3.0).timeout
			var m := await _measure(vp, 6.0)
			_say("FOREST PERF %s %s: %.1f fps, worst frame %.1f ms, draw calls %d, triangles %d, objects %d, CPU %.2f ms, GPU %.2f ms" % [
				time, v, m.fps, m.worst, m.calls, m.tris, m.objects, m.cpu, m.gpu])
			await _shot_as("forest_%s_%s" % [time, v])
			# Two more shots 1.5 s apart, to see whether the shadows hold still.
			if v == "opening":
				await get_tree().create_timer(1.5).timeout
				await _shot_as("forest_%s_%s_b" % [time, v])
	game.set_process(true)
	game.minute = 10.0   # by day, for the walk
	await _walk_to_mill(game, vp)
	await _hills_perf(game, vp)
	await _town_perf(game, vp)
	await _river_perf(game, vp)
	_say("FOREST PERF DONE")


## The hills: a view over the raised regions, a ledge climb, and a real rise, with the frame cost of each.
func _hills_perf(game: Game, vp: RID) -> void:
	var map := game.map
	game.set_process(true)
	var snowy := {}
	for g in game.regions:
		if g.variant == "snowy_peaks":
			snowy = g
	var lm: Vector2i = snowy.landmark_tile
	game.rig.frame(Hex.to3(Hex.tile_position(lm.x, lm.y), 6.0), 58.0, 50.0)
	await get_tree().create_timer(2.0).timeout
	var m := await _measure(vp, 5.0)
	_say("HILLS PERF over the snowy region at the opening zoom: %.1f fps, worst frame %.1f ms, draw calls %d, triangles %d, CPU %.2f ms, GPU %.2f ms" % [m.fps, m.worst, m.calls, m.tris, m.cpu, m.gpu])
	await _shot_as("hills_opening")
	game.rig.frame(Hex.to3(Hex.tile_position(lm.x, lm.y), 6.0), Rules.DAY_MAX_ZOOM, 50.0)
	await get_tree().create_timer(2.0).timeout
	m = await _measure(vp, 5.0)
	_say("HILLS PERF zoomed all the way out over the raised regions: %.1f fps, worst frame %.1f ms, draw calls %d, triangles %d, CPU %.2f ms, GPU %.2f ms" % [m.fps, m.worst, m.calls, m.tris, m.cpu, m.gpu])
	await _shot_as("hills_zoomed_out")
	# A ledge climb, from the foot of one of its ledges to the landmark.
	var climb: Array = map.climbs.filter(func(c): return c[0] in snowy.tiles)[0]
	var foot := Cliffs.beside(climb[0], climb[1] - 1)
	game.party_tile = foot
	game.party_node.place_at(foot)
	map.party_moved(foot)
	game.rig.frame(game.party_node.centre(), 30.0, 50.0)
	await get_tree().create_timer(0.5).timeout
	var t0 := Time.get_ticks_usec()
	var route := game.path_to(lm)
	game.party_node.route_preview(route)
	_say("HILLS PERF working out the route up: %.1f ms" % ((Time.get_ticks_usec() - t0) / 1000.0))
	game.walk_to(lm)
	m = await _measure(vp, 4.0)
	_say("HILLS PERF climbing a ledge: %.1f fps, worst frame %.1f ms, draw calls %d" % [m.fps, m.worst, m.calls])
	await _shot_as("hills_climbing")
	while game.busy:
		await get_tree().process_frame
	# A real rise, with the party on it: seven tiles on spare land.
	var c := Vector2i(16, 10)
	var tiles: Array[Vector2i] = [c]
	for n in Hex.NEIGHBOURS:
		tiles.append(c + n)
	var land := {}
	game._debug_road(c + Vector2i(-2, 0), land)
	for t in tiles:
		land[t] = "hills"
		game.order[t] = game.order.size()
	map.retile(land)
	game.party_tile = c
	game.party_node.place_at(c)
	map.party_moved(c)
	game.rig.frame(Hex.to3(Hex.tile_position(c.x, c.y), 2.0), 40.0, 50.0)
	await get_tree().create_timer(1.0).timeout
	var region := game.new_region("hills", tiles, "volcanic_peaks", tiles[1])
	t0 = Time.get_ticks_usec()
	game._transform(tiles, region, c)
	var frames := 0
	var worst := 0.0
	var last := Time.get_ticks_usec()
	var shot := false
	while game.busy:
		await get_tree().process_frame
		var now := Time.get_ticks_usec()
		worst = maxf(worst, (now - last) / 1000.0)
		last = now
		frames += 1
		if not shot and map.lift.get(c, 0.0) > 2.5:
			shot = true
			await _shot_as("hills_rising")
	_say("HILLS PERF the rise, with the tiles' change before it: %.1f fps, worst frame %.1f ms over %.1f s" % [frames / ((last - t0) / 1e6), worst, (last - t0) / 1e6])
	await _shot_as("hills_risen")


## The towns, the busiest common tiles: each 12-tile town at the opening zoom.
func _town_perf(game: Game, vp: RID) -> void:
	for v: String in Game.DEBUG_TOWNS:
		var c: Vector2i = Game.DEBUG_TOWNS[v]
		game.rig.frame(Hex.to3(Hex.tile_position(c.x, c.y)), 58.0, 50.0)
		await get_tree().create_timer(2.0).timeout
		var m := await _measure(vp, 5.0)
		_say("TOWN PERF %s at the opening zoom: %.1f fps, worst frame %.1f ms, draw calls %d, triangles %d, CPU %.2f ms, GPU %.2f ms" % [v, m.fps, m.worst, m.calls, m.tris, m.cpu, m.gpu])
		await _shot_as("town_%s" % v)


func _river_perf(game: Game, vp: RID) -> void:
	for v: String in Game.DEBUG_RIVERS:
		var c: Vector2i = Game.DEBUG_RIVERS[v]
		game.rig.frame(Hex.to3(Hex.tile_position(c.x, c.y)), 58.0, 50.0)
		await get_tree().create_timer(2.0).timeout
		var m := await _measure(vp, 5.0)
		_say("RIVER PERF %s at the opening zoom: %.1f fps, worst frame %.1f ms, draw calls %d, triangles %d, CPU %.2f ms, GPU %.2f ms" % [v, m.fps, m.worst, m.calls, m.tris, m.cpu, m.gpu])
		await _shot_as("river_%s" % v)


## Walks the party to the Great Windmill, measuring the walk, and logs how it stops on the narrow path.
func _walk_to_mill(game: Game, vp: RID) -> void:
	var lm: Vector2i = Vector2i.ZERO
	for g in game.regions:
		if g.variant == "windmill_country":
			lm = g.landmark_tile
	game.rig.frame(game.party_node.centre(), 58.0, 50.0)
	game.walk_to(lm)
	var m := await _measure(vp, 6.0)
	_say("FOREST PERF walking at the opening zoom: %.1f fps, worst frame %.1f ms, draw calls %d" % [m.fps, m.worst, m.calls])
	while game.busy:
		await get_tree().process_frame
	await get_tree().create_timer(Rules.SETTLE_SECONDS + 0.5).timeout
	var graph := game.map.path_graph(lm)
	var ms := game.party_node.members
	var worst := 0.0
	var closest := INF
	for k in ms.size():
		var a := Vector2(ms[k].node.position.x, -ms[k].node.position.z)
		var g2 := game.map.path_graph(GroundCover.tile_at(a))
		worst = maxf(worst, g2.distance_to_paths(a) if not g2.nodes.is_empty() else 0.0)
		for j in k:
			closest = minf(closest, a.distance_to(Vector2(ms[j].node.position.x, -ms[j].node.position.z)))
	_say("FOREST PERF party at the Great Windmill %s: centres at most %.2f m off the path, %.2f m apart, on the path graph: %s" % [
		lm, worst, closest, not graph.nodes.is_empty()])
	var e := game.map.entrance_angle(lm)
	game.rig.frame(game.party_node.centre(), 18.0, 40.0, -90.0 - rad_to_deg(e))
	await get_tree().create_timer(0.6).timeout
	await _shot_as("forest_party_line")


## Frames over `seconds`: average fps, the worst frame, and the render cost of the last frame.
func _measure(vp: RID, seconds: float) -> Dictionary:
	var t0 := Time.get_ticks_usec()
	var last := t0
	var worst := 0.0
	var frames := 0
	var cpu := 0.0
	var gpu := 0.0
	while Time.get_ticks_usec() - t0 < seconds * 1e6:
		await get_tree().process_frame
		var now := Time.get_ticks_usec()
		worst = maxf(worst, (now - last) / 1000.0)
		last = now
		frames += 1
		cpu += RenderingServer.viewport_get_measured_render_time_cpu(vp)
		gpu += RenderingServer.viewport_get_measured_render_time_gpu(vp)
	var rs := RenderingServer
	return {fps = frames / ((last - t0) / 1e6), worst = worst, cpu = cpu / frames, gpu = gpu / frames,
		calls = rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
		tris = rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME),
		objects = rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME)}


func _shot_as(tag: String) -> void:
	await StallWatch.drawn(get_tree())
	get_viewport().get_texture().get_image().save_png(_dir.path_join(tag + ".png"))


func _screen() -> void:
	_say("  screen %s, scale %.2f, window %s, safe area %s, orientation %d" % [DisplayServer.screen_get_size(),
		DisplayServer.screen_get_scale(), DisplayServer.window_get_size(), DisplayServer.get_display_safe_area(),
		DisplayServer.screen_get_orientation()])


func _say(line: String) -> void:
	print("PHONECHECK ", line)
	_lines.append(line)
	var f := FileAccess.open(_dir.path_join("report.txt"), FileAccess.WRITE)
	if f:
		f.store_string("\n".join(_lines) + "\n")
