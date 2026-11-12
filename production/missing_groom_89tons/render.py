#!/usr/bin/env python3
"""Deterministic 180 s cut from verified Agnes sources and shot-locked Chinese narration."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FPS = 24
RATE = 48_000


def run(args: list[object], capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run([str(x) for x in args], check=True, text=capture, capture_output=capture)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def probe(path: Path) -> dict:
    result = run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", path], True)
    return json.loads(result.stdout)


def duration(path: Path) -> float:
    return float(probe(path)["format"]["duration"])


def srt_time(seconds: float) -> str:
    ms = max(0, round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def ffmpeg_escape(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def ass_time(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, centiseconds = divmod(centiseconds, 360000)
    minutes, centiseconds = divmod(centiseconds, 6000)
    secs, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def ass_escape(text: str) -> str:
    return text.replace("\\", "／").replace("{", "（").replace("}", "）").replace("\n", " ")


def caption_lines(text: str, limit: int = 24) -> list[str]:
    """Keep Chinese captions compact and centered, using a consistent small type size."""
    if len(text) <= limit:
        return [text]
    split_at = len(text) // 2
    punctuation = set("，。；：！？、")
    candidates = [i + 1 for i, char in enumerate(text) if char in punctuation and 6 <= i + 1 <= limit]
    if candidates:
        split_at = min(candidates, key=lambda i: abs(i - len(text) / 2))
    else:
        split_at = min(limit, split_at)
    left, right = text[:split_at].strip(), text[split_at:].strip()
    if len(right) > limit:
        return [left] + caption_lines(right, limit)
    return [left, right]


def ass_caption(text: str, phrases: list[str]) -> str:
    """Apply gold to selected phrases only; all text keeps the same font size and weight."""
    text = ass_escape(text)
    ordered = sorted(set(phrases), key=len, reverse=True)
    out = []
    i = 0
    while i < len(text):
        hit = next((phrase for phrase in ordered if text.startswith(phrase, i)), None)
        if hit:
            out.append(r"{\c&H0000C8FF&\fs42}" + hit + r"{\rCaption}")
            i += len(hit)
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def write_ass(path: Path, cues: list[tuple[float, float, str]], phrases: list[str],
              end_card: tuple[str, str, float, float] | None = None) -> None:
    rows = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Caption,Noto Sans CJK SC,36,&H00FFFFFF,&H00FFFFFF,&H00111110,&H99000000,0,0,0,0,100,100,0,0,1,2.0,0.5,2,140,140,54,1",
        "Style: Title,Noto Sans CJK SC,104,&H0000C8FF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,2,0,1,3.0,1.0,2,120,120,330,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for start, end, text in cues:
        rendered = r"\N".join(ass_caption(line, phrases) for line in caption_lines(text))
        rows.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{{\\q2\\fad(60,70)}}{rendered}")
    if end_card:
        title, subtitle, start, end = end_card
        card = (ass_escape(title) + r"\N" +
                r"{\fs38\c&H00FFFFFF&}" + ass_escape(subtitle))
        rows.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Title,,0,0,0,,{{\\q2\\fad(200,400)}}{card}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    results = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    manifest_path = HERE / "audio" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audio_rows = {row["id"]: row for row in manifest.get("clips", [])}
    if len(audio_rows) != len(story["shots"]):
        raise RuntimeError("Need exactly one verified narration clip for each of the 30 shots")
    if manifest.get("voice") != story["narration_spec"]["voice_id"]:
        raise RuntimeError("Narration manifest does not use the story's selected voice")

    args.work.mkdir(parents=True, exist_ok=True)
    segments = args.work / "segments"
    segments.mkdir(parents=True, exist_ok=True)
    video_list = args.work / "video-concat.txt"
    audio_list = args.work / "audio-concat.txt"
    srt = args.output.with_suffix(".srt")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    video_entries, audio_entries, cues, technical = [], [], [], []

    for shot in story["shots"]:
        sid = shot["id"]
        target = float(shot["duration"])
        frames = round(target * FPS)
        record = results.get("shots", {}).get(sid, {})
        source = args.sources / f"{sid}.mp4"
        if record.get("status") != "completed" or not source.is_file():
            raise RuntimeError(f"{sid}: no completed, retrieved Agnes source; refusing a still substitute")
        if record.get("request_hash") != __import__("generate").request_hash(story, shot):
            raise RuntimeError(f"{sid}: request hash differs from the approved storyboard")
        if record.get("sha256") != digest(source) or record.get("bytes") != source.stat().st_size:
            raise RuntimeError(f"{sid}: source SHA-256/size differs from its Agnes receipt")
        source_probe = probe(source)
        video = next((s for s in source_probe["streams"] if s.get("codec_type") == "video"), None)
        if not video:
            raise RuntimeError(f"{sid}: source has no video stream")
        source_duration = float(source_probe["format"]["duration"])
        width, height = int(video["width"]), int(video["height"])
        if source_duration < target - 1 / FPS or width < 640 or height < 360:
            raise RuntimeError(f"{sid}: source too short or too small ({source_duration:.3f}s, {width}x{height})")
        if abs(width / height - 16 / 9) > 0.015:
            raise RuntimeError(f"{sid}: source aspect ratio is not 16:9; refusing to distort/crop")

        normalized = segments / f"{sid}.mp4"
        if sid == "S30":
            # Closing shot: hold the falling drop, then a 0.6s fade into black under the end title.
            vf = (f"scale=1920:1080:flags=lanczos,fps={FPS},trim=duration={target:.6f},"
                  f"setpts=PTS-STARTPTS,setsar=1,format=yuv420p,"
                  f"fade=t=out:st={target-0.8:.3f}:d=0.8")
            filter_args = ["-vf", vf, "-map", "0:v:0"]
        else:
            vf = f"scale=1920:1080:flags=lanczos,fps={FPS},trim=duration={target:.6f},setpts=PTS-STARTPTS,setsar=1,format=yuv420p"
            filter_args = ["-vf", vf, "-map", "0:v:0"]
        run(["ffmpeg", "-y", "-v", "error", "-threads", "2", "-i", source,
             *filter_args, "-an", "-frames:v", frames, "-r", FPS,
             "-vsync", "cfr", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
             "-movflags", "+faststart", normalized])
        video_entries.append(f"file '{normalized.resolve()}'")

        arow = audio_rows.get(sid)
        narration = HERE / "audio" / (arow.get("file", "") if arow else "")
        if not arow or not narration.is_file() or arow.get("text") != shot["narration"]:
            raise RuntimeError(f"{sid}: missing narration or narration text mismatch")
        if arow.get("sha256") != digest(narration) or arow.get("voice_id") != manifest["voice"]:
            raise RuntimeError(f"{sid}: narration checksum/voice provenance mismatch")
        raw_duration = duration(narration)
        speed = max(1.0, raw_duration / target)
        if speed > 1.55 + 1e-9:
            raise RuntimeError(f"{sid}: speech needs {speed:.3f}x, beyond the 1.55x limit")
        wav = segments / f"{sid}.wav"
        audio_filter = f"atempo={speed:.6f},apad,atrim=duration={target:.6f},asetpts=PTS-STARTPTS"
        run(["ffmpeg", "-y", "-v", "error", "-i", narration, "-vn", "-af", audio_filter,
             "-ar", RATE, "-ac", 2, "-c:a", "pcm_s16le", wav])
        audio_entries.append(f"file '{wav.resolve()}'")
        speech_end = min(target, raw_duration / speed)
        cues.append((float(shot["start"]), float(shot["start"]) + speech_end, shot["narration"]))
        technical.append({"id": sid, "target_seconds": target, "target_frames": frames,
                          "source_seconds": round(source_duration, 3), "source_size": [width, height],
                          "source_sha256": record["sha256"], "narration_seconds": round(raw_duration, 3),
                          "narration_atempo": round(speed, 4)})

    video_list.write_text("\n".join(video_entries) + "\n", encoding="utf-8")
    audio_list.write_text("\n".join(audio_entries) + "\n", encoding="utf-8")
    srt.write_text("\n".join(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n"
                                  for i, (a, b, text) in enumerate(cues, 1)), encoding="utf-8")
    ass = args.work / "subtitles.ass"
    pres = story["presentation"]
    write_ass(ass, cues, pres.get("highlight_phrases", []),
              (pres.get("end_title", ""), pres.get("end_subtitle", ""),
               174.6, 179.5) if pres.get("end_title") else None)
    silent = args.work / "picture-only.mp4"
    voice = args.work / "voiceover.wav"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", video_list,
         "-c", "copy", "-an", "-movflags", "+faststart", silent])
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", audio_list,
         "-c:a", "pcm_s16le", "-ar", RATE, "-ac", 2, voice])

    subtitle_filter = f"subtitles='{ffmpeg_escape(ass)}'"
    run(["ffmpeg", "-y", "-v", "error", "-threads", "2", "-i", silent, "-i", voice,
         "-vf", subtitle_filter, "-map", "0:v:0", "-map", "1:a:0", "-t", "180",
         "-frames:v", 180 * FPS, "-r", FPS, "-vsync", "cfr",
         "-c:v", "libx264", "-preset", "medium", "-crf", "22",
         "-maxrate", "3200k", "-bufsize", "6400k", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", RATE, "-ac", 2, "-movflags", "+faststart", args.output])
    # GitHub rejects a single file over 100 MB; a 3-minute 1080p master must fit comfortably.
    size_mb = args.output.stat().st_size / (1024 * 1024)
    if size_mb > 95:
        raise RuntimeError(f"Final master is {size_mb:.1f} MB; cap the bitrate before delivering")

    cover = args.output.parent / "消失的未婚夫_Cover.jpg"
    run(["ffmpeg", "-y", "-v", "error", "-ss", "2", "-i", args.output,
         "-frames:v", 1, "-q:v", 2, cover])
    report = {"film": str(args.output), "duration_seconds": 180, "width": 1920, "height": 1080,
              "fps": FPS, "frames": 180 * FPS, "audio": "voiceover only; no unlicensed music",
              "subtitle_file": str(srt), "shots": technical}
    report_path = args.work / "technical-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("FIRST_CUT_READY", args.output, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
