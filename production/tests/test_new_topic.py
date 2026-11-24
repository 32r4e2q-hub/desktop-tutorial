"""脚手架测试（上海冰柜藏尸案模式）：新题目目录能不能被真实地用起来。

覆盖四件事：
1. 复制出来的引擎副本、渲染模板、工作流里没有残留参考项目的路径 / 分支 / 片名 / 案件内容；
2. 生成的 ``story.json`` 骨架在时间轴上是机械正确的（30 镜 × 6 秒、6 章 × 30 秒），
   ``generate.validate()`` 在内容为空时**会拦下来**、填完（含批准参考图与配音收据）之后**放行**；
3. 模板 ``build_story.py`` 能写出带 ``presentation`` 的 story.json，
   模板 ``render.py`` 只留本片常数的钩子（END_FADES），不把 上海片的结尾定稿烧进去；
4. 参考项目 ``production/shanghai_freezer_case`` 在脚手架运行前后一个字节都没变。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "production"))
import agnes_video  # noqa: E402  (共用引擎：空提示词由它先拦下)
import new_topic  # noqa: E402

SLUG = "scaffoldtest"
TITLE = "测试题目：脚手架自检"
BRANCH = "arena/scaffold-test-branch"
REFERENCE = ROOT / "production/shanghai_freezer_case"
RUNS_ON = "runs-on: ${{ vars.RUNNER_LABEL || 'ubuntu-latest' }}"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _hash_tree(root: Path) -> dict:
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            out[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


class ScaffoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference_before = _hash_tree(REFERENCE)
        cls.tmp = Path(tempfile.mkdtemp(prefix="scaffold-test-"))
        # 副本里的 generate.py 会按 parents[2] 找仓库根，再把 ROOT/production
        # 放进 sys.path 去找共享引擎 agnes_video.py，所以临时目录要长成仓库的样子。
        cls.production = cls.tmp / "production"
        cls.production.mkdir(parents=True)
        shutil.copy2(ROOT / "production/agnes_video.py", cls.production / "agnes_video.py")
        shutil.copy2(ROOT / "production/gwangju_style.py", cls.production / "gwangju_style.py")
        if (ROOT / ".cache/fonts").is_dir():   # 渲染信息卡用的 CJK 字体（render 先查 ROOT/.cache/fonts）
            shutil.copytree(ROOT / ".cache/fonts", cls.tmp / ".cache/fonts")
        cls.project_dir = cls.production / SLUG
        new_topic.scaffold(SLUG, TITLE, BRANCH, cls.project_dir, REFERENCE)
        cls.workflows = {
            "case": cls.project_dir / "workflows" / f"{SLUG}.yml",
            "verbatim": cls.project_dir / "workflows" / f"{SLUG}-verbatim.yml",
            "visual-qc": cls.project_dir / "workflows" / f"{SLUG}-visual-qc.yml",
        }

    @classmethod
    def tearDownClass(cls):
        for name in list(sys.modules):
            if name.startswith("scaffold_"):
                del sys.modules[name]
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # -- 1. 副本干净 ------------------------------------------------------
    def test_engine_template_and_workflow_files_present(self):
        for name in (*new_topic.ENGINE_FILES, *new_topic.TEMPLATE_FILES):
            self.assertTrue((self.project_dir / name).is_file(), name)
        for name in ("story.json", "screenplay.md", "README.md",
                     "audio/manifest.json", "reference/approvals.json"):
            self.assertTrue((self.project_dir / name).is_file(), name)
        for path in self.workflows.values():
            self.assertTrue(path.is_file(), path.name)

    def test_no_reference_identity_leaks_into_the_copy(self):
        leftovers = []
        # 只扫"复制出来的副本"：.py / .yml。story.json、README.md、screenplay.md 是新生成的文档，
        # 里面**故意**保留"参考 production/shanghai_freezer_case"的出处说明。
        # build_story.py 的文档字符串也允许提一次出处；案情内容、分支、成片名一个都不许出现。
        forbidden = ("work/shanghai_freezer_case", new_topic.REFERENCE_BRANCH, "f9f847e0",
                     new_topic.REFERENCE_FILM, new_topic.REFERENCE_TITLE, new_topic.REFERENCE_STEM,
                     "上海冰柜藏尸案", "朱晓东", "杨俪萍", "杨父", "20161017", "2017年2月1日",
                     "shanghai_freezer_case-agnes", "上海")
        for path in sorted(self.project_dir.rglob("*")):
            if not path.is_file() or path.suffix not in (".py", ".yml"):
                continue
            text = path.read_text(encoding="utf-8")
            lowered = text.lower()
            for token in forbidden:
                if token.lower() in lowered:
                    leftovers.append(f"{path.name}:{token}")
            if path.name != "build_story.py" and "shanghai_freezer_case" in lowered:
                leftovers.append(f"{path.name}:shanghai_freezer_case")
        self.assertEqual(leftovers, [])
        story = json.loads((self.project_dir / "story.json").read_text())
        self.assertEqual(story["_scaffold"]["reference"], "production/shanghai_freezer_case")
        self.assertEqual(story["presentation"]["hooks"], [])

    def test_branch_and_artifact_names_follow_the_new_project(self):
        generator = load_module("scaffold_generate", self.project_dir / "generate.py")
        self.assertEqual(generator.BRANCH, BRANCH)
        story = json.loads((self.project_dir / "story.json").read_text())
        self.assertEqual(story["branch"], BRANCH)
        self.assertEqual(story["title"], TITLE)
        film = new_topic.film_name(TITLE)
        self.assertEqual(film, "测试题目_脚手架自检_三分钟_带声音.mp4")
        self.assertEqual(story["film_name"], film)
        for kind, path in self.workflows.items():
            text = path.read_text(encoding="utf-8")
            self.assertIn(f"refs/heads/{BRANCH}", text, kind)
            self.assertIn(f"production/{SLUG}/", text, kind)
            self.assertNotIn("shanghai_freezer_case", text.lower(), kind)
        case = self.workflows["case"].read_text(encoding="utf-8")
        self.assertIn(f"production/{SLUG}/GEN_REQUEST", case)
        self.assertIn(f"python3 production/{SLUG}/generate.py --validate", case)
        self.assertIn(f"production/{SLUG}/CANCEL_REQUEST", case)
        verbatim = self.workflows["verbatim"].read_text(encoding="utf-8")
        self.assertIn(f"production/{SLUG}/VERBATIM_REQUEST", verbatim)
        self.assertIn("production/verbatim_check.py", verbatim)
        self.assertIn(film, verbatim)
        visual_qc = self.workflows["visual-qc"].read_text(encoding="utf-8")
        self.assertIn(f"production/{SLUG}/VISUAL_QC_REQUEST", visual_qc)
        self.assertIn(f"production/{SLUG}/qc.py", visual_qc)

    def test_workflows_parse_and_follow_repo_conventions(self):
        for kind, path in self.workflows.items():
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertIsInstance(doc, dict, kind)
            trigger = doc.get("on", doc.get(True))
            self.assertIsInstance(trigger, dict, kind)
            self.assertEqual(trigger["push"]["branches"], [BRANCH], kind)
            self.assertTrue(doc.get("jobs"), kind)
            for job in doc["jobs"].values():
                self.assertTrue(job.get("steps"), kind)
            self.assertIn(RUNS_ON, path.read_text(encoding="utf-8"), kind)
            self.assertIn(SLUG, doc["concurrency"]["group"], kind)

    # -- 2. 骨架正确 + 闸门有效 -------------------------------------------
    def test_story_skeleton_timeline_is_mechanically_correct(self):
        story = json.loads((self.project_dir / "story.json").read_text())
        self.assertEqual(len(story["shots"]), 30)
        self.assertEqual(story["target_duration"], 180)
        self.assertEqual((story["width"], story["height"], story["fps"]), (1920, 1080, 24))
        self.assertEqual(story["model"], "agnes-video-2.5-flash")
        self.assertEqual(story["source_size"], "720P")
        for index, shot in enumerate(story["shots"]):
            self.assertEqual(shot["id"], f"S{index + 1:02d}")
            self.assertEqual(shot["start"], index * 6)
            self.assertEqual(shot["duration"], 6)
            self.assertEqual(shot["seconds"], 6)
            self.assertEqual(shot["kind"], "agnes")
            self.assertEqual(shot["aspect"], "16:9")
        self.assertEqual([c["start"] for c in story["chapters"]], [0, 30, 60, 90, 120, 150])
        self.assertEqual(sum(chapter["duration"] for chapter in story["chapters"]), 180)
        self.assertEqual(story["shots"][0]["narration_id"], "N01")
        self.assertEqual(story["shots"][4]["narration_id"], "N01")
        self.assertEqual(story["shots"][5]["narration_id"], "N02")
        self.assertEqual(story["shots"][29]["narration_id"], "N06")
        self.assertEqual(len({shot["seed"] for shot in story["shots"]}), 30)

    def test_validate_blocks_the_empty_skeleton(self):
        generator = load_module("scaffold_generate_gate", self.project_dir / "generate.py")
        story = json.loads((self.project_dir / "story.json").read_text())
        # 提示词、解说词、style 都是空的：validate() 必须抛错，不许去烧生成额度。
        with self.assertRaises((ValueError, agnes_video.Fatal)):
            generator.validate(story)

    def test_validate_passes_once_the_plan_is_written(self):
        generator = load_module("scaffold_generate_filled", self.project_dir / "generate.py")
        project_dir = self.project_dir
        story = json.loads((project_dir / "story.json").read_text())
        prefix = "【STYLE】Hand-drawn 2D documentary, muted palette, 16:9. "
        story["style_prefix"] = prefix
        story["style_rumor_prefix"] = prefix
        story["negative_prompt"] = "【NEGATIVE】readable text, blood, corpse"
        for shot in story["shots"]:
            shot["prompt"] = f"a wide establishing shot of a foggy street, unit {shot['id']}"
            shot["narration"] = f"第{int(shot['id'][1:])}句解说。"
            shot["reference_ids"] = "R1"
        for chapter in story["chapters"]:
            chapter["title"] = "章节"
            chapter["text"] = "解说词占位，实际写作时逐句填写。"
        # 批准参考图：validate 要求 1–5 张 approved、PNG 魔数、sha256 与 approvals.json 一致
        from PIL import Image
        import io
        ref = project_dir / "reference" / "R1.png"
        Image.new("RGB", (16, 16), (24, 32, 48)).save(ref, format="PNG")
        ref_sha = hashlib.sha256(ref.read_bytes()).hexdigest()
        revision = "deadbeef" * 5
        (project_dir / "reference" / "approvals.json").write_text(json.dumps({
            "assets": {"R1": {"status": "approved", "file": "reference/R1.png", "sha256": ref_sha}},
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (project_dir / "reference" / "revision.txt").write_text(revision + "\n", encoding="utf-8")
        story["reference_images"] = [{
            "id": "R1", "file": "reference/R1.png", "status": "approved", "sha256": ref_sha,
        }]
        story["reference_revision"] = revision
        # 配音收据：require_audio=True 时要求每镜一条 sha256 对得上的音频
        audio_dir = project_dir / "audio"
        audio_dir.mkdir(exist_ok=True)
        voice_id = "voice-test"
        story["narration_spec"]["voice_id"] = voice_id
        clips = []
        for shot in story["shots"]:
            clip = audio_dir / f"{shot['id']}.mp3"
            clip.write_bytes(f"fake-tts-{shot['id']}".encode())
            clips.append({
                "id": shot["id"], "file": clip.name, "text": shot["narration"],
                "sha256": hashlib.sha256(clip.read_bytes()).hexdigest(),
                "voice_id": voice_id, "narration_id": shot["narration_id"],
                "target_start": shot["start"], "target_duration": shot["duration"],
                "alignment": "shot-locked",
            })
        (audio_dir / "manifest.json").write_text(json.dumps({
            "language": "zh-CN", "voice": voice_id,
            "generation": "test", "alignment": "one-clip-one-shot-one-caption",
            "max_speedup_factor": 1.55, "slowdown_allowed": False, "clips": clips,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        generator.validate(story)              # 填完必须放行
        for shot in story["shots"]:
            payload = generator.full_payload(story, shot)
            self.assertEqual(payload["model"], "agnes-video-2.5-flash")

    def test_narration_manifest_is_bound_to_the_shot_ids(self):
        story = json.loads((self.project_dir / "story.json").read_text())
        manifest = json.loads((self.project_dir / "audio" / "manifest.json").read_text())
        self.assertEqual([clip["id"] for clip in manifest["clips"]],
                         [shot["id"] for shot in story["shots"]])
        self.assertEqual(manifest["alignment"], "one-clip-one-shot-one-caption")
        self.assertIs(manifest["slowdown_allowed"], False)
        for clip, shot in zip(manifest["clips"], story["shots"]):
            self.assertEqual(clip["sha256"], "")   # 没配音就是空，build_audio_manifest.py 会拒绝
            self.assertEqual(clip["text"], "")
            self.assertEqual(clip["target_start"], shot["start"])
            self.assertEqual(clip["target_duration"], shot["duration"])

    # -- 3. 模板 render.py / build_story.py 的守卫 ---------------------------
    def test_render_template_keeps_only_the_local_fade_hook(self):
        render = load_module("scaffold_render", self.project_dir / "render.py")
        self.assertEqual(render.FPS, 24)
        self.assertEqual(render.END_FADES, {"S30": (0.8, 0.8)})
        # 上海片专属的结尾定稿（第28镜日历/年仅32岁）不许被带进模板
        text = (self.project_dir / "render.py").read_text(encoding="utf-8")
        self.assertNotIn("S28", text)

    def test_build_story_template_writes_presentation_and_publish_copy(self):
        # 在一个独立副本上跑，不污染其它测试读取的骨架
        project = self.production / "buildtest"
        new_topic.scaffold("buildtest", TITLE, BRANCH, project, REFERENCE)
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        run = subprocess.run([sys.executable, "build_story.py"], cwd=project, capture_output=True, text=True, env=env)
        self.assertEqual(run.returncode, 0, run.stderr)
        story = json.loads((project / "story.json").read_text())
        self.assertEqual(len(story["shots"]), 30)
        self.assertEqual([s["id"] for s in story["shots"]], [f"S{i:02d}" for i in range(1, 31)])
        self.assertEqual(sum(s["duration"] for s in story["shots"]), 180)
        for key in ("onscreen_label", "highlight_phrases", "hooks", "explainers",
                    "end_title", "end_subtitle", "title_start", "title_end", "cover_text",
                    "cover_concept", "publish_title", "hashtags", "caption_policy"):
            self.assertIn(key, story["presentation"], key)
        self.assertEqual(story["presentation"]["onscreen_label"], "AI动画情景重现 · 非真实影像")
        publish = (project / "抖音发布文案.md").read_text(encoding="utf-8")
        for heading in ("## 抖音标题", "## 简短介绍", "## 提问读者一句话", "## 话题"):
            self.assertIn(heading, publish)

    def test_manifest_schema_matches_build_audio_manifest(self):
        # 骨架 manifest 必须是 build_audio_manifest.py 能原样回填的形状
        manifest = json.loads((self.project_dir / "audio" / "manifest.json").read_text())
        self.assertEqual(manifest["alignment"], "one-clip-one-shot-one-caption")
        self.assertEqual(manifest["max_speedup_factor"], 1.55)
        self.assertEqual(set(manifest["clips"][0]),
                         {"id", "file", "text", "sha256", "voice_id", "voice_description",
                          "narration_id", "target_start", "target_duration", "alignment",
                          "source_duration", "atempo", "tail_silence_seconds"})

    # -- 4. 参考项目不许被动 ----------------------------------------------
    def test_reference_project_is_untouched(self):
        # 脚手架运行前后，参考项目每个文件的哈希必须完全一致。
        self.assertEqual(_hash_tree(REFERENCE), self.reference_before,
                         "脚手架不允许修改已交付的参考项目")

    def test_scaffold_refuses_to_overwrite_an_existing_project(self):
        with self.assertRaises(SystemExit):
            new_topic.scaffold(SLUG, TITLE, BRANCH, self.project_dir, REFERENCE)


if __name__ == "__main__":
    unittest.main()
