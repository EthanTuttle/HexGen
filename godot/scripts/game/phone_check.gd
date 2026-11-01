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
	await RenderingServer.frame_post_draw
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
	_say("FOREST PERF DONE")


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
	await RenderingServer.frame_post_draw
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
