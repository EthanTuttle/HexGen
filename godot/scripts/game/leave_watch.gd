class_name LeaveWatch
extends RefCounted
## A test aid: watches followers while the party leaves a landmark, until the hero is well clear (they bunch up
## again on arriving, which isn't this). Followers on the hero's way out must not step toward where the hero stood
## (one round a bend walks its line to where the way out parts from it);
## each holds its spot until the hero has gone by, then keeps behind it.

const CLEAR := 8.0                      # metres the hero walks while being watched

var walker: PartyWalker
var hero_at: Vector2
var door: Vector2
var travelled := 0.0
var followers := []                     # {m, spot}
var stepped_in := 0.0                   # the most a follower on the way out moved toward the hero's old spot
var early := 0
var closest := INF                      # how near a moving follower came to the hero


func _init(party: PartyWalker) -> void:
	walker = party
	door = _plan(party.members[0].node)
	hero_at = door
	for i in range(1, party.members.size()):
		followers.append({m = party.members[i], spot = _plan(party.members[i].node)})


static func _plan(node: Node3D) -> Vector2:
	return Vector2(node.position.x, -node.position.z)


## Call every frame while the party walks.
func frame() -> void:
	var hero := _plan(walker.members[0].node)
	travelled += hero.distance_to(hero_at)
	hero_at = hero
	if travelled > CLEAR or not walker.peeled:
		return
	for f in followers:
		var p := _plan(f.m.node)
		var from_door: float = f.spot.distance_to(door)
		if f.m.leg.is_empty():
			stepped_in = maxf(stepped_in, from_door - p.distance_to(door))
		if p.distance_to(f.spot) > 0.15:
			if travelled < from_door:
				early += 1
			closest = minf(closest, p.distance_to(hero))


func passed() -> bool:
	return stepped_in <= 0.1 and early == 0 and closest >= Rules.FILE_GAP * 0.7


func report() -> String:
	if not walker.peeled:
		return "the way out is another lane, so the followers walk the lanes to it"
	return "followers stepped %.2f m toward the door, moved early on %d frames, kept %.2f m behind the hero" % [stepped_in, early, closest]
