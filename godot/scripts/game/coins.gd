class_name Coins
extends RefCounted
## Coin checks (design/03 Classes & combat.md -> Coin checks): flip coins, heads count toward success.


static func flip(rng: RandomNumberGenerator, n: int) -> Array[bool]:
	var out: Array[bool] = []
	for k in maxi(n, 0):
		out.append(rng.randf() < 0.5)
	return out


static func heads(coins: Array[bool]) -> int:
	return coins.count(true)


static func text(coins: Array[bool]) -> String:
	var s := PackedStringArray()
	for c in coins:
		s.append("H" if c else "T")
	return " ".join(s)
