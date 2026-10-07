extends SceneTree
## Headless checks for the walkable world.
##   Godot --headless --fixed-fps 60 --path . --script res://tools/verify_world.gd

var failures := 0
var scene: Node3D
var player: CharacterBody3D

func check(ok: bool, message: String) -> void:
	print(('PASS ' if ok else 'FAIL ') + message)
	if not ok:
		failures += 1

func _init() -> void:
	call_deferred('run')

func frames(n: int) -> void:
	for i in n:
		await physics_frame

func walk(points: Array, label: String, limit := 1500, radius := 0.9) -> bool:
	for target in points:
		var t := Vector2(target[0], target[1])
		var count := 0
		while Vector2(player.global_position.x, player.global_position.z).distance_to(t) > radius and count < limit:
			var look := Vector3(t.x, player.global_position.y, t.y)
			if player.global_position.distance_to(look) > 0.05:
				player.look_at(look, Vector3.UP)
			Input.action_press('move_forward')
			await physics_frame
			count += 1
		Input.action_release('move_forward')
		if count >= limit:
			print('BLOCKED ', label, ' at ', player.global_position, ' heading to ', t)
			return false
	return true

func teleport(p: Vector3, yaw := 0.0) -> void:
	player.global_position = p
	player.velocity = Vector3.ZERO
	player.rotation.y = yaw
	await frames(40)

func run() -> void:
	scene = load('res://scenes/world/veyr.tscn').instantiate()
	root.add_child(scene)
	player = scene.get_node('Player')
	var weather: Node = scene.get_node('Weather')
	await frames(90)
	check(player.is_on_floor(), 'Player starts standing on the harbour pier')
	check(player.global_position.y > 1.8 and player.global_position.y < 3.0, 'Pier holds the player above the water (y=%.2f)' % player.global_position.y)
	var start := player.global_position

	# harbour -> quay -> main street -> plaza -> temple stairs
	var ok := await walk([[-12, 72], [-12, 64.5], [-3, 60], [0, 40], [1, 28], [0, 10], [0, -6], [0, -30], [0, -50]], 'town')
	check(ok, 'Walk from the pier up onto the quay and along the main street to the plaza')
	ok = await walk([[0, -58.2]], 'temple stairs', 600, 0.5)
	check(ok and player.global_position.y > 7.6, 'Climb the temple stairs (y=%.2f)' % player.global_position.y)

	# plaza -> north road -> mine
	await teleport(Vector3(0, 7.2, -30))
	ok = await walk([[14, -46], [26, -50], [34, -58], [40, -70], [46, -98], [38, -124], [29, -140], [28, -146]], 'north road', 2500)
	check(ok, 'Follow the north road from the plaza to the mine entrance')
	ok = await walk([[28, -152], [28.4, -162], [29.6, -172], [33.5, -182], [41, -190], [45, -193]], 'mine', 2500, 0.8)
	check(ok and player.is_on_floor(), 'Walk through the mine tunnel to the cavern')
	await frames(150)
	check(weather.interior > 0.5, 'Interior lighting takes over inside the mine (interior=%.2f)' % weather.interior)
	check(scene.region_at(player.global_position) == 'The Hollow Mine', 'Region reports the mine')

	# crossing -> east road -> Shell Ward
	await teleport(Vector3(0, 5.0, 28), -PI / 2)
	ok = await walk([[22, 28], [46, 28], [62, 20], [76, 6], [90, -4], [102, -12]], 'east road', 2500)
	check(ok and player.global_position.y > 11.0, 'Walk the east road up into the Shell Ward (y=%.2f)' % player.global_position.y)

	# west road to the marsh
	await teleport(Vector3(-46, 5.0, 28), PI / 2)
	ok = await walk([[-70, 22], [-95, 26], [-112, 34]], 'west road', 2500)
	check(ok, 'Walk the west road down to the marsh')

	# swimming
	await teleport(Vector3(10, 0.5, 125))
	await frames(120)
	check(player.swimming and absf(player.global_position.y + 1.35) < 0.6, 'Deep water switches to swimming (y=%.2f)' % player.global_position.y)

	# world systems
	var seen := []
	for w in weather.ORDER:
		weather.set_weather(w, true)
		await process_frame
		seen.append(weather.current)
	check(seen == weather.ORDER, 'All seven weather types can be set')
	weather.set_weather('Clear', true)
	var h0: float = weather.hour
	weather.wait_hours(1.0)
	for i in 120:
		await process_frame
	check(absf(fposmod(weather.hour - h0, 24.0) - 1.0) < 0.1, 'Waiting advances the clock by an hour')
	# third-person view shows the body and pulls the camera back
	await teleport(Vector3(0, 7.2, -30))
	player.set_third_person(true)
	for i in 90:
		await process_frame
	var cam_back: float = player.camera.position.length()
	check(player.body != null and player.body.visible and cam_back > 2.0, 'Tab view shows the player model (camera %.2f m back)' % cam_back)
	player.set_third_person(false)
	await process_frame
	check(not player.body.visible and player.camera.position.length() < 0.01, 'First person hides the model again')
	player.set_menu(true)
	check(player.paused and Input.mouse_mode == Input.MOUSE_MODE_VISIBLE, 'Menu pauses and frees the mouse')
	player.return_to_spawn()
	check(not player.paused and player.global_position.distance_to(start) < 1.0, 'Return to the harbour')

	# the tavern door by the quay: prompt up close, E goes inside, the inside door leads back out
	var doors: Node = scene.doors
	var hud: CanvasLayer = scene.hud
	ok = await walk([[-12, 72], [-12, 64.5], [-3, 60], [-4, 48.6]], 'to the tavern', 1500)
	ok = ok and await walk([[-11.3, 48.6]], 'tavern door', 600, 0.4)
	player.rotation.y = PI / 2
	player.head.rotation.x = 0.0
	await frames(10)
	check(ok and doors.focused == 'tavern_enter' and hud.prompt.visible, 'Looking at the tavern door shows "E Enter" (focused=%s)' % doors.focused)
	player.rotation.y = 0.0
	await frames(5)
	check(doors.focused == '' and not hud.prompt.visible, 'Looking away hides the prompt')
	player.rotation.y = PI / 2
	await frames(5)
	check(doors.use_focused(), 'E uses the door')
	await frames(60)
	check(Doors.interior_at(player.global_position) == Doors.TAVERN_NAME, 'Inside the tavern (%s)' % player.global_position)
	check(scene.region_at(player.global_position) == Doors.TAVERN_NAME and weather.interior > 0.99, 'Region and interior lighting switch to the tavern')
	check(player.is_on_floor(), 'The tavern floor holds the player')
	ok = await walk([[Doors.TAVERN_ORIGIN.x + 2.0, Doors.TAVERN_ORIGIN.z - 1.5], [Doors.TAVERN_ORIGIN.x - 3.5, Doors.TAVERN_ORIGIN.z - 1.5]], 'tavern floor', 900, 0.5)
	check(ok and player.is_on_floor(), 'Walk across the taproom to the hearth')
	await teleport(Doors.TAVERN_ORIGIN + Vector3(4.6, 0.05, 0.0), -PI / 2)
	await frames(5)
	check(doors.focused == 'tavern_exit', 'The inside door offers "E Exit"')
	doors.use_focused()
	await frames(60)
	check(Doors.interior_at(player.global_position) == '' and player.global_position.distance_to(Vector3(-11.4, 4.3, 48.6)) < 1.5,
			'Exit puts the player back on the street at the door (%s)' % player.global_position)
	await frames(100)
	check(weather.interior < 0.01, 'Daylight again outside')

	scene.queue_free()
	for i in 5:
		await process_frame
	print('VERIFICATION_FAILURES ', failures)
	quit(1 if failures else 0)
