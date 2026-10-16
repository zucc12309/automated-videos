import tokens from '../../brand/tokens.json';
import {Easing, interpolate, spring} from 'remotion';

/* Colours come from the FIELDNOTES premium tokens (brand/tokens.json), the same file the premium renderer and QA read.
   The names below are roles: `charcoal` = ground, `ivory` = ink, `orange` = the brand accent. */
const C = tokens.color;
export const DM = {
  charcoal: C.ground, charcoal2: C.groundLift, panel: C.surface, panelHi: C.surfaceRaised, line: C.line,
  ivory: C.ink, ivoryShade: '#dcdcd6', ivorySoft: C.inkSoft, muted: C.muted, dim: C.dim,
  orange: C.accent, orangeHot: '#b3c0ff', orangeDeep: '#5d70d6', orangeGlow: 'rgba(142,162,255,0.35)',
  error: C.danger, ok: C.success,
};
/** Accent as rgba with the given alpha (for glows and tints). */
export const accentA = (a: number) => `rgba(142,162,255,${a})`;
export const FONT = {sans: "Figtree, 'Helvetica Neue', sans-serif", serif: "'Instrument Serif', Georgia, serif", mono: "'JetBrains Mono', Menlo, monospace"};
export const FPS = 30;

export type Word = {w: string; s: number; e: number};
export type DMScene = {id: string; kind: string; from: number; frames: number; lead_s: number; speech_s: number; words: Word[]; text: Record<string, any>};
export type IntroProps = {fps: number; durationInFrames: number; scenes: DMScene[]; mouth: number[]; handle?: string | null};

export const EASE = Easing.bezier(.2, .8, .2, 1);
export const EASE_IN = Easing.bezier(.6, 0, .9, .4);
/** Clamped interpolation (unclamped eased interpolations made words vanish in V2.2; never again). */
export const io = (f: number, a: number, b: number, from = 0, to = 1, easing = EASE) =>
  interpolate(f, [a, b], [from, to], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing});
export const sp = (f: number, delay = 0, damping = 12, stiffness = 140, mass = .6) =>
  spring({frame: f - delay, fps: FPS, config: {damping, stiffness, mass}});
/** Frame (scene-local) at which word i starts. */
export const wf = (scene: DMScene, i: number) => Math.round((scene.words[i]?.s ?? 0) * FPS);
export const rand = (i: number) => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
