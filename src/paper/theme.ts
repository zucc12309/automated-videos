export const P = {
  paper: '#ebe8e1', card: '#fffdf8', ink: '#1c1a17', soft: '#8b857a', line: '#d9d3c7', red: '#d63a2a', redSoft: '#d63a2a22',
  sans: '"Avenir Next", "Helvetica Neue", Helvetica, sans-serif',
  serif: 'Baskerville, "Baskerville Old Face", Georgia, serif',
  mono: 'Menlo, "SF Mono", monospace',
};

// Frame offsets inside a scene; mirror the seconds in video_mcp/audio.py (CARD_AT, PLUG_AT, STAMP_AT, COUNT_*).
export const T = {card: 4, plug: 22, stamp: 30, countFrom: 10, countTo: 54, circle: 46};

export const hue = (text: string) => {
  let h = 0;
  for (const c of text) h = (h * 31 + c.charCodeAt(0)) % 360;
  return h;
};

export const formatStars = (n: number) => n >= 10000 ? `${(n / 1000).toFixed(1)}k` : n.toLocaleString('en-US');
