"""闸门二本地试渲染：用「场记板替身片段」跑通整条 render 路径。

为什么要这一步：Agnes 素材只能在有 API 出口的地方生成，而 render.py 里所有
硬闸门（5400 帧 / 1920×1080 / 30fps / 字幕烧录 / 卡片动画 / 慢放系数 / 响度）
都跟素材内容无关。用替身先在本地把这条路径跑通，等真素材到位就只剩「画面质量」
一类问题，不会在最后一天才发现字幕溢出、卡片时长不够、响度不达标。

产物一律落在 work/（不入库、不当交付）：文件名里带 slate，交付必须由 render
工作流用 results.json 里真实的 Agnes 收据重跑一次。

用法：PATH="$PWD/bin:$PATH" python3 production/monalisa/slate_render.py
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
WORK = ROOT / "work" / "monalisa" / "slate"
CLIPS = WORK / "clips"
W, H, FPS, SECONDS = 1920, 1080, 24, 7.041667

import render  # noqa: E402
from generate import request_hash  # noqa: E402


def slate(sid, index, total, kind, text, dest):
    """一块能动的场记板：横向缓慢平移，避免被判成静帧。"""
    frames = int(round(SECONDS * FPS))
    band = np.zeros((H, W, 3), np.uint8)
    yy = np.arange(H)[:, None]
    xx = np.arange(W)[None, :]
    band[..., 0] = np.clip(46 + 26 * np.sin(yy / 90 + index), 0, 255).astype(np.uint8)
    band[..., 1] = np.clip(52 + 20 * np.cos(xx / 210 + index), 0, 255).astype(np.uint8)
    band[..., 2] = np.clip(44 + 14 * np.sin((xx + yy) / 260), 0, 255).astype(np.uint8)
    base = Image.fromarray(band)
    draw = ImageDraw.Draw(base)
    font = render.font(86)
    small = render.font(34)
    label = f"{sid} · {kind}"
    draw.text((W // 2, H // 2 - 60), label, font=font, fill="#e8e2d0", anchor="mm")
    for i, line in enumerate(textwrap_lines(text, 26)):
        draw.text((W // 2, H // 2 + 60 + i * 46), line, font=small, fill="#b9b39c", anchor="mm")
    draw.rectangle([40, 40, W - 40, H - 40], outline="#6b6650", width=3)
    draw.text((W - 60, 70), f"{index + 1}/{total}", font=small, fill="#8f8a72", anchor="rm")

    ffmpeg = str(ROOT / "bin" / "ffmpeg")
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-t", f"{SECONDS:.6f}", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-shortest",
         str(dest)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    arr = np.asarray(base)
    for f in range(frames):
        shift = int(10 * np.sin(f / frames * np.pi))          # 缓慢推拉，制造真实微动
        crop = np.roll(arr, shift, axis=1)
        proc.stdin.write(np.ascontiguousarray(crop).tobytes())
    proc.stdin.close()
    err = proc.stderr.read().decode()
    if proc.wait():
        raise SystemExit(f"ffmpeg 失败：{err[-600:]}")


def textwrap_lines(text, width):
    text = (text or "").strip()
    return [text[i:i + width] for i in range(0, len(text), width)][:2]


def main():
    CLIPS.mkdir(parents=True, exist_ok=True)
    project = json.loads((HERE / "story.json").read_text())
    agnes = [s for s in project["shots"] if s["kind"] == "agnes"]
    receipts = {"model": "agnes-video-v2.0", "project": project.get("id") or "monalisa",
                "note": "SLATE TEST FIXTURE — 不是 Agnes 产物，只用于本地跑通 render 闸门",
                "shots": {}}
    for i, shot in enumerate(project["shots"]):
        if shot["kind"] != "agnes":
            continue
        dest = CLIPS / f"{shot['id']}.mp4"
        if not dest.exists() or dest.stat().st_size < 10_000:
            print(f"SLATE {shot['id']} ({i + 1}/{len(agnes)})", flush=True)
            slate(shot["id"], i, len(agnes), shot["kind"], shot["purpose"], dest)
        digest = render.digest(dest)
        receipts["shots"][shot["id"]] = {
            "status": "completed", "sha256": digest,
            "request_hash": request_hash(project, shot),
            "seconds": SECONDS, "slate": True,
        }
    (WORK / "results.json").write_text(json.dumps(receipts, ensure_ascii=False, indent=2))
    out = WORK / "slate-preview.mp4"
    cmd = [sys.executable, str(HERE / "render.py"), "--sources", str(CLIPS), "--work", str(WORK / "r"),
           "--output", str(out), "--results", str(WORK / "results.json"), "--skip-asr"]
    print("RENDER", " ".join(cmd[1:]), flush=True)
    env = {"PATH": f"{ROOT / 'bin'}:" + __import__("os").environ.get("PATH", ""),
           "HOME": str(Path.home())}
    import os
    full = dict(os.environ, **env)
    subprocess.run(cmd, env=full, check=True)
    print("SLATE_RENDER_DONE", out)


if __name__ == "__main__":
    main()
