from array import array
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from production.somerton import qc
from production.somerton.build_audio import voice_tempo_factor


class SomertonOcrTests(unittest.TestCase):
    def test_motion_sample_times_are_evenly_spaced_inside_shot(self):
        shot = {"start": 125, "duration": 8}
        times = qc.motion_sample_times(shot)
        self.assertEqual(len(times), 9)
        self.assertEqual(times[0], 125.0)
        self.assertAlmostEqual(times[-1], 125 + 8 * 8 / 9, delta=0.001)
        steps = [times[index + 1] - times[index] for index in range(8)]
        self.assertTrue(all(abs(step - 8 / 9) < 0.002 for step in steps))

    def test_letterbox_scan_requires_persistent_paired_black_edges(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            samples = []
            for index in range(9):
                frame = Image.new("RGB", (640, 360), "black")
                draw = ImageDraw.Draw(frame)
                draw.rectangle((0, 72, 639, 287), fill=(55, 85, 105))
                path = root / f"barred-{index}.jpg"
                frame.save(path, quality=95)
                samples.append({"id": "S24", "frame": str(path), "time_seconds": index / 30})
            report = qc.scan_final_letterbox_bars(samples)
        self.assertEqual(report["finding_count"], 1)
        self.assertEqual(report["findings"][0]["shot"], "S24")
        self.assertGreaterEqual(report["findings"][0]["median_top_bar_px"], 70)
        self.assertGreaterEqual(report["findings"][0]["median_bottom_bar_px"], 70)

    def test_letterbox_scan_catches_bars_present_in_half_of_samples(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            samples = []
            for index in range(9):
                frame = Image.new("RGB", (640, 360), (55, 85, 105))
                if index < 5:
                    draw = ImageDraw.Draw(frame)
                    draw.rectangle((0, 0, 639, 71), fill="black")
                    draw.rectangle((0, 288, 639, 359), fill="black")
                path = root / f"mixed-{index}.jpg"
                frame.save(path, quality=95)
                samples.append({"id": "S24", "frame": str(path), "time_seconds": index / 30})
            report = qc.scan_final_letterbox_bars(samples)
        self.assertEqual(report["finding_count"], 1)
        self.assertEqual(report["findings"][0]["paired_bar_frames"], 5)

    def test_letterbox_scan_ignores_smoothly_fading_dark_end_card_edges(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            samples = []
            for index in range(9):
                frame = Image.new("RGB", (640, 360), "black")
                draw = ImageDraw.Draw(frame)
                for y in range(frame.height):
                    distance = min(y, frame.height - 1 - y)
                    level = min(58, int(distance * 0.22))
                    draw.line((0, y, frame.width - 1, y), fill=(level, level, level))
                path = root / f"gradient-{index}.jpg"
                frame.save(path, quality=95)
                samples.append({"id": "S29", "frame": str(path), "time_seconds": index / 30})
            report = qc.scan_final_letterbox_bars(samples)
        self.assertEqual(report["finding_count"], 0)

    def test_motion_sample_targets_map_to_exact_source_frame_times(self):
        shot = {"id": "S01", "start": 0.0, "duration": 5.0}
        positions = qc.motion_sample_frame_positions(shot, 9)
        self.assertEqual([index for index, _ in positions], [0, 17, 33, 50, 67, 83, 100, 117, 133])
        self.assertEqual(positions[1][1], 0.567)
        self.assertEqual(positions[-1][1], 4.433)

    def test_final_motion_sheet_is_a_labeled_three_by_three_grid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            frames = []
            colors = [(index * 20, 100, 160) for index in range(9)]
            for index, color in enumerate(colors):
                frame = root / f"frame-{index}.jpg"
                Image.new("RGB", (640, 360), color).save(frame)
                frames.append(frame)
            output = root / "S21.jpg"
            qc.assemble_final_motion_sheet("S21", [float(i) for i in range(9)], frames, output)
            with Image.open(output) as sheet:
                self.assertEqual(sheet.size, (1278, 801))

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
        self.assertEqual(words, [{"token": "TAMAN", "confidence": 91.3}])
        self.assertFalse(temp_path.exists())

    def test_subtitle_ocr_can_keep_partial_low_confidence_cjk(self):
        tsv = (
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
            "5\t1\t1\t1\t1\t1\t10\t10\t20\t20\t68.0\t一\n"
            "5\t1\t1\t1\t1\t2\t30\t10\t20\t20\t52.0\t九\n"
        )
        completed = subprocess.CompletedProcess([], 0, stdout=tsv, stderr="")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch.object(qc.subprocess, "run", return_value=completed):
                strict = qc.ocr_words(Image.new("RGB", (64, 32), "white"), root / "strict.png")
                subtitle = qc.ocr_words(Image.new("RGB", (64, 32), "white"), root / "subtitle.png",
                                        psm=6, allow_partial_cjk=True)
        self.assertEqual(strict, [])
        self.assertEqual([word["token"] for word in subtitle], ["一", "九"])

    def test_ocr_token_filter_keeps_confident_words_and_multidigit_marks(self):
        self.assertTrue(qc.plausible_ocr_token("LUGGAGE", 80.0))
        self.assertTrue(qc.plausible_ocr_token("19", 95.0))
        self.assertTrue(qc.plausible_ocr_token("案卷", 75.0))
        self.assertFalse(qc.plausible_ocr_token("WwW.", 46.4))
        self.assertFalse(qc.plausible_ocr_token("A", 99.0))
        self.assertFalse(qc.plausible_ocr_token("一", 99.0))

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
        self.assertEqual(report["final_frames_scanned"], 1)
        self.assertEqual(ocr.call_count, 1)
        self.assertEqual(ocr.call_args.args[0].size, (100, 80))

    def test_ocr_scans_explicit_additional_final_motion_frames(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            frame = root / "motion.jpg"
            Image.new("RGB", (100, 100), "white").save(frame)
            midpoint_samples = [{"id": "S01", "frame": str(frame), "time_seconds": 2.5}]
            motion_samples = [{"id": "S01", "frame": str(frame), "time_seconds": 1.0},
                              {"id": "S01", "frame": str(frame), "time_seconds": 4.0}]
            with patch.object(qc.shutil, "which", return_value="/usr/bin/tesseract"), \
                 patch.object(qc, "find_file", return_value=None), \
                 patch.object(qc, "ocr_words", return_value=[]) as ocr:
                report = qc.scan_unapproved_text(Path(temp_dir), midpoint_samples,
                                                 Path(temp_dir) / "ocr", motion_samples)
        self.assertEqual(report["final_frames_scanned"], 2)
        self.assertEqual(ocr.call_count, 2)

    def test_narration_timing_receipt_must_match_reconstruction(self):
        chapter = {"id": "N01", "start": 0.0, "duration": 10.0,
                   "source_seconds": 3.2, "tempo_factor": 1.0,
                   "target_chars_per_second": 4.3, "inserted_pause_seconds": 0.0,
                   "inserted_pause_at_chapter_seconds": None, "speech_seconds": 6.0,
                   "shot_ids": ["S01", "S02"], "characters": 43}
        shot = {"id": "S01", "narration_id": "N01", "text": "海滩旁白。",
                "start": 0.0, "duration": 5.0, "source_seconds": 1.9,
                "natural_clip_seconds": 1.8, "natural_speech_seconds": 1.69,
                "spoken_seconds": 1.69, "tempo_factor": 1.0,
                "speech_start": 0.03, "speech_end": 1.72,
                "characters": 5, "target_chars_per_second": 1.0}
        header = {"voice_id": "voice-01", "alignment": "one-clip-one-shot-one-caption",
                  "slowdown_allowed": False, "max_speedup_factor": 1.55,
                  "duration_seconds": 180.0}
        actual = {**header, "chapters": [chapter.copy()], "shots": [shot.copy()]}
        expected = {**header, "chapters": [chapter.copy()], "shots": [shot.copy()]}
        self.assertEqual(qc.narration_timing_matches(actual, expected), (True, []))
        expected["chapters"][0]["tempo_factor"] = 0.8
        matches, mismatches = qc.narration_timing_matches(actual, expected)
        self.assertFalse(matches)
        self.assertEqual(mismatches, ["chapters1:tempo_factor"])

    def test_narration_pacing_never_slowed_and_caps_acceleration(self):
        self.assertEqual(voice_tempo_factor(3.4, 4.0), 1.0)
        self.assertAlmostEqual(voice_tempo_factor(4.4, 4.0), 1.1)
        with self.assertRaisesRegex(RuntimeError, "Shorten/regenerate"):
            voice_tempo_factor(6.4, 4.0, max_speedup=1.55)

    def test_caption_voice_activity_flags_cues_without_narration_energy(self):
        voiced_then_silent = array("f", [0.1] * 48000 + [0.0] * 48000).tobytes()
        cues = [{"start": 0.0, "end": 1.0, "text": "有旁白"},
                {"start": 1.0, "end": 2.0, "text": "静音"}]
        with patch.object(qc.subprocess, "check_output", return_value=voiced_then_silent):
            report = qc.analyze_caption_voice_activity(Path("voiceover.wav"), cues)
        self.assertEqual(report["cue_count"], 2)
        self.assertEqual(report["weak_cue_count"], 1)
        self.assertEqual(report["weak_cues"][0]["cue"], 2)

    def test_visible_text_normalizer_keeps_chinese_and_latin_letters(self):
        self.assertEqual(qc.normalize_visible_text("Tamam Shud，塔玛姆·舒德！"), "tamamshud塔玛姆舒德")

    def test_rendered_subtitle_ocr_compares_sampled_burned_in_caption(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            frame = root / "frame.jpg"
            Image.new("RGB", (100, 100), "white").save(frame)
            samples = [{"id": "S01", "frame": str(frame), "time_seconds": 1.5}]
            cues = [{"start": 1.0, "end": 2.0, "text": "索马顿海滩"}]
            with patch.object(qc.shutil, "which", return_value="/usr/bin/tesseract"), \
                 patch.object(qc, "ocr_words", return_value=[{"token": "索马顿海滩", "confidence": 90.0}]) as ocr:
                report = qc.scan_rendered_subtitles(samples, cues, root / "subtitle-ocr")
        self.assertTrue(report["available"])
        self.assertEqual(report["checked_frames"], 1)
        self.assertEqual(report["finding_count"], 0)
        self.assertEqual(ocr.call_args.kwargs["psm"], 6)
        self.assertTrue(ocr.call_args.kwargs["allow_partial_cjk"])
        self.assertEqual(ocr.call_args.args[0].size, (200, 48))

    def test_rendered_subtitle_ocr_skips_cue_boundary_samples(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            frame = root / "frame.jpg"
            Image.new("RGB", (100, 100), "white").save(frame)
            samples = [{"id": "S01", "frame": str(frame), "time_seconds": 1.0}]
            cues = [{"start": 1.0, "end": 2.0, "text": "索马顿海滩"}]
            with patch.object(qc.shutil, "which", return_value="/usr/bin/tesseract"), \
                 patch.object(qc, "ocr_words", return_value=[]) as ocr:
                report = qc.scan_rendered_subtitles(samples, cues, root / "subtitle-ocr")
        self.assertEqual(report["skipped_near_cue_boundaries"], 1)
        self.assertEqual(ocr.call_count, 0)

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
