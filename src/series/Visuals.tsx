import React from 'react';
import {Img, OffthreadVideo, staticFile} from 'remotion';
import {Mimo} from '../devmimo/Mimo';
import {accentA, clamp01, FONT, HandKey, inkA, io, lerp, Panel, S, samplePath} from './theme';

/* Demonstration panels and cover illustrations. Each panel is drawn from data (a keyed hand path, terminal lines, code, a real
   screenshot), so an episode only supplies what it verified; nothing here knows which repository it is showing. */

// ---------------------------------------------------------------- hand (MediaPipe's 21-landmark topology)
const TEMPLATE: [number, number][] = [
  [0, 0], [-.18, -.08], [-.32, -.2], [-.42, -.32], [-.5, -.42],
  [-.16, -.42], [-.2, -.6], [-.22, -.72], [-.24, -.83],
  [0, -.45], [0, -.66], [0, -.79], [0, -.91],
  [.14, -.42], [.16, -.61], [.17, -.72], [.18, -.82],
  [.26, -.36], [.31, -.5], [.34, -.59], [.36, -.68],
];
export const BONES: [number, number][] = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16], [13, 17], [0, 17], [17, 18], [18, 19], [19, 20]];

/** Landmarks for a pose: pinch 0..1 brings thumb and index tips together; open 0..1 (1 = flat hand) curls the other fingers. */
export const handPose = (pinch = 0, open = 1): [number, number][] => {
  const p = TEMPLATE.map(([x, y]) => [x, y] as [number, number]);
  const curl = 1 - clamp01(open);
  for (const [mcp, tips] of [[9, [10, 11, 12]], [13, [14, 15, 16]], [17, [18, 19, 20]]] as [number, number[]][]) {
    tips.forEach((j, k) => {
      const amt = curl * (.45 + k * .2);
      p[j] = [lerp(p[j][0], p[mcp][0], amt), lerp(p[j][1], p[mcp][1] + .12 * curl, amt)];
    });
  }
  const meet: [number, number] = [-.36, -.62];
  const k = clamp01(pinch);
  p[8] = [lerp(p[8][0], meet[0] + .02, k), lerp(p[8][1], meet[1], k)];
  p[7] = [lerp(p[7][0], -.29, k * .8), lerp(p[7][1], -.7, k * .8)];
  p[4] = [lerp(p[4][0], meet[0] - .02, k), lerp(p[4][1], meet[1] + .02, k)];
  p[3] = [lerp(p[3][0], -.44, k * .7), lerp(p[3][1], -.48, k * .7)];
  return p;
};

/** A flat, non-photographic hand: soft silhouette + landmark skeleton. (cx, cy) is the wrist, size the hand length in px. */
export const HandGlyph: React.FC<{cx: number; cy: number; size: number; pinch?: number; open?: number; mirror?: boolean; skeleton?: number;
  silhouette?: string; tilt?: number}> = ({cx, cy, size, pinch = 0, open = 1, mirror = false, skeleton = 1, silhouette = inkA(.16), tilt = 0}) => {
  const pts = handPose(pinch, open).map(([x, y]) => {
    const a = tilt * Math.PI / 180, xx = (mirror ? -x : x), yy = y;
    return [cx + (xx * Math.cos(a) - yy * Math.sin(a)) * size, cy + (xx * Math.sin(a) + yy * Math.cos(a)) * size];
  });
  const palm = [0, 1, 5, 9, 13, 17].map(i => pts[i].join(',')).join(' ');
  return <g>
    <polygon points={palm} fill={silhouette} stroke={silhouette} strokeWidth={size * .2} strokeLinejoin="round"/>
    {BONES.map(([a, b], i) =>
      <line key={`s${i}`} x1={pts[a][0]} y1={pts[a][1]} x2={pts[b][0]} y2={pts[b][1]} stroke={silhouette} strokeWidth={size * .13} strokeLinecap="round"/>)}
    <g opacity={skeleton}>
      {BONES.map(([a, b], i) => <line key={i} x1={pts[a][0]} y1={pts[a][1]} x2={pts[b][0]} y2={pts[b][1]} stroke={S.accent} strokeWidth={Math.max(2, size * .012)} strokeLinecap="round"/>)}
      {pts.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={Math.max(3.5, size * (i % 4 === 0 && i ? .022 : .016))} fill={S.ink} stroke={S.accent} strokeWidth={Math.max(1.5, size * .007)}/>)}
    </g>
  </g>;
};

export const handTip = (cx: number, cy: number, size: number, pinch = 0, open = 1, mirror = false) => {
  const p = handPose(pinch, open);
  const m = pinch > .5 ? [(p[4][0] + p[8][0]) / 2, (p[4][1] + p[8][1]) / 2] : p[8];
  return [cx + (mirror ? -m[0] : m[0]) * size, cy + m[1] * size];
};

// ---------------------------------------------------------------- panel chrome
export const PanelFrame: React.FC<{w: number; h: number; title?: string; tag?: string | null; children: React.ReactNode; tone?: 'cam' | 'ui'}> =
  ({w, h, title, tag, children, tone = 'ui'}) =>
    <div style={{position: 'relative', width: w, height: h, borderRadius: 26, overflow: 'hidden', background: tone === 'cam' ? '#121316' : S.panel,
      border: `2px solid ${inkA(.09)}`, boxShadow: '0 30px 80px rgba(0,0,0,.55)'}}>
      {children}
      {title && <div style={{position: 'absolute', left: 20, top: 16, fontFamily: FONT.mono, fontSize: 24, fontWeight: 700, letterSpacing: 2, color: S.inkSoft,
        display: 'flex', alignItems: 'center', gap: 10}}>
        {tone === 'cam' && <span style={{width: 12, height: 12, borderRadius: 6, background: S.error, display: 'inline-block'}}/>}{title}</div>}
      {tag && <div style={{position: 'absolute', right: 14, bottom: 12, fontFamily: FONT.mono, fontSize: 18, letterSpacing: 1.5, color: S.muted,
        background: 'rgba(14,15,18,.7)', padding: '4px 10px', borderRadius: 8}}>{tag}</div>}
    </div>;

/** Webcam-style view: hand silhouette, landmarks, bounding box and the orange tracking indicator. */
export const HandPanel: React.FC<{w: number; h: number; path: HandKey[]; t: number; title?: string; tag?: string | null; handSize?: number}> =
  ({w, h, path, t, title = 'CAM', tag, handSize}) => {
    const k = samplePath(path, t);
    const size = handSize ?? Math.min(w, h) * .52;
    const cx = k.x * w, cy = k.y * h + size * .45;
    const pts = handPose(k.pinch, k.open).map(([x, y]) => [cx + x * size, cy + y * size]);
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
    const [tx, ty] = handTip(cx, cy, size, k.pinch, k.open);
    const pad = 22;
    return <PanelFrame w={w} h={h} title={title} tag={tag} tone="cam">
      <svg width={w} height={h} style={{position: 'absolute', inset: 0}}>
        <defs><pattern id="scan" width="6" height="6" patternUnits="userSpaceOnUse"><rect width="6" height="1" fill={inkA(.025)}/></pattern></defs>
        <rect width={w} height={h} fill="url(#scan)"/>
        <HandGlyph cx={cx} cy={cy} size={size} pinch={k.pinch} open={k.open}/>
        <rect x={Math.min(...xs) - pad} y={Math.min(...ys) - pad} width={Math.max(...xs) - Math.min(...xs) + pad * 2} height={Math.max(...ys) - Math.min(...ys) + pad * 2}
          fill="none" stroke={accentA(.55)} strokeWidth={2} strokeDasharray="10 8" rx={10}/>
        <circle cx={tx} cy={ty} r={26 + k.pinch * -6} fill="none" stroke={S.accent} strokeWidth={4}/>
        <circle cx={tx} cy={ty} r={7} fill={S.accent}/>
      </svg>
    </PanelFrame>;
  };

const Arrow: React.FC<{x: number; y: number; s?: number; press?: number}> = ({x, y, s = 1, press = 0}) =>
  <g transform={`translate(${x} ${y}) scale(${s * (1 - press * .12)})`}>
    <path d="M0,0 L0,38 L10,29 L17,45 L24,42 L17,26 L30,26 Z" fill={S.ink} stroke={S.ground} strokeWidth={3} strokeLinejoin="round"/>
  </g>;

/** Desktop view: the cursor follows the same keyed path (mirrored like a webcam); pinch = press. */
export const CursorPanel: React.FC<{w: number; h: number; path: HandKey[]; t: number; title?: string; tag?: string | null; mirror?: boolean}> =
  ({w, h, path, t, title = 'DESKTOP', tag, mirror = true}) => {
    const k = samplePath(path, t);
    const map = (kk: {x: number; y: number}) => [(mirror ? 1 - kk.x : kk.x) * w * .9 + w * .05, kk.y * h * .8 + h * .12];
    const [x, y] = map(k);
    const trail = [.32, .24, .16, .08].map(d => map(samplePath(path, t - d)));
    // press ripples: every frame where pinch crosses .7 upward within the last .5 s
    const ripples: {x: number; y: number; age: number}[] = [];
    for (let d = 0; d < .5; d += 1 / 30) {
      const a = samplePath(path, t - d - 1 / 30), b = samplePath(path, t - d);
      if ((a.pinch ?? 0) < .7 && (b.pinch ?? 0) >= .7) { const [rx, ry] = map(b); ripples.push({x: rx, y: ry, age: d}); }
    }
    const pressed = k.pinch >= .7;
    return <PanelFrame w={w} h={h} title={title} tag={tag}>
      <svg width={w} height={h} style={{position: 'absolute', inset: 0}}>
        {[[.08, .2, .5, .36], [.42, .5, .5, .34]].map(([a, b, c, d], i) =>
          <g key={i}>
            <rect x={a * w} y={b * h} width={c * w} height={d * h} rx={14} fill={S.panelHi} stroke={inkA(.08)} strokeWidth={2}/>
            <rect x={a * w} y={b * h} width={c * w} height={30} rx={14} fill={S.line}/>
            {[0, 1, 2].map(j => <circle key={j} cx={a * w + 20 + j * 18} cy={b * h + 15} r={5} fill={inkA(.25)}/>)}
            {[0, 1, 2].map(j => <rect key={j} x={a * w + 22} y={b * h + 50 + j * 26} width={c * w * (.7 - j * .15)} height={12} rx={6} fill={inkA(.08)}/>)}
          </g>)}
        {trail.map(([tx, ty], i) => <circle key={i} cx={tx} cy={ty} r={6 - i} fill={accentA(.35 - i * .07)}/>)}
        {ripples.map((r, i) => <circle key={i} cx={r.x} cy={r.y} r={10 + r.age * 120} fill="none" stroke={S.accent} strokeWidth={4} opacity={1 - r.age * 2}/>)}
        {pressed && <circle cx={x} cy={y} r={16 * Math.max(1, w / 520)} fill={accentA(.35)}/>}
        <Arrow x={x} y={y} s={Math.max(1, w / 520)} press={pressed ? 1 : 0}/>
      </svg>
    </PanelFrame>;
  };

export const TerminalPanel: React.FC<{w: number; h: number; lines: {text: string; at: number; tone?: string}[]; t: number; title?: string; tag?: string | null;
  size?: number}> = ({w, h, lines, t, title = 'TERMINAL', tag, size = 30}) => {
    const col = (tone?: string) => tone === 'ok' ? S.ok : tone === 'dim' ? S.muted : tone === 'out' ? S.inkSoft : S.ink;
    return <PanelFrame w={w} h={h} title={title} tag={tag}>
      <div style={{position: 'absolute', left: 26, right: 26, top: 66, fontFamily: FONT.mono, fontSize: size, lineHeight: 1.45}}>
        {lines.filter(l => t >= l.at).map((l, i) => {
          const typed = l.tone === 'cmd' || !l.tone ? Math.floor(clamp01((t - l.at) / .6) * l.text.length) : l.text.length;
          return <div key={i} style={{color: col(l.tone), whiteSpace: 'pre', overflow: 'hidden'}}>
            {(l.tone === 'cmd' || !l.tone) && <span style={{color: S.accent}}>$ </span>}{l.text.slice(0, typed)}</div>;
        })}
      </div>
    </PanelFrame>;
  };

export const CodePanel: React.FC<{w: number; h: number; lines: string[]; highlight?: number[]; t: number; title?: string; tag?: string | null}> =
  ({w, h, lines, highlight = [], t, title = 'SOURCE', tag}) =>
    <PanelFrame w={w} h={h} title={title} tag={tag}>
      <div style={{position: 'absolute', left: 0, right: 0, top: 66, fontFamily: FONT.mono, fontSize: 26, lineHeight: 1.55}}>
        {lines.map((l, i) => {
          const on = highlight.includes(i);
          return <div key={i} style={{padding: '0 26px', color: on ? S.ink : S.muted, whiteSpace: 'pre', overflow: 'hidden',
            background: on ? accentA(.14 * io(t * 30, 6 + i * 2, 16 + i * 2)) : 'transparent', borderLeft: `4px solid ${on ? S.accent : 'transparent'}`}}>{l}</div>;
        })}
      </div>
    </PanelFrame>;

export const ImagePanel: React.FC<{w: number; h: number; src: string; t: number; pan?: [number, number]; title?: string; tag?: string | null;
  position?: string}> = ({w, h, src, t, pan = [0, 0], title, tag, position = 'center'}) =>
    <PanelFrame w={w} h={h} title={title} tag={tag}>
      <Img src={staticFile(src)} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', objectPosition: position,
        transform: `translate(${pan[0] * t}px, ${pan[1] * t}px)`}}/>
    </PanelFrame>;

/** A real output video in a phone frame (9:16, centred in w × h). Muted: the episode's narration carries the sound. */
export const VideoPanel: React.FC<{w: number; h: number; src: string; startFrom?: number; title?: string; tag?: string | null}> =
  ({w, h, src, startFrom = 0, title, tag}) => {
    const ph = Math.min(h, w * 16 / 9), pw = ph * 9 / 16;
    return <div style={{position: 'relative', width: w, height: h}}>
      <div style={{position: 'absolute', left: (w - pw) / 2, top: (h - ph) / 2, width: pw, height: ph, borderRadius: pw * .09, overflow: 'hidden',
        border: `${Math.max(4, pw * .018)}px solid ${S.line}`, boxShadow: `0 30px 80px rgba(0,0,0,.6), 0 0 0 2px ${inkA(.08)}`, background: '#000'}}>
        <OffthreadVideo src={staticFile(src)} muted startFrom={Math.round(startFrom * 30)} style={{width: '100%', height: '100%', objectFit: 'cover'}}/>
        {title && <div style={{position: 'absolute', left: 14, top: 14, fontFamily: FONT.mono, fontWeight: 700, fontSize: 20, letterSpacing: 2, color: S.ground,
          background: S.accent, padding: '4px 10px', borderRadius: 8}}>{title}</div>}
        {tag && <div style={{position: 'absolute', left: 0, right: 0, top: 50, textAlign: 'center'}}><span style={{fontFamily: FONT.mono, fontSize: 17,
          letterSpacing: 1.2, color: S.inkSoft, background: 'rgba(14,15,18,.75)', padding: '4px 10px', borderRadius: 8}}>{tag}</span></div>}
      </div>
    </div>;
  };

export const PanelView: React.FC<{panel: Panel; w: number; h: number; t: number; tag?: string | null}> = ({panel, w, h, t, tag}) => {
  switch (panel.kind) {
    case 'hand': return <HandPanel w={w} h={h} path={panel.path} t={t} title={panel.label} tag={tag}/>;
    case 'cursor': return <CursorPanel w={w} h={h} path={panel.path} t={t} title={panel.label} tag={tag}/>;
    case 'terminal': return <TerminalPanel w={w} h={h} lines={panel.lines} t={t} title={panel.title ?? panel.label} tag={tag} size={panel.size}/>;
    case 'code': return <CodePanel w={w} h={h} lines={panel.lines} highlight={panel.highlight} t={t} title={panel.title ?? panel.label} tag={tag}/>;
    case 'image': return <ImagePanel w={w} h={h} src={panel.src} t={t} pan={panel.pan} title={panel.label} tag={tag} position={panel.position}/>;
    case 'video': return <VideoPanel w={w} h={h} src={panel.src} startFrom={panel.startFrom} title={panel.label} tag={tag}/>;
  }
};

// ---------------------------------------------------------------- cover illustrations (static, original vector art)
const CoverHandCursor: React.FC<{w: number; h: number}> = ({w, h}) => {
  const size = h * .8, cx = w * .27, cy = h * .96;
  const [tx, ty] = handTip(cx, cy, size, .15, 1);
  const cxr = w * .8, cyr = h * .3;
  return <svg width={w} height={h} style={{overflow: 'visible'}}>
    <HandGlyph cx={cx} cy={cy} size={size} pinch={.15} silhouette={inkA(.12)}/>
    <circle cx={tx} cy={ty} r={22} fill="none" stroke={S.accent} strokeWidth={5}/>
    <path d={`M${tx + 26},${ty} C${tx + 140},${ty - 10} ${cxr - 150},${cyr + 40} ${cxr - 18},${cyr + 8}`} fill="none" stroke={S.accent} strokeWidth={4} strokeDasharray="12 10"/>
    <circle cx={cxr} cy={cyr + 12} r={34} fill={accentA(.18)}/>
    <Arrow x={cxr - 6} y={cyr - 6} s={1.9}/>
  </svg>;
};
const CoverTerminal: React.FC<{w: number; h: number}> = ({w, h}) =>
  <svg width={w} height={h}>
    <rect x={w * .12} y={h * .08} width={w * .76} height={h * .84} rx={26} fill={S.panel} stroke={inkA(.1)} strokeWidth={3}/>
    {[0, 1, 2].map(i => <circle key={i} cx={w * .12 + 34 + i * 26} cy={h * .08 + 30} r={7} fill={inkA(.25)}/>)}
    {[[.3, S.accent], [.5, S.inkSoft], [.4, S.inkSoft], [.22, S.ok]].map(([len, c], i) =>
      <rect key={i} x={w * .12 + 40} y={h * .08 + 80 + i * 52} width={w * .76 * (len as number)} height={20} rx={10} fill={c as string}/>)}
  </svg>;

/** Input → output: a real screenshot of the project's input, an arrow, and a real frame of what it produced, in a phone. */
const CoverInputOutput: React.FC<{w: number; h: number; input?: string; output?: string}> = ({w, h, input, output}) => {
  const ch = h * .86, cw = ch * .68, ph = h * .98, pw = ph * 9 / 16;
  return <div style={{position: 'relative', width: w, height: h}}>
    <div style={{position: 'absolute', left: w * .02, top: (h - ch) / 2 + 14, width: cw, height: ch, borderRadius: 22, overflow: 'hidden', transform: 'rotate(-4deg)',
      border: `3px solid ${inkA(.14)}`, boxShadow: '0 24px 60px rgba(0,0,0,.6)', background: S.panel}}>
      {input && <Img src={staticFile(input)} style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top left'}}/>}
    </div>
    <svg width={w} height={h} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
      <path d={`M${w * .02 + cw + 8},${h * .5} C${w * .5},${h * .38} ${w * .55},${h * .62} ${w - pw - w * .04},${h * .5}`} fill="none" stroke={S.accent} strokeWidth={6}
        strokeLinecap="round"/>
      <path d={`M${w - pw - w * .04 - 22},${h * .5 - 16} L${w - pw - w * .04},${h * .5} L${w - pw - w * .04 - 22},${h * .5 + 16}`} fill="none" stroke={S.accent}
        strokeWidth={6} strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
    <div style={{position: 'absolute', right: w * .02, top: (h - ph) / 2, width: pw, height: ph, borderRadius: pw * .1, overflow: 'hidden', transform: 'rotate(3deg)',
      border: `5px solid ${S.line}`, boxShadow: `0 24px 60px rgba(0,0,0,.6), 0 0 0 3px ${S.accent}`, background: '#000'}}>
      {output && <Img src={staticFile(output)} style={{width: '100%', height: '100%', objectFit: 'cover'}}/>}
    </div>
  </div>;
};

/** The episode's central cover illustration, chosen by `visual`. New kinds slot in here without touching the cover layout. */
export const ProjectVisual: React.FC<{visual: string; w: number; h: number; assets?: {input?: string; output?: string}}> = ({visual, w, h, assets}) => {
  switch (visual) {
    case 'hand-cursor': return <CoverHandCursor w={w} h={h}/>;
    case 'input-output': return <CoverInputOutput w={w} h={h} input={assets?.input} output={assets?.output}/>;
    default: return <CoverTerminal w={w} h={h}/>;
  }
};

/** The series mascot: the brand character (identity.json) with the series' reaction states. */
export type MimoState = 'curious' | 'surprised' | 'thinking' | 'excited' | 'pointing' | 'neutral';
export const MimoMascot: React.FC<{state: MimoState; size: number; frame: number; mouth?: number; look?: {x: number; y: number}; amount?: number;
  pointAngle?: number}> = ({state, size, frame, mouth = 0, look, amount = 1, pointAngle = -20}) => {
  const a = clamp01(amount);
  const t = frame / 30;
  switch (state) {
    case 'curious': return <Mimo size={size} frame={frame} mouth={mouth} look={look ?? {x: .7, y: -.2}} tilt={7 * a}/>;
    case 'surprised': return <Mimo size={size} frame={frame} mouth={mouth} expression="surprised" look={look} squash={-.25 * a}/>;
    case 'thinking': return <Mimo size={size} frame={frame} mouth={mouth} expression="focused" look={look ?? {x: -.6, y: -.8}} tilt={-5 * a}/>;
    case 'excited': return <Mimo size={size} frame={frame} mouth={mouth} expression="happy" glow={1 + .5 * a} hop={a * Math.abs(Math.sin(t * Math.PI * 2.2)) * .8}/>;
    case 'pointing': return <Mimo size={size} frame={frame} mouth={mouth} look={look ?? {x: 1, y: -.3}} point={a} pointAngle={pointAngle} tilt={6 * a}/>;
    default: return <Mimo size={size} frame={frame} mouth={mouth} look={look}/>;
  }
};
