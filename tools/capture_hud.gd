extends SceneTree
## Visual QA of the real scene. Run with a graphics renderer (not --headless).
var scene: Node
var hud: Node
var player: Node
func _init() -> void:
	call_deferred('run')
func frames(n := 8) -> void:
	for i in n:
		await process_frame
func capture(file: String) -> void:
	await frames(20)
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png('res://docs/hud/' + file + '.png')
	print('CAPTURE ', file)
func click(control: Control) -> void:
	var motion := InputEventMouseMotion.new()
	motion.position = control.get_global_rect().get_center()
	root.push_input(motion, true)
	await frames(2)
	print('CLICK ', control, ' rect ', control.get_global_rect(), ' viewport ', root.get_visible_rect(), ' hover ', root.gui_get_hovered_control())
	var e := InputEventMouseButton.new()
	e.position = control.get_global_rect().get_center()
	e.button_index = MOUSE_BUTTON_LEFT
	e.pressed = true
	root.push_input(e, true)
	await frames(2)
	e = e.duplicate()
	e.pressed = false
	root.push_input(e, true)
	await frames(2)
func run() -> void:
	scene = load('res://scenes/world/veyr.tscn').instantiate()
	root.add_child(scene)
	hud = scene.get_node('HUD')
	player = scene.get_node('Player')
	player.paused = true
	scene.weather.time_flows = false
	await frames(40)
	player.global_position = Vector3(0, 5.2, 35)
	player.rotation.y = 0
	player.head.rotation.x = deg_to_rad(-7)
	player.set_third_person(true)
	player.set_weapon(false, true)
	scene.weather.set_hour(10)
	await frames(200)
	hud._region_time = 0
	await capture('preview')
	# Exercise actual hit testing through the viewport, not just pressed signals.
	player.paused = false
	hud.set_interface_open(true)
	hud.add_chat_message('Players', 'Ready for the road ahead.', 'Adventurer')
	await click(hud.chat_tabs[2])
	if hud.active_channel != 'Players':
		await frames(10)
		await click(hud.chat_tabs[2])
	assert(hud.active_channel == 'Players', 'Players tab must respond to mouse clicks')
	await click(hud.dock_buttons[2])
	assert(hud.active_panel == 'Inventory' and hud.info_panel.visible, 'Inventory icon must respond to mouse clicks')
	await capture('chat-and-inventory')
	await click(hud.dock_buttons[5])
	await frames()
	assert(hud.active_panel == 'Settings' and hud.dock_settings.visible and not hud.menu.visible, 'Settings icon must use the attached panel')
	await capture('settings')
	var original_model: String = player.body_model
	player.set_body_model('female')
	player.set_menu(false)
	player.paused = true
	root.content_scale_size = Vector2i.ZERO
	root.size = Vector2i(800, 600)
	await frames()
	hud._layout()
	hud._open_panel('Inventory')
	await capture('compact-female')
	player.set_body_model(original_model)
	scene.queue_free()
	await frames()
	quit()


