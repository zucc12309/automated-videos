import React from 'react';
import {interpolate, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';
import {LayoutProps, Panel, cl} from './kit';
import {Counter, DrawPath, FlowDot, WordEmphasis, enterStyle, progress, typed} from './motion';
import {FONT, STAGE, clampText} from './tokens';

/* Semantic layouts added in V2. Each one shows structured data from the storyboard (scene.visualData) and falls back to
   the scene's points so a layout never renders empty. Text sizes stay >= 30 px at 1080 px width. */

const vd = (p: LayoutProps) => p.scene.visualData ?? {};
const items = (p: LayoutProps, key: 'steps' | 'timeline' | 'nodes', min = 2) => {
  const own = (vd(p)[key] as string[] | undefined) ?? [];
  return own.length >= min ? own : (p.scene.points.length ? p.scene.points : [p.scene.heading]);
};

const tokenize = (line: string) => {
  const out: {t: string; k: 'kw' | 'str' | 'num' | 'cm' | 'tx'}[] = [];
  const re = /(#.*$|\/\/.*$)|("[^"]*"|'[^']*'|`[^`]*`)|(\b\d[\d.]*\b)|(\b(?:const|let|var|function|return|import|from|export|async|await|def|class|if|else|for|while|new|npm|npx|pip|git|gh|brew|curl|install|run)\b)/g;
  let last = 0, m: RegExpExecArray | null;
  while ((m = re.exec(line))) {
    if (m.index > last) out.push({t: line.slice(last, m.index), k: 'tx'});
    out.push({t: m[0], k: m[1] ? 'cm' : m[2] ? 'str' : m[3] ? 'num' : 'kw'});
    last = m.index + m[0].length;
  }
  if (last < line.length) out.push({t: line.slice(last), k: 'tx'});
  return out;
};

/** Code editor window: syntax-highlighted lines type in; the focus line gets a gutter marker. */
export const CodeBlock: React.FC<LayoutProps> = p => {
  const {P, scene} = p;
  const f = useCurrentFrame();
  const lines = ((vd(p).code as string[] | undefined)?.length ? vd(p).code as string[] : scene.points.map(x => `// ${x}`)).slice(0, 8);
  const rows = typed(f, lines, {delay: 6, cps: 2.2, lineGap: 4});
  // Shrink long lines to fit the window instead of clipping them (mono glyph ~0.6em; floor 24 px).
  const size = Math.max(28, Math.min(40, 720 / (.6 * Math.max(1, ...lines.map(l => l.length)))));
  const colors = {kw: P.accent, str: P.dark ? '#a5d6a7' : '#2e7d32', num: P.accent2, cm: P.muted, tx: P.ink};
  const lang = (vd(p).code_language as string) || (lines.some(l => /^\$|npm|pip|git /.test(l)) ? 'shell' : 'code');
  return <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 22}}>
    <div style={{fontFamily: FONT.sans, fontWeight: 760, fontSize: 52, color: P.ink, letterSpacing: -1, ...enterStyle('reveal', f)}}>{clampText(scene.heading, 30)}</div>
    <Panel P={P} style={{overflow: 'hidden', padding: 0, ...enterStyle('scale', f, {delay: 2})}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 12, padding: '18px 24px', borderBottom: `2px solid ${P.line}`, background: P.bg2}}>
        {[0, 1, 2].map(i => <span key={i} style={{width: 16, height: 16, borderRadius: 8, background: P.line}}/>)}
        <span style={{marginLeft: 14, fontFamily: FONT.mono, fontSize: 28, color: P.muted}}>{lang}</span>
      </div>
      <div style={{padding: '22px 26px 30px'}}>
        {rows.map((r, i) => <div key={i} style={{display: 'flex', gap: 22, fontFamily: FONT.mono, fontSize: size, lineHeight: 1.55, whiteSpace: 'pre'}}>
          <span style={{color: r.active ? P.accent : P.muted, width: size, textAlign: 'right', opacity: .8}}>{i + 1}</span>
          <span>{tokenize(r.text).map((tk, k) => <span key={k} style={{color: colors[tk.k]}}>{tk.t}</span>)}
            {r.active && Math.floor(f / 8) % 2 === 0 && <span style={{background: P.ink, color: P.ink}}>▍</span>}</span>
        </div>)}
      </div>
    </Panel>
  </div>;
};

/** Request -> response flow: named parts in a column, connectors draw, packets travel along them. */
export const FlowDiagram: React.FC<LayoutProps> = p => {
  const {P} = p;
  const f = useCurrentFrame();
  const nodes = items(p, 'nodes').slice(0, 4);
  const h = STAGE.height, n = nodes.length;
  // Node height ~120 px at 40 px type; keep >= 50 px of visible connector between nodes and stay inside the stage.
  const top = 60, bottom = h - 70;
  const ys = nodes.map((_, i) => top + i * ((bottom - top) / Math.max(1, n - 1)));
  const fontSize = n >= 4 ? 40 : 46;
  const x = STAGE.width / 2;
  return <div style={{position: 'absolute', inset: 0}}>
    <svg width={STAGE.width} height={h} style={{position: 'absolute', inset: 0}}>
      {ys.slice(1).map((y, i) => <g key={i}>
        <DrawPath d={`M ${x} ${ys[i] + 58} L ${x} ${y - 58}`} color={P.line} width={8} delay={8 + i * 8}/>
        <FlowDot x1={x} y1={ys[i] + 58} x2={x} y2={y - 58} color={P.accent} delay={20 + i * 8}/>
      </g>)}
    </svg>
    {nodes.map((label, i) => {
      const e = progress(f, {delay: 2 + i * 8, duration: 14});
      const first = i === 0, last = i === n - 1;
      return <div key={i} style={{position: 'absolute', left: x, top: ys[i], transform: `translate(-50%, -50%) scale(${.9 + e * .1})`, opacity: e,
        minWidth: 420, padding: '14px 30px', borderRadius: 24, textAlign: 'center', background: first || last ? P.accent : P.surface,
        border: `3px solid ${first || last ? P.accent : P.line}`, color: first || last ? P.bg : P.ink, fontFamily: FONT.sans, fontWeight: 760, fontSize, lineHeight: 1.1, whiteSpace: 'nowrap'}}>
        <div style={{fontFamily: FONT.mono, fontSize: 28, opacity: .75, letterSpacing: 2}}>{first ? 'REQUEST' : last ? 'RESPONSE' : `STEP ${i}`}</div>
        {clampText(label, 22)}
      </div>;
    })}
  </div>;
};

/** Horizontal-to-vertical timeline: a rail draws, dated events land on it in order. */
export const Timeline: React.FC<LayoutProps> = p => {
  const {P, scene} = p;
  const f = useCurrentFrame();
  const events = items(p, 'timeline').length >= 2 ? items(p, 'timeline') : items(p, 'steps');
  const list = events.slice(0, 5);
  const rail = progress(f, {delay: 2, duration: 26});
  const gap = (STAGE.height - 120) / Math.max(1, list.length - 1);
  return <div style={{position: 'absolute', inset: 0}}>
    <div style={{fontFamily: FONT.mono, fontSize: 26, color: P.muted, letterSpacing: 3}}>{clampText(scene.heading.toUpperCase(), 34)}</div>
    <div style={{position: 'absolute', left: 60, top: 80, width: 6, height: (STAGE.height - 120) * rail, background: P.accent, borderRadius: 3}}/>
    {list.map((ev, i) => {
      const e = progress(f, {delay: 6 + i * 7, duration: 14});
      const [when, ...rest] = ev.split(/[:—-]\s*/);
      const has = rest.length > 0;
      return <div key={i} style={{position: 'absolute', left: 36, top: 80 + i * gap - 26, display: 'flex', alignItems: 'center', gap: 34, opacity: e,
        transform: `translateX(${(1 - e) * 40}px)`}}>
        <span style={{width: 54, height: 54, borderRadius: 27, background: P.bg, border: `6px solid ${P.accent}`, boxSizing: 'border-box'}}/>
        <span style={{fontFamily: FONT.sans, fontSize: 46, color: P.ink, fontWeight: 720}}>
          {has && <span style={{color: P.accent, fontFamily: FONT.mono, fontSize: 32, marginRight: 16}}>{clampText(when, 10)}</span>}
          {clampText(has ? rest.join(' ') : ev, 26)}</span>
      </div>;
    })}
  </div>;
};

/** Bar chart for a series from the source data; the last bar is the payoff and counts up. */
export const ChartBars: React.FC<LayoutProps> = p => {
  const {P, scene} = p;
  const f = useCurrentFrame();
  const labels = (vd(p).series_labels as string[] | undefined) ?? [];
  const values = ((vd(p).series_values as number[] | undefined) ?? []).slice(0, 6);
  if (values.length < 2) return null;
  const max = Math.max(...values, 1);
  const barW = Math.min(150, (STAGE.width - 40) / values.length - 30);
  return <div style={{position: 'absolute', inset: 0}}>
    <div style={{fontFamily: FONT.sans, fontWeight: 760, fontSize: 50, color: P.ink, letterSpacing: -1}}>{clampText(scene.heading, 30)}</div>
    <div style={{position: 'absolute', left: 0, right: 0, bottom: 70, height: 480, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around', borderBottom: `3px solid ${P.line}`}}>
      {values.map((val, i) => {
        const g = progress(f, {delay: 6 + i * 5, duration: 22});
        const last = i === values.length - 1;
        return <div key={i} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10}}>
          <span style={{fontFamily: FONT.mono, fontSize: 36, color: last ? P.accent : P.muted, opacity: g}}>{last ? <Counter value={String(val)} delay={8 + i * 5}/> : val.toLocaleString('en-US')}</span>
          <div style={{width: barW, height: 420 * (val / max) * g, borderRadius: '14px 14px 0 0', background: last ? P.accent : P.line}}/>
        </div>;
      })}
    </div>
    <div style={{position: 'absolute', left: 0, right: 0, bottom: 10, display: 'flex', justifyContent: 'space-around'}}>
      {values.map((_, i) => <span key={i} style={{fontFamily: FONT.sans, fontSize: 34, color: P.muted, width: barW + 30, textAlign: 'center'}}>{clampText(labels[i] ?? '', 10)}</span>)}
    </div>
  </div>;
};

/** Browser window demo: address bar, a hero line and the points as UI rows; a cursor clicks the primary action. */
export const BrowserMock: React.FC<LayoutProps> = p => {
  const {P, scene} = p;
  const f = useCurrentFrame();
  const rows = (scene.points.length ? scene.points : [scene.heading]).slice(0, 3);
  const url = clampText((vd(p).url as string) || (scene.label ? `${scene.label.toLowerCase().replace(/\s+/g, '')}.app` : 'app'), 28);
  const click = interpolate(f, [30, 34, 40], [1, .9, 1], cl);
  return <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center'}}>
    <Panel P={P} style={{width: '100%', overflow: 'hidden', padding: 0, ...enterStyle('slide', f, {direction: 'up'})}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 14, padding: '18px 22px', background: P.bg2, borderBottom: `2px solid ${P.line}`}}>
        {[0, 1, 2].map(i => <span key={i} style={{width: 16, height: 16, borderRadius: 8, background: P.line}}/>)}
        <span style={{flex: 1, marginLeft: 12, padding: '10px 20px', borderRadius: 14, background: P.surface, fontFamily: FONT.mono, fontSize: 30, color: P.muted}}>{url}</span>
      </div>
      <div style={{padding: '34px 36px 40px'}}>
        <div style={{fontFamily: FONT.sans, fontWeight: 820, fontSize: 54, color: P.ink, lineHeight: 1.08, letterSpacing: -1.2}}>{clampText(scene.heading, 32)}</div>
        {rows.map((r, i) => <div key={i} style={{marginTop: 20, padding: '20px 24px', borderRadius: 18, border: `2px solid ${i === 0 ? P.accent : P.line}`,
          background: i === 0 ? P.accent : P.surface, color: i === 0 ? P.bg : P.ink, fontFamily: FONT.sans, fontWeight: 700, fontSize: 42,
          transform: `scale(${i === 0 ? click : 1})`, ...enterStyle('slide', f, {delay: 8 + i * 5, direction: 'left', amplitude: .5})}}>{clampText(r, 30)}</div>)}
      </div>
    </Panel>
    <svg width="80" height="80" viewBox="0 0 24 24" style={{position: 'absolute', left: interpolate(f, [10, 30], [700, 420], cl), top: interpolate(f, [10, 30], [640, 400], cl), transform: `scale(${click})`}}>
      <path d="M5 2 L19 13 L12 14 L15 21 L12 22 L9 15 L5 19 Z" fill="#fff" stroke="#111" strokeWidth="1.6" strokeLinejoin="round"/>
    </svg>
  </div>;
};

/** Editorial warning: a rule draws, a caution label, the risk in large type. */
export const WarningCard: React.FC<LayoutProps> = p => {
  const {P, scene, beat} = p;
  const f = useCurrentFrame();
  const rule = progress(f, {delay: 2, duration: 18});
  return <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 30}}>
    <div style={{display: 'flex', alignItems: 'center', gap: 18, ...enterStyle('fade', f)}}>
      <span style={{width: 64, height: 64, borderRadius: 14, background: P.accent, color: P.bg, display: 'grid', placeItems: 'center', fontFamily: FONT.sans, fontWeight: 900, fontSize: 44}}>!</span>
      <span style={{fontFamily: FONT.mono, fontSize: 30, letterSpacing: 4, color: P.accent}}>{clampText((scene.label || 'CAUTION').toUpperCase(), 20)}</span>
    </div>
    <div style={{height: 6, width: `${rule * 100}%`, background: P.accent, borderRadius: 3}}/>
    <WordEmphasis text={clampText(scene.heading, 48)} emphasis={beat.focus} P={P} kind="underline" size={70} delay={6}/>
    {scene.points[0] && <div style={{fontFamily: FONT.sans, fontSize: 44, color: P.muted, ...enterStyle('reveal', f, {delay: 20})}}>{clampText(scene.points[0], 38)}</div>}
  </div>;
};

/** Split-screen comparison with titled columns; rows align so differences read across. */
export const SplitCompare: React.FC<LayoutProps> = p => {
  const {P, scene} = p;
  const f = useCurrentFrame();
  const v = vd(p);
  const titles = (v.compare_titles as string[] | undefined)?.length === 2 ? v.compare_titles as string[] : ['Before', 'After'];
  const left = (v.compare_left as string[] | undefined) ?? [];
  const right = (v.compare_right as string[] | undefined) ?? [];
  const rows = Math.max(left.length, right.length);
  const divider = progress(f, {delay: 0, duration: 16});
  const col = (side: 0 | 1, list: string[]) => <div style={{flex: 1, display: 'flex', flexDirection: 'column', gap: 22, padding: side ? '0 0 0 34px' : '0 34px 0 0'}}>
    <div style={{fontFamily: FONT.mono, fontSize: 30, letterSpacing: 3, color: side ? P.accent : P.muted, ...enterStyle('fade', f, {delay: 4})}}>{clampText(titles[side].toUpperCase(), 14)}</div>
    {Array.from({length: rows}, (_, i) => <div key={i} style={{minHeight: 110, padding: '20px 22px', borderRadius: 20, boxSizing: 'border-box',
      background: side ? P.accent : P.surface, border: `2px solid ${side ? P.accent : P.line}`, color: side ? P.bg : P.ink,
      fontFamily: FONT.sans, fontWeight: 720, fontSize: 42, lineHeight: 1.15,
      ...enterStyle('slide', f, {delay: 8 + i * 6 + side * 3, direction: side ? 'right' : 'left', amplitude: .6})}}>{clampText(list[i] ?? '—', 30)}</div>)}
  </div>;
  return <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 30}}>
    <div style={{fontFamily: FONT.sans, fontWeight: 800, fontSize: 52, color: P.ink, letterSpacing: -1}}>{clampText(scene.heading, 30)}</div>
    <div style={{position: 'relative', display: 'flex'}}>
      {col(0, left)}{col(1, right)}
      <div style={{position: 'absolute', left: '50%', top: 0, width: 4, height: `${divider * 100}%`, background: P.line}}/>
    </div>
  </div>;
};

/** Full-bleed cinematic footage, graded toward the theme so it sits with the graphics; heading overlaid by Remotion. */
export const Cinematic: React.FC<LayoutProps> = p => {
  const {P, scene, beat, dur} = p;
  const media = scene.media;
  // Stretch a short clip across the beat (never below half speed) instead of letting it run out.
  const rate = scene.mediaSeconds ? Math.max(.5, Math.min(1, scene.mediaSeconds / Math.max(.1, dur / 30))) : 1;
  return <div style={{position: 'absolute', left: -STAGE.left, top: -STAGE.top, width: 1080, height: 1920, overflow: 'hidden', background: P.bg}}>
    {media && <OffthreadVideo src={staticFile(media)} muted playbackRate={rate} style={{width: '100%', height: '100%', objectFit: 'cover',
      filter: `saturate(.86) contrast(1.06) brightness(${P.dark ? .82 : .95})`}}/>}
    <div style={{position: 'absolute', inset: 0, background: `linear-gradient(180deg, ${P.bg}cc 0%, ${P.bg}00 26%, ${P.bg}00 52%, ${P.bg}e6 78%, ${P.bg} 100%)`}}/>
    <div style={{position: 'absolute', inset: 0, mixBlendMode: 'soft-light', background: P.accent, opacity: .12}}/>
    <div style={{position: 'absolute', left: STAGE.left, right: 1080 - STAGE.left - STAGE.width, top: STAGE.top}}>
      <WordEmphasis text={clampText(scene.heading, 40)} emphasis={beat.focus} P={P} kind="underline" size={76} serif delay={4}/>
    </div>
  </div>;
};
