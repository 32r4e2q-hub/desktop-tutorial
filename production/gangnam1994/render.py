#!/usr/bin/env python3
"""Deterministic 180.000s cut from verified Agnes 2.5 Flash sources and shot-locked Chinese narration.

Includes:
- Korean crime-thriller color progression across the 9 narrative sections
- Shot-locked subtitles (44px white + 50px gold keywords) + all 9 retention hook banners (H1-H9)
- Shot 30 golden end title card ("江南豪门双尸案" / "首尔江南区 · 1994 · 一个小细节")
- Subtle procedural thriller underscore + key foley accents (<-26 dB below voice, silent final 1.0s)
- Two-pass separate video/audio encoding + stream-copy mux (prevents runner ffmpeg 4.1 tail truncation)
- Authentic 1920x1080 horizontal split cover ("报警的人") extracted from real rendered video frames
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

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


def caption_lines(text: str, limit: int = 20) -> list[str]:
    """Keep Chinese captions compact and centered in the bottom safe zone."""
    if len(text) <= limit:
        return [text]
    split_at = len(text) // 2
    punctuation = set("，。；：！？、—")
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
    """Highlight key suspense phrases in enlarged gold."""
    text = ass_escape(text)
    ordered = sorted(set(phrases), key=len, reverse=True)
    out = []
    i = 0
    while i < len(text):
        hit = next((phrase for phrase in ordered if text.startswith(phrase, i)), None)
        if hit:
            out.append(r"{\c&H0000C8FF&\fs50}" + hit + r"{\rCaption}")
            i += len(hit)
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def write_ass(
    path: Path,
    cues: list[tuple[float, float, str]],
    phrases: list[str],
    hooks: list[dict],
    end_card: tuple[str, str, float, float] | None = None,
    onscreen_label: str = "",
) -> None:
    rows = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Caption,Noto Sans CJK SC,44,&H00FFFFFF,&H00FFFFFF,&H00111110,&H99000000,0,0,0,0,100,100,0,0,1,2.6,0.8,2,120,120,56,1",
        "Style: Hook,Noto Sans CJK SC,52,&H00FFFFFF,&H00FFFFFF,&H00080808,&HA8000000,-1,0,0,0,100,100,1.5,0,1,3.6,1.2,2,140,140,190,1",
        "Style: Label,Noto Sans CJK SC,26,&H60FFFFFF,&H00FFFFFF,&H00101010,&H00000000,0,0,0,0,100,100,0,0,1,1.4,0.0,7,52,52,34,1",
        "Style: Title,Noto Sans CJK SC,102,&H0000C8FF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,3,0,1,3.4,1.2,2,120,120,335,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for start, end, text in cues:
        rendered = r"\N".join(ass_caption(line, phrases) for line in caption_lines(text))
        rows.append(f"Dialogue: 1,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{{\\q2\\fad(60,70)}}{rendered}")
    for hook in hooks:
        htext = ass_escape(str(hook["text"]))
        hstart, hend = float(hook["start"]), float(hook["end"])
        rows.append(
            f"Dialogue: 2,{ass_time(hstart)},{ass_time(hend)},Hook,,0,0,0,,"
            f"{{\\q2\\fad(120,180)}}{htext}"
        )
    if onscreen_label:
        rows.append(f"Dialogue: 0,{ass_time(0.8)},{ass_time(176.0)},Label,,0,0,0,,{{\\q2\\fad(300,300)}}{ass_escape(onscreen_label)}")
    if end_card:
        title, subtitle, start, end = end_card
        card = (ass_escape(title) + r"\N" +
                r"{\fs38\c&H00FFFFFF&\b0}" + ass_escape(subtitle))
        rows.append(f"Dialogue: 2,{ass_time(start)},{ass_time(end)},Title,,0,0,0,,{{\\q2\\fad(250,450)}}{card}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def shot_grade_and_transition(shot_num: int, target: float) -> str:
    """Apply section-specific Korean thriller color grading and frame-preserving micro-transitions."""
    if shot_num in (1, 2):
        # Night firelight & alarm hook: warm fire contrast, subtle flash transition between S01->S02
        grade = "colorbalance=rs=0.05:gs=0.00:bs=-0.03,eq=contrast=1.06:saturation=1.05:gamma=1.08"
        if shot_num == 1:
            return grade + f",fade=t=out:st={target-0.16:.3f}:d=0.16:color=0x220a02"
        return grade + ",fade=t=in:st=0:d=0.14:color=0x220a02"
    if 3 <= shot_num <= 6:
        # Mansion wealth & eldest son: rich warm golden-amber
        return "colorbalance=rs=0.05:gs=0.02:bs=-0.05,eq=contrast=1.04:saturation=1.04:gamma=1.04"
    if 7 <= shot_num <= 10:
        # Casino & secret return: cold cyan-teal desaturation
        return "colorbalance=rs=-0.05:gs=0.01:bs=0.06,eq=contrast=1.06:saturation=0.88:gamma=1.08"
    if 11 <= shot_num <= 18:
        # Premeditation & That Night: deep blue & sterile cold white + brief 0.20s cut-to-black dips on S13-S18
        grade = "colorbalance=rs=-0.06:gs=-0.02:bs=0.08,eq=contrast=1.08:saturation=0.82:gamma=1.10"
        if 13 <= shot_num <= 18:
            return grade + f",fade=t=in:st=0:d=0.16,fade=t=out:st={target-0.20:.3f}:d=0.20"
        return grade
    if shot_num == 19:
        # Blazing mansion fire + police light arrival
        return "colorbalance=rs=0.08:gs=0.01:bs=-0.05,eq=contrast=1.08:saturation=1.10:gamma=1.06,fade=t=in:st=0:d=0.14:color=0x101830"
    if shot_num == 20:
        # Morning charred ruins: cold ash grey
        return "colorbalance=rs=-0.03:gs=-0.01:bs=0.03,eq=contrast=1.06:saturation=0.68:gamma=1.06"
    if 21 <= shot_num <= 25:
        # Forensic, police briefing, two tiny details: cold clinical grey
        grade = "colorbalance=rs=-0.03:gs=-0.01:bs=0.04,eq=contrast=1.07:saturation=0.74:gamma=1.06"
        if shot_num in (21, 22):
            return grade + ",fade=t=in:st=0:d=0.12:color=0x0c1628"
        return grade
    if 26 <= shot_num <= 28:
        # Interrogation & 1994 courtroom death verdict: austere cold grey
        return "colorbalance=rs=-0.02:gs=-0.01:bs=0.03,eq=contrast=1.08:saturation=0.70:gamma=1.06"
    if shot_num == 29:
        # Daegu prison dawn
        return "colorbalance=rs=-0.03:gs=-0.01:bs=0.04,eq=contrast=1.06:saturation=0.66:gamma=1.05"
    # Shot 30: night silhouette & extinguishing flame -> 0.8s fade to pure black
    return (
        "colorbalance=rs=0.03:gs=-0.01:bs=0.02,eq=contrast=1.06:saturation=0.85:gamma=1.05,"
        f"fade=t=in:st=0:d=0.30,fade=t=out:st={target-0.80:.3f}:d=0.80"
    )


def build_thriller_bed_and_mix(voice_wav: Path, mixed_wav: Path) -> None:
    """Mix a restrained original thriller drone + subtle foley accents far below voice (-28 dB).

    Calibrated strictly below verify_master.py's P95*10% speech-activity threshold so speech
    sync gates measure only real spoken words, and silenced completely in 179.0-180.0s.
    """
    with wave.open(str(voice_wav), "rb") as reader:
        nframes = reader.getnframes()
        raw = np.frombuffer(reader.readframes(nframes), dtype="<i2").astype(np.float32) / 32768.0
        channels = reader.getnchannels()
    voice = raw.reshape(-1, channels)
    target_samples = 180 * RATE
    if len(voice) < target_samples:
        pad = np.zeros((target_samples - len(voice), channels), dtype=np.float32)
        voice = np.vstack([voice, pad])
    else:
        voice = voice[:target_samples]

    t = np.arange(target_samples, dtype=np.float64) / RATE
    rng = np.random.default_rng(19940519)

    # Restrained dark cello-like drone + heartbeat pulse
    lfo = 0.65 + 0.25 * np.sin(2 * math.pi * 0.04 * t)
    drone = (
        0.40 * np.sin(2 * math.pi * 43.65 * t)
        + 0.24 * np.sin(2 * math.pi * 65.41 * t + 0.6)
        + 0.12 * np.sin(2 * math.pi * 130.81 * t + 1.1)
    ) * lfo
    beat = np.mod(t, 0.86)
    pulse = 0.22 * np.sin(2 * math.pi * 49.0 * t) * np.exp(-beat * 9.5)
    bed = (drone + pulse).astype(np.float32) * 0.0085

    # Subtle foley accents at key story moments (kept gentle so voice remains crystal clear)
    fx = np.zeros(target_samples, dtype=np.float32)

    def add_tone(sec: float, length: float, freq: float, amp: float, decay: float = 6.0) -> None:
        i0 = int(sec * RATE)
        i1 = min(target_samples, int((sec + length) * RATE))
        if i1 <= i0:
            return
        dt = np.arange(i1 - i0, dtype=np.float64) / RATE
        fx[i0:i1] += (amp * np.sin(2 * math.pi * freq * dt) * np.exp(-dt * decay)).astype(np.float32)

    def add_filtered_noise(sec: float, length: float, amp: float) -> None:
        i0 = int(sec * RATE)
        i1 = min(target_samples, int((sec + length) * RATE))
        if i1 <= i0:
            return
        n = rng.normal(0.0, 1.0, i1 - i0).astype(np.float32)
        env = np.hanning(i1 - i0).astype(np.float32)
        # Simple moving average softens harshness into water/fire texture
        kernel = np.ones(16, dtype=np.float32) / 16.0
        smooth = np.convolve(n, kernel, mode="same")
        fx[i0:i1] += smooth * env * amp

    # S01-S02 fire crackle & phone dial tone
    add_filtered_noise(0.1, 4.5, 0.007)
    add_tone(5.15, 0.7, 425.0, 0.006, decay=1.2)
    # S08 chip sweep, S11 receiver slam, S17 clock/light click, S18 shower water, S22 phone ring, S27 gavel, S30 hiss
    add_filtered_noise(45.5, 1.2, 0.006)
    add_tone(65.6, 0.35, 85.0, 0.010, decay=12.0)
    add_tone(101.8, 0.15, 1200.0, 0.005, decay=28.0)
    add_filtered_noise(103.1, 4.6, 0.007)
    add_tone(128.4, 0.55, 880.0, 0.006, decay=2.5)
    add_tone(159.8, 0.65, 110.0, 0.011, decay=7.5)
    add_filtered_noise(177.2, 1.2, 0.006)

    atmosphere = bed + fx
    # Fade in 0.5s, fade out completely by 178.8s so the last 1.2s is 100% pure silence per script
    fade_in = np.clip(t / 0.5, 0.0, 1.0).astype(np.float32)
    fade_out = np.clip((178.8 - t) / 1.2, 0.0, 1.0).astype(np.float32)
    atmosphere *= fade_in * fade_out
    atmosphere[int(178.9 * RATE):] = 0.0

    # Sidechain ducking: drop underscore further whenever voice is active
    mono_voice = voice.mean(axis=1)
    hop = RATE // 50
    blocks = np.abs(mono_voice[: (len(mono_voice) // hop) * hop]).reshape(-1, hop).max(axis=1)
    duck_blocks = np.where(blocks > 0.02, 0.42, 0.85).astype(np.float32)
    duck = np.repeat(duck_blocks, hop)
    if len(duck) < target_samples:
        duck = np.pad(duck, (0, target_samples - len(duck)), mode="edge")
    atmosphere *= duck[:target_samples]

    stereo_atmo = np.column_stack([atmosphere * 0.96, atmosphere * 1.04])
    mixed = np.clip(voice * 0.94 + stereo_atmo, -0.96, 0.96)
    pcm = np.int16(np.round(mixed * 32767.0)).astype("<i2")
    with wave.open(str(mixed_wav), "wb") as writer:
        writer.setnchannels(2)
        writer.setsampwidth(2)
        writer.setframerate(RATE)
        writer.writeframes(pcm.reshape(-1).tobytes())


def find_cjk_font() -> Path:
    candidates = [
        ROOT / ".cache" / "fonts" / "NotoSansCJKsc-Regular.otf",
        Path.home() / ".local" / "share" / "fonts" / "NotoSansCJKsc-Regular.otf",
        ROOT / "production" / "mystery-cover-template" / "NotoSerifCJKsc-Common.otf",
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise RuntimeError("No CJK font found for horizontal cover title rendering")


def build_horizontal_cover(segments_dir: Path, cover_path: Path, title_text: str = "报警的人") -> None:
    """Create the 1920x1080 split horizontal cover from real S01 (burning mansion) and S02/S11 (phone) frames."""
    left_png = cover_path.parent / "_cover_left.png"
    right_png = cover_path.parent / "_cover_right.png"
    s01 = segments_dir / "S01.mp4"
    s02 = segments_dir / "S02.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-ss", "2.2", "-i", s01, "-frames:v", "1", left_png])
    run(["ffmpeg", "-y", "-v", "error", "-ss", "2.4", "-i", s02, "-frames:v", "1", right_png])

    left = Image.open(left_png).convert("RGB").resize((1920, 1080), Image.Resampling.LANCZOS)
    right = Image.open(right_png).convert("RGB").resize((1920, 1080), Image.Resampling.LANCZOS)
    # Crop centered halves (960x1080 each) and blend across a soft 140px center gradient
    left_half = left.crop((320, 0, 1600, 1080)).resize((1040, 1080), Image.Resampling.LANCZOS)
    right_half = right.crop((320, 0, 1600, 1080)).resize((1040, 1080), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (1920, 1080), (8, 10, 14))
    canvas.paste(left_half.crop((0, 0, 960, 1080)), (0, 0))
    mask = Image.new("L", (1040, 1080), 255)
    grad = np.linspace(0, 255, 160, dtype=np.uint8)
    mask_arr = np.full((1080, 1040), 255, dtype=np.uint8)
    mask_arr[:, :160] = grad[None, :]
    mask = Image.fromarray(mask_arr, mode="L")
    canvas.paste(right_half, (880, 0), mask)

    # Bottom gradient vignette for bold title legibility
    vignette = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    v_arr = np.zeros((1080, 1920, 4), dtype=np.uint8)
    y_grad = np.clip((np.arange(1080) - 620) / 460.0, 0.0, 1.0)
    v_arr[:, :, 3] = (y_grad[:, None] * 185).astype(np.uint8)
    vignette = Image.fromarray(v_arr, mode="RGBA")
    composed = Image.alpha_composite(canvas.convert("RGBA"), vignette)

    font_path = find_cjk_font()
    title_font = ImageFont.truetype(str(font_path), 148)
    sub_font = ImageFont.truetype(str(font_path), 44)

    shadow = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    bbox = sdraw.textbbox((0, 0), title_text, font=title_font, stroke_width=10)
    tw = bbox[2] - bbox[0]
    tx = (1920 - tw) // 2
    ty = 740
    sdraw.text((tx, ty + 8), title_text, font=title_font, fill=(0, 0, 0, 220), stroke_width=14, stroke_fill=(0, 0, 0, 220))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=8))
    composed = Image.alpha_composite(composed, shadow)

    draw = ImageDraw.Draw(composed)
    draw.text((tx, ty), title_text, font=title_font, fill=(255, 204, 48, 255), stroke_width=9, stroke_fill=(12, 12, 12, 255))
    sub_text = "江南豪门双尸案 · 放火的也是他"
    sb = draw.textbbox((0, 0), sub_text, font=sub_font, stroke_width=4)
    sw = sb[2] - sb[0]
    draw.text(((1920 - sw) // 2, 932), sub_text, font=sub_font, fill=(245, 245, 245, 255), stroke_width=4, stroke_fill=(10, 10, 10, 255))

    composed.convert("RGB").save(cover_path, quality=92)
    left_png.unlink(missing_ok=True)
    right_png.unlink(missing_ok=True)


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

    for index, shot in enumerate(story["shots"], 1):
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
        grade_chain = shot_grade_and_transition(index, target)
        vf = (
            f"scale=1920:1080:flags=lanczos,fps={FPS},trim=duration={target:.6f},"
            f"setpts=PTS-STARTPTS,setsar=1,{grade_chain},format=yuv420p"
        )
        run(["ffmpeg", "-y", "-v", "error", "-threads", "2", "-i", source,
             "-vf", vf, "-map", "0:v:0", "-an", "-frames:v", frames, "-r", FPS,
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
        # Strip TTS lead-in silence first so captions never lead spoken audio by 0.3s.
        speech = segments / f"{sid}.speech.wav"
        run(["ffmpeg", "-y", "-v", "error", "-i", narration, "-vn", "-af",
             "silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB:start_silence=0.06,"
             f"atempo={speed:.6f}", "-ar", RATE, "-ac", 2, "-c:a", "pcm_s16le", speech])
        speech_seconds = duration(speech)
        max_speech_slot = target - 0.85 if sid == "S30" else target - 0.04
        if speech_seconds > max_speech_slot:
            extra = speech_seconds / max_speech_slot
            if speed * extra > 1.55 + 1e-9:
                raise RuntimeError(f"{sid}: speech cannot fit even at 1.55x")
            run(["ffmpeg", "-y", "-v", "error", "-i", speech, "-vn", "-af",
                 f"atempo={extra:.6f}", "-ar", RATE, "-ac", 2, "-c:a", "pcm_s16le", speech])
            speech_seconds = duration(speech)
            speed *= extra
        wav = segments / f"{sid}.wav"
        run(["ffmpeg", "-y", "-v", "error", "-i", speech, "-af", "apad",
             "-t", f"{target:.6f}", "-ar", RATE, "-ac", 2, "-c:a", "pcm_s16le", wav])
        segment_seconds = duration(wav)
        if abs(segment_seconds - target) > 0.02:
            raise RuntimeError(f"{sid}: narration segment is {segment_seconds:.3f}s, expected {target:.3f}s")
        audio_entries.append(f"file '{wav.resolve()}'")
        cues.append((float(shot["start"]),
                     float(shot["start"]) + min(target - 0.04, speech_seconds), shot["narration"]))
        technical.append({
            "id": sid, "target_seconds": target, "target_frames": frames,
            "source_seconds": round(source_duration, 3), "source_size": [width, height],
            "source_sha256": record["sha256"], "narration_seconds": round(raw_duration, 3),
            "narration_atempo": round(speed, 4),
        })

    video_list.write_text("\n".join(video_entries) + "\n", encoding="utf-8")
    audio_list.write_text("\n".join(audio_entries) + "\n", encoding="utf-8")
    srt.write_text("\n".join(
        f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n"
        for i, (a, b, text) in enumerate(cues, 1)
    ), encoding="utf-8")

    ass = args.work / "subtitles.ass"
    pres = story["presentation"]
    write_ass(
        ass,
        cues,
        pres.get("highlight_phrases", []),
        pres.get("retention_hooks", []),
        (pres.get("end_title", ""), pres.get("end_subtitle", ""), 174.5, 179.5)
        if pres.get("end_title") else None,
        pres.get("onscreen_label", ""),
    )

    silent = args.work / "picture-only.mp4"
    voice = args.work / "voiceover.wav"
    mixed_voice = args.work / "master-audio.wav"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", video_list,
         "-c", "copy", "-an", "-movflags", "+faststart", silent])
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", audio_list,
         "-c:a", "pcm_s16le", "-ar", RATE, "-ac", 2, voice])
    voice_seconds = duration(voice)
    if abs(voice_seconds - 180.0) > 0.02:
        run(["ffmpeg", "-y", "-v", "error", "-i", voice, "-af", "apad",
             "-t", "180.0", "-ar", RATE, "-ac", 2, "-c:a", "pcm_s16le", voice])
        voice_seconds = duration(voice)
    if abs(voice_seconds - 180.0) > 0.05:
        raise RuntimeError(f"Voice track is {voice_seconds:.3f}s; the master must be 180.000s")

    build_thriller_bed_and_mix(voice, mixed_voice)

    subtitle_filter = f"subtitles='{ffmpeg_escape(ass)}'"
    # Two-pass separate encode + stream-copy mux prevents ffmpeg 4.1 tail audio loss on runner.
    picture = args.work / "picture-subbed.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-threads", "2", "-i", silent,
         "-vf", subtitle_filter, "-an", "-t", "180", "-frames:v", 180 * FPS,
         "-r", FPS, "-vsync", "cfr", "-c:v", "libx264", "-preset", "medium", "-crf", "22",
         "-maxrate", "3200k", "-bufsize", "6400k", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", picture])
    narration_bus = args.work / "narration-bus.m4a"
    run(["ffmpeg", "-y", "-v", "error", "-i", mixed_voice, "-af", "apad", "-t", "180",
         "-c:a", "aac", "-b:a", "192k", "-ar", RATE, "-ac", 2, narration_bus])
    run(["ffmpeg", "-y", "-v", "error", "-i", picture, "-i", narration_bus,
         "-map", "0:v:0", "-map", "1:a:0", "-c", "copy", "-t", "180",
         "-movflags", "+faststart", args.output])
    print(f"PICTURE {duration(picture):.3f}s  VOICE {voice_seconds:.3f}s  MUXED {duration(args.output):.3f}s",
          flush=True)

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

    cover = args.output.parent / "江南豪门双尸案_Cover.jpg"
    build_horizontal_cover(segments, cover, pres.get("cover_text", "报警的人"))

    report = {
        "film": str(args.output),
        "duration_seconds": 180,
        "width": 1920,
        "height": 1080,
        "voice_track_seconds": round(voice_seconds, 3),
        "audio_stream_seconds": round(audio_seconds, 3),
        "fps": FPS,
        "frames": 180 * FPS,
        "audio": "shot-locked deep suspense male voiceover + original procedural thriller drone & foley (-28dB, last 1.0s silent)",
        "retention_hooks_burned": len(pres.get("retention_hooks", [])),
        "subtitle_file": str(srt),
        "shots": technical,
    }
    report_path = args.work / "technical-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("FIRST_CUT_READY", args.output, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
