class_name CombatBoard
extends Node3D
## The radius-4 combat board (61 flat-top cells; art/scripts/render_preview.py build_board) with
## stand-in minis, and the attack hop and recoil as tweens (look test 3). Space plays an attack;
## attacks also play by themselves every few seconds.

const RADIUS := 4
const TREES := [Vector2i(1, -3), Vector2i(2, -3), Vector2i(-3, 1), Vector2i(-2, 2), Vector2i(3, 0)]
const ROCKS := [Vector2i(0, 2), Vector2i(-1, -1), Vector2i(2, 1)]

# The line-up of art/scripts/render_standin_minis.py (board): the party faces the camera (south),
# the enemies face north.
const LINEUP := [
	["standin_hero", Vector2i(0, 0)],
	["standin_chelmsford", Vector2i(-1, 1)],
	["standin_small", Vector2i(1, 0)],
	["standin_fluffy", Vector2i(-1, 2)],
	["standin_enemy", Vector2i(0, -3)],
	["standin_enemy", Vector2i(1, -2)],
	["standin_enemy", Vector2i(-1, -2)],
]
# Who attacks whom, in turn (indices into LINEUP). Placeholder order for the look test.
const BOUTS := [[0, 5], [5, 2], [1, 6], [4, 0]]

# Tween timings and sizes (no values in the docs yet; tuned by eye).
const HOP_HEIGHT := 0.35
const HOP_LEAN := 0.3        # how far the attacker moves toward the target at the top of the hop
const HOP_TIME := 0.16       # up; the same down
const RECOIL_TILT := 16.0    # degrees the target tips away
const RECOIL_PUSH := 0.12
const SHRINK_WAIT := 0.35     # PLACEHOLDER: a fallen foe lies there this long, then shrinks away
const SHRINK_TIME := 0.45
const RECOIL_TIME := 0.07
const SETTLE_TIME := 0.35

var minis: Array[Node3D] = []
var auto_play := false
var _bout := 0
var _timer := 1.0
var _busy := false


var _cells: Node3D
var heights := {}     # a map's raised cells: cell -> how high


## The look-test board: render_preview.py's trees and rocks and render_standin_minis.py's line-up.
func build() -> void:
	setup(TREES, ROCKS)
	for m in LINEUP:
		var c: Vector2i = m[1]
		minis.append(add_mini(m[0], c, Vector2(0, 1) if m[0] == "standin_enemy" else Vector2(0, -1)))


## Lays out the 61 cells with the given trees and rocks (clears any earlier board).
func setup(trees: Array, rocks: Array) -> void:
	for child in get_children():
		child.free()
	minis.clear()
	var kit := Kit.meshes("res://art/combat_cells.glb")
	_cells = Node3D.new()
	_cells.name = "cells"
	add_child(_cells)
	for c in cells():
		var name := "cell_tree" if c in trees else "cell_rock" if c in rocks else "cell_grass_" + "abc"[posmod(c.x - c.y, 3)]
		Kit.place(_cells, kit, name, Hex.cell_position(c.x, c.y))


## An approved map in place of the look-test board. Returns its triangles.
func setup_map(id: String) -> int:
	for child in get_children():
		child.free()
	minis.clear()
	_cells = Node3D.new()
	_cells.name = "cells"
	add_child(_cells)
	return CombatMap.build(id, _cells)


static func cells() -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	for q in range(-RADIUS, RADIUS + 1):
		for r in range(maxi(-RADIUS, -q - RADIUS), mini(RADIUS, -q + RADIUS) + 1):
			out.append(Vector2i(q, r))
	return out


func add_mini(name: String, c: Vector2i, facing: Vector2) -> Node3D:
	var mini := Minis.make(name, Hex.cell_position(c.x, c.y), facing)
	add_child(mini)
	return mini


func _process(delta: float) -> void:
	if not auto_play or _busy:
		return
	_timer -= delta
	if _timer <= 0.0:
		play_next()


func _unhandled_input(event: InputEvent) -> void:
	if visible and event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_SPACE:
		play_next()


func play_next() -> void:
	if _busy:
		return
	var b: Array = BOUTS[_bout % BOUTS.size()]
	_bout += 1
	attack(minis[b[0]], minis[b[1]])


## The attacker hops toward the target; on landing the target recoils (tips away and slides back), then settles.
## hit = false: the target doesn't recoil (a miss). Can be awaited.
func attack(attacker: Node3D, target: Node3D, hit := true) -> void:
	_busy = true
	var body := attacker.get_node("body") as Node3D
	var tbody := target.get_node("body") as Node3D
	var to_target := target.position - attacker.position
	to_target.y = 0
	to_target = to_target.normalized()
	# The attacker turns to face the target first.
	var face := snappedf(atan2(to_target.x, to_target.z), PI / 3.0)   # a base stays lined up with its cell (art/handoff/combat_forest_kit.md)
	var tw := create_tween()
	if attacker.has_meta("pivot"):
		tw.tween_interval(0.12)   # PLACEHOLDER: a giant's facing stays fixed (design/03: turning is open)
	else:
		tw.tween_property(attacker, "rotation:y", attacker.rotation.y + wrapf(face - attacker.rotation.y, -PI, PI), 0.12)
	# Hop: up and forward, then down and back. The lean is in the body's local space (forward = +Z).
	var lean := Vector3(0, HOP_HEIGHT, HOP_LEAN)
	tw.tween_property(body, "position", lean, HOP_TIME).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tw.tween_property(body, "position", Vector3.ZERO, HOP_TIME).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	if hit:
		tw.tween_callback(func(): _recoil(target, tbody, to_target))
	tw.tween_interval(SETTLE_TIME + 0.15)
	tw.tween_callback(func():
		_busy = false
		_timer = 1.2)
	await tw.finished


## Slides a mini hex by hex along a path of cells, turning to face each step.
func step_along(mini: Node3D, path: Array) -> void:
	for c: Vector2i in path:
		var pivot: Vector2 = mini.get_meta("pivot", Vector2.ZERO)
		var to := Hex.to3(Hex.cell_position(c.x, c.y) + pivot, heights.get(c, 0.0))
		var d := to - mini.position
		var tw := create_tween()
		if d.length() > 0.01 and not mini.has_meta("pivot"):
			tw.tween_property(mini, "rotation:y", mini.rotation.y + wrapf(atan2(d.x, d.z) - mini.rotation.y, -PI, PI), 0.08)
		tw.tween_property(mini, "position", to, 0.18 if is_zero_approx(d.y) else 0.26).set_trans(Tween.TRANS_SINE)
		await tw.finished


## A downed mini tips over and stays down.
## A downed mini tips over. A fallen foe then shrinks into nothing and is hidden (Ethan's phone note, Nov 5, 2026), without
## holding up the turn; a downed ally stays lying there, since it can still be brought back (03 -> Downed).
func fall(mini: Node3D, vanish := false) -> void:
	var body := mini.get_node("body") as Node3D
	var tw := create_tween()
	tw.tween_property(body, "quaternion", Quaternion(Vector3.RIGHT, deg_to_rad(-80)), 0.35).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	await tw.finished
	if vanish:
		var gone := create_tween()
		gone.tween_interval(SHRINK_WAIT)
		gone.tween_property(mini, "scale", Vector3.ONE * 0.01, SHRINK_TIME).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		gone.tween_callback(func(): mini.visible = false)
		mini.set_meta("vanish", gone)


## Back on its feet at full size (test aid: the checks reuse a fallen unit).
func stand(mini: Node3D) -> void:
	if mini.has_meta("vanish"):
		(mini.get_meta("vanish") as Tween).kill()
		mini.remove_meta("vanish")
	mini.scale = Vector3.ONE
	mini.visible = true
	(mini.get_node("body") as Node3D).quaternion = Quaternion.IDENTITY


func _recoil(target: Node3D, tbody: Node3D, dir: Vector3) -> void:
	# Push and tilt in the target's local space: the hit comes along dir (world).
	var local_dir := (target.basis.inverse() * dir).normalized()
	var axis := Vector3.UP.cross(local_dir).normalized()
	var tw := create_tween().set_parallel()
	tw.tween_property(tbody, "position", local_dir * RECOIL_PUSH, RECOIL_TIME).set_ease(Tween.EASE_OUT)
	tw.tween_property(tbody, "quaternion", Quaternion(axis, deg_to_rad(RECOIL_TILT)), RECOIL_TIME).set_ease(Tween.EASE_OUT)
	tw.chain().tween_property(tbody, "position", Vector3.ZERO, SETTLE_TIME).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.parallel().tween_property(tbody, "quaternion", Quaternion.IDENTITY, SETTLE_TIME).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
