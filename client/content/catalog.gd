class_name Catalog
extends RefCounted
## What the client knows about the game's content: only the display data the realm sends after sign-in
## (S_CATALOG - names, descriptions, icons, skin tints) and client-side presentation helpers (icons, body
## scenes, the placeholder race tint). No rules, stats, drop tables or quest logic live on the client.

const SEXES := ['male', 'female']
const BODY_SCENES := {'male': 'res://scenes/props/player_body.tscn', 'female': 'res://scenes/props/player_body_female.tscn'}
const RACE_BODY_SCENES := {'high_elf/male': 'res://scenes/props/player_high_elf_male.tscn', 'high_elf/female': 'res://scenes/props/player_high_elf_female.tscn'}
const PREVIEW_SPOT := Vector3(-11.6, 2.58, 100.5)   ## harbour pier, where the lobby shows the character

static var version := ''
static var races: Dictionary = {}      ## id -> {name, description, scale, skins, playable}
static var race_order: Array = []
static var classes: Dictionary = {}    ## id -> {name, description, resource, abilities: [{name, level, icon}]}
static var class_order: Array = []
static var items: Dictionary = {}      ## id -> {name, description, icon, stack, usable}
static var skills: Array = []
static var rules: Dictionary = {'gcd': 1.5, 'potion_cooldown': 10.0, 'max_level': 20, 'pack_slots': 28}

static func receive(data: Dictionary) -> void:
	version = str(data.get('version', ''))
	races.clear()
	race_order.clear()
	for r in data.get('races', []):
		races[r.id] = r.duplicate()
		if r.id == 'high_elf':
			races[r.id].description = str(r.get('description', '')).replace(' (Placeholder: shares the human body for now.)', '')
		race_order.append(r.id)
	classes.clear()
	class_order.clear()
	for c in data.get('classes', []):
		classes[c.id] = c
		class_order.append(c.id)
	items = data.get('items', {})
	skills = data.get('skills', [])
	rules.merge(data.get('rules', {}), true)

static func item(id: String) -> Dictionary:
	return items.get(id, {'name': id, 'description': '', 'icon': '', 'stack': 1, 'usable': false})

# ---------------------------------------------------------------- bodies and placeholder appearance

static var _bodies: Dictionary = {}   ## resource path -> PackedScene, held so the 5 MB scenes are parsed only once

static func preload_bodies() -> void:
	## Starts parsing available bodies in the background at boot, so the first NPC doesn't stall a frame.
	for path in BODY_SCENES.values() + RACE_BODY_SCENES.values():
		ResourceLoader.load_threaded_request(path)

static func body_scene(sex: String, race: String = '') -> PackedScene:
	if not BODY_SCENES.has(sex):
		sex = 'male'
	var key := race + '/' + sex
	var path: String = RACE_BODY_SCENES.get(key, BODY_SCENES[sex])
	if not _bodies.has(path):
		if ResourceLoader.load_threaded_get_status(path) != ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
			_bodies[path] = ResourceLoader.load_threaded_get(path)
		else:
			_bodies[path] = load(path)
	return _bodies[path]

static func race_scale(race: String) -> float:
	return float(races.get(race, {}).get('scale', 1.0))

static func race_stretch(race: String) -> Vector3:
	## A race's `scale` is a height stretch: taller and longer-limbed, never wider (high elves 1.07, from the races table).
	return Vector3(1.0, race_scale(race), 1.0)

static func skin_color(race: String, skin: int) -> Color:
	var list: Array = races.get(race, {}).get('skins', ['ffffff'])
	return Color(str(list[clampi(skin, 0, list.size() - 1)]))

static func apply_appearance(model: Node3D, race: String, skin: int) -> void:
	## Baked race models carry their own skin and hair; tone only the body material.
	var tint := skin_color(race, skin)
	if race == 'high_elf' and model.has_meta('race_preset'):
		var neutral := skin_color(race, 1)
		tint = Color(tint.r / maxf(neutral.r, 0.01), tint.g / maxf(neutral.g, 0.01), tint.b / maxf(neutral.b, 0.01))
	for node in model.find_children('*', 'MeshInstance3D', true, false):
		var mi := node as MeshInstance3D
		for s in mi.mesh.get_surface_count():
			var base: Material = mi.get_surface_override_material(s)
			if base == null:
				base = mi.mesh.surface_get_material(s)
			if base is StandardMaterial3D and not base.resource_name.begins_with('hair_'):
				var m: StandardMaterial3D = base.duplicate()
				m.albedo_color = tint
				mi.set_surface_override_material(s, m)

# ---------------------------------------------------------------- icons

static var _icon_cache: Dictionary = {}

static func icon(spec: String) -> Texture2D:
	## 'atlas:N' = tile N of the ability atlas (4x2); 'gen:name' = assets/ui/icons/name.png.
	if _icon_cache.has(spec):
		return _icon_cache[spec]
	var tex: Texture2D = null
	if spec.begins_with('atlas:'):
		var i := int(spec.trim_prefix('atlas:'))
		var atlas := AtlasTexture.new()
		atlas.atlas = load('res://assets/ui/ability_atlas.png')
		var w := atlas.atlas.get_width() / 4.0
		var h := atlas.atlas.get_height() / 2.0
		atlas.region = Rect2((i % 4) * w, floori(i / 4.0) * h, w, h)
		tex = atlas
	elif spec.begins_with('gen:'):
		var path := 'res://assets/ui/icons/%s.png' % spec.trim_prefix('gen:')
		if ResourceLoader.exists(path):
			tex = load(path)
	_icon_cache[spec] = tex
	return tex
