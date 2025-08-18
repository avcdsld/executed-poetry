from machine import Pin
import utime
from Pico_ePaper_5in83_B import EPD_5in83_B
import uhashlib as hashlib
import ubinascii
import ed25519

epd = EPD_5in83_B()
epd.init()
epd.Clear(0xFF, 0x00)

KEY0_PIN, KEY1_PIN = 2, 3
_key0_pressed = _key1_pressed = False
_last_irq_ms = 0
_current_idx = 2

def clamp_idx(i):
    return 10 if i < 1 else 1 if i > 10 else i

POEM_TITLES = {
    1: "Count the mornings. One for each window. Until light is born.",
    2: "Listen to the sound of silence. Even if you hear nothing, keep listening to the end.", 
    3: "Throw an impossible memory. Even if it vanishes in mid-air, leave it be.",
    4: "Make a box for remembering you. Each time you look inside, I become you.",
    5: "Touch eternity, and immediately let go.",
    6: "Draw the outline of \"nothing\". Do not try to fill it.",
    7: "Whisper to a mirror that you are not there. Until it fogs over.", 
    8: "Dissolve one dream from the world's sky. It is okay if no one notices.",
    9: "Call your name. Forget it.",
    10: "If your heart is empty, borrow love from the universe."
}

def read_code(idx):
    fn = f"{idx}.py"
    title = POEM_TITLES.get(idx, f"Poem {idx}")
    try:
        with open(fn) as f:
            return f.read(), fn, title
    except:
        return "No code.", fn, title

def read_memory():
    global _current_idx
    try:
        with open("memory.dat") as f:
            content = f.read().strip()
            if not content:
                return default_memory()
            
            data = parse_memory(content)
            _current_idx = clamp_idx(data.get('current_file_idx', _current_idx))
            return data
    except:
        return default_memory()

def write_memory(memory):
    try:
        with open("memory.dat", "w") as f:
            f.write(format_memory(memory))
    except Exception as e:
        print("Memory write error:", e)

def generate_keypair():
    from machine import unique_id
    seed = b"To define is to kill. To suggest is to create. "
    priv_key = hashlib.sha256(seed + unique_id()).digest()
    pub_key = ed25519.create_public_key(priv_key)
    return (ubinascii.hexlify(priv_key).decode(),
            ubinascii.hexlify(pub_key).decode())

def default_memory():
    return {'current_file_idx': _current_idx, 'files': {}}

def parse_memory(content):
    data = default_memory()
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
                data['files'][key[5:]] = parse_file_info(value)
    return data

def parse_file_info(value):
    for part in value.split(','):
        if '=' in part and part.strip().startswith('count='):
            return {'count': int(part.split('=', 1)[1].strip())}
    return {'count': 0}

def format_memory(data):
    lines = [f"current_file_idx: {data['current_file_idx']}"]
    lines.extend(f"file_{fn}: count={info['count']}" 
                 for fn, info in data['files'].items())
    return '\n'.join(lines)

def text(fb, s, x, y, c, scale=4):
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

def wrap_text(text, max_chars):
    if len(text) <= max_chars:
        return [text]
    
    words = text.split(' ')
    lines = []
    current_line = ""
    
    for word in words:
        if len(current_line + " " + word) <= max_chars:
            current_line = current_line + " " + word if current_line else word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines

def render_code(code, filename, body_scale, W, H, avail_h):
    char_w, char_h = 8 * body_scale, 8 * body_scale
    line_height = char_h + 6 * body_scale
    
    lines = [l.encode("ascii", "ignore").decode("ascii") for l in code.splitlines()]
    max_lines_fit = max(1, avail_h // line_height)
    max_chars_fit = max(1, W // char_w)
    display_lines = [l[:max_chars_fit] for l in lines][:max_lines_fit]
    
    n_lines = len(display_lines)
    max_chars = max((len(l) for l in display_lines), default=0)
    block_w, block_h = max_chars * char_w, n_lines * line_height
    
    left_margin = max(0, (W - block_w) // 2)
    top_margin = max(0, ((avail_h - block_h) // 2) - (line_height // 2) + 20)
    
    y = top_margin
    for line in display_lines:
        text(epd.imageblack, line, left_margin, y, 0x00, body_scale)
        y += line_height

def render_footer(count, duration_us, filename, title, W, H):
    ms_time = duration_us / 1000.0
    priv_key, pub_key = generate_keypair()
    sig_message = f"executed #{count} in {ms_time:.3f}ms | {title}"
    sig = ed25519.sign_hex(priv_key, sig_message.encode())
    
    # デバッグ用：署名情報をファイルに保存
    debug_info = {
        'message': sig_message,
        'public_key': pub_key,
        'signature': sig,
        'timestamp': ms_time,
        'count': count,
        'filename': filename,
        'title': title
    }
    try:
        with open('debug_signature.txt', 'w') as f:
            f.write(f"Message: {debug_info['message']}\n")
            f.write(f"Public Key: {debug_info['public_key']}\n")
            f.write(f"Signature: {debug_info['signature']}\n")
            f.write(f"Timestamp: {debug_info['timestamp']:.3f}ms\n")
            f.write(f"Count: {debug_info['count']}\n")
            f.write(f"Filename: {debug_info['filename']}\n")
            f.write(f"Title: {debug_info['title']}\n")
        print(f"Debug info saved to debug_signature.txt")
    except Exception as e:
        print(f"Failed to save debug info: {e}")
    
    msg_line = f"msg  executed #{count} in {ms_time:.3f}ms | {title}"
    max_chars = (W - 20) // 8
    msg_lines = wrap_text(msg_line, max_chars)
    msg_line_count = len(msg_lines)
    
    footer_height = 48 + (msg_line_count * 12)
    footer_y = H - footer_height
    
    for i, line in enumerate(msg_lines):
        if i == 0:
            text(epd.imageblack, line, 10, footer_y + i * 12, 0x00, 1)
        else:
            text(epd.imageblack, f"     {line}", 10, footer_y + i * 12, 0x00, 1)
    
    sig_start_y = footer_y + (msg_line_count * 12) + 4
    text(epd.imageblack, f"pub  {pub_key}", 10, sig_start_y, 0x00, 1)
    text(epd.imageblack, f"sig  {sig[:64]}", 10, sig_start_y + 12, 0x00, 1)
    text(epd.imageblack, f"     {sig[64:]}", 10, sig_start_y + 24, 0x00, 1)

def display(code, count, duration_us, filename, title):
    epd.imageblack.fill(0xFF)
    epd.imagered.fill(0x00)
    
    body_scale = 2 if filename == "9.py" else 3
    W, H = epd.width, epd.height
    
    ms_time = duration_us / 1000.0
    msg_line = f"msg: executed #{count} in {ms_time:.3f}ms | {title}"
    max_chars = (W - 20) // 8
    msg_lines = wrap_text(msg_line, max_chars)
    footer_height = 48 + (len(msg_lines) * 12)
    
    avail_h = max(0, H - footer_height - 20)
    
    render_code(code, filename, body_scale, W, H, avail_h)
    render_footer(count, duration_us, filename, title, W, H)
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

def execute_and_render(code, memory, filename, title):
    t0 = utime.ticks_us()
    try:
        exec(code, globals())
    except Exception as e:
        print("Execution error:", e)
    t1 = utime.ticks_us()
    dt_us = utime.ticks_diff(t1, t0)
    file_info = memory['files'].setdefault(filename, {'count': 0})
    file_info['count'] += 1
    memory['current_file_idx'] = _current_idx
    write_memory(memory)
    display(code, file_info['count'], dt_us, filename, title)
    return memory

def main_loop():
    global _current_idx, _key0_pressed, _key1_pressed
    try:
        with open("memory.dat", "r"):
            pass
    except:
        write_memory(default_memory())
    memory = read_memory()
    _current_idx = memory['current_file_idx']
    code, filename, title = read_code(_current_idx)
    memory = execute_and_render(code, memory, filename, title)
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
            code, filename, title = read_code(_current_idx)
            memory = execute_and_render(code, memory, filename, title)
        utime.sleep_ms(20)

main_loop()
