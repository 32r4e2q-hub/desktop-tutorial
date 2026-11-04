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
        max_speech_end = min(shot_end - 0.08, float(story["target_duration"]) - 1.6)
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
    """Original procedural score and Foley, cut to the storyboard's two palettes.

    Fear line: contrabass, low strings, a heartbeat kick, a lone clarinet, church-organ pads,
    chisel on wood, shutter knocks, a ticking clock, river horn and pistol echo only as
    reverberation. Jazz line: cornet, clarinet, trombone, banjo, brushed drum kit and a walking
    bass over a swinging 12-bar-ish loop, plus bell strikes and lantern sizzle. Everything is
    synthesised here, so the film carries no licensed audio and no stock music.
    """
    work_audio = work_dir / "audio"
    work_audio.mkdir(parents=True, exist_ok=True)
    music_path = work_audio / "original-neworleans-score.wav"
    sfx_path = work_audio / "procedural-sfx.wav"
    duration = float(story["target_duration"])
    total = int(round(duration * RATE))
    rng = np.random.default_rng(19190319)
    wind_state = 0.0
    rumble_state = 0.0
    # Chapter edges come from the storyboard, so the score always follows the picture.
    chapter_edges = np.array([float(c["start"]) for c in story["chapters"]] + [duration])
    tones = [c.get("tone", "fear") for c in story["chapters"]]
    sections = len(story["chapters"])
    # Per-chapter score level: the jazz chapters are allowed to sit closer to the voice.
    levels = np.array([0.74, 0.60, 0.62, 0.62, 0.64, 0.80, 0.58, 0.62, 0.70])[:sections]
    trumpet_shots = {"N1": 0.0, "N6": 108.0, "N9": 174.0}

    def section_index(t: np.ndarray) -> np.ndarray:
        return np.clip(np.searchsorted(chapter_edges, t, side="right") - 1, 0, sections - 1)

    def gate(t: np.ndarray, lo: float, hi: float) -> np.ndarray:
        return ((t >= lo) & (t < hi)).astype(np.float64)

    # ---- jazz material: a swung 12-bar in F, one bar = 2.0 s -------------------------------
    swing = 2.0 / 3.0            # 3 eighth notes per 2 seconds -> shuffle feel
    jazz_hz = {
        "F3": 174.61, "A3": 220.00, "C4": 261.63, "E4": 329.63, "F4": 349.23,
        "G4": 392.00, "A4": 440.00, "Bb4": 466.16, "C5": 523.25, "D5": 587.33,
    }
    # (bar, eighth index 0..5, note, instrument)
    jazz_hits = []
    cornet_line = ["F4", "A4", "C5", "A4", "G4", "F4"]
    clarinet_line = ["C5", "A4", "F4", "G4", "A4", "C5"]
    trombone_line = ["F3", "F3", "Bb4", "A4", "G4", "F4"]
    for bar in range(90):
        for eighth in range(6):
            step = eighth / 3.0
            base = bar * swing * 3
            jazz_hits.append((base + step, cornet_line[eighth % 6], "cornet", bar))
            if eighth in (1, 4):
                jazz_hits.append((base + step, clarinet_line[eighth % 6], "clarinet", bar))
            if eighth in (0, 3):
                jazz_hits.append((base + step, trombone_line[eighth % 6], "trombone", bar))
            if eighth in (0, 2, 3, 5):
                jazz_hits.append((base + step, ["F3", "A3", "C4", "E4"][(bar + eighth) % 4], "banjo", bar))
    # walking bass: one note per beat (2 per bar)
    bass_walk = ["F3", "A3", "C4", "A3", "Bb4" if False else "F3", "E4", "F3", "C4"]
    jazz_bass = [(bar * swing * 3 + beat * swing * 1.5, bass_walk[(bar * 2 + beat) % 8])
                 for bar in range(90) for beat in range(2)]

    # Bucket every note/brush/kick by the 1-second render block it can touch, so the synth loop
    # stays O(events-nearby) instead of scanning the whole score 180 times.
    def bucket(events, tail=1.3):
        buckets = {}
        for event in events:
            at = event[0]
            for block_index in range(int(at // BLOCK), int((at + tail) // BLOCK) + 1):
                buckets.setdefault(block_index, []).append(event)
        return buckets

    jazz_buckets = bucket(jazz_hits)
    bass_buckets = bucket(jazz_bass)
    ride_events = [(bar * swing * 3 + eighth / 3.0, "ride")
                   for bar in range(90) for eighth in (1, 3, 5)]
    kick_events = [(bar * swing * 3 + beat, "kick", amp)
                   for bar in range(90) for beat, amp in ((0.0, 0.055), (swing * 1.5, 0.030), (swing * 3.0, 0.048))]
    ride_buckets = bucket(ride_events, tail=0.5)
    kick_buckets = bucket(kick_events, tail=0.6)

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
            is_jazz = np.isin(section, [i for i, tone in enumerate(tones) if tone == "jazz"])
            fade = np.minimum(np.clip(t / 1.2, 0, 1), np.clip((duration - t) / 2.2, 0, 1))

            # ---- fear bed: contrabass + low strings + heartbeat ------------------------------
            lfo = 0.72 + 0.22 * np.sin(2 * np.pi * 0.021 * t)
            cello = (0.088 * np.sin(2 * np.pi * 55.00 * t)
                     + 0.040 * np.sin(2 * np.pi * 82.41 * t + 0.35)
                     + 0.019 * np.sin(2 * np.pi * 110.00 * t + 0.90)) * lfo
            sub = 0.048 * np.sin(2 * np.pi * 36.71 * t)
            drone = (0.042 * np.sin(2 * np.pi * 73.42 * t)
                     + 0.024 * np.sin(2 * np.pi * 146.83 * t + 0.4)
                     * (0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t)))
            tremolo = ((0.024 * np.sin(2 * np.pi * 98.00 * t)
                        + 0.017 * np.sin(2 * np.pi * 116.54 * t + 0.16))
                       * (0.62 + 0.38 * np.sin(2 * np.pi * 5.4 * t)))
            heartbeat_age = np.mod(np.maximum(t - 10.0, 0.0), 0.92)
            heartbeat = (0.055 * np.sin(2 * np.pi * 46.0 * t) * np.exp(-heartbeat_age * 14.0)
                         + 0.028 * np.sin(2 * np.pi * 46.0 * t) * np.exp(-np.mod(heartbeat_age + 0.72, 0.92) * 16.0))
            # a lone clarinet line over the fear sections, sparse and sour
            reed_step = 2.35
            reed_age = np.mod(np.maximum(t - 10.0, 0.0), reed_step)
            reed_index = np.mod(np.floor((t - 10.0) / reed_step).astype(int), 7)
            reed_notes = np.array([233.08, 220.00, 196.00, 174.61, 196.00, 220.00, 185.00])
            lonely_clarinet = 0.030 * _reed(t, reed_notes[reed_index] / 2.0) * np.exp(-reed_age * 1.9)
            # organ pad for the letter chapter, low and hollow
            organ = (0.030 * (np.sin(2 * np.pi * 73.42 * t) + 0.7 * np.sin(2 * np.pi * 110.00 * t)
                              + 0.45 * np.sin(2 * np.pi * 146.83 * t))
                     * (0.62 + 0.38 * np.sin(2 * np.pi * 0.4 * t)))
            # piano single notes for the river / Gretna chapter
            piano_step = 1.65
            piano_age = np.mod(np.maximum(t - 60.0, 0.0), piano_step)
            piano_index = np.mod(np.floor((t - 60.0) / piano_step).astype(int), 4)
            piano_notes = np.array([146.83, 174.61, 196.00, 130.81])
            river_piano = 0.042 * _pluck(t - 60.0 - np.floor((t - 60.0) / piano_step) * piano_step,
                                         piano_notes[piano_index], 2.1)
            # the closing unease: a slow descending cello
            descent = np.clip((t - 168.0) / 11.0, 0.0, 1.0)
            glide_hz = 110.0 * np.exp(-0.40 * descent)
            gliding = 0.050 * np.sin(2 * np.pi * glide_hz * t) * gate(t, 168.0, 179.0)

            # ---- jazz band (only the events that overlap this second) ----------------------
            jazz = np.zeros(count, dtype=np.float64)
            for at, note, instrument, _bar in jazz_buckets.get(block_index, ()):
                local = t - at
                decay = 3.4 if instrument == "banjo" else 2.2
                env = np.where(local >= 0, np.exp(-np.clip(local, 0, None) * decay), 0.0)
                freq = jazz_hz[note]
                if instrument == "cornet":
                    jazz += 0.055 * env * _brass(local, freq)
                elif instrument == "clarinet":
                    jazz += 0.030 * env * _reed(local, freq)
                elif instrument == "trombone":
                    jazz += 0.036 * env * _reed(local, freq / 2.0, phase=0.8)
                else:
                    jazz += 0.030 * env * _pluck(local, freq * 2.0, 6.0)
            for at, note in bass_buckets.get(block_index, ()):
                local = t - at
                env = np.where(local >= 0, np.exp(-np.clip(local, 0, None) * 2.8), 0.0)
                jazz += 0.048 * env * np.sin(2 * np.pi * jazz_hz[note] / 2.0 * local)
            for at, _kind in ride_buckets.get(block_index, ()):
                local = t - at
                env = np.where(local >= 0, np.exp(-np.clip(local, 0, None) * 26.0), 0.0)
                jazz += 0.020 * env * rng.normal(0.0, 1.0, count)
            for at, _kind, amp in kick_buckets.get(block_index, ()):
                local = t - at
                env = np.where(local >= 0, np.exp(-np.clip(local, 0, None) * 22.0), 0.0)
                jazz += amp * env * np.sin(2 * np.pi * 62.0 * local)
            jazz_env = np.clip((t - chapter_edges[0]) / 0.6, 0, 1)

            fear = (cello * 0.90 + sub + drone * 0.40
                    + gate(t, 35.0, 60.0) * (tremolo + heartbeat)
                    + gate(t, 10.0, 60.0) * lonely_clarinet
                    + gate(t, 85.0, 108.0) * (organ + tremolo * 0.5)
                    + gate(t, 60.0, 85.0) * (river_piano + drone * 0.6 + cello * 0.3)
                    + gate(t, 108.0, 130.0) * 0.0
                    + gate(t, 130.0, 150.0) * (river_piano * 0.8 + cello * 0.5 + heartbeat * 0.6)
                    + gate(t, 150.0, 168.0) * (cello * 0.55 + drone * 0.6 + tremolo * 0.5)
                    + gliding)
            score = np.where(is_jazz, jazz * jazz_env, fear)
            section_level = levels[section]
            score = np.tanh(score * 1.25) * section_level * fade
            pan = 0.06 * np.sin(2 * np.pi * 0.013 * t)
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

            wind_gain = np.where(is_jazz, 0.012, 0.026) * fade
            sfx = wind * wind_gain
            noise = rng.normal(0.0, 1.0, count)

            # Street bells: the sound-and-picture sync at 0 s, 120 s and the last bell at 174 s.
            for at, amp in ((0.0, 0.080), (120.0, 0.058), (174.2, 0.044)):
                env = _event_envelope(t, at, 3.0, 1.05)
                local = np.maximum(t - at, 0.0)
                for ratio, strength in ((1.0, 1.0), (2.02, 0.55), (2.98, 0.30), (4.07, 0.16)):
                    sfx += env * amp * strength * np.sin(2 * np.pi * 196.0 * ratio * local)
            # Dance-hall crowd: a soft filtered babble during the jazz chapters.
            crowd = np.where(is_jazz, 1.0, 0.0) * 0.011 * noise * (0.55 + 0.45 * np.sin(2 * np.pi * 1.7 * t))
            sfx += crowd
            # Lanterns and gas jets hissing on the fear streets.
            for at, amp in ((10.2, 0.016), (35.4, 0.012), (49.2, 0.010), (137.4, 0.014), (144.3, 0.018)):
                env = _event_envelope(t, at, 1.8, 1.2)
                sfx += env * amp * noise
            # Chisel biting into wood (slow, rhythmic) under the door-panel shot.
            for at in (17.4, 18.6, 19.9, 21.2, 22.5, 23.4):
                env = _event_envelope(t, at, 0.30, 11.0)
                scratch = np.sin(2 * np.pi * 720.0 * (t - at)) * 0.35 + noise * 0.65
                sfx += env * 0.055 * scratch
            for at in (23.6, 24.4):
                env = _event_envelope(t, at, 0.22, 26.0)
                sfx += env * 0.045 * noise
            # Wood shavings ticking onto flagstones; hammer blows when the windows are boarded.
            for at in (22.9, 23.9, 24.6):
                sfx += _event_envelope(t, at, 0.10, 34.0) * 0.024 * noise
            for at in (50.4, 51.1, 52.0, 52.8, 53.6):
                env = _event_envelope(t, at, 0.16, 24.0)
                sfx += env * (0.050 * np.sin(2 * np.pi * 168.0 * (t - at)) + 0.030 * noise)
            # Cupboard door closing, curtain drawn, a nail dropping.
            for at, amp in ((50.0, 0.030), (52.3, 0.022), (54.1, 0.018)):
                sfx += _event_envelope(t, at, 0.20, 18.0) * amp * noise
            # Newspaper: paper slaps and ripples.
            for at, amp in ((55.2, 0.030), (56.1, 0.022), (57.3, 0.026), (58.4, 0.020), (97.4, 0.026), (98.9, 0.022)):
                sfx += _event_envelope(t, at, 0.34, 7.5) * amp * noise
            # River: a steamboat horn across the water, then water against the bank.
            horn_env = np.clip((t - 61.4) / 0.5, 0, 1) * np.clip((65.6 - t) / 1.2, 0, 1)
            horn_local = np.maximum(t - 61.4, 0.0)
            sfx += horn_env * 0.052 * (np.sin(2 * np.pi * 98.0 * horn_local)
                                       + 0.5 * np.sin(2 * np.pi * 147.0 * horn_local + 0.4))
            water = gate(t, 60.0, 69.0) * 0.012 * noise * (0.5 + 0.5 * np.sin(2 * np.pi * 0.55 * t))
            sfx += water
            # The small ball rolling over floorboards, then stopping at the sill.
            roll = gate(t, 67.4, 71.0)
            sfx += roll * 0.016 * noise * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 11.0 * t)))
            sfx += _event_envelope(t, 71.1, 0.10, 30.0) * 0.026 * noise
            # Kerchief / chair scrape and the low clock in the interrogation room.
            for at, amp in ((74.6, 0.020), (76.2, 0.016)):
                sfx += _event_envelope(t, at, 0.30, 12.0) * amp * noise
            tick = gate(t, 74.0, 80.0) * ((np.mod(t, 1.0) < 0.045) | ((np.mod(t, 1.0) > 0.5) & (np.mod(t, 1.0) < 0.545)))
            sfx += tick * 0.024 * noise
            # Envelope slit, thunder rolling outside the newspaper office.
            sfx += _event_envelope(t, 85.6, 0.26, 20.0) * 0.040 * noise
            thunder = _event_envelope(t, 88.9, 3.4, 0.7) * 0.070 * rumble
            sfx += thunder
            # A printed page igniting line by line: soft paper crepitation and a writing nib.
            for at in (92.0, 92.9, 93.7, 94.6, 95.5):
                sfx += _event_envelope(t, at, 0.18, 16.0) * 0.020 * noise
            sfx += gate(t, 91.0, 97.0) * 0.008 * noise * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 8.4 * t)))
            # Press rollers and the crowd outside.
            roller = gate(t, 97.0, 103.0)
            sfx += roller * (0.020 * np.sin(2 * np.pi * 43.0 * t) + 0.012 * noise)
            sfx += gate(t, 99.0, 103.0) * 0.012 * noise * (0.5 + 0.5 * np.sin(2 * np.pi * 0.8 * t))
            # Gramophone: needle drop, surface hiss, then the first notes of the band.
            sfx += _event_envelope(t, 103.5, 0.18, 26.0) * 0.032 * noise
            sfx += gate(t, 103.7, 108.0) * 0.010 * noise * (0.6 + 0.4 * np.sin(2 * np.pi * 1.3 * t))
            # Instruments tuning up before the big night: short detuned plucks.
            for index, at in enumerate((108.6, 109.4, 110.3, 111.1, 112.0, 112.8)):
                env = _event_envelope(t, at, 0.22, 12.0)
                sfx += env * 0.020 * _pluck(np.maximum(t - at, 0.0), 220.0 * (2 ** ((index % 4) / 12.0)), 9.0)
            # Piano keys and a pencil while the composer writes.
            for index, at in enumerate((114.5, 115.2, 115.9, 116.6, 117.6, 118.3, 119.0)):
                env = _event_envelope(t, at, 0.55, 4.2)
                note = [349.23, 392.00, 440.00, 523.25, 440.00, 392.00, 349.23][index]
                sfx += env * 0.030 * _pluck(np.maximum(t - at, 0.0), note, 3.4)
            sfx += gate(t, 114.2, 119.6) * 0.009 * noise * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 13.0 * t)))
            # Midnight: the whole city plays. A swell of brass over the jazz bed.
            swell = _event_envelope(t, 120.0, 5.0, 0.35)
            sfx += swell * 0.030 * _brass(np.maximum(t - 120.0, 0.0), 174.61)
            # The shadow stepping backwards: boots on stone, swallowed by the band.
            for at in (127.4, 128.1, 128.9):
                env = _event_envelope(t, at, 0.20, 20.0)
                sfx += env * 0.026 * noise
            # Autumn street: dry leaves scraping along the gutter.
            leaves = gate(t, 130.0, 137.0) * 0.010 * noise * (0.35 + 0.65 * np.abs(np.sin(2 * np.pi * 3.1 * t)))
            sfx += leaves
            # Back room: breath, a door swinging, the lamp catching.
            sfx += _event_envelope(t, 137.2, 0.9, 2.6) * 0.020 * noise
            sfx += _event_envelope(t, 140.1, 0.28, 16.0) * 0.034 * noise
            sfx += _event_envelope(t, 141.0, 0.12, 30.0) * 0.026 * noise
            # Lantern hiss and low voices at the last scene.
            sfx += gate(t, 144.0, 150.0) * 0.008 * noise * (0.5 + 0.5 * np.sin(2 * np.pi * 0.9 * t))
            sfx += _event_envelope(t, 146.4, 0.9, 2.2) * 0.014 * rumble
            # Pages turning over the case files, a tarpaulin-shrouded clock ticking.
            for at, amp in ((150.6, 0.026), (152.1, 0.020), (153.4, 0.022), (168.6, 0.022), (170.2, 0.018)):
                sfx += _event_envelope(t, at, 0.34, 8.0) * amp * noise
            # Los Angeles, 1920: tram bell and a dry hot wind.
            when_jazz_end = gate(t, 156.0, 168.0)
            sfx += when_jazz_end * 0.012 * noise * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 0.7 * t)))
            for at, amp in ((156.6, 0.030), (157.4, 0.022)):
                env = _event_envelope(t, at, 0.35, 9.0)
                sfx += env * amp * (np.sin(2 * np.pi * 1046.5 * (t - at)) + 0.4 * np.sin(2 * np.pi * 1568.0 * (t - at)))
            # Pistol: only the reverberation and the pigeons - never a shot in the clear.
            echo = _event_envelope(t, 162.5, 2.2, 1.5)
            local = np.maximum(t - 162.5, 0.0)
            sfx += echo * 0.052 * (np.sin(2 * np.pi * 72.0 * local) + 0.35 * rumble)
            wings = gate(t, 162.7, 165.2) * 0.020 * noise * (0.3 + 0.7 * np.abs(np.sin(2 * np.pi * 7.7 * t)))
            sfx += wings
            # Nothing sounds in the final stretch beyond the closing bell: clean fade to silence.
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
        "bgm_sidechain_makeup_db": BGM_SIDECHAIN_MAKEUP_DB,
        "bgm_under_voice_measured_db": dbfs(float(np.median(
            (music_levels[active_voice] * smooth_gain[active_voice]) / np.maximum(voice_levels[active_voice], 1e-6)
        ))) if np.any(active_voice) else None,
        "bgm_silence_gain": BGM_SILENCE_LEVEL,
        "sfx_level": SFX_LEVEL,
        "narration": narration_report,
        "music_file": "original-neworleans-score.wav",
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
