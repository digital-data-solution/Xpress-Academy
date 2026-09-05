# Xpress Academy — lecture video pipeline

Standalone Remotion project. Deliberately not entangled with the Django
app — it consumes JSON, nothing else. See `../ARCHITECTURE.md` for the
Django side.

## What's real vs. what's flagged

Built and **verified working end-to-end in this environment**:
the data pipeline (Django → JSON → cached audio → measured duration →
rendered MP4), the TTS provider interface + cache + ElevenLabs cost
guard, track-driven theming, and all seven scene components. A real
render was smoke-tested with placeholder audio (this sandbox has no
`espeak-ng`, so real Kokoro output couldn't be generated here) and
produced a correct, playable MP4 with per-scene durations exactly
matching the measured audio lengths.

**Not done / explicitly deferred** — don't assume these exist:
- Real Kokoro/ElevenLabs audio was never generated or listened to here.
  Do the "generate one line and listen to it" step below before
  trusting this on anything real.
- Word-level caption sync (whisper.cpp) — `bulletReveal`/`workedExample`
  currently reveal on an even time spread, not on the word that
  introduces each point. See the comment in `src/scenes/BulletReveal.tsx`.
- Real whiteboard stroke-drawing animation (potrace + stroke-dashoffset)
  — `WhiteboardDiagram.tsx` currently does a plain wipe-reveal as a
  placeholder. See that file's comment.
- JAMB/Manim adapter — no JAMB models exist in the Django app yet;
  out of scope until they do.
- Writing the rendered video's URL back onto the `Lesson` record. This
  repo's real media convention is Django-managed storage (S3 in prod,
  local in dev — see `apps/certificates`), **not Cloudinary** — Prompt
  1's "upload to Cloudinary" doesn't match how this app actually stores
  files. `Lesson.video_provider`/`video_id` are built for
  externally-hosted streaming (Bunny/Cloudinary), so wiring a
  locally-rendered file back in is a real product decision (a new
  `VideoProvider` choice? a new field? how the player embeds it?) that
  touches the live lesson-playback view — deliberately left for Sam to
  decide rather than guessed at here.

## Authoring a lesson's video script

Lecture videos are NOT generated from `Lesson.body` (the CKEditor
prose). They come from `Lesson.video_scenes`
(`apps.catalog.models.VideoScene`) — an explicit, ordered scene script
you write per lesson, editable as an inline on the Lesson's Django
admin page. Each scene has a `scene_type` (titleCard, bulletReveal,
whiteboardDiagram, fullImage, workedExample, evidenceCard, outroCard),
the narration text, an optional image, and a `payload` JSON blob for
whatever that scene type needs (bullets, evidence grade + citation,
captions — see each scene component in `src/scenes/`).

A lesson with no `VideoScene` rows has no video script yet — exporting
it refuses rather than fabricate one from `body`.

## One-time setup

```bash
npm install

# Kokoro (default, local, free — the ONLY provider that runs during
# iteration; ElevenLabs never runs unless you explicitly pass --voice=elevenlabs)
pip install kokoro soundfile numpy
# Kokoro shells out to espeak-ng for phonemization:
#   Windows:       winget install eSpeak-NG.eSpeak-NG
#   macOS:         brew install espeak-ng
#   Debian/Ubuntu: apt-get install espeak-ng

# Generate one line and LISTEN to it before building anything on top —
# per the build doc's own advice, and because this pipeline was never
# actually verified against real Kokoro output in the environment it
# was built in:
echo "Hello, this is a test." | python scripts/kokoro_tts.py /tmp/test.wav
```

Copy `.env.example` to `.env` if you'll use ElevenLabs (`ELEVENLABS_API_KEY`,
`ELEVENLABS_VOICE_ID`) — leave it unset and everything still works with Kokoro.

## Exporting a lesson from Django

```bash
# from the Django repo root, against whichever DB that shell is pointed at
python manage.py export_lesson_video_json <lesson_id> --out=../video/samples/<slug>.json
```

## Rendering

```bash
# Preview in Remotion Studio (opens with the bundled sample lesson)
npm run studio

# Render the bundled sample with Kokoro (safe, free, default)
npm run render:sample

# Render a real exported lesson
node scripts/render-lesson.mjs --props=samples/<slug>.json --voice=kokoro

# Final render with your cloned voice, once ELEVENLABS_VOICE_ID is set —
# this is the ONLY thing that spends a real credit, and it prints the
# character count + estimated cost and asks for typed confirmation first
node scripts/render-lesson.mjs --props=samples/<slug>.json --voice=elevenlabs

# The 30s vertical teaser (WhatsApp status / Reels)
node scripts/render-lesson.mjs --props=samples/<slug>.json --composition=LessonVideoTeaser
```

Output lands at `out/<track>/<lesson-slug>/<CompositionId>.mp4`, lowercased
by track (`vet`, `breeder`, `general`) per Prompt 1's folder convention.

## How timing actually works (read this before touching Composition.tsx)

`calculateMetadata` in `src/Composition.tsx` runs inside Remotion's
headless-Chromium context — **not** a plain Node process. That means it
can use `getAudioDurationInSeconds` (needs a real browser audio
decoder) but it can **never** touch `fs`, `crypto`, or spawn a
subprocess — confirmed the hard way while building this (webpack has no
Node polyfills, and `getAudioDurationInSeconds` throws
`"only available in the browser"` if you try it from plain Node).

So generating/caching audio (Kokoro subprocess, ElevenLabs fetch, the
sha256 cache key) happens in `scripts/render-lesson.mjs` — a real Node
process that runs **before** bundling — which writes files under
`public/audio/` and stamps `audioRelPath` onto each scene. Only then
does `calculateMetadata` turn that into a URL via `staticFile()` and
measure it. If you see `"has no audioRelPath"` at render time, you
opened `Root.tsx` some way that skipped `render-lesson.mjs`'s prep step.

## Project layout

```
src/types.ts          the input contract — mirrors apps.catalog.models.VideoScene
src/theme.ts           track -> tone/colors (BREEDER plain/warm, VET clinical/evidence-graded)
src/tts/               provider interface + disk cache + ElevenLabs cost guard
src/scenes/            one component per scene type
src/Composition.tsx    calculateMetadata + the actual <Series> layout
src/Root.tsx           registers both compositions with a real sample as defaultProps
scripts/render-lesson.mjs   the real render entry point (see above)
scripts/kokoro_tts.py  Python sidecar render-lesson.mjs spawns for Kokoro
samples/               example lesson JSON (also Root.tsx's defaultProps)
```
