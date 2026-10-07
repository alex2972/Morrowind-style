extends Node
## The RPC transport shared by the realm and every client. Both sides own a node named `Link` running this
## script under their own MultiplayerAPI branch (SceneTree.set_multiplayer), so the RPC paths match.
## Calls are forwarded to the parent: the realm gateway gets `on_*(sender, ...)`, a client gets `on_*(...)`.
## Message names and shapes live in shared/protocol.gd.

func _sender() -> int:
	return multiplayer.get_remote_sender_id()

@rpc('any_peer', 'call_remote', 'reliable')
func c_hello(version: int, username: String, password: String, creating: bool) -> void:
	get_parent().on_hello(_sender(), version, username, password, creating)

@rpc('any_peer', 'call_remote', 'reliable')
func c_msg(type: String, data: Dictionary) -> void:
	get_parent().on_msg(_sender(), type, data)

@rpc('any_peer', 'call_remote', 'unreliable_ordered', 1)
func c_move(pos: Vector3, yaw: float, clip: String, rate: float) -> void:
	get_parent().on_move(_sender(), pos, yaw, clip, rate)

@rpc('authority', 'call_remote', 'reliable')
func s_msg(type: String, data: Dictionary) -> void:
	get_parent().on_msg(type, data)

@rpc('authority', 'call_remote', 'unreliable_ordered', 1)
func s_state(packed: PackedByteArray, size: int) -> void:
	if size <= 0 or size > 1 << 20:
		return
	var value: Variant = bytes_to_var(packed.decompress(size, FileAccess.COMPRESSION_ZSTD))
	if value is Array and value.size() == 2:
		get_parent().on_state(value[0], value[1])
