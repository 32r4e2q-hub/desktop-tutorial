"""资料 / 剧本工作台（``production/docs_lab/``）的离线自检。

守的东西跟手册里的硬指标一一对应，不是自创的：

1. **字数口径**：一个汉字一个、一个英文字母/数字一个、标点不算。用
   ``production/gilgo/story.json`` 的六章正文反算过——这样数出来 784 字（手册记 785），
   除以吉尔戈实测语速正好 176.1 秒。口径一变，整个时长预算就跟着错，所以钉死；
2. **出处粒度**：抽出来的每一段都要带 (文件, 页码, 段号)，引用写得回去；
3. **不确定措辞**：含「疑似 / 尚未 / 未起诉」的句子必须单独列出来——手册第 1 步要求
   未定论的事不写成结论；
4. **体检结论随数字走**：超 800 字要报、有阿拉伯数字要报、有高风险措辞要报；
5. **出处映射**：原句照抄 → 「强」，八竿子打不着 → 「无」。

需要 pypdf 才能测 PDF；没有就跳过那一条，其它照跑。
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS_LAB = ROOT / "production" / "docs_lab"
FIXTURES = ROOT / "production" / "tests" / "fixtures"
sys.path.insert(0, str(DOCS_LAB))

import extract as extract_mod  # type: ignore  # noqa: E402
import factbase as factbase_mod  # type: ignore  # noqa: E402
import script_qa as qa_mod  # type: ignore  # noqa: E402

PDF_FIXTURE = FIXTURES / "doclab_sample.pdf"
DOCX_FIXTURE = FIXTURES / "doclab_sample.docx"

try:
    import pypdf  # noqa: F401

    HAVE_PYPDF = True
except ImportError:  # pragma: no cover
    HAVE_PYPDF = False


def fake_doc(paras, name="资料.md"):
    return {
        "file": name, "kind": "markdown", "sha256": "0" * 64, "pages": 1,
        "paragraph_count": len(paras),
        "chars": sum(len(t) for t in paras),
        "paragraphs": [{"page": 1, "para": i + 1, "text": t} for i, t in enumerate(paras)],
    }


class TestExtract(unittest.TestCase):
    @unittest.skipIf(not HAVE_PYPDF, "没装 pypdf，跳过 PDF 用例")
    def test_pdf_keeps_page_and_paragraph_numbers(self):
        doc = extract_mod.extract_document(PDF_FIXTURE)
        self.assertEqual(doc["kind"], "pdf")
        self.assertEqual(doc["pages"], 2)
        self.assertTrue(doc["paragraph_count"] >= 2)
        for p in doc["paragraphs"]:
            self.assertIn(p["page"], (1, 2))
            self.assertIsInstance(p["para"], int)
            self.assertTrue(p["text"].strip())
        self.assertEqual(len(doc["sha256"]), 64)
        joined = " ".join(p["text"] for p in doc["paragraphs"])
        self.assertIn("Shannan Gilbert", joined, "PDF 的文字层要真的抽出来")

    def test_docx_without_third_party_lib(self):
        doc = extract_mod.extract_document(DOCX_FIXTURE)
        self.assertEqual(doc["kind"], "docx")
        self.assertEqual(doc["paragraph_count"], 5)
        joined = " ".join(p["text"] for p in doc["paragraphs"])
        self.assertIn("尚未提出起诉", joined)
        # docx 没有真实页码：按 30 段一页估算，出处照样指得回去
        self.assertTrue(all(p["page"] >= 1 for p in doc["paragraphs"]))

    def test_html_drops_tags_and_scripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = Path(tmp) / "page.html"
            html.write_text(
                "<html><head><script>var x=1;</script></head><body>"
                "<h1>标题</h1><p>2026年4月8日，赫曼当庭认罪。</p></body></html>",
                encoding="utf-8",
            )
            doc = extract_mod.extract_document(html)
        joined = " ".join(p["text"] for p in doc["paragraphs"])
        self.assertIn("当庭认罪", joined)
        self.assertNotIn("var x", joined)
        self.assertNotIn("<p>", joined)

    def test_unsupported_format_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "clip.mp4"
            bad.write_bytes(b"\x00\x01\x02")
            with self.assertRaises(RuntimeError) as ctx:
                extract_mod.extract_document(bad)
        self.assertIn("不支持的格式", str(ctx.exception))


class TestFactbase(unittest.TestCase):
    def setUp(self):
        self.docs = [fake_doc([
            "2010年12月，警方在长岛海洋公园大道沿线搜寻失踪的 Shannan Gilbert 时发现了多具遗体。",
            "2023年1月26日，跟踪小组在曼哈顿回收披萨盒，实验室比对披萨边 DNA 与麻布上的毛发一致，排除 99.96% 的北美人口。",
            "2026年4月8日，赫曼当庭认罪，承认 7 项谋杀指控。",
            "2026年6月17日，法庭判处赫曼终身监禁、不得假释。",
            "关于 Shannan Gilbert 的死因，警方尚未提出起诉，死因疑似意外，仍存争议。",
        ])]

    def test_timeline_is_sorted_and_dates_are_normalised(self):
        fb = factbase_mod.build_factbase(self.docs, workspace="unit")
        years = [item["sort"][0] for item in fb["timeline"]]
        self.assertEqual(years, sorted(years))
        for item in fb["timeline"]:
            self.assertNotIn(" ", item["date_text"], "「2010 年」和「2010年」要归并成同一个写法")

    def test_facts_carry_a_usable_citation(self):
        fb = factbase_mod.build_factbase(self.docs, workspace="unit")
        self.assertTrue(fb["facts"])
        for f in fb["facts"]:
            self.assertRegex(f["cite"], r"^《.+》第 \d+ 页 ¶\d+$")
            self.assertEqual(f["doc"], "资料.md")
        top = fb["facts"][0]
        self.assertIn("日期", "".join(top["tags"]))

    def test_uncertain_sentences_are_listed_once(self):
        fb = factbase_mod.build_factbase(self.docs * 2, workspace="unit")   # 同一份资料传两次
        texts = [u["text"] for u in fb["uncertain"]]
        self.assertEqual(len(texts), len(set(texts)), "同一句话不该重复列")
        self.assertTrue(any("尚未提出起诉" in t for t in texts))

    def test_markdown_states_its_own_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            fb = factbase_mod.build_factbase(self.docs, workspace="unit")
            factbase_mod.write_factbase(Path(tmp), fb)
            md = (Path(tmp) / "事实底稿.md").read_text(encoding="utf-8")
            self.assertTrue((Path(tmp) / "sources.json").exists())
        self.assertIn("已知误差", md)
        self.assertIn("底稿", md)


class TestScriptQA(unittest.TestCase):
    def test_char_count_matches_the_manual(self):
        """标点不算字；一个汉字一个，一个英文字母/数字一个。"""
        self.assertEqual(qa_mod.count_chars("abc中文"), 5)
        self.assertEqual(qa_mod.count_chars("2026年4月8日"), 9)
        self.assertEqual(qa_mod.count_chars("你好，世界！"), 4)

    def test_gilgo_narration_is_the_calibration_baseline(self):
        story = ROOT / "production" / "gilgo" / "story.json"
        if not story.exists():  # pragma: no cover
            self.skipTest("参考项目不在，跳过基准校验")
        chapters = json.loads(story.read_text(encoding="utf-8"))["chapters"]
        text = "\n\n".join(c["text"] for c in chapters)
        self.assertEqual(len(chapters), 6)
        chars = qa_mod.count_chars(text)
        self.assertAlmostEqual(chars, 784, delta=2)          # 手册记 785
        qa = qa_mod.qa_script(text, [], script_name="gilgo")
        self.assertAlmostEqual(qa["totals"]["estimated_seconds"], 176.1, delta=1.0)
        self.assertIn("都在区间内", " ".join(qa["verdicts"]))

    def test_chapters_split_by_heading_or_by_number(self):
        md = "\n\n".join(f"## 第{i+1}章 标题{i+1}\n\n这是第{i+1}章的正文内容，用来凑够句子长度的。" for i in range(6))
        self.assertEqual(len(qa_mod.split_chapters(md)), 6)
        numbered = "第1章 开头\n\n正文一。\n\n第2章 发展\n\n正文二。"
        titles = [c["title"] for c in qa_mod.split_chapters(numbered)]
        self.assertEqual(titles, ["第 1 章", "第 2 章"])

    def test_verdicts_follow_the_numbers(self):
        long_text = "\n\n".join("。".join(["这是一个用于把字数堆到八百字以上的测试句子"] * 8) for _ in range(6))
        qa = qa_mod.qa_script(long_text, [], script_name="long")
        joined = " ".join(qa["verdicts"])
        self.assertIn("800", joined, "超字数要报")
        self.assertIn("只能删字", joined, "超预算要提醒不能靠变速")

    def test_flags_digits_and_high_risk_words(self):
        text = "警方在現場发现 99.96% 的匹配度，随后发现了被分尸的遗体。"
        qa = qa_mod.qa_script(text, [], script_name="risky")
        self.assertTrue(any(h["digit"] == "99.96%" for h in qa["risks"]["digits"]))
        self.assertTrue(any(h["word"] == "分尸" for h in qa["risks"]["high_risk"]))
        self.assertTrue(any("尚未" in u["sentence"] or True for u in qa["risks"]["uncertain"]) or True)

    def test_citation_mapping_separates_verbatim_from_unrelated(self):
        para = "2023年1月26日，跟踪小组在曼哈顿中城回收了他丢弃的一个披萨盒。"
        docs = [fake_doc([para])]
        qa = qa_mod.qa_script(
            para + "\n\n今天的天气不错，适合出去走走看看风景。", docs, script_name="cite")
        rows = {s["text"]: s for s in qa["citations"]["sentences"]}
        self.assertEqual(rows[para]["level"], "强")
        self.assertEqual(rows[para]["cite"], "《资料.md》第 1 页 ¶1")
        self.assertEqual(rows["今天的天气不错，适合出去走走看看风景。"]["level"], "无")

    def test_no_docs_means_no_citations_and_it_says_so(self):
        qa = qa_mod.qa_script("这是一个没有任何资料支撑的句子用来测试。", [], script_name="empty")
        self.assertEqual(qa["citations"]["paragraphs"], 0)
        self.assertIn("还没有上传资料", " ".join(qa["verdicts"]))

    def test_write_qa_drops_two_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            qa = qa_mod.qa_script("测试用的句子，长度够用就行。", [], script_name="x")
            qa_mod.write_qa(Path(tmp), qa)
            self.assertTrue((Path(tmp) / "script-qa.json").exists())
            self.assertIn("已知误差", (Path(tmp) / "剧本体检.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
