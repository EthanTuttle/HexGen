class_name Screens
extends RefCounted
## Hooks the first playable's scenes into Game: the Enter card's town, and Social and Discovery events.


static func attach(game: Game) -> void:
	game.enter_town_screen = func(t: Vector2i):
		var scene := TownScene.new(game, t)
		_under_hud(game, scene)
	if "--cardscheck" in OS.get_cmdline_user_args():
		var check := ActionCardsCheck.new()
		check.game = game
		game.add_child(check)
	Saves.watch(game)
	if not Saves.pending.is_empty():   # Continue or Load: the save goes over the fresh game once its _ready is done
		var data := Saves.pending
		Saves.pending = {}
		(func():
			SaveGame.apply(game, data)
			SaveGame.resume(game)).call_deferred()
	if "--loadprofile" in OS.get_cmdline_user_args():
		LoadProfile.attach(game)
	if "--savecheck" in OS.get_cmdline_user_args():
		SaveCheck.attach(game)
	if "--layoutmock" in OS.get_cmdline_user_args():
		var lm := LayoutMock.new()
		lm.game = game
		game.add_child(lm)
	if "--pausemock" in OS.get_cmdline_user_args():
		var mock := PauseMock.new()
		mock.game = game
		game.add_child(mock)
	game.event_screen = func(t: Vector2i, entry: Dictionary):
		var scene := SocialScreen.new(game, t, entry)
		_under_hud(game, scene)


## Under the HUD: the party tray stays on top, and the check pop-up, which lives in the HUD, opens over the scene.
static func _under_hud(game: Game, scene: Control) -> void:
	game.safe.add_child(scene)
	game.safe.move_child(scene, game.hud.get_index())
