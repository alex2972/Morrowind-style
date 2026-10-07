extends SceneTree
## Integration check: exported race scene, shared skeleton/clips, fallback and hair tint.
var failures := 0
func check(ok: bool, label: String) -> void:
	print(('PASS ' if ok else 'FAIL ') + label)
	if not ok: failures += 1
func _init() -> void:
	call_deferred('run')
func run() -> void:
	Catalog.races['high_elf'] = {'scale': 1.06, 'skins': ['fff8dc', 'f7ecc4', 'ecdcac', 'dcc794']}
	var human: Node3D = Catalog.body_scene('male').instantiate()
	var elf: Node3D = Catalog.body_scene('male', 'high_elf').instantiate()
	root.add_child(human)
	root.add_child(elf)
	check(elf.get_meta('race_preset', '') == 'high_elf/male', 'male High Elf selects sculpted model')
	check(Catalog.body_scene('female', 'high_elf') == Catalog.body_scene('female'), 'female falls back to existing model')
	check(Catalog.body_scene('male', 'dark_elf') == Catalog.body_scene('male'), 'other races retain their models')
	var hs := human.find_children('*', 'Skeleton3D', true, false)[0] as Skeleton3D
	var es := elf.find_children('*', 'Skeleton3D', true, false)[0] as Skeleton3D
	check(es.get_bone_count() == 53, '53 bones')
	for i in hs.get_bone_count():
		check(hs.get_bone_name(i) == es.get_bone_name(i) and hs.get_bone_parent(i) == es.get_bone_parent(i) and hs.get_bone_rest(i).is_equal_approx(es.get_bone_rest(i)), 'same bone rest: ' + hs.get_bone_name(i))
	var ha := human.find_child('AnimationPlayer', true, false) as AnimationPlayer
	var ea := elf.find_child('AnimationPlayer', true, false) as AnimationPlayer
	var hc := ha.get_animation_list()
	var ec := ea.get_animation_list()
	check(hc == ec, 'same 73 named clips plus RESET')
	for clip in ec:
		check(is_equal_approx(ha.get_animation(clip).length, ea.get_animation(clip).length), 'same clip duration: ' + clip)
		ea.play(clip)
		ha.play(clip)
		for phase in [0.0, 0.5, 0.95]:
			ea.seek(ea.get_animation(clip).length * phase, true)
			ha.seek(ha.get_animation(clip).length * phase, true)
			for i in es.get_bone_count():
				if not es.get_bone_global_pose(i).is_equal_approx(hs.get_bone_global_pose(i)):
					check(false, 'pose differs from shared animation: ' + clip)
				if not es.get_bone_global_pose(i).is_finite():
					check(false, 'non-finite pose: ' + clip)
	var hair: MeshInstance3D
	for mesh in elf.find_children('*', 'MeshInstance3D', true, false):
		check(mesh.layers == 16, 'player render layer: ' + mesh.name)
		if 'Hair' in mesh.name: hair = mesh
	check(hair != null, 'separate swappable hair mesh')
	if hair:
		var before := (hair.get_active_material(0) as StandardMaterial3D).albedo_color
		Catalog.apply_appearance(elf, 'high_elf', 3)
		check((hair.get_active_material(0) as StandardMaterial3D).albedo_color == before, 'skin tone does not tint hair')
	check(is_equal_approx(Catalog.race_scale('high_elf'), 1.06), 'existing height scale applied by callers')
	human.free()
	elf.free()
	print('RACE VALIDATION FAILURES: ', failures)
	quit(1 if failures else 0)
