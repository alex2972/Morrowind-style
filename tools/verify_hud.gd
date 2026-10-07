extends SceneTree
## Integration checks: actual scene, HUD channels, keyboard routing, and window layout.
var failures := 0
var scene: Node
var hud: Node
var player: Node

func _init() -> void:
	call_deferred('run')

func check(ok: bool, description: String) -> void:
	print(('PASS ' if ok else 'FAIL ') + description)
	if not ok:
		failures += 1

func frames(count := 3) -> void:
	for i in count:
		await process_frame

func key(code: Key) -> void:
	var event := InputEventKey.new()
	event.keycode = code
	event.physical_keycode = code
	event.pressed = true
	root.push_input(event)
	await frames()
	event = event.duplicate()
	event.pressed = false
	root.push_input(event)
	await frames()

func run() -> void:
	scene = load('res://scenes/world/veyr.tscn').instantiate()
	root.add_child(scene)
	hud = scene.get_node('HUD')
	player = scene.get_node('Player')
	await frames(10)
	check(hud.chat_tabs.size() == 4, 'All four chat tabs exist')
	check(hud.dock_buttons.size() == 6, 'Six reference menu icons are interactive; two slots remain empty')
	hud.add_chat_message('Game', 'game sentinel')
	hud.add_chat_message('Players', '[b]literal player message[/b]', 'Visitor')
	hud.add_chat_message('Combat', 'combat sentinel')
	for i in 4:
		hud.chat_tabs[i].pressed.emit()
		var text: String = hud.chat_log.get_parsed_text()
		check(text.contains('game sentinel') == (i in [0, 1]), 'Game filter on ' + hud.CHANNELS[i])
		check(text.contains('literal player message') == (i in [0, 2]), 'Players filter on ' + hud.CHANNELS[i])
		check(text.contains('combat sentinel') == (i in [0, 3]), 'Combat filter on ' + hud.CHANNELS[i])
	hud._select_channel('All')
	check(hud.chat_log.get_parsed_text().contains('[b]literal'), 'Player text cannot inject chat formatting')
	await key(KEY_ENTER)
	check(hud.chat_input.has_focus() and player.ui_active, 'Enter focuses chat and blocks game input')
	var before: Vector3 = player.position
	Input.action_press('move_forward')
	for i in 8:
		await physics_frame
	Input.action_release('move_forward')
	check(player.position.is_equal_approx(before), 'Typing movement keys leaves the character stationary')
	var armed: bool = player.weapon_out
	await key(KEY_F)
	check(player.weapon_out == armed, 'Typing F does not toggle the sword')
	hud.chat_input.text = 'A message from the integration check'
	await key(KEY_ENTER)
	check(not player.ui_active and not hud.chat_input.has_focus(), 'Submitting chat releases UI focus')
	check(hud.chat_history.back().text == 'A message from the integration check', 'Enter submits the player message')
	await key(KEY_I)
	check(hud.interface_open and player.ui_active, 'I releases the cursor for the HUD')
	hud._open_panel('Inventory')
	check(hud.info_panel.visible and hud.info_text.text.contains('Iron sword'), 'Inventory opens with current travelling gear')
	hud._open_panel('Settings')
	await frames()
	check(hud.dock_settings.visible and not hud.menu.visible and player.ui_active, 'Settings opens inside the shared dock panel')
	var panel_size: Vector2 = hud.info_panel.size
	for title in ['Spellbook', 'Journal', 'Inventory', 'Equipment', 'Players', 'Settings']:
		hud._open_panel(title)
		check(hud.info_panel.visible and hud.info_panel.size == panel_size, title + ' uses the same panel dimensions')
		check(hud.dock_buttons.filter(func(b: Button) -> bool: return b.button_pressed).size() == 1, title + ' highlights exactly one icon')
	hud._open_panel('Settings')
	check(not hud.info_panel.visible, 'Selecting the same icon closes its panel')
	player.set_menu(true)
	check(hud.menu_shade.visible, 'Pause menu blocks clicks to the HUD beneath it')
	player.set_menu(false)
	await key(KEY_ENTER)
	await key(KEY_ESCAPE)
	check(not player.ui_active and not player.paused, 'Escape closes chat without opening the pause menu')
	hud.show_region('The Hollow Mine')
	check(hud.zone_label.text.contains('Hollow Mine'), 'Minimap zone label updates on region changes')
	player.health = 37
	player.mana = 42
	await frames()
	check(player.health == 37 and player.mana == 42, 'Status bars consume exported player vitals')
	root.content_scale_size = Vector2i.ZERO
	for dimensions in [Vector2i(800, 600), Vector2i(1280, 720), Vector2i(1600, 900), Vector2i(2560, 1080)]:
		root.size = dimensions
		await frames()
		hud._layout()
		var usable: Vector2 = hud.root.size
		var panel_rect: Rect2 = hud.info_panel.get_global_rect()
		var dock_rect: Rect2 = hud.dock.get_global_rect()
		check(is_equal_approx(panel_rect.end.y, dock_rect.position.y) and is_equal_approx(panel_rect.position.x, dock_rect.position.x) and is_equal_approx(panel_rect.size.x, dock_rect.size.x), 'Panel joins the dock with matching width at ' + str(dimensions))
		check(hud.chat_box.position.x + hud.chat_box.size.x < hud.dock.position.x, 'Bottom corners do not overlap at ' + str(dimensions))
		check(hud.status.position.x + hud.status.size.x < hud.map_box.position.x, 'Top corners do not overlap at ' + str(dimensions))
		check((hud.dock.position + hud.dock.size * hud.dock.scale).is_equal_approx(usable), 'Dock stays inside viewport at ' + str(dimensions))
	for i in 210:
		hud.add_chat_message('Game', str(i))
	check(hud.chat_history.size() == 200, 'Chat history stays bounded at 200 messages')
	print('HUD CHECKS COMPLETE: ', failures, ' failure(s)')
	for audio in scene.find_children('*', 'AudioStreamPlayer', true, false):
		audio.stop()
	await create_timer(0.1).timeout
	scene.queue_free()
	await frames(3)
	quit(1 if failures else 0)



