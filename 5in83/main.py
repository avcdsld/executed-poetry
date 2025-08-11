from machine import Pin
import utime
import time
from Pico_ePaper_5in83_B import EPD_5in83_B
import uhashlib as hashlib
import ubinascii
import ed25519

def make_exec_token(code, filename, next_count, dt_us, t_start_us, t_end_us):
    h_code = hashlib.sha256(code.encode('utf-8')).digest()
    meta = "{}|{}|{}|{}|{}".format(filename, next_count, dt_us, t_start_us, t_end_us).encode()
    h = hashlib.sha256(h_code + meta).digest()
    full_hex = ubinascii.hexlify(h).decode()
    short = full_hex[:8]
    return short, full_hex

def sign_execution(filename, count):
    private_key, _ = generate_ed25519_keypair_from_device()
    message = "{}{}".format(filename, count).encode()
    signature = ed25519.sign_hex(private_key, message)
    return signature

epd = EPD_5in83_B()
epd.init()
epd.Clear(0xFF, 0x00)

KEY0_PIN = 2
KEY1_PIN = 3

_key0_pressed = False
_key1_pressed = False
_last_irq_ms = 0

_current_idx = 2

def clamp_idx(i):
    if i < 1:  return 10
    if i > 10: return 1
    return i

def read_code(idx):
    fn = "{}.py".format(idx)
    try:
        with open(fn) as f:
            return f.read(), fn
    except:
        return "No code.", fn

def read_memory():
    global _current_idx
    try:
        with open("memory.dat") as f:
            content = f.read().strip()
            if not content:
                return init_default_memory()
            
            data = parse_memory_data(content)
            _current_idx = clamp_idx(data.get('current_file_idx', _current_idx))
            return data
    except:
        return init_default_memory()

def write_memory(memory_data):
    try:
        with open("memory.dat", "w") as f:
            f.write(format_memory_data(memory_data))
    except Exception as e:
        print("Memory write error:", e)

def generate_ed25519_keypair_from_device():
    from machine import unique_id
    seed = b"To define is to kill. To suggest is to create. "
    signing_key_bytes = hashlib.sha256(seed + unique_id()).digest()
    public_key_bytes = ed25519.create_public_key(signing_key_bytes)
    return (ubinascii.hexlify(signing_key_bytes).decode(),
            ubinascii.hexlify(public_key_bytes).decode())

def init_default_memory():
    return {
        'current_file_idx': _current_idx,
        'files': {}
    }

def parse_memory_data(content):
    data = init_default_memory()
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if key == 'current_file_idx':
                data['current_file_idx'] = int(value)
            elif key.startswith('file_'):
                filename = key[5:]
                file_info = parse_file_info(value)
                data['files'][filename] = file_info
    return data

def parse_file_info(value):
    info = {'count': 0, 'hash': ''}
    parts = value.split(',')
    for part in parts:
        part = part.strip()
        if '=' in part:
            k, v = part.split('=', 1)
            if k.strip() == 'count':
                info['count'] = int(v.strip())
            elif k.strip() == 'hash':
                info['hash'] = v.strip()
    return info

def format_memory_data(data):
    lines = [
        "current_file_idx: {}".format(data['current_file_idx'])
    ]
    if data['files']:
        for filename, info in data['files'].items():
            lines.append("file_{}: count={},hash={}".format(
                filename, info['count'], info['hash']
            ))
    return '\n'.join(lines)

def text_big(fb, s, x, y, c, scale=4):
    from framebuf import FrameBuffer, MONO_HLSB
    buf = bytearray(8*8//8)
    glyph = FrameBuffer(buf, 8, 8, MONO_HLSB)
    for i, ch in enumerate(s):
        glyph.fill(0xFF)
        glyph.text(ch, 0, 0, c)
        gx = x + i * 8 * scale
        for yy in range(8):
            for xx in range(8):
                if glyph.pixel(xx, yy) == 0:
                    X = gx + xx*scale
                    Y = y  + yy*scale
                    for dy in range(scale):
                        for dx in range(scale):
                            fb.pixel(X+dx, Y+dy, 0)

def display(code, count, duration_us, filename):
    epd.imageblack.fill(0xFF)
    epd.imagered.fill(0x00)

    body_scale   = 2 if filename == "9.py" else 3
    footer_scale = 1

    char_w      = 8 * body_scale
    char_h      = 8 * body_scale
    line_gap    = 6 * body_scale
    line_height = char_h + line_gap

    W, H = epd.width, epd.height

    footer_h = 12 * footer_scale * 4 + 8
    avail_h  = max(0, H - footer_h)

    raw_lines = code.splitlines()
    lines = [l.encode("ascii", "ignore").decode("ascii") for l in raw_lines]

    max_lines_fit = max(1, avail_h // line_height)
    max_chars_fit = max(1, W // char_w)

    display_lines = [l[:max_chars_fit] for l in lines][:max_lines_fit]

    n_lines   = len(display_lines)
    max_chars = max((len(l) for l in display_lines), default=0)
    block_w   = max_chars * char_w
    block_h   = n_lines * line_height if n_lines > 0 else 0

    left_margin = max(0, (W - block_w) // 2)

    top_margin = max(0, ((avail_h - block_h) // 2) - (line_height // 2) + 24)

    y = top_margin
    for line in display_lines:
        text_big(epd.imageblack, line, left_margin, y, 0x00, body_scale)
        y += line_height

    ms_time = duration_us / 1000.0
    _, public_key = generate_ed25519_keypair_from_device()
    ed25519_sig = sign_execution(filename, count)
    
    line1 = "run #{} | {:.3f}ms".format(count, ms_time)
    line2 = "pub {}".format(public_key)
    line3 = "sig {}".format(ed25519_sig[:64])
    line4 = "    {}".format(ed25519_sig[64:])
    
    footer_y = H - (12 * footer_scale * 4) - 8
    text_big(epd.imageblack, line1, 10, footer_y, 0x00, footer_scale)
    text_big(epd.imageblack, line2, 10, footer_y + 12 * footer_scale, 0x00, footer_scale)
    text_big(epd.imageblack, line3, 10, footer_y + 24 * footer_scale, 0x00, footer_scale)
    text_big(epd.imageblack, line4, 10, footer_y + 36 * footer_scale, 0x00, footer_scale)

    epd.display(epd.buffer_black, epd.buffer_red)

def _key0_irq(pin):
    global _key0_pressed, _last_irq_ms
    now = utime.ticks_ms()
    if utime.ticks_diff(now, _last_irq_ms) > 300:
        _key0_pressed = True
        _last_irq_ms = now

def _key1_irq(pin):
    global _key1_pressed, _last_irq_ms
    now = utime.ticks_ms()
    if utime.ticks_diff(now, _last_irq_ms) > 300:
        _key1_pressed = True
        _last_irq_ms = now

def run_and_render(code, memory_data, filename):
    t0 = utime.ticks_us()
    try:
        exec(code, globals())
    except Exception as e:
        print("Execution error:", e)
    t1 = utime.ticks_us()
    dt_us = utime.ticks_diff(t1, t0)

    if filename not in memory_data['files']:
        memory_data['files'][filename] = {'count': 0, 'hash': ''}
    
    current_count = memory_data['files'][filename]['count'] + 1
    memory_data['files'][filename]['count'] = current_count
    

    _, hash_full = make_exec_token(code, filename, current_count, dt_us, t0, t1)
    memory_data['files'][filename]['hash'] = hash_full

    memory_data['current_file_idx'] = _current_idx

    write_memory(memory_data)

    display(code, current_count, dt_us, filename)
    return memory_data

def ensure_memory_exists():
    try:
        with open("memory.dat", "r") as f:
            return True
    except:
        memory_data = init_default_memory()
        write_memory(memory_data)
        return False

def main_loop():
    global _current_idx, _key0_pressed, _key1_pressed

    ensure_memory_exists()
    memory_data = read_memory()
    _current_idx = memory_data['current_file_idx']
    
    code, filename = read_code(_current_idx)
    

    memory_data = run_and_render(code, memory_data, filename)

    key0 = Pin(KEY0_PIN, Pin.IN, Pin.PULL_UP)
    key1 = Pin(KEY1_PIN, Pin.IN, Pin.PULL_UP)
    key0.irq(trigger=Pin.IRQ_FALLING, handler=_key0_irq)
    key1.irq(trigger=Pin.IRQ_FALLING, handler=_key1_irq)

    while True:
        if _key0_pressed or _key1_pressed:
            if _key0_pressed:
                _current_idx = clamp_idx(_current_idx + 1)
                _key0_pressed = False
            if _key1_pressed:
                _current_idx = clamp_idx(_current_idx - 1)
                _key1_pressed = False
            code, filename = read_code(_current_idx)
            memory_data = run_and_render(code, memory_data, filename)
        utime.sleep_ms(20)

main_loop()
