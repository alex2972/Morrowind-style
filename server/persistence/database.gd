class_name RealmDatabase
extends RefCounted
## Thin wrapper over the godot-sqlite GDExtension: opening (WAL, foreign keys), versioned migrations,
## parameter-bound queries returning plain String-keyed rows, and transactions. Only the persistence and
## content layers talk to it; game systems go through Repository / Content.

const Schema = preload('res://server/persistence/schema.gd')

var db: Object
var path := ''

func open(file: String) -> bool:
	path = file
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(file.get_base_dir()))
	if not ClassDB.class_exists('SQLite'):
		push_error('The godot-sqlite add-on is not loaded (addons/godot-sqlite). Open the project in the editor once.')
		return false
	db = ClassDB.instantiate('SQLite')
	db.path = file
	db.verbosity_level = 0
	if not db.open_db():
		push_error('Could not open the database %s' % file)
		return false
	exec('PRAGMA journal_mode = WAL')      # readers (e.g. DB Browser) never block the realm
	exec('PRAGMA synchronous = NORMAL')
	exec('PRAGMA foreign_keys = ON')
	exec('PRAGMA busy_timeout = 2000')
	return migrate()

func close() -> void:
	if db:
		db.close_db()
		db = null

## Runs a statement; returns false (and logs) on error.
func exec(sql: String, args: Array = []) -> bool:
	var ok: bool = db.query(sql) if args.is_empty() else db.query_with_bindings(sql, args)
	if not ok:
		push_error('SQL error: %s\n  in: %s' % [db.error_message, sql.left(240)])
	return ok

func rows(sql: String, args: Array = []) -> Array:
	if not exec(sql, args):
		return []
	var out: Array = []
	for r in db.query_result:
		var row := {}
		for k in r:
			row[str(k)] = r[k]
		out.append(row)
	return out

func row(sql: String, args: Array = []) -> Dictionary:
	var r := rows(sql, args)
	return r[0] if not r.is_empty() else {}

func value(sql: String, args: Array = [], default: Variant = null) -> Variant:
	var r := row(sql, args)
	return r.values()[0] if not r.is_empty() else default

func last_id() -> int:
	return int(db.last_insert_rowid)

## Runs `work` inside BEGIN IMMEDIATE ... COMMIT; rolls back if it returns false or a statement fails.
func transaction(work: Callable) -> bool:
	if not exec('BEGIN IMMEDIATE'):
		return false
	var ok: bool = work.call()
	if ok:
		ok = exec('COMMIT')
	if not ok:
		exec('ROLLBACK')
	return ok

func migrate() -> bool:
	exec('CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)')
	var current := int(value('SELECT COALESCE(MAX(version), 0) FROM schema_version', [], 0))
	for i in Schema.MIGRATIONS.size():
		var version := i + 1
		if version <= current:
			continue
		var steps: Array = Schema.MIGRATIONS[i]
		var ok := transaction(func() -> bool:
			for sql in steps:
				if not exec(sql):
					return false
			return exec('INSERT INTO schema_version (version) VALUES (?)', [version]))
		if not ok:
			push_error('Database migration %d failed.' % version)
			return false
		print('Database migrated to schema version %d' % version)
	return true
