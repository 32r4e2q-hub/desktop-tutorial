"""出片工作流的自检：`.github/workflows/` 里的东西必须真的是工作流。

守四条，全部离线（不需要网络、ffmpeg、也不需要 pyyaml 才生效）：

1. ``production/verbatim-check.workflow.yml`` 与 ``.github/workflows/verbatim-check.yml``
   **逐字节相同**——手动复制那一步贴错内容立刻失败；
2. 每个工作流形状正确（``name`` / ``on`` / ``jobs``），且**非注释行**里不出现
   Markdown 正文特征；装了 ``pyyaml`` 时再做完整解析与结构校验；
3. 在**当前分支**上跑的工作流（没有 pin ``ref:`` 的），它引用的脚本必须在本仓库
   真实存在且能通过 ``bash -n``；
4. runs-on 必须走仓库变量开关（``vars.RUNNER_LABEL``），不许写死 GitHub-hosted runner。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
CI_TEMPLATE = ROOT / "production" / "ci-tests.workflow.yml"
CI_INSTALLED = WORKFLOWS_DIR / "ci-tests.yml"
VERBATIM_TEMPLATE = ROOT / "production" / "verbatim-check.workflow.yml"
VERBATIM_INSTALLED = WORKFLOWS_DIR / "verbatim-check.yml"
SHANGHAI_WORKFLOW = WORKFLOWS_DIR / "shanghai-freezer-case.yml"

try:  # pyyaml 不在最小依赖里：装了就做完整解析，没装就退回形状检查
    import yaml
except ImportError:  # pragma: no cover - 取决于环境
    yaml = None

# 顶层键从行首开始，值可以为空（on: / jobs:）也可以跟在冒号后（name: 名称）
TOP_LEVEL = re.compile(r"^(?P<key>[A-Za-z_][\w-]*):(?:[ \t].*)?$", re.MULTILINE)
CHECKOUT_REF = re.compile(r"^\s+ref:\s*(\S+)", re.MULTILINE)
RUNS_ON = re.compile(r"^\s*runs-on:\s*(?P<value>.+?)\s*$", re.MULTILINE)
# runs-on 统一走这一个仓库变量开关：默认落到 GitHub-hosted（ubuntu-latest），
# 若仓库改设为自托管 runner，只需在仓库 Settings → Variables 里改 RUNNER_LABEL，无需改 YAML。
RUNNER_SWITCH = "vars.RUNNER_LABEL"


def workflow_files() -> list[Path]:
    return sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))


def top_level_keys(text: str) -> set[str]:
    return set(TOP_LEVEL.findall(text))


def non_comment_lines(text: str) -> str:
    """去掉整行注释与行尾注释：模板里的 Markdown 记号都写在注释里，不算正文。"""
    kept = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        kept.append(re.sub(r"[ \t]+#.*$", "", line))
    return "\n".join(kept)


class WorkflowIntegrityTests(unittest.TestCase):
    def test_verbatim_check_template_runs_the_real_script(self):
        """逐字听检模板必须真的调用 production/verbatim_check.py，并把报告落回分支。"""
        text = VERBATIM_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("production/verbatim_check.py", text,
                      "听检模板没有调用 production/verbatim_check.py")
        self.assertTrue((ROOT / "production" / "verbatim_check.py").exists())
        self.assertIn("production/$PROJECT/delivery/verbatim-check.json", text,
                      "报告没有 commit 回分支，本地就拿不到听检结果")
        self.assertIn("continue-on-error: true", text,
                      "转写不达标的运行也要先把报告 publish 出来")
        self.assertIn("WHISPER_CACHE_DIR", text,
                      "听检工作流没有透传 WHISPER_CACHE_DIR，自托管 runner 上会每次重下模型")
        self.assertIn("HF_HUB_DISABLE_XET", text,
                      "听检工作流没有关掉 HF 的 Xet 存储：配镜像时会 401，模型下不下来")

    def test_verbatim_workflow_matches_template_when_installed(self):
        if not VERBATIM_INSTALLED.exists():
            self.skipTest("未启用：把 production/verbatim-check.workflow.yml 复制成 "
                          ".github/workflows/verbatim-check.yml 即可")
        self.assertEqual(
            VERBATIM_TEMPLATE.read_bytes(), VERBATIM_INSTALLED.read_bytes(),
            f"{VERBATIM_INSTALLED.relative_to(ROOT)} 与模板不一致：请重新执行 "
            "cp production/verbatim-check.workflow.yml .github/workflows/verbatim-check.yml",
        )

    def test_ci_workflow_matches_template_when_installed(self):
        """CI 自检模板同样要手动复制一次；放进去了就必须与模板逐字节一致。"""
        if not CI_INSTALLED.exists():
            self.skipTest("未启用：把 production/ci-tests.workflow.yml 复制成 "
                          ".github/workflows/ci-tests.yml 即可（代理写不了那个目录）")
        self.assertEqual(
            CI_TEMPLATE.read_bytes(), CI_INSTALLED.read_bytes(),
            f"{CI_INSTALLED.relative_to(ROOT)} 与模板不一致：请重新执行 "
            "cp production/ci-tests.workflow.yml .github/workflows/ci-tests.yml",
        )

    def test_ci_template_actually_runs_the_offline_gate(self):
        """自检工作流不能被人改成"跑点别的"——它必须跑 production/tests。"""
        text = CI_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("production/tests", text,
                      "CI 模板没有跑 production/tests，改回去")
        self.assertIn("production/requirements.txt", text,
                      "CI 模板没有用 production/requirements.txt 装依赖")
        self.assertTrue((ROOT / "production" / "requirements.txt").exists(),
                        "CI 模板引用的 requirements.txt 不存在")
        if yaml is not None:
            jobs = yaml.safe_load(text)["jobs"]
            self.assertEqual(len(jobs), 1, "CI 只该有一个 job，别把出片混进来")
            steps = next(iter(jobs.values()))["steps"]
            self.assertTrue(any("pytest" in str(step) for step in steps),
                            "CI 里没有任何一步调用 pytest")

    def test_every_workflow_has_required_top_level_keys(self):
        files = workflow_files()
        self.assertTrue(files, "仓库里一个工作流都没有？")
        for path in files:
            with self.subTest(workflow=path.name):
                keys = top_level_keys(path.read_text(encoding="utf-8"))
                for required in ("name", "jobs"):
                    self.assertIn(required, keys, f"{path.name} 缺顶层 {required}:")
                self.assertTrue(
                    {"on", "true"} & keys,
                    f"{path.name} 缺触发器 on:（pyyaml 把 on 解析成布尔 True，故两者都认）",
                )

    def test_no_workflow_is_prose(self):
        for path in workflow_files():
            with self.subTest(workflow=path.name):
                text = path.read_text(encoding="utf-8")
                first = next((ln for ln in text.splitlines() if ln.strip()), "")
                self.assertRegex(first, r"^(name|on|run-name|#)",
                                 f"{path.name} 的首个非空行是 {first!r}，看起来不是工作流")
                body = non_comment_lines(text)
                # release-upload.yml 用 production/**/RELEASE_UPLOAD_REQUEST 这个 glob，不是 Markdown 粗体
                body = body.replace("production/**/RELEASE_UPLOAD_REQUEST", "production/RELEASE_UPLOAD_REQUEST")
                self.assertNotRegex(body, r"(?m)^#{1,6}\s", "正文里有 Markdown 标题，不是 YAML 工作流")
                self.assertNotIn("**", body, "正文里有 Markdown 粗体，不是 YAML 工作流")

    @unittest.skipIf(yaml is None, "未安装 pyyaml，跳过完整解析")
    def test_every_workflow_parses_and_declares_a_runnable_job(self):
        files = workflow_files() + sorted(ROOT.glob("production/**/*.workflow.yml")) + \
            sorted((ROOT / "production" / "templates").glob("*.yml")) + \
            sorted((ROOT / "production" / "templates").glob("*.workflow.yml"))
        for path in files:
            with self.subTest(workflow=path.name):
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertIsInstance(data, dict, f"{path.name} 顶层不是映射")
                trigger = data.get("on", data.get(True))
                self.assertIsNotNone(trigger, f"{path.name} 没有触发器")
                jobs = data["jobs"]
                self.assertIsInstance(jobs, dict, f"{path.name} 的 jobs 不是映射")
                for job_name, job in jobs.items():
                    if "uses" in job:
                        self.assertIsInstance(job["uses"], str)
                        self.assertTrue(job["uses"].strip())
                        self.assertNotIn("runs-on", job)
                        self.assertNotIn("steps", job)
                        if job["uses"].startswith("./"):
                            target = ROOT / job["uses"][2:]
                            self.assertTrue(target.is_file(), f"{path.name}:{job_name} 调用的工作流不存在")
                            called = yaml.safe_load(target.read_text(encoding="utf-8"))
                            called_on = called.get("on", called.get(True))
                            self.assertIn("workflow_call", called_on, f"{target.name} 缺 workflow_call")
                    else:
                        self.assertIn("runs-on", job, f"{path.name}:{job_name} 缺 runs-on")
                        self.assertIn("steps", job, f"{path.name}:{job_name} 缺 steps")

    def test_no_workflow_hardcodes_a_github_hosted_runner(self):
        """runs-on 必须走仓库变量开关，不能写死 ubuntu-latest。"""
        files = workflow_files() + sorted(ROOT.glob("production/**/*.workflow.yml")) + \
            sorted((ROOT / "production" / "templates").glob("*.yml"))
        self.assertTrue(files, "仓库里一个工作流都没有？")
        for path in files:
            text = path.read_text(encoding="utf-8")
            values = RUNS_ON.findall(text)
            with self.subTest(workflow=path.name):
                self.assertTrue(values, f"{path.name} 里一个 runs-on 都没有")
                for value in values:
                    self.assertIn(
                        RUNNER_SWITCH, value,
                        f"{path.name} 的 runs-on 写死了 {value!r}：转私有后这里会继续烧 "
                        "GitHub-hosted 额度。改成 "
                        "${{ vars.RUNNER_LABEL || 'ubuntu-latest' }}",
                    )

    def test_no_sigpipe_prone_git_status_head_in_workflows(self):
        """`git status --short | head -N` 必须带 `|| true`，守 SIGPIPE(141) 假成功。"""
        candidates = list(WORKFLOWS_DIR.glob("*.yml")) + list(WORKFLOWS_DIR.glob("*.yaml"))
        candidates += sorted((ROOT / "production" / "templates").glob("*.yml"))
        candidates += sorted((ROOT / "production" / "templates").glob("*.workflow.yml"))
        candidates += sorted(ROOT.glob("production/*/workflows/*.yml"))
        checked = 0
        for path in candidates:
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped.startswith("git status") or "| head" not in stripped:
                    continue
                if stripped.startswith("#"):
                    continue
                checked += 1
                with self.subTest(workflow=str(path.relative_to(ROOT)), line=stripped):
                    self.assertIn("|| true", stripped,
                                  "git status | head 在 pipefail 下会 SIGPIPE(141) 假成功，必须带 || true")
        # 注：历史上出事的那几份工作流已经删掉；现在仓库里可能一条都没有——
        # 这个测试只保证"凡是写了这行的都必须带 || true"，不要求仓库里必须存在这行。

    def test_scripts_run_on_this_branch_exist_and_are_valid_shell(self):
        """只有没 pin ref 的工作流跑本分支代码，它们引用的脚本必须真的在这儿。"""
        for path in workflow_files():
            text = path.read_text(encoding="utf-8")
            scripts = re.findall(r"bash\s+(production/[\w./-]+\.sh)", text)
            refs = CHECKOUT_REF.findall(text)
            if refs:
                self.assertTrue(
                    all(not ref.startswith(("refs/", "$")) for ref in refs),
                    f"{path.name} 的 ref 是动态表达式，无法判断它跑哪个分支",
                )
                continue  # pin 了 ref 的工作流跑的是别的分支上的脚本，本分支没有是正常的
            for script in scripts:
                with self.subTest(workflow=path.name, script=script):
                    target = ROOT / script
                    self.assertTrue(target.exists(),
                                    f"{path.name} 在当前分支上调用了不存在的 {script}")
                    proc = subprocess.run(["bash", "-n", str(target)],
                                          capture_output=True, text=True)
                    self.assertEqual(proc.returncode, 0, f"{script} 语法错误：{proc.stderr}")

    def test_artifact_cleanup_workflow_can_actually_delete(self):
        """清理工作流必须声明 actions: write —— 没有它删除会 403，配额照样满。"""
        path = WORKFLOWS_DIR / "cleanup-artifacts.yml"
        self.assertTrue(path.exists(), "缺少 artifact 清理工作流")
        text = path.read_text(encoding="utf-8")
        self.assertIn("actions: write", text, "没声明 actions: write，删除会 403")
        self.assertIn("workflow_dispatch", text, "清理工作流要能手动触发")
        # 上传那一步不能因为配额满就把整场出片判死
        render = SHANGHAI_WORKFLOW.read_text(encoding="utf-8")
        upload_at = render.index("actions/upload-artifact")
        self.assertIn("continue-on-error: true", render[:upload_at][-400:],
                      "成片上传失败会把出片判死，但成片本来就 commit 回 交付/ 了")

    def test_shanghai_workflow_uses_the_generic_runner_switch_and_pins_the_branch(self):
        """上海片的出片工作流：runs-on 走开关、检出固定在本出片分支、只认 GEN_REQUEST。"""
        text = SHANGHAI_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(RUNNER_SWITCH, text)
        self.assertIn("refs/heads/arena/f9f847e0-desktop-tutorial", text)
        self.assertIn("production/shanghai_freezer_case/GEN_REQUEST", text)


if __name__ == "__main__":
    unittest.main()
