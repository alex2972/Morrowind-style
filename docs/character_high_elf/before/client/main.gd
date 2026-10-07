extends Node
## Game client boot (scenes/main.tscn): loads the world, shows the front end (login, lobby, creation) and
## hands over to the session once a character enters the world. "Play offline" starts a private realm in
## this process (bound to 127.0.0.1) and connects to it through the normal network code.
## `-- --server` switches to the dedicated realm scene instead (server/server.tscn, no art).

const WORLD_SCENE := 'res://scenes/world/veyr.tscn'
const OFFLINE_CFG := 'user://offline_account.cfg'
const OFFLINE_DIR := 'user://offline'

var world: Node3D
var realm: Realm
var session: Node
var front: CanvasLayer
var preview_camera: Camera3D
var preview_model: Node3D
var preview_key := ''
var client_cfg := ConfigFile.new()

func _ready() -> void:
	if OS.has_feature('dedicated_server') or '--server' in OS.get_cmdline_user_args() or '--server' in OS.get_cmdline_args():
		get_tree().change_scene_to_file.call_deferred('res://server/server.tscn')
		return
	name = 'Main'
	Catalog.preload_bodies()
	world = load(WORLD_SCENE).instantiate()
	world.name = 'World'
	add_child(world)
	client_cfg.load('res://config/client.cfg')
	session = Node.new()
	session.name = 'Client'
	session.set_script(load('res://client/net/session.gd'))
	add_child(session)
	session.setup(self)
	session.roster_received.connect(_on_roster)
	session.entered_world.connect(_on_entered)
	session.left_world.connect(_on_left)
	session.disconnected.connect(_on_disconnected)
	preview_camera = Camera3D.new()
	preview_camera.far = 1600.0
	preview_camera.cull_mask = 0xFFFFF & ~8   # not the frozen player's first-person sword and torch (layer 8)
	world.add_child(preview_camera)
	front = CanvasLayer.new()
	front.set_script(load('res://client/ui/front_end.gd'))
	add_child(front)
	_front_end_mode(true)
	front.setup(self)

func default_address() -> String:
	return '%s:%d' % [client_cfg.get_value('client', 'address', '127.0.0.1'), int(client_cfg.get_value('client', 'port', Protocol.PORT))]

# ---------------------------------------------------------------- front end <-> world

func _front_end_mode(on: bool) -> void:
	var p: CharacterBody3D = world.player
	p.frozen = on
	if on:
		if p.paused:
			p.set_menu(false)
		p.velocity = Vector3.ZERO
		if p.body:
			p.body.visible = false
		world.hud.visible = false
		world.hud.process_mode = Node.PROCESS_MODE_DISABLED
		preview_camera.global_transform = _preview_camera_transform()
		preview_camera.make_current()
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		front.visible = true
	else:
		show_preview({})
		front.visible = false
		world.hud.visible = true
		world.hud.process_mode = Node.PROCESS_MODE_INHERIT
		p.camera.make_current()
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _preview_camera_transform() -> Transform3D:
	var spot := Catalog.PREVIEW_SPOT
	var t := Transform3D(Basis(), spot + Vector3(0.9, 1.35, -3.3))
	return t.looking_at(spot + Vector3(-0.35, 1.0, 0), Vector3.UP)

func show_preview(identity: Dictionary) -> void:
	## The character shown in the lobby and creation screens (same placeholder tint/scale as in the game).
	var key := '' if identity.is_empty() else '%s/%s/%d' % [identity.get('sex'), identity.get('race'), int(identity.get('skin', 0))]
	if key == preview_key:
		return
	preview_key = key
	if preview_model:
		preview_model.queue_free()
		preview_model = null
	if key == '':
		return
	preview_model = Catalog.body_scene(str(identity.sex)).instantiate()
	world.add_child(preview_model)
	preview_model.global_position = Catalog.PREVIEW_SPOT
	preview_model.rotation.y = PI + 0.35
	preview_model.scale = Vector3.ONE * ActorView.BODY_SCALE * Catalog.race_scale(str(identity.race))
	Catalog.apply_appearance(preview_model, str(identity.race), int(identity.skin))
	var anim := preview_model.find_child('AnimationPlayer', true, false) as AnimationPlayer
	if anim:
		anim.play('idle')

# ---------------------------------------------------------------- signing in

func sign_in(address: String, username: String, password: String, creating: bool) -> void:
	_stop_local_realm()
	var host := address.get_slice(':', 0) if address.contains(':') else address
	var port := int(address.get_slice(':', 1)) if address.contains(':') else Protocol.PORT
	session.connect_to(host if host != '' else '127.0.0.1', port)
	session.login(username, password, creating)

func start_offline(save_dir := OFFLINE_DIR) -> void:
	## A private realm inside the game, bound to this computer only, with a local admin account.
	_stop_local_realm()
	var port := Protocol.PORT + 1
	var err := FAILED
	for attempt in 10:
		realm = Realm.new()
		realm.name = 'Realm'
		add_child(realm)
		err = realm.start({'database': save_dir.path_join('veyr.db'), 'port': port + attempt, 'bind': '127.0.0.1',
			'max_players': 4, 'legacy_dir': save_dir, 'offline_admin': true})
		if err == OK:
			port += attempt
			break
		_stop_local_realm()
	if err != OK:
		front.set_status('Could not start the local realm (error %d).' % err)
		return
	var cfg := ConfigFile.new()
	cfg.load(OFFLINE_CFG)
	var password: String = cfg.get_value('offline', 'password', '')
	if password == '':
		password = Crypto.new().generate_random_bytes(18).hex_encode()
		cfg.set_value('offline', 'password', password)
		cfg.save(OFFLINE_CFG)
	var creating: bool = realm.repo.find_account('offline').is_empty()
	session.connect_to('127.0.0.1', port)
	session.login('offline', password, creating)

func _stop_local_realm() -> void:
	if realm:
		realm.stop()
		realm.queue_free()
		realm = null

func log_out_account() -> void:
	session.close()
	_stop_local_realm()
	front.show_login()

func logout() -> void:
	## Esc menu: back to character select.
	session.leave_world()

func _on_roster(ok: bool, message: String, roster: Array) -> void:
	if session.in_world:
		return
	if ok:
		front.show_lobby(roster, message)
	else:
		front.show_login(message)

func _on_entered() -> void:
	_front_end_mode(false)

func _on_left() -> void:
	_front_end_mode(true)
	front.set_status('Returning to character select...')

func _on_disconnected() -> void:
	_stop_local_realm()
	_front_end_mode(true)
	front.show_login(front.status.text)

func _exit_tree() -> void:
	if session:
		session.close()
	_stop_local_realm()
