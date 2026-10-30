class_name Deck
extends RefCounted
## The map-card deck, hand and discard pile (design/05 Cards & progression.md -> Deck and hand).

var draw_pile: Array[String] = []
var hand: Array[String] = []
var discard: Array[String] = []
var rng: RandomNumberGenerator


func _init(cards: Dictionary, random: RandomNumberGenerator) -> void:
	rng = random
	for terrain in cards:
		for k in cards[terrain]:
			draw_pile.append(terrain)
	_shuffle(draw_pile)


## Draws up to n cards. If the deck runs out, the rest of the draw is lost (DOCS: Empty deck).
func draw(n: int) -> Array[String]:
	var got: Array[String] = []
	for k in n:
		if draw_pile.is_empty():
			break
		got.append(draw_pile.pop_back())
	hand.append_array(got)
	return got


## Resting: discard down to the hand limit, then reshuffle the discard pile into the deck.
## PLACEHOLDER: the newest cards are discarded automatically (the player should pick).
func rest() -> int:
	var dropped := 0
	while hand.size() > Rules.HAND_LIMIT:
		discard.append(hand.pop_back())
		dropped += 1
	draw_pile.append_array(discard)
	discard.clear()
	_shuffle(draw_pile)
	return dropped


func _shuffle(a: Array) -> void:
	for i in range(a.size() - 1, 0, -1):
		var j := rng.randi_range(0, i)
		var t = a[i]
		a[i] = a[j]
		a[j] = t
