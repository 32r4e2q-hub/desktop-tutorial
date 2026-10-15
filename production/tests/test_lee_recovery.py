"""Offline regression tests: task recovery and bounded cloud submission."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

PATH = Path(__file__).resolve().parents[1] / 'lee_hyung_ho1991/generate.py'
spec = importlib.util.spec_from_file_location('lee_generate', PATH)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class RecoveryTests(unittest.TestCase):
    def test_resume_requires_same_payload_and_live_task(self):
        row = dict(status='queued', task_id='existing', request_hash='abc')
        self.assertEqual(g.resumable_task(row, 'abc'), 'existing')
        self.assertIsNone(g.resumable_task(row, 'changed'))
        self.assertIsNone(g.resumable_task(dict(row, status='failed'), 'abc'))

    def test_queue_is_bounded_and_reuses_tasks(self):
        client = Mock()
        client.videos.generations.return_value = {'id': 'new-task'}
        doc = {'shots': {'S01': dict(status='queued', task_id='live', request_hash='hash')}}
        shots = [{'id': f'S{i:02}'} for i in range(1, 8)]
        def record(doc, label, sid, **values):
            values.pop('publish', None)
            doc['shots'][sid] = values
        with patch.object(g, 'request_hash', return_value='hash'), patch.object(g, 'full_payload', return_value={}), patch.object(g, 'reference_sha256', return_value=None), patch.object(g, 'checkpoint', side_effect=record):
            g.prefill(client, {}, shots, doc, False)
            self.assertEqual(client.videos.generations.call_count, 2)
            g.prefill(client, {}, shots, doc, False)
            self.assertEqual(client.videos.generations.call_count, 2)

    def test_quota_is_not_retried(self):
        self.assertFalse(g.retryable(RuntimeError('1113 余额不足')))
        self.assertTrue(g.retryable(RuntimeError('1234 网络错误')))


if __name__ == '__main__':
    unittest.main()
