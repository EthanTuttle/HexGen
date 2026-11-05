class_name ActionCards
extends Control
## The Action cards screen (design/07 -> Action cards screen; from v3b, mockups/action-cards/v3b-ActionCards-FromCombat.dc.html):
## the top bar (back, name and subtitle, party), every card the character has grouped by source, the details panel, and the
## hotbar tray with Rules.HOTBAR_SLOTS slots. Drag a card onto a slot to place it; between slots to swap; off the tray to
## clear. A tap or a long-press shows a card's details. On touch a quick swipe up or down in the list scrolls it (PLACEHOLDER). Back returns to where it was opened from.
## Opened from combat's Edit hotbar (All actions pop-up). There's no gear screen yet, so the gear way in isn't hooked up.
## The bar is kept per member as `hot_slots` (Rules.HOTBAR_SLOTS ids, "" for empty), and `hot` (what combat draws) is the same
## cards without the gaps, changed in place so a fight's unit, which holds the same array, sees it.
## Phone layout (design/07, Ethan, Nov 5, 2026): v3's arrangement with combat's 170 pt details panel and no label column on
## the tray, so 7 slots fit; Set 1 / Set 2 tabs always show, and Set 2, which no member has yet, is dimmed with "No weapon" and
## can't be picked (Ethan, Nov 5, 2026). Race comes first in the list, and Block stands in Basic for Defend (04 -> Shields).
## Cut from v3's text (design/07): the hints, tiles' source words, the slots' numbers, "always available", the set's name in
## the list's header (the tab says it), and the Class section's race and class.

const SLOT := Vector2(66, 76)
const SLOT_GAP := 6.0
const TILE_H := 44.0
const COMBAT_DIM := Color(0.141, 0.188, 0.172, 0.42)
const MENU_BG := Color("#BFD9D2")
const TILE_EDGE := Color("#E2D5BC")
const WELL := Color("#9E8264")
const BACK_ICON := "M15 5l-7 7 7 7"
## How the sections group the cards' sources (design/07: Race first, with the racial card and racial spells). Block is
## listed with Basic, as with a shield it is the basic defend action (04 -> Shields); which members have it is theirs (Rules.PARTY).
const SECTIONS := [["race", "Race", ["race", "elven", "bloodline"]], ["basic", "Basic", ["basic"]], ["weapon", "Weapon", ["weapon"]],
	["klass", "Class", ["klass"]]]
const DETAILS_W := 170.0           # combat's (design/07 -> Action cards screen -> Phone layout)
## DOCS: design/01 -> Companions (classes); Fluffy's race name is open, so the mockup's "Cat" stands in.
const COMPANION := {"Fluffy": ["Cat", "Wizard"], "Chelmsford": ["Dragonborn", "Cleric"], "Mel": ["Wood Elf", "Rogue"]}

signal closed

var game: Game
var from := "combat"               # or "gear"
var ci := 0                        # whose cards
var _tabs := HBoxContainer.new()
var sel := ""
var _safe := SafeArea.new()
var _root := Control.new()         # inside the safe area
var _top := Control.new()
var _party := HBoxContainer.new()
var _list_panel: PanelContainer
var _list := VBoxContainer.new()
var _scroll := ScrollContainer.new()
var _tray: PanelContainer
var _slots: Array[_Slot] = []
var _details_panel: PanelContainer
var _details := VBoxContainer.new()
var _ghost: _Card
var _press := {}                   # {id, from (slot or -1), pos, ms, moved, held}
var over := -1


## Opens over the fight for the character acting (combat's Edit hotbar).
static func open_from_fight(f: Fight) -> ActionCards:
	var s := ActionCards.new(f.game, "combat")
	s.ci = maxi(0, f.game.party.find(f.current.get("member", {})))
	f.hud.visible = false   # v3b: only the world shows behind, dimmed
	s.closed.connect(func():
		f.hud.visible = true
		f.refresh())   # combat's bar reads `hot_slots`, gaps included
	f.game.ui.add_child(s)
	return s


func _init(g: Game, opened_from: String) -> void:
	game = g
	from = opened_from
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP


func _ready() -> void:
	accessibility_name = "Action cards"
	if from == "combat":
		var dim := ColorRect.new()
		dim.color = COMBAT_DIM
		dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(dim)
	add_child(_safe)
	_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_safe.add_child(_root)
	_build_top()
	_build_list()
	_build_tray()
	_build_details()
	_ghost = _Card.new()
	_ghost.ghost = true
	_ghost.visible = false
	_ghost.rotation_degrees = -5.0
	_ghost.pivot_offset = SLOT * 0.5
	add_child(_ghost)
	_root.resized.connect(_layout)
	resized.connect(queue_redraw)
	_pick_member(ci)
	_layout.call_deferred()


func _draw() -> void:
	if from == "combat":
		return
	draw_rect(Rect2(Vector2.ZERO, size), MENU_BG)
	var line := Color("#2F5D52", 0.14)   # the menu's hex pattern (26 x 45)
	for y in range(0, int(size.y) + 45, 45):
		for x in range(0, int(size.x) + 26, 26):
			var o := Vector2(x, y)
			var pts := PackedVector2Array([o + Vector2(13, 0), o + Vector2(26, 7.5), o + Vector2(26, 22.5), o + Vector2(13, 30),
				o + Vector2(0, 22.5), o + Vector2(0, 7.5), o + Vector2(13, 0)])
			draw_polyline(pts, line, 1.0)
			draw_line(o + Vector2(13, 30), o + Vector2(13, 45), line, 1.0)


# --- Layout: the mockup's 844 x 390, fitted to the safe area's width ---------------------------------------------------

func _layout() -> void:
	var w := _root.size.x
	var m := 18.0 if w >= 844.0 else 12.0
	var dw := DETAILS_W
	var lw := w - m * 2.0 - dw - 12.0
	_top.position = Vector2(m, 12)
	_top.size = Vector2(w - m * 2.0, 54)
	_party.position = Vector2((_top.size.x - _party.get_combined_minimum_size().x) * 0.5, 0)
	_tabs.position = Vector2(_top.size.x - _tabs.get_combined_minimum_size().x, 7)
	_list_panel.position = Vector2(m, 76)
	_list_panel.size = Vector2(lw, 192)
	_tray.position = Vector2(m, 282)
	_tray.size = Vector2(lw, 94)
	var n := Rules.HOTBAR_SLOTS
	var gap := clampf((lw - 16.0 - n * SLOT.x) / (n - 1), 3.0, SLOT_GAP)
	var row := n * SLOT.x + (n - 1) * gap
	for i in n:
		_slots[i].position = Vector2((lw - row) * 0.5 + i * (SLOT.x + gap), 9)
	_details_panel.position = Vector2(w - m - dw, 76)
	_details_panel.size = Vector2(dw, 300)
	_details_panel.custom_minimum_size = Vector2(dw, 300)
	_fill_list()
	_fill_details()


# --- Top bar -------------------------------------------------------------------------------------------------------

var _name: Label
var _sub: Label


func _build_top() -> void:
	_top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(_top)
	var back := HexShape.make(44, 51, UI.RIM, UI.CREAM_LIGHT, 3).with_icon(BACK_ICON, Color("#33403B"), 20, 2.4).with_shadow(UI.HEX_SHADOW, 4)
	back.clickable = true
	back.accessibility_name = "Back to fight" if from == "combat" else "Back to gear"
	back.position = Vector2(0, 1)
	back.pressed.connect(close)
	_top.add_child(back)
	var words := VBoxContainer.new()
	words.add_theme_constant_override("separation", 0)
	words.position = Vector2(54, 6)
	var on_dark := from == "combat"
	_name = UI.label("", "lilita", 22, UI.WHITE_WARM if on_dark else UI.INK, 0, 1.1)
	_sub = UI.label("", "n700", 12, Color("#F1E6D2") if on_dark else UI.INK_SOFT)
	words.add_child(_name)
	words.add_child(_sub)
	words.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_top.add_child(words)
	_party.add_theme_constant_override("separation", 6)
	_party.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_top.add_child(_party)
	_tabs.add_theme_constant_override("separation", 4)
	_tabs.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_top.add_child(_tabs)


## Set 1 / Set 2, always both (design/07 -> Action cards screen -> Phone layout), as v3b's tabs.
func _fill_tabs() -> void:
	for c in _tabs.get_children():
		_tabs.remove_child(c)
		c.queue_free()
	for i in 2:
		var t := _SetTab.new()
		t.label = "Set %d" % (i + 1)
		t.gear = weapon_name(i)
		t.on = i == 0
		t.dim = i == 1   # members have one set (Ethan, Nov 5, 2026: dimmed, "No weapon", can't be picked)
		t.accessibility_name = "%s, %s%s" % [t.label, t.gear, ", selected" if t.on else ""]
		_tabs.add_child(t)
	if _top.size.x > 0:
		_tabs.position = Vector2(_top.size.x - _tabs.get_combined_minimum_size().x, 7)


## The set's weapon as its tab says it. Members have one set.
func weapon_name(i: int) -> String:
	return String(member().get("weapon", "")).capitalize() if i == 0 else "No weapon"


func _fill_party() -> void:
	for c in _party.get_children():
		_party.remove_child(c)
		c.queue_free()
	for i in game.party.size():
		var p: Dictionary = game.party[i]
		var on := i == ci
		var h := HexShape.make(46, 53, UI.ORANGE if on else UI.RIM, Color(p.color), 4 if on else 3).with_text(p.initial, 19).with_shadow(UI.HEX_SHADOW, 4)
		h.clickable = true
		h.accessibility_name = p.name + (", selected" if on else "")
		h.pressed.connect(_pick_member.bind(i))
		_party.add_child(h)


## "Race Class (Subclass) · Lv" (design/07 -> Screen text -> Character subtitles). No subclass before level 5.
func subtitle(m: Dictionary) -> String:
	if m == game.party[0] and Hero.current != null:
		return Hero.current.subtitle(game.level)
	if COMPANION.has(m.name):
		return "%s %s · Lv %d" % [COMPANION[m.name][0], COMPANION[m.name][1], game.level]
	var race: String = m.get("sub", "") if m.get("sub", "") != "" and m.get("race", "") in ["Elf", "Dwarf"] else m.get("race", "")
	return "%s Fighter · Lv %d" % [race, game.level]   # the hero with no creator behind the run (Rules.HERO_DEFAULT)


func _pick_member(i: int) -> void:
	ci = clampi(i, 0, game.party.size() - 1)
	var m := member()
	sel = "attack" if "attack" in m.get("cards", []) else ""
	_name.text = m.name
	_sub.text = subtitle(m)
	_fill_party()
	_fill_tabs()
	if is_inside_tree() and _root.size.x > 0:
		_party.position.x = (_top.size.x - _party.get_combined_minimum_size().x) * 0.5
		_fill_list()
		_fill_details()
	_fill_slots()


func member() -> Dictionary:
	return game.party[ci]


func card(id: String) -> Dictionary:
	var m := member()
	return Cards.get_card(id, m.get("weapon", ""), m.get("sub", ""))


# --- The bar ---------------------------------------------------------------------------------------------------------

## The member's slots, Rules.HOTBAR_SLOTS long; made from `hot` the first time.
func slots() -> Array:
	var m := member()
	if not m.has("hot_slots"):
		var s: Array = m.get("hot", []).duplicate()
		s.resize(Rules.HOTBAR_SLOTS)
		m.hot_slots = s.map(func(id): return "" if id == null else id)
	return m.hot_slots


func _set_slots(s: Array) -> void:
	var m := member()
	m.hot_slots = s
	if not m.has("hot"):
		m.hot = []
	var hot: Array = m.hot
	hot.clear()
	hot.append_array(s.filter(func(id): return id != ""))


## Drops `id` (from slot `from_slot`, or -1 from the list) on slot `to` (-1: off the tray). As v3b: a card already on the bar
## moves; slot to slot swaps; a slot's card dropped off the tray clears it.
func drop(id: String, from_slot: int, to: int) -> void:
	var s: Array = slots().duplicate()
	if to >= 0:
		if from_slot >= 0:
			var t: String = s[to]
			s[to] = s[from_slot]
			s[from_slot] = t
		else:
			var was := s.find(id)
			if was >= 0:
				s[was] = s[to]
			s[to] = id
	elif from_slot >= 0:
		s[from_slot] = ""
	else:
		return
	_set_slots(s)
	sel = id
	_fill_slots()
	_fill_list()
	_fill_details()


func _build_tray() -> void:
	_tray = UI.panel(UI.TRAY, 18, UI.TRAY_EDGE, 4, Vector4(0, 0, 0, 0))
	_tray.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(_tray)
	var holder := Control.new()   # slots sit by position, not in the panel's container layout
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_tray.add_child(holder)
	for i in Rules.HOTBAR_SLOTS:
		var s := _Slot.new()
		s.screen = self
		s.idx = i
		holder.add_child(s)
		_slots.append(s)


func _fill_slots() -> void:
	var s := slots()
	for i in _slots.size():
		var id: String = s[i]
		_slots[i].set_card(card(id) if id != "" else {}, id != "" and id == sel)
		_slots[i].accessibility_name = "Hotbar slot %d: %s" % [i + 1, card(id).n if id != "" else "empty"]
		_slots[i].lit = i == over


# --- The list --------------------------------------------------------------------------------------------------------

func _build_list() -> void:
	_list_panel = UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(12, 10, 12, 10))
	_root.add_child(_list_panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	v.add_child(UI.label("All actions", "lilita", 15))
	_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_list.add_theme_constant_override("separation", 8)
	_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_scroll.add_child(_list)
	v.add_child(_scroll)
	_list_panel.add_child(v)


func _fill_list() -> void:
	for c in _list.get_children():
		_list.remove_child(c)
		c.queue_free()
	var m := member()
	var bar := slots()
	var inner := _list_panel.size.x - 24.0 - 6.0
	var cols := 4 if inner >= 560.0 else 3
	var m_cards: Array = m.get("cards", [])
	for sec: Array in SECTIONS:
		var ids := m_cards.filter(func(id): return section_of(id) == sec[0])
		if ids.is_empty():
			continue
		var block := VBoxContainer.new()
		block.add_theme_constant_override("separation", 5)
		var head := HBoxContainer.new()
		head.add_theme_constant_override("separation", 6)
		var src: Dictionary = Cards.SRC[sec[2][0]]
		var band := ColorRect.new()
		band.color = Color(src.band)
		band.custom_minimum_size = Vector2(16, 6)
		band.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		head.add_child(band)
		head.add_child(UI.label(String(sec[1]).to_upper(), "n900", 11, Color(src.ink), 1))
		block.add_child(head)
		var grid := GridContainer.new()
		grid.columns = cols
		grid.add_theme_constant_override("h_separation", 5)
		grid.add_theme_constant_override("v_separation", 5)
		var tw := floorf((inner - 5.0 * (cols - 1)) / cols)
		for id: String in ids:
			var t := _Tile.new()
			t.screen = self
			t.id = id
			t.k = card(id)
			t.slot = bar.find(id)
			t.on = id == sel
			t.custom_minimum_size = Vector2(tw, TILE_H)
			t.accessibility_name = "%s, %s AP%s" % [t.k.n, Cards.ap_text(t.k), ", on hotbar slot %d" % (t.slot + 1) if t.slot >= 0 else ""]
			grid.add_child(t)
		block.add_child(grid)
		_list.add_child(block)


func section_of(id: String) -> String:
	if id == "block":
		return "basic"
	for sec: Array in SECTIONS:
		if Cards.ALL[id].src in sec[2]:
			return sec[0]
	return ""


# --- Details (v3: source and AP, name, text, Use, and Attack Flip or Save) ------------------------------------------------

func _build_details() -> void:
	_details_panel = UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(12, 12, 12, 12))
	_details_panel.clip_contents = true
	_details.add_theme_constant_override("separation", 6)
	_details_panel.add_child(_details)
	_root.add_child(_details_panel)


func _fill_details() -> void:
	for c in _details.get_children():
		_details.remove_child(c)
		c.queue_free()
	if sel == "":
		return
	var k := card(sel)
	var src: Dictionary = Cards.SRC[k.src]
	var wide := _details_panel.size.x - 24.0
	var top := VBoxContainer.new()
	top.add_theme_constant_override("separation", 0)
	top.add_child(_wrap(UI.label(("%s · %s" % [src.label, "AP not set" if k.ap < 0 else "%d AP" % k.ap]).to_upper(), "n900", 11, Color(src.ink), 1), wide))
	# Combat's sizes from its fit pass (design/07: everything fits, 11 pt or more): name 17, text 11.
	top.add_child(_wrap(UI.label(k.n, "lilita", 17, UI.INK, 0, 1.1), wide))
	top.add_child(_wrap(UI.label(k.desc, "n700", 11, UI.INK_SOFT), wide))
	_details.add_child(top)
	var div := ColorRect.new()
	div.color = Color(UI.HEX_SHADOW, 0.5)
	div.custom_minimum_size = Vector2(wide, 2)
	_details.add_child(div)
	_details.add_child(_line("Use:", {"": "Repeatable", "turn": "Once per turn", "fight": "Once per fight"}.get(k.limit, "")))
	var how := resolves(k)
	if not how.is_empty():
		_details.add_child(_line(how[0] + ":", how[1]))


## How a card resolves (design/07 -> Action cards screen -> Details panel): ["Attack Flip", ability] for an attack (a card's own
## ability, else the member's: the weapon's, or the caster's for spells), ["Save", ability] for a save, or [] for neither.
func resolves(k: Dictionary) -> Array:
	if k.kind == "attack":
		return ["Attack Flip", k.get("ab", member().get("ability", ""))]
	if k.has("save"):
		return ["Save", k.save]
	return []


func _line(a: String, b: String) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 4)
	h.add_child(UI.label(a, "n700", 11, UI.INK_SOFT))
	h.add_child(UI.label(b, "n900", 11))
	return h


func _wrap(l: Label, w: float) -> Label:
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size.x = w
	return l


func select(id: String) -> void:
	sel = id
	_fill_slots()
	_fill_list()
	_fill_details()


# --- Pressing, dragging, long-press ----------------------------------------------------------------------------------

## A press on a tile or a filled slot. Moving past the tap distance lifts the card; holding still shows its details.
func begin_press(id: String, from_slot: int, at: Vector2) -> void:
	_press = {"id": id, "from": from_slot, "pos": at, "ms": Time.get_ticks_msec(), "moved": false, "held": false}


func _process(_delta: float) -> void:
	if not _press.is_empty() and not _press.moved and not _press.held and not _press.get("scroll", false) and Time.get_ticks_msec() - int(_press.ms) >= Rules.TAP_MS:
		_press.held = true   # long-press: details, as on the gear screen
		select(_press.id)


func _input(e: InputEvent) -> void:
	if _press.is_empty():
		return
	if e is InputEventMouseMotion:
		var at := (e as InputEventMouseMotion).global_position
		if _press.get("scroll", false):
			if _scroll.get_global_rect().has_point(at):
				_scroll.scroll_vertical = int(_press.scroll_from - (at.y - _press.pos.y))
				get_viewport().set_input_as_handled()
				return
			_scroll.scroll_vertical = _press.scroll_from   # out of the list: it was a drag to the tray after all
			_press.scroll = false
			_lift()
		if not _press.moved and at.distance_to(_press.pos) >= Rules.TAP_PIXELS:
			var d: Vector2 = at - _press.pos
			# PLACEHOLDER (question to Ethan): on touch, a quick swipe mostly up or down in the list scrolls it, until the finger
			# leaves the list, which lifts the card after all; a sideways move, or any move after a long-press, lifts it at
			# once. With the mouse, every drag lifts and the wheel scrolls.
			if _press.from < 0 and not _press.held and e.device == InputEvent.DEVICE_ID_EMULATION and absf(d.y) > absf(d.x) \
					and _scroll.get_v_scroll_bar().max_value > _scroll.size.y:
				_press.scroll = true
				_press.scroll_from = _scroll.scroll_vertical
				return
			_lift()
		if _press.moved:
			_ghost.global_position = at - Vector2(33, 50)
			_set_over(slot_at(at))
		get_viewport().set_input_as_handled()
	elif e is InputEventMouseButton and (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT and not e.pressed:
		var at := (e as InputEventMouseButton).global_position
		var p := _press
		_press = {}
		_ghost.visible = false
		_set_over(-1)
		if p.get("scroll", false):
			pass
		elif p.moved:
			drop(p.id, p.from, slot_at(at))
		elif not p.held:
			select(p.id)
		get_viewport().set_input_as_handled()


func _lift() -> void:
	_press.moved = true
	_ghost.set_card(card(_press.id), false)
	_ghost.visible = true


## The slot under a point on screen, or -1.
func slot_at(at: Vector2) -> int:
	for s in _slots:
		if s.get_global_rect().grow(4).has_point(at):
			return s.idx
	return -1


func _set_over(i: int) -> void:
	if i == over:
		return
	over = i
	for s in _slots:
		s.lit = s.idx == over
		s.queue_redraw()


func close() -> void:
	closed.emit()
	queue_free()


# --- Drawn pieces ----------------------------------------------------------------------------------------------------

## A weapon set tab (v3b: 40 tall, pointed ends): "Set 1" over its weapon; dark when picked.
class _SetTab extends Control:
	signal pressed
	var label := ""
	var gear := ""
	var on := false
	var dim := false

	func _ready() -> void:
		var f := UI.font("n900")
		var w := maxf(f.get_string_size(label, 0, -1, 12).x, UI.font("n700").get_string_size(gear, 0, -1, 11).x)
		custom_minimum_size = Vector2(ceilf(w) + 32.0, 40)
		mouse_filter = Control.MOUSE_FILTER_IGNORE if dim else Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_ARROW if dim or on else Control.CURSOR_POINTING_HAND
		modulate.a = 0.45 if dim else 1.0

	func _draw() -> void:
		draw_colored_polygon(UI.tag_points(Rect2(Vector2.ZERO, size), 10), UI.DARK if on else UI.SAND)
		var ink := UI.CREAM if on else Color("#4A4034")
		var f := UI.font("n900")
		var g := UI.font("n700")
		draw_string(f, Vector2((size.x - f.get_string_size(label, 0, -1, 12).x) * 0.5, 18), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, ink)
		draw_string(g, Vector2((size.x - g.get_string_size(gear, 0, -1, 11).x) * 0.5, 31), gear, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(ink, 0.85))

	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
			accept_event()

	func _has_point(point: Vector2) -> bool:
		return UI.finger_rect(size).has_point(point)


## A card in the list (v3b: 44 tall): AP hex, icon and name. No slot number (design/07: the hotbar shows it).
class _Tile extends Control:
	var screen: ActionCards
	var id := ""
	var k: Dictionary
	var slot := -1
	var on := false

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_DRAG

	func _draw() -> void:
		var src: Dictionary = Cards.SRC[k.src]
		var face := UI.box(UI.CREAM_LIGHT, 10)
		face.border_color = UI.ORANGE if on else ActionCards.TILE_EDGE
		face.set_border_width_all(2)
		draw_style_box(face, Rect2(Vector2.ZERO, size))
		draw_colored_polygon(UI.hex_points(Rect2(Vector2(8, 10.5), Vector2(20, 23))), UI.DARK)
		var f := UI.font("n900")
		var ap := Cards.ap_text(k)
		draw_string(f, Vector2(18 - f.get_string_size(ap, 0, -1, 11).x * 0.5, 26), ap, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.CREAM)
		draw_texture_rect(UI.icon(k.icon, Color(src.icon_ink), 18, 2), Rect2(Vector2(34, 13), Vector2(18, 18)), false)
		draw_string(f, Vector2(58, 27), k.n, HORIZONTAL_ALIGNMENT_LEFT, size.x - 64.0, 12, UI.INK)

	func _gui_input(e: InputEvent) -> void:
		if e is InputEventMouseButton and (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT and e.pressed:
			screen.begin_press(id, -1, (e as InputEventMouseButton).global_position)
			accept_event()


## A hotbar slot (v3b: a 66 x 76 well, without its number: design/07), holding a card or "Empty".
class _Slot extends Control:
	var screen: ActionCards
	var idx := 0
	var k: Dictionary = {}
	var on := false
	var lit := false
	var _card := _Card.new()

	func _ready() -> void:
		custom_minimum_size = ActionCards.SLOT
		size = ActionCards.SLOT
		mouse_filter = Control.MOUSE_FILTER_STOP
		_card.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(_card)

	func set_card(c: Dictionary, selected: bool) -> void:
		k = c
		on = selected
		_card.visible = not c.is_empty()
		if not c.is_empty():
			_card.set_card(c, selected)
		mouse_default_cursor_shape = Control.CURSOR_ARROW if c.is_empty() else Control.CURSOR_DRAG
		queue_redraw()

	func _draw() -> void:
		var r := Rect2(Vector2.ZERO, size)
		if lit:
			var ring := StyleBoxFlat.new()
			ring.draw_center = false
			ring.set_corner_radius_all(13)
			ring.set_border_width_all(3)
			ring.border_color = UI.ORANGE
			draw_style_box(ring, r.grow(5))
		draw_style_box(UI.box(ActionCards.WELL, 10), r)
		draw_rect(Rect2(Vector2(6, 0), Vector2(size.x - 12, 3)), Color(UI.INK, 0.22))   # the inset shadow's top
		if k.is_empty():
			var f := UI.font("n800")
			var w := f.get_string_size("Empty", 0, -1, 11).x
			draw_string(f, Vector2((size.x - w) * 0.5, size.y * 0.5 + 4), "Empty", HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color("#F1E6D2"))

	func _gui_input(e: InputEvent) -> void:
		if k.is_empty():
			return
		if e is InputEventMouseButton and (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT and e.pressed:
			screen.begin_press(k.id, idx, (e as InputEventMouseButton).global_position)
			accept_event()


## The card drawn in a slot and under the finger while dragging (v3b): band, AP hex, repeat icon or once-per-fight tag,
## icon and name. Once per turn carries no badge (design/07 -> Combat screen).
class _Card extends Control:
	var k: Dictionary = {}
	var on := false
	var ghost := false

	func _ready() -> void:
		size = ActionCards.SLOT
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		z_index = 10 if ghost else 0

	func set_card(c: Dictionary, selected: bool) -> void:
		k = c
		on = selected
		queue_redraw()

	func _draw() -> void:
		if k.is_empty():
			return
		var src: Dictionary = Cards.SRC[k.src]
		var r := Rect2(Vector2.ZERO, ActionCards.SLOT)
		draw_style_box(UI.box(UI.HEX_SHADOW, 10), Rect2(r.position + Vector2(0, 6 if ghost else 4), r.size))
		var face := UI.box(UI.CREAM_LIGHT, 10)
		face.border_color = UI.ORANGE if on or ghost else UI.CREAM_LIGHT
		face.set_border_width_all(3 if on or ghost else 2)
		draw_style_box(face, r)
		draw_rect(Rect2(Vector2(2.5, 2.5), Vector2(r.size.x - 5, 6)), Color(src.band))
		var f := UI.font("n900")
		if not ghost:
			draw_colored_polygon(UI.hex_points(Rect2(Vector2(4, 9), Vector2(18, 21))), UI.DARK)
			var ap := Cards.ap_text(k)
			draw_string(f, Vector2(13 - f.get_string_size(ap, 0, -1, 10).x * 0.5, 24), ap, HORIZONTAL_ALIGNMENT_LEFT, -1, 10, UI.CREAM)
			if k.limit == "":
				draw_texture_rect(UI.icon("repeat", ON_BAR_INK, 14, 2.6), Rect2(Vector2(r.size.x - 18, 10), Vector2(14, 14)), false)
			elif k.limit == "fight":
				draw_style_box(UI.box(Color("#843E0E"), 7), Rect2(Vector2(r.size.x - 27, 9), Vector2(24, 15)))
				draw_string(f, Vector2(r.size.x - 24, 20), "1", HORIZONTAL_ALIGNMENT_LEFT, -1, 10, UI.WHITE_WARM)
				draw_texture_rect(UI.icon("fight_once", UI.WHITE_WARM, 9, 2.6), Rect2(Vector2(r.size.x - 15, 12), Vector2(9, 9)), false)
		draw_texture_rect(UI.icon(k.icon, Color(src.icon_ink), 22, 2), Rect2(Vector2((r.size.x - 22) * 0.5, 22 if not ghost else 20), Vector2(22, 22)), false)
		# The name, on up to two lines (11 pt: the smallest text size in the docs).
		var words := String(k.n).split(" ")
		var lines: Array[String] = [k.n]
		if f.get_string_size(k.n, 0, -1, 11).x > r.size.x - 6 and words.size() > 1:
			lines = [" ".join(words.slice(0, words.size() / 2)), " ".join(words.slice(words.size() / 2))]
		var y := 58.0 if lines.size() == 1 else 54.0
		for i in lines.size():
			var w := f.get_string_size(lines[i], 0, -1, 11).x
			draw_string(f, Vector2((r.size.x - w) * 0.5, y + i * 12), lines[i], HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.INK)

	const ON_BAR_INK := Color("#2E6B3A")
