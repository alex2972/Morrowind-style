class_name CombatFx
extends Node3D
## Small spell effects: a glowing bolt that flies from caster to target and bursts on arrival, a burst on
## the target (heals, instant spells) or an expanding ring (Thunder Clap).

const COLORS := {'fire': Color(1.0, 0.45, 0.08), 'frost': Color(0.5, 0.85, 1.0), 'holy': Color(1.0, 0.86, 0.45),
	'shadow': Color(0.62, 0.3, 1.0), 'healing': Color(0.45, 1.0, 0.45), 'thunder': Color(1.0, 0.9, 0.6),
	'level': Color(1.0, 0.85, 0.35)}

var mode := 'bolt'
var color := Color.WHITE
var from: Node3D
var to: Node3D
var _t := 0.0
var _duration := 0.35
var _mesh: MeshInstance3D
var _mat: StandardMaterial3D
var _light: OmniLight3D

static func spawn(parent: Node, kind: String, from_node: Node3D, to_node: Node3D) -> void:
	if not COLORS.has(kind) or from_node == null:
		return
	var fx := CombatFx.new()
	fx.color = COLORS[kind]
	fx.from = from_node
	fx.to = to_node if to_node else from_node
	match kind:
		'thunder':
			fx.mode = 'ring'
		'healing', 'level':
			fx.mode = 'burst'
		_:
			fx.mode = 'bolt' if to_node and to_node != from_node else 'burst'
	parent.add_child(fx)

func _ready() -> void:
	_mat = StandardMaterial3D.new()
	_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	_mat.albedo_color = color
	_mesh = MeshInstance3D.new()
	_mesh.material_override = _mat
	_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_mesh)
	_light = OmniLight3D.new()
	_light.light_color = color
	_light.light_energy = 2.5
	_light.omni_range = 5.0
	add_child(_light)
	match mode:
		'bolt':
			var s := SphereMesh.new()
			s.radius = 0.16
			s.height = 0.32
			_mesh.mesh = s
			_duration = clampf(_from_point().distance_to(_to_point()) / 28.0, 0.12, 0.9)
		'burst':
			var s := SphereMesh.new()
			s.radius = 0.5
			s.height = 1.0
			_mesh.mesh = s
			_duration = 0.6
		'ring':
			var t := TorusMesh.new()
			t.inner_radius = 0.9
			t.outer_radius = 1.0
			_mesh.mesh = t
			_mesh.scale = Vector3(1, 0.15, 1)
			_duration = 0.5
	global_position = _from_point() if mode == 'bolt' else _to_point()

func _from_point() -> Vector3:
	return from.global_position + Vector3.UP * 1.35 if is_instance_valid(from) else global_position

func _to_point() -> Vector3:
	return to.global_position + Vector3.UP * 1.1 if is_instance_valid(to) else global_position

func _process(delta: float) -> void:
	_t += delta
	var k := clampf(_t / _duration, 0.0, 1.0)
	match mode:
		'bolt':
			global_position = _from_point().lerp(_to_point(), k)
			if k >= 1.0:
				mode = 'burst'
				_t = 0.0
				_duration = 0.35
				var s := SphereMesh.new()
				s.radius = 0.5
				s.height = 1.0
				_mesh.mesh = s
				return
		'burst':
			global_position = _to_point()
			_mesh.scale = Vector3.ONE * lerpf(0.4, 1.6, k)
			_mat.albedo_color.a = 1.0 - k
			_light.light_energy = 2.5 * (1.0 - k)
		'ring':
			global_position = (to.global_position if is_instance_valid(to) else global_position) + Vector3.UP * 0.3
			var r := lerpf(0.5, 8.0, k)
			_mesh.scale = Vector3(r, 0.15 * r, r)
			_mat.albedo_color.a = 1.0 - k
			_light.light_energy = 3.0 * (1.0 - k)
	if k >= 1.0:
		queue_free()
