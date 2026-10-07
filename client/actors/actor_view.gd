class_name ActorView
extends Node3D
## Client-side view of another player or an NPC: the body (placeholder tint and scale per race), its
## animation, a nameplate, a quest marker, a selection ring and a click target. Driven by realm snapshots.

const CLICK_LAYER := 32       ## physics layer of the click targets (rays only, never collides)
const BODY_SCALE := 0.94      ## same scale as the player's own body
const NAME_COLORS := {'enemy': Color('#e0533f'), 'npc': Color('#e8cf6c'), 'player': Color('#8fc6ff'), 'party': Color('#7be07b')}

var eid := ''
var session: Node
var info: Dictionary = {}
var state: Dictionary = {}
var body: Node3D
var anim: AnimationPlayer
var plate: Label3D
var marker: Label3D
var ring: MeshInstance3D
var dead := false
var casting := ''
var casting_name := ''
var _goal := Vector3.ZERO
var _goal_yaw := 0.0
var _action_left := 0.0
var _clip := ''
var _placed := false

func setup(id: String, actor_info: Dictionary, owner_session: Node = null) -> void:
	eid = id
	session = owner_session
	name = id
	info = actor_info
	body = Catalog.body_scene(str(info.sex), str(info.race)).instantiate()
	add_child(body)
	body.rotation.y = PI
	body.scale = Vector3.ONE * BODY_SCALE * Catalog.race_stretch(str(info.race))
	Catalog.apply_appearance(body, str(info.race), int(info.skin))
	anim = body.find_child('AnimationPlayer', true, false) as AnimationPlayer
	var height := 1.85 * body.scale.y
	plate = Label3D.new()
	plate.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	plate.fixed_size = false
	plate.pixel_size = 0.0042
	plate.font_size = 40
	plate.outline_size = 10
	plate.outline_modulate = Color(0, 0, 0, 0.85)
	plate.no_depth_test = false
	plate.position.y = height + 0.32
	add_child(plate)
	marker = Label3D.new()
	marker.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	marker.pixel_size = 0.008
	marker.font_size = 64
	marker.outline_size = 14
	marker.modulate = Color('#ffd23a')
	marker.position.y = height + 0.85
	add_child(marker)
	ring = MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = 0.58
	torus.outer_radius = 0.66
	torus.rings = 32
	torus.ring_segments = 6
	ring.mesh = torus
	ring.scale = Vector3(1, 0.08, 1)
	ring.position.y = 0.04
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color.WHITE
	ring.material_override = mat
	ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	ring.visible = false
	add_child(ring)
	var click := Area3D.new()
	click.collision_layer = CLICK_LAYER
	click.collision_mask = 0
	click.monitoring = false
	click.monitorable = false
	click.set_meta('actor_id', eid)
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.5
	capsule.height = height
	shape.shape = capsule
	shape.position.y = height * 0.5
	click.add_child(shape)
	add_child(click)
	refresh_plate()

func category() -> String:
	if info.get('kind') == 'player':
		return 'player'
	return 'enemy' if info.get('hostile', false) else 'npc'

func refresh_plate() -> void:
	var text := str(info.name)
	if info.get('subtitle', '') != '':
		text += '\n<%s>' % info.subtitle
	plate.text = text
	var look := 'party' if session and session.in_party(eid) else category()
	plate.modulate = NAME_COLORS[look]
	(ring.material_override as StandardMaterial3D).albedo_color = NAME_COLORS[category()]

func set_marker(mark: String) -> void:
	marker.text = mark
	marker.modulate = Color('#ffd23a') if mark != '·' else Color('#b0a890')

func set_selected(value: bool) -> void:
	ring.visible = value

func apply(s: Dictionary) -> void:
	state = s
	_goal = s.p
	_goal_yaw = float(s.y)
	if not _placed:
		_placed = true
		global_position = _goal
		rotation.y = _goal_yaw
	var now_dead := bool(s.dead)
	if now_dead != dead:
		dead = now_dead
		_clip = ''
		if dead:
			_action_left = 0.0
	casting = str(s.get('cast', ''))

func play_action(clip: String) -> void:
	if dead or not anim or not anim.has_animation(clip):
		return
	anim.play(clip, 0.08)
	anim.speed_scale = 1.0
	_clip = clip
	_action_left = anim.get_animation(clip).length - 0.12

func _process(delta: float) -> void:
	if not _placed:
		return
	global_position = global_position.lerp(_goal, 1.0 - exp(-delta * 12.0))
	rotation.y = lerp_angle(rotation.y, _goal_yaw, 1.0 - exp(-delta * 12.0))
	if not anim:
		return
	if dead:
		if _clip != 'death':
			_clip = 'death'
			anim.play('death', 0.1)
			anim.speed_scale = 1.0
		return
	if _action_left > 0.0:
		_action_left -= delta
		return
	var clip := str(state.get('c', 'idle'))
	var rate := float(state.get('r', 1.0))
	if casting != '':
		clip = 'spell_idle'
		rate = 1.0
	if not anim.has_animation(clip):
		clip = 'idle'
	if clip != _clip:
		anim.play(clip, 0.18)
		_clip = clip
	anim.speed_scale = maxf(rate, 0.15) if clip in ['walk', 'run'] else 1.0
