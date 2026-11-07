class_name Brains
## Who drives a kart: a local player (Controls) or the AI.

class PlayerBrain:
	var p := 0
	func _init(n: int) -> void:
		p = n
	func think(k: Kart, _dt: float) -> void:
		var s: Dictionary = Controls.state(p)
		k.inp.throttle = s.get("throttle", 0.0)
		k.inp.brake = s.get("brake", 0.0)
		k.inp.steer = s.get("steer", 0.0)
		k.inp.drift = s.get("drift", false)
		k.inp.item = Controls.just(p, "item")
		k.inp.back = s.get("back", false)


class AIBrain:
	## Follows the centre line with its own lane offset, slows for sharp
	## bends, drifts long bends (normal / hard), dodges karts ahead, uses
	## items with a little delay. Skill 0..1 sets speed, lines and mistakes.
	var skill := 0.5
	var lane := 0.0
	var _lane_t := 0.0
	var _item_wait := 0.0
	var _wobble := 0.0
	var _stuck := 0.0
	var _reverse := 0.0
	var rng := RandomNumberGenerator.new()

	func _init(s: float, seed_: int) -> void:
		skill = s
		rng.seed = seed_
		lane = rng.randf_range(-0.45, 0.45)
		_wobble = rng.randf() * 10.0

	func think(k: Kart, dt: float) -> void:
		var t := k.track
		_lane_t -= dt
		if _lane_t <= 0.0:
			_lane_t = rng.randf_range(2.0, 5.0)
			lane = clampf(lane + rng.randf_range(-0.3, 0.3), -0.5, 0.5)
		_wobble += dt
		if k.race.state == "countdown":
			k.inp.throttle = 1.0 if (k.race.countdown_left < 0.9 + (1.0 - skill) * 0.6 and skill > 0.4) else 0.0
			k.inp.steer = 0.0
			return
		var spd := absf(k.speed)
		var look := 7.0 + spd * 0.55
		var s0 := k.prog
		var kk := t.index_at_dist(s0 + look)
		# bend ahead: how much the road turns over the next stretch
		var bend := t.curvature_at(k.seg, int(clampf(spd * 0.6, 4.0, 18.0)))
		var w := t.width[kk] * 0.5 - 1.2
		var want_lat := lane * w
		# cut the inside of bends a little (better lines with skill)
		want_lat += clampf(bend * 3.5 * skill, -w * 0.4, w * 0.4)
		# avoid karts just ahead in the same lane
		for o in k.race.karts:
			if o == k:
				continue
			var gap: float = fposmod(o.prog - k.prog, t.length)
			if gap > 0.5 and gap < 9.0:
				var ol := t.lateral_at(o.global_position, o.seg)
				if absf(ol - want_lat) < 1.6:
					want_lat += 2.2 * (1.0 if want_lat >= ol else -1.0)
		want_lat += sin(_wobble * 0.7) * (1.0 - skill) * 1.2
		want_lat = clampf(want_lat, -w, w)
		var target := t.pos[kk] + t.right[kk] * want_lat
		var to := target - k.global_position
		var fwd := Vector3(-sin(k.yaw), 0, -cos(k.yaw))
		var ang := Vector2(fwd.x, fwd.z).angle_to(Vector2(to.x, to.z))
		var steer := clampf(ang * 2.2, -1.0, 1.0)
		var sharp := absf(bend)
		var throttle := 1.0
		var brake := 0.0
		var limit := k.top_speed * (1.15 - clampf(sharp * 0.9, 0.0, 0.55))
		if spd > limit and sharp > 0.35:
			throttle = 0.0
			if spd > limit * 1.15:
				brake = 0.4
		if absf(ang) > 1.2 and spd > 6.0:
			throttle = 0.3
		# drift long bends
		# drift long bends, only into the bend, and let go when it straightens
		# or turns the other way
		var drift := false
		var bdir := signf(bend)
		if skill > 0.35 and sharp > 0.45 and spd > k.top_speed * 0.6 and steer * bdir > 0.35:
			drift = true
		if k.drifting:
			drift = bdir == k.drift_dir and (sharp > 0.2 or k.drift_t < 0.6 + skill * 0.4)
			if k.drift_level >= 2 and sharp < 0.3:
				drift = false
			if steer * k.drift_dir < -0.4:
				drift = false
		# stuck against something: back up and turn
		if spd < 1.5 and k.race.state == "race" and not k.done:
			_stuck += dt
		else:
			_stuck = 0.0
		if _stuck > 1.2:
			_reverse = 0.9
			_stuck = 0.0
		if _reverse > 0.0:
			_reverse -= dt
			throttle = 0.0
			brake = 1.0
			steer = -steer
		k.inp.throttle = throttle
		k.inp.brake = brake
		k.inp.steer = steer
		k.inp.drift = drift
		k.inp.back = false
		# items
		k.inp.item = false
		if k.item != "":
			_item_wait -= dt
			if _item_wait <= 0.0:
				if _want_use(k):
					k.inp.item = true
				_item_wait = rng.randf_range(0.6, 2.5) * (1.5 - skill)
		else:
			_item_wait = rng.randf_range(0.8, 2.5)

	func _want_use(k: Kart) -> bool:
		match k.item:
			"egg", "egg3", "seeker":
				var a = k.race.kart_ahead(k)
				return a != null and fposmod(a.prog - k.prog, k.track.length) < 45.0 or rng.randf() < 0.15
			"mud":
				var b = k.race.kart_behind(k)
				return b != null and fposmod(k.prog - b.prog, k.track.length) < 20.0 or rng.randf() < 0.2
			"roar":
				for o in k.race.karts:
					if o != k and o.global_position.distance_to(k.global_position) < 10.0:
						return true
				return rng.randf() < 0.05
			"bubble":
				return rng.randf() < 0.3
			_:
				return absf(k.track.curvature_at(k.seg, 12)) < 0.25


class BattleBrain:
	## Arena AI: grab an item egg when empty-handed, otherwise chase the
	## nearest kart that still has balloons, fire when it is in front.
	var skill := 0.5
	var _wait := 0.0
	var _retarget := 0.0
	var target: Node3D
	var _stuck := 0.0
	var _rev := 0.0
	var rng := RandomNumberGenerator.new()

	func _init(s: float, seed_: int) -> void:
		skill = s
		rng.seed = seed_

	func think(k: Kart, dt: float) -> void:
		k.inp.item = false
		k.inp.drift = false
		k.inp.back = false
		if k.race.state != "race" or k.out:
			k.inp.throttle = 0.0
			return
		_retarget -= dt
		if _retarget <= 0.0 or target == null or not is_instance_valid(target):
			_retarget = rng.randf_range(1.5, 3.0)
			target = _pick(k)
		var to := (target.global_position if target else Vector3.ZERO) - k.global_position
		var fwd := Vector3(-sin(k.yaw), 0, -cos(k.yaw))
		var ang := Vector2(fwd.x, fwd.z).angle_to(Vector2(to.x, to.z))
		k.inp.steer = clampf(ang * 2.0, -1.0, 1.0)
		k.inp.throttle = 1.0 if absf(ang) < 2.2 else 0.4
		k.inp.brake = 0.0
		if absf(k.speed) < 1.5:
			_stuck += dt
		else:
			_stuck = 0.0
		if _stuck > 1.0:
			_rev = 0.8
			_stuck = 0.0
		if _rev > 0.0:
			_rev -= dt
			k.inp.throttle = 0.0
			k.inp.brake = 1.0
			k.inp.steer = -k.inp.steer
		if k.item != "":
			_wait -= dt
			if _wait <= 0.0:
				var d := to.length()
				var front := absf(ang) < 0.35 and d < 22.0
				if k.item in ["egg", "egg3", "seeker"] and (front or k.item == "seeker"):
					k.inp.item = true
				elif k.item == "roar" and d < 10.0:
					k.inp.item = true
				elif k.item == "mud" and rng.randf() < 0.3:
					k.inp.item = true
				elif k.item in ["bubble", "fern", "feather"]:
					k.inp.item = rng.randf() < 0.4
				_wait = rng.randf_range(0.4, 1.4) * (1.5 - skill)

	func _pick(k: Kart) -> Node3D:
		var best: Node3D = null
		var bd := INF
		if k.item == "":
			for e in k.track.get_children():
				if e is ItemEgg and (e as ItemEgg).visible_egg():
					var d := (e as Node3D).global_position.distance_to(k.global_position)
					if d < bd:
						bd = d
						best = e
			if best and bd < 40.0:
				return best
		bd = INF
		for o in k.race.karts:
			if o == k or o.out:
				continue
			var d: float = o.global_position.distance_to(k.global_position) * rng.randf_range(0.8, 1.2)
			if d < bd:
				bd = d
				best = o
		return best
