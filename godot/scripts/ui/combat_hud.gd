class_name CombatHud
extends Control
## The combat screen's HUD, built from Combat v14 (mockups/combat/Combat-v14-AllyTargets.dc.html) in its
## 844 x 390 layout: the party tray with phase, End and AP pips; camera buttons; the short details panel with
## the card, target, coins and the action button; the hotbar and All actions; the End confirmation;
## HP bars standing over the minis.

var fight: Fight

var _phase_label: Label
var _portraits := VBoxContainer.new()
var _hotbar := HBoxContainer.new()
var _details := VBoxContainer.new()
var _tray_panel: Control
var _details_panel: Control
var _hotbar_row: Control
var _button_box := VBoxContainer.new()
var _all: PanelContainer
var _all_grid := GridContainer.new()
var _all_title: Label
var _confirm: ColorRect
var _confirm_rows := VBoxContainer.new()
var _enemy_pill: PanelContainer
var _bars := Control.new()
var _bar_nodes := {}


func _init(f: Fight) -> void:
	fight = f
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _ready() -> void:
	_bars.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_bars.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_bars)
	_build_tray()
	_build_details()
	_build_hotbar()
	_build_all()
	_build_confirm()
	_build_enemy_pill()


# --- Party tray (left 12, top 12) -----------------------------------------------

func _build_tray() -> void:
	var p := UI.panel(UI.TRAY, 18, UI.TRAY_EDGE, 4, Vector4(6, 8, 6, 8))
	p.custom_minimum_size.x = 72       # CSS width 60 + padding (content-box)
	UI.at(p, 12, 12)
	_tray_panel = p
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	_phase_label = UI.label("Allies", "lilita", 12)
	_phase_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(_phase_label)
	var end := _EndHex.new()
	end.custom_minimum_size = Vector2(38, 47)
	end.pressed.connect(fight.end_phase)
	end.accessibility_name = "End allies' phase"
	var cc := CenterContainer.new()
	cc.add_child(end)
	v.add_child(cc)
	var gap := Control.new()
	gap.custom_minimum_size.y = 0
	v.add_child(gap)
	_portraits.add_theme_constant_override("separation", 4)
	v.add_child(_portraits)
	p.add_child(v)
	add_child(p)


func _refresh_tray() -> void:
	for c in _portraits.get_children():
		_portraits.remove_child(c)
		c.queue_free()
	var party := fight.allies().filter(func(u): return not Fight.is_summon(u))
	var tight: bool = party.size() >= 4 and party.any(func(u): return not fight.summon_of(u).is_empty())
	_portraits.add_theme_constant_override("separation", 1 if tight else 4)   # a full party and a summon still fit the phone's height
	for u in party:
		_portrait(u, tight)
		var s := fight.summon_of(u)
		if not s.is_empty():   # a summon's small portrait hex under its caster's (03, Ethan, Nov 6, 2026)
			_summon_portrait(s)


## One portrait: hex, HP bar and AP pips; tight, a little closer together.
func _portrait(u: Dictionary, tight := false) -> void:
	var on: bool = u == fight.current
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 2 if tight else 3)
	var h := HexShape.make(38, 44, UI.ORANGE if on else UI.RIM, Color(u.color), 4 if on else 3).with_text(u.initial, 16).with_shadow(UI.HEX_SHADOW)
	h.clickable = true
	h.accessibility_name = u.name
	h.tooltip_text = UI.effects_tip(u.name, fight.effects(u))   # DOCS: Long-press on HUD controls
	h.pressed.connect(func():
		fight.select(u)
		_recentre(u))
	if u.down:
		h.modulate.a = 0.5
	var cc := CenterContainer.new()
	cc.add_child(h)
	v.add_child(cc)
	v.add_child(Bar.make(40, 5, Color("#E6DCC8"), UI.GREEN, float(maxi(u.hp, 0)) / u.max_hp, UI.HEX_SHADOW))
	var pips := HBoxContainer.new()
	pips.add_theme_constant_override("separation", 2)
	pips.alignment = BoxContainer.ALIGNMENT_CENTER
	# Bonus AP display (DOCS, combat v4d): always 3 pips; a blue lightning pip is worth 2, shown first.
	var t: int = u.ap + u.bonus
	var bolts := mini(3, maxi(0, t - 3))
	var golds := mini(3, t) - bolts
	for i in 3:
		var col := Color("#3F8FC4") if i < bolts else (UI.GOLD if i < bolts + golds else Color("#6F5A41"))
		var pip := HexShape.make(10, 11.5, col, col, 0)
		if i < bolts:
			pip.with_icon("bolt_fill", Color.WHITE, 8, 2, true)
		pips.add_child(pip)
	v.add_child(pips)
	_portraits.add_child(v)


## A summon's portrait as one short row: its small hex, then its HP bar over its 2 AP pips.
func _summon_portrait(u: Dictionary) -> void:
	var on: bool = u == fight.current
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 4)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	var h := HexShape.make(24, 28, UI.ORANGE if on else UI.RIM, Color(u.color), 3 if on else 2).with_text(u.initial, 12).with_shadow(UI.HEX_SHADOW)
	h.clickable = true
	h.accessibility_name = u.name
	h.tooltip_text = UI.effects_tip(u.name, fight.effects(u))
	h.pressed.connect(func():
		fight.select(u)
		_recentre(u))
	row.add_child(h)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 3)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_child(Bar.make(24, 4, Color("#E6DCC8"), UI.GREEN, float(maxi(u.hp, 0)) / u.max_hp, UI.HEX_SHADOW))
	var pips := HBoxContainer.new()
	pips.add_theme_constant_override("separation", 2)
	for i in Rules.SUMMON_AP:
		var col := UI.GOLD if i < u.ap + u.bonus else Color("#6F5A41")
		pips.add_child(HexShape.make(10, 11.5, col, col, 0))
	v.add_child(pips)
	row.add_child(v)
	_portraits.add_child(row)

class _EndHex extends Control:
	signal pressed

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND

	func _draw() -> void:
		var r := Rect2(Vector2.ZERO, Vector2(38, 44))
		draw_colored_polygon(UI.hex_points(Rect2(Vector2(0, 3), r.size)), UI.ORANGE_EDGE)
		draw_colored_polygon(UI.hex_points(r), UI.ORANGE)
		draw_texture_rect(UI.icon("chevron", UI.WHITE_WARM, 12, 3), Rect2(Vector2(13, 9), Vector2(12, 12)), false)
		var f := UI.font("lilita")
		var w := f.get_string_size("End", HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x
		draw_string(f, Vector2(19 - w * 0.5, 32), "End", HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.WHITE_WARM)

	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
			accept_event()

	func _has_point(point: Vector2) -> bool:
		return UI.finger_rect(size).has_point(point)


# --- The open area and recentring ------------------------------------------------
# No camera buttons: the camera moves by gestures, and tapping a portrait in the tray recentres on that character
# (Ethan, Nov 5, 2026; design/07 -> Menu replaces the nav button).

## The screen rect between the panels, in viewport units: what a fight's opening frames (Fight.open_area). The Dynamic Island's inset moves the panels on a phone.
func open_rect() -> Rect2:
	var left: float = _tray_panel.get_global_rect().end.x
	var right: float = _details_panel.get_global_rect().position.x
	var bottom: float = _hotbar_row.get_global_rect().position.y
	return Rect2(left, 0.0, right - left, bottom)


func _recentre(u: Dictionary) -> void:
	var rig := fight.game.rig
	rig.player_moved = false   # the camera goes back to the game
	rig.ease_to(fight.global_position + u.mini.position, rig.distance, rig.yaw_deg)


# --- Details panel (left 656, top 12, 170 x 268: it ends above the hotbar, design/07 -> Combat screen) --------------

func _build_details() -> void:
	var p := UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(12, 12, 12, 12))
	_details_panel = p
	p.custom_minimum_size = Vector2(170, DETAILS_H)
	p.size = Vector2(170, DETAILS_H)
	p.clip_contents = true
	UI.at_right(p, 656, 12)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	_details.add_theme_constant_override("separation", 2)   # tight, so the fullest states fit the short panel (design/07)
	_details.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(_details)
	_button_box.add_theme_constant_override("separation", 4)
	v.add_child(_button_box)
	p.add_child(v)
	add_child(p)


func _wrap(l: Label) -> Label:
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size.x = 146
	return l


func _refresh_details() -> void:
	for c in _details.get_children() + _button_box.get_children():
		c.get_parent().remove_child(c)
		c.queue_free()
	if fight.phase == "enemies":
		_details.add_child(_wrap(UI.label("Enemies' phase", "lilita", 20)))
		return
	if fight.phase == "over" or fight.current.is_empty():
		return
	var u := fight.current
	var k := fight.card()
	var src: Dictionary = Cards.SRC[k.src]
	var lim: String = {"turn": " · once per turn", "fight": " · once per fight"}.get(k.limit, "")
	var head_text := ("%s · %s%s" % [src.label, "AP not set" if k.ap < 0 else "%d AP" % k.ap, lim]).to_upper()
	if k.limit == "":
		var head := HBoxContainer.new()
		head.add_theme_constant_override("separation", 4)
		head.add_child(UI.label(head_text, "n900", 11, Color(src.ink), 1))
		head.add_child(UI.icon_rect("repeat", Color(src.ink), 12, 2.8))
		_details.add_child(head)
	else:
		_details.add_child(_wrap(UI.label(head_text, "n900", 11, Color(src.ink), 1)))
	# Sizes for the short panel (design/07: everything must fit; text stays at 11 pt or more): name 17, text 11.
	var name := _wrap(UI.label(k.n, "lilita", 17))
	_details.add_child(name)
	# Option B (design/07, Ethan, Nov 5, 2026): the description hides once a target is picked or a result shows, which
	# leaves room for Breath Weapon's targets, the coin line's modifiers, the target's statuses and Lucky.
	var aimed_any: bool = not fight.result.is_empty() or not (fight.ally_target if k.kind == "ally" else fight.target).is_empty() \
			or (k.kind == "breath" and fight.breath_dir >= 0) or (k.kind == "cell" and fight.cell_target != null) or fight.self_done == k.id
	if not aimed_any:
		_details.add_child(_wrap(UI.label(k.desc, "n700", 11, UI.INK_SOFT)))
	if k.get("hp", 0) > 0 and fight.result.is_empty():
		_details.add_child(_wrap(UI.label("Also costs %d HP" % k.hp, "n800", 11, UI.RED)))   # the line that explains the heart (07)
	if k.get("conc", false) and not u.conc.is_empty() and fight.self_done != k.id:
		_details.add_child(_wrap(UI.label("Ends %s" % Cards.ALL[u.conc.id].n, "n800", 11, UI.RED)))   # stops a mistake (07)
	var div := ColorRect.new()
	div.color = Color(UI.HEX_SHADOW, 0.5)
	div.custom_minimum_size = Vector2(146, 2)
	_details.add_child(div)

	var targeting: bool = k.kind in ["attack", "save", "ally", "mark"]
	var has_target: bool = not (fight.ally_target if k.kind == "ally" else fight.target).is_empty()
	var aimed: bool = (k.kind == "breath" and fight.breath_dir >= 0) or (k.kind in ["cell", "arc"] and fight.cell_target != null)
	# Screen text (DOCS: UI -> Screen text): no Move rule sentence and no "pick a target" prompts; the lit
	# hexes, gold rings and AP pips show them. A check shows only the coin line.
	if targeting and not fight.result.is_empty():
		var coins := HFlowContainer.new()   # 22 pt coins that wrap, so 6 or more stay inside the panel
		coins.add_theme_constant_override("h_separation", 3)
		coins.add_theme_constant_override("v_separation", 3)
		coins.custom_minimum_size.x = 146
		for h in fight.result.coins:
			coins.add_child(CoinView.make(h, 22))
		if not fight.result.coins.is_empty():
			_details.add_child(coins)
		var title := HBoxContainer.new()
		title.add_theme_constant_override("separation", 6)
		title.add_child(UI.label(fight.result.title, "lilita", 17, Color("#2E7A3E") if fight.result.good else UI.RED))
		if fight.result.get("lucky", false):   # Lucky reflipped a coin in this flip
			title.add_child(_icon(status_path("clover"), Color("#2E7A3E"), 16))
		_details.add_child(title)
		if fight.result.sub != "":
			_details.add_child(_wrap(UI.label(fight.result.sub, "n700", 12, UI.INK_SOFT)))
	elif targeting and has_target:
		var t: Dictionary = fight.ally_target if k.kind == "ally" else fight.target
		var row := VBoxContainer.new()   # the name over its HP bar, so long names wrap inside the panel
		row.add_theme_constant_override("separation", 2)
		row.add_child(_wrap(UI.label(t.name, "lilita", 14)))
		var fx := fight.status_icons(t)
		if not fx.is_empty():   # the target's statuses, as icons
			var icons := HBoxContainer.new()
			icons.add_theme_constant_override("separation", 3)
			for e in fx:
				icons.add_child(_icon(status_path(e[0]), Color(STATUS_INK.get(e[0], "#33403B")), 14))
			row.add_child(icons)
		var bar := Bar.make(40, 6, UI.DARK, UI.GREEN if t.ally else Color("#C4542A"), float(maxi(t.hp, 0)) / t.max_hp)
		bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		row.add_child(bar)
		_details.add_child(row)
		if k.kind in ["ally", "mark"]:
			_details.add_child(_wrap(UI.label("No roll", "n800", 13)))
		elif k.kind == "attack":
			_details.add_child(_wrap(UI.label(coin_line(u, fight.target, k), "n800", 13)))
		else:
			_details.add_child(_wrap(UI.label("Save: %d coins · %s · needs %d heads%s" % [fight.save_coins(fight.target, u, k.save), k.save, Rules.SAVE_HEADS,
					" · +1 cover" if fight.cover_between(u, fight.target) == "partial" else ""], "n800", 13)))
	elif k.kind == "breath" and (aimed or fight.result.has("rows")):
		_breath_rows(u, k)
	elif k.kind == "cell" and aimed:
		_details.add_child(_wrap(UI.label("No roll", "n800", 13)))
	elif k.kind in ["self", "cell", "arc"] and fight.self_done == k.id:
		_details.add_child(UI.label("Used", "lilita", 18, Color("#2E7A3E")))   # no message: HP bars and effects show it

	# The button (and the note under it when the card can't be used)
	var label := ""
	if targeting and (has_target or not fight.result.is_empty()):
		if k.kind == "ally":
			label = "Cast again" if not fight.result.is_empty() else "Cast"
		elif k.kind == "save":
			label = "Cast"
		elif k.kind == "mark":
			label = "Use"
		else:
			label = "Flip again" if not fight.result.is_empty() else "Flip coins"
	elif k.kind == "self":
		label = "Use"
	elif aimed:   # spells cast; Sweeping Arc flips; the Snare and Dancing Step are used
		label = "Flip coins" if k.kind == "arc" else ("Cast" if k.src in ["elven", "bloodline", "race"] else "Use")
	if label != "":
		var note := fight.cant_use(u, k)
		if (k.kind in ["attack", "save", "mark"] and fight.target.is_empty()) or (k.kind == "ally" and fight.ally_target.is_empty()):
			note = note if note != "" else "Pick a target again"
		var b := TagButton.make(label, 146, 36, 15, true)   # drawn 36 high; taps still get the 44 pt finger area
		b.disabled = note != "" or fight.busy
		b.pressed.connect(fight.press_button)
		_button_box.add_child(b)
		if note != "" and not fight.spent(u, k) and not note.begins_with("_"):   # no use-limit note: the header gives the limit and the card dims (07)
			var nl := _wrap(UI.label(note, "n800", 11, UI.INK_MUTED))
			nl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			_button_box.add_child(nl)


func _icon(path: String, col: Color, px: float) -> TextureRect:
	var r := TextureRect.new()
	r.texture = UI.icon(path, col, px, 2.4)
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	r.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	return r


## The attack's coin line with what changed the coins: Bless, cover, and the long shot when there are fewer coins than
## heads needed (design/03 -> Coin checks, Combat -> Cover). Forge, glow and acid coins are in the count.
func coin_line(u: Dictionary, t: Dictionary, k: Dictionary) -> String:
	var n: int = fight.attack_coins(u, t, k)
	var need: int = fight.heads_needed(t, u, k) if not t.is_empty() else Rules.HEADS_TO_HIT
	var ab: String = k.get("ab", u.ability)
	var mods := ""
	if u.blessed:
		mods += " · +1 Bless"
	if not t.is_empty() and fight.cover_between(u, t) == "partial" and not k.get("pierce", false):
		mods += " · −%d cover" % Rules.COVER_COINS
	if n < need:   # the long shot: 1 coin, heads in a row
		return "Long shot · %s · %d heads in a row%s" % [ab, need + (need - n), mods]
	return "%d coins · %s · needs %d heads%s" % [n, ab, need, mods]


## Breath Weapon: each one in the line, with their save; after the cast, their coins and what they took.
func _breath_rows(u: Dictionary, k: Dictionary) -> void:
	var rows: Array = fight.result.get("rows", [])
	if rows.is_empty():
		var partial := false
		for c: Vector2i in fight.breath_line(u, fight.breath_dir):
			var t := fight.unit_at(c)
			if not t.is_empty() and not t.down and t != u:
				rows.append({name = t.name, line = "Save: %d coins · DEX" % fight.save_coins(t, {}, "DEX", partial)})
			if fight.cover.get(c, "") == "partial":
				partial = true
	for r: Dictionary in rows:
		var box := VBoxContainer.new()
		box.add_theme_constant_override("separation", 1)
		box.add_child(_wrap(UI.label(r.name, "lilita", 14)))   # as the target row's name
		if r.has("coins"):
			var line := HBoxContainer.new()
			line.add_theme_constant_override("separation", 3)
			for h in r.coins:
				line.add_child(CoinView.make(h, 20))
			line.add_child(UI.label("  -%d" % r.dmg, "lilita", 14, UI.RED if r.dmg > 0 else UI.INK_SOFT))
			if r.get("lucky", false):
				line.add_child(_icon(status_path("clover"), Color("#2E7A3E"), 14))
			box.add_child(line)
		else:
			box.add_child(_wrap(UI.label(r.line, "n800", 13)))   # as the coin line
		_details.add_child(box)


# --- Hotbar (top 286): 7 slots and All actions, from the party tray to the details panel's right edge --------------

const DETAILS_H := 268.0   # the panel's bottom stays 6 above the hotbar's lifted card
const BAR_TOP := 286.0
const BAR_LEFT := 95.0     # 11 past the party tray
const CARD_W := 74.0


## The bar spans from BAR_LEFT to the details panel's right edge, which moves with the screen's width and safe areas:
## the gaps share what's left (4 to 24 each); on a very wide screen the bar sits centred in that span.
func _layout_bar() -> void:
	var right: float = _details_panel.position.x + _details_panel.size.x
	var gap := clampf((right - BAR_LEFT - Rules.HOTBAR_SLOTS * CARD_W - 56.0) / Rules.HOTBAR_SLOTS, 4.0, 24.0)
	var width: float = Rules.HOTBAR_SLOTS * CARD_W + Rules.HOTBAR_SLOTS * gap + 56.0
	_hotbar.add_theme_constant_override("separation", int(gap))
	_hotbar_row.add_theme_constant_override("separation", int(gap))
	_hotbar_row.position = Vector2(BAR_LEFT + maxf(0.0, (right - BAR_LEFT - width) * 0.5), BAR_TOP)


func _build_hotbar() -> void:
	var row := HBoxContainer.new()
	_hotbar_row = row
	UI.at(row, BAR_LEFT, BAR_TOP)
	row.custom_minimum_size = Vector2(0, 92)
	row.add_child(_hotbar)
	var all := UI.FingerButton.new()
	all.text = "All actions"
	all.icon = UI.icon("grid", UI.CREAM, 22, 2)
	all.expand_icon = false
	all.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
	all.vertical_icon_alignment = VERTICAL_ALIGNMENT_TOP
	all.custom_minimum_size = Vector2(56, 84)
	all.add_theme_constant_override("icon_max_width", 22)
	all.size_flags_vertical = Control.SIZE_SHRINK_END
	all.add_theme_font_override("font", UI.font("n900"))
	all.add_theme_font_size_override("font_size", 11)
	all.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	all.add_theme_constant_override("h_separation", 4)
	for s in ["normal", "hover", "pressed", "focus"]:
		all.add_theme_stylebox_override(s, UI.box(UI.DARK, 10, UI.DARK_EDGE, 4, Vector4(4, 14, 4, 10)))
	for s in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		all.add_theme_color_override(s, UI.CREAM)
	all.pressed.connect(func(): _all.visible = true; _refresh_all())
	row.add_child(all)
	add_child(row)


func _card_button(id: String, big: bool) -> Control:
	var u := fight.current
	var k := Cards.get_card(id, u.weapon)
	var src: Dictionary = Cards.SRC[k.src]
	var on: bool = id == fight.sel
	var dim := fight.spent(u, k)
	if big:
		var c := _HotCard.new()
		c.setup(k, src, on, dim)
		c.pressed.connect(fight.pick_card.bind(id))
		c.tooltip_text = "%s, %s card, %s" % [k.n, src.label, "AP cost not set" if k.ap < 0 else "%d AP" % k.ap]
		return c
	var b := _AllCard.new()
	b.setup(k, src, on, dim, " · on hotbar" if id in u.hot else "")
	b.pressed.connect(func():
		_all.visible = false
		fight.pick_card(id))
	return b


func _refresh_hotbar() -> void:
	for c in _hotbar.get_children():
		_hotbar.remove_child(c)
		c.queue_free()
	if fight.current.is_empty():
		return
	# Each card keeps its slot: Edit hotbar's `hot_slots` ("" for a cleared slot) when there are any, else `hot` in order;
	# empty slots draw as a faint outline, so the bar always has Rules.HOTBAR_SLOTS places.
	var slots: Array = fight.current.member.get("hot_slots", fight.current.hot)
	for i in Rules.HOTBAR_SLOTS:
		var id: String = slots[i] if i < slots.size() else ""
		_hotbar.add_child(_card_button(id, true) if id != "" else _EmptySlot.new())


## A cleared hotbar slot: the card's outline, faint and dashed. PLACEHOLDER look.
class _EmptySlot extends Control:
	func _init() -> void:
		custom_minimum_size = Vector2(74, 92)
		mouse_filter = Control.MOUSE_FILTER_IGNORE

	func _draw() -> void:
		var r := Rect2(Vector2(1, 9), Vector2(72, 82))
		var col := Color(UI.CREAM_LIGHT, 0.7)
		var pts := [r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y), r.position]
		for k in 4:
			var a: Vector2 = pts[k]
			var b: Vector2 = pts[k + 1]
			var n := int(a.distance_to(b) / 9.0)
			for j in n:
				draw_line(a.lerp(b, float(j) / n), a.lerp(b, (j + 0.55) / n), col, 2.0)


## A hotbar card (74 x 84): colour band, AP hex, repeat icon or once-per-fight tag, icon and name.
class _HotCard extends Control:
	signal pressed
	var k: Dictionary
	var src: Dictionary
	var on := false
	var dim := false

	func setup(card: Dictionary, s: Dictionary, selected: bool, spent: bool) -> void:
		k = card
		src = s
		on = selected
		dim = spent
		custom_minimum_size = Vector2(74, 92)
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		modulate.a = 0.45 if dim else 1.0

	func _draw() -> void:
		var y := 0.0 if on else 8.0           # the picked card lifts 8 px
		var r := Rect2(Vector2(0, y), Vector2(74, 84))
		draw_style_box(UI.box(UI.HEX_SHADOW, 10), Rect2(r.position + Vector2(0, 4), r.size))
		var face := UI.box(UI.CREAM_LIGHT, 10)
		face.border_color = UI.ORANGE if on else Color(src.band)
		face.set_border_width_all(3 if on else 2)
		draw_style_box(face, r)
		draw_rect(Rect2(r.position + Vector2(2.5, 2.5), Vector2(69, 6)), Color(src.band))
		draw_colored_polygon(UI.hex_points(Rect2(r.position + Vector2(4, 9), Vector2(20, 23))), UI.DARK)
		var f := UI.font("n900")
		var ap := Cards.ap_text(k)
		draw_string(f, r.position + Vector2(14 - f.get_string_size(ap, 0, -1, 11).x * 0.5, 25), ap, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.CREAM)
		if k.limit == "":
			draw_texture_rect(UI.icon("repeat", Color("#2E6B3A"), 16, 2.6), Rect2(r.position + Vector2(54, 10), Vector2(16, 16)), false)
		elif k.limit == "fight":
			draw_style_box(UI.box(Color("#843E0E"), 8), Rect2(r.position + Vector2(44, 9), Vector2(27, 16)))   # 7.4:1 under the 11 pt "1"
			draw_string(f, r.position + Vector2(48, 21), "1", HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.WHITE_WARM)
			draw_texture_rect(UI.icon("fight_once", UI.WHITE_WARM, 10, 2.6), Rect2(r.position + Vector2(57, 12), Vector2(10, 10)), false)
		if k.get("hp", 0) > 0:   # a blood art's HP cost: a small heart with the number, beside the AP hex (Ethan, Nov 6, 2026)
			draw_texture_rect(UI.icon(HP_HEART, UI.RED, 14, 2.4), Rect2(r.position + Vector2(25, 12), Vector2(14, 14)), false)
			draw_string(f, r.position + Vector2(40, 24), str(k.hp), HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.RED)
		draw_texture_rect(UI.icon(k.icon, Color(src.icon_ink), 26, 2), Rect2(r.position + Vector2(24, 20), Vector2(26, 26)), false)
		var parts := Cards.name_lines(k.n, f, 11, 64)
		var text_y := 60.0 if parts.size() == 1 else 56.0
		for i in parts.size():
			var w := f.get_string_size(parts[i], 0, -1, 11).x
			draw_string(f, r.position + Vector2(37 - w * 0.5, text_y + i * 12), parts[i], HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.INK)

	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
			accept_event()

	func _has_point(point: Vector2) -> bool:
		return UI.finger_rect(size).has_point(point)


const HP_HEART := "M12 21s-7.5-4.6-9.5-10A5 5 0 0 1 12 6.5 5 5 0 0 1 21.5 11c-2 5.4-9.5 10-9.5 10z"


## A card in the All actions list (48 tall): AP hex, icon, name and source.
class _AllCard extends Control:
	signal pressed
	var k: Dictionary
	var src: Dictionary
	var on := false
	var note := ""

	func setup(card: Dictionary, s: Dictionary, selected: bool, spent: bool, hot_note: String) -> void:
		k = card
		src = s
		on = selected
		note = hot_note
		custom_minimum_size = Vector2(160, 48)
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		modulate.a = 0.45 if spent else 1.0

	func _draw() -> void:
		var r := Rect2(Vector2.ZERO, size)
		var face := UI.box(UI.CREAM_LIGHT, 10)
		face.border_color = UI.ORANGE if on else Color(src.band)
		face.set_border_width_all(2)
		draw_style_box(face, r)
		draw_colored_polygon(UI.hex_points(Rect2(Vector2(8, 12.5), Vector2(20, 23))), UI.DARK)
		var f := UI.font("n900")
		var ap := Cards.ap_text(k)
		draw_string(f, Vector2(18 - f.get_string_size(ap, 0, -1, 11).x * 0.5, 28), ap, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.CREAM)
		draw_texture_rect(UI.icon(k.icon, Color(src.icon_ink), 20, 2), Rect2(Vector2(36, 14), Vector2(20, 20)), false)
		draw_string(f, Vector2(64, 22), k.n, HORIZONTAL_ALIGNMENT_LEFT, size.x - 70, 12, UI.INK)
		draw_string(UI.font("n700"), Vector2(64, 37), src.label + note, HORIZONTAL_ALIGNMENT_LEFT, size.x - 70, 11, UI.INK_SOFT)

	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
			accept_event()

	func _has_point(point: Vector2) -> bool:
		return UI.finger_rect(size).has_point(point)


# --- All actions (left 90, top 12, 524 x 262) ---------------------------------------

func _build_all() -> void:
	_all = UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(12, 12, 12, 12))
	_all.custom_minimum_size = Vector2(524, 262)
	UI.at(_all, 90, 12)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 8)
	var head := HBoxContainer.new()
	_all_title = UI.label("All actions", "lilita", 18)
	head.add_child(_all_title)
	var sp := Control.new()
	sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(sp)
	var edit := TagButton.make("Edit hotbar", 120, 36, 14)
	edit.cut = 10
	edit.icon = UI.icon("M4 20h4L19 9l-4-4L4 16z M13 7l4 4", UI.WHITE_WARM, 16, 2.4)
	edit.pressed.connect(func(): _all.visible = false; ActionCards.open_from_fight(fight))
	head.add_child(edit)
	var close := HexShape.make(30, 30, Color(0, 0, 0, 0), Color(0, 0, 0, 0), 0).with_icon("close", UI.INK_SOFT, 16, 2.6)
	close.clickable = true
	close.pressed.connect(func(): _all.visible = false)
	head.add_child(close)
	v.add_child(head)
	_all_grid.columns = 3
	_all_grid.add_theme_constant_override("h_separation", 6)
	_all_grid.add_theme_constant_override("v_separation", 6)
	v.add_child(_all_grid)
	_all.add_child(v)
	_all.visible = false
	add_child(_all)


func _refresh_all() -> void:
	for c in _all_grid.get_children():
		_all_grid.remove_child(c)
		c.queue_free()
	if fight.current.is_empty():
		return
	_all_title.text = "All actions · " + fight.current.name
	for id in fight.current.cards:
		_all_grid.add_child(_card_button(id, false))


# --- End confirmation and the enemies' phase ---------------------------------------

func _build_confirm() -> void:
	_confirm = ColorRect.new()
	_confirm.color = Color(0.141, 0.188, 0.172, 0.55)
	_confirm.set_anchors_preset(Control.PRESET_FULL_RECT)
	_confirm.mouse_filter = Control.MOUSE_FILTER_STOP
	var cc := CenterContainer.new()
	cc.set_anchors_preset(Control.PRESET_FULL_RECT)
	_confirm.add_child(cc)
	var p := UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(16, 16, 16, 16))
	p.custom_minimum_size.x = 300
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	v.add_child(UI.label("End allies' phase?", "lilita", 20))
	var t := UI.label("Unspent AP is lost when the phase ends.", "n700", 13, UI.INK_SOFT)
	t.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	t.custom_minimum_size.x = 268
	v.add_child(t)
	_confirm_rows.add_theme_constant_override("separation", 6)
	v.add_child(_confirm_rows)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var keep := UI.FingerButton.new()
	keep.text = "Keep playing"
	keep.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	keep.custom_minimum_size.y = 44
	keep.add_theme_font_override("font", UI.font("lilita"))
	keep.add_theme_font_size_override("font_size", 14)
	var ks := UI.box(UI.CREAM_LIGHT, 12)
	ks.border_color = UI.RIM
	ks.set_border_width_all(2)
	for s in ["normal", "hover", "pressed", "focus"]:
		keep.add_theme_stylebox_override(s, ks)
	for s in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		keep.add_theme_color_override(s, UI.INK)
	keep.pressed.connect(hide_confirm)
	row.add_child(keep)
	var end := TagButton.make("End phase", 130, 44, 14)
	end.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	end.pressed.connect(fight.confirm_end)
	row.add_child(end)
	var gap := Control.new()
	gap.custom_minimum_size.y = 0
	v.add_child(gap)
	v.add_child(row)
	p.add_child(v)
	cc.add_child(p)
	_confirm.visible = false
	add_child(_confirm)


func show_confirm(left: Array) -> void:
	for c in _confirm_rows.get_children():
		_confirm_rows.remove_child(c)
		c.queue_free()
	for u in left:
		var h := HBoxContainer.new()
		h.add_theme_constant_override("separation", 8)
		h.add_child(HexShape.make(26, 30, Color(u.color), Color(u.color), 0).with_text(u.initial, 13))
		var n := UI.label(u.name, "n800", 13)
		n.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		n.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		n.size_flags_vertical = Control.SIZE_FILL
		h.add_child(n)
		var a := UI.label("%d AP%s" % [fight.ap_left(u), " (%d bonus)" % u.bonus if u.bonus > 0 else ""], "n900", 12, Color("#5A3A05"))
		a.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		a.size_flags_vertical = Control.SIZE_FILL
		h.add_child(a)
		_confirm_rows.add_child(h)
	_confirm.visible = true


func hide_confirm() -> void:
	_confirm.visible = false


func confirm_open() -> bool:
	return _confirm.visible


## While the foes act, a pill at the top says so (the mockup shows a modal "Enemies' phase" card with
## "[Enemy actions play out on the board]"; here they really do, so the board stays visible).
func _build_enemy_pill() -> void:
	_enemy_pill = UI.panel(UI.CREAM, 20, UI.CREAM_EDGE, 4, Vector4(18, 0, 18, 0))
	_enemy_pill.custom_minimum_size.y = 40
	var l := UI.label("Enemies' phase", "lilita", 17)
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_enemy_pill.add_child(l)
	_enemy_pill.visible = false
	add_child(_enemy_pill)


# --- HP bars and floating numbers over the minis -----------------------------------

func _process(_delta: float) -> void:
	if not visible:
		return
	_enemy_pill.position = Vector2(368 - _enemy_pill.size.x * 0.5, 14)
	_layout_bar()
	var cam := fight.game.rig.camera
	for u in fight.units:
		var key: int = u.mini.get_instance_id()
		var node: Control = _bar_nodes.get(key)
		if node == null:
			node = _make_bar(u)
			_bars.add_child(node)
			_bar_nodes[key] = node
		var world: Vector3 = u.mini.global_position + Vector3(0, 1.75, 0)
		node.visible = not (u.down and not u.ally) and not cam.is_position_behind(world)
		node.global_position = cam.unproject_position(world) - Vector2(node.size.x * 0.5, node.size.y)  # screen coordinates
		var bar: Bar = node.get_meta("bar")
		var shown: Dictionary = u
		if u.decoy == "mirror":   # a copy looks like you, HP bar too
			for o in fight.units:
				if o.name == u.copy_of and o.decoy == "" and not Fight.is_summon(o):
					shown = o
		bar.value = float(maxi(shown.hp, 0)) / shown.max_hp
		var fx: Array = fight.status_icons(u).map(func(e): return e[0])
		if fx != node.get_meta("fx_key", []):
			node.set_meta("fx_key", fx)
			fill_status(node.get_meta("fx"), fx)
	for key in _bar_nodes.keys():
		if not fight.units.any(func(u): return u.mini.get_instance_id() == key):
			_bar_nodes[key].queue_free()
			_bar_nodes.erase(key)


## Above each mini: its letter (as on the mockup's tokens) and a 24 x 4 HP bar (Combat v14).
func _make_bar(u: Dictionary) -> Control:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 2)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var plate := HexShape.make(17, 19.5, UI.RED if not u.ally else Color("#C9A97A"), UI.RED if not u.ally else Color(u.color), 0 if not u.ally else 1.5)
	plate.with_text(u.initial, 11, UI.WHITE_WARM if not u.ally else UI.INK)
	var cc := CenterContainer.new()
	cc.add_child(plate)
	v.add_child(cc)
	var bar := Bar.make(24, 4, UI.DARK, UI.GREEN if u.ally else Color("#C4542A"))
	v.add_child(bar)
	v.set_meta("bar", bar)
	var fx := HBoxContainer.new()   # status chips beside the hex, level with it, outside the marker's box so the hex stays centred over the mini
	fx.add_theme_constant_override("separation", 2)
	fx.position = Vector2(plate.size.x + 2, (plate.size.y - STATUS_CHIP) * 0.5)
	plate.add_child(fx)
	fx.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.set_meta("fx", fx)
	v.reset_size()
	return v


## A status chip's size across. PLACEHOLDER size.
const STATUS_CHIP := 12.0
const STATUS_CHIPS_SHOWN := 3   # then "+N" (07 -> Combat)


## A marker's status icons (`fx`: status_icons names) as chips: up to 3, then "+N" (07 -> Combat; Ethan, Nov 7, 2026).
func fill_status(holder: Control, fx: Array) -> void:
	for c in holder.get_children():
		holder.remove_child(c)
		c.queue_free()
	for k in mini(fx.size(), STATUS_CHIPS_SHOWN):
		holder.add_child(StatusChip.make(STATUS_CHIP, fx[k], Color(STATUS_INK.get(fx[k], "#33403B"))))
	if fx.size() > STATUS_CHIPS_SHOWN:
		holder.add_child(StatusChip.make(STATUS_CHIP, "", UI.INK, fx.size() - STATUS_CHIPS_SHOWN))


## An attack's coins over who's flipping, one at a time (design/07): stops at the heads it needs, then holds so the result can be read. Returns the coins shown.
func flip_coins(u: Dictionary, coins: Array[bool], need: int, step: float) -> Array[bool]:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 3)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(row)
	var cam := fight.game.rig.camera
	var shown: Array[bool] = []
	var heads := 0
	var size_ := 24.0
	var at := cam.unproject_position(u.mini.global_position + Vector3(0, 2.4, 0))
	var count := coins.size()
	row.global_position = at - Vector2((size_ + 3.0) * count * 0.5, size_)
	for h: bool in coins:
		var coin := CoinView.make(h, size_)
		coin.pivot_offset = Vector2(size_, size_) * 0.5
		coin.scale = Vector2(0.05, 1.0)
		row.add_child(coin)
		var tw := create_tween()
		tw.tween_property(coin, "scale:x", 1.0, step * 0.8).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		await get_tree().create_timer(step).timeout
		shown.append(h)
		heads += 1 if h else 0
		if heads >= need:
			break
	await get_tree().create_timer(Rules.COIN_HOLD).timeout
	row.queue_free()
	return shown


## An icon rising over a mini, as float_text: Lucky's clover when it fires (design/07: icons, not words). PLACEHOLDER icon.
func float_icon(u: Dictionary, icon: String) -> void:
	var t := TextureRect.new()
	t.texture = UI.icon(status_path(icon), Color("#2E7A3E"), 26, 2.6)
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(t)
	var cam := fight.game.rig.camera
	t.global_position = cam.unproject_position(u.mini.global_position + Vector3(0, 2.2, 0)) - Vector2(13, 30)
	var tw := create_tween().set_parallel()
	tw.tween_property(t, "position:y", t.position.y - 24, 1.0)
	tw.tween_property(t, "modulate:a", 0.0, 0.6).set_delay(0.6)
	tw.chain().tween_callback(t.queue_free)


## Status and Lucky icons: the HUD's own, else the creator's, else these PLACEHOLDER paths.
const STATUS_PATHS := {"mark": "M12 3v4 M12 17v4 M3 12h4 M17 12h4 M12 8a4 4 0 1 0 0 8a4 4 0 1 0 0-8", "snare": "M4 18h16 M7 18l5-9 5 9 M12 9V5", "lock": "M7 11V8a5 5 0 0 1 10 0v3 M5 11h14v9H5z", "acid": "M12 3c3 5 6 8 6 12a6 6 0 0 1-12 0c0-4 3-7 6-12z M9 15h6"}
const STATUS_INK := {"mark": "#B3261E", "snare": "#5A4528", "spark": "#B07A12", "moon": "#3E5A70", "drop": "#B3261E", "skull": "#3E7A2E", "snow": "#3F8FC4", "acid": "#4F7A12", "lock": "#33403B"}


static func status_path(n: String) -> String:
	return Icons.PATHS.get(n, CreatorData.PI.get(n, STATUS_PATHS.get(n, n)))


func float_text(u: Dictionary, text: String, hurt: bool, heal := false) -> void:
	var l := UI.label(text, "lilita", 18, Color("#2E7A3E") if heal else (UI.RED if hurt else UI.INK_SOFT))
	l.add_theme_constant_override("outline_size", 6)
	l.add_theme_color_override("font_outline_color", UI.CREAM_LIGHT)
	add_child(l)
	var cam := fight.game.rig.camera
	var p := cam.unproject_position(u.mini.global_position + Vector3(0, 2.2, 0))
	l.global_position = p - Vector2(20, 10)
	var tw := create_tween().set_parallel()
	tw.tween_property(l, "position:y", l.position.y - 24, 1.0)
	tw.tween_property(l, "modulate:a", 0.0, 0.6).set_delay(0.5)
	tw.chain().tween_callback(l.queue_free)


func refresh() -> void:
	_phase_label.text = {"allies": "Allies", "enemies": "Enemies", "over": "Done"}.get(fight.phase, "Allies")
	_enemy_pill.visible = fight.phase == "enemies"
	_refresh_tray()
	_refresh_details()
	_refresh_hotbar()
	if _all.visible:
		_refresh_all()
