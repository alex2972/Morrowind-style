extends MeshInstance3D
## Planar reflection for the water plane: a mirrored camera renders the scene (minus small
## props, flora and the viewmodel) into a half-resolution viewport sampled by water.gdshader.

@export var resolution_scale := 0.5
@export_flags_3d_render var reflect_mask := 1
const CLIP_FLAG := 1 << 19  # tells the terrain shader to discard below the water plane

var _vp: SubViewport
var _cam: Camera3D
var _mat: ShaderMaterial

func _ready() -> void:
	_mat = material_override as ShaderMaterial
	_vp = SubViewport.new()
	_vp.name = 'ReflectionViewport'
	_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_vp.msaa_3d = Viewport.MSAA_DISABLED
	_vp.positional_shadow_atlas_size = 0
	add_child(_vp)
	_cam = Camera3D.new()
	_cam.cull_mask = reflect_mask | CLIP_FLAG
	_vp.add_child(_cam)
	_cam.current = true
	_mat.set_shader_parameter('reflection_tex', _vp.get_texture())
	_mat.set_shader_parameter('has_reflection', 1.0)

func _process(_delta: float) -> void:
	var main := get_viewport().get_camera_3d()
	if main == null:
		return
	var size := Vector2i(get_viewport().get_visible_rect().size * resolution_scale)
	if _vp.size != size:
		_vp.size = size
	var h := global_position.y
	var t := main.global_transform
	var below := t.origin.y < h + 0.05
	var interior: float = get_parent().get_node('Weather').interior if get_parent().has_node('Weather') else 0.0
	var active := not below and interior < 0.95
	_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS if active else SubViewport.UPDATE_DISABLED
	_mat.set_shader_parameter('has_reflection', 1.0 if active else 0.0)
	if not active:
		return
	var r := t.basis.x
	var u := t.basis.y
	var b := t.basis.z
	var rm := Vector3(r.x, -r.y, r.z)
	var um := Vector3(u.x, -u.y, u.z)
	var bm := Vector3(b.x, -b.y, b.z)
	var o := t.origin
	o.y = 2.0 * h - o.y
	_cam.global_transform = Transform3D(Basis(-rm, um, bm), o)
	_cam.fov = main.fov
	_cam.near = main.near
	_cam.far = main.far
