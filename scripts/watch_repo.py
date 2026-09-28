#!/usr/bin/env python3
"""盯着**用户自己仓库**的 Actions 进度 + 逐格质检结论，一条命令出报表。

为什么需要它：沙箱这个身份对 `ozzy282576/monalisa-film` 是**只读**的（写会 403
`Resource not accessible by integration`），日志正文的下载域名也被沙箱网络切掉，
所以能用的信号只有两类：

1. `gh api repos/<repo>/actions/runs` —— 每条工作流最新一次的状态 / 跑了多久 / 第几次 attempt；
2. `git fetch` 该分支，读被 Actions 回推的 `results.json` / `qa/` / `QA_REPORT.md`
   （这正是工作流要把结论 commit 回分支的原因）。

用法：
    python3 scripts/watch_repo.py                       # 看一次
    python3 scripts/watch_repo.py --follow 120          # 每 2 分钟刷新，Ctrl-C 停
    python3 scripts/watch_repo.py --repo USER/REPO --branch main --cache /tmp/watch
退出码：0 素材齐 + QA 全放行；1 还有镜头待重做 / 有工作流失败；2 还没开始跑。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

WORKFLOWS = {
    "monalisa-gen.yml": "Agnes 生成",
    "monalisa-render.yml": "出片（三道闸门）",
    "monalisa-verbatim.yml": "逐字听检",
}


def sh(cmd: list[str], cwd: Path | None = None, timeout: int = 180) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or "") + (("\n" + r.stderr) if r.returncode else "")
    return r.returncode, out.strip()


def gh_runs(repo: str) -> dict[str, dict]:
    """每条工作流的最新一次运行；gh 不可用/没权限就返回空表，不影响 git 那半边。"""
    rc, out = sh(["gh", "api", f"repos/{repo}/actions/runs?per_page=50", "--jq",
                  "[.workflow_runs[] | {name, status, conclusion,"
                  " started_at, run_attempt, html_url}]"])
    if rc != 0:
        return {}
    try:
        rows = json.loads(out or "[]")
    except json.JSONDecodeError:
        return {}
    got: dict[str, dict] = {}
    for r in rows:                       # 返回顺序就是"新→旧"，先命中的那条即最新
        name = r.get("name") or ""
        for label in WORKFLOWS.values():
            if label in name:
                got.setdefault(label, r)
    return got


def sync(repo: str, branch: str, cache: Path, fresh: bool) -> Path | None:
    url = f"https://github.com/{repo}.git"
    if fresh and cache.exists():
        shutil.rmtree(cache)
    if not (cache / ".git").exists():
        cache.mkdir(parents=True, exist_ok=True)
        rc, out = sh(["git", "clone", "-q", "--depth", "1", "-b", branch, url, str(cache)], timeout=900)
        if rc != 0:
            print(f"（clone 失败：{out.splitlines()[-1] if out else '仓库还是空的？'}）")
            return None
    else:
        sh(["git", "-C", str(cache), "fetch", "-q", "--depth", "1", "origin", branch], timeout=900)
        sh(["git", "-C", str(cache), "reset", "-q", "--hard", "FETCH_HEAD"], timeout=120)
    return cache


def tally(root: Path) -> tuple[int, int, str]:
    """results.json 里成功的镜头数 / 计划应生成的镜头数 / 失败摘要。"""
    proj = root / "production" / "monalisa"
    plan = proj / "story.json"
    res = proj / "results.json"
    if not plan.exists():
        return 0, 0, "没找到 story.json（分支不对？）"
    want = [s["id"] for s in json.loads(plan.read_text())["shots"] if s.get("kind") == "agnes"]
    if not res.exists():
        return 0, len(want), "results.json 还没被推回来（生成还没产出第一个镜头）"
    try:
        data = json.loads(res.read_text())
    except json.JSONDecodeError:
        return 0, len(want), "results.json 读不出来"
    recs = data.get("shots", data) if isinstance(data, dict) else data
    ok = [k for k, v in (recs.items() if isinstance(recs, dict) else {})
          if isinstance(v, dict) and (v.get("sha256") or v.get("video_url")) and not v.get("error")]
    bad = [f"{k}:{(v.get('error') or '')[:60]}" for k, v in (recs.items() if isinstance(recs, dict) else {})
           if isinstance(v, dict) and v.get("error")]
    note = "；".join(bad[:4]) if bad else ""
    return len(ok), len(want), note


def qa_verdicts(root: Path) -> tuple[list[str], str]:
    proj = root / "production" / "monalisa"
    if not (proj / "qa_rejects.py").exists():
        return [], "qa_rejects.py 还没进仓库"
    rc, out = sh([sys.executable, str(proj / "qa_rejects.py")], cwd=root, timeout=600)
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if not lines:
        return [], f"qa_rejects 无输出（rc={rc}）"
    rejects = [x for x in lines[0].split(",") if x.strip()]
    return rejects, lines[-1]


def report(repo: str, branch: str, cache: Path | None, runs: dict, rejects: list[str], tail: str,
           ok: int, want: int, note: str) -> int:
    print(f"\n=== {repo} @ {branch} — {time.strftime('%H:%M:%S')} ===")
    if runs:
        for label, r in sorted(runs.items()):
            st, cc = r.get("s"), r.get("c")
            mark = {"completed": {"success": "✓", "failure": "✗", "cancelled": "⚠"}.get(cc, "•"),
                    "in_progress": "▶", "queued": "⏳", "waiting": "⏸"}.get(st, "•")
            print(f"  {mark} {label:16s} {st}{('/' + str(cc)) if cc and cc != 'skipped' else ''}"
                  f"  起于 {r.get('t','-')[:16]}  第 {r.get('a',1)} 次")
            if cc == "failure":
                print(f"      {r.get('u')}")
    else:
        print("  （还没查到任何 workflow run —— 说明 Actions 没被点火，或刚推完还没排队）")
    if cache is None:
        print(f"  分支 {branch} 还没内容 → 搬家那一格跑成功了吗？")
        return 2
    started = not note.startswith("results.json 还没")
    print(f"  素材 {ok}/{want} 镜" + ("" if started else "（results.json 还没被推回来 → 生成还没产出第一镜）")
          + (f"（异常：{note}）" if started and note else ""))
    if started:
        print(f"  逐格 QA：{tail if len(tail) < 400 else tail[:400] + '…'}")
    if not started:
        runs_busy = [r for r in runs.values() if r.get("status") in ("queued", "in_progress", "waiting")]
        print("  → " + ("工作流在跑，等着" if runs_busy else "还没点火（见操作卡第 2 步）"))
        return 2
    if ok >= want and not rejects:
        print("  → 可以进出片闸门")
        return 0
    if rejects:
        payload = json.dumps({"workers": 1, "only": ",".join(rejects)}, ensure_ascii=False)
        print(f"  → 请在 Actions 里对「Agnes生成」Run workflow，payload 贴：{payload}")
        return 1
    print("  → 还在生成中，继续盯")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="ozzy282576/monalisa-film")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--cache", default="/tmp/watch-repo")
    ap.add_argument("--fresh", action="store_true", help="重新 clone（默认增量 fetch）")
    ap.add_argument("--follow", type=int, default=0, metavar="秒", help="循环刷新，直到全放行/手动停")
    args = ap.parse_args()
    cache_dir = Path(args.cache)
    first = True
    while True:
        runs = gh_runs(args.repo)
        root = sync(args.repo, args.branch, cache_dir, args.fresh and first)
        ok = want = 0
        note = tail = ""
        rejects: list[str] = []
        if root is not None:
            ok, want, note = tally(root)
            rejects, tail = qa_verdicts(root)
        rc = report(args.repo, args.branch, root, runs, rejects, tail, ok, want, note)
        first = False
        args.fresh = False
        if not args.follow or rc == 0:
            return rc
        time.sleep(args.follow)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n停了")
        sys.exit(0)
