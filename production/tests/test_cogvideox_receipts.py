"""《姜浩顺》智谱收据逻辑的离线自检（不联网、不花配额）。

为什么单独守这几条：出片链的钱都花在「这一镜要不要重投」这一个判断上。

1. **定妆照开关**（``ref_image``）：免费档收不收 ``image_url`` 随服务端负载波动
   （2026-10-12 实测 02:00 探测 429、03:00 supported=true、04:00 带图任务排队
   20 分钟全超时）。开关必须只影响 payload 形状，且两种形状的哈希都得在
   ``fetch_sources.cogvideox_request_hashes`` 的认账集合里 —— 否则 render 会把
   已经签收的素材判成缺料。
2. **历史收据恢复**：开关一抖动，旧收据就落在 ``previous_results`` 里；本轮要哪个
   版本就得先找回来，找不到才生成（否则每抖一次都重烧一次配额）。
"""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "production" / "kanghosun2009"


_CACHE: dict[str, object] = {}


def _load(name: str):
    """按路径加载本项目引擎，并把这次加载带进 ``sys.modules`` 的旁链清干净。

    清理不是洁癖：仓库里每个项目都有一份 ``generate.py`` / ``media.py``，本项目
    ``fetch_sources.py`` 顶层那句 ``from generate import request_hash`` 会把
    （按 ``sys.path`` 顺序）先撞上的那份留在 ``sys.modules['generate']``；后面的
    ``test_dahlia.py`` 再 import 时拿到的就是别人的模块 —— 实测直接把它的两条
    收据断言弄红。只删本次加载**新增**的条目，已缓存的不动。
    """
    if name in _CACHE:
        return _CACHE[name]
    before = set(sys.modules)
    spec = importlib.util.spec_from_file_location(f"kanghosun2009_test_{name}",
                                                  PROJECT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        for extra in set(sys.modules) - before:
            sys.modules.pop(extra, None)
    _CACHE[name] = module
    return module


cog = _load("generate_cogvideox")
fetch = _load("fetch_sources")
STORY = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))
CAST_SHOT = next(s for s in STORY["shots"] if s.get("reference_image"))
PLAIN_SHOT = next(s for s in STORY["shots"]
                  if s.get("kind") != "graphic" and not s.get("reference_image"))


class RefImageSwitchTests(unittest.TestCase):
    def setUp(self):
        self._mode, self._ok = cog.REF_IMAGE_MODE, cog.REF_IMAGE_OK

    def tearDown(self):
        cog.REF_IMAGE_MODE, cog.REF_IMAGE_OK = self._mode, self._ok

    def test_parse_accepts_bools_and_strings(self):
        self.assertIsNone(cog.parse_ref_image(None))
        self.assertIs(cog.parse_ref_image(True), True)
        self.assertIs(cog.parse_ref_image(False), False)
        for truthy in ("1", "true", "TRUE", "yes", " on "):
            self.assertIs(cog.parse_ref_image(truthy), True, truthy)
        for falsy in ("0", "false", "no", "off", ""):
            self.assertIs(cog.parse_ref_image(falsy), False, falsy)

    def test_forced_plain_skips_probe_even_with_client_none(self):
        cog.REF_IMAGE_MODE = False
        record = cog.probe_ref_image(None, STORY)  # client=None：探测被短路，不该碰它
        self.assertTrue(record["skipped"])
        self.assertFalse(cog.REF_IMAGE_OK)

    def test_payload_shape_follows_the_switch(self):
        cog.REF_IMAGE_MODE = False
        cog.probe_ref_image(None, STORY)
        plain = cog.full_payload(STORY, CAST_SHOT)
        cog.REF_IMAGE_MODE = True
        cog.probe_ref_image(None, STORY)
        with_portrait = cog.full_payload(STORY, CAST_SHOT)
        self.assertNotIn("image_url", plain)
        self.assertEqual(with_portrait["image_url"], CAST_SHOT["reference_image"])
        self.assertEqual(sorted(plain), ["model", "prompt", "quality"])
        # 纯文生镜头在两种模式下都不该带图。
        cog.REF_IMAGE_MODE = True
        cog.probe_ref_image(None, STORY)
        self.assertNotIn("image_url", cog.full_payload(STORY, PLAIN_SHOT))

    def test_both_hash_flavours_are_accepted_by_the_render_gate(self):
        plain_hash, with_hash = fetch.cogvideox_request_hashes(STORY, CAST_SHOT)
        self.assertNotEqual(plain_hash, with_hash)
        cog.REF_IMAGE_MODE, cog.REF_IMAGE_OK = None, None
        self.assertEqual(cog.request_hash(STORY, CAST_SHOT), plain_hash)
        cog.REF_IMAGE_MODE, cog.REF_IMAGE_OK = None, True
        self.assertEqual(cog.request_hash(STORY, CAST_SHOT), with_hash)
        # 开关不该改变纯文生镜头的哈希（否则 38 镜全被重投）。
        self.assertEqual(fetch.cogvideox_request_hashes(STORY, PLAIN_SHOT),
                         (cog.request_hash(STORY, PLAIN_SHOT),) * 2)


class ReceiptReuseTests(unittest.TestCase):
    WANTED = "a" * 64

    def receipt(self, **overrides):
        row = {"id": "S22", "status": "completed", "request_hash": self.WANTED,
               "video_url": "https://example.invalid/S22.mp4", "sha256": "b" * 64}
        row.update(overrides)
        return row

    def test_current_receipt_is_kept(self):
        doc = {"shots": {"S22": self.receipt()}}
        self.assertEqual(cog.reuse_receipt(doc, "S22", self.WANTED), "current")
        self.assertNotIn("previous_results", doc)

    def test_history_receipt_is_revived_and_replaces_the_stale_row(self):
        doc = {"shots": {"S22": {"id": "S22", "status": "failed", "error": "1301"}},
               "previous_results": {"S22": [self.receipt()]}}
        self.assertEqual(cog.reuse_receipt(doc, "S22", self.WANTED), "history")
        self.assertEqual(doc["shots"]["S22"]["status"], "completed")
        self.assertEqual(doc["shots"]["S22"]["sha256"], "b" * 64)
        self.assertEqual(doc["previous_results"]["S22"][-1]["status"], "failed")

    def test_hash_mismatch_means_generate_and_archives_the_old_row(self):
        doc = {"shots": {"S22": self.receipt(request_hash="c" * 64)}}
        self.assertEqual(cog.reuse_receipt(doc, "S22", self.WANTED), "generate")

    def test_history_with_wrong_hash_is_not_good_enough(self):
        doc = {"shots": {},
               "previous_results": {"S22": [self.receipt(request_hash="c" * 64)]}}
        self.assertEqual(cog.reuse_receipt(doc, "S22", self.WANTED), "generate")

    def test_incomplete_history_rows_are_ignored(self):
        # 没有 video_url / sha256 的行是「提交过但没收货」，不算收据。
        broken = self.receipt(video_url=None)
        doc = {"shots": {}, "previous_results": {"S22": [broken]}}
        self.assertEqual(cog.reuse_receipt(doc, "S22", self.WANTED), "generate")

    def test_empty_placeholder_is_not_pushed_into_history(self):
        doc = {"shots": {"S22": {"id": "S22"}}, "previous_results": {}}
        self.assertEqual(cog.reuse_receipt(doc, "S22", self.WANTED), "generate")
        self.assertEqual(doc["previous_results"].get("S22") or [], [])


if __name__ == "__main__":
    unittest.main()
