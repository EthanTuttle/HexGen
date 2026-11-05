class_name CreatorMini
extends TextureRect
## PLACEHOLDER: the mockup's flat stand-in mini, drawn from the same picks with the same SVG, until Combat Art's mini kit
## is exported. Turning squeezes it as the mockup does, and the eyes go at the back.

const D = preload("res://scripts/creator/creator_data.gd")
const BODY := "M44 70 Q70 58 96 70 L102 120 Q96 124 90 120 L88 96 L86 128 L90 174 L76 174 L70 134 L64 174 L50 174 L54 128 L52 96 L50 120 Q44 124 38 120 Z"
const HEADS := [[17, 17], [15, 18.5], [18.5, 16], [16, 17]]
const TURN_X: Array[float] = [1.0, 0.62, -1.0, -0.62]


func setup(c: Creator, turn: int, hex_base: bool, w: float, h: float) -> void:
	texture = make(c, turn, hex_base, w, h)
	expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	custom_minimum_size = Vector2(w, h)
	size = Vector2(w, h)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	accessibility_name = "Your hero"


static func make(c: Creator, turn: int, _hex_base: bool, w: float, h: float) -> Texture2D:
	var race := c.race_data()
	var build_x: float = {"Slim": 0.86, "Average": 1.0, "Broad": 1.16}.get(c.build, 1.0)
	var hs: float = race.get("h", 1.0)
	var skin := c.colour_of("skin")
	var hair_d: String = D.HAIRD[c.hair] if race.get("hair", true) else ""
	var head: Array = HEADS[c.head]
	var mw := c.weapon(c.main)
	var off_icon := ""
	if c.off == "shield":
		off_icon = D.IC.shield
	elif c.off != "" and c.off != "none":
		off_icon = D.IC[c.weapon(c.off).i]
	var vi := posmod(turn, 4)
	var parts := PackedStringArray()
	parts.append('<svg xmlns="http://www.w3.org/2000/svg" width="%s" height="%s" viewBox="0 0 140 190">' % [w, h])
	parts.append('<path d="M30 178 L46 186 L94 186 L110 178 L94 170 L46 170 Z" fill="#8F7458"/>')
	parts.append('<path d="M30 174 L46 182 L94 182 L110 174 L94 166 L46 166 Z" fill="#B89C7E"/>')
	parts.append('<g transform="translate(70 0) scale(%s 1) translate(-70 0)"><g transform="translate(70 176) scale(%.3f %.3f) translate(-70 -176)">' % [TURN_X[vi], build_x * hs, hs])
	parts.append('<path d="%s" fill="%s"/>' % [BODY, c.colour_of("cloth")])
	parts.append('<circle cx="40" cy="121" r="5" fill="%s"/><circle cx="100" cy="121" r="5" fill="%s"/>' % [skin, skin])
	parts.append('<rect x="64" y="52" width="12" height="10" fill="%s"/>' % skin)
	if race.get("horns", false):
		parts.append('<path d="%s" fill="#E8DCC0"/>' % D.HORN)
	parts.append('<ellipse cx="70" cy="40" rx="%s" ry="%s" fill="%s"/>' % [head[0], head[1], skin])
	if hair_d != "":
		parts.append('<path d="%s" fill="%s"/>' % [hair_d, c.colour_of("hair")])
	if vi != 2:
		var eyes := c.colour_of("eyes")
		parts.append('<circle cx="64" cy="42" r="2.4" fill="%s"/><circle cx="76" cy="42" r="2.4" fill="%s"/>' % [eyes, eyes])
	if not mw.is_empty():
		parts.append('<g transform="translate(90 96) scale(1.5)"><path d="%s" fill="none" stroke="#33403B" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></g>' % D.IC[mw.i])
	if off_icon != "":
		parts.append('<g transform="translate(16 102) scale(1.3)"><path d="%s" fill="#FCF7EE" stroke="#33403B" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></g>' % off_icon)
	parts.append("</g></g></svg>")
	var img := Image.new()
	img.load_svg_from_string("".join(parts), 2.0)
	return ImageTexture.create_from_image(img)
