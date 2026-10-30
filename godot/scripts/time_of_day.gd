class_name TimeOfDay
extends Node
## The pastel backdrop and the light drift with the day clock (look test 2;
## design/07 Presentation.md -> Art direction: soft peach at dawn, pale sky-blue at midday,
## rose at dusk, a darker, cooler pastel at night).
## Every colour and angle below except midday is a PLACEHOLDER: the exact colours per time of day
## are an open question in the docs. Midday matches the Blender previews (backdrop #CFE4F2, the
## preview sun), so the screenshots line up with art/preview.
## Keys: T starts or stops the clock, [ and ] step an hour.

@export var hour := 12.0
@export var running := false
@export var day_seconds := 90.0           # a whole day per this many seconds while running (test speed)

var environment: Environment
var sun: DirectionalLight3D

# hour, backdrop (sRGB), sun colour, sun energy, sun elevation (deg), sun travel azimuth (deg)
const KEYS := [
	[0.0, "#5F6B8F", "#AFC0E8", 0.35, 35.0, 28.4],    # night: moonlight
	[4.5, "#5F6B8F", "#AFC0E8", 0.35, 35.0, 28.4],
	[6.5, "#F6D5C0", "#FFD2A8", 1.1, 24.0, -30.0],   # dawn: soft peach
	[9.0, "#CFE4F2", "#FFFFFF", 1.18, 30.0, 0.0],
	[12.0, "#CFE4F2", "#FFFFFF", 1.18, 37.7, 28.4],   # midday: the preview backdrop and sun
	[15.0, "#CFE4F2", "#FFFFFF", 1.18, 30.0, 60.0],
	[18.0, "#F1C6CF", "#FFC0A8", 1.1, 24.0, 90.0],   # dusk: rose
	[20.0, "#5F6B8F", "#AFC0E8", 0.35, 35.0, 28.4],
	[24.0, "#5F6B8F", "#AFC0E8", 0.35, 35.0, 28.4],
]


func _process(delta: float) -> void:
	if running:
		hour = fmod(hour + delta * 24.0 / day_seconds, 24.0)
	apply()


func apply() -> void:
	var k := 0
	while k < KEYS.size() - 2 and KEYS[k + 1][0] <= hour:
		k += 1
	var a: Array = KEYS[k]
	var b: Array = KEYS[k + 1]
	var t := smoothstep(0.0, 1.0, (hour - a[0]) / maxf(b[0] - a[0], 0.001))
	var backdrop := Color.html(a[1]).lerp(Color.html(b[1]), t)
	environment.background_color = backdrop
	# The backdrop also lights the scene, softer (Blender world: strength 0.5 off camera).
	environment.ambient_light_color = backdrop
	environment.ambient_light_energy = 0.5
	sun.light_color = Color.html(a[2]).lerp(Color.html(b[2]), t)
	sun.light_energy = lerpf(a[3], b[3], t)
	var el := deg_to_rad(lerpf(a[4], b[4], t))
	var az := deg_to_rad(lerpf(a[5], b[5], t))
	# Direction the light travels, in plan coordinates, then in Godot's Y-up world.
	var dir := Vector3(cos(el) * cos(az), -sin(el), -cos(el) * sin(az))
	sun.basis = Basis.looking_at(dir, Vector3.UP if absf(dir.y) < 0.99 else Vector3.FORWARD)


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
