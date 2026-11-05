#!/usr/bin/env python3
"""Build shot-locked New Orleans narration, matched captions and the measured final mix.

Each line has its own user-selected Arena voice clip and one subtitle cue, both attached to
one of the unchanged 29 shots. Natural pace is preserved; speech is never slowed to fill a
shot and may only be accelerated slightly when needed to stay inside its cut. Music/SFX are
original procedural WAV synthesis, unchanged from the existing production design.
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import wave
from pathlib import Path

import numpy as np

RATE = 48_000
TAIL_GUARD = 0.05      # 收尾留白，避免切点吞字
PUNCH_PAUSE = 0.45     # 关键句后的静默（加 TAIL_GUARD 约 0.5 s）
PUNCH_LINES = ("斧头不会落下", "没有人遇害", "哪首歌")
BLOCK = RATE
TARGET_RMS_DBFS = -20.0
PEAK_CEILING_DBFS = -1.5
BGM_TARGET_BELOW_VOICE_DB = -18.0
BGM_JAZZ_BELOW_VOICE_DB = -12.0   # 开场与爵士狂欢段落
JAZZ_MUSIC_BOOST_DB = 8.0         # 爵士段音乐额外抬升，形成明确的段落对比
BGM_SIDECHAIN_MAKEUP_DB = 1.5
BGM_SILENCE_LEVEL = 0.24
SFX_LEVEL = 0.50
SILENCE_THRESHOLD_DBFS = -50.0


def run(command) -> None:
    subprocess.run([str(part) for part in command], check=True)


def probe_duration(path: Path) -> float:
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)
    ], text=True).strip())


def decode_mp3(path: Path, output: Path, tempo: float) -> np.ndarray:
    output.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-v", "error", "-i", path,
        "-af", f"atempo={tempo:.8f},aresample={RATE},highpass=f=65,lowpass=f=11000",
        "-ar", RATE, "-ac", 1, "-c:a", "pcm_s16le", output,
    ])
    with wave.open(str(output), "rb") as reader:
        frames = reader.readframes(reader.getnframes())
        return np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0


def write_wave(path: Path, data: np.ndarray, channels: int = 1, rate: int = RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(data, -1.0, 1.0)
    pcm = np.int16(np.round(clipped * 32767.0)).astype("<i2")
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(pcm.reshape(-1).tobytes())


def read_wave(path: Path) -> tuple[np.ndarray, int, int]:
    with wave.open(str(path), "rb") as reader:
        rate, channels = reader.getframerate(), reader.getnchannels()
        samples = np.frombuffer(reader.readframes(reader.getnframes()), dtype="<i2")
        data = samples.astype(np.float32) / 32768.0
        return data.reshape(-1, channels), rate, channels


def visible_weight(text: str) -> int:
    return max(1, len(re.sub(r"[^\u3400-\u9fffA-Za-z0-9]", "", text)))


def energy(samples: np.ndarray, hop: int = RATE // 100) -> np.ndarray:
    if len(samples) < hop:
        return np.array([float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))])
    count = len(samples) // hop
    blocks = samples[:count * hop].reshape(count, hop)
    return np.sqrt(np.mean(np.square(blocks.astype(np.float64)), axis=1))


def trim_voice_edges(samples: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Trim only encoder silence, retaining short natural breath margins around speech."""
    if len(samples) < RATE // 5:
        raise RuntimeError("Narration clip is unexpectedly short")
    levels = energy(samples)
    if not len(levels) or float(levels.max()) < 1e-5:
        raise RuntimeError("Narration clip contains no detectable speech energy")
    threshold = max(0.0002, float(levels.max()) * 0.003)
    active = np.flatnonzero(levels > threshold)
    if not len(active):
        raise RuntimeError("Narration clip contains no detectable speech energy")
    hop = RATE // 100
    first_frame, last_frame = int(active[0]), int(active[-1])
    speech_start = first_frame * hop
    speech_end = min(len(samples), (last_frame + 1) * hop)
    keep_start = max(0, speech_start - int(0.03 * RATE))
    keep_end = min(len(samples), speech_end + int(0.08 * RATE))
    trimmed = samples[keep_start:keep_end].astype(np.float32, copy=True)
    return trimmed, (speech_start - keep_start) / RATE, (speech_end - keep_start) / RATE


def voice_tempo_factor(source_seconds: float, available_seconds: float,
                       max_speedup: float = 1.55) -> float:
    """Preserve natural pace; speed up only enough to fit, never slow down."""
    if source_seconds <= 0 or available_seconds <= 0:
        raise ValueError("Narration and available shot durations must be positive")
    factor = max(1.0, source_seconds / available_seconds)
    if factor > max_speedup + 1e-6:
        raise RuntimeError(
            f"Narration needs {factor:.3f}x speed to fit; maximum allowed is {max_speedup:.2f}x. "
            "Shorten/regenerate the line instead of slowing or cutting it."
        )
    return factor


def build_narration(story: dict, audio_dir: Path, work_dir: Path) -> tuple[np.ndarray, list[dict], dict]:
    """Build a shot-locked voice track and one precisely mapped caption for every line."""
    work_audio = work_dir / "audio"
    work_audio.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((audio_dir / "manifest.json").read_text(encoding="utf-8"))
    records = {row["id"]: row for row in manifest["clips"]}
    shots = story["shots"]
    if len(records) != len(shots):
        raise ValueError(f"Expected one narration clip for each of {len(shots)} shots; got {len(records)}")
    spec = story.get("narration_spec", {})
    voice_id = spec.get("voice_id")
    if manifest.get("voice") != voice_id or manifest.get("slowdown_allowed") is not False:
        raise ValueError("Narration voice/alignment manifest is not the selected no-slowdown version")
    max_speedup = float(spec.get("max_speedup_factor", 1.55))
    total_frames = round(float(story["target_duration"]) * RATE)
    voice = np.zeros(total_frames, dtype=np.float32)
    cues: list[dict] = []
    shot_timings: list[dict] = []

    for shot in shots:
        sid = shot["id"]
        record = records.get(sid)
        if record is None:
            raise ValueError("Missing shot narration manifest entry: " + sid)
        if (record.get("text") != shot["narration"]
                or record.get("voice_id") != voice_id
                or record.get("narration_id") != shot["narration_id"]
                or record.get("target_start") != shot["start"]
                or record.get("target_duration") != shot["duration"]
                or record.get("alignment") != "shot-locked"):
            raise ValueError("Shot-locked narration text/voice/timing mismatch: " + sid)
        source = audio_dir / record["file"]
        digest = __import__("hashlib").sha256(source.read_bytes()).hexdigest()
        if record.get("sha256") != digest:
            raise ValueError("Narration SHA-256 mismatch: " + sid)

        shot_start = float(shot["start"])
        shot_duration = float(shot["duration"])
        shot_end = shot_start + shot_duration
        # Speech stops just before the cut; the closing shot also leaves the brief's final
        # second and a half for the last hanging note before the picture fades.
        # The brief asks for a ~0.5 s beat after three signature lines (斧头不会落下 / 没有人遇害 /
        # 你放哪首歌). The pause is made by pulling the line slightly earlier so silence runs to the
        # cut - it never truncates a syllable, it only moves the line.
        # 关键句自动识别：「斧头不会落下」「没有人遇害」「你放哪首歌」之后各留 0.5 s 静默。
        # 不依赖 manifest 的手工标记（同步 manifest 时会丢），只认旁白文本本身。
        punch = any(key in shot["narration"] for key in PUNCH_LINES) or bool(record.get("punch_pause"))
        lead_out = (TAIL_GUARD + PUNCH_PAUSE) if punch else 0.08
        max_speech_end = min(shot_end - lead_out, float(story["target_duration"]) - 1.6)
        available = max_speech_end - shot_start
        if available <= 0:
            raise ValueError("No safe speech window remains in " + sid)

        raw_duration = probe_duration(source)
        decoded_path = work_audio / f"{sid}-retimed.wav"
        natural_samples = decode_mp3(source, decoded_path, 1.0)
        natural_trimmed, natural_onset, natural_offset = trim_voice_edges(natural_samples)
        natural_clip_seconds = len(natural_trimmed) / RATE
        natural_speech_seconds = natural_offset - natural_onset
        tempo = voice_tempo_factor(natural_clip_seconds, available, max_speedup)
        samples = natural_samples if tempo == 1.0 else decode_mp3(source, decoded_path, tempo)
        trimmed, speech_onset, speech_offset = trim_voice_edges(samples)

        # Re-run at a minimally faster rate for small filter/encoder timing differences;
        # never truncate syllables and never slow down to pad the rest of the shot.
        if len(trimmed) > round(available * RATE):
            correction = (len(trimmed) / (available * RATE)) * 1.005
            tempo = voice_tempo_factor(tempo * correction, 1.0, max_speedup)
            samples = decode_mp3(source, decoded_path, tempo)
            trimmed, speech_onset, speech_offset = trim_voice_edges(samples)
        # Sub-second rounding may still leave a few milliseconds over. Converge instead of
        # failing the whole render: shrink the speed slightly and retry, up to the same hard cap.
        for _ in range(6):
            if len(trimmed) <= round(available * RATE):
                break
            correction = (len(trimmed) / (available * RATE)) * 1.004
            tempo = voice_tempo_factor(tempo * correction, 1.0, max_speedup)
            samples = decode_mp3(source, decoded_path, tempo)
            trimmed, speech_onset, speech_offset = trim_voice_edges(samples)
        if len(trimmed) > round(available * RATE):
            raise RuntimeError(f"{sid}: complete narration still exceeds its shot after safe speed-up")

        clip_start = round(shot_start * RATE)
        clip_end = clip_start + len(trimmed)
        allowed_end = round(max_speech_end * RATE)
        if clip_end > allowed_end:
            # Only sub-sample rounding may reach this path; do not discard spoken audio.
            raise RuntimeError(f"{sid}: narration crosses its shot boundary")
        fade = min(int(0.005 * RATE), len(trimmed) // 2)
        if fade:
            trimmed[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)
            trimmed[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
        voice[clip_start:clip_end] += trimmed

        caption_start = shot_start + speech_onset
        caption_end = shot_start + speech_offset
        if caption_end <= caption_start:
            raise RuntimeError(f"{sid}: narration activity window is empty")
        cue = {
            "shot_id": sid,
            "narration_id": shot["narration_id"],
            "start": round(caption_start, 3),
            "end": round(caption_end, 3),
            "text": shot["narration"],
        }
        if cues and cue["start"] < cues[-1]["end"] - 0.001:
            raise RuntimeError(f"{sid}: shot-locked subtitle overlaps the preceding shot")
        cues.append(cue)
        characters = visible_weight(shot["narration"])
        shot_timings.append({
            "id": sid,
            "narration_id": shot["narration_id"],
            "text": shot["narration"],
            "start": shot_start,
            "duration": shot_duration,
            "source_seconds": round(raw_duration, 3),
            "natural_clip_seconds": round(natural_clip_seconds, 3),
            "natural_speech_seconds": round(natural_speech_seconds, 3),
            "spoken_seconds": round(speech_offset - speech_onset, 3),
            "tempo_factor": round(tempo, 4),
            "speech_start": round(caption_start, 3),
            "speech_end": round(caption_end, 3),
            "characters": characters,
            "target_chars_per_second": round(characters / shot_duration, 3),
        })

    if len(voice) != total_frames:
        raise RuntimeError(f"Narration timeline has {len(voice)/RATE:.4f}s, expected {story['target_duration']}s")
    voice_path = work_audio / "voiceover.wav"
    write_wave(voice_path, voice, channels=1)

    chapter_timings = []
    for chapter in story["chapters"]:
        members = [row for row in shot_timings if row["narration_id"] == chapter["id"]]
        if not members:
            raise ValueError("Narration chapter has no shot-locked audio: " + chapter["id"])
        chapter_timings.append({
            "id": chapter["id"],
            "start": float(chapter["start"]),
            "duration": float(chapter["duration"]),
            "characters": visible_weight(chapter["text"]),
            "target_chars_per_second": round(visible_weight(chapter["text"]) / chapter["duration"], 3),
            "source_seconds": round(sum(row["source_seconds"] for row in members), 3),
            "tempo_factor": max(row["tempo_factor"] for row in members),
            "inserted_pause_seconds": 0.0,
            "inserted_pause_at_chapter_seconds": None,
            "speech_seconds": round(sum(row["spoken_seconds"] for row in members), 3),
            "shot_ids": [row["id"] for row in members],
        })
    return voice, cues, {
        "voice_id": voice_id,
        "alignment": "one-clip-one-shot-one-caption",
        "slowdown_allowed": False,
        "max_speedup_factor": max_speedup,
        "shots": shot_timings,
        "chapters": chapter_timings,
        "output": str(voice_path),
        "duration_seconds": float(story["target_duration"]),
    }


def _event_envelope(t: np.ndarray, at: float, duration: float, decay: float = 2.0) -> np.ndarray:
    delta = t - at
    safe_delta = np.clip(delta, 0.0, duration)
    return np.where((delta >= 0) & (delta <= duration), np.exp(-safe_delta * decay), 0.0)


def _brass(t: np.ndarray, freq: float, phase: float = 0.0) -> np.ndarray:
    """A cheap but bright brass voice: stacked odd harmonics with a slow vibrato."""
    vibrato = 1.0 + 0.0045 * np.sin(2 * np.pi * 5.1 * t + phase)
    tone = (0.62 * np.sin(2 * np.pi * freq * vibrato * t + phase)
            + 0.24 * np.sin(2 * np.pi * freq * 2.0 * vibrato * t + phase * 1.7)
            + 0.11 * np.sin(2 * np.pi * freq * 3.0 * vibrato * t + phase * 2.3)
            + 0.05 * np.sin(2 * np.pi * freq * 4.0 * vibrato * t + phase * 3.1))
    return tone


def _reed(t: np.ndarray, freq: float, phase: float = 0.0) -> np.ndarray:
    """Clarinet-ish: odd harmonics with a breathy edge."""
    return (0.60 * np.sin(2 * np.pi * freq * t + phase)
            + 0.20 * np.sin(2 * np.pi * freq * 3.0 * t + phase * 1.4)
            + 0.10 * np.sin(2 * np.pi * freq * 5.0 * t + phase * 2.1)
            + 0.04 * np.sin(2 * np.pi * freq * 7.0 * t + phase * 2.9))


def _pluck(t: np.ndarray, freq: float, decay: float) -> np.ndarray:
    """Banjo / upright-piano style pluck: fast attack, quick exponential decay."""
    env = np.exp(-np.clip(t, 0, None) * decay)
    return env * (0.55 * np.sin(2 * np.pi * freq * t)
                  + 0.22 * np.sin(2 * np.pi * freq * 2.01 * t + 0.3)
                  + 0.10 * np.sin(2 * np.pi * freq * 3.02 * t + 0.7))


def synthesize_beds(work_dir: Path, story: dict) -> tuple[np.ndarray, np.ndarray]:
    """原创程序合成配乐与音效（无任何授权音频）。

    三条音景线跟随三色调：夏夜恐惧线用低音大提琴、低频心跳与孤单萨克斯；
    追查线（专案组/罚单/电话）用冷色电子脉冲、拨号音与打字机；结尾暖金线
    用舒缓萨克斯独奏收尾。音效全部按镜头时间点合成（风、蒸汽、警笛、水花、
    电话铃、翻纸、狗叫等），最后 0.9 秒淡出至静音。
    """
    work_audio = work_dir / "audio"
    work_audio.mkdir(parents=True, exist_ok=True)
    music_path = work_audio / "original-sonofsam-score.wav"
    sfx_path = work_audio / "procedural-sfx.wav"
    duration = float(story["target_duration"])
    total = int(round(duration * RATE))
    rng = np.random.default_rng(19770810)
    wind_state = 0.0
    rumble_state = 0.0
    chapter_edges = np.array([float(c["start"]) for c in story["chapters"]] + [duration])
    tones = [c.get("tone", "night") for c in story["chapters"]]
    sections = len(story["chapters"])
    # 开场钩子（N1）与结尾（N9）用暖金萨克斯，声音略抬；追查线（N4、N6）压得更冷更轻。
    warm_idx = {i for i, tone in enumerate(tones) if tone == "gold"} | {0}
    chase_idx = {i for i, tone in enumerate(tones) if tone == "chase"}
    levels = np.array([1.45, 0.62, 0.66, 0.60, 0.66, 0.58, 0.64, 0.68, 1.35])[:sections]

    def section_index(t: np.ndarray) -> np.ndarray:
        return np.clip(np.searchsorted(chapter_edges, t, side="right") - 1, 0, sections - 1)

    def gate(t: np.ndarray, lo: float, hi: float) -> np.ndarray:
        return ((t >= lo) & (t < hi)).astype(np.float64)

    # 萨克斯旋律：开场与结尾各一条慢句（A 小调五声音阶），每音 0.9–1.4 秒。
    sax_line = [220.00, 261.63, 293.66, 329.63, 261.63, 220.00, 196.00, 220.00,
                246.94, 293.66, 329.63, 392.00, 329.63, 293.66, 261.63, 220.00]
    sax_step = 1.05
    # 冷色追查脉冲：每 1.1 秒一次的短促低音 + 偶发高频提示音
    pulse_step = 1.1

    def bucket(events, tail=1.3):
        buckets = {}
        for event in events:
            at = float(event[0])
            first = int((at * RATE) // BLOCK)
            last = int(((at + tail) * RATE) // BLOCK)
            for block_index in range(first, last + 1):
                buckets.setdefault(block_index, []).append(event)
        return buckets

    # 萨克斯音符事件（只落在暖金段落）
    sax_events = []
    for section in sorted(warm_idx):
        lo = chapter_edges[section]
        hi = chapter_edges[section + 1] if section + 1 < len(chapter_edges) else duration
        t0 = lo + 0.4
        index = 0
        while t0 < hi - 0.5:
            sax_events.append((t0, sax_line[index % len(sax_line)]))
            t0 += sax_step * (1 + (index % 3 == 2))
            index += 1
    sax_buckets = bucket(sax_events, tail=2.6)

    with wave.open(str(music_path), "wb") as music_file, wave.open(str(sfx_path), "wb") as sfx_file:
        for writer in (music_file, sfx_file):
            writer.setnchannels(2)
            writer.setsampwidth(2)
            writer.setframerate(RATE)
        for offset in range(0, total, BLOCK):
            count = min(BLOCK, total - offset)
            t = (offset + np.arange(count, dtype=np.float64)) / RATE
            block_index = offset // BLOCK
            section = section_index(t)
            is_warm = np.isin(section, list(warm_idx))
            is_chase = np.isin(section, list(chase_idx))
            fade = np.minimum(np.clip(t / 1.2, 0, 1), np.clip((duration - t) / 2.2, 0, 1))

            # ---- 夏夜恐惧床：低音大提琴 + 亚低音 + 心跳 ---------------------------------
            lfo = 0.72 + 0.22 * np.sin(2 * np.pi * 0.021 * t)
            cello = (0.088 * np.sin(2 * np.pi * 55.00 * t)
                     + 0.040 * np.sin(2 * np.pi * 82.41 * t + 0.35)
                     + 0.019 * np.sin(2 * np.pi * 110.00 * t + 0.90)) * lfo
            sub = 0.048 * np.sin(2 * np.pi * 36.71 * t)
            drone = (0.042 * np.sin(2 * np.pi * 73.42 * t)
                     + 0.024 * np.sin(2 * np.pi * 146.83 * t + 0.4)
                     * (0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t)))
            heartbeat_age = np.mod(np.maximum(t - 30.0, 0.0), 0.92)
            heartbeat = (0.055 * np.sin(2 * np.pi * 46.0 * t) * np.exp(-heartbeat_age * 14.0)
                         + 0.028 * np.sin(2 * np.pi * 46.0 * t)
                         * np.exp(-np.mod(heartbeat_age + 0.72, 0.92) * 16.0))
            # 孤单萨克斯（恐惧线里的远奏，恐惧线也用萨克斯母题）
            reed_step = 2.6
            reed_age = np.mod(np.maximum(t - 10.0, 0.0), reed_step)
            reed_index = np.mod(np.floor(np.maximum(t - 10.0, 0.0) / reed_step).astype(int), 8)
            reed_notes = np.array([220.00, 196.00, 174.61, 196.00, 220.00, 261.63, 246.94, 220.00])
            lonely_sax = 0.034 * _reed(t, reed_notes[reed_index] / 2.0) * np.exp(-reed_age * 1.6)
            # 追查线冷脉冲：低音"嘟"与高频"叮"
            pulse_age = np.mod(np.maximum(t - 60.0, 0.0), pulse_step)
            cold_pulse = 0.030 * np.sin(2 * np.pi * 110.0 * t) * np.exp(-pulse_age * 9.0)
            cold_ding = (0.016 * np.sin(2 * np.pi * 1567.98 * t)
                         * np.exp(-np.mod(np.maximum(t - 60.0, 0.0) + 0.55, pulse_step) * 12.0))
            # 结尾暖金长音
            descent = np.clip((t - 168.0) / 11.0, 0.0, 1.0)
            warm_chord = gate(t, 168.0, 179.5) * 0.040 * (
                np.sin(2 * np.pi * 220.0 * (1.0 - 0.06 * descent) * t)
                + 0.7 * np.sin(2 * np.pi * 277.18 * t + 0.3)
                + 0.5 * np.sin(2 * np.pi * 329.63 * t + 0.7))

            night_bed = (cello * 0.9 + sub + drone * 0.4
                         + gate(t, 30.0, 60.0) * heartbeat
                         + gate(t, 85.0, 108.0) * heartbeat * 1.2
                         + gate(t, 108.0, 130.0) * heartbeat
                         + gate(t, 150.0, 168.0) * heartbeat * 0.8
                         + lonely_sax * gate(t, 10.0, 168.0))
            chase_bed = cold_pulse + cold_ding * 0.8 + drone * 0.25
            score = np.where(is_warm, night_bed * 0.5 + warm_chord, night_bed)
            score = np.where(is_chase, chase_bed, score)
            # 暖金段落的萨克斯独奏主旋律
            for at, note in sax_buckets.get(block_index, ()):
                local = t - at
                env = np.where(local >= 0, np.exp(-np.clip(local, 0, None) * 1.35)
                               * np.minimum(local / 0.06, 1.0), 0.0)
                vib = 1.0 + 0.006 * np.sin(2 * np.pi * 5.2 * local)
                score += np.where(is_warm, 1.0, 0.0) * 0.075 * env * _reed(local, note * vib)
            section_level = levels[section]
            score = np.tanh(score * 1.25) * section_level * fade
            pan = 0.06 * np.sin(2 * np.pi * 0.013 * t)
            music_pcm = np.clip(np.column_stack((score * (1.0 - pan), score * (1.0 + pan))) * 32767,
                                -32768, 32767).astype("<i2")
            music_file.writeframes(music_pcm.tobytes())

            # ---- 音效床 ---------------------------------------------------------------
            raw_wind = rng.normal(0.0, 1.0, count)
            raw_rumble = rng.normal(0.0, 1.0, count)
            wind = np.empty(count, dtype=np.float64)
            rumble = np.empty(count, dtype=np.float64)
            state, rstate = wind_state, rumble_state
            for i, value in enumerate(raw_wind):
                state = 0.9950 * state + 0.0050 * value
                wind[i] = state
            for i, value in enumerate(raw_rumble):
                rstate = 0.986 * rstate + 0.014 * value
                rumble[i] = rstate
            wind_state, rumble_state = state, rstate

            sfx = wind * 0.026 * fade
            noise = rng.normal(0.0, 1.0, count)
            # 井盖蒸汽嘶嘶（开头与罚单线）
            sfx += gate(t, 0.0, 12.0) * 0.014 * noise * (0.6 + 0.4 * np.sin(2 * np.pi * 2.3 * t))
            sfx += gate(t, 85.0, 108.0) * 0.008 * noise
            # 远处警笛（开头、案发后、抓捕前）
            for at in (1.5, 31.0, 60.5, 150.5):
                env = _event_envelope(t, at, 2.6, 1.6)
                f = 720.0 + 130.0 * np.sin(2 * np.pi * 0.9 * (t - at))
                sfx += env * 0.020 * np.sin(2 * np.pi * f * np.maximum(t - at, 0.0))
            # 孩子笑声 + 水花（消防栓，10–17 秒）
            sfx += gate(t, 10.0, 17.0) * 0.012 * noise * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 9.0 * t)))
            for i, at in enumerate(np.arange(10.5, 16.5, 0.7)):
                sfx += _event_envelope(t, at, 0.12, 18.0) * 0.018 * _pluck(
                    np.maximum(t - at, 0.0), 1200.0 + 500.0 * (i % 3), 14.0)
            # 收音机摇滚（车内，17–24 秒）：短促吉他拨奏
            for i, at in enumerate(np.arange(17.2, 24.0, 0.9)):
                note = [329.63, 392.00, 440.00, 329.63][i % 4]
                sfx += gate(t, 17.0, 24.5) * _event_envelope(t, at, 0.30, 6.0) * 0.020 * _pluck(
                    np.maximum(t - at, 0.0), note, 5.0)
            # 蝉鸣（17–30 秒）
            sfx += gate(t, 17.0, 30.0) * 0.008 * np.sin(2 * np.pi * 4200.0 * t) * (
                0.5 + 0.5 * np.sin(2 * np.pi * 13.0 * t)) * noise * 0.4
            # 垃圾桶盖空响（24–30 秒，切黑骤停）
            for at, amp in ((26.2, 0.060), (28.0, 0.042), (29.3, 0.030)):
                env = _event_envelope(t, at, 0.5, 3.5)
                sfx += env * amp * (np.sin(2 * np.pi * 340.0 * (t - at)) * 0.5 + noise)
            # 理发店：剪刀 + 吹风机（42–49 秒）
            for at in np.arange(42.4, 48.6, 0.55):
                sfx += _event_envelope(t, at, 0.09, 30.0) * 0.030 * noise
            sfx += gate(t, 42.0, 49.0) * 0.010 * noise
            # 迪斯科鼓点（49–55 秒）
            for bar in range(12):
                at = 49.2 + bar * 0.5
                sfx += _event_envelope(t, at, 0.12, 14.0) * 0.045 * np.sin(2 * np.pi * 60.0 * (t - at))
                sfx += _event_envelope(t, at + 0.25, 0.06, 24.0) * 0.016 * noise
            # 报纸抖动（55–60 秒）
            for at, amp in ((55.4, 0.030), (56.3, 0.022), (57.2, 0.026), (58.6, 0.020)):
                sfx += _event_envelope(t, at, 0.30, 8.0) * amp * noise
            # 现场拾信：纸张声 + 低语（60–67 秒）
            sfx += _event_envelope(t, 61.0, 0.3, 10.0) * 0.035 * noise
            sfx += gate(t, 60.0, 67.0) * 0.006 * noise
            # 专案组：电话铃 + 打字机（67–74 秒）
            for at in (67.4, 69.8, 72.2):
                for k in range(2):
                    ring_at = at + k * 0.42
                    env = _event_envelope(t, ring_at, 0.18, 8.0)
                    sfx += env * 0.028 * (np.sin(2 * np.pi * 1400.0 * (t - ring_at))
                                          + 0.7 * np.sin(2 * np.pi * 1760.0 * (t - ring_at)))
            for at in np.arange(67.8, 74.0, 0.16):
                sfx += _event_envelope(t, at, 0.05, 26.0) * 0.014 * noise
            # 拆信 + 打字机戛然而止（74–80 秒）
            sfx += _event_envelope(t, 74.6, 0.28, 18.0) * 0.038 * noise
            for at in np.arange(74.8, 76.4, 0.16):
                sfx += _event_envelope(t, at, 0.05, 26.0) * 0.016 * noise
            # 信纸特写：低频嗡鸣 + 钟摆滴答（80–85 秒）
            sfx += gate(t, 80.0, 85.0) * 0.020 * np.sin(2 * np.pi * 55.0 * t)
            tick = gate(t, 80.0, 85.0) * ((np.mod(t, 1.0) < 0.04) | ((np.mod(t, 1.0) > 0.5) & (np.mod(t, 1.0) < 0.54)))
            sfx += tick * 0.022 * noise
            # 夜风 + 远处警哨（85–91 秒）
            for at in (86.5, 89.5):
                env = _event_envelope(t, at, 1.2, 2.2)
                sfx += env * 0.016 * np.sin(2 * np.pi * 880.0 * (t - at))
            # 笔写字 + 风吹纸（91–97 秒）
            for at in np.arange(91.3, 96.8, 0.5):
                sfx += _event_envelope(t, at, 0.16, 12.0) * 0.020 * noise
            sfx += _event_envelope(t, 93.5, 0.4, 6.0) * 0.018 * noise
            # 急促脚步 + 车门关闭（97–103 秒）
            for at in (97.4, 97.9, 98.4, 99.0, 99.6, 100.2, 101.5):
                sfx += _event_envelope(t, at, 0.08, 22.0) * 0.030 * (
                    0.5 * np.sin(2 * np.pi * 180.0 * (t - at)) + 0.5 * noise)
            sfx += _event_envelope(t, 102.6, 0.22, 12.0) * 0.050 * (
                np.sin(2 * np.pi * 90.0 * (t - 102.6)) + 0.4 * noise)
            # 狗轻声呜咽（103–108 秒）
            yelp = _event_envelope(t, 104.2, 0.7, 4.0)
            sfx += yelp * 0.030 * np.sin(2 * np.pi * (620.0 - 160.0 * (t - 104.2)) * np.maximum(t - 104.2, 0.0))
            # 翻罚单纸页 + 钟摆（108–114 秒）
            for at in np.arange(108.4, 113.6, 0.35):
                sfx += _event_envelope(t, at, 0.12, 12.0) * 0.022 * noise
            tick = gate(t, 108.0, 120.0) * ((np.mod(t, 1.0) < 0.04) | ((np.mod(t, 1.0) > 0.5) & (np.mod(t, 1.0) < 0.54)))
            sfx += tick * 0.020 * noise
            # 『叮』一声 + 心跳加速（114–120 秒）
            sfx += _event_envelope(t, 114.6, 0.8, 4.0) * 0.045 * np.sin(2 * np.pi * 1318.5 * (t - 114.6))
            hb_age = np.mod(np.maximum(t - 114.0, 0.0), 0.55)
            sfx += gate(t, 114.0, 120.0) * 0.040 * np.sin(2 * np.pi * 48.0 * t) * np.exp(-hb_age * 16.0)
            # 拨号声（120–125 秒）：拨盘咔哒
            for at in (120.4, 120.9, 121.5, 122.2, 122.9, 123.7, 124.4):
                sfx += _event_envelope(t, at, 0.05, 26.0) * 0.026 * noise
            sfx += gate(t, 120.0, 125.0) * 0.006 * np.sin(2 * np.pi * 350.0 * t) * noise
            # 电话铃 + 呼吸（125–130 秒）
            for at in (125.3, 126.5, 127.7, 128.9):
                env = _event_envelope(t, at, 0.30, 6.0)
                sfx += env * 0.030 * (np.sin(2 * np.pi * 1200.0 * (t - at))
                                      + 0.7 * np.sin(2 * np.pi * 1500.0 * (t - at)))
            # 夜风 + 远处狗吠（130–137 秒）
            for at, amp in ((131.2, 0.030), (134.6, 0.024)):
                env = _event_envelope(t, at, 0.5, 4.0)
                sfx += env * amp * np.sin(2 * np.pi * (520.0 - 120.0 * (t - at)) * np.maximum(t - at, 0.0))
            # 狗喘息 + 篱笆风吹（137–144 秒）
            sfx += gate(t, 137.0, 144.0) * 0.010 * noise * (0.5 + 0.5 * np.sin(2 * np.pi * 3.4 * t))
            sfx += _event_envelope(t, 139.8, 0.5, 3.0) * 0.020 * noise
            # 钟摆 + 压低交谈（144–150 秒）
            tick = gate(t, 144.0, 150.0) * ((np.mod(t, 1.0) < 0.04) | ((np.mod(t, 1.0) > 0.5) & (np.mod(t, 1.0) < 0.54)))
            sfx += tick * 0.022 * noise
            sfx += gate(t, 144.0, 150.0) * 0.007 * rumble
            # 脚步 + 对讲机低声（150–156 秒），156 秒静音一拍后心跳（156–162 秒）
            for at in np.arange(150.3, 155.5, 0.62):
                sfx += _event_envelope(t, at, 0.08, 22.0) * 0.024 * noise
            sfx += gate(t, 150.0, 156.0) * 0.005 * noise
            hb_age = np.mod(np.maximum(t - 156.2, 0.0), 0.8)
            sfx += gate(t, 156.0, 162.0) * 0.050 * np.sin(2 * np.pi * 46.0 * t) * np.exp(-hb_age * 15.0)
            # 警灯嗡鸣 + 远处人群喧哗（162–168 秒）
            sfx += gate(t, 162.0, 168.0) * 0.012 * np.sin(2 * np.pi * 100.0 * t)
            sfx += gate(t, 165.0, 168.0) * 0.010 * noise * (0.5 + 0.5 * np.sin(2 * np.pi * 1.1 * t))
            # 欢呼（168–174 秒）
            sfx += gate(t, 168.0, 174.0) * 0.014 * noise * (0.5 + 0.5 * np.sin(2 * np.pi * 2.2 * t))
            for i, at in enumerate(np.arange(168.4, 173.5, 0.8)):
                sfx += _event_envelope(t, at, 0.3, 5.0) * 0.016 * _pluck(
                    np.maximum(t - at, 0.0), 523.25 + 100.0 * (i % 3), 6.0)
            # 最后一秒静音（收尾萨克斯在音乐床里，音效 179.1 秒后淡尽）
            sfx *= np.clip((179.1 - t) / 0.7, 0, 1)
            stereo = np.column_stack((sfx, sfx * (1.0 + 0.03 * np.sin(2 * np.pi * 0.05 * t))))
            sfx_file.writeframes(np.clip(stereo * 32767, -32768, 32767).astype("<i2").tobytes())

    music, _, _ = read_wave(music_path)
    effects, _, _ = read_wave(sfx_path)
    return music.astype(np.float32), effects.astype(np.float32)


def dbfs(value: float) -> float:
    if value <= 1e-12:
        return -120.0
    return round(20.0 * math.log10(value), 2)


def build_soundtrack(story: dict, audio_dir: Path, work_dir: Path) -> tuple[Path, dict, list[dict]]:
    voice, cues, narration_report = build_narration(story, audio_dir, work_dir)
    music, effects = synthesize_beds(work_dir, story)
    if music.ndim != 2:
        music = music.reshape(-1, 2)
    voice_stereo = np.repeat(voice[:, None], 2, axis=1)

    # Measure each 10ms speech/music block and ride the score to a real -18dB-under-voice target.
    hop = RATE // 100
    usable = min(len(voice), len(music)) // hop * hop
    voice_blocks = voice[:usable].reshape(-1, hop)
    music_blocks = music[:usable].reshape(-1, hop, 2)
    voice_levels = np.sqrt(np.mean(np.square(voice_blocks.astype(np.float64)), axis=1))
    music_levels = np.sqrt(np.mean(np.square(music_blocks.astype(np.float64)), axis=(1, 2)))
    # 分档：开场钩子（S01-S02）与暖金结尾（S29-S30）按简报抬到 -12 dB，其余 -18 dB，
    # 否则全片旁白不断，自动压音会让每一段听起来一样响，结尾的暖金就没了。
    loud_windows = []
    cursor = 0.0
    for shot in story["shots"]:
        start = float(shot["start"]); end = start + float(shot["duration"])
        if shot["id"] in {"S01", "S02"} or shot.get("style_variant") == "gold":
            loud_windows.append((start, end))
    block_time = (np.arange(len(voice_levels)) + 0.5) * hop / RATE
    is_loud = np.zeros(len(voice_levels), dtype=bool)
    for start, end in loud_windows:
        is_loud |= (block_time >= start) & (block_time < end)
    below_db = np.where(is_loud, BGM_JAZZ_BELOW_VOICE_DB, BGM_TARGET_BELOW_VOICE_DB)
    target_ratio = 10 ** ((below_db + BGM_SIDECHAIN_MAKEUP_DB) / 20.0)
    # 逐块算完再按段统一：同一段落里保持自然的乐句起伏，段落之间才是硬性 -18 / -12 dB 差。
    raw_gain = (voice_levels * target_ratio) / np.maximum(music_levels, 1e-5)
    segment_ids = np.zeros(len(raw_gain), dtype=np.int32)
    for index, (start, end) in enumerate(loud_windows):
        segment_ids[(block_time >= start) & (block_time < end)] = index + 1
    # 分段取中位增益：段内保留律动，段间保持目标响度差。
    for segment in np.unique(segment_ids):
        mask = segment_ids == segment
        if mask.sum() < 3:
            continue
        raw_gain[mask] = np.median(raw_gain[mask])
    active_voice = voice_levels > 0.003
    desired_gain = np.where(active_voice, np.clip(raw_gain, 0.015, 0.85), BGM_SILENCE_LEVEL)
    # Fast enough for narration onset, slow enough not to pump on syllables.
    attack = math.exp(-1.0 / (100.0 * 0.025))
    release = math.exp(-1.0 / (100.0 * 0.12))
    smooth_gain = np.empty_like(desired_gain)
    state = BGM_SILENCE_LEVEL
    for i, value in enumerate(desired_gain):
        coeff = attack if value < state else release
        state = coeff * state + (1.0 - coeff) * value
        smooth_gain[i] = state
    # 暖金段落再抬 JAZZ_MUSIC_BOOST_DB：结尾高光，音乐必须顶上来。
    jazz_mask = np.zeros(len(smooth_gain), dtype=bool)
    for start, end in loud_windows:
        jazz_mask |= (block_time >= start) & (block_time < end)
    smooth_gain = np.where(jazz_mask, smooth_gain * (10 ** (JAZZ_MUSIC_BOOST_DB / 20.0)), smooth_gain)
    per_sample_gain = np.repeat(smooth_gain.astype(np.float32), hop)
    if len(per_sample_gain) < len(voice):
        per_sample_gain = np.pad(per_sample_gain, (0, len(voice) - len(per_sample_gain)),
                                 constant_values=BGM_SILENCE_LEVEL)
    music_mix = music * per_sample_gain[:len(voice), None]
    mix = voice_stereo + music_mix + effects * SFX_LEVEL

    # The brief asks for the last note to hang, then silence: ease out over the final 0.8 s.
    fade_start = int(178.20 * RATE)
    fade_end = int(179.0 * RATE)
    mix[fade_start:fade_end] *= np.linspace(1.0, 0.0, max(1, fade_end-fade_start), dtype=np.float32)[:, None]
    mix[int(179.0 * RATE):] = 0.0

    rms = float(np.sqrt(np.mean(np.square(mix.astype(np.float64)))))
    gain = 10 ** ((TARGET_RMS_DBFS - dbfs(rms)) / 20.0)
    peak_abs = float(np.abs(mix).max())
    peak_gain = 10 ** ((PEAK_CEILING_DBFS - dbfs(peak_abs)) / 20.0)
    gain = min(gain, peak_gain, 10.0)
    mix *= gain
    if np.abs(mix).max() > 10 ** (PEAK_CEILING_DBFS / 20.0):
        mix *= (10 ** (PEAK_CEILING_DBFS / 20.0) / float(np.abs(mix).max()))

    output = work_dir / "audio" / "final-mix.wav"
    write_wave(output, mix, channels=2)
    final_rms = float(np.sqrt(np.mean(np.square(mix.astype(np.float64)))))
    final_peak = float(np.abs(mix).max())
    mono_mix = mix.mean(axis=1)
    windows = [mono_mix[i:i+RATE] for i in range(0, len(mono_mix), RATE) if len(mono_mix[i:i+RATE])]
    silent = sum(float(np.sqrt(np.mean(w.astype(np.float64)**2))) < 10**(SILENCE_THRESHOLD_DBFS/20) for w in windows)
    report = {
        "duration_seconds": round(len(mix) / RATE, 3),
        "sample_rate": RATE,
        "channels": 2,
        "rms_dbfs": dbfs(final_rms),
        "peak_dbfs": dbfs(final_peak),
        "silent_windows": int(silent),
        "window_count": len(windows),
        "silent_fraction": round(silent / max(1, len(windows)), 4),
        "target_rms_dbfs": TARGET_RMS_DBFS,
        "peak_ceiling_dbfs": PEAK_CEILING_DBFS,
        "bgm_under_voice_target_db": BGM_TARGET_BELOW_VOICE_DB,
        "bgm_warm_under_voice_target_db": BGM_JAZZ_BELOW_VOICE_DB,
        "bgm_loud_windows": loud_windows,
        "bgm_sidechain_makeup_db": BGM_SIDECHAIN_MAKEUP_DB,
        "bgm_under_voice_measured_db": dbfs(float(np.median(
            (music_levels[active_voice] * smooth_gain[active_voice]) / np.maximum(voice_levels[active_voice], 1e-6)
        ))) if np.any(active_voice) else None,
        "bgm_silence_gain": BGM_SILENCE_LEVEL,
        "sfx_level": SFX_LEVEL,
        "narration": narration_report,
        "music_file": "original-sonofsam-score.wav",
        "sfx_file": "procedural-sfx.wav",
        "output": str(output),
    }
    if report["duration_seconds"] != 180.0:
        raise RuntimeError("Mixed audio is not exactly 180 seconds")
    if report["rms_dbfs"] < -30 or report["peak_dbfs"] > -1.4:
        raise RuntimeError("Final audio failed measured loudness/peak gates: " + json.dumps(report, ensure_ascii=False))
    (work_dir / "audio" / "mix-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                                              encoding="utf-8")
    return output, report, cues
