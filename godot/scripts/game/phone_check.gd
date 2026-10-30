class_name PhoneCheck
extends Node
## A check on a real phone (README -> iOS): when launched with HEXGEN_PHONECHECK=1 in the environment (devicectl:
## DEVICECTL_CHILD_HEXGEN_PHONECHECK=1) or `--phonecheck`, it writes the renderer, the screen and safe area and the
## frame rate to user://phonecheck/report.txt and saves screenshots there every few seconds (the app's own Documents
## folder, which `xcrun devicectl device copy from` can read). The game plays normally meanwhile. A test aid only.

const SHOTS := [4.0, 10.0, 20.0, 35.0, 60.0]   # seconds after launch
var _t := 0.0
var _next := 0
var _frames := 0
var _lines := PackedStringArray()
var _dir := "user://phonecheck"


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
	if _next < SHOTS.size() and _t >= SHOTS[_next]:
		_next += 1
		_shot.call_deferred("t%02d" % int(_t))


func _shot(tag: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(_dir.path_join(tag + ".png"))
	_say("%s: shot, %.1f fps on average so far, %d fps now" % [tag, _frames / _t, Engine.get_frames_per_second()])
	_screen()


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
