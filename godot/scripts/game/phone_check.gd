class_name PhoneCheck
extends Node
## A check on a real phone (README -> iOS): when launched with HEXGEN_PHONECHECK=1 in the environment (devicectl:
## DEVICECTL_CHILD_HEXGEN_PHONECHECK=1) or `--phonecheck`, it writes the renderer, the screen and safe area and the
## frame rate to user://phonecheck/report.txt and saves screenshots there every few seconds (the app's own Documents
## folder, which `xcrun devicectl device copy from` can read), and logs touches (each finger down, the most
## fingers at once). The game plays normally meanwhile. A test aid only.

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


func _process(delta: float) -> void:
	_t += delta
	_frames += 1
	var due: float = SHOTS[_next] if _next < SHOTS.size() else 60.0 + 15.0 * (_next - SHOTS.size() + 1)
	if due <= 300.0 and _t >= due:
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
