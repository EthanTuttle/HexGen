class_name SocialScreen
extends Control
## The Social encounter screen, from Social v9 (mockups/social-encounter/Social-v9-Camera.dc.html; design/07 -> Social
## encounter screen): the speaker's line on top, paged by a tap anywhere; the options dealt as cards once the last page
## shows; a tagged option opens the check pop-up, and nothing is committed until Flip coins.
##
## PLACEHOLDER: Ethan's 3 or 4 events aren't written yet (design/06), so every Social and Discovery encounter plays one
## stand-in, the Lady of the Lake's first talk, with her written lines (STAND_IN). Her sword quest and the pull aren't here.
## A blessing shows and flies home, but nothing holds it yet. Silver Tongue's reflip and the who-flips picker aren't built:
## the stand-in's checks are social and the hero's, and Silver Tongue is a feat the first playable doesn't have.

const STAND_IN := {
	"name": "The Lady of the Lake", "initial": "L", "face": "#BFE3D2", "start": "greet",
	"lines": {
		"greet": ["Long have these waters waited, traveller. Few come seeking me, and fewer still come worthy.", "Speak, and let the lake hear what manner of soul you are."],
		"sword": ["It lies far from here, bound in stone beneath an open sky. I will show you the way.", "But mark me: the stone yields only once. Fail it, and the blade is lost to you forever."],
		"pPass": ["There is truth in you. I feel it as I feel the rain.", "Take my blessing, and let the stone know you come in my name."],
		"pFail": ["Not today. Prove yourself in deed, not word, and perhaps the lake will think again."],
		"iPass": ["Boldly spoken. The old kings were bold too, and the stone answered them.", "Go, with what blessing a threat can buy."],
		"iFail": ["You dare threaten me at my own waters? Then let the lake answer you."],
	},
	"checks": {
		"swear": {"approach": "persuade", "need": 2, "text": "Swear you are true", "pass": "pPass", "fail": "pFail", "blessing": true},
		"draw": {"approach": "intimidate", "need": 2, "text": "Draw your weapon", "pass": "iPass", "fail": "iFail", "blessing": true, "fail_fight": true},
	},
	"talks": {"ask": {"text": "Ask about the sword", "line": "sword", "icon": "M12 3v4 M12 17v4 M12 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6"}},
	# design/characters/Fluffy.md -> Special lines
	"chime": {"swear": {"Fluffy": "\"I am King Alexander the All Conquering Legend and He Who Rules, and I vouch for them.\""}},
}
const APPROACH := {
	"persuade": {"n": "Persuade", "ab": "CHA", "bg": "#3E7F66", "prof": "Persuade", "icon": "M4 5h16v10H9l-5 4z"},
	"intimidate": {"n": "Intimidate", "ab": "STR", "bg": "#9A3F2A", "prof": "Intimidate", "icon": "M5 19L19 5 M15 5h4v4 M7 13l4 4 M5 17l2 2"},
}
const STAND_OFF := 26.0

var game: Game
var tile: Vector2i
var entry: Dictionary
var head := SceneUI.Head.new()
var data: Dictionary = STAND_IN
var _line := "greet"
var _page := 0
var _you := ""
var _used := {}
var _blessed := false
var _told := false
var _fight_next := false
var _row: HBoxContainer
var _press := {}
var _busy := false


func _init(g: Game, t: Vector2i, e: Dictionary) -> void:
	game = g
	tile = t
	entry = e
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	game.busy = true
	game.pick(null)
	game.hud.set_scene(true)
	game.rig.ease_to(game.party_node.centre(), STAND_OFF, 0.0)
	add_child(head)
	head.fit(size.x - 160.0 - 12.0)
	_line = data.start
	_say()


func _pages() -> Array:
	return data.lines[_line]


func _say() -> void:
	var more := _page < _pages().size() - 1 or _fight_next
	head.say(data.name, _you, _pages()[_page], Color(data.face), UI.INK, "", data.initial, "", more)
	if _row:
		_row.queue_free()
		_row = null
	if _page >= _pages().size() - 1 and not _fight_next:
		_deal()


func say_line(line: String, you: String) -> void:
	_line = line
	_page = 0
	_you = you
	_say()


func _unhandled_input(event: InputEvent) -> void:
	if not _busy and SceneUI.is_scene_tap(event, _press):
		next_page()


## A tap anywhere moves the line on while it has more pages (DOCS: Tap anywhere to continue).
func next_page() -> void:
	if _busy:
		return
	if _page < _pages().size() - 1:
		_page += 1
		_say()
	elif _fight_next:
		_leave_for_fight()


func _deal() -> void:
	_row = SceneUI.card_row()
	add_child(_row)
	_row.modulate.a = 0.0
	_row.create_tween().tween_property(_row, "modulate:a", 1.0, 0.25)
	if not _told:
		var t: Dictionary = data.talks.ask
		var c := _option_card("TALK", UI.SAND, Color("#5A5040"), t.icon, Color("#5A5040"), t.text)
		c.pressed.connect(func():
			_told = true
			say_line(t.line, t.text))
		_row.add_child(c)
	if not _blessed:
		for id: String in data.checks:
			if _used.has(id):
				continue
			var k: Dictionary = data.checks[id]
			var a: Dictionary = APPROACH[k.approach]
			var c := _option_card(str(a.n).to_upper(), Color(a.bg), UI.WHITE_WARM, a.icon, Color(a.bg), k.text)
			c.pressed.connect(_open_check.bind(id))
			_row.add_child(c)
	var leave := SceneUI.dark_card("Leave")
	leave.pressed.connect(_leave)
	_row.add_child(leave)


func _option_card(band_text: String, band: Color, band_ink: Color, icon: String, ink: Color, words: String) -> SceneUI.OptionCard:
	var c := SceneUI.card(band_text, band, icon, ink, words)
	c.band_ink = band_ink
	c.word_font = "n800"
	c.word_px = 12   # the mockup's 11, up a little: option cards are read at arm's length
	return c


# --- Checks (design/03 -> Checks outside combat) ---------------------------------------

func _view(id: String) -> Dictionary:
	var k: Dictionary = data.checks[id]
	var a: Dictionary = APPROACH[k.approach]
	var hero: Dictionary = game.party[0]
	var coins := Hero.coins_for(a.ab, a.prof)
	return {"tag": a.n, "tag_bg": Color(a.bg), "text": k.text, "initial": hero.initial, "face": hero.color,
		"line": "%d coin%s · %s · needs %d heads" % [coins, "" if coins == 1 else "s", a.ab, k.need], "coins": coins}


func _open_check(id: String) -> void:
	_busy = true
	game.hud.check.ask(_view(id), "Back", func():
		game.hud.check.visible = false
		_busy = false, _flip.bind(id), "Flip coins")


func _flip(id: String) -> void:
	var k: Dictionary = data.checks[id]
	var view := _view(id)
	var flips: Array[bool] = Coins.flip(game.rng, view.coins)
	if game.debug_near_miss != 0:
		for i in flips.size():
			flips[i] = i < int(k.need) - 1
	var first := flips.duplicate()
	var luck := game.lucky_check(flips, int(k.need))
	var heads := Coins.heads(flips)
	var helper := {}
	var helper_heads := false
	if heads == int(k.need) - 1:   # a miss by exactly 1: the proficient companion steps in
		var m := game._chime_helper(APPROACH[k.approach].prof)
		if not m.is_empty():
			var lines: Dictionary = data.chime.get(id, {})
			helper = {"initial": m.initial, "face": m.color, "name": m.name, "note": "", "line": lines.get(m.name, Rules.chime_line(m.name, APPROACH[k.approach].prof))}
			helper_heads = game.debug_near_miss > 0 or (game.debug_near_miss == 0 and game.rng.randf() < 0.5)
	var passed: bool = heads + (1 if helper_heads else 0) >= int(k.need)
	game.hud.check.play(view, first, helper, helper_heads, passed, luck)
	await game.hud.check.continued
	_busy = false
	_used[id] = true
	if passed and k.get("blessing", false):
		_blessed = true
		SceneUI.reveal_reward(self, "Blessing", "Lady of the Lake", Color("#3F86C8"), SceneUI.ICONS.drop, Vector2(42, 283))
	if not passed and k.get("fail_fight", false):
		_fight_next = true
	say_line(k.pass if passed else k.fail, k.text)


func _leave() -> void:
	_close()
	game.choose_event_done()


## A fight started from a scene (DOCS): it opens on the encounter's combat map.
func _leave_for_fight() -> void:
	_close()
	game.hud.hide_encounter()
	game.event_start_fight(tile)


func _close() -> void:
	game.hud.set_scene(false)
	queue_free()
