import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import assemble as A
import finish
import recover_assets as recovery


class TimelineTests(unittest.TestCase):
    def test_missing_clips_fail_instead_of_exporting_partial_film(self):
        with patch.object(A.os.path, 'exists', return_value=False):
            with self.assertRaisesRegex(RuntimeError, 'Missing/invalid clips'):
                A.build_timeline()

    def test_trims_and_block_continuity(self):
        shots = {'shots': [
            {'id': 'S22', 'vo': 'N07', 'seconds': 7, 'use': [1.5, 5.6]},
            {'id': 'S23', 'vo': 'N08', 'seconds': 9},
        ]}
        with patch.object(A, 'SHOTS', shots), patch.object(A, 'NARRATION', {'N07': ['a'], 'N08': ['b']}), \
             patch.object(A.os.path, 'exists', return_value=True), patch.object(A.os.path, 'getsize', return_value=2000), \
             patch.object(A, 'clip_frames', return_value=(240, 24)), patch.object(A, 'probe_duration', return_value=10):
            timeline, blocks, total, _ = A.build_timeline()
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[0]['offset'], 36)
        self.assertAlmostEqual(timeline[0]['natural'], 4.1)
        self.assertAlmostEqual(timeline[1]['start'], timeline[0]['dur'])
        self.assertAlmostEqual(total, sum(b['dur'] for b in blocks))

    def test_zero_frame_clip_is_rejected(self):
        with patch.object(A.os.path, 'exists', return_value=True), \
             patch.object(A.os.path, 'getsize', return_value=2000), patch.object(A, 'clip_frames', return_value=(0, 24)):
            with self.assertRaisesRegex(RuntimeError, 'Missing/invalid clips'):
                A.build_timeline()

    def test_decode_error_is_not_silently_zero_duration(self):
        result = MagicMock(returncode=1, stderr='broken media')
        with patch.object(A.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'Cannot decode'):
                A.probe_duration('bad.mp3')


class RenderTests(unittest.TestCase):
    @unittest.skipUnless((HERE / 'assets/fonts/NotoSansCJKsc-Regular.otf').exists(), 'run recover_assets.py for CJK fonts')
    def test_every_subtitle_fits_safe_width(self):
        for lines in A.NARRATION.values():
            for line in lines:
                size = A.subtitle_size(line)
                rgb, _ = A.render_text(line, size, False, (245, 240, 230), 3, (10, 8, 6))
                self.assertLessEqual(rgb.shape[1], int(A.W * 0.84), line)
                self.assertGreaterEqual(size, 40, line)

    def test_flow_interpolation_endpoints(self):
        rng = np.random.default_rng(42)
        a = rng.integers(0, 256, (64, 64, 3), dtype=np.uint8)
        b = np.roll(a, 2, axis=1)
        self.assertTrue(np.array_equal(A.flow_interp(a, b, 0.0), a))
        self.assertTrue(np.array_equal(A.flow_interp(a, b, 1.0), b))

    def test_time_remap_never_reverses_and_respects_trim(self):
        class Reader:
            def __init__(self):
                self.indices = []
            def get(self, path, index):
                self.indices.append(index)
                return np.zeros((8, 8, 3), dtype=np.uint8)
        reader = Reader()
        shot = {'id': 'S22', 'vo': 'N07', 'path': 'clip', 'start': 0, 'dur': 6.5,
                'natural': 5.6, 'fps': 24, 'offset': 36}
        block = {'vo': 'N07', 'start': 0, 'dur': 6.5, 'vo_dur': 5}
        with patch.object(A, 'post', side_effect=lambda img, *a, **k: img), \
             patch.object(A, 'fit_cover', side_effect=lambda img, *a, **k: img), \
             patch.object(A, 'flow_interp', side_effect=lambda a, b, *args, **kw: a), \
             patch.object(A, 'subtitle_for', return_value=(None, 0)):
            for t in np.linspace(0.1, 6.4, 30):
                A.compose(float(t), [shot], [block], 6.5, reader, np.random.default_rng(0))
        self.assertGreaterEqual(min(reader.indices), 36)
        self.assertLessEqual(max(reader.indices), 36 + 134)
        # Adjacent interpolation pairs overlap but shot time must not run backwards.
        self.assertTrue(all(b >= a - 1 for a, b in zip(reader.indices, reader.indices[1:])))

    def test_encoder_failure_raises(self):
        process = MagicMock()
        process.wait.return_value = 1
        with patch.object(A.subprocess, 'Popen', return_value=process):
            with self.assertRaisesRegex(RuntimeError, 'Segment encoding failed'):
                A.render_range((0, 0, 'failed.mp4', [], [], 0))


class DeliveryTests(unittest.TestCase):
    def test_audio_smoother_matches_original_zero_padded_window(self):
        from scipy.ndimage import uniform_filter1d
        x = np.random.default_rng(1).random(1000)
        for size in [6, 15, 80]:
            np.testing.assert_allclose(uniform_filter1d(x, size, mode='constant'),
                                       np.convolve(x, np.ones(size) / size, mode='same'), atol=1e-12)

    def test_subtitle_millisecond_carry(self):
        self.assertEqual(finish.stamp(59.9996), '00:01:00,000')
        self.assertEqual(finish.stamp(3661.001), '01:01:01,001')

    def test_narration_check_detects_actual_alignment(self):
        sr = 8000
        rng = np.random.default_rng(3)
        pcm = (rng.standard_normal(sr * 2) * 1000).astype(np.int16)
        mixed = np.zeros(sr * 4, np.int16)
        offset = round(0.7 * sr)
        mixed[offset:offset + len(pcm)] = pcm
        with patch.object(finish.wavfile, 'read', return_value=(sr, mixed)), \
             patch.object(finish.subprocess, 'check_output', return_value=pcm.tobytes()):
            report = finish.narration_alignment('file', [{'vo': 'N01', 'start': 0}])
        self.assertTrue(report[0]['passed'])
        self.assertLess(abs(report[0]['offset_error_seconds']), 1 / sr)

    def test_narration_check_rejects_wrong_offset(self):
        sr = 8000
        pcm = (np.random.default_rng(3).standard_normal(sr * 2) * 1000).astype(np.int16)
        mixed = np.zeros(sr * 4, np.int16)
        offset = round(0.9 * sr)
        mixed[offset:offset + len(pcm)] = pcm
        with patch.object(finish.wavfile, 'read', return_value=(sr, mixed)), \
             patch.object(finish.subprocess, 'check_output', return_value=pcm.tobytes()):
            report = finish.narration_alignment('file', [{'vo': 'N01', 'start': 0}])
        self.assertFalse(report[0]['passed'])


class RecoveryTests(unittest.TestCase):
    def test_verified_download_and_cache(self):
        data = b'existing-video-content'
        item = {'path': 'ripper/clips/S01.mp4', 'sha': recovery.git_hash(data), 'size': len(data)}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(recovery, 'ROOT', root), patch.object(recovery, 'CACHE', root / '.cache'), \
                 patch.object(recovery.subprocess, 'check_output', return_value=data) as download:
                recovery.restore(item, 'owner/repo')
                recovery.restore(item, 'owner/repo')
                self.assertEqual(download.call_count, 1)
                self.assertEqual((root / item['path']).read_bytes(), data)

    def test_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(recovery, 'ROOT', Path(temp)), patch.object(recovery, 'CACHE', Path(temp) / '.cache'), \
                 patch.object(recovery.subprocess, 'check_output', return_value=b'wrong'):
                with self.assertRaisesRegex(RuntimeError, 'verification failed'):
                    recovery.restore({'path': 'ripper/clips/S01.mp4', 'size': 5, 'sha': '0' * 40}, 'owner/repo')

    def test_unsafe_path_is_rejected(self):
        for name in ['../escape.mp4', '/tmp/escape.mp4', 'other/file.mp4']:
            with self.assertRaises(ValueError):
                recovery.restore({'path': name, 'size': 0, 'sha': '0' * 40}, 'owner/repo')


if __name__ == '__main__':
    unittest.main()
