import {Easing, interpolate, spring} from 'remotion';

// ---- Brand layer (never varies): type, safe zones, line weights ----
export const FONT = {
  sans: '"Avenir Next", "Helvetica Neue", Helvetica, sans-serif',
  serif: 'Baskerville, Georgia, serif',
  mono: 'Menlo, "SF Mono", monospace',
};

// Union of Reels/TikTok/Shorts UI safe zones at 1080x1920: text stays inside x 120-960, y 290-1248.
export const SAFE = {left: 120, right: 960, top: 290, bottom: 1248};
export const STAGE = {left: 120, top: 360, width: 840, height: 700};   // layout content area under the progress bar
export const CAPTION_Y = 1100;

// ---- Theme layer (seeded per video) ----
export type Palette = {bg: string; bg2: string; surface: string; ink: string; muted: string; line: string; accent: string; accent2: string; hl: string; dark: boolean};
export const PALETTES: Record<string, Palette> = {
  'paper-red': {bg: '#ebe8e1', bg2: '#e2ded4', surface: '#fffdf8', ink: '#1c1a17', muted: '#857f74', line: '#d9d3c7', accent: '#d63a2a', accent2: '#2d4bff', hl: '#ffd84d', dark: false},
  'midnight-lime': {bg: '#0e1012', bg2: '#16191d', surface: '#1b1f24', ink: '#f2f2ee', muted: '#8a9099', line: '#2c3138', accent: '#c6f432', accent2: '#7aa2ff', hl: '#c6f432', dark: true},
  'cream-cobalt': {bg: '#f4efe4', bg2: '#ebe4d4', surface: '#fffaf0', ink: '#14161c', muted: '#7d7a72', line: '#ddd5c4', accent: '#2d4bff', accent2: '#ff6b3d', hl: '#ffd84d', dark: false},
  'ink-orange': {bg: '#121212', bg2: '#1a1a1a', surface: '#1f1f1f', ink: '#f5f1ea', muted: '#8d8a84', line: '#2e2e2e', accent: '#ff7a1a', accent2: '#5ad1ff', hl: '#ff7a1a', dark: true},
  'mint-forest': {bg: '#e3f1e8', bg2: '#d5eadc', surface: '#ffffff', ink: '#10261c', muted: '#5d7466', line: '#c4dccd', accent: '#0f8a5f', accent2: '#ff5c7a', hl: '#b6f2cf', dark: false},
  'lilac-ink': {bg: '#ebe6fb', bg2: '#ded7f6', surface: '#ffffff', ink: '#1b1530', muted: '#6e6890', line: '#d3cbef', accent: '#6c3cff', accent2: '#ff8a00', hl: '#ffd84d', dark: false},
  'blueprint': {bg: '#10306b', bg2: '#0d2858', surface: '#173d84', ink: '#eaf2ff', muted: '#9fb6dd', line: '#2a5199', accent: '#ffd84d', accent2: '#7fe3ff', hl: '#ffd84d', dark: true},
  'sand-teal': {bg: '#efe3cf', bg2: '#e6d7bd', surface: '#fff8ec', ink: '#1f1a14', muted: '#8a7b66', line: '#dccbb0', accent: '#0a8f8f', accent2: '#e04f2f', hl: '#ffcf5a', dark: false},
};

export type Variant = {seed: string; palette: string; background: string; temperament: 'snappy' | 'smooth' | 'editorial'; captions: 'pill' | 'bold' | 'editorial';
  transitions: string[]; outfit: string; hair: string; camera: number};

export const DEFAULT_VARIANT: Variant = {seed: 'default', palette: 'paper-red', background: 'grain', temperament: 'snappy', captions: 'editorial', transitions: ['whip', 'zoom', 'cut'], outfit: '#2f3b52', hair: '#3b2a21', camera: 1};

// ---- Motion tokens (IBM Carbon curves; Remotion springs) ----
const EXPRESSIVE_IN = Easing.bezier(0, 0, .3, 1);
const PRODUCTIVE_IN = Easing.bezier(0, 0, .38, .9);

/** 0..1 entrance progress for an element appearing `delay` frames into a beat, shaped by the video's temperament. */
export const enter = (frame: number, delay: number, temperament: Variant['temperament'], fps = 30) => {
  const f = frame - delay;
  if (temperament === 'snappy') return spring({frame: f, fps, config: {damping: 13, stiffness: 170, mass: .9}});
  if (temperament === 'smooth') return interpolate(f, [0, 12], [0, 1], {easing: PRODUCTIVE_IN, extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return interpolate(f, [0, 18], [0, 1], {easing: EXPRESSIVE_IN, extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
};

export const STAGGER = {snappy: 3, smooth: 4, editorial: 5};

/** Keyword punch 1 -> 1.15 -> 1 across ~10 frames, starting `lead` frames before the hit. */
export const punch = (frame: number, hitFrame: number, amount = .15, lead = 4) => {
  const f = frame - (hitFrame - lead);
  if (f < 0 || f > 14) return 1;
  return 1 + amount * (f < 5 ? Easing.out(Easing.cubic)(f / 5) : 1 - Easing.inOut(Easing.cubic)((f - 5) / 9));
};

export const clampText = (text: string, max: number) => {
  if (text.length <= max) return text;
  const cut = text.slice(0, max + 1).replace(/\s+\S*$/, '');
  return (cut || text.slice(0, max)).replace(/[\s,.;:—-]+$/, '') + '…';
};

export const hueOf = (text: string) => { let h = 0; for (const c of text) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
