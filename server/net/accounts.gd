extends RefCounted
## Sign-in, account creation and the character lobby. Passwords are stored as PBKDF2-HMAC-SHA256 with a
## random per-account salt; hashing runs on a worker thread so logins never stall the simulation. Attempts
## are rate-limited per address. Storage goes through the Repository.

const ITERATIONS := 60000

var realm: Realm
var hashing: Dictionary = {}    ## peer id -> pending job
var attempts: Dictionary = {}   ## address -> realm time of the last attempt
var offline_admin := false      ## the in-game offline realm makes its local account an admin

func _init(owner: Realm) -> void:
	realm = owner

## PBKDF2-HMAC-SHA256, one 32-byte block. The XOR runs on four 64-bit words instead of 32 bytes.
static func derive(password: String, salt: PackedByteArray, iterations: int = ITERATIONS) -> PackedByteArray:
	var crypto := Crypto.new()
	var key := password.to_utf8_buffer()
	var block := salt.duplicate()
	block.append_array(PackedByteArray([0, 0, 0, 1]))
	var u := crypto.hmac_digest(HashingContext.HASH_SHA256, key, block)
	var r0 := u.decode_s64(0)
	var r1 := u.decode_s64(8)
	var r2 := u.decode_s64(16)
	var r3 := u.decode_s64(24)
	for i in range(1, iterations):
		u = crypto.hmac_digest(HashingContext.HASH_SHA256, key, u)
		r0 ^= u.decode_s64(0)
		r1 ^= u.decode_s64(8)
		r2 ^= u.decode_s64(16)
		r3 ^= u.decode_s64(24)
	var result := PackedByteArray()
	result.resize(32)
	result.encode_s64(0, r0)
	result.encode_s64(8, r1)
	result.encode_s64(16, r2)
	result.encode_s64(24, r3)
	return result

func _fail(id: int, message: String) -> void:
	realm.gateway.send(id, Protocol.S_AUTH, {'ok': false, 'message': message, 'roster': []})

func authenticate(id: int, username: String, password: String, creating: bool) -> void:
	if hashing.has(id):
		return
	var now: float = realm.now
	var address: String = realm.gateway.address_of(id)
	if now - float(attempts.get(address, -10.0)) < 1.5:
		_fail(id, 'Please wait a moment before trying again.')
		return
	attempts[address] = now
	username = username.strip_edges().to_lower()
	if username.length() < 3 or username.length() > 24 or password.length() < 8 or password.length() > 128:
		_fail(id, 'Username: 3-24 letters or numbers. Password: 8-128 characters.')
		return
	for character in username:
		if not character in 'abcdefghijklmnopqrstuvwxyz0123456789_':
			_fail(id, 'Use letters, numbers or underscores for your username.')
			return
	var record := realm.repo.find_account(username)
	if creating and not record.is_empty():
		_fail(id, 'That username is taken. Try signing in.')
		return
	if not creating and record.is_empty():
		_fail(id, 'Username or password is incorrect.')
		return
	var salt: PackedByteArray = Crypto.new().generate_random_bytes(16) if creating else str(record.salt).hex_decode()
	var iterations := ITERATIONS if creating else int(record.iterations)
	var worker := Thread.new()
	if worker.start(derive.bind(password, salt, iterations)) != OK:
		_fail(id, 'The realm is busy. Please try again.')
		return
	hashing[id] = {'worker': worker, 'username': username, 'record': record, 'salt': salt, 'creating': creating}

func poll() -> void:
	for id in hashing.keys():
		var job: Dictionary = hashing[id]
		if job.worker.is_alive():
			continue
		var digest: PackedByteArray = job.worker.wait_to_finish()
		hashing.erase(id)
		if realm.gateway.has_peer(id):
			_finish(id, job, digest)

func shutdown() -> void:
	for job in hashing.values():
		job.worker.wait_to_finish()
	hashing.clear()

func _finish(id: int, job: Dictionary, digest: PackedByteArray) -> void:
	var account_id := 0
	if job.creating:
		account_id = realm.repo.create_account(job.username, job.salt.hex_encode(), digest.hex_encode(), ITERATIONS, offline_admin)
		if account_id == 0:
			_fail(id, 'That username is taken. Try signing in.')
			return
	else:
		if not Crypto.new().constant_time_compare(digest, str(job.record.digest).hex_decode()):
			_fail(id, 'Username or password is incorrect.')
			return
		account_id = int(job.record.id)
	for s in realm.gateway.sessions.values():
		if s.account_id == account_id:
			_fail(id, 'This account is already connected.')
			return
	var s: Dictionary = realm.gateway.session(id)
	s.stage = 'lobby'
	s.account_id = account_id
	s.username = job.username
	realm.repo.touch_login(account_id)
	realm.gateway.send(id, Protocol.S_CATALOG, realm.content.client_catalog())
	send_roster(id, 'Account created. Create your first character.' if job.creating else 'Choose your character.')

func send_roster(id: int, message: String) -> void:
	var s: Dictionary = realm.gateway.session(id)
	var roster: Array = []
	for c in realm.repo.roster(s.account_id):
		roster.append({'id': int(c.id), 'name': c.name, 'sex': c.sex, 'race': c.race_id, 'class': c.class_id,
			'skin': int(c.skin), 'level': int(c.level), 'zone': c.region if str(c.region) != '' else 'Veyr'})
	realm.gateway.send(id, Protocol.S_AUTH, {'ok': true, 'message': message, 'roster': roster})

func create_character(id: int, data: Dictionary) -> void:
	var s: Dictionary = realm.gateway.session(id)
	var content: Content = realm.content
	var identity := {'name': Rules.safe_name(str(data.get('name', ''))), 'sex': str(data.get('sex', '')),
		'race': str(data.get('race', '')), 'class': str(data.get('class', '')), 'skin': int(data.get('skin', -1))}
	var race: Dictionary = content.races.get(identity.race, {})
	var cls: Dictionary = content.classes.get(identity['class'], {})
	if identity.name.length() < 3 or not identity.sex in ['male', 'female'] or race.is_empty() or not race.playable \
			or cls.is_empty() or not cls.playable or identity.skin < 0 or identity.skin >= race.skins.size():
		send_roster(id, 'Choose a name (3+ letters), a sex, a race, a skin tone and a class.')
		return
	if realm.repo.name_taken(identity.name):
		send_roster(id, 'That name is already taken on this realm.')
		return
	if realm.repo.roster(s.account_id).size() >= Repository.SLOTS:
		send_roster(id, 'All three character slots are taken.')
		return
	var zone: Zone = realm.zones[Realm.START_ZONE]
	var start := {'zone': zone.id, 'pos': zone.spawn_point(), 'yaw': zone.spawn_yaw(), 'region': zone.region_at(zone.spawn_point())}
	var items: Array = [['health_tonic', 2]]
	if cls.resource == 'mana':
		items.append(['mana_tonic', 1])
	if realm.repo.create_character(s.account_id, identity, start, items) > 0:
		send_roster(id, '%s has been created.' % identity.name)
	else:
		send_roster(id, 'The realm could not save your character.')

func delete_character(id: int, character_id: int) -> void:
	var s: Dictionary = realm.gateway.session(id)
	for c in realm.repo.roster(s.account_id):
		if int(c.id) == character_id:
			realm.repo.delete_character(s.account_id, character_id)
			send_roster(id, '%s has been deleted.' % c.name)
			return
