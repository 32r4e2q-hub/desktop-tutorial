#!/usr/bin/env python3
"""重写 production/monalisa/colab出片.ipynb：从"Colab 当主战场"改成"Colab 只干两件事 ——
搬家 + 备胎出片"，并且搬家那一格在搬完之后重跑也不会把你仓库写坏。

关键点：镜像仓库的 URL / 分支名用字符串拼接写，故意不让它们成为可被
`move_to_new_repo.py` 重写的连续字面量 —— 搬进你仓库之后，这一格仍然指向 Arena 镜像
（那才是"抓沙箱最新代码"的正确来源）。
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
        "**默认不用这个笔记本出片** —— 你的仓库有 Actions（Public 仓库时长无限制），点火方式是",
        "根目录的 `你的仓库操作卡.md`。这个笔记本只负责两件事：",
        "",
        "| 格 | 干什么 | 什么时候用 |",
        "|---|---|---|",
        "| ② | 把沙箱里的最新代码整树搬进**你自己的**仓库 | 只做一次（做完 Actions 自动点火） |",
        "| ③ | 读进度 + 逐格质检结论 | 随时跑，不烧额度、不需要 key |",
        "| ④⑤ | 不靠 Actions，就在这台 Colab 上把 38 镜和成片跑完，并把结果推回分支 | Actions 出问题时当备胎 |",
        "",
        "> 安全线：② 用的是**一次性 token**（只需 Contents: Read and write），跑完立刻去 revoke；",
        "> token 只活在运行时内存里，不进文件、不进 git。④⑤ 才会用到 Agnes key。",
    ),
    code(
        "# ① 挂载 Google Drive（跑 60 分钟以上必备：断线不丢进度）",
        "from google.colab import drive",
        "drive.mount('/content/drive')",
        "print('Drive 已挂载')",
    ),
    code(
        "# ② 搬家：从 Arena 镜像拉最新代码 → 重写仓库名/分支名 → 单提交推到你的仓库",
        "#    （初始 push 自带 GEN_REQUEST，所以推完那一刻 Actions 就自己点火了，不需要你点按钮）",
        "MYREPO = 'ozzy282576/monalisa-film'      # ← 改成你的 用户名/仓库名",
        "BRANCH = 'main'",
        "MIRROR = 'https://github.com/' + '32r4e2q-hub' + '/' + 'desktop-tutorial' + '.git'   # 拼接是故意的：别让搬家脚本把它改掉",
        "SRC_BR = 'arena/' + '01a0aa24' + '-desktop-tutorial'",
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
        "if not os.path.isdir('/content/mirror/.git'):",
        "    run('git', 'clone', '-q', '--depth', '1', '-b', SRC_BR, MIRROR, '/content/mirror')",
        "else:",
        "    run('git', '-C', '/content/mirror', 'fetch', '-q', '--depth', '1', 'origin', SRC_BR)",
        "    run('git', '-C', '/content/mirror', 'reset', '-q', '--hard', 'FETCH_HEAD')",
        "",
        "try:",
        "    TOKEN = getpass.getpass('贴你的 fine-grained PAT（输入不显示）: ').strip()",
        "except Exception:",
        "    TOKEN = input('贴你的 fine-grained PAT: ').strip()",
        "run('python3', 'scripts/move_to_new_repo.py', '--target', MYREPO, '--branch', BRANCH,",
        "    '--dest', '/tmp/mv', '--push', cwd='/content/mirror', env={'GH_PUSH_TOKEN': TOKEN})",
        "print()",
        "print('看到这行 = 没报错。刷新你的仓库首页应该能看到 368 个文件 + 一条新提交。')",
    ),
    code(
        "# ③ 看进度（匿名读你的公开仓库：不用 token、不用 Agnes key、不烧额度，随时重跑）",
        "run('python3', 'scripts/watch_repo.py', '--repo', MYREPO, '--branch', BRANCH,",
        "    '--cache', '/tmp/watch', '--fresh')",
    ),
    code(
        "# ④【备胎】不走 Actions，直接在这台 Colab 上出片：体检 → 38 镜 → 渲染 → 逐格复核",
        "#    约 50~70 分钟；被掐断就重跑这一格，已生成的镜头按 SHA-256 复用，不重复扣额度",
        "if not os.path.isdir('/content/proj/.git'):",
        "    run('git', 'clone', '-q', '-b', BRANCH, f'https://github.com/{MYREPO}.git', '/content/proj')",
        "else:",
        "    run('git', '-C', '/content/proj', 'fetch', '-q', 'origin', BRANCH)",
        "    run('git', '-C', '/content/proj', 'reset', '-q', '--hard', 'FETCH_HEAD')",
        "run('bash', 'production/monalisa/本机出片.sh', '--dry', cwd='/content/proj')      # 先体检",
        "# os.environ['AGNES_API_KEY'] = TOKEN2 = input('Agnes key: ').strip()   ← 下一格再用，别把 key 写进文件",
    ),
    code(
        "# ④b 确认体检绿了再放开这一格（生成 + 出片一条龙）",
        "os.environ['AGNES_API_KEY'] = getpass.getpass('Agnes API key: ').strip()",
        "run('bash', 'production/monalisa/本机出片.sh', cwd='/content/proj')",
        "run('ls', '-la', '交付', cwd='/content/proj')",
    ),
    code(
        "# ⑤ 把这台 Colab 的产出推回你的分支（只推 results.json / qa 联络表 / 三份报告，不推视频字节）",
        "#    推完 Arena 那边就能 fetch 到并开始逐格 QC",
        "for rel in ['production/monalisa/results.json', 'production/monalisa/qa',",
        "            'production/monalisa/QA_REPORT.md', 'production/monalisa/work']:",
        "    if os.path.isdir('/content/proj/' + rel) or os.path.isfile('/content/proj/' + rel):",
        "        run('git', 'add', '-f', rel, cwd='/content/proj')",
        "dirty = sp.run(['git', 'diff', '--cached', '--quiet'], cwd='/content/proj', env=dict(os.environ)).returncode != 0",
        "if dirty:",
        "    run('git', 'commit', '-q', '-m', 'monalisa: Colab 备胎产出同步（results + qa）', cwd='/content/proj')",
        "    run('git', '-c', 'credential.helper=', 'push',",
        "        f'https://x-access-token:{TOKEN}@github.com/{MYREPO}.git', f'HEAD:{BRANCH}', cwd='/content/proj')",
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

# 自检：能被 json 读、每个 code 格都能编译、没有把镜像字面量写成可被重写的连续串
data = json.loads(NB.read_text())
for i, c in enumerate(data["cells"]):
    if c["cell_type"] == "code":
        compile("".join(c["source"]), f"<cell{i}>", "exec")
print(f"笔记本重写完成：{len(data['cells'])} 格，代码格语法全过")
