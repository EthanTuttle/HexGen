class_name StallWatch
extends Node
## A test aid: on a check, demo or touch run, prints the game's state when nothing has moved for STALL_SECONDS (a check's
## await that never ends otherwise just stops the output: DOCS: 06 -> Engine prototype, error logging). Test output only.
## Checks call beat() as they go. The dump also says what is waiting: who's connected to the signals an await can sit on, and
## whether frames are still drawn. A second dump comes at QUIT_SECONDS, then a `--quit` run ends instead of using up its limit.

const STALL_SECONDS := 60.0
const QUIT_SECONDS := 150.0
const NODRAW_AFTER := 20.0
const DRAW_WAIT_MS := 3000

static var _beats := 0
static var _last := ""

var game: Game
var _quiet := 0.0
var _seen := []
var _reported := false
var _draws := 0
var _procs := 0
var _draws_quiet := 0
var _procs_quiet := 0


func _ready() -> void:
	RenderingServer.frame_post_draw.connect(func(): _draws += 1)
	get_tree().process_frame.connect(func(): _procs += 1)
	if "--nodraw" in OS.get_cmdline_user_args():   # stops drawing as a hidden window does, to test the waits below
		await get_tree().create_timer(NODRAW_AFTER).timeout
		print("STALL TEST: drawing stopped")
		RenderingServer.render_loop_enabled = false


## Waits for a frame to be drawn, or says it wasn't and carries on (true if drawn). On the Mac nothing is drawn while the window is
## hidden, covered by other windows after the screen unlocks, so `await frame_post_draw` alone never ended and hung the check
## (README -> Stall detector). Processing goes on as normal. A check's screens and pixel comparisons after an UNDRAWN line can't be trusted.
static func drawn(tree: SceneTree) -> bool:
	var seen := [false]
	var mark := func(): seen[0] = true
	RenderingServer.frame_post_draw.connect(mark, CONNECT_ONE_SHOT)
	var until := Time.get_ticks_msec() + DRAW_WAIT_MS
	while not seen[0] and Time.get_ticks_msec() < until:
		await tree.process_frame
	if not seen[0]:
		RenderingServer.frame_post_draw.disconnect(mark)
		print("UNDRAWN: no frame drawn in %d ms, is the window hidden? Last check: %s" % [DRAW_WAIT_MS, _last])
	return seen[0]


## A check has got this far.
static func beat(what: String) -> void:
	_beats += 1
	_last = what


func _process(delta: float) -> void:
	var now := [_beats, game.map.tiles_built, game.party_node.members[0].node.position, game.rig.target, game.rig.distance, game.fight.active, game.busy, game.fight.units.map(func(u): return [u.cell, u.hp])]
	if now != _seen:
		_seen = now
		_quiet = 0.0
		_reported = false
		_draws_quiet = _draws
		_procs_quiet = _procs
		return
	_quiet += delta
	if _quiet > STALL_SECONDS and not _reported:
		_reported = true
		_dump()
	elif _quiet > QUIT_SECONDS:
		_dump()
		if "--quit" in OS.get_cmdline_user_args():
			get_tree().quit(3)
		_quiet = STALL_SECONDS + 1.0


func _dump() -> void:
	print("STALL %d s with nothing moving, last check: %s | tile %s, busy %s, walking %s, holding %s, check pop-up %s, shop %s, encounter %s, fight %s, day %d minute %.1f, tiles built %d" % [
			int(_quiet), _last, game.party_tile, game.busy, game.party_node.walking, game.party_node.holding,
			game.hud.check.visible, game.hud.shop.visible, game.hud.encounter_open(), game.fight.active, game.day, game.minute, game.map.tiles_built])
	print("STALL panels: level up %s, after combat %s, end panel %s, ended %s, town %s, fading %s" % [game.level_up.visible, game.after.visible, game.end_panel.visible, game._ended, game.get("in_town"), game.get("_fading")])
	print("STALL frames in those %d s: %d processed, %d post-draw signals, %d drawn in all; %.0f fps; time scale %.2f; paused %s; render loop %s; window mode %d, focused %s, size %s" % [
			int(_quiet), _procs - _procs_quiet, _draws - _draws_quiet, Engine.get_frames_drawn(), Engine.get_frames_per_second(), Engine.time_scale,
			get_tree().paused, RenderingServer.render_loop_enabled, DisplayServer.window_get_mode(), DisplayServer.window_is_focused(), DisplayServer.window_get_size()])
	print("STALL waiting on: post-draw %s | process frame %s | physics frame %s" % [_waiters(RenderingServer.frame_post_draw), _waiters(get_tree().process_frame), _waiters(get_tree().physics_frame)])


## Who's connected to a signal, other than this watch: a check's await shows as a GDScriptFunctionState.
func _waiters(s: Signal) -> String:
	var out := []
	for c: Dictionary in s.get_connections():
		var who: Object = (c.callable as Callable).get_object()
		if who != self:
			out.append("%s.%s" % [who.get_class() if who != null else "null", (c.callable as Callable).get_method()])
	return "%d %s" % [out.size(), out]
