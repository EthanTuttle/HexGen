class_name SavePopups
extends Control
## The pop-ups saving uses, in Title v11's Load pop-up style (mockups/final-screens/TitleScreen.dc.html; design/07 ->
## Title screen): a cream card over a dim scrim with a title and a close hex. The pause menu (Save, Load, Settings, Quit to
## title; design/06 -> Saving), the save slots, Load (heroes, then their autosaves and save slots) and a confirm.
## One pop-up shows at a time; each replaces the last. Data comes in as plain dictionaries (Saves' rows).

signal closed
signal deleted                    # a hero's saves were deleted from Load

const MENU_ICON := "M4 7h16 M4 12h16 M4 17h16"
const TRASH_ICON := "M4 7h16 M9 7V4h6v3 M6 7l1 13h10l1-13 M10 11v6 M14 11v6"
const CLOSE_ICON := "M6 6l12 12M18 6L6 18"
const MUTED := Color("#5A6862")
const PICKED := Color("#FFE9A8")

var _scrim := ColorRect.new()
var _card: PanelContainer


func _init() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_scrim.color = Color(0.141, 0.188, 0.172, 0.42)
	_scrim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_scrim.mouse_filter = Control.MOUSE_FILTER_STOP
	_scrim.visible = false
	add_child(_scrim)


func close() -> void:
	if _card:
		_card.queue_free()
		_card = null
	_scrim.visible = false
	closed.emit()


## A fresh card of width w with a title; returns its body.
func _open(title: String, w: float) -> VBoxContainer:
	if _card:
		_card.queue_free()
	_scrim.visible = true
	var box := UI.box(UI.CREAM_LIGHT, 18, Color(0, 0, 0, 0), 0, Vector4(18, 16, 18, 18))
	box.shadow_color = UI.RIM
	box.shadow_offset = Vector2(0, 6)
	box.shadow_size = 0
	_card = PanelContainer.new()
	_card.add_theme_stylebox_override("panel", box)
	_card.custom_minimum_size.x = w
	_card.anchor_left = 0.5
	_card.anchor_right = 0.5
	_card.anchor_top = 0.5
	_card.anchor_bottom = 0.5
	_card.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_card.grow_vertical = Control.GROW_DIRECTION_BOTH
	add_child(_card)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 10)
	_card.add_child(col)
	var head := HBoxContainer.new()
	head.add_child(UI.label(title, "lilita", 22))
	var gap := Control.new()
	gap.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(gap)
	var x := HexShape.make(34, 38, UI.SAND, UI.SAND, 0).with_icon(CLOSE_ICON, Color("#33403B"), 16, 3.0)
	x.clickable = true
	x.accessibility_name = "Close"
	x.pressed.connect(close)
	head.add_child(x)
	col.add_child(head)
	var body := VBoxContainer.new()
	body.add_theme_constant_override("separation", 6)
	col.add_child(body)
	return body


# --- Pause menu ----------------------------------------------------------------

## items: [[label, callable], ...]
func open_menu(items: Array) -> void:
	var body := _open("Menu", 270)
	body.add_theme_constant_override("separation", 10)
	for it: Array in items:
		var b := TagButton.make(it[0], 234, 40, 16)
		b.cut = 13.0
		b.bg = UI.CREAM
		b.ink = Color("#33403B")
		b.shadow = UI.HEX_SHADOW
		b.drop = 3.0
		b.accessibility_name = it[0]
		b.pressed.connect(it[1])
		var c := CenterContainer.new()
		c.add_child(b)
		body.add_child(c)


# --- Save slots ------------------------------------------------------------------

## slots: three rows, each {} for an empty slot or {place, time}. pick(i) is called with the slot's index.
func open_save(slots: Array, pick: Callable) -> void:
	var body := _open("Save", 330)
	for i in slots.size():
		var s: Dictionary = slots[i]
		body.add_child(_row("Slot %d" % (i + 1), "Empty" if s.is_empty() else "%s · %s" % [s.place, s.time], s.is_empty(), pick.bind(i), true))


# --- Confirm ----------------------------------------------------------------------

## A question that stops a mistake (design/07 -> Screen text -> Sentences that stay), with its action and Cancel.
func open_confirm(title: String, action: String, yes: Callable, danger := false, no := Callable()) -> void:
	var body := _open(title, 330)
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 12)
	var cancel := TagButton.make("Cancel", 136, 40, 16)
	cancel.cut = 13.0
	cancel.bg = UI.CREAM
	cancel.ink = Color("#33403B")
	cancel.shadow = UI.HEX_SHADOW
	cancel.drop = 3.0
	cancel.pressed.connect(no if no.is_valid() else close)
	row.add_child(cancel)
	var ok := TagButton.make(action, 136, 40, 16)
	ok.cut = 13.0
	if danger:
		ok.bg = UI.RED
		ok.shadow = UI.RED_EDGE
	ok.pressed.connect(yes)
	row.add_child(ok)
	body.add_child(row)


# --- Load -------------------------------------------------------------------------

## heroes: [{id, name, subtitle, time, initial, color, autos: [{place, time}], slots: [{} or {place, time}] x3}], most recent
## first. load(hero_index, kind, i) with kind "auto" or "slot"; delete(hero_index) asks first (open_confirm).
func open_load(heroes: Array, picked: int, load: Callable, delete: Callable) -> void:
	var body := _open("Load", 640)
	var cols := HBoxContainer.new()
	cols.add_theme_constant_override("separation", 14)
	body.add_child(cols)
	var left := VBoxContainer.new()
	left.custom_minimum_size.x = 178
	left.add_theme_constant_override("separation", 6)
	left.add_child(_cap("Heroes"))
	var list := VBoxContainer.new()
	list.add_theme_constant_override("separation", 6)
	left.add_child(_scroll(list, 196))
	for k in heroes.size():
		list.add_child(_hero_row(heroes[k], k == picked, func(): open_load(heroes, k, load, delete)))
	cols.add_child(left)
	if heroes.is_empty():
		return
	var bin := TagButton.make("Delete", 110, 32, 14)   # the picked hero's saves; it asks first
	bin.cut = 11.0
	bin.bg = UI.SAND
	bin.ink = UI.RED
	bin.shadow = UI.RIM
	bin.drop = 2.0
	bin.icon = UI.icon(TRASH_ICON, UI.RED, 16, 2.4)
	bin.accessibility_name = "Delete"
	bin.pressed.connect(delete.bind(picked))
	left.add_child(bin)
	var h: Dictionary = heroes[picked]
	var autos := VBoxContainer.new()
	autos.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	autos.add_theme_constant_override("separation", 6)
	autos.add_child(_cap("Autosaves"))
	var alist := VBoxContainer.new()
	alist.add_theme_constant_override("separation", 6)
	autos.add_child(_scroll(alist, 236))
	for i in h.autos.size():
		alist.add_child(_row(h.autos[i].place, h.autos[i].time, h.autos[i].get("broken", false), load.bind(picked, "auto", i)))
	cols.add_child(autos)
	var slots := VBoxContainer.new()
	slots.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	slots.add_theme_constant_override("separation", 6)
	slots.add_child(_cap("Save slots"))
	for i in h.slots.size():
		var s: Dictionary = h.slots[i]
		var row := _row("Slot %d" % (i + 1), "Empty" if s.is_empty() else "%s · %s" % [s.place, s.time], s.is_empty() or s.get("broken", false),
				load.bind(picked, "slot", i))
		slots.add_child(row)
	cols.add_child(slots)


## Load with the saves on disk: tapping a row opens that save in the game scene; Delete asks, then removes the picked hero's
## saves. A save that won't read dims its row.
func show_load(picked := 0, broken := {}) -> void:
	var heroes := Saves.heroes()
	for k in heroes.size():
		for kind in ["autos", "slots"]:
			for i in heroes[k][kind].size():
				if broken.has([heroes[k].id, kind, i]):
					heroes[k][kind][i].broken = true
	var load := func(h: int, kind: String, i: int):
		var rows: Array = heroes[h].autos if kind == "auto" else heroes[h].slots
		var data := Saves.read(heroes[h].id, rows[i].file)
		if data.is_empty():
			broken[[heroes[h].id, kind + "s", i]] = true
			show_load(h, broken)
			return
		Saves.play(get_tree(), data)
	var delete := func(h: int):
		open_confirm("Delete %s's saves?" % heroes[h].name, "Delete", func():
			Saves.delete_hero(heroes[h].id)
			deleted.emit()
			show_load(0, broken), true, func(): show_load(h, broken))
	open_load(heroes, mini(picked, maxi(heroes.size() - 1, 0)), load, delete)


func _cap(text: String) -> Label:
	return UI.label(text.to_upper(), "n900", 10, MUTED, 1)


func _scroll(inner: Control, most: float) -> ScrollContainer:
	var s := ScrollContainer.new()
	s.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	s.custom_minimum_size.y = most
	inner.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	s.add_child(inner)
	return s


## A save row: two lines, dimmed (and not tappable) when empty or unreadable.
## dim: pale, and not tappable unless live (Save's empty slots look pale, as mocked up, but take a save).
func _row(top: String, sub: String, dim: bool, tap: Callable, live := false) -> Control:
	var r := _Tap.new()
	r.add_theme_stylebox_override("panel", UI.box(UI.CREAM, 10, Color(0, 0, 0, 0), 0, Vector4(10, 7, 10, 7)))
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 0)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(UI.label(top, "n900", 12))
	v.add_child(UI.label(sub, "n700", 10, MUTED))
	r.add_child(v)
	if dim:
		r.modulate.a = 0.6
	if live or not dim:
		r.tapped.connect(tap)
	return r


func _hero_row(h: Dictionary, on: bool, pick: Callable) -> Control:
	var r := _Tap.new()
	var box := UI.box(PICKED if on else UI.CREAM, 12, Color(0, 0, 0, 0), 0, Vector4(8, 6, 8, 6))
	if on:   # CSS: inset 0 0 0 2px #B5532F
		box.set_border_width_all(2)
		box.border_color = UI.ORANGE
	r.add_theme_stylebox_override("panel", box)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 9)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var hex := HexShape.make(32, 37, Color(h.color), Color(h.color), 0).with_text(h.initial, 15, UI.CREAM_LIGHT)
	var cc := CenterContainer.new()
	cc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	cc.add_child(hex)
	row.add_child(cc)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 0)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for t in [[h.name, "n900", 12, UI.INK], [h.subtitle, "n700", 10, MUTED], [h.time, "n700", 10, MUTED]]:
		var l := UI.label(t[0], t[1], t[2], t[3])
		l.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		l.clip_text = true
		v.add_child(l)
	row.add_child(v)
	r.add_child(row)
	if not on:
		r.tapped.connect(pick)
	return r


## A panel that reports a tap (UI.is_tap), letting drags through to a scroll.
class _Tap extends PanelContainer:
	signal tapped

	func _init() -> void:
		mouse_filter = Control.MOUSE_FILTER_PASS
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND

	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			tapped.emit()
