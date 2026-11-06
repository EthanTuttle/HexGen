class_name CreatorGear
extends Control
## The Gear step (Creator v18c, v19c, v20): the slots on the hero card, 5 item hexes per row, a details pane. Picking only
## shows an item; Choose flies its hex to the slot. Back and Next walk the slots. Armour shows the mockup's [Item stats].

const D = preload("res://scripts/creator/creator_data.gd")

var c: Creator
var slot := "main"
var _shown_slot := ""                   # the slot whose list was last built
var _focus := ""
var _land := ""
var _hexes := {}                       # item id -> its hex
var _slots := {}                       # slot -> its hex


func _init(creator: Creator) -> void:
	c = creator
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _items() -> Array:
	match slot:
		"main": return c.allowed_weapons()
		"off": return c.off_options()
	var armour := [{"id": "none", "n": "No armour"}]
	for a: String in (["Light", "Medium", "Heavy"] if c.human() else c.cls_data().a):
		armour.append({"id": a, "n": a + " armour"})
	return armour


func _icon_of(o: Dictionary) -> String:
	if slot == "arm":
		return D.IC.none if o.id == "none" else D.IC.armour
	return D.IC.get(o.get("i", "none"), D.IC.none)


func _current() -> String:
	return c.main if slot == "main" else (c.off if slot == "off" else c.arm)


func _off_crossed() -> bool:
	return c.main != "" and c.off_options().is_empty()


func _restore_scroll(y: int) -> void:
	CUI.keep_scroll(self, y)


func _order() -> Array[String]:
	var out: Array[String] = ["main"]
	if c.main != "" and not _off_crossed():
		out.append("off")
	out.append("arm")
	return out


func refresh() -> void:
	if slot == "off" and (_off_crossed() or c.main == ""):
		slot = "main"
	var y := CUI.scroll_of(self) if _shown_slot == slot else 0   # a tap in the list keeps its place (phone notes, Nov 5)
	_shown_slot = slot
	call_deferred("_restore_scroll", y)
	for ch in get_children():
		remove_child(ch)
		ch.queue_free()
	_hexes.clear()
	_slots.clear()
	var h := CUI.hbox(14 if size.x >= 760.0 else 10)
	h.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(h)
	h.add_child(_card())
	var panel := CUI.panel(Vector4(12, 12, 12, 12))
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var row := CUI.hbox(10)
	row.add_child(_grid())
	row.add_child(_details())
	panel.add_child(row)
	h.add_child(panel)
	_land = ""


func _card() -> Control:
	var pad := Vector4(10, 14, 10, 12)
	var card := CUI.panel(pad)
	card.custom_minimum_size.x = 196.0 if size.x >= 760.0 else 180.0
	var v := CUI.vbox(6)
	var who := CreatorTraining.who_card(c, 64, 74, 32, 16, Vector4(18, 0, 18, 0))
	who.add_theme_constant_override("separation", 6)
	v.add_child(who)
	v.add_child(CUI.spring())
	var row := CUI.hbox(0)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	var mw := c.weapon(c.main)
	var off_item := {}
	for o: Dictionary in c.off_options():
		if o.id == c.off:
			off_item = o
	var off_icon: String = D.IC.none if off_item.is_empty() or off_item.id == "none" else D.IC[off_item.i]
	var off_note := "Pick a weapon first" if c.main == "" else ("Worn as a pair" if str(mw.get("h", "")) == "f" else "Both hands")
	row.add_child(_slot_hex("main", "Main hand", mw.get("n", ""), D.IC[mw.i] if not mw.is_empty() else "", false, ""))
	var empty_hand: bool = not off_item.is_empty() and off_item.id == "none"
	row.add_child(_slot_hex("off", "Offhand", "Empty hand" if empty_hand else off_item.get("n", ""), off_icon if not off_item.is_empty() else "", c.main == "" or _off_crossed(), off_note))
	var arm_name := "" if c.arm == "" else ("No armour" if c.arm == "none" else c.arm + " armour")
	row.add_child(_slot_hex("arm", "Armour", arm_name, (D.IC.none if c.arm == "none" else D.IC.armour) if c.arm != "" else "", false, ""))
	v.add_child(row)
	card.add_child(v)
	return card


func _slot_hex(k: String, lab: String, item_name: String, icon: String, crossed: bool, note: String) -> Control:
	var act := slot == k and not crossed
	var filled := item_name != ""
	var rim := UI.GOLD if act else (CUI.SEL_RIM if filled else UI.RIM)
	var hx := CUI.hex(48, 55, rim, 3, "", Color("#33403B"), 22, UI.SAND if crossed else UI.CREAM_LIGHT, act).with_shadow(UI.HEX_SHADOW, 3)
	if filled:
		hx.with_icon(icon, Color("#33403B"), 22)
	elif crossed:
		hx.with_icon("M6 6l12 12 M18 6L6 18", Color("#8A7D66"), 20)
	else:
		hx.with_icon("M12 6v12 M6 12h12", Color("#8A7D66"), 20)
	_slots[k] = hx
	if _land == k:
		hx.pivot_offset = Vector2(24, 27)
		hx.scale = Vector2(0.3, 0.3)
		var tw := hx.create_tween()
		tw.tween_interval(0.44)
		tw.tween_property(hx, "scale", Vector2(1.15, 1.15), 0.22)
		tw.tween_property(hx, "scale", Vector2.ONE, 0.1)
	var name_l := UI.label(note if crossed else (item_name if filled else "Empty"), "n700", 11, CUI.CAP_INK, 0, 1.15)
	name_l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	name_l.autowrap_mode = TextServer.AUTOWRAP_WORD
	name_l.custom_minimum_size = Vector2(56, 26)
	var t := CUI.tap_column(lab, [hx, UI.label(lab, "n900", 11, Color("#33403B")), name_l])
	t.modulate.a = 0.6 if crossed else 1.0
	t.custom_minimum_size.x = 58
	if not crossed and (k == "main" or c.main != ""):
		t.pressed.connect(func():
			slot = k
			_focus = ""
			c.render())
	return t


func _grid() -> Control:
	var v := CUI.vbox(8)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var head := CUI.hbox(7)
	head.add_child(UI.label({"main": "Main hand", "off": "Offhand", "arm": "Armour"}[slot], "lilita", 16))
	head.add_child(CUI.mark(_current() != ""))
	var sub := UI.label(_slot_note(), "n800", 11, CUI.CAP_INK)
	sub.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	sub.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sub.clip_text = true
	sub.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	sub.custom_minimum_size.x = 30
	head.add_child(sub)
	v.add_child(head)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_SHOW_NEVER
	var grid := GridContainer.new()
	grid.columns = 5
	grid.add_theme_constant_override("h_separation", 0)
	grid.add_theme_constant_override("v_separation", 8)
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var items: Array = _items()
	if slot == "main":   # in the mockup's groups
		var ordered := []
		for g: Array in D.WG:
			for w: Dictionary in items:
				if w.id in g[1]:
					ordered.append(w)
		items = ordered
	var fid := _focus_id(items)
	for o: Dictionary in items:
		grid.add_child(_item(o, fid))
	scroll.add_child(grid)
	v.add_child(scroll)
	return v


func _slot_note() -> String:
	var k := c.cls_data()
	match slot:
		"main":
			return "Any basic weapon (Versatile)" if c.human() else ("Any basic weapon" if str(k.w) == "all" else k.id + " weapons")
		"off":
			var mw := c.weapon(c.main)
			return "A shield, or nothing: two-handed %s" % str(mw.n).to_lower() if str(mw.h) == "v" else "A shield, a second one-handed weapon or nothing"
	return "Any basic armour (Versatile)" if c.human() else k.id + " armour"


func _focus_id(items: Array) -> String:
	if _focus != "":
		return _focus
	if _current() != "":
		return _current()
	return items[0].id if not items.is_empty() else ""


func _item(o: Dictionary, fid: String) -> Control:
	var sel: bool = _current() == o.id
	var foc: bool = fid == o.id
	var rim := CUI.FOCUS_RIM if foc else (CUI.SEL_RIM if sel else UI.RIM)
	var hx := CUI.hex(48, 55, rim, 3, _icon_of(o), Color("#33403B"), 22, UI.CREAM_LIGHT, sel).with_shadow(UI.HEX_SHADOW, 3)
	if sel:
		var tick := CUI.Dot.make(16, CUI.SEL_RIM, CUI.TICK, 10)
		UI.at(tick, 37, -3)
		hx.add_child(tick)
	_hexes[o.id] = hx
	var lab: String = ("None" if o.id == "none" else o.id) if slot == "arm" else o.n
	var l := UI.label(lab, "n800", 11, Color("#33403B"), 0, 1.1)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.autowrap_mode = TextServer.AUTOWRAP_WORD
	l.custom_minimum_size.x = 58
	var t := CUI.tap_column(str(o.n), [hx, l])
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	t.pressed.connect(func():
		_focus = o.id
		c.render())
	return t


func _details() -> Control:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", CUI.tile_box(CUI.PANEL_LINE, 2.5, 14, Vector4(12, 10, 12, 12)))
	var w := 214.0 if size.x >= 760.0 else 186.0
	p.custom_minimum_size.x = w
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var inner := w - 24.0
	var v := CUI.vbox(6)
	var items: Array = _items()
	var fid := _focus_id(items)
	var det: Dictionary = {}
	for o: Dictionary in items:
		if o.id == fid:
			det = o
	if not det.is_empty():
		v.add_child(UI.label({"main": "MAIN HAND", "off": "OFFHAND", "arm": "ARMOUR"}[slot], "n900", 11, Color("#3E5A70"), 1))
		var title := CUI.hbox(8)
		title.add_child(UI.icon_rect(_icon_of(det), Color("#33403B"), 20))
		title.add_child(UI.label(det.n, "lilita", 19, UI.INK, 0, 1.05))
		v.add_child(title)
		var mod: Array = D.WM.get(det.id, []) if slot != "arm" else []
		var hands := ""
		if slot == "main":
			hands = D.HL[str(det.h)]
		elif slot == "off" and str(det.get("h", 0)) == "1":
			hands = "One-handed"
		if hands != "" or not mod.is_empty():
			var chips := CUI.hbox(5)
			if hands != "":
				chips.add_child(_chip(hands, Color("#EFE4D0"), CUI.SOFT_INK))
			if not mod.is_empty():
				chips.add_child(_chip(mod[0], Color("#3E6F8C"), UI.WHITE_WARM))
			v.add_child(chips)
		if slot != "arm":
			for card: Array in D.WC.get(det.id, []):
				v.add_child(_action_card(card, inner))
		if not mod.is_empty():
			v.add_child(CUI.wrap(UI.label("%s: %s" % [mod[0], mod[1]], "n700", 11, CUI.SOFT_INK, 0, 1.25), inner))
		var note := _note_of(det)
		if note != "":
			v.add_child(CUI.wrap(UI.label(note, "n700", 11, CUI.CAP_INK, 0, 1.25), inner))
		v.add_child(CUI.spring())
		if _current() == det.id:
			v.add_child(CreatorTraining.chosen())
		else:
			var b := CUI.choose_button("Choose", inner)
			b.accessibility_name = "Choose " + str(det.n)
			b.pressed.connect(_choose.bind(det))
			v.add_child(b)
	else:
		v.add_child(CUI.spring())
	v.add_child(_nav())
	p.add_child(v)
	return p


func _chip(t: String, bg: Color, ink: Color) -> Control:
	var p := UI.panel(bg, 9, Color(0, 0, 0, 0), 0, Vector4(9, 0, 9, 0))
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.add_child(UI.label(t, "n800", 11, ink))
	return p


func _note_of(o: Dictionary) -> String:
	if slot == "arm":
		return "" if o.id == "none" else "[Item stats]"
	if slot == "off":
		if o.id == "none":
			var mw := c.weapon(c.main)
			return "The %s is held in both hands for more damage" % str(mw.n).to_lower() if str(mw.h) == "v" else ""
		if str(o.get("h", 0)) == "1":
			return "Free offhand attack once per turn"
	return ""


func _action_card(card: Array, w: float) -> Control:
	var p := PanelContainer.new()
	var sb := CUI.tile_box(Color("#D9CDB6"), 1.5, 8, Vector4(30, 4, 6, 4))
	p.add_theme_stylebox_override("panel", sb)
	p.custom_minimum_size = Vector2(w, 40)
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var v := CUI.vbox(0)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_child(UI.label(card[0], "n900", 12, Color("#3E5A70"), 0, 1.1))
	v.add_child(CUI.wrap(UI.label(card[2], "n700", 11, CUI.SOFT_INK, 0, 1.2), w - 38.0))
	p.add_child(v)
	var band := ColorRect.new()
	band.color = Color("#5F7F99")
	band.mouse_filter = Control.MOUSE_FILTER_IGNORE
	band.position = Vector2(0, 2)
	band.size = Vector2(4, 36)
	var holder := Control.new()
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.custom_minimum_size = p.custom_minimum_size
	holder.add_child(p)
	holder.add_child(band)
	var ap := HexShape.make(17, 20, UI.DARK, UI.DARK, 0).with_text(str(card[1]), 11, UI.CREAM, "n900")
	UI.at(ap, 8, 10)
	holder.add_child(ap)
	p.resized.connect(func(): holder.custom_minimum_size = p.size)
	return holder


func _nav() -> Control:
	var h := CUI.hbox(6)
	var order := _order()
	var i := order.find(slot)
	var back := CUI.big("Back", false, 16)
	back.bg = UI.SAND   # the mockup's cream vanishes on this cream pane
	back.pressed.connect(func():
		if i > 0:
			slot = order[i - 1]
			_focus = ""
			c.render()
		else:
			c.go_back())
	h.add_child(back)
	h.add_child(CUI.spring())
	var next_empty := ""
	if _current() != "":
		for k: String in order:
			if k != slot and not _filled(k):
				next_empty = k
				break
	if next_empty != "":
		var lab: String = {"main": "Main hand", "off": "Offhand", "arm": "Armour"}[next_empty]
		var go := CUI.big("Next: " + lab, true, 8)
		go.text_size = 13
		go.pressed.connect(func():
			slot = next_empty
			_focus = ""
			c.render())
		h.add_child(go)
	else:
		var next := CUI.big("Next", true, 16)
		next.disabled = not c.done("gear")
		next.pressed.connect(c.go_next)
		h.add_child(next)
	return h


func _filled(k: String) -> bool:
	return (c.main if k == "main" else (c.off if k == "off" else c.arm)) != ""


func _choose(o: Dictionary) -> void:
	var from: Control = _hexes.get(o.id)
	var to: Control = _slots.get(slot)
	var start: Vector2 = from.global_position if from else Vector2.ZERO
	var end: Vector2 = to.global_position if to else Vector2.ZERO
	var icon := _icon_of(o)
	var flies: bool = from != null and to != null and o.id != "none"
	match slot:
		"main":
			if c.main != o.id:
				c.off = ""
			c.main = o.id
		"off": c.off = o.id
		"arm": c.arm = o.id
	_focus = o.id
	if flies:
		_land = slot
	c.render()
	if flies:
		_fly(icon, start, end)


## v20: the item's hex flies into its slot with a gold glow, and the slot's icon pops in as it lands.
func _fly(icon: String, from: Vector2, to: Vector2) -> void:
	var hx := CUI.hex(48, 55, CUI.SEL_RIM, 3, icon, Color("#33403B"), 22, UI.CREAM_LIGHT, true)
	hx.top_level = true
	hx.global_position = from
	c.add_child(hx)
	var tw := hx.create_tween()
	tw.tween_property(hx, "global_position", to, 0.44).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN_OUT)
	tw.tween_callback(hx.queue_free)
