import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {CountUp, splitStat} from '../shared';
import {LayoutProps, Marker, Panel, cl} from './kit';
import {FONT, STAGGER, clampText, enter, punch} from './tokens';

/** One giant word: the beat's focus, revealed letter by letter through a mask. */
export const HeroWord: React.FC<LayoutProps> = ({beat, scene, P, v, hit}) => {
  const f = useCurrentFrame();
  const word = clampText(beat.focus.replace(/[.,!?;:]$/, ''), 22);
  const longest = Math.max(4, ...word.split(' ').map(w => w.length));
  const size = Math.max(96, Math.min(250, 1380 / longest));
  const k = punch(f, hit ?? -99);
  return <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
    <div style={{fontFamily: FONT.mono, fontSize: 26, color: P.muted, letterSpacing: 3, opacity: enter(f, 0, v.temperament)}}>// {clampText(scene.heading.toLowerCase(), 34)}</div>
    <div style={{display: 'flex', flexWrap: 'wrap', columnGap: size * .28, marginTop: 12, transform: `scale(${k})`, transformOrigin: 'left center'}}>
      {word.split(' ').map((part, wi, parts) => {
        const offset = parts.slice(0, wi).join(' ').length + (wi ? 1 : 0);
        return <span key={wi} style={{display: 'inline-flex', whiteSpace: 'nowrap'}}>{part.split('').map((ch, ci) => {
          const i = offset + ci;
          const p = enter(f, 2 + i * 1.5, v.temperament);
          return <span key={ci} style={{display: 'inline-block', overflow: 'hidden', height: size * 1.12}}>
            <span style={{display: 'inline-block', fontFamily: v.temperament === 'editorial' ? FONT.serif : FONT.sans, fontStyle: v.temperament === 'editorial' ? 'italic' : 'normal',
              fontWeight: 800, fontSize: size, lineHeight: 1.05, letterSpacing: -size * .03, color: i === 0 ? P.accent : P.ink, transform: `translateY(${(1 - p) * 110}%)`}}>{ch}</span>
          </span>;
        })}</span>;
      })}
    </div>
    <div style={{height: 14, width: `${interpolate(f, [8, 22], [0, 62], cl)}%`, background: P.hl, borderRadius: 7, marginTop: 18}}/>
  </div>;
};

/** A number that counts up, circled with a marker; stars or any stat. */
export const BigNumber: React.FC<LayoutProps> = ({beat, scene, P, v, props}) => {
  const f = useCurrentFrame();
  const item = scene.item ?? 0;
  const repo = item > 0 ? props.repos?.[item - 1] : undefined;
  const raw = splitStat(beat.focus) ? beat.focus : scene.stat || (repo ? repo.stars.toLocaleString('en-US') : beat.focus);
  const label = repo && !splitStat(beat.focus) ? 'GitHub stars' : scene.heading;
  const p = enter(f, 0, v.temperament);
  return <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'flex-start'}}>
    <div style={{fontFamily: FONT.mono, fontSize: 26, color: P.muted, letterSpacing: 4, textTransform: 'uppercase'}}>{clampText(label, 30)}</div>
    <div style={{position: 'relative', marginTop: 10, fontFamily: v.temperament === 'snappy' ? FONT.sans : FONT.serif, fontWeight: v.temperament === 'snappy' ? 900 : 400,
      fontStyle: v.temperament === 'snappy' ? 'normal' : 'italic', fontSize: raw.length > 8 ? 170 : 230, lineHeight: 1, color: P.ink, letterSpacing: -6,
      transform: `scale(${.82 + p * .18})`, transformOrigin: 'left bottom', opacity: Math.min(1, p * 1.6)}}>
      {splitStat(raw) ? <CountUp stat={raw} delay={4} duration={30}/> : raw}
      <Marker at={24} width={raw.length * 120 + 80} height={260} color={P.accent}/>
    </div>
    <div style={{display: 'flex', gap: 10, marginTop: 34}}>
      {Array.from({length: 12}, (_, i) => <span key={i} style={{width: 46, height: 14, borderRadius: 7, background: i < interpolate(f, [10, 40], [0, 12], cl) ? P.accent : P.line}}/>)}
    </div>
  </div>;
};

/** The spoken line as a pull quote; the focus phrase gets a highlighter sweep. */
export const Quote: React.FC<LayoutProps> = ({beat, P, v}) => {
  const f = useCurrentFrame();
  const words = clampText(beat.text, 110).split(' ');
  const focus = beat.focus.toLowerCase().split(/\s+/);
  return <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
    <div style={{fontFamily: FONT.serif, fontSize: 220, lineHeight: .6, color: P.accent, height: 110}}>“</div>
    <div style={{fontFamily: FONT.serif, fontSize: words.length > 14 ? 64 : 78, lineHeight: 1.18, color: P.ink}}>
      {words.map((w, i) => {
        const on = enter(f, i * STAGGER[v.temperament] * .6, v.temperament);
        const key = focus.includes(w.toLowerCase().replace(/[^\w$%.,]/g, '').replace(/[.,]$/, ''));
        const sweep = interpolate(f, [12 + i * 2, 24 + i * 2], [0, 100], cl);
        return <span key={i} style={{display: 'inline-block', marginRight: 18, opacity: on, transform: `translateY(${(1 - on) * 24}px)`,
          backgroundImage: key ? `linear-gradient(90deg, ${P.hl} ${sweep}%, transparent ${sweep}%)` : undefined, padding: key ? '0 6px' : undefined,
          fontStyle: key ? 'italic' : 'normal', color: key && P.dark ? P.bg : P.ink}}>{w}</span>;
      })}
    </div>
  </div>;
};

/** Close-up beat: the character takes the stage (anchor=center); a speech bubble carries the focus word. */
export const MascotCloseup: React.FC<LayoutProps> = ({beat, P, v}) => {
  const f = useCurrentFrame();
  const p = enter(f, 4, v.temperament);
  return <div style={{position: 'absolute', left: 0, right: 0, top: -10, display: 'flex', justifyContent: 'flex-end'}}>
    <div style={{position: 'relative', padding: '26px 40px', background: P.surface, border: `5px solid ${P.ink}`, borderRadius: 40, fontFamily: FONT.sans, fontWeight: 800,
      fontSize: 72, color: P.ink, transform: `scale(${p}) rotate(${(1 - p) * -8 + 2}deg)`, transformOrigin: 'left bottom', boxShadow: `10px 10px 0 ${P.ink}`}}>
      {clampText(beat.focus, 16)}{/[?]$/.test(beat.text) ? '?' : '!'}
      <span style={{position: 'absolute', left: 60, bottom: -34, width: 44, height: 44, background: P.surface, borderRight: `5px solid ${P.ink}`, borderBottom: `5px solid ${P.ink}`, transform: 'rotate(45deg)'}}/>
    </div>
  </div>;
};

/** Points as a cascading stack of cards; the focus row is accented. */
export const ListStack: React.FC<LayoutProps> = ({scene, beat, P, v}) => {
  const f = useCurrentFrame();
  const items = (scene.points.length ? scene.points : [scene.heading]).slice(0, 4);
  return <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 22}}>
    <div style={{fontFamily: FONT.sans, fontWeight: 800, fontSize: 64, color: P.ink, letterSpacing: -1.5, marginBottom: 10}}>{clampText(scene.heading, 34)}</div>
    {items.map((it, i) => {
      const p = enter(f, 4 + i * STAGGER[v.temperament] * 2, v.temperament);
      const hot = beat.text.toLowerCase().includes(it.toLowerCase().split(' ')[0]) || i === 0;
      return <Panel key={i} P={P} style={{display: 'flex', alignItems: 'center', gap: 26, padding: '26px 32px', opacity: Math.min(1, p * 1.5),
        transform: `translateX(${(1 - p) * 120}px) rotate(${(1 - p) * 4}deg)`, borderColor: hot ? P.accent : P.line}}>
        <span style={{width: 64, height: 64, borderRadius: 32, background: hot ? P.accent : P.bg2, color: hot ? P.bg : P.ink, display: 'grid', placeItems: 'center',
          fontFamily: FONT.mono, fontWeight: 800, fontSize: 30}}>{i + 1}</span>
        <span style={{fontFamily: FONT.sans, fontWeight: 650, fontSize: 48, color: P.ink, letterSpacing: -.8}}>{clampText(it, 26)}</span>
      </Panel>;
    })}
  </div>;
};

/** Vertical timeline: a line draws down and nodes light up in order. */
export const Steps: React.FC<LayoutProps> = ({scene, P, v}) => {
  const f = useCurrentFrame();
  const items = (scene.points.length ? scene.points : [scene.heading]).slice(0, 3);
  const line = interpolate(f, [4, 30], [0, 1], cl);
  return <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center'}}>
    <div style={{position: 'relative', width: '100%', height: 560}}>
      <div style={{position: 'absolute', left: 42, top: 40, width: 8, height: 480 * line, borderRadius: 4, background: P.accent}}/>
      {items.map((it, i) => {
        const p = enter(f, 6 + i * 9, v.temperament);
        return <div key={i} style={{position: 'absolute', left: 0, top: 10 + i * 220, display: 'flex', alignItems: 'center', gap: 36}}>
          <span style={{width: 92, height: 92, borderRadius: 46, border: `6px solid ${P.accent}`, background: p > .5 ? P.accent : P.bg, display: 'grid', placeItems: 'center',
            color: P.bg, fontFamily: FONT.sans, fontWeight: 900, fontSize: 40, transform: `scale(${.6 + p * .4})`}}>{i + 1}</span>
          <span style={{fontFamily: FONT.sans, fontWeight: 700, fontSize: 52, color: P.ink, opacity: p, transform: `translateX(${(1 - p) * 40}px)`}}>{clampText(it, 22)}</span>
        </div>;
      })}
    </div>
  </div>;
};

/** Two columns with a VS badge, from the first two points. */
export const Compare: React.FC<LayoutProps> = ({scene, P, v}) => {
  const f = useCurrentFrame();
  const [a, b] = scene.points.length >= 2 ? scene.points : [scene.heading, scene.label || scene.heading];
  const col = (text: string, i: number) => {
    const p = enter(f, 4 + i * 6, v.temperament);
    return <Panel P={P} style={{flex: 1, height: 460, padding: 30, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', opacity: p,
      transform: `translateY(${(1 - p) * 80}px)`, background: i ? P.accent : P.surface, borderColor: i ? P.accent : P.line}}>
      <span style={{fontFamily: FONT.mono, fontSize: 24, color: i ? P.bg : P.muted, letterSpacing: 3}}>{i ? 'NOW' : 'BEFORE'}</span>
      <span style={{fontFamily: FONT.sans, fontWeight: 800, fontSize: 50, lineHeight: 1.1, color: i ? P.bg : P.ink}}>{clampText(text, 40)}</span>
    </Panel>;
  };
  const vs = enter(f, 14, 'snappy');
  return <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', gap: 28}}>
    {col(a, 0)}{col(b, 1)}
    <div style={{position: 'absolute', left: '50%', top: '50%', width: 110, height: 110, borderRadius: 55, background: P.ink, color: P.bg, display: 'grid', placeItems: 'center',
      fontFamily: FONT.sans, fontWeight: 900, fontSize: 38, transform: `translate(-50%, -50%) scale(${vs}) rotate(${(1 - vs) * 90}deg)`}}>VS</div>
  </div>;
};
