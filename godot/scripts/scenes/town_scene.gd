class_name TownScene
extends Control
## The town, from Town v9 (mockups/town/Town-v9-SwapDetails.dc.html; design/07 -> Town screen): a scene with Shop and Inn
## as option cards, each opening its own panel.
##
## The square and inn are Terrain Art's scenes (TownStage), each shown on its own with the map hidden.
##
## PLACEHOLDERS: every keeper's line and the town's name, as bracketed in the mockup (design/characters/Places.md has the
## slots, not yet written); the inn's price and the stock (TownShop). No Quest board (no quests yet), Swap party (nobody's
## waiting) or Injuries chip (no injuries yet).

const INN_PRICE := 5                   # PLACEHOLDER: design/04 -> open question, gold prices
const SHOP_C := Color("#B0672A")
const INN_C := Color("#3F6FA8")
const NIGHT_C := Color("#14203A")

var game: Game
var tile: Vector2i
var mode := ""                         # "", "shop", "inn"
var head := SceneUI.Head.new()
var stage: TownStage
var _row: HBoxContainer
var _gold: Control
var _shop: TownShop
var _rested := false
var _phase := ""                       # the inn's rest: "", "revel", "night", "results"
var _banter: Array = []
var _step := 0
var _press := {}
var _mugs: Array[Control] = []


func _init(g: Game, t: Vector2i) -> void:
	game = g
	tile = t
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	game.busy = true
	game.pick(null)
	game.hud.set_scene(true)
	add_child(head)
	head.fit(size.x - 160.0 - 96.0)
	stage = TownStage.new(game)
	game.add_child(stage)
	await _fade_cut(func():
		stage.begin()
		stage.show_scene("square", "none", _is_night()))
	_show_square()


func _is_night() -> bool:
	return Rules.is_night(game.minute)


## A short fade over a change of scene, as the board swaps.
func _fade_cut(swap: Callable) -> void:
	game._fade_to(1.0, 0.2)
	await get_tree().create_timer(0.2).timeout
	swap.call()
	game._fade_to(0.0, 0.25)


func town_name() -> String:
	if tile == Rules.START_TILE and game.run != null and game.run.background in ["criminal", "folk_hero"]:
		return RunSetup.BACKGROUNDS[game.run.background].place
	return "[Town name]"


func _clear_row() -> void:
	if _row:
		_row.queue_free()
	_row = SceneUI.card_row()
	add_child(_row)
	_row.modulate.a = 0.0
	_row.create_tween().tween_property(_row, "modulate:a", 1.0, 0.25)


func _refresh_gold() -> void:
	if _gold:
		_gold.queue_free()
	_gold = SceneUI.gold_pill(game.gold)
	add_child(_gold)


func _show_square() -> void:
	if mode == "inn":
		await _fade_cut(func(): stage.show_scene("square", "none", _is_night()))
	elif mode == "shop":
		stage.show_scene("square", "none", _is_night())
	mode = ""
	_refresh_gold()
	head.say(town_name(), "Market town", "[Town greeting]", Color("#E2C79A"), Color("#6B4C35"), SceneUI.ICONS.house)
	_clear_row()
	var shop := SceneUI.card("TOWN", SHOP_C, SceneUI.ICONS.shop, SHOP_C, "Shop")
	shop.pressed.connect(_open_shop)
	_row.add_child(shop)
	var inn := SceneUI.card("TOWN", INN_C, SceneUI.ICONS.inn, INN_C, "Inn")
	inn.pressed.connect(_open_inn)
	_row.add_child(inn)
	var leave := SceneUI.dark_card("Leave")
	leave.pressed.connect(_leave)
	_row.add_child(leave)


func _leave() -> void:
	await _fade_cut(func():
		stage.finish()
		game.hud.set_scene(false)
		game.busy = false
		game._refresh())
	queue_free()


# --- Shop ----------------------------------------------------------------------------

func _open_shop() -> void:
	mode = "shop"
	stage.show_scene("square", "shop", _is_night())
	head.say("[Shopkeeper]", "%s · Shop" % town_name(), "[Shopkeeper line]", Color("#F2D8B0"), SHOP_C, SceneUI.ICONS.person)
	_row.queue_free()
	_row = null
	_shop = TownShop.new(self)
	add_child(_shop)
	_shop.closed.connect(func():
		_shop.queue_free()
		_show_square())


# --- Inn: a night at the bar (v2e) -----------------------------------------------------

func _open_inn() -> void:
	await _fade_cut(func(): stage.show_scene("inn", "seats", _is_night()))
	mode = "inn"
	_phase = ""
	_inn_head("[Innkeeper morning line]" if _rested else "[Innkeeper line]")
	_inn_cards()


func _inn_head(line: String) -> void:
	head.say("[Innkeeper]", "%s · Inn" % town_name(), line, Color("#C9DCEF"), INN_C, SceneUI.ICONS.person)


func _inn_cards() -> void:
	_clear_row()
	var rest := SceneUI.card("Rested" if _rested else str(INN_PRICE), UI.INK_MUTED if _rested else INN_C, SceneUI.ICONS.inn, INN_C, "Rest the night")
	rest.coin = not _rested
	rest.dim = _rested
	rest.pressed.connect(_rest_pressed)
	_row.add_child(rest)
	var back := SceneUI.dark_card("Back")
	back.pressed.connect(_show_square)
	_row.add_child(back)


func _rest_pressed() -> void:
	if _rested or _phase != "":
		return
	if not game.spend(INN_PRICE):
		_inn_head("[Innkeeper can't afford line]")
		return
	_refresh_gold()
	_phase = "revel"
	_row.queue_free()
	_row = null
	_banter = []
	for k in range(1, game.party.size()):
		var who: String = game.party[k].name
		_banter.append({"who": k, "line": Rules.BAR_LINES.get(who, "[%s's bar line]" % who)})
	_banter.append({"who": 0, "line": "[Hero toast line]"})
	_step = 0
	_show_mugs()
	_say_banter()


func _say_banter() -> void:
	var b: Dictionary = _banter[_step]
	var m: Dictionary = game.party[b.who]
	head.say(m.name, "At the bar", b.line, Color(m.color), UI.INK, "", m.initial, "", true)
	stage.hop(b.who)


func _show_mugs() -> void:
	for i in game.party.size():
		var mug := CUI.Dot.make(22, Color("#F2C14E"), "", 0)
		mug.position = Vector2(12 + 6 + 38 - 13, 12 + 8 - 4 + i * 57.0)
		add_child(mug)
		var ic := UI.icon_rect(SceneUI.ICONS.mug, Color("#5A3A05"), 14, 2.4)
		UI.at(ic, 4, 4)
		mug.add_child(ic)
		_mugs.append(mug)


func _unhandled_input(event: InputEvent) -> void:
	if _phase == "revel" and SceneUI.is_scene_tap(event, _press):
		_next_banter()


func next_line() -> void:
	if _phase == "revel":
		_next_banter()


func _next_banter() -> void:
	_step += 1
	if _step < _banter.size():
		_say_banter()
		return
	_phase = "night"
	for m in _mugs:
		m.queue_free()
	_mugs.clear()
	_inn_head("[Innkeeper goodnight line]")
	_night()


func _night() -> void:
	var before: Array = game.party.map(func(m): return float(m.hp) / m.max_hp)
	var dark := ColorRect.new()
	dark.color = NIGHT_C
	dark.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dark.set_anchors_preset(Control.PRESET_FULL_RECT)
	dark.modulate.a = 0.0
	game.ui.add_child(dark)
	game.ui.move_child(dark, 0)
	var moon := UI.icon_rect(SceneUI.ICONS.moon, Color("#F2E3B0"), 48, 2.0)
	moon.position = Vector2(size.x * 0.5 - 24, 150)
	moon.modulate.a = 0.0
	add_child(moon)
	stage.set_night(true)
	var tw := create_tween()
	tw.tween_property(dark, "modulate:a", 0.4, 1.1).set_ease(Tween.EASE_IN_OUT)
	tw.parallel().tween_property(moon, "modulate:a", 1.0, 0.8).set_delay(0.4)
	tw.tween_interval(1.2)
	tw.tween_property(dark, "modulate:a", 0.0, 0.6)
	tw.parallel().tween_property(moon, "modulate:a", 0.0, 0.4)
	await tw.finished
	dark.queue_free()
	moon.queue_free()
	game.rest_here()
	stage.set_night(_is_night())
	_rested = true
	_phase = "results"
	_inn_head("[Innkeeper morning line]")
	_results(before)


## v7: the rest's results in the middle of the screen, the party's HP filling and ticks on what it did.
func _results(before: Array) -> void:
	var cc := CenterContainer.new()
	cc.set_anchors_preset(Control.PRESET_FULL_RECT)
	cc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(cc)
	var p := UI.panel(UI.CREAM, 20, UI.CREAM_EDGE, 5, Vector4(14, 12, 14, 14))
	p.custom_minimum_size.x = 520
	var v := CUI.vbox(10)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	var title := UI.label("Rested", "lilita", 20, UI.INK, 0, 1.0)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(title)
	var tray := UI.panel(UI.TRAY, 18, Color(0, 0, 0, 0), 0, Vector4(18, 10, 18, 10))
	tray.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	tray.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var who := CUI.hbox(14)
	for i in game.party.size():
		var m: Dictionary = game.party[i]
		var col := CUI.vbox(5)
		var hx := HexShape.make(52, 60, UI.RIM, Color(m.color), 3).with_text(m.initial, 21).with_shadow(UI.TRAY_EDGE)
		hx.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		col.add_child(hx)
		var bar := HpBar.new()
		bar.custom_minimum_size = Vector2(56, 7)
		bar.fill = before[i]
		col.add_child(bar)
		who.add_child(col)
		bar.create_tween().tween_property(bar, "fill", 1.0, 1.1).set_delay(0.25).set_ease(Tween.EASE_OUT)
	tray.add_child(who)
	v.add_child(tray)
	var chips := CUI.hbox(6)
	chips.alignment = BoxContainer.ALIGNMENT_CENTER
	for c: Array in [[SceneUI.ICONS.heart, "Heal"], [SceneUI.ICONS.clock, "+8 hours"], [SceneUI.ICONS.cards, "Reshuffle deck"], [SceneUI.ICONS.cards, "Hand to 7"]]:
		chips.add_child(_chip(c[0], c[1]))
	v.add_child(chips)
	var on := CUI.Tap.new("Carry on")
	on.custom_minimum_size = Vector2(120, 40)
	on.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	on.draw.connect(func(): on.draw_style_box(UI.box(UI.DARK, 20), Rect2(Vector2.ZERO, on.size)))
	var on_l := UI.label("Carry on", "n900", 13, UI.CREAM)
	on_l.set_anchors_preset(Control.PRESET_FULL_RECT)
	on_l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	on_l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	on.add_child(on_l)
	on.pressed.connect(func():
		cc.queue_free()
		_phase = ""
		_inn_cards())
	v.add_child(on)
	p.add_child(v)
	cc.add_child(p)


## A chip that turns from its icon to a green tick as the bars fill.
func _chip(icon: String, text: String) -> Control:
	var p := UI.panel(UI.SAND, 14, Color(0, 0, 0, 0), 0, Vector4(4, 0, 11, 0))
	p.custom_minimum_size.y = 28
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var h := CUI.hbox(6)
	var dot := CUI.Dot.make(20, UI.INK_MUTED, icon, 12)
	h.add_child(dot)
	var l := UI.label(text, "n900", 12, UI.INK)
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(l)
	p.add_child(h)
	get_tree().create_timer(0.25).timeout.connect(func():
		if is_instance_valid(p):
			p.add_theme_stylebox_override("panel", UI.box(Color("#DDEBD5"), 14, Color(0, 0, 0, 0), 0, Vector4(4, 0, 11, 0)))
			dot.col = Color("#4E9A5B")
			dot.icon = UI.icon(SceneUI.ICONS.check, UI.WHITE_WARM, 12, 4.0)
			dot.queue_redraw())
	return p


class HpBar extends Control:
	var fill := 1.0:
		set(v):
			fill = v
			queue_redraw()

	func _draw() -> void:
		draw_style_box(UI.box(UI.SAND, 4), Rect2(Vector2.ZERO, size))
		draw_style_box(UI.box(UI.GREEN, 4), Rect2(Vector2.ZERO, Vector2(size.x * fill, size.y)))
