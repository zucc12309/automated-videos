import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {Beat, Scene, Word} from '../shared';
import {CAPTION_Y, FONT, Palette, SAFE, Variant} from './tokens';

/** Seeded background treatment; `shift` gives a slow parallax drift against the camera. */
export const Backdrop: React.FC<{P: Palette; kind: string; shift: {x: number; y: number}}> = ({P, kind, shift}) => {
  const f = useCurrentFrame();
  const drift = `translate(${shift.x * .25 + Math.sin(f / 90) * 6}px, ${shift.y * .25 + Math.cos(f / 110) * 6}px)`;
  const layer: React.CSSProperties = {position: 'absolute', inset: -80, transform: drift};
  const ink = P.dark ? '#ffffff' : '#000000';
  return <AbsoluteFill style={{background: P.bg, overflow: 'hidden'}}>
    {kind === 'dots' && <div style={{...layer, backgroundImage: `radial-gradient(${ink}1c 3px, transparent 3.5px)`, backgroundSize: '44px 44px'}}/>}
    {kind === 'grid' && <div style={{...layer, backgroundImage: `linear-gradient(${ink}12 2px, transparent 2px), linear-gradient(90deg, ${ink}12 2px, transparent 2px)`, backgroundSize: '90px 90px'}}/>}
    {kind === 'lines' && <div style={{...layer, backgroundImage: `repeating-linear-gradient(-35deg, ${ink}0d 0 3px, transparent 3px 46px)`}}/>}
    {kind === 'mesh' && <div style={{...layer, background: `radial-gradient(ellipse at ${30 + Math.sin(f / 70) * 10}% 20%, ${P.accent}38 0%, transparent 45%), radial-gradient(ellipse at 80% ${70 + Math.cos(f / 80) * 10}%, ${P.accent2}30 0%, transparent 50%), ${P.bg}`}}/>}
    {(kind === 'grain' || kind === 'mesh') && <svg width="1080" height="1920" style={{position: 'absolute', opacity: P.dark ? .18 : .3, mixBlendMode: P.dark ? 'screen' : 'multiply'}}>
      <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 .45  0 0 0 0 .4  0 0 0 0 .33  0 0 0 .55 0"/></filter>
      <rect width="1080" height="1920" filter="url(#grain)"/>
    </svg>}
    <AbsoluteFill style={{background: `radial-gradient(ellipse at 50% 38%, transparent 50%, ${P.dark ? '#00000070' : '#7a6a5520'} 100%)`}}/>
  </AbsoluteFill>;
};

const chunkOf = (words: Word[], i: number) => {
  // 2-4 word chunks, breaking at punctuation.
  let start = 0;
  for (let k = 0; k < words.length; k++) {
    if (/[.,!?;:—]$/.test(words[k].w) || k - start >= 3 || k === words.length - 1) {
      if (i <= k) return [start, k];
      start = k + 1;
    }
  }
  return [start, words.length - 1];
};

/** Word-timed captions in one of three seeded styles, inside the caption safe band. */
export const Captions: React.FC<{scene: Scene; beat?: Beat; local: number; P: Palette; v: Variant}> = ({scene, local, P, v}) => {
  const words = scene.words ?? [];
  const t = local / 30 + .03;
  let active = -1;
  words.forEach((w, i) => { if (w.s <= t) active = i; });
  if (active < 0 || t > (words[words.length - 1]?.e ?? 0) + .4) return null;
  const [a, b] = chunkOf(words, active);
  const emphasis = (scene.emphasis ?? '').toLowerCase().split(/\s+/);
  const style = v.captions;
  const pop = interpolate(t - words[a].s, [0, .12], [.9, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  // Anchored to the safe-area bottom so a two-line chunk grows upward and never enters the platform UI zone.
  return <div style={{position: 'absolute', left: SAFE.left, right: 1080 - SAFE.right, bottom: 1920 - SAFE.bottom, minHeight: SAFE.bottom - CAPTION_Y, display: 'flex', justifyContent: 'center', alignItems: 'flex-start'}}>
    <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: style === 'bold' ? 16 : 12, padding: style === 'pill' ? '14px 26px' : 0, borderRadius: 30,
      background: style === 'pill' ? (P.dark ? '#000000a8' : '#fffdf8e8') : undefined, transform: `scale(${pop})`}}>
      {words.slice(a, b + 1).map((w, k) => {
        const i = a + k, on = i === active, said = i <= active;
        const key = emphasis.includes(w.w.toLowerCase().replace(/[^\w$%]/g, ''));
        if (style === 'bold') return <span key={i} style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: 76, textTransform: 'uppercase', letterSpacing: -1,
          color: on ? P.hl : '#ffffff', WebkitTextStroke: '10px #111', paintOrder: 'stroke fill', opacity: said ? 1 : .35, transform: `scale(${on ? 1.08 : 1})`, display: 'inline-block'} as React.CSSProperties}>{w.w}</span>;
        if (style === 'pill') return <span key={i} style={{fontFamily: FONT.sans, fontWeight: 750, fontSize: 64, color: on ? P.bg : P.ink, background: on ? P.accent : 'transparent',
          borderRadius: 14, padding: '0 10px', opacity: said ? 1 : .4}}>{w.w}</span>;
        return <span key={i} style={{fontFamily: key ? FONT.serif : FONT.sans, fontStyle: key ? 'italic' : 'normal', fontWeight: key ? 400 : 650, fontSize: key ? 76 : 66,
          color: key ? P.accent : P.ink, opacity: said ? 1 : .3, textShadow: `0 0 18px ${P.bg}, 0 0 4px ${P.bg}`}}>{w.w}</span>;
      })}
    </div>
  </div>;
};
