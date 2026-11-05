class_name StartCheck
extends Node
## Can a starting tile be walked from to any neighbour, whatever is laid there (`-- --startcheck`, design/06 -> First playable)? Prints which can't.

var game: Game


func _ready() -> void:
	_run.call_deferred()


func _run() -> void:
	if "--startshots" in OS.get_cmdline_user_args():
		await _shots()
		return
	var failed := 0
	for terrain: String in RunSetup.ONE_OF_EACH:
		var shut := []
		for i in 6:
			var map := MapBoard.new()
			add_child(map)
			map.place(Rules.START_TILE, Rules.START_TERRAIN)
			var n: Vector2i = Rules.START_TILE + Hex.NEIGHBOURS[i]
			map.place(n, terrain)
			if not map.edge_open(Rules.START_TILE, n) or not map.can_visit(n):
				shut.append(i)
			if not i in map.gates.get(Rules.START_TILE, []) and not terrain in FenceGates.FENCED:
				shut.append("no gate %d" % i)
			remove_child(map)
			map.free()
		print("START %s %s: %s" % ["OK" if shut.is_empty() else "FAIL", terrain, "open on every side" if shut.is_empty() else "shut at %s" % [shut]])
		failed += 0 if shut.is_empty() else 1
	# A farm beside a starting tile that isn't itself fenced shows a gate toward it, whichever side.
	for i in 6:
		var start := Rules.START_TILE
		var farm: Vector2i = start + Hex.NEIGHBOURS[i]
		var out := FenceGates.gates({start: "plains", farm: "farmland"}, {}, [], [start])
		if not (i + 3) % 6 in out[farm]:
			print("START FAIL farm beside a start: no gate on side %d" % i)
			failed += 1
	failed += _check_water_gate()
	print("START DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()


## A fence that cuts the party off across water gets a gate, which stays when land opens another way; one that doesn't, doesn't.
func _check_water_gate() -> int:
	var failed := 0
	var map := MapBoard.new()
	add_child(map)
	map.party_walks = true
	map.party_at = Rules.START_TILE
	var river: Vector2i = Rules.START_TILE + Hex.NEIGHBOURS[0]
	var farm: Vector2i = river + Hex.NEIGHBOURS[0]
	map.place(Rules.START_TILE, StartTiles.MONTO)
	map.place(river, "river")
	map.place(farm, "farmland")
	var opened: bool = 3 in map.water_gates.get(farm, []) and map.edge_open(river, farm)
	map.place(river + Hex.NEIGHBOURS[1], "plains")
	map.place(river + Hex.NEIGHBOURS[5], "plains")
	var stayed: bool = 3 in map.gates.get(farm, []) and map.edge_open(river, farm)
	print("START %s water gate: opens when cut off, stays when land opens another way" % ("OK" if opened and stayed else "FAIL"))
	failed += 0 if opened and stayed else 1
	remove_child(map)
	map.free()
	map = MapBoard.new()
	add_child(map)
	map.party_walks = true
	map.party_at = Rules.START_TILE
	map.place(Rules.START_TILE, "plains")
	map.place(Rules.START_TILE + Hex.NEIGHBOURS[0], "river")
	map.place(Rules.START_TILE + Hex.NEIGHBOURS[1], "farmland")
	print("START %s water gate: none when the fence doesn't cut the party off" % ("OK" if map.water_gates.is_empty() else "FAIL"))
	failed += 0 if map.water_gates.is_empty() else 1
	remove_child(map)
	map.free()
	return failed


## Each background's tile by day and night, alone, then among neighbours, walked across on the way (`-- --startshots --background=<name>`).
func _shots() -> void:
	var out := ProjectSettings.globalize_path("res://screens")
	var tag: String = game.run.background
	game.hud.visible = false
	var shot := func(name: String, dist: float) -> void:
		game.rig.frame(game.party_node.centre(), dist, 50.0)
		await get_tree().create_timer(2.5).timeout
		await RenderingServer.frame_post_draw
		game.get_viewport().get_texture().get_image().save_png(out.path_join("start_%s_%s.png" % [tag, name]))
	await shot.call("day", 20.0)
	var name: String = game.map.terrains[Rules.START_TILE]
	var same: String = Variants.terrain_of(name)
	var near := [same, "plains", "forest", "plains", "farmland", "hills"]
	if name == StartTiles.MONTO:
		near = ["river", "plains", "forest", "plains", "farmland", "hills"]
	for i in 6:
		game.map.place(Rules.START_TILE + Hex.NEIGHBOURS[i], near[i])
	await shot.call("among", 30.0)
	# Walked in by every side: the party ends at the stop whichever way it came.
	var z := []
	for i in 6:
		game.party_node.place_at(Rules.START_TILE + Hex.NEIGHBOURS[i])
		game.party_tile = Rules.START_TILE + Hex.NEIGHBOURS[i]
		var path: Array[Vector2i] = game.path_to(Rules.START_TILE)
		print("START walk from side %d: %d steps" % [i, path.size()])
		if path.is_empty():
			continue
		Engine.time_scale = 8.0
		game.walk_to(Rules.START_TILE)
		var waited := 0
		while game.busy and waited < 600:
			waited += 1
			await get_tree().process_frame
		Engine.time_scale = 1.0
		z.append(snappedf(game.party_node.members[0].node.position.y, 0.01))
		print("START at the stop from side %d: tile %s, height %.2f, %d frames" % [i, game.party_tile, z[-1], waited])
	game._advance(Rules.NIGHT_AT + 2.0 - game.minute)
	await get_tree().create_timer(4.0).timeout
	await shot.call("night", 30.0)
	print("START SHOTS DONE %s" % tag)
	get_tree().quit()
