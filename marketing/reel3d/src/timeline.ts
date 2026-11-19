// Everything time-based is derived from the voice-over word timings in timing.json,
// so a new voice take re-cuts the whole video automatically.
import T from './timing.json';

export const FPS = 30;
export const TIMING = T as {
  scratch: boolean;
  duration: number;
  words: {text: string; start: number; end: number; scene: string}[];
  scenes: {id: string; start: number}[];
};
export const END = TIMING.duration + 1.4;
export const TOTAL_FRAMES = Math.ceil(END * FPS);

export type SceneId = 'hook' | 'reveal' | 'demo' | 'focal' | 'optimise' | 'features' | 'cta';

export const sceneStart = (id: SceneId): number => TIMING.scenes.find((s) => s.id === id)!.start;
export const sceneEnd = (id: SceneId): number => {
  const i = TIMING.scenes.findIndex((s) => s.id === id);
  return i + 1 < TIMING.scenes.length ? TIMING.scenes[i + 1].start : END;
};

const clean = (s: string) => s.toLowerCase().replace(/[^a-z0-9']/g, '');

/** start time of the first word in `scene` that begins with `prefix` */
export const wordAt = (scene: SceneId, prefix: string): number => {
  const w =
    TIMING.words.find((x) => x.scene === scene && clean(x.text) === prefix) ??
    TIMING.words.find((x) => x.scene === scene && clean(x.text).startsWith(prefix));
  if (!w) throw new Error(`word ${prefix} not found in ${scene}`);
  return w.start;
};

// ------------------------------------------------------------- screens + colours
export type Rgb = [number, number, number];
export const SCREENS: Record<string, {img: string; col: Rgb; label: string}> = {
  ring: {img: 'scenes/ring.png', col: [60, 255, 150], label: 'GAMES'},
  sunset: {img: 'scenes/sunset.png', col: [255, 128, 48], label: 'MOVIES'},
  night: {img: 'scenes/night.png', col: [230, 90, 200], label: 'ANIME'},
  city: {img: 'scenes/city.png', col: [34, 204, 255], label: 'YOUTUBE'},
  fire: {img: 'scenes/fire.png', col: [255, 64, 40], label: 'GAMES'},
};

export const SCHEDULE: [number, string][] = [
  [0, 'ring'],
  [wordAt('demo', 'games'), 'fire'],
  [wordAt('demo', 'movies'), 'sunset'],
  [wordAt('demo', 'anime'), 'night'],
  [wordAt('demo', 'watches'), 'city'],
  [sceneStart('focal'), 'ring'],
  [sceneStart('optimise'), 'city'],
  [wordAt('features', 'openrgb'), 'sunset'],
  [wordAt('features', 'free'), 'night'],
  [wordAt('features', 'open'), 'fire'],
  [sceneStart('cta'), 'ring'],
];

export const screenAt = (t: number) => {
  let i = 0;
  for (let k = 0; k < SCHEDULE.length; k++) if (t >= SCHEDULE[k][0]) i = k;
  return {cur: SCHEDULE[i][1], prev: SCHEDULE[Math.max(0, i - 1)][1], since: t - SCHEDULE[i][0], index: i};
};

// ------------------------------------------------------------- colour maths
export const rgb2hsv = ([r, g, b]: Rgb): Rgb => {
  r /= 255; g /= 255; b /= 255;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
  let h = 0;
  if (d) {
    if (mx === r) h = ((g - b) / d) % 6;
    else if (mx === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h /= 6;
    if (h < 0) h += 1;
  }
  return [h, mx ? d / mx : 0, mx];
};
export const hsv2rgb = ([h, s, v]: Rgb): Rgb => {
  const i = Math.floor(h * 6), f = h * 6 - i;
  const p = v * (1 - s), q = v * (1 - f * s), t = v * (1 - (1 - f) * s);
  const [r, g, b] = [[v, t, p], [q, v, p], [p, v, t], [p, q, v], [t, p, v], [v, p, q]][((i % 6) + 6) % 6];
  return [r * 255, g * 255, b * 255];
};
export const mixHsv = (a: Rgb, b: Rgb, m: number): Rgb => {
  const A = rgb2hsv(a), B = rgb2hsv(b);
  if (A[1] < 0.15) A[0] = B[0];
  const dh = ((B[0] - A[0] + 1.5) % 1) - 0.5;
  return hsv2rgb([(A[0] + dh * m + 1) % 1, A[1] + (B[1] - A[1]) * m, A[2] + (B[2] - A[2]) * m]);
};
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const smooth = (x: number) => {
  const t = clamp01(x);
  return t * t * (3 - 2 * t);
};

export const WHITE_KEYS: Rgb = [225, 232, 245];

/** The single colour LumiSync would be sending at time t (lags the picture slightly, like real capture). */
export const colourAt = (t: number): Rgb => {
  const s = screenAt(t);
  const m = smooth((s.since - 0.06) / 0.28);
  return mixHsv(SCREENS[s.prev].col, SCREENS[s.cur].col, m);
};

/** Per-key colour; x is 0..1 across the keyboard. Handles the white hook and the rainbow wave reveal. */
export const keyColour = (t: number, x: number, row: number): {c: Rgb; i: number} => {
  const reveal = sceneStart('reveal');
  if (t < reveal) return {c: WHITE_KEYS, i: 0.6};
  const local = t - reveal;
  const front = local / 0.45; // wave crosses the keyboard in 0.45 s
  if (x > front) return {c: WHITE_KEYS, i: 0.6};
  const age = local - x * 0.45;
  const rainbow = hsv2rgb([(x * 0.9 + row * 0.04 + age * 1.2) % 1, 1, 1]);
  const settle = smooth((age - 0.35) / 0.6);
  const flash = 1.6 - 0.6 * smooth(age / 0.4);
  return {c: mixHsv(rainbow, colourAt(t), settle), i: flash};
};

export const hex = (c: Rgb) => '#' + c.map((v) => Math.round(v).toString(16).padStart(2, '0')).join('').toUpperCase();
export const css = (c: Rgb, a = 1) => `rgba(${c.map(Math.round).join(',')},${a})`;
export const lighten = (c: Rgb, k: number): Rgb => c.map((v) => v + (255 - v) * k) as Rgb;
