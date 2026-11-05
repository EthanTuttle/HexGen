class_name CreatorBanners
extends Control
## The Class, Race and Background steps: hanging banners across the screen (Creator v4a, v5c, v8a, v11a, v13). The picked
## one widens and the rest narrow to their emblems with their names written down the cloth.
##
## Laid out for the phone's 734 pt (Ethan, Nov 4, 2026), where the picked banner is about 410 pt, not the mockup's 460, so
## blurbs run to two lines. Its crest, name and blurb still stack down the middle where there's room. A race with a row of
## sub-types has none, so there the crest moves beside the name and blurb, and a two-line blurb costs no height. A
## background's starting-place tile is 80 pt, not 108. Banners and gaps tighten a little.

const D = preload("res://scripts/creator/creator_data.gd")

var c: Creator
var _items: Array = []
var _banners: Array[Banner] = []
var _row := Control.new()
var _pop_key := ""
var _step := ""


func _init(creator: Creator) -> void:
	c = creator
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _ready() -> void:
	_row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_row)


func _gap() -> float:
	return 6.0 if size.x < 760.0 else 8.0


func _narrow() -> float:
	if size.x < 760.0:
		return 46.0 if _items.size() > 6 else 54.0
	return 50.0 if _items.size() > 6 else 60.0


func _picked_id() -> String:
	return {"class": c.cls, "race": c.race, "bg": c.bg}.get(c.step, "")


func refresh() -> void:
	_row.position = Vector2(0, 6)
	_row.size = Vector2(size.x, size.y - 6 - 10 - 40)
	for ch in get_children():
		if ch != _row:
			remove_child(ch)
			ch.queue_free()
	var nav := c.nav_row()
	nav.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	nav.offset_top = -40
	add_child(nav)
	_items = _class_items() if c.step == "class" else (_race_items() if c.step == "race" else _bg_items())
	var fresh := _step != c.step
	_step = c.step
	if fresh:
		for b in _banners:
			b.queue_free()
		_banners.clear()
		_pop_key = ""
		for it: Dictionary in _items:
			var b := Banner.new()
			b.id = it.id
			b.accessibility_name = it.n
			b.pressed.connect(_pick.bind(it.id))
			_row.add_child(b)
			_banners.append(b)
	_place_banners(not fresh)
	_buildhang()
	_build_pop()


func _pick(id: String) -> void:
	_pop_key = ""
	match c.step:
		"class":
			if c.cls != id:
				c.cls = id
				c.cb = ""
				c.pc = ""
				c.main = ""
				c.off = ""
				c.arm = ""
		"race":
			if c.race != id:
				var flip := (id == "Human") != c.human()
				c.race = id
				c.sub = ""
				c.elf_spell = ""
				c.rb = []
				c.col = {}
				if flip:
					c.main = ""
					c.off = ""
					c.arm = ""
		"bg":
			c.bg = id
			c.pb = ""
	c.render()


func _widths() -> Array[float]:
	var n := _items.size()
	var avail := size.x - _gap() * (n - 1)
	var picked := _picked_id()
	var out: Array[float] = []
	for it: Dictionary in _items:
		if picked == "":
			out.append(floorf(avail / n))
		elif it.id == picked:
			out.append(avail - _narrow() * (n - 1))
		else:
			out.append(_narrow())
	return out


func _place_banners(animate: bool) -> void:
	var w := _widths()
	var x := 0.0
	var picked := _picked_id()
	for i in _banners.size():
		var b := _banners[i]
		var it: Dictionary = _items[i]
		b.setup(it, picked)
		b.size.y = _row.size.y
		if animate:
			var tw := b.create_tween().set_parallel().set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_CUBIC)
			tw.tween_property(b, "position:x", x, 0.4)
			tw.tween_property(b, "size:x", w[i], 0.4)
		else:
			b.position.x = x
			b.size.x = w[i]
		b.fill(it, picked, w[i], self)
		x += w[i] + _gap()


func _picked_centre() -> float:
	var w := _widths()
	var x := 0.0
	var picked := _picked_id()
	for i in _items.size():
		if _items[i].id == picked:
			return x + w[i] * 0.5
		x += w[i] + _gap()
	return -1.0


# --- Each step's banners (the mockup's classItems, raceItems, bgItems) -----------------

func _class_items() -> Array:
	var out := []
	for k: Dictionary in D.CLS:
		var x: Dictionary = D.CX[k.id]
		var kit := []
		if x.has("kit"):
			for card: Dictionary in x.kit:
				kit.append({"card": true, "n": card.n, "ap": card.ap, "icon": card.icon, "t": card.t, "use": card.get("use", ""), "tag": "Level 1 · Class card"})
		else:
			for _i in 2:
				kit.append({"card": false, "n": "Spell"})
		out.append({"id": k.id, "n": k.id, "bl": x.bl, "icon": D.IC[k.i], "cloth": Color(D.TER[k.t[0]][1]), "dark": D.DARK.has(k.t[0]),
			"chips": k.main, "lines": [["Weapons", x.wt], ["Armour", x.at]], "kit": kit, "locked": not k.id in Creator.PLAYABLE})
	return out


func _race_items() -> Array:
	var out := []
	for r: Dictionary in D.RACES:
		var rx: Dictionary = D.RX[r.id]
		var picked: bool = c.race == r.id
		var sb: Dictionary = c.sub_data() if picked else {}
		var sx: Dictionary = D.SX[sb.id] if not sb.is_empty() else {}
		var cloth: Color = Color(sx.c) if sx.has("c") and r.id != "Tiefling" else Color(D.RCOL[r.id][0])
		var dark: bool = bool(sx.get("dark", 0)) if sx.has("c") and r.id != "Tiefling" else bool(D.RCOL[r.id][1])
		var card = null if r.id == "Tiefling" else sx.get("card", rx.get("card", null))
		if card != null and r.id == "Dragonborn":
			card = card.duplicate()
			card.icon = D.PI[D.DRI[sb.id]] if not sb.is_empty() else D.PI.breath
			if not sb.is_empty():
				card.t = "%s %s" % [card.t, D.ELEM[sb.id]]
		var kit := []
		if card != null:
			kit.append({"card": true, "n": card.n, "ap": card.ap, "icon": card.icon, "t": card.t, "use": card.get("use", ""), "tag": "Racial card"})
		var spells: Array = []
		if not sb.is_empty():
			if sb.id == "High elf":
				spells = ["Glimmerstep", "Faerie Fire", "Lull"]
			elif D.BSP.has(sb.id):
				spells = [D.BSP[sb.id]]
		for nm: String in spells:
			var q: Dictionary = D.RSP[nm]
			var pk: bool = sb.id == "High elf"
			kit.append({"card": true, "n": nm, "ap": q.ap, "icon": D.PI[q.i], "t": q.t, "use": "", "tag": q.tag, "band": "#3E6F8C", "pickable": pk, "chosen": pk and c.elf_spell == nm})
		var lines := []
		if r.id == "Human":
			lines.append(["Boosts", "Any 2 scores"])
		var passives: Array = D.RP.get(r.id, []).duplicate()
		if not sb.is_empty():
			passives.append_array(D.SP2.get(sb.id, []))
		out.append({"id": r.id, "n": c.race_name() if picked and not sb.is_empty() else r.id, "bl": sx.bl if not sb.is_empty() else rx.bl,
			"icon": D.RIC[r.id], "cloth": cloth, "dark": dark, "chips": [] if r.id == "Human" else r.b, "lines": lines, "kit": kit,
			"passives": passives, "subs": r.get("subs", []) if picked else [], "hang_label": "Pick 1 elven spell" if not sb.is_empty() and sb.id == "High elf" else ""})
	return out


func _bg_items() -> Array:
	var out := []
	for b: Dictionary in D.BGS:
		var ter: Color = Color(D.TER[b.t][1])
		out.append({"id": b.id, "n": b.id, "bl": D.BBL[b.id], "icon": D.IC[b.i], "cloth": ter, "dark": D.DARK.has(b.t), "chips": [], "lines": [], "kit": [],
			"is_bg": true, "place": b.hex, "tile": CUI.shade(ter, 0.8)})
	return out


# --- The picked banner's hanging cards and their pop-up ---------------------------------

func _buildhang() -> void:
	var picked := _picked_id()
	if picked == "":
		return
	var it: Dictionary
	for x: Dictionary in _items:
		if x.id == picked:
			it = x
	var kit: Array = it.kit
	var label: String = "Locked" if it.get("locked", false) else it.get("hang_label", "")
	if kit.is_empty() and label == "":
		return
	var cx := _picked_centre()
	var hang := CUI.vbox(0)
	hang.alignment = BoxContainer.ALIGNMENT_END
	var string := ColorRect.new()
	string.color = Color("#6E5A44")
	string.custom_minimum_size = Vector2(2, 12)
	string.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	string.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hang.add_child(string)
	var row := CUI.hbox(6)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	for i in kit.size():
		var k: Dictionary = kit[i]
		var card: Control = _card(k, i) if k.card else _slot(k)
		row.add_child(card)
	hang.add_child(row)
	add_child(hang)
	hang.reset_size()
	var w := hang.get_combined_minimum_size().x
	# The mockup hangs them from the banner's tip, 50 pt below the row, between Back and Next.
	hang.position = Vector2(cx - w * 0.5, size.y - 82 - 4)
	hang.modulate.a = 0.0
	var tw := hang.create_tween()
	tw.tween_property(hang, "modulate:a", 1.0, 0.25).set_delay(0.2)
	if label != "":
		var chip := UI.panel(UI.DARK, 10, Color(0, 0, 0, 0), 0, Vector4(9, 0, 9, 0))
		chip.custom_minimum_size.y = 20
		chip.mouse_filter = Control.MOUSE_FILTER_IGNORE
		chip.add_child(UI.label(label, "n900", 11, UI.CREAM))
		add_child(chip)
		chip.reset_size()
		if kit.is_empty():
			chip.position = Vector2(cx - chip.size.x * 0.5, size.y - 66)
		else:
			chip.position = Vector2(cx + w * 0.5 + 8, size.y - 44)   # the mockup's left side would hit Back at this width


func _card(k: Dictionary, i: int) -> Control:
	var t := CUI.Tap.new(str(k.n))
	t.custom_minimum_size = Vector2(62, 70)
	t.draw.connect(func():
		var open: bool = _pop_key == str(i)
		var border := 3 if open else 2
		var sb := CUI.tile_box(CUI.SEL_RIM, border, 9, Vector4.ZERO)
		sb.shadow_color = Color(0.141, 0.188, 0.172, 0.35)
		sb.shadow_size = 1
		sb.shadow_offset = Vector2(0, 2)
		t.draw_style_box(sb, Rect2(Vector2.ZERO, t.size))
		t.draw_rect(Rect2(2, 2, 58, 5), Color(k.get("band", "#B5532F"))))
	var hx := HexShape.make(18, 21, UI.DARK, UI.DARK, 0).with_text(str(k.ap), 11, UI.CREAM, "n900")
	UI.at(hx, 3, 8)
	t.add_child(hx)
	var ic := UI.icon_rect(k.icon, Color("#9A4A12"), 18, 2.2)
	UI.at(ic, 22, 11)
	t.add_child(ic)
	var name_l := UI.label(k.n, "n900", 11, UI.INK, 0, 1.0)
	name_l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	name_l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	name_l.position = Vector2(2, 32)
	name_l.size = Vector2(58, 34)
	t.add_child(name_l)
	if k.get("chosen", false):
		var tick := CUI.Dot.make(16, Color("#2E7A3E"), CUI.TICK, 10)
		UI.at(tick, 43, 9)
		t.add_child(tick)
		t.position.y = -6
	t.pressed.connect(func():
		if k.get("pickable", false):
			c.elf_spell = k.n
		_pop_key = "" if _pop_key == str(i) else str(i)
		c.render())
	return t


func _slot(k: Dictionary) -> Control:
	var p := PanelContainer.new()
	var sb := CUI.tile_box(UI.HEX_SHADOW, 2, 9, Vector4(3, 0, 3, 0))
	p.add_theme_stylebox_override("panel", sb)
	p.custom_minimum_size = Vector2(44, 70)
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var l := UI.label(k.n, "n900", 11, Color("#6E5A44"))
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	p.add_child(l)
	return p


func toggle_passive(key: String) -> void:
	_pop_key = "" if _pop_key == key else key
	c.render()


func _build_pop() -> void:
	if _pop_key == "":
		return
	var picked := _picked_id()
	var it: Dictionary
	for x: Dictionary in _items:
		if x.id == picked:
			it = x
	if it.is_empty():
		return
	var info := {}
	if _pop_key.begins_with("p:"):
		for p: Dictionary in it.get("passives", []):
			if "p:" + str(p.n) == _pop_key:
				info = {"tag": "Racial passive", "n": p.n, "t": p.t, "ap": "", "use": ""}
	elif _pop_key.is_valid_int() and _pop_key.to_int() < it.kit.size():
		info = it.kit[_pop_key.to_int()]
	if info.is_empty():
		return
	var box := PanelContainer.new()
	var sb := CUI.tile_box(CUI.SEL_RIM, 3, 16, Vector4(10, 8, 10, 10))
	sb.shadow_color = UI.HEX_SHADOW
	sb.shadow_size = 1
	sb.shadow_offset = Vector2(0, 4)
	box.add_theme_stylebox_override("panel", sb)
	box.custom_minimum_size.x = 236
	var v := CUI.vbox(4)
	var top := CUI.hbox(6)
	var names := CUI.vbox(0)
	names.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	names.add_child(UI.label(str(info.tag).to_upper(), "n900", 11, Color("#9A4A12"), 1))
	names.add_child(UI.label(info.n, "lilita", 17, UI.INK, 0, 1.1))
	top.add_child(names)
	var close := HexShape.make(20, 20, Color(0, 0, 0, 0), Color(0, 0, 0, 0), 0).with_icon("M6 6l12 12 M18 6L6 18", CUI.SOFT_INK, 16, 2.6)
	close.clickable = true
	close.accessibility_name = "Close"
	close.pressed.connect(func():
		_pop_key = ""
		c.render())
	top.add_child(close)
	v.add_child(top)
	v.add_child(CUI.wrap(UI.label(info.t, "n700", 12, Color("#33403B"), 0, 1.35), 216))
	var chips := CUI.hbox(6)
	if str(info.get("ap", "")) != "":
		chips.add_child(_pop_chip("Passive" if info.ap == "P" else "%s AP" % info.ap, UI.DARK, UI.CREAM))
	if str(info.get("use", "")) != "":
		chips.add_child(_pop_chip(info.use, Color("#F1E8D8"), UI.INK_MUTED))
	if chips.get_child_count() > 0:
		v.add_child(chips)
	box.add_child(v)
	add_child(box)
	box.reset_size()
	var x := clampf(_picked_centre(), 124.0, size.x - 124.0) - 118.0
	box.position = Vector2(x, size.y - 80 - box.size.y)


func _pop_chip(t: String, bg: Color, ink: Color) -> Control:
	var p := UI.panel(bg, 10, Color(0, 0, 0, 0), 0, Vector4(8, 1, 8, 1))
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.add_child(UI.label(t, "n900", 11, ink))
	return p


## One hanging cloth: rod, edge, cloth and what's written on it.
class Banner extends Control:
	signal pressed
	var id := ""
	var cloth := Color.WHITE
	var edge := Color.WHITE
	var dim := 1.0
	var _content: Control

	func _init() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		resized.connect(queue_redraw)

	func setup(it: Dictionary, picked: String) -> void:
		cloth = it.cloth
		edge = CUI.shade(cloth, 0.72)
		dim = 0.7 if picked != "" and picked != it.id else 1.0
		if it.get("locked", false):
			dim *= 0.75
		queue_redraw()

	func _gui_input(event: InputEvent) -> void:
		if UI.is_tap(self, event):
			pressed.emit()
			accept_event()

	func _draw() -> void:
		var w := size.x
		var h := size.y
		draw_colored_polygon(PackedVector2Array([Vector2(0, 0), Vector2(w, 0), Vector2(w, h - 26), Vector2(w * 0.5, h), Vector2(0, h - 26)]), edge)
		draw_colored_polygon(PackedVector2Array([Vector2(3, 0), Vector2(w - 3, 0), Vector2(w - 3, h - 29), Vector2(w * 0.5, h - 5), Vector2(3, h - 29)]), Color(cloth, dim))
		var rod := StyleBoxFlat.new()
		rod.bg_color = UI.TRAY_EDGE
		rod.set_corner_radius_all(5)
		rod.shadow_color = Color("#6E5A44")
		rod.shadow_size = 1
		rod.shadow_offset = Vector2(0, 1)
		draw_style_box(rod, Rect2(-3, -6, w + 6, 9))

	## Rebuilds what's on the cloth. `w` is the width it's growing or shrinking to, so text doesn't reflow on the way.
	func fill(it: Dictionary, picked: String, w: float, view: CreatorBanners) -> void:
		if _content:
			_content.queue_free()
		_content = Control.new()
		_content.clip_contents = true
		_content.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_content.set_anchors_preset(Control.PRESET_FULL_RECT)
		_content.offset_top = 12
		_content.offset_bottom = -30
		add_child(_content)
		var ink := UI.WHITE_WARM if it.dark else UI.INK
		if picked == it.id:
			var v := _picked(it, w, ink, view)
			v.position = Vector2(10, 0)
			v.size = Vector2(w - 20, 0)
			_content.add_child(v)
			CUI.reveal(v, 0.45)
		else:
			_content.add_child(_folded(it, picked != "", w, ink))

	func _folded(it: Dictionary, narrow: bool, w: float, ink: Color) -> Control:
		var v := CUI.vbox(6)
		v.alignment = BoxContainer.ALIGNMENT_BEGIN
		v.position = Vector2(0, 0)
		v.size = Vector2(w, 0)
		var small := w < 100.0   # seven banners on a phone
		var hw: float = 40.0 if narrow else (48.0 if small else 54.0)
		var hh: float = 46.0 if narrow else (55.0 if small else 62.0)
		var hex := CUI.hex(hw, hh, UI.RIM, 3, it.icon, Color("#33403B"), 20.0 if narrow else 28.0).with_shadow(UI.HEX_SHADOW, 3)
		hex.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		if it.get("locked", false):
			var lock := CUI.Dot.make(18, UI.DARK, Creator.LOCK_ICON, 11)
			UI.at(lock, hw - 14, -2)
			hex.add_child(lock)
		v.add_child(hex)
		if narrow:
			var vt := VerticalText.new()
			vt.setup(it.n, 15, ink)
			vt.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
			v.add_child(vt)
		else:
			var name_l := UI.label(it.n, "lilita", 14 if _is_many(w) else 17, ink, 0, 1.05)
			name_l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			name_l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			name_l.custom_minimum_size.x = w - 8.0
			v.add_child(name_l)
			var bl := UI.label(it.bl, "n800", 11, Color(ink, 0.9), 0, 1.3)
			bl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			bl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			bl.custom_minimum_size.x = w - (12.0 if small else 20.0)
			bl.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
			v.add_child(bl)
		return v

	func _is_many(w: float) -> bool:
		return w < 115.0

	func _picked(it: Dictionary, w: float, ink: Color, view: CreatorBanners) -> Control:
		var soft := Color(ink, 0.78) if it.dark else Color(ink, 0.62)
		var stitch := Color(ink, 0.5) if it.dark else Color(ink, 0.38)
		var inner := w - 20.0
		var side: bool = w < 450.0 and not it.get("subs", []).is_empty()   # the phone's width, with sub-types to fit too
		var v := CUI.vbox(5 if side else 6)
		var head: Control
		var words := CUI.vbox(3)
		var name_l := UI.label(it.n, "lilita", 22, ink, 0, 1.0)
		var bl := UI.label(it.bl, "n800", 12, Color(ink, 0.9), 0, 1.3)
		bl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		var is_bg: bool = it.get("is_bg", false)
		var crest: Control
		if is_bg:
			var tw: float = 80.0 if w < 450.0 else 108.0
			var th: float = 92.0 if w < 450.0 else 124.0
			crest = CUI.hex(tw, th, UI.CREAM_LIGHT, 4, it.icon, UI.WHITE_WARM, 44, it.tile, true, 2.0).with_shadow(Color(0.141, 0.188, 0.172, 0.4), 4)
		else:
			crest = CUI.hex(40, 46, CUI.SEL_RIM, 3, it.icon, Color("#33403B"), 22, UI.CREAM_LIGHT, true).with_shadow(UI.HEX_SHADOW, 3)
		crest.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		if it.get("locked", false):
			var lock := CUI.Dot.make(18, UI.DARK, Creator.LOCK_ICON, 11)
			UI.at(lock, 28, -2)
			crest.add_child(lock)
		if side:
			var row := CUI.hbox(10)
			row.add_child(crest)
			var text_w := inner - crest.custom_minimum_size.x - 10.0
			bl.custom_minimum_size.x = text_w
			name_l.custom_minimum_size.x = text_w
			words.add_child(name_l)
			words.add_child(bl)
			words.size_flags_vertical = Control.SIZE_SHRINK_CENTER
			row.add_child(words)
			head = row
		else:
			var col := CUI.vbox(4)
			col.alignment = BoxContainer.ALIGNMENT_CENTER
			crest.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
			col.add_child(crest)
			name_l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			bl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			bl.custom_minimum_size.x = minf(inner, 440.0)
			bl.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
			col.add_child(name_l)
			col.add_child(bl)
			head = col
		if is_bg:
			var place := CUI.hbox(8)
			place.alignment = BoxContainer.ALIGNMENT_BEGIN if side else BoxContainer.ALIGNMENT_CENTER
			place.add_child(CUI.cap("Starting place", soft))
			place.add_child(UI.label(it.place, "lilita", 16, ink))
			if side:
				words.add_theme_constant_override("separation", 5)
				words.add_child(_stitch(stitch, inner - crest.custom_minimum_size.x - 10.0))
				words.add_child(place)
				v.add_child(head)
			else:
				v.add_child(head)
				v.add_child(_stitch(stitch, inner))
				v.add_child(place)
			return v
		v.add_child(head)
		var subs: Array = it.get("subs", [])
		if not subs.is_empty():
			v.add_child(_sub_row(subs, inner, stitch, ink, view))
		else:
			v.add_child(_stitch(stitch, inner))
		var facts := CUI.hbox(16)
		facts.alignment = BoxContainer.ALIGNMENT_CENTER
		var chips: Array = it.chips
		if not chips.is_empty():
			var ch := CUI.hbox(5)
			for k: String in chips:
				var hx := HexShape.make(30, 34, UI.RIM, UI.CREAM_LIGHT, 2).with_text(k, 11, UI.INK, "n900").with_shadow(Color(0.141, 0.188, 0.172, 0.3), 2)
				ch.add_child(hx)
			ch.size_flags_vertical = Control.SIZE_SHRINK_CENTER
			facts.add_child(ch)
		var lines: Array = it.lines
		if not lines.is_empty():
			var col2 := CUI.vbox(4)
			var line_w := minf(inner - 16.0 - (115.0 if not chips.is_empty() else 0.0) - 64.0, 222.0)
			for l: Array in lines:
				var row2 := CUI.hbox(6)
				var key := CUI.cap(l[0], soft)
				key.custom_minimum_size.x = 58
				key.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
				row2.add_child(key)
				row2.add_child(CUI.wrap(UI.label(l[1], "n800", 11, ink, 0, 1.3), line_w))
				col2.add_child(row2)
			facts.add_child(col2)
		var passives: Array = it.get("passives", [])
		if not passives.is_empty():
			var ph := CUI.hbox(6)
			for p: Dictionary in passives:
				var hx := CUI.hex(34, 39, Color("#3E6F8C"), 3, CreatorData.PI[p.i], Color("#3E6F8C"), 18, UI.CREAM_LIGHT, view._pop_key == "p:" + str(p.n)).with_shadow(Color(0.141, 0.188, 0.172, 0.35), 3)
				hx.clickable = true
				hx.accessibility_name = "%s (racial passive)" % p.n
				hx.pressed.connect(view.toggle_passive.bind("p:" + str(p.n)))
				ph.add_child(hx)
			facts.add_child(ph)
		if facts.get_child_count() > 0:
			v.add_child(facts)
		return v

	func _stitch(col: Color, w: float) -> Control:
		var s := Stitch.new()
		s.col = col
		s.custom_minimum_size = Vector2(w, 8)
		s.mouse_filter = Control.MOUSE_FILTER_IGNORE
		return s

	func _sub_row(subs: Array, inner: float, stitch: Color, ink: Color, view: CreatorBanners) -> Control:
		var holder := Control.new()
		holder.custom_minimum_size = Vector2(inner, 54)
		holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var line := _stitch(stitch, inner)
		line.position = Vector2(0, 14)
		holder.add_child(line)
		var row := CUI.hbox(14)
		row.alignment = BoxContainer.ALIGNMENT_CENTER
		row.size = Vector2(inner, 54)
		var c: Creator = view.c
		var drag: bool = c.race == "Dragonborn"
		for x: Dictionary in subs:
			var d: Dictionary = CreatorData.SX[x.id]
			var sel: bool = c.sub == x.id
			var icon: String = CreatorData.PI[CreatorData.DRI[x.id]] if drag else CreatorData.PI[CreatorData.SUBI[x.id]]
			var face := Color(d.c) if drag else UI.CREAM_LIGHT
			var hink := (UI.WHITE_WARM if d.get("dark", 0) else UI.INK) if drag else Color("#33403B")
			var hx := CUI.hex(32, 37, CUI.SEL_RIM if sel else UI.RIM, 4 if sel else 3, icon, hink, 16, face, sel).with_shadow(Color(0.141, 0.188, 0.172, 0.35), 2)
			var lab := UI.label(d.s, "n900", 11, Color(ink, 1.0 if sel else 0.78))
			var t := CUI.tap_column(str(x.id), [hx, lab], 2)
			t.pressed.connect(func():
				c.sub = x.id
				c.elf_spell = ""
				if x.has("c"):
					c.col["skin"] = x.c
				elif c.race == "Golem":
					c.col.erase("skin")
				view._pop_key = ""
				c.render())
			row.add_child(t)
		holder.add_child(row)
		return holder


## CSS's 2 px dashed line.
class Stitch extends Control:
	var col := Color.WHITE
	func _draw() -> void:
		var x := 0.0
		var y := size.y * 0.5
		while x < size.x:
			draw_line(Vector2(x, y), Vector2(minf(x + 5.0, size.x), y), col, 2.0)
			x += 9.0


## writing-mode: vertical-rl.
class VerticalText extends Control:
	var text := ""
	var px := 15
	var ink := UI.INK

	func setup(t: String, s: int, c: Color) -> void:
		text = t
		px = s
		ink = c
		var w := UI.font("lilita").get_string_size(t, HORIZONTAL_ALIGNMENT_LEFT, -1, s).x
		custom_minimum_size = Vector2(s + 3, w + t.length() * 0.6)
		mouse_filter = Control.MOUSE_FILTER_IGNORE

	func _draw() -> void:
		var f := UI.font("lilita")
		draw_set_transform(Vector2(f.get_descent(px) + 1.0, 0.0), PI * 0.5, Vector2.ONE)
		draw_string(f, Vector2.ZERO, text, HORIZONTAL_ALIGNMENT_LEFT, -1, px, ink)
		draw_set_transform(Vector2.ZERO)
