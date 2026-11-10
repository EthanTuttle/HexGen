class_name Creator
extends Control
## The character creator, from Creator v22b (mockups/character-creator/Creator-v22b-Banners.dc.html; design/07 ->
## Character creator screen). Guided steps with hex pips along the top; each step's view lives in its own script here.
## God can't be reached while no Cleric is playable, so it isn't built; Spells shows for casters (the Wizard). Other classes show locked:
## PLACEHOLDER look, no mockup (a dimmed banner with a lock; it opens to read, and Next stays off).

signal finished(hero: Hero, banners: Array)
signal cancelled

const D = preload("res://scripts/creator/creator_data.gd")
const PLAYABLE: Array[String] = ["Fighter", "Ranger", "Rogue", "Wizard"]   # DOCS (06 -> Start: Ranger added Nov 5, Rogue and Wizard Nov 6, 2026)
const LOCK_ICON := "M7 11V8a5 5 0 0 1 10 0v3 M6 11h12v9H6z"
const STEPS := [["class", "Class"], ["race", "Race"], ["bg", "Background"], ["scores", "Scores"], ["skills", "Skills"],
	["gear", "Gear"], ["look", "Look"], ["name", "Name"]]
const SPELLS_STEP := ["spells", "Spells"]   # casters only, after Gear (design/07 -> Character creator v1a)

# The picks (the mockup's state).
var step := "class"
var cls := ""
var race := ""
var sub := ""
var elf_spell := ""
var spells: Array = []                # a caster's level-1 picks, as card ids
var bg := ""
var rb: Array = []                    # race +1s
var cb := ""                          # class +1
var pb := ""                          # background proficiency
var pc := ""                          # class proficiency
var main := ""
var off := ""
var arm := ""
var build := "Average"
var pronouns := ""
var head := 0
var hair := 0
var col := {}                         # chosen colours by part
var hero_name := ""

var _bar := Control.new()
var _body := Control.new()
var _view: Control
var _view_kind := ""


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_bar)
	_body.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_body)
	resized.connect(_layout)
	_layout()
	render()


## The mockup's padding (12 18 14). Inside a phone's safe area the inset already leaves room at the sides.
func _layout() -> void:
	var pad := 6.0 if size.x < 800.0 else 18.0
	_bar.position = Vector2(pad, 12)
	_bar.size = Vector2(size.x - pad * 2.0, 52)
	_body.position = Vector2(pad, 72)
	_body.size = Vector2(size.x - pad * 2.0, size.y - 72 - 14)
	if _view:   # the safe area changed
		_view.size = _body.size
		_view.position = Vector2.ZERO
		render()


func render() -> void:
	_build_bar()
	var kind: String = {"class": "banners", "race": "banners", "bg": "banners", "scores": "train", "skills": "train",
		"gear": "gear", "spells": "spells", "look": "look", "name": "name"}[step]
	if kind != _view_kind:
		if _view:
			_view.queue_free()
		_view_kind = kind
		match kind:
			"banners": _view = CreatorBanners.new(self)
			"train": _view = CreatorTraining.new(self)
			"gear": _view = CreatorGear.new(self)
			"spells": _view = CreatorSpells.new(self)
			"look": _view = CreatorLook.new(self)
			"name": _view = CreatorName.new(self)
		_view.size = _body.size
		_body.add_child(_view)
	_view.call("refresh")


func _build_bar() -> void:
	for c in _bar.get_children():
		_bar.remove_child(c)
		c.queue_free()
	var back := CUI.hex(44, 51, UI.RIM, 3, "M15 5l-7 7 7 7", Color("#33403B"), 20, UI.CREAM_LIGHT, false, 2.4).with_shadow(UI.HEX_SHADOW, 4)
	back.clickable = true
	back.accessibility_name = "Back to main menu"
	back.pressed.connect(func(): cancelled.emit())
	_bar.add_child(back)
	var title := UI.label("New hero", "lilita", 22)
	UI.at(title, 58, 12)
	_bar.add_child(title)
	var all := steps()
	var reach := all.size() - 1
	for i in all.size():
		if not done(all[i][0]):
			reach = i
			break
	# Pips at one pitch, centred in the room right of the title; a long label ("Background") overhangs its slot a little
	# rather than pushing its neighbours apart (Ethan's phone note, Nov 5, 2026: even spacing).
	var room := _bar.size.x - 150.0
	var pitch := minf(66.0 if _bar.size.x >= 760.0 else 60.0, room / all.size())
	var left := 150.0 + (room - pitch * all.size()) * 0.5
	for i in all.size():
		var t := _pip(i, reach)
		_bar.add_child(t)
		t.position = Vector2(left + pitch * (i + 0.5) - t.custom_minimum_size.x * 0.5, 0)


func _pip(i: int, reach: int) -> Control:
	var k: String = steps()[i][0]
	var cur := k == step
	var is_done := done(k)
	var ok := i <= reach or is_done
	var rim := Color("#7E3519") if cur else (Color("#5E8F5A") if is_done else UI.RIM)
	var face := UI.ORANGE if cur else (Color("#E3EFD9") if is_done else UI.CREAM_LIGHT)
	var ink := UI.WHITE_WARM if cur else (Color("#2E5A2A") if is_done else Color("#33403B"))
	var hx := CUI.hex(28, 32, rim, 3, CUI.TICK if is_done and not cur else "", ink, 14, face, false, 3.2).with_shadow(UI.HEX_SHADOW, 3)
	if not (is_done and not cur):
		hx.with_text(str(i + 1), 13, ink)
	var lab := UI.label(steps()[i][1], "n800", 11, Color("#33403B"))
	var t := CUI.tap_column(steps()[i][1], [hx, lab])
	t.modulate.a = 1.0 if ok else 0.5
	if ok:
		t.pressed.connect(func(): go(k))
	return t


func go(k: String) -> void:
	step = k
	render()


## The steps for the picked class: Spells only for casters.
func steps() -> Array:
	var out := STEPS.duplicate()
	if cls_data().has("sp"):
		out.insert(6, SPELLS_STEP)
	return out


func index() -> int:
	var all := steps()
	for i in all.size():
		if all[i][0] == step:
			return i
	return 0


func go_back() -> void:
	if index() > 0:
		go(steps()[index() - 1][0])


func go_next() -> void:
	if done(step) and index() < steps().size() - 1:
		go(steps()[index() + 1][0])


## The row every banner and level-up step ends with.
func nav_row() -> Control:
	var h := CUI.hbox(0)
	var back := CUI.big("Back", false)
	back.disabled = index() == 0
	back.pressed.connect(go_back)
	h.add_child(back)
	h.add_child(CUI.spring())
	h.add_child(next_button())
	return h


func next_button() -> TagButton:
	var n := CUI.big("Next", true)
	n.disabled = not done(step)
	n.pressed.connect(go_next)
	return n


# --- What's picked ----------------------------------------------------------------

func cls_data() -> Dictionary:
	for c: Dictionary in D.CLS:
		if c.id == cls:
			return c
	return {}


func race_data() -> Dictionary:
	for r: Dictionary in D.RACES:
		if r.id == race:
			return r
	return {}


func sub_data() -> Dictionary:
	for x: Dictionary in race_data().get("subs", []):
		if x.id == sub:
			return x
	return {}


func bg_data() -> Dictionary:
	for b: Dictionary in D.BGS:
		if b.id == bg:
			return b
	return {}


func weapon(id: String) -> Dictionary:
	return Gear.item(id)


func race_name() -> String:
	if race == "":
		return ""
	if sub == "":
		return race
	match race:
		"Dragonborn": return sub + " dragonborn"
		"Golem": return sub + " golem"
		"Tiefling": return sub + " tiefling"
	return sub


func done(k: String) -> bool:
	match k:
		"class": return cls in PLAYABLE
		"race":
			var r := race_data()
			return not r.is_empty() and (not r.has("subs") or sub != "") and (sub != "High elf" or elf_spell != "")
		"bg": return bg != ""
		"scores": return race != "" and cls != "" and rb.size() == 2 and cb != ""
		"skills": return pb != "" and pc != "" and bg != "" and cls != ""
		"gear": return main != "" and (off_options().is_empty() or off != "") and arm != ""
		"spells": return spells.size() == Weapons.SPELL_PICKS
		"look": return pronouns != ""
		"name": return hero_name.strip_edges() != ""
	return false


func all_done() -> bool:
	for s: Array in steps():
		if not done(s[0]):
			return false
	return true


func human() -> bool:
	return race == "Human"


## What the offhand can hold beside the main weapon.
func off_options() -> Array:
	return Gear.off_for(cls, human(), main)


func allowed_weapons() -> Array:
	return Gear.weapons_for(cls, human())


## The armour slot's choices: Clothes, or Clothes and Armoured.
func armour_options() -> Array:
	return Gear.armour_for(cls, human())


func scores() -> Dictionary:
	var out := {}
	for k: String in D.AB:
		out[k] = 1 + (1 if k in rb else 0) + (1 if cb == k else 0)
	return out


## The colour rows for this race (the mockup's partsDef).
func colour_parts() -> Array:
	var r := race_data()
	var golem: Dictionary = {}
	if race == "Golem":
		golem = sub_data() if sub != "" else r.subs[0]
	var skin_pal: Array = golem.sk if not golem.is_empty() else r.get("sk", D.SKIN)
	var parts := [{"k": "skin", "n": "Scales" if race == "Dragonborn" else ("Material" if not golem.is_empty() else "Skin"), "pal": skin_pal}]
	if r.is_empty() or r.hair:
		parts.append({"k": "hair", "n": "Hair", "pal": D.HAIR})
	parts.append({"k": "eyes", "n": "Eyes", "pal": D.EYES})
	parts.append({"k": "cloth", "n": "Cloth", "pal": D.CLOTH})
	return parts


func colour_of(k: String) -> String:
	for p: Dictionary in colour_parts():
		if p.k == k:
			return col[k] if col.get(k, "") in p.pal else p.pal[0]
	return ""


func cloth_colour() -> Color:
	return Color(colour_of("cloth"))


## The hero's three banners for the Name step and the send-off: colour, edge, icon, label.
func hero_banners() -> Array:
	var out := []
	var c := cls_data()
	if not c.is_empty():
		out.append({"c": Color(D.TER[c.t[0]][1]), "icon": D.IC[c.i], "lab": c.id})
	if race != "":
		var x := sub_data()
		var rc: String = x.c if x.has("c") and race != "Tiefling" else D.RCOL[race][0]
		out.append({"c": Color(rc), "icon": "", "lab": race})
	var b := bg_data()
	if not b.is_empty():
		out.append({"c": Color(D.TER[b.t][1]), "icon": D.IC[b.i], "lab": b.id})
	return out


## The description the game reads (Hero).
func hero() -> Hero:
	var h := Hero.new()
	h.name = hero_name.strip_edges()
	h.klass = cls.to_lower()
	h.race = race
	h.sub = sub
	h.race_name = race_name()
	h.elf_spell = elf_spell
	h.spells = spells.duplicate()
	h.pronouns = pronouns
	h.background = bg.to_lower().replace(" ", "_")
	h.scores = scores()
	h.proficiencies = [pb, pc]
	h.gear = {"main": main, "off": off, "armour": arm}
	h.appearance = {"race": race, "sub": sub, "build": build, "head": head, "hair": hair, "skin": colour_of("skin"),
		"hair_colour": colour_of("hair"), "eyes": colour_of("eyes"), "cloth": colour_of("cloth")}
	return h


func finish() -> void:
	if all_done():
		finished.emit(hero(), hero_banners())
