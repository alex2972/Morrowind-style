extends RealmSystem
## Experience and character levels. Kills give XP to everyone credited (the tagger and their party members
## nearby, split with a group bonus); quests call give_xp directly.

func setup() -> void:
	realm.on('npc_killed', _on_kill)

func write_save(p: Dictionary, state: Dictionary) -> void:
	state.level = p.level
	state.xp = p.xp

func write_sheet(p: Dictionary, sheet: Dictionary) -> void:
	sheet.level = p.level
	sheet.xp = p.xp
	sheet.xp_next = Rules.xp_to_next(p.level)

func _on_kill(e: Dictionary) -> void:
	var npc: Dictionary = e.npc
	var credited: Array = realm.party.credited(e.tag, npc)
	var share := Rules.party_share(credited.size())
	for p in credited:
		give_xp(p, int(round(Rules.kill_xp(p.level, npc.level, float(npc.template.xp_factor)) * share)), npc.name)

func give_xp(p: Dictionary, amount: int, from: String) -> void:
	if amount <= 0 or p.level >= Rules.MAX_LEVEL:
		return
	p.xp += amount
	realm.send(p, Protocol.S_EVENT, {'type': 'xp', 'amount': amount, 'from': from})
	while p.level < Rules.MAX_LEVEL and p.xp >= Rules.xp_to_next(p.level):
		p.xp -= Rules.xp_to_next(p.level)
		p.level += 1
		realm.combat.refresh_stats(p)
		p.health = p.max_health
		if p.resource_kind != 'rage':
			p.resource = p.max_resource
		realm.event_near(p, {'type': 'level', 'id': p.eid, 'level': p.level})
		realm.tell(p, 'You have reached level %d!' % p.level)
		for aid in realm.content.classes[p.job].abilities:
			if int(realm.content.abilities[aid].level) == p.level:
				realm.tell(p, 'You have learned a new ability: %s.' % realm.content.abilities[aid].name)
		realm.party.member_changed(p)
	if p.level >= Rules.MAX_LEVEL:
		p.xp = 0
	p.sheet_dirty = true
	p.save_due = true
