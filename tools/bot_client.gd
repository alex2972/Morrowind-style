extends Node
## A headless game client that speaks the protocol without any UI or world: connects, signs in, creates and
## enters a character, moves, chats and answers invites. Used by tools/verify_online.gd for multiplayer
## checks, and a starting point for load tests (spawn many of these against a dedicated realm).

var link: Node
var api: SceneMultiplayer
var peer: ENetMultiplayerPeer
var connected := false
var roster: Array = []
var auth_ok := false
var auth_message := ''
var eid := ''
var pos := Vector3.ZERO
var sheet: Dictionary = {}
var me: Dictionary = {}
var party: Dictionary = {}
var seen: Dictionary = {}       ## eid -> info
var events: Array = []          ## every S_EVENT received

func start(host: String, port: int) -> void:
	api = SceneMultiplayer.new()
	get_tree().set_multiplayer(api, get_path())
	link = Node.new()
	link.name = 'Link'
	link.set_script(load('res://shared/link.gd'))
	add_child(link)
	peer = ENetMultiplayerPeer.new()
	peer.create_client(host, port)
	api.multiplayer_peer = peer
	api.connected_to_server.connect(func() -> void: connected = true)

func stop() -> void:
	if peer:
		peer.close()

func hello(username: String, password: String, creating: bool) -> void:
	link.c_hello.rpc_id(1, Protocol.VERSION, username, password, creating)

func send(type: String, data: Dictionary = {}) -> void:
	link.c_msg.rpc_id(1, type, data)

func move(to: Vector3) -> void:
	pos = to
	link.c_move.rpc_id(1, to, 0.0, 'idle', 1.0)

func had_event(type: String) -> Dictionary:
	for e in events:
		if e.type == type:
			return e
	return {}

func on_msg(type: String, data: Dictionary) -> void:
	match type:
		Protocol.S_AUTH:
			auth_ok = data.ok
			auth_message = data.message
			roster = data.get('roster', [])
		Protocol.S_ENTER:
			eid = data.eid
			pos = data.pos
		Protocol.S_SHEET:
			sheet = data
		Protocol.S_APPEAR:
			seen[data.id] = data.info
		Protocol.S_VANISH:
			seen.erase(data.id)
		Protocol.S_EVENT:
			events.append(data)
		Protocol.S_PARTY:
			party = data
		Protocol.S_TELEPORT:
			pos = data.pos

func on_state(state: Dictionary, _actors: Array) -> void:
	me = state
