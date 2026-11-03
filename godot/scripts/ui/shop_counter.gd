class_name ShopCounter
extends Control
## The shopkeeper's counter, from Town v2a (mockups/town/Town-v2a-Counter.dc.html; design/07 -> Town screen -> Shop),
## as far as the prototype needs it: the River Port's stock, which is the raft. PLACEHOLDERS: there's no town scene or
## service cards, shopkeeper token, Sell (no inventory) or gold in the loop, so the shopkeeper's name and line, the gold,
## the price and the item's stats show the mockup's placeholders, and buying costs nothing. The raft's icon is the
## river terrain's. A bought item pops and flies to the equipment button (v1's rule).

signal closed

var fly_to := Vector2.ZERO              # where a bought item flies: the equipment button
var _on_buy: Callable
var _tray := HBoxContainer.new()
var _pop: PanelContainer
var _item: Control


func _init() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	visible = false
	_build_head()
	_build_gold()
	_build_counter()


func open(where: String, on_buy: Callable) -> void:
	_on_buy = on_buy
	(_head_sub as Label).text = "%s · Shop" % where
	_fill()
	visible = true


var _head_sub: Label


func _build_head() -> void:
	var p := UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(10, 10, 10, 10))
	p.custom_minimum_size = Vector2(560, 76)
	UI.at(p, 160, 12)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 12)
	h.add_child(HexShape.make(46, 53, UI.RIM, Color("#F2D8B0"), 3).with_shadow(UI.HEX_SHADOW))
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 3)
	var top := HBoxContainer.new()
	top.add_theme_constant_override("separation", 8)
	top.add_child(UI.label("[Shopkeeper]", "lilita", 16, UI.terrain_ink("river")))
	_head_sub = UI.label("", "n800", 11, UI.INK_MUTED)
	top.add_child(_head_sub)
	v.add_child(top)
	v.add_child(UI.label("[Shopkeeper line]", "n800", 14))
	h.add_child(v)
	p.add_child(h)
	add_child(p)


func _build_gold() -> void:
	var p := UI.panel(UI.DARK, 17, Color(0, 0, 0, 0), 0, Vector4(6, 0, 12, 0))
	p.custom_minimum_size.y = 34
	UI.at_right(p, 745, 12)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 6)
	var coin := CoinView.blank(22)
	coin.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(coin)
	var l := UI.label("[gold]", "n900", 13, UI.CREAM)
	l.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(l)
	p.add_child(h)
	add_child(p)


func _build_counter() -> void:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 8)
	h.anchor_top = 1.0
	h.anchor_bottom = 1.0
	h.anchor_right = 1.0
	h.offset_left = 116   # clears the nav button (design/07: the overlap is still being compared in town v5)
	h.offset_right = -12
	h.offset_top = -122
	h.offset_bottom = -14
	var buy := UI.panel(UI.DARK, 12, UI.DARK_EDGE, 4, Vector4(0, 0, 0, 0))
	buy.custom_minimum_size.x = 78
	var buy_l := UI.label("Buy", "n900", 13, UI.CREAM)
	buy_l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	buy_l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	buy.add_child(buy_l)
	h.add_child(buy)
	var tray := UI.panel(UI.TRAY, 14, UI.TRAY_EDGE, 4, Vector4(12, 10, 12, 8))
	tray.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_tray.add_theme_constant_override("separation", 6)
	tray.add_child(_tray)
	h.add_child(tray)
	var back := UI.FingerButton.new()
	back.text = "Back"
	back.custom_minimum_size.x = 78
	back.add_theme_font_override("font", UI.font("n900"))
	back.add_theme_font_size_override("font_size", 13)
	for s in ["normal", "hover", "pressed", "focus"]:
		back.add_theme_stylebox_override(s, UI.box(UI.DARK, 12, UI.DARK_EDGE, 4))
	for s in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		back.add_theme_color_override(s, UI.CREAM)
	back.pressed.connect(close)
	h.add_child(back)
	add_child(h)


func close() -> void:
	_close_pop()
	visible = false
	closed.emit()


## The stock: the raft, as a hex with its price.
func _fill() -> void:
	for c in _tray.get_children():
		_tray.remove_child(c)
		c.queue_free()
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	v.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	var hex := HexShape.make(54, 62, UI.RIM, UI.CREAM_LIGHT, 3).with_icon("t_river", UI.terrain_ink("river"), 24).with_shadow(UI.TRAY_EDGE)
	hex.clickable = true
	hex.accessibility_name = "Raft"
	hex.pressed.connect(_toggle_pop)
	v.add_child(hex)
	var price := UI.panel(UI.CREAM_LIGHT, 9, Color(0, 0, 0, 0), 0, Vector4(7, 0, 7, 0))
	price.mouse_filter = Control.MOUSE_FILTER_IGNORE
	price.add_child(UI.label("[price]", "n900", 11))
	v.add_child(price)
	_item = hex
	_tray.add_child(v)


## The gear screen's item pop-up over the picked item, with Buy in it (Town v2a).
func _toggle_pop() -> void:
	if _pop:
		_close_pop()
		return
	_pop = UI.panel(UI.CREAM_LIGHT, 16, UI.HEX_SHADOW, 5, Vector4(12, 10, 12, 12))
	var box := _pop.get_theme_stylebox("panel") as StyleBoxFlat
	box.set_border_width_all(3)
	box.border_color = UI.RIM
	_pop.custom_minimum_size.x = 220
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	var name_l := UI.label("Raft", "lilita", 20, UI.INK, 0, 1.1)
	v.add_child(name_l)
	v.add_child(UI.label("[Item stats]", "n700", 11, UI.INK_MUTED))
	var buy := TagButton.make("Buy · [price]", 130, 44, 14)
	buy.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	buy.pressed.connect(_buy)
	v.add_child(buy)
	_pop.add_child(v)
	_pop.anchor_top = 1.0
	_pop.anchor_bottom = 1.0
	_pop.offset_left = 214
	_pop.offset_bottom = -132
	_pop.grow_vertical = Control.GROW_DIRECTION_BEGIN
	add_child(_pop)


func _close_pop() -> void:
	if _pop:
		_pop.queue_free()
		_pop = null


func _buy() -> void:
	_close_pop()
	var from := _item.global_position - global_position
	var fly := HexShape.make(54, 62, UI.RIM, UI.CREAM_LIGHT, 3).with_icon("t_river", UI.terrain_ink("river"), 24)
	fly.position = from
	fly.pivot_offset = fly.size * 0.5
	add_child(fly)
	_tray.get_child(0).queue_free()
	_on_buy.call()
	var mid := size * 0.5 - fly.size * 0.5
	var tw := fly.create_tween()
	tw.tween_property(fly, "position", mid, 0.25).set_ease(Tween.EASE_OUT)
	tw.parallel().tween_property(fly, "scale", Vector2(1.5, 1.5), 0.25)
	tw.tween_interval(0.4)
	tw.tween_property(fly, "position", fly_to - fly.size * 0.5, 0.45).set_ease(Tween.EASE_IN).set_trans(Tween.TRANS_QUAD)
	tw.parallel().tween_property(fly, "scale", Vector2(0.4, 0.4), 0.45)
	tw.tween_callback(fly.queue_free)
