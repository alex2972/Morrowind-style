extends Node3D
## Load doors (shared/doors.gd): builds the interiors, puts a clickable volume on every door, shows the
## Skyrim-style "E  Enter" prompt while the player looks at one up close, and moves them through it on E
## (through the realm when online, directly in a standalone world scene).

const LAYER_INTERIOR := 2
const LAYER_DOORS := 1 << 9    ## physics layer of the door volumes (only these rays look for it)
const FADE_OUT := 0.16         ## seconds to black before the move
const FADE_HOLD := 0.18

var focused := ''              ## door id under the crosshair, or ''
var _mats := {}
var _busy := 0.0

func world() -> Node:
	return get_parent()

func _ready() -> void:
	name = 'Doors'
	for id in Doors.DOORS:
		_add_volume(id, Doors.DOORS[id])
	_build_tavern()

# ---------------------------------------------------------------- prompt and use

func _process(delta: float) -> void:
	_busy = maxf(0.0, _busy - delta)
	var id := _look()
	if id != focused:
		focused = id
		var hud: CanvasLayer = world().hud
		if id == '':
			hud.set_prompt('', '')
		else:
			hud.set_prompt(Doors.DOORS[id].action, Doors.DOORS[id].label)

func _look() -> String:
	var p: CharacterBody3D = world().player
	if p.frozen or p.paused or p.dead or p.ui_active or _busy > 0.0:
		return ''
	var cam: Camera3D = p.camera
	var from := cam.global_position
	var dir := -cam.global_basis.z
	# third person: start the ray at the head so the door must be near the character, not the camera
	var eyes: Vector3 = p.head.global_position
	var q := PhysicsRayQueryParameters3D.create(from, from + dir * (Doors.RANGE + from.distance_to(eyes)), 1 | LAYER_DOORS)
	q.collide_with_areas = true
	q.exclude = [p.get_rid()]
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty() or not hit.collider.has_meta('door') or eyes.distance_to(hit.position) > Doors.RANGE:
		return ''
	return hit.collider.get_meta('door')

func _unhandled_input(event: InputEvent) -> void:
	# online the session handles E (it calls use_focused); this covers the bare world scene
	if world().hud.session == null and event is InputEventKey and event.pressed and not event.echo \
			and event.physical_keycode == KEY_E and use_focused():
		get_viewport().set_input_as_handled()

func use_focused() -> bool:
	## Go through the door under the crosshair. False when there is none (E then talks / attacks).
	if focused == '' or _busy > 0.0:
		return false
	var id := focused
	_busy = FADE_OUT + FADE_HOLD + 0.3
	focused = ''
	world().hud.set_prompt('', '')
	world().hud.fade(FADE_OUT, FADE_HOLD)
	_go_through(id)
	return true

func _go_through(id: String) -> void:
	await get_tree().create_timer(FADE_OUT).timeout
	var session: Node = world().hud.session
	if session and session.in_world:
		session.send(Protocol.C_USE_DOOR, {'door': id})
	else:
		var door: Dictionary = Doors.DOORS[id]
		var p: CharacterBody3D = world().player
		p.global_position = door.to
		p.velocity = Vector3.ZERO
		p.rotation.y = door.to_yaw

func _add_volume(id: String, door: Dictionary) -> void:
	var area := Area3D.new()
	area.name = 'Door_' + id
	area.collision_layer = LAYER_DOORS
	area.collision_mask = 0
	area.monitoring = false
	area.set_meta('door', id)
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(0.3, 2.45, 1.4)    # across x = depth, z = width (rotated to the door's facing)
	shape.shape = box
	area.add_child(shape)
	add_child(area)
	var facing: Vector3 = door.facing
	area.global_position = door.pos + facing * 0.12
	area.rotation.y = atan2(facing.z, -facing.x) + PI   # local +x out of the door

# ---------------------------------------------------------------- the tavern

func _mat(key: String) -> Material:
	## The shared material, mapped in world space (the boxes below have no authored UVs).
	if _mats.has(key):
		return _mats[key]
	var m: Material = load('res://materials/%s.tres' % key).duplicate()
	if m is BaseMaterial3D and key not in ['glow', 'dark']:
		var scale := {'plaster': 3.0, 'timber': 1.6, 'planks': 2.0, 'fieldstone': 2.6, 'door': 2.4, 'cloth': 2.0, 'bark': 1.5}
		m.uv1_triplanar = true
		m.uv1_world_triplanar = true
		m.uv1_triplanar_sharpness = 4.0
		m.uv1_scale = Vector3.ONE / float(scale.get(key, 2.0))
	_mats[key] = m
	return m

func _box(parent: Node3D, size: Vector3, pos: Vector3, mat: String, solid := true, yaw := 0.0) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	mi.mesh = mesh
	mi.material_override = _mat(mat)
	mi.layers = LAYER_INTERIOR
	mi.position = pos
	mi.rotation.y = yaw
	parent.add_child(mi)
	if solid:
		var body := StaticBody3D.new()
		body.set_meta('surface', 'wood' if mat in ['planks', 'timber'] else 'stone')
		var cs := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = size
		cs.shape = shape
		body.add_child(cs)
		mi.add_child(body)
	return mi

func _prop(parent: Node3D, key: String, pos: Vector3, yaw := 0.0, scale := 1.0) -> Node3D:
	var path := 'res://scenes/props/%s.tscn' % key
	if not ResourceLoader.exists(path):
		return null
	var n: Node3D = load(path).instantiate()
	n.position = pos
	n.rotation.y = yaw
	n.scale = Vector3.ONE * scale
	parent.add_child(n)
	for g in n.find_children('*', 'GeometryInstance3D', true, false):
		(g as GeometryInstance3D).layers = LAYER_INTERIOR   # lit by the room's lamps, never the sun
	return n

func _light(parent: Node3D, pos: Vector3, color: Color, energy: float, reach: float, shadows := false) -> OmniLight3D:
	var l := OmniLight3D.new()
	l.position = pos
	l.light_color = color
	l.light_energy = energy
	l.light_specular = 0.0
	l.omni_range = reach
	l.omni_attenuation = 1.3
	l.shadow_enabled = shadows
	l.set_meta('flicker', energy)
	parent.add_child(l)
	return l

func _flame(parent: Node3D, pos: Vector3, size: Vector2, seed: float) -> void:
	var f := MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = size
	q.center_offset = Vector3(0, size.y * 0.5, 0)
	f.mesh = q
	f.position = pos
	var m: ShaderMaterial = load('res://materials/flame.tres').duplicate()
	m.set_shader_parameter('seed', seed)
	f.material_override = m
	f.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	f.layers = LAYER_INTERIOR
	f.extra_cull_margin = 1.0
	parent.add_child(f)

func _build_tavern() -> void:
	## A half-timbered taproom: bar along the north wall, hearth in the west wall, tables, lanterns,
	## and the street door in the east wall (the house it belongs to faces east onto the main street).
	var room := Node3D.new()
	room.name = 'Tavern'
	add_child(room)
	room.global_position = Doors.TAVERN_ORIGIN
	var hx := Doors.TAVERN_HALF.x
	var hz := Doors.TAVERN_HALF.z
	var h := Doors.TAVERN_HALF.y
	# shell
	_box(room, Vector3(hx * 2 + 0.6, 0.3, hz * 2 + 0.6), Vector3(0, -0.15, 0), 'planks')
	_box(room, Vector3(hx * 2 + 0.6, 0.3, hz * 2 + 0.6), Vector3(0, h + 0.15, 0), 'planks')
	_box(room, Vector3(hx * 2 + 0.6, h, 0.3), Vector3(0, h * 0.5, -hz - 0.15), 'plaster')
	_box(room, Vector3(hx * 2 + 0.6, h, 0.3), Vector3(0, h * 0.5, hz + 0.15), 'plaster')
	_box(room, Vector3(0.3, h, hz * 2), Vector3(-hx - 0.15, h * 0.5, 0), 'plaster')
	_box(room, Vector3(0.3, h, hz * 2), Vector3(hx + 0.15, h * 0.5, 0), 'plaster')
	# timber framing: sill, wall posts, mid rail, ceiling beams
	for z in [-hz + 0.06, hz - 0.06]:
		_box(room, Vector3(hx * 2, 0.22, 0.12), Vector3(0, 0.11, z), 'timber', false)
		_box(room, Vector3(hx * 2, 0.16, 0.12), Vector3(0, 1.1, z), 'timber', false)
		for x in [-hx + 0.12, -3.0, 0.0, 3.0, hx - 0.12]:
			_box(room, Vector3(0.24, h, 0.14), Vector3(x, h * 0.5, z), 'timber', false)
	for x in [-hx + 0.06, hx - 0.06]:
		_box(room, Vector3(0.12, 0.22, hz * 2), Vector3(x, 0.11, 0), 'timber', false)
		_box(room, Vector3(0.14, h, 0.24), Vector3(x, h * 0.5, -hz + 0.12), 'timber', false)
		_box(room, Vector3(0.14, h, 0.24), Vector3(x, h * 0.5, hz - 0.12), 'timber', false)
	for x in [-4.5, -1.5, 1.5, 4.5]:
		_box(room, Vector3(0.28, 0.32, hz * 2), Vector3(x, h - 0.16, 0), 'timber', false)
	_box(room, Vector3(hx * 2, 0.26, 0.3), Vector3(0, h - 0.45, 0), 'timber', false)
	for x in [-1.5, 1.5]:   # two posts hold the long beam
		_box(room, Vector3(0.28, h, 0.28), Vector3(x, h * 0.5, 0.0), 'timber')
	# the street door (inside face of the same door)
	_box(room, Vector3(0.1, 2.3, 1.2), Vector3(hx - 0.05, 1.15, 0), 'door', false)
	_box(room, Vector3(0.18, 2.55, 0.16), Vector3(hx - 0.08, 1.27, -0.68), 'timber', false)
	_box(room, Vector3(0.18, 2.55, 0.16), Vector3(hx - 0.08, 1.27, 0.68), 'timber', false)
	_box(room, Vector3(0.18, 0.18, 1.52), Vector3(hx - 0.08, 2.46, 0), 'timber', false)
	_box(room, Vector3(0.06, 0.06, 0.06), Vector3(hx - 0.13, 1.1, 0.42), 'iron', false)
	# hearth in the west wall
	var fx := -hx + 0.5
	_box(room, Vector3(1.0, 1.25, 0.6), Vector3(fx, 0.625, -1.0), 'fieldstone')
	_box(room, Vector3(1.0, 1.25, 0.6), Vector3(fx, 0.625, 1.0), 'fieldstone')
	_box(room, Vector3(1.0, h - 1.25, 2.6), Vector3(fx, 1.25 + (h - 1.25) * 0.5, 0), 'fieldstone')
	_box(room, Vector3(0.12, 1.25, 1.4), Vector3(-hx + 0.06, 0.625, 0), 'dark', false)
	_box(room, Vector3(1.5, 0.1, 3.0), Vector3(fx + 0.2, 0.05, 0), 'fieldstone')
	_box(room, Vector3(1.2, 0.12, 2.9), Vector3(fx + 0.02, 1.31, 0), 'timber', false)   # mantel
	for i in 3:
		var piece := _box(room, Vector3(0.6, 0.13, 0.13), Vector3(fx - 0.05, 0.17 + (0.1 if i == 2 else 0.0), -0.2 + i * 0.2), 'bark', false, 0.5 - i * 0.5)
		piece.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_box(room, Vector3(0.5, 0.06, 0.6), Vector3(fx - 0.05, 0.12, 0), 'glow', false)
	_flame(room, Vector3(fx, 0.18, -0.15), Vector2(0.5, 0.7), 0.2)
	_flame(room, Vector3(fx - 0.05, 0.18, 0.18), Vector2(0.45, 0.6), 0.7)
	_light(room, Vector3(fx + 0.6, 0.7, 0), Color(1.0, 0.55, 0.24), 2.6, 9.0, true)
	# bar along the north wall
	_box(room, Vector3(5.0, 1.02, 0.6), Vector3(0.5, 0.51, -hz + 1.65), 'timber')
	_box(room, Vector3(5.3, 0.08, 0.8), Vector3(0.5, 1.06, -hz + 1.62), 'planks', false)
	_box(room, Vector3(0.6, 1.02, 1.3), Vector3(3.3, 0.51, -hz + 1.0), 'timber')
	for y in [1.45, 2.1]:
		_box(room, Vector3(4.6, 0.06, 0.36), Vector3(0.0, y, -hz + 0.2), 'planks', false)
	for i in 7:
		_prop(room, 'urn', Vector3(-2.0 + i * 0.62, 1.48, -hz + 0.2), i * 0.9, 0.32)
		if i % 2 == 0:
			_prop(room, 'urn_tall', Vector3(-1.7 + i * 0.6, 2.13, -hz + 0.2), i * 0.7, 0.28)
	for x in [-1.6, -0.2, 1.2, 2.6]:   # stools
		_box(room, Vector3(0.36, 0.06, 0.36), Vector3(x, 0.62, -hz + 2.3), 'planks', false)
		_box(room, Vector3(0.1, 0.6, 0.1), Vector3(x, 0.3, -hz + 2.3), 'timber', false)
	_prop(room, 'barrel_interior', Vector3(-2.9, 0, -hz + 0.55), 0.3)
	_prop(room, 'barrel_interior', Vector3(-3.7, 0, -hz + 0.6), 1.4)
	_prop(room, 'barrel_interior', Vector3(-3.3, 0, -hz + 1.3), 2.2)
	# tables and benches
	for t in [[Vector3(-2.4, 0, 2.3), 0.0], [Vector3(1.6, 0, 2.6), 0.0], [Vector3(0.0, 0, 0.1), 0.0], [Vector3(4.3, 0, 3.0), PI * 0.5]]:
		var at: Vector3 = t[0]
		var yaw: float = t[1]
		_prop(room, 'table_interior', at, yaw)
		var side := Vector3(0, 0, 0.78).rotated(Vector3.UP, yaw)
		_prop(room, 'bench', at + side, yaw)
		_prop(room, 'bench', at - side, yaw)
	# rug, hanging lanterns, stores in the corner
	_box(room, Vector3(3.0, 0.02, 1.9), Vector3(-3.3, 0.01, -0.0), 'cloth', false).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_prop(room, 'lantern_hanging_interior', Vector3(-1.5, 2.9, hz), PI)
	_prop(room, 'lantern_hanging_interior', Vector3(3.0, 2.9, hz), PI)
	_prop(room, 'lantern_hanging_interior', Vector3(-1.0, 2.9, -hz), 0.0)
	_prop(room, 'lantern_hanging_interior', Vector3(2.0, 2.9, -hz), 0.0)
	_prop(room, 'crate_interior', Vector3(hx - 0.6, 0, -hz + 1.4), 0.2)
	_prop(room, 'crate_small_interior', Vector3(hx - 0.5, 0, -hz + 0.5), -0.3)
	_prop(room, 'sack_interior', Vector3(hx - 1.4, 0, -hz + 0.5), 0.8)
	_prop(room, 'sack_interior', Vector3(-hx + 0.6, 0, hz - 0.6), 2.0)
