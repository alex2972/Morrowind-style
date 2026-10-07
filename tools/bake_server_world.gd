extends SceneTree
## Bakes the server's copy of a zone: only the collision shapes of the world (terrain chunks and every prop
## on physics layer 1), plus the zone's regions, spawn point and mine path. The realm loads this instead of
## the art, so a dedicated server never touches meshes, textures or shaders.
##   Godot --headless --path . --script res://tools/bake_server_world.gd
## Re-run after rebuilding the world (tools/rebuild.ps1 does it).

const WORLD := 'res://scenes/world/veyr.tscn'
const OUT := 'res://server/world/veyr/'

func _init() -> void:
	call_deferred('run')

func run() -> void:
	var world: Node3D = load(WORLD).instantiate()
	root.add_child(world)
	await process_frame
	var baked := Node3D.new()
	baked.name = 'VeyrCollision'
	var count := 0
	for node in world.find_children('*', 'CollisionShape3D', true, false):
		var shape_node := node as CollisionShape3D
		var body := shape_node.get_parent() as CollisionObject3D
		if body == null or not body is StaticBody3D or (body.collision_layer & 1) == 0 or shape_node.shape == null \
				or shape_node.disabled or world.get_node('Player').is_ancestor_of(body):
			continue
		var copy := StaticBody3D.new()
		copy.name = 'B%d' % count
		copy.collision_layer = 1
		copy.collision_mask = 0
		copy.global_transform = shape_node.global_transform
		var cs := CollisionShape3D.new()
		cs.name = 'Shape'
		cs.shape = shape_node.shape
		copy.add_child(cs)
		baked.add_child(copy)
		copy.owner = baked
		cs.owner = baked
		count += 1
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT))
	var packed := PackedScene.new()
	packed.pack(baked)
	var err := ResourceSaver.save(packed, OUT + 'collision.scn', ResourceSaver.FLAG_COMPRESS)
	var tunnel: Array = []
	for p in world.tunnel_path:
		tunnel.append([snappedf(p.x, 0.01), snappedf(p.y, 0.01), snappedf(p.z, 0.01)])
	var info := {'name': 'Veyr', 'regions': world.regions, 'tunnel': tunnel, 'default_region': 'The Veyr Coast',
		'tunnel_region': 'The Hollow Mine', 'spawn': [-11.6, 2.6, 100.5], 'spawn_yaw': 0.0, 'half': world.map_half}
	var f := FileAccess.open(OUT + 'zone.json', FileAccess.WRITE)
	f.store_string(JSON.stringify(info, ' '))
	f.close()
	print('Baked %d collision shapes -> %scollision.scn (err %d)' % [count, OUT, err])
	baked.free()
	quit(0 if err == OK else 1)
