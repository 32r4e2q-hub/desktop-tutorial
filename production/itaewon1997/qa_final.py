#!/usr/bin/env python3
"""成片抽帧验收：每镜取中点一帧（含烧录字幕），拼成 2 张联系表 + 片尾两帧 + 封面缩略，供人工目检。"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DELIVERY = ROOT / "work/itaewon1997/delivery"
OUT = HERE / "qa_final"


def main():
    OUT.mkdir(exist_ok=True)
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    film = DELIVERY / "Itaewon1997_Final.mp4"
    frames = []
    for s in story["shots"]:
        t = s["start"] + min(s["duration"] - 0.3, 0.25 + 2.0)
        dest = OUT / f"_{s['id']}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(film), "-frames:v", "1", "-vf", "scale=640:360", str(dest)], check=True)
        frames.append((s["id"], dest))
    for i in range(0, 30, 15):
        sheet = Image.new("RGB", (1920, 360 * 5))
        for k, (sid, p) in enumerate(frames[i:i + 15]):
            im = Image.open(p).convert("RGB"); ImageDraw.Draw(im).text((8, 6), sid, fill=(255, 255, 0))
            sheet.paste(im, ((k % 3) * 640, (k // 3) * 360))
        sheet.save(OUT / f"sheet{i // 15 + 1}.jpg", quality=82)
    end = Image.new("RGB", (1920, 360))
    for k, t in enumerate((177.0, 178.6, 179.6)):
        p = OUT / f"_end{k}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t}", "-i", str(film), "-frames:v", "1", "-vf", "scale=640:360", str(p)], check=True)
        end.paste(Image.open(p).convert("RGB"), (k * 640, 0))
    end.save(OUT / "ending.jpg", quality=85)
    cov = Image.open(DELIVERY / "Itaewon1997_Cover.png").convert("RGB"); cov.thumbnail((1280, 720)); cov.save(OUT / "cover_preview.jpg", quality=88)
    for p in OUT.glob("_*.jpg"): p.unlink()
    for n in ("audio_report.json", "render_report.json", "captions.srt"):
        (OUT / n).write_bytes((DELIVERY / n).read_bytes())
    print("qa_final written")


if __name__ == "__main__":
    sys.exit(main())
