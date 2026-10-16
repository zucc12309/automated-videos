import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame} from 'remotion';
import {ensureFonts} from '../premium/tokens';
import {EpisodeNumber, SeriesHeader} from './Cover';
import {CursorPanel, handTip, HandPanel, MimoMascot, PanelView} from './Visuals';
import L from './layout.json';
import {accentA, clamp01, EpisodeInfo, EpisodeProps, FONT, inkA, io, Label, Panel, S, samplePath, Scene, SeriesInfo, sp, SubGroup, wf} from './theme';

/* One episode of a series, entirely data-driven: build_episode.py times every scene to the measured narration (scenes[].from/frames/
   words), groups the subtitles, and passes the verified demo panels. Nothing episode-specific is written here. */

type SP = {scene: Scene; f: number; p: EpisodeProps; mouth: number};
const R = L.regions;

const Backdrop: React.FC<{g: number; kx?: number; ky?: number}> = ({g, kx = 50, ky = 40}) =>
  <AbsoluteFill>
    <svg width={1080} height={1920} style={{position: 'absolute', inset: 0}}>
      <defs>
        <pattern id="edots" width="40" height="40" patternUnits="userSpaceOnUse" patternTransform={`translate(0 ${(g * .4) % 40})`}>
          <circle cx="2" cy="2" r="1.6" fill={inkA(.06)}/></pattern>
        <radialGradient id="ekey" cx={`${kx}%`} cy={`${ky}%`} r="60%"><stop offset="0" stopColor={accentA(.09)}/><stop offset="1" stopColor={accentA(0)}/></radialGradient>
        <radialGradient id="evig" cx="50%" cy="50%" r="75%"><stop offset=".6" stopColor="#000" stopOpacity="0"/><stop offset="1" stopColor="#000" stopOpacity=".5"/></radialGradient>
      </defs>
      <rect width={1080} height={1920} fill="url(#edots)"/>
      <rect width={1080} height={1920} fill="url(#ekey)"/>
      <rect width={1080} height={1920} fill="url(#evig)"/>
    </svg>
  </AbsoluteFill>;

const Chip: React.FC<{text: string; on: number; active?: boolean}> = ({text, on, active = true}) =>
  <div style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: 34, letterSpacing: 4, padding: '12px 22px', borderRadius: 14,
    color: active ? S.ground : S.inkSoft, background: active ? S.accent : S.panel, border: `2px solid ${active ? S.accent : inkA(.1)}`,
    opacity: clamp01(on * 1.5), transform: `translateY(${(1 - on) * 26}px) scale(${.85 + .15 * on})`}}>{text}</div>;

const ownFrame = (scene: Scene, l: Label, i: number, n: number) =>
  l.at !== undefined ? wf(scene, l.at) : Math.round(scene.frames * (.15 + .6 * i / Math.max(1, n)));
/** Chips land in order: a label never appears before the one to its left. */
const labelFrame = (scene: Scene, labels: Label[], i: number) =>
  Math.max(...labels.slice(0, i + 1).map((l, j) => ownFrame(scene, l, j, labels.length)));

/** The desktop + webcam picture-in-picture used by the hook and the payoff (or any single panel). */
const DemoStage: React.FC<{panels: Panel[]; t: number; w: number; h: number; tag?: string | null}> = ({panels, t, w, h, tag}) => {
  const cursor = panels.find(p => p.kind === 'cursor');
  const hand = panels.find(p => p.kind === 'hand');
  if (cursor && hand && cursor.kind === 'cursor' && hand.kind === 'hand') {
    const pw = Math.round(w * .4), ph = Math.round(pw * .75);
    return <div style={{position: 'relative', width: w, height: h}}>
      <CursorPanel w={w} h={h} path={cursor.path} t={t} title={cursor.label} tag={tag}/>
      <div style={{position: 'absolute', right: 22, top: 22, borderRadius: 26, boxShadow: `0 0 0 3px ${S.accent}`}}>
        <HandPanel w={pw} h={ph} path={hand.path} t={t} title={hand.label ?? 'CAM'}/></div>
    </div>;
  }
  const vid = panels.find(x => x.kind === 'video'), other = panels.find(x => x.kind !== 'video');
  if (vid && other) {                                   // input → output: what you give the project, and the real thing it made
    const vw = Math.round(h * 9 / 16), lw = w - vw - 56, lh = h - 90;
    const on = clamp01(t * 2);
    return <div style={{position: 'relative', width: w, height: h}}>
      <div style={{position: 'absolute', left: 0, top: 45}}><PanelView panel={other} w={lw} h={lh} t={t}/></div>
      <svg width={w} height={h} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        <path d={`M${lw - 6},${h / 2} L${w - vw + 4},${h / 2}`} stroke={S.accent} strokeWidth={6} strokeLinecap="round" strokeDasharray="12 10"
          strokeDashoffset={-t * 60} opacity={on}/>
        <circle cx={lw - 6} cy={h / 2} r={11} fill={S.accent} opacity={on}/>
      </svg>
      <div style={{position: 'absolute', right: 0, top: 0}}><PanelView panel={vid} w={vw} h={h} t={t} tag={tag}/></div>
    </div>;
  }
  return <PanelView panel={panels[0]} w={w} h={h} t={t} tag={tag}/>;
};

// ---------------------------------------------------------------- scenes
const HookScene: React.FC<SP> = ({scene, f, p, mouth}) => {
  const t = f / 30;
  const lines = p.episode.headline;
  const at = lines.map((_, i) => i === 0 ? 0 : wf(scene, Math.round(i * scene.words.length / lines.length)));
  const pop = sp(f, 0, 16, 220);
  return <AbsoluteFill>
    <div style={{position: 'absolute', left: R.hook.stage[0], top: R.hook.stage[1], transform: `scale(${.94 + .06 * pop})`, transformOrigin: '50% 0%'}}>
      <DemoStage panels={p.hook.panels} t={t} w={R.hook.stage[2]} h={R.hook.stage[3]} tag={p.episode.demoTag}/>
    </div>
    <div style={{position: 'absolute', left: R.hook.headline[0], width: R.hook.headline[2], top: R.hook.headline[1], textAlign: 'center', fontFamily: FONT.sans, fontWeight: 900, letterSpacing: -3}}>
      {lines.map((l, i) => {
        const k = sp(f, at[i], 13, 260, .5);
        return <div key={i} style={{fontSize: 132, lineHeight: 1, color: i === lines.length - 1 && lines.length > 1 ? S.accent : S.ink,
          opacity: f >= at[i] ? 1 : 0, transform: `scale(${1.35 - .35 * k})`, whiteSpace: 'nowrap'}}>{l}</div>;
      })}
    </div>
    {/* Mimo peeks over the stage edge as the punchline lands: a reaction, not an intro */}
    <div style={{position: 'absolute', left: R.hook.peek[0], top: R.hook.peek[1], width: R.hook.peek[2], height: R.hook.peek[3], overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 30, top: R.hook.peek[3] - 150 * sp(f, at[at.length - 1] + 4, 12, 180)}}>
        <MimoMascot state="surprised" size={200} frame={f} mouth={mouth} look={{x: 1, y: -.6}}/></div>
    </div>
  </AbsoluteFill>;
};

const RepoGlyph: React.FC<{size: number}> = ({size}) =>
  <svg width={size} height={size} viewBox="0 0 24 24"><path d="M5 3h12a2 2 0 0 1 2 2v13H7a2 2 0 0 0-2 2V3z M5 20a2 2 0 0 0 2 2h12v-4"
    fill="none" stroke={S.accent} strokeWidth={2} strokeLinejoin="round"/></svg>;

const DiscoveryScene: React.FC<SP> = ({scene, f, p, mouth}) => {
  const enter = sp(f, 2, 13, 150);
  const card = sp(f, 10, 16, 150);
  const point = io(f, 22, 32);
  const r = p.repoCard;
  return <AbsoluteFill>
    <div style={{position: 'absolute', top: 290, left: 0, right: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 26,
      opacity: io(f, 0, 6), transform: `translateY(${(1 - sp(f, 0, 16, 200)) * -30}px)`}}>
      <SeriesHeader text={p.series.header} size={40}/>
      <EpisodeNumber label={p.episode.label} size={60}/>
    </div>
    <div style={{position: 'absolute', left: 90, right: 90, top: 640, padding: '40px 44px', borderRadius: 30, background: S.panel,
      border: `2px solid ${inkA(.1)}`, boxShadow: '0 40px 90px rgba(0,0,0,.55)',
      transform: `translateX(${(1 - card) * 900}px) translateY(${Math.sin(f / 14) * 7}px) rotate(${(1 - card) * 4 + Math.sin(f / 22) * .5}deg)`}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 18, fontFamily: FONT.mono, fontSize: 36, color: S.inkSoft}}>
        <RepoGlyph size={44}/><span>{r.owner} /</span></div>
      <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: 70, color: S.ink, marginTop: 8, letterSpacing: -1, whiteSpace: 'nowrap', overflow: 'hidden',
        textOverflow: 'ellipsis'}}>{r.name}</div>
      <div style={{fontFamily: FONT.sans, fontSize: 36, color: S.inkSoft, marginTop: 14, lineHeight: 1.3}}>{r.description}</div>
      <div style={{display: 'flex', gap: 30, marginTop: 24, fontFamily: FONT.mono, fontSize: 28, color: S.muted}}>
        {r.language && <span><span style={{display: 'inline-block', width: 18, height: 18, borderRadius: 9, background: S.accent, marginRight: 10}}/>{r.language}</span>}
        {r.license && <span>{r.license} license</span>}
      </div>
    </div>
    {/* identity signature: Mimo pops up from behind a hairline, so it never crosses the subtitle band */}
    <div style={{position: 'absolute', left: 60, top: R.discovery.mimo[1], width: 420, height: R.discovery.mimo[3], overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 50, top: (1 - enter) * 380}}>
        <MimoMascot state={point > .05 ? 'pointing' : 'surprised'} size={R.discovery.mimo[2]} frame={f} mouth={mouth} amount={point > .05 ? point : 1} pointAngle={-55}/>
      </div>
    </div>
    <div style={{position: 'absolute', left: 90, top: R.discovery.mimo[1] + R.discovery.mimo[3] - 1, width: 360, height: 2, background: inkA(.12)}}/>
    <div style={{position: 'absolute', left: 500, top: 1230, fontFamily: FONT.serif, fontStyle: 'italic', fontSize: 64, color: S.ink,
      opacity: io(f, 26, 34), transform: `translateY(${(1 - io(f, 26, 34)) * 20}px)`}}>found this.</div>
  </AbsoluteFill>;
};

const DemoScene: React.FC<SP> = ({scene, f, p, mouth}) => {
  const t = f / 30;
  const {left, right, labels} = p.demo;
  const [lx, top, pw, ph] = R.demo.left, rx = R.demo.right[0];
  const inL = sp(f, 0, 16, 170), inR = sp(f, 5, 16, 170);
  let wire: React.ReactNode = null;
  if (left.kind === 'hand' && right.kind === 'cursor') {
    const kh = samplePath(left.path, t), kc = samplePath(right.path, t);
    const size = Math.min(pw, ph) * .52;
    const [hx, hy] = handTip(kh.x * pw, kh.y * ph + size * .45, size, kh.pinch, kh.open);
    const cx = (1 - kc.x) * pw * .9 + pw * .05, cy = kc.y * ph * .8 + ph * .12;
    const ax = lx + hx, ay = top + hy, bx = rx + cx, by = top + cy;
    const on = io(f, 10, 22);
    wire = <svg width={1080} height={1920} style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
      <path d={`M${ax},${ay} C${ax + 160},${ay} ${bx - 160},${by} ${bx},${by}`} fill="none" stroke={S.accent} strokeWidth={3}
        strokeDasharray="10 9" strokeDashoffset={-f * 2} opacity={on}/>
      <circle cx={ax} cy={ay} r={8} fill={S.accent} opacity={on}/>
    </svg>;
  } else {                                                // any other pair: input panel → output panel
    const on = io(f, 10, 22), y = top + ph / 2, ax = lx + pw, bx = rx + (right.kind === 'video' ? (pw - ph * 9 / 16) / 2 : 0);
    wire = <svg width={1080} height={1920} style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
      <path d={`M${ax - 4},${y} L${bx + 4},${y}`} stroke={S.accent} strokeWidth={5} strokeDasharray="10 8" strokeDashoffset={-f * 2} opacity={on}/>
      <circle cx={ax - 4} cy={y} r={9} fill={S.accent} opacity={on}/>
    </svg>;
  }
  const speed = (() => {
    const a = samplePath(right.kind === 'cursor' ? right.path : [], t - .1), b = samplePath(right.kind === 'cursor' ? right.path : [], t);
    return clamp01(Math.hypot(a.x - b.x, a.y - b.y) * 12);
  })();
  // Mimo nods as each label lands and lights up for the last one
  const hits = labels.map((_, i) => labelFrame(scene, labels, i));
  const nod = Math.max(0, ...hits.map(h => f >= h ? Math.exp(-(f - h) / 5) * Math.sin(Math.min(Math.PI, (f - h) / 3)) : 0));
  const lastHit = hits.length > 0 && f >= hits[hits.length - 1];
  return <AbsoluteFill>
    <div style={{position: 'absolute', left: lx, top, opacity: inL, transform: `translateY(${(1 - inL) * 60}px)`}}>
      <PanelView panel={left} w={pw} h={ph} t={t} tag={p.episode.demoTag}/></div>
    <div style={{position: 'absolute', left: rx, top, opacity: inR, transform: `translateY(${(1 - inR) * 60}px)`}}>
      <PanelView panel={right} w={pw} h={ph} t={t}/></div>
    {wire}
    <div style={{position: 'absolute', top: top + ph + 44, left: 0, right: 0, display: 'flex', justifyContent: 'center', gap: 22}}>
      {labels.map((l, i) => {
        const at = labelFrame(scene, labels, i);
        const next = i + 1 < labels.length ? labelFrame(scene, labels, i + 1) : 1e9;
        return <Chip key={l.text} text={l.text} on={sp(f, at, 14, 200)} active={f < next}/>;
      })}
    </div>
    <div style={{position: 'absolute', left: R.demo.mimo[0], top: R.demo.mimo[1]}}>
      <div style={{transform: `translateY(${-nod * 18}px) scale(${1 + nod * .04}, ${1 - nod * .05})`, transformOrigin: '50% 100%'}}>
        <MimoMascot state={lastHit ? 'excited' : 'curious'} size={R.demo.mimo[2]} frame={f} mouth={mouth}
          amount={lastHit ? .5 : right.kind === 'cursor' ? .4 + .6 * speed : .8} look={{x: .8, y: -1}}/></div></div>
  </AbsoluteFill>;
};

const FlowScene: React.FC<SP> = ({scene, f, p, mouth}) => {
  const nodes = p.flow;
  const nodeAt = nodes.map((_, i) => Math.round(8 + i * Math.min(26, (scene.frames - 50) / Math.max(1, nodes.length))));
  const active = nodeAt.filter(a => f >= a).length - 1;
  const y0 = R.flow.nodes[1], nh = 170, gap = (R.flow.nodes[3] - nh) / Math.max(1, nodes.length - 1);
  const mimoY = y0 + Math.max(0, active) * gap + nh / 2 - R.flow.mimo[2] * .6 + Math.sin(f / 30 * Math.PI * 4) * 4;
  const walking = active >= 0 && f - nodeAt[Math.max(0, active)] < 12;
  return <AbsoluteFill>
    <div style={{position: 'absolute', top: 290, left: 0, right: 0, textAlign: 'center', opacity: io(f, 0, 8)}}>
      <div style={{fontFamily: FONT.mono, fontSize: 34, color: S.muted, letterSpacing: 2}}>{p.repoCard.owner} /</div>
      <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: 64, color: S.ink, letterSpacing: -1}}>{p.repoCard.name}</div>
    </div>
    <svg width={1080} height={1920} style={{position: 'absolute', inset: 0}}>
      {nodes.slice(1).map((_, i) => {
        const on = io(f, nodeAt[i + 1] - 8, nodeAt[i + 1]);
        const x = 640, ya = y0 + i * gap + nh, yb = y0 + (i + 1) * gap;
        return <g key={i}>
          <line x1={x} y1={ya} x2={x} y2={ya + (yb - ya) * on} stroke={S.accent} strokeWidth={4}/>
          {on > .99 && [0, 1, 2].map(j => <circle key={j} cx={x} cy={ya + ((f * 2.5 + j * 27) % (yb - ya))} r={7} fill={S.accentHot}/>)}
        </g>;
      })}
    </svg>
    {nodes.map((n, i) => {
      const k = sp(f, nodeAt[i], 15, 190);
      const on = i <= active;
      const sweep = active === nodes.length - 1 && f > nodeAt[nodes.length - 1] + 12 ? Math.floor((f - nodeAt[nodes.length - 1] - 12) / 9) % nodes.length === i : false;
      return <div key={i} style={{position: 'absolute', left: 300, width: 680, top: y0 + i * gap, height: nh, borderRadius: 28,
        background: sweep ? accentA(.16) : on ? S.panelHi : S.panel, border: `3px solid ${on ? S.accent : inkA(.08)}`, display: 'flex', flexDirection: 'column',
        justifyContent: 'center', padding: '0 40px', opacity: k, transform: `translateX(${(1 - k) * 80}px)`}}>
        <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: 56, color: S.ink, letterSpacing: -.5, whiteSpace: 'nowrap'}}>{n.label}</div>
        {n.sub && <div style={{fontFamily: FONT.mono, fontSize: 26, color: S.muted, marginTop: 6, whiteSpace: 'nowrap'}}>{n.sub}</div>}
      </div>;
    })}
    <div style={{position: 'absolute', left: R.flow.mimo[0], top: mimoY}}>
      <MimoMascot state={active === nodes.length - 1 && !walking ? 'excited' : walking ? 'curious' : 'thinking'} size={R.flow.mimo[2]} frame={f} mouth={mouth}
        amount={active === nodes.length - 1 && !walking ? .5 : 1} look={{x: 1, y: 0}}/></div>
  </AbsoluteFill>;
};

const PayoffScene: React.FC<SP> = ({scene, f, p, mouth}) => {
  const t = f / 30 + (p.payoff.replayFrom ?? 0);                    // replay the strongest verified moment of the demo path
  const qw = p.payoff.question.split(' ');                         // two balanced lines
  const cut = qw.reduce((best, _, i) => Math.abs(qw.slice(0, i).join(' ').length - qw.slice(i).join(' ').length) <
    Math.abs(qw.slice(0, best).join(' ').length - qw.slice(best).join(' ').length) ? i : best, 1);
  const q = [qw.slice(0, cut).join(' '), qw.slice(cut).join(' ')].filter(Boolean);
  const qAt = 4;
  const follow = scene.words.findIndex(w => /^follow/i.test(w.w));
  const stampAt = follow >= 0 ? wf(scene, follow) : Math.round(scene.frames * .55);
  const st = sp(f, stampAt, 11, 240, .5);
  return <AbsoluteFill>
    <div style={{position: 'absolute', left: R.payoff.stage[0], top: R.payoff.stage[1], transform: `scale(${.92 + .08 * sp(f, 0, 16, 180)})`}}>
      <DemoStage panels={[p.payoff.panel, ...p.hook.panels.filter(x => x.kind !== p.payoff.panel.kind)]} t={t} w={R.payoff.stage[2]} h={R.payoff.stage[3]} tag={p.episode.demoTag}/></div>
    <div style={{position: 'absolute', left: R.payoff.mimo[0], top: R.payoff.mimo[1]}}>
      <MimoMascot state="excited" size={R.payoff.mimo[2]} frame={f} mouth={mouth} amount={io(f, 0, 10)}/></div>
    <div style={{position: 'absolute', left: 360, right: 50, top: 930, fontFamily: FONT.sans, fontWeight: 900, fontSize: 92, lineHeight: .98, letterSpacing: -2}}>
      {q.map((l, i) => {
        const k = sp(f, qAt + i * 6, 14, 220);
        return <div key={i} style={{color: i === q.length - 1 ? S.accent : S.ink, opacity: k, transform: `translateY(${(1 - k) * 30}px)`, whiteSpace: 'nowrap'}}>{l.trim()}</div>;
      })}
    </div>
    <div style={{position: 'absolute', left: 0, right: 0, top: 1210, display: 'flex', justifyContent: 'center', opacity: f >= stampAt ? 1 : 0,
      transform: `scale(${1.5 - .5 * st}) rotate(${-2 * st}deg)`}}>
      <div style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: 36, letterSpacing: 2, color: S.accent, border: `4px solid ${S.accent}`, borderRadius: 14,
        padding: '12px 24px', background: 'rgba(14,15,18,.85)', whiteSpace: 'nowrap'}}>{p.episode.label} — SAVED TO {p.series.collection}</div>
    </div>
  </AbsoluteFill>;
};

/** Reusable 2-second outro: mascot, DevMimo wordmark, episode number, follow CTA naming the next episode. */
export const SeriesOutro: React.FC<{f: number; series: SeriesInfo; episode: EpisodeInfo}> = ({f, series, episode}) => {
  const m = sp(f, 0, 12, 170), w = sp(f, 5, 15, 190), c = sp(f, 12, 14, 200);
  const next = `EP. ${String(episode.n + 1).padStart(3, '0')}`;
  return <AbsoluteFill style={{alignItems: 'center'}}>
    <div style={{position: 'absolute', top: 470, transform: `translateY(${(1 - m) * 200}px)`, opacity: clamp01(m * 2)}}>
      <MimoMascot state="excited" size={300} frame={f + 20} amount={.6}/></div>
    <div style={{position: 'absolute', top: 900, fontFamily: FONT.sans, fontWeight: 900, fontSize: 150, letterSpacing: -5, opacity: w,
      transform: `scale(${.9 + .1 * w})`}}><span style={{color: S.ink}}>Dev</span><span style={{color: S.accent}}>Mimo</span></div>
    <div style={{position: 'absolute', top: 1090, display: 'flex', alignItems: 'center', gap: 20, opacity: w}}>
      <EpisodeNumber label={episode.label} size={40} solid={false}/>
      <span style={{fontFamily: FONT.mono, fontSize: 28, color: S.muted, letterSpacing: 3}}>{series.header}</span>
    </div>
    <div style={{position: 'absolute', top: 1230, opacity: c, transform: `translateY(${(1 - c) * 30}px)`, fontFamily: FONT.sans, fontWeight: 800, fontSize: 46,
      color: S.ground, background: S.accent, padding: '20px 40px', borderRadius: 999, whiteSpace: 'nowrap'}}>FOLLOW {series.handle} · {next} SOON</div>
  </AbsoluteFill>;
};

// ---------------------------------------------------------------- overlays
export const Subtitles: React.FC<{g: number; groups: SubGroup[]; scenes: Scene[]}> = ({g, groups, scenes}) => {
  const t = g / 30;
  const grp = groups.find(x => t >= x.s && t < x.e);
  if (!grp) return null;
  const y = grp.y ?? L.subtitle.y;
  const k = clamp01((t - grp.s) * 30 / 4);
  return <div style={{position: 'absolute', left: 60, right: 60, top: y, display: 'flex', justifyContent: 'center'}}>
    <div style={{fontFamily: FONT.sans, fontWeight: 800, fontSize: 54, lineHeight: 1.15, color: S.ink, background: 'rgba(14,15,18,.84)',
      padding: '14px 28px', borderRadius: 18, textAlign: 'center', maxWidth: 960, opacity: k, transform: `translateY(${(1 - k) * 8}px)`}}>
      {grp.words.map((w, i) => <span key={i} style={{color: w.em ? S.accent : S.ink}}>{w.w}{i < grp.words.length - 1 ? ' ' : ''}</span>)}
    </div>
  </div>;
};

const SeriesBug: React.FC<{series: SeriesInfo; episode: EpisodeInfo; on: number}> = ({series, episode, on}) =>
  <div style={{position: 'absolute', top: 222, left: 60, right: 60, display: 'flex', alignItems: 'center', gap: 14, opacity: on,
    fontFamily: FONT.mono, fontWeight: 700, fontSize: 22, letterSpacing: 3, color: S.muted}}>
    <span style={{color: S.ground, background: S.accent, padding: '3px 10px', borderRadius: 6}}>{episode.label}</span>{series.header}
  </div>;

const SCENES: Record<string, React.FC<SP>> = {hook: HookScene, discovery: DiscoveryScene, demo: DemoScene, flow: FlowScene, payoff: PayoffScene};
const KEYL: Record<string, [number, number]> = {hook: [50, 30], discovery: [50, 45], demo: [50, 35], flow: [55, 45], payoff: [45, 55]};

export const SeriesEpisode: React.FC<EpisodeProps> = p => {
  ensureFonts();
  const g = useCurrentFrame();
  const scenes = p.scenes;
  const last = scenes[scenes.length - 1];
  const outroFrom = last.from + last.frames;
  const cur = scenes.find(s => g >= s.from && g < s.from + s.frames);
  const [kx, ky] = cur ? KEYL[cur.kind] ?? [50, 40] : [50, 40];
  const mouth = p.mouth[g] ?? 0;
  const bug = scenes.find(s => s.kind === 'demo');
  const bugOn = bug && g >= bug.from && g < outroFrom ? io(g, bug.from, bug.from + 8) : 0;
  return <AbsoluteFill style={{background: S.ground}}>
    <Backdrop g={g} kx={kx} ky={ky}/>
    {scenes.map(s => {
      const Comp = SCENES[s.kind];
      return Comp ? <Sequence key={s.id} from={s.from} durationInFrames={s.frames} layout="none">
        <SceneClock scene={s} p={p} mouth={mouth} Comp={Comp}/>
      </Sequence> : null;
    })}
    <Sequence from={outroFrom} durationInFrames={p.outroFrames} layout="none"><OutroClock p={p}/></Sequence>
    {bugOn > 0 && <SeriesBug series={p.series} episode={p.episode} on={bugOn}/>}
    {p.showSubtitles !== false && <Subtitles g={g} groups={p.subtitles} scenes={scenes}/>}
  </AbsoluteFill>;
};

/* Slow camera push on every scene (1 → 1.045) so holds never freeze; the subtitles and series bug sit outside it and stay still. */
const SceneClock: React.FC<{scene: Scene; p: EpisodeProps; mouth: number; Comp: React.FC<SP>}> = ({scene, p, mouth, Comp}) => {
  const f = useCurrentFrame();
  const k = f / Math.max(1, scene.frames);
  return <AbsoluteFill style={{transform: `scale(${1 + .045 * k}) translateY(${-10 * k}px)`, transformOrigin: '50% 42%'}}>
    <Comp scene={scene} f={f} p={p} mouth={mouth}/></AbsoluteFill>;
};
const OutroClock: React.FC<{p: EpisodeProps}> = ({p}) => {
  const f = useCurrentFrame();
  return <SeriesOutro f={f} series={p.series} episode={p.episode}/>;
};
