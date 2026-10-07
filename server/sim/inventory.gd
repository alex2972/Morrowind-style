extends RealmSystem
## The backpack: Rules.PACK_SLOTS slots, each null or [item_id, count] up to the item's stack size, plus
## gold. Every change goes through add()/remove(), which are all-or-nothing, so items can't be duplicated or
## lost half-way. Also handles using items (tonics) and rearranging slots.

func setup() -> void:
	realm.handle(Protocol.C_USE_ITEM, _on_use)
	realm.handle(Protocol.C_SWAP_SLOTS, _on_swap)

func player_joined(p: Dictionary, data: Dictionary) -> void:
	p.gold = int(data.row.gold)
	p.pack = []
	p.pack.resize(Rules.PACK_SLOTS)
	for it in data.items:
		var slot := int(it.slot)
		if it.container == 'pack' and slot >= 0 and slot < Rules.PACK_SLOTS and realm.content.items.has(it.item_id):
			p.pack[slot] = [str(it.item_id), int(it.count)]

func write_save(p: Dictionary, state: Dictionary) -> void:
	state.gold = p.gold
	state.pack = p.pack

func write_sheet(p: Dictionary, sheet: Dictionary) -> void:
	sheet.gold = p.gold
	sheet.pack = p.pack

func count(p: Dictionary, item: String) -> int:
	var n := 0
	for s in p.pack:
		if s != null and s[0] == item:
			n += s[1]
	return n

func room_for(p: Dictionary, item: String, n: int) -> bool:
	var stack := int(realm.content.items[item].stack)
	var space := 0
	for s in p.pack:
		if s == null:
			space += stack
		elif s[0] == item:
			space += stack - s[1]
	return space >= n

## Adds n of item, filling existing stacks first. All or nothing.
func add(p: Dictionary, item: String, n: int) -> bool:
	if n <= 0 or not realm.content.items.has(item) or not room_for(p, item, n):
		return false
	var stack := int(realm.content.items[item].stack)
	for s in p.pack:
		if n > 0 and s != null and s[0] == item and s[1] < stack:
			var put := mini(n, stack - s[1])
			s[1] += put
			n -= put
	for i in p.pack.size():
		if n > 0 and p.pack[i] == null:
			var put := mini(n, stack)
			p.pack[i] = [item, put]
			n -= put
	p.sheet_dirty = true
	return true

## Removes n of item. All or nothing.
func remove(p: Dictionary, item: String, n: int) -> bool:
	if n <= 0 or count(p, item) < n:
		return false
	for i in range(p.pack.size() - 1, -1, -1):
		var s: Variant = p.pack[i]
		if n > 0 and s != null and s[0] == item:
			var take := mini(n, s[1])
			s[1] -= take
			n -= take
			if s[1] <= 0:
				p.pack[i] = null
	p.sheet_dirty = true
	return true

func add_gold(p: Dictionary, amount: int) -> void:
	p.gold = maxi(0, p.gold + amount)
	p.sheet_dirty = true

func _on_swap(p: Dictionary, d: Dictionary) -> void:
	var a := int(d.get('a', -1))
	var b := int(d.get('b', -1))
	if a < 0 or b < 0 or a >= Rules.PACK_SLOTS or b >= Rules.PACK_SLOTS or a == b:
		return
	var tmp: Variant = p.pack[a]
	p.pack[a] = p.pack[b]
	p.pack[b] = tmp
	p.sheet_dirty = true

func _on_use(p: Dictionary, d: Dictionary) -> void:
	var item := str(d.get('item', ''))
	if d.has('slot'):
		var slot := int(d.slot)
		if slot >= 0 and slot < Rules.PACK_SLOTS and p.pack[slot] != null:
			item = p.pack[slot][0]
	var def: Dictionary = realm.content.items.get(item, {})
	if p.dead or def.is_empty() or def.use_effect.is_empty() or count(p, item) <= 0:
		return
	if realm.now < p.potion:
		realm.error(p, 'Tonics are not ready yet.')
		return
	var use: Dictionary = def.use_effect
	if use.has('mana') and p.resource_kind != 'mana':
		realm.error(p, 'You have no mana to restore.')
		return
	remove(p, item, 1)
	p.potion = realm.now + Rules.POTION_COOLDOWN
	realm.event_near(p, {'type': 'anim', 'id': p.eid, 'clip': 'drink'})
	if use.has('heal'):
		realm.combat.heal(p, p, float(use.heal), item)
	if use.has('mana'):
		p.resource = minf(p.max_resource, p.resource + float(use.mana))
		realm.tell(p, 'You restore %d mana.' % int(use.mana), 'Combat')
