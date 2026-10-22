# Devarf Motion-Graphics Music Video Workflow Reference

This document details the architecture, visual choreography patterns, and benchmark lessons from Devarf's experiment (*"I Had Opus 5.5 Make the Same Music Video at Every Effort"*).

---

## 1. Why Pre-Computed Audio Telemetry Matters

Because code-generating models cannot listen to raw `.mp3` files directly, giving the agent only an audio file forces it to guess BPM and lyric timings. Devarf solved this by running an audio analysis tool prior to video generation and placing 7 structured files in `song/`:

| File | Purpose |
| :--- | :--- |
| `passage.mp3` | Unmodified audio clip to be muxed into the final MP4. |
| `README.md` | Entry-point overview of all files in `song/`. |
| `song-story.md` | Narrative summary, thematic conflict, and visual metaphors of the song. |
| `lyrics-passage.md` | Line-by-line and word-by-word timestamps for kinetic typography. |
| `song-map.md` | Human-readable summary of tempo, sections, bars, and beat timestamps. |
| `song-map.json` | Exact arrays for `beats`, `bars`, `drum_hits`, `notes`, and `sections`. |
| `envelopes.json` | 30fps array of `{ frame, time, rms, bass, drums, voice, other }` normalized `0.0–1.0`. |
| `report.json` | Global metrics (sample rate, duration, BPM, total bars/beats). |

---

## 2. Three Proven Visual Architectures

Across the 6 effort levels in Devarf's experiment, three distinct visual paradigms emerged:

### A. 2D Vector Storytelling & Kinetic Typography (*"Low Effort" Style*)
* **Tech Stack**: `Canvas 2D` + `SVG` path morphing.
* **Signature Visual Techniques**:
  * **Symbolic Framing**: Opening with a giant stylized eye whose pupil frames the protagonist silhouette.
  * **Split-Screen Mirror Duality**: Dividing the canvas down the center (warm amber/purple on the left vs. cool cyan/teal on the right) with mirrored characters dancing in opposition and an audio waveform running along the bottom border.
  * **Multi-Dancer Chorus Lines**: 5–7 flat vector characters in distinct color palettes performing synchronized arm/leg keyframes on every beat.
  * **Integrated Lyric Typography**: Bold sans-serif lyrics placed at the top/bottom third or inside scene props (e.g., film strips, crowns, chess pieces) with active words highlighted in accent colors.

### B. 3D Articulated Mannequins, Lighting & Shadow Play (*"Medium to Max" Style*)
* **Tech Stack**: `three.js` (`WebGLRenderer` with shadows, bloom/post-processing, procedural textures, and particle systems).
* **Signature Visual Techniques**:
  * **Articulated 3D Character Rig**: Hierarchical `THREE.Group` joints (`pelvis -> spine -> chest -> head / upperArm -> foreArm -> hand / thigh -> shin -> foot`) driven by inverse-kinematics or sinusoidal beat phase functions (`beatPhase = time * (bpm / 60) * Math.PI * 2`).
  * **Material Evolution**:
    * *Medium*: Matte/metallic two-tone humanoid with bold wall typography.
    * *High*: Reflective gold vs. glowing cyan/holographic double, geodesic shattered spheres, and film-reel overlays.
    * *xhigh*: Artist wooden/porcelain mannequin with giant 3D chess pieces, golden birdcage bars, and narrative shadow projections on the back wall.
    * *Max*: Kintsugi/cracked dark porcelain body with glowing golden seams, volumetric spotlights, brick-wall shadow choreography, and overhead mandala dance formations.

### C. Hybrid 2D Character on a 3D Stage (*"Max + Ultracode" Style*)
* **Tech Stack**: `Canvas 2D` / `SVG` high-detail character textures mapped onto planes inside a `three.js` 3D environment.
* **Signature Visual Techniques**:
  * **2D Illustrated Rig**: A stained-glass/harlequin Jack-of-Clubs character with articulated 2D limbs and expressive costume geometry.
  * **3D Architectural Stage**: Giant 3D playing cards arranged in arches, fans, and rotating corridors, backed by radial gold sunbeams, speaker stacks, and an all-seeing eye backdrop.

---

## 3.Choreography & Beat-Sync Formulas

To make motion graphics feel locked to the music rather than floaty:

1. **Snappy Beat Impact (Exponential Decay)**:
   Compute time since the most recent beat or drum hit (`dt = time - lastBeatTime`), and apply an impulse curve:
   ```javascript
   const beatImpulse = Math.exp(-dt * 12.0); // Sharp 1.0 spike on beat, fast decay
   ```
   Use `beatImpulse` for camera FOV punches, background flashes (keep flash intensity comfortable), and floor ring expansions.

2. **Multi-Band Driven Articulation**:
   * `env.bass` -> Knee bend depth (`pelvis.position.y`), floor bounce, stage speaker cone excursion.
   * `env.drums` -> Shoulder shrugs, head nods, particle burst emission, rim light strobe.
   * `env.voice` -> Lyric scale/glow, character chest expansion or mouth/mask glow.
   * `env.other` -> High-frequency ambient dust/sparkle rotation and background geometric shimmer.

3. **Camera Choreography by Musical Section**:
   * **Intro / Quiet Sections**: Slow dolly-in or wide atmospheric establishing shot with strong silhouettes.
   * **Verse**: Medium tracking shot or split-mirror two-shot synced to lyric lines.
   * **Chorus / Loud Sections**: Dynamic orbit, low-angle hero framing, or overhead kaleidoscopic/mandala formation cuts on every bar (`barIndex % 2 === 0`).

---

## 4. Lessons from the "Ultracode Problem"

In Devarf's test, running `Max + Ultracode` spawned **42 agent sessions across 5 teams**:
* Output tokens jumped from **625k** (`Max`, **$48.78**) to **2.58M+** (`Max + Ultracode`, **$348.34+**).
* **$175.85** of that cost was purely **subagent cache writes** because each spawned subagent built its own isolated context cache instead of sharing the main session's cache.
* After delivering the video, 7 review agents triggered 9 scene agents to rewrite scenes, hitting the 5-hour usage limit twice and forcing unfinished agents to restart from scratch.

**Best Practice**:
* Keep the entire scene design and rendering pipeline in **one cohesive agent session** (or at most delegate isolated, read-only preparation tasks).
* Use a fast, low-resolution preview render (`960x540` or a 20-frame contact sheet via `verify_video.py`) for visual QA rather than spawning multi-agent review teams.
