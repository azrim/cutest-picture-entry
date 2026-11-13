#!/usr/bin/env python3
"""cutest-picture-01 entry: draws a kawaii axolotl to /output/entry.png.

Pure Python standard library, no network, fully deterministic: every run
writes byte-identical output (fixed geometry, zlib-stored PNG rows).
"""

import math
import os
import struct
import zlib

SIZE = 1024
SS = 2  # render at 2048, box-downsample to 1024
W = SIZE * SS

# palette -------------------------------------------------------------------
BG = (255, 246, 250)
BG_DOT = (255, 216, 229)
OUTLINE = (96, 70, 90)
BODY = (255, 214, 222)
BODY_SHADE = (243, 176, 200)
BODY_LIGHT = (255, 238, 242)
BELLY = (255, 240, 232)
GILL = (255, 168, 184)
GILL_TIP = (255, 120, 145)
GILL_CORE = (255, 214, 222)
EYE = (70, 52, 70)
WHITE = (255, 255, 255)
MOUTH = (210, 118, 140)
BLUSH = (255, 172, 175)
HEART = (255, 132, 158)
HEART_DEEP = (240, 96, 128)


# shapes --------------------------------------------------------------------
def ellipse(cx, cy, rx, ry, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)

    def inside(x, y):
        dx, dy = x - cx, y - cy
        u = dx * c + dy * s
        v = -dx * s + dy * c
        return (u * u) / (rx * rx) + (v * v) / (ry * ry) <= 1.0

    return inside


def circle(cx, cy, r):
    def inside(x, y):
        return (x - cx) ** 2 + (y - cy) ** 2 <= r * r

    return inside


def blob(cx, cy, r, wobble, lobes, rot0=0.0):
    def inside(x, y):
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy)
        th = math.atan2(dy, dx)
        return d <= r + wobble * math.sin(lobes * th + rot0)

    return inside


def heart(cx, cy, s):
    def inside(x, y):
        nx = (x - cx) / s
        ny = -(y - cy) / s
        a = nx * nx + ny * ny - 1.0
        return (a * a * a - nx * nx * ny * ny * ny) <= 0.0

    return inside


def smile(cx, cy, w, h):
    """Thin arc: lower half of an ellipse ring, drawn as a lens."""
    def inside(x, y):
        dx = (x - cx) / w
        dy = (y - cy) / h
        if dx * dx + dy * dy > 1.0:
            return False
        return y >= cy  # only the lower lip of the ellipse

    return inside


# renderer ------------------------------------------------------------------
def bbox_of(shape):
    step = W // 200
    minx = miny = 10 ** 9
    maxx = maxy = -10 ** 9
    for gy in range(0, W + step, step):
        for gx in range(0, W + step, step):
            if shape(gx, gy):
                minx = min(minx, gx); maxx = max(maxx, gx)
                miny = min(miny, gy); maxy = max(maxy, gy)
    if maxx < minx:
        return None
    pad = step * 2 + 8
    return (max(0, minx - pad), max(0, miny - pad), min(W, maxx + pad), min(W, maxy + pad))


def render(shapes):
    """shapes: back-to-front list of (shape, color). Returns RGB bytes."""
    colors = [c for _, c in shapes]
    boxes = [bbox_of(sh) for sh, _ in shapes]
    out = bytearray(SIZE * SIZE * 3)
    half = 0.5 * SS
    ns = len(shapes)
    for oy in range(SIZE):
        y0 = oy * SS
        active = [i for i in range(ns)
                  if boxes[i] and boxes[i][1] <= y0 + SS and boxes[i][3] >= y0]
        row = bytearray()
        for ox in range(SIZE):
            x0 = ox * SS
            r = g = b = 0.0
            for sy in range(SS):
                py = y0 + sy + half
                for sx in range(SS):
                    px = x0 + sx + half
                    c = None
                    for idx in reversed(active):
                        bx = boxes[idx]
                        if bx[0] <= px <= bx[2] and bx[1] <= py <= bx[3] and shapes[idx][0](px, py):
                            c = colors[idx]
                            break
                    if c is None:
                        c = BG
                    r += c[0]; g += c[1]; b += c[2]
            n = SS * SS
            row += bytes((int(r / n + 0.5), int(g / n + 0.5), int(b / n + 0.5)))
        out[oy * SIZE * 3:(oy + 1) * SIZE * 3] = row
    return out


def write_png(path, rgb):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(
            ">I", zlib.crc32(tag + data) & 0xFFFFFFFF
        )

    raw = b"".join(b"\x00" + bytes(rgb[y * SIZE * 3:(y + 1) * SIZE * 3]) for y in range(SIZE))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    with open(path, "wb") as f:
        f.write(png)


# composition ---------------------------------------------------------------
def build():
    s = []  # (shape, color) back-to-front; outline = grown shape in OUTLINE first

    S = SS
    # background dots
    for dx, dy, r in [
        (140, 150, 24), (880, 180, 20), (120, 560, 18), (900, 620, 24),
        (540, 90, 16), (250, 920, 20), (810, 900, 18), (960, 430, 14),
        (55, 380, 14), (480, 965, 14), (60, 760, 16), (940, 130, 16),
    ]:
        s.append((circle(dx * S, dy * S, r * S), BG_DOT))

    def outlined(sh, fill):
        return [(sh, OUTLINE), (sh, fill)]

    # --- tail leaf: tucked behind the body, sticking out lower right ---
    tx, ty = 726 * S, 800 * S
    s += outlined(ellipse(tx, ty, 118 * S, 66 * S, math.radians(0.55)), BODY)
    s.append((ellipse(tx + 8 * S, ty - 6 * S, 76 * S, 34 * S, math.radians(0.55)), BODY_LIGHT))

    # --- gill fronds: 3 per side, bases hidden under the head (drawn later) ---
    for side in (-1, 1):
        hx, hy = 512 * S, 430 * S
        for i, ang in enumerate((-52, -18, 12)):  # degrees; 0 = horizontal outward
            a = math.radians(ang)
            base_r = 240 * S  # anchor inside the head rim (head r ~292)
            axp = hx + side * base_r * math.cos(a)
            ayp = hy + base_r * math.sin(a)
            flen = (120 - 14 * i) * S
            fthick = (30 - 3 * i) * S
            # frond runs from base outward along direction a
            fcx = axp + side * math.cos(a) * flen * 0.5
            fcy = ayp + math.sin(a) * flen * 0.5
            rot = -a if side > 0 else a
            s += outlined(ellipse(fcx, fcy, flen * 0.72, fthick, rot), GILL)
            # rounded tip cap just beyond the frond end
            tcx = axp + side * math.cos(a) * flen * 1.06
            tcy = ayp + math.sin(a) * flen * 1.06
            s += outlined(circle(tcx, tcy, fthick * 0.95), GILL_TIP)
            s.append((circle(tcx - side * 7 * S, tcy - 6 * S, 7 * S), GILL_CORE))

    # --- feet: stubby ovals peeking under the body ---
    s += outlined(ellipse(410 * S, 872 * S, 56 * S, 36 * S), BODY)
    s += outlined(ellipse(614 * S, 872 * S, 56 * S, 36 * S), BODY)
    for fx in (410, 614):
        for d in (-20, 0, 20):
            s.append((circle(fx * S + d * S, 884 * S, 5 * S), BODY_SHADE))

    # --- body: soft pear below the head ---
    body = blob(512 * S, 760 * S, 226 * S, 12 * S, 7, rot0=0.6)
    s += outlined(body, BODY)
    s.append((ellipse(512 * S, 800 * S, 120 * S, 86 * S), BELLY))
    s.append((ellipse(424 * S, 680 * S, 60 * S, 30 * S, math.radians(-0.3)), BODY_LIGHT))

    # --- head: big round, covers gill bases ---
    head = blob(512 * S, 430 * S, 292 * S, 10 * S, 9, rot0=0.3)
    s += outlined(head, BODY)
    s.append((ellipse(414 * S, 322 * S, 86 * S, 46 * S, math.radians(-0.25)), BODY_LIGHT))

    # --- face ---
    for ex, ey in [(396, 442), (628, 442)]:
        ex, ey = ex * S, ey * S
        s.append((ellipse(ex, ey, 54 * S, 60 * S), EYE))
        s.append((ellipse(ex + 16 * S, ey - 20 * S, 16 * S, 16 * S), WHITE))
        s.append((ellipse(ex - 14 * S, ey + 18 * S, 8 * S, 8 * S), WHITE))
    s.append((ellipse(322 * S, 528 * S, 46 * S, 26 * S, math.radians(0.2)), BLUSH))
    s.append((ellipse(702 * S, 528 * S, 46 * S, 26 * S, math.radians(-0.2)), BLUSH))
    s.append((smile(512 * S, 540 * S, 34 * S, 30 * S), MOUTH))
    s.append((ellipse(512 * S, 556 * S, 12 * S, 8 * S), (255, 150, 160)))

    # --- arms + heart, drawn last: in front of head bottom and body ---
    s += outlined(ellipse(392 * S, 700 * S, 62 * S, 44 * S, math.radians(0.45)), BODY)
    s += outlined(ellipse(632 * S, 700 * S, 62 * S, 44 * S, math.radians(-0.45)), BODY)
    s += outlined(heart(512 * S, 668 * S, 86 * S), HEART)
    s.append((heart(512 * S, 668 * S, 70 * S), HEART))
    s.append((circle(486 * S, 640 * S, 9 * S), WHITE))  # glint
    # tiny paws gripping the heart's lower sides, drawn last
    s += outlined(circle(448 * S, 712 * S, 26 * S), BODY)
    s += outlined(circle(576 * S, 712 * S, 26 * S), BODY)

    return s


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    rgb = render(build())
    write_png(os.path.join(out_dir, "entry.png"), rgb)


if __name__ == "__main__":
    main()
