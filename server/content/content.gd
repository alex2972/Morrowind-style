class_name Content
extends RefCounted
## Everything the game IS, loaded from the database's content tables into lookup dictionaries. Seeds empty
## tables from server/content/seed/content.json; reload() re-reads the tables at runtime (the `/reload` admin
## command) and keeps the previous content if the new rows don't validate. Clients only ever receive
## client_catalog(): names, icons and descriptions - never drop rates, NPC stats or quest logic.

const SEED := 'res://server/content/seed/content.json'
const JSON_COLUMNS := ['skins', 'effects', 'use_effect']

var db: RealmDatabase
var races: Dictionary = {}
var classes: Dictionary = {}       ## + 'abilities': [ability ids in bar order]
var abilities: Dictionary = {}     ## 'effects' parsed
var items: Dictionary = {}         ## 'use_effect' parsed
var templates: Dictionary = {}     ## npc templates + 'loot', 'sells', 'buys'
var spawns: Array = []
var paths: Dictionary = {}         ## routes NPCs walk + 'points': [{x, z, wait, yaw, anim}] in order
var quests: Dictionary = {}        ## + 'objectives', 'start_items' {item: n}, 'reward_items' {item: n}
var quest_order: Array = []
var skills: Dictionary = {}
var version := ''

func _init(database: RealmDatabase) -> void:
	db = database

# ---------------------------------------------------------------- seeding

func seed_empty_tables() -> void:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(SEED))
	if not parsed is Dictionary:
		push_error('Content seed missing or invalid: ' + SEED)
		return
	for table in parsed.order:
		if int(db.value('SELECT COUNT(*) FROM %s' % table, [], 0)) > 0:
			continue
		var rows: Array = parsed.tables[table]
		var ok := db.transaction(func() -> bool:
			for r in rows:
				var cols: Array = r.keys()
				var values: Array = []
				for c in cols:
					values.append(JSON.stringify(r[c]) if r[c] is Array or r[c] is Dictionary else r[c])
				if not db.exec('INSERT INTO %s (%s) VALUES (%s)' % [table, ', '.join(cols), ', '.join(cols.map(func(_c: String) -> String: return '?'))], values):
					return false
			return true)
		print('Seeded content table %s (%d rows)%s' % [table, rows.size(), '' if ok else ' - FAILED'])

# ---------------------------------------------------------------- loading

func _rows(table: String, order := 'rowid') -> Array:
	var out := db.rows('SELECT * FROM %s ORDER BY %s' % [table, order])
	for r in out:
		for c in JSON_COLUMNS:
			if r.has(c):
				r[c] = JSON.parse_string(str(r[c])) if str(r[c]) != '' else null
	return out

static func _index(rows: Array) -> Dictionary:
	var out := {}
	for r in rows:
		out[str(r.id)] = r
	return out

## Loads every content table. Returns a list of problems; on any problem nothing is replaced.
func reload() -> Array:
	var next := {
		'races': _index(_rows('races', 'sort, id')),
		'classes': _index(_rows('classes', 'sort, id')),
		'abilities': _index(_rows('abilities', 'level, id')),
		'items': _index(_rows('items', 'id')),
		'templates': _index(_rows('npc_templates', 'id')),
		'spawns': _rows('spawns', 'id'),
		'paths': _index(_rows('paths', 'id')),
		'quests': _index(_rows('quests', 'sort, id')),
		'skills': _index(_rows('skills', 'sort, id')),
	}
	for r in next.races.values():
		r.playable = bool(r.playable)
		if not r.skins is Array or r.skins.is_empty():
			r.skins = ['ffffff']
	for c in next.classes.values():
		c.playable = bool(c.playable)
		c.abilities = []
	for row in _rows('class_abilities', 'class_id, sort'):
		if next.classes.has(row.class_id):
			next.classes[row.class_id].abilities.append(str(row.ability_id))
	for a in next.abilities.values():
		if not a.effects is Array:
			a.effects = []
	for it in next.items.values():
		it.quest_item = bool(it.quest_item)
		if not it.use_effect is Dictionary:
			it.use_effect = {}
	for t in next.templates.values():
		t.hostile = bool(t.hostile)
		t.loot = []
		t.sells = []
		t.buys = []
	for row in _rows('npc_loot', 'template_id'):
		if next.templates.has(row.template_id):
			next.templates[row.template_id].loot.append(row)
	for row in _rows('npc_vendor', 'template_id, mode, item_id'):
		if next.templates.has(row.template_id):
			next.templates[row.template_id]['sells' if row.mode == 'sell' else 'buys'].append(str(row.item_id))
	for path in next.paths.values():
		path.points = []
	for row in _rows('path_points', 'path_id, idx'):
		if next.paths.has(row.path_id):
			next.paths[row.path_id].points.append(row)
	for q in next.quests.values():
		q.objectives = []
		q.start_items = {}
		q.reward_items = {}
		q.requires_id = str(q.requires_id) if q.requires_id != null else ''
	for row in _rows('quest_objectives', 'quest_id, idx'):
		if next.quests.has(row.quest_id):
			next.quests[row.quest_id].objectives.append(row)
	for row in _rows('quest_items', 'quest_id'):
		if next.quests.has(row.quest_id):
			next.quests[row.quest_id]['start_items' if row.kind == 'start' else 'reward_items'][str(row.item_id)] = int(row.count)
	var problems := _validate(next)
	if not problems.is_empty():
		return problems
	races = next.races
	classes = next.classes
	abilities = next.abilities
	items = next.items
	templates = next.templates
	spawns = next.spawns
	paths = next.paths
	quests = next.quests
	quest_order = quests.keys()
	skills = next.skills
	version = str(JSON.stringify(client_catalog(true)).hash())
	return []

func _validate(c: Dictionary) -> Array:
	var p: Array = []
	for cls in c.classes.values():
		for aid in cls.abilities:
			if not c.abilities.has(aid):
				p.append('class %s uses unknown ability %s' % [cls.id, aid])
	for s in c.spawns:
		if not c.templates.has(s.template_id):
			p.append('spawn %s uses unknown npc template %s' % [s.id, s.template_id])
		match str(s.movement):
			'wander':
				if float(s.wander_radius) <= 0.0:
					p.append('spawn %s wanders but has no wander_radius' % s.id)
			'path':
				if not c.paths.has(str(s.path_id)):
					p.append('spawn %s walks unknown path %s' % [s.id, s.path_id])
				elif c.paths[str(s.path_id)].points.size() < 2:
					p.append('path %s needs at least two points' % s.path_id)
	for t in c.templates.values():
		if not c.races.has(t.race_id):
			p.append('npc %s has unknown race %s' % [t.id, t.race_id])
	for q in c.quests.values():
		for k in ['giver_id', 'turn_in_id']:
			if not c.templates.has(q[k]):
				p.append('quest %s: unknown %s %s' % [q.id, k, q[k]])
		if q.requires_id != '' and not c.quests.has(q.requires_id):
			p.append('quest %s requires unknown quest %s' % [q.id, q.requires_id])
		if q.objectives.is_empty():
			p.append('quest %s has no objectives' % q.id)
		for o in q.objectives:
			var table: Dictionary = c.templates if o.type in ['kill', 'talk'] else c.items
			if not table.has(o.target):
				p.append('quest %s objective %d targets unknown %s' % [q.id, o.idx, o.target])
		for item in q.start_items.keys() + q.reward_items.keys():
			if not c.items.has(item):
				p.append('quest %s gives unknown item %s' % [q.id, item])
	return p

# ---------------------------------------------------------------- what clients may see

func client_catalog(for_hash := false) -> Dictionary:
	var out_races: Array = []
	for r in races.values():
		out_races.append({'id': r.id, 'name': r.name, 'description': r.description, 'scale': r.scale,
			'skins': r.skins, 'playable': r.playable})
	var out_classes: Array = []
	for c in classes.values():
		var preview: Array = []
		for aid in c.abilities:
			preview.append({'name': abilities[aid].name, 'level': int(abilities[aid].level), 'icon': abilities[aid].icon})
		out_classes.append({'id': c.id, 'name': c.name, 'description': c.description, 'resource': c.resource,
			'playable': c.playable, 'abilities': preview})
	var out_items := {}
	for it in items.values():
		out_items[it.id] = {'name': it.name, 'description': it.description, 'icon': it.icon, 'stack': int(it.stack),
			'usable': not it.use_effect.is_empty(), 'quest_item': it.quest_item}
	var out_skills: Array = []
	for s in skills.values():
		out_skills.append({'id': s.id, 'name': s.name, 'description': s.description, 'icon': s.icon})
	var catalog := {'races': out_races, 'classes': out_classes, 'items': out_items, 'skills': out_skills,
		'rules': {'gcd': Rules.GCD, 'potion_cooldown': Rules.POTION_COOLDOWN, 'max_level': Rules.MAX_LEVEL,
			'pack_slots': Rules.PACK_SLOTS}}
	if not for_hash:
		catalog.version = version
	return catalog
