#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阴曹使者 抖音解说视频制作脚本
=====================================
流程：
  1. PySceneDetect 检测镜头切点
  2. Whisper 转录原片台词 + 时间码
  3. 人工/自动生成解说文案（参考抖音解说视频）
  4. Edge-TTS 云希声（zh-CN-YunxiNeural）逐句生成音频
  5. 音频反驱动剪辑：每句音频真实时长决定对应画面长度
  6. 逐句字幕（PIL 渲染，遮盖原字幕区域）
  7. 合并输出 720p MP4

依赖安装（一键）：
  pip install edge-tts scenedetect[opencv] openai-whisper pysrt pillow numpy tqdm imageio-ffmpeg
  (ffmpeg 由 imageio-ffmpeg 自动携带，或系统自带)

用法：
  python make_douyin_video.py \
      --movie  原版电影.mp4 \
      --ref    抖音解说视频.mp4 \
      --script script.txt   # 可选：手动提供解说文案，否则自动从ref提取
      --output 成品.mp4
"""

import argparse
import asyncio
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

# ─────────────────────────── 工具函数 ──────────────────────────────

def get_ffmpeg():
    """获取 ffmpeg 可执行路径"""
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise RuntimeError("未找到 ffmpeg，请安装: pip install imageio-ffmpeg 或系统安装 ffmpeg")

FFMPEG = get_ffmpeg()

def run(cmd, desc="", check=True):
    """运行 shell 命令"""
    if desc:
        print(f"[CMD] {desc}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"[ERROR] {result.stderr[-500:]}")
        raise RuntimeError(f"命令失败: {cmd[:100]}")
    return result.stdout.strip()

def get_duration(path):
    """获取视频时长(秒)"""
    out = run(
        f'"{FFMPEG}" -i "{path}" 2>&1 | grep Duration',
        check=False
    )
    # 也用 ffprobe 方式
    cmd = f'"{FFMPEG}" -v quiet -print_format json -show_streams -i "{path}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        import json
        data = json.loads(result.stdout)
        for s in data.get("streams", []):
            if s.get("codec_type") == "video":
                return float(s.get("duration", 0))
    # fallback: parse Duration from stderr
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", result.stderr + out)
    if m:
        h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
        return h * 3600 + mi * 60 + s
    return 0.0

# ─────────────────────────── Step 1: 镜头检测 ──────────────────────

def detect_scenes(movie_path, threshold=27.0):
    """使用 PySceneDetect 检测镜头切点，返回 [(start_sec, end_sec), ...]"""
    print("\n[Step 1] 检测镜头切点...")
    from scenedetect import open_video, SceneManager
    from scenedetect.detectors import ContentDetector

    video = open_video(movie_path)
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=threshold))
    manager.detect_scenes(video, show_progress=True)
    scene_list = manager.get_scene_list()

    scenes = []
    for s, e in scene_list:
        scenes.append((s.get_seconds(), e.get_seconds()))

    print(f"  → 检测到 {len(scenes)} 个镜头")
    return scenes

# ─────────────────────────── Step 2: 语音识别 ──────────────────────

def transcribe_audio(video_path, lang="zh"):
    """使用 Whisper 转录视频音频，返回 [{start, end, text}, ...]"""
    print("\n[Step 2] Whisper 转录音频...")
    try:
        import whisper
    except ImportError:
        print("  [WARN] openai-whisper 未安装，跳过转录。pip install openai-whisper")
        return []

    model = whisper.load_model("base")
    result = model.transcribe(video_path, language=lang, verbose=False)
    segments = []
    for seg in result["segments"]:
        segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip()
        })
    print(f"  → 识别到 {len(segments)} 条台词")
    return segments

# ─────────────────────────── Step 3: 解说文案 ──────────────────────

def load_script(script_path):
    """从文本文件加载解说文案，每行一句"""
    lines = []
    with open(script_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                lines.append(line)
    return lines

def extract_ref_script(ref_path):
    """从抖音解说视频提取解说文案（Whisper）"""
    print("\n[Step 3] 从参考解说视频提取文案...")
    segs = transcribe_audio(ref_path, lang="zh")
    lines = [s["text"] for s in segs if s["text"]]
    # 合并过短的句子
    merged = []
    buf = ""
    for line in lines:
        buf += line
        if len(buf) >= 15 or any(c in buf for c in "。！？…"):
            merged.append(buf.strip())
            buf = ""
    if buf:
        merged.append(buf.strip())
    print(f"  → 提取到 {len(merged)} 句解说")
    return merged

# ─────────────────────────── Step 4: TTS 生成 ──────────────────────

async def _tts_single(text, out_path, voice="zh-CN-YunxiNeural", rate="+10%"):
    """异步生成单句 TTS 音频"""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(out_path)

def generate_tts_audio(sentences, tts_dir, voice="zh-CN-YunxiNeural", rate="+10%"):
    """
    逐句生成 TTS 音频
    返回 [(text, audio_path, duration_sec), ...]
    """
    print(f"\n[Step 4] Edge-TTS 生成云希声音频 ({voice})...")
    os.makedirs(tts_dir, exist_ok=True)
    results = []

    async def run_all():
        tasks = []
        for i, text in enumerate(sentences):
            out = os.path.join(tts_dir, f"line_{i:04d}.mp3")
            tasks.append(_tts_single(text, out, voice, rate))
        for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks)):
            await coro

    asyncio.run(run_all())

    # 获取每句时长
    for i, text in enumerate(sentences):
        mp3 = os.path.join(tts_dir, f"line_{i:04d}.mp3")
        if os.path.exists(mp3):
            dur = get_audio_duration(mp3)
            results.append((text, mp3, dur))
        else:
            print(f"  [WARN] 第{i}句 TTS 生成失败: {text[:30]}")

    total = sum(r[2] for r in results)
    print(f"  → {len(results)} 句音频，总时长 {total:.1f}s ({total/60:.1f}min)")
    return results

def get_audio_duration(path):
    """获取音频时长(秒)"""
    cmd = f'"{FFMPEG}" -v quiet -print_format json -show_streams -i "{path}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            for s in data.get("streams", []):
                dur = float(s.get("duration", 0))
                if dur > 0:
                    return dur
        except Exception:
            pass
    # fallback via stderr
    cmd2 = f'"{FFMPEG}" -i "{path}" 2>&1'
    out = subprocess.run(cmd2, shell=True, capture_output=True, text=True).stderr
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", out)
    if m:
        h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
        return h * 3600 + mi * 60 + s
    return 3.0  # fallback

# ─────────────────────────── Step 5: EDL 剪辑单 ────────────────────

def build_edl(scenes, tts_results, movie_duration):
    """
    根据 TTS 音频时长，从镜头列表中分配对应的原片片段
    每句解说占用与 TTS 时长相同的原片画面

    返回：
      edl = [
        {
          "text": str,
          "audio": str (path),
          "audio_dur": float,
          "movie_start": float,
          "movie_end": float,
        },
        ...
      ]
    """
    print("\n[Step 5] 构建 EDL 剪辑单...")
    edl = []
    movie_cursor = 0.0  # 原片时间游标

    # 把镜头列表展开为连续时间轴
    # 如果解说比原片长，循环复用原片
    total_tts = sum(r[2] for r in tts_results)
    print(f"  TTS 总时长: {total_tts:.1f}s | 原片时长: {movie_duration:.1f}s")

    for text, audio_path, audio_dur in tts_results:
        clip_start = movie_cursor
        clip_end = movie_cursor + audio_dur

        # 不超过原片末尾
        if clip_end > movie_duration:
            clip_end = movie_duration
            if clip_start >= movie_duration:
                clip_start = movie_duration - audio_dur
                clip_start = max(0, clip_start)

        edl.append({
            "text": text,
            "audio": audio_path,
            "audio_dur": audio_dur,
            "movie_start": clip_start,
            "movie_end": clip_end,
        })
        movie_cursor = clip_end

    # 打印 EDL
    print(f"  → EDL 共 {len(edl)} 条")
    for i, e in enumerate(edl):
        print(f"    [{i:03d}] {e['movie_start']:.2f}s-{e['movie_end']:.2f}s | "
              f"{e['audio_dur']:.2f}s | {e['text'][:30]}")

    return edl

# ─────────────────────────── Step 6: 字幕渲染 ──────────────────────

def get_font(size=48):
    """获取中文字体"""
    font_paths = [
        # Linux
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        # Windows
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    print("  [WARN] 未找到中文字体，使用默认字体（字幕可能显示不正常）")
    return ImageFont.load_default()

def render_subtitle_frame(frame_np, text, font=None, out_h=720):
    """
    在视频帧上渲染字幕：
    - 遮盖原字幕区域（底部15%）
    - 绘制新字幕（白字黑描边）
    """
    img = Image.fromarray(frame_np)
    w, h = img.size

    draw = ImageDraw.Draw(img)

    # 遮盖原字幕区域（底部 15%）
    sub_mask_top = int(h * 0.83)
    draw.rectangle([(0, sub_mask_top), (w, h)], fill=(0, 0, 0))

    # 字幕区域：底部中央
    if font is None:
        font = get_font(max(28, h // 20))

    # 自动换行
    max_width = int(w * 0.92)
    lines = wrap_text(text, font, max_width, draw)

    # 计算总高度
    line_spacing = 6
    _, _, _, lh = draw.textbbox((0, 0), "测", font=font)
    total_h = len(lines) * (lh + line_spacing)

    y = h - total_h - int(h * 0.03)

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (w - lw) // 2

        # 黑色描边
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0))
        # 白色主体
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
        y += lh + line_spacing

    return np.array(img)

def wrap_text(text, font, max_width, draw):
    """按宽度自动换行（支持中文）"""
    lines = []
    current = ""
    for char in text:
        test = current + char
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] > max_width and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines

# ─────────────────────────── Step 7: 视频合成 ──────────────────────

def process_segment(args):
    """处理单个片段（多进程友好）"""
    idx, edl_item, movie_path, seg_dir, width, height, fps = args
    text = edl_item["text"]
    m_start = edl_item["movie_start"]
    m_end = edl_item["movie_end"]
    audio_path = edl_item["audio"]
    audio_dur = edl_item["audio_dur"]

    seg_video = os.path.join(seg_dir, f"seg_{idx:04d}.mp4")

    # 从原片裁剪视频片段（静音，720p）
    clip_dur = m_end - m_start
    cmd = (
        f'"{FFMPEG}" -y -ss {m_start:.4f} -i "{movie_path}" '
        f'-t {clip_dur:.4f} '
        f'-vf "scale={width}:{height}:force_original_aspect_ratio=decrease,'
        f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1" '
        f'-an -c:v libx264 -preset fast -crf 23 "{seg_video}" 2>/dev/null'
    )
    subprocess.run(cmd, shell=True)

    # 用 PIL 逐帧渲染字幕
    seg_sub = os.path.join(seg_dir, f"seg_{idx:04d}_sub.mp4")
    add_subtitle_to_video(seg_video, text, seg_sub, width, height, fps)

    # 合并视频 + TTS 音频（以音频时长为准）
    seg_final = os.path.join(seg_dir, f"seg_{idx:04d}_final.mp4")
    cmd2 = (
        f'"{FFMPEG}" -y -i "{seg_sub}" -i "{audio_path}" '
        f'-map 0:v:0 -map 1:a:0 '
        f'-c:v libx264 -preset fast -crf 23 '
        f'-c:a aac -b:a 128k '
        f'-shortest "{seg_final}" 2>/dev/null'
    )
    subprocess.run(cmd2, shell=True)

    return seg_final

def add_subtitle_to_video(in_video, text, out_video, width, height, fps):
    """通过 ffmpeg drawtext 或 PIL 帧处理方式添加字幕"""
    # 使用 ffmpeg drawtext（更快，不需要 PIL 逐帧处理）
    # 遮盖底部 + 绘制字幕
    safe_text = text.replace("'", "\\'").replace(":", "\\:").replace(",", "\\,")

    # 字体路径
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ]
    font_file = ""
    for p in font_paths:
        if os.path.exists(p):
            font_file = p
            break

    sub_top = int(height * 0.83)
    font_size = max(28, height // 20)

    if font_file:
        vf = (
            f"drawbox=y={sub_top}:x=0:w={width}:h={height-sub_top}:color=black@1.0:t=fill,"
            f"drawtext=fontfile='{font_file}':text='{safe_text}':"
            f"fontcolor=white:fontsize={font_size}:borderw=2:bordercolor=black:"
            f"x=(w-text_w)/2:y=h-th-{int(height*0.03)}:line_spacing=6"
        )
    else:
        vf = (
            f"drawbox=y={sub_top}:x=0:w={width}:h={height-sub_top}:color=black@1.0:t=fill,"
            f"drawtext=text='{safe_text}':"
            f"fontcolor=white:fontsize={font_size}:borderw=2:bordercolor=black:"
            f"x=(w-text_w)/2:y=h-th-{int(height*0.03)}"
        )

    cmd = (
        f'"{FFMPEG}" -y -i "{in_video}" '
        f'-vf "{vf}" '
        f'-c:v libx264 -preset fast -crf 23 -an "{out_video}" 2>/dev/null'
    )
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        # 字幕失败，用原视频
        shutil.copy(in_video, out_video)

def concat_segments(seg_finals, output_path):
    """拼接所有片段"""
    print(f"\n[Step 7] 拼接 {len(seg_finals)} 个片段...")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for p in seg_finals:
            f.write(f"file '{os.path.abspath(p)}'\n")
        concat_list = f.name

    cmd = (
        f'"{FFMPEG}" -y -f concat -safe 0 -i "{concat_list}" '
        f'-c:v libx264 -preset medium -crf 22 '
        f'-c:a aac -b:a 128k '
        f'-movflags +faststart "{output_path}" 2>&1'
    )
    out = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    os.unlink(concat_list)
    if not os.path.exists(output_path):
        print(out.stderr[-500:])
        raise RuntimeError("拼接失败")
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"  → 输出: {output_path} ({size_mb:.1f} MB)")

# ─────────────────────────── Step 8: 质检 ──────────────────────────

def quality_check(output_path, edl):
    """质检：打印每句对应时间段，检查空档"""
    print("\n[Step 8] 质检报告")
    print("=" * 70)
    cur = 0.0
    for i, e in enumerate(edl):
        dur = e["audio_dur"]
        print(f"[{i:03d}] {cur:.2f}s-{cur+dur:.2f}s | {e['text'][:40]}")
        cur += dur
    total = get_duration(output_path)
    print(f"\n总时长: {total:.1f}s = {total/60:.1f}min")
    print("=" * 70)
    print("✅ 质检完成")

# ─────────────────────────── 主流程 ────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="阴曹使者抖音解说视频生成器")
    parser.add_argument("--movie",  required=True, help="原版电影 MP4 路径")
    parser.add_argument("--ref",    default="",    help="抖音解说参考视频（用于提取文案）")
    parser.add_argument("--script", default="",    help="手动提供的解说文案（TXT，每行一句）")
    parser.add_argument("--output", default="成品解说.mp4", help="输出 MP4 路径")
    parser.add_argument("--voice",  default="zh-CN-YunxiNeural", help="TTS 声音")
    parser.add_argument("--rate",   default="+8%",  help="TTS 语速")
    parser.add_argument("--width",  default=1280, type=int)
    parser.add_argument("--height", default=720,  type=int)
    parser.add_argument("--fps",    default=30.0, type=float)
    parser.add_argument("--threshold", default=27.0, type=float, help="镜头检测阈值")
    parser.add_argument("--work-dir", default="work_tmp", help="临时工作目录")
    args = parser.parse_args()

    os.makedirs(args.work_dir, exist_ok=True)
    tts_dir  = os.path.join(args.work_dir, "tts")
    seg_dir  = os.path.join(args.work_dir, "segments")
    os.makedirs(tts_dir, exist_ok=True)
    os.makedirs(seg_dir, exist_ok=True)

    # ── Step 1: 镜头检测 ──
    scenes = detect_scenes(args.movie, threshold=args.threshold)

    # ── Step 2: 转录原片（辅助参考，可选）──
    # movie_subs = transcribe_audio(args.movie)

    # ── Step 3: 获取解说文案 ──
    if args.script and os.path.exists(args.script):
        sentences = load_script(args.script)
        print(f"\n[Step 3] 从文件加载 {len(sentences)} 句解说文案")
    elif args.ref and os.path.exists(args.ref):
        sentences = extract_ref_script(args.ref)
    else:
        print("\n[ERROR] 请提供 --script 或 --ref 参数")
        sys.exit(1)

    if not sentences:
        print("[ERROR] 解说文案为空")
        sys.exit(1)

    # 打印文案
    print(f"\n解说文案（共 {len(sentences)} 句）:")
    for i, s in enumerate(sentences):
        print(f"  [{i+1:03d}] {s}")

    # ── Step 4: TTS 生成 ──
    tts_results = generate_tts_audio(sentences, tts_dir, args.voice, args.rate)

    # ── Step 5: EDL ──
    movie_dur = get_duration(args.movie)
    print(f"\n原片时长: {movie_dur:.1f}s = {movie_dur/60:.1f}min")
    edl = build_edl(scenes, tts_results, movie_dur)

    # ── Step 6+7: 逐段处理 ──
    print(f"\n[Step 6] 逐段渲染字幕并合成...")
    seg_finals = []
    for idx, edl_item in enumerate(tqdm(edl)):
        seg_final = process_segment((
            idx, edl_item, args.movie,
            seg_dir, args.width, args.height, args.fps
        ))
        if os.path.exists(seg_final):
            seg_finals.append(seg_final)

    if not seg_finals:
        print("[ERROR] 没有成功生成任何片段")
        sys.exit(1)

    # ── Step 7: 拼接 ──
    concat_segments(seg_finals, args.output)

    # ── Step 8: 质检 ──
    quality_check(args.output, edl)

    # 清理临时文件
    print(f"\n临时文件保留在: {args.work_dir}（可手动删除）")
    print(f"\n🎬 完成！输出: {args.output}")


if __name__ == "__main__":
    main()
