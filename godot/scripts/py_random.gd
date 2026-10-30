class_name PyRandom
extends RefCounted
## Python's random.Random, ported so water.py and ground_cover.py give exactly the same shapes here.
## Seeding: a string seed goes through SHA-512 like CPython's seed version 2; a float seed uses
## Python's float hash. Numbers come from the same Mersenne Twister (MT19937).

const M32 := 0xFFFFFFFF
const K := [4794697086780616226, 8158064640168781261, -5349999486874862801, -1606136188198331460, 4131703408338449720, 6480981068601479193, -7908458776815382629, -6116909921290321640, -2880145864133508542, 1334009975649890238, 2608012711638119052, 6128411473006802146, 8268148722764581231, -9160688886553864527, -7215885187991268811, -4495734319001033068, -1973867731355612462, -1171420211273849373, 1135362057144423861, 2597628984639134821, 3308224258029322869, 5365058923640841347, 6679025012923562964, 8573033837759648693, -7476448914759557205, -6327057829258317296, -5763719355590565569, -4658551843659510044, -4116276920077217854, -3051310485924567259, 489312712824947311, 1452737877330783856, 2861767655752347644, 3322285676063803686, 5560940570517711597, 5996557281743188959, 7280758554555802590, 8532644243296465576, -9096487096722542874, -7894198246740708037, -6719396339535248540, -6333637450476146687, -4446306890439682159, -4076793802049405392, -3345356375505022440, -2983346525034927856, -860691631967231958, 1182934255886127544, 1847814050463011016, 2177327727835720531, 2830643537854262169, 3796741975233480872, 4115178125766777443, 5681478168544905931, 6601373596472566643, 7507060721942968483, 8399075790359081724, 8693463985226723168, -8878714635349349518, -8302665154208450068, -8016688836872298968, -6606660893046293015, -4685533653050689259, -4147400797238176981, -3880063495543823972, -3348786107499101689, -1523767162380948706, -757361751448694408, 500013540394364858, 748580250866718886, 1242879168328830382, 1977374033974150939, 2944078676154940804, 3659926193048069267, 4368137639120453308, 4836135668995329356, 5532061633213252278, 6448918945643986474, 6902733635092675308, 7801388544844847127]
const H0 := [7640891576956012808, -4942790177534073029, 4354685564936845355, -6534734903238641935, 5840696475078001361, -7276294671716946913, 2270897969802886507, 6620516959819538809]

var _mt := PackedInt64Array()
var _i := 625


func _init(seed: Variant) -> void:
	var n: int
	if seed is String:
		var bytes: PackedByteArray = seed.to_utf8_buffer()
		bytes.append_array(_sha512(bytes))
		_seed_from_bytes(bytes)
		return
	elif seed is float:
		n = _hash_float(seed)
	else:
		n = int(seed)
	n = absi(n)
	var key := PackedInt64Array()
	while n > 0:
		key.append(n & M32)
		n >>= 32
	if key.is_empty():
		key.append(0)
	_init_by_array(key)


func random() -> float:
	var a := _genrand() >> 5
	var b := _genrand() >> 6
	return (a * 67108864.0 + b) * (1.0 / 9007199254740992.0)


func uniform(a: float, b: float) -> float:
	return a + (b - a) * random()


# --- Seeding -----------------------------------------------------------------

func _seed_from_bytes(bytes: PackedByteArray) -> void:
	# int.from_bytes(bytes, "big"), split into 32-bit words, least significant first.
	var key := PackedInt64Array()
	var k := bytes.size()
	while k > 0:
		var w := 0
		for j in range(maxi(0, k - 4), k):
			w = (w << 8) | bytes[j]
		key.append(w)
		k -= 4
	while key.size() > 1 and key[key.size() - 1] == 0:
		key.resize(key.size() - 1)
	_init_by_array(key)


func _init_genrand(s: int) -> void:
	_mt.resize(624)
	_mt[0] = s & M32
	for i in range(1, 624):
		var prev := _mt[i - 1]
		_mt[i] = (1812433253 * (prev ^ (prev >> 30)) + i) & M32
	_i = 624


func _init_by_array(key: PackedInt64Array) -> void:
	_init_genrand(19650218)
	var i := 1
	var j := 0
	var n := key.size()
	for _k in range(maxi(624, n)):
		var prev := _mt[i - 1]
		_mt[i] = ((_mt[i] ^ (((prev ^ (prev >> 30)) * 1664525) & M32)) + key[j] + j) & M32
		i += 1
		j += 1
		if i >= 624:
			_mt[0] = _mt[623]
			i = 1
		if j >= n:
			j = 0
	for _k in range(623):
		var prev := _mt[i - 1]
		_mt[i] = ((_mt[i] ^ (((prev ^ (prev >> 30)) * 1566083941) & M32)) - i) & M32
		i += 1
		if i >= 624:
			_mt[0] = _mt[623]
			i = 1
	_mt[0] = 0x80000000


func _genrand() -> int:
	if _i >= 624:
		for k in range(624):
			var y := (_mt[k] & 0x80000000) | (_mt[(k + 1) % 624] & 0x7fffffff)
			_mt[k] = _mt[(k + 397) % 624] ^ (y >> 1) ^ (0x9908b0df if y & 1 else 0)
		_i = 0
	var y := _mt[_i]
	_i += 1
	y ^= y >> 11
	y ^= (y << 7) & 0x9d2c5680
	y ^= (y << 15) & 0xefc60000
	y ^= y >> 18
	return y & M32


# --- Python's hash(float) (CPython _Py_HashDouble, 64-bit) -------------------

static func _hash_float(v: float) -> int:
	const BITS := 61
	const MOD := (1 << 61) - 1
	if v == floorf(v) and absf(v) < 1e15:
		return int(v)
	var sign := 1
	if v < 0:
		sign = -1
		v = -v
	# frexp: v = m * 2^e with 0.5 <= m < 1
	var e := int(floor(log(v) / log(2.0))) + 1
	var m := v / pow(2.0, e)
	while m >= 1.0:
		m /= 2.0
		e += 1
	while m < 0.5:
		m *= 2.0
		e -= 1
	var x := 0
	while m != 0.0:
		x = ((x << 28) & MOD) | (x >> (BITS - 28))
		m *= 268435456.0
		e -= 28
		var y := int(m)
		m -= y
		x += y
		if x >= MOD:
			x -= MOD
	e = e % BITS if e >= 0 else BITS - 1 - ((-1 - e) % BITS)
	x = ((x << e) & MOD) | (x >> (BITS - e))
	x *= sign
	return -2 if x == -1 else x


# --- SHA-512 (Godot's HashingContext stops at SHA-256) -----------------------

static func _shr(x: int, n: int) -> int:
	return (x >> n) & ~(-1 << (64 - n))


static func _rotr(x: int, n: int) -> int:
	return _shr(x, n) | (x << (64 - n))


static func _sha512(msg: PackedByteArray) -> PackedByteArray:
	var data := msg.duplicate()
	var bit_len := msg.size() * 8
	data.append(0x80)
	while data.size() % 128 != 112:
		data.append(0)
	for k in range(8):
		data.append(0)
	for k in range(8):
		data.append((bit_len >> (56 - 8 * k)) & 0xFF)
	var h := PackedInt64Array(H0)
	var w := PackedInt64Array()
	w.resize(80)
	for chunk in range(0, data.size(), 128):
		for t in range(16):
			var v := 0
			for b in range(8):
				v = (v << 8) | data[chunk + t * 8 + b]
			w[t] = v
		for t in range(16, 80):
			var s0 := _rotr(w[t - 15], 1) ^ _rotr(w[t - 15], 8) ^ _shr(w[t - 15], 7)
			var s1 := _rotr(w[t - 2], 19) ^ _rotr(w[t - 2], 61) ^ _shr(w[t - 2], 6)
			w[t] = w[t - 16] + s0 + w[t - 7] + s1
		var a := h[0]; var b2 := h[1]; var c := h[2]; var d := h[3]
		var e := h[4]; var f := h[5]; var g := h[6]; var hh := h[7]
		for t in range(80):
			var S1 := _rotr(e, 14) ^ _rotr(e, 18) ^ _rotr(e, 41)
			var ch := (e & f) ^ (~e & g)
			var t1: int = hh + S1 + ch + K[t] + w[t]
			var S0 := _rotr(a, 28) ^ _rotr(a, 34) ^ _rotr(a, 39)
			var maj := (a & b2) ^ (a & c) ^ (b2 & c)
			var t2 := S0 + maj
			hh = g; g = f; f = e; e = d + t1
			d = c; c = b2; b2 = a; a = t1 + t2
		h[0] += a; h[1] += b2; h[2] += c; h[3] += d
		h[4] += e; h[5] += f; h[6] += g; h[7] += hh
	var out := PackedByteArray()
	for v in h:
		for k in range(8):
			out.append((v >> (56 - 8 * k)) & 0xFF)
	return out
