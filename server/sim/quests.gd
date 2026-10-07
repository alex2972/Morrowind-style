extends RealmSystem
## Quests from the `quests` / `quest_objectives` / `quest_items` tables. Each objective is data:
##   kill <npc template> x count      - progress counts credited kills (party members share them)
##   talk <npc template>              - progress when the player talks to that NPC
##   collect <item> x count           - satisfied while the pack holds that many
##   deliver <item> x count           - like collect, and the items are handed over on completion
## Per-character state: p.quests[id] = {state: 'active'|'done', progress: [one counter per objective]}.

func setup() -> void:
	realm.on('npc_killed', _on_kill)
	realm.on('talked', _on_talk)
	realm.handle(Protocol.C_ABANDON_QUEST, func(p: Dictionary, d: Dictionary) -> void: abandon(p, str(d.get('quest', ''))))

func player_joined(p: Dictionary, data: Dictionary) -> void:
	p.quests = {}
	for qid in data.quests:
		if realm.content.quests.has(qid):
			p.quests[qid] = data.quests[qid]

func write_save(p: Dictionary, state: Dictionary) -> void:
	state.quests = p.quests

func write_sheet(p: Dictionary, sheet: Dictionary) -> void:
	var entries: Array = []
	var done: Array = []
	for qid in realm.content.quest_order:
		var st: Dictionary = p.quests.get(qid, {})
		var q: Dictionary = realm.content.quests[qid]
		if st.get('state') == 'done':
			done.append(q.title)
		elif st.get('state') == 'active':
			var objectives: Array = []
			for o in q.objectives:
				objectives.append({'label': o.label, 'have': _have(p, qid, o), 'need': int(o.count)})
			entries.append({'id': qid, 'title': q.title, 'text': q.progress_text, 'objectives': objectives, 'ready': ready(p, qid)})
	sheet.quests = entries
	sheet.quests_done = done

# ---------------------------------------------------------------- state queries

func _have(p: Dictionary, qid: String, o: Dictionary) -> int:
	if o.type in ['collect', 'deliver']:
		return mini(realm.inventory.count(p, o.target), int(o.count))
	var progress: Array = p.quests[qid].progress
	return int(progress[o.idx]) if o.idx < progress.size() else 0

func available(p: Dictionary, qid: String) -> bool:
	var q: Dictionary = realm.content.quests[qid]
	if p.quests.has(qid) or p.level < int(q.level):
		return false
	return q.requires_id == '' or p.quests.get(q.requires_id, {}).get('state') == 'done'

func ready(p: Dictionary, qid: String) -> bool:
	if p.quests.get(qid, {}).get('state') != 'active':
		return false
	for o in realm.content.quests[qid].objectives:
		if _have(p, qid, o) < int(o.count):
			return false
	return true

func mark_for(p: Dictionary, template_id: String) -> String:
	## The marker over an NPC's head for this player: '?' turn-in ready, '!' quest available.
	var mark := ''
	for qid in realm.content.quest_order:
		var q: Dictionary = realm.content.quests[qid]
		if q.turn_in_id == template_id and ready(p, qid):
			return '?'
		if q.giver_id == template_id and available(p, qid):
			mark = '!'
	return mark

# ---------------------------------------------------------------- changes

func accept(p: Dictionary, qid: String) -> bool:
	if not available(p, qid):
		return false
	var q: Dictionary = realm.content.quests[qid]
	for item in q.start_items:
		if not realm.inventory.room_for(p, item, q.start_items[item]):
			realm.error(p, 'Your pack is full.')
			return false
	for item in q.start_items:
		realm.inventory.add(p, item, q.start_items[item])
	var progress: Array = []
	progress.resize(q.objectives.size())
	progress.fill(0)
	p.quests[qid] = {'state': 'active', 'progress': progress}
	realm.tell(p, 'Quest accepted: %s' % q.title)
	p.sheet_dirty = true
	p.save_due = true
	return true

func complete(p: Dictionary, qid: String) -> bool:
	if not ready(p, qid):
		return false
	var q: Dictionary = realm.content.quests[qid]
	# hand over delivered items first, so the reward can use the freed slots
	for o in q.objectives:
		if o.type == 'deliver':
			realm.inventory.remove(p, o.target, int(o.count))
	for item in q.reward_items:
		if not realm.inventory.room_for(p, item, q.reward_items[item]):
			for o in q.objectives:
				if o.type == 'deliver':
					realm.inventory.add(p, o.target, int(o.count))
			realm.error(p, 'Make room in your pack for the reward first.')
			return false
	for item in q.reward_items:
		realm.inventory.add(p, item, q.reward_items[item])
	realm.inventory.add_gold(p, int(q.reward_gold))
	p.quests[qid] = {'state': 'done', 'progress': []}
	realm.tell(p, 'Quest complete: %s' % q.title)
	realm.progression.give_xp(p, int(q.reward_xp), q.title)
	p.sheet_dirty = true
	p.save_due = true
	return true

func abandon(p: Dictionary, qid: String) -> void:
	if p.quests.get(qid, {}).get('state') != 'active':
		return
	var q: Dictionary = realm.content.quests[qid]
	for item in q.start_items:
		realm.inventory.remove(p, item, mini(realm.inventory.count(p, item), q.start_items[item]))
	p.quests.erase(qid)
	realm.tell(p, 'Quest abandoned: %s' % q.title)
	p.sheet_dirty = true
	p.save_due = true

func _advance(p: Dictionary, type: String, target: String) -> void:
	for qid in p.quests:
		var st: Dictionary = p.quests[qid]
		if st.state != 'active':
			continue
		var q: Dictionary = realm.content.quests[qid]
		for o in q.objectives:
			if o.type != type or o.target != target or _have(p, qid, o) >= int(o.count):
				continue
			while st.progress.size() <= o.idx:
				st.progress.append(0)
			st.progress[o.idx] = int(st.progress[o.idx]) + 1
			realm.tell(p, '%s: %d/%d' % [o.label, st.progress[o.idx], o.count])
			if ready(p, qid):
				realm.tell(p, 'Quest ready to turn in: %s' % q.title)
			p.sheet_dirty = true

func _on_kill(e: Dictionary) -> void:
	for p in realm.party.credited(e.tag, e.npc):
		_advance(p, 'kill', str(e.npc.template.id))

func _on_talk(e: Dictionary) -> void:
	_advance(e.player, 'talk', str(e.npc.template.id))
