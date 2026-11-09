class_name MasteryScreen
extends Control
## The Weapon mastery screen (design/07 -> Weapon mastery screen; final v5c, mockups/final-screens/WeaponMastery.dc.html),
## opened in train mode from the level-up's Weapon mastery step: the top bar (back, name and subtitle, "Training ×1"),
## a tab per weapon the character holds with its learned count, the tree from the weapon's root hex (its category cards
## and passives as badges above and below, then each branch's three nodes, the capstone bigger), and the details panel
## with Train. Learned nodes have an orange rim and a tick, nodes that can be trained glow gold, later ones are dim; for
## non-Fighters the other branches lock once one is started ("Only Fighters can mix branches").
## Train picks the node for this level and returns to the level-up screen (the pick applies on Done, Game.level_picked).
## Nodes come from design/04 (MasteryData); only each branch's first node can be trained in the prototype (Progression).

signal trained(cat: String, id: String)

const BG := Color("#D9E3C8")      # the Training Grounds' background (v5c); the level-up trains here too
const PANEL := Color("#F6EEDF")
const PANEL_EDGE := Color("#CDB894")
const LINE := Color("#CDBFA6")
const DONE := Color("#B5532F")
const LOCK_LINE := Color(0.804, 0.749, 0.651, 0.45)
const BLUE := Color("#5F7F99")
const BLUE_INK := Color("#3E5A70")
const BLUE_FACE := Color("#EAF0F4")
const FOCUS := Color("#3F86C8")
const GOLD := Color("#E4B54C")
const CARD_ICON := "M7 4h10v16H7z M10 9h4 M10 13h4"
const UP_ICON := "M12 19V5 M6 11l6-6 6 6"
const PASSIVE_ICON := "M12 3l7 4v10l-7 4-7-4V7z M12 9v6 M9 12h6"
const STAR := "M12 2l3 6 6 .9-4.5 4.3 1 6.3L12 16.6 6.5 19.5l1-6.3L3 8.9 9 8z"
const SHIELD_ICON := "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"
const KIND := {"card": "New card", "upgrade": "Upgrade", "passive": "Passive"}
var NX := [300.0, 400.0, 506.0]   # the nodes' centres, right-anchored to the tree's width (v5c at 594: 300, 400, 506)
var lx := 170.0                   # where the branch lines fan out to and the branch names start (v5c), 136 when narrow
var details_w := 214.0            # v5c; 170 when the safe area is narrower than the mockup (as combat's details panel)

var game: Game
var member: Dictionary
var cat := ""
var pick: Array = []              # [cat, id] picked this level, shown as learned
var sel := {"kind": "node", "r": 0, "i": 0}
var _safe := SafeArea.new()
var _root := Control.new()
var _glow := 0.0


func _init(g: Game, m: Dictionary, weapon: String, picked: Array) -> void:
	game = g
	member = m
	cat = weapon
	pick = picked.duplicate()
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP


func _ready() -> void:
	accessibility_name = "Weapon mastery"
	add_child(_safe)
	_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_safe.add_child(_root)
	_root.resized.connect(_build)
	sel = {"kind": "node", "r": _first_open_row(), "i": 0}
	_build.call_deferred()


func _process(delta: float) -> void:
	_glow += delta
	for n in _root.find_children("node_*", "Control", true, false):
		n.queue_redraw()


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), BG)


## The weapon's big root hex (v5c), also drawn on the level-up's Weapon mastery step.
static func root_hex(weapon: String) -> HexShape:
	var t: Dictionary = MasteryData.TREES[weapon]
	var h := HexShape.make(92, 106, BLUE, UI.CREAM_LIGHT, 4).with_shadow(UI.HEX_SHADOW, 4)
	var v := CUI.vbox(2)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var ic := UI.icon_rect(icon_of(weapon), BLUE_INK, 38, 2.0)
	ic.custom_minimum_size = Vector2(38, 38)
	ic.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(ic)
	var n := UI.label(t.n, "lilita", 13, BLUE_INK, 0, 1.0)
	n.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(n)
	h.add_child(v)
	return h


static func icon_of(weapon: String) -> String:
	return SHIELD_ICON if weapon == "shield" else CreatorData.IC.get("w_" + weapon, "")


func _tree() -> Dictionary:
	return MasteryData.TREES[cat]


## Progression's node for a branch's first node (the only ones the prototype trains), or {}.
func _prog_node(r: int) -> Dictionary:
	var branch: String = _tree().rows[r].branch
	for n: Dictionary in Progression.MASTERY.get(cat, []):
		if n.branch == branch:
			return n
	return {}


func _learned(r: int, i: int) -> bool:
	if i != 0:
		return false   # later nodes aren't trained before level 6 (05)
	var n := _prog_node(r)
	if n.is_empty():
		return false
	return Progression.has_mastery(member, cat, n.id) or pick == [cat, n.id]


## The branch a non-Fighter has started on this weapon, or -1 (04: other martials commit to one branch per weapon).
func _committed() -> int:
	if Progression.klass(member) == "fighter":
		return -1
	for r in _tree().rows.size():
		if _learned(r, 0):
			return r
	return -1


func _state(r: int, i: int) -> String:
	if _learned(r, i):
		return "done"
	var c := _committed()
	if c >= 0 and c != r:
		return "locked"
	if i == 0 and not _prog_node(r).is_empty():
		return "open"
	return "later"


func _first_open_row() -> int:
	for r in _tree().rows.size():
		if _state(r, 0) in ["open", "done"]:
			return r
	return 0


func _weapons() -> Array:
	return [member.get("weapon", ""), member.get("off", "")].filter(func(w): return MasteryData.TREES.has(w) and Progression.MASTERY.has(w))


# --- Building ------------------------------------------------------------------------------------------------------

func _build() -> void:
	if not is_inside_tree() or cat == "":
		return
	for c in _root.get_children():
		_root.remove_child(c)
		c.queue_free()
	var w := _root.size.x if _root.size.x > 0 else 844.0
	details_w = 214.0 if w >= 844.0 else 170.0
	var tw := w - 24 - details_w - 12
	var sp := clampf((tw - 84 - 250) * 0.5, 86.0, 106.0)
	NX = [tw - 84 - sp * 2, tw - 84 - sp, tw - 84]
	lx = 170.0 if tw >= 594.0 else 136.0
	_build_top(w)
	_build_tabs()
	_build_tree(w)
	_build_details(w)


func _build_top(w: float) -> void:
	var back := HexShape.make(44, 51, UI.RIM, UI.CREAM_LIGHT, 3).with_icon("M15 5l-7 7 7 7", Color("#33403B"), 18, 2.6).with_shadow(UI.HEX_SHADOW, 4)
	back.clickable = true
	back.accessibility_name = "Back to level up"
	back.pressed.connect(queue_free)
	UI.at(back, 12, 12)
	_root.add_child(back)
	var words := CUI.vbox(0)
	words.add_child(UI.label(member.name, "lilita", 21, UI.INK, 0, 1.05))
	words.add_child(UI.label(_subtitle(), "n800", 12, Color("#43524D")))
	UI.at(words, 66, 15)
	_root.add_child(words)
	var pill := UI.panel(UI.DARK, 20, Color(0, 0, 0, 0), 0, Vector4(6, 0, 14, 0))
	pill.custom_minimum_size.y = 40
	var h := CUI.hbox(8)
	var flag := HexShape.make(28, 32, GOLD, GOLD, 0).with_icon("M6 21V4 M6 4h11l-3 4 3 4H6", UI.INK, 16, 2.4)
	flag.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(flag)
	var t := UI.label("Training ×1", "lilita", 16, UI.CREAM)
	t.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(t)
	pill.add_child(h)
	pill.accessibility_name = "1 training left"
	_root.add_child(pill)
	pill.reset_size()
	UI.at(pill, w - 12 - pill.get_combined_minimum_size().x, 18)


func _subtitle() -> String:
	if member == game.party[0] and Hero.current != null:
		return Hero.current.subtitle(game.level, Progression.sub(member))
	if ActionCards.COMPANION.has(member.name):
		return Hero.subtitle_of(ActionCards.COMPANION[member.name][0], ActionCards.COMPANION[member.name][1], Progression.sub(member), game.level)
	return Hero.subtitle_of(member.get("race", ""), "Fighter", Progression.sub(member), game.level)


## A tab per weapon the character holds, with its learned count ("1/9").
func _build_tabs() -> void:
	var row := CUI.hbox(6)
	for wpn: String in _weapons():
		var t: Dictionary = MasteryData.TREES[wpn]
		var total := 0
		var got := 0
		for r in t.rows.size():
			total += t.rows[r].nodes.size()
			var saved := cat
			cat = wpn
			got += 1 if _learned(r, 0) else 0
			cat = saved
		var tab := _Tab.new()
		tab.text = t.n
		tab.count = "%d/%d" % [got, total]
		tab.icon_path = icon_of(wpn)
		tab.on = wpn == cat
		tab.pressed.connect(func():
			cat = wpn
			sel = {"kind": "node", "r": _first_open_row(), "i": 0}
			_build())
		row.add_child(tab)
	UI.at(row, 12, 74)
	_root.add_child(row)


func _build_tree(w: float) -> void:
	var panel := UI.panel(PANEL, 18, PANEL_EDGE, 5, Vector4.ZERO)
	panel.custom_minimum_size = Vector2(w - 24 - details_w - 12, 262)
	UI.at(panel, 12, 116)
	panel.clip_contents = true
	var area := Control.new()
	area.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(area)
	var t := _tree()
	var rows: int = t.rows.size()
	var row_h := 82.0 if rows == 3 else 110.0
	var top0 := 8.0 if rows == 3 else 18.0
	var lines := _Lines.new()
	lines.set_anchors_preset(Control.PRESET_FULL_RECT)
	area.add_child(lines)
	area.custom_minimum_size = panel.custom_minimum_size
	var root := root_hex(cat)
	UI.at(root, 18, 78)
	area.add_child(root)
	var base := _base_items()
	var spots := [Vector2(24, 28), Vector2(24, 188)]
	for k in mini(base.size(), 2):
		var b: Dictionary = base[k]
		lines.add(Vector2(44, 72) if k == 0 else Vector2(44, 172), Vector2(44, 92) if k == 0 else Vector2(44, 190), false, false)
		var on: bool = sel.kind == b.kind and sel.i == b.i
		var badge := _Badge.make(b, on)
		UI.at(badge, spots[k].x, spots[k].y)
		badge.pressed.connect(func():
			sel = {"kind": b.kind, "i": b.i}
			_build())
		area.add_child(badge)
	var committed := _committed()
	for r in rows:
		var row: Dictionary = t.rows[r]
		var cy := top0 + r * row_h + row_h * 0.5
		var s0 := _state(r, 0)
		lines.add(Vector2(108, 131), Vector2(lx, cy), s0 == "done", s0 == "locked")
		lines.add(Vector2(lx, cy), Vector2(NX[0] - 24, cy), s0 == "done", s0 == "locked")
		for i in 2:
			var s := _state(r, i + 1)
			lines.add(Vector2(NX[i] + 24, cy), Vector2(NX[i + 1] - (28 if i == 1 else 24), cy), s == "done", s == "locked")
		var label := CUI.vbox(4)
		label.modulate.a = 0.5 if committed >= 0 and committed != r else 1.0
		var lh := UI.panel(PANEL, 0, Color(0, 0, 0, 0), 0, Vector4(4, 1, 6, 1))
		var lrow := CUI.hbox(5)
		if committed >= 0 and committed != r:
			lrow.add_child(UI.icon_rect("M6 11h12v10H6z M8.5 11V8a3.5 3.5 0 0 1 7 0v3", Color("#5A5040"), 13, 2.6))
		lrow.add_child(UI.label(row.branch, "lilita", 15, UI.INK, 0, 1.1))
		lh.add_child(lrow)
		label.add_child(lh)
		if row.two_handed:
			var chip := UI.panel(Color("#E6DCC8"), 9, Color(0, 0, 0, 0), 0, Vector4(7, 0, 7, 0))
			chip.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
			chip.add_child(UI.label("Two-handed", "n900", 11, UI.INK))
			label.add_child(chip)
		UI.at(label, lx, cy - 10 - (11 if row.two_handed else 0))
		area.add_child(label)
		for i in 3:
			var cap := i == 2
			var node := _Node.make(row.nodes[i], _state(r, i), cap, sel.kind == "node" and sel.r == r and sel.i == i, self)
			node.name = "node_%d_%d" % [r, i]
			var hh := 65.0 if cap else 55.0
			UI.at(node, NX[i] - 40, cy - hh * 0.5 - 6)
			node.pressed.connect(func():
				sel = {"kind": "node", "r": r, "i": i}
				_build())
			area.add_child(node)
	_root.add_child(panel)


## The weapon's category cards, then its passives (04 -> Weapon rules).
func _base_items() -> Array:
	var out := []
	var ids: Array = ["block", "shield_bash"] if cat == "shield" else Weapons.CAT.get(cat, {}).get("cards", [])
	for k in ids.size():
		if Cards.ALL.has(ids[k]):
			var c := Cards.get_card(ids[k], cat)
			out.append({"kind": "base", "i": k, "n": c.n, "ap": c.ap, "text": LevelUp.text_of(c), "card": true, "icon": icon_of(cat)})
	var ps: Array = MasteryData.PASSIVES.get(cat, [])
	for k in ps.size():
		out.append({"kind": "wpas", "i": k, "n": ps[k].n, "ap": -1, "text": ps[k].text, "card": false, "icon": PASSIVE_ICON})
	return out


func _build_details(w: float) -> void:
	var panel := UI.panel(PANEL, 18, PANEL_EDGE, 5, Vector4(12, 12, 12, 12))
	panel.custom_minimum_size = Vector2(details_w, 302)
	UI.at(panel, w - 12 - details_w, 76)
	var v := CUI.vbox(7)
	panel.add_child(v)
	var tag := ""
	var tag_ink := BLUE_INK
	var name := ""
	var text := ""
	var was := ""
	var note := ""
	var is_card := true
	var ap := -1
	var learned := false
	var can_train := false
	var t := _tree()
	if sel.kind == "node":
		var nd: Dictionary = t.rows[sel.r].nodes[sel.i]
		var s := _state(sel.r, sel.i)
		ap = nd.ap
		if ap < 0 and nd.kind == "upgrade" and sel.i == 0 and Cards.ALL.has(_prog_node(sel.r).get("of", "")):
			ap = Cards.ALL[_prog_node(sel.r).of].ap   # the upgraded card keeps its AP
		tag = "%s%s · %s %d" % [KIND[nd.kind], (" · %d AP" % ap) if ap >= 0 else "", t.rows[sel.r].branch, sel.i + 1]
		tag_ink = BLUE_INK if nd.kind == "passive" else Color("#9A4A12")
		name = nd.n
		text = nd.text
		is_card = nd.kind != "passive"
		if nd.kind == "upgrade":
			was = _upgraded_from(sel.r, sel.i)
		if s == "locked":
			note = "Only Fighters can mix branches; %s is on %s." % [member.name, t.rows[_committed()].branch]
		elif s == "later" and sel.i > 0:
			note = "Needs %s first." % t.rows[sel.r].nodes[sel.i - 1].n
		learned = s == "done"
		can_train = s == "open"
	else:
		var b: Dictionary = _base_items().filter(func(x): return x.kind == sel.kind and x.i == sel.i)[0]
		tag = ("Weapon card · %d AP" % b.ap) if b.card else "Weapon passive · %s" % t.n
		name = b.n
		text = b.text
		is_card = b.card
		ap = b.ap
		learned = true
	v.add_child(UI.label(tag.to_upper(), "n900", 11, tag_ink, 1))
	var head: BoxContainer = CUI.hbox(10) if details_w >= 214.0 else CUI.vbox(6)   # narrow: the name under the card
	if is_card:
		head.add_child(_MiniCard.make(name, ap, icon_of(cat)))
	else:
		head.add_child(HexShape.make(58, 67, BLUE, BLUE_FACE, 4).with_icon(PASSIVE_ICON, BLUE_INK, 24, 2.2).with_shadow(UI.HEX_SHADOW))
	var names := CUI.vbox(2)
	names.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var nw := details_w - 100 if details_w >= 214.0 else details_w - 24
	names.add_child(CUI.wrap(UI.label(name, "lilita", 18, UI.INK, 0, 1.1), nw))
	if was != "" and not name.begins_with(was):
		names.add_child(CUI.wrap(UI.label("Replaces %s" % was, "n800", 11, Color("#5A5040")), nw))
	head.add_child(names)
	v.add_child(head)
	v.add_child(CUI.wrap(UI.label(text, "n700", 12, Color("#43524D"), 0, 1.35), details_w - 24))
	if note != "":
		var nb := UI.panel(Color("#F1E8D8"), 10, Color(0, 0, 0, 0), 0, Vector4(8, 6, 8, 6))
		var nh := CUI.hbox(6)
		nh.add_child(UI.icon_rect("M6 11h12v10H6z M8.5 11V8a3.5 3.5 0 0 1 7 0v3", Color("#5A5040"), 13, 2.6))
		nh.add_child(CUI.wrap(UI.label(note, "n800", 11, Color("#5A5040"), 0, 1.25), details_w - 60))
		nb.add_child(nh)
		v.add_child(nb)
	v.add_child(CUI.spring())
	if learned:
		var pill := UI.panel(Color("#E9F3E2"), 15, Color(0, 0, 0, 0), 0, Vector4(12, 0, 12, 0))
		pill.custom_minimum_size.y = 30
		pill.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
		var ph := CUI.hbox(5)
		var tick := UI.icon_rect("M5 12l5 5 9-10", Color("#2E6B3A"), 12, 4.0)
		tick.custom_minimum_size = Vector2(12, 12)
		tick.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		ph.add_child(tick)
		var lt := UI.label("Learned", "n900", 12, Color("#2E6B3A"))
		lt.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		ph.add_child(lt)
		pill.add_child(ph)
		v.add_child(pill)
	elif can_train:
		var b := TagButton.make("Train", details_w - 24, 42, 16)
		b.accessibility_name = "Train"
		var r: int = sel.r
		b.pressed.connect(func():
			var n := _prog_node(r)
			trained.emit(cat, n.id)
			queue_free())
		v.add_child(b)
	_root.add_child(panel)


## The card an upgrade node changes: the weapon card it names, or the node before it.
func _upgraded_from(r: int, i: int) -> String:
	if i == 0:
		var n := _prog_node(r)
		if n.has("of") and Cards.ALL.has(n.of):
			return Cards.ALL[n.of].n
		return String(n.get("n", "")).trim_suffix("+")
	return _tree().rows[r].nodes[i - 1].n


func glow() -> float:
	return 0.5 - 0.5 * cos(_glow * TAU / 1.6)


# --- Drawn pieces --------------------------------------------------------------------------------------------------

## The branch lines (v5c: 2 px, 3 px and orange once learned, faded where locked).
class _Lines extends Control:
	var segs := []
	func _init() -> void:
		mouse_filter = Control.MOUSE_FILTER_IGNORE
	func add(a: Vector2, b: Vector2, done: bool, locked: bool) -> void:
		segs.append([a, b, done, locked])
		queue_redraw()
	func _draw() -> void:
		for s: Array in segs:
			draw_line(s[0], s[1], DONE if s[2] else (LOCK_LINE if s[3] else LINE), 3.0 if s[2] else 2.0, true)


## A weapon tab (v5c): a tag shape, dark when picked, the icon, the name and the learned count.
class _Tab extends Control:
	signal pressed
	var text := ""
	var count := ""
	var icon_path := ""
	var on := false
	func _ready() -> void:
		accessibility_name = "%s, %s learned" % [text, count]
		var f := UI.font("n900")
		custom_minimum_size = Vector2(10 + 16 + 6 + f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x + 5 + f.get_string_size(count, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x + 16, 34)
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	func _draw() -> void:
		draw_colored_polygon(UI.tag_points(Rect2(Vector2.ZERO, size), 10), UI.DARK if on else Color("#F6EEDF"))
		var ink := Color("#F6EEDF") if on else UI.INK
		draw_texture_rect(UI.icon(icon_path, ink, 16, 2.2), Rect2(Vector2(10, 9), Vector2(16, 16)), false)
		var f := UI.font("n900")
		draw_string(f, Vector2(32, 22), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, ink)
		var x := 32 + f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x + 5
		draw_string(UI.font("n800"), Vector2(x, 22), count, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(ink, 0.7))
	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
	func _has_point(p: Vector2) -> bool:
		return UI.finger_rect(size).has_point(p)


## A category card or passive hanging off the root: a small blue hex (AP badge on cards), its name beside it.
class _Badge extends Control:
	signal pressed
	var item := {}
	var on := false
	static func make(b: Dictionary, picked: bool) -> _Badge:
		var x := _Badge.new()
		x.item = b
		x.on = picked
		x.accessibility_name = b.n + (", weapon card, %d AP" % b.ap if b.card else ", weapon passive, always on")
		var f := UI.font("n900")
		x.custom_minimum_size = Vector2(40 + 6 + f.get_string_size(b.n, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x, 46)
		x.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		return x
	func _draw() -> void:
		var r := Rect2(Vector2.ZERO, Vector2(40, 46))
		draw_colored_polygon(UI.hex_points(Rect2(Vector2(0, 3), r.size)), UI.HEX_SHADOW)
		draw_colored_polygon(UI.hex_points(r), FOCUS if on else BLUE)
		draw_colored_polygon(UI.hex_points(r.grow(-4.5 if on else -3.0)), UI.CREAM_LIGHT if item.card else BLUE_FACE)
		draw_texture_rect(UI.icon(item.icon, BLUE_INK, 18, 2.2), Rect2(Vector2(11, 14), Vector2(18, 18)), false)
		var f := UI.font("n900")
		if item.card:
			draw_colored_polygon(UI.hex_points(Rect2(Vector2(-2, 4), Vector2(16, 18))), UI.DARK)
			draw_string(f, Vector2(6 - f.get_string_size(str(item.ap), HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x * 0.5, 17), str(item.ap), HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.CREAM)
		draw_string(f, Vector2(46, 27), item.n, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.INK)
	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
	func _has_point(p: Vector2) -> bool:
		return UI.finger_rect(size).has_point(p)


## A tree node (v5c 'below'): the hex (icon by type: new card, capstone star, upgrade arrow, passive), a tick once learned,
## the name under it; gold and glowing when it can be trained, dim when later or locked.
class _Node extends Control:
	signal pressed
	var nd := {}
	var state := ""
	var cap := false
	var on := false
	var screen: MasteryScreen
	static func make(n: Dictionary, s: String, capstone: bool, picked: bool, sc: MasteryScreen) -> _Node:
		var x := _Node.new()
		x.nd = n
		x.state = s
		x.cap = capstone
		x.on = picked
		x.screen = sc
		x.custom_minimum_size = Vector2(80, (65.0 if capstone else 55.0) + 6 + 3 + 28)
		x.modulate.a = {"locked": 0.45, "later": 0.7}.get(s, 1.0)
		x.accessibility_name = "%s (%s, %s)" % [n.n, KIND[n.kind], {"done": "learned", "open": "can be trained", "later": "needs the previous node", "locked": "locked"}[s]]
		x.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		return x
	func _draw() -> void:
		var hw := 56.0 if cap else 48.0
		var hh := 65.0 if cap else 55.0
		var r := Rect2(Vector2((80 - hw) * 0.5, 6), Vector2(hw, hh))
		if state == "open":
			var g := screen.glow()
			for k in 4:
				draw_colored_polygon(UI.hex_points(r.grow(2.0 + k * 2.0)), Color(0.894, 0.71, 0.298, 0.12 * g))
		draw_colored_polygon(UI.hex_points(Rect2(r.position + Vector2(0, 3), r.size)), UI.HEX_SHADOW)
		var rim: Color = FOCUS if on else {"done": DONE, "open": GOLD}.get(state, LINE)
		draw_colored_polygon(UI.hex_points(r), rim)
		var face: Color = {"done": Color("#FFF4E8"), "open": Color("#FFFBEF")}.get(state, Color("#F1E8D8"))
		draw_colored_polygon(UI.hex_points(r.grow(-5.0 if on else -3.5)), face)
		var icon: String = (STAR if cap else CARD_ICON) if nd.kind == "card" else (UP_ICON if nd.kind == "upgrade" else PASSIVE_ICON)
		var isz := 26.0 if cap else 22.0
		draw_texture_rect(UI.icon(icon, Color("#9A4A12") if state == "done" else Color("#5A5040"), isz, 2.2), Rect2(r.get_center() - Vector2(isz, isz) * 0.5, Vector2(isz, isz)), false)
		if state == "done":
			var c := Vector2(r.end.x - 5, r.end.y - 8)
			draw_circle(c, 8.5, Color("#2E7A3E"))
			draw_texture_rect(UI.icon("M5 12l5 5 9-10", UI.WHITE_WARM, 10, 4.0), Rect2(c - Vector2(5, 5), Vector2(10, 10)), false)
		var f := UI.font("n900")
		var lines := Cards.name_lines(String(nd.n), f, 11, 80)
		if lines.size() == 1 and f.get_string_size(lines[0], HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x > 80:
			var words := String(nd.n).split(" ")
			lines = PackedStringArray([" ".join(words.slice(0, words.size() / 2)), " ".join(words.slice(words.size() / 2))])
		for k in lines.size():
			var w := f.get_string_size(lines[k], HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x
			draw_string(f, Vector2((80 - w) * 0.5, r.end.y + 15 + k * 12), lines[k], HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.INK)
	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
	func _has_point(p: Vector2) -> bool:
		return UI.finger_rect(size).has_point(p)


## The details panel's card (v5c): 66 x 76, the weapon band, AP hex, icon, name.
class _MiniCard extends Control:
	var n := ""
	var ap := 0
	var icon_path := ""
	static func make(name: String, a: int, icon: String) -> _MiniCard:
		var c := _MiniCard.new()
		c.n = name
		c.ap = a
		c.icon_path = icon
		c.custom_minimum_size = Vector2(66, 80)
		c.mouse_filter = Control.MOUSE_FILTER_IGNORE
		return c
	func _draw() -> void:
		var r := Rect2(Vector2.ZERO, Vector2(66, 76))
		draw_style_box(UI.box(UI.HEX_SHADOW, 10), Rect2(Vector2(0, 4), r.size))
		var sb := UI.box(UI.CREAM_LIGHT, 10)
		sb.set_border_width_all(2)
		sb.border_color = BLUE
		draw_style_box(sb, r)
		draw_rect(Rect2(Vector2(2, 2), Vector2(62, 6)), BLUE)
		var f := UI.font("n900")
		if ap >= 0:   # an upgrade with no AP of its own shows none
			draw_colored_polygon(UI.hex_points(Rect2(Vector2(3, 8), Vector2(18, 21))), UI.DARK)
			var s := str(ap)
			draw_string(f, Vector2(12 - f.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x * 0.5, 23), s, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.CREAM)
		draw_texture_rect(UI.icon(icon_path, BLUE_INK, 22, 2.0), Rect2(Vector2(22, 18), Vector2(22, 22)), false)
		var lines := Cards.name_lines(n, f, 11, 60)
		for k in lines.size():
			var w := f.get_string_size(lines[k], HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x
			draw_string(f, Vector2((66 - w) * 0.5, 54 + k * 12), lines[k], HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.INK)
