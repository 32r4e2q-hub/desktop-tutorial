"""Single canary helper tests; no API/secret or network access."""
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1] / 'kimdaedoo'

class CanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        old_path = list(sys.path)
        old = sys.modules.pop('generate', None)
        try:
            spec = importlib.util.spec_from_file_location('kim_canary', HERE/'canary.py')
            cls.m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.m)
        finally:
            sys.path[:] = old_path
            sys.modules.pop('generate', None)
            if old is not None:
                sys.modules['generate'] = old

    def test_top_level_video_id(self):
        self.assertEqual(self.m.extract_ids({'video_id':'v1','task_id':'t1'}), ('v1','t1'))

    def test_nested_task_id(self):
        self.assertEqual(self.m.extract_ids({'data':{'task_id':'t1'}}), ('t1','t1'))

    def test_ambiguous_response(self):
        self.assertEqual(self.m.extract_ids({'success':True}), (None,None))

    def test_key_redacted(self):
        self.assertEqual(self.m.safe({'message':'secret-value'},'secret-value'), {'message':'[redacted]'})

    def test_only_flash_and_no_batch(self):
        self.assertEqual(self.m.MODEL,'agnes-video-2.5-flash')
        source = (HERE/'canary.py').read_text()
        self.assertIn("'accepted_tasks': 1",source)
        self.assertIn("'batch_started': False",source)
        self.assertNotIn('zhipuai',source)

if __name__=='__main__':
    unittest.main()
