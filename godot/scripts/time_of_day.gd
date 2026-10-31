class_name TimeOfDay
extends Node
## The pastel backdrop and the light drift with the day clock (look test 2;
## design/07 Presentation.md -> Art direction: soft peach at dawn, pale sky-blue at midday,
## rose at dusk, a darker, cooler pastel at night).
## DOCS: the sun colour, strength, height and ambient light below are the chosen look (Oct 30, 2026;
## revisit in playtesting): design/07 Presentation.md -> Art direction -> Time of day -> The light.
## Midday matches the Blender previews (backdrop #CFE4F2, the preview sun). The backdrops here are the
## look tests'; the loop uses its own (Game.SKY).
## Keys: T starts or stops the clock, [ and ] step an hour.

@export var hour := 12.0
@export var running := false
@export var day_seconds := 90.0           # a whole day per this many seconds while running (test speed)

var environment: Environment
var keys: Array = KEYS        # the game swaps in the mockups' backdrop colours
var sun: DirectionalLight3D
## The sun's angle moves in steps this many hours apart, blending to each over `sun_blend_seconds`, so shadows
## hold still between steps instead of creeping (0: it follows the clock exactly, as in the look tests).
var sun_step_hours := 0.0
var sun_blend_seconds := 0.6
var _sun_hour := -1.0
var _sun_from := Quaternion.IDENTITY
var _sun_to := Quaternion.IDENTITY
var _blend := 1.0

# hour, backdrop (sRGB), sun colour, sun energy, sun elevation (deg), sun travel azimuth (deg), ambient energy
# (ambient is lifted when the sun is low, so the shade side of dense pieces like the deep forest isn't black)
const KEYS := [
	[0.0, "#5F6B8F", "#AFC0E8", 0.35, 35.0, 28.4, 0.5],    # night: moonlight
	[4.5, "#5F6B8F", "#AFC0E8", 0.35, 35.0, 28.4, 0.5],
	[6.5, "#F6D5C0", "#FFE2C8", 1.1, 24.0, -30.0, 0.7],   # dawn: soft peach
	[9.0, "#CFE4F2", "#FFFFFF", 1.18, 30.0, 0.0, 0.55],
	[12.0, "#CFE4F2", "#FFFFFF", 1.18, 37.7, 28.4, 0.5],   # midday: the preview backdrop and sun
	[15.0, "#CFE4F2", "#FFFFFF", 1.18, 30.0, 60.0, 0.55],
	[18.0, "#F1C6CF", "#FFD8CC", 1.1, 24.0, 90.0, 0.7],   # dusk: rose
	[20.0, "#5F6B8F", "#AFC0E8", 0.35, 35.0, 28.4, 0.5],
	[24.0, "#5F6B8F", "#AFC0E8", 0.35, 35.0, 28.4, 0.5],
]


func _process(delta: float) -> void:
	if running:
		hour = fmod(hour + delta * 24.0 / day_seconds, 24.0)
	_blend = minf(1.0, _blend + delta / maxf(sun_blend_seconds, 0.001))
	apply()


## The two keys around hour h and how far between them (eased).
func _between(h: float) -> Array:
	var k := 0
	while k < keys.size() - 2 and keys[k + 1][0] <= h:
		k += 1
	var a: Array = keys[k]
	var b: Array = keys[k + 1]
	return [a, b, smoothstep(0.0, 1.0, (h - a[0]) / maxf(b[0] - a[0], 0.001))]


## Which way the sun shines at hour h.
func _sun_at(h: float) -> Quaternion:
	var ab := _between(h)
	var a: Array = ab[0]
	var b: Array = ab[1]
	var el := deg_to_rad(lerpf(a[4], b[4], ab[2]))
	var az := deg_to_rad(lerpf(a[5], b[5], ab[2]))
	# Direction the light travels, in plan coordinates, then in Godot's Y-up world.
	var dir := Vector3(cos(el) * cos(az), -sin(el), -cos(el) * sin(az))
	return Basis.looking_at(dir, Vector3.UP if absf(dir.y) < 0.99 else Vector3.FORWARD).get_rotation_quaternion()


func apply() -> void:
	var ab := _between(hour)
	var a: Array = ab[0]
	var b: Array = ab[1]
	var t: float = ab[2]
	var backdrop := Color.html(a[1]).lerp(Color.html(b[1]), t)
	environment.background_color = backdrop
	# The backdrop also lights the scene, softer (Blender world: strength 0.5 off camera).
	environment.ambient_light_color = backdrop
	environment.ambient_light_energy = lerpf(a[6], b[6], t)
	sun.light_color = Color.html(a[2]).lerp(Color.html(b[2]), t)
	sun.light_energy = lerpf(a[3], b[3], t)
	if sun_step_hours <= 0.0:
		sun.basis = Basis(_sun_at(hour))
		return
	var step := floorf(hour / sun_step_hours) * sun_step_hours
	if step != _sun_hour:
		_sun_from = sun.basis.get_rotation_quaternion() if _sun_hour >= 0.0 else _sun_at(step)
		_sun_to = _sun_at(step)
		_sun_hour = step
		_blend = 0.0 if _sun_from.angle_to(_sun_to) > 0.0001 else 1.0
	sun.basis = Basis(_sun_from.slerp(_sun_to, smoothstep(0.0, 1.0, _blend)))


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match (event as InputEventKey).keycode:
			KEY_T:
				running = not running
			KEY_BRACKETLEFT:
				hour = fposmod(hour - 1.0, 24.0)
			KEY_BRACKETRIGHT:
				hour = fposmod(hour + 1.0, 24.0)


func label() -> String:
	var name := "night"
	if hour >= 5.0 and hour < 8.0:
		name = "dawn"
	elif hour >= 8.0 and hour < 16.5:
		name = "midday"
	elif hour >= 16.5 and hour < 19.5:
		name = "dusk"
	return "%02d:%02d %s" % [int(hour), int(fmod(hour, 1.0) * 60), name]
