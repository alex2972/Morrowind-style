extends RealmSystem
## Chat and slash commands. Plain text goes to everyone in the realm; commands are parsed here, so new
## commands never need a client update.

const INTERVAL := 0.4
const HELP := '/p <text> party chat  ·  /invite [name] (or your target)  ·  /accept  ·  /decline  ·  /leave  ·  /who'

func setup() -> void:
	realm.handle(Protocol.C_CHAT, _on_chat)

func player_joined(p: Dictionary, _data: Dictionary) -> void:
	p.chat_t = -10.0

func system_message(text: String) -> void:
	realm.broadcast({'type': 'chat', 'channel': 'Game', 'text': text})

func _on_chat(p: Dictionary, d: Dictionary) -> void:
	var text := str(d.get('text', '')).strip_edges().left(240)
	if text.is_empty() or realm.now - p.chat_t < INTERVAL:
		return
	p.chat_t = realm.now
	if not text.begins_with('/'):
		realm.broadcast({'type': 'chat', 'channel': 'Players', 'text': text, 'from': p.name})
		return
	var command := text.get_slice(' ', 0).to_lower()
	var rest := text.substr(command.length()).strip_edges()
	match command:
		'/p', '/party':
			realm.party.say(p, rest)
		'/invite', '/inv':
			realm.party.invite(p, rest)
		'/accept':
			realm.party.respond(p, true)
		'/decline':
			realm.party.respond(p, false)
		'/leave':
			realm.party.leave(p)
		'/who':
			var names: Array = realm.players.values().map(func(o: Dictionary) -> String: return '%s (%d)' % [o.name, o.level])
			realm.tell(p, '%d online: %s' % [names.size(), ', '.join(names)])
		'/reload':
			if not p.is_admin:
				realm.error(p, 'Only realm admins can reload content.')
				return
			var problems: Array = realm.reload_content()
			if problems.is_empty():
				system_message('Content reloaded (version %s).' % realm.content.version)
			else:
				realm.tell(p, 'Reload refused - fix these rows first:\n' + '\n'.join(problems))
		'/help':
			realm.tell(p, HELP)
		_:
			realm.tell(p, 'Unknown command. ' + HELP)
