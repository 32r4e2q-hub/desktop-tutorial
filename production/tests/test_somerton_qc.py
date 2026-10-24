import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from production.somerton import qc


class SomertonOcrTests(unittest.TestCase):
    def test_ocr_parser_keeps_confident_text_and_ignores_low_confidence_noise(self):
        tsv = (
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
            "5\t1\t1\t1\t1\t1\t10\t10\t80\t20\t91.3\tTAMAN\n"
            "5\t1\t1\t1\t1\t2\t90\t10\t30\t20\t44.0\tnoise\n"
            "5\t1\t1\t1\t1\t3\t130\t10\t10\t20\t80.0\tA\n"
        )
        completed = subprocess.CompletedProcess([], 0, stdout=tsv, stderr="")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "ocr-temp.png"
            with patch.object(qc.subprocess, "run", return_value=completed):
                words = qc.ocr_words(Image.new("RGB", (64, 32), "white"), temp_path)
        self.assertEqual(words, [{"token": "TAMAN", "confidence": 91.3}, {"token": "A", "confidence": 80.0}])
        self.assertFalse(temp_path.exists())

    def test_final_ocr_excludes_subtitle_band_and_approved_title_shots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            frame = Path(temp_dir) / "frame.jpg"
            Image.new("RGB", (100, 100), "white").save(frame)
            samples = [
                {"id": "S01", "frame": str(frame), "time_seconds": 3.5},
                {"id": "S14", "frame": str(frame), "time_seconds": 88.0},
                {"id": "S29", "frame": str(frame), "time_seconds": 177.0},
            ]
            with patch.object(qc.shutil, "which", return_value="/usr/bin/tesseract"), \
                 patch.object(qc, "find_file", return_value=None), \
                 patch.object(qc, "ocr_words", return_value=[]) as ocr:
                report = qc.scan_unapproved_text(Path(temp_dir), samples, Path(temp_dir) / "ocr")
        self.assertTrue(report["available"])
        self.assertEqual(report["final_frames_scanned"], 2)
        self.assertEqual(ocr.call_count, 2)
        self.assertTrue(all(call.args[0].size == (100, 85) for call in ocr.call_args_list))

    def test_only_s14_tamam_shud_words_are_allowlisted(self):
        words = [
            {"token": "Tamam", "confidence": 90.0},
            {"token": "Shud", "confidence": 91.0},
            {"token": "LUGGAGE", "confidence": 88.0},
        ]
        self.assertEqual(qc.unapproved_ocr_words("S14", words), [words[2]])
        self.assertEqual(qc.unapproved_ocr_words("S10", words), words)


if __name__ == "__main__":
    unittest.main()
