import React from 'react';
import {ID} from './tokens';

/* The brand character, rebuilt from Reference A: a marshmallow block with a domed top, a slightly darker base band,
   two vertical pill eyes and pink cheeks. Drawn in a 100 x 79 viewBox (identity.json proportions).
   Everything is a pure function of its props, so renders are deterministic. */

export type BlobState = 'idle' | 'speaking' | 'thinking' | 'pointing' | 'typing' | 'explaining' | 'surprised' | 'celebrating'
  | 'warning' | 'confused' | 'presenting' | 'exiting';

export type BlobProps = {
  size: number;                     // rendered width in px
  frame: number;                    // composition frame (idle motion)
  state: BlobState;
  stateFrame: number;               // frames since this state began
  mouth?: number;                   // 0..1 speech loudness
  look?: {x: number; y: number};    // -1..1 gaze
  blink?: number;                   // frames since last blink start
  point?: 'left' | 'right' | 'up';  // nub direction for pointing/presenting
  wink?: boolean;
  dim?: number;                     // 0 (full) .. 1 (dimmed while content has focus)
};

const P = ID.palette;
const R = 34, r = 15, Hh = 79, BAND = Hh * (1 - ID.proportions.band_height);
const BODY = `M0,${R} A${R},${R} 0 0 1 ${R},0 L${100 - R},0 A${R},${R} 0 0 1 100,${R} L100,${Hh - r} A${r},${r} 0 0 1 ${100 - r},${Hh} L${r},${Hh} A${r},${r} 0 0 1 0,${Hh - r} Z`;

const Eye: React.FC<{cx: number; cy: number; kind: string; open: number}> = ({cx, cy, kind, open}) => {
  if (kind === 'happy') return <path d={`M${cx - 4.2},${cy + 1.5} Q${cx},${cy - 4.5} ${cx + 4.2},${cy + 1.5}`} stroke={P.eye} strokeWidth={2.6} fill="none" strokeLinecap="round"/>;
  if (kind === 'surprised') return <circle cx={cx} cy={cy} r={4.6 * Math.max(.15, open)} fill={P.eye}/>;
  const h = (kind === 'squint' ? 8 : 15.5) * Math.max(.1, open);
  return <rect x={cx - 3.5} y={cy - h / 2} width={7} height={h} rx={3.5} fill={P.eye}/>;
};

export const Blob: React.FC<BlobProps> = ({size, frame, state, stateFrame, mouth = 0, look = {x: 0, y: 0}, blink = 99, point, wink, dim = 0}) => {
  const t = frame / 30;
  const breathe = 1 + .015 * Math.sin(t * Math.PI * .5);
  // Signature motions
  const hop = state === 'celebrating' || state === 'surprised' ? Math.max(0, Math.sin(Math.min(1, stateFrame / 14) * Math.PI)) * (state === 'celebrating' ? 16 : 9) : 0;
  const shiver = state === 'warning' ? Math.sin(stateFrame * 1.9) * Math.max(0, 1 - stateFrame / 24) * 1.4 : 0;
  const lean = state === 'presenting' || state === 'pointing' || state === 'explaining' ? (point === 'left' ? -6 : 6) * Math.min(1, stateFrame / 10) : 0;
  const typing = state === 'typing' ? Math.abs(Math.sin(stateFrame * .9)) * 1.6 : 0;
  const nod = state === 'speaking' ? Math.max(0, Math.sin(t * 7)) * mouth * 1.2 : 0;
  const squash = 1 - (hop > 0 ? .06 * Math.cos(Math.min(1, stateFrame / 14) * Math.PI) : 0);
  const blinkOpen = blink < 3 ? 1 - blink / 3 : blink < 6 ? (blink - 3) / 3 : 1;
  const eyeKind = state === 'celebrating' ? 'happy' : state === 'surprised' && stateFrame < 30 ? 'surprised' : state === 'warning' || state === 'confused' ? 'squint' : 'pill';
  const lx = look.x * 3.2, ly = look.y * 2.2 - (state === 'thinking' ? 2 : 0);
  const exit = state === 'exiting' ? Math.min(1, stateFrame / 14) : 0;
  const showNub = (state === 'pointing' || state === 'presenting') && point;
  const nubAngle = point === 'left' ? 180 : point === 'up' ? -70 : -10;
  const nubGrow = Math.min(1, stateFrame / 8);
  const glyph = state === 'thinking' ? '…' : state === 'confused' ? '?' : state === 'warning' ? '!' : '';
  const height = size * .79;
  return <div style={{position: 'relative', width: size, height, opacity: (1 - exit) * (1 - dim * .55), filter: dim > .05 ? `blur(${dim * 3}px)` : undefined,
    transform: `translate(${shiver}px, ${-hop + exit * size * .6 - typing}px) rotate(${lean}deg) scale(${1 / squash * (2 - breathe)}, ${squash * breathe})`, transformOrigin: '50% 100%'}}>
    <svg viewBox="-14 -26 128 115" width={size * 1.28} height={size * 1.15} style={{position: 'absolute', left: -size * .14, top: -size * .26, overflow: 'visible'}}>
      <ellipse cx={50} cy={Hh + 6} rx={38} ry={4.5} fill={P.shadow} opacity={.6 - hop / 40}/>
      {showNub && <g transform={`translate(${point === 'left' ? 4 : 96}, 52) rotate(${nubAngle}) scale(${nubGrow})`}>
        <rect x={0} y={-5} width={18} height={10} rx={5} fill={P.body}/></g>}
      <defs><clipPath id="blobClip"><path d={BODY}/></clipPath></defs>
      <path d={BODY} fill={P.body}/>
      <rect x={0} y={BAND} width={100} height={Hh - BAND} fill={P.band} clipPath="url(#blobClip)"/>
      <g transform={`translate(${lx}, ${ly + nod})`}>
        <Eye cx={41} cy={37} kind={eyeKind} open={blinkOpen}/>
        {wink ? <path d="M54.8,38.5 Q59,34 63.2,38.5" stroke={P.eye} strokeWidth={2.6} fill="none" strokeLinecap="round"/>
          : <Eye cx={59} cy={37} kind={eyeKind} open={blinkOpen}/>}
        {mouth > .12 && state !== 'celebrating' && <rect x={50 - 3.5} y={46 - mouth * 1.5} width={7} height={1.6 + mouth * 4.2} rx={1.8} fill={P.eye} opacity={.85}/>}
      </g>
      <ellipse cx={28} cy={BAND + 1} rx={5.2} ry={2.6} fill={P.cheek}/>
      <ellipse cx={72} cy={BAND + 1} rx={5.2} ry={2.6} fill={P.cheek}/>
      {glyph && <text x={88} y={-6} fontFamily="'JetBrains Mono', monospace" fontSize={22} fontWeight={700} fill={P.body}
        opacity={Math.min(1, stateFrame / 8)}>{glyph}</text>}
      {state === 'celebrating' && [0, 1, 2].map(i => {
        const k = Math.min(1, Math.max(0, (stateFrame - i * 3) / 10));
        return <path key={i} d="M0,-6 L1.6,-1.6 6,0 1.6,1.6 0,6 -1.6,1.6 -6,0 -1.6,-1.6Z" fill={P.spark}
          transform={`translate(${[8, 50, 92][i]}, ${-8 - k * 14 - (i === 1 ? 8 : 0)}) scale(${k * (1 - Math.max(0, (stateFrame - 26) / 14))})`}/>;
      })}
    </svg>
  </div>;
};
