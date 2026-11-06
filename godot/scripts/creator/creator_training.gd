class_name CreatorTraining
extends Control
## The Scores and Skills steps, in the level-up look (Creator v15a): a who-you-are card on the left, then the six coin
## tiles with their +1 chips, or the proficiency list and its details.

const D = preload("res://scripts/creator/creator_data.gd")
const RACE_C := Color("#2E7A6E")
const CLASS_C := Color("#B5532F")

var c: Creator
var _shown := ""                       # the step last built, so a rebuild within it doesn't fade in again
var _focus := ""                       # "bg:Lore": the proficiency being looked at


func _init(creator: Creator) -> void:
	c = creator
	mouse_filter = Control.MOUSE_FILTER_IGNORE


static func who_card(cr: Creator, hex_w: float, hex_h: float, icon: float, title_px: int, pad: Vector4) -> VBoxContainer:
	var v := CUI.vbox(8)
	v.alignment = BoxContainer.ALIGNMENT_BEGIN
	var k := cr.cls_data()
	var hx := CUI.hex(hex_w, hex_h, UI.RIM, 4, D.IC[k.i], UI.INK, icon, UI.GOLD, false, 2.0).with_shadow(UI.HEX_SHADOW, 4)
	hx.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(hx)
	var title := UI.label("%s %s" % [cr.race_name(), cr.cls], "lilita", title_px, UI.INK, 0, 1.1)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	title.custom_minimum_size.x = 196.0 - pad.x - pad.z
	v.add_child(title)
	var b := cr.bg_data()
	var sub := UI.label("%s · %s" % [b.id, b.hex], "n700", 11, CUI.SOFT_INK, 0, 1.3)
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	sub.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	sub.custom_minimum_size.x = 196.0 - pad.x - pad.z
	v.add_child(sub)
	return v


## Rebuilt on every change; it fades in and the list starts at the top only when the step is new, so a tap doesn't flash
## or jump (Ethan's phone notes, Nov 5, 2026).
func refresh() -> void:
	var same := _shown == c.step
	var y := CUI.scroll_of(self) if same else 0
	_shown = c.step
	for ch in get_children():
		remove_child(ch)
		ch.queue_free()
	var h := CUI.hbox(14 if size.x >= 760.0 else 10)
	h.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(h)
	var pad := Vector4(12, 18, 12, 14)
	var card := CUI.panel(pad)
	card.custom_minimum_size.x = 196
	card.add_child(CreatorTraining.who_card(c, 92, 106, 44, 18, pad))
	h.add_child(card)
	var panel := CUI.panel(Vector4(14, 12, 14, 12))
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(panel)
	if c.step == "scores":
		panel.add_child(_scores())
	else:
		panel.add_child(_skills())
	if not same:
		CUI.reveal(h)
	CUI.keep_scroll(self, y)


# --- Scores ------------------------------------------------------------------------

func _race_list() -> Array:
	var r := c.race_data()
	return D.AB if c.human() else r.b


func _scores() -> Control:
	var v := CUI.vbox(8)
	var head := CUI.hbox(12)
	head.add_child(_head_part("%s +1s" % c.race, c.rb.size() == 2, "%d / 2 · %s" % [c.rb.size(), "Any 2 scores" if c.human() else " · ".join(_race_list())]))
	head.add_child(CUI.spring())
	head.add_child(_head_part("%s +1" % c.cls, c.cb != "", "%d / 1 · %s" % [1 if c.cb != "" else 0, " · ".join(c.cls_data().main)]))
	v.add_child(head)
	var grid := GridContainer.new()
	grid.columns = 3
	grid.add_theme_constant_override("h_separation", 8)
	grid.add_theme_constant_override("v_separation", 8)
	grid.size_flags_vertical = Control.SIZE_EXPAND_FILL
	for k: String in D.AB:
		grid.add_child(_tile(k))
	v.add_child(grid)
	v.add_child(c.nav_row())
	return v


func _head_part(title: String, is_done: bool, note: String) -> Control:
	var h := CUI.hbox(7)
	h.add_child(UI.label(title, "lilita", 16))
	h.add_child(CUI.mark(is_done))
	var n := UI.label(note, "n800", 11, CUI.CAP_INK)
	n.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(n)
	return h


func _tile(k: String) -> Control:
	var r_on: bool = k in c.rb
	var c_on: bool = c.cb == k
	var r_can: bool = k in _race_list()
	var c_can: bool = k in c.cls_data().main
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", CUI.tile_box(UI.GOLD if r_on or c_on else CUI.PANEL_LINE, 2.5, 12, Vector4(10, 7, 10, 6)))
	p.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	p.size_flags_vertical = Control.SIZE_EXPAND_FILL
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var v := CUI.vbox(4)
	var top := CUI.hbox(6)
	var names := CUI.vbox(0)
	names.add_child(UI.label(k, "n900", 11, UI.INK, 1))
	names.add_child(UI.label(str(c.scores()[k]), "lilita", 26, UI.INK, 0, 1.0))
	top.add_child(names)
	top.add_child(CUI.spring())
	var coins := CUI.hbox(3)
	coins.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	coins.add_child(_coin(Color(0, 0, 0, 0)))
	if r_on:
		coins.add_child(_coin(RACE_C))
	if c_on:
		coins.add_child(_coin(CLASS_C))
	top.add_child(coins)
	v.add_child(top)
	v.add_child(CUI.spring())
	var chips := CUI.hbox(5)
	chips.alignment = BoxContainer.ALIGNMENT_CENTER
	if r_can:
		chips.add_child(_chip("Race +1" if r_on else "+1 Race", r_on, RACE_C, "Race +1 %s" % k, _toggle_race.bind(k)))
	if c_can:
		chips.add_child(_chip("Class +1" if c_on else "+1 Class", c_on, CLASS_C, "Class +1 %s" % k, _toggle_class.bind(k)))
	v.add_child(chips)
	p.add_child(v)
	return p


func _coin(ring: Color) -> Control:
	var d := Coin.new()
	d.ring = ring
	d.custom_minimum_size = Vector2(14, 14)
	d.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return d


func _chip(t: String, on: bool, col: Color, what: String, act: Callable) -> Control:
	var b := CUI.Tap.new(what)
	b.custom_minimum_size = Vector2(UI.font("n900").get_string_size(t, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x + 18.0, 22)
	b.draw.connect(func():
		var sb := UI.box(col if on else UI.CREAM_LIGHT, 11)
		sb.set_border_width_all(2)
		sb.border_color = col
		b.draw_style_box(sb, Rect2(Vector2.ZERO, b.size)))
	var l := UI.label(t, "n900", 11, UI.WHITE_WARM if on else col)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.set_anchors_preset(Control.PRESET_FULL_RECT)
	b.add_child(l)
	b.pressed.connect(act)
	return b


func _toggle_race(k: String) -> void:
	if k in c.rb:
		c.rb.erase(k)
	else:
		c.rb.append(k)
		if c.rb.size() > 2:
			c.rb = c.rb.slice(-2)
	c.render()


func _toggle_class(k: String) -> void:
	c.cb = "" if c.cb == k else k
	c.render()


# --- Skills ------------------------------------------------------------------------

func _skills() -> Control:
	var h := CUI.hbox(12)
	var b := c.bg_data()
	var k := c.cls_data()
	if _focus == "":
		_focus = "bg:" + str(b.pr[0]) if c.pb == "" else ("cls:" + str(k.pr[0]) if c.pc == "" else "bg:" + c.pb)
	var scroll := ScrollContainer.new()
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_SHOW_NEVER
	var list := CUI.vbox(6)
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_child(_group(b.id, c.pb != ""))
	for p: String in b.pr:
		list.add_child(_row(p, "bg"))
	list.add_child(_group("%s · %s" % [k.id, D.LOC[k.id]], c.pc != ""))
	for p: String in k.pr:
		list.add_child(_row(p, "cls"))
	scroll.add_child(list)
	h.add_child(scroll)
	h.add_child(_prof_details())
	return h


func _group(title: String, is_done: bool) -> Control:
	var h := CUI.hbox(7)
	h.add_child(UI.label(title, "lilita", 16))
	h.add_child(CUI.mark(is_done))
	var n := UI.label("pick 1", "n800", 11, CUI.CAP_INK)
	n.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(n)
	return h


func _row(p: String, src: String) -> Control:
	var key := "%s:%s" % [src, p]
	var picked: bool = (c.pb if src == "bg" else c.pc) == p
	var foc := _focus == key
	var t := CUI.Tap.new(key)
	t.custom_minimum_size.y = 48
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var box := PanelContainer.new()
	box.add_theme_stylebox_override("panel", CUI.tile_box(CUI.FOCUS_RIM if foc else (CUI.SEL_RIM if picked else CUI.PANEL_LINE), 3 if foc else 2.5, 12, Vector4(8, 5, 10, 5)))
	box.set_anchors_preset(Control.PRESET_FULL_RECT)
	box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var h := CUI.hbox(9)
	h.add_child(CUI.hex(30, 34, CUI.SEL_RIM if picked else UI.RIM, 2.5, D.PROFI.get(p, D.PROFI.Lore), Color("#33403B"), 16))
	var words := CUI.vbox(0)
	words.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	words.add_child(UI.label(p, "n900", 14, UI.INK, 0, 1.15))
	var checks := UI.label(D.PROFD[p][0], "n700", 11, CUI.SOFT_INK, 0, 1.25)
	checks.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	checks.custom_minimum_size.x = 40
	words.add_child(checks)
	h.add_child(words)
	if picked and c.pb == c.pc:
		h.add_child(_tag("Rank 2", Color("#3E6F8C"), UI.WHITE_WARM))
	h.add_child(_tag(D.PROFB[p], Color("#E9F3E2"), Color("#2E6B3A")))
	if picked:
		h.add_child(CUI.Dot.make(18, CUI.SEL_RIM, CUI.TICK, 12))
	box.add_child(h)
	t.add_child(box)
	t.pressed.connect(func():
		_focus = key
		c.render())
	return t


func _tag(t: String, bg: Color, ink: Color) -> Control:
	var p := UI.panel(bg, 11, Color(0, 0, 0, 0), 0, Vector4(9, 0, 9, 0))
	p.custom_minimum_size.y = 22
	p.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var l := UI.label(t, "n800", 11, ink)
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	p.add_child(l)
	return p


func _prof_details() -> Control:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", CUI.tile_box(CUI.PANEL_LINE, 2.5, 14, Vector4(12, 10, 12, 12)))
	p.custom_minimum_size.x = 212
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var v := CUI.vbox(6)
	var parts := _focus.split(":")
	var src := parts[0]
	var prof := parts[1]
	var picked: bool = (c.pb if src == "bg" else c.pc) == prof
	var other: String = c.pc if src == "bg" else c.pb
	var inner := 212.0 - 24.0
	v.add_child(UI.label(("Background proficiency" if src == "bg" else "Class proficiency").to_upper(), "n900", 11, Color("#7A5A2E") if src == "bg" else Color("#9A4424"), 1))
	v.add_child(UI.label(prof, "lilita", 18, UI.INK, 0, 1.05))
	v.add_child(CUI.wrap(UI.label(D.PROFD[prof][0], "n700", 11, CUI.SOFT_INK, 0, 1.3), inner))
	v.add_child(UI.label("Base: %s + 1 coin" % D.PROFB[prof], "n800", 11, Color("#2E6B3A")))
	var sig := PanelContainer.new()
	sig.add_theme_stylebox_override("panel", UI.box(Color("#F3EADA"), 10, Color(0, 0, 0, 0), 0, Vector4(8, 5, 8, 5)))
	sig.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var sv := CUI.vbox(1)
	sv.add_child(UI.label("SIGNATURE", "n900", 11, UI.INK_MUTED, 1))
	sv.add_child(CUI.wrap(UI.label(D.PROFD[prof][1], "n800", 11, UI.INK, 0, 1.25), inner - 16.0))
	sig.add_child(sv)
	v.add_child(sig)
	if other == prof and not picked:   # once chosen, the rows' Rank 2 tags show it
		v.add_child(CUI.wrap(UI.label("Matches your other pick: choosing it makes rank 2", "n900", 11, Color("#3E6F8C")), inner))
	v.add_child(CUI.spring())
	if picked:
		v.add_child(CreatorTraining.chosen())
	else:
		var b := CUI.choose_button("Choose", inner)
		b.accessibility_name = "Choose " + prof
		b.pressed.connect(func():
			if src == "bg":
				c.pb = prof
			else:
				c.pc = prof
			c.render())
		v.add_child(b)
	var nav := CUI.hbox(6)
	var back := CUI.big("Back", false, 16)
	back.bg = UI.SAND   # the mockup's cream vanishes on this cream pane
	back.pressed.connect(c.go_back)
	nav.add_child(back)
	nav.add_child(CUI.spring())
	var next := CUI.big("Next", true, 16)
	next.disabled = not c.done("skills")
	next.pressed.connect(c.go_next)
	nav.add_child(next)
	v.add_child(nav)
	p.add_child(v)
	return p


static func chosen() -> Control:
	var p := UI.panel(Color("#E9F3E2"), 15, Color(0, 0, 0, 0), 0, Vector4(12, 0, 12, 0))
	p.custom_minimum_size.y = 30
	p.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var h := CUI.hbox(5)
	h.add_child(UI.icon_rect(CUI.TICK, Color("#2E6B3A"), 13, 3.2))
	(h.get_child(0) as Control).size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var l := UI.label("Chosen", "n900", 12, Color("#2E6B3A"))
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(l)
	p.add_child(h)
	return p


class Coin extends Control:
	var ring := Color(0, 0, 0, 0)
	func _draw() -> void:
		var m := size * 0.5
		if ring.a > 0:
			draw_circle(m, 9.5, ring)
		draw_circle(m, 7, UI.GOLD_EDGE)
		draw_circle(m - Vector2(0, 1), 6, UI.GOLD)
