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
const RECOIL_TIME := 0.07
const SETTLE_TIME := 0.35

var minis: Array[Node3D] = []
var auto_play := true
var _bout := 0
var _timer := 1.0
var _busy := false


func build() -> void:
	var kit := Kit.meshes("res://art/combat_cells.glb")
	var cells := Node3D.new()
	cells.name = "cells"
	add_child(cells)
	for q in range(-RADIUS, RADIUS + 1):
		for r in range(maxi(-RADIUS, -q - RADIUS), mini(RADIUS, -q + RADIUS) + 1):
			var c := Vector2i(q, r)
			var name := "cell_tree" if c in TREES else "cell_rock" if c in ROCKS else "cell_grass_" + "abc"[posmod(q - r, 3)]
			Kit.place(cells, kit, name, Hex.cell_position(q, r))
	for m in LINEUP:
		var c: Vector2i = m[1]
		var facing := Vector2(0, 1) if m[0] == "standin_enemy" else Vector2(0, -1)
		var mini := Minis.make(m[0], Hex.cell_position(c.x, c.y), facing)
		add_child(mini)
		minis.append(mini)


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
func attack(attacker: Node3D, target: Node3D) -> void:
	_busy = true
	var body := attacker.get_node("body") as Node3D
	var tbody := target.get_node("body") as Node3D
	var to_target := target.position - attacker.position
	to_target.y = 0
	to_target = to_target.normalized()
	# The attacker turns to face the target first.
	var face := atan2(to_target.x, to_target.z)
	var tw := create_tween()
	tw.tween_property(attacker, "rotation:y", attacker.rotation.y + wrapf(face - attacker.rotation.y, -PI, PI), 0.12)
	# Hop: up and forward, then down and back. The lean is in the body's local space (forward = +Z).
	var lean := Vector3(0, HOP_HEIGHT, HOP_LEAN)
	tw.tween_property(body, "position", lean, HOP_TIME).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tw.tween_property(body, "position", Vector3.ZERO, HOP_TIME).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	tw.tween_callback(func(): _recoil(target, tbody, to_target))
	tw.tween_interval(SETTLE_TIME + 0.4)
	tw.tween_callback(func():
		_busy = false
		_timer = 1.2)


func _recoil(target: Node3D, tbody: Node3D, dir: Vector3) -> void:
	# Push and tilt in the target's local space: the hit comes along dir (world).
	var local_dir := (target.basis.inverse() * dir).normalized()
	var axis := Vector3.UP.cross(local_dir).normalized()
	var tw := create_tween().set_parallel()
	tw.tween_property(tbody, "position", local_dir * RECOIL_PUSH, RECOIL_TIME).set_ease(Tween.EASE_OUT)
	tw.tween_property(tbody, "quaternion", Quaternion(axis, deg_to_rad(RECOIL_TILT)), RECOIL_TIME).set_ease(Tween.EASE_OUT)
	tw.chain().tween_property(tbody, "position", Vector3.ZERO, SETTLE_TIME).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.parallel().tween_property(tbody, "quaternion", Quaternion.IDENTITY, SETTLE_TIME).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
