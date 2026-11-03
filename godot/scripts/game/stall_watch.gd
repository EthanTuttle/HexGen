class_name StallWatch
extends Node
## A test aid: on a check, demo or touch run, prints the game's state when nothing has moved for STALL_SECONDS (a check's
## await that never ends otherwise just stops the output: DOCS: 06 -> Engine prototype, error logging). Test output only.
## Checks call beat() as they go.

const STALL_SECONDS := 60.0

static var _beats := 0
static var _last := ""

var game: Game
var _quiet := 0.0
var _seen := []
var _reported := false


## A check has got this far.
static func beat(what: String) -> void:
	_beats += 1
	_last = what


func _process(delta: float) -> void:
	var now := [_beats, game.map.tiles_built, game.party_node.members[0].node.position, game.rig.target, game.rig.distance, game.fight.active, game.busy]
	if now != _seen:
		_seen = now
		_quiet = 0.0
		_reported = false
		return
	_quiet += delta
	if _quiet > STALL_SECONDS and not _reported:
		_reported = true
		print("STALL %d s with nothing moving, last check: %s | tile %s, busy %s, walking %s, holding %s, check pop-up %s, shop %s, encounter %s, fight %s, day %d minute %.1f, tiles built %d" % [
				int(_quiet), _last, game.party_tile, game.busy, game.party_node.walking, game.party_node.holding,
				game.hud.check.visible, game.hud.shop.visible, game.hud.encounter_open(), game.fight.active, game.day, game.minute, game.map.tiles_built])
