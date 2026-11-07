extends Node
## Controls for up to 4 local players, read straight from the devices so
## each player owns one joypad (or one half of the keyboard).
##
## Joypad:  stick / d-pad steer, A accelerate, B brake / reverse,
##          RB or RT hop + drift, LB, LT or X use item, Y look back, Start pause.
## Keyboard "left" (WASD): W accelerate, S brake, A/D steer, Space drift,
##          E item, Q look back.
## Keyboard "right" (arrows): arrows, Right Shift or . drift, Enter or , item,
##          / look back.
## One player alone gets both halves, Z item and X drift too, and every joypad.

const DEAD := 0.22

# per player: {"kb": "both" | "left" | "right" | "", "joy": device id, -1 = any, -2 = none}
var slots := [{"kb": "both", "joy": -1}]
var _prev := [{}, {}, {}, {}]
var _now := [{}, {}, {}, {}]

const KB := {
	"left": {"up": [KEY_W], "down": [KEY_S], "left": [KEY_A], "right": [KEY_D],
		"drift": [KEY_SPACE], "item": [KEY_E], "back": [KEY_Q], "ok": [KEY_E, KEY_SPACE], "cancel": [KEY_Q, KEY_TAB]},
	"right": {"up": [KEY_UP], "down": [KEY_DOWN], "left": [KEY_LEFT], "right": [KEY_RIGHT],
		"drift": [KEY_SHIFT, KEY_PERIOD], "item": [KEY_ENTER, KEY_KP_ENTER, KEY_COMMA], "back": [KEY_SLASH],
		"ok": [KEY_ENTER, KEY_KP_ENTER], "cancel": [KEY_BACKSPACE, KEY_SLASH]},
	"solo": {"drift": [KEY_X, KEY_SHIFT], "item": [KEY_Z, KEY_CTRL], "back": [KEY_C], "ok": [KEY_Z],
		"cancel": [KEY_X, KEY_ESCAPE]},
}

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	process_priority = -100
	process_physics_priority = -100
	_extend_ui()

func set_players(list: Array) -> void:
	## list of {"kb":..., "joy":...}; called by the join screen
	slots = list.duplicate(true)

func count() -> int:
	return slots.size()

func _physics_process(_dt: float) -> void:
	for p in slots.size():
		_prev[p] = _now[p]
		_now[p] = _read(p)

func _read(p: int) -> Dictionary:
	var s: Dictionary = slots[p]
	var r := {"steer": 0.0, "throttle": 0.0, "brake": 0.0, "drift": false, "item": false, "back": false,
		"pause": false, "up": false, "down": false, "left": false, "right": false, "ok": false, "cancel": false}
	var kbs := []
	match s.get("kb", ""):
		"both":
			kbs = ["left", "right", "solo"]
		"left":
			kbs = ["left"]
		"right":
			kbs = ["right"]
	for k in kbs:
		var m: Dictionary = KB[k]
		if _any(m.get("left", [])): r.steer -= 1.0
		if _any(m.get("right", [])): r.steer += 1.0
		if _any(m.get("up", [])): r.throttle = 1.0; r.up = true
		if _any(m.get("down", [])): r.brake = 1.0; r.down = true
		if _any(m.get("drift", [])): r.drift = true
		if _any(m.get("item", [])): r.item = true
		if _any(m.get("back", [])): r.back = true
		if _any(m.get("left", [])): r.left = true
		if _any(m.get("right", [])): r.right = true
		if _any(m.get("ok", [])): r.ok = true
		if _any(m.get("cancel", [])): r.cancel = true
	if kbs.size() > 0 and Input.is_physical_key_pressed(KEY_ESCAPE):
		r.pause = true
	var devs := []
	var j: int = s.get("joy", -2)
	if j == -1:
		devs = Input.get_connected_joypads()
	elif j >= 0:
		devs = [j]
	for d in devs:
		var ax := Input.get_joy_axis(d, JOY_AXIS_LEFT_X)
		if absf(ax) > DEAD:
			r.steer += (absf(ax) - DEAD) / (1.0 - DEAD) * signf(ax)
		if Input.is_joy_button_pressed(d, JOY_BUTTON_DPAD_LEFT): r.steer -= 1.0
		if Input.is_joy_button_pressed(d, JOY_BUTTON_DPAD_RIGHT): r.steer += 1.0
		if Input.is_joy_button_pressed(d, JOY_BUTTON_A): r.throttle = 1.0; r.ok = true
		if Input.is_joy_button_pressed(d, JOY_BUTTON_B): r.brake = 1.0; r.cancel = true
		if Input.is_joy_button_pressed(d, JOY_BUTTON_RIGHT_SHOULDER) or Input.get_joy_axis(d, JOY_AXIS_TRIGGER_RIGHT) > 0.4:
			r.drift = true
		if Input.is_joy_button_pressed(d, JOY_BUTTON_LEFT_SHOULDER) or Input.is_joy_button_pressed(d, JOY_BUTTON_X) \
				or Input.get_joy_axis(d, JOY_AXIS_TRIGGER_LEFT) > 0.4:
			r.item = true
		if Input.is_joy_button_pressed(d, JOY_BUTTON_Y): r.back = true
		if Input.is_joy_button_pressed(d, JOY_BUTTON_START): r.pause = true
		var ay := Input.get_joy_axis(d, JOY_AXIS_LEFT_Y)
		if ay < -0.5 or Input.is_joy_button_pressed(d, JOY_BUTTON_DPAD_UP): r.up = true
		if ay > 0.5 or Input.is_joy_button_pressed(d, JOY_BUTTON_DPAD_DOWN): r.down = true
		if ax < -0.5 or Input.is_joy_button_pressed(d, JOY_BUTTON_DPAD_LEFT): r.left = true
		if ax > 0.5 or Input.is_joy_button_pressed(d, JOY_BUTTON_DPAD_RIGHT): r.right = true
	r.steer = clampf(r.steer, -1.0, 1.0)
	return r

func _any(keys: Array) -> bool:
	for k in keys:
		if Input.is_physical_key_pressed(k):
			return true
	return false

func state(p: int) -> Dictionary:
	return _now[p] if p < slots.size() else {}

func just(p: int, key: String) -> bool:
	if p >= slots.size():
		return false
	return bool(_now[p].get(key, false)) and not bool(_prev[p].get(key, false))

func any_pause() -> bool:
	for p in slots.size():
		if just(p, "pause"):
			return true
	return false

## Joypad that pressed A (for "press A to join"); -1 none. Keyboard halves
## join with their item key: returns "left" / "right".
func join_press(taken: Array) -> Variant:
	for d in Input.get_connected_joypads():
		if d in taken:
			continue
		if Input.is_joy_button_pressed(d, JOY_BUTTON_A):
			return d
	if not "left" in taken and Input.is_physical_key_pressed(KEY_E):
		return "left"
	if not "right" in taken and (Input.is_physical_key_pressed(KEY_ENTER) or Input.is_physical_key_pressed(KEY_COMMA)):
		return "right"
	return null

var using_joypad := false
var last_joy := -1        # joypad that pressed something last (-1: keyboard)

func _input(e: InputEvent) -> void:
	if e is InputEventJoypadButton or (e is InputEventJoypadMotion and absf(e.axis_value) > 0.5):
		using_joypad = true
		last_joy = e.device
	elif e is InputEventKey:
		using_joypad = false
		last_joy = -1

## Slot for one player alone: the keyboard and every joypad.
func solo() -> void:
	set_players([{"kb": "both", "joy": -1}])

## Read a device's menu keys without it being a player yet (join screen).
func peek(slot: Dictionary) -> Dictionary:
	var keep := slots
	slots = [slot]
	var r := _read(0)
	slots = keep
	return r

func _extend_ui() -> void:
	_ext("ui_accept", [KEY_Z, KEY_SPACE, KEY_ENTER, KEY_E], [JOY_BUTTON_A])
	_ext("ui_cancel", [KEY_X, KEY_ESCAPE, KEY_BACKSPACE], [JOY_BUTTON_B])
	_ext("ui_up", [KEY_W], [JOY_BUTTON_DPAD_UP])
	_ext("ui_down", [KEY_S], [JOY_BUTTON_DPAD_DOWN])
	_ext("ui_left", [KEY_A], [JOY_BUTTON_DPAD_LEFT])
	_ext("ui_right", [KEY_D], [JOY_BUTTON_DPAD_RIGHT])

func _ext(action: String, ks: Array, bs: Array) -> void:
	for k in ks:
		var e := InputEventKey.new()
		e.physical_keycode = k
		if not InputMap.action_has_event(action, e):
			InputMap.action_add_event(action, e)
	for b in bs:
		var e := InputEventJoypadButton.new()
		e.button_index = b
		e.device = -1
		if not InputMap.action_has_event(action, e):
			InputMap.action_add_event(action, e)
