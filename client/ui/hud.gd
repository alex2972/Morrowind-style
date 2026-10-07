extends CanvasLayer
## Four-corner retro MMO HUD. Chat is local until a multiplayer transport is connected.
signal chat_submitted(text: String)

const Frame = preload('res://client/ui/retro_frame.gd')
const GOLD := Color('#dfc780')
const GOLD_DIM := Color('#a49470')
const FRAME := Color('#877044')
const FRAME_DARK := Color('#211b12')
const PANEL := Color(0.035, 0.039, 0.034, 0.89)
const CHANNELS := ['All', 'Game', 'Players', 'Combat']
const CHAT_COLORS := {'Game': Color('#d9b85e'), 'Players': Color('#e2dfcf'), 'Combat': Color('#dc957f')}

var font := SystemFont.new()
var chat_font := SystemFont.new()
var player: CharacterBody3D
var world: Node3D
var weather: Node
var root: Control
var status: Control
var map_box: Control
var crosshair: Control
var region_label: Label
var zone_label: Label
var menu: PanelContainer
var menu_shade: ColorRect
var time_label: Label
var time_slider: HSlider
var weather_select: OptionButton
var flow_check: CheckBox
var map_texture: Texture2D
var map_half := 256.0
var _region_time := 0.0
var _updating_menu := false
var chat_box: Control
var chat_log: RichTextLabel
var chat_input: LineEdit
var chat_tabs: Array[Button] = []
var chat_history: Array[Dictionary] = []
var active_channel := 'All'
var interface_open := false
var dock: Control
var dock_hint: Label
var dock_settings: ScrollContainer
var dock_hour: HSlider
var dock_weather: OptionButton
var dock_flow: CheckBox
var dock_model: OptionButton
var dock_sensitivity: HSlider
var dock_time: Label
var dock_buttons: Array[Button] = []
var info_panel: Control
var info_title: Label
var info_text: RichTextLabel
var active_panel := ''
var portrait_view: SubViewport
var portrait_model: Node3D
var portrait_body := ''
var _ui_scale := 1.0
var session: Node = null   ## the online session (scripts/net/session.gd) while in the world
var menu_logout: Button

func _ready() -> void:
	layer = 10
	world = get_parent()
	player = world.get_node('Player')
	weather = world.get_node('Weather')
	font.font_names = PackedStringArray(['Palatino Linotype', 'Book Antiqua', 'Georgia', 'serif'])
	chat_font.font_names = PackedStringArray(['Trebuchet MS', 'Verdana', 'sans-serif'])
	root = Control.new()
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	status = _canvas(root, Vector2(344, 112))
	status.draw.connect(_draw_status)
	_build_portrait()
	map_box = _canvas(root, Vector2(236, 256))
	map_box.draw.connect(_draw_map)
	var zone_frame := _frame(map_box, Vector2.ZERO, Vector2(236, 34))
	zone_label = _label('Veyr', 17)
	zone_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	zone_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	zone_label.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	_place(zone_frame, zone_label, Vector2(10, 2), Vector2(216, 30))
	crosshair = _canvas(root, Vector2(16, 16))
	crosshair.draw.connect(_draw_crosshair)
	_build_chat()
	_build_dock()
	_build_info_panel()
	region_label = _label('', 25)
	region_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_place(root, region_label, Vector2.ZERO, Vector2(600, 40))
	menu_shade = ColorRect.new()
	menu_shade.color = Color(0, 0, 0, 0.28)
	root.add_child(menu_shade)
	menu_shade.hide()
	_build_menu()
	get_viewport().size_changed.connect(_layout)
	_layout()
	add_chat_message('Game', 'Welcome to Veyr. Your journey begins at the harbour.')
	add_chat_message('Game', 'Enter to chat  •  I to use the interface  •  Esc for the menu')
	add_chat_message('Game', 'WASD move  •  Tab target  •  1-0 abilities  •  E talk / attack  •  V change view')

func _canvas(parent: Node, dimensions: Vector2) -> Control:
	var c := Control.new()
	c.size = dimensions
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(c)
	return c

func _place(parent: Node, child: Control, pos: Vector2, dimensions: Vector2) -> void:
	parent.add_child(child)
	child.position = pos
	child.size = dimensions

func _frame(parent: Node, pos: Vector2, dimensions: Vector2) -> Control:
	var frame := Frame.new()
	_place(parent, frame, pos, dimensions)
	return frame

func _layout() -> void:
	var viewport_size := get_viewport().get_visible_rect().size
	_ui_scale = minf(1.0, minf(viewport_size.x / 1152.0, viewport_size.y / 700.0))
	root.scale = Vector2.ONE * _ui_scale
	root.size = viewport_size / _ui_scale
	menu_shade.size = root.size
	status.position = Vector2(18, 18)
	map_box.position = Vector2(root.size.x - 254, 16)
	chat_box.position = Vector2(18, root.size.y - 218)
	dock.position = root.size - dock.size * dock.scale
	info_panel.position = Vector2(0, -info_panel.size.y)
	crosshair.position = root.size * 0.5 - Vector2(8, 8)
	region_label.position = Vector2((root.size.x - 600) * 0.5, 48)
	if menu.visible:
		menu.position = (root.size - menu.size) * 0.5

func _label(text: String, size: int, color := GOLD) -> Label:
	var l := Label.new()
	l.text = text
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	l.add_theme_font_override('font', font)
	l.add_theme_font_size_override('font_size', size)
	l.add_theme_color_override('font_color', color)
	l.add_theme_color_override('font_shadow_color', Color(0, 0, 0, 0.95))
	l.add_theme_constant_override('shadow_offset_x', 1)
	l.add_theme_constant_override('shadow_offset_y', 1)
	return l

func _panel_style(alpha := 0.9) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = Color(PANEL, alpha)
	s.border_color = FRAME
	s.set_border_width_all(2)
	s.set_corner_radius_all(4)
	s.shadow_color = Color(0, 0, 0, 0.6)
	s.shadow_size = 3
	s.content_margin_left = 14
	s.content_margin_right = 14
	s.content_margin_top = 8
	s.content_margin_bottom = 8
	return s

func _style_button(b: BaseButton) -> void:
	b.add_theme_font_override('font', font)
	b.add_theme_font_size_override('font_size', 16)
	b.add_theme_color_override('font_color', Color('#d5cdb7'))
	b.add_theme_color_override('font_hover_color', GOLD)
	b.add_theme_color_override('font_pressed_color', GOLD)
	var normal := _panel_style(0.94)
	normal.set_border_width_all(1)
	normal.content_margin_top = 3
	normal.content_margin_bottom = 3
	var hover := normal.duplicate()
	hover.bg_color = Color('#302a1c')
	hover.border_color = GOLD_DIM
	var selected := hover.duplicate()
	selected.border_color = GOLD
	b.add_theme_stylebox_override('normal', normal)
	b.add_theme_stylebox_override('hover', hover)
	b.add_theme_stylebox_override('pressed', selected)
	b.add_theme_stylebox_override('hover_pressed', selected)
	var focus := normal.duplicate()
	focus.bg_color = Color.TRANSPARENT
	focus.border_color = GOLD
	b.add_theme_stylebox_override('focus', focus)
	b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND

func _build_portrait() -> void:
	portrait_view = SubViewport.new()
	portrait_view.size = Vector2i(192, 192)
	portrait_view.own_world_3d = true
	portrait_view.render_target_update_mode = SubViewport.UPDATE_DISABLED
	add_child(portrait_view)
	var cam := Camera3D.new()
	portrait_view.add_child(cam)
	cam.position = Vector3(0, 1.64, 1.1)
	cam.look_at(Vector3(0, 1.61, 0))
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = 0.60
	cam.current = true
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color('#252b24')
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color('#e6d9bd')
	env.ambient_light_energy = 0.7
	cam.environment = env
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-25, -35, 0)
	light.light_color = Color('#ffe1a8')
	light.light_energy = 1.4
	portrait_view.add_child(light)
	_refresh_portrait()

func _refresh_portrait() -> void:
	if portrait_model:
		portrait_view.remove_child(portrait_model)
		portrait_model.queue_free()
	portrait_body = _portrait_key()
	portrait_model = Catalog.body_scene(player.body_model, player.body_race).instantiate()
	portrait_view.add_child(portrait_model)
	portrait_model.transform = Transform3D.IDENTITY
	if session:
		Catalog.apply_appearance(portrait_model, str(session.identity.race), int(session.identity.skin))
	var anim := portrait_model.find_child('AnimationPlayer', true, false) as AnimationPlayer
	if anim:
		anim.play('idle')
		anim.advance(0.0)
		anim.pause()
	var portrait_camera := portrait_view.get_camera_3d()
	var eye_height := 1.50 if player.body_model == 'female' else 1.64
	portrait_camera.position.y = eye_height
	portrait_camera.look_at(Vector3(0, eye_height - 0.03, 0))
	portrait_view.render_target_update_mode = SubViewport.UPDATE_ONCE

func _portrait_key() -> String:
	if session:
		return '%s/%s/%d' % [player.body_model, session.identity.race, int(session.identity.skin)]
	return player.body_model

func _ring(c: Control, center: Vector2, radius: float) -> void:
	c.draw_circle(center + Vector2(1, 3), radius + 5, Color(0, 0, 0, 0.6))
	c.draw_circle(center, radius + 3, FRAME_DARK)
	for band in [[radius + 2, Color('#51432c'), 3.0], [radius, Color('#c0a568'), 1.5], [radius - 3, Color('#725b36'), 2.0], [radius - 5, Color('#161810'), 2.0]]:
		c.draw_arc(center, band[0], 0, TAU, 100, band[1], band[2], true)
	for i in 32:
		var a := TAU * i / 32.0
		var p := center + Vector2(cos(a), sin(a)) * (radius - 1)
		c.draw_circle(p, 0.7, GOLD_DIM)

func _round_texture(c: Control, tex: Texture2D, center: Vector2, radius: float, uv_center := Vector2(0.5, 0.5), uv_radius := Vector2(0.5, 0.5)) -> void:
	if not tex:
		return
	var points := PackedVector2Array()
	var uvs := PackedVector2Array()
	for i in 96:
		var direction := Vector2(cos(TAU * i / 96.0), sin(TAU * i / 96.0))
		points.append(center + direction * radius)
		uvs.append(uv_center + direction * uv_radius)
	c.draw_polygon(points, PackedColorArray([Color.WHITE]), uvs, tex)

func _text(c: Control, pos: Vector2, text: String, width: float, size: int, color := GOLD) -> void:
	c.draw_string_outline(font, pos, text, HORIZONTAL_ALIGNMENT_CENTER, width, size, 3, Color('#11130f'))
	c.draw_string(font, pos, text, HORIZONTAL_ALIGNMENT_CENTER, width, size, color)

func _draw_status() -> void:
	var c := status
	c.draw_style_box(_panel_style(), Rect2(87, 12, 244, 88))
	c.draw_style_box(_panel_style(0.0), Rect2(90, 15, 238, 82))
	_text(c, Vector2(113, 38), player.character_name, 204, 21)
	_bar(c, Vector2(115, 47), Vector2(200, 19), Color('#248823'), player.health, player.max_health)
	_bar(c, Vector2(115, 73), Vector2(200, 19), Color('#b3261c') if player.resource_kind == 'rage' else Color('#2169bf'), player.mana, player.max_mana)
	_ring(c, Vector2(53, 53), 50)
	_round_texture(c, portrait_view.get_texture(), Vector2(53, 53), 44)
	_ring(c, Vector2(20, 94), 17)
	c.draw_circle(Vector2(20, 94), 12, Color('#10140f'))
	_text(c, Vector2(6, 101), str(player.character_level), 28, 20)
	# Small engraved flourishes connect the portrait to the plate.
	for y in [19.0, 94.0]:
		c.draw_polyline(PackedVector2Array([Vector2(96, y + 6), Vector2(104, y), Vector2(109, y + 4), Vector2(104, y + 8)]), GOLD_DIM, 1, true)
		c.draw_polyline(PackedVector2Array([Vector2(320, y + 3), Vector2(326, y), Vector2(327, y + 9)]), GOLD_DIM, 1, true)

func _bar(c: Control, pos: Vector2, dimensions: Vector2, color: Color, current: float, maximum: float) -> void:
	var fraction := clampf(current / maxf(maximum, 1), 0, 1)
	c.draw_style_box(_panel_style(1.0), Rect2(pos - Vector2.ONE * 2, dimensions + Vector2.ONE * 4))
	if fraction > 0:
		for y in int(dimensions.y):
			var t := float(y) / dimensions.y
			var shade := color.lightened(0.28 * (1.0 - t * 2.0)) if t < 0.5 else color.darkened((t - 0.5) * 0.9)
			c.draw_rect(Rect2(pos + Vector2(0, y), Vector2(dimensions.x * fraction, 1)), shade)
		c.draw_line(pos + Vector2(1, 1), pos + Vector2(maxf(1, dimensions.x * fraction - 1), 1), color.lightened(0.55), 1)
	_text(c, pos + Vector2(0, 15), '%d / %d' % [current, maximum], dimensions.x, 15, Color('#f1ebd8'))

func set_minimap(tex: Texture2D, half: float) -> void:
	map_texture = tex
	map_half = half

func _draw_map() -> void:
	var c := map_box
	var center := Vector2(118, 151)
	_ring(c, center, 103)
	c.draw_circle(center, 97, Color('#293529'))
	var p := player.global_position
	var uv := (Vector2(p.x, p.z) + Vector2.ONE * map_half) / (2.0 * map_half)
	_round_texture(c, map_texture, center, 97, uv, Vector2.ONE * (48.0 / (2.0 * map_half)))
	# World -Z is north. The map never rotates; only the player marker turns.
	var fwd := Vector2(-sin(player.rotation.y), -cos(player.rotation.y))
	var right := Vector2(-fwd.y, fwd.x)
	var pts := PackedVector2Array([center + fwd * 9, center - fwd * 6 + right * 5, center - fwd * 3, center - fwd * 6 - right * 5])
	c.draw_circle(center, 13, Color(0, 0, 0, 0.3))
	c.draw_colored_polygon(pts, Color('#ffe396'))
	c.draw_polyline(pts + PackedVector2Array([pts[0]]), FRAME_DARK, 1.5, true)
	_text(c, Vector2(106, 58), 'N', 24, 24, Color('#fff2cf'))
	for pair in [[Vector2(210, 157), 'E'], [Vector2(106, 250), 'S'], [Vector2(3, 157), 'W']]:
		_text(c, pair[0], pair[1], 24, 13, GOLD_DIM)

func _build_chat() -> void:
	chat_box = _canvas(root, Vector2(470, 200))
	var frame := _frame(chat_box, Vector2(0, 29), Vector2(470, 171))
	frame.mouse_filter = Control.MOUSE_FILTER_STOP
	var group := ButtonGroup.new()
	for i in CHANNELS.size():
		var b := Button.new()
		b.text = CHANNELS[i]
		b.toggle_mode = true
		b.button_group = group
		b.button_pressed = i == 0
		_style_button(b)
		_place(chat_box, b, Vector2(i * 99 + 2, 0), Vector2(96, 30))
		b.pressed.connect(_select_channel.bind(CHANNELS[i]))
		chat_tabs.append(b)
	chat_log = RichTextLabel.new()
	chat_log.add_theme_font_override('normal_font', chat_font)
	chat_log.add_theme_font_size_override('normal_font_size', 16)
	chat_log.add_theme_constant_override('line_separation', 4)
	chat_log.add_theme_color_override('default_color', GOLD)
	chat_log.scroll_following = true
	chat_log.selection_enabled = true
	_place(chat_box, chat_log, Vector2(14, 41), Vector2(442, 111))
	chat_input = LineEdit.new()
	chat_input.placeholder_text = 'Press Enter to chat…'
	chat_input.tooltip_text = 'Local chat. Enter sends; Escape returns to the game.'
	chat_input.max_length = 240
	chat_input.add_theme_font_override('font', chat_font)
	chat_input.add_theme_font_size_override('font_size', 15)
	chat_input.add_theme_color_override('font_color', Color('#e4dcc9'))
	chat_input.add_theme_stylebox_override('normal', _panel_style(0.7))
	chat_input.add_theme_stylebox_override('focus', _panel_style(1.0))
	_place(chat_box, chat_input, Vector2(9, 158), Vector2(452, 33))
	chat_input.text_submitted.connect(_submit_chat)
	chat_input.focus_entered.connect(func() -> void: set_interface_open(true))

func add_chat_message(channel: String, text: String, sender := '') -> void:
	if text.is_empty():
		return
	if not CHAT_COLORS.has(channel):
		channel = 'Game'
	chat_history.append({'channel': channel, 'text': text, 'sender': sender})
	if chat_history.size() > 200:
		chat_history.pop_front()
	_refresh_chat()

func _select_channel(channel: String) -> void:
	active_channel = channel
	for i in chat_tabs.size():
		chat_tabs[i].button_pressed = CHANNELS[i] == channel
	_refresh_chat()

func _refresh_chat() -> void:
	chat_log.clear()
	for entry in chat_history:
		if active_channel != 'All' and active_channel != entry.channel:
			continue
		chat_log.push_color(CHAT_COLORS[entry.channel])
		var sender: String = entry.sender if entry.sender != '' else entry.channel
		# add_text keeps player-supplied brackets literal (no BBCode injection).
		chat_log.add_text('[%s] %s\n' % [sender, entry.text])
		chat_log.pop()

func _submit_chat(text: String) -> void:
	text = text.strip_edges()
	if not text.is_empty():
		_select_channel('Players' if active_channel in ['Game', 'Combat'] else active_channel)
		if session:
			session.send_chat(text)   # the realm echoes it back to everyone, including us
		else:
			add_chat_message('Players', text, player.character_name)
		chat_submitted.emit(text)
	chat_input.clear()
	set_interface_open(false)

func _build_dock() -> void:
	dock = _canvas(root, Vector2(292, 161))
	dock.scale = Vector2.ONE * 0.9
	var atlas := AtlasTexture.new()
	atlas.atlas = load('res://assets/ui/menu_reference.png')
	atlas.region = Rect2(91, 106, 990, 540)
	var art := TextureRect.new()
	art.texture = atlas
	art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	art.stretch_mode = TextureRect.STRETCH_SCALE
	art.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_place(dock, art, Vector2.ZERO, dock.size)
	var names := ['Spellbook', 'Journal', 'Inventory', 'Equipment', '', 'Players', 'Settings', '']
	for i in names.size():
		if names[i].is_empty():
			continue
		var b := Button.new()
		b.tooltip_text = names[i]
		b.toggle_mode = true
		b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		b.add_theme_stylebox_override('normal', StyleBoxEmpty.new())
		var hover := _panel_style(0.12)
		hover.border_color = GOLD
		hover.set_border_width_all(1)
		b.add_theme_stylebox_override('hover', hover)
		b.add_theme_stylebox_override('focus', hover)
		b.add_theme_stylebox_override('pressed', hover)
		b.add_theme_stylebox_override('hover_pressed', hover)
		_place(dock, b, Vector2(16 + (i % 4) * 66.5, 16 + floori(i / 4.0) * 66.5), Vector2(61, 61))
		b.pressed.connect(_open_panel.bind(names[i]))
		dock_buttons.append(b)
	dock_hint = _label('I  ·  INTERFACE', 11, GOLD_DIM)
	dock_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_place(dock, dock_hint, Vector2(50, -20), Vector2(238, 18))

func _build_info_panel() -> void:
	# One shared rectangle, parented to the dock so its scale and edges stay joined.
	info_panel = _frame(dock, Vector2(0, -300), Vector2(dock.size.x, 300))
	info_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	info_title = _label('', 23)
	_place(info_panel, info_title, Vector2(16, 12), Vector2(222, 32))
	var close := Button.new()
	close.text = '×'
	_style_button(close)
	_place(info_panel, close, Vector2(248, 12), Vector2(30, 30))
	close.pressed.connect(_close_panel)
	info_text = RichTextLabel.new()
	info_text.add_theme_font_override('normal_font', chat_font)
	info_text.add_theme_font_size_override('normal_font_size', 16)
	info_text.add_theme_color_override('default_color', Color('#cfc5aa'))
	info_text.bbcode_enabled = true
	info_text.meta_clicked.connect(_on_info_link)
	_place(info_panel, info_text, Vector2(16, 56), Vector2(260, 228))
	_build_dock_settings()
	info_panel.hide()

func _build_dock_settings() -> void:
	dock_settings = ScrollContainer.new()
	dock_settings.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_place(info_panel, dock_settings, Vector2(16, 56), Vector2(260, 228))
	var box := VBoxContainer.new()
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_theme_constant_override('separation', 8)
	dock_settings.add_child(box)
	dock_time = _label('Time of day', 16)
	box.add_child(dock_time)
	dock_hour = HSlider.new()
	dock_hour.max_value = 23.99
	dock_hour.step = 0.05
	dock_hour.value_changed.connect(_on_time_changed)
	box.add_child(dock_hour)
	dock_flow = CheckBox.new()
	dock_flow.text = 'Time passes'
	_style_button(dock_flow)
	dock_flow.toggled.connect(_on_flow_toggled)
	box.add_child(dock_flow)
	box.add_child(_label('Weather', 16))
	dock_weather = OptionButton.new()
	for w in weather.ORDER:
		dock_weather.add_item(w)
	_style_button(dock_weather)
	dock_weather.item_selected.connect(_on_weather_selected)
	box.add_child(dock_weather)
	box.add_child(_label('Character', 16))
	dock_model = OptionButton.new()
	for model in ['Male', 'Female']:
		dock_model.add_item(model)
	_style_button(dock_model)
	dock_model.item_selected.connect(func(i: int) -> void: player.set_body_model(['male', 'female'][i]))
	box.add_child(dock_model)
	box.add_child(_label('Mouse sensitivity', 16))
	dock_sensitivity = HSlider.new()
	dock_sensitivity.min_value = 0.0006
	dock_sensitivity.max_value = 0.005
	dock_sensitivity.step = 0.0001
	dock_sensitivity.value_changed.connect(func(v: float) -> void: player.mouse_sensitivity = v)
	box.add_child(dock_sensitivity)
	dock_settings.hide()

func _sync_dock_selection() -> void:
	dock_hint.visible = not info_panel.visible
	for button in dock_buttons:
		button.set_pressed_no_signal(info_panel.visible and button.tooltip_text == active_panel)

func _close_panel() -> void:
	info_panel.hide()
	active_panel = ''
	_sync_dock_selection()

func _open_panel(title: String) -> void:
	if active_panel == title and info_panel.visible:
		_close_panel()
		return
	set_interface_open(true)
	active_panel = title
	info_title.text = title
	info_text.visible = title != 'Settings'
	dock_settings.visible = title == 'Settings'
	if title == 'Settings':
		dock_settings.scroll_vertical = 0
		dock_sensitivity.set_value_no_signal(player.mouse_sensitivity)
	_refresh_info()
	info_panel.show()
	_sync_dock_selection()

func _refresh_info() -> void:
	if active_panel == 'Settings':
		dock_time.text = 'Time of day:  ' + weather.clock_text()
		dock_hour.set_value_no_signal(weather.hour)
		dock_flow.set_pressed_no_signal(weather.time_flows)
		dock_weather.select(weather.ORDER.find(weather.target))
		dock_model.select(1 if player.body_model == 'female' else 0)
		dock_model.disabled = session != null
		return
	if session:
		var text := _session_panel(active_panel)
		if text != info_text.text:
			info_text.text = text
		return
	var entries := {
		'Spellbook': 'MAGICKA\n%d / %d\n\nNo spells learned yet.' % [player.mana, player.max_mana],
		'Journal': 'EXPLORATION\n%s\n\nFollow the cobbled road to the temple, explore the harbour, or seek the Hollow Mine.\n\nNo active quests.' % zone_label.text,
		'Inventory': 'TRAVELLING GEAR\n\nIron sword\nHand torch\n\nF  ·  Draw or sheathe sword\nG  ·  Light or extinguish torch',
		'Equipment': 'MAIN HAND\nIron sword · %s\n\nOFF HAND\nTorch · %s\n\nARMOUR\nNone equipped' % ['drawn' if player.weapon_out else 'sheathed', 'lit' if player.torch_out else 'unlit'],
		'Players': 'LOCAL SESSION\n\n%s\n\nPlayer chat is stored for this session. Multiplayer is not connected.' % player.character_name,
	}
	info_text.text = entries.get(active_panel, '')

func _session_panel(title: String) -> String:
	## Dock panels while playing on a realm, built only from the character sheet the realm sent
	## (BBCode; [url] links are handled by _on_info_link).
	var sheet: Dictionary = session.sheet
	if sheet.is_empty():
		return ''
	var stats: Dictionary = sheet.stats
	var level := int(sheet.level)
	var out := PackedStringArray()
	match title:
		'Spellbook':
			out.append('[color=#dfc780]%s ABILITIES[/color]\n' % str(stats.class_name).to_upper())
			for a in sheet.abilities:
				out.append('[color=%s][b]%s[/b]  (level %d)[/color]' % ['#f1ebd8' if a.known else '#7d7666', a.name, int(a.level)])
				out.append('[color=%s]%s[/color]\n' % ['#cfc5aa' if a.known else '#6f6a5c', a.text])
		'Journal':
			out.append('[color=#dfc780]ACTIVE QUESTS[/color]')
			for q in sheet.quests:
				var lines := PackedStringArray()
				for o in q.objectives:
					lines.append('%s: %d/%d' % [o.label, int(o.have), int(o.need)] if int(o.need) > 1 else str(o.label))
				var progress := 'Ready to turn in' if q.ready else '\n'.join(lines)
				out.append('\n[b]%s[/b]\n%s\n[color=#9fd48a]%s[/color]  [url=abandon:%s][color=#c07a6a](abandon)[/color][/url]' % [q.title, q.text, progress, q.id])
			if sheet.quests.is_empty():
				out.append('\nNo active quests. Look for townsfolk marked with [color=#ffd23a]![/color]')
			if not sheet.quests_done.is_empty():
				out.append('\n[color=#dfc780]COMPLETED[/color]\n' + '\n'.join(sheet.quests_done))
		'Inventory':
			out.append('[color=#dfc780]PURSE[/color]  %d gold\n' % int(sheet.gold))
			var used := 0
			for i in sheet.pack.size():
				var s: Variant = sheet.pack[i]
				if s == null:
					continue
				used += 1
				var it: Dictionary = Catalog.item(str(s[0]))
				var use := ('  [url=use:%s][color=#9fd48a](use)[/color][/url]' % s[0]) if it.usable else ''
				out.append('[b]%s[/b]%s%s\n[color=#9b927c]%s[/color]\n' % [it.name, ' x%d' % int(s[1]) if int(s[1]) > 1 else '', use, it.description])
			if used == 0:
				out.append('Your pack is empty.')
			out.append('[color=#7d7666]%d / %d slots used[/color]' % [used, sheet.pack.size()])
		'Equipment':
			out.append('[color=#dfc780]%s[/color]' % str(session.identity.name).to_upper())
			out.append('Level %d %s %s %s\n' % [level, str(session.identity.sex).capitalize(), stats.race_name, stats.class_name])
			out.append('Health  %d' % int(stats.health))
			out.append('%s  %d' % [str(stats.resource_kind).capitalize(), int(stats.resource)])
			out.append('Weapon damage  %d' % int(stats.melee))
			out.append('Attack speed  %.1f s' % float(stats.swing))
			out.append('Armour  %d\n' % int(stats.armor))
			out.append('[color=#9b927c]Armour and weapon slots arrive with the item update.[/color]')
		'Players':
			if not session.party.is_empty():
				out.append('[color=#dfc780]PARTY[/color]')
				for m in session.party.members:
					out.append('%s%s, level %d' % ['* ' if m.eid == session.party.leader else '', m.name, int(m.level)])
				out.append('[color=#7d7666]/p to talk  ·  /leave to leave[/color]\n')
			out.append('[color=#dfc780]NEARBY TRAVELLERS[/color]\n')
			out.append('%s (you), level %d' % [session.identity.name, level])
			for view in session.actors.values():
				if view.category() == 'player':
					out.append('%s, level %d %s' % [view.info.name, int(view.state.get('lv', 1)), Catalog.classes.get(str(view.info.get('class', '')), {}).get('name', '')])
			out.append('\n[color=#7d7666]/invite <name> (or your target) to form a party  ·  /who[/color]')
	return '\n'.join(out)

func _on_info_link(meta: Variant) -> void:
	var target := str(meta)
	if not session:
		return
	if target.begins_with('use:'):
		session.use_item(target.trim_prefix('use:'))
	elif target.begins_with('abandon:'):
		session.abandon_quest(target.trim_prefix('abandon:'))

func set_interface_open(value: bool) -> void:
	interface_open = value
	player.ui_active = value
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE if value or player.paused else Input.MOUSE_MODE_CAPTURED
	if not value:
		var focus := get_viewport().gui_get_focus_owner()
		if focus:
			focus.release_focus()
		_close_panel()
		if session:
			session.close_dialogue()

func _input(event: InputEvent) -> void:
	if player.paused or not event is InputEventKey or not event.pressed or event.echo:
		return
	if chat_input.has_focus():
		if event.keycode == KEY_ESCAPE:
			set_interface_open(false)
			get_viewport().set_input_as_handled()
		return
	if event.keycode == KEY_ENTER or event.keycode == KEY_KP_ENTER:
		visible = true
		set_interface_open(true)
		chat_input.grab_focus()
		get_viewport().set_input_as_handled()
	elif event.physical_keycode == KEY_I:
		visible = true
		set_interface_open(not interface_open)
		get_viewport().set_input_as_handled()
	elif event.keycode == KEY_ESCAPE and interface_open:
		set_interface_open(false)
		get_viewport().set_input_as_handled()

func show_message(text: String, _seconds := 3.5) -> void:
	add_chat_message('Game', text)

func show_region(text: String) -> void:
	region_label.text = text
	zone_label.text = text if text.contains('Veyr') else 'Veyr · ' + text.trim_prefix('The ')
	zone_label.tooltip_text = zone_label.text
	_region_time = 4.0
	add_chat_message('Game', 'Entered ' + text + '.')

func _draw_crosshair() -> void:
	var m := Vector2(8, 8)
	var col := Color(0.9, 0.9, 0.85, 0.75)
	crosshair.draw_line(m + Vector2(-5, 0), m + Vector2(-1.5, 0), col)
	crosshair.draw_line(m + Vector2(1.5, 0), m + Vector2(5, 0), col)
	crosshair.draw_line(m + Vector2(0, -5), m + Vector2(0, -1.5), col)
	crosshair.draw_line(m + Vector2(0, 1.5), m + Vector2(0, 5), col)

func _process(delta: float) -> void:
	status.queue_redraw()
	map_box.queue_redraw()
	crosshair.visible = not player.paused and not interface_open
	_region_time -= delta
	region_label.modulate.a = clampf(_region_time, 0, 1) * clampf((4 - _region_time) * 2, 0, 1)
	if portrait_body != _portrait_key():
		_refresh_portrait()
	if info_panel.visible:
		_refresh_info()
	if menu.visible:
		_updating_menu = true
		time_label.text = 'Time of day:  ' + weather.clock_text()
		time_slider.value = weather.hour
		weather_select.select(weather.ORDER.find(weather.target))
		flow_check.button_pressed = weather.time_flows
		_updating_menu = false

func _build_menu() -> void:
	menu = PanelContainer.new()
	var st := _panel_style(0.94)
	st.content_margin_left = 30
	st.content_margin_right = 30
	st.content_margin_top = 22
	st.content_margin_bottom = 22
	st.set_border_width_all(3)
	menu.add_theme_stylebox_override('panel', st)
	menu.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	menu.custom_minimum_size = Vector2(470, 0)
	root.add_child(menu)
	menu.hide()
	var box := VBoxContainer.new()
	box.add_theme_constant_override('separation', 9)
	menu.add_child(box)
	var title := _label('V E Y R', 34, Color(0.92, 0.82, 0.58))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(title)
	var sub := _label('An island town in the style of the Elder Scrolls III', 14, GOLD_DIM)
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(sub)
	box.add_child(HSeparator.new())
	for pair in [['Return to the journey', func() -> void: player.set_menu(false)],
			['Wait one hour', func() -> void: weather.wait_hours(1.0)],
			['Return to the harbour', _return_to_harbour],
			['Log out to character select', _log_out]]:
		var b := Button.new()
		b.text = pair[0]
		b.pressed.connect(pair[1])
		_style_button(b)
		box.add_child(b)
		if pair[0].begins_with('Log out'):
			menu_logout = b
	time_label = _label('Time of day', 16)
	box.add_child(time_label)
	time_slider = HSlider.new()
	time_slider.min_value = 0.0
	time_slider.max_value = 23.99
	time_slider.step = 0.05
	time_slider.value_changed.connect(_on_time_changed)
	box.add_child(time_slider)
	flow_check = CheckBox.new()
	flow_check.text = 'Time passes'
	_style_button(flow_check)
	flow_check.toggled.connect(_on_flow_toggled)
	box.add_child(flow_check)
	box.add_child(_label('Weather', 16))
	weather_select = OptionButton.new()
	for w in weather.ORDER:
		weather_select.add_item(w)
	_style_button(weather_select)
	weather_select.item_selected.connect(_on_weather_selected)
	box.add_child(weather_select)
	box.add_child(_label('Character', 16))
	var model_select := OptionButton.new()
	for m in ['Male', 'Female']:
		model_select.add_item(m)
	_style_button(model_select)
	model_select.item_selected.connect(func(i: int) -> void: player.set_body_model(['male', 'female'][i]))
	model_select.visibility_changed.connect(func() -> void:
		model_select.select(1 if player.body_model == 'female' else 0)
		model_select.disabled = session != null)
	box.add_child(model_select)
	box.add_child(_label('Mouse sensitivity', 16))
	var sens := HSlider.new()
	sens.min_value = 0.0006
	sens.max_value = 0.005
	sens.step = 0.0001
	sens.value = player.mouse_sensitivity
	sens.value_changed.connect(func(v: float) -> void: player.mouse_sensitivity = v)
	box.add_child(sens)
	box.add_child(HSeparator.new())
	var keys := _label('WASD walk  -  Shift run  -  Caps Lock auto-run  -  Space jump  -  C sneak  -  V change view\nTab target  -  click target  -  1-0 action bar  -  E talk / attack  -  right-click talk / attack\nF ready sword  -  G torch  -  T wait  -  Y weather  -  F1 hide HUD  -  I interface  -  Enter chat', 13, GOLD_DIM)
	keys.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(keys)
	var quit := Button.new()
	quit.text = 'Quit'
	quit.pressed.connect(func() -> void: get_tree().quit())
	_style_button(quit)
	box.add_child(quit)

func _return_to_harbour() -> void:
	if session:
		session.request_unstuck()
		player.set_menu(false)
	else:
		player.return_to_spawn()

func _log_out() -> void:
	player.set_menu(false)
	var main := get_tree().root.get_node_or_null('Main')
	if main:
		main.logout()

func _on_time_changed(v: float) -> void:
	if not _updating_menu:
		weather.set_hour(v)

func _on_flow_toggled(v: bool) -> void:
	if not _updating_menu:
		weather.time_flows = v

func _on_weather_selected(i: int) -> void:
	if not _updating_menu:
		weather.set_weather(weather.ORDER[i])

func set_menu(value: bool) -> void:
	if value:
		visible = true
		set_interface_open(false)
	menu_shade.visible = value
	menu.visible = value
	if menu_logout:
		menu_logout.visible = session != null
	if value:
		menu.reset_size()
		menu.position = (root.size - menu.size) * 0.5
