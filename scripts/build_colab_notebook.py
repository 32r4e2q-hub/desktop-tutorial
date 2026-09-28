#!/usr/bin/env python3
"""重写 production/monalisa/colab出片.ipynb。

为什么是生成器而不是直接改 ipynb：笔记本是 JSON，手改容易把 source 数组写坏；生成器自带
自检（json 能读 + 每个代码格 compile 得过），改完一句 `python3 scripts/build_colab_notebook.py` 就行。

架构（2026-09-28 定稿）：沙箱这个身份对**任何** GitHub 仓库都只有 Arena 机器人的读写边界，
镜像仓库 `32r4e2q-hub/desktop-tutorial` 是 Arena 私有 org（匿名 HTTP 404），所以
**Colab 不能 clone 镜像**。改成：沙箱把已经改写好仓库名/分支名的瘦身包打成
`monalisa-film.tar.gz`（9 MB）→ 你上传到 Colab → 这一格把它 init + push 到你自己的仓库
→ 初始 push 自带 GEN_REQUEST，Actions 自己点火。
"""
import json
from pathlib import Path

NB = Path("/home/user/desktop-tutorial/production/monalisa/colab出片.ipynb")


def code(*lines: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": [ln + "\n" for ln in lines][:-1] + [lines[-1]]}


def md(*lines: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": [ln + "\n" for ln in lines][:-1] + [lines[-1]]}


cells = [
    md(
        "# 蒙娜丽莎：行李箱里的 779 号 · Colab 工具箱",
        "",
        "前提：你先在 Arena 沙箱里让我打好 **`monalisa-film.tar.gz`**（已经改写好你的仓库名和 `main` 分支，",
        "86 个文件 / 45 镜计划 / 3 份工作流 / 6 段配音），然后把它拖进左边 Files 面板的 `/content` 根目录。",
        "",
        "| 格 | 干什么 | 什么时候用 |",
        "|---|---|---|",
        "| ② | 把上传的瘦身包推到**你自己的仓库** | 只做一次（推完 Actions 自动点火） |",
        "| ③ | 读进度 + 逐格质检结论（匿名读公开仓库） | 随时跑，不烧额度、不需要 key |",
        "| ④⑤ | 不靠 Actions，就在这台 Colab 上把 38 镜和成片跑完，并把结果推回分支 | Actions 出问题时当备胎 |",
        "",
        "> 为什么不让 Colab 直接 clone Arena 镜像仓库：`32r4e2q-hub` 是 Arena 的私有 org，匿名",
        "> `git clone` 会 128 失败（`repository not found`）——沙箱里能读是因为出口代理自动带上了",
        "> Arena 机器人的凭据，那套凭据在 Colab 不存在。所以代码靠**上传文件**进来，不靠 clone。",
        "",
        "> 安全线：② 用的 GitHub token 只需要 `Contents: Read and write` 且设成 **1 天过期**，",
        "> 跑完立刻 revoke；token 只活在运行时内存里，不写文件、不进 git。④⑤ 才用到 Agnes key。",
    ),
    code(
        "# ① 挂载 Google Drive（跑 60 分钟以上必备：断线不丢进度）",
        "from google.colab import drive",
        "drive.mount('/content/drive')",
        "print('Drive 已挂载')",
    ),
    code(
        "# ② 把瘦身包推到你自己的仓库（推完那一刻 Actions 就自己点火，不用你点按钮）",
        "MYREPO = 'ozzy282576/monalisa-film'      # ← 改成你的 用户名/仓库名",
        "BRANCH = 'main'",
        "BUNDLE = '/content/monalisa-film.tar.gz'  # Files 面板上传后就是这个路径",
        "BUNDLE_URL = ''                           # 或者填 Arena 沙箱给的下载链接，填了就自动 wget，不用手动上传",
        "FORCE  = False                            # 只有你确定要覆盖仓库历史时才改 True",
        "",
        "import os, subprocess as sp, getpass",
        "os.environ['GIT_TERMINAL_PROMPT'] = '0'",
        "",
        "def run(*a, cwd=None, env=None):",
        "    e = dict(os.environ); e.update(env or {})",
        "    r = sp.run([str(x) for x in a], cwd=str(cwd) if cwd else None, env=e)",
        "    if r.returncode:",
        "        raise SystemExit(f'退出码 {r.returncode}：{a[0]} {\" \".join(map(str, a[1:]))}')",
        "    return r",
        "",
        "if BUNDLE_URL:",
        "    run('wget', '-q', '-O', BUNDLE, BUNDLE_URL)",
        "    print('下载完成：', os.path.getsize(BUNDLE), '字节')",
        "assert os.path.isfile(BUNDLE), '要么填 BUNDLE_URL，要么把 monalisa-film.tar.gz 拖进左边 Files 面板'",
        "PROJ = '/content/monalisa-film',",
        "run('rm', '-rf', PROJ)",
        "run('tar', 'xzf', BUNDLE, '-C', '/content')",
        "run('git', 'init', '-q', '-b', BRANCH, PROJ)",
        "run('git', 'config', 'user.name',  'monalisa-move', cwd=PROJ)",
        "run('git', 'config', 'user.email', 'arena@local',   cwd=PROJ)",
        "run('git', 'add', '-A', cwd=PROJ)",
        "run('git', 'commit', '-q', '-m', '蒙娜丽莎：行李箱里的779号 —— 86 文件 / 45 镜计划 / 3 份工作流', cwd=PROJ)",
        "",
        "try:",
        "    TOKEN = getpass.getpass('贴你的 fine-grained PAT（输入不显示）: ').strip()",
        "except Exception:",
        "    TOKEN = input('贴你的 fine-grained PAT: ').strip()",
        "URL = f'https://x-access-token:{TOKEN}@github.com/{MYREPO}.git'",
        "",
        "have = sp.run(['git', 'ls-remote', URL, f'refs/heads/{BRANCH}'], env=dict(os.environ),",
        "              capture_output=True, text=True).stdout.strip()",
        "if have and not FORCE:",
        "    print('!! 远端已有提交（', have.split()[0][:9], '）—— 大概率是 Actions 回推的素材记录，不覆盖。')",
        "    print('   确实要从这个包重来一遍，就把上面 FORCE 改成 True 再跑。')",
        "else:",
        "    run('git', '-c', 'credential.helper=', 'push', URL, f'HEAD:{BRANCH}', cwd=PROJ)",
        "    print('推完了。刷新仓库首页：应该看到 87 个文件 + main 分支；')",
        "    print('去 Actions 页应该已经有一条「Agnes生成」在跑（初始 push 自带 GEN_REQUEST 触发的）。')",
    ),
    code(
        "# ③ 看进度（匿名读你的公开仓库：不用 token、不用 Agnes key、不烧额度，随时重跑）",
        "run('python3', 'scripts/watch_repo.py', '--repo', MYREPO, '--branch', BRANCH,",
        "    '--cache', '/tmp/watch', '--fresh', cwd=PROJ)",
    ),
    code(
        "# ④【备胎】不走 Actions，直接在这台 Colab 上出片：先体检（不联网、不烧额度）",
        "run('bash', 'production/monalisa/本机出片.sh', '--dry', cwd=PROJ)",
    ),
    code(
        "# ④b 体检绿了再放开这一格（生成 + 出片一条龙；被掐断就重跑，已生成的按 SHA-256 复用）",
        "os.environ['AGNES_API_KEY'] = getpass.getpass('Agnes API key: ').strip()",
        "run('bash', 'production/monalisa/本机出片.sh', cwd=PROJ)",
        "run('ls', '-la', '交付', cwd=PROJ)",
    ),
    code(
        "# ⑤ 把这台 Colab 的产出推回你的分支（只推 results.json / qa 联络表 / 报告，不推视频字节）",
        "#    推完 Arena 那边就能 fetch 到并开始逐格 QC",
        "for rel in ['production/monalisa/results.json', 'production/monalisa/qa',",
        "            'production/monalisa/QA_REPORT.md', 'production/monalisa/work']:",
        "    if os.path.isdir(PROJ + '/' + rel) or os.path.isfile(PROJ + '/' + rel):",
        "        run('git', 'add', '-f', rel, cwd=PROJ)",
        "dirty = sp.run(['git', 'diff', '--cached', '--quiet'], cwd=PROJ, env=dict(os.environ)).returncode != 0",
        "if dirty:",
        "    run('git', 'commit', '-q', '-m', 'monalisa: Colab 备胎产出同步（results + qa）', cwd=PROJ)",
        "    run('git', '-c', 'credential.helper=', 'push', URL, f'HEAD:{BRANCH}', cwd=PROJ)",
        "    print('已推回', BRANCH)",
        "else:",
        "    print('没有新东西要推（已经同步过了）')",
    ),
    code(
        "# ⑥（可选）另开一个标签页挂着这一格，防空闲掐断；主任务跑完就关掉",
        "from google.colab import output",
        "output.eval_js('new Promise(resolve => setTimeout(() => resolve(0), 3600000))')",
        "print('这一格挂着 = 运行时不会被空闲掐断')",
    ),
]

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
        "language_info": {"name": "python"},
        "colab": {"provenance": [], "toc_visible": True},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}
NB.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n")

data = json.loads(NB.read_text())
for i, c in enumerate(data["cells"]):
    if c["cell_type"] == "code":
        compile("".join(c["source"]), f"<cell{i}>", "exec")
txt = "".join("".join(c["source"]) for c in data["cells"])
assert "32r4e2q-hub/desktop-tutorial" not in txt, "笔记本里出现了完整镜像 slug，搬家脚本会把它改掉"
assert "git clone -q --depth 1" not in txt, "②里不该再有 clone 镜像那一行"
print(f"笔记本重写完成：{len(data['cells'])} 格，代码格语法全过；不再依赖 clone 镜像仓库")
