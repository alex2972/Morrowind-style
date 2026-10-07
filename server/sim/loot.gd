extends RealmSystem
## Kill rewards from the `npc_loot` table and the template's gold range. Gold is split between credited
## party members; items go to one looter (round-robin in a party) and straight into their pack.

func setup() -> void:
	realm.on('npc_killed', _on_kill)

func _on_kill(e: Dictionary) -> void:
	var npc: Dictionary = e.npc
	var credited: Array = realm.party.credited(e.tag, npc)
	if credited.is_empty():
		return
	var rng := realm.rng()
	var t: Dictionary = npc.template
	var gold := rng.randi_range(int(t.gold_min), int(t.gold_max))
	if gold > 0:
		var each := maxi(1, floori(gold / float(credited.size())))
		for p in credited:
			realm.inventory.add_gold(p, each)
			realm.tell(p, 'You receive %d gold.' % each)
	var looter: Dictionary = realm.party.looter(credited)
	for roll in t.loot:
		if rng.randf() >= float(roll.chance):
			continue
		var item := str(roll.item_id)
		var n := rng.randi_range(int(roll.count_min), int(roll.count_max))
		var name := str(realm.content.items[item].name)
		if realm.inventory.add(looter, item, n):
			realm.tell(looter, 'You loot: %s%s.' % [name, ' x%d' % n if n > 1 else ''])
		else:
			realm.tell(looter, 'Your pack is full; you leave the %s behind.' % name)
