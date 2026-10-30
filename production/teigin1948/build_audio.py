#!/usr/bin/env python3
"""Build shot-locked Teigin narration, matched captions and the measured final mix.

Each line has its own selected Arena voice clip and one subtitle cue, locked to one of the
29 visual shots. Audio is fit to the available shot window with modest tempo adjustment only;
full sentences are preserved, speech is not cut, and coverage is checked so no shot ends with
a long narration gap. Music/SFX are original procedural WAV synthesis.
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
BLOCK = RATE
TARGET_RMS_DBFS = -20.0
PEAK_CEILING_DBFS = -1.5
BGM_TARGET_BELOW_VOICE_DB = -18.0
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
                       max_speedup: float = 1.35, min_tempo: float = 0.80) -> float:
    """Fit the complete line to its shot, permitting only modest, natural time adjustment."""
    if source_seconds <= 0 or available_seconds <= 0:
        raise ValueError("Narration and available shot durations must be positive")
    factor = source_seconds / available_seconds
    if factor > max_speedup + 1e-6:
        raise RuntimeError(
            f"Narration needs {factor:.3f}x speed to fit; maximum allowed is {max_speedup:.2f}x. "
            "Shorten/regenerate the line instead of cutting syllables."
        )
    if factor < min_tempo - 1e-6:
        raise RuntimeError(
            f"Narration occupies only {factor:.1%} of its shot; modest time expansion bottoms at "
            f"{min_tempo:.2f}x. Add meaningful copy instead of leaving a long silent tail."
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
    if (manifest.get("voice") != voice_id
            or manifest.get("slowdown_allowed") is not bool(spec.get("slowdown_allowed", False))):
        raise ValueError("Narration voice/alignment/tempo manifest does not match the approved shot-locked version")
    max_speedup = float(spec.get("max_speedup_factor", 1.35))
    min_tempo = float(spec.get("min_tempo_factor", 0.80))
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
        # Speech stops just before the cut. S29 additionally honors the required final
        # second of silence while the animated end card remains on screen.
        max_speech_end = min(shot_end - 0.08, float(story["target_duration"]) - 1.0)
        available = max_speech_end - shot_start
        if available <= 0:
            raise ValueError("No safe speech window remains in " + sid)

        raw_duration = probe_duration(source)
        decoded_path = work_audio / f"{sid}-retimed.wav"
        natural_samples = decode_mp3(source, decoded_path, 1.0)
        natural_trimmed, natural_onset, natural_offset = trim_voice_edges(natural_samples)
        natural_clip_seconds = len(natural_trimmed) / RATE
        natural_speech_seconds = natural_offset - natural_onset
        tempo = voice_tempo_factor(natural_clip_seconds, available, max_speedup, min_tempo)
        samples = natural_samples if tempo == 1.0 else decode_mp3(source, decoded_path, tempo)
        trimmed, speech_onset, speech_offset = trim_voice_edges(samples)

        # MP3 frame rounding can leave a few milliseconds over the boundary. Correct iteratively,
        # using only a small additional tempo change; never truncate or discard spoken audio.
        for _ in range(4):
            if len(trimmed) <= round(available * RATE):
                break
            correction = (len(trimmed) / (available * RATE)) * 1.005
            tempo = voice_tempo_factor(tempo * correction, 1.0, max_speedup, min_tempo)
            samples = decode_mp3(source, decoded_path, tempo)
            trimmed, speech_onset, speech_offset = trim_voice_edges(samples)
        if len(trimmed) > round(available * RATE):
            raise RuntimeError(f"{sid}: complete narration still exceeds its shot after safe time-fit")

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
        spoken_seconds = speech_offset - speech_onset
        fill_fraction = spoken_seconds / shot_duration
        if fill_fraction < 0.82:
            raise RuntimeError(
                f"{sid}: narration covers only {fill_fraction:.1%} of its video shot; "
                "revise the line/audio instead of accepting a short voiceover."
            )
        shot_timings.append({
            "id": sid,
            "narration_id": shot["narration_id"],
            "text": shot["narration"],
            "start": shot_start,
            "duration": shot_duration,
            "source_seconds": round(raw_duration, 3),
            "natural_clip_seconds": round(natural_clip_seconds, 3),
            "natural_speech_seconds": round(natural_speech_seconds, 3),
            "spoken_seconds": round(spoken_seconds, 3),
            "shot_fill_fraction": round(fill_fraction, 4),
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


def synthesize_beds(work_dir: Path, story: dict) -> tuple[np.ndarray, np.ndarray]:
    """Original procedural score and Foley for the nine chapters (no stock audio).

    Palette: low cello, winter wind, distant postwar traffic, abacus clicks, a ticking wall clock, delicate glass-cup chimes, printing-press rhythm, snow footsteps and a restrained courtroom gavel. All music and Foley are procedurally synthesised; no licensed recordings are used.
    """
    work_audio = work_dir / "audio"
    work_audio.mkdir(parents=True, exist_ok=True)
    music_path = work_audio / "original-suspense-score.wav"
    sfx_path = work_audio / "procedural-sfx.wav"
    duration = float(story["target_duration"])
    total = int(round(duration * RATE))
    rng = np.random.default_rng(20001230)
    wind_state = 0.0
    rumble_state = 0.0
    # Chapter edges come from the storyboard, so the score always follows the picture.
    chapter_edges = np.array([float(c["start"]) for c in story["chapters"]] + [duration])
    sections = len(story["chapters"])

    def section_index(t: np.ndarray) -> np.ndarray:
        return np.clip(np.searchsorted(chapter_edges, t, side="right") - 1, 0, sections - 1)

    def gate(t: np.ndarray, lo: float, hi: float) -> np.ndarray:
        return ((t >= lo) & (t < hi)).astype(np.float64)

    # Suspense piano phrase under the false-official sequence.
    piano_notes = np.array([196.00, 233.08, 261.63, 174.61, 207.65, 233.08, 164.81, 220.00])
    piano_step = 0.52

    with wave.open(str(music_path), "wb") as music_file, wave.open(str(sfx_path), "wb") as sfx_file:
        for writer in (music_file, sfx_file):
            writer.setnchannels(2)
            writer.setsampwidth(2)
            writer.setframerate(RATE)
        for offset in range(0, total, BLOCK):
            count = min(BLOCK, total - offset)
            t = (offset + np.arange(count, dtype=np.float64)) / RATE
            section = section_index(t)
            fade = np.minimum(np.clip(t / 1.6, 0, 1), np.clip((duration - t) / 1.8, 0, 1))

            # ---- sustained bed: contrabass + cello + one detuned pair for width
            lfo = 0.76 + 0.18 * np.sin(2 * np.pi * 0.019 * t)
            cello = (0.090 * np.sin(2 * np.pi * 55.00 * t)
                     + 0.042 * np.sin(2 * np.pi * 82.41 * t + 0.35)
                     + 0.020 * np.sin(2 * np.pi * 110.00 * t + 0.90)) * lfo
            sub = 0.050 * np.sin(2 * np.pi * 36.71 * t)
            drone = (0.046 * np.sin(2 * np.pi * 73.42 * t)
                     + 0.026 * np.sin(2 * np.pi * 146.83 * t + 0.4)
                     * (0.5 + 0.5 * np.sin(2 * np.pi * 0.06 * t)))
            strings = (0.026 * np.sin(2 * np.pi * 98.00 * t)
                       + 0.020 * np.sin(2 * np.pi * 116.54 * t + 0.16)
                       + 0.014 * np.sin(2 * np.pi * 146.83 * t + 0.72))
            tremolo = strings * (0.65 + 0.35 * np.sin(2 * np.pi * 5.6 * t))
            tension = 0.013 * np.sin(2 * np.pi * 233.08 * t) + 0.010 * np.sin(2 * np.pi * 246.94 * t + 0.5)
            room_tone = 0.007 * (np.sin(2 * np.pi * 60.0 * t) + np.sin(2 * np.pi * 120.3 * t))

            # ---- suspense piano under the false-official sequence, cooling at its end
            step = np.floor((t - 10.0) / piano_step).astype(int)
            age = np.mod(np.maximum(t - 10.0, 0.0), piano_step)
            note = piano_notes[np.mod(np.maximum(step, 0), len(piano_notes))]
            warm_piano = 0.048 * np.sin(2 * np.pi * note * t) * np.exp(-age * 3.1)
            warm_piano += 0.016 * np.sin(2 * np.pi * note * 2.01 * t + 0.3) * np.exp(-age * 5.4)
            warm_piano *= gate(t, 10.0, 31.0)

            # ---- sparse suspense piano and slow pulse for the investigation chapters
            pulse_step = 1.05
            pulse_age = np.mod(np.maximum(t - 72.0, 0.0), pulse_step)
            pulse = 0.040 * np.sin(2 * np.pi * 55.0 * t) * np.exp(-pulse_age * 3.6)
            pulse *= gate(t, 72.0, 114.0)
            suspense_step = 1.9
            s_age = np.mod(np.maximum(t - 72.0, 0.0), suspense_step)
            s_index = np.mod(np.floor((t - 72.0) / suspense_step).astype(int), 5)
            s_notes = np.array([146.83, 174.61, 220.00, 174.61, 130.81])
            suspense_piano = 0.045 * np.sin(2 * np.pi * s_notes[s_index] * t) * np.exp(-s_age * 2.4)
            suspense_piano *= gate(t, 72.0, 93.0)
            office_piano = 0.038 * np.sin(2 * np.pi * s_notes[s_index] * t) * np.exp(-s_age * 2.0)
            office_piano *= gate(t, 114.0, 135.0)

            # ---- decaying cello line over the unsolved chapters, then the closing notes
            descent = np.clip((t - 135.0) / 21.0, 0.0, 1.0)
            glide_hz = 110.0 * np.exp(-0.42 * descent)
            gliding = 0.052 * np.sin(2 * np.pi * glide_hz * t) * gate(t, 135.0, 156.0)
            outro_env = np.clip((168.0 - t) / 12.0, 0.0, 1.0)
            outro = (0.058 * np.sin(2 * np.pi * 110.0 * t)
                     + 0.026 * np.sin(2 * np.pi * 87.31 * t + 0.4)) * outro_env * (t >= 156.0)

            levels = np.array([0.62, 0.58, 0.66, 0.60, 0.62, 0.58, 0.60, 0.66, 0.44])
            score = (
                (cello * 0.85 + sub + drone * 0.35) * (section == 0)
                + (warm_piano + drone * 0.45 + cello * 0.25) * (section == 1)
                + (tremolo + cello * 0.55 + sub * 0.6) * (section == 2)
                + (cello * 0.45 + drone * 0.7 + room_tone * 0.5) * (section == 3)
                + (pulse + suspense_piano + drone * 0.4) * (section == 4)
                + (pulse * 0.7 + room_tone * 0.8 + cello * 0.3 + tension * 0.6) * (section == 5)
                + (cello * 0.5 + office_piano + drone * 0.5) * (section == 6)
                + (gliding + cello * 0.40 + tremolo * 0.35) * (section == 7)
                + (outro + cello * 0.22) * (section == 8)
            )
            section_level = levels[section]
            score = np.tanh(score * 1.30) * section_level * fade
            # At the first indirect aftermath image, pull the score sharply back, then let
            # the low piano bed return under the rescue/report montage.
            aftermath = np.clip((t - 65.0) / 8.0, 0.12, 1.0)
            score *= np.where((t >= 60.0) & (t < 73.0), aftermath, 1.0)
            pan = 0.05 * np.sin(2 * np.pi * 0.015 * t)
            music_pcm = np.clip(np.column_stack((score * (1.0 - pan), score * (1.0 + pan))) * 32767,
                                -32768, 32767).astype("<i2")
            music_file.writeframes(music_pcm.tobytes())

            # ---- Foley beds -------------------------------------------------------------
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
            wind_gain = np.select(
                [section == 0, section == 1, section == 2, section == 3,
                 section == 4, section == 5, section == 6, section == 7, section == 8],
                [0.032, 0.010, 0.006, 0.014, 0.008, 0.012, 0.009, 0.025, 0.018],
                default=0.012,
            )
            sfx = wind * wind_gain

            # Snowy postwar street traffic and the muffled wind at the bank exterior.
            for at, amp in ((2.2, 0.022), (21.8, 0.018), (26.7, 0.014), (75.0, 0.018), (171.2, 0.010)):
                env = _event_envelope(t, at, 3.0, 0.85)
                sfx += env * amp * rumble

            # Wooden abacus beads in the opening bank hall and the signature glass-cup motif.
            for at in np.arange(3.0, 9.2, 0.32):
                env = _event_envelope(t, float(at), 0.11, 32.0)
                sfx += env * (0.020 * np.sin(2 * np.pi * 1450.0 * (t-at))
                              + 0.009 * np.sin(2 * np.pi * 2180.0 * (t-at)+0.3))
            for at in (30.7, 32.2, 42.5, 44.2, 46.4, 55.6, 57.0, 58.3):
                env = _event_envelope(t, at, 0.48, 4.8)
                sfx += env * (0.018 * np.sin(2 * np.pi * 1320.0 * (t-at))
                              + 0.010 * np.sin(2 * np.pi * 1975.0 * (t-at)+0.5))

            # A faint distant bell over the opening snow-night street.
            bell_env = _event_envelope(t, 7.8, 2.0, 2.1)
            sfx += bell_env * (0.008 * np.sin(2 * np.pi * 659.3 * (t-7.8))
                               + 0.004 * np.sin(2 * np.pi * 987.8 * (t-7.8)+0.2))

            # Three firm knocks on the rear door; restrained rather than startling.
            for at in (10.8, 11.5, 12.2):
                env = _event_envelope(t, at, 0.20, 18.0)
                sfx += env * (0.030 * np.sin(2 * np.pi * 165.0 * (t-at))
                              + 0.012 * rng.normal(0.0, 1.0, count))

            # The old wall clock ticks clearly for the one-minute wait (S09).
            for at in np.arange(49.15, 60.1, 1.0):
                env = _event_envelope(t, float(at), 0.12, 30.0)
                sfx += env * (0.026 * np.sin(2 * np.pi * 930.0 * (t-at))
                              + 0.012 * np.sin(2 * np.pi * 1860.0 * (t-at)))

            # Subtle high-frequency room tone after the cutaway; no distress or pain sound.
            sfx += gate(t, 60.1, 65.0) * 0.0018 * np.sin(2 * np.pi * 760.0 * t)

            # One cup drops and taps the floor; no distress, impact on a person or violent foley.
            for at, amp in ((60.45, 0.050), (60.72, 0.020), (61.05, 0.012)):
                env = _event_envelope(t, at, 0.34, 8.0)
                sfx += env * (amp * np.sin(2 * np.pi * 780.0 * (t-at))
                              + amp * 0.35 * np.sin(2 * np.pi * 1240.0 * (t-at)+0.4))

            # A soft rolling press rhythm for the non-readable newspaper montage.
            press = gate(t, 80.0, 85.0)
            press_phase = np.mod(t * 3.2, 1.0)
            press_pulse = np.exp(-press_phase * 9.0) * (press_phase < 0.28)
            sfx += press * (0.018 * press_pulse * np.sin(2 * np.pi * 92.0 * t)
                            + 0.006 * rng.normal(0.0, 1.0, count))
            for at in (80.4, 82.2, 84.1):
                env = _event_envelope(t, at, 0.45, 5.5)
                sfx += env * 0.018 * rng.normal(0.0, 1.0, count)

            # A distant, low ambulance/police siren swells briefly outside the bank.
            siren_env = gate(t, 73.0, 81.0)
            siren_hz = 440.0 + 70.0 * np.sin(2 * np.pi * 0.28 * (t-73.0))
            sfx += siren_env * 0.004 * np.sin(2 * np.pi * siren_hz * t)

            # Snow footsteps during the Otaru tail and arrest; cloth and canvas rustle nearby.
            for at in np.arange(117.4, 134.0, 0.72):
                env = _event_envelope(t, float(at), 0.32, 7.5)
                sfx += env * (0.023 * np.sin(2 * np.pi * 88.0 * (t-at))
                              + 0.020 * rng.normal(0.0, 1.0, count))
            for at in (124.8, 126.4, 128.0, 131.1, 133.0):
                env = _event_envelope(t, at, 0.36, 6.5)
                sfx += env * 0.014 * rng.normal(0.0, 1.0, count)

            # Paper, pen and subdued room tone across the interrogation and court scenes.
            for at in (137.0, 140.1, 143.0, 146.3, 151.1):
                env = _event_envelope(t, at, 0.40, 6.0)
                sfx += env * 0.017 * rng.normal(0.0, 1.0, count)
            pen = gate(t, 142.0, 148.0)
            sfx += pen * 0.008 * rng.normal(0.0, 1.0, count) * (0.5 + 0.5 * np.sin(2 * np.pi * 8.0 * t))

            # A single muted wooden court gavel at the verdict; no aggressive impact design.
            gavel_at = 154.05
            gavel = _event_envelope(t, gavel_at, 0.58, 6.0)
            sfx += gavel * (0.060 * np.sin(2 * np.pi * 118.0 * (t-gavel_at))
                            + 0.025 * rng.normal(0.0, 1.0, count))

            # A restrained closing glassy tone under the question/end card, then silence.
            for at, amp in ((169.0, 0.020), (176.8, 0.025)):
                env = _event_envelope(t, at, 1.35, 3.0)
                sfx += env * amp * (np.sin(2 * np.pi * 1046.5 * (t-at))
                                    + 0.48 * np.sin(2 * np.pi * 1568.0 * (t-at)+0.4))
            sfx *= np.clip((178.6 - t) / 0.6, 0, 1)
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
    target_ratio = 10 ** ((BGM_TARGET_BELOW_VOICE_DB + BGM_SIDECHAIN_MAKEUP_DB) / 20.0)
    raw_gain = (voice_levels * target_ratio) / np.maximum(music_levels, 1e-5)
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
    per_sample_gain = np.repeat(smooth_gain.astype(np.float32), hop)
    if len(per_sample_gain) < len(voice):
        per_sample_gain = np.pad(per_sample_gain, (0, len(voice) - len(per_sample_gain)),
                                 constant_values=BGM_SILENCE_LEVEL)
    music_mix = music * per_sample_gain[:len(voice), None]
    mix = voice_stereo + music_mix + effects * SFX_LEVEL

    # Last second is fully silent; the previous 0.25s eases the synthesized beds down.
    fade_start = int(178.75 * RATE)
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
        "bgm_sidechain_makeup_db": BGM_SIDECHAIN_MAKEUP_DB,
        "bgm_under_voice_measured_db": dbfs(float(np.median(
            (music_levels[active_voice] * smooth_gain[active_voice]) / np.maximum(voice_levels[active_voice], 1e-6)
        ))) if np.any(active_voice) else None,
        "bgm_silence_gain": BGM_SILENCE_LEVEL,
        "sfx_level": SFX_LEVEL,
        "narration": narration_report,
        "music_file": "original-suspense-score.wav",
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
