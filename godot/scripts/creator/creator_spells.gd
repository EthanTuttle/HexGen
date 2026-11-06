class_name CreatorSpells
extends Control
## The Spells step, for casters (design/06 -> Start, Ethan, Nov 6, 2026: it copies level-up v8a's caster pick; design/07
## -> Level-up screen -> Caster level 3): two slots on top that fill as you pick, tapping a filled one clears it; below,
## the 9 level-1 spells in a column per school, as rows with AP, name and a tick once picked. Tapping a spell opens its
## pop-up (school, text, Choose); choosing a third shows "Replaces ..." and swaps out the first pick. PLACEHOLDER look
## beyond the level-up mockup's: no creator mockup of this step yet.

const D = preload("res://scripts/creator/creator_data.gd")
## The schools' icons, from the level-up mockup (SCHOOL_IC).
const SCHOOL_ICON := {"Summoner": "M12 4a8 8 0 1 0 0 16 8 8 0 1 0 0-16 M12 8a4 4 0 0 1 4 4",
	"Blaster": "M12 2l1.8 4.6L18.5 4l-1.6 4.9 5 .9-4.2 2.7 3.4 3.7-5-.4.4 5L12.9 18 12 23l-.9-5-3.6 2.8.4-5-5 .4 3.4-3.7-4.2-2.7 5-.9L5.5 4l4.7 2.6z M12.7 8.6l-2.4 3.7h3.4l-2.4 3.7",
	"Deceiver": "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z M12 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6",
	"Ritualist": "M12 3c3 4 6 8 6 11a6 6 0 0 1-12 0c0-3 3-7 6-11z"}
const BAND := "#B5532F"   # class cards' band (Cards.SRC.klass)

var c: Creator
var _focus := ""          # the spell whose pop-up is open
var _shown := false


func _init(creator: Creator) -> void:
	c = creator
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func refresh() -> void:
	for ch in get_children():
		remove_child(ch)
		ch.queue_free()
	var h := CUI.hbox(14 if size.x >= 760.0 else 10)
	h.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(h)
	var pad := Vector4(12, 18, 12, 14)
	var card := CUI.panel(pad)
	card.custom_minimum_size.x = 196 if size.x >= 760.0 else 180
	card.add_child(CreatorTraining.who_card(c, 92, 106, 44, 18, pad))
	h.add_child(card)
	var panel := CUI.panel(Vector4(14, 12, 14, 12))
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var v := CUI.vbox(8)
	v.add_child(_top())
	v.add_child(_schools())
	v.add_child(CUI.spring())
	v.add_child(c.nav_row())
	panel.add_child(v)
	h.add_child(panel)
	if not _shown:   # fades in when the step is new, not on each tap (Ethan's phone notes, Nov 5, 2026)
		_shown = true
		CUI.reveal(h)
	if _focus != "":
		_pop.call_deferred(panel)


static func school_of(id: String) -> String:
	for s: String in Weapons.WIZARD_SPELLS:
		if id in Weapons.WIZARD_SPELLS[s]:
			return s
	return ""


## The card's text without its "Blaster spell:" lead, which the pop-up's tag already says.
static func text_of(k: Dictionary) -> String:
	var t: String = k.desc
	return t.substr(t.find(": ") + 2) if t.contains(" spell: ") else t


# --- The title and the two slots ------------------------------------------------------

func _top() -> Control:
	var row := CUI.hbox(10)
	var head := CUI.hbox(7)
	head.add_child(UI.label("Pick %d spells" % Weapons.SPELL_PICKS, "lilita", 16))
	head.add_child(CUI.mark(c.done("spells")))
	head.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	row.add_child(head)
	row.add_child(CUI.spring())
	for i in Weapons.SPELL_PICKS:
		row.add_child(_slot(i))
	return row


## A slot: dashed with "Spell 1" while empty, else the spell as a card; tapping a filled one clears it.
func _slot(i: int) -> Control:
	var id: String = c.spells[i] if i < c.spells.size() else ""
	var t := CUI.Tap.new("Spell %d" % (i + 1) if id == "" else Cards.ALL[id].n)
	t.custom_minimum_size = Vector2(62, 70)
	if id == "":
		t.mouse_filter = Control.MOUSE_FILTER_IGNORE
		t.draw.connect(func():
			var r := Rect2(Vector2(1, 1), t.size - Vector2(2, 2))
			var pts := [r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y), r.position]
			for k in 4:
				var a: Vector2 = pts[k]
				var b: Vector2 = pts[k + 1]
				var n := int(a.distance_to(b) / 8.0)
				for j in n:
					t.draw_line(a.lerp(b, float(j) / n), a.lerp(b, (j + 0.55) / n), Color("#A8957A"), 2.0))
		var l := UI.label("Spell %d" % (i + 1), "n900", 11, Color("#6E5A44"))
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		l.set_anchors_preset(Control.PRESET_FULL_RECT)
		t.add_child(l)
		return t
	var k := Cards.get_card(id)
	t.draw.connect(func():
		t.draw_style_box(CUI.tile_box(CUI.SEL_RIM, 2, 9, Vector4.ZERO), Rect2(Vector2.ZERO, t.size))
		t.draw_rect(Rect2(2, 2, 58, 5), Color(BAND)))
	var hx := HexShape.make(18, 21, UI.DARK, UI.DARK, 0).with_text(str(k.ap), 11, UI.CREAM, "n900")
	UI.at(hx, 3, 8)
	t.add_child(hx)
	var ic := UI.icon_rect(k.icon, Color("#9A4A12"), 18, 2.2)
	UI.at(ic, 22, 11)
	t.add_child(ic)
	var name_l := UI.label("\n".join(Cards.name_lines(str(k.n), UI.font("n900"), 11, 56)), "n900", 11, UI.INK, 0, 1.0)
	name_l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	name_l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	name_l.position = Vector2(2, 32)
	name_l.size = Vector2(58, 34)
	t.add_child(name_l)
	t.pressed.connect(func():
		c.spells.erase(id)
		_focus = ""
		c.render())
	return t


# --- The school columns ---------------------------------------------------------------

func _schools() -> Control:
	var grid := GridContainer.new()
	grid.columns = Weapons.WIZARD_SPELLS.size()
	grid.add_theme_constant_override("h_separation", 8)
	grid.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for s: String in Weapons.WIZARD_SPELLS:
		var col := CUI.vbox(4)
		col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var head := CUI.hbox(4)
		head.add_child(UI.icon_rect(SCHOOL_ICON[s], Color("#5A5040"), 13, 2.2))
		head.add_child(UI.label(s.to_upper(), "n900", 11, Color("#5A5040"), 1))
		col.add_child(head)
		for id: String in Weapons.WIZARD_SPELLS[s]:
			col.add_child(_row(id))
		grid.add_child(col)
	return grid


## A spell's row: AP hex, name (a blood art's HP heart beside it) and a tick once picked.
func _row(id: String) -> Control:
	var k := Cards.get_card(id)
	var on: bool = id in c.spells
	var open := _focus == id
	var t := CUI.Tap.new(k.n)
	t.custom_minimum_size = Vector2(0, 30)
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	t.draw.connect(func():
		t.draw_style_box(CUI.tile_box(CUI.SEL_RIM if on or open else UI.HEX_SHADOW, 2.5 if open else 2.0, 9, Vector4.ZERO), Rect2(Vector2.ZERO, t.size)))
	var h := CUI.hbox(5)
	h.set_anchors_preset(Control.PRESET_FULL_RECT)
	h.offset_left = 4
	h.offset_right = -5
	var hx := HexShape.make(18, 21, UI.DARK, UI.DARK, 0).with_text(str(k.ap), 10, UI.CREAM, "n900")
	hx.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(hx)
	var name_l := UI.label(k.n, "n900", 11, UI.INK, 0, 1.0)
	name_l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	name_l.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	name_l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	h.add_child(name_l)
	if k.get("hp", 0) > 0:
		h.add_child(_hp_badge(k.hp))
	if on:
		h.add_child(CUI.Dot.make(16, Color("#2E7A3E"), CUI.TICK, 10))
	t.add_child(h)
	t.pressed.connect(func():
		_focus = "" if _focus == id else id
		c.render())
	return t


func _hp_badge(n: int) -> Control:
	var h := CUI.hbox(1)
	h.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(UI.icon_rect(CombatHud.HP_HEART, UI.RED, 12, 2.4))
	h.add_child(UI.label(str(n), "n900", 11, UI.RED))
	return h


# --- The pop-up ----------------------------------------------------------------------

## School and name, the card's text, AP (and HP), then Choose; a third pick names the spell it replaces.
func _pop(panel: Control) -> void:
	var k := Cards.get_card(_focus)
	var box := PanelContainer.new()
	var sb := CUI.tile_box(CUI.SEL_RIM, 3, 16, Vector4(10, 8, 10, 10))
	sb.shadow_color = UI.HEX_SHADOW
	sb.shadow_size = 1
	sb.shadow_offset = Vector2(0, 4)
	box.add_theme_stylebox_override("panel", sb)
	box.custom_minimum_size.x = 250
	var v := CUI.vbox(4)
	var top := CUI.hbox(6)
	var names := CUI.vbox(0)
	names.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	names.add_child(UI.label(("%s spell" % school_of(_focus)).to_upper(), "n900", 11, Color("#9A4A12"), 1))
	names.add_child(UI.label(k.n, "lilita", 17, UI.INK, 0, 1.1))
	top.add_child(names)
	var close := HexShape.make(20, 20, Color(0, 0, 0, 0), Color(0, 0, 0, 0), 0).with_icon("M6 6l12 12 M18 6L6 18", CUI.SOFT_INK, 16, 2.6)
	close.clickable = true
	close.accessibility_name = "Close"
	close.pressed.connect(func():
		_focus = ""
		c.render())
	top.add_child(close)
	v.add_child(top)
	v.add_child(CUI.wrap(UI.label(text_of(k), "n700", 12, Color("#33403B"), 0, 1.35), 230))
	var foot := CUI.hbox(6)
	foot.add_child(_chip("%d AP" % k.ap, UI.DARK, UI.CREAM))
	if k.get("hp", 0) > 0:
		foot.add_child(_chip("%d HP" % k.hp, UI.RED, UI.WHITE_WARM))
	foot.add_child(CUI.spring())
	var picked: bool = _focus in c.spells
	if picked:
		var done := CUI.hbox(4)
		done.add_child(CUI.Dot.make(16, Color("#2E7A3E"), CUI.TICK, 10))
		foot.add_child(done)
	else:
		if c.spells.size() >= Weapons.SPELL_PICKS:
			foot.add_child(UI.label("Replaces %s" % Cards.ALL[c.spells[0]].n, "n800", 11, CUI.CAP_INK))
		var choose := CUI.choose_button("Choose", 92)
		var id := _focus
		choose.pressed.connect(func():
			if c.spells.size() >= Weapons.SPELL_PICKS:
				c.spells.pop_front()
			c.spells.append(id)
			_focus = ""
			c.render())
		foot.add_child(choose)
	v.add_child(foot)
	box.add_child(v)
	add_child(box)
	box.reset_size()
	var r := panel.get_rect()
	box.position = Vector2(r.position.x + (r.size.x - box.size.x) * 0.5, r.end.y - 52 - box.size.y)


func _chip(t: String, bg: Color, ink: Color) -> Control:
	var p := UI.panel(bg, 10, Color(0, 0, 0, 0), 0, Vector4(8, 1, 8, 1))
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	p.add_child(UI.label(t, "n900", 11, ink))
	return p
