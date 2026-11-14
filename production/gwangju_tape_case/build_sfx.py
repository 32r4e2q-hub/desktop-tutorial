#!/usr/bin/env python3
"""Create restrained, deterministic non-musical Foley beds for the 30-shot cut.

These sounds are generated from noise bursts, short clicks, impacts and isolated tones; there
is no music track. Replace individual cues only with properly licensed material and keep the
shot timing/hash manifest in work/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import wave

import numpy as np

HERE = Path(__file__).resolve().parent
SAMPLE_RATE = 48_000

# (bed, events): event times are relative to the start of each shot.
CUES = {
    "S01": ("outdoor", [("bird", 0.35), ("car_pass", 1.65), ("soft_click", 4.0)]),
    "S02": ("silence", [("tape_peel", 1.2)]),
    "S03": ("room", [("kitchen_clink", 1.3), ("footsteps", 4.3)]),
    "S04": ("room", [("door_latch", 4.4)]),
    "S05": ("outdoor", [("bird", 0.45), ("zipper", 3.2)]),
    "S06": ("corridor", [("wind", 0.5)]),
    "S07": ("outdoor", [("footsteps", 0.4), ("car_pass", 3.0)]),
    "S08": ("room", [("bag_drop", 0.8), ("fruit_roll", 1.35)]),
    "S09": ("room", [("footsteps", 0.4), ("clock_tick", 3.8)]),
    "S10": ("room", [("phone_buttons", 1.1), ("phone_connect", 3.0)]),
    "S11": ("corridor", [("distant_siren", 0.6), ("footsteps", 2.6)]),
    "S12": ("room", [("paper", 1.6), ("radio_hush", 4.0)]),
    "S13": ("room", [("evidence_bag", 1.8), ("metal_tap", 3.2)]),
    "S14": ("room", [("evidence_bag", 0.5), ("evidence_bag", 1.35), ("evidence_bag", 2.2), ("soft_click", 4.1)]),
    "S15": ("room", [("paper", 0.7), ("phone_bell", 3.0)]),
    "S16": ("room", [("clock_tick", 0.4), ("murmur", 2.2)]),
    "S17": ("room", [("keypad", 1.4), ("keypad", 2.0)]),
    "S18": ("room", [("file_slide", 0.7), ("paper", 2.8)]),
    "S19": ("cold_room", [("clock_tick", 1.0), ("soft_click", 4.2)]),
    "S20": ("cold_room", [("pen_tap", 1.7), ("tape_set_down", 3.4)]),
    "S21": ("room", [("footsteps", 1.3), ("cloth_rustle", 3.6)]),
    "S22": ("silence", [("tape_peel", 1.0), ("tape_peel", 3.15)]),
    "S23": ("cold_room", [("metal_door", 0.5), ("footsteps", 2.25)]),
    "S24": ("lab", [("lab_fan", 0.3), ("electronic_beep", 4.0)]),
    "S25": ("lab", [("lab_fan", 0.3), ("electronic_beep", 1.4), ("electronic_beep", 3.5)]),
    "S26": ("room", [("stamp", 1.0), ("clock_stop", 3.0)]),
    "S27": ("cold_room", [("lock_click", 1.9)]),
    "S28": ("outdoor", [("wind", 0.7), ("camera_relay", 3.7)]),
    "S29": ("room", [("wind", 1.0), ("clock_tick", 3.9)]),
    "S30": ("silence", [("tape_peel", 0.7)]),
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
    if kind == "outdoor":
        noise = filtered_noise(rng, n, 520)
        gain = 0.0042
    elif kind == "corridor":
        noise = filtered_noise(rng, n, 320)
        gain = 0.0040
    elif kind == "cold_room":
        noise = filtered_noise(rng, n, 410)
        gain = 0.0028
    elif kind == "lab":
        noise = filtered_noise(rng, n, 700)
        gain = 0.0025
    else:
        noise = filtered_noise(rng, n, 620)
        gain = 0.0024
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
    if shape == "decay":
        env = np.exp(-7.0 * u)
    elif shape == "flat":
        env = np.minimum(1.0, np.minimum(u * 14.0, (1.0 - u) * 14.0))
    else:
        # Float32 sin(pi) can be a tiny negative value; clamp it before the fractional power.
        env = np.maximum(0.0, np.sin(np.pi * u)) ** 1.4
    out[i0:i1] += noise * env * gain


def add_tone(out: np.ndarray, start: float, duration: float, gain: float,
             f0: float, f1: float | None = None, rng: np.random.Generator | None = None) -> None:
    i0 = max(0, int(start * SAMPLE_RATE))
    i1 = min(len(out), i0 + max(1, int(duration * SAMPLE_RATE)))
    count = i1 - i0
    if count <= 1:
        return
    t = np.arange(count, dtype=np.float32) / SAMPLE_RATE
    final = f0 if f1 is None else f1
    phase = 2 * np.pi * (f0 * t + 0.5 * (final - f0) * t * t / max(duration, 0.001))
    # Clamp tiny negative round-off at sin(pi) before the fractional power.
    env = np.maximum(0.0, np.sin(np.pi * np.linspace(0.0, 1.0, count, dtype=np.float32))) ** 1.2
    out[i0:i1] += gain * np.sin(phase) * env


def add_click(out: np.ndarray, at: float, rng: np.random.Generator,
              gain: float = 0.035, duration: float = 0.045, f: float = 900.0) -> None:
    start = max(0.0, at - 0.008)
    add_noise_burst(out, start, duration, gain, rng, cutoff=5000, highpass=420,
                    shape="decay")
    add_tone(out, at, 0.055, gain * 0.27, f, f * 0.78, rng)


def add_impact(out: np.ndarray, at: float, rng: np.random.Generator,
               gain: float = 0.055, metallic: bool = False) -> None:
    duration = 0.38 if metallic else 0.24
    start = max(0.0, at)
    add_noise_burst(out, start, duration, gain * 0.65, rng,
                    cutoff=1100 if not metallic else 3300,
                    highpass=None if not metallic else 500,
                    shape="decay")
    add_tone(out, start, duration, gain * 0.42, 105 if not metallic else 420,
             68 if not metallic else 250, rng)


def add_chirp(out: np.ndarray, at: float, rng: np.random.Generator,
              gain: float = 0.022, f0: float = 1900.0, f1: float = 2550.0,
              duration: float = 0.16) -> None:
    add_tone(out, at, duration, gain, f0, f1, rng)
    add_tone(out, at + duration + 0.08, duration * 0.8, gain * 0.8,
             f1, f0 * 1.05, rng)


def apply_event(out: np.ndarray, at: float, event: str,
                rng: np.random.Generator) -> None:
    if event == "bird":
        add_chirp(out, at, rng)
    elif event == "car_pass":
        add_noise_burst(out, at, 1.6, 0.012, rng, cutoff=280, shape="bell")
        add_tone(out, at, 1.6, 0.004, 90, 58, rng)
    elif event in {"soft_click", "camera_relay", "lock_click", "keypad"}:
        add_click(out, at, rng, gain=0.024 if event == "soft_click" else 0.03,
                  f=650 if event != "keypad" else 1050)
    elif event in {"door_latch", "metal_tap", "metal_door", "stamp", "bag_drop", "tape_set_down"}:
        add_impact(out, at, rng, gain=0.048 if event not in {"stamp", "bag_drop"} else 0.062,
                   metallic=event in {"metal_tap", "metal_door", "door_latch"})
        if event == "door_latch":
            add_click(out, at + 0.16, rng, gain=0.022, f=500)
    elif event in {"footsteps", "fruit_roll"}:
        for offset in (0.0, 0.54, 1.08):
            add_impact(out, at + offset, rng, gain=0.028 if event == "footsteps" else 0.018)
        if event == "fruit_roll":
            add_noise_burst(out, at + 0.2, 0.75, 0.009, rng, cutoff=420, shape="bell")
    elif event in {"tape_peel", "zipper"}:
        add_noise_burst(out, at, 1.25 if event == "tape_peel" else 0.8,
                        0.018 if event == "tape_peel" else 0.014,
                        rng, cutoff=6000, highpass=800, shape="bell")
    elif event in {"kitchen_clink", "evidence_bag", "paper", "file_slide", "cloth_rustle",
                   "radio_hush", "wind", "murmur", "lab_fan"}:
        duration = {"kitchen_clink": 0.09, "evidence_bag": 0.5, "paper": 0.42,
                    "file_slide": 0.7, "cloth_rustle": 0.55, "radio_hush": 0.8,
                    "wind": 1.2, "murmur": 0.7, "lab_fan": 1.4}[event]
        gain = {"kitchen_clink": 0.025, "evidence_bag": 0.016, "paper": 0.013,
                "file_slide": 0.016, "cloth_rustle": 0.012, "radio_hush": 0.006,
                "wind": 0.009, "murmur": 0.006, "lab_fan": 0.006}[event]
        cutoff = 4200 if event == "kitchen_clink" else (600 if event in {"wind", "lab_fan"} else 2800)
        add_noise_burst(out, at, duration, gain, rng, cutoff=cutoff,
                        highpass=180 if event in {"paper", "cloth_rustle", "evidence_bag"} else None,
                        shape="bell")
        if event == "kitchen_clink":
            add_tone(out, at, 0.11, 0.014, 1200, 760, rng)
    elif event == "phone_buttons":
        for offset, freq in ((0.0, 820), (0.38, 990), (0.78, 730)):
            add_click(out, at + offset, rng, gain=0.035, f=freq)
    elif event == "phone_connect":
        add_tone(out, at, 0.28, 0.014, 430, 390, rng)
    elif event == "phone_bell":
        add_tone(out, at, 0.52, 0.018, 660, 730, rng)
        add_tone(out, at + 0.65, 0.52, 0.018, 660, 730, rng)
    elif event == "distant_siren":
        add_tone(out, at, 1.7, 0.009, 500, 720, rng)
        add_tone(out, at + 1.7, 1.5, 0.009, 720, 510, rng)
    elif event == "electronic_beep":
        add_tone(out, at, 0.14, 0.012, 850, 920, rng)
    elif event == "clock_tick":
        add_click(out, at, rng, gain=0.014, f=1350)
        add_click(out, at + 0.95, rng, gain=0.011, f=1250)
    elif event == "pen_tap":
        add_click(out, at, rng, gain=0.022, f=950)
    elif event == "clock_stop":
        add_click(out, at, rng, gain=0.018, f=1100)
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
        rng = np.random.default_rng(20261114 + index)
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
        "generation": "build_sfx.py deterministic seed 20261114+shot index",
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
