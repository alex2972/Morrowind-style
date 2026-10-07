extends SceneTree
## Screenshots of the front end and the in-game combat UI (needs a renderer, not --headless):
##   Godot --path . --script res://tools/capture_online.gd -- --out=docs/previews

const SAVE := 'user://capture_realm'
const BotClient = preload('res://tools/bot_client.gd')
var out := 'res://docs/previews'
var main: Node
var session: Node
var rosters: Array = []

func _init() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with('--out='):
			out = arg.trim_prefix('--out=')
	call_deferred('run')

func frames(n: int) -> void:
	for i in n:
		await process_frame

func wait_for(condition: Callable, seconds := 10.0) -> void:
	var t := 0
	while not condition.call() and t < seconds * 60:
		await process_frame
		t += 1

func shot(file: String) -> void:
	await frames(20)
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	img.save_png(out.path_join(file))
	print('SHOT ', file)

func wipe(path: String) -> void:
	var dir := DirAccess.open(path)
	if dir == null:
		return
	for sub in dir.get_directories():
		wipe(path.path_join(sub))
	for f in dir.get_files():
		dir.remove(f)
	DirAccess.remove_absolute(path)

func run() -> void:
	root.size = Vector2i(1600, 900)
	wipe(ProjectSettings.globalize_path(SAVE))
	main = load('res://scenes/main.tscn').instantiate()
	root.add_child(main)
	await frames(30)
	session = main.session
	main.world.weather.time_flows = false
	main.world.weather.set_hour(10.0)
	main.world.weather.set_weather('Clear', true)
	session.roster_received.connect(func(ok: bool, msg: String, list: Array) -> void: rosters.append(list))
	await shot('online_login.png')
	main.start_offline(SAVE)
	await wait_for(func() -> bool: return not rosters.is_empty())
	main.front.show_create()
	main.front._identity.merge({'name': 'Aelinor', 'sex': 'female', 'race': 'high_elf', 'skin': 1, 'class': 'priest'}, true)
	main.front.show_create()
	await shot('online_create.png')
	rosters.clear()
	session.create_character(main.front._identity.duplicate())
	await wait_for(func() -> bool: return not rosters.is_empty())
	rosters.clear()
	session.create_character({'name': 'Brannoc', 'sex': 'male', 'race': 'dark_elf', 'skin': 2, 'class': 'warrior'})
	await wait_for(func() -> bool: return not rosters.is_empty())
	await shot('online_lobby.png')
	session.enter(rosters[-1][0].id)
	await wait_for(func() -> bool: return session.in_world and not session.sheet.is_empty())
	var realm: Realm = main.realm
	var p: Dictionary = realm.players.values()[0]
	var hm: Dictionary = realm.entities.harbourmaster
	realm.movement.teleport(p, hm.pos + Vector3(1.2, 0.05, 3.2), atan2(1.2, 3.2))
	await frames(40)
	session.set_target('harbourmaster')
	session.interact()
	await wait_for(func() -> bool: return not session.dialogue.is_empty())
	await shot('online_dialogue.png')
	session.choose('quest:marsh_trouble')
	await frames(10)
	session.choose('accept:marsh_trouble')
	await frames(10)
	session.close_dialogue()
	main.world.hud.set_interface_open(false)
	var bot: Node = BotClient.new()
	bot.name = 'Bot'
	root.add_child(bot)
	bot.start('127.0.0.1', realm.port)
	await wait_for(func() -> bool: return bot.connected)
	bot.hello('capturebot', 'capturebot1', true)
	await wait_for(func() -> bool: return bot.auth_ok)
	bot.send(Protocol.C_CREATE_CHARACTER, {'name': 'Ilsa', 'sex': 'female', 'race': 'human', 'skin': 1, 'class': 'mage'})
	await wait_for(func() -> bool: return not bot.roster.is_empty())
	print('bot: ', bot.connected, ' ', bot.auth_ok, ' ', bot.auth_message)
	bot.send(Protocol.C_ENTER, {'id': bot.roster[0].id})
	await wait_for(func() -> bool: return bot.eid != '')
	session.send_chat('/invite Ilsa')
	await frames(30)
	bot.send(Protocol.C_PARTY_RESPOND, {'accept': true})
	await frames(30)
	var bandit: Dictionary = realm.entities.bandit_1
	var spot: Vector3 = bandit.pos + Vector3(0, 0, 6)
	spot.y = realm.zone_of(p).ground(spot.x, spot.z) + 0.05
	realm.movement.teleport(p, spot, 0.0)
	var bp: Dictionary = realm.entities[bot.eid]
	var bspot: Vector3 = spot + Vector3(-2.5, 0, 1.5)
	bspot.y = realm.zone_of(p).ground(bspot.x, bspot.z) + 0.05
	realm.movement.teleport(bp, bspot, 0.0)
	main.world.player.head.rotation.x = -0.12
	await frames(30)
	session.set_target('bandit_1')
	session.use_slot(1)   # Heroic Strike starts auto-attack and pulls the bandit
	await frames(200)
	session.use_slot(9)
	await frames(30)
	await shot('online_combat.png')
	bot.stop()
	main.log_out_account()
	await frames(5)
	wipe(ProjectSettings.globalize_path(SAVE))
	quit()
