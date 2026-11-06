class_name SaveUpgrade
extends RefCounted
## Brings an older save up to SaveGame.VERSION, one step at a time (design/06 -> Saving). Add a step here whenever the save's
## layout changes: `_from_1` turns a version 1 save into version 2, and so on. The file is rewritten at the new version on
## the next save. Nothing to upgrade yet.

static func upgrade(d: Dictionary) -> Dictionary:
	while int(d.version) < SaveGame.VERSION:
		d = Callable(SaveUpgrade, "_from_%d" % int(d.version)).call(d)
	return d
