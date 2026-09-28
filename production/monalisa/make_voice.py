#!/usr/bin/env python3
"""在没有 Arena TTS 的机器上重生 6 段解说，并把 `audio/` 与 `audio/manifest.json` 一次配对好。

为什么需要它
------------
6 段配音原本是**沙箱自带的 TTS** 合成的（那个端点只有沙箱调得到）。当整个项目只能靠
「纯文本粘贴」过墙时，5.6 MB 的 mp3 是过不去的 —— 文本载荷再怎么压也只有 ~70 KB。
所以声音必须在你的机器上重新合成。这里用免费的 edge-tts（不需要任何 key，中文神经音色），
并且**不靠手感调语速**，而是按 `render.py` 真正的判据反推：

    usable = DURATION - INTRO - OUTRO - GAP * (章节数 - 1)     # 本片 = 180-0.6-6-1.08*5 = 168.0 s
    tempo  = 收紧后的原始总时长 / usable                        # render 要求 0.86 ≤ tempo ≤ 1.10

批准的成片节奏是 tempo ≈ 1.0662（解说被均匀加速 6.6%）。换音色最容易搞坏的就是这个数：
读慢了 tempo 冲高 → render 直接拒绝渲染。所以本脚本按轮次自动改 edge-tts 的 `rate`，
每轮都跑 `tighten_pauses.py` 之后**实测**，直到 tempo 落进 [0.98, 1.09] 才收手。

自检后门
--------
`--backend test` 不调网络，而是拿仓库里已有的参考 mp3 做 `atempo` 变速来冒充新配音，
用来在没网的环境里验证「测速 → 配速 → 写 manifest → 过 validate」这条链是对的。

用法：
    python3 production/monalisa/make_voice.py                      # 正常重生
    python3 production/monalisa/make_voice.py --voice zh-CN-XiaoxiaoNeural
    python3 production/monalisa/make_voice.py --only N03           # 只重做一段（先看别段是否仍配）
    python3 production/monalisa/make_voice.py --backend test       # 离线自检
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
RENDER_PY = HERE / "render.py"
AUDIO = HERE / "audio"
RAW = AUDIO / "raw"


def constants() -> tuple[float, float, float, float]:
    """从 render.py 源码里取 DURATION/INTRO/OUTRO/GAP，避免 import 拉起 PIL+numpy。"""
    text = RENDER_PY.read_text()
    def grab(name, default):
        m = re.search(rf"^{name}\s*=\s*([0-9.]+)", text, re.M)
        return float(m.group(1)) if m else default
    return grab("DURATION", 180.0), grab("INTRO", 0.6), grab("OUTRO", 6.0), grab("GAP", 1.08)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def ffmpeg_bin() -> str:
    """ffmpeg：PATH 里有就用，没有就退到仓库自带的静态二进制（本机出片.sh 会准备）。"""
    return shutil.which("ffmpeg") or str(HERE.parents[1] / "bin" / "ffmpeg")


def seconds(path: Path) -> float:
    """时长一律走 media.probe —— 它在没有 ffprobe 的机器上自动改用 pyav，两端等价。"""
    import media
    return float(media.probe(path)["duration"])


def tts_edge(text: str, voice: str, rate: int, dest: Path) -> None:
    import edge_tts
    async def go():
        await edge_tts.Communicate(text=text, voice=voice, rate=f"{rate:+d}%").save(str(dest))
    asyncio.run(go())


def tts_test(ref: Path, rate: int, dest: Path) -> None:
    """离线自检：拿参考配音按 rate 变速，冒充一个新音色的产物。

    方向必须和 edge-tts 一致：``rate=+25%`` 是"读快 25%"→ 时长除以 1.25；
    atempo 的倍率就是那个除数，所以 factor = 1 + rate/100（>1 变快变短）。
    """
    factor = max(0.5, min(2.0, 1.0 + rate / 100.0))
    subprocess.run([ffmpeg_bin(), "-v", "error", "-y", "-i", str(ref),
                    "-filter:a", f"atempo={factor:.4f}", "-q:a", "6", str(dest)], check=True)


def tighten() -> None:
    subprocess.run([sys.executable, str(HERE / "tighten_pauses.py")], check=True,
                   capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="zh-CN-YunyangNeural",
                    help="edge-tts 音色（新闻男声；想换女声用 zh-CN-XiaoxiaoNeural）")
    ap.add_argument("--backend", choices=["edge", "test"], default="edge")
    ap.add_argument("--only", default="", help="只重做这几段：N01,N04")
    ap.add_argument("--rate", type=int, default=8, help="起始语速 %%（脚本会自动修）")
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--lo", type=float, default=0.98, help="tempo 下限（低于它说明读太快）")
    ap.add_argument("--hi", type=float, default=1.09, help="tempo 上限（高于它 render 会拒渲染）")
    ap.add_argument("--ref", default="", help="--backend test 用的参考 mp3 目录，默认用 audio/ 现成的")
    args = ap.parse_args()

    story = json.loads((HERE / "story.json").read_text())
    chapters = story["chapters"]
    todo = {x.strip() for x in args.only.split(",") if x.strip()}
    if todo - {c["id"] for c in chapters}:
        raise SystemExit(f"--only 里有不存在的章节号：{sorted(todo)}")
    duration, intro, outro, gap = constants()
    usable = duration - intro - outro - gap * (len(chapters) - 1)
    RAW.mkdir(parents=True, exist_ok=True)
    refdir = Path(args.ref) if args.ref else AUDIO
    if args.backend == "test" and not any(refdir.glob("N0*.mp3")):
        print("（自检模式没有参考 mp3，改用 6 秒静音当配音 —— 只验流程，不验节奏）")

    rate = args.rate
    for rnd in range(1, args.rounds + 1):
        for c in chapters:
            if todo and c["id"] not in todo:
                continue
            dest = RAW / f"{c['id']}.mp3"
            if args.backend == "edge":
                tts_edge(c["text"], args.voice, rate, dest)
            else:
                ref = refdir / f"{c['id']}.mp3"
                if ref.is_file():
                    tts_test(ref, rate, dest)
                else:
                    subprocess.run([ffmpeg_bin(), "-v", "error", "-y", "-f", "lavfi",
                                    "-i", "anullsrc=r=48000:cl=mono", "-t", "6", str(dest)], check=True)
        for c in chapters:                       # 没重做的章节，把现有成品搬回 raw，保证 tighten 全量覆盖
            if not (RAW / f"{c['id']}.mp3").exists() and (AUDIO / f"{c['id']}.mp3").is_file():
                (RAW / f"{c['id']}.mp3").write_bytes((AUDIO / f"{c['id']}.mp3").read_bytes())
        tighten()

        per = {}
        for c in chapters:
            p = AUDIO / f"{c['id']}.mp3"
            if not p.is_file():
                raise SystemExit(f"tighten_pauses.py 没产出 {p}")
            per[c["id"]] = seconds(p)
        total = sum(per.values())
        tempo = total / usable
        print(f"第 {rnd} 轮：rate={rate:+d}%  各段 {[round(v, 1) for v in per.values()]}  "
              f"总计 {total:.2f}s / 可用 {usable:.1f}s → tempo={tempo:.4f}")
        if args.lo <= tempo <= args.hi:
            break
        if args.backend == "test" and not any((refdir / f"{c['id']}.mp3").is_file() for c in chapters):
            print("  （静音占位，节奏无法收敛 —— 只验流程，直接收尾）")
            break
        nxt = max(-15, min(35, rate + round((total / (usable * 1.05) - 1) * 100)))
        if nxt == rate:
            print(f"  （rate 已到可给范围的边界，停在 {rate:+d}%：tempo={tempo:.4f}）")
            break
        rate = nxt

    manifest_path = AUDIO / "manifest.json"
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    doc = {
        "voice_id": old.get("voice_id", "voice-00"),
        "language": old.get("language", "zh-CN"),
        "selection": (f"{args.backend}:{args.voice}（rate={rate:+d}%，tempo={tempo:.4f}，"
                      f"由 make_voice.py 自动配速；原音色见 git 历史）"),
        "clips": [{"id": c["id"], "file": f"{c['id']}.mp3",
                   "sha256": digest(AUDIO / f"{c['id']}.mp3"), "text": c["text"]} for c in chapters],
        "post_processing": old.get("post_processing", ""),
        "postprocess": old.get("postprocess", "tighten_pauses.py：只剪过长静音，逐字不动"),
    }
    manifest_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    print(f"\n配音就位：{len(chapters)} 段 / {total:.2f}s（加速 {tempo:.4f}× 后正好铺满 {usable:.1f}s 窗口）")
    print(f"manifest 已写：{manifest_path.relative_to(HERE.parent.parent)}")
    ok = args.lo <= tempo <= args.hi
    if not ok:
        print(f":: 警告 :: tempo={tempo:.4f} 没进 [{args.lo}, {args.hi}]，render 可能拒绝渲染；"
              "可以 --rate 手动给一个值再跑")
    if args.backend == "edge":
        print("下一步：python3 production/monalisa/clause_times.py && python3 production/monalisa/make_cuts.py")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
