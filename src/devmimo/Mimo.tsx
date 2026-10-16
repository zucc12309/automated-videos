import React from 'react';
import {ID} from '../premium/tokens';
import {lerp} from './theme';

/* Mimo is the brand's recurring character (brand/character/identity.json, the same design as src/premium/Blob.tsx): a soft
   marshmallow block with a domed top, a darker base band, two vertical pill eyes, pink cheeks and no limbs at rest. A short
   rounded nub appears only to wave. Shape and palette are read from identity.json, so the intro stays on-model.

   This wrapper adds the intro's animation controls (scripted blinks, wave, squash, typing bob, expressions) on top of the same
   drawing. Layout contract used by the scenes: the component is `size` wide and `size * 1.2` tall, feet at the bottom. */

export type MimoExpr = 'neutral' | 'happy' | 'surprised' | 'wink' | 'focused';
export type MimoProps = {
  size: number;               // rendered width of the body in px
  frame: number;              // drives breathing / blinking / waving
  mouth?: number;             // 0..1 loudness of the narration at this frame
  wave?: number;              // 0 rest .. 1 nub up and waving
  typing?: number;            // 0..1 quick bob
  expression?: MimoExpr;
  look?: {x: number; y: number}; // -1..1 gaze
  blinkAt?: number[];         // extra blinks (frames, same clock as `frame`)
  squash?: number;            // -1..1 landing squash / stretch
  glow?: number;              // >1 adds sparkles (big moments)
  autoBlink?: boolean;
  tilt?: number;              // degrees, body leans/tilts around the feet (curious, thinking)
  point?: number;             // 0..1 nub held out steadily toward pointAngle (identity gesture 'point'); overrides wave
  pointAngle?: number;        // degrees; 0 = straight right, -40 = up-right
  hop?: number;               // 0..1 lift (fraction of size * .25)
};

const P = ID.palette;
const R = 34, r = 15, Hh = 79, BAND = Hh * (1 - ID.proportions.band_height);
const BODY = `M0,${R} A${R},${R} 0 0 1 ${R},0 L${100 - R},0 A${R},${R} 0 0 1 100,${R} L100,${Hh - r} A${r},${r} 0 0 1 ${100 - r},${Hh} L${r},${Hh} A${r},${r} 0 0 1 0,${Hh - r} Z`;

const blinkOpen = (frame: number, extra: number[], auto: boolean) => {
  const windows = extra.map(b => frame - b);
  if (auto) windows.push((frame + 23) % 101, (frame + 61) % 167);      // every ~3.4 s and ~5.6 s, out of phase
  const d = windows.find(x => x >= 0 && x < 6);
  return d === undefined ? 1 : d < 3 ? 1 - d / 3 : (d - 3) / 3;
};

export const Mimo: React.FC<MimoProps> = ({size, frame, mouth = 0, wave = 0, typing = 0, expression = 'neutral', look = {x: 0, y: 0},
  blinkAt = [], squash = 0, glow = 1, autoBlink = true, tilt = 0, point = 0, pointAngle = -20, hop = 0}) => {
  const t = frame / 30;
  const breathe = Math.sin(t * Math.PI * .5) * .015;                    // identity: 1.5% at 0.25 Hz
  const bob = typing * Math.abs(Math.sin(t * Math.PI * 5.5)) * 2;
  const open = blinkOpen(frame, blinkAt, autoBlink);
  const lx = look.x * 3.2, ly = look.y * 2.2;
  const nod = mouth > .12 ? Math.max(0, Math.sin(t * 7)) * mouth * 1.2 : 0;
  const sx = 1 + squash * .09, sy = 1 - squash * .11 + breathe;
  const nubAngle = point > .02 ? lerp(30, pointAngle, Math.min(1, point)) : lerp(-10, -62 + Math.sin(t * Math.PI * 4.2) * 24, Math.min(1, wave));
  const nub = Math.max(wave, point);
  const sparkle = glow > 1.05 ? Math.min(1, (glow - 1) * 2) : 0;

  const eye = (cx: number, right: boolean) => {
    const cy = 37;
    if (expression === 'happy' || (right && expression === 'wink'))
      return <path d={`M${cx - 4.2},${cy + 1.5} Q${cx},${cy - 4.5} ${cx + 4.2},${cy + 1.5}`} stroke={P.eye} strokeWidth={2.6} fill="none" strokeLinecap="round"/>;
    if (expression === 'surprised') return <circle cx={cx} cy={cy} r={4.6 * Math.max(.15, open)} fill={P.eye}/>;
    const h = (expression === 'focused' ? 8 : 15.5) * Math.max(.1, open);
    return <rect x={cx - 3.5} y={cy - h / 2} width={7} height={h} rx={3.5} fill={P.eye}/>;
  };

  // body is drawn in a 100 x 79 box; the svg adds room for the nub, sparkles and shadow
  const W = size * 1.4, Hs = size * 1.2;
  return <div style={{position: 'relative', width: size, height: Hs}}>
    <svg viewBox="-20 -16.5 140 120" width={W} height={W * 120 / 140} style={{position: 'absolute', left: -size * .2, bottom: 0, overflow: 'visible'}}>
      <ellipse cx={50} cy={Hh + 6} rx={38 * (1 + squash * .12)} ry={4.5} fill={P.shadow} opacity={.7}/>
      <g transform={`translate(0 ${-bob - hop * 25}) translate(50 ${Hh}) rotate(${tilt}) scale(${sx} ${sy}) translate(-50 ${-Hh})`}>
        {nub > .02 && <g transform={`translate(96, 50) rotate(${nubAngle}) scale(${Math.min(1, nub * 1.5)})`}>
          <rect x={0} y={-5.5} width={20} height={11} rx={5.5} fill={P.body}/></g>}
        <defs><clipPath id="mimoClip"><path d={BODY}/></clipPath></defs>
        <path d={BODY} fill={P.body}/>
        <rect x={0} y={BAND} width={100} height={Hh - BAND} fill={P.band} clipPath="url(#mimoClip)"/>
        <g transform={`translate(${lx}, ${ly + nod})`}>
          {eye(41, false)}{eye(59, true)}
          {mouth > .12
            ? <rect x={50 - 3.5} y={46 - mouth * 1.5} width={7} height={1.6 + mouth * 4.2} rx={1.8} fill={P.eye} opacity={.85}/>
            : expression === 'surprised' ? <ellipse cx={50} cy={47.5} rx={2.2} ry={2.6} fill={P.eye} opacity={.85}/> : null}
        </g>
        <ellipse cx={28} cy={BAND + 1} rx={5.2} ry={2.6} fill={P.cheek}/>
        <ellipse cx={72} cy={BAND + 1} rx={5.2} ry={2.6} fill={P.cheek}/>
        {sparkle > 0 && [0, 1, 2].map(i => <path key={i} d="M0,-6 L1.6,-1.6 6,0 1.6,1.6 0,6 -1.6,1.6 -6,0 -1.6,-1.6Z" fill={P.spark}
          opacity={sparkle} transform={`translate(${[6, 50, 94][i]}, ${-10 - (i === 1 ? 6 : 0) + Math.sin(t * 4 + i) * 2}) scale(${.8 + .2 * Math.sin(t * 6 + i)})`}/>)}
      </g>
    </svg>
  </div>;
};
