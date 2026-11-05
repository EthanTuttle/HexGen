class_name StartCheck
extends Node
## Can a starting tile be walked from to any neighbour, whatever is laid there (`-- --startcheck`, design/06 -> First playable)? Prints which can't.

var game: Game


func _ready() -> void:
	_run.call_deferred()


func _run() -> void:
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
	print("START DONE: %d failed" % failed)
	if "--quit" in OS.get_cmdline_user_args():
		get_tree().quit()
