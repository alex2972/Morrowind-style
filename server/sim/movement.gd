extends RealmSystem
## Player movement. Clients move themselves (WoW-style responsiveness) and report their position 15 times a
## second; the realm accepts it only if it is physically plausible and snaps the client back otherwise.
## Also owns teleports, doors (shared/doors.gd) and /unstuck.

const MAX_SPEED := 11.0    ## m/s horizontally (run is 5; leaves room for latency bursts)

func setup() -> void:
	realm.handle(Protocol.C_UNSTUCK, _on_unstuck)
	realm.handle(Protocol.C_USE_DOOR, _on_use_door)

func player_joined(p: Dictionary, _data: Dictionary) -> void:
	p.clip = 'idle'
	p.rate = 1.0
	p.move_t = realm.now

func write_save(p: Dictionary, state: Dictionary) -> void:
	state.pos = p.pos
	state.yaw = p.yaw

func on_move(p: Dictionary, pos: Vector3, yaw: float, clip: String, rate: float) -> void:
	if p.dead or not pos.is_finite() or not is_finite(yaw):
		return
	var dt := maxf(realm.now - p.move_t, 0.05)
	var planar := Vector2(pos.x - p.pos.x, pos.z - p.pos.z).length()
	if planar > MAX_SPEED * dt + 1.5 or absf(pos.y - p.pos.y) > 60.0:
		teleport(p, p.pos, p.yaw)   # too fast: back to where the realm says they are
		return
	if not p.cast.is_empty() and planar > 0.12:
		realm.combat.cancel_cast(p, 'Interrupted')
	p.pos = pos
	p.yaw = yaw
	p.clip = clip.left(24)
	p.rate = clampf(rate, 0.0, 3.0)
	p.move_t = realm.now
	realm.zone_of(p).moved(p)

func teleport(p: Dictionary, pos: Vector3, yaw: float) -> void:
	p.pos = pos
	p.yaw = yaw
	p.move_t = realm.now
	realm.zone_of(p).moved(p)
	realm.send(p, Protocol.S_TELEPORT, {'pos': pos, 'yaw': yaw})

func _on_unstuck(p: Dictionary, _data: Dictionary) -> void:
	if p.dead or realm.now - p.combat < Rules.COMBAT_TIMEOUT:
		realm.error(p, 'You cannot do that while in combat.')
		return
	var zone := realm.zone_of(p)
	teleport(p, zone.spawn_point(), zone.spawn_yaw())

func _on_use_door(p: Dictionary, data: Dictionary) -> void:
	var door: Dictionary = Doors.DOORS.get(str(data.get('door', '')), {})
	if p.dead or door.is_empty():
		return
	var at: Vector3 = door.pos
	if Vector2(p.pos.x - at.x, p.pos.z - at.z).length() > Doors.REALM_RANGE or absf(p.pos.y - at.y) > 4.0:
		return
	if not p.cast.is_empty():
		realm.combat.cancel_cast(p, 'Interrupted')
	teleport(p, door.to, door.to_yaw)
