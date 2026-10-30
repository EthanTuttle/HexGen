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
	"plains": "#A8CF7E", "forest": "#5E8F5A", "farmland": "#DCC562", "river": "#86BEDB", "village": "#E6C590",
	"hills": "#BFAE8E", "swamp": "#7F9A6E", "desert": "#EDD49A", "ruins": "#B3ADA4", "soil_light": "#8A6446",
	"soil_dark": "#6B4C35", "grass_ink": "#7FA95A", "leaf": "#4E8049", "leaf_dark": "#3B6A3A",
	"trunk": "#7A5236", "field_a": "#DCC562", "field_b": "#C9A94A", "field_c": "#9DBF5E", "hedge": "#4F7A33",
	"water": "#86BEDB", "bank": "#C9B58A", "reed": "#6E8F3E", "lily": "#5E9E4E", "boat": "#E9DCC0",
	"wall": "#EFE2C6", "roof": "#B5523B", "road": "#CDB58A", "cobble": "#BCB2A4", "cobble_dark": "#A69C8E",
	"fence": "#8A6446", "rock": "#A9A39A", "rock_dark": "#8F897F", "rock_light": "#BEB8AE",
	"stone_tan": "#B8A88E", "stone_blue": "#8E959B", "stone_brown": "#9C8B78", "flower": "#F2D46B",
	"hill_grass": "#A3C47A", "cliff": "#A89F8E", "sand": "#F3DFAC", "cracked": "#D8BB7E", "scrub": "#9C9A5C",
	"cactus": "#6E9A5A", "bog_water": "#5F7F6C", "mud": "#7A7152", "hummock": "#6F8E5C", "deadwood": "#7C6E5E",
	"deep_forest": "#466F47", "pine_deep": "#3A6A41", "hide": "#8A6A4E", "hide_light": "#C9B79C",
	"flower_pink": "#E9A3B8", "flower_white": "#F4F1E8", "flower_blue": "#9DB4E0", "highland_grass": "#9FB07E",
	"heather": "#9C6FA0", "hay": "#E3C45E", "stubble": "#D9C27A", "sail": "#EFE6D2", "timber": "#5E4532",
	"awning_a": "#C8553D", "awning_b": "#F2E8D5", "crate": "#A7825A", "fruit": "#D9822B", "sandbar": "#E3D3A8",
	"bog": "#6B8462", "bog_dark": "#4A6457", "toadstool": "#F0C24E", "poison_purple": "#8E4FA6",
	"poison_yellow": "#E6D23F", "spiky": "#4F6B3A", "wasteland": "#E2CFA2", "sandstone": "#D6B484",
	"bone": "#F1EBDD", "pit": "#6B5038", "pit_dark": "#3A2B20", "canvas": "#E2B98A", "lantern": "#F6D36B",
	"rope": "#C9B58A", "slot": "#F6EFE4", "backdrop": "#CFE4F2", "cell_grass_a": "#8DBB7A",
	"cell_grass_b": "#96C283", "cell_grass_c": "#88B575",
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
