#!/usr/bin/env python3
"""找一台能用的 ffmpeg。

沙箱里系统包管理器装不了东西（PEP 668 / 非 root），所以优先用 pip 装的
``imageio-ffmpeg`` 带的那份静态 ffmpeg；没有再退回 PATH 里的系统 ffmpeg。

用法::

    from production.style_lab.ffmpeg_tool import find_ffmpeg
    ffmpeg = find_ffmpeg()      # 找不到抛 RuntimeError
"""
from __future__ import annotations

import os
import shutil
import subprocess
from functools import lru_cache


def _usable(path: str) -> bool:
    try:
        proc = subprocess.run(
            [path, "-hide_banner", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0 and b"ffmpeg version" in proc.stdout


@lru_cache(maxsize=1)
def find_ffmpeg() -> str:
    """返回可用的 ffmpeg 可执行文件路径。"""
    candidates = []
    env = os.environ.get("FFMPEG_BINARY")
    if env:
        candidates.append(env)
    try:  # pip install imageio-ffmpeg 会带一份静态编译的 ffmpeg
        import imageio_ffmpeg  # type: ignore

        candidates.append(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:  # pragma: no cover - 取决于环境
        pass
    which = shutil.which("ffmpeg")
    if which:
        candidates.append(which)

    for cand in candidates:
        if cand and _usable(cand):
            return cand
    raise RuntimeError(
        "找不到可用的 ffmpeg。装一份：python3 -m pip install --break-system-packages imageio-ffmpeg"
        "（或系统包管理器装 ffmpeg）。"
    )


def ffmpeg_version(ffmpeg: str) -> str:
    try:
        out = subprocess.run(
            [ffmpeg, "-hide_banner", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
        ).stdout.decode("utf-8", "replace")
    except Exception:  # pragma: no cover
        return "unknown"
    for line in out.splitlines():
        if line.startswith("ffmpeg version"):
            return line.split(" Copyright")[0].strip()
    return "unknown"
