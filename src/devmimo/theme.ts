import {Easing, interpolate, spring} from 'remotion';

/* DevMimo identity: charcoal, ivory, orange. Fonts are the bundled OFL files the premium renderer already loads (ensureFonts). */
export const DM = {
  charcoal: '#141416', charcoal2: '#1b1b1f', panel: '#222228', panelHi: '#2b2b33', line: '#34343d',
  ivory: '#f4efe4', ivoryShade: '#e3dccd', ivorySoft: '#cfc8ba', muted: '#8f897e', dim: '#5c5952',
  orange: '#ff7a1a', orangeHot: '#ff9a3d', orangeDeep: '#d9550a', orangeGlow: 'rgba(255,122,26,0.35)',
  error: '#ff5a47', ok: '#ffb066',
};
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
