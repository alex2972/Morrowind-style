extends RefCounted
## Database schema as an append-only list of migrations. Never edit a migration that has shipped; add a new
## one (ALTER TABLE / CREATE TABLE ...) at the end. database.gd records the applied version.
##
## Two families of tables:
##   content  - what the game IS (races, classes, abilities, items, NPCs, loot, vendors, spawns, quests,
##              skills). Edit these freely (DB Browser for SQLite), then `/reload` in game or restart.
##   players  - what players HAVE (accounts, characters, items, quests, skills). Written by the realm.

const MIGRATIONS := [
	# 1 - initial schema
	[
		# ---- players
		"""CREATE TABLE accounts (
			id INTEGER PRIMARY KEY,
			username TEXT NOT NULL UNIQUE COLLATE NOCASE,
			salt TEXT NOT NULL,
			digest TEXT NOT NULL,
			iterations INTEGER NOT NULL,
			is_admin INTEGER NOT NULL DEFAULT 0,
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			last_login TEXT)""",
		"""CREATE TABLE characters (
			id INTEGER PRIMARY KEY,
			account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
			name TEXT NOT NULL UNIQUE COLLATE NOCASE,
			sex TEXT NOT NULL,
			race_id TEXT NOT NULL,
			class_id TEXT NOT NULL,
			skin INTEGER NOT NULL DEFAULT 0,
			level INTEGER NOT NULL DEFAULT 1,
			xp INTEGER NOT NULL DEFAULT 0,
			gold INTEGER NOT NULL DEFAULT 0,
			health REAL,
			resource REAL,
			zone_id TEXT NOT NULL DEFAULT 'veyr',
			x REAL, y REAL, z REAL,
			yaw REAL NOT NULL DEFAULT 0,
			region TEXT NOT NULL DEFAULT '',
			played_seconds INTEGER NOT NULL DEFAULT 0,
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			last_login TEXT)""",
		"CREATE INDEX characters_by_account ON characters(account_id)",
		"""CREATE TABLE character_items (
			character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
			container TEXT NOT NULL,          -- 'pack' (28 slots), later 'bank', 'equipment'
			slot INTEGER NOT NULL,
			item_id TEXT NOT NULL,
			count INTEGER NOT NULL CHECK (count > 0),
			PRIMARY KEY (character_id, container, slot))""",
		"""CREATE TABLE character_quests (
			character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
			quest_id TEXT NOT NULL,
			state TEXT NOT NULL CHECK (state IN ('active', 'done')),
			progress TEXT NOT NULL DEFAULT '[]', -- JSON array, one counter per objective
			updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			PRIMARY KEY (character_id, quest_id))""",
		"""CREATE TABLE character_skills (
			character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
			skill_id TEXT NOT NULL,
			xp INTEGER NOT NULL DEFAULT 0,
			PRIMARY KEY (character_id, skill_id))""",
		# ---- content
		"""CREATE TABLE races (
			id TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			description TEXT NOT NULL DEFAULT '',
			scale REAL NOT NULL DEFAULT 1.0,
			playable INTEGER NOT NULL DEFAULT 1,
			skins TEXT NOT NULL DEFAULT '["ffffff"]', -- JSON array of hex tints
			sort INTEGER NOT NULL DEFAULT 0)""",
		"""CREATE TABLE classes (
			id TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			description TEXT NOT NULL DEFAULT '',
			resource TEXT NOT NULL CHECK (resource IN ('mana', 'rage', 'energy')),
			health_base REAL NOT NULL, health_per_level REAL NOT NULL,
			resource_base REAL NOT NULL, resource_per_level REAL NOT NULL,
			melee_base REAL NOT NULL, melee_per_level REAL NOT NULL,
			swing REAL NOT NULL DEFAULT 2.4,
			power REAL NOT NULL DEFAULT 1.0,
			armor REAL NOT NULL DEFAULT 0,
			playable INTEGER NOT NULL DEFAULT 1,
			sort INTEGER NOT NULL DEFAULT 0)""",
		"""CREATE TABLE abilities (
			id TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			description TEXT NOT NULL DEFAULT '', -- {damage} {heal} {dot} are filled in per caster level
			icon TEXT NOT NULL DEFAULT '',
			level INTEGER NOT NULL DEFAULT 1,
			cost REAL NOT NULL DEFAULT 0,
			cooldown REAL NOT NULL DEFAULT 0,
			cast_time REAL NOT NULL DEFAULT 0,
			range REAL NOT NULL DEFAULT 0,
			target TEXT NOT NULL CHECK (target IN ('enemy', 'ally', 'self', 'self_area')),
			anim TEXT NOT NULL DEFAULT '',
			fx TEXT NOT NULL DEFAULT '',
			effects TEXT NOT NULL DEFAULT '[]')""", # JSON: [{type: damage|heal|dot|area_damage, amount, weapon?, ticks?, interval?, radius?}]
		"""CREATE TABLE class_abilities (
			class_id TEXT NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
			ability_id TEXT NOT NULL REFERENCES abilities(id) ON DELETE CASCADE,
			sort INTEGER NOT NULL DEFAULT 0,
			PRIMARY KEY (class_id, ability_id))""",
		"""CREATE TABLE items (
			id TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			description TEXT NOT NULL DEFAULT '',
			icon TEXT NOT NULL DEFAULT '',
			price INTEGER NOT NULL DEFAULT 0,
			stack INTEGER NOT NULL DEFAULT 1 CHECK (stack >= 1), -- max per pack slot
			quest_item INTEGER NOT NULL DEFAULT 0,
			use_effect TEXT NOT NULL DEFAULT '{}')""",  # JSON: {heal: n} {mana: n}
		"""CREATE TABLE npc_templates (
			id TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			subtitle TEXT NOT NULL DEFAULT '',
			sex TEXT NOT NULL DEFAULT 'male',
			race_id TEXT NOT NULL DEFAULT 'human',
			skin INTEGER NOT NULL DEFAULT 0,
			role TEXT NOT NULL DEFAULT '',        -- '', 'quest', 'vendor', 'guard', 'enemy'
			hostile INTEGER NOT NULL DEFAULT 0,
			level INTEGER NOT NULL DEFAULT 1,
			health REAL NOT NULL DEFAULT 100,
			damage_min REAL NOT NULL DEFAULT 0, damage_max REAL NOT NULL DEFAULT 0,
			swing REAL NOT NULL DEFAULT 2.4,
			aggro_radius REAL NOT NULL DEFAULT 0,
			leash_radius REAL NOT NULL DEFAULT 30,
			respawn_seconds REAL NOT NULL DEFAULT 30,
			speed REAL NOT NULL DEFAULT 3.5,
			xp_factor REAL NOT NULL DEFAULT 1.0,
			gold_min INTEGER NOT NULL DEFAULT 0, gold_max INTEGER NOT NULL DEFAULT 0,
			greeting TEXT NOT NULL DEFAULT '')""",
		"""CREATE TABLE npc_loot (
			template_id TEXT NOT NULL REFERENCES npc_templates(id) ON DELETE CASCADE,
			item_id TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
			chance REAL NOT NULL CHECK (chance > 0 AND chance <= 1),
			count_min INTEGER NOT NULL DEFAULT 1,
			count_max INTEGER NOT NULL DEFAULT 1)""",
		"""CREATE TABLE npc_vendor (
			template_id TEXT NOT NULL REFERENCES npc_templates(id) ON DELETE CASCADE,
			item_id TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
			mode TEXT NOT NULL CHECK (mode IN ('sell', 'buy')),
			PRIMARY KEY (template_id, item_id, mode))""",
		"""CREATE TABLE spawns (
			id TEXT PRIMARY KEY,
			zone_id TEXT NOT NULL DEFAULT 'veyr',
			template_id TEXT NOT NULL REFERENCES npc_templates(id) ON DELETE CASCADE,
			x REAL NOT NULL, z REAL NOT NULL,
			yaw REAL NOT NULL DEFAULT 0)""",        # degrees; 0 faces north (-Z)
		"""CREATE TABLE quests (
			id TEXT PRIMARY KEY,
			title TEXT NOT NULL,
			giver_id TEXT NOT NULL REFERENCES npc_templates(id),
			turn_in_id TEXT NOT NULL REFERENCES npc_templates(id),
			level INTEGER NOT NULL DEFAULT 1,
			requires_id TEXT REFERENCES quests(id),
			offer_text TEXT NOT NULL DEFAULT '',
			progress_text TEXT NOT NULL DEFAULT '',
			complete_text TEXT NOT NULL DEFAULT '',
			reward_xp INTEGER NOT NULL DEFAULT 0,
			reward_gold INTEGER NOT NULL DEFAULT 0,
			sort INTEGER NOT NULL DEFAULT 0)""",
		"""CREATE TABLE quest_objectives (
			quest_id TEXT NOT NULL REFERENCES quests(id) ON DELETE CASCADE,
			idx INTEGER NOT NULL,
			type TEXT NOT NULL CHECK (type IN ('kill', 'collect', 'deliver', 'talk')),
			target TEXT NOT NULL,                 -- npc template (kill, talk) or item (collect, deliver)
			count INTEGER NOT NULL DEFAULT 1,
			label TEXT NOT NULL DEFAULT '',
			PRIMARY KEY (quest_id, idx))""",
		"""CREATE TABLE quest_items (
			quest_id TEXT NOT NULL REFERENCES quests(id) ON DELETE CASCADE,
			item_id TEXT NOT NULL REFERENCES items(id),
			count INTEGER NOT NULL DEFAULT 1,
			kind TEXT NOT NULL CHECK (kind IN ('start', 'reward')))""",
		"""CREATE TABLE skills (
			id TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			description TEXT NOT NULL DEFAULT '',
			icon TEXT NOT NULL DEFAULT '',
			sort INTEGER NOT NULL DEFAULT 0)""",
	],
]
