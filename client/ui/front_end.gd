extends CanvasLayer
## Login, character lobby and character creation, drawn over a live view of the harbour. Styled with the
## HUD's own helpers so it matches the in-game interface. All decisions go through main.gd / the session.

const CLIENT_CFG := 'user://client.cfg'
const SLOTS := 3   ## character slots shown (the realm enforces its own limit)

var main: Node
var hud: CanvasLayer
var root: Control
var title: Label
var panel: PanelContainer
var box: VBoxContainer
var status: Label
var roster: Array = []
var selected := 0
var _delete_armed := -1
var _username: LineEdit
var _password: LineEdit
var _address: LineEdit
var _identity := {'name': '', 'sex': 'male', 'race': 'human', 'skin': 1, 'class': 'warrior'}

func setup(game: Node) -> void:
	main = game
	hud = main.world.hud
	layer = 20
	root = Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	title = hud._label('V E Y R', 64, Color(0.92, 0.82, 0.58))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	title.position.y = 40
	root.add_child(title)
	var sub: Label = hud._label('An island town in the style of the Elder Scrolls III', 16, hud.GOLD_DIM)
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	sub.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	sub.position.y = 118
	root.add_child(sub)
	panel = PanelContainer.new()
	var st: StyleBoxFlat = hud._panel_style(0.93)
	st.set_border_width_all(3)
	st.content_margin_left = 26
	st.content_margin_right = 26
	st.content_margin_top = 20
	st.content_margin_bottom = 20
	panel.add_theme_stylebox_override('panel', st)
	panel.custom_minimum_size = Vector2(420, 0)
	root.add_child(panel)
	box = VBoxContainer.new()
	box.add_theme_constant_override('separation', 8)
	panel.add_child(box)
	status = hud._label('', 15, Color('#e9c88a'))
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	main.session.status_changed.connect(set_status)
	show_login()

func set_status(text: String) -> void:
	status.text = text

func _process(_delta: float) -> void:
	var area := root.get_viewport_rect().size
	panel.position = Vector2(maxf(40.0, area.x * 0.08), maxf(160.0, (area.y - panel.size.y) * 0.5))

func _clear() -> void:
	if status.get_parent():
		status.get_parent().remove_child(status)
	for child in box.get_children():
		box.remove_child(child)
		child.queue_free()
	panel.reset_size()

func _heading(text: String) -> void:
	var l: Label = hud._label(text, 26)
	box.add_child(l)
	box.add_child(HSeparator.new())

func _field(label: String, placeholder: String, value: String, secret := false) -> LineEdit:
	box.add_child(hud._label(label, 15, hud.GOLD_DIM))
	var e := LineEdit.new()
	e.placeholder_text = placeholder
	e.text = value
	e.secret = secret
	e.add_theme_font_override('font', hud.chat_font)
	e.add_theme_font_size_override('font_size', 17)
	e.add_theme_color_override('font_color', Color('#e4dcc9'))
	e.add_theme_stylebox_override('normal', hud._panel_style(0.7))
	e.add_theme_stylebox_override('focus', hud._panel_style(1.0))
	box.add_child(e)
	return e

func _button(text: String, action: Callable, parent: Node = null) -> Button:
	var b := Button.new()
	b.text = text
	hud._style_button(b)
	b.pressed.connect(action)
	(parent if parent else box).add_child(b)
	return b

func _row() -> HBoxContainer:
	var r := HBoxContainer.new()
	r.add_theme_constant_override('separation', 8)
	box.add_child(r)
	return r

func _option(label: String, items: Array, selected_index: int, on_pick: Callable) -> OptionButton:
	box.add_child(hud._label(label, 15, hud.GOLD_DIM))
	var o := OptionButton.new()
	for item in items:
		o.add_item(item)
	o.select(selected_index)
	hud._style_button(o)
	o.item_selected.connect(on_pick)
	box.add_child(o)
	return o

func _note(text: String, color := Color('#cfc5aa'), size := 14) -> Label:
	var l: Label = hud._label(text, size, color)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size.x = 400
	box.add_child(l)
	return l

# ---------------------------------------------------------------- login

func show_login(message := '') -> void:
	visible = true
	main.show_preview({})
	_clear()
	_heading('Sign in')
	var cfg := ConfigFile.new()
	cfg.load(CLIENT_CFG)
	_username = _field('Account', 'username', cfg.get_value('login', 'username', ''))
	_password = _field('Password', '8 or more characters', '', true)
	_address = _field('Realm', 'host:port', cfg.get_value('login', 'address', main.default_address()))
	_password.text_submitted.connect(func(_t: String) -> void: _sign_in(false))
	var r := _row()
	_button('Sign in', _sign_in.bind(false), r).size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_button('Create account', _sign_in.bind(true), r).size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_child(HSeparator.new())
	_button('Play offline', func() -> void: set_status('Starting a local realm...'); main.start_offline())
	_note('Offline play runs a private realm inside the game. Your offline characters are kept on this computer.', hud.GOLD_DIM, 13)
	_button('Quit', func() -> void: get_tree().quit())
	box.add_child(status)
	status.text = message
	var first: LineEdit = _username if _username.text == '' else _password
	first.grab_focus.call_deferred()

func _sign_in(creating: bool) -> void:
	var cfg := ConfigFile.new()
	cfg.set_value('login', 'username', _username.text.strip_edges())
	cfg.set_value('login', 'address', _address.text.strip_edges())
	cfg.save(CLIENT_CFG)
	main.sign_in(_address.text.strip_edges(), _username.text.strip_edges(), _password.text, creating)

# ---------------------------------------------------------------- lobby

func show_lobby(list: Array, message := '') -> void:
	visible = true
	roster = list
	selected = clampi(selected, 0, maxi(roster.size() - 1, 0))
	_delete_armed = -1
	_clear()
	_heading('Characters')
	for i in roster.size():
		var c: Dictionary = roster[i]
		var b := Button.new()
		b.toggle_mode = true
		b.button_pressed = i == selected
		b.text = '%s\nLevel %d %s %s  ·  %s' % [c.name, int(c.level), Catalog.races.get(c.race, {}).get('name', c.race), Catalog.classes.get(c['class'], {}).get('name', c['class']), c.zone]
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		hud._style_button(b)
		b.custom_minimum_size.y = 54
		b.pressed.connect(func() -> void: selected = i; show_lobby(roster))
		b.gui_input.connect(func(e: InputEvent) -> void:
			if e is InputEventMouseButton and e.double_click:
				_enter())
		box.add_child(b)
	for i in range(roster.size(), SLOTS):
		_button('+  Create a new character', show_create).add_theme_color_override('font_color', hud.GOLD_DIM)
	box.add_child(HSeparator.new())
	if not roster.is_empty():
		_button('Enter the world', _enter).add_theme_color_override('font_color', hud.GOLD)
	var r := _row()
	if not roster.is_empty():
		_button('Delete', _delete, r).size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_button('Log out', func() -> void: main.log_out_account(), r).size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_child(status)
	status.text = message
	if roster.is_empty():
		main.show_preview({})
	else:
		main.show_preview(roster[selected])

func _enter() -> void:
	if roster.is_empty():
		return
	main.session.enter(int(roster[selected].id))

func _delete() -> void:
	var c: Dictionary = roster[selected]
	if _delete_armed != int(c.id):
		_delete_armed = int(c.id)
		set_status('Press Delete again to permanently delete %s.' % c.name)
		return
	main.session.delete_character(int(c.id))

# ---------------------------------------------------------------- creation

func show_create() -> void:
	_clear()
	_heading('New character')
	var name_edit := _field('Name', 'letters, spaces, apostrophes', _identity.name)
	name_edit.max_length = 18
	name_edit.text_changed.connect(func(t: String) -> void: _identity.name = t)
	box.add_child(hud._label('Sex', 15, hud.GOLD_DIM))
	var sex_row := _row()
	var group := ButtonGroup.new()
	for sex in Catalog.SEXES:
		var b := _button(sex.capitalize(), func() -> void: _identity.sex = sex; _update_preview(), sex_row)
		b.toggle_mode = true
		b.button_group = group
		b.button_pressed = _identity.sex == sex
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var race_ids: Array = Catalog.race_order.filter(func(id: String) -> bool: return Catalog.races[id].playable)
	if not _identity.race in race_ids:
		_identity.race = race_ids[0]
	var refs := {}   # lambdas capture locals by value, so the widgets they update live in a shared dictionary
	_option('Race', race_ids.map(func(id: String) -> String: return Catalog.races[id].name), race_ids.find(_identity.race),
		func(i: int) -> void:
			_identity.race = race_ids[i]
			refs.race_note.text = Catalog.races[race_ids[i]].description
			_fill_skins(refs.skin_row)
			_update_preview())
	refs.race_note = _note(Catalog.races[_identity.race].description, hud.GOLD_DIM, 13)
	box.add_child(hud._label('Skin tone', 15, hud.GOLD_DIM))
	refs.skin_row = _row()
	_fill_skins(refs.skin_row)
	var class_ids: Array = Catalog.class_order.filter(func(id: String) -> bool: return Catalog.classes[id].playable)
	if not _identity['class'] in class_ids:
		_identity['class'] = class_ids[0]
	_option('Class', class_ids.map(func(c: String) -> String: return Catalog.classes[c].name), class_ids.find(_identity['class']),
		func(i: int) -> void:
			_identity['class'] = class_ids[i]
			refs.class_note.text = _class_text(class_ids[i]))
	refs.class_note = _note(_class_text(_identity['class']), Color('#cfc5aa'), 13)
	box.add_child(HSeparator.new())
	var r := _row()
	_button('Create', func() -> void: main.session.create_character(_identity.duplicate()), r).size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_button('Back', func() -> void: show_lobby(roster), r).size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_child(status)
	status.text = 'Male High Elves now have a sculpted bald head and pointed ears. Other race variants are in progress.'
	_update_preview()
	name_edit.grab_focus.call_deferred()

func _class_text(job: String) -> String:
	var c: Dictionary = Catalog.classes[job]
	var names: Array = c.abilities.map(func(a: Dictionary) -> String: return '%s (%d)' % [a.name, int(a.level)])
	return '%s\nUses %s.  Abilities: %s.' % [c.description, c.resource, ', '.join(names)]

func _fill_skins(row: HBoxContainer) -> void:
	for child in row.get_children():
		child.queue_free()
	var skins: Array = Catalog.races[_identity.race].skins
	_identity.skin = clampi(int(_identity.skin), 0, skins.size() - 1)
	var group := ButtonGroup.new()
	for i in skins.size():
		var b := Button.new()
		b.toggle_mode = true
		b.button_group = group
		b.button_pressed = i == _identity.skin
		b.custom_minimum_size = Vector2(52, 34)
		var normal := StyleBoxFlat.new()
		normal.bg_color = Color(str(skins[i])) * Color(0.82, 0.68, 0.58)
		normal.set_border_width_all(2)
		normal.border_color = hud.FRAME_DARK
		normal.set_corner_radius_all(3)
		var chosen := normal.duplicate()
		chosen.border_color = hud.GOLD
		chosen.set_border_width_all(3)
		b.add_theme_stylebox_override('normal', normal)
		b.add_theme_stylebox_override('hover', chosen)
		b.add_theme_stylebox_override('pressed', chosen)
		b.add_theme_stylebox_override('hover_pressed', chosen)
		b.pressed.connect(func() -> void: _identity.skin = i; _update_preview())
		row.add_child(b)

func _update_preview() -> void:
	main.show_preview(_identity)
