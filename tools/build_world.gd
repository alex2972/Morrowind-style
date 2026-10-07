extends SceneTree
## Assembles res://scenes/world/veyr.tscn from the generated assets.
##   Godot --headless --path . --script res://tools/build_world.gd

const MaterialLibrary := preload('res://client/world/material_library.gd')
const AssetLibrary := preload('res://client/world/asset_library.gd')
const TerrainBuilder := preload('res://client/world/terrain_builder.gd')

const LAYER_WORLD := 1
const LAYER_INTERIOR := 2
const LAYER_SMALL := 4
const LAYER_VIEWMODEL := 8
const LAYER_PLAYER := 16
const FLORA_CELL := 32.0

var mats
var lib
var terrain
var layout: Dictionary
var world: Node3D
var groups := {}
var rng := RandomNumberGenerator.new()

func _init() -> void:
	call_deferred('build')

func group(name: String) -> Node3D:
	if not groups.has(name):
		var n := Node3D.new()
		n.name = name.to_pascal_case()
		world.add_child(n)
		groups[name] = n
	return groups[name]

func build() -> void:
	rng.seed = 2026
	layout = JSON.parse_string(FileAccess.get_file_as_string('res://assets/terrain_src/layout.json'))
	mats = MaterialLibrary.new()
	mats.build_all()
	lib = AssetLibrary.new(mats)
	terrain = TerrainBuilder.new(layout)
	world = Node3D.new()
	world.name = 'Veyr'
	world.set_script(load('res://client/world/world.gd'))
	_environment()
	world.add_child(terrain.build())
	var water: MeshInstance3D = terrain.build_water()
	world.add_child(water)
	water.set('reflect_mask', LAYER_WORLD | LAYER_PLAYER)
	world.add_child(terrain.build_distant(rng))
	_castle()
	_objects()
	_flora()
	_tunnel()
	_player()
	_ui()
	var path := PackedVector3Array()
	for p in layout.tunnel:
		path.append(Vector3(p[0], p[1], p[2]))
	world.set('tunnel_path', path)
	world.set('regions', layout.regions)
	world.set('map_half', float(layout.half))
	world.set('splat_b_texture', load('res://assets/terrain/splat_b.res'))
	_own(world, world)
	var packed := PackedScene.new()
	var err := packed.pack(world)
	if err == OK:
		DirAccess.make_dir_recursive_absolute('res://scenes/world')
		err = ResourceSaver.save(packed, 'res://scenes/world/veyr.tscn')
	print('WORLD_BUILD ', err, ' nodes=', _count(world), ' objects=', layout.objects.size(), ' flora=', layout.flora.size())
	world.free()
	quit(err)

func _count(n: Node) -> int:
	var c := 1
	for k in n.get_children():
		c += _count(k)
	return c

func _own(node: Node, owner: Node) -> void:
	for c in node.get_children():
		c.owner = owner
		if c.scene_file_path == '':
			_own(c, owner)

# ------------------------------------------------------------------------------------------

func _environment() -> void:
	var we := WorldEnvironment.new()
	we.name = 'WorldEnvironment'
	var e := Environment.new()
	e.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sm := ShaderMaterial.new()
	sm.shader = load('res://shaders/sky.gdshader')
	sm.set_shader_parameter('stars_tex', load('res://assets/textures/stars.png'))
	sm.set_shader_parameter('moon_large_tex', load('res://assets/textures/moon_large.png'))
	sm.set_shader_parameter('moon_small_tex', load('res://assets/textures/moon_small.png'))
	sm.set_shader_parameter('clouds_a', load('res://assets/textures/sky_clear.png'))
	sm.set_shader_parameter('clouds_b', load('res://assets/textures/sky_clear.png'))
	sky.sky_material = sm
	sky.radiance_size = Sky.RADIANCE_SIZE_32
	e.sky = sky
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	e.tonemap_exposure = 1.1
	e.tonemap_white = 4.0
	e.fog_enabled = true
	e.fog_mode = Environment.FOG_MODE_DEPTH
	e.fog_density = 1.0
	e.fog_depth_begin = 15.0
	e.fog_depth_end = 300.0
	e.fog_depth_curve = 1.5
	e.fog_sky_affect = 0.0
	e.fog_light_energy = 1.0
	e.glow_enabled = true
	e.glow_intensity = 0.55
	e.glow_strength = 1.0
	e.glow_bloom = 0.02
	e.glow_hdr_threshold = 1.1
	e.glow_blend_mode = Environment.GLOW_BLEND_MODE_SOFTLIGHT
	e.adjustment_enabled = true
	e.adjustment_saturation = 0.95
	e.adjustment_contrast = 1.04
	we.environment = e
	world.add_child(we)
	var sun := DirectionalLight3D.new()
	sun.name = 'Sun'
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	sun.directional_shadow_max_distance = 150.0
	sun.light_angular_distance = 0.6
	sun.shadow_blur = 1.2
	sun.shadow_bias = 0.16
	sun.shadow_normal_bias = 2.6
	sun.light_specular = 0.25
	sun.light_cull_mask = 0xFFFFF & ~LAYER_INTERIOR
	world.add_child(sun)
	var weather := Node.new()
	weather.name = 'Weather'
	weather.set_script(load('res://client/world/weather.gd'))
	world.add_child(weather)

func _castle() -> void:
	var src: PackedScene = load('res://assets/models/castle.glb')
	var inst := src.instantiate()
	var meshes := []
	lib._collect_meshes(inst, Transform3D.IDENTITY, meshes)
	var m := ShaderMaterial.new()
	m.shader = load('res://shaders/distant.gdshader')
	m.set_shader_parameter('albedo_tex', load('res://assets/textures/castle_stone.png'))
	m.set_shader_parameter('uv_scale', 0.08)
	m.set_shader_parameter('min_haze', 0.2)
	m.set_shader_parameter('max_haze', 0.8)
	m.set_shader_parameter('haze_reach', 4.0)
	m.set_shader_parameter('tint', Color(0.55, 0.52, 0.5))
	ResourceSaver.save(m, 'res://materials/distant_castle.tres')
	m = load('res://materials/distant_castle.tres')
	var root := Node3D.new()
	root.name = 'IslandFortress'
	root.position = Vector3(-215, -1.5, 270)
	root.rotation.y = deg_to_rad(205)
	for pair in meshes:
		var mi := MeshInstance3D.new()
		mi.name = 'Fortress'
		mi.mesh = pair[0].mesh
		mi.transform = pair[1]
		mi.material_override = m
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(mi)
	inst.free()
	# rocky islets
	for i in 9:
		var r: PackedScene = lib.scene(['rock_cliff', 'rock_cliff_b', 'rock_b'][i % 3])
		var n := r.instantiate()
		var a := TAU * i / 9.0
		n.position = Vector3(cos(a) * 52.0, -3.0, sin(a) * 34.0)
		n.rotation.y = a
		n.scale = Vector3.ONE * rng.randf_range(3.0, 5.0)
		root.add_child(n)
	group('distant').add_child(root)

func _objects() -> void:
	for o in layout.objects:
		var key: String = o.m
		var interior: bool = o.g == 'mine_interior'
		var ps: PackedScene = lib.scene(key, interior)
		var n: Node3D = ps.instantiate()
		n.position = Vector3(o.p[0], o.p[1], o.p[2])
		n.rotation.y = float(o.r)
		n.scale = Vector3.ONE * float(o.s)
		group(o.g).add_child(n, true)

func _flora() -> void:
	var buckets := {}
	for f in layout.flora:
		var cx := int(floor((float(f.p[0]) + 256.0) / FLORA_CELL))
		var cz := int(floor((float(f.p[2]) + 256.0) / FLORA_CELL))
		var k := '%s|%d|%d' % [f.m, cx, cz]
		if not buckets.has(k):
			buckets[k] = []
		var basis := Basis(Vector3.UP, float(f.r)).scaled(Vector3.ONE * float(f.s))
		buckets[k].append(Transform3D(basis, Vector3(f.p[0], f.p[1], f.p[2])))
	var parent := group('flora')
	for k in buckets:
		var parts: PackedStringArray = k.split('|')
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = lib.flora_mesh(parts[0])
		var list: Array = buckets[k]
		mm.instance_count = list.size()
		for i in list.size():
			mm.set_instance_transform(i, list[i])
		var mmi := MultiMeshInstance3D.new()
		mmi.name = '%s_%s_%s' % [parts[0].to_pascal_case(), parts[1], parts[2]]
		mmi.multimesh = mm
		mmi.layers = LAYER_SMALL
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mmi.visibility_range_end = 95.0
		mmi.visibility_range_end_margin = 10.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		parent.add_child(mmi)

func _tunnel() -> void:
	var n: Node3D = lib.scene('mine_tunnel').instantiate()
	n.name = 'MineTunnel'
	group('mine_interior').add_child(n)

func _particles(name: String, amount: int, lifetime: float, extents: Vector3, offset: Vector3, dir: Vector3,
		speed: Vector2, grav: Vector3, size: Vector2, color: Color, texture: String) -> GPUParticles3D:
	var p := GPUParticles3D.new()
	p.name = name
	p.amount = amount
	p.lifetime = lifetime
	p.local_coords = false
	p.emitting = false
	p.position = offset
	p.visibility_aabb = AABB(Vector3(-30, -35, -30), Vector3(60, 55, 60))
	p.preprocess = lifetime
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = extents
	pm.direction = dir
	pm.spread = 4.0
	pm.initial_velocity_min = speed.x
	pm.initial_velocity_max = speed.y
	pm.gravity = grav
	p.process_material = pm
	var q := QuadMesh.new()
	q.size = size
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_color = color
	m.albedo_texture = load('res://assets/textures/%s.png' % texture)
	m.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	m.vertex_color_use_as_albedo = true
	q.material = m
	p.draw_pass_1 = q
	return p

func _player() -> void:
	var p := CharacterBody3D.new()
	p.name = 'Player'
	p.set_script(load('res://client/player/player.gd'))
	p.floor_max_angle = deg_to_rad(46.0)
	p.floor_snap_length = 0.5
	p.safe_margin = 0.02
	var col := CollisionShape3D.new()
	col.name = 'Body'
	var cap := CapsuleShape3D.new()
	cap.radius = 0.32
	cap.height = 1.78
	col.shape = cap
	col.position.y = 0.89
	p.add_child(col)
	var head := Node3D.new()
	head.name = 'Head'
	head.position.y = 1.62
	p.add_child(head)
	var cam := Camera3D.new()
	cam.name = 'Camera3D'
	cam.fov = 75.0
	cam.near = 0.05
	cam.far = 1600.0
	cam.cull_mask = LAYER_WORLD | LAYER_INTERIOR | LAYER_SMALL | LAYER_VIEWMODEL | LAYER_PLAYER
	cam.current = true
	head.add_child(cam)
	var vm := Node3D.new()
	vm.name = 'Viewmodel'
	cam.add_child(vm)
	# right hand: longsword held point-up, leaning in toward the centre of view
	var sword := Node3D.new()
	sword.name = 'SwordRig'
	sword.position = Vector3(0.3, -0.33, -0.5)
	sword.rotation = Vector3(-0.72, 0.22, 0.52)
	vm.add_child(sword)
	sword.add_child(lib.viewmodel_mesh('fp_sword'))
	var rh: MeshInstance3D = lib.viewmodel_mesh('fp_hand')
	rh.name = 'RightHand'
	sword.add_child(rh)
	# left hand: torch
	var torch := Node3D.new()
	torch.name = 'TorchRig'
	torch.position = Vector3(-0.36, -0.4, -0.55)
	torch.rotation = Vector3(-0.3, 0.0, -0.16)
	vm.add_child(torch)
	torch.add_child(lib.viewmodel_mesh('fp_torch'))
	var lh: MeshInstance3D = lib.viewmodel_mesh('fp_hand')
	lh.name = 'LeftHand'
	lh.scale = Vector3(-1, 1, 1)
	torch.add_child(lh)
	var flame := MeshInstance3D.new()
	flame.name = 'Flame'
	var q := QuadMesh.new()
	q.size = Vector2(0.2, 0.3)
	q.center_offset = Vector3(0, 0.15, 0)
	flame.mesh = q
	flame.position = Vector3(0, 0.42, 0)
	flame.material_override = mats.get_material('flame')
	flame.layers = LAYER_VIEWMODEL
	flame.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	torch.add_child(flame)
	var tl := OmniLight3D.new()
	tl.name = 'TorchLight'
	tl.position = Vector3(0, 0.6, 0)
	tl.light_color = Color(1.0, 0.62, 0.3)
	tl.light_energy = 1.7
	tl.omni_range = 12.0
	tl.omni_attenuation = 1.3
	tl.shadow_enabled = true
	tl.light_specular = 0.0
	torch.add_child(tl)
	var steps := AudioStreamPlayer.new()
	steps.name = 'Footsteps'
	steps.volume_db = -8.0
	p.add_child(steps)
	var precip := Node3D.new()
	precip.name = 'Precipitation'
	p.add_child(precip)
	precip.add_child(_particles('Rain', 6000, 1.15, Vector3(20, 1, 20), Vector3(0, 14, 0), Vector3(0.06, -1, 0.03),
			Vector2(15, 18), Vector3(0, -9.8, 0), Vector2(0.035, 1.3), Color(0.8, 0.82, 0.86, 0.5), 'rain_streak'))
	precip.add_child(_particles('Ash', 3000, 2.4, Vector3(24, 7, 24), Vector3(-14, 3, 0), Vector3(1, -0.08, 0.35),
			Vector2(9, 14), Vector3(0, -0.4, 0), Vector2(0.12, 0.12), Color(0.3, 0.23, 0.19, 0.85), 'glow_dot'))
	var dust := _particles('Dust', 260, 3.2, Vector3(26, 4, 26), Vector3(-20, 2.5, 0), Vector3(1, 0.02, 0.3),
			Vector2(10, 15), Vector3(0, 0, 0), Vector2(10, 7), Color(0.42, 0.3, 0.24, 0.24), 'glow_dot')
	((dust.draw_pass_1 as QuadMesh).material as StandardMaterial3D).billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	precip.add_child(dust)
	# the player's own body: hidden in first person, shown in third person (Tab)
	var body: Node3D = lib.scene('player_body').instantiate()
	body.name = 'Model'
	body.rotation.y = PI
	body.scale = Vector3.ONE * 0.94
	body.visible = false
	p.add_child(body)
	var spawn: Dictionary = layout.spawn
	p.position = Vector3(spawn.p[0], spawn.p[1], spawn.p[2])
	p.rotation.y = float(spawn.yaw)
	world.add_child(p)

func _ui() -> void:
	var hud := CanvasLayer.new()
	hud.name = 'HUD'
	hud.set_script(load('res://client/ui/hud.gd'))
	world.add_child(hud)
	var glare := CanvasLayer.new()
	glare.name = 'SunGlare'
	glare.set_script(load('res://client/ui/sun_glare.gd'))
	world.add_child(glare)
