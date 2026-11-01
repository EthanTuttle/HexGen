extends SceneTree
## Checks the landmark flow port (scripts/landmark_flow.gd), the edge_same_b hash and the fence gates
## (scripts/fence_gates.gd) against art/scripts/landmark_flow.py and fence_gates.py on the same regions. Cases come from tools/flow_cases.py, from the repo root:
##   python3 -I godot/tools/flow_cases.py art/scripts /tmp/flow_cases.json
##   godot --headless --path godot --script res://tools/flow_check.gd -- /tmp/flow_cases.json

func _init() -> void:
	var path: String = OS.get_cmdline_user_args()[0]
	var cases: Array = JSON.parse_string(FileAccess.get_file_as_string(path))
	var bad := 0
	for c in cases:
		var region: Array = c.region.map(func(t): return Vector2i(t[0], t[1]))
		var lm := Vector2i(c.landmark[0], c.landmark[1])
		var f := LandmarkFlow.flow(region, lm)
		var turn := LandmarkFlow.turn(lm, f.dist, f.toward)
		var ok: bool = turn == int(c.turn) and f.toward.size() == c.toward.size()
		for key in c.toward:
			var p: PackedStringArray = key.split(",")
			var t := Vector2i(int(p[0]), int(p[1]))
			ok = ok and f.toward.get(t) == Vector2i(c.toward[key][0], c.toward[key][1])
		for key in c.trails:
			var p: PackedStringArray = key.split(",")
			var mine := LandmarkFlow.trail_edges(Vector2i(int(p[0]), int(p[1])), f.toward)
			ok = ok and mine == c.trails[key].map(func(x): return int(x))
		for key in c.same_b:
			var p: PackedStringArray = key.split(",")
			var b := GroundCover.hash01(int(p[0]) * 6 + int(p[2]), int(p[1]), 8) < 0.5
			ok = ok and b == c.same_b[key]
		for key in c.heads_in:
			var p: PackedStringArray = key.split(",")
			ok = ok and LandmarkFlow.heads_in(Vector2i(int(p[0]), int(p[1])), int(p[2]), f.dist) == c.heads_in[key]
		for key in c.toward_edge:
			var p: PackedStringArray = key.split(",")
			ok = ok and LandmarkFlow.toward_edge(Vector2i(int(p[0]), int(p[1])), f.toward) == int(c.toward_edge[key])
		var terrains := {}
		for row in c.terrains:
			terrains[Vector2i(row[0], row[1])] = row[2]
		var gates := FenceGates.gates(terrains)
		ok = ok and gates.size() == c.gates.size()
		for key in c.gates:
			var p: PackedStringArray = key.split(",")
			var mine: Array = gates.get(Vector2i(int(p[0]), int(p[1])), [])
			ok = ok and mine == c.gates[key].map(func(x): return int(x))
		if not ok:
			bad += 1
	print("FLOW CHECK: %d cases, %d differ from landmark_flow.py and fence_gates.py" % [cases.size(), bad])
	quit()
