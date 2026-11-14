#!/usr/bin/env python3
"""Deterministic 180 s cut from verified Agnes video, shot-locked narration and SFX."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FPS = 24
RATE = 48_000
# Targeted, frame-locked exposure repairs found during final visual triage.  Each is
# confined to the offending source frame/window; runtime, cut points, and audio sync stay fixed.
FLASH_REPAIR_FRAME = 464             # S04, 19.333s: blend isolated near-black frame.
HOLD_REPAIR_FRAMES = (2533, 3450)    # S18, 105.542s and S24, 143.750s: one-frame occlusion dips.
DARK_REPAIR_START = 159.25           # S27: raise only the brief unmotivated exposure dip.
DARK_REPAIR_END = 160.0417
DARK_REPAIR_GAMMA = 1.5


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


def caption_lines(text: str, limit: int = 20) -> list[str]:
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


def ass_caption(text: str, phrases: list[str], highlight_size: int = 50) -> str:
    """Apply gold to selected phrases, restoring the active base style after each hit."""
    text = ass_escape(text)
    ordered = sorted(set(phrases), key=len, reverse=True)
    out = []
    i = 0
    while i < len(text):
        hit = next((phrase for phrase in ordered if text.startswith(phrase, i)), None)
        if hit:
            out.append(r"{\c&H0000C8FF&\fs" + str(highlight_size) + "}" + hit + r"{\r}")
            i += len(hit)
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def write_ass(path: Path, cues: list[tuple[float, float, str]], phrases: list[str],
              end_card: tuple[str, str, float, float] | None = None,
              onscreen_label: str = "", hooks: list[dict] | None = None,
              explainers: list[dict] | None = None) -> None:
    rows = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Caption,Noto Sans CJK SC,44,&H00FFFFFF,&H00FFFFFF,&H00111110,&H99000000,0,0,0,0,100,100,0,0,1,2.4,0.6,2,120,120,62,1",
        "Style: Label,Noto Sans CJK SC,26,&H60FFFFFF,&H00FFFFFF,&H00101010,&H00000000,0,0,0,0,100,100,0,0,1,1.4,0.0,7,52,52,34,1",
        "Style: Hook,Noto Sans CJK SC,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4.0,1.0,2,100,100,275,1",
        "Style: Explainer,Noto Sans CJK SC,32,&H0000C8FF,&H00FFFFFF,&H00000000,&H70000000,0,0,0,0,100,100,0,0,1,2.2,0.5,2,120,120,145,1",
        "Style: Title,Noto Sans CJK SC,104,&H0000C8FF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,2,0,1,3.0,1.0,2,120,120,330,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for start, end, text in cues:
        rendered = r"\N".join(ass_caption(line, phrases) for line in caption_lines(text))
        rows.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{{\\q2\\fad(60,70)}}{rendered}")
    for hook in hooks or []:
        start, end = float(hook["start"]), float(hook["end"])
        if abs((end - start) - 2.0) > 1e-6:
            raise ValueError(f"{hook.get('id')}: hook overlay must be exactly 2 seconds")
        rendered = r"\N".join(
            ass_caption(line, phrases, highlight_size=86)
            for line in caption_lines(str(hook["text"]), limit=18)
        )
        rows.append(f"Dialogue: 2,{ass_time(start)},{ass_time(end)},Hook,,0,0,0,,{{\\q2\\fad(90,100)}}{rendered}")
    for explainer in explainers or []:
        start, end = float(explainer["start"]), float(explainer["end"])
        if end <= start:
            raise ValueError("Explainer overlay has a non-positive duration")
        rendered = r"\N".join(caption_lines(str(explainer["text"]), limit=28))
        rows.append(f"Dialogue: 1,{ass_time(start)},{ass_time(end)},Explainer,,0,0,0,,{{\\q2\\fad(90,120)}}{rendered}")
    if onscreen_label:
        rows.append(f"Dialogue: 0,{ass_time(0.8)},{ass_time(176.0)},Label,,0,0,0,,{{\\q2\\fad(300,300)}}{ass_escape(onscreen_label)}")
    if end_card:
        title, subtitle, start, end = end_card
        card = (ass_escape(title) + r"\N" +
                r"{\fs38\c&H00FFFFFF&}" + ass_escape(subtitle))
        rows.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Title,,0,0,0,,{{\\q2\\fad(200,400)}}{card}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_cover_ass(path: Path, title: str, subtitle: str) -> None:
    """Lay clean, legible title type over a real frame from this film (never a reference PNG)."""
    rows = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: CoverTitle,Noto Sans CJK SC,144,&H0000C8FF,&H00FFFFFF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,6,2,2,100,100,188,1",
        "Style: CoverSubtitle,Noto Sans CJK SC,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&HAA000000,0,0,0,0,100,100,0,0,1,3,1,8,100,100,64,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 1,0:00:00.00,0:00:02.00,CoverSubtitle,,0,0,0,,{{\\q2\\fad(0,0)}}{ass_escape(subtitle)}",
        f"Dialogue: 2,0:00:00.00,0:00:02.00,CoverTitle,,0,0,0,,{{\\q2\\fad(0,0)}}{ass_escape(title)}",
    ]
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
    sfx_dir = args.work / "sfx"
    subprocess.run([sys.executable, str(HERE / "build_sfx.py"), "--output", str(sfx_dir)],
                   cwd=ROOT, check=True)
    sfx_manifest = json.loads((sfx_dir / "manifest.json").read_text(encoding="utf-8"))
    sfx_rows = {row["id"]: row for row in sfx_manifest.get("clips", [])}
    if len(sfx_rows) != len(story["shots"]) or "no BGM" not in sfx_manifest.get("policy", ""):
        raise RuntimeError("Need exactly 30 scripted SFX clips and no BGM")
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
        # Strip the TTS lead-in silence first: otherwise every caption cue runs ~0.3s ahead
        # of the spoken word and the last line can spill past its shot window.
        speech = segments / f"{sid}.speech.wav"
        run(["ffmpeg", "-y", "-v", "error", "-i", narration, "-vn", "-af",
             "silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB:start_silence=0.06,"
             f"atempo={speed:.6f}", "-ar", RATE, "-ac", 2, "-c:a", "pcm_s16le", speech])
        speech_seconds = duration(speech)
        if speech_seconds > target:
            extra = speech_seconds / target
            if speed * extra > 1.55 + 1e-9:
                raise RuntimeError(f"{sid}: speech cannot fit even at 1.55x")
            run(["ffmpeg", "-y", "-v", "error", "-i", speech, "-vn", "-af",
                 f"atempo={extra:.6f}", "-ar", RATE, "-ac", 2, "-c:a", "pcm_s16le", speech])
            speech_seconds = duration(speech)
        sfx_record = sfx_rows.get(sid, {})
        sfx_path = sfx_dir / sfx_record.get("file", "missing.wav")
        if (not sfx_path.is_file() or sfx_record.get("script_note") != shot["sound_design"]
                or sfx_record.get("sha256") != digest(sfx_path)
                or abs(float(sfx_record.get("seconds", 0)) - target) > 1e-9):
            raise RuntimeError(f"{sid}: scripted SFX file/hash/timing mismatch")
        wav = segments / f"{sid}.wav"
        # Pad narration to the exact shot window, mix only restrained scripted SFX underneath,
        # then trim to the exact shot length. No generated-video audio or BGM enters the mix.
        # This runner's pinned FFmpeg 4.1 build predates amix's ``normalize`` option.
        # Its default normalization divides two inputs by their count, so restore that
        # factor immediately after amix to retain the intended voice + quiet-SFX gain.
        mix_filter = (
            f"[0:a]apad,atrim=duration={target:.6f},volume=1.0[voice];"
            f"[1:a]atrim=duration={target:.6f},volume=0.35[sfx];"
            f"[voice][sfx]amix=inputs=2:duration=first:dropout_transition=0,volume=2.0,"
            f"alimiter=limit=0.98,atrim=duration={target:.6f}[a]"
        )
        run(["ffmpeg", "-y", "-v", "error", "-i", speech, "-i", sfx_path,
             "-filter_complex", mix_filter, "-map", "[a]", "-ar", RATE, "-ac", 2,
             "-c:a", "pcm_s16le", wav])
        segment_seconds = duration(wav)
        if abs(segment_seconds - target) > 0.02:
            raise RuntimeError(f"{sid}: narration segment is {segment_seconds:.3f}s, expected {target:.3f}s")
        audio_entries.append(f"file '{wav.resolve()}'")
        cues.append((float(shot["start"]),
                     float(shot["start"]) + min(target - 0.04, speech_seconds), shot["narration"]))
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
    write_ass(
        ass, cues, pres.get("highlight_phrases", []),
        (pres.get("end_title", ""), pres.get("end_subtitle", ""),
         float(pres.get("title_start", 174.6)), float(pres.get("title_end", 179.5)))
        if pres.get("end_title") else None,
        pres.get("onscreen_label", ""), pres.get("hooks", []), pres.get("explainers", []),
    )
    silent = args.work / "picture-only.mp4"
    audio_mix = args.work / "audio-mix.wav"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", video_list,
         "-c", "copy", "-an", "-movflags", "+faststart", silent])
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", audio_list,
         "-c:a", "pcm_s16le", "-ar", RATE, "-ac", 2, audio_mix])
    audio_mix_seconds = duration(audio_mix)
    if abs(audio_mix_seconds - 180.0) > 0.02:
        # Force the narration/SFX bus to the full 180s so no line or tail can be clipped.
        run(["ffmpeg", "-y", "-v", "error", "-i", audio_mix, "-af", "apad",
             "-t", "180.0", "-ar", RATE, "-ac", 2, "-c:a", "pcm_s16le", audio_mix])
        audio_mix_seconds = duration(audio_mix)
    if abs(audio_mix_seconds - 180.0) > 0.05:
        raise RuntimeError(f"Audio mix is {audio_mix_seconds:.3f}s; the master must be 180.000s")

    subtitle_filter = f"subtitles='{ffmpeg_escape(ass)}'"
    gamma_expr = (
        f"1+{DARK_REPAIR_GAMMA - 1:.3f}*max(0,min(1,min("
        f"(t-{DARK_REPAIR_START:.4f})/0.125,({DARK_REPAIR_END:.4f}-t)/0.125)))"
    )
    hold_expr = "+".join(f"eq(n,{frame})" for frame in HOLD_REPAIR_FRAMES)
    picture_filter = (
        f"eq=gamma='{gamma_expr}':eval=frame,{subtitle_filter},"
        f"tblend=all_mode=average:enable='eq(n,{FLASH_REPAIR_FRAME})',"
        f"tblend=all_mode=lighten:enable='{hold_expr}'"
    )
    # Encode picture and narration/SFX mix separately and then stream-copy them together.
    # On the runner's older ffmpeg a single combined encode silently dropped the last ~2s of
    # audio (177.834s instead of 180.000s), which clipped the closing question.
    picture = args.work / "picture-subbed.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-threads", "2", "-i", silent,
         "-vf", picture_filter, "-an", "-t", "180", "-frames:v", 180 * FPS,
         "-r", FPS, "-vsync", "cfr", "-c:v", "libx264", "-preset", "medium", "-crf", "22",
         "-maxrate", "3200k", "-bufsize", "6400k", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", picture])
    audio_bus = args.work / "audio-bus.m4a"
    run(["ffmpeg", "-y", "-v", "error", "-i", audio_mix, "-af", "apad", "-t", "180",
         "-c:a", "aac", "-b:a", "192k", "-ar", RATE, "-ac", 2, audio_bus])
    run(["ffmpeg", "-y", "-v", "error", "-i", picture, "-i", audio_bus,
         "-map", "0:v:0", "-map", "1:a:0", "-c", "copy", "-t", "180",
         "-movflags", "+faststart", args.output])
    print(f"PICTURE {duration(picture):.3f}s  AUDIO_MIX {audio_mix_seconds:.3f}s  MUXED {duration(args.output):.3f}s",
          flush=True)
    # GitHub rejects a single file over 100 MB; a 3-minute 1080p master must fit comfortably.
    size_mb = args.output.stat().st_size / (1024 * 1024)
    if size_mb > 95:
        raise RuntimeError(f"Final master is {size_mb:.1f} MB; cap the bitrate before delivering")

    pcm = probe(args.output)
    audio_stream = next((s for s in pcm["streams"] if s.get("codec_type") == "audio"), None)
    if audio_stream is None:
        raise RuntimeError("Master has no audio stream")
    audio_seconds = float(audio_stream.get("duration") or 0.0)
    if abs(audio_seconds - 180.0) > 0.06:
        raise RuntimeError(f"Master audio stream is {audio_seconds:.3f}s, expected 180.000s")

    cover = args.output.parent / "光州胶带案_Cover.jpg"
    cover_ass = args.work / "cover.ass"
    write_cover_ass(cover_ass, pres.get("cover_text", "22米胶带"), pres.get("end_title", "光州胶带案"))
    cover_filter = f"setpts=PTS-STARTPTS,subtitles='{ffmpeg_escape(cover_ass)}'"
    run(["ffmpeg", "-y", "-v", "error", "-ss", "2", "-i", silent,
         "-vf", cover_filter, "-frames:v", 1, "-q:v", 2, cover])
    if not cover.is_file() or cover.stat().st_size < 10_000:
        raise RuntimeError("Cover must be a real 1080p frame from the rendered film with the post-production title")

    report = {"film": str(args.output), "duration_seconds": 180, "width": 1920, "height": 1080,
              "audio_mix_seconds": round(audio_mix_seconds, 3), "audio_stream_seconds": round(audio_seconds, 3),
              "fps": FPS, "frames": 180 * FPS,
              "audio": "shot-locked Mandarin narration plus scripted procedural SFX only; no BGM",
              "sfx_manifest": str((sfx_dir / "manifest.json").relative_to(ROOT)),
              "cover": str(cover), "cover_sha256": digest(cover),
              "cover_source": "frame at 2 seconds from the rendered picture-only film; ASS title overlay",
              "subtitle_file": str(srt), "shots": technical}
    report_path = args.work / "technical-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("FIRST_CUT_READY", args.output, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
