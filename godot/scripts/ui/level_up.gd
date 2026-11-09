class_name LevelUp
extends Control
## The Level-up screen (design/07 -> Level-up; built from LevelUp v9a / v9b and v8c / v8d, mockups/rewards-and-level-up/),
## in the mockups' 844 x 390 layout fitted to the safe area: the top bar (back to the map, "Level up!", the party level, the
## step chips), the character card on the left (portrait, name, subtitle, the Max HP pill) and the choices on the right.
## One character at a time, hero first, then the Party step with the level's terrain card (06: one of three into the hand).
## Each step shows only what the level grants (Progression.sections):
##   mastery (level 2, martials): a weapon's root hex; tapping it opens the Weapon mastery screen to train (07 v5c)
##   class_cards (level 3, martials): "Your class cards", the kit drawn large, the new card tagged (07 v9a)
##   spells (level 3, casters): two slots on top that fill as you pick; every level-3 spell in a column per school (07 v9a)
##   feat (levels 4 and 12): the list and the details panel, Back and Next inside it (07 v8b, v9b)
##   points (levels 4, 8, 12, 16): "Place 1 ability point", six coin tiles (07 v8d)
##   subclass (level 5): the subclass hexes, then "You gain" (martials) or "Pick a spell" (casters) (07 v8c)
##   follow (level 5, Shifter, Companion ranger, Holy Defender): the form, beast or god, as hexes (no mockup)
## A character with nothing to choose at this level is skipped; its chip shows done. Back to map keeps the choices (the
## banner waits on the map); Done applies them (Game.level_picked).
## The step list keeps LevelPick's shape ([member index, section], then "terrain"), so the checks drive it the same way.

signal left   # Back to map, the choices kept

const CAP := 6                     # DOCS (03 -> Ability scores): no score above 6
const ABILITIES := ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
const BG := Color("#BFD9D2")
const PANEL := Color("#F6EEDF")
const PANEL_EDGE := Color("#CDB894")
const LINE := Color("#E2D5BC")
const SOFT := Color("#43524D")
const CAP_INK := Color("#5A5040")
const BAND := Color("#B5532F")
const BAND_INK := Color("#9A4A12")
const PICKED_BG := Color("#FFF4E8")
const FOCUS := Color("#3F86C8")
const TODO := Color("#E07A2F")
const DONE_GREEN := Color("#2E7A3E")
const OFF_BG := Color("#E6DCC8")
const OFF_INK := Color("#6B6152")
const BACK_ICON := "M15 5l-7 7 7 7"
const TICK := "M5 12l5 5 9-10"
const LOCK := "M6 11h12v10H6z M8.5 11V8a3.5 3.5 0 0 1 7 0v3"
const HEART := "M12 21s-7.5-4.6-9.5-10A5 5 0 0 1 12 6.5 5 5 0 0 1 21.5 11c-2 5.4-9.5 10-9.5 10z"
const UP := "M12 19V5 M6 11l6-6 6 6"
## Martial subclass icons (the mockups' placeholders, 07 v8c); the rangers' aren't in a mockup (PLACEHOLDER star).
const SUB_ICON := {"Brawler": "M7 11V7a2 2 0 0 1 4 0v3 M11 10V6a2 2 0 0 1 4 0v4 M15 10V8a2 2 0 0 1 4 0v5c0 4-3 7-7 7s-6-2-7-5l-1-3a2 2 0 0 1 3-2l1 1",
	"Holy Defender": "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z M12 8v6 M9 11h6", "Tactician": "M6 21V4 M6 4h11l-3 4 3 4H6",
	"Arcane Knight": "M12 3l7 4v10l-7 4-7-4V7z M12 8v8 M9 10l6 4 M15 10l-6 4", "Con Artist": "M4 8c3-2 13-2 16 0 0 6-3 10-8 10S4 14 4 8z M8.5 11h2 M13.5 11h2",
	"Assassin": "M14 3l7 7-9 9-3-1-1-3z M5 19l3-3", "Gambler": "M5 5h14v14H5z M9 9h.01 M15 9h.01 M12 12h.01 M9 15h.01 M15 15h.01",
	"Arcane Trickster": "M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z"}
const STAR := "M12 2l3 6 6 .9-4.5 4.3 1 6.3L12 16.6 6.5 19.5l1-6.3L3 8.9 9 8z"
## Feat groups (07 v8b): name, icon, rim, face, ink.
const FGROUP := {"General": ["General", STAR, "#5F7F99", "#EAF0F4", "#3E5A70"],
	"Race": ["Race", "M5 19c0-8 6-14 15-14 0 9-6 15-14 15 M5 19l7-7", "#4F7A33", "#EEF5E4", "#3D6128"],
	"Background": ["Background", "M4 11l8-6 8 6 M6 10v9h12v-9", "#9A4A12", "#FFF1E2", "#9A4A12"]}

var game: Game
var _level := 0
var _options := []
var _members := []       # who places a point this level (the party at a score level), or none
var _party := []         # everyone who levels
var step := 0            # the step showing now; == _steps().size() for the Party step
var placed := {}         # member index -> the ability its point went on
var picks := {}          # member index -> {mastery: [cat, id], spells: [], feat, follow, subclass, sub_follow, tier1}
var terrain := ""        # the Party step's terrain card
var show_all := false    # the feat list's Show all toggle (07: off by default)
var _focus := ""         # the choice whose pop-up is open (or whose details show, on the feat step)
var _pending := {}       # member index -> the follow-up chip tapped in the feat details
var _safe := SafeArea.new()
var _root := Control.new()


static func attach(g: Game) -> LevelUp:
	var p := LevelUp.new()
	p.game = g
	p.name = "level_up"
	p.visible = false
	p.set_anchors_preset(Control.PRESET_FULL_RECT)
	p.mouse_filter = Control.MOUSE_FILTER_STOP
	g.ui.add_child(p)
	return p


func _ready() -> void:
	accessibility_name = "Level up"
	add_child(_safe)
	_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_safe.add_child(_root)
	_root.resized.connect(func():
		if visible:
			_build())


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), BG)


## A new level's choices, from the first character. members: who places a point (the party at a score level).
func open(level: int, options: Array, members := []) -> void:
	_level = level
	_options = options
	_members = members
	_party = game.party.duplicate() if game != null else members
	step = 0
	placed = {}
	picks = {}
	terrain = ""
	for i in _party.size():
		picks[i] = {"mastery": [], "spells": [], "feat": "", "follow": "", "subclass": "", "sub_follow": "", "tier1": ""}
	show_all = false
	_focus = ""
	_pending = {}
	show_again()


## Opens the screen on the choices already made (the banner, Level up now).
func show_again() -> void:
	visible = true
	move_to_front()
	_build()


func _bg() -> String:
	return game.run.background if game != null and game.run != null else ""


## Every step this level: [member index, section], in order. A Shifter's form, a Companion's beast or a Holy Defender's god
## follows the subclass once one is chosen.
func _steps() -> Array:
	var out := []
	for i in _party.size():
		var m: Dictionary = _party[i]
		var secs := Progression.sections(m, _level, _bg()) if int(m.get("levelled", 1)) < _level else []
		for s: String in secs:
			out.append([i, s])
			if s == "subclass" and picks[i].subclass != "" and Progression.SUBCLASSES[Progression.klass(m)][picks[i].subclass].has("follow"):
				out.append([i, "follow"])
		if i < _members.size():
			out.append([i, "points"])
	return out


## The test bots' pick: each member's point on its main score, or its highest score under the cap; the built options first
## for the rest (Progression's bot picks), then the first terrain card.
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
	terrain = _options[0]
	finish()


## Done: the level's choices go in (Game.level_picked closes the screen).
func finish() -> void:
	if terrain == "":
		terrain = _options[0]
	game.level_picked(terrain, placed, picks)


## Places this member's point (or moves it; tapping the same tile again takes it back, as in the mockup).
func place(ability: String) -> void:
	var i := _who()
	if i < 0 or Races.score(_party[i], ability) >= CAP:
		return
	placed[i] = ability
	_build()


## On to the next step, once this one is done.
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


## Back to the map: the screen closes and the choices wait (07 -> Level-up).
func leave() -> void:
	visible = false
	_focus = ""
	left.emit()


## Whose step this is, or -1 on the Party step.
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
			var left_n := 0
			for g in Progression.spell_groups_3(m).values():
				left_n += g.size()
			return p.spells.size() >= mini(Progression.SPELL_PICKS_3, left_n)
		"feat":
			return p.feat != "" and (not Progression.feat_of(p.feat).has("follow") or p.follow != "")
		"subclass":
			return p.subclass != "" and (not Progression.klass(m) in Progression.CASTERS or p.tier1 != "" or _tier1_of(m, p.subclass).is_empty())
		"follow":
			return p.sub_follow != ""
	return true


## Every one of a member's steps done (its chip's tick).
func _member_done(i: int) -> bool:
	return _steps().filter(func(s): return s[0] == i).all(func(s): return _done(s))


func _tier1_of(m: Dictionary, sub: String) -> Array:
	var src: Dictionary = Progression.WIZARD_T1 if Progression.klass(m) == "wizard" else Progression.CLERIC_T1
	return src.get(sub, []).filter(func(id): return not id in m.get("cards", []))


# --- Building the screen -------------------------------------------------------------------------------------------

func _build() -> void:
	if not is_inside_tree():
		return
	var scroll := CUI.scroll_of(_root)
	for c in _root.get_children():
		_root.remove_child(c)
		c.queue_free()
	var w := maxf(_root.size.x, 844.0) if _root.size.x <= 0 else _root.size.x
	var steps := _steps()
	var sec: String = steps[step][1] if step < steps.size() else "terrain"
	var i: int = steps[step][0] if step < steps.size() else -1
	_build_top(w, i)
	_build_card(i)
	var panel := _panel(Vector4(14, 12, 14, 12))
	UI.at(panel, 210, 76)
	panel.custom_minimum_size = Vector2(w - 222, 302)
	panel.size = panel.custom_minimum_size
	var v := CUI.vbox(8)
	panel.add_child(v)
	var body := CUI.vbox(12)
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(body)
	var m: Dictionary = _party[i] if i >= 0 else {}
	match sec:
		"terrain":
			body.add_child(_terrain_section())
		"points":
			body.add_child(_points_section(i, m))
		"mastery":
			body.add_child(_mastery_section(i, m))
		"class_cards":
			body.add_child(_kit_section(m))
		"spells":
			body.add_child(_spells_section(i, m))
		"feat":
			body.add_child(_feat_section(i, m, w - 222 - 28))
		"subclass":
			body.add_child(_subclass_section(i, m))
		"follow":
			body.add_child(_follow_section(i, m))
	if sec != "feat":   # the feat step's Back and Next sit in its details panel (07 v9b)
		v.add_child(_footer(false))
	_root.add_child(panel)
	CUI.keep_scroll(_root, scroll)


## Back to the map, "Level up!", "Party level 4 → 5", and the step chips (07: who's done).
func _build_top(w: float, who: int) -> void:
	var back := HexShape.make(44, 51, UI.RIM, UI.CREAM_LIGHT, 3).with_icon(BACK_ICON, Color("#33403B"), 18, 2.6).with_shadow(UI.HEX_SHADOW, 4)
	back.clickable = true
	back.accessibility_name = "Back to map"
	back.pressed.connect(leave)
	UI.at(back, 12, 12)
	_root.add_child(back)
	var words := CUI.vbox(0)
	words.add_child(UI.label("Level up!", "lilita", 22, UI.INK, 0, 1.05))
	words.add_child(UI.label("Party level %d → %d" % [_level - 1, _level], "n800", 12, SOFT))
	UI.at(words, 68, 16)
	_root.add_child(words)
	var chips := CUI.hbox(6)
	for k in _party.size():
		var m: Dictionary = _party[k]
		var on := k == who
		var done := _member_done(k)
		var h := HexShape.make(35, 40, BAND if on else UI.RIM, Color(m.color), 3).with_text(m.initial, 15)
		h.shadow = Color("#7E9A92")
		h.modulate.a = 1.0 if on or done else 0.55
		h.accessibility_name = "%s%s" % [m.name, ", current step" if on else (", done" if done else ", to do")]
		if done and not on:
			var d := CUI.Dot.make(16, DONE_GREEN, TICK, 10)
			UI.at(d, 23, 26)
			h.add_child(d)
		chips.add_child(h)
	var on_party := who < 0
	var pill := _TagChip.new()
	pill.text = "Party"
	pill.rim = BAND if on_party else UI.RIM
	pill.custom_minimum_size = Vector2(64, 40)
	pill.modulate.a = 1.0 if on_party or terrain != "" else 0.55
	pill.accessibility_name = "Party milestone%s" % (", current step" if on_party else "")
	if terrain != "" and not on_party:
		var d := CUI.Dot.make(16, DONE_GREEN, TICK, 10)
		UI.at(d, 52, 26)
		pill.add_child(d)
	chips.add_child(pill)
	UI.at(chips, 250, 17)
	_root.add_child(chips)


## The character card (portrait, name, subtitle, Max HP pill), or the party on the Party step. A pop-up covers it.
func _build_card(who: int) -> void:
	var card := _panel(Vector4(12, 14, 12, 14))
	UI.at(card, 12, 76)
	card.custom_minimum_size = Vector2(186, 302)
	card.size = card.custom_minimum_size
	var v := CUI.vbox(8)
	v.alignment = BoxContainer.ALIGNMENT_BEGIN
	card.add_child(v)
	if who >= 0:
		var m: Dictionary = _party[who]
		var face := HexShape.make(92, 106, UI.RIM, Color(m.color), 5).with_text(m.initial, 40).with_shadow(UI.HEX_SHADOW, 4)
		face.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		v.add_child(face)
		v.add_child(_centred(UI.label(m.name, "lilita", 18, UI.INK, 0, 1.1)))
		v.add_child(_centred(CUI.wrap(UI.label(_subtitle(m), "n800", 12, SOFT), 162)))
		var gain := Races.level_hp(m) + Races.extra_hp(m, _level) - Races.extra_hp(m, _level - 1)
		var hp := UI.panel(Color("#E9F3E2"), 17, Color("#9CC79A"), 2, Vector4(8, 0, 12, 0))
		hp.custom_minimum_size.y = 34
		hp.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		var row := CUI.hbox(6)
		var heart := UI.icon_rect(HEART, Color("#C4542A"), 18, 2.2, true)
		heart.custom_minimum_size = Vector2(18, 18)
		heart.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		row.add_child(heart)
		var t := UI.label("Max HP +%d" % gain, "lilita", 16, Color("#2E6B3A"))
		t.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		row.add_child(t)
		hp.add_child(row)
		hp.accessibility_name = "Max HP up by %d" % gain
		var gap := Control.new()
		gap.custom_minimum_size.y = 2
		v.add_child(gap)
		v.add_child(hp)
	else:
		var grid := GridContainer.new()
		grid.columns = 2
		grid.add_theme_constant_override("h_separation", 6)
		grid.add_theme_constant_override("v_separation", 6)
		grid.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		for m: Dictionary in _party:
			grid.add_child(HexShape.make(44, 51, UI.RIM, Color(m.color), 3).with_text(m.initial, 18).with_shadow(UI.HEX_SHADOW))
		var gap := Control.new()
		gap.custom_minimum_size.y = 8
		v.add_child(gap)
		v.add_child(grid)
		v.add_child(_centred(UI.label("The party", "lilita", 18, UI.INK, 0, 1.1)))
	_root.add_child(card)
	if _focus != "":
		_pop.call_deferred(who)


## The subtitle at the new level: "Race Class (Subclass) · Lv" (07 -> Screen text), with the subclass once picked.
func _subtitle(m: Dictionary) -> String:
	var i := _party.find(m)
	var sc: String = picks[i].subclass if picks.has(i) and picks[i].subclass != "" else Progression.sub(m)
	if m == game.party[0] and Hero.current != null:
		return Hero.current.subtitle(_level, sc)
	if ActionCards.COMPANION.has(m.name):
		return Hero.subtitle_of(ActionCards.COMPANION[m.name][0], ActionCards.COMPANION[m.name][1], sc, _level)
	var race: String = m.get("sub", "") if m.get("sub", "") != "" and m.get("race", "") in ["Elf", "Dwarf"] else m.get("race", "")
	return Hero.subtitle_of(race, "Fighter", sc, _level)


## Back, then Next (off until the step is done) or Done on the Party step.
func _footer(compact: bool) -> Control:
	var row := CUI.hbox(6 if compact else 10)
	row.alignment = BoxContainer.ALIGNMENT_END
	if not compact:
		row.add_child(CUI.spring())
	var steps := _steps()
	if step > 0:
		var b := _PillButton.new()
		b.text = "Back"
		b.custom_minimum_size = Vector2(0 if compact else 0, 36 if compact else 42)
		b.font_px = 12 if compact else 13
		b.pressed.connect(back)
		row.add_child(b)
	var last := step >= steps.size()
	var on := _done(steps[step]) if not last else terrain != ""
	var label := "Done"
	if not last:
		var nxt := step + 1
		if nxt < steps.size() and steps[nxt][0] == steps[step][0]:
			label = "Next"   # the same character's next page (the feat, then the point; the subclass, then the follow-up)
		else:
			label = "Next: %s" % (String(_party[steps[nxt][0]].name) if nxt < steps.size() else "Party")
	var f := UI.font("lilita")
	var px := 14 if compact else 15
	var go := TagButton.make(label, f.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, px).x + (40 if compact else 52), 36 if compact else 42, px)
	go.cut = 10.0 if compact else 12.0
	go.accessibility_name = label
	if compact:
		go.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	if not on:
		go.bg = OFF_BG
		go.ink = OFF_INK
		go.drop = 0.0
		go.mouse_filter = Control.MOUSE_FILTER_IGNORE
	go.pressed.connect(next if not last else finish)
	row.add_child(go)
	return row


# --- Sections ------------------------------------------------------------------------------------------------------

## A section title with its dot: orange until done, then a green tick (07 -> Level-up, no to-do line).
func _title(text: String, done: Variant = null) -> HBoxContainer:
	var h := CUI.hbox(7)
	h.add_child(UI.label(text, "lilita", 16, UI.INK, 0, 1.1))
	if done != null:
		var dot := CUI.Dot.make(16, DONE_GREEN if done else TODO, TICK if done else "", 10)
		dot.accessibility_name = "%s: %s" % [text, "done" if done else "to do"]
		h.add_child(dot)
	return h


## Level 8 and 16 (and 4 and 12, after the feat): six large coin tiles, two rows of three (07 v8d).
func _points_section(i: int, m: Dictionary) -> Control:
	var v := CUI.vbox(6)
	v.add_child(_title("Place 1 ability point", placed.has(i) or _full(m)))
	var grid := GridContainer.new()
	grid.columns = 3
	grid.add_theme_constant_override("h_separation", 8)
	grid.add_theme_constant_override("v_separation", 8)
	for k: String in ABILITIES:
		grid.add_child(_tile(i, m, k))
	v.add_child(grid)
	return v


## One ability's tile: name, score and a coin per point, the placed coin ringed green; dimmed at the cap.
func _tile(i: int, m: Dictionary, k: String) -> Control:
	var mine: bool = placed.get(i, "") == k
	var n: int = Races.score(m, k) + (1 if mine else 0)
	var capped := Races.score(m, k) >= CAP
	var b := Button.new()
	b.accessibility_name = k
	b.custom_minimum_size = Vector2(0, 96)
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b.add_theme_stylebox_override("normal", CUI.tile_box(DONE_GREEN if mine else LINE, 2.5, 12, Vector4(10, 6, 10, 6), Color("#E9F3E2") if mine else UI.CREAM_LIGHT))
	for s in ["hover", "pressed", "focus", "disabled"]:
		b.add_theme_stylebox_override(s, b.get_theme_stylebox("normal"))
	b.disabled = capped
	b.modulate.a = 0.45 if capped else 1.0
	b.pressed.connect(func():
		if mine:
			placed.erase(i)
			_build()
		else:
			place(k))
	var h := CUI.hbox(10)
	h.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 10)
	var names := CUI.vbox(1)
	names.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	names.add_child(UI.label(k, "n900", 13, UI.INK, 1))
	names.add_child(UI.label(str(n), "lilita", 34, Color("#2E6B3A") if mine else UI.INK, 0, 1.0))
	h.add_child(names)
	h.add_child(CUI.spring())
	var coins := CUI.hbox(-6 if n > 6 else 3)   # past what fits they overlap a little (07 -> coins stay on one line)
	coins.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	for c in n:
		var cv := CoinView.blank(18)
		if mine and c == n - 1:
			cv.ring = UI.GREEN
		coins.add_child(cv)
	h.add_child(coins)
	b.add_child(h)
	return b


## Level 3, martials: "Your class cards", the whole kit large, the level-3 card tagged New with a gold glow (07 v9a).
func _kit_section(m: Dictionary) -> Control:
	var v := CUI.vbox(10)
	v.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(_title("Your class cards"))
	var row := CUI.hbox(28)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.size_flags_vertical = Control.SIZE_EXPAND_FILL
	var k := Progression.klass(m)
	var ids: Array = Weapons.CLASS_CARDS.get(k, []).filter(func(id): return id in m.get("cards", [])) + [Progression.LEVEL3_CARD.get(k, "")]
	for id: String in ids:
		if id == "":
			continue
		var new: bool = id == Progression.LEVEL3_CARD.get(k, "")
		var c := Cards.get_card(id)
		var col := CUI.vbox(8)
		col.custom_minimum_size.x = 170
		col.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		var big := _BigCard.make(c, new)
		big.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		var open: bool = _focus == "kit." + id
		big.focused = open
		big.set_meta("key", "kit." + id)
		big.set_meta("pop", {"tag": "%s · %d AP" % ["New card" if new else "Class card", c.ap], "name": c.n, "text": text_of(c),
			"lines": [["Use", _use(c)]] if _use(c) != "" else []})
		big.pressed.connect(_toggle.bind("kit." + id))
		col.add_child(big)
		var t := CUI.wrap(UI.label(text_of(c), "n700", 12, SOFT, 0, 1.3), 170)
		t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		col.add_child(t)
		if _use(c) != "":
			var chip := UI.panel(Color("#F1E8D8"), 10, Color(0, 0, 0, 0), 0, Vector4(8, 1, 8, 1))
			chip.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
			chip.add_child(UI.label(_use(c), "n900", 11, CAP_INK))
			col.add_child(chip)
		row.add_child(col)
	v.add_child(row)
	return v


func _use(c: Dictionary) -> String:
	return {"turn": "Once per turn", "fight": "Once per fight"}.get(c.get("limit", ""), "")


## Level 3, casters: "Pick 2 spells", the slots that fill, then every level-3 spell in a column per school or order (07 v9a).
func _spells_section(i: int, m: Dictionary) -> Control:
	var v := CUI.vbox(10)
	var mine: Array = picks[i].spells
	var head := CUI.vbox(6)
	head.add_child(_title("Pick %d spells" % Progression.SPELL_PICKS_3, _done([i, "spells"])))
	var slots := CUI.hbox(8)
	for n in Progression.SPELL_PICKS_3:
		if n < mine.size():
			var id: String = mine[n]
			var card := _SmallCard.make(Cards.get_card(id), Progression.SCHOOL_ICON.get(_school_of(m, id), ""))
			card.picked = true
			card.accessibility_name = "Spell slot %d: %s. Tap to clear" % [n + 1, Cards.ALL[id].n]
			card.pressed.connect(func():   # tapping a filled slot clears it (07 v9a)
				picks[i].spells.erase(id)
				_focus = ""
				_build())
			slots.add_child(card)
		else:
			slots.add_child(_SmallCard.empty("Spell %d" % (n + 1)))
	head.add_child(slots)
	v.add_child(head)
	var groups := Progression.spell_groups_3(m)
	var grid := GridContainer.new()
	grid.columns = maxi(groups.size(), 1)
	grid.add_theme_constant_override("h_separation", 10)
	for g: String in groups:
		var col := CUI.vbox(5)
		col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var gh := CUI.hbox(5)
		gh.add_child(UI.icon_rect(Progression.SCHOOL_ICON.get(g, ""), CAP_INK, 14, 2.2))
		gh.add_child(UI.label(g.replace("Order of ", "").to_upper(), "n900", 11, CAP_INK, 1))   # the column's icon names the order
		col.add_child(gh)
		for id: String in groups[g]:
			var c := Cards.get_card(id)
			var on: bool = id in mine
			var full: bool = mine.size() >= Progression.SPELL_PICKS_3
			var key := "sp." + id
			var row := _Row.make(c.n, c.ap, on, _focus == key)
			row.custom_minimum_size.y = 34
			row.set_meta("key", key)
			var lines := [["Order" if Progression.klass(m) == "cleric" else "School", g]]
			if full and not on:
				lines.append(["Replaces", Cards.ALL[mine[0]].n])
			row.set_meta("pop", {"tag": "Spell · %d AP" % c.ap, "name": c.n, "text": text_of(c), "lines": lines,
				"button": "Remove" if on else "Choose", "act": func():
					if on:
						picks[i].spells.erase(id)
					else:
						if picks[i].spells.size() >= Progression.SPELL_PICKS_3:
							picks[i].spells.pop_front()   # a third pick swaps out the first (07 v9a)
						picks[i].spells.append(id)})
			row.pressed.connect(_toggle.bind(key))
			col.add_child(row)
		grid.add_child(col)
	v.add_child(grid)
	return v


func _school_of(m: Dictionary, id: String) -> String:
	for src: Dictionary in [Progression.WIZARD_3, Progression.CLERIC_3, Progression.WIZARD_T1, Progression.CLERIC_T1]:
		for g: String in src:
			if id in src[g]:
				return g
	return ""


## Level 5: "Subclass" (hexes; the companion's default tagged), then "You gain" (martials: the new card and the upgraded
## one) or "Pick a spell" (casters: the new school's tier 1), drawn as action cards; empty dashed slots until a subclass
## is chosen (07 v8c).
func _subclass_section(i: int, m: Dictionary) -> Control:
	var v := CUI.vbox(14)
	var k := Progression.klass(m)
	var sid: String = picks[i].subclass
	var top := CUI.vbox(6)
	top.add_child(_title("Subclass", sid != ""))
	var row := CUI.hbox(10)
	for name: String in Progression.SUBCLASSES[k]:
		var s: Dictionary = Progression.SUBCLASSES[k][name]
		var on := sid == name
		var key := "sub." + name
		var hx := _HexChoice.make(name, SUB_ICON.get(name, Progression.SCHOOL_ICON.get(name, STAR)), on, _focus == key, Progression.DEFAULT_SUBCLASS.get(m.name, "") == name)
		hx.set_meta("key", key)
		var lines := []
		if s.has("card"):
			var c := Cards.get_card(s.card)
			lines = [["New card · %d AP" % c.ap, "%s: %s" % [c.n, text_of(c)]], ["Upgrade · %s → %s" % [Cards.ALL[s.of].n, s.n], s.text]]
		else:
			lines = [["Spells to pick from", ", ".join(_tier1_of(m, name).map(func(id): return Cards.ALL[id].n))]]
		hx.set_meta("pop", {"tag": "Subclass" + (" · Default" if Progression.DEFAULT_SUBCLASS.get(m.name, "") == name else ""), "name": name,
			"text": s.blurb, "lines": lines, "button": "Choose" if not on else "", "picked": on, "act": func():
				if picks[i].subclass != name:
					picks[i].sub_follow = ""
					picks[i].tier1 = ""
				picks[i].subclass = name})
		hx.pressed.connect(_toggle.bind(key))
		row.add_child(hx)
	top.add_child(row)
	v.add_child(top)
	var bottom := CUI.vbox(6)
	var caster := k in Progression.CASTERS
	bottom.add_child(_title("Pick a spell" if caster else "You gain", (picks[i].tier1 != "") if caster else null))
	var gains := CUI.hbox(6)
	if sid == "":
		for n in (3 if caster else 2):
			var e := _SmallCard.empty("")
			e.accessibility_name = "Choose a subclass first"
			e.lift = 8.0
			gains.add_child(e)
	elif caster:
		for id: String in _tier1_of(m, sid):
			var c := Cards.get_card(id)
			var on: bool = picks[i].tier1 == id
			var key := "t1." + id
			var card := _SmallCard.make(c, Progression.SCHOOL_ICON.get(sid, ""))
			card.picked = on
			card.focused = _focus == key
			card.lift = 0.0 if on else 8.0
			card.set_meta("key", key)
			card.set_meta("pop", {"tag": "Spell · %d AP" % c.ap, "name": c.n, "text": text_of(c), "lines": [],
				"button": "Choose" if not on else "", "picked": on, "act": func(): picks[i].tier1 = id})
			card.pressed.connect(_toggle.bind(key))
			gains.add_child(card)
	else:
		var s: Dictionary = Progression.SUBCLASSES[k][sid]
		var c := Cards.get_card(s.card)
		var card := _SmallCard.make(c, c.icon)
		card.new_tag = true
		card.lift = 8.0
		card.focused = _focus == "gain.card"
		card.set_meta("key", "gain.card")
		card.set_meta("pop", {"tag": "New card · %d AP" % c.ap, "name": c.n, "text": text_of(c), "lines": []})
		card.pressed.connect(_toggle.bind("gain.card"))
		gains.add_child(card)
		var old := Cards.get_card(s.of)
		var up := _SmallCard.make(old, old.icon)
		up.shown_name = s.n
		up.up_badge = true
		up.lift = 8.0
		up.focused = _focus == "gain.up"
		up.set_meta("key", "gain.up")
		up.set_meta("pop", {"tag": "Upgrade", "name": s.n, "text": s.text, "lines": [] if String(s.n).begins_with(old.n) else [["Replaces", old.n]]})
		up.pressed.connect(_toggle.bind("gain.up"))
		gains.add_child(up)
	bottom.add_child(gains)
	v.add_child(bottom)
	return v


## A Shifter's form, a Companion ranger's beast or a Holy Defender's god, as hexes (no mockup: the subclass row's look).
func _follow_section(i: int, m: Dictionary) -> Control:
	var s: Dictionary = Progression.SUBCLASSES[Progression.klass(m)][picks[i].subclass]
	var src: Dictionary = {"form": Progression.FORMS, "beast": Progression.BEASTS, "god": Progression.GODS}[s.follow]
	var v := CUI.vbox(6)
	v.add_child(_title({"form": "Pick a form", "beast": "Pick a beast", "god": "Pick a god"}[s.follow], picks[i].sub_follow != ""))
	var flow := HFlowContainer.new()
	flow.add_theme_constant_override("h_separation", 10)
	flow.add_theme_constant_override("v_separation", 8)
	for name: String in src:
		var card_id: String = src[name] if s.follow == "god" else src[name].card
		var c := Cards.get_card(card_id)
		var tag: String = {"form": src[name].feel if s.follow == "form" else "", "beast": "Beast", "god": Progression.GOD_OF.get(name, "").capitalize()}[s.follow]
		var text: String = src[name].text if s.follow == "beast" else text_of(c)
		var on: bool = picks[i].sub_follow == name
		var key := "fol." + name
		var hx := _HexChoice.make(name, c.icon, on, _focus == key, false)
		hx.set_meta("key", key)
		hx.set_meta("pop", {"tag": tag, "name": name, "text": text, "lines": [["New card · %d AP" % c.ap, c.n]],
			"button": "Choose" if not on else "", "picked": on, "act": func(): picks[i].sub_follow = name})
		hx.pressed.connect(_toggle.bind(key))
		flow.add_child(hx)
	v.add_child(flow)
	return v


## Level 2, martials: "Weapon mastery", a root hex per weapon the character holds; tapping one opens the Weapon mastery
## screen to train a node (07 -> Weapon mastery screen, v5c). The node picked shows beside it.
func _mastery_section(i: int, m: Dictionary) -> Control:
	var v := CUI.vbox(10)
	v.add_child(_title("Weapon mastery", not picks[i].mastery.is_empty()))
	var row := CUI.hbox(28)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	for cat: String in [m.get("weapon", ""), m.get("off", "")]:
		if not MasteryData.TREES.has(cat) or not Progression.MASTERY.has(cat):
			continue
		var col := CUI.vbox(8)
		col.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		var root := MasteryScreen.root_hex(cat)
		root.clickable = true
		root.accessibility_name = "%s mastery" % MasteryData.TREES[cat].n
		root.pressed.connect(_train.bind(i, cat))
		root.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		col.add_child(root)
		var go := CUI.choose_button("Train", 120)
		go.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		go.pressed.connect(_train.bind(i, cat))
		col.add_child(go)
		if picks[i].mastery.size() == 2 and picks[i].mastery[0] == cat:
			for node: Dictionary in Progression.MASTERY[cat]:
				if node.id == picks[i].mastery[1]:
					var chip := CUI.hbox(5)
					chip.alignment = BoxContainer.ALIGNMENT_CENTER
					chip.add_child(CUI.Dot.make(16, DONE_GREEN, TICK, 10))
					chip.add_child(UI.label("%s · %s" % [node.branch, node.n], "n900", 12, UI.INK))
					col.add_child(chip)
		col.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
		row.add_child(col)
	v.add_child(row)
	return v


## Opens the Weapon mastery screen to train one node for this level; Back returns here.
func _train(i: int, cat: String) -> void:
	var ms := MasteryScreen.new(game, _party[i], cat, picks[i].mastery)
	ms.trained.connect(func(c: String, id: String):
		picks[i].mastery = [c, id]
		_build())
	game.ui.add_child(ms)


## Levels 4 and 12: the feat list (own race and background first; Show all adds the rest, faded and locked) and the details
## panel with Choose, the follow-up chips, and Back and Next (07 v8b, v9b).
func _feat_section(i: int, m: Dictionary, w: float) -> Control:
	var row := CUI.hbox(12)
	row.size_flags_vertical = Control.SIZE_EXPAND_FILL
	var left_col := CUI.vbox(6)
	left_col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var head := _title("Pick a feat", _done([i, "feat"]))
	head.add_child(CUI.spring())
	var sw := _Switch.new()
	sw.on = show_all
	sw.pressed.connect(func():
		show_all = not show_all
		_build())
	head.add_child(sw)
	left_col.add_child(head)
	var list := CUI.vbox(5)
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var shown := []
	for g in ["Race", "Background", "General"]:
		var fs: Array = Progression.FEATS.filter(func(f): return f.group == g and (show_all or Progression.missing(m, f, _bg()) == ""))
		if fs.is_empty():
			continue
		list.add_child(UI.label(g.to_upper(), "n900", 11, CAP_INK, 1))
		for f: Dictionary in fs:
			shown.append(f)
			list.add_child(_feat_row(i, m, f))
	var sc := ScrollContainer.new()
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	sc.custom_minimum_size = Vector2(w - 232 - 12, 236)
	sc.add_child(list)
	left_col.add_child(sc)
	row.add_child(left_col)
	var cur := _feat_shown(i, m, shown)
	row.add_child(_feat_details(i, m, cur))
	return row


## The feat in the details panel: the one tapped, else the chosen one, else the first the character qualifies for.
func _feat_shown(i: int, m: Dictionary, shown: Array) -> Dictionary:
	if _focus.begins_with("feat."):
		var f := Progression.feat_of(_focus.substr(5))
		if not f.is_empty():
			return f
	if picks[i].feat != "":
		return Progression.feat_of(picks[i].feat)
	for f: Dictionary in shown:
		if Progression.missing(m, f, _bg()) == "":
			return f
	return shown[0] if not shown.is_empty() else {}


func _feat_row(i: int, m: Dictionary, f: Dictionary) -> Control:
	var miss := Progression.missing(m, f, _bg())
	var chosen: bool = picks[i].feat == f.id
	var key: String = "feat." + f.id
	var g: Array = FGROUP[f.group]
	var t := CUI.Tap.new(f.n)
	t.set_meta("key", key)
	t.custom_minimum_size = Vector2(0, 50)
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var sel := _focus == key or (_focus == "" and chosen)
	t.draw.connect(func():
		t.draw_style_box(CUI.tile_box(BAND if chosen else (FOCUS if sel else LINE), 2.5 if chosen or sel else 2.0, 12, Vector4.ZERO, PICKED_BG if chosen else UI.CREAM_LIGHT), Rect2(Vector2.ZERO, t.size)))
	t.modulate.a = 1.0 if miss == "" else 0.6
	var h := CUI.hbox(8)
	h.set_anchors_preset(Control.PRESET_FULL_RECT)
	h.offset_left = 6
	h.offset_right = -10
	var hx := HexShape.make(28, 32, Color(g[2]), Color(g[3]), 2.5).with_icon(g[1] if miss == "" else LOCK, Color(g[4]), 15, 2.2)
	hx.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(hx)
	var words := CUI.vbox(0)
	words.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	words.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var name: String = f.n
	if chosen and picks[i].follow != "":
		name += " · " + (picks[i].follow.capitalize() if f.follow == "weapon" else picks[i].follow)
	words.add_child(UI.label(name, "n900", 12, UI.INK, 0, 1.15))
	var line := UI.label(f.text, "n700", 11, SOFT, 0, 1.2)
	line.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	line.max_lines_visible = 2
	line.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	words.add_child(line)
	h.add_child(words)
	var need := Progression.need_text(f)
	if need != "":
		var chip := UI.panel(Color("#E9F3E2") if miss == "" else Color("#F3E3DC"), 10, Color(0, 0, 0, 0), 0, Vector4(7, 1, 7, 1))
		chip.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		chip.add_child(UI.label(need if miss == "" else miss, "n900", 11, Color("#2E6B3A") if miss == "" else Color("#8A3A22")))
		h.add_child(chip)
	if chosen:
		h.add_child(CUI.Dot.make(18, DONE_GREEN, TICK, 10))
	t.add_child(h)
	t.pressed.connect(func():
		_focus = key
		_build())
	return t


func _feat_details(i: int, m: Dictionary, f: Dictionary) -> Control:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", CUI.tile_box(LINE, 2, 14, Vector4(12, 10, 12, 10)))
	p.custom_minimum_size.x = 232
	var v := CUI.vbox(6)
	p.add_child(v)
	var body := CUI.vbox(6)
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(body)
	if not f.is_empty():
		var g: Array = FGROUP[f.group]
		var miss := Progression.missing(m, f, _bg())
		var chosen: bool = picks[i].feat == f.id
		body.add_child(UI.label(("%s feat" % g[0]).to_upper(), "n900", 11, Color(g[4]), 1))
		body.add_child(UI.label(f.n, "lilita", 18, UI.INK, 0, 1.1))
		body.add_child(CUI.wrap(UI.label(f.text, "n700", 12, SOFT, 0, 1.3), 204))
		var need := Progression.need_text(f)
		if need != "":
			var box := UI.panel(Color("#E9F3E2") if miss == "" else Color("#F3E3DC"), 10, Color(0, 0, 0, 0), 0, Vector4(8, 5, 8, 5))
			var nh := CUI.hbox(6)
			nh.add_child(UI.icon_rect(TICK if miss == "" else LOCK, Color("#2E6B3A") if miss == "" else Color("#8A3A22"), 12, 3.0))
			nh.add_child(UI.label("Needs " + need, "n900", 12, Color("#2E6B3A") if miss == "" else Color("#8A3A22")))
			box.add_child(nh)
			body.add_child(box)
		var ready := miss == ""
		if f.has("follow") and miss == "":
			var opts := Progression.follow_options(m, f)
			var cur: String = picks[i].follow if chosen else _pending.get(i, "")
			if opts.is_empty():
				var note := UI.panel(Color("#F1E8D8"), 10, Color(0, 0, 0, 0), 0, Vector4(8, 5, 8, 5))
				note.add_child(CUI.wrap(UI.label("Humans can already use every weapon." if m.get("race", "") == "Human" else "Your class can already use every weapon.", "n800", 11, CAP_INK), 196))
				body.add_child(note)
				ready = false
			else:
				body.add_child(UI.label(("Pick a proficiency" if f.follow == "proficiency" else "Pick a weapon category").to_upper(), "n900", 11, CAP_INK, 1))
				var flow := HFlowContainer.new()
				flow.add_theme_constant_override("h_separation", 4)
				flow.add_theme_constant_override("v_separation", 4)
				flow.custom_minimum_size.x = 204
				for o: String in opts:
					var shown_o: String = o.capitalize() if f.follow == "weapon" else o
					var b := _Chip.new()
					b.text = shown_o
					b.on = cur == o
					b.pressed.connect(func():
						_pending[i] = o
						if chosen:
							picks[i].follow = o
						_build())
					flow.add_child(b)
				body.add_child(flow)
				ready = ready and cur != ""
		if chosen and (not f.has("follow") or picks[i].follow != ""):
			body.add_child(_chosen_pill())
		elif miss == "":
			var choose := TagButton.make("Choose", 204, 36, 15)
			choose.cut = 10.0
			choose.drop = 3.0
			choose.accessibility_name = "Choose"
			if not ready:
				choose.bg = OFF_BG
				choose.ink = OFF_INK
				choose.drop = 0.0
				choose.mouse_filter = Control.MOUSE_FILTER_IGNORE
			choose.pressed.connect(func():
				picks[i].feat = f.id
				picks[i].follow = _pending.get(i, "") if f.has("follow") else ""
				_build())
			body.add_child(choose)
	var line := ColorRect.new()
	line.color = Color("#EFE5D3")
	line.custom_minimum_size.y = 2
	v.add_child(line)
	v.add_child(_footer(true))
	return p


## The Party step: "Add terrain cards" with its count, the level's three terrains to pick one from (06: one into the hand).
func _terrain_section() -> Control:
	var v := CUI.vbox(6)
	var head := _title("Add terrain cards", terrain != "")
	head.add_child(CUI.spring())
	head.add_child(UI.label("%d / 1" % (1 if terrain != "" else 0), "lilita", 15, Color("#2E6B3A") if terrain != "" else SOFT))
	v.add_child(head)
	var row := CUI.hbox(8)
	for t: String in _options:
		var on := terrain == t
		var col := CUI.vbox(3)
		var lift := Control.new()
		lift.custom_minimum_size.y = 0 if on else 6
		col.add_child(lift)
		var hx := HexShape.make(44, 51, BAND if on else UI.CREAM_LIGHT, UI.terrain_bg(t), 3).with_icon("t_" + t, UI.terrain_ink(t), 20)
		hx.shadow = UI.ORANGE_EDGE if on else UI.HEX_SHADOW
		hx.clickable = true
		hx.accessibility_name = Rules.NAMES[t] + (", picked" if on else "")
		hx.pressed.connect(func():
			terrain = "" if on else t
			_build())
		hx.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		col.add_child(hx)
		var n := UI.label(Rules.NAMES[t], "n900", 11, UI.INK)
		n.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		n.custom_minimum_size.x = 56
		col.add_child(n)
		row.add_child(col)
	v.add_child(row)
	return v


# --- The pop-up (07: the item pop-up's style; it covers the character card so the choices stay visible) ---------------

func _toggle(key: String) -> void:
	_focus = "" if _focus == key else key
	_build()


func _pop(_who: int) -> void:
	var r: Dictionary = {}
	for n in _root.find_children("*", "Control", true, false):
		if n.has_meta("pop") and n.get_meta("key", "") == _focus:
			r = n.get_meta("pop")
	if r.is_empty():
		return
	var p := PanelContainer.new()
	var sb := CUI.tile_box(FOCUS, 3, 16, Vector4(10, 8, 10, 10))
	sb.shadow_color = Color(0.141, 0.188, 0.172, 0.25)
	sb.shadow_size = 6
	sb.shadow_offset = Vector2(0, 5)
	p.add_theme_stylebox_override("panel", sb)
	p.custom_minimum_size = Vector2(186, 0)
	var v := CUI.vbox(5)
	var top := CUI.hbox(6)
	var names := CUI.vbox(0)
	names.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	names.add_child(CUI.wrap(UI.label(String(r.tag).to_upper(), "n900", 11, Color("#225C91"), 1), 120))
	names.add_child(CUI.wrap(UI.label(r.name, "lilita", 17, UI.INK, 0, 1.1), 120))
	top.add_child(names)
	var close := HexShape.make(20, 20, Color(0, 0, 0, 0), Color(0, 0, 0, 0), 0).with_icon("M6 6l12 12 M18 6L6 18", SOFT, 16, 2.6)
	close.clickable = true
	close.accessibility_name = "Close details"
	close.pressed.connect(func():
		_focus = ""
		_build())
	top.add_child(close)
	v.add_child(top)
	v.add_child(CUI.wrap(UI.label(r.text, "n700", 12, SOFT, 0, 1.3), 160))
	for ln: Array in r.get("lines", []):
		var box := UI.panel(Color("#F3EADA"), 10, Color(0, 0, 0, 0), 0, Vector4(7, 5, 7, 5))
		var lv := CUI.vbox(1)
		lv.add_child(CUI.wrap(UI.label(String(ln[0]).to_upper(), "n900", 11, CAP_INK, 1), 146))
		lv.add_child(CUI.wrap(UI.label(ln[1], "n800", 11, UI.INK, 0, 1.25), 146))
		box.add_child(lv)
		v.add_child(box)
	if r.get("picked", false):
		var pill := _chosen_pill()
		pill.size_flags_horizontal = Control.SIZE_SHRINK_END
		v.add_child(pill)
	elif r.get("button", "") != "":
		var f: Callable = r.act
		var b := CUI.choose_button(r.button, UI.font("lilita").get_string_size(r.button, HORIZONTAL_ALIGNMENT_LEFT, -1, 15).x + 40)
		b.size_flags_horizontal = Control.SIZE_SHRINK_END
		b.pressed.connect(func():
			f.call()
			_focus = ""
			_build())
		v.add_child(b)
	var sc := ScrollContainer.new()
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.add_child(v)
	p.add_child(sc)
	_root.add_child(p)
	UI.at(p, 12, 76)
	sc.custom_minimum_size = Vector2(160, minf(v.get_combined_minimum_size().y, 302 - 18 - 6))


func _chosen_pill() -> Control:
	var pill := UI.panel(Color("#E9F3E2"), 15, Color(0, 0, 0, 0), 0, Vector4(12, 0, 12, 0))
	pill.custom_minimum_size.y = 30
	pill.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	var h := CUI.hbox(5)
	var tick := UI.icon_rect(TICK, Color("#2E6B3A"), 12, 4.0)
	tick.custom_minimum_size = Vector2(12, 12)
	tick.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(tick)
	var t := UI.label("Chosen", "n900", 12, Color("#2E6B3A"))
	t.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(t)
	pill.add_child(h)
	return pill


# --- Small helpers -------------------------------------------------------------------------------------------------

func _panel(pad: Vector4) -> PanelContainer:
	return UI.panel(PANEL, 18, PANEL_EDGE, 5, pad)


func _centred(l: Label) -> Label:
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.size_flags_horizontal = Control.SIZE_FILL
	return l


## A card's text without its "Blaster spell:" or "Fighter:" lead, which the pop-up's tag already says.
static func text_of(k: Dictionary) -> String:
	var t: String = k.desc
	if t.find(": ") >= 0 and t.find(": ") < 24:
		t = t.substr(t.find(": ") + 2)
		t = t[0].to_upper() + t.substr(1)
	return t


## The Party chip: a tag shape with "Party" (07 v8c).
class _TagChip extends Control:
	var text := ""
	var rim := UI.RIM
	func _draw() -> void:
		var r := Rect2(Vector2(0, 3), size)
		draw_colored_polygon(UI.tag_points(r, 10), Color("#7E9A92"))
		draw_colored_polygon(UI.tag_points(Rect2(Vector2.ZERO, size), 10), rim)
		draw_colored_polygon(UI.tag_points(Rect2(Vector2(3, 3), size - Vector2(6, 6)), 8), Color("#F6EEDF"))
		var f := UI.font("lilita")
		var w := f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x
		draw_string(f, Vector2((size.x - w) * 0.5, size.y * 0.5 + 5), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#22262E"))


## The footer's Back: a cream pill.
class _PillButton extends Control:
	signal pressed
	var text := ""
	var font_px := 13
	func _ready() -> void:
		accessibility_name = text
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		var f := UI.font("n900")
		custom_minimum_size.x = f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_px).x + 36
	func _draw() -> void:
		draw_style_box(UI.box(Color("#E6DCC8"), int(size.y * 0.5)), Rect2(Vector2.ZERO, size))
		var f := UI.font("n900")
		var w := f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_px).x
		draw_string(f, Vector2((size.x - w) * 0.5, size.y * 0.5 + font_px * 0.36), text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_px, UI.INK)
	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
	func _has_point(p: Vector2) -> bool:
		return UI.finger_rect(size).has_point(p)


## Show all: the label and a switch (07 v8b: a toggle, off by default).
class _Switch extends Control:
	signal pressed
	var on := false
	func _ready() -> void:
		accessibility_name = "Show all"
		custom_minimum_size = Vector2(100, 28)
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	func _draw() -> void:
		draw_style_box(UI.box(Color("#E6DCC8"), 14), Rect2(Vector2.ZERO, size))
		var f := UI.font("n900")
		draw_string(f, Vector2(10, 18), "Show all", HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.INK)
		var track := Rect2(Vector2(size.x - 38, 4), Vector2(34, 20))
		draw_style_box(UI.box(Color("#2E7A3E") if on else Color("#BFAE8E"), 10), track)
		draw_circle(track.position + Vector2(26 if on else 10, 10), 8, UI.WHITE_WARM)
	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
	func _has_point(p: Vector2) -> bool:
		return UI.finger_rect(size).has_point(p)


## A follow-up chip in the feat details (07 v9: proficiencies, weapon categories).
class _Chip extends Control:
	signal pressed
	var text := ""
	var on := false
	func _ready() -> void:
		accessibility_name = text
		var f := UI.font("n900")
		custom_minimum_size = Vector2(f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x + 18, 24)
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	func _draw() -> void:
		var sb := UI.box(Color("#FFF4E8") if on else Color("#FFFFFF"), 12)
		sb.set_border_width_all(2)
		sb.border_color = Color("#B5532F") if on else Color("#E2D5BC")
		draw_style_box(sb, Rect2(Vector2.ZERO, size))
		draw_string(UI.font("n900"), Vector2(9, 16), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color("#9A4A12") if on else UI.INK)
	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
	func _has_point(p: Vector2) -> bool:
		return UI.finger_rect(size).has_point(p)


## A compact row: AP hex, name, a tick once picked (07 v9a's spell rows).
class _Row extends Control:
	signal pressed
	var label := ""
	var ap := 0
	var on := false
	var focused := false
	static func make(n: String, a: int, picked: bool, open: bool) -> _Row:
		var r := _Row.new()
		r.label = n
		r.ap = a
		r.on = picked
		r.focused = open
		r.accessibility_name = "%s, %d AP%s" % [n, a, ", picked" if picked else ""]
		r.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		r.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		return r
	func _draw() -> void:
		draw_style_box(CUI.tile_box(Color("#B5532F") if on else (Color("#3F86C8") if focused else Color("#E2D5BC")), 2.5 if on or focused else 2.0, 10, Vector4.ZERO, Color("#FFF4E8") if on else UI.CREAM_LIGHT), Rect2(Vector2.ZERO, size))
		draw_colored_polygon(UI.hex_points(Rect2(Vector2(4, (size.y - 23) * 0.5), Vector2(20, 23))), UI.DARK)
		var f := UI.font("n900")
		var s := str(ap)
		draw_string(f, Vector2(14 - f.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x * 0.5, size.y * 0.5 + 4), s, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.CREAM)
		var room := size.x - (52 if on else 36)
		var lines := [label]
		if f.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x > room and label.contains(" "):
			var words := label.split(" ")
			var cut := words.size() - 1
			while cut > 1 and f.get_string_size(" ".join(words.slice(0, cut)), HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x > room:
				cut -= 1
			lines = [" ".join(words.slice(0, cut)), " ".join(words.slice(cut))]
		for k in lines.size():
			var y := size.y * 0.5 + 4 + (k - (lines.size() - 1) * 0.5) * 12
			draw_string(f, Vector2(30, y), lines[k], HORIZONTAL_ALIGNMENT_LEFT, room, 11, UI.INK)
		if on:
			draw_circle(Vector2(size.x - 14, size.y * 0.5), 8, Color("#2E7A3E"))
			draw_texture_rect(UI.icon("M5 12l5 5 9-10", UI.WHITE_WARM, 10, 4.0), Rect2(Vector2(size.x - 19, size.y * 0.5 - 5), Vector2(10, 10)), false)
	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
	func _has_point(p: Vector2) -> bool:
		return UI.finger_rect(size).has_point(p)


## A choice as an icon hex with its name under it (subclasses, forms, beasts, gods; 07 v8c), "Default" over the companion's.
class _HexChoice extends Control:
	signal pressed
	var label := ""
	var icon_path := ""
	var on := false
	var focused := false
	var default_tag := false
	static func make(n: String, icon: String, picked: bool, open: bool, is_default: bool) -> _HexChoice:
		var h := _HexChoice.new()
		h.label = n
		h.icon_path = icon
		h.on = picked
		h.focused = open
		h.default_tag = is_default
		h.accessibility_name = n + (", chosen" if picked else "")
		h.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		var f := UI.font("n900")
		var lines := 1 if f.get_string_size(n, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x <= 66 else 2
		h.custom_minimum_size = Vector2(66, 58 + 4 + 14 * lines)
		return h
	func _draw() -> void:
		var r := Rect2(Vector2(8, 0), Vector2(50, 58))
		draw_colored_polygon(UI.hex_points(Rect2(r.position + Vector2(0, 3), r.size)), UI.HEX_SHADOW)
		draw_colored_polygon(UI.hex_points(r), Color("#B5532F") if on else (Color("#3F86C8") if focused else UI.RIM))
		var ins := 5.0 if on else 3.5
		draw_colored_polygon(UI.hex_points(r.grow(-ins)), Color("#FFF4E8") if on else UI.CREAM_LIGHT)
		if icon_path != "":
			draw_texture_rect(UI.icon(icon_path, Color("#33403B"), 24, 2.0), Rect2(r.get_center() - Vector2(12, 12), Vector2(24, 24)), false)
		var f := UI.font("n900")
		var words := label.split(" ")
		var lines := [label] if f.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x <= 66 else [" ".join(words.slice(0, maxi(1, words.size() / 2))), " ".join(words.slice(maxi(1, words.size() / 2)))]
		for k in lines.size():
			var w := f.get_string_size(lines[k], HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x
			draw_string(f, Vector2((size.x - w) * 0.5, 74 + k * 13), lines[k], HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.INK)
		if default_tag:
			var tw := f.get_string_size("Default", HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x + 12
			draw_style_box(UI.box(UI.DARK, 8), Rect2(Vector2((size.x - tw) * 0.5, -9), Vector2(tw, 16)))
			draw_string(f, Vector2((size.x - tw) * 0.5 + 6, 3), "Default", HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.CREAM)
	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
	func _has_point(p: Vector2) -> bool:
		return UI.finger_rect(size).has_point(p)


## A combat card as the hotbar draws it, 74 x 84 (07 v6: gains as real action cards): class band, AP hex, icon, name; New
## tag or the upgrade's green arrow; dashed when empty. A picked one sits lower (lift 0), as a picked hotbar card.
class _SmallCard extends Control:
	signal pressed
	var card := {}
	var icon_path := ""
	var shown_name := ""
	var empty_text := ""
	var is_empty := false
	var picked := false
	var focused := false
	var new_tag := false
	var up_badge := false
	var lift := 0.0:
		set(v):
			lift = v
			custom_minimum_size.y = 84.0 + v
	static func make(c: Dictionary, icon: String) -> _SmallCard:
		var s := _SmallCard.new()
		s.card = c
		s.icon_path = icon if icon != "" else String(c.get("icon", ""))
		s.accessibility_name = "%s, %d AP" % [c.n, c.ap]
		s.custom_minimum_size = Vector2(74, 84)
		s.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		return s
	static func empty(t: String) -> _SmallCard:
		var s := _SmallCard.new()
		s.is_empty = true
		s.empty_text = t
		s.accessibility_name = "Spell slot, empty" if t != "" else ""
		s.custom_minimum_size = Vector2(74, 84)
		s.mouse_filter = Control.MOUSE_FILTER_IGNORE
		return s
	func _draw() -> void:
		var r := Rect2(Vector2(0, lift), Vector2(74, 84))
		if is_empty:
			var pts := [r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y), r.position]
			for q in 4:
				var a: Vector2 = pts[q]
				var b: Vector2 = pts[q + 1]
				var cnt := int(a.distance_to(b) / 8.0)
				for j in cnt:
					draw_line(a.lerp(b, float(j) / cnt), a.lerp(b, (j + 0.55) / cnt), Color("#CDBFA6"), 2.0)
			if empty_text != "":
				var f := UI.font("n900")
				var w := f.get_string_size(empty_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x
				draw_string(f, Vector2((74 - w) * 0.5, r.position.y + 48), empty_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.INK)
			return
		draw_style_box(UI.box(UI.HEX_SHADOW, 10), Rect2(r.position + Vector2(0, 4), r.size))
		var sb := UI.box(Color("#FFF4E8") if picked else UI.CREAM_LIGHT, 10)
		sb.set_border_width_all(3 if picked or focused else 2)
		sb.border_color = Color("#3F86C8") if focused and not picked else Color("#B5532F")
		draw_style_box(sb, r)
		draw_rect(Rect2(r.position + Vector2(2, 2), Vector2(70, 6)), Color("#B5532F"))
		draw_colored_polygon(UI.hex_points(Rect2(r.position + Vector2(4, 9), Vector2(20, 23))), UI.DARK)
		var f := UI.font("n900")
		var ap := str(card.get("ap", 0))
		draw_string(f, r.position + Vector2(14 - f.get_string_size(ap, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x * 0.5, 25), ap, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.CREAM)
		if new_tag:
			draw_style_box(UI.box(Color("#B5532F"), 8), Rect2(r.position + Vector2(44, 10), Vector2(27, 16)))
			draw_string(f, r.position + Vector2(48, 22), "New", HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.WHITE_WARM)
		if up_badge:
			draw_circle(r.position + Vector2(61, 19), 9, Color("#2E7A3E"))
			draw_texture_rect(UI.icon("M12 19V5 M6 11l6-6 6 6", UI.WHITE_WARM, 11, 3.4), Rect2(r.position + Vector2(55.5, 13.5), Vector2(11, 11)), false)
		if icon_path != "":
			draw_texture_rect(UI.icon(icon_path, Color("#9A4A12"), 26, 2.0), Rect2(r.position + Vector2(24, 20), Vector2(26, 26)), false)
		var n := shown_name if shown_name != "" else String(card.n)
		var lines := Cards.name_lines(n, f, 11, 66)
		for k in lines.size():
			var w := f.get_string_size(lines[k], HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x
			draw_string(f, r.position + Vector2((74 - w) * 0.5, 60 + k * 12), lines[k], HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.INK)
	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
	func _has_point(p: Vector2) -> bool:
		return UI.finger_rect(size).has_point(p)


## A large class card, 104 x 118 (07 v9a "Your class cards"): band, AP hex, New tag, icon, name; the new one glows gold.
class _BigCard extends Control:
	signal pressed
	var card := {}
	var new := false
	var focused := false
	static func make(c: Dictionary, is_new: bool) -> _BigCard:
		var b := _BigCard.new()
		b.card = c
		b.new = is_new
		b.custom_minimum_size = Vector2(104, 124)
		b.accessibility_name = "%s%s, %d AP" % ["New card: " if is_new else "Class card: ", c.n, c.ap]
		b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		return b
	func _draw() -> void:
		var r := Rect2(Vector2.ZERO, Vector2(104, 118))
		if new:
			draw_style_box(UI.box(Color(0.894, 0.71, 0.298, 0.55), 15), r.grow(4))
		draw_style_box(UI.box(UI.HEX_SHADOW, 12), Rect2(Vector2(0, 5), r.size))
		var sb := UI.box(UI.CREAM_LIGHT, 12)
		sb.set_border_width_all(3 if new or focused else 2)
		sb.border_color = Color("#3F86C8") if focused else Color("#B5532F")
		draw_style_box(sb, r)
		draw_rect(Rect2(Vector2(2, 2), Vector2(100, 8)), Color("#B5532F"))
		draw_colored_polygon(UI.hex_points(Rect2(Vector2(6, 13), Vector2(26, 30))), UI.DARK)
		var f := UI.font("n900")
		var ap := str(card.ap)
		draw_string(f, Vector2(19 - f.get_string_size(ap, HORIZONTAL_ALIGNMENT_LEFT, -1, 14).x * 0.5, 33), ap, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, UI.CREAM)
		if new:
			draw_style_box(UI.box(Color("#B5532F"), 9), Rect2(Vector2(68, 14), Vector2(31, 18)))
			draw_string(f, Vector2(73, 27), "New", HORIZONTAL_ALIGNMENT_LEFT, -1, 11, UI.WHITE_WARM)
		draw_texture_rect(UI.icon(String(card.icon), Color("#9A4A12"), 36, 2.0), Rect2(Vector2(34, 36), Vector2(36, 36)), false)
		var lines := Cards.name_lines(String(card.n), f, 13, 94)
		for k in lines.size():
			var w := f.get_string_size(lines[k], HORIZONTAL_ALIGNMENT_LEFT, -1, 13).x
			draw_string(f, Vector2((104 - w) * 0.5, 90 + k * 14), lines[k], HORIZONTAL_ALIGNMENT_LEFT, -1, 13, UI.INK)
	func _gui_input(e: InputEvent) -> void:
		if UI.is_tap(self, e):
			pressed.emit()
	func _has_point(p: Vector2) -> bool:
		return UI.finger_rect(size).has_point(p)
