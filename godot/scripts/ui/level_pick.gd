class_name LevelPick
extends Control
## A level's picks (design/06: simple, the full Level-up screen comes later), one character at a time, hero first (07 ->
## Level-up), each character's choices as steps with Next and Back, then three terrain cards, one into the hand.
##   points (levels 4, 8, 12, 16): place 1 ability point (03 -> Ability scores; 07 v8d's six coin tiles, 2 rows of 3, the new
##       coin ringed green; no score above 6, a tile at 6 dimmed)
##   mastery (level 2, martials): a weapon mastery node, the first of a branch (04; Progression)
##   class_cards (level 3, martials): the class kit as cards, the new one tagged, nothing to choose (07 v9a)
##   spells (level 3, casters): two slots on top that fill as you pick; every level-3 spell in a column per school or order
##       (07 v9a, as the creator's Spells step)
##   feat (levels 4 and 12): one list grouped Race, Background, General, own race and background first, Show all adds the
##       ones out of reach, faded with the missing requirement (07 v8b, v9); Skilled and Weapon Training pick in the pop-up
##   subclass, then follow (a Shifter's form, a Companion's beast, a Holy Defender's god), then gain: the new card and the
##       upgraded one (martials, nothing to choose) or a spell from the new school's or order's tier 1 (casters) (07 v8c)
## Rows open a pop-up (group, name, text, Choose), as the creator's Spells step does. PLACEHOLDER look: the mockups' screen
## is a full page; this is the first playable's panel over the map.

const ABILITIES := ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
const CAP := 6
const BAND := "#B5532F"   # class cards' band (Cards.SRC.klass)
const WEAPON_BAND := "#5F7F99"

var game: Game
var _level := 0
var _options := []
var _members := []       # who places a point this level (the party), or none
var _party := []         # everyone who levels
var step := 0            # the step showing now; == _steps().size() for the terrain cards
var placed := {}         # member index -> the ability its point went on
var picks := {}          # member index -> {mastery: [cat, id], spells: [], feat, follow, subclass, sub_follow, tier1}
var show_all := false    # the feat list's Show all toggle (07: off by default)
var _focus := ""         # the row whose pop-up is open


static func attach(g: Game) -> LevelPick:
	var p := LevelPick.new()
	p.game = g
	p.name = "level_pick"
	p.visible = false
	p.set_anchors_preset(Control.PRESET_FULL_RECT)
	g.safe.add_child(p)
	return p


## members: who places a point (the party at a score level). The level's other picks follow Progression.sections for every
## party member.
func open(level: int, options: Array, members := []) -> void:
	_level = level
	_options = options
	_members = members
	_party = game.party.duplicate() if game != null else members
	step = 0
	placed = {}
	picks = {}
	for i in _party.size():
		picks[i] = {"mastery": [], "spells": [], "feat": "", "follow": "", "subclass": "", "sub_follow": "", "tier1": ""}
	show_all = false
	_focus = ""
	_build()


func _bg() -> String:
	return game.run.background if game != null and game.run != null else ""


## Every step this level: [member index, section], in order. Follow and gain come once a subclass is chosen.
func _steps() -> Array:
	var out := []
	for i in _party.size():
		var m: Dictionary = _party[i]
		var secs := Progression.sections(m, _level, _bg()) if int(m.get("levelled", 1)) < _level else []
		for s: String in secs:
			if s == "feat":
				out.append([i, "feat"])
				if not _members.is_empty():
					out.append([i, "points"])
				continue
			out.append([i, s])
			if s == "subclass" and picks[i].subclass != "":
				if Progression.SUBCLASSES[Progression.klass(m)][picks[i].subclass].has("follow"):
					out.append([i, "follow"])
				out.append([i, "gain"])
		if not "feat" in secs and not _members.is_empty() and i < _members.size():
			out.append([i, "points"])
	return out


## The test bots' pick: each member's point on its main score (the weapon's), or its highest score under the cap; the
## built options first for the rest (Progression's bot picks), then the first terrain card.
func bot_pick() -> void:
	for i in _members.size():
		var m: Dictionary = _members[i]
		var open := ABILITIES.filter(func(k): return Races.score(m, k) < CAP)
		if open.is_empty():
			continue
		open.sort_custom(func(a, b): return Races.score(m, a) > Races.score(m, b))
		placed[i] = String(m.ability) if String(m.ability) in open else open[0]
	for i in _party.size():
		var m: Dictionary = _party[i]
		if int(m.get("levelled", 1)) >= _level:
			continue
		for s: String in Progression.sections(m, _level, _bg()):
			match s:
				"mastery":
					var o := Progression.bot_mastery(m)
					picks[i].mastery = [o.cat, o.node.id]
				"spells":
					picks[i].spells = Progression.bot_spells(m)
				"feat":
					picks[i].feat = Progression.bot_feat(m, _bg())
					picks[i].follow = Progression.bot_follow(m, Progression.feat_of(picks[i].feat))
				"subclass":
					picks[i].subclass = Progression.bot_subclass(m)
					picks[i].sub_follow = Progression.bot_follow_sub(m, picks[i].subclass)
					picks[i].tier1 = Progression.bot_tier1(m, picks[i].subclass)
	game.level_picked(_options[0], placed, picks)


## Places this member's point (or moves it).
func place(ability: String) -> void:
	var i := _who()
	if i < 0 or Races.score(_party[i], ability) >= CAP:
		return
	placed[i] = ability
	_build()


## On to the next step, or the terrain cards, once this one is done.
func next() -> void:
	if step < _steps().size() and _done(_steps()[step]):
		step += 1
		_focus = ""
		_build()


## Back to the previous step, whose choice stays made until changed.
func back() -> void:
	if step > 0:
		step -= 1
		_focus = ""
		_build()


## Whose step this is, or -1 on the terrain cards.
func _who() -> int:
	var steps := _steps()
	return steps[step][0] if step < steps.size() else -1


func _full(m: Dictionary) -> bool:
	return ABILITIES.all(func(k): return Races.score(m, k) >= CAP)


func _done(st: Array) -> bool:
	var i: int = st[0]
	var m: Dictionary = _party[i]
	var p: Dictionary = picks[i]
	match st[1]:
		"points":
			return placed.has(i) or _full(m)
		"mastery":
			return not p.mastery.is_empty()
		"spells":
			var left := 0
			for g in Progression.spell_groups_3(m).values():
				left += g.size()
			return p.spells.size() >= mini(Progression.SPELL_PICKS_3, left)
		"feat":
			return p.feat != "" and (not Progression.feat_of(p.feat).has("follow") or p.follow != "")
		"subclass":
			return p.subclass != ""
		"follow":
			return p.sub_follow != ""
		"gain":
			return not Progression.klass(m) in Progression.CASTERS or p.tier1 != "" or _tier1_of(m, p.subclass).is_empty()
	return true


func _tier1_of(m: Dictionary, sub: String) -> Array:
	var src: Dictionary = Progression.WIZARD_T1 if Progression.klass(m) == "wizard" else Progression.CLERIC_T1
	return src.get(sub, []).filter(func(id): return not id in m.get("cards", []))


# --- Building the panel ----------------------------------------------------------------

func _build() -> void:
	for c in get_children():
		remove_child(c)
		c.queue_free()
	var dim := Scrim.make(Color(0.141, 0.188, 0.172, 0.45))
	dim.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(dim)
	var steps := _steps()
	var sec: String = steps[step][1] if step < steps.size() else "terrain"
	var wide := sec in ["mastery", "spells", "feat", "subclass", "follow", "gain", "class_cards"]
	var box := UI.panel(UI.CREAM, 18, UI.CREAM_EDGE, 5, Vector4(24, 16, 24, 16))
	box.custom_minimum_size = Vector2(600 if wide else 320, 150)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	box.add_child(v)
	v.add_child(UI.label("Level %d" % _level, "lilita", 26, Color("#2E6B3A")))
	if sec == "terrain":
		var row := HBoxContainer.new()
		row.alignment = BoxContainer.ALIGNMENT_CENTER
		row.add_theme_constant_override("separation", 14)
		v.add_child(row)
		for t: String in _options:
			var hx := HexShape.make(66, 76, UI.CREAM_LIGHT, UI.terrain_bg(t), 4).with_icon("t_" + t, UI.terrain_ink(t), 32)
			hx.clickable = true
			hx.accessibility_name = Rules.NAMES[t]
			hx.pressed.connect(func(): game.level_picked(t, placed, picks))
			row.add_child(hx)
		if not steps.is_empty():
			v.add_child(_nav(false))
	else:
		var i: int = steps[step][0]
		var m: Dictionary = _party[i]
		var head := HBoxContainer.new()
		head.add_theme_constant_override("separation", 12)
		head.add_child(UI.label(String(m.name), "lilita", 20))
		head.add_child(_section(_title(m, sec), _done(steps[step])))
		if sec == "feat":
			head.add_child(CUI.spring())
			var all := CUI.pill("Show all", show_all)
			all.pressed.connect(func():
				show_all = not show_all
				_build())
			head.add_child(all)
		v.add_child(head)
		match sec:
			"points":
				var grid := GridContainer.new()
				grid.columns = 3
				grid.add_theme_constant_override("h_separation", 8)
				grid.add_theme_constant_override("v_separation", 8)
				for k: String in ABILITIES:
					grid.add_child(_tile(i, m, k))
				v.add_child(grid)
			"mastery":
				v.add_child(_columns(_mastery_columns(m)))
			"class_cards":
				v.add_child(_class_cards(m))
			"spells":
				v.add_child(_spell_slots(i))
				v.add_child(_columns(_spell_columns(m, Progression.spell_groups_3(m), picks[i].spells)))
			"feat":
				v.add_child(_scroll(_columns(_feat_columns(i, m)), 190))
			"subclass":
				v.add_child(_columns(_subclass_columns(i, m)))
			"follow":
				v.add_child(_columns(_follow_columns(i, m)))
			"gain":
				if Progression.klass(m) in Progression.CASTERS:
					v.add_child(_columns(_spell_columns(m, {picks[i].subclass: _tier1_of(m, picks[i].subclass)}, [picks[i].tier1])))
				else:
					v.add_child(_gain_cards(m, picks[i].subclass))
		v.add_child(_nav(true, _done(steps[step])))
	add_child(Scrim.centre(box))
	if _focus != "" and sec != "terrain":
		_pop.call_deferred(box, steps[step])
	visible = true
	move_to_front()


## Each section's title (07 -> Level-up: "Place 1 ability point", "Your class cards", "Pick a feat", "Pick a spell"; the
## rest are new strings for the Screen text check).
func _title(m: Dictionary, sec: String) -> String:
	match sec:
		"points":
			return "Place 1 ability point"
		"mastery":
			return "Weapon mastery"
		"class_cards":
			return "Your class cards"
		"spells":
			return "Pick %d spells" % Progression.SPELL_PICKS_3
		"feat":
			return "Pick a feat"
		"subclass":
			return "Pick a subclass"
		"follow":
			match Progression.SUBCLASSES[Progression.klass(m)][picks[_party.find(m)].subclass].follow:
				"form":
					return "Pick a form"
				"beast":
					return "Pick a beast"
				"god":
					return "Pick a god"
		"gain":
			return "Pick a spell" if Progression.klass(m) in Progression.CASTERS else "You gain"
	return ""


## Back from the second step on, then a spring, then Next (off until the step is done).
func _nav(with_next: bool, on := true) -> HBoxContainer:
	var nav := HBoxContainer.new()
	if step > 0:
		var b := CUI.big("Back", false)
		b.pressed.connect(back)
		nav.add_child(b)
	var spring := Control.new()
	spring.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	nav.add_child(spring)
	if with_next:
		var go := CUI.big("Next", true)
		go.modulate.a = 1.0 if on else 0.4
		go.mouse_filter = Control.MOUSE_FILTER_STOP if on else Control.MOUSE_FILTER_IGNORE
		go.pressed.connect(next)
		nav.add_child(go)
	return nav


## A section title with its dot: orange until done, then a green tick (07 -> Level-up, no to-do line).
func _section(title: String, done: bool) -> Control:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 7)
	h.add_child(UI.label(title, "lilita", 16))
	var mark := CUI.mark(done)
	mark.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(mark)
	return h


func _scroll(c: Control, h: float) -> Control:
	var sc := ScrollContainer.new()
	sc.custom_minimum_size = Vector2(0, h)
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	c.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.add_child(c)
	return sc


# --- Rows in columns, and their pop-up -----------------------------------------------------
# A column: {title, icon, rows}; a row: {key, name, ap (or -1), line (a second line, or ""), chip, picked, dim, pop: {tag,
# name, text, chips, choose (Callable or null), note, extra (Control or null)}}.

func _columns(cols: Array) -> Control:
	var grid := GridContainer.new()
	grid.columns = maxi(cols.size(), 1)
	grid.add_theme_constant_override("h_separation", 8)
	grid.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for c: Dictionary in cols:
		var col := CUI.vbox(4)
		col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		col.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
		if c.title != "":
			var head := CUI.hbox(4)
			if c.get("icon", "") != "":
				head.add_child(UI.icon_rect(c.icon, Color("#5A5040"), 13, 2.2))
			head.add_child(UI.label(String(c.title).to_upper(), "n900", 11, Color("#5A5040"), 1))
			col.add_child(head)
		for r: Dictionary in c.rows:
			col.add_child(_row(r))
		grid.add_child(col)
	return grid


func _row(r: Dictionary) -> Control:
	var open: bool = _focus == r.key
	var t := CUI.Tap.new(r.name)
	t.custom_minimum_size = Vector2(0, 30 if r.get("line", "") == "" else 44)
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var on: bool = r.get("picked", false)
	t.draw.connect(func():
		t.draw_style_box(CUI.tile_box(CUI.SEL_RIM if on or open else UI.HEX_SHADOW, 2.5 if open or on else 2.0, 9, Vector4.ZERO), Rect2(Vector2.ZERO, t.size)))
	t.modulate.a = 0.5 if r.get("dim", false) else 1.0
	var h := CUI.hbox(5)
	h.set_anchors_preset(Control.PRESET_FULL_RECT)
	h.offset_left = 4
	h.offset_right = -5
	if int(r.get("ap", -1)) >= 0:
		var hx := HexShape.make(18, 21, UI.DARK, UI.DARK, 0).with_text(str(r.ap), 10, UI.CREAM, "n900")
		hx.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		h.add_child(hx)
	elif r.get("icon", "") != "":
		var ic := UI.icon_rect(r.icon, Color("#9A4A12"), 16, 2.2)
		ic.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		h.add_child(ic)
	var names := CUI.vbox(0)
	names.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	names.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	names.add_child(UI.label(r.name, "n900", 11, UI.INK, 0, 1.0))
	if r.get("line", "") != "":
		var l := UI.label(r.line, "n700", 11, CUI.CAP_INK, 0, 1.0)
		l.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		l.clip_text = true
		names.add_child(l)
	h.add_child(names)
	if r.get("chip", "") != "":
		h.add_child(_chip(r.chip, UI.RED if r.get("dim", false) else Color("#2E7A3E"), UI.WHITE_WARM))
	if on:
		h.add_child(CUI.Dot.make(16, Color("#2E7A3E"), CUI.TICK, 10))
	t.add_child(h)
	t.set_meta("pop", r.pop)
	t.set_meta("key", r.key)
	t.pressed.connect(func():
		_focus = "" if _focus == r.key else r.key
		_build())
	return t


## The open row's pop-up: tag, name, text, chips, then Choose (or a tick once picked, or a note).
func _pop(box: Control, _st: Array) -> void:
	var r: Dictionary = {}
	for n in find_children("*", "Control", true, false):
		if n.has_meta("pop") and n.get_meta("key", "") == _focus:
			r = n.get_meta("pop")
	if r.is_empty():
		return
	var p := PanelContainer.new()
	var sb := CUI.tile_box(CUI.SEL_RIM, 3, 16, Vector4(10, 8, 10, 10))
	sb.shadow_color = UI.HEX_SHADOW
	sb.shadow_size = 1
	sb.shadow_offset = Vector2(0, 4)
	p.add_theme_stylebox_override("panel", sb)
	p.custom_minimum_size.x = 280
	var v := CUI.vbox(4)
	var top := CUI.hbox(6)
	var names := CUI.vbox(0)
	names.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	names.add_child(UI.label(String(r.tag).to_upper(), "n900", 11, Color("#9A4A12"), 1))
	names.add_child(UI.label(r.name, "lilita", 17, UI.INK, 0, 1.1))
	top.add_child(names)
	var close := HexShape.make(20, 20, Color(0, 0, 0, 0), Color(0, 0, 0, 0), 0).with_icon("M6 6l12 12 M18 6L6 18", CUI.SOFT_INK, 16, 2.6)
	close.clickable = true
	close.accessibility_name = "Close"
	close.pressed.connect(func():
		_focus = ""
		_build())
	top.add_child(close)
	v.add_child(top)
	v.add_child(CUI.wrap(UI.label(r.text, "n700", 12, Color("#33403B"), 0, 1.35), 260))
	if r.get("extra") != null:
		v.add_child(r.extra)
	var foot := CUI.hbox(6)
	for c: Array in r.get("chips", []):
		foot.add_child(_chip(c[0], c[1], UI.WHITE_WARM if c[1] != UI.CREAM_LIGHT else UI.INK))
	foot.add_child(CUI.spring())
	if r.get("picked", false):
		foot.add_child(CUI.Dot.make(16, Color("#2E7A3E"), CUI.TICK, 10))
	elif r.get("note", "") != "":
		foot.add_child(UI.label(r.note, "n800", 11, CUI.CAP_INK))
	if r.get("choose") != null and not r.get("picked", false):
		var choose := CUI.choose_button("Choose", 92)
		var on: bool = r.get("can", true)
		choose.modulate.a = 1.0 if on else 0.4
		choose.mouse_filter = Control.MOUSE_FILTER_STOP if on else Control.MOUSE_FILTER_IGNORE
		var f: Callable = r.choose
		choose.pressed.connect(func():
			f.call()
			_focus = ""
			_build())
		foot.add_child(choose)
	v.add_child(foot)
	p.add_child(v)
	add_child(p)
	p.reset_size()
	var rb := box.get_global_rect()
	p.global_position = Vector2(rb.position.x + (rb.size.x - p.size.x) * 0.5, rb.end.y - 60 - p.size.y)


func _chip(t: String, bg: Color, ink: Color) -> Control:
	var p := UI.panel(bg, 10, Color(0, 0, 0, 0), 0, Vector4(8, 1, 8, 1))
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	p.add_child(UI.label(t, "n900", 11, ink))
	return p


## A card's text without its "Blaster spell:" or "Longsword:" lead, which the pop-up's tag already says.
static func text_of(k: Dictionary) -> String:
	var t: String = k.desc
	if t.find(": ") >= 0 and t.find(": ") < 24:
		t = t.substr(t.find(": ") + 2)
		t = t[0].to_upper() + t.substr(1)   # "mark a foe" after "Order of Light:" reads as a sentence
	return t


func _card_row(id: String, tag: String, picked: bool, choose: Variant, note := "") -> Dictionary:
	var k := Cards.get_card(id)
	var chips := [["%d AP" % k.ap, UI.DARK]]
	if k.get("hp", 0) > 0:
		chips.append(["%d HP" % k.hp, UI.RED])
	return {"key": id, "name": k.n, "ap": k.ap, "picked": picked,
		"pop": {"tag": tag, "name": k.n, "text": text_of(k), "chips": chips, "choose": choose, "picked": picked, "note": note}}


# --- Mastery ---------------------------------------------------------------------------------

func _mastery_columns(m: Dictionary) -> Array:
	var i := _party.find(m)
	var cols := {}
	for o: Dictionary in Progression.mastery_options(m):
		var node: Dictionary = o.node
		var cat: String = o.cat
		if not cols.has(cat):
			cols[cat] = {"title": cat.capitalize(), "icon": CreatorData.IC.get("w_" + cat, ""), "rows": []}
		var key := "%s.%s" % [cat, node.id]
		var on: bool = picks[i].mastery == [cat, node.id]
		var text: String = node.get("text", "")
		var chips := []
		if node.kind == "card":
			var k := Cards.get_card(node.card)
			text = text_of(k)
			chips.append(["%d AP" % k.ap, UI.DARK])
		var note := ""
		if node.branch in Progression.TWO_HANDED_BRANCHES:
			note = "Two-handed only"
		var choose := func(): picks[i].mastery = [cat, node.id]
		var r := {"key": key, "name": node.n, "line": node.branch, "icon": "", "picked": on,
			"pop": {"tag": "%s · %s" % [node.branch, cat.capitalize()], "name": node.n, "text": text, "chips": chips, "choose": choose, "picked": on, "note": note}}
		if node.kind == "card":
			r.ap = Cards.get_card(node.card).ap
		cols[cat].rows.append(r)
	return cols.values()


# --- Level 3 ---------------------------------------------------------------------------------

## The class kit as cards (07 v9a): the level-1 card, then the level-3 one, tagged New when this level gives it.
func _class_cards(m: Dictionary) -> Control:
	var row := CUI.hbox(10)
	var k := Progression.klass(m)
	for id: String in Weapons.CLASS_CARDS.get(k, []) + [Progression.LEVEL3_CARD.get(k, "")]:
		var new: bool = id == Progression.LEVEL3_CARD.get(k, "") and not id in m.get("cards", [])
		row.add_child(_card_tile(id, m, new))
	return row


func _spell_slots(i: int) -> Control:
	var row := CUI.hbox(10)
	row.add_child(CUI.spring())
	for n in Progression.SPELL_PICKS_3:
		var id: String = picks[i].spells[n] if n < picks[i].spells.size() else ""
		if id == "":
			var t := Control.new()
			t.custom_minimum_size = Vector2(62, 70)
			t.draw.connect(func():
				var r := Rect2(Vector2(1, 1), t.size - Vector2(2, 2))
				var pts := [r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y), r.position]
				for q in 4:
					var a: Vector2 = pts[q]
					var b: Vector2 = pts[q + 1]
					var cnt := int(a.distance_to(b) / 8.0)
					for j in cnt:
						t.draw_line(a.lerp(b, float(j) / cnt), a.lerp(b, (j + 0.55) / cnt), Color("#A8957A"), 2.0))
			var l := UI.label("Spell %d" % (n + 1), "n900", 11, Color("#6E5A44"))
			l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
			l.set_anchors_preset(Control.PRESET_FULL_RECT)
			t.add_child(l)
			row.add_child(t)
		else:
			var tile := _card_tile(id, _party[i], false)
			var tap := CUI.Tap.new(Cards.ALL[id].n)
			tap.set_anchors_preset(Control.PRESET_FULL_RECT)
			tap.pressed.connect(func():   # tapping a filled slot clears it (07 v9a)
				picks[i].spells.erase(id)
				_build())
			tile.add_child(tap)
			row.add_child(tile)
	return row


## Spell rows per school or order; picking past the slots swaps out the first pick ("Replaces ...", 07 v9a).
func _spell_columns(m: Dictionary, groups: Dictionary, chosen: Array) -> Array:
	var i := _party.find(m)
	var cols := []
	var level5: bool = _steps()[step][1] == "gain"
	for g: String in groups:
		var rows := []
		for id: String in groups[g]:
			var on: bool = id in chosen
			var note := ""
			var choose: Callable
			if level5:
				choose = func(): picks[i].tier1 = id
			else:
				if picks[i].spells.size() >= Progression.SPELL_PICKS_3:
					note = "Replaces %s" % Cards.ALL[picks[i].spells[0]].n
				choose = func():
					if picks[i].spells.size() >= Progression.SPELL_PICKS_3:
						picks[i].spells.pop_front()
					picks[i].spells.append(id)
			var tag := "%s spell" % g if Progression.klass(m) == "wizard" else g
			rows.append(_card_row(id, tag, on, choose, note))
		cols.append({"title": g.replace("Order of ", ""), "icon": Progression.SCHOOL_ICON.get(g, ""), "rows": rows})
	return cols


# --- Feats -----------------------------------------------------------------------------------

## Race, Background, General (07 v8b), the character's own race and background feats first; Show all adds the rest, faded
## with the missing requirement.
func _feat_columns(i: int, m: Dictionary) -> Array:
	var rows := []
	for g in ["Race", "Background", "General"]:
		for f: Dictionary in Progression.FEATS:
			if f.group != g:
				continue
			var miss := Progression.missing(m, f, _bg())
			if miss != "" and not show_all:
				continue
			var on: bool = picks[i].feat == f.id
			var extra: Control = null
			var follow_opts := Progression.follow_options(m, f)
			var can := miss == ""
			var note := ""
			if f.has("follow"):
				can = can and not follow_opts.is_empty() and (picks[i].feat == f.id and picks[i].follow != "" or _pending_follow(i, f) != "")
				if follow_opts.is_empty() and miss == "":
					note = "Nothing to pick"
				else:
					extra = _follow_chips(i, f, follow_opts)
			var name: String = f.n
			if on and picks[i].follow != "":
				name = "%s · %s" % [f.n, picks[i].follow.capitalize() if f.follow == "weapon" else picks[i].follow]
			var chips := [[("Needs " + miss) if miss != "" else Progression.need_text(f), UI.RED if miss != "" else Color("#2E7A3E")]] if Progression.need_text(f) != "" else []
			var choose := func():
				picks[i].feat = f.id
				picks[i].follow = _pending_follow(i, f) if f.has("follow") else ""
			rows.append({"key": f.id, "name": name, "line": f.text, "picked": on, "dim": miss != "",
				"chip": ("Needs " + miss) if miss != "" else Progression.need_text(f),
				"pop": {"tag": g, "name": f.n, "text": f.text, "chips": chips, "choose": choose if miss == "" else null, "picked": on, "can": can, "note": note, "extra": extra}})
	return [{"title": "", "rows": rows}]


var _pending := {}   # member index -> the follow-up chip tapped in the open feat pop-up


func _pending_follow(i: int, f: Dictionary) -> String:
	var p: String = _pending.get(i, "")
	return p if p in Progression.follow_options(_party[i], f) else ""


## Skilled's proficiencies or Weapon Training's categories as chips under the effect (07 v9: "Pick a proficiency").
func _follow_chips(i: int, f: Dictionary, opts: Array) -> Control:
	var v := CUI.vbox(4)
	v.add_child(UI.label("Pick a proficiency" if f.follow == "proficiency" else "Pick a weapon", "n800", 11, CUI.CAP_INK))
	var flow := HFlowContainer.new()
	flow.add_theme_constant_override("h_separation", 4)
	flow.add_theme_constant_override("v_separation", 4)
	flow.custom_minimum_size.x = 260
	for o: String in opts:
		var b := CUI.pill(o.capitalize() if f.follow == "weapon" else o, _pending_follow(i, f) == o)
		b.pressed.connect(func():
			_pending[i] = o
			_build())
		flow.add_child(b)
	v.add_child(flow)
	return v


# --- Level 5 ---------------------------------------------------------------------------------

func _subclass_columns(i: int, m: Dictionary) -> Array:
	var rows := []
	var k := Progression.klass(m)
	for name: String in Progression.SUBCLASSES[k]:
		var s: Dictionary = Progression.SUBCLASSES[k][name]
		var on: bool = picks[i].subclass == name
		var text: String = s.blurb
		var choose := func():
			if picks[i].subclass != name:
				picks[i].sub_follow = ""
				picks[i].tier1 = ""
			picks[i].subclass = name
		rows.append({"key": name, "name": name, "icon": Progression.SCHOOL_ICON.get(name, "star"), "picked": on,
			"pop": {"tag": k.capitalize(), "name": name, "text": text, "chips": _gives(s), "choose": choose, "picked": on}})
	return [{"title": "", "rows": rows}]


## What a martial subclass gives, as chips in its pop-up: the new card and the upgraded card's new name.
func _gives(s: Dictionary) -> Array:
	if not s.has("card"):
		return []
	return [[Cards.ALL[s.card].n, Color(BAND)], [s.n, Color("#2E7A3E")]]


func _follow_columns(i: int, m: Dictionary) -> Array:
	var s: Dictionary = Progression.SUBCLASSES[Progression.klass(m)][picks[i].subclass]
	var rows := []
	var src: Dictionary = {"form": Progression.FORMS, "beast": Progression.BEASTS, "god": Progression.GODS}[s.follow]
	for name: String in src:
		var on: bool = picks[i].sub_follow == name
		var card_id: String
		var text: String
		var tag: String
		match s.follow:
			"form":
				card_id = src[name].card
				tag = src[name].feel
				text = text_of(Cards.get_card(card_id))
			"beast":
				card_id = src[name].card
				tag = "Beast"
				text = src[name].text
			"god":
				card_id = src[name]
				tag = Progression.GOD_OF[name]
				text = text_of(Cards.get_card(card_id))
		var choose := func(): picks[i].sub_follow = name
		rows.append({"key": name, "name": name, "line": Cards.ALL[card_id].n, "picked": on,
			"pop": {"tag": tag, "name": name, "text": text, "chips": [[Cards.ALL[card_id].n, Color(BAND)]], "choose": choose, "picked": on}})
	return [{"title": "", "rows": rows}]


## A martial's level-5 gains as cards (07 v8c "You gain"): the subclass card, tagged New, and the upgraded class card under
## its new name.
func _gain_cards(m: Dictionary, sub: String) -> Control:
	var s: Dictionary = Progression.SUBCLASSES[Progression.klass(m)][sub]
	var row := CUI.hbox(14)
	row.add_child(_card_tile(s.card, m, true))
	var up := _card_tile(s.of, m, false, s.n)
	row.add_child(up)
	var v := CUI.vbox(2)
	v.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	v.add_child(UI.label(s.n, "lilita", 15))
	v.add_child(CUI.wrap(UI.label(s.text, "n700", 12, Color("#33403B"), 0, 1.3), 300))
	v.add_child(UI.label("Replaces %s" % Cards.ALL[s.of].n, "n800", 11, CUI.CAP_INK))
	row.add_child(v)
	return row


## A combat card as the hotbar draws it, small: class band, AP hex, icon, name; "New" tag with a gold glow.
func _card_tile(id: String, _m: Dictionary, new: bool, name := "") -> Control:
	var k := Cards.get_card(id)
	var t := Control.new()
	t.custom_minimum_size = Vector2(62, 70)
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var band := Color(WEAPON_BAND if k.src == "weapon" else BAND)
	t.draw.connect(func():
		if new:
			t.draw_style_box(CUI.tile_box(Color("#E9C46A"), 4, 11, Vector4.ZERO), Rect2(Vector2(-3, -3), t.size + Vector2(6, 6)))
		t.draw_style_box(CUI.tile_box(CUI.SEL_RIM, 2, 9, Vector4.ZERO), Rect2(Vector2.ZERO, t.size))
		t.draw_rect(Rect2(2, 2, 58, 5), band))
	var hx := HexShape.make(18, 21, UI.DARK, UI.DARK, 0).with_text(str(k.ap), 11, UI.CREAM, "n900")
	UI.at(hx, 3, 8)
	t.add_child(hx)
	var ic := UI.icon_rect(k.icon, Color("#9A4A12"), 18, 2.2)
	UI.at(ic, 22, 11)
	t.add_child(ic)
	var shown := name if name != "" else String(k.n)
	var name_l := UI.label("\n".join(Cards.name_lines(shown, UI.font("n900"), 11, 56)), "n900", 11, UI.INK, 0, 1.0)
	name_l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	name_l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	name_l.position = Vector2(2, 32)
	name_l.size = Vector2(58, 34)
	name_l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	t.add_child(name_l)
	if new:
		var tag := _chip("New", Color("#E9C46A"), UI.INK)
		UI.at(tag, 30, -10)
		t.add_child(tag)
	return t


## One ability's tile: its name, score and a coin per point; the placed point's coin is ringed green. Dimmed at the cap.
func _tile(i: int, m: Dictionary, k: String) -> Control:
	var mine: bool = placed.get(i, "") == k
	var n: int = Races.score(m, k) + (1 if mine else 0)
	var capped := Races.score(m, k) >= CAP
	var b := Button.new()
	b.accessibility_name = k
	b.custom_minimum_size = Vector2(120, 58)
	b.add_theme_stylebox_override("normal", UI.box(UI.CREAM_LIGHT, 12, UI.GREEN if mine else UI.CREAM_EDGE, 3 if mine else 2))
	for s in ["hover", "pressed", "focus", "disabled"]:
		b.add_theme_stylebox_override(s, b.get_theme_stylebox("normal"))
	b.disabled = capped
	b.modulate.a = 0.45 if capped else 1.0
	b.pressed.connect(place.bind(k))
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 6)
	h.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 8)
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var names := VBoxContainer.new()
	names.add_theme_constant_override("separation", 0)
	names.mouse_filter = Control.MOUSE_FILTER_IGNORE
	names.add_child(UI.label(k, "n900", 11, UI.INK, 1))
	names.add_child(UI.label(str(n), "lilita", 24, UI.INK, 0, 1.0))
	h.add_child(names)
	var coins := HBoxContainer.new()
	coins.add_theme_constant_override("separation", -6)   # past what fits they overlap slightly (07 -> coins stay on one line)
	coins.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	coins.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for c in n:
		var cv := CoinView.blank(18)
		if mine and c == n - 1:
			cv.ring = UI.GREEN
		coins.add_child(cv)
	h.add_child(coins)
	b.add_child(h)
	return b
