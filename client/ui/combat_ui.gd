extends Control
## The game-session HUD layer added on top of hud.gd while in the world: action bar (1-0) with cooldown
## sweeps, experience bar, cast bar, target frame, quest tracker, NPC dialogue, death overlay, floating
## combat text and error messages. It only displays what the session received from the realm.

const SLOT := 50.0
const GAP := 6.0
const KEY_LABELS := ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
const RAGE := Color('#b3261c')
const MANA := Color('#2169bf')
const HEALTH := Color('#248823')
const XP := Color('#7c3fb5')

var session: Node
var hud: CanvasLayer
var bar: Control
var bar_buttons: Array[Button] = []
var target_frame: Control
var cast_bar: Control
var tracker: RichTextLabel
var error_label: Label
var banner: Label
var dialogue_panel: PanelContainer
var dialogue_title: Label
var dialogue_sub: Label
var dialogue_text: RichTextLabel
var dialogue_options: VBoxContainer
var death_panel: PanelContainer
var party_frame: Control
var invite_panel: PanelContainer
var invite_label: Label
var _error_t := 0.0
var _banner_t := 0.0
var _flash: Dictionary = {}
var _floats: Array = []
var _tracker_hash := 0

func setup(game: Node) -> void:
	session = game
	hud = session.hud()
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	bar = _canvas(Vector2(10 * SLOT + 9 * GAP + 24, SLOT + 46))
	bar.draw.connect(_draw_bar)
	for i in 10:
		var b := Button.new()
		b.flat = true
		b.focus_mode = Control.FOCUS_NONE
		b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		for style in ['normal', 'hover', 'pressed', 'hover_pressed', 'focus']:
			b.add_theme_stylebox_override(style, StyleBoxEmpty.new())
		b.position = _slot_pos(i)
		b.size = Vector2(SLOT, SLOT)
		b.pressed.connect(session.use_slot.bind(i))
		bar.add_child(b)
		bar_buttons.append(b)
	target_frame = _canvas(Vector2(300, 92))
	target_frame.draw.connect(_draw_target)
	cast_bar = _canvas(Vector2(300, 34))
	cast_bar.draw.connect(_draw_cast)
	tracker = RichTextLabel.new()
	tracker.bbcode_enabled = true
	tracker.fit_content = true
	tracker.scroll_active = false
	tracker.mouse_filter = Control.MOUSE_FILTER_IGNORE
	tracker.add_theme_font_override('normal_font', hud.chat_font)
	tracker.add_theme_font_override('bold_font', hud.font)
	tracker.add_theme_font_size_override('normal_font_size', 14)
	tracker.add_theme_font_size_override('bold_font_size', 16)
	tracker.add_theme_constant_override('outline_size', 4)
	tracker.add_theme_color_override('font_outline_color', Color(0, 0, 0, 0.9))
	tracker.add_theme_color_override('default_color', Color('#e4dcc9'))
	tracker.size = Vector2(250, 10)
	add_child(tracker)
	error_label = hud._label('', 20, Color('#ff5a43'))
	error_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	error_label.size = Vector2(700, 30)
	add_child(error_label)
	banner = hud._label('', 44, Color('#ffd86a'))
	banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	banner.size = Vector2(700, 60)
	add_child(banner)
	_build_dialogue()
	_build_death()
	_build_party()
	refresh_bar()

func _canvas(dimensions: Vector2) -> Control:
	var c := Control.new()
	c.size = dimensions
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(c)
	return c

func _slot_pos(i: int) -> Vector2:
	return Vector2(12 + i * (SLOT + GAP), 34)

# ---------------------------------------------------------------- action bar

func _slot_icon(spec: String) -> Texture2D:
	if spec == 'attack':
		return Catalog.icon('atlas:0')
	if spec.begins_with('item:'):
		return Catalog.icon(str(Catalog.item(spec.trim_prefix('item:')).icon))
	var a: Dictionary = session.ability(spec)
	return Catalog.icon(str(a.icon)) if not a.is_empty() else null

func refresh_bar() -> void:
	for i in bar_buttons.size():
		var spec: String = session.hotbar[i] if i < session.hotbar.size() else ''
		var tip := ''
		if spec == 'attack':
			tip = 'Attack\nStart or stop attacking your target with your weapon.'
		elif spec.begins_with('item:'):
			var it: Dictionary = Catalog.item(spec.trim_prefix('item:'))
			tip = '%s\n%s' % [it.name, it.description]
		elif spec != '':
			var a: Dictionary = session.ability(spec)
			if not a.is_empty():
				tip = '%s\n%s' % [a.name, a.text]
				if not a.known:
					tip += '\nLearned at level %d.' % int(a.level)
		bar_buttons[i].tooltip_text = tip

func flash_slot(i: int) -> void:
	_flash[i] = 0.2

func _slot_ready(spec: String) -> Dictionary:
	## {cd: seconds left, total: sweep length, usable: bool}
	var me: Dictionary = session.me
	if spec == 'attack':
		return {'cd': 0.0, 'total': 1.0, 'usable': true}
	if spec.begins_with('item:'):
		var have: int = session.item_count(spec.trim_prefix('item:'))
		return {'cd': float(me.get('potion', 0.0)), 'total': float(Catalog.rules.potion_cooldown), 'usable': have > 0}
	var a: Dictionary = session.ability(spec)
	if a.is_empty():
		return {'cd': 0.0, 'total': 1.0, 'usable': false}
	var cd := float(me.get('cds', {}).get(spec, 0.0))
	var total := float(a.cooldown)
	var gcd := float(me.get('gcd', 0.0))
	if gcd > cd:
		cd = gcd
		total = float(Catalog.rules.gcd)
	var usable: bool = a.known and float(me.get('res', 0.0)) >= float(a.cost)
	var view: ActorView = session.target_view()
	if usable and a.target == 'enemy' and view and view.global_position.distance_to(session.player().global_position) > float(a.range) + 0.6:
		usable = false
	return {'cd': cd, 'total': maxf(total, 0.01), 'usable': usable}

func _draw_bar() -> void:
	var c := bar
	c.draw_style_box(hud._panel_style(0.92), Rect2(0, 26, c.size.x, SLOT + 18))
	# experience bar along the top edge
	var xp := float(session.sheet.get('xp', 0))
	var need := float(session.sheet.get('xp_next', 1))
	var xr := Rect2(4, 6, c.size.x - 8, 14)
	c.draw_rect(xr.grow(2), Color('#120f0a'))
	if need > 0:
		c.draw_rect(Rect2(xr.position, Vector2(xr.size.x * clampf(xp / need, 0, 1), xr.size.y)), XP)
		for k in range(1, 20):
			c.draw_line(xr.position + Vector2(xr.size.x * k / 20.0, 0), xr.position + Vector2(xr.size.x * k / 20.0, xr.size.y), Color(0, 0, 0, 0.45))
	var level := int(session.sheet.get('level', 1))
	var text := 'Level %d   ·   %d / %d experience' % [level, xp, need] if need > 0 else 'Level %d (maximum)' % level
	c.draw_string_outline(hud.chat_font, Vector2(4, 18), text, HORIZONTAL_ALIGNMENT_CENTER, xr.size.x, 12, 3, Color.BLACK)
	c.draw_string(hud.chat_font, Vector2(4, 18), text, HORIZONTAL_ALIGNMENT_CENTER, xr.size.x, 12, Color('#efe6ff'))
	for i in 10:
		var r := Rect2(_slot_pos(i), Vector2(SLOT, SLOT))
		c.draw_rect(r.grow(2), Color('#0b0a07'))
		c.draw_rect(r.grow(1), hud.FRAME, false, 1.0)
		var spec: String = session.hotbar[i] if i < session.hotbar.size() else ''
		var tex := _slot_icon(spec)
		if tex:
			var st := _slot_ready(spec)
			var tint := Color.WHITE if st.usable else Color(0.42, 0.38, 0.38)
			if spec.begins_with('item:') and not st.usable:
				tint = Color(0.3, 0.3, 0.3)
			c.draw_texture_rect(tex, r, false, tint)
			if st.cd > 0.05:
				_sweep(c, r, st.cd / st.total)
				if st.cd > 1.5:
					c.draw_string_outline(hud.font, r.position + Vector2(0, 33), str(ceili(st.cd)), HORIZONTAL_ALIGNMENT_CENTER, SLOT, 20, 4, Color.BLACK)
					c.draw_string(hud.font, r.position + Vector2(0, 33), str(ceili(st.cd)), HORIZONTAL_ALIGNMENT_CENTER, SLOT, 20, Color('#fff2cf'))
			if spec == 'attack' and session.me.get('auto', false):
				var pulse := 0.6 + 0.4 * sin(Time.get_ticks_msec() * 0.008)
				c.draw_rect(r.grow(-1), Color(1, 0.85, 0.3, pulse), false, 3.0)
			if spec.begins_with('item:'):
				var count := str(int(session.sheet.get('inventory', {}).get(spec.trim_prefix('item:'), 0)))
				c.draw_string_outline(hud.chat_font, r.position + Vector2(0, SLOT - 4), count, HORIZONTAL_ALIGNMENT_RIGHT, SLOT - 4, 14, 3, Color.BLACK)
				c.draw_string(hud.chat_font, r.position + Vector2(0, SLOT - 4), count, HORIZONTAL_ALIGNMENT_RIGHT, SLOT - 4, 14, Color.WHITE)
			if _flash.get(i, 0.0) > 0.0:
				c.draw_rect(r, Color(1, 1, 0.8, _flash[i] * 2.0))
		c.draw_string_outline(hud.chat_font, r.position + Vector2(4, 14), KEY_LABELS[i], HORIZONTAL_ALIGNMENT_LEFT, -1, 13, 3, Color.BLACK)
		c.draw_string(hud.chat_font, r.position + Vector2(4, 14), KEY_LABELS[i], HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color('#e9dfc2'))

func _sweep(c: Control, r: Rect2, fraction: float) -> void:
	## Dark clock-wipe over the part of the cooldown still remaining.
	var center := r.get_center()
	var pts := PackedVector2Array([center])
	var steps := 24
	for k in steps + 1:
		var a := -PI * 0.5 + TAU * (1.0 - fraction) + TAU * fraction * k / steps
		var d := Vector2(cos(a), sin(a))
		var t := minf(absf(r.size.x * 0.5 / d.x) if absf(d.x) > 1e-4 else 1e9, absf(r.size.y * 0.5 / d.y) if absf(d.y) > 1e-4 else 1e9)
		pts.append(center + d * t)
	c.draw_colored_polygon(pts, Color(0, 0, 0, 0.62))

# ---------------------------------------------------------------- target frame and cast bar

func _draw_target() -> void:
	var view: ActorView = session.target_view()
	if view == null:
		return
	var c := target_frame
	var s: Dictionary = view.state
	c.draw_style_box(hud._panel_style(), Rect2(0, 0, c.size.x, c.size.y))
	var color: Color = ActorView.NAME_COLORS[view.category()]
	var title := str(view.info.name)
	c.draw_string_outline(hud.font, Vector2(14, 26), title, HORIZONTAL_ALIGNMENT_LEFT, 220, 19, 3, Color('#11130f'))
	c.draw_string(hud.font, Vector2(14, 26), title, HORIZONTAL_ALIGNMENT_LEFT, 220, 19, color)
	var lv := str(int(s.get('lv', 1)))
	var lv_color := _level_color(int(s.get('lv', 1)))
	c.draw_string_outline(hud.font, Vector2(c.size.x - 64, 26), lv, HORIZONTAL_ALIGNMENT_RIGHT, 50, 19, 3, Color('#11130f'))
	c.draw_string(hud.font, Vector2(c.size.x - 64, 26), lv, HORIZONTAL_ALIGNMENT_RIGHT, 50, 19, lv_color)
	if view.dead:
		hud._text(c, Vector2(14, 58), 'Dead', c.size.x - 28, 18, Color('#9b9384'))
		return
	hud._bar(c, Vector2(14, 36), Vector2(c.size.x - 28, 18), HEALTH, float(s.get('hp', 0)), float(s.get('mhp', 1)))
	if s.has('mres'):
		hud._bar(c, Vector2(14, 62), Vector2(c.size.x - 28, 14), RAGE if s.get('kind') == 'rage' else MANA, float(s.res), float(s.mres))
	elif view.casting != '':
		hud._text(c, Vector2(14, 80), 'Casting ' + view.casting_name, c.size.x - 28, 14, Color('#ffd86a'))
	elif view.info.get('subtitle', '') != '':
		hud._text(c, Vector2(14, 80), str(view.info.subtitle), c.size.x - 28, 14, hud.GOLD_DIM)

func _level_color(level: int) -> Color:
	var diff := level - int(session.sheet.get('level', 1))
	if diff >= 3:
		return Color('#ff3b30')
	if diff >= 1:
		return Color('#ff9a2e')
	if diff >= -2:
		return Color('#ffe14a')
	if diff >= -4:
		return Color('#4fd44a')
	return Color('#9b9b9b')

func _draw_cast() -> void:
	var cast: Dictionary = session.me.get('cast', {})
	if cast.is_empty():
		return
	var c := cast_bar
	var total := float(cast.total)
	var left := maxf(float(cast.left) - _since_snapshot(), 0.0)
	var r := Rect2(4, 6, c.size.x - 8, 22)
	c.draw_style_box(hud._panel_style(1.0), r.grow(3))
	c.draw_rect(Rect2(r.position, Vector2(r.size.x * clampf(1.0 - left / total, 0, 1), r.size.y)), Color('#d6a730'))
	var spell := str(session.ability(str(cast.ability)).get('name', ''))
	hud._text(c, r.position + Vector2(0, 17), '%s   %.1f' % [spell, left], r.size.x, 15, Color('#fff7df'))

var _snapshot_clock := 0.0
var _last_me: Dictionary = {}

func _since_snapshot() -> float:
	return _snapshot_clock

# ---------------------------------------------------------------- tracker, errors, banner, floating text

func _tracker_text() -> String:
	var lines := PackedStringArray()
	for q in session.sheet.get('quests', []):
		lines.append('[b][color=#ffd86a]%s[/color][/b]' % q.title)
		if q.ready:
			lines.append('  [color=#8fe07a]Ready to turn in[/color]')
			continue
		for o in q.objectives:
			lines.append('  %s: %d/%d' % [o.label, int(o.have), int(o.need)] if int(o.need) > 1 else '  ' + str(o.label))
	return '\n'.join(lines)

func show_error(text: String) -> void:
	error_label.text = text
	_error_t = 2.0

func show_banner(text: String) -> void:
	banner.text = text
	_banner_t = 3.0

func float_text(node: Node3D, text: String, color: Color, big := false) -> void:
	if node == null:
		return
	var l: Label = hud._label(text, 26 if big else 20, color)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.size = Vector2(160, 30)
	l.add_theme_constant_override('outline_size', 5)
	l.add_theme_color_override('font_outline_color', Color(0, 0, 0, 0.9))
	add_child(l)
	_floats.append({'label': l, 'node': node, 't': 0.0, 'dx': randf_range(-30, 30)})

# ---------------------------------------------------------------- dialogue and death

func _build_dialogue() -> void:
	dialogue_panel = PanelContainer.new()
	var st: StyleBoxFlat = hud._panel_style(0.95)
	st.set_border_width_all(3)
	st.content_margin_left = 22
	st.content_margin_right = 22
	st.content_margin_top = 16
	st.content_margin_bottom = 16
	dialogue_panel.add_theme_stylebox_override('panel', st)
	dialogue_panel.custom_minimum_size = Vector2(520, 0)
	add_child(dialogue_panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override('separation', 8)
	dialogue_panel.add_child(box)
	var head := HBoxContainer.new()
	box.add_child(head)
	var names := VBoxContainer.new()
	names.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(names)
	dialogue_title = hud._label('', 24)
	names.add_child(dialogue_title)
	dialogue_sub = hud._label('', 14, hud.GOLD_DIM)
	names.add_child(dialogue_sub)
	var close := Button.new()
	close.text = '×'
	close.custom_minimum_size = Vector2(32, 32)
	hud._style_button(close)
	close.pressed.connect(func() -> void: session.choose('bye'); session.close_dialogue())
	head.add_child(close)
	box.add_child(HSeparator.new())
	dialogue_text = RichTextLabel.new()
	dialogue_text.bbcode_enabled = true
	dialogue_text.fit_content = true
	dialogue_text.custom_minimum_size = Vector2(476, 0)
	dialogue_text.add_theme_font_override('normal_font', hud.chat_font)
	dialogue_text.add_theme_font_size_override('normal_font_size', 17)
	dialogue_text.add_theme_font_size_override('italics_font_size', 15)
	dialogue_text.add_theme_color_override('default_color', Color('#e4dcc9'))
	box.add_child(dialogue_text)
	box.add_child(HSeparator.new())
	dialogue_options = VBoxContainer.new()
	dialogue_options.add_theme_constant_override('separation', 4)
	box.add_child(dialogue_options)
	dialogue_panel.hide()

func show_dialogue(d: Dictionary) -> void:
	for child in dialogue_options.get_children():
		child.queue_free()
	if d.is_empty():
		if dialogue_panel.visible:
			dialogue_panel.hide()
			hud.set_interface_open(false)
		return
	dialogue_title.text = str(d.name)
	dialogue_sub.text = str(d.get('subtitle', ''))
	dialogue_text.text = str(d.text)
	for o in d.options:
		var b := Button.new()
		var mark := str(o.get('mark', ''))
		b.text = ('%s  %s' % [mark, o.label]) if mark != '' else str(o.label)
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		hud._style_button(b)
		if mark == '!' or mark == '?':
			b.add_theme_color_override('font_color', Color('#ffd86a'))
		if o.has('icon'):
			b.icon = Catalog.icon(str(o.icon))
			b.expand_icon = true
			b.custom_minimum_size.y = 36
		b.pressed.connect(session.choose.bind(str(o.id)))
		dialogue_options.add_child(b)
	dialogue_panel.reset_size()
	dialogue_panel.show()
	hud.set_interface_open(true)

# ---------------------------------------------------------------- party

const PARTY_ROW := 46.0

func _build_party() -> void:
	party_frame = _canvas(Vector2(250, 5 * PARTY_ROW))
	party_frame.draw.connect(_draw_party)
	party_frame.mouse_filter = Control.MOUSE_FILTER_STOP
	party_frame.gui_input.connect(func(e: InputEvent) -> void:
		if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
			var members: Array = session.me.get('party', [])
			var row := int(e.position.y / PARTY_ROW)
			if row < members.size():
				session.set_target(str(members[row][0])))
	invite_panel = PanelContainer.new()
	invite_panel.add_theme_stylebox_override('panel', hud._panel_style(0.95))
	add_child(invite_panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override('separation', 8)
	invite_panel.add_child(box)
	invite_label = hud._label('', 18)
	box.add_child(invite_label)
	var row := HBoxContainer.new()
	box.add_child(row)
	for pair in [['Accept', true], ['Decline', false]]:
		var b := Button.new()
		b.text = pair[0]
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		hud._style_button(b)
		b.pressed.connect(func() -> void:
			session.respond_invite(pair[1])
			invite_panel.hide())
		row.add_child(b)
	invite_panel.hide()

func show_invite(from: String) -> void:
	invite_label.text = '%s invites you to join a party.' % from
	invite_panel.reset_size()
	invite_panel.show()
	hud.set_interface_open(true)

func _draw_party() -> void:
	var c := party_frame
	var members: Array = session.me.get('party', [])
	for i in members.size():
		var m: Array = members[i]
		var y := i * PARTY_ROW
		c.draw_style_box(hud._panel_style(0.85), Rect2(0, y, c.size.x, PARTY_ROW - 6))
		var color := Color('#7be07b') if str(m[0]) != session.target else Color('#ffe396')
		c.draw_string_outline(hud.chat_font, Vector2(10, y + 15), '%s  %d' % [m[1], int(m[2])], HORIZONTAL_ALIGNMENT_LEFT, 220, 14, 3, Color.BLACK)
		c.draw_string(hud.chat_font, Vector2(10, y + 15), '%s  %d' % [m[1], int(m[2])], HORIZONTAL_ALIGNMENT_LEFT, 220, 14, color)
		if bool(m[8]):
			c.draw_string(hud.chat_font, Vector2(10, y + 33), 'Dead', HORIZONTAL_ALIGNMENT_LEFT, 220, 13, Color('#9b9384'))
			continue
		var hp_frac := clampf(float(m[3]) / maxf(float(m[4]), 1.0), 0, 1)
		var res_frac := clampf(float(m[5]) / maxf(float(m[6]), 1.0), 0, 1)
		c.draw_rect(Rect2(10, y + 20, c.size.x - 20, 9), Color('#120f0a'))
		c.draw_rect(Rect2(10, y + 20, (c.size.x - 20) * hp_frac, 9), HEALTH)
		c.draw_rect(Rect2(10, y + 31, c.size.x - 20, 5), Color('#120f0a'))
		c.draw_rect(Rect2(10, y + 31, (c.size.x - 20) * res_frac, 5), RAGE if m[7] == 'rage' else MANA)

func _build_death() -> void:
	death_panel = PanelContainer.new()
	death_panel.add_theme_stylebox_override('panel', hud._panel_style(0.95))
	add_child(death_panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override('separation', 10)
	death_panel.add_child(box)
	var l: Label = hud._label('You have died.', 26, Color('#e0533f'))
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(l)
	var b := Button.new()
	b.text = 'Release spirit'
	hud._style_button(b)
	b.pressed.connect(session.release_spirit)
	box.add_child(b)
	death_panel.hide()

# ---------------------------------------------------------------- frame

func _process(delta: float) -> void:
	var area: Vector2 = get_parent().size
	size = area
	if session.me != _last_me:
		_last_me = session.me
		_snapshot_clock = 0.0
	_snapshot_clock += delta
	bar.position = Vector2((area.x - bar.size.x) * 0.5, area.y - bar.size.y - 8)
	cast_bar.position = Vector2((area.x - cast_bar.size.x) * 0.5, bar.position.y - 74)
	target_frame.position = Vector2(372, 26)
	tracker.position = Vector2(area.x - 266, 290)
	error_label.position = Vector2((area.x - 700) * 0.5, 112)
	banner.position = Vector2((area.x - 700) * 0.5, area.y * 0.28)
	dialogue_panel.position = Vector2(area.x - dialogue_panel.size.x - 24, maxf(290.0, (area.y - dialogue_panel.size.y) * 0.5))
	death_panel.position = (area - death_panel.size) * Vector2(0.5, 0.4)
	party_frame.position = Vector2(26, 136)
	party_frame.size.y = PARTY_ROW * session.me.get('party', []).size()
	party_frame.queue_redraw()
	invite_panel.position = Vector2((area.x - invite_panel.size.x) * 0.5, area.y * 0.22)
	death_panel.visible = bool(session.me.get('dead', false))
	if death_panel.visible and not hud.interface_open:
		hud.set_interface_open(true)
	for i in _flash.keys():
		_flash[i] -= delta
		if _flash[i] <= 0.0:
			_flash.erase(i)
	bar.queue_redraw()
	target_frame.queue_redraw()
	cast_bar.queue_redraw()
	var text := _tracker_text()
	if text.hash() != _tracker_hash:
		_tracker_hash = text.hash()
		tracker.text = text
	_error_t -= delta
	error_label.modulate.a = clampf(_error_t, 0.0, 1.0)
	_banner_t -= delta
	banner.modulate.a = clampf(_banner_t, 0.0, 1.0)
	var cam: Camera3D = session.player().camera
	var scale_inv := 1.0 / maxf(hud._ui_scale, 0.01)
	for f in _floats.duplicate():
		f.t += delta
		var l: Label = f.label
		if f.t > 1.3 or not is_instance_valid(f.node):
			l.queue_free()
			_floats.erase(f)
			continue
		var world_pos: Vector3 = f.node.global_position + Vector3.UP * (2.1 + f.t * 0.9)
		if cam.is_position_behind(world_pos):
			l.hide()
			continue
		l.show()
		l.position = cam.unproject_position(world_pos) * scale_inv - Vector2(80 - f.dx, 15)
		l.modulate.a = clampf((1.3 - f.t) * 2.5, 0.0, 1.0)
