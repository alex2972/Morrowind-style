extends RealmSystem
## Tells each client what it can see. Interest comes from the zone's grid (VIEW_RADIUS around the player).
## Reliable S_APPEAR / S_VANISH messages carry an actor's static info (name, race, quest marker...) once;
## the unreliable state packet carries only actors whose dynamic state changed since we last sent it, plus a
## staggered full refresh so a lost packet heals within a second. The owner's vitals ride in every packet,
## and the character sheet is sent reliably whenever a system marks it dirty.

const VIEW_RADIUS := 120.0
const REFRESH_EVERY := 10        ## state packets between unconditional resends of an actor

var _packets := 0

func player_joined(p: Dictionary, _data: Dictionary) -> void:
	p.view = {}

func tick(_dt: float) -> void:
	if realm.tick_count % Protocol.SNAPSHOT_EVERY != 0:
		return
	_packets += 1
	for p in realm.players.values():
		_update(p)

static func dynamic(e: Dictionary) -> Array:
	var d := [e.pos, e.yaw, e.clip, e.rate, e.health, e.max_health, e.level, e.dead,
		e.cast.get('ability', '') if not e.cast.is_empty() else '', e.target]
	if e.kind == 'player':
		d.append_array([e.resource, e.max_resource, e.resource_kind])
	return d

func info(viewer: Dictionary, e: Dictionary) -> Dictionary:
	if e.kind == 'player':
		return {'kind': 'player', 'name': e.name, 'sex': e.sex, 'race': e.race, 'skin': e.skin, 'class': e.job,
			'hostile': false, 'subtitle': '', 'party': realm.party.same_party(viewer, e)}
	var t: Dictionary = e.template
	return {'kind': 'npc', 'name': t.name, 'sex': t.sex, 'race': t.race_id, 'skin': int(t.skin), 'hostile': t.hostile,
		'role': t.role, 'subtitle': t.subtitle, 'mark': realm.quests.mark_for(viewer, str(t.id))}

func _update(p: Dictionary) -> void:
	var zone := realm.zone_of(p)
	var seen := {}
	var actors: Array = []
	for e in zone.nearby(p.pos, VIEW_RADIUS):
		if e.eid == p.eid:
			continue
		seen[e.eid] = true
		var v: Dictionary = p.view.get(e.eid, {})
		var i := info(p, e)
		var h := i.hash()
		if v.is_empty() or v.info != h:
			realm.send(p, Protocol.S_APPEAR, {'id': e.eid, 'info': i})
			v = {'info': h, 'dyn': [], 'fresh': 3 if v.is_empty() else v.fresh}
			p.view[e.eid] = v
		var d := dynamic(e)
		if v.fresh > 0 or d != v.dyn or (e.eid.hash() + _packets) % REFRESH_EVERY == 0:
			v.fresh = maxi(v.fresh - 1, 0)
			v.dyn = d
			actors.append([e.eid] + d)
	for eid in p.view.keys():
		if not seen.has(eid):
			p.view.erase(eid)
			realm.send(p, Protocol.S_VANISH, {'id': eid})
	if p.sheet_dirty:
		p.sheet_dirty = false
		realm.send(p, Protocol.S_SHEET, realm.sheet(p))
	var me: Dictionary = realm.combat.vitals(p)
	me.party = realm.party.vitals(p)
	realm.gateway.send_state(p.peer, me, actors)
