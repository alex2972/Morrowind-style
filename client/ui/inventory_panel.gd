extends Control
## The backpack: a RuneScape-proportioned panel with 4 columns of WoW-style square slots (28 = 7 rows),
## each showing its item's icon and stack count. Click to use, drag onto another slot to swap, hover for
## the item's name and description. Everything shown comes from the character sheet; every action is a
## request to the realm (use_item / swap_slots).

const COLS := 4
const GAP := 4.0
const PAD := 9.0
const SLOT_TEX := preload('res://assets/ui/inventory/slot.png')
const PANEL_TEX := preload('res://assets/ui/inventory/panel.png')

var session: Node
var hud: CanvasLayer
var slot_size := 48.0
var slots: Array = []
var _shown_hash := 0

class Slot extends Control:
	var index := 0
	var view: Control          ## the inventory panel
	var item := ''
	var count := 0
	var icon: Texture2D

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_entered.connect(queue_redraw)
		mouse_exited.connect(queue_redraw)

	func _draw() -> void:
		draw_texture_rect(view.SLOT_TEX, Rect2(Vector2.ZERO, size), false)
		if icon:
			draw_texture_rect(icon, Rect2(Vector2.ONE * 3.0, size - Vector2.ONE * 6.0), false)
		if count > 1:
			var font: Font = view.hud.chat_font
			var at := Vector2(0, size.y - 4)
			draw_string_outline(font, at, str(count), HORIZONTAL_ALIGNMENT_RIGHT, size.x - 5, 14, 4, Color.BLACK)
			draw_string(font, at, str(count), HORIZONTAL_ALIGNMENT_RIGHT, size.x - 5, 14, Color('#f4ecd6'))
		if get_global_rect().has_point(get_global_mouse_position()):
			draw_rect(Rect2(Vector2.ONE, size - Vector2.ONE * 2), Color(0.95, 0.85, 0.55, 0.85), false, 1.5)

	func _gui_input(event: InputEvent) -> void:
		if event is InputEventMouseButton and not event.pressed and item != '' \
				and event.button_index in [MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT] and not get_viewport().gui_is_dragging():
			view.use_slot(index)
			accept_event()

	func _get_drag_data(_at: Vector2) -> Variant:
		if item == '':
			return null
		var preview := TextureRect.new()
		preview.texture = icon
		preview.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		preview.size = size - Vector2.ONE * 6.0
		preview.modulate.a = 0.85
		set_drag_preview(preview)
		return {'pack_slot': index}

	func _can_drop_data(_at: Vector2, data: Variant) -> bool:
		return data is Dictionary and data.has('pack_slot')

	func _drop_data(_at: Vector2, data: Variant) -> void:
		if int(data.pack_slot) != index:
			view.session.send(Protocol.C_SWAP_SLOTS, {'a': int(data.pack_slot), 'b': index})

func setup(owner_hud: CanvasLayer, owner_session: Node) -> void:
	hud = owner_hud
	session = owner_session
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var bg := NinePatchRect.new()
	bg.name = 'Panel'
	bg.texture = PANEL_TEX
	bg.patch_margin_left = 8
	bg.patch_margin_top = 8
	bg.patch_margin_right = 8
	bg.patch_margin_bottom = 8
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(bg)
	for i in int(Catalog.rules.get('pack_slots', 28)):
		var s := Slot.new()
		s.index = i
		s.view = self
		add_child(s)
		slots.append(s)

func rows() -> int:
	return ceili(slots.size() / float(COLS))

func needed_size(slot: float) -> Vector2:
	return Vector2(COLS * slot + (COLS - 1) * GAP + PAD * 2, rows() * slot + (rows() - 1) * GAP + PAD * 2)

func arrange(slot: float) -> void:
	slot_size = slot
	size = needed_size(slot)
	$Panel.size = size
	for i in slots.size():
		slots[i].position = Vector2(PAD + (i % COLS) * (slot + GAP), PAD + floori(i / float(COLS)) * (slot + GAP))
		slots[i].size = Vector2(slot, slot)

func refresh() -> void:
	var pack: Array = session.sheet.get('pack', [])
	var h := pack.hash()
	if h == _shown_hash:
		return
	_shown_hash = h
	for i in slots.size():
		var s: Slot = slots[i]
		var entry: Variant = pack[i] if i < pack.size() else null
		s.item = str(entry[0]) if entry != null else ''
		s.count = int(entry[1]) if entry != null else 0
		if s.item != '':
			var it: Dictionary = Catalog.item(s.item)
			s.icon = Catalog.icon(str(it.icon))
			s.tooltip_text = '%s\n%s%s' % [it.name, it.description, '\nClick to use.' if it.usable else '']
		else:
			s.icon = null
			s.tooltip_text = ''
		s.queue_redraw()

func use_slot(i: int) -> void:
	var s: Slot = slots[i]
	if not Catalog.item(s.item).get('usable', false):
		if session.ui:
			session.ui.show_error('You cannot use that.')
		return
	session.send(Protocol.C_USE_ITEM, {'slot': i})
