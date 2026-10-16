import React from 'react';
import {AbsoluteFill, Img, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {ensureFonts} from '../premium/tokens';
import {EpisodeNumber, SeriesHeader} from './Cover';
import {Backdrop} from './Episode';
import {MimoMascot} from './Visuals';
import L from './layout-reel.json';
import {accentA, clamp01, EpisodeInfo, fitSize, FONT, inkA, io, S, Scene, SeriesInfo, sp, SubGroup, wf} from './theme';

/* Reel format v2 (story arc: shock → context → mystery → discovery → proof → possibility → question). Everything is data from the
   episode spec (series/<slug>/specs/*.json, "format": "reel-v2"), timed by examples/series/build_reel.py to the measured narration.
   Critical content sits inside layout-reel.json `safe` (the Instagram UI margins in series.json safe_zone.reel_v2); backgrounds bleed.
   Nothing here names a repository or an episode. */

const R = L.regions;
const SAFE_W = L.safe.right - L.safe.left;

export type Shot = {src: string; name: string; inspired?: string; label?: string; focus?: [number, number]; zoom?: [number, number]; at?: string};
type Lines = {at: string; kind: 'mcp' | 'disasm' | 'findings'; title: string; lines: string[]; highlight?: number[]};
export type Beat = Scene & {
  headline?: string[]; headline_at?: string[]; shots?: Shot[]; text?: string[];
  apps?: {at: string; name: string; inspired: string; src: string; focus?: [number, number]}[];
  grid?: {src: string; name: string}[]; question?: string; question_at?: string; cta?: string;
  app?: {name: string; note: string; input: string; output: string}; steps?: Lines[]; stamp?: {at?: string; text: string}; tag?: string;
  stages?: {at: string; text: string}[];
  compare?: {left: {src: string; label: string}; right: {src: string; label: string}; badge: string; sub?: string};
};
export type ReelProps = {
  fps: number; durationInFrames: number; series: SeriesInfo; episode: EpisodeInfo; scenes: Beat[]; subtitles: SubGroup[]; mouth: number[];
  repoCard: {owner: string; name: string; title: string; description: string; language?: string; license?: string};
  showSubtitles?: boolean; safeGuides?: boolean;
};
type BP = {b: Beat; f: number; p: ReelProps; mouth: number};

// ---------------------------------------------------------------- timing helpers
const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
/** Scene-local frame of the first narrated word starting with `token` ('' = scene start). */
export const atWord = (b: Scene, token: string | undefined, fallback = 0) => {
  if (!token) return fallback;
  const i = b.words.findIndex(w => norm(w.w).startsWith(norm(token)));
  return i >= 0 ? wf(b, i) : fallback;
};
const box = (r: number[]): React.CSSProperties => ({position: 'absolute', left: r[0], top: r[1], width: r[2], height: r[3]});

// ---------------------------------------------------------------- shared pieces
/** A real screenshot in an app-window frame, slowly zooming toward its focus point (no random zooms: one direction per shot). */
const ShotWindow: React.FC<{shot: Shot; w: number; h: number; k: number; tag?: string}> = ({shot, w, h, k, tag}) => {
  const [z0, z1] = shot.zoom ?? [1.1, 1.25];
  const [fx, fy] = shot.focus ?? [50, 50];
  return <div style={{position: 'relative', width: w, height: h, borderRadius: 26, overflow: 'hidden', background: '#000',
    border: `2px solid ${inkA(.14)}`, boxShadow: '0 34px 90px rgba(0,0,0,.6)'}}>
    <Img src={staticFile(shot.src)} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover',
      objectPosition: `${fx}% ${fy}%`, transform: `scale(${z0 + (z1 - z0) * k})`, transformOrigin: `${fx}% ${fy}%`}}/>
    <div style={{position: 'absolute', left: 18, top: 18, display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 6}}>
      <span style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: 40, letterSpacing: 1, color: S.ground, background: S.accent, padding: '4px 14px', borderRadius: 10}}>
        {shot.label ?? shot.name}</span>
      {shot.inspired && <span style={{fontFamily: FONT.sans, fontWeight: 700, fontSize: 30, color: S.ink, background: 'rgba(14,15,18,.82)', padding: '4px 12px',
        borderRadius: 8}}>{shot.inspired}-style · open source</span>}
    </div>
    {tag && <div style={{position: 'absolute', left: 0, right: 0, bottom: 16, display: 'flex', justifyContent: 'center'}}>
      <span style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: 26, letterSpacing: 1.5, color: S.ink, background: 'rgba(14,15,18,.85)', padding: '6px 14px',
        borderRadius: 8, border: `2px solid ${accentA(.6)}`}}>{tag}</span></div>}
  </div>;
};

/** Full-bleed blurred copy of the current picture: the background fills the frame while the content stays in the safe area. */
const Bleed: React.FC<{src?: string; o?: number}> = ({src, o = .32}) => src
  ? <AbsoluteFill style={{overflow: 'hidden'}}><Img src={staticFile(src)} style={{position: 'absolute', inset: -80, width: 1240, height: 2080, objectFit: 'cover',
    filter: 'blur(46px) saturate(.8)', opacity: o}}/><AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(14,15,18,.55), rgba(14,15,18,.2) 40%, rgba(14,15,18,.75))'}}/></AbsoluteFill>
  : null;

const Headline: React.FC<{lines: string[]; at: number[]; f: number; r: number[]; max?: number}> = ({lines, at, f, r, max = 128}) => {
  const size = Math.min(fitSize(lines, r[2], max), r[3] / lines.length / 1.02);
  return <div style={{...box(r), display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', fontFamily: FONT.sans, fontWeight: 900,
    letterSpacing: -size * .02}}>
    {lines.map((l, i) => {
      const k = sp(f, at[i], 13, 260, .5);
      return <div key={i} style={{fontSize: size, lineHeight: 1.02, whiteSpace: 'nowrap', color: i === lines.length - 1 && lines.length > 1 ? S.accent : S.ink,
        opacity: f >= at[i] ? 1 : 0, transform: `scale(${1.25 - .25 * k})`}}>{l}</div>;
    })}
  </div>;
};

const Stamp: React.FC<{text: string; on: number; r: number[]; size?: number; tone?: 'accent' | 'ink'}> = ({text, on, r, size = 48, tone = 'accent'}) =>
  on <= 0 ? null : <div style={{...box(r), display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: clamp01(on * 3),
    transform: `scale(${1.6 - .6 * on}) rotate(${-2.5 * on}deg)`}}>
    <div style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: size, letterSpacing: 3, whiteSpace: 'nowrap', color: tone === 'accent' ? S.accent : S.ink,
      border: `5px solid ${tone === 'accent' ? S.accent : S.ink}`, borderRadius: 16, padding: '10px 26px', background: 'rgba(14,15,18,.9)'}}>{text}</div>
  </div>;

const Mascot: React.FC<{r: number[]; children: React.ReactNode; on?: number; clip?: boolean}> = ({r, children, on = 1, clip = false}) =>
  <div style={{...box(r), overflow: clip ? 'hidden' : 'visible'}}>
    <div style={{position: 'absolute', left: 0, bottom: 0, transform: `translateY(${(1 - on) * r[3] * 1.1}px)`}}>{children}</div></div>;

// ---------------------------------------------------------------- beats
/** SHOCK: a real result first. Frame 0 already shows a recreation (labelled as such) and the first headline line. */
const ShockBeat: React.FC<BP> = ({b, f, mouth}) => {
  const shots = b.shots ?? [];
  const cuts = shots.map((s, i) => i === 0 ? 0 : atWord(b, s.at, Math.round(b.frames * i / shots.length)));
  const cur = Math.max(0, cuts.filter(c => f >= c).length - 1);
  const local = f - cuts[cur], span = (cuts[cur + 1] ?? b.frames) - cuts[cur];
  const flash = cur > 0 ? 1 - clamp01(local / 5) : 0;
  const lines = b.headline ?? [];
  const at = lines.map((_, i) => atWord(b, b.headline_at?.[i], i === 0 ? 0 : Math.round(b.frames * .55)));
  const peek = sp(f, atWord(b, 'seven', 12), 12, 170);
  return <AbsoluteFill>
    <Bleed src={shots[cur]?.src}/>
    <div style={{...box(R.shock.stage), transform: `translateX(${cur > 0 ? (1 - sp(local, 0, 16, 240)) * 120 : 0}px)`}}>
      {shots[cur] && <ShotWindow shot={shots[cur]} w={R.shock.stage[2]} h={R.shock.stage[3]} k={clamp01(local / Math.max(1, span))} tag={b.text?.[0]}/>}
      <div style={{position: 'absolute', inset: 0, borderRadius: 26, background: '#fff', opacity: flash * .35}}/>
    </div>
    <Mascot r={R.shock.mimo} on={peek} clip><MimoMascot state="surprised" size={R.shock.mimo[2]} frame={f} mouth={mouth} look={{x: -.6, y: -.8}}/></Mascot>
    <Headline lines={lines} at={at} f={f} r={R.shock.headline}/>
  </AbsoluteFill>;
};

/** CONTEXT: one identifiable app per spoken name, each labelled with the product it is modelled on. */
const ContextBeat: React.FC<BP> = ({b, f}) => {
  const apps = b.apps ?? [];
  const at = apps.map((a, i) => atWord(b, a.at, Math.round(b.frames * i / apps.length)));
  const cur = Math.max(0, at.filter(x => f >= x).length - 1);
  const a = apps[cur];
  const local = f - at[cur], span = (at[cur + 1] ?? b.frames) - at[cur];
  const k = sp(local, 0, 15, 230);
  const nameSize = fitSize([a.name], R.context.name[2], 120);
  return <AbsoluteFill>
    <Bleed src={a.src}/>
    {cur > 0 && <div style={{...box(R.context.stage), transform: `translateX(${-k * 160}px) scale(${1 - .08 * k})`, opacity: 1 - k}}>
      <ShotWindow shot={{src: apps[cur - 1].src, name: apps[cur - 1].name, inspired: apps[cur - 1].inspired, focus: apps[cur - 1].focus}} w={R.context.stage[2]}
        h={R.context.stage[3]} k={1}/></div>}
    <div style={{...box(R.context.stage), transform: `translateX(${(1 - k) * 260}px) rotate(${(1 - k) * 3}deg)`, opacity: clamp01(k * 2)}}>
      <ShotWindow shot={{src: a.src, name: a.name, focus: a.focus, zoom: [1.12, 1.3]}} w={R.context.stage[2]} h={R.context.stage[3]} k={clamp01(local / Math.max(1, span))}
        tag={b.text?.[0]}/>
    </div>
    <div style={{...box(R.context.name), display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT.sans, fontWeight: 900, fontSize: nameSize,
      color: S.ink, letterSpacing: -2, transform: `translateY(${(1 - k) * 24}px)`, opacity: clamp01(k * 2)}}>{a.name}</div>
    <div style={{...box(R.context.inspired), display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT.sans, fontWeight: 700, fontSize: 46,
      color: S.inkSoft, opacity: clamp01(k * 2)}}><span style={{color: S.muted}}>inspired by&nbsp;</span><span style={{color: S.accent}}>{a.inspired}</span></div>
    <div style={{...box(R.context.dots), display: 'flex', justifyContent: 'center', gap: 16}}>
      {apps.map((_, i) => <div key={i} style={{width: i === cur ? 54 : 18, height: 18, borderRadius: 9, background: i <= cur ? S.accent : inkA(.2)}}/>)}
    </div>
  </AbsoluteFill>;
};

/** MYSTERY: the wider landscape (all seven), then the turn: how do you understand an app? */
const MysteryBeat: React.FC<BP> = ({b, f, mouth}) => {
  const tiles = b.grid ?? [];
  const [gx, gy, gw, gh] = R.mystery.grid;
  const cols = 3, gap = 16, tw = (gw - gap * (cols - 1)) / cols, th = (gh - gap * 2) / 3;
  const lastWord = b.words.length ? wf(b, -1) + Math.round((b.words[b.words.length - 1].e - b.words[b.words.length - 1].s) * 30) : Math.round(b.frames * .6);
  const turn = Math.min(lastWord + 4, b.frames - 22);
  const q = sp(f, turn, 14, 200), dim = io(f, turn, turn + 8);
  const lines = balance(b.question ?? '', 2);
  const qs = Math.min(fitSize(lines, R.mystery.question[2], 104), R.mystery.question[3] / lines.length / 1.05);
  return <AbsoluteFill>
    <AbsoluteFill style={{background: accentA(.04 * dim)}}/>
    {[...tiles, null, 'mimo'].map((t, i) => {
      const x = gx + (i % cols) * (tw + gap), y = gy + Math.floor(i / cols) * (th + gap);
      const k = sp(f, i * 2, 15, 220);
      const style: React.CSSProperties = {position: 'absolute', left: x, top: y, width: tw, height: th, borderRadius: 18, overflow: 'hidden',
        transform: `scale(${(.6 + .4 * k) * (1 - .04 * dim)})`, opacity: clamp01(k * 1.6) * (1 - .55 * dim * (t && t !== 'mimo' ? 1 : 0))};
      if (t === 'mimo') return <div key={i} style={{...style, overflow: 'hidden', border: `3px dashed ${accentA(.7)}`, background: S.panel}}>
        <div style={{position: 'absolute', left: (tw - 170) / 2, bottom: -8 + (1 - sp(f, 8, 12, 170)) * 200}}>
          <MimoMascot state={f >= turn ? 'curious' : 'thinking'} size={170} frame={f} mouth={mouth} amount={1}/></div></div>;
      if (!t) return <div key={i} style={{...style, border: `3px dashed ${inkA(.3)}`, display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: FONT.sans, fontWeight: 900, fontSize: 110, color: inkA(.35)}}>?</div>;
      if (typeof t === 'string') return null;
      return <div key={i} style={{...style, border: `2px solid ${inkA(.14)}`, background: '#000'}}>
        <Img src={staticFile(t.src)} style={{width: '100%', height: '100%', objectFit: 'cover'}}/>
        <div style={{position: 'absolute', left: 8, bottom: 8, fontFamily: FONT.sans, fontWeight: 800, fontSize: 28, color: S.ink, background: 'rgba(14,15,18,.85)',
          padding: '2px 10px', borderRadius: 8}}>{t.name}</div>
      </div>;
    })}
    <div style={{...box(R.mystery.question), display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', fontFamily: FONT.sans,
      fontWeight: 900, fontSize: qs, lineHeight: 1.04, letterSpacing: -2, opacity: q, transform: `translateY(${(1 - q) * 40}px)`}}>
      {lines.map((l, i) => <div key={i} style={{whiteSpace: 'nowrap', color: i === lines.length - 1 ? S.accent : S.ink}}>{l}</div>)}
    </div>
  </AbsoluteFill>;
};

const RepoGlyph: React.FC<{size: number}> = ({size}) =>
  <svg width={size} height={size} viewBox="0 0 24 24"><path d="M5 3h12a2 2 0 0 1 2 2v13H7a2 2 0 0 0-2 2V3z M5 20a2 2 0 0 0 2 2h12v-4"
    fill="none" stroke={S.accent} strokeWidth={2} strokeLinejoin="round"/></svg>;

/** DISCOVERY: the real repository, name large, URL legible, never a static hold (title words land with the narration). */
const DiscoveryBeat: React.FC<BP> = ({b, f, p, mouth}) => {
  const r = p.repoCard;
  const card = sp(f, 0, 15, 200);
  const words = r.title.split(' ');
  const wAt = words.map((w, i) => atWord(b, w, 6 + i * 6));
  const titleLines = balance(r.title, 2);
  const ts = fitSize(titleLines, R.discovery.card[2] - 88, 112);
  let wi = 0;
  return <AbsoluteFill>
    <div style={{...box(R.discovery.card), padding: '34px 44px', boxSizing: 'border-box', borderRadius: 30, background: S.panel, border: `2px solid ${inkA(.12)}`,
      boxShadow: '0 40px 90px rgba(0,0,0,.55)', transform: `translateY(${(1 - card) * 500}px) translateY(${Math.sin(f / 13) * 5}px)`}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 18}}>
        <EpisodeNumber label={p.episode.label} size={40}/><SeriesHeader text={p.series.header} size={24} color={S.inkSoft}/></div>
      <div style={{display: 'flex', alignItems: 'center', gap: 16, marginTop: 34, fontFamily: FONT.mono, fontSize: 50, fontWeight: 700, color: S.ink}}>
        <RepoGlyph size={54}/><span>{r.owner}<span style={{color: S.muted}}> / </span>{r.name}</span></div>
      <div style={{marginTop: 22, fontFamily: FONT.sans, fontWeight: 900, fontSize: ts, lineHeight: 1, letterSpacing: -2}}>
        {titleLines.map((l, i) => <div key={i} style={{whiteSpace: 'nowrap'}}>{l.split(' ').map((w, j) => {
          const at = wAt[wi++]; const k = sp(f, at, 12, 260, .5);
          return <span key={j} style={{display: 'inline-block', marginRight: ts * .26, color: i === titleLines.length - 1 ? S.accent : S.ink, opacity: f >= at ? 1 : 0,
            transform: `scale(${1.3 - .3 * k})`}}>{w}</span>;
        })}</div>)}
      </div>
      <div style={{marginTop: 30, fontFamily: FONT.mono, fontSize: 42, fontWeight: 700, color: S.accent, opacity: io(f, 10, 18)}}>github.com/{r.owner}/{r.name}</div>
      <div style={{marginTop: 18, fontFamily: FONT.sans, fontSize: 34, lineHeight: 1.25, color: S.inkSoft, opacity: io(f, 14, 24)}}>{r.description}</div>
    </div>
    <Mascot r={R.discovery.mimo} on={sp(f, 4, 12, 170)} clip>
      <MimoMascot state="excited" size={R.discovery.mimo[2] - 30} frame={f} mouth={mouth} amount={io(f, 6, 16)}/></Mascot>
    <div style={{...box(R.discovery.chips), display: 'flex', flexDirection: 'column', gap: 16, justifyContent: 'center'}}>
      {[b.text?.[0], `${r.license} · ${r.language}`].filter(Boolean).map((t, i) => {
        const k = sp(f, 14 + i * 6, 14, 220);
        return <div key={i} style={{alignSelf: 'flex-start', fontFamily: FONT.mono, fontWeight: 700, fontSize: 34, letterSpacing: 2, padding: '12px 22px', borderRadius: 14,
          color: i === 0 ? S.ground : S.ink, background: i === 0 ? S.accent : S.panel, border: `2px solid ${i === 0 ? S.accent : inkA(.14)}`, opacity: k,
          transform: `translateX(${(1 - k) * 60}px)`}}>{t}</div>;
      })}
    </div>
  </AbsoluteFill>;
};

/** PROOF: a real investigation, step by step on the narration: the app's behaviour → agent calls the tool → evidence → findings. */
const ProofBeat: React.FC<BP> = ({b, f, mouth}) => {
  const app = b.app!;
  const steps = b.steps ?? [];
  const at = steps.map((s, i) => atWord(b, s.at, Math.round(b.frames * (.2 + .2 * i))));
  const cur = at.filter(x => f >= x).length - 1;
  const [ax, ay, aw, ah] = R.proof.app;
  const img = ah - 70, warm = io(f, 6, 16);
  const stampAt = atWord(b, b.stamp?.at, Math.round(b.frames * .7));
  const step = steps[Math.max(0, cur)];
  const local = f - (at[Math.max(0, cur)] ?? 0);
  return <AbsoluteFill>
    <div style={{...box(R.proof.app)}}>
      {[{src: app.input, label: 'INPUT'}, {src: app.output, label: 'APP OUTPUT'}].map((x, i) =>
        <div key={i} style={{position: 'absolute', left: i * (img + 70), top: 0, width: img, height: img, borderRadius: 20, overflow: 'hidden', background: '#000',
          border: `3px solid ${i ? S.accent : inkA(.16)}`, opacity: i ? warm : 1, transform: i ? `translateX(${(1 - warm) * -40}px)` : undefined}}>
          <Img src={staticFile(x.src)} style={{width: '100%', height: '100%', objectFit: 'cover'}}/>
          <div style={{position: 'absolute', left: 8, top: 8, fontFamily: FONT.mono, fontWeight: 700, fontSize: 24, color: i ? S.ground : S.ink,
            background: i ? S.accent : 'rgba(14,15,18,.85)', padding: '2px 10px', borderRadius: 6}}>{x.label}</div>
        </div>)}
      <svg width={70} height={img} style={{position: 'absolute', left: img, top: 0}}>
        <path d={`M12,${img / 2} L56,${img / 2} M44,${img / 2 - 12} L56,${img / 2} L44,${img / 2 + 12}`} stroke={S.accent} strokeWidth={6} fill="none" strokeLinecap="round"
          strokeLinejoin="round" opacity={warm}/></svg>
      <div style={{position: 'absolute', left: 0, top: img + 12, width: aw, fontFamily: FONT.mono, fontSize: 30, color: S.ink, whiteSpace: 'nowrap'}}>
        <span style={{fontWeight: 700}}>{app.name}</span><span style={{color: S.accent}}> · {app.note}</span></div>
    </div>
    <Mascot r={R.proof.mimo} on={sp(f, 10, 12, 170)}><MimoMascot state="thinking" size={R.proof.mimo[2]} frame={f} mouth={mouth} look={{x: -.4, y: .9}}/></Mascot>
    <div style={{...box(R.proof.panel), borderRadius: 24, background: '#0A0B0D', border: `2px solid ${cur >= 0 ? accentA(.55) : inkA(.12)}`, overflow: 'hidden',
      boxShadow: '0 30px 80px rgba(0,0,0,.6)'}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 12, padding: '18px 24px', borderBottom: `2px solid ${inkA(.08)}`, fontFamily: FONT.mono, fontWeight: 700,
        fontSize: 32, letterSpacing: 2, color: S.accent}}>
        {[0, 1, 2].map(i => <span key={i} style={{width: 14, height: 14, borderRadius: 7, background: inkA(.25), display: 'inline-block'}}/>)}
        <span style={{marginLeft: 8}}>{cur >= 0 ? step.title : 'AGENT'}</span>
        <span style={{marginLeft: 'auto', fontSize: 24, color: S.muted}}>{cur >= 0 ? `${cur + 1}/${steps.length}` : ''}</span>
      </div>
      <div style={{padding: '22px 26px', fontFamily: step?.kind === 'findings' ? FONT.sans : FONT.mono, fontSize: step?.kind === 'findings' ? 46 : 33,
        fontWeight: step?.kind === 'findings' ? 800 : 500, lineHeight: step?.kind === 'findings' ? 1.5 : 1.45}}>
        {cur < 0 && <div style={{color: S.muted}}>waiting for the agent…<span style={{opacity: Math.round(f / 8) % 2}}>▍</span></div>}
        {cur >= 0 && step.lines.map((l, i) => {
          const on = local >= i * (step.kind === 'disasm' ? 3 : 5);
          const hi = step.highlight?.includes(i);
          if (step.kind === 'findings') return <div key={i} style={{opacity: on ? 1 : 0, color: S.ink, display: 'flex', gap: 16, alignItems: 'center',
            transform: `translateX(${on ? 0 : 30}px)`}}><span style={{color: S.ok}}>✓</span>{l}</div>;
          return <div key={i} style={{opacity: on ? 1 : 0, whiteSpace: 'pre', color: hi ? S.ground : l.startsWith('←') ? S.ok : l.startsWith('→') ? S.ink : S.inkSoft,
            background: hi ? S.accent : 'transparent', borderRadius: 6, padding: '0 8px', marginLeft: -8}}>{l}</div>;
        })}
      </div>
      {b.tag && <div style={{position: 'absolute', left: 0, right: 0, bottom: 14, textAlign: 'center', fontFamily: FONT.mono, fontSize: 24, letterSpacing: 1.5,
        color: S.muted}}>{b.tag}</div>}
    </div>
    <Stamp text={b.stamp?.text ?? ''} on={f >= stampAt ? sp(f, stampAt, 11, 240, .5) : 0} r={R.proof.stamp} size={50}/>
  </AbsoluteFill>;
};

/** POSSIBILITY: observe → investigate → rebuild, proved on one feature: the rebuilt filter matches the original byte for byte. */
const PossibilityBeat: React.FC<BP> = ({b, f}) => {
  const stages = b.stages ?? [];
  const at = stages.map((s, i) => atWord(b, s.at, Math.round(b.frames * (.1 + .25 * i))));
  const rebuildAt = at[at.length - 1] ?? Math.round(b.frames * .6);
  const c = b.compare!;
  const [cx, cy, cw, ch] = R.possibility.compare;
  const iw = (cw - 30) / 2;
  const wipe = io(f, rebuildAt, rebuildAt + 12);
  const badge = sp(f, rebuildAt + 12, 13, 230);
  const stampAt = Math.max(rebuildAt + 26, b.frames - 30);
  return <AbsoluteFill>
    <div style={{...box(R.possibility.stages), display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
      {stages.map((s, i) => {
        const on = f >= at[i], k = sp(f, at[i], 14, 240);
        return <React.Fragment key={i}>
          {i > 0 && <div style={{flex: 1, height: 6, margin: '0 10px', borderRadius: 3, background: f >= at[i] ? S.accent : inkA(.15)}}/>}
          <div style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: 34, letterSpacing: 2, padding: '14px 18px', borderRadius: 14, whiteSpace: 'nowrap',
            color: on ? S.ground : S.muted, background: on ? S.accent : S.panel, border: `2px solid ${on ? S.accent : inkA(.12)}`,
            transform: `scale(${on ? .9 + .1 * k : .9})`}}>{s.text}</div>
        </React.Fragment>;
      })}
    </div>
    {[c.left, c.right].map((x, i) => <div key={i} style={{position: 'absolute', left: cx + i * (iw + 30), top: cy, width: iw, height: ch, borderRadius: 22, overflow: 'hidden',
      background: S.panel, border: `3px solid ${i && wipe > .99 ? S.ok : inkA(.14)}`}}>
      <div style={{position: 'absolute', inset: 0, clipPath: i ? `inset(0 ${(1 - wipe) * 100}% 0 0)` : undefined}}>
        <Img src={staticFile(x.src)} style={{width: '100%', height: '100%', objectFit: 'cover'}}/></div>
      {i === 1 && wipe < 1 && <div style={{position: 'absolute', top: 0, bottom: 0, left: `${wipe * 100}%`, width: 6, background: S.accent, opacity: wipe > 0 ? 1 : 0}}/>}
      {i === 1 && wipe <= 0 && <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT.mono,
        fontSize: 32, color: S.muted}}>rebuilding…</div>}
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, padding: '10px 0', textAlign: 'center', fontFamily: FONT.mono, fontWeight: 700, fontSize: 28,
        letterSpacing: 1.5, color: S.ink, background: 'rgba(14,15,18,.85)'}}>{x.label}</div>
    </div>)}
    <div style={{...box(R.possibility.badge), display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: badge,
      transform: `scale(${.8 + .2 * badge})`}}>
      <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: 76, color: S.ok, letterSpacing: -1, whiteSpace: 'nowrap'}}>✓ {c.badge}</div>
      {c.sub && <div style={{fontFamily: FONT.mono, fontSize: 30, color: S.inkSoft}}>{c.sub}</div>}
    </div>
    <Stamp text={b.stamp?.text ?? ''} on={f >= stampAt ? sp(f, stampAt, 11, 240, .5) : 0} r={R.possibility.stamp} size={52} tone="ink"/>
  </AbsoluteFill>;
};

/* Generic app glyphs (original line art; no product icons). */
const ICONS = ['M4 6h16v12H4z M4 15l5-5 4 4 3-3 4 4', 'M4 6h16v12H4z M8 6v12 M16 6v12 M4 10h4 M16 10h4 M4 14h4 M16 14h4', 'M5 19l4-1 9-9-3-3-9 9z M14 7l3 3',
  'M12 4l8 4-8 4-8-4z M4 12l8 4 8-4 M4 16l8 4 8-4', 'M9 17V6l10-2v11 M9 17a2 2 0 1 1-4 0 2 2 0 0 1 4 0 M19 15a2 2 0 1 1-4 0 2 2 0 0 1 4 0',
  'M5 19V9 M10 19V5 M15 19v-7 M20 19v-11', 'M4 6h16v10H9l-5 4z', 'M8 9l-4 3 4 3 M16 9l4 3-4 3 M13 6l-2 12', 'M4 7l5-2 6 2 5-2v12l-5 2-6-2-5 2z M9 5v12 M15 7v12'];

/** QUESTION: Mimo points at a field of apps; the question lands with the narration, then a small follow CTA. The reel ends here. */
const QuestionBeat: React.FC<BP> = ({b, f, mouth}) => {
  const [ix, iy, iw, ih] = R.question.icons;
  const qAt = atWord(b, b.question_at, Math.round(b.frames * .4));
  const ctaAt = Math.min(b.frames - 16, atWord(b, 'engineer', b.frames - 20));
  const lines = balance(b.question ?? '', 2);
  const qs = Math.min(fitSize(lines, R.question.question[2], 120), R.question.question[3] / lines.length / 1.04);
  const cols = 3, cell = iw / cols;
  return <AbsoluteFill>
    {ICONS.map((d, i) => {
      const k = sp(f, 2 + i * 2, 13, 200);
      const x = ix + (i % cols) * cell + cell / 2, y = iy + Math.floor(i / cols) * (ih / 3) + ih / 6 + Math.sin(f / 12 + i) * 8;
      const s = 128;
      return <div key={i} style={{position: 'absolute', left: x - s / 2, top: y - s / 2, width: s, height: s, borderRadius: 32, background: i === 4 ? S.accent : S.panel,
        border: `2px solid ${i === 4 ? S.accent : inkA(.14)}`, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${k})`,
        boxShadow: '0 18px 40px rgba(0,0,0,.5)'}}>
        <svg width={72} height={72} viewBox="0 0 24 24"><path d={d} fill="none" stroke={i === 4 ? S.ground : S.ink} strokeWidth={1.8} strokeLinecap="round"
          strokeLinejoin="round"/></svg></div>;
    })}
    <Mascot r={R.question.mimo} on={sp(f, 0, 12, 170)}>
      <MimoMascot state="pointing" size={R.question.mimo[2]} frame={f} mouth={mouth} amount={io(f, 4, 14)} pointAngle={-38}/></Mascot>
    <div style={{...box(R.question.question), display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', fontFamily: FONT.sans,
      fontWeight: 900, fontSize: qs, lineHeight: 1.02, letterSpacing: -2}}>
      {lines.map((l, i) => { const k = sp(f, qAt + i * 5, 14, 230);
        return <div key={i} style={{whiteSpace: 'nowrap', color: i === lines.length - 1 ? S.accent : S.ink, opacity: k, transform: `translateY(${(1 - k) * 30}px)`}}>{l}</div>; })}
    </div>
    <div style={{...box(R.question.cta), display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: sp(f, ctaAt, 14, 230)}}>
      <div style={{fontFamily: FONT.sans, fontWeight: 800, fontSize: 40, color: S.ground, background: S.accent, padding: '14px 34px', borderRadius: 999,
        whiteSpace: 'nowrap'}}>{b.cta}</div></div>
  </AbsoluteFill>;
};

/** Split a phrase into n lines of similar length (word boundaries only). */
export const balance = (text: string, n: number) => {
  const words = text.split(' '), target = text.length / n, out: string[] = [];
  let cur = '';
  for (const w of words) {
    if (cur && (cur + ' ' + w).length > target + 3 && out.length < n - 1) { out.push(cur); cur = w; } else cur = cur ? cur + ' ' + w : w;
  }
  return [...out, cur];
};

// ---------------------------------------------------------------- overlays
const ReelSubtitles: React.FC<{g: number; groups: SubGroup[]}> = ({g, groups}) => {
  const t = g / 30;
  const grp = groups.find(x => t >= x.s && t < x.e);
  if (!grp) return null;
  const k = clamp01((t - grp.s) * 30 / 4);
  const s = L.subtitle;
  return <div style={{position: 'absolute', left: s.x, width: s.w, top: s.y, display: 'flex', justifyContent: 'center'}}>
    <div style={{fontFamily: FONT.sans, fontWeight: 800, fontSize: s.size, lineHeight: 1.15, color: S.ink, background: 'rgba(14,15,18,.86)', padding: '12px 24px',
      borderRadius: 16, textAlign: 'center', maxWidth: s.w, opacity: k, transform: `translateY(${(1 - k) * 8}px)`}}>
      {grp.words.map((w, i) => <span key={i} style={{color: w.em ? S.accent : S.ink}}>{w.w}{i < grp.words.length - 1 ? ' ' : ''}</span>)}
    </div>
  </div>;
};

const Bug: React.FC<{series: SeriesInfo; episode: EpisodeInfo; on: number}> = ({series, episode, on}) =>
  <div style={{...box(L.bug), display: 'flex', alignItems: 'center', gap: 14, opacity: on, fontFamily: FONT.mono, fontWeight: 700, fontSize: 28, letterSpacing: 3,
    color: S.inkSoft, whiteSpace: 'nowrap'}}>
    <span style={{color: S.ground, background: S.accent, padding: '3px 10px', borderRadius: 6}}>{episode.label}</span>{series.header}
  </div>;

/** QA overlay: the Instagram safe area. Never part of an export. */
export const ReelSafeGuides: React.FC = () => <AbsoluteFill style={{pointerEvents: 'none'}}>
  <div style={{position: 'absolute', left: L.safe.left, top: L.safe.top, width: SAFE_W, height: L.safe.bottom - L.safe.top, border: '3px solid #3f6'}}/>
  <div style={{position: 'absolute', left: L.subtitle.x, top: L.subtitle.y, width: L.subtitle.w, height: L.subtitle.max_h, border: '3px dashed #39f'}}/>
</AbsoluteFill>;

const BEATS: Record<string, React.FC<BP>> = {shock: ShockBeat, context: ContextBeat, mystery: MysteryBeat, discovery: DiscoveryBeat, proof: ProofBeat,
  possibility: PossibilityBeat, question: QuestionBeat};
const KEYL: Record<string, [number, number]> = {shock: [50, 30], context: [50, 35], mystery: [50, 40], discovery: [50, 40], proof: [50, 45], possibility: [50, 40],
  question: [45, 45]};

const BeatClock: React.FC<{b: Beat; p: ReelProps; mouth: number; Comp: React.FC<BP>}> = ({b, p, mouth, Comp}) => {
  const f = useCurrentFrame();
  const k = f / Math.max(1, b.frames);
  return <AbsoluteFill style={{transform: `scale(${1 + .03 * k})`, transformOrigin: '42% 40%'}}><Comp b={b} f={f} p={p} mouth={mouth}/></AbsoluteFill>;
};

export const SeriesReel: React.FC<ReelProps> = p => {
  ensureFonts();
  const g = useCurrentFrame();
  const cur = p.scenes.find(s => g >= s.from && g < s.from + s.frames);
  const [kx, ky] = cur ? KEYL[cur.kind] ?? [50, 40] : [50, 40];
  const mouth = p.mouth[g] ?? 0;
  const ctx = p.scenes.find(s => s.kind === 'context');
  const disc = p.scenes.find(s => s.kind === 'discovery');
  const bugOn = ctx && g >= ctx.from && !(disc && g >= disc.from && g < disc.from + disc.frames) ? io(g, ctx.from, ctx.from + 8) : 0;
  return <AbsoluteFill style={{background: S.ground}}>
    <Backdrop g={g} kx={kx} ky={ky}/>
    {p.scenes.map(s => {
      const Comp = BEATS[s.kind];
      return Comp ? <Sequence key={s.id} from={s.from} durationInFrames={s.frames} layout="none"><BeatClock b={s} p={p} mouth={mouth} Comp={Comp}/></Sequence> : null;
    })}
    {bugOn > 0 && <Bug series={p.series} episode={p.episode} on={bugOn}/>}
    {p.showSubtitles !== false && <ReelSubtitles g={g} groups={p.subtitles}/>}
    {p.safeGuides && <ReelSafeGuides/>}
  </AbsoluteFill>;
};
