extends SceneTree
## Refresh only the player prop after importing a regenerated player_body.glb.
## Run: Godot --headless --path . --script res://tools/refresh_character.gd [-- player_body_female]

const MaterialLibrary = preload("res://client/world/material_library.gd")
const AssetLibrary = preload("res://client/world/asset_library.gd")

func _init() -> void:
	call_deferred("_refresh")

func _refresh() -> void:
	var materials = MaterialLibrary.new()
	var assets = AssetLibrary.new(materials)
	var requested := OS.get_cmdline_user_args()
	for key in AssetLibrary.CHARACTERS:
		if not requested.is_empty() and not key in requested:
			continue
		if ResourceLoader.exists("res://assets/models/%s.glb" % key):
			assets.build_scene(key)
			print("Refreshed res://scenes/props/%s.tscn" % key)
	quit()
