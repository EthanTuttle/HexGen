class_name CoinView
extends Control
## A flipped coin as in the mockups: gold with "H" for heads, grey with "T" for tails; plain before it's flipped, and
## ringed for a companion's coin.

var heads := true
var diameter := 34.0
var is_blank := false
var ring := Color(0, 0, 0, 0)
var is_lost := false   # a coin a modifier took: greyed, never flipped
const BUFF_RING := Color("#2E9A3E")     # a modifier chip's ring (07 -> Modifier coins); PLACEHOLDER shades
const PENALTY_RING := Color("#C62E24")


## The ink of each modifier's icon on a coin (Fight.attack_mods). PLACEHOLDER icons and inks.
const MOD_INK := {"bless": "#B07A12", "forge": "#5A4528", "glow": "#B07A12", "acid": "#4F7A12", "cover": "#2E6B32",
	"close": "#B3261E", "night": "#3E5A70"}
const MOD_ICON := {"opening": "bolt", "frail": "drop", "exposed": "parry", "drowsy": "moon", "bless": "star", "forge": "mace", "glow": "spark", "acid": "acid", "cover": "tree_fill", "close": "swords",
	"night": "moon"}


static func make(h: bool, d := 34.0) -> CoinView:
	var c := CoinView.new()
	c.heads = h
	c.diameter = d
	c.custom_minimum_size = Vector2(d, d)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return c


## A coin still to flip, or spinning (Social v9).
static func blank(d := 34.0) -> CoinView:
	var c := make(true, d)
	c.is_blank = true
	return c


## A coin a penalty took (03 -> Coin checks -> Readable flips): greyed in the row, with the penalty's icon.
static func lost(d: float, mod: String, good := false) -> CoinView:
	var c := make(false, d)
	c.is_lost = true
	c.add_badge(mod, good)
	return c


## A modifier's chip, `d` across. Its ring is from the party's side, whoever flips (07 -> Modifier coins): green when it
## helps the party, red when it hurts it.
static func mod_chip(d: float, mod: String, good: bool) -> StatusChip:
	return StatusChip.make(d, MOD_ICON.get(mod, mod), Color(MOD_INK.get(mod, "#33403B")), 0, BUFF_RING if good else PENALTY_RING)


## The modifier's chip on the coin's top right corner.
func add_badge(mod: String, good := true) -> void:
	var chip := mod_chip(roundf(diameter * 0.5), mod, good)
	chip.position = Vector2(diameter - chip.size.x * 0.7, -chip.size.y * 0.3)
	add_child(chip)


func _draw() -> void:
	var r := diameter * 0.5
	var ctr := Vector2(r, r)
	if ring.a > 0:
		draw_circle(ctr, r + 3, ring)
	var bg := Color("#EFE6D3") if is_blank else (UI.GOLD if heads else Color("#CFC2A8"))
	var edge := UI.CREAM_EDGE if is_blank else (UI.GOLD_EDGE if heads else Color("#8A7D66"))
	var ink := Color("#5A3A05") if heads else Color("#4A4034")
	if is_lost:   # PLACEHOLDER look: a flat pale grey coin, no letter
		draw_circle(ctr, r, Color("#B3AB9C"))
		draw_circle(ctr, r - 1.5, Color("#E2DDD3"))
		return
	draw_circle(ctr, r, edge)
	draw_circle(ctr - Vector2(0, 1.5), r - 1.5, bg)
	if is_blank:
		return
	var f := UI.font("lilita")
	var sz := int(diameter * 0.44)
	var t := "H" if heads else "T"
	var ts := f.get_string_size(t, HORIZONTAL_ALIGNMENT_LEFT, -1, sz)
	var asc := f.get_ascent(sz)
	draw_string(f, Vector2(r - ts.x * 0.5, r - (asc + f.get_descent(sz)) * 0.5 + asc - 1), t, HORIZONTAL_ALIGNMENT_LEFT, -1, sz, ink)
