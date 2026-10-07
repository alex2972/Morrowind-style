extends Node
## The client side of a game session: connects to a realm, signs in, runs the character lobby, and once in
## the world drives the local player (sends its movement, applies corrections), shows other players and NPCs
## as the realm reports them, and turns input into intents: targeting (Tab / click), the action bar (1-0),
## interaction (E), chat. It never decides an outcome and holds no game rules - only what the realm sent.

signal status_changed(text: String)
signal roster_received(ok: bool, message: String, roster: Array)
signal catalog_received
signal entered_world
signal left_world
signal disconnected

const TAB_RANGE := 45.0
const CLICK_RANGE := 80.0
const HOTBAR_KEYS := [KEY_1, KEY_2, KEY_3, KEY_4, KEY_5, KEY_6, KEY_7, KEY_8, KEY_9, KEY_0]

var main: Node
var link: Node
var api: SceneMultiplayer
var peer: ENetMultiplayerPeer
var connected := false
var in_world := false
var _pending_login: Array = []

var eid := ''
var identity: Dictionary = {}
var me: Dictionary = {}            ## own vitals, every state packet
var sheet: Dictionary = {}         ## level, xp, gold, pack, quests, abilities, stats (reliable, on change)
var party: Dictionary = {}         ## {leader, members: [{eid, name, level, class}]} or {}
var actors: Dictionary = {}        ## eid -> ActorView
var target := ''
var hotbar: Array = []             ## slot specs: 'attack', ability id, 'item:<id>'
var dialogue: Dictionary = {}
var actor_root: Node3D
var ui: Control                    ## client/ui/combat_ui.gd while in the world
var _move_t := 0.0

func setup(game: Node) -> void:
	main = game
	link = Node.new()
	link.name = 'Link'
	link.set_script(load('res://shared/link.gd'))
	add_child(link)

func world() -> Node3D:
	return main.world

func player() -> CharacterBody3D:
	return main.world.player

func hud() -> CanvasLayer:
	return main.world.hud

func send(type: String, data: Dictionary = {}) -> void:
	if connected:
		link.c_msg.rpc_id(1, type, data)

# ---------------------------------------------------------------- connection and lobby

func connect_to(address: String, port: int) -> void:
	close()
	api = SceneMultiplayer.new()
	get_tree().set_multiplayer(api, get_path())
	peer = ENetMultiplayerPeer.new()
	if peer.create_client(address, port) != OK:
		status_changed.emit('Could not reach %s:%d.' % [address, port])
		return
	api.multiplayer_peer = peer
	api.connected_to_server.connect(_on_connected)
	api.connection_failed.connect(_on_failed)
	api.server_disconnected.connect(_on_server_gone)
	status_changed.emit('Connecting to %s:%d...' % [address, port])

func close() -> void:
	if in_world:
		_leave_world_locally()
	if peer:
		peer.close()
	peer = null
	connected = false
	_pending_login.clear()

func login(username: String, password: String, creating: bool) -> void:
	if connected:
		link.c_hello.rpc_id(1, Protocol.VERSION, username, password, creating)
		status_changed.emit('Creating the account...' if creating else 'Signing in...')
	else:
		_pending_login = [username, password, creating]

func _on_connected() -> void:
	connected = true
	status_changed.emit('Connected.')
	if not _pending_login.is_empty():
		var l := _pending_login
		_pending_login = []
		login(l[0], l[1], l[2])

func _on_failed() -> void:
	status_changed.emit('Could not connect to the realm.')
	close()
	disconnected.emit()

func _on_server_gone() -> void:
	close()
	status_changed.emit('The connection to the realm was lost.')
	disconnected.emit()

func create_character(identity_data: Dictionary) -> void:
	send(Protocol.C_CREATE_CHARACTER, identity_data)

func delete_character(character_id: int) -> void:
	send(Protocol.C_DELETE_CHARACTER, {'id': character_id})

func enter(character_id: int) -> void:
	send(Protocol.C_ENTER, {'id': character_id})
	status_changed.emit('Entering the world...')

func leave_world() -> void:
	if in_world:
		send(Protocol.C_LEAVE)
		_leave_world_locally()

# ---------------------------------------------------------------- realm -> client

func on_msg(type: String, data: Dictionary) -> void:
	match type:
		Protocol.S_AUTH:
			roster_received.emit(bool(data.ok), str(data.message), data.get('roster', []))
		Protocol.S_CATALOG:
			Catalog.receive(data)
			catalog_received.emit()
		Protocol.S_ENTER:
			_enter_world(data)
		Protocol.S_SHEET:
			_on_sheet(data)
		Protocol.S_APPEAR:
			_appear(str(data.id), data.info)
		Protocol.S_VANISH:
			_vanish(str(data.id))
		Protocol.S_EVENT:
			_on_event(data)
		Protocol.S_DIALOGUE:
			dialogue = {} if data.get('close', false) else data
			if ui:
				ui.show_dialogue(dialogue)
		Protocol.S_TELEPORT:
			_teleport(data.pos, float(data.yaw))
		Protocol.S_PARTY:
			party = data
			for view in actors.values():
				view.refresh_plate()

func on_state(state: Dictionary, list: Array) -> void:
	if not in_world:
		return
	me = state
	var p := player()
	p.max_health = state.mhp
	p.health = state.hp
	p.max_mana = state.mres
	p.mana = state.res
	p.resource_kind = state.kind
	p.set_dead(state.dead)
	p.set_casting(not state.cast.is_empty())
	for a in list:
		var view: ActorView = actors.get(a[0])
		if view == null:
			continue   # its S_APPEAR is still on the way; the realm resends until we have it
		var s := {'p': a[1], 'y': a[2], 'c': a[3], 'r': a[4], 'hp': a[5], 'mhp': a[6], 'lv': a[7], 'dead': a[8],
			'cast': a[9], 't': a[10]}
		if a.size() > 11:
			s.merge({'res': a[11], 'mres': a[12], 'kind': a[13]})
		view.apply(s)

func _appear(id: String, info: Dictionary) -> void:
	if not in_world:
		return
	var view: ActorView = actors.get(id)
	if view == null:
		view = ActorView.new()
		actor_root.add_child(view)
		view.setup(id, info, self)
		view.set_selected(id == target)
		actors[id] = view
	else:
		view.info = info
		view.refresh_plate()
	view.set_marker(str(info.get('mark', '')))

func _vanish(id: String) -> void:
	if actors.has(id):
		actors[id].queue_free()
		actors.erase(id)
		if id == target:
			set_target('')

func _enter_world(state: Dictionary) -> void:
	eid = state.eid
	identity = state
	me = {}
	sheet = {}
	party = {}
	target = ''
	dialogue = {}
	hotbar = []
	actor_root = Node3D.new()
	actor_root.name = 'Actors'
	world().add_child(actor_root)
	var p := player()
	p.set_body_model(str(state.sex), false, str(state.race))
	Catalog.apply_appearance(p.body, str(state.race), int(state.skin))
	p.body.scale = Vector3.ONE * ActorView.BODY_SCALE * Catalog.race_stretch(str(state.race))
	p.character_name = str(state.name)
	p.collision_layer = 2
	_teleport(state.pos, float(state.yaw))
	ui = Control.new()
	ui.set_script(load('res://client/ui/combat_ui.gd'))
	hud().root.add_child(ui)
	ui.setup(self)
	hud().session = self
	in_world = true
	p.set_third_person(true)
	entered_world.emit()

func _leave_world_locally() -> void:
	in_world = false
	for a in actors.values():
		a.queue_free()
	actors.clear()
	if actor_root:
		actor_root.queue_free()
		actor_root = null
	if ui:
		ui.queue_free()
		ui = null
	hud().session = null
	player().set_dead(false)
	player().set_casting(false)
	left_world.emit()

func _teleport(pos: Vector3, yaw: float) -> void:
	var p := player()
	p.global_position = pos
	p.velocity = Vector3.ZERO
	p.rotation.y = yaw
	if p.body:
		p.body.rotation.y = p._body_home_yaw

func _on_sheet(data: Dictionary) -> void:
	var old_level := int(sheet.get('level', -1))
	sheet = data
	player().character_level = int(data.level)
	if hotbar.is_empty():
		hotbar = ['attack']
		for a in data.abilities:
			hotbar.append(a.id)
		while hotbar.size() < 8:
			hotbar.append('')
		hotbar.append('item:health_tonic')
		hotbar.append('item:mana_tonic' if data.stats.resource_kind == 'mana' else '')
	if ui and int(data.level) != old_level:
		ui.refresh_bar()

func ability(id: String) -> Dictionary:
	for a in sheet.get('abilities', []):
		if a.id == id:
			return a
	return {}

func item_count(item: String) -> int:
	var n := 0
	for s in sheet.get('pack', []):
		if s != null and s[0] == item:
			n += int(s[1])
	return n

func in_party(id: String) -> bool:
	for m in party.get('members', []):
		if m.eid == id:
			return true
	return false

func _on_event(e: Dictionary) -> void:
	if not in_world:
		return
	match str(e.type):
		'chat':
			var channel := str(e.channel)
			var sender := str(e.get('from', ''))
			if channel == 'Party':
				channel = 'Players'
				sender = '[Party] ' + sender if sender != '' else '[Party]'
			hud().add_chat_message(channel, str(e.text), sender)
		'error':
			if ui:
				ui.show_error(str(e.text))
		'hit', 'heal':
			_combat_text(e)
		'cast':
			if actors.has(str(e.id)):
				actors[str(e.id)].casting = str(e.ability)
				actors[str(e.id)].casting_name = str(e.get('name', ''))
		'cast_stop':
			if actors.has(str(e.id)):
				actors[str(e.id)].casting = ''
		'ability':
			_play(str(e.id), str(e.clip))
			CombatFx.spawn(world(), str(e.fx), _node_of(str(e.id)), _node_of(str(e.target)))
		'anim':
			_play(str(e.id), str(e.clip))
		'xp':
			hud().add_chat_message('Game', 'You gain %d experience.' % int(e.amount))
			if ui:
				ui.float_text(player(), '+%d XP' % int(e.amount), Color('#c58cff'))
		'level':
			CombatFx.spawn(world(), 'level', _node_of(str(e.id)), _node_of(str(e.id)))
			if str(e.id) == eid and ui:
				ui.show_banner('Level %d' % int(e.level))
		'party_invite':
			if ui:
				ui.show_invite(str(e.from))

func _node_of(id: String) -> Node3D:
	if id == eid:
		return player()
	return actors.get(id)

func _play(id: String, clip: String) -> void:
	if id == eid:
		player().play_action(clip)
	elif actors.has(id):
		actors[id].play_action(clip)

func _name_of(id: String) -> String:
	if id == eid:
		return 'you'
	if actors.has(id):
		return str(actors[id].info.name)
	return 'someone'

func _combat_text(e: Dictionary) -> void:
	var src := str(e.src)
	var dst := str(e.dst)
	if src != eid and dst != eid:
		return
	var amount := int(e.amount)
	var what := str(e.what)
	var label := 'Attack' if what == 'melee' else str(ability(what).get('name', Catalog.item(what).name))
	var heal: bool = e.type == 'heal'
	var crit: bool = e.crit
	var line := ''
	if src == eid:
		line = 'Your %s %s %s for %d%s' % [label, 'heals' if heal else ('crits' if crit else 'hits'), 'you' if dst == eid else _name_of(dst), amount, '!' if crit else '.']
	else:
		line = '%s %s you for %d.' % [_name_of(src).capitalize(), 'heals' if heal else 'hits', amount]
	hud().add_chat_message('Combat', line)
	if ui:
		var color := Color('#7dff6a') if heal else (Color('#ff4b3a') if dst == eid else Color('#fff3c4'))
		ui.float_text(_node_of(dst), ('+%d' if heal else '%d') % amount + ('!' if crit else ''), color, crit)
	if dst != eid and actors.has(dst) and not heal and randf() < 0.35 and actors[dst].casting == '':
		actors[dst].play_action('hit_chest')

# ---------------------------------------------------------------- targeting and intents

func set_target(id: String) -> void:
	if id == target:
		return
	if actors.has(target):
		actors[target].set_selected(false)
	target = id
	if actors.has(target):
		actors[target].set_selected(true)
	send(Protocol.C_TARGET, {'id': target})

func target_view() -> ActorView:
	return actors.get(target)

func cycle_target() -> void:
	## Tab: nearest living enemies in front of the camera, nearest first, cycling on repeat presses.
	var cam: Camera3D = player().camera
	var forward: Vector3 = -cam.global_basis.z
	var candidates: Array = []
	for view in actors.values():
		if view.category() != 'enemy' or view.dead:
			continue
		var to: Vector3 = view.global_position - player().global_position
		if to.length() > TAB_RANGE or forward.dot(to.normalized()) < 0.2:
			continue
		candidates.append([to.length(), view.eid])
	if candidates.is_empty():
		return
	candidates.sort()
	var ids: Array = candidates.map(func(c: Array) -> String: return c[1])
	set_target(ids[(ids.find(target) + 1) % ids.size()])

func click_target(screen_point: Vector2) -> bool:
	var cam: Camera3D = player().camera
	var from: Vector3 = cam.project_ray_origin(screen_point)
	var q := PhysicsRayQueryParameters3D.create(from, from + cam.project_ray_normal(screen_point) * CLICK_RANGE, ActorView.CLICK_LAYER)
	q.collide_with_areas = true
	q.collide_with_bodies = false
	var hit: Dictionary = cam.get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty() or not hit.collider.has_meta('actor_id'):
		return false
	set_target(str(hit.collider.get_meta('actor_id')))
	return true

func use_slot(i: int) -> void:
	if i >= hotbar.size() or hotbar[i] == '' or bool(me.get('dead', false)):
		return
	var spec: String = hotbar[i]
	if ui:
		ui.flash_slot(i)
	if spec == 'attack':
		send(Protocol.C_ATTACK, {'on': not bool(me.get('auto', false))})
	elif spec.begins_with('item:'):
		send(Protocol.C_USE_ITEM, {'item': spec.trim_prefix('item:')})
	else:
		var a := ability(spec)
		if a.is_empty() or not a.known:
			if ui:
				ui.show_error('You have not learned that yet.')
			return
		if not player().is_on_floor() and float(a.cast) > 0.0:
			if ui:
				ui.show_error('You cannot cast while jumping.')
			return
		send(Protocol.C_CAST, {'ability': spec, 'target': target})

func interact() -> void:
	var view := target_view()
	if view == null or view.dead or view.global_position.distance_to(player().global_position) > 5.0:
		view = null
		var best := 5.0
		for v in actors.values():   # nothing useful targeted: talk to the nearest friendly NPC
			var d: float = v.global_position.distance_to(player().global_position)
			if v.category() == 'npc' and d < best:
				best = d
				view = v
	if view == null:
		return
	set_target(view.eid)
	send(Protocol.C_INTERACT, {'id': view.eid})

func choose(option: String) -> void:
	if not dialogue.is_empty():
		send(Protocol.C_DIALOGUE, {'npc': dialogue.npc, 'choice': option})

func close_dialogue() -> void:
	dialogue = {}
	if ui:
		ui.show_dialogue({})

func release_spirit() -> void:
	send(Protocol.C_RELEASE)

func send_chat(text: String) -> void:
	send(Protocol.C_CHAT, {'text': text})

func request_unstuck() -> void:
	send(Protocol.C_UNSTUCK)

func abandon_quest(qid: String) -> void:
	send(Protocol.C_ABANDON_QUEST, {'quest': qid})

func use_item(item: String) -> void:
	send(Protocol.C_USE_ITEM, {'item': item})

func respond_invite(accept: bool) -> void:
	send(Protocol.C_PARTY_RESPOND, {'accept': accept})

func _unhandled_input(event: InputEvent) -> void:
	if not in_world or player().paused:
		return
	if event is InputEventKey and event.pressed and not event.echo:
		var slot := HOTBAR_KEYS.find(event.physical_keycode)
		if slot >= 0:
			use_slot(slot)
			get_viewport().set_input_as_handled()
		elif event.physical_keycode == KEY_TAB:
			cycle_target()
			get_viewport().set_input_as_handled()
		elif event.physical_keycode == KEY_E:
			interact()
			get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton and event.pressed and event.button_index in [MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT]:
		var point: Vector2 = get_viewport().get_visible_rect().size * 0.5 if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED else event.position
		var hit := click_target(point)
		if event.button_index == MOUSE_BUTTON_RIGHT and hit:
			interact()
		elif not hit and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED and event.button_index == MOUSE_BUTTON_LEFT:
			set_target('')

func _physics_process(delta: float) -> void:
	if not in_world or not connected:
		return
	_move_t -= delta
	if _move_t <= 0.0:
		_move_t = 1.0 / Protocol.MOVE_RATE
		var p := player()
		link.c_move.rpc_id(1, p.global_position, p.facing_yaw(), p.current_clip(), p.current_rate())
	if not dialogue.is_empty() and actors.has(str(dialogue.npc)) \
			and actors[dialogue.npc].global_position.distance_to(player().global_position) > 7.0:
		close_dialogue()
