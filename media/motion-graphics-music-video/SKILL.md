---
name: motion-graphics-music-video
description: >-
  End-to-end workflow for generating code-driven 2D, 3D, or hybrid motion-graphics
  music videos synchronized to an audio track (based on Devarf's Claude Opus 5.5
  motion-graphics workflow). Use this skill whenever the user asks to generate a
  music video, audio visualizer, kinetic typography video, or synchronized
  motion-graphics animation from an audio file using code (Three.js, Canvas 2D,
  SVG, anime.js, and FFmpeg).
---

# Motion-Graphics Music Video Generator (Devarf Workflow)

This skill implements the code-driven motion-graphics music video pipeline popularized by Devarf (*"I Had Opus 5.5 Make the Same Music Video at Every Effort"*). Instead of diffusion models, it translates an audio file into structured musical/lyrical telemetry (`song/`) and renders deterministic, beat-synchronized 2D/3D frames (`tools/`) compiled via `FFmpeg` into `final/music-video.mp4`.

## Workspace Directory Structure

Every music video run operates inside a self-contained project folder with the following layout:

```text
<run-folder>/
├── song/
│   ├── passage.mp3          # Source audio clip (unmodified)
│   ├── README.md            # Overview of song metadata and file schemas
│   ├── song-story.md        # Thematic meaning, narrative arc, and visual concept
│   ├── lyrics-passage.md    # Timestamped lyrics (lines and/or words)
│   ├── song-map.md          # Human-readable bar/beat/section/note map
│   ├── song-map.json        # Machine-readable beats, bars, notes, drum hits, sections
│   ├── envelopes.json       # Frame-locked (30 fps) energy envelopes (bass, drums, voice, high, rms)
│   └── report.json          # Global audio metrics (duration, BPM, key, loudness profile)
├── tools/
│   ├── README.md            # Documentation of local rendering runners
│   └── web-engine/          # Headless Chrome deterministic frame renderer (Three.js / Canvas 2D / SVG)
├── src/                     # Generated scene code, shaders, characters, and choreography
├── final/
│   └── music-video.mp4      # Delivered video: 1920x1080, 30 fps, H.264 yuv420p, AAC audio
└── report.md                # Post-run report: concept, technical implementation, QA checks, and caveats
```

---

## Step-by-Step Workflow

### Phase 1: Audio Analysis & `song/` Preparation

Because the model cannot directly hear audio, **never guess beat timings**. If `song/song-map.json` and `song/envelopes.json` do not exist yet, generate them from the source audio file first.

1. **Run the Audio Analyzer**:
   Execute [analyze_audio.py](./scripts/analyze_audio.py) via `uv run` to extract exact duration, tempo, beats, bars, drum hits (percussive onsets), pitch/note contours, loud/quiet sections, and 30fps frequency-band envelopes (`bass`, `drums`, `voice`, `other`, `rms`):
   ```bash
   uv run --with librosa --with numpy --with scipy python3 .agents/skills/motion-graphics-music-video/scripts/analyze_audio.py \
     --audio song/passage.mp3 \
     --out-dir song
   ```
2. **Prepare Lyrics & Narrative (`lyrics-passage.md` & `song-story.md`)**:
   * If the user provided lyrics or timestamps, format them into `song/lyrics-passage.md`. If not provided and the track has vocals, offer to transcribe timestamps (e.g., via `mlx-whisper` or `openai-whisper` with `uvx`) or treat as instrumental.
   * Write `song/song-story.md` summarizing the emotional arc, visual metaphors, color palette, and section-by-section narrative progression based on the lyrics and loud/quiet energy map.
   * Caution: *If the song data is off, every downstream scene gets the same mistake.* Verify `song/report.json` duration matches `ffprobe` on `song/passage.mp3`.

### Phase 2: Choose Dimensionality & Visual Architecture

Read `song/README.md`, `song/song-story.md`, `song/lyrics-passage.md`, and `song/song-map.md`. Select one of the three proven visual architectures from [devarf_workflow_guide.md](./references/devarf_workflow_guide.md):

1. **2D Vector & Kinetic Typography (`Canvas 2D` + `SVG`)**:
   * Best for fast rendering, bold graphic storytelling, split-screen mirror motifs, flat rigged characters, and high-contrast lyric choreography.
2. **3D Motion Graphics (`three.js` + Custom Shaders/Lights)**:
   * Best for articulated 3D mannequins/characters, reflective/metallic or kintsugi materials, dynamic shadows on textured walls, volumetric lighting, particle shattering, and kaleidoscopic camera sweeps.
3. **Hybrid 2D-on-3D (`three.js` 3D Stage + `Canvas 2D`/`SVG` Character Textures)**:
   * Best for distinct artistic styles (e.g., a 2D stained-glass or illustrated character rigged onto planes inside a 3D architectural stage made of playing cards, speakers, and radial beams).

> [!WARNING]
> **Avoid the "Ultracode" Multi-Agent Trap**
> Do **not** split scene coding across dozens of independent subagents or run open-ended multi-agent review/fix loops. In Devarf's benchmark, spawning 42 agent sessions caused each agent to build isolated prompt caches and restart on rate limits, multiplying cost by **7×** ($348 vs. $48) without finishing. Keep scene orchestration in a single cohesive session with shared data and deterministic modular JS files.

### Phase 3: Implement Deterministic Frame-Driven Animation

1. Start from [web_scene_template.html](./resources/web_scene_template.html) or build a modular scene entry point in `src/index.html`.
2. **Never rely on real-time `requestAnimationFrame` wall-clock timing for final capture.** Expose a deterministic hook:
   ```javascript
   window.seekToFrame = async function(frameIndex, timeSeconds) {
     // Compute state strictly as a pure function of (frameIndex, timeSeconds, songMap, envelopes)
     // Render Three.js / Canvas 2D / SVG for this exact timestamp
   };
   ```
3. Drive visual motion directly from `song/envelopes.json` and `song/song-map.json`:
   * **Beat & Bar synchronization**: Trigger camera cuts, pose switches, and flashes on `songMap.beats` and `songMap.bars`.
   * **Continuous articulation**: Modulate limb angles, light intensity, bloom, and particle velocity using `envelopes.frames[frameIndex]` (`bass`, `drums`, `voice`, `other`, `rms`).
   * **Kinetic typography**: Display and animate lyrics from `lyrics-passage.md` in sync with vocal phrases, integrating text into the 2D/3D space (e.g., wall projections, split-mirror text, or stage backdrops).
   * **Licensing**: Use only locally installed free tools and open-licensed fonts (e.g., OFL, keeping the license file in the workspace). Do not download external stock footage or copyrighted artwork.

### Phase 4: Render & Compile (`final/music-video.mp4`)

Use [render_web_video.mjs](./scripts/render_web_video.mjs) to step through every frame (`0` to `Math.round(duration * 30) - 1`) in headless Chrome (`1920x1080`) and pipe directly into `FFmpeg` with `song/passage.mp3`:

```bash
# 1. Optional fast preview (e.g., 5 seconds at 960x540) to inspect visuals first:
node .agents/skills/motion-graphics-music-video/scripts/render_web_video.mjs \
  --html src/index.html \
  --audio song/passage.mp3 \
  --out final/preview.mp4 \
  --width 960 --height 540 --fps 30 --duration 5

# 2. Full production render (1920x1080, 30 fps, H.264 yuv420p, AAC):
node .agents/skills/motion-graphics-music-video/scripts/render_web_video.mjs \
  --html src/index.html \
  --audio song/passage.mp3 \
  --out final/music-video.mp4 \
  --width 1920 --height 1080 --fps 30
```

### Phase 5: Automated Verification & `report.md`

Before finishing, **always** verify the rendered video and write `report.md`:

1. **Run the Verification Script**:
   Execute [verify_video.py](./scripts/verify_video.py) to validate that `final/music-video.mp4` plays to the end, matches `song/passage.mp3` duration within `< 0.05s`, uses `h264` (`yuv420p`) at `1920x1080` @ `30 fps` with `aac` audio, and generates a tiled contact sheet (`final/qa_contact_sheet.jpg`) to visually inspect scenes:
   ```bash
   python3 .agents/skills/motion-graphics-music-video/scripts/verify_video.py \
     --video final/music-video.mp4 \
     --audio song/passage.mp3 \
     --contact-sheet final/qa_contact_sheet.jpg
   ```
2. **Inspect the Contact Sheet**:
   Use `read_file` on `final/qa_contact_sheet.jpg` to verify visual framing, lighting contrast, character visibility, and typography legibility across the entire timeline.
3. **Write `report.md`**:
   Document:
   * **Concept & Visual Direction**: The creative idea and how it maps to `song-story.md`.
   * **Technical Architecture**: How scenes, characters, shaders, and beat synchronization were implemented.
   * **Verification Summary**: What was checked (`ffprobe` metrics, sync accuracy, frame inspection).
   * **Known Limitations / Uncertainties**: Honest notes on any rough transitions or trade-offs (never claim to have "listened" to the audio directly).
