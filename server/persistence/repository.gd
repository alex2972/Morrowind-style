class_name Repository
extends RefCounted
## All reads and writes of player data. Game systems never write SQL; they call these functions with plain
## dictionaries. Multi-row saves run in one transaction, so a crash can never leave half a character (or a
## duplicated item) behind. Swapping SQLite for MySQL later means rewriting this file and database.gd only.

const SLOTS := 3   ## characters per account

var db: RealmDatabase

func _init(database: RealmDatabase) -> void:
	db = database

# ---------------------------------------------------------------- accounts

func find_account(username: String) -> Dictionary:
	return db.row('SELECT * FROM accounts WHERE username = ?', [username])

func create_account(username: String, salt: String, digest: String, iterations: int, is_admin := false) -> int:
	if not db.exec('INSERT INTO accounts (username, salt, digest, iterations, is_admin) VALUES (?, ?, ?, ?, ?)',
			[username, salt, digest, iterations, 1 if is_admin else 0]):
		return 0
	return db.last_id()

func touch_login(account_id: int) -> void:
	db.exec('UPDATE accounts SET last_login = CURRENT_TIMESTAMP WHERE id = ?', [account_id])

func is_admin(account_id: int) -> bool:
	return int(db.value('SELECT is_admin FROM accounts WHERE id = ?', [account_id], 0)) == 1

# ---------------------------------------------------------------- characters

func roster(account_id: int) -> Array:
	return db.rows('SELECT id, name, sex, race_id, class_id, skin, level, region FROM characters WHERE account_id = ? ORDER BY id',
		[account_id])

func name_taken(name: String) -> bool:
	return db.value('SELECT id FROM characters WHERE name = ?', [name]) != null

## Returns the new character id, or 0. `start_items` are placed in the first pack slots.
func create_character(account_id: int, identity: Dictionary, start: Dictionary, start_items: Array) -> int:
	var made := {'id': 0}   # lambdas capture locals by value; write the result through a dictionary
	db.transaction(func() -> bool:
		if int(db.value('SELECT COUNT(*) FROM characters WHERE account_id = ?', [account_id], 0)) >= SLOTS:
			return false
		if not db.exec('INSERT INTO characters (account_id, name, sex, race_id, class_id, skin, zone_id, x, y, z, yaw, region) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
				[account_id, identity.name, identity.sex, identity.race, identity['class'], identity.skin, start.zone,
				start.pos.x, start.pos.y, start.pos.z, start.yaw, start.region]):
			return false
		made.id = db.last_id()
		for i in start_items.size():
			if not db.exec('INSERT INTO character_items (character_id, container, slot, item_id, count) VALUES (?, ?, ?, ?, ?)',
					[made.id, 'pack', i, start_items[i][0], start_items[i][1]]):
				return false
		return true)
	return made.id

func delete_character(account_id: int, character_id: int) -> bool:
	return db.exec('DELETE FROM characters WHERE id = ? AND account_id = ?', [character_id, account_id])

## Everything stored about one character, or {} if it is not this account's.
func load_character(account_id: int, character_id: int) -> Dictionary:
	var row := db.row('SELECT * FROM characters WHERE id = ? AND account_id = ?', [character_id, account_id])
	if row.is_empty():
		return {}
	var items: Array = db.rows('SELECT container, slot, item_id, count FROM character_items WHERE character_id = ?', [character_id])
	var quests := {}
	for q in db.rows('SELECT quest_id, state, progress FROM character_quests WHERE character_id = ?', [character_id]):
		var progress: Variant = JSON.parse_string(str(q.progress))
		quests[str(q.quest_id)] = {'state': str(q.state), 'progress': progress if progress is Array else []}
	var skills := {}
	for s in db.rows('SELECT skill_id, xp FROM character_skills WHERE character_id = ?', [character_id]):
		skills[str(s.skill_id)] = int(s.xp)
	db.exec('UPDATE characters SET last_login = CURRENT_TIMESTAMP WHERE id = ?', [character_id])
	return {'row': row, 'items': items, 'quests': quests, 'skills': skills}

## Saves a character's whole state in one transaction. `pack` is an Array of null or [item_id, count].
func save_character(s: Dictionary) -> bool:
	return db.transaction(func() -> bool:
		if not db.exec('UPDATE characters SET level = ?, xp = ?, gold = ?, health = ?, resource = ?, zone_id = ?, x = ?, y = ?, z = ?, yaw = ?, region = ?, played_seconds = played_seconds + ? WHERE id = ?',
				[s.level, s.xp, s.gold, s.health, s.resource, s.zone, s.pos.x, s.pos.y, s.pos.z, s.yaw, s.region, int(s.played), s.id]):
			return false
		if not db.exec("DELETE FROM character_items WHERE character_id = ? AND container = 'pack'", [s.id]):
			return false
		for i in s.pack.size():
			var slot: Variant = s.pack[i]
			if slot != null and not db.exec("INSERT INTO character_items (character_id, container, slot, item_id, count) VALUES (?, 'pack', ?, ?, ?)",
					[s.id, i, slot[0], slot[1]]):
				return false
		if not db.exec('DELETE FROM character_quests WHERE character_id = ?', [s.id]):
			return false
		for qid in s.quests:
			var q: Dictionary = s.quests[qid]
			if not db.exec('INSERT INTO character_quests (character_id, quest_id, state, progress) VALUES (?, ?, ?, ?)',
					[s.id, qid, q.state, JSON.stringify(q.progress)]):
				return false
		for sid in s.skills:
			if not db.exec('INSERT INTO character_skills (character_id, skill_id, xp) VALUES (?, ?, ?) ON CONFLICT (character_id, skill_id) DO UPDATE SET xp = excluded.xp',
					[s.id, sid, s.skills[sid]]):
				return false
		return true)

# ---------------------------------------------------------------- one-time import of the old JSON saves

func import_legacy(dir: String) -> int:
	## Brings accounts and characters from the first online version (JSON files) into an empty database.
	var accounts_dir := dir.path_join('accounts')
	if int(db.value('SELECT COUNT(*) FROM accounts', [], 0)) > 0 or not DirAccess.dir_exists_absolute(accounts_dir):
		return 0
	var imported := 0
	for file in DirAccess.get_files_at(accounts_dir):
		if not file.ends_with('.json'):
			continue
		var acc: Variant = JSON.parse_string(FileAccess.get_file_as_string(accounts_dir.path_join(file)))
		if not acc is Dictionary or not acc.has('username'):
			continue
		var account_id := create_account(str(acc.username), str(acc.salt), str(acc.digest), int(acc.get('iterations', 60000)), acc.username == 'offline')
		if account_id == 0:
			continue
		for c in acc.get('characters', []):
			var save: Variant = JSON.parse_string(FileAccess.get_file_as_string(dir.path_join('characters').path_join(str(c.token).sha256_text() + '.json'))) \
				if FileAccess.file_exists(dir.path_join('characters').path_join(str(c.token).sha256_text() + '.json')) else {}
			if not save is Dictionary:
				save = {}
			var pos: Array = save.get('pos', [-11.6, 2.6, 100.5])
			if not db.exec('INSERT INTO characters (account_id, name, sex, race_id, class_id, skin, level, xp, gold, health, resource, x, y, z, yaw, region) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
					[account_id, str(c.name), str(c.sex), str(c.race), str(c['class']), int(c.skin), int(save.get('level', 1)),
					int(save.get('xp', 0)), int(save.get('gold', 0)), save.get('health'), save.get('resource'),
					float(pos[0]), float(pos[1]), float(pos[2]), float(save.get('yaw', 0.0)), str(save.get('zone', ''))]):
				continue
			var cid := db.last_id()
			var slot := 0
			for item in save.get('inventory', {}):
				db.exec("INSERT INTO character_items (character_id, container, slot, item_id, count) VALUES (?, 'pack', ?, ?, ?)",
					[cid, slot, item, int(save.inventory[item])])
				slot += 1
			for qid in save.get('quests', {}):
				var q: Dictionary = save.quests[qid]
				db.exec('INSERT INTO character_quests (character_id, quest_id, state, progress) VALUES (?, ?, ?, ?)',
					[cid, qid, str(q.state), JSON.stringify([int(q.get('count', 0))])])
			imported += 1
	if imported > 0:
		print('Imported %d characters from the old JSON saves in %s' % [imported, dir])
	return imported
