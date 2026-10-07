extends RealmSystem
## Parties: invite / accept / decline / leave, a leader, party chat, member vitals for the party frames,
## and shared credit - members within Rules.PARTY_RANGE of a kill share its XP (with a group bonus), gold
## and quest progress; item loot goes round-robin.

const INVITE_SECONDS := 60.0

var parties: Dictionary = {}    ## party id -> {id, leader (eid), members: [eid], loot_turn}
var _next_id := 1

func setup() -> void:
	realm.handle(Protocol.C_PARTY_RESPOND, func(p: Dictionary, d: Dictionary) -> void: respond(p, bool(d.get('accept', false))))

func player_joined(p: Dictionary, _data: Dictionary) -> void:
	p.party = 0
	p.invite = {}

func player_left(p: Dictionary) -> void:
	leave(p)

func _party(p: Dictionary) -> Dictionary:
	return parties.get(p.party, {})

func members(p: Dictionary) -> Array:
	var party := _party(p)
	if party.is_empty():
		return [p]
	return party.members.map(func(eid: String) -> Dictionary: return realm.entities.get(eid, {})).filter(
		func(e: Dictionary) -> bool: return not e.is_empty())

func same_party(a: Dictionary, b: Dictionary) -> bool:
	return a.party != 0 and a.party == b.get('party', -1)

func credited(tag: String, npc: Dictionary) -> Array:
	## Who shares a kill: the tagger, or every living party member near the kill.
	var tagger: Dictionary = realm.entities.get(tag, {})
	if tagger.is_empty() or tagger.kind != 'player':
		return []
	var out: Array = []
	for m in members(tagger):
		if m.eid == tagger.eid or (not m.dead and m.zone == npc.zone and m.pos.distance_to(npc.pos) <= Rules.PARTY_RANGE):
			out.append(m)
	return out

func looter(credited_players: Array) -> Dictionary:
	var party := _party(credited_players[0])
	if party.is_empty() or credited_players.size() == 1:
		return credited_players[0]
	party.loot_turn = (int(party.loot_turn) + 1) % credited_players.size()
	return credited_players[party.loot_turn]

func vitals(p: Dictionary) -> Array:
	## Party frames: every other member's health and resource, even out of view.
	var out: Array = []
	for m in members(p):
		if m.eid != p.eid:
			out.append([m.eid, m.name, m.level, m.health, m.max_health, m.resource, m.max_resource, m.resource_kind, m.dead])
	return out

# ---------------------------------------------------------------- invites and membership

func invite(p: Dictionary, target_name: String) -> void:
	var target: Dictionary = realm.player_by_name(target_name) if target_name != '' else realm.entities.get(p.target, {})
	if target.is_empty() or target.kind != 'player':
		realm.error(p, 'Invite whom? Target a player or type /invite <name>.')
		return
	if target.eid == p.eid:
		realm.error(p, 'You cannot invite yourself.')
		return
	var party := _party(p)
	if not party.is_empty() and party.leader != p.eid:
		realm.error(p, 'Only the party leader can invite.')
		return
	if not party.is_empty() and party.members.size() >= Rules.PARTY_MAX:
		realm.error(p, 'Your party is full.')
		return
	if target.party != 0:
		realm.error(p, '%s is already in a party.' % target.name)
		return
	target.invite = {'from': p.eid, 'until': realm.now + INVITE_SECONDS}
	realm.send(target, Protocol.S_EVENT, {'type': 'party_invite', 'from': p.name})
	realm.tell(p, 'You invite %s to your party.' % target.name)

func respond(p: Dictionary, accept: bool) -> void:
	var inv: Dictionary = p.invite
	p.invite = {}
	var host: Dictionary = realm.entities.get(inv.get('from', ''), {})
	if inv.is_empty() or realm.now > float(inv.until) or host.is_empty():
		realm.error(p, 'You have no pending invitation.')
		return
	if not accept:
		realm.tell(host, '%s declines your invitation.' % p.name)
		return
	if p.party != 0:
		leave(p)
	var party := _party(host)
	if party.is_empty():
		party = {'id': _next_id, 'leader': host.eid, 'members': [host.eid], 'loot_turn': 0}
		parties[_next_id] = party
		host.party = _next_id
		_next_id += 1
	if party.members.size() >= Rules.PARTY_MAX:
		realm.error(p, 'That party is full.')
		return
	party.members.append(p.eid)
	p.party = party.id
	_say_system(party, '%s joins the party.' % p.name)
	_send(party)

func leave(p: Dictionary) -> void:
	var party := _party(p)
	if party.is_empty():
		return
	party.members.erase(p.eid)
	p.party = 0
	realm.send(p, Protocol.S_PARTY, {})
	_say_system(party, '%s leaves the party.' % p.name)
	realm.tell(p, 'You leave the party.')
	if party.members.size() <= 1:
		for eid in party.members:
			var last: Dictionary = realm.entities.get(eid, {})
			if not last.is_empty():
				last.party = 0
				realm.send(last, Protocol.S_PARTY, {})
				realm.tell(last, 'Your party has disbanded.')
		parties.erase(party.id)
		return
	if party.leader == p.eid:
		party.leader = party.members[0]
	_send(party)

func member_changed(p: Dictionary) -> void:
	var party := _party(p)
	if not party.is_empty():
		_send(party)

func _send(party: Dictionary) -> void:
	var list: Array = []
	for eid in party.members:
		var m: Dictionary = realm.entities.get(eid, {})
		if not m.is_empty():
			list.append({'eid': eid, 'name': m.name, 'level': m.level, 'class': m.job})
	for eid in party.members:
		var m: Dictionary = realm.entities.get(eid, {})
		if not m.is_empty():
			realm.send(m, Protocol.S_PARTY, {'leader': party.leader, 'members': list})

# ---------------------------------------------------------------- party chat

func say(p: Dictionary, text: String) -> void:
	var party := _party(p)
	if party.is_empty():
		realm.error(p, 'You are not in a party.')
		return
	if text == '':
		return
	for m in members(p):
		realm.send(m, Protocol.S_EVENT, {'type': 'chat', 'channel': 'Party', 'text': text, 'from': p.name})

func _say_system(party: Dictionary, text: String) -> void:
	for eid in party.members:
		var m: Dictionary = realm.entities.get(eid, {})
		if not m.is_empty():
			realm.send(m, Protocol.S_EVENT, {'type': 'chat', 'channel': 'Party', 'text': text})
