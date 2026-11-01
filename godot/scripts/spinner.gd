class_name Spinner
extends Node3D
## Turns about its own axis: the Great Windmill's sails, the crows over the haunted farms.

var axis := Vector3.UP
var speed := 0.6      # radians a second


func _process(delta: float) -> void:
	rotate_object_local(axis, speed * delta)
