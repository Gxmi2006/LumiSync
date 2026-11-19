// Sound effects and music bed for the LumiSync reel, made with ElevenLabs.
//
//   node --env-file=.env.local tools/sfx.mjs            all effects + music
//   node --env-file=.env.local tools/sfx.mjs impact pop  only the named ones
//
// Writes public/sfx/el_<name>.mp3. The key is read from ELEVENLABS_API_KEY.
import {ElevenLabsClient} from '@elevenlabs/elevenlabs-js';
import {readFileSync, writeFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const client = new ElevenLabsClient();

const EFFECTS = {
  counter: ['Fast digital number counter rolling up, rapid soft electronic ticks accelerating, clean tech UI', 1.8, 0.7],
  scratch: ['Comedic vinyl record scratch, short and punchy', 0.8, 0.8],
  riser: ['Cinematic tension riser, airy synth swell building quickly to a peak, modern trailer', 1.6, 0.6],
  impact: ['Huge cinematic bass drop impact, deep sub boom with a bright shimmering tail, modern tech trailer', 2.5, 0.6],
  click: ['Soft tactile modern UI click, subtle and clean, single tap', 0.5, 0.8],
  whoosh: ['Fast clean airy swoosh transition, short, modern motion graphics', 0.7, 0.7],
  glitch: ['Retro digital pixelation glitch sweep, bit-crushed data scan, short', 1.2, 0.6],
  pop: ['Bubbly satisfying UI pop, playful and bright, single', 0.5, 0.8],
  sparkle: ['Magical bright sparkle chime with twinkling stars, uplifting', 1.6, 0.6],
  // music beds made with the sound-effects model (the Music API needs a paid plan)
  pad: ['Dark atmospheric synth pad drone with rising tension, cinematic, slow, no drums', 7, 0.5],
  beat: ['Energetic modern electronic music loop for a tech promo, punchy drums, deep bass, bright synth plucks, 112 BPM, catchy, instrumental', 15, 0.5, true],
};

const MUSIC_PROMPT =
  'Instrumental background music for a short tech product promo video. Starts with six seconds of dark, quiet, ' +
  'atmospheric synth pads with tension, then the beat drops into an energetic, modern electronic track with punchy ' +
  'drums, deep bass and bright synth plucks at 112 BPM, confident and catchy. No vocals.';

const toBuffer = async (audio) => {
  if (audio && typeof audio.pipe === 'function') {
    const chunks = [];
    for await (const c of audio) chunks.push(Buffer.from(c));
    return Buffer.concat(chunks);
  }
  return Buffer.from(await new Response(audio).arrayBuffer());
};

const wanted = process.argv.slice(2);
const pick = (name) => wanted.length === 0 || wanted.includes(name);

for (const [name, [text, duration, influence, loop = false]] of Object.entries(EFFECTS)) {
  if (!pick(name)) continue;
  const audio = await client.textToSoundEffects.convert({
    text,
    modelId: 'eleven_text_to_sound_v3',
    durationSeconds: duration,
    promptInfluence: influence,
    loop,
    outputFormat: 'mp3_44100_128',
  });
  writeFileSync(join(ROOT, 'public', 'sfx', `el_${name}.mp3`), await toBuffer(audio));
  console.log('sfx', name);
}

if (wanted.includes('music')) { // Music API: paid ElevenLabs plans only
  const timing = JSON.parse(readFileSync(join(ROOT, 'src', 'timing.json'), 'utf8'));
  const ms = Math.ceil((timing.duration + 2) * 1000);
  const audio = await client.music.compose({prompt: MUSIC_PROMPT, musicLengthMs: ms, forceInstrumental: true});
  writeFileSync(join(ROOT, 'public', 'sfx', 'el_music.mp3'), await toBuffer(audio));
  console.log('music', ms, 'ms');
}
