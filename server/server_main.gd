extends Node
## Dedicated realm entry point (server/server.tscn). Loads no art: only the database, content and the
## zones' baked collision. Start it with run_server.bat, or:
##   Godot --headless --path . res://server/server.tscn

func _ready() -> void:
	var cfg := ConfigFile.new()
	cfg.load('res://config/server.cfg')
	var settings := {}
	for key in cfg.get_section_keys('realm') if cfg.has_section('realm') else []:
		settings[key] = cfg.get_value('realm', key)
	var realm := Realm.new()
	realm.name = 'Realm'
	add_child(realm)
	var err := realm.start(settings)
	if err != OK:
		push_error('The realm could not start (error %d).' % err)
		get_tree().quit(1)
