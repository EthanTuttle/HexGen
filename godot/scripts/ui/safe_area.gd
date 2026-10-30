class_name SafeArea
extends Control
## The HUD's root (DOCS: Camera and controls -> Phone screen edges): the board and backdrop fill the whole
## screen, behind the Dynamic Island too, but the trays, hand, hotbar, buttons and pop-ups keep out of the
## island's strip. On whichever side the island is, this control's left or right edge moves in by the
## safe-area inset; the HUD inside it lays out as before. Only left and right matter: the home bar is
## hidden while playing (project.godot: display/window/ios/hide_home_indicator).
## The island swaps sides when the phone turns round without the size changing, so the inset is read
## again every half second, not only on resize.
## `-- --safe=left|right` fakes a 59 pt inset on that side (the iPhone 15 Pro's), for testing on the Mac.

const FAKE_INSET := 59.0

var inset := Vector2.ZERO          # left, right, in layout units (about pt)
var _fake := ""
var _wait := 0.0


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--safe="):
			_fake = a.split("=")[1]
	get_tree().root.size_changed.connect(_update)
	_update()


func _process(delta: float) -> void:
	_wait -= delta
	if _wait <= 0.0:
		_wait = 0.5
		_update()


func _update() -> void:
	var want := Vector2.ZERO
	if _fake == "left":
		want.x = FAKE_INSET
	elif _fake == "right":
		want.y = FAKE_INSET
	else:
		var screen := Vector2(DisplayServer.screen_get_size())
		var safe := Rect2(DisplayServer.get_display_safe_area())
		if screen.x > 0 and safe.size.x > 0 and safe.size.x < screen.x:
			# Screen pixels to layout units: the window fills the screen on a phone.
			var k := get_viewport_rect().size.x / screen.x
			want = Vector2(safe.position.x, screen.x - safe.end.x) * k
	if want != inset:
		inset = want
		offset_left = inset.x
		offset_right = -inset.y
