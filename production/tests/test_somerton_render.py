import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from production.somerton import render
from production.somerton.render import detect_matte_bands, letterbox_crop_filter


class SomertonRenderTests(unittest.TestCase):
    def test_s24_letterbox_detector_finds_sharp_paired_mattes(self):
        image = Image.new("RGB", (640, 360), "black")
        ImageDraw.Draw(image).rectangle((0, 50, 639, 309), fill=(55, 85, 105))
        self.assertEqual(detect_matte_bands(image), (50, 50))

    def test_source_detector_requires_repeated_samples_and_cleans_temporary_frames(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "S24.mp4"
            source.touch()

            def fake_ffmpeg(command):
                image = Image.new("RGB", (640, 360), "black")
                ImageDraw.Draw(image).rectangle((0, 50, 639, 309), fill=(55, 85, 105))
                image.save(command[-1])

            with patch.object(render, "run", side_effect=fake_ffmpeg) as mocked:
                bands = render.detect_source_letterbox_bands(
                    source, {"id": "S24"}, {"duration_seconds": 7.0})
            self.assertEqual(len(mocked.call_args_list), 3)
            self.assertEqual(bands, [(50, 50)] * 3)
            self.assertFalse(list(Path(temp_dir).glob("*.png")))

    def test_dark_gradient_is_not_misclassified_as_a_letterbox(self):
        image = Image.new("RGB", (640, 360), "black")
        draw = ImageDraw.Draw(image)
        for y in range(image.height):
            distance = min(y, image.height - 1 - y)
            level = min(58, int(distance * 0.22))
            draw.line((0, y, image.width - 1, y), fill=(level, level, level))
        self.assertIsNone(detect_matte_bands(image))

    def test_s24_crop_uses_detected_bar_size_and_centers_16_9_active_area(self):
        bands = [(50, 50), (49, 50), (50, 49)]
        crop = letterbox_crop_filter({"id": "S24"}, {"width": 1280, "height": 720}, bands)
        self.assertEqual(crop, "crop=916:516:182:102")

    def test_regenerated_full_frame_s24_without_detected_bars_is_not_cropped(self):
        self.assertIsNone(letterbox_crop_filter({"id": "S24"}, {"width": 1280, "height": 720}, []))

    def test_other_shots_keep_their_full_generated_frame(self):
        for shot_id in ("S23", "S25", "S29"):
            with self.subTest(shot=shot_id):
                self.assertIsNone(letterbox_crop_filter(
                    {"id": shot_id}, {"width": 1280, "height": 720}, [(50, 50)] * 3))


if __name__ == "__main__":
    unittest.main()
