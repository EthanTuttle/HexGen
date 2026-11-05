class_name TownShop
extends Control
## The shopkeeper's counter (Town v2a, as in v9): items as hexes on a wooden counter, the gear screen's item pop-up over the
## picked one. Gold spends here.
## PLACEHOLDERS: the stock is Town v9's own list, the prices are made up, and buying takes the gold but does nothing yet
## (no gear or camp kits in the first playable): design/06 -> open question, what shops sell. No Sell tab: nothing to sell.

signal closed

const STOCK := [
	{"name": "Camp kit", "r": "C", "icon": "tent", "kind": "Consumable", "price": 10, "desc": "Pitch a camp. One kit covers the whole party."},
	{"name": "Potion", "r": "C", "icon": "potion", "kind": "Consumable", "price": 5},
	{"name": "Spear", "r": "C", "icon": "spear", "kind": "Weapon", "price": 15, "desc": "Versatile. Reach: hits 2 squares away.", "cards": ["Throw"]},
	{"name": "Battleaxe", "r": "C", "icon": "axe", "kind": "Weapon", "price": 20, "desc": "Versatile. Can be thrown.", "cards": ["Hack", "Throw"]},
	{"name": "Shortbow", "r": "C", "icon": "bow", "kind": "Weapon", "price": 20},
	{"name": "Light armor", "r": "C", "icon": "armor", "kind": "Armor", "price": 25},
	{"name": "Dagger", "r": "R", "icon": "sword", "kind": "Weapon", "price": 30, "cards": ["Backstab", "Throw"]},
]
const RIM := {"C": "#BFAE8E", "R": "#3F86C8", "L": "#E07A2F"}
const FACE := {"C": "#FCF7EE", "R": "#EAF3FB", "L": "#FDEEDF"}
const INK := {"C": "#33403B", "R": "#225C91", "L": "#9A4A12"}
const TAG_INK := {"C": "#5A5040", "R": "#225C91", "L": "#9A4A12"}
const RARITY := {"C": "Common", "R": "Rare", "L": "Legendary"}

static var bag: Array = []             # PLACEHOLDER: what's been bought, until there's an inventory

var scene: TownScene
var _pop: Control
var _hexes: Array[Control] = []
var _picked := -1


func _init(s: TownScene) -> void:
	scene = s
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var h := CUI.hbox(8)
	h.anchor_top = 1.0
	h.anchor_bottom = 1.0
	h.anchor_right = 1.0
	h.offset_left = 116   # clears the nav button
	h.offset_right = -12
	h.offset_top = -122
	h.offset_bottom = -14
	var tray := UI.panel(UI.TRAY, 14, UI.TRAY_EDGE, 4, Vector4(12, 10, 12, 8))
	tray.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var scroll := ScrollContainer.new()
	scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_SHOW_NEVER
	var row := CUI.hbox(6)
	for i in STOCK.size():
		row.add_child(_item(i))
	scroll.add_child(row)
	tray.add_child(scroll)
	h.add_child(tray)
	var back := SceneUI.dark_card("Back")
	back.pressed.connect(func(): closed.emit())
	h.add_child(back)
	add_child(h)


func _item(i: int) -> Control:
	var it: Dictionary = STOCK[i]
	var hx := HexShape.make(54, 62, Color(RIM[it.r]), Color(FACE[it.r]), 3).with_icon(SceneUI.ICONS[it.icon], Color(INK[it.r]), 26).with_shadow(UI.TRAY_EDGE)
	_hexes.append(hx)
	var price := UI.panel(UI.CREAM_LIGHT, 9, Color(0, 0, 0, 0), 0, Vector4(6, 0, 7, 0))
	price.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var ph := CUI.hbox(3)
	var coin := CUI.Dot.make(9, UI.GOLD, "", 0)
	ph.add_child(coin)
	ph.add_child(UI.label(str(it.price), "n900", 11))
	price.add_child(ph)
	var t := CUI.tap_column(it.name, [hx, price], 4)
	t.custom_minimum_size.x = 58
	t.pressed.connect(_toggle.bind(i))
	return t


func _toggle(i: int) -> void:
	_close_pop()
	if _picked == i:
		_picked = -1
		return
	_picked = i
	var it: Dictionary = STOCK[i]
	var p := PanelContainer.new()
	var sb := CUI.tile_box(Color(RIM[it.r]), 3, 16, Vector4(12, 10, 12, 12))
	sb.shadow_color = UI.HEX_SHADOW
	sb.shadow_size = 1
	sb.shadow_offset = Vector2(0, 4)
	p.add_theme_stylebox_override("panel", sb)
	p.custom_minimum_size.x = 220
	var v := CUI.vbox(6)
	v.add_child(UI.label(("%s · %s" % [it.kind, RARITY[it.r]]).to_upper(), "n900", 11, Color(TAG_INK[it.r]), 1))
	v.add_child(UI.label(it.name, "lilita", 20, UI.INK, 0, 1.1))
	if it.has("desc"):
		v.add_child(CUI.wrap(UI.label(it.desc, "n700", 12, CUI.SOFT_INK, 0, 1.35), 190))
	if it.has("cards"):
		var cards := CUI.hbox(5)
		for c: String in it.cards:
			var chip := UI.panel(Color("#F1E8D8"), 9, Color(0, 0, 0, 0), 0, Vector4(8, 1, 8, 1))
			chip.mouse_filter = Control.MOUSE_FILTER_IGNORE
			chip.add_child(UI.label(c, "n800", 11, UI.INK_MUTED))
			cards.add_child(chip)
		v.add_child(cards)
	var buy := TagButton.make("Buy · %d" % it.price, 130, 44, 14)
	buy.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	buy.ink = UI.WHITE_WARM
	buy.accessibility_name = "Buy " + str(it.name)
	buy.pressed.connect(_buy.bind(i))
	v.add_child(buy)
	p.add_child(v)
	add_child(p)
	p.reset_size()
	var from: Rect2 = _hexes[i].get_global_rect()
	var left := get_global_rect().position.x
	p.position = Vector2(clampf(from.get_center().x - left - 110.0, 96.0, size.x - 232.0), size.y - 132.0 - p.size.y)
	_pop = p


func _close_pop() -> void:
	if _pop:
		_pop.queue_free()
		_pop = null


func _buy(i: int) -> void:
	var it: Dictionary = STOCK[i]
	if not scene.game.spend(int(it.price)):
		scene.head.say("[Shopkeeper]", "%s · Shop" % scene.town_name(), "[Shopkeeper can't afford line]", Color("#F2D8B0"), TownScene.SHOP_C, SceneUI.ICONS.person)
		return
	bag.append(it.name)
	scene._refresh_gold()
	scene.head.say("[Shopkeeper]", "%s · Shop" % scene.town_name(), "[Shopkeeper buy line]", Color("#F2D8B0"), TownScene.SHOP_C, SceneUI.ICONS.person)
	_close_pop()
	_picked = -1
	var to: Vector2 = scene.game.hud.gear_button_centre() - get_global_rect().position
	SceneUI.reveal_reward(self, "Item", it.name, Color(RIM[it.r]), SceneUI.ICONS[it.icon], to)
