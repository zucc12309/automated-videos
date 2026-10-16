import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {ensureFonts} from '../premium/tokens';
import {Backdrop} from '../series/Episode';
import {MimoMascot} from '../series/Visuals';
import {accentA, clamp01, FONT, inkA, io, S, sp, SubGroup} from '../series/theme';
import L from './layout.json';

/* Creator reel built around real screen recordings (a game recorded with its engine's movie writer).
   Everything is data: examples/game_reel/build_game_reel.py times the beats to the measured narration and resolves every cut to
   frames. Text overlays live in L.headline (over the recording's own title bar, never over the play area), subtitles in L.subtitle,
   all inside the Instagram safe area (L.safe). No repository, account or project name is ever passed in. */

export type Seg = {clip: string; src: number; from: number; frames: number; crop_y?: number};
export type GBeat = {
  id: string; kind: string; from: number; frames: number; words: {w: string; s: number; e: number}[]; segs: Seg[];
  headline?: {lines: string[]; accent?: number[]; at?: number}; label?: {text: string; at: number}[]; pill?: {text: string; at: number};
  prompt?: {label: string; lines: string[]; out: number}; split?: {left: Seg & {label: string}; right: Seg & {label: string}; note: string};
  cta?: {big: string; small: string; handle: string; at: number};
};
export type GameReelProps = {fps: number; durationInFrames: number; beats: GBeat[]; subtitles: SubGroup[]; mouth: number[]; safeGuides?: boolean};

const box = (r: number[]): React.CSSProperties => ({position: 'absolute', left: r[0], top: r[1], width: r[2], height: r[3]});
const SRC_W = 1080;

/** The recording, cropped to the title bar + board and scaled into the card. One <OffthreadVideo> per cut, muted (the game's own
 *  sound is mixed by the builder). */
const Clip: React.FC<{seg: Seg; w: number; h: number; full?: boolean}> = ({seg, w, h, full}) => {
  const k = w / SRC_W;
  return <div style={{position: 'relative', width: w, height: h, overflow: 'hidden'}}>
    <OffthreadVideo src={staticFile(`game-reel/${seg.clip}.mp4`)} startFrom={Math.round(seg.src * 30)} muted
      style={{position: 'absolute', left: 0, top: full ? 0 : -(seg.crop_y ?? 0) * k, width: SRC_W * k, height: 1920 * k}}/>
  </div>;
};

const Card: React.FC<{segs: Seg[]; f: number; dim?: number}> = ({segs, f, dim = 0}) => {
  const [, , w, h] = L.card;
  return <div style={{...box(L.card), borderRadius: 34, overflow: 'hidden', boxShadow: `0 30px 90px rgba(0,0,0,.55), 0 0 0 3px ${inkA(.08)}`}}>
    {segs.map((s, i) => {
      // each cut lands with a small punch-in, so fast cuts read as deliberate, not as glitches
      const k = io(f, s.from, s.from + 7);
      return <Sequence key={i} from={s.from} durationInFrames={s.frames} layout="none">
        <div style={{position: 'absolute', inset: 0, transform: `scale(${1.045 - .045 * k})`, transformOrigin: '50% 45%'}}><Clip seg={s} w={w} h={h}/></div>
      </Sequence>;
    })}
    {dim > 0 && <div style={{position: 'absolute', inset: 0, background: `rgba(14,15,18,${dim})`}}/>}
    <div style={{position: 'absolute', left: 0, top: 0, width: w, height: h, borderRadius: 34, boxShadow: `inset 0 0 0 2px ${inkA(.1)}`}}/>
  </div>;
};

/** Big two-line statement over the recording's title bar. */
/** Font size that keeps the longest line (plus its plate) inside the safe width; `em` = average caps advance in ems. */
const fit = (lines: string[], size: number, em: number) => Math.min(size, Math.floor((L.headline[2] - 60) / (em * Math.max(...lines.map(l => l.length)))));

const Headline: React.FC<{lines: string[]; accent?: number[]; on: number; size?: number}> = ({lines, accent = [], on, size: want = 92}) => {
  const size = fit(lines, want, .56);
  return on <= 0 ? null : <div style={{...box(L.headline), display: 'flex', flexDirection: 'column', justifyContent: 'flex-start', alignItems: 'center', gap: 4,
    paddingTop: 14}}>
    {lines.map((l, i) => {
      const k = clamp01(on * 1.6 - i * .35);
      return <div key={i} style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: size, lineHeight: 1.02, letterSpacing: -1, whiteSpace: 'nowrap',
        color: accent.includes(i) ? S.accent : S.ink, background: 'rgba(14,15,18,.9)', padding: '6px 22px 10px', borderRadius: 18, opacity: k,
        transform: `translateY(${(1 - k) * 26}px) scale(${.92 + .08 * k})`}}>{l}</div>;
    })}
  </div>;
};

const Pill: React.FC<{text: string; on: number; r: number[]; tone?: 'accent' | 'dark'}> = ({text, on, r, tone = 'accent'}) =>
  on <= 0 ? null : <div style={{...box(r), display: 'flex', justifyContent: 'center', alignItems: 'center'}}>
    <div style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: 34, letterSpacing: 3, whiteSpace: 'nowrap', padding: '10px 24px', borderRadius: 999,
      color: tone === 'accent' ? S.ground : S.ink, background: tone === 'accent' ? S.accent : 'rgba(14,15,18,.9)', border: tone === 'dark' ? `2px solid ${accentA(.7)}` : 'none',
      opacity: clamp01(on * 2), transform: `scale(${.85 + .15 * on})`}}>{text}</div>
  </div>;

/** The real first prompt, typed out (verbatim excerpt), then it slides away to reveal the game it became. */
const PromptCard: React.FC<{p: NonNullable<GBeat['prompt']>; f: number}> = ({p, f}) => {
  const total = p.lines.join('').length;
  const typed = Math.min(total, Math.round(f * total / Math.max(1, p.out - 10)));
  const away = io(f, p.out, p.out + 10);
  let left = typed;
  return <div style={{...box(L.prompt), transform: `translateY(${-away * 160}px) scale(${1 - .25 * away})`, opacity: 1 - away}}>
    <div style={{position: 'absolute', inset: 0, borderRadius: 30, background: 'rgba(21,23,27,.96)', border: `2px solid ${accentA(.55)}`, padding: '34px 40px',
      boxShadow: '0 40px 120px rgba(0,0,0,.6)'}}>
      <div style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: 28, letterSpacing: 4, color: S.accent, marginBottom: 22}}>{p.label}</div>
      {p.lines.map((l, i) => {
        const shown = l.slice(0, Math.max(0, left));
        left -= l.length;
        return <div key={i} style={{fontFamily: FONT.mono, fontSize: i === 0 ? 36 : 33, fontWeight: i === 0 ? 700 : 500, lineHeight: 1.36, color: i === 0 ? S.ink : S.inkSoft,
          marginBottom: 18, minHeight: 1}}>{shown}{shown.length < l.length && shown.length > 0 ? <span style={{color: S.accent}}>▍</span> : null}</div>;
      })}
    </div>
  </div>;
};

const Split: React.FC<{s: NonNullable<GBeat['split']>; f: number}> = ({s, f}) => {
  const [lx, y, w, h] = L.split.left;
  const rx = L.split.right[0];
  const on = sp(f, 0, 16);
  const side = (seg: Seg & {label: string}, x: number, accent: boolean, d: number) =>
    <div style={{position: 'absolute', left: x, top: y, width: w, transform: `translateY(${(1 - sp(f, d, 16)) * 80}px)`, opacity: clamp01(sp(f, d, 16) * 1.4)}}>
      <div style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: 30, letterSpacing: 3, textAlign: 'center', marginBottom: 14, whiteSpace: 'nowrap',
        color: accent ? S.ground : S.ink, background: accent ? S.accent : 'rgba(14,15,18,.9)', borderRadius: 12, padding: '8px 0',
        border: accent ? 'none' : `2px solid ${inkA(.25)}`}}>{seg.label}</div>
      <div style={{borderRadius: 26, overflow: 'hidden', boxShadow: '0 24px 70px rgba(0,0,0,.55)', border: `3px solid ${accent ? S.accent : inkA(.2)}`}}>
        <Clip seg={{...seg, from: 0}} w={w - 6} h={h} full/></div>
    </div>;
  return <>
    {side(s.left, lx, false, 0)}
    {side(s.right, rx, true, 5)}
    <div style={{...box(L.split.note), display: 'flex', justifyContent: 'center', alignItems: 'center', opacity: on, fontFamily: FONT.mono, fontSize: 28,
      letterSpacing: 2, color: S.muted, whiteSpace: 'nowrap'}}>{s.note}</div>
  </>;
};

const Cta: React.FC<{c: NonNullable<GBeat['cta']>; f: number; g: number; mouth: number}> = ({c, f, g, mouth}) => {
  const on = sp(f, c.at, 13);
  const on2 = sp(f, c.at + 8, 13);
  const pulse = 1 + .025 * Math.sin((f - c.at) / 30 * Math.PI * 2 * 1.1) * clamp01((f - c.at - 14) / 10);
  return <>
    {on > 0 && <div style={{...box(L.headline), display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, paddingTop: 10}}>
      <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: fit([c.big], 104, .64), lineHeight: 1, letterSpacing: -1, whiteSpace: 'nowrap', color: S.ground,
        background: S.accent, padding: '12px 30px 16px', borderRadius: 22, transform: `scale(${(.7 + .3 * on) * pulse})`, opacity: clamp01(on * 2),
        boxShadow: '0 18px 60px rgba(0,0,0,.5)'}}>{c.big}</div>
      <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: 62, lineHeight: 1, whiteSpace: 'nowrap', color: S.ink, background: 'rgba(14,15,18,.92)',
        padding: '10px 26px 14px', borderRadius: 18, opacity: clamp01(on2 * 2), transform: `translateY(${(1 - on2) * 20}px)`}}>{c.small}</div>
    </div>}
    <div style={{...box(L.mimo), transform: `translateY(${(1 - sp(f, 4, 14)) * 220}px)`}}>
      <div style={{position: 'absolute', left: 0, bottom: 0}}><MimoMascot state="pointing" size={L.mimo[2]} frame={g} mouth={mouth} pointAngle={-55} amount={on}/></div>
    </div>
    <div style={{...box(L.handle), display: 'flex', alignItems: 'center', opacity: clamp01(sp(f, 6, 14) * 1.5)}}>
      <div style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: 30, letterSpacing: 3, color: S.ink, background: 'rgba(14,15,18,.9)', padding: '8px 18px',
        borderRadius: 12, border: `2px solid ${accentA(.6)}`}}>{c.handle}</div>
    </div>
  </>;
};

const Subtitles: React.FC<{g: number; groups: SubGroup[]}> = ({g, groups}) => {
  const t = g / 30;
  const grp = groups.find(x => t >= x.s && t < x.e);
  if (!grp) return null;
  const k = clamp01((t - grp.s) * 30 / 4);
  const s = L.subtitle;
  return <div style={{position: 'absolute', left: s.x, width: s.w, top: s.y, display: 'flex', justifyContent: 'center'}}>
    <div style={{fontFamily: FONT.sans, fontWeight: 800, fontSize: s.size, lineHeight: 1.15, color: S.ink, background: 'rgba(14,15,18,.88)', padding: '12px 24px',
      borderRadius: 16, textAlign: 'center', maxWidth: s.w, opacity: k, transform: `translateY(${(1 - k) * 8}px)`}}>
      {grp.words.map((w, i) => <span key={i} style={{color: w.em ? S.accent : S.ink}}>{w.w}{i < grp.words.length - 1 ? ' ' : ''}</span>)}
    </div>
  </div>;
};

export const GameSafeGuides: React.FC = () => <AbsoluteFill style={{pointerEvents: 'none'}}>
  <div style={{...box([L.safe.left, L.safe.top, L.safe.right - L.safe.left, L.safe.bottom - L.safe.top]), border: '3px solid #3f6'}}/>
  <div style={{...box([L.subtitle.x, L.subtitle.y, L.subtitle.w, L.subtitle.max_h]), border: '3px dashed #39f'}}/>
  <div style={{...box(L.headline), border: '3px dashed #f3c'}}/>
</AbsoluteFill>;

const BeatView: React.FC<{b: GBeat; mouth: number; g0: number}> = ({b, mouth, g0}) => {
  const f = useCurrentFrame();
  const g = g0 + f;
  const segs = b.segs.map(s => ({...s, from: s.from - b.from}));
  const headOn = b.headline ? clamp01((f - ((b.headline.at ?? b.from) - b.from) + 1) / 6) : 0;
  const labels = b.label ?? [];
  const cur = labels.filter(l => f >= l.at - b.from).pop();
  return <AbsoluteFill>
    {b.split ? <Split s={b.split} f={f}/> : <Card segs={segs} f={f} dim={b.prompt ? .55 * (1 - io(f, b.prompt.out - b.from, b.prompt.out - b.from + 10)) : 0}/>}
    {b.prompt && <PromptCard p={{...b.prompt, out: b.prompt.out - b.from}} f={f}/>}
    {b.headline && <Headline lines={b.headline.lines} accent={b.headline.accent} on={b.kind === 'hook' ? 1 : headOn}/>}
    {cur && <Headline key={cur.text} lines={[cur.text]} accent={[0]} size={78} on={clamp01((f - (cur.at - b.from) + 1) / 5)}/>}
    {b.pill && <Pill text={b.pill.text} on={sp(f, b.pill.at - b.from, 14)} r={L.pill}/>}
    {b.cta && <Cta c={{...b.cta, at: b.cta.at - b.from}} f={f} g={g} mouth={mouth}/>}
  </AbsoluteFill>;
};

export const GameReel: React.FC<GameReelProps> = p => {
  ensureFonts();
  const g = useCurrentFrame();
  const mouth = p.mouth[g] ?? 0;
  return <AbsoluteFill style={{background: S.ground}}>
    <Backdrop g={g} kx={50} ky={38}/>
    {p.beats.map(b => <Sequence key={b.id} from={b.from} durationInFrames={b.frames} layout="none"><BeatView b={b} mouth={mouth} g0={b.from}/></Sequence>)}
    <Subtitles g={g} groups={p.subtitles}/>
    {p.safeGuides && <GameSafeGuides/>}
  </AbsoluteFill>;
};

/** Cover: one real frame of the game, large, under the statement. Square-safe content between y 420 and 1500 (the 1:1 crop);
 *  the 4:5 crop (285–1635) adds the brand line. */
export type GameCoverProps = {frame: string; crop: [number, number]; lines: string[]; accent: number[]; tag: string; handle: string; mask?: boolean};
export const GameReelCover: React.FC<GameCoverProps> = p => {
  ensureFonts();
  const C = L.cover;
  const cw = C.card[2];
  const k = cw / SRC_W;
  return <AbsoluteFill style={{background: S.ground}}>
    <Backdrop g={0} kx={50} ky={55}/>
    <div style={{...box(C.card), borderRadius: 36, overflow: 'hidden', boxShadow: `0 40px 120px rgba(0,0,0,.6), 0 0 0 4px ${accentA(.8)}`}}>
      <Img src={staticFile(p.frame)} style={{position: 'absolute', left: 0, top: -p.crop[0] * k, width: cw, height: 1920 * k}}/>
    </div>
    <div style={{...box(C.headline), display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6}}>
      {p.lines.map((l, i) => <div key={i} style={{fontFamily: FONT.sans, fontWeight: 900, lineHeight: 1.04, letterSpacing: -2, whiteSpace: 'nowrap',
        fontSize: Math.min(96, Math.floor((C.headline[2] - 20) / (.56 * Math.max(...p.lines.map(x => x.length))))),
        color: p.accent.includes(i) ? S.accent : S.ink}}>{l}</div>)}
    </div>
    <div style={{...box(C.tag), display: 'flex', justifyContent: 'center', alignItems: 'center'}}>
      <div style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: 28, letterSpacing: 4, color: S.ground, background: S.accent, padding: '8px 22px', borderRadius: 999}}>{p.tag}</div>
    </div>
    <div style={{...box(C.brand), display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16}}>
      <MimoMascot state="excited" size={64} frame={0} amount={.5}/>
      <div style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: 30, letterSpacing: 4, color: S.inkSoft}}>{p.handle}</div>
    </div>
    {p.mask && <AbsoluteFill>
      {/* every crop Instagram applies to a Reel cover; content must sit inside the solid green box */}
      <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height: 240, background: 'rgba(255,0,80,.45)'}}/>
      <div style={{position: 'absolute', left: 0, top: 1680, width: 1080, height: 240, background: 'rgba(255,0,80,.45)'}}/>
      <div style={{position: 'absolute', left: 0, top: 285, width: 1080, height: 1350, border: '4px dashed #f80'}}/>
      <div style={{position: 'absolute', left: 0, top: 420, width: 1080, height: 1080, border: '4px dashed #3cf'}}/>
      <div style={{position: 'absolute', left: 160, top: 285, width: 760, height: 1350, border: '4px dashed #c6f'}}/>
      <div style={{...box(C.safe), border: '5px solid #3f6'}}/>
    </AbsoluteFill>}
  </AbsoluteFill>;
};
