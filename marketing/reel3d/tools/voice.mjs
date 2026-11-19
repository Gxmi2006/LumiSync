// Voice-over for the LumiSync reel, made with ElevenLabs.
//
//   node --env-file=.env.local tools/voice.mjs --list            list the account's premade voices
//   node --env-file=.env.local tools/voice.mjs --voice <id>      generate public/voice.mp3 + src/timing.json
//
// The key is read from ELEVENLABS_API_KEY (loaded from .env.local); it never appears in code.
import {ElevenLabsClient} from '@elevenlabs/elevenlabs-js';
import {writeFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');

// Approved script. Scene ids decide what the video shows during each line.
const SCRIPT = [
  ['hook', 'Your keyboard can show sixteen million colours, so why is it still glowing plain white?'],
  ['reveal', 'Watch this.'],
  ['demo', 'This is LumiSync. Games, movies, anime, it watches your screen and lights your keyboard to match.'],
  ['focal', "It finds the thing that's actually glowing, instead of averaging everything into mud."],
  ['optimise', "And it's seriously light. It shrinks your screen to just a hundred and sixty by ninety pixels before it does any maths, and it skips updates when nothing changes."],
  ['features', "It works with OpenRGB, and it's completely free and open source."],
  ['cta', "Link's in my bio. Go give it a star."],
];
const LEAD_IN = 0.3; // seconds of silence before the voice starts in the video

const client = new ElevenLabsClient();
const args = process.argv.slice(2);

if (args.includes('--list')) {
  const res = await client.voices.getAll();
  for (const v of res.voices.filter((v) => v.category === 'premade')) {
    const l = v.labels ?? {};
    console.log(`${v.voiceId}  ${v.name}  ${[l.gender, l.age, l.accent, l.descriptive ?? l.description, l.use_case ?? l.useCase].filter(Boolean).join(', ')}`);
  }
  process.exit(0);
}

const voiceId = args[args.indexOf('--voice') + 1];
if (!args.includes('--voice') || !voiceId) throw new Error('pass --voice <id> (see --list)');
const model = args.includes('--model') ? args[args.indexOf('--model') + 1] : 'eleven_v4';

const text = SCRIPT.map(([, line]) => line).join(' ');
const res = await client.textToSpeech.convertWithTimestamps(voiceId, {
  text,
  modelId: model,
  outputFormat: 'mp3_44100_128',
  voiceSettings: {stability: 0.4, similarityBoost: 0.8},
});
writeFileSync(join(ROOT, 'public', 'voice.mp3'), Buffer.from(res.audioBase64, 'base64'));

// characters -> words
const al = res.alignment;
const words = [];
let cur = '', start = 0, end = 0;
al.characters.forEach((c, i) => {
  if (/\s/.test(c)) {
    if (cur) words.push({text: cur, start: start + LEAD_IN, end: end + LEAD_IN});
    cur = '';
    return;
  }
  if (!cur) start = al.characterStartTimesSeconds[i];
  cur += c;
  end = al.characterEndTimesSeconds[i];
});
if (cur) words.push({text: cur, start: start + LEAD_IN, end: end + LEAD_IN});

let i = 0;
for (const [scene, line] of SCRIPT) for (const _ of line.split(/\s+/)) words[i++].scene = scene;
if (i !== words.length) throw new Error(`word count mismatch: script ${i}, audio ${words.length}`);

const scenes = SCRIPT.map(([id]) => ({id, start: words.find((w) => w.scene === id).start}));
const duration = words.at(-1).end + 0.3;
writeFileSync(join(ROOT, 'src', 'timing.json'), JSON.stringify({scratch: false, duration, words, scenes}, null, 1));
console.log(`voice ${voiceId} (${model}): ${duration.toFixed(2)} s, ${words.length} words`);
