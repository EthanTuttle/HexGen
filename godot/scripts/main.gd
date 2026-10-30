extends Node3D
## The look tests (scenes/look_tests.tscn); the playable loop is scenes/main.tscn (scripts/game/game.gd).
## Godot half of the engine prototype: the look tests (design/06 Multiplayer & tech.md -> Engine prototype).
## Tab switches between the map board and the combat board.
##
## Screenshots: godot --path godot scenes/look_tests.tscn -- --shots         (writes godot/screens/*.png and quits)
## Every terrain, and every region finished (render_preview.py -- --terrains / -- --variants):
##              godot --path godot --resolution 1600x1000 scenes/look_tests.tscn -- --map=terrains --shots --only=terrains
## Movie:       godot --path godot --write-movie out.png --fixed-fps 30 --quit-after 240 scenes/look_tests.tscn -- --view=water

# Framings of the Blender previews (render_preview.stage: target, distance, elevation).
var VIEWS := {
	"map": [Vector2(2, -2), 74.0, 45.0],
	"water": [Vector2(-3.5, -10.5), 20.0, 40.0],
	"water_anim": [Vector2(5, -5), 46.0, 42.0],   # render_animation.py framing
	"combat": [Vector2(0, -0.4), 20.0, 48.0],
	"terrains": [Vector2(4, -1), 82.0, 45.0],   # render_preview --terrains / --variants framing
	"party": [Vector2(3.897 + 0.6, -6.75 - 0.9), 22.0, 45.0],   # standin_map framing, on tile (0, 1)
}
const COMBAT_AT := Vector2(1000, 0)   # the combat board lives away from the map

var map := MapBoard.new()
var combat := CombatBoard.new()
var rig := CameraRig.new()
var clock: TimeOfDay
var hud := Label.new()
var mode := "map"
var _look_yaw := 0.0
var which := "test"


func _ready() -> void:
	clock = Stage.create(self)

	map.name = "map"
	map.time_of_day = clock
	add_child(map)
	which = "test"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--map="):
			which = a.split("=")[1]
	var t0 := Time.get_ticks_msec()
	if which == "terrains":
		map.build(MapBoard.TERRAIN_MAP)
	elif which == "variants":
		map.build(MapBoard.variant_map())
	else:
		map.build()
		map.add_child(Minis.party(Hex.tile_position(0, 1)))
	if "--perf" in OS.get_cmdline_user_args():
		print("PERF build %s map: %d tiles in %d ms" % [which, map.terrains.size(), Time.get_ticks_msec() - t0])
		_perf.call_deferred()

	combat.name = "combat"
	combat.position = Hex.to3(COMBAT_AT)
	add_child(combat)
	combat.build()

	add_child(rig)
	var layer := CanvasLayer.new()
	add_child(layer)
	hud.position = Vector2(16, 12)
	hud.add_theme_color_override("font_color", Color(0.2, 0.22, 0.26))
	layer.add_child(hud)

	var args := OS.get_cmdline_user_args()
	var view := "map"
	for a in args:
		if a.begins_with("--view="):
			view = a.split("=")[1]
		elif a.begins_with("--look="):   # x,y,distance,pitch,yaw in plan coordinates, for checking details
			var v := a.split("=")[1].split_floats(",")
			VIEWS["look"] = [Vector2(v[0], v[1]), v[2], v[3]]
			view = "look"
			_look_yaw = v[4] if v.size() > 4 else 0.0
		elif a.begins_with("--hour="):
			clock.hour = float(a.split("=")[1])
	if "--review" in args:
		hud.visible = false
		_review.call_deferred(which)
	elif "--shots" in args:
		hud.visible = false
		_shots.call_deferred()
	else:
		show_view(view)
		hud.visible = not ("--nohud" in args)


## Close-ups from the game camera (the loop's 50 degree tilt, nearer than the overview), at dawn, midday,
## dusk and night, into screens/review/ (`-- --map=terrains|variants --review`).
func _review(map_name: String) -> void:
	var out := ProjectSettings.globalize_path("res://screens/review")
	DirAccess.make_dir_recursive_absolute(out)
	clock.keys = Game.sky_keys()   # the loop's backdrop colours, so the light is the game's
	var frames := {"west": Vector2(-7.8, -5.5), "centre": Vector2(6.0, 1.5), "east": Vector2(19.5, 2.0),
		"south": Vector2(10.0, -11.0)}
	var times := {"dawn": 6.5, "midday": 12.0, "dusk": 18.0, "night": 22.0}
	for f in frames:
		for t in times:
			clock.hour = times[t]
			rig.frame(Hex.to3(frames[f]), 34.0, 50.0)
			for _k in 12:
				await get_tree().process_frame
			await RenderingServer.frame_post_draw
			get_viewport().get_texture().get_image().save_png(out.path_join("%s_%s_%s.png" % [map_name, f, t]))
	print("REVIEW DONE")
	get_tree().quit()


## Prints the frame cost of the current view after it settles (`-- --perf`).
func _perf() -> void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	for _f in 240:   # let shaders compile and the camera settle
		await get_tree().process_frame
	var rs := RenderingServer
	var info := [rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
		rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME),
		rs.get_rendering_info(rs.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME)]
	var t0 := Time.get_ticks_usec()
	for _f in 300:
		await get_tree().process_frame
	var ms := (Time.get_ticks_usec() - t0) / 300000.0
	print("PERF draw calls %d, primitives %d, objects %d; %.1f ms a frame (%.0f fps, vsync off)" % [
		info[0], info[1], info[2], ms, 1000.0 / ms])


func show_view(view: String) -> void:
	mode = "combat" if view == "combat" else "map"
	map.visible = mode == "map"
	combat.visible = mode == "combat"
	combat.auto_play = mode == "combat"   # look test: attacks play by themselves
	var v: Array = VIEWS[view]
	var at: Vector2 = v[0] + (COMBAT_AT if mode == "combat" else Vector2.ZERO)
	rig.frame(Hex.to3(at), v[1], v[2], _look_yaw if view == "look" else 0.0)
	rig.min_distance = 3.0 if mode == "combat" else 6.0


func _process(_delta: float) -> void:
	if hud.visible:
		hud.text = "%s   %s%s\nTab map/combat · drag pan · wheel zoom · right-drag or Q/E rotate · F frame · T clock · [ ] hour%s" % [
			mode, clock.label(), "  (running)" if clock.running else "",
			" · Space attack" if mode == "combat" else ""]


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_TAB:
		show_view("map" if mode == "combat" else "combat")


func _shots() -> void:
	var out := ProjectSettings.globalize_path("res://screens")
	DirAccess.make_dir_recursive_absolute(out)
	var shots := [
		["map_board", "map", 12.0], ["water_closeup", "water", 12.0], ["combat_board", "combat", 12.0],
		["party_closeup", "party", 12.0],
		["look", "look", 12.0], ["map_dawn", "map", 6.5], ["map_dusk", "map", 18.0], ["map_night", "map", 22.0],
		["terrains", "terrains", 12.0], ["variants", "terrains", 12.0], ["variants_night", "terrains", 22.0],
	]
	var only := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--only="):
			only = a.split("=")[1]
	for s in shots:
		if (only and not s[0] in only.split(",")) or not VIEWS.has(s[1]):
			continue
		clock.hour = s[2]
		show_view(s[1])
		combat.auto_play = false
		for _f in 20:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		img.save_png(out.path_join(s[0] + ".png"))
		print("SAVED ", s[0])
	get_tree().quit()
