import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {CountUp, Repo} from '../shared';
import {LayoutProps, Marker, Panel, cl} from './kit';
import {FONT, STAGGER, clampText, enter, hueOf} from './tokens';

const repoOf = (p: LayoutProps): Repo | undefined => (p.scene.item ?? 0) > 0 ? p.props.repos?.[(p.scene.item ?? 1) - 1] : undefined;

const Avatar: React.FC<{name: string; size: number}> = ({name, size}) =>
  <div style={{width: size, height: size, borderRadius: size * .28, background: `hsl(${hueOf(name)} 60% 52%)`, display: 'grid', placeItems: 'center', color: '#fff',
    fontFamily: FONT.sans, fontWeight: 800, fontSize: size * .4, flexShrink: 0}}>{name.replace(/[^a-z0-9]/gi, '').slice(0, 2).toUpperCase()}</div>;

/** GitHub repo card with real API data: owner/name, description, stars counting up inside a marker loop. */
export const RepoCard: React.FC<LayoutProps> = p => {
  const {P, v, scene} = p;
  const f = useCurrentFrame();
  const repo = repoOf(p);
  if (!repo) return null;
  const e = enter(f, 0, v.temperament);
  return <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center'}}>
    <Panel P={P} style={{width: '100%', padding: '36px 40px', transform: `translateY(${(1 - e) * 140 + Math.sin(f / 22) * 6}px) rotate(${(1 - e) * -5 + (p.index % 2 ? .8 : -.8) + Math.sin(f / 37) * .4}deg)`, opacity: Math.min(1, e * 1.6)}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 24}}>
        <Avatar name={repo.name} size={104}/>
        <div>
          <div style={{fontFamily: FONT.mono, fontSize: 26, color: P.muted}}>github.com/{clampText(repo.owner, 18)}</div>
          <div style={{fontFamily: FONT.sans, fontWeight: 850, fontSize: 64, color: P.ink, letterSpacing: -1.5, lineHeight: 1.05}}>{clampText(repo.name, 18)}</div>
        </div>
      </div>
      <div style={{fontFamily: FONT.sans, fontSize: 46, lineHeight: 1.22, color: P.ink, opacity: .82, marginTop: 26}}>{clampText(repo.description, 70)}</div>
      {repo.topics.length > 0 && <div style={{marginTop: 22, overflow: 'hidden', whiteSpace: 'nowrap', maskImage: 'linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent)'}}>
        <div style={{display: 'inline-flex', gap: 14, transform: `translateX(${-((f * 2.2) % 420)}px)`}}>{[...repo.topics, ...repo.topics, ...repo.topics].map((t, i) =>
          <span key={i} style={{fontFamily: FONT.mono, fontSize: 30, padding: '8px 18px', borderRadius: 24, background: P.bg2, color: P.ink}}>#{clampText(t, 18)}</span>)}</div>
      </div>}
      <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 30}}>
        <div style={{position: 'relative', fontFamily: FONT.sans, fontWeight: 900, fontSize: 76, color: P.ink}}>
          <span style={{color: '#f2b01e'}}>★ </span><CountUp stat={repo.stars.toLocaleString('en-US')} delay={8} duration={34}/>
          <Marker at={40} width={420} height={130} color={P.accent}/>
        </div>
        {repo.language && <span style={{fontFamily: FONT.mono, fontSize: 28, color: P.ink, padding: '10px 20px', borderRadius: 30, background: P.bg2}}>● {repo.language}</span>}
      </div>
      {scene.points[0] && <div style={{marginTop: 24, fontFamily: FONT.sans, fontWeight: 760, fontSize: 44, color: P.accent}}>→ {clampText(scene.points[0], 28)}</div>}
    </Panel>
  </div>;
};

/** Native terminal: real clone command, then points as output lines; one line in focus, the rest dimmed. */
export const Terminal: React.FC<LayoutProps> = p => {
  const {P, v, scene} = p;
  const f = useCurrentFrame();
  const repo = repoOf(p);
  const own = ((scene.visualData?.code as string[] | undefined) ?? []).filter(l => l.trim()).slice(0, 5);
  const lines = own.length ? own.map(l => l.replace(/^\$\s*/, ''))
    : [repo ? `git clone github.com/${repo.full_name}` : clampText(scene.heading.toLowerCase(), 30), ...(scene.points.slice(0, 3).map(x => `✓ ${x}`))];
  const focusLine = Math.min(lines.length - 1, Math.floor(interpolate(f, [0, 60], [0, lines.length], cl)));
  const e = enter(f, 0, v.temperament);
  return <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center'}}>
    <div style={{width: '100%', borderRadius: 26, background: '#111315', border: '3px solid #2a2d31', padding: '26px 30px 34px', boxShadow: '0 30px 70px #00000055',
      transform: `scale(${.9 + e * .1})`, opacity: Math.min(1, e * 1.5)}}>
      <div style={{display: 'flex', gap: 12, marginBottom: 26}}>{['#ff5f57', '#febc2e', '#28c840'].map(c => <span key={c} style={{width: 18, height: 18, borderRadius: 9, background: c}}/>)}</div>
      {lines.map((l, i) => {
        const start = 4 + i * 14;
        const chars = Math.floor(interpolate(f, [start, start + Math.min(24, l.length * .8)], [0, l.length], cl));
        const text = clampText(l, 32);
        return <div key={i} style={{fontFamily: FONT.mono, fontSize: 40, lineHeight: 1.5, color: i === 0 ? '#f2f2ee' : '#9be38f', opacity: f < start ? 0 : i === focusLine ? 1 : .4, whiteSpace: 'nowrap'}}>
          {i === 0 && <span style={{color: P.dark ? P.accent : '#ff8a5c'}}>$ </span>}{text.slice(0, chars)}{i === focusLine && chars < text.length && <span style={{background: '#f2f2ee'}}>&nbsp;</span>}
        </div>;
      })}
    </div>
  </div>;
};

/** Topic chips tumble in around the repo/heading name. */
export const Chips: React.FC<LayoutProps> = p => {
  const {P, v, scene} = p;
  const f = useCurrentFrame();
  const repo = repoOf(p);
  const chips = [...(repo?.topics ?? []), ...scene.points].slice(0, 6);
  return <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 34}}>
    <div style={{fontFamily: FONT.sans, fontWeight: 850, fontSize: 80, color: P.ink, letterSpacing: -2}}>{clampText(repo?.name ?? scene.label ?? scene.heading, 18)}</div>
    <div style={{display: 'flex', flexWrap: 'wrap', gap: 18}}>
      {chips.map((c, i) => {
        const e = enter(f, 3 + i * STAGGER[v.temperament], 'snappy');
        return <span key={i} style={{fontFamily: FONT.sans, fontWeight: 720, fontSize: 46, padding: '16px 28px', borderRadius: 40, background: i % 3 === 0 ? P.accent : P.surface,
          color: i % 3 === 0 ? P.bg : P.ink, border: `3px solid ${i % 3 === 0 ? P.accent : P.line}`, transform: `translateY(${(1 - e) * -200}px) rotate(${(1 - e) * (i % 2 ? 30 : -30) + (i % 2 ? 2 : -2)}deg)`}}>#{clampText(c, 20)}</span>;
      })}
    </div>
  </div>;
};

/** Star comparison across every repo in the roundup (real numbers); the current repo is highlighted. */
export const StarMeter: React.FC<LayoutProps> = p => {
  const {P, v, props, scene} = p;
  const f = useCurrentFrame();
  const repos = props.repos ?? [];
  const max = Math.max(1, ...repos.map(r => r.stars));
  return <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 26}}>
    <div style={{fontFamily: FONT.mono, fontSize: 28, color: P.muted, letterSpacing: 3}}>★ GITHUB STARS</div>
    {repos.map((r, i) => {
      const me = i === (scene.item ?? 0) - 1;
      const w = interpolate(f, [4 + i * 3, 30 + i * 3], [0, r.stars / max], cl);
      return <div key={i} style={{opacity: enter(f, i * 3, v.temperament)}}>
        <div style={{display: 'flex', justifyContent: 'space-between', fontFamily: FONT.sans, fontWeight: me ? 800 : 600, fontSize: 44, color: me ? P.ink : P.muted, marginBottom: 10}}>
          <span>{clampText(r.name, 18)}</span><span>{Math.round(w * max).toLocaleString('en-US')}</span>
        </div>
        <div style={{height: 30, borderRadius: 15, background: P.bg2}}><div style={{height: '100%', width: `${w * 100}%`, borderRadius: 15, background: me ? P.accent : P.line}}/></div>
      </div>;
    })}
  </div>;
};

/** A phone mockup with an app-like screen built from the scene's points; a cursor taps the first row. */
export const DeviceMock: React.FC<LayoutProps> = ({scene, P, v}) => {
  const f = useCurrentFrame();
  const e = enter(f, 0, v.temperament);
  const rows = (scene.points.length ? scene.points : [scene.heading]).slice(0, 3);
  const tap = interpolate(f, [26, 30, 36], [1, .85, 1], cl);
  return <div style={{position: 'absolute', inset: 0, display: 'flex', justifyContent: 'center', alignItems: 'center'}}>
    <div style={{width: 470, height: 690, borderRadius: 64, background: '#0f1012', padding: 16, boxShadow: '0 40px 80px #00000050', transform: `translateY(${(1 - e) * 300}px) rotate(${(1 - e) * 12 - 3}deg)`}}>
      <div style={{width: '100%', height: '100%', borderRadius: 50, background: P.surface, overflow: 'hidden', padding: '60px 28px', boxSizing: 'border-box'}}>
        <div style={{fontFamily: FONT.sans, fontWeight: 850, fontSize: 46, color: P.ink, lineHeight: 1.1}}>{clampText(scene.heading, 26)}</div>
        {rows.map((r, i) => <div key={i} style={{marginTop: 22, padding: '22px 20px', borderRadius: 22, background: i === 0 ? P.accent : P.bg2, color: i === 0 ? P.bg : P.ink,
          fontFamily: FONT.sans, fontWeight: 720, fontSize: 38, transform: `scale(${i === 0 ? tap : 1})`, opacity: enter(f, 6 + i * 4, v.temperament)}}>{clampText(r, 20)}</div>)}
      </div>
    </div>
    <svg width="90" height="90" viewBox="0 0 24 24" style={{position: 'absolute', left: 520, top: interpolate(f, [8, 26], [620, 300], cl), transform: `scale(${tap})`}}>
      <path d="M5 2 L19 13 L12 14 L15 21 L12 22 L9 15 L5 19 Z" fill="#fff" stroke="#111" strokeWidth="1.6" strokeLinejoin="round"/>
    </svg>
  </div>;
};

/** Chat thread: a question from the heading, the answer from the points, with a typing indicator. */
export const Chat: React.FC<LayoutProps> = ({scene, P, v}) => {
  const f = useCurrentFrame();
  const answer = (scene.points.length ? scene.points : [scene.heading]).slice(0, 3);
  const q = `${scene.heading.replace(/[.!]$/, '')}?`;
  const typing = f > 10 && f < 22;
  return <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24}}>
    <div style={{alignSelf: 'flex-end', maxWidth: 640, padding: '24px 32px', borderRadius: '36px 36px 8px 36px', background: P.accent, color: P.bg, fontFamily: FONT.sans,
      fontWeight: 700, fontSize: 42, transform: `scale(${enter(f, 0, 'snappy')})`, transformOrigin: 'right bottom'}}>{clampText(q, 44)}</div>
    {typing && <div style={{alignSelf: 'flex-start', padding: '24px 32px', borderRadius: 36, background: P.surface, border: `3px solid ${P.line}`, display: 'flex', gap: 10}}>
      {[0, 1, 2].map(i => <span key={i} style={{width: 18, height: 18, borderRadius: 9, background: P.muted, transform: `translateY(${Math.sin((f + i * 4) / 3) * 5}px)`}}/>)}
    </div>}
    {f >= 22 && <Panel P={P} style={{alignSelf: 'flex-start', maxWidth: 700, padding: '26px 32px', borderRadius: '36px 36px 36px 8px', transform: `scale(${enter(f, 22, 'snappy')})`, transformOrigin: 'left bottom'}}>
      {answer.map((a, i) => <div key={i} style={{fontFamily: FONT.sans, fontSize: 44, fontWeight: 640, color: P.ink, padding: '8px 0', opacity: enter(f, 24 + i * 5, v.temperament)}}>
        <span style={{color: P.accent}}>●</span> {clampText(a, 28)}</div>)}
    </Panel>}
  </div>;
};

/** Node graph: the focus in the middle, points as satellites joined by drawing edges. */
export const NodeGraph: React.FC<LayoutProps> = ({beat, scene, P, v}) => {
  const f = useCurrentFrame();
  const sats = (scene.points.length ? scene.points : [scene.heading]).slice(0, 3);
  const pos = [[140, 120], [700, 170], [420, 600]];
  const c = [420, 340];
  return <div style={{position: 'absolute', inset: 0}}>
    <svg width="840" height="700" style={{position: 'absolute', inset: 0}}>
      {sats.map((_, i) => <line key={i} x1={c[0]} y1={c[1]} x2={pos[i][0]} y2={pos[i][1]} stroke={P.accent} strokeWidth="6" strokeLinecap="round"
        pathLength={1} strokeDasharray={1} strokeDashoffset={1 - interpolate(f, [8 + i * 5, 20 + i * 5], [0, 1], cl)}/>)}
    </svg>
    {sats.map((s, i) => {
      const e = enter(f, 14 + i * 5, 'snappy');
      return <div key={i} style={{position: 'absolute', left: pos[i][0], top: pos[i][1], transform: `translate(-50%, -50%) scale(${e})`, padding: '18px 26px', borderRadius: 28,
        background: P.surface, border: `3px solid ${P.line}`, fontFamily: FONT.sans, fontWeight: 720, fontSize: 40, color: P.ink, whiteSpace: 'nowrap'}}>{clampText(s, 16)}</div>;
    })}
    <div style={{position: 'absolute', left: c[0], top: c[1], transform: `translate(-50%, -50%) scale(${enter(f, 0, v.temperament)})`, padding: '30px 40px', borderRadius: 999,
      background: P.accent, color: P.bg, fontFamily: FONT.sans, fontWeight: 900, fontSize: 52, whiteSpace: 'nowrap'}}>{clampText(scene.label || beat.focus, 14)}</div>
  </div>;
};
