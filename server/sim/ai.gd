extends RealmSystem
## NPCs: spawning from the `spawns` table, respawning, how they move while nobody fights them, and the brain
## of hostile ones - notice players in aggro range (with line of sight), chase the highest-threat target,
## swing at it, give up past the leash radius and walk back healing ("evade").
##
## Out of combat every NPC follows its spawn's `movement`:
##   still   stands at its spawn point, facing its yaw, playing `idle_anim` (e.g. sit_idle on a bench)
##   wander  strolls to random points within `wander_radius` of its spawn, pausing between them
##   path    walks a route from the `paths` / `path_points` tables (loop or back_and_forth), stopping at
##           points with a wait to face a direction and play a clip
## Hostile NPCs keep watching for players while they move; after evading they walk back to where the
## fight started and carry on.

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
			# movement out of combat
			'movement': str(s.get('movement', 'still')), 'wander_radius': float(s.get('wander_radius', 0.0)),
			'path': realm.content.paths.get(str(s.get('path_id', '')), {}), 'idle_anim': str(s.get('idle_anim', '')),
			'anchor': home, 'goal': null, 'wait': 0.0, 'leg': 0, 'leg_step': 1, 'pose': '',
		}
		_reset_movement(npc)
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
		npc.anchor = npc.pos   # evading walks back here, then the NPC carries on wandering / patrolling
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
			npc.anchor = npc.home
			_reset_movement(npc)
			realm.zone_of(npc).moved(npc)
		return
	var zone := realm.zone_of(npc)
	match npc.state:
		'idle':
			_move(npc, dt)
			if not t.hostile:
				return
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
			if Vector2(npc.pos.x - npc.anchor.x, npc.pos.z - npc.anchor.z).length() > float(t.leash_radius):
				_evade(npc)
				return
			var to := Vector3(target.pos.x - npc.pos.x, 0.0, target.pos.z - npc.pos.z)
			if to.length() > 0.01:
				npc.yaw = atan2(-to.x, -to.z)
			if to.length() > Rules.NPC_REACH:
				_step(npc, to.normalized() * minf(float(t.speed) * dt, to.length() - Rules.NPC_REACH * 0.8), dt)
				npc.clip = 'run'
				npc.rate = float(t.speed) / Rules.RUN_CLIP_SPEED
			else:
				npc.clip = 'combat_idle'
				npc.rate = 1.0
			npc.swing -= dt
			if npc.swing <= 0.0 and to.length() <= Rules.NPC_REACH + 0.6 and absf(target.pos.y - npc.pos.y) < 3.0:
				npc.swing = float(t.swing)
				realm.event_near(npc, {'type': 'anim', 'id': npc.eid, 'clip': ['punch_jab', 'punch_cross', 'punch_hook'][realm.rng().randi() % 3]})
				realm.combat.damage(npc, target, realm.rng().randf_range(float(t.damage_min), float(t.damage_max)), 'melee')
		'return':
			npc.health = minf(npc.max_health, npc.health + npc.max_health * dt)
			if _walk_to(npc, npc.anchor, float(t.speed) * 1.5, dt, 'run'):
				npc.state = 'idle'
				npc.health = npc.max_health
				npc.goal = null
				npc.wait = 0.0
				if npc.movement == 'still':
					npc.yaw = npc.home_yaw

# ---------------------------------------------------------------- movement out of combat

func _reset_movement(npc: Dictionary) -> void:
	npc.goal = null
	npc.leg = 0
	npc.leg_step = 1
	npc.pose = ''
	npc.wait = realm.rng().randf_range(0.5, 4.0) if npc.movement == 'wander' else 0.0
	npc.clip = npc.idle_anim if npc.idle_anim != '' else 'idle'
	npc.rate = 1.0

func _move(npc: Dictionary, dt: float) -> void:
	match npc.movement:
		'wander':
			_wander(npc, dt)
		'path':
			_patrol(npc, dt)
		_:
			npc.clip = npc.idle_anim if npc.idle_anim != '' else 'idle'
			npc.rate = 1.0

func _stand(npc: Dictionary, dt: float) -> bool:
	## Counts down a pause, playing the pose. True while still waiting.
	if npc.wait <= 0.0:
		return false
	npc.wait -= dt
	npc.clip = npc.pose if npc.pose != '' else (npc.idle_anim if npc.idle_anim != '' else 'idle')
	npc.rate = 1.0
	return true

func hold_for_talk(npc: Dictionary, p: Dictionary) -> void:
	## A player talks to a walking NPC: it stops and turns to them for a while (seated ones stay put).
	if npc.movement == 'still' or npc.state != 'idle':
		return
	npc.wait = maxf(npc.wait, 12.0)
	npc.pose = 'idle'
	var to := Vector3(p.pos.x - npc.pos.x, 0.0, p.pos.z - npc.pos.z)
	if to.length() > 0.01:
		npc.yaw = atan2(-to.x, -to.z)

func _wander(npc: Dictionary, dt: float) -> void:
	if _stand(npc, dt):
		return
	if npc.goal == null:
		var rng := realm.rng()
		var zone := realm.zone_of(npc)
		var angle := rng.randf() * TAU
		var r := float(npc.wander_radius) * sqrt(rng.randf())
		var spot := Vector3(npc.home.x + cos(angle) * r, 0.0, npc.home.z + sin(angle) * r)
		spot.y = zone.ground(spot.x, spot.z, npc.pos.y + 4.0)
		# no cliffs and nothing solid in between, otherwise try again a moment later
		if absf(spot.y - npc.pos.y) > 2.5 or not zone.sight(npc.pos, spot):
			npc.wait = 0.5
			return
		npc.goal = spot
	if _walk_to(npc, npc.goal, Rules.NPC_WALK_SPEED, dt):
		npc.goal = null
		npc.wait = realm.rng().randf_range(3.0, 9.0)

func _patrol(npc: Dictionary, dt: float) -> void:
	if _stand(npc, dt):
		return
	npc.pose = ''
	var points: Array = npc.path.get('points', [])
	if points.size() < 2:
		npc.clip = 'idle'
		return
	var point: Dictionary = points[npc.leg]
	if not _walk_to(npc, Vector3(float(point.x), npc.pos.y, float(point.z)), Rules.NPC_WALK_SPEED, dt):
		return
	if float(point.wait) > 0.0:
		npc.wait = float(point.wait)
		npc.pose = str(point.anim)
		if point.yaw != null:
			npc.yaw = deg_to_rad(float(point.yaw))
		npc.clip = npc.pose if npc.pose != '' else 'idle'
		npc.rate = 1.0
	# next point: around again (loop) or turn back at either end (back_and_forth)
	if str(npc.path.mode) == 'back_and_forth':
		if npc.leg + npc.leg_step < 0 or npc.leg + npc.leg_step >= points.size():
			npc.leg_step = -npc.leg_step
		npc.leg += npc.leg_step
	else:
		npc.leg = (npc.leg + 1) % points.size()

func _walk_to(npc: Dictionary, goal: Vector3, speed: float, dt: float, clip := 'walk') -> bool:
	## Moves towards goal (horizontally, following the ground). True once there.
	var to := Vector3(goal.x - npc.pos.x, 0.0, goal.z - npc.pos.z)
	var dist := to.length()
	if dist < 0.15:
		return true
	npc.yaw = atan2(-to.x, -to.z)
	_step(npc, to / dist * minf(speed * dt, dist), dt)
	npc.clip = clip
	npc.rate = speed / (Rules.RUN_CLIP_SPEED if clip == 'run' else Rules.WALK_CLIP_SPEED)
	return dist <= speed * dt

func _step(npc: Dictionary, step: Vector3, dt: float) -> void:
	npc.pos += step
	npc.ground_t -= dt
	if npc.ground_t <= 0.0:
		npc.ground_t = 0.15
		npc.pos.y = realm.zone_of(npc).ground(npc.pos.x, npc.pos.z, npc.pos.y + 3.0)
	realm.zone_of(npc).moved(npc)
