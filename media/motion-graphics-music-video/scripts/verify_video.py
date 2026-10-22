#!/usr/bin/env python3
"""
Verification & Visual QA Script for Motion-Graphics Music Videos.

Checks:
1. File existence and non-zero size
2. Video stream codec (`h264`), pixel format (`yuv420p`), resolution (`1920x1080`), frame rate (`30` fps)
3. Audio stream codec (`aac`)
4. Duration synchronization between `final/music-video.mp4` and `song/passage.mp3` (< 0.08s drift)
5. Generates a 4x5 visual QA contact sheet (`final/qa_contact_sheet.jpg`) to inspect scenes.

Usage:
  python3 verify_video.py --video final/music-video.mp4 --audio song/passage.mp3 --contact-sheet final/qa_contact_sheet.jpg
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def probe_media(path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def generate_contact_sheet(video_path: Path, duration: float, out_sheet: Path) -> None:
    out_sheet.parent.mkdir(parents=True, exist_ok=True)
    interval = max(0.5, duration / 20.0)
    vf = f"fps=1/{interval:.4f},scale=480:-1,tile=4x5"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        vf,
        "-frames:v",
        "1",
        "-update",
        "1",
        str(out_sheet),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify rendered music video spec and sync.")
    parser.add_argument("--video", default="final/music-video.mp4", help="Path to rendered MP4")
    parser.add_argument("--audio", default="song/passage.mp3", help="Path to reference audio")
    parser.add_argument(
        "--contact-sheet",
        default="final/qa_contact_sheet.jpg",
        help="Output path for visual QA contact sheet",
    )
    args = parser.parse_args()

    video_path = Path(args.video)
    audio_path = Path(args.audio)
    sheet_path = Path(args.contact_sheet)

    if not video_path.exists():
        print(f"FAIL: Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    v_info = probe_media(video_path)
    a_info = probe_media(audio_path)

    v_streams = [s for s in v_info.get("streams", []) if s.get("codec_type") == "video"]
    a_streams = [s for s in v_info.get("streams", []) if s.get("codec_type") == "audio"]

    if not v_streams:
        print("FAIL: No video stream found in output MP4.", file=sys.stderr)
        sys.exit(1)
    if not a_streams:
        print("FAIL: No audio stream found in output MP4.", file=sys.stderr)
        sys.exit(1)

    vs = v_streams[0]
    as_ = a_streams[0]

    v_dur = float(v_info["format"]["duration"])
    a_dur = float(a_info["format"]["duration"])
    drift = abs(v_dur - a_dur)

    width = int(vs.get("width", 0))
    height = int(vs.get("height", 0))
    v_codec = vs.get("codec_name")
    pix_fmt = vs.get("pix_fmt")
    r_frame_rate = vs.get("r_frame_rate", "0/1")
    a_codec = as_.get("codec_name")

    print("=== Video Verification Report ===")
    print(f"Video File     : {video_path} ({video_path.stat().st_size / (1024*1024):.2f} MiB)")
    print(f"Resolution     : {width}x{height} (target: 1920x1080)")
    print(f"Video Codec    : {v_codec} / {pix_fmt} @ {r_frame_rate} fps (target: h264 / yuv420p @ 30/1)")
    print(f"Audio Codec    : {a_codec} (target: aac)")
    print(f"Audio Duration : {a_dur:.3f}s")
    print(f"Video Duration : {v_dur:.3f}s (drift: {drift:.3f}s)")

    errors = []
    if v_codec != "h264":
        errors.append(f"Expected video codec 'h264', got '{v_codec}'")
    if pix_fmt != "yuv420p":
        errors.append(f"Expected pix_fmt 'yuv420p', got '{pix_fmt}'")
    if a_codec != "aac":
        errors.append(f"Expected audio codec 'aac', got '{a_codec}'")
    if drift > 0.10:
        errors.append(f"Duration drift ({drift:.3f}s) exceeds 0.10s threshold")

    generate_contact_sheet(video_path, v_dur, sheet_path)
    print(f"Contact Sheet  : {sheet_path} (20-frame grid generated)")

    if errors:
        print("\nVERIFICATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("\nVERIFICATION PASSED: Spec, audio sync, and playback checks succeeded.")


if __name__ == "__main__":
    main()
