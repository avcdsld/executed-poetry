from machine import Pin
import utime
import time
from Pico_ePaper_5in83_B import EPD_5in83_B

try:
    import uhashlib as hashlib
except ImportError:
    import hashlib
import ubinascii

def make_exec_token(code, filename, next_count, dt_us, t_start_us, t_end_us):
    h_code = hashlib.sha256(code.encode('utf-8')).digest()
    meta = "{}|{}|{}|{}|{}".format(filename, next_count, dt_us, t_start_us, t_end_us).encode()
    h = hashlib.sha256(h_code + meta).digest()
    full_hex = ubinascii.hexlify(h).decode()
    short = full_hex[:8]
    return short, full_hex

epd = EPD_5in83_B()
epd.init()
epd.Clear(0xFF, 0x00)

KEY0_PIN = 2  # User Key 0
KEY1_PIN = 3  # User Key 1

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

def read_meta():
    global _current_idx
    try:
        with open("meta.txt") as f:
            lines = [x.strip() for x in f.readlines()]
            count = int(lines[0]) if len(lines) > 0 else 0
            idx = int(lines[1]) if len(lines) > 1 else _current_idx
            _current_idx = clamp_idx(idx)
            return count, _current_idx
    except:
        return 0, _current_idx

def write_meta(count, idx):
    with open("meta.txt", "w") as f:
        f.write("{}\n{}\n".format(count, idx))

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

def display(code, count, duration_us, filename, sig_short=""):
    epd.imageblack.fill(0xFF)
    epd.imagered.fill(0x00)

    body_scale   = 2 if filename == "9.py" else 3
    footer_scale = 2

    char_w      = 8 * body_scale       # 1文字の幅
    char_h      = 8 * body_scale       # 1文字の高さ
    line_gap    = 6 * body_scale       # 行間
    line_height = char_h + line_gap    # 実効行高

    W, H = epd.width, epd.height

    footer_h = 12 * footer_scale + 4
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
    footer_str = "run #{} | time {:.3f}ms | {} {}".format(count, ms_time, sig_short, filename)
    fy = H - (12 * footer_scale) - 4
    text_big(epd.imageblack, footer_str, 10, fy, 0x00, footer_scale)

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

def run_and_render(code, count, filename):
    t0 = utime.ticks_us()
    try:
        exec(code, globals())
    except Exception as e:
        print("Execution error:", e)
    t1 = utime.ticks_us()
    dt_us = utime.ticks_diff(t1, t0)

    sig_short, sig_full = make_exec_token(code, filename, count+1, dt_us, t0, t1)

    count += 1
    write_meta(count, _current_idx)
    try:
        with open("meta.txt", "a") as f:
            f.write("sig:{}\n".format(sig_full))
    except:
        pass

    display(code, count, dt_us, filename, sig_short)
    return count

def main_loop():
    global _current_idx, _key0_pressed, _key1_pressed

    count, _current_idx = read_meta()
    code, filename = read_code(_current_idx)

    count = run_and_render(code, count, filename)

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
            count = run_and_render(code, count, filename)
        utime.sleep_ms(20)

main_loop()
