#!/usr/bin/env python3
"""Create restrained, deterministic non-musical Foley beds for the 30-shot cut."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import wave

import numpy as np

HERE = Path(__file__).resolve().parent
SAMPLE_RATE = 48_000

CUES = {
    "S01": ("outdoor", [("metal_door", 0.35), ("wind", 1.2), ("footsteps", 2.9)]),
    "S02": ("room", [("cloth_rustle", 0.9), ("soft_click", 2.4)]),
    "S03": ("outdoor", [("wind", 0.4), ("bird", 2.8)]),
    "S04": ("outdoor", [("footsteps", 0.6), ("radio_hush", 2.4), ("car_pass", 4.1)]),
    "S05": ("outdoor", [("wind", 0.5), ("door_latch", 2.1), ("footsteps", 3.6)]),
    "S06": ("outdoor", [("murmur", 0.6), ("bag_drop", 2.6)]),
    "S07": ("room", [("paper", 1.1), ("lab_fan", 2.6), ("soft_click", 4.5)]),
    "S08": ("cold_room", [("tape_set_down", 0.9), ("paper", 2.4), ("clock_tick", 4.1)]),
    "S09": ("cold_room", [("clock_tick", 0.4), ("murmur", 2.2), ("clock_tick", 3.9)]),
    "S10": ("cold_room", [("paper", 0.9), ("pen_tap", 2.6), ("wind", 3.8)]),
    "S11": ("room", [("gavel", 2.8), ("murmur", 4.0)]),
    "S12": ("outdoor", [("wind", 0.6), ("murmur", 2.1), ("door_latch", 4.6)]),
    "S13": ("room", [("wind", 0.9), ("cloth_rustle", 3.1)]),
    "S14": ("corridor", [("door_latch", 0.8), ("footsteps", 2.0), ("metal_door", 3.6)]),
    "S15": ("room", [("gavel", 1.0), ("cloth_rustle", 3.2)]),
    "S16": ("cold_room", [("wind", 0.6), ("paper", 2.8)]),
    "S17": ("cold_room", [("wind", 0.4), ("pen_tap", 1.8), ("paper", 3.5)]),
    "S18": ("room", [("phone_connect", 0.8), ("paper", 2.5)]),
    "S19": ("room", [("paper", 0.9), ("file_slide", 2.8)]),
    "S20": ("outdoor", [("door_latch", 0.8), ("footsteps", 2.1), ("file_slide", 3.9)]),
    "S21": ("cold_room", [("stamp", 1.1), ("tape_set_down", 2.8)]),
    "S22": ("room", [("paper", 0.7), ("pen_tap", 2.4)]),
    "S23": ("outdoor", [("footsteps", 0.9), ("wind", 2.6), ("cloth_rustle", 4.4)]),
    "S24": ("room", [("file_slide", 1.0), ("paper", 2.9), ("soft_click", 4.8)]),
    "S25": ("room", [("gavel", 1.3), ("clock_stop", 3.2)]),
    "S26": ("outdoor", [("metal_door", 0.4), ("footsteps", 2.1), ("cloth_rustle", 3.7)]),
    "S27": ("cold_room", [("stamp", 1.4), ("file_slide", 3.0)]),
    "S28": ("room", [("paper", 1.0), ("murmur", 2.8), ("soft_click", 4.4)]),
    "S29": ("outdoor", [("wind", 0.7), ("car_pass", 3.2)]),
    "S30": ("silence", [("soft_click", 0.9)]),
}


def filtered_noise(rng: np.random.Generator, count: int, cutoff: float,
                   highpass: float | None = None) -> np.ndarray:
    x = rng.normal(0.0, 1.0, count).astype(np.float32)
    spectrum = np.fft.rfft(x)
    frequencies = np.fft.rfftfreq(count, 1.0 / SAMPLE_RATE)
    low = 1.0 / np.sqrt(1.0 + (frequencies / max(cutoff, 1.0)) ** 4)
    if highpass is not None:
        high = 1.0 - 1.0 / np.sqrt(1.0 + (frequencies / max(highpass, 1.0)) ** 4)
        low *= high
    shaped = np.fft.irfft(spectrum * low, n=count).astype(np.float32)
    peak = float(np.max(np.abs(shaped))) if count else 0.0
    return shaped / max(peak, 1e-6)


def add_bed(out: np.ndarray, kind: str, rng: np.random.Generator) -> None:
    n = len(out)
    if kind == "silence":
        return
    gains = {"outdoor": (520, 0.0042), "corridor": (320, 0.0040), "cold_room": (410, 0.0028),
             "lab": (700, 0.0025), "room": (620, 0.0024)}
    cutoff, gain = gains.get(kind, (620, 0.0024))
    noise = filtered_noise(rng, n, cutoff)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    slow = 0.72 + 0.28 * np.sin(2 * np.pi * 0.17 * t + 1.1)
    out += noise * slow.astype(np.float32) * gain


def add_noise_burst(out: np.ndarray, start: float, duration: float, gain: float,
                    rng: np.random.Generator, cutoff: float = 2500,
                    highpass: float | None = None, shape: str = "bell") -> None:
    i0 = max(0, int(start * SAMPLE_RATE))
    i1 = min(len(out), i0 + max(1, int(duration * SAMPLE_RATE)))
    count = i1 - i0
    if count <= 1:
        return
    noise = filtered_noise(rng, count, cutoff, highpass)
    u = np.linspace(0.0, 1.0, count, dtype=np.float32)
    env = np.exp(-7.0 * u) if shape == "decay" else np.maximum(0.0, np.sin(np.pi * u)) ** 1.4
    out[i0:i1] += noise * env * gain


def add_tone(out: np.ndarray, start: float, duration: float, gain: float,
             f0: float, f1: float | None = None) -> None:
    i0 = max(0, int(start * SAMPLE_RATE))
    i1 = min(len(out), i0 + max(1, int(duration * SAMPLE_RATE)))
    count = i1 - i0
    if count <= 1:
        return
    t = np.arange(count, dtype=np.float32) / SAMPLE_RATE
    final = f0 if f1 is None else f1
    phase = 2 * np.pi * (f0 * t + 0.5 * (final - f0) * t * t / max(duration, 0.001))
    env = np.maximum(0.0, np.sin(np.pi * np.linspace(0.0, 1.0, count, dtype=np.float32))) ** 1.2
    out[i0:i1] += gain * np.sin(phase) * env


def add_click(out: np.ndarray, at: float, rng: np.random.Generator,
              gain: float = 0.035, duration: float = 0.045, f: float = 900.0) -> None:
    add_noise_burst(out, max(0.0, at - 0.008), duration, gain, rng, cutoff=5000, highpass=420, shape="decay")
    add_tone(out, at, 0.055, gain * 0.27, f, f * 0.78)


def add_impact(out: np.ndarray, at: float, rng: np.random.Generator,
               gain: float = 0.055, metallic: bool = False) -> None:
    duration = 0.38 if metallic else 0.24
    add_noise_burst(out, max(0.0, at), duration, gain * 0.65, rng,
                    cutoff=3300 if metallic else 1100, highpass=500 if metallic else None, shape="decay")
    add_tone(out, max(0.0, at), duration, gain * 0.42, 420 if metallic else 105, 250 if metallic else 68)


def apply_event(out: np.ndarray, at: float, event: str, rng: np.random.Generator) -> None:
    if event == "bird":
        add_tone(out, at, 0.16, 0.018, 1900.0, 2550.0)
        add_tone(out, at + 0.24, 0.13, 0.014, 2550.0, 1995.0)
    elif event == "car_pass":
        add_noise_burst(out, at, 1.6, 0.012, rng, cutoff=280, shape="bell")
        add_tone(out, at, 1.6, 0.004, 90, 58)
    elif event in {"soft_click", "clock_stop"}:
        add_click(out, at, rng, gain=0.022, f=700)
    elif event in {"door_latch", "metal_door", "stamp", "gavel", "bag_drop", "tape_set_down"}:
        add_impact(out, at, rng, gain=0.058 if event in {"stamp", "gavel", "bag_drop"} else 0.048,
                   metallic=event in {"metal_door", "door_latch"})
    elif event == "footsteps":
        for offset in (0.0, 0.54, 1.08):
            add_impact(out, at + offset, rng, gain=0.028)
    elif event in {"paper", "file_slide", "cloth_rustle", "radio_hush", "wind", "murmur", "lab_fan"}:
        durations = {"paper": 0.42, "file_slide": 0.7, "cloth_rustle": 0.55,
                     "radio_hush": 0.8, "wind": 1.2, "murmur": 0.7, "lab_fan": 1.4}
        gains = {"paper": 0.013, "file_slide": 0.016, "cloth_rustle": 0.012,
                 "radio_hush": 0.006, "wind": 0.009, "murmur": 0.006, "lab_fan": 0.006}
        cutoff = 600 if event in {"wind", "lab_fan"} else 2800
        add_noise_burst(out, at, durations[event], gains[event], rng, cutoff=cutoff,
                        highpass=180 if event in {"paper", "cloth_rustle"} else None, shape="bell")
    elif event == "phone_connect":
        add_tone(out, at, 0.28, 0.014, 430, 390)
    elif event == "clock_tick":
        add_click(out, at, rng, gain=0.014, f=1350)
        add_click(out, at + 0.95, rng, gain=0.011, f=1250)
    elif event == "pen_tap":
        add_click(out, at, rng, gain=0.022, f=950)
    else:
        raise ValueError(f"Unknown SFX event: {event}")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def build(output: Path) -> dict:
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    clips = []
    for index, shot in enumerate(story["shots"], 1):
        sid = shot["id"]
        duration = float(shot["duration"])
        count = round(duration * SAMPLE_RATE)
        rng = np.random.default_rng(20261115 + index)
        mix = np.zeros(count, dtype=np.float32)
        bed, events = CUES[sid]
        add_bed(mix, bed, rng)
        for event, start in events:
            apply_event(mix, float(start), event, rng)
        if sid == "S30":
            fade = min(SAMPLE_RATE, count)
            mix[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
        peak = float(np.max(np.abs(mix))) if count else 0.0
        if peak > 0.22:
            mix *= 0.22 / peak
        stereo = np.column_stack((mix, mix)).astype(np.float32)
        pcm = np.clip(stereo * 32767.0, -32768, 32767).astype("<i2")
        path = output / f"{sid}.wav"
        with wave.open(str(path), "wb") as stream:
            stream.setnchannels(2)
            stream.setsampwidth(2)
            stream.setframerate(SAMPLE_RATE)
            stream.writeframes(pcm.tobytes())
        clips.append({
            "id": sid, "file": path.name, "sha256": digest(path),
            "seconds": duration, "samples": count, "sample_rate": SAMPLE_RATE,
            "bed": bed, "events": [{"name": name, "start": start} for name, start in events],
            "script_note": shot["sound_design"], "source": "deterministic procedural SFX; no music",
        })
    manifest = {
        "sample_rate": SAMPLE_RATE, "channels": 2,
        "policy": "shot-locked ambient Foley and short effects only; no BGM",
        "generation": "build_sfx.py deterministic seed 20261115+shot index",
        "clips": clips,
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(clips)} deterministic non-musical SFX clips to {output}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
