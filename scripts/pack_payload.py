#!/usr/bin/env python3
"""把"过墙只需要贴文本"的那套最小可跑载荷打成若干 base64 段，逐段贴进聊天。

背景：沙箱的出口只允许 GitHub 一类域名，浏览器下载入口也被挡，所以 6 MB 的二进制
（配音 mp3）无论如何都过不去；能过去的只有文本。于是：

* 载荷 = 跑完整条流水线**必需**的代码 + `story.json`（片子本身），xz -9 之后 base64；
* 配音不在载荷里 —— 到对面由 `make_voice.py`（edge-tts，免费）重生并自动配速；
* 每一段自带长度与 sha256，组装格会逐段核对，贴错/贴漏直接指出是第几段。

用法：
    python3 scripts/pack_payload.py                      # 打印所有段（贴聊天用）
    python3 scripts/pack_payload.py --blocks 4 --out /tmp/payload
    python3 scripts/pack_payload.py --tree /tmp/monalisa-move     # 从已改写好的搬家树打包
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import lzma
import tarfile
from pathlib import Path

# 必需集：渲染/生成/QC 的闭包 + 三个 marker 工作流。别的一律不带（文档、别的片子、脚手架）。
NEEDED = [
    "production/monalisa/story.json",
    "production/monalisa/generate.py",
    "production/monalisa/media.py",
    "production/monalisa/throttle.py",
    "production/monalisa/build_audio.py",
    "production/monalisa/render.py",
    "production/monalisa/slate_render.py",
    "production/monalisa/make_cuts.py",
    "production/monalisa/plan_cuts.py",
    "production/monalisa/clause_times.py",
    "production/monalisa/tighten_pauses.py",
    "production/monalisa/make_voice.py",
    "production/monalisa/scan_qa.py",
    "production/monalisa/qa_rejects.py",
    "production/monalisa/gen_status.py",
    "production/monalisa/watch_gen.py",
    "production/monalisa/本机出片.sh",
    "production/monalisa/QA_REPORT.md",
    "production/monalisa/GEN_REQUEST",
    "production/monalisa/RENDER_REQUEST",
    "production/monalisa/VERBATIM_REQUEST",
    "production/agnes_video.py",
    "production/verbatim_check.py",
    "production/review_film.py",
    "production/requirements.txt",
    ".github/workflows/monalisa-gen.yml",
    ".github/workflows/monalisa-render.yml",
    ".github/workflows/monalisa-verbatim.yml",
]


def build(tree: Path) -> tuple[bytes, list[str]]:
    missing = [f for f in NEEDED if not (tree / f).is_file()]
    present = [f for f in NEEDED if (tree / f).is_file()]
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as t:
        for f in present:
            t.add(tree / f, arcname=f)
    return lzma.compress(buf.getvalue(), preset=9, filters=[{"id": lzma.FILTER_LZMA2, "preset": 9}]), missing


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", default="/home/user/desktop-tutorial", help="从哪个目录取文件")
    ap.add_argument("--blocks", type=int, default=4)
    ap.add_argument("--out", default="/tmp/payload", help="把每段写成 p1.b64..pN.b64 并打印贴用格式")
    args = ap.parse_args()

    tree = Path(args.tree)
    packed, missing = build(tree)
    b64 = base64.b64encode(packed).decode()
    n = len(b64)
    size = -(-n // args.blocks)
    chunks = [b64[i * size:(i + 1) * size] for i in range(args.blocks)]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps({
        "tar_xz_bytes": len(packed), "base64_bytes": n, "blocks": len(chunks),
        "sha256_tar_xz": hashlib.sha256(packed).hexdigest(),
        "files": [f for f in NEEDED if (tree / f).is_file()],
        "missing": missing,
        "each": [{"i": i + 1, "chars": len(c), "sha256_12": hashlib.sha256(c.encode()).hexdigest()[:12]}
                 for i, c in enumerate(chunks)],
    }, ensure_ascii=False, indent=2) + "\n")
    for i, c in enumerate(chunks):
        (out / f"p{i + 1}.b64").write_text(c)

    total = sum(len(c) for c in chunks)
    print(f"# 载荷：{len(packed) / 1024:.1f} KB（xz）→ base64 {total / 1024:.1f} KB，分 {len(chunks)} 段，"
          f"每段约 {size / 1024:.1f} KB")
    print(f"# 整包 sha256(前12)：{hashlib.sha256(packed).hexdigest()[:12]}   文件 {len(NEEDED) - len(missing)} 个"
          + (f"   缺：{missing}" if missing else ""))
    print(f"# 段清单：" + "  ".join(f"[{i + 1}] {len(c)} 字 /{hashlib.sha256(c.encode()).hexdigest()[:8]}"
                                   for i, c in enumerate(chunks)))
    for i, c in enumerate(chunks):
        print(f"\n----- 第 {i + 1}/{len(chunks)} 段（{len(c)} 字符，整段复制，别改内容）-----\n{c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
