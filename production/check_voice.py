#!/usr/bin/env python3
"""固定音色闸门：解说配音必须是《黑色大丽花》同款普通话男音。

为什么存在
-----------
zodiac1969 第一版成片的解说用的是偏高音的音色（实测中位基频 168–200 Hz，
明显偏女声），和参考片《黑色大丽花》的男音（113–139 Hz）不是同一个声音，
直到成片交付才被人耳发现。这个脚本把"音色对了没有"变成一道机器闸门：
出片流程（``production/run_project.sh``）在混音之前先量每段配音的基频，
不在钉死区间内的配音直接拒绝出片，不再依赖事后人耳。

它量什么
---------
- 每段配音的基频（F0）中位数与低十分位（p10），方法与
  ``voice_reference/spec.json`` 里记录参考数值时完全一致：
  40 ms 帧 / 20 ms 跳、自相关、有声判据 RMS > 0.02 且峰值 > 0.35；
- 汇总中位数与参考音色（124.5 Hz）的偏差。

它**不**做什么
--------------
- 不做说话人识别：两个不同的男声可能都过闸。它拦的是"根本不是男音 /
  和参考音色明显不是一路"的配音；音色的最终一致性仍要靠试听时对照
  ``production/voice_reference/`` 里的参考样本。

用法::

    python3 production/check_voice.py --project production/<slug> \
        [--spec production/voice_reference/spec.json] [--report out.json]

退出码：0 = 通过；1 = 不过（附整改说明）。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_SPEC = HERE / "voice_reference" / "spec.json"
SR = 16000
FRAME = 0.04
HOP = 0.02
FMIN = 70.0
FMAX = 350.0
VOICED_RMS = 0.02
VOICED_PEAK = 0.35


class VoiceGateError(RuntimeError):
    """配音不在钉死的男音区间内。"""


def _ffmpeg() -> str:
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 - fall through to the clear error below
        pass
    raise VoiceGateError("找不到 ffmpeg：装系统 ffmpeg 或 `pip install imageio-ffmpeg`")


def decode(path: Path) -> np.ndarray:
    """任何音频解码成 16 kHz 单声道 float32；wav 直读，不依赖 ffmpeg。"""
    if path.suffix.lower() == ".wav":
        with wave.open(str(path), "rb") as reader:
            assert reader.getframerate() == SR and reader.getnchannels() == 1, \
                "wav 直读只支持 16 kHz 单声道（测试用）；其他情况走 ffmpeg"
            data = np.frombuffer(reader.readframes(reader.getnframes()), dtype="<i2")
            return data.astype(np.float32) / 32768.0
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        subprocess.run([
            _ffmpeg(), "-v", "error", "-y", "-i", str(path),
            "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", str(temporary),
        ], check=True)
        return decode(temporary)
    finally:
        temporary.unlink(missing_ok=True)


def f0_track(samples: np.ndarray) -> np.ndarray:
    """自相关基频轨迹；只保留有声帧，返回 F0 数组（可能为空）。"""
    frame = int(FRAME * SR)
    hop = int(HOP * SR)
    lag_min = int(SR / FMAX)
    lag_max = int(SR / FMIN)
    values = []
    window = np.hanning(frame)
    for start in range(0, max(0, len(samples) - frame), hop):
        block = samples[start:start + frame] * window
        if float(np.sqrt(np.mean(block * block))) <= VOICED_RMS:
            continue
        correlation = np.correlate(block, block, "full")[frame - 1:]
        if correlation[0] <= 0:
            continue
        correlation = correlation / correlation[0]
        segment = correlation[lag_min:lag_max]
        if len(segment) == 0:
            continue
        lag = int(np.argmax(segment)) + lag_min
        if correlation[lag] > VOICED_PEAK:
            values.append(SR / lag)
    return np.asarray(values, dtype=np.float64)


def profile(path: Path) -> dict:
    samples = decode(path)
    track = f0_track(samples)
    profile = {
        "file": path.name,
        "duration_seconds": round(len(samples) / SR, 2),
        "voiced_frames": int(len(track)),
    }
    if len(track):
        profile["median_f0_hz"] = round(float(np.median(track)), 1)
        profile["p10_f0_hz"] = round(float(np.percentile(track, 10)), 1)
    return profile


def check(project_dir: Path, spec_path: Path) -> dict:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    gate = spec["gate"]
    manifest_path = project_dir / "audio" / "manifest.json"
    if not manifest_path.is_file():
        raise VoiceGateError(f"找不到 {manifest_path}：先按手册把配音与清单做好")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    clips = manifest.get("clips", [])
    if not clips:
        raise VoiceGateError("audio/manifest.json 里没有配音条目")

    problems: list[str] = []
    profiles = []
    for clip in clips:
        path = project_dir / "audio" / clip["file"]
        if not path.is_file():
            problems.append(f"{clip['id']}: 缺文件 {path}")
            continue
        row = {"id": clip["id"], **profile(path)}
        profiles.append(row)
        if row["voiced_frames"] < gate["min_voiced_frames_per_clip"]:
            problems.append(
                f"{row['id']}: 有声帧只有 {row['voiced_frames']}，低于 "
                f"{gate['min_voiced_frames_per_clip']}（配音太短或几乎无声？）")
            continue
        low, high = gate["median_f0_hz"]
        if not low <= row["median_f0_hz"] <= high:
            problems.append(
                f"{row['id']}: 中位基频 {row['median_f0_hz']} Hz，不在男音区间 "
                f"[{low}, {high}] Hz（参考男音 113–139 Hz；第一版十二宫的偏高音色是 168–200 Hz）")
        if row["p10_f0_hz"] > gate["p10_f0_hz_max"]:
            problems.append(
                f"{row['id']}: 低十分位基频 {row['p10_f0_hz']} Hz 高于 "
                f"{gate['p10_f0_hz_max']} Hz（男音低频下不去，多半不是男声）")

    reference = float(spec["measured_reference"]["pooled_median_f0_hz"])
    tolerance = gate["pooled_median_within_percent_of_reference"] / 100.0
    if profiles and all("median_f0_hz" in row for row in profiles):
        pooled = float(np.median([row["median_f0_hz"] for row in profiles]))
        if not reference * (1 - tolerance) <= pooled <= reference * (1 + tolerance):
            problems.append(
                f"汇总中位基频 {pooled:.1f} Hz 偏离参考音色（{reference} Hz）超过 "
                f"{gate['pooled_median_within_percent_of_reference']}%：和《黑色大丽花》"
                "的男音不是一路，请对照 production/voice_reference/ 重新试听选择")

    report = {
        "project": str(project_dir),
        "spec": str(spec_path),
        "voice_id": manifest.get("voice_id", ""),
        "language": manifest.get("language", ""),
        "reference_pooled_median_f0_hz": reference,
        "pooled_median_f0_hz": (round(float(np.median([row["median_f0_hz"] for row in profiles])), 1)
                                if profiles and all("median_f0_hz" in row for row in profiles) else None),
        "clips": profiles,
        "problems": problems,
        "passed": not problems,
        "remedy": ("重新配音：试听时指定 普通话（zh-CN）/ 男声（masculine）/ 解说（narration），"
                   "对照 production/voice_reference/ 里的参考样本选最接近的音色，"
                   "配完重跑本命令。参考片《黑色大丽花》与《十二宫杀手》用的都是同一把男音。")
                  if problems else "",
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="解说固定音色闸门（男音钉死检查）")
    parser.add_argument("--project", type=Path, required=True, help="项目目录，例如 production/zodiac1969")
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC, help="音色规格 JSON")
    parser.add_argument("--report", type=Path, default=None, help="把结果写到这个 JSON 文件")
    args = parser.parse_args()
    try:
        report = check(args.project, args.spec)
    except VoiceGateError as error:
        print(f"VOICE_GATE_ERROR {error}", file=sys.stderr)
        return 1
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {row.get("id"): row.get("median_f0_hz") for row in report["clips"]}
    print("VOICE_PROFILE " + json.dumps(summary, ensure_ascii=False))
    if report["passed"]:
        print("VOICE_GATE_PASS 每段配音都在钉死的男音区间内")
        return 0
    print("VOICE_GATE_FAIL 配音不在钉死的男音区间内：", file=sys.stderr)
    for problem in report["problems"]:
        print(f"  - {problem}", file=sys.stderr)
    print(f"  整改：{report['remedy']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
