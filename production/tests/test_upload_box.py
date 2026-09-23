"""投递台测试：Word/Excel 表格能不能变成我能直接读的正文，上传接口能不能真落盘。

覆盖：
1. 手搓的最小 .docx（zip + document.xml）里那张表被原样解析成 Markdown，中文和竖线不丢；
2. .xlsx 的共享字符串 + 稀疏列（B/D 有值）能补成对齐的表格；
3. 旧版 .doc / .xls 给的是**人话错误**，不是 traceback；
4. 真实 HTTP 上传：multipart POST → 文件落盘 + parsed/*.md 生成 + /files 列得出来；
   重名不覆盖、非白名单扩展名跳过、路径穿越（../../etc/passwd）被 safe_name 拍平；
5. 补充要求写进 notes.md；删除会同时清掉解析结果。

不依赖网络、不依赖第三方包。
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "production" / "upload_box"))

import extract_tables  # noqa: E402
import server  # noqa: E402

WML = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
DOC_XML_TMPL = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<w:document xmlns:w="{WML}"><w:body>{{BODY}}</w:body></w:document>'
)


def make_docx(path: Path, paragraphs=(), table=None) -> Path:
    """按最小 OOXML 拼一个能开、能解析的 .docx。"""
    body = "".join(f"<w:p><w:r><w:t>{t}</w:t></w:r></w:p>" for t in paragraphs)
    if table:
        rows = "".join(
            "<w:tr>" + "".join(f"<w:tc><w:p><w:r><w:t>{c}</w:t></w:r></w:p></w:tc>" for c in row) + "</w:tr>"
            for row in table
        )
        body += f"<w:tbl>{rows}</w:tbl>"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", DOC_XML_TMPL.format(BODY=body))
    return path


def make_xlsx(path: Path, cells: dict[str, str]) -> Path:
    """cells 形如 {"A1": "时长", "B1": "3 分钟"}，全部走 sharedStrings。"""
    strings = list(dict.fromkeys(cells.values()))
    si = "".join(f"<si><t>{s}</t></si>" for s in strings)
    row_xml: dict[int, list[str]] = {}
    for ref, val in sorted(cells.items()):
        col = "".join(ch for ch in ref if ch.isalpha())
        row = int("".join(ch for ch in ref if ch.isdigit()))
        idx = strings.index(val)
        row_xml.setdefault(row, []).append(f'<c r="{col}{row}" t="s"><v>{idx}</v></c>')
    sheet = "".join(
        f'<row r="{r}">' + "".join(row_xml[r]) + "</row>" for r in sorted(row_xml)
    )
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/sharedStrings.xml", f'<?xml version="1.0"?><sst {ns}>{si}</sst>')
        z.writestr(
            "xl/worksheets/sheet1.xml",
            f'<?xml version="1.0"?><worksheet {ns}><sheetData>{sheet}</sheetData></worksheet>',
        )
        z.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0"?>'
            f'<workbook {ns} '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="要求" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
        )
    return path


class ExtractTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_docx_table_becomes_markdown(self):
        docx = make_docx(
            self.dir / "要求.docx",
            paragraphs=["三分钟悬疑解说 · 交付要求"],
            table=[
                ["栏目", "要求", "备注"],
                ["标题", "披萨盒里的凶手", "三个备选"],
                ["时长", "180 s ± 5", "竖版另说"],
                ["台词", "他|也是爸爸", "含竖线要转义"],
            ],
        )
        res = extract_tables.extract(docx)
        self.assertEqual(res["error"], "")
        self.assertEqual(res["n_tables"], 1)
        md = res["markdown"]
        self.assertIn("三分钟悬疑解说 · 交付要求", md)
        self.assertIn("| 栏目 | 要求 | 备注 |", md)
        self.assertIn("披萨盒里的凶手", md)
        self.assertIn(r"他\|也是爸爸", md)  # 竖线转义，表格不能塌
        self.assertIn("180 s ± 5", md)
        blocks = res["blocks"]
        self.assertEqual(blocks[0]["kind"], "para")
        self.assertEqual(len(blocks[1]["rows"]), 4)

    def test_xlsx_sparse_columns_align(self):
        xlsx = make_xlsx(
            self.dir / "分镜.xlsx",
            {"A1": "镜", "C1": "口播", "E1": "音效", "A2": "N01", "C2": "第一句", "E2": "低频嗡鸣"},
        )
        res = extract_tables.extract(xlsx)
        self.assertEqual(res["error"], "")
        rows = res["blocks"][0]["rows"]
        self.assertEqual(len(rows[0]), 5)          # A..E 补齐
        self.assertEqual(rows[1][1], "")           # 空列没串位
        self.assertEqual(rows[1][2], "第一句")
        self.assertIn("工作表：要求", res["markdown"])

    def test_legacy_office_formats_say_why(self):
        fake = self.dir / "老.doc"
        fake.write_bytes(b"\xd0\xcf\x11\xe0 not a zip")
        res = extract_tables.extract(fake)
        self.assertIn("另存为", res["error"])
        self.assertEqual(res["markdown"], "")

    def test_unknown_suffix_is_not_an_error_for_images(self):
        png = self.dir / "参考图.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n")
        res = extract_tables.extract(png)
        self.assertIn("已原样存好", res["error"])

    def test_nested_table_is_unwrapped(self):
        """Word 里最常见的坑：外层一个 1×1 的框，真表格套在里面（用户的开工表就是这么排的）。"""
        outer = self.dir / "套娃.docx"
        inner_rows = "".join(
            "<w:tr>" + "".join(f"<w:tc><w:p><w:r><w:t>{c}</w:t></w:r></w:p></w:tc>" for c in row) + "</w:tr>"
            for row in [["时间轴", "口播"], ["0-5秒", "第一句"], ["5-20秒", "第二句"]]
        )
        body = (
            "<w:p><w:r><w:t>详细脚本（表格形式）</w:t></w:r></w:p>"
            # 外层 1×1 的框：一个空段落 + 一个真正套在单元格里的 <w:tbl>
            f"<w:tbl><w:tr><w:tc><w:p><w:r><w:t></w:t></w:r></w:p><w:tbl>{inner_rows}</w:tbl>"
            "</w:tc></w:tr></w:tbl>"
        )
        with zipfile.ZipFile(outer, "w") as z:
            z.writestr("word/document.xml", DOC_XML_TMPL.format(BODY=body))
        res = extract_tables.extract(outer)
        self.assertEqual(res["error"], "")
        tables = [b for b in res["blocks"] if b["kind"] == "table"]
        self.assertEqual(len(tables), 1)                 # 包装框不该变成一张"表"
        self.assertEqual(len(tables[0]["rows"]), 3)      # 内层 3 行
        self.assertEqual(tables[0]["rows"][1], ["0-5秒", "第一句"])
        self.assertEqual(res["n_rows"], 3)
        self.assertIn("| 时间轴 | 口播 |", res["markdown"])

    def test_shipped_sample_still_parses(self):
        """仓库里那份示例表格是文档也是回归样本：解析不出来就说明抽取器退步了。"""
        res = extract_tables.extract(ROOT / "production" / "upload_box" / "sample_需求示例.docx")
        self.assertEqual(res["error"], "")
        self.assertEqual(res["n_tables"], 1)
        self.assertEqual(res["n_rows"], 5)
        self.assertIn("| 栏目 | 要求 | 备注 |", res["markdown"])

    def test_json_output_is_stable(self):
        docx = make_docx(self.dir / "a.docx", paragraphs=["hi"], table=[["x", "y"], ["1", "2"]])
        payload = json.dumps(extract_tables.extract(docx), ensure_ascii=False)
        self.assertIn('"n_rows": 2', payload)


class _Multipart:
    @staticmethod
    def build(fields: dict[str, str], files: list[tuple[str, str, bytes]], boundary="BOUND") -> bytes:
        buf = bytearray()
        for key, val in fields.items():
            buf += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{val}\r\n".encode()
        for name, filename, data in files:
            buf += (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; "
                f'filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'
            ).encode()
            buf += data + b"\r\n"
        buf += f"--{boundary}--\r\n".encode()
        return bytes(buf)


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        server.use_inbox(Path(cls.tmp.name) / "inbox")
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.tmp.cleanup()

    def post(self, path: str, data: bytes | None = None, ctype: str = "application/json"):
        req = urllib.request.Request(self.base + path, data=data if data is not None else b"", method="POST")
        if data is not None:
            req.add_header("Content-Type", ctype)
        try:
            with urllib.request.urlopen(req, data=data if data is not None else b"") as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def test_upload_docx_lands_and_gets_parsed(self):
        with tempfile.TemporaryDirectory() as td:
            docx = make_docx(Path(td) / "要求.docx", table=[["项", "值"], ["时长", "180 s"]])
            body = _Multipart.build({}, [("file", "要求.docx", docx.read_bytes())])
            code, raw = self.post("/upload", body, "multipart/form-data; boundary=BOUND")
        payload = json.loads(raw)
        self.assertEqual(code, 200, payload)
        self.assertEqual(payload["parsed"], 1)
        self.assertEqual(payload["names"], ["要求.docx"])
        saved = server.INBOX / "要求.docx"
        self.assertTrue(saved.exists())
        md = (server.EXTRACTED / "要求.md").read_text(encoding="utf-8")
        self.assertIn("| 项 | 值 |", md)
        files = json.loads(self.post_get("/files")[1])
        row = next(x for x in files if x["name"] == "要求.docx")
        self.assertIn("已解析出 1 个表格", row["note"])
        self.assertEqual(row["view"], "/view/要求")

    def post_get(self, path: str):
        with urllib.request.urlopen(self.base + path) as resp:
            return resp.status, resp.read()

    def test_duplicate_names_never_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            docx = make_docx(Path(td) / "dup.docx", table=[["a"], ["1"]])
            data = docx.read_bytes()
            for _ in range(2):
                self.post("/upload", _Multipart.build({}, [("file", "dup.docx", data)]),
                          "multipart/form-data; boundary=BOUND")
        names = {p.name for p in server.INBOX.glob("dup*")}
        self.assertEqual(names, {"dup.docx", "dup-1.docx"})

    def test_traversal_and_bad_suffix_are_handled(self):
        with tempfile.TemporaryDirectory() as td:
            junk = Path(td) / "x.txt"
            junk.write_text("hi", encoding="utf-8")
            body = _Multipart.build({}, [("file", "../../../../etc/passwd.exe", junk.read_bytes())])
            code, raw = self.post("/upload", body, "multipart/form-data; boundary=BOUND")
        payload = json.loads(raw)
        self.assertEqual(code, 200)
        self.assertEqual(payload["names"], [])
        self.assertIn("passwd.exe", payload["skipped"][0])
        self.assertIn("白名单", payload["skipped"][0])
        self.assertFalse((server.INBOX / "passwd.exe").exists())
        self.assertFalse(Path("/etc/passwd.exe").exists())  # 穿越没生效
        # 中文名 + 空格 + 竖线：存下来的是安全名，且解析结果能对上
        with tempfile.TemporaryDirectory() as td:
            docx = make_docx(Path(td) / "n.docx", table=[["a"], ["1"]])
            body = _Multipart.build({}, [("file", "第 2 版|需求.docx", docx.read_bytes())])
            code, raw = self.post("/upload", body, "multipart/form-data; boundary=BOUND")
        names = json.loads(raw)["names"]
        self.assertEqual(names, ["第_2_版_需求.docx"])
        self.assertTrue((server.INBOX / "第_2_版_需求.docx").exists())
        self.assertIn("| a |", (server.EXTRACTED / "第_2_版_需求.md").read_text(encoding="utf-8"))

    def test_note_appends_and_delete_cleans_parse(self):
        code, _ = self.post("/note", json.dumps({"text": "竖版 9:16，标题要三个备选"}).encode())
        self.assertEqual(code, 200)
        self.assertIn("竖版 9:16", (server.INBOX / "notes.md").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            docx = make_docx(Path(td) / "todelete.docx", table=[["a"], ["2"]])
            self.post("/upload", _Multipart.build({}, [("file", "todelete.docx", docx.read_bytes())]),
                      "multipart/form-data; boundary=BOUND")
        self.assertTrue((server.EXTRACTED / "todelete.md").exists())
        code, raw = self.post("/delete?name=todelete.docx")
        self.assertEqual(code, 200)
        self.assertFalse((server.INBOX / "todelete.docx").exists())
        self.assertFalse((server.EXTRACTED / "todelete.md").exists())

    def test_reparse_refreshes_existing_file(self):
        """解析器改进后不必重新上传：/reparse 拿原件重跑。"""
        with tempfile.TemporaryDirectory() as td:
            docx = make_docx(Path(td) / "again.docx", table=[["a"], ["1"]])
            self.post("/upload", _Multipart.build({}, [("file", "again.docx", docx.read_bytes())]),
                      "multipart/form-data; boundary=BOUND")
        (server.EXTRACTED / "again.md").write_text("旧的、错的", encoding="utf-8")
        code, raw = self.post("/reparse?name=again.docx")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(raw)["n_tables"], 1)
        self.assertIn("| a |", (server.EXTRACTED / "again.md").read_text(encoding="utf-8"))
        code, raw = self.post("/reparse?name=" + urllib.parse.quote("不存在.docx"))
        self.assertEqual(code, 404)

    def test_page_serves_and_oversize_is_rejected(self):
        code, raw = self.post_get("/")
        self.assertEqual(code, 200)
        self.assertIn("把文件拖到这里", raw.decode())
        big = _Multipart.build({}, [("file", "big.docx", b"\0" * (server.MAX_BYTES + 10))])
        code, raw = self.post("/upload", big, "multipart/form-data; boundary=BOUND")
        self.assertEqual(code, 413)
        self.assertIn("80 MB", json.loads(raw)["error"])

    def test_safe_name_keeps_chinese(self):
        self.assertEqual(server.safe_name("第 3 版·需求.docx"), "第_3_版_需求.docx")
        self.assertEqual(server.safe_name("a/../b.txt"), "b.txt")


if __name__ == "__main__":
    unittest.main()
