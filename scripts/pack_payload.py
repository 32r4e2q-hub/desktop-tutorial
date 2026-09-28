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
import re
import tarfile
from pathlib import Path

# 种子集，真正的载荷由 closure() 求出来的传递闭包决定（本地 import + 工作流里写死的仓库路径）。
# 别的一律不带：文档、别的片子、脚手架、6 段配音 mp3（对面用 edge-tts 现做）。
SEED = [
    "production/monalisa/story.json",
    "production/monalisa/generate.py",
    "production/run_project.sh",
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
    "production/agnes_video.py",
    "production/verbatim_check.py",
    "production/review_film.py",
    "production/requirements.txt",
    ".github/workflows/monalisa-gen.yml",
    ".github/workflows/monalisa-render.yml",
    ".github/workflows/monalisa-verbatim.yml",
]


LOCAL = ("production/monalisa", "production", "scripts")
DROP = {"production/new_topic.py"}

IMPORT_RE = re.compile(r"^(?:from|import)\s+([a-zA-Z_][\w]*)\b", re.M)
PATH_RE = re.compile(r"(?:production|scripts|\.github)/[\w./-]+\.(?:py|sh|yml|json|md|txt)")


def closure(tree: Path, seed: list[str]) -> list[str]:
    """从种子出发求闭包：本地模块 import + 工作流里写死的仓库路径，全部并进来。

    手工挑清单一定会漏（曾经漏了 run_project.sh，render 作业直接起不来），所以这里让
    打包器自己去读依赖。只认 production/ production/monalisa/ scripts/ 三个目录里的 .py，
    其它 import（PIL/numpy/av…）属于 pip 依赖，由安装阶梯负责。
    """
    have = set(seed) - DROP
    todo, extra = list(seed), []
    dirs = [tree / d for d in LOCAL]
    while todo:
        f = todo.pop()
        fp = tree / f
        if not fp.is_file():
            continue
        text = fp.read_text(encoding="utf-8", errors="ignore")
        if f.endswith((".py", ".sh", ".yml")):
            for m in IMPORT_RE.findall(text):
                for d in LOCAL:
                    cand = f"{d}/{m}.py"
                    if (tree / cand).is_file() and cand not in have:
                        have.add(cand); extra.append(cand); todo.append(cand)
            for cand in PATH_RE.findall(text):
                if (tree / cand).is_file() and cand not in have:
                    have.add(cand); extra.append(cand); todo.append(cand)
    # 脚手架不进载荷：new_topic.py 只在建项目时用，运行时不需要（省 6 KB 就是省一次粘贴）
    return sorted(f for f in have if f not in DROP)


def build(tree: Path) -> tuple[bytes, list[str]]:
    needed = closure(tree, SEED)
    build.files = needed            # 给 main() 打印清单用
    missing = [f for f in SEED if not (tree / f).is_file()]
    present = [f for f in needed if (tree / f).is_file()]
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as t:
        for f in present:
            t.add(tree / f, arcname=f)
    return lzma.compress(buf.getvalue(), preset=9), missing


def emit_cells(dest: Path, chunks: list[str], whole_sha: str, total_chars: int, files: list[str]) -> None:
    """写出「从文件面板复制即可」的 Colab 格子：格子很小，大块内容留在 pN.b64 里各自复制。

    格子内容取自 `production/templates/paste-cells/`，只做占位替换（不用 str.format ——
    模板里有 f-string 的花括号，会被 format 吃掉）。
    """
    tpl = Path(__file__).resolve().parents[1] / "production" / "templates" / "paste-cells"
    dest.mkdir(parents=True, exist_ok=True)

    def fill(name: str, **kw: object) -> str:
        text = (tpl / name).read_text()
        for k, v in kw.items():
            text = text.replace("{" + k + "}", str(v))
        return text

    n = len(chunks)
    for i, c in enumerate(chunks):
        (dest / f"{i + 1:02d}-贴第{i + 1}段.py").write_text(
            fill("贴段.py", IDX=i + 1, CHARS=len(c), SHA12=hashlib.sha256(c.encode()).hexdigest()[:12]))
    (dest / f"{n + 1:02d}-组装并自检.py").write_text(fill("组装并自检.py", N=n, WHOLE12=whole_sha[:12]))
    (dest / f"{n + 2:02d}-配音重生.py").write_text(fill("配音重生.py"))
    (dest / f"{n + 3:02d}-推到你的仓库.py").write_text(fill("推到你的仓库.py"))

    lines = ["# 照这个顺序贴（一次配好，之后都不用再贴）", "",
             "前提：你现在看的是 Arena 沙箱的**文件面板**，`dist/payload/` 下面这些都是文本文件，",
             "点开就能全选复制 —— 复制走的是文件本身，不经过聊天转述，所以不会抄错字符。",
             "",
             "1. 开 Colab：<https://colab.research.google.com/#create=new> → New notebook",
             "2. 逐格来（每格两次复制）：",
             ""]
    for i in range(n):
        lines.append(f"   - 面板打开 `dist/payload/{i + 1:02d}-贴第{i + 1}段.py` → 全选复制 → 粘成 Colab 第 {i + 1} 格；")
        lines.append(f"     再把 `dist/payload/p{i + 1}.b64` 全选复制 → 粘进该格的三引号之间（替换那行提示）→ 运行该格")
    lines += [f"   - 每格自己会报 `✓ 对上了`；报 ✗ 就回面板把那一段整个重复制一次（防手滑漏尾巴）",
              f"3. {n} 段全绿 → 运行 `{n + 1:02d}-组装并自检.py`（整包 sha256 + 解出项目 + `--validate`）",
              f"4. 运行 `{n + 2:02d}-配音重生.py`：edge-tts 合成 6 段解说、自动配速、按实测重排切点",
              f"5. 运行 `{n + 3:02d}-推到你的仓库.py`：贴一次 PAT → 推上去 → Actions 自动点火跑 38 镜",
              "",
              "**为什么绕这一圈**：沙箱出口只放行 GitHub 一类域名，预览端口又只认浏览器会话，",
              "所以任何「下载文件」的按钮都是死的；唯一稳的通道是**文本 + 你在面板里复制**。",
              "6 MB 的配音 mp3 过不来，于是改成到你那边用免费的 edge-tts 重生 —— 音色和原先试听选定的",
              "那个会不同，但节奏由脚本按 `render.py` 的实测判据（0.86 ≤ tempo ≤ 1.10）自动配回去；",
              "批准的成片 tempo 是 1.0662，重生后一般落在 1.00~1.07。",
              "",
              f"载荷：{n} 段 / 共 {total_chars} 字符 base64；整包 xz sha256 前 12 位 `{whole_sha[:12]}`；",
              f"文件 {len(files)} 个：", ""]
    lines += [f"- `{f}`" for f in files]
    (dest / "README-照这个顺序贴.md").write_text("\n".join(lines) + "\n")
    print(f"格子已写到 {dest}（{n} 段 + 组装 + 配音 + 推仓库 + README）")



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", default="/home/user/desktop-tutorial", help="从哪个目录取文件")
    ap.add_argument("--blocks", type=int, default=4)
    ap.add_argument("--out", default="/tmp/payload", help="把每段写成 p1.b64..pN.b64 并打印贴用格式")
    ap.add_argument("--emit", default="", metavar="目录",
                    help="额外写出可贴的 Colab 格子（每段一格 + 组装 + 配音 + 推仓库 + README）")
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
        "files": [f for f in build.files if (tree / f).is_file()],
        "missing": missing,
        "each": [{"i": i + 1, "chars": len(c), "sha256_12": hashlib.sha256(c.encode()).hexdigest()[:12]}
                 for i, c in enumerate(chunks)],
    }, ensure_ascii=False, indent=2) + "\n")
    for i, c in enumerate(chunks):
        (out / f"p{i + 1}.b64").write_text(c)

    total = sum(len(c) for c in chunks)
    print(f"# 载荷：{len(packed) / 1024:.1f} KB（xz）→ base64 {total / 1024:.1f} KB，分 {len(chunks)} 段，"
          f"每段约 {size / 1024:.1f} KB")
    print(f"# 整包 sha256(前12)：{hashlib.sha256(packed).hexdigest()[:12]}   文件 {len(build.files)} 个"
          + (f"   缺：{missing}" if missing else ""))
    print(f"# 段清单：" + "  ".join(f"[{i + 1}] {len(c)} 字 /{hashlib.sha256(c.encode()).hexdigest()[:8]}"
                                   for i, c in enumerate(chunks)))
    for i, c in enumerate(chunks):
        print(f"\n----- 第 {i + 1}/{len(chunks)} 段（{len(c)} 字符，整段复制，别改内容）-----\n{c}")
    if args.emit:
        emit_cells(Path(args.emit), chunks, hashlib.sha256(packed).hexdigest(), total,
                   [f for f in build.files if (tree / f).is_file()])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
