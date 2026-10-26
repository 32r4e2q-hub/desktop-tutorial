#!/usr/bin/env python3
"""Build shot-locked Somerton narration, matched captions and the measured final mix.

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


def synthesize_beds(work_dir: Path, duration: float = 180.0) -> tuple[np.ndarray, np.ndarray]:
    """Create low original score and quiet generated Foley in one-second chunks."""
    work_audio = work_dir / "audio"
    work_audio.mkdir(parents=True, exist_ok=True)
    music_path = work_audio / "original-suspense-score.wav"
    sfx_path = work_audio / "procedural-sfx.wav"
    total = int(round(duration * RATE))
    rng = np.random.default_rng(19481201)
    noise_state = 0.0
    wind_state = 0.0

    with wave.open(str(music_path), "wb") as music_file, wave.open(str(sfx_path), "wb") as sfx_file:
        for writer in (music_file, sfx_file):
            writer.setnchannels(2)
            writer.setsampwidth(2)
            writer.setframerate(RATE)
        for offset in range(0, total, BLOCK):
            count = min(BLOCK, total - offset)
            t = (offset + np.arange(count, dtype=np.float64)) / RATE
            section = np.select(
                [t < 10, t < 35, t < 55, t < 75, t < 100, t < 125, t < 150, t < 172],
                [0, 1, 2, 3, 4, 5, 6, 7], default=8,
            )
            progress = t / duration
            fade = np.minimum(np.clip(t / 1.3, 0, 1), np.clip((duration - t) / 1.1, 0, 1))
            section_level = np.select(
                [section == 0, section == 1, section == 2, section == 3, section == 4,
                 section == 5, section == 6, section == 7, section == 8],
                [0.62, 0.42, 0.58, 0.48, 0.48, 0.58, 0.60, 0.66, 0.34], default=0.5,
            )
            lfo = 0.76 + 0.18 * np.sin(2 * np.pi * 0.025 * t)
            cello = (0.090 * np.sin(2 * np.pi * 55.0 * t)
                     + 0.041 * np.sin(2 * np.pi * 110.0 * t + 0.35)
                     + 0.018 * np.sin(2 * np.pi * 165.0 * t + 0.90)) * lfo
            strings = (0.026 * np.sin(2 * np.pi * 73.42 * t)
                       + 0.021 * np.sin(2 * np.pi * 110.0 * t + 0.16)
                       + 0.014 * np.sin(2 * np.pi * 146.83 * t + 0.72))
            tension = 0.017 * np.sin(2 * np.pi * 220.0 * t) + 0.014 * np.sin(2 * np.pi * 233.08 * t + 0.5)
            pulse_period = np.mod(t, 0.82)
            heartbeat = 0.050 * np.sin(2 * np.pi * 48.0 * t) * np.exp(-pulse_period * 8.0)
            synth_pulse = 0.020 * np.sin(2 * np.pi * 92.50 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 1.3 * t))

            # Sparse Persian-inspired minor-mode plucks; all frequencies are original synthesis.
            motif_freq = np.array([146.83, 164.81, 196.00, 220.00, 246.94])
            note_index = np.floor((t - 75.0) / 2.6).astype(int)
            motif_active = (t >= 75.0) & (t < 100.0)
            selected_freq = motif_freq[np.mod(np.maximum(note_index, 0), len(motif_freq))]
            note_age = np.mod(np.maximum(t - 75.0, 0), 2.6)
            pluck = 0.040 * np.sin(2 * np.pi * selected_freq * t) * np.exp(-note_age * 2.2) * motif_active

            score = ((cello + strings) * np.isin(section, [0, 1, 2, 3, 8])
                     + (cello * 0.45 + strings * 0.55 + pluck) * (section == 4)
                     + (cello * 0.48 + tension * 0.8 + synth_pulse * 0.35) * (section == 5)
                     + (cello * 0.35 + tension * 1.35 + heartbeat * 0.42) * (section == 6)
                     + (cello * 0.55 + synth_pulse + strings * 0.4) * (section == 7)
                     + cello * (section == 8))
            score = np.tanh(score * 1.4) * section_level * fade
            pan = 0.06 * np.sin(2 * np.pi * 0.018 * t)
            left_music = score * (1.0 - pan)
            right_music = score * (1.0 + pan)
            music_pcm = np.clip(np.column_stack((left_music, right_music)) * 32767, -32768, 32767).astype("<i2")
            music_file.writeframes(music_pcm.tobytes())

            # Low-passed surf and breeze. State is carried across chunks to avoid seams.
            raw_noise = rng.normal(0.0, 1.0, count)
            raw_wind = rng.normal(0.0, 1.0, count)
            surf = np.empty(count, dtype=np.float64)
            wind = np.empty(count, dtype=np.float64)
            state = noise_state
            wstate = wind_state
            for i, value in enumerate(raw_noise):
                state = 0.988 * state + 0.012 * value
                surf[i] = state
            for i, value in enumerate(raw_wind):
                wstate = 0.996 * wstate + 0.004 * value
                wind[i] = wstate
            noise_state, wind_state = state, wstate
            wave_gain = (0.025 + 0.035 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 6.8)))
            coastal = np.isin(section, [0, 1, 8])
            sfx = surf * wave_gain * coastal + wind * 0.012

            # One distant bell near the hook, formed from soft inharmonic partials.
            bell = _event_envelope(t, 8.2, 3.4, 1.20)
            sfx += bell * (0.060 * np.sin(2*np.pi*523.25*t) + 0.032*np.sin(2*np.pi*784.0*t + 0.2)
                           + 0.018*np.sin(2*np.pi*1046.5*t + 0.5))

            # Two abstract gull calls, not a stock recording.
            for at in (13.5, 18.4):
                d = t - at
                call = (d >= 0) & (d < 1.0)
                freq = 1350 + 420 * np.sin(2 * np.pi * np.clip(d, 0, 1) * 1.2)
                sfx += call * 0.020 * np.sin(2 * np.pi * freq * d) * np.sin(np.pi * np.clip(d, 0, 1))

            # Cloth, paper, scissors and suitcase touches are restrained transients.
            for at, amp in ((30.8, 0.045), (32.0, 0.035), (33.1, 0.040), (37.0, 0.060),
                            (63.0, 0.050), (74.0, 0.035), (76.0, 0.030), (83.0, 0.030),
                            (90.0, 0.030), (97.0, 0.030)):
                click = _event_envelope(t, at, 0.22, 16.0)
                sfx += click * amp * rng.normal(0, 0.6, count)

            # Steam-train hiss/chuff at Adelaide station.
            train_window = (t >= 55) & (t < 75)
            chuff_phase = np.mod(t - 55, 1.7)
            steam = np.where(chuff_phase < 0.45, np.exp(-chuff_phase * 4.0), 0.0) * train_window
            sfx += steam * wind * 0.032

            # Quiet old rotary-phone dual tone and a heartbeat-like pulse in the theory section.
            dial_window = (t >= 114) & (t < 120)
            dial_phase = np.mod(t - 114, 1.1)
            dial_gate = ((dial_phase > 0.12) & (dial_phase < 0.52)).astype(float) * dial_window
            sfx += dial_gate * (0.025 * np.sin(2*np.pi*350*t) + 0.020*np.sin(2*np.pi*440*t))
            hb_phase = np.mod(t - 125, 0.88)
            hb = 0.050 * np.sin(2*np.pi*50*t) * np.exp(-hb_phase * 9.0) * ((t >= 125) & (t < 150))
            sfx += hb

            # Subtle electrical-room tone over the modern DNA segment.
            lab = (t >= 150) & (t < 172)
            sfx += lab * 0.012 * np.sin(2 * np.pi * (118 + 3 * np.sin(2*np.pi*0.2*t)) * t)

            # Nothing sounds in the final second, as requested.
            sfx *= np.clip((179.0 - t) / 0.18, 0, 1)
            stereo_sfx = np.column_stack((sfx, sfx * (1.0 + 0.035 * np.sin(2*np.pi*0.07*t))))
            sfx_pcm = np.clip(stereo_sfx * 32767, -32768, 32767).astype("<i2")
            sfx_file.writeframes(sfx_pcm.tobytes())

    music, _, _ = read_wave(music_path)
    effects, _, _ = read_wave(sfx_path)
    return music.astype(np.float32), effects.astype(np.float32)


def dbfs(value: float) -> float:
    if value <= 1e-12:
        return -120.0
    return round(20.0 * math.log10(value), 2)


def build_soundtrack(story: dict, audio_dir: Path, work_dir: Path) -> tuple[Path, dict, list[dict]]:
    voice, cues, narration_report = build_narration(story, audio_dir, work_dir)
    music, effects = synthesize_beds(work_dir, float(story["target_duration"]))
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
