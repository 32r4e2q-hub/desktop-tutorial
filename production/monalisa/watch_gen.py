"""盯 Agnes 生成进度（纯 git 版），跑完自动收 QA 表并跑逐格扫描。

为什么不用 production/monalisa/watch_run.py：那个走 `gh api`，需要 Actions 读权限；
本仓库的 Actions 接口对沙箱返回 404。而生成工作流是**逐镜把 results.json + qa/ commit
回分支**的，所以只靠 `git fetch` 就能看到进度，不需要任何 API 权限。

用法：
    python3 production/monalisa/watch_gen.py                 # 一直盯到生成结束（默认 6 小时预算）
    python3 production/monalisa/watch_gen.py --once          # 只打一次当前状态
    python3 production/monalisa/watch_gen.py --interval 30 --budget 7200

结束条件：story.json 里要求的 Agnes 镜头全部 completed（phase=selected_sources_ready），
或者 results.json 报 generation_incomplete / pipeline_failed。
正常结束时会在 work/monalisa/gen-done.flag 写一份摘要，并把 qa/*.jpg、qa/*.json、results.json
收进工作区，随后自动执行 scan_qa.py 做逐格初筛。
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BRANCH = "arena/01a0aa24-desktop-tutorial"
RESULTS = "production/monalisa/results.json"
DIAG = "production/monalisa/gen-diag.log"
QA_DIR = "production/monalisa/qa"


def git(*args, check=False):
    proc = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if check and proc.returncode:
        raise RuntimeError(proc.stderr.strip()[-400:])
    return proc


def show(path, rev="FETCH_HEAD"):
    proc = git("show", f"{rev}:{path}")
    return proc.stdout if proc.returncode == 0 else None


def ls_qa(rev="FETCH_HEAD"):
    proc = git("ls-tree", "--name-only", f"{rev}:{QA_DIR}")
    return [f"{QA_DIR}/{n}" for n in proc.stdout.split()] if proc.returncode == 0 else []


def status():
    """返回 (phase, done_ids, failed_ids, 全部需要的镜头号)。"""
    raw = show(RESULTS)
    required = [s["id"] for s in json.loads((HERE / "story.json").read_text())["shots"]
                if s["kind"] == "agnes"]
    if not raw:
        return None, [], [], required
    doc = json.loads(raw)
    shots = doc.get("shots", {})
    done = [sid for sid in required if shots.get(sid, {}).get("status") == "completed"]
    failed = [sid for sid, row in shots.items()
              if row.get("status") in ("failed", "blocked", "error")]
    return doc.get("phase"), done, sorted(failed), required


def pull():
    """把远程分支上已生成的 QA 与收据取进工作区（只覆盖这几个路径，不动其他文件）。"""
    git("checkout", "FETCH_HEAD", "--", RESULTS, QA_DIR, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--budget", type=int, default=6 * 3600)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--kick-after", type=int, default=0,
                    help="这么久还没开跑就重发一次 GEN_REQUEST（0=不重发）")
    ap.add_argument("--max-kicks", type=int, default=3)
    args = ap.parse_args()

    started = time.monotonic()
    last = None
    kicks = 0
    last_kick = time.monotonic()
    while True:
        stamp = time.strftime("%H:%M:%S")
        proc = git("fetch", "origin", BRANCH)
        if proc.returncode:
            print(f"[{stamp}] FETCH_RETRY {proc.stderr.strip()[-160:]}", flush=True)
        else:
            head = git("rev-parse", "--short", "FETCH_HEAD").stdout.strip()
            phase, done, failed, required = status()
            sheets = ls_qa()
            line = f"[{stamp}] head={head} phase={phase or '未开跑'} 完成 {len(done)}/{len(required)} 张 QA 表 {len(sheets)}"
            if failed:
                line += f" 失败 {','.join(failed)}"
            if line != last:
                print(line, flush=True)
                last = line
            if phase is None and args.kick_after and time.monotonic() - last_kick > args.kick_after \
                    and kicks < args.max_kicks and not args.once:
                kicks += 1
                last_kick = time.monotonic()
                marker = HERE / "GEN_REQUEST"
                marker.write_text(json.dumps({"workers": 2, "kick": kicks}) + "\n")
                git("add", "--", str(marker.relative_to(ROOT)))
                if git("diff", "--cached", "--quiet").returncode:
                    git("commit", "-m",
                        f"monalisa: 重发 GEN_REQUEST（第 {kicks} 次；runner 一上线就开工）",
                        "--", str(marker.relative_to(ROOT)))
                    pushed = git("push", "origin", f"HEAD:{BRANCH}").returncode == 0
                    print(f"[{stamp}] KICK {kicks} 重发触发标记 {'成功' if pushed else '失败（推送被拒）'}", flush=True)
            if phase is None:
                diag = show(DIAG)
                if diag:
                    print(f"[{stamp}] 工作流报错，诊断日志尾部：\n{diag[-1500:]}", flush=True)
                    return 1
            if len(done) == len(required) or phase in ("selected_sources_ready", "first_cut_ready"):
                try:
                    pull()
                except RuntimeError as exc:
                    print(f"PULL_FAIL {exc}", flush=True)
                    return 1
                print(f"[{stamp}] 生成齐了，跑逐格扫描…", flush=True)
                scan = subprocess.run([sys.executable, str(HERE / "scan_qa.py"),
                                       "--out", str(ROOT / "work/monalisa/qa-scan.md"),
                                       "--json", str(ROOT / "work/monalisa/qa-scan.json")],
                                      cwd=ROOT, capture_output=True, text=True)
                print(scan.stdout[-4000:] or scan.stderr[-1500:], flush=True)
                bad = [r for r in json.loads((ROOT / "work/monalisa/qa-scan.json").read_text())
                       if r.get("verdict") != "pass"] if (ROOT / "work/monalisa/qa-scan.json").exists() else []
                summary = {"phase": phase, "done": done, "required": required,
                           "scan_flags": [r["id"] for r in bad], "head": head}
                (ROOT / "work/monalisa/gen-done.flag").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
                print("GEN_DONE " + json.dumps(summary, ensure_ascii=False), flush=True)
                return 0
            if phase in ("generation_incomplete", "pipeline_failed"):
                diag = show(DIAG) or ""
                print(f"[{stamp}] 生成未完成（phase={phase}）：\n{diag[-1500:]}", flush=True)
                return 1
        if args.once:
            return 0
        if time.monotonic() - started > args.budget:
            print("WATCH_BUDGET_REACHED 还没跑完，继续等就再启动一次本脚本", flush=True)
            return 2
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
