class_name CombatBoard
extends Node3D
## The radius-4 combat board (61 flat-top cells; art/scripts/render_preview.py build_board) with
## stand-in minis, and the attack motions (AttackMotions; look test 3). Space plays an attack;
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
const SHRINK_WAIT := 0.35     # PLACEHOLDER: a fallen foe lies there this long, then shrinks away
const SHRINK_TIME := 0.45

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
	_clock += delta
	_draw_glows()
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


## An attack's motion (art/handoff/attack_motions.md, AttackMotions): the attacker turns to face the target first, then plays
## its kind's motion; hit = false plays the miss (the target sidesteps). Can be awaited.
func attack(attacker: Node3D, target: Node3D, hit := true, kind := "melee") -> void:
	_busy = true
	await _face(attacker, target)
	await AttackMotions.new(self).attack(kind, attacker, target, hit)
	_busy = false
	_timer = 1.2


## Sweeping Arc's one spin over all its foes (AttackMotions.sweep), after turning to face the first. Can be awaited.
func sweep(attacker: Node3D, targets: Array, hits: Array) -> void:
	_busy = true
	if not targets.is_empty():
		await _face(attacker, targets[0])
	await AttackMotions.new(self).sweep(attacker, targets, hits)
	_busy = false
	_timer = 1.2


## Turns an attacker to face its target, snapped to a cell side.
func _face(attacker: Node3D, target: Node3D) -> void:
	var to_target := target.position - attacker.position
	to_target.y = 0
	to_target = to_target.normalized()
	var face := snappedf(atan2(to_target.x, to_target.z), PI / 3.0)   # a base stays lined up with its cell (art/handoff/combat_forest_kit.md)
	var tw := create_tween()
	if attacker.has_meta("pivot"):
		tw.tween_interval(0.12)   # PLACEHOLDER: a giant's facing stays fixed (design/03: turning is open)
	else:
		tw.tween_property(attacker, "rotation:y", attacker.rotation.y + wrapf(face - attacker.rotation.y, -PI, PI), 0.12)
	await tw.finished


## A single-target save spell (AttackMotions.bloom): spell "flame", "glow" or "lull"; passed: the foe saved.
func bloom(caster: Node3D, foe: Node3D, spell: String, passed: bool) -> void:
	_busy = true
	await _face(caster, foe)
	await AttackMotions.new(self).bloom(caster, foe, spell, passed)
	_busy = false
	_timer = 1.2


# Faerie Fire's lasting look: a glow outline round the mini, pulsing, with eight motes circling it and twinkling, for as long
# as it glows (art/handoff/attack_motions.md -> Single-target save spells). PLACEHOLDER: the motes stay as long as the
# outline; the handoff gives them no end.
var _clock := 0.0   # frame time, so a fixed-rate capture plays at real speed
var _glows := {}    # mini -> [hull, motes (AttackMotions.Fx), started]


## Turns a mini's glow on (from now) or off.
func glow(mini: Node3D, on: bool) -> void:
	if on and not _glows.has(mini):
		var cols: Array = AttackMotions.SAVE_COLS["glow"]
		var motes := []
		for n in 8:
			motes.append(AttackMotions.Fx.new(self, AttackMotions.ico(0.055, 0), Color(cols[1] if n % 2 else cols[2])))
		_glows[mini] = [hull(mini, cols[0]), motes, _clock]
	elif not on and _glows.has(mini):
		_drop_glow(mini)


func _drop_glow(mini: Node3D) -> void:
	var g: Array = _glows[mini]
	if is_instance_valid(g[0]):
		g[0].queue_free()
	for f: AttackMotions.Fx in g[1]:
		f.node.queue_free()
	_glows.erase(mini)


func _draw_glows() -> void:
	for mini: Node3D in _glows.keys():
		if not is_instance_valid(mini) or not mini.is_inside_tree():
			_drop_glow(mini)
			continue
		var g: Array = _glows[mini]
		var t: float = _clock - g[2]
		hull_alpha(g[0], AttackMotions.out(AttackMotions.seg(t, 0.0, 0.12)) * (0.75 + 0.2 * sin(TAU * 2.2 * t)))
		var c := mini.global_position
		var cam := get_viewport().get_camera_3d()
		var toward := AttackMotions.flat(cam.global_position - c) * AttackMotions.FRONT if cam else Vector3.ZERO
		for n in 8:
			var f: AttackMotions.Fx = g[1][n]
			var ph := t - 0.05 * n
			if ph > 0.0 and mini.visible:
				var tw := AttackMotions.bump(fmod(ph * 1.6, 1.0))
				f.show(c + AttackMotions.dir_at(n * 45.0 + 40.0 * ph) * 0.32 + Vector3.UP * (0.2 + 0.09 * n) + toward * 0.3, 0.6 + 0.6 * tw, Basis.IDENTITY, tw)
			else:
				f.hide()


## A glow outline (inverted hull) of the mini's mesh in `col`, on its body so it follows every move; hidden until
## hull_alpha shows it.
func hull(mini: Node3D, col: String) -> MeshInstance3D:
	var body := mini.get_node("body") as MeshInstance3D
	var h := MeshInstance3D.new()
	h.name = "glow_hull"
	h.mesh = AttackMotions.hull_mesh(body.mesh)
	h.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.cull_mode = BaseMaterial3D.CULL_FRONT
	m.albedo_color = Color(col, 0.0)
	h.material_override = m
	h.visible = false
	body.add_child(h)
	return h


func hull_alpha(h: MeshInstance3D, a: float) -> void:
	if not is_instance_valid(h):
		return
	var m := h.material_override as StandardMaterial3D
	m.albedo_color.a = clampf(a, 0.0, 1.0)
	h.visible = a > 0.003


## Bless and heals: the rising ring on the ally (AttackMotions.buff).
func buff(caster: Node3D, ally: Node3D) -> void:
	await AttackMotions.new(self).buff(caster, ally)


## A summon drops onto its cell (AttackMotions.summon).
func summon(caster: Node3D, it: Node3D) -> void:
	await AttackMotions.new(self).summon(caster, it)


## Breath Weapon's cone (AttackMotions.cone), toward a direction, over the line's cell points; `hit` minis recoil.
func cone(breather: Node3D, toward: Vector3, cells: Array, hit: Array) -> void:
	await AttackMotions.new(self).cone(breather, toward, cells, hit)


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
