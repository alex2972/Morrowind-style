extends Node
## The realm's network edge: the ENet server, one session per connection (connected -> lobby -> world),
## protocol-version check, per-connection rate limiting, and routing of client messages to the account
## service (lobby) or to the game systems' handlers (world). Nothing here knows game rules.

const RATE := 20.0       ## messages per second a client may send, sustained
const BURST := 40.0

var realm: Realm
var api: SceneMultiplayer
var peer: ENetMultiplayerPeer
var link: Node
var sessions: Dictionary = {}    ## peer id -> {stage, account_id, username, tokens, t}

func start(owner: Realm, port: int, bind_ip: String, max_players: int) -> Error:
	realm = owner
	api = SceneMultiplayer.new()
	api.server_relay = false
	get_tree().set_multiplayer(api, get_path())
	link = Node.new()
	link.name = 'Link'
	link.set_script(load('res://shared/link.gd'))
	add_child(link)
	peer = ENetMultiplayerPeer.new()
	peer.set_bind_ip(bind_ip)
	var err := peer.create_server(port, max_players)
	if err != OK:
		return err
	api.multiplayer_peer = peer
	api.peer_connected.connect(func(id: int) -> void:
		sessions[id] = {'stage': 'connected', 'account_id': 0, 'username': '', 'tokens': BURST, 't': realm.now})
	api.peer_disconnected.connect(_on_disconnected)
	return OK

func stop() -> void:
	if peer:
		peer.close()
		peer = null

func has_peer(id: int) -> bool:
	return sessions.has(id)

func address_of(id: int) -> String:
	if peer == null or peer.get_peer(id) == null:
		return ''
	return peer.get_peer(id).get_remote_address()

func session(id: int) -> Dictionary:
	return sessions.get(id, {})

func send(id: int, type: String, data: Dictionary) -> void:
	if sessions.has(id):
		link.s_msg.rpc_id(id, type, data)

func send_state(id: int, me: Dictionary, actors: Array) -> void:
	if sessions.has(id):
		var raw := var_to_bytes([me, actors])
		link.s_state.rpc_id(id, raw.compress(FileAccess.COMPRESSION_ZSTD), raw.size())

func _on_disconnected(id: int) -> void:
	sessions.erase(id)   # first, so nothing tries to message the departed peer while it is cleaned up
	if realm.players.has(id):
		realm.leave_world(id)

func _allow(s: Dictionary) -> bool:
	## Token bucket: floods are dropped, not queued.
	s.tokens = minf(BURST, s.tokens + (realm.now - s.t) * RATE)
	s.t = realm.now
	if s.tokens < 1.0:
		return false
	s.tokens -= 1.0
	return true

# ---------------------------------------------------------------- from link.gd

func on_hello(id: int, version: int, username: String, password: String, creating: bool) -> void:
	var s: Dictionary = sessions.get(id, {})
	if s.is_empty() or s.stage != 'connected':
		return
	if version != Protocol.VERSION:
		send(id, Protocol.S_AUTH, {'ok': false, 'roster': [],
			'message': 'Your game (protocol %d) does not match this realm (protocol %d). Please update.' % [version, Protocol.VERSION]})
		return
	realm.accounts.authenticate(id, username, password, creating)

func on_msg(id: int, type: String, data: Dictionary) -> void:
	var s: Dictionary = sessions.get(id, {})
	if s.is_empty() or not _allow(s):
		return
	match s.stage:
		'lobby':
			match type:
				Protocol.C_CREATE_CHARACTER:
					realm.accounts.create_character(id, data)
				Protocol.C_DELETE_CHARACTER:
					realm.accounts.delete_character(id, int(data.get('id', 0)))
				Protocol.C_ENTER:
					if realm.enter_world(id, s.account_id, int(data.get('id', 0))):
						s.stage = 'world'
					else:
						realm.accounts.send_roster(id, 'That character could not enter the world.')
		'world':
			if type == Protocol.C_LEAVE:
				realm.leave_world(id)
				s.stage = 'lobby'
				realm.accounts.send_roster(id, 'Choose your character.')
				return
			var handler: Callable = realm.handlers.get(type, Callable())
			if handler.is_valid() and realm.players.has(id):
				handler.call(realm.players[id], data)

func on_move(id: int, pos: Vector3, yaw: float, clip: String, rate: float) -> void:
	if realm.players.has(id):
		realm.movement.on_move(realm.players[id], pos, yaw, clip, rate)
