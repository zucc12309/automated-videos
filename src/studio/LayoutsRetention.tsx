import React from 'react';
import {interpolate, OffthreadVideo, spring, staticFile, useCurrentFrame} from 'remotion';
import {LayoutProps, Panel, cl} from './kit';
import {DrawPath, FlowDot, progress} from './motion';
import {FONT, STAGE, clampText, hueOf} from './tokens';

/* Retention layouts (V2.1), from review notes on a generated reel:
   - the first two seconds must land a bold, complete statement (readable on frame 0, then a punch)
   - fewer static cards: things scroll, connect and transform while the narrator talks
   - phone-size type: body >= 40 px, labels >= 28 px at 1080 px width
   - a memorable ending: fast recap, then one big call to action that loops back to the hook */

const repoFor = (p: LayoutProps) => (p.scene.item ?? 0) > 0 ? p.props.repos?.[(p.scene.item ?? 1) - 1] : undefined;

/** Hook: one bold statement, fully visible at frame 0. The count slams in, the payoff word gets a drawn underline,
    and the items' avatars fly in underneath as proof that a list is coming. */
export const HookBold: React.FC<LayoutProps> = ({scene, props, P}) => {
  const f = useCurrentFrame();
  const text = clampText(scene.heading || props.title, 46);
  const words = text.split(' ');
  const size = text.length > 30 ? 104 : 124;
  const slam = spring({frame: f + 6, fps: 30, config: {damping: 9, stiffness: 220, mass: .7}});     // already mid-slam on frame 0
  const line = progress(f, {delay: 10, duration: 14});
  const repos = props.repos ?? [];
  const count = props.scenes.filter(s => (s.item ?? 0) > 0).length;
  const accentAt = words.findIndex(w => /\d/.test(w));
  return <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 44}}>
    <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: size, lineHeight: .98, letterSpacing: -size * .035, color: P.ink,
      transform: `scale(${1.08 - .08 * slam})`, transformOrigin: 'left center'}}>
      {words.map((w, i) => <span key={i} style={{display: 'inline-block', marginRight: size * .24, position: 'relative',
        color: i === accentAt || (accentAt < 0 && i === 0) ? P.accent : P.ink}}>
        {w}
        {i === words.length - 1 && <span style={{position: 'absolute', left: 0, bottom: -10, height: 14, width: `${line * 100}%`, borderRadius: 7, background: P.accent}}/>}
      </span>)}
    </div>
    {count > 0 && <div style={{display: 'flex', gap: 22}}>
      {Array.from({length: count}, (_, i) => {
        const s = spring({frame: f - 8 - i * 4, fps: 30, config: {damping: 12, stiffness: 180}});
        const name = repos[i]?.name ?? props.scenes.find(x => x.item === i + 1)?.label ?? `${i + 1}`;
        return <div key={i} style={{width: 150, height: 150, borderRadius: 40, background: `hsl(${hueOf(name)} 62% 52%)`, display: 'grid', placeItems: 'center',
          color: '#fff', fontFamily: FONT.sans, fontWeight: 900, fontSize: 60, transform: `translateY(${(1 - s) * 220}px) rotate(${(1 - s) * (i % 2 ? 24 : -24)}deg)`,
          opacity: Math.min(1, s * 1.5), boxShadow: '0 20px 40px #00000040'}}>{name.replace(/[^a-z0-9]/gi, '').slice(0, 2).toUpperCase()}</div>;
      })}
    </div>}
  </div>;
};

/** The repository README scrolls inside a window while the narrator talks; the line matching the spoken focus is
    highlighted as it passes the reading band. Real README text from the GitHub API only. */
export const ReadmeScroll: React.FC<LayoutProps> = p => {
  const {P, scene, beat, dur} = p;
  const f = useCurrentFrame();
  const repo = repoFor(p);
  const source = (repo?.readme || repo?.description || scene.narration).replace(/\s+/g, ' ');
  const sentences = source.split(/(?<=[.!?])\s+/).filter(s => s.length > 12).slice(0, 9);
  const lines = sentences.length ? sentences : [source];
  const rowH = 128;
  const travel = Math.max(0, lines.length * rowH - 420);
  const y = interpolate(f, [8, Math.max(20, dur)], [0, travel], {...cl, easing: t => t});
  const key = (beat.focus || scene.emphasis || '').toLowerCase().split(/\s+/)[0];
  return <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 22}}>
    <div style={{fontFamily: FONT.mono, fontSize: 30, color: P.muted, letterSpacing: 2}}>{repo ? `${clampText(repo.full_name, 30)} · README` : clampText(scene.heading, 30)}</div>
    <Panel P={P} style={{height: 560, overflow: 'hidden', padding: 0, position: 'relative'}}>
      <div style={{position: 'absolute', left: 0, right: 0, top: 210, height: rowH, background: `${P.accent}22`, borderTop: `3px solid ${P.accent}`, borderBottom: `3px solid ${P.accent}`}}/>
      <div style={{transform: `translateY(${-y + 210}px)`, padding: '0 34px'}}>
        {lines.map((l, i) => {
          const hot = !!key && l.toLowerCase().includes(key);
          return <div key={i} style={{height: rowH, display: 'flex', alignItems: 'center', fontFamily: FONT.sans, fontSize: 42, lineHeight: 1.18,
            fontWeight: hot ? 800 : 560, color: hot ? P.ink : P.muted}}>{clampText(l, 64)}</div>;
        })}
      </div>
      <div style={{position: 'absolute', inset: 0, background: `linear-gradient(180deg, ${P.surface} 0%, ${P.surface}00 18%, ${P.surface}00 82%, ${P.surface} 100%)`}}/>
    </Panel>
  </div>;
};

/** What the tool connects: the repo in the middle, its topics/points as nodes that link in one by one,
    with packets moving along the links (continuous motion for the whole beat). */
export const RepoConnect: React.FC<LayoutProps> = p => {
  const {P, scene} = p;
  const f = useCurrentFrame();
  const repo = repoFor(p);
  const nodes = [...(scene.points ?? []), ...(repo?.topics ?? [])].filter((x, i, a) => x && a.indexOf(x) === i).slice(0, 4);
  const c = {x: STAGE.width / 2, y: STAGE.height / 2};
  const pos = [[150, 110], [STAGE.width - 150, 130], [140, STAGE.height - 110], [STAGE.width - 150, STAGE.height - 120]];
  const hub = spring({frame: f, fps: 30, config: {damping: 14, stiffness: 160}});
  return <div style={{position: 'absolute', inset: 0}}>
    <svg width={STAGE.width} height={STAGE.height} style={{position: 'absolute', inset: 0}}>
      {nodes.map((_, i) => <g key={i}>
        <DrawPath d={`M ${c.x} ${c.y} L ${pos[i][0]} ${pos[i][1]}`} color={P.line} width={7} delay={6 + i * 6}/>
        <FlowDot x1={c.x} y1={c.y} x2={pos[i][0]} y2={pos[i][1]} color={P.accent} delay={18 + i * 6} period={30 + i * 4}/>
      </g>)}
    </svg>
    {nodes.map((n, i) => {
      const e = spring({frame: f - 10 - i * 6, fps: 30, config: {damping: 13, stiffness: 170}});
      return <div key={i} style={{position: 'absolute', left: pos[i][0], top: pos[i][1], transform: `translate(-50%, -50%) scale(${e})`, padding: '20px 28px',
        borderRadius: 26, background: P.surface, border: `3px solid ${P.line}`, fontFamily: FONT.sans, fontWeight: 760, fontSize: 40, color: P.ink, whiteSpace: 'nowrap'}}>
        {clampText(n, 14)}</div>;
    })}
    <div style={{position: 'absolute', left: c.x, top: c.y, transform: `translate(-50%, -50%) scale(${.6 + .4 * hub}) rotate(${(1 - hub) * -8}deg)`, padding: '34px 44px',
      borderRadius: 999, background: P.accent, color: P.bg, fontFamily: FONT.sans, fontWeight: 900, fontSize: 58, whiteSpace: 'nowrap',
      boxShadow: `0 0 ${30 + 20 * Math.sin(f / 8)}px ${P.accent}66`}}>{clampText(repo?.name ?? scene.label ?? scene.heading, 16)}</div>
  </div>;
};

/** Ending: every item ticks off fast, then the stage clears for one big call to action with a pulsing save icon
    and a loop arrow back to the hook. */
export const OutroCTA: React.FC<LayoutProps> = ({props, scene, P, dur}) => {
  const f = useCurrentFrame();
  const items = props.scenes.filter(s => (s.item ?? 0) > 0).map(s => s.label || s.heading);
  const recapEnd = Math.min(Math.max(24, items.length * 6 + 14), Math.max(24, dur * .45));
  const out = progress(f, {delay: recapEnd, duration: 10});
  const cta = spring({frame: f - recapEnd - 4, fps: 30, config: {damping: 10, stiffness: 170, mass: .8}});
  const pulse = 1 + .06 * Math.max(0, Math.sin((f - recapEnd) / 5));
  const line = clampText(scene.heading || 'Save this for later', 34);
  return <div style={{position: 'absolute', inset: 0}}>
    <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 18, opacity: 1 - out,
      transform: `translateY(${-out * 120}px)`}}>
      {items.map((it, i) => {
        const e = progress(f, {delay: i * 6, duration: 8});
        return <div key={i} style={{display: 'flex', alignItems: 'center', gap: 24, opacity: e, transform: `translateX(${(1 - e) * 80}px)`}}>
          <span style={{width: 64, height: 64, borderRadius: 18, background: P.accent, color: P.bg, display: 'grid', placeItems: 'center', fontSize: 40, fontWeight: 900}}>✓</span>
          <span style={{fontFamily: FONT.sans, fontWeight: 820, fontSize: 60, color: P.ink, letterSpacing: -1}}>{clampText(it, 18)}</span>
        </div>;
      })}
    </div>
    {f >= recapEnd && <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'flex-start', gap: 40}}>
      <div style={{width: 170, height: 170, borderRadius: 48, background: P.accent, display: 'grid', placeItems: 'center', transform: `scale(${cta * pulse})`}}>
        <svg width="90" height="110" viewBox="0 0 24 30"><path d="M3 2 H21 V28 L12 21 L3 28 Z" fill={P.bg}/></svg>
      </div>
      <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: line.length > 22 ? 96 : 118, lineHeight: 1, letterSpacing: -4, color: P.ink,
        transform: `translateY(${(1 - cta) * 80}px)`, opacity: Math.min(1, cta * 1.4)}}>{line}</div>
      <div style={{display: 'flex', alignItems: 'center', gap: 16, fontFamily: FONT.mono, fontSize: 32, color: P.muted, opacity: progress(f, {delay: recapEnd + 14, duration: 10})}}>
        <svg width="44" height="44" viewBox="0 0 24 24" style={{transform: `rotate(${(f - recapEnd) * 6}deg)`}}>
          <path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5" fill="none" stroke={P.accent} strokeWidth="2.6" strokeLinecap="round"/></svg>
        watch it again
      </div>
    </div>}
  </div>;
};

/** An imported motion-graphics clip (e.g. exported from Claude's motion tools or any editor), shown full-stage and
    unmodified; captions still run over it. */
export const MotionClip: React.FC<LayoutProps> = ({scene, P, dur}) => {
  const media = scene.media;
  const rate = scene.mediaSeconds ? Math.max(.5, Math.min(1, scene.mediaSeconds / Math.max(.1, dur / 30))) : 1;
  return <div style={{position: 'absolute', left: -STAGE.left, top: -STAGE.top, width: 1080, height: 1920, background: P.bg}}>
    {media && <OffthreadVideo src={staticFile(media)} muted playbackRate={rate} style={{width: '100%', height: '100%', objectFit: 'cover'}}/>}
  </div>;
};
