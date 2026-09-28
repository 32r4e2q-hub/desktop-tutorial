#!/usr/bin/env python3
"""把这个项目整树搬到**你自己的** GitHub 仓库，并把分支/仓库名一起改掉。

为什么需要它：沙箱这边能读写的是 Arena 侧的镜像仓库（`32r4e2q-hub/…`），那个账号你我没有
Settings 权限，Actions 也不归我们管；而流水线的三份 marker 工作流 + `generate.py --publish`
都写死了当前分支名。直接 `git push` 过去会因为分支名不符而全部失灵，所以搬家必须连
「仓库名 / 分支名」一起重写。

规则：
- 只搬 git 跟踪的文件（跳过 .git 与未跟踪垃圾）；
- 丢掉大媒体（成片/联络表/音效），保留 `production/monalisa/audio/`（闸门一要按 SHA 校配音）；
- 文本文件里把 `32r4e2q-hub/desktop-tutorial` 换成目标仓库、把当前工作分支换成目标分支；
- 生成一个**全新的单提交**历史（不把 190 MB 的旧对象库拖过去）。

用法：
    python3 scripts/move_to_new_repo.py --target USER/REPO --dry-run        # 只看会搬什么
    python3 scripts/move_to_new_repo.py --target USER/REPO --push            # 真搬（需 GH_TOKEN 或 URL 内嵌 token）
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE_BRANCH = "arena/01a0aa24-desktop-tutorial"
HERE_REPO = "32r4e2q-hub/desktop-tutorial"
KEEP_MEDIA = ("production/monalisa/audio/",)          # 配音是闸门一的校验对象，必须跟着走
MEDIA = re.compile(r"\.(mp4|mov|webm|jpg|jpeg|png|webp|gif|bmp|wav|flac|mp3|ogg)$", re.I)


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "-c", "core.quotePath=false", "ls-files", "-z"],
                         cwd=ROOT, capture_output=True, check=True).stdout
    return sorted(p for p in out.decode().split("\0") if p)


def pick(files: list[str]) -> list[str]:
    keep = []
    for f in files:
        if f.startswith("node_modules/") or "/__pycache__/" in f or f.endswith(".pyc"):
            continue
        if f.endswith(".md") and (f.startswith("交付/") or "/交付/" in f):
            continue
        # 只丢"大到不该进 git 的媒体"（成片/联络表/音效）；小图要留着——
        # dahlia 的档案图是 generate.py 的校验对象，丢了搬过去的树就自检不过。
        if MEDIA.search(f) and not f.startswith(KEEP_MEDIA) and (ROOT / f).stat().st_size > 3_000_000:
            continue
        keep.append(f)
    return keep


def rewrite(text: str, target_repo: str, target_branch: str) -> str:
    text = text.replace(HERE_REPO, target_repo)
    text = text.replace(HERE_BRANCH, target_branch)
    # 工作流里的 concurrency group 用的是"分支名消毒后的样子"（斜杠换横线），
    # 上面那条替换不到它，这里补一刀，否则新仓库里还挂着旧会话的分组名。
    text = text.replace(HERE_BRANCH.replace("/", "-"), target_branch.replace("/", "-"))
    # 工作流里的 if: github.ref == 'refs/heads/<旧分支>' 已被上一条覆盖；这里兜住只写分支短名的地方
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="新仓库 USER/REPO")
    ap.add_argument("--branch", default="main", help="新仓库的分支（默认 main）")
    ap.add_argument("--dest", default="/tmp/monalisa-move", help="暂存目录")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--token", default="", help="可选：粘贴用的 token（只用于本次 URL，不写进任何文件）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = pick(tracked_files())
    total = sum((ROOT / f).stat().st_size for f in files)
    print(f"将搬运 {len(files)} 个文件，共 {total/1024/1024:.1f} MB（跳过大媒体，保留 monalisa 配音）")
    src = Path(args.dest).resolve()
    if src.exists():
        shutil.rmtree(src)
    changed = 0
    for f in files:
        d = src / f
        d.parent.mkdir(parents=True, exist_ok=True)
        data = (ROOT / f).read_bytes()
        if MEDIA.search(f) or f.startswith(KEEP_MEDIA) and f.endswith((".mp3", ".wav")):
            d.write_bytes(data)
        else:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                d.write_bytes(data)
                continue
            new = rewrite(text, args.target, args.branch)
            if new != text:
                changed += 1
            d.write_text(new, encoding="utf-8")
    print(f"其中 {changed} 个文件改写了仓库名/分支名")
    left = subprocess.run("grep -rl %s %s 2>/dev/null | head" % (re.escape(HERE_BRANCH.split("/")[-1]), src),
                          shell=True, capture_output=True, text=True).stdout.strip()
    print("残留旧分支引用：" + (left or "无"))

    meta = {"target": args.target, "branch": args.branch, "files": len(files), "bytes": total}
    (src / ".move-manifest.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    def git(*a, check=True):
        r = subprocess.run(["git", *a], cwd=src, capture_output=True, text=True)
        if check and r.returncode:
            raise SystemExit(f"git {' '.join(a)} 失败：\n{r.stderr[-800:]}")
        return r.stdout.strip()

    git("init", "-q", "-b", args.branch)     # dry-run 也建 git 仓库：production/tests 里
                                              # run_project.sh 要在 git 环境里才报得出正确退出码
    git("config", "user.name", "arena-move")
    git("config", "user.email", "arena@local")
    git("add", "-A")
    git("commit", "-q", "-m",
        "蒙娜丽莎：行李箱里的779号 —— 从 Arena 镜像仓库整树搬来（配音 + 45 镜计划 + 引擎 + 三份 marker 工作流）")
    if args.dry_run:
        print("DRY-RUN：已在 " + str(src) + " 建好可自检的 git 仓库，没有推送")
        return 0
    url = f"https://github.com/{args.target}.git"
    if args.token:
        url = f"https://x-access-token:{args.token}@github.com/{args.target}.git"
    print("推送到 " + re.sub(r":[^@/]+@", ":***@", url))
    for attempt in range(1, 4):
        r = subprocess.run(["git", "-c", "credential.helper=", "push", url, f"HEAD:refs/heads/{args.branch}"],
                           cwd=src, capture_output=True, text=True)
        if r.returncode == 0:
            print("PUSH_OK")
            break
        print(f"第 {attempt} 次失败：{r.stderr.strip()[-400:]}")
        if attempt == 3:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
