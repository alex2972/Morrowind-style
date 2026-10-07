class_name RealmSystem
extends RefCounted
## Base for the realm's game systems (combat, AI, inventory, quests...). Each one owns a slice of the
## entity data and the messages for it, and talks to the others through the realm's events. Override only
## the hooks you need.

var realm: Realm

func _init(owner: Realm) -> void:
	realm = owner

## Called once after all systems exist: register message handlers and event listeners here.
func setup() -> void:
	pass

## Called every simulation tick (Protocol.TICK_RATE per second).
func tick(_dt: float) -> void:
	pass

## A character enters the world: add this system's fields to `p` from the loaded save `data`.
func player_joined(_p: Dictionary, _data: Dictionary) -> void:
	pass

## A character leaves the world (after its final save).
func player_left(_p: Dictionary) -> void:
	pass

## Write this system's fields into the save `state` (see Repository.save_character).
func write_save(_p: Dictionary, _state: Dictionary) -> void:
	pass

## Add this system's part of the character sheet sent to the owning client.
func write_sheet(_p: Dictionary, _sheet: Dictionary) -> void:
	pass
