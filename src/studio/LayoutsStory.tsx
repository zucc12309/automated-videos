import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {CountUp} from '../shared';
import {LayoutProps, Marker, Panel, cl} from './kit';
import {FONT, clampText, enter, hueOf} from './tokens';

/** Hook: the promise is fully readable on frame 0 (no fade-in), with the list teased as fanned cards. */
export const HookStack: React.FC<LayoutProps> = ({scene, props, P, v}) => {
  const f = useCurrentFrame();
  const count = props.scenes.filter(s => (s.item ?? 0) > 0).length;
  const repos = props.repos ?? [];
  const title = clampText(scene.heading || props.title, 40);
  return <div style={{position: 'absolute', inset: 0}}>
    <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: title.length > 26 ? 84 : 104, lineHeight: 1.02, letterSpacing: -3, color: P.ink}}>
      {title.split(' ').map((w, i) => <span key={i} style={{display: 'inline-block', marginRight: 22, color: /\d/.test(w) || i === 0 ? P.accent : P.ink}}>{w}</span>)}
    </div>
    <div style={{position: 'absolute', left: 0, right: 0, top: 330, height: 360}}>
      {Array.from({length: Math.max(count, 1)}, (_, i) => {
        const spread = i - (Math.max(count, 1) - 1) / 2;
        const e = Math.max(.7, enter(f, i * 3, 'snappy'));   // already on screen at frame 0
        const name = repos[i]?.name ?? props.scenes.find(s => s.item === i + 1)?.label ?? '';
        return <Panel key={i} P={P} style={{position: 'absolute', left: 300 + spread * 150, top: Math.abs(spread) * 22, width: 250, height: 320, padding: 22, boxSizing: 'border-box',
          transform: `rotate(${spread * 8 * e}deg) translateY(${(1 - e) * 120}px)`, display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
          background: i === count - 1 ? P.accent : P.surface, borderColor: i === count - 1 ? P.accent : P.line}}>
          <span style={{fontFamily: FONT.mono, fontSize: 22, color: i === count - 1 ? P.bg : P.muted}}>#{i + 1}</span>
          <span style={{fontFamily: FONT.serif, fontStyle: 'italic', fontSize: 140, lineHeight: 1, color: i === count - 1 ? P.bg : P.ink, textAlign: 'center',
            filter: f < 24 + i * 6 && name ? 'blur(0px)' : undefined}}>{i + 1}</span>
          <span style={{height: 14, borderRadius: 7, background: name ? `hsl(${hueOf(name)} 55% 60%)` : P.line, width: `${interpolate(f, [10 + i * 4, 30 + i * 4], [20, 100], cl)}%`}}/>
        </Panel>;
      })}
    </div>
  </div>;
};

/** Document with a big "FACT No. n" stamp; the stat (if any) circled. */
export const DocStamp: React.FC<LayoutProps> = ({scene, props, P, v, index}) => {
  const f = useCurrentFrame();
  const e = enter(f, 0, v.temperament);
  const stamp = enter(f, 16, 'snappy');
  const series = (props.series || 'FACTS').replace(/S$/, '');
  return <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center'}}>
    <div style={{position: 'relative', width: '100%'}}>
      <div style={{position: 'absolute', top: -130, left: -6, zIndex: 2, fontFamily: FONT.serif, fontStyle: 'italic', fontSize: 170, color: P.accent, lineHeight: 1,
        transform: `scale(${1.8 - stamp * .8}) rotate(-5deg)`, transformOrigin: 'left bottom', opacity: Math.min(1, stamp * 1.4)}}>
        <span style={{fontFamily: FONT.sans, fontStyle: 'normal', fontWeight: 900, fontSize: 58, color: P.ink, letterSpacing: 2, verticalAlign: 'top'}}>{series} </span>No. {scene.item ?? index}
      </div>
      <Panel P={P} style={{padding: '110px 40px 40px', transform: `rotate(${index % 2 ? 1.5 : -1.5}deg) translateY(${(1 - e) * 120}px)`, opacity: Math.min(1, e * 1.5)}}>
        <div style={{fontFamily: FONT.serif, fontSize: 60, lineHeight: 1.1, color: P.ink}}>{clampText(scene.heading, 40)}</div>
        {scene.stat && <div style={{position: 'relative', display: 'inline-block', fontFamily: FONT.serif, fontStyle: 'italic', fontSize: 120, color: P.accent, marginTop: 10}}>
          <CountUp stat={scene.stat} delay={8} duration={30}/><Marker at={36} width={520} height={160} color={P.accent}/></div>}
        {scene.points.slice(0, 2).map((pt, i) => {
          const sweep = interpolate(f, [18 + i * 8, 30 + i * 8], [0, 100], cl);
          return <div key={i} style={{fontFamily: FONT.sans, fontSize: 40, color: P.ink, padding: '14px 0', borderTop: `2px solid ${P.line}`}}>
            <span style={{backgroundImage: `linear-gradient(90deg, ${P.hl}${P.dark ? '55' : ''} ${sweep}%, transparent ${sweep}%)`, padding: '0 6px'}}>{clampText(pt, 34)}</span>
          </div>;
        })}
      </Panel>
    </div>
  </div>;
};

/** Recap: every item ticks off. */
export const Recap: React.FC<LayoutProps> = ({props, P, v}) => {
  const f = useCurrentFrame();
  const items = props.scenes.filter(s => (s.item ?? 0) > 0).map(s => s.label || s.heading);
  return <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 16}}>
    <div style={{fontFamily: FONT.mono, fontSize: 28, color: P.muted, letterSpacing: 4}}>RECAP · SAVE THIS</div>
    {items.map((it, i) => {
      const e = enter(f, 2 + i * 4, v.temperament);
      return <div key={i} style={{display: 'flex', alignItems: 'center', gap: 26, padding: '18px 0', borderBottom: `3px solid ${P.line}`, opacity: e, transform: `translateX(${(1 - e) * 60}px)`}}>
        <span style={{width: 58, height: 58, borderRadius: 16, background: P.accent, color: P.bg, display: 'grid', placeItems: 'center', fontSize: 34, fontWeight: 900}}>✓</span>
        <span style={{fontFamily: FONT.sans, fontWeight: 800, fontSize: 52, color: P.ink}}>{clampText(it, 22)}</span>
      </div>;
    })}
  </div>;
};
