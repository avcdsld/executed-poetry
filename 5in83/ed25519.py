# Minimal Ed25519 implementation for MicroPython
# Extracted and optimized from https://github.com/warner/python-pure25519

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
    B = (Y1*Y1)
    C = (2*Z1*Z1)
    D = (-A) % Q
    J = (X1+Y1) % Q
    E = (J*J-A-B) % Q
    G = (D+B) % Q
    F = (G-C) % Q
    H = (D-B) % Q
    X3 = (E*F) % Q
    Y3 = (G*H) % Q
    Z3 = (F*G) % Q
    T3 = (E*H) % Q
    return (X3, Y3, Z3, T3)

def _add_elements(pt1, pt2):
    (X1, Y1, Z1, T1) = pt1
    (X2, Y2, Z2, T2) = pt2
    A = ((Y1-X1)*(Y2+X2)) % Q
    B = ((Y1+X1)*(Y2-X2)) % Q
    C = (Z1*2*T2) % Q
    D = (T1*2*Z2) % Q
    E = (D+C) % Q
    F = (B-A) % Q
    G = (B+A) % Q
    H = (D-C) % Q
    X3 = (E*F) % Q
    Y3 = (G*H) % Q
    Z3 = (F*G) % Q
    T3 = (E*H) % Q
    return (X3, Y3, Z3, T3)

def _scalarmult_element(pt, n):
    if n == 0:
        return _xform_affine_to_extended((0,1))
    _ = _double_element(_scalarmult_element(pt, n>>1))
    return _add_elements(_, pt) if n&1 else _

def _encodepoint(P):
    x = P[0]
    y = P[1]
    if x & 1:
        y += 1<<255
    return binascii.unhexlify("%064x" % y)[::-1]

def _bytes_to_scalar(s):
    return int(binascii.hexlify(s[::-1]), 16)

def _bytes_to_clamped_scalar(s):
    a_unclamped = _bytes_to_scalar(s)
    AND_CLAMP = (1<<254) - 1 - 7
    OR_CLAMP = (1<<254)
    a_clamped = (a_unclamped & AND_CLAMP) | OR_CLAMP
    return a_clamped

def _scalar_to_bytes(y):
    y = y % L
    return binascii.unhexlify("%064x" % y)[::-1]

def _H(m):
    return hashlib.sha512(m).digest()

def _Hint(m):
    h = _H(m)
    return int(binascii.hexlify(h[::-1]), 16)

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
