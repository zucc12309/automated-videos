import React from 'react';
import {DM, FONT, lerp} from './theme';

/* Mimo, the DevMimo mascot: an ivory desk-robot with a charcoal screen face and orange LED eyes, an antenna bulb and a </> chest
   badge. Everything is layered SVG so each part animates on its own (blink, breathe, bob, wave, talk, squash).

   NOTE: no approved mascot image reached this build, so this is an original drawing. To match an approved profile image, change the
   shapes/colours here; every scene only uses this component's props. */

export type MimoExpr = 'neutral' | 'happy' | 'surprised' | 'wink' | 'focused';
export type MimoProps = {
  size: number;               // rendered width in px
  frame: number;              // drives breathing / blinking / waving
  mouth?: number;             // 0..1 loudness of the narration at this frame
  wave?: number;              // 0 rest .. 1 full wave (right arm up and swinging)
  typing?: number;            // 0..1 both arms tap quickly
  expression?: MimoExpr;
  look?: {x: number; y: number}; // -1..1 eye direction
  blinkAt?: number[];         // extra blinks (frames, same clock as `frame`)
  squash?: number;            // -1..1 landing squash / stretch
  glow?: number;              // eye + bulb glow 0..1.5
  autoBlink?: boolean;
};

const VB = {x: -50, y: -70, w: 500, h: 600};

const blinkAmount = (frame: number, extra: number[], auto: boolean) => {
  const windows = extra.map(b => frame - b);
  if (auto) windows.push((frame + 23) % 101, (frame + 61) % 167);
  const d = windows.find(x => x >= 0 && x < 6);
  return d === undefined ? 0 : Math.sin((d + .5) / 6 * Math.PI);
};

export const Mimo: React.FC<MimoProps> = ({size, frame, mouth = 0, wave = 0, typing = 0, expression = 'neutral', look = {x: 0, y: 0},
  blinkAt = [], squash = 0, glow = 1, autoBlink = true}) => {
  const t = frame / 30;
  const breath = Math.sin(t * 2 * Math.PI * .42);
  const bob = Math.sin(t * 2 * Math.PI * .42 - .7) * 5;
  const blink = expression === 'happy' ? 0 : blinkAmount(frame, blinkAt, autoBlink);
  const eyeOpen = Math.max(.08, 1 - blink);
  const lx = look.x * 15, ly = look.y * 10;
  const swing = Math.sin(t * 2 * Math.PI * 2.1) * 24;
  const tap = Math.sin(t * 2 * Math.PI * 5.5) * 9 * typing;
  const rightArm = lerp(-16 + breath * 2 + tap, -142 + swing, wave);
  const leftArm = 16 - breath * 2 - tap + wave * 6;
  const sx = 1 + squash * .09, sy = 1 - squash * .11 + breath * .012;
  const eyeH = expression === 'surprised' ? 74 : expression === 'focused' ? 44 : 62;
  const eyeW = expression === 'surprised' ? 42 : 34;
  const talking = mouth > .06;
  const bulb = .55 + .45 * Math.sin(t * 2 * Math.PI * .8);
  const g = Math.max(0, glow);

  const eye = (cx: number, cy: number, kind: 'open' | 'arc') => kind === 'arc'
    ? <path d={`M ${cx - 20} ${cy + 10} Q ${cx} ${cy - 22} ${cx + 20} ${cy + 10}`} fill="none" stroke={DM.orange} strokeWidth={11} strokeLinecap="round"/>
    : <rect x={cx - eyeW / 2} y={cy - eyeH * eyeOpen / 2} width={eyeW} height={Math.max(6, eyeH * eyeOpen)} rx={Math.min(eyeW / 2, eyeH * eyeOpen / 2)} fill={DM.orange}/>;
  const leftKind = expression === 'happy' ? 'arc' : 'open';
  const rightKind = expression === 'happy' || expression === 'wink' ? 'arc' : 'open';

  const arm = (shoulderX: number, angle: number) => <g transform={`rotate(${angle} ${shoulderX} 330)`}>
    <rect x={shoulderX - 15} y={322} width={30} height={104} rx={15} fill={DM.ivoryShade}/>
    <circle cx={shoulderX} cy={432} r={23} fill={DM.ivory}/>
  </g>;

  return <svg width={size} height={size * VB.h / VB.w} viewBox={`${VB.x} ${VB.y} ${VB.w} ${VB.h}`} style={{overflow: 'visible', display: 'block'}}>
    <defs>
      <linearGradient id="mimoHead" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#fbf7ef"/><stop offset="1" stopColor={DM.ivoryShade}/></linearGradient>
      <linearGradient id="mimoBody" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={DM.ivory}/><stop offset="1" stopColor="#d8d0bf"/></linearGradient>
      <radialGradient id="mimoGlow"><stop offset="0" stopColor={DM.orange} stopOpacity=".55"/><stop offset="1" stopColor={DM.orange} stopOpacity="0"/></radialGradient>
      <linearGradient id="mimoScreen" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#24242a"/><stop offset="1" stopColor="#141417"/></linearGradient>
      <filter id="mimoBloom" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation={6 * g + .01}/></filter>
    </defs>
    <ellipse cx={200} cy={512} rx={130 * (1 + squash * .15)} ry={16} fill="#000" opacity={.38}/>
    <g transform={`translate(200 500) scale(${sx} ${sy}) translate(-200 -500)`}>
      {/* legs */}
      <rect x={140} y={410} width={44} height={90} rx={20} fill={DM.ivorySoft}/>
      <rect x={216} y={410} width={44} height={90} rx={20} fill={DM.ivorySoft}/>
      {arm(112, leftArm)}
      {/* body */}
      <rect x={112} y={286} width={176} height={150} rx={56} fill="url(#mimoBody)"/>
      <rect x={160} y={326} width={80} height={52} rx={16} fill={DM.orange}/>
      <text x={200} y={362} textAnchor="middle" fontFamily={FONT.mono} fontWeight={700} fontSize={30} fill={DM.charcoal}>{'</>'}</text>
      {/* head */}
      <g transform={`translate(0 ${bob})`}>
        <g transform={`rotate(${Math.sin(t * 2 * Math.PI * .6) * 6} 200 46)`}>
          <line x1={200} y1={46} x2={200} y2={-6} stroke={DM.ivorySoft} strokeWidth={9} strokeLinecap="round"/>
          <circle cx={200} cy={-22} r={46} fill="url(#mimoGlow)" opacity={bulb * g}/>
          <circle cx={200} cy={-22} r={17} fill={DM.orange}/>
          <circle cx={194} cy={-28} r={5} fill="#ffd2a8"/>
        </g>
        <rect x={36} y={140} width={22} height={70} rx={10} fill={DM.ivorySoft}/>
        <rect x={342} y={140} width={22} height={70} rx={10} fill={DM.ivorySoft}/>
        <rect x={52} y={40} width={296} height={258} rx={92} fill="url(#mimoHead)"/>
        <rect x={86} y={84} width={228} height={172} rx={64} fill="url(#mimoScreen)"/>
        <rect x={104} y={96} width={120} height={12} rx={6} fill="#ffffff" opacity={.06}/>
        <g transform={`translate(${lx} ${ly})`}>
          <g filter="url(#mimoBloom)" opacity={.85 * Math.min(1, g)}>{eye(162, 160, leftKind)}{eye(238, 160, rightKind)}</g>
          {eye(162, 160, leftKind)}{eye(238, 160, rightKind)}
          <ellipse cx={122} cy={212} rx={17} ry={9} fill={DM.orange} opacity={.28}/>
          <ellipse cx={278} cy={212} rx={17} ry={9} fill={DM.orange} opacity={.28}/>
          {talking
            ? <rect x={200 - (30 - mouth * 8) / 2} y={214 - mouth * 10} width={30 - mouth * 8} height={8 + mouth * 22} rx={(8 + mouth * 22) / 2.2} fill={DM.orange}/>
            : expression === 'surprised'
              ? <ellipse cx={200} cy={220} rx={11} ry={13} fill={DM.orange}/>
              : <path d={expression === 'focused' ? 'M 186 220 L 214 220' : 'M 182 213 Q 200 232 218 213'} fill="none" stroke={DM.orange} strokeWidth={8} strokeLinecap="round"/>}
        </g>
      </g>
      {arm(288, rightArm)}
    </g>
  </svg>;
};
