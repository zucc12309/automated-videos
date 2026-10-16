#!/usr/bin/env python3
"""Rebuild of mystery-filter, recovered from REA objdump disassembly (main @ 0x11c0)."""
import sys, re

def read_ppm(path):
    data = open(path, "rb").read()
    # binary does fscanf("P6 %d %d %d") then one fgetc() to eat the single whitespace
    m = re.match(rb"P6\s+(\d+)\s+(\d+)\s+(\d+)", data)
    if not m:
        sys.stderr.write("not a P6 ppm\n"); sys.exit(1)
    w, h = int(m.group(1)), int(m.group(2))
    start = m.end() + 1
    px = bytearray(data[start:start + 3 * w * h])
    if len(px) != 3 * w * h:
        sys.stderr.write("short read\n"); sys.exit(1)
    return w, h, px

def main():
    if len(sys.argv) < 3:
        sys.stderr.write("usage: mystery-filter in.ppm out.ppm\n"); sys.exit(2)
    w, h, px = read_ppm(sys.argv[1])
    locked = 0
    for i in range(0, len(px), 3):
        r, g, b = px[i], px[i + 1], px[i + 2]
        y = 77 * r + 150 * g + 29 * b          # 0x12fa..0x130b
        if y > 0xE8FF:                          # 0x1315: luma >= 233 -> "locked"
            locked += 1
            nr, ng, nb = 0xF8, 0xF0, 0xE4       # 0x1325..0x132f: (248,240,228)
        else:
            lum = y >> 8                        # 0x1311
            nr = min(255, ((228 * r + 28 * g) >> 8) + 24)   # 0x1290..0x12af
            ng = ((24 * r + 216 * g) >> 8) + 10             # 0x12b3,0x12bf,0x12c9,0x12cf
            nb = ((176 * b + 40 * lum) >> 8) + 4            # 0x12b9,0x12c2,0x12c6,0x12cc,0x12d2
        px[i], px[i + 1], px[i + 2] = nr & 0xFF, ng & 0xFF, nb & 0xFF
    with open(sys.argv[2], "wb") as f:
        f.write(b"P6\n%d %d\n255\n" % (w, h))
        f.write(px)
    print("filtered %dx%d (%d px locked)" % (w, h, locked))

if __name__ == "__main__":
    main()
