#!/usr/bin/env python3
from __future__ import annotations
import argparse, asyncio, csv, json, math, re, subprocess
from pathlib import Path
import edge_tts


def run(cmd):
    print("+", " ".join(map(str, cmd[:12])), "..." if len(cmd) > 12 else "", flush=True)
    subprocess.run([str(x) for x in cmd], check=True)


def media_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path)
    ], text=True)
    return float(out.strip())


def parse_scenes(path: Path):
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Scene Number,"))
    return [
        (float(row["Start Time (seconds)"]), float(row["End Time (seconds)"]))
        for row in csv.DictReader(lines[start:])
    ]


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[。！？])", text) if s.strip()]


def subtitle_timeline(text, duration):
    sentences = split_sentences(text)
    weights = [max(5, len(re.sub(r"[^\u3400-\u9fffA-Za-z0-9]", "", s))) + 1.8 for s in sentences]
    scale = duration / sum(weights)
    output, current = [], 0.0
    for i, (sentence, weight) in enumerate(zip(sentences, weights)):
        end = duration if i == len(sentences) - 1 else current + weight * scale
        output.append((current, end, sentence))
        current = end
    return output


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
Style: Narration,Noto Sans CJK SC,37,&H00FFFFFF,&H000000FF,&H00101010,&H78000000,1,0,0,0,100,100,0,0,1,2.4,0,2,45,45,48,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    rows = []
    for start, end, text in timeline:
        text = text.replace("\\", "\\\\").replace("{", "（").replace("}", "）").replace("\n", "")
        rows.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Narration,,0,0,0,,{text}")
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def pick_shots(scenes, start, end, target):
    candidates = []
    for scene_start, scene_end in scenes:
        a, b = max(scene_start, start), min(scene_end, end)
        if b - a >= 1.0:
            candidates.append((a, b))
    if not candidates:
        return [(start, start + target)]
    count = max(1, math.ceil(target / 3.7))
    while True:
        indices = []
        for j in range(count):
            idx = min(len(candidates) - 1, max(0, round((j + 0.5) * len(candidates) / count - 0.5)))
            if idx not in indices:
                indices.append(idx)
        selected = [candidates[i] for i in indices]
        caps = [min(4.6, b - a - 0.04) for a, b in selected]
        if sum(caps) >= target - 0.01 or count >= len(candidates):
            break
        count += 1
    durations = [0.0] * len(selected)
    remaining, active = target, set(range(len(selected)))
    while active and remaining > 1e-6:
        share = remaining / len(active)
        saturated = False
        for i in list(active):
            room = caps[i] - durations[i]
            addition = min(share, room)
            durations[i] += addition
            remaining -= addition
            if room <= share + 1e-6:
                active.remove(i)
                saturated = True
        if not saturated and active:
            for i in active:
                durations[i] += remaining / len(active)
            remaining = 0
    shots = []
    for (a, b), duration in zip(selected, durations):
        if duration >= 0.15:
            clip_start = a + max(0, (b - a - duration) / 2)
            shots.append((clip_start, clip_start + duration))
    delta = target - sum(b - a for a, b in shots)
    if shots and abs(delta) > 0.001:
        shots[-1] = (shots[-1][0], shots[-1][1] + delta)
    return shots


async def generate_tts(sections, directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    for index, section in enumerate(sections, 1):
        target = directory / f"section_{index:02d}.mp3"
        if target.exists() and target.stat().st_size:
            continue
        print(f"Generating Yunxi narration {index}/{len(sections)}", flush=True)
        for attempt in range(4):
            try:
                communicate = edge_tts.Communicate(
                    section["text"], "zh-CN-YunxiNeural", rate="-3%", volume="+0%"
                )
                await communicate.save(str(target))
                break
            except Exception:
                if attempt == 3:
                    raise
                await asyncio.sleep(2 ** attempt)


def render_section(index, section, scenes, source: Path, audio: Path, directory: Path):
    output = directory / f"section_{index:02d}.mp4"
    ass = directory / f"section_{index:02d}.ass"
    duration = media_duration(audio)
    timeline = subtitle_timeline(section["text"], duration)
    write_ass(ass, timeline)
    shots = []
    for start, end, ratio in section["blocks"]:
        shots.extend(pick_shots(scenes, float(start), float(end), duration * float(ratio)))
    total = sum(b - a for a, b in shots)
    shots[-1] = (shots[-1][0], shots[-1][1] + duration - total)

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for a, b in shots:
        cmd += ["-ss", f"{a:.3f}", "-t", f"{b-a:.3f}", "-i", str(source)]
    cmd += ["-i", str(audio)]
    filters, pairs = [], []
    for i, (a, b) in enumerate(shots):
        d = b - a
        filters.append(
            f"[{i}:v]trim=duration={d:.4f},setpts=PTS-STARTPTS,"
            "crop=iw:ih-114:0:60,scale=1280:-2:flags=lanczos,"
            "pad=1280:720:0:(oh-ih)/2:black,drawbox=x=0:y=0:w=iw:h=90:color=black:t=fill,"
            f"setsar=1,fps=24,format=yuv420p[v{i}]"
        )
        filters.append(
            f"[{i}:a]atrim=duration={d:.4f},asetpts=PTS-STARTPTS,aresample=44100[a{i}]"
        )
        pairs.append(f"[v{i}][a{i}]")
    filters.append("".join(pairs) + f"concat=n={len(shots)}:v=1:a=1[vcat][acat]")
    ass_name = str(ass).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    filters.append(f"[vcat]subtitles=filename='{ass_name}'[vout]")
    n = len(shots)
    filters.append(f"[{n}:a]atrim=duration={duration:.4f},asetpts=PTS-STARTPTS,aresample=44100[narr]")
    filters.append(
        "[acat]volume=0.11[movie];[movie][narr]"
        "amix=inputs=2:duration=first:weights=1 1:normalize=0,alimiter=limit=0.96[aout]"
    )
    cmd += [
        "-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "veryfast", "-b:v", "1100k", "-maxrate", "1450k",
        "-bufsize", "2200k", "-pix_fmt", "yuv420p", "-r", "24", "-g", "48",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-movflags", "+faststart",
        "-t", f"{duration:.4f}", str(output)
    ]
    print(f"Rendering section {index}: {duration:.1f}s / {len(shots)} shots", flush=True)
    run(cmd)
    return output


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--scenes", required=True, type=Path)
    ap.add_argument("--narration", required=True, type=Path)
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    sections = json.loads(args.narration.read_text(encoding="utf-8"))
    tts_dir, render_dir = args.work / "tts", args.work / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    asyncio.run(generate_tts(sections, tts_dir))
    scenes = parse_scenes(args.scenes)
    outputs = []
    for index, section in enumerate(sections, 1):
        outputs.append(render_section(index, section, scenes, args.source, tts_dir / f"section_{index:02d}.mp3", render_dir))
    concat_list = render_dir / "sections.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in outputs) + "\n")
    raw = args.work / "raw.mp4"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", "-movflags", "+faststart", raw])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", raw,
        "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "128k",
        "-ar", "44100", "-movflags", "+faststart", args.output
    ])
    run(["ffmpeg", "-v", "error", "-i", args.output, "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"])
    print(f"FINAL: {args.output} / {media_duration(args.output):.2f}s / {args.output.stat().st_size/1048576:.1f}MB")


if __name__ == "__main__":
    main()
