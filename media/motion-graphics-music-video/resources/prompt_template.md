# Devarf Autonomous Music Video Prompt & Setup Template

Below is the exact prompt structure used in Devarf's *"I Had Opus 5.5 Make the Same Music Video at Every Effort"* experiment, ready to adapt for any song workspace.

## Canonical Prompt

```text
Make a music video for the song in this folder.

What I want: a full music video like a real official music video, with a lot of dance or some story, but made as motion graphics only. No filmed footage. It can be 2D, 3D or both. What matters to me is that it's creative and unique.

- The song is song/passage.mp3. Use all of it (<DURATION> seconds), with its audio unchanged.
- Read song/README.md first. The folder has what the whole song is about, the lyrics, and measurements of the music: beats, bars, notes, drum hits, loud and quiet parts.
- tools/README.md lists ready-made tools in this folder and what is installed on this PC. Using them is optional.
- Deliver one finished video: final/music-video.mp4, 1920x1080, 30 fps, H.264 yuv420p with AAC audio, the same length as the song file.
- Work on your own from start to finish. Don't stop to ask me for approval; deliver the finished video.
- Keep all your work inside this folder. Use only free tools already installed on this PC. Don't download footage or artwork. Fonts must be open-licensed (for example OFL), with the licence file kept.
- You can't hear the audio. Don't say you listened to or watched something you didn't.
- Before you finish, check that the file plays to the end and that the music is in sync with the song file.
- Then write report.md: what you made and the idea behind it, how you made it, what you checked, and what you're unsure about.
```

## Workspace `tools/README.md` Template

When setting up a run directory, include `tools/README.md` so the agent knows what rendering pipelines are available on the machine:

```markdown
# Tools & Rendering Pipeline

You can use any of the following approaches to generate `final/music-video.mp4` (`1920x1080`, `30 fps`, `H.264 yuv420p`, `AAC`):

1. **Web Engine (`three.js` 3D, `Canvas 2D`, `SVG`, `anime.js`)**:
   - Write an HTML/JS scene in `src/index.html` that exposes `window.seekToFrame(frameIndex, timeSeconds)`.
   - Render deterministically via headless Chrome + FFmpeg using:
     `node .agents/skills/motion-graphics-music-video/scripts/render_web_video.mjs --html src/index.html --audio song/passage.mp3 --out final/music-video.mp4`
2. **Installed Local Binaries**:
   - `node` / `npm` / `npx`
   - `python3` / `uv`
   - `ffmpeg` / `ffprobe`
   - `Google Chrome` (headless WebGL & Canvas 2D support)
```
