extends SceneTree
## Headless end-to-end check of the realm and the client through the real network code (an offline realm in
## process, the game client, and a protocol-only bot): database and content, accounts, character creation,
## entering the world, interest management, dialogue and quests, combat, XP and levels, parties and shared
## credit, content hot-reload, death and release, persistence across logout and a fresh sign-in.
##   Godot --headless --fixed-fps 60 --path . --script res://tools/verify_online.gd

const SAVE := 'user://verify_realm'
const BotClient = preload('res://tools/bot_client.gd')

var failures := 0
var main: Node
var session: Node
var realm: Realm
var rosters: Array = []

func check(ok: bool, message: String) -> void:
	print(('PASS ' if ok else 'FAIL ') + message)
	if not ok:
		failures += 1

func _init() -> void:
	call_deferred('run')

func frames(n: int) -> void:
	for i in n:
		await physics_frame

func wait_for(condition: Callable, seconds := 10.0) -> bool:
	var t := 0
	while not condition.call() and t < seconds * 60:
		await physics_frame
		t += 1
	return condition.call()

func wipe(path: String) -> void:
	var dir := DirAccess.open(path)
	if dir == null:
		return
	for sub in dir.get_directories():
		wipe(path.path_join(sub))
	for f in dir.get_files():
		dir.remove(f)
	DirAccess.remove_absolute(path)

func me_server() -> Dictionary:
	return realm.players.values()[0] if not realm.players.is_empty() else {}

func teleport(p: Dictionary, pos: Vector3, yaw := 0.0) -> void:
	pos.y = realm.zone_of(p).ground(pos.x, pos.z) + 0.05
	realm.movement.teleport(p, pos, yaw)
	await frames(20)

func say(choice: String) -> void:
	var before: Dictionary = session.dialogue
	session.choose(choice)
	await wait_for(func() -> bool: return session.dialogue != before, 3.0)

func run() -> void:
	wipe(ProjectSettings.globalize_path(SAVE))
	main = load('res://scenes/main.tscn').instantiate()
	root.add_child(main)
	await frames(10)
	session = main.session
	session.roster_received.connect(func(ok: bool, msg: String, list: Array) -> void: rosters.append([ok, msg, list]))
	var t0 := Time.get_ticks_msec()
	main.start_offline(SAVE)
	realm = main.realm
	check(await wait_for(func() -> bool: return not rosters.is_empty(), 20.0) and rosters[-1][0], 'offline account created and signed in (%d ms)' % (Time.get_ticks_msec() - t0))

	# Database and content
	check(FileAccess.file_exists(SAVE.path_join('veyr.db')), 'SQLite database created')
	check(int(realm.db.value('SELECT COUNT(*) FROM npc_templates')) == 11 and int(realm.db.value('SELECT COUNT(*) FROM spawns')) == 20 and int(realm.db.value('SELECT COUNT(*) FROM path_points')) == 7, 'content tables seeded')
	check(int(realm.db.value("SELECT is_admin FROM accounts WHERE username = 'offline'")) == 1, 'offline account is a realm admin')
	check(Catalog.races.has('high_elf') and Catalog.items.has('health_tonic'), 'client received the display catalog')
	check(not Catalog.items.health_tonic.has('price') and not Catalog.classes.mage.has('health_base'), 'catalog carries no rules (prices, stats)')

	# Character creation (bad then good)
	rosters.clear()
	session.create_character({'name': 'x', 'sex': 'female', 'race': 'high_elf', 'skin': 1, 'class': 'mage'})
	await wait_for(func() -> bool: return not rosters.is_empty())
	check(rosters[-1][2].is_empty(), 'invalid character rejected: ' + rosters[-1][1])
	rosters.clear()
	session.create_character({'name': 'Aelinor', 'sex': 'female', 'race': 'high_elf', 'skin': 2, 'class': 'mage'})
	await wait_for(func() -> bool: return not rosters.is_empty())
	check(rosters[-1][2].size() == 1 and rosters[-1][2][0].name == 'Aelinor', 'character created: ' + rosters[-1][1])
	var slot: int = rosters[-1][2][0].id

	# Enter the world
	session.enter(slot)
	check(await wait_for(func() -> bool: return session.in_world and not session.me.is_empty() and not session.sheet.is_empty()), 'entered the world')
	var player: CharacterBody3D = main.world.player
	check(player.global_position.distance_to(realm.zones.veyr.spawn_point()) < 1.0, 'spawned on the harbour pier')
	check(player.body_model == 'female', 'body set from identity')
	check(session.hotbar[1] == 'fireball' and session.ui != null, 'action bar built from the sheet')
	check(session.item_count('health_tonic') == 2 and session.item_count('mana_tonic') == 1, 'starting items in the pack')
	var hud: CanvasLayer = main.world.hud
	hud._open_panel('Inventory')
	await frames(5)
	var inv: Control = hud.inventory_view
	check(inv != null and inv.visible and inv.slots.size() == 28 and inv.slots[0].item == 'health_tonic' and inv.slots[0].count == 2 and inv.slots[0].icon != null, 'inventory grid: 28 slots, tonic icon and count')
	inv.use_slot(0)
	await wait_for(func() -> bool: return session.item_count('health_tonic') == 1, 2.0)
	check(session.item_count('health_tonic') == 1, 'clicking a slot uses the item')
	session.send(Protocol.C_SWAP_SLOTS, {'a': 0, 'b': 5})
	await wait_for(func() -> bool: return inv.slots[5].item == 'health_tonic', 2.0)
	check(inv.slots[5].item == 'health_tonic' and inv.slots[0].item == '', 'dragging swaps slots')
	session.send(Protocol.C_SWAP_SLOTS, {'a': 0, 'b': 5})
	hud._close_panel()
	for e in realm.entities.values():
		if e.kind == 'npc' and e.pos.y < -0.3:
			print('  npc %s is under water at %s' % [e.eid, e.pos])
	check(not session.actors.has('cultist_1'), 'interest management: distant cultists are not sent')

	# Talk to the harbourmaster and accept the first quest
	var hm: Dictionary = realm.entities.harbourmaster
	await teleport(me_server(), hm.pos + Vector3(0, 0, 2.5))
	check(await wait_for(func() -> bool: return session.actors.has('harbourmaster')), 'harbourmaster visible to the client')
	check(session.actors.harbourmaster.marker.text == '!', 'harbourmaster shows a quest marker (sent by the realm)')
	session.set_target('harbourmaster')   # wandering harbour folk may pass closer
	session.interact()
	check(await wait_for(func() -> bool: return not session.dialogue.is_empty()), 'dialogue opened')
	await say('quest:marsh_trouble')
	await say('accept:marsh_trouble')
	await frames(10)
	check(session.sheet.quests.size() == 1 and session.sheet.quests[0].id == 'marsh_trouble', 'quest accepted')

	# Combat: fireball a bandit until it dies
	var bandit: Dictionary = realm.entities.bandit_1
	await teleport(me_server(), bandit.pos + Vector3(0, 0, 14))
	await wait_for(func() -> bool: return session.actors.has('bandit_1'))
	session.set_target('bandit_1')
	await frames(5)
	check(session.player().wow_controls and Input.mouse_mode == Input.MOUSE_MODE_VISIBLE, 'WoW controls: free cursor in the world')
	await teleport(me_server(), bandit.pos + Vector3(0, 0, 14), PI)   # back turned to the bandit
	session.use_slot(1)
	await wait_for(func() -> bool: return session.ui.error_label.text.contains('facing'), 2.0)
	check(session.ui.error_label.text.contains('facing') and session.me.get('cast', {}).is_empty(), 'cannot cast at an enemy behind you')
	await teleport(me_server(), bandit.pos + Vector3(0, 0, 14))
	var hp0: float = bandit.health
	session.use_slot(1)
	await wait_for(func() -> bool: return not session.me.get('cast', {}).is_empty(), 2.0)
	check(not session.me.cast.is_empty(), 'casting Fireball (cast bar)')
	if session.me.cast.is_empty():
		print('  last error: ', session.ui.error_label.text)
	await wait_for(func() -> bool: return bandit.health < hp0, 4.0)
	check(bandit.health < hp0, 'Fireball hit the bandit (%d -> %d)' % [hp0, bandit.health])
	check(bandit.state == 'chase', 'bandit aggroed on the attacker')
	for i in 12:
		if bandit.dead:
			break
		await wait_for(func() -> bool: return session.me.gcd <= 0.0 and session.me.cast.is_empty(), 3.0)
		session.use_slot(1)
		await frames(150)
	check(bandit.dead, 'bandit killed')
	await frames(10)
	check(int(session.sheet.xp) > 0 or int(session.sheet.level) > 1, 'experience gained (%d xp)' % int(session.sheet.xp))
	check(int(session.sheet.quests[0].objectives[0].have) == 1, 'quest kill counted')

	# A second player (protocol bot): visibility, party, shared credit
	var bot: Node = BotClient.new()
	bot.name = 'Bot'
	root.add_child(bot)
	bot.start('127.0.0.1', realm.port)
	await wait_for(func() -> bool: return bot.connected, 5.0)
	bot.hello('botuser', 'botpassword1', true)
	await wait_for(func() -> bool: return bot.auth_ok, 10.0)
	bot.send(Protocol.C_CREATE_CHARACTER, {'name': 'Brannoc', 'sex': 'male', 'race': 'dark_elf', 'skin': 1, 'class': 'warrior'})
	await wait_for(func() -> bool: return not bot.roster.is_empty())
	if bot.roster.is_empty():
		print('  bot: connected=%s auth=%s message=%s' % [bot.connected, bot.auth_ok, bot.auth_message])
	bot.send(Protocol.C_ENTER, {'id': bot.roster[0].id})
	check(await wait_for(func() -> bool: return bot.eid != ''), 'second player entered the world')
	var bp: Dictionary = realm.entities[bot.eid]
	await teleport(bp, me_server().pos + Vector3(2, 0, 0))
	check(await wait_for(func() -> bool: return session.actors.has(bot.eid)), 'the other player is visible to the client')
	check(session.actors.has(bot.eid) and session.actors[bot.eid].category() == 'player', 'shown as a player')
	session.send_chat('/invite Brannoc')
	check(await wait_for(func() -> bool: return not bot.had_event('party_invite').is_empty()), 'party invite delivered')
	bot.send(Protocol.C_PARTY_RESPOND, {'accept': true})
	check(await wait_for(func() -> bool: return session.party.get('members', []).size() == 2), 'party formed (client sees 2 members)')
	await wait_for(func() -> bool: return session.me.get('party', []).size() == 1)
	check(session.me.get('party', []).size() == 1, 'party frame vitals for the other member')
	var bandit2: Dictionary = realm.entities.bandit_2
	var bot_xp := int(bp.xp)
	realm.combat.damage(me_server(), bandit2, 99999.0, 'melee')
	await frames(10)
	check(bandit2.dead and int(bp.xp) > bot_xp, 'party member nearby shares the kill XP')
	check(int(session.sheet.quests[0].objectives[0].have) == 2, 'quest kill counted for the party kill')

	# Turn in (the remaining kills are credited directly to keep the test short)
	me_server().quests.marsh_trouble.progress = [5]
	me_server().sheet_dirty = true
	await teleport(me_server(), hm.pos + Vector3(0, 0, 2.5))
	await wait_for(func() -> bool: return session.actors.has('harbourmaster') and session.actors.harbourmaster.marker.text == '?')
	check(session.actors.harbourmaster.marker.text == '?', 'turn-in marker shown')
	var level0 := int(session.sheet.level)
	var xp0 := int(session.sheet.xp)
	session.set_target('harbourmaster')
	session.interact()
	await wait_for(func() -> bool: return not session.dialogue.is_empty())
	await say('turnin:marsh_trouble')
	await say('complete:marsh_trouble')
	await frames(20)
	check(session.sheet.quests_done.has('Trouble in the Marsh'), 'quest completed')
	check(int(session.sheet.level) > level0 or int(session.sheet.xp) >= xp0 + 250, 'quest XP awarded (level %d, %d xp)' % [int(session.sheet.level), int(session.sheet.xp)])
	check(session.item_count('health_tonic') >= 4, 'quest reward items received')
	check(session.actors.harbourmaster.marker.text == '!', 'follow-up quest offered')

	# Content hot reload (an admin edits the database, then /reload)
	realm.db.exec("UPDATE npc_templates SET health = 222 WHERE id = 'marsh_bandit'")
	session.send_chat('/reload')
	await wait_for(func() -> bool: return realm.entities.has('bandit_3') and realm.entities.bandit_3.max_health == 222.0, 3.0)
	check(realm.entities.has('bandit_3') and realm.entities.bandit_3.max_health == 222.0, 'content reloaded from the database without a restart')
	realm.db.exec("UPDATE npc_templates SET health = 110 WHERE id = 'marsh_bandit'")

	# Death and release
	realm.combat.damage(realm.entities.bandit_4, me_server(), 99999.0, 'melee')
	await wait_for(func() -> bool: return session.me.dead and player.dead, 3.0)
	check(session.me.dead and player.dead, 'player died')
	session.release_spirit()
	await wait_for(func() -> bool: return not session.me.dead and not player.dead, 3.0)
	await frames(20)
	check(not session.me.dead and player.global_position.distance_to(realm.zones.veyr.spawn_point()) < 1.5, 'released at the harbour')

	# Doors: the realm only moves a player through a door they stand at
	main.world.hud.set_interface_open(false)   # the dialogues above left the cursor mode on
	session.send(Protocol.C_USE_DOOR, {'door': 'tavern_enter'})
	await frames(20)
	check(Doors.interior_at(me_server().pos) == '', 'tavern door refused from the pier')
	await teleport(me_server(), Vector3(-11.4, 0, 48.6))
	player.rotation.y = PI / 2
	player.head.rotation.x = 0.0
	await wait_for(func() -> bool: return main.world.doors.focused == 'tavern_enter', 3.0)
	check(main.world.doors.focused == 'tavern_enter' and main.world.doors.use_focused(), 'E at the tavern door')
	await wait_for(func() -> bool: return Doors.interior_at(player.global_position) != '', 3.0)
	check(Doors.interior_at(me_server().pos) == Doors.TAVERN_NAME and Doors.interior_at(player.global_position) == Doors.TAVERN_NAME,
			'realm moved the player into the tavern')
	session.send(Protocol.C_USE_DOOR, {'door': 'tavern_exit'})
	await frames(20)
	check(Doors.interior_at(me_server().pos) == '' and player.global_position.distance_to(Vector3(-11.4, 4.4, 48.6)) < 1.5, 'and back out to the street')

	# NPC movement: still / sitting, a waypoint path, wandering hostiles
	var keeper: Dictionary = realm.entities.innkeeper
	check(absf(keeper.pos.y - Doors.TAVERN_ORIGIN.y) < 0.1 and keeper.movement == 'still', 'innkeeper stands on the tavern floor (y=%.2f)' % keeper.pos.y)
	check(realm.entities.old_fisher.clip == 'sit_talk' and realm.entities.scholar.clip == 'sit_idle', 'patrons sit at the tables')
	var tilda: Dictionary = realm.entities.serving_girl
	var tilda_seen := {}
	var tilda_start: Vector3 = tilda.pos
	var tilda_far := 0.0
	for i in 600:
		await physics_frame
		tilda_seen[tilda.leg] = true
		tilda_far = maxf(tilda_far, tilda.pos.distance_to(tilda_start))
		if Doors.interior_at(tilda.pos) == '':
			break
	check(tilda_seen.size() >= 3 and tilda_far > 0.5, 'serving girl walks her path (reached %d points)' % tilda_seen.size())
	check(Doors.interior_at(tilda.pos) == Doors.TAVERN_NAME and absf(tilda.pos.y - Doors.TAVERN_ORIGIN.y) < 0.1, 'and stays inside on the floor')
	var wanderer: Dictionary = realm.entities.bandit_6
	var furthest := 0.0
	for i in 900:
		await physics_frame
		furthest = maxf(furthest, Vector2(wanderer.pos.x - wanderer.home.x, wanderer.pos.z - wanderer.home.z).length())
	check(wanderer.movement == 'wander' and furthest > 0.5 and furthest <= wanderer.wander_radius + 0.3,
			'bandit wanders around its camp (%.1f m of %.0f)' % [furthest, wanderer.wander_radius])
	await teleport(me_server(), tilda.pos + Vector3(1.0, 0, 0))
	await wait_for(func() -> bool: return session.actors.has('serving_girl'))
	session.set_target('serving_girl')
	session.interact()
	await wait_for(func() -> bool: return not session.dialogue.is_empty(), 3.0)
	var held: Vector3 = tilda.pos
	await frames(120)
	check(tilda.pos.distance_to(held) < 0.05 and not session.dialogue.is_empty(), 'serving girl stops to talk')
	session.close_dialogue()
	await teleport(me_server(), realm.zones.veyr.spawn_point())

	# Persistence: log out to the lobby, then sign in again from scratch
	var level := int(session.sheet.level)
	bot.stop()
	await frames(10)
	rosters.clear()
	main.logout()
	await wait_for(func() -> bool: return not rosters.is_empty())
	check(not session.in_world and int(rosters[-1][2][0].level) == level, 'back at character select, level saved')
	check(int(realm.db.value("SELECT level FROM characters WHERE name = 'Aelinor'")) == level, 'level stored in the characters table')
	rosters.clear()
	main.log_out_account()
	await frames(10)
	main.start_offline(SAVE)
	realm = main.realm
	check(await wait_for(func() -> bool: return not rosters.is_empty(), 20.0) and rosters[-1][0], 'signed in again with the stored offline account')
	session.enter(slot)
	await wait_for(func() -> bool: return session.in_world and not session.sheet.is_empty())
	check(session.sheet.quests_done.has('Trouble in the Marsh') and int(session.sheet.level) == level, 'quests and level persisted')
	check(session.item_count('health_tonic') >= 4, 'pack persisted')
	main.log_out_account()
	await frames(5)
	bot.queue_free()
	wipe(ProjectSettings.globalize_path(SAVE))
	print('RESULT ', 'OK' if failures == 0 else '%d FAILURES' % failures)
	quit(1 if failures else 0)
