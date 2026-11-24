#!/usr/bin/env python3
"""《门田典子案：三个女人——一个死在暴力里，一个死在自己曾经做过的事里》—— 确定性 180 秒成片（模板由 production/templates/render.py 生成；内容只写在 build_story.py 里）。

只接受 results.json 里登记过、SHA-256 对得上的 Agnes 2.5 Flash 720P 片段 + 每镜一条 TTS；
缺任何一镜都直接报错，绝不用静帧/幻灯片顶替。输出成片、SRT、Technical_Report.json 与 QA 抽帧。
字幕、钩子大字、金色注释全部走仓库共享的 gwangju_style.py（从仓库根 production/ 导入，不拷贝）。
"""
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
# 结尾渐黑（本片专属，可按需增删）：镜头号 -> (在结束前多少秒开始淡出, 淡出时长秒)。
# 默认只给最后一镜 S30（片尾标题在渐黑中压暗收场）；别的镜头的情绪停顿靠剪辑与音效做。
END_FADES = {"S30": (0.8, 0.8)}
# Agnes 2.5 Flash 最长只接受 12 秒来源；镜头窗口超过 12 秒时，渲染会以克隆最后一帧补齐（最多 2 秒），
# 并在日志里打印 SHORT-SOURCE 警告。超过 2 秒的不足仍然直接报错，绝不静默拉伸/变格。
SOURCE_SHORTFALL_TOLERANCE = 2.0


def normalized_video_filter(shot_id: str, shot_start: float,
                            target_seconds: float, frame_count: int,
                            shortfall: float = 0.0) -> str:
    """Build a shot's normalized picture filter (global anti-flicker grade only)."""
    if frame_count != round(target_seconds * FPS):
        raise ValueError(f"{shot_id}: frame count does not match its target duration")
    base = (
        f"deflicker=size=61:mode=am,hqdn3d=3:2:9:9,"
        f"scale=1920:1080:flags=lanczos,fps={FPS},"
        f"eq=contrast=0.97:brightness=0.018:saturation=0.94"
    )
    if shortfall > 0:
        print(f"SHORT-SOURCE {shot_id}: source is {shortfall:.3f}s under the {target_seconds:.1f}s window; "
              f"holding the last frame (tolerance {SOURCE_SHORTFALL_TOLERANCE:.1f}s)", flush=True)
        base += f",tpad=stop_mode=clone:stop_duration={shortfall + 0.05:.3f}"
    vf = (f"{base},trim=duration={target_seconds:.6f},setpts=PTS-STARTPTS,"
          "setsar=1,format=yuv420p")
    fade = END_FADES.get(shot_id)
    if fade:
        offset, fade_duration = fade
        # 只做画面渐隐；文字层由 presentation.hooks / explainers / end_title 承担，不新增后期大字。
        vf += f",fade=t=out:st={max(0.0, target_seconds - offset):.3f}:d={fade_duration:.3f}"
    return vf


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


# 默认画面文字层：光州胶带案风格已固化为仓库共享模板。
sys.path.insert(0, str(ROOT / "production"))
from gwangju_style import ass_time, ass_escape, caption_lines, ass_caption, write_ass  # noqa: E402


def write_cover_ass(path: Path, title: str, subtitle: str) -> None:
    """Lay clean, legible title type over a real frame from this film (never a reference PNG)."""
    rows = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: CoverTitle,Noto Sans CJK SC,144,&H0000C8FF,&H00FFFFFF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,6,2,2,100,100,188,1",
        "Style: CoverSubtitle,Noto Sans CJK SC,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&HAA000000,0,0,0,0,100,100,0,0,1,3,1,8,100,100,64,1",
        "Style: CoverAI,Noto Sans CJK SC,30,&H99FFFFFF,&H00FFFFFF,&H00000000,&HAA000000,0,0,0,0,100,100,0,0,1,1.6,0.5,7,34,34,26,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 1,0:00:00.00,0:00:02.00,CoverSubtitle,,0,0,0,,{{\\q2\\fad(0,0)}}{ass_escape(subtitle)}",
        f"Dialogue: 2,0:00:00.00,0:00:02.00,CoverTitle,,0,0,0,,{{\\q2\\fad(0,0)}}{ass_escape(title)}",
        "Dialogue: 3,0:00:00.00,0:00:02.00,CoverAI,,0,0,0,,AI动画情景重现 · 非真实影像",
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
        shortfall = max(0.0, target - source_duration)
        if shortfall > SOURCE_SHORTFALL_TOLERANCE or width < 640 or height < 360:
            raise RuntimeError(f"{sid}: source too short or too small ({source_duration:.3f}s, {width}x{height}; "
                               f"shortfall tolerance {SOURCE_SHORTFALL_TOLERANCE:.1f}s)")
        if abs(width / height - 16 / 9) > 0.015:
            raise RuntimeError(f"{sid}: source aspect ratio is not 16:9; refusing to distort/crop")

        normalized = segments / f"{sid}.mp4"
        vf = normalized_video_filter(sid, float(shot["start"]), target, frames, shortfall)
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
        # 2026-11-24（第二十六期）：-50dB 太宽松。选定的 TTS 音色在字头前普遍有约 0.2 秒
        # −47～−50dB 的气口，穿得过阈值，导致字幕比语音早 0.23 秒（S05 判 FAIL）。
        # 改为 -36dB 并附加「持续 3 个 10ms 块」条件：既切掉气口，又不会削掉以弱辅音开头的字头。
        speech = segments / f"{sid}.speech.wav"
        run(["ffmpeg", "-y", "-v", "error", "-i", narration, "-vn", "-af",
             "silenceremove=start_periods=1:start_duration=0.03:start_threshold=-36dB:start_silence=0.06,"
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
    picture_filter = subtitle_filter
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

    film_name = str(story.get("film_name") or args.output.name)
    stem = film_name[: -len("_三分钟_带声音.mp4")] if film_name.endswith("_三分钟_带声音.mp4") else Path(film_name).stem
    cover_text = pres.get("cover_text") or ""
    end_title = pres.get("end_title") or ""
    if not cover_text or not end_title:
        raise RuntimeError("presentation.cover_text / presentation.end_title 必须在 build_story.py 里填好，渲染才生成封面")
    cover = args.output.parent / f"{stem}_Cover.jpg"
    cover_ass = args.work / "cover.ass"
    write_cover_ass(cover_ass, cover_text, end_title)
    cover_filter = f"setpts=PTS-STARTPTS,subtitles='{ffmpeg_escape(cover_ass)}'"
    run(["ffmpeg", "-y", "-v", "error", "-ss", "2", "-i", silent,
         "-vf", cover_filter, "-frames:v", 1, "-q:v", 2, cover])
    if not cover.is_file() or cover.stat().st_size < 10_000:
        raise RuntimeError("Cover must be a real 1080p frame from the rendered film with the post-production title")

    report = {"film": str(args.output), "duration_seconds": 180, "width": 1920, "height": 1080,
              "audio_mix_seconds": round(audio_mix_seconds, 3), "audio_stream_seconds": round(audio_seconds, 3),
              "fps": FPS, "frames": 180 * FPS,
              "anti_flicker": "all shots: deflicker=size=61:mode=am,hqdn3d=3:2:9:9,eq=contrast=0.97:brightness=0.018:saturation=0.94; no legacy frame gamma/blend spikes; no strobe/flash transitions",
              "audio": "shot-locked Mandarin narration plus scripted procedural SFX only; no BGM",
              "sfx_manifest": str((sfx_dir / "manifest.json").relative_to(ROOT)),
              "cover": str(cover), "cover_sha256": digest(cover),
              "cover_source": "frame at 2 seconds from the rendered picture-only film; ASS title overlay",
              "subtitle_file": str(srt), "shots": technical}
    report_path = args.work / "technical-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # 逐字听检（production/verbatim_check.py）按章节边界切成片再转写，边界只能来自渲染实测。
    # 2026-11-24：这条时间轴以前没人写，听检在 Actions 上一步就 SystemExit（少了报告，
    # 但 continue-on-error 把它算成 success），等于听检从未真正跑过。缺文件必须当场崩，
    # 不许让"没跑"看起来像"通过"。
    timing = HERE / "delivery" / "narration-timing.json"
    timing.parent.mkdir(parents=True, exist_ok=True)
    timing.write_text(json.dumps(
        {"film_sha256": digest(args.output),
         "note": "render.py 实测的章节边界（字幕窗口同源），供 verbatim_check.py 切片转写",
         "chapters": [{"id": row["id"], "start": shot["start"],
                       "end": round(shot["start"] + row["target_seconds"], 3)}
                      for row, shot in zip(technical, story["shots"])]},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("TIMING_WRITTEN", timing.relative_to(ROOT), flush=True)
    print("FIRST_CUT_READY", args.output, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
