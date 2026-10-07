extends CanvasLayer
## Morrowind's sun glare: a bright bloom over the screen when looking toward an unobstructed sun.

var rect: ColorRect
var mat: ShaderMaterial
var weather: Node
var _vis := 0.0
var _occluded := false
var _probe_time := 0.0

func _ready() -> void:
	layer = 5
	weather = get_parent().get_node('Weather')
	rect = ColorRect.new()
	rect.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	mat = ShaderMaterial.new()
	mat.shader = load('res://shaders/glare.gdshader')
	rect.material = mat
	add_child(rect)

func _process(delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	var sun_dir: Vector3 = weather.sun_direction(weather.hour)
	var glare: float = float(weather.blended.get('glare', 0.0)) * smoothstep(0.0, 0.08, sun_dir.y) * (1.0 - weather.interior)
	var fwd := -cam.global_basis.z
	var facing := fwd.dot(sun_dir)
	var target := 0.0
	var far_point := cam.global_position + sun_dir * 2000.0
	if glare > 0.01 and facing > 0.35 and not cam.is_position_behind(far_point):
		_probe_time -= delta
		if _probe_time <= 0.0:
			_probe_time = 0.08
			var q := PhysicsRayQueryParameters3D.create(cam.global_position, cam.global_position + sun_dir * 600.0)
			q.exclude = [get_parent().get_node('Player').get_rid()]
			_occluded = not cam.get_world_3d().direct_space_state.intersect_ray(q).is_empty()
		if not _occluded:
			target = glare * pow(clampf((facing - 0.35) / 0.65, 0.0, 1.0), 2.2)
		var size := get_viewport().get_visible_rect().size
		mat.set_shader_parameter('sun_screen', cam.unproject_position(far_point) / size)
		mat.set_shader_parameter('aspect', size.x / size.y)
		var sun_col: Color = weather.blended.get('sun', Color.WHITE)
		mat.set_shader_parameter('glare_color', sun_col.lerp(Color(1, 0.97, 0.9), 0.6))
	_vis = move_toward(_vis, target, delta * (4.0 if target < _vis else 2.0))
	mat.set_shader_parameter('intensity', _vis * 0.75)
	rect.visible = _vis > 0.003
