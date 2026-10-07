extends Node
## Morrowind-style day/night cycle and weather.
##
## Every frame this blends per-weather colour tables (sunrise / day / sunset / night) and
## drives the sky shader, depth fog, ambient light, sun or moon light, precipitation,
## lightning, lit windows and ambient sound. Colours are modelled on the classic
## Morrowind.ini weather settings, nudged slightly brighter at night.

signal weather_changed(weather_name: String)

const PHASES := 4  # sunrise, day, sunset, night

const WEATHER := {
	'Clear': {
		'sky': [Color8(117, 141, 164), Color8(95, 135, 203), Color8(70, 76, 120), Color8(14, 18, 30)],
		'fog': [Color8(255, 189, 157), Color8(178, 198, 224), Color8(255, 150, 96), Color8(16, 19, 28)],
		'ambient': [Color8(70, 82, 104), Color8(137, 140, 160), Color8(84, 84, 100), Color8(44, 50, 68)],
		'sun': [Color8(242, 159, 119), Color8(255, 252, 238), Color8(255, 104, 52), Color8(70, 104, 176)],
		'disc': Color8(255, 170, 120), 'light': 1.0, 'fog_far': 300.0, 'clouds': 'sky_clear', 'cloud_speed': 1.0,
		'cloud_opacity': 0.9, 'cloud_bright': 1.05, 'glare': 1.0, 'rain': 0.0, 'ash': 0.0, 'wind': 0.25, 'stars': 1.0,
		'shadow': 0.8,
	},
	'Cloudy': {
		'sky': [Color8(126, 158, 173), Color8(117, 160, 215), Color8(111, 114, 159), Color8(14, 17, 26)],
		'fog': [Color8(255, 207, 149), Color8(212, 210, 204), Color8(255, 155, 106), Color8(16, 18, 26)],
		'ambient': [Color8(76, 84, 98), Color8(137, 145, 160), Color8(84, 88, 100), Color8(44, 50, 66)],
		'sun': [Color8(241, 177, 99), Color8(255, 236, 221), Color8(255, 89, 30), Color8(77, 91, 124)],
		'disc': Color8(255, 189, 157), 'light': 0.9, 'fog_far': 280.0, 'clouds': 'sky_cloudy', 'cloud_speed': 1.6,
		'cloud_opacity': 0.95, 'cloud_bright': 1.0, 'glare': 0.9, 'rain': 0.0, 'ash': 0.0, 'wind': 0.4, 'stars': 0.7,
		'shadow': 0.7,
	},
	'Foggy': {
		'sky': [Color8(197, 190, 180), Color8(184, 211, 228), Color8(142, 159, 176), Color8(18, 23, 28)],
		'fog': [Color8(173, 164, 148), Color8(150, 187, 209), Color8(113, 135, 157), Color8(19, 24, 29)],
		'ambient': [Color8(64, 60, 54), Color8(104, 120, 130), Color8(48, 54, 62), Color8(36, 40, 48)],
		'sun': [Color8(178, 120, 96), Color8(223, 223, 223), Color8(131, 89, 72), Color8(42, 50, 66)],
		'disc': Color8(206, 180, 160), 'light': 0.55, 'fog_far': 85.0, 'clouds': 'sky_overcast', 'cloud_speed': 0.6,
		'cloud_opacity': 0.75, 'cloud_bright': 1.1, 'glare': 0.3, 'rain': 0.0, 'ash': 0.0, 'wind': 0.1, 'stars': 0.15,
		'shadow': 0.35,
	},
	'Overcast': {
		'sky': [Color8(91, 99, 106), Color8(143, 146, 149), Color8(108, 115, 121), Color8(12, 13, 15)],
		'fog': [Color8(91, 99, 106), Color8(143, 146, 149), Color8(108, 115, 121), Color8(13, 14, 16)],
		'ambient': [Color8(84, 88, 92), Color8(112, 116, 124), Color8(83, 77, 75), Color8(46, 49, 56)],
		'sun': [Color8(87, 125, 163), Color8(163, 169, 183), Color8(85, 103, 157), Color8(40, 58, 100)],
		'disc': Color8(200, 200, 200), 'light': 0.55, 'fog_far': 210.0, 'clouds': 'sky_overcast', 'cloud_speed': 1.2,
		'cloud_opacity': 1.0, 'cloud_bright': 0.95, 'glare': 0.0, 'rain': 0.0, 'ash': 0.0, 'wind': 0.45, 'stars': 0.1,
		'shadow': 0.25,
	},
	'Rain': {
		'sky': [Color8(71, 74, 75), Color8(116, 120, 122), Color8(73, 73, 73), Color8(20, 21, 23)],
		'fog': [Color8(71, 74, 75), Color8(120, 126, 126), Color8(73, 73, 73), Color8(21, 22, 24)],
		'ambient': [Color8(97, 90, 88), Color8(105, 110, 113), Color8(88, 97, 97), Color8(46, 50, 60)],
		'sun': [Color8(131, 82, 51), Color8(178, 188, 199), Color8(82, 94, 94), Color8(44, 50, 64)],
		'disc': Color8(160, 160, 160), 'light': 0.45, 'fog_far': 140.0, 'clouds': 'sky_storm', 'cloud_speed': 2.0,
		'cloud_opacity': 1.0, 'cloud_bright': 0.85, 'glare': 0.0, 'rain': 0.75, 'ash': 0.0, 'wind': 0.65, 'stars': 0.0,
		'shadow': 0.15,
	},
	'Thunderstorm': {
		'sky': [Color8(35, 36, 39), Color8(97, 104, 115), Color8(35, 36, 39), Color8(17, 18, 21)],
		'fog': [Color8(35, 36, 39), Color8(97, 104, 115), Color8(35, 36, 39), Color8(18, 19, 22)],
		'ambient': [Color8(54, 54, 58), Color8(90, 92, 98), Color8(54, 54, 58), Color8(42, 44, 52)],
		'sun': [Color8(91, 99, 122), Color8(138, 144, 155), Color8(96, 101, 117), Color8(50, 66, 100)],
		'disc': Color8(140, 140, 140), 'light': 0.4, 'fog_far': 110.0, 'clouds': 'sky_storm', 'cloud_speed': 3.0,
		'cloud_opacity': 1.0, 'cloud_bright': 0.7, 'glare': 0.0, 'rain': 1.0, 'ash': 0.0, 'wind': 0.9, 'stars': 0.0,
		'shadow': 0.1, 'thunder': true,
	},
	'Ashstorm': {
		'sky': [Color8(91, 56, 51), Color8(124, 73, 58), Color8(106, 55, 40), Color8(22, 18, 17)],
		'fog': [Color8(91, 56, 51), Color8(124, 73, 58), Color8(106, 55, 40), Color8(24, 19, 18)],
		'ambient': [Color8(119, 102, 86), Color8(120, 111, 98), Color8(93, 80, 76), Color8(46, 42, 44)],
		'sun': [Color8(255, 108, 60), Color8(187, 127, 76), Color8(255, 94, 40), Color8(60, 58, 70)],
		'disc': Color8(255, 140, 90), 'light': 0.55, 'fog_far': 70.0, 'clouds': 'sky_ash', 'cloud_speed': 5.0,
		'cloud_opacity': 1.0, 'cloud_bright': 0.9, 'glare': 0.15, 'rain': 0.0, 'ash': 1.0, 'wind': 1.0, 'stars': 0.0,
		'shadow': 0.2,
	},
}
const ORDER := ['Clear', 'Cloudy', 'Foggy', 'Overcast', 'Rain', 'Thunderstorm', 'Ashstorm']
const CHANCES := {'Clear': 34, 'Cloudy': 26, 'Foggy': 8, 'Overcast': 12, 'Rain': 10, 'Thunderstorm': 4, 'Ashstorm': 6}
const LIGHT_PHASE := [0.85, 1.25, 0.85, 0.42]
const INTERIOR_FOG := Color8(24, 17, 12)
const INTERIOR_AMBIENT := Color8(58, 46, 38)

@export var hour := 8.0
@export var time_scale := 30.0  ## game seconds per real second (Morrowind default)
@export var time_flows := true
@export var start_weather := 'Clear'

var current := 'Clear'
var target := 'Clear'
var blend := 1.0
var blend_speed := 0.05
var auto_change_in := 4.0  ## game hours until the next automatic weather change
var interior := 0.0  ## 0 outdoors, 1 deep inside the mine
var flash := 0.0
var wetness := 0.0
var night_factor := 0.0  ## 0 by day, 1 at night (lit windows, beacon)
var cloud_offset := Vector2.ZERO
var wait_left := 0.0
var _thunder_timer := 8.0
var _thunder_delay := -1.0
var _rng := RandomNumberGenerator.new()

var env: Environment
var sun: DirectionalLight3D
var sky_mat: ShaderMaterial
var rain: GPUParticles3D
var ash: GPUParticles3D
var dust: GPUParticles3D
var glow_materials: Array[BaseMaterial3D] = []
var sounds := {}
var cloud_textures := {}
var blended := {}

func _ready() -> void:
	_rng.randomize()
	var world := get_parent()
	env = world.get_node('WorldEnvironment').environment
	sun = world.get_node('Sun')
	sky_mat = env.sky.sky_material
	for key in ['sky_clear', 'sky_cloudy', 'sky_overcast', 'sky_storm', 'sky_ash']:
		cloud_textures[key] = load('res://assets/textures/%s.png' % key)
	for path in ['res://materials/window.tres', 'res://materials/bubble_glass.tres']:
		if ResourceLoader.exists(path):
			glow_materials.append(load(path))
	current = start_weather
	target = start_weather
	sky_mat.set_shader_parameter('clouds_a', cloud_textures[WEATHER[current].clouds])
	sky_mat.set_shader_parameter('clouds_b', cloud_textures[WEATHER[current].clouds])
	_setup_sounds()
	_apply(0.0)

func _setup_sounds() -> void:
	for key in ['wind', 'rain', 'waves', 'crickets', 'birds']:
		var path := 'res://assets/audio/%s.wav' % key
		if not ResourceLoader.exists(path):
			continue
		var p := AudioStreamPlayer.new()
		var stream: AudioStreamWAV = load(path)
		stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
		stream.loop_end = int(stream.get_length() * stream.mix_rate)
		p.stream = stream
		p.volume_db = -80.0
		p.name = key.capitalize() + 'Ambience'
		add_child(p)
		p.play()
		sounds[key] = p
	if ResourceLoader.exists('res://assets/audio/thunder.wav'):
		var t := AudioStreamPlayer.new()
		t.stream = load('res://assets/audio/thunder.wav')
		t.name = 'Thunder'
		add_child(t)
		sounds['thunder'] = t

# ---------------------------------------------------------------- public controls

func set_weather(weather_name: String, instant := false) -> void:
	if not WEATHER.has(weather_name):
		return
	if instant:
		current = weather_name
		target = weather_name
		blend = 1.0
		sky_mat.set_shader_parameter('clouds_a', cloud_textures[WEATHER[current].clouds])
		sky_mat.set_shader_parameter('clouds_b', cloud_textures[WEATHER[current].clouds])
		sky_mat.set_shader_parameter('cloud_blend', 0.0)
	else:
		if blend < 1.0:
			current = target
		target = weather_name
		blend = 0.0
		blend_speed = 1.0 / 8.0
		sky_mat.set_shader_parameter('clouds_a', cloud_textures[WEATHER[current].clouds])
		sky_mat.set_shader_parameter('clouds_b', cloud_textures[WEATHER[target].clouds])
	auto_change_in = _rng.randf_range(3.0, 7.0)
	if not instant:
		weather_changed.emit(weather_name)

func next_weather() -> String:
	var i := ORDER.find(target)
	var n: String = ORDER[(i + 1) % ORDER.size()]
	set_weather(n)
	return n

func wait_hours(hours: float) -> void:
	wait_left += hours

func set_hour(h: float) -> void:
	hour = fposmod(h, 24.0)

func clock_text() -> String:
	var h := int(hour)
	var m := int((hour - h) * 60.0)
	return '%02d:%02d' % [h, m]

# ---------------------------------------------------------------- simulation

func _process(delta: float) -> void:
	var advance := 0.0
	if wait_left > 0.0:
		var step := minf(wait_left, delta * 1.6)
		wait_left -= step
		advance += step
	elif time_flows:
		advance += delta * time_scale / 3600.0
	hour = fposmod(hour + advance, 24.0)
	auto_change_in -= advance
	if auto_change_in <= 0.0 and blend >= 1.0:
		_pick_random_weather()
	if blend < 1.0:
		blend = minf(1.0, blend + delta * blend_speed + advance * 0.6)
		if blend >= 1.0:
			current = target
			sky_mat.set_shader_parameter('clouds_a', cloud_textures[WEATHER[current].clouds])
			sky_mat.set_shader_parameter('clouds_b', cloud_textures[WEATHER[current].clouds])
	_update_thunder(delta)
	_apply(delta)

func _pick_random_weather() -> void:
	var total := 0
	for k in CHANCES:
		total += CHANCES[k]
	var r := _rng.randi_range(0, total - 1)
	for k in ORDER:
		r -= CHANCES[k]
		if r < 0:
			if k != target:
				blend_speed = 1.0 / 30.0
				if blend < 1.0:
					current = target
				target = k
				blend = 0.0
				sky_mat.set_shader_parameter('clouds_a', cloud_textures[WEATHER[current].clouds])
				sky_mat.set_shader_parameter('clouds_b', cloud_textures[WEATHER[target].clouds])
				weather_changed.emit(k)
			break
	auto_change_in = _rng.randf_range(3.0, 7.0)

func _update_thunder(delta: float) -> void:
	flash = maxf(0.0, flash - delta * 2.5)
	var storm := _value('thunder_amount')
	if storm > 0.5 and interior < 0.5:
		_thunder_timer -= delta
		if _thunder_timer <= 0.0:
			flash = _rng.randf_range(0.55, 1.0)
			_thunder_timer = _rng.randf_range(6.0, 18.0)
			_thunder_delay = _rng.randf_range(0.4, 2.2)
	if _thunder_delay > 0.0:
		_thunder_delay -= delta
		if _thunder_delay <= 0.0 and sounds.has('thunder'):
			sounds.thunder.pitch_scale = _rng.randf_range(0.8, 1.1)
			sounds.thunder.volume_db = _rng.randf_range(-6.0, 0.0)
			sounds.thunder.play()

func phase_weights(h: float) -> Array[float]:
	var s := func(a: float, b: float) -> float: return smoothstep(a, b, h)
	if h < 4.5 or h >= 20.5:
		return [0.0, 0.0, 0.0, 1.0]
	if h < 6.0:
		var t: float = s.call(4.5, 6.0)
		return [t, 0.0, 0.0, 1.0 - t]
	if h < 8.0:
		var t: float = s.call(6.0, 8.0)
		return [1.0 - t, t, 0.0, 0.0]
	if h < 16.5:
		return [0.0, 1.0, 0.0, 0.0]
	if h < 18.5:
		var t: float = s.call(16.5, 18.5)
		return [0.0, 1.0 - t, t, 0.0]
	var t_night: float = s.call(18.5, 20.5)
	return [0.0, 0.0, 1.0 - t_night, t_night]

static func sun_direction(h: float) -> Vector3:
	var a := (h - 5.6) / 12.8 * PI
	return Vector3(cos(a) * 0.92, sin(a) * 0.9, 0.34).normalized()

static func moon_direction(h: float, offset: float, tilt: float) -> Vector3:
	var a := (h - 17.2 + offset) / 13.5 * PI
	return Vector3(cos(a) * 0.9, sin(a) * 0.85, tilt).normalized()

func _mix4(colors: Array, w: Array[float]) -> Color:
	var c := Color(0, 0, 0, 1)
	for i in PHASES:
		c.r += colors[i].r * w[i]
		c.g += colors[i].g * w[i]
		c.b += colors[i].b * w[i]
	return c

func _weather_values(weather_name: String, w: Array[float]) -> Dictionary:
	var d: Dictionary = WEATHER[weather_name]
	var lp := 0.0
	for i in PHASES:
		lp += LIGHT_PHASE[i] * w[i]
	return {
		'sky': _mix4(d.sky, w), 'fog': _mix4(d.fog, w), 'ambient': _mix4(d.ambient, w), 'sun': _mix4(d.sun, w),
		'disc': d.disc, 'light': d.light * lp, 'fog_far': d.fog_far * (0.8 if w[3] > 0.5 else 1.0), 'cloud_speed': d.cloud_speed,
		'cloud_opacity': d.cloud_opacity, 'cloud_bright': d.cloud_bright, 'glare': d.glare, 'rain': d.rain, 'ash': d.ash,
		'wind': d.wind, 'stars': d.stars, 'shadow': d.shadow, 'thunder_amount': 1.0 if d.get('thunder', false) else 0.0,
	}

func _value(key: String) -> float:
	return blended.get(key, 0.0)

func _blend_dicts(a: Dictionary, b: Dictionary, t: float) -> Dictionary:
	var out := {}
	for k in a:
		if a[k] is Color:
			out[k] = (a[k] as Color).lerp(b[k], t)
		else:
			out[k] = lerpf(a[k], b[k], t)
	return out

func _apply(delta: float) -> void:
	var w := phase_weights(hour)
	var t := smoothstep(0.0, 1.0, blend)
	var v := _blend_dicts(_weather_values(current, w), _weather_values(target, w), t)
	blended = v
	var night: float = w[3]
	var twilight: float = w[0] + w[2]
	var sun_dir := sun_direction(hour)
	var masser := moon_direction(hour, 0.0, -0.42)
	var secunda := moon_direction(hour, -1.4, -0.2)

	# interior blend (mine)
	var fog_col: Color = (v.fog as Color).lerp(INTERIOR_FOG, interior)
	var fog_far: float = lerpf(v.fog_far, 42.0, interior)
	var amb: Color = (v.ambient as Color).lerp(INTERIOR_AMBIENT, interior)
	amb = amb.lerp(Color(0.75, 0.8, 0.95), flash * 0.4 * (1.0 - interior))

	# sky
	sky_mat.set_shader_parameter('sky_color', (v.sky as Color) + Color(flash, flash, flash) * 0.25)
	sky_mat.set_shader_parameter('horizon_color', v.fog)
	sky_mat.set_shader_parameter('sun_color', v.sun)
	sky_mat.set_shader_parameter('sun_disc_color', (v.sun as Color).lerp(v.disc, twilight))
	sky_mat.set_shader_parameter('sun_direction', sun_dir)
	var sun_vis := float(v.glare) * smoothstep(-0.06, 0.06, sun_dir.y)
	sky_mat.set_shader_parameter('sun_visibility', sun_vis)
	sky_mat.set_shader_parameter('sunset_glow', twilight * float(v.glare) * 0.9)
	var cloud_lit: Color = ((v.fog as Color).lerp(v.sky, 0.25) * 1.18 + (v.sun as Color) * 0.12) * float(v.cloud_bright)
	sky_mat.set_shader_parameter('cloud_lit', cloud_lit)
	sky_mat.set_shader_parameter('cloud_shade', cloud_lit * 0.6)
	sky_mat.set_shader_parameter('cloud_opacity', v.cloud_opacity)
	sky_mat.set_shader_parameter('cloud_blend', t)
	cloud_offset += Vector2(0.0035, 0.0012) * float(v.cloud_speed) * delta
	sky_mat.set_shader_parameter('cloud_offset', cloud_offset)
	sky_mat.set_shader_parameter('stars_alpha', night * float(v.stars) + twilight * 0.15 * float(v.stars))
	sky_mat.set_shader_parameter('moon_alpha', clampf(night + twilight * 0.6, 0.0, 1.0) * clampf(float(v.stars) * 1.3, 0.25, 1.0))
	sky_mat.set_shader_parameter('moon_large_dir', masser)
	sky_mat.set_shader_parameter('moon_small_dir', secunda)
	sky_mat.set_shader_parameter('flash', flash * 0.35)

	# fog
	env.fog_light_color = fog_col
	env.fog_depth_end = fog_far
	env.fog_depth_begin = fog_far * 0.06
	env.fog_sun_scatter = 0.25 * float(v.glare) * (1.0 - night) * (1.0 - interior)
	RenderingServer.global_shader_parameter_set('fog_color', fog_col.srgb_to_linear())
	RenderingServer.global_shader_parameter_set('fog_far', fog_far)
	env.ambient_light_color = amb
	env.ambient_light_energy = 1.0

	# sun / moon light
	var day_light := smoothstep(-0.05, 0.15, sun_dir.y)
	var moon_light := smoothstep(-0.04, -0.16, sun_dir.y) * smoothstep(0.0, 0.2, masser.y)
	var dir := sun_dir if sun_dir.y > -0.05 else masser
	var energy: float = float(v.light) * (day_light if sun_dir.y > -0.05 else moon_light * 0.9)
	energy *= (1.0 - interior)
	energy += flash * 0.8 * (1.0 - interior)
	if dir.y > 0.01:
		sun.look_at(sun.global_position - dir, Vector3.UP if absf(dir.y) < 0.99 else Vector3.FORWARD)
	sun.light_color = (v.sun as Color).lerp(Color(0.85, 0.9, 1.0), flash)
	sun.light_energy = energy
	sun.shadow_opacity = float(v.shadow) * (0.6 if night > 0.5 else 1.0)
	sun.visible = energy > 0.01

	# world state for other shaders and scripts
	night_factor = clampf(night + twilight * 0.45, 0.0, 1.0)
	RenderingServer.global_shader_parameter_set('night_factor', night_factor)
	RenderingServer.global_shader_parameter_set('sun_dir', sun_dir)
	RenderingServer.global_shader_parameter_set('wind_strength', v.wind)
	wetness = clampf(wetness + (float(v.rain) * 0.08 - 0.01) * delta, 0.0, 1.0)
	RenderingServer.global_shader_parameter_set('wetness', wetness * (1.0 - interior))
	for m in glow_materials:
		m.emission_energy_multiplier = night_factor * night_factor * 3.0
	if rain:
		rain.amount_ratio = float(v.rain) * (1.0 - interior)
		rain.emitting = rain.amount_ratio > 0.01
	if ash:
		ash.amount_ratio = float(v.ash) * (1.0 - interior)
		ash.emitting = ash.amount_ratio > 0.01
	if dust:
		dust.amount_ratio = float(v.ash) * (1.0 - interior)
		dust.emitting = dust.amount_ratio > 0.01
	_update_sound(v, night, delta)

func _update_sound(v: Dictionary, night: float, delta: float) -> void:
	var player := get_parent().get_node_or_null('Player') as Node3D
	var coast := 0.0
	if player:
		coast = clampf(1.0 - (60.0 - player.global_position.z) / 60.0, 0.0, 1.0) * (1.0 - interior)
	var targets := {
		'wind': lerpf(-26.0, -8.0, clampf(float(v.wind) + float(v.ash) * 0.3, 0.0, 1.0)) if interior < 0.9 else -32.0,
		'rain': lerpf(-60.0, -6.0, float(v.rain)) if interior < 0.5 else -60.0,
		'waves': lerpf(-60.0, -10.0, coast),
		'crickets': lerpf(-60.0, -18.0, night * (1.0 - float(v.rain)) * (1.0 - interior)),
		'birds': lerpf(-60.0, -22.0, (1.0 - night) * float(v.glare) * (1.0 - interior)),
	}
	for k in sounds:
		if targets.has(k):
			var p: AudioStreamPlayer = sounds[k]
			p.volume_db = lerpf(p.volume_db, targets[k], clampf(delta * 1.5, 0.0, 1.0))
