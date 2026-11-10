class_name Places
extends RefCounted
## Every place you enter and the scene it opens (design/07 -> Town screen -> Each place gets its own scene; plan approved
## by Ethan, Nov 9, 2026). A kit is a glb and a JSON from the art side; a place names its kit, its cards and its subtitle.
## A place with no kit of its own yet opens the market square (PLACEHOLDER), so every place you enter opens a scene.
##
## Kit JSON (as art/town_scenes.json): `hexes` {"q,r": [x, y]}, and `spots`, `keepers` keyed by the kit's scene name.
## `places` (what the party walks to) and `lights` are read per kit. A new kit's JSON may carry its own `lights` and
## `backdrop`; the town kit's live here, as its JSON predates them.

## A kit's scene. glb, json, mesh: where it is. backdrop: "" for the map's day and night, or a flat colour. glow: the
## ts_glow emission by day (night is NIGHT_GLOW). night_sun: the sun's scale at night. focus: where the camera holds on
## screen, between the speaker's panel and the cards. lights: [q, r, x, y, z, colour, day, night, flicker], Blender's
## energies (PlaceStage.LIGHT_SCALE turns them into Godot's); a light at 0 is off.
const KITS := {
	"square": {"glb": "res://art/town_scenes.glb", "json": "res://art/town_scenes.json", "mesh": "town_square",
		"backdrop": "", "glow": 0.4, "night_sun": 1.0, "focus": Vector2(450, 174), "lights": [
			[-1, -1, 0.5, 1.8, -0.2, "#FFC27A", 0.0, 32.0, false], [2, 0, 0.5, 1.8, -0.2, "#FFC27A", 0.0, 32.0, false],
			[1, -2, 0.5, 0.9, -0.2, "#FFC27A", 0.0, 32.0, false]]},
	# The one inn every town and the roadside Inn share (Ethan, Nov 9, 2026); The Oak & Lantern gets its own.
	"inn": {"glb": "res://art/town_scenes.glb", "json": "res://art/town_scenes.json", "mesh": "town_inn",
		"backdrop": "#2A1C15", "glow": 0.9, "night_sun": 0.5, "focus": Vector2(450, 186), "lights": [
			[-2, 1, 0.5, 0.9, -0.15, "#FF8C40", 55.0, 75.0, true],
			[0, 0, 0.0, 1.2, 0.0, "#FFC27A", 8.0, 16.0, false], [2, 0, 0.0, 1.2, 0.0, "#FFC27A", 8.0, 16.0, false],
			[0, -2, 0.3, 1.5, -0.9, "#FFC27A", 8.0, 16.0, false], [2, -2, 0.3, 1.5, -0.9, "#FFC27A", 8.0, 16.0, false]]},
}
const NIGHT_GLOW := 1.6
## PLACEHOLDER: the keepers are the hero kit's minis in a keeper's colour; no keeper models yet.
const KEEPER_COLOURS := {"shopkeeper": "#B0672A", "innkeeper": "#3F6FA8"}

## Each place: its kit (the square it opens on), the inn it uses, its cards and its subtitle. own: false while it borrows
## the market square (PLACEHOLDER until its kit is made). Town variants hold their landmark in the square (Ethan,
## Nov 9, 2026: the Trading House, Keep, Black Market and College are part of their town's square).
## PLACEHOLDER: every town's places and services (design/07 -> open question); each has today's Shop and Inn.
const PLACES := {
	"market_town": {"kit": "square", "own": true, "inn": "inn", "cards": ["shop", "inn"], "sub": "Market town"},
	"fortified_town": {"kit": "square", "own": false, "inn": "inn", "cards": ["shop", "inn"], "sub": "Market town"},
	"slums": {"kit": "square", "own": false, "inn": "inn", "cards": ["shop", "inn"], "sub": "Market town"},
	"scholars_town": {"kit": "square", "own": false, "inn": "inn", "cards": ["shop", "inn"], "sub": "Market town"},
	# The starting tiles that are a town and an inn (design/06 -> Towns); each gets a hand-made scene.
	"start_criminal": {"kit": "square", "own": false, "inn": "inn", "cards": ["shop", "inn"], "sub": "Market town"},
	"start_folk_hero": {"kit": "square", "own": false, "inn": "inn", "cards": ["shop", "inn"], "sub": "Market town"},
}


## Which place tile t is: a starting tile by its background, else its town variant (a landmark counts as its town's).
static func id_at(game: Game, t: Vector2i) -> String:
	if t == Rules.START_TILE and game.run != null and PLACES.has("start_" + game.run.background):
		return "start_" + game.run.background
	var name: String = str(game.map.terrains.get(t, ""))
	name = Variants.LANDMARKS.get(name, name)
	return name if PLACES.has(name) else "market_town"


static func at(game: Game, t: Vector2i) -> Dictionary:
	return PLACES[id_at(game, t)]
