# mystery-filter: findings

## What it does (plain English)
- It reads a colour picture (PPM format), changes every pixel, and saves a new picture.
- First it works out how bright each pixel is. Green counts most, then red, then blue.
- Very bright pixels (brightness 233 or more out of 255) are "locked". Each one becomes the same cream colour (248, 240, 228), and the program counts them.
- Every other pixel gets a warm, faded "vintage" tint. Red goes up (+24). Green gets a little red mixed in (+10). Blue is toned down and blended toward grey (+4).
- At the end it prints `filtered WxH (N px locked)`. On the demo image that is `filtered 600x600 (13600 px locked)`.

## Recovered formula (per pixel, integer maths; `>>8` = shift right by 8, i.e. divide by 256 and round down)
```
Y   = 77*R + 150*G + 29*B
if Y > 0xE8FF (59647):          # luma >= 233
    out = (248, 240, 228); locked += 1
else:
    L  = Y >> 8
    R' = min(255, ((228*R + 28*G) >> 8) + 24)
    G' = ((24*R + 216*G) >> 8) + 10      # max 249, no clamp needed/present
    B' = ((176*B + 40*L)  >> 8) + 4      # max 215, no clamp needed/present
```
Input/output: it reads the header with `fscanf("P6 %d %d %d")`, uses one `fgetc` to skip the separator byte, then `fread`s W*H*3 bytes. It always writes the header `P6\n%d %d\n255\n`. Strings in .rodata: `usage: mystery-filter in.ppm out.ppm`, `filtered %dx%d (%ld px locked)`, `not a P6 ppm`, `short read`.

## Key disassembly (REA inspect_with_objdump, operation=disassemble)
Luma:
```
12ef:	0f b6 38             	movzbl (%rax),%edi
12f2:	0f b6 48 01          	movzbl 0x1(%rax),%ecx
12f6:	0f b6 70 02          	movzbl 0x2(%rax),%esi
12fa:	44 6b cf 4d          	imul   $0x4d,%edi,%r9d
12fe:	69 d1 96 00 00 00    	imul   $0x96,%ecx,%edx
1307:	44 6b ce 1d          	imul   $0x1d,%esi,%r9d
1311:	41 c1 f9 08          	sar    $0x8,%r9d
```
Lock test, fixed colour and counter:
```
1315:	81 fa ff e8 00 00    	cmp    $0xe8ff,%edx
131b:	0f 86 6f ff ff ff    	jbe    1290 <__fprintf_chk@plt+0x100>
1321:	49 83 c5 01          	add    $0x1,%r13
1325:	ba f8 ff ff ff       	mov    $0xfffffff8,%edx
132a:	bf f0 ff ff ff       	mov    $0xfffffff0,%edi
132f:	b9 e4 ff ff ff       	mov    $0xffffffe4,%ecx
```
Red channel (228R + 28G, >>8, +24, clamp 255):
```
1290:	44 69 d7 e4 00 00 00 	imul   $0xe4,%edi,%r10d
129a:	6b d1 1c             	imul   $0x1c,%ecx,%edx
12a6:	c1 fa 08             	sar    $0x8,%edx
12a9:	83 c2 18             	add    $0x18,%edx
12ac:	44 39 d2             	cmp    %r10d,%edx
12af:	41 0f 4f d2          	cmovg  %r10d,%edx
```
Green (216G + 8*3R = 216G + 24R, >>8, +10) and blue (176B + 8*5L = 176B + 40L, >>8, +4):
```
1297:	8d 3c 7f             	lea    (%rdi,%rdi,2),%edi
12b3:	69 c9 d8 00 00 00    	imul   $0xd8,%ecx,%ecx
12b9:	69 f6 b0 00 00 00    	imul   $0xb0,%esi,%esi
12bf:	8d 3c f9             	lea    (%rcx,%rdi,8),%edi
12c2:	43 8d 0c 89          	lea    (%r9,%r9,4),%ecx
12c6:	8d 0c ce             	lea    (%rsi,%rcx,8),%ecx
12c9:	c1 ff 08             	sar    $0x8,%edi
12cc:	c1 f9 08             	sar    $0x8,%ecx
12cf:	83 c7 0a             	add    $0xa,%edi
12d2:	83 c1 04             	add    $0x4,%ecx
```
Store in place (R, G, B):
```
12d9:	88 10                	mov    %dl,(%rax)
12df:	40 88 78 fe          	mov    %dil,-0x2(%rax)
12e3:	88 48 ff             	mov    %cl,-0x1(%rax)
```

## REA tool calls (in order; all made through mcp_call.mjs and logged in transcript.jsonl)
1. `capture_process_scenario` (mystery-filter input.ppm original-out.ppm): exit 0, printed `filtered 600x600 (13600 px locked)`
2. `inspect_with_objdump` operation=disassemble
3. `inspect_with_objdump` operation=section_headers (found .rodata at 0x2000, size 0x8f)
4. `inspect_with_objdump` operation=disassemble_all (to read the .rodata bytes and recover the strings)

(The `tools/list` and schema lookups are not counted as tool calls.)

## Comparison
`python3 rebuild.py input.ppm rebuilt-out.ppm` prints `filtered 600x600 (13600 px locked)`.
`rebuilt-out.ppm` vs `original-out.ppm`: **0 differing bytes**. The two files are byte-identical (1,080,015 bytes each).
