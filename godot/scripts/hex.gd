class_name Hex
extends RefCounted
## Sizes, palette and hex maths, copied from art/scripts/hexkit.py.
##
## The art scripts work in Blender's plan coordinates (X east, Y north, Z up). Here the same plan
## point is a Vector2 (x, y), and to3() turns it into Godot's Y-up world: (x, height, -y).
## Edge rotations carry over unchanged: rotation.y = 60 degrees x i.

const CELL_FLATS := 1.0
const CELL_RADIUS := CELL_FLATS / sqrt(3.0)
const R := 4.5                       # map tile, centre to corner (pointy-top)
const A := R * sqrt(3.0) / 2.0       # map tile apothem
const INNER := 0.45

# Axial neighbour offsets for pointy-top tiles, edge 0 facing +X, anticlockwise.
const NEIGHBOURS := [Vector2i(1, 0), Vector2i(1, -1), Vector2i(0, -1), Vector2i(-1, 0), Vector2i(-1, 1), Vector2i(0, 1)]

const PALETTE := {
	"plains": "#A8CF7E", "forest": "#5E8F5A", "farmland": "#DCC562", "river": "#86BEDB",
	"village": "#E6C590", "soil_light": "#8A6446", "soil_dark": "#6B4C35",
	"grass_ink": "#4F7A33", "leaf": "#4E8049", "leaf_dark": "#3B6A3A", "trunk": "#7A5236",
	"water": "#86BEDB", "bank": "#C9B58A", "reed": "#6E8F3E", "lily": "#5E9E4E", "boat": "#E9DCC0",
	"cobble": "#BCB2A4", "fence": "#8A6446", "rock": "#A9A39A", "flower": "#F2D46B",
	"slot": "#F6EFE4", "backdrop": "#CFE4F2",
}


static func colour(name: String) -> Color:
	return Color.html(PALETTE[name])


static func to3(p: Vector2, h := 0.0) -> Vector3:
	return Vector3(p.x, h, -p.y)


static func tile_position(q: int, r: int) -> Vector2:
	return Vector2(2.0 * A * (q + r / 2.0), -1.5 * R * r)


static func cell_position(q: int, r: int) -> Vector2:
	return Vector2(1.5 * CELL_RADIUS * q, -CELL_FLATS * (r + q / 2.0))


static func hex_corners(radius: float, pointy: bool) -> PackedVector2Array:
	var start := 90.0 if pointy else 0.0
	var out := PackedVector2Array()
	for i in 6:
		var a := deg_to_rad(start - 60.0 * i)
		out.append(Vector2(radius * cos(a), radius * sin(a)))
	return out
