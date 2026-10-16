import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {ensureFonts, ID} from '../premium/tokens';
import {Backdrop} from './Backdrop';
import {DM, FONT, io, sp} from './theme';

/* DevMimo logo: the mark is the brand character (identity.json) between code brackets; the wordmark is "Dev" in ink + "Mimo" in
   the accent, Figtree 900 (FIELDNOTES premium tokens). `LogoReveal` is the reusable 5 s animation (150
   frames at 30 fps); the outro of the intro plays the same component. */

const P = ID.palette;
const BAND = 79 * (1 - ID.proportions.band_height);
const BODY = 'M0,34 A34,34 0 0 1 34,0 L66,0 A34,34 0 0 1 100,34 L100,64 A15,15 0 0 1 85,79 L15,79 A15,15 0 0 1 0,64 Z';

/** The mark is the brand character itself (identity.json): marshmallow body, base band, pill eyes, cheeks. */
export const LogoMark: React.FC<{size: number; eyes?: number; happy?: boolean; glow?: number}> = ({size, eyes = 1, happy = false, glow = 1}) => {
  const open = Math.max(.1, eyes);
  const eye = (cx: number) => happy
    ? <path d={`M${cx - 4.2},38.5 Q${cx},32 ${cx + 4.2},38.5`} stroke={P.eye} strokeWidth={2.6} fill="none" strokeLinecap="round"/>
    : <rect x={cx - 3.5} y={37 - 7.75 * open} width={7} height={15.5 * open} rx={3.5} fill={P.eye}/>;
  return <svg width={size} height={size} viewBox="-10 -20 120 120" style={{overflow: 'visible', display: 'block'}}>
    <defs>
      <radialGradient id="lmGlow"><stop offset="0" stopColor={DM.orange} stopOpacity=".45"/><stop offset="1" stopColor={DM.orange} stopOpacity="0"/></radialGradient>
      <clipPath id="lmClip"><path d={BODY}/></clipPath>
    </defs>
    <circle cx={50} cy={40} r={70} fill="url(#lmGlow)" opacity={glow * .8}/>
    <ellipse cx={50} cy={85} rx={36} ry={4} fill={P.shadow}/>
    <path d={BODY} fill={P.body}/>
    <rect x={0} y={BAND} width={100} height={79 - BAND} fill={P.band} clipPath="url(#lmClip)"/>
    {eye(41)}{eye(59)}
    <ellipse cx={28} cy={BAND + 1} rx={5.2} ry={2.6} fill={P.cheek}/>
    <ellipse cx={72} cy={BAND + 1} rx={5.2} ry={2.6} fill={P.cheek}/>
  </svg>;
};

const Bracket: React.FC<{side: 'l' | 'r'; size: number}> = ({side, size}) =>
  <svg width={size * .42} height={size} viewBox="0 0 100 240" style={{display: 'block', overflow: 'visible'}}>
    <path d={side === 'l' ? 'M 78 40 L 22 120 L 78 200' : 'M 22 40 L 78 120 L 22 200'} fill="none" stroke={DM.orange} strokeWidth={22} strokeLinecap="round" strokeLinejoin="round"/>
  </svg>;

const WORD = [...'Dev'].map(c => ({c, color: DM.ivory})).concat([...'Mimo'].map(c => ({c, color: DM.orange})));

/** Reusable logo animation. `f` is the local frame (0..150). Lays itself out centred in a 1080-wide box. */
export const LogoReveal: React.FC<{f: number; scale?: number; tagline?: string; showTagline?: boolean}> = ({f, scale = 1, tagline = 'REAL BUILDS, EXPLAINED', showTagline = true}) => {
  ensureFonts();
  const mark = 240 * scale;
  const bracketIn = sp(f, 0, 14, 170);
  const markIn = sp(f, 12, 9, 160);
  const apart = io(f, 38, 54);
  const eyes = io(f, 26, 32) * (f >= 98 && f < 104 ? 0 : 1);
  const ring = io(f, 30, 52);
  const lift = io(f, 38, 58) * 150 * scale;
  const typed = Math.floor(io(f, 62, 92, 0, tagline.length, t => t));
  const sweep = io(f, 58, 76);
  const gap = (70 + apart * 36) * scale;
  return <div style={{position: 'relative', width: 1080, height: 760 * scale, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
    <div style={{position: 'absolute', top: 260 * scale - lift, left: 0, right: 0, display: 'flex', justifyContent: 'center', alignItems: 'center'}}>
      {/* impact ring */}
      <div style={{position: 'absolute', width: mark * (1 + ring * 2.4), height: mark * (1 + ring * 2.4), borderRadius: '50%',
        border: `${6 * scale}px solid ${DM.orange}`, opacity: f >= 30 ? (1 - ring) * .8 : 0}}/>
      <div style={{position: 'absolute', transform: `translateX(${-(gap + mark * .21) * bracketIn - (1 - bracketIn) * 700}px)`, opacity: Math.min(1, bracketIn * 2) * (1 - apart * .0)}}><Bracket side="l" size={mark}/></div>
      <div style={{position: 'absolute', transform: `translateX(${(gap + mark * .21) * bracketIn + (1 - bracketIn) * 700}px)`, opacity: Math.min(1, bracketIn * 2)}}><Bracket side="r" size={mark}/></div>
      <div style={{transform: `scale(${markIn}) rotate(${(1 - markIn) * -25}deg)`}}><LogoMark size={mark} eyes={eyes} happy={f >= 104 && f < 122}/></div>
    </div>
    <div style={{position: 'absolute', top: 470 * scale - lift * .35, display: 'flex', fontFamily: FONT.sans, fontWeight: 900, fontSize: 168 * scale, letterSpacing: '-0.035em', lineHeight: 1}}>
      {WORD.map((ch, i) => {
        const k = sp(f, 40 + i * 3, 13, 180);
        return <span key={i} style={{color: ch.color, display: 'inline-block', transform: `translateY(${(1 - k) * 90 * scale}px)`, opacity: Math.min(1, k * 1.6)}}>{ch.c}</span>;
      })}
    </div>
    <div style={{position: 'absolute', top: 470 * scale + 186 * scale - lift * .35, height: 10 * scale, width: 640 * scale * sweep, background: DM.orange, borderRadius: 6 * scale}}/>
    {showTagline && <div style={{position: 'absolute', top: 470 * scale + 226 * scale - lift * .35, fontFamily: FONT.mono, fontWeight: 500, fontSize: 38 * scale,
      letterSpacing: '0.18em', color: DM.ivorySoft, whiteSpace: 'nowrap'}}>
      {tagline.slice(0, typed)}<span style={{opacity: f >= 62 && Math.floor(f / 8) % 2 === 0 ? 1 : 0, color: DM.orange}}>▍</span>
    </div>}
  </div>;
};

/** 5 s logo sting: 150 frames, 1080x1920. */
export const DevMimoLogo: React.FC = () => {
  const f = useCurrentFrame();
  const flash = f >= 30 && f < 36 ? io(f, 30, 36, .12, 0) : 0;
  const out = io(f, 138, 150);
  return <AbsoluteFill style={{background: DM.charcoal}}>
    <Backdrop f={f} intensity={io(f, 20, 60) * .9}/>
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', transform: `scale(${1 + f * .0006})`}}>
      <div style={{marginTop: 120}}><LogoReveal f={f}/></div>
    </AbsoluteFill>
    <AbsoluteFill style={{background: DM.orange, opacity: flash, mixBlendMode: 'screen'}}/>
    <AbsoluteFill style={{background: DM.charcoal, opacity: out}}/>
  </AbsoluteFill>;
};
