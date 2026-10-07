class_name Zone
extends Node
## One simulated area (Veyr today; later the tutorial island, dungeons, party instances). It owns:
##   * its own physics world: the baked collision (server/world/<zone>/collision.scn) inside a SubViewport
##     with its own World3D, so server ray casts never touch - or depend on - the client's scene;
##   * the entities in it, bucketed in a 32 m grid for interest management;
##   * region names for saves, rosters and messages.

const CELL := 32.0

var id := ''
var info: Dictionary = {}
var entities: Dictionary = {}    ## eid -> entity
var players: Dictionary = {}     ## eid -> player entity
var _grid: Dictionary = {}       ## Vector2i -> {eid: true}
var _world: SubViewport

func setup(zone_id: String) -> bool:
	id = zone_id
	name = 'Zone_' + zone_id
	var dir := 'res://server/world/%s/' % zone_id
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(dir + 'zone.json'))
	if not parsed is Dictionary or not ResourceLoader.exists(dir + 'collision.scn'):
		push_error('Zone %s is not baked. Run tools/bake_server_world.gd.' % zone_id)
		return false
	info = parsed
	_world = SubViewport.new()
	_world.own_world_3d = true
	_world.size = Vector2i(2, 2)
	_world.render_target_update_mode = SubViewport.UPDATE_DISABLED
	add_child(_world)
	_world.add_child(load(dir + 'collision.scn').instantiate())
	return true

func spawn_point() -> Vector3:
	var s: Array = info.spawn
	return Vector3(s[0], s[1], s[2])

func spawn_yaw() -> float:
	return float(info.get('spawn_yaw', 0.0))

# ---------------------------------------------------------------- entities and interest

static func cell_of(pos: Vector3) -> Vector2i:
	return Vector2i(floori(pos.x / CELL), floori(pos.z / CELL))

func add(e: Dictionary) -> void:
	e.zone = id
	entities[e.eid] = e
	if e.kind == 'player':
		players[e.eid] = e
	e.cell = cell_of(e.pos)
	_grid.get_or_add(e.cell, {})[e.eid] = true

func remove(e: Dictionary) -> void:
	entities.erase(e.eid)
	players.erase(e.eid)
	if _grid.has(e.cell):
		_grid[e.cell].erase(e.eid)

func moved(e: Dictionary) -> void:
	## Call after changing e.pos; keeps the grid bucket current.
	var c := cell_of(e.pos)
	if c != e.cell:
		if _grid.has(e.cell):
			_grid[e.cell].erase(e.eid)
		e.cell = c
		_grid.get_or_add(c, {})[e.eid] = true

func nearby(pos: Vector3, radius: float, only_players := false) -> Array:
	var out: Array = []
	var r := ceili(radius / CELL)
	var c := cell_of(pos)
	var r2 := radius * radius
	for x in range(c.x - r, c.x + r + 1):
		for z in range(c.y - r, c.y + r + 1):
			for eid in _grid.get(Vector2i(x, z), {}):
				var e: Dictionary = entities[eid]
				if (not only_players or e.kind == 'player') and e.pos.distance_squared_to(pos) <= r2:
					out.append(e)
	return out

# ---------------------------------------------------------------- physics queries

func _space() -> PhysicsDirectSpaceState3D:
	return _world.find_world_3d().direct_space_state

func ground(x: float, z: float, from_y := 150.0) -> float:
	var hit := _space().intersect_ray(PhysicsRayQueryParameters3D.create(Vector3(x, from_y, z), Vector3(x, -60.0, z), 1))
	return hit.position.y if not hit.is_empty() else 0.0

func sight(a: Vector3, b: Vector3) -> bool:
	var hit := _space().intersect_ray(PhysicsRayQueryParameters3D.create(a + Vector3.UP * 1.5, b + Vector3.UP * 1.4, 1))
	return hit.is_empty()

# ---------------------------------------------------------------- regions

func region_at(p: Vector3) -> String:
	var tunnel: Array = info.get('tunnel', [])
	for i in range(tunnel.size() - 1):
		var a := Vector2(tunnel[i][0], tunnel[i][2])
		var b := Vector2(tunnel[i + 1][0], tunnel[i + 1][2])
		var ab := b - a
		var t := clampf((Vector2(p.x, p.z) - a).dot(ab) / ab.length_squared(), 0.0, 1.0)
		var floor_y := lerpf(tunnel[i][1], tunnel[i + 1][1], t)
		if Vector2(p.x, p.z).distance_to(a + ab * t) < 9.0 and p.y > floor_y - 2.0 and p.y < floor_y + 9.0 and (i > 0 or t > 0.2):
			return str(info.get('tunnel_region', ''))
	for r in info.get('regions', []):
		var rect: Array = r.rect
		if p.x >= rect[0] and p.x <= rect[1] and p.z >= rect[2] and p.z <= rect[3]:
			return str(r.name)
	return str(info.get('default_region', info.get('name', id)))
