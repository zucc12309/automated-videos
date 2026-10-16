import cfg from '../../series/mimo-found-this-on-github/series.json';
import {Easing, interpolate, spring} from 'remotion';

/* Series look. Colours come from the series config (series/<slug>/series.json, the cover identity in the series brief); the mascot
   keeps its own identity.json colours. Shared components take everything episode-specific through props, never from here. */

export const S = cfg.palette;
export const accentA = (a: number) => {
  const h = S.accent.replace('#', '');
  return `rgba(${parseInt(h.slice(0, 2), 16)},${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4, 6), 16)},${a})`;
};
export const inkA = (a: number) => `rgba(245,240,232,${a})`;
export const FONT = {sans: "Figtree, 'Helvetica Neue', sans-serif", serif: "'Instrument Serif', Georgia, serif", mono: "'JetBrains Mono', Menlo, monospace"};
export const FPS = 30;
export const W = 1080, H = 1920;
export const SAFE = cfg.safe_zone;

export type Word = {w: string; s: number; e: number};
export type SubWord = {w: string; em: boolean};
export type SubGroup = {s: number; e: number; words: SubWord[]; y?: number};
export type Scene = {id: string; kind: string; from: number; frames: number; lead_s: number; speech_s: number; words: Word[]; narration?: string};

export type HandKey = {t: number; x: number; y: number; pinch?: number; open?: number};
/** A demonstration panel. Every panel kind is drawn from data; `label` names what it shows. */
export type Panel =
  | {kind: 'hand'; path: HandKey[]; label?: string; mirror?: boolean}
  | {kind: 'cursor'; path: HandKey[]; label?: string; clicks?: number[]; windows?: string[]}
  | {kind: 'terminal'; lines: {text: string; at: number; tone?: 'cmd' | 'out' | 'ok' | 'dim'}[]; label?: string; title?: string; size?: number}
  | {kind: 'code'; lines: string[]; highlight?: number[]; label?: string; title?: string}
  | {kind: 'image'; src: string; label?: string; pan?: [number, number]; position?: string}
  | {kind: 'video'; src: string; label?: string; startFrom?: number};
export type Label = {text: string; feature: string; at?: number};
export type FlowNode = {label: string; sub?: string};
export type RepoCard = {owner: string; name: string; description: string; language?: string; license?: string};

export type SeriesInfo = {header: string; tagline: string; footer: string; handle: string; collection: string};
export type EpisodeInfo = {n: number; label: string; title: string; repo: string; category: string; headline: string[]; expression: string;
  visual: string; demoStatus: string; demoTag?: string | null; hookHeadline?: string[]; visualAssets?: {input?: string; output?: string; frames?: string[]}; coverMinimal?: boolean};

export type EpisodeProps = {
  fps: number; durationInFrames: number; series: SeriesInfo; episode: EpisodeInfo; scenes: Scene[]; subtitles: SubGroup[]; mouth: number[];
  hook: {panels: Panel[]; labels: Label[]}; demo: {left: Panel; right: Panel; labels: Label[]; input?: {label: string; text: string; note?: string}; output?: Panel}; flow: FlowNode[]; repoCard: RepoCard;
  payoff: {panel: Panel; question: string; replayFrom?: number}; outroFrames: number; showSubtitles?: boolean;
};
export type CoverProps = {series: SeriesInfo; episode: EpisodeInfo; mask?: boolean};

export const EASE = Easing.bezier(.2, .8, .2, 1);
export const io = (f: number, a: number, b: number, from = 0, to = 1, easing = EASE) =>
  interpolate(f, [a, b], [from, to], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing});
export const sp = (f: number, delay = 0, damping = 14, stiffness = 150, mass = .6) =>
  spring({frame: f - delay, fps: FPS, config: {damping, stiffness, mass}});
/** Frame (scene-local) at which word i starts; negative i counts from the end. */
export const wf = (scene: Scene, i: number) => {
  const w = scene.words[i < 0 ? scene.words.length + i : i];
  return Math.round((w?.s ?? 0) * FPS);
};
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

/** Interpolate a keyed path ({t: seconds}) at time t; returns x, y, pinch, open. */
export const samplePath = (path: HandKey[], t: number): Required<HandKey> => {
  if (!path.length) return {t, x: .5, y: .5, pinch: 0, open: 1};
  if (t <= path[0].t) return {open: 1, pinch: 0, ...path[0], t};
  for (let i = 1; i < path.length; i++) {
    const a = path[i - 1], b = path[i];
    if (t <= b.t) {
      const k = Easing.inOut(Easing.cubic)((t - a.t) / Math.max(1e-6, b.t - a.t));
      return {t, x: lerp(a.x, b.x, k), y: lerp(a.y, b.y, k), pinch: lerp(a.pinch ?? 0, b.pinch ?? 0, k), open: lerp(a.open ?? 1, b.open ?? 1, k)};
    }
  }
  const z = path[path.length - 1];
  return {open: 1, pinch: 0, ...z, t};
};

/** Deterministic width estimate (em units) for Figtree 900 uppercase; the cover QA checks the rendered result for overflow. */
const WIDE = 'MW', NARROW = 'IJ1', PUNCT = '.,:;!\'’', SPACE = ' ';
export const textEm = (s: string) => [...s].reduce((a, c) =>
  a + (WIDE.includes(c) ? .98 : NARROW.includes(c) ? .36 : PUNCT.includes(c) ? .3 : c === SPACE ? .26 : c === '?' ? .6 : .72), 0);
export const fitSize = (lines: string[], width: number, max: number) =>
  Math.floor(Math.min(max, ...lines.map(l => width / Math.max(1, textEm(l)))));
