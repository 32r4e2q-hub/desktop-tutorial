#!/usr/bin/env python3
"""Technical and sampled-frame QC for the source reels and exact 180-second cut.

Automated exposure/freeze checks are warnings, not substitutes for human review of every
full-resolution clip, especially hands, faces, printed matter, and temporal morphs.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FPS = 24
DURATION = 180.0


def probe(path: Path, count_frames: bool = False) -> dict:
    cmd = ["ffprobe", "-v", "error"]
    if count_frames:
        cmd += ["-count_frames"]
    cmd += ["-show_format", "-show_streams", "-of", "json", str(path)]
    return json.loads(subprocess.check_output(cmd, text=True))


def digest(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sampled_video(path: Path) -> dict:
    proc = subprocess.run([
        "ffmpeg", "-v", "error", "-i", str(path), "-vf",
        "fps=4,scale=160:90:flags=area,format=gray", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
    ], check=True, stdout=subprocess.PIPE)
    frame_bytes = 160 * 90
    count = len(proc.stdout) // frame_bytes
    if count < 2:
        raise RuntimeError(f"Could not sample enough frames from {path.name}")
    frames = np.frombuffer(proc.stdout[:count * frame_bytes], dtype=np.uint8).reshape(count, 90, 160)
    means = frames.mean(axis=(1, 2))
    black = (frames < 8).mean(axis=(1, 2))
    white = (frames > 250).mean(axis=(1, 2))
    white_hits = white > 0.99
    longest_white = run_length = 0
    for hit in white_hits:
        run_length = run_length + 1 if hit else 0
        longest_white = max(longest_white, run_length)
    diffs = np.abs(np.diff(frames.astype(np.int16), axis=0)).mean(axis=(1, 2))
    # Three seconds at 4 fps with almost no pixel change is suspicious; keep as warning only.
    freeze_windows = []
    width = 12
    if len(diffs) >= width:
        for start in range(len(diffs) - width + 1):
            if float(diffs[start:start + width].mean()) < 0.25:
                freeze_windows.append(round(start / 4, 2))
    return {
        "sample_fps": 4,
        "sampled_frames": int(count),
        "mean_luma_min": round(float(means.min()), 2),
        "mean_luma_max": round(float(means.max()), 2),
        "near_black_sample_seconds": [round(i / 4, 2) for i, value in enumerate(black) if value > 0.995],
        "near_white_sample_seconds": [round(i / 4, 2) for i, value in enumerate(white) if value > 0.99],
        "near_white_longest_run_frames": int(longest_white),
        "suspected_freeze_window_starts": freeze_windows[:20],
    }


def decode_check(path: Path) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], check=True)


def read_srt_cues(path: Path) -> list[tuple[float, float]]:
    import re
    if not path.is_file():
        return []
    blocks = path.read_text(encoding="utf-8").strip().split("\n\n")
    pattern = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+) --> (\d+):(\d+):(\d+)[,.](\d+)")
    cues = []
    for block in blocks:
        match = pattern.search(block)
        if not match:
            continue
        g = [int(value) for value in match.groups()]
        cues.append((g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000,
                     g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000))
    return cues


def speech_activity(film: Path):
    """10 ms RMS envelope of the delivered narration bed, so caption timing can be checked."""
    import av
    container = av.open(str(film))
    stream = container.streams.audio[0]
    rate = int(stream.codec_context.sample_rate)
    chunks = []
    for frame in container.decode(audio=0):
        data = frame.to_ndarray()
        chunks.append(data.mean(axis=0) if data.ndim > 1 else data)
    samples = np.concatenate(chunks).astype(np.float32)
    hop = max(1, rate // 100)
    count = len(samples) // hop
    rms = np.sqrt((samples[: count * hop].reshape(count, hop) ** 2).mean(axis=1))
    threshold = max(0.004, float(np.percentile(rms, 95)) * 0.10)
    active = rms > threshold

    def window(start_block: int, end_block: int) -> bool:
        lo, hi = max(0, start_block), min(len(active), end_block)
        return bool(hi > lo and active[lo:hi].mean() > 0.12)

    return window


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, default=ROOT / "work" / "gwangju_tape_case" / "sources")
    parser.add_argument("--film", type=Path, default=ROOT / "交付" / "光州胶带案_22米胶带_三分钟_带声音.mp4")
    parser.add_argument("--sources-only", action="store_true", help="decode and sample all sources without requiring a rendered film")
    args = parser.parse_args()
    results_path = HERE / "results.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    sources = args.sources
    film = args.film
    if not args.sources_only and not film.is_file():
        raise SystemExit(f"Final film is missing: {film}")
    hard_failures = []
    rows = []
    for shot in story["shots"]:
        sid = shot["id"]
        path = sources / f"{sid}.mp4"
        record = results.get("shots", {}).get(sid, {})
        if record.get("status") != "completed" or not path.is_file():
            hard_failures.append(f"{sid}: missing completed source")
            continue
        if record.get("sha256") != digest(path) or record.get("bytes") != path.stat().st_size:
            hard_failures.append(f"{sid}: source receipt checksum/size mismatch")
            continue
        source_meta = probe(path)
        video = next((s for s in source_meta["streams"] if s.get("codec_type") == "video"), None)
        if not video:
            hard_failures.append(f"{sid}: no video stream")
            continue
        sample = sampled_video(path)
        if sample["near_white_longest_run_frames"] >= 3:
            hard_failures.append(f"{sid}: near-total whiteout for at least 0.75s; manual review/replacement required")
        rows.append({"id": sid, "duration_seconds": round(float(source_meta["format"]["duration"]), 3),
                     "width": int(video["width"]), "height": int(video["height"]),
                     "fps": video.get("avg_frame_rate"), "decoded_ok": True, **sample})

    meta = None
    if not args.sources_only:
        decode_check(film)
        final = probe(film, count_frames=True)
        video = next((s for s in final["streams"] if s.get("codec_type") == "video"), None)
        audio = next((s for s in final["streams"] if s.get("codec_type") == "audio"), None)
        if not video:
            hard_failures.append("Final film has no video stream")
        else:
            meta = {
                "duration_seconds": round(float(final["format"]["duration"]), 3),
                "width": int(video["width"]), "height": int(video["height"]),
                "fps": video.get("avg_frame_rate"), "frames": int(video.get("nb_read_frames") or 0),
                "video_codec": video.get("codec_name"),
                "audio_codec": audio.get("codec_name") if audio else None,
                "audio_sample_rate": int(audio.get("sample_rate", 0)) if audio else None,
            }
            if abs(meta["duration_seconds"] - DURATION) > 0.04:
                hard_failures.append(f"Final duration is {meta['duration_seconds']}s, expected 180s")
            if (meta["width"], meta["height"], meta["fps"]) != (1920, 1080, "24/1"):
                hard_failures.append(f"Final video format mismatch: {meta['width']}x{meta['height']} at {meta['fps']}")
            if meta["frames"] != 180 * FPS:
                hard_failures.append(f"Final frame count is {meta['frames']}, expected {180 * FPS}")
            if not audio:
                hard_failures.append("Final film has no narration/audio stream")
            else:
                if int(audio.get("sample_rate", 0)) != 48_000:
                    hard_failures.append(f"Final audio sample rate is {audio.get('sample_rate')}, expected 48000 Hz")
                # A narration bus that stops early silently clips the closing line, so the
                # audio stream length must match the picture, not just the container header.
                audio_seconds = float(audio.get("duration") or 0.0)
                meta["audio_seconds"] = round(audio_seconds, 3)
                if abs(audio_seconds - DURATION) > 0.06:
                    hard_failures.append(
                        f"Final audio stream is {audio_seconds:.3f}s, expected {DURATION}s (narration clipped)")
                # Subtitle timing gate: one cue per shot, inside its own shot window and over real speech.
                cues = read_srt_cues(film.with_suffix(".srt"))
                meta["subtitle_cues"] = len(cues)
                if len(cues) != len(story["shots"]):
                    hard_failures.append(
                        f"Subtitle cue count is {len(cues)}, expected {len(story['shots'])}")
                shot_spans = [(float(s["start"]), float(s["start"]) + float(s["duration"]))
                              for s in story["shots"]]
                for index, ((cue_start, cue_end), (shot_start, shot_end)) in enumerate(
                        zip(cues, shot_spans), 1):
                    if cue_start < shot_start - 0.02 or cue_end > shot_end + 0.02:
                        hard_failures.append(
                            f"Subtitle cue {index} {cue_start:.2f}-{cue_end:.2f}s runs outside its shot "
                            f"{shot_start:.2f}-{shot_end:.2f}s")
                active = speech_activity(film)
                missed = [i for i, (a, b) in enumerate(cues, 1)
                          if not active(int(a * 100), int(min(b, DURATION) * 100) + 1)]
                meta["cues_without_speech"] = missed
                if missed:
                    hard_failures.append(f"Subtitle cues with no speech energy: {missed}")
        if not film.with_suffix(".srt").is_file():
            hard_failures.append("Subtitle sidecar is missing")

    report = {"status": "FAIL" if hard_failures else "TECHNICAL_PASS_VISUAL_REVIEW_PENDING",
              "scope": "sources_only" if args.sources_only else "sources_and_final", "final": meta,
              "source_shots": rows,
              "hard_failures": hard_failures,
              "limitations": ["Sampled grayscale freeze/exposure metrics do not detect anatomical distortions reliably.",
                              "Human full-playback signoff is required for faces, hands, scene continuity, and temporal artifacts."]}
    qa = HERE / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    (qa / "qc-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    title = "源片技术 QC" if args.sources_only else "成片技术 QC"
    summary = [f"# {title}", "", f"状态：**{report['status']}**", "", "## 成片规格", "",
               json.dumps(report.get("final"), ensure_ascii=False, indent=2), "", "## 源片抽样警告", ""]
    for row in rows:
        if row["near_black_sample_seconds"] or row["near_white_sample_seconds"] or row["suspected_freeze_window_starts"]:
            summary.append(f"- {row['id']}: black={row['near_black_sample_seconds']}, white={row['near_white_sample_seconds']}, freeze≈{row['suspected_freeze_window_starts']}")
    if not any(row["near_black_sample_seconds"] or row["near_white_sample_seconds"] or row["suspected_freeze_window_starts"] for row in rows):
        summary.append("未检出超过阈值的持续近黑/近白/近静止采样窗（不代表不存在面部或手部形变）。")
    if hard_failures:
        summary += ["", "## 必须修复", ""] + [f"- {item}" for item in hard_failures]
    summary += ["", "自动采样不能代替逐镜完整播放和人工畸变签核。"]
    (qa / "qc-summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(hard_failures) if hard_failures else "TECHNICAL QC PASS; human visual review remains required")
    return 1 if hard_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
