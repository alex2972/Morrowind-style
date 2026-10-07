extends RefCounted
## Turns the Blender GLB models into reusable prop scenes (res://scenes/props/*.tscn):
## shared materials by name, collision from "<name>_hull" meshes, render layers,
## visibility ranges, plus lights and flames for torches, lamps and lanterns.

const LAYER_WORLD := 1
const LAYER_INTERIOR := 2
const LAYER_SMALL := 4
const LAYER_VIEWMODEL := 8
const LAYER_PLAYER := 16

const FLORA := ['grass_clump', 'reeds', 'fern_plant', 'flower_plant', 'bush', 'bush_swamp', 'mushrooms']
const SMALL := ['barrel', 'crate', 'crate_small', 'crate_long', 'sack', 'urn', 'urn_tall', 'basket', 'bench', 'table',
	'signpost', 'fence', 'lantern_hanging', 'ore_crystals', 'mine_cart', 'rail_segment', 'rail_trestle', 'well',
	'market_stall', 'planter', 'rowboat', 'torch_post', 'lamp_post', 'stone_pillar']
const NO_SHADOW := ['rail_segment', 'ore_crystals', 'lantern_hanging']
const WOOD := ['dock', 'rowboat', 'market_stall', 'bench', 'table', 'crate', 'crate_small', 'crate_long', 'barrel', 'rail_trestle', 'mine_cart']
const SOFT := ['mine_tunnel', 'tree_coastal', 'tree_coastal_b', 'tree_broad', 'tree_broad_b', 'tree_swamp', 'tree_dead', 'tree_dead_b', 'tree_sapling']

var mats
var scenes := {}
var flora_meshes := {}

func _init(material_library) -> void:
	mats = material_library
	DirAccess.make_dir_recursive_absolute('res://scenes/props')
	DirAccess.make_dir_recursive_absolute('res://assets/generated')

func model_keys() -> PackedStringArray:
	var out := PackedStringArray()
	for f in DirAccess.get_files_at('res://assets/models'):
		if f.ends_with('.glb'):
			out.append(f.get_basename())
	return out

func _collect_meshes(node: Node, xf: Transform3D, out: Array) -> void:
	var local := xf
	if node is Node3D:
		local = xf * (node as Node3D).transform
	if node is MeshInstance3D:
		out.append([node, local])
	for c in node.get_children():
		_collect_meshes(c, local, out)

func _surface_material(mesh: Mesh, i: int) -> String:
	var m := mesh.surface_get_material(i)
	return m.resource_name if m else 'dark'

func _visibility(key: String) -> float:
	if key in FLORA:
		return 70.0
	if key in SMALL:
		return 130.0
	if key.begins_with('tree'):
		return 380.0
	if key.begins_with('rock'):
		return 460.0
	return 0.0

# character models (skinned, layer PLAYER) and their materials
const CHARACTERS := {'player_body': 'char_skin', 'player_body_female': 'char_skin_female'}

func build_scene(key: String, interior := false) -> PackedScene:
	var src: PackedScene = load('res://assets/models/%s.glb' % key)
	if key in CHARACTERS:
		return _build_character_scene(src, key)
	var inst := src.instantiate()
	var meshes := []
	_collect_meshes(inst, Transform3D.IDENTITY, meshes)
	var root := Node3D.new()
	root.name = key.to_pascal_case()
	var layer := LAYER_INTERIOR if interior or key == 'mine_tunnel' else (LAYER_SMALL if key in SMALL else LAYER_WORLD)
	if key == 'player_body':
		layer = LAYER_PLAYER
	for pair in meshes:
		var node: MeshInstance3D = pair[0]
		var xf: Transform3D = pair[1]
		if String(node.name).ends_with('_hull'):
			var body := StaticBody3D.new()
			body.name = 'Collision'
			body.transform = xf
			var cs := CollisionShape3D.new()
			cs.name = 'Shape'
			var shape := node.mesh.create_trimesh_shape()
			if key == 'mine_tunnel':
				shape.backface_collision = true
			cs.shape = shape
			body.add_child(cs)
			body.set_meta('surface', 'wood' if key in WOOD else ('soft' if key in SOFT else 'stone'))
			root.add_child(body)
			continue
		var mi := MeshInstance3D.new()
		mi.name = 'Visual'
		mi.mesh = node.mesh
		mi.transform = xf
		for i in node.mesh.get_surface_count():
			mi.set_surface_override_material(i, mats.get_material(_surface_material(node.mesh, i)))
		mi.layers = layer
		var vr := _visibility(key)
		if vr > 0.0 and not interior:
			mi.visibility_range_end = vr
			mi.visibility_range_end_margin = vr * 0.08
			mi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		if key in NO_SHADOW or key in FLORA:
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(mi)
	inst.free()
	_add_extras(key, root, interior)
	_own(root, root)
	var packed := PackedScene.new()
	packed.pack(root)
	var path := 'res://scenes/props/%s%s.tscn' % [key, '_interior' if interior else '']
	ResourceSaver.save(packed, path)
	root.free()
	return ResourceLoader.load(path, '', ResourceLoader.CACHE_MODE_REPLACE)

func _build_character_scene(source: PackedScene, key: String) -> PackedScene:
	# Skinned meshes depend on their complete skeleton hierarchy and animation paths.
	var root := source.instantiate()
	root.name = key.to_pascal_case()
	for node in root.find_children('*', '', true, false):
		if node is MeshInstance3D:
			node.layers = LAYER_PLAYER
			node.extra_cull_margin = 1.0
			for surface in node.mesh.get_surface_count():
				node.set_surface_override_material(surface, mats.get_material(CHARACTERS[key]))
		elif node is AnimationPlayer:
			node.name = 'AnimationPlayer'
			node.playback_default_blend_time = 0.18
			for clip in ['idle', 'walk', 'run', 'walk_backward', 'strafe_left', 'strafe_right', 'combat_idle', 'fall']:
				if node.has_animation(clip):
					node.get_animation(clip).loop_mode = Animation.LOOP_LINEAR
	_own(root, root)
	var packed := PackedScene.new()
	packed.pack(root)
	var path := 'res://scenes/props/%s.tscn' % key
	ResourceSaver.save(packed, path)
	root.free()
	return ResourceLoader.load(path, '', ResourceLoader.CACHE_MODE_REPLACE)

func _light(root: Node3D, pos: Vector3, color: Color, energy: float, range_m: float, flicker := true) -> OmniLight3D:
	var l := OmniLight3D.new()
	l.name = 'Light'
	l.position = pos
	l.light_color = color
	l.light_energy = energy
	l.omni_range = range_m
	l.omni_attenuation = 1.4
	l.light_specular = 0.0
	l.distance_fade_enabled = true
	l.distance_fade_begin = 90.0
	l.distance_fade_length = 30.0
	if flicker:
		l.set_meta('flicker', energy)
	root.add_child(l)
	return l

func _flame(root: Node3D, pos: Vector3, size: Vector2, seed: float) -> void:
	var f := MeshInstance3D.new()
	f.name = 'Flame'
	var q := QuadMesh.new()
	q.size = size
	q.center_offset = Vector3(0, size.y * 0.5, 0)
	f.mesh = q
	f.position = pos
	var m: ShaderMaterial = mats.get_material('flame').duplicate()
	m.set_shader_parameter('seed', seed)
	f.material_override = m
	f.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	f.layers = LAYER_SMALL
	f.extra_cull_margin = 1.0
	root.add_child(f)

func _add_extras(key: String, root: Node3D, interior: bool) -> void:
	match key:
		'torch_post':
			_flame(root, Vector3(0, 2.86, 0), Vector2(0.55, 0.85), 0.3)
			_light(root, Vector3(0, 3.25, 0), Color(1.0, 0.6, 0.28), 1.8, 11.0)
		'lamp_post':
			_light(root, Vector3(0, 3.42, 0), Color(1.0, 0.74, 0.44), 1.5, 10.0, false)
		'lantern_hanging':
			_light(root, Vector3(0, -0.3, 0.5), Color(1.0, 0.66, 0.34), 2.2 if interior else 1.4, 10.0 if interior else 8.0)
		'lighthouse':
			var beacon := _light(root, Vector3(0, 18.8, 0), Color(1.0, 0.72, 0.4), 3.0, 40.0, false)
			beacon.set_meta('night_only', 3.0)
			beacon.distance_fade_enabled = false
		'ore_crystals':
			_light(root, Vector3(0, 0.6, 0), Color(0.35, 0.78, 0.9), 0.9, 5.5, false)

func _own(node: Node, owner: Node) -> void:
	for c in node.get_children():
		c.owner = owner
		_own(c, owner)

func scene(key: String, interior := false) -> PackedScene:
	var k := key + ('#i' if interior else '')
	if not scenes.has(k):
		scenes[k] = build_scene(key, interior)
	return scenes[k]

func flora_mesh(key: String) -> Mesh:
	if flora_meshes.has(key):
		return flora_meshes[key]
	var src: PackedScene = load('res://assets/models/%s.glb' % key)
	var inst := src.instantiate()
	var meshes := []
	_collect_meshes(inst, Transform3D.IDENTITY, meshes)
	var mesh: ArrayMesh = (meshes[0][0] as MeshInstance3D).mesh.duplicate()
	for i in mesh.get_surface_count():
		mesh.surface_set_material(i, mats.get_material(_surface_material(mesh, i)))
	inst.free()
	var path := 'res://assets/generated/flora_%s.res' % key
	ResourceSaver.save(mesh, path)
	flora_meshes[key] = ResourceLoader.load(path, '', ResourceLoader.CACHE_MODE_REPLACE)
	return flora_meshes[key]

func viewmodel_mesh(key: String) -> MeshInstance3D:
	var src: PackedScene = load('res://assets/models/%s.glb' % key)
	var inst := src.instantiate()
	var meshes := []
	_collect_meshes(inst, Transform3D.IDENTITY, meshes)
	var node: MeshInstance3D = meshes[0][0]
	var mi := MeshInstance3D.new()
	mi.name = key.to_pascal_case()
	mi.mesh = node.mesh
	for i in node.mesh.get_surface_count():
		mi.set_surface_override_material(i, mats.viewmodel_material(_surface_material(node.mesh, i)))
	mi.layers = LAYER_VIEWMODEL
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	inst.free()
	return mi
