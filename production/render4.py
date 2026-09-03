#!/usr/bin/env python3
"""渲染合成（v4）：
- 音频：逐句 WAV 拼接，每句 12ms 淡入 + 0.15s 停顿（消除抢话与破音）。
- 视频：清理后的片段按"句子+停顿"时长做温和变速（setpts）后拼接。
- 字幕：ASS 时间轴按实测语音时长走（语音念完字幕同时消失）。
- 总装：段落重编码拼接 + 悬疑 BGM 混音（侧链压缩 + 响度标准化）。
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FF = "/usr/local/bin/ffmpeg"
FONTNAME = os.environ.get("FONTNAME", "Noto Sans CJK SC")
FONTS_DIR = os.environ.get("FONTS_DIR", "")
GAP = 0.15
BGM_VOLUME = 0.05
BGM_LOOP_SECONDS = 96.0
SINGLE_LINE_SUBTITLE_CHARS = 24
PAD_Y = 46
FPS = 24


def run(cmd):
    print("+", " ".join(map(str, cmd[:14])), "..." if len(cmd) > 14 else "", flush=True)
    subprocess.run([str(c) for c in cmd], check=True)


def dur(path):
    out = subprocess.run([FF, "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True).stderr
    m = re.search(r"Duration:\s*(\d+):(\d+):([0-9.]+)", out)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def visible_length(t):
    return len(re.sub(r"[^\u3400-\u9fffA-Za-z0-9]", "", t))


def split_clauses(t):
    return [p.strip() for p in re.findall(r"[^，。！？；：]+[，。！？；：]?", t) if p.strip()] or [t]


def fmt(t):
    L = max(1, visible_length(t))
    fs = max(34, min(42, int(1120 / L))) if L > SINGLE_LINE_SUBTITLE_CHARS else 42
    return f"[[SINGLE:{fs}]]{t}"


def ass_time(s):
    h = int(s // 3600)
    s -= h * 3600
    m = int(s // 60)
    s -= m * 60
    return f"{h}:{m:02d}:{s:05.2f}"


def write_ass(path, events):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Narration,""" + FONTNAME + """,42,&H00FFFFFF,&H000000FF,&H00101010,&H78000000,1,0,0,0,100,100,0,0,1,2.8,0,2,40,40,18,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    rows = []
    for start, end, text in events:
        m = re.match(r"^\[\[SINGLE:(\d+)\]\]", text)
        fs = m.group(1) if m else "42"
        if m:
            text = text[m.end():]
        text = text.replace("\\", "\\\\").replace("{", "（").replace("}", "）").replace("\n", "")
        rows.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Narration,,0,0,0,,{{\\q2\\fs{fs}}}{text}")
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def build_section_audio(idx, wavs, outdir):
    inputs = []
    for w in wavs:
        inputs += ["-i", str(w)]
    n = len(wavs)
    parts = [f"[{i}:a]aresample=44100,aformat=sample_fmts=s16p:channel_layouts=stereo,"
             f"afade=t=in:st=0:d=0.012,apad=pad_dur={GAP}[a{i}]" for i in range(n)]
    parts.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[out]")
    out = outdir / f"section_{idx:02d}.wav"
    run([FF, "-y", "-v", "error"] + inputs + ["-filter_complex", ";".join(parts),
                                              "-map", "[out]", "-c:a", "pcm_s16le", str(out)])
    return out


def render_section(idx, records, clean_dir, render_dir, speech):
    clips = [clean_dir / f"clip_{r['gi']:03d}.mp4" for r in records]
    wavs = [Path(r["wav"]) for r in records]
    ass = render_dir / f"section_{idx:02d}.ass"
    out = render_dir / f"section_{idx:02d}.mp4"

    adurs = [dur(w) for w in wavs]
    cdurs = [dur(c) for c in clips]
    narration_wav = build_section_audio(idx, wavs, render_dir)
    section_duration = dur(narration_wav)
    out_durs = [a + GAP for a in adurs]

    events = []
    cursor = 0.0
    for r, sp, od in zip(records, [speech[r["gi"]] for r in records], out_durs):
        clauses = split_clauses(r["text"])
        weights = [max(3, visible_length(cl)) + 1.0 for cl in clauses]
        scale = sp / sum(weights)
        cs = cursor
        for cl, w in zip(clauses, weights):
            events.append((cs, cs + w * scale, fmt(cl)))
            cs += w * scale
        cursor += od
    write_ass(ass, events)

    command = [FF, "-y", "-v", "error"]
    for c in clips:
        command += ["-i", str(c)]
    command += ["-i", str(narration_wav)]

    filters = []
    for i, r in enumerate(records):
        sf = out_durs[i] / cdurs[i]
        if not 0.5 <= sf <= 1.5:
            raise RuntimeError(f"clip {r['gi']} retime {sf:.3f}")
        filters.append(f"[{i}:v]setpts=(PTS-STARTPTS)*{sf:.8f},fps={FPS},"
                       f"pad=1280:720:0:{PAD_Y}:black,setsar=1,trim=duration={out_durs[i]:.4f},"
                       f"format=yuv420p[v{i}]")
    filters.append("".join(f"[v{i}]" for i in range(len(records))) +
                   f"concat=n={len(records)}:v=1:a=0[vcat]")
    ass_name = str(ass).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    sub_args = f"subtitles=filename='{ass_name}'" + (f":fontsdir={FONTS_DIR}" if FONTS_DIR else "")
    filters.append(f"[vcat]{sub_args}[vout]")
    ni = len(records)
    filters.append(f"[{ni}:a]atrim=duration={section_duration:.4f},asetpts=PTS-STARTPTS,"
                   "aresample=44100,highpass=f=70,lowpass=f=12000,"
                   "equalizer=f=160:t=q:w=1:g=2,"
                   "acompressor=threshold=0.125:ratio=2.2:attack=15:release=140:makeup=1.4[narr]")
    command += ["-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[narr]",
                "-c:v", "libx264", "-preset", "veryfast", "-b:v", "1000k",
                "-maxrate", "1400k", "-bufsize", "2800k", "-pix_fmt", "yuv420p",
                "-r", str(FPS), "-g", "48", "-c:a", "aac", "-b:a", "96k", "-ar", "44100",
                "-movflags", "+faststart", "-t", f"{section_duration:.4f}", str(out)]
    print(f"section {idx}: {section_duration:.1f}s / {len(records)} clips", flush=True)
    run(command)
    return out


def main():
    narr = json.load(open(ROOT / "work" / "production" / "narration_aligned.json", encoding="utf-8"))
    durs_raw = json.load(open(ROOT / "work" / "tts_src" / "durations.json", encoding="utf-8"))
    speech = {int(k): float(v) for k, v in durs_raw.items()}
    clean_dir = ROOT / "work" / "clean"
    tts_dir = ROOT / "work" / "production" / "tts"
    render_dir = ROOT / "work" / "production" / "render4"
    render_dir.mkdir(parents=True, exist_ok=True)

    sections = []
    gi = 0
    for si, sec in enumerate(narr, 1):
        recs = []
        for ci, cue in enumerate(sec["cues"], 1):
            wav = tts_dir / f"section_{si:02d}_cue_{ci:02d}_clip_01.wav"
            recs.append({"gi": gi, "wav": str(wav), "text": cue["text"]})
            gi += 1
        sections.append(recs)

    outputs = []
    for si, recs in enumerate(sections, 1):
        outputs.append(render_section(si, recs, clean_dir, render_dir, speech))

    concat_list = render_dir / "sections.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in outputs) + "\n",
                           encoding="utf-8")
    raw = ROOT / "work" / "raw4.mp4"
    run([FF, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list),
         "-c:v", "libx264", "-preset", "veryfast", "-b:v", "1000k", "-maxrate", "1400k", "-bufsize", "2800k",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-ar", "44100", "-movflags", "+faststart", str(raw)])

    sys.path.insert(0, str(ROOT / "production"))
    from generate_horror_bgm import generate_horror_bgm
    bgm = ROOT / "work" / "bgm4.wav"
    generate_horror_bgm(bgm, BGM_LOOP_SECONDS)

    out = ROOT / "output" / "无名之众_10分钟电影解说_720p.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    mix = ("[0:a]asplit=2[main][side];[1:a]volume=0.05[bg];"
           "[bg][side]sidechaincompress=threshold=0.02:ratio=3:attack=25:release=350[ducked];"
           "[main][ducked]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
    run([FF, "-y", "-v", "error", "-i", str(raw), "-stream_loop", "-1", "-i", str(bgm),
         "-filter_complex", mix, "-map", "0:v:0", "-map", "[aout]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "96k", "-ar", "44100", "-movflags", "+faststart", str(out)])
    run([FF, "-v", "error", "-i", str(out), "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"])
    print(f"FINAL: {out} / {dur(out):.2f}s / {out.stat().st_size/1048576:.1f}MB")


if __name__ == "__main__":
    main()
