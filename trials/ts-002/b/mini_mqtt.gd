# TS-002 trial, option B: a minimal MQTT 3.1.1 client in GDScript (subscribe, publish
# with QoS 0, last will, keep-alive). A real build would use a maintained add-on such as
# goatchurchprime/godot-mqtt; this exists only to check gate G4 without third-party code.
#
# COUPLING (see TS-002 §2): GDScript can't import shared/topics.py, so the topic names are
# copied here by hand. A Godot renderer would need a neutral topics file instead.
class_name MiniMqtt
extends RefCounted

signal message(topic: String, payload: String)

const EYES_BLINK := "monster/eyes/blink"
const EYES_EXPRESSION := "monster/eyes/expression"

var _tcp := StreamPeerTCP.new()
var _buf := PackedByteArray()
var _status_topic := ""
var _connected := false
var _last_ping := 0


func start(host: String, port: int, side: String) -> void:
	_status_topic = "monster/eyes/%s/status" % side
	_tcp.connect_to_host(host, port)


func poll() -> void:
	_tcp.poll()
	var st := _tcp.get_status()
	if st == StreamPeerTCP.STATUS_CONNECTED and not _connected:
		_connected = true
		_send_connect()
		_send(0x82, _u16(1) + _str(EYES_BLINK) + PackedByteArray([0]) + _str(EYES_EXPRESSION) + PackedByteArray([0]))
		publish(_status_topic, "online", true)
		_last_ping = Time.get_ticks_msec()
	if not _connected:
		return
	var n := _tcp.get_available_bytes()
	if n > 0:
		_buf.append_array(_tcp.get_data(n)[1])
		_parse()
	if Time.get_ticks_msec() - _last_ping > 30000:
		_send(0xC0, PackedByteArray())
		_last_ping = Time.get_ticks_msec()


func publish(topic: String, payload: String, retain := false) -> void:
	_send(0x31 if retain else 0x30, _str(topic) + payload.to_utf8_buffer())


func stop() -> void:
	if _connected:
		publish(_status_topic, "offline", true)
		_send(0xE0, PackedByteArray())   # clean DISCONNECT
		_tcp.poll()
	_tcp.disconnect_from_host()


func _send_connect() -> void:
	var client_id := "ts002-godot-%d" % (randi() % 1000000)
	var vh := _str("MQTT") + PackedByteArray([4, 0x26, 0, 60])   # level 4; clean session + will (retained, QoS 0); keep-alive 60 s
	_send(0x10, vh + _str(client_id) + _str(_status_topic) + _str("offline"))


func _parse() -> void:
	while _buf.size() >= 2:
		var mult := 1
		var length := 0
		var i := 1
		while true:
			if i >= _buf.size():
				return                        # wait for more bytes
			length += (_buf[i] & 127) * mult
			mult *= 128
			if _buf[i] & 128 == 0:
				break
			i += 1
		var total := i + 1 + length
		if _buf.size() < total:
			return
		var kind := _buf[0] >> 4
		var body := _buf.slice(i + 1, total)
		_buf = _buf.slice(total)
		if kind == 3:                          # PUBLISH (QoS 0 only)
			var tlen := (body[0] << 8) | body[1]
			var topic := body.slice(2, 2 + tlen).get_string_from_utf8()
			message.emit(topic, body.slice(2 + tlen).get_string_from_utf8())


func _send(header: int, body: PackedByteArray) -> void:
	var out := PackedByteArray([header])
	var n := body.size()
	while true:                               # MQTT "remaining length" varint
		var byte := n % 128
		n = n / 128
		out.append(byte | (128 if n > 0 else 0))
		if n == 0:
			break
	out.append_array(body)
	_tcp.put_data(out)


func _u16(v: int) -> PackedByteArray:
	return PackedByteArray([v >> 8, v & 255])


func _str(s: String) -> PackedByteArray:
	var b := s.to_utf8_buffer()
	return _u16(b.size()) + b
