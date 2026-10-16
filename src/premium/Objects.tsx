import React from 'react';
import {interpolate, OffthreadVideo, staticFile} from 'remotion';
import {Beat, Props, Repo, Scene} from '../shared';
import {Selected} from './Frame';
import {C, EASE, F, H, STAGE, T, W, clamp01, clip, shortId} from './tokens';

/* Scene objects in the FIELDNOTES language: one dark card at a time, centred in the stage, resolving from blur.
   Motion is semantic: rows switch on, code types, commands execute, links draw, the before becomes the after. */

export type ObjProps = {beat: Beat; scene: Scene; props: Props; f: number; dur: number; count: number};

const cl = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const prog = (f: number, delay = 0, len: number = T.motion.durations.enter) => clamp01(interpolate(f - delay, [0, len], [0, 1], {...cl, easing: EASE.enter}));
const vd = (s: Scene) => (s.visualData ?? {}) as Record<string, any>;
const repoOf = (p: ObjProps): Repo | undefined => (p.scene.item ?? 0) > 0 ? p.props.repos?.[(p.scene.item ?? 1) - 1] : undefined;

/** Entrance used by every object: rises 30 px, sharpens from blur, settles from 97 %. */
export const enterStyle = (f: number, delay = 0): React.CSSProperties => {
  const p = prog(f, delay);
  return {opacity: p, filter: `blur(${(1 - p) * T.motion.blur.enter}px)`, transform: `translateY(${(1 - p) * 30}px) scale(${.97 + .03 * p})`};
};

export const Card: React.FC<{children: React.ReactNode; style?: React.CSSProperties; pad?: number}> = ({children, style, pad = 48}) =>
  <div style={{width: STAGE.width, boxSizing: 'border-box', background: C.surface, border: T.border.card, borderRadius: T.radius.card,
    boxShadow: T.shadow.card, padding: pad, ...style}}>{children}</div>;

const Centre: React.FC<{children: React.ReactNode; f: number; delay?: number}> = ({children, f, delay = 0}) =>
  <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', ...enterStyle(f, delay)}}>{children}</div>;

const Meta: React.FC<{children: React.ReactNode; style?: React.CSSProperties}> = ({children, style}) =>
  <div style={{fontFamily: F.mono, fontSize: T.type.minMeta, letterSpacing: 2, color: C.muted, ...style}}>{children}</div>;

const Avatar: React.FC<{name: string; size?: number}> = ({name, size = 112}) =>
  <div style={{width: size, height: size, borderRadius: size * .26, background: C.avatar, display: 'grid', placeItems: 'center', color: '#fff',
    fontFamily: F.sans, fontWeight: 900, fontSize: size * .38, flexShrink: 0}}>{name.replace(/[^a-z0-9]/gi, '').slice(0, 2).toUpperCase()}</div>;

const Badge: React.FC<{children: React.ReactNode}> = ({children}) =>
  <span style={{fontFamily: F.mono, fontWeight: 700, fontSize: 32, color: '#0c2a17', background: C.success, borderRadius: 8, padding: '4px 10px', letterSpacing: 1}}>{children}</span>;

const Toggle: React.FC<{on: number}> = ({on}) =>
  <span style={{width: 96, height: 56, borderRadius: 28, background: on > .5 ? C.successStrong : C.line, position: 'relative', flexShrink: 0}}>
    <span style={{position: 'absolute', top: 6, left: 6 + on * 40, width: 44, height: 44, borderRadius: 22, background: '#fff', boxShadow: '0 2px 6px #0006'}}/>
  </span>;

const count = (f: number, value: number, delay = 8, len = 34) => Math.round(value * (1 - Math.pow(1 - clamp01((f - delay) / len), 3)));

// ---------------------------------------------------------------- RepositoryReveal
export const RepositoryReveal: React.FC<ObjProps> = p => {
  const repo = repoOf(p);
  if (!repo) return <PullQuote {...p}/>;
  const {f} = p;
  return <Centre f={f}><Card>
    <div style={{display: 'flex', gap: 30, alignItems: 'center'}}>
      <Avatar name={repo.name}/>
      <div>
        <Meta>github.com/{clip(repo.owner, 22)}</Meta>
        <div style={{display: 'flex', alignItems: 'center', gap: 16, marginTop: 4}}>
          <span style={{fontFamily: F.sans, fontWeight: 800, fontSize: 64, color: C.ink, letterSpacing: -1.5}}>{clip(repo.name, 16)}</span><Badge>REPO</Badge>
        </div>
      </div>
    </div>
    <div style={{fontFamily: F.serif, fontStyle: 'italic', fontSize: 50, lineHeight: 1.18, color: C.ink, marginTop: 34, ...enterStyle(f, 6)}}>
      {clip(repo.description, 96)}</div>
    {repo.topics.length > 0 && <div style={{display: 'flex', flexWrap: 'wrap', gap: 14, marginTop: 28}}>
      {[repo.language, ...repo.topics].filter(Boolean).slice(0, 4).map((t, i) => <span key={i} style={{fontFamily: F.mono, fontSize: 32, color: '#aab8ff',
        background: C.accentSoft, borderRadius: 10, padding: '6px 14px', ...enterStyle(f, 10 + i * 3)}}>{clip(t, 14)}</span>)}</div>}
    <div style={{borderTop: `2px solid ${C.line}`, marginTop: 34, paddingTop: 26, display: 'flex', justifyContent: 'space-between', alignItems: 'baseline'}}>
      <span style={{fontFamily: F.sans, fontWeight: 800, fontSize: 68, color: C.ink}}>★ {count(f, repo.stars).toLocaleString('en-US')}</span>
      <Meta>GITHUB STARS</Meta>
    </div>
  </Card></Centre>;
};

// ---------------------------------------------------------------- Points panel (key/value rows, from Reference A)
export const PointsPanel: React.FC<ObjProps> = p => {
  const {scene, f} = p;
  const label = scene.label || scene.heading;
  const rows = (scene.points.length ? scene.points : [scene.heading]).slice(0, 3);
  const settle = Math.min(40, p.dur * .55);
  return <Centre f={f}><Card>
    <Meta style={{textAlign: 'center'}}>{clip(scene.heading.toLowerCase(), 34)}</Meta>
    <div style={{fontFamily: F.mono, fontSize: 40, color: C.ink, marginTop: 20}}>
      <span style={{color: C.keyPink}}>key</span> = hash(<span style={{color: C.accent}}>{clip(label.toLowerCase().replace(/\s+/g, '-'), 18)}</span>)</div>
    {rows.map((r, i) => <div key={i} style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 20, padding: '24px 28px',
      borderRadius: T.radius.row, background: C.surfaceRaised, ...enterStyle(f, 8 + i * 6)}}>
      <span style={{fontFamily: F.sans, fontSize: 44, color: C.ink}}>{clip(r, 22)}</span>
      <span style={{fontFamily: F.mono, fontSize: 34, color: C.success}}>{shortId(r)}</span></div>)}
    <div style={{marginTop: 26, display: 'inline-block', background: C.pill, color: C.pillInk, borderRadius: 999, padding: '14px 28px', fontFamily: F.sans,
      fontWeight: 800, fontSize: 40, opacity: prog(f, settle, 10), transform: `scale(${.9 + .1 * prog(f, settle, 10)})`}}>✓ {clip(rows[0], 24)}</div>
  </Card></Centre>;
};

// ---------------------------------------------------------------- Phone notification (BrowserInteraction for apps)
export const PhoneNotice: React.FC<ObjProps> = p => {
  const {scene, props, f, dur} = p;
  const tap = clamp01((f - Math.min(46, dur * .6)) / 6);
  const app = (props.series || scene.label || 'app').toUpperCase();
  return <Centre f={f}>
    <div style={{width: 480, height: 840, borderRadius: 70, border: `6px solid ${C.line}`, background: '#08090c', boxShadow: T.shadow.card, padding: 24, boxSizing: 'border-box',
      display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
      <div style={{width: 150, height: 36, borderRadius: 18, background: '#000', marginTop: 4}}/>
      <div style={{fontFamily: F.sans, fontWeight: 600, fontSize: 34, color: C.muted, marginTop: 50}}>Friday</div>
      <div style={{fontFamily: F.sans, fontWeight: 700, fontSize: 132, color: C.ink, lineHeight: 1}}>9:41</div>
      <div style={{width: '100%', marginTop: 50, background: '#1d1e25ee', borderRadius: 30, padding: 26, boxSizing: 'border-box', ...enterStyle(f, 14)}}>
        <div style={{fontFamily: F.mono, fontSize: 32, color: C.muted, letterSpacing: 1}}>{clip(app, 14)} · now</div>
        <div style={{fontFamily: F.sans, fontWeight: 800, fontSize: 40, color: C.ink, marginTop: 8, lineHeight: 1.1}}>{clip(scene.heading, 26)}</div>
        <div style={{fontFamily: F.sans, fontSize: 40, color: C.inkSoft, marginTop: 6}}>{clip(scene.points[0] ?? scene.label ?? '', 26)}</div>
        <div style={{display: 'flex', gap: 14, marginTop: 20}}>
          <span style={{flex: 1, textAlign: 'center', padding: '14px 0', borderRadius: 18, background: C.line, color: C.inkSoft, fontFamily: F.sans, fontSize: 34}}>Later</span>
          <span style={{flex: 1, textAlign: 'center', padding: '14px 0', borderRadius: 18, background: C.successStrong, color: '#05240f', fontFamily: F.sans, fontWeight: 800,
            fontSize: 34, transform: `scale(${1 - .08 * Math.sin(tap * Math.PI)})`}}>✓ Done</span>
        </div>
      </div>
    </div>
  </Centre>;
};

// ---------------------------------------------------------------- Emphasis tile (serif word on a quiet grid)
export const EmphasisTile: React.FC<ObjProps> = p => {
  const {beat, scene, f} = p;
  const word = clip((beat.focus || scene.emphasis || scene.heading).replace(/[.,!?;:]$/, ''), 18);
  const size = word.length > 12 ? 120 : 150;
  return <Centre f={f}>
    <div style={{position: 'relative', width: STAGE.width, height: 520, borderRadius: T.radius.card, overflow: 'hidden', background: C.surface, border: T.border.card}}>
      <div style={{position: 'absolute', inset: 0, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gridTemplateRows: 'repeat(2, 1fr)', gap: 4, padding: 4}}>
        {Array.from({length: 8}, (_, i) => <div key={i} style={{background: C.surfaceRaised, borderRadius: 12, opacity: .55 + .45 * prog(f, i * 2, 10)}}/>)}
      </div>
      <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{fontFamily: F.serif, fontStyle: 'italic', fontSize: size, color: C.ink, lineHeight: 1, ...enterStyle(f, 6)}}>{word}</div>
        <Meta style={{marginTop: 22, letterSpacing: 6}}>{clip(scene.heading.toUpperCase(), 28)}</Meta>
      </div>
    </div>
  </Centre>;
};

// ---------------------------------------------------------------- Terminal execution
export const TerminalRun: React.FC<ObjProps> = p => {
  const {scene, f} = p;
  const repo = repoOf(p);
  const own = ((vd(scene).code as string[] | undefined) ?? []).filter(l => l.trim());
  const lines = own.length ? own.slice(0, 6) : [`$ ${repo ? `gh repo clone ${repo.full_name}` : clip(scene.heading.toLowerCase(), 28)}`, ...scene.points.slice(0, 3).map(x => `✓ ${x}`)];
  let t = f - 8;
  return <Centre f={f}><Card pad={0} style={{overflow: 'hidden', background: '#0d0e12'}}>
    <div style={{display: 'flex', gap: 12, padding: '22px 28px', borderBottom: `2px solid ${C.line}`, alignItems: 'center'}}>
      {['#ff5f57', '#febc2e', '#28c840'].map(c => <span key={c} style={{width: 18, height: 18, borderRadius: 9, background: c, opacity: .8}}/>)}
      <Meta style={{marginLeft: 16}}>{clip(scene.label || 'terminal', 20)}</Meta>
    </div>
    <div style={{padding: '30px 34px 40px'}}>
      {lines.map((raw, i) => {
        const cmd = /^[$>]/.test(raw);
        const text = clip(raw.replace(/^[$>]\s*/, ''), 30);
        const typedLen = cmd ? Math.max(0, Math.min(text.length, Math.floor(t * 1.4))) : (t > 0 ? text.length : 0);
        const shown = cmd ? text.slice(0, typedLen) : text;
        const visible = t > 0;
        const active = cmd && typedLen < text.length && visible;
        t -= cmd ? text.length / 1.4 + 6 : 5;
        return visible ? <div key={i} style={{fontFamily: F.mono, fontSize: 40, lineHeight: 1.6, color: cmd ? C.ink : C.success, whiteSpace: 'pre'}}>
          {cmd && <span style={{color: C.accent}}>{raw[0]} </span>}{shown}{active && <span style={{background: C.ink}}> </span>}</div> : null;
      })}
    </div>
  </Card></Centre>;
};

// ---------------------------------------------------------------- Code editor / Git diff reveal
const SYNTAX = /(#.*$|\/\/.*$)|("[^"]*"|'[^']*'|`[^`]*`)|(\b\d[\d.]*\b)|(\b(?:const|let|function|return|import|from|export|async|await|def|class|if|else|for|new|npm|npx|pip|git)\b)/g;
const colour = (line: string) => {
  const out: React.ReactNode[] = [];
  let last = 0, m: RegExpExecArray | null, k = 0;
  SYNTAX.lastIndex = 0;
  while ((m = SYNTAX.exec(line))) {
    if (m.index > last) out.push(line.slice(last, m.index));
    out.push(<span key={k++} style={{color: m[1] ? C.dim : m[2] ? C.success : m[3] ? C.warn : C.keyPink}}>{m[0]}</span>);
    last = m.index + m[0].length;
  }
  out.push(line.slice(last));
  return out;
};

export const CodeEditor: React.FC<ObjProps> = p => {
  const {scene, f} = p;
  const lines = ((vd(scene).code as string[] | undefined) ?? scene.points.map(x => `// ${x}`)).slice(0, 8);
  const lang = (vd(scene).code_language as string | undefined) ?? '';
  // A diff only when declared, or when both additions and removals are present (markdown '- ' lists are not removals).
  const diff = lang === 'diff' || (lines.some(l => /^\+ /.test(l)) && lines.some(l => /^- /.test(l)));
  const longest = Math.max(1, ...lines.map(l => l.length));
  const size = Math.max(30, Math.min(40, 760 / (.6 * longest)));
  return <Centre f={f}><Card pad={0} style={{overflow: 'hidden'}}>
    <div style={{padding: '22px 30px', borderBottom: `2px solid ${C.line}`, display: 'flex', justifyContent: 'space-between'}}>
      <Meta>{clip(scene.heading, 26)}</Meta><Meta>{(vd(scene).code_language as string) || (diff ? 'diff' : 'code')}</Meta>
    </div>
    <div style={{padding: '24px 30px 34px'}}>
      {lines.map((l, i) => {
        const d = diff ? l.match(/^([+-]) /)?.[1] : undefined;
        const at = 8 + i * (diff ? 7 : 5);
        const pIn = prog(f, at, 10);
        const strike = d === '-' ? clamp01((f - at - 14) / 12) : 0;
        return <div key={i} style={{display: 'flex', gap: 22, fontFamily: F.mono, fontSize: size, lineHeight: 1.6, whiteSpace: 'pre', opacity: pIn,
          background: d === '+' ? `${C.success}1f` : d === '-' ? `${C.danger}1a` : 'transparent', borderRadius: 8, padding: '0 10px',
          transform: `translateX(${(1 - pIn) * 24}px)`}}>
          <span style={{color: d === '+' ? C.success : d === '-' ? C.danger : C.dim, width: size * .7}}>{d ?? i + 1}</span>
          <span style={{color: C.ink, textDecoration: strike > 0 ? 'line-through' : 'none', opacity: 1 - strike * .45}}>{colour(d ? l.slice(2) : l)}</span>
        </div>;
      })}
    </div>
  </Card></Centre>;
};

// ---------------------------------------------------------------- Before / after transform (CodeMorph for prompts)
export const BeforeAfter: React.FC<ObjProps> = p => {
  const {scene, f, dur} = p;
  const v = vd(scene);
  const before: string[] = (v.prompt_before as string[] | undefined)?.length ? v.prompt_before : (v.compare_left as string[] | undefined) ?? [scene.points[0] ?? ''];
  const after: string[] = (v.prompt_after as string[] | undefined)?.length ? v.prompt_after : (v.compare_right as string[] | undefined) ?? scene.points.slice(1);
  const titles: string[] = (v.compare_titles as string[] | undefined)?.length === 2 ? v.compare_titles : ['Before', 'After'];
  const swap = Math.min(dur * .42, 70);
  const m = clamp01((f - swap) / 16);
  const block = (lines: string[], good: boolean, o: number, y: number) => <div style={{position: 'absolute', inset: 0, opacity: o, transform: `translateY(${y}px)`,
    filter: `blur(${(1 - o) * 8}px)`}}>
    <div style={{display: 'flex', alignItems: 'center', gap: 16}}>
      <span style={{width: 56, height: 56, borderRadius: 16, display: 'grid', placeItems: 'center', fontSize: 34, fontWeight: 900, fontFamily: F.sans,
        background: good ? C.successStrong : `${C.danger}33`, color: good ? '#05240f' : C.danger}}>{good ? '✓' : '✕'}</span>
      <Meta style={{fontSize: 32, color: good ? C.success : C.danger, letterSpacing: 4}}>{clip(titles[good ? 1 : 0].toUpperCase(), 18)}</Meta>
    </div>
    <div style={{marginTop: 26, fontFamily: good ? F.sans : F.mono, fontSize: good ? 44 : 42, lineHeight: 1.3, color: good ? C.ink : C.inkSoft}}>
      {lines.slice(0, 5).map((l, i) => <div key={i} style={{marginTop: i ? 10 : 0, ...(good ? enterStyle(f - swap, 4 + i * 6) : {})}}>
        {good && <span style={{color: C.success}}>→ </span>}{clip(l, 40)}</div>)}
    </div>
  </div>;
  return <Centre f={f}><Card style={{height: 640, position: 'relative'}}>
    <div style={{position: 'relative', height: '100%'}}>
      {block(before, false, 1 - m, -m * 30)}
      {m > 0 && block(after, true, m, (1 - m) * 30)}
    </div>
  </Card></Centre>;
};

// ---------------------------------------------------------------- Workflow connection (flow + hub)
export const Workflow: React.FC<ObjProps & {hub?: boolean}> = p => {
  const {scene, f, hub} = p;
  const repo = repoOf(p);
  const v = vd(scene);
  const nodes: string[] = ((v.nodes as string[] | undefined)?.length ? v.nodes : [...scene.points, ...(repo?.topics ?? [])]).filter(Boolean).slice(0, hub ? 4 : 4);
  const w = STAGE.width, h = STAGE.height;
  const centre = {x: w / 2, y: h / 2};
  const pos = hub ? [[w * .22, h * .16], [w * .78, h * .2], [w * .22, h * .84], [w * .78, h * .82]].slice(0, nodes.length)
    : nodes.map((_, i) => [w / 2, 70 + i * ((h - 140) / Math.max(1, nodes.length - 1))]);
  const links = hub ? pos.map(pt => [centre.x, centre.y, pt[0], pt[1]]) : pos.slice(1).map((pt, i) => [pos[i][0], pos[i][1] + 62, pt[0], pt[1] - 62]);
  const node = (label: string, i: number, strong: boolean) => <div key={i} style={{position: 'absolute', left: pos[i][0], top: pos[i][1],
    transform: `translate(-50%, -50%) scale(${.92 + .08 * prog(f, 6 + i * 7, 12)})`, opacity: prog(f, 6 + i * 7, 12), padding: '18px 30px', borderRadius: 22,
    background: strong ? C.pill : C.surface, color: strong ? C.pillInk : C.ink, border: T.border.card, boxShadow: T.shadow.card, fontFamily: F.sans,
    fontWeight: 700, fontSize: 44, lineHeight: 1.15, textAlign: 'center', maxWidth: hub ? 400 : 720, width: 'max-content'}}>{clip(label, hub ? 28 : 30)}</div>;
  return <div style={{position: 'absolute', inset: 0}}>
    <svg width={w} height={h} style={{position: 'absolute', inset: 0}}>
      {links.map(([x1, y1, x2, y2], i) => {
        const d = clamp01((f - 12 - i * 7) / 14);
        const period = 34, k = ((f - 26 - i * 7) % period + period) % period / period;
        return <g key={i}>
          <line x1={x1} y1={y1} x2={x1 + (x2 - x1) * d} y2={y1 + (y2 - y1) * d} stroke={C.line} strokeWidth={6} strokeLinecap="round"/>
          {f > 26 + i * 7 && <circle cx={x1 + (x2 - x1) * k} cy={y1 + (y2 - y1) * k} r={11} fill={C.accent}/>}
        </g>;
      })}
    </svg>
    {nodes.map((n, i) => node(n, i, !hub && (i === 0 || i === nodes.length - 1)))}
    {hub && <div style={{position: 'absolute', left: centre.x, top: centre.y, transform: `translate(-50%, -50%) scale(${.85 + .15 * prog(f, 0, 14)})`,
      padding: '28px 44px', borderRadius: 48, background: C.pill, color: C.pillInk, fontFamily: F.sans, fontWeight: 900, fontSize: 52, lineHeight: 1.1,
      textAlign: 'center', maxWidth: 560, width: 'max-content',
      boxShadow: `0 0 0 ${10 + 6 * Math.sin(f / 9)}px ${C.accent}22`}}>{clip(scene.label || repo?.name || scene.emphasis || scene.heading, 24)}</div>}
  </div>;
};

// ---------------------------------------------------------------- Toggle list (steps, recap, lists)
export const ToggleList: React.FC<ObjProps & {items?: string[]; title?: string}> = p => {
  const {scene, f, dur} = p;
  const v = vd(scene);
  const items: string[] = (p.items ?? ((v.steps as string[] | undefined)?.length ? v.steps : (v.timeline as string[] | undefined)?.length ? v.timeline : scene.points)).slice(0, 5);
  const gap = Math.max(5, Math.min(12, (dur - 20) / Math.max(1, items.length)));
  return <Centre f={f}><Card>
    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline'}}>
      <span style={{fontFamily: F.sans, fontWeight: 800, fontSize: 48, lineHeight: 1.15, color: C.ink, paddingRight: 20}}>{clip(p.title ?? scene.heading, 34)}</span>
      <Meta>{items.length} items</Meta>
    </div>
    {items.map((it, i) => {
      const on = clamp01((f - 14 - i * gap) / 6);
      return <div key={i} style={{display: 'flex', alignItems: 'center', gap: 22, padding: '24px 0', borderTop: `2px solid ${C.line}`, marginTop: i ? 0 : 22,
        ...enterStyle(f, 4 + i * 4)}}>
        <span style={{fontFamily: F.mono, fontSize: 32, color: C.muted, width: 44}}>{i + 1}</span>
        <span style={{flex: 1, fontFamily: F.sans, fontSize: 44, lineHeight: 1.2, fontWeight: 600, color: on > .5 ? C.ink : C.inkSoft}}>{clip(it, 44)}</span>
        <Toggle on={on}/>
      </div>;
    })}
  </Card></Centre>;
};

// ---------------------------------------------------------------- README panel
export const ReadmePanel: React.FC<ObjProps> = p => {
  const {scene, f, dur, beat} = p;
  const repo = repoOf(p);
  const text = (repo?.readme || repo?.description || scene.narration).replace(/\s+/g, ' ');
  const lines = text.split(/(?<=[.!?])\s+/).filter(s => s.length > 8).slice(0, 8);
  const rowH = 132, travel = Math.max(0, lines.length * rowH - 380);
  const y = interpolate(f, [10, Math.max(30, dur)], [0, travel], cl);
  const key = (beat.focus || scene.emphasis || '').toLowerCase().split(/\s+/)[0];
  return <Centre f={f}><Card pad={0} style={{overflow: 'hidden', height: 620, position: 'relative'}}>
    <div style={{padding: '24px 34px', borderBottom: `2px solid ${C.line}`}}><Meta>{repo ? `${clip(repo.full_name, 28)} / README.md` : 'README.md'}</Meta></div>
    <div style={{position: 'absolute', left: 0, right: 0, top: 260, height: rowH, background: `${C.accent}14`, borderTop: `2px solid ${C.accent}55`, borderBottom: `2px solid ${C.accent}55`}}/>
    <div style={{transform: `translateY(${-y + 190}px)`, padding: '0 40px'}}>
      {lines.map((l, i) => <div key={i} style={{height: rowH, display: 'flex', alignItems: 'center', fontFamily: F.serif, fontStyle: 'italic', fontSize: 46, lineHeight: 1.15,
        color: key && l.toLowerCase().includes(key) ? C.ink : C.muted}}>{clip(l, 56)}</div>)}
    </div>
  </Card></Centre>;
};

// ---------------------------------------------------------------- Browser window
export const BrowserWindow: React.FC<ObjProps> = p => {
  const {scene, f, dur} = p;
  const rows = (scene.points.length ? scene.points : [scene.heading]).slice(0, 3);
  const url = clip(((vd(scene).url as string) || (scene.label ? `${scene.label.toLowerCase().replace(/\s+/g, '')}.app` : 'localhost:3000')), 26);
  const click = clamp01((f - Math.min(40, dur * .5)) / 6);
  return <Centre f={f}><Card pad={0} style={{overflow: 'hidden'}}>
    <div style={{display: 'flex', alignItems: 'center', gap: 12, padding: '20px 26px', borderBottom: `2px solid ${C.line}`}}>
      {[0, 1, 2].map(i => <span key={i} style={{width: 16, height: 16, borderRadius: 8, background: C.line}}/>)}
      <span style={{flex: 1, marginLeft: 12, padding: '10px 20px', borderRadius: 14, background: C.surfaceRaised, fontFamily: F.mono, fontSize: 32, color: C.muted}}>{url}</span>
    </div>
    <div style={{padding: '36px 40px 44px'}}>
      <div style={{fontFamily: F.sans, fontWeight: 800, fontSize: 64, color: C.ink, lineHeight: 1.05, letterSpacing: -1}}>{clip(scene.heading, 28)}</div>
      {rows.map((r, i) => <div key={i} style={{marginTop: 20, padding: '22px 26px', borderRadius: T.radius.row, fontFamily: F.sans, fontWeight: 600, fontSize: 42,
        background: i === 0 ? C.pill : C.surfaceRaised, color: i === 0 ? C.pillInk : C.ink, transform: `scale(${i === 0 ? 1 - .05 * Math.sin(click * Math.PI) : 1})`,
        ...enterStyle(f, 8 + i * 5)}}>{clip(r, 26)}</div>)}
    </div>
  </Card></Centre>;
};

// ---------------------------------------------------------------- Warning note
export const WarningNote: React.FC<ObjProps> = p => {
  const {scene, f} = p;
  return <Centre f={f}><Card style={{borderLeft: `8px solid ${C.warn}`}}>
    <Meta style={{color: C.warn, letterSpacing: 6}}>{clip((scene.label || 'Heads up').toUpperCase(), 20)}</Meta>
    <div style={{fontFamily: F.serif, fontStyle: 'italic', fontSize: 76, lineHeight: 1.05, color: C.ink, marginTop: 20}}>{clip(scene.heading, 40)}</div>
    {scene.points[0] && <div style={{fontFamily: F.sans, fontSize: 44, color: C.inkSoft, marginTop: 24, ...enterStyle(f, 12)}}>{clip(scene.points[0], 40)}</div>}
  </Card></Centre>;
};

// ---------------------------------------------------------------- Stat figure
export const StatFigure: React.FC<ObjProps> = p => {
  const {scene, beat, f} = p;
  const repo = repoOf(p);
  const raw = scene.stat || (repo ? String(repo.stars) : (beat.focus.match(/\$?\d[\d,.]*%?/)?.[0] ?? ''));
  const m = raw.match(/^(\D*)([\d,.]+)(.*)$/);
  const value = m ? Number(m[2].replace(/,/g, '')) : NaN;
  const shown = m && Number.isFinite(value) ? `${m[1]}${count(f, value).toLocaleString('en-US')}${m[3]}` : raw || beat.focus;
  return <Centre f={f}><div style={{textAlign: 'center'}}>
    <div style={{fontFamily: F.serif, fontStyle: 'italic', fontSize: shown.length > 7 ? 200 : 260, color: C.ink, lineHeight: 1}}>{shown}</div>
    <Meta style={{marginTop: 24, letterSpacing: 6}}>{clip((repo && !scene.stat ? 'github stars' : scene.heading).toUpperCase(), 30)}</Meta>
  </div></Centre>;
};

// ---------------------------------------------------------------- Pull quote
export const PullQuote: React.FC<ObjProps> = p => {
  const {beat, scene, f} = p;
  const text = clip(beat.text || scene.narration, 90);
  return <Centre f={f}><div style={{width: STAGE.width}}>
    <div style={{fontFamily: F.serif, fontSize: 140, lineHeight: .6, color: C.dim}}>“</div>
    <div style={{fontFamily: F.serif, fontStyle: 'italic', fontSize: text.length > 60 ? 64 : 76, lineHeight: 1.12, color: C.ink}}>{text}</div>
    <Meta style={{marginTop: 26}}>{clip(scene.label || scene.heading, 30)}</Meta>
  </div></Centre>;
};

// ---------------------------------------------------------------- Footage (Higgsfield / imported motion clip)
export const Footage: React.FC<ObjProps> = ({scene, dur}) => {
  if (!scene.media) return null;
  const rate = scene.mediaSeconds ? Math.max(.5, Math.min(1, scene.mediaSeconds / Math.max(.1, dur / 30))) : 1;
  return <div style={{position: 'absolute', left: -STAGE.left, top: -STAGE.top, width: W, height: H}}>
    <OffthreadVideo src={staticFile(scene.media)} muted playbackRate={rate} style={{width: '100%', height: '100%', objectFit: 'cover', filter: 'saturate(.75) contrast(1.05) brightness(.62)'}}/>
    <div style={{position: 'absolute', inset: 0, background: `linear-gradient(180deg, ${C.ground}f0 0%, ${C.ground}66 30%, ${C.ground}55 60%, ${C.ground}f2 92%)`}}/>
  </div>;
};

// ---------------------------------------------------------------- Hook (frame-0 bold statement)
export const PremiumHook: React.FC<ObjProps> = p => {
  const {scene, props, f} = p;
  const text = clip(scene.heading || props.title, 52);
  const words = text.split(' ');
  const keys = (scene.emphasis || '').toLowerCase().split(/\s+/);
  const size = text.length > 34 ? 104 : 118;
  const settle = clamp01((f + 10) / 16);       // already mostly settled on frame 0
  const items = props.scenes.filter(s => (s.item ?? 0) > 0);
  return <div style={{position: 'absolute', left: 0, right: 0, top: -160, height: STAGE.height + 160}}>
    {scene.media && <Footage {...p}/>}
    <Meta style={{letterSpacing: 6, color: C.muted, marginBottom: 30}}>{`${props.brand ?? 'FIELDNOTES'} / ${(props.series || 'PRODUCT NOTES').toUpperCase()}`}</Meta>
    <div style={{fontFamily: F.sans, fontWeight: 800, fontSize: size, lineHeight: 1.02, letterSpacing: -size * .03, color: C.ink,
      transform: `translateY(${(1 - settle) * 16}px)`}}>
      {words.map((w, i) => {
        const key = keys.includes(w.toLowerCase().replace(/[^\p{L}\p{N}']/gu, ''));
        return <span key={i} style={{display: 'inline-block', marginRight: size * .22}}>{key ? <Selected size={size * .92} p={settle}>{w}</Selected> : w}</span>;
      })}
    </div>
    {items.length > 1 && <div style={{display: 'flex', gap: 18, marginTop: 50}}>
      {items.map((s, i) => {
        const e = clamp01((f - 6 - i * 4) / 12);
        const name = props.repos?.[(s.item ?? 1) - 1]?.name ?? s.label ?? '';
        return <div key={i} style={{opacity: e, filter: `blur(${(1 - e) * 8}px)`, transform: `translateY(${(1 - e) * 24}px)`}}><Avatar name={name || `${i + 1}`} size={104}/></div>;
      })}
    </div>}
  </div>;
};

// ---------------------------------------------------------------- Signature CTA
export const SignatureCTA: React.FC<ObjProps> = p => {
  const {scene, props, f, dur} = p;
  const cta = (scene as any).cta as {keyword?: string; secondary?: string} | undefined;
  const items = props.scenes.filter(s => (s.item ?? 0) > 0).map(s => s.label || s.heading);
  const recapEnd = items.length ? Math.min(Math.max(26, items.length * 7 + 12), dur * .4) : 0;
  const out = clamp01((f - recapEnd) / 10);
  const k = clamp01((f - recapEnd - 2) / 14);
  const keyword = cta?.keyword ?? '';
  // Keyword and both quote marks stay on one line inside the 888 px safe width.
  const kSize = Math.min(220, 840 / (keyword.length * .68 + 1.2));
  return <div style={{position: 'absolute', inset: 0}}>
    {items.length > 0 && <div style={{position: 'absolute', inset: 0, opacity: 1 - out, filter: `blur(${out * 10}px)`}}>
      <ToggleList {...p} items={items} title="Recap" dur={recapEnd + 10}/></div>}
    <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', opacity: k, filter: `blur(${(1 - k) * 12}px)`,
      transform: `translateY(${(1 - k) * 24}px)`}}>
      {keyword ? <>
        <div style={{fontFamily: F.sans, fontWeight: 700, fontSize: 64, color: C.muted, letterSpacing: 2}}>Comment</div>
        <div style={{fontFamily: F.sans, fontWeight: 900, fontSize: kSize, color: C.ink, lineHeight: 1, letterSpacing: -6, marginTop: 6, whiteSpace: 'nowrap'}}>
          “<Selected size={kSize * .92} p={k}><span style={{fontFamily: F.sans, fontStyle: 'normal', fontWeight: 900}}>{keyword}</span></Selected>”</div>
        <div style={{fontFamily: F.serif, fontStyle: 'italic', fontSize: 56, color: C.inkSoft, marginTop: 30}}>{clip(cta?.secondary ?? scene.heading, 34)}</div>
      </> : <div style={{fontFamily: F.sans, fontWeight: 900, fontSize: 110, color: C.ink, lineHeight: 1, letterSpacing: -4}}>{clip(scene.heading, 30)}</div>}
    </div>
  </div>;
};
