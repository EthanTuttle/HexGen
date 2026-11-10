class_name CreatorName
extends Control
## The Name step (Creator v22b): the class, race and background banners hang behind the mini, with the hero's own banner
## right behind it, the typed name stitched on. The mockup's "Type a name" prompt is cut (Screen text: no hints for standard
## input; the plate already says Name). On a phone the step slides up clear of the keyboard: PLACEHOLDER, not mocked.

var c: Creator
var _edit: LineEdit
var _banner_name: Label
var _begin: TagButton


func _init(creator: Creator) -> void:
	c = creator
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _process(_delta: float) -> void:
	if not DisplayServer.has_feature(DisplayServer.FEATURE_VIRTUAL_KEYBOARD):
		return
	var kb := DisplayServer.virtual_keyboard_get_height()
	if kb > 0:
		var layout: float = float(kb) * get_viewport_rect().size.y / float(DisplayServer.window_get_size().y)
		position.y = -maxf(layout - 14.0, 0.0)
	else:
		position.y = 0.0


func refresh() -> void:
	if _edit:   # typing re-renders the bar; keep the field and its focus
		_begin.disabled = not c.all_done()
		return
	var cx := size.x * 0.5
	var all: Array = c.hero_banners()
	var i := 0
	for b: Dictionary in all:
		var on_left := i < 2
		var bx: float = cx - 96.0 - (52.0 + 14.0) * (2 - i) + 14.0 if on_left else cx + 96.0
		var side := SideBanner.make(b, 52, 180, 13, 22)
		UI.at(side, bx, 6)
		add_child(side)
		_dangle(side, 0.0)
		i += 1
	var hero := HeroCloth.new()
	hero.setup(c.cloth_colour(), all, 150, 210, 22)
	UI.at(hero, cx - 75.0, 6)
	add_child(hero)
	_dangle(hero, 0.2)
	_banner_name = hero.name_label
	_banner_name.text = "[Hero name]" if c.hero_name.strip_edges() == "" else c.hero_name.strip_edges()
	var mini := HeroView.new(150, 204)
	UI.at(mini, cx - 75.0, size.y - 46 - 4 - 204)
	add_child(mini)
	mini.show_hero.call_deferred(HeroMini.description(c.hero()))
	var row := CUI.hbox(0)
	row.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	row.offset_top = -46
	var back := CUI.big("Back", false)
	back.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	back.pressed.connect(c.go_back)
	row.add_child(back)
	row.add_child(CUI.spring())
	row.add_child(_plate())
	row.add_child(CUI.spring())
	_begin = CUI.big("Begin", true)
	_begin.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_begin.disabled = not c.all_done()
	_begin.pressed.connect(c.finish)
	row.add_child(_begin)
	add_child(row)


func _plate() -> Control:
	var p := PanelContainer.new()
	var sb := CUI.tile_box(UI.TRAY_EDGE, 3, 10, Vector4(14, 0, 14, 0), Color("#A8865E"))
	sb.shadow_color = Color("#6E5A44")
	sb.shadow_size = 1
	sb.shadow_offset = Vector2(0, 3)
	p.add_theme_stylebox_override("panel", sb)
	p.custom_minimum_size.y = 46
	var h := CUI.hbox(8)
	h.add_child(CUI.Dot.make(6, Color("#6E5A44"), "", 0))
	var lab := UI.label("NAME", "n900", 11, UI.CREAM, 1)
	lab.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(lab)
	_edit = LineEdit.new()
	_edit.custom_minimum_size = Vector2(190, 32)
	_edit.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_edit.max_length = 20
	_edit.alignment = HORIZONTAL_ALIGNMENT_CENTER
	_edit.accessibility_name = "Name"
	_edit.add_theme_font_override("font", UI.font("lilita"))
	_edit.add_theme_font_size_override("font_size", 17)
	_edit.add_theme_color_override("font_color", UI.INK)
	_edit.add_theme_color_override("caret_color", UI.INK)
	for s in ["normal", "focus", "read_only"]:
		_edit.add_theme_stylebox_override(s, UI.box(UI.CREAM, 6, Color(0, 0, 0, 0), 0, Vector4(10, 0, 10, 0)))
	_edit.text = c.hero_name
	_edit.text_changed.connect(_typed)
	h.add_child(_edit)
	h.add_child(CUI.Dot.make(6, Color("#6E5A44"), "", 0))
	p.add_child(h)
	return p


func _typed(t: String) -> void:
	c.hero_name = t
	var nm := t.strip_edges()
	_banner_name.text = "[Hero name]" if nm == "" else nm
	c.render()


func _dangle(b: Control, delay: float) -> void:
	b.pivot_offset = Vector2(b.size.x * 0.5, 0)
	b.rotation = deg_to_rad(-8.0)
	b.modulate.a = 0.0
	var tw := b.create_tween()
	tw.tween_interval(delay)
	tw.tween_property(b, "modulate:a", 1.0, 0.15)
	tw.parallel().tween_property(b, "rotation", deg_to_rad(4.0), 0.36)
	tw.tween_property(b, "rotation", 0.0, 0.24)


## A narrow banner: the class, race or background's own colour, its icon, its name down the cloth.
class SideBanner extends Control:
	var col := Color.WHITE
	var cut := 20.0

	static func make(b: Dictionary, w: float, h: float, px: int, icon_px: float) -> SideBanner:
		var s := SideBanner.new()
		s.col = b.c
		s.size = Vector2(w, h)
		s.custom_minimum_size = s.size
		s.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var v := CUI.vbox(4)
		v.position = Vector2(0, 12)
		v.size = Vector2(w, 0)
		if str(b.icon) != "":
			var ic := UI.icon_rect(b.icon, UI.WHITE_WARM, icon_px, 2.0)
			ic.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
			v.add_child(ic)
		var vt := CreatorBanners.VerticalText.new()
		vt.setup(b.lab, px, UI.WHITE_WARM)
		vt.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		v.add_child(vt)
		s.add_child(v)
		return s

	func _draw() -> void:
		var w := size.x
		var h := size.y
		draw_colored_polygon(PackedVector2Array([Vector2(0, 0), Vector2(w, 0), Vector2(w, h - cut), Vector2(w * 0.5, h), Vector2(0, h - cut)]), CUI.shade(col, 0.72))
		draw_colored_polygon(PackedVector2Array([Vector2(3, 0), Vector2(w - 3, 0), Vector2(w - 3, h - 4 - cut + 1), Vector2(w * 0.5, h - 4), Vector2(3, h - 4 - cut + 1)]), col)
		var rod := StyleBoxFlat.new()
		rod.bg_color = UI.TRAY_EDGE
		rod.set_corner_radius_all(4)
		draw_style_box(rod, Rect2(-3, -5, w + 6, 8))


## The hero's own banner: cream, edged in the cloth colour, the name stitched on, a hex in each banner's colour.
class HeroCloth extends Control:
	var edge_c := Color.WHITE
	var name_label: Label

	func setup(cloth: Color, banners: Array, w: float, h: float, px: int) -> void:
		edge_c = cloth
		size = Vector2(w, h)
		custom_minimum_size = size
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		var v := CUI.vbox(5)
		v.alignment = BoxContainer.ALIGNMENT_BEGIN
		v.position = Vector2(4, 16)
		v.size = Vector2(w - 8, 0)
		name_label = UI.label("", "lilita", px, UI.INK, 0, 1.05)
		name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		name_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		name_label.custom_minimum_size.x = w - 24.0
		CUI.reserve(name_label, ["-\n-"])   # two lines, as a long 20-letter name takes, so the hexes don't drop while typing (Nov 8 note)
		name_label.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		v.add_child(name_label)
		var st := CreatorBanners.Stitch.new()
		st.col = cloth
		st.custom_minimum_size = Vector2(w * 0.7, 4)
		st.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		st.mouse_filter = Control.MOUSE_FILTER_IGNORE
		v.add_child(st)
		var hexes := CUI.hbox(4)
		hexes.alignment = BoxContainer.ALIGNMENT_CENTER
		for b: Dictionary in banners:
			hexes.add_child(HexShape.make(22, 25, CUI.shade(b.c, 0.72), b.c, 2))
		v.add_child(hexes)
		add_child(v)

	func _draw() -> void:
		var w := size.x
		var h := size.y
		draw_colored_polygon(PackedVector2Array([Vector2(0, 0), Vector2(w, 0), Vector2(w, h - 26), Vector2(w * 0.5, h), Vector2(0, h - 26)]), edge_c)
		draw_colored_polygon(PackedVector2Array([Vector2(4, 0), Vector2(w - 4, 0), Vector2(w - 4, h - 29), Vector2(w * 0.5, h - 5), Vector2(4, h - 29)]), UI.CREAM)
		var rod := StyleBoxFlat.new()
		rod.bg_color = UI.TRAY_EDGE
		rod.set_corner_radius_all(5)
		draw_style_box(rod, Rect2(-4, -6, w + 8, 9))
