extends RealmSystem
## NPCs: spawning from the `spawns` table, respawning, and the brain of hostile ones - notice players in
## aggro range (with line of sight), chase the highest-threat target, swing at it, give up past the leash
## radius and walk home healing ("evade").

var _spawned := false

func setup() -> void:
	pass

func spawn_all() -> void:
	for s in realm.content.spawns:
		var zone: Zone = realm.zones.get(str(s.zone_id))
		if zone == null:
			continue
		var t: Dictionary = realm.content.templates[s.template_id]
		var home := Vector3(float(s.x), 0.0, float(s.z))
		home.y = zone.ground(home.x, home.z)
		var yaw := deg_to_rad(float(s.yaw))
		var npc := {
			'eid': str(s.id), 'kind': 'npc', 'template': t, 'name': str(t.name), 'level': int(t.level),
			'max_health': float(t.health), 'health': float(t.health), 'home': home, 'pos': home, 'home_yaw': yaw, 'yaw': yaw,
			'state': 'idle', 'target': '', 'threat': {}, 'tag': '', 'swing': 0.0, 'dots': [], 'dead': false,
			'respawn_at': 0.0, 'clip': 'idle', 'rate': 1.0, 'look_t': 0.0, 'ground_t': 0.0, 'cast': {}, 'combat': -100.0,
		}
		realm.add_entity(npc, zone.id)

func respawn_all() -> void:
	## After a content reload: NPCs are rebuilt from the new templates and spawns.
	for e in realm.entities.values():
		if e.kind == 'npc':
			realm.remove_entity(e)
	spawn_all()

func engage(npc: Dictionary, eid: String, threat := 1.0) -> void:
	if npc.dead or not npc.template.hostile or npc.state == 'return':
		return
	if npc.state == 'idle':
		npc.swing = 0.6
	npc.state = 'chase'
	npc.threat[eid] = float(npc.threat.get(eid, 0.0)) + threat
	if npc.target == '' or not npc.threat.has(npc.target):
		npc.target = eid

func forget(eid: String) -> void:
	## A player died or left: every NPC drops them.
	for e in realm.entities.values():
		if e.kind == 'npc' and e.threat.has(eid):
			e.threat.erase(eid)
			if e.target == eid:
				_next_target(e)

func _next_target(npc: Dictionary) -> void:
	npc.threat.erase(npc.target)
	var best := ''
	var best_threat := -1.0
	for eid in npc.threat:
		var t: Dictionary = realm.entities.get(eid, {})
		if not t.is_empty() and not t.dead and npc.threat[eid] > best_threat:
			best = eid
			best_threat = npc.threat[eid]
	npc.target = best
	if best == '':
		_evade(npc)

func _evade(npc: Dictionary) -> void:
	npc.state = 'return'
	npc.target = ''
	npc.threat.clear()
	npc.tag = ''
	npc.dots.clear()

func tick(dt: float) -> void:
	if not _spawned:   # first tick: the zones' physics spaces are populated by now
		_spawned = true
		spawn_all()
	for e in realm.entities.values():
		if e.kind == 'npc':
			_think(e, dt)

func _think(npc: Dictionary, dt: float) -> void:
	var t: Dictionary = npc.template
	if npc.dead:
		if realm.now >= npc.respawn_at:
			npc.dead = false
			npc.health = npc.max_health
			npc.pos = npc.home
			npc.yaw = npc.home_yaw
			npc.state = 'idle'
			npc.clip = 'idle'
			realm.zone_of(npc).moved(npc)
		return
	if not t.hostile:
		return
	var zone := realm.zone_of(npc)
	match npc.state:
		'idle':
			npc.clip = 'idle'
			npc.look_t -= dt
			if npc.look_t <= 0.0:
				npc.look_t = 0.4
				for p in zone.nearby(npc.pos, 18.0, true):
					var reach := clampf(float(t.aggro_radius) - (p.level - npc.level), 4.0, 18.0)
					if not p.dead and npc.pos.distance_to(p.pos) < reach and zone.sight(npc.pos, p.pos):
						engage(npc, p.eid)
						break
		'chase':
			var target: Dictionary = realm.entities.get(npc.target, {})
			if target.is_empty() or target.dead or target.zone != npc.zone:
				_next_target(npc)
				return
			if Vector2(npc.pos.x - npc.home.x, npc.pos.z - npc.home.z).length() > float(t.leash_radius):
				_evade(npc)
				return
			var to := Vector3(target.pos.x - npc.pos.x, 0.0, target.pos.z - npc.pos.z)
			if to.length() > 0.01:
				npc.yaw = atan2(-to.x, -to.z)
			if to.length() > Rules.NPC_REACH:
				_step(npc, to.normalized() * minf(float(t.speed) * dt, to.length() - Rules.NPC_REACH * 0.8), dt)
				npc.clip = 'run'
				npc.rate = float(t.speed) / 4.9
			else:
				npc.clip = 'combat_idle'
				npc.rate = 1.0
			npc.swing -= dt
			if npc.swing <= 0.0 and to.length() <= Rules.NPC_REACH + 0.6 and absf(target.pos.y - npc.pos.y) < 3.0:
				npc.swing = float(t.swing)
				realm.event_near(npc, {'type': 'anim', 'id': npc.eid, 'clip': ['punch_jab', 'punch_cross', 'punch_hook'][realm.rng().randi() % 3]})
				realm.combat.damage(npc, target, realm.rng().randf_range(float(t.damage_min), float(t.damage_max)), 'melee')
		'return':
			var to := Vector3(npc.home.x - npc.pos.x, 0.0, npc.home.z - npc.pos.z)
			npc.health = minf(npc.max_health, npc.health + npc.max_health * dt)
			if to.length() < 0.4:
				npc.state = 'idle'
				npc.yaw = npc.home_yaw
				npc.health = npc.max_health
				npc.pos = npc.home
				zone.moved(npc)
				return
			npc.yaw = atan2(-to.x, -to.z)
			_step(npc, to.normalized() * minf(float(t.speed) * 1.5 * dt, to.length()), dt)
			npc.clip = 'run'
			npc.rate = float(t.speed) * 1.5 / 4.9

func _step(npc: Dictionary, step: Vector3, dt: float) -> void:
	npc.pos += step
	npc.ground_t -= dt
	if npc.ground_t <= 0.0:
		npc.ground_t = 0.15
		npc.pos.y = realm.zone_of(npc).ground(npc.pos.x, npc.pos.z, npc.pos.y + 3.0)
	realm.zone_of(npc).moved(npc)
