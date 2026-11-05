class_name Front
extends Node3D
## The default scene: the title screen over a small world, then the creator, then the game (design/06 -> First playable).
## Any run with its own arguments or a phone-check variable goes straight to the game, so every check, demo and
## phone run starts as it always has. `--direct` asks for that with no other arguments; `--front` forces the title.

const GAME_SCENE := "res://scenes/main.tscn"
const PHONE_FLAGS: Array[String] = ["HEXGEN_PHONECHECK", "HEXGEN_PHONELIST", "HEXGEN_FORESTPERF", "HEXGEN_PHONEQUICK"]
## The title's generic world for a first launch (DOCS: Title screen -> v1b), by tile. PLACEHOLDER: no doc sets it.
const FOV := 40.0
const TILE_REACH := 5.0                # m from a tile's centre to its far corner, and a little
const DRIFT_SECONDS := 40.0            # Title v11's pan
const DRIFT_METRES := Vector3(5.0, 0.0, -3.0)
const DUSK_HOUR := 17.6                # Title v11's backdrop: #EDCFD7

var map := MapBoard.new()
var clock: TimeOfDay
var cam := Camera3D.new()
var ui := CanvasLayer.new()
var safe := SafeArea.new()
var title: TitleScreen
var creator: Creator
var _backdrop := ColorRect.new()
var _t := 0.0


static func goes_direct() -> bool:
	var args := OS.get_cmdline_user_args()
	if "--front" in args:
		return false
	return not args.is_empty() or PHONE_FLAGS.any(func(f): return OS.get_environment(f) == "1")


func _ready() -> void:
	TestNotes.attach(get_tree())
	if goes_direct():
		for unused: Node in [map, cam, ui, safe, _backdrop]:   # never added to the tree, so nothing else frees them
			unused.free()
		get_tree().change_scene_to_file.call_deferred(GAME_SCENE)
		return
	clock = Stage.create(self)
	clock.running = false
	clock.keys = Game.sky_keys()
	clock.hour = DUSK_HOUR
	map.time_of_day = clock
	add_child(map)
	var t0 := Time.get_ticks_msec()
	map.retile(world())
	print("FRONT world: %d tiles in %d ms" % [map.terrains.size(), Time.get_ticks_msec() - t0])
	cam.current = true
	add_child(ui)
	_backdrop.color = Color("#BFD9D2")   # Creator v16's plain background
	_backdrop.set_anchors_preset(Control.PRESET_FULL_RECT)
	_backdrop.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_backdrop.visible = false
	ui.add_child(_backdrop)
	ui.add_child(safe)
	title = TitleScreen.new(self)
	safe.add_child(title)
	_drift(0.0)
	title.new_campaign.connect(open_creator)
	if "--check" in OS.get_cmdline_user_args():
		var check := FrontCheck.new()
		check.front = self
		get_tree().root.add_child.call_deferred(check)   # outlives the change of scene


func _process(delta: float) -> void:
	if cam.is_inside_tree():
		_drift(delta)


## Title v11's slow pan there and back, eased (CSS: ease-in-out over 40 s).
func _drift(delta: float) -> void:
	_t += delta
	_aim(sin(_t * TAU / DRIFT_SECONDS))


func _aim(along: float) -> void:
	var at := DRIFT_METRES * along + Vector3(6.0, 0.0, 0.0)
	cam.position = at + Vector3(0.0, 28.0, 30.0)
	cam.look_at(at)


## PLACEHOLDER: a generic land along a river: woods and hills to the north, farms and a town to the south. Only the
## tiles the drifting camera can see are built, as each one costs load time.
func world() -> Dictionary:
	var out := {}
	cam.fov = FOV
	add_child(cam)
	var ends: Array[float] = [-1.0, 0.0, 1.0]
	for q in range(-16, 17):
		for r in range(-16, 17):
			var at := Hex.to3(Hex.tile_position(q, r))
			for along in ends:
				_aim(along)
				if cam.is_position_in_frustum(at) or _near_view(at):
					out[Vector2i(q, r)] = _terrain(q, r)
					break
	return out


## A tile whose centre is just off screen still shows its edge.
func _near_view(at: Vector3) -> bool:
	for d: Vector3 in [Vector3(TILE_REACH, 0, 0), Vector3(-TILE_REACH, 0, 0), Vector3(0, 0, TILE_REACH), Vector3(0, 0, -TILE_REACH)]:
		if cam.is_position_in_frustum(at + d):
			return true
	return false


static func _terrain(q: int, r: int) -> String:
	var river := floori(-q / 2.0)
	if r == river:
		return "river"
	if r < river:
		if q >= 5 and r <= -5:
			return "hills"
		return "forest" if posmod(q * 7 + r * 3, 5) != 0 else "plains"
	if r >= 2 and q >= -1 and q <= 2:
		return "village"
	return "farmland" if q >= 3 else "plains"


func open_creator() -> void:
	title.visible = false
	_backdrop.visible = true
	map.visible = false
	creator = Creator.new()
	safe.add_child(creator)
	creator.finished.connect(start_game)
	creator.cancelled.connect(_close_creator)


func _close_creator() -> void:
	creator.queue_free()
	creator = null
	_backdrop.visible = false
	map.visible = true
	title.visible = true


## Leaves for the game, through the send-off.
func start_game(hero: Hero, banners: Array) -> void:
	SendOff.new().play(get_tree(), hero, banners)
