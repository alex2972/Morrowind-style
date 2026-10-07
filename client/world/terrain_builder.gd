extends RefCounted
## Builds the landscape from assets/terrain_src (written by tools/build_terrain.py):
## 64 m chunks with smooth normals, trimesh collision (with the mine-mouth hole), the splat
## terrain material, the sea plane and a ring of distant mountains.

const SRC := 'res://assets/terrain_src/'
const OUT := 'res://assets/terrain/'
const CHUNK := 32  # quads per chunk side

var n := 0
var res := 2.0
var half := 256.0
var heights := PackedFloat32Array()
var holes: Image
var layout: Dictionary

func _init(layout_data: Dictionary) -> void:
	layout = layout_data
	n = int(layout.size)
	res = float(layout.res)
	half = float(layout.half)
	var f := FileAccess.open(SRC + 'height.bin', FileAccess.READ)
	heights = f.get_buffer(f.get_length()).to_float32_array()
	holes = Image.load_from_file(ProjectSettings.globalize_path(SRC + 'holes.png'))
	DirAccess.make_dir_recursive_absolute(OUT)

func h(ix: int, iz: int) -> float:
	return heights[clampi(iz, 0, n - 1) * n + clampi(ix, 0, n - 1)]

func height_at(x: float, z: float) -> float:
	var fx := (x + half) / res
	var fz := (z + half) / res
	var ix := clampi(int(floor(fx)), 0, n - 2)
	var iz := clampi(int(floor(fz)), 0, n - 2)
	var u := fx - ix
	var v := fz - iz
	var h00 := h(ix, iz)
	var h10 := h(ix + 1, iz)
	var h01 := h(ix, iz + 1)
	var h11 := h(ix + 1, iz + 1)
	if u >= v:
		return h00 + (h10 - h00) * u + (h11 - h10) * v
	return h00 + (h11 - h01) * u + (h01 - h00) * v

func normal_at(ix: int, iz: int) -> Vector3:
	var dx := (h(ix + 1, iz) - h(ix - 1, iz)) / (2.0 * res)
	var dz := (h(ix, iz + 1) - h(ix, iz - 1)) / (2.0 * res)
	return Vector3(-dx, 1.0, -dz).normalized()

func is_hole(ix: int, iz: int) -> bool:
	return holes.get_pixel(clampi(ix, 0, n - 1), clampi(iz, 0, n - 1)).r > 0.5

func _texture_resource(name: String, mipmaps := true) -> Texture2D:
	var img := Image.load_from_file(ProjectSettings.globalize_path(SRC + name + '.png'))
	if mipmaps:
		img.generate_mipmaps()
	var t := ImageTexture.create_from_image(img)
	var path := OUT + name + '.res'
	ResourceSaver.save(t, path)
	return ResourceLoader.load(path, '', ResourceLoader.CACHE_MODE_REPLACE)

func material() -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load('res://shaders/terrain.gdshader')
	m.set_shader_parameter('splat_a', _texture_resource('splat_a', false))
	m.set_shader_parameter('splat_b', _texture_resource('splat_b', false))
	m.set_shader_parameter('tint_map', _texture_resource('tint', false))
	m.set_shader_parameter('macro_tex', load('res://assets/textures/t_macro.png'))
	m.set_shader_parameter('map_half', half)
	for pair in [['tex_grass', 't_grass'], ['tex_dirt', 't_dirt'], ['tex_rock', 't_rock'], ['tex_mud', 't_mud'],
			['tex_ash', 't_ash'], ['tex_sand', 't_sand'], ['tex_cobble', 't_cobble'], ['tex_road', 't_road']]:
		m.set_shader_parameter(pair[0], load('res://assets/textures/%s.png' % pair[1]))
	ResourceSaver.save(m, OUT + 'terrain_material.tres')
	return ResourceLoader.load(OUT + 'terrain_material.tres', '', ResourceLoader.CACHE_MODE_REPLACE)

func build() -> Node3D:
	var root := Node3D.new()
	root.name = 'Terrain'
	var mat := material()
	var chunks := (n - 1) / CHUNK
	for cz in chunks:
		for cx in chunks:
			var verts := PackedVector3Array()
			var norms := PackedVector3Array()
			var uvs := PackedVector2Array()
			var idx := PackedInt32Array()
			var faces := PackedVector3Array()
			var base_x := cx * CHUNK
			var base_z := cz * CHUNK
			for j in CHUNK + 1:
				for i in CHUNK + 1:
					var ix := base_x + i
					var iz := base_z + j
					var p := Vector3(-half + ix * res, h(ix, iz), -half + iz * res)
					verts.append(p)
					norms.append(normal_at(ix, iz))
					uvs.append(Vector2(p.x, p.z))
			for j in CHUNK:
				for i in CHUNK:
					var ix := base_x + i
					var iz := base_z + j
					if is_hole(ix, iz) or is_hole(ix + 1, iz) or is_hole(ix, iz + 1) or is_hole(ix + 1, iz + 1):
						continue
					var a := j * (CHUNK + 1) + i
					var b := a + 1
					var c := a + CHUNK + 1
					var d := c + 1
					# split along (x0,z0)-(x1,z1), clockwise when seen from above (Godot front faces)
					for tri in [[a, b, d], [a, d, c]]:
						for k in tri:
							idx.append(k)
							faces.append(verts[k])
			var arrays := []
			arrays.resize(Mesh.ARRAY_MAX)
			arrays[Mesh.ARRAY_VERTEX] = verts
			arrays[Mesh.ARRAY_NORMAL] = norms
			arrays[Mesh.ARRAY_TEX_UV] = uvs
			arrays[Mesh.ARRAY_INDEX] = idx
			var mesh := ArrayMesh.new()
			mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
			var mpath := OUT + 'chunk_%d_%d.res' % [cx, cz]
			ResourceSaver.save(mesh, mpath)
			var mi := MeshInstance3D.new()
			mi.name = 'Chunk_%d_%d' % [cx, cz]
			mi.mesh = ResourceLoader.load(mpath, '', ResourceLoader.CACHE_MODE_REPLACE)
			mi.material_override = mat
			mi.layers = 1
			root.add_child(mi)
			var body := StaticBody3D.new()
			body.name = 'Collision'
			body.set_meta('terrain', true)
			var cs := CollisionShape3D.new()
			cs.name = 'Shape'
			var shape := ConcavePolygonShape3D.new()
			shape.set_faces(faces)
			var spath := OUT + 'collision_%d_%d.res' % [cx, cz]
			ResourceSaver.save(shape, spath)
			cs.shape = ResourceLoader.load(spath, '', ResourceLoader.CACHE_MODE_REPLACE)
			body.add_child(cs)
			mi.add_child(body)
	return root

func build_water() -> MeshInstance3D:
	var water := MeshInstance3D.new()
	water.name = 'Water'
	var plane := PlaneMesh.new()
	plane.size = Vector2(2400, 2400)
	water.mesh = plane
	water.position = Vector3(0, float(layout.water), 300)
	var m := ShaderMaterial.new()
	m.shader = load('res://shaders/water.gdshader')
	m.set_shader_parameter('normal_tex', load('res://assets/textures/water_normal.png'))
	water.material_override = m
	water.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	water.layers = 1
	water.set_script(load('res://client/world/water_reflection.gd'))
	return water

func build_distant(rng: RandomNumberGenerator) -> Node3D:
	## Jagged ridges ringing the map beyond the playable land, plus a smoking volcano far to
	## the north-east. Rendered with the distant-haze shader.
	var root := Node3D.new()
	root.name = 'DistantLand'
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var noise := FastNoiseLite.new()
	noise.seed = 4242
	noise.frequency = 0.012
	noise.fractal_octaves = 4
	var rings := [[340.0, 0.0], [480.0, 0.8], [640.0, 1.6]]
	var seg := 160
	var profile: Array = []
	for r in rings.size():
		var row := PackedVector3Array()
		for k in seg + 1:
			var a := TAU * k / seg
			var rad: float = rings[r][0] + noise.get_noise_2d(k * 3.0, r * 50.0) * 40.0
			var dir := Vector2(cos(a), sin(a))
			# keep the southern sea open: no mountains in the southern quarter
			var south := clampf((dir.y - 0.2) / 0.5, 0.0, 1.0)
			var hgt: float = (45.0 + rings[r][1] * 40.0) * (0.5 + 0.7 * absf(noise.get_noise_2d(k * 7.0, r * 13.0 + 7.0)))
			hgt *= 1.0 - south
			if r == 0:
				hgt *= 0.6
			row.append(Vector3(dir.x * rad, hgt - 8.0, dir.y * rad))
		profile.append(row)
	var inner := PackedVector3Array()
	for k in seg + 1:
		var a := TAU * k / seg
		inner.append(Vector3(cos(a) * 250.0, -10.0, sin(a) * 250.0))
	profile.push_front(inner)
	for r in profile.size() - 1:
		for k in seg:
			var p00: Vector3 = profile[r][k]
			var p01: Vector3 = profile[r][k + 1]
			var p10: Vector3 = profile[r + 1][k]
			var p11: Vector3 = profile[r + 1][k + 1]
			for v in [p00, p10, p11, p00, p11, p01]:
				st.set_color(Color(0.9, 0.88, 0.85))
				st.add_vertex(v)
	# volcano
	var vc := Vector3(520, 0, -760)
	var vseg := 40
	var vprof := [[300.0, -10.0], [220.0, 90.0], [120.0, 230.0], [45.0, 330.0], [30.0, 318.0]]
	for r in vprof.size() - 1:
		for k in vseg:
			var a0 := TAU * k / vseg
			var a1 := TAU * (k + 1) / vseg
			var j0 := 1.0 + noise.get_noise_2d(k * 9.0, r * 5.0) * 0.18
			var j1 := 1.0 + noise.get_noise_2d((k + 1) % vseg * 9.0, r * 5.0) * 0.18
			var r0: float = vprof[r][0]
			var r1: float = vprof[r + 1][0]
			var y0: float = vprof[r][1]
			var y1: float = vprof[r + 1][1]
			var q00 := vc + Vector3(cos(a0) * r0 * j0, y0, sin(a0) * r0 * j0)
			var q01 := vc + Vector3(cos(a1) * r0 * j1, y0, sin(a1) * r0 * j1)
			var q10 := vc + Vector3(cos(a0) * r1 * j0, y1, sin(a0) * r1 * j0)
			var q11 := vc + Vector3(cos(a1) * r1 * j1, y1, sin(a1) * r1 * j1)
			for v in [q00, q11, q10, q00, q01, q11]:
				st.set_color(Color(0.62, 0.52, 0.46))
				st.add_vertex(v)
	st.generate_normals()
	var mesh := st.commit()
	ResourceSaver.save(mesh, OUT + 'distant_land.res')
	var mi := MeshInstance3D.new()
	mi.name = 'Mountains'
	mi.mesh = ResourceLoader.load(OUT + 'distant_land.res', '', ResourceLoader.CACHE_MODE_REPLACE)
	var m := ShaderMaterial.new()
	m.shader = load('res://shaders/distant.gdshader')
	m.set_shader_parameter('albedo_tex', load('res://assets/textures/t_rock.png'))
	m.set_shader_parameter('uv_scale', 0.02)
	m.set_shader_parameter('max_haze', 0.82)
	m.set_shader_parameter('tint', Color(0.7, 0.66, 0.62))
	ResourceSaver.save(m, OUT + 'distant_material.tres')
	mi.material_override = ResourceLoader.load(OUT + 'distant_material.tres', '', ResourceLoader.CACHE_MODE_REPLACE)
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(mi)
	return root
