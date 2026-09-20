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

    def test_setup_blocks_musl_and_explains_why(self):
        """Alpine / musl 要直接拦下，别让它装到一半才撞墙。

        `wsl` 默认丢出来的可能是 Alpine：GitHub 官方 runner 只发 glibc 构建，
        出片脚本还写死了 sudo apt-get install fonts-noto-cjk，musl 系根本跑不通。
        """
        setup = SETUP.read_text(encoding="utf-8")
        self.assertIn("musl", setup, "必须探测 musl libc")
        self.assertIn("glibc", setup, "拦下的时候要说明原因（runner 只有 glibc 构建）")
        # 拦截动作里要给出换回 Ubuntu / Debian 系的退路，而不是一句干巴巴的拒绝
        self.assertRegex(setup, r"Ubuntu\s*/\s*Debian", "拦下 musl 时要给出换发行版的退路")

    def test_setup_installs_cjk_fonts_independently_of_other_deps(self):
        """中文字体要单独查、单独装，不能跟着 '依赖都在就整段跳过' 一起被跳过。

        2026-09-20 实测：ffmpeg 等都在时，脚本整段跳过 apt，中文字体就从没被装过，
        出片才在 render 那步报 'refusing to render missing glyphs'。
        """
        setup = SETUP.read_text(encoding="utf-8")
        # 第二次检查必须脱离第一次装依赖的 apt 分支（ffmpeg / python 都在的时候也要查 font）
        idx = setup.index("fc-list | grep -qi")
        # 字体装的是 fonts-noto-cjk，而且是独立的一条安装
        self.assertIn("fonts-noto-cjk", setup[idx:],
                      "字体检查后面没有独立的一条 fonts-noto-cjk 安装")
        # 有 apt-get 时才自动补装；没有（非 apt 发行版）得警告，不能让它默默过去
        self.assertTrue(
            ("apt-get install" in setup[idx:] and "refusing to render missing glyphs" in setup),
            "字体缺失时要么 apt-get 补装，要么给出 refusing-to-render 的警告",
        )

    def test_setup_removes_a_stale_registration_before_configuring(self):
        """目录里已有 .runner 时，注册前要先用 config.sh remove 摘掉旧注册。

        2026-09-20 实测：旧注册挡路时 config.sh 报 'already configured'，
        --replace 在部分版本上不顶用；先 remove 再注册才真的幂等。
        """
        setup = SETUP.read_text(encoding="utf-8")
        self.assertIn("config.sh remove", setup, "注册前要先用 config.sh remove 摘掉旧注册")
        remove_idx = setup.index("config.sh remove")
        # remove 拿到的也是同一个现场 token
        self.assertIn("--token", setup[remove_idx:remove_idx + 120],
                      "remove 也要带现场取到的 token")
        remove_line = next(ln for ln in setup.splitlines() if "config.sh remove" in ln)
        self.assertIn('"$TOKEN"', remove_line, "remove 要用同一个 $TOKEN，别拼第二把")
        # remove 要发生在真正的注册（--url）之前，顺序不能反
        self.assertLess(remove_idx, setup.index("./config.sh --url"),
                        "先摘旧注册、再注册，顺序反了等于白摘")

    def test_setup_checks_online_status_without_gh_api_arg(self):
        """gh api 没有 --arg 参数：写 `--jq --arg n "$RUNNER_NAME"` 每次查询都失败、白等。

        名字必须拼进 --jq 表达式（select(.name==…)，双引号包住），而不是当参数传。
        """
        setup = SETUP.read_text(encoding="utf-8")
        self.assertIn("--arg", setup, "注释里要留下这个坑，别让后人再写回去")
        for ln in setup.splitlines():
            if ln.lstrip().startswith("#"):
                continue
            if "gh api" in ln and "--arg" in ln:
                self.fail(f"gh api 调用里不能带 --arg：{ln!r}")
        # 名字拼进 --jq：先 assign 一个带 select(.name==…) 的表达式，再 --jq 引用它
        self.assertIn("select(.name==", setup, "名字要拼进 --jq 的 select(.name==…)")
        self.assertIn('--jq "$RJQ"', setup, "查询要引用拼好的 jq 表达式")

    def test_setup_sets_pypi_mirror_even_without_a_pip3_command(self):
        """--pypi-mirror 在只有 python3 -m pip 的机器上会静默失败（pip3 命令不存在），
        必须退回 python3 -m pip 再试，而不是一声不吭地装成成功。"""
        setup = SETUP.read_text(encoding="utf-8")
        self.assertIn("python3 -m pip config", setup,
                      "pip3 不存在时要退回 python3 -m pip config 设镜像")
        self.assertIn("PYPI_MIRROR", setup)

    def test_setup_keeps_the_background_runner_alive_via_setsid_disown(self):
        """后台 runner 必须 setsid + disown 活着，且判据不能是假阳性。

        2026-09-20 实测：`a || b &` 的 & 作用于整个 || 列表，且缺 setsid 时脚本一退出
        进程就没了；而 pgrep -f 'Runner.Listener' 会命中后台子进程命令行的同名字样，
        属于假阳性（runner 其实死了还在说"已在后台跑"）。
        """
        setup = SETUP.read_text(encoding="utf-8")
        self.assertIn("setsid ./run.sh", setup, "后台启动必须走 setsid")
        self.assertIn("disown", setup, "setsid 起的进程还要 disown，才不会被 shell 拖走")
        # 判据必须改盯 run.sh，不能再用 Runner.Listener 那个假阳性写法
        haystack = setup[setup.index("setsid ./run.sh"):]
        self.assertNotIn("pgrep -f \"Runner.Listener\"", haystack,
                         "后台存活的判据不能再用 Runner.Listener（假阳性）")
        self.assertIn("run.sh", haystack, "存活判据至少要看 run.sh 这个进程名")


if __name__ == "__main__":
    unittest.main()
