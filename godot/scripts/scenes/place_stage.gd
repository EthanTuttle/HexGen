class_name PlaceStage
extends Node3D
## A place's scene on its own, away from the map: any kit in Places.KITS (the market square and the inn from
## art/handoff/town_scenes_kit.md, town_scenes_v4, so far). The map is hidden while it's up, as in a fight. It takes the
## camera and hands it back as it was.
## PLACEHOLDERS: the kits' own (glow strengths, lights, by eye against their previews), and the keepers, who are the hero
## kit's minis in a keeper's colour, as there are no keeper models yet.

const AT := Vector2(-1000, 0)          # the combat board is at +1000
const FLOOR := 0.03
const VIEW_AT := Vector3(0.3, 0.6, -0.75)   # the town kit's (0.3, 0.75, 0.6) in Blender's axes
const VIEW_DISTANCE := 33.0             # the kit's 21 m suits its 16:10 previews. On a phone's wide screen, with the speaker's panel and cards over the view, this keeps the party and the keeper in the clear
const VIEW_PITCH := 42.0
const MAX_DISTANCE := 42.0                  # behind a scene's back row and outside the inn's walls is plain
const PAN_ROOM := 8.0
const LIGHT_SCALE := 0.045             # Blender's point-light watts to Godot's energy, by eye
const LIGHT_RANGE := 5.5

var game: Game
var data: Dictionary                   # the shown kit's JSON
var kit: Dictionary                    # the shown kit's Places.KITS entry
var scene_name := ""                   # the shown kit's id
var _mesh := MeshInstance3D.new()
var _minis: Array[Node3D] = []
var _keeper: Node3D
var _lights: Array[OmniLight3D] = []
var _flicker: Array = []               # [light, energy] for each light that flickers with the fire
var _saved := {}
var _fire: Array[BaseMaterial3D] = []
var _night := false


func _init(g: Game) -> void:
	game = g
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
	if not _fire.is_empty():   # a slow flicker on the fire (PLACEHOLDER)
		var t := Time.get_ticks_msec() / 1000.0
		var f := 1.0 + 0.12 * sin(t * 7.0) + 0.08 * sin(t * 13.0 + 1.0)
		for k in _fire.size():
			_fire[k].emission_energy_multiplier = (1.3 if k == 0 else 1.5) * _glow() * f
		for fl: Array in _flicker:
			(fl[0] as OmniLight3D).light_energy = fl[1] * f


func _glow() -> float:
	return Places.NIGHT_GLOW if _night else float(kit.glow)


## Shows a kit's scene with the party on a set of spots.
func show_scene(which: String, spot_set: String, night: bool) -> void:
	scene_name = which
	kit = Places.KITS[which]
	data = JSON.parse_string(FileAccess.get_file_as_string(kit.json))
	_night = night
	var meshes := Kit.meshes(kit.glb)
	Kit.combat_materials(meshes)
	_mesh.mesh = meshes[kit.mesh]
	_materials()
	_place_party(spot_set)
	_place_keeper()
	_place_lights()
	var backdrop: String = data.get("backdrop", kit.backdrop)
	game.clock.backdrop_lock = Color(backdrop) if backdrop != "" else Color(0, 0, 0, 0)
	game.clock.sun_scale = float(kit.night_sun) if night else 1.0   # the kits' previews
	game.rig.focus = kit.focus
	game.rig.frame(to_global(VIEW_AT), VIEW_DISTANCE, VIEW_PITCH)


## Rest's night fall: the kit's night lighting, without leaving the scene.
func set_night(night: bool) -> void:
	_night = night
	game.clock.sun_scale = float(kit.night_sun) if night else 1.0
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


## The kit's places the party can walk to: `<kit>_places`, or `places` (the town kit keeps the square's there).
func _places() -> Dictionary:
	return data.get(scene_name + "_places", data.get("places", {}))


## Towards what they came for; otherwise out at the camera, turned a little each.
func _facing(spot_set: String, from: Vector3) -> float:
	var p = _places().get(spot_set) if spot_set in ["shop", "board"] else null
	if not p is Array or (p as Array).is_empty() or (p as Array)[0] is Array:
		return from.x * 0.08
	var d := _hex(int(p[0]), int(p[1])) - from
	return atan2(d.x, d.z)


func _place_keeper() -> void:
	if _keeper:
		_keeper.queue_free()
		_keeper = null
	var keepers: Dictionary = data.keepers.get(scene_name, {})
	for who: String in keepers:
		var k: Array = keepers[who]
		_keeper = MeshInstance3D.new()
		_keeper.name = who
		(_keeper as MeshInstance3D).mesh = HeroMini.mesh_for_description({"race": "human", "build": "average", "head": "a", "hair": "short", "armour": "none",
			"main": "wraps", "offhand": "", "colours": {"skin": "#C68E64", "hair": "#5A3A26", "eyes": "#3E6FA0", "cloth": Places.KEEPER_COLOURS.get(who, "#7A6A58")}})
		add_child(_keeper)
		_keeper.position = _hex(int(k[0]), int(k[1])) + Vector3(k[3], 0.0, -k[2])


func _place_lights() -> void:
	for l in _lights:
		l.queue_free()
	_lights.clear()
	_flicker.clear()
	for l: Array in data.get("lights", kit.lights):
		var energy: float = float(l[7] if _night else l[6]) * LIGHT_SCALE
		if energy <= 0.0:
			continue
		var light := _add_light(_hex(int(l[0]), int(l[1])) + Vector3(l[2], l[3], l[4]), Color(l[5]), energy)
		if l[8]:
			_flicker.append([light, energy])


func _add_light(at: Vector3, col: Color, energy: float) -> OmniLight3D:
	var l := OmniLight3D.new()
	l.position = at
	l.light_color = col
	l.light_energy = energy
	l.omni_range = LIGHT_RANGE
	l.omni_attenuation = 1.4
	add_child(l)
	_lights.append(l)
	return l


## The speaker hops at the bar (Town v2e).
func hop(i: int) -> void:
	if i >= _minis.size():
		return
	var body: Node3D = _minis[i].get_node("body")
	var tw := body.create_tween()
	tw.tween_property(body, "position:y", 0.28, 0.14).set_ease(Tween.EASE_OUT)
	tw.tween_property(body, "position:y", 0.0, 0.16).set_ease(Tween.EASE_IN)
