#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""金大斗案 · 最终装配（180 秒抖音版）。

输入：
  production/kimdaedoo/results.json  —— 30 镜的 CDN 地址、字节数、SHA-256
  production/kimdaedoo/story.json    —— 30 镜旁白、提示词、时间轴
输出（work/kimdaedoo-final/）：
  final.mp4            180.000 秒 / 1920×1080 / 30fps / 中文旁白 + 原创悬疑 BGM
  captions.srt         按 TTS 实际时窗切分的字幕
  technical-report.json 逐镜哈希、音画对位、QC、响度
  final-contact.jpg    16 帧成片接触表
  final-per-slot.jpg   30 个镜头窗口中点帧（权威目检表）

动作：
  ① 下载 30 镜并逐字节校验 SHA-256（任何一条不符立即停，绝不带病出片）
  ② edge-tts 中文男声（Yunjian，低沉；pitch -4Hz）逐镜配音
  ③ 每镜旁白压进 6 秒窗口（超长才加速，不剪字）
  ④ 30 × 6 秒硬切拼接，字幕按真实语音时窗烧录
  ⑤ 原创悬疑 BGM（程序生成，无版权问题）+ 响度归一
  ⑥ 程序化 QC：时长/解码/分辨率/响度/黑帧
  ⑦ 交付文件落到 production/kimdaedoo/delivery/final/；Release 由工作流发布

退出码：0 成功；1 任何校验不过 / 素材不全。
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STORY = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
RESULTS = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
SHOTS = sorted(STORY["shots"], key=lambda s: int(s["id"][1:]))
assert len(SHOTS) == 30, "必须恰好 30 镜"
assert sum(s["duration"] for s in SHOTS) == 180, "30 × 6 秒必须等于 180"

OUT = ROOT / "work/kimdaedoo-final"
CLIPS = OUT / "clips"
TTS = OUT / "tts"
for folder in (OUT, CLIPS, TTS):
    folder.mkdir(parents=True, exist_ok=True)

VOICE = "zh-CN-YunjianNeural"      # 中文男声·小说演播，低沉、克制，适合悬疑
PITCH = "-4Hz"                      # 再压低一点，不靠怪腔怪调制造气氛
# 语速标定（2026-10-22 CI 实测，Yunjian +0%）：约 0.24 秒/字，标点会额外拖长。
# 用户的硬要求是「有片段就有解说」：每镜 6 秒都要被旁白铺满，不能念两三秒留一大段静默；
# 同时也绝不能顶出镜头窗。所以每镜做**双向对位**——太短就把语速放慢（-6%/-12%），
# 太长就提速（+6%…+30%），最后才用 atempo 兜底，绝不剪字。
BASE_RATE = "+0%"
MIN_LINE_S = 5.30                   # 铺满镜头：旁白至少 5.30 秒（起播留白 0.15 秒）
MAX_LINE_S = 5.85                   # 不能顶出窗口：最多 5.85 秒
SLOW_RATES = ["-6%", "-12%", "-18%", "-24%"]
FAST_RATES = ["+6%", "+12%", "+18%", "+24%", "+30%"]
LEAD_S = 0.15                       # 旁白相对镜头起点
W, H, FPS = 1920, 1080, 30
TOTAL_S = 180.0
BGM_VOLUME = 0.13
PRESET = os.getenv("KIMDAEDOO_PRESET", "slow")
WATERMARK = "AI动画情景重现"

def log(*args):
    print("[finalize]", *args, flush=True)


def die(message: str, code: int = 1) -> None:
    log("FATAL:", message)
    (OUT / "FATAL.txt").write_text(message + "\n", encoding="utf-8")
    raise SystemExit(code)


def sh(cmd, check=True, **kwargs):
    log("$", " ".join(str(c) for c in cmd)[:240])
    return subprocess.run([str(c) for c in cmd], check=check,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def ffprobe_duration(path: Path) -> float:
    result = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "json", str(path)])
    return float(json.loads(result.stdout)["format"]["duration"])


def find_cjk_font() -> str:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    found = [p for p in Path("/usr/share/fonts").rglob("NotoSansCJK*")
             if p.suffix in (".ttc", ".otf")] if Path("/usr/share/fonts").exists() else []
    if not found:
        die("找不到 Noto CJK 字体；请先 apt-get install fonts-noto-cjk")
    return str(found[0])


# ---------------------------------------------------------------- 0 素材新鲜度（防旧提示词素材混进成片）
def stale_shots() -> list[str]:
    """story.json 改过、但 results.json 里还是旧 request_hash 的镜头。

    2026-10-21 实测：提示词重写后，旧一轮生成仍可能先把 30/30 凑齐并触发 final，
    结果把上一版（有伪文字）的素材装进成片。素材的 request_hash 与当前
    story.json 算出来的不一致时，说明这条片子是旧提示词的产物，必须停下重新生成。
    """
    spec = importlib.util.spec_from_file_location("kimdaedoo_generate", HERE / "generate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stale = []
    for shot in SHOTS:
        row = RESULTS["shots"].get(shot["id"]) or {}
        recorded = row.get("request_hash")
        if recorded and recorded != module.request_hash(STORY, shot):
            stale.append(shot["id"])
    return stale


# ---------------------------------------------------------------- 1 下载 + 校验
def download(sid: str) -> Path:
    row = RESULTS["shots"].get(sid) or {}
    if row.get("status") != "completed" or not row.get("video_url") or not row.get("sha256"):
        die(f"{sid} 还没有完成的 Agnes 素材（status={row.get('status')}）")
    dest = CLIPS / f"{sid}.mp4"
    want = row["sha256"]
    if dest.is_file() and dest.stat().st_size == row.get("bytes") and sha256(dest) == want:
        log(f"  {sid} 已存在，校验通过")
        return dest
    last = None
    for attempt in range(4):
        try:
            request = urllib.request.Request(row["video_url"], headers={"User-Agent": "kimdaedoo-final/1.0"})
            with urllib.request.urlopen(request, timeout=300) as response, dest.open("wb") as handle:
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    handle.write(chunk)
            got = sha256(dest)
            if got != want:
                raise RuntimeError(f"sha256 不符: {got} != {want}")
            log(f"  {sid} OK {dest.stat().st_size:,} B")
            return dest
        except Exception as exc:
            last = exc
            log(f"  {sid} 下载第 {attempt + 1} 次失败：{exc}")
            time.sleep(5 * (attempt + 1))
    die(f"{sid} 下载/校验失败：{last}")


# ---------------------------------------------------------------- 2 TTS
def trim_silence(raw: Path, wav: Path) -> None:
    sh(["ffmpeg", "-y", "-v", "error", "-i", str(raw),
        "-af", "silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,"
               "areverse,silenceremove=start_periods=1:start_silence=0.02:"
               "start_threshold=-38dB,areverse",
        "-ar", "48000", "-ac", "2", str(wav)])


async def synth(text: str, rate: str, dest: Path) -> None:
    import edge_tts
    for attempt in range(4):
        try:
            communicate = edge_tts.Communicate(text, VOICE, rate=rate, pitch=PITCH)
            await communicate.save(str(dest))
            if dest.stat().st_size > 1000:
                return
        except Exception as exc:
            log(f"  TTS 第 {attempt + 1} 次失败：{exc}")
            await asyncio.sleep(2 + attempt * 2)
    raise RuntimeError(f"TTS 四次失败：{text[:20]}")


def synth_shot(shot: dict, rate: str) -> Path:
    sid = shot["id"]
    raw = TTS / f"{sid}.raw.mp3"
    wav = TTS / f"{sid}.wav"
    asyncio.run(synth(shot["narration"], rate, raw))
    trim_silence(raw, wav)
    return wav


def fit_speech(shot: dict) -> tuple[Path, float, str]:
    """把每镜旁白对到 [5.30, 5.85] 秒：短了就放慢，长了就提速，绝不剪字。"""
    sid = shot["id"]
    wav = synth_shot(shot, BASE_RATE)
    duration = ffprobe_duration(wav)
    if MIN_LINE_S <= duration <= MAX_LINE_S:
        return wav, duration, BASE_RATE
    best = (wav, duration, BASE_RATE)
    ladder = FAST_RATES if duration > MAX_LINE_S else SLOW_RATES
    for rate in ladder:
        wav = synth_shot(shot, rate)
        duration = ffprobe_duration(wav)
        if abs(duration - (MIN_LINE_S + MAX_LINE_S) / 2) < abs(best[1] - (MIN_LINE_S + MAX_LINE_S) / 2):
            best = (wav, duration, rate)
        if MIN_LINE_S <= duration <= MAX_LINE_S:
            log(f"  {sid} 对位 {duration:.2f}s @ {rate}")
            return wav, duration, rate
        log(f"  {sid} {rate} 仍 {duration:.2f}s，继续对位")
    wav, duration, rate = best
    if duration < MIN_LINE_S:
        # 已经放到最慢还偏短：如实记下（说明这句字数不够，不是剪辑问题）
        log(f"  {sid} COVERAGE_SHORT {duration:.2f}s @ {rate}（建议加字）")
        return wav, duration, rate
    # 极端情况才用 atempo；只压 1.0–1.18 倍，避免音色变形。
    target = MAX_LINE_S
    tempo = min(1.30, max(1.0, duration / target))
    fixed = TTS / f"{sid}.fit.wav"
    sh(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-filter:a", f"atempo={tempo:.4f}",
        "-ar", "48000", "-ac", "2", str(fixed)])
    duration = ffprobe_duration(fixed)
    return fixed, duration, f"{rate}+atempo{tempo:.2f}"


ASS_FONT = "Noto Sans CJK SC"
ASS_HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{ASS_FONT},54,&H00FFFFFF,&H000000FF,&H00000000,&H66000000,0,0,0,0,100,100,0,0,1,3.2,1.2,2,90,90,92,1
Style: Title,{ASS_FONT},92,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,2.5,3,8,80,80,96,1
Style: Title2,{ASS_FONT},50,&H0000FFFF,&H000000FF,&H00000000,&H99000000,0,0,0,0,100,100,0,0,1,2.5,2,8,80,80,210,1
Style: Mark,{ASS_FONT},30,&H66FFFFFF,&H000000FF,&H66000000,&H66000000,0,0,0,0,100,100,0,0,1,1.5,1,9,40,40,34,1
Style: End,{ASS_FONT},44,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,0,0,0,0,100,100,0,0,1,2.5,2,2,80,80,160,1
Style: End2,{ASS_FONT},28,&HCCFFFFFF,&H000000FF,&H00000000,&H99000000,0,0,0,0,100,100,0,0,1,2,1.5,2,80,80,104,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ass_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int(seconds % 3600 // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"


def ass_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def srt_ts(seconds: float) -> str:
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{int((seconds - int(seconds)) * 1000):03d}"


def split_caption(text: str) -> list[str]:
    parts = [p for p in re.split(r"(?<=[。；])", text) if p.strip()]
    chunks: list[str] = []
    for part in parts:
        part = part.strip()
        while len(part) > 16:
            cut = part.rfind("，", 0, 16)
            if cut < 7:
                cut = 16
            chunks.append(part[:cut + 1].strip())
            part = part[cut + 1:].strip()
        if part:
            chunks.append(part)
    return [c for c in chunks if c]


def build_subtitles(timeline: list[dict]) -> tuple[Path, Path]:
    """同时产出 SRT（交付/可编辑）与 ASS（烧录用，含标题卡/水印/片尾）。"""
    srt_lines, ass_events, index = [], [], 1
    # 常驻 AI 标识：整片都在，透明度约 40%
    ass_events.append(
        f"Dialogue: 1,{ass_time(0)},{ass_time(TOTAL_S)},Mark,,0,0,0,,{ass_text(WATERMARK)}"
    )
    # 片头标题
    ass_events.append(f"Dialogue: 3,{ass_time(0.6)},{ass_time(4.2)},Title,,0,0,0,,55天，17条人命")
    ass_events.append(f"Dialogue: 3,{ass_time(1.0)},{ass_time(4.2)},Title2,,0,0,0,,一条牛仔裤，揭开真相")
    # 片尾
    ass_events.append(
        f"Dialogue: 3,{ass_time(174.8)},{ass_time(TOTAL_S)},End,,0,0,0,,金大斗连环杀人案｜韩国 1975—1976"
    )
    ass_events.append(
        f"Dialogue: 3,{ass_time(175.4)},{ass_time(TOTAL_S)},End2,,0,0,0,,根据公开报道整理 · 部分画面为3D动画重现"
    )
    for row in timeline:
        chunks = split_caption(row["narration"])
        span = row["audio_end"] - row["audio_start"]
        total = sum(len(c) for c in chunks) or 1
        cursor = row["audio_start"]
        for chunk in chunks:
            end = cursor + span * len(chunk) / total
            srt_lines += [str(index), f"{srt_ts(cursor)} --> {srt_ts(end)}", chunk, ""]
            ass_events.append(
                f"Dialogue: 2,{ass_time(cursor)},{ass_time(end)},Caption,,0,0,0,,{ass_text(chunk)}"
            )
            index += 1
            cursor = end
    srt_path = OUT / "captions.srt"
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    ass_path = OUT / "overlay.ass"
    ass_path.write_text(ASS_HEADER + "\n".join(ass_events) + "\n", encoding="utf-8")
    return srt_path, ass_path


def make_bgm(duration: float) -> Path:
    """生成原创悬疑 BGM（程序合成，无版权问题）。

    2026-10-22 实测：这里原本是 `make_bgm(TOTAL_S)` 却从来没有定义过这个函数——
    出片在下载 30 镜、跑完 30 条配音之后，才在第 4/7 步抛 NameError 死掉，
    一次白跑 64 秒。现在真正接上 `电影解说工具包/generate_horror_bgm.py`。
    """
    module_path = ROOT / "电影解说工具包" / "generate_horror_bgm.py"
    if not module_path.is_file():
        die(f"找不到 BGM 生成器：{module_path}")
    spec = importlib.util.spec_from_file_location("kimdaedoo_bgm", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = OUT / "bgm.wav"
    module.generate_horror_bgm(output, duration)
    log(f"  BGM {output.name} {output.stat().st_size / 1e6:.1f} MB / {duration:.0f}s")
    return output


def render(timeline: list[dict], ass: Path, bgm: Path) -> Path:

    cmd = ["ffmpeg", "-y", "-v", "warning", "-stats"]
    cmd += ["-i", str(bgm)]
    for row in timeline:
        cmd += ["-i", str(row["wav"])]
    for row in timeline:
        cmd += ["-i", str(row["clip"])]
    audio0 = 1
    video0 = 1 + len(timeline)

    fg: list[str] = []
    fg.append(f"[0:a]atrim=duration={TOTAL_S},asetpts=PTS-STARTPTS,volume={BGM_VOLUME}[bgm]")
    for index, row in enumerate(timeline):
        delay = int(round(row["audio_start"] * 1000))
        fg.append(f"[{audio0 + index}:a]adelay={delay}|{delay},asetpts=PTS-STARTPTS[a{index}]")
    mix = "[bgm]" + "".join(f"[a{i}]" for i in range(len(timeline)))
    fg.append(f"{mix}amix=inputs={len(timeline) + 1}:duration=first:normalize=0,"
              f"loudnorm=I=-16:TP=-1.5:LRA=11[aout]")

    for index, row in enumerate(timeline):
        fg.append(
            f"[{video0 + index}:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},setsar=1,trim=duration=6,setpts=PTS-STARTPTS,fps={FPS},"
            f"eq=gamma=1.06:brightness=0.008:saturation=1.02,format=yuv420p[v{index}]"
        )
    concat = "".join(f"[v{i}]" for i in range(len(timeline)))
    fg.append(f"{concat}concat=n={len(timeline)}:v=1:a=0[vcat]")
    fg.append(f"[vcat]ass={ass},format=yuv420p[vsub]")
    fg.append(f"[vsub]fade=t=in:st=0:d=0.8,fade=t=out:st={TOTAL_S - 2.0}:d=2.0[vout]")

    final = OUT / "final.mp4"
    cmd += ["-filter_complex", ";".join(fg), "-map", "[vout]", "-map", "[aout]",
            "-t", str(TOTAL_S), "-c:v", "libx264", "-crf", "19", "-preset", PRESET,
            "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", str(final)]
    started = time.time()
    try:
        sh(cmd)
    except subprocess.CalledProcessError as exc:
        die("ffmpeg 合成失败：\n" + (exc.stderr or b"").decode("utf-8", "replace")[-5000:])
    log(f"  合成完成 {time.time() - started:.0f}s → {final.stat().st_size / 1e6:.1f} MB")
    return final


# ---------------------------------------------------------------- 6 QC
def qc(final: Path, timeline: list[dict], tts_total: float) -> dict:
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    decode_errors = [line for line in decode.stderr.decode("utf-8", "replace").splitlines() if line.strip()]
    probe = json.loads(sh(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                          str(final)]).stdout)
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    duration = float(probe["format"]["duration"])
    black = subprocess.run(["ffmpeg", "-v", "info", "-i", str(final), "-vf",
                            "blackdetect=d=0.5:pix_th=0.08", "-f", "null", "-"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    black_segments = re.findall(r"black_start:\s*([\d.]+)\s*black_end:\s*([\d.]+)",
                                black.stderr.decode("utf-8", "replace"))
    loud = subprocess.run(["ffmpeg", "-i", str(final), "-af", "ebur128", "-f", "null", "-"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    loud_text = loud.stderr.decode("utf-8", "replace")
    integrated = (re.findall(r"I:\s*(-?[\d.]+)\s*LUFS", loud_text) or ["?"])[-1]
    peak = (re.findall(r"Peak:\s*(-?[\d.]+)\s*dBFS", loud_text) or ["?"])[-1]

    qc_data = {
        "duration_s": round(duration, 3),
        "duration_ok": abs(duration - TOTAL_S) < 0.15,
        "width": int(video["width"]),
        "height": int(video["height"]),
        "fps": video.get("avg_frame_rate"),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "audio_sample_rate": int(audio.get("sample_rate", 0)),
        "decode_errors": len(decode_errors),
        "decode_error_lines": decode_errors[:5],
        "black_segments": [[float(a), float(b)] for a, b in black_segments],
        "loudness_integrated_lufs": integrated,
        "true_peak_dbfs": peak,
        "tts_total_s": round(tts_total, 3),
        "narration_chars": sum(len(re.sub(r"[，。、；：“”《》（）\s]", "", s["narration"])) for s in SHOTS),
        # 覆盖：每镜旁白时长 / 6 秒；用户要求「有片段就有解说」，所以这里要看得到每镜的数
        "narration_coverage_pct": round(tts_total / TOTAL_S * 100, 1),
        "per_shot_tts_s": [t["tts_s"] for t in timeline],
        "min_shot_tts_s": min(t["tts_s"] for t in timeline),
    }
    qc_data["passed"] = (
        qc_data["duration_ok"]
        and qc_data["min_shot_tts_s"] >= 5.0
        and qc_data["decode_errors"] == 0
        and qc_data["width"] == W
        and qc_data["height"] == H
        and qc_data["audio_sample_rate"] == 48000
    )
    # 黑帧只允许出现在最后的淡出（>=177s）；否则判异常。
    unexpected_black = [seg for seg in qc_data["black_segments"]
                        if seg[0] > 1.5 and seg[1] < 177.0]
    qc_data["unexpected_black_segments"] = unexpected_black
    if unexpected_black:
        qc_data["passed"] = False
    return qc_data


def contact_sheets(final: Path) -> tuple[Path, Path]:
    contact = OUT / "final-contact.jpg"
    step = max(1, int(TOTAL_S * FPS / 16))
    sh(["ffmpeg", "-y", "-v", "error", "-i", str(final),
        "-vf", f"select='not(mod(n,{step}))',scale=480:270,tile=4x4",
        "-frames:v", "1", str(contact)])
    per_slot = OUT / "final-per-slot.jpg"
    expr = "+".join(f"eq(n,{round((i * 6 + 3) * FPS)})" for i in range(len(SHOTS)))
    sh(["ffmpeg", "-y", "-v", "error", "-i", str(final),
        "-vf", f"select='{expr}',scale=320:180,tile=6x5",
        "-frames:v", "1", str(per_slot)])
    return contact, per_slot


def write_delivery(final: Path, report: dict, srt: Path, contact: Path, per_slot: Path) -> None:
    delivery = HERE / "delivery" / "final"
    delivery.mkdir(parents=True, exist_ok=True)
    # 大视频不进 Git：final.mp4 只进 Actions artifact 与 Release。
    for path in (srt, contact, per_slot):
        shutil.copy2(path, delivery / path.name)
    (delivery / "README.md").write_text(
        "# 金大斗案 · 成片交付\n\n"
        "- 成片 `final.mp4`（180 秒 / 1920×1080 / 30fps）在 Actions artifact `kimdaedoo-final`\n"
        "  与 GitHub Release `kimdaedoo-v1-*` 中；仓库不提交大视频。\n"
        "- `captions.srt`：烧录进成片的同一份字幕。\n"
        "- `final-contact.jpg` / `final-per-slot.jpg`：16 帧总览与 30 镜中点抽检表。\n"
        "- `technical-report.json`：逐镜哈希、音画对位、QC 与响度。\n"
        "- `narration-180s.txt`：180 秒版逐镜旁白。\n",
        encoding="utf-8")
    (delivery / "technical-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    narration = "\n".join(f"{s['id']}｜{s['narration']}" for s in SHOTS) + "\n"
    (delivery / "narration-180s.txt").write_text(narration, encoding="utf-8")
    (delivery / "release-notes.md").write_text(
        "# 金大斗案 · 三分钟成片\n\n"
        f"- 时长 **180.0 秒**（30 镜 × 6 秒，严格 1920×1080 / 30fps）\n"
        f"- 画面：**Agnes `agnes-video-2.5-flash` 720P** 逐镜生成，出片放大到 1080p\n"
        f"- 配音：**edge-tts {VOICE}**（中文男声，低沉；pitch {PITCH}），30 段逐镜对位\n"
        f"- 音乐：程序生成的原创悬疑 BGM（无版权问题）\n"
        f"- 字幕：按 TTS 实际时窗烧录；片头/片尾标题 + 常驻「{WATERMARK}」标签\n"
        f"- QC：{report['qc']['duration_s']}s / 解码错误 {report['qc']['decode_errors']} / "
        f"响度 {report['qc']['loudness_integrated_lufs']} LUFS\n\n"
        "## 素材与事实\n\n"
        "- 真实案件，画面为写实 3D 动画情景重现，不是新闻影像。\n"
        "- 受害者不出现在暴力画面里；不展示血腥、遗体或作案过程。\n"
        "- 金大斗为虚构重建形象，不对应真实照片。\n"
        "- 事实核对见 `production/kimdaedoo/史实核对.md`。\n", encoding="utf-8")


def main() -> int:
    stale = stale_shots()
    if stale:
        die("FATAL: 以下镜头的素材来自旧提示词，必须先重新生成：" + " ".join(stale))

    log("1/7 下载 30 镜并校验 SHA-256 …")
    for shot in SHOTS:
        download(shot["id"])

    log("2/7 edge-tts 逐镜配音（%s, pitch %s）…" % (VOICE, PITCH))
    timeline = []
    tts_total = 0.0
    for index, shot in enumerate(SHOTS):
        wav, duration, used_rate = fit_speech(shot)
        start = index * 6 + LEAD_S
        if start + duration > (index + 1) * 6 - 0.03:
            die(f"{shot['id']} 配音仍超出镜头窗：{duration:.2f}s")
        tts_total += duration
        timeline.append({
            "slot": index + 1,
            "id": shot["id"],
            "narration": shot["narration"],
            "wav": wav,
            "clip": CLIPS / f"{shot['id']}.mp4",
            "tts_s": round(duration, 3),
            "tts_rate": used_rate,
            "audio_start": round(start, 3),
            "audio_end": round(start + duration, 3),
            "slot_start": index * 6,
            "slot_duration": 6,
        })
        log(f"  {shot['id']} {duration:.2f}s @ {used_rate}")
    # 「有片段就有解说」的硬闸：每镜旁白必须铺到 5 秒以上；
    # 5.0–5.3 秒记 warning（可能有一瞬留白），低于 5.0 秒直接停，不带病出片。
    coverage_gaps = [t for t in timeline if t["tts_s"] < MIN_LINE_S - 0.02]
    hard_gaps = [t["id"] for t in timeline if t["tts_s"] < 5.0]
    if hard_gaps:
        die("以下镜头旁白不足 5 秒，等于有画面没解说：" + " ".join(hard_gaps))
    if coverage_gaps:
        log("  COVERAGE_WARN " + " ".join(f"{t['id']}={t['tts_s']:.2f}s" for t in coverage_gaps))
    log(f"  解说总时长 {tts_total:.1f}s / {TOTAL_S:.0f}s（覆盖 {tts_total / TOTAL_S * 100:.0f}%）；"
        f"平均 {report_rate(tts_total):.0f} 字/分钟")

    log("3/7 生成字幕 …")
    srt, ass = build_subtitles(timeline)

    log("4/7 生成原创悬疑 BGM …")
    bgm = make_bgm(TOTAL_S)

    log("5/7 合成成片 …")
    final = render(timeline, ass, bgm)

    log("6/7 程序化 QC …")
    qc_data = qc(final, timeline, tts_total)
    if not qc_data["passed"]:
        die("QC 未通过：" + json.dumps(qc_data, ensure_ascii=False))

    contact, per_slot = contact_sheets(final)
    report = {
        "title": STORY["title"],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": RESULTS.get("model") or STORY.get("model"),
        "size": "720P → 1920×1080",
        "fps": FPS,
        "target_duration_s": TOTAL_S,
        "actual_duration_s": qc_data["duration_s"],
        "narration_mode": STORY.get("narration_mode"),
        "narration_chars": qc_data["narration_chars"],
        "tts_voice": VOICE,
        "tts_pitch": PITCH,
        "tts_total_s": round(tts_total, 3),
        "avg_speech_rate_cpm": round(qc_data["narration_chars"] / (tts_total / 60)),
        "bgm": {"generator": "电影解说工具包/generate_horror_bgm.py", "volume": BGM_VOLUME},
        "qc": qc_data,
        "slots": [{k: v for k, v in row.items() if k not in ("wav", "clip")} | {
            "clip": str(row["clip"].relative_to(ROOT)),
        } for row in timeline],
        "source_note": (
            "画面为 1975 年韩国真实案件的情景重现，不是新闻影像；金大斗为虚构重建形象，"
            "不对应真实照片；受害者不出现在暴力画面里。"
        ),
    }
    log("7/7 写入交付 …")
    write_delivery(final, report, srt, contact, per_slot)

    # 报告推回分支（失败不阻断交付，artifact 里已有完整报告）
    try:
        sh(["git", "config", "user.name", "kimdaedoo-final"])
        sh(["git", "config", "user.email", "kimdaedoo-final@users.noreply.github.com"])
        sh(["git", "add", "production/kimdaedoo/delivery/final/"])
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode:
            sh(["git", "commit", "-q", "-m", "kimdaedoo: 180 秒成片交付（报告 + 字幕 + 抽检表）"], cwd=ROOT)
            sh(["git", "push", "origin", "HEAD:arena/b726ea5e-desktop-tutorial"], cwd=ROOT)
    except subprocess.CalledProcessError as exc:
        log("  报告推送失败（不影响 artifact）：", exc)

    log(f"DONE final={final} dur={qc_data['duration_s']}s size={final.stat().st_size / 1e6:.1f}MB")
    return 0


def report_rate(seconds: float) -> float:
    chars = sum(len(re.sub(r"[，。、；：“”《》（）\s]", "", s["narration"])) for s in SHOTS)
    return chars / (seconds / 60) if seconds else 0


if __name__ == "__main__":
    raise SystemExit(main())
