"""脚手架测试：新题目目录能不能被真实地用起来。

覆盖三件事：
1. 复制出来的引擎副本里没有残留参考项目的路径/分支/成片名；
2. 生成的 ``story.json`` 骨架在时间轴上是机械正确的（30 镜 × 6 秒、6 章 × 30 秒），
   并且 ``generate.validate()`` 在提示词为空时**会拦下来**、填完之后**放行**；
3. 参考项目 ``production/dahlia`` 在脚手架运行前后一个字节都没变。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "production"))
import agnes_video  # noqa: E402  (共用引擎：空提示词由它先拦下)
import new_topic  # noqa: E402

SLUG = "scaffoldtest"
TITLE = "测试题目：脚手架自检"
BRANCH = "arena/scaffold-test-branch"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _hash_tree(root: Path) -> dict:
    import hashlib
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


class ScaffoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dahlia_before = _hash_tree(ROOT / "production/dahlia")
        cls.tmp = Path(tempfile.mkdtemp(prefix="scaffold-test-"))
        # 副本里的 generate.py 会按 parents[2] 找仓库根，再把 ROOT/production
        # 放进 sys.path 去找共享引擎 agnes_video.py，所以临时目录要长成仓库的样子。
        cls.production = cls.tmp / "production"
        cls.production.mkdir(parents=True)
        shutil.copy2(ROOT / "production/agnes_video.py", cls.production / "agnes_video.py")
        cls.project_dir = cls.production / SLUG
        new_topic.scaffold(SLUG, TITLE, BRANCH, cls.project_dir, ROOT / "production/dahlia")

    @classmethod
    def tearDownClass(cls):
        for name in list(sys.modules):
            if name.startswith("scaffold_"):
                del sys.modules[name]
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # -- 1. 副本干净 ------------------------------------------------------
    def test_engine_files_copied_and_repointed(self):
        for name in new_topic.ENGINE_FILES:
            self.assertTrue((self.project_dir / name).is_file(), name)
        for name in ("story.json", "screenplay.md", "README.md",
                     f"{SLUG}.workflow.yml", "audio/manifest.json"):
            self.assertTrue((self.project_dir / name).is_file(), name)

        leftovers = []
        # 只扫"复制出来的副本"：.py / .yml / .sh。
        # story.json、README.md、screenplay.md 是新生成的文档，里面**故意**保留
        # "参考 production/dahlia" 的出处说明。
        for path in sorted(self.project_dir.rglob("*")):
            if not path.is_file() or path.suffix not in (".py", ".yml", ".sh"):
                continue
            text = path.read_text().lower()
            for token in ("production/dahlia", "work/dahlia", new_topic.REFERENCE_BRANCH,
                          "黑色大丽花", "消失的六天", "black dahlia", "dahlia",
                          "伊丽莎白", "肖特", "比尔特莫尔", "los angeles", "行踪缺口"):
                if token in text:
                    leftovers.append(f"{path.name}:{token}")
        self.assertEqual(leftovers, [])
        story = json.loads((self.project_dir / "story.json").read_text())
        self.assertEqual(story["_scaffold"]["reference"], "production/dahlia")
        # 参考片子的卡片文案、变体覆盖、特殊画法、档案照片、字幕关键词、
        # 逐镜标签、片头字幕卡——七处内容都必须留下显式 TODO
        render_source = (self.project_dir / "render.py").read_text()
        self.assertGreaterEqual(render_source.count("TODO"), 7,
                                "render.py 副本里参考项目的内容没有被标成 TODO")

    def test_branch_and_artifact_names_follow_the_new_project(self):
        generator = load_module("scaffold_generate", self.project_dir / "generate.py")
        self.assertEqual(generator.BRANCH, BRANCH)
        story = json.loads((self.project_dir / "story.json").read_text())
        self.assertEqual(story["branch"], BRANCH)
        self.assertEqual(story["title"], TITLE)
        workflow = (self.project_dir / f"{SLUG}.workflow.yml").read_text()
        self.assertIn(f"refs/heads/{BRANCH}", workflow)
        self.assertIn(f"{TITLE} · 出片", workflow)
        self.assertNotIn("dahlia", workflow.lower())
        # 出片步骤统一在共用脚本里，工作流只是薄薄一层
        self.assertIn(f"bash production/run_project.sh {SLUG}", workflow)

    # -- 2. 骨架正确 + 闸门有效 -------------------------------------------
    def test_story_skeleton_timeline_is_mechanically_correct(self):
        story = json.loads((self.project_dir / "story.json").read_text())
        self.assertEqual(len(story["shots"]), 30)
        for index, shot in enumerate(story["shots"]):
            self.assertEqual(shot["id"], f"S{index + 1:02d}")
            self.assertEqual(shot["start"], index * 6)
            self.assertEqual(shot["duration"], 6)
        self.assertEqual(sum(chapter["duration"] for chapter in story["chapters"]), 180)
        # 每段解说对应 5 个镜头：N01 -> S01..S05，N06 -> S26..S30
        self.assertEqual(story["shots"][0]["narration_id"], "N01")
        self.assertEqual(story["shots"][4]["narration_id"], "N01")
        self.assertEqual(story["shots"][5]["narration_id"], "N02")
        self.assertEqual(story["shots"][29]["narration_id"], "N06")

    def test_validate_blocks_the_empty_skeleton(self):
        generator = load_module("scaffold_generate_gate", self.project_dir / "generate.py")
        story = json.loads((self.project_dir / "story.json").read_text())
        # 提示词与 style_prefix 都是空的：validate() 必须抛错，不许去烧生成额度。
        # 空提示词由 agnes_video.build_payload 先拦（Fatal），其余结构性错误是 ValueError。
        with self.assertRaises((ValueError, agnes_video.Fatal)) as caught:
            generator.validate(story)
        self.assertIn("prompt", str(caught.exception).lower())

    def test_validate_passes_once_the_plan_is_written(self):
        generator = load_module("scaffold_generate_filled", self.project_dir / "generate.py")
        story = json.loads((self.project_dir / "story.json").read_text())
        story["style_prefix"] = "Photorealistic documentary reconstruction, 16:9. "
        for shot in story["shots"]:
            shot["prompt"] = f"a wide establishing shot of a foggy street, unit {shot['id']}"
        for chapter in story["chapters"]:
            chapter["title"] = "章节"
            chapter["text"] = "解说词占位，实际写作时按九十到一百二十字填写。"
        generator.validate(story)              # 填完必须放行
        for shot in story["shots"]:
            self.assertEqual(generator.full_payload(story, shot)["model"], "agnes-video-v2.0")
            self.assertEqual((generator.full_payload(story, shot)["num_frames"] - 1) % 8, 0)

    def test_render_cuts_skeleton_matches_the_story_grid(self):
        render = load_module("scaffold_render", self.project_dir / "render.py")
        story = json.loads((self.project_dir / "story.json").read_text())
        self.assertEqual(sorted(render.CUTS), [f"N{i:02d}" for i in range(1, 7)])
        known = {shot["id"] for shot in story["shots"]}
        for cue, entries in render.CUTS.items():
            self.assertEqual(len(entries), 5, cue)
            for offset, shot_id, variant in entries:
                self.assertIn(shot_id, known)
                self.assertEqual(variant, "")
                self.assertIsInstance(offset, (int, float))

    def test_narration_manifest_is_bound_to_the_chapter_ids(self):
        story = json.loads((self.project_dir / "story.json").read_text())
        manifest = json.loads((self.project_dir / "audio/manifest.json").read_text())
        self.assertEqual([clip["id"] for clip in manifest["clips"]],
                         [chapter["id"] for chapter in story["chapters"]])
        for clip in manifest["clips"]:
            self.assertEqual(clip["sha256"], "")   # 没配音就是空，generate.py 会拒绝
            self.assertEqual(clip["text"], "")

    # -- 3. 参考项目不许被动 ----------------------------------------------
    def test_reference_project_is_untouched(self):
        # 脚手架运行前后，参考项目每个文件的哈希必须完全一致。
        # （不能用 git status：参考项目里允许另外提交审片记录这类新文件。）
        self.assertEqual(_hash_tree(ROOT / "production/dahlia"), self.dahlia_before,
                         "脚手架不允许修改已交付的参考项目")

    def test_scaffold_refuses_to_overwrite_an_existing_project(self):
        with self.assertRaises(SystemExit):
            new_topic.scaffold(SLUG, TITLE, BRANCH, self.project_dir,
                               ROOT / "production/dahlia")


if __name__ == "__main__":
    unittest.main()
