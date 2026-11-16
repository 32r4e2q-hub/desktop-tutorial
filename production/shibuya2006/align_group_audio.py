#!/usr/bin/env python3
"""Cut the three-shot TTS sources at real word boundaries found by ASR.

Why this exists
---------------
``prepare_group_audio.py`` guesses the two internal boundaries from silent pauses
plus a character-count prior. The 2026-11-16 evidence run showed the guess is not
reliable: G08 got cut between “可法庭的争议” and “才刚刚开始”, so S23 lost its last
six characters and S24 opened with them. Silence is not the same thing as a sentence
boundary — a narrator pauses inside a sentence and sometimes runs two sentences
together.

This script asks the model where the words actually are. It transcribes the whole
group once with word timestamps, aligns the known script to those words, and cuts at
the start of the word that begins each sentence. It still produces **candidates**:
``status`` stays ``asr_boundary_candidate`` and every clip must pass the independent
second-pass transcript in ``transcribe_audio_candidates.py`` (or a human listen)
before it can enter ``audio/manifest.json``.

Missing groups are never filled with silence, another voice, or the old script.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

from transcribe_audio_candidates import (
    HERE, ROOT, decode_float32, load_model, measured_seconds, normalize,
)

WORK = ROOT / "work/shibuya2006/audio_candidates"
PRE_ROLL = 0.06        # keep the consonant onset that starts the sentence
MIN_CLIP = 1.5


def group_words(model, path: Path, language: str) -> list:
    samples = decode_float32(path)
    segments, _info = model.transcribe(
        samples, language=language, beam_size=5, word_timestamps=True,
        vad_filter=False, condition_on_previous_text=False,
    )
    return [word for segment in segments for word in (segment.words or [])]


def char_spans(words: list) -> tuple[str, list[tuple[float, float]]]:
    """Normalised character stream of the ASR result, with the time span of each char."""
    chars: list[str] = []
    spans: list[tuple[float, float]] = []
    for word in words:
        for character in normalize(word.word):
            chars.append(character)
            spans.append((float(word.start), float(word.end)))
    return "".join(chars), spans


def nearest_match(mapping: dict[int, int], index: int, limit: int) -> int | None:
    """Map an expected character index to the ASR stream, walking forward then back."""
    for offset in range(0, limit):
        if index + offset in mapping:
            return mapping[index + offset]
        if index - offset in mapping:
            return mapping[index - offset]
    return None


def boundaries_for(texts: list[str], heard: str, spans: list[tuple[float, float]],
                   duration: float) -> tuple[list[float], list[dict], int]:
    expected = "".join(normalize(text) for text in texts)
    matcher = difflib.SequenceMatcher(None, expected, heard, autojunk=False)
    mapping: dict[int, int] = {}
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            mapping[block.a + offset] = block.b + offset

    cuts = [0.0]
    evidence = []
    cursor = 0
    for text in texts[:-1]:
        cursor += len(normalize(text))
        heard_index = nearest_match(mapping, cursor, max(1, len(heard)))
        if heard_index is None:
            evidence.append({"expected_char": cursor, "asr_char": None, "time": None})
            cuts.append(cuts[-1])
            continue
        start, end = spans[heard_index]
        cut = max(0.0, start - PRE_ROLL)
        evidence.append({"expected_char": cursor, "asr_char": heard_index,
                         "time": round(start, 3), "cut": round(min(cut, duration), 3),
                         "word_end": round(end, 3)})
        cuts.append(min(cut, duration))
    cuts.append(duration)
    # Guarantee a usable window per shot; otherwise the caller must fall back.
    for left, right in zip(cuts, cuts[1:]):
        if right - left < MIN_CLIP:
            raise ValueError(f"ASR boundaries produce a {right - left:.3f}s clip")
    return cuts, evidence, len(mapping)


def cut_clip(source: Path, dest: Path, start: float, end: float) -> float:
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-ss", f"{start:.6f}", "-t", f"{end - start:.6f}",
        "-i", str(source), "-af",
        "silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.06,"
        "areverse,silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.06,areverse",
        "-ar", "48000", "-ac", "1", "-c:a", "libmp3lame", "-q:a", "2", str(dest),
    ], check=True)
    seconds = measured_seconds(dest)
    if seconds is None:
        raise RuntimeError(f"ffprobe could not measure {dest}")
    return seconds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=None)
    parser.add_argument("--language", default="zh")
    args = parser.parse_args(argv)

    import transcribe_audio_candidates as transcribe
    model_size = args.model or transcribe.DEFAULT_MODEL
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    manifest = json.loads((HERE / "audio/groups/manifest.json").read_text(encoding="utf-8"))
    shots = {shot["id"]: shot for shot in story["shots"]}
    WORK.mkdir(parents=True, exist_ok=True)

    model = load_model(model_size)
    report = {
        "status": "asr_boundary_candidate",
        "method": "faster-whisper word timestamps; script aligned to words; cuts at word onsets",
        "voice": story["narration_spec"]["voice_id"],
        "policy": "Candidates only. Every clip still needs the independent second-pass "
                  "transcript (or a human listen) before audio/manifest.json is written.",
        "groups": [],
        "clips": [],
        "missing": [],
    }

    for group in manifest["groups"]:
        if group["status"] != "generated":
            report["missing"].append({"id": group["id"], "reason": group["status"],
                                      "shots": group["shots"]})
            continue
        source = HERE / "audio/groups" / group["file"]
        if not source.is_file():
            report["missing"].append({"id": group["id"], "reason": "file missing",
                                      "shots": group["shots"]})
            continue
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != group["sha256"]:
            raise RuntimeError(f"{group['id']}: source changed after TTS; regenerate, do not relabel")
        texts = [shots[sid]["narration"] for sid in group["shots"]]
        if "".join(texts) != group["text"]:
            raise RuntimeError(f"{group['id']}: script changed after TTS; regenerate, do not relabel")
        duration = measured_seconds(source)
        if duration is None:
            raise RuntimeError(f"{group['id']}: cannot measure duration")

        words = group_words(model, source, args.language)
        heard, spans = char_spans(words)
        try:
            cuts, evidence, matched = boundaries_for(texts, heard, spans, duration)
        except ValueError as exc:
            report["missing"].append({"id": group["id"], "reason": str(exc),
                                      "shots": group["shots"]})
            continue
        coverage = matched / max(1, len("".join(normalize(t) for t in texts)))
        report["groups"].append({
            "id": group["id"], "duration": round(duration, 3),
            "cuts": [round(cut, 3) for cut in cuts],
            "boundaries": evidence,
            "asr_char_coverage": round(coverage, 4),
            "heard": heard,
            "review": "pending_second_pass_asr_or_listening",
        })
        for shot_id, start, end in zip(group["shots"], cuts, cuts[1:]):
            dest = WORK / f"{shot_id}.mp3"
            seconds = cut_clip(source, dest, start, end)
            target = float(shots[shot_id]["duration"])
            report["clips"].append({
                "id": shot_id, "group": group["id"],
                "cut_start": round(start, 3), "cut_end": round(end, 3),
                "seconds": seconds, "target": target,
                "atempo_required": round(max(1.0, seconds / target), 4),
                "text": shots[shot_id]["narration"],
                "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                "file": str(dest.relative_to(ROOT)),
                "alignment_review": "pending; second-pass ASR or human listen required",
            })
        print(f"{group['id']}: cuts {[round(c, 2) for c in cuts]} "
              f"coverage {coverage:.3f}", flush=True)

    (HERE / "qa/group-tts-split-candidates.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ASR-guided candidates: {len(report['clips'])}/30; "
          f"unavailable groups: {len(report['missing'])}; NOT approved", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
