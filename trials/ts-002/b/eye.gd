# TS-002 trial, option B: eye logic in GDScript (same rules as option A's EyeState).
# Run:  godot --path trials/ts-002/b -- [--mirror] [--rotate90] [--bench 60] [--no-vsync]
#                                       [--expression happy] [--screenshot file.png] [--mqtt]
# Keys: 1-6 expressions, space blinks, Esc quits. Mouse moves the gaze.
extends ColorRect

const MOODS := {
	"neutral":   {"open": 1.0,  "low": 0.0,  "curve": 0.0, "pupil": 1.0,  "spark": 0.0},
	"happy":     {"open": 0.9,  "low": 0.38, "curve": 1.0, "pupil": 1.15, "spark": 0.0},
	"sparkle":   {"open": 0.95, "low": 0.3,  "curve": 1.0, "pupil": 1.3,  "spark": 1.0},
	"surprised": {"open": 1.15, "low": 0.0,  "curve": 0.0, "pupil": 0.65, "spark": 0.0},
	"sleepy":    {"open": 0.42, "low": 0.08, "curve": 0.0, "pupil": 0.9,  "spark": 0.0},
	"asleep":    {"open": 0.0,  "low": 0.05, "curve": 0.0, "pupil": 1.0,  "spark": 0.0},
}
var EXPRESSION_RATE := -log(1.0 - 0.12) * 60.0
var GAZE_RATE := -log(1.0 - 0.2) * 60.0
const BLINK_S := 0.2

var now := 0.0
var cur: Dictionary = MOODS["neutral"].duplicate()
var target: Dictionary = MOODS["neutral"].duplicate()
var gaze := Vector2.ZERO
var gaze_target := Vector2.ZERO
var last_aim := -1e9
var next_wander := 0.0
var next_blink := 2.5
var blink_start := -1.0

var args := {"bench": 0.0, "eye_size": 0.9, "mirror": false, "rotate90": false,
	"no_vsync": false, "expression": "neutral", "screenshot": "", "mqtt": false, "fps_cap": 0}
var frame_ms: PackedFloat64Array = []
var start_us := 0
var last_us := 0
var next_mood := 3.0
var mqtt: MiniMqtt = null
var finishing := false


func _ready() -> void:
	_parse_args()
	if args.no_vsync:
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = args.fps_cap
	print("GL: ", RenderingServer.get_video_adapter_name(), " | ", OS.get_video_adapter_driver_info(),
		" | ", RenderingServer.get_current_rendering_driver_name())
	var m := material as ShaderMaterial
	m.set_shader_parameter("u_eye_size", args.eye_size)
	m.set_shader_parameter("u_mirror", args.mirror)
	m.set_shader_parameter("u_rotate90", args.rotate90)
	set_expression(args.expression)
	if args.mqtt:
		mqtt = MiniMqtt.new()
		mqtt.message.connect(_on_mqtt)
		mqtt.start("127.0.0.1", 1883, "left")
	start_us = Time.get_ticks_usec()
	last_us = start_us


func _parse_args() -> void:
	var a := OS.get_cmdline_user_args()
	var i := 0
	while i < a.size():
		match a[i]:
			"--bench": args.bench = float(a[i + 1]); i += 1
			"--eye-size": args.eye_size = float(a[i + 1]); i += 1
			"--expression": args.expression = a[i + 1]; i += 1
			"--screenshot": args.screenshot = a[i + 1]; i += 1
			"--fps-cap": args.fps_cap = int(a[i + 1]); i += 1
			"--mirror": args.mirror = true
			"--rotate90": args.rotate90 = true
			"--no-vsync": args.no_vsync = true
			"--mqtt": args.mqtt = true
		i += 1


func set_expression(name: String) -> void:
	if MOODS.has(name):
		target = MOODS[name].duplicate()


func blink() -> void:
	if blink_start < 0.0:
		blink_start = now


func _on_mqtt(topic: String, payload: String) -> void:
	var data = JSON.parse_string(payload)   # TBD-003: plain JSON until schemas exist
	if typeof(data) != TYPE_DICTIONARY:
		return                              # fail friendly: ignore bad messages
	if topic == MiniMqtt.EYES_BLINK:
		blink()
		print("mqtt: blink ", data)
	elif topic == MiniMqtt.EYES_EXPRESSION:
		set_expression(str(data.get("name", "")))
		print("mqtt: expression ", data)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_ESCAPE:
			_finish()
		elif event.keycode == KEY_SPACE:
			blink()
		elif event.keycode >= KEY_1 and event.keycode <= KEY_6:
			set_expression(MOODS.keys()[event.keycode - KEY_1])
	elif event is InputEventMouseMotion:
		var size := get_viewport_rect().size
		var scale: float = minf(size.x / 300.0, size.y / 400.0) * args.eye_size
		var p: Vector2 = (event.position - size / 2.0) / scale + Vector2(150, 200)
		gaze_target = Vector2(clampf((p.x - 150.0) / 170.0, -1, 1) * 46.0, clampf((p.y - 200.0) / 220.0, -1, 1) * 88.0)
		last_aim = now


func _process(_delta: float) -> void:
	var t_us := Time.get_ticks_usec()
	var dt := (t_us - last_us) / 1e6
	last_us = t_us
	frame_ms.append(dt * 1000.0)
	var elapsed := (t_us - start_us) / 1e6
	if mqtt:
		mqtt.poll()
	if args.bench > 0.0:
		if elapsed > next_mood:
			set_expression(MOODS.keys()[int(next_mood / 3.0) % MOODS.size()])
			next_mood += 3.0
		if elapsed > args.bench:
			_finish()
			return

	now += dt
	var k := 1.0 - exp(-EXPRESSION_RATE * dt)
	for key in cur:
		cur[key] += (target[key] - cur[key]) * k
	if now - last_aim > 2.5 and now > next_wander:
		gaze_target = Vector2(randf_range(-40, 40), randf_range(-60, 60))
		next_wander = now + randf_range(1.2, 3.0)
	gaze += (gaze_target - gaze) * (1.0 - exp(-GAZE_RATE * dt))
	if now > next_blink and target["open"] > 0.2:
		blink()
	var factor := 1.0
	if blink_start >= 0.0:
		var b := (now - blink_start) / BLINK_S
		if b >= 1.0:
			blink_start = -1.0
			next_blink = now + randf_range(2.5, 6.0)
		else:
			factor = absf(1.0 - 2.0 * b)

	var m := material as ShaderMaterial
	m.set_shader_parameter("u_window", get_viewport_rect().size)
	m.set_shader_parameter("u_gaze", gaze)
	m.set_shader_parameter("u_open", cur["open"] * factor)
	for key in ["low", "curve", "pupil", "spark"]:
		m.set_shader_parameter("u_" + key, cur[key])


func _finish() -> void:
	if finishing:
		return
	finishing = true
	if args.screenshot != "":
		await RenderingServer.frame_post_draw
		var err := get_viewport().get_texture().get_image().save_png(args.screenshot)
		print("screenshot ", args.screenshot, " -> ", error_string(err))
	if mqtt:
		mqtt.stop()
	if args.bench > 0.0:
		_report()
	get_tree().quit()


func _report() -> void:
	var ms: Array = Array(frame_ms.slice(30 if frame_ms.size() > 60 else 0))
	ms.sort()
	if ms.is_empty():
		print("no frames recorded")
		return
	var total := 0.0
	var hitches := 0
	for v in ms:
		total += v
		if v > 25.0:
			hitches += 1
	print(JSON.stringify({
		"frames": ms.size(),
		"mean_fps": snappedf(1000.0 / (total / ms.size()), 0.01),
		"p99_frame_ms": snappedf(ms[int(ms.size() * 0.99)], 0.01),
		"max_frame_ms": snappedf(ms[-1], 0.01),
		"mean_frame_ms": snappedf(total / ms.size(), 0.001),
		"hitches_over_25ms": hitches,
	}))
