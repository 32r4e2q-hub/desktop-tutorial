#!/usr/bin/env python3
"""ffprobe 替身：在没有 ffprobe 的 runner 上给出 render.py / build_audio.py 需要的最小信息。

优先用 PyAV 读容器（精确、快）；PyAV 不可用时退回解析 ``ffmpeg -i`` 的 stderr。
支持本仓库用到的两种调用：
  * ``-show_entries format=duration -of default=nw=1:nk=1``  → 只输出秒数
  * ``-show_format -show_streams -of json``                  → 输出 streams/format
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

PATH = sys.argv[-1]
WANTS_DURATION_ONLY = "-show_entries" in sys.argv and "format=duration" in " ".join(sys.argv)
WANTS_JSON = "-show_format" in sys.argv or "-show_streams" in sys.argv


def fraction(text: str) -> float:
    match = re.fullmatch(r"(\d+)/(\d+)", text.strip())
    if match:
        numerator, denominator = int(match.group(1)), int(match.group(2))
        return numerator / denominator if denominator else 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def parity(value: float) -> int:
    return int(value) + (int(value) % 2)


def probe_with_pyav() -> dict:
    import av  # 仅在没有 ffprobe 的镜像里才会走到这里

    container = av.open(PATH)
    try:
        duration = (container.duration or 0) / 1e6
        streams = []
        for stream in container.streams:
            context = stream.codec_context
            if stream.type == "video":
                rate = stream.average_rate or stream.guessed_rate or 24
                fps = f"{rate.numerator}/{rate.denominator}"
                frames = int(stream.frames or 0) or int(round(duration * fraction(fps)))
                streams.append({
                    "index": stream.index, "codec_type": "video",
                    "codec_name": context.name,
                    "width": int(context.width), "height": int(context.height),
                    "avg_frame_rate": fps, "nb_frames": str(frames),
                    "duration": f"{duration:.6f}",
                })
            elif stream.type == "audio":
                streams.append({
                    "index": stream.index, "codec_type": "audio",
                    "codec_name": context.name,
                    "sample_rate": str(getattr(context, "sample_rate", 48000) or 48000),
                    "channels": int(getattr(context, "channels", 2) or 2),
                    "duration": f"{duration:.6f}",
                })
        return {"streams": streams,
                "format": {"duration": f"{duration:.6f}", "size": "0", "format_name": "mp4"}}
    finally:
        container.close()


def probe_with_ffmpeg(ffmpeg: str) -> dict:
    output = subprocess.run([ffmpeg, "-hide_banner", "-i", PATH], capture_output=True, text=True).stderr
    duration = 0.0
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", output)
    if match:
        hours, minutes, seconds = match.groups()
        duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    streams, index = [], 0
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("Stream #"):
            index = len(streams)
            if "Video:" in line:
                size = re.search(r"(\d{2,5})x(\d{2,5})", line)
                rate = re.search(r"(\d+(?:\.\d+)?) fps", line)
                fps_value = float(rate.group(1)) if rate else 24.0
                streams.append({
                    "index": index, "codec_type": "video",
                    "codec_name": line.split("Video:")[1].split()[0].strip(","),
                    "width": int(size.group(1)) if size else 0,
                    "height": int(size.group(2)) if size else 0,
                    "avg_frame_rate": f"{fps_value:.0f}/1",
                    "nb_frames": str(int(round(duration * fps_value))),
                    "duration": f"{duration:.6f}",
                })
            elif "Audio:" in line:
                rate = re.search(r"(\d+) Hz", line)
                if "mono" in line:
                    channels = 1
                elif "stereo" in line:
                    channels = 2
                else:
                    counted = re.search(r"(\d+) channels", line)
                    channels = int(counted.group(1)) if counted else 2
                streams.append({
                    "index": index, "codec_type": "audio",
                    "codec_name": line.split("Audio:")[1].split()[0].strip(","),
                    "sample_rate": rate.group(1) if rate else "48000",
                    "channels": channels,
                    "duration": f"{duration:.6f}",
                })
    return {"streams": streams,
            "format": {"duration": f"{duration:.6f}", "size": "0", "format_name": "mp4"}}


def main() -> int:
    try:
        payload = probe_with_pyav()
    except Exception as error:  # PyAV 装不上或解不开时退回 ffmpeg 文本解析
        print(f"pyav probe failed ({error}); falling back to ffmpeg -i", file=sys.stderr)
        payload = probe_with_ffmpeg("ffmpeg")
    if not payload["streams"]:
        print(f"ffprobe shim could not read {PATH}", file=sys.stderr)
        return 1
    if WANTS_DURATION_ONLY and not WANTS_JSON:
        print(payload["format"]["duration"])
        return 0
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
