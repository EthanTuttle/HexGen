class_name TownStage
extends Node3D
## The town's square and inn on their own, away from the map, from art/handoff/town_scenes_kit.md (town_scenes_v4). The map
## is hidden while it's up, as in a fight. It takes the camera and hands it back as it was.
## PLACEHOLDERS: the kit's own (glow strengths, lights, by eye against its previews), and the keepers, who are the hero kit's
## minis in a keeper's colour, as there are no keeper models yet.

const AT := Vector2(-1000, 0)          # the combat board is at +1000
const JSON_PATH := "res://art/town_scenes.json"
const FLOOR := 0.03
const VIEW_AT := Vector3(0.3, 0.6, -0.75)   # the kit's (0.3, 0.75, 0.6) in Blender's axes
const VIEW_DISTANCE := 33.0             # the kit's 21 m suits its 16:10 previews. On a phone's wide screen, with the speaker's panel and cards over the view, this keeps the party and the keeper in the clear
const VIEW_PITCH := 42.0
const SCREEN_FOCUS := {"square": Vector2(450, 174), "inn": Vector2(450, 186)}    # where it holds: between the speaker's panel and the cards
const MAX_DISTANCE := 42.0                  # behind the square's back row and outside the inn's walls is plain
const PAN_ROOM := 8.0
const INN_BACKDROP := Color("#2A1C15")
const LAMP := Color("#FFC27A")
const HEARTH := Color("#FF8C40")
const LIGHT_SCALE := 0.045             # Blender's point-light watts to Godot's energy, by eye
const LIGHT_RANGE := 5.5
const KEEPER_COLOURS := {"shopkeeper": "#B0672A", "innkeeper": "#3F6FA8"}

var game: Game
var data: Dictionary
var scene_name := ""
var _mesh := MeshInstance3D.new()
var _minis: Array[Node3D] = []
var _keeper: Node3D
var _lights: Array[OmniLight3D] = []
var _saved := {}
var _fire: Array[BaseMaterial3D] = []
var _night := false


func _init(g: Game) -> void:
	game = g
	data = JSON.parse_string(FileAccess.get_file_as_string(JSON_PATH))
	position = Hex.to3(AT)
	add_child(_mesh)


## Takes the camera and hides the map.
func begin() -> void:
	var r := game.rig
	_saved = {"target": r.target, "distance": r.distance, "pitch": r.pitch_deg, "yaw": r.yaw_deg, "focus": r.focus, "limits": r.limits, "floor": r.floor_at, "moved": r.player_moved}
	r.floor_at = Callable()
	var at := position
	r.limits = Rect2(at.x - PAN_ROOM, at.z - PAN_ROOM, PAN_ROOM * 2.0, PAN_ROOM * 2.0)
	game.map.visible = false
	game.party_node.visible = false


## Gives everything back.
func finish() -> void:
	var r := game.rig
	r.floor_at = _saved.floor
	r.focus = _saved.focus
	r.limits = _saved.limits
	r.frame(_saved.target, _saved.distance, _saved.pitch, _saved.yaw)
	r.player_moved = _saved.moved
	game.clock.backdrop_lock = Color(0, 0, 0, 0)
	game.clock.sun_scale = 1.0
	game.map.visible = true
	game.party_node.visible = true
	queue_free()


func _process(_delta: float) -> void:
	if game.rig.distance > MAX_DISTANCE:
		game.rig.distance = MAX_DISTANCE
	if not _fire.is_empty():   # a slow flicker on the hearth (PLACEHOLDER)
		var t := Time.get_ticks_msec() / 1000.0
		var f := 1.0 + 0.12 * sin(t * 7.0) + 0.08 * sin(t * 13.0 + 1.0)
		for k in _fire.size():
			_fire[k].emission_energy_multiplier = (1.3 if k == 0 else 1.5) * _glow() * f
		if scene_name == "inn" and not _lights.is_empty():
			_lights[0].light_energy = _hearth_energy() * f


func _glow() -> float:
	if _night:
		return 1.6
	return 0.9 if scene_name == "inn" else 0.4


func _hearth_energy() -> float:
	return (75.0 if _night else 55.0) * LIGHT_SCALE


## Shows a scene with the party on a set of spots.
func show_scene(which: String, spot_set: String, night: bool) -> void:
	scene_name = which
	_night = night
	var kit := Kit.meshes("res://art/town_scenes.glb")
	Kit.combat_materials(kit)
	_mesh.mesh = kit["town_" + which]
	_materials()
	_place_party(spot_set)
	_place_keeper()
	_place_lights()
	game.clock.backdrop_lock = INN_BACKDROP if which == "inn" else Color(0, 0, 0, 0)
	game.clock.sun_scale = 0.5 if night and which == "inn" else 1.0   # the kit's previews
	game.rig.focus = SCREEN_FOCUS[which]
	game.rig.frame(to_global(VIEW_AT), VIEW_DISTANCE, VIEW_PITCH)


## Rest's night fall: the kit's night lighting, without leaving the scene.
func set_night(night: bool) -> void:
	_night = night
	game.clock.sun_scale = 0.5 if night and scene_name == "inn" else 1.0
	_materials()
	_place_lights()


func _materials() -> void:
	_fire.clear()
	var m := _mesh.mesh
	for i in m.get_surface_count():
		var mat := m.surface_get_material(i) as BaseMaterial3D
		if mat == null:
			continue
		match mat.resource_name:
			"ts_glow":
				_glow_on(mat, _glow())
			"ts_fire":
				_glow_on(mat, _glow() * 1.3)
				_fire.append(mat)
			"ts_fire_b":
				_glow_on(mat, _glow() * 1.5)
				_fire.append(mat)


func _glow_on(mat: BaseMaterial3D, energy: float) -> void:
	mat.emission_enabled = true
	mat.emission = mat.albedo_color
	mat.emission_energy_multiplier = energy


func _hex(q: int, r: int) -> Vector3:
	var h: Array = data.hexes["%d,%d" % [q, r]]
	return Vector3(h[0], FLOOR, -h[1])


## Where the party stands (`spots` in the kit's data), checked clear of everything standing.
func spot(which: String, spot_set: String, i: int) -> Vector3:
	var s: Array = data.spots[which][spot_set][i]
	return _hex(int(s[0]), int(s[1]))


func _place_party(spot_set: String) -> void:
	var fresh := _minis.is_empty()
	if fresh:
		for m: Dictionary in game.party:
			var node := Minis.make(m.mini, Vector2.ZERO, Vector2(0, -1))
			add_child(node)
			_minis.append(node)
	for i in _minis.size():
		_minis[i].position = spot(scene_name, spot_set, i)
		_minis[i].rotation.y = _facing(spot_set, _minis[i].position)


## Towards what they came for; otherwise out at the camera, turned a little each.
func _facing(spot_set: String, from: Vector3) -> float:
	var place := ""
	if scene_name == "square" and spot_set in ["shop", "board"]:
		place = spot_set
	if place == "":
		return from.x * 0.08
	var p: Array = data.places[place]
	var d := _hex(int(p[0]), int(p[1])) - from
	return atan2(d.x, d.z)


func _place_keeper() -> void:
	if _keeper:
		_keeper.queue_free()
		_keeper = null
	var keepers: Dictionary = data.keepers[scene_name]
	for who: String in keepers:
		var k: Array = keepers[who]
		_keeper = MeshInstance3D.new()
		_keeper.name = who
		(_keeper as MeshInstance3D).mesh = HeroMini.mesh_for_description({"race": "human", "build": "average", "head": "a", "hair": "short", "armour": "none",
			"main": "wraps", "offhand": "", "colours": {"skin": "#C68E64", "hair": "#5A3A26", "eyes": "#3E6FA0", "cloth": KEEPER_COLOURS[who]}})
		add_child(_keeper)
		_keeper.position = _hex(int(k[0]), int(k[1])) + Vector3(k[3], 0.0, -k[2])


func _place_lights() -> void:
	for l in _lights:
		l.queue_free()
	_lights.clear()
	if scene_name == "inn":
		var h := _hex(-2, 1)
		_add_light(h + Vector3(0.5, 0.9, -0.15), HEARTH, _hearth_energy())
		var lamp: float = (16.0 if _night else 8.0) * LIGHT_SCALE
		for t: Array in data.inn_places.tables:
			_add_light(_hex(int(t[0]), int(t[1])) + Vector3(0, 1.2, 0), LAMP, lamp)
		_add_light(_hex(0, -2) + Vector3(0.3, 1.5, -0.9), LAMP, lamp)
		_add_light(_hex(2, -2) + Vector3(0.3, 1.5, -0.9), LAMP, lamp)
	elif _night:
		_add_light(_hex(-1, -1) + Vector3(0.5, 1.8, -0.2), LAMP, 32.0 * LIGHT_SCALE)
		_add_light(_hex(2, 0) + Vector3(0.5, 1.8, -0.2), LAMP, 32.0 * LIGHT_SCALE)
		_add_light(_hex(1, -2) + Vector3(0.5, 0.9, -0.2), LAMP, 32.0 * LIGHT_SCALE)


func _add_light(at: Vector3, col: Color, energy: float) -> void:
	var l := OmniLight3D.new()
	l.position = at
	l.light_color = col
	l.light_energy = energy
	l.omni_range = LIGHT_RANGE
	l.omni_attenuation = 1.4
	add_child(l)
	_lights.append(l)


## The speaker hops at the bar (Town v2e).
func hop(i: int) -> void:
	if i >= _minis.size():
		return
	var body: Node3D = _minis[i].get_node("body")
	var tw := body.create_tween()
	tw.tween_property(body, "position:y", 0.28, 0.14).set_ease(Tween.EASE_OUT)
	tw.tween_property(body, "position:y", 0.0, 0.16).set_ease(Tween.EASE_IN)
