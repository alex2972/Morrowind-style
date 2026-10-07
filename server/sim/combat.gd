extends RealmSystem
## WoW-style combat: abilities with costs, cast times, a global cooldown and their own cooldowns; range and
## line-of-sight checks; auto-attack; damage over time; area damage; armour; crits; rage/mana; regeneration;
## death and release. Emits 'npc_killed' {npc, tag} and 'player_died' {player}.

func setup() -> void:
	realm.handle(Protocol.C_TARGET, func(p: Dictionary, d: Dictionary) -> void:
		var id := str(d.get('id', ''))
		p.target = id if realm.entities.has(id) else '')
	realm.handle(Protocol.C_ATTACK, func(p: Dictionary, d: Dictionary) -> void: set_auto(p, bool(d.get('on', false))))
	realm.handle(Protocol.C_CAST, func(p: Dictionary, d: Dictionary) -> void:
		begin(p, str(d.get('ability', '')), str(d.get('target', ''))))
	realm.handle(Protocol.C_RELEASE, func(p: Dictionary, _d: Dictionary) -> void: release(p))

func player_joined(p: Dictionary, data: Dictionary) -> void:
	p.merge({'target': '', 'auto': false, 'swing': 0.0, 'gcd': 0.0, 'cooldowns': {}, 'cast': {}, 'potion': 0.0,
		'dead': false, 'combat': -100.0, 'last_cast': -100.0, 'dots': []}, true)
	refresh_stats(p)
	var row: Dictionary = data.row
	p.health = clampf(float(row.health) if row.health != null else p.max_health, 1.0, p.max_health)
	var start: float = 0.0 if p.resource_kind == 'rage' else p.max_resource
	p.resource = clampf(float(row.resource) if row.resource != null else start, 0.0, p.max_resource)

func player_left(p: Dictionary) -> void:
	realm.ai.forget(p.eid)

func write_save(p: Dictionary, state: Dictionary) -> void:
	state.health = p.health if not p.dead else p.max_health * 0.5
	state.resource = p.resource

func write_sheet(p: Dictionary, sheet: Dictionary) -> void:
	var cls: Dictionary = realm.content.classes[p.job]
	var list: Array = []
	for aid in cls.abilities:
		var a: Dictionary = realm.content.abilities[aid]
		list.append({'id': aid, 'name': a.name, 'icon': a.icon, 'text': Rules.ability_text(a, cls, p.level),
			'level': int(a.level), 'known': int(a.level) <= p.level, 'cost': float(a.cost), 'cast': float(a.cast_time),
			'cooldown': float(a.cooldown), 'range': float(a.range), 'target': a.target})
	sheet.abilities = list
	sheet.stats = {'health': p.max_health, 'resource': p.max_resource, 'resource_kind': p.resource_kind,
		'melee': Rules.melee_damage(cls, p.level), 'swing': float(cls.swing), 'armor': Rules.armor(cls, p.level),
		'class_name': cls.name, 'race_name': realm.content.races.get(p.race, {}).get('name', p.race)}

func refresh_stats(p: Dictionary) -> void:
	var cls: Dictionary = realm.content.classes[p.job]
	p.max_health = Rules.max_health(cls, p.level)
	p.max_resource = Rules.max_resource(cls, p.level)
	p.resource_kind = str(cls.resource)
	if p.has('health'):
		p.health = minf(p.health, p.max_health)
		p.resource = minf(p.resource, p.max_resource)

func vitals(p: Dictionary) -> Dictionary:
	## The owner's own fast-changing state, sent in every state packet.
	var cds := {}
	for aid in p.cooldowns:
		if p.cooldowns[aid] > realm.now:
			cds[aid] = p.cooldowns[aid] - realm.now
	return {'hp': p.health, 'mhp': p.max_health, 'res': p.resource, 'mres': p.max_resource, 'kind': p.resource_kind,
		'gcd': maxf(0.0, p.gcd - realm.now), 'cds': cds, 'potion': maxf(0.0, p.potion - realm.now), 'auto': p.auto,
		'dead': p.dead, 'combat': realm.now - p.combat < Rules.COMBAT_TIMEOUT, 'target': p.target, 'level': p.level,
		'cast': {} if p.cast.is_empty() else {'ability': p.cast.ability, 'total': p.cast.total, 'left': p.cast.end - realm.now}}

# ---------------------------------------------------------------- abilities

func set_auto(p: Dictionary, on: bool) -> void:
	if not on or p.dead:
		p.auto = false
		return
	var t: Dictionary = realm.entities.get(p.target, {})
	if t.is_empty() or t.kind != 'npc' or t.dead or not t.template.hostile:
		realm.error(p, 'You have no target.' if t.is_empty() else 'You cannot attack that target.')
		p.auto = false
		return
	if not p.auto:
		p.swing = minf(p.swing, 0.3)
	p.auto = true

func _target_for(p: Dictionary, a: Dictionary, tid: String) -> Dictionary:
	## The validated target, or {'error': message}.
	var zone := realm.zone_of(p)
	match str(a.target):
		'enemy':
			var t: Dictionary = realm.entities.get(tid, {})
			if t.is_empty():
				return {'error': 'You have no target.'}
			if t.kind != 'npc' or not t.template.hostile or t.dead or t.zone != p.zone:
				return {'error': 'Invalid target.'}
			if p.pos.distance_to(t.pos) > float(a.range) + 0.6:
				return {'error': 'Out of range.'}
			if not zone.sight(p.pos, t.pos):
				return {'error': 'Target not in line of sight.'}
			return t
		'ally':
			var t: Dictionary = realm.entities.get(tid, {})
			if t.is_empty() or t.kind != 'player' or t.dead or t.zone != p.zone:
				return p
			if p.pos.distance_to(t.pos) > float(a.range) + 0.6:
				return {'error': 'Out of range.'}
			if not zone.sight(p.pos, t.pos):
				return {'error': 'Target not in line of sight.'}
			return t
	return p

func begin(p: Dictionary, aid: String, tid: String) -> void:
	var a: Dictionary = realm.content.abilities.get(aid, {})
	if p.dead or a.is_empty() or not aid in realm.content.classes[p.job].abilities or int(a.level) > p.level:
		return
	if not p.cast.is_empty():
		realm.error(p, 'You are already casting.')
		return
	if realm.now < p.gcd or realm.now < float(p.cooldowns.get(aid, 0.0)):
		realm.error(p, 'That ability is not ready yet.')
		return
	if p.resource < float(a.cost):
		realm.error(p, 'Not enough %s.' % p.resource_kind)
		return
	var t := _target_for(p, a, tid)
	if t.has('error'):
		realm.error(p, t.error)
		return
	p.gcd = realm.now + Rules.GCD
	if a.fx == 'melee':
		p.target = t.eid
		set_auto(p, true)
	if float(a.cast_time) > 0.0:
		p.cast = {'ability': aid, 'target': t.eid, 'end': realm.now + float(a.cast_time), 'total': float(a.cast_time)}
		realm.event_near(p, {'type': 'cast', 'id': p.eid, 'ability': aid, 'name': a.name, 'time': float(a.cast_time)})
	else:
		_resolve(p, a, t)

func cancel_cast(p: Dictionary, reason: String) -> void:
	if p.cast.is_empty():
		return
	p.cast = {}
	p.gcd = realm.now
	realm.event_near(p, {'type': 'cast_stop', 'id': p.eid})
	realm.error(p, reason)

func _finish_cast(p: Dictionary) -> void:
	var a: Dictionary = realm.content.abilities.get(p.cast.ability, {})
	var tid: String = p.cast.target
	p.cast = {}
	if a.is_empty():
		return
	var t := _target_for(p, a, tid)
	if p.resource < float(a.cost) or t.has('error'):
		realm.event_near(p, {'type': 'cast_stop', 'id': p.eid})
		realm.error(p, 'Not enough %s.' % p.resource_kind if not t.has('error') else t.error)
		return
	_resolve(p, a, t)

func _resolve(p: Dictionary, a: Dictionary, t: Dictionary) -> void:
	var cls: Dictionary = realm.content.classes[p.job]
	p.resource -= float(a.cost)
	p.last_cast = realm.now
	if float(a.cooldown) > 0.0:
		p.cooldowns[a.id] = realm.now + float(a.cooldown)
	realm.event_near(p, {'type': 'ability', 'id': p.eid, 'target': t.eid, 'ability': a.id, 'clip': a.anim, 'fx': a.fx})
	var rng := realm.rng()
	for e in a.effects:
		var amount := Rules.effect_amount(e, cls, p.level)
		match str(e.type):
			'damage':
				damage(p, t, amount * rng.randf_range(0.92, 1.08), a.id)
			'heal':
				heal(p, t, amount * rng.randf_range(0.92, 1.08), a.id)
			'dot':
				t.dots = t.dots.filter(func(d: Dictionary) -> bool: return not (d.src == p.eid and d.ability == a.id))
				t.dots.append({'src': p.eid, 'ability': a.id, 'amount': amount, 'ticks': int(e.ticks),
					'interval': float(e.interval), 'next': realm.now + float(e.interval)})
				_aggro(p, t, 1.0)
			'area_damage':
				for npc in realm.zone_of(p).nearby(p.pos, float(e.radius)):
					if npc.kind == 'npc' and npc.template.hostile and not npc.dead:
						damage(p, npc, amount * rng.randf_range(0.92, 1.08), a.id)

# ---------------------------------------------------------------- damage, healing, death

func _aggro(src: Dictionary, npc: Dictionary, threat: float) -> void:
	if npc.kind != 'npc':
		return
	if npc.tag == '' and src.kind == 'player':
		npc.tag = src.eid      # first to hit gets the credit (shared with their party)
	realm.ai.engage(npc, src.eid, threat)
	src.combat = realm.now
	npc.combat = realm.now

func damage(src: Dictionary, dst: Dictionary, amount: float, what: String) -> void:
	if dst.is_empty() or dst.dead:
		return
	var crit: bool = src.kind == 'player' and realm.rng().randf() < 0.06
	var armor: float = Rules.armor(realm.content.classes[dst.job], dst.level) if dst.kind == 'player' else Rules.npc_armor(dst.level)
	var dealt := maxi(1, int(round(Rules.mitigate(amount, armor) * (1.5 if crit else 1.0))))
	dst.health = maxf(0.0, dst.health - dealt)
	src.combat = realm.now
	dst.combat = realm.now
	if src.kind == 'player' and src.resource_kind == 'rage' and what == 'melee':
		src.resource = minf(src.max_resource, src.resource + 7.0 + dealt * 0.15)
	if dst.kind == 'player' and dst.resource_kind == 'rage':
		dst.resource = minf(dst.max_resource, dst.resource + dealt * 0.4)
	_aggro(src, dst, dealt)
	realm.event_near(dst, {'type': 'hit', 'src': src.eid, 'dst': dst.eid, 'amount': dealt, 'crit': crit, 'what': what})
	if dst.health <= 0.0:
		if dst.kind == 'player':
			_player_died(dst)
		else:
			_npc_died(dst)

func heal(src: Dictionary, dst: Dictionary, amount: float, what: String) -> void:
	if dst.dead:
		return
	var crit := realm.rng().randf() < 0.06
	var healed := int(round(minf(amount * (1.5 if crit else 1.0), dst.max_health - dst.health)))
	dst.health += healed
	if realm.now - dst.combat < Rules.COMBAT_TIMEOUT:
		src.combat = realm.now
		for npc in realm.zone_of(dst).nearby(dst.pos, 40.0):   # healing someone in a fight draws attention
			if npc.kind == 'npc' and npc.state == 'chase' and npc.threat.has(dst.eid):
				realm.ai.engage(npc, src.eid, healed * 0.5)
	realm.event_near(dst, {'type': 'heal', 'src': src.eid, 'dst': dst.eid, 'amount': healed, 'crit': crit, 'what': what})

func _player_died(p: Dictionary) -> void:
	p.dead = true
	p.health = 0.0
	p.auto = false
	p.cast = {}
	p.dots.clear()
	realm.ai.forget(p.eid)
	realm.event_near(p, {'type': 'death', 'id': p.eid})
	realm.tell(p, 'You have died. Release your spirit to return to the harbour.')
	realm.emit('player_died', {'player': p})

func _npc_died(npc: Dictionary) -> void:
	npc.dead = true
	npc.health = 0.0
	npc.state = 'dead'
	npc.clip = 'death'
	npc.dots.clear()
	npc.threat.clear()
	npc.target = ''
	npc.respawn_at = realm.now + float(npc.template.respawn_seconds)
	realm.event_near(npc, {'type': 'death', 'id': npc.eid})
	var tag: String = npc.tag
	npc.tag = ''
	for p in realm.players.values():
		if p.target == npc.eid:
			p.auto = false
	realm.emit('npc_killed', {'npc': npc, 'tag': tag})

func release(p: Dictionary) -> void:
	if not p.dead:
		return
	p.dead = false
	p.health = p.max_health * 0.5
	p.resource = 0.0 if p.resource_kind == 'rage' else p.max_resource * 0.5
	p.combat = -100.0
	var zone := realm.zone_of(p)
	realm.movement.teleport(p, zone.spawn_point(), zone.spawn_yaw())
	realm.event_near(p, {'type': 'revive', 'id': p.eid})
	realm.tell(p, 'Your spirit returns to the harbour.')

# ---------------------------------------------------------------- tick

func tick(dt: float) -> void:
	for e in realm.entities.values():
		if not e.dead and not e.dots.is_empty():
			_tick_dots(e)
	for p in realm.players.values():
		if not p.dead:
			_tick_player(p, dt)

func _tick_dots(e: Dictionary) -> void:
	for dot in e.dots.duplicate():
		if realm.now < dot.next:
			continue
		dot.next += dot.interval
		dot.ticks -= 1
		if dot.ticks <= 0:
			e.dots.erase(dot)
		var src: Dictionary = realm.entities.get(dot.src, {})
		if src.is_empty():
			e.dots.erase(dot)
			continue
		damage(src, e, dot.amount, dot.ability)
		if e.dead:
			return

func _tick_player(p: Dictionary, dt: float) -> void:
	var fighting: bool = realm.now - p.combat < Rules.COMBAT_TIMEOUT
	if not fighting:
		p.health = minf(p.max_health, p.health + p.max_health * 0.04 * dt)
	if p.resource_kind == 'rage':
		if not fighting:
			p.resource = maxf(0.0, p.resource - 3.0 * dt)
	elif realm.now - p.last_cast > 5.0:   # the "five-second rule"
		p.resource = minf(p.max_resource, p.resource + p.max_resource * (0.015 if fighting else 0.05) * dt)
	if not p.cast.is_empty() and realm.now >= p.cast.end:
		_finish_cast(p)
	p.swing = maxf(0.0, p.swing - dt)
	if p.auto:
		var t: Dictionary = realm.entities.get(p.target, {})
		if t.is_empty() or t.dead:
			p.auto = false
		elif p.swing <= 0.0 and p.cast.is_empty() and p.pos.distance_to(t.pos) <= Rules.MELEE_RANGE:
			var cls: Dictionary = realm.content.classes[p.job]
			p.swing = float(cls.swing)
			realm.event_near(p, {'type': 'anim', 'id': p.eid, 'clip': 'sword_slash_a' if realm.rng().randf() < 0.5 else 'sword_slash_b'})
			damage(p, t, Rules.melee_damage(cls, p.level) * realm.rng().randf_range(0.85, 1.15), 'melee')
