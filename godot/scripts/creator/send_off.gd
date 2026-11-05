class_name SendOff
extends CanvasLayer
## Begin (Creator v22b): the banners rise away, the screen fades to the board with the party on its starting tile, and the
## hero's banner drops in at the top. It sits on the scene tree's root so it outlives the change of scene.
## PLACEHOLDER: how long the hero's banner stays (no doc says), and that it then rises away so the HUD is clear.

const GAME_SCENE := "res://scenes/main.tscn"
const BANNER_STAYS := 4.0
const BANNER_LEFT := 96.0              # clear of the party tray, inside the safe area

var _cover := ColorRect.new()


## `hero` becomes Hero.current. `banners` and `cloth` are the mockup's; with none it just fades.
func play(tree: SceneTree, hero: Dictionary, banners: Array) -> void:
	layer = 50
	tree.root.add_child(self)
	_cover.color = UI.CREAM
	_cover.set_anchors_preset(Control.PRESET_FULL_RECT)
	_cover.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(_cover)
	_cover.modulate.a = 0.0
	var row := CUI.hbox(14)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.set_anchors_preset(Control.PRESET_TOP_WIDE)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for b: Dictionary in banners:
		row.add_child(CreatorName.SideBanner.make(b, 60, 230, 13, 26))
	add_child(row)
	var fade_in := create_tween()
	fade_in.tween_property(_cover, "modulate:a", 1.0, 0.15)
	var rise := create_tween()
	rise.tween_interval(0.2)
	rise.tween_property(row, "position:y", -420.0, 1.0).set_ease(Tween.EASE_IN).set_trans(Tween.TRANS_QUAD)
	await rise.finished
	row.queue_free()
	Hero.current = hero
	await tree.process_frame
	tree.change_scene_to_file(GAME_SCENE)
	await tree.process_frame
	await tree.process_frame
	var fade_out := create_tween()
	fade_out.tween_property(_cover, "modulate:a", 0.0, 0.5)
	await fade_out.finished
	_cover.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if not banners.is_empty():
		await _drop_banner(hero, banners)
	queue_free()


func _drop_banner(hero: Dictionary, banners: Array) -> void:
	var cloth := CreatorName.HeroCloth.new()
	cloth.setup(Color(hero.look.cloth), banners, 120, 170, 18)
	cloth.name_label.text = hero.name
	var safe := SafeArea.new()
	add_child(safe)
	safe.add_child(cloth)
	cloth.position = Vector2(BANNER_LEFT, -200)
	var drop := create_tween()
	drop.tween_interval(0.3)
	drop.tween_property(cloth, "position:y", 6.0, 0.7).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	drop.tween_interval(BANNER_STAYS)
	drop.tween_property(cloth, "position:y", -200.0, 0.6).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	await drop.finished
