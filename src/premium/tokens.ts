import {loadFont} from '@remotion/fonts';
import {Easing, staticFile} from 'remotion';
import tokens from '../../brand/tokens.json';
import identity from '../../brand/character/identity.json';

/* fieldnotes-premium: the production design system, measured from the FIELDNOTES reference reel.
   All values come from brand/tokens.json so Remotion and the Python QA read the same numbers. */

export const T = tokens;
export const C = tokens.color;
export const F = tokens.font;
export const ID = identity;
export const W = 1080, H = 1920;
export const SAFE = {left: tokens.space.safeLeft, right: tokens.space.safeRight, top: tokens.space.safeTop, bottom: tokens.space.safeBottom};
export const GUTTER = tokens.space.gutter;
export const STAGE = {left: GUTTER, top: tokens.space.stageTop, width: W - GUTTER * 2, height: tokens.space.stageHeight};
export const HEADLINE_Y = tokens.caption.y;

const bez = (b: number[]) => Easing.bezier(b[0], b[1], b[2], b[3]);
export const EASE = {standard: bez(tokens.motion.easing.standard), enter: bez(tokens.motion.easing.enter), exit: bez(tokens.motion.easing.exit)};
export const DUR = tokens.motion.durations;
export const SPRING = tokens.motion.spring;

let loaded = false;
/** Bundled OFL fonts (public/fonts) so the render looks the same on every machine. */
export const ensureFonts = () => {
  if (loaded) return;
  loaded = true;
  for (const [family, files] of Object.entries(tokens.font.files)) {
    for (const entry of files as (string | number)[][]) {
      const [file, weight, style] = entry as [string, number, string | undefined];
      loadFont({family, url: staticFile(`fonts/${file}`), weight: String(weight), style: style ?? 'normal'}).catch(() => undefined);
    }
  }
};

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const clip = (text: string, max: number) => {
  if (!text || text.length <= max) return text ?? '';
  const cut = text.slice(0, max + 1).replace(/\s+\S*$/, '');
  return (cut || text.slice(0, max)).replace(/[\s,.;:—-]+$/, '') + '…';
};
/** Deterministic short id for decorative UI (never presented as data). */
export const shortId = (text: string) => { let h = 2166136261; for (const c of text) h = Math.imul(h ^ c.charCodeAt(0), 16777619); return (h >>> 0).toString(16).slice(0, 6); };
