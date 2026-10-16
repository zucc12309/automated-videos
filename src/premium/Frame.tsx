import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {Word} from '../shared';
import {C, EASE, F, GUTTER, HEADLINE_Y, T, W, clamp01} from './tokens';

/** Publication chrome: ground with a soft centre lift, film grain, masthead, scene counter and hairline progress. */
export const Ground: React.FC<{frame: number}> = ({frame}) => <AbsoluteFill style={{background: C.ground, overflow: 'hidden'}}>
  <AbsoluteFill style={{background: `radial-gradient(ellipse 70% 45% at 50% 48%, ${C.groundLift} 0%, ${C.ground} 70%)`}}/>
  {T.frame.grain > 0 && <svg width={W} height={1920} style={{position: 'absolute', opacity: T.frame.grain * 2.2, mixBlendMode: 'screen'}}>
    <filter id="pgrain"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves={2} seed={Math.floor(frame / 2) % 7} stitchTiles="stitch"/>
      <feColorMatrix values="0 0 0 0 .5  0 0 0 0 .5  0 0 0 0 .5  0 0 0 .35 0"/></filter>
    <rect width={W} height={1920} filter="url(#pgrain)"/>
  </svg>}
  <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 45%, transparent 55%, #00000066 100%)'}}/>
</AbsoluteFill>;

export const Masthead: React.FC<{brand: string; series: string; index: number; total: number; progress: number}> = ({brand, series, index, total, progress}) =>
  <>
    <div style={{position: 'absolute', left: GUTTER, right: GUTTER, top: 150, display: 'flex', justifyContent: 'space-between', fontFamily: F.mono,
      fontSize: T.type.masthead, letterSpacing: 6, color: C.dim}}>
      <span>{brand}{series ? <span style={{color: C.muted}}>{`  ·  ${series}`}</span> : null}</span>
      <span><span style={{color: C.muted}}>{String(index).padStart(2, '0')}</span>{` / ${String(total).padStart(2, '0')}`}</span>
    </div>
    <div style={{position: 'absolute', left: GUTTER, right: GUTTER, top: 1690, height: 3, borderRadius: 2, background: C.line}}>
      <div style={{width: `${clamp01(progress) * 100}%`, height: '100%', borderRadius: 2, background: C.accent}}/>
    </div>
  </>;

/** Serif italic word inside a thin selection box with corner handles (the reference's signature emphasis). */
export const Selected: React.FC<{children: React.ReactNode; size: number; p: number}> = ({children, size, p}) => {
  const handle = (s: React.CSSProperties) => <span style={{position: 'absolute', width: size * .12, height: size * .12, background: C.ground,
    border: `2px solid ${C.accent}`, opacity: p, ...s}}/>;
  return <span style={{position: 'relative', display: 'inline-block', padding: `0 ${size * .14}px`, margin: `0 ${size * .06}px`}}>
    <span style={{position: 'absolute', inset: `${size * .04}px 0`, border: `2px solid ${C.accent}`, opacity: p, borderRadius: 2}}/>
    {handle({left: -size * .06, top: -size * .02})}{handle({right: -size * .06, top: -size * .02})}
    {handle({left: -size * .06, bottom: -size * .02})}{handle({right: -size * .06, bottom: -size * .02})}
    <span style={{fontFamily: F.serif, fontStyle: 'italic', fontWeight: 400, fontSize: size * 1.08, letterSpacing: 0}}>{children}</span>
  </span>;
};

const bare = (w: string) => w.toLowerCase().replace(/[^\p{L}\p{N}$%]/gu, '');

/** Kinetic headline at the top: the current phrase resolves word by word from blur as it is spoken; spoken words settle
    to grey, the latest word stays ivory, the emphasis word becomes serif italic in a selection box. Two lines max. */
export const Headline: React.FC<{words: Word[]; t: number; emphasis: string; size?: number; hidden?: boolean}> = ({words, t, emphasis, size = T.type.headline, hidden}) => {
  if (hidden || !words.length) return null;
  // Page the scene's words into chunks that fit two lines (~26 chars/line at 60 px), breaking after punctuation.
  const pages: [number, number][] = [];
  let start = 0, chars = 0;
  words.forEach((w, i) => {
    chars += w.w.length + 1;
    const last = i === words.length - 1;
    if (last || chars > 44 || (chars > 22 && /[.!?;:]$/.test(w.w))) { pages.push([start, i]); start = i + 1; chars = 0; }
  });
  let active = -1;
  words.forEach((w, i) => { if (w.s <= t + .02) active = i; });
  const page = pages.find(([a, b]) => active >= a && active <= b) ?? (active < 0 ? pages[0] : pages[pages.length - 1]);
  if (!page) return null;
  const keys = emphasis.toLowerCase().split(/\s+/).map(bare).filter(Boolean);
  const [a, b] = page;
  return <div style={{position: 'absolute', left: GUTTER, right: GUTTER, top: HEADLINE_Y, display: 'flex', flexWrap: 'wrap', justifyContent: 'center',
    columnGap: size * .26, rowGap: size * .12, fontFamily: F.sans, fontWeight: 600, fontSize: size, lineHeight: 1.12, letterSpacing: -size * .015, textAlign: 'center'}}>
    {words.slice(a, b + 1).map((w, k) => {
      const i = a + k;
      const p = clamp01(interpolate(t, [w.s - .06, w.s + .18], [0, 1], {easing: EASE.enter, extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
      const latest = i === active || (i === b && active > b);
      const color = !latest && i < active ? C.muted : C.ink;
      const key = keys.includes(bare(w.w));
      return <span key={i} style={{display: 'inline-block', color, opacity: p, filter: `blur(${(1 - p) * T.motion.blur.enter * .6}px)`,
        transform: `translateY(${(1 - p) * 10}px)`}}>
        {key ? <Selected size={size} p={p}>{w.w}</Selected> : w.w}
      </span>;
    })}
  </div>;
};
