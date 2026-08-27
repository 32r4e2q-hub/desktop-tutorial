#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import re
import subprocess
from pathlib import Path

import edge_tts

VOICE = "zh-CN-YunxiNeural"
VOICE_RATE = "-3%"
MOVIE_VOLUME = 0.025
MAX_SUBTITLE_CHARS = 14


def run(command):
    print("+", " ".join(map(str, command[:12])), "..." if len(command) > 12 else "", flush=True)
    subprocess.run([str(value) for value in command], check=True)


def media_duration(path: Path) -> float:
    output = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        text=True,
    )
    return float(output.strip())


def parse_scenes(path: Path):
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header = next(index for index, line in enumerate(lines) if line.startswith("Scene Number,"))
    return [
        (float(row["Start Time (seconds)"]), float(row["End Time (seconds)"]))
        for row in csv.DictReader(lines[header:])
    ]


def visible_length(text: str) -> int:
    return len(re.sub(r"[^\u3400-\u9fffA-Za-z0-9]", "", text))


def split_subtitle_phrases(text: str, limit: int = MAX_SUBTITLE_CHARS):
    # Prefer semantic punctuation, then hard-wrap exceptionally long clauses.
    clauses = [part.strip() for part in re.findall(r"[^，。！？；：]+[，。！？；：]?", text) if part.strip()]
    output = []
    for clause in clauses:
        punctuation = clause[-1] if clause[-1] in "，。！？；：" else ""
        body = clause[:-1] if punctuation else clause
        while visible_length(body) > limit:
            cut = min(limit, len(body))
            output.append(body[:cut])
            body = body[cut:]
        if body or punctuation:
            output.append(body + punctuation)
    return output or [text]


def cue_subtitle_timeline(cues, cue_durations):
    timeline = []
    cursor = 0.0
    for cue, duration in zip(cues, cue_durations):
        phrases = split_subtitle_phrases(cue["text"])
        weights = [max(2, visible_length(phrase)) + 0.8 for phrase in phrases]
        scale = duration / sum(weights)
        phrase_start = cursor
        for index, (phrase, weight) in enumerate(zip(phrases, weights)):
            phrase_end = cursor + duration if index == len(phrases) - 1 else phrase_start + weight * scale
            timeline.append((phrase_start, phrase_end, phrase))
            phrase_start = phrase_end
        cursor += duration
    return timeline


def ass_time(seconds):
    hours = int(seconds // 3600)
    seconds -= hours * 3600
    minutes = int(seconds // 60)
    seconds -= minutes * 60
    return f"{hours}:{minutes:02d}:{seconds:05.2f}"


def write_ass(path: Path, timeline):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Narration,Noto Sans CJK SC,39,&H00FFFFFF,&H000000FF,&H00101010,&H78000000,1,0,0,0,100,100,0,0,1,2.5,0,2,55,55,48,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    rows = []
    for start, end, text in timeline:
        text = text.replace("\\", "\\\\").replace("{", "（").replace("}", "）").replace("\n", "")
        rows.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Narration,,0,0,0,,{text}")
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def subtract_used(start, end, used, padding=0.35):
    segments = [(start, end)]
    for used_start, used_end in sorted(used):
        blocked_start = used_start - padding
        blocked_end = used_end + padding
        revised = []
        for a, b in segments:
            if blocked_end <= a or blocked_start >= b:
                revised.append((a, b))
                continue
            if blocked_start > a:
                revised.append((a, min(b, blocked_start)))
            if blocked_end < b:
                revised.append((max(a, blocked_end), b))
        segments = revised
    return [(a, b) for a, b in segments if b - a >= 0.25]


def pick_shots(scenes, start, end, target, used):
    candidates = []
    for scene_start, scene_end in scenes:
        a, b = max(scene_start, start), min(scene_end, end)
        if b - a < 0.9:
            continue
        candidates.extend(
            (free_start, free_end)
            for free_start, free_end in subtract_used(a, b, used)
            if free_end - free_start >= 0.9
        )
    if not candidates:
        candidates = [segment for segment in subtract_used(start, end, used) if segment[1] - segment[0] >= 0.4]
    if not candidates:
        # Stay near the described event while still avoiding an exact repeat.
        candidates = [
            segment
            for segment in subtract_used(max(0, start - 12), end + 12, used)
            if segment[1] - segment[0] >= 0.4
        ]
    if not candidates:
        raise RuntimeError(f"No unused source footage remains for cue range {start}-{end}")

    count = max(1, math.ceil(target / 3.4))
    while True:
        indices = []
        for item in range(count):
            index = min(
                len(candidates) - 1,
                max(0, round((item + 0.5) * len(candidates) / count - 0.5)),
            )
            if index not in indices:
                indices.append(index)
        selected = [candidates[index] for index in indices]
        caps = [min(4.4, b - a - 0.03) for a, b in selected]
        if sum(caps) >= target - 0.01 or count >= len(candidates):
            break
        count += 1

    # If an event is mostly one long take, permit a longer excerpt rather than
    # filling from a different event.
    if sum(caps) < target:
        caps = [b - a - 0.03 for a, b in selected]

    durations = [0.0] * len(selected)
    remaining = target
    active = set(range(len(selected)))
    while active and remaining > 1e-6:
        share = remaining / len(active)
        saturated = False
        for index in list(active):
            room = caps[index] - durations[index]
            addition = min(share, room)
            durations[index] += addition
            remaining -= addition
            if room <= share + 1e-6:
                active.remove(index)
                saturated = True
        if not saturated and active:
            for index in active:
                durations[index] += remaining / len(active)
            remaining = 0

    shots = []
    for (a, b), duration in zip(selected, durations):
        if duration < 0.12:
            continue
        clip_start = a + max(0, (b - a - duration) / 2)
        shots.append((clip_start, clip_start + duration))
    delta = target - sum(b - a for a, b in shots)
    if shots and abs(delta) > 0.001:
        shots[-1] = (shots[-1][0], min(end, shots[-1][1] + delta))
    return shots


async def generate_cue_tts(sections, directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    total = sum(len(section["cues"]) for section in sections)
    completed = 0
    for section_index, section in enumerate(sections, 1):
        for cue_index, cue in enumerate(section["cues"], 1):
            completed += 1
            target = directory / f"section_{section_index:02d}_cue_{cue_index:02d}.mp3"
            if target.exists() and target.stat().st_size:
                continue
            print(f"Generating Yunxi cue {completed}/{total}: {cue['text']}", flush=True)
            for attempt in range(4):
                try:
                    communication = edge_tts.Communicate(
                        cue["text"], VOICE, rate=VOICE_RATE, volume="+0%"
                    )
                    await communication.save(str(target))
                    break
                except Exception:
                    if attempt == 3:
                        raise
                    await asyncio.sleep(2**attempt)
            await asyncio.sleep(0.12)


def build_section_audio(section_index, cue_paths, directory: Path):
    concat_list = directory / f"section_{section_index:02d}_audio.txt"
    concat_list.write_text(
        "\n".join(f"file '{path.resolve().as_posix()}'" for path in cue_paths) + "\n",
        encoding="utf-8",
    )
    output = directory / f"section_{section_index:02d}.wav"
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list,
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            output,
        ]
    )
    return output


def render_section(
    index, section, scenes, source: Path, tts_directory: Path, directory: Path, used_intervals
):
    output = directory / f"section_{index:02d}.mp4"
    ass = directory / f"section_{index:02d}.ass"
    cue_paths = [
        tts_directory / f"section_{index:02d}_cue_{cue_index:02d}.mp3"
        for cue_index in range(1, len(section["cues"]) + 1)
    ]
    cue_durations = [media_duration(path) for path in cue_paths]
    narration_audio = build_section_audio(index, cue_paths, tts_directory)
    section_duration = media_duration(narration_audio)

    # Keep the final cue exactly aligned with the decoded, concatenated audio.
    cue_durations[-1] += section_duration - sum(cue_durations)
    write_ass(ass, cue_subtitle_timeline(section["cues"], cue_durations))

    shots = []
    edl_rows = []
    output_cursor = 0.0
    for cue_index, (cue, cue_duration) in enumerate(zip(section["cues"], cue_durations), 1):
        cue_shots = []
        ranges = cue["ranges"]
        per_range = cue_duration / len(ranges)
        for start, end in ranges:
            cue_shots.extend(
                pick_shots(
                    scenes, float(start), float(end), per_range, used_intervals
                )
            )
        cue_total = sum(b - a for a, b in cue_shots)
        if cue_shots:
            cue_shots[-1] = (
                cue_shots[-1][0],
                cue_shots[-1][1] + cue_duration - cue_total,
            )
        for source_in, source_out in cue_shots:
            if any(
                source_in < used_end and source_out > used_start
                for used_start, used_end in used_intervals
            ):
                raise RuntimeError(
                    f"Duplicate source interval detected: {source_in}-{source_out}"
                )
            used_intervals.append((source_in, source_out))
            duration = source_out - source_in
            shots.append((source_in, source_out))
            edl_rows.append(
                {
                    "section": index,
                    "cue": cue_index,
                    "source_in": round(source_in, 3),
                    "source_out": round(source_out, 3),
                    "output_in": round(output_cursor, 3),
                    "output_out": round(output_cursor + duration, 3),
                    "narration": cue["text"],
                }
            )
            output_cursor += duration

    with (directory / f"section_{index:02d}_edl.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=edl_rows[0].keys())
        writer.writeheader()
        writer.writerows(edl_rows)

    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for source_in, source_out in shots:
        command += [
            "-ss",
            f"{source_in:.3f}",
            "-t",
            f"{source_out-source_in:.3f}",
            "-i",
            str(source),
        ]
    command += ["-i", str(narration_audio)]

    filters, pairs = [], []
    for shot_index, (source_in, source_out) in enumerate(shots):
        duration = source_out - source_in
        filters.append(
            f"[{shot_index}:v]trim=duration={duration:.4f},setpts=PTS-STARTPTS,"
            "crop=iw:ih-114:0:60,scale=1280:-2:flags=lanczos,"
            "pad=1280:720:0:(oh-ih)/2:black,drawbox=x=0:y=0:w=iw:h=90:color=black:t=fill,"
            f"setsar=1,fps=24,format=yuv420p[v{shot_index}]"
        )
        filters.append(
            f"[{shot_index}:a]atrim=duration={duration:.4f},"
            f"asetpts=PTS-STARTPTS,aresample=44100[a{shot_index}]"
        )
        pairs.append(f"[v{shot_index}][a{shot_index}]")
    filters.append("".join(pairs) + f"concat=n={len(shots)}:v=1:a=1[vcat][acat]")
    ass_name = str(ass).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    filters.append(f"[vcat]subtitles=filename='{ass_name}'[vout]")
    narration_index = len(shots)
    filters.append(
        f"[{narration_index}:a]atrim=duration={section_duration:.4f},"
        "asetpts=PTS-STARTPTS,aresample=44100[narr]"
    )
    filters.append(
        f"[acat]volume={MOVIE_VOLUME}[movie];[movie][narr]"
        "amix=inputs=2:duration=first:weights=1 1:normalize=0,"
        "alimiter=limit=0.96[aout]"
    )
    command += [
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-b:v",
        "1100k",
        "-maxrate",
        "1450k",
        "-bufsize",
        "2200k",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "24",
        "-g",
        "48",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        "-movflags",
        "+faststart",
        "-t",
        f"{section_duration:.4f}",
        str(output),
    ]
    print(
        f"Rendering aligned section {index}: {section_duration:.1f}s / "
        f"{len(section['cues'])} cues / {len(shots)} shots",
        flush=True,
    )
    run(command)
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--scenes", required=True, type=Path)
    parser.add_argument("--narration", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    args.work.mkdir(parents=True, exist_ok=True)
    sections = json.loads(args.narration.read_text(encoding="utf-8"))
    tts_directory = args.work / "tts"
    render_directory = args.work / "render"
    render_directory.mkdir(parents=True, exist_ok=True)

    asyncio.run(generate_cue_tts(sections, tts_directory))
    scenes = parse_scenes(args.scenes)
    outputs = []
    used_intervals = []
    for index, section in enumerate(sections, 1):
        outputs.append(
            render_section(
                index,
                section,
                scenes,
                args.source,
                tts_directory,
                render_directory,
                used_intervals,
            )
        )

    concat_list = render_directory / "sections.txt"
    concat_list.write_text(
        "\n".join(f"file '{path.resolve().as_posix()}'" for path in outputs) + "\n",
        encoding="utf-8",
    )
    raw_output = args.work / "raw.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list,
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            raw_output,
        ]
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            raw_output,
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-c:v",
            "copy",
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "44100",
            "-movflags",
            "+faststart",
            args.output,
        ]
    )
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            args.output,
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-f",
            "null",
            "-",
        ]
    )
    print(
        f"FINAL: {args.output} / {media_duration(args.output):.2f}s / "
        f"{args.output.stat().st_size/1048576:.1f}MB"
    )


if __name__ == "__main__":
    main()
