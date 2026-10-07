class_name Realm
extends Node
## The authoritative game server. It owns the database, the content, the zones and every entity in them,
## and runs the simulation at a fixed tick. Clients only send intents (shared/protocol.gd); systems in
## server/sim/ validate and resolve them and the replication system tells clients what happened.
##
## Runs in the game process for offline play (bound to 127.0.0.1) or headless as a dedicated realm
## (server/server.tscn, run_server.bat). It never loads art: zones use baked collision only.

const Gateway = preload('res://server/net/gateway.gd')
const Accounts = preload('res://server/net/accounts.gd')
const Replication = preload('res://server/net/replication.gd')
const Movement = preload('res://server/sim/movement.gd')
const Combat = preload('res://server/sim/combat.gd')
const AI = preload('res://server/sim/ai.gd')
const Progression = preload('res://server/sim/progression.gd')
const Inventory = preload('res://server/sim/inventory.gd')
const Loot = preload('res://server/sim/loot.gd')
const Quests = preload('res://server/sim/quests.gd')
const Dialogue = preload('res://server/sim/dialogue.gd')
const Chat = preload('res://server/sim/chat.gd')
const Party = preload('res://server/sim/party.gd')

const SAVE_INTERVAL := 60.0
const START_ZONE := 'veyr'

var db: RealmDatabase
var repo: Repository
var content: Content
var gateway: Node
var accounts: RefCounted
var zones: Dictionary = {}       ## zone id -> Zone
var entities: Dictionary = {}    ## eid -> entity, every zone
var players: Dictionary = {}     ## peer id -> player entity
var handlers: Dictionary = {}    ## client message type -> Callable(player, data)
var systems: Array = []          ## tick order
var now := 0.0                   ## simulation clock, seconds
var port := 0
var tick_count := 0

# systems, by name, for direct calls between them
var movement: RefCounted
var combat: RefCounted
var ai: RefCounted
var progression: RefCounted
var inventory: RefCounted
var loot: RefCounted
var quests: RefCounted
var dialogue: RefCounted
var chat: RefCounted
var party: RefCounted
var replication: RefCounted

var _listeners: Dictionary = {}
var _accumulator := 0.0
var _save_t := 0.0
var _rng := RandomNumberGenerator.new()

## settings: database (path), port, bind, max_players, legacy_dir (old JSON saves to import once),
## offline_admin (accounts created on this realm are admins - the in-game offline realm)
func start(settings: Dictionary) -> Error:
	_rng.randomize()
	db = RealmDatabase.new()
	if not db.open(str(settings.get('database', 'user://realm/veyr.db'))):
		return ERR_CANT_OPEN
	repo = Repository.new(db)
	content = Content.new(db)
	content.seed_empty_tables()
	var problems := content.reload()
	if not problems.is_empty():
		push_error('Content problems:\n  ' + '\n  '.join(problems))
		return ERR_INVALID_DATA
	if settings.has('legacy_dir'):
		repo.import_legacy(str(settings.legacy_dir))
	var zone := Zone.new()
	add_child(zone)
	if not zone.setup(START_ZONE):
		return ERR_FILE_NOT_FOUND
	zones[zone.id] = zone
	movement = Movement.new(self)
	combat = Combat.new(self)
	ai = AI.new(self)
	progression = Progression.new(self)
	inventory = Inventory.new(self)
	loot = Loot.new(self)
	quests = Quests.new(self)
	dialogue = Dialogue.new(self)
	chat = Chat.new(self)
	party = Party.new(self)
	replication = Replication.new(self)
	systems = [movement, ai, combat, progression, inventory, loot, quests, dialogue, chat, party, replication]
	for s in systems:
		s.setup()
	accounts = Accounts.new(self)
	accounts.offline_admin = bool(settings.get('offline_admin', false))
	gateway = Gateway.new()
	gateway.name = 'Net'
	add_child(gateway)
	port = int(settings.get('port', Protocol.PORT))
	var err: Error = gateway.start(self, port, str(settings.get('bind', '*')),
		int(settings.get('max_players', 64)))
	if err != OK:
		return err
	print('Realm up: %s:%d, database %s, content %s' % [settings.get('bind', '*'), settings.get('port', Protocol.PORT),
		ProjectSettings.globalize_path(db.path), content.version])
	return OK

func stop() -> void:
	for p in players.values():
		save_player(p)
	players.clear()
	if accounts:
		accounts.shutdown()
	if gateway:
		gateway.stop()
	if db:
		db.close()
		db = null

func _exit_tree() -> void:
	stop()

func rng() -> RandomNumberGenerator:
	return _rng

# ---------------------------------------------------------------- events between systems

func on(event: String, listener: Callable) -> void:
	_listeners.get_or_add(event, []).append(listener)

func emit(event: String, data: Dictionary) -> void:
	for listener in _listeners.get(event, []):
		listener.call(data)

func handle(type: String, handler: Callable) -> void:
	handlers[type] = handler

# ---------------------------------------------------------------- sending

func send(p: Dictionary, type: String, data: Dictionary) -> void:
	gateway.send(p.peer, type, data)

func tell(p: Dictionary, text: String, channel := 'Game') -> void:
	send(p, Protocol.S_EVENT, {'type': 'chat', 'channel': channel, 'text': text})

func error(p: Dictionary, text: String) -> void:
	send(p, Protocol.S_EVENT, {'type': 'error', 'text': text})

func event_near(at: Dictionary, event: Dictionary) -> void:
	## Sends an event to every player who can see entity `at`.
	for p in zone_of(at).nearby(at.pos, Replication.VIEW_RADIUS, true):
		send(p, Protocol.S_EVENT, event)

func broadcast(event: Dictionary) -> void:
	for p in players.values():
		send(p, Protocol.S_EVENT, event)

# ---------------------------------------------------------------- entities

func zone_of(e: Dictionary) -> Zone:
	return zones[e.zone]

func add_entity(e: Dictionary, zone_id: String) -> void:
	entities[e.eid] = e
	zones[zone_id].add(e)

func remove_entity(e: Dictionary) -> void:
	entities.erase(e.eid)
	zone_of(e).remove(e)

func player_by_name(character_name: String) -> Dictionary:
	for p in players.values():
		if str(p.name).to_lower() == character_name.strip_edges().to_lower():
			return p
	return {}

# ---------------------------------------------------------------- characters entering and leaving

func enter_world(peer: int, account_id: int, character_id: int) -> bool:
	var data := repo.load_character(account_id, character_id)
	if data.is_empty() or players.has(peer):
		return false
	var row: Dictionary = data.row
	var zone_id := str(row.zone_id) if zones.has(str(row.zone_id)) else START_ZONE
	var p := {
		'eid': 'p%d' % peer, 'kind': 'player', 'peer': peer, 'account_id': account_id, 'id': int(row.id),
		'name': str(row.name), 'sex': str(row.sex), 'race': str(row.race_id), 'job': str(row.class_id), 'skin': int(row.skin),
		'level': clampi(int(row.level), 1, Rules.MAX_LEVEL), 'xp': int(row.xp), 'pos': Vector3.ZERO, 'yaw': float(row.yaw),
		'region': str(row.region), 'joined_at': now, 'sheet_dirty': true, 'save_due': false,
		'is_admin': repo.is_admin(account_id),
	}
	if row.x != null:
		p.pos = Vector3(row.x, row.y, row.z)
	else:
		p.pos = zones[zone_id].spawn_point()
	for s in systems:
		s.player_joined(p, data)
	players[peer] = p
	add_entity(p, zone_id)
	send(p, Protocol.S_ENTER, {'eid': p.eid, 'name': p.name, 'sex': p.sex, 'race': p.race, 'class': p.job, 'skin': p.skin,
		'pos': p.pos, 'yaw': p.yaw, 'zone': zone_id})
	chat.system_message('%s has entered Veyr.' % p.name)
	return true

func leave_world(peer: int) -> void:
	var p: Dictionary = players.get(peer, {})
	if p.is_empty():
		return
	save_player(p)
	for s in systems:
		s.player_left(p)
	players.erase(peer)
	remove_entity(p)
	chat.system_message('%s has left Veyr.' % p.name)

func save_player(p: Dictionary) -> bool:
	var state := {'id': p.id, 'level': p.level, 'xp': p.xp, 'zone': p.zone, 'pos': p.pos, 'yaw': p.yaw,
		'region': zone_of(p).region_at(p.pos), 'played': now - p.joined_at, 'gold': 0, 'pack': [], 'quests': {},
		'skills': {}, 'health': null, 'resource': null}
	p.joined_at = now
	for s in systems:
		s.write_save(p, state)
	p.save_due = false
	var ok := repo.save_character(state)
	if not ok:
		push_error('Could not save %s' % p.name)
	return ok

func sheet(p: Dictionary) -> Dictionary:
	var out := {}
	for s in systems:
		s.write_sheet(p, out)
	return out

# ---------------------------------------------------------------- admin

func reload_content() -> Array:
	var problems := content.reload()
	if not problems.is_empty():
		return problems
	ai.respawn_all()
	for p in players.values():
		send(p, Protocol.S_CATALOG, content.client_catalog())
		combat.refresh_stats(p)
		p.sheet_dirty = true
	return []

# ---------------------------------------------------------------- simulation

func _physics_process(delta: float) -> void:
	if gateway == null:
		return
	accounts.poll()
	_accumulator = minf(_accumulator + delta, 0.25)   # never spiral after a hitch
	var step := 1.0 / Protocol.TICK_RATE
	while _accumulator >= step:
		_accumulator -= step
		now += step
		tick_count += 1
		for s in systems:
			s.tick(step)
	_save_t += delta
	var periodic := _save_t > SAVE_INTERVAL
	if periodic:
		_save_t = 0.0
	for p in players.values():
		if p.save_due or periodic:
			save_player(p)
