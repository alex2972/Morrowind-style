extends Node3D
## Root of the Veyr scene. Wires the player, weather and HUD together, tracks when the player
## is inside the mine or an interior behind a door (interior lighting), names regions, renders the local map once, and
## offers a capture mode used to produce preview screenshots.
##
## Capture mode (user args after `--`):
##   --shots=res://path/shots.json   list of {file, pos:[x,y,z], yaw, pitch, hour, weather, hud}

const LAYER_WORLD := 1
const LAYER_INTERIOR := 2
const LAYER_FLORA := 4
const LAYER_VIEWMODEL := 8

@export var tunnel_path: PackedVector3Array
@export var regions: Array = []
@export var map_half := 256.0
@export var splat_b_texture: Texture2D

@onready var weather: Node = $Weather
@onready var player: CharacterBody3D = $Player
@onready var hud: CanvasLayer = $HUD

var minimap_texture: Texture2D
var doors: Node3D
var _flicker: Array[OmniLight3D] = []
var _night_lights: Array[OmniLight3D] = []
var _time := 0.0
var _splat_b: Image
var _region := ''
var _tunnel_len := PackedFloat32Array()
var _indoors := false

func _ready() -> void:
	doors = Node3D.new()
	doors.set_script(load('res://client/world/doors.gd'))
	add_child(doors)
	weather.rain = player.get_node_or_null('Precipitation/Rain')
	weather.ash = player.get_node_or_null('Precipitation/Ash')
	weather.dust = player.get_node_or_null('Precipitation/Dust')
	weather.weather_changed.connect(func(n: String) -> void: hud.show_message('The weather turns: %s.' % n.to_lower()))
	if splat_b_texture:
		_splat_b = splat_b_texture.get_image()
		if _splat_b and _splat_b.is_compressed():
			_splat_b.decompress()
	var acc := 0.0
	_tunnel_len.append(0.0)
	for i in range(1, tunnel_path.size()):
		acc += Vector2(tunnel_path[i].x - tunnel_path[i - 1].x, tunnel_path[i].z - tunnel_path[i - 1].z).length()
		_tunnel_len.append(acc)
	_collect_flicker(self)
	_render_minimap()
	var shots := ''
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with('--shots='):
			shots = arg.trim_prefix('--shots=')
	if shots != '':
		_run_shots(shots)

func _collect_flicker(n: Node) -> void:
	if n is OmniLight3D and n.has_meta('flicker'):
		_flicker.append(n)
	if n is OmniLight3D and n.has_meta('night_only'):
		_night_lights.append(n)
	for c in n.get_children():
		_collect_flicker(c)

func _process(delta: float) -> void:
	_time += delta
	var cam_pos := player.global_position
	for i in _flicker.size():
		var l := _flicker[i]
		if l.global_position.distance_squared_to(cam_pos) > 9000.0:
			continue
		var base: float = l.get_meta('flicker')
		var t := _time * 9.0 + i * 1.7
		l.light_energy = base * (0.86 + 0.08 * sin(t) + 0.06 * sin(t * 2.3 + 1.1) + 0.04 * sin(t * 5.7))
	var nf: float = weather.night_factor
	for l in _night_lights:
		l.light_energy = float(l.get_meta('night_only')) * nf
		l.visible = nf > 0.02
	var p := player.global_position
	var indoors := Doors.interior_at(p) != ''
	if indoors != _indoors:   # stepping through a door: the light changes at once
		_indoors = indoors
		weather.interior = 1.0 if indoors else 0.0
	var target := 1.0 if indoors else smoothstep(1.0, 9.0, tunnel_depth(p))
	weather.interior = move_toward(weather.interior, target, delta * 0.9)
	var r := region_at(p)
	if r != _region:
		_region = r
		if r != '':
			hud.show_region(r)

func tunnel_depth(p: Vector3) -> float:
	## Metres travelled into the mine along its path (0 when outside).
	if tunnel_path.size() < 2:
		return 0.0
	var best := 1e9
	var along := 0.0
	var floor_y := 0.0
	for i in range(tunnel_path.size() - 1):
		var a := Vector2(tunnel_path[i].x, tunnel_path[i].z)
		var b := Vector2(tunnel_path[i + 1].x, tunnel_path[i + 1].z)
		var q := Vector2(p.x, p.z)
		var ab := b - a
		var t := clampf((q - a).dot(ab) / ab.length_squared(), 0.0, 1.0)
		var d := q.distance_to(a + ab * t)
		if d < best:
			best = d
			along = _tunnel_len[i] + ab.length() * t
			floor_y = lerpf(tunnel_path[i].y, tunnel_path[i + 1].y, t)
	if best > 9.0 or p.y < floor_y - 2.0 or p.y > floor_y + 9.0:
		return 0.0
	# the first stations sit at the mouth; count depth from there
	var mouth := Vector2(tunnel_path[0].x, tunnel_path[0].z)
	var dir := Vector2(tunnel_path[1].x, tunnel_path[1].z) - mouth
	var into := (Vector2(p.x, p.z) - mouth).dot(dir.normalized())
	return maxf(0.0, minf(along, into))

func region_at(p: Vector3) -> String:
	var inside := Doors.interior_at(p)
	if inside != '':
		return inside
	if tunnel_depth(p) > 3.0:
		return 'The Hollow Mine'
	for r in regions:
		var rect: Array = r.rect
		if p.x >= rect[0] and p.x <= rect[1] and p.z >= rect[2] and p.z <= rect[3]:
			return r.name
	return 'The Veyr Coast'

func surface_at(p: Vector3) -> String:
	## 'stone' on cobbles, otherwise 'soft'.
	if _splat_b == null:
		return 'soft'
	var w := _splat_b.get_width()
	var x := clampi(int((p.x + map_half) / (2.0 * map_half) * w), 0, w - 1)
	var y := clampi(int((p.z + map_half) / (2.0 * map_half) * w), 0, w - 1)
	return 'stone' if _splat_b.get_pixel(x, y).b > 0.45 else 'soft'

func _render_minimap() -> void:
	if DisplayServer.get_name() == 'headless':
		return
	var vp := SubViewport.new()
	vp.size = Vector2i(1024, 1024)
	vp.render_target_update_mode = SubViewport.UPDATE_ONCE
	add_child(vp)
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = map_half * 2.0
	cam.position = Vector3(0, 380, 0)
	cam.rotation_degrees = Vector3(-90, 0, 0)
	cam.far = 800.0
	cam.cull_mask = LAYER_WORLD
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.1, 0.13, 0.13)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.85, 0.82, 0.74)
	env.ambient_light_energy = 0.9
	cam.environment = env
	vp.add_child(cam)
	cam.current = true
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var img := vp.get_texture().get_image()
	if img == null or img.is_empty():
		vp.queue_free()
		return
	minimap_texture = ImageTexture.create_from_image(img)
	hud.set_minimap(minimap_texture, map_half)
	vp.queue_free()

func _run_shots(path: String) -> void:
	var data = JSON.parse_string(FileAccess.get_file_as_string(path))
	if data == null:
		push_error('Could not read shots file ' + path)
		get_tree().quit(1)
		return
	player.paused = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	weather.time_flows = false
	for i in range(30):
		await get_tree().process_frame
	hud.show_message('', 0.0)
	for shot in data:
		var pos: Array = shot.pos
		player.global_position = Vector3(pos[0], pos[1], pos[2])
		player.rotation.y = deg_to_rad(shot.get('yaw', 0.0))
		player.get_node('Head').rotation.x = deg_to_rad(shot.get('pitch', 0.0))
		weather.set_hour(shot.get('hour', 9.0))
		weather.set_weather(shot.get('weather', 'Clear'), true)
		player.set_weapon(shot.get('weapon', true), true)
		player.set_torch(shot.get('torch', false))
		player.set_third_person(shot.get('third_person', false))
		if player.body:
			player.body.rotation.y = PI + deg_to_rad(shot.get('model_yaw', 0.0))
		hud.visible = shot.get('hud', true)
		weather.interior = 1.0 if Doors.interior_at(player.global_position) != '' else smoothstep(1.0, 9.0, tunnel_depth(player.global_position))
		for i in range(int(shot.get('frames', 40))):
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		var err := img.save_png(shot.file)
		print('SHOT ', shot.file.get_file(), ' err=', err, ' fps=', Engine.get_frames_per_second(),
				' draws=', Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
	get_tree().quit()
