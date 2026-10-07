extends RefCounted
## Builds the shared material resources (res://materials/*.tres) from tools/materials.json.
## Surfaces are matte (Lambert, no specular) like the original game; foliage uses a wind shader.

const TABLE_PATH := 'res://tools/materials.json'
const OUT_DIR := 'res://materials/'

var table: Dictionary = {}
var cache: Dictionary = {}
var viewmodel_cache: Dictionary = {}

func _init() -> void:
	table = JSON.parse_string(FileAccess.get_file_as_string(TABLE_PATH))
	DirAccess.make_dir_recursive_absolute(OUT_DIR)

func tex(name: String) -> Texture2D:
	return load('res://assets/textures/%s.png' % name)

func get_material(key: String) -> Material:
	if cache.has(key):
		return cache[key]
	var info: Dictionary = table.get(key, {})
	var m: Material
	if info.get('foliage', false):
		var sm := ShaderMaterial.new()
		sm.shader = load('res://shaders/foliage.gdshader')
		sm.set_shader_parameter('albedo_tex', tex(info.tex))
		if key in ['grass_tuft', 'fern', 'flowers']:
			sm.set_shader_parameter('sway', 2.2)
		if key == 'hanging_moss':
			sm.set_shader_parameter('sway', 1.6)
		m = sm
	elif info.get('flame', false):
		var fm := ShaderMaterial.new()
		fm.shader = load('res://shaders/flame.gdshader')
		fm.set_shader_parameter('flame_tex', tex('flame'))
		fm.set_shader_parameter('noise_tex', tex('t_macro'))
		m = fm
	else:
		var s := StandardMaterial3D.new()
		s.diffuse_mode = BaseMaterial3D.DIFFUSE_LAMBERT
		s.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
		s.roughness = 1.0
		s.vertex_color_use_as_albedo = true
		s.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
		if info.has('tex'):
			s.albedo_texture = tex(info.tex)
		if info.has('color'):
			var c: Array = info.color
			s.albedo_color = Color(c[0], c[1], c[2])
		if info.has('emission'):
			var e: Array = info.emission
			s.emission_enabled = true
			s.emission = Color(e[0], e[1], e[2])
			s.emission_energy_multiplier = info.get('energy', 1.0)
		if info.has('glow'):
			s.emission_enabled = true
			s.emission_texture = tex(info.glow)
			s.emission = Color.WHITE
			s.emission_operator = BaseMaterial3D.EMISSION_OP_MULTIPLY
			s.emission_energy_multiplier = 0.0
		if info.get('triplanar', false):
			s.uv1_triplanar = true
			s.uv1_world_triplanar = true
			s.uv1_triplanar_sharpness = 2.0
			s.uv1_scale = Vector3.ONE / float(info.get('scale', 4.0))
		if info.get('metal', false):
			s.specular_mode = BaseMaterial3D.SPECULAR_SCHLICK_GGX
			s.diffuse_mode = BaseMaterial3D.DIFFUSE_BURLEY
			s.metallic = 0.0
			s.metallic_specular = 0.8
			s.roughness = 0.32
		if info.get('double_sided', false):
			s.cull_mode = BaseMaterial3D.CULL_DISABLED
		if info.get('no_receive_shadows', false):
			# like the original game's actors: shading comes from the texture and the lights, not
			# from shadow maps (which also acne on flat-shaded low-poly facets)
			s.disable_receive_shadows = true
		if key == 'collision':
			s.albedo_color = Color(1, 0, 1)
		m = s
	m.resource_name = key
	var path := OUT_DIR + key + '.tres'
	ResourceSaver.save(m, path)
	var stored: Material = ResourceLoader.load(path, '', ResourceLoader.CACHE_MODE_REPLACE)
	cache[key] = stored
	return stored

func viewmodel_material(key: String) -> Material:
	## Variant that never clips into walls and keeps its own field of view.
	if viewmodel_cache.has(key):
		return viewmodel_cache[key]
	var base := get_material(key)
	var m: Material = base.duplicate()
	if m is BaseMaterial3D:
		var b := m as BaseMaterial3D
		b.use_z_clip_scale = true
		b.z_clip_scale = 0.25
		b.use_fov_override = true
		b.fov_override = 70.0
	m.resource_name = key + '_viewmodel'
	var path := OUT_DIR + key + '_viewmodel.tres'
	ResourceSaver.save(m, path)
	m = ResourceLoader.load(path, '', ResourceLoader.CACHE_MODE_REPLACE)
	viewmodel_cache[key] = m
	return m

func build_all() -> void:
	for key in table:
		if not key.begins_with('_'):
			get_material(key)
