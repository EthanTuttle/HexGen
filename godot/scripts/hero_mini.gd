class_name HeroMini
extends RefCounted
## The hero as one merged mesh, built from a description by the steps in art/handoff/hero_kit.md: the kit's pieces placed by
## art/export/heroes_placements.json, player colours swapped in where the vertex colours carry a mark. The description, not
## the mesh, is what a save or a guest carries later.
## description: {race, build, head, hair, armour, main, offhand, two, caster, colours: {skin, hair, eyes, cloth}}, in the kit's
## words (kit v10: every pose moves the whole hero, legs and arms are posed parts).

const GLB := "res://art/heroes.glb"
const TABLE := "res://art/heroes_placements.json"
const MARK_BLUE := 253                 # a mark's blue in sRGB bytes. Nothing else in the kit has it
const ZONES: Array[String] = ["", "skin", "hair", "eyes", "cloth"]
const CASTERS := ["wizard", "cleric", "bard"]   # DOCS (07 -> Pose library): a staff with an empty hand takes the casting pose

static var _t := {}
static var _pieces := {}               # piece -> its arrays and marks, read once
static var _material: Material
static var _mesh_for := {}             # description's text -> the mesh, so the map and fights share one


static func table() -> Dictionary:
	if _t.is_empty():
		_t = JSON.parse_string(FileAccess.get_file_as_string(TABLE))
	return _t


## A hero from the creator, in the kit's words. Creator's names differ here and there.
static func description(h: Hero) -> Dictionary:
	var a := h.appearance
	var t := table()
	var main: String = {"knuckles": "brass_knuckles"}.get(h.gear.get("main", ""), h.gear.get("main", ""))
	var off: String = h.gear.get("off", "")
	off = "" if off == "none" else {"knuckles": "brass_knuckles"}.get(off, off)
	var armour: String = str(h.gear.get("armour", "none")).to_lower()
	if main == "":
		main = "longsword"
	return {
		"race": h.race.to_lower(), "build": str(a.get("build", "Average")).to_lower(),
		"head": t.heads[int(a.get("head", 0))], "hair": t.hairstyles[int(a.get("hair", 0))],
		"armour": armour, "main": main, "offhand": off,
		# 07 -> Pose library: a versatile weapon with the off hand empty is held in both hands (04's two-handed damage);
		# a caster class's staff with an empty hand casts, a martial's takes the quarterstaff guard.
		"two": off == "" and main in t.two_grip, "caster": off == "" and main == "staff" and h.klass.to_lower() in CASTERS,
		"colours": {"skin": a.get("skin", "#F3D2B5"), "hair": a.get("hair_colour", "#2B211C"), "eyes": a.get("eyes", "#4F7A33"), "cloth": a.get("cloth", "#B5532F")},
	}


## The mesh for this hero, built once.
static func mesh_for(h: Hero) -> ArrayMesh:
	var d := description(h)
	var key := JSON.stringify(d)
	if not _mesh_for.has(key):
		_mesh_for[key] = build(d)
	return _mesh_for[key]


## The same for a description with no Hero behind it (a keeper).
static func mesh_for_description(d: Dictionary) -> ArrayMesh:
	var key := JSON.stringify(d)
	if not _mesh_for.has(key):
		_mesh_for[key] = build(d)
	return _mesh_for[key]


static func _matrix(m: Array) -> Transform3D:
	return Transform3D(Basis(Vector3(m[0], m[1], m[2]), Vector3(m[3], m[4], m[5]), Vector3(m[6], m[7], m[8])), Vector3(m[9], m[10], m[11]))


## Which pieces, with which matrix: the hand-off's "What Godot needs" (from_table() in art/scripts/export_hero_kit.py).
## [[piece, matrix or null]...]
static func parts(d: Dictionary) -> Array:
	var t := table()
	var race: String = d.race
	var build: String = d.build
	var armour: String = d.armour if d.armour != "" else "none"
	var main: String = d.main
	var off: String = d.offhand
	var variant := "none"
	if main == "staff" and d.get("caster", false) and off == "":
		variant = "cast"
	elif d.get("two", false) and main in t.two_grip and off == "":
		variant = "two"
	elif off != "":
		variant = "shield" if off == "shield" else "second"
	var pose: Dictionary = t.races[race].builds[build].poses[main][variant]
	var golem := race == "golem"
	var leg := "golem" if golem else ("scaled" if race == "dragonborn" else "cloth")
	var kind: String = "golem" if golem else {"medium": "chain", "heavy": "plate"}.get(armour, "bare")
	var fist := "golem" if golem else ("gauntlet" if armour == "heavy" else "bare")
	var out: Array = [["hero_base", null], ["hero_body_%s_%s" % [race, build], pose.torso]]
	if armour != "none":
		out.append(["hero_armour_%s_%s_%s" % [armour, race, build], pose.torso])
	out.append(["hero_head_%s_%s" % [race, d.head], pose.head])
	if d.hair != "" and d.hair != "none" and not race in t.hairless:
		out.append(["hero_hair_%s" % d.hair, pose.hair])
	for l: Dictionary in pose.legs:
		out.append(["hero_leg_upper_" + leg, l.upper])
		out.append(["hero_leg_lower_" + leg, l.lower])
		if armour == "heavy" and not golem:
			out.append(["hero_leg_greave", l.greave])
		out.append(["hero_boot_golem" if golem else "hero_boot_leather", l.boot])
	for arm: Dictionary in pose.arms:   # right, then left
		out.append(["hero_arm_upper_" + kind, arm.upper])
		out.append(["hero_arm_fore_" + kind, arm.fore])
		out.append(["hero_hand_open_wraps" if arm.hand_piece == "open_wraps" else "hero_hand_" + fist, arm.hand])
		if arm.has("fist_weapon"):
			out.append(["hero_" + main, arm.fist_weapon])
	if pose.has("main"):
		out.append(["hero_" + main, pose.main])
	if off != "":
		out.append(["hero_shield" if off == "shield" else "hero_" + off, pose.offhand])
	return out


## A piece's arrays, with where its marks are, worked out once (the hand-off's step 2).
static func _piece(piece: String) -> Dictionary:
	if _pieces.has(piece):
		return _pieces[piece]
	var kit := Kit.meshes(GLB)
	if _material == null:
		Kit.combat_materials(kit)
	var mesh: Mesh = kit[piece]
	if _material == null:
		_material = mesh.surface_get_material(0)
	var a := mesh.surface_get_arrays(0)
	var cols: PackedColorArray = a[Mesh.ARRAY_COLOR]
	var marks := PackedInt32Array()
	var zones := PackedByteArray()
	var shades := PackedFloat32Array()
	for i in cols.size():
		var s := cols[i].linear_to_srgb()
		if roundi(s.b * 255.0) >= MARK_BLUE:
			marks.append(i)
			zones.append(clampi(roundi(s.r * 255.0 / 20.0), 1, 4))
			shades.append(pow(s.g * 255.0 / 100.0, 2.2))
	var out := {"verts": a[Mesh.ARRAY_VERTEX], "normals": a[Mesh.ARRAY_NORMAL], "colors": cols, "index": a[Mesh.ARRAY_INDEX],
		"marks": marks, "zones": zones, "shades": shades}
	_pieces[piece] = out
	return out


static func build(d: Dictionary) -> ArrayMesh:
	var swatch: Array[Color] = [Color.WHITE]
	for z in range(1, 5):
		swatch.append(Color.from_string(d.colours[ZONES[z]], Color.BLACK).srgb_to_linear())   # a race with no hair has no hair colour ("")
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	var index := PackedInt32Array()
	for part: Array in parts(d):
		var p := _piece(part[0])
		var at := verts.size()
		var src_colors: PackedColorArray = (p.colors as PackedColorArray).duplicate()   # packed arrays are shared, not copied
		var marks: PackedInt32Array = p.marks
		var zones: PackedByteArray = p.zones
		var shades: PackedFloat32Array = p.shades
		for k in marks.size():
			var c: Color = swatch[zones[k]]
			var s: float = shades[k]
			src_colors[marks[k]] = Color(minf(c.r * s, 1.0), minf(c.g * s, 1.0), minf(c.b * s, 1.0), 1.0)
		colors.append_array(src_colors)
		if part[1] == null:
			verts.append_array(p.verts)
			normals.append_array(p.normals)
		else:
			var t := _matrix(part[1])
			verts.append_array(t * (p.verts as PackedVector3Array))
			# Scale isn't uniform on arms, legs, open palms and planted weapons: normals by the inverse transpose.
			var n: PackedVector3Array = Transform3D(t.basis.inverse().transposed(), Vector3.ZERO) * (p.normals as PackedVector3Array)
			for k in n.size():
				n[k] = n[k].normalized()
			normals.append_array(n)
		var src_index: PackedInt32Array = (p.index as PackedInt32Array).duplicate()
		for k in src_index.size():
			src_index[k] += at
		if part[1] != null and _matrix(part[1]).basis.determinant() < 0.0:
			for k in range(0, src_index.size(), 3):   # a mirrored piece: reverse each face's winding
				var swap := src_index[k + 1]
				src_index[k + 1] = src_index[k + 2]
				src_index[k + 2] = swap
		index.append_array(src_index)
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_COLOR] = colors
	arrays[Mesh.ARRAY_INDEX] = index
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.surface_set_material(0, _material)
	# The walker and framing read a mini's width from its box: the base's, not a long weapon's.
	var box := mesh.get_aabb()
	var base: AABB = Kit.meshes(GLB).hero_base.get_aabb()
	mesh.custom_aabb = AABB(Vector3(base.position.x, box.position.y, base.position.z), Vector3(base.size.x, box.size.y, base.size.z))
	return mesh


## The hand-off's "one test": what the colours came through import as. Prints each zone's marks and how far the shades drift.
static func decode_report() -> String:
	var counts := [0, 0, 0, 0, 0]
	var low := 9.0
	var high := 0.0
	var bad := 0
	var kit := Kit.meshes(GLB)
	for piece: String in kit:
		var p := _piece(piece)
		for k in p.zones.size():
			counts[p.zones[k]] += 1
			var s: float = pow(p.shades[k], 1.0 / 2.2)
			low = minf(low, s)
			high = maxf(high, s)
		for c: Color in p.colors:
			var q := c.linear_to_srgb()
			if q.b > 0.95 and roundi(q.b * 255.0) < MARK_BLUE:
				bad += 1
	return "marks skin %d, hair %d, eyes %d, cloth %d; shades %.2f to %.2f; near-marks missed %d; %d pieces" % [counts[1], counts[2], counts[3], counts[4], low, high, bad, kit.size()]
