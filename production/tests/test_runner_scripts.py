"""本地 runner 三件套的自检（离线，不联网、不需要 ffmpeg）。

为什么要有这份测试：``runner/`` 里的三个脚本是**在仓库主的私人机器上以 sudo 跑**的，
装错一步（漏了中文字体、把 token 打进日志、在公开仓库上注册）代价都比 CI 红一次大。
它们不会被任何工作流调用，所以 ``test_workflows.py`` 那套"工作流引用的脚本"检查
覆盖不到——这里单独守四条：

1. 三个脚本都得是语法正确的 bash（``bash -n``）；
2. 默认仓库、开关变量名必须和工作流里的对得上（``RUNNER_LABEL`` / ``WHISPER_CACHE_DIR``）；
3. ``setup-runner.sh`` 必须先查仓库可见性、**公开就拒绝注册**，并且提供的退路是
   ``--no-register``（公开仓库上挂自托管 runner = 任何 fork PR 都能在那台机器上执行代码）；
4. token 只现场取、不落盘、不进输出（脚本里不能出现会把它打印出来的写法）。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNNER_DIR = ROOT / "runner"
SETUP = RUNNER_DIR / "setup-runner.sh"
SELFCHECK = RUNNER_DIR / "selfcheck.sh"
UNINSTALL = RUNNER_DIR / "uninstall-runner.sh"
README = RUNNER_DIR / "README.md"
MANUAL = ROOT / "转私有与自托管Runner手册.md"

# 与 .github/workflows/*.yml 里 runs-on 用的开关是同一个
EXPECTED_REPO = "32r4e2q-hub/desktop-tutorial"
ECHO_TOKEN = re.compile(r"echo[^#\n]*\$\{?TOKEN\}?", re.IGNORECASE)


class RunnerScriptTests(unittest.TestCase):
    def test_all_three_scripts_exist_and_are_valid_shell(self):
        for script in (SETUP, SELFCHECK, UNINSTALL):
            with self.subTest(script=script.name):
                self.assertTrue(script.exists(), f"缺 {script}")
                proc = subprocess.run(["bash", "-n", str(script)],
                                      capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0,
                                 f"{script.name} 语法错误：{proc.stderr}")

    def test_readme_exists_and_points_at_the_manual(self):
        self.assertTrue(README.exists(), "runner/README.md 是给仓库主看的最短路径，不能没有")
        text = README.read_text(encoding="utf-8")
        self.assertIn("转私有与自托管Runner手册.md", text,
                      "runner/README.md 要指回完整手册，别让人只看三分钟版就去动仓库设置")
        self.assertTrue(MANUAL.exists())

    def test_scripts_default_to_this_repository(self):
        for script in (SETUP, SELFCHECK, UNINSTALL):
            with self.subTest(script=script.name):
                self.assertIn(EXPECTED_REPO, script.read_text(encoding="utf-8"),
                              f"{script.name} 的默认仓库不是本仓库")

    def test_switch_names_match_the_workflows(self):
        """脚本设的变量名，必须就是工作流读的那几个。"""
        setup = SETUP.read_text(encoding="utf-8")
        self.assertIn("RUNNER_LABEL", setup)
        self.assertIn("WHISPER_CACHE_DIR", setup)
        # 走镜像时必须一起关掉 Xet，否则 HF 会绕过 HF_ENDPOINT 直连 cas-server 被 401
        self.assertIn("HF_HUB_DISABLE_XET", setup)

    def test_setup_refuses_to_register_on_a_public_repository(self):
        """公开仓库上挂自托管 runner，等于把机器交给任何 fork PR。"""
        setup = SETUP.read_text(encoding="utf-8")
        self.assertIn(".private", setup, "注册前必须先查仓库可见性")
        self.assertIn("--no-register", setup, "仓库还是公开时，要给一条只装软件不注册的退路")
        index = setup.index("--no-register")
        self.assertLess(index, setup.index("./config.sh"),
                        "拒绝注册的分支要出现在真正调用 config.sh 之前")

    def test_token_is_never_printed_or_written_to_disk(self):
        """token 只现场取、用完 unset；脚本里不能有 echo $TOKEN 之类的写法。"""
        for script in (SETUP, UNINSTALL):
            with self.subTest(script=script.name):
                text = script.read_text(encoding="utf-8")
                self.assertIsNone(ECHO_TOKEN.search(text),
                                  f"{script.name} 会把 token 打印出来")
                self.assertIn("unset TOKEN", text,
                              f"{script.name} 用完 token 要 unset")

    def test_selfcheck_fails_loudly_when_a_hard_requirement_is_missing(self):
        """自检遇到必须修的问题（缺 ffmpeg / 没字体）要返回非 0，别让人以为能出片。"""
        text = SELFCHECK.read_text(encoding="utf-8")
        self.assertIn("exit 1", text)
        self.assertIn("fonts-noto-cjk", text, "中文字体缺失要给出那条 apt 命令")
        self.assertIn("repos/$REPO", text, "自检要顺手确认仓库仍是私有")


if __name__ == "__main__":
    unittest.main()
