class_name Hero
extends RefCounted
## Who the player made in the creator. Game reads Hero.current when it starts; null means a direct start, with the placeholder hero. The Screens session owns this file's growth;
## Game only needs these fields.

static var current: Hero

var name := "[Hero name]"
var klass := "fighter"
var race := ""
var background := "soldier"
var appearance := {}
