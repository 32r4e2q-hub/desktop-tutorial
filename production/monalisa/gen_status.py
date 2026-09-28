#!/usr/bin/env python3
"""看一眼 Agnes 生成还剩几镜（不联网、不装依赖、随时可跑）。

Colab 那种「一格一格跑」的场景最需要的就是这个：跑完一格先执行本脚本，
它会说清楚「已完成多少、还差哪些、下一步该敲哪条命令」。判断依据只有两个文件：
story.json（要求哪些镜头）与 results.json（工作流逐镜写的收据）。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def main():
    plan = json.loads((HERE / "story.json").read_text())
    need = [s["id"] for s in plan["shots"] if s["kind"] == "agnes"]
    cards = [s["id"] for s in plan["shots"] if s["kind"] == "graphic"]
    rpath = HERE / "results.json"
    done, broken = [], []
    if rpath.exists():
        doc = json.loads(rpath.read_text())
        for sid, row in doc.get("shots", {}).items():
            if row.get("status") == "completed":
                (done if row.get("video_url") else broken).append(sid)
    else:
        doc = {}
    src = REPO / "work" / "monalisa" / "sources"
    have_files = sorted(p.stem for p in src.glob("S??.mp4")) if src.exists() else []
    missing_file = [s for s in done if s not in set(have_files)]
    rest = [s for s in need if s not in set(done)]
    print(f"计划：{len(need)} 个 Agnes 镜头 + {len(cards)} 张信息卡（卡片本地画，不占额度）")
    print(f"已生成：{len(done)}/{len(need)}    素材文件在本地：{len(have_files)}")
    if doc.get("phase"):
        print(f"收据里的 phase：{doc['phase']}")
    if broken:
        print(f"⚠ 收据说完成但没有下载链接（重跑会自动补）：{','.join(sorted(broken))}")
    if missing_file:
        print(f"⚠ 有收据但本地缺文件（断线清的）：{','.join(sorted(missing_file))} → 重跑会用 video_url 直接回填，不重新生成")
    if not rest:
        print("\n镜头齐了 → 下一步：bash production/monalisa/本机出片.sh --render-only")
        return 0
    print(f"还差 {len(rest)} 镜：{','.join(rest)}")
    print("→ 再跑一次刚才那条命令/那一格即可续跑（已完成的按 SHA-256 复用，不重复烧额度）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
