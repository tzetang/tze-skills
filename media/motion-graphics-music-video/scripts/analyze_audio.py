#!/usr/bin/env python3
"""
Audio Analysis Pipeline for Code-Driven Motion Graphics (Devarf Workflow).

Extracts beats, bars, drum hits (percussive onsets), pitch/note contours,
loud/quiet sections, and 30fps frequency-band energy envelopes from an audio file.

Usage:
  uv run --with librosa --with numpy --with scipy python3 analyze_audio.py \
    --audio song/passage.mp3 --out-dir song --fps 30
"""

import argparse
import json
import math
import os
from pathlib import Path

import librosa
import numpy as np


def normalize_array(arr: np.ndarray) -> np.ndarray:
    if len(arr) == 0:
        return arr
    p99 = float(np.percentile(arr, 99)) if np.max(arr) > 0 else 1.0
    if p99 <= 1e-8:
        return np.zeros_like(arr)
    return np.clip(arr / p99, 0.0, 1.0)


def hz_to_note_name(hz: float) -> str:
    if hz <= 0 or math.isnan(hz):
        return "Rest"
    try:
        return str(librosa.hz_to_note(hz))
    except Exception:
        return "N/A"


def analyze_audio(audio_path: Path, out_dir: Path, fps: int = 30) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[1/5] Loading audio: {audio_path} ...")
    y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))
    total_frames = int(round(duration * fps))

    print("[2/5] Separating harmonic and percussive components ...")
    y_harm, y_perc = librosa.effects.hpss(y)

    print("[3/5] Tracking tempo, beats, bars, and percussive drum hits ...")
    tempo_val, beat_frames = librosa.beat.beat_track(y=y_perc, sr=sr)
    bpm = float(np.asarray(tempo_val).flat[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

    # Group beats into 4/4 bars
    bars = []
    for idx in range(0, len(beat_times), 4):
        bar_beats = beat_times[idx : idx + 4]
        bars.append(
            {
                "bar": (idx // 4) + 1,
                "start": round(bar_beats[0], 3),
                "end": round(
                    beat_times[idx + 4] if idx + 4 < len(beat_times) else duration, 3
                ),
                "beats": [round(b, 3) for b in bar_beats],
            }
        )

    # Percussive onset detection (drum hits)
    onset_env = librosa.onset.onset_strength(y=y_perc, sr=sr)
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env, sr=sr, backtrack=False
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    onset_strengths = normalize_array(onset_env[onset_frames]) if len(onset_frames) else []
    drum_hits = [
        {"time": round(float(t), 3), "strength": round(float(s), 3)}
        for t, s in zip(onset_times, onset_strengths)
        if float(s) >= 0.25
    ]

    print("[4/5] Computing pitch contours and loud/quiet sections ...")
    f0, voiced_flag, _ = librosa.pyin(
        y_harm,
        fmin=float(librosa.note_to_hz("C2")),
        fmax=float(librosa.note_to_hz("C6")),
        sr=sr,
    )
    times_f0 = librosa.times_like(f0, sr=sr)
    notes_list = []
    step = max(1, int(len(times_f0) / min(250, max(1, int(duration * 3)))))
    for i in range(0, len(times_f0), step):
        if voiced_flag[i] and not np.isnan(f0[i]):
            notes_list.append(
                {
                    "time": round(float(times_f0[i]), 3),
                    "hz": round(float(f0[i]), 1),
                    "note": hz_to_note_name(float(f0[i])),
                }
            )

    # Compute 30fps multi-band envelopes (bass, drums, voice, other, rms)
    print(f"[5/5] Computing {fps}fps frame-locked frequency envelopes ...")
    hop_length = max(1, int(sr / fps))
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop_length))
    S_perc = np.abs(librosa.stft(y_perc, n_fft=2048, hop_length=hop_length))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)

    bass_mask = (freqs >= 20) & (freqs < 250)
    voice_mask = (freqs >= 250) & (freqs < 4000)
    other_mask = freqs >= 4000

    raw_bass = np.mean(S[bass_mask, :], axis=0) if np.any(bass_mask) else np.zeros(S.shape[1])
    raw_drums = np.mean(S_perc, axis=0)
    raw_voice = np.mean(S[voice_mask, :], axis=0) if np.any(voice_mask) else np.zeros(S.shape[1])
    raw_other = np.mean(S[other_mask, :], axis=0) if np.any(other_mask) else np.zeros(S.shape[1])
    raw_rms = librosa.feature.rms(S=S)[0]

    env_times = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=hop_length)
    target_times = np.arange(total_frames) / float(fps)

    bass_env = normalize_array(np.interp(target_times, env_times, raw_bass))
    drums_env = normalize_array(np.interp(target_times, env_times, raw_drums))
    voice_env = normalize_array(np.interp(target_times, env_times, raw_voice))
    other_env = normalize_array(np.interp(target_times, env_times, raw_other))
    rms_env = normalize_array(np.interp(target_times, env_times, raw_rms))

    # Loud & quiet dynamics segmentation (4-second windows)
    sections = []
    win_sec = 4.0
    win_frames = int(win_sec * fps)
    median_rms = float(np.median(rms_env)) if len(rms_env) else 0.5
    for start_f in range(0, total_frames, win_frames):
        end_f = min(total_frames, start_f + win_frames)
        seg_rms = float(np.mean(rms_env[start_f:end_f]))
        level = "loud" if seg_rms >= median_rms * 1.1 else ("quiet" if seg_rms <= median_rms * 0.85 else "medium")
        sections.append(
            {
                "start": round(start_f / fps, 3),
                "end": round(end_f / fps, 3),
                "mean_energy": round(seg_rms, 3),
                "dynamics": level,
            }
        )

    # Write report.json
    report_data = {
        "audio_file": audio_path.name,
        "duration_seconds": round(duration, 3),
        "fps": fps,
        "total_frames": total_frames,
        "sample_rate": sr,
        "bpm": round(bpm, 2),
        "total_beats": len(beat_times),
        "total_bars": len(bars),
        "total_drum_hits": len(drum_hits),
        "dynamics_sections": sections,
    }
    (out_dir / "report.json").write_text(json.dumps(report_data, indent=2))

    # Write song-map.json
    song_map = {
        "duration_seconds": round(duration, 3),
        "bpm": round(bpm, 2),
        "beats": [round(b, 3) for b in beat_times],
        "bars": bars,
        "drum_hits": drum_hits,
        "notes": notes_list,
        "sections": sections,
    }
    (out_dir / "song-map.json").write_text(json.dumps(song_map, indent=2))

    # Write envelopes.json
    frames_payload = [
        {
            "frame": i,
            "time": round(i / fps, 4),
            "rms": round(float(rms_env[i]), 4),
            "bass": round(float(bass_env[i]), 4),
            "drums": round(float(drums_env[i]), 4),
            "voice": round(float(voice_env[i]), 4),
            "other": round(float(other_env[i]), 4),
        }
        for i in range(total_frames)
    ]
    (out_dir / "envelopes.json").write_text(
        json.dumps({"fps": fps, "total_frames": total_frames, "frames": frames_payload}, indent=2)
    )

    # Write song-map.md
    md_lines = [
        f"# Song Map (`{audio_path.name}`)",
        "",
        f"- **Duration**: `{duration:.3f}` seconds (`{total_frames}` frames at `{fps}` fps)",
        f"- **Estimated Tempo**: `{bpm:.2f}` BPM",
        f"- **Total Bars (4/4)**: `{len(bars)}`",
        f"- **Total Beats**: `{len(beat_times)}`",
        f"- **Strong Drum Hits**: `{len(drum_hits)}`",
        "",
        "## Loud & Quiet Dynamics Map",
        "",
        "| Start (s) | End (s) | Dynamics | Mean Energy (0-1) |",
        "| :--- | :--- | :--- | :--- |",
    ]
    for s in sections:
        md_lines.append(
            f"| {s['start']:.2f} | {s['end']:.2f} | **{s['dynamics']}** | {s['mean_energy']:.3f} |"
        )
    md_lines.extend(["", "## Bar & Beat Map (First 32 Bars)", "", "| Bar | Start (s) | End (s) | Beat Timestamps (s) |", "| :--- | :--- | :--- | :--- |"])
    for b in bars[:32]:
        beats_str = ", ".join(f"{x:.2f}" for x in b["beats"])
        md_lines.append(f"| {b['bar']} | {b['start']:.2f} | {b['end']:.2f} | {beats_str} |")
    (out_dir / "song-map.md").write_text("\n".join(md_lines) + "\n")

    # Write song/README.md if not present
    readme_path = out_dir / "README.md"
    if not readme_path.exists():
        readme_path.write_text(
            f"""# Song Data Directory

This folder contains the source audio (`{audio_path.name}`, {duration:.3f}s) and pre-computed musical measurements:

- `passage.mp3`: Source audio file ({duration:.3f} seconds). Keep audio unchanged in the final video.
- `song-story.md`: Narrative meaning, visual themes, and story arc of the song.
- `lyrics-passage.md`: Timestamped lyrics for kinetic typography and lip/character sync.
- `song-map.md`: Human-readable overview of tempo ({bpm:.1f} BPM), loud/quiet sections, and bar/beat timings.
- `song-map.json`: Exact timestamps for `beats`, `bars`, `drum_hits`, `notes`, and `sections`.
- `envelopes.json`: Frame-by-frame ({fps} fps, {total_frames} frames) normalized energy values (`0.0` to `1.0`) for `rms`, `bass`, `drums`, `voice`, and `other`.
- `report.json`: Global summary statistics of the audio analysis.
"""
        )

    for stub, title in [
        ("song-story.md", "# Song Story & Visual Concept\n\nDescribe the narrative arc, themes, and visual metaphors here.\n"),
        ("lyrics-passage.md", "# Timestamped Lyrics\n\nAdd `[mm:ss.xx] Lyric line` entries here.\n"),
    ]:
        p = out_dir / stub
        if not p.exists():
            p.write_text(title)

    print(f"Done! Generated report.json, song-map.json, song-map.md, envelopes.json, and README.md in {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze audio for motion-graphics music video generation.")
    parser.add_argument("--audio", required=True, help="Path to input audio file (e.g., song/passage.mp3)")
    parser.add_argument("--out-dir", default="song", help="Output directory for song analysis files")
    parser.add_argument("--fps", type=int, default=30, help="Frame rate for envelope extraction (default: 30)")
    args = parser.parse_args()
    analyze_audio(Path(args.audio), Path(args.out_dir), args.fps)
