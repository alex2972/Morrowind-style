extends RealmSystem
## Talking to NPCs: greeting, quest offers / progress / turn-ins, and vendor trade (npc_vendor table).
## Every choice is re-validated (distance, quest state, gold, pack space) - the client only picks options.

func setup() -> void:
	realm.handle(Protocol.C_INTERACT, _on_interact)
	realm.handle(Protocol.C_DIALOGUE, _on_choice)

func _npc(id: String) -> Dictionary:
	var e: Dictionary = realm.entities.get(id, {})
	return e if not e.is_empty() and e.kind == 'npc' else {}

func _on_interact(p: Dictionary, d: Dictionary) -> void:
	var npc := _npc(str(d.get('id', '')))
	if p.dead or npc.is_empty() or npc.dead or npc.zone != p.zone:
		return
	if npc.template.hostile:
		p.target = npc.eid
		realm.combat.set_auto(p, true)
		return
	if p.pos.distance_to(npc.pos) > Rules.INTERACT_RANGE:
		realm.error(p, 'You are too far away.')
		return
	realm.ai.hold_for_talk(npc, p)
	realm.emit('talked', {'player': p, 'npc': npc})
	_show(p, npc, str(npc.template.greeting))

func _show(p: Dictionary, npc: Dictionary, text: String, choices: Array = []) -> void:
	var options := choices.duplicate()
	var t: Dictionary = npc.template
	if options.is_empty():
		var quests = realm.quests
		for qid in realm.content.quest_order:
			var q: Dictionary = realm.content.quests[qid]
			if q.turn_in_id == t.id and quests.ready(p, qid):
				options.append({'id': 'turnin:' + qid, 'label': q.title + '  (complete)', 'mark': '?'})
			elif q.giver_id == t.id and quests.available(p, qid):
				options.append({'id': 'quest:' + qid, 'label': q.title, 'mark': '!'})
			elif (q.giver_id == t.id or q.turn_in_id == t.id) and p.quests.get(qid, {}).get('state') == 'active':
				options.append({'id': 'progress:' + qid, 'label': q.title + '  (in progress)', 'mark': '·'})
		if not t.sells.is_empty() or not t.buys.is_empty():
			options.append({'id': 'trade', 'label': 'Let me see your wares.'})
		options.append({'id': 'bye', 'label': 'Farewell.'})
	realm.send(p, Protocol.S_DIALOGUE, {'npc': npc.eid, 'name': t.name, 'subtitle': t.subtitle, 'text': text, 'options': options})

func _reward_text(q: Dictionary) -> String:
	var parts: Array = ['%d experience' % int(q.reward_xp)]
	if int(q.reward_gold) > 0:
		parts.append('%d gold' % int(q.reward_gold))
	for item in q.reward_items:
		parts.append('%s x%d' % [realm.content.items[item].name, q.reward_items[item]])
	return ', '.join(parts)

func _on_choice(p: Dictionary, d: Dictionary) -> void:
	var npc := _npc(str(d.get('npc', '')))
	var choice := str(d.get('choice', ''))
	if npc.is_empty() or npc.template.hostile or p.dead:
		return
	if choice == 'bye' or p.pos.distance_to(npc.pos) > Rules.INTERACT_RANGE + 1.0:
		realm.send(p, Protocol.S_DIALOGUE, {'close': true})
		return
	var t: Dictionary = npc.template
	var verb := choice.get_slice(':', 0)
	var arg := choice.get_slice(':', 1) if choice.contains(':') else ''
	var q: Dictionary = realm.content.quests.get(arg, {})
	var quests = realm.quests
	match verb:
		'back':
			_show(p, npc, str(t.greeting))
		'quest':
			if q.get('giver_id') == t.id and quests.available(p, arg):
				_show(p, npc, '%s\n\n[i]Rewards: %s[/i]' % [q.offer_text, _reward_text(q)],
					[{'id': 'accept:' + arg, 'label': 'Accept'}, {'id': 'back', 'label': 'Not now.'}])
		'accept':
			if q.get('giver_id') == t.id and quests.accept(p, arg):
				_show(p, npc, q.progress_text)
		'progress':
			if p.quests.has(arg):
				_show(p, npc, q.progress_text, [{'id': 'back', 'label': 'Back.'}])
		'turnin':
			if q.get('turn_in_id') == t.id and quests.ready(p, arg):
				_show(p, npc, '%s\n\n[i]Rewards: %s[/i]' % [q.complete_text, _reward_text(q)],
					[{'id': 'complete:' + arg, 'label': 'Complete quest'}, {'id': 'back', 'label': 'Back.'}])
		'complete':
			if q.get('turn_in_id') == t.id and quests.complete(p, arg):
				_show(p, npc, str(t.greeting))
		'trade':
			_trade(p, npc, 'What do you need?')
		'buy':
			if arg in t.sells:
				var price := int(realm.content.items[arg].price)
				if p.gold < price:
					_trade(p, npc, 'You cannot afford that.')
				elif not realm.inventory.room_for(p, arg, 1):
					_trade(p, npc, 'Your pack is full.')
				else:
					realm.inventory.add_gold(p, -price)
					realm.inventory.add(p, arg, 1)
					_trade(p, npc, 'A fine choice.')
		'sell':
			if arg in t.buys and realm.inventory.remove(p, arg, 1):
				realm.inventory.add_gold(p, int(realm.content.items[arg].price))
				_trade(p, npc, 'I can use that.')

func _trade(p: Dictionary, npc: Dictionary, text: String) -> void:
	var t: Dictionary = npc.template
	var options: Array = []
	for item in t.sells:
		var it: Dictionary = realm.content.items[item]
		options.append({'id': 'buy:' + item, 'label': 'Buy %s  (%d gold)' % [it.name, it.price], 'icon': it.icon})
	for item in t.buys:
		var have: int = realm.inventory.count(p, item)
		if have > 0:
			var it: Dictionary = realm.content.items[item]
			options.append({'id': 'sell:' + item, 'label': 'Sell %s x%d  (%d gold each)' % [it.name, have, it.price], 'icon': it.icon})
	options.append({'id': 'back', 'label': 'Back.'})
	_show(p, npc, '%s\n\n[i]Your purse: %d gold[/i]' % [text, p.gold], options)
