# tze-skills

Collection of reusable AI coding agent skills.

## Skills

### `media/`
* **[`motion-graphics-music-video`](./media/motion-graphics-music-video/SKILL.md)** — End-to-end workflow for generating code-driven 2D, 3D, or hybrid motion-graphics music videos synchronized to an audio track (based on Devarf's Claude Opus 5.5 motion-graphics workflow using `Three.js`, `Canvas 2D`, `SVG`, `librosa`, headless Chrome CDP, and `FFmpeg`).
  * [`SKILL.md`](./media/motion-graphics-music-video/SKILL.md) — Main skill instructions
  * [`scripts/analyze_audio.py`](./media/motion-graphics-music-video/scripts/analyze_audio.py) — Extracts beats, bars, drum hits, pitch contours, and 30fps multi-band envelopes (`rms`, `bass`, `drums`, `voice`, `other`)
  * [`scripts/render_web_video.mjs`](./media/motion-graphics-music-video/scripts/render_web_video.mjs) — Deterministic frame-by-frame headless Chrome + FFmpeg video renderer (`1920x1080`, `30 fps`, `H.264 yuv420p`, `AAC`)
  * [`scripts/verify_video.py`](./media/motion-graphics-music-video/scripts/verify_video.py) — Stream, codec, audio-sync verification, and 20-frame visual QA contact sheet generator
  * [`resources/`](./media/motion-graphics-music-video/resources/) — Starter `1920x1080` WebGL/Canvas/SVG template & autonomous prompt template
  * [`references/devarf_workflow_guide.md`](./media/motion-graphics-music-video/references/devarf_workflow_guide.md) — Deep-dive architecture & choreography reference
