# Minimal Ed25519 implementation for MicroPython
# Extracted and adapted from https://github.com/warner/python-pure25519
# - Adds SHA-512 fallback (one-shot) for MicroPython
# - Replaces b[::-1] with bytes(reversed(b)) compatibility helper

try:
    import uhashlib as hashlib
except ImportError:
    import hashlib

try:
    import ubinascii as binascii
except ImportError:
    import binascii

try:
    import urandom
    def _urandom(n):
        return urandom.getrandbits(n*8).to_bytes(n, 'big')
except ImportError:
    try:
        import os
        _urandom = os.urandom
    except ImportError:
        import time
        def _urandom(n):
            t = int(time.ticks_us())
            result = []
            for i in range(n):
                t = (t * 1664525 + 1013904223) % (2**32)
                result.append(t & 0xFF)
            return bytes(result)

# ---- compatibility: reverse bytes without b[::-1] (MicroPython safe)
def _rev(b):
    return bytes(reversed(b))

Q = 2**255 - 19
L = 2**252 + 27742317777372353535851937790883648493

def _inv(x):
    return pow(x, Q-2, Q)

d = -121665 * _inv(121666)
I = pow(2, (Q-1)//4, Q)

def _xrecover(y):
    xx = (y*y-1) * _inv(d*y*y+1)
    x = pow(xx, (Q+3)//8, Q)
    if (x*x - xx) % Q != 0:
        x = (x*I) % Q
    if x % 2 != 0:
        x = Q-x
    return x

By = 4 * _inv(5)
Bx = _xrecover(By)
B = [Bx % Q, By % Q]

def _xform_affine_to_extended(pt):
    (x, y) = pt
    return (x%Q, y%Q, 1, (x*y)%Q)

def _xform_extended_to_affine(pt):
    (x, y, z, _) = pt
    return ((x*_inv(z))%Q, (y*_inv(z))%Q)

def _double_element(pt):
    (X1, Y1, Z1, _) = pt
    A = (X1*X1)
    Bv = (Y1*Y1)
    C = (2*Z1*Z1)
    D = (-A) % Q
    J = (X1+Y1) % Q
    E = (J*J-A-Bv) % Q
    G = (D+Bv) % Q
    F = (G-C) % Q
    H = (D-Bv) % Q
    X3 = (E*F) % Q
    Y3 = (G*H) % Q
    Z3 = (F*G) % Q
    T3 = (E*H) % Q
    return (X3, Y3, Z3, T3)

def _add_elements(pt1, pt2):
    (X1, Y1, Z1, T1) = pt1
    (X2, Y2, Z2, T2) = pt2
    A = ((Y1-X1)*(Y2+X2)) % Q
    Bv = ((Y1+X1)*(Y2-X2)) % Q
    C = (Z1*2*T2) % Q
    D = (T1*2*Z2) % Q
    E = (D+C) % Q
    F = (Bv-A) % Q
    G = (Bv+A) % Q
    H = (D-C) % Q
    X3 = (E*F) % Q
    Y3 = (G*H) % Q
    Z3 = (F*G) % Q
    T3 = (E*H) % Q
    return (X3, Y3, Z3, T3)

def _scalarmult_element(pt, n):
    if n == 0:
        return _xform_affine_to_extended((0, 1))

    R = _xform_affine_to_extended((0, 1))
    Q = pt
    while n > 0:
        if n & 1:
            R = _add_elements(R, Q)
        Q = _double_element(Q)
        n >>= 1
    return R

def _encodepoint(P):
    x = P[0]
    y = P[1]
    if x & 1:
        y += 1<<255
    return _rev(binascii.unhexlify("%064x" % y))

def _bytes_to_scalar(s):
    return int(binascii.hexlify(_rev(s)), 16)

def _bytes_to_clamped_scalar(s):
    a_unclamped = _bytes_to_scalar(s)
    # Standard Ed25519 clamp:
    # clear lowest 3 bits, clear highest bit, set second-highest bit
    AND_CLAMP = (1<<254) - 1 - 7
    OR_CLAMP  = (1<<254)
    a_clamped = (a_unclamped & AND_CLAMP) | OR_CLAMP
    return a_clamped

def _scalar_to_bytes(y):
    y = y % L
    return _rev(binascii.unhexlify("%064x" % y))

# --- SHA-512 fallback for MicroPython (one-shot) ---
try:
    _has_sha512 = hasattr(hashlib, "sha512")
except:
    _has_sha512 = False

if not _has_sha512:
    import struct
    _K = [
        0x428a2f98d728ae22,0x7137449123ef65cd,0xb5c0fbcfec4d3b2f,0xe9b5dba58189dbbc,
        0x3956c25bf348b538,0x59f111f1b605d019,0x923f82a4af194f9b,0xab1c5ed5da6d8118,
        0xd807aa98a3030242,0x12835b0145706fbe,0x243185be4ee4b28c,0x550c7dc3d5ffb4e2,
        0x72be5d74f27b896f,0x80deb1fe3b1696b1,0x9bdc06a725c71235,0xc19bf174cf692694,
        0xe49b69c19ef14ad2,0xefbe4786384f25e3,0x0fc19dc68b8cd5b5,0x240ca1cc77ac9c65,
        0x2de92c6f592b0275,0x4a7484aa6ea6e483,0x5cb0a9dcbd41fbd4,0x76f988da831153b5,
        0x983e5152ee66dfab,0xa831c66d2db43210,0xb00327c898fb213f,0xbf597fc7beef0ee4,
        0xc6e00bf33da88fc2,0xd5a79147930aa725,0x06ca6351e003826f,0x142929670a0e6e70,
        0x27b70a8546d22ffc,0x2e1b21385c26c926,0x4d2c6dfc5ac42aed,0x53380d139d95b3df,
        0x650a73548baf63de,0x766a0abb3c77b2a8,0x81c2c92e47edaee6,0x92722c851482353b,
        0xa2bfe8a14cf10364,0xa81a664bbc423001,0xc24b8b70d0f89791,0xc76c51a30654be30,
        0xd192e819d6ef5218,0xd69906245565a910,0xf40e35855771202a,0x106aa07032bbd1b8,
        0x19a4c116b8d2d0c8,0x1e376c085141ab53,0x2748774cdf8eeb99,0x34b0bcb5e19b48a8,
        0x391c0cb3c5c95a63,0x4ed8aa4ae3418acb,0x5b9cca4f7763e373,0x682e6ff3d6b2b8a3,
        0x748f82ee5defb2fc,0x78a5636f43172f60,0x84c87814a1f0ab72,0x8cc702081a6439ec,
        0x90befffa23631e28,0xa4506cebde82bde9,0xbef9a3f7b2c67915,0xc67178f2e372532b,
        0xca273eceea26619c,0xd186b8c721c0c207,0xeada7dd6cde0eb1e,0xf57d4f7fee6ed178,
        0x06f067aa72176fba,0x0a637dc5a2c898a6,0x113f9804bef90dae,0x1b710b35131c471b,
        0x28db77f523047d84,0x32caab7b40c72493,0x3c9ebe0a15c9bebc,0x431d67c49c100d4c,
        0x4cc5d4becb3e42b6,0x597f299cfc657e2a,0x5fcb6fab3ad6faec,0x6c44198c4a475817
    ]
    def _rotr(x,n): return ((x>>n)|(x<<(64-n))) & 0xffffffffffffffff
    def _shr(x,n):  return x>>n
    def _Ch(x,y,z): return (x & y) ^ (~x & z)
    def _Maj(x,y,z): return (x & y) ^ (x & z) ^ (y & z)
    def _BSIG0(x): return _rotr(x,28) ^ _rotr(x,34) ^ _rotr(x,39)
    def _BSIG1(x): return _rotr(x,14) ^ _rotr(x,18) ^ _rotr(x,41)
    def _SSIG0(x): return _rotr(x,1) ^ _rotr(x,8) ^ _shr(x,7)
    def _SSIG1(x): return _rotr(x,19) ^ _rotr(x,61) ^ _shr(x,6)

    def _sha512_one_shot(msg):
        if isinstance(msg, str):
            msg = msg.encode("utf-8")
        ml = len(msg) * 8
        msg += b"\x80"
        while ((len(msg) + 16) % 128) != 0:
            msg += b"\x00"
        import struct as _struct  # local alias for speed
        msg += _struct.pack(">QQ", (ml >> 64) & 0xffffffffffffffff, ml & 0xffffffffffffffff)

        H = [
            0x6a09e667f3bcc908,0xbb67ae8584caa73b,0x3c6ef372fe94f82b,0xa54ff53a5f1d36f1,
            0x510e527fade682d1,0x9b05688c2b3e6c1f,0x1f83d9abfb41bd6b,0x5be0cd19137e2179
        ]
        for i in range(0, len(msg), 128):
            W = list(_struct.unpack(">16Q", msg[i:i+128]))
            for t in range(16, 80):
                W.append((_SSIG1(W[t-2]) + W[t-7] + _SSIG0(W[t-15]) + W[t-16]) & 0xffffffffffffffff)
            a,b,c,d,e,f,g,h = H
            for t in range(80):
                T1 = (h + _BSIG1(e) + _Ch(e,f,g) + _K[t] + W[t]) & 0xffffffffffffffff
                T2 = (_BSIG0(a) + _Maj(a,b,c)) & 0xffffffffffffffff
                h,g,f,e,d,c,b,a = g,f,e,(d + T1) & 0xffffffffffffffff,c,b,a,(T1 + T2) & 0xffffffffffffffff
            H = [(H[0]+a)&0xffffffffffffffff,(H[1]+b)&0xffffffffffffffff,(H[2]+c)&0xffffffffffffffff,
                 (H[3]+d)&0xffffffffffffffff,(H[4]+e)&0xffffffffffffffff,(H[5]+f)&0xffffffffffffffff,
                 (H[6]+g)&0xffffffffffffffff,(H[7]+h)&0xffffffffffffffff]
        return _struct.pack(">8Q", *H)

    def _sha512_digest_once(m):
        return _sha512_one_shot(m)
# --- end fallback ---

def _H(m):
    if hasattr(hashlib, "sha512"):
        return hashlib.sha512(m).digest()
    else:
        return _sha512_digest_once(m)

def _Hint(m):
    h = _H(m)
    return int(binascii.hexlify(_rev(h)), 16)

def create_private_key():
    return _urandom(32)

def create_public_key(priv_key):
    if len(priv_key) != 32:
        raise ValueError("priv_key must be 32 bytes")
    h = _H(priv_key)
    a = _bytes_to_clamped_scalar(h[:32])
    A_pt = _scalarmult_element(_xform_affine_to_extended(B), a)
    A_affine = _xform_extended_to_affine(A_pt)
    return _encodepoint(A_affine)

def sign(priv_key, message):
    if len(priv_key) != 32:
        raise ValueError("priv_key must be 32 bytes")
    if isinstance(message, str):
        message = message.encode('utf-8')

    pub_key = create_public_key(priv_key)

    h = _H(priv_key)
    a_bytes, inter = h[:32], h[32:]
    a = _bytes_to_clamped_scalar(a_bytes)

    r = _Hint(inter + message)
    R_pt = _scalarmult_element(_xform_affine_to_extended(B), r)
    R_affine = _xform_extended_to_affine(R_pt)
    R_bytes = _encodepoint(R_affine)

    S = r + _Hint(R_bytes + pub_key + message) * a
    return R_bytes + _scalar_to_bytes(S)

def sign_hex(priv_key_hex, message):
    priv_key = binascii.unhexlify(priv_key_hex)
    return binascii.hexlify(sign(priv_key, message)).decode()
