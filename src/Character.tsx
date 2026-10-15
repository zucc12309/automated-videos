import React from 'react';
import {Easing, interpolate, useCurrentFrame} from 'remotion';

/* "Dev" — original presenter built only from rounded primitives (rounded rects, circles, pills), per Duolingo-style
   appeal rules: one shape vocabulary, pill eyes with off-center pupils, oversized glasses as the signature feature,
   base + one shadow tone per material, uniform warm outline. Drawn in a 500x640 box. */

export type Pose = 'rest' | 'point' | 'pointRight' | 'wave' | 'present' | 'thumbs' | 'shrug' | 'count';
export type Expression = 'talk' | 'happy' | 'surprised' | 'smug';
export type Viseme = 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G' | 'H' | 'X';
type Hand = 'mitt' | 'point' | 'thumb' | 'open';
type Arm = {a1: number; a2: number; hand: Hand};

const REST: Arm = {a1: 10, a2: 14, hand: 'mitt'};
export const POSES: Record<Pose, {left: Arm; right: Arm}> = {
  rest: {left: REST, right: REST},
  point: {left: {a1: 140, a2: 158, hand: 'point'}, right: REST},
  pointRight: {left: REST, right: {a1: 140, a2: 158, hand: 'point'}},
  present: {left: {a1: 96, a2: 118, hand: 'open'}, right: REST},
  wave: {left: REST, right: {a1: 122, a2: 170, hand: 'open'}},
  thumbs: {left: REST, right: {a1: 62, a2: 150, hand: 'thumb'}},
  shrug: {left: {a1: 58, a2: 128, hand: 'open'}, right: {a1: 58, a2: 128, hand: 'open'}},
  count: {left: REST, right: {a1: 74, a2: 168, hand: 'point'}},
};

const LINE = '#2a1d18';
const LW = 6;
const SKIN = '#f6c9a6', SKIN_SH = '#e7a986';

// Deterministic smooth value noise in [-1, 1]; different seeds per body part avoid visibly looping sine motion.
const hash = (n: number) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return (x - Math.floor(x)) * 2 - 1; };
export const noise1 = (seed: number, t: number) => {
  const i = Math.floor(t), f = t - i, u = f * f * (3 - 2 * f);
  return hash(i + seed * 1000) * (1 - u) + hash(i + 1 + seed * 1000) * u;
};

const mix = (a: Arm, b: Arm, t: number): Arm => ({a1: a.a1 + (b.a1 - a.a1) * t, a2: a.a2 + (b.a2 - a.a2) * t, hand: t < .45 ? a.hand : b.hand});

const HandShape: React.FC<{hand: Hand}> = ({hand}) => {
  // Wrist at (0,0); forearm direction is -y.
  const s = {fill: SKIN, stroke: LINE, strokeWidth: LW};
  return <g>
    {hand === 'point' && <rect x="-9" y="-78" width="18" height="46" rx="9" {...s}/>}
    {hand === 'thumb' && <rect x="16" y="-64" width="18" height="40" rx="9" {...s} transform="rotate(-58 25 -44)"/>}
    {hand === 'open' && [-20, -6, 8, 22].map((x, i) => <rect key={i} x={x - 8} y={-74 + Math.abs(x - 1) * .45} width="16" height="40" rx="8" {...s}/>)}
    <rect x="-30" y="-50" width="60" height="56" rx="28" {...s}/>
    {hand !== 'thumb' && <rect x="-44" y="-36" width="18" height="34" rx="9" {...s} transform="rotate(-30 -35 -19)"/>}
  </g>;
};

const Limb: React.FC<{x: number; y: number; dir: 1 | -1; arm: Arm; sleeve: string; wobble: number}> = ({x, y, dir, arm, sleeve, wobble}) => {
  const r = (a: number) => a * Math.PI / 180;
  const ex = x + Math.sin(r(arm.a1)) * 118 * dir, ey = y + Math.cos(r(arm.a1)) * 118;
  const a2 = arm.a2 + wobble;
  const wx = ex + Math.sin(r(a2)) * 104 * dir, wy = ey + Math.cos(r(a2)) * 104;
  const rot = Math.atan2(wx - ex, -(wy - ey)) * 180 / Math.PI;
  const d = `M${x} ${y} L${ex} ${ey} L${wx} ${wy}`;
  return <g>
    <path d={d} fill="none" stroke={LINE} strokeWidth={58} strokeLinecap="round" strokeLinejoin="round"/>
    <path d={d} fill="none" stroke={sleeve} strokeWidth={46} strokeLinecap="round" strokeLinejoin="round"/>
    <g transform={`translate(${wx} ${wy}) rotate(${rot})`}><g transform="translate(0 -4) scale(1.05)"><HandShape hand={arm.hand}/></g></g>
  </g>;
};

// Mouth shapes centered at (250, 372). `open` scales jaw height for C/D from loudness (clamped 0.6-1.1).
const Mouth: React.FC<{v: Viseme; open: number; happy: boolean; id: string}> = ({v, open, happy, id}) => {
  const dark = '#6a2522', tongue = '#e0716a', teeth = '#fffaf2';
  const box = (w: number, h: number, extra?: React.ReactNode) => <g>
    <defs><clipPath id={`m-${id}-${v}`}><rect x={250 - w / 2} y={372 - h / 2} width={w} height={h} rx={Math.min(w, h) / 2}/></clipPath></defs>
    <rect x={250 - w / 2} y={372 - h / 2} width={w} height={h} rx={Math.min(w, h) / 2} fill={dark}/>
    <g clipPath={`url(#m-${id}-${v})`}>
      <rect x={250 - w / 2} y={372 - h / 2} width={w} height={Math.min(16, h * .34)} fill={teeth}/>
      {extra ?? <rect x={250 - w * .32} y={372 + h * .12} width={w * .64} height={h * .6} rx={h * .3} fill={tongue}/>}
    </g>
    <rect x={250 - w / 2} y={372 - h / 2} width={w} height={h} rx={Math.min(w, h) / 2} fill="none" stroke={LINE} strokeWidth={LW}/>
  </g>;
  const k = Math.max(.6, Math.min(1.1, open));
  switch (v) {
    case 'A': return <rect x="222" y="368" width="56" height="9" rx="4.5" fill={LINE}/>;
    case 'B': return box(66, 22, <rect x="214" y="372" width="72" height="4" fill={dark}/>);
    case 'C': return box(62, 38 * k);
    case 'D': return box(78, 54 * k);
    case 'E': return box(48, 40);
    case 'F': return <g><rect x="234" y="356" width="32" height="32" rx="16" fill={dark} stroke={LINE} strokeWidth={LW}/><rect x="242" y="364" width="16" height="16" rx="8" fill="#4a1816"/></g>;
    case 'G': return box(60, 24, <rect x="214" y="374" width="72" height="20" fill="#d9706a"/>);
    case 'H': return box(58, 42, <rect x="232" y={360} width="36" height="16" rx="8" fill={tongue}/>);
    default: return <path d={happy ? 'M216 360 Q250 398 284 360' : 'M222 366 Q250 384 278 366'} fill="none" stroke={LINE} strokeWidth="7" strokeLinecap="round"/>;
  }
};

const ampToViseme = (m: number): Viseme => m < .08 ? 'X' : m < .3 ? 'B' : m < .62 ? 'C' : 'D';

export const Character: React.FC<{
  width: number; mouth: number; pose: Pose; prevPose?: Pose; poseT?: number; expression?: Expression;
  look?: {x: number; y: number}; accent?: string; hoodie?: string; hair?: string; emphasis?: boolean; flip?: boolean;
  viseme?: Viseme; nod?: number; blink?: number; seed?: number;
}> = ({width, mouth, pose, prevPose, poseT = 1, expression = 'talk', look = {x: 0, y: .3}, accent = '#d63a2a', hoodie = '#2f3b52',
  hair = '#3b2a21', emphasis = false, flip = false, viseme, nod = 0, blink, seed = 1}) => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  const from = POSES[prevPose ?? pose] ?? POSES.rest, to = POSES[pose] ?? POSES.rest;
  // Anticipation + overshoot via back easing, then settle.
  const e = interpolate(poseT, [0, 1], [0, 1], {easing: Easing.out(Easing.back(1.4)), extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const arms = {left: mix(from.left, to.left, e), right: mix(from.right, to.right, e)};
  const wobble = pose === 'wave' ? Math.sin(frame / 3.4) * 14 * poseT : 0;
  const breath = Math.sin(t * Math.PI * 2 / 4.2);
  const tilt = noise1(seed + 1, t * .6) * 2.4 + (emphasis ? -2.5 : 0) - nod * 4;
  const tiltLag = noise1(seed + 1, (t - .13) * .6) * 2.4 - nod * 2;
  const drift = {x: noise1(seed + 2, t * .45) * 3, y: noise1(seed + 3, t * .4) * 2 + nod * 7};
  // Blink: close 2f, hold 1f, open 4f. `blink` = frames since the last blink cue (motivated or random).
  const b = blink ?? 99;
  const lid = b < 2 ? b / 2 : b < 3 ? 1 : b < 7 ? 1 - (b - 3) / 4 : 0;
  const happy = expression === 'happy';
  const surprised = expression === 'surprised';
  const lidAmt = Math.max(lid, happy ? .5 : expression === 'smug' ? .35 : 0);
  const brow = (emphasis || surprised ? -12 : 0) - Math.max(0, mouth - .5) * 6 + (expression === 'smug' ? 4 : 0);
  const px = look.x * 11, py = 7 + look.y * 9;
  const v = viseme ?? ampToViseme(mouth);
  const id = `c${seed}`;
  const eye = (cx: number) => <g>
    <defs><clipPath id={`eye-${id}-${cx}`}><rect x={cx - 27} y={250} width={54} height={74} rx={27}/></clipPath></defs>
    <rect x={cx - 27} y={250} width={54} height={74} rx={27} fill="#fffdf8"/>
    <g clipPath={`url(#eye-${id}-${cx})`}>
      <circle cx={cx + px} cy={287 + py} r={surprised ? 13 : 16} fill={LINE}/>
      <circle cx={cx + px + 6} cy={281 + py} r={5} fill="#fff"/>
      <rect x={cx - 30} y={246} width={60} height={80 * lidAmt} fill={SKIN}/>
      {lidAmt > .05 && <rect x={cx - 30} y={246 + 80 * lidAmt - 3} width={60} height={6} rx={3} fill={LINE}/>}
    </g>
    <rect x={cx - 27} y={250} width={54} height={74} rx={27} fill="none" stroke={LINE} strokeWidth={4}/>
  </g>;
  return <svg width={width} height={width * 640 / 500} viewBox="0 0 500 640" style={{overflow: 'visible', transform: flip ? 'scaleX(-1)' : undefined}}>
    <g transform={`translate(${drift.x} ${breath * 2})`}>
      <g transform={`translate(250 640) scale(${1 + breath * .006} ${1 + breath * .014}) translate(-250 -640)`}>
        <rect x="104" y="432" width="292" height="300" rx="120" fill={hoodie} stroke={LINE} strokeWidth={LW}/>
        <rect x="300" y="470" width="70" height="200" rx="35" fill="#00000026"/>
        <rect x="182" y="430" width="136" height="54" rx="27" fill={hoodie} stroke={LINE} strokeWidth={LW}/>
        <rect x="200" y="438" width="100" height="34" rx="17" fill="#00000030"/>
        <rect x="214" y="500" width="10" height="70" rx="5" fill="#fffdf8"/>
        <rect x="276" y="500" width="10" height="70" rx="5" fill="#fffdf8"/>
        <rect x="128" y="410" width="244" height="40" rx="20" fill="none" stroke="#1d1b1a" strokeWidth="14"/>
        <rect x="112" y="406" width="54" height="76" rx="26" fill="#1d1b1a" stroke={LINE} strokeWidth={LW}/>
        <rect x="334" y="406" width="54" height="76" rx="26" fill="#1d1b1a" stroke={LINE} strokeWidth={LW}/>
        <rect x="124" y="420" width="28" height="48" rx="14" fill={accent}/>
        <rect x="348" y="420" width="28" height="48" rx="14" fill={accent}/>
      </g>
      <g transform={`translate(${drift.x * .6} ${drift.y}) rotate(${tilt} 250 430)`}>
        <circle cx="96" cy="290" r="32" fill={SKIN} stroke={LINE} strokeWidth={LW}/>
        <circle cx="404" cy="290" r="32" fill={SKIN} stroke={LINE} strokeWidth={LW}/>
        <rect x="92" y="112" width="316" height="320" rx="150" fill={SKIN} stroke={LINE} strokeWidth={LW}/>
        <rect x="320" y="250" width="66" height="150" rx="33" fill={SKIN_SH} opacity=".7"/>
        <g transform={`rotate(${(tiltLag - tilt) * 1.6} 250 200)`} fill={hair} stroke={LINE} strokeWidth={LW} strokeLinejoin="round">
          <rect x="86" y="80" width="328" height="112" rx="56"/>
          <rect x="92" y="140" width="56" height="100" rx="28"/>
          <rect x="352" y="140" width="56" height="100" rx="28"/>
          <rect x="200" y="58" width="150" height="76" rx="38" transform="rotate(-12 275 96)"/>
          <rect x="226" y="80" width="90" height="18" rx="9" fill="#ffffff33" stroke="none" transform="rotate(-12 271 89)"/>
        </g>
        <g transform={`translate(0 ${brow})`}>
          <rect x="160" y="204" width="66" height="16" rx="8" fill={hair} transform={`rotate(${surprised ? -6 : -3} 193 212)`}/>
          <rect x="274" y="204" width="66" height="16" rx="8" fill={hair} transform={`rotate(${surprised ? 6 : 3 + (expression === 'smug' ? 6 : 0)} 307 212)`}/>
        </g>
        {eye(200)}{eye(300)}
        <g fill="#ffffff1c" stroke={LINE} strokeWidth="10">
          <rect x="146" y="236" width="106" height="102" rx="40"/>
          <rect x="248" y="236" width="106" height="102" rx="40"/>
        </g>
        <rect x="236" y="262" width="28" height="10" rx="5" fill={LINE}/>
        <rect x="164" y="252" width="16" height="44" rx="8" fill="#ffffff55" transform="rotate(28 172 274)"/>
        <rect x="266" y="252" width="16" height="44" rx="8" fill="#ffffff55" transform="rotate(28 274 274)"/>
        <rect x="236" y="320" width="28" height="26" rx="13" fill={SKIN_SH}/>
        <rect x="140" y="350" width="44" height="20" rx="10" fill="#f39a86" opacity=".55"/>
        <rect x="316" y="350" width="44" height="20" rx="10" fill="#f39a86" opacity=".55"/>
        {surprised && v === 'X' ? <rect x="232" y="354" width="36" height="40" rx="18" fill="#6a2522" stroke={LINE} strokeWidth={LW}/> : <Mouth v={v} open={.6 + mouth * .55} happy={happy} id={id}/>}
      </g>
      <Limb x={140} y={500} dir={-1} arm={arms.left} sleeve={hoodie} wobble={0}/>
      <Limb x={360} y={500} dir={1} arm={arms.right} sleeve={hoodie} wobble={wobble}/>
    </g>
  </svg>;
};
