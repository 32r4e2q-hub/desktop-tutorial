#!/usr/bin/env python3
"""Smoke tests for the self-contained editor and distributable package."""
from pathlib import Path
import base64,re,unittest,zipfile
from PIL import Image

HERE=Path(__file__).resolve().parent
class TemplateTests(unittest.TestCase):
    def test_cover_dimensions(self):
        with Image.open(HERE/'第一期_西口彰_封面.png') as im:self.assertEqual(im.size,(1080,1440))
    def test_editor_self_contained(self):
        s=(HERE/'封面模板_可编辑.html').read_text(encoding='utf8')
        self.assertNotIn('__IMAGE_DATA__',s);self.assertNotIn('__FONT_DATA__',s)
        for name in ['id="episode"','id="line1"','id="line2"','id="screenshot"','canvas.toBlob','resetShot()','逃亡78天的西口彰','却被女孩一眼认出']:
            self.assertIn(name,s)
        image=re.search(r'data:image/jpeg;base64,([A-Za-z0-9+/=]+)',s);font=re.search(r'data:font/woff2;base64,([A-Za-z0-9+/=]+)',s)
        self.assertTrue(image and font);self.assertTrue(base64.b64decode(image[1]).startswith(b'\xff\xd8'));self.assertTrue(base64.b64decode(font[1]).startswith(b'wOF2'))
    def test_zip_has_standalone_editor_and_cover(self):
        with zipfile.ZipFile(HERE/'迷案解码人_封面模板.zip') as z:
            self.assertEqual(set(z.namelist()),{'封面模板_可编辑.html','第一期_西口彰_封面.png','第一期_视频截图示例.jpg','使用说明.txt','OFL.txt'})
            self.assertIsNone(z.testzip())
            self.assertEqual(z.read('封面模板_可编辑.html'),(HERE/'封面模板_可编辑.html').read_bytes())
if __name__=='__main__':unittest.main()
