#!/usr/bin/env python3
"""2026-10-23 素材救援：智谱 CDN 签名 URL 过期且平台不重签，原始 mp4 永久丢失。
成片 artifact 里的 image-track.mp4 是 31 段拼接后的纯画面轨（字幕/角标/横幅均为
最终混成才烧录的 ASS，delogo 也在混成级），画面内容与最终成片逐帧一致。
按 v2.1 交付 EDL 的精确帧边界把 image-track 切回 31 条源（frame accurate 重编码，
crf18），入仓 production/maryceleste1872/sources/，之后出片从仓库恢复素材。
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FPS = 30
ARTIFACT_RUN = "39898596032"      # v2.1 渲染 run（成片 artifact 157MB = 成片 + image-track）
ARTIFACT_NAME = "maryceleste1872-成片-3"


def sh(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def main() -> int:
    frames = json.loads((HERE / "recovery" / "sources-frames.json").read_text(encoding="utf-8"))
    art_dir = Path("/tmp/recover-artifact")
    art_dir.mkdir(parents=True, exist_ok=True)
    if not any(art_dir.rglob("image-track.mp4")):
        print(f"DOWNLOAD artifact {ARTIFACT_NAME} from run {ARTIFACT_RUN}", flush=True)
        sh("gh", "run", "download", ARTIFACT_RUN, "--dir", str(art_dir),
           "--name", ARTIFACT_NAME, "--repo", "32r4e2q-hub/desktop-tutorial")
    tracks = list(art_dir.rglob("image-track.mp4"))
    if not tracks:
        print("FATAL: artifact 里没有 image-track.mp4", flush=True)
        return 1
    track = tracks[0]
    info = json.loads(sh("ffprobe", "-v", "error", "-print_format", "json",
                         "-show_format", "-show_streams", str(track)))
    duration = float(info["format"]["duration"])
    print(f"IMAGE_TRACK {track} {duration:.3f}s", flush=True)
    if abs(duration - 180.0) > 0.5:
        print("FATAL: image-track 时长不是 180s", flush=True)
        return 1

    out_dir = HERE / "sources"
    out_dir.mkdir(exist_ok=True)
    for entry in frames:
        sid, a, b = entry["id"], entry["start_frame"], entry["end_frame"]
        n = b - a
        target = out_dir / f"{sid}.mp4"
        start = a / FPS
        sh("ffmpeg", "-y", "-v", "error", "-accurate_seek", "-ss", f"{start:.6f}",
           "-i", str(track), "-frames:v", str(n), "-an",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           str(target))
        got = float(json.loads(sh("ffprobe", "-v", "error", "-print_format", "json",
                                  "-show_format", str(target)))["format"]["duration"])
        want = n / FPS
        if abs(got - want) > 0.15:
            print(f"FATAL: {sid} 时长 {got:.3f} != 期望 {want:.3f}", flush=True)
            return 1
        print(f"CUT {sid} frames[{a},{b}) -> {got:.3f}s {target.stat().st_size}B", flush=True)

    sh("git", "config", "user.name", "arena-diag")
    sh("git", "config", "user.email", "arena@local")
    sh("git", "add", "production/maryceleste1872/sources")
    try:
        sh("git", "commit", "-m",
           "maryceleste1872: 31 条源从成片 image-track 切出入仓（CDN URL 过期救援）")
    except subprocess.CalledProcessError:
        print("nothing to commit", flush=True)
    pushed = False
    for _ in range(3):
        try:
            sh("git", "pull", "--rebase", "origin", "arena/63ceeca2-desktop-tutorial")
            sh("git", "push", "origin", "HEAD:arena/63ceeca2-desktop-tutorial")
            pushed = True
            break
        except subprocess.CalledProcessError as error:
            print(f"push/rebase retry: {error}", flush=True)
    print("RECOVER_DONE" if pushed else "RECOVER_PUSH_FAILED", flush=True)
    return 0 if pushed else 1


if __name__ == "__main__":
    sys.exit(main())
