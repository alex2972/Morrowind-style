extends Control
## Resolution-independent engraved bronze frame. All ornament stays outside the content.
@export var inset := 0.0
@export var fill := Color(0.035, 0.039, 0.034, 0.87)
const DARK := Color('#19150f')
const BRONZE := Color('#79613b')
const LIGHT := Color('#b39b65')

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	resized.connect(queue_redraw)

func _draw() -> void:
	var r := Rect2(Vector2.ONE * inset, size - Vector2.ONE * inset * 2.0)
	draw_style_box(_style(Color.TRANSPARENT, DARK, 6), r.grow(2))
	draw_style_box(_style(fill, BRONZE, 2), r)
	draw_style_box(_style(Color.TRANSPARENT, LIGHT.darkened(0.25), 1), r.grow(-3))
	draw_style_box(_style(Color.TRANSPARENT, DARK, 1), r.grow(-6))
	# Fine hammered-metal highlights along the outer rim.
	for x in range(10, int(r.size.x) - 10, 7):
		var a := 0.12 + 0.1 * sin(float(x) * 1.7)
		draw_line(r.position + Vector2(x, 1), r.position + Vector2(x + 3, 1), Color(0.95, 0.83, 0.58, a))
	for corner in [Vector2(1, 1), Vector2(-1, 1), Vector2(1, -1), Vector2(-1, -1)]:
		var p := r.position + Vector2(5.0 if corner.x > 0 else r.size.x - 5.0, 5.0 if corner.y > 0 else r.size.y - 5.0)
		var points := PackedVector2Array()
		for v in [Vector2(0, 17), Vector2(3, 8), Vector2(10, 5), Vector2(6, 2), Vector2(0, 0), Vector2(2, 6), Vector2(5, 10), Vector2(8, 3), Vector2(17, 0)]:
			points.append(p + v * corner)
		draw_polyline(points, DARK, 3.0, true)
		draw_polyline(points, LIGHT, 1.0, true)
		draw_circle(p + Vector2(3, 3) * corner, 1.5, LIGHT)

func _style(bg: Color, border: Color, width: int) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = bg
	style.border_color = border
	style.set_border_width_all(width)
	style.set_corner_radius_all(5)
	return style
