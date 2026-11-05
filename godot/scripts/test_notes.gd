class_name TestNotes
extends CanvasLayer
## Test notes (design/06 -> First playable, Ethan, Nov 4, 2026): a small flag on every screen in test builds, for typing an
## issue, bug or tweak during play. Each note is a JSON file with its screenshot, taken before the box opened, and the
## game's state, in user://test_notes. No network. The total is capped, and nothing here ever deletes a note: at the cap the
## box says so and Save is off until they're collected (tools/collect_notes.sh). A test aid, not game UI: it isn't under the
## Screen text rules, and it never ships.

const MAX_NOTES := 500                 # PLACEHOLDER caps. Past the bytes, notes still save, without a screenshot
const MAX_BYTES := 150 * 1024 * 1024
const SHOT_SCALE := 0.5
const FLAG_ICON := "M6 21V4 M6 4h11l-3 4 3 4H6"
## Runs that aren't play keep their screens and numbers as they were.
const PLAY_ARGS: Array[String] = ["--front", "--direct", "--phone", "--touch", "--check", "--shots", "--flag"]

static var dir := "user://test_notes"   # FrontCheck uses its own, so checks never mix with real notes
static var _instance: TestNotes

var _button: Flag
var _dim: ColorRect
var _edit: TextEdit
var _save: TagButton
var _title: Label
var _warn: Label
var _shot: Image
var _state := {}
var _was_paused := false
var _full := false


## Called once at launch; the layer lives on the tree's root, so it stays through every change of scene.
static func attach(tree: SceneTree) -> void:
	if _instance != null or not OS.is_debug_build():
		return
	for a: String in OS.get_cmdline_user_args():
		if not (a in PLAY_ARGS or a.begins_with("--safe=") or a.begins_with("--seed=")):
			return
	_instance = TestNotes.new()
	tree.root.add_child.call_deferred(_instance)


func _ready() -> void:
	layer = 90
	DirAccess.make_dir_recursive_absolute(dir)
	process_mode = Node.PROCESS_MODE_ALWAYS
	_button = Flag.new()
	_button.accessibility_name = "Test note"
	_button.pressed.connect(_open)
	add_child(_button)
	_build_box()
	get_tree().root.size_changed.connect(_place)
	_place()


## The top right corner, past the HUD: in the phone's strip beside the safe area, clear of the island, which sits at the
## side's middle. The rounded corner leaves room at this height.
func _place() -> void:
	var w := get_viewport().get_visible_rect().size.x
	_button.position = Vector2(w - 44.0, 2.0)
	_button.size = Vector2(36, 36)


func _build_box() -> void:
	_dim = ColorRect.new()
	_dim.color = Color(0.141, 0.188, 0.172, 0.55)
	_dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_dim.visible = false
	add_child(_dim)
	# At the top, as the phone's keyboard takes the bottom half.
	var p := UI.panel(UI.CREAM, 16, UI.CREAM_EDGE, 4, Vector4(12, 8, 12, 10))
	p.anchor_left = 0.5
	p.anchor_right = 0.5
	p.offset_left = -220
	p.offset_right = 220
	p.offset_top = 6
	_dim.add_child(p)
	var v := CUI.vbox(6)
	var head := CUI.hbox(8)
	_title = UI.label("Test note", "lilita", 16)
	head.add_child(_title)
	_warn = UI.label("", "n800", 11, UI.RED)
	_warn.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	head.add_child(_warn)
	v.add_child(head)
	_edit = TextEdit.new()
	_edit.custom_minimum_size = Vector2(0, 84)
	_edit.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	_edit.accessibility_name = "Note text"
	_edit.add_theme_font_override("font", UI.font("n700"))
	_edit.add_theme_font_size_override("font_size", 14)
	_edit.add_theme_color_override("font_color", UI.INK)
	_edit.add_theme_color_override("caret_color", UI.INK)
	for s in ["normal", "focus"]:
		var sb := CUI.tile_box(CUI.PANEL_LINE, 2, 8, Vector4(8, 6, 8, 6))
		_edit.add_theme_stylebox_override(s, sb)
	_edit.text_changed.connect(_refresh_save)
	v.add_child(_edit)
	var row := CUI.hbox(8)
	var cancel := CUI.big("Cancel", false)
	cancel.pressed.connect(_close)
	row.add_child(cancel)
	row.add_child(CUI.spring())
	_save = CUI.big("Save", true)
	_save.pressed.connect(_store)
	row.add_child(_save)
	v.add_child(row)
	p.add_child(v)


func _open() -> void:
	_shot = get_viewport().get_texture().get_image()
	_state = state()
	_was_paused = get_tree().paused
	get_tree().paused = true
	_edit.text = ""
	_dim.visible = true
	_button.visible = false
	var count := _note_files().size()
	_title.text = "Test note %d" % (count + 1)
	_warn.text = ""
	if count >= MAX_NOTES:
		_warn.text = "Full: collect the notes first"
	elif _bytes() >= MAX_BYTES:
		_warn.text = "Nearly full: no screenshot"
	_full = count >= MAX_NOTES
	_refresh_save()
	_edit.grab_focus()


func _refresh_save() -> void:
	_save.disabled = _edit.text.strip_edges() == "" or _full


func _close() -> void:
	_edit.release_focus()
	if DisplayServer.has_feature(DisplayServer.FEATURE_VIRTUAL_KEYBOARD):
		DisplayServer.virtual_keyboard_hide()
	_dim.visible = false
	_button.visible = true
	get_tree().paused = _was_paused
	_shot = null


func _store() -> void:
	if _save.disabled:
		return
	save_note(_edit.text.strip_edges(), _shot, _state)
	_close()


## Writes one note and its screenshot; returns its name. Never overwrites: each gets a name of its own.
static func save_note(text: String, shot: Image, game_state: Dictionary) -> String:
	DirAccess.make_dir_recursive_absolute(dir)
	var stamp := Time.get_datetime_string_from_system(false, false).replace(":", "").replace("-", "").replace("T", "_")
	var note_name := "note_%s" % stamp
	var k := 1
	while FileAccess.file_exists("%s/%s.json" % [dir, note_name]):
		k += 1
		note_name = "note_%s_%d" % [stamp, k]
	var note := {"text": text, "saved": Time.get_datetime_string_from_system(false, true)}
	note.merge(game_state)
	if shot != null and _bytes() < MAX_BYTES:
		var small: Image = shot.duplicate()
		small.resize(int(small.get_width() * SHOT_SCALE), int(small.get_height() * SHOT_SCALE), Image.INTERPOLATE_BILINEAR)
		if small.save_jpg("%s/%s.jpg" % [dir, note_name], 0.8) == OK:
			note["screenshot"] = note_name + ".jpg"
	var f := FileAccess.open("%s/%s.json" % [dir, note_name], FileAccess.WRITE)
	if f == null:
		push_error("TestNotes: can't write %s" % note_name)
		return ""
	f.store_string(JSON.stringify(note, "\t"))
	f.close()
	print("NOTE saved %s" % note_name)
	return note_name


func state() -> Dictionary:
	var scene := get_tree().current_scene
	var out := {"scene": scene.name if scene else "", "screen": "", "window": str(get_viewport().get_visible_rect().size)}
	if scene is Front:
		var fr := scene as Front
		out.screen = "creator: " + fr.creator.step if fr.creator else "title"
	elif scene is Game:
		var g := scene as Game
		out.screen = "fight" if g.fight.active else ("scene" if g.busy else "map")
		out.tile = str(g.party_tile)
		out.tile_terrain = str(g.map.terrains.get(g.party_tile, ""))
		out.map_id = g.fight.map_id if g.fight.active else ""
		out.seed = g.run.seed_text if g.run else ""
		out.background = g.run.background if g.run else ""
		out.day = g.day
		out.minute = g.minute
		out.gold = g.gold
		out.xp = g.xp
		out.level = g.level
		out.potions = g.potions
		out.hand = g.deck.hand.size()
		out.tiles_placed = g.map.terrains.size()
		out.regions = g.regions.size()
		out.encounters = g.encounters.size()
		out.party = g.party.map(func(m): return {"name": m.name, "hp": m.hp, "max_hp": m.max_hp})
	if Hero.current != null:
		out.hero = {"name": Hero.current.name, "race": Hero.current.race_name, "background": Hero.current.background, "gear": Hero.current.gear}
	return out


func _note_files() -> Array:
	return Array(DirAccess.get_files_at(dir)).filter(func(n): return n.ends_with(".json"))


static func _bytes() -> int:
	var total := 0
	for n in DirAccess.get_files_at(dir):
		var f := FileAccess.open("%s/%s" % [dir, n], FileAccess.READ)
		if f:
			total += f.get_length()
	return total


## The flag: small and faint, with a finger-sized hit area.
class Flag extends Control:
	signal pressed

	func _init() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND

	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
			accept_event()

	func _has_point(point: Vector2) -> bool:
		return UI.finger_rect(size).has_point(point)

	func _draw() -> void:
		var m := size * 0.5
		draw_circle(m, 13, Color(0.141, 0.188, 0.172, 0.45))
		draw_texture_rect(UI.icon(TestNotes.FLAG_ICON, UI.CREAM_LIGHT, 16, 2.6), Rect2(m - Vector2(8, 8), Vector2(16, 16)), false)
